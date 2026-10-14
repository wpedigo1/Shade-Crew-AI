# ModelMix Punch Board

Locked: 2026-08-27 17:39 CT  
Reconciled through Mission 034: 2026-08-31 CT

Status: **BUILD PLAN LOCKED FOR ALPHA**

This is the authoritative repository copy of the ModelMix build order and project roadmap. Mission numbers are implementation slices; they are not one-to-one with Punch Board items.

Changes to this order require a concrete technical blocker or newly verified fact, not preference or curiosity.

## Mission Ledger

| Mission | Result | Engineering outcome |
|---|---|---|
| 001 | PASS | Baseline/architecture spike; inherited verification and streaming/SSE/process/credential ground truth |
| 002 | PASS | Provider stream contract, ChatGPT OAuth streaming, two independent workers, ordered seat/run SSE |
| 003 | PASS | Process-local event journal, replay/tailing, disconnect-vs-cancel separation, explicit cancellation |
| 004 | PASS | Browser observer, independent Worker A/B rendering, reconnect/replay, fixed Send/Stop |
| 005 | PASS | Moderator backend fan-in/synthesis, isolation, partial/failure handling |
| 006 | PASS | Three-panel Worker A / wider Moderator / Worker B cockpit |
| 007 | PASS | Searchable configured-model selectors, exact IDs, active-run locking, accessible keyboard behavior |
| 007.5 | **PASS** | MCP 2.x security/compatibility interlock closed; clean dependency set retained |
| 008 | **PASS** | Versioned atomic JSON persistence, restart reconstruction, and cockpit hydration on `main` |
| 009 | **PASS (LOCAL)** | Seat-scoped bounded multi-turn Worker/Moderator history with hot-swap continuity and leakage tests |
| 010 | **PASS (LOCAL)** | Seat history owned character budgets: per-message 4k and per-seat 24k deterministic bounding with whole-turn oldest-first eviction |
| 010.5 | **PASS (LOCAL)** | Frontend test runner interlock: Vitest runner wired in; existing frontend tests collected and passing (24/24) |
| 011 | **PASS (LOCAL)** | Multi-turn cockpit display: prior runs archived into per-seat history and rendered above the live turn in each panel |
| 012 | **PASS (LOCAL)** | Session control and prompt plumbing: archived turns carry real prompts/models; separate New Session control that clears local session key and resets the cockpit |
| 013 | **PASS (LOCAL)** | Run and seat timeouts: ModelMix-owned 600s run / 300s seat-Moderator wall-clock bounds enforced with honest `reason: "timeout"` terminal outcomes and a proven no-late-writes guarantee |
| 014 | **PASS (LOCAL)** | Reachability + test hygiene: real `GET /modelmix` serves `index.html` from `FRONTEND_DIST_DIR` so a production build can reach the three-panel cockpit, a visible Council sidebar link navigates there, and every `RunRegistry()` construction in `backend/tests/` now writes to an isolated `tmp_path` store instead of the live `data/modelmix/sessions/` directory |
| 015 | **PASS (LOCAL)** | Telemetry truth layer: events carry wall-clock `ts`; `_apply_event` persists provider-reported `usage`/`finish_reason` (opaque, un-normalized) plus `started_at`/`completed_at`; the frontend truth layer and `describeUsage` capture them without rendering; and the last Mission 014 polling test (streaming route) now uses an isolated persistence |
| 016 | **PASS (LOCAL)** | Compact top bar and panel view controls: one thin persistent top strip (brand, inert `Mode: Mix` label, session status, New Session moved from `.modelmix-actions`, Details-hidden run metadata, Back to Council), and CSS-driven per-panel Collapse/Maximize/Reset view controls that hide panels from layout without ever unmounting them — view state lives only in local component state, untouched by `modelmixState.js` |
| 017 | **PASS (LOCAL)** | Settings shell: a gear entry in the top bar opens an in-app overlay (About renders the real package.json version plus MIT/copyright and text-only AI Counsel attribution; Providers is a read-only Connected/Not-connected list computed from the now-exported `configuredSources` with zero credential values; Defaults saves/clears `modelmix.defaultSeatModels` in localStorage and applies saved seat defaults at initial mount with the exact built-in fallbacks preserved) — frontend-only, no route, no new dependencies |
| 018 | **PASS (LOCAL)** | Telemetry rendering: the cockpit surfaces Mission 015's captured truth as compact per-seat footers (usage labeled `authoritative (provider-reported)` via `describeUsage` showing the provider-reported total token count when present — `total_tokens`/`totalTokenCount` — else the raw key names, or honest `unavailable`, ModelMix-calculated elapsed timing labeled `(calculated)` from `started_at`/`completed_at`, Moderator-only `finish_reason`, raw wall-clock start/end range) rendered only for the live turn — prior-turn archives keep telemetry hidden (explicit follow-up) and cost/pricing wiring stays deliberately out of scope |
| 019 | **PASS (LOCAL)** | Output guardrails, backend enforcement: a new `guardrails.py` owns the provisional char bounds (`WARNING_OUTPUT_THRESHOLD_CHARS = 20_000`, `HARD_OUTPUT_CAP_CHARS = 40_000`, exact-boundary `clip_delta`); `run_seat` and `run_moderator` emit a one-shot `seat_output_warning`/`moderator_output_warning` on the first threshold crossing, then stop consuming the provider stream at the hard cap, truncating deterministically to exactly the cap and terminating as `seat_completed`/`moderator_completed` (NOT failed) with `finish_reason: "modelmix_output_cap"` — honestly distinct from provider termination, failure, timeout, and user cancellation. Non-streaming paths are capped with no warning. Constants are provisional defaults (configurability is a later settings mission); provider-quota usage warnings are explicitly deferred as not honestly buildable — no quota data exists. No changes to `events.py`/`persistence.py`/`journal.py`/`timeouts.py`/`history.py`/`registry.py` or any frontend file |
| 020 | **PASS (LOCAL)** | Configurable output guardrails, backend: `TwoWorkerRequest` gains optional `warning_threshold_chars`/`hard_cap_chars` (`gt=0`); `routes.py::_resolve_guardrail_overrides` defaults omitted fields to the Mission 019 constants, rejects values outside `guardrails.MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`, and rejects `hard_cap_chars < warning_threshold_chars` — every violation surfaces as a 422 before any provider is resolved or called. The resolved pair rides the exact `registry.start → _run → _run_phase → multiplex_workers/run_moderator` chain (mirroring `seat_timeout`); enforcement logic, event payloads, and the `modelmix_output_cap` finish reason are byte-for-byte unchanged, the frontend sends neither field yet (omitting both is byte-for-byte Mission 019 behavior), and nothing is persisted server-side |
| 021 | **PASS (LOCAL)** | Guardrails settings and visibility, frontend: a 4th Settings section (Guardrails) saves/clears a local `modelmix.guardrails` override via a new `guardrailSettings.js` module (validate/load/save/clear, `MIN=100`/`MAX=200_000` bounds mirroring the backend, server cross-check mirrored); `send()` injects `warning_threshold_chars`/`hard_cap_chars` only when a valid override exists (both omitted otherwise — byte-for-byte Mission 020 behavior); `seat_output_warning`/`moderator_output_warning` become a live-only `outputWarning` on the seat (never persisted to history/hydration) rendered in every seat footer as `Approaching output limit: 22,451 / 20,000 chars`; worker seats gain the Moderator's `finish_reason` capture, and finish captions render on all seats (`modelmix_output_cap` → "Output capped by ModelMix", everything else verbatim). Frontend-only — no backend, API, or persistence changes |
| 022 | **PASS (LOCAL)** | Alpha acceptance integration tests (backend, verify-only): new `test_modelmix_alpha_acceptance.py` proves items 4–11 of the item-33 checklist through the real HTTP surface — stream both workers + Moderator on one ordered feed, cancel (real route; terminal `run_cancelled`, no post-cancel deltas, persisted `cancelled`), survive worker failure (partial run, failed worker excluded from the Moderator handoff), reopen session (full persisted transcript), multi-turn isolation across a second POST, provider-faithful telemetry (exact usage/finish/timestamps), and no credential leak into stream/journal/persisted session. One deliberate async-httpx single-loop deviation for the two-in-flight cancel test; everything else reuses the sync TestClient pattern. Discloses an observed cancel-path race (sub-ms cancel window can hang the run until the 600s run timeout) as a real gap, not patched under verify-only rules | `022-alpha-acceptance-integration-test.md` |
| 023 | **PASS (LOCAL)** | Deterministic cancellation-race fix: `multiplex_workers`' `finally` swapped its unbounded `asyncio.gather` for `await_cancellation_grace` (`CANCEL_GRACE_SECONDS = 5.0` in `timeouts.py`), so a seat task that absorbs cancellation can no longer block `run_cancelled`; the Moderator phase awaits its task through `asyncio.shield` so a slow-to-cancel Moderator can no longer leave `_run_phase` un-woken indefinitely. A cancel now reaches terminal `run_cancelled` within the bound even when every seat/Moderator holds past the grace period, and prompt-cancel stays byte-for-byte unchanged. Proven deterministically by `backend/tests/test_modelmix_cancel_race.py` (8 tests that construct the stall condition with a holding fake provider rather than racing timing, plus structural "abandoned mid-stream / never a timeout" contract asserts); full backend **403 passed**, frontend unchanged at **118 passed** / build / lint green | `023-cancellation-race-fix.md` |
| 024 | **PASS (LOCAL)** | Cancel-before-start terminal state fix: a run cancelled before `_run`'s first `await` now reliably reaches `run.status == "cancelled"` with a `run_cancelled` event. Root cause: CPython 3.10 `coro.throw(CancelledError)` on a never-started coroutine skips the entire body — no `try/except` inside the coroutine catches it. Fix: `await asyncio.sleep(0)` in `start()` after `create_task` guarantees `_run` has entered its `try` block and suspended at a real `await` before the caller can cancel; `mark_status("active")` moved inside `try` so the except handler covers the earliest cancel point. Proven deterministically by `test_cancel_before_run_starts_reaches_terminal_cancelled` in `test_modelmix_cancel_race.py`; full backend **404 passed**, no existing test modified, `ruff check` clean | `024-cancel-before-start-terminal-fix.md` |
| 025 | **PASS (LOCAL)** | Harden the local backend boundary: `_require_admin` (reused exactly as-is) required on every endpoint that reads/writes/uses stored credentials or makes a server outbound request with a client-influenced target/credential - 20 endpoints in `backend/main.py` (16 required + 4 judgment extensions: `GET /api/models`, `GET /api/models/direct`, `GET /api/ollama/tags`, `GET /api/custom-endpoint/models`). Closes the `test-custom-endpoint` blind SSRF-to-stored-key path before any outbound call. Three existing tests (font-size, advisor presets, council presets) switched to loopback peers as the legitimate local-operator case. New `test_admin_guard_credential_endpoints.py` (27 tests) proves non-loopback rejection without token, loopback/token success, and outbound-never-invoked for the SSRF path. Full backend **431 passed**, `ruff` clean; frontend **118 passed**, build green, lint clean. Flagged follow-ups: CORS regex matches any dotted-IPv4 origin; custom-endpoint URL allow-listing for a local loopback attacker | `025-harden-local-backend-boundary.md` |
| 026 | **PASS (LOCAL)** | Real Windows ACL hardening for credential file storage: `os.chmod(0o600)` is a no-op on Windows, so `file_backend` now runs `icacls "<path>" /inheritance:r /grant:r "<current-user>":F` via `subprocess` (no pywin32) after each atomic credential write, gated behind `sys.platform == "win32"`; current user resolved from `USERNAME`/`USERDOMAIN` env vars (fallback `os.getlogin()`); failures log a warning and never crash a write (mirrors the `except OSError: pass` philosophy but logs); a once-per-process startup warning surfaces pre-existing/never-hardened plaintext files on Windows. Scoped to `file_backend.py` only; default `file` mode and `get_effective_mode()` unchanged by declared boundary; no credential-value changes. New `test_credentials_file_hardening.py` (7 tests) mocks `subprocess.run`/`sys.platform`. Full backend **438 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Advances Punch Board item 30 (current-model half); a separate later re-verification of credential storage is required once Tauri (item 34) exists | `026-windows-credential-file-hardening.md` |
| 027 | **PASS (LOCAL)** | Auto-remediate an unhardened credentials file on startup: `_warn_if_unhardened()` in `file_backend.py` now attempts `_harden_credentials_file()` directly on the first touch (read or write) of an existing, unhardened Windows file, then logs INFO "Restricted..." on success or the existing warning on failure — a single, one-time, automatic remediation (no new key write or manual icacls needed to protect a pre-existing file). `_harden_credentials_file()` logic reused exactly; never raises. Extends `test_credentials_file_hardening.py` to 10 tests (one Mission 026 test necessarily reconciled, flagged). Full backend **441 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Item 30 current-model half closeable; Tauri re-check (item 34) carried forward | `027-credentials-file-startup-remediation.md` |
| 028 | **PASS (LOCAL)** | Verify and harden the existing Compare (no-moderator) backend path: `TwoWorkerRequest.moderator_model` optional and `registry._run_phase` / `orchestrator.multiplex_workers` already support a two-worker run with no moderator phase, but had zero test coverage. Driven through the REAL HTTP route (`POST /runs/stream` with `moderator_model` omitted) in new `test_modelmix_compare_mode_backend.py` (7 tests), proving: both workers stream with ZERO moderator events and `run_completed "completed"`; one worker fails -> `"partial"` + persisted session reflects the failed seat via `GET /sessions/{id}`; both workers fail -> observed as-shipped `run_completed "partial"` (not `failed`; product-semantics note, not a defect); multi-turn isolation holds moderator-less and the dead `seat_histories["moderator"]` key never leaks; per-worker guardrails (warning/hard cap) apply; cancellation reaches `run_cancelled` mid-stream; reopening a moderator-less session reconstructs with no moderator message and nothing chokes on the moderator's absence (`models["moderator"]` persists as `None`, tolerated). NO production code changed; no `mode` concept added; no frontend change. Full backend **448 passed**, `ruff` clean; frontend **118 passed** / build / lint green. Backend half of item 28 deliverable | `028-compare-backend-verification.md` |
| 029 | **PASS (LOCAL)** | Deliver the frontend Compare mode + a no-moderator status fix, closing item 28. Part 1 backend fix: when BOTH workers fail with no moderator, `multiplex_workers` now reaches `run_completed` with `status="failed"` instead of `"partial"` (replaced `failed: bool` with `failed_seats: set`; moderator path `emit_run_completed=False` untouched); point-3 test renamed to `test_no_moderator_both_workers_fail_reaches_run_completed_failed` and asserts `failed`. Part 2 frontend Compare mode: inert top-bar `Mode: Mix` span becomes a real `select.modelmix-mode-select` (Mix / Compare) persisted via new `modelmixMode.js` (`loadSavedMode`/`saveMode`, `localStorage["modelmix.mode"]`, valid values only `mix`/`compare`, NO `solo`); Compare hides the Moderator selector, omits `moderator_model` from the request body, hides-but-keeps-mounted the center moderator panel (`modelmix-panel-hidden`), and uses a 2-column models grid; mode control disables during an active run via existing `modelSelectorsDisabled`. New tests: `modelmixMode.test.js` (6), `ModelMixSendCompare.test.jsx` (6). One existing top-bar test necessarily updated (span became a real control) — sole modified existing test. Validation: backend **448 passed**, `ruff` clean; frontend **130 passed** / build / lint green. Item 28 (Compare) CLOSED | `029-compare-mode-status-fix-and-frontend.md` |
| 030 | **PASS (LOCAL)** | Backend support for Solo (single-worker) mode. `TwoWorkerRequest.worker_b_model` is now `Optional[str]` (default `None`); the route rejects the worker_b-absent + moderator hybrid with 422 **before** any provider resolver call; `worker_b_model: Optional[str]` threads through `RunRegistry.start`/`_run`/`_run_phase` and `orchestrator.multiplex_workers` (active seats computed locally; removed now-unused `SEATS`). For a Solo run, persisted `models` carry `worker_a` + `moderator: None` with the `worker_b` key absent, never passed to `multiplex_workers`, and no `moderator` events emitted. `persistence._validate` statically relaxes the structural guard from an exact three-key set to a subset-of-{worker_a,worker_b,moderator} with `worker_a` always present non-empty and `worker_b` never None/empty; Mix/Compare/old shapes still validate (proven by tests). Defensive no-hybrid guard in `_run_phase` (`moderator_model` and `worker_b_model` both present required). Zero changes to `history.py` (Solo turns already produce no worker_b message). New `test_modelmix_solo_mode.py` (7 route/orchestration tests: solo completed, solo failed, 422-before-resolver, defaults, solo-then-mix isolation, guardrails, cancellation) + new persistence validator tests. Validation: backend **460 passed**, `ruff` check clean; frontend **130 passed** / build / lint green. Frontend Solo mode out of scope — item 27 remains partially open | `030-solo-mode-backend.md` |
| 031 | **PASS (LOCAL)** | Frontend Solo delivery, closing item 27 with Mission 030. Adds `solo` to the persisted mode vocabulary and Mix / Compare / Solo control. Solo renders only Worker A's selector, requires only Worker A, and omits `worker_b_model` plus `moderator_model` from the request object. Moderator and Worker B panels stay mounted but CSS-hidden; Worker A uses the existing single-column maximized visual treatment. Mode visibility remains independent from panel-view state, and a maximize target on a hidden seat cannot blank Solo. New `ModelMixSendSolo.test.jsx` (8 tests); Solo persistence tests extended; sole modified existing test is the necessary top-bar three-option assertion. Frontend **138 passed** / build / lint green; backend workspace-temp rerun **460 passed** after the exact command reproduced the known inaccessible default-temp `WinError 5`. Items 27 (Solo) and 28 (Compare) complete end to end | `031-solo-mode-frontend.md` |
| 032 | **PASS (LOCAL)** | Tauri 2 toolchain check and minimal shell scaffold. Rust/Cargo and Windows C++ Build Tools/WebView2 were present; missing `cargo-tauri` was installed as CLI 2.11.4. Standard `src-tauri/` reuses the existing Vite dev server at `/modelmix` and `frontend/dist`, with no sidecar/backend-launch behavior. `cargo tauri dev` visibly opened the native ModelMix three-panel cockpit against the separately started backend. Frontend **138 passed** / build / lint green; `cargo check` green; backend workspace-temp rerun **460 passed** after the exact command reproduced the known inaccessible default-temp `WinError 5`. Begins item 34; installer, sidecar, and packaged credential re-verification remain open | `032-tauri-toolchain-and-shell.md` |
| 033 | **PASS (LOCAL)** | Standalone Windows PyInstaller `onedir` backend bundle proven from the frozen executable: sanitized no-Python/uv/venv launch, real health/session/settings/MCP routes, cross-process Windows keyring retrieval and cleanup, file-mode restart plus non-inherited current-user FullControl ACL, clean Ctrl+C/no orphan, valid JSON/no credential temp, and unchanged repository data. Backend **461 passed** with the workspace-temp workaround after the exact command reproduced the known default-temp `WinError 5` (**247 passed, 214 errors**); frontend **138 passed** / build / lint green; Rust format/check and focused Ruff green. Item 34 remains open for Tauri sidecar integration/lifecycle, installer delivery, and final credential packaging | `033-pyinstaller-backend-bundle.md` |
| 034 | **PASS (LOCAL)** | Frozen-aware user data directory, fixing the Mission 033 finding (`_internal\data\credentials.json`). New `backend/user_data_dir.py`: `is_frozen()` (standard `getattr(sys, "frozen", False)`) and `resolve_user_data_dir()` — repo `data/` when not frozen (same path the three files already used), `%LOCALAPPDATA%\ModelMix` when frozen, executable-dir fallback with a clear warning if `LOCALAPPDATA` is absent, and `mkdir(exist_ok=True)` before return. `CREDENTIALS_FILE`, `SETTINGS_FILE`, and `personas._DATA_DIR` now derive from it; no other module, keyring/store facade, route, `icacls` hardening, `src-tauri/`, or `frontend/` change; stdlib only. New `test_user_data_dir.py` (7 regression/simulation tests). Backend **468 passed** (461 unmodified + 7 new); focused credential run **24 passed**; `ruff` clean; frontend **138 passed** / build / lint green (required, unchanged). Frozen-mode path proven by simulation; real frozen-build confirmation deferred with item 34 | `034-frozen-aware-user-data-directory.md` |


**Mission 008 is present on `main` and its persistence tests pass.**

### Mission 007.5 Interlock Result

Mission 007.5 did **not** reorder the locked 47-item build plan. It was a bounded remediation interlock created from an observed repository compatibility blocker after dependency-security cleanup.

Accepted Mission 007.5 implementation commit:

`e018ed06807beda2c11531f065b2d4181c346ca8` — `fix(mcp): migrate inherited MCP integration to MCP 2.x API`

Observed accepted results:

- MCP retained at **2.1.1**;
- MCP tests: **146 passed**;
- full backend suite: **458 passed, 5 failed**;
- five remaining failures recorded as pre-existing Windows-specific legacy chassis test issues, not MCP migration regressions;
- Python dependency audit: **0 known vulnerabilities** across 95 locked dependencies;
- frontend dependency audit: **0 vulnerabilities**;
- frontend production build: **PASS**;
- backend import/runtime mount verified at `/mcp` with SSE `/mcp/sse`.

MCP remains an **alpha non-goal** as a ModelMix product capability; compatibility maintenance did not promote it into alpha scope.

## Progress Against the Locked Board

### Satisfied or substantially satisfied

- **1 — Freeze inherited baseline**
- **2 — Run inherited verification**
- **3 — Spike the four unknowns**
- **5 — Lock chassis policy**
- **6 — Create ModelMix-owned backend boundary**
- **8 — Define context isolation policy**
- **10 — Define ordered event contract** — every canonical event now carries a wall-clock `ts` in both constructors, additive alongside `seq`/`run_id`/`type` (Mission 015); the cockpit surfaces that timing truth per seat (Mission 018)
- **11 — Define persistence boundary**
- **15 — Build NON-STREAMING Mix vertical slice first**
- **16 — Prove failure + cancellation**
- **18 — Add normalized provider streaming interface**
- **19 — Multiplex streams into one ordered SSE run feed**
- **20 — Stream Moderator**
- **21 — Build browser-first three-panel cockpit** — reachable from a production build (`GET /modelmix`) and from the Council sidebar (ModelMix nav link) as of **Mission 014**
- **22 — Bind UI to durable run/session state**
- **23 — Add Stop behavior**
- **25 — Add minimal telemetry** — state, elapsed time, provider-reported tokens, labeled estimates, reliable per-call cost only (Mission 018 renders honest per-seat usage labels, Moderator finish reason, and calculated timing; cost/pricing wiring and per-historical-turn footers are deferred follow-ups)

### Partially satisfied — keep open

- **7 — Define domain objects:** run/event/seat concepts exist; full locked domain/schema-version contract remains incomplete.
- **9 — Define run state machine:** core active/terminal outcomes exist; complete timeout/retry/state contract remains open. Mission 013 adds honest wall-clock `reason: "timeout"` outcomes for runs, seats, and Moderator.
- **12 — Define provider capability matrix:** streaming/fallback and configured discovery exist; full matrix remains open.
- **14 — Build deterministic mock provider:** deterministic fakes/mocks support current tests; full failure/timeout/rate-limit fixture matrix remains open.
- **17 — Add basic spend/runtime guardrails — CLOSED (visibility: 044/045, warning: 050/051, gate: 052/057).** Stop, turn cap, wall-clock run (600s) / seat-Moderator (300s) timeouts (Mission 013), seat-history character budgets (Mission 010), hard output cap + warning (Missions 019–021), dollar cost visibility (Missions 044/045), per-seat spend warning (Missions 050/051), and dollar-cap enforcement with frontend confirmation UX (Missions 052/057) are all complete end to end.
- **29 — Finalize Mix multi-turn session behavior:** seat-scoped Worker/Moderator history, bounding, failure-partial reuse, hot-swap continuity, completed-turn cockpit display, and New Session reset are implemented; retention/delete UX remains open.
- **26 — Add provider/settings UX sufficient for alpha:** searchable configured selectors are complete; the visible ModelMix navigation entry point in the Council sidebar exists (Mission 014); the cockpit Settings surface is now a real entry (Mission 017) with read-only provider status from the exported `configuredSources`; full alpha provider/settings flow remains open.

### Open / upcoming

- **4 — Lock license and provenance** — **PARTIAL — MISSION 017** (the cockpit About section now surfaces the MIT license, the copyright holder, the real version, the text-only AI Counsel attribution, and the repo URL; `OPEN_SOURCE_CREDITS.md`, inherited-module provenance, and the shipped dependency-license inventory remain open)
- **13 — Define privacy/data-routing rules**
- **24 — Build thin top controls** — **CLOSED (Missions 012/016/017/029/031).** Compact top strip, session and Settings controls, panel controls, and persisted Mix / Compare / Solo selector are delivered.
- **27 — Add Solo** — **CLOSED (Missions 030 + 031).** One-worker backend path plus persisted frontend Solo mode, exact request-key omission, and full-width single-panel cockpit are delivered.
- **30 — Verify credential storage in actual packaging model**
- **31 — Harden local backend boundary**
- **32 — Add basic structured observability**
- **33 — Alpha acceptance test**
- **34–47 — Post-alpha work**

---

# Locked 47-Item Build Order

## PHASE 0 — Establish Ground Truth

### 1. Freeze inherited baseline — **SUBSTANTIALLY SATISFIED**

Record ModelMix baseline commit, AI Counsel upstream revision, dependency lockfile state, and inherited provenance.

### 2. Run inherited verification — **SUBSTANTIALLY SATISFIED**

Run/document backend tests, frontend tests/build, existing lint/type checks, practical dependency/security scan, and inherited app launch. Mission 010.5 wired a Vitest runner and brought the existing frontend test files to a real 24/24 observed pass; `npm audit` reports 0 vulnerabilities.

### 3. Spike the four unknowns — **SATISFIED**

Verify provider streaming, SSE/reconnect, process-local run state, and credential behavior from actual code.

## PHASE 1 — Own the Product Boundary

### 4. Lock license and provenance — **SATISFIED — MISSIONS 017 + 037 + 038**

Preserve MIT/copyright, add `OPEN_SOURCE_CREDITS.md`, visible credit, inherited-module provenance, and shipped dependency-license inventory. Mission 017 added the visible credit and copyright/license surface in the cockpit About section. Mission 037 added `OPEN_SOURCE_CREDITS.md` at the repo root (MIT/copyright, text-only AI Counsel attribution, curated direct-dependency licenses), the three tool-generated inventories in `docs/modelmix/licenses/` (Python `pip-licenses`, frontend `license-checker`, Rust `cargo-license`), and a one-line About-section pointer to the credits file on the real GitHub URL. Mission 038 removed the GPLv3 `yake` runtime dependency from `pyproject.toml`/`uv.lock`/imports and replaced it with a stdlib-only RAKE implementation in `backend/search.py`, regenerated the Python inventory (no `yake`), updated `OPEN_SOURCE_CREDITS.md`, and added the first tests for `extract_search_keywords`.

### 5. Lock chassis policy — **SUBSTANTIALLY SATISFIED**

Keep the current ModelMix repo. Upstream is a reference/selective-fix source, not a live product parent. ModelMix owns orchestration/UI.

### 6. Create ModelMix-owned backend boundary — **SUBSTANTIALLY SATISFIED**

Dedicated ModelMix domain/session/run/seat/Moderator/orchestration/event/persistence/capability/telemetry seams.

## PHASE 2 — Define the Core Contracts

### 7. Define domain objects — **SATISFIED — MISSION 043**

Session, Run, Seat, Message, Moderator, Provider/Model reference, ProviderCapabilities, UsageRecord, RunEvent, Artifact/reference, Error/terminal result, with schema versions. Documented from code in `docs/modelmix/domain-objects.md`. Note: `Artifact/reference` is not implemented in this alpha slice and is recorded as such; `Error/terminal result` maps to the persisted message status/error/reason and run status.

### 8. Define context isolation policy — **SATISFIED — MISSION 009**

Workers see only user/authorized shared context plus their own seat history. Moderator sees authorized user/context and current worker outputs. Seat history belongs to the seat, not the selected model.

### 9. Define run state machine — **SATISFIED — MISSION 043**

Created, dispatching, workers_running, moderating, completed, partially_completed, cancelled, failed, timed_out; define partial Moderator policy, Stop, persistence, retries, and UI terminal states. **Mission 013** adds the wall-clock `timed_out` outcome: `run_failed` / `seat_failed` / `moderator_failed` with `reason: "timeout"` through the existing event seam; retries remain open.

Documented from code in `docs/modelmix/run-state-machine.md`. **Vocabulary correction:** the punch-board token `partially_completed` does not match the implemented value, which is **`partial`** (`persistence.py` `TERMINAL_STATUSES`; `registry.py:314`). The code value `partial` is authoritative. Retries remain open.

### 10. Define ordered event contract — **SATISFIED**

SSE events carry `run_id`, monotonic `seq`, actor/seat identity, type, and payload/timestamp; reconnect uses replay cursor.

### 11. Define persistence boundary — **SATISFIED — MISSION 008**

Keep JSON for alpha behind a ModelMix interface; add schema versioning and atomic writes; store canonical messages with seat/audience/role metadata; store immutable run snapshots; preserve partial results; **do not migrate to SQLite now**.

**PASS:** restart reconstructs a session without relying on in-memory run state.

### 12. Define provider capability matrix — **SATISFIED — MISSION 043**

Track only capabilities needed to prevent false UI promises: chat, streaming, known limits, usage, inherited tool/vision/file support, auth, local/remote, cancellation, pricing support. Documented from code in `docs/modelmix/provider-capability-matrix.md`. Capabilities not implemented anywhere (streaming for all but `openai-oauth`, per-query costs, vision/file/tools in the alpha run path) are explicitly marked absent rather than advertised.

### 13. Define privacy/data-routing rules — **SATISFIED — MISSION 043**

Document what each provider may receive; credentials are references; no raw secrets in logs/frontend/session JSON; cross-provider forwarding is intelligible. Documented from code in `docs/modelmix/privacy-and-data-routing.md` (credential store backends, settings-API/credential-store separation, OAuth single-flight refresh, seat-scoped history, and the bounded visible-only Moderator fan-in).

## PHASE 3 — Build the Smallest Real Engine

### 14. Build deterministic mock provider - **SATISFIED**

Support normal response, stream, slow stream, failure, timeout, rate limit, 
cancellation, malformed event, missing usage, duplicate/out-of-order fixtures.
**Mission 046** delivers this as one shared, composable library in
`backend/tests/mock_providers.py` (ten factory functions implementing
`LLMProvider`), each proven by its own direct test, with one test
demonstrating a real `multiplex_workers` flow. Existing tests are not
migrated; the library is additive infrastructure for future ModelMix tests.
### 15. Build NON-STREAMING Mix vertical slice first — **SATISFIED — MISSION 009**

Two isolated workers → complete bounded outputs → Moderator → persisted session. Mission 009 adds bounded seat-scoped continuation while preserving the same isolated worker and Moderator flow.

### 16. Prove failure + cancellation with the same loop — **SUBSTANTIALLY SATISFIED**

One/both worker failure, Moderator failure, timeout/rate limit/cancellation/partial outcomes modeled honestly. **Mission 013** proves run/seat/Moderator timeouts share the same loop and cancellation machinery as failure and explicit cancel, with a no-late-writes guarantee verified in both the journal and durable session. **Mission 023** proves cancellation stays terminal and bounded even when a seat/Moderator provider does not honor cancellation promptly (deterministic stall tests; `run_cancelled` within `CANCEL_GRACE_SECONDS`). Persisted restart case remains tied to item 11.

### 17. Add basic spend/runtime guardrails — **CLOSED (visibility: 044/045, warning: 050/051, gate: 052/057)**

Max workers, run timeout, Stop, seat-history character budgets (Mission 010 partial), optional cost/token ceiling, no automatic provider/model substitution without permission. **Mission 013** adds the ModelMix-owned wall-clock bounds: `RUN_TIMEOUT_SECONDS = 600` enforced by `RunRegistry`, `SEAT_TIMEOUT_SECONDS = 300` enforced per worker seat and for the Moderator phase, with honest `reason: "timeout"` terminal events. **Mission 019** enforces the output guardrails behind module constants (`guardrails.py`): `WARNING_OUTPUT_THRESHOLD_CHARS = 20_000` and `HARD_OUTPUT_CAP_CHARS = 40_000`, with a one-shot `seat_output_warning`/`moderator_output_warning` on first crossing and an exact-cap deterministic truncation that stops consuming the stream and terminates as `seat_completed`/`moderator_completed` with `finish_reason: "modelmix_output_cap"` (never `seat_failed`, never colliding with provider reasons). **Mission 020** makes both
thresholds configurable per request through `POST /api/modelmix/runs/stream`:
optional `warning_threshold_chars`/`hard_cap_chars` on `TwoWorkerRequest`,
defaulted to the module constants when omitted, bounded to
`guardrails.MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`,
cross-checked (`hard_cap_chars >= warning_threshold_chars`), and rejected as
422 **before** any provider is resolved or called. The pair rides the exact
`seat_timeout` chain (`registry.start → _run → _run_phase →
multiplex_workers/run_moderator`); enforcement logic and event payloads are
unchanged. **Mission 021** closes the frontend slice: a Guardrails section in
the cockpit Settings saves/clears a local `modelmix.guardrails` override
(validated to the same bounds and cross-check so the UI never offers a
payload the server would 422), `send()` includes both fields only when a valid
override exists, the per-seat warning renders live in the footer as a plain
informational line, and worker seats now report honest finish captions
including "Output capped by ModelMix". The provider/account usage warning
remains open because no authoritative quota data exists to compare against;
the cost/token ceiling is the remaining item-17 sub-work. **Mission 044**
delivers the dollar-visibility half: real OpenRouter per-token pricing is
preserved from `get_models()`, cached, and multiplied by real per-seat usage
tokens at the Mission 015 capture point to attach an honest `cost_usd` to
`seat_completed`/`moderator_completed` events and persisted messages —
computed only for `openrouter:`-prefixed models with cached pricing and real
token counts, entirely absent (never 0, never estimated) in every other case.
No spend cap or enforcement was built: what an exceeded dollar budget should
*do* is a separate, undecided product question. **Mission 045** closes the
frontend half: ``cost_usd`` now flows through the full frontend state lifecycle
(no-clobber capture, hydration, archiving) and renders as a standalone ``Cost``
footer row only when a real finite figure exists - sub-cent values show four
decimals so a real cost never displays as a misleading ``$0.00`` - with no
cross-seat aggregate and no ``unavailable`` placeholder. The visibility half is
now done end to end; any actual dollar spend-cap enforcement remains a
separate, explicitly undecided product question. **Mission 050** adds a
per-seat spend warning (informational only, no enforcement): a module
constant ``WARNING_COST_USD_THRESHOLD = 0.10`` and, whenever a completed
seat/moderator's real ``cost_usd`` strictly exceeds it, one
``seat_cost_warning``/``moderator_cost_warning`` event firing alongside the
already-computed completion (never blocking or altering it). ``None`` cost
(non-OpenRouter or uncached) never warns. This fires once at completion per
seat — not mid-stream, not a cumulative session total — exactly matching the
telemetry honesty rules. Enforcement/cutoff and cumulative session-cost
tracking remain separate, explicitly undecided future work. **Mission 051**
closes the frontend visibility half: `seat_cost_warning`/`moderator_cost_warning`
are captured in live seat state (`seat.costWarning = { cost_usd, threshold }`,
mirroring the `outputWarning` pattern exactly) and rendered as a plain,
non-alarming `Cost notice` footer row reusing the existing `formatCostUsd`
(sub-cent values never show as `$0.00`), live-only — not persisted, not
threaded through hydration/history/archive, matching `outputWarning`'s scope.
Item 17's spend visibility work is now complete end to end; enforcement/cutoff
and cumulative session-cost tracking remain explicitly separate, undecided
future work. **Mission 052** adds the first dollar-cap enforcement (backend): a
per-request `spend_limit_usd` (+`confirm_over_budget` flag) on
`TwoWorkerRequest`. Before the next run starts, the gate loads the session's most
recent run and, per-seat only (never aggregated), compares its real,
already-persisted `cost_usd`; if any seat's real cost exceeds the limit and the
request did not confirm, the run is rejected with HTTP 402 naming the seat and
actual cost. `None` cost (non-OpenRouter/uncached) is never treated as
over-budget, `confirm_over_budget: true` bypasses the check, and omitting
`spend_limit_usd` is byte-for-byte unchanged. It reads only previously computed
facts from the existing `load_session` — no `should_warn_cost` change, no
server-side persistence of the limit, no schema bump, no new dependency. Mission
053/054 (per-request temperature/moderator guidance, frontend) land on top had
already shipped before 052 was retroactively renumbered. **Mission 057** closes
the frontend half: a new `loadSpendLimit`/`saveSpendLimit`/`clearSpendLimit`
triple in `modelmixBehavior.js` (validating `value > 0`, matching the backend's
`gt=0` bound exactly, same defensive storage discipline as every existing
settings module) powers a dollar-amount input with save/clear pair in the
Behavior Settings section; `send()` includes `spend_limit_usd` in the request
body only when a valid saved value exists (key genuinely absent otherwise,
matching the absence-not-null discipline for every other optional field); when
`startModelMixRun` rejects with HTTP 402, the real backend message (which seat,
actual cost) renders in a dedicated confirmation UI with an explicit "Proceed
anyway" button that resends the identical original request body plus
`confirm_over_budget: true` — never auto-retrying, never persisting the
confirmation flag. Frontend-only — no backend changes. Item 17 is now complete
end to end: visibility (044/045), warning (050/051), and gate (052/057) all
real backend AND frontend.

## PHASE 4 — Streaming

### 18. Add normalized provider streaming interface — **SATISFIED**

### 19. Multiplex streams into one ordered SSE run feed — **SATISFIED**

### 20. Stream Moderator — **SATISFIED**

## PHASE 5 — Build the Actual ModelMix UI

### 21. Build browser-first three-panel cockpit — **SATISFIED**

Worker A | wider Moderator | Worker B; full-height chat surfaces; independent scrolling; clear states.

### 22. Bind UI to durable run/session state — **SATISFIED — MISSION 008**

Hydrate from persisted canonical messages, subscribe to existing events, replay from the durable last sequence, and suppress duplicates. Reload/reopen and backend restart reconstruction are covered by Mission 008.

### 23. Add Stop behavior — **SATISFIED**

One visible Stop action; separate fixed Send and Stop controls; honest partial-state display.

### 24. Build thin top controls — **CLOSED (Missions 012/016/017/029/031)**

ModelMix, Mode, Models, Session, Settings, compact overflow as needed. No dead controls. Mission 012 delivered the separate New Session control (disabled while a run is active) and cleared the local session key on activation. Mission 016 delivered the compact persistent top strip (brand, inert `Mode: Mix` label, session status, New Session moved up out of the composer, `Run`/`Last sequence` behind a Details disclosure that is off by default, Back to Council) and CSS-driven per-panel Collapse/Maximize/Reset view controls that hide panels from layout without unmounting them. Mission 017 delivers the Settings surface as a gear entry opening an in-app overlay (About / Providers / Defaults).

Mission 029 replaced the inert mode label with the persisted Mix / Compare
selector. Mission 031 adds Solo and preserves the existing active-run lock, so
the mode control now covers all three delivered conversation modes and this
item is closed.

### 25. Add minimal telemetry — **SUBSTANTIALLY SATISFIED — MISSIONS 015/018**

State, elapsed time, provider-reported tokens where available, labeled estimates, reliable per-call cost only. Confidence colors represent data quality, not danger.

Mission 015 landed the truth layer: wall-clock `ts`, persisted provider-reported `usage`/`finish_reason`, and `started_at`/`completed_at` timing. Mission 018 renders it honestly in the cockpit: compact per-seat footers for the live turn only — usage labeled `authoritative (provider-reported)` (via the `describeUsage` vocabulary) showing the provider-reported total token count (`total_tokens`/`totalTokenCount`, formatted `<n> tokens`) when it is a finite number, else the raw provider key names as fallback, or honest `unavailable`, elapsed time labeled `(calculated)`, the Moderator-only `finish_reason`, and the raw start/end range. No fabricated estimates, no fake normalized percentages; each seat's provider-reported usage stays opaque and un-normalized. **Deferred, explicitly noted follow-ups:** per-historical-turn telemetry footers (archived turns currently render zero footers even though the data is captured) and reliable per-call cost/pricing wiring (deliberately out of scope here — cost fields are never guessed or displayed).

### 26. Add provider/settings UX sufficient for alpha — **CLOSED (Missions 055 + 056)**

**Mission 056** (closing the credential fold-in) adds native OAuth connect/disconnect for the remaining three providers (`xai-oauth`, `openai-oauth`, `github-copilot`) directly in the cockpit Settings "Providers" section, reusing the existing uniform device-code flow (`POST /api/oauth/{id}/start` returns `user_code` + `verification_uri`/`verification_uri_complete`; the server polls; the frontend polls `GET /api/oauth/{id}/status?session_id=...` on a bounded 2.5s interval until `complete`/`error`/`expired`, then stops; `DELETE /api/oauth/{id}` disconnects). Connected status is the real `xai_oauth_connected`/`openai_oauth_connected`/`github_copilot_connected` field from `GET /api/settings`. Polling is bounded to the session's `expires_in` and every interval is cleared on unmount — no React leak. All three routes are the existing `_require_admin`-guarded ones; zero backend changes. This closes item 26: no provider (simple or OAuth) requires a trip to Council settings for anything ModelMix needs. Mission 007 completed searchable configured selectors. Mission 017 adds the cockpit Settings overlay with read-only provider status (derived from the now-exported `configuredSources`) and saved default seat models. Credential/endpoint/settings entry flow remains in the Council route and remains open. **Mission 053** adds real ModelMix-native per-request run settings: optional `temperature` (0.0–2.0, validated) and optional `moderator_guidance` (max 2000 chars, appended additively after `MODERATOR_INSTRUCTIONS`, never replacing it), both threaded through `TwoWorkerRequest` → registry → orchestrator/moderator to all four real provider call sites; `None` means byte-for-byte unchanged behavior. Frontend controls and persistence remain open. **Mission 054** closes the frontend half: a new Settings "Behavior" section renders a temperature input (0.0–2.0, step 0.1) and a moderator-guidance textarea (max 2000 chars, live remaining count), each independent and saved via the `modelmixBehavior.js` localStorage module; `send()` includes `temperature`/`moderator_guidance` only when a valid saved value exists (omitted, never `null`). Both settings are local-preference only, persisted nowhere server-side. **Mission 055** folds native credential entry for ModelMix's 12 simple (non-OAuth) providers into the cockpit Settings "Providers" section — material progress on the credential/endpoint entry item that previously required a trip to Council settings. Each of the 12 in-scope providers (OpenRouter; OpenAI, Anthropic, Google, Mistral, DeepSeek, Groq, NVIDIA; OpenCode Zen+Go sharing one key; Ollama base URL; custom endpoint name/url/key) gets a write-only input, a "Test" button wired to the exact existing `_require_admin`-guarded test endpoint (`test-provider`, `test-openrouter`, `test-opencode`, `test-ollama`, `test-custom-endpoint`) that renders the real returned message, and a "Save" that PUTs only the edited field(s) via the existing partial-merge `PUT /api/settings`. Saved values are never pre-filled or echoed; the connected/not-connected `configuredSources` READ status stays and is refreshed after a successful save. No backend change. OAuth providers (xAI, ChatGPT, GitHub Copilot) are explicitly out of scope and remain a separate, later mission still linked to Council settings.

## PHASE 6 — Conversation Modes and Persistence UX

### 27. Add Solo — **CLOSED (Missions 030 + 031)**

Mission 030 makes `worker_b_model` optional end to end so a run can be Worker A
alone. Backend changes: `TwoWorkerRequest.worker_b_model` is now
`Optional[str]` (default `None`), threaded through `RunRegistry.start` /
`_run` / `_run_phase` and `orchestrator.multiplex_workers` (active seats computed
locally; the now-unused `SEATS` constant removed); the route rejects the
worker_b-absent + moderator hybrid with 422 **before** any provider resolver
call; persisted `models` for a Solo run carry `worker_a` plus `moderator: None`
with the `worker_b` key absent; `persistence._validate` statically relaxes the
structural guard from an exact three-key set to a subset with `worker_a` always
present non-empty and `worker_b` never `None`/empty (Mix/Compare/old shapes all
still validate — proven by tests). Zero changes to `history.py` (Solo turns
already produce no worker_b message, so `build_seat_history` never reuses one).
Validation for Mission 030: new `test_modelmix_solo_mode.py` (7
route/orchestration tests) + new persistence validator tests; backend **460
passed**, `ruff` clean; frontend **130 passed** / build / lint green.

Mission 031 completes the frontend. `solo` is a valid persisted third mode; the
composer renders only Worker A's selector and requires only its model; requests
omit both `worker_b_model` and `moderator_model` as keys. Moderator and Worker B
panels remain mounted but CSS-hidden, and Worker A fills the cockpit through the
existing single-column visual treatment. Mode visibility does not overwrite
panel-view state; a maximize target on a hidden seat is neutralized while Solo
is active so the cockpit never becomes blank. New `ModelMixSendSolo.test.jsx`
adds 8 tests. Observed validation: frontend **138 passed** / build / lint green;
backend workspace-temp rerun **460 passed in 35.32s** after the exact command
reproduced the known inaccessible default-temp `WinError 5`. Item 27 is closed.

### 28. Add Compare — **CLOSED (Missions 028 + 029)**

Mission 028 verified the existing no-moderator two-worker backend path end to
end through the real HTTP route (`POST /api/modelmix/runs/stream` with
`moderator_model` omitted): both workers stream with zero moderator events,
`run_completed "completed"`; one worker fails -> `"partial"` with the persisted
session reflecting the failed seat; both workers fail -> observed as-shipped
`run_completed "partial"`; multi-turn isolation holds moderator-less with the
dead `seat_histories["moderator"]` key never leaking; per-worker guardrails
apply; cancellation reaches `run_cancelled` mid-stream; and reopening a
moderator-less session reconstructs with no moderator message
(`models["moderator"]` persists as `None`, tolerated). New
`test_modelmix_compare_mode_backend.py` (7 tests).

Mission 029 delivers the rest. Part 1 backend status fix: when **both** workers
fail with no moderator, `multiplex_workers` now reaches `run_completed` with
`status="failed"` instead of `"partial"` (point-3 test now asserts `failed`);
the moderator path is untouched. Part 2 frontend Compare mode: the inert top-bar
`Mode: Mix` span becomes a real `select.modelmix-mode-select` (Mix / Compare),
persisted via new `modelmixMode.js`; in Compare mode the Moderator selector is
hidden, `moderator_model` is omitted from the request body, and the center
moderator panel is hidden-but-kept-mounted. Validation: backend **448 passed** +
`ruff` clean; frontend **130 passed** / build / lint green. One existing
frontend top-bar test was updated (the mode span had to become a real control)
and is the sole modified existing test. Reports:
`028-compare-backend-verification.md`, `029-compare-mode-status-fix-and-frontend.md`.

### 29. Finalize Mix multi-turn session behavior — **PARTIAL — MISSIONS 009/011/012/048/049**

Independent bounded seat histories, Moderator history, hot-swap continuity, and context without cross-seat leakage are implemented. Mission 011 displays completed prior turns above the live turn in each cockpit panel; Mission 012 makes archived turns carry their real prompt/models and adds the New Session reset control. **Mission 048** adds manual session listing and deletion (backend): ``list_sessions()`` returns lightweight newest-first summaries and ``delete_session()`` removes a session file via the existing validated-id path, exposed as ``GET /api/modelmix/sessions`` and ``DELETE /api/modelmix/sessions/{session_id}`` (409 while a run in that session is active, 404 if absent). Retention/delete basics are now complete end to end. **Mission 049** adds the session manager UI: a Sessions section in the Settings shell lists real sessions (id, created/updated time, message count) and deletes each with an explicit two-click confirmation; a 409 shows the real backend error, deleting the currently-open session resets the cockpit via the existing ``startNewSession``, and a deleted row is removed from the list. Automatic/scheduled retention remains explicitly a separate, undecided future item.

## PHASE 7 — Security Hardening for Alpha

### 30. Verify credential storage in actual packaging model — **CLOSED (current-model half: Missions 026/027; Tauri/frozen half: Missions 033/034)**

Current-model half (Missions 026/027): real Windows per-user ACL hardening of
`data/credentials.json` via `icacls "<path>" /inheritance:r /grant:r
"<current-user>":F` after each atomic write (Mission 026, proven by
`test_windows_write_invokes_icacls_args`), plus automatic **once-per-process
remediation** of a pre-existing unhardened file on its first touch, read or
write (Mission 027, proven by
`test_read_triggers_remediation_on_existing_unhardened_file`). No new
dependency (`subprocess` + `icacls` only); non-Windows/containers stay a
logged no-op, never a write-path crash.

Tauri/frozen half (Missions 033/034): Mission 033 ran the **real PyInstaller
frozen executable** and, inside it, proved a real Windows keyring sentinel
round-trip across a genuine process restart (distinct PIDs), the file
credential backend across a second restart, and the expected non-inherited
current-user Windows ACL (`icacls` proof) — no simulation. Mission 034 then
fixed the credential storage **location** for frozen builds:
`_internal\data\credentials.json` → `%LOCALAPPDATA%\ModelMix\credentials.json`
(frozen), repo `data/` byte-identical when not frozen.

### 31. Harden local backend boundary — **CLOSED (Mission 025)**

Mission 025 closed the confirmed SSRF → stored-credential-exfiltration path
(`POST /api/settings/test-custom-endpoint`) by adding
`dependencies=[Depends(_require_admin)]` in `backend/main.py` to **20
credential-sensitive endpoints** (16 required + 4 judgment-call extensions),
with the full, unchanged `_require_admin` semantics: Bearer token required when
`LLM_COUNCIL_ADMIN_TOKEN` is set, otherwise loopback-peers-only
(`127.0.0.1`/`::1`/`localhost`) plus forwarded-header spoofing protection.
Evidence: `backend/tests/test_admin_guard_credential_endpoints.py` (27 tests)
and the endpoint-by-endpoint audit table in
`docs/modelmix/025-harden-local-backend-boundary.md`.

Deliberately-deferred findings from Mission 025, carried forward on the board
so they are not lost (still open, NOT fixed by this or any later mission):

- **31a. `_dev_cors_regex` over-permissive origin matching.** In
  `backend/main.py`, `_dev_cors_regex` uses `(?:\d{1,3}\.){3}\d{1,3}`, which
  matches **any** dotted-IPv4 origin on **any** port — no private/loopback-range
  restriction. Flagged in Mission 025 as a review follow-up; still real, still
  not fixed. Tracked as its own item.
- **31b. Custom-endpoint URL allow-listing.** The arbitrary
  custom-endpoint-URL SSRF is now admin-gated, but a loopback-local attacker
  (or a compromised local process) could still point the custom-endpoint URL at
  an internal host. Mission 025 recommended a separate URL allow-list review;
  that recommendation also remains open.

### 32. Add basic structured observability — **CLOSED (Mission 040)**

Mission 040 delivered durable structured logging. `backend/logging_config.py::configure_logging()`
adds a `RotatingFileHandler` (5 MB, 3 backups) at
`<user_data_dir>/logs/modelmix.log` with a
`%(asctime)s %(levelname)s %(name)s: %(message)s` format, preserves the console
(stderr) handler, and honors `LLM_COUNCIL_LOG_LEVEL` (default `INFO`). The log
file receives the same Windows per-user ACL hardening as the credentials file,
with the `icacls` logic de-duplicated into shared `user_data_dir.harden_user_dir()`
(credentials path unchanged). A credential-leak audit across all 89 `logger.*`
call sites found no secret interpolation. See `040-durable-structured-logging.md`.

## ALPHA GATE

### 33. Alpha acceptance test — **BACKEND-PROVABLE COVERAGE COMPLETE — MISSIONS 022/023**

Launch; three panels; configure A/B/Moderator; stream both workers; stream Moderator; cancel; survive worker failure; reopen session; multi-turn isolation; honest telemetry; no credential leak.

Mission 014 removed the reachability blocker: a production build now serves the
cockpit at `/modelmix` and offers a visible Council sidebar link, so the alpha
acceptance launch can actually begin from a built app rather than a dev server.

Mission 022 proves items 4–11 (the backend-provable checklist) as integration
tests through the real HTTP surface in
`backend/tests/test_modelmix_alpha_acceptance.py` (7 tests, 395 backend total).
Items 1–3 are UI-bound and remain covered by prior-mission evidence (014
launch, 016 three panels, 007/016 configure A/B/Moderator). A final
live-provider manual launch pass is still the remaining alpha step.

Mission 022 additionally disclosed one genuine robustness gap found during the
cancel verification: a sub-millisecond cancel window (cancel fires right as a
seat emits) can leave the run stuck `active` until the 600s run timeout, with
`_run_phase` blocked in the `multiplex_workers` generator-`finally` gather and
one seat's provider generator never receiving `CancelledError`.

**Mission 023 fixed that race:** cancellation cleanup is now bounded by
`CANCEL_GRACE_SECONDS = 5.0` (`timeouts.await_cancellation_grace`), replacing
the unbounded gather in `multiplex_workers`' `finally`; the Moderator phase in
`registry.py` awaits its task through `asyncio.shield` so a slow-to-cancel
Moderator can no longer hang `_run_phase` indefinitely. A cancel now reaches
terminal `run_cancelled` within the bound even when every seat/Moderator
absorbs cancellation. Proven deterministically by
`backend/tests/test_modelmix_cancel_race.py` (8 tests, fast-cancel regressions
assert the old behavior is byte-for-byte unchanged); see `023-cancellation-race-fix.md`.

**Nothing below this line may delay the alpha gate.**

## PHASE 8 — Desktop Packaging

### 34. Package single-window app with Tauri 2 — **SUBSTANTIALLY COMPLETE (Missions 032–035) — still OPEN on MSI bundle, code signing, CSP hardening, and dynamic ports**

Mission 032 added the standard Tauri 2 `src-tauri/` shell and directly observed
the existing ModelMix cockpit in a native Windows window via `cargo tauri dev`.
The shell reuses the Vite frontend and separately started backend; it contains
no Python sidecar or backend-launch configuration. Mission 033 separately
proved a Windows PyInstaller `onedir` backend launched directly from an
isolated copy: the frozen executable served the real API/MCP routes, retrieved
and cleared a fake keyring sentinel across restart, preserved and cleared a
second fake file sentinel across restart, and produced the required
non-inherited current-user FullControl ACL. The isolated credential file was
deleted with the mission runtime and repository data remained unchanged.
Mission 033's evidence also confirmed the frozen path defect —
`_internal\data\credentials.json` — that Mission 034 fixes with a frozen-aware
user data directory.

Mission 034 closes the credential/data-path correctness finding: a new
`backend/user_data_dir.py` resolves the repo `data/` folder when not frozen
(byte-for-byte unchanged dev behavior) and `%LOCALAPPDATA%\ModelMix` when
frozen (executable-dir fallback + warning if `LOCALAPPDATA` is absent);
`credentials.json`, `settings.json`, and persona data all derive from it. The
mechanism is proven by simulation; a real frozen-build run observing the
actual resolved path is still required.

Mission 035 wires the frozen backend into the Tauri app as an app-spawned
process (decided: `bundle.resources` folder recursive-copy, not
`externalBin`/sidecar, because the onedir `_internal/` directory has no
documented sidecar path). Dev and a real NSIS production install both spawn
the bundle with no manual Python; the window stays hidden until `/api/health`
answers (cold 2.03-10.17 s across runs on this box, 30 s cap); zero orphaned
`modelmix-backend` processes on graceful close and on force-kill (Win32 Job
Object `KILL_ON_JOB_CLOSE`); broken-backend states show a native error dialog
and exit cleanly; production webview origin `https://tauri.localhost` is
allowed via the backend's documented `FRONTEND_HOST` env config at spawn.
Full evidence: `docs/modelmix/035-tauri-sidecar-wiring.md`.

Remaining known gaps on item 34 that were deliberately out of scope for each
mission: MSI bundle, code-signing/installer polish, CSP hardening (currently
`null`), dynamic port discovery, and a real frozen-build credential-path run.

Mission 047 replaces the `null` CSP in `tauri.conf.json` with a real policy
(`default-src 'self'`; `script-src 'self'`; `style-src 'self' 'unsafe-inline'
https://fonts.googleapis.com`; `font-src 'self' https://fonts.gstatic.com`;
`img-src 'self' data:`; `connect-src 'self' http://localhost:8001
http://127.0.0.1:8001 http://tauri.localhost:8001`) so the shipped webview no
longer runs with no script/style/connect restrictions. The production
`connect-src` origin `http://tauri.localhost:8001` is required because the
frontend builds its backend URL from `window.location.hostname` (which is
`tauri.localhost` in the packaged app, per `FRONTEND_HOST` at
`lib.rs:223`). CSP hardening is therefore addressed. Item 34 remains **OPEN**
only on MSI bundle, code signing, dynamic ports, and the real frozen-build
credential-path run. The CSP change itself requires the user's runtime
confirmation (fonts render, real Mix run streams, zero CSP console errors) in
both `cargo tauri dev` and a launched production build before it is
considered fully proven — see `047-tauri-csp-hardening.md`.

### 35. Measure before optimizing — **OPEN**

## PHASE 9 — Research and Workspace Features

### 36. Add Moderator-only web/document access first — **OPEN**

### 37. Add workspace/context permissions gradually — **OPEN**

## PHASE 10 — Advanced Telemetry

### 38. Add provider-account usage only where real — **OPEN**

## PHASE 11 — Detachable Windows

### 39. Define authoritative shared-state owner — **OPEN**

### 40. Add one pop-out panel — **OPEN**

### 41. Generalize detach/re-dock — **OPEN**

## PHASE 12 — Advanced Modes

### 42. Revisit compact handoffs — **OPEN**

### 43. Deep Mix — **OPEN**

## PHASE 13 — Android

### 44. Design mobile interaction model separately — **OPEN**

### 45. Validate Tauri Android packaging — **OPEN**

## PHASE 14 — Cleanup and Upstream Maintenance

### 46. Prune dead Council/Advisor/debate code — **CLOSED**

Mission 041 produced the three-category dead-code inventory
(`041-dead-code-inventory.md`). Mission 042 performed the removal of every
confirmed-unreachable item, each re-verified by whole-repo grep at removal
time (zero references beyond the own definition). Removed: three `config.py`
legacy constants (`OPENROUTER_API_KEY`, `COUNCIL_MODELS`, `CHAIRMAN_MODEL`),
`settings.AVAILABLE_MODELS`, four `credentials/ids.py` symbols
(`SECRET_ID_TO_SETTINGS_FIELD`, `OAUTH_CONNECTED_FLAGS`, `api_secret_id`,
`oauth_secret_id`, plus the now-orphaned `Optional` import),
`store.secret_id_for_settings_field`,
`DocumentLimits.document_timeout_seconds`, three dead `query_models_parallel`
wrappers in `council.py`/`ollama_client.py`/`openrouter.py`,
`openrouter.fetch_models`, `search._fetch_with_jina_sync`,
`oauth.types.parse_stored_oauth_credential`, `keyring_backend._entry`, and
the `@types/react-dom` devDependency (lockfile updated). Left untouched per
the mission boundary: all FastAPI routes, Pydantic/dataclass fields, the
intentional async-generator `yield` in `providers/base.py`, pytest fixtures,
and ambiguous `@types/react`. New findings reported for a future cleanup:
`openrouter.BROKEN_MODELS` and `search.get_sync_client` became orphaned as a
consequence of the removals. Validation: backend `485 passed`, frontend `138
passed`, build + lint clean. See `042-remove-confirmed-dead-code.md`.

### 47. Establish selective upstream watch — **OPEN**

---

# Explicit Alpha Non-Goals

Detachable windows; Android; Deep Mix; 5-worker cockpit; mandatory structured compact handoffs; MCP; connected-service actions; advanced workspace permission matrix; account-wide quota dashboard; SQLite migration; formal debate; autonomous agent planning; automatic provider rerouting; elaborate personas; giant evidence/conflict dashboard; elaborate desktop updater polish.

# Locked Architectural Calls

1. Repository: keep current ModelMix repo.
2. Upstream: reference/selective-fix source, not live product parent.
3. Default: Worker A + Moderator + Worker B.
4. Workers are independent witnesses.
5. Transport: SSE.
6. Streaming: multiplexed ordered run feed.
7. Context: seat-scoped projections, not one shared transcript.
8. Moderator MVP input: complete bounded worker outputs.
9. Persistence MVP: versioned atomic JSON behind interface.
10. Backend alpha: single worker/process unless run-state design changes.
11. UI alpha: single-window browser/React cockpit.
12. Desktop shell: Tauri 2 after browser alpha.
13. Pop-outs: post-alpha.
14. Android: post-Windows, separate UX.
15. Telemetry MVP: per-run/per-call truth first.
16. Security: preserve verified inherited protections and harden desktop-local boundary.
17. No hidden chain-of-thought.
18. No Stage 2 peer ranking/debate.
19. No automatic cross-worker context leakage.
20. Simple first. Power when requested.

## UX Lock — 2026-08-27 17:35 CT

Three full-height conversation surfaces. Thin chrome.

Send and Stop are separate fixed adjacent controls:
- idle/composing: Send active, Stop disabled;
- running: Send disabled, Stop active;
- never morph Send into Stop at the same cursor location.

## Feature Lock — Usage Warnings and Output Guardrails

### Provider / Account Usage Warning

Toggle; configurable warning percentage; authoritative percentage only when truly available; otherwise labeled ModelMix-tracked/estimated; warn once; soft by default.

### Excessive Output Token Warning

Separate toggle; configurable absolute and/or known-max percentage threshold; warn once; estimates labeled. The configurable threshold is now realized as **character** counts (not tokens — no reliable token-equivalence data exists) via the Guardrails settings section (Mission 021), saved locally and sent per request as `warning_threshold_chars`.

### Hard Output Cap

Separate toggle; configurable threshold; stop at cap or closest enforceable boundary. Realized as an exact deterministic character cap (Missions 019–021), user-configurable via the Guardrails settings section and sent per request as `hard_cap_chars`.

Terminal state must distinguish:
- normal completion;
- user cancellation;
- provider/model termination;
- ModelMix hard-cap termination.

Hard cap is **not post-alpha by default**. Wire it when settings/run-control reaches output limits.

## Immediate Next Engineering Gap

The output guardrails are now enforced for real output (Mission 019), the
two thresholds are configurable per request (Mission 020), and the cockpit
makes them user-configurable with local persistence (Mission 021): a
Guardrails section in Settings saves/clears a local `modelmix.guardrails`
override (bounded 100–200_000 and cross-checked like the server) that
`send()` attaches to every run request, the one-shot warning renders live in
the seat footer as a plain informational line
(`Approaching output limit: 22,451 / 20,000 chars`), and every seat — workers
included — reports its honest `finish_reason` caption, with "Output capped by
ModelMix" for capped runs. No running value is ever persisted server-side, and
the frontend's static 20k/40k default help text is explicitly labeled
non-live. The provider/account usage warning stays explicitly open
because no authoritative quota/rate-limit data exists anywhere to compare
against. Mission 015's telemetry truth layer is rendered as compact per-seat
footers (Mission 018) with no telemetry dashboard, usage kept opaque and
un-normalized, and no fabricated estimates; two follow-ups remain explicitly
deferred: per-historical-turn telemetry footers and reliable per-call cost
wiring. Item 24 is now closed: the Settings surface shipped as the Mission 017
gear entry, Mission 029 delivered Mix / Compare selection, and Mission 031
completed the control with Solo.
