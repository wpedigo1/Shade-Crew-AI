# Mission 011 — Multi-Turn Cockpit Display

Route: Big Pickle (OpenCode Zen)
Punch Board items: 22, 29 (partial)
Base: `main` @ `9564cbf`
Date: 2026-08-29
Result: **PASS (LOCAL)**

## Objective

Each cockpit panel shows the full conversation for its seat across turns, not
just the latest run.

## Delivered

- `createModelMixState()` gained `history: []`. The live seat slots
  (`worker_a`, `moderator`, `worker_b`) and every other field are unchanged.
- `history.py`-style entries live in a sibling `history` array. Each entry:
  `{ runId, prompt, models, status, worker_a: { text, status, error },
  moderator: { text, status, error, finishReason }, worker_b: { text, status,
  error } }`.
- `hydrateModelMixState` iterates all `document.session.runs` in order. The last
  run populates the live slots with exactly the existing logic (unchanged); every
  prior run becomes a `history` entry via a new local `buildHistoryEntry`, built
  by filtering `document.session.messages` on that run's `run_id`.
  Chronological order is preserved. Zero runs still returns
  `createModelMixState()`.
- Added exported pure `archiveCurrentRun(state)` to `modelmixState.js`. It
  returns fresh state with live slots reset, `sessionId` preserved, and the
  outgoing run appended to `history` — or nothing appended when the outgoing run
  produced no seat content at all.
- `ModelMixObserver.jsx` calls `archiveCurrentRun` when starting a new run,
  before the live slots are reset, replacing the previous
  `createModelMixState()`-based starting state.
- `TranscriptPane` renders that seat's prior turns above the live turn. Each
  prior turn shows its user prompt as a compact header (`.modelmix-prior-prompt`)
  above that turn's output. Panels keep independent scrolling
  (`.modelmix-transcript` overflow) and the chrome stays sparse. Turns without
  any content for the seat are skipped; the existing empty-state text appears
  only when neither prior nor live content exists.
- `applyModelMixEvent` is unchanged — not one line. `modelmixApi.js`,
  `configuredModels.js`, all backend files, `package.json`, and the lockfile are
  untouched.

Out of scope per the mission and not built: collapsing/expanding turns,
timestamps, per-turn telemetry/token counts, editing, deleting, branching,
virtualization, turn-count limits, and export.

## Acceptance Coverage

New tests were appended to `frontend/src/modelmixState.test.js`; the 24 existing
frontend tests run unmodified.

1. Hydrating a 3-run document yields `history.length === 2` in chronological
   order with the live slots holding run 3.
2. Hydrating a 1-run document yields `history === []` with live-slot behavior
   identical to before (`sessionId`, `runId`, `lastSeq`, `overall`, seat text,
   `moderator.started`).
3. Hydrating a 0-run document returns exactly `createModelMixState()`.
4. `archiveCurrentRun` appends the outgoing run, resets live seat slots,
   preserves `sessionId`, clears `runId`/`lastSeq`/`overall`, and does not mutate
   the input state.
5. `archiveCurrentRun` appends nothing when the outgoing run has no seat content.
6. Seat isolation holds in history: a `history` entry's `worker_a.text` contains
   no substring of that run's `worker_b` or moderator content (distinct
   sentinels), while the live slots still hold the newest run's content.
7. `applyModelMixEvent` unchanged — the 24 existing tests pass unmodified.
8. `npm run build` and `npm run lint` both pass.

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

 ✓ src/utils/fontSize.test.js (3 tests) 4ms
 ✓ src/configuredModels.test.js (3 tests) 12ms
 ✓ src/modelmixState.test.js (24 tests) 31ms

 Test Files  3 passed (3)
      Tests  30 passed (30)
   Start at  22:07:07
   Duration  293ms
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
dist/assets/ModelMixObserver-DfroZIt2.css      3.18 kB │ gzip:  1.05 kB
dist/assets/LandingPage-CqcwYOwM.css           5.72 kB │ gzip:  1.55 kB
dist/assets/index-BBDNWvSr.css               16.09 kB │ gzip:  4.04 kB
dist/assets/Settings-C_CQ48Qz.css             34.71 kB │ gzip:  6.63 kB
dist/assets/ChatInterface-CUo4Eqg3.css       105.01 kB │ gzip: 17.15 kB
dist/assets/LandingPage-3AOWt4G4.js            4.86 kB │ gzip:  1.18 kB
dist/assets/opencode-D5BbqXFQ.js               9.07 kB │ gzip:  3.39 kB
dist/assets/ModelMixObserver-DQIEDogU.js      14.12 kB │ gzip:  4.91 kB
dist/assets/Settings-BG8MLvpA.js              93.38 kB │ gzip: 23.05 kB
dist/assets/ChatInterface-BFKLYKUl.js        102.03 kB │ gzip: 26.24 kB
dist/assets/index-BoUulhb9.js                235.98 kB │ gzip: 72.18 kB
dist/assets/SearchableModelSelect-MKhCTBMk.js 247.89 kB │ gzip: 79.35 kB
✓ built in 2.15s
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
341 passed in 11.06s
```

## Git Diff Stat

Working tree was fully staged at capture, so the unstaged `git diff --stat` was
empty; the staged diff is shown (Git also emits existing LF-to-CRLF
working-copy warnings).

Command:

```text
git diff --cached --stat
```

Raw unedited output:

```text
 docs/modelmix/ENGINEERING-PROGRESS.md        |  18 +++-
 docs/modelmix/MISSION-INDEX.md               |  12 +++
 docs/modelmix/PUNCH-BOARD.md                 |  15 ++--
 frontend/src/components/ModelMixObserver.css |   3 +
 frontend/src/components/ModelMixObserver.jsx |  23 +++--
 frontend/src/modelmixState.js                |  51 +++++++++++
 frontend/src/modelmixState.test.js           | 127 +++++++++++++++++++++++++++
 7 files changed, 234 insertions(+), 15 deletions(-)
```

`docs/modelmix/011-multi-turn-cockpit-display.md` was still untracked when this
stat was captured and is part of the Mission 011 deliverable.

## Punch Board Mapping

- Item 22: the cockpit now displays the full per-seat conversation, folding
  durable run/session state forward across turns.
- Item 29: partial progress — completed-turn cockpit display is now implemented;
  retention/delete UX remains open.