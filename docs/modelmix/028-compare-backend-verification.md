# Mission 028 — Verify and Harden the Existing Compare (No-Moderator) Backend Path

Route: Big Pickle (OpenCode Zen)
Punch Board item: 28 (Compare — backend verification half)
Date: 2026-08-31 CT
Base: `main @ a4bf06a` (Mission 027)

## Purpose

Mission 022's job, narrower, for the existing Compare (no-moderator) path.
Before writing any new orchestration code, determine — with real evidence —
whether the already-shipped, completely-unexercised two-worker-without-moderator
capability actually works end to end. The route (`POST /api/modelmix/runs/stream`
with `moderator_model` omitted), `registry.py::_run_phase`, and
`orchestrator.py::multiplex_workers` already support this path; it simply had
zero test coverage anywhere in the codebase (confirmed by grep: nothing
referenced `moderator_model=None` or `emit_run_completed` in any test file).

The start-of-mission rule was honored exactly as Mission 022's was: if a real
defect had been found, it would be reported precisely instead of silently
patched to make a test pass. **No real defect was found.** The path is correct
end to end.

## What was tested and the evidence

All scenarios driven through the REAL HTTP surface (`POST
/api/modelmix/runs/stream` with `moderator_model` omitted), using the exact
harness already established in `test_modelmix_alpha_acceptance.py` (bare
`FastAPI()` + `include_router(router)`, `run_registry` /
`get_provider_for_model` monkeypatched to deterministic fakes, isolated
`tmp_path` persistence, SSE parsed by stripping the `data: ` prefix). New file:
`backend/tests/test_modelmix_compare_mode_backend.py` (7 tests).

For each of the seven numbered investigation points — confirmed working (with
evidence), confirmed broken (with evidence and severity), or unable to
determine:

1. **Normal no-moderator run — CONFIRMED WORKING.** Both workers stream their
   full output (`seat_deltas` for worker_a and worker_b), `seat_completed`
   appears exactly twice, and the run reaches `run_completed` with
   `status="completed"`. The journal contains **zero** moderator-related events
   of any kind — `moderator_started`, `moderator_delta`, `moderator_completed`,
   `moderator_failed` (and `moderator_output_warning`) asserted absent, not just
   "the run finished". Sequence numbers are contiguous
   `1..N`. (test 1)

2. **One worker fails, moderator omitted — CONFIRMED WORKING.** Run reaches
   `run_completed` with `status="partial"`. Reading the persisted session back
   through `GET /sessions/{id}` (as Mission 022's reopen-session scenario did)
   shows worker_a message `status="failed"` with `error="worker A exploded"`
   and worker_b `status="completed"` with the surviving output. No moderator
   message exists for that run. (test 2)

3. **Both workers fail, moderator omitted — OBSERVED (asserted as real
   behavior), CONFIRMED WORKING as-shipped but noteworthy.** Observed actual
   behavior: both seats emit `seat_failed`, then the run still reaches
   `run_completed` with `status="partial"` — it does **not** emit `run_failed`
   and does not become `failed`. This is a deliberate consequence of
   `multiplex_workers` emitting `run_completed` with `"partial" if failed else
   "completed"` whenever `emit_run_completed=True`, where `failed` is true if
   EITHER seat failed. Note this differs from the moderator path, where both
   workers failing yields `run_failed` / `status="failed"`. For a compare
   (no-moderator) run this is coherent with the semantic that "partial" means
   "some witnesses produced output"; here neither did, so "partial" arguably
   understates it. Reported as a product-semantics observation, NOT a defect:
   it is the shipped, deterministic behavior, and changing it is product work
   (out of scope by the mission's hard boundaries). (test 3)

4. **Multi-turn isolation in a moderator-less session — CONFIRMED WORKING.**
   Over two turns in one session, each worker's seat history contains only that
   seat's own prior turns (exact list equality against the 
   `prompt1 / answer1 / prompt2` shape) and never the other worker's or the
   moderator's content. The dead `seat_histories["moderator"]` data — registry
   always builds the `"moderator"` key even when no moderator ever runs — does
   **not** leak anywhere: `_run_phase` forwards only `worker_a`/`worker_b`
   histories into `multiplex_workers`, so a moderator-poison sentinel never
   reaches either provider's message payload. (test 4)

5. **Per-worker guardrails in a moderator-less run — CONFIRMED WORKING.**
   With per-request `warning_threshold_chars=100`, `hard_cap_chars=200` and two
   250-char single-delta fakes: each worker emits exactly one
   `seat_output_warning` (threshold 100) and is capped, both produce
   `finish_reason="modelmix_output_cap"`, both final streams are exactly 200
   chars, and the run still reaches `run_completed`/`completed`. (test 5)

6. **Cancellation of a moderator-less run mid-stream — CONFIRMED WORKING.**
   Using the same two-in-flight-request async pattern as Mission 022's cancel
   scenario, once output is visible, `POST /runs/{id}/cancel` drives terminal
   `run.status == "cancelled"`, the stream ends in `run_cancelled`, no
   `run_completed`/`run_failed`, no post-cancel deltas, and both fake providers
   observed `CancelledError` (`cancelled=True`). (test 6)

7. **Reopening a moderator-less session — CONFIRMED WORKING.** `GET
   /sessions/{id}` reconstructs the conversation with NO moderator message at
   all: the run's assistant messages are exactly `{worker_a, worker_b}`, no
   `seat == "moderator"` message exists, and the stored run's `models` dict
   carries `"moderator": None` (validated fine by persistence, which requires
   the key but tolerates `None`). `snapshot["status"]=="completed"`,
   `latest_seq == len(events)`, all events carry the right `run_id`, and no
   moderator event is present in the stored journal. Nothing downstream
   (persistence `_validate`, `_apply_event`, or history rebuild) assumes a
   moderator message always exists and chokes on its absence. (test 7)

## Defects found

**None.** No production code was changed by this mission. The only two test
failures encountered during development were bugs in my own test assertions
(mis-reading `seat_deltas` cardinality and asserting that a turn's own output
appears in its own input history), fixed in the test file — not backend defects.

## Small fixes applied

None. Per the mission's boundaries, nothing in `routes.py`, `registry.py`, or
`orchestrator.py` was modified; no request/event schema concept (`mode` or
otherwise) was added; no frontend change was made.

## Effort / scope notes

- The `seat_histories["moderator"]` dead key (point 4) and the 
  `models["moderator"]: None` key (point 7) are inert structural leftovers from
  shared persistence/history code. Neither leaks to workers and neither breaks
  reopening. Left as-is; cleaning them up would touch shared contract code
  beyond this verify mission's scope.

## Acceptance criteria

All 7 numbered investigation points each produced at least one test with a
clear, evidence-based assertion (7 tests, one per point, all through the real
route). No assertion is a guess about what "should" happen; point 3 explicitly
asserts the observed-as-shipped behavior.

## Validation observed (raw)

- `uv run pytest backend/tests/test_modelmix_alpha_acceptance.py -v` →
  **7 passed in 1.81s** (unchanged; moderator-full path undisturbed).
- `uv run pytest backend/tests/test_modelmix_compare_mode_backend.py -v` →
  **7 passed in 1.61s** (new).
- `uv run pytest backend/tests -q` → **448 passed in 28.58s** (441 prior + 7
  net new).
- `uv run ruff check backend` → **All checks passed!**
- Frontend (`cd frontend && npm test && npm run build && npm run lint`):
  **118 passed**, build **green (1.61s)**, lint **clean**.

## git status --short / git diff --stat

Recorded at commit time (see final report for the raw outputs).

## Files changed

- `backend/tests/test_modelmix_compare_mode_backend.py` (new, 7 tests).
- `docs/modelmix/028-compare-backend-verification.md` (this report).
- `docs/modelmix/PUNCH-BOARD.md`, `MISSION-INDEX.md`, `ENGINEERING-PROGRESS.md`
  (bookkeeping).

## Bottom line

The existing no-moderator two-worker backend path is real, load-bearing Compare
readiness: it works end to end through the real HTTP route, with correct
streaming, honest terminal status (`completed`/`partial`), per-worker
guardrails, cancellation, multi-turn isolation, and moderator-absence-tolerant
reopen/persistence. This is now backed by real tests instead of an unverified
assumption, and it becomes a solid ground for the next (frontend) Compare
mission. The one product-semantics observation worth carrying forward is point
3 (both workers failing yields `run_completed "partial"` rather than `failed`);
that is deterministic shipped behavior and any change to it is product work for
a later mission.
