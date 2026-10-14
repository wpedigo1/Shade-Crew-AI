"""Punch Board item 28 (backend verification half) — Compare (no-moderator) path.

Mission 028 verifies an already-shipped but completely unexercised capability:
``TwoWorkerRequest.moderator_model`` is optional and ``registry._run_phase`` /
``orchestrator.multiplex_workers`` already support a two-worker run with no
moderator phase. Before writing any new Compare-mode orchestration code, this
mission proves whether that existing path is correct end to end.

Every scenario is driven through the REAL HTTP surface (``POST
/api/modelmix/runs/stream`` with ``moderator_model`` omitted), using the exact
harness already established in ``test_modelmix_alpha_acceptance.py``: a bare
``FastAPI()`` + ``include_router(router)``, ``run_registry`` and
``get_provider_for_model`` monkeypatched to deterministic fakes, isolated
``tmp_path`` persistence, SSE parsed by stripping the ``data: `` prefix.

The seven numbered investigation points in the mission each map to at least one
test with an evidence-based assertion rather than a guess about what "should
happen":
  1. normal two-worker run with no moderator events at all;
  2. one worker fails -> run_completed "partial" + persisted document reflects
     one failed seat (read back via GET /sessions/{id});
  3. both workers fail -> observe and assert the real terminal behavior;
  4. multi-turn isolation still holds moderator-less, and the dead
     ``seat_histories["moderator"]`` data does not leak into either worker;
  5. per-worker guardrails (warning/hard cap) still apply moderator-less;
  6. cancellation still reaches ``run_cancelled`` mid-stream moderator-less;
  7. reopening a moderator-less session reconstructs with no moderator message
     and nothing downstream chokes on the moderator's absence.

No production behavior is patched by this mission. If a genuine defect had been
found it would be reported separately rather than silently fixed.
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


MODERATOR_EVENT_TYPES = {
    "moderator_started",
    "moderator_delta",
    "moderator_completed",
    "moderator_failed",
    "moderator_output_warning",
}


def build_app(monkeypatch, tmp_path, providers):
    """Bare FastAPI app wired to deterministic fakes (alpha-acceptance pattern)."""
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


# ---------------------------------------------------------------------------
# Investigation point 1 — normal no-moderator run emits no moderator events.
# ---------------------------------------------------------------------------


def test_no_moderator_normal_run_streams_both_workers_without_moderator_events(
    monkeypatch, tmp_path
):
    providers = {
        "model-a": FakeStreamingProvider(("A1 ", "A2"), usage={"total_tokens": 17}),
        "model-b": FakeStreamingProvider(("B1 ", "B2"), usage={"total_tokens": 23}),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "two witnesses, no moderator",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    assert events[0]["type"] == "run_started"
    assert seat_deltas(events, "seat_delta", "worker_a") == ["A1 ", "A2"]
    assert seat_deltas(events, "seat_delta", "worker_b") == ["B1 ", "B2"]
    assert [event["type"] for event in events].count("seat_completed") == 2

    moderator_events = [
        event["type"] for event in events if event["type"] in MODERATOR_EVENT_TYPES
    ]
    assert moderator_events == []

    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))


# ---------------------------------------------------------------------------
# Investigation point 2 — one worker fails moderator-less, run_completed partial,
# persisted session reflects one seat succeeded and one failed.
# ---------------------------------------------------------------------------


def test_no_moderator_one_worker_fails_reaches_partial_and_persists_failure(
    monkeypatch, tmp_path
):
    providers = {
        "model-a": FakeStreamingProvider(("partial alpha",), failure="worker A exploded"),
        "model-b": FakeStreamingProvider(("usable B",)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        posted = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "one witness breaks",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
            },
        )
        run_id = posted.headers.get("X-ModelMix-Run-ID")
        session_id = posted.headers.get("X-ModelMix-Session-ID")
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")

    assert posted.status_code == 200 and reopened.status_code == 200
    events = parse_sse(posted)
    assert any(
        event["type"] == "seat_failed" and event["seat_id"] == "worker_a"
        for event in events
    )
    assert not any(event["type"] == "seat_failed" and event["seat_id"] == "worker_b"
                   for event in events)
    assert seat_deltas(events, "seat_delta", "worker_b") == ["usable B"]
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"

    document = reopened.json()
    messages = document["session"]["messages"]
    by_seat = {
        message["seat"]: message
        for message in messages
        if message["run_id"] == run_id and message["role"] == "assistant"
    }
    assert by_seat["worker_a"]["status"] == "failed"
    assert by_seat["worker_a"]["error"] == "worker A exploded"
    assert by_seat["worker_b"]["status"] == "completed"
    assert by_seat["worker_b"]["content"] == "usable B"
    assert "moderator" not in by_seat


# ---------------------------------------------------------------------------
# Investigation point 3 — both workers fail moderator-less: the honest terminal
# status is "failed" (nothing survived to look at), aligning the no-moderator
# path with the moderator path's all-failed outcome. Corrected by Mission 029.
# ---------------------------------------------------------------------------


def test_no_moderator_both_workers_fail_reaches_run_completed_failed(
    monkeypatch, tmp_path
):
    providers = {
        "model-a": FakeStreamingProvider(("a ", "delta"), failure="A exploded"),
        "model-b": FakeStreamingProvider(("b ", "delta"), failure="B exploded"),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "both witnesses break",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    failed_seats = {
        event.get("seat_id")
        for event in events
        if event["type"] == "seat_failed"
    }
    assert failed_seats == {"worker_a", "worker_b"}
    assert not any(event["type"] in MODERATOR_EVENT_TYPES for event in events)
    # Corrected honest-terminal behavior (Mission 029): every seat that ran
    # failed, so multiplex_workers emits run_completed with status "failed" --
    # matching the moderator path's all-failed outcome -- rather than the
    # previous misleading "partial", and it never emits run_failed.
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "failed"


# ---------------------------------------------------------------------------
# Investigation point 4 — multi-turn isolation holds moderator-less, and the
# dead seat_histories["moderator"] data never leaks into either worker.
# ---------------------------------------------------------------------------


def test_no_moderator_multiturn_isolation_holds_and_moderator_key_never_leaks(
    monkeypatch, tmp_path
):
    prompt_1 = "FIRST_PROMPT_NO_MOD_ISOLATION"
    worker_a_1 = "FIRST_TURN_WORKER_A_NO_MOD_ISOLATION"
    worker_b_1 = "FIRST_TURN_WORKER_B_NO_MOD_ISOLATION"
    prompt_2 = "SECOND_PROMPT_NO_MOD_ISOLATION"
    worker_a_2 = "SECOND_TURN_WORKER_A_NO_MOD_ISOLATION"
    worker_b_2 = "SECOND_TURN_WORKER_B_NO_MOD_ISOLATION"
    moderator_poison = "THIS_MODERATOR_DATA_MUST_NEVER_REACH_A_WORKER"

    providers = {
        "model-a": FakeStreamingProvider((worker_a_1,)),
        "model-b": FakeStreamingProvider((worker_b_1,)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        first = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_1,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
            },
        )
        assert first.status_code == 200
        session_id = first.headers.get("X-ModelMix-Session-ID")
        assert session_id
        assert parse_sse(first)[-1]["status"] == "completed"

        providers["model-a"] = FakeStreamingProvider((worker_a_2,))
        providers["model-b"] = FakeStreamingProvider((worker_b_2,))

        second = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt_2,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "session_id": session_id,
            },
        )
        assert second.status_code == 200
        assert parse_sse(second)[-1]["status"] == "completed"

    worker_a_history = providers["model-a"].messages[0]
    worker_b_history = providers["model-b"].messages[0]

    assert worker_a_history == [
        {"role": "user", "content": prompt_1},
        {"role": "assistant", "content": worker_a_1},
        {"role": "user", "content": prompt_2},
    ]
    assert worker_a_2 not in json.dumps(worker_a_history)
    assert worker_b_1 not in json.dumps(worker_a_history)
    assert worker_b_2 not in json.dumps(worker_a_history)
    assert moderator_poison not in json.dumps(worker_a_history)

    assert worker_b_history == [
        {"role": "user", "content": prompt_1},
        {"role": "assistant", "content": worker_b_1},
        {"role": "user", "content": prompt_2},
    ]
    assert worker_b_2 not in json.dumps(worker_b_history)
    assert worker_a_1 not in json.dumps(worker_b_history)
    assert worker_a_2 not in json.dumps(worker_b_history)
    assert moderator_poison not in json.dumps(worker_b_history)

    # The second turn's own output is not part of its own input history (correct
    # ordering), and neither worker ever receives moderator data of any kind.
    assert worker_a_1 in json.dumps(worker_a_history)
    assert worker_b_1 in json.dumps(worker_b_history)

    # seat_histories in a moderator-less session still carries a "moderator" key
    # (registry always builds it), but it is never forwarded to either worker
    # because _run_phase passes only worker_a/worker_b histories downstream.
    for provider in (providers["model-a"], providers["model-b"]):
        for payload in provider.messages:
            assert moderator_poison not in json.dumps(payload)


# ---------------------------------------------------------------------------
# Investigation point 5 — per-worker guardrails still apply moderator-less.
# ---------------------------------------------------------------------------


def test_no_moderator_guardrails_still_apply_to_each_worker(monkeypatch, tmp_path):
    providers = {
        "model-a": FakeStreamingProvider(("x" * 250,)),
        "model-b": FakeStreamingProvider(("y" * 250,)),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        response = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": "cap both witnesses",
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
                "warning_threshold_chars": 100,
                "hard_cap_chars": 200,
            },
        )

    assert response.status_code == 200
    events = parse_sse(response)
    warnings = [
        event for event in events if event["type"] == "seat_output_warning"
    ]
    assert len(warnings) == 2
    assert {event["seat_id"] for event in warnings} == {"worker_a", "worker_b"}
    assert all(event["threshold"] == 100 for event in warnings)

    capped = [
        event for event in events
        if event.get("finish_reason") == "modelmix_output_cap"
    ]
    assert len(capped) == 2
    assert "".join(seat_deltas(events, "seat_delta", "worker_a")) == "x" * 200
    assert "".join(seat_deltas(events, "seat_delta", "worker_b")) == "y" * 200

    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


# ---------------------------------------------------------------------------
# Investigation point 6 — cancellation still reaches run_cancelled mid-stream
# for a moderator-less run.
# ---------------------------------------------------------------------------


async def test_no_moderator_cancel_reaches_run_cancelled_mid_stream(monkeypatch, tmp_path):
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
                    "prompt": "cancel me mid-run, no moderator",
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
        assert cancel.json()["cancellation_requested"] is True

        for _ in range(1000):
            if run.status in {"cancelled", "failed", "completed", "partial"}:
                break
            await asyncio.sleep(0.01)
        assert run.status == "cancelled"

        response = await asyncio.wait_for(stream_task, timeout=10)

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
    assert providers["model-a"].cancelled and providers["model-b"].cancelled


# ---------------------------------------------------------------------------
# Investigation point 7 — reopening a moderator-less session reconstructs with
# no moderator message at all; nothing downstream chokes on the moderator's
# absence.
# ---------------------------------------------------------------------------


def test_no_moderator_reopen_session_reconstructs_without_moderator_message(
    monkeypatch, tmp_path
):
    prompt = "reopen a moderatorkess session"
    providers = {
        "model-a": FakeStreamingProvider(("alpha ", "answer")),
        "model-b": FakeStreamingProvider(("beta ", "answer")),
    }
    app, _registry = build_app(monkeypatch, tmp_path, providers)

    with TestClient(app) as client:
        posted = client.post(
            "/api/modelmix/runs/stream",
            json={
                "prompt": prompt,
                "worker_a_model": "model-a",
                "worker_b_model": "model-b",
            },
        )
        session_id = posted.headers.get("X-ModelMix-Session-ID")
        run_id = posted.headers.get("X-ModelMix-Run-ID")
        assert session_id and run_id
        reopened = client.get(f"/api/modelmix/sessions/{session_id}")

    assert reopened.status_code == 200
    document = reopened.json()
    assert document["schema_version"] == 1
    messages = document["session"]["messages"]
    run_messages = [
        message for message in messages if message["run_id"] == run_id
    ]
    by_seat = {
        message["seat"]: message for message in run_messages if message["role"] == "assistant"
    }
    assert set(by_seat) == {"worker_a", "worker_b"}
    assert by_seat["worker_a"]["content"] == "alpha answer"
    assert by_seat["worker_b"]["content"] == "beta answer"
    assert "moderator" not in by_seat
    assert not any(message["seat"] == "moderator" for message in run_messages)

    user_message = next(
        message for message in run_messages if message["role"] == "user"
    )
    assert user_message["content"] == prompt

    snapshot = next(
        run for run in document["session"]["runs"] if run["run_id"] == run_id
    )
    assert snapshot["status"] == "completed"
    assert snapshot["latest_seq"] == len(snapshot["events"])
    assert all(event["run_id"] == run_id for event in snapshot["events"])
    assert not any(event["type"] in MODERATOR_EVENT_TYPES for event in snapshot["events"])
    # The persisted models dict still carries a "moderator" key set to None;
    # validation tolerates it and no moderator event/message is produced.
    assert snapshot["models"]["moderator"] is None
