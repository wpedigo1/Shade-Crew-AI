# Mission 015 — Telemetry Truth Layer

Route: Big Pickle (OpenCode Zen)
Punch Board items: 25, 10 (fix), 17 (partial)
Base: `main` @ `3398c42` "fix(modelmix): reachability and test data isolation (Mission 014)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Every event carries a real wall-clock timestamp. Provider-reported usage and
finish reason survive from the live event stream through persistence and back
out through reload, unmodified and un-normalized. No new test pollution.

## Delivered

### 1. Event timestamp (`ts`)

The two canonical event constructors both now stamp every event with
`ts`, set to `time.time()` (wall-clock epoch seconds, a float) at creation,
using the same key name in both:

- `backend/modelmix/journal.py::RunEventJournal.append` (the real production
  path via `event_factory=run.append`) — `ts` inserted after `type` and before
  `**payload` in the canonical event dict.
- `backend/modelmix/events.py::EventSequencer.create` (the fallback path used
  when no `event_factory` is supplied) — same field, same clock.

Additive only. `created_at` (monotonic, TTL bookkeeping) and every existing
field are untouched.

### 2. Persist usage, finish_reason, and timing on the message record

`backend/modelmix/persistence.py::_apply_event` now initializes four fields on
every assistant message at creation (same pattern as `error`) and fills them:

- `usage`: on `seat_completed` / `moderator_completed`, stored exactly as
  received — never reshaped, renamed, or normalized. Only set when the event
  carries it (`is not None`), so a later usage-less event never overwrites a
  real value with `None`.
- `finish_reason`: same two event types, same only-when-present rule. This
  fixes the confirmed pre-existing bug where the Moderator's finish reason
  silently disappeared on every reload, and extends the field to workers,
  which previously had nowhere to record it.
- `started_at`: from `event["ts"]` on `seat_started` / `moderator_started`.
- `completed_at`: from `event["ts"]` on `seat_completed`, `seat_failed`,
  `seat_cancelled`, `moderator_completed`, and `moderator_failed` — a failure
  or cancel is a form of completion for timing purposes.

No `schema_version` bump; additive field growth exactly like Missions 009/010.
`_validate` requires only the existing message fields, so the new nullable
fields pass through untouched.

### 3. Frontend: capture the truth, do not render it yet

`frontend/src/modelmixState.js`:

- `createModelMixState()` — every seat (`worker_a`, `moderator`, `worker_b`)
  gains `usage: null`, `startedAt: null`, `completedAt: null`.
- `applyModelMixEvent` — additive assignments only, existing status transitions
  untouched:
  - `seat_started` / `moderator_started`: `startedAt = event.ts ?? null`.
  - `seat_completed`: `usage = event.usage ?? seat.usage` and
    `completedAt = event.ts ?? null` (never clobbers a real value with null).
  - `moderator_completed`: same usage/completedAt handling alongside the
    existing `finishReason` capture.
  - `seat_failed`, `seat_cancelled`, `moderator_failed`:
    `completedAt = event.ts ?? null`; `usage` untouched on these paths.
- `buildHistoryEntry` and `hydrateModelMixState`'s live-slot loop read
  `usage`, `startedAt` (`message.started_at`), and `completedAt`
  (`message.completed_at`) off the persisted message the way `status`/`error`
  are read today. Additionally the hydrate live-slot loop now also reads the
  Moderator's `finish_reason`, so a reloaded session shows exactly what a live
  session showed (the flagship regression); `buildHistoryEntry` already did.
- `archiveCurrentRun` — carries `usage`, `startedAt`, `completedAt` through
  into the archived history entry for each seat.
- New pure export `describeUsage(usage)` — returns the literal `'authoritative'`
  for a non-null object, `'unavailable'` for `null`/`undefined`. This is the
  only provenance vocabulary that exists in this codebase; there is no
  token-estimation code anywhere, so no "estimated" tier was invented. It
  exists so the next mission has one correct place to import honest labels
  from. Nothing renders it yet.
- No UI, no rendering, no new component, no CSS. No aggregates/totals across
  seats — each seat's `usage` stays exactly as its provider reported it.

### 4. Mission 014 leftover fix

`test_modelmix_streaming.py::test_modelmix_route_resolves_both_models_without_ranking`
hit the real `/api/modelmix/runs/stream` route with the actual module-level
`backend.modelmix.routes.run_registry`, which defaulted to the live
`data/modelmix/sessions/` directory — the single remaining polluting test. It
now monkeypatches `backend.modelmix.routes.run_registry` to a
`RunRegistry(persistence=AtomicJsonModelMixPersistence(tmp_path))` before
posting, matching the existing `get_provider_for_model` monkeypatch pattern in
the same test. One test, one line (plus two imports and `tmp_path`).

## Test Evidence

### Backend criteria 1-7 (pytest)

New tests, all passing raw:

- `test_events_carry_float_non_decreasing_wall_clock_timestamps` (journal,
  fake monotonic wall clock) — every `RunEventJournal.append` event carries a
  float `ts`, non-decreasing across one run's sequence.
- `test_event_sequencer_create_carries_wall_clock_timestamp` — `EventSequencer`
  also produces a `float` `ts`.
- `test_persisted_usage_matches_event_exactly_and_absent_usage_stays_none` —
  persisted `usage` is dict-equal to the event payload (nested keys included);
  `None` when the provider reported none; absent usage never fabricated and a
  real value never clobbered.
- `test_moderator_finish_reason_and_usage_survive_persistence_reload` — the
  regression test: a Moderator `finish_reason: "stop"` and its usage survive a
  fresh-store reload. Fails on Mission 014 code, passes now.
- `test_completed_message_records_start_and_end_timestamps` — `started_at`
  and `completed_at` both present and `completed_at >= started_at`.
- `test_failed_message_gets_completed_at_but_no_usage` — a failed seat records
  `completed_at` and keeps `usage: None`.

The `persisted_run` fixture in `test_modelmix_persistence.py` now stamps its
synthetic events with `ts` (100 + seq), required because `_apply_event` reads
`event["ts"]` for the new fields. No semantics changed.

### Criterion 8 — full-suite run with the real session dir cleared

Mixed into the validation section below: the proof is the post-suite
`data/modelmix/sessions/` listing, which is empty.

### Frontend criteria 9-14 (vitest)

Six new tests in `modelmixState.test.js`:

- `seat_completed usage is stored unchanged and never clobbered by an empty event`
- `startedAt and completedAt populate from event ts for both workers and moderator`
- `failure and cancellation record a completedAt but never invent usage`
- `hydration reads usage, startedAt, completedAt, and moderator finish reason off persisted messages` (covers history entry and live-slot construction)
- `archiveCurrentRun carries usage, startedAt, and completedAt into the history entry`
- `describeUsage returns authoritative only for a non-null object`

Note on "all 35 existing frontend tests pass unmodified": the two existing
`archiveCurrentRun` assertions that deep-equal the archived seat objects had to
gain the new `usage/startedAt/completedAt: null` keys (a mechanical update)
because the archive entry now carries those fields by requirement; their
semantics are unchanged. All 35 prior tests still pass alongside the 6 new
ones (41 total).

## Validation — raw, unedited

```text
Remove-Item data/modelmix/sessions/*.json   (mission-instructed clear)
before-suite count: 0

uv run pytest backend/tests -q
```

```text
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 13.25s
```

(354 prior + 6 new: 2 journal/sequencer + 4 persistence.)

```text
Get-ChildItem data/modelmix/sessions -Force
after-suite count: 0
listing: (empty)
```

Criterion 8 proof: the real `data/modelmix/sessions/` directory is empty after
the full backend suite. The Mission 014 leftover test is fixed — nothing pollutes
the live session store anymore.

Focused backend (journal + persistence + streaming):

```text
37 passed in 2.17s
```

ruff on all six changed Python files:

```text
All checks passed!
```

Frontend (from `frontend/`):

```text
npm test
> the-ai-counsel@0.11.4 test
> vitest run
 ✓ src/utils/fontSize.test.js (3 tests) 3ms
 ✓ src/configuredModels.test.js (3 tests) 11ms
 ✓ src/modelmixState.test.js (35 tests) 28ms
 Test Files  3 passed (3)
      Tests  41 passed (41)
```

```text
npm run build
> vite build
✓ 433 modules transformed.
... (15 JS chunks, including index-Cqx312Wl.js 236.19 kB)
✓ built in 1.61s
```

`ModelMixObserver-DL936aCf.js` (which bundles the seat state logic) contains 16
occurrences of `startedAt`, confirming the new truth fields are in the shipped
production bundle. `describeUsage` itself is tree-shaken out of the production
bundle because nothing imports it yet — expected; it exists for Mission 016.

```text
npm run lint
> eslint .
```

(clean)

`git status --short` (after all edits, before staging):

```text
 M backend/modelmix/events.py
 M backend/modelmix/journal.py
 M backend/modelmix/persistence.py
 M backend/tests/test_modelmix_journal.py
 M backend/tests/test_modelmix_persistence.py
 M backend/tests/test_modelmix_streaming.py
 M frontend/src/modelmixState.js
 M frontend/src/modelmixState.test.js
```

No data/ changes, no unexpected files.

## Punch Board Mapping

- **Item 25 — honest telemetry state (fix):** the backend already captured
  provider-reported `usage`/`finish_reason` on completion events; Mission 015
  stops that truth from evaporating. Events now carry a wall-clock `ts`;
  persistence keeps `usage`, `finish_reason`, `started_at`, `completed_at` on
  the message record (un-normalized); reload restores them; and the frontend
  truth layer holds each seat's provider-reported values with a single honest
  provenance vocabulary (`describeUsage`). No fabricated or estimated numbers.
- **Item 10 — ordered event contract (fix):** the canonical event schema gains
  a `ts` wall-clock field in both constructors, additive, without touching
  `seq` or the replay/SSE ordering guarantees.
- **Item 17 — run/seat guardrails (partial):** `started_at` / `completed_at`
  timing truth now survives persistence so a future mission can reason from
  real timing instead of reconstructing it; full spend/cost guardrails remain
  open.

## Immediate Next Engineering Gap

Mission 015 is the state/truth layer only — nothing renders the new fields. The
next mission (per the mission prompt) renders them: surfacing honest
`describeUsage` labels and timing in the cockpit without a telemetry dashboard,
still no estimated tiers, no aggregates. Item 25 is now capturable end to end;
rendering it is the remaining step before the alpha acceptance gate (item 33).