# Mission 006 Result

**PASS** — `/modelmix` now presents the first end-to-end three-panel cockpit with independent
Worker A and Worker B surfaces around a wider Moderator surface.

## Branch / Commit

- Branch: `codex/modelmix-mission-006`
- Commit: `feat: add ModelMix moderator cockpit pane` (the commit containing this report)
- The requested Mission 005 SHA was not present in the supplied object database. The available
  base commit was `a88cc6f987cff2c060efe196bb3240e4389f8733`, containing the combined Mission 002–005 tree.

## Three-Panel Layout

The existing persistent cockpit section now renders stable siblings in this order:

1. Worker A on the left;
2. Moderator in a center column sized at 1.45 times a worker column;
3. Worker B on the right.

The section consumes the remaining viewport height, and each transcript scrolls independently.
The center has only a subtle surface distinction rather than dashboard-card chrome. All panels use
the existing safe shared `MarkdownContent` renderer. Static component positions preserve worker
surfaces during ordinary state transitions.

## Moderator Configuration

The compact model row now contains Worker A, Moderator, and Worker B provider/model-ID fields in
the same visual order as the panes. Moderator starts empty and is required, so the UI neither
hardwires nor silently substitutes a provider. The exact trimmed value is sent as
`moderator_model` in the existing Mission 005 run request. No credential input was added.

## Frontend State / Event Routing

The centralized `modelmixState` seam now includes Moderator text, status, error, `started`, and
finish reason. Initial status is `waiting`, displayed as the quiet `Waiting for workers…` state.
The existing single event reducer routes:

- `moderator_started` to running/synthesizing state;
- `moderator_delta` only to Moderator text;
- `moderator_completed` to completed state and optional finish reason;
- `moderator_failed` to a visible center-pane failure without touching worker output.

Worker events retain seat-only routing. All three surfaces share the existing global `lastSeq`
check; no panel owns a sequence or network stream. A partial `run_completed` changes a successfully
completed Moderator to `partial`, while preserving the failed worker and successful evidence.
Cancellation changes a waiting or active Moderator to `cancelled`.

## Reconnect / Replay

Mission 004's fetch/SSE loop is unchanged. It retains `run_id` and the last accepted global
sequence, reconnects to the journal with `after_seq`, and routes replay through the same reducer.
Moderator replay is therefore deduplicated exactly like worker replay. While reconnecting, the
center surface displays `reconnecting` without clearing any transcript. HTTP 409/404 recovery
states continue to preserve all three visible outputs.

## Partial / Failure UX

- Before fan-in, the center is visibly waiting and contains no fake activity or output.
- During synthesis, Moderator is marked running while both worker transcripts remain visible.
- One worker failure remains visible in that worker pane; a successful Moderator synthesis remains
  visible and becomes honestly partial/degraded when the backend terminal event arrives.
- Moderator failure appears in the center while both worker transcripts remain intact.
- Cancellation preserves accumulated text and marks unfinished Moderator work cancelled.

## Send / Stop

Send and Stop remain separate adjacent controls. Idle and terminal states enable Send and disable
Stop. Active worker, Moderator, reconnect, and cancellation-request states disable Send and enable
Stop. The brief pre-run-ID connection state disables both so Stop never implies an unaddressable
cancellation. Stop still calls only the explicit cancel endpoint; stream loss never calls it.

## Test Evidence

- `node --test src/modelmixState.test.js` from `frontend/` — 15 passed.
- `npx eslint src/modelmixState.js src/modelmixState.test.js
  src/components/ModelMixObserver.jsx` from `frontend/` — passed, with only the existing npm
  environment/browser-data warnings.
- `npm run build` from `frontend/` — passed; Vite transformed 431 modules.
- `uv run pytest -q` — 463 passed.
- Development launch: `uv run python -m backend.main` and
  `npm run dev -- --host 127.0.0.1` both started successfully.
- `curl http://127.0.0.1:5173/modelmix` — HTTP 200, 1,181-byte Vite entry response.
- `curl http://127.0.0.1:5173/src/components/ModelMixObserver.jsx` — HTTP 200, confirming Vite
  transformed/served the cockpit module.
- `curl http://127.0.0.1:8001/api/health` — HTTP 200.
- `git diff --check` — passed.

The lightweight tests cover Moderator-only routing, worker isolation from both peer and Moderator,
duplicate/replay suppression, waiting/running/completed/failed/partial/cancelled state, finish
reason, explicit Moderator request configuration, Moderator-phase reconnect cursor, three-panel
reset, fixed Send/Stop behavior, explicit cancellation, no cancellation on stream close, and
existing 409/404 recovery behavior.

A screenshot could not be captured because the execution image exposes no browser binary or
browser-automation package. Route, transformed module, build, reducer, and backend availability
were verified programmatically; this report makes no unexecuted visual claim.

## Manual Test Steps

1. Run `uv run python -m backend.main` from the repository root.
2. Run `cd frontend && npm run dev` in another terminal.
3. Open `http://localhost:5173/modelmix`.
4. Enter configured Worker A, Moderator, and Worker B IDs, then select **Send**.
5. Confirm A/B stream independently while the wider center says `Waiting for workers…`.
6. Confirm the center switches to running and streams only after both workers terminate.
7. Interrupt the SSE request during Moderator output; confirm reconnect uses the displayed global
   sequence and does not duplicate center text.
8. Run again and select **Stop** during Moderator output; confirm accumulated panel text remains,
   cancellation is shown, and successful completion is not shown.
9. Exercise a one-worker failure with deterministic fake providers or configured local models;
   confirm the failed pane, surviving evidence, center synthesis, and partial status all remain.

No paid API credit is required; the automated state/API tests use deterministic mocks.

## Known Limitations

- Model IDs remain compact free-text alpha controls rather than discovered searchable selectors.
- Run/sequence state survives subscriber replacement but not a full page reload.
- The cockpit has no presets or dedicated settings surface.
- Moderator finish reason is tracked but not yet displayed as separate UI metadata.
- Backend journals remain process-local and require the single-worker alpha deployment.

## Recommended Mission 007

Replace the three free-text ModelMix model fields with the existing configured-provider searchable
model discovery controls while preserving explicit Worker A, Moderator, and Worker B selection and
the current cockpit run/reconnect state.
