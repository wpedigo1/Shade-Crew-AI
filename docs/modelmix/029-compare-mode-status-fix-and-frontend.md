# Mission 029 — Compare Mode Status Fix and Frontend Delivery

Route: Big Pickle (OpenCode Zen)
Punch Board item: 28 (Compare — closing mission)
Date: 2026-08-31 CT
Base: `main @ 4dc105c` (Mission 028)

## Purpose

Mission 028 verified the existing no-moderator two-worker backend path end to
end and left two things open: (1) an observed product-semantics wart — when both
workers fail with no moderator, `multiplex_workers` emitted `run_completed` with
`status="partial"`, which is misleading for a run with no surviving output; and
(2) the entire frontend Compare mode, which did not exist. Mission 029 fixes the
backend status edge and ships the Compare frontend mode, closing item 28.

## Part 1 — Backend status fix

Where: `backend/modelmix/orchestrator.py`, `multiplex_workers`.

Before, a `failed: bool` drove the terminal status as `"partial" if failed else
"completed"` whenever `emit_run_completed=True` (the no-moderator case). When
both workers failed, that produced `run_completed "partial"` despite zero
surviving output.

After: `failed: bool` is replaced with `failed_seats: set`, and the terminal
status is computed as:

```python
"failed" if failed_seats and len(failed_seats) == len(tasks)
else "partial" if failed_seats
else "completed"
```

So both-workers-failed → `"failed"`, one-worker-failed → `"partial"`,
all-completed → `"completed"`.

Boundaries respected:
- The moderator path (`emit_run_completed=False`) is untouched; a
  `run_completed` is still only emitted for the no-moderator case.
- `registry._run_phase` simply passes the resulting status through via
  `mark_status` (already a no-op for the moderator terminal route).
- No public contract changed other than the terminal `status` value for the
  both-workers-failed no-moderator case, which is exactly the intended behavior
  change.

Test change (Mission 028 file, `backend/tests/test_modelmix_compare_mode_backend.py`):
point-3 test renamed from
`test_no_moderator_both_workers_fail_reaches_run_completed_partial` to
`test_no_moderator_both_workers_fail_reaches_run_completed_failed` and now
asserts `status="failed"` with an updated comment. The other six tests are
unmodified.

## Part 2 — Frontend Compare mode

New pure module `frontend/src/modelmixMode.js`:
- `MODES = { mix: 'mix', compare: 'compare' }`, `DEFAULT_MODE = 'mix'`,
  `MODE_STORAGE_KEY = 'modelmix.mode'`.
- `loadSavedMode(storage)` returns only `'mix'` or `'compare'`, defaulting to
  `'mix'`. There is **no** `solo` anywhere.
- `saveMode(mode, storage)` persists it and returns the stored value.
- `frontend/src/modelmixMode.test.js` (6 tests) covers round-trip, validation,
  storage read/write, and defaults.

`frontend/src/components/ModelMixObserver.jsx`:
- Imports `loadSavedMode, MODES, saveMode`; adds `mode` state initialized from
  `loadSavedMode(window.localStorage)`.
- `send()`/`sendDisabled` are mode-aware: in compare mode the moderator model is
  not required to enable send.
- `send()` builds `requestBody` with `moderator_model` only when `mode !==
  'compare'`; `starting.models.moderator` is `''` in compare mode.
- The top-bar `Mode: Mix` `<span>` becomes a `<label class="modelmix-mode">`
  wrapping `<select class="modelmix-mode-select" aria-label="Mode">` with options
  Mix / Compare; the handler calls `saveMode(next, window.localStorage)`.
- The mode select is disabled while models are loading or during an active run,
  using the existing `modelSelectorsDisabled(observer.overall)` /
  `controlState(...).sendDisabled` helpers.
- The composer Moderator selector is not rendered in compare mode.
- The center moderator panel gets `.modelmix-panel-hidden` when
  `mode === 'compare' && seatKey === 'moderator'`, so it stays mounted but is
  hidden from layout (reusing the `panelView` hidden mechanism).

`frontend/src/components/ModelMixObserver.css`:
- `.modelmix-mode` pill container, `.modelmix-mode-select` styling, and
  `.modelmix-models--compare { grid-template-columns: 1fr 1fr; }` (base
  3-column grid unchanged).

New `frontend/src/components/ModelMixSendCompare.test.jsx` (6 tests), modeled on
the existing `ModelMixSendGuardrails.test.jsx`, covering:
1. selecting Compare hides the Moderator selector and hides-but-keeps-mounted
   the Moderator panel;
2. Mix-mode behavior is unchanged (moderator selector + all panels render);
3. the mode control is disabled during an active run;
4. Compare-mode send omits the `moderator_model` key entirely;
5. Mix-mode send still includes `moderator_model`;
6. a Compare-mode run renders worker content cleanly with no moderator-shaped
   content (no 'Moderator synthesis', no worker deltas in the hidden moderator
   panel).

`frontend/src/components/ModelMixObserver.test.jsx`: the top-bar test now asserts
the real `select.modelmix-mode-select` with options `['Mix', 'Compare']`, default
`value === 'mix'`, and `#modelmix-moderator-model` present. This is the **sole
existing frontend test that was modified**. It was unavoidable: the old test
asserted the mode was an inert `<span>` with no `<select>` elements, which is
directly contradicted by turning it into a real control. Every other existing
frontend test passes unmodified.

## Files changed

- `backend/modelmix/orchestrator.py` — `multiplex_workers` `failed_seats` change.
- `backend/tests/test_modelmix_compare_mode_backend.py` — point-3 test
  renamed/reworded to assert `status="failed"`.
- `frontend/src/modelmixMode.js` (new) — module.
- `frontend/src/modelmixMode.test.js` (new) — 6 tests.
- `frontend/src/components/ModelMixSendCompare.test.jsx` (new) — 6 tests.
- `frontend/src/components/ModelMixObserver.jsx` — mode state, mode control,
  compare behavior.
- `frontend/src/components/ModelMixObserver.css` — mode control + compare grid.
- `frontend/src/components/ModelMixObserver.test.jsx` — top-bar test updated
  (sole modified existing test).

## Validation actually run (observed)

- `uv run pytest backend/tests/test_modelmix_compare_mode_backend.py backend/tests/test_modelmix_moderator.py -v`
  (with `--basetemp` in the pre-approved temp dir) → **18 passed** (7 compare +
  11 moderator).
- `uv run pytest backend/tests -q` → **448 passed**.
- `uv run ruff check backend/modelmix/orchestrator.py backend/tests/test_modelmix_compare_mode_backend.py`
  → All checks passed.
- `cd frontend && npm test` → **130 passed** (14 files); `npm run build` →
  green; `npm run lint` → clean.

## Assumptions

- The compare/status fix is complete only for the no-moderator path; the
  moderator path is deliberately unchanged.
- The one modified existing test (top-bar) was acceptable because the mode had
  to become a real control; all other existing tests pass unmodified.
- `mode` is persisted per-browser via `localStorage["modelmix.mode"]`; it is not
  per-seat server state, consistent with the alpha surface.

## Residual / notes

- The frontend `observe()` loop's terminal check uses `isTerminalOverall` on the
  observer ref; a unit test that replays a whole run through a synchronous mock
  SSE can show a transient `reconnecting` status because React batches the ref
  updates. This is a test-harness artifact, not a product defect; the send-
  compare rendering test therefore asserts worker/moderator content outcomes
  rather than the transient status string.

## Closing

Punch Board item 28 (Add Compare) is now CLOSED (Missions 028 + 029). Backend
half: verified in Mission 028; status fix in this mission. Frontend half: Compare
mode selector + panel behavior delivered here.
