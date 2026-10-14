# Mission 022 — Alpha Acceptance Integration Test (Backend)

Route: Big Pickle (OpenCode Zen)
Punch Board items: 33 (advance — backend-provable alpha acceptance checklist items as integration tests through the real HTTP surface)
Base: `main` @ `129a127` "feat(modelmix): guardrails settings and visibility (Mission 021)"
Date: 2026-08-30
Result: **PASS (LOCAL)**

## Objective

Deliver the backend-provable half of Punch Board item 33 as one new integration
test file, `backend/tests/test_modelmix_alpha_acceptance.py`, which exercises
the real HTTP routes end-to-end: stream both workers, stream the Moderator,
cancel a run, survive a worker failure, reopen a session, verify multi-turn
isolation, and assert honest telemetry and no credential leak.

Verify-only mission: **no production file, no existing test file, and no
dependency may be touched.** The diff is exactly one new test file plus this
report and the board-doc updates. If a real gap was found during verification,
it is reported honestly here and not patched (see the cancel-path disclosure).

UI-bound checklist items (Launch, three panels, configure A/B/Moderator)
cannot be proven from the backend surface and are covered by prior missions'
evidence, noted in the disposition.

## 11-Item Disposition

| # | Checklist item | Disposition | Evidence |
|---|---|---|---|
| 1 | Launch | PASS (prior) | Frontend/UI — proven by Mission 014 (`GET /modelmix` serves the built cockpit). Not re-provable from the backend surface. |
| 2 | Three panels | PASS (prior) | Frontend/UI — proven by Mission 016 (Worker A / wider Moderator / Worker B cockpit). Not re-provable from the backend surface. |
| 3 | Configure A/B/Moderator | PASS (prior) | Frontend/UI + backend discovery — proven by Missions 007/016. Not re-provable from the backend surface. |
| 4 | Stream both workers | **PROVEN (Mission 022)** | `test_scenario_1_full_run_streams_both_workers_then_moderator` |
| 5 | Stream Moderator | **PROVEN (Mission 022)** | `test_scenario_1...` (seat/Moderator events in order on the single run feed) |
| 6 | Cancel | **PROVEN, with disclosed race** | `test_scenario_2_cancel_route_stops_stream_without_post_cancel_deltas` — see Cancel-Path disclosure |
| 7 | Survive worker failure | **PROVEN (Mission 022)** | `test_scenario_3_worker_failure_survives_with_partial_moderation` |
| 8 | Reopen session | **PROVEN (Mission 022)** | `test_scenario_4_reopen_session_reconstructs_full_conversation` |
| 9 | Multi-turn isolation | **PROVEN (Mission 022)** | `test_scenario_5_multi_turn_isolation_via_real_route` |
| 10 | Honest telemetry | **PROVEN (Mission 022)** | `test_scenario_6_reopened_session_carries_honest_telemetry` |
| 11 | No credential leak | **PROVEN (Mission 022)** | `test_scenario_7_fake_credential_never_leaks_into_stream_or_persistence` |

## Deliverables

One new file: `backend/tests/test_modelmix_alpha_acceptance.py` — 7 tests, 395
backend total (388 prior + 7 new).

- Reuses the repo's canonical sync `FastAPI TestClient` route pattern from
  `test_modelmix_streaming.py` for every test that needs only one control flow.
- The **cancel scenario is the sole deviation**: two requests must be in flight
  (the streaming POST holds the socket open until the run is terminal, so a
  sync TestClient cannot cancel mid-run). It uses the existing single-loop
  `httpx.AsyncClient(ASGITransport(app))` pattern from
  `test_modelmix_journal.py`, on one asyncio loop, rather than two loop portals
  sharing asyncio locks. Everything else is the exact sync TestClient pattern.
- Deterministic provider fakes (fixed deltas, hang-after-deltas, gate synced
  to a second event-loop thread for reopen/multi-turn) inject usage/finish
  reasons through the same `get_provider_for_model` seam the real routes use.
- Scenario 2 asserts the real, observed cancel contract: exactly one
  `run_cancel_requested` (seq after every `seat_delta`), terminal
  `run_cancelled`, no `run_completed`/`run_failed`, no deltas after the cancel
  marker, the persisted `/sessions/latest` run entry ends `cancelled`, and both
  provider sessions actually received cancellation.

## Cancel-Path Disclosure (real gap found — not patched)

During the cancel investigation, a real robustness race in the production
cancellation path was reproduced deterministically through the real HTTP
surface (`POST /runs/stream` + `POST /runs/{id}/cancel`):

- **Trigger:** issuing the cancel inside the sub-millisecond window right after
  the first seat delta — a client that polls the journal on an
  `asyncio.sleep(0)` tight loop does exactly this. Reproduced 5/5 with that
  timing in this harness.
- **Mechanism observed in a task dump:** `_run_phase` was found blocked in
  `multiplex_workers`' generator `finally` `await asyncio.gather(...)` while
  the model-a seat task sat un-cancelled awaiting the provider stream inside
  `aiter_with_deadline` (`asyncio.wait_for` over the provider's `__anext__`);
  that provider generator never received its `CancelledError`. Model-b's seat
  cancelled normally, making the hung path seat/emission-window dependent.
- **Outcome:** the run stays `active` with no terminal event until the 600s
  run timeout force-marks it failed. The frontend would see a run that never
  stops.
- **Current real-world posture:** with a natural client rhythm (cancel issued
  ~10ms+ after output is visible) the cancel completes cleanly and the 
  submission's scenario-2 shape passed 10/10 consecutive runs. The existing
  sync TestClient cancel test (`test_modelmix_journal.py`) passes. The race
  window is tight, but it is a genuine reachable state, not a harness artifact
  of this single test.
- **Why not patched:** the mission is verify-only; AGENTS.md requires gaps to
  be reported, not silently fixed. Recommended follow-up: make cancellation
  propagate first through the `aiter_with_deadline` enclosing `asyncio.wait_for`
  (e.g. shielding/timeout-aware `aclose()` of the provider stream, or
  transferring cancellation into the seat task promptly) so the generator
  `finally` gather cannot wait forever on a seat that never observes cancel.

## Test Evidence

All seven scenarios run through the real routes → registry → run-phase chain:

1. Full run: both workers then Moderator, ordered single-`run_id` SSE with
   `run_started → seat_started×2 → seat_delta → seat_completed×2 →
   moderator_started/delta/completed → run_completed`, seqs contiguous, both
   session/run headers present, entire 7-run history persisted.
2. Cancel: 200 cancel, `run_cancel_requested` once, terminal `run_cancelled`,
   no post-cancel deltas, persisted status `cancelled`, both providers marked
   cancelled (see disclosure for the race boundary).
3. Worker failure: failed seat persists its partial deltas, survives in the
   reopened transcript, does **not** enter the Moderator handoff; Moderator
   receives the honest `Worker A status: Unavailable because the worker failed.`
   line and moderates with B only; run ends `partial`, moderator events and
   handoff never mention the other worker.
4. Reopen: fresh registry + same persisted dir; `/sessions/latest` → latest run;
   full 7-message transcript rehydrated per seat with exact names/prompts/
   text/roles and no cross-seat leakage.
5. Multi-turn isolation: a second streaming POST on the same client picks up
   the same session; each seat history is `[P1, own-1, P2]`, the Moderator
   history is `[P1, M1]` then turn-2 handoff; no seat ever sees the other
   worker's turn-1 output.
6. Honest telemetry: reopens persisted messages and asserts exact provider
   `usage` dicts, `finish_reason`, and real float `started_at`/`completed_at`
   (completed ≥ started) on all three seat messages; nothing fabricated.
7. Credential leak: a fake provider pre-sends the fake key as its first delta
   and persists it; the SSE stream, the persisted journal, and the persisted
   session document all byte-check that the secret never appears.

## Validation

Raw output, run from the repo root:

### New file (backend)

```text
uv run pytest backend/tests/test_modelmix_alpha_acceptance.py -v
  ...::test_scenario_1_full_run_streams_both_workers_then_moderator PASSED
  ...::test_scenario_2_cancel_route_stops_stream_without_post_cancel_deltas PASSED
  ...::test_scenario_3_worker_failure_survives_with_partial_moderation PASSED
  ...::test_scenario_4_reopen_session_reconstructs_full_conversation PASSED
  ...::test_scenario_5_multi_turn_isolation_via_real_route PASSED
  ...::test_scenario_6_reopened_session_carries_honest_telemetry PASSED
  ...::test_scenario_7_fake_credential_never_leaks_into_stream_or_persistence PASSED
7 passed in 1.80s

# cancel scenario stability probe (natural-rhythm body):
uv run pytest backend/tests/test_modelmix_alpha_acceptance.py::test_scenario_2... -q   # 10/10 passed, ~0.76s each
```

### Full backend suite

```text
uv run pytest backend/tests -q
........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 54%]
........................................................................ [ 72%]
........................................................................ [ 91%]
...................................                                      [100%]
395 passed in 16.64s   (388 prior + 7 new; no existing test modified)
```

### Frontend (unchanged baseline, re-asserted; `npm.cmd` because PS blocks `npm.ps1`)

```text
npm test      Test Files 12 passed (12)   Tests 118 passed (118)
npm run build (vite v7.3.6, 438 modules transformed, built in 2.87s)
npm run lint  (eslint . — clean)
```

### Diff scope

```text
git status --short   →  ?? backend/tests/test_modelmix_alpha_acceptance.py
                       (untracked before commit; report + docs follow)
git diff --stat      →  (no tracked file changed prior to commit)
```

## Remaining Risks / Open

- **Cancel-path race (disclosed above)** — the one real gap found. Not patched
  (verify-only); flag for a follow-up fix in `_run_phase` /
  `aiter_with_deadline` cancellation hand-off.
- **Cancellation is proven to be instantly-clean only in clean scheduling; for
  a human-paced client it works, but the sub-ms cancel window can hang a run
  until the 600s run timeout.** Honest caveat on the item 33 "cancel" claim.
- UI items (Launch / three panels / configure) remain proven only by prior
  mission evidence + the built-app reachability test; a live-provider manual
  launch pass is still the final alpha step.

## Acceptance Criteria → Where Covered

1. One new backend test file, no production/legacy-test/dependency changes — diff scope above.
2. Full run streams both workers then the Moderator over one feed — scenario 1.
3. Cancel route stops the stream with no post-cancel deltas — scenario 2.
4. Worker failure survives and is honestly represented (partial, handoff exclusion) — scenario 3.
5. Session reopen reconstructs the full conversation from persisted state — scenario 4.
6. Multi-turn isolation preserved across a real second POST — scenario 5.
7. Telemetry is provably provider-faithful (exact usage/finish/timestamps) — scenario 6.
8. Credentials never appear in stream, journal, or persisted session — scenario 7.
9. 11-item disposition documented with prior-mission evidence where applicable — this report.
10. Cancel-path race discovered during verification is disclosed, not hidden — this report.