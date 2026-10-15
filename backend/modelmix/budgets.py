"""Explicit Case-run resource rails, independent of legacy single-call defaults."""
from dataclasses import asdict, dataclass
import math
import os


@dataclass(frozen=True)
class ResearchBudget:
    seconds: float
    output_chars: int
    reported_tokens: int
    context_chars: int
    emergency_actions: int
    research_fraction: float = 0.75
    tool_seconds: float = 15.0
    tool_result_chars: int = 16_000

    def __post_init__(self):
        if not all(math.isfinite(v) and v > 0 for v in (self.seconds, self.output_chars, self.reported_tokens, self.context_chars, self.emergency_actions, self.tool_seconds, self.tool_result_chars)):
            raise ValueError('Research budgets must be finite and positive')
        if self.context_chars < 4096 or self.tool_result_chars < 256:
            raise ValueError('Context projection requires at least 4096 chars and tool results at least 256 chars')
        if not 0.1 <= self.research_fraction <= 0.95:
            raise ValueError('Research fraction must be between 0.1 and 0.95')


def _number(name, default, cast=int, maximum=10_000_000):
    raw = os.environ.get(name, str(default))
    try:
        value = cast(raw)
        if not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError()
        return value
    except ValueError as exc:
        raise ValueError(f'{name} must be positive and at most {maximum}') from exc


def case_budgets():
    def seat(prefix, seconds, chars, tokens, context, actions):
        return ResearchBudget(
            seconds=_number(f'SHADE_CREW_{prefix}_SECONDS', seconds, float, 3600),
            output_chars=_number(f'SHADE_CREW_{prefix}_OUTPUT_CHARS', chars),
            reported_tokens=_number(f'SHADE_CREW_{prefix}_REPORTED_TOKENS', tokens),
            context_chars=_number(f'SHADE_CREW_{prefix}_CONTEXT_CHARS', context),
            emergency_actions=_number(f'SHADE_CREW_{prefix}_EMERGENCY_ACTIONS', actions, int, 1024),
            research_fraction=_number('SHADE_CREW_RESEARCH_FRACTION', 0.75, float, 0.95),
            tool_seconds=_number('SHADE_CREW_TOOL_SECONDS', 15, float, 120),
            tool_result_chars=_number('SHADE_CREW_TOOL_RESULT_CHARS', 16000))
    return {'mechanic': asdict(seat('MECHANIC', 600, 64_000, 50_000, 12_000, 128)),
            'chief': asdict(seat('CHIEF', 900, 96_000, 80_000, 18_000, 256)),
            'run_seconds': _number('SHADE_CREW_CASE_RUN_SECONDS', 1200, float, 3600)}
