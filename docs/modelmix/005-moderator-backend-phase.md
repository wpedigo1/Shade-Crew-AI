# Mission 005 Result

**PASS** — an explicitly selected Moderator now fans in bounded visible worker output only after
both witnesses terminate, then streams through the existing canonical ModelMix journal.

## Branch / Commit

- Branch: `codex/modelmix-mission-005`
- Commit: `feat: add ModelMix moderator phase` (the commit containing this report)
- Base: Mission 004 commit `0179aaf95f626fbe02537e0689bf677a48fa76e2`.

## Moderator Start Policy

The run request accepts an optional `moderator_model` provider/model identifier and resolves it
through the existing provider registry. No provider is substituted. Omitting it preserves the
existing two-worker observer route semantics; providing it opts into a full moderated Mix.

Both worker tasks are created together and remain independent. The worker async generator must
observe a terminal event for both seats before registry control reaches Moderator eligibility.
Both successful outputs permit moderation. One successful output plus one failure permits degraded
moderation. Two failures, including successful calls that produce no visible text, emit
`moderator_failed` with `reason: insufficient_input`, then `run_failed`; the Moderator provider is
never called.

## Moderator Input Contract

`assemble_moderator_input()` is the single ModelMix-owned handoff builder. It creates:

- a fixed system instruction to evaluate, reconcile, resolve discrepancies, and answer without
  ranking, voting, debating, mechanical concatenation, or hidden reasoning;
- one user message containing the original prompt;
- neutral `Worker A visible output` and `Worker B visible output` sections; or
- a structured unavailable note for a failed/missing witness.

Only text accumulated from normalized `seat_delta` events enters the handoff. Provider completion
objects, reasoning fields, usage, credentials, and raw errors are excluded. Each worker output is
bounded to 100,000 characters. Overflow retains deterministic equal head/tail portions separated
by an explicit truncation marker, and `moderator_started.input_truncated` records each affected
seat. No summarizer/model call is introduced.

## Witness Isolation

Each worker still receives a separately allocated message list containing only the original user
prompt. Worker events are captured downstream by the registry; neither worker is called again and
neither receives peer identity, peer output, Moderator input, or Moderator output. Only the
Moderator receives the neutral fan-in message.

## Streaming / Replay

The Moderator uses the Mission 002 capability check. Native providers emit incremental
`moderator_delta`; request/response providers emit their complete visible result as one delta.
Events are:

- `moderator_started` with `actor: moderator`, selected model, and truncation metadata;
- `moderator_delta` with `actor: moderator` and visible text;
- `moderator_completed` with optional usage and finish reason; or
- `moderator_failed` with the failure.

No Moderator `seat_id` is fabricated. All events are created by `RunEventJournal.append`, so they
share the worker run ID and one globally monotonic sequence. Existing cursor replay and live tailing
therefore reproduce Moderator deltas without a second protocol or duplicate sequence source.

## Failure / Partial Success

Full `run_completed` is deferred until Moderator success. Two successful workers plus Moderator
success yields `completed`. One worker failure plus Moderator success preserves `seat_failed` and
yields honest `partial`. Moderator failure preserves all retained worker deltas, appends
`moderator_failed` and `run_failed`, and marks the run failed without successful completion. Both
worker failures follow the explicit insufficient-input failure path and cannot fabricate synthesis.

## Cancellation

The registry remains the owner of the complete worker-plus-Moderator task. Explicit cancellation
before fan-in closes the worker generator, cancels both local workers, and prevents Moderator start.
Cancellation during a streaming or fallback Moderator propagates through the provider await,
appends the existing replayable `run_cancelled`, and never emits `moderator_completed` or
`run_completed`. Cancellation remains idempotent. Subscriber disconnect remains independent.

The worker queue now awaits directly when disconnect polling is not requested. This avoids Python
3.10 `wait_for` cancellation races for registry-owned runs while retaining the legacy polling path
used by the standalone Mission 002 disconnect test.

## Output-Limit Hook

`ModeratorOutputLimits` provides an isolated future integration point for warning and hard token
limits. Finish reasons already flow to `moderator_completed`. The current provider abstraction has
no normalized max-output-token argument, so this mission does not claim enforcement: requesting a
hard cap fails clearly before the Moderator starts. The warning threshold is passed as execution
metadata but is not enforced until normalized token counting exists.

## Test Evidence

- `uv run pytest -q backend/tests/test_modelmix_moderator.py
  backend/tests/test_modelmix_streaming.py backend/tests/test_modelmix_journal.py
  backend/tests/test_provider_openai_oauth.py` — 28 passed.
- `uv run pytest -q` — 463 passed.
- `npm run build` from `frontend/` — passed; Vite transformed 431 modules.
- `uv run ruff check backend/modelmix backend/tests/test_modelmix_moderator.py` — passed.
- `git diff --check` — passed.

Deterministic fakes cover delayed two-worker fan-in, visible-only input, witness isolation, hidden
field exclusion, successful and failed workers, insufficient input, labeled native streaming,
canonical sequences/run IDs, replay identity, non-stream fallback, Moderator failure preservation,
pre-Moderator cancellation, in-Moderator cancellation, truncation metadata, and unsupported hard
cap rejection. Existing ModelMix suites remain unchanged and pass.

## Known Limitations

- Moderator selection is a request field only; Settings and frontend selection are deferred.
- The experimental frontend deliberately remains a two-pane observer and ignores Moderator events.
- Input limits are character-based; normalized provider token counting/output caps do not yet exist.
- Provider cancellation and billing termination remain best effort.
- Journals and run state retain the existing single-process alpha limitation.

## Recommended Mission 006

Extend the experimental ModelMix observer with a center Moderator pane that renders and reconnects
the existing Moderator events while preserving the independent Worker A/B panes and explicit
Send/Stop controls.
