"""Punch Board item 27 (backend half) — Solo (single-worker) mode.

Mission 030 makes ``worker_b_model`` optional end to end so a run can consist of
Worker A alone. Verified through the REAL HTTP surface, using the same harness
as ``test_modelmix_compare_mode_backend.py`` (bare ``FastAPI()`` + router,
``run_registry`` / ``get_provider_for_model`` monkeypatched to deterministic
fakes, isolated ``tmp_path`` persistence, SSE parsed by stripping ``data: ``).

Acceptance criteria exercised here:
  8.  a full Solo run streams Worker A deltas only, with zero worker_b /
      moderator events and a ``run_completed`` / ``completed`` terminal;
  9.  a Solo worker failure honestly reaches ``run_completed`` / ``failed``;
  10. the route rejects (422) the hybrid ``worker_b``-absent + ``moderator``
      combination BEFORE any provider resolver call;
  11. multi-turn isolation holds across a Solo-then-Mix sequence (worker_b never
      sees the Solo turn's Worker A output; persisted models encode the shape);
  12. per-worker guardrails and mid-stream cancellation still apply to the Solo
      worker.
"""

import asyncio
import json

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.providers.base import LLMProvider, ProviderStreamEvent

MODERATOR_EVENT_TYPES = {
    "moderator_started",
    "moderator_delta",
    "moderator_completed",
    "moderator_failed",
    "moderator_output_warning",
}

WORKER_B_MARKERS = ("worker_b",)


class FakeStreamingProvider(LLMProvider):
    """Deterministic streaming fake (same pattern as alpha acceptance)."""

    def __init__(self, deltas=(), *, gate=None, failure=None, usage=None, finish_reason="stop"):
        self.deltas = tuple(deltas)
        self.gate = gate
        self.failure = failure
        self.usage = usage
        self.finish_reason = finish_reason
        self.messages = []
        self.started = False
        self.cancelled = False

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.started = True
        self.messages.append(messages)
        try:
            if self.gate is not None:
                await self.gate.wait()
            for delta in self.deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            if self.failure is not None:
                yield ProviderStreamEvent(type="error", error_message=self.failure)
                return
            result = {"content": "".join(self.deltas)}
            if self.usage is not None:
                result["usage"] = self.usage
            yield ProviderStreamEvent(type="completed", result=result, finish_reason=self.finish_reason)
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("streaming fake must not use query fallback")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class DeltasThenHangProvider(FakeStreamingProvider):
    """Streams its deltas, then blocks forever until cancelled (cancel pattern)."""

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.started = True
        self.messages.append(messages)
        try:
            for delta in self.deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


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


def parse_sse(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def seat_deltas(events, event_type, seat_id=None):
    return [
        event["delta"]
        for event in events
        if event["type"] == event_type
        and (seat_id is None or event.get("seat_id") == seat_id)
    ]


async def active_run_id_via_session_route(client):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 5
    while True:
        response = await client.get("/api/modelmix/sessions/latest")
        if response.status_code == 200:
            for run in response.json()["session"]["runs"]:
                if run["status"] == "active":
                    return run["run_id"]
        if loop.time() >= deadline:
            raise TimeoutError("the run never became active in the persisted session")
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# Criterion 8 — a full Solo run streams Worker A only, no worker_b/moderator
# events, and ends run_completed / completed.
# ---------------------------------------------------------------------------


def test_solo_run_streams_only_worker_a_and_completes(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("alone ", "here"), usage={"total_tokens": 5}),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "solo run, no second worker",
                "worker_a_model": "model-a",
            },
        )
        session_id = response.headers.get("X-ModelMix-Session-ID")
        run_id = response.headers.get("X-ModelMix-Run-ID")
        assert session_id and run_id
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")

    assert response.status_code == 200
    events = parse_sse(response)
    assert events[0]["type"] == "run_started"
    assert events[0]["seats"] == ["worker_a"]
    assert seat_deltas(events, "seat_delta", "worker_a") == ["alone ", "here"]
    assert not any(WORKER_B_MARKERS[0] in str(event) for event in events)
    assert not any(
        event["type"] in MODERATOR_EVENT_TYPES or event.get("actor") == "moderator"
        for event in events
    )
    assert [event["type"] for event in events].count("seat_completed") == 1
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))

    # The persisted model snapshot encodes the Solo shape: worker_a present,
    # worker_b key absent, moderator key None (as in Compare).
    snapshot = next(
        run for run in reopened.json()["session"]["runs"] if run["run_id"] == run_id
    )
    assert snapshot["models"]["worker_a"] == "model-a"
    assert "worker_b" not in snapshot["models"]
    assert snapshot["models"]["moderator"] is None


# ---------------------------------------------------------------------------
# Criterion 9 — a Solo worker failure honestly reaches run_completed / failed.
# ---------------------------------------------------------------------------


def test_solo_worker_failure_reaches_run_completed_failed(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("something ", "then breaks"), failure="A exploded"),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "solo witness breaks",
                "worker_a_model": "model-a",
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    assert any(
        event["type"] == "seat_failed" and event["seat_id"] == "worker_a"
        for event in events
    )
    # Every seat that ran failed, so the honest terminal is run_completed/failed
    # (Mission 029 semantics preserved for the single-seat Solo path).
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "failed"


# ---------------------------------------------------------------------------
# Criterion 10 — the worker_b-absent + moderator hybrid is rejected with 422
# before any provider resolver call.
# ---------------------------------------------------------------------------


def test_solo_requests_default_to_no_worker_b(monkeypatch, tmp_path):
    app, _registry = build_app(
        monkeypatch, tmp_path, {"model-a": FakeStreamingProvider(("x",))}
    )

    with TestClient(app) as client:
        for payload in [
            {"prompt": "p", "worker_a_model": "model-a"},
            {"prompt": "p", "worker_a_model": "model-a", "worker_b_model": None},
        ]:
            response = client.post("/api/modelmix/runs/stream", json=payload)
            assert response.status_code == 200
            events = parse_sse(response)
            assert events[0]["seats"] == ["worker_a"]
            assert events[-1]["type"] == "run_completed"


def test_moderator_without_worker_b_rejected_422_before_resolver(monkeypatch, tmp_path):
    called = []

    def resolver(model_id):
        called.append(model_id)
        raise AssertionError(f"resolver must not be called for {model_id}")

    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    monkeypatch.setattr("backend.modelmix.routes.run_registry", registry)
    monkeypatch.setattr("backend.modelmix.routes.get_provider_for_model", resolver)
    app = FastAPI()
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "moderator needs a second witness",
                "worker_a_model": "model-a",
                "moderator_model": "model-m",
            },
        )

    assert response.status_code == 422
    assert called == []
    assert "worker_b_model" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Criterion 11 — multi-turn isolation: a Solo turn then a Mix turn. Worker B in
# the Mix turn must never see the Solo turn's Worker A output.
# ---------------------------------------------------------------------------


def test_solo_then_mix_turn_isolation_holds(monkeypatch, tmp_path):
    prompt_solo = "PROMPT_SOLO_SENTINEL"
    worker_a_solo = "WORKER_A_SOLO_SENTINEL"
    prompt_mix = "PROMPT_MIX_SENTINEL"
    worker_a_mix = "WORKER_A_MIX_SENTINEL"
    worker_b_mix = "WORKER_B_MIX_SENTINEL"

    providers = {
        "model-a": FakeStreamingProvider((worker_a_solo,)),
        "model-b": FakeStreamingProvider((worker_b_mix,)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        # Solo turn: exactly one participant.
        first = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_solo,
                "worker_a_model": "model-a",
            },
        )
        assert first.status_code == 200
        assert parse_sse(first)[0]["seats"] == ["worker_a"]
        assert parse_sse(first)[-1]["status"] == "completed"
        session_id = first.headers.get("X-ModelMix-Session-ID")
        assert session_id

        # Mix turn in the same session.
        providers["model-a"] = FakeStreamingProvider((worker_a_mix,))
        second = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_mix,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "session_id": session_id,
            },
        )
        assert second.status_code == 200
        assert parse_sse(second)[-1]["status"] == "completed"

    # Worker B in the Mix turn gets a blank history -- the Solo turn produced no
    # worker_b message, so nothing about Worker A's Solo output can leak.
    worker_b_history = providers["model-b"].messages[0]
    assert worker_b_history == [{"role": "user", "content": prompt_mix}]
    assert worker_a_solo not in json.dumps(worker_b_history)
    assert worker_a_mix not in json.dumps(worker_b_history)
    assert worker_b_mix not in json.dumps(worker_b_history)

    worker_a_mix_provider = providers["model-a"]
    assert worker_a_mix_provider.messages  # Worker A did run during the Mix turn
    worker_a_history = worker_a_mix_provider.messages[0]
    # Worker A's own prior Solo output is its permitted history...
    assert worker_a_solo in json.dumps(worker_a_history)
    # ...but Worker B's output never appears in Worker A's view (full isolation).
    assert "WORKER_B" not in json.dumps(worker_a_history)


# ---------------------------------------------------------------------------
# Criterion 12 — per-worker guardrails and mid-stream cancellation apply to the
# Solo worker.
# ---------------------------------------------------------------------------


def test_solo_worker_guardrails_still_apply(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("x" * 250,)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "cap a lone witness",
                "worker_a_model": "model-a",
                "warning_threshold_chars": 100,
                "hard_cap_chars": 200,
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    warnings = [
        event for event in events if event["type"] == "seat_output_warning"
    ]
    assert len(warnings) == 1
    assert warnings[0]["seat_id"] == "worker_a"
    assert warnings[0]["threshold"] == 100

    capped = [
        event for event in events
        if event.get("finish_reason") == "modelmix_output_cap"
    ]
    assert len(capped) == 1
    assert "".join(seat_deltas(events, "seat_delta", "worker_a")) == "x" * 200
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


async def test_solo_worker_cancel_reaches_run_cancelled_mid_stream(monkeypatch, tmp_path):
    providers = {
        "model-a": DeltasThenHangProvider(("leading ", "delta")),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        stream_task = asyncio.create_task(
            client.post(
                "/api/modelmix/runs/stream",
                json={
                    "prompt": "cancel a lone witness mid-run",
                    "worker_a_model": "model-a",
                },
            )
        )
        run_id = await active_run_id_via_session_route(client)
        run = registry._runs[run_id]
        for _ in range(500):
            if any(e["type"] == "seat_delta" for e in run._events):
                break
            await asyncio.sleep(0.01)

        cancel = await client.post(f"/api/modelmix/runs/{run_id}/cancel")
        assert cancel.status_code == 200

        for _ in range(1000):
            if run.status in {"cancelled", "failed", "completed", "partial"}:
                break
            await asyncio.sleep(0.01)
        assert run.status == "cancelled"

        response = await asyncio.wait_for(stream_task, timeout=10)

    assert response.status_code == 200
    events = parse_sse(response)
    assert any(event["type"] == "seat_delta" for event in events)
    cancel_markers = [
        event for event in events if event["type"] == "run_cancel_requested"
    ]
    assert len(cancel_markers) == 1
    assert not any(event["type"] == "run_completed" for event in events)
    assert events[-1]["type"] == "run_cancelled"
    assert providers["model-a"].cancelled
