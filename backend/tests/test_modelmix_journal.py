"""Event journal, replay, retention, and run-lifecycle coverage."""

import asyncio
import time

import httpx
import pytest
from fastapi import FastAPI

from backend.modelmix.events import EventSequencer
from backend.modelmix.journal import ReplayUnavailableError, RunEventJournal
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.providers.base import LLMProvider, ProviderStreamEvent


class ControlledProvider(LLMProvider):
    def __init__(self, gate=None, delta="answer"):
        self.gate = gate
        self.delta = delta
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
            yield ProviderStreamEvent(type="text_delta", delta=self.delta)
            yield ProviderStreamEvent(type="completed", result={"content": self.delta})
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("query fallback was not expected")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


async def wait_for(predicate, timeout=1):
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("condition was not reached")
        await asyncio.sleep(0)


async def test_append_and_cursor_replay_preserve_original_events():
    journal = RunEventJournal("run-1")
    first = await journal.append("run_started")
    second = await journal.append("seat_delta", seat_id="worker_a", delta="hello")
    third = await journal.append("seat_completed", seat_id="worker_a")

    replay = await journal.events_after(1)
    assert replay == [second, third]
    assert replay[0] is second
    assert [event["seq"] for event in [first, second, third]] == [1, 2, 3]
    assert all(event["run_id"] == "run-1" for event in replay)


async def test_active_tail_replays_then_receives_live_event():
    journal = RunEventJournal("active")
    await journal.mark_status("active")
    missed = await journal.append("seat_delta", seat_id="worker_a", delta="missed")
    subscriber = journal.tail(0)

    assert await anext(subscriber) is missed
    pending = asyncio.create_task(anext(subscriber))
    await asyncio.sleep(0)
    live = await journal.append("seat_delta", seat_id="worker_b", delta="live")
    assert await pending is live
    await subscriber.aclose()


async def test_terminal_tail_replays_and_closes():
    journal = RunEventJournal("done")
    event = await journal.append("run_completed", status="completed")
    await journal.mark_status("completed")
    assert [item async for item in journal.tail(0)] == [event]


async def test_per_run_retention_is_bounded_and_gap_is_explicit():
    journal = RunEventJournal("bounded", max_events=2)
    await journal.append("one")
    second = await journal.append("two")
    third = await journal.append("three")
    assert await journal.events_after(1) == [second, third]
    with pytest.raises(ReplayUnavailableError, match="no longer retained"):
        await journal.events_after(0)


async def test_concurrent_appends_have_unique_monotonic_sequences():
    journal = RunEventJournal("concurrent", max_events=200)
    events = await asyncio.gather(
        *(journal.append("seat_delta", seat_id="worker_a", delta=str(index)) for index in range(100))
    )
    assert [event["seq"] for event in events] == list(range(1, 101))
    assert len({event["seq"] for event in events}) == 100


async def test_events_carry_float_non_decreasing_wall_clock_timestamps(monkeypatch):
    clock = iter([1000.0, 1000.25, 1000.5, 1000.75, 1001.0])
    monkeypatch.setattr("backend.modelmix.journal.time.time", lambda: next(clock))
    journal = RunEventJournal("ts-run")
    events = [await journal.append(event_type) for event_type in [
        "run_started",
        "seat_started",
        "seat_delta",
        "seat_completed",
        "run_completed",
    ]]
    assert all(isinstance(event["ts"], float) for event in events)
    assert [event["ts"] for event in events] == [1000.0, 1000.25, 1000.5, 1000.75, 1001.0]


def test_event_sequencer_create_carries_wall_clock_timestamp():
    sequencer = EventSequencer("seq-run")
    event = sequencer.create("seat_delta", seat_id="worker_a", delta="x")
    assert event["ts"] is not None
    assert isinstance(event["ts"], float)
    assert event["seq"] == 1
    assert event["run_id"] == "seq-run"


async def test_registry_replay_survives_subscriber_disconnect_and_completes(tmp_path):
    gate = asyncio.Event()
    providers = {"a": ControlledProvider(gate, "A"), "b": ControlledProvider(gate, "B")}
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    run = await registry.start("same prompt", "a", "b", providers.__getitem__)
    await wait_for(lambda: len(run._events) >= 3)

    subscriber = run.tail(0)
    first = await anext(subscriber)
    await subscriber.aclose()
    assert first["type"] == "run_started"
    assert run.status == "active"
    assert run.task and not run.task.done()

    gate.set()
    await run.task
    replay = await run.events_after(first["seq"])
    assert replay[-1]["type"] == "run_completed"
    assert run.status == "completed"
    assert providers["a"].messages == providers["b"].messages == [
        [{"role": "user", "content": "same prompt"}]
    ]


async def test_explicit_cancel_is_idempotent_and_replayable(tmp_path):
    gate = asyncio.Event()
    providers = {"a": ControlledProvider(gate), "b": ControlledProvider(gate)}
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    run = await registry.start("prompt", "a", "b", providers.__getitem__)
    await wait_for(lambda: len(run._events) >= 3)

    assert await registry.cancel(run.run_id) is run
    assert await registry.cancel(run.run_id) is run
    await run.task
    replay = await run.events_after(0)
    types = [event["type"] for event in replay]
    assert types.count("run_cancel_requested") == 1
    assert types.count("run_cancelled") == 1
    assert "run_completed" not in types
    assert run.status == "cancelled"
    assert all(provider.cancelled for provider in providers.values())


async def test_completed_run_retention_count_and_ttl_are_bounded(tmp_path):
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        max_terminal_runs=1,
        terminal_ttl_seconds=60,
    )
    now = time.monotonic()
    first = RunEventJournal("first", status="completed", terminal_at=now - 2)
    second = RunEventJournal("second", status="completed", terminal_at=now - 1)
    registry._runs = {first.run_id: first, second.run_id: second}
    assert await registry.get("first") is None
    assert await registry.get("second") is second

    expiring = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        max_terminal_runs=2,
        terminal_ttl_seconds=0,
    )
    expired = RunEventJournal("expired", status="completed", terminal_at=1)
    expiring._runs[expired.run_id] = expired
    assert await expiring.get("expired") is None


async def test_replay_route_supports_cursor_last_event_id_and_clear_errors(monkeypatch, tmp_path):
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    run = RunEventJournal("route-run", max_events=2)
    await run.append("discarded")
    second = await run.append("seat_delta", seat_id="worker_a", delta="two")
    third = await run.append("run_completed", status="completed")
    await run.mark_status("completed")
    registry._runs[run.run_id] = run
    monkeypatch.setattr("backend.modelmix.routes.run_registry", registry)
    app = FastAPI()
    app.include_router(router)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/modelmix/runs/route-run/events", headers={"Last-Event-ID": "1"}
        )
        explicit = await client.get(
            "/api/modelmix/runs/route-run/events?after_seq=2",
            headers={"Last-Event-ID": "0"},
        )
        gap = await client.get("/api/modelmix/runs/route-run/events?after_seq=0")
        missing = await client.get("/api/modelmix/runs/missing/events")

    assert response.status_code == 200
    assert f'id: {second["seq"]}' in response.text
    assert f'id: {third["seq"]}' in response.text
    assert f'id: {second["seq"]}' not in explicit.text
    assert f'id: {third["seq"]}' in explicit.text
    assert gap.status_code == 409
    assert "no longer retained" in gap.json()["detail"]
    assert missing.status_code == 404
    assert missing.json()["detail"] == "ModelMix run not found or expired"
