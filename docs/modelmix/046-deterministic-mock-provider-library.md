# Mission 046 — Deterministic Mock Provider Library

Date: 2026-09-02 CT · Base: main @ `3f2597b` (Mission 045)

## What changed

Additive test infrastructure only. No production code and no existing test was
modified; nothing outside `backend/tests/` was touched.

### `backend/tests/mock_providers.py`

One shared, composable library of ten plain `LLMProvider` factory functions
implementing the real interface from `backend/providers/base.py`
(`query`, `stream_query` yielding `ProviderStreamEvent`, `supports_streaming`):

1. `normal_provider(content, usage, supports_streaming=True)` — single complete
   response on both `query()` and `stream_query()` paths.
2. `streaming_provider(deltas, usage, finish_reason)` — `text_delta` events then
   `completed`.
3. `slow_streaming_provider(deltas, delay_between=0.01)` — small controllable
   per-delta delay for timeout/cancellation tests (tiny default, no real sleeps).
4. `failing_provider(error_message)` — errors on both streaming (`type="error"`)
   and non-streaming (`{"error": True, "error_message": ...}`) paths.
5. `timeout_provider()` — hangs forever, never yielding a terminal event; no
   timeout logic of its own (the caller's `aiter_with_deadline`/`wait_for`
   bounds it).
6. `rate_limited_provider()` — error shaped like a real rate limit, matching the
   repo's existing convention (`"Rate limit exceeded (HTTP 429)"`, "429").
7. `cancellation_aware_provider(deltas)` — re-raises `asyncio.CancelledError`
   cleanly and records `.cancelled`.
8. `malformed_event_provider()` — yields a `ProviderStreamEvent` with an
   unexpected `type` value, then a normal completion (documented contract
   violation for testing provider-misbehavior handling).
9. `missing_usage_provider(content)` — completes normally with `usage=None` on
   both paths.
10. `out_of_order_provider(deltas)` / `duplicate_provider(deltas)` — reordered
    and repeated `text_delta` arrival for sequence/dedup handling.

Each returns a plain subclass instance, is genuinely simple, and keeps default
timing fast. No new dependency.

### `backend/tests/test_mock_providers.py`

13 tests — one direct test per fixture proving documented behavior, plus a
demonstration that the library genuinely replaces an ad-hoc fake: a real
`multiplex_workers` flow driven by `streaming_provider`, asserting streamed
deltas, persisted usage, and finish reason.

## Validation (observed)

- `uv run pytest backend/tests/test_mock_providers.py -v --basetemp=...` →
  **13 passed**.
- `uv run pytest backend/tests -q --basetemp=...` → **507 passed** (494 prior +
  13 new).
- `cd frontend && npm test` → **148 passed**; `npm run build` → built clean;
  `npm run lint` → clean. (Nothing frontend changed; run as required.)

As in Missions 043/044/045, the literal `--basetemp`-less commands reproduce
the known pre-existing environmental `WinError 5` on the corrupt
`pytest-of-wpedigo` system temp dir; the workspace `--basetemp` override is
the established workaround.

## Doc updates

- `PUNCH-BOARD.md` item 14 → **SATISFIED**.
- `MISSION-INDEX.md` (row + result) and `ENGINEERING-PROGRESS.md` (result)
  updated.

## Remaining risks / open items

- The library is additive; the ~5 existing test files that hand-roll their own
  fakes are deliberately not migrated (out of scope by design). Future tests
  can import `backend.tests.mock_providers` directly.