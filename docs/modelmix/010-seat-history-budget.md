# Mission 010 — Seat History Budget

Route: Big Pickle (OpenCode Zen)
Punch Board items: 17 (partial), 8
Base: `main` @ `cd403d7`
Date: 2026-08-29
Result: **PASS (LOCAL)**

## Objective

Give seat history its own bounded character budget, owned by `history.py`,
without changing Moderator current-turn behavior.

## Delivered

- Added ModelMix-owned constants in `backend/modelmix/history.py`:
  `MAX_HISTORY_MESSAGE_CHARS = 4_000` and `MAX_HISTORY_TOTAL_CHARS = 24_000`;
  `MAX_SEAT_HISTORY_TURNS = 8` is unchanged.
- Added local `_bounded_history_text(text) -> tuple[str, bool]` using
  `MAX_HISTORY_MESSAGE_CHARS`. It mirrors the existing deterministic
  middle-truncation shape (`head`, marker, `tail`) exactly, so a truncated
  message is exactly `MAX_HISTORY_MESSAGE_CHARS` characters long.
- Removed `from .moderator import _bounded_visible_text`. `history.py` no longer
  depends on a private symbol in `moderator.py`.
- Both the historical user prompt and the historical assistant answer are now
  bounded per-message at 4,000 characters.
- `MAX_HISTORY_TOTAL_CHARS` is enforced across the assembled history for one
  seat. Oldest turns are evicted first, whole turns only (an assistant message
  is never emitted without its paired user message), until the total is within
  budget or nothing remains.
- Both caps apply: the turn cap trims to the last 8 turns, then the character
  budget trims further from the oldest end.
- Added the one-line invariant comment: `session["runs"]` is chronological
  because `create_run` appends (verified at `backend/modelmix/persistence.py:124`).
- `moderator.py`, `registry.py`, and `orchestrator.py` are untouched.
  `MAX_VISIBLE_OUTPUT_CHARS = 100_000` and current-turn worker-output bounding
  are unchanged. `build_seat_history` signature and its callers are unchanged.

Worst-case single-seat history is now capped at 24,000 characters instead of the
previous ~1.6M-character worst case.

## Acceptance Coverage

1. Truncation to exactly `MAX_HISTORY_MESSAGE_CHARS` with the marker in the
   middle: covered by the new `_bounded_history_text` test plus the updated
   bounding test.
2. History exceeding `MAX_HISTORY_TOTAL_CHARS` drops oldest turns until within
   budget: new `test_over_budget_history_drops_oldest_turns_until_within_total_budget`.
3. Strictly alternating user/assistant pairs after eviction — explicitly
   asserted; no orphan assistant message: `test_eviction_never_emits_orphan_assistant_message`.
4. Character budget binds before the 8-turn cap: `test_total_budget_binds_before_eight_turn_cap`.
5. Regression that `assemble_moderator_input` still bounds current-turn worker
   output at `MAX_VISIBLE_OUTPUT_CHARS`: `test_moderator_current_turn_output_still_bounded_at_visible_cap`.
6. Mission 009 seat-isolation tests pass unmodified.
7. History that fits within both budgets is returned unchanged:
   `test_history_within_both_budgets_is_returned_unchanged`.

## New per-message budget vs. Mission 009 bounding test

`test_build_seat_history_caps_latest_qualifying_turns_and_bounds_each_message`
in `test_modelmix_persistence.py` asserted that history messages are bounded at
`MAX_VISIBLE_OUTPUT_CHARS` (100,000). Mission 010 explicitly replaces the
per-message history bound with `MAX_HISTORY_MESSAGE_CHARS` (4,000), so that
single bounding test's stale assertion was updated to the new budget. The two
actual seat-isolation tests
(`test_build_seat_history_uses_only_own_nonempty_messages_without_mutation` and
`test_build_seat_history_is_empty_for_fresh_session`) are unmodified.

## Validation

Pytest's default Windows temp root at
`C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo` is unreadable to the
current account (`PermissionError: [WinError 5] Access is denied`), the same
environment limitation recorded in Mission 009. `TEMP` and `TMP` were therefore
pointed at the workspace-local `.pytest_temp` directory before running the exact
requested pytest commands.

Command:

```text
uv run pytest backend/tests/test_modelmix_persistence.py backend/tests/test_modelmix_journal.py backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py -q
```

Raw unedited output:

```text
..........................................                               [100%]
42 passed in 4.43s
```

Command:

```text
uv run pytest backend/tests -q
```

Raw unedited output:

```text
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
.....................................................                    [100%]
341 passed in 12.14s
```

Focused style check on changed files:

```text
uv run ruff check backend/modelmix/history.py backend/tests/test_modelmix_history.py backend/tests/test_modelmix_persistence.py
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

Raw unedited output (Git also emits the existing LF-to-CRLF working-copy warnings):

```text
 backend/modelmix/history.py                | 36 +++++++++++++++++++++++++-----
 backend/tests/test_modelmix_persistence.py | 15 ++++++++-----
 2 files changed, 40 insertions(+), 11 deletions(-)
```

As expected for unstaged new files, this command does not list
`backend/tests/test_modelmix_history.py`, this mission report, or the
bookkeeping/README edits. All are present in the working tree and are included
in the Mission 010 deliverable.

## Punch Board Mapping

- Item `8` (context isolation policy): seat history and its bounds remain owned
  by the seat; the new budget is applied per seat without any cross-seat change.
- Item `17` (basic spend/runtime guardrails): partial progress — seat-history
  context is now deterministically bounded per message and per seat, which is
  the first explicit context/spend bounding hook beyond turn count and Stop.
  Timeout/cost-token ceilings and output warning/hard cap remain open.