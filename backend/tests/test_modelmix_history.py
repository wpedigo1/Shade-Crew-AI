"""Mission 010 seat-history budget coverage."""

from backend.modelmix.history import (
    MAX_HISTORY_MESSAGE_CHARS,
    MAX_HISTORY_TOTAL_CHARS,
    MAX_SEAT_HISTORY_TURNS,
    _bounded_history_text,
    build_seat_history,
)
from backend.modelmix.moderator import (
    MAX_VISIBLE_OUTPUT_CHARS,
    assemble_moderator_input,
)


def _full_message(prefix: str) -> str:
    """Return a deterministic message of exactly the per-message budget."""
    return (prefix + "x" * MAX_HISTORY_MESSAGE_CHARS)[:MAX_HISTORY_MESSAGE_CHARS]


def _full_history_document(run_count: int) -> dict:
    """Build a document whose qualifying messages all consume the message budget."""
    runs = []
    messages = []
    for index in range(run_count):
        run_id = f"run-{index}"
        runs.append({
            "run_id": run_id,
            "prompt": _full_message(f"U{index}SENTINEL:"),
            "models": {},
            "status": "completed",
            "latest_seq": 0,
            "events": [],
        })
        messages.append({
            "run_id": run_id,
            "seat": "worker_a",
            "content": _full_message(f"A{index}SENTINEL:"),
        })
        messages.append({
            "run_id": run_id,
            "seat": "worker_b",
            "content": _full_message(f"B{index}SENTINEL:"),
        })
        messages.append({
            "run_id": run_id,
            "seat": "moderator",
            "content": _full_message(f"M{index}SENTINEL:"),
        })
    return {"schema_version": 1, "session": {"runs": runs, "messages": messages}}


def test_history_message_truncated_to_exact_budget_with_middle_marker():
    original = "head-" + "x" * 10_000 + "-tail"

    first, first_flagged = _bounded_history_text(original)
    second, second_flagged = _bounded_history_text(original)

    assert first_flagged is True
    assert second_flagged is True
    assert len(first) == MAX_HISTORY_MESSAGE_CHARS
    assert first == second
    assert first.startswith("head-")
    assert first.endswith("-tail")
    marker_index = first.find("[... history truncated deterministically ...]")
    assert marker_index > 0
    assert marker_index < len(first) - 1
    assert "x" in first[marker_index:]


def test_short_history_message_is_returned_untouched():
    assert _bounded_history_text("SHORT_SENTINEL") == ("SHORT_SENTINEL", False)


def test_over_budget_history_drops_oldest_turns_until_within_total_budget():
    document = _full_history_document(5)

    history = build_seat_history(document, "worker_a", exclude_run_id="run-4")

    assert len(history) == 3 * 2
    assert history[0]["content"] == _full_message("U1SENTINEL:")
    assert history[-1]["content"] == _full_message("A3SENTINEL:")
    assert "run-0" not in str(history)
    assert sum(len(message["content"]) for message in history) == MAX_HISTORY_TOTAL_CHARS


def test_eviction_never_emits_orphan_assistant_message():
    document = _full_history_document(8)

    history = build_seat_history(document, "worker_a", exclude_run_id="run-7")

    assert len(history) != 0
    assert len(history) % 2 == 0
    for index, message in enumerate(history):
        expected_role = "user" if index % 2 == 0 else "assistant"
        assert message["role"] == expected_role
    assert history[0]["role"] == "user"


def test_total_budget_binds_before_eight_turn_cap():
    document = _full_history_document(9)

    history = build_seat_history(document, "worker_a", exclude_run_id="run-8")

    assert len(history) < MAX_SEAT_HISTORY_TURNS * 2
    total = sum(len(message["content"]) for message in history)
    assert total <= MAX_HISTORY_TOTAL_CHARS
    assert total == MAX_HISTORY_TOTAL_CHARS
    assert history[0]["content"] == _full_message("U5SENTINEL:")
    assert history[-1]["content"] == _full_message("A7SENTINEL:")
    for old_turn in ("run-0", "run-1", "run-2", "run-3", "run-4"):
        assert old_turn not in str(history)


def test_moderator_current_turn_output_still_bounded_at_visible_cap():
    long_text = "x" * (MAX_VISIBLE_OUTPUT_CHARS + 10)

    moderator_input = assemble_moderator_input(
        "prompt", {"worker_a": long_text}, {"worker_b": "failed"}
    )

    assert moderator_input.truncation == {"worker_a": True}
    assert "truncated deterministically" in moderator_input.messages[1]["content"]
    section = moderator_input.messages[1]["content"].split("Worker A visible output:\n", 1)[1]
    section = section.split("\n\nWorker B status:", 1)[0]
    assert len(section) == MAX_VISIBLE_OUTPUT_CHARS


def test_history_within_both_budgets_is_returned_unchanged():
    document = {
        "schema_version": 1,
        "session": {
            "runs": [
                {
                    "run_id": "run-1",
                    "prompt": "PROMPT_1",
                    "models": {},
                    "status": "completed",
                    "latest_seq": 0,
                    "events": [],
                },
                {
                    "run_id": "run-2",
                    "prompt": "PROMPT_2",
                    "models": {},
                    "status": "completed",
                    "latest_seq": 0,
                    "events": [],
                },
            ],
            "messages": [
                {"run_id": "run-1", "seat": "worker_a", "content": "ANSWER_1"},
                {"run_id": "run-1", "seat": "worker_b", "content": "B_1"},
                {"run_id": "run-2", "seat": "worker_a", "content": "ANSWER_2"},
                {"run_id": "run-2", "seat": "worker_b", "content": "B_2"},
            ],
        },
    }

    history = build_seat_history(document, "worker_a", exclude_run_id="run-2")

    assert history == [
        {"role": "user", "content": "PROMPT_1"},
        {"role": "assistant", "content": "ANSWER_1"},
    ]
    assert "truncated deterministically" not in str(history)