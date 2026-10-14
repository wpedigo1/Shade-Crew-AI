# Mission 045 — Cost Rendering (Frontend)

Date: 2026-09-02 CT · Base: main @ `2b1742e` (Mission 044) · Route: GLM 5.3 Flash

## What changed

Purely frontend. Mission 044 already computes, attaches, and persists a real
`cost_usd` for OpenRouter-routed seats; this mission surfaces it through the
established telemetry state lifecycle and footer rendering. No backend file
was touched.

### `frontend/src/modelmixState.js`

- `costUsd: null` added to `worker_a`, `moderator`, `worker_b` in
  `createModelMixState()` and to the initial seat objects in
  `buildHistoryEntry()` — full three-seat parity.
- `applyModelMixEvent`: on `seat_completed`/`moderator_completed`,
  `costUsd = event.cost_usd ?? seat.costUsd` — the exact no-clobber pattern
  used for `usage`.
- `hydrateModelMixState` live slots and `buildHistoryEntry` history entries
  read `message.cost_usd ?? null` the same way `usage`/`finish_reason` are
  read.
- `archiveCurrentRun` carries `costUsd ?? null` into the archived history
  entry for all three seats.

### `frontend/src/seatTelemetry.js`

- New exported `formatCostUsd(value)`: returns `null` for any non-finite
  non-number; otherwise `$X` with 4 decimal places under $0.01 and 2 decimal
  places at or above it. Mission 044's own test fixture value `$0.0045`
  renders as `$0.0045` — never a misleading `$0.00`.
- `buildSeatTelemetry` pushes a `Cost` row **only** when `seat.costUsd` is a
  real finite number. Absent/`null`/non-finite: no row at all — matching
  Timing/Finish-style conditional rendering, deliberately NOT Usage's
  always-present `unavailable` pattern, because cost is genuinely not a
  capability most providers have today.
- Each seat's cost renders standalone; no cross-seat aggregate is computed or
  displayed anywhere.
- Live seat footers only; historical/prior-turn footers are untouched (same
  scope boundary Mission 018 set for the rest of the telemetry footer).

Note: `isSeatActive` was deliberately left unchanged — a seat with only
`costUsd` set is not a reachable state (cost implies a completed event, which
sets `status`/`completedAt`), and Timing/Finish follow the same rule.

## Tests

`modelmixState.test.js` (6 new): worker and moderator `cost_usd` capture with
no-clobber on a later event lacking the field; seats without reported cost
stay `null`; hydration reads `cost_usd` off persisted messages and leaves
absence `null`; `archiveCurrentRun` carries `costUsd` through. Two existing
archive `deepEqual` expectations gained `costUsd: null` — the unavoidable
consequence of the new field on archived seat objects; no behavior
expectation changed.

`seatTelemetry.test.js` (5 new): sub-cent cost renders `$0.0045` (explicitly
asserted NOT `$0.00`); over-a-cent renders two decimals; `costUsd: null` and
field-absent render no Cost row; non-finite/non-numeric values never render.

## Validation (observed)

- `cd frontend && npm test` → **148 passed** (15 files; 138 prior + 10 new).
- `npm run build` → built clean.
- `npm run lint` → clean.
- `uv run pytest backend/tests -q --basetemp=...` → **494 passed** (backend
  unchanged; the workspace `--basetemp` override remains the workaround for
  the known pre-existing `pytest-of-wpedigo` system-temp ACL error).

## Punch Board item 17

The visibility half (dollar spend visibility: Mission 044 computation +
this rendering) is now complete end to end. Item 17's runtime half was
already satisfied by Missions 013/019/020/021. Any actual dollar spend-cap
enforcement (cutting off generation, refusing runs, warning thresholds over
USD) remains a separate, explicitly undecided product question.
