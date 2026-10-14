# Mission 056 — Native OAuth Connect/Disconnect in ModelMix Settings

Date: 2026-09-03 CT · Base: main @ `70477e4` (Mission 055)
· Punch Board item 26 (CLOSE)

## Scope decision

This closes the credential fold-in. After Missions 055 (simple providers) and 056
(OAuth), no provider requires a trip to Council settings for anything ModelMix
needs. All three OAuth providers (`xai-oauth`, `openai-oauth`, `github-copilot`)
share one uniform DEVICE-CODE flow — no redirect URI, no callback route needed —
so this is a frontend-only integration reusing the exact existing backend routes.

## What changed — frontend only, zero backend changes

### `frontend/src/modelmixApi.js` (three new functions, same `checkedFetch` pattern)

- `startOAuthConnection(providerId)` → POST `/api/oauth/{id}/start`.
- `getOAuthConnectionStatus(providerId, sessionId)` → GET
  `/api/oauth/{id}/status?session_id=...` (both id and session id encoded).
- `disconnectOAuthProvider(providerId)` → DELETE `/api/oauth/{id}`.

Each targets the existing `_require_admin`-guarded route and returns the real
JSON. No new endpoint, no new auth.

### `frontend/src/components/ModelMixObserver.jsx` (Providers section)

Extends the Mission 055 section with an `OAuthRow` per provider:

- **Real connected status** from the existing `xai_oauth_connected` /
  `openai_oauth_connected` / `github_copilot_connected` fields already returned
  by the settings the section fetches — matching how Mission 055 reused
  `configuredSources`. No fabricated status.
- **Not connected** → a Connect button. On click it calls `startOAuthConnection`,
  then renders the real returned `user_code` plainly and a clickable link using
  `verification_uri_complete` when present, `verification_uri` otherwise
  (confirmed `verification_uri_complete` is `null` for `openai-oauth` in the real
  backend code). The link opens in a new tab (`target="_blank"`,
  `rel="noopener noreferrer"`).
- **Polling** `getOAuthConnectionStatus` every 2.5s after starting, bounded by
  the session's `expires_in` (stops even if no terminal status is reached):
  - `status === "complete"` → stop, refetch settings, show connected.
  - `status === "error"` / `"expired"` → stop, show the REAL returned `error`
    message, allow retrying via Connect again.
  - deadline exceeded → stop, show "Connection timed out."
- **Cleanup**: every interval is tracked per-session in a ref map and cleared when
  a terminal state is reached and on component unmount — a test proves no leak.
- **Connected** → a Disconnect button calling the existing DELETE route, then
  refetching status.
- **Removed** the stale "OAuth providers … still managed in council settings"
  copy from Mission 055.

### `frontend/src/components/ModelMixObserver.css` (styles only)

Added `.modelmix-oauth-pending`, `.modelmix-oauth-code`, `.modelmix-oauth-link`,
`.modelmix-oauth-note` for the approval code/link/note, matching the existing
settings palette.

## Security posture

- Every request reuses the existing `_require_admin`-guarded routes — no new
  write path, no new auth wiring.
- No credential value is ever rendered or echoed; only the user's transient
  `user_code` from the live OAuth session is shown.
- Connected/error state is always the real server-returned value — never guessed.
- Zero backend changes, so the existing secure-credential-reference behavior is
  untouched.

## Boundaries honored (hard)

- No backend file, OAuth route, or `backend/oauth/sessions.py` touched.
- No redirect-callback flow built — the device-code flow is reused as-is.
- `Settings.jsx` (Council's own component) not touched.
- The 12 simple-provider rows from Mission 055 not touched.
- No fabricated connection status; only real `status`/`error` is displayed.
- No new dependency.

## Tests

### `frontend/src/modelmixApi.test.js` (+5)

- `startOAuthConnection` POSTs `/api/oauth/xai-oauth/start` and returns the
  session; provider id encoded.
- `getOAuthConnectionStatus` GETs `/api/oauth/{id}/status?session_id=...` and
  encodes the session id.
- `disconnectOAuthProvider` DELETEs `/api/oauth/{id}` and returns the result.

### `frontend/src/components/ModelMixSettings.test.jsx` (+7 component, updated 1 stale)

- Connect for each of the 3 providers calls the correct start endpoint and
  renders the real `user_code` and a working `verification_uri_complete` link.
- Fallback to `verification_uri` when `verification_uri_complete` is `null`.
- Polling transitions to connected display on `status: "complete"` (fake timers),
  with no further polling after complete.
- Polling stops and shows the real error message on `status: "error"`, with no
  further polling after error.
- Polling stops and shows the expired message on `status: "expired"`.
- Closing settings mid-poll clears the active interval (fake timers advanced;
  no polling after unmount).
- Disconnect calls the real DELETE route and the connected status updates
  afterward.
- The stale "still managed in council settings" copy is removed (the Mission 055
  test asserting it was updated to the new behavior).

All 9 acceptance criteria are covered.

## Validation (observed)

- `cd frontend && npm test` → **215 passed** (18 files; 203 prior + 12 new).
- `npm run build` → built clean (440 modules, `✓ built`).
- `npm run lint` → clean (exit 0).
- `cd .. && uv run pytest backend/tests -q --basetemp=...` → **544 passed**
  (unchanged; backend files never modified, confirmed via `git status`).
- `git status --short` shows only the 5 expected frontend files.

## Doc updates

- `PUNCH-BOARD.md` item 26 → **CLOSED (Missions 055 + 056)**; added Mission 056
  summary. No provider now requires a trip to Council settings for anything
  ModelMix needs.
- `MISSION-INDEX.md` — added Mission 056 table row + Result.
- `ENGINEERING-PROGRESS.md` — added Mission 056 Result.

## Remaining risks / open items

- The device-code sessions are in-memory (`backend/oauth/sessions.py`): a backend
  restart during an active approval discards the pending session, so the frontend
  would keep polling until `expires_in` elapsed and show "timed out." This is
  inherited backend behavior, out of scope, and safe (no terminal status was
  mishandled — the poll is bounded).
- OAuth disconnect silently leaves any orphaned in-progress session in the backend
  map until its `expires_in` elapses; harmless and inherited.
- No cross-tab sync: concurrent edits to the same provider in two tabs are last
  writer wins, matching the simple-provider behavior from Mission 055.
