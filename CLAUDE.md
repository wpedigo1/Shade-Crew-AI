# Claude Code — ModelMix

@AGENTS.md

`AGENTS.md` is the canonical ModelMix project instruction file.

Follow it as the source of truth for:

* product architecture;
* Worker A / Moderator / Worker B isolation;
* run and SSE behavior;
* persistence boundaries;
* UI constraints;
* provider behavior;
* telemetry honesty;
* security;
* testing;
* validation;
* scope discipline;
* definition of done.

Do not duplicate or reinterpret those rules here.

## Claude-Specific Working Rules

Before editing:

1. Read `AGENTS.md`.
2. Inspect the relevant implementation and tests.
3. Search the repository for existing working patterns.
4. Trace the affected state/data path before introducing new abstractions.
5. Prefer the smallest change consistent with existing ModelMix architecture.

For routine, well-defined tasks, inspect and proceed without stopping for plan approval.

Ask before implementation only when a material ambiguity, destructive action, security issue, architectural conflict, or major product decision cannot be resolved from the repository and project instructions.

For broad architectural changes, authentication/credential changes, persistence redesign, or major cross-cutting refactors, provide a short implementation plan before editing.

## Repository Behavior

Do not treat previous Claude sessions, mission reports, summaries, commit SHAs, branch names, or PASS statements as proof of current repository state.

Inspect the actual repository.

Do not:

* create a second implementation beside an existing working path;
* replace established ModelMix infrastructure merely because another pattern is stylistically preferable;
* broaden a focused mission into cleanup or redesign;
* resurrect Council/Advisor/debate architecture;
* silently change locked ModelMix decisions.

When project documentation and repository behavior conflict, identify the conflict instead of silently resolving it.

## Validation

Use the repository's actual commands and configuration.

Do not invent test, lint, build, or type-check commands.

Run the narrowest relevant validation first, followed by broader validation justified by the change.

Never report a command as successful unless its successful result was observed.

Before reporting completion, review the final diff for:

* unintended files;
* unrelated refactors;
* accidental formatting churn;
* leaked credentials;
* broken worker isolation;
* duplicated state ownership;
* architectural drift.

## Completion Report

Keep the final report short.

Include:

* what changed;
* files changed;
* validation actually run and results;
* material assumptions;
* unresolved failures or risks.

Never claim external actions or successful state that was not directly verified.