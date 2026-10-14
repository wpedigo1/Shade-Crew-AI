# ModelMix — Project Instructions

## Project

ModelMix is a local-first multi-model application designed to reduce single-model bias and unsupported conclusions.

The default ModelMix workflow is:

```text
Worker A ──┐
           ├──> Moderator ──> Final answer
Worker B ──┘
```

Worker A and Worker B are independent witnesses.

The Moderator is the only participant that receives both worker results and is responsible for evaluating evidence, resolving disagreement, identifying uncertainty, and producing the final synthesis.

Core principle:

**Simple first. Power when requested.**

Do not redesign settled ModelMix architecture unless repository evidence or an explicit task requires reconsideration.

---

## Source of Truth

Before changing code:

1. Read this file.
2. Inspect the relevant implementation and tests.
3. Search for an existing working pattern before inventing a new one.
4. Check applicable ModelMix documentation and current contracts.
5. Prefer observed repository behavior over comments, plans, or previous agent reports.
6. If repository behavior conflicts with authoritative project documentation, report the conflict instead of silently choosing one.

Do not assume a previous mission report, PASS statement, branch name, commit SHA, or agent summary proves the current repository state.

---

## Locked Product Architecture

Unless an explicit approved change says otherwise:

* Default experience is **Worker A | wider Moderator | Worker B**.
* Worker A and Worker B execute independently.
* Workers must not see each other's output, identity, conclusions, or participation.
* Workers must not critique, rank, debate, rebut, or wait for one another.
* Only the Moderator receives worker outputs.
* The Moderator evaluates evidence and disagreement; it does not majority-vote or mechanically concatenate answers.
* No hidden chain-of-thought is required or exposed.
* Context is seat-scoped, not one shared transcript.
* Seat history belongs to the seat rather than the currently selected model.
* Model/provider substitution must never happen silently.
* Transport is **SSE**.
* Streaming uses one multiplexed ordered run feed.
* Events use durable run identity and monotonic sequence ordering.
* Reconnect/replay must preserve ordering and prevent duplicates.
* Moderator output uses the same run/event path rather than a second independent stream.
* Persistence for alpha is **versioned atomic JSON behind a ModelMix-owned interface**.
* Do not introduce SQLite merely because it may be useful later.
* Browser/React is the alpha application surface.
* Tauri 2 desktop packaging comes after browser alpha.
* Android has a separate later UX and is not a literal three-column desktop port.
* Preserve secure credential references; never move plaintext secrets into frontend payloads, logs, session files, prompts, or repository files.
* Telemetry must distinguish authoritative provider data from ModelMix-tracked or estimated values.
* Unknown telemetry remains unknown.
* Do not fake provider status, usage, cost, latency, messages, credentials, or model responses.

---

## Worker Independence — Hard Boundary

For a standard Mix run:

### Worker A may receive

* User prompt.
* Authorized shared context.
* Worker A's own permitted seat history/resources.

### Worker A must not receive

* Worker B output.
* Worker B identity.
* Worker B conclusions.
* Moderator output.
* Ranking or comparison information about other workers.

Worker B follows the same rule symmetrically.

### Moderator may receive

* Original user prompt and authorized context.
* Complete bounded visible Worker A output when available.
* Complete bounded visible Worker B output when available.
* Authorized research/files/tools when the product feature explicitly permits them.

Never forward hidden reasoning, credentials, private provider metadata, or unauthorized context.

**The side models are independent witnesses. The Moderator is the only one who knows the full picture.**

---

## Current Alpha UI Contract

The main ModelMix cockpit uses three persistent conversation surfaces:

```text
Worker A | Moderator | Worker B
```

Requirements:

* Moderator center panel is wider.
* Panels use essentially the full available vertical workspace.
* Each panel scrolls independently.
* Keep permanent chrome sparse.
* Avoid turning the main interface into a telemetry dashboard.
* Advanced information belongs behind secondary controls unless explicitly promoted.

### Send / Stop

Send and Stop are separate fixed adjacent controls.

Idle/composing:

```text
Send: active
Stop: disabled
```

Running:

```text
Send: disabled
Stop: active
```

Never morph Send into Stop at the same cursor position.

---

## Run and Event Integrity

Preserve the existing ordered ModelMix run model.

Important concepts include:

* `run_id`
* seat/actor identity
* monotonic `seq`
* ordered SSE events
* event journal/replay
* reconnect from the last known sequence
* duplicate suppression
* explicit cancellation
* visible partial results
* distinct terminal outcomes

Do not create competing copies of canonical run state without a concrete architectural reason.

A frontend disconnect is not automatically a run cancellation.

Already-produced output should survive cancellation or partial failure when the run model supports it.

Terminal state must honestly distinguish relevant outcomes such as:

* normal completion;
* partial completion;
* user cancellation;
* failure;
* timeout;
* provider/model termination;
* ModelMix hard-cap termination.

---

## Persistence

Persistence belongs behind a ModelMix-owned boundary.

For alpha:

* Use versioned JSON.
* Use atomic writes.
* Persist enough canonical session/run/message state to reconstruct the application after restart.
* Preserve seat/audience/role metadata.
* Preserve completed and partial results.
* Do not rely exclusively on process memory for durable session state.
* Keep persistence implementation replaceable behind its interface.
* Do not migrate to SQLite unless an approved architecture change explicitly requires it.

Do not let persistence introduce cross-seat context leakage.

---

## Providers and Models

ModelMix supports multiple cloud and local providers through normalized provider behavior.

Do not hardcode product behavior around one provider unless the task explicitly concerns that provider.

Preserve exact provider/model identifiers when required.

Do not:

* silently substitute models;
* fabricate capabilities;
* claim usage information a provider did not report;
* assume every provider supports identical streaming, cancellation, limits, tools, files, vision, pricing, or authentication.

Capability-dependent UI must reflect real capability information.

---

## Telemetry and Usage

ModelMix does not bullshit users.

When displaying usage or limits:

* Provider-reported values may be labeled authoritative when they truly are.
* ModelMix-computed values must be labeled tracked or calculated as appropriate.
* Estimates must be labeled estimates.
* Missing data must remain unavailable/unknown.
* Do not turn rate limits, token counts, billing limits, quotas, and estimates into one fake normalized percentage.

Usage warnings, output warnings, and hard output caps are separate controls.

---

## Security

Never expose or commit:

* API keys;
* OAuth tokens;
* refresh tokens;
* passwords;
* private certificates;
* production credentials;
* sensitive connection strings.

Credentials should be references to secure storage, not serialized raw values.

Do not weaken inherited credential protection, authentication, sandboxing, permissions, or local-backend protections as a shortcut.

If a task changes credential storage, authentication, provider authorization, data routing, or security boundaries, inspect the existing implementation carefully before editing.

Do not claim security behavior works merely because the code appears intended to provide it. Verify what can actually be verified.

---

## Repository Change Rules

* Keep changes focused on the requested behavior.
* Reuse existing ModelMix seams and utilities before creating parallel abstractions.
* Follow existing naming, typing, state-management, error-handling, logging, and testing conventions.
* Do not broadly refactor unrelated code.
* Do not reformat unrelated files.
* Do not upgrade dependencies unless the task requires it.
* Do not modify lockfiles unless dependency changes require it.
* Do not change public contracts casually.
* Do not replace working reconnect, replay, streaming, cancellation, credential, or provider paths merely for stylistic consistency.
* Do not resurrect deprecated Council/Advisor/debate architecture in new ModelMix code.
* Do not remove inherited code until ModelMix replacements are covered and runtime dependencies are understood.
* Upstream is a selective reference/fix source, not ModelMix's live product parent.

Prefer the smallest implementation that cleanly satisfies the requested behavior.

---

## Alpha Scope Discipline

Do not pull post-alpha features into an alpha mission unless explicitly approved.

Current alpha non-goals include:

* detachable windows;
* Android;
* Deep Mix;
* five-worker cockpit;
* mandatory compact handoff packets;
* MCP;
* connected-service actions;
* advanced workspace permission systems;
* account-wide quota dashboards;
* SQLite migration;
* formal worker debate;
* autonomous agent planning;
* automatic provider rerouting;
* elaborate personas;
* giant evidence/conflict dashboards.

Future ideas are not current requirements.

---

## Investigation Before Editing

Before modifying relevant code:

1. Inspect applicable instructions.
2. Inspect the implementation involved.
3. Inspect nearby tests.
4. Search for similar existing behavior.
5. Identify the authoritative state/data owner.
6. Trace affected call paths far enough to avoid duplicate state or competing implementations.
7. Determine the smallest consistent change.

Search specifically for existing implementations before creating new ones for:

* run state;
* SSE streaming;
* replay/reconnect;
* cancellation;
* provider resolution;
* model discovery;
* Moderator fan-in;
* seat routing;
* persistence;
* credential references;
* telemetry;
* frontend ModelMix state.

Do not begin with a broad rewrite.

---

## Questions and Ambiguity

Ask for clarification only when ambiguity would materially change the implementation or create meaningful risk.

Examples:

* two plausible interpretations require different product behavior;
* a required product decision is missing;
* the requested change conflicts with locked architecture;
* the change could expose credentials or sensitive data;
* the change could delete or corrupt persisted state;
* the change alters an important public/API contract.

Otherwise:

* use repository evidence;
* choose the least invasive reasonable interpretation;
* state important assumptions;
* proceed.

---

## Testing and Validation

Changed behavior should have appropriate test coverage.

For bug fixes, add regression coverage when practical.

For new ModelMix contracts or state behavior, test both normal and failure paths where relevant.

Validation must use the repository's actual existing commands and tooling. Inspect project configuration instead of inventing command names.

Run:

1. The narrowest relevant tests first.
2. Relevant backend/frontend tests.
3. Existing lint/type-check validation when applicable.
4. The production/frontend build when applicable.
5. Broader validation justified by the scope of the change.

If a validation command fails:

* do not hide it;
* determine whether it appears caused by the change, pre-existing state, or environment when possible;
* report the exact failed command and useful error;
* do not claim the validation passed.

A test is only PASS if its successful result was actually observed.

---

## Definition of Done

A task is complete only when:

1. Requested behavior is implemented.
2. Architectural boundaries remain intact.
3. Worker independence is preserved where applicable.
4. Relevant tests were added or updated when warranted.
5. Required validation was actually run.
6. Observed failures are reported honestly.
7. The diff contains no accidental unrelated work.
8. Secrets or unauthorized context were not introduced.
9. The final report distinguishes completed work from unresolved issues.

---

## Final Report

When implementation work is finished, report concisely:

* what changed;
* important files changed;
* validation actually run and observed results;
* assumptions that materially affected implementation;
* remaining risks, failures, or unresolved issues.

Do not claim:

* pushed;
* merged;
* deployed;
* running;
* saved;
* connected;
* fixed;
* PASS;

unless the relevant result was actually observed.

---

## Task Prompts vs. This File

This file describes permanent ModelMix rules.

Individual mission/task prompts should contain only:

* objective;
* verified starting state/base;
* relevant constraints;
* required behavior;
* boundaries;
* acceptance criteria;
* validation;
* expected deliverable.

Do not add one-off mission requirements to this file.

Do not dump unrelated ModelMix history into task prompts.

**Project instructions describe ModelMix. Mission prompts describe the change.**
