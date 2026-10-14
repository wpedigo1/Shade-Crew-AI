# Mission 023 — Deterministic Cancellation-Race Fix (Bounded Cancel Cleanup)

Route: Big Pickle (OpenCode Zen)
Punch Board items: 33 (close the remaining cancel gap), 9/17 (cancellation robustness)
Base: `main` @ `b82505d` "test(modelmix): alpha acceptance integration coverage (Mission 022)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Close the Mission 022-disclosed cancellation race: a cancel must always reach
a terminal `run_cancelled` within a bounded time, even when a provider task
does not honor its cancellation promptly (absorbs `CancelledError` and holds).
Delivered as a code + deterministic-test fix mission on top of the verified
`main @ b82505d` (full backend suite 395 passed).

## Root Cause (confirmed and refined)

Mission 022 observed `_run_phase` blocked in `multiplex_workers`' generator
`finally`:

```python
finally:
    await asyncio.gather(*tasks.values(), return_exceptions=True)  # unbounded
```

Mechanism confirmed against the installed Python 3.10.20 asyncio source and a
task-dump diagnostic: `asyncio.wait_for`'s cancellation path calls
`_cancel_and_wait(fut)`, which awaits the inner awaitable's actual completion.
When the seat's provider generator absorbs the first `CancelledError` and then
holds indefinitely, all of these happen and each blocks on the absorbing
generator:

- the seat task inside `aiter_with_deadline` (its inner `__anext__` task
  committed on `await queue.get()`/provider-hold never finishes);
- the `async with aclosing(worker_stream)` exit pushing the closure
  `GeneratorExit` into `multiplex_workers`, whose `finally` gather then waits
  on those seat tasks forever;
- and in turn the `CancelledError` that `_run`'s own
  `except asyncio.CancelledError` handler needs to emit `run_cancelled`.

The run stayed `active` (run.task parked at `registry.py:168`) until the 600s
run-timeout force-marked it failed.

Two refinements found while making the fix deterministic:

1. **The seat task absorbing the first cancel is the intended "slow-to-cancel"
   provider state, so the fix cannot rely on the seat ever finishing.** The
   correct boundary is on the *cleanup that waits for seat tasks*, not on the
   seat itself.
2. **Moderator path is fatally analogous but structurally distinct.** During
   the Moderator phase `_run_phase` awaits the `moderator_task` **directly**
   (a `Task`). Under cancellation, `Task.cancel()` only injects
   `CancelledError` into `_run_phase` *after its `_fut_waiter` completes*; a
   `moderator_task` that absorbed the cancel (same holding generator) never
   completes, so `_run_phase` is never woken and the run hangs **forever** —
   not even the 5s grace would help, because the `except
   asyncio.CancelledError` block one level down can never run. Verified with a
   task dump: `_run_phase` parked at the plain `await moderator_task` with
   `_must_cancel` unset on both `_run_phase` and `moderator_task` 20s after
   cancel.

## What Changed

### `backend/modelmix/timeouts.py`

- New constant **`CANCEL_GRACE_SECONDS = 5.0`**.
- New helper **`await_cancellation_grace(tasks)`**: waits up to the grace
  period for the given tasks to finish, then returns regardless. Never
  force-kills beyond `.cancel()`; stray tasks are abandoned to loop/GC
  cleanup. Uses `asyncio.wait(..., timeout=...)`, which cannot block the
  unwinding exception beyond the bound.

### `backend/modelmix/orchestrator.py`

`multiplex_workers`' `finally` block replaces the unbounded gather with an
explicit `.cancel()` of every pending seat task followed by
`await timeouts.await_cancellation_grace(tasks.values())`. If the tasks
finish within the grace period the behavior is identical to before; otherwise
the cleanup gives up after the bound and the run's `CancelledError` is free
to unwind to `run_cancelled`. No throw, no retry.

### `backend/modelmix/registry.py`

The Moderator phase now awaits the moderator task through an intermediate
shield so that cancellation of `_run_phase` completes promptly even if the
moderator task can never finish:

```python
try:
    moderator_ok = await asyncio.shield(moderator_task)
except asyncio.CancelledError:
    if not moderator_task.done():
        moderator_task.cancel()
    await timeouts.await_cancellation_grace((moderator_task,))
    raise
```

`asyncio.shield`'s outer future completes immediately on cancellation, so the
cancelling `_run_phase` is woken right away; the existing guarantee that
`moderator_task` is explicitly cancelled and bounded by the same
`await_cancellation_grace` is retained. Normal completion is unchanged (the
shield resolves with the task's result).

### Explicitly unchanged (mission boundaries)

- `_run`'s `except asyncio.CancelledError` handler (registry.py) — untouched.
- `aiter_with_deadline` implementation — untouched by design; the fix lives
  at the cleanup layer, which is where the race actually is.
- `SEAT_TIMEOUT_SECONDS = 300` / `RUN_TIMEOUT_SECONDS = 600` backstops.
- Guardrails output-cap logic, thresholds, and event shapes.
- No new dependencies; no frontend changes.

## Deterministic Test Confirmation

New file `backend/tests/test_modelmix_cancel_race.py` (8 tests). Instead of
racing timing, every test **constructs the failure condition directly**: a
`StallOnCancelProvider` fake that emits one delta, then either absorbs the
`CancelledError` and holds on a gate event or simply never advances — both
keep the seat/moderator task pending well beyond the grace period. A
`release` event lets the test drain the stray afterwards, so no test leaks a
pending task onto the event loop.

The stalled-task assertion itself is timing-independent structure: terminal
`run_cancelled`, `reason is None`, no `run_failed`/`run_completed`, no
`"timeout"` in the serialized journal, `run.status == "cancelled"`, and the
stall provider's `stream_finished` marker **unset at the moment the run is
terminal** — proving the task was abandoned mid-stream rather than raced to
completion. Wall-clock upper bounds (`< 8.0s` with the real 5.0s grace) are a
secondary guard, and fast-cancel regressions assert `< 3.0s`.

| Test | Proves |
|---|---|
| `test_module_cancel_grace_constant_is_explicit` | `CANCEL_GRACE_SECONDS == 5.0` |
| `test_grace_helper_returns_immediately_when_tasks_finish_or_none` | helper short-circuits done/empty inputs |
| `test_grace_helper_stops_after_grace_for_a_stubborn_task` | helper abandons a stubborn task at the bound |
| `test_one_slow_to_cancel_seat_reaches_run_cancelled_within_grace` | criterion **1** (one slow seat + one normal) |
| `test_both_seats_slow_to_cancel_still_terminal_cancelled` | criterion **2** (both seats slow) |
| `test_prompt_cancel_regression_is_completely_unchanged` | criterion **3** (both honor cancel promptly) |
| `test_moderator_slow_to_cancel_reaches_run_cancelled_within_grace` | criterion **5** (Moderator path determined + fixed) |
| `test_moderator_prompt_cancel_regression` | Moderator fast-cancel unchanged |

Criterion **4** (cancel never mislabeled timeout) is asserted structurally by
the terminal contract in every grace test.

Two historical hang causes found during development were test-harness bugs in
earlier drafts (a `while True` re-hang in the stall fake and a leaked pending
task in the grace-helper test), each of which stalled the pytest loop teardown
— both fixed; the final 8-test file completes in **11.98s** observed with zero
leaks.

## Evidence / Validation (raw outputs observed)

### New file

```text
uv run pytest backend/tests/test_modelmix_cancel_race.py -v
8 passed in 11.98s
```

### Targeted acceptance subset (alpha + streaming + timeouts + journal + moderator + cancel)

```text
uv run pytest backend/tests/test_modelmix_alpha_acceptance.py \
  backend/tests/test_modelmix_streaming.py \
  backend/tests/test_modelmix_timeouts.py \
  backend/tests/test_modelmix_journal.py \
  backend/tests/test_modelmix_moderator.py \
  backend/tests/test_modelmix_cancel_race.py -q
57 passed in 16.54s
```

### Full backend suite

```text
uv run pytest backend/tests -q
403 passed in 27.94s   (395 prior + 8 new; no existing test modified)
```

### Frontend (unchanged baseline, re-asserted; `npm.cmd` because PS blocks `npm.ps1`)

```text
npm test       12 files / 118 tests passed
npm run build  built in 1.70s
npm run lint   eslint . — clean
```

### Diff scope (before commit)

```text
git status --short →
  M backend/modelmix/orchestrator.py
  M backend/modelmix/registry.py
  M backend/modelmix/timeouts.py
  ?? backend/tests/test_modelmix_cancel_race.py
```

## Remaining Risks / Open

- **Abandoned-stray residual:** a provider that ignores cancellation forever
  leaves its seat task parked until loop/GC cleanup. This is deliberately
  preferred over the previous indefinite `active` run; the 600s run-timeout
  backstop still holds. No force-kill mechanism was added because the provider
  boundary does not offer a safe one.
- The item-33 alpha gate is **not declared met here**; per mission rules that
  declaration is left to the next verification pass. UI-bound checklist items
  (launch, three panels, configure) still rely on prior-mission evidence plus
  a final live-provider manual launch.
- `asyncio.shield` usage is new to this codebase; covered by the Moderator
  slow-to-cancel and fast-cancel regression tests, and semantically confined to
  the moderator await introduced here.

## Acceptance Criteria → Where Covered

1. One slow-to-cancel seat + one normal → `run_cancelled` bounded (<8s) — `test_one_slow_...`.
2. Both seats slow → same bounded outcome — `test_both_seats_slow_...`.
3. Prompt-cancel regression completely unchanged — `test_prompt_cancel_regression_...`.
4. Cancel never mislabeled timeout — structural `"timeout" not in journal` assertion in every grace test.
5. Moderator path determination (analogous, fixed via shield) with its own test — `test_moderator_slow_...` + `test_moderator_prompt_cancel_regression`.
6. Full existing suite passes with only new tests — 403 passed, no existing test modified.