# Mission 012 — Session Control and Prompt Plumbing

Route: Big Pickle (OpenCode Zen)
Punch Board items: 24 (partial), 29 (partial)
Base: `main` @ `296534b`
Date: 2026-08-29
Result: **PASS (LOCAL)**

## Objective

Archived turns show their real prompt during a live session, and the user can
start a new session.

## Delivered

- `send()` in `ModelMixObserver.jsx` now stamps the `starting` state with
  `prompt` (the submitted, trimmed prompt) and `models` (the three trimmed
  selected model IDs) alongside `overall` and `message`. The NEXT
  `archiveCurrentRun` therefore captures real prompts/models for runs started in
  a live session. Previously only `hydrateModelMixState` wrote `state.prompt`
  and `state.models`, so live-run archives carried `prompt: undefined`.
- `TranscriptPane` no longer substitutes `—` for a missing prior-turn prompt.
  The prompt header renders only when a prompt is present; an absent prompt
  shows nothing rather than disguising missing data.
- Added exported pure `startNewSession(state)` to `modelmixState.js`. It returns
  a fresh cockpit — exactly `createModelMixState()` with empty `history` — and
  carries the current model selections forward when the state has them (`models`
  is not session state, so model choices are preserved). It does not touch any
  backend endpoint.
- Added a separate **New Session** button to the existing top controls area
  (`.modelmix-actions`). Send/Stop are unchanged. On activation it removes
  `modelmix.sessionId` from localStorage, then resets the cockpit observer to
  `startNewSession(observerRef.current)`. Persisted sessions on disk are
  untouched; the next run without a session ID creates a fresh backend session.
- New Session is disabled only while a run is active — connecting, running,
  reconnecting, cancelling — using the existing `modelSelectorsDisabled`
  predicate. It is a separate control; the fixed Send/Stop pair is unchanged.
- `applyModelMixEvent` is unchanged — not one line. No backend, API, schema,
  dependency, `package.json`, or lockfile changes.

Out of scope per the mission and not built: session picker/list, rename,
delete, export, telemetry, timestamps, and token counts.

## Acceptance Coverage

Five tests were appended to `frontend/src/modelmixState.test.js`; the existing
30 frontend tests run unmodified.

1. `archiveCurrentRun preserves prompt and models into the history entry` —
   a state carrying `prompt` and `models` archives both into the history entry
   (extension coverage; the existing Mission 011 archive test is untouched).
2. `archiveCurrentRun with no prompt archives an entry whose prompt is
   undefined` — the archive never invents a prompt, so the renderer shows
   nothing (no placeholder).
3. `startNewSession resets cockpit state while preserving model selections` —
   deep-equal to `createModelMixState()` except `models` carries the selections;
   `sessionId`/`runId`/`lastSeq` clear, `overall` returns to `idle`, `history`
   is empty, and the input state is not mutated. A companion test asserts a
   default cockpit resets to byte-for-deep-equal `createModelMixState()`.
4. `New Session gating matches the frozen-selector predicate for every
   lifecycle state` — disabled for connecting/running/reconnecting/cancelling,
   enabled for idle/completed/partial/failed/cancelled/replay_gap/expired.
5. Existing 30 tests pass unmodified.
6. `npm run build` and `npm run lint` succeed; backend suite unaffected.

## Validation

Command (from `frontend/`):

```text
npm test && npm run build && npm run lint
```

Raw unedited output:

```text
> the-ai-counsel@0.11.4 test
> vitest run

 RUN  v4.1.11 C:/Users/wpedi/ModelMix/frontend

 ✓ src/utils/fontSize.test.js (3 tests) 3ms
 ✓ src/configuredModels.test.js (3 tests) 12ms
 ✓ src/modelmixState.test.js (29 tests) 31ms

 Test Files  3 passed (3)
      Tests  35 passed (35)
   Start at  22:22:05
   Duration  275ms
```

```text
> the-ai-counsel@0.11.4 build
> vite build

vite v7.3.6 building client environment for production...
transforming...
✓ 433 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                1.04 kB │ gzip:  0.54 kB
dist/assets/ollama-DE2Cu6-_.svg                4.78 kB │ gzip:  2.24 kB
dist/assets/ModelMixObserver-QQz_hUhO.css      3.23 kB │ gzip:  1.06 kB
dist/assets/LandingPage-CqcwYOwM.css           5.72 kB │ gzip:  1.55 kB
dist/assets/index-BBDNWvSr.css               16.09 kB │ gzip:  4.04 kB
dist/assets/Settings-C_CQ48Qz.css             34.71 kB │ gzip:  6.63 kB
dist/assets/ChatInterface-CUo4Eqg3.css       105.01 kB │ gzip: 17.15 kB
dist/assets/LandingPage-D0cj4OEw.js            4.86 kB │ gzip:  1.18 kB
dist/assets/opencode-D5BbqXFQ.js               9.07 kB │ gzip:  3.39 kB
dist/assets/ModelMixObserver-wnfuGQ0T.js      14.48 kB │ gzip:  5.00 kB
dist/assets/Settings-CYEkTPcy.js              93.38 kB │ gzip: 23.05 kB
dist/assets/ChatInterface-GncriZ-q.js        102.03 kB │ gzip: 26.24 kB
dist/assets/index-dLSmgDJe.js                235.98 kB │ gzip: 72.17 kB
dist/assets/SearchableModelSelect-N2vPgmtO.js 247.89 kB │ gzip: 79.35 kB
✓ built in 1.93s
```

```text
> the-ai-counsel@0.11.4 lint
> eslint .

```

Command (from repo root, with the documented workspace-local `TEMP`/`TMP`
workaround for the unreadable `pytest-of-wpedigo` root):

```text
uv run pytest backend/tests -q
```

Raw unedited output:

```text
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
.....................................................                    [100%]
341 passed in 10.70s
```

## Git Diff Stat

Working tree was fully staged at capture, so the unstaged `git diff --stat` was
empty; the staged diff is shown (Git also emits existing LF-to-CRLF
working-copy warnings).

Command:

```text
git diff --cached --stat
```

Raw unedited output (captured after staging the full deliverable, including
this report):

```text
 .../012-session-control-and-prompt-plumbing.md     | 176 +++++++++++++++++++++
 docs/modelmix/ENGINEERING-PROGRESS.md              |  20 ++-
 docs/modelmix/MISSION-INDEX.md                     |  16 ++
 docs/modelmix/PUNCH-BOARD.md                       |  22 +--
 docs/modelmix/README.md                            |   1 +
 frontend/src/components/ModelMixObserver.css       |   1 +
 frontend/src/components/ModelMixObserver.jsx       |  16 +-
 frontend/src/modelmixState.js                      |   7 +
 frontend/src/modelmixState.test.js                 |  78 +++++++++
 9 files changed, 325 insertions(+), 12 deletions(-)
```

## Punch Board Mapping

- Item 24: first slice shipped — separate New Session control; Mode/Models/
  Settings surface remains open.
- Item 29: further partial progress — archived prompts/models are now honest and
  New Session gives the user a way to start fresh; retention/delete UX remains
  open.