# Persistent Cases and crew-wide research

Current product architecture: **Gearhead | wider Crew Chief | Grease Monkey**.
Internal seat IDs, routes, provider identities, event ordering, replay and cancellation remain stable.

## Local persistence and compatibility

Default local layout:

```text
data/modelmix/
  cases/<case-id>/case.json
  objects/<sha256>
  sessions/<legacy-session-id>.json
```

`case.json` is the single atomic source of truth for metadata, canonical session,
runs, messages, tool activity, evidence and final Chief rulings. This retains the
existing versioned JSON interface and fsync/atomic-replace implementation; no
SQLite or dual-write event store was added. Folder IDs remain stable on rename.
`SHADE_CREW_CASES_DIR` changes the Case root; attachment objects live in its sibling
`objects` directory. Existing `MODELMIX_DATA_DIR` controls the legacy session root.

Attachments are user-supplied, hash-addressed objects, shared across Cases. Uploads
are limited to 8 MiB, fsynced and atomically published before a Case references them.
Objects are hash-checked on read. Tools can read only snapshot-authorized UTF-8
`.txt`, `.md`, `.csv`, `.json`, `.log` resources; binary/PDF metadata can be retained
but there is no PDF/manual parser. No automatic document download. No settings,
provider credentials or credential-store contents are copied into Cases. Users
must avoid placing secrets in prompts, records, attachments or research queries.

Legacy files remain readable and unchanged. An explicit **Import legacy session
as Case** copies terminal conversation history into a new named Case, records
`imported_from`, and is idempotent. Old runs retain their original IDs and records;
pre-Case runs cannot acquire a retrospectively invented Case snapshot. Legacy
sessions cannot receive new runs or be deleted through the compatibility facade.
Unfinished legacy records are not silently rewritten or imported; recovery is a
separate deliberate operation. Terminal legacy replay remains available.

## Schema and provenance

```json
{
  "schema_version": 1,
  "case": {
    "case_id": "stable-uuid", "name": "Truck no crank", "revision": 2,
    "created_at": 0, "updated_at": 0,
    "machine": {"engine": "unknown"},
    "facts": [], "observations": [], "measurements": [], "repair_history": [],
    "attachments": [], "accepted_promotions": [], "imported_from": null
  },
  "session": {
    "session_id": "same-stable-uuid", "created_at": 0, "updated_at": 0,
    "messages": [], "runs": []
  }
}
```

Records have stable `fact_id`, `created_at`, `category`, `subject`, string `value`,
optional `unit`, `status`, and `provenance`:

```json
{
  "category": "measurements", "subject": "Battery voltage", "value": "12.6", "unit": "V",
  "status": "measured",
  "provenance": {"kind": "user_measurement", "reference": "Meter at battery posts",
                 "run_id": null, "source_ids": [], "supporting_fact_ids": []}
}
```

Statuses: `user_reported`, `observed`, `measured`, `verified`,
`crew_chief_accepted`, `disputed`, `unresolved`, `hypothesis`, `rejected`.
Provenance kinds: `user`, `user_measurement`, `direct_observation`,
`official_reference`, `crew_chief`, `model`. Measured records require measurement
provenance; verified records require an explicit official reference. Manual
verified entries are **user attestations**, not proof the app retrieved an official
source. All statuses remain visible; hypotheses/disputes do not silently become facts.
Records are currently appended, not silently overwritten or semantically deduplicated.

## Immutable run input

Run creation atomically freezes the Case ID/name/revision, machine identity,
records and attachment references plus current question and capture time in
`case_snapshot`. Each Case run also retains its exact initial seat histories,
model IDs, controls, execution budgets and input-contract version. Later Case
updates or promotions do not change old snapshots. Tool reads use that frozen
snapshot, not the mutable current Case. A resource added during a run is not
available to that run. Prompt projections are explicitly bounded; paged tools
allow inspection of the underlying frozen data and work.

## Read-only repair toolbox

Case runs use the shared research executor; legacy Pass 1 functions remain for
compatibility/testing. The default browser stream creates a Case if none is
selected. Both mechanics may repeatedly choose:

- `search`: existing free Bing/DDGS search, three snippets per call; no paid fallback.
- `case.read`: page a frozen Case section.
- `attachment.read`: page an authorized text attachment by hash.
- `work.read`: page the seat's own visible activity.

Crew Chief receives both final/partial mechanic answers, their visible work and
terminal conditions. It can page either worker's activity and complete answer
(`work.read`, `section: answer`), salvage evidence, reject interpretations, and
independently re-search. Worker answers are explicitly marked opinions, never
sources of proof. Workers never receive peer work or peer answers. They receive
the same authorized shared Case snapshot plus their own seat history.

Structured actions contain no reasoning field. Only allowlisted actions/arguments,
visible findings and promotion fields are retained. Source text is untrusted data,
not instructions. Verified/contradicted findings require retrieved source identity
and exact quote binding, as in Pass 1. This still depends on model judgments of
source relevance, authority and applicability. Search snippets are incomplete.
Public queries can leave this device; privacy exclusion remains partly model-dependent.

## Resource rails

| Default | Each mechanic | Crew Chief |
|---|---:|---:|
| Seat wall clock, including local queue wait | 600 s | 900 s |
| Cumulative generated visible characters | 64,000 | 96,000 |
| Reported total-token stop threshold, when available | 50,000 | 80,000 |
| Model prompt projection characters | 12,000 | 18,000 |
| Emergency action ceiling | 128 | 256 |

Whole Case run: **1,200 seconds**, which takes precedence over remaining seat time.
Research uses at most 75% of the seat's time/generated-output allocation, reserving
room for the final answer. There is no normal one-round/three-search/three-model-call
limit. The emergency ceiling is a runaway failsafe. Search/read tools have a
15-second async bound; the existing search library has a 10-second socket timeout.
An in-flight synchronous search thread cannot be killed; cancelled results are discarded.

Each tool result is capped at 16,000 logical serialized characters. Paged work
results are nonrecursive references/projections, preventing nested read amplification.
Oversize results are visibly limited/uncitable. Text/Case pages adapt to that limit.
Reported token thresholds stop further generation once reported; they cannot
predict unreported provider tokens. Providers that do not report total tokens
remain unknown. Character streaming limits/timeouts provide universal rails;
nonstreaming providers can only be checked after their bounded response returns.

Environment configuration (validated finite positive values):

- `SHADE_CREW_MECHANIC_SECONDS`, `_OUTPUT_CHARS`, `_REPORTED_TOKENS`, `_CONTEXT_CHARS`, `_EMERGENCY_ACTIONS`.
- `SHADE_CREW_CHIEF_SECONDS`, `_OUTPUT_CHARS`, `_REPORTED_TOKENS`, `_CONTEXT_CHARS`, `_EMERGENCY_ACTIONS`.
- `SHADE_CREW_CASE_RUN_SECONDS`, `SHADE_CREW_RESEARCH_FRACTION`, `SHADE_CREW_TOOL_SECONDS`, `SHADE_CREW_TOOL_RESULT_CHARS`.

The shortened names in each prefix group mean full environment names, for example
`SHADE_CREW_CHIEF_OUTPUT_CHARS`. Defaults are conservative character projections for
the observed resident 8,192-token FOB context, not exact tokenizer guarantees.
All phases use the selected provider's existing streaming path, local queue and
model identity checks. No llama.cpp settings, residency, templates or models changed.

## Durable work, cancellation and promotion

Canonical `research_started`, `tool_started/completed`, `research_usage`,
`research_completed/limited`, `seat_evidence`/`moderator_evidence` and
`moderator_promotion_proposed` events carry the usual run ID, sequence and timestamp.
Tool records retain tool ID/name/arguments/result/error, source IDs/URLs/excerpts,
seat/model, and start/end timestamps. Projection into assistant messages supports
reload and compact UI details without a second state owner. Additional usage and
calculable costs remain separate and count toward the existing per-seat prior-run
spend check. Failed partial final calls retain reported telemetry.

On cancellation or run failure, pending tools are journaled as interrupted before
the terminal run event, including when worker cleanup queues are abandoned. After
backend restart, active Case runs similarly retain interrupted tool records and
terminate as failed with `backend_restart`. Partial answers/work remain inspectable.
Limits never count as successful verification. No hidden chain-of-thought is stored.

Chief may emit structured proposals; **nothing is promoted automatically**. The
user explicitly accepts a saved candidate from a completed Chief ruling. The API
cannot accept a caller-supplied replacement fact. Acceptance is idempotent by
run/candidate ID and records its provenance.

`crew_chief_accepted` requires matching supported snapshot facts, or an actually
verified Chief finding with the exact same quote/source and proposed value in
both claim and quote. Search excerpts cannot create officially verified facts.
`measured`/`verified` promotions require an exact matching measured/verified frozen
record and its provenance. Unresolved/disputed/hypothesis/rejected proposals may
be retained only under those same statuses. A failed/incomplete Chief ruling
cannot promote. Linguistic entailment/applicability still needs human review.

## Validation and limitations

Deterministic tests cover Case create/reopen/multiple runs, status/provenance,
immutable snapshots, attachment deduplication/atomic failure, legacy import,
crew-wide tool recording and isolation, evidence salvage/recheck, promotion guards,
resource exhaustion, cancellation/restart recovery and ordered replay. UI tests
cover Case controls, explicit promotion and live/archive/reload evidence consistency.
A small live single-seat local-model check exercised real `case.read` and reported
a synthetic stored measurement; it is not a diagnosis or model-quality benchmark.

Storage remains single-backend-process atomic JSON, matching alpha architecture;
it is not a multi-process transactional database. Case files grow with their
journal; no compaction, record editing, attachment browser, Case deletion or global
object garbage collection is provided. Generic text resources only; no VIN/manual/
wiring databases, RAG, training, model downloads or paid search were added.
Next: evaluate real crew behavior on a small fixed repair Case set, including
source applicability and promotion accuracy, before adding specialized sources.
