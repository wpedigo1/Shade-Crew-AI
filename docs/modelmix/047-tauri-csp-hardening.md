# Mission 047 — Tauri CSP Hardening

Date: 2026-09-02 CT · Base: main @ `30f064a` (Mission 046)

## Verification limits (stated plainly, same as Missions 032/033/035)

I cannot compile Rust, launch a webview, or run a real `cargo tauri dev` /
`cargo tauri build` / launch the packaged app. The CSP change below is
implemented and its directives are justified from the actual repo evidence I
read, but PROOF that the packaged production app still loads fonts, reaches
the sidecar backend, and streams a real Mix run **requires your hands**. This
report therefore does **not** claim PASS on the runtime criteria — dev-mode or
production — and marks exactly what remains to be verified.

## What changed

`src-tauri/tauri.conf.json`: `app.security.csp` changed from `null` to a real
policy string. Nothing else in the config, and no production code, was
touched.

```json
"csp": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' http://localhost:8001 http://127.0.0.1:8001 http://tauri.localhost:8001;"
```

## Per-directive justification (criterion 4)

Every directive is present because removing it would break a resource the app
ALREADY loads — nothing was added speculatively.

- `default-src 'self'` — base restriction: only the app's own origin may load
  anything not explicitly allowed. This is the blocking-default that `null`
  was missing.
- `script-src 'self'` — `frontend/index.html` loads only same-origin scripts
  (`/config.js`, `/src/main.jsx`). Verified there is NO CDN/inline script; a
  bare `'self'` therefore suffices and `'unsafe-inline'` is deliberately NOT
  granted for scripts (no inline scripts exist to break).
- `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com` —
  `https://fonts.googleapis.com` is the font stylesheet origin loaded in
  `index.html:11`. `'unsafe-inline'` is required because React applies dynamic
  styling via inline `style` attributes (governed by `style-src` /
  `style-src-attr`) and Vite-injected styles; a stricter `style-src 'self'`
  would break inline-styled UI even though the bundled `.css` itself is
  same-origin. (Verified-conditional: this is the one directive I could not
  conclusively drop; see open items — it is the established React + Google
  Fonts pattern and is narrower than a blanket script allowance.)
- `font-src 'self' https://fonts.gstatic.com` — the actual font files load
  from `fonts.gstatic.com` (via the `crossorigin` preconnect in
  `index.html:10`). Omitting it silently drops the four app fonts.
- `img-src 'self' data:` — bundled icons/favicon are same-origin; `data:` is
  for inline images already used by the UI. Narrower would break inline
  images; nothing else is loaded.
- `connect-src 'self' http://localhost:8001 http://127.0.0.1:8001
  http://tauri.localhost:8001` — this is the mission's crux and where the
  starting policy was corrected from repo evidence.
  - The frontend builds its backend URL as
    `http://${window.location.hostname}:8001`
    (`frontend/src/modelmixApi.js:4` and `frontend/src/api.js:15`), always the
    `http://` scheme.
  - Dev: `devUrl` is `http://localhost:5173`, so `window.location.hostname` is
    `localhost` → `http://localhost:8001`.
  - Production: the webview serves on the `tauri.localhost` host — confirmed
    by `FRONTEND_HOST = "https://tauri.localhost,http://tauri.localhost"` set
    at spawn (`src-tauri/src/lib.rs:223`). So
    `window.location.hostname` is `tauri.localhost` → the real production
    connect target is `http://tauri.localhost:8001`.
  - The starting policy listed only `127.0.0.1:8001` and `localhost:8001`,
    which works in dev but would let the browser block the production request
    before it reaches the (already CORS-permitting) backend — the exact
    dev/production divergence Mission 035 warned about. `http://tauri.localhost:8001`
    is added because that is what the code actually connects to in the shipped
    app.
  - `127.0.0.1:8001` is kept because the backend sidecar binds there
    (`LLM_COUNCIL_BIND_PORT`, Mission 035) and `localhost` may resolve to it;
    both are already-valid connect targets, not new allowances.
  - `connect-src` uses only `http://` because the frontend code hardcodes the
    `http://` scheme for the backend fetch; no `https://` backend connect
    exists in the codebase.

## Boundaries honored

- Backend CORS (`backend/main.py`) and `FRONTEND_HOST` untouched — separate
  layer.
- Sidecar spawn / Job Object / rest of `lib.rs` untouched — CSP doesn't
  interact with it.
- No new external resource/CDN introduced; only allowances for what is already
  loaded.
- MSI, code signing, dynamic ports left untouched (still-open item 34 tail).

## Validation performed (observed)

- `uv run pytest backend/tests -q --basetemp=...` → **507 passed** (unaffected).
- `cd frontend && npm test` → **148 passed** (unaffected).
- `npm run build` → built clean; `npm run lint` → clean.

## Validation NOT performed / REQUIRES YOUR HANDS (criterion 2, 3, and the
## runtime half of 5)

The following could not be run by me and are required before this can be
called a PASS:

1. `cargo tauri dev` — confirm fonts render, a real Mix run streams end to end
   (backend reachable), and zero CSP violations in the webview console.
2. `cargo tauri build` then LAUNCH the produced package (not just build it) —
   same three checks, specifically the production `http://tauri.localhost:8001`
   connect path this mission's policy now permits.
3. Confirm `'unsafe-inline'` on `style-src` is genuinely needed (check the
   console while the app runs; if no inline-style violation appears, it can be
   tightened to `style-src 'self' https://fonts.googleapis.com` and this
   directive shrinks accordingly).

## Doc updates

- `PUNCH-BOARD.md` item 34 → CSP hardening now addressed; still OPEN only on
  MSI bundle, code signing, and dynamic ports (and the real frozen-build
  credential-path run). Note the CSP change itself needs the user's runtime
  confirmation before item 34 advances further.
- `MISSION-INDEX.md` (row + result), `ENGINEERING-PROGRESS.md` (result)
  updated.

## Remaining risks / open items

- The `'unsafe-inline'` `style-src` directive and the production
  `connect-src` origin are my best read of the repo, not runtime-verified.
- The packaged-app runtime proof (fonts + real Mix stream + zero CSP console
  errors) is outstanding and blocks a full PASS.