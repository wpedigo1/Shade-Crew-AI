"""Process-local ModelMix run ownership and lifecycle."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import aclosing
from copy import deepcopy
from typing import Dict, List, Optional

from . import timeouts
from .budgets import case_budgets, ResearchBudget
from .cases import CasePersistence
from .research import run_research_seat
from .history import build_seat_history
from .journal import (
    MAX_EVENTS_PER_RUN,
    MAX_RETAINED_TERMINAL_RUNS,
    TERMINAL_RUN_TTL_SECONDS,
    TERMINAL_STATUSES,
    RunEventJournal,
)
from .orchestrator import ProviderResolver, multiplex_workers
from .moderator import assemble_moderator_input
from .verification import run_crew_chief
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
        moderator_runner=run_crew_chief,
        research_adapter=None,
        research_budgets=None,
    ) -> None:
        self.max_events_per_run = max_events_per_run
        self.max_terminal_runs = max_terminal_runs
        self.terminal_ttl_seconds = terminal_ttl_seconds
        self.persistence = persistence
        self.seat_timeout = seat_timeout
        self.run_timeout = run_timeout
        # Executor seam: verification uses this bounded visible input
        # and canonical event factory. Registry retains lifecycle/persistence ownership.
        self.moderator_runner = moderator_runner
        self.research_adapter = research_adapter
        self.research_budgets = research_budgets
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
        execution_budgets = None
        if isinstance(self.persistence, CasePersistence):
            execution_budgets = deepcopy(self.research_budgets or case_budgets())
            if self.run_timeout is not None:
                execution_budgets['run_seconds'] = self.run_timeout
            if self.seat_timeout is not None:
                execution_budgets = {**execution_budgets,
                                     'mechanic': {**execution_budgets['mechanic'], 'seconds': self.seat_timeout},
                                     'chief': {**execution_budgets['chief'], 'seconds': self.seat_timeout}}
        await self.persistence.create_run(session_id, {
            "run_id": run.run_id,
            "prompt": prompt,
            "models": models,
            "status": "created",
            "latest_seq": 0,
            "events": [],
            **({"execution_budgets": execution_budgets, 'seat_histories': seat_histories,
                'input_contract': 'case-research-v1',
                'controls': {'temperature': temperature, 'moderator_guidance': moderator_guidance,
                             'warning_threshold_chars': warning_threshold_chars, 'hard_cap_chars': hard_cap_chars}}
               if execution_budgets else {}),
        })
        if execution_budgets:
            persisted = await self.persistence.load_session(session_id)
            current = next(item for item in persisted['session']['runs'] if item['run_id'] == run.run_id)
            run.case_snapshot = current['case_snapshot']
            run.execution_budgets = execution_budgets
            prompt = prompt + '\n\nFrozen shared Case context:\n' + json.dumps(run.case_snapshot)
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
            if isinstance(self.persistence, CasePersistence):
                for message in session['session']['messages']:
                    if message['run_id'] != run_id:
                        continue
                    for record in message.get('research', []):
                        if record['status'] == 'running':
                            snapshot['latest_seq'] += 1
                            await self.persistence.append_event(session_id, run_id, {
                                'run_id': run_id, 'seq': snapshot['latest_seq'], 'ts': time.time(),
                                'type': 'tool_completed', 'seat_id': message['seat'], 'model': record.get('model'),
                                'tool': {**record, 'status': 'interrupted', 'completed_at': time.time(),
                                         'error': 'Backend restarted; result unresolved', 'completion_origin': 'backend_restart'}}, 'active')
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

    async def _settle_research(self, run, status):
        """Journal pending tool interruption before the terminal run event.

        Worker cleanup queues can be abandoned during cancellation; this records
        lifecycle interruption honestly without claiming the tool actually stopped.
        """
        if not hasattr(run, 'case_snapshot'):
            return
        doc = await self.persistence.load_session(run.session_id)
        for message in doc['session']['messages']:
            if message['run_id'] != run.run_id:
                continue
            for record in message.get('research', []):
                if record['status'] == 'running':
                    await run.append('tool_completed', seat_id=message['seat'], actor=message['seat'],
                                     model=record.get('model'), tool={**record, 'status': status,
                                     'error': 'Run interrupted; tool result unresolved', 'completed_at': time.time(),
                                     'completion_origin': 'run_lifecycle'})

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
        case_run_bound = getattr(run, 'execution_budgets', {}).get('run_seconds', timeouts.RUN_TIMEOUT_SECONDS)
        bound = case_run_bound if self.run_timeout is None else self.run_timeout
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
            await self._settle_research(run, 'timeout')
            await run.append(
                "run_failed",
                error=f"Run timed out after {bound:g} seconds",
                reason="timeout",
            )
            await run.mark_status("failed")
        except asyncio.CancelledError:
            await self._settle_research(run, 'cancelled')
            await run.append("run_cancelled")
            await run.mark_status("cancelled")
        except Exception as exc:
            await self._settle_research(run, 'failed')
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
        is_case = hasattr(run, 'case_snapshot')
        worker_work = {seat: [] for seat in worker_outputs}
        async def research_worker(seat, model, provider, messages, create, **kwargs):
            budget = ResearchBudget(**run.execution_budgets['mechanic'])
            return await run_research_seat(seat, model, provider, messages, create, snapshot=run.case_snapshot,
                                           resources=self.persistence, budget=budget, adapter=self.research_adapter, **kwargs)
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
            seat_runner=research_worker if is_case else None,
        )
        async with aclosing(worker_stream):
            async for source_event in worker_stream:
                seat_id = source_event.get("seat_id")
                if source_event['type'] == 'tool_completed' and seat_id in worker_work:
                    worker_work[seat_id].append({**source_event['tool'], 'seat_id': seat_id,
                                                'model': source_event.get('model'), 'run_id': run.run_id})
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
            if is_case:
                # Failed/limited work can contain useful evidence; Chief may salvage it.
                successful_outputs = {seat: text for seat, text in worker_outputs.items() if text}
            if not successful_outputs and not (is_case and any(worker_work.values())):
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
                await run.append("run_failed", error="Crew Chief provider resolution failed")
                await run.mark_status("failed")
                return
            if is_case:
                async def case_chief(model, provider, handoff, create, **kwargs):
                    kwargs.pop('seat_timeout', None)
                    extra = {'role': 'user', 'content': 'Mechanic terminal conditions: ' + json.dumps(worker_failures)}
                    return await run_research_seat('moderator', model, provider, [*handoff.messages, extra], create,
                                                   snapshot=run.case_snapshot, resources=self.persistence,
                                                   budget=ResearchBudget(**run.execution_budgets['chief']),
                                                   peer_work=worker_work, peer_answers=worker_outputs, adapter=self.research_adapter, **kwargs)
                chief_runner = case_chief
            else:
                chief_runner = self.moderator_runner
            moderator_task = asyncio.create_task(
                chief_runner(
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
                if is_case:
                    saved = await self.persistence.load_session(run.session_id)
                    if any(m.get('run_id') == run.run_id and m.get('seat') == 'moderator' and m.get('content') for m in saved['session']['messages']):
                        await run.append('run_completed', status='partial')
                        await run.mark_status('partial')
                        return
                await run.append("run_failed", error="Crew Chief failed")
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


case_persistence = CasePersistence(os.environ.get('SHADE_CREW_CASES_DIR', modelmix_persistence.root.parent / 'cases'),
                                   legacy=modelmix_persistence)
run_registry = RunRegistry(persistence=case_persistence)
