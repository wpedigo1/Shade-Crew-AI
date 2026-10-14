# Mission 025 — Harden the Local Backend Boundary

## Objective

Require admin authentication (`_require_admin`, reused exactly as-is) on every
backend endpoint that reads/writes/uses stored credentials or makes a server
outbound request using a client-influenced target or credential.

Base: `main @ a1cea42` (Mission 024). All work committed on `main`.

## What changed

`backend/main.py` — added `dependencies=[Depends(_require_admin)]` to the
decorator of **20 endpoints** (16 required + 4 judgment-call extensions). No
handler bodies, no credential-store logic, and `_require_admin` itself were
modified.

New coverage: `backend/tests/test_admin_guard_credential_endpoints.py` (27
tests) proving rejection/allowance for each newly-guarded endpoint.

Three existing tests that hit a newly-guarded endpoint via a non-loopback
TestClient peer were switched to a loopback peer (`127.0.0.1`), which is the
legitimate local-operator case:
`test_font_size.py`, `test_advisor_presets.py`, `test_council_presets.py`
(one-line change each).

## `_require_admin` semantics (unchanged)

- If `LLM_COUNCIL_ADMIN_TOKEN` is set → require `Authorization: Bearer <token>`
  (401 otherwise), via `secrets.compare_digest`.
- Else → allow only loopback TCP peers (`127.0.0.1`, `::1`, `localhost`),
  plus forwarded-header spoofing protection (`_forwarded_client_hosts`).
  403 otherwise.
- Token branch reads `_ADMIN_TOKEN` from module globals at call time.

## Endpoint audit table

Legend: **Guard: New** = added in this mission; **Guard: Existing** = was
already guarded in base. **Justification** = why the endpoint is in or out of
scope.

### Guarded (newly) — required list (16)

| Method + Path | Guard | Why guarded |
|---|---|---|
| PUT `/api/settings` | New | Writes API keys into credential store (`apply_settings_secret_updates` → `set_secret`) |
| POST `/api/settings/credential-storage` | New | Migrates credential storage mode (keyring ↔ file) |
| POST `/api/oauth/{provider_id}/start` | New | Starts OAuth session writing provider tokens |
| GET `/api/oauth/{provider_id}/status` | New | Reads OAuth credential state |
| DELETE `/api/oauth/{provider_id}` | New | Disconnects/removes provider credentials |
| GET `/api/credentials/import/relay-ai/discover` | New | Reads client OS keystore/credential files |
| POST `/api/credentials/import/relay-ai` | New | Writes imported credentials to store |
| POST `/api/settings/test-tavily` | New | Uses stored/request API key, server outbound |
| POST `/api/settings/test-brave` | New | Same |
| POST `/api/settings/test-serper` | New | Same |
| POST `/api/settings/test-tinyfish` | New | Same |
| POST `/api/settings/test-provider` | New | Same |
| POST `/api/settings/test-opencode` | New | Same |
| POST `/api/settings/test-ollama` | New | Uses client-supplied `base_url` for server GET (SSRF) |
| POST `/api/settings/test-custom-endpoint` | New | **SSRF → stored-key exfiltration** (see below) |
| POST `/api/settings/test-openrouter` | New | Uses stored/request key, server outbound |

### Guarded (newly) — judgment-call extensions (4)

| Method + Path | Guard | Why guarded |
|---|---|---|
| GET `/api/models/direct` | New | Uses stored keys + iterates direct providers outbound |
| GET `/api/models` | New | Uses stored OpenRouter key (`get_openrouter_api_key`) outbound |
| GET `/api/ollama/tags` | New | Client-supplied `base_url` query → server GET (SSRF) |
| GET `/api/custom-endpoint/models` | New | Uses stored custom-endpoint URL + stored key outbound |

These four trigger server outbound requests whose target/key derives from
client-influenced or stored credential state; the objective's "any other
endpoint" clause covers them. Loopback browsers keep working (no frontend
change).

### Already guarded (pre-existing, unchanged)

| Method + Path | Why |
|---|---|
| GET `/api/settings/export` | Contains full credential values |
| POST `/api/settings/import` | Writes credentials |
| POST `/api/settings/reset` | Destructive settings/credential reset |
| POST `/api/settings/disconnect-all-providers` | Wipes credential store |

### Not guarded — intentionally (verified)

| Method + Path | Why not |
|---|---|
| GET `/api/settings` | Returns only `*_key_set` booleans + `custom_endpoint_url`; **no credential values leaked** (`build_settings_response`) |
| GET `/api/settings/defaults` | Static defaults, no credentials, no outbound |
| PUT `/api/settings/relay-ai-import-dismissed` | UI flag only; no credential access, no outbound |

## SSRF → credential-exfiltration path (test-custom-endpoint)

`POST /api/settings/test-custom-endpoint` forwards a client-supplied `url` to
`CustomOpenAIProvider.validate_connection`; when the request omits `api_key`,
`resolve_api_key` falls back to the **stored** credential. On a server reachable
from the attacker's origin, this was a blind SSRF-to-credential path
(server-side call, CORS irrelevant). Guarding it rejects the request (401/403)
**before** any outbound call. Test proves `validate_connection` is never
awaited for a rejected non-loopback request with an arbitrary URL and omitted
key.

## Acceptance verification (observed)

- **Non-loopback, no token → rejected** on every one of the 20 newly-guarded
  endpoints (parametrized; 401 when a token is configured, 403 otherwise).
- **Loopback, no token → reaches the handler** (regression: local operator).
- **Non-loopback + correct bearer token → success** (only possible when
  `LLM_COUNCIL_ADMIN_TOKEN` is set; matches existing `_require_admin` token
  branch).
- **`test-custom-endpoint` SSRF rejected before outbound** — spy on
  `CustomOpenAIProvider.validate_connection` asserted never awaited for a
  rejected non-loopback request.
- **Non-loopback-with-token and loopback success** proofs use
  `PUT /api/settings` (handler-side effects mocked to return a valid response)
  and `test-custom-endpoint` (provider mocked), so no real outbound or
  credential IO occurs during tests.

## Validation actually run

| Command | Result |
|---|---|
| `uv run pytest backend/tests -q -k "admin or credential or settings" --basetemp ...` | 71 passed |
| `uv run pytest backend/tests -q --basetemp ...` | 431 passed (404 original + 27 new) |
| `uv run ruff check backend` | All checks passed |
| `cd frontend && npm test` | 12 files / 118 tests passed |
| `cd frontend && npm run build` | built in 1.56s |
| `cd frontend && npm run lint` | clean |
| `git status --short` / `git diff --stat` | only intended files |

Notes: `tmp_path`-based tests were run with
`--basetemp "C:\Users\wpedi\AppData\Local\Temp\opencode\pt..."` (the default
pytest temp dir is PermissionError-locked on this machine).

## Flagged follow-ups (NOT changed, per scope)

1. **CORS regex** (`_dev_cors_regex`, `main.py` ~line 332):
   `(?:\d{1,3}\.){3}\d{1,3}` matches **any** dotted-IPv4 origin, not just
   private/loopback ranges. Not modified in this mission (out of scope);
   recommend a follow-up review.
2. **Arbitrary custom-endpoint URL SSRF** is now admin-gated, but a
   loopback-local attacker (or a compromised local process) could still point
   the custom-endpoint URL at an internal host. Recommend a separate
   follow-up to reconsider URL allow-listing for custom endpoints.
3. `resolve_api_key` fallback precedence (request value → credential store →
   legacy settings.json field) is intentionally untouched and consistent with
   prior missions.

## Assumptions

- Loopback browser access (the whole purpose of the local backend) is
  preserved; the frontend calls all guarded endpoints via `API_BASE`
  (localhost) → loopback peer → unauthenticated OK.
- Extending scope to `GET /api/models`, `GET /api/models/direct`,
  `GET /api/ollama/tags`, and `GET /api/custom-endpoint/models` is an explicit
  judgment call under the objective's "any other endpoint" clause; each is
  documented above.
- No new dependencies, no frontend changes, no changes to
  `backend/modelmix/*` or the credential-store contract.

## Remaining risks / unresolved

- Token-branch correctness relies on the single pre-existing proof for
  `_require_admin`'s token path (export test) plus the new-put-settings token
  test here; no per-endpoint token test was added for all 20 (token path is a
  single shared branch, not per-endpoint logic).
- The two flagged follow-ups above remain open.
