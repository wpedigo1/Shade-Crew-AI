# Mission 027 — Auto-Remediate an Unhardened Credentials File on Startup

Base: `main @ 2b32422` (Mission 026).

## Objective

An existing, unhardened, pre-Mission-026 `data/credentials.json` gets
**actually hardened automatically, once**, the next time the backend process
touches it — not just warned about. Remediation, not just detection.

Mission 026 only ran `_harden_credentials_file()` from the **write** path and
`_warn_if_unhardened()` only logged a warning for an existing unhardened file.
So a machine that only ever **reads** credentials (never writes a new key) kept
its pre-existing file unhardened indefinitely.

## What changed

Scoped to `backend/credentials/file_backend.py`, and to `_warn_if_unhardened()`
only. `_harden_credentials_file()`'s own logic is **unchanged and reused
exactly** — this mission only changes **when** it is called.

`_warn_if_unhardened()` now, on the first touch (read or write) of an existing
file on Windows that is not already hardened this session, **attempts**
`_harden_credentials_file()` directly, then logs:

- **INFO** (`"Restricted %s to the current user account."`) if remediation
  succeeds;
- the **existing warning** (unchanged wording, `"The credentials file %s is not
  restricted..."`) if remediation still fails.

The once-per-process `_startup_warned` guard and the `_hardened` flag semantics
are preserved, so this is a single, automatic, one-time remediation. A user who
upgrades and simply opens the app (even a single settings read) gets their
pre-existing file protected.

## Boundaries honored

- `_harden_credentials_file()` logic untouched — reused verbatim.
- Never raises out of the read/write path; a failed remediation logs and
  continues exactly as before.
- `keyring_backend.py`, `store.py`, and all routes in `main.py` untouched.
- Default storage mode and `get_effective_mode()` unchanged.
- Tests mock `subprocess.run` and `sys.platform`; no real `icacls` invoked.

## Acceptance criteria → test mapping

| # | Criterion | Test |
|---|---|---|
| 1 | Existing unhardened file gets `_harden_credentials_file()` on first `get_secret` (icacls-invoking mock called, not just no-error) | `test_read_triggers_remediation_on_existing_unhardened_file` |
| 2 | Successful remediation logs no warning — only a success message | `test_startup_remediation_runs_once_on_existing_unhardened_file` (asserts 0 WARNING, INFO "Restricted") |
| 3 | Failed remediation preserves the existing warning | `test_startup_remediation_failure_warns_once` |
| 4 | Already-hardened-this-session file gets no redundant icacls on subsequent read | `test_already_hardened_this_session_no_icacls_on_read` |
| 5 | Non-Windows: no behavior change | `test_no_startup_warning_on_non_windows` (unchanged) |
| 6 | Mission 026 tests continue to pass — see note below | 10 passed in `test_credentials_file_hardening.py` |
| 7 | Full suite passes, only new/extended tests added | 441 passed |

## Test reconciliation note (criterion 6)

One Mission 026 test — `test_startup_warning_fires_once_on_existing_unhardened_file`
— is **necessarily reconciled** for Mission 027. Its Mission 026 assertions
were "reads never invoke icacls" (`calls == []`) and "exactly one warning".
Mission 027 intentionally replaces detection-only with remediation, so the
first read of an existing unhardened file **now invokes icacls** and, on
success, logs INFO instead of a warning. These two requirements are directly
contradictory, so the test was updated to assert the new, correct once-per-
process remediation semantics:

- `test_startup_remediation_runs_once_on_existing_unhardened_file`: exactly one
  icacls attempt across two reads, INFO "Restricted" logged, zero warnings.
- `test_startup_remediation_failure_warns_once`: exactly one icacls attempt and
  the operator-facing "not restricted" warning fires exactly once.

All other Mission 026 tests pass unmodified. This is flagged explicitly because
criterion 6 ("unmodified") cannot be simultaneously satisfied with acceptance
criterion 1 ("first get_secret invokes icacls").

## Validation (raw results observed)

`uv run pytest backend/tests/test_credentials_file_hardening.py -v` → **10
passed** (7 Mission 026-origin + 3 net new; see note above).

`uv run pytest backend/tests -q --basetemp ...` → **441 passed in 28.55s**
(438 prior + 3 net new).

`uv run ruff check backend/credentials/file_backend.py
backend/tests/test_credentials_file_hardening.py` → All checks passed.

`cd frontend && npm test` → **12 files / 118 tests passed**.
`npm run build` → built in 1.84s. `npm run lint` → clean.

`git status --short` / `git diff --stat` → see below; only intended files.

## Punch Board item 30

With Mission 026 (real ACL hardening on write) and Mission 027 (automatic
remediation of a pre-existing file on first touch, read or write), item 30's
**current-model half is now closeable**: both newly-written and
already-existing credentials files are user-restricted on Windows, with Unix
0o600 unchanged.

The **Tauri-specific re-verification is carried forward exactly as Mission 026
stated it**: a SEPARATE, later re-verification of credential storage will be
needed once Tauri 2 packaging (item 34) actually exists, since Tauri's own
storage/IPC model may behave differently and cannot be assumed to inherit this
mission's guarantees.
