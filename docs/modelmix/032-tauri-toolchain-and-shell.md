# Mission 032 — Tauri Toolchain Check and Minimal Shell Scaffold

Route: Big Pickle (OpenCode Zen)
Punch Board item: 34 (begin — toolchain + minimal shell only)
Date: 2026-08-31 CT
Base: `main @ 08f1bc3327b4b55bd3222144fdfb395c1e44174d`

## Outcome

This mission took outcome **(b)**: the required Windows/Rust toolchain was
present, the missing project CLI was installed, and a standard Tauri 2
`src-tauri/` shell was added. `cargo tauri dev` launched a real native window
that displayed the existing ModelMix cockpit while the existing Python backend
ran separately on port 8001.

This is only a development shell. It does not package, launch, or configure a
Python sidecar, and no production installer was built.

## Toolchain observations before scaffolding

Checks were performed in the required order:

1. `rustc --version` → `rustc 1.98.0 (88d9e12ae 2026-08-18)`; `cargo
   --version` → `cargo 1.98.0 (797e8a9bc 2026-08-05)`. The active toolchain was
   `stable-x86_64-pc-windows-msvc` and the rustc host was
   `x86_64-pc-windows-msvc`.
2. The first `cargo tauri --version` returned Cargo error 101, `no such command:
   tauri`. With Rust already present and approval confirmed, `cargo install
   tauri-cli --version "^2.0.0" --locked` installed
   `C:\Users\wpedi\.cargo\bin\cargo-tauri.exe`; the follow-up version check
   reported `tauri-cli 2.11.4`. Cargo emitted a non-fatal warning that locked
   dependency `spin v0.9.8` is yanked.
3. `vswhere.exe` found complete, launchable Visual Studio Community 2026
   18.9.2 with `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`. The
   installed WebView2 Runtime was found at
   `C:\Program Files (x86)\Microsoft\EdgeWebView\Application\151.0.4129.107`
   and its registry version was `151.0.4129.107`.

## Shell configuration

The generated Tauri 2 scaffold lives only in `src-tauri/`. Its build
configuration reuses the existing frontend:

- `devUrl`: `http://localhost:5173/modelmix`;
- `frontendDist`: `../frontend/dist`;
- `beforeDevCommand`: `npm run dev`;
- `beforeBuildCommand`: `npm run build`.

The `/modelmix` route is intentional: it opens the existing cockpit instead of
the repository's legacy root page. Tauri runs the frontend hooks with the
frontend directory as their working directory, so the initially generated
`npm --prefix frontend run dev` hook failed by looking for
`frontend/frontend/package.json`. Replacing both hooks with their standard
directory-local forms fixed that observed launch failure.

There is no sidecar, external binary, backend command, port-8001 launch hook,
or new frontend pipeline in the Tauri configuration. No backend file,
`frontend/src` file, credential code, CORS configuration, or existing package
manifest was changed.

## Native window observation

The backend was started separately with `uv run python -m backend.main`; its
health endpoint returned HTTP 200 with `status: "ok"`. The corrected `cargo
tauri dev` started Vite at `http://localhost:5173`, compiled the shell, and ran
`target\debug\app.exe`.

Windows inspection found exactly one native `ModelMix` window owned by that
executable. The visible window had a native title bar and rendered the real
three-panel cockpit: Worker A, the wider Moderator, and Worker B, plus the
prompt, Mix/Compare/Solo mode control, three model selectors, separate Send and
Stop buttons, and the Ready state. With no providers configured for that run,
the UI honestly displayed `No models were discovered from configured
providers.` rather than a shell or connection error. The backend log also
observed successful `GET /api/settings` requests from the window.

Both temporary development processes were then stopped. The Tauri process
reported the expected Ctrl+C termination status after the native window had
already been observed; the backend completed an orderly application shutdown.

## Validation actually run

- `cargo check --manifest-path src-tauri/Cargo.toml` → completed successfully.
- `cargo fmt --manifest-path src-tauri/Cargo.toml -- --check` → completed
  successfully after formatting the generator's two-space Rust output.
- `cargo tauri dev` → Vite ready, Rust build finished, and
  `target\debug\app.exe` launched; the native cockpit was visually inspected as
  described above.
- `cd frontend && npm test && npm run build && npm run lint` → **15 files / 138
  tests passed**; Vite transformed **439 modules** and completed the production
  frontend build; ESLint exited successfully with no findings.
- Exact `uv run pytest backend/tests -q` → **246 passed, 214 setup errors**,
  all rooted in the known inaccessible Windows pytest temp directory:
  `PermissionError: [WinError 5]` for
  `C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo`.
- The unchanged backend suite rerun with shell-local `TEMP` / `TMP` and
  `--basetemp` under `.tmp/mission032` → **460 passed in 38.91s**.

## Scope and remaining work

Punch Board item 34 is now **IN PROGRESS**, not closed. Remaining separate
missions include packaging/launching the Python backend as a sidecar, producing
and testing a real installer with `cargo tauri build`, and performing the
Tauri-specific credential-storage re-verification deferred by Missions 026 and
027. None of those were attempted here.
