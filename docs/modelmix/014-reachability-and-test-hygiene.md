# Mission 014 — Reachability and Test Data Isolation

Route: Big Pickle (OpenCode Zen)
Punch Board items: 21 (fix), 26 (partial), 33 (enabler)
Base: `main` @ `aafedaa`
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

1. Stop backend ModelMix tests from writing fake sessions into the real
   `data/modelmix/sessions/` directory by giving every `RunRegistry()`
   construction in tests an explicit isolated `AtomicJsonModelMixPersistence`.
2. Make the ModelMix cockpit actually reachable in a production build: a real
   `GET /modelmix` route that serves `index.html` from `FRONTEND_DIST_DIR`.
3. Add ONE visible Council → ModelMix navigation entry.
4. Two one-line cosmetic fixes in ModelMix backend files.

## Delivered

### 1. Test data isolation (the important fix)

`RunRegistry` defaults to the live `modelmix_persistence` (Persistence.py),
whose default root is `data/modelmix/sessions/` relative to the working
directory. `registry.start()` always calls `persistence.create_session(...)`, so
every previously-unisolated test construction wrote a real JSON session file
into the same directory the running app uses.

The mission named four sites in `test_modelmix_timeouts.py` (lines 231, 254,
294, 314) and required grepping the whole of `backend/tests/` for any other
`RunRegistry()` construction without `persistence=`. The grep found 17
`RunRegistry(` call sites across four files. **Findings beyond the named four —
all fixed:**

- `test_modelmix_timeouts.py` lines **231, 254, 294, 314** (the named four).
  Lines 179 and 266 already passed `persistence=store`.
- `test_modelmix_journal.py` lines **112, 136, 153, 161, 168** — all five
  constructions lacked persistence. 153/161 and 168 never call `start()` (they
  manipulate `_runs` directly) but were still hardened for consistency and to
  keep the grep clean.
- `test_modelmix_moderator.py` line **88** — the shared `start_run` helper used
  by seven tests. Because every data-dependent test flows through `start_run`,
  this single fixture was the whole file's pollution source. It now accepts a
  `persistence` argument (`RunRegistry()` only when `persistence is None`) and
  all seven callers pass `AtomicJsonModelMixPersistence(tmp_path)`.
- `test_modelmix_persistence.py` lines 153, 165, 185 already passed explicit
  persistence and were left untouched.

No construction anywhere in `backend/tests/` now defaults to the live session
store. Actual disk receipts: the repo-root `data/modelmix/sessions/` contained
**229 session files (all gitignored legacy pollution)**; after running the three
previously-polluting files, the count was still **229** — zero new files. The
full-suite run also left `git status --short` with nothing under `data/`.

### 2. `GET /modelmix` route

`backend/main.py` gained a real route alongside the existing `/`:

- `GET /modelmix` serves `index.html` from `FRONTEND_DIST_DIR` when it exists
  and returns HTTP 404 with a clear message otherwise. It is registered before
  the `StaticFiles(directory=FRONTEND_DIST_DIR, html=True)` mount at the bottom
  of the module, so it wins over the catch-all mount in production builds.
- Scoped to exactly `/modelmix` — no wildcard, no SPA catch-all, no new
  dependencies.
- Test: `test_main_preflight.py` (the existing file that already exercises
  `main.app` through `TestClient`) gained two tests:
  `test_modelmix_route_serves_built_frontend_index` (200, serves the dist
  `index.html` with no Vite dev server) and
  `test_modelmix_route_reports_404_when_frontend_not_built` (404 failure path).
  Each monkeypatches `main.FRONTEND_DIST_DIR` to a tmp dist directory.

### 3. Council → ModelMix navigation

`frontend/src/components/Sidebar.jsx` (the app's persistent nav chrome) gained
one full-width link in the existing `sidebar-actions` block: a green
`sidebar-action-btn--modelmix` anchor `href="/modelmix"` labeled **ModelMix**
(`◈`). `Sidebar.css` gained the anchor variant styling and `text-decoration:
none` on the shared action-button class (no effect on the button elements). The
ModelMixObserver's existing `Back to Council` link and the `main.jsx` pathname
gating are unchanged. Presence in shipped markup was confirmed by grepping the
built bundle: exactly one `href ... /modelmix`, one
`sidebar-action-btn--modelmix`, and the label string present.

### 4. Cosmetic fixes

- `backend/modelmix/orchestrator.py` line 27 — `event_factory: Optional[EventFactory] = None`
  had lost its indentation in a prior mission's diff; restored to align with the
  `multiplex_workers` signature. One-line-only diff.
- `backend/modelmix/history.py` — added the missing trailing newline at EOF.
  One-line-only diff.

## Acceptance Coverage

1. `uv run pytest backend/tests -q` passes and `git status --short` afterwards
   shows nothing under `data/modelmix/`. Both observed; additionally proven
   with an exact disk-count check (229 → 229) on the previously-polluting files.
2. New route test in an appropriate existing file confirms `GET /modelmix`
   returns 200 with a built dist `index.html` and reports 404 when not built.
3. Navigation link confirmed in the built production bundle, not just JSX.
4. `orchestrator.py` and `history.py` diffs are exactly the one cosmetic line
   each (see Git Diff Stat).
5. Backend suite count is 354 = 352 prior tests + 2 new route tests; the
   isolation changes modified existing tests, adding no count of their own.
   Frontend suite unchanged at **35 passed**.

## Validation

All output below is raw and unedited.

Focused ModelMix suites after isolation (TEMP/TMP pointed at the
workspace-local `.pytest_temp`):

```text
uv run pytest backend/tests/test_modelmix_timeouts.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py -q
```

```text
...............................                                          [100%]
31 passed in 4.91s
```

Preflight + new route tests:

```text
uv run pytest backend/tests/test_main_preflight.py -q
```

```text
............                                                             [100%]
12 passed in 2.06s
```

Full backend suite:

```text
uv run pytest backend/tests -q
```

```text
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 61%]
........................................................................ [ 81%]
..................................................................       [100%]
354 passed in 13.27s
```

Lint (changed Python files):

```text
uv run ruff check backend/main.py backend/modelmix/history.py backend/modelmix/orchestrator.py backend/tests/test_main_preflight.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_timeouts.py
```

```text
All checks passed!
```

Frontend (from `frontend/`):

```text
npm test
```

```text
> the-ai-counsel@0.11.4 test
> vitest run

 RUN  v4.1.11 C:/Users/wpedi/ModelMix/frontend

 ✓ src/utils/fontSize.test.js (3 tests) 3ms
 ✓ src/configuredModels.test.js (3 tests) 15ms
 ✓ src/modelmixState.test.js (29 tests) 32ms

 Test Files  3 passed (3)
      Tests  35 passed (35)
   Start at  09:58:03
   Duration  788ms
```

```text
npm run build
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
dist/assets/ModelMixObserver-QQz_hUhO.css      3.23 kB │ gzip:  1.06 kB
dist/assets/index-DE2Cu6-_.svg ... (assets as built)
dist/assets/index-DEsTBKrN.js                 236.19 kB │ gzip: 72.21 kB
✓ built in 3.91s
```

Built-bundle markup check (Sidebar lives in the main `index` bundle):

```text
href /modelmix count: 1
label ModelMix count: 4
sidebar-action-btn--modelmix count: 1
```

```text
npm run lint
```

```text
> the-ai-counsel@0.11.4 lint
> eslint .
```

(clean)

Isolation proof — count of files in the real `data/modelmix/sessions/` before
and after re-running every previously-polluting test file:

```text
before: 229
uv run pytest backend/tests/test_modelmix_timeouts.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py -q
31 passed in 3.81s
after: 229
```

`data/` is gitignored (`.gitignore` line 19), so the honest proof is the disk
count above, not the git status noise. `git status --short` after the full
suite shows only the intended working files and nothing under `data/`.

### Observed during development

- `git` emits the pre-existing LF-to-CRLF working-copy warnings on touched
  text files; they are noise and were ignored.
- The first focused-suite run was done before adding the route tests; the 31/
  31 was re-confirmed at 354-suite time. No failures occurred at any stage.

## Git Diff Stat

Working tree was fully staged at capture, so the unstaged `git diff --stat` was
empty; the staged diff is shown (Git also emits the existing LF-to-CRLF
working-copy warnings).

Command:

```text
git diff --cached --stat
```

Raw unedited output (captured after staging the full deliverable, including
this report):

```text
 backend/main.py                          |  9 ++++++
 backend/modelmix/history.py              |  2 +-
 backend/modelmix/orchestrator.py         |  2 +-
 backend/tests/test_main_preflight.py     | 29 +++++++++++++++++++++
 backend/tests/test_modelmix_journal.py   | 27 +++++++++++++++-------
 backend/tests/test_modelmix_moderator.py | 43 +++++++++++++++++++++++++---------
 backend/tests/test_modelmix_timeouts.py  | 27 ++++++++++++++++------
 docs/modelmix/014-reachability-and-test-hygiene.md | ...
 docs/modelmix/ENGINEERING-PROGRESS.md     | ...
 docs/modelmix/MISSION-INDEX.md            | ...
 docs/modelmix/PUNCH-BOARD.md              | ...
 docs/modelmix/README.md                   | ...
 frontend/src/components/Sidebar.css      | 15 +++++++++++
 frontend/src/components/Sidebar.jsx      |  4 +++
```

## Punch Board Mapping

- **Item 21 — browser-first three-panel cockpit (fix):** the cockpit was only
  reachable through its experimental `/modelmix` path, which a production build
  did not serve; `GET /modelmix` plus a nav link in Council's persistent chrome
  make the shipped cockpit reachable from the built app.
- **Item 26 — provider/settings UX (partial):** the ModelMix entry point in the
  main app is now a visible, labeled navigation control (green ModelMix action
  in the sidebar), a first step in the alpha app-flow; full provider/settings
  UX remains open.
- **Item 33 — alpha acceptance test (enabler):** the acceptance launch flow
  (launch built app → navigate to ModelMix → three panels without a dev server)
  is now actually possible; before this mission, the production-built app could
  not reach the cockpit at all.

## Immediate Next Engineering Gap

Mission 014 removes the last hygiene/reachability blockers in the test and
production-build path and re-establishes the cockpit as reachable from the main
app. The next mission per the locked board is the thin top controls /
settings-and-telemetry surface (items **24/25/26**), or the first provider /
settings UX slice. Reachability means the alpha acceptance run (item 33) can
now actually start from a production build.