# Mission 003 Result

**PASS** — ModelMix runs now have bounded process-local journals, replay/tailing, and explicit
cancellation independent of SSE subscriber lifetime.

## Branch / Commit

- Branch: `codex/modelmix-mission-003`
- Commit: `feat: add ModelMix event journal and replay` (the commit containing this report)
- Base available in this checkout: `d9895a060fc61ad2f6f042278d6b52c05a951e1e`, whose tree is
  the Mission 002 implementation. The requested SHA
  `05a92b232981283d8a89c06f4721c6ec21fc85b6` and Mission 001 report object were not present in
  this supplied Git object database, and no remote was configured.

## Event Journal Design

`RunEventJournal` is the authoritative record for one ModelMix run. Its async condition protects
canonical sequence allocation, append, replay snapshots, state changes, and subscriber wakeups.
`append()` creates the actual event dictionary with the run ID and next sequence; the orchestrator
publishes that same journal-created object. It is therefore the sole sequence source for registered
runs. `RunRegistry` owns each background run task and journal without using Council `_active_runs`.

Lifecycle state begins as `created`, changes to `active` when the task starts, and terminates as
`completed`, `partial`, `failed`, or `cancelled`. A worker failure remains isolated and produces the
existing partial completion after the other worker reaches a terminal state.

## Retention Policy

The process-local defaults are:

- 1,000 events per run;
- 100 retained terminal runs;
- 15 minutes after terminal state.

Per-run overflow deterministically removes the lowest-sequence event without renumbering retained
events. A cursor older than retained history receives HTTP 409 with the first missing sequence
range. Registry pruning first expires terminal runs by TTL, then removes the oldest terminal runs
until the count bound is met. Active runs are never retention-evicted. An expired or count-evicted
run returns HTTP 404 with `ModelMix run not found or expired`.

## Replay API

`GET /api/modelmix/runs/{run_id}/events?after_seq=N` sends retained events whose original
`seq > N`. For active runs it then waits on the journal condition and tails new events; for terminal
runs it closes after replay. Each SSE item includes `id: <seq>` and the unchanged ModelMix event as
JSON. `Last-Event-ID` is supported when `after_seq` is absent; an explicit query cursor takes
precedence.

The existing `POST /api/modelmix/runs/stream` now creates a registry-owned background run and
subscribes from sequence zero. Its `X-ModelMix-Run-ID` response header and first `run_started`
event expose the reconnect key.

## Subscriber Disconnect vs Run Cancellation

Closing any journal tail/SSE subscriber only closes that subscriber generator. It does not cancel
the registry-owned run task or either worker. Another subscriber can reconnect using the run ID and
last observed sequence, replay missed retained events, and continue tailing the same run.

## Cancellation Semantics

`POST /api/modelmix/runs/{run_id}/cancel` is separate and idempotent. The first active cancellation
appends `run_cancel_requested`, flags the journal, and cancels the local run task. Cleanup cancels
local worker tasks, then the registry appends terminal `run_cancelled` and records `cancelled`.
Repeated cancellation returns the same stable run state without appending duplicate request/final
events. A cancelled run never emits `run_completed`, and its cancellation events remain replayable
within retention. This is local best-effort cancellation and makes no claim about upstream billing.

## Test Count Reconciliation

The Mission 001 report file requested by the mission was absent from this supplied checkout, so its
literal command could not be read from that artifact. The discrepancy is nevertheless exactly
reconciled by test collection:

- `uv run pytest --collect-only -q backend/tests` collected 300 tests at the Mission 002 tree.
- `uv run pytest --collect-only -q` collected 446 tests at the Mission 002 tree.
- Mission 002 added 8 backend tests, so the repository-wide pre-Mission-002 count was
  `446 - 8 = 438`.
- The 146-test Mission 002 difference (`446 - 300`) is exactly
  `the_ai_counsel_mcp/tests`. It was omitted by the narrower Mission 002 command, not failing or
  deleted.
- Mission 003 adds 9 tests, producing 309 backend tests and 455 repository-wide tests.

The broader correct regression command is therefore `uv run pytest -q`, and it was used for the
Mission 003 pass decision.

## Test Evidence

- `uv run pytest -q` — 455 passed in 15.56 seconds.
- `uv run pytest -q backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_streaming.py`
  — 17 passed.
- `uv run pytest -q backend/tests/test_modelmix_streaming.py
  backend/tests/test_provider_openai_oauth.py` — 11 passed (Mission 002 focused regression).
- `uv run ruff check backend/modelmix backend/tests/test_modelmix_journal.py
  backend/tests/test_modelmix_streaming.py` — passed.
- `git diff --check` — passed.

Tests cover canonical concurrent sequencing, cursor filtering and object preservation, active replay
then tail, terminal replay then close, subscriber independence, idempotent explicit cancellation,
replayable cancellation, absence of successful completion after cancellation, per-run/count/TTL
bounds, clear replay-gap and expired semantics, both-seat isolation, and Mission 002 behavior.

## Known Limitations

- Journals, lifecycle, and cancellation are process-local and disappear on restart.
- Multiple backend workers do not share runs; alpha must remain single-process/single-worker.
- Terminal-run lookup does not distinguish expiry from an unknown run beyond the clear combined
  `not found or expired` response.
- A subscriber that falls behind while already tailing can have its connection close on a retention
  gap; reconnecting at that cursor returns the explicit HTTP 409 detail.
- Cancellation closes local HTTP streams where supported but cannot certify upstream billing has
  stopped.

## Recommended Mission 004

Add a minimal experimental frontend ModelMix observer that starts a two-worker run, renders both
seat streams independently, and reconnects with `run_id` plus the last received sequence, without
adding a Moderator or peer interaction.
