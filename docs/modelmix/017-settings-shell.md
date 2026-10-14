# Mission 017 — Settings Shell

Route: Big Pickle (OpenCode Zen)
Punch Board items: 26 (advance), 4 (toward satisfied), 24 (Settings surface)
Base: `main` @ `a30dbfa` "feat(modelmix): compact top bar and panel view controls (Mission 016)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Give the ModelMix cockpit a real Settings entry that opens an in-app overlay
(no new route, no new window) with three honest sections — **About**, **Providers**,
**Defaults** — while exporting the existing configured-source truth for reuse,
teaching the cockpit to apply saved default seat models, leaving the credential
flow in the separate Council route untouched, and not regressing any of the 51
existing frontend tests.

## Delivered

### 1. `configuredSources` exported for direct use

`frontend/src/configuredModels.js` changes one line: the private helper
`function configuredSources(settings)` becomes `export function
configuredSources(settings)`. The implementation is byte-identical, so
`discoverConfiguredModels` behavior is unchanged. This satisfies the
direct-import + call test path (see Test 1) and lets the Providers section reuse
exactly the same truth the model-discovery path uses — no duplicated derivation.

### 2. Settings entry in the top bar and a conditional overlay

`header.modelmix-topbar` gains one small gear control
(`button.modelmix-settings-toggle`, `aria-label="Settings"`, `aria-expanded`)
placed after Back to Council. The Settings overlay is **conditionally rendered
only while open** (`settingsOpen`), so the closed strip never contains the word
"Settings" in `textContent` — preserving the existing test assertion
(`ModelMixObserver.test.jsx:99`) that no "Settings" text exists in the default
cockpit. The overlay itself is a modal dialog for keyboard/AT surface:

- backdrop (`modelmix-settings-backdrop`) closes on click;
- the dialog (`role="dialog"`, `aria-modal="true"`, `aria-label="Settings"`)
  stops the click from bubbling so inner content never closes it;
- a close control (`✕`, `aria-label="Close Settings"`) dismisses it;
- a three-item nav (About / Providers / Defaults) switches sections in place;
  the active item carries `aria-pressed`.

No new route: the overlay lives inside `ModelMixObserver` and toggles local
state only. `Settings.jsx`/`App.jsx` (the separate Council React root) are
untouched; the mission did not touch `main.jsx`, SSE, `modelmixState.js`, or the
backend.

### 3. About — real version, real license, text-only attribution

`ModelMixObserver` imports `pkg from '../../package.json'` and the About section
renders `Version {pkg.version}` from that import (no duplicated literal). It
also renders the license line verified from the repository `LICENSE` ("MIT —
Copyright (c) 2025 Jacob Ben David") and the README-verified attribution
"ModelMix began as a fork/evolution of The AI Counsel, an open-source
multi-model AI project" — **text only, no invented upstream URL** (the inherited
README attributes upstream in prose; the mission adds no external link that does
not exist in the repository). The real ModelMix repo URL
(`https://github.com/wpedigo1/ModelMix`) is rendered as a link, matching the
`git clone` URL already present in `README.md:280`.

### 4. Providers — read-only, computed from the walked settings snapshot

During initial model discovery, `loadModels` now keeps the settings it already
fetched (`settingsSnapshot`). The Providers section computes `configuredSources`
against that snapshot at render time (only inside the section render, so mocked
tests that never open Settings never call it) and lists five read-only rows:

```
OpenRouter          Connected | Not connected
Ollama (local)      Connected | Not connected
Direct API keys     Connected | Not connected
Custom endpoint     Connected | Not connected
OAuth accounts      Connected | Not connected
```

The rows carry a `data-connected` attribute for styling. No credential **value**
is ever rendered — the settings object only holds boolean `*_key_set` /
`*_connected` flags and endpoint/base URLs, and neither the endpoint URLs nor
any `sk-*` material appears in the provider list (asserted in Test 7). When the
settings snapshot is `null` (e.g. discovery failed), the section says provider
status is unavailable instead of faking "Not connected" rows. A link points to
`/` where credentials are actually managed — the Settings shell adds no entry
fields and no new storage of secrets.

### 5. Defaults — localStorage-backed seat defaults, applied at initial mount

New pure module `frontend/src/defaultSeatModels.js`:

- `DEFAULT_SAVED_MODELS_KEY = 'modelmix.defaultSeatModels'`;
- `FALLBACK_SEAT_MODELS = Object.freeze({ worker_a: 'openai-oauth:gpt-5',
  moderator: '', worker_b: 'ollama:llama3' })` — exactly the literals the
  cockpit previously hardcoded, now frozen and regression-tested;
- `loadSavedSeatModels(storage)` — null-safe, returns `null` for missing /
  unparseable / wrong-shape values (only a plain object whose three seat keys
  are all strings parses), never throws, even against throwing storage;
- `saveSeatModels(storage, models)` / `clearSavedSeatModels(storage)` — returns
  a boolean, silently `false` on missing/throwing storage.

`ModelMixObserver` reads the saved trio once (`useMemo`), and the three seat
selectors initialize from `savedSeatModels?.<seat> ?? FALLBACK_SEAT_MODELS.<seat>`.
Because the pasted default now comes from the same source that produces the
fallbacks, criterion 5 is a direct regression guarantee: with no saved value the
cockpit mounts the exact built-in selections, and any saved value wins.

The Defaults section shows the current selections per seat, a saved/no-saved
status line, a **Save current selections as defaults** action (writes the trio),
and a **Clear saved defaults** action (removes the key, disabled when nothing is
saved). A `defaultsRevision` counter forces a re-render after either action so
the section reflects the just-written storage. The section reads storage at
render, so it always reflects reality.

### Architecture boundaries preserved

- Worker independence, Moderator fan-in, SSE/replay, persistence interface, and
  the run/event model are untouched; `modelmixState.js`, `modelmixApi.js`, and
  all backend files are byte-identical to Mission 016.
- No `Settings.jsx`/`App.jsx` change; the Council route remains the credential
  surface; Settings here is read-only status, `localStorage`, and About text.
- No new dependencies, no lockfile changes, no credential handling changes.
- Guardrails (usage warnings, output warning, hard cap) were **not** wired and
  no placeholder toggles were added — they remain open for a later mission.

## Test Evidence

3 new files; no existing test file was modified.

### New — `frontend/src/configuredSources.test.js` (node env, 5 tests)

1. `reports every source connected when all credentials are configured`.
2. `reports no sources when nothing is configured`.
3. `a provider explicitly disabled in enabled_providers stays off despite
   credentials`.
4. `oauth requires both a connected flag and the provider not being disabled`.
5. `direct requires at least one configured direct key flag`.

These exercise the now-exported `configuredSources` directly (criterion 1).

### New — `frontend/src/defaultSeatModels.test.js` (node env, 5 tests)

1. `fallback seat models match the built-in default selections` — pins
   `FALLBACK_SEAT_MODELS` to `openai-oauth:gpt-5` / `''` / `ollama:llama3` and
   frozen (the direct regression for criterion 5's built-in defaults).
2. `loadSavedSeatModels returns null when nothing is saved` — including
   `undefined` and empty-storage cases.
3. `parses a saved trio and rejects corrupt shapes without throwing` — bad JSON,
   missing seats, non-string seats, array values; extras are dropped.
4. `saveSeatModels writes the trio and clearSavedSeatModels removes it` — the
   save/load/clear round trip (criterion 8 at unit level).
5. `helpers tolerate broken or throwing storage without throwing`.

### New — `frontend/src/components/ModelMixSettings.test.jsx` (jsdom render tests, 8)

Renders the real `ModelMixObserver` with gravitational mocks: `../api`
(`getSettings` returns a mutable `mockSettings.value`), `../configuredModels`
(kept via `importOriginal` so the **[real]** `configuredSources` runs, with a
mutable `mockDiscovered.value`), and `../modelmixApi` (hydrate rejects a 404 so
the observe loop never spins). The `vi.hoisted` container pattern avoids the
vitest hoisting/TDZ trap. Cleanup unmounts + removes each container and clears
`localStorage`; the render helper does **not** clear storage so saved-defaults
tests can seed before mount.

6. `gear button opens a settings dialog and the close control dismisses it` —
   closed cockpit has no `.modelmix-settings` and no "Settings" text; open shows
   the `role="dialog"` `aria-modal="true"` section; close restores the closed
   DOM (criterion 2).
7. `About section renders the version from package.json with license and
   attribution` — asserts `Version ${pkg.version}` where `pkg` is itself
   imported from the same `../../package.json`, plus the copyright and
   attribution text (criterion 3, no duplicated literal).
8. `Providers section lists every source as connected for all-configured
   settings with no credential values` — five `Connected` rows with
   `data-connected="true"`, and the provider list text contains neither `sk-`
   nor the endpoint/base URLs (criterion 4, all-configured).
9. `Providers section lists every source as not connected when nothing is
   configured` — five `Not connected` rows (criterion 4, none-configured).
10. `without saved defaults the hardcoded built-in seat selections win on mount`
    — Worker A shows `gpt-5 (ChatGPT)`, Worker B `llama3`, Moderator renders the
    placeholder (criterion 5).
11. `saved defaults win over the hardcoded selections on mount` — seeded
    `modelmix.defaultSeatModels`; Worker A/Moderator/Worker B all show the saved
    models, and the empty Defaults section reports the saved state
    (criterion 6).
12. `a corrupted saved value falls back to the built-in defaults without
    throwing` — garbage value; selectors fall back, no error (criterion 7).
13. `Defaults section saves the current selections and Clear removes them` —
    shows the built-in trio initially + clear disabled + "No saved defaults";
    Save writes the trio to storage and flips the status line + enables Clear;
    Clear removes the key and re-flips the section (criteria 6/8 through the UI).

### Existing tests pass unmodified

`modelmixState.test.js` (35), `configuredModels.test.js` (3), `fontSize.test.js`
(3), `panelView.test.js` (4), and `ModelMixObserver.test.jsx` (6, including the
line-99 "no Settings text" and line-100 "no settings links" assertions) all pass
untouched (criterion 9). Total observed: **69 passed**.

## Validation — raw, unedited

From `frontend/`:

```text
npm test

> the-ai-counsel@0.11.4 test
> vitest run

 ✓ src/defaultSeatModels.test.js (5 tests) 7ms
 ✓ src/utils/fontSize.test.js (3 tests) 5ms
 ✓ src/configuredSources.test.js (5 tests) 6ms
 ✓ src/panelView.test.js (4 tests) 8ms
 ✓ src/configuredModels.test.js (3 tests) 20ms
 ✓ src/modelmixState.test.js (35 tests) 43ms
 ✓ src/components/ModelMixObserver.test.jsx (6 tests) 342ms
 ✓ src/components/ModelMixSettings.test.jsx (8 tests) 381ms

 Test Files  8 passed (8)
      Tests  69 passed (69)
```

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
✓ 436 modules transformed.
✓ built in 1.81s
```

From the repository root (backend unchanged, suite still required):

```text
uv run pytest backend/tests -q

........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 13.57s
```

`git status --short` (after all edits, before staging):

```text
 M frontend/src/components/ModelMixObserver.css
 M frontend/src/components/ModelMixObserver.jsx
 M frontend/src/configuredModels.js
 ?? frontend/src/defaultSeatModels.js
 ?? frontend/src/defaultSeatModels.test.js
 ?? frontend/src/configuredSources.test.js
 ?? frontend/src/components/ModelMixSettings.test.jsx
 ?? docs/modelmix/017-settings-shell.md
```

No backend changes, no `data/` changes, no lockfile changes, no dependency
changes. One implementation bug was caught by tests during the run and fixed:
the first vitest pass failed 3 suites because `../package.json` is not a valid
import path from `src/components/` (needs `../../package.json`), and
`loadSavedSeatModels` only guarded `JSON.parse`, not a throwing `getItem`. Both
were corrected and the clean 69/69 run above is the final observed result.

## Punch Board Mapping

- **Item 26 — provider/settings UX (advanced):** the Settings surface now exists
  in the cockpit as a real entry with read-only provider status derived from
  exported `configuredSources`. Credential entry/edit still lives in the Council
  `/` route; full alpha provider/settings flow remains open.
- **Item 4 — license and provenance (partial):** the About section now surfaces
  the MIT license, the copyright holder, the real app version, the text-only AI
  Counsel attribution, and the repo URL. `OPEN_SOURCE_CREDITS.md`, inherited-
  module provenance, and the shipped dependency-license inventory remain open.
- **Item 24 — thin top controls (advanced):** the Settings entry is no longer
  missing; the compact strip now ends in a gear that opens the overlay. The
  interactive Mode selector (Solo/Compare, items 27/28) remains open.
- Items 27/28 (Solo/Compare), 25 (telemetry rendering), 17 (guardrails), 30–33
  are untouched by this mission.

## Immediate Next Engineering Gap

The Settings shell is status/About/defaults only. The primary rendering gap is
unchanged from Mission 016: Mission 015's telemetry truth layer is still
capture-only, so the cockpit should surface honest per-seat provider-reported
labels and timing (no telemetry dashboard; estimates/unknowns labeled exactly as
required) before the alpha acceptance run (item 33). The guardrails (usage
warning, output warning, hard cap) remain explicitly open and should be wired
when the settings/run-control layer reaches them — this mission deliberately did
not add placeholder toggles.