# Mission 052 — Spend Confirmation Gate (Backend)

Date: 2026-09-03 CT · Base: main @ `0fab512` (Mission 054 test follow-up) ·
Mission 052 was retroactively renumbered after being skipped.

## What changed

Backend only. Adds the first real dollar-cap enforcement for ModelMix: a
per-request spend limit on `POST /api/modelmix/runs/stream`. If the LAST run in a
session had any seat/moderator whose **real, already-persisted** `cost_usd`
exceeded the user-configured limit, the NEXT run in that same session is blocked
with HTTP 402 (naming the seat and actual cost) until the request sends
`confirm_over_budget: true`.

This enforces on a known past fact — never a guess and never an estimate.

### `backend/modelmix/routes.py`

- `TwoWorkerRequest` gains `spend_limit_usd: Optional[float] = Field(default=None, gt=0)`
  and `confirm_over_budget: bool = False`.
- `stream_two_workers` runs the gate **before** `run_registry.start()`, so a
  rejected run never touches a provider.
- New helper `_over_budget_rejection(session_id, spend_limit_usd)`:
  - Loads the session via the existing `run_registry.persistence.load_session`.
  - Missing session or `None` document → proceeds.
  - Reads only the MOST RECENT run (`runs[-1]`; runs are chronological).
  - Iterates that run's messages; compares each seat's real `cost_usd`.
  - **Per-seat only — never aggregates seats.**
  - `cost_usd is None` (non-OpenRouter or uncached) is never over-budget.
  - Returns the first offending seat + real cost, else `None`.

Gate condition: runs only when `spend_limit_usd is not None` AND
`session_id is not None` AND `confirm_over_budget is False`.

## Boundaries honored

- `confirm_over_budget: true` skips the check entirely and proceeds.
- Omitted `spend_limit_usd` → byte-for-byte unchanged behavior.
- No change to `should_warn_cost` / `WARNING_COST_USD_THRESHOLD` or any Mission
  050 warning-emission behavior.
- No server-side persistence of `spend_limit_usd`.
- No change to `compute_openrouter_cost_usd`.
- No new dependency; no `schema_version` bump.
- ModelMix-only path (`TwoWorkerRequest` / `modelmix/*`). No Council/Advisor.
- Not persisted to session; the limit lives only in the request.

## Tests — `backend/tests/test_modelmix_spend_gate.py` (9 new)

Covers all 7 acceptance criteria plus a no-session_id regression:

1. Single seat over limit → HTTP 402, first offending seat + real cost named,
   and the provider resolver is never invoked (loud `BlowUpProvider`).
2. Over budget + `confirm_over_budget: true` → proceeds normally.
3. All seats under limit → proceeds without confirmation.
4. All costs `None` → proceeds even with an extreme limit.
5. Session with no prior runs → proceeds even with a limit.
6. No `session_id` → proceeds even with a limit.
7. `confirm_over_budget: true` bypasses even when multiple seats are over.
8. Per-seat (not aggregate) named seat: worker_a 0.30 / worker_b 0.08 against
   limit 0.10 → 402 names only worker_a.
9. Omitted `spend_limit_usd` regression → unchanged behavior.

Tests drive the real HTTP surface (`FastAPI` + `include_router(router)`), seeding
a completed prior run on disk with its own persistence instance, and assert
provider usage / rejection status.

## Validation (observed)

- `uv run pytest backend/tests/test_modelmix_spend_gate.py -v` → **9 passed**.
- Targeted suite
  (`test_modelmix_cost_backend.py`, `test_modelmix_streaming.py`,
  `test_modelmix_alpha_acceptance.py`, `test_modelmix_spend_gate.py`) → **44 passed**.
- Full backend `uv run pytest backend/tests -q` → **544 passed** (535 + 9).
- Frontend (unchanged by this backend-only mission): `npm test` → **181 passed**;
  `npm run build` → built clean; `npm run lint` → clean.
- Backend runs used `--basetemp=...` (established workaround for the known
  pre-existing `pytest-of-wpedigo` ACL `WinError 5`).

## Doc updates

- `PUNCH-BOARD.md` item 17 — added Mission 052 (first real enforcement).
- `MISSION-INDEX.md` — added missing Mission 052 table row + Result section.
- `ENGINEERING-PROGRESS.md` — added Mission 052 Result.

## Remaining risks / open items

- The gate reads the most recent run in the session; it is not a cumulative
  across-run budget and does not cap a single run while it streams. A hard
  mid-stream cutoff remains separate, undecided future work.
- `spend_limit_usd` is a per-request value only (not persisted server-side), so
  the frontend/operator must send it every run to keep the gate active.
- Cost is real only for `openrouter:`-prefixed, priced, cached providers; that
  honesty model is unchanged — a non-OpenRouter seat reports `None` and can
  never trip this gate.
