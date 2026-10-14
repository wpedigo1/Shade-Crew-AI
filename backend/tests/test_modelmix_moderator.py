"""Deterministic tests for the ModelMix Moderator fan-in phase."""

import asyncio

from backend.modelmix.moderator import (
    MAX_VISIBLE_OUTPUT_CHARS,
    MODERATOR_INSTRUCTIONS,
    ModeratorOutputLimits,
    assemble_moderator_input,
    run_moderator,
)
from backend.modelmix.registry import RunRegistry
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.providers.base import LLMProvider, ProviderStreamEvent


class StreamingProvider(LLMProvider):
    def __init__(self, deltas=(), gate=None, failure=None):
        self.deltas = tuple(deltas)
        self.gate = gate
        self.failure = failure
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
            if self.gate:
                await self.gate.wait()
            if self.failure:
                yield ProviderStreamEvent(type="error", error_message=self.failure)
                return
            for delta in self.deltas:
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(
                type="completed",
                result={"content": "".join(self.deltas), "reasoning": "private"},
                finish_reason="stop",
            )
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("streaming provider used query fallback")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class NonStreamingModerator(StreamingProvider):
    @property
    def supports_streaming(self):
        return False

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.started = True
        self.messages.append(messages)
        return {"content": "fallback synthesis", "finish_reason": "stop", "error": False}


class PartialFailureProvider(StreamingProvider):
    async def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.started = True
        self.messages.append(messages)
        yield ProviderStreamEvent(type="text_delta", delta=self.deltas[0])
        yield ProviderStreamEvent(type="error", error_message=self.failure)


async def wait_for(predicate, timeout=1):
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("condition was not reached")
        await asyncio.sleep(0)


async def start_run(worker_a, worker_b, moderator, persistence=None):
    providers = {"a": worker_a, "b": worker_b, "m": moderator}
    registry = RunRegistry() if persistence is None else RunRegistry(persistence=persistence)
    run = await registry.start("original prompt", "a", "b", providers.__getitem__, "m")
    return registry, run


async def test_moderator_waits_for_both_workers_and_receives_visible_isolated_outputs(tmp_path):
    gate_a = asyncio.Event()
    gate_b = asyncio.Event()
    worker_a = StreamingProvider(("visible A",), gate_a)
    worker_b = StreamingProvider(("visible B",), gate_b)
    moderator = StreamingProvider(("final ", "answer"))
    _, run = await start_run(
        worker_a, worker_b, moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )

    await wait_for(lambda: worker_a.started and worker_b.started)
    gate_a.set()
    await wait_for(lambda: any(event["type"] == "seat_completed" for event in run._events))
    assert not moderator.started
    gate_b.set()
    await run.task

    moderator_text = moderator.messages[0][1]["content"]
    assert "original prompt" in moderator_text
    assert "Worker A visible output:\nvisible A" in moderator_text
    assert "Worker B visible output:\nvisible B" in moderator_text
    assert "private" not in moderator_text
    assert worker_a.messages == [[{"role": "user", "content": "original prompt"}]]
    assert worker_b.messages == [[{"role": "user", "content": "original prompt"}]]
    assert "visible B" not in str(worker_a.messages)
    assert "visible A" not in str(worker_b.messages)
    assert "final answer" not in str(worker_a.messages + worker_b.messages)

    events = await run.events_after(0)
    moderator_events = [event for event in events if event["type"].startswith("moderator_")]
    assert [event["type"] for event in moderator_events] == [
        "moderator_started", "moderator_delta", "moderator_delta", "moderator_completed"
    ]
    assert all(event["run_id"] == run.run_id for event in events)
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


def test_moderator_input_places_own_history_before_current_worker_handoff():
    moderator_input = assemble_moderator_input(
        "TURN2_PROMPT_SENTINEL",
        {
            "worker_a": "TURN2_WORKER_A_SENTINEL",
            "worker_b": "TURN2_WORKER_B_SENTINEL",
        },
        {},
        history=[
            {"role": "user", "content": "TURN1_PROMPT_SENTINEL"},
            {"role": "assistant", "content": "TURN1_MODERATOR_SENTINEL"},
        ],
    )

    assert moderator_input.messages[1:3] == [
        {"role": "user", "content": "TURN1_PROMPT_SENTINEL"},
        {"role": "assistant", "content": "TURN1_MODERATOR_SENTINEL"},
    ]
    current_handoff = moderator_input.messages[3]["content"]
    assert "TURN2_PROMPT_SENTINEL" in current_handoff
    assert "TURN2_WORKER_A_SENTINEL" in current_handoff
    assert "TURN2_WORKER_B_SENTINEL" in current_handoff
    assert "TURN1_WORKER_A_SENTINEL" not in str(moderator_input.messages)
    assert "TURN1_WORKER_B_SENTINEL" not in str(moderator_input.messages)


async def test_registry_preserves_seat_history_across_turns_and_model_hot_swap(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store)
    first = {
        "a-v1": StreamingProvider(("TURN1_WORKER_A_SENTINEL",)),
        "b-v1": StreamingProvider(("TURN1_WORKER_B_SENTINEL",)),
        "m-v1": StreamingProvider(("TURN1_MODERATOR_SENTINEL",)),
    }
    run_1 = await registry.start(
        "TURN1_PROMPT_SENTINEL",
        "a-v1",
        "b-v1",
        first.__getitem__,
        "m-v1",
        "shared-session",
    )
    await run_1.task

    second = {
        "a-v2": StreamingProvider(("TURN2_WORKER_A_SENTINEL",)),
        "b-v1": StreamingProvider(("TURN2_WORKER_B_SENTINEL",)),
        "m-v2": StreamingProvider(("TURN2_MODERATOR_SENTINEL",)),
    }
    run_2 = await registry.start(
        "TURN2_PROMPT_SENTINEL",
        "a-v2",
        "b-v1",
        second.__getitem__,
        "m-v2",
        "shared-session",
    )
    await run_2.task

    worker_a_messages = second["a-v2"].messages[0]
    worker_b_messages = second["b-v1"].messages[0]
    moderator_messages = second["m-v2"].messages[0]
    assert worker_a_messages == [
        {"role": "user", "content": "TURN1_PROMPT_SENTINEL"},
        {"role": "assistant", "content": "TURN1_WORKER_A_SENTINEL"},
        {"role": "user", "content": "TURN2_PROMPT_SENTINEL"},
    ]
    assert worker_b_messages == [
        {"role": "user", "content": "TURN1_PROMPT_SENTINEL"},
        {"role": "assistant", "content": "TURN1_WORKER_B_SENTINEL"},
        {"role": "user", "content": "TURN2_PROMPT_SENTINEL"},
    ]
    assert "TURN1_WORKER_B_SENTINEL" not in str(worker_a_messages)
    assert "TURN1_WORKER_A_SENTINEL" not in str(worker_b_messages)
    assert "TURN1_MODERATOR_SENTINEL" not in str(worker_a_messages + worker_b_messages)
    assert moderator_messages[1:3] == [
        {"role": "user", "content": "TURN1_PROMPT_SENTINEL"},
        {"role": "assistant", "content": "TURN1_MODERATOR_SENTINEL"},
    ]
    assert "TURN1_WORKER_A_SENTINEL" not in str(moderator_messages)
    assert "TURN1_WORKER_B_SENTINEL" not in str(moderator_messages)
    assert "TURN2_WORKER_A_SENTINEL" in moderator_messages[-1]["content"]
    assert "TURN2_WORKER_B_SENTINEL" in moderator_messages[-1]["content"]


async def test_failed_seat_partial_history_is_reused_and_empty_failure_is_skipped(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store)
    first = {
        "a": PartialFailureProvider(("TURN1_A_PARTIAL_SENTINEL",), failure="A failed"),
        "b": StreamingProvider(failure="B failed empty"),
    }
    run_1 = await registry.start(
        "TURN1_FAILURE_PROMPT_SENTINEL",
        "a",
        "b",
        first.__getitem__,
        session_id="failure-session",
    )
    await run_1.task

    second = {
        "a-next": StreamingProvider(("TURN2_A_SENTINEL",)),
        "b-next": StreamingProvider(("TURN2_B_SENTINEL",)),
    }
    run_2 = await registry.start(
        "TURN2_AFTER_FAILURE_SENTINEL",
        "a-next",
        "b-next",
        second.__getitem__,
        session_id="failure-session",
    )
    await run_2.task

    assert second["a-next"].messages[0] == [
        {"role": "user", "content": "TURN1_FAILURE_PROMPT_SENTINEL"},
        {"role": "assistant", "content": "TURN1_A_PARTIAL_SENTINEL"},
        {"role": "user", "content": "TURN2_AFTER_FAILURE_SENTINEL"},
    ]
    assert second["b-next"].messages[0] == [
        {"role": "user", "content": "TURN2_AFTER_FAILURE_SENTINEL"},
    ]
    assert run_2.status == "completed"


async def test_one_worker_failure_allows_honest_partial_moderation(tmp_path):
    worker_a = StreamingProvider(failure="worker A failed")
    worker_b = StreamingProvider(("usable B",))
    moderator = StreamingProvider(("synthesis",))
    _, run = await start_run(
        worker_a, worker_b, moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await run.task

    handoff = moderator.messages[0][1]["content"]
    assert "Worker A status:\nUnavailable because the worker failed." in handoff
    assert "Worker B visible output:\nusable B" in handoff
    events = await run.events_after(0)
    assert any(event["type"] == "seat_failed" and event["seat_id"] == "worker_a" for event in events)
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"
    assert run.status == "partial"


async def test_both_workers_failing_prevents_moderator_synthesis(tmp_path):
    moderator = StreamingProvider(("must not run",))
    _, run = await start_run(
        StreamingProvider(failure="A failed"),
        StreamingProvider(failure="B failed"),
        moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await run.task
    events = await run.events_after(0)
    assert not moderator.started
    assert any(event["type"] == "moderator_failed" and event["reason"] == "insufficient_input" for event in events)
    assert events[-1]["type"] == "run_failed"
    assert not any(event["type"] == "run_completed" for event in events)
    assert run.status == "failed"


async def test_moderator_failure_preserves_worker_output_and_fails_run(tmp_path):
    moderator = StreamingProvider(failure="moderator unavailable")
    _, run = await start_run(
        StreamingProvider(("kept A",)), StreamingProvider(("kept B",)), moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await run.task
    events = await run.events_after(0)
    assert "".join(
        event["delta"] for event in events
        if event["type"] == "seat_delta" and event["seat_id"] == "worker_a"
    ) == "kept A"
    assert any(event["type"] == "moderator_failed" for event in events)
    assert events[-1]["type"] == "run_failed"
    assert not any(event["type"] == "run_completed" for event in events)


async def test_non_streaming_moderator_fallback_is_replayable_once(tmp_path):
    moderator = NonStreamingModerator()
    _, run = await start_run(
        StreamingProvider(("A",)), StreamingProvider(("B",)), moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await run.task
    events = await run.events_after(0)
    delta = next(event for event in events if event["type"] == "moderator_delta")
    replay = await run.events_after(delta["seq"] - 1)
    assert replay[0] is delta
    assert delta["delta"] == "fallback synthesis"
    assert sum(event["type"] == "moderator_delta" for event in events) == 1


async def test_cancel_before_moderator_prevents_start_and_is_replayable(tmp_path):
    gate = asyncio.Event()
    worker_a = StreamingProvider(("A",), gate)
    worker_b = StreamingProvider(("B",), gate)
    moderator = StreamingProvider(("final",))
    registry, run = await start_run(
        worker_a, worker_b, moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await wait_for(lambda: worker_a.started and worker_b.started)
    await registry.cancel(run.run_id)
    await run.task
    events = await run.events_after(0)
    assert not moderator.started
    assert run.status == "cancelled"
    assert any(event["type"] == "run_cancelled" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)


async def test_cancel_during_moderator_cancels_it_without_success(tmp_path):
    moderator_gate = asyncio.Event()
    moderator = StreamingProvider(("late",), moderator_gate)
    registry, run = await start_run(
        StreamingProvider(("A",)), StreamingProvider(("B",)), moderator,
        persistence=AtomicJsonModelMixPersistence(tmp_path),
    )
    await wait_for(lambda: moderator.started)
    await registry.cancel(run.run_id)
    await run.task
    events = await run.events_after(0)
    assert moderator.cancelled
    assert run.status == "cancelled"
    assert not any(event["type"] in {"moderator_completed", "run_completed"} for event in events)


async def test_input_truncation_and_unsupported_hard_cap_are_explicit():
    long_text = "x" * (MAX_VISIBLE_OUTPUT_CHARS + 10)
    moderator_input = assemble_moderator_input("prompt", {"worker_a": long_text}, {"worker_b": "failed"})
    assert moderator_input.truncation == {"worker_a": True}
    assert "truncated deterministically" in moderator_input.messages[1]["content"]
    handoff_output = moderator_input.messages[1]["content"].split("Worker A visible output:\n", 1)[1]
    handoff_output = handoff_output.split("\n\nWorker B status:", 1)[0]
    assert len(handoff_output) == MAX_VISIBLE_OUTPUT_CHARS

    events = []

    async def create_event(event_type, **payload):
        event = {"type": event_type, **payload}
        events.append(event)
        return event

    try:
        await run_moderator(
            "m",
            NonStreamingModerator(),
            moderator_input,
            create_event,
            ModeratorOutputLimits(hard_cap_tokens=10),
        )
    except ValueError as exc:
        assert "not supported" in str(exc)
    else:
        raise AssertionError("unsupported hard cap must fail clearly")
    assert events == []


class RecordingProvider(LLMProvider):
    """Records each provider call's messages and exact kwargs."""

    def __init__(self, *, streaming=True):
        self.calls = []
        self._streaming = streaming

    @property
    def supports_streaming(self):
        return self._streaming

    async def stream_query(self, model_id, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        yield ProviderStreamEvent(type="text_delta", delta="out")
        yield ProviderStreamEvent(
            type="completed", result={"content": "out"}, finish_reason="stop"
        )

    async def query(self, model_id, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"content": "out", "finish_reason": "stop", "error": False}

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


def test_moderator_guidance_is_appended_after_full_unmodified_instructions():
    guidance = "Emphasize numeric claims and flag missing citations."
    moderator_input = assemble_moderator_input(
        "prompt",
        {"worker_a": "A output", "worker_b": "B output"},
        {},
        moderator_guidance=guidance,
    )
    system = moderator_input.messages[0]["content"]
    assert MODERATOR_INSTRUCTIONS in system
    assert f"Additional guidance from the user:\n{guidance}" in system
    assert system.index(MODERATOR_INSTRUCTIONS) < system.index(
        "Additional guidance from the user:"
    )


def test_omitted_moderator_guidance_keeps_system_message_byte_identical():
    moderator_input = assemble_moderator_input(
        "prompt",
        {"worker_a": "A output", "worker_b": "B output"},
        {},
    )
    assert moderator_input.messages[0]["content"] == MODERATOR_INSTRUCTIONS


async def test_moderator_guidance_reaches_the_real_system_message(tmp_path):
    guidance = "Favor concrete next steps."
    providers = {
        "a": RecordingProvider(streaming=True),
        "b": RecordingProvider(streaming=True),
        "m": RecordingProvider(streaming=True),
    }
    registry = RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))
    run = await registry.start(
        "original prompt", "a", "b", providers.__getitem__, "m",
        moderator_guidance=guidance,
    )
    await run.task
    assert run.status == "completed"
    moderator_calls = providers["m"].calls
    assert moderator_calls, "moderator provider must have been called"
    for call in moderator_calls:
        system = call["messages"][0]["content"]
        assert system.startswith(MODERATOR_INSTRUCTIONS)
        assert f"Additional guidance from the user:\n{guidance}" in system


async def test_moderator_temperature_reaches_provider_exactly_when_provided(tmp_path):
    for streaming in (True, False):
        store = AtomicJsonModelMixPersistence(tmp_path / f"temp-{streaming}")
        providers = {
            "a": RecordingProvider(streaming=True),
            "b": RecordingProvider(streaming=True),
            "m": RecordingProvider(streaming=streaming),
        }
        registry = RunRegistry(persistence=store)
        run = await registry.start(
            "original prompt", "a", "b", providers.__getitem__, "m",
            temperature=1.25,
        )
        await run.task
        assert run.status == "completed"
        assert providers["m"].calls, "moderator provider must have been called"
        assert all(call.get("temperature") == 1.25 for call in providers["m"].calls)
        assert all(call.get("temperature") == 1.25 for call in providers["a"].calls)
        assert all(call.get("temperature") == 1.25 for call in providers["b"].calls)


async def test_omitted_temperature_never_reaches_any_provider(tmp_path):
    for streaming in (True, False):
        store = AtomicJsonModelMixPersistence(tmp_path / f"no-temp-{streaming}")
        providers = {
            "a": RecordingProvider(streaming=True),
            "b": RecordingProvider(streaming=True),
            "m": RecordingProvider(streaming=streaming),
        }
        registry = RunRegistry(persistence=store)
        run = await registry.start(
            "original prompt", "a", "b", providers.__getitem__, "m",
        )
        await run.task
        assert run.status == "completed"
        for provider in providers.values():
            assert provider.calls, "provider must have been called"
            assert all("temperature" not in call for call in provider.calls)
