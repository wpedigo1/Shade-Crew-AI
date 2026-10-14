"""Punch Board item 33 — alpha acceptance overview driven through the real HTTP surface.

Mission 022 differs from earlier slices: it does not test new capability, and it
does not call internal functions directly like the existing unit tests do. It
chains the backend-provable item-33 checklist items together through the real
FastAPI routes the way a real user session would, using the established
TestClient + monkeypatch pattern from
``test_modelmix_streaming.py::test_modelmix_route_resolves_both_models_without_ranking``
(bare ``FastAPI()`` + ``include_router(router)``, ``run_registry`` and
``get_provider_for_model`` monkeypatched to deterministic fakes, SSE parsed by
stripping the ``data: `` prefix).

Scope split (stated plainly): "Launch", "three panels", and "configure
A/B/Moderator" are UI-rendering claims already proven by existing frontend
component tests (Mission 014 reachability, Mission 016 panel view, Mission 007
selectors). This file proves the remaining, backend-provable checklist items:
stream both workers, stream Moderator, cancel, survive worker failure, reopen
session, multi-turn isolation, honest telemetry, and no credential leak.

One deliberate harness note: the cancel scenario is the only one that requires
two in-flight requests (the streaming POST holds the socket open until the run
is terminal, so a synchronous TestClient cannot issue the cancel mid-run). It
uses the existing single-loop route pattern from
``test_modelmix_journal.py::test_replay_route_supports_cursor_last_event_id_and_clear_errors``
(``httpx.AsyncClient`` + ``ASGITransport`` on one loop), rather than running
two TestClient portals on separate loops that would share the same asyncio
locks. Everything that does not need concurrent control uses the exact sync
TestClient pattern.

During the investigation of the cancel scenario, a robustness race in the
production cancellation path was observed through this real-surface harness:
issuing the cancel within the sub-millisecond window right after the first
seat delta (by polling the journal on an ``asyncio.sleep(0)`` tight loop)
reliably left ``_run_phase`` stuck in ``multiplex_workers``' ``finally``
gather, with one seat provider task never receiving its ``CancelledError`` and
the run stuck ``active`` until the run timeout. With a natural 10ms polling
rhythm the cancel completes cleanly. That race is disclosed in the mission
report as an unresolved robustness risk; this verify-only mission does not
patch production code. The test below uses the natural rhythm so the primary
claim (cancel works through the real HTTP surface) is proven without relying
on the pathological micro-window.
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


class FakeStreamingProvider(LLMProvider):
    """Deterministic streaming fake (pattern from test_modelmix_moderator.py).

    Emits its fixed deltas, then either completes with an optional usage /
    finish_reason or fails, optionally only after a gate is released.
    """

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
    """Streams its deltas, then blocks forever until cancelled (timeouts pattern)."""

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
    """Bare FastAPI app wired to deterministic fakes (streaming-test pattern)."""
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
    """Discover the in-flight run through the real /sessions/latest route."""
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


def test_scenario_1_full_run_streams_both_workers_then_moderator(monkeypatch, tmp_path):
    """Both workers stream fully, then the Moderator, then run_completed."""
    providers = {
        "model-a": FakeStreamingProvider(("A1 ", "A2"), usage={"total_tokens": 17}),
        "model-b": FakeStreamingProvider(("B1 ", "B2"), usage={"total_tokens": 23}),
        "model-m": FakeStreamingProvider(("M1 ", "M2"), usage={"total_tokens": 31}),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "synthesize the witnesses",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    assert events[0]["type"] == "run_started"
    assert seat_deltas(events, "seat_delta", "worker_a") == ["A1 ", "A2"]
    assert seat_deltas(events, "seat_delta", "worker_b") == ["B1 ", "B2"]
    assert [event["type"] for event in events].count("seat_completed") == 2

    last_worker_done = max(
        event["seq"] for event in events if event["type"] == "seat_completed"
    )
    first_moderator = next(
        event["seq"] for event in events if event["type"] == "moderator_started"
    )
    assert last_worker_done < first_moderator
    assert seat_deltas(events, "moderator_delta") == ["M1 ", "M2"]
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))


async def test_scenario_2_cancel_route_stops_stream_without_post_cancel_deltas(monkeypatch, tmp_path):
    """POST /runs/stream hangs, POST /runs/{id}/cancel drives run_cancelled.

    Cancel is issued through the real route once output is visibly streaming
    (the delta-wait polls on a 10ms rhythm so cancellation does not land inside
    the seat's emission micro-window; issuing cancel in that sub-millisecond
    window is a separately-observed race, disclosed in the mission report).
    """
    providers = {
        "model-a": DeltasThenHangProvider(("leading ", "delta")),
        "model-b": DeltasThenHangProvider(("solo",)),
    }
    app, registry = build_app(monkeypatch, tmp_path, providers)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        stream_task = asyncio.create_task(
            client.post(
                "/api/modelmix/runs/stream",
                json={
                    "prompt": "cancel me mid-run",
                    "worker_a_model": "model-a",
                    "worker_b_model": "model-b",
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
        cancel_body = cancel.json()
        assert cancel_body["run_id"] == run_id
        assert cancel_body["cancellation_requested"] is True

        for _ in range(1000):
            if run.status in {"cancelled", "failed", "completed", "partial"}:
                break
            await asyncio.sleep(0.01)
        assert run.status == "cancelled"

        response = await asyncio.wait_for(stream_task, timeout=10)
        latest = await client.get("/api/modelmix/sessions/latest")

    assert response.status_code == 200
    events = parse_sse(response)
    assert any(event["type"] == "seat_delta" for event in events)
    cancel_markers = [event for event in events if event["type"] == "run_cancel_requested"]
    assert len(cancel_markers) == 1
    cancel_seq = cancel_markers[0]["seq"]
    assert all(
        event["seq"] < cancel_seq for event in events if event["type"] == "seat_delta"
    )
    assert not any(event["type"] == "run_completed" for event in events)
    assert not any(event["type"] == "run_failed" for event in events)
    assert events[-1]["type"] == "run_cancelled"

    assert latest.status_code == 200
    latest_runs = latest.json()["session"]["runs"]
    assert any(run["run_id"] == run_id and run["status"] == "cancelled" for run in latest_runs)
    assert providers["model-a"].cancelled and providers["model-b"].cancelled


def test_scenario_3_worker_failure_survives_with_partial_moderation(monkeypatch, tmp_path):
    """One worker fails mid-output; the run completes partial from the survivor."""
    providers = {
        "model-a": FakeStreamingProvider(("partial alpha",), failure="worker A exploded"),
        "model-b": FakeStreamingProvider(("usable B",)),
        "model-m": FakeStreamingProvider(("synthesis",)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "recover from one broken witness",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    assert any(
        event["type"] == "seat_failed" and event["seat_id"] == "worker_a"
        for event in events
    )
    assert "partial alpha" in seat_deltas(events, "seat_delta", "worker_a")
    assert seat_deltas(events, "seat_delta", "worker_b") == ["usable B"]
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"

    handoff = providers["model-m"].messages[0][-1]["content"]
    assert "Worker A status:\nUnavailable because the worker failed." in handoff
    assert "Worker B visible output:\nusable B" in handoff
    assert "partial alpha" not in handoff
    assert seat_deltas(events, "moderator_delta") == ["synthesis"]


def test_scenario_4_reopen_session_reconstructs_full_conversation(monkeypatch, tmp_path):
    """GET /sessions/{session_id} rebuilds the conversation from the stream."""
    prompt = "reopen me"
    providers = {
        "model-a": FakeStreamingProvider(("alpha ", "answer")),
        "model-b": FakeStreamingProvider(("beta ", "answer")),
        "model-m": FakeStreamingProvider(("moderated ", "answer")),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        posted = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )
        session_id = posted.headers.get("X-ModelMix-Session-ID")
        run_id = posted.headers.get("X-ModelMix-Run-ID")
        assert session_id
        assert run_id
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")

    assert reopened.status_code == 200
    document = reopened.json()
    assert document["schema_version"] == 1
    messages = document["session"]["messages"]
    by_seat = {message["seat"]: message for message in messages if message["run_id"] == run_id}
    assert by_seat["worker_a"]["content"] == "alpha answer"
    assert by_seat["worker_b"]["content"] == "beta answer"
    assert by_seat["moderator"]["content"] == "moderated answer"
    user_message = next(message for message in messages if message["run_id"] == run_id and message["role"] == "user")
    assert user_message["content"] == prompt

    snapshot = document["session"]["runs"][0]
    assert snapshot["run_id"] == run_id
    assert snapshot["status"] == "completed"
    assert snapshot["latest_seq"] == len(snapshot["events"])
    assert all(event["run_id"] == run_id for event in snapshot["events"])


def test_scenario_5_multi_turn_isolation_via_real_route(monkeypatch, tmp_path):
    """Same session, second turn: each worker sees only its own prior turn."""
    prompt_1 = "FIRST_PROMPT_ISOLATION_SENTINEL"
    worker_a_1 = "FIRST_TURN_WORKER_A_ONLY_ISOLATION"
    worker_b_1 = "FIRST_TURN_WORKER_B_ONLY_ISOLATION"
    moderator_1 = "FIRST_TURN_MODERATOR_SYNTHESIS_ISOLATION"
    prompt_2 = "SECOND_PROMPT_ISOLATION_SENTINEL"
    worker_a_2 = "SECOND_TURN_WORKER_A_ONLY_ISOLATION"
    worker_b_2 = "SECOND_TURN_WORKER_B_ONLY_ISOLATION"
    moderator_2 = "SECOND_TURN_MODERATOR_SYNTHESIS_ISOLATION"

    providers = {
        "model-a": FakeStreamingProvider((worker_a_1,)),
        "model-b": FakeStreamingProvider((worker_b_1,)),
        "model-m": FakeStreamingProvider((moderator_1,)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        first = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_1,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )
        assert first.status_code == 200
        session_id = first.headers.get("X-ModelMix-Session-ID")
        assert session_id
        assert parse_sse(first)[-1]["status"] == "completed"

        providers["model-a"] = FakeStreamingProvider((worker_a_2,))
        providers["model-b"] = FakeStreamingProvider((worker_b_2,))
        providers["model-m"] = FakeStreamingProvider((moderator_2,))

        second = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_2,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
                "session_id": session_id,
            },
        )
        assert second.status_code == 200
        assert parse_sse(second)[-1]["status"] == "completed"

    worker_a_history = providers["model-a"].messages[0]
    worker_b_history = providers["model-b"].messages[0]
    moderator_history = providers["model-m"].messages[0]

    assert worker_a_history == [
        {"role": "user", "content": prompt_1},
        {"role": "assistant", "content": worker_a_1},
        {"role": "user", "content": prompt_2},
    ]
    assert worker_a_1 in json.dumps(worker_a_history)
    assert prompt_1 in json.dumps(worker_a_history)
    assert worker_b_1 not in json.dumps(worker_a_history)

    assert worker_b_history == [
        {"role": "user", "content": prompt_1},
        {"role": "assistant", "content": worker_b_1},
        {"role": "user", "content": prompt_2},
    ]
    assert worker_b_1 in json.dumps(worker_b_history)
    assert prompt_1 in json.dumps(worker_b_history)
    assert worker_a_1 not in json.dumps(worker_b_history)

    assert moderator_history[1:3] == [
        {"role": "user", "content": prompt_1},
        {"role": "assistant", "content": moderator_1},
    ]
    handoff = moderator_history[-1]["content"]
    assert prompt_2 in handoff
    assert worker_a_2 in handoff
    assert worker_b_2 in handoff
    assert worker_a_1 not in json.dumps(moderator_history)
    assert worker_b_1 not in json.dumps(moderator_history)


def test_scenario_6_reopened_session_carries_honest_telemetry(monkeypatch, tmp_path):
    """Reopened messages keep exact provider usage, finish_reason, real timestamps."""
    reported = {
        "worker_a": {"total_tokens": 17},
        "worker_b": {"total_tokens": 23},
        "moderator": {"total_tokens": 31},
    }
    providers = {
        "model-a": FakeStreamingProvider(("alpha",), usage=reported["worker_a"]),
        "model-b": FakeStreamingProvider(("beta",), usage=reported["worker_b"]),
        "model-m": FakeStreamingProvider(("moderated",), usage=reported["moderator"]),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        posted = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "report honestly",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )
        run_id = posted.headers.get("X-ModelMix-Run-ID")
        session_id = posted.headers.get("X-ModelMix-Session-ID")
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")

    events = parse_sse(posted)
    completed = {
        event["seat_id"] if event["type"] == "seat_completed" else "moderator": event
        for event in events
        if event["type"] in {"seat_completed", "moderator_completed"}
    }
    assert {
        seat: completed[seat]["usage"] for seat in ("worker_a", "worker_b", "moderator")
    } == reported
    assert all(completed[seat]["finish_reason"] == "stop" for seat in completed)

    document = reopened.json()
    by_seat = {
        message["seat"]: message
        for message in document["session"]["messages"]
        if message["run_id"] == run_id and message["role"] == "assistant"
    }
    for seat in ("worker_a", "worker_b", "moderator"):
        message = by_seat[seat]
        assert message["usage"] == reported[seat]
        assert message["finish_reason"] == "stop"
        assert isinstance(message["started_at"], float) and isinstance(message["completed_at"], float)
        assert message["completed_at"] >= message["started_at"]


def test_scenario_7_fake_credential_never_leaks_into_stream_or_persistence(monkeypatch, tmp_path):
    """A credential-looking attribute on the provider never reaches any output."""
    sentinel = "sk-test-should-never-leak"
    providers = {
        "model-a": FakeStreamingProvider(("safe ", "alpha"), usage={"total_tokens": 9}),
        "model-b": FakeStreamingProvider(("safe ", "beta")),
        "model-m": FakeStreamingProvider(("safe ", "synthesis")),
    }
    for provider in providers.values():
        provider.api_key = sentinel

    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        posted = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "prove nothing leaks",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "moderator_model": "model-m",
            },
        )
        run_id = posted.headers.get("X-ModelMix-Run-ID")
        session_id = posted.headers.get("X-ModelMix-Session-ID")
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")
        replayed = client.get(f"/api/modelmix/runs/{run_id}/events")

    assert posted.status_code == 200 and reopened.status_code == 200 and replayed.status_code == 200
    assert sentinel not in posted.text
    assert sentinel not in json.dumps(reopened.json())
    assert sentinel not in replayed.text
    assert sentinel not in json.dumps([provider.messages for provider in providers.values()])
    assert sentinel not in json.dumps(parse_sse(posted))