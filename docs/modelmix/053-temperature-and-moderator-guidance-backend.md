# Mission 053 — Temperature Control and Moderator Guidance (Backend)

Date: 2026-09-02 CT · Base: main @ `65729ea` (Mission 051)

## What changed

Backend-only. `TwoWorkerRequest` gains two optional ModelMix-native per-request
fields, threaded through the established Mission 020 chain so that `None`
means byte-for-byte unchanged behavior.

### `backend/modelmix/routes.py`

- `TwoWorkerRequest.temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)`.
- `TwoWorkerRequest.moderator_guidance: Optional[str] = Field(default=None, max_length=2000)`.
- Both passed to `run_registry.start(...)`. Pydantic validates bounds/length
  before any provider resolution or call.

### `backend/modelmix/registry.py`

- `temperature` and `moderator_guidance` threaded `start` → `_run` →
  `_run_phase` exactly like `warning_threshold_chars`.
- `temperature` forwarded to `multiplex_workers` and `run_moderator`;
  `moderator_guidance` forwarded to `assemble_moderator_input`.

### `backend/modelmix/orchestrator.py`

- `multiplex_workers` gains `temperature: Optional[float] = None`.
- Both worker call sites (streaming `stream_query`, non-streaming `query`)
  pass `temperature` only when not `None`, via a `provider_kwargs` dict —
  when `None`, no `temperature` kwarg at all, so each provider's own default
  applies. No new ModelMix-level default.

### `backend/modelmix/moderator.py`

- `run_moderator` gains `temperature: Optional[float] = None`; both moderator
  call sites use the same conditional `provider_kwargs` pattern.
- `assemble_moderator_input` gains `moderator_guidance: Optional[str] = None`.
  When provided, the system message becomes
  `MODERATOR_INSTRUCTIONS + "\n\nAdditional guidance from the user:\n" + guidance`
  — strictly append-only. `MODERATOR_INSTRUCTIONS` itself is untouched; when
  `None`, the system message is byte-for-byte identical to today.

## Boundaries honored

- Guidance append-only; never replaces or precedes the instructions.
- ModelMix-only: no Council/Advisor path touched.
- `backend/settings.py` untouched — per-request fields only, no server-side
  persistence (Mission 020 pattern; frontend persistence is a later mission).
- No per-provider special-casing; temperature is passed through as-is.
- No new dependencies; no `schema_version` bump.

## Tests (10 new)

`test_modelmix_streaming.py` (+5): worker `temperature` reaches
`query`/`stream_query` exactly (streaming + non-streaming, via a
`RecordingProvider` that captures exact kwargs); omitted `temperature`
results in NO `temperature` kwarg at all (regression proof, both paths);
`moderator_guidance` > 2000 chars rejected by validation; `temperature`
outside `[0.0, 2.0]` rejected; boundary values 0.0/2.0 and 2000-char
guidance accepted.

`test_modelmix_moderator.py` (+5): guidance appended after the FULL unmodified
`MODERATOR_INSTRUCTIONS` (exact containment + ordering); omitted guidance
leaves the system message byte-identical (`== MODERATOR_INSTRUCTIONS`);
guidance reaches the real system message through a full registry run;
moderator + worker `temperature` reaches providers exactly through a full
registry run (streaming + non-streaming); omitted `temperature` never
reaches any provider through a full registry run (both paths).

## Validation (observed)

- `uv run pytest backend/tests/test_modelmix_moderator.py
  backend/tests/test_modelmix_streaming.py -q --basetemp=...` → **30 passed**.
- `uv run pytest backend/tests -q --basetemp=...` → **535 passed**
  (525 prior + 10 new).
- `cd frontend && npm test` → **166 passed** (nothing frontend changed).
- `npm run build` → clean; `npm run lint` → clean.
- `--basetemp` is the established workaround for the known pre-existing
  `pytest-of-wpedigo` ACL `WinError 5`.

## Remaining risks / open items

- Frontend controls for temperature/guidance and local persistence are a
  separate, later mission (Punch Board item 26 remains PARTIAL).
- Providers that ignore or reject a custom `temperature` are a
  provider-capability question outside this mission's scope.
