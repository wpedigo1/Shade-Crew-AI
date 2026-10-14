# Mission 031 — Solo Mode Frontend Delivery

Route: Big Pickle (OpenCode Zen)
Punch Board item: 27 (Solo — closing mission)
Date: 2026-08-31 CT
Base: `main @ 1503aef` (Mission 030)

## Purpose

Mission 030 delivered the backend half of Solo mode. Mission 031 completes the
frontend half: Solo is now a third persisted mode that runs Worker A alone,
omits the other two model fields from the request, and presents one full-width
worker panel. This closes Punch Board item 27 and completes the Mix / Compare /
Solo mode control.

## Frontend behavior

- `frontend/src/modelmixMode.js` accepts `mix`, `compare`, and `solo`; stored
  Solo mode round-trips through the existing local-storage helpers.
- The mode control renders Mix / Compare / Solo and retains the existing
  active-run disabled-state mechanism.
- Solo hides the Moderator and Worker B selectors. Worker A remains the only
  required model; Moderator is required only for Mix, and Worker B is required
  for Mix and Compare.
- Solo requests contain `prompt` and `worker_a_model`, while
  `worker_b_model` and `moderator_model` are absent as keys.
- Moderator and Worker B panels remain mounted but receive
  `modelmix-panel-hidden`, matching the established Compare-mode mechanism.
  The cockpit receives the existing single-column
  `modelmix-workers--maximized` visual treatment in Solo mode.
- Mode and panel-view state remain separate. In Solo, the mode owns which
  panels are visible; a maximize state targeting a hidden seat is visually
  neutralized so the cockpit cannot become blank. The stored panel-view state
  is not overwritten and becomes effective again after leaving Solo.

The reducer and persistence/event helpers named as hard boundaries were not
changed. A worker-A-only mocked SSE run renders cleanly with the unused seats
remaining at their existing empty state.

## Tests

`frontend/src/components/ModelMixSendSolo.test.jsx` adds eight tests covering:

1. Solo selector and panel visibility, including mounted hidden panels;
2. exact omission of both unused request keys;
3. Solo send enablement without Worker B or Moderator;
4. unchanged Mix behavior;
5. unchanged Compare behavior;
6. active-run mode-control locking while Solo is selected;
7. clean Worker-A-only SSE rendering with no leaked content in hidden seats;
8. a hidden-seat maximize attempt remaining inert in Solo.

`frontend/src/modelmixMode.test.js` now covers Solo validation and persistence.
The sole existing frontend test modified for this mission is the top-bar option
list assertion in `ModelMixObserver.test.jsx`, necessarily extended from
`['Mix', 'Compare']` to `['Mix', 'Compare', 'Solo']`. Every other pre-existing
frontend test passes unmodified.

## Files changed

- `frontend/src/modelmixMode.js`
- `frontend/src/modelmixMode.test.js`
- `frontend/src/components/ModelMixObserver.jsx`
- `frontend/src/components/ModelMixObserver.test.jsx`
- `frontend/src/components/ModelMixSendSolo.test.jsx` (new)
- `docs/modelmix/031-solo-mode-frontend.md` (new)
- `docs/modelmix/PUNCH-BOARD.md`
- `docs/modelmix/MISSION-INDEX.md`
- `docs/modelmix/ENGINEERING-PROGRESS.md`

No backend file, reducer helper, CSS file, dependency, or lockfile changed.

## Validation actually run (observed)

- `cd frontend && npm test && npm run build && npm run lint`:
  - Vitest: **15 files passed, 138 tests passed**;
  - Vite: **439 modules transformed**, production build completed in 1.75s;
  - ESLint: exited successfully with no findings.
- The exact required `uv run pytest backend/tests -q` command encountered the
  known Windows environment failure: **246 passed, 214 setup errors**, all
  rooted in `PermissionError: [WinError 5]` for
  `C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo`.
- Rerun with shell-local `TEMP` / `TMP` and `--basetemp` pointing inside the
  workspace: **460 passed in 35.32s**. No backend code changed.

## Closing

Punch Board item 27 (Add Solo) is CLOSED through Missions 030 and 031: Mission
030 supplies and verifies the one-worker backend path; Mission 031 supplies and
verifies the frontend mode, request shape, selectors, and panel layout. Items
27 (Solo) and 28 (Compare) are now both complete end to end. The thin mode
control portion of item 24 is also complete.
