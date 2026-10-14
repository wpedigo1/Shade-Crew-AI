# Mission 050 — Per-Seat Spend Warning (Backend)

Date: 2026-09-02 CT · Base: main @ `6a38114` (Mission 049)

## What changed

A single, informational per-seat spend warning. No enforcement, no cutoff, no
cumulative tracking. Backend only.

### `backend/modelmix/guardrails.py`

- `WARNING_COST_USD_THRESHOLD = 0.10` — a provisional "notice this" default
  (ten cents for a single seat's response). Same spirit as Mission 019's
  provisional character thresholds, not a researched number. It is the
  reasonable point where a single OpenRouter turn's cost becomes worth
  surfacing; sub-cent responses (Mission 044's own `$0.0045` fixture) never
  warn.
- `should_warn_cost(cost_usd)` — True only for a real, finite number strictly
  above the threshold. `None` (non-OpenRouter or uncached pricing) and
  non-numeric/infinite values never warn — absence of cost data is unknown,
  not a warning condition.

### `backend/modelmix/orchestrator.py`

At the exact points where `cost_usd` is already computed for a completed
worker (both the streaming and non-streaming paths, Mission 044), if
`should_warn_cost(cost_usd)`, emit one `seat_cost_warning` event carrying
`{cost_usd, threshold}` just before the `seat_completed` event. Purely
additional — the completion event still carries the real cost.

### `backend/modelmix/moderator.py`

Symmetric: if the moderator's computed `cost_usd` warns, emit one
`moderator_cost_warning` (with `actor="moderator"`) before
`moderator_completed`.

## Structural note (why this differs from the output-length warning)

The output-length warning fires mid-stream because characters accumulate
delta-by-delta. Cost cannot — token counts only arrive on the terminal
`completed` event's `usage`, and estimating cost mid-stream is forbidden.
So this warning fires once, at completion, for one seat's own actual cost.
No running/cumulative session total is tracked (separate, undecided future
feature).

## Boundaries honored

- No enforcement, cutoff, or run-blocking. Strictly informational.
- No cumulative/session-total cost tracking.
- Output-length warning (`WARNING_OUTPUT_THRESHOLD_CHARS`,
  `seat_output_warning`) untouched — a separate parallel mechanism.
- Threshold is a module constant, not per-request configurable (Mission 020
  bounds-style configurability left for later).
- Frontend untouched. No new dependency.

## Tests

`test_modelmix_cost_backend.py` (+8): a worker whose cost exceeds the
threshold emits exactly one `seat_cost_warning` with the correct
`cost_usd`/`threshold` alongside its normal `seat_completed` (both present,
neither replaced); sub-threshold cost emits none; `None`/non-OpenRouter cost
never warns (worker + moderator, all three cases each);
`should_warn_cost` unit cases (None, sub-threshold, exactly-threshold,
inf, string, real above-threshold).

`test_modelmix_guardrails.py` (+1 regression): with a low output-warning
threshold AND a warn-worthy cost on the same seat, both `seat_output_warning`
and `seat_cost_warning` fire, the output warning carries the correct
chars/threshold, and the seat still completes normally with
`finish_reason="stop"` — proving the two mechanisms coexist and the new cost
warning does not disturb the existing output-length warning.

## Validation (observed)

- `uv run pytest backend/tests/test_modelmix_cost_backend.py
  backend/tests/test_modelmix_guardrails.py -v --basetemp=...` → **43 passed**.
- `uv run pytest backend/tests -q --basetemp=...` → **525 passed** (517 prior +
  8 new).
- `cd frontend && npm test` → **157 passed**; `npm run build` → clean;
  `npm run lint` → clean. (Nothing frontend changed; run as required.)

The literal `--basetemp`-less commands reproduce the known pre-existing
`pytest-of-wpedigo` system-temp ACL `WinError 5`; the workspace `--basetemp`
override is the established workaround.

## Doc updates

- `PUNCH-BOARD.md` item 17 → Mission 050 added (spend warning, informational).
- `MISSION-INDEX.md` (row + result), `ENGINEERING-PROGRESS.md` (result).

## Threshold reasoning (provisional)

`0.10` — ten cents for a single seat's response. This is the point at which a
one-turn OpenRouter cost is worth "notice this". It is deliberately a
provisional default, not a researched figure, matching Mission 019's precedent
for the character thresholds.

## Remaining risks / open items

- Enforcement/cutoff (what happens when a dollar budget is exceeded) is still
  an explicitly undecided product question.
- Cumulative/session-total cost tracking is a separate, bigger, undecided
  feature (explicitly out of scope here).
- The warning is not yet rendered anywhere in the UI (separate later mission,
  same split as every other guardrail feature).