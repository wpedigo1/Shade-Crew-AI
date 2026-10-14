# Mission 042 — Remove Confirmed Dead Code

Route: Big Pickle (OpenCode Zen)
Punch Board item: **46. Prune dead Council/Advisor/debate code — CLOSE** (this
mission performs the removal that Mission 041 deferred).
Base: `main` @ `2c9366f` "docs(modelmix): dead code inventory via
vulture/depcheck (Mission 041)".

Result: **PASS**. Every symbol on Mission 041's confirmed-unreachable list was
re-grepped by me at removal time and confirmed dead with zero references
beyond their own definition (plus prose/tests string matches that are not
symbol references). Each was removed cleanly with no orphaned imports left
behind. Full validation passed. Item 46 is closeable.

## 1. Per-item re-confirmation (my own re-check, not relying on Mission 041)

Before removing each item I grepped the whole repo (`rg`, all file types)
and required zero references outside the definition site. Green = confirmed
dead at removal time.

| Item | Re-check result | Removed |
|------|-----------------|---------|
| `config.py` `OPENROUTER_API_KEY` | Only def line; all other hits are the getter `get_openrouter_api_key`, the `"OPENROUTER_API_KEY"` env-var string in `ids.py:48`, and `monkeypatch.setenv`/map strings in tests — not the config constant | Yes |
| `config.py` `COUNCIL_MODELS` | Only def line; other hits are getter `get_council_models` and `DEFAULT_COUNCIL_MODELS` (separate symbol) | Yes |
| `config.py` `CHAIRMAN_MODEL` | Only def line; other hits are getter `get_chairman_model` and `DEFAULT_CHAIRMAN_MODEL` | Yes |
| `settings.py` `AVAILABLE_MODELS` | Only def line; zero references anywhere | Yes |
| `ids.py` `SECRET_ID_TO_SETTINGS_FIELD` | Only def line | Yes |
| `ids.py` `OAUTH_CONNECTED_FLAGS` | Only def line | Yes |
| `ids.py` `api_secret_id` | Only def line | Yes |
| `ids.py` `oauth_secret_id` | Only def line | Yes |
| `store.py` `secret_id_for_settings_field` | Only def line | Yes |
| `documents.py` `document_timeout_seconds` | Only def line; not read anywhere | Yes |
| `council.py` `query_models_parallel` | Only def line + one prose comment (`council.py:84`); never imported/called | Yes |
| `ollama_client.py` `query_models_parallel` | Only def line | Yes |
| `openrouter.py` `query_models_parallel` | Only def line + council.py prose comment | Yes |
| `openrouter.py` `fetch_models` | Only def line | Yes |
| `search.py` `_fetch_with_jina_sync` | Only def line | Yes |
| `oauth/types.py` `parse_stored_oauth_credential` | Only def line | Yes |
| `keyring_backend.py` `_entry` | Only def line; `_entry` in other files are unrelated symbols | Yes |
| `@types/react-dom` | devDep; not imported/used anywhere; no TS in project | Yes |

## 2. What changed

Removed ~229 lines of dead code plus the `@types/react-dom` devDependency.

* `backend/config.py` — removed three legacy constants
  `OPENROUTER_API_KEY`, `COUNCIL_MODELS`, `CHAIRMAN_MODEL` (previously
  commented "Legacy constants for backwards compatibility"). The getter
  functions `get_openrouter_api_key`, `get_council_models`,
  `get_chairman_model` remain the live API. `os` import stays (still used by
  the env fallback inside `get_openrouter_api_key`).
* `backend/settings.py` — removed the hardcoded 24-line `AVAILABLE_MODELS`
  list (live model data comes from `/api/models`). No imports orphaned.
* `backend/credentials/ids.py` — removed `SECRET_ID_TO_SETTINGS_FIELD`,
  `OAUTH_CONNECTED_FLAGS`, `api_secret_id`, `oauth_secret_id`. Dropped the
  now-orphaned `Optional` from the `typing` import (`Optional` was used only
  by `oauth_secret_id`; `Dict`/`List` remain used).
* `backend/credentials/store.py` — removed `secret_id_for_settings_field`
  (its only logical caller, `apply_settings_secret_updates`, uses
  `SETTINGS_FIELD_TO_SECRET_ID.items()` directly).
* `backend/credentials/keyring_backend.py` — removed the `_entry` stub.
* `backend/documents.py` — removed the `DocumentLimits.document_timeout_seconds`
  field (never read; the env var `LLM_COUNCIL_DOCUMENT_TIMEOUT_SECONDS` was
  read into it but never consumed).
* `backend/council.py` — removed the dead `query_models_parallel` free
  function (and the prose comment referencing `openrouter.query_models_parallel`).
* `backend/ollama_client.py` — removed the dead `query_models_parallel` free
  function.
* `backend/openrouter.py` — removed the dead `query_models_parallel` and
  `fetch_models` free functions (118 lines, the largest block). `query_model`
  and the `OpenRouterProvider` class remain the live path.
* `backend/search.py` — removed the dead `_fetch_with_jina_sync` sync wrapper
  (the async `_fetch_with_jina` remains the live path).
* `backend/oauth/types.py` — removed the dead
  `parse_stored_oauth_credential` function.
* `frontend/package.json` — removed `@types/react-dom` devDependency.
* `frontend/package-lock.json` — lockfile regenerated; only the
  `@types/react-dom` entries (root dep + `node_modules/@types/react-dom`)
  were removed.

## 3. Orphaned-import hygiene

* `credentials/ids.py`: `Optional` removed from the `typing` import (sole
  consumer was `oauth_secret_id`).
* `config.py`: `os` retained (still used by the env fallback in the getter).
* `council.py`/`ollama_client.py`/`openrouter.py`: after removing
  `query_models_parallel`, `asyncio`/`List`/`Dict`/`Optional`/`Any` are still
  used by the retained functions — no orphans.
* `search.py`/`oauth/types.py`/`store.py`/`documents.py`/`keyring_backend.py`:
  no imports relied solely on the removed symbols.

## 4. Consequences observed (reported, not silently removed)

Two names became unreferenced as a cascade of the listed removals but are
**not** on Mission 041's confirmed list, so per the hard boundary I left them
in place and report them as new findings for a future mission (do not delete
code not on the list):

1. `backend/openrouter.py` `BROKEN_MODELS` (module constant) — was consumed
   only by the now-removed `fetch_models`. Now orphaned.
2. `backend/search.py` `get_sync_client` (module function) — was consumed
   only by the now-removed `_fetch_with_jina_sync`. Now orphaned.

Both are candidates for removal in a future cleanup; leaving them here honors
the "exactly the list above, report anything else" rule.

I also confirmed the alpha non-goal `@types/react` stays untouched (Mission
041 listed it as Ambiguous, not confirmed-unreachable) and none of the
false-positive categories (43 FastAPI routes, Pydantic/dataclass fields,
`providers/base.py:52` intentional generator yield, pytest fixtures) were
touched.

## 5. Validation (raw, unedited)

### Backend

The mission's literal command `uv run pytest backend/tests -q` currently
fails at pytest `tmp_path` fixture setup with an **environmental**
`PermissionError [WinError 5] Access is denied:
'C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo'`. That directory's ACL
is corrupted (owner ACL itself unreadable, `rmdir` yields access denied), so
every test that requests `tmp_path` errors during setup. This is unrelated to
this mission — it blocks any `tmp_path` test regardless of code changes, and
the 14 modified files all still collect cleanly (the errors are pure
`tmp_path` setup permission failures, not import/NameError/syntax failures).

To actually validate my changes, I reran with `--basetemp` pointed at a fresh
directory:

```text
485 passed in 32.52s
```

Clean, zero failures. The remaining backend suite (all non-`tmp_path` tests)
passed under the literal command too (`262 passed` in the 223-error run, all
223 being `tmp_path` setup permission errors).

### Frontend

```text
> the-ai-counsel@0.11.4 test
> vitest run

 Test Files  15 passed (15)
      Tests  138 passed (138)
```

```text
> the-ai-counsel@0.11.4 build
> vite build

✓ built in 2.67s
```

```text
> the-ai-counsel@0.11.4 lint
> eslint .

(clean — no output)
```

### git status --short / git diff --stat

```text
 M backend/config.py
 M backend/council.py
 M backend/credentials/ids.py
 M backend/credentials/keyring_backend.py
 M backend/credentials/store.py
 M backend/documents.py
 M backend/oauth/types.py
 M backend/ollama_client.py
 M backend/openrouter.py
 M backend/search.py
 M backend/settings.py
 M frontend/package-lock.json
 M frontend/package.json
```

`git diff --stat` shows only those 13 files — exactly the files containing the
listed symbols plus `package.json` and the lockfile. No unrelated changes.

## 6. Files changed (this mission)

* 11 backend source files (list above)
* `frontend/package.json`, `frontend/package-lock.json`
* `docs/modelmix/042-remove-confirmed-dead-code.md` (this report)
* `docs/modelmix/PUNCH-BOARD.md` — item 46 marked CLOSED
* `docs/modelmix/MISSION-INDEX.md` — row 042
* `docs/modelmix/ENGINEERING-PROGRESS.md` — Mission 042 Result

## 7. Commit

`chore(modelmix): remove confirmed dead code (Mission 042)` — committed and
pushed, verified local == origin.

## 8. Notes

* No `schema_version` bump and no new dependencies were introduced.
* No credits/license regeneration was performed in this mission; Mission 041's
  §7 step 4 suggested regenerating `OPEN_SOURCE_CREDITS.md` /
  `THIRD-PARTY-LICENSES-frontend.txt` after the frontend dep removal. That
  remains an optional follow-up and is out of this mission's scope (the list
  mandated only `package.json` + lockfile for the frontend).
* `BROKEN_MODELS` and `get_sync_client` (see §4) should be folded into a
  future dead-code cleanup mission rather than addressed here.