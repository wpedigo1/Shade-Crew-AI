# Mission 051 — Spend Warning Rendering (Frontend)

Date: 2026-09-02 CT · Base: main @ `9761092` (Mission 050)

## What changed

Frontend-only. Mission 050 already emits real `seat_cost_warning` /
`moderator_cost_warning` events carrying `{cost_usd, threshold}`; this mission
captures and renders them. No backend file touched.

### `frontend/src/modelmixState.js`

- On `seat_cost_warning`: `seat.costWarning = { cost_usd: event.cost_usd, threshold: event.threshold }`
  (worker branch, mirroring the `seat_output_warning` → `seat.outputWarning`
  set exactly).
- On `moderator_cost_warning`: `moderator.costWarning = { cost_usd, threshold }`
  (moderator branch, same style).

### `frontend/src/seatTelemetry.js`

- `buildSeatTelemetry` adds a footer item only when `seat.costWarning` has a
  real finite `cost_usd` and `threshold` (guarded via the existing
  `formatCostUsd`, which returns `null` for non-finite/non-number): label
  `Cost notice`, value `"$<cost> (above $<threshold> notice threshold)"`.
  Both figures reuse the existing `formatCostUsd` (Mission 045) — no second
  formatter — so sub-cent values render with four decimals and never as a
  misleading `$0.00`. Tone is plain/informational, matching the existing
  output-warning row; no color/alarm styling.

### Scope (live-only)

`costWarning` is deliberately NOT added to `createModelMixState`'s
persisted/history shapes, `hydrateModelMixState`, `buildHistoryEntry`, or
`archiveCurrentRun` — exactly matching `outputWarning`'s established
Mission 018 deferral.

## Boundaries honored

- No backend change.
- No `costWarning` in hydration/history/archive shapes.
- No new formatting function — reused `formatCostUsd`.
- No color-coded alarm styling.
- No new dependency.

## Tests

`modelmixState.test.js` (+5): a `seat_cost_warning` sets that seat's
`costWarning` and never the peers or moderator; a `moderator_cost_warning`
sets only the moderator (isolation); `costWarning` stays live-only and never
leaks into `archiveCurrentRun` history/outgoing entries; hydration never
invents `costWarning` on live seats or history even when persisted `cost_usd`
exists; a seat that warns then completes keeps the truthful warning alongside
finish.

`seatTelemetry.test.js` (+4): a valid `costWarning` renders a `Cost notice`
row with correctly formatted currency (two decimals at/above a cent,
including the `$0.10` threshold); a sub-cent value renders with four decimals
(explicitly asserted NOT `$0.00`); no `costWarning` renders no row; a
`costWarning` with missing/non-numeric/incomplete values renders no row.

## Validation (observed)

- `cd frontend && npm test` → **166 passed** (16 files; 157 prior + 9 new).
- `npm run build` → built clean; `npm run lint` → clean.
- `uv run pytest backend/tests -q --basetemp=...` → **525 passed** (backend
  unchanged; `--basetemp` is the established workaround for the known
  pre-existing `pytest-of-wpedigo` ACL `WinError 5`).

## Doc updates

- `PUNCH-BOARD.md` item 17 → Mission 051 added; spend visibility work now
  complete end to end; enforcement/cutoff and cumulative session-cost
  tracking remain explicitly separate, undecided future work.
- `MISSION-INDEX.md` (row + result), `ENGINEERING-PROGRESS.md` (result).

## Remaining risks / open items

- Enforcement/cutoff (what happens when a dollar budget is exceeded) remains
  an explicitly undecided product question.
- Cumulative/session-total cost tracking is a separate, undecided feature.
- The cost warning is live-only by design (Mission 018 deferral), matching
  `outputWarning`.