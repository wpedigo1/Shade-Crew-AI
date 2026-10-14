# Mission 037 — Open Source Credits and Dependency License Inventory

Base: `main` @ `280643b` "docs(modelmix): close punch board items 30 and 31
against completed evidence (Mission 036)".

Result: **PASS (LOCAL, pushed)**. Punch Board item 4 closed (SATISFIED with
Mission 017). No backend application logic, Rust process logic, or existing
test file was touched; `LICENSE` and the MIT text are unchanged. No license
checking tool was added to any manifest (`pyproject.toml`, `package.json`,
`Cargo.toml` are all unmodified) — `pip-licenses`, `npx license-checker`, and
`cargo-license` were one-off/dev-only, with `pip-licenses` installed only into
the gitignored `.venv` and `cargo-license` into the user's `~/.cargo/bin`.

## 1. Machine-generated inventories

All three committed as-is under `docs/modelmix/licenses/`, each with a header
stating the exact generation command and date (2026-09-01).

| File | Tool / exact command | Run against | Lines |
| --- | --- | --- | --- |
| `THIRD-PARTY-LICENSES-python.txt` | `uv run pip-licenses --order=name --with-authors` (pip-licenses 5.5.5, `PYTHONIOENCODING=utf-8` for a cp1252 console) | project `.venv` (all installed packages) | 95 (approx. 91 packages + header) |
| `THIRD-PARTY-LICENSES-frontend.txt` | `npx.cmd --yes license-checker --start .` (npm package license-checker, invoked from `frontend/`) | `frontend/node_modules` (runtime + devDependencies tree) | 2491 |
| `THIRD-PARTY-LICENSES-rust.txt` | `cargo license --color never` (cargo-license 0.7.0, installed via `cargo install cargo-license --locked`; run from `src-tauri/`) | `src-tauri/Cargo.lock` | 20 |

Notes: the Python inventory inspects the declared metadata of every installed
distribution, so the one-off tools themselves (`pip-licenses`, `prettytable`,
`wcwidth`) also appear in it; they are not project dependencies (stated in
`OPEN_SOURCE_CREDITS.md`). The Rust output groups packages by license
expression and lists every crate in the lockfile; no crate was reported as
UNKNOWN. The frontend inventory is a per-package tree from `node_modules`.

## 2. OPEN_SOURCE_CREDITS.md spot-checks (acceptance criterion 2)

Direct dependencies were cross-checked package-by-package against the three
machine files. Every license string below is quoted from the inventory, with
the file line where the reviewer can re-verify.

**Python runtime** (`THIRD-PARTY-LICENSES-python.txt`):

| Direct dep | Version | License in machine file | Line |
| --- | --- | --- | --- |
| `fastapi` | 0.141.1 | `MIT` | 25 |
| `uvicorn` | 0.38.0 | `BSD-3-Clause` | 90 |
| `python-dotenv` | 1.2.3 | `BSD-3-Clause` | 69 |
| `httpx` | 0.28.1 | `BSD License` | 32 |
| `pydantic` | 2.12.4 | `MIT` | 62 |
| `pdfplumber` | 0.11.10 | `MIT License` | 56 |
| `python-multipart` | 0.0.32 | `Apache-2.0` | 70 |
| `ddgs` | 9.9.1 | `MIT` | 22 |
| `yake` | 0.6.0 | `GNU General Public License v3 (GPLv3)` | 93 |
| `mcp` (with `cli` extra: `mcp`/`mcp-types`/`typer`/`rich`) | 2.1.1 | `MIT License` | 47 |
| `keyring` | 25.7.0 | `MIT` | 44 |

**Python dev**: `pyinstaller` 6.22.2 `GNU General Public License v2 (GPLv2)`
(line 64), `pytest` 9.0.3 `MIT` (67), `pytest-asyncio` 1.3.0 `Apache-2.0`
(68), `respx` 0.23.1 `BSD License` (75), `ruff` 0.15.16 `MIT` (78).

**Frontend** (`THIRD-PARTY-LICENSES-frontend.txt`): every direct dependency —
runtime `react`/`react-dom`/`react-markdown`/`react-select`/`remark-gfm` and
dev `vite`/`vitest`/`eslint`/`@eslint/js`/`@types/react`/`@types/react-dom`/
`@vitejs/plugin-react`/`eslint-plugin-react-hooks`/
`eslint-plugin-react-refresh`/`globals`/`jsdom` — is reported as `MIT`
(e.g. `react@19.2.0 — licenses: MIT`, `vite@7.3.6 — licenses: MIT`,
`jsdom@26.1.0 — licenses: MIT`).

**Rust** (`THIRD-PARTY-LICENSES-rust.txt`, line 13, the `Apache-2.0 OR MIT`
group): `serde`, `serde_json`, `log`, `tauri`, `tauri-plugin-log`,
`windows-sys`, and the build dependency `tauri-build` are all listed under
`Apache-2.0 OR MIT`; the `app` crate (this repo's Tauri crate) appears in the
`MIT` group.

No direct dependency was left UNKNOWN; where the tool's string is not a
canonical SPDX spelling (e.g. httpx "BSD License"), the machine-reported string
is used verbatim in `OPEN_SOURCE_CREDITS.md`.

## 3. AI Counsel attribution and ModelMix MIT (reused, not re-derived)

Credits file restates the MIT copyright exactly as the `LICENSE` file and
Mission 017's About section state it, and reuses the `README.md` wording for
the AI Counsel foundation paragraph plus the "Credit to the original AI Counsel
project and its contributors..." sentence — text only, no fabricated URL.

## 4. About-section pointer (one line)

`frontend/src/components/ModelMixObserver.jsx` `AboutSection` gained one line
reusing the existing `modelmix-settings-line`/anchor layout:

```jsx
<p className="modelmix-settings-line"><a href="https://github.com/wpedigo1/ModelMix/blob/main/OPEN_SOURCE_CREDITS.md">OPEN_SOURCE_CREDITS.md — open-source credits and dependency licenses</a></p>
```

The URL is the same real `github.com/wpedigo1/ModelMix` already used in that
About block. No Settings-shell restructuring.

## 5. Validation (raw output)

### Frontend

```
> the-ai-counsel@0.11.4 test
> vitest run

 Test Files  15 passed (15)
      Tests  138 passed (138)
   Duration  9.88s (transform 2.15s, setup 0ms, import 27.44s, tests 4.00s, environment 24.40s)
test exit: 0
```

`ModelMixSettings.test.jsx` (12 tests) — which covers the About section, incl.
`About section renders the version from package.json with license and
attribution` — passed among the 138.

```
=== npm run build ===
assets/index-Dj3kk8OM.js   236.19 kB │ gzip: 72.22 kB
✓ built in 2.46s
build exit: 0

=== npm run lint ===
> eslint .
lint exit: 0
```

### Backend

The exact command from the mission, `uv run pytest backend/tests -q`, fails on
this machine at the pytest `tmp_path` fixture before any test asserts:

```
ERROR backend/tests/test_storage_modes.py::test_rebuild_index_skips_non_conversation_json
ERROR backend/tests/test_user_data_dir.py::test_frozen_uses_localappdata_modelmix
ERROR backend/tests/test_version_consistency.py::test_checker_reports_a_stale_release_surface
252 passed, 216 errors in 13.56s
pytest exit: 1

_ ERROR at setup of test_newly_guarded_endpoint_rejects_non_loopback_without_token[put-/api/settings-body0] _
E PermissionError: [WinError 5] Access is denied: 'C:\\Users\\wpedi\\AppData\\Local\\Temp\\pytest-of-wpedigo'
        .venv\lib\site-packages\pytest_asyncio\plugin.py:730: PermissionError
```

That is this machine's pre-existing environment issue with pytest's default
temp root (no backend files changed in this mission), documented by the repo's
established `--basetemp` override. With it:

```
uv run pytest backend/tests -q --basetemp "C:\Users\wpedi\AppData\Local\Temp\opencode\pt"
468 passed in 31.37s
pytest exit: 0
```

## 6. Files changed

- Added: `OPEN_SOURCE_CREDITS.md`, `docs/modelmix/licenses/THIRD-PARTY-LICENSES-python.txt`, `docs/modelmix/licenses/THIRD-PARTY-LICENSES-frontend.txt`, `docs/modelmix/licenses/THIRD-PARTY-LICENSES-rust.txt`, `docs/modelmix/037-open-source-credits-and-license-inventory.md`.
- Modified: `frontend/src/components/ModelMixObserver.jsx` (one About line), `docs/modelmix/PUNCH-BOARD.md` (item 4 -> SATISFIED), `docs/modelmix/MISSION-INDEX.md` (row 037), `docs/modelmix/ENGINEERING-PROGRESS.md` (Mission 037 Result).
- Unchanged: `pyproject.toml`, `frontend/package.json`, `src-tauri/Cargo.toml`, `src-tauri/Cargo.lock`, `LICENSE`, all tests.

Diff stat before commit:

```text
 docs/modelmix/ENGINEERING-PROGRESS.md        | 22 ++++++++++++++++++++++
 docs/modelmix/MISSION-INDEX.md               |  1 +
 docs/modelmix/PUNCH-BOARD.md                 |  4 ++--
 frontend/src/components/ModelMixObserver.jsx |  1 +
 OPEN_SOURCE_CREDITS.md                       | 88 ++++++++++++++++++++++++++++++++++++++++++++++++
 docs/modelmix/037-open-source-credits-and-license-inventory.md | ~100 ++++++++++++++++++++
 docs/modelmix/licenses/THIRD-PARTY-LICENSES-python.txt         | ~95 ++++++++++++
 docs/modelmix/licenses/THIRD-PARTY-LICENSES-frontend.txt       | ~2491 ++++...
 docs/modelmix/licenses/THIRD-PARTY-LICENSES-rust.txt           | ~20 ++++
 4 tracked files changed, 26 insertions(+), 2 deletions(-), plus 5 new untracked files
```