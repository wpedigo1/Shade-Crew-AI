"""ModelMix-owned cumulative output bounds for a single participant turn.

Worker A, Worker B, and the Moderator share one hard output cap so no single
turn can generate unbounded visible output. The values below are provisional
defaults; configurable thresholds arrive in a later settings mission.

The output cap is distinct from the wall-clock timeouts in timeouts.py and the
historical char budgets in history.py. Whichever bound is reached first
governs; reaching the output cap is a ModelMix termination
(finish_reason "modelmix_output_cap"), never a provider or failure outcome.
"""

from __future__ import annotations

from typing import Any

WARNING_OUTPUT_THRESHOLD_CHARS = 20_000
HARD_OUTPUT_CAP_CHARS = 40_000

MIN_OUTPUT_CHARS_BOUND = 100
MAX_OUTPUT_CHARS_BOUND = 200_000

# Provisional per-seat spend "notice this" threshold in USD. Fires a single
# informational warning once a real per-turn cost is known at completion; it
# never blocks or alters the completed run. This is informational only —
# enforcement/cutoff and cumulative session totals are separate, undecided
# future work. 0.10 (ten cents for one seat's response) is a sensible notice
# default, same provisional spirit as the character thresholds above.
WARNING_COST_USD_THRESHOLD = 0.10


def should_warn_cost(cost_usd: Any) -> bool:
    """Whether a real per-seat cost warrants an informational warning.

    Only a real, finite number strictly above the threshold warns. ``None``
    (non-OpenRouter or uncached pricing) and sub-threshold values never warn —
    absence of cost data is unknown, not a warning condition.
    """
    if cost_usd is None:
        return False
    if not isinstance(cost_usd, (int, float)) or not _finite(cost_usd):
        return False
    return cost_usd > WARNING_COST_USD_THRESHOLD


def _finite(value: Any) -> bool:
    try:
        return float(value) == float(value) and float(value) not in (float("inf"), float("-inf"))
    except (TypeError, ValueError):
        return False


def clip_delta(delta: str, emitted: int, cap: int) -> tuple[str, bool]:
    """Clip one stream delta so cumulative emitted chars never exceed cap.

    Returns (delta_to_emit, capped). The clipped delta always keeps the output
    at exactly `cap` characters when the producer would have gone over.
    `capped` is True exactly when the cumulative budget is exhausted, so
    callers stop consuming the provider stream instead of waiting for more.
    """
    remaining = cap - emitted
    if remaining <= 0:
        return "", True
    if len(delta) > remaining:
        return delta[:remaining], True
    return delta, False


async def close_stream(stream: Any) -> None:
    """Best-effort explicit close of a provider stream after an output cap.

    Breaking out of the wrapped deadline iterator does not deterministically
    close the provider's own async iterator, so close it directly when it
    exposes `aclose`. A stream without `aclose`, or one that errors on close
    (already closed, provider-specific teardown failure), must never disturb
    the capped terminal outcome.
    """
    if hasattr(stream, "aclose"):
        try:
            await stream.aclose()
        except Exception:
            pass