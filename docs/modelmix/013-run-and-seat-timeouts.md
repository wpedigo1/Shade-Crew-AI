# Mission 013 — Run and Seat Timeouts

Route: Big Pickle (OpenCode Zen)
Punch Board items: 17 (partial), 9 (partial), 16
Base: `main` @ `e50ba80`
Date: 2026-08-29
Result: **PASS (LOCAL)**

## Objective

Give ModelMix its own wall-clock enforcement so a worker seat, the Moderator,
and the whole run cannot run forever — terminating honestly through the existing
event vocabulary plus an explicit `reason`, with no new SSE event types, no
persistence schema change, and no late journal or persistence writes after a run
goes terminal.

## Delivered

- **`backend/modelmix/timeouts.py`** — ModelMix-owned `SEAT_TIMEOUT_SECONDS = 300`,
  `RUN_TIMEOUT_SECONDS = 600`, and `aiter_with_deadline`, one cumulative
  wall-clock deadline helper. Python 3.10 compatible (`asyncio.timeout()` is 3.11+
  and is not used); every element waits at most the time remaining on the deadline.
- **`orchestrator.py::run_seat`** — each worker seat is bounded. Streaming is
  wrapped by `aiter_with_deadline`; non-streaming `provider.query` by
  `asyncio.wait_for`. Expiry emits the existing `seat_failed` event with
  `reason: "timeout"` and `error: "Worker timed out after N seconds"`. Explicit
  cancel keeps `seat_cancelled` (and re-raises); generic failures keep the
  existing path. The `except asyncio.TimeoutError` branch sits before the generic
  `Exception` branch (correct on Python 3.10, where `asyncio.TimeoutError` is a
  distinct `Exception` subclass).
- **`moderator.py::run_moderator`** — the Moderator phase gets the same seat
  bound and emits `moderator_failed` with `reason: "timeout"` on expiry.
  `CancelledError` is re-raised explicitly, so an explicit cancel during
  Moderator still produces the existing `run_cancelled` outcome and never a
  `moderator_failed` event.
- **`registry.py`** — `RunRegistry` accepts `seat_timeout` / `run_timeout`
  (default `None` → the live module constants). `_run` now wraps `_run_phase` in
  `asyncio.wait_for`. On run expiry `wait_for` cancels the phase, which cancels
  and gathers the outstanding seat tasks, then `_run` emits `run_failed` with
  `reason: "timeout"` and marks the run failed. On explicit cancel the outer
  cancellation still yields `run_cancelled` / status `cancelled` — never a
  timeout label.
- **No-late-writes invariant** — seat tasks only ever `put` into the local queue;
  the multiplex drain loop is the single journal writer. On run timeout or
  explicit cancel the drain is cancelled, so a seat's final `seat_cancelled` sits
  in the undrained queue and is dropped rather than appended after a terminal
  event. Journal and durable session both verified stable after terminal.

All timeout values are read from `backend/modelmix/timeouts.py` module constants
live at call time, so the module defaults (300/600) are the shipped contract and
tests override per-call with small values. A timed-out seat routes through the
existing one-failed-worker partial path, so the Moderator phase still runs with
the surviving worker's output.

### Boundaries respected

Backend only. Reuses the existing event types `seat_failed`, `moderator_failed`,
`run_failed` plus the `reason` field seam already used for
`reason: "backend_restart"` — no new SSE event types, no `schema_version`
change, no persistence public-interface change. `history.py`, replay, and
reconnect are untouched. Explicit cancellation semantics are unchanged.
No settings UI, telemetry, or token caps. Wall-clock only.

## Acceptance Coverage

Eleven tests were added in `backend/tests/test_modelmix_timeouts.py`; existing
tests run unmodified.

1. `test_module_timeout_constants_are_explicit` — constants are 300 and 600.
2. `test_seat_timeout_emits_seat_failed_with_reason_timeout` — a seat exceeding
   the bound emits `seat_failed` with `reason: "timeout"`; peer completes; run
   completed partial. (Acceptance 1.)
3. `test_seat_timeout_keeps_prior_deltas_and_peer_survives` — deltas emitted
   before the timeout remain in the journal and the other worker is unaffected.
   (Acceptance 2 + 3.)
4. `test_timed_out_seat_reaches_moderator_with_survivor_and_persists_partial_failure`
   — registry + persistence integration: the timed-out seat still reaches the
   Moderator with the surviving worker's output; the Moderator handoff shows
   `Unavailable because the worker failed.` and never sees the timed-out seat's
   partial content as complete; the persisted session records the timed-out
   seat's partial content with status `failed` and an error naming the timeout.
   (Acceptance 4 + 6.)
5. `test_run_timeout_cancels_seats_and_emits_run_failed_with_reason_timeout` —
   run bound: `run_failed` with `reason: "timeout"` is last, both outstanding
   seats were cancelled, no `seat_cancelled` is appended after terminal, sequences
   are contiguous, and the prior `seat_started` events remain. (Acceptance 5.)
6. `test_no_events_append_after_run_reaches_terminal` — after terminal plus a
   0.3s pause the journal is identical, the persisted document is identical, and
   `latest_seq` is stable. (Acceptance 9.)
7. `test_explicit_cancel_is_run_cancelled_and_never_labeled_timeout` — explicit
   cancel produces `run_cancelled`, never `run_failed`, and the string `timeout`
   appears nowhere. (Acceptance 7.)
8. `test_normal_run_emits_unmodified_canonical_sequence` — a normal run produces
   exactly the 11 canonical events (run, 2× seat, moderator, completion) with
   contiguous sequences and no `reason` keys. (Acceptance 8.)
9. `test_moderator_timeout_emits_moderator_failed_with_reason_timeout` —
   `run_moderator` emits `moderator_failed` with `reason: "timeout"` and returns
   `False`.
10./11. `test_seat_timeout_defaults_to_live_module_constant` and
   `test_run_timeout_defaults_to_live_module_constant` — monkeypatched module
   constants apply live when no explicit override is given.

No test sleeps for a real timeout and no single test exceeds ~0.5s.

## Validation

Command (repo root, with the documented workspace-local `TEMP`/`TMP` workaround
for the unreadable `pytest-of-wpedigo` root):

```text
uv run pytest backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py backend/tests/test_modelmix_history.py -q
```

Raw unedited output:

```text
.................................................                        [100%]
49 passed in 3.21s
```

New timeouts coverage, verbose:

```text
test_module_timeout_constants_are_explicit PASSED
test_seat_timeout_emits_seat_failed_with_reason_timeout PASSED
test_seat_timeout_keeps_prior_deltas_and_peer_survives PASSED
test_seat_timeout_defaults_to_live_module_constant PASSED
test_timed_out_seat_reaches_moderator_with_survivor_and_persists_partial_failure PASSED
test_run_timeout_cancels_seats_and_emits_run_failed_with_reason_timeout PASSED
test_run_timeout_defaults_to_live_module_constant PASSED
test_no_events_append_after_run_reaches_terminal PASSED
test_explicit_cancel_is_run_cancelled_and_never_labeled_timeout PASSED
test_normal_run_emits_unmodified_canonical_sequence PASSED
test_moderator_timeout_emits_moderator_failed_with_reason_timeout PASSED
```

```text
.......................................                                [100%]
11 passed in 2.52s
```

Command:

```text
uv run ruff check backend/modelmix/timeouts.py backend/modelmix/orchestrator.py backend/modelmix/moderator.py backend/modelmix/registry.py backend/tests/test_modelmix_timeouts.py
```

Raw unedited output:

```text
All checks passed!
```

Command:

```text
uv run pytest backend/tests -q
```

Raw unedited output:

```text
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 61%]
........................................................................ [ 81%]
................................................................         [100%]
352 passed in 12.26s
```

Command (from `frontend/`):

```text
npm test && npm run build && npm run lint
```

Raw unedited output:

```text
> the-ai-counsel@0.11.4 test
> vitest run

 RUN  v4.1.11 C:/Users/wpedi/ModelMix/frontend

 ✓ src/utils/fontSize.test.js (3 tests) 3ms
 ✓ src/configuredModels.test.js (3 tests) 11ms
 ✓ src/modelmixState.test.js (29 tests) 28ms

 Test Files  3 passed (3)
      Tests  35 passed (35)
   Start at  22:47:15
   Duration  249ms
```

```text
> the-ai-counsel@0.11.4 build
> vite build

vite v7.3.6 building client environment for production...
transforming...
✓ 433 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.04 kB │ gzip:  0.54 kB
dist/assets/ollama-DE2Cu6-_.svg                4.78 kB │ gzip:  2.24 kB
dist/assets/ModelMixObserver-QQz_hUhO.css      3.23 kB │ gzip:  1.06 kB
dist/assets/LandingPage-CqcwYOwM.css           5.72 kB │ gzip:  1.55 kB
dist/assets/index-BBDNWvSr.css               16.09 kB │ gzip:  4.04 kB
dist/assets/Settings-C_CQ48Qz.css             34.71 kB │ gzip:  6.63 kB
dist/assets/ChatInterface-CUo4Eqg3.css       105.01 kB │ gzip: 17.15 kB
dist/assets/LandingPage-D0cj4OEw.js            4.86 kB │ gzip:  1.18 kB
dist/assets/opencode-D5BbqXFQ.js               9.07 kB │ gzip:  3.39 kB
dist/assets/ModelMixObserver-wnfuGQ0T.js      14.48 kB │ gzip:  5.00 kB
dist/assets/Settings-CYEkTPcy.js              93.38 kB │ gzip: 23.05 kB
dist/assets/ChatInterface-GncriZ-q.js        102.03 kB │ gzip: 26.24 kB
dist/assets/index-dLSmgDJe.js                235.98 kB │ gzip: 72.17 kB
dist/assets/SearchableModelSelect-N2vPgmtO.js 247.89 kB │ gzip: 79.35 kB
✓ built in 1.63s
```

```text
> the-ai-counsel@0.11.4 lint
> eslint .
```

### Observed during development (now resolved)

- The first collection of the focused suites failed with an
  `IndentationError` in `registry.py` caused by my `_run`/`_run_phase`
  edit (the method lost its class indentation). Fixed, verified with an
  `ast.parse` check, and the focused suites then passed clean.
- The initial run-timeout test flagged a wording mismatch: the run error read
  `Run exceeded 0.5 seconds timeout` while the seat/moderator messages read
  `...timed out after N seconds`. The run error was aligned to
  `Run timed out after N seconds` for consistent honest wording, and the suite
  passed 11/11 on re-run.
- `git` emits the pre-existing LF-to-CRLF working-copy warnings on touched
  text files; they are noise and were ignored.

## Git Diff Stat

Working tree was fully staged at capture, so the unstaged `git diff --stat` was
empty; the staged diff is shown (Git also emits the existing LF-to-CRLF
working-copy warnings).

Command:

```text
git diff --cached --stat
```

Raw unedited output (captured after staging the full deliverable, including
this report):

```text
 backend/modelmix/moderator.py              |  22 +-
 backend/modelmix/orchestrator.py           |  20 +-
 backend/modelmix/registry.py               | 189 +++++++++------
 backend/modelmix/timeouts.py               |  33 +++
 backend/tests/test_modelmix_timeouts.py    | 355 +++++++++++++++++++++++++++++
 docs/modelmix/013-run-and-seat-timeouts.md | 270 ++++++++++++++++++++++
 docs/modelmix/ENGINEERING-PROGRESS.md      |  30 ++-
 docs/modelmix/MISSION-INDEX.md             |  18 ++
 docs/modelmix/PUNCH-BOARD.md               |  22 +-
 docs/modelmix/README.md                    |   1 +
 10 files changed, 868 insertions(+), 92 deletions(-)
```

## Punch Board Mapping

- **Item 17 — spend/runtime guardrails (partial):** ModelMix now enforces its own
  run (600s) and seat/Moderator (300s) wall-clock bounds with honest timeout
  outcomes. Stop, the turn cap, and seat-history budgets existed before.
  Cost/token ceilings and output warning/hard-cap work remain open.
- **Item 9 — run state machine (partial):** `run_failed`,
  `seat_failed`, and `moderator_failed` with `reason: "timeout"` are now honest,
  distinct wall-clock terminal outcomes; retries and the full state contract
  remain open.
- **Item 16 — failure + cancellation:** timeouts now share the same loop and
  cancellation machinery as worker/Moderator failure and explicit cancellation,
  with a proven no-late-writes guarantee.