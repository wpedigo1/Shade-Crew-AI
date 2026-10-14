# Mission 019 — Output Guardrails, Backend Enforcement

Route: Big Pickle (OpenCode Zen)
Punch Board items: 17 (new — output warning + hard cap)
Base: `main` @ `38f9fd9` "fix(modelmix): show provider-reported token totals in telemetry usage detail"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Bound how much a single Worker A / Worker B / Moderator turn can generate in
one live streaming turn in the backend run path: a one-shot informational
output warning at a first crossing threshold plus a hard output cap that stops
consuming the provider stream, truncates deterministically to the exact cap,
and reports a ModelMix-owned terminal outcome — `finish_reason:
"modelmix_output_cap"` — that is honestly distinct from provider termination
(`stop`, `length`, `content_filter`, …), failure, timeout, and user
cancellation. Constants are module-level provisional defaults only; no
settings/configurability is introduced. This mission lives in the same live
streaming loop as Mission 013's timeouts, so truncation boundaries and event
ordering (criteria 3, 4, 7) are the highest-risk parts.

## Delivered

### 1. `backend/modelmix/guardrails.py` (new)

Single source of truth for the bounds:

- `WARNING_OUTPUT_THRESHOLD_CHARS = 20_000`
- `HARD_OUTPUT_CAP_CHARS = 40_000`
- `clip_delta(delta, emitted, cap)` — clips one stream delta so the cumulative
  emitted length never exceeds `cap`; returns `(delta_to_emit, capped)` where
  the clipped delta lands the cumulative total **exactly** on `cap` when the
  producer would have gone over, and `capped=True` exactly when the budget is
  exhausted so callers stop consuming the stream.

**Both constants are provisional defaults pending a later configurability
(settings) mission. They are not user-configurable here.** The documented
provider-quota guardrail (warn/limit against account usage) is explicitly
**deferred and not honestly buildable**: no provider quota or rate-limit data
exists anywhere in this codebase, so comparing output against it would be a
fabricated number. Nothing estimates, percentages, or normalizes it.

### 2. `orchestrator.py::run_seat` — worker enforcement

Cumulative length is tracked off the same `text_delta` char runs that land in
the persisted message `content`, for both the streaming and non-streaming
branches:

- **Warning:** the FIRST time cumulative length reaches `WARNING_OUTPUT_THRESHOLD_CHARS`,
  exactly one `seat_output_warning` event is emitted per seat with payload
  `{chars: <cumulative_int>, threshold: <threshold>}`. It is emitted after the
  delta that caused the crossing, so `chars` equals the actual cumulative
  output at that point and is reconstructable from replay. It is informational
  only: it stops nothing and does not touch the multiplexer's `terminal_seats`
  bookkeeping (it is not in the terminal-event set).
- **Hard cap:** when the next delta would push the cumulative length past
  `HARD_OUTPUT_CAP_CHARS`, the delta is clipped via `clip_delta` so content
  lands at exactly the cap; the final truncated `seat_delta` is emitted, the
  provider stream is no longer consumed (`break`), and `seat_completed` (not
  `seat_failed`) is emitted with `finish_reason: "modelmix_output_cap"`.
  Provider `finish_reason`/`usage` are simply not collected after the break
  (never collides with real provider reasons; no fake usage).
  Because the capped seat *completes* rather than fails, the run's final
  status stays `completed` — a hard cap is a clean ModelMix termination, not a
  failure.
- **Non-streaming path** (`provider.query`): if the full returned content
  exceeds the cap it is truncated to exactly the cap before the single
  `seat_delta`; `finish_reason` is `modelmix_output_cap` on `seat_completed`. No
  `seat_output_warning` is emitted on this path (there is no incremental
  stream to warn mid-run).
- **Interactions:** output cap and wall-clock timeout stay independent —
  whichever is reached first governs, and a capped seat is never also reported
  timed out (the stream break exits the `async for` ahead of the deadline).
  User cancellation (`seat_cancelled`/`run_cancelled`) is untouched. A seat
  that never reaches either threshold produces byte-identical behavior to the
  pre-guardrail path.

### 3. `moderator.py::run_moderator` — identical mechanism

The Moderator receives the same treatment with the same module constants:
`moderator_output_warning` (one-shot, `chars`/`threshold`, payload carries
`actor="moderator"`), exact-cap clipping, stop consuming the stream, and
`moderator_completed` with `finish_reason: "modelmix_output_cap"`. The same
rules apply to its non-streaming query branch. The pre-existing
`ModeratorOutputLimits` preview dataclass (`warning_threshold_tokens` /
`hard_cap_tokens`, token-shaped) and its existing "unsupported hard cap raises
ValueError" contract are **unchanged** — that is a separate, still-unsupported
public contract; the guardrails mission wires enforcement and payloads through
the module constants, not that knob.

### 4. Boundaries preserved — no-edit files

- `events.py`, `persistence.py`, `journal.py`, `timeouts.py`, `history.py`:
  byte-identical. New event types flow through the existing
  `EventSequencer.create` / `RunEventJournal.append` constructors (both accept
  arbitrary type strings) and `_apply_event` already handles an unrecognized
  seat event as a no-op, so the warning events append to `run["events"]` and
  advance `latest_seq` without mutating message content/status/finish_reason.
- `registry.py`: untouched. The existing `_run_phase` consumes `seat_*`/
  `moderator_*` events and simply ignores the new warning events, which is the
  correct fan-in behavior (the Moderator still receives the bounded visible
  worker output because that content comes only from `seat_delta` events).
- Frontend: **zero changes.** `applyModelMixEvent` already advances
  `lastSeq`/`run_id` for any well-formed event and ignores unknown types, so
  the new events replay cleanly without frontend work. Frontend
  test/build/lint are still run in validation to prove no regression.

## Test Evidence

New file `backend/tests/test_modelmix_guardrails.py` (13 tests), using the
small-threshold-monkeypatch pattern from Mission 013's timeout tests
(`monkeypatch.setattr("backend.modelmix.guardrails.WARNING_OUTPUT_THRESHOLD_CHARS", 40)`,
cap 80, and a huge cap when only the warning is under test). Streaming seams are
exercised through `multiplex_workers` and `run_moderator` exactly like the
existing `test_modelmix_timeouts.py` / `test_modelmix_streaming.py` harnesses.

1. `test_seat_crossing_warning_threshold_emits_exactly_one_warning` — one
   `seat_output_warning`, `chars == 40`, `threshold == 40`, seat_id correct,
   ordered before the completion, and the seat still completes normally with
   the provider's `finish_reason` (`stop`). *(Criterion 1)*
2. `test_seat_below_warning_threshold_emits_no_warning` — zero
   `seat_output_warning`. *(Criterion 2)*
3. `test_hard_cap_truncates_stream_to_exact_cap_length` — deltas totaling
   120 chars clipped to exactly **80 chars** (`"a"*60 + "b"*20`); the joined
   `seat_delta` length asserts the exact boundary. *(Criterion 3)*
4. `test_capped_seat_terminates_completed_with_output_cap_finish` — the seat's
   terminal event is `seat_completed` (no `seat_failed`), with
   `finish_reason == "modelmix_output_cap"`, and the run completes with status
   `completed`, not `partial`. *(Criterion 4)*
5. `test_seat_under_both_thresholds_behaves_unchanged` — canonical
   `[seat_started, seat_delta, seat_delta, seat_completed]` sequence,
   provider `finish_reason` preserved, run `completed`. *(Criterion 5)*
6. Moderator treatment *(Criterion 6)*:
   - `test_moderator_crossing_warning_threshold_emits_exactly_one_warning`;
   - `test_moderator_crosses_warning_then_cap_in_order_with_completed_terminal`
     — full event sequence with the warning between deltas and the
     `modelmix_output_cap` completion terminal;
   - `test_moderator_under_thresholds_behaves_unchanged`.
7. `test_seat_crosses_warning_then_cap_in_order_with_cap_terminal` — exact
   worker_A sequence
   `[started, delta, delta, output_warning, delta, completed]`, `chars == 60`,
   joined output exactly 80 chars, exactly one warning, completion is
   `modelmix_output_cap`. *(Criterion 7)*
8. `test_timed_out_seat_emits_no_guardrail_events` — blocking seat with
   `seat_timeout=0.05` → `seat_failed` `reason: "timeout"`, no warning, no
   `modelmix_output_cap`; run `partial`. *(Criterion 8)*
9. `test_cancelled_seat_emits_no_guardrail_events` — disconnect-driven cancel
   → two `seat_cancelled`, no warning/cap events, no `run_completed`.
   *(Criterion 9)*
10. `test_non_streaming_over_cap_truncates_with_output_cap_finish` (delta is
    exactly `"z"*80`, completion carries `modelmix_output_cap`, no warning)
    and `test_non_streaming_under_cap_unaffected_and_no_warning` (delta
    untouched, usage passthrough, no finish_reason injected). *(Criterion 10)*

One test-only bug caught on the first run: the disconnect harness passed
`disconnect=` where `multiplex_workers` expects `is_disconnected=`; fixed in the
test. Implementation was already correct.

### Existing suites pass unmodified

Full backend suite observed: **373 passed** = 360 pre-existing + 13 new, no
existing test modified.

## Validation — raw, unedited

New tests:

```text
uv run pytest backend/tests/test_modelmix_guardrails.py -q
.............                                                            [100%]
13 passed in 0.78s
```

Targeted existing suites (persistence, journal, moderator, streaming, history,
timeouts):

```text
uv run pytest backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py backend/tests/test_modelmix_history.py backend/tests/test_modelmix_timeouts.py -q
..................................................................       [100%]
66 passed in 5.13s
```

Full backend suite:

```text
uv run pytest backend/tests -q
........................................................................ [ 19%]
........................................................................ [ 38%]
........................................................................ [ 57%]
........................................................................ [ 77%]
........................................................................ [ 96%]
.............                                                            [100%]
373 passed in 13.26s
```

Frontend (no changes; regression proof), from `frontend/`:

```text
npm test
 ✓ src/defaultSeatModels.test.js (5 tests) 6ms
 ✓ src/utils/fontSize.test.js (3 tests) 6ms
 ✓ src/configuredSources.test.js (5 tests) 7ms
 ✓ src/panelView.test.js (4 tests) 7ms
 ✓ src/seatTelemetry.test.js (14 tests) 11ms
 ✓ src/configuredModels.test.js (3 tests) 26ms
 ✓ src/modelmixState.test.js (35 tests) 54ms
 ✓ src/components/ModelMixTelemetry.test.jsx (3 tests) 177ms
 ✓ src/components/ModelMixObserver.test.jsx (6 tests) 388ms
 ✓ src/components/ModelMixSettings.test.jsx (8 tests) 437ms

 Test Files  10 passed (10)
      Tests  86 passed (86)

npm run build   (437 modules transformed, built in 1.68s)
npm run lint    (eslint . — clean)
```

`git status --short` (after all edits, before staging):

```text
 M backend/modelmix/moderator.py
 M backend/modelmix/orchestrator.py
 ?? backend/modelmix/guardrails.py
 ?? backend/tests/test_modelmix_guardrails.py
 ?? docs/modelmix/019-output-guardrails-backend.md
```

`git diff --stat` (before staging):

```text
 backend/modelmix/moderator.py    | 42 ++++++++++++++++++++++++++++-------
 backend/modelmix/orchestrator.py | 51 ++++++++++++++++++++++++++++++-----
```

No `data/`, no lockfile, no dependency, no frontend, no `events.py`/
`persistence.py`/`journal.py`/`timeouts.py`/`history.py`/`registry.py` changes.

## Punch Board Mapping

- **Item 17 — spend/runtime guardrails (new output-cap slice):** the hard
  output cap is no longer open. Both workers and the Moderator are bounded by
  the same exact-cap truncation with an honest, distinct terminal outcome
  (`finish_reason: "modelmix_output_cap"`), plus a one-shot informational
  `seat_output_warning`/`moderator_output_warning`. Terminal state now
  distinguishes: normal completion, user cancellation, provider/model
  termination (provider `finish_reason` pass-through), failure, timeout, and
  ModelMix hard-cap termination. Wall-clock timeouts (Mission 013), seat
  history budgets (Mission 010), and the output cap are independent bounds;
  whichever is reached first governs.
- **Item 17 — still open:** the provider/account usage warning (warn/limit
  against quota) is **not** wired because no authoritative quota or rate-limit
  data exists — comparing against it would fabricate a number. Configurability
  of the two output constants (toggles/thresholds in Settings) also remains a
  later mission; the constants are provisional defaults.

## Assumptions

- The output cap is a deterministic **prefix** cut at the exact cap length —
  the `_bounded_visible_text`/`_bounded_history_text` principle (hard char
  budget, deterministic, replay-safe) matched without reusing those input-side
  functions and without a marker that would break the exact-length guarantee.
- Capped output is counted in the same character units as the persisted
  message `content` (`str` length of each `text_delta`), keeping journal,
  persistence, and Moderator fan-in consistent.
- The warning event is emitted **after** the delta that crosses the threshold
  so its `chars` equals the live cumulative total at that point.
- `ModeratorOutputLimits` token-shaped preview contract is left untouched to
  preserve its existing unimplemented-knob behavior; enforcement uses module
  constants.

## Remaining Risks / Open

- Provisional thresholds: `20_000`/`40_000` chars are not yet configurable;
  a later Settings mission should move them behind controls.
- Provider quota/rate-limit usage warnings are deferred (no authoritative data
  to compare against); they must never be fabricated.
- The cap is enforced in the live seat/Moderator loop only; batch/replay and
  future non-Mix paths are out of alpha scope.
- Stream close on `break` is now explicit: the capped branch calls
  `guardrails.close_stream(stream)` (best-effort `aclose` when present), so
  provider streams are torn down deterministically instead of only via
  async-generator finalization. A stream without `aclose`, or one that errors on
  close, cannot disturb the capped terminal outcome (see Follow-up Fix below).
- No frontend rendering of the warning/cap events yet (unknown event types are
  correctly ignored); surfacing them in the cockpit is a deliberate later step
  and was explicitly out of scope for this backend mission.

## Follow-up Fix — explicit provider stream close on output cap

Immediately after the original Mission 019 close. Review pointed out that
breaking out of `aiter_with_deadline` did not deterministically close the
provider's own async stream — teardown relied on `GeneratorExit` at the
suspension point. Change: in `orchestrator.py::run_seat` and
`moderator.py::run_moderator`, the capped branch now calls a new
`guardrails.close_stream(stream)` helper before `break`. The helper calls
`aclose()` only when the stream exposes it, and swallows any close error so an
already-closed or teardown-failing provider stream never disturbs the
`modelmix_output_cap` terminal outcome. `except Exception` deliberately does not
catch `CancelledError`, so task cancellation still propagates.

Test impact: two new tests in `backend/tests/test_modelmix_guardrails.py` (one
per code file) — `test_capped_seat_closes_provider_stream` (via the seat/run
path) and `test_capped_moderator_closes_provider_stream` (via `run_moderator`).
Each drives a recorded `FakeStream`, a `BareStream` with no `aclose` attribute,
and a `FakeStream` that raises on close, via a `FakeStreamProvider` whose
`stream_query` returns the injected stream object directly. Validated from the
repo root:

```text
.venv\Scripts\python -m pytest backend\tests\test_modelmix_guardrails.py -q
15 passed in 0.80s

.venv\Scripts\python -m pytest backend\tests -q
375 passed in 13.11s   (373 prior + 2 new)

.venv\Scripts\ruff check backend\modelmix\guardrails.py backend\modelmix\orchestrator.py backend\modelmix\moderator.py backend\tests\test_modelmix_guardrails.py
All checks passed!
```

Frontend unchanged. Committed as a separate follow-up fix on `main`.