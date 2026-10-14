# ModelMix Privacy and Data Routing

**Mission 043 (foundational domain documentation).** This document describes how
ModelMix stores credentials, routes data between seats, and keeps the Moderator
as the only participant with the full picture — all **as implemented**, cited to
`backend/credentials/*`, `backend/oauth/refresh.py`, and
`backend/modelmix/routes.py`. Aligned with Punch Board item **13 = SATISFIED**.

---

## 1. Credential storage model

Credentials never appear in plaintext in frontend payloads, logs, session
files, or version control. The store is a single facade
(`credentials/store.py:1`) that can back onto **OS keyring** or **an
encrypted-file fallback** depending on environment.

- Preferred mode comes from `settings.credential_storage` (`store.py:29-33`);
  only `"file"` or `"keyring"` are accepted (`store.py:33`).
- **Containers always fall back to file** (`get_effective_mode`,
  `store.py:36-47`), and a keyring preference with no working backend **fails
  closed** to file for recovery reads (`store.py:42-46`).
- Backends live in `file_backend.py` and `keyring_backend.py`; availability is
  probed in `availability.py` (`get_availability`, `store.py:50-70`), including
  container detection.

**Secret identity** is by a stable id, not by wrapping a raw token. `ids.py`
defines the canonical id scheme:

- `KNOWN_SECRET_IDS` (`ids.py:6-24`) — every secret id the app may store.
- `SETTINGS_FIELD_TO_SECRET_ID` (`ids.py:27-42`) — how settings API fields map
  to stored secrets. (Mission 042 removed the now-unused *reverse* map.)
- `ENV_OVERRIDES` (`ids.py:45-60`) — env var names that, when present, override
  a stored secret (used for local development/CI; the env value is read, never
  written back to disk).
- `OAUTH_PROVIDER_IDS` and `OAUTH_SECRET_IDS` (`ids.py:61-63+`) — the OAuth
  provider set (`xai-oauth`, `openai-oauth`, `github-copilot`) and their secret
  ids.

**Read path.** `store.get_secret(id)` reads from the effective backend first and
falls back to an env-var override (`ENV_OVERRIDES`) when present
(`store.py`, `get_secret`). Secrets are exposed to callers as references to
secure storage, not as values that are serialized into the session JSON.

**OAuth gating.** `get_oauth_credential` (`store.py:207-220`) only resolves
credentials whose stored `type == "oauth"`; it refuses to treat an API key as an
OAuth credential.

---

## 2. Settings-API vs credential-store separation

`apply_settings_secret_updates` (`store.py:380-398`) deliberately **routes
settings-API secret fields into the credential store** instead of re-inlining
them into `settings.json`. Consequences:

- The secret value does not land in the settings document.
- `settings.json` keeps only the *reference* (the stored secret id).
- `SETTINGS_FIELD_TO_SECRET_ID` is the mapping used to decide where each
  settings field's secret goes.

`disconnect_all_credentials` (`store.py:257-306`) wipes and disables all stored
credentials (used for sign-out / credential reset). Export/import of secrets is
handled by `export_all_secrets`/`import_secrets` (crypto + reload path) rather
than by copying `settings.json`.

---

## 3. OAuth refresh (single-flight, keep-alive)

`backend/oauth/refresh.py`:

- Refresh tokens are persisted as part of the *stored* credential
  (`tokens_to_stored_credential`), i.e. inside the credential store, keyed by
  provider, and preserving `accountId`.
- Per-provider refresh is implemented for `xai-oauth`, `openai-oauth`,
  `github-copilot`.
- Refresh is **single-flight**: concurrent requests for the same provider
  collide on an `_inflight`/`_lock` guard so only one network refresh happens
  and concurrent callers await the same result.

---

## 4. Session / run data routing (worker isolation)

The durable session uses seat-scoped context, not one shared transcript.

- **Message ownership**: each message has one `seat` and an explicit
  `audience`. Workers store `audience=["worker_a"]` / `["worker_b"]`;
  the Moderator stores `audience=["moderator","user"]`; the shared user prompt
  is `seat="shared"`, `audience=["worker_a","worker_b","moderator"]`
  (`persistence.py:178-182`, validated at `persistence.py:274-289`).
- **History is seat-scoped**: `build_seat_history` in `history.py` returns only
  a given seat's own prior turns (never another worker's), bounded by
  `MAX_SEAT_HISTORY_TURNS = 8`, `MAX_HISTORY_MESSAGE_CHARS = 4_000`,
  `MAX_HISTORY_TOTAL_CHARS = 24_000` (`history.py:7-9`, `:27-66`).
- **Worker isolation at call time**: each worker's message list is only
  `[*histories[seat_id], {"role":"user","content":prompt}]`
  (`orchestrator.py:51-54`) — Worker A never sees Worker B's output, identity,
  or conclusions, and vice versa.

**Moderator fan-in** is the only place both worker outputs appear, and even
then they are **bounded and visible-only**:

- `assemble_moderator_input` (`moderator.py:46-74`) builds the moderator prompt
  from the original prompt plus each worker's *visible* output and *structured*
  failure notes.
- Each worker's visible text is deterministically middle-truncated to
  `MAX_VISIBLE_OUTPUT_CHARS = 100_000` (`moderator.py:14`, `:36-43`); the
  resulting truncation flags are carried in `ModeratorInput.truncation`
  (`moderator.py:67-73`).
- The moderator never receives other workers' identities, rankings, private
  metadata, or credentials.

---

## 5. Reconnect / replay data integrity

Frontend disconnect is **not** a run cancellation. On reconnect the run is
replayed from the last-known `seq` with duplicate suppression, preserving order
and identity (persistence `latest_seq == len(events)` and per-event `seq`/`run_id`
checks at `persistence.py:264-273`; replay journal `restore` at
`journal.py:87-95`, `ReplayUnavailableError` in `journal.py`). This preserves
seat-scoped data and prevents either worker or the moderator from seeing another
seat's stream.

---

## 6. Guardrail override resolution (`backend/modelmix/routes.py`)

Guardrail limits are resolved per request with code defaults when override
fields are absent. `routes.py` resolves `warning_threshold_chars` /
`hard_cap_chars` and falls back to the module defaults
(`guardrails.WARNING_OUTPUT_THRESHOLD_CHARS = 20_000`,
`guardrails.HARD_OUTPUT_CAP_CHARS = 40_000`). These overrides travel down to
`registry._run_phase` → `multiplex_workers` / `run_moderator`
(`registry.py:219-220`, `orchestrator.py:56-65`, `moderator.py`), so caps apply
identically to worker and moderator output.

---

## 7. What is NOT routed anywhere

Per the locked architecture and current implementation:

- No worker-to-worker output, identity, or reasoning is forwarded.
- No hidden chain-of-thought is exposed in any audience.
- No credentials, OAuth tokens, or refresh tokens leave the credential store
  into prompts, session JSON, SSE wire, logs, or frontend payloads.
- No provider status/usage/cost is invented by the telemetry layer; unknowns
  stay unknown (see `provider-capability-matrix.md` §6).

---

## 8. Verification posture

This document is a description of intended-and-observed behavior. It does not
claim security credentials work merely because the routing code exists; the
relevant tests covering store read/write, OAuth gating, and history isolation are
part of the backend suite and were exercised during Mission 043 validation (see
the mission report).