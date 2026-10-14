# Mission 041 — Dead Code Inventory (Tool-Driven, Report Only)

Route: Big Pickle (OpenCode Zen)
Punch Board item: **46. Prune dead Council/Advisor/debate code — OPEN** (this
mission is the inventory; item 46 stays OPEN).
Base: `main` @ `1f7c6d4` "feat(modelmix): durable structured logging
(Mission 040)".

Result: **PASS**. Two real dead-code detectors ran against the real codebase.
Every finding was independently confirmed or explained. **Zero code files
modified** — `git diff --stat` shows documentation only.

## 1. What ran

| Tool | Target | Version | Install method | Scope |
|------|--------|---------|----------------|-------|
| `vulture` | `backend/` | latest | `uvx` (one-off, not a project dep) | Python dead code (functions, variables, attributes, classes) |
| `npx depcheck` | `frontend/` | latest | `npx --yes` (one-off, not a project dep) | Unused npm dependencies |
| `npx unimported` | `frontend/` | latest | `npx --yes` (one-off) | Unused source files |

## 2. Backend — vulture raw output

```text
backend/config.py:43: unused variable 'OPENROUTER_API_KEY' (60% confidence)
backend/config.py:44: unused variable 'COUNCIL_MODELS' (60% confidence)
backend/config.py:50: unused variable 'CHAIRMAN_MODEL' (60% confidence)
backend/council.py:71: unused function 'query_models_parallel' (60% confidence)
backend/credentials/ids.py:44: unused variable 'SECRET_ID_TO_SETTINGS_FIELD' (60% confidence)
backend/credentials/ids.py:72: unused variable 'OAUTH_CONNECTED_FLAGS' (60% confidence)
backend/credentials/ids.py:79: unused function 'api_secret_id' (60% confidence)
backend/credentials/ids.py:83: unused function 'oauth_secret_id' (60% confidence)
backend/credentials/keyring_backend.py:15: unused function '_entry' (60% confidence)
backend/credentials/store.py:380: unused function 'secret_id_for_settings_field' (60% confidence)
backend/documents.py:44: unused variable 'document_timeout_seconds' (60% confidence)
backend/main.py:426: unused function 'extract_documents_endpoint' (60% confidence)
backend/main.py:438: unused function 'extract_documents_json_endpoint' (60% confidence)
backend/main.py:617: unused variable 'created_at' (60% confidence)
backend/main.py:620: unused variable 'message_count' (60% confidence)
backend/main.py:630: unused variable 'created_at' (60% confidence)
backend/main.py:639: unused function 'health_check' (60% confidence)
backend/main.py:663: unused function 'modelmix' (60% confidence)
backend/main.py:704: unused function 'get_conversation_progress' (60% confidence)
backend/main.py:747: unused function 'send_message_stream' (60% confidence)
backend/main.py:974: unused function 'send_debate_message_stream' (60% confidence)
backend/main.py:1211: unused function 'list_personas' (60% confidence)
backend/main.py:1222: unused variable 'avatar_emoji' (60% confidence)
backend/main.py:1225: unused function 'update_persona' (60% confidence)
backend/main.py:1234: unused function 'reset_persona' (60% confidence)
backend/main.py:1243: unused function 'start_debate_stream' (60% confidence)
backend/main.py:1377: unused function 'send_message_sync' (60% confidence)
backend/main.py:1439: unused function 'ask_oneshot' (60% confidence)
backend/main.py:1636: unused function 'get_app_settings' (60% confidence)
backend/main.py:1643: unused function 'get_default_settings' (60% confidence)
backend/main.py:1657: unused function 'export_settings' (60% confidence)
backend/main.py:1672: unused function 'import_settings' (60% confidence)
backend/main.py:1682: unused function 'reset_settings' (60% confidence)
backend/main.py:1690: unused function 'disconnect_all_providers' (60% confidence)
backend/main.py:1711: unused function 'update_app_settings' (60% confidence)
backend/main.py:1949: unused function 'set_credential_storage' (60% confidence)
backend/main.py:1960: unused class 'OAuthStartResponse' (60% confidence)
backend/main.py:1963: unused variable 'user_code' (60% confidence)
backend/main.py:1964: unused variable 'verification_uri' (60% confidence)
backend/main.py:1965: unused variable 'verification_uri_complete' (60% confidence)
backend/main.py:1970: unused function 'oauth_start' (60% confidence)
backend/main.py:1980: unused function 'oauth_status' (60% confidence)
backend/main.py:1985: unused function 'oauth_disconnect' (60% confidence)
backend/main.py:1994: unused function 'relay_ai_discover' (60% confidence)
backend/main.py:1999: unused function 'relay_ai_import' (60% confidence)
backend/main.py:2012: unused function 'dismiss_relay_import' (60% confidence)
backend/main.py:2021: unused function 'get_direct_models' (60% confidence)
backend/main.py:2042: unused function 'test_tavily_api' (60% confidence)
backend/main.py:2081: unused function 'test_brave_api' (60% confidence)
backend/main.py:2120: unused function 'test_serper_api' (60% confidence)
backend/main.py:2158: unused function 'test_tinyfish_api' (60% confidence)
backend/main.py:2199: unused function 'test_provider_api' (60% confidence)
backend/main.py:2221: unused function 'test_opencode_key' (60% confidence)
backend/main.py:2249: unused function 'get_ollama_tags' (60% confidence)
backend/main.py:2290: unused function 'test_ollama_connection' (60% confidence)
backend/main.py:2321: unused function 'test_custom_endpoint' (60% confidence)
backend/main.py:2331: unused function 'get_custom_endpoint_models' (60% confidence)
backend/main.py:2346: unused function 'get_openrouter_models' (60% confidence)
backend/main.py:2406: unused function 'test_openrouter_api' (60% confidence)
backend/modelmix/journal.py:28: unused variable 'created_at' (60% confidence)
backend/modelmix/routes.py:73: unused function 'stream_two_workers' (60% confidence)
backend/modelmix/routes.py:118: unused function 'get_session' (60% confidence)
backend/modelmix/routes.py:129: unused function 'replay_run_events' (60% confidence)
backend/modelmix/routes.py:152: unused function 'cancel_run' (60% confidence)
backend/oauth/types.py:65: unused function 'parse_stored_oauth_credential' (60% confidence)
backend/ollama_client.py:96: unused function 'query_models_parallel' (60% confidence)
backend/openrouter.py:132: unused function 'query_models_parallel' (60% confidence)
backend/openrouter.py:188: unused function 'fetch_models' (60% confidence)
backend/personas.py:22: unused variable 'avatar_emoji' (60% confidence)
backend/providers/base.py:52: unreachable code after 'raise' (100% confidence)
backend/search.py:936: unused function '_fetch_with_jina_sync' (60% confidence)
backend/settings.py:90: unused variable 'AVAILABLE_MODELS' (60% confidence)
backend/tests/test_advisor_presets.py:80: unused attribute 'side_effect' (60% confidence)
backend/tests/test_advisors_backend.py:22: unused variable 'SKEPTIC' (60% confidence)
backend/tests/test_advisors_backend.py:23: unused variable 'PRAGMATIST' (60% confidence)
backend/tests/test_advisors_backend.py:24: unused variable 'INNOVATOR' (60% confidence)
backend/tests/test_advisors_backend.py:421: unused attribute 'side_effect' (60% confidence)
backend/tests/test_advisors_backend.py:460: unused attribute 'side_effect' (60% confidence)
backend/tests/test_advisors_backend.py:534: unused attribute 'side_effect' (60% confidence)
backend/tests/test_council_presets.py:72: unused attribute 'side_effect' (60% confidence)
backend/tests/test_credentials_availability.py:21: unused class 'P' (60% confidence)
backend/tests/test_credentials_file_hardening.py:26: unused function '_reset_process_guards' (60% confidence)
backend/tests/test_credentials_file_hardening.py:51: unused function '_raising' (60% confidence)
backend/tests/test_font_size.py:38: unused attribute 'side_effect' (60% confidence)
backend/tests/test_font_size.py:39: unused attribute 'side_effect' (60% confidence)
backend/tests/test_logging_config.py:18: unused function '_isolate_logging_config' (60% confidence)
backend/tests/test_modelmix_cancel_race.py:32: unused attribute 'cancelled_seen' (60% confidence)
backend/tests/test_modelmix_cancel_race.py:48: unused attribute 'cancelled_seen' (60% confidence)
backend/tests/test_oauth_openai_chatgpt.py:24: unused attribute 'side_effect' (60% confidence)
backend/tests/test_oauth_xai.py:24: unused attribute 'side_effect' (60% confidence)
backend/tests/test_opencode_provider.py:8: unused function '_isolate_opencode_credentials' (60% confidence)
backend/tests/test_opencode_provider.py:38: unused attribute 'entered' (60% confidence)
backend/tests/test_opencode_provider.py:42: unused attribute 'entered' (60% confidence)
backend/tests/test_personas.py:22: unused function 'isolated_overrides' (60% confidence)
backend/tests/test_settings_backup.py:19: unused function '_make_settings_with_keys' (60% confidence)
```

## 3. Backend — confirmed unreachable (independent evidence)

These are vulture-flagged symbols with **zero references** anywhere in the
repository — no imports, no qualified access, no test calls, no dynamic
dispatch (confirmed via whole-repo `git grep`). They are safe candidates for
removal in a later mission.

### 3.1 config.py — 3 legacy constants (9 lines)

`OPENROUTER_API_KEY` (line 43), `COUNCIL_MODELS` (lines 44-49), and
`CHAIRMAN_MODEL` (line 50) are explicitly commented "Legacy constants for
backwards compatibility." None is imported by any other module (all import
lines in the repo reference the getter functions `get_council_models`,
`get_chairman_model`, `get_openrouter_api_key` instead). `git grep` for
each as a bare token across the whole repo finds them only at their own
definition lines (plus the `"OPENROUTER_API_KEY"` string in `ids.py`
`ENV_OVERRIDES` — a dict value, not the config variable). The env-var
string `"OPENROUTER_API_KEY"` also appears in tests as `monkeypatch.setenv`
and credential-map strings; those reference the env var name, not the
config module constant. All three are genuinely dead.

### 3.2 settings.py — AVAILABLE_MODELS list (24 lines, lines 89-112)

`AVAILABLE_MODELS` is a hardcoded "popular OpenRouter models" list. `git
grep -rn "AVAILABLE_MODELS"` finds only its own definition line — zero
imports, zero references anywhere. The frontend models dropdown now uses the
live `/api/models` and `/api/models/direct` endpoints (the vulture-flagged
route handlers at main.py lines 2021/2346 that are the ACTUAL live code).
Dead: a candidate for removal.

### 3.3 credentials/ids.py — 4 symbols (13 lines total)

* `SECRET_ID_TO_SETTINGS_FIELD` (line 44): reverse mapping dict `{v: k for k, v in ...}`. `SETTINGS_FIELD_TO_SECRET_ID` (forward direction) is imported by `store.py`, `upgrade.py`, `settings.py`, `settings_payload.py`; the REVERSE `SECRET_ID_TO_SETTINGS_FIELD` is imported by nobody. `git grep` finds it only at its own definition line.
* `OAUTH_CONNECTED_FLAGS` (lines 72-76): dict mapping provider IDs to "connected" flag names. `git grep` finds only its own definition line — not imported by `main.py`, `oauth/sessions.py`, or any other module. The settings payload builds connected flags differently (inline, not via this dict).
* `api_secret_id(provider)` (lines 79-80): trivial function `f"api:{provider}"`. `git grep` finds only its own `def` line — never called.
* `oauth_secret_id(provider_id)` (lines 83-84): wraps `OAUTH_SECRET_IDS.get(provider_id)`. `git grep` finds only its own `def` line — never called.

All four are independently confirmed unreachable (module is imported, but these specific symbols are never referenced).

### 3.4 credentials/store.py — secret_id_for_settings_field (2 lines)

`secret_id_for_settings_field(field)` at line 380 does `SETTINGS_FIELD_TO_SECRET_ID.get(field)`. `git grep` finds only its own definition. The caller that needs this logic (`apply_settings_secret_updates`, immediately below it) uses `SETTINGS_FIELD_TO_SECRET_ID.items()` directly instead. The function wrapper is dead.

### 3.5 documents.py — DocumentLimits.document_timeout_seconds (1 line)

`document_timeout_seconds` at line 44 is a class attribute of `DocumentLimits`. `git grep` finds it only at its own definition — no code accesses `limits.document_timeout_seconds` anywhere (main.py constructs `DocumentLimits()` but never reads this attribute; tests override other attributes like `max_document_chars`, `max_ocr_pages`). The env var `LLM_COUNCIL_DOCUMENT_TIMEOUT_SECONDS` is read but never consumed — the actual timeout must be hardcoded elsewhere. Dead.

### 3.6 council.py — query_models_parallel (27 lines, lines 71-97)

Free function at module level. `git grep` finds it only at its own definition line and one comment (line 84: `# 'openrouter.query_models_parallel' was doing the gather`). It is never imported or called. `stage1_collect_responses` (line 133) does its own inline `asyncio.gather` instead. Dead.

### 3.7 ollama_client.py — query_models_parallel (22 lines, lines 96-117)

Same function name, separate standalone function. `git grep` finds only its own `def` line — never imported, never called, no cross-reference from `main.py` or anywhere else. Dead.

### 3.8 openrouter.py — query_models_parallel + fetch_models (118 lines total)

* `query_models_parallel` (lines 132-187): standalone function, never called. `OpenRouterProvider` (the live class in the same file) is what `main.py` uses via `providers/openrouter.py`. `git grep` finds the function name only at its own `def` line and in `council.py:84` as a prose comment. Dead.
* `fetch_models` (lines 188-249): standalone function, never called. `git grep` finds only its own `def` line. Dead.

Both functions are legacy wrappers from before the `OpenRouterProvider` class refactoring. Together they are 118 lines — the single largest dead-code block identified.

### 3.9 search.py — _fetch_with_jina_sync (27 lines, lines 936-962)

Synchronous wrapper around a Jina fetch. `git grep` finds only its own `def` line. The live code uses `_fetch_with_jina` (async) or the async streaming paths. Dead.

### 3.10 oauth/types.py — parse_stored_oauth_credential (16 lines, lines 65-80)

Function to parse a raw credential string into structured OAuth fields. `git grep` finds only its own `def` line — never imported or called. The actual credential parsing happens inline in `sessions.py` / `oauth_start` routes. Dead.

### 3.11 keyring_backend.py — _entry (4 lines, lines 15-18)

Stub: `import keyring; return keyring`. `git grep` finds only its own `def` line. Dead. (Not to be confused with `test_packaging_entrypoint.py`'s `_load_entry`/`ENTRY_PATH` — different symbol; a grep substring match is a false alarm.)

### 3.12 providers/base.py:52 — `yield` after `raise NotImplementedError` (1 line, 100% confidence)

`stream_query` raises `NotImplementedError` then has `yield` — unreachable code by control flow. This is **intentional and correct**: the `yield` makes the method an async generator so subclasses can override it as a generator. Marked `# pragma: no cover`. This is a standard Python abstract-async-generator pattern and must not be removed.

### Summary of confirmed-unreachable (backend)

| Symbol | File | Lines | Size |
|--------|------|-------|------|
| `OPENROUTER_API_KEY` (var) | `config.py` | 43 | 1 |
| `COUNCIL_MODELS` (list) | `config.py` | 44-49 | 6 |
| `CHAIRMAN_MODEL` (str) | `config.py` | 50 | 1 |
| `AVAILABLE_MODELS` (list) | `settings.py` | 89-112 | 24 |
| `SECRET_ID_TO_SETTINGS_FIELD` | `credentials/ids.py` | 44 | 1 |
| `OAUTH_CONNECTED_FLAGS` (dict) | `credentials/ids.py` | 72-76 | 5 |
| `api_secret_id()` | `credentials/ids.py` | 79-80 | 2 |
| `oauth_secret_id()` | `credentials/ids.py` | 83-84 | 2 |
| `secret_id_for_settings_field()` | `credentials/store.py` | 380-381 | 2 |
| `DocumentLimits.document_timeout_seconds` | `documents.py` | 44 | 1 |
| `query_models_parallel()` | `council.py` | 71-97 | 27 |
| `query_models_parallel()` | `ollama_client.py` | 96-117 | 22 |
| `query_models_parallel()` | `openrouter.py` | 132-187 | 56 |
| `fetch_models()` | `openrouter.py` | 188-249 | 62 |
| `_fetch_with_jina_sync()` | `search.py` | 936-962 | 27 |
| `parse_stored_oauth_credential()` | `oauth/types.py` | 65-80 | 16 |
| `_entry()` | `credentials/keyring_backend.py` | 15-18 | 4 |
| **Total** | | | **~263 lines** |

## 4. Backend — vulture false positives (explained)

### 4.1 FastAPI route handlers (`main.py`, `modelmix/routes.py`)

vulture reports "unused function" for every FastAPI route handler. FastAPI
registers functions via `@app.get`/`@app.post`/`@app.put`/`@app.delete`
decorators — the functions are called by HTTP requests from the frontend (or
from `httpx` test clients), not by direct Python import. vulture cannot see
decorator-based registration. Every flagged main.py function has an
immediately preceding `@app.get(...)` or `@app.post(...)` decorator (verified
by line-number inspection). Affected:

`extract_documents_endpoint` (426), `extract_documents_json_endpoint` (438),
`health_check` (639), `modelmix` (663), `get_conversation_progress` (704),
`send_message_stream` (747), `send_debate_message_stream` (974),
`list_personas` (1211), `update_persona` (1225), `reset_persona` (1234),
`start_debate_stream` (1243), `send_message_sync` (1377), `ask_oneshot`
(1439), `get_app_settings` (1636), `get_default_settings` (1643),
`export_settings` (1657), `import_settings` (1672), `reset_settings` (1682),
`disconnect_all_providers` (1690), `update_app_settings` (1711),
`set_credential_storage` (1949), `oauth_start` (1970), `oauth_status`
(1980), `oauth_disconnect` (1985), `relay_ai_discover` (1994),
`relay_ai_import` (1999), `dismiss_relay_import` (2012), `get_direct_models`
(2021), `test_tavily_api` (2042), `test_brave_api` (2081), `test_serper_api`
(2120), `test_tinyfish_api` (2158), `test_provider_api` (2199),
`test_opencode_key` (2221), `get_ollama_tags` (2249), `test_ollama_connection`
(2290), `test_custom_endpoint` (2321), `get_custom_endpoint_models` (2331),
`get_openrouter_models` (2346), `test_openrouter_api` (2406).

ModelMix routes: `stream_two_workers` (routes.py:73), `get_session` (118),
`replay_run_events` (129), `cancel_run` (152) — all `@router.post/get`
decorators on the ModelMix router, included via
`include_router(modelmix_router)` in main.py. All are live endpoints tested
by ModelMix alpha-acceptance tests.

**Verdict:** All false positives — all are reachable via HTTP.

### 4.2 Pydantic / dataclass model fields

vulture reports "unused variable" for fields on Pydantic `BaseModel` and
`@dataclass` classes. These are serialized to JSON by Pydantic's `model_dump()`
or `dict()` at runtime; vulture sees only direct attribute access and misses
serialization.

* `main.py:617` `created_at` — field of `ConversationMetadata` (Pydantic response model returned by `GET /api/conversations`). Returned to frontend as JSON.
* `main.py:620` `message_count` — same class, same reason.
* `main.py:630` `created_at` — field of a `Conversation` response model. Same.
* `main.py:1222` `avatar_emoji` — Pydantic field on the persona update request model. Sent from frontend persona editor UI, consumed by `personas.py` via `data.get("avatar_emoji")`. Heavily used (frontend `AdvisorSetup.jsx`, `AdvisorGrid.jsx`, `DebateView.jsx` all read `persona.avatar_emoji`).
* `main.py:1960` `OAuthStartResponse` class and its `user_code` (1963), `verification_uri` (1964), `verification_uri_complete` (1965) — Pydantic response model for `POST /api/oauth/{provider_id}/start`. Serialized to JSON and consumed by the OAuth device-code flow UI.
* `modelmix/journal.py:28` `created_at` — `@dataclass` field on `RunEventJournal` (uses `time.monotonic()` default factory). Read elsewhere in journal.py itself via `self.created_at` — vulture missed it.
* `personas.py:22` `avatar_emoji` — Pydantic `Persona` dataclass field, used by 12+ persona objects in `personas.py` and by the frontend.

**Verdict:** All false positives — all are serialized via Pydantic/dataclass.

### 4.3 providers/base.py:52 — unreachable `yield` after `raise` (100% confidence)

This is a **deliberate pattern**, not dead code. `stream_query` raises
`NotImplementedError` (making it abstract-ish for subclasses) then yields to
make it an async generator (so subclasses can override it as a generator). The
`yield` after `raise` is unreachable by control flow, but Python needs it to
recognize the function as a generator. Marked `# pragma: no cover`. Must not
be removed.

### 4.4 pytest fixtures, mock attributes, and autouse flags (`backend/tests/`)

vulture reports many test-only symbols as "unused" — these are pytest
fixtures (`@pytest.fixture(autouse=True)` decorated functions), mock
attributes (`side_effect`, `cancelled_seen`, `entered`), and test helper
variables (`SKEPTIC`, `PRAGMATIST`, `INNOVATOR`, `P`). All are consumed by
pytest's runtime discovery, not by direct imports. vulture does not see
pytest's fixture injection mechanism. This is expected and not actionable.

Affected test files: `test_advisor_presets.py`, `test_advisors_backend.py`,
`test_council_presets.py`, `test_credentials_availability.py`,
`test_credentials_file_hardening.py`, `test_font_size.py`,
`test_logging_config.py`, `test_modelmix_cancel_race.py`,
`test_oauth_openai_chatgpt.py`, `test_oauth_xai.py`, `test_opencode_provider.py`,
`test_personas.py`, `test_settings_backup.py`.

**Verdict:** All false positives — consumed by pytest runtime.

## 5. Frontend — depcheck + unimported raw output

### npx unimported

```
✓ There don't seem to be any unimported files.
```

No unused source files. All 24 frontend source files are imported (via
`App.jsx` or test files). Consistent with the mission's own framing that
Council components are actively used by Wes.

### npx depcheck

```
Unused devDependencies
* @types/react-dom
```

**One finding:** `@types/react-dom` (v19.2.3).

### depcheck finding — double confirmation

The frontend is **100% JavaScript/JSX** — no `.ts`/`.tsx`/`.d.ts` files exist,
and there is no `tsconfig.json`. Vite builds JSX directly via
`@vitejs/plugin-react` (Babel), not the TypeScript compiler. `@types/*`
packages provide TypeScript type declarations only; since no TypeScript
compilation or IDE TypeScript-check is configured in this project's build
pipeline, the types are never consumed.

`@types/react-dom` is never imported, never referenced in any config file,
and is a dev-only metadata package. **Confirmed genuinely unused** by this
project.

**Ambiguous companion:** `@types/react` is equally present but not flagged by
depcheck (it associates it with the used `react` package). By the same
no-TypeScript reasoning it is also unused by the build. However, it is the
standard companion package that `react-select` transitively declares as a
peer dependency (confirmed in `package-lock.json`: `react-select` depends on
`@types/react`). Removing `@types/react` could trigger peer-dep warnings; I
place it in **Ambiguous** rather than confirmed-unreachable.

**`@types/react-transition-group`** (transitive, in `package-lock.json`) is a
real dependency of `react-select` and is not a direct project dependency — no
action needed.

## 6. Deliverable — three-category breakdown

### Confirmed unreachable (safe to remove in a later mission)

| Symbol | File | Lines removed | Notes |
|--------|------|---------------|-------|
| `OPENROUTER_API_KEY` (var) | `config.py:43` | 1 | Legacy; getter `get_openrouter_api_key()` replaces it |
| `COUNCIL_MODELS` (list) | `config.py:44-49` | 6 | Legacy; getter `get_council_models()` replaces it |
| `CHAIRMAN_MODEL` (str) | `config.py:50` | 1 | Legacy; getter `get_chairman_model()` replaces it |
| `AVAILABLE_MODELS` (list) | `settings.py:89-112` | 24 | Hardcoded OpenRouter models list; `/api/models` provides live data |
| `SECRET_ID_TO_SETTINGS_FIELD` | `credentials/ids.py:44` | 1 | Reverse mapping never imported |
| `OAUTH_CONNECTED_FLAGS` (dict) | `credentials/ids.py:72-76` | 5 | Never imported |
| `api_secret_id()` | `credentials/ids.py:79-80` | 2 | Never called |
| `oauth_secret_id()` | `credentials/ids.py:83-84` | 2 | Never called |
| `secret_id_for_settings_field()` | `credentials/store.py:380-381` | 2 | Wrapper never called |
| `DocumentLimits.document_timeout_seconds` | `documents.py:44` | 1 | Class attribute never read |
| `query_models_parallel()` | `council.py:71-97` | 27 | Dead free function |
| `query_models_parallel()` | `ollama_client.py:96-117` | 22 | Dead free function |
| `query_models_parallel()` | `openrouter.py:132-187` | 56 | Dead legacy wrapper |
| `fetch_models()` | `openrouter.py:188-249` | 62 | Dead legacy wrapper |
| `_fetch_with_jina_sync()` | `search.py:936-962` | 27 | Sync wrapper, async path used instead |
| `parse_stored_oauth_credential()` | `oauth/types.py:65-80` | 16 | Never called |
| `_entry()` | `credentials/keyring_backend.py:15-18` | 4 | Dead stub |
| `@types/react-dom` | `frontend/package.json` | 1 dep | No TypeScript in this project |
| **Total** | | **~263 lines + 1 dep** | |

### False positives (vulture/depcheck flagged, genuinely reachable)

* **All 43 FastAPI route handlers** in `main.py` and `routes.py` — vulture
  cannot see `@app.get`/`@app.post` decorator-based registration; these are
  all HTTP endpoints called by the Council and ModelMix frontends.
* **All Pydantic/dataclass fields** (`created_at`, `message_count`,
  `avatar_emoji`, `OAuthStartResponse` fields, `RunEventJournal.created_at`)
  — vulture cannot see Pydantic's `model_dump()` serialization.
* **`providers/base.py:52` yield after raise** — intentional async-generator
  interface pattern, marked `# pragma: no cover`.
* **All 13 pytest fixture/attribute findings** — consumed by pytest runtime
  injection, not direct imports.

### Ambiguous

* **`@types/react`** (frontend devDep) — no TypeScript in the project, so
  technically unused by the build, but it is `react-select`'s declared peer
  dependency and is the standard companion package. Safe to remove in theory
  but requires testing `npm install` peer-dep behavior. Leaving alone until a
  dedicated frontend cleanup mission.

## 7. What a future removal mission would need to do

1. Remove confirmed-unreachable symbols from their source files (263 lines
   across 11 backend files, one frontend dep from package.json).
2. Run `uv run ruff check backend` — no import breakage expected (none of the
   symbols are imported anywhere).
3. Run `npm install && npm test && npm run build && npm run lint` — verify
   frontend unaffected by the `@types/react-dom` removal.
4. Regenerate `docs/modelmix/OPEN_SOURCE_CREDITS.md` and
   `docs/modelmix/licenses/THIRD-PARTY-LICENSES-frontend.txt` after the
   frontend dep removal (to remove the `@types/react-dom` entry).
5. Run full suite: `uv run pytest backend/tests -q` — no regressions expected.
6. Do NOT remove `providers/base.py:52` yield — it is intentional.

## 8. Validation (this mission touched no code — re-asserted)

```text
uv run pytest backend/tests -q --basetemp ... -> 485 passed in 33.70s
npx unimported -> no unimported files
npx depcheck   -> Unused devDependencies: @types/react-dom (as expected)
```

## 9. Files changed (this mission)

* `docs/modelmix/041-dead-code-inventory.md` (this report)
* `docs/modelmix/PUNCH-BOARD.md` — item 46 noted (still OPEN, inventory phase
  done)
* `docs/modelmix/MISSION-INDEX.md` — row 041
* `docs/modelmix/ENGINEERING-PROGRESS.md` — Mission 041 Result

Zero application code files modified — `git diff --stat` shows documentation
only.

## 10. Commit

`docs(modelmix): dead code inventory via vulture/depcheck (Mission 041)` —
pushed, verified local == origin == live remote.

## 11. Notes

* The three duplicate `query_models_parallel` functions (in `council.py`,
  `ollama_client.py`, and `openrouter.py`) tell a clear story: these were the
  original batch-call wrappers from before the `Provider` ABC and
  `OpenRouterProvider`/`OllamaProvider` class refactoring; the class methods
  replaced them, but the old free functions were never deleted. Together they
  are 105 lines — the single largest dead-code mass, all removable in one
  commit.
* `config.py`'s "Legacy constants for backwards compatibility" comment may
  indicate an earlier effort to support code that imported these directly. No
  such code exists in the current repo.
* Council/Advisor/debate code is a **live product** (Punch Board item 46's own
  framing confirms this). It is NOT dead — it is shared infrastructure. The
  confirmed-unreachable items above are genuinely dead (legacy function
  remnants and unused dict/constant definitions), not the Council pipeline
  itself.
