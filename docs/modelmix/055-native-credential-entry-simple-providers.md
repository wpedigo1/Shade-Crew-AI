# Mission 055 — Native Credential Entry in ModelMix Settings (Simple Providers)

Date: 2026-09-03 CT · Base: main @ `75054b9` (Mission 052)
· Punch Board item 26 (advance)

## Scope decision

ModelMix can route to 15 real provider prefixes (`backend/council.py::PROVIDERS`).
Three are OAuth-based (`xai-oauth`, `openai-oauth`, `github-copilot`) and need a
connect/disconnect redirect flow, not a text field — those are explicitly OUT of
scope and deferred to a separate, later mission. This mission covers the
remaining 12 simple providers: `openai`, `anthropic`, `google`, `mistral`,
`deepseek`, `groq`, `nvidia`, `openrouter`, `opencode-zen`/`opencode-go` (one
shared key), `ollama` (a URL, not a key), and `custom` (name + URL + key).

## What changed — frontend only, zero backend changes

### `frontend/src/modelmixApi.js` (new functions following the existing `checkedFetch` pattern)

- `updateSettings(body)` → `PUT /api/settings` with a JSON partial body.
- `testProvider(providerId, apiKey?)` → `POST /api/settings/test-provider`
  body `{provider_id, api_key?}`.
- `testOpenrouter(apiKey?)` → `POST /api/settings/test-openrouter`.
- `testOpencode(apiKey?)` → `POST /api/settings/test-opencode`.
- `testOllama(baseUrl)` → `POST /api/settings/test-ollama` body `{base_url}`.
- `testCustomEndpoint(name, url, apiKey?)` → `POST /api/settings/test-custom-endpoint`.

Each test function POSTs to the **exact** `_require_admin`-guarded endpoint
Counsel already uses and returns the real JSON result — nothing fabricated.
`api_key`/`apiKey` is omitted entirely when not supplied, so the server's
stored-secret resolver (`resolve_api_key`) path still works.

### `frontend/src/components/ModelMixObserver.jsx` (Providers section)

The existing connected/not-connected READ list (`configuredSources`) is kept
verbatim (same 5 rows, same classes), and the section now additionally renders:

- A **write-only** password-masked key input for each key provider (OpenRouter;
  OpenAI, Anthropic, Google, Mistral, DeepSeek, Groq, NVIDIA; OpenCode Zen+Go
  sharing one key). Inputs always start empty — a saved value is never pre-filled
  or echoed; the connected indicator is how the user knows a credential exists.
- A **URL** input for Ollama's base URL.
- **name + URL + optional key** inputs for the custom endpoint (blank key allowed
  for local servers).
- A **Test** button per provider calling the correct existing test endpoint and
  rendering the real returned success/failure message (`result.message`), with a
  truthful status role and success/error styling.
- A **Save** action that PUTs **only the edited field(s)** via the existing
  partial-merge `PUT /api/settings`, then re-fetches settings so the READ status
  updates.

The former "Manage providers in council settings" link is now scoped and
reworded to "OAuth providers (xAI, ChatGPT, GitHub Copilot) are still managed in
council settings" — reflecting that the 12 simple providers are now handled
natively.

### `frontend/src/components/ModelMixObserver.css` (styles only)

Added `.modelmix-credential-editors`, `.modelmix-credential-row`,
`.modelmix-cred-name`, `.modelmix-cred-hint`, `.modelmix-cred-controls`,
`.modelmix-cred-test`, `.modelmix-cred-save`, `.modelmix-cred-result` and
`--ok`/`--err` variants, matching the existing settings palette.

## Security posture

- Reuses the existing, already-`_require_admin`-guarded `PUT /api/settings` and
  `test-*` endpoints — no new endpoint, no new write path, no new auth wiring.
- The loopback admin guard is independent of which frontend page makes the
  request (same browser, same machine), so the ModelMix Settings shell works
  without any new auth code.
- Write-only inputs: never pre-fill or render a saved credential value in the
  DOM (verified by a test asserting no `sk-` text and an empty input even when
  the key is configured).
- No backend change, so the existing secure-credential-reference behavior is
  untouched.

## Boundaries honored (hard)

- Zero backend changes: `PUT /api/settings`, all `test-*` endpoints, and every
  other backend route untouched.
- No UI for `xai-oauth`, `openai-oauth`, or `github-copilot` — explicitly
  deferred.
- No input field ever pre-fills or displays a previously-saved credential value.
- `Settings.jsx` (Counsel's own settings component) not touched at all.
- No new backend dependency, endpoint, or model.
- No `schema_version` change — this touches no persisted ModelMix run data.

## Tests

### `frontend/src/modelmixApi.test.js` (+11)

Exact request-body verification for each new function: `updateSettings` PUTs
only the provided field(s) (single key; ollama URL; custom fields without key);
`testProvider` (with and without `api_key`); `testOpenrouter` (with and without);
`testOpencode`; `testOllama`; `testCustomEndpoint` (with and without `api_key`).

### `frontend/src/components/ModelMixSettings.test.jsx` (+11)

- Write-only password inputs start empty even when `openai_api_key_set: true`,
  and no saved value leaks into the document.
- Save PUTs only that field for a plain API-key provider, ollama URL, and the
  3-field custom endpoint (blank-key case omits `api_key`); custom-with-key case
  includes it.
- Test calls the correct endpoint and renders the real returned message, for
  provider (success), openrouter (failure), ollama, and custom.
- READ status updates to Connected after a successful save via the refetch.
- Council-settings link is scoped to OAuth providers only.

All 7 acceptance criteria are covered. Existing frontend tests pass unmodified.

## Validation (observed)

- `cd frontend && npm test` → **203 passed** (18 files; 181 prior + 22 new).
- `npm run build` → built clean (440 modules, `✓ built`).
- `npm run lint` → clean (no output, exit 0).
- `cd .. && uv run pytest backend/tests -q --basetemp=...` → **544 passed**
  (unchanged; backend files never modified, confirmed via `git status`).
- `git status --short` and `git diff --stat` captured in the commit.

## Doc updates

- `PUNCH-BOARD.md` item 26 — added Mission 055; credential/endpoint entry for
  the 12 simple providers now natively in ModelMix; OAuth providers noted as a
  separate, later mission.
- `MISSION-INDEX.md` — added Mission 055 table row + Result section.
- `ENGINEERING-PROGRESS.md` — added Mission 055 Result.

## Remaining risks / open items

- OAuth-based providers (xAI, ChatGPT/ChatGPT-openai-oauth, GitHub Copilot)
  remain a separate, later mission still linked to Council settings.
- The custom endpoint and per-provider "disconnect/clear" affordances are not
  built here; users can still disconnect via Council settings.
- Settings snapshot staleness: if two tabs edit credentials concurrently, the
  optimistic refetch reflects the server state at save time; no cross-tab sync
  was added.
