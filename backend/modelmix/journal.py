"""Bounded process-local event journals for ModelMix alpha runs."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Deque, Dict, List, Optional

MAX_EVENTS_PER_RUN = 1000
MAX_RETAINED_TERMINAL_RUNS = 100
TERMINAL_RUN_TTL_SECONDS = 15 * 60
TERMINAL_STATUSES = {"completed", "partial", "failed", "cancelled"}


class ReplayUnavailableError(Exception):
    """The requested cursor predates the oldest retained event."""


@dataclass
class RunEventJournal:
    """Ordered event storage and notification for one run."""

    run_id: str
    max_events: int = MAX_EVENTS_PER_RUN
    status: str = "created"
    created_at: float = field(default_factory=time.monotonic)
    terminal_at: Optional[float] = None
    task: Optional[asyncio.Task[None]] = field(default=None, repr=False)
    cancellation_requested: bool = False
    session_id: Optional[str] = None
    _events: Deque[Dict[str, Any]] = field(default_factory=deque, repr=False)
    _next_seq: int = 1
    _condition: asyncio.Condition = field(default_factory=asyncio.Condition, repr=False)
    persist_event: Optional[Callable[[Dict[str, Any], str], Awaitable[None]]] = field(default=None, repr=False)

    async def append(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        """Create and append the next canonical event atomically."""
        async with self._condition:
            event = {
                "run_id": self.run_id,
                "seq": self._next_seq,
                "type": event_type,
                "ts": time.time(),
                **payload,
            }
            self._next_seq += 1
            self._events.append(event)
            while len(self._events) > self.max_events:
                self._events.popleft()
            self._condition.notify_all()
            if self.persist_event is not None:
                await self.persist_event(event, self.status)
            return event

    async def events_after(self, after_seq: int) -> List[Dict[str, Any]]:
        """Return retained original events after a cursor or signal a replay gap."""
        async with self._condition:
            self._validate_cursor(after_seq)
            return [event for event in self._events if event["seq"] > after_seq]

    async def tail(self, after_seq: int) -> AsyncIterator[Dict[str, Any]]:
        """Replay retained events, then wait for events until the run is terminal."""
        cursor = after_seq
        while True:
            async with self._condition:
                self._validate_cursor(cursor)
                available = [event for event in self._events if event["seq"] > cursor]
                if not available and self.status not in TERMINAL_STATUSES:
                    await self._condition.wait()
                    continue
                terminal = self.status in TERMINAL_STATUSES
            for event in available:
                cursor = event["seq"]
                yield event
            if terminal:
                return

    async def mark_status(self, status: str) -> None:
        async with self._condition:
            self.status = status
            if status in TERMINAL_STATUSES and self.terminal_at is None:
                self.terminal_at = time.monotonic()
            self._condition.notify_all()

    @classmethod
    def restore(cls, snapshot: Dict[str, Any], *, max_events: int = MAX_EVENTS_PER_RUN) -> "RunEventJournal":
        """Reconstruct a replayable journal without prior process memory."""
        run = cls(snapshot["run_id"], max_events=max_events, status=snapshot["status"])
        run._events = deque(snapshot["events"][-max_events:])
        run._next_seq = snapshot["latest_seq"] + 1
        if run.status in TERMINAL_STATUSES:
            run.terminal_at = time.monotonic()
        return run

    def _validate_cursor(self, after_seq: int) -> None:
        if after_seq < 0:
            raise ValueError("after_seq must be non-negative")
        if self._events and after_seq < self._events[0]["seq"] - 1:
            raise ReplayUnavailableError(
                f"events through seq {self._events[0]['seq'] - 1} are no longer retained"
            )
