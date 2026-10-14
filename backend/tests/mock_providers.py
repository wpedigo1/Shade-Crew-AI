"""Deterministic mock LLM providers for ModelMix tests (Mission 046).

Small, composable factory functions returning plain ``LLMProvider`` subclass
instances. Each fixture is single-purpose and readable — test infrastructure,
not a subsystem. Tests import these instead of hand-rolling ad-hoc fakes.

All fixtures keep timing tiny by default (no real sleeps beyond the small,
bounded ``delay_between`` needed for a specific timeout/race test).
"""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

from backend.providers.base import LLMProvider, ProviderStreamEvent


class _MockBase(LLMProvider):
    """Shared no-op catalog/key methods for all fixtures."""

    async def get_models(self) -> List[Dict[str, Any]]:
        return []

    async def validate_key(self, api_key: str) -> Dict[str, Any]:
        return {"success": True}


def normal_provider(
    content: str = "a normal response",
    usage: Optional[Dict[str, Any]] = None,
    supports_streaming: bool = True,
) -> LLMProvider:
    """A single complete response with real content and optional usage.

    Supports both ``query()`` and ``stream_query()``. Set ``supports_streaming``
    to ``False`` to exercise the non-streaming ``query`` path.
    """

    class NormalProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return supports_streaming

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            return {"content": content, "usage": usage, "error": False}

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            yield ProviderStreamEvent(
                type="completed",
                result={"content": content, "usage": usage},
                finish_reason="stop",
                usage=usage,
            )

    return NormalProvider()


def streaming_provider(
    deltas: List[str] = ("delta",),
    usage: Optional[Dict[str, Any]] = None,
    finish_reason: Optional[str] = None,
) -> LLMProvider:
    """Yield real ``text_delta`` events, then a ``completed`` event."""

    class StreamingProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            for delta in deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(
                type="completed",
                result={"content": "".join(deltas), "usage": usage},
                finish_reason=finish_reason,
                usage=usage,
            )

    return StreamingProvider()


def slow_streaming_provider(
    deltas: List[str] = ("slow ", "stream"),
    delay_between: float = 0.01,
) -> LLMProvider:
    """Like ``streaming_provider`` but sleeps ``delay_between`` before each delta.

    For timeout/cancellation tests. The default delay is tiny so tests stay fast.
    """

    class SlowStreamingProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            for delta in deltas:
                await asyncio.sleep(delay_between)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(
                type="completed",
                result={"content": "".join(deltas)},
                finish_reason="stop",
            )

    return SlowStreamingProvider()


def failing_provider(error_message: str = "Provider failed") -> LLMProvider:
    """Produce an error on both the streaming and non-streaming paths."""

    class FailingProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            return {"error": True, "error_message": error_message}

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            yield ProviderStreamEvent(type="error", error_message=error_message)

    return FailingProvider()


def timeout_provider() -> LLMProvider:
    """Hangs forever, never yielding a terminal event or returning.

    No timeout logic of its own — the caller's own timeout wrapper
    (``aiter_with_deadline`` / ``asyncio.wait_for``) is responsible for
    bounding it.
    """

    class TimeoutProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            await asyncio.Event().wait()  # never returns

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            while True:
                await asyncio.sleep(3600)
                yield ProviderStreamEvent(type="text_delta", delta="")  # pragma: no cover

    return TimeoutProvider()


def rate_limited_provider() -> LLMProvider:
    """Yield/return an error shaped like a real rate-limit response."""

    error_message = "Rate limit exceeded (HTTP 429)"

    class RateLimitedProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            return {"error": True, "error_message": error_message}

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            yield ProviderStreamEvent(type="error", error_message=error_message)

    return RateLimitedProvider()


def cancellation_aware_provider(deltas: List[str] = ("cancelled ", "delta")) -> LLMProvider:
    """Streams normally but re-raises ``asyncio.CancelledError`` cleanly.

    Records cancellation on ``.cancelled`` so tests can assert the provider
    observed it.
    """

    class CancellationAwareProvider(_MockBase):
        def __init__(self):
            self.cancelled = False

        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            try:
                for delta in deltas:
                    await asyncio.sleep(0)
                    yield ProviderStreamEvent(type="text_delta", delta=delta)
                yield ProviderStreamEvent(type="completed", result={"content": "".join(deltas)})
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    return CancellationAwareProvider()


def malformed_event_provider() -> LLMProvider:
    """Yield an event that violates the ``ProviderStreamEvent`` contract.

    Specifically, a ``ProviderStreamEvent`` carrying an unexpected ``type``
    value (outside ``text_delta|completed|error``), then a normal completion —
    so calling code can be tested against provider misbehavior.
    """

    class MalformedEventProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            yield ProviderStreamEvent(type="unexpected_event_type", delta="surprise")
            yield ProviderStreamEvent(type="completed", result={"content": "recovered"})

    return MalformedEventProvider()


def missing_usage_provider(content: str = "a response without usage") -> LLMProvider:
    """Completes normally but reports ``usage=None`` on both paths."""

    class MissingUsageProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            return {"content": content, "usage": None, "error": False}

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            yield ProviderStreamEvent(
                type="completed",
                result={"content": content, "usage": None},
                finish_reason="stop",
                usage=None,
            )

    return MissingUsageProvider()


def out_of_order_provider(deltas: List[str] = ("a", "b", "c")) -> LLMProvider:
    """Yield ``text_delta`` events in the reverse of ``deltas`` order.

    Demonstrates out-of-order arrival at whatever layer tests the ordering.
    """

    class OutOfOrderProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            for delta in reversed(deltas):
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(type="completed", result={"content": "".join(reversed(deltas))})

    return OutOfOrderProvider()


def duplicate_provider(deltas: List[str] = ("a", "b")) -> LLMProvider:
    """Yield each ``text_delta`` twice, then complete.

    For testing dedup/sequence handling against repeated content at whatever
    layer needs it.
    """

    class DuplicateProvider(_MockBase):
        @property
        def supports_streaming(self) -> bool:
            return True

        async def query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> Dict[str, Any]:
            raise AssertionError("streaming fake must not use query fallback")

        async def stream_query(
            self, model_id: str, messages: List[Dict[str, str]], timeout: float = 120.0, temperature: float = 0.7
        ) -> AsyncIterator[ProviderStreamEvent]:
            for delta in deltas:
                await asyncio.sleep(0)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
                yield ProviderStreamEvent(type="text_delta", delta=delta)
            yield ProviderStreamEvent(type="completed", result={"content": "".join(deltas) * 2})

    return DuplicateProvider()