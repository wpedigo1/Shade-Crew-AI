# Mission 034 — Frozen-Aware User Data Directory

Route: Big Pickle (OpenCode Zen)
Punch Board item: 34 (advance — credential/data-path correctness)
Date: 2026-08-31 CT
Base: `main @ 9fc4da7` (Mission 033)
Result: **PASS (LOCAL)**

## Why this mission exists

Mission 033 proved the frozen backend works and in doing so confirmed a real
finding: `CREDENTIALS_FILE` resolved via `Path(__file__)` module-relative
arithmetic, which in a frozen build resolves INSIDE the app bundle
(`_internal\data\credentials.json`, confirmed directly in Mission 033's
evidence). The identical pattern existed for `SETTINGS_FILE`
(`backend/settings.py`) and persona data (`backend/personas.py`). A real
distributable would therefore have stored user credentials, settings, and
persona overrides inside its own install/bundle folder instead of an
OS-conventional per-user location.

This mission fixes the underlying mechanism once, applies it to all three
files, and changes dev-mode behavior byte-for-byte not at all.

## Change

New module `backend/user_data_dir.py`:

- `is_frozen() -> bool` uses PyInstaller's standard `getattr(sys, "frozen", False)`.
- `resolve_user_data_dir() -> Path`:
  - Not frozen: the existing repo-relative `data/` directory, computed from the
    new module's own location with the same two-`.parent` arithmetic
    `settings.py`/`personas.py` already used, landing on `<repo>/data` — the
    exact directory the three files already targeted.
  - Frozen (Windows): `Path(os.environ["LOCALAPPDATA"]) / "ModelMix"`. If
    `LOCALAPPDATA` is absent, falls back to the directory containing the
    running executable (`sys.executable`'s parent) and logs a clear warning.
  - The resolved directory is created via `mkdir(parents=True, exist_ok=True)`
    before returning.

The three module-level data paths now derive from the shared helper:

- `backend/credentials/file_backend.py`:
  `CREDENTIALS_FILE = resolve_user_data_dir() / "credentials.json"`
- `backend/settings.py`:
  `SETTINGS_FILE = resolve_user_data_dir() / "settings.json"`
- `backend/personas.py`:
  `_DATA_DIR = resolve_user_data_dir()`, `_OVERRIDES_FILE` unchanged subpath.

`backend/user_data_dir.py` imports only stdlib (`os`, `sys`, `logging`,
`pathlib`). No dependency changes. Nothing in `main.py`, `keyring_backend.py`,
the store facade, the Mission 026/027 `icacls` hardening logic, `src-tauri/`,
or `frontend/` was touched. The `icacls` hardening simply keeps operating on
`CREDENTIALS_FILE`, which now points at the frozen-only user-data location.

## Tests

New `backend/tests/test_user_data_dir.py` (7 tests), one per acceptance
criterion 1–4 plus coverage:

1. not frozen → `resolve_user_data_dir()` equals the exact path the three files
   resolved to before (recomputed from the historical `.parent` formulas);
2. `LOCALAPPDATA` env is ignored when not frozen (dev-mode cannot drift);
3. frozen + `LOCALAPPDATA` → `<LOCALAPPDATA>/ModelMix`, created on return;
4. frozen, missing `LOCALAPPDATA` → executable dir + a clear WARNING log;
5. `CREDENTIALS_FILE` derives from the helper with the `credentials.json`
   filename;
6. `SETTINGS_FILE` derives from the helper with the `settings.json` filename;
7. `personas._DATA_DIR` equals the helper result and `_OVERRIDES_FILE` keeps
   its `persona_overrides.json` subpath.

Dev-mode regression is proven two ways: criterion 1/5–7 test the exact
historical path equality, and the full suite's existing credential, settings,
and persona tests pass completely unmodified.

## Validation actually run (observed)

- `uv run pytest backend/tests/test_credentials_store.py backend/tests/test_credentials_keyring.py backend/tests/test_credentials_availability.py backend/tests/test_credentials_file_hardening.py -v`:
  the exact command reproduced the known Windows default-temp failure
  (**2 passed, 22 errors**, every error a `PermissionError [WinError 5]` on
  `pytest-of-wpedigo`). Rerun with the documented
  `--basetemp ...\Temp\opencode\pt` workaround: **24 passed** (all credential
  tests, verbose, PASSED observed for every item).
- `uv run pytest backend/tests -q`: the exact command reproduced the same
  known environment failure (**252 passed, 216 errors**). Rerun with the
  `--basetemp` workaround: **468 passed in 30.51s** (461 pre-existing tests
  all still pass unmodified + 7 new).
- `uv run ruff check backend`: **All checks passed!**
- Dev-mode live inspection:
  `frozen: False`, `data_dir: C:\Users\wpedi\ModelMix\data`, and all three
  constants resolve under it (`credentials.json`, `settings.json`,
  `persona_overrides.json`).
- `cd frontend && npm test && npm run build && npm run lint`: Vitest **15
  files / 138 passed**, Vite build completed successfully, ESLint clean. No
  frontend files changed, as required.

## Closing

This closes the specific finding from Mission 033's evidence
(`_internal\data\credentials.json`). The mechanism that caused it — module-
relative `Path(__file__)` arithmetic — is replaced once and applied to all
three user-data files.

Honest caveat: the frozen-mode path is verified by simulation
(monkeypatched `sys.frozen = True` / `LOCALAPPDATA` / `sys.executable`), not
by running the real PyInstaller build. Whether a real frozen run lands in
`%LOCALAPPDATA%\ModelMix` needs the same hands-on proof Mission 033 required —
a frozen-build run observing the actual resolved path and written file
locations. That verification is not possible from an ordinary dev run and
remains outstanding for the Tauri sidecar/installer mission (item 34).

Dev-mode behavior is unchanged: the full pre-existing suite passes
unmodified, `data/` remains the repo-relative location, and blockpaths beyond
the three named files (`config.DATA_DIR` CWD-relative conversations, the
`MODELMIX_DATA_DIR`-overridable ModelMix persistence) were intentionally out
of scope for this mission.

## Files changed

- `backend/user_data_dir.py` (new)
- `backend/credentials/file_backend.py`
- `backend/settings.py`
- `backend/personas.py`
- `backend/tests/test_user_data_dir.py` (new)
- `docs/modelmix/034-frozen-aware-user-data-directory.md` (new)
- `docs/modelmix/PUNCH-BOARD.md`
- `docs/modelmix/MISSION-INDEX.md`
- `docs/modelmix/ENGINEERING-PROGRESS.md`