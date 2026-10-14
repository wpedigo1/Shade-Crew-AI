"""Tests for the deterministic mock provider library (Mission 046)."""

import asyncio

import pytest

from backend.modelmix.orchestrator import multiplex_workers
from backend.modelmix.timeouts import aiter_with_deadline
from backend.providers.base import ProviderStreamEvent

from backend.tests.mock_providers import (
    cancellation_aware_provider,
    duplicate_provider,
    failing_provider,
    malformed_event_provider,
    missing_usage_provider,
    normal_provider,
    out_of_order_provider,
    rate_limited_provider,
    slow_streaming_provider,
    streaming_provider,
    timeout_provider,
)


async def collect_stream(provider, model_id="m"):
    events = []
    async for event in provider.stream_query(model_id, [{"role": "user", "content": "hi"}]):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_normal_provider_query_and_stream():
    provider = normal_provider(content="hello", usage={"total_tokens": 5})
    result = await provider.query("m", [{"role": "user", "content": "hi"}])
    assert result["content"] == "hello"
    assert result["usage"] == {"total_tokens": 5}
    assert result["error"] is False

    events = await collect_stream(provider)
    assert len(events) == 1
    assert events[0].type == "completed"
    assert events[0].result["content"] == "hello"
    assert events[0].usage == {"total_tokens": 5}


@pytest.mark.asyncio
async def test_normal_provider_non_streaming_path():
    provider = normal_provider(content="plain", supports_streaming=False)
    assert provider.supports_streaming is False
    result = await provider.query("m", [{"role": "user", "content": "hi"}])
    assert result["content"] == "plain"


@pytest.mark.asyncio
async def test_streaming_provider_yields_deltas_then_completed():
    provider = streaming_provider(deltas=("a", "b"), usage={"total_tokens": 3}, finish_reason="stop")
    events = await collect_stream(provider)
    assert [e.type for e in events] == ["text_delta", "text_delta", "completed"]
    assert [e.delta for e in events[:2]] == ["a", "b"]
    assert events[-1].finish_reason == "stop"
    assert events[-1].usage == {"total_tokens": 3}
    assert events[-1].result["content"] == "ab"


@pytest.mark.asyncio
async def test_slow_streaming_provider_respects_delay():
    provider = slow_streaming_provider(deltas=("x", "y"), delay_between=0.005)
    events = await collect_stream(provider)
    assert [e.delta for e in events if e.type == "text_delta"] == ["x", "y"]


@pytest.mark.asyncio
async def test_failing_provider_errors_on_both_paths():
    provider = failing_provider(error_message="boom")
    result = await provider.query("m", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert result["error_message"] == "boom"

    events = await collect_stream(provider)
    assert events == [ProviderStreamEvent(type="error", error_message="boom")]


@pytest.mark.asyncio
async def test_timeout_provider_never_completes_within_bounded_wait():
    provider = timeout_provider()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            collect_stream(provider), timeout=0.05
        )


@pytest.mark.asyncio
async def test_rate_limited_provider_shape():
    provider = rate_limited_provider()
    result = await provider.query("m", [{"role": "user", "content": "hi"}])
    assert result["error"] is True
    assert "Rate limit exceeded" in result["error_message"]
    assert "429" in result["error_message"]

    events = await collect_stream(provider)
    assert events[0].type == "error"
    assert "429" in events[0].error_message


@pytest.mark.asyncio
async def test_cancellation_aware_provider_reraises_cleanly():
    provider = cancellation_aware_provider(deltas=("a", "b"))
    stream = provider.stream_query("m", [{"role": "user", "content": "hi"}])
    first = await anext(stream)
    assert first.type == "text_delta"
    task = asyncio.ensure_future(anext(stream))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.cancelled is True


@pytest.mark.asyncio
async def test_malformed_event_provider_yields_unexpected_type():
    provider = malformed_event_provider()
    events = await collect_stream(provider)
    assert events[0].type == "unexpected_event_type"
    assert events[0].delta == "surprise"
    assert events[1].type == "completed"


@pytest.mark.asyncio
async def test_missing_usage_provider_reports_no_usage():
    provider = missing_usage_provider(content="no usage here")
    result = await provider.query("m", [{"role": "user", "content": "hi"}])
    assert result["content"] == "no usage here"
    assert result["usage"] is None

    events = await collect_stream(provider)
    assert events[-1].usage is None
    assert events[-1].result["usage"] is None


@pytest.mark.asyncio
async def test_out_of_order_provider_reverses_deltas():
    provider = out_of_order_provider(deltas=("a", "b", "c"))
    events = await collect_stream(provider)
    deltas = [e.delta for e in events if e.type == "text_delta"]
    assert deltas == ["c", "b", "a"]
    assert events[-1].result["content"] == "cba"


@pytest.mark.asyncio
async def test_duplicate_provider_yields_each_delta_twice():
    provider = duplicate_provider(deltas=("a", "b"))
    events = await collect_stream(provider)
    deltas = [e.delta for e in events if e.type == "text_delta"]
    assert deltas == ["a", "a", "b", "b"]
    assert events[-1].result["content"] == "abab"


@pytest.mark.asyncio
async def test_streaming_provider_drives_real_multiplex_flow():
    """Proof of real usability: replace an ad-hoc fake in a new test."""
    provider = streaming_provider(deltas=("final ", "answer"), usage={"total_tokens": 4}, finish_reason="stop")
    events = []
    async for event in multiplex_workers("prompt", "worker:model", None, lambda mid: provider):
        events.append(event)

    deltas = [e["delta"] for e in events if e["type"] == "seat_delta"]
    assert "".join(deltas) == "final answer"
    completed = [e for e in events if e["type"] == "seat_completed"]
    assert len(completed) == 1
    assert completed[0]["usage"] == {"total_tokens": 4}
    assert completed[0]["finish_reason"] == "stop"