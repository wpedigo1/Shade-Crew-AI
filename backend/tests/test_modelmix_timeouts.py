"""Mission 013 run and seat wall-clock timeout coverage."""

import asyncio
import json

from backend.modelmix.moderator import ModeratorInput, run_moderator
from backend.modelmix.orchestrator import multiplex_workers
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.timeouts import RUN_TIMEOUT_SECONDS, SEAT_TIMEOUT_SECONDS
from backend.providers.base import LLMProvider, ProviderStreamEvent


class HangingProvider(LLMProvider):
    """Produces no visible output and blocks until cancelled."""

    def __init__(self, gate=None):
        self.gate = gate
        self.cancelled = False
        self.messages = []

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        try:
            if self.gate:
                await self.gate.wait()
            await asyncio.sleep(30)
            yield ProviderStreamEvent(type="completed", result={"content": "late"})
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("query fallback was not expected")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class DeltasThenHangProvider(HangingProvider):
    """Emits fixed deltas, then blocks until cancelled."""

    def __init__(self, deltas, gate=None):
        super().__init__(gate=gate)
        self.deltas = tuple(deltas)

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        try:
            for delta in self.deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            if self.gate:
                await self.gate.wait()
            await asyncio.sleep(30)
            yield ProviderStreamEvent(type="completed", result={"content": "".join(self.deltas)})
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class DoneProvider(LLMProvider):
    """Completes immediately with one fixed visible delta."""

    def __init__(self, content):
        self.content = content
        self.cancelled = False
        self.messages = []

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        try:
            yield ProviderStreamEvent(type="text_delta", delta=self.content)
            yield ProviderStreamEvent(type="completed", result={"content": self.content})
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("query fallback was not expected")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class RecordingModerator(DoneProvider):
    pass


async def wait_for(predicate, timeout=1):
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("condition was not reached")
        await asyncio.sleep(0)


async def collect_workers(worker_a, worker_b, **kwargs):
    providers = {"a": worker_a, "b": worker_b}
    return [
        event
        async for event in multiplex_workers(
            "timeout prompt", "a", "b", providers.__getitem__, **kwargs
        )
    ]


def test_module_timeout_constants_are_explicit():
    assert SEAT_TIMEOUT_SECONDS == 300
    assert RUN_TIMEOUT_SECONDS == 600


async def test_seat_timeout_emits_seat_failed_with_reason_timeout():
    hung = HangingProvider()
    done = DoneProvider("still fine")
    events = await collect_workers(hung, done, seat_timeout=0.05)

    failed = [event for event in events if event["type"] == "seat_failed"]
    assert len(failed) == 1
    assert failed[0]["seat_id"] == "worker_a"
    assert failed[0]["reason"] == "timeout"
    assert "timed out" in failed[0]["error"]
    assert hung.cancelled
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"


async def test_seat_timeout_keeps_prior_deltas_and_peer_survives():
    hung = DeltasThenHangProvider(("partial ", "alpha"))
    done = DoneProvider("beta")
    events = await collect_workers(hung, done, seat_timeout=0.1)

    deltas_a = [
        event["delta"]
        for event in events
        if event.get("seat_id") == "worker_a" and event["type"] == "seat_delta"
    ]
    assert deltas_a == ["partial ", "alpha"]
    fail_a = next(
        event for event in events
        if event.get("seat_id") == "worker_a" and event["type"] == "seat_failed"
    )
    assert fail_a["reason"] == "timeout"
    assert any(
        event["type"] == "seat_completed" and event["seat_id"] == "worker_b"
        for event in events
    )
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"


async def test_seat_timeout_defaults_to_live_module_constant(monkeypatch):
    monkeypatch.setattr("backend.modelmix.timeouts.SEAT_TIMEOUT_SECONDS", 0.05)
    hung = HangingProvider()
    done = DoneProvider("ok")
    events = await collect_workers(hung, done)

    failed = [event for event in events if event["type"] == "seat_failed"]
    assert len(failed) == 1
    assert failed[0]["reason"] == "timeout"


async def test_timed_out_seat_reaches_moderator_with_survivor_and_persists_partial_failure(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store, seat_timeout=0.1)
    hung = DeltasThenHangProvider(("partial alpha",))
    done = DoneProvider("beta")
    moderator = RecordingModerator("synthesis")
    providers = {"a": hung, "b": done, "m": moderator}
    run = await registry.start(
        "original prompt", "a", "b", providers.__getitem__, "m", "timeout-session"
    )
    await run.task

    events = await run.events_after(0)
    assert any(
        event["type"] == "seat_failed"
        and event["seat_id"] == "worker_a"
        and event["reason"] == "timeout"
        for event in events
    )
    seat_a_deltas = "".join(
        event["delta"]
        for event in events
        if event.get("seat_id") == "worker_a" and event["type"] == "seat_delta"
    )
    assert seat_a_deltas == "partial alpha"
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"
    assert run.status == "partial"

    handoff = moderator.messages[0][1]["content"]
    assert "Worker A status:\nUnavailable because the worker failed." in handoff
    assert "partial alpha" not in handoff
    assert "Worker B visible output:\nbeta" in handoff

    document = await store.load_session("timeout-session")
    snapshot = document["session"]["runs"][0]
    assert snapshot["status"] == "partial"
    assert snapshot["latest_seq"] == len(snapshot["events"])
    messages = {
        message["seat"]: message
        for message in document["session"]["messages"]
        if message["run_id"] == run.run_id
    }
    assert messages["worker_a"]["content"] == "partial alpha"
    assert messages["worker_a"]["status"] == "failed"
    assert "timed out" in messages["worker_a"]["error"]
    assert messages["worker_b"]["content"] == "beta"
    assert messages["worker_b"]["status"] == "completed"


async def test_run_timeout_cancels_seats_and_emits_run_failed_with_reason_timeout(tmp_path):
    hung_a = HangingProvider()
    hung_b = HangingProvider()
    providers = {"a": hung_a, "b": hung_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=0.5,
    )
    run = await registry.start("timeout run", "a", "b", providers.__getitem__)
    await run.task

    events = await run.events_after(0)
    assert events[-1]["type"] == "run_failed"
    assert events[-1]["reason"] == "timeout"
    assert "timed out" in events[-1]["error"]
    assert not any(event["type"] == "run_completed" for event in events)
    assert not any(event["type"] == "seat_cancelled" for event in events)
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert {event["seat_id"] for event in events if event["type"] == "seat_started"} == {
        "worker_a", "worker_b"
    }
    assert run.status == "failed"
    assert hung_a.cancelled and hung_b.cancelled


async def test_run_timeout_defaults_to_live_module_constant(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.modelmix.timeouts.RUN_TIMEOUT_SECONDS", 0.1)
    hung_a = HangingProvider()
    hung_b = HangingProvider()
    providers = {"a": hung_a, "b": hung_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
    )
    run = await registry.start("default run timeout", "a", "b", providers.__getitem__)
    await run.task

    events = await run.events_after(0)
    assert events[-1]["type"] == "run_failed"
    assert events[-1]["reason"] == "timeout"
    assert run.status == "failed"


async def test_no_events_append_after_run_reaches_terminal(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store, seat_timeout=0.1)
    hung = DeltasThenHangProvider(("tail partial",))
    done = DoneProvider("beta")
    moderator = RecordingModerator("synthesis")
    providers = {"a": hung, "b": done, "m": moderator}
    run = await registry.start(
        "later writes", "a", "b", providers.__getitem__, "m", "late-session"
    )
    await run.task

    before = await run.events_after(0)
    assert before[-1]["type"] == "run_completed"
    before_persisted = await store.load_session("late-session")

    await asyncio.sleep(0.3)

    assert await run.events_after(0) == before
    after_persisted = await store.load_session("late-session")
    assert after_persisted == before_persisted
    snapshot = after_persisted["session"]["runs"][0]
    assert snapshot["latest_seq"] == len(snapshot["events"])


async def test_explicit_cancel_is_run_cancelled_and_never_labeled_timeout(tmp_path):
    gate = asyncio.Event()
    hung_a = HangingProvider(gate)
    hung_b = HangingProvider(gate)
    providers = {"a": hung_a, "b": hung_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start("cancel me", "a", "b", providers.__getitem__)
    await wait_for(lambda: len(run._events) >= 3)

    await registry.cancel(run.run_id)
    await run.task

    events = await run.events_after(0)
    assert events[-1]["type"] == "run_cancelled"
    assert events[-1].get("reason") is None
    assert "timeout" not in json.dumps(events)
    assert not any(event["type"] == "run_failed" for event in events)
    assert run.status == "cancelled"


async def test_normal_run_emits_unmodified_canonical_sequence(tmp_path):
    done_a = DoneProvider("alpha")
    done_b = DoneProvider("beta")
    moderator = RecordingModerator("synthesis")
    providers = {"a": done_a, "b": done_b, "m": moderator}
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    run = await registry.start("normal", "a", "b", providers.__getitem__, "m")
    await run.task

    events = await run.events_after(0)
    canonical_types = {
        "run_started", "seat_started", "seat_delta", "seat_completed",
        "moderator_started", "moderator_delta", "moderator_completed", "run_completed",
    }
    types = [event["type"] for event in events]
    assert len(events) == 11
    assert types[0] == "run_started" and types[-1] == "run_completed"
    assert events[-1]["status"] == "completed"
    assert set(types) <= canonical_types
    assert [event["seq"] for event in events] == list(range(1, 12))
    assert all("reason" not in event for event in events)
    assert run.status == "completed"


async def test_moderator_timeout_emits_moderator_failed_with_reason_timeout():
    hung = HangingProvider()
    events = []

    async def create_event(event_type, **payload):
        event = {"type": event_type, **payload}
        events.append(event)
        return event

    ok = await run_moderator(
        "m",
        hung,
        ModeratorInput(messages=[{"role": "user", "content": "hi"}], truncation={}),
        create_event,
        seat_timeout=0.05,
    )

    assert ok is False
    failed = [event for event in events if event["type"] == "moderator_failed"]
    assert len(failed) == 1
    assert failed[0]["reason"] == "timeout"
    assert "timed out" in failed[0]["error"]
    assert hung.cancelled