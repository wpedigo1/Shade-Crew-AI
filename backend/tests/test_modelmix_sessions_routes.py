"""Mission 048: session listing and deletion routes over the real HTTP surface."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.tests.mock_providers import streaming_provider, timeout_provider


def build_app(monkeypatch, tmp_path, providers):
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    monkeypatch.setattr("backend.modelmix.routes.run_registry", registry)
    monkeypatch.setattr(
        "backend.modelmix.routes.get_provider_for_model",
        lambda model_id: providers[model_id],
    )
    app = FastAPI()
    app.include_router(router)
    return app, registry


async def client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_list_sessions_route_empty_and_after_creation(monkeypatch, tmp_path):
    providers = {"model-a": streaming_provider(("hi",))}
    app, registry = build_app(monkeypatch, tmp_path, providers)

    async with await client_for(app) as client:
        empty = await client.get("/api/modelmix/sessions")
        assert empty.status_code == 200
        assert empty.json() == []

        await registry.persistence.create_session("alpha")
        await registry.persistence.create_session("beta")

        listing = await client.get("/api/modelmix/sessions")
        assert listing.status_code == 200
        sessions = listing.json()
        assert {s["session_id"] for s in sessions} == {"alpha", "beta"}
        for summary in sessions:
            assert "messages" not in summary
            assert "runs" not in summary
            assert "message_count" in summary


@pytest.mark.asyncio
async def test_delete_session_route_success_then_404(monkeypatch, tmp_path):
    providers = {"model-a": streaming_provider(("hi",))}
    app, registry = build_app(monkeypatch, tmp_path, providers)
    await registry.persistence.create_session("alpha")

    async with await client_for(app) as client:
        deleted = await client.delete("/api/modelmix/sessions/alpha")
        assert deleted.status_code == 204

        gone = await client.get("/api/modelmix/sessions/alpha")
        assert gone.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_route_nonexistent_404_and_bad_id_422(monkeypatch, tmp_path):
    providers = {"model-a": streaming_provider(("hi",))}
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    async with await client_for(app) as client:
        missing = await client.delete("/api/modelmix/sessions/nope")
        assert missing.status_code == 404

        bad = await client.delete("/api/modelmix/sessions/bad%20id")
        assert bad.status_code == 422


@pytest.mark.asyncio
async def test_delete_route_409_when_session_has_active_run(monkeypatch, tmp_path):
    providers = {
        "model-a": timeout_provider(),
        "model-b": timeout_provider(),
        "model-m": timeout_provider(),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers)
    session_id = "session-with-active-run"

    async with await client_for(app) as client:
        stream_task = asyncio.create_task(
            client.post(
                "/api/modelmix/runs/stream",
                json={
                    "prompt": "question",
                    "worker_a_model": "model-a",
                    "worker_b_model": "model-b",
                    "moderator_model": "model-m",
                    "session_id": session_id,
                },
            )
        )

        loop = asyncio.get_running_loop()
        deadline = loop.time() + 5
        run_id = None
        while run_id is None:
            run_id = await registry.active_run_for_session(session_id)
            if run_id is not None:
                break
            if loop.time() >= deadline:
                raise TimeoutError("run never became active")
            await asyncio.sleep(0.01)

        refused = await client.delete(f"/api/modelmix/sessions/{session_id}")
        assert refused.status_code == 409

        await client.post(f"/api/modelmix/runs/{run_id}/cancel")

        # Wait until the run is terminal so the session is no longer protected.
        deadline = loop.time() + 5
        while await registry.active_run_for_session(session_id) is not None:
            if loop.time() >= deadline:
                raise TimeoutError("run never went terminal after cancel")
            await asyncio.sleep(0.01)

        deleted = await client.delete(f"/api/modelmix/sessions/{session_id}")
        assert deleted.status_code == 204

        await stream_task