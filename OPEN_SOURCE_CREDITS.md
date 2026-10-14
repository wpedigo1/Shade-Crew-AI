# OPEN_SOURCE_CREDITS

This file names ModelMix's direct dependencies (declared in `pyproject.toml`,
`frontend/package.json`, and `src-tauri/Cargo.toml`) and states each package's
license as reported by real package-metadata inspection, not by name or
reputation. The complete, tool-generated transitive license inventories for all
three ecosystems live in `docs/modelmix/licenses/`:

* `THIRD-PARTY-LICENSES-python.txt` — generated with `pip-licenses` against the
  project virtual environment.
* `THIRD-PARTY-LICENSES-frontend.txt` — generated with `license-checker` against
  `frontend/node_modules`.
* `THIRD-PARTY-LICENSES-rust.txt` — generated with `cargo-license` against
  `src-tauri/Cargo.lock`.

Each inventory file's header states the exact command and generation date. This
document intentionally lists direct dependencies only; the full transitive trees
are in those three files.

## ModelMix's own license

Like the repository `LICENSE` file (and the cockpit About section, which this
repeats verbatim from that file):

> MIT License — Copyright (c) 2025 Jacob Ben David.

## AI Counsel attribution

ModelMix began as a fork/evolution of The AI Counsel, an open-source multi-model
AI project. AI Counsel provided substantial working infrastructure around
providers, conversations, model access, streaming, and other capabilities.

> Credit to the original AI Counsel project and its contributors for the
> foundation ModelMix started from.

License identifiers below are quoted exactly as the machine inspection reported
them; where a tool's metadata string differs from a canonical SPDX spelling, the
reported string is what this file states.

## Python dependencies (from `pyproject.toml`)

Runtime dependencies:

| Package | License (as reported by pip-licenses) |
| --- | --- |
| `fastapi` | MIT |
| `uvicorn` | BSD-3-Clause |
| `python-dotenv` | BSD-3-Clause |
| `httpx` | BSD License |
| `pydantic` | MIT |
| `pdfplumber` | MIT License |
| `python-multipart` | Apache-2.0 |
| `ddgs` | MIT |
| `mcp` (with `cli` extra) | MIT License |
| `keyring` | MIT |

Development dependencies:

| Package | License (as reported by pip-licenses) |
| --- | --- |
| `pyinstaller` | GNU General Public License v2 (GPLv2) |
| `pytest` | MIT |
| `pytest-asyncio` | Apache-2.0 |
| `respx` | BSD License |
| `ruff` | MIT |

Note: `pip-licenses` (the inspection tool) and its helper packages do not
appear in the Python inventory — it omits itself from its own report — and they
are not project dependencies.

## Frontend dependencies (from `frontend/package.json`)

Runtime dependencies — every one reported as **MIT** by `license-checker`:
`react`, `react-dom`, `react-markdown`, `react-select`, `remark-gfm`.

Development dependencies — every one reported as **MIT** by `license-checker`:
`vite`, `vitest`, `eslint`, `@eslint/js`, `@types/react`, `@types/react-dom`,
`@vitejs/plugin-react`, `eslint-plugin-react-hooks`,
`eslint-plugin-react-refresh`, `globals`, `jsdom`.

## Rust dependencies (from `src-tauri/Cargo.toml`)

Direct dependencies plus the build-time dependency `tauri-build`. Per
`cargo-license`, every one of the following is in the **`Apache-2.0 OR MIT`**
group of `THIRD-PARTY-LICENSES-rust.txt`: `serde`, `serde_json`, `log`,
`tauri`, `tauri-plugin-log`, `windows-sys`, `tauri-build`. (The `app` crate in the
MIT group of that inventory is this repository's own Tauri crate.)