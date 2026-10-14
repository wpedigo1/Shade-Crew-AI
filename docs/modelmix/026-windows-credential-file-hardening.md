# Mission 026 — Real Windows File-Permission Hardening for Credential Storage

Base: `main @ a4af374` (Mission 025).

## Objective

On Windows, `data/credentials.json` gets **real** access-control hardening
restricted to the current user account, not just the ineffective
`os.chmod(0o600)` no-op that Windows silently ignores. On Unix, existing
behavior is unchanged. No default storage mode change, no migration.

## The confirmed gap (before this mission)

- `backend/settings.py` defaults `credential_storage = "file"`.
- `file_backend._write_all` wrote plaintext JSON then attempted
  `os.chmod(CREDENTIALS_FILE, 0o600)` in a `try/except OSError: pass`.
- On Windows, `chmod` with a POSIX octal mode has **no** meaningful
  per-user-account ACL effect — the hardening was effectively a silent no-op
  on Windows.

## What changed (scoped to `backend/credentials/file_backend.py` only)

1. **Real Windows ACL hardening.** After the atomic replace and the unchanged
   `os.chmod(0o600)` (kept exactly as-is for Unix), `_write_all` now calls
   `_harden_credentials_file()`, which on `sys.platform == "win32"` runs:

       icacls "<path>" /inheritance:r /grant:r "<current-user>":F

   `/inheritance:r` removes inherited folder permissions; `/grant:r` replaces
   explicit grants with exactly one: full control for the current user.
   Implemented with `subprocess` — no `pywin32` dependency.

2. **Current-user resolution.** `_resolve_windows_current_user()` prefers the
   `USERNAME` / `USERDOMAIN` environment variables (`DOMAIN\user` when both are
   present), falling back to `os.getlogin()`. Choice rationale: `USERNAME` is
   set reliably for a logged-in interactive session and for a user-run service,
   while `os.getlogin()` can raise `OSError` when there is no controlling
   terminal (some service / SSH contexts). Not hardcoded.

3. **Fail-safe, never crashes the write path.** `icacls` unavailability,
   exceptions, or a non-zero exit are caught and logged as a warning; the
   credential write still succeeds. This mirrors the existing
   `except OSError: pass` philosophy but logs the failure instead of silently
   swallowing it, since it is worth an operator seeing.

4. **Once-per-process startup warning** (`_warn_if_unhardened`), called from
   both `_read_all` and `_write_all`, guarded by a module-level `_startup_warned`
   flag so it fires at most once per process. It warns when running on Windows
   AND the credentials file exists AND the file has not been successfully
   hardened this session. Because a pre-existing file created before this
   mission has unknown history (we do not persist a "hardened" marker), such
   files are treated as unhardened and surface the warning once — this catches
   exactly the risk the requirement targets.

## Boundaries honored

- `credential_storage` default value **unchanged**; `get_effective_mode()`
  selection logic **unchanged**. Default `file` mode remaining unchanged is
  this mission's declared boundary (a product decision), not an oversight.
- No `pywin32` or any new dependency; `subprocess` + `icacls` only.
- `keyring_backend.py`, `store.py` facade logic, and all routes in `main.py`
  untouched.
- No migration / re-encryption; credential **values** are never modified —
  only the file's OS-level access control changes.
- Unix `os.chmod(0o600)` left exactly as-is; no real Unix permission changes.
- `availability.py::is_container_environment()` path: off-Windows (Linux CI /
  containers) this hardening is a no-op returning False without invoking
  icacls — not an error, consistent with the existing chmod tolerance.

## Acceptance-test mapping

| # | Criterion | Test |
|---|---|---|
| 1 | Windows write invokes `icacls` with correct path + current-user arg | `test_windows_write_invokes_icacls_args` |
| 2 | Non-Windows never invokes `icacls` (assert-not-called) | `test_non_windows_never_invokes_icacls`, `test_no_startup_warning_on_non_windows` |
| 3 | Failing `icacls` does not raise; write still succeeds, value readable | `test_failing_icacls_does_not_raise_and_value_survives` (returncode!=0 and OSError cases) |
| 4 | Failing case logs a warning | `test_failing_icacls_logs_warning` |
| 5 | Startup warning fires once on Windows + existing unhardened file, not a second time in-process | `test_startup_warning_fires_once_on_existing_unhardened_file` |
| 6 | Startup warning does not fire on non-Windows regardless of file state | `test_no_startup_warning_on_non_windows` |
| 7 | Existing credential/admin-guard tests pass unmodified | see Validation |
| 8 | Full existing suite passes, only new tests added | 438 passed |

Tests mock `subprocess.run` and `sys.platform`; no real `icacls` is ever
invoked. `subprocess` is imported directly and monkeypatched by each test.

## Validation (raw results observed)

`uv run pytest backend/tests/test_credentials_store.py backend/tests/test_credentials_keyring.py
backend/tests/test_credentials_availability.py backend/tests/test_admin_guard_credential_endpoints.py -v`
→ **41 passed** (all unmodified).

`uv run pytest backend/tests -q --basetemp ...` → **438 passed in 27.76s**
(431 prior + 7 new; no existing test modified).

`uv run ruff check backend` → **All checks passed!**

`cd frontend && npm test` → **12 files / 118 tests passed**.
`npm run build` → built in 1.57s. `npm run lint` → clean.

`git status --short` / `git diff --stat` → see below; only intended files.

## Assumptions / notes

- "Unhardened startup warning" relies on an in-process flag, not a persisted
  marker. A file that was previously hardened by an earlier process but never
  touched this session will still produce one startup warning (we cannot know
  its history). This is a deliberate, documented conservative choice honoring
  the requirement's "created before this mission" case.
- The credential store tests run on the real `win32` platform here; the
  non-Windows acceptance tests mock `sys.platform = "linux"` and assert
  `subprocess.run` is never called, which is the meaningful proof.

## Remaining risks / follow-ups

- **Punch Board item 30 (advance):** this mission's hardening covers the
  current-model half (the `file` backend on the local Python server). A
  **separate, later re-verification of credential storage is required once
  Tauri 2 packaging (Punch Board item 34) actually exists**, because Tauri's
  own storage/IPC model may behave differently and cannot be assumed to inherit
  this mission's guarantees. This must be re-checked, not assumed.
- The startup warning for pre-existing files is heuristic (no persisted
  hardened-marker); a future enhancement could persist a marker or inspect the
  file's current ACL to distinguish genuinely hardened pre-existing files.
