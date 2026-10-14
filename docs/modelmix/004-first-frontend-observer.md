# Mission 004 Result

**PASS** — the isolated `/modelmix` proof surface starts, observes, reconnects to, and explicitly
cancels two-worker ModelMix runs without replacing the Council UI.

## Branch / Commit

- Branch: `codex/modelmix-mission-004`
- Commit: `feat: add first ModelMix frontend observer` (the commit containing this report)
- The requested Mission 003 SHA was not present in the supplied object database. The available
  base commit was `343aa693f1104b3f926e5f99b22739ee9718dc5c`, containing the combined Mission 002/003 tree.
  No Git remote was configured.

## Experimental Route

Open `http://localhost:5173/modelmix` while the normal Vite development server is running. A
minimal pathname hook in `frontend/src/main.jsx` lazy-loads the observer; every other path still
loads the inherited `App` unchanged. The ModelMix view calls the existing
`POST /api/modelmix/runs/stream`, replay, and explicit cancel endpoints.

The backend CORS middleware now exposes `X-ModelMix-Run-ID`, allowing the cross-origin Vite client
to retain the run ID as soon as response headers arrive, even before the first SSE data event.

## UI Structure

The view uses the available vertical workspace rather than dashboard cards:

- a small header and link back to Council;
- one prompt textarea;
- plain Worker A and Worker B model-ID fields with editable alpha defaults;
- permanently separate Send and Stop buttons;
- inline overall status plus visible run ID and last sequence;
- exactly two equal transcript panes: Worker A on the left and Worker B on the right.

Each pane owns text, state, and error fields. Visible output uses the existing safe markdown
renderer. There is no center or Moderator surface.

## SSE Event Routing

`applyModelMixEvent()` rejects any event whose integer `seq` is not greater than the last processed
sequence. Accepted `seat_delta` text is appended only to the matching `worker_a` or `worker_b`
state. Seat terminal events update only that seat, so a failure never clears or changes its peer's
transcript. Run events independently update overall state. The reducer also stores the event run ID
and latest sequence outside the transient response reader.

## Reconnect / Replay

The fetch-based SSE observer treats a non-terminal stream close or read failure as a subscriber
failure, not run cancellation. It changes the inline state to `reconnecting`, then calls
`GET /api/modelmix/runs/{run_id}/events?after_seq={lastSeq}`. Replayed and new live events pass
through the same sequence-deduplicating reducer. A terminal event makes a clean stream close final.

HTTP 409 displays a replay-gap message instructing the user to start a new run. HTTP 404 displays
an expired/not-found recovery message. Component unmount aborts only its fetch subscriber; it does
not call cancellation.

## Send / Stop Behavior

Send and Stop remain separate controls in fixed positions:

- idle or terminal: Send enabled, Stop disabled;
- connecting before a run ID is received: both disabled so Stop never implies a cancellation that
  cannot yet be addressed;
- running or reconnecting: Send disabled, Stop enabled;
- cancelling: Send disabled and Stop remains enabled because cancellation is idempotent.

Stop alone calls `POST /api/modelmix/runs/{run_id}/cancel`. A dropped stream never calls it.

## Test Evidence

- `node --test src/modelmixState.test.js` from `frontend/` — 7 passed.
- `npm run build` from `frontend/` — passed; Vite transformed 431 modules.
- `npx eslint src/main.jsx src/modelmixApi.js src/modelmixState.js src/modelmixState.test.js
  src/components/ModelMixObserver.jsx` from `frontend/` — passed. npm emitted only environment and
  browser-mapping data warnings.
- `uv run pytest -q` — 455 passed.
- `curl -I http://127.0.0.1:5173/modelmix` while Vite was running — HTTP 200.
- `git diff --check` — passed.

The focused tests verify independent seat routing, duplicate/replayed sequence suppression,
reconnect URL cursor construction, exact-once text append, fixed Send/Stop enablement, peer-output
preservation on failure, explicit cancel HTTP routing, no cancel on stream close, and visible
409/404 recovery states. The dev server reported the page route available. A browser screenshot
could not be captured because this execution image has no browser binary or browser automation
package; no visual-success claim depends on an unexecuted screenshot.

## Manual Test Steps

1. Start the backend from the repository root: `uv run python -m backend.main`.
2. Start Vite in another terminal: `cd frontend && npm run dev`.
3. Open `http://localhost:5173/modelmix`.
4. Enter two configured model IDs and a prompt, then select **Send**.
5. Confirm Send becomes disabled, Stop becomes active, and Worker A/B deltas remain in their own
   left/right panes.
6. In browser developer tools, note the displayed run ID and last sequence, then interrupt the
   streaming request without calling Stop. Confirm the inline state changes to reconnecting and
   output resumes without duplicated text.
7. Start another run and select **Stop**. Confirm cancellation appears, Send becomes enabled after
   terminal cancellation, and the retained transcript remains visible.
8. To exercise recovery states deterministically, request replay with an evicted cursor for HTTP
   409 or a missing run ID for HTTP 404 and confirm the inline recovery message.

Real output requires configured providers, but no secret is embedded in the page and the model-ID
defaults remain editable.

## Known Limitations

- This is a direct experimental route with no navigation entry, presets, or provider model picker.
- Reconnect retries use a fixed 500 ms delay and have no capped exponential backoff.
- Run ID and sequence survive connection replacement within the mounted view, not a full browser
  refresh; durable browser storage is intentionally deferred.
- The observer relies on the Mission 003 process-local journal and its single-worker backend limit.
- The two panes remain a proof layout and are not the future three-surface cockpit.

## Recommended Mission 005

Add a ModelMix Moderator backend phase that receives the user prompt plus completed Worker A/B
visible outputs only after both workers terminate, streams a labeled synthesis, and preserves
witness isolation.
