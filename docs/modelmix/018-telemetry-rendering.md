# Mission 018 — Telemetry Rendering

Route: Big Pickle (OpenCode Zen)
Punch Board items: 25 (close), 10 (verify visible)
Base: `main` @ `99cc63f` "feat(modelmix): settings shell (Mission 017)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Take Mission 015's capture-only telemetry truth (provider-reported `usage`,
`finish_reason`, and wall-clock `started_at`/`completed_at`, plus the single
`describeUsage` provenance vocabulary) and surface it honestly in the cockpit:
compact per-seat labels and timing, no telemetry dashboard, no fabricated
estimates, estimates/labels exactly as required, each seat's provider-reported
usage kept opaque and un-normalized. No backend changes; no regression of the 69
existing frontend tests.

## Delivered

### 1. Pure rendering logic — `frontend/src/seatTelemetry.js`

New node-testable module with no React/DOM dependencies:

- `formatTimestamp(ts)` — local `HH:MM:SS` for a finite epoch-seconds timestamp;
  `null` for anything missing/non-finite.
- `formatElapsed(startedAt, completedAt)` — `12.4s` (< 60s), `1m 0s`,
  `1h 1m`; `null` when either bound is missing or the duration is not positive
  (no fabricated durations).
- `rawUsageKeys(usage)` — the raw provider key names (`prompt_tokens ·
  completion_tokens · total_tokens`), bounded to 8 keys then summarized as
  `N fields`; `null` when there is nothing to show. The values are never
  read, normalized, summed, or merged into a percentage.
- `usageDetail(usage)` — when the provider-reported usage carries a finite
  `total_tokens` or `totalTokenCount`, returns that number formatted as
  `<n> tokens`; otherwise falls back exactly to `rawUsageKeys(usage)`.
- `buildSeatTelemetry(seat, seatKey)` — returns the footer item list, importing
  the existing `describeUsage` from `modelmixState.js` so there is exactly one
  provenance vocabulary:

| Key | Label | When | Value |
|---|---|---|---|
| `usage` | Usage | every active seat | `authoritative (provider-reported)` + the provider-reported total (`<n> tokens`) when it is a finite number, else the raw key names; or honest `unavailable` |
| `finish` | Finish | Moderator only | `finish_reason` as reported, or `not reported` |
| `timing` | Elapsed | both bounds present | duration `(calculated)` + `HH:MM:SS → HH:MM:SS` range |
| `timing` | Started | only `startedAt` | `HH:MM:SS` (running seat — no duration fabricated) |
| `timing` | Completed | only `completedAt` | `HH:MM:SS` |

Gating: `isSeatActive` returns `false` (→ no items) for idle/waiting seats or
when no telemetry field exists, so the default cockpit renders zero footers.

### 2. Live-turn footer in `TranscriptPane`

`ModelMixObserver.jsx` imports `buildSeatTelemetry`; `TranscriptPane` computes
`telemetry` for its seat and, when items exist, renders

```html
<footer class="modelmix-telemetry" aria-label="Seat telemetry">
  <span class="modelmix-telemetry-item">
    <span class="modelmix-telemetry-label">Usage</span>: authoritative
    (provider-reported) · <span class="modelmix-telemetry-detail">prompt_tokens · completion_tokens · total_tokens</span>
  </span>
  ...
</footer>
```

inside `.modelmix-transcript` (scrolls with the content; hidden with the panel
when collapsed). Timing is explicitly labeled `(calculated)` because elapsed
is ModelMix-computed from persisted event timestamps — per the telemetry lock,
ModelMix-computed values carry that label, provider-reported usage carries the
`authoritative (provider-reported)` label, and missing data stays
`unavailable`/`not reported`.

### 3. Scope discipline

- **Footer is live-turn only.** `history` entries are archived with the same
  captured fields (Mission 015/011), but prior turns render **zero** telemetry.
  This is the explicitly deferred per-historical-turn footer follow-up, noted in
  the Punch Board — not a silent omission.
- **Cost/pricing is deliberately out of scope.** No cost field is ever guessed
  or displayed even if a provider's usage object contains a cost-like key; the
  existing item-25 "reliable per-call cost only" stays open as a follow-up.
- No fake normalized percentage, no estimated tiers, no cross-seat aggregates.

### Architecture boundaries preserved

- Backend untouched: `journal.py`, `events.py`, `persistence.py`, all backend
  files byte-identical to Mission 017.
- `modelmixState.js` and `modelmixApi.js` untouched (the mission consumes
  `describeUsage`, it does not move it).
- Worker independence, Moderator fan-in, SSE/replay, persistence interface, and
  the run/event model are untouched.
- No new dependencies, no lockfile changes, no credential handling changes.
- Guardrails (usage/output warning, hard cap) remain open and unwired; mission
  018 adds no placeholder controls.

## Test Evidence

2 new files; no existing test file was modified.

### New — `frontend/src/seatTelemetry.test.js` (node env, 14 tests)

1. `formatTimestamp returns local HH:MM:SS for a finite timestamp`.
2. `formatTimestamp returns null for missing or non-finite input`.
3. `formatElapsed renders seconds, minutes, and hours` (`12.4s`, `1m 0s`,
   `1h 1m`).
4. `formatElapsed returns null for missing, inverted, or zero duration`.
5. `idle seats produce no telemetry items` (worker `idle`, moderator `waiting`).
6. `a completed seat with usage shows authoritative provider-reported usage`
   (label + the provider-reported total `46 tokens`; values are never
   normalized).
7. `a usage object without total_tokens falls back to totalTokenCount`
   (`77 tokens`).
8. `a completed seat without usage shows honest unavailable`.
9. `elapsed timing is labeled calculated with a time range detail` (value
   `12.4s (calculated)`, detail `HH:MM:SS → HH:MM:SS`).
10. `a started but not completed seat shows a Started item without fabricating a
    duration`.
11. `a completed seat with only completedAt shows a Completed item`.
12. `moderator finish reason is rendered only for the moderator seat`.
13. `moderator without a reported finish reason stays known-unknown`
    (`not reported`).
14. `an oversized usage object is summarized by field count, never merged`
    (`10 fields` for > 8 keys).

### New — `frontend/src/components/ModelMixTelemetry.test.jsx` (jsdom render tests, 3)

Renders the real `ModelMixObserver` with the same gravitational mock pattern as
`ModelMixSettings.test.jsx` (`api`/`configuredModels`/`modelmixApi`), except the
hydrate mock returns a mutable `vi.hoisted` `mockHydrate.document` session
instead of a 404 so telemetry can flow into the truth layer. Per-test
deterministic cleanup unmounts/removes containers and clears `localStorage`.

1. `with no session the cockpit renders no telemetry footers` — the no-data
   default stays clean (zero `.modelmix-telemetry`).
2. `completed seats render authoritative provider-reported usage, finish reason,
   and calculated timing` — three footers; Worker A shows `authoritative
   (provider-reported)` with the provider-reported total `46 tokens`, `Elapsed`,
   `(calculated)`, and the `HH:MM:SS → HH:MM:SS` arrow; Moderator shows
   `Finish: stop` and `99 tokens`; Worker B (no usage) shows honest
   `unavailable`.
3. `prior-turn archives keep their telemetry hidden while live seats still
   render footers` — a two-run session where the prior run carries usage/timing
   in its archived messages: `.modelmix-prior-turn .modelmix-telemetry` count is
   0 (the deferral), total footers remain 3, prior content still renders, the
   live Worker A footer does not leak the prior run's `total_tokens`, and the
   latest Moderator without a reported finish shows `not reported`.

### Existing tests pass unmodified

`modelmixState.test.js` (35), `configuredModels.test.js` (3), `fontSize.test.js`
(3), `panelView.test.js` (4), `configuredSources.test.js` (5),
`defaultSeatModels.test.js` (5), `ModelMixObserver.test.jsx` (6), and
`ModelMixSettings.test.jsx` (8) all pass untouched. Total observed at the
original Mission 018 close: **85 passed** (was 69).

## Validation — raw, unedited

From `frontend/`:

```text
npm test

> the-ai-counsel@0.11.4 test
> vitest run

 ✓ src/utils/fontSize.test.js (3 tests) 5ms
 ✓ src/panelView.test.js (4 tests) 6ms
 ✓ src/defaultSeatModels.test.js (5 tests) 8ms
 ✓ src/seatTelemetry.test.js (13 tests) 10ms
 ✓ src/configuredSources.test.js (5 tests) 7ms
 ✓ src/configuredModels.test.js (3 tests) 24ms
 ✓ src/modelmixState.test.js (35 tests) 48ms
 ✓ src/components/ModelMixTelemetry.test.jsx (3 tests) 179ms
 ✓ src/components/ModelMixObserver.test.jsx (6 tests) 371ms
 ✓ src/components/ModelMixSettings.test.jsx (8 tests) 409ms

 Test Files  10 passed (10)
      Tests  85 passed (85)
```

(Original Mission 018 close; see the Follow-up Fix addendum for the post-fix
run — **86 passed**, with the usage detail now preferring the provider-reported
total.)

```text
npm run lint

> the-ai-counsel@0.11.4 lint
> eslint .
```

(clean)

```text
npm run build

> the-ai-counsel@0.11.4 build
> vite build

vite v7.3.6 building client environment for production...
✓ 437 modules transformed.
✓ built in 1.86s
```

From the repository root (backend unchanged, suite still required):

```text
uv run pytest backend/tests -q

........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 12.88s
```

`git status --short` (after all edits, before staging):

```text
 M frontend/src/components/ModelMixObserver.css
 M frontend/src/components/ModelMixObserver.jsx
 ?? frontend/src/seatTelemetry.js
 ?? frontend/src/seatTelemetry.test.js
 ?? frontend/src/components/ModelMixTelemetry.test.jsx
 ?? docs/modelmix/018-telemetry-rendering.md
```

No backend changes, no `data/` changes, no lockfile changes, no dependency
changes. One expectation bug was caught by the first vitest pass and fixed in
test-only code: `formatElapsed(100, 3700)` is exactly `1h 0m` (3600s), not
`1h 1m` — the assertion was corrected to `formatElapsed(100, 3760)`; the
implementation was already correct. The clean 85/85 run above is the final
observed result.

## Punch Board Mapping

- **Item 25 — minimal telemetry (SUBSTANTIALLY SATISFIED — MISSIONS 015/018):**
  the truth layer (Mission 015) is now rendered honestly per seat: state was
  already visible; elapsed time renders labeled `(calculated)`; provider-
  reported tokens surface as `authoritative (provider-reported)` labels showing
  the provider-reported total token count (`<n> tokens`) when finite, else the
  raw key names; estimates never exist so nothing is estimated; cost stays open
  (deferral 1 — reliable per-call cost/pricing wiring is deliberately out of
  scope); per-historical-turn footers are deferred (deferral 2 — archived turns
  render zero telemetry today). Confidence colors were never introduced; the
  mission renders labels, not danger colors.
- **Item 10 — ordered event contract (verified visible):** the wall-clock `ts`
  captured by both event constructors (Mission 015) now visibly drives `Started`,
  `Elapsed`, and `Completed` per seat.
- **Item 17 — timing guardrail input (note):** persisted `started_at`/
  `completed_at` are now surfaced; the future guardrail layer (usage warning,
  output warning, hard cap) remains explicitly open and unwired.
- Items 27/28 (Solo/Compare), 30–33, 4, 24, 26 are untouched by this mission.

## Assumptions

- Local time-of-day formatting (browser timezone) is acceptable for the current
  raw `HH:MM:SS` range display; no UTC/ISO formatting is implied.
- A non-null object `usage` is treated as provider-reported authoritative via
  the existing `describeUsage` vocabulary; values are never parsed.
- Elapsed duration, being ModelMix-derived from event timestamps, carries the
  `(calculated)` label per the telemetry lock.

## Remaining Risks / Open

- Per-historical-turn telemetry footers remain deferred (data is captured in
  `history`; rendering is intentionally withheld this mission).
- Cost/pricing wiring remains open and is never guessed.
- The future guardrail layer (usage/output warning, hard cap) remains open.

## Follow-up Fix — provider-reported token totals

2026-08-30, immediately after the original Mission 018 close. Review flagged
that the authoritative usage detail steered into a raw key-name derivation
(`prompt_tokens · completion_tokens · total_tokens`) instead of surfacing the
provider-reported total the user asked for. One function-level extension in
`frontend/src/seatTelemetry.js`: `buildSeatTelemetry` now routes through a
private `usageDetail(usage)` which, when `usage.total_tokens` or
`usage.totalTokenCount` is a finite number, returns that number formatted as
`<n> tokens` INSTEAD of the raw key list; `rawUsageKeys` is byte-identical and
remains the fallback for every other shape. Test impact: the existing unit test
assertion changed from the key list to `46 tokens`, the jsdom render test's
Worker A/Moderator assertions changed to `46 tokens`/`99 tokens`, and one new
test covers the `totalTokenCount` branch (`77 tokens`) — no new test files.
Validated from `frontend/`:

```text
npm test
 ✓ src/utils/fontSize.test.js (3 tests) 6ms
 ✓ src/defaultSeatModels.test.js (5 tests) 9ms
 ✓ src/configuredSources.test.js (5 tests) 8ms
 ✓ src/panelView.test.js (4 tests) 8ms
 ✓ src/seatTelemetry.test.js (14 tests) 11ms
 ✓ src/configuredModels.test.js (3 tests) 29ms
 ✓ src/modelmixState.test.js (35 tests) 54ms
 ✓ src/components/ModelMixTelemetry.test.jsx (3 tests) 252ms
 ✓ src/components/ModelMixObserver.test.jsx (6 tests) 484ms
 ✓ src/components/ModelMixSettings.test.jsx (8 tests) 519ms

 Test Files  10 passed (10)
      Tests  86 passed (86)

npm run lint   (eslint . — clean)
npm run build  (437 modules transformed, built in 1.71s)
```

Backend unchanged (prior run: 360 passed). Committed as a separate follow-up
commit on `main`.