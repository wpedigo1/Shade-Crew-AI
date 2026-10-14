"""Mission 052 — spend confirmation gate (backend).

A user can set a per-request spend limit. If the LAST completed run in a session
had any seat/moderator whose real, already-persisted cost exceeded it, the next
run is blocked (402) until the request explicitly confirms — enforcing on a known
past fact, never a guess. Per-seat only; no aggregation; unknown cost is never
treated as over-budget.
"""

import asyncio
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.providers.base import LLMProvider, ProviderStreamEvent


class FakeStreamingProvider(LLMProvider):
    """Deterministic streaming fake (pattern from the alpha-acceptance harness)."""

    def __init__(self, deltas=(), *, usage=None):
        self.deltas = tuple(deltas)
        self.usage = usage
        self.messages = []

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        for delta in self.deltas:
            await asyncio.sleep(0)
            yield ProviderStreamEvent(type="text_delta", delta=delta)
        result = {"content": "".join(self.deltas)}
        if self.usage is not None:
            result["usage"] = self.usage
        yield ProviderStreamEvent(type="completed", result=result, finish_reason="stop")

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("streaming fake must not use query fallback")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class BlowUpProvider(LLMProvider):
    """Raise if ever used — proves the gate rejects before provider lookup."""

    def __getattr__(self, name):
        raise AssertionError(
            f"provider must never be resolved by the gate test: used {name}"
        )

    async def stream_query(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("provider must never be resolved")

    async def query(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("provider must never be resolved")

    async def get_models(self):  # pragma: no cover
        raise AssertionError("provider must never be resolved")

    async def validate_key(self, api_key):  # pragma: no cover
        raise AssertionError("provider must never be resolved")


def build_app(monkeypatch, tmp_path, resolver):
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    monkeypatch.setattr("backend.modelmix.routes.run_registry", registry)
    monkeypatch.setattr("backend.modelmix.routes.get_provider_for_model", resolver)
    app = FastAPI()
    app.include_router(router)
    return app, registry


AUDIENCE_BY_SEAT = {
    "worker_a": ["worker_a"],
    "worker_b": ["worker_b"],
    "moderator": ["moderator", "user"],
}


def seed_session_with_costs(tmp_path, session_id, costs, run_id="prior-run"):
    """Persist a single completed last run whose seats carry the given costs.

    ``costs`` maps seat -> cost_usd (None for unknown). A user message is always
    present and cost-less, matching the real persisted shape. Written directly to
    disk with its own persistence instance so the app's separate instance (and
    event loop) reads it cleanly.
    """
    run = {
        "run_id": run_id,
        "prompt": "previous prompt",
        "models": {"worker_a": "model-a", "moderator": "model-m", "worker_b": "model-b"},
        "status": "completed",
        "latest_seq": 1,
        "events": [{
            "run_id": run_id,
            "seq": 1,
            "type": "run_completed",
            "status": "completed",
            "ts": 1.0,
        }],
    }

    async def _seed():
        persistence = AtomicJsonModelMixPersistence(tmp_path)
        await persistence.create_session(session_id)
        document = await persistence.load_session(session_id)
        now = time.time()
        document = {
            "schema_version": 1,
            "session": {
                "session_id": session_id,
                "created_at": now,
                "updated_at": now,
                "messages": [
                    {
                        "message_id": f"{run_id}:user",
                        "run_id": run_id,
                        "seat": "shared",
                        "audience": ["worker_a", "worker_b", "moderator"],
                        "role": "user",
                        "content": run["prompt"],
                    },
                    *[
                        {
                            "message_id": f"{run_id}:{seat}",
                            "run_id": run_id,
                            "seat": seat,
                            "audience": AUDIENCE_BY_SEAT[seat],
                            "role": "assistant",
                            "content": "final answer",
                            "status": "completed",
                            "error": None,
                            "usage": None,
                            "finish_reason": "stop",
                            "cost_usd": cost,
                            "started_at": 1.0,
                            "completed_at": 2.0,
                        }
                        for seat, cost in costs.items()
                    ],
                ],
                "runs": [run],
            },
        }
        persistence._write_atomic(persistence._path(session_id), document)

    asyncio.run(_seed())


def seed_empty_session(tmp_path, session_id):
    asyncio.run(AtomicJsonModelMixPersistence(tmp_path).create_session(session_id))


def stream_post(client, body):
    return client.post("/api/modelmix/runs/stream", json=body)


def test_single_seat_over_limit_rejects_402_and_never_resolves_provider(monkeypatch, tmp_path):
    session_id = "gate-session-1"
    app, registry = build_app(monkeypatch, tmp_path, BlowUpProvider())
    seed_session_with_costs(tmp_path, session_id, {"worker_b": 0.30})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.10,
        })

    assert response.status_code == 402
    detail = response.json()["detail"]
    assert "worker_b" in detail
    assert "0.3" in detail


def test_over_limit_with_confirmation_proceeds_normally(monkeypatch, tmp_path):
    session_id = "gate-session-2"
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_session_with_costs(tmp_path, session_id, {"worker_a": 0.50})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.10,
            "confirm_over_budget": True,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_all_costs_under_limit_proceeds_without_confirmation(monkeypatch, tmp_path):
    session_id = "gate-session-3"
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_session_with_costs(tmp_path, session_id, {"worker_a": 0.01, "worker_b": 0.02})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.10,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_unknown_cost_never_triggers_rejection(monkeypatch, tmp_path):
    session_id = "gate-session-4"
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_session_with_costs(tmp_path, session_id, {"worker_a": None, "worker_b": None})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.001,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_session_with_no_prior_runs_proceeds_even_with_limit(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_empty_session(tmp_path, "empty-session")

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": "empty-session",
            "spend_limit_usd": 0.01,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_no_session_id_proceeds_even_with_limit(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "spend_limit_usd": 0.01,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_omitting_spend_limit_is_unchanged_regression(monkeypatch, tmp_path):
    session_id = "gate-session-6"
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_session_with_costs(tmp_path, session_id, {"worker_a": 9.99})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
        })

    assert response.status_code == 200
    assert providers["model-a"].messages


def test_multiple_over_budget_seats_rejects_not_an_aggregate(monkeypatch, tmp_path):
    session_id = "gate-session-7"
    app, registry = build_app(monkeypatch, tmp_path, BlowUpProvider())
    seed_session_with_costs(tmp_path, session_id, {"worker_a": 0.30, "worker_b": 0.08})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.10,
        })

    # worker_a (0.30) is over; worker_b (0.08) is under. Aggregate 0.38 would also
    # be over, but the check is per-seat: only worker_a trips it and is named.
    assert response.status_code == 402
    detail = response.json()["detail"]
    assert "worker_a" in detail
    assert "0.3" in detail


def test_confirm_over_budget_bypasses_when_multiple_seats_over(monkeypatch, tmp_path):
    session_id = "gate-session-8"
    providers = {
        "model-a": FakeStreamingProvider(("A",), usage={"total_tokens": 10}),
        "model-b": FakeStreamingProvider(("B",), usage={"total_tokens": 10}),
        "model-m": FakeStreamingProvider(("M",), usage={"total_tokens": 10}),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers.__getitem__)
    seed_session_with_costs(tmp_path, session_id, {"worker_a": 0.40, "worker_b": 0.60})

    with TestClient(app) as client:
        response = stream_post(client, {
            "prompt": "new question",
            "worker_a_model": "model-a",
            "worker_b_model": "model-b",
            "moderator_model": "model-m",
            "session_id": session_id,
            "spend_limit_usd": 0.10,
            "confirm_over_budget": True,
        })

    assert response.status_code == 200
