# ModelMix Mission Record Index

Updated: 2026-09-01 CT

This index reconciles completed implementation missions with the canonical engineering records in this repository.

Authoritative build order and roadmap: [`PUNCH-BOARD.md`](PUNCH-BOARD.md)  
Current implementation overlay: [`ENGINEERING-PROGRESS.md`](ENGINEERING-PROGRESS.md)

Mission prompts and worker responses may also exist in the ModelMix project Library. Repo mission reports are the canonical engineering records for state accepted into current `main`; Library copies preserve dispatch/response history and additional project provenance.

| Mission | Prompt owner / route at dispatch | Result | Canonical repo report |
|---|---|---|---|
| 001 | Claude Code | PASS | `001-baseline-architecture-spike.md` |
| 002 | Codex | PASS | `002-first-streaming-slice.md` |
| 003 | Codex | PASS | `003-event-journal-reconnect.md` |
| 004 | Codex | PASS | `004-first-frontend-observer.md` |
| 005 | Codex | PASS | `005-moderator-backend-phase.md` |
| 006 | Codex | PASS | `006-three-panel-cockpit-slice.md` |
| 007 | Codex-labeled historical prompt; final implementation/verification completed through ChatGPT Work after repository recovery | PASS | `007-searchable-model-discovery-controls.md` |
| 007.5 | Codex | **PASS** | `007.5-mcp-2-security-compatibility.md` |
| 008 | Codex isolated checkout | **PASS** | `008-durable-persistence-cockpit-hydration.md`; accepted on `main` |
| 009 | Codex | **PASS (LOCAL)** | `009-seat-scoped-multi-turn-context.md` |
| 010 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `010-seat-history-budget.md` |
| 010.5 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `010.5-frontend-test-runner-interlock.md` |
| 011 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `011-multi-turn-cockpit-display.md` |
| 012 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `012-session-control-and-prompt-plumbing.md` |
| 013 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `013-run-and-seat-timeouts.md` |
| 014 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `014-reachability-and-test-hygiene.md` |
| 015 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `015-telemetry-truth-layer.md` |
| 016 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `016-compact-top-bar-and-panel-controls.md` |
| 017 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `017-settings-shell.md` |
| 018 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `018-telemetry-rendering.md` |
| 019 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `019-output-guardrails-backend.md` |
| 020 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `020-configurable-output-guardrails-backend.md` |
| 021 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `021-guardrails-settings-and-visibility.md` |
| 022 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `022-alpha-acceptance-integration-test.md` |
| 023 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `023-cancellation-race-fix.md` |
| 024 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `024-cancel-before-start-terminal-fix.md` |
| 025 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `025-harden-local-backend-boundary.md` |
| 026 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `026-windows-credential-file-hardening.md` |
| 027 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `027-credentials-file-startup-remediation.md` |
| 028 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `028-compare-backend-verification.md` |
| 029 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `029-compare-mode-status-fix-and-frontend.md` |
| 030 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `030-solo-mode-backend.md` |
| 031 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `031-solo-mode-frontend.md` |
| 032 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `032-tauri-toolchain-and-shell.md` |
| 033 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `033-pyinstaller-backend-bundle.md` |
| 034 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `034-frozen-aware-user-data-directory.md` |
| 035 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `035-tauri-sidecar-wiring.md` |
| 036 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed, documentation-only)** | Punch Board accuracy pass — see `PUNCH-BOARD.md` items 30/31 and Record Repair Note below |
| 037 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `037-open-source-credits-and-license-inventory.md` |
| 038 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `038-remove-gplv3-yake-dependency.md` |
| 039 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `039-fix-nondeterministic-query-preprocessing.md` |
| 040 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `040-durable-structured-logging.md` |
| 041 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed, docs-only)** | `041-dead-code-inventory.md` |
| 042 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed)** | `042-remove-confirmed-dead-code.md` — closes Punch Board item 46 |
| 043 | Big Pickle (OpenCode Zen) | **PASS (LOCAL, pushed, docs-only)** | `043-foundational-domain-documentation.md` — draws Punch Board items 7/9/12/13 to SATISFIED |
| 044 | Big Pickle (OpenCode Zen) | **PASS (LOCAL)** | `044-real-cost-computation-backend.md` — advances Punch Board item 17 (spend visibility backend half) |
| 045 | GLM 5.3 Flash (OpenCode) | **PASS (LOCAL)** | `045-cost-rendering-frontend.md` — closes Punch Board item 17 visibility half (frontend rendering) |
| 046 | OpenCode | **PASS (LOCAL)** | `046-deterministic-mock-provider-library.md` — closes Punch Board item 14 |
| 047 | OpenCode | **PARTIAL — config implemented, runtime verification REQUIRES USER** | `047-tauri-csp-hardening.md` — advances Punch Board item 34 (CSP half); runtime proof outstanding |
| 048 | OpenCode | **PASS (LOCAL)** | `048-session-listing-and-deletion-backend.md` — advances Punch Board item 29 (retention/delete basics) |
| 049 | OpenCode | **PASS (LOCAL)** | `049-session-manager-frontend.md` — closes Punch Board item 29 (retention/delete UI) |
| 050 | OpenCode | **PASS (LOCAL)** | `050-per-seat-spend-warning-backend.md` — advances Punch Board item 17 (informational spend warning) |
| 051 | OpenCode | **PASS (LOCAL)** | `051-spend-warning-rendering-frontend.md` — closes Punch Board item 17 spend visibility (frontend warning) |
| 052 | OpenCode | **PASS (LOCAL)** | `052-spend-confirmation-gate-backend.md` — advances Punch Board item 17 (backend dollar-cap enforcement gate) |
| 053 | OpenCode | **PASS (LOCAL)** | `053-temperature-and-moderator-guidance-backend.md` — advances Punch Board item 26 (temperature + moderator guidance, backend) |
| 054 | OpenCode | **PASS (LOCAL)** | `054-temperature-and-moderator-guidance-frontend.md` — advances Punch Board item 26 (temperature + moderator guidance, frontend) |
| 055 | OpenCode | **PASS (LOCAL)** | `055-native-credential-entry-simple-providers.md` — advances Punch Board item 26 (native credential entry for 12 simple providers, frontend) |
| 056 | OpenCode | **PASS (LOCAL)** | `056-native-oauth-connect-disconnect.md` — closes Punch Board item 26 (native OAuth connect/disconnect for xAI, ChatGPT, GitHub Copilot, frontend; zero backend changes) |
| 057 | OpenCode | **PASS (LOCAL)** | `057-spend-limit-control-and-confirmation-frontend.md` — closes Punch Board item 17 (spend limit control, 402 confirmation UX, frontend-only) |


## Mission 007 Provenance Clarification

The final Mission 007 implementation/verification result was produced through **ChatGPT Work** after earlier Codex/repository recovery work. Do not attribute the accepted final Mission 007 result to GLM-5.3.

Accepted Mission 007 implementation commit recorded in the project evidence:

`b10be680c437293d104727ee7f6c26f7e698f79b` — `feat: add ModelMix model discovery selectors`

## Mission 007.5 Security Interlock — CLOSED

Mission 007.5 was a bounded remediation mission inserted between completed Mission 007 and planned Mission 008. It did **not** reorder the locked 47-item Punch Board and did not promote MCP into alpha product scope.

Accepted result on remote `main`:

`e018ed06807beda2c11531f065b2d4181c346ca8` — `fix(mcp): migrate inherited MCP integration to MCP 2.x API`

Verified results recorded by the mission:

- MCP retained at **2.1.1**;
- MCP tests: **146 passed**;
- full backend suite: **458 passed, 5 failed**;
- the five remaining failures were recorded as pre-existing Windows-specific legacy chassis test issues, not MCP migration regressions;
- Python security audit: **0 known vulnerabilities** across 95 locked dependencies;
- backend import/runtime mount verified with MCP mounted at `/mcp` and SSE at `/mcp/sse`;
- frontend dependency audit: **0 vulnerabilities**;
- frontend production build: **PASS**.

Remote `main` was independently verified to resolve to `e018ed06807beda2c11531f065b2d4181c346ca8` before this bookkeeping update.

## Mission 008 Result

**Mission 008 is implemented on current `main` and its persistence behavior passes the current backend suite.**

Objective:

**ModelMix-owned durable session/run persistence plus cockpit hydration using versioned atomic JSON, preserving completed/partial seat state and the existing SSE replay contract.**

Mission 008 corresponds primarily to Punch Board items **11** and **22** and
adds schema-v1 atomic JSON persistence plus durable cockpit hydration.

## Mission 009 Result

**Mission 009 is implemented and verified locally.**

Mission 009 adds bounded, seat-scoped multi-turn history for Worker A, Worker B,
and Moderator. It closes Punch Board items **8** and **15**, partially satisfies
item **29**, preserves history across model hot-swaps, and proves by sentinel
tests that no prior Worker or Moderator content leaks into another worker seat.

## Mission 010 Result

**Mission 010 is implemented and verified locally.**

Mission 010 gives seat history its own owned character budgets: each historical
message is deterministically middle-truncated at 4,000 characters and the
assembled single-seat history is capped at 24,000 characters with whole-turn
oldest-first eviction. It makes partial progress on Punch Board item **17**
(context/spend bounding) while leaving `moderator.py`, `registry.py`, and
`orchestrator.py` untouched.

## Mission 010.5 Result

**Mission 010.5 is implemented and verified locally.**

Mission 010.5 wires Vitest (`npm test` non-watch) and jsdom into the frontend,
adds a `test` block to the existing `vite.config.js`, and brings the three
existing frontend test files to an observed **24/24 pass** through a real
runner. It strengthens Punch Board item **2** (verification) and enables
follow-on work for item **22** (UI to durable run/session state).

## Mission 011 Result

**Mission 011 is implemented and verified locally.**

Mission 011 displays the full per-seat conversation across turns in the cockpit:
`createModelMixState` gains `history: []`, `hydrateModelMixState` archives every
prior run chronologically, `archiveCurrentRun` (pure) moves the outgoing run into
history when it produced seat content, and each `TranscriptPane` renders its
seat's prior turns above the live turn. It advances Punch Board item **22** and
makes partial progress on item **29**.

## Mission 012 Result

**Mission 012 is implemented and verified locally.**

Mission 012 makes archived turns honest and gives the cockpit a session reset
control: the state produced when starting a run carries the submitted `prompt`
and the three selected model IDs so the next archive captures them; the prior
prompt renderer no longer substitutes a `—` placeholder for a missing prompt; and
a separate New Session control clears the `modelmix.sessionId` local key, resets
the cockpit to `createModelMixState()` (empty `history`), and preserves model
selections — without touching any backend endpoint. New Session is disabled
while a run is active via the existing `modelSelectorsDisabled` predicate. It is
the first slice of Punch Board item **24** and makes further partial progress on
item **29**.

## Mission 013 Result

**Mission 013 is implemented and verified locally.**

Mission 013 gives ModelMix its own wall-clock run and seat enforcement:
`backend/modelmix/timeouts.py` owns `RUN_TIMEOUT_SECONDS = 600` and
`SEAT_TIMEOUT_SECONDS = 300` plus one cumulative-deadline helper. `run_seat`
bounds each worker seat, `run_moderator` bounds the Moderator phase, and
`RunRegistry._run` bounds the whole run — all terminating through the existing
`seat_failed` / `moderator_failed` / `run_failed` events with an explicit
`reason: "timeout"`. A timed-out seat still routes through the one-failed-worker
partial path so the Moderator runs with the surviving output; explicit cancel
still yields `run_cancelled` and is never labeled a timeout; and no event is
written to the journal or durable session after a run reaches terminal — proven
for both timeout and cancel paths. It makes partial progress on Punch Board items
**17** and **9** and strengthens item **16**.

## Mission 014 Result

**Mission 014 is implemented and verified locally.**

Mission 014 adds a real `GET /modelmix` route (serving `index.html` from
`FRONTEND_DIST_DIR`) and a visible Council sidebar navigation link, making
the three-panel cockpit reachable from a production build. It fixes every
`RunRegistry()` construction in `backend/tests/` to write to an isolated
`tmp_path` store, eliminating the test-suite's long-standing pollution of the
live `data/modelmix/sessions/` directory. The grep that found all sites is
reported in the canonical mission report. It corresponds to Punch Board items
**21** (fix: production-build reachability), **26** (partial: visible navigation
entry), and **33** (enabler: acceptance run can now start from a built app).

## Mission 015 Result

**Mission 015 is implemented and verified locally.**

Mission 015 is the telemetry truth layer. Events now carry a real wall-clock
`ts` (both `RunEventJournal.append` and `EventSequencer.create`). Persistence
keeps provider-reported `usage` and `finish_reason` (opaque, un-normalized,
never clobbered with null) plus `started_at`/`completed_at` on each message,
fixing the confirmed pre-existing bug where a Moderator's finish reason
silently disappeared on every reload. The frontend truth layer captures
`usage`/`startedAt`/`completedAt` per seat through the live stream, history
entries, hydration, and archiving, and adds the single `describeUsage`
provenance vocabulary — nothing renders yet. Mission 015 also fixes the last
Mission 014 leftover: the streaming route test now uses an isolated
persistence, proven by an empty `data/modelmix/sessions/` after the full suite.
It corresponds to Punch Board items **25** (partial slice), **10** (fix), and
**17** (partial).

## Mission 016 Result

**Mission 016 is implemented and verified locally.**

Mission 016 converts the cockpit's top area into one thin persistent strip and
adds CSS-driven panel view controls. `ModelMixObserver` now renders a single
`header.modelmix-topbar` (brand, inert `Mode: Mix` label, session status from
the existing `observer.overall` vocabulary, New Session moved out of
`.modelmix-actions` with its handler/disabled binding unchanged, a Details
disclosure that stays off by default and hides the `Run: <id>` /
`Last sequence: <n>` debug line, and the unchanged Back to Council link — with
no Settings entry). Each `TranscriptPane` header gains Collapse/expand (hides
only the transcript body; header stays) and Maximize (one panel full width,
others CSS-hidden, all three nodes still mounted), plus one Reset control that
appears whenever any panel is collapsed or maximized. Layout state lives only in
new local `panelView`/`detailsOpen` state in `ModelMixObserver`; the pure view
helpers live in `frontend/src/panelView.js` (`getPanelViewClasses`,
`panelLayoutNeedsReset`, `DEFAULT_PANEL_VIEW`, `PANEL_SEATS`);
`modelmixState.js` and `modelmixApi.js` are byte-identical to Mission 015, and
no backend file changed. Tests: 4 new pure unit tests + 6 new jsdom render tests
of the real component (mocked API layer, completed-session hydration,
deterministic per-test DOM cleanup). It corresponds to Punch Board item **24**
(further advanced: Mission 012's New Session control now sits in the compact
strip); an interactive Mode selector and the Settings surface remain open.

## Mission 017 Result

**Mission 017 is implemented and verified locally.**

Mission 017 is the Settings shell. `configuredModels.js` exports
`configuredSources` (implementation unchanged). `ModelMixObserver` gains a gear
entry in the top bar (`aria-label="Settings"`, `aria-expanded`) that opens a
conditionally-rendered modal overlay — so the default cockpit still contains no
"Settings" text, preserving the existing render test — with three sections:
**About** renders the real `pkg.version` from an imported `../../package.json`
(no duplicated literal), the MIT/copyright line, text-only AI Counsel
attribution, and the repo URL; **Providers** lists OpenRouter / Ollama /
Direct / Custom / OAuth as Connected or Not connected, computed at render from
the exported `configuredSources` against the settings snapshot `loadModels`
already fetches, with zero credential values and an honest "unavailable" state
when the snapshot is null; **Defaults** saves/clears the
`modelmix.defaultSeatModels` localStorage trio (`worker_a`/`moderator`/`worker_b`)
and the three seat selectors initialize from the saved value, falling back to
the frozen `FALLBACK_SEAT_MODELS` that exactly preserves the previous built-in
literals — so criterion "no saved defaults → the exact hardcoded selections"
is a direct regression test. New state is local-only (`settingsOpen`,
`settingsSection`, `settingsSnapshot`, `defaultsRevision`); `modelmixState.js`,
`modelmixApi.js`, and all backend files are unchanged; `Settings.jsx`/`App.jsx`
(separate Council root) are untouched; no new dependencies. Tests: 5 new
`configuredSources.test.js`, 5 new `defaultSeatModels.test.js`, 8 new jsdom
render tests `ModelMixSettings.test.jsx` (mocked API with a mutable
`vi.hoisted` settings container, discovery mocked while the real
`configuredSources` runs via `importOriginal`, per-test deterministic cleanup) —
plus the existing **51 frontend tests pass unmodified** (criterion), for **69
passed**; `npm run lint` clean; `npm run build` green; backend **360 passed**
unchanged. It corresponds to Punch Board items **26** (advanced: real
provider/settings surface), **4** (partial: visible license/copyright/credit),
and **24** (advanced: Settings surface delivered; interactive Mode selector
remains open).

## Mission 018 Result

**Mission 018 is implemented and verified locally.**

Mission 018 makes Mission 015's captured telemetry visibly honest in the
cockpit. A new pure module `frontend/src/seatTelemetry.js` builds a compact
footer item list per seat via `buildSeatTelemetry(seat, seatKey)`, reusing the
single `describeUsage` provenance vocabulary: usage renders as `authoritative
(provider-reported)` showing the provider-reported total token count
(`total_tokens`/`totalTokenCount`, formatted `<n> tokens`) when it is a finite
number, else the raw provider key names as fallback (never normalized, never
merged into a fake percentage) or honest `unavailable`; Moderator-only
`finish_reason` renders as-is or `not reported`; elapsed timing from
`started_at`/`completed_at` renders as `HH:MM:SS → HH:MM:SS` and is explicitly
labeled `(calculated)` because it is ModelMix-computed, and a running seat
shows `Started:` without fabricating a duration. `TranscriptPane` renders a
`.modelmix-telemetry` footer **only for the live turn** when the seat has run —
prior-turn archives keep their telemetry hidden (explicitly deferred
follow-up), and cost/pricing wiring is deliberately out of scope (never
guessed, never displayed). Rendering is gated on honest data presence; idle
and waiting seats show no footer. Tests: 13 new node tests
`seatTelemetry.test.js` (formatting, provenance labeling, timing, finish
reason, oversized usage, no-fabrication rules) and 3 new jsdom render tests
`ModelMixTelemetry.test.jsx` (no-session → zero footers; completed seats →
authoritative/finish/calculated footers; prior-turn archives → zero `prior`
footers while the live turn renders, with known-unknown `not reported`),
reusing the `vi.hoisted` mutable hydrate container pattern — plus the existing
**69 frontend tests pass unmodified**, for **85 passed**; `npm run lint`
clean; `npm run build` green (437 modules); backend **360 passed** unchanged.
Backend, `modelmixState.js`, and `modelmixApi.js` are untouched. It closes Punch
Board item **25** (SUBSTANTIALLY SATISFIED — MISSIONS 015/018, with the two
deferrals noted) and verifies items **10** (ordering/timing contract) and
**17** (timing guardrail input) as visible.

## Mission 019 Result

**Mission 019 is implemented and verified locally.**

Mission 019 enforces the output guardrails in the backend run path at the
live streaming loop. New module `backend/modelmix/guardrails.py` owns the
provisional char bounds — `WARNING_OUTPUT_THRESHOLD_CHARS = 20_000` and
`HARD_OUTPUT_CAP_CHARS = 40_000` — plus `clip_delta`, which clips one stream
delta so the cumulative emitted length lands *exactly* on the cap and reports
when the budget is exhausted. `run_seat` and `run_moderator` both track
cumulative emitted characters over `text_delta`/`moderator_delta`, emit exactly
one `seat_output_warning`/`moderator_output_warning` (`chars`/`threshold`) on
the first crossing (informational only; does not affect multiplexer terminal
bookkeeping), and at the hard cap clip the crossing delta deterministically,
stop consuming the provider stream, and terminate the participant as
`seat_completed`/`moderator_completed` — NOT failed — with `finish_reason:
"modelmix_output_cap"`, which never collides with real provider reasons and
stays honestly distinct from normal completion, user cancellation,
provider/model termination, failure, and timeout. The non-streaming
(`provider.query`) paths are capped with the same exact truncation and no
warning. Timeouts and the output cap are independent; whichever is reached
first governs. The two constants are provisional defaults pending a
configurability (Settings) mission; the provider-quota usage warning is
explicitly deferred as not honestly buildable — no quota/rate-limit data
exists anywhere in this codebase. No changes to `events.py`, `persistence.py`,
`journal.py`, `timeouts.py`, `history.py`, `registry.py`, or any frontend
file: the new events flow through the existing constructors and
`_apply_event`'s unrecognized-event no-op, and the cockpit's
`applyModelMixEvent` already ignores unknown types, so no replay/persistence/
frontend work was required. Coverage: 13 new tests in
`backend/tests/test_modelmix_guardrails.py` using the Mission 013
small-threshold monkeypatch pattern, covering every acceptance criterion
(warning one-shot payload, zero warning below threshold, exact-cap truncation,
`seat_completed`/`modelmix_output_cap` terminal, unchanged under-threshold
behavior, full Moderator equivalence, warning-then-cap ordering with cap
terminal, timeout-before-threshold no-guardrail-events, cancel no-guardrail
events, non-streaming over/under cap). Validation: full backend suite **373
passed** (360 pre-existing + 13 new, no existing test modified); frontend
unchanged with `npm test` **86 passed**, `npm run lint` clean, `npm run build`
green (437 modules). It advances Punch Board item **17** (hard output cap,
output warning, and the `modelmix_output_cap` terminal outcome are no longer
open; the configurable thresholds and the provider/account usage warning
remain open).

## Mission 020 Result

**Mission 020 is implemented and verified locally.**

Mission 020 makes the output guardrails configurable per request. The
`POST /api/modelmix/runs/stream` body (`TwoWorkerRequest`) gains optional
`warning_threshold_chars: Optional[int] = Field(default=None, gt=0)` and
`hard_cap_chars: Optional[int] = Field(default=None, gt=0)`. Before starting a
run, `routes.py` resolves each omitted field to the Mission 019 module default
(`guardrails.WARNING_OUTPUT_THRESHOLD_CHARS` = 20_000 /
`HARD_OUTPUT_CAP_CHARS` = 40_000), rejects values outside the new
`guardrails.MIN_OUTPUT_CHARS_BOUND = 100` / `MAX_OUTPUT_CHARS_BOUND = 200_000`
range, and rejects `hard_cap_chars < warning_threshold_chars` — every violation
surfaces as `HTTPException(status_code=422, detail=...)` **before** the run
starts, so no provider is ever resolved or called on an invalid request. The
resolved pair is threaded through the exact existing `seat_timeout` call chain
(`RunRegistry.start → _run → _run_phase`) into both `multiplex_workers(...)`
and `run_moderator(...)`, which resolve the two numbers exactly like
`seat_timeout` and feed them into the existing `clip_delta` and one-shot
warning check. Mission 019's enforcement, event payloads, and
`modelmix_output_cap` finish reason are unchanged; the frontend is untouched
(an omitted pair is byte-for-byte identical to Mission 019); nothing is
persisted server-side. Coverage: 13 new tests in
`backend/tests/test_modelmix_guardrails.py` mapping to all nine acceptance
criteria — including route-level tests over the full routes → registry →
run-phase chain via `FastAPI TestClient` (a resolver spy proves rejection never
invokes a provider) and a registry-level test proving `_run_phase` delivers the
override to both worker seats and the Moderator. Validation: full backend
suite **388 passed** (375 prior + 13 new, no existing test modified), targeted
suites **65 passed**, `ruff check` clean on all six changed Python files, and
frontend unchanged with `npm test` **86 passed**, `npm run build` green (437
modules), `npm run lint` clean. This advances Punch Board item **17** to the
per-request configurability level; the remaining item-17 openings are the
provider/account usage warning (deferred, not honestly buildable) and
frontend/local-preference wiring of threshold controls.

## Mission 022 Result

**Mission 022 is implemented and verified locally.**

Mission 022 (verify-only) adds the backend-provable half of Punch Board item 33
as one new integration test file,
`backend/tests/test_modelmix_alpha_acceptance.py` — 7 tests driving the real
HTTP routes: ordered stream of both workers then the Moderator on one feed;
cancel via the real route (one `run_cancel_requested` after all deltas,
terminal `run_cancelled`, no post-cancel deltas, persisted `cancelled`, both
providers terminated); worker-failure survival (run ends `partial`, failed seat
excluded from the Moderator handoff, replaced by the honest unavailable line);
session reopen reconstructing the full 7-message transcript; multi-turn seat
isolation across a real second POST; provider-faithful telemetry on reopen
(exact usage, finish_reason, real timestamps); and no credential leak into the
SSE stream, the journal, or the persisted session. The cancel scenario is the
single deliberate harness deviation (two in-flight requests → async httpx on
one loop); everything else reuses the sync TestClient pattern. No production
file, existing test file, or dependency was changed.

Disclosed as a genuine gap (not patched under verify-only rules): a
sub-millisecond cancel window can leave the run stuck `active` until the 600s
run timeout, with `_run_phase` blocked in the `multiplex_workers`
generator-`finally` gather and one seat's provider generator never receiving
`CancelledError`. The natural client rhythm used by scenario 2 cancels cleanly
(10/10 observed); follow-up in the `_run_phase`/`aiter_with_deadline` cancel
hand-off is recommended.

Validation observed: new file **7 passed in 1.80s**; cancel scenario stable
10/10; full backend **395 passed in 16.64s** (388 prior + 7 new); frontend
baseline re-asserted **118 passed**, build green, lint clean; pre-commit diff
was exactly one new test file. Items 1–3 of the item-33 checklist remain
covered by prior-mission evidence (014/016/007); a live-provider manual launch
pass is the remaining alpha step.

## Mission 023 Result

**Mission 023 is implemented and verified locally.**

Mission 023 fixes the cancel-path race Mission 022 disclosed, with a code +
deterministic-test change, on base `main @ b82505d`. Cancellation cleanup is
bounded by a new ModelMix-owned `CANCEL_GRACE_SECONDS = 5.0`:
`backend/modelmix/timeouts.py` gains `await_cancellation_grace(tasks)`, which
`multiplex_workers`' generator `finally` now uses in place of the unbounded
`asyncio.gather` that could previously block the unwinding `CancelledError`
behind a seat task that absorbed cancellation. The Moderator phase in
`registry.py` awaits its moderator task through `asyncio.shield` because the
same absorbing-generator mechanism left `_run_phase` parked at a plain task
await with no way to be woken (verified by task dump: `_must_cancel` unset on
both tasks 20s after cancel); the shield's outer future completes immediately
on cancellation, the task is then explicitly cancelled, and the same bounded
grace covers it. `_run`'s `CancelledError` handler, `aiter_with_deadline`,
the 600s/300s backstops, guardrails logic, and event shapes were left
untouched.

Deterministic proof: `backend/tests/test_modelmix_cancel_race.py` (8 tests)
constructs the failure condition directly with a `StallOnCancelProvider` that
absorbs `CancelledError` and holds on a gate, rather than racing timing; the
terminal contract is asserted structurally (stall provider's `stream_finished`
marker still unset at the terminal `run_cancelled`, no `run_failed`
/`run_completed`, never `"timeout"`, `status == "cancelled"`) with wall-clock
bounds as a secondary guard, and prompt-cancel regressions assert the old
behavior is unchanged. Validation observed: new file **8 passed in 11.98s**;
targeted acceptance subset **57 passed in 16.54s**; full backend **403
passed in 27.94s** (395 prior + 8 new, no existing test modified); frontend
unchanged, re-asserted **118 passed**, build green (1.70s), lint clean. The
alpha gate is **not** declared met here; that declaration is left to the next
verification pass.

## Mission 024 Result

**Mission 024 is implemented and verified locally.**

Mission 024 closes the synthetic edge case where a run cancelled before
`_run`'s first `await` stays `"created"` forever instead of reaching terminal
`"cancelled"`. Root cause: CPython 3.10 `coro.throw(CancelledError)` on a
never-started coroutine skips the coroutine body entirely — no `try/except`
inside `_run` catches it. Fix: `await asyncio.sleep(0)` in `start()` after
`create_task` guarantees `_run` has entered its `try` block and suspended at a
real `await` before the caller can cancel; `await run.mark_status("active")`
moved inside `try` so the except handler covers the earliest cancel point.
Deterministically proven by `test_cancel_before_run_starts_reaches_terminal_cancelled`
in `test_modelmix_cancel_race.py`. Full backend **404 passed**, no existing
test modified, `ruff check` clean.

## Mission 025 Result

**Mission 025 is implemented and verified locally.**

Mission 025 requires admin auth (`_require_admin`, reused exactly as-is) on
every endpoint that reads/writes/uses stored credentials or makes a server
outbound request using a client-influenced target/credential. Added
`dependencies=[Depends(_require_admin)]` to 20 endpoints in `backend/main.py`
(16 required + 4 judgment-call extensions: `GET /api/models`,
`GET /api/models/direct`, `GET /api/ollama/tags`,
`GET /api/custom-endpoint/models`). Three existing tests that hit a newly-
guarded endpoint over a non-loopback TestClient peer (font-size, advisor
presets, council presets) were switched to loopback peers as the legitimate
local-operator case. New `test_admin_guard_credential_endpoints.py` (27 tests)
proves non-loopback rejection without a token, loopback/token success, and
that the `test-custom-endpoint` SSRF-to-credential path is rejected before any
outbound call. Full backend **431 passed**, `ruff` clean; frontend **118
passed**, build green, lint clean. Flagged follow-ups: CORS regex matches any
dotted-IPv4 origin, and custom-endpoint URL allow-listing for a local
loopback attacker.

## Mission 026 Result

**Mission 026 is implemented and verified locally.**

Mission 026 replaces the ineffective `os.chmod(0o600)` no-op on Windows with
real per-user ACL hardening for `data/credentials.json`, scoped to
`backend/credentials/file_backend.py` only. After the atomic write and the
unchanged Unix `chmod`, `_harden_credentials_file()` runs
`icacls "<path>" /inheritance:r /grant:r "<current-user>":F` via `subprocess`
(no `pywin32`), resolving the current user from `USERNAME`/`USERDOMAIN` env
vars (fallback `os.getlogin()`), gated entirely behind
`sys.platform == "win32"`. Failures log a warning and never crash a write; a
once-per-process startup warning surfaces pre-existing/never-hardened
plaintext files on Windows. Default `file` storage mode and
`get_effective_mode()` are unchanged by declared boundary. New
`test_credentials_file_hardening.py` (7 tests) mocks `subprocess.run` /
`sys.platform`. Full backend **438 passed**, `ruff` clean; frontend **118
passed** / build / lint green. Punch Board item 30 advanced (current-model
half); a separate later re-verification of credential storage is required once
Tauri packaging (item 34) exists.

## Mission 027 Result

**Mission 027 is implemented and verified locally.**

Mission 027 turns Mission 026's detection-only warning into automatic
remediation for a pre-existing, unhardened credentials file. Scoped to
`_warn_if_unhardened()` in `backend/credentials/file_backend.py` only; the
`_harden_credentials_file()` logic is reused exactly as Mission 026 built it.
On the first touch (read or write) of an existing file on Windows that is not
already hardened this session, the function now attempts
`_harden_credentials_file()` directly, then logs INFO "Restricted..." on
success or the existing warning on failure — a single, one-time, automatic
remediation (a user who upgrades and just opens the app gets their existing
file protected). Never raises; a failed attempt logs and continues. Extends
`test_credentials_file_hardening.py` to 10 tests (reconciling the one Mission
026 test whose "reads never invoke icacls / always warn" assertion is directly
contradicted by Mission 027's remediation-on-read requirement; flagged
explicitly). Full backend **441 passed**, `ruff` clean; frontend **118 passed**
/ build / lint green. Punch Board item 30 current-model half is now closeable;
the Tauri-specific re-verification (item 34) is carried forward exactly as
Mission 026 stated it.

## Mission 028 Result

**Mission 028 is implemented and verified locally.**

Mission 028 verifies and hardens the existing Compare (no-moderator) backend
path — Punch Board item 28's backend verification half. Before writing any new
Compare orchestration code it determines, with real evidence, whether the
already-shipped, completely-unexercised capability (optional
`moderator_model`; `registry._run_phase` / `orchestrator.multiplex_workers`
already support a two-worker run with no moderator phase) is correct end to
end. It is: **no real defect was found**, and the path now has real
evidence-backed coverage.

New `test_modelmix_compare_mode_backend.py` (7 tests), all through the REAL
HTTP route (`POST /api/modelmix/runs/stream` with `moderator_model` omitted)
using the alpha-acceptance harness, one test per investigation point:
1. both workers stream fully with ZERO moderator events of any kind, then
   `run_completed "completed"`;
2. one worker fails -> `"partial"`, and `GET /sessions/{id}` reflects worker_a
   `failed` + worker_b `completed`, no moderator message;
3. both workers fail -> OBSERVED as-shipped `run_completed "partial"` (not
   `failed`), differing from the moderator path (which yields `failed`); a
   product-semantics note, not a defect, and any change to it is out of scope;
4. multi-turn isolation holds moderator-less; the dead
   `seat_histories["moderator"]` key never leaks to either worker;
5. per-worker guardrails (warning/hard cap) still apply;
6. cancellation mid-stream reaches terminal `run_cancelled`;
7. reopening a moderator-less session reconstructs with no moderator message;
   `models["moderator"]` persists as `None` and `_validate` tolerates it; nothing
   chokes on the moderator's absence.

No production code was changed; no `mode` concept added; no frontend change.
Full backend **448 passed** (441 prior + 7 net new), `ruff` clean; frontend
**118 passed** / build / lint green. Punch Board item 28's backend verification
half is complete; the frontend Compare mode selector/panel work is the next
mission.

## Mission 029 Result

**Mission 029 is implemented and verified locally.**

Mission 029 delivers the other half of Punch Board item 28 (Compare): it fixes
one no-moderator backend status edge and ships the Compare frontend mode.

**Part 1 — Backend status fix.** In the no-moderator path, when **both** workers
fail, `multiplex_workers` now reaches `run_completed` with `status="failed"`
instead of `"partial"` (which was misleading for a run with no surviving output).
Implemented by replacing a `failed: bool` with a `failed_seats: set` and
computing the status as `"failed" if failed_seats and len(failed_seats) ==
len(tasks) else "partial" if failed_seats else "completed"`. The moderator path
(`emit_run_completed=False`) is untouched; a `run_completed` is still only
emitted for the no-moderator case. [revert candidate: `git revert <sha>`]

**Part 2 — Frontend Compare mode.** Replaces the inert top-bar `Mode: Mix`
`<span>` with a real `select.modelmix-mode-select` (options Mix / Compare),
persisted to `localStorage["modelmix.mode"]` via the new pure module
`modelmixMode.js` (`loadSavedMode` / `saveMode`, valid values only `mix` /
`compare`, default `mix`; **no** `solo` anywhere). In Compare mode: the
composer's Moderator selector is not rendered; the Moderator model is omitted
from the request body (`moderator_model` key absent); the center moderator panel
is hidden-but-kept-mounted via the existing `modelmix-panel-hidden` seam; the
models strip uses a 2-column grid. The mode control disables during an active
run using the existing `modelSelectorsDisabled` helper.

Files: `backend/modelmix/orchestrator.py`,
`backend/tests/test_modelmix_compare_mode_backend.py` (point-3 test renamed to
`test_no_moderator_both_workers_fail_reaches_run_completed_failed`, now asserts
`status="failed"`), `frontend/src/modelmixMode.js` (new),
`frontend/src/modelmixMode.test.js` (new, 6 tests),
`frontend/src/components/ModelMixSendCompare.test.jsx` (new, 6 tests),
`frontend/src/components/ModelMixObserver.{jsx,css}`,
`frontend/src/components/ModelMixObserver.test.jsx`.

Validation observed: combined backend `test_modelmix_compare_mode_backend.py` +
`test_modelmix_moderator.py` **18 passed**; full `uv run pytest backend/tests -q`
**448 passed**; `ruff` clean on both changed backend files; frontend **130
passed** (up from 118; +6 `modelmixMode`, +6 `ModelMixSendCompare`) / `build`
green / `lint` green.

One existing frontend test was modified: the top-bar test now asserts the real
`select.modelmix-mode-select` (options `['Mix','Compare']`, default `value===
'mix'`) instead of the old inert `Mode: Mix` span; it was impossible to keep the
span as a non-control while making it a real mode control. This is the sole
modified existing test; all other existing tests pass unmodified. Punch Board
item 28 (Compare) is now genuinely closeable.

## Mission 030 Result

**Mission 030 is implemented and verified locally.**

Mission 030 delivers the backend half of Punch Board item 27 (Solo): it makes
`worker_b_model` optional end to end so a run can consist of Worker A alone.
The frontend Solo surface is intentionally out of scope, so item 27 stays
partially open.

**Routes.** `TwoWorkerRequest.worker_b_model` is now
`Optional[str] = Field(default=None, min_length=1)`. The route rejects the
worker_b-absent + moderator hybrid with `422` **before** any provider resolver
call (`"A moderator requires a second worker (worker_b_model); Solo mode runs
worker_a only"`), honoring the "Solo is exactly one participant, full stop"
boundary. [revert candidate: `git revert <sha>`]

**Registry.** `worker_b_model: Optional[str]` threads through
`RunRegistry.start` / `_run` / `_run_phase` (kept as a positional-None parameter
rather than a keyword default to avoid reordering the required
`provider_resolver` across the codebase). `start` builds only a `worker_a` +
`moderator` seat history and adds `worker_b` only when it is configured; the
persisted `models` dict for a Solo run carries `{"worker_a", "moderator": None}`
(the `worker_b` key is absent); the existing Compare shape
(`{"worker_a", "worker_b", "moderator": None}`) is unchanged. `_run_phase` passes
only the active worker seat histories downstream and adds a defensive
no-hybrid guard (`moderator_model is not None and worker_b_model is not None`
must both hold before the moderator phase runs).

**Orchestrator.** `multiplex_workers` accepts `worker_b_model: Optional[str]`
and computes active seats locally (`models` starts as `{"worker_a"}` and gains
`worker_b` only when configured); the now-unused `SEATS` constant was removed.

**Persistence.** `_validate` statically relaxes the model-references guard from
an exact three-key set equality to: keys a subset of `{worker_a, worker_b,
moderator}`; `worker_a` always present non-empty; plus the existing per-key loop
(any present non-moderator key must be a non-empty string, `moderator` may be a
non-empty string or `None`). Mix / Compare / old three-key shapes still
validate; genuinely malformed shapes (missing or empty `worker_a`, `worker_b:
None`, unknown keys like `worker_c`, empty/non-string `moderator`) are still
rejected.

**No changes to `history.py`.** A Solo turn produces no worker_b message, so a
later Mix turn's `build_seat_history("worker_b")` correctly skips it (verified by
the solo-then-mix isolation test, not patched).

Files: `backend/modelmix/routes.py`, `backend/modelmix/registry.py`,
`backend/modelmix/orchestrator.py`, `backend/modelmix/persistence.py`,
`backend/tests/test_modelmix_persistence.py` (new validator tests),
`backend/tests/test_modelmix_solo_mode.py` (new, 7 tests).

Validation observed: new `test_modelmix_solo_mode.py` **7 passed**; targeted
persistence/streaming/moderator/compare/acceptance/solo files **63 passed**; full
`uv run pytest backend/tests -q` **460 passed**; `ruff check` clean on changed
backend files (the repo-wide `ruff format --check` state is pre-existing and
untouched); frontend **130 passed** / `build` green / `lint` green.

## Mission 031 Result

**Mission 031 is implemented and verified locally.**

Mission 031 delivers the frontend half of Punch Board item 27 (Solo), closing
the item with Mission 030's backend support. `modelmixMode.js` now accepts and
persists `solo`, and the mode control presents Mix / Compare / Solo. In Solo,
the composer renders only the Worker A selector; Worker B and Moderator are not
required, and `send()` omits both `worker_b_model` and `moderator_model` from
the request object entirely.

The Moderator and Worker B panels stay mounted and receive the existing
`modelmix-panel-hidden` class. Worker A uses the existing single-column
`modelmix-workers--maximized` visual treatment. Mode visibility remains
independent from panel-view state: Solo neutralizes a maximize target on a
mode-hidden seat so Worker A cannot disappear, while preserving the underlying
panel-view state for use after leaving Solo.

New `frontend/src/components/ModelMixSendSolo.test.jsx` adds 8 tests for Solo
selector/panel visibility, exact request-key omission, model requirements, Mix
and Compare regressions, active-run mode locking, worker-A-only SSE rendering,
and the hidden-seat maximize interaction. `modelmixMode.test.js` now covers
Solo validity and persistence. The sole modified pre-existing frontend test is
the necessary top-bar option-list assertion, extended to
`['Mix','Compare','Solo']`; every other pre-existing frontend test passes
unmodified.

Validation observed: frontend **138 passed** (15 files; 130 prior + 8 Solo) /
production build green (**439 modules transformed**) / lint clean. The exact
backend command hit the known inaccessible Windows pytest temp root (**246
passed, 214 setup errors**, `WinError 5`); the workspace-temp rerun passed
**460 tests in 35.32s**. No backend file, reducer helper, CSS, dependency, or
lockfile changed. Punch Board items 27 (Solo) and 28 (Compare) are now complete
end to end.

## Mission 032 Result

**Mission 032 is implemented and verified locally.**

The machine already had Rust 1.98.0, Cargo 1.98.0, the MSVC C++ build tools,
and WebView2 Runtime 151.0.4129.107. The initially absent Tauri Cargo subcommand
was installed as `tauri-cli 2.11.4`. A standard `src-tauri/` scaffold now points
at `http://localhost:5173/modelmix` for development and `../frontend/dist` for
the existing production frontend output; its frontend hooks are directory-local
`npm run dev` / `npm run build` commands. It contains no sidecar or backend
launch configuration.

With the Python backend running separately, `cargo tauri dev` compiled and
launched `target\debug\app.exe`. Direct Windows inspection observed exactly one
native ModelMix window displaying the real Worker A / wider Moderator / Worker
B cockpit, controls, and honest no-configured-models state. Validation observed:
`cargo check` passed; frontend **138 passed** / build / lint green; backend
workspace-temp rerun **460 passed** after the exact command reproduced the
known default-temp `WinError 5`. Item 34 is started but remains open for the
Python sidecar, installer, and packaged credential-storage verification.

## Mission 038 Result

**Mission 038 is implemented, verified, and pushed.**

Mission 038 removes the GPLv3-licensed `yake` runtime dependency that Mission
037's inventory exposed (and Mission 033's PyInstaller bundle embeds) and
replaces it with a stdlib-only RAKE implementation in `backend/search.py` —
no new dependency. The public `extract_search_keywords(query, max_keywords)`
contract, the `"yake"` config-mode token (`"direct"` / `"yake"` / `"llm"`, kept
for compatibility across `main.py` validation, `settings.py`, the MCP tool, and
the frontend), and every existing noise/role-play/dedup filter were preserved
byte-for-byte; only the keyword source changed. `pyproject.toml` (yake row
removed) and `uv.lock` (yake + its transitive `numpy`/`regex`/`segtok`/`tabulate`
gone) were updated, and the Python license inventory was regenerated with the
real `pip-licenses` command (yake absent; remaining GPL rows are dev-only
`pyinstaller`/`pyinstaller-hooks-contrib`, GPLv2). RAKE is implemented from the
standard algorithm (stopword-split spans, 1–3 word candidate n-grams,
degree/frequency word scoring, phrase score = sum, descending-by-score return
so the most central phrase comes first), deterministic
and dependency-free. First-ever tests for `search.py` added
(`backend/tests/test_search_keywords.py`). Validation observed: search
tests **8 passed** (after a post-push correction that fixed an inverted sort
and added two semantic subject-phrase regression tests — see
`038-remove-gplv3-yake-dependency.md` section 12); full backend **476 passed**
(474 at push + 2 semantic tests, `--basetemp` workspace override for the known
Windows temp-dir issue); frontend
**138 passed**, build green, lint clean (settings label text updated to
`Smart Keywords (RAKE)`; config value unchanged). Quality is comparable to YAKE,
not identical (documented per-query before/after table in the report, regenerated
after the sort correction);
`pip-licenses` also does not list itself in its own output, which corrected the
Mission 037 credits note. Closes the GPLv3 exposure from Missions 033/037 and
advances Punch Board item 4.

## Mission 039 Result

**Mission 039 is implemented, verified, and pushed.** Fixes a pre-existing,
confirmed correctness bug (not a Punch Board item — surfaced by Mission 038's
own new test coverage, not introduced by it): `_preprocess_query`
(`backend/search.py`) applied sequential, interactive regex substitutions
inside plain-`set` iteration over `ROLE_PLAY_TITLES` / `NOISE_PHRASES`, so the
result depended on the per-process `PYTHONHASHSEED` (~3 of 13 seeds degraded,
e.g. left `current 2025` in "tesla stock" queries). Fix: iterate the two sets
in a fixed, fully reproducible order (`sorted(..., key=lambda s: (-len(s), s))`,
longest-first + alphabetical tiebreak — precomputed as module-level tuples),
which also lowers the interaction risk. `NOISE_WORDS` and
`CURRENT_EVENT_INDICATORS` were audited and left untouched (membership-only
usage, order-independent); regex patterns, set contents, and all other
functions unchanged. New cross-seed subprocess test spawns real
`PYTHONHASHSEED`-overridden processes per seed 0–12 (a same-process test
cannot see this class of bug) asserting identical `_preprocess_query` /
`extract_search_keywords` output and exactly `"tesla stock"` for the
previously-flaky scenario. Validation: raw 13-seed sweep over
`test_search_keywords.py` = `9 passed` under every seed 0–12; full backend **477
passed**; frontend **138 passed** / build / lint green; ruff clean.

## Mission 043 Result

**Mission 043 is implemented, verified, and pushed.** Foundational domain
documentation (docs-only, **zero code changes**) establishing run/seat/event/
moderator/provider concepts and rules **from real code** rather than from
punch-board aspirational wording. Four reference docs under `docs/modelmix/`:
`domain-objects.md` (item 7), `run-state-machine.md` (item 9),
`provider-capability-matrix.md` (item 12), and
`privacy-and-data-routing.md` (item 13), each cited to file/line. The run doc
records an explicit vocabulary correction: the implemented run status is
`partial` (`persistence.py` `TERMINAL_STATUSES`; `registry.py:314`), not the
punch-board's `partially_completed`; the code value is authoritative. Backend
**485 passed** (`--basetemp` workspace override for the known corrupt
`pytest-of-wpedigo` system temp-dir ACL; the literal command reproduces the
same environmental `WinError 5`), frontend **138 passed**, build and lint
clean. Closes Punch Board items **7, 9, 12, 13** to SATISFIED.

## Mission 044 Result

**Mission 044 is implemented and verified locally.** Real per-token cost
computation for OpenRouter-routed models (backend only): `get_models()` now
preserves `prompt_price_per_token`/`completion_price_per_token` and refreshes a
module-level `_PRICING` cache (last successful fetch wins); a new
`compute_openrouter_cost_usd()` attaches an exact `cost_usd` to the existing
`seat_completed`/`moderator_completed` event payloads only when the model is
`openrouter:`-prefixed, pricing is cached, and real non-negative prompt/
completion token counts exist — cost stays entirely absent (never 0, never
estimated) in every other case, including all non-OpenRouter providers.
`persistence.py::_apply_event` captures `cost_usd` onto persisted messages
using the same additive pattern as `usage`/`finish_reason` (no schema bump).
No spend cap, no enforcement, no frontend changes. Item 17 advances (dollar
visibility half); frontend rendering and any spend-cap decision remain
explicitly open. Validation: narrow persistence/streaming/moderator suite
**44 passed**, full backend **494 passed** (`--basetemp` workspace override
for the known corrupt `pytest-of-wpedigo` system temp-dir ACL), frontend
**138 passed**, `npm run build` and `npm run lint` clean.

## Mission 045 Result

**Mission 045 is implemented and verified locally.** Cost rendering, frontend
only (no backend change): `cost_usd` now flows through the full frontend
telemetry lifecycle exactly like `usage`/`finish_reason` — `costUsd: null` on
all three seats in `createModelMixState()`/`buildHistoryEntry()`, no-clobber
capture from `seat_completed`/`moderator_completed` events
(`event.cost_usd ?? seat.costUsd`), hydration from persisted
`message.cost_usd`, and carry-through in `archiveCurrentRun`.
`seatTelemetry.js` renders a standalone `Cost` footer row **only** when
`seat.costUsd` is a real finite number — 4 decimals under $0.01 (so Mission
044's own `$0.0045` fixture never displays as a misleading `$0.00`), 2
decimals at or above — and no row at all when absent (Timing/Finish-style
conditional rendering, deliberately not Usage's always-present pattern). No
cross-seat aggregate; live seat footers only; no new dependencies. Punch
Board item 17 is now **SATISFIED** (visibility half complete end to end);
any actual dollar spend-cap enforcement remains a separate, explicitly
undecided product question. Validation: frontend **148 passed** (138 prior +
10 new), `npm run build` and `npm run lint` clean, backend **494 passed**
(unchanged).

## Mission 046 Result

**Mission 046 is implemented and verified locally.** One shared, deterministic
mock provider library in `backend/tests/mock_providers.py` (additive test
infrastructure; no production code and no existing test touched). Ten factory
functions implementing `LLMProvider` — `normal_provider`, `streaming_provider`,
`slow_streaming_provider`, `failing_provider`, `timeout_provider`,
`rate_limited_provider`, `cancellation_aware_provider`,
`malformed_event_provider`, `missing_usage_provider`, and
`out_of_order_provider`/`duplicate_provider` — each proven by a direct test,
plus one test driving a real `multiplex_workers` flow to prove usability
(replacing an ad-hoc fake). Punch Board item 14 is now **SATISFIED**.
Validation: new suite **13 passed**, full backend **507 passed**, frontend
**148 passed**, build and lint clean.

## Mission 047 Result

**CSP change implemented; runtime verification REQUIRES the user's hands
(same limit as Missions 032/033/035).** `src-tauri/tauri.conf.json`'s
`app.security.csp` changed from `null` to a real policy: `default-src 'self'`;
`script-src 'self'`; `style-src 'self' 'unsafe-inline'
https://fonts.googleapis.com`; `font-src 'self' https://fonts.gstatic.com`;
`img-src 'self' data:`; `connect-src 'self' http://localhost:8001
http://127.0.0.1:8001 http://tauri.localhost:8001`. The production
`connect-src` origin `http://tauri.localhost:8001` was added beyond the
mission's starting policy from repo evidence: the frontend builds its backend
URL as `http://${window.location.hostname}:8001` (`modelmixApi.js:4`,
`api.js:15`), and `window.location.hostname` is `tauri.localhost` in the
packaged app (confirmed by `FRONTEND_HOST` at `lib.rs:223`) — so the
starting 127.0.0.1/localhost-only policy would pass dev but block the
production backend fetch, exactly Mission 035's warned divergence. Automated
suites unaffected: backend **507 passed**, frontend **148 passed**, build and
lint clean. NOT yet PASS: `cargo tauri dev` and a launched `cargo tauri
build` package with fonts rendering, a real streaming Mix run, and zero CSP
console errors remain to be verified by the user (and the `'unsafe-inline'`
`style-src` directive is my best read of React/Google Fonts needs, not
runtime-confirmed).

## Mission 048 Result

**Mission 048 is implemented and verified locally.** Manual session listing
and deletion (backend only, Punch Board item 29 retention/delete basics; no
automatic retention, no frontend, no schema bump). `persistence.py`:
`ModelMixPersistence` gains `list_sessions()` and `delete_session()`;
`AtomicJsonModelMixPersistence` implements `list_sessions()` via the
`latest_session()` glob+mtime pattern returning lightweight newest-first
summaries (`session_id`, `created_at`, `updated_at`, `message_count`, never
message/run content) and `delete_session()` reusing the existing `_path()`
validation to unlink inside `self._lock` (True if existed, False if not).
`registry.py`: `active_run_for_session()` returns a non-terminal run_id from
the existing `_runs` map (pruned, locked). `routes.py`: `GET
/api/modelmix/sessions` and `DELETE /api/modelmix/sessions/{session_id}` (409
while a run in that session is active, 422 on bad id, 404 if absent, 204 on
success). Validation: targeted persistence+streaming suite **39 passed**, full
backend **517 passed** (10 new tests), frontend **148 passed**, build and lint
clean.

## Mission 049 Result

**Mission 049 is implemented and verified locally.** Session manager UI
(frontend only, Punch Board item 29 retention/delete UI; no backend change).
`modelmixApi.js`: `listModelMixSessions()` (GET) and `deleteModelMixSession()`
(DELETE with encoded id), reusing `checkedFetch`. `ModelMixObserver.jsx`: a
`Sessions` section added to `SETTINGS_SECTIONS`; `SessionsSection` lists real
sessions (shortened id, created/updated absolute time, message count) with an
honest empty/loading state, per-row two-click delete confirmation (a single
click never calls the API), removal of the deleted row without a full
re-fetch, and the real backend message surfaced on a 409. Deleting the
currently-open session resets the cockpit via the existing `startNewSession`
(reused `resetToFreshSession`); deleting any other session leaves the live
cockpit unchanged. No auto/scheduled retention UI, no bulk delete, no new
dependency. Validation: frontend **157 passed** (9 new tests), `npm run build`
and `npm run lint` clean, backend **517 passed** (unchanged).

## Mission 050 Result

**Mission 050 is implemented and verified locally.** Per-seat spend warning
(backend only, Punch Board item 17, informational only � no enforcement).
`guardrails.py`: `WARNING_COST_USD_THRESHOLD = 0.10` (provisional default,
the "notice this" point for a single seat turn) and `should_warn_cost()` �
true only for a real finite number strictly above the threshold; `None`
(non-OpenRouter or uncached) never warns. `orchestrator.py` (both streaming
and non-streaming worker paths) and `moderator.py` emit one
`seat_cost_warning`/`moderator_cost_warning` (cost_usd, threshold) at the
exact point cost is computed, just before the completion event � purely
additional, never replacing/altering it. Fires once at completion per seat,
never mid-stream, no cumulative session total. Output-length warning
untouched. Validation: targeted cost+guardrails suite **43 passed**, full
backend **525 passed** (8 new tests), frontend **157 passed**, build and lint
clean. Enforcement/cutoff and cumulative tracking remain separate, undecided
future work.

## Mission 051 Result

**Mission 051 is implemented and verified locally.** Spend warning rendering
(frontend only, Punch Board item 17 spend visibility closed; no backend
change). `modelmixState.js`: `seat_cost_warning`/`moderator_cost_warning` set
`seat.costWarning`/`moderator.costWarning = { cost_usd, threshold }`, mirroring
the `outputWarning` set exactly at both branches. `seatTelemetry.js`:
`buildSeatTelemetry` renders a plain, non-alarming `Cost notice` footer row
only when `costWarning` has a real finite `cost_usd` and `threshold`, reusing
the existing `formatCostUsd` (sub-cent values four decimals, never `$0.00`) �
value like `$0.12 (above $0.10 notice threshold)`. Live-only by design:
`costWarning` is deliberately absent from `createModelMixState` shapes,
`hydrateModelMixState`, `buildHistoryEntry`, and `archiveCurrentRun`, exactly
matching `outputWarning`. No new formatter, no alarm styling, no new
dependency. Validation: frontend **166 passed** (9 new tests), `npm run build`
and `npm run lint` clean, backend **525 passed** (unchanged). Enforcement/cutoff
and cumulative session-cost tracking remain separate, undecided future work.

## Mission 052 Result

**Mission 052 is implemented and verified locally.** Per-request spend
confirmation gate, backend only (Punch Board item 17 advanced with the first
real dollar-cap enforcement). `TwoWorkerRequest` gains `spend_limit_usd`
(Optional[float], `gt=0`) and `confirm_over_budget` (bool, default False).
`routes.py::stream_two_workers` runs the gate BEFORE `run_registry.start()`:
when `spend_limit_usd` AND `session_id` are provided and `confirm_over_budget`
is False, `_over_budget_rejection` loads the session via the existing
`load_session` and inspects only the most recent run's already-persisted
messages. Per-seat only — never an aggregate — any message with a real,
non-`None` `cost_usd > limit` yields HTTP 402 naming the seat and actual cost.
`None` cost is never treated as over-budget; a missing session or prior run
proceeds; `confirm_over_budget: true` bypasses the check entirely; omitting
`spend_limit_usd` is byte-for-byte unchanged. Hard boundaries honored: no
`should_warn_cost`/`WARNING_COST_USD_THRESHOLD`/Mission 050 warning changes, no
server-side persistence of the limit, no `compute_openrouter_cost_usd` change,
no schema bump, no new dependency. ModelMix-only path. Validation:
`test_modelmix_spend_gate.py` **9 passed** (7 acceptance criteria + regression),
targeted 4-file suite **44 passed**, full backend **544 passed** (535 + 9),
frontend **181 passed**, `npm run build` + `npm run lint` clean.

## Mission 053 Result

Temperature control and moderator guidance, backend only (Punch Board item 26
advanced). `TwoWorkerRequest` gains `temperature` (Optional[float], 0.0�2.0,
validated) and `moderator_guidance` (Optional[str], max 2000 chars, validated).
Both thread through `registry.start()` ? `_run` ? `_run_phase` exactly like
`warning_threshold_chars`. All four real provider call sites
(`orchestrator.py` streaming + non-streaming, `moderator.py` streaming +
non-streaming) pass `temperature` only when not `None` via a conditional
`provider_kwargs` dict � when `None`, NO `temperature` kwarg at all, so each
provider's own default applies unchanged; no ModelMix-level default added.
`assemble_moderator_input` appends guidance after the FULL unmodified
`MODERATOR_INSTRUCTIONS` as `Additional guidance from the user:` � strictly
append-only; when `None`, the system message is byte-for-byte identical.
ModelMix-only; no Council/Advisor path, no `settings.py` persistence, no new
dependencies, no schema bump. Validation: targeted pytest **30 passed**, full
suite **535 passed** (525 + 10 new), frontend **166 passed**, build + lint
clean. Frontend controls and local persistence remain open (item 26 still
PARTIAL).
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
server-side.
## Mission 055 Result

Native credential entry for ModelMix's 12 simple (non-OAuth) providers,
frontend only (Punch Board item 26 significantly advanced — the credential/
endpoint entry that previously shipped users to Council settings now lives in
the ModelMix cockpit). `frontend/src/modelmixApi.js` gains `updateSettings`
(partial PUT to the existing `PUT /api/settings`), `testProvider`, `testOpenrouter`,
`testOpencode`, `testOllama`, and `testCustomEndpoint` (each POSTing to the exact
existing `_require_admin`-guarded test endpoint and returning the real JSON).
`ModelMixObserver.jsx` Providers section: keeps the connected/not-connected
`configuredSources` READ list, then adds a write-only editor per provider —
password-masked key inputs (OpenRouter; OpenAI, Anthropic, Google, Mistral,
DeepSeek, Groq, NVIDIA; OpenCode Zen+Go sharing one key), a URL input for
Ollama's base URL, and name/url/optional-key inputs for custom endpoint — each
with a Test button that renders the real returned success/failure message and a
Save that PUTs only the edited field(s). Saved values are never pre-filled or
echoed (write-only); after a successful save the section re-fetches settings so
the READ status updates. The former "Manage providers in council settings" link
is now scoped to OAuth providers only (xAI, ChatGPT, GitHub Copilot), which are
explicitly deferred to a separate mission. Zero backend changes. Validation:
frontend **203 passed** (181 + 22 new: 11 API + 11 component), build + lint
green, backend **544 passed** (unchanged).
## Mission 056 Result

Native OAuth connect/disconnect for the three OAuth providers (`xai-oauth`,
`openai-oauth`, `github-copilot`) directly in the cockpit Settings "Providers"
section — closing the credential fold-in (Punch Board item 26, now **CLOSED**).
Zero backend changes: reuses the existing uniform device-code flow
(`backend/oauth/sessions.py`) and the existing `_require_admin`-guarded routes
exactly. `frontend/src/modelmixApi.js` gains `startOAuthConnection` (POST
`/api/oauth/{id}/start`), `getOAuthConnectionStatus` (GET
`/api/oauth/{id}/status?session_id=...`), and `disconnectOAuthProvider` (DELETE
`/api/oauth/{id}`). `ModelMixObserver.jsx` extends the Mission 055 Providers
section with an `OAuthRow` per provider: real connected status from the
`xai_oauth_connected`/`openai_oauth_connected`/`github_copilot_connected`
fields, a Connect button that starts the flow and renders the real returned
`user_code` plus a clickable `verification_uri_complete` link (falling back to
`verification_uri` when complete is `null`), then polls `getOAuthConnectionStatus`
every 2.5s until `complete`/`error`/`expired`, stopping (interval cleared) and
showing the real returned error/expired message; a Disconnect button calls the
DELETE route and refetches status. Polling is bounded to the session's
`expires_in` and every interval is cleared on unmount — no React leak and the
test suite proves it. The stale "still managed in council settings" OAuth copy
is removed. Validation: frontend **215 passed** (203 + 12 new: 5 API + 7
component), build + lint green, backend **544 passed** (unchanged, no backend
files touched). Full report in `056-native-oauth-connect-disconnect.md`.
## Mission 057 Result

Spend limit control and 402 confirmation UX (frontend-only) — closing Punch
Board item 17's gate half. `frontend/src/modelmixBehavior.js` gains
`loadSpendLimit`/`saveSpendLimit`/`clearSpendLimit` (validating `value > 0`,
matching the backend's `gt=0` bound exactly, same defensive storage discipline
as every existing settings module). `send()` includes `spend_limit_usd` in the
request body only when a valid saved value exists (key genuinely absent
otherwise). When `startModelMixRun` rejects with HTTP 402, the real backend
message (which seat, actual cost) renders in a dedicated confirmation UI with an
explicit "Proceed anyway" button that resends the identical original request
body plus `confirm_over_budget: true` — never auto-retrying, never persisting
the confirmation flag. A new dollar-amount input with save/clear pair is added
to the existing Behavior Settings section. Validation: frontend **228 passed**
(215 prior + 13 new: 4 in `modelmixBehavior.test.js`, 3 in
`ModelMixSendBehavior.test.jsx`, 6 in new `ModelMixSpendLimit.test.jsx`), build
+ lint green. Backend: zero files touched; observed errors are pre-existing
Windows temp-dir `WinError 5` PermissionErrors, not mission regressions. Full
report in `057-spend-limit-control-and-confirmation-frontend.md`.

## Evidence Rule

Historical worker branch names, reports, local commit SHAs, or PASS statements are evidence to reconcile; they are not proof of current remote state by themselves.

The accepted repository state is what is reachable from current `main`. Historical mission reports are retained as execution evidence and provenance.

## Record Repair Note

On 2026-08-28 CT, project bookkeeping was reconciled after detecting that Mission 001 and Mission 007 reports were missing from `main` even though corresponding work/evidence existed elsewhere. Mission 001 was recovered from its verified Claude branch object; Mission 007 was reconstructed from the observed ChatGPT Work result and verified GitHub commit.

On 2026-08-29 CT, the current Library Punch Board and repo project records were reconciled. The authoritative Punch Board was copied into `docs/modelmix/PUNCH-BOARD.md`, while this index and `ENGINEERING-PROGRESS.md` were refreshed to point to the same current mission state and next gap.

On 2026-09-01 CT (Mission 036, documentation-only), Punch Board items 30 and 31 were corrected against already-completed evidence and closed: item 30 citing Missions 026/027 (current-model ACL hardening + startup remediation) and 033/034 (real frozen-executable keyring/ACL proofs + frozen `%LOCALAPPDATA%\ModelMix` credential location); item 31 citing Mission 025 (admin-auth guards on 20 endpoints closing the SSRF→credential-exfiltration path), with the deliberately-deferred `_dev_cors_regex` finding carried forward as sub-item 31a (and the custom-endpoint URL allow-list note as 31b). Item 34 was relabeled from "DONE" to "SUBSTANTIALLY COMPLETE" to stay explicitly open on MSI, code signing, CSP hardening, and dynamic ports. No code changed.

Later on 2026-08-29 CT, Mission 007.5 was inserted as a security/compatibility interlock after dependency remediation reached a clean audit but exposed an MCP 2.x API incompatibility in inherited MCP code. Mission 007.5 subsequently completed and was verified on remote `main` at `e018ed06807beda2c11531f065b2d4181c346ca8`.

