# Mission 020 — Configurable Output Guardrails (Backend)

Route: Big Pickle (OpenCode Zen)
Punch Board items: 17 (advance — per-request configurability of the output guardrails)
Base: `main` @ `a96d8f1` "fix(modelmix): explicitly close provider stream on output cap (Mission 019 follow-up)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

A caller of `POST /api/modelmix/runs/stream` can optionally override the
warning threshold and hard cap for that one run. Omitting either falls back to
the existing Mission 019 module defaults. Invalid values are rejected with a
clear 422 **before any provider call is made** — never silently clamped, never
silently ignored. This is a per-request override only; nothing is persisted.

## Delivered

### 1. `routes.py` request contract

`TwoWorkerRequest` gains two optional fields:

```text
warning_threshold_chars: Optional[int] = Field(default=None, gt=0)
hard_cap_chars: Optional[int] = Field(default=None, gt=0)
```

Pydantic's `gt=0` rejects non-positive supplied values at parse time.

### 2. Validation — reject before the run starts

`stream_two_workers` first resolves both fields to enforced values via a new
private `_resolve_guardrail_overrides(warning_threshold_chars, hard_cap_chars)`
helper, which:

- defaults a `None` field to the Mission 019 module constant
  (`guardrails.WARNING_OUTPUT_THRESHOLD_CHARS` / `HARD_OUTPUT_CAP_CHARS`);
- rejects supplied values outside the sanitized range — both must lie within
  `guardrails.MIN_OUTPUT_CHARS_BOUND = 100` and
  `guardrails.MAX_OUTPUT_CHARS_BOUND = 200_000` (named constants in
  `guardrails.py`, no magic numbers in routes). The point of a hard cap is cost
  protection: an override that can set it arbitrarily high defeats the feature,
  and a near-zero value produces degenerate useless output. The single
  `MIN`/`MAX` range also covers the "positive integer after defaulting" guard,
  including the case where only one of the two fields was supplied.
- rejects `hard_cap_chars < warning_threshold_chars` after resolution — a cap
  smaller than the warning point would cap before ever warning.

Any violation raises `ValueError`; `stream_two_workers` catches it and wraps it
in `HTTPException(status_code=422, detail=str(exc))`, the exact pattern already
used for `PersistenceError` in this handler. Because the invalid value is
rejected before `run_registry.start(...)`, no provider is ever resolved or
called.

### 3. Threading the override through the canonical chain

The override rides the exact `seat_timeout`/`seat_histories` call chain — no
parallel path invented:

- `RunRegistry.start(...)` gains `warning_threshold_chars: Optional[int] = None`
  and `hard_cap_chars: Optional[int] = None`, threaded positionally into
  `self._run(...)`.
- `_run(...)` forwards them into `self._run_phase(...)`.
- `_run_phase(...)` passes them to **both** consumers:
  - `multiplex_workers(..., warning_threshold_chars=..., hard_cap_chars=...)`;
  - `run_moderator(..., warning_threshold_chars=..., hard_cap_chars=...)`.
- `routes.py::stream_two_workers` passes the already-resolved,
  already-validated values to `run_registry.start(...)`.

`multiplex_workers` and `run_moderator` each gain the same two optional
parameters and resolve them inside exactly like `seat_timeout`
(`bound = timeouts.SEAT_TIMEOUT_SECONDS if seat_timeout is None else
seat_timeout`):

```python
warning_limit = (
    guardrails.WARNING_OUTPUT_THRESHOLD_CHARS
    if warning_threshold_chars is None
    else warning_threshold_chars
)
cap = (
    guardrails.HARD_OUTPUT_CAP_CHARS
    if hard_cap_chars is None
    else hard_cap_chars
)
```

Only where the two threshold numbers come from changed — the resolved values
feed the existing `clip_delta(...)` cap argument and the one-shot warning check
in both the streaming and non-streaming branches, in `run_seat` and
`run_moderator`. Mission 019's enforcement logic, event payloads
(`seat_output_warning` / `moderator_output_warning` with `chars`/`threshold`),
and the `modelmix_output_cap` finish reason are byte-for-byte unchanged.

### 4. Boundaries preserved

- **Frontend: zero changes.** The frontend does not send these fields yet; when
  it doesn't, both remain `None` and behavior is byte-identical to Mission 019.
  Regression proof is the route test below that posts a body with no guardrail
  fields and asserts the module defaults are enforced end-to-end.
- `guardrails.clip_delta` signature and logic untouched (it always took `cap`;
  only the value passed in changes).
- `seat_timeout`/`run_timeout` handling untouched — this is a parallel,
  independent override mechanism.
- `ModeratorOutputLimits` token-shaped preview contract untouched.
- No persistence of a chosen threshold anywhere — per-request only, matching
  the locked "no new session/document field" scope.
- `events.py`, `persistence.py`, `journal.py`, `timeouts.py`, `history.py`,
  `council/`: byte-identical. No new dependencies.

## Test Evidence

13 new tests in `backend/tests/test_modelmix_guardrails.py` (no existing test's
assertions modified). Route-level tests drive the full
`routes → registry.start → _run → _run_phase → multiplex_workers/run_moderator`
chain through a FastAPI `TestClient` with a `RunRegistry` on a
`tmp_path` `AtomicJsonModelMixPersistence`, and record the provider resolver to
prove it was never invoked on rejection:

1. `test_route_without_override_fields_enforces_module_defaults` — body with no
   guardrail fields; non-streaming providers emitting `40_000 + 5_000` chars;
   each seat truncated to exactly `guardrails.HARD_OUTPUT_CAP_CHARS`,
   `finish_reason == "modelmix_output_cap"`, run `completed`. *(Criterion 1;
   Mission 019 defaults through the full route/registry path)*
2. `test_route_smaller_cap_than_default_caps_seat` — `{warning: 100,
   hard_cap: 120}`; 5_000-char content truncated to exactly 120 per seat,
   capped terminal — a cap far under the 40_000 default, proving earlier
   capping. *(Criterion 2)*
3. `test_route_smaller_warning_fires_earlier_than_default` — `{warning: 100}`
   only (cap → default); streaming 150 chars; exactly one `seat_output_warning`
   with `threshold == 100`, `chars == 100`, seat completes `stop`. *(Criterion 3)*
4. `test_route_rejects_cap_below_warning_before_provider_call` —
   `{warning: 500, hard_cap: 300}` → 422, message present, resolver never
   called (`resolved == []`). *(Criterion 4)*
5. `test_route_resolves_omitted_warning_to_default_before_cross_check` —
   `{hard_cap: 150}` only → default warning 20_000 > 150 → 422, resolver never
   called. *(Criterion 4 / 6 cross-check)*
6. `test_route_rejects_out_of_bounds_override_before_provider_call`
   (parametrized ×4) — `warning_threshold_chars`/`hard_cap_chars` at
   `MIN_OUTPUT_CHARS_BOUND - 1` and `MAX_OUTPUT_CHARS_BOUND + 1` → 422, message
   present, resolver never called. *(Criterion 5)*
7. `test_route_only_cap_supplied_uses_default_warning_and_enforces_cap` —
   `{hard_cap: 25_000}` only (≥ default warning 20_000); 26_000-char content
   truncated to exactly 25_000 per seat, capped terminal. *(Criterion 6)*
8. `test_route_only_warning_supplied_uses_default_cap` — `{warning: 1_000}`
   only; streaming 1_100 chars; exactly one warning (`threshold == 1_000`),
   seat completes `stop`, no `modelmix_output_cap` anywhere. *(Criterion 7)*
9. `test_moderator_honors_per_request_override` — `run_moderator` with
   `warning_threshold_chars=10`, `hard_cap_chars=30`; exact event sequence
   `[started, delta, output_warning, delta, completed]`, joined output
   `"a"*20 + "b"*10` (30 chars), warning `chars == 20`, `threshold == 10`,
   terminal `moderator_completed` `finish_reason == "modelmix_output_cap"`.
   *(Criterion 8, at the run_moderator level)*
10. `test_registry_threads_override_to_workers_and_moderator` — `registry.start`
    with `{warning: 15, hard_cap: 35}` and a Moderator; both worker seats emit
    exactly 35 chars with the capped finish and the Moderator emits exactly 35
    chars with the capped finish — proving `_run_phase` delivers the override to
    both consumers. *(Criterion 8 threading)*

## Validation

Raw output, run from the repo root:

### Targeted suites

```text
.venv\Scripts\python -m pytest backend\tests\test_modelmix_guardrails.py backend\tests\test_modelmix_streaming.py backend\tests\test_modelmix_moderator.py backend\tests\test_modelmix_persistence.py -q
.................................................................        [100%]
65 passed in 5.09s
```

### Full backend suite

```text
.venv\Scripts\python -m pytest backend\tests -q
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 92%]
............................                                             [100%]
388 passed in 15.44s   (375 prior + 13 new)
```

### Lint

```text
.venv\Scripts\ruff check backend\modelmix\guardrails.py backend\modelmix\orchestrator.py backend\modelmix\moderator.py backend\modelmix\registry.py backend\modelmix\routes.py backend\tests\test_modelmix_guardrails.py
All checks passed!
```

### Frontend (unchanged, still validated)

```text
npm test
  ✓ src/utils/fontSize.test.js (3 tests) 5ms
  ✓ src/defaultSeatModels.test.js (5 tests) 5ms
  ✓ src/configuredSources.test.js (5 tests) 6ms
  ✓ src/panelView.test.js (4 tests) 7ms
  ✓ src/seatTelemetry.test.js (14 tests) 11ms
  ✓ src/configuredModels.test.js (3 tests) 18ms
  ✓ src/modelmixState.test.js (35 tests) 45ms
  ✓ src/components/ModelMixTelemetry.test.jsx (3 tests) 185ms
  ✓ src/components/ModelMixObserver.test.jsx (6 tests) 383ms
  ✓ src/components/ModelMixSettings.test.jsx (8 tests) 417ms

 Test Files  10 passed (10)
      Tests  86 passed (86)

npm run build   (vite v7.3.6, 437 modules transformed, built in 1.60s)
npm run lint    (eslint . — clean)
```

## Remaining Risks / Open

- The configured bounds (`100`–`200_000`) apply to the per-request override
  path only; the module default constants are, by definition, inside them.
  These are provisional and belong to a future Settings mission that will also
  surface them in the UI.
- Non-streaming (`provider.query`) overrides cannot demonstrate the warning
  (that path never warns by design, per Mission 019); the cap is still enforced
  exactly there.
- The frontend does not yet send these fields; wiring them into the request
  body from the cockpit settings is a deliberate later mission ("make it feel
  persistent" — local preference storage, not server persistence).
- Route-level bounds/cross-check validation lives in `routes.py`; the
  enforcement points (`multiplex_workers`/`run_moderator`) remain permissive
  consumers of whatever numbers they are given, matching the `seat_timeout`
  precedent exactly.