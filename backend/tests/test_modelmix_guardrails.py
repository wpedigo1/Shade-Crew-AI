"""Mission 019 cumulative output guardrail coverage (backend enforcement).

Mission 020 adds per-request configurability of the two thresholds; the
route/registry-level tests below cover that contract.
"""

import asyncio
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modelmix import guardrails
from backend.modelmix.moderator import ModeratorInput, run_moderator
from backend.modelmix.orchestrator import multiplex_workers
from backend.modelmix.persistence import AtomicJsonModelMixPersistence
from backend.modelmix.registry import RunRegistry
from backend.modelmix.routes import router
from backend.providers.base import LLMProvider, ProviderStreamEvent


def set_thresholds(monkeypatch, *, warning=40, cap=80):
    monkeypatch.setattr(
        "backend.modelmix.guardrails.WARNING_OUTPUT_THRESHOLD_CHARS", warning
    )
    monkeypatch.setattr("backend.modelmix.guardrails.HARD_OUTPUT_CAP_CHARS", cap)


class DeltasProvider(LLMProvider):
    def __init__(self, deltas, *, finish_reason="stop", gate=None, usage=None):
        self.deltas = tuple(deltas)
        self.finish_reason = finish_reason
        self.gate = gate
        self.usage = usage
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
            for delta in self.deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(
                type="completed",
                result={"content": "".join(self.deltas)},
                finish_reason=self.finish_reason,
                usage=self.usage,
            )
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("streaming fake must not use query fallback")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class BlockingProvider(DeltasProvider):
    def __init__(self, gate):
        super().__init__((), gate=gate)


class QueryProvider(LLMProvider):
    def __init__(self, content, *, usage=None):
        self.content = content
        self.usage = usage
        self.messages = []

    @property
    def supports_streaming(self):
        return False

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        return {"content": self.content, "usage": self.usage, "error": False}

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


class FakeStream:
    """Async provider stream recording aclose calls and optionally raising on close."""

    def __init__(self, deltas, *, finish_reason="stop", close_error=None):
        self.deltas = tuple(deltas)
        self.finish_reason = finish_reason
        self.close_error = close_error
        self.close_calls = 0
        self.closed = False
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i < len(self.deltas):
            event = ProviderStreamEvent(type="text_delta", delta=self.deltas[self._i])
            self._i += 1
            return event
        if self._i == len(self.deltas):
            self._i += 1
            return ProviderStreamEvent(
                type="completed",
                result={"content": "".join(self.deltas)},
                finish_reason=self.finish_reason,
            )
        raise StopAsyncIteration

    async def aclose(self):
        self.close_calls += 1
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class BareStream:
    """Async provider stream with no `aclose` attribute at all."""

    def __init__(self, deltas):
        self.deltas = tuple(deltas)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i < len(self.deltas):
            event = ProviderStreamEvent(type="text_delta", delta=self.deltas[self._i])
            self._i += 1
            return event
        if self._i == len(self.deltas):
            self._i += 1
            return ProviderStreamEvent(
                type="completed",
                result={"content": "".join(self.deltas)},
                finish_reason="stop",
            )
        raise StopAsyncIteration


class FakeStreamProvider(LLMProvider):
    """Streaming provider whose stream_query returns an injected stream object."""

    def __init__(self, stream):
        self.stream = stream
        self.messages = []

    @property
    def supports_streaming(self):
        return True

    def stream_query(self, model_id, messages, timeout=120.0, temperature=0.7):
        self.messages.append(messages)
        return self.stream

    async def query(self, model_id, messages, timeout=120.0, temperature=0.7):
        raise AssertionError("FakeStreamProvider is streaming-only")

    async def get_models(self):
        return []

    async def validate_key(self, api_key):
        return {"success": True}


async def collect(provider_a, provider_b, **kwargs):
    providers = {"model-a": provider_a, "model-b": provider_b}
    return [
        event
        async for event in multiplex_workers(
            "guardrail prompt", "model-a", "model-b", providers.__getitem__, **kwargs
        )
    ]


# Criterion 1: crossing the warning threshold emits exactly one warning.
async def test_seat_crossing_warning_threshold_emits_exactly_one_warning(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=100_000)
    events = await collect(
        DeltasProvider(("a" * 20, "b" * 20, "c" * 20)),
        DeltasProvider(("ok",)),
    )

    warnings = [event for event in events if event["type"] == "seat_output_warning"]
    assert len(warnings) == 1
    assert warnings[0]["seat_id"] == "worker_a"
    assert warnings[0]["chars"] == 40
    assert warnings[0]["threshold"] == 40
    assert warnings[0]["seq"] < next(
        event["seq"] for event in events if event["type"] == "seat_completed"
    )
    completed_a = next(
        event for event in events
        if event["type"] == "seat_completed" and event["seat_id"] == "worker_a"
    )
    assert completed_a["finish_reason"] == "stop"


# Criterion 2: never crossing the warning threshold emits no warning.
async def test_seat_below_warning_threshold_emits_no_warning(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=100_000)
    events = await collect(
        DeltasProvider(("short",)),
        DeltasProvider(("ok",)),
    )
    assert not any(event["type"] == "seat_output_warning" for event in events)


# Criterion 3: exceeding the hard cap truncates output to exactly the cap length.
async def test_hard_cap_truncates_stream_to_exact_cap_length(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        DeltasProvider(("a" * 60, "b" * 60)),
        DeltasProvider(("ok",)),
    )

    deltas_a = [
        event["delta"]
        for event in events
        if event.get("seat_id") == "worker_a" and event["type"] == "seat_delta"
    ]
    joined = "".join(deltas_a)
    assert len(joined) == 80
    assert joined == "a" * 60 + "b" * 20


# Criterion 4: the capped seat terminates as seat_completed, not seat_failed.
async def test_capped_seat_terminates_completed_with_output_cap_finish(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        DeltasProvider(("a" * 60, "b" * 60)),
        DeltasProvider(("ok",)),
    )

    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["type"] == "seat_completed"
    assert not any(event["type"] == "seat_failed" for event in seat_a)
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


# Criterion 5: a seat under both thresholds behaves unchanged.
async def test_seat_under_both_thresholds_behaves_unchanged(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        DeltasProvider(("hello ", "world")),
        DeltasProvider(("ok",)),
    )

    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert [event["type"] for event in seat_a] == [
        "seat_started", "seat_delta", "seat_delta", "seat_completed",
    ]
    assert "".join(event["delta"] for event in seat_a if event["type"] == "seat_delta") == "hello world"
    assert seat_a[-1]["finish_reason"] == "stop"
    assert not any(event["type"] == "seat_output_warning" for event in events)
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


# Criterion 7: crossing both thresholds yields both events, cap terminal, in order.
async def test_seat_crosses_warning_then_cap_in_order_with_cap_terminal(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        DeltasProvider(("a" * 30, "b" * 30, "c" * 30)),
        DeltasProvider(("ok",)),
    )

    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert [event["type"] for event in seat_a] == [
        "seat_started",
        "seat_delta",
        "seat_delta",
        "seat_output_warning",
        "seat_delta",
        "seat_completed",
    ]
    joined = "".join(event["delta"] for event in seat_a if event["type"] == "seat_delta")
    assert len(joined) == 80
    assert joined == "a" * 30 + "b" * 30 + "c" * 20
    warning = next(event for event in seat_a if event["type"] == "seat_output_warning")
    assert warning["chars"] == 60
    assert warning["threshold"] == 40
    assert len([event for event in events if event["type"] == "seat_output_warning"]) == 1
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"


# Criterion 8: timing out before thresholds emits a timeout failure and no guardrail events.
async def test_timed_out_seat_emits_no_guardrail_events(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    hung = BlockingProvider(asyncio.Event())
    events = await collect(hung, DeltasProvider(("ok",)), seat_timeout=0.05)

    failed = [event for event in events if event["type"] == "seat_failed"]
    assert len(failed) == 1
    assert failed[0]["seat_id"] == "worker_a"
    assert failed[0]["reason"] == "timeout"
    assert not any(event["type"] == "seat_output_warning" for event in events)
    assert not any(event.get("finish_reason") == "modelmix_output_cap" for event in events)
    assert hung.cancelled
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "partial"


# Criterion 9: cancellation before thresholds emits seat_cancelled and no guardrail events.
async def test_cancelled_seat_emits_no_guardrail_events():
    gate = asyncio.Event()
    provider_a = BlockingProvider(gate)
    provider_b = BlockingProvider(gate)
    checks = 0

    async def disconnected():
        nonlocal checks
        checks += 1
        return checks > 1

    events = await collect(provider_a, provider_b, is_disconnected=disconnected)
    assert [event["type"] for event in events].count("seat_cancelled") == 2
    assert not any(event["type"] == "seat_output_warning" for event in events)
    assert not any(event.get("finish_reason") == "modelmix_output_cap" for event in events)
    assert not any(event["type"] == "run_completed" for event in events)


# Criterion 10: non-streaming over-cap truncates exactly; under-cap is untouched; no warning.
async def test_non_streaming_over_cap_truncates_with_output_cap_finish(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        QueryProvider("z" * 200),
        DeltasProvider(("ok",)),
    )

    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    delta = next(event["delta"] for event in seat_a if event["type"] == "seat_delta")
    assert delta == "z" * 80
    assert len(delta) == 80
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"
    assert not any(event["type"] == "seat_output_warning" for event in events)


async def test_non_streaming_under_cap_unaffected_and_no_warning(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    events = await collect(
        QueryProvider("hello", usage={"total_tokens": 7}),
        DeltasProvider(("ok",)),
    )

    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    delta = next(event["delta"] for event in seat_a if event["type"] == "seat_delta")
    assert delta == "hello"
    assert seat_a[-1]["type"] == "seat_completed"
    assert "finish_reason" not in seat_a[-1]
    assert seat_a[-1]["usage"] == {"total_tokens": 7}
    assert not any(event["type"] == "seat_output_warning" for event in events)


# Criterion 6: the Moderator receives the same warning/cap/finish treatment.
async def run_moderator_events(provider, **kwargs):
    events = []

    async def create_event(event_type, **payload):
        event = {"type": event_type, **payload}
        events.append(event)
        return event

    ok = await run_moderator(
        "m",
        provider,
        ModeratorInput(messages=[{"role": "user", "content": "hi"}], truncation={}),
        create_event,
        **kwargs,
    )
    return ok, events


async def test_moderator_crossing_warning_threshold_emits_exactly_one_warning(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=100_000)
    ok, events = await run_moderator_events(
        DeltasProvider(("a" * 20, "b" * 20, "c" * 20))
    )

    warnings = [event for event in events if event["type"] == "moderator_output_warning"]
    assert len(warnings) == 1
    assert warnings[0]["actor"] == "moderator"
    assert warnings[0]["chars"] == 40
    assert warnings[0]["threshold"] == 40
    assert ok is True
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "stop"


async def test_moderator_crosses_warning_then_cap_in_order_with_completed_terminal(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    _, events = await run_moderator_events(
        DeltasProvider(("a" * 30, "b" * 30, "c" * 30))
    )

    assert [event["type"] for event in events if event["actor"] == "moderator"] == [
        "moderator_started",
        "moderator_delta",
        "moderator_delta",
        "moderator_output_warning",
        "moderator_delta",
        "moderator_completed",
    ]
    joined = "".join(
        event["delta"] for event in events if event["type"] == "moderator_delta"
    )
    assert len(joined) == 80
    assert joined == "a" * 30 + "b" * 30 + "c" * 20
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "modelmix_output_cap"


async def test_moderator_under_thresholds_behaves_unchanged(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)
    ok, events = await run_moderator_events(
        DeltasProvider(("final ", "answer"), finish_reason="stop")
    )

    assert ok is True
    assert not any(event["type"] == "moderator_output_warning" for event in events)
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "stop"
    assert "".join(
        event["delta"] for event in events if event["type"] == "moderator_delta"
    ) == "final answer"


# Follow-up (Mission 019): the capped seat closes its provider stream; a stream
# without aclose, or one that errors on close, must not disturb the outcome.
async def test_capped_seat_closes_provider_stream(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)

    stream = FakeStream(("a" * 60, "b" * 60))
    events = await collect(FakeStreamProvider(stream), DeltasProvider(("ok",)))
    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"
    assert stream.close_calls == 1
    assert stream.closed

    stream = BareStream(("a" * 60, "b" * 60))
    events = await collect(FakeStreamProvider(stream), DeltasProvider(("ok",)))
    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"

    stream = FakeStream(("a" * 60, "b" * 60), close_error=RuntimeError("already closed"))
    events = await collect(FakeStreamProvider(stream), DeltasProvider(("ok",)))
    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "modelmix_output_cap"
    assert stream.close_calls == 1


# Follow-up (Mission 019): the capped Moderator closes its provider stream; a
# stream without aclose, or one that errors on close, must not disturb it.
async def test_capped_moderator_closes_provider_stream(monkeypatch):
    set_thresholds(monkeypatch, warning=40, cap=80)

    stream = FakeStream(("a" * 60, "b" * 60))
    ok, events = await run_moderator_events(FakeStreamProvider(stream))
    assert ok is True
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "modelmix_output_cap"
    assert stream.close_calls == 1
    assert stream.closed

    stream = BareStream(("a" * 60, "b" * 60))
    ok, events = await run_moderator_events(FakeStreamProvider(stream))
    assert ok is True
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "modelmix_output_cap"

    stream = FakeStream(("a" * 60, "b" * 60), close_error=RuntimeError("already closed"))
    ok, events = await run_moderator_events(FakeStreamProvider(stream))
    assert ok is True
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "modelmix_output_cap"
    assert stream.close_calls == 1


# ------------------------- Mission 020: per-request configurability --------


def _route_post(monkeypatch, tmp_path, *, body, providers):
    resolved = []

    def resolve(model_id):
        resolved.append(model_id)
        return providers[model_id]

    monkeypatch.setattr("backend.modelmix.routes.get_provider_for_model", resolve)
    monkeypatch.setattr(
        "backend.modelmix.routes.run_registry",
        RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path)),
    )
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post("/api/modelmix/runs/stream", json=body)
    return response, resolved


def _parse_sse(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


# Criterion 1: no guardrail fields behaves exactly as Mission 019 defaults.
def test_route_without_override_fields_enforces_module_defaults(monkeypatch, tmp_path):
    extra = 5_000
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={"prompt": "default", "worker_a_model": "a", "worker_b_model": "b"},
        providers={
            "a": QueryProvider("z" * (guardrails.HARD_OUTPUT_CAP_CHARS + extra)),
            "b": QueryProvider("z" * (guardrails.HARD_OUTPUT_CAP_CHARS + extra)),
        },
    )

    assert response.status_code == 200
    events = _parse_sse(response)
    assert resolved == ["a", "b"]
    for seat in ("worker_a", "worker_b"):
        seat_events = [event for event in events if event.get("seat_id") == seat]
        assert seat_events[-1]["type"] == "seat_completed"
        assert seat_events[-1]["finish_reason"] == "modelmix_output_cap"
        joined = "".join(
            event["delta"] for event in seat_events if event["type"] == "seat_delta"
        )
        assert len(joined) == guardrails.HARD_OUTPUT_CAP_CHARS
    assert not any(event["type"] == "run_failed" for event in events)
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"


# Criterion 2: a smaller hard_cap than the module default caps the seat earlier.
def test_route_smaller_cap_than_default_caps_seat(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "warning_threshold_chars": 100,
            "hard_cap_chars": 120,
        },
        providers={"a": QueryProvider("z" * 5_000), "b": QueryProvider("z" * 5_000)},
    )

    assert response.status_code == 200
    events = _parse_sse(response)
    for seat in ("worker_a", "worker_b"):
        seat_events = [event for event in events if event.get("seat_id") == seat]
        joined = "".join(
            event["delta"] for event in seat_events if event["type"] == "seat_delta"
        )
        assert joined == "z" * 120
        assert seat_events[-1]["finish_reason"] == "modelmix_output_cap"
    assert not any(event["type"] == "run_failed" for event in events)


# Criterion 3: a smaller warning_threshold fires the warning earlier than default.
def test_route_smaller_warning_fires_earlier_than_default(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "warning_threshold_chars": 100,
        },
        providers={
            "a": DeltasProvider(("a" * 10,) * 15),
            "b": DeltasProvider(("ok",)),
        },
    )

    assert response.status_code == 200
    events = _parse_sse(response)
    warnings = [event for event in events if event["type"] == "seat_output_warning"]
    assert len(warnings) == 1
    assert warnings[0]["seat_id"] == "worker_a"
    assert warnings[0]["threshold"] == 100
    assert warnings[0]["chars"] == 100
    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["type"] == "seat_completed"
    assert seat_a[-1]["finish_reason"] == "stop"


# Criterion 4: cap < warning is rejected with 422 before any provider is called.
def test_route_rejects_cap_below_warning_before_provider_call(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "warning_threshold_chars": 500,
            "hard_cap_chars": 300,
        },
        providers={"a": QueryProvider("x"), "b": QueryProvider("x")},
    )

    assert response.status_code == 422
    assert "hard_cap_chars must be >= warning_threshold_chars" in response.text
    assert resolved == []


def test_route_resolves_omitted_warning_to_default_before_cross_check(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "hard_cap_chars": 150,
        },
        providers={"a": QueryProvider("x"), "b": QueryProvider("x")},
    )

    assert response.status_code == 422
    assert "hard_cap_chars must be >= warning_threshold_chars" in response.text
    assert resolved == []


# Criterion 5: values outside the sane bounds are rejected for both fields.
@pytest.mark.parametrize(
    "field,value",
    [
        ("warning_threshold_chars", guardrails.MIN_OUTPUT_CHARS_BOUND - 1),
        ("warning_threshold_chars", guardrails.MAX_OUTPUT_CHARS_BOUND + 1),
        ("hard_cap_chars", guardrails.MIN_OUTPUT_CHARS_BOUND - 1),
        ("hard_cap_chars", guardrails.MAX_OUTPUT_CHARS_BOUND + 1),
    ],
)
def test_route_rejects_out_of_bounds_override_before_provider_call(
    monkeypatch, tmp_path, field, value
):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            field: value,
        },
        providers={"a": QueryProvider("x"), "b": QueryProvider("x")},
    )

    assert response.status_code == 422
    assert "must be between" in response.text
    assert resolved == []


# Criterion 6: only hard_cap supplied uses the module default warning in the
# cross-check and enforces the supplied cap.
def test_route_only_cap_supplied_uses_default_warning_and_enforces_cap(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "hard_cap_chars": 25_000,
        },
        providers={"a": QueryProvider("z" * 26_000), "b": QueryProvider("z" * 26_000)},
    )

    assert response.status_code == 200
    events = _parse_sse(response)
    for seat in ("worker_a", "worker_b"):
        seat_events = [event for event in events if event.get("seat_id") == seat]
        joined = "".join(
            event["delta"] for event in seat_events if event["type"] == "seat_delta"
        )
        assert joined == "z" * 25_000
        assert seat_events[-1]["finish_reason"] == "modelmix_output_cap"
    assert not any(event["type"] == "run_failed" for event in events)


# Criterion 7: only warning_threshold supplied uses the module default cap.
def test_route_only_warning_supplied_uses_default_cap(monkeypatch, tmp_path):
    response, resolved = _route_post(
        monkeypatch,
        tmp_path,
        body={
            "prompt": "override",
            "worker_a_model": "a",
            "worker_b_model": "b",
            "warning_threshold_chars": 1_000,
        },
        providers={
            "a": DeltasProvider(("a" * 10,) * 110),
            "b": DeltasProvider(("ok",)),
        },
    )

    assert response.status_code == 200
    events = _parse_sse(response)
    warnings = [event for event in events if event["type"] == "seat_output_warning"]
    assert len(warnings) == 1
    assert warnings[0]["threshold"] == 1_000
    seat_a = [event for event in events if event.get("seat_id") == "worker_a"]
    assert seat_a[-1]["finish_reason"] == "stop"
    assert not any(
        event.get("finish_reason") == "modelmix_output_cap" for event in events
    )
    assert not any(event["type"] == "run_failed" for event in events)


# Criterion 8: the Moderator honors the same per-request override.
async def test_moderator_honors_per_request_override():
    ok, events = await run_moderator_events(
        DeltasProvider(("a" * 20, "b" * 20, "c" * 20)),
        warning_threshold_chars=10,
        hard_cap_chars=30,
    )

    assert ok is True
    assert [event["type"] for event in events if event["actor"] == "moderator"] == [
        "moderator_started",
        "moderator_delta",
        "moderator_output_warning",
        "moderator_delta",
        "moderator_completed",
    ]
    joined = "".join(
        event["delta"] for event in events if event["type"] == "moderator_delta"
    )
    assert joined == "a" * 20 + "b" * 10
    warning = next(event for event in events if event["type"] == "moderator_output_warning")
    assert warning["chars"] == 20
    assert warning["threshold"] == 10
    assert events[-1]["type"] == "moderator_completed"
    assert events[-1]["finish_reason"] == "modelmix_output_cap"


# Criterion 8 threading: the registry delivers the override to both the worker
# seats and the Moderator through the run-phase chain.
async def test_registry_threads_override_to_workers_and_moderator(tmp_path):
    store = AtomicJsonModelMixPersistence(tmp_path)
    registry = RunRegistry(persistence=store)
    providers = {
        "a": DeltasProvider(("w" * 60,)),
        "b": DeltasProvider(("x" * 60,)),
        "m": DeltasProvider(("m" * 40, "n" * 40)),
    }
    run = await registry.start(
        "override prompt",
        "a",
        "b",
        providers.__getitem__,
        "m",
        warning_threshold_chars=15,
        hard_cap_chars=35,
    )
    await run.task

    events = await run.events_after(0)
    for seat in ("worker_a", "worker_b"):
        seat_events = [event for event in events if event.get("seat_id") == seat]
        joined = "".join(
            event["delta"] for event in seat_events if event["type"] == "seat_delta"
        )
        assert len(joined) == 35
        assert seat_events[-1]["type"] == "seat_completed"
        assert seat_events[-1]["finish_reason"] == "modelmix_output_cap"
    moderator_events = [event for event in events if event["type"].startswith("moderator_")]
    joined = "".join(
        event["delta"] for event in moderator_events if event["type"] == "moderator_delta"
    )
    assert joined == "m" * 35
    assert moderator_events[-1]["type"] == "moderator_completed"
    assert moderator_events[-1]["finish_reason"] == "modelmix_output_cap"
    assert events[-1]["type"] == "run_completed"
    assert events[-1]["status"] == "completed"

# Mission 050 regression: the per-seat cost warning never disturbs the existing
# output-length warning; both coexist on one completion.
@pytest.mark.asyncio
async def test_cost_warning_coexists_with_output_warning_unaffected(monkeypatch):
    from backend.providers.openrouter import _PRICING
    _PRICING["vendor/pricey"] = {"prompt": 1e-3, "completion": 1e-3}
    monkeypatch.setattr("backend.modelmix.guardrails.WARNING_OUTPUT_THRESHOLD_CHARS", 40)
    monkeypatch.setattr("backend.modelmix.guardrails.HARD_OUTPUT_CAP_CHARS", 100_000)
    usage = {"prompt_tokens": 100, "completion_tokens": 100}
    providers = {"openrouter:vendor/pricey": DeltasProvider(("a" * 20, "b" * 20, "c" * 20), usage=usage)}
    events = [
        event
        async for event in multiplex_workers(
            "guardrail prompt", "openrouter:vendor/pricey", None, providers.__getitem__
        )
    ]
    output_warnings = [e for e in events if e["type"] == "seat_output_warning"]
    cost_warnings = [e for e in events if e["type"] == "seat_cost_warning"]
    assert len(output_warnings) == 1
    assert output_warnings[0]["chars"] == 40
    assert output_warnings[0]["threshold"] == 40
    assert len(cost_warnings) == 1
    completed = [e for e in events if e["type"] == "seat_completed"]
    assert len(completed) == 1
    # Cap is huge, so this is a normal stop completion; cost warning was extra.
    assert completed[0]["finish_reason"] == "stop"
    _PRICING.clear()
