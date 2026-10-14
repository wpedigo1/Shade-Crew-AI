# Mission 035 — Tauri Sidecar Wiring

**Status:** PASS (local, pushed to `main`) · **Date:** 2026-09-01 CT
**Objective:** Wire the frozen ModelMix backend into the Tauri 2 app as an app-**spawned** process, gate the window on real readiness, and guarantee zero orphaned `modelmix-backend.exe` processes on app exit — proven in BOTH `cargo tauri dev` and a real `cargo tauri build` production run with zero manual Python launches.
**Advancing:** Punch Board item 34 (of which item 34 now closes at this mission).

---

## 0. Step 0 — onedir-vs-sidecar decision (evidence)

The PyInstaller frozen bundle is a PyInstaller **onedir** (executable + required
`_internal/` directory); it is not a single self-contained binary.

| Option | Official behavior | Fitness |
|---|---|---|
| `bundle.externalBin` / sidecar (`tauri-plugin-shell` `sidecar()`) | v2.tauri.app/develop/sidecar/: a single binary per target, named `<name>-<target-triple>.exe`, invoked by filename | **No documented way to ship the `_internal/` directory** needed by the frozen onedir bundle. Rejected. |
| `bundle.resources` | v2.tauri.app/develop/resources/: recursively copies a whole directory into the packaged resource layout preserving structure | Fits — ship the entire `dist/modelmix-backend/` folder. **Chosen.** |

Spawn is done from Rust with `std::process::Command` on the **resolved resource
path**. Rust-side process spawn does not go through the Tauri permission system,
so **no shell-plugin capability entry is required** (the capability `shell:
allow-execute` etc. only gates the JS-facing shell plugin). `capabilities/default.json`
is untouched.

### `_up_` contract discovered during validation

At runtime `BaseDirectory::Resource` does **not** resolve `../`-relative resources
where the tauri bundler copies them *unless the supplied path string mirrors the
bundler algorithm*. Tauri's `resolve_path` (tauri `src/path/mod.rs`,
`BaseDirectory::Resource`) normalizes the **given string** the same way the bundler
does: a `..` component becomes `_up_` under the resource base. Concretely:

- Config: `"resources": ["../dist/modelmix-backend/"]`
- Bundler writes to: `<install>/_up_/dist/modelmix-backend/` (verified in the NSIS output).
- Correct resolve string: `Resource.resolve("../dist/modelmix-backend/modelmix-backend.exe")`
- An earlier flat resolve string (`modelmix-backend/modelmix-backend.exe`) silently fell back to the dev bundle path in production — caught and fixed because the startup log names each candidate that was probed.

The frozen bundle's `console=True` spec requires `CREATE_NO_WINDOW` (`0x0800_0000`,
`std::os::windows::process::CommandExt::creation_flags`) so no console briefly
appears — no backend files are touched.

---

## 1. What changed

| File | Change |
|---|---|
| `src-tauri/src/lib.rs` | Sidecar wiring: exe resolution (env override → packaged resource → dev bundle fallback), spawn with `CREATE_NO_WINDOW` + env (`LLM_COUNCIL_BIND_PORT=8001`, `FRONTEND_HOST=https://tauri.localhost,http://tauri.localhost`), background readiness poll (raw `TcpStream` GET `/api/health`, 250 ms, 30 s cap, no new HTTP dep), hidden until ready, native error dialog on failure, shutdown on `RunEvent::Exit` (kill + `taskkill /T /F` tree fallback), and a Win32 Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` for zero-orphan guarantees even on hard kills. Startup log to `%TEMP%\modelmix-sidecar-startup.log` naming each candidate/probe. |
| `src-tauri/tauri.conf.json` | `bundle.resources: ["../dist/modelmix-backend/"]`; main window starts `"visible": false` (readiness gate); window 1200×800 (three-column cockpit at production scale). `csp` remains `null` — explicitly deferred hardening (see Risks). |
| `src-tauri/Cargo.toml` | `windows-sys 0.61` direct dep with `Win32_Foundation/Security/System_JobObjects/System_Threading/UI_WindowsAndMessaging` features (version was already in the tree transitively — **no new crate**, lockfile records one new `app → windows-sys` edge). |
| `src-tauri/Cargo.lock` | +1 dependency edge. |

Not touched: `backend/` (any Python), `packaging/modelmix-backend.spec`,
`frontend/src/`, `capabilities/default.json`.

---

## 2. Runtime proof — DEV mode (`cargo tauri dev`)

Canonical invocation learned here: run `cargo tauri dev` from the **repo root**
(tauri-cli finds `src-tauri/tauri.conf.json` downward; frontend hooks run with the
Vite `frontend/` as working directory).

First-clean run, no manual Python anywhere:

```
[1788296370.963] resource-dir candidate absent: ...\target\debug\modelmix-backend\modelmix-backend.exe
[1788296370.964] dev fallback backend -> ...\dist\modelmix-backend\modelmix-backend.exe
[1788296370.964] SPAWNED backend pid=23836 exe=...\dist\modelmix-backend\modelmix-backend.exe
[1788296370.965] kill-on-close job assignment: true
[1788296375.661] BACKEND READY after 4.57s          <- first cold spawn, frozen bundle
[1788296375.662] main window shown                    <- window gated until healthy
```

Process-parent proof (the app spawned it, not the user):
`backend(23836) ← app.exe(2832) ← cargo ← cargo-tauri(25484) ← cargo(9392)`.

Live frontend↔backend proof: WebView2 (`msedgewebview2`, pid 3760) held an
`Established` TCP connection `127.0.0.1:61234 → 127.0.0.1:8001`.

After the `_up_` fix, dev re-validation resolved the injected resource copy
`target\debug\_up_\dist\modelmix-backend\modelmix-backend.exe`, spawned it as a
child of the dev app, `BACKEND READY after 10.17s` (cold), window shown.

Graceful close (`CloseMainWindow`) → log tail `terminating backend pid=23744` →
**0 `modelmix-backend` processes, port 8001 free, no leftover cargo/tauri/vite**
from this run.

---

## 3. Runtime proof — PRODUCTION build (criterion 3)

`cargo tauri build --bundles nsis` (release 2 m 39 s) → silent-installed to a clean
temp dir → ran the **installed** `app.exe`.

Startup log for the production run (no `MODELMIX_BACKEND_EXE` set):

```
[1788297466.046] resource-dir backend -> \\?\...\installed2\_up_\dist\modelmix-backend\modelmix-backend.exe
[1788297466.162] SPAWNED backend pid=29116 exe=\\?\...\installed2\_up_\dist\modelmix-backend\modelmix-backend.exe
[1788297466.162] kill-on-close job assignment: true
[1788297468.190] BACKEND READY after 2.03s
[1788297468.191] main window shown
```

- Packaged app spawned the **bundled** backend (parent = `installed2\app.exe`, pid 24404).
- Window: `MainWindowTitle='ModelMix'`, `Responding=True`.
- **Origin/CORS proof** (the known production gotcha, resolved via documented
  `FRONTEND_HOST` config env at spawn — no backend change):
  `GET /api/models` with `Origin: https://tauri.localhost` →
  `200`, `Access-Control-Allow-Origin: https://tauri.localhost`, `Vary: Origin`.
- `GET /api/health` → `{"status":"ok","service":"The AI Counsel API","mcp":{...}}`.

**Graceful close** → 0 orphans, port free.
**Hard-kill clone test** (`taskkill /F` the app after ready, simulating a crash):
backend 15684 was actively listening; after force-kill both were gone —
**0 orphaned `modelmix-backend`**, port freed (Job Object `KILL_ON_JOB_CLOSE`).

---

## 4. Broken-backend error state (criterion 6)

Both failure branches exercised on the production install via `MODELMIX_BACKEND_EXE`:

- **Spawn failure** (nonexistent path): `SPAWN FAILED for C:\nope\fake-backend.exe: The system cannot find the path specified. (os error 3)` → native error dialog ("ModelMix: backend failed to start") appeared; after dismissing it the app exited cleanly. Main window was never shown (gated).
- **Readiness timeout** (a real spawned child that never serves health):
  `SPAWNED backend pid=27104` … `BACKEND NOT READY within 30s — showing fatal error and exiting` at +31.7 s → error dialog → clean exit on dismiss. Log tail `terminating backend pid=27104 / taskkill ... exit=128 / backend terminated`.
  Note: live-child reaping under timeout uses the same teardown already proven live by the hard-kill test above.

`taskkill ... exit=128` = ERROR_WAIT_NO_CHILDREN, observed when the child was
already reaped by `Child::kill`/`wait` first; benign and logged honestly.

---

## 5. Validation actually run (observed)

- `cargo build` (dev profile) — Finished, no warnings.
- `cargo clippy --all-targets` — clean (no warnings/errors).
- Backend: `uv run pytest backend/tests -q --basetemp "C:\Users\wpedi\AppData\Local\Temp\opencode\pt"` → **468 passed in 32.00s** (no backend files changed).
- Frontend: `npm.cmd test` → **15 files / 138 passed** in 10.98 s; `npm.cmd run lint` clean; `npm.cmd run build` ✓ built.
- `cargo tauri build --bundles nsis` → `ModelMix_0.1.0_x64-setup.exe` (43 MiB), makensis emitted the bundle.

## 6. Evidence artifacts

Saved under `C:\Users\wpedi\AppData\Local\Temp\opencode\modelmix-run\` (outside the repo):

- `startup.log.dev` — dev timelines (incl. 4.57 s cold; webview-established run)
- `startup.log.prod-misrun` — first production run (the flat-resolve miss) for the record
- `startup.log.prod-timeout` — timeout-branch production run
- `dev-cockpit.png`, `prod-cockpit.png` — full-window screenshots for human review
- `tauri-build.log`, `tauri-build2.log(.err)` — build transcripts

## 7. Assumptions, scope notes, remaining risks

- **Canonical invocation is repo-root**: `cargo tauri dev`/`cargo tauri build` from the repository root (tauri-cli descends to `src-tauri/tauri.conf.json`; frontend hooks run in `frontend/`). Invoking from `src-tauri/` mis-locates the Vite hook and is not supported.
- **Dist bundle is a build prerequisite**: the frozen `dist/modelmix-backend/` (Mission 033 output) must exist before `cargo tauri build`, because it is a bundled resource. It is gitignored; dev also needs it locally.
- **`--bundles nsis`** was used for this validation. MSI layout is untested (resource resolver semantics are shared, but WiX/MSI was deliberately out of scope).
- **Readiness gate probes the shared port:** under concurrent app instances a late spawner can see its predecessor's health. The product is a single-window app; concurrent-instance behavior is a known, documented limitation, not a supported scenario.
- **`MODELMIX_BACKEND_EXE` is a binary path only** (no extra args): intended for tests/troubleshooting. Persisting children via it isn't possible without args; timeout teardown was still proven live by the hard-kill case.
- **Windows first-run/AV variance** explains cold-start spread (4.57 s / 10.17 s dev, 2.03 s prod on this machine); readiness timeout is 30 s and covered the observed floor.
- **No CSP hardening** (stays `null`), no code-signing/installer polish, no dynamic port discovery — per mission boundaries; CSP is a known later-mission dependency before hardening can be approved.
- **100% reliable child termination** for graceful close relies on the Exit handler (+ `taskkill /T /F` tree fallback); the Job Object (`KILL_ON_JOB_CLOSE`, assignment observed `true`) additionally covers hard kills even if the Exit handler never runs.