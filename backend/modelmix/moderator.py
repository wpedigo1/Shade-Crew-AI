"""Moderator input assembly and execution for ModelMix."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..providers.base import LLMProvider
from ..providers.openrouter import compute_openrouter_cost_usd
from . import guardrails, timeouts
from .orchestrator import EventFactory
from .timeouts import aiter_with_deadline

MAX_VISIBLE_OUTPUT_CHARS = 100_000

MODERATOR_INSTRUCTIONS = """You are the ModelMix Moderator. Produce the best final answer to the
user by evaluating and reconciling the visible witness outputs. Resolve discrepancies using sound
reasoning. Do not rank, vote, debate, mechanically concatenate, or mention hidden reasoning. A
missing witness may be noted as unavailable, but do not invent its evidence."""


@dataclass(frozen=True)
class ModeratorOutputLimits:
    """Future output-limit integration point; enforcement is not yet supported."""

    warning_threshold_tokens: Optional[int] = None
    hard_cap_tokens: Optional[int] = None


@dataclass(frozen=True)
class ModeratorInput:
    messages: List[Dict[str, str]]
    truncation: Dict[str, bool]


def _bounded_visible_text(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_VISIBLE_OUTPUT_CHARS:
        return text, False
    marker = "\n\n[... visible output truncated deterministically ...]\n\n"
    available = MAX_VISIBLE_OUTPUT_CHARS - len(marker)
    head = available // 2
    tail = available - head
    return f"{text[:head]}{marker}{text[-tail:]}", True


def assemble_moderator_input(
    prompt: str,
    worker_outputs: Dict[str, str],
    worker_failures: Dict[str, str],
    history: Optional[List[Dict[str, str]]] = None,
    moderator_guidance: Optional[str] = None,
) -> ModeratorInput:
    """Build a bounded handoff from visible deltas and structured failure notes only."""
    instructions = MODERATOR_INSTRUCTIONS
    if moderator_guidance is not None:
        instructions = (
            f"{MODERATOR_INSTRUCTIONS}\n\n"
            f"Additional guidance from the user:\n{moderator_guidance}"
        )
    sections = [f"Original user prompt:\n{prompt}"]
    truncation: Dict[str, bool] = {}
    for seat_id, label in (("worker_a", "Worker A"), ("worker_b", "Worker B")):
        if seat_id in worker_outputs:
            visible, truncated = _bounded_visible_text(worker_outputs[seat_id])
            truncation[seat_id] = truncated
            sections.append(f"{label} visible output:\n{visible}")
        else:
            status = (
                "Unavailable because the worker failed."
                if seat_id in worker_failures
                else "Unavailable because no visible output was produced."
            )
            sections.append(f"{label} status:\n{status}")
    return ModeratorInput(
        messages=[
            {"role": "system", "content": instructions},
            *(history or []),
            {"role": "user", "content": "\n\n".join(sections)},
        ],
        truncation=truncation,
    )


async def run_moderator(
    model_id: str,
    provider: LLMProvider,
    moderator_input: ModeratorInput,
    create_event: EventFactory,
    output_limits: Optional[ModeratorOutputLimits] = None,
    seat_timeout: Optional[float] = None,
    warning_threshold_chars: Optional[int] = None,
    hard_cap_chars: Optional[int] = None,
    temperature: Optional[float] = None,
) -> bool:
    """Stream or query one Moderator and publish through the canonical event factory."""
    limits = output_limits or ModeratorOutputLimits()
    if limits.hard_cap_tokens is not None:
        raise ValueError("Moderator hard output caps are not supported by the provider contract")
    bound = timeouts.SEAT_TIMEOUT_SECONDS if seat_timeout is None else seat_timeout
    warning_limit = (
        guardrails.WARNING_OUTPUT_THRESHOLD_CHARS
        if warning_threshold_chars is None
        else warning_threshold_chars
    )
    cap = (
        guardrails.HARD_OUTPUT_CAP_CHARS
        if hard_cap_chars is None
        else hard_cap_chars
    )
    provider_kwargs: Dict[str, Any] = {}
    if temperature is not None:
        provider_kwargs["temperature"] = temperature

    await create_event(
        "moderator_started",
        actor="moderator",
        model=model_id,
        input_truncated=moderator_input.truncation,
        output_warning_threshold_tokens=limits.warning_threshold_tokens,
    )
    try:
        if provider.supports_streaming:
            usage = None
            finish_reason = None
            emitted = 0
            warned = False
            capped = False
            stream = provider.stream_query(model_id, moderator_input.messages, **provider_kwargs)
            async for item in aiter_with_deadline(stream, bound):
                if item.type == "text_delta" and item.delta:
                    delta, capped = guardrails.clip_delta(
                        item.delta, emitted, cap
                    )
                    if delta:
                        emitted += len(delta)
                        await create_event("moderator_delta", actor="moderator", delta=delta)
                    if (
                        not warned
                        and emitted >= warning_limit
                    ):
                        warned = True
                        await create_event(
                            "moderator_output_warning",
                            actor="moderator",
                            chars=emitted,
                            threshold=warning_limit,
                        )
                    if capped:
                        await guardrails.close_stream(stream)
                        break
                elif item.type == "completed":
                    usage = item.usage or (item.result or {}).get("usage")
                    finish_reason = item.finish_reason
                elif item.type == "error":
                    raise RuntimeError(item.error_message or "Moderator stream failed")
        else:
            result = await asyncio.wait_for(
                provider.query(model_id, moderator_input.messages, **provider_kwargs), timeout=bound
            )
            if result.get("error"):
                raise RuntimeError(result.get("error_message") or "Moderator query failed")
            content = str(result.get("content") or "")
            capped = len(content) > cap
            if capped:
                content = content[:cap]
            if content:
                await create_event("moderator_delta", actor="moderator", delta=content)
            usage = result.get("usage")
            finish_reason = result.get("finish_reason")

        payload: Dict[str, Any] = {"actor": "moderator"}
        if usage is not None:
            payload["usage"] = usage
        cost_usd = compute_openrouter_cost_usd(model_id, usage)
        if cost_usd is not None:
            payload["cost_usd"] = cost_usd
        if guardrails.should_warn_cost(cost_usd):
            await create_event(
                "moderator_cost_warning",
                actor="moderator",
                cost_usd=cost_usd,
                threshold=guardrails.WARNING_COST_USD_THRESHOLD,
            )
        finish_reason = "modelmix_output_cap" if capped else finish_reason
        if finish_reason is not None:
            payload["finish_reason"] = finish_reason
        await create_event("moderator_completed", **payload)
        return True
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        await create_event(
            "moderator_failed",
            actor="moderator",
            error=f"Moderator timed out after {bound:g} seconds",
            reason="timeout",
        )
        return False
    except Exception as exc:
        await create_event("moderator_failed", actor="moderator", error=str(exc))
        return False
