# Mission 030 — Solo Mode Backend Support

Route: Big Pickle (OpenCode Zen)
Punch Board item: 27 (Solo — backend half)
Date: 2026-08-31 CT
Base: `main @ a72d2b6` (Mission 029)

## Purpose

Mission 029 closed Compare (item 28). This mission delivers the backend half of
item 27 (Solo): make `worker_b_model` optional end to end so a run can consist
of Worker A alone. The frontend Solo surface (send with no `worker_b` /
Workers=1) is explicitly out of scope, keeping item 27 partially open.

## What changed

### `backend/modelmix/routes.py`

`TwoWorkerRequest.worker_b_model` is now `Optional[str] = Field(default=None,
min_length=1)`. The route rejects the worker_b-absent + moderator hybrid with
`422` **before** any provider resolver call:

```python
if body.worker_b_model is None and body.moderator_model is not None:
    raise HTTPException(status_code=422, detail=...)
```

This enforces the locked boundary that Solo is exactly one participant — a
"moderator + one worker" hybrid is not a supported mode.

### `backend/modelmix/registry.py`

- `RunRegistry.start` / `_run` / `_run_phase` accept `worker_b_model:
  Optional[str]`.
- `start` builds only `worker_a` + `moderator` seat histories, adding
  `worker_b` only when configured.
- The persisted `models` dict for a Solo run is `{"worker_a", "moderator":
  None}` — the `worker_b` key is absent. The existing Compare shape
  (`{"worker_a", "worker_b", "moderator": None}`) is unchanged.
- `_run_phase` forwards only the active worker seat histories downstream and
  guards the moderator phase so it runs only when **both** `moderator_model`
  and `worker_b_model` are present (defensive no-hybrid).

### `backend/modelmix/orchestrator.py`

- `multiplex_workers` accepts `worker_b_model: Optional[str]`.
- Active seats computed locally: `models` starts as `{"worker_a"}` and gains
  `worker_b` only when configured, so the task loop, `run_started.seats`, the
  completion loop, and the `failed_seats`/`len(tasks)` terminal-status logic all
  behave correctly for a single seat.
- The now-unused `SEATS` module constant was removed.

### `backend/modelmix/persistence.py`

`_validate` statically relaxes the model-references guard:

| Check | Before | After |
|---|---|---|
| Key set | exact `{worker_a, worker_b, moderator}` | subset of `{worker_a, worker_b, moderator}` |
| `worker_a` | implied non-empty string | explicit: must be present non-empty |
| Any present non-moderator key | must be non-empty string | must be non-empty string (unchanged) |
| `moderator` | non-empty string or `None` | non-empty string or `None` (unchanged) |

Result: Mix, Compare, Solo, and old three-key shapes all validate; genuinely
malformed shapes (missing/empty `worker_a`, `worker_b: None`, unknown keys like
`worker_c`, empty/non-string `moderator`) are still rejected.

### `backend/modelmix/history.py`

**Not modified.** A Solo turn produces no worker_b message, so a later Mix
turn's `build_seat_history("worker_b")` already skips the Solo turn (its
`own_message is None: continue` branch). Verified by a test, not patched.

## Tests

- `backend/tests/test_modelmix_solo_mode.py` (new, 7 tests): solo streams Worker
  A only (`run_started.seats == ["worker_a"]`, zero worker_b/moderator events,
  `run_completed "completed"`); solo failure reaches `run_completed "failed"`;
  requests with no `worker_b` default to Solo; the hybrid is 422-rejected with
  the provider resolver never called; solo-then-mix multi-turn isolation holds
  (worker_b sees a blank history, never Worker A's Solo output); per-worker
  guardrails apply to the Solo worker; cancellation reaches `run_cancelled`
  mid-stream.
- `backend/tests/test_modelmix_persistence.py` (new validator tests): Mix /
  Compare / Solo shapes accepted; missing/empty `worker_a`, `worker_b: None`,
  unknown keys, and empty/non-string `moderator` rejected; Solo shape survives
  load-from-disk; Mix/Compare/Solo all load.

## Validation observed

- New solo suite: **7 passed**.
- Targeted persistence/streaming/moderator/compare/acceptance/solo files:
  **63 passed**.
- Full `uv run pytest backend/tests -q`: **460 passed** (up from 448).
- `uv run ruff check backend/modelmix backend/tests`: **All checks passed**.
  The repo-wide `ruff format --check` state is pre-existing and left untouched
  per the no-reformat-unrelated-code rule.
- Frontend (`cd frontend && npm test && npm run build && npm run lint`): **130
  passed**, build green, lint clean.

## Assumptions

- `worker_b_model` is typed `Optional[str]` and threaded as a positional-None
  (the route passes `None` for Solo) rather than given a `= None` keyword
  default, because a default before the required `provider_resolver` position
  would force a broad signature reorder across many existing call sites.
  Functionally equivalent for the route-driven Solo path.
- Real Solo runs persist `models` as `{"worker_a", "moderator": None}` (worker_b
  key absent). This is valid under the new rules; the pure `{"worker_a"}` shape
  is also accepted by the validator.

## Remaining / risks

- Frontend Solo mode is not implemented (item 27 remains partially open).
- The defensive no-hybrid guard in `_run_phase` makes any direct registry call
  with `moderator_model` but no `worker_b_model` skip the moderator phase; the
  route already prevents that input, so this is unreachable through the HTTP
  surface.
