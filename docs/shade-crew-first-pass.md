# First Shade Crew AI surgery

Product: **Shade Crew AI**. Three active seats: **Mechanic A | wider Moderator |
Mechanic B**. This pass replaces browser entry/navigation and product text,
adds named anonymous local endpoint configuration, and preserves the existing
run contracts. Original ModelMix is a read-only provenance reference.

## Retained boundaries

- `worker_a`, `moderator`, `worker_b` remain canonical seat identifiers.
- `/api/modelmix`, `X-ModelMix-*`, event schema, browser storage keys, package
  names and JSON persistence contracts remain unchanged.
- Workers receive only their own seat history plus the user prompt.
- Moderator receives bounded visible worker outputs plus its own history.
- Existing worker-output labels inside Moderator messages are intentionally
  retained. UI seat labels are Mechanic A/B.
- Shared Council/provider/backend code remains where dependencies require it.
  Root browser entry directly loads the cockpit; legacy App is not imported
  into the production entry, and there is no Back to Council action.
- LICENSE, OPEN_SOURCE_CREDITS.md and PROVENANCE.md are unchanged.

## Named local servers

`Settings.local_endpoints` holds validated `{id, name, url, enabled}` records.
IDs are unique stable lowercase slugs. URLs must be HTTP(S) without userinfo,
query parameters or fragments. Secrets/extra fields are rejected. These servers
are anonymous; authenticated servers retain the existing custom endpoint
credential adapter. No credentials from another provider are borrowed.

`GET /api/local-endpoints/models` is protected by the existing admin guard.
Enabled servers are discovered independently. Failures are returned separately
from working catalogs. Discovery and chat use the backend's network access.
`local:<id>:<exact-model>` identities prevent collisions across servers.
Missing, disabled or malformed local selections never default to OpenRouter.

The local adapter reuses custom-provider non-streaming behavior and adds
OpenAI-compatible streaming. It publishes only visible content, reported usage
and finish reasons. It excludes `reasoning_content`, closes on cancellation,
and preserves canonical timeout events. Interrupted streams with no completion
marker are failures rather than invented successful completions.

## Moderator extension contract

`RunRegistry(..., moderator_runner=run_moderator)` is the only added execution
seam. The callable retains `run_moderator`'s parameters and returns a boolean
completion outcome. Input assembly stays in `assemble_moderator_input`; the
registry owns fan-in, sequencing, journal, persistence, run deadlines and
cancellation. A future executor must publish through `create_event`, not a
separate stream or shared transcript.

Default behavior is the existing single-call synthesis. No tool registry,
search, manuals, VIN parsing, autonomous verification, model bakeoff, training,
model download, five-worker cockpit or new dependency is added.

## Next mission

Connect the user's already-running FOB llama.cpp endpoints, discover actual
model IDs, select three seats and verify real inference end-to-end. Compatibility
fixtures validate transport and app behavior, not live model quality, exact FOB
addresses, capability claims or a measured model ranking.
