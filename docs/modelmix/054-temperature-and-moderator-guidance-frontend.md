# Mission 054 — Temperature and Moderator Guidance (Frontend)

Date: 2026-09-03 CT · Base: main @ `c57e151` (Mission 053)

## What changed

Frontend-only. Mission 053 made `temperature` (0.0–2.0) and
`moderator_guidance` (max 2000 chars) real request fields; this mission
renders the controls, persists them locally, and wires them into the
request. No backend file touched.

### `frontend/src/modelmixBehavior.js` (new)

Stands alongside `guardrailSettings.js`, mirroring its defensive discipline:

- `BEHAVIOR_STORAGE_KEY = 'modelmix.behavior'`.
- `MIN_TEMPERATURE = 0.0`, `MAX_TEMPERATURE = 2.0`,
  `MAX_MODERATOR_GUIDANCE_LENGTH = 2000` — matching the backend bounds.
- `validateBehavior({temperature, moderator_guidance})` — each field is
  independent: an absent (`undefined`/`null`) field is skipped, never an
  error; a provided field must satisfy its bound. Returns
  `{valid:true}` or `{valid:false, errors:{...}}`.
- `loadBehavior` / `saveBehavior` / `clearBehavior` — `localStorage`
  behind the same `defaultStorage()` indirection. Storage values are
  validated on load and save; malformed/missing always fall back to
  `null` (load) / `false` (save/clear) and never throw. A stored object
  holding only a temperature, only a guidance, or both is accepted; an
  empty object returns `null`.

### `frontend/src/components/ModelMixObserver.jsx`

- `SETTINGS_SECTIONS` gains `{ id: 'behavior', label: 'Behavior' }`
  following the section convention.
- New `BehaviorSection` component mirrors `GuardrailsSection`: a
  temperature number input (`min` 0, `max` 2, `step` 0.1) and a guidance
  textarea (`maxLength` 2000) with a live remaining-character count, each
  independent, plus the same `modelmix-settings-actions` Save / Clear
  pair. Save is disabled when the inputs are empty or invalid; Clear is
  disabled when nothing is saved.
- Parent state `behaviorRevision` + `saveBehaviorSettings` /
  `clearBehaviorSettings` handlers (same shape as the guardrails ones),
  threaded through `ModelMixSettings` props and section dispatch.
- `send()` includes `temperature` and `moderator_guidance` in the request
  body ONLY when a valid saved value exists — exactly the guardrail
  override precedent: each key is omitted entirely when not set, never
  sent as `null`.

## Boundaries honored

- No backend change; no `schema_version` bump; no new dependencies.
- Independent fields — a user can set temperature alone, guidance alone,
  both, or neither.
- Malformed/missing localStorage never throws and never blocks a run.
- Values are validated against the exact backend bounds (`0.0–2.0`,
  `<= 2000`) before saving and before sending.

## Tests (15 total)

`frontend/src/modelmixBehavior.test.js` (10): bound constants match backend;
`validateBehavior` accepts valid/independent/empty and boundary values;
rejects temperature outside `[0.0, 2.0]` (including NaN/non-finite/
non-number); rejects guidance over 2000 chars and non-strings; treats an
absent temperature as independent (valid); `loadBehavior` returns null on
missing/unavailable storage and parses valid single/multi-field objects
while rejecting corrupt shapes without throwing; `saveBehavior` writes and
`clearBehavior` removes; `saveBehavior` refuses invalid or empty values
without writing; helpers tolerate broken/throwing storage without throwing.

`frontend/src/components/ModelMixSendBehavior.test.jsx` (5) — mirrors
`ModelMixSendCompare.test.jsx`'s mocked-`startModelMixRun` capture pattern:
with both a saved temperature and guidance, `send()` builds a body carrying
both correct values; with nothing saved, NEITHER key is present (`'temperature'
in body === false`, `'moderator_guidance' in body === false`); with only
temperature saved, guidance is genuinely absent; with only guidance saved,
temperature is genuinely absent; malformed saved behavior is ignored and
omits both keys.

## Validation (observed)

- `cd frontend && npm test` → **181 passed** (18 files; 166 prior + 15 new).
- `npm run build` → clean; `npm run lint` → clean.
- `uv run pytest backend/tests -q --basetemp=...` → **535 passed**
  (backend unchanged; `--basetemp` is the established workaround for the
  pre-existing `pytest-of-wpedigo` ACL `WinError 5`).

## Remaining risks / open items

- None identified. Behavior is local-preference persistence (frontend
  only), consistent with the Mission 020 / 053 per-request model; no
  server-side persistence was added.
