# Mission 009 — Seat-Scoped Multi-Turn Context

Route: Codex  
Date: 2026-08-29  
Result: **PASS (LOCAL)**

## Objective

Give Worker A, Worker B, and Moderator bounded histories from their own persisted
seat messages across runs in the same session, with no cross-seat leakage and no
dependency on the model currently assigned to a seat.

## Delivered

- Added `backend/modelmix/history.py` with `build_seat_history(...)` and an
  eight-turn module cap.
- Historical prompt and answer messages are bounded independently through the
  existing deterministic visible-text helper.
- Worker provider messages now contain only that worker seat's history followed
  by the current user prompt.
- Moderator provider messages contain its system instruction, prior user prompts
  and Moderator answers, then the current prompt/current worker-output handoff.
- `RunRegistry.start()` loads the canonical session before creating the new run,
  builds all histories without mutating persisted state, and passes them through
  the existing orchestration path.
- History is keyed only by `seat_id`; changing a model ID does not change the
  history source.
- No frontend, endpoint, schema-version, SSE, journal, replay, cancellation,
  provider, credential, settings, telemetry, Solo, Compare, timeout, or output-cap
  behavior changed.

## Acceptance Coverage

Distinct sentinel fixtures verify:

1. each turn-2 worker receives its own turn-1 prompt and answer;
2. neither worker receives any substring from the other worker's prior answer;
3. worker messages never receive Moderator output;
4. Moderator receives its own prior answer and prompt plus current worker output,
   but receives no prior worker output;
5. non-empty partial output from a failed seat is retained while an empty failed
   seat contributes no history, and turn 2 still completes;
6. changing Worker A's model on turn 2 preserves Worker A history;
7. only the latest eight qualifying prior turns are included, with each message
   deterministically bounded;
8. a fresh session produces an empty history and retains the existing one-prompt
   provider message shape.

## Validation

Pytest's default Windows temp root at
`C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo` was present but unreadable
to the current account (`Get-Acl` returned an unauthorized-operation error).
`TEMP` and `TMP` were therefore pointed to a workspace-local temporary directory
before running the exact requested pytest commands. No external temp directory
was modified or removed.

Command:

```text
uv run pytest backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py -q
```

Raw unedited output:

```text
..........................................                               [100%]
42 passed in 4.74s
```

Command:

```text
uv run pytest backend/tests -q
```

Raw unedited output:

```text
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
..............................................                           [100%]
334 passed in 11.73s
```

Additional focused style check:

```text
uv run ruff check backend/modelmix/history.py backend/modelmix/orchestrator.py backend/modelmix/moderator.py backend/modelmix/registry.py backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py
```

Raw unedited output:

```text
All checks passed!
```

## Git Diff Stat

Command:

```text
git diff --stat
```

Stat output (Git also emitted existing LF-to-CRLF working-copy warnings):

```text
 backend/modelmix/moderator.py              |   2 +
 backend/modelmix/orchestrator.py           |   9 +-
 backend/modelmix/registry.py               |  21 ++++-
 backend/tests/test_modelmix_moderator.py   | 134 +++++++++++++++++++++++++++++
 backend/tests/test_modelmix_persistence.py |  80 +++++++++++++++++
 backend/tests/test_modelmix_streaming.py   |  42 +++++++++
 docs/modelmix/ENGINEERING-PROGRESS.md      |  28 ++++--
 docs/modelmix/MISSION-INDEX.md             |  17 +++-
 docs/modelmix/PUNCH-BOARD.md               |  29 ++++---
 docs/modelmix/README.md                    |   8 +-
 10 files changed, 338 insertions(+), 32 deletions(-)
```

As expected for unstaged new files, this command does not list
`backend/modelmix/history.py` or this mission report. Both are present in the
working tree and are included in the Mission 009 deliverable.

## Punch Board Mapping

- Item 8: satisfied by explicit, tested seat isolation and hot-swap continuity.
- Item 15: satisfied by the persisted worker-to-Moderator vertical slice with
  bounded continuation.
- Item 29: partially satisfied; seat histories, Moderator history, bounding, and
  hot-swap continuity are complete, while retention/delete UX remains open.
