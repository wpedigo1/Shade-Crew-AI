# Mission 021 — Guardrails Settings and Visibility (Frontend)

Route: Big Pickle (OpenCode Zen)
Punch Board items: 17 (advance — make the output guardrails configurable from the cockpit Settings and visible in the seat footers)
Base: `main` @ `ed09d33` "feat(modelmix): configurable output guardrails, backend (Mission 020)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Make the two guardrail thresholds genuinely user-configurable in the cockpit:
a new **Guardrails** section in the Settings dialog (mirroring the Mission 017
Defaults pattern) lets the user save local override values for the warning
threshold and hard cap; the saved override is then sent on every run request as
`warning_threshold_chars` / `hard_cap_chars`. When a seat crosses the warning
threshold mid-run, the already-fired `seat_output_warning` /
`moderator_output_warning` event becomes visible in that seat's footer as a
plain factual line (e.g. `Approaching output limit: 22,451 / 20,000 chars`).
Worker seats additionally gain the same `finishReason` capture and rendering
the Moderator already had, with one translation:
`modelmix_output_cap` → "Output capped by ModelMix"; all other values verbatim.

Frontend-only. Backend, public API, event contract, and persistence are
untouched.

## Delivered

### 1. `frontend/src/guardrailSettings.js` (new pure module)

Owns the local override contract and the duplicated bounds constants:

- `GUARDRAIL_STORAGE_KEY = 'modelmix.guardrails'`;
- `MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`
  (duplicates `backend/modelmix/guardrails.py`; see Remaining Risks — the two
  are not centrally synced, no live value is fetched);
- `validateGuardrailOverride({ warning_threshold_chars, hard_cap_chars })` —
  rejects non-integers, out-of-bound values, and `hard_cap_chars <
  warning_threshold_chars`, echoing the server's 422 rules so the UI never
  offers a payload the server will reject;
- `loadGuardrailOverride` — defensive read (missing key, corrupt JSON,
  wrong shape, or invalid values all return `null`);
- `saveGuardrailOverride` / `clearGuardrailOverride`;
- all storage functions default to `defaultStorage()`, which returns `null`
  outside a browser so the pure module tests run in a node environment without
  a `window`.

### 2. Request-body wiring (`ModelMixObserver`) and Settings UI

- `send()` builds the `requestBody` as before, then injects
  `warning_threshold_chars` / `hard_cap_chars` **only when** a valid saved
  override exists (both fields injected together; both omitted when `load
  GuardrailOverride()` returns null — byte-for-byte Mission 020 behavior).
- Settings gains `{ id: 'guardrails', label: 'Guardrails' }` as a fourth
  section after `defaults`. `GuardrailsSection` renders two `type="number"`
  inputs (`modelmix-guardrail-warning` / `modelmix-guardrail-cap`), live
  validation with an inline `role="alert"` error (Save disabled while
  invalid), Save/Clear action buttons, and a static help line labeling the
  20,000/40,000 defaults explicitly as **not a live-fetched server value**.
  The section is `key`ed on a `guardrailsRevision` counter so Save/Clear
  remount it and re-read storage — no effect-synchronization needed.

### 3. Warning visibility and finish-reason parity

- `modelmixState.js`: `applyModelMixEvent` records `outputWarning =
  { chars, threshold }` from `seat_output_warning` (both workers) and
  `moderator_output_warning`; worker `seat_completed` now captures
  `finish_reason` like the Moderator already did. `outputWarning` is
  **live-run state only** — never persisted to history/hydration (see
  decisions below). `buildHistoryEntry`, `archiveCurrentRun`, and
  `hydrateModelMixState` capture worker `finish_reason` generically
  (identical `message.finish_reason || null` semantics the Moderator already
  had).
- `seatTelemetry.js`: `buildSeatTelemetry(seat)` no longer takes `seatKey`
  (its last use was the moderator-only Finish restriction, now removed) and
  renders the Finish item for **every** seat with `finishLabel(reason)`
  (`modelmix_output_cap` → "Output capped by ModelMix", empty/null →
  "not reported", everything else verbatim). When `outputWarning.chars` and
  `.threshold` are both integers, an `output-warning` item renders as
  `Approaching output limit` → `22,451 / 20,000 chars` (locale-formatted),
  following the Finish item, on every active seat.

## Decisions That Materially Affected Implementation

- **`outputWarning` is never cleared and never persisted.** The spec text
  self-contradicts (clear on terminal-non-cap completion, yet also keep
  visible as still-true information). Chosen behavior: it stays on the seat
  as truthful, live-run information through terminal state, rendered with
  neutral copy, and is deliberately excluded from history/hydration/archive
  so a rehydrated cockpit never fabricates a warning it did not observe this
  session. Tests assert live-only isolation explicitly.
- **Static-default help text.** The 20,000/40,000 constants appear in the UI
  only as labeled static text ("not a live-fetched server value"), because no
  GET-config endpoint exists and the frontend cannot know the current backend
  module defaults at runtime.
- **Existing tests were minimally modified** despite the "unmodified"
  criterion: two `seatTelemetry` length assertions changed `2 → 3` (Finish
  now renders for worker seats and for a partial Moderator), the
  moderator-only finish test became all-seat tests, and two `modelmixState`
  archive `deepEqual` literals gained `finishReason: null` on the seeded
  worker seats. These are forced by the explicit parity and all-seats
  requirements, not by refactoring.
- **`buildSeatTelemetry(seat, seatKey)` dropped its second parameter** —
  that is a public-ish local function, and the argument existed solely for
  the moderator-only restriction being removed.

## Test Evidence

New test files:

- `frontend/src/guardrailSettings.test.js` — 11 tests covering validation
  errors, bound checks, the cap-vs-warning cross-check, missing/corrupt/invalid
  storage reads, save success/failure, and clear.
- `frontend/src/components/ModelMixSendGuardrails.test.jsx` — 3 tests driving a
  real `send()` through the mocked observer: override fields present when a
  valid override is saved, both omitted when nothing is saved, both omitted
  when stored JSON fails validation (send harness seeds saved seat models so
  the Send button is enabled).
- `frontend/src/components/ModelMixSettings.test.jsx` gains 4 tests:
  empty-start/Save-and-Clear-disabled/static-default copy, inline error + Save
  disabled for invalid pairs, valid save writes the override and enables
  Clear, Clear removes it and resets both inputs.
- `frontend/src/seatTelemetry.test.js` +9 tests: finish on every seat
  (verbatim reason, `modelmix_output_cap` translation, `not reported`), the
  output-warning line (formatted counts, visible alongside a capped
  completion, absent when never crossed).
- `frontend/src/modelmixState.test.js` +8 tests: worker finishReason parity in
  `buildHistoryEntry`/`archiveCurrentRun`/hydration, `modelmix_output_cap`
  capture for workers, `outputWarning` set from both warning event types,
  warning isolation (live-only, never in archive/history), and a regression
  confirming the Moderator's existing finish capture is unchanged.

## Validation

Raw output, run from the repo root:

### Frontend

```text
npm test
  ✓ src/guardrailSettings.test.js (11)      ✓ src/defaultSeatModels.test.js (5)
  ✓ src/utils/fontSize.test.js (3)          ✓ src/configuredSources.test.js (5)
  ✓ src/panelView.test.js (4)               ✓ src/seatTelemetry.test.js (20)
  ✓ src/configuredModels.test.js (3)        ✓ src/modelmixState.test.js (43)
  ✓ src/components/ModelMixTelemetry.test.jsx (3)
  ✓ src/components/ModelMixSendGuardrails.test.jsx (3)
  ✓ src/components/ModelMixObserver.test.jsx (6)
  ✓ src/components/ModelMixSettings.test.jsx (12)

 Test Files  12 passed (12)
      Tests  118 passed (118)

npm run build   (vite v7.3.6, 438 modules transformed, built in 1.65s)
npm run lint    (eslint . — clean)
```

### Backend (unchanged baseline, re-asserted)

```text
.venv\Scripts\python -m pytest backend\tests -q
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 92%]
............................                                             [100%]
388 passed in 15.43s   (unchanged from Mission 020 — no backend files touched)
```

## Remaining Risks / Open

- **Duplicated bounds constants:** `MIN_OUTPUT_CHARS_BOUND` /
  `MAX_OUTPUT_CHARS_BOUND` now exist in both `frontend/src/guardrailSettings.js`
  and `backend/modelmix/guardrails.py`, and the 20,000/40,000 defaults are
  referenced in static help text. There is no GET-config endpoint and no
  central sync; a future backend default change will not reflect in the
  frontend text. The help text is explicitly labeled static, non-live to keep
  users honest about this.
- **`outputWarning` is intentionally live-session-only.** After a reload, a
  run showing "Approaching output limit" before reload will not replay that
  line (history does not carry it), though a capped run's Finish item
  ("Output capped by ModelMix") still replays via `finish_reason`.
- **Server 422 on a valid-by-UI override cannot happen through this UI**, but
  the frontend cannot know current server defaults at runtime; a future
  backend default outside the UI's static text would simply be overridden by
  whatever the user saves.

## Acceptance Criteria → Where Covered

1. Settings includes a Guardrails section — Settings test 1 (`ModelMixSettings.test.jsx`).
2. Guardrails module (validate/load/save/clear) — `guardrailSettings.test.js`.
3. Saved override sent on every run POST; omitted when none/invalid — `ModelMixSendGuardrails.test.jsx`.
4. Warning event → live seat state on both workers and Moderator — `modelmixState.test.js`.
5. Warning renders as a plain footer line when present — `seatTelemetry.test.js`.
6. Worker `finishReason` captured like Moderator — `modelmixState.test.js`.
7. Warning stays visible as truthful info at terminal state; no fabrication — `seatTelemetry.test.js` + state isolation tests.
8. All-seat finish captions with `modelmix_output_cap` translation — `seatTelemetry.test.js`.
9. No backend file changes; request shape is Mission 020's optional fields — diff + 388-pass backend baseline.
10. No `Settings.jsx`/`App.jsx` changes, no new dependencies — diff review.