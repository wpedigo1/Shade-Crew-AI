# Mission 024 — Cancel-Before-Start Terminal State Fix

Route: Big Pickle (OpenCode Zen)
Punch Board items: 9/16/33 (cancellation robustness, run state machine)
Base: `main` @ `2bb038f` "fix(modelmix): bound cancellation cleanup to close the alpha-blocking race (Mission 023)"
Date: 2026-08-31
Result: **PASS (LOCAL)**

## Objective

Close the synthetic edge case where a run is cancelled before `_run`'s first
`await` and the run stays `"created"` forever instead of reaching terminal
`"cancelled"` with a `run_cancelled` event.

## Root Cause

Calling `task.cancel()` on a task whose coroutine has **never been stepped**
(beyond the initial `asyncio.create_task` scheduling) causes CPython to call
`coro.throw(CancelledError)` on a never-started coroutine. The Python 3.10
`Task.__step` mechanism clears `_must_cancel` before the throw (line 222), but
`generator.throw()` on a never-started generator raises the exception **without
executing any of the coroutine body** — not even a `try:` that is the literal
first statement. This was confirmed empirically with three CPython 3.10.20
probes:

1. Coroutine starting with `try: await asyncio.sleep(...)` — cancelled before
   start, the `except asyncio.CancelledError` block **never entered**.
2. Same structure with a `log.append` before `try:` — the append also never
   executed. The body was entirely skipped.
3. Comparing "started first" vs "cancel before start" on the same coroutine:
   started-first returns `"handled"` (handler completes normally);
   cancel-before-start returns `CancelledError` (handler never runs).

This is structurally distinct from the cancel-during-execution case (Mission
023) where the coroutine is already suspended at a real `await` — in that case
`task.cancel()` cancels the `_fut_waiter` future directly (lines 204–209), and
the `try/except asyncio.CancelledError` inside the coroutine catches it as
expected.

The net effect: the planned "move `mark_status("active")` inside `try`" fix is
sufficient for the already-started case but completely ineffective for the
never-started case. The `try/except` can only catch CancelledError thrown into
a coroutine that has already entered its body.

## What Changed

### `backend/modelmix/registry.py`

Two changes:

1. **`start()`:** `await asyncio.sleep(0)` added after `asyncio.create_task(...)`
   and before `return run`. This yields control to the event loop, which runs
   `_run`'s first `__step`. The coroutine enters its body, reaches its first
   real `await` (inside the `try` block), and suspends with `_fut_waiter` set.
   A subsequent `cancel()` from the caller therefore cancels that future
   (lines 204–209), and the `CancelledError` is raised at a real await point
   inside the `try` — where the existing except handler catches it.

2. **`_run()`:** `await run.mark_status("active")` moved from before the `try:`
   block to inside it, as the first statement after `try:`. This is now
   reachable for the never-started case (because `_run` is guaranteed to have
   been stepped at least once by the time `start()` returns). The `bound`
   assignment stays before `try:` (pure expression, no await).

The two changes are complementary: `sleep(0)` guarantees `_run` has entered its
body; `mark_status` inside `try` ensures the except handler covers the earliest
possible cancel point after entry.

### `backend/tests/test_modelmix_cancel_race.py`

New test `test_cancel_before_run_starts_reaches_terminal_cancelled`:
- Creates a run via `registry.start(...)` (which now steps `_run` once).
- Immediately calls `run.task.cancel()` to cancel after the first step.
- Uses `asyncio.wait({run.task}, timeout=5.0)` — NOT `asyncio.wait_for`,
  which re-cancels the task when the handler's first `await` completes.
- Asserts `run.status == "cancelled"` and last event type `"run_cancelled"`.
- Proves the cancellation handler completed despite the cancel happening
  before `start()` returned to the caller.

### Explicitly unchanged

- `timeouts.py` — no changes to `CANCEL_GRACE_SECONDS`, `await_cancellation_grace`,
  `RUN_TIMEOUT_SECONDS`, or `SEAT_TIMEOUT_SECONDS`.
- `orchestrator.py` — no changes.
- `asyncio.shield` moderator path from Mission 023 — untouched.
- Frontend — no changes.
- All 8 existing Mission 023 cancel-race tests — unchanged and passing.

## Why `asyncio.sleep(0)` and Not `asyncio.wait_for`

`asyncio.wait_for(run.task, timeout=5.0)` was the initial test approach, but
`wait_for` re-cancels the wrapped task: when the handler's first `await`
completes, `wait_for` resumes, sees `fut.done()` is `False` (handler still
running), and calls `_cancel_and_wait(fut)` — killing the handler mid-execution.
`asyncio.wait({run.task}, timeout=5.0)` never cancels the task; it simply waits
for completion or timeout.

## Evidence / Validation (raw outputs observed)

### New test

```text
uv run pytest backend/tests/test_modelmix_cancel_race.py -v -k cancel_before --basetemp ...
backend/tests/test_modelmix_cancel_race.py::test_cancel_before_run_starts_reaches_terminal_cancelled PASSED
1 passed in 0.82s
```

### Full backend suite

```text
uv run pytest backend/tests -q --basetemp ...
404 passed in 27.16s   (403 prior + 1 new; no existing test modified)
```

### Lint

```text
uv run ruff check backend/modelmix/registry.py backend/tests/test_modelmix_cancel_race.py
All checks passed!
```

### Diff scope (before commit)

```text
git diff →
  M backend/modelmix/registry.py
  M backend/tests/test_modelmix_cancel_race.py
```

## Remaining Risks

- The `await asyncio.sleep(0)` adds one event-loop tick before `start()`
  returns. This is semantically correct (the run should be "active" before the
  caller can cancel it) but slightly changes the observable timing: `run.status`
  will read `"active"` immediately after `start()` instead of `"created"`. No
  existing test asserted `"created"` right after start — the full suite passed.
- Cancel-before-start is unreachable via real HTTP transport (the cancel HTTP
  request requires the run ID, which is only available after `start()` returns).
  This fix is for robustness of the terminal state contract and deterministic
  testability.

## Acceptance Criteria → Where Covered

1. Deterministic test — cancel before first yield, assert `run.status == "cancelled"` + last event `"run_cancelled"` — `test_cancel_before_run_starts_reaches_terminal_cancelled`.
2. All Mission 023 cancel regressions unchanged — 8 existing tests pass, full 404 suite green.
3. Only new test(s) added; no existing test modified — confirmed by diff.
