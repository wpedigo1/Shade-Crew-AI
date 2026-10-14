# Mission 044 — Real Cost Computation (Backend, OpenRouter Only)

Date: 2026-09-02 CT · Base: main @ `986a2be` · Route: Big Pickle (OpenCode Zen)

## What changed

The pricing data OpenRouter already reports was being parsed and thrown away;
this mission preserves it, caches it, and multiplies it by the real usage
tokens Mission 015 already captures.

### `backend/providers/openrouter.py`

- `get_models()` now includes `prompt_price_per_token` and
  `completion_price_per_token` in each returned model dict, alongside the
  unchanged `is_free` derivation.
- Module-level `_PRICING` dict, keyed by the bare upstream model id, is
  populated/refreshed on every successful `get_models()` fetch (last fetch
  wins; no TTL). Fresh app state starts with an empty cache: pricing is simply
  unavailable until the first successful fetch.
- New `compute_openrouter_cost_usd(model_id, usage)` returns a real USD figure
  only when ALL hold:
  - model id is `openrouter:`-prefixed;
  - the bare model id has a cached entry;
  - `usage` carries real, numeric, non-negative `prompt_tokens` and
    `completion_tokens`.
  Otherwise it returns `None` — callers leave `cost_usd` entirely absent
  (never `0`, never estimated).

### `backend/modelmix/orchestrator.py` and `backend/modelmix/moderator.py`

At the exact existing Mission 015 usage-capture points (streaming
`completed` event and non-streaming `query` result), the computed
`cost_usd` — when computable — is attached as a sibling field on the same
`seat_completed`/`moderator_completed` payload that already carries `usage`.
No new capture path, no other event touched.

### `backend/modelmix/persistence.py`

`_apply_event` extends the additive `usage`/`finish_reason` pattern: a new
`cost_usd: None` field on canonical messages, set from the event when present,
never overwritten by absence. No `schema_version` bump.

## What was deliberately NOT built

- No spend cap, warning threshold, or enforcement. What should happen when a
  dollar budget is exceeded is an undecided product decision.
- No frontend rendering (separate later mission, matching 015→018→019
  sequencing).
- No pricing for any non-OpenRouter provider. No provider-capability changes
  elsewhere.

## Tests

New `backend/tests/test_modelmix_cost_backend.py` (8 tests) covering:
`get_models()` pricing fields verified against a realistic fake API fixture
with cache population; exact `cost_usd` for a cached priced OpenRouter worker
seat (asserted ≈ 0.0045 exactly derived from token counts × prices); absent
`cost_usd` for uncached OpenRouter pricing; absent `cost_usd` for
non-OpenRouter models with usage present; exact moderator `cost_usd`
(≈ 0.009); moderator absence case; `compute_openrouter_cost_usd` rejection of
missing/non-numeric/negative tokens and unprefixed models.

New persistence regression tests in `test_modelmix_persistence.py`:
`cost_usd` survives a persisted/reopened session for worker and moderator
messages, and stays `None` for messages whose completion events lacked it —
matching Mission 015's exact discipline for `usage`/`finish_reason`.

## Validation (observed)

- `uv run pytest backend/tests/test_modelmix_persistence.py
  backend/tests/test_modelmix_streaming.py backend/tests/test_modelmix_moderator.py -q
  --basetemp=...` → **44 passed**.
- `uv run pytest backend/tests -q --basetemp=...` → **494 passed** (485 prior
  + 9 new).
- `cd frontend && npm test` → **138 passed** (15 files).
- `npm run build` → built clean; `npm run lint` → clean.

Note: the literal `--basetemp`-less commands reproduce the known environmental
`WinError 5` on the corrupt system temp dir `pytest-of-wpedigo` (pre-existing,
documented in Mission 043); the workspace `--basetemp` override is the
established workaround. Nothing frontend changed in this mission; the frontend
commands were run as required and passed unchanged.

## Doc updates

- `docs/modelmix/provider-capability-matrix.md`: pricing section now states
  OpenRouter pricing is preserved, cached, and used for per-seat `cost_usd`,
  not just parsed and discarded.
- `PUNCH-BOARD.md` item 17, `MISSION-INDEX.md` (row + result),
  `ENGINEERING-PROGRESS.md` (result): item 17 advances on the dollar
  visibility half; frontend rendering and any spend-cap decision remain
  explicitly open.

## Remaining risks / open items

- Pricing cache is per-process and only populated by successful OpenRouter
  `get_models()` fetches; a seat run against an OpenRouter model before any
  model-list fetch will have no cost (honest absence, by design).
- OpenRouter catalog prices can change; last-fetch-wins means stale prices
  persist until the next successful fetch.
- `cost_usd` is not yet rendered anywhere in the UI.
