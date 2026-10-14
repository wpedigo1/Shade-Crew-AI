# Mission 040 — Durable Structured Logging

Route: Big Pickle (OpenCode Zen)
Punch Board item: **32. Add basic structured observability** — **CLOSED**.
Base: `main` @ `010af4f` "fix(modelmix): deterministic query preprocessing
across process restarts (Mission 039)".

Result: **PASS**. The backend now has durable, rotating, structured logs at
`<user_data_dir>/logs/modelmix.log` with a timestamp/level/logger/message
format, a preserved console handler, `LLM_COUNCIL_LOG_LEVEL` control, and the
same Windows per-user ACL hardening as the credentials file. Full suite green
(485 = 477 + 8 new), `ruff` clean.

## 1. What was built

`backend/logging_config.py::configure_logging()`, stdlib only, no side effects
at import (must be called):

* `RotatingFileHandler` at `<resolve_user_data_dir()>/logs/modelmix.log`,
  `encoding="utf-8"`, `maxBytes = 5 * 1024 * 1024`, `backupCount = 3`.
* Format `%(asctime)s %(levelname)s %(name)s: %(message)s`
  (`datefmt` `%Y-%m-%d %H:%M:%S`).
* Console `StreamHandler` on `sys.stderr` with the same root handlers, so
  `python -m backend.main` still prints to the terminal exactly as before.
* Level from `LLM_COUNCIL_LOG_LEVEL` (case-insensitive), default `INFO`; an
  invalid name falls back to `INFO`.
* Log directory created with `mkdir(parents=True, exist_ok=True)`.
* The log file is handed to the shared Windows ACL hardener immediately after
  configuration.
* One-shot: a second `configure_logging()` call is a no-op (guarded by a
  function attribute), so re-imports / test teardowns cannot double-configure.

Wired into `backend/main.py` right after the module imports, **before** the
FastAPI `app` is built (the existing `logger = logging.getLogger(__name__)`
line still follows), so every module-level log produced during bootstrap lands
in the file.

## 2. ACL de-duplication (reuse, not duplication)

The M040 task required sharing the credentials file's Windows hardening rather
than duplicating it. The `icacls` logic was extracted **verbatim** into
`backend/user_data_dir.py`:

* `is_windows()` — `sys.platform == "win32"` (loopback-safe for tests).
* `resolve_windows_current_user()` — the exact same USERNAME/USERDOMAIN →
  `os.getlogin()` fallback logic.
* `harden_user_dir(path)` — `icacls "<path>" /inheritance:r /grant:r "<user>":F`,
  catches `OSError`/`SubprocessError` and non-zero return, logs a warning on
  failure, never raises, no-op off Windows.

`backend/credentials/file_backend._harden_credentials_file()` now delegates to
`harden_user_dir(CREDENTIALS_FILE)` and sets `_hardened` on success. No
credentials behavior changed; the existing Mission 026/027 hardening tests were
retargeted to mock the shared helper's surface (sys.platform, `user_data_dir.is_windows`,
`user_data_dir.resolve_windows_current_user`, `user_data_dir.subprocess.run`)
and all still pass. The `-F` full-control grant on the log **file** mirrors the
credentials-file grant; `-R` recursion is intentionally not used (single file).

## 3. Credential-leak audit of `logger.*` call sites (acceptance criterion 5)

Audited **89** `logger.debug/info/warning/error/exception/critical` lines across
**17** backend source files. Method: full grep dump plus a review of every line
that references a variable that could plausibly hold or echo a secret.

Findings — **no credential value, API key, token, password, or request body is
logged**:

* **Credentials store/backends** (`credentials/store.py`, `file_backend.py`,
  `keyring_backend.py`, `relay_import.py`, `upgrade.py`) — log only secret
  *identifiers* (`secret_id`, `sid`), the file *path* (`CREDENTIALS_FILE`,
  `registry_path`), or counts. Never the secret value.
* **OAuth** (`oauth/sessions.py`, `oauth/refresh.py`) — `session_id`,
  `provider_id`. Never tokens or refresh-token values (the `"refresh failed"`
  string is prose about a failed refresh, not a token value).
* **Providers** (`providers/github_copilot.py`, `opencode.py`) — "Failed to
  refresh Copilot account plan" / "Failed to list Copilot models" with no
  interpolated secret; opencode logs response *dict keys* (`list(data.keys())`)
  and `model` ids, not values.
* **Search** (`search.py`) — logs truncate user queries to ~50 chars
  (`web_query[:50]`, `query[:50]`), URLs, HTTP status codes, or provider error
  text; the `*_API_KEY not set` messages log only the presence/absence of a key
  (a boolean), never its value. Note: `logger.error(f"...{e.response.text}")`
  on Tavily/Brave/Serper/TinyFish errors forwards the provider's HTTP error
  body — those are pre-existing call sites that M040 is expressly barred from
  modifying, and none has been observed to echo a key back; the risk is
  documented for future hardening rather than silently fixed here.
* **Core pipeline** (`council.py`, `debate.py`, `advisors.py`, `model_preflight.py`)
  — prompt-format errors, exceptions, stage transitions, model ids, attempt
  counts, status codes. No secrets.
* **`user_data_dir.py`** (new) — logs the path and icacls status only.

A **structural regression guard** was added as a test
(`test_no_credential_leak_in_logger_log_calls`): it scans every non-test
`backend/*.py` for `logger.*` lines containing a credential identifier token
(`api_key`, `apiKey`, `apikey`, `refresh_token`, `password`, `csrf`,
`authorization_header`, `secret_key`, `client_secret`, `access_token=`). The
token list deliberately avoids the bare word "token"/"Authorization" to prevent
false positives on valid prose like "access token". This is a structural audit
that complements — it cannot replace — the manual review above.

## 4. Tests (`backend/tests/test_logging_config.py`, 8 new)

Covering all six acceptance criteria, all hermetic (no real files written to
the user-data tree, no real `icacls`):

* `test_rotating_handler_at_expected_location` — RotatingFileHandler with the
  right class / `maxBytes` / `backupCount`, filename ends
  `logs\modelmix.log`.
* `test_env_level_controls_root_level`, `test_default_level_is_info_when_unset`,
  `test_invalid_env_level_falls_back_to_info` — `LLM_COUNCIL_LOG_LEVEL`
  Debug/INFO/invalid.
* `test_hardens_log_file_path` — on simulated Windows the log file path is
  passed to the shared hardener (mocked, no real `icacls`).
* `test_console_handler_present_alongside_file` — both console and file
  handlers attached to root.
* `test_no_credential_leak_in_logger_log_calls` — structural credential
  identifier scan (above).
* `test_configure_logging_is_idempotent` — second call is a no-op.

The existing `test_credentials_file_hardening.py` was updated only to retarget
the mock surface to the shared helper; all original assertions (correct icacls
args including `ACME\alice`, no icacls off Windows, failure-logging, once-per-
process remediation, already-hardened short-circuit) are preserved and pass.

## 5. Validation (all actually run)

```text
uv run ruff check backend                                  -> All checks passed
uv run pytest backend/tests -q --basetemp ...              -> 485 passed in 41.36s
  (baseline 477 + 8 new; --basetemp needed for the documented
   pytest-of-wpedigo temp-dir WinError 5 issue)
```

Direct end-to-end smoke: `python -c "from backend.main import app; ..."` with
`LLM_COUNCIL_LOG_LEVEL=DEBUG` booted the app and produced a real
`data\logs\modelmix.log` (dev mode). The file contained records in the exact
structured format, e.g.:

```text
2026-09-02 15:44:49 INFO backend.main: MCP server mounted at /mcp (SSE at /mcp/sse, messages at /mcp/messages)
```

and captured first-party (`backend.search`, `backend.providers.opencode`,
`backend.model_preflight`, `backend.credentials...`) plus third-party
(`httpx`, `httpx2`, MCP server) loggers at the configured level. The DEBUG
lines also reached the console, proving the console handler works side by side.
The smoke-created repo `data/logs/` tree was removed after verification (`data/`
is gitignored; this was a manual validation artifact only).

## 6. Files changed

* `backend/logging_config.py` — NEW; `configure_logging()`.
* `backend/user_data_dir.py` — ADD `is_windows()`, `resolve_windows_current_user()`,
  `harden_user_dir(path)` (extracted from file_backend).
* `backend/credentials/file_backend.py` — `_harden_credentials_file()`
  delegates to shared `harden_user_dir`; removed duplicated `_is_windows` /
  `_resolve_windows_current_user` / inline `subprocess`+`sys`/`sys` imports;
  `_warn_if_unhardened()` uses `is_windows()`.
* `backend/main.py` — imports and calls `configure_logging()` before the app.
* `backend/tests/test_logging_config.py` — NEW; 8 tests.
* `backend/tests/test_credentials_file_hardening.py` — retargeted mock surface
  to the shared helper (no behavioral assertion changed).
* Docs: `040-durable-structured-logging.md` (this report),
  `PUNCH-BOARD.md` (item 32 → CLOSED), `MISSION-INDEX.md` (row 040),
  `ENGINEERING-PROGRESS.md` (Mission 040 Result).

## 7. Boundaries respected

* No `src-tauri/` / Rust changes; the `tauri_plugin_log` / stdout-stderr
  discard gap is flagged (below), not fixed.
* **No existing `logger.*` call site was modified** (89/89 untouched; the only
  logging changes are the new `configure_logging()` and the new log-directory
  helpers).
* No credentials / API keys / request bodies logged (audit above).
* `file_backend.py` behavior unchanged (delegation only); all 477 baseline
  tests pass unmodified except the retargeted mock surface.
* Stdlib only — no new dependencies; `pyproject.toml` / `uv.lock` untouched.
* Console handler preserved; packaged-build stdout/stderr handling unaffected.

## 8. Commit

`feat(modelmix): durable structured logging (Mission 040)` — pushed, verified
local == origin == live remote.

## 9. Notes / follow-ups (NOT done in this mission)

* **Frozen-build terminal silence (flagged):** `src-tauri/src/lib.rs` sets
  `.stdout(Stdio::null())` and `.stderr(Stdio::null())`, so a packaged build's
  logs exist on disk after this mission but are not echoed to any terminal.
  `tauri_plugin_log` is `cfg!(debug_assertions)`-gated there. Tailing the file
  to the Tauri UI or forwarding to `tauri_plugin_log` in release is a deliberate
  follow-up outside M040's boundary.
* **Provider error-body forwarding:** the `e.response.text` error logs in
  `search.py` echo the provider's HTTP error body, which in principle could
  reflect a key back. Pre-existing, out of M040's modify-boundary; flagged for
  a future hardening pass rather than silently changed.
* Third-party loggers (`httpx`, MCP, uvicorn) now flow into the file at the
  configured level. This is intended for observability; HTTP request URLs are
  logged (e.g. OAuth/token endpoints) but never request bodies or headers.