# Mission 057 — Spend Limit Control and Confirmation UX (Frontend)

**Status:** PASS (LOCAL)
**Route:** whoever's next up
**Punch Board item:** 17 (close — spend visibility, warning, and gate all real end to end)
**Base:** main @ 6e2f0e9 "feat(modelmix): native oauth connect/disconnect (Mission 056)"

## Objective

A user can set a spend limit from Settings, persisted locally, sent on every run. When a run is rejected for exceeding it, the user sees the REAL backend message (which seat, what it actually cost) and can explicitly choose to proceed anyway — which resends the exact same request with `confirm_over_budget: true`, never silently retrying, never hiding that this happened.

## What changed

### 1. Persisted limit control (`frontend/src/modelmixBehavior.js`)

Added `loadSpendLimit()`/`saveSpendLimit(value)`/`clearSpendLimit()` alongside the existing behavior helpers, following the exact `guardrailSettings.js` pattern:

- `SPEND_LIMIT_STORAGE_KEY = 'modelmix.spendLimit'`
- Validation: `value > 0` (matches backend `gt=0` bound exactly), finite number
- Malformed storage -> `null`, never throws
- Broken/trowing storage tolerated (returns `false`/`null`, never throws)

### 2. `send()` wiring (`frontend/src/components/ModelMixObserver.jsx`)

- `spend_limit_usd` included in request body ONLY when a valid saved value exists
- Key is genuinely ABSENT when unset (same absence-not-null discipline as every other optional field)
- `confirm_over_budget` is NOT sent on the initial attempt

### 3. 402 handling — the real feature

When `send()` catches a `ModelMixHttpError` with `.status === 402`:
- Does NOT show as generic connection error
- Stores the original request body and real backend message in `pendingSpendConfirmation` state
- Renders the REAL backend message (which seat, actual cost) in a dedicated confirmation UI
- Offers an explicit "Proceed anyway" button (not automatic retry)
- On click: resends the EXACT SAME request body with `confirm_over_budget: true` added
- If the confirmed retry also fails: shows that failure normally (no retry loop)

### 4. Behavior section UI

Added a dollar-amount input with save/clear pair to the existing Behavior section, separated by a visual divider. Matches the established Guardrails section UX pattern.

## Files changed

| File | Change |
|---|---|
| `frontend/src/modelmixBehavior.js` | Added `SPEND_LIMIT_STORAGE_KEY`, `loadSpendLimit`, `saveSpendLimit`, `clearSpendLimit` |
| `frontend/src/components/ModelMixObserver.jsx` | `send()` wiring, 402 catch, `confirmOverBudget` callback, `pendingSpendConfirmation` state, BehaviorSection spend limit UI, `ModelMixSettings` prop threading |
| `frontend/src/components/ModelMixObserver.css` | `.modelmix-spend-confirmation`, `.modelmix-spend-confirmation-message`, `.modelmix-spend-confirm`, `.modelmix-settings-divider` |
| `frontend/src/modelmixBehavior.test.js` | 4 new tests for spend limit round-trip, validation, malformed storage, broken storage |
| `frontend/src/components/ModelMixSendBehavior.test.jsx` | 3 new tests for `spend_limit_usd` inclusion/omission, `confirm_over_budget` absence |
| `frontend/src/components/ModelMixSpendLimit.test.jsx` | New file, 6 tests: 402 rendering, confirm-and-retry exact payload, non-402 exclusion |

## Validation actually run

### Frontend tests
```
Test Files  19 passed (19)
     Tests  228 passed (228)
```
(215 existing + 13 new = 228, all pass)

### Frontend build
```
✓ built in 1.79s
```

### Frontend lint
```
(no output — clean)
```

### Backend tests
```
297 passed, 247 errors
```
All 247 errors are `PermissionError: [WinError 5] Access is denied: 'C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo'` — pre-existing Windows temp-directory ACL issues, not related to this mission (zero backend files touched). The 297 tests that can run all pass.

## Acceptance criteria

1. `loadSpendLimit`/`saveSpendLimit`/`clearSpendLimit` round-trip correctly; invalid values rejected; malformed storage returns `null` — **PASS** (4 tests in `modelmixBehavior.test.js`)
2. `send()`'s request body includes `spend_limit_usd` when saved, key genuinely ABSENT when unset — **PASS** (2 tests in `ModelMixSendBehavior.test.jsx`)
3. `confirm_over_budget` never present on initial request — **PASS** (1 test in `ModelMixSendBehavior.test.jsx`)
4. Mocked 402 renders real backend message, not generic error — **PASS** (1 test in `ModelMixSpendLimit.test.jsx`)
5. Confirm-and-retry resends identical original body plus `confirm_over_budget: true` — **PASS** (1 test in `ModelMixSpendLimit.test.jsx`)
6. All 215 existing frontend tests pass unmodified — **PASS** (228 total = 215 + 13 new)
7. `npm run build` and `npm run lint` succeed — **PASS**

## Boundaries respected

- Zero backend files touched
- No auto-retry of 402 without explicit user action
- `confirm_over_budget` never persisted (one-shot confirmation in component state only)
- `applyModelMixEvent` and run/event state logic untouched
- No new dependencies

## Punch Board item 17 status

Item 17 is now **closeable**. All three halves are real end to end:
- Visibility: cost computation (044), frontend rendering (045)
- Warning: backend threshold event (050), frontend rendering (051)
- Gate: backend enforcement (052), frontend control + confirmation UX (057)
