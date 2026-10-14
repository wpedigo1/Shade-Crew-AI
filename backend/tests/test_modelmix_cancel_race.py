"""Mission 023 cancellation-race coverage.

Deterministic cancellation tests that directly construct the failure
condition -- a fake provider that refuses to finish after cancellation for
longer than the cancel grace period -- instead of racing asyncio's internal
timing. The grace-path tests assert a structural proof that the stalled task
was abandoned mid-stream (``stream_finished`` unset at the moment the run is
terminal), which is timing-independent.
"""

import asyncio
import json

from backend.modelmix.registry import RunRegistry
from backend.modelmix.timeouts import CANCEL_GRACE_SECONDS, await_cancellation_grace
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.providers.base import LLMProvider, ProviderStreamEvent


class StallOnCancelProvider(LLMProvider):
    """Emits one delta, then absorbs cancellation and holds past the grace.

    The generator advances past its yield as soon as the ordering consumer
    has the delta, so cancellation deterministically lands either at the
    cancellation-absorbing hold or at a suspension the provider never leaves
    -- both keep the seat/moderator task pending well beyond the grace
    period. ``release`` lets the test drain the stray afterwards.
    """

    def __init__(self):
        self.cancelled = False
        self.cancelled_seen = False
        self.release = asyncio.Event()
        self.stream_finished = asyncio.Event()

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        try:
            yield ProviderStreamEvent(type="text_delta", delta="stall ")
            while True:
                try:
                    await self.release.wait()
                    break
                except asyncio.CancelledError:
                    self.cancelled_seen = True
                    await self.release.wait()
                    break
            raise asyncio.CancelledError
        finally:
            self.stream_finished.set()

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("query fallback was not expected")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class PromptCancelledProvider(LLMProvider):
    """Streams nothing and reliably finishes cancelling (today's behavior)."""

    def __init__(self):
        self.cancelled = False
        self.stream_finished = asyncio.Event()

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        try:
            await asyncio.sleep(30)
            yield ProviderStreamEvent(type="completed", result={"content": "late"})
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        finally:
            self.stream_finished.set()

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("query fallback was not expected")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class InstantProvider(LLMProvider):
    """Completes immediately with one fixed visible delta."""

    def __init__(self, content):
        self.content = content
        self.cancelled = False

    @property
    def supports_streaming(self):
        return True

    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
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


async def until(predicate, timeout=20):
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("condition was not reached")
        await asyncio.sleep(0.01)


def release_and_drain(*providers):
    for provider in providers:
        provider.release.set()


def assert_terminal_cancel_contract(events, run, *stall_providers):
    assert events[-1]["type"] == "run_cancelled"
    assert events[-1].get("reason") is None
    assert not any(event["type"] == "run_failed" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)
    assert "timeout" not in json.dumps(events)
    assert run.status == "cancelled"
    for provider in stall_providers:
        assert provider.stream_finished.is_set() is False


def test_module_cancel_grace_constant_is_explicit():
    assert CANCEL_GRACE_SECONDS == 5.0


async def test_grace_helper_returns_immediately_when_tasks_finish_or_none():
    fast = asyncio.create_task(asyncio.sleep(0.05))
    await await_cancellation_grace((fast,))
    assert fast.done()
    await await_cancellation_grace(())


async def test_grace_helper_stops_after_grace_for_a_stubborn_task(monkeypatch):
    monkeypatch.setattr("backend.modelmix.timeouts.CANCEL_GRACE_SECONDS", 0.25)
    release = asyncio.Event()
    stubborn = None

    async def stubborn_task():
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            await release.wait()

    stubborn = asyncio.create_task(stubborn_task())
    started = asyncio.get_running_loop().time()
    await await_cancellation_grace((stubborn,))
    elapsed = asyncio.get_running_loop().time() - started
    assert elapsed >= 0.2
    assert stubborn.done() is False
    release.set()
    stubborn.cancel()
    await stubborn
    await asyncio.sleep(0.05)


async def test_one_slow_to_cancel_seat_reaches_run_cancelled_within_grace(tmp_path):
    stall_a = StallOnCancelProvider()
    done_b = InstantProvider("beta")
    providers = {"a": stall_a, "b": done_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start("grace one", "a", "b", providers.__getitem__)
    await until(lambda: any(
        e["type"] == "seat_delta" and e["seat_id"] == "worker_a" for e in run._events
    ))

    started = asyncio.get_running_loop().time()
    await registry.cancel(run.run_id)
    await asyncio.wait_for(run.task, timeout=8.0)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 8.0
    assert elapsed >= 3.0
    events = await run.events_after(0)
    assert_terminal_cancel_contract(events, run, stall_a)
    assert next(
        e for e in events if e["type"] == "run_cancel_requested"
    )["seq"] < events[-1]["seq"]
    release_and_drain(stall_a)
    await stall_a.stream_finished.wait()
    await asyncio.sleep(0.05)


async def test_both_seats_slow_to_cancel_still_terminal_cancelled(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.modelmix.timeouts.CANCEL_GRACE_SECONDS", 0.25)
    stall_a = StallOnCancelProvider()
    stall_b = StallOnCancelProvider()
    providers = {"a": stall_a, "b": stall_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start("grace both", "a", "b", providers.__getitem__)
    await until(lambda: len(run._events) >= 3)

    started = asyncio.get_running_loop().time()
    await registry.cancel(run.run_id)
    await asyncio.wait_for(run.task, timeout=8.0)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 8.0
    events = await run.events_after(0)
    assert_terminal_cancel_contract(events, run, stall_a, stall_b)
    release_and_drain(stall_a, stall_b)
    await stall_a.stream_finished.wait()
    await stall_b.stream_finished.wait()
    await asyncio.sleep(0.05)


async def test_prompt_cancel_regression_is_completely_unchanged(tmp_path):
    hung_a = PromptCancelledProvider()
    hung_b = PromptCancelledProvider()
    providers = {"a": hung_a, "b": hung_b}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start("fast cancel", "a", "b", providers.__getitem__)
    await until(lambda: len(run._events) >= 3)

    started = asyncio.get_running_loop().time()
    await registry.cancel(run.run_id)
    await asyncio.wait_for(run.task, timeout=8.0)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 8.0
    assert elapsed < 3.0
    events = await run.events_after(0)
    assert events[-1]["type"] == "run_cancelled"
    assert events[-1].get("reason") is None
    assert "timeout" not in json.dumps(events)
    assert not any(event["type"] == "run_failed" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)
    cancel_marker = next(
        e for e in events if e["type"] == "run_cancel_requested"
    )
    cancel_seq = cancel_marker["seq"]
    assert all(
        e["seq"] < cancel_seq for e in events if e["type"] == "seat_delta"
    )
    assert not any(
        e["type"] == "seat_delta" and e["seq"] > cancel_seq for e in events
    )
    assert run.status == "cancelled"
    assert hung_a.cancelled and hung_b.cancelled
    assert hung_a.stream_finished.is_set() and hung_b.stream_finished.is_set()


async def test_moderator_slow_to_cancel_reaches_run_cancelled_within_grace(tmp_path):
    workers_a = InstantProvider("alpha")
    workers_b = InstantProvider("beta")
    moderator = StallOnCancelProvider()
    providers = {"a": workers_a, "b": workers_b, "m": moderator}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start(
        "grace moderator", "a", "b", providers.__getitem__, "m"
    )
    await until(lambda: any(e["type"] == "moderator_delta" for e in run._events))

    started = asyncio.get_running_loop().time()
    await registry.cancel(run.run_id)
    await asyncio.wait_for(run.task, timeout=8.0)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 8.0
    assert elapsed >= 3.0
    events = await run.events_after(0)
    assert events[-1]["type"] == "run_cancelled"
    assert events[-1].get("reason") is None
    assert not any(event["type"] == "run_failed" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)
    assert "timeout" not in json.dumps(events)
    assert run.status == "cancelled"
    assert moderator.stream_finished.is_set() is False
    release_and_drain(moderator)
    await moderator.stream_finished.wait()
    await asyncio.sleep(0.05)


async def test_moderator_prompt_cancel_regression(tmp_path):
    workers_a = InstantProvider("alpha")
    workers_b = InstantProvider("beta")
    moderator = PromptCancelledProvider()
    providers = {"a": workers_a, "b": workers_b, "m": moderator}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start(
        "fast moderator cancel", "a", "b", providers.__getitem__, "m"
    )
    await until(lambda: any(e["type"] == "moderator_started" for e in run._events))

    started = asyncio.get_running_loop().time()
    await registry.cancel(run.run_id)
    await asyncio.wait_for(run.task, timeout=8.0)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 8.0
    assert elapsed < 3.0
    events = await run.events_after(0)
    assert events[-1]["type"] == "run_cancelled"
    assert events[-1].get("reason") is None
    assert not any(event["type"] == "run_failed" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)
    assert "timeout" not in json.dumps(events)
    assert run.status == "cancelled"
    assert moderator.cancelled
    assert moderator.stream_finished.is_set()


async def test_cancel_before_run_starts_reaches_terminal_cancelled(tmp_path):
    """Cancelling before _run's first await still yields run_cancelled."""
    providers = {"a": InstantProvider("alpha"), "b": InstantProvider("beta")}
    registry = RunRegistry(
        persistence=AtomicJsonModelMixPersistence(tmp_path),
        seat_timeout=3.0,
        run_timeout=60,
    )
    run = await registry.start("cancel-before-start", "a", "b", providers.__getitem__)
    run.task.cancel()
    done, pending = await asyncio.wait({run.task}, timeout=5.0)
    assert not pending, "run.task did not complete within timeout"
    assert run.status == "cancelled"
    events = await run.events_after(0)
    assert events[-1]["type"] == "run_cancelled"