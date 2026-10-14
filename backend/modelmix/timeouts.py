"""ModelMix-owned wall-clock run and seat timeout bounds."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Iterable, TypeVar

SEAT_TIMEOUT_SECONDS = 300
RUN_TIMEOUT_SECONDS = 600
CANCEL_GRACE_SECONDS = 5.0

_T = TypeVar("_T")


async def await_cancellation_grace(tasks: Iterable[asyncio.Task]) -> None:
    """Wait up to ``CANCEL_GRACE_SECONDS`` for cancelled tasks, then let go.

    Cancellation cleanup must never be able to block an unwinding exception
    for longer than the grace period, even when a task (or the provider
    stream it wraps) does not honor its cancellation promptly. Tasks still
    pending after the grace period are abandoned to loop/GC cleanup instead
    of being awaited forever; this is an accepted residual risk deliberately
    smaller than the 600s run-timeout backstop.
    """
    still_running = [task for task in tasks if not task.done()]
    if still_running:
        await asyncio.wait(still_running, timeout=CANCEL_GRACE_SECONDS)


async def aiter_with_deadline(
    iterator: AsyncIterator[_T],
    timeout: float,
) -> AsyncIterator[_T]:
    """Stream one async iterator within a cumulative wall-clock deadline.

    Raises asyncio.TimeoutError when the deadline passes before exhaustion.
    Each element waits no longer than the time remaining on the deadline, so
    a slow producer is surfaced as a timeout instead of silently stalling.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError
        try:
            yield await asyncio.wait_for(iterator.__anext__(), timeout=remaining)
        except StopAsyncIteration:
            return