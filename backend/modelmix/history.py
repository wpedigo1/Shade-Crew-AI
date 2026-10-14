"""Seat-scoped historical context assembly for ModelMix sessions."""

from __future__ import annotations

from typing import Any, Dict, List

MAX_SEAT_HISTORY_TURNS = 8
MAX_HISTORY_MESSAGE_CHARS = 4_000
MAX_HISTORY_TOTAL_CHARS = 24_000

_HISTORY_TRUNCATION_MARKER = "\n\n[... history truncated deterministically ...]\n\n"


def _bounded_history_text(text: str) -> tuple[str, bool]:
    """Deterministically middle-truncate one historical message to its budget."""
    if len(text) <= MAX_HISTORY_MESSAGE_CHARS:
        return text, False
    available = MAX_HISTORY_MESSAGE_CHARS - len(_HISTORY_TRUNCATION_MARKER)
    head = available // 2
    tail = available - head
    return (
        f"{text[:head]}{_HISTORY_TRUNCATION_MARKER}{text[-tail:]}",
        True,
    )


def build_seat_history(
    session_document: Dict[str, Any],
    seat_id: str,
    *,
    exclude_run_id: str,
    max_turns: int = MAX_SEAT_HISTORY_TURNS,
) -> List[Dict[str, str]]:
    """Return bounded prior prompt/answer pairs visible to exactly one seat."""
    if max_turns <= 0:
        return []

    session = session_document["session"]
    messages = session["messages"]
    # session["runs"] is chronological because create_run appends.
    turns: List[List[Dict[str, str]]] = []
    for run in session["runs"]:
        run_id = run["run_id"]
        if run_id == exclude_run_id:
            continue
        own_message = next(
            (
                message
                for message in messages
                if message.get("run_id") == run_id
                and message.get("seat") == seat_id
                and message.get("content")
            ),
            None,
        )
        if own_message is None:
            continue
        prompt, _ = _bounded_history_text(run["prompt"])
        answer, _ = _bounded_history_text(own_message["content"])
        turns.append([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ])

    turns = turns[-max_turns:]
    total_chars = sum(
        len(message["content"]) for turn in turns for message in turn
    )
    while turns and total_chars > MAX_HISTORY_TOTAL_CHARS:
        evicted = turns.pop(0)
        total_chars -= sum(
            len(message["content"]) for message in evicted
        )

    return [message for turn in turns for message in turn]
