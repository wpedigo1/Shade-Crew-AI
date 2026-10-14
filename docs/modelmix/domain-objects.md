# ModelMix Domain Objects

**Mission 043 (foundational domain documentation).** This document defines the
ModelMix domain objects **as they exist in the code**, cited to file/line. It
is written from real repository behavior (`backend/modelmix/persistence.py`,
`journal.py`, `events.py`, `orchestrator.py`, `moderator.py`), not from
aspirational punch-board wording. Where the punch-board wording differs from the
code, this document says so explicitly.

Aligned with Punch Board item **7 = SATISFIED** (see `PUNCH-BOARD.md`).

---

## 1. Threading through the three persistence layers

There are three related but distinct representations of the same objects:

| Concept | In-memory journal | Durable JSON (schema v1) | HTTP/SSE wire |
|---|---|---|---|
| `RunEventJournal` | `backend/modelmix/journal.py:22` | Run snapshot under `session["runs"]` | encoded in the SSE `event` dict |
| Event | `journal.append` built dict already canonical (`journal.py:41-47`) | `run["events"]` list (identical shape) | `data: <json>` per SSE frame |
| Message | not kept in-memory in a separate owner | `session["messages"]` (`persistence.py:82`) | re-derived on reopen / hydrated |

The canonical on-disk unit is **one versioned JSON document per session**
(`persistence.py` docstring lines 1-5, `_path` at `persistence.py:58`). Callers
depend on the `ModelMixPersistence` ABC (`persistence.py:29`), not on the
on-disk representation, so the storage engine is replaceable behind the
ModelMix-owned boundary.

---

## 2. Session document (`schema_version = 1`)

`SCHEMA_VERSION = 1` (`persistence.py:19`). A session document is:

```json
{
  "schema_version": 1,
  "session": {
    "session_id": "...",
    "created_at": <unix float>,
    "updated_at": <unix float>,
    "messages": [],
    "runs": []
  }
}
```

Created by `create_session` (`persistence.py:70-87`). Identity rule: the file's
basename must equal `session["session_id"]` (`_read` check at
`persistence.py:224-225`). Validation guards: `schema_version` must equal
`SCHEMA_VERSION`; `session_id` must be a non-empty string; `created_at` /
`updated_at` must be numeric; `messages`/`runs` must be lists
(`_validate`, `persistence.py:229-240`).

The session is **seat-independent top-level container**; it owns the two ordered
canonical collections — `messages` and `runs`.

---

## 3. Message (canonical persisted message)

Messages are built once per seat per run by `_apply_event`
(`persistence.py:167-211`) and carry seat/audience/role metadata. The canonical
message shape (from `_apply_event`:

```json
{
  "message_id": "<run_id>:<seat>",
  "run_id": "<run_id>",
  "seat": "worker_a" | "worker_b" | "moderator" | "shared",
  "audience": ["worker_a"] | ["worker_b"] | ["moderator","user"] | ["worker_a","worker_b","moderator"],
  "role": "user" | "assistant",
  "content": "...",
  "status": "waiting" | "running" | "completed" | "failed" | "cancelled",
  "error": null | "...",
  "usage": null | <provider-reported dict, opaque>,
  "finish_reason": null | "...",
  "started_at": null | <unix float>,
  "completed_at": null | <unix float>
}
```

Semantics:

- The **shared user message** is appended by `create_run`
  (`persistence.py:125-132`) with `seat="shared"`, `role="user"`,
  `audience=["worker_a","worker_b","moderator"]`, `content=run["prompt"]`.
- Each **assistant message** belongs to exactly one seat. A worker message has
  `audience=[<itself>]`; the moderator message has `audience=["moderator","user"]`
  (`persistence.py:182`). This is the durable encoding of seat-scoped context
  and the Moderator-only fan-in.
- `usage` and `finish_reason` are only written when `event.get(...) is not
  None` (`persistence.py:201-204`) — a real provider value is never clobbered
  with null.
- Validation `_validate` enforces the exact seat/role/audience pairing per seat
  (`persistence.py:274-289`): `shared`→`user`/all; `worker_a`→`assistant`/`[worker_a]`;
  `worker_b`→`assistant`/`[worker_b]`; `moderator`→`assistant`/`[moderator,user]`.

---

## 4. Run snapshot

`create_run` (`persistence.py:118-134`) appends one run snapshot per run. Shape
(see `_validate` required fields, `persistence.py:242`, and `_read`):

```json
{
  "run_id": "...",
  "prompt": "<original user prompt>",
  "models": { "worker_a": "id", "worker_b": "id"?, "moderator": "id"?|null },
  "status": "created"|"active"|"completed"|"partial"|"failed"|"cancelled",
  "latest_seq": <int>,
  "events": [ <Event>, ... ]
}
```

- `models` is validated to carry a non-empty `worker_a` and any present
  `worker_b`/`moderator` keys; the key set is a subset of
  `{worker_a, worker_b, moderator}`; `moderator` may be `null`/absent while
  `worker_b` may not be `null` (`persistence.py:249-263`). This is the relaxed
  Solo/Compare-friendly contract (Missions 030/028).
- `latest_seq` must equal `len(events)` and each event's `seq` must equal its
  1-based index with the correct `run_id` (`persistence.py:264-273`) — replay
  identity and order are part of the run object contract.

---

## 5. Run (runtime owners)

At runtime the "run" is not the JSON snapshot; it is a `RunEventJournal`
(`journal.py:22`). State living only at runtime:

- `run_id`, `status` (mirror), `created_at` (monotonic), `terminal_at`,
  `cancellation_requested`, `session_id`
- `task` (the asyncio task running `_run`)
- `_events` (deque, bounded), `_next_seq`, `_condition`, `persist_event`
  callback that feeds the durable session.

`restore` (`journal.py:87-95`) reconstructs a replayable journal from a snapshot
without prior process memory.

---

## 6. RunEvent (canonical event)

Built atomically by `RunEventJournal.append` (`journal.py:38-55`) and by
`EventSequencer.create` (`events.py`). Canonical shape (from `journal.py:41-47`):

```json
{
  "run_id": "...",
  "seq": 1,
  "type": "<event type string>",
  "ts": <unix float>,
  ...event-specific payload...
}
```

- `seq` is monotonic per run, starting at 1 (`_next_seq = 1`,
  `journal.py:34`, `persistence.py:147` requires contiguity).
- `ts` is a real wall-clock epoch float (`time.time()`), added in Mission 015
  (`journal.py:45`).
- `type` is an arbitrary string; payload is free-form `**payload`.

**Known event types** (from the code that creates them):

| type | creator |
|---|---|
| `run_started` (`seats=[...]`) | `orchestrator.py:142` |
| `seat_started` (`model`) | `orchestrator.py:50` |
| `seat_delta` (`delta`) | `orchestrator.py:82`, `:122` |
| `seat_output_warning` (`chars`,`threshold`) | `orchestrator.py:88` |
| `seat_completed` (`usage?`,`finish_reason?`) | `orchestrator.py:110`, `:128` |
| `seat_failed` (`error`,`reason?`) | `orchestrator.py:134`, `:140` |
| `seat_cancelled` | `orchestrator.py:130` |
| `run_cancel_requested` | `orchestrator.py:154`, `registry.py:158` |
| `run_completed` (`status`) | `orchestrator.py:178`, `registry.py:315` |
| `run_failed` (`error`,`reason?`) | `registry.py` |
| `run_cancelled` | `registry.py` |
| `moderator_started`/`moderator_delta`/`moderator_completed`/`moderator_failed`/`moderator_output_warning`/`moderator_cancelled` | `moderator.py` |

Moderator events carry `actor="moderator"` and their `seat_id`-less payloads are
mapped to `seat="moderator"` in persistence (`persistence.py:170-172`).

---

## 7. Seat

A **seat** is the identity under which context is owned and isolated. The valid
seat ids are `worker_a`, `worker_b`, `moderator` (plus the synthetic `shared`
used for the shared user message). Source of truth: the `seat in
{"worker_a","worker_b","moderator"}` check at `persistence.py:173` and the
message validation set `{"shared","worker_a","moderator","worker_b"}`
(`persistence.py:278`).

Seat ownership is seat-scoped, not model-scoped (locked architecture: seat
history belongs to the seat; `history.py` builds per-seat history keyed by
`seat_id`, `history.py:27-46`).

---

## 8. Moderator

The Moderator is a fan-in participant with:

- a dedicated system instruction `MODERATOR_INSTRUCTIONS`
  (`moderator.py:16-19`) — evaluate/reconcile, do not rank/vote/concatenate;
- a bounded handoff built from *visible* worker output and structured failure
  notes via `assemble_moderator_input` (`moderator.py:46-74`);
- a `MAX_VISIBLE_OUTPUT_CHARS = 100_000` deterministic middle-truncation bound
  on each worker's visible output (`_bounded_visible_text`, `moderator.py:14`,
  `:36-43`);
- persisted audience `["moderator","user"]` (`persistence.py:182`);
- `ModeratorOutputLimits` internally exists but is documented "enforcement is
  not yet supported" (`moderator.py:22-28`) — the live enforcement is the
  character guardrail injected by the orchestrator/registry
  (`warning_threshold_chars`/`hard_cap_chars`), not the token-shaped dataclass.

---

## 9. Provider / Model reference

A `ProviderResolver` is `Callable[[str], LLMProvider]`
(`orchestrator.py:14`), mapping a model id (a prefixed string like
`openrouter:...`, `ollama:...`) to a concrete provider object. Each provider is
an `LLMProvider` (`providers/base.py:20`) with `query`,
`get_models`, `validate_key`, an optional `supports_streaming` flag, and an
optional `stream_query`. The full per-provider capability facts are in
`provider-capability-matrix.md`.

---

## 10. ProviderStreamEvent (streaming contract boundary)

`ProviderStreamEvent` (`providers/base.py:8-17`) is the provider-neutral,
user-visible streaming event with `type` one of
`"text_delta" | "completed" | "error"`, plus optional `delta`, `result`,
`finish_reason`, `usage`, `error_message`. Only one provider
(`OpenAIOauthProvider`) currently emits real streams (`supports_streaming=True`
at `openai_oauth.py:79`); all others fall back to the non-streaming `query`
path.

---

## 11. Artifact / reference

No artifact/attachment domain object exists in the alpha slice. The locked item
7 list names "Artifact/reference" and "Error/terminal result" as concepts; in
the current code these map onto:

- **Error/terminal result** → the persisted message `status`/`error`/`reason`
  fields (`persistence.py:185-211`) and the run `status`
  (`RUN_STATUSES`, `persistence.py:22`).
- **Artifact/reference** → **not implemented**. There is no file/attachment
  object in this alpha. This document records it as absent rather than inventing
  one.

---

## 12. Discrepancy note (punch-board vs code)

The locked item-7 wording uses "partially_completed" as a domain state. The real
code uses **`"partial"`** for a run/seat status (see `persistence.py:21`
`TERMINAL_STATUSES` and `registry.py:314`). These are not the same token. This
document and `run-state-machine.md` use the real value `"partial"`; the
punch-board vocabulary is a stale guess corrected here (see the mission report).