# Mission 016 — Compact Top Bar and Panel View Controls

Route: Big Pickle (OpenCode Zen)
Punch Board item: 24 (further advanced)
Base: `main` @ `1b449ec` "feat(modelmix): telemetry truth layer (Mission 015)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Replace the cockpit's separate header and always-visible run metadata with
**one thin persistent top strip**, and give each conversation panel its own
view controls (collapse the transcript body, maximize one panel over the other
two, one Reset) without ever unmounting a panel, without touching server-backed
state, and without adding a Settings surface or a real Mode selector.

## Delivered

### 1. Compact persistent top strip

`ModelMixObserver` now renders one `header.modelmix-topbar` instead of
`.modelmix-header` + always-visible `.modelmix-run-meta`:

- **Brand** — `ModelMix` as a thin display header; the "Experimental cockpit"
  kicker is dropped (allowed by the lock: the kicker may drop or shrink).
- **`Mode: Mix`** — a plain inert `<span>`, not a button/dropdown. There is no
  Solo/Compare mode (Punch Board items 27/28 remain open), so nothing here is
  interactive.
- **Session status** — reuses the existing `observer.overall` vocabulary
  verbatim (`idle`, `connecting`, `running`, `reconnecting`, `cancelling`,
  `completed`, `partial`, `failed`, `cancelled`, `replay_gap`, `expired`); no
  new status words were invented. Colored by the same `data-status` CSS pattern
  the panel headers use.
- **New Session** — moved out of `.modelmix-actions` into the strip. Same
  handler, same `modelSelectorsDisabled(observer.overall)` disabled binding,
  unchanged behavior (clears `modelmix.sessionId`, resets via `startNewSession`).
- **Details disclosure** — a small toggle, **off by default**, reveals the
  `Run: <id>` / `Last sequence: <n>` debug line. The `.modelmix-run-meta`
  element stays MOUNTED; it is hidden with CSS (`display: none`, toggled by a
  `data-open` attribute) and `aria-hidden`, so the debug truth is behind a
  disclosure rather than shown or destroyed.
- **Back to Council** — kept as-is (`<a href="/">Back to Council</a>`).
- **No Settings** entry, link, route, or gear anywhere in the strip; no new
  `window.open`/`BroadcastChannel`/cross-window behavior (items 39–41 untouched).

### 2. Model selectors, textarea, and Send/Stop untouched

The `.modelmix-composer` and `.modelmix-models` nodes stay functionally
identical: the same three `SearchableModelSelect`s, the same textarea, the same
handlers, and the same `send()` reads. The container was only re-tightened
(Send/Stop grouping and paddings) and it no longer contains the New Session
button. `controlState`, `modelSelectorsDisabled`, and the Send/Stop disabled
logic are untouched; Send and Stop remain adjacent fixed controls in
`.modelmix-actions`.

### 3. Panel view controls — CSS-hide, never unmount

New local component state in `ModelMixObserver` only:

```js
const [panelView, setPanelView] = useState(DEFAULT_PANEL_VIEW);
const [detailsOpen, setDetailsOpen] = useState(false);
```

`panelView = { maximized, collapsed }` drives layout purely through CSS classes.
The pure helpers live in a new module, `frontend/src/panelView.js`
(`PANEL_SEATS`, `DEFAULT_PANEL_VIEW`, `getPanelViewClasses`,
`panelLayoutNeedsReset`) so the class derivation is unit-testable without DOM:

- **Collapse/expand** — each panel header gains a control that toggles
  `modelmix-panel-collapsed`; the `header` and title/status stay, the
  `.modelmix-transcript` body is hidden by `.modelmix-panel-collapsed
  .modelmix-transcript { display: none; }`. The `TranscriptPane` node remains
  in the DOM and grid cell.
- **Maximize** — each panel header gains a control that sets
  `panelView.maximized` to that seat. The workers grid gains
  `modelmix-workers--maximized` (`grid-template-columns: minmax(0, 1fr)`), the
  chosen panel gets `modelmix-panel-maximized`, and the other two get
  `modelmix-panel-hidden` (`display: none`). All three `<article>` nodes stay
  mounted — only layout is hidden. Clicking a different panel's Maximize moves
  focus; clicking the active panel's Restore returns to the three-up grid.
- **Reset** — one `Reset panel layout` button is rendered only while any panel
  is collapsed or maximized (`panelLayoutNeedsReset`); it clears both keys and
  returns the grid to `1fr 1.35fr 1fr`.

**The hard technical rule held:** there is no `{!hidden && <TranscriptPane/>}`
anywhere. Panels are never conditionally unmounted; the render test proves all
three remain in the DOM after collapse/maximize.

### 4. View state never touches the ModelMix state layer

Nothing in `createModelMixState`, `applyModelMixEvent`, `hydrateModelMixState`,
`buildHistoryEntry`, or `archiveCurrentRun` changed; `modelmixState.js` and
`modelmixApi.js` are byte-identical to Mission 015. View state lives only in the
new local `panelView`/`detailsOpen` state — reload resets it, which the mission
explicitly accepts. Panels still read the same `observer` slices; view classes
are computed from `panelView` only.

No backend files changed. No dependencies were added or upgraded
(`jsdom`/`vitest` were already devDependencies). No lockfile changes.

## Test Evidence

### New tests — `frontend/src/panelView.test.js` (node env)

1. `panel class computation stays CSS-driven and mounted-safe` — pure matrix of
   `getPanelViewClasses` outputs, including the combined
   `collapsed` + `hidden` and `collapsed` + `maximized` cases.
2. `reset is offered whenever any panel is collapsed or maximized` —
   `panelLayoutNeedsReset` true for any maximize or any collapse key.
3. `default panel view is an empty layout that needs no reset`.
4. `panel view state never leaks into observable server-backed state` — asserts
   `createModelMixState()` and a real `applyModelMixEvent` result carry none of
   `maximized`/`collapsed`/`hidden`/`detailsOpen`/`panelLayout` at the state
   root or on any seat.

### New tests — `frontend/src/components/ModelMixObserver.test.jsx` (jsdom render tests)

Real render of `ModelMixObserver` under `// @vitest-environment jsdom` with
mocked `../api`, `../configuredModels`, and `../modelmixApi` (hydration returns
a completed session so the observe loop never spins):

5. `top bar is a single compact strip ...` — one strip; `Mode: Mix` is a plain
   SPAN; session status shows the hydrated `completed`; `.modelmix-actions`
   contains exactly `Send` then `Stop`; no "Settings" text or settings links;
   no `<select>` anywhere; `.modelmix-header`/`.modelmix-kicker` gone.
6. `collapse hides only the transcript body via class while the panel stays
   mounted` — `modelmix-panel-collapsed` applied, `.modelmix-transcript` and
   `h2` nodes still present, other panels untouched, Reset appears and restores.
7. `maximize keeps all three panels mounted and hides the others from layout via
   class` — 3 `<article>` nodes and 3 `.modelmix-transcript` nodes after
   maximize; hidden classes on the two non-maximized panels;
   `modelmix-workers--maximized` on the grid; Restore returns to default.
8. `maximize switches focus and reset restores the three-up grid from any
   combination` — maximize Worker B + collapse Moderator + then maximize Worker
   A, then Reset clears every view class and removes the Reset control.
9. `New Session stays in the top bar, clears the persisted session id, and
   resets transcripts` — enabled at `completed`; clears `modelmix.sessionId`
   and empties the panels' text.
10. `run metadata debug line sits behind Details, hidden by default` —
    `.modelmix-run-meta` present but `data-open="false"` and `aria-hidden`,
    holding `Run: run-001` / `Last sequence: 6`; Details toggles it on and off.

Existing frontend tests were not modified: `modelmixState.test.js` (35) plus
`configuredModels.test.js` (3) and `fontSize.test.js` (3) all pass unchanged.

## Validation — raw, unedited

From `frontend/`:

```text
npm test

> the-ai-counsel@0.11.4 test
> vitest run

 ✓ src/utils/fontSize.test.js (3 tests) 6ms
 ✓ src/panelView.test.js (4 tests) 5ms
 ✓ src/configuredModels.test.js (3 tests) 20ms
 ✓ src/modelmixState.test.js (35 tests) 43ms
 ✓ src/components/ModelMixObserver.test.jsx (6 tests) 365ms

 Test Files  5 passed (5)
      Tests  51 passed (51)
```

```text
npm run build

> the-ai-counsel@0.11.4 build
> vite build

vite v7.3.6 building client environment for production...
✓ 434 modules transformed.
✓ built in 2.21s
```

```text
npm run lint

> the-ai-counsel@0.11.4 lint
> eslint .
```

(clean)

From the repository root (backend suite required even though nothing changed):

```text
uv run pytest backend/tests -q

........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 13.42s
```

`git status --short` (after all edits, before staging):

```text
 M frontend/src/components/ModelMixObserver.css
 M frontend/src/components/ModelMixObserver.jsx
?? frontend/src/components/ModelMixObserver.test.jsx
?? frontend/src/panelView.js
?? frontend/src/panelView.test.js
```

No data/ changes, no backend changes, no lockfile changes. Note the earlier
vitest run (12:05) failed 3 render tests with leaked-DOM counts (6/9 articles)
and one cross-test button click; the fix was deterministic per-test cleanup —
`root.unmount()` inside `act` plus `container.remove()` in `afterEach`, with
`IS_REACT_ACT_ENVIRONMENT = true`. The published passing result above is the
clean, warning-free run.

## Punch Board Mapping

- **Item 24 — thin top controls (further advanced):** Mission 012 added the
  separate New Session control; Mission 016 converts the top of the cockpit
  into one compact persistent strip (brand, inert `Mode: Mix` label, session
  status, moved New Session, Details-hidden debug metadata, Back to Council)
  and adds CSS-driven per-panel view controls (collapse body, maximize over the
  other two, single Reset). **Remaining for item 24:** an interactive Mode
  selector (Solo/Compare depend on items 27/28) and the Settings surface —
  both remain explicitly open, per the mission constraints.
- Item 25 telemetry rendering, item 10/17 state that Mission 015 prepared, and
  every run/SSE/persistence contract are untouched by this mission.

## Immediate Next Engineering Gap

Mission 015's telemetry truth layer (persisted provider-reported `usage`,
`finish_reason`, `started_at`/`completed_at`, and the `describeUsage`
provenance vocabulary) is still capture-only. The next rendering mission should
surface those honest per-seat labels and timing in the cockpit without a
telemetry dashboard — still no estimated tiers, no fabrications — completing the
remaining step before the alpha acceptance gate (item 33). Within item 24, the
Mode selector and Settings surface remain open.