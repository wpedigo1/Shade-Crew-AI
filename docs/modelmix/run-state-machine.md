# ModelMix Run State Machine

**Mission 043 (foundational domain documentation).** This document describes the
run lifecycle **as implemented** in the current alpha slice
(`backend/modelmix/persistence.py`, `journal.py`, `registry.py`,
`orchestrator.py`, `moderator.py`, `timeouts.py`), cited to file/line.

Aligned with Punch Board item **9 = SATISFIED** (see `PUNCH-BOARD.md`),
except that the punch board's vocabulary uses `partially_completed`; the real
code value is **`partial`**. This document uses the real value.

---

## 1. Status vocabulary (persistence)

Defined at `persistence.py:19-22`:

```python
SCHEMA_VERSION = 1
TERMINAL_STATUSES = {"completed", "partial", "failed", "cancelled"}
RUN_STATUSES = {"created", "active", *TERMINAL_STATUSES}
```

So the **run** status set is: `created`, `active`, `completed`, `partial`,
`failed`, `cancelled`. Terminal set: `completed`, `partial`, `failed`,
`cancelled`.

**Message** status set is a parallel but different set, driven by `_apply_event`
(`persistence.py:185-211`): `waiting`, `running`, `completed`, `failed`,
`cancelled`. Note: `partial` is a *run* status only; a message is either
`completed`, `failed`, or `cancelled`. `partial` therefore describes a run whose
workers had mixed outcomes, not an individual message state.

---

## 2. Run creation

`create_session` (`persistence.py:70`) → `create_run` (`persistence.py:118`)
persist the initial snapshot with `status="created"`. The in-memory
`RunEventJournal` starts at `status="created"` (`journal.py:22`).

The runtime `_run` marks the run `active` as it begins work:
`await run.mark_status("active")` at `registry.py:177`.

---

## 3. `run_started` / seat lifecycle

`multiplex_workers` first emits `run_started` with the list of seats
(`orchestrator.py:142`), then one `run_seat` task per model in
`{"worker_a":..., "worker_b":...}`. Each seat task emits `seat_started`
(`orchestrator.py:50`), then either streams (`seat_delta`) or performs a single
`query`, then emits a terminal seat event: `seat_completed`, `seat_failed`, or
`seat_cancelled` (`orchestrator.py:129-140`).

The multiplexer tracks `terminal_seats` and `failed_seats`
(`orchestrator.py:147-169`) and finishes when every seat task is terminal.

---

## 4. Seat-scoped output guardrails

While consuming a stream, `guardrails.clip_delta` bounds emitted chars to a hard
cap (`orchestrator.py:77`); when `emitted >= warning_limit` it emits
`seat_output_warning` (`orchestrator.py:88`); when capped it calls
`guardrails.close_stream` and sets `finish_reason = "modelmix_output_cap"`
(`orchestrator.py:96-107`). On the non-streaming path, output is truncated to the
cap and `finish_reason = "modelmix_output_cap"` (`orchestrator.py:118-127`).
Constants: `WARNING_OUTPUT_THRESHOLD_CHARS = 20_000`,
`HARD_OUTPUT_CAP_CHARS = 40_000`, bounds 100..200_000
(`guardrails.py:17-21`).

---

## 5. Run terminal transitions

There are two terminal-model writers, depending on whether a Moderator model
resolves.

### 5a. No Moderator (worker-only; `emit_run_completed=True`)

The `multiplex_workers` loop terminal logic (`orchestrator.py:171-178`):

```python
if not cancelled and emit_run_completed:
    if failed_seats and len(failed_seats) == len(tasks):
        status = "failed"
    elif failed_seats:
        status = "partial"
    else:
        status = "completed"
    yield await create("run_completed", status=status)
```

So with **no moderator**:

| worker_a | worker_b | run status |
|---|---|---|
| ok | ok | `completed` |
| ok | failed | `partial` |
| failed | ok | `partial` |
| failed | failed | `failed` |

### 5b. With Moderator (`registry._run_phase`)

`registry._run_phase` consumes the worker stream (`registry.py:242-256`), records
`worker_outputs` from `seat_delta` and `worker_failures` from `seat_failed` /
empty-output (`registry.py:245-254`). It forwards the worker-level `run_completed`
status to the journal when the moderator path emits it
(`registry.py:255-256`). Then, if a moderator model is present and `worker_b`
exists (`registry.py:258`):

- **Both workers failed** → emits `moderator_failed` with
  `reason="insufficient_input"`, then `run_failed` ("Both workers failed") and
  status `failed` (`registry.py:264-273`). No moderator is called.
- **Moderator provider unresolvable** → `moderator_failed`, `run_failed`
  ("Moderator provider resolution failed"), status `failed`
  (`registry.py:282-291`).
- **Moderator task returns not-ok** → `run_failed` ("Moderator failed"),
  status `failed` (`registry.py:310-313`).
- **Moderator ok** → final run status is
  `"partial" if worker_failures else "completed"` (`registry.py:314`), emitted as
  `run_completed(status=...)` then `mark_status(final_status)`
  (`registry.py:315-316`).

So with a moderator, a run that reaches a moderator-completed answer is either
`partial` (at least one worker failed) or `completed` (all workers produced
visible output). A run that cannot produce a moderator answer is `failed`.

---

## 6. Cancellation

- **User/disconnect cancellation**: `run_cancel_requested` is appended as soon
  as `is_disconnected()` returns true (`orchestrator.py:152-156`,
  `registry.py:158`); seat tasks are cancelled. After the multiplexer loop, the
  registry layer appends `run_cancelled` and marks status `cancelled`
  (`registry.py:200-201`).
- **Grace period**: in-flight tasks get up to `CANCEL_GRACE_SECONDS = 5.0` to
  unwind (`await_cancellation_grace`, `timeouts.py:25-27`, `:10`).
- A frontend disconnect is **not** automatically a run cancellation; it is only a
  trigger when `is_disconnected` is supplied (see
  `orchestrator.py:24`, `:152-156`).

---

## 7. Timeouts (seat vs run)

- Per-seat bound: `SEAT_TIMEOUT_SECONDS = 300` (`timeouts.py:8`); applied via
  `aiter_with_deadline` on streams (`orchestrator.py:75`) and
  `asyncio.wait_for` on `_stream_query`/`query` (`orchestrator.py:112-113`,
  `moderator.py:138-165`).
- A seat timeout produces `seat_failed` with `reason="timeout"`
  (`orchestrator.py:132-138`). A moderator timeout produces
  `moderator_failed` with `reason="timeout"` (`moderator.py:175`).
- `RUN_TIMEOUT_SECONDS = 600` (`timeouts.py:9`) is the outstanding run budget;
  when hit, the run is marked `failed` with `reason="timeout"` and emits
  `run_failed` (`registry.py:194-198`).

---

## 8. Terminal outcomes summary

Per AGENTS.md, terminal state must honestly distinguish outcomes. The code maps:

| outcome | run status | evidence |
|---|---|---|
| normal completion | `completed` | `registry.py:314`, `orchestrator.py:177` |
| partial completion | `partial` | `registry.py:314`, `orchestrator.py:175` |
| user / disconnect cancellation | `cancelled` | `registry.py:200-201` |
| failure (worker/moderator/provider/timeout) | `failed` | `registry.py:126`, `:198`, `:204`, `:272`, `:290`, `:312` |
| ModelMix output cap | run may still `completed`/`partial`; seat `finish_reason = "modelmix_output_cap"` | `orchestrator.py:107`,`:127` |

Reset policy: terminal runs are pruned from the in-memory registry by TTL
(`TERMINAL_RUN_TTL_SECONDS = 900`) and by count cap
(`MAX_RETAINED_TERMINAL_RUNS = 100`) in `_prune` (`registry.py:318-339`,
`journal.py:MAX_*`).

---

## 9. Visual flow

```text
created ──► active
              │
              ├─ workers stream  ─► seat_completed/failed/cancelled per seat
              │     │
              │     ├─ (no moderator) ──► completed | partial | failed
              │     │
              │     └─ (with moderator)
              │           ├─ both workers failed      ──► failed (insufficient_input)
              │           ├─ moderator provider err   ──► failed
              │           ├─ moderator task not-ok    ──► failed
              │           └─ moderator ok  ──► partial | completed
              │
              ├─ run timeout (600s)                    ──► failed (timeout)
              └─ disconnect cancel                     ──► cancelled
```

---

## 10. Discrepancy note (punch-board vs code)

The locked item-9 wording lists a terminal state spelled `partially_completed`.
The real value in `TERMINAL_STATUSES` and `registry.py:314` is **`partial`**.
This is a documented vocabulary correction; the punch board remains the product
memory, but the code value is `partial`.