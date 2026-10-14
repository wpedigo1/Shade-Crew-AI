"""Process-local ModelMix run ownership and lifecycle."""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import aclosing
from typing import Dict, List, Optional

from . import timeouts
from .history import build_seat_history
from .journal import (
    MAX_EVENTS_PER_RUN,
    MAX_RETAINED_TERMINAL_RUNS,
    TERMINAL_RUN_TTL_SECONDS,
    TERMINAL_STATUSES,
    RunEventJournal,
)
from .orchestrator import ProviderResolver, multiplex_workers
from .moderator import assemble_moderator_input, run_moderator
from .persistence import ModelMixPersistence, modelmix_persistence


class RunRegistry:
    """Own ModelMix run tasks and their bounded in-memory journals."""

    def __init__(
        self,
        *,
        max_events_per_run: int = MAX_EVENTS_PER_RUN,
        max_terminal_runs: int = MAX_RETAINED_TERMINAL_RUNS,
        terminal_ttl_seconds: float = TERMINAL_RUN_TTL_SECONDS,
        persistence: ModelMixPersistence = modelmix_persistence,
        seat_timeout: Optional[float] = None,
        run_timeout: Optional[float] = None,
    ) -> None:
        self.max_events_per_run = max_events_per_run
        self.max_terminal_runs = max_terminal_runs
        self.terminal_ttl_seconds = terminal_ttl_seconds
        self.persistence = persistence
        self.seat_timeout = seat_timeout
        self.run_timeout = run_timeout
        self._runs: Dict[str, RunEventJournal] = {}
        self._lock = asyncio.Lock()

    async def start(
        self,
        prompt: str,
        worker_a_model: str,
        worker_b_model: Optional[str],
        provider_resolver: ProviderResolver,
        moderator_model: Optional[str] = None,
        session_id: Optional[str] = None,
        warning_threshold_chars: Optional[int] = None,
        hard_cap_chars: Optional[int] = None,
        temperature: Optional[float] = None,
        moderator_guidance: Optional[str] = None,
    ) -> RunEventJournal:
        await self._prune()
        session_id = session_id or str(uuid.uuid4())
        await self.persistence.create_session(session_id)
        run = RunEventJournal(str(uuid.uuid4()), max_events=self.max_events_per_run)
        session_document = await self.persistence.load_session(session_id)
        if session_document is None:
            raise RuntimeError("ModelMix session disappeared before run creation")
        seat_histories = {
            "worker_a": build_seat_history(
                session_document,
                "worker_a",
                exclude_run_id=run.run_id,
            ),
            "moderator": build_seat_history(
                session_document,
                "moderator",
                exclude_run_id=run.run_id,
            ),
        }
        if worker_b_model is not None:
            seat_histories["worker_b"] = build_seat_history(
                session_document,
                "worker_b",
                exclude_run_id=run.run_id,
            )
        models = {"worker_a": worker_a_model, "moderator": moderator_model}
        if worker_b_model is not None:
            models["worker_b"] = worker_b_model
        await self.persistence.create_run(session_id, {
            "run_id": run.run_id,
            "prompt": prompt,
            "models": models,
            "status": "created",
            "latest_seq": 0,
            "events": [],
        })
        run.persist_event = lambda event, status: self.persistence.append_event(
            session_id, run.run_id, event, status
        )
        run.session_id = session_id
        async with self._lock:
            self._runs[run.run_id] = run
        run.task = asyncio.create_task(
            self._run(
                run,
                prompt,
                worker_a_model,
                worker_b_model,
                provider_resolver,
                moderator_model,
                seat_histories,
                warning_threshold_chars,
                hard_cap_chars,
                temperature,
                moderator_guidance,
            )
        )
        await asyncio.sleep(0)
        return run

    async def restore(self, run_id: str, session: Dict[str, object]) -> Optional[RunEventJournal]:
        """Restore one durable run into this process for replay after restart."""
        snapshot = next((item for item in session["session"]["runs"] if item["run_id"] == run_id), None)
        if snapshot is None:
            return None
        session_id = session["session"]["session_id"]
        if snapshot["status"] not in TERMINAL_STATUSES:
            await self.persistence.append_event(session_id, run_id, {
                "run_id": run_id,
                "seq": snapshot["latest_seq"] + 1,
                "type": "run_failed",
                "error": "Backend restarted before the run reached a terminal state",
                "reason": "backend_restart",
            }, "failed")
            refreshed = await self.persistence.load_session(session_id)
            snapshot = next(item for item in refreshed["session"]["runs"] if item["run_id"] == run_id)
        run = RunEventJournal.restore(snapshot, max_events=self.max_events_per_run)
        run.session_id = session_id
        async with self._lock:
            existing = self._runs.setdefault(run_id, run)
        return existing

    async def restore_persisted(self, run_id: str) -> Optional[RunEventJournal]:
        """Locate and restore a run from any durable session."""
        found = await self.persistence.find_run(run_id)
        if found is None:
            return None
        session, _snapshot = found
        return await self.restore(run_id, session)

    async def get(self, run_id: str) -> Optional[RunEventJournal]:
        await self._prune()
        async with self._lock:
            return self._runs.get(run_id)

    async def active_run_for_session(self, session_id: str) -> Optional[str]:
        """Return the run_id of an in-process, non-terminal run for a session.

        A run is considered active while its status is not in
        ``TERMINAL_STATUSES`` (e.g. ``created``/``active``). Used by the delete
        route to refuse deleting a session out from under a streaming run.
        """
        await self._prune()
        async with self._lock:
            for run in self._runs.values():
                if (
                    run.session_id == session_id
                    and run.status not in TERMINAL_STATUSES
                ):
                    return run.run_id
            return None

    async def cancel(self, run_id: str) -> Optional[RunEventJournal]:
        run = await self.get(run_id)
        if run is None:
            return None
        if run.status in TERMINAL_STATUSES or run.cancellation_requested:
            return run
        run.cancellation_requested = True
        await run.append("run_cancel_requested")
        if run.task and not run.task.done():
            run.task.cancel()
        return run

    async def _run(
        self,
        run: RunEventJournal,
        prompt: str,
        worker_a_model: str,
        worker_b_model: Optional[str],
        provider_resolver: ProviderResolver,
        moderator_model: Optional[str],
        seat_histories: Dict[str, List[Dict[str, str]]],
        warning_threshold_chars: Optional[int] = None,
        hard_cap_chars: Optional[int] = None,
        temperature: Optional[float] = None,
        moderator_guidance: Optional[str] = None,
    ) -> None:
        bound = timeouts.RUN_TIMEOUT_SECONDS if self.run_timeout is None else self.run_timeout
        try:
            await run.mark_status("active")
            await asyncio.wait_for(
                self._run_phase(
                    run,
                    prompt,
                    worker_a_model,
                    worker_b_model,
                    provider_resolver,
                    moderator_model,
                    seat_histories,
                    warning_threshold_chars,
                    hard_cap_chars,
                    temperature,
                    moderator_guidance,
                ),
                timeout=bound,
            )
        except asyncio.TimeoutError:
            await run.append(
                "run_failed",
                error=f"Run timed out after {bound:g} seconds",
                reason="timeout",
            )
            await run.mark_status("failed")
        except asyncio.CancelledError:
            await run.append("run_cancelled")
            await run.mark_status("cancelled")
        except Exception as exc:
            await run.append("run_failed", error=str(exc))
            await run.mark_status("failed")
        finally:
            if run.status not in TERMINAL_STATUSES:
                await run.mark_status("failed")
            await self._prune()

    async def _run_phase(
        self,
        run: RunEventJournal,
        prompt: str,
        worker_a_model: str,
        worker_b_model: Optional[str],
        provider_resolver: ProviderResolver,
        moderator_model: Optional[str],
        seat_histories: Dict[str, List[Dict[str, str]]],
        warning_threshold_chars: Optional[int] = None,
        hard_cap_chars: Optional[int] = None,
        temperature: Optional[float] = None,
        moderator_guidance: Optional[str] = None,
    ) -> None:
        worker_outputs = {"worker_a": ""}
        if worker_b_model is not None:
            worker_outputs["worker_b"] = ""
        worker_failures: Dict[str, str] = {}
        worker_seat_histories = {"worker_a": seat_histories["worker_a"]}
        if worker_b_model is not None:
            worker_seat_histories["worker_b"] = seat_histories["worker_b"]
        worker_stream = multiplex_workers(
            prompt,
            worker_a_model,
            worker_b_model,
            provider_resolver,
            run_id=run.run_id,
            event_factory=run.append,
            emit_run_completed=moderator_model is None,
            seat_timeout=self.seat_timeout,
            warning_threshold_chars=warning_threshold_chars,
            hard_cap_chars=hard_cap_chars,
            temperature=temperature,
            seat_histories=worker_seat_histories,
        )
        async with aclosing(worker_stream):
            async for source_event in worker_stream:
                seat_id = source_event.get("seat_id")
                if source_event["type"] == "seat_delta" and seat_id in worker_outputs:
                    worker_outputs[seat_id] += str(source_event.get("delta") or "")
                elif source_event["type"] == "seat_failed" and seat_id:
                    worker_failures[seat_id] = str(source_event.get("error") or "Worker failed")
                elif (
                    source_event["type"] == "seat_completed"
                    and seat_id in worker_outputs
                    and not worker_outputs[seat_id]
                ):
                    worker_failures[seat_id] = "Worker returned no visible output"
                if source_event["type"] == "run_completed":
                    await run.mark_status(str(source_event.get("status") or "completed"))

        if moderator_model is not None and worker_b_model is not None:
            successful_outputs = {
                seat_id: output
                for seat_id, output in worker_outputs.items()
                if seat_id not in worker_failures
            }
            if not successful_outputs:
                await run.append(
                    "moderator_failed",
                    actor="moderator",
                    error="Insufficient worker input: both workers failed",
                    reason="insufficient_input",
                )
                await run.append("run_failed", error="Both workers failed")
                await run.mark_status("failed")
                return

            moderator_input = assemble_moderator_input(
                prompt,
                successful_outputs,
                worker_failures,
                history=seat_histories["moderator"],
                moderator_guidance=moderator_guidance,
            )
            try:
                moderator_provider = provider_resolver(moderator_model)
            except Exception as exc:
                await run.append(
                    "moderator_failed",
                    actor="moderator",
                    error=str(exc),
                )
                await run.append("run_failed", error="Moderator provider resolution failed")
                await run.mark_status("failed")
                return
            moderator_task = asyncio.create_task(
                run_moderator(
                    moderator_model,
                    moderator_provider,
                    moderator_input,
                    run.append,
                    seat_timeout=self.seat_timeout,
                    warning_threshold_chars=warning_threshold_chars,
                    hard_cap_chars=hard_cap_chars,
                    temperature=temperature,
                )
            )
            try:
                moderator_ok = await asyncio.shield(moderator_task)
            except asyncio.CancelledError:
                if not moderator_task.done():
                    moderator_task.cancel()
                await timeouts.await_cancellation_grace((moderator_task,))
                raise
            if not moderator_ok:
                await run.append("run_failed", error="Moderator failed")
                await run.mark_status("failed")
                return
            final_status = "partial" if worker_failures else "completed"
            await run.append("run_completed", status=final_status)
            await run.mark_status(final_status)

    async def _prune(self) -> None:
        now = time.monotonic()
        async with self._lock:
            expired = [
                run_id
                for run_id, run in self._runs.items()
                if run.terminal_at is not None
                and now - run.terminal_at >= self.terminal_ttl_seconds
            ]
            for run_id in expired:
                self._runs.pop(run_id, None)

            terminal = sorted(
                (
                    run
                    for run in self._runs.values()
                    if run.terminal_at is not None
                ),
                key=lambda run: run.terminal_at or 0,
            )
            for run in terminal[: max(0, len(terminal) - self.max_terminal_runs)]:
                self._runs.pop(run.run_id, None)


run_registry = RunRegistry()
