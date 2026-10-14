# Mission 002 Result

**PASS** — the repository's available functional suite and the focused ModelMix suite pass.

The supplied checkout had no Git remote configured, no `origin/modelmix-foundation` ref, and no
`1ee5d90` object. The mission branch was therefore created from the supplied `work` HEAD
(`6454171`) rather than pretending the requested fetch/cherry-pick succeeded. This environment
contained 292 inherited backend tests rather than the 438 reported for Mission 001.

## Files Changed

- `backend/providers/base.py` — optional normalized provider stream contract.
- `backend/providers/openai_oauth.py` — incremental ChatGPT OAuth output-text streaming.
- `backend/modelmix/` — event sequencing, two-worker orchestration, and experimental route.
- `backend/main.py` — ModelMix router registration only.
- `backend/tests/test_modelmix_streaming.py` — deterministic vertical-slice tests.
- `docs/modelmix/002-first-streaming-slice.md` — this report.

## Provider Streaming Contract

`ProviderStreamEvent` normalizes `text_delta`, `completed`, and `error` events, with optional
completed result, finish reason, usage, and error message. `LLMProvider.supports_streaming`
defaults to false and `stream_query()` is non-abstract, so all existing adapters remain valid and
their unchanged `query()` implementations remain the fallback.

## ChatGPT OAuth Streaming

`OpenAIOauthProvider.stream_query()` uses the existing credential lookup, token refresh, request
headers, Codex Responses endpoint, and upstream SSE request. It yields only
`response.output_text.delta` and `response.text.delta`; reasoning and unknown event types are
ignored. Completion carries usage/status, while HTTP and upstream stream failures become
normalized provider errors. The inherited `query()` path now consumes this normalized stream and
assembles the same visible final response dictionary expected by Council callers.

## ModelMix Event Schema v0

Every event has `run_id`, a centrally assigned positive monotonic `seq`, and `type`. Seat events
also have `seat_id`, fixed to `worker_a` or `worker_b`.

- `run_started`: declares both stable seats.
- `seat_started`: identifies the seat and selected model.
- `seat_delta`: carries one visible `delta` tagged to its seat.
- `seat_completed`: terminal success, optionally carrying usage and finish reason.
- `seat_failed`: terminal isolated failure with an error message.
- `seat_cancelled`: terminal local cancellation.
- `run_cancel_requested`: records detected client disconnect before local task cancellation.
- `run_completed`: emitted only after both seats terminate; status is `completed` or `partial`.

## Two-Worker Orchestration

`POST /api/modelmix/runs/stream` accepts one prompt plus the two model IDs. The orchestrator builds
a fresh one-message list separately for each seat and creates both tasks before consuming their
shared internal queue. Providers receive no seat identity, peer output, team framing, ranking
instruction, or synchronization dependency. One consumer assigns sequence numbers as queued
events enter the single SSE response, preventing duplicate sequences.

## Fallback Behavior

When `supports_streaming` is false, the worker calls the existing `query()` method. Successful
visible content becomes one `seat_delta`, followed by `seat_completed`; provider errors become
`seat_failed`. No other adapter was converted.

## Cancellation / Failure Behavior

The route injects the raw FastAPI `Request` and checks `request.is_disconnected()`. A disconnect
emits `run_cancel_requested` where delivery remains possible, cancels both local tasks, records
their local terminal cancellation, and never emits successful `run_completed`. Cancellation of
the HTTP task closes ChatGPT OAuth's `httpx` stream context, but this slice does not claim that an
upstream provider has stopped billing. A normal failure in either seat is caught within that seat;
the peer continues and the run terminates as `partial` after both seats are terminal.

## Test Evidence

- `uv run pytest -q backend/tests/test_modelmix_streaming.py backend/tests/test_provider_openai_oauth.py`
  — 11 passed (focused plus adjacent provider compatibility tests).
- `uv run pytest -q backend/tests` — 300 passed (all 292 inherited tests available in this
  checkout plus 8 new ModelMix tests).
- `npm run build` (from `frontend/`) — passed, 427 modules transformed. npm reported only its
  pre-existing `http-proxy` configuration deprecation warning.
- `git diff --check` — passed.
- `uv run ruff check backend/providers/base.py backend/providers/openai_oauth.py backend/modelmix
  backend/tests/test_modelmix_streaming.py` — passed for all touched Python files.

The focused tests deterministically prove concurrent start, identical isolated prompts, routing,
seat-tagged interleaving, unique monotonic sequence, stable run ID, independent failure, two-seat
termination, request/response fallback, cancellation semantics, route SSE behavior, absence of a
ranking call, and ChatGPT OAuth visible stream assembly that excludes a simulated reasoning delta.

## Known Limitations

- Events and cancellation state are not persisted or replayable.
- Runs remain tied to one backend process and one live HTTP connection.
- Only ChatGPT OAuth provides native deltas; all other adapters use one-delta fallback.
- Disconnect cancellation is best effort and cannot certify upstream billing termination.
- The endpoint is experimental and has no product UI or persistent seat settings.
- The supplied checkout lacked the requested origin/base ref and Mission 001 commit, as recorded
  at the top of this report.

## Recommended Mission 003

Add a bounded process-local ModelMix event journal with `run_id` reconnect/replay semantics while
retaining the single-backend-worker alpha constraint.
