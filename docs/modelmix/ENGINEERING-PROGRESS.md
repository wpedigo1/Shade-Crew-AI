# ModelMix Engineering Progress

Updated: 2026-09-01 CT


This is the current implementation-state overlay for the locked ModelMix Punch Board. It records observed implementation progress without silently reordering or deleting locked board items.

Authoritative build order and roadmap: [`PUNCH-BOARD.md`](PUNCH-BOARD.md)  
Mission provenance/index: [`MISSION-INDEX.md`](MISSION-INDEX.md)

## Current Repository Checkpoint

Completed and locally verified implementation missions: **001–035, 037–057**.

Mission **007.5 — PASS** closed the dependency-security compatibility interlock.

Accepted Mission 007.5 implementation commit:

`e018ed06807beda2c11531f065b2d4181c346ca8` — `fix(mcp): migrate inherited MCP integration to MCP 2.x API`

Remote `main` was independently verified to resolve to that commit before this documentation update.

Mission **008** persistence is present on current `main` and passes the current backend suite.

## Mission Ledger

| Mission | Result | Engineering outcome | Evidence location |
|---|---|---|---|
| 001 | PASS | Baseline/architecture spike: inherited verification, streaming/SSE/process/credential ground truth, reuse seams | `001-baseline-architecture-spike.md` |
| 002 | PASS | First real ModelMix streaming slice: optional provider stream contract, ChatGPT OAuth streaming, two independent workers, ordered seat/run SSE | `002-first-streaming-slice.md` |
| 003 | PASS | Bounded process-local event journal, replay/tailing, disconnect-vs-cancel separation, explicit idempotent cancellation | `003-event-journal-reconnect.md` |
| 004 | PASS | First browser observer: independent Worker A/B rendering, reconnect/replay, fixed Send/Stop | `004-first-frontend-observer.md` |
| 005 | PASS | Moderator backend fan-in/synthesis phase, isolation, partial/failure handling, replay/cancellation integration | `005-moderator-backend-phase.md` |
| 006 | PASS | Persistent three-panel cockpit: Worker A / wider Moderator / Worker B, centralized event routing, reconnect and failure UX | `006-three-panel-cockpit-slice.md` |
| 007 | PASS | Searchable configured-model selectors for Worker A/Moderator/Worker B; exact IDs, active-run locking, accessible keyboard behavior | `007-searchable-model-discovery-controls.md` |
| 007.5 | **PASS** | MCP 2.x compatibility migration; security-clean dependency set preserved | `007.5-mcp-2-security-compatibility.md` |
| 008 | **PASS** | Versioned atomic JSON session/run persistence, restart replay reconstruction, and cockpit hydration/deduplication | `008-durable-persistence-cockpit-hydration.md` |
| 009 | **PASS (LOCAL)** | Bounded seat-scoped Worker/Moderator history, failure-partial reuse, hot-swap continuity, and leakage proof | `009-seat-scoped-multi-turn-context.md` |
| 010 | **PASS (LOCAL)** | Seat history character budgets: 4k per message (`MAX_HISTORY_MESSAGE_CHARS`) and 24k per seat (`MAX_HISTORY_TOTAL_CHARS`) with deterministic middle truncation and whole-turn oldest-first eviction | `010-seat-history-budget.md` |
| 010.5 | **PASS (LOCAL)** | Frontend test runner interlock: Vitest + jsdom devDeps, `npm test` non-watch run, existing three test files collected and observed 24/24 pass | `010.5-frontend-test-runner-interlock.md` |
| 011 | **PASS (LOCAL)** | Multi-turn cockpit display: prior runs archived chronologically into per-seat `history`, pure `archiveCurrentRun`, prior turns rendered above the live turn in each panel | `011-multi-turn-cockpit-display.md` |
| 012 | **PASS (LOCAL)** | Session control and prompt plumbing: starting state carries `prompt`/`models`, no placeholder for absent prompts, separate New Session control via `modelSelectorsDisabled` (clears local session key, resets cockpit, preserves models) | `012-session-control-and-prompt-plumbing.md` |
| 013 | **PASS (LOCAL)** | Run and seat timeouts: ModelMix-owned 600s/300s wall-clock bounds (`timeouts.py`), `reason: "timeout"` terminal outcomes reusing `seat_failed`/`moderator_failed`/`run_failed`, honest partial Moderator path for a timed-out seat, and a verified no-late-writes guarantee | `013-run-and-seat-timeouts.md` |
| 014 | **PASS (LOCAL)** | Reachability + test hygiene: real `GET /modelmix` serves the built frontend and the Council sidebar gains a ModelMix nav link (cockpit reachable from a production build); every backend-test `RunRegistry()` writes to an isolated `tmp_path` store instead of the live session directory | `014-reachability-and-test-hygiene.md` |
| 015 | **PASS (LOCAL)** | Telemetry truth layer: events carry wall-clock `ts`; persistence keeps provider `usage`/`finish_reason` (opaque) and `started_at`/`completed_at` on messages — fixing the moderator finish_reason reload bug; the frontend truth layer + `describeUsage` capture everything without rendering; the last polling test is isolated | `015-telemetry-truth-layer.md` |
| 016 | **PASS (LOCAL)** | Compact top bar + panel view controls (frontend-only): one thin persistent top strip (brand, inert `Mode: Mix` label, session status, New Session moved from `.modelmix-actions`, Details-hidden run metadata, Back to Council; no Settings), and CSS-driven per-panel Collapse/Maximize/Reset controls that hide panels from layout without unmounting them, with view state confined to local component state + pure `panelView.js` helpers and `modelmixState.js`/backend untouched | `016-compact-top-bar-and-panel-controls.md` |
| 017 | **PASS (LOCAL)** | Settings shell (frontend-only): a gear entry in the compact top bar opens a conditionally-rendered overlay — About (real `pkg.version` from an imported `../../package.json`, MIT/copyright, text-only AI Counsel attribution, repo URL), Providers (read-only Connected/Not-connected rows computed from the now-exported `configuredSources` with zero credential values and an honest unavailable state), Defaults (`modelmix.defaultSeatModels` localStorage trio saved/cleared and applied at initial mount, with frozen `FALLBACK_SEAT_MODELS` preserving the exact built-in defaults) | `017-settings-shell.md` |
| 018 | **PASS (LOCAL)** | Telemetry rendering (frontend-only): `seatTelemetry.js` builds honest per-seat footers — usage labeled `authoritative (provider-reported)` via `describeUsage` showing the provider-reported total token count (`total_tokens`/`totalTokenCount`, `<n> tokens`) when finite, else the raw key names, or `unavailable`, Moderator-only `finish_reason` (`stop`/`not reported`), ModelMix-calculated elapsed labeled `(calculated)` with the raw wall-clock `HH:MM:SS → HH:MM:SS` range (running seats show `Started:`), rendered only for the live turn | `018-telemetry-rendering.md` |
| 019 | **PASS (LOCAL)** | Output guardrails (backend enforcement): new `guardrails.py` owns provisional `WARNING_OUTPUT_THRESHOLD_CHARS = 20_000` / `HARD_OUTPUT_CAP_CHARS = 40_000` and an exact-boundary `clip_delta`; `run_seat`/`run_moderator` emit a one-shot `seat_output_warning`/`moderator_output_warning` on first crossing, then at the hard cap stop consuming the provider stream and terminate as `seat_completed`/`moderator_completed` with `finish_reason: "modelmix_output_cap"` — an honest terminal outcome distinct from completion, cancellation, provider termination, failure, and timeout; non-streaming paths are capped with no warning; no `events.py`/`persistence.py`/`journal.py`/`timeouts.py`/`history.py`/`registry.py`/frontend changes | `019-output-guardrails-backend.md` |
| 020 | **PASS (LOCAL)** | Configurable output guardrails (backend): `TwoWorkerRequest` gains optional `warning_threshold_chars`/`hard_cap_chars` (`gt=0`); `routes.py::_resolve_guardrail_overrides` defaults omissions to the Mission 019 constants, rejects values outside `guardrails.MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`, and rejects `hard_cap_chars < warning_threshold_chars` — all surfaced as 422 before any provider is called; the resolved pair rides the exact `registry.start → _run → _run_phase → multiplex_workers/run_moderator` chain (mirroring `seat_timeout`); enforcement logic and event contract byte-for-byte unchanged, frontend zero changes, nothing persisted | `020-configurable-output-guardrails-backend.md` |
| 021 | **PASS (LOCAL)** | Guardrails settings + visibility (frontend): new `guardrailSettings.js` pure module (validate/load/save/clear + `MIN=100`/`MAX=200_000` bounds) powers a 4th **Guardrails** section in the Settings overlay (after Defaults) that saves/clears a local `modelmix.guardrails` override; `send()` injects `warning_threshold_chars`/`hard_cap_chars` only when a valid override exists; `seat_output_warning`/`moderator_output_warning` are recorded as live-only `outputWarning` (never persisted to history/hydration) and rendered in every seat footer (`Approaching output limit: 22,451 / 20,000 chars`); worker seats gain the Moderator's `finish_reason` capture and finish captions now render on all seats with `modelmix_output_cap` → "Output capped by ModelMix" and every other value verbatim; `buildSeatTelemetry` drops the now-obsolete `seatKey` param. Frontend-only — no backend, API, or persistence changes | `021-guardrails-settings-and-visibility.md` |
| 022 | **PASS (LOCAL)** | Alpha acceptance integration tests, backend (verify-only): new `test_modelmix_alpha_acceptance.py` proves Punch Board item-33 checklist items 4–11 through the real routes — ordered stream of both workers then the Moderator, cancel via the real route (one `run_cancel_requested` after all deltas, terminal `run_cancelled`, no post-cancel deltas, persisted `cancelled`, both providers terminated), worker-failure survival (run ends `partial`; failed worker's partial output stays persisted but is excluded from the Moderator handoff, replaced by the honest unavailable line), session reopen reconstructing the full 7-message transcript, multi-turn seat isolation across a real second POST (no cross-seat leakage), provider-faithful telemetry on reopen, and no credential leak into stream/journal/persisted session. One deliberate async-httpx single-loop deviation only for the two-in-flight cancel test — everything else reuses the sync TestClient pattern. Discloses an observed cancel-path race: a sub-ms cancel window can hang the run `active` until the 600s run timeout, with `_run_phase` stuck in the `multiplex_workers` generator-`finally` gather and one seat's provider generator never receiving `CancelledError`; reported as a real gap, not patched (verify-only) | `022-alpha-acceptance-integration-test.md` |
| 023 | **PASS (LOCAL)** | Deterministic cancellation-race fix on `main @ b82505d`: `multiplex_workers`' generator `finally` replaces the unbounded `asyncio.gather` with `await_cancellation_grace(tasks)` (new `CANCEL_GRACE_SECONDS = 5.0` in `timeouts.py`), so a seat task that absorbs cancellation can no longer block the `CancelledError` from reaching `run_cancelled`; the Moderator phase awaits its task via `asyncio.shield` because a direct task await was proven to leave `_run_phase` un-woken forever when the moderator task absorbs the cancel. Deterministically proven by `backend/tests/test_modelmix_cancel_race.py` (8 tests constructing the stall with a holding fake — abandoned-mid-stream structure asserts, no-fast-path change, never `"timeout"`); full backend **403 passed**, frontend unchanged at **118 passed** / build / lint green | `023-cancellation-race-fix.md` |
| 024 | **PASS (LOCAL)** | Cancel-before-start terminal state fix: `start()` adds `await asyncio.sleep(0)` after `asyncio.create_task(...)` to guarantee `_run` has entered its `try` block before the caller can cancel; `mark_status("active")` moved inside `try` so the except handler covers the earliest cancel point. Root cause: CPython 3.10 `coro.throw(CancelledError)` on a never-started coroutine skips the body entirely. Deterministically proven by `test_cancel_before_run_starts_reaches_terminal_cancelled`; full backend **404 passed**, `ruff check` clean, no existing test modified | `024-cancel-before-start-terminal-fix.md` |
| 025 | **PASS (LOCAL)** | Harden the local backend boundary: required admin auth (`_require_admin`, reused unchanged) on every endpoint that reads/writes/uses stored credentials or makes a server outbound request with a client-influenced target/credential. Added `dependencies=[Depends(_require_admin)]` to 20 endpoints in `backend/main.py` (16 required + 4 judgment extensions: `GET /api/models`, `GET /api/models/direct`, `GET /api/ollama/tags`, `GET /api/custom-endpoint/models`), closing the `test-custom-endpoint` blind SSRF-to-stored-key path before any outbound call. Three existing tests hitting a newly-guarded endpoint over a non-loopback TestClient peer (font-size, advisor presets, council presets) switched to loopback peers as the legitimate local-operator case. New `test_admin_guard_credential_endpoints.py` (27 tests) proves non-loopback rejection without token (401/403), loopback success, bearer-token success, and outbound-never-invoked for the SSRF path. Full backend **431 passed**, `ruff clean`; frontend **118 passed** / build / lint green. Flagged follow-ups: CORS regex matches any dotted-IPv4 origin; custom-endpoint URL allow-listing for a local loopback attacker | `025-harden-local-backend-boundary.md` |
| 026 | **PASS (LOCAL)** | Real Windows ACL hardening for credential file storage, scoped to `backend/credentials/file_backend.py`: `os.chmod(0o600)` is a no-op on Windows, so after each atomic credential write `_harden_credentials_file()` runs `icacls "<path>" /inheritance:r /grant:r "<current-user>":F` via `subprocess` (no new dependency), gated behind `sys.platform == "win32"`; the current user is resolved from `USERNAME`/`USERDOMAIN` env vars (fallback `os.getlogin()`). Failures log a warning and never crash a write; a once-per-process startup warning surfaces pre-existing or never-hardened plaintext files on Windows. Default `file` mode and `get_effective_mode()` unchanged by declared boundary. New `test_credentials_file_hardening.py` (7 tests) mocks `subprocess.run`/`sys.platform`. Full backend **438 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Advances item 30 (current-model half); separate later re-verification of credential storage required once Tauri (item 34) exists | `026-windows-credential-file-hardening.md` |
| 027 | **PASS (LOCAL)** | Auto-remediate an unhardened credentials file on startup, scoped to `_warn_if_unhardened()` in `backend/credentials/file_backend.py`: on the first touch (read or write) of an existing, not-yet-hardened Windows file it now attempts `_harden_credentials_file()` directly (logic reused exactly from Mission 026), logging INFO "Restricted..." on success or the existing warning on failure. A single once-per-process automatic remediation — an upgraded user who just opens the app gets their pre-existing plaintext file protected without writing a new key or running icacls themselves. Never raises; a failed attempt logs and continues. Extends `test_credentials_file_hardening.py` to 10 tests (one Mission 026 test necessarily reconciled because its "reads never invoke icacls / always warn" assertion is directly contradicted by remediation-on-read; flagged). Full backend **441 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Item 30 current-model half closeable; Tauri re-check (item 34) carried forward | `027-credentials-file-startup-remediation.md` |
| 028 | **PASS (LOCAL)** | Verify and harden the existing Compare (no-moderator) backend path. `TwoWorkerRequest.moderator_model` optional and `registry._run_phase` / `orchestrator.multiplex_workers` already support a two-worker run with no moderator phase, but had ZERO test coverage. Driven through the REAL HTTP route (`POST /api/modelmix/runs/stream` with `moderator_model` omitted) in new `test_modelmix_compare_mode_backend.py` (7 tests, alpha-acceptance harness): (1) both workers stream fully with ZERO moderator events and `run_completed "completed"`; (2) one worker fails -> `run_completed "partial"` + persisted session reflects the failed seat via `GET /sessions/{id}`; (3) both workers fail -> OBSERVED as-shipped `run_completed "partial"` (not `failed`; product-semantics note, not a defect); (4) multi-turn isolation holds moderator-less and the dead `seat_histories["moderator"]` key never leaks to either worker; (5) per-worker guardrails (warning/hard cap) still apply; (6) cancellation reaches `run_cancelled` mid-stream; (7) reopening a moderator-less session reconstructs with no moderator message and nothing chokes on the moderator's absence (`models["moderator"]` persists as `None`, tolerated by `_validate`). No real defect found; NO production code changed; no `mode` concept added; no frontend change. Full backend **448 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Backend half of item 28 deliverable; frontend Compare half is the next mission | `028-compare-backend-verification.md` |
| 029 | **PASS (LOCAL)** | Deliver the frontend Compare mode + a no-moderator status fix, closing item 28. Part 1 backend fix in `orchestrator.multiplex_workers`: replaced `failed: bool` with `failed_seats: set`, so when BOTH workers fail with no moderator the run reaches `run_completed` with `status="failed"` (not `"partial"`); moderator path (`emit_run_completed=False`) untouched. Point-3 compare test renamed to `test_no_moderator_both_workers_fail_reaches_run_completed_failed` and now asserts `failed`. Part 2 frontend Compare mode: the inert top-bar `Mode: Mix` `<span>` becomes a real `select.modelmix-mode-select` (Mix / Compare) persisted via new pure module `modelmixMode.js` (`loadSavedMode`/`saveMode`, `localStorage["modelmix.mode"]`, valid values only `mix`/`compare`, default `mix`, NO `solo`); in Compare mode the composer Moderator selector is not rendered, `moderator_model` is omitted from the request body, the center moderator panel is hidden-but-kept-mounted via existing `modelmix-panel-hidden` seam, and the models strip uses a 2-col grid; the mode control disables during an active run via existing `modelSelectorsDisabled`. New tests: `modelmixMode.test.js` (6), `ModelMixSendCompare.test.jsx` (6). One existing top-bar test necessarily updated (the mode span had to become a real control) — sole modified existing test; all others pass unmodified. Validation: combined compare+moderator backend **18 passed**, full **448 passed**, `ruff` clean; frontend **130 passed** (118 prior + 12 net new) / build green / lint green. Item 28 (Compare) CLOSED | `029-compare-mode-status-fix-and-frontend.md` |
| 030 | **PASS (LOCAL)** | Backend support for Solo: optional `worker_b_model`, pre-provider 422 rejection of the one-worker-plus-Moderator hybrid, active-seat orchestration, persistence validation for the Solo model shape, and isolation/guardrail/cancellation coverage. Backend **460 passed**; frontend baseline **130 passed** / build / lint green. Backend half of item 27 | `030-solo-mode-backend.md` |
| 031 | **PASS (LOCAL)** | Frontend Solo delivery, closing item 27 with Mission 030. `modelmixMode.js` accepts and persists `solo`; the control is Mix / Compare / Solo and retains active-run locking. Solo renders only Worker A's selector, requires only Worker A, and omits both unused model keys. Moderator and Worker B panels remain mounted but CSS-hidden; Worker A uses the existing single-column visual treatment. Mode visibility stays independent from panel-view state, preventing a hidden-seat maximize target from blanking Solo. Eight new Solo tests; sole modified existing test is the necessary top-bar option assertion. Frontend **138 passed** / build / lint green; backend workspace-temp rerun **460 passed** | `031-solo-mode-frontend.md` |
| 032 | **PASS (LOCAL)** | Tauri 2 toolchain check and minimal native shell: observed Rust/Cargo 1.98.0, MSVC C++ tools, and WebView2 151.0.4129.107; installed the missing `tauri-cli 2.11.4`; added standard `src-tauri/` pointing development at the existing `/modelmix` Vite route and production assets at `frontend/dist`, with no sidecar/backend launch. Direct Windows inspection observed the real three-panel cockpit in the native `target\debug\app.exe` window against the separately started backend. `cargo check` green; frontend **138 passed** / build / lint green; backend workspace-temp rerun **460 passed** after the exact command reproduced the known default-temp `WinError 5`. Item 34 remains in progress for sidecar and installer work | `032-tauri-toolchain-and-shell.md` |
| 033 | **PASS (LOCAL)** | Standalone Windows PyInstaller `onedir` backend bundle: packaging-only package-context adapter, durable spec, installed keyring hook verification, and narrow bundled project-metadata fallback. The isolated frozen executable ran with a sanitized no-Python/uv/venv environment, served health/session/settings/MCP routes, persisted and cleared fake keyring/file sentinels across restarts, produced a direct non-inherited current-user FullControl ACL, and shut down with no orphan/JSON/temp-file/live-data damage. Backend **461 passed** with workspace-temp after the known default-temp failure; frontend **138 passed** / build / lint green; Rust format/check and focused Ruff green. Item 34 remains open for Tauri sidecar, installer, and final credential packaging | `033-pyinstaller-backend-bundle.md` |
| 034 | **PASS (LOCAL)** | Frozen-aware user data directory fixing the Mission 033 finding (`_internal\data\credentials.json`): new stdlib-only `backend/user_data_dir.py` (`is_frozen()` + `resolve_user_data_dir()` → repo `data/` unmodified when not frozen, `%LOCALAPPDATA%\ModelMix` when frozen, executable-dir fallback + warning, mkdir before return); `CREDENTIALS_FILE`, `SETTINGS_FILE`, and `personas._DATA_DIR` derive from it; keyring/store/route/`icacls`/`src-tauri`/frontend untouched. New 7-test regression/simulation suite. Backend **468 passed** (461 unmodified + 7 new); focused credential run **24 passed**; `ruff` clean; frontend **138 passed** / build / lint green (required, unchanged). Frozen-mode path proven by simulation; real frozen-build confirmation required with item 34 | `034-frozen-aware-user-data-directory.md` |
| 057 | **PASS (LOCAL)** | Spend limit control and 402 confirmation UX (frontend-only) — closes Punch Board item 17. `modelmixBehavior.js` gains `loadSpendLimit`/`saveSpendLimit`/`clearSpendLimit` (validating `value > 0`); `send()` includes `spend_limit_usd` only when a valid saved value exists; a 402 renders the real backend message with an explicit "Proceed anyway" button that resends the identical original request body plus `confirm_over_budget: true`. Frontend **228 passed** (215 + 13 new) / build / lint green. Backend: zero files touched | `057-spend-limit-control-and-confirmation-frontend.md` |


## Current Verified Product Slice

The accepted implementation through Mission 009 establishes:

- two independent worker seats with no cross-worker answer leakage in the implemented run path;
- one Moderator phase that receives the allowed completed worker outputs;
- true incremental ChatGPT OAuth streaming through the ModelMix streaming contract, with non-streaming fallback support;
- one ordered SSE run feed carrying ModelMix run/seat identity and monotonic sequence information;
- process-local event journal with replay/tailing;
- disconnect separated from explicit cancellation;
- fixed separate Send and Stop controls;
- three-panel browser cockpit: Worker A | wider Moderator | Worker B;
- searchable configured-model selectors for all three seats;
- exact provider/model IDs preserved with no silent substitution;
- selector locking during active/reconnecting/cancelling runs;
- explicit worker/Moderator failure and partial-result handling in the implemented slice.
- durable schema-v1 atomic JSON sessions with canonical seat/audience/role messages and immutable terminal run snapshots;
- cockpit hydration from persisted truth with the durable sequence used as the existing SSE replay cursor.
- bounded multi-turn history keyed only by seat identity, including a Moderator history that excludes prior-turn worker output;
- worker model hot-swaps that preserve the seat's history and failed/cancelled seat partial output when non-empty.
- a deterministic seat-history character budget: each historical message middle-truncated to 4,000 characters and each single-seat assembled history capped at 24,000 characters via whole-turn oldest-first eviction (never an orphan assistant message).
- a runnable frontend test suite: `npm test` executes the existing reducer/API/hydration tests (and configured-model and font-size tests) through Vitest with an observed 24/24 pass; `npm audit` reports 0 vulnerabilities.
- a multi-turn cockpit display: each panel renders its seat's prior turns (compact prompt header above that turn's output) above the live streaming turn, sourced from a `history` array archived from prior session runs.
- honest prompt/model plumbing and a session reset: archived turns carry the real submitted prompt and selected model IDs, absent prompts render nothing (no placeholder), and a separate New Session control (disabled while a run is active) clears the local session key and resets the cockpit while preserving model selections.
- ModelMix-owned wall-clock run and seat timeouts: `timeouts.py` owns `RUN_TIMEOUT_SECONDS = 600` and `SEAT_TIMEOUT_SECONDS = 300`; `run_seat` and `run_moderator` bound their phases and `RunRegistry._run` bounds the whole run, terminating through the existing event types with `reason: "timeout"`, preserving prior deltas, routing a timed-out seat through the honest partial Moderator path, distinguishing explicit cancel (`run_cancelled`) from timeout, and guaranteeing no journal/persistence writes after a run reaches terminal.
- production-build reachability and test hygiene: `GET /modelmix` serves `index.html` from `FRONTEND_DIST_DIR` (404 with a clear message when not built) and the Council sidebar has one visible ModelMix nav link, so the three-panel cockpit is reachable from a built app; every `RunRegistry()` in `backend/tests/` writes to an isolated `tmp_path` store — proven by an unchanged real-data file count (229 before = 229 after) across every previously-polluting test file.
- a compact persistent top strip and CSS-driven panel view controls: one `header.modelmix-topbar` replaces the separate header and always-visible run metadata — brand, inert `Mode: Mix` label, session status from the existing `observer.overall` vocabulary, the New Session control (moved, same handler/disabled binding, no behavior change), a Details disclosure (off by default) holding the `Run: <id>` / `Last sequence: <n>` debug line, and the unchanged Back to Council link, with no Settings entry; each `TranscriptPane` header gains Collapse (body only, header stays) and Maximize (one panel full width, the other two hidden from layout), plus one Reset visible whenever any panel is collapsed or maximized — all layout via CSS classes so all three panels stay mounted, with view state in `panelView.js` helpers and `ModelMixObserver` local state only (`modelmixState.js`/backend untouched; reload resets the view).
- a Settings shell in the cockpit: a gear entry in the compact strip (`aria-label="Settings"`, `aria-expanded`) opens a conditionally-rendered modal overlay (no route, no new window) with three sections — About (real `pkg.version` imported from `../../package.json` with no duplicated literal, the MIT/copyright line, text-only AI Counsel attribution, and the repo URL), Providers (read-only OpenRouter/Ollama/Direct/Custom/OAuth Connected-or-Not-connected rows computed from the exported `configuredSources` against the settings `loadModels` already fetches, zero credential values, honest "unavailable" when the snapshot is null), and Defaults (Save/Clear the `modelmix.defaultSeatModels` localStorage trio; the three seat selectors initialize from the saved value at mount, falling back to frozen `FALLBACK_SEAT_MODELS` that exactly match the previous built-in selections — so "no saved defaults ⇒ exact hardcoded defaults" is a direct regression test).
- bounded cancellation cleanup: a cancel now reaches terminal `run_cancelled` within `CANCEL_GRACE_SECONDS = 5.0` even when a seat or the Moderator's provider absorbs `CancelledError` and holds — `multiplex_workers`' `finally` uses `await_cancellation_grace` (`timeouts.py`) in place of the unbounded gather, and the Moderator await is shielded in `registry.py` so a slow-to-cancel moderator cannot leave the run phase un-woken; fast-cancel behavior is unchanged and proven by deterministic stall-provider tests.

## Mission 007.5 Verification Evidence

Accepted Mission 007.5 results:

- MCP retained at **2.1.1**;
- MCP tests: **146 passed**;
- full backend suite: **458 passed, 5 failed**;
- the five remaining failures were recorded as pre-existing Windows-specific legacy chassis test issues rather than MCP migration regressions;
- Python security audit: **0 known vulnerabilities** across 95 locked dependencies;
- backend import/runtime mount: verified, MCP mounted at `/mcp` with SSE `/mcp/sse`;
- frontend dependency audit: **0 vulnerabilities**;
- frontend production build: **PASS**.

MCP remains an **alpha non-goal** for ModelMix product scope; compatibility maintenance did not promote it into the alpha feature plan.

## Punch Board Progress Mapping

Mission numbers are implementation slices; they are not one-to-one with the 47 locked Punch Board items.

### Satisfied or substantially satisfied

- **1 — Freeze inherited baseline**
- **2 — Run inherited verification**
- **3 — Spike the four unknowns**
- **5 — Lock chassis policy**
- **6 — Create ModelMix-owned backend boundary**
- **8 — Context isolation policy**
- **10 — Define ordered event contract** — every canonical event now carries a wall-clock `ts` in both constructors, additive alongside `seq`/`run_id`/`type` (Mission 015); the cockpit surfaces that timing truth per seat (Mission 018)
- **11 — ModelMix persistence boundary**
- **15 — Non-streaming Mix vertical slice**
- **16 — Prove failure + cancellation** — **Mission 013** proves run/seat/Moderator timeouts share the same loop and cancellation machinery as failure and explicit cancel (no-late-writes verified in journal and session); **Mission 023** proves cancellation stays terminal `run_cancelled` within `CANCEL_GRACE_SECONDS` even when a seat/Moderator provider does not honor cancellation (deterministic stall tests)
- **18 — Add normalized provider streaming interface**
- **19 — Multiplex streams into one ordered SSE run feed**
- **20 — Stream Moderator**
- **21 — Build browser-first three-panel cockpit** — reachable from a production build (`GET /modelmix`) and from the Council sidebar (ModelMix nav link) as of Mission 014
- **22 — Bind UI to durable run/session state**
- **23 — Add Stop behavior**
- **24 — Thin top controls** — compact top strip, session and Settings controls, panel controls, and persisted Mix / Compare / Solo selector, completed through Missions 012/016/017/029/031
- **25 — Minimal telemetry** — state, elapsed time, provider-reported tokens where available, labeled estimates, reliable per-call cost only; rendered honestly per seat since Mission 018 (usage provenance, calculated timing, Moderator finish reason; cost/pricing wiring and per-historical-turn footers are deferred follow-ups)
- **27 — Solo** — closed through Missions 030 + 031: one-worker backend path plus persisted frontend mode, exact request omission, and single-panel cockpit

### Partially satisfied — keep open

- **7 — Domain objects:** run/event/seat concepts exist, but the full locked domain/schema-version contract is incomplete.
- **9 — Run state machine:** core active/terminal outcomes exist; complete timeout/retry/state contract remains open. Mission 013 adds honest wall-clock `reason: "timeout"` terminal outcomes for runs, seats, and Moderator.
- **12 — Provider capability matrix:** streaming capability/fallback and configured discovery exist; the full capability matrix remains open.
- **14 — Deterministic mock provider:** current tests use deterministic fakes/mocks, but the full locked failure/timeout/rate-limit fixture matrix remains open.
- **29 — Finalized Mix multi-turn behavior:** seat histories, Moderator history, hot-swap continuity, deterministic context bounding, and completed-turn cockpit display are implemented; retention/delete UX remains open.
- **17 — Spend/runtime guardrails — CLOSED (visibility: 044/045, warning: 050/051, gate: 052/057).** explicit Stop, the turn cap, seat-history character budgets (Mission 010), wall-clock run (600s) / seat-Moderator (300s) timeouts (Mission 013), hard output cap + warning (Missions 019–021), dollar cost visibility (Missions 044/045), per-seat spend warning (Missions 050/051), and dollar-cap enforcement with frontend confirmation UX (Missions 052/057) are all complete end to end.
- **26 — Provider/settings UX:** searchable configured selectors are complete; the visible ModelMix sidebar navigation entry point exists (Mission 014); the cockpit Settings surface is now a real entry (Mission 017) with read-only provider status from the exported `configuredSources` and saved default seat models; full alpha provider/settings entry flow remains open.
- **4 — License and provenance — PARTIAL — MISSION 017** (the cockpit About section surfaces the MIT license, the copyright holder, the real version, the text-only AI Counsel attribution, and the repo URL; the `OPEN_SOURCE_CREDITS.md`, inherited-module provenance, and dependency-license inventory remain open)

### Not yet satisfied / upcoming

- **13 — Privacy/data-routing rules**
- **28 — Compare** — **CLOSED (Missions 028 + 029).** Backend path verified end to end (Mission 028) and the frontend Compare mode + no-moderator status fix delivered (Mission 029): real `select.modelmix-mode-select` (Mix/Compare) persisted via `modelmixMode.js`; Compare hides the Moderator selector, omits `moderator_model` from the request body, hides-but-keeps-mounted the moderator panel; both-workers-fail now emits `run_completed "failed"` instead of `"partial"`. Backend **448 passed**, `ruff` clean; frontend **130 passed** / build / lint green.
- **30 — Credential verification in actual packaging model**
- **31 — Local backend hardening**
- **32 — Basic structured observability**
- **33 — Alpha acceptance gate** — backend-provable checklist items (stream both workers + Moderator, cancel, survive worker failure, reopen session, multi-turn isolation, honest telemetry, no credential leak) proven through the real HTTP surface by **Mission 022** (`test_modelmix_alpha_acceptance.py`, 7 tests/395 total); the cancel-path race Mission 022 disclosed (sub-ms cancel window could hang a run until the 600s run timeout) is **closed by Mission 023** with bounded cancel cleanup (`CANCEL_GRACE_SECONDS = 5.0`, deterministic `test_modelmix_cancel_race.py`, 8 tests/403 total). UI-bound items (launch, three panels, configure) remain covered by Missions 014/016/007 evidence, and a live-provider manual launch pass remains the final alpha step. Gate declaration is deferred to the next verification pass
- **34–47 — Post-alpha roadmap**

## Locked Safeguards Still Open

The Punch Board safeguards remain active requirements:

- provider/account usage warning where authoritative data exists, otherwise clearly labeled ModelMix-tracked/estimated data — **Mission 019 codes this as explicitly deferred**: no authoritative quota/rate-limit data exists in this codebase to compare against, so it is not honestly buildable;
- excessive output-token warning — **implemented (Mission 019), configurable per request (Mission 020), and user-configurable from the cockpit (Mission 021)** as a one-shot `seat_output_warning`/`moderator_output_warning`, defaulting to the 20k-char threshold, with the saved override sent on each run request and the crossed threshold rendered live in the seat footer;
- configurable hard output cap at the closest enforceable boundary — **implemented (Missions 019/020/021)** as an exact 40k-char deterministic cap in `guardrails.py`, with the default now overridable per request (bounded 100–200_000 chars) and via the Guardrails settings section;
- terminal state must distinguish normal completion, user cancellation, provider/model termination, and ModelMix hard-cap termination — **implemented (Mission 019)**: capped participants terminate as `seat_completed`/`moderator_completed` with `finish_reason: "modelmix_output_cap"`, never as failed or timed out.

These safeguards are not to be implemented prematurely in unrelated missions, but they are **not post-alpha by default** and must be wired when the settings/run-control layer reaches them.

## Mission 008 Result

Mission 008 directly closes items 11 and 22 with schema-v1 atomic JSON behind a
ModelMix interface, canonical isolated seat messages, durable run/event cursors,
restart reconstruction, and three-panel hydration. See
`008-durable-persistence-cockpit-hydration.md` for observed commands and scope.

## Mission 009 Result

Mission 009 reads schema-v1 canonical runs/messages without mutation, builds at
most eight prior prompt/answer pairs independently for each seat, and passes
those histories into the existing worker and Moderator provider calls. Prior
worker output is never added to Moderator history, and Moderator output is never
added to either worker history. See `009-seat-scoped-multi-turn-context.md` for
the observed validation output and exact scope.

## Mission 010 Result

Mission 010 replaces the previous 100,000-character-per-message history bound
with a ModelMix-owned per-message budget of 4,000 characters and adds a
24,000-character per-seat assembled-history budget with whole-turn oldest-first
eviction. `history.py` no longer imports a private symbol from `moderator.py`;
current-turn Moderator bounding and the `build_seat_history` contract are
unchanged. See `010-seat-history-budget.md` for the observed validation output.

## Mission 010.5 Result

Mission 010.5 adds Vitest (`^4.1.11`, Vite 7-compatible) and jsdom (`^26.1.0`)
as frontend devDependencies, a non-watch `npm test` (`vitest run`) script, and a
minimal `test` block in the existing `vite.config.js`. The three existing test
files were converted from the `node:test` API to purely an import-path change
(`import { test } from 'vitest'`); no assertions or product code changed. The
observed run: 24/24 pass, 3 files, exit clean. `npm audit`: 0 vulnerabilities.
See `010.5-frontend-test-runner-interlock.md`.

## Mission 011 Result

Mission 011 adds a `history` array of completed prior runs to the frontend seat
state. `hydrateModelMixState` archives every run before the latest one in
chronological order (filtered per run by message `run_id`), the live slots keep
exactly their prior behavior, and a new pure `archiveCurrentRun(state)` resets
the live slots while preserving `sessionId` and appending the outgoing run when
it produced seat content. `ModelMixObserver` archives when a new run starts, and
`TranscriptPane` renders each seat's prior turns above the live turn with the
prior prompt as a compact header. `applyModelMixEvent` is unchanged. See
`011-multi-turn-cockpit-display.md`.

## Mission 012 Result

Mission 012 ensures archived turns show their real prompt during a live session
and adds a session reset control. `send()` stamps the `starting` state with the
submitted `prompt` and the three trimmed selected model IDs so the next
`archiveCurrentRun` captures them. `TranscriptPane` renders the prior-turn prompt
only when present — no `—` placeholder for missing data. A new pure
`startNewSession(state)` returns a fresh cockpit (`createModelMixState()`, empty
`history`) carrying the current model selections forward; `ModelMixObserver`
calls it after removing `modelmix.sessionId` from localStorage. No backend
endpoint is called. The New Session button is a separate fixed control,
disabled only while a run is active via the existing `modelSelectorsDisabled`.
Five tests were added; the existing 30 frontend tests pass unmodified.
`applyModelMixEvent` is unchanged. See
`012-session-control-and-prompt-plumbing.md`.

## Mission 013 Result

Mission 013 delivers ModelMix-owned wall-clock enforcement for runs, seats, and
the Moderator. `backend/modelmix/timeouts.py` owns `SEAT_TIMEOUT_SECONDS = 300`,
`RUN_TIMEOUT_SECONDS = 600`, and a single cumulative-deadline helper
(`aiter_with_deadline`, Python 3.10 compatible). `run_seat` bounds each worker
seat, `run_moderator` bounds the Moderator phase, and `RunRegistry._run` bounds
the whole run — all terminating through the existing `seat_failed` /
`moderator_failed` / `run_failed` events with an explicit `reason: "timeout"`.
A timed-out seat routes through the existing one-failed-worker partial path so
the Moderator still runs with the surviving output (its handoff never treats the
timed-out seat's partial deltas as complete), and the persisted session records
the timed-out seat's partial content with `status: "failed"` and an error naming
the timeout. Explicit cancel is unchanged (`run_cancelled`, never a timeout
label). Because seats only ever push to the local queue and the drain loop is
the single journal writer, no event is written after a run reaches terminal —
verified in both the in-memory journal and the durable document. Existing tests
are untouched: the focused suites (49) and the full backend suite (341 prior
tests, 352 with the 11 new timeout tests) pass, and the frontend trio
(test/build/lint) stays green even though no frontend file changed. See
`013-run-and-seat-timeouts.md`.

## Mission 014 Result

Mission 014 makes the cockpit reachable and stops the tests from polluting live
data. `backend/main.py` registers `GET /modelmix` next to the root handler: it
serves `index.html` from `FRONTEND_DIST_DIR` (registered before the StaticFiles
mount so it wins in production builds) and returns a clear 404 when the frontend
is not built; two route tests in `test_main_preflight.py` cover the 200 and 404
paths. The Council sidebar gains one visible green **ModelMix** link
(`/modelmix`). Every `RunRegistry()` construction in `backend/tests/` now passes
an explicit `AtomicJsonModelMixPersistence` rooted at `tmp_path`: the four
named timeout sites plus the five journal constructors and the shared moderator
`start_run` helper (see the canonical report for the exact grep). The suite-run
disk proof: 229 session files in the real `data/modelmix/sessions/` before and
after re-running all three previously-polluting test files. Two one-line
cosmetics landed: the `multiplex_workers` `event_factory` parameter regained
its signature indentation, and `history.py` regained its trailing newline.
Validation: full backend suite **354 passed** (352 prior + 2 new route tests),
ruff clean, frontend **35 passed** / build green / lint clean. See
`014-reachability-and-test-hygiene.md`.

## Mission 015 Result

Mission 015 is the telemetry truth layer — capture only, no rendering. Both
canonical event constructors now stamp every event with a wall-clock float `ts`
(`journal.append`, the production path, and `events.EventSequencer.create`, the
fallback path). `persistence._apply_event` initializes four new nullable message
fields and fills them: `usage` and `finish_reason` on `seat_completed` /
`moderator_completed` (opaque, un-normalized, only-when-present so a real value
is never clobbered with null); `started_at` from `seat_started` /
`moderator_started`; `completed_at` on every completion, failure, and cancel.
That fixes the confirmed pre-existing bug: a Moderator finish reason used to
vanish on reload because persistence never wrote it. The frontend captures
`usage` / `startedAt` / `completedAt` per seat through the live stream,
hydrated live slots, archived history entries, and `buildHistoryEntry`, and
exports the single provenance vocabulary `describeUsage` (`'authoritative'` /
`'unavailable'`). Mission 015 also fixed the last Mission 014 leftover: the
streaming route test monkeypatches `routes.run_registry` to an isolated
`tmp_path` store. Validation (mission-specified): cleared
`data/modelmix/sessions/*.json`, full backend suite **360 passed** (354 prior +
6 new), and the directory was **empty** afterward — hard proof of no pollution;
frontend **41 passed** (35 prior + 6 new, two existing archive assertions
extended with the new null fields); build green; lint clean; ruff clean. See
`015-telemetry-truth-layer.md`.

## Mission 016 Result

Mission 016 is frontend-only: `ModelMixObserver.jsx`, `ModelMixObserver.css`,
and two new files (`panelView.js` view helpers and their tests). The
old `.modelmix-header` (kicker + title + Back to Council) and the always-visible
`.modelmix-run-meta` are gone, replaced by one `header.modelmix-topbar`: the
ModelMix brand; an inert `Mode: Mix` `<span>` (no dropdown — Solo/Compare are
items 27/28); the session status reusing `observer.overall` verbatim with the
same data-status color vocabulary as the panels; the New Session button moved up
from `.modelmix-actions` (same handler, same `modelSelectorsDisabled` binding,
behavior unchanged); a Details disclosure, off by default, that CSS-hides the
`Run: <id>` / `Last sequence: <n>` debug line (element stays mounted); and the
unchanged Back to Council link. No Settings entry/link/route was added. The
composer and its model selectors are functionally identical (only the container
was re-tightened and New Session removed from the actions row); Send/Stop
adjacency and all disabled logic are unchanged. Each `TranscriptPane` header now
has Collapse/expand (hides only its `.modelmix-transcript` via
`.modelmix-panel-collapsed`; header stays) and Maximize/Restore (one panel full
width via `.modelmix-workers--maximized`, other two `.modelmix-panel-hidden`;
all three nodes stay mounted), with one Reset control shown whenever any panel
is collapsed or maximized. View state lives only in new local
`panelView`/`detailsOpen` state and the pure helpers in `frontend/src/panelView.js`;
`modelmixState.js`, `modelmixApi.js`, and all backend code are untouched, so the
41 prior frontend tests pass unmodified. New coverage: 4 `panelView.test.js`
unit tests (class matrix, reset predicate, default view, and a proof that view
keys never leak into `createModelMixState`/`applyModelMixEvent`) and 6 jsdom
render tests of the real component with mocked API/configuredModels/modelmixApi
modules (top-strip structure, collapse-mounts, maximize-mounts, reset-from-any-
combination, New Session behavior, Details disclosure). Validation
(mission-specified): `npm test` **51 passed** (41 prior + 10 new), `npm run
build` green, `npm run lint` clean, `uv run pytest backend/tests -q` **360
passed** unchanged. See `016-compact-top-bar-and-panel-controls.md`.

## Mission 017 Result

Mission 017 is the Settings shell — frontend-only, no new route. One line in
`configuredModels.js` exports `configuredSources` (implementation unchanged).
`ModelMixObserver` adds `button.modelmix-settings-toggle` (gear, `aria-label`/
`title` "Settings", `aria-expanded`) to the compact strip; the Settings overlay
is **conditionally rendered only while open**, a modal (`role="dialog"`,
`aria-modal="true"`) with backdrop-click and close-control dismissal, so the
default cockpit's `textContent` still contains no "Settings" (the existing
`ModelMixObserver.test.jsx` line-99 assertion passes unmodified). Three
sections: **About** imports `pkg` from `../../package.json` and renders the real
`pkg.version` (no literal), "MIT — Copyright (c) 2025 Jacob Ben David" (from the
repo `LICENSE`), the text-only "ModelMix began as a fork/evolution of The AI
Counsel…" attribution, and the repo URL already in `README.md`; **Providers**
computes `configuredSources` against the `settingsSnapshot` captured inside the
existing `loadModels` effect and lists five read-only Connected / Not-connected
rows with `data-connected` — never rendering credential values or endpoint/based
URLs, with an honest "unavailable" state when the snapshot is null; **Defaults**
saves/clears `modelmix.defaultSeatModels` in `localStorage` and the three seat
selectors initialize from the saved trio at mount, falling back to a frozen
`FALLBACK_SEAT_MODELS` in the new pure `frontend/src/defaultSeatModels.js` that
exactly preserves the previous built-in literals. New local-only state:
`settingsOpen`/`settingsSection`/`settingsSnapshot`/`defaultsRevision`;
`modelmixState.js`, `modelmixApi.js`, `Settings.jsx`, `App.jsx`, `main.jsx`,
and all backend files are untouched; no dependencies added. Coverage: 5
`configuredSources.test.js` + 5 `defaultSeatModels.test.js` (node) and 8 jsdom
render tests in `ModelMixSettings.test.jsx` (vi.hoisted mutable settings mock,
real `configuredSources` via `importOriginal`, corrupt-value fallback, saved-
wins-on-mount, save/clear round-trip, and the existing 51 unmodified tests pass)
= **69 passed**; `npm run lint` clean; `npm run build` green (436 modules);
`uv run pytest backend/tests -q` **360 passed** unchanged. Maps to Punch Board
items **26** (Settings surface now real; entry flow remains), **4** (visible
license/copyright/credit — first slice), **24** (Settings surface delivered;
Mode selector remains open).

## Mission 018 Result

Mission 018 makes Mission 015's capture visibly honest — frontend-only, no
backend or `modelmixState.js`/`modelmixApi.js` changes. New pure module
`frontend/src/seatTelemetry.js` (with `formatTimestamp`/`formatElapsed`/
`rawUsageKeys`/`buildSeatTelemetry`) imports the single `describeUsage`
vocabulary and builds a footer item list per seat, gated on real activity:
idle and waiting seats render nothing. Rendered items in
`TranscriptPane`'s `.modelmix-telemetry` footer:

- **Usage** — `authoritative (provider-reported)`; when the provider-reported
  usage carries a finite `total_tokens` or `totalTokenCount`, the detail shows
  that number formatted as `<n> tokens`; otherwise it falls back to the raw
  provider key names (bounded to 8, then `N fields`). Honest `unavailable`
  otherwise (no guessed totals, no normalization, no fake percentage).
- **Finish** — Moderator only, from `finish_reason` (`stop`, `tool-calls`, …)
  or `not reported` when absent.
- **Elapsed** — `HH:MM:SS → HH:MM:SS` range plus a duration explicitly labeled
  `(calculated)` because it is ModelMix-computed from persisted event
  timestamps; a seat that started but did not finish shows only `Started: …`
  (no fabricated duration); a seat with only `completedAt` shows `Completed: …`.

The footer is rendered **only for the live turn** — prior-turn archives render
zero telemetry even though Mission 015 captures the same fields into history
(this is the explicitly deferred per-historical-turn footer follow-up), and
cost/pricing wiring is deliberately out of scope (a cost field is never
guessed or displayed). Coverage: 13 node tests `seatTelemetry.test.js`
(timestamp/elapsed formatting, provenance labels, raw-key detail, fake-free
running-seat behavior, finish-reason moderation, oversized-usage field count,
no-fabrication rules) and 3 jsdom render tests `ModelMixTelemetry.test.jsx`
(no session → zero footers; completed seats → authoritative/finish/calculated
footers; prior-turn archives → zero `prior` footers while live turns render and
`not reported` stays known-unknown), reusing the vi.hoisted mutable hydrate
container pattern with the same `api`/`configuredModels` mocks. Validation:
`npm test` **85 passed** (69 prior + 16 new), `npm run lint` clean, `npm run
build` green (437 modules), backend **360 passed** unchanged. Closes Punch
Board item **25** (SUBSTANTIALLY SATISFIED — MISSIONS 015/018 with the two
deferrals noted) and verifies items **10** (order/timing contract) and **17**
(timing guardrail input) as visible.

## Mission 019 Result

Mission 019 enforces the output guardrails at the backend live streaming loop
— the same loop as Mission 013's timeouts, so the exact-cap truncation and
event-order tests were the critical parts. New module
`backend/modelmix/guardrails.py` owns the provenance of the bounds:
`WARNING_OUTPUT_THRESHOLD_CHARS = 20_000`, `HARD_OUTPUT_CAP_CHARS = 40_000`
(provisional module-constant defaults; configurability is a later Settings
mission), and `clip_delta(delta, emitted, cap)` which clips one stream delta so
the cumulative emitted characters land exactly on `cap` when the producer
would exceed it and reports when the budget is exhausted.

`run_seat` and `run_moderator` now track cumulative emitted characters and:

- emit exactly one `seat_output_warning` / `moderator_output_warning` (payload
  `chars`/`threshold`, emitted after the crossing delta so `chars` is the live
  cumulative total) the first time the warning threshold is reached — purely
  informational, no stream interruption, no effect on multiplexer terminal
  bookkeeping;
- at the hard cap, clip the crossing delta deterministically so the persisted
  visible output is exactly the cap length, stop consuming the provider
  stream immediately (`break`), and terminate the participant as
  `seat_completed` / `moderator_completed` — never `seat_failed` — with
  `finish_reason: "modelmix_output_cap"`. Provider `finish_reason`/`usage`
  after the break are not collected, so `modelmix_output_cap` can never
  collide with real provider reasons and no fake usage is recorded. A capped
  seat/moderator completing means a capped run still finishes `completed`, not
  `partial` (the cap is a clean ModelMix termination, not a failure);
- cap the non-streaming (`provider.query`) path identically with no warning.

Interactions: the output cap and wall-clock timeouts are independent bounds —
whichever is reached first governs, and a capped seat is never also reported
timed out. User cancellation (`seat_cancelled`/`run_cancelled`) is untouched.
Under-threshold turns are byte-identical to the pre-guardrail path.

Boundaries: `events.py`, `persistence.py`, `journal.py`, `timeouts.py`,
`history.py`, `registry.py`, and every frontend file are untouched. The new
event types flow through the existing `EventSequencer.create`/`RunEventJournal
.append` constructors (arbitrary type strings), `_apply_event` ignores the
unrecognized warning events without mutating content/status/finish_reason, and
the cockpit's `applyModelMixEvent` already advances `lastSeq` for any
well-formed event and ignores unknown types — so no replay, persistence, SSE,
or frontend work was required. The pre-existing `ModeratorOutputLimits`
(token-shaped preview dataclass with an "unsupported hard cap → ValueError"
contract) is deliberately untouched; enforcement uses module constants.

Coverage: 13 new tests in `backend/tests/test_modelmix_guardrails.py` using
the Mission 013 small-threshold monkeypatch pattern (40/80 chars), one per
acceptance criterion: exact one-shot warning payload (criterion 1); zero
warnings below threshold (2); exact-cap truncation asserting the literal
character count (3); terminal `seat_completed` with `modelmix_output_cap`, no
`seat_failed` (4); unchanged under-threshold behavior (5); full Moderator
equivalence — warning, cap, ordering, finish reason (6); warning-then-cap
ordering with the cap event terminal (7); timeout-before-threshold →
`seat_failed` `reason: "timeout"` and no guardrail events (8);
cancel-before-threshold → `seat_cancelled` and no guardrail events (9);
non-streaming over-cap exact truncation plus under-cap unaffected, no warning
(10). Validation: full backend suite **373 passed** (360 pre-existing + 13
new; no existing test modified); frontend unchanged with `npm test` **86
passed**, `npm run lint` clean, `npm run build` green (437 modules). Advances
Punch Board item **17**: the hard output cap, the output warning, and the
distinct `modelmix_output_cap` terminal outcome are no longer open; remaining
item-17 openings are the configurable thresholds and the provider/account
usage warning (deferred as not honestly buildable — no authority-quota data
exists to compare against). The provisional thresholds themselves are a noted
follow-up for a settings/configurability mission.

## Mission 020 Result

Mission 020 advances Punch Board item **17** one level deeper: both guardrail
thresholds are now configurable per request through
`POST /api/modelmix/runs/stream`. `TwoWorkerRequest` gains optional
`warning_threshold_chars`/`hard_cap_chars` (`Field(default=None, gt=0)`), and
`stream_two_workers` resolves both to enforced values through a private
`routes._resolve_guardrail_overrides`, which defaults an omitted field to the
Mission 019 module constant, rejects values outside the new
`guardrails.MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`
range, and rejects `hard_cap_chars < warning_threshold_chars`. Every rejection
is a 422 raised **before** `run_registry.start(...)`, so no provider is ever
resolved or called on an invalid request.

The override rides the exact existing `seat_timeout` call chain — no parallel
path: `RunRegistry.start → _run → _run_phase` thread the two optional params
into both `multiplex_workers(...)` and `run_moderator(...)`, and each resolves
them exactly like `seat_timeout` into a `warning_limit`/`cap` used by the
existing `clip_delta` and one-shot warning check. Mission 019's enforcement
logic, event payloads, and `modelmix_output_cap` finish reason are unchanged —
only where the two threshold numbers come from.

Boundaries: frontend zero changes (when the request omits both fields the run
is byte-for-byte identical to Mission 019), `clip_delta` untouched,
`seat_timeout`/`run_timeout` untouched, `ModeratorOutputLimits` untouched, no
server-side persistence of a chosen threshold, no new dependencies. Coverage:
13 new tests in `backend/tests/test_modelmix_guardrails.py` mapping to all nine
acceptance criteria, including route-level tests over the full
routes → registry → run-phase chain (via FastAPI `TestClient`) and one
registry-level test proving `_run_phase` delivers the override to both worker
seats and the Moderator. Validation: full backend suite **388 passed** (375
prior + 13 new; no existing test modified), targeted suites **65 passed**,
`ruff check` clean on all six changed Python files, and frontend unchanged with
`npm test` **86 passed**, `npm run build` green (437 modules), `npm run lint`
clean.

## Mission 022 Result

Mission 022 proves the backend-provable half of the Punch Board item-33 alpha
acceptance checklist as integration tests through the real HTTP surface, in
one new file `backend/tests/test_modelmix_alpha_acceptance.py` (7 tests; 395
backend total = 388 prior + 7 new; no production file, no existing test file,
and no dependency modified). The file reuses the canonical sync TestClient
route pattern for everything except the cancel scenario, which needs two
in-flight requests on one loop and uses `httpx.AsyncClient(ASGITransport)`
on the existing single-loop pattern from `test_modelmix_journal.py`.

Coverage in item-33 terms: items 4 (stream both workers) and 5 (stream
Moderator) via scenario 1 (ordered single-feed SSE, contiguous seqs, full
persisted history); item 6 (cancel) via scenario 2 — exactly one
`run_cancel_requested` after all deltas, terminal `run_cancelled`, no
post-cancel deltas, persisted `cancelled`, both providers terminated; item 7
(worker failure) via scenario 3 — run ends `partial`, the failed worker's
partial output stays persisted, the Moderator handoff receives only the honest
`Unavailable because the worker failed.` line and never the failed worker's
deltas; item 8 (reopen) via scenario 4 — a fresh registry rehydrates the full
7-message transcript from the same persisted dir; item 9 (multi-turn) via
scenario 5 — real second POST, exact per-seat turn histories with no
cross-worker leakage; item 10 (honest telemetry) via scenario 6 — exact
provider `usage`, `finish_reason`, and real `started_at`/`completed_at` floats
on reopen; item 11 (no credential leak) via scenario 7 — a fake key pre-sent
by the provider is byte-absent from the stream, the journal, and the persisted
session document. Items 1–3 are UI-bound and remain covered by prior-mission
evidence (Mission 014 launch reachability, Mission 016 three panels, Missions
007/016 configure A/B/Moderator).

One genuine robustness gap was discovered during the cancel verification and
is disclosed rather than patched (verify-only rules): issuing the cancel
inside a sub-millisecond window right after a seat delta can leave the run
stuck `active` until the 600s run timeout, with `_run_phase` blocked in the
`multiplex_workers` generator-`finally` gather and the seat's provider
generator never receiving its `CancelledError`. With the natural client rhythm
used by the submission's scenario 2 — cancellation fired ~10ms after output is
visible — the cancel completes cleanly (10/10 consecutive runs observed). The
existing sync TestClient cancel test still passes. Follow-up is recommended in
the `_run_phase`/`aiter_with_deadline` cancellation hand-off.

Validation actually run and observed: `uv run pytest
backend/tests/test_modelmix_alpha_acceptance.py -v` → **7 passed in 1.80s**;
the cancel test repeated 10× → **10 passed**; full `uv run pytest backend/tests
-q` → **395 passed in 16.64s**; frontend baseline re-asserted with `npm test`
→ **118 passed (12 files)**, `npm run build` → green (438 modules, 2.87s),
`npm run lint` → clean; pre-commit `git status --short` showed only the new
test file untracked.

## Mission 023 Result

Mission 023 closes the cancel-path race Mission 022 disclosed, on base `main
@ b82505d` (verified full backend 395 passed before touching code). The root
cause was confirmed: `multiplex_workers`' generator `finally` did an unbounded
`await asyncio.gather(*tasks.values(), return_exceptions=True)`; under Python
3.10.20 `asyncio.wait_for`'s cancellation path awaits the inner awaitable's
actual completion (`_cancel_and_wait`), so a seat task whose provider generator
absorbs `CancelledError` and holds keeps that gather (and the unwinding
`CancelledError` that `_run`'s `run_cancelled` handler needs) blocked until the
600s run-timeout force-marked the run failed — the run stayed `active` with
`run.task` parked at `_run`'s `wait_for`.

Fix, all at the cleanup layer (not inside `aiter_with_deadline`, which was
left untouched by design):
- `backend/modelmix/timeouts.py` adds `CANCEL_GRACE_SECONDS = 5.0` and
  `await_cancellation_grace(tasks)` (`asyncio.wait(..., timeout=...)` over the
  pending tasks; never force-kills beyond `.cancel()`, abandons strays after
  the bound).
- `backend/modelmix/orchestrator.py` `multiplex_workers` `finally` now cancels
  every pending seat task then awaits `await_cancellation_grace(tasks.values())`
  — if the tasks finish within grace the behavior is unchanged, otherwise the
  cleanup gives up after 5s and the run's cancellation unwinds to
  `run_cancelled`.
- `backend/modelmix/registry.py` awaits the moderator task through
  `asyncio.shield(...)` inside the existing try/except: the shield's outer
  future completes immediately on cancellation, so `_run_phase` is woken
  promptly and the existing explicit `moderator_task.cancel()` +
  `await_cancellation_grace((moderator_task,))` + `raise` path runs. The direct
  `await moderator_task` variant was proven to hang **forever** (a task dump
  showed `_run_phase` still parked there 20s after cancel with `_must_cancel`
  unset on both tasks, because `Task.cancel()` only injects `CancelledError`
  after the awaited task — which had absorbed the cancel — completes).

Deterministic proof, new `backend/tests/test_modelmix_cancel_race.py` (8
tests): a `StallOnCancelProvider` fake emits one delta then absorbs
cancellation and holds on a gate, constructing the failure condition directly
instead of racing timing; the terminal contract is asserted structurally —
stall provider's `stream_finished` marker unset at the moment of terminal
`run_cancelled`, `reason is None`, no `run_failed`/`run_completed`, no
`"timeout"` in the serialized journal, `status == "cancelled"` — with
wall-clock upper bounds as a secondary guard and prompt-cancel regressions
asserting the old fast path is byte-for-byte unchanged. Both historical hang
sources found while developing (a `while True` re-hang in an earlier fake and
a leaked pending task in the grace-helper test) were test-harness bugs now
fixed; the final file runs clean in 11.98s.

Validation observed: new file **8 passed in 11.98s**; targeted acceptance
subset (alpha + streaming + timeouts + journal + moderator + cancel) → **57
passed in 16.54s**; full `uv run pytest backend/tests -q` → **403 passed in
27.94s** (395 prior + 8 new, no existing test modified); frontend unchanged,
re-asserted `npm test` → **118 passed (12 files)**, `npm run build` → green
(1.70s), `npm run lint` → clean. The alpha gate is **not** declared met here;
the next verification pass owns that declaration.

## Mission 024 Result

Mission 024 closes the synthetic edge case where a run cancelled before
`_run`'s first `await` stays `"created"` forever instead of reaching terminal
`"cancelled"` with a `run_cancelled` event. The root cause was confirmed
empirically against CPython 3.10.20: `coro.throw(CancelledError)` on a
never-started coroutine skips the coroutine body entirely — no `try/except`
inside `_run` catches it.

Fix: `await asyncio.sleep(0)` added after `asyncio.create_task(...)` in
`RunRegistry.start()` so `_run` reliably enters its `try` block and suspends at
a real `await` before `start()` returns. Additionally, `await
run.mark_status("active")` moved inside the `try:` block in `_run` so the
except handler covers the earliest cancel point after body entry. Both changes
are needed: `sleep(0)` guarantees the body is entered; `mark_status` inside
`try` ensures the handler covers the first await.

Deterministic proof: new test `test_cancel_before_run_starts_reaches_terminal_cancelled`
in `backend/tests/test_modelmix_cancel_race.py` — creates a run, immediately
cancels the task, uses `asyncio.wait` (not `wait_for`, which re-cancels the
task) and asserts `run.status == "cancelled"` + last event `"run_cancelled"`.

Validation observed: new test **1 passed in 0.82s**; full `uv run pytest
backend/tests -q` → **404 passed in 27.16s** (403 prior + 1 new, no existing
test modified); `ruff check` clean on both changed Python files. The alpha gate
is **not** declared here; the next verification pass owns that declaration.

## Mission 025 Result

Mission 025 hardens the local backend boundary so endpoints that
read/write/use stored credentials or make a server outbound request with a
client-influenced target/credential require admin auth. `_require_admin` is
reused exactly as-is; its token branch is identical to the one already proven
by the existing export test.

Implementation: `dependencies=[Depends(_require_admin)]` added to 20 endpoint
decorators in `backend/main.py`:

- Required (16): `PUT /api/settings`, `POST /api/settings/credential-storage`,
  `POST /api/oauth/{provider_id}/start`, `GET /api/oauth/{provider_id}/status`,
  `DELETE /api/oauth/{provider_id}`,
  `GET /api/credentials/import/relay-ai/discover`,
  `POST /api/credentials/import/relay-ai`, and the nine
  `POST /api/settings/test-*` endpoints.
- Judgment extensions (4): `GET /api/models`, `GET /api/models/direct`,
  `GET /api/ollama/tags`, `GET /api/custom-endpoint/models` — server outbound
  requests whose target/key derives from stored or client-influenced state.

Not guarded (verified): `GET /api/settings` (booleans only, no credential
values), `GET /api/settings/defaults` (static), `PUT
/api/settings/relay-ai-import-dismissed` (UI flag).

Security impact: the previously-confirmed `test-custom-endpoint` blind
SSRF-to-stored-key path (forwards client `url` to
`CustomOpenAIProvider.validate_connection`, omitted `api_key` falls back to the
stored credential via `resolve_api_key`) is now rejected 401/403 **before** any
outbound call; the test spies on `validate_connection` and asserts it is never
awaited for a rejected request.

Deferred/report-only findings: `_dev_cors_regex` matches any dotted-IPv4 origin
(not just private/loopback ranges); a loopback-local attacker could still point
the custom-endpoint URL at an internal host (suggest URL allow-listing in a
follow-up). `resolve_api_key`, the credential store, and CORS regex are
intentionally untouched per scope.

Validation observed: new `test_admin_guard_credential_endpoints.py` passes;
targeted `-k "admin or credential or settings"` → **71 passed**; full `uv run
pytest backend/tests -q` → **431 passed** (404 prior + 27 new); `ruff check
backend` clean; frontend re-asserted **118 passed**, build green (1.56s), lint
clean. The alpha gate is **not** declared here; the next verification pass owns
that declaration.

## Mission 026 Result

Mission 026 advances Punch Board item 30 (current-model half) by giving
`data/credentials.json` **real** per-user access-control hardening on Windows,
scoped to `backend/credentials/file_backend.py` only. The confirmed gap:
`os.chmod(CREDENTIALS_FILE, 0o600)` is a no-op for per-user-account ACL
enforcement on Windows.

Implementation:
- `_harden_credentials_file()` runs, after the unchanged Unix `chmod`, the
  `icacls "<path>" /inheritance:r /grant:r "<current-user>":F` command via
  `subprocess` (no `pywin32`), gated entirely behind
  `sys.platform == "win32"`.
- `_resolve_windows_current_user()` resolves the grant principal from
  `USERNAME`/`USERDOMAIN` env vars (preferred: reliable for a logged-in session
  and a user-run service), falling back to `os.getlogin()`.
- Fail-safe: icacls unavailability / exceptions / non-zero exit are logged as
  a warning and never raise, so a credential write always succeeds — mirroring
  the existing `except OSError: pass` philosophy but logging the failure.
- `_warn_if_unhardened()` logs once per process (module `_startup_warned`
  flag) when running on Windows and the credentials file exists and was not
  successfully hardened this session, surfacing pre-existing plaintext files.

Declared boundary (not an oversight): `credential_storage`'s default `file`
mode and `get_effective_mode()` are product decisions, unchanged here.
Credential values are never modified; `keyring_backend.py`, `store.py` facade,
and `main.py` routes untouched.

Validation observed:
- `uv run pytest backend/tests/test_credentials_store.py
  backend/tests/test_credentials_keyring.py
  backend/tests/test_credentials_availability.py
  backend/tests/test_admin_guard_credential_endpoints.py -v` → **41 passed**
  (all unmodified).
- New `test_credentials_file_hardening.py`: **7 passed** (acceptance criteria
  1–6).
- Full `uv run pytest backend/tests -q` → **438 passed in 27.76s** (431 prior
  + 7 new, no existing test modified).
- `uv run ruff check backend` → All checks passed.
- Frontend re-asserted: **118 passed**, build green (1.57s), lint clean.

Follow-up required: a **separate, later re-verification of credential storage
is needed once Tauri 2 packaging (Punch Board item 34) actually exists**, since
Tauri's own storage/IPC model may behave differently and cannot be assumed to
inherit this mission's guarantees. The alpha gate is **not** declared here; the
next verification pass owns that declaration.

## Mission 027 Result

Mission 027 closes the remaining current-model gap on Punch Board item 30:
Mission 026 only hardened a credentials file when a credential was WRITTEN and
only logged a warning for a pre-existing unhardened file. A machine that only
ever reads credentials (no new key written) kept its pre-existing file
unhardened indefinitely.

Fix, scoped to `_warn_if_unhardened()` in `backend/credentials/file_backend.py`
(`_harden_credentials_file()` reused exactly, unchanged): on the first touch
(read or write) of an existing, not-yet-hardened Windows file, it now attempts
`_harden_credentials_file()` directly, then logs INFO "Restricted %s to the
current user account." on success or the existing "not restricted" warning on
failure. The `_startup_warned` once-per-process guard makes this a single,
automatic, one-time remediation. Never raises; a failed attempt logs and
continues. Non-Windows behavior is unchanged.

Test reconciliation: `test_credentials_file_hardening.py` grows from 7 to 10
tests. One Mission 026 test (`test_startup_warning_fires_once_on_existing_unhardened_file`)
was necessarily reconciled because Mission 027's remediation-on-read directly
contradicts its old "reads never invoke icacls / always warn" assertions; it is
split into a success case (one icacls, INFO, no warning) and a failure case
(one icacls, one "not restricted" warning). All other Mission 026 tests pass
unmodified — flagged explicitly since criterion 6 ("unmodified") and acceptance
criterion 1 ("first get_secret invokes icacls") are mutually exclusive.

Validation observed:
- `uv run pytest backend/tests/test_credentials_file_hardening.py -v` → **10
  passed**.
- Full `uv run pytest backend/tests -q` → **441 passed in 28.55s** (438 prior +
  3 net new).
- `uv run ruff check backend/credentials/file_backend.py
  backend/tests/test_credentials_file_hardening.py` → All checks passed.
- Frontend re-asserted: **118 passed**, build green (1.84s), lint clean.

Punch Board item 30's current-model half is now closeable (both newly-written
and pre-existing files are user-restricted on Windows; Unix 0o600 unchanged).
The Tauri-specific re-verification is carried forward exactly as Mission 026
stated it: a SEPARATE, later check is required once Tauri 2 packaging (item 34)
exists, since Tauri's storage/IPC model cannot be assumed to inherit these
guarantees. The alpha gate is **not** declared here; the next verification pass
owns that declaration.

## Mission 028 Result

Mission 028 verifies and hardens the existing Compare (no-moderator) backend
path — Punch Board item 28's backend verification half. Before writing any new
Compare orchestration code, it determines whether the already-shipped,
completely-unexercised capability (optional `moderator_model`;
`registry._run_phase` / `orchestrator.multiplex_workers` already supporting a
two-worker run with no moderator phase) is actually correct. It was: **no real
defect was found**, and the path now has real evidence-backed coverage.

New `backend/tests/test_modelmix_compare_mode_backend.py` (7 tests), all driven
through the REAL HTTP route (`POST /api/modelmix/runs/stream` with
`moderator_model` omitted) using the alpha-acceptance harness, one test per
investigation point:
1. both workers stream fully with ZERO moderator events of any kind, then
   `run_completed "completed"`, contiguous `1..N` sequence;
2. one worker fails -> `run_completed "partial"`, and `GET /sessions/{id}`
   reflects worker_a `failed` + worker_b `completed`, no moderator message;
3. both workers fail -> OBSERVED as-shipped `run_completed "partial"` (not
   `failed`). This differs from the moderator path (which yields `failed`).
   Reported as a product-semantics observation, not a defect; changing it is
   product work outside this verify mission's scope;
4. multi-turn isolation holds moderator-less; the dead
   `seat_histories["moderator"]` key (always built, never run) is never
   forwarded to either worker (poison-sentinel never reaches a payload);
5. per-worker guardrails still apply (warning + hard cap respected
   independently for each worker, `modelmix_output_cap` finish_reason);
6. cancellation mid-stream reaches terminal `run_cancelled`, no post-cancel
   deltas, both providers cancelled;
7. reopening a moderator-less session reconstructs with no moderator message at
   all; `models["moderator"]` persists as `None` and `_validate` tolerates it;
   nothing downstream assumes a moderator message exists.

No production code was changed; no `mode` concept added; no frontend change.
The only test failures during development were bugs in my own test assertions,
fixed in the test file.

Validation observed:
- `uv run pytest backend/tests/test_modelmix_alpha_acceptance.py -v` → **7
  passed in 1.81s** (moderator-full path undisturbed).
- `uv run pytest backend/tests/test_modelmix_compare_mode_backend.py -v` →
  **7 passed in 1.61s**.
- Full `uv run pytest backend/tests -q` → **448 passed in 28.58s** (441 prior +
  7 net new).
- `uv run ruff check backend` → All checks passed.
- Frontend (`cd frontend && npm test && npm run build && npm run lint`): **118
  passed**, build green (1.61s), lint clean.

Punch Board item 28's backend verification half was complete after Mission 028;
Mission 029 delivered the rest and closed item 28.

## Mission 029 Result

Mission 029 delivers the frontend Compare mode and a no-moderator status fix,
closing Punch Board item 28 (Compare).

**Part 1 — Backend status fix.** In the no-moderator path, when **both** workers
fail, `multiplex_workers` now reaches `run_completed` with `status="failed"`
instead of `"partial"` — a run with no surviving output should not present as a
mere partial completion. Implementation: `failed: bool` → `failed_seats: set`,
with the terminal status computed as `"failed" if failed_seats and
len(failed_seats) == len(tasks) else "partial" if failed_seats else
"completed"`. The moderator path (`emit_run_completed=False`) is untouched; a
`run_completed` is still only emitted for the no-moderator case. The Mission 028
point-3 test was renamed to `test_no_moderator_both_workers_fail_reaches_run_completed_failed`
and now asserts `status="failed"`.

**Part 2 — Frontend Compare mode.** The inert top-bar `Mode: Mix` `<span>` is
replaced by a real `select.modelmix-mode-select` with options Mix / Compare,
persisted to `localStorage["modelmix.mode"]` through the new pure module
`modelmixMode.js` (`loadSavedMode` / `saveMode`; valid values only `mix` /
`compare`; default `mix`; **no** `solo` anywhere). Behavior in Compare mode:
the composer's Moderator selector is not rendered; `moderator_model` is omitted
from the request body entirely; the center moderator panel is hidden-but-kept-
mounted using the existing `modelmix-panel-hidden` seam; the models strip uses a
2-column grid (`.modelmix-models--compare`). The mode control disables during an
active run through the existing `modelSelectorsDisabled`/`controlState` helpers.

Validation observed:
- `uv run pytest backend/tests/test_modelmix_compare_mode_backend.py
  backend/tests/test_modelmix_moderator.py -v` → **18 passed** (7 compare + 11
  moderator; moderator path undisturbed by the status fix).
- Full `uv run pytest backend/tests -q` → **448 passed** (unchanged total: the
  compare test was renamed, not added).
- `uv run ruff check backend/modelmix/orchestrator.py
  backend/tests/test_modelmix_compare_mode_backend.py` → All checks passed.
- Frontend (`cd frontend && npm test && npm run build && npm run lint`): **130
  passed** (118 prior + 6 `modelmixMode.test.js` + 6
  `ModelMixSendCompare.test.jsx`), build green, lint clean.

One existing frontend test was modified: the top-bar test now asserts the real
`select.modelmix-mode-select` (options `['Mix','Compare']`, default
`value === 'mix'`, present `#modelmix-moderator-model`) instead of the old inert
span. The mode control needed to be a real control, so the span-based assertion
could not survive as-is. This is the sole modified existing test; every other
existing test passes unchanged. Punch Board item 28 (Compare) is now CLOSED.

## Mission 030 Result

Mission 030 delivers the backend half of Punch Board item 27 (Solo): it makes
`worker_b_model` optional end to end so a run can consist of Worker A alone. The
frontend Solo surface is intentionally out of scope for this mission, leaving
item 27 partially open.

**Routes.** `TwoWorkerRequest.worker_b_model` is `Optional[str] =
Field(default=None, min_length=1)`. The route rejects the worker_b-absent +
moderator hybrid with `422` **before** any provider resolver call (boundary:
"Solo is exactly one participant, full stop"; no moderator-with-one-worker hybrid
mode).

**Registry.** `worker_b_model: Optional[str]` threads through
`RunRegistry.start` / `_run` / `_run_phase`. It is kept as a positional-None
parameter (not a keyword default) so the required `provider_resolver` order is
preserved across the existing call sites without a broad signature reorder.
`start` builds only a `worker_a` + `moderator` seat history and adds `worker_b`
only when configured; the persisted `models` for a Solo run is
`{"worker_a", "moderator": None}` (the `worker_b` key is absent); the existing
Compare shape (`{"worker_a", "worker_b", "moderator": None}`) is unchanged.
`_run_phase` forwards only the active worker seat histories downstream and adds
a defensive no-hybrid guard so the moderator phase only runs when BOTH
`moderator_model` and `worker_b_model` are present.

**Orchestrator.** `multiplex_workers` now accepts `worker_b_model: Optional[str]`
and computes active seats locally (`models` starts `{"worker_a"}`, gains
`worker_b` only when configured). The now-unused `SEATS` module constant was
removed.

**Persistence.** `_validate` replaces the exact three-key set-equality guard
with: `models` keys a subset of `{worker_a, worker_b, moderator}`; `worker_a`
always present non-empty; then the existing per-key loop (any present
non-moderator key must be a non-empty string; `moderator` may be non-empty or
`None`). Mix / Compare / old three-key shapes still validate; genuinely malformed
shapes (missing or empty `worker_a`, `worker_b: None`, unknown keys, empty or
non-string `moderator`) are still rejected — proven by new validator tests.

**No `history.py` change.** A Solo turn produces no worker_b message, so a later
Mix turn's `build_seat_history("worker_b")` correctly skips the Solo turn
(verified by the solo-then-mix isolation test; not patched).

Validation observed:
- New `backend/tests/test_modelmix_solo_mode.py` → **7 passed** (solo streams
  Worker A only and completes; solo failure reaches `run_completed "failed"`;
  requests with no worker_b default to Solo; the hybrid is 422-rejected with the
  resolver never called; solo-then-mix multi-turn isolation holds with worker_b
  never seeing Worker A's Solo output; per-worker guardrails apply to the Solo
  worker; cancellation reaches `run_cancelled` mid-stream).
- New persistence validator tests in `test_modelmix_persistence.py` (Mix /
  Compare / Solo shapes accepted; missing/empty `worker_a`, `worker_b: None`,
  unknown keys, non-string/empty `moderator` rejected; Solo shape survives
  load-from-disk; Mix/Compare/Solo all load).
- Targeted `uv run pytest` on persistence/streaming/moderator/compare/
  acceptance/solo files → **63 passed**.
- Full `uv run pytest backend/tests -q` → **460 passed** (up from 448).
- `uv run ruff check backend/modelmix backend/tests` → All checks passed. (The
  repo-wide `ruff format --check` state is pre-existing and left untouched per
  the no-reformat unrelated code rule.)
- Frontend (`cd frontend && npm test && npm run build && npm run lint`) → **130
  passed**, build green, lint clean.

Files: `backend/modelmix/routes.py`, `backend/modelmix/registry.py`,
`backend/modelmix/orchestrator.py`, `backend/modelmix/persistence.py`,
`backend/tests/test_modelmix_persistence.py` (validator tests),
`backend/tests/test_modelmix_solo_mode.py` (new, 7 tests).

Assumption that materially affected implementation: `worker_b_model` is typed
`Optional[str]` and threaded as a positional-None (route passes `None` for Solo)
rather than given a `= None` keyword default, because a default before the
required `provider_resolver`/`moderator_model` position would force a broad
signature reorder across many existing call sites. Functionally equivalent for
the route-driven Solo path.

## Mission 031 Result

Mission 031 delivers the frontend half of Solo and closes Punch Board item 27.
The persisted mode vocabulary and control now contain Mix / Compare / Solo. In
Solo, only Worker A's model selector is rendered and required; requests omit
both `worker_b_model` and `moderator_model` as keys. Moderator and Worker B
panels remain mounted but use the existing CSS-hidden mechanism, while Worker A
fills the cockpit through the established single-column visual class.

Mode visibility is composed with, but does not overwrite, local panel-view
state. In Solo, a maximize target on a hidden seat is visually neutralized so
the cockpit remains usable; leaving Solo restores the independent panel-view
effect. No reducer, persistence/event helper, backend file, CSS file,
dependency, or lockfile changed.

New `ModelMixSendSolo.test.jsx` contributes 8 tests. Solo validity/persistence
coverage was added to `modelmixMode.test.js`; the only modified pre-existing
frontend test is the necessary top-bar option-list expectation. Observed
validation: frontend **138 passed** / build green / lint clean. The exact
backend command reproduced the known default-temp `WinError 5` (**246 passed,
214 setup errors**); a workspace-temp rerun completed with **460 passed in
35.32s**. Items 27 (Solo) and 28 (Compare) are complete end to end, and the
mode-control remainder of item 24 is complete.

## Mission 032 Result

Mission 032 begins Punch Board item 34 with the smallest verified desktop
slice. The Windows host had Rust/Cargo 1.98.0, the MSVC C++ build tools, and
WebView2 Runtime 151.0.4129.107. `cargo tauri` was initially absent and was
installed as `tauri-cli 2.11.4` after approval.

The new standard `src-tauri/` shell reuses the existing Vite app through
`devUrl: http://localhost:5173/modelmix` and `frontendDist:
../frontend/dist`; its hooks are `npm run dev` and `npm run build`. There is no
sidecar, external binary, backend-launch command, backend/CORS change, or
`frontend/src` change.

Observed runtime evidence: a separately started backend returned HTTP 200 from
its health endpoint; corrected `cargo tauri dev` reached Vite ready, completed
the Rust build, and ran `target\debug\app.exe`; direct Windows inspection found
exactly one native `ModelMix` window and showed the actual Worker A / wider
Moderator / Worker B cockpit, prompt and model controls, separate Send/Stop,
Ready state, and honest no-configured-models message. `cargo check` passed;
frontend **138 passed** / build / lint green; backend workspace-temp rerun
**460 passed in 38.91s** after the exact command reproduced the known
default-temp `WinError 5` (**246 passed, 214 setup errors**).

Item 34 remains **IN PROGRESS**. Python sidecar packaging/lifecycle, a real
installer build, and Tauri-specific credential-storage re-verification remain
separate later work.

## Mission 033 Result

Mission 033 proves the standalone backend-bundling half of Punch Board item
34. PyInstaller 6.22.2 with hooks-contrib 2026.7 produced a Windows `onedir`
bundle through a durable spec and a packaging-only adapter that executes
`backend.main` with package context. The installed keyring hook was directly
verified to collect `keyring.backends` and copy keyring metadata. The initial
spec's `SPECPATH` resolution failed before analysis and was corrected to the
observed spec-directory behavior; the first frozen launch then disclosed the
missing project-metadata fallback, fixed narrowly by bundling only
`pyproject.toml`.

The corrected copied executable ran on `127.0.0.1:8133` with system-only
`PATH` and empty Python/uv/venv variables, loaded its Python DLLs from its own
bundle, and had no Python/uv/venv child. Real health, empty-session, redacted
settings, and MCP SSE responses were retained. Two fixed fake sentinels were
used: the keyring sentinel survived restart and was cleared; the isolated
file sentinel survived restart, the generated credential file had a direct
non-inherited `MSI\wpedigo` FullControl ACL, and it was cleared. The isolated
credential file and runtime were deleted afterward; repository `data/` hashes
were unchanged.

Observed validation: the exact backend command reproduced the known Windows
default-temp `WinError 5` (**247 passed, 214 errors**), then the unchanged suite
passed **461 tests in 30.69s** with worktree-local `TEMP`/`TMP` and
`--basetemp`; frontend **138 passed** / production build / lint green; Cargo
format and check passed; focused Ruff passed. The final bundle measured
12,629,354 bytes for the executable and 122,797,389 bytes total.

Item 34 remains **IN PROGRESS**. This mission did not add Tauri `externalBin`,
Rust sidecar spawning/lifecycle, a production installer, or final credential
packaging in the delivered Tauri application.

## Mission 034 Result

Mission 034 fixes the frozen-path finding confirmed in Mission 033's evidence
(`_internal\data\credentials.json`). A new, stdlib-only
`backend/user_data_dir.py` provides `is_frozen()` (PyInstaller's standard
`getattr(sys, "frozen", False)`) and `resolve_user_data_dir()`: when not
frozen it returns the repository `data/` directory computed from the new
module's own location with the same arithmetic the three files already used,
so dev-mode behavior is byte-for-byte unchanged; when frozen it returns
`%LOCALAPPDATA%\ModelMix`, falling back to the running executable's
directory with a warning if `LOCALAPPDATA` is absent, and creates the
resolved directory before returning. `CREDENTIALS_FILE`, `SETTINGS_FILE`,
and `personas._DATA_DIR` (plus its `persona_overrides.json` subpath) now
derive from the shared helper. The `icacls` hardening logic, keyring backend,
store facade, routes, `src-tauri/`, and `frontend/` were untouched; no new
dependencies.

Observed validation: the exact credential-command and full-suite commands
reproduced the known Windows default-temp `WinError 5` (`2 passed, 22
errors` and `252 passed, 216 errors` respectively); with the documented
`--basetemp` workaround the full suite passed **468 tests in 30.51s** (461
pre-existing tests unmodified + 7 new), the focused four-file credential run
passed all **24**, and `ruff check backend` reported **All checks passed!**.
Frontend commands ran as required (nothing frontend changed): **138 passed** /
production build / lint clean. A live dev-mode inspection showed
`frozen: False` with all constants resolving under
`C:\Users\wpedi\ModelMix\data`.

The frozen-mode path is proven by simulation (monkeypatched `sys.frozen`,
`LOCALAPPDATA`, and `sys.executable`), not by a real frozen build. Whether
a real PyInstaller run actually lands persisted files in
`%LOCALAPPDATA%\ModelMix` still needs the same hands-on proof Mission 033
required and stays with item 34. Dev-mode `data/` behavior and every
pre-existing test are unchanged.

## Mission 035 Result

Mission 035 wired the frozen backend into the Tauri 2 app as an app-spawned
process and closed item 34. Decisions: `bundle.resources` recursive copy of
`dist/modelmix-backend/` (externalBin/sidecar cannot carry the onedir
`_internal/` directory), Rust `std::process::Command` spawn with
`CREATE_NO_WINDOW` (no shell-plugin capability needed), and a Win32 Job
Object (`KILL_ON_JOB_CLOSE`) plus `RunEvent::Exit` teardown for zero orphans.

Observed behavior (all runs on this box):

- Dev (`cargo tauri dev`, invoked from repo root): app spawned the bundle —
  no manual Python. Cold readiness 4.57 s (first) / 10.17 s (post-fix
  resource copy). WebView2 held an established connection to
  `127.0.0.1:8001`. Graceful close → 0 orphaned `modelmix-backend`, port free.
- Production (`cargo tauri build --bundles nsis`, silent install, ran the
  installed exe): packaged app spawned the bundled backend from
  `<install>/_up_/dist/modelmix-backend/` — ready in 2.03 s; window
  `ModelMix` responding; `Origin: https://tauri.localhost` accepted
  (Access-Control-Allow-Origin returned, `Vary: Origin`) via the backend's
  documented `FRONTEND_HOST` env supplied at spawn. Health verified.
- Zero orphans on graceful close AND on force-kill (`taskkill /F`) in the
  NSIS install.
- Broken-backend states: spawn failure and 30 s readiness timeout each show
  a native error dialog and exit cleanly; main window stays gated.

Validation observed: backend `468 passed` (32.0 s), frontend `138 passed` /
lint clean / build ok, `cargo clippy --all-targets` clean. Full evidence:
`docs/modelmix/035-tauri-sidecar-wiring.md`.

Remaining open items on the packaged app (out of scope, per mission): MSI
bundle, code-signing/installer polish, CSP hardening (`csp` still `null`),
dynamic port discovery, and a real frozen-build local-appdata credential
proof.

## Mission 036 Result

Documentation-only accuracy pass (no code changed). Punch Board item 30
(verify credential storage in the actual packaging model) closed against
completed evidence: Missions 026/027 (real `icacls` ACL hardening + once-per-
process startup remediation) and 033/034 (real frozen-executable keyring
round-trip across a process restart with distinct PIDs, ACL proof, and the
frozen `%LOCALAPPDATA%\ModelMix` credential location). Item 31 (harden local
backend boundary) closed against Mission 025 (admin-auth guards on 20
endpoints closing the `test-custom-endpoint` SSRF→credential-exfiltration
vulnerability; 27-test guard suite + endpoint audit table), with the
deliberately-deferred `_dev_cors_regex` finding tracked as sub-item 31a (and
the custom-endpoint URL allow-list note as 31b). Item 34 relabeled to
"SUBSTANTIALLY COMPLETE" to stay explicitly open on MSI, code signing, CSP
hardening, and dynamic ports per Mission 035.

## Mission 037 Result

Open-source credits and dependency-license inventory (Punch Board item 4 closed
as SATISFIED with Mission 017). Three tool-generated inventory files, each from
real package metadata and committed as-is under `docs/modelmix/licenses/`:
`THIRD-PARTY-LICENSES-python.txt` (`uv run pip-licenses --order=name
--with-authors`, pip-licenses 5.5.5, against the project `.venv`),
`THIRD-PARTY-LICENSES-frontend.txt` (`npx.cmd --yes license-checker --start .`
against `frontend/node_modules`), and `THIRD-PARTY-LICENSES-rust.txt`
(`cargo license --color never`, cargo-license 0.7.0, against
`src-tauri/Cargo.lock`). `OPEN_SOURCE_CREDITS.md` added at the repo root with the
already-verified MIT/copyright (Mission 017), the text-only AI Counsel
attribution matching `README.md`, and all direct dependencies from the three
ecosystems with licenses quoted exactly from the machine inventories. The
cockpit About section gained one line linking to `OPEN_SOURCE_CREDITS.md` on the
real `github.com/wpedigo1/ModelMix` URL. Spot-checked licenses: frontend direct
deps all MIT (`react`, `react-markdown`, `vite`, `vitest`, `jsdom`, ...); Python
runtime differs per package (`fastapi` MIT, `uvicorn` BSD-3-Clause, `httpx` BSD
License, `yake` GPLv3, `python-multipart` Apache-2.0); Rust direct deps all
`Apache-2.0 OR MIT`. No `pyproject.toml`/`package.json`/`Cargo.toml` changes; no
runtime-or-permanent tool added to any manifest.

## Mission 038 Result

Removed the GPLv3 `yake` runtime dependency (finding of Mission 037) from
`pyproject.toml`, `uv.lock`, and all imports, replacing it with a stdlib-only
RAKE implementation in `backend/search.py` (`_RAKE_PHRASE_STOPWORDS` +
`_rake_extract_keywords`, implemented from the standard algorithm:
stopword-split spans, 1–3 word candidate n-grams, degree/frequency word
scoring, phrase score = sum, returned highest-score-first so the most central
phrase comes first — corrected post-push, after the initial version returned an
ascending list and the report/tests were updated accordingly, see
`038-remove-gplv3-yake-dependency.md` section 12). The public
`extract_search_keywords` contract, the `"yake"` config-mode token (kept across
`main.py`/`settings.py`/MCP tool/frontend for compatibility), and all existing
noise/role-play/dedup filters were preserved byte-for-byte; only comments,
docstrings, the `TOOLS.md`/`SKILL.md` mode descriptions, and the frontend
settings label ("Smart Keywords (RAKE)") changed. Regenerated
`THIRD-PARTY-LICENSES-python.txt` with the real `pip-licenses` command (yake
absent; only dev-only GPLv2 `pyinstaller`/`pyinstaller-hooks-contrib` remain);
removed the `yake` row from `OPEN_SOURCE_CREDITS.md` and corrected the note
(`pip-licenses` does not list itself). First test coverage for `search.py` added
(`backend/tests/test_search_keywords.py`, 8 tests incl. two semantic
subject-phrase regression tests added with the sort correction). Validation
observed:
search tests **8 passed**; full backend **476 passed** (474 at push + 2
semantic tests,
`--basetemp` override for the known Windows temp-dir issue); frontend **138
passed**, build green, lint clean; `rg` proves no `yake` in
`pyproject.toml`/`uv.lock`/backend imports. Quality is comparable to YAKE, not
identical (before/after table in the report, regenerated after the sort
correction). Closes the GPLv3 exposure from
Missions 033/037; Punch Board item 4 now cites Missions 017 + 037 + 038.

## Mission 039 Result

Deterministic query preprocessing. Fixed a pre-existing, confirmed
correctness bug in `backend/search.py::_preprocess_query`: it applied
sequential, interactive regex substitutions over plain-`set` iteration of
`ROLE_PLAY_TITLES` and `NOISE_PHRASES`, so the output depended on the
per-process `PYTHONHASHSEED` (verified ~3 of 13 seeds degraded, e.g. leaving
`current 2025` in a "tesla stock" query). Not introduced by Mission 038 — its
sort fix was correct; Mission 038's new tests were simply the first with
enough sensitivity to catch this much older bug. Fix: iterate both sets in a
fully reproducible order (`sorted(..., key=lambda s: (-len(s), s))` —
longest-first with alphabetical tiebreak, precomputed as module-level tuples),
which also lowers the interaction risk; `NOISE_WORDS` /
`CURRENT_EVENT_INDICATORS` were audited (membership-only, order-independent)
and deliberately left unchanged; regex patterns, set contents, and every other
function untouched. New cross-seed test spawns real
`PYTHONHASHSEED`-overridden subprocesses (seeds 0–12; a same-process test
cannot see this bug) and asserts identical `_preprocess_query` /
`extract_search_keywords` output plus exactly `"tesla stock"` for the
previously-flaky scenario ("Act as a financial analyst and evaluate the
current market in late 2025 for tesla stock"). Validation observed: raw
13-seed sweep over `test_search_keywords.py` = **9 passed under every seed
0–12** (pre-fix, seeds 5/11/12 failed); full backend **477 passed**; frontend
**138 passed**, build green, lint clean; `ruff check` clean. Maps to no Punch
Board item — recorded as a pre-existing correctness bug found and fixed via
Mission 038's own test coverage.

## Mission 040 Result

Durable structured logging (closes Punch Board item 32, "Add basic structured
observability"). Added a rotating-file console-preserving logging setup behind
a new `backend/logging_config.py::configure_logging()`, invoked once early in
`backend/main.py` (before the FastAPI app is built). Stdlib only; behavior is a
no-op second call. Key behavior: a `RotatingFileHandler` (5 MB maxBytes, 3
backups) writes `<user_data_dir>/logs/modelmix.log` with format
`%(asctime)s %(levelname)s %(name)s: %(message)s`; the console (stderr) handler
is preserved so `python -m backend.main` still prints; the effective level
comes from `LLM_COUNCIL_LOG_LEVEL` (default `INFO`, invalid values fall back to
`INFO`); the log file gets the same Windows per-user ACL hardening as the
credentials file. ACL hardening was de-duplicated: the `icacls` logic moved
verbatim into shared `user_data_dir.is_windows()`,
`user_data_dir.resolve_windows_current_user()`, and
`user_data_dir.harden_user_dir(path)`, and `file_backend._harden_credentials_file()`
now delegates to it (credentials behavior byte-for-byte unchanged; the existing
Mission 026/027 hardening tests were retargeted to the shared helper and all
pass). Credential-leak audit of all 89 `logger.*` call sites (17 files): no
message interpolates a credential value, API key, token, password, or request
body — matches are secret identifiers/keys, absence flags, URLs, status codes,
or provider error text (see report §3 for the case-by-case review). New
`backend/tests/test_logging_config.py` (8 tests) covers all six acceptance
criteria (rotation location/config, env-var level + invalid fallback, ACL
hardening path via mock — no real icacls, console-presence, structural
credential-leak audit, idempotency). Validation observed: full backend **485
passed** (477 baseline + 8 new), `ruff check backend` clean, and a live
`python -m backend.main` import booted the app and actually wrote a
structured-format `data/logs/modelmix.log` (dev mode) capturing first-party and
third-party (httpx/MCP) records. Flagged follow-up, NOT changed in this mission
(boundary): `src-tauri/src/lib.rs` discards backend stdout/stderr in packaged
builds, so a frozen build's logs exist on disk but are not tailed to the
terminal; `tauri_plugin_log` remains debug-gated there.

## Mission 041 Result

Dead code inventory via one-off tools (Punch Board item 46 — inventory phase
only; item stays OPEN). Ran `uvx vulture backend` (Python dead code),
`npx.depcheck` and `npx unimported` against `frontend/` (unused deps/files) —
all one-off, no permanent dependencies, no file-modifying tool. Categorized
every finding into confirmed-unreachable / false-positive / ambiguous with
independent whole-repo `git grep`-based confirmation for each. **Confirmed
unreachable (~263 lines across 12 backend symbols in 11 files plus one frontend
devDependency):** `config.py` legacy constants `OPENROUTER_API_KEY` /
`COUNCIL_MODELS` / `CHAIRMAN_MODEL` (superseded by the getter functions);
`settings.AVAILABLE_MODELS` hardcoded model list (live `/api/models` provides
data); `credentials/ids.py` `SECRET_ID_TO_SETTINGS_FIELD`, `OAUTH_CONNECTED_FLAGS`,
`api_secret_id`, `oauth_secret_id` (never imported/called); `store.py`
`secret_id_for_settings_field` (wrapper never called); `DocumentLimits
.document_timeout_seconds` (class attr never read); three dead
`query_models_parallel` wrappers in `council.py`/`ollama_client.py`/
`openrouter.py` plus `openrouter.fetch_models` (legacy pre-refactor free
functions, 105 lines — the single largest dead block); `search.py`
`_fetch_with_jina_sync`; `oauth/types.py` `parse_stored_oauth_credential`;
`keyring_backend.py` `_entry` stub; and the `@types/react-dom` devDependency
(project is 100% JSX with no tsconfig/TS source). **False positives (not to
touch):** all 43 FastAPI route handlers (`@app.*`/`@router.*` decorators vulture
can't see), all Pydantic/dataclass fields (`created_at`, `message_count`,
`avatar_emoji`, `OAuthStartResponse` fields, `RunEventJournal.created_at` — all
serialized via `model_dump()`), the intentional async-generator `yield` after
`raise` in `providers/base.py:52` (`# pragma: no cover`), and all 13 pytest
fixture/mock-attribute findings (pytest runtime injection). **Ambiguous:**
`@types/react` (unused by build but `react-select`'s peer dep — left alone).
Council/Advisor/debate code confirmed to be a live product, not a corpse.
Validation: `pytest backend/tests` **485 passed**, `npx unimported` clean,
`npx depcheck` flagged only `@types/react-dom`. Zero code files modified. Full
inventory and a follow-up removal checklist in `041-dead-code-inventory.md`.

## Mission 042 Result

Executed Mission 041's deferred removal (Punch Board item 46 — CLOSED). Every
confirmed-unreachable item was re-grepped across the whole repo at removal
time and confirmed dead (zero references beyond the definition site) before
deleting. Removed: `config.py` legacy constants `OPENROUTER_API_KEY` /
`COUNCIL_MODELS` / `CHAIRMAN_MODEL`; `settings.AVAILABLE_MODELS`; `credentials
/ids.py` `SECRET_ID_TO_SETTINGS_FIELD`, `OAUTH_CONNECTED_FLAGS`,
`api_secret_id`, `oauth_secret_id` (plus the now-orphaned `Optional` import);
`store.secret_id_for_settings_field`; `DocumentLimits
.document_timeout_seconds`; three dead `query_models_parallel` wrappers in
`council.py`/`ollama_client.py`/`openrouter.py`; `openrouter.fetch_models`;
`search._fetch_with_jina_sync`; `oauth/types.py`
`parse_stored_oauth_credential`; `keyring_backend._entry`; and the
`@types/react-dom` devDependency (lockfile updated, no other diff). Left
untouched per the hard boundary: all 43 FastAPI routes, Pydantic/dataclass
fields, the intentional async-generator `yield` in `providers/base.py`,
pytest fixtures, and ambiguous `@types/react`. New findings reported (not
removed — not on the list): `openrouter.BROKEN_MODELS` and
`search.get_sync_client` became orphaned as a consequence of the removals.
Validation: backend **485 passed** (via `--basetemp`; the literal
`uv run pytest backend/tests -q` currently fails at the corrupt
`pytest-of-wpedigo` system temp-dir ACL with a `PermissionError`, an
environmental issue unrelated to this mission), frontend **138 passed**,
`npm run build` clean, `npm run lint` clean. Commit
`chore(modelmix): remove confirmed dead code (Mission 042)`. Full report in
`042-remove-confirmed-dead-code.md`.

## Mission 043 Result

Foundational domain documentation (docs-only, **zero code changes**). Wrote
four code-sourced reference docs under `docs/modelmix/` claiming behavior **from
real code, not** from punch-board wording: `domain-objects.md` (Punch Board
item 7), `run-state-machine.md` (item 9), `provider-capability-matrix.md`
(item 12), and `privacy-and-data-routing.md` (item 13). The run doc documents
the actual terminal transitions (`completed`/`partial`/`failed`/`cancelled`,
plus `created`/`active`) with line citations, and explicitly corrects one piece
of stale punch-board vocabulary: the code value is `partial`
(`persistence.py:21`, `registry.py:314`), not `partially_completed`. The matrix
node-by-node confirms exactly one streaming provider (`openai-oauth`), that only
`openrouter` derives pricing, and which providers derive `is_free` honestly;
capabilities not implemented anywhere are explicitly marked absent. The privacy
doc covers the credential store backends, settings-API/credential-store
separation, single-flight OAuth refresh, seat-scoped history, and the bounded
visible-only Moderator fan-in. Items 7, 9, 12, and 13 are now **SATISFIED**
(`PUNCH-BOARD.md` updated; item 9 retains the `partial` vocabulary note).
Validation: backend **485 passed** (`--basetemp` workspace override for the
known corrupt system-temp ACL; the literal `uv run pytest backend/tests -q`
reproduces the same environmental `WinError 5` and is reported honestly),
frontend **138 passed**, `npm run build` and `npm run lint` clean. Commit
`docs(modelmix): foundational domain documentation (Mission 043)`. Full report
in `043-foundational-domain-documentation.md`.

## Mission 044 Result

Real per-token cost computation for OpenRouter-routed models (backend only,
Punch Board item 17 spend-visibility half). `openrouter.py`: `get_models()`
stops discarding `prompt_price`/`completion_price` — model dicts now carry
`prompt_price_per_token`/`completion_price_per_token` (existing `is_free`
derivation untouched), and a module-level `_PRICING` dict is refreshed on
every successful fetch (last fetch wins, no TTL). New
`compute_openrouter_cost_usd()` returns a real USD figure only when the model
id is `openrouter:`-prefixed, the bare model id is cached, and usage carries
real non-negative `prompt_tokens`/`completion_tokens`; otherwise `None`, so
`cost_usd` stays entirely absent (never 0, never estimated) — including for
every non-OpenRouter provider. `orchestrator.py::run_seat` (streaming and
non-streaming paths) and `moderator.py::run_moderator` attach `cost_usd` as a
sibling field on the same `seat_completed`/`moderator_completed` payloads
that already carry Mission 015 usage. `persistence.py::_apply_event` extends
the additive `usage`/`finish_reason` pattern to capture `cost_usd` onto
persisted messages (no schema bump). No spend cap, enforcement, or frontend
changes; what an exceeded dollar budget should do remains an open product
decision. Validation: targeted persistence/streaming/moderator suite **44
passed**, full backend **494 passed** (9 new tests; `--basetemp` workspace
override for the known corrupt system-temp ACL), frontend **138 passed**,
`npm run build` and `npm run lint` clean. Full report in
`044-real-cost-computation-backend.md`.

## Mission 045 Result

Cost rendering, frontend only (Punch Board item 17 visibility half closed; no
backend change). `modelmixState.js`: `costUsd: null` on all three seats in
`createModelMixState()` and `buildHistoryEntry()`; no-clobber capture from
`seat_completed`/`moderator_completed` (`event.cost_usd ?? seat.costUsd`,
matching the `usage` pattern exactly); hydration and history entries read
persisted `message.cost_usd ?? null`; `archiveCurrentRun` carries `costUsd`
through. `seatTelemetry.js`: new `formatCostUsd()` renders 4 decimals under
$0.01 and 2 decimals at or above (Mission 044's `$0.0045` fixture displays as
`$0.0045`, never `$0.00`), and `buildSeatTelemetry` pushes a `Cost` row only
for a real finite value — absent/null renders no row at all (Timing/Finish
conditional pattern, deliberately not Usage's always-present one). No
cross-seat aggregate, no "unavailable" placeholder, live footers only, no new
dependencies. Two existing archive `deepEqual` expectations gained
`costUsd: null` as the unavoidable consequence of the new field; no behavior
expectation changed. Validation: frontend **148 passed** (10 new tests),
`npm run build` and `npm run lint` clean, backend **494 passed** (unchanged).
Punch Board item 17 is now **SATISFIED**; dollar spend-cap enforcement remains
a separate, undecided product question. Full report in
`045-cost-rendering-frontend.md`.

## Mission 046 Result

Deterministic mock provider library (additive test infrastructure, Punch
Board item 14 closed; no production code and no existing test touched).
`backend/tests/mock_providers.py` provides ten composable `LLMProvider` factory
functions — `normal_provider`, `streaming_provider`, `slow_streaming_provider`,
`failing_provider`, `timeout_provider`, `rate_limited_provider`,
`cancellation_aware_provider`, `malformed_event_provider`,
`missing_usage_provider`, and `out_of_order_provider`/`duplicate_provider` —
each matching the real `backend/providers/base.py` interface, keeping default
timing fast (no real sleeps beyond a small bounded delay), and adding no
dependency. `test_mock_providers.py` (13 tests) proves each fixture directly
and demonstrates genuine usability by driving a real `multiplex_workers` flow
with `streaming_provider`. Existing tests are deliberately not migrated.
Validation: new suite **13 passed**, full backend **507 passed**, frontend
**148 passed**, `npm run build` and `npm run lint` clean. Full report in
`046-deterministic-mock-provider-library.md`.

## Mission 047 Result

Tauri CSP hardening (Punch Board item 34 CSP half; no production code touched
outside the config). `src-tauri/tauri.conf.json` `app.security.csp` changed
from `null` to: `default-src 'self'; script-src 'self'; style-src 'self'
'unsafe-inline' https://fonts.googleapis.com; font-src 'self'
https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'
http://localhost:8001 http://127.0.0.1:8001 http://tauri.localhost:8001`.
Per-directive justification is repo-evidence based (fonts origin, no CDN
scripts, backend URL built from `window.location.hostname`). Production
connect-src `http://tauri.localhost:8001` was added beyond the starting policy
because the frontend connects to `http://${window.location.hostname}:8001` and
that hostname is `tauri.localhost` in the packaged app (`FRONTEND_HOST`,
`lib.rs:223`) — the dev-only starting policy would block production. Runtime
verification (fonts render, real streaming Mix run, zero CSP console errors,
in BOTH `cargo tauri dev` and a launched production build) **requires the
user's hands** and is outstanding; the `'unsafe-inline'` style-src directive
is not runtime-confirmed. Automated suites unaffected: backend **507 passed**,
frontend **148 passed**, build and lint clean. Full report in
`047-tauri-csp-hardening.md`.

## Mission 048 Result

Manual session listing and deletion (backend only, Punch Board item 29
retention/delete basics; no automatic retention, no frontend, no schema
bump). `persistence.py`: `ModelMixPersistence` gains `list_sessions()` and
`delete_session()`; `AtomicJsonModelMixPersistence.list_sessions()` reuses the
`latest_session()` glob+mtime pattern and returns lightweight newest-first
summaries (`session_id`/`created_at`/`updated_at`/`message_count`, never
message/run content); `delete_session()` reuses the existing `_path()`
validation and unlinks inside `self._lock` (True if existed, False if not).
`registry.py`: `active_run_for_session()` returns a non-terminal run_id from
the existing `_runs` map (pruned, locked). `routes.py`: `GET
/api/modelmix/sessions` and `DELETE /api/modelmix/sessions/{session_id}` - 409
while a run in that session is active (checked before any delete), 422 on bad
id, 404 if absent, 204 on success. Validation: targeted persistence+streaming
suite **39 passed**, full backend **517 passed** (10 new tests), frontend
**148 passed**, `npm run build` and `npm run lint` clean. Full report in
`048-session-listing-and-deletion-backend.md`.

## Mission 049 Result

Session manager UI (frontend only, Punch Board item 29 retention/delete UI;
no backend change). `modelmixApi.js`: `listModelMixSessions()` (GET) and
`deleteModelMixSession()` (DELETE with encoded id), reusing `checkedFetch`.
`ModelMixObserver.jsx`: `Sessions` added to `SETTINGS_SECTIONS`;
`SessionsSection` lists real sessions (shortened id, created/updated absolute
time, message count) with an honest empty/loading state, per-row two-click
delete confirmation (a single click never calls the API), removal of the
deleted row without a full re-fetch, and the real backend message surfaced
on a 409. Deleting the currently-open session resets the cockpit via the
existing `startNewSession` (reused `resetToFreshSession`); deleting any other
session leaves the live cockpit unchanged. No auto/scheduled retention UI, no
bulk delete, no new dependency. Validation: frontend **157 passed** (9 new
tests), `npm run build` and `npm run lint` clean, backend **517 passed**
(unchanged). Full report in `049-session-manager-frontend.md`.

## Mission 050 Result

Per-seat spend warning (backend only, Punch Board item 17, informational only
- no enforcement, no cutoff, no cumulative tracking). `guardrails.py`:
`WARNING_COST_USD_THRESHOLD = 0.10` (provisional notice-this default for a
single seat turn, matching the Mission 019 provisional-default precedent) and
`should_warn_cost()` - true only for a real finite number strictly above the
threshold; `None` (non-OpenRouter or uncached pricing) never warns, exactly
matching the telemetry honesty rules. `orchestrator.py` (streaming and
non-streaming worker paths) and `moderator.py` emit one
`seat_cost_warning`/`moderator_cost_warning` (cost_usd, threshold) at the
exact point real cost is computed, just before the completion event -
purely additional, never replacing or altering the completed run. Fires once
at completion per seat; never mid-stream, no cumulative session total. The
output-length warning (`WARNING_OUTPUT_THRESHOLD_CHARS`/`seat_output_warning`)
is untouched - a separate parallel mechanism. Validation: targeted
cost+guardrails suite **43 passed**, full backend **525 passed** (8 new
tests), frontend **157 passed**, `npm run build` and `npm run lint` clean.
Enforcement/cutoff and cumulative session-cost tracking remain separate,
undecided future work. Full report in `050-per-seat-spend-warning-backend.md`.

## Mission 051 Result

Spend warning rendering (frontend only, Punch Board item 17 spend visibility
closed; no backend change). `modelmixState.js`: `seat_cost_warning` and
`moderator_cost_warning` set `seat.costWarning`/`moderator.costWarning =
{ cost_usd, threshold }`, mirroring the `outputWarning` set exactly in both
applyModelMixEvent branches. `seatTelemetry.js`: `buildSeatTelemetry` renders
a plain, non-alarming `Cost notice` footer row only when `costWarning` has a
real finite `cost_usd` and `threshold`, reusing the existing `formatCostUsd`
(sub-cent values four decimals, never `$0.00`). Live-only by design:
`costWarning` is deliberately absent from `createModelMixState` shapes,
`hydrateModelMixState`, `buildHistoryEntry`, and `archiveCurrentRun`, exactly
matching `outputWarning`. No new formatter, no alarm styling, no new
dependency. Validation: frontend **166 passed** (9 new tests), `npm run
build` and `npm run lint` clean, backend **525 passed** (unchanged).
Enforcement/cutoff and cumulative session-cost tracking remain separate,
undecided future work. Full report in `051-spend-warning-rendering-frontend.md`.

## Mission 052 Result

Per-request spend confirmation gate, backend only (Punch Board item 17 advanced
with the first real dollar-cap enforcement). `TwoWorkerRequest` gains
`spend_limit_usd` (Optional[float], `gt=0`) and `confirm_over_budget` (bool,
default False). `routes.py::stream_two_workers` runs the gate BEFORE
`run_registry.start()`: when `spend_limit_usd` AND `session_id` are provided and
`confirm_over_budget` is False, `_over_budget_rejection` loads the session via
the existing `load_session` and inspects only the most recent run's
already-persisted messages. Per-seat only - never an aggregate - any message
with a real, non-`None` `cost_usd > limit` yields HTTP 402 naming the seat and
actual cost. `None` cost is never treated as over-budget; a missing session or
prior run proceeds; `confirm_over_budget: true` bypasses the check entirely;
omitting `spend_limit_usd` is byte-for-byte unchanged. Hard boundaries honored:
no `should_warn_cost`/`WARNING_COST_USD_THRESHOLD`/Mission 050 warning changes,
no server-side persistence of the limit, no `compute_openrouter_cost_usd`
change, no schema bump, no new dependency. ModelMix-only path. Validation:
`test_modelmix_spend_gate.py` **9 passed** (7 acceptance criteria + regression),
targeted 4-file suite **44 passed**, full backend **544 passed** (535 + 9),
frontend **181 passed**, `npm run build` + `npm run lint` clean. Full report in
`052-spend-confirmation-gate-backend.md`.

## Mission 053 Result

Temperature control and moderator guidance, backend only (Punch Board item 26
advanced). `TwoWorkerRequest` gains `temperature` (Optional[float], 0.0-2.0,
validated) and `moderator_guidance` (Optional[str], max 2000 chars, validated).
Both thread through `registry.start()` -> `_run` -> `_run_phase` exactly like
`warning_threshold_chars`. All four real provider call sites
(`orchestrator.py` streaming + non-streaming, `moderator.py` streaming +
non-streaming) pass `temperature` only when not `None` via a conditional
`provider_kwargs` dict - when `None`, NO `temperature` kwarg at all, so each
provider's own default applies unchanged; no ModelMix-level default added.
`assemble_moderator_input` appends guidance after the FULL unmodified
`MODERATOR_INSTRUCTIONS` as `Additional guidance from the user:` - strictly
append-only; when `None`, the system message is byte-for-byte identical.
ModelMix-only; no Council/Advisor path, no `settings.py` persistence, no new
dependencies, no schema bump. Validation: targeted pytest **30 passed**, full
suite **535 passed** (525 + 10 new), frontend **166 passed**, build + lint
clean. Frontend controls and local persistence remain open (item 26 still
PARTIAL). Full report in `053-temperature-and-moderator-guidance-backend.md`.

## Mission 054 Result

Temperature and moderator guidance, frontend only (Punch Board item 26). New
`frontend/src/modelmixBehavior.js` mirrors `guardrailSettings.js`: bounds
`MIN/MAX_TEMPERATURE = 0.0/2.0`, `MAX_MODERATOR_GUIDANCE_LENGTH = 2000`, plus
`validateBehavior`/`loadBehavior`/`saveBehavior`/`clearBehavior` with the same
defensive discipline (malformed/missing localStorage -> null/false, never
throws; each field independent, absent field skipped). `ModelMixObserver.jsx`:
new Settings "Behavior" section renders a temperature number input (0.0-2.0,
step 0.1) and a moderator-guidance textarea (max 2000 chars, live remaining
count) with a Save/Clear pair mirroring `GuardrailsSection`; `send()` includes
`temperature`/`moderator_guidance` only when a valid saved value exists,
omitting the key otherwise (never `null`) - exact guardrail-override
precedent. No backend change, no new dependency. Validation: frontend **176
passed** (166 + 10 new), build + lint clean, backend **535 passed**
(unchanged). Both settings are local-preference only, not persisted
server-side. Full report in `054-temperature-and-moderator-guidance-frontend.md`.

Follow-up: added `frontend/src/components/ModelMixSendBehavior.test.jsx`
(+5) mirroring ModelMixSendCompare.test.jsx's mocked-startModelMixRun capture
pattern: both saved values -> body carries both correctly; nothing saved ->
NEITHER key present (`'temperature' in body === false`);
temperature-only-saved -> guidance genuinely absent; guidance-only -> temperature
genuinely absent; malformed saved behavior ignored (both omitted). Frontend
suite now **181 passed** (18 files; 166 -> +15), build + lint clean; backend
unchanged **535 passed**.
## Mission 055 Result

Native credential entry for ModelMix's 12 simple (non-OAuth) providers,
frontend only (Punch Board item 26 significantly advanced — credential/endpoint
entry that previously shipped users to Council settings now lives in the ModelMix
cockpit). `frontend/src/modelmixApi.js` gains `updateSettings` (partial PUT to the
existing `PUT /api/settings`), `testProvider`, `testOpenrouter`, `testOpencode`,
`testOllama`, and `testCustomEndpoint` (each POSTing to the exact existing
`_require_admin`-guarded test endpoint and returning the real JSON).
`ModelMixObserver.jsx` Providers section: keeps the connected/not-connected
`configuredSources` READ list, then adds a write-only editor per provider —
password-masked key inputs (OpenRouter; OpenAI, Anthropic, Google, Mistral,
DeepSeek, Groq, NVIDIA; OpenCode Zen+Go sharing one key), a URL input for
Ollama's base URL, and name/url/optional-key inputs for custom endpoint — each
with a Test button rendering the real returned success/failure message and a
Save that PUTs only the edited field(s) via the existing partial-merge endpoint.
Saved values are never pre-filled or echoed (write-only); after a successful save
the section re-fetches settings so the READ status updates. The former "Manage
providers in council settings" link is now scoped to OAuth providers only (xAI,
ChatGPT, GitHub Copilot), which are explicitly deferred to a separate mission.
Zero backend changes; no new dependency. Validation: frontend **203 passed**
(181 + 22 new: 11 API + 11 component), build + lint green, backend **544 passed**
(unchanged). Full report in `055-native-credential-entry-simple-providers.md`.
## Mission 056 Result

Native OAuth connect/disconnect for the three OAuth providers (`xai-oauth`,
`openai-oauth`, `github-copilot`) in the cockpit Settings "Providers" section —
**closing the credential fold-in (Punch Board item 26 is now CLOSED)**. Zero
backend changes: reuses the existing uniform device-code flow and the existing
`_require_admin`-guarded routes exactly. `frontend/src/modelmixApi.js` gains
`startOAuthConnection` (POST `/api/oauth/{id}/start`), `getOAuthConnectionStatus`
(GET `/api/oauth/{id}/status?session_id=...`), and `disconnectOAuthProvider`
(DELETE `/api/oauth/{id}`). `ModelMixObserver.jsx` extends the Mission 055
Providers section with an `OAuthRow` per provider: real connected status from
`xai_oauth_connected`/`openai_oauth_connected`/`github_copilot_connected`, a
Connect button that starts the flow and renders the real `user_code` plus a
clickable `verification_uri_complete` link (falling back to `verification_uri`
when complete is `null`), then polls every 2.5s until `complete`/`error`/`expired`
(interval cleared) showing the real error/expired message; a Disconnect button
calls the DELETE route and refetches status. Polling is bounded to `expires_in`
and every interval is cleared on unmount — a test proves no leak. The stale
"still managed in council settings" OAuth copy is removed. No provider (simple or
OAuth) now requires a trip to Council settings. Validation: frontend **215 passed**
(203 + 12 new: 5 API + 7 component), build + lint green, backend **544 passed**
(unchanged, no backend files touched). Full report in
`056-native-oauth-connect-disconnect.md`.

## Mission 057 Result

Spend limit control and 402 confirmation UX (frontend-only) — **closing Punch
Board item 17's gate half**. `frontend/src/modelmixBehavior.js` gains
`loadSpendLimit`/`saveSpendLimit`/`clearSpendLimit` (validating `value > 0`,
matching the backend's `gt=0` bound exactly, same defensive storage discipline
as every existing settings module). `send()` includes `spend_limit_usd` in the
request body only when a valid saved value exists (key genuinely absent
otherwise). When `startModelMixRun` rejects with HTTP 402, the real backend
message (which seat, actual cost) renders in a dedicated confirmation UI with an
explicit "Proceed anyway" button that resends the identical original request
body plus `confirm_over_budget: true` — never auto-retrying, never persisting
the confirmation flag. A dollar-amount input with save/clear pair is added to
the existing Behavior Settings section. Validation: frontend **228 passed**
(215 prior + 13 new: 4 in `modelmixBehavior.test.js`, 3 in
`ModelMixSendBehavior.test.jsx`, 6 in new `ModelMixSpendLimit.test.jsx`), build
+ lint green. Backend: zero files touched; observed errors are pre-existing
Windows temp-dir `WinError 5` PermissionErrors, not mission regressions. Full
report in `057-spend-limit-control-and-confirmation-frontend.md`.
