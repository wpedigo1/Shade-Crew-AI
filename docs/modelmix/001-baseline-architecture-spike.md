# ModelMix Mission 001 — Baseline Architecture Spike

Inspection-only mission. No product/orchestration/provider/frontend code was
changed. This document is the only artifact this mission produces.

## 1. Executive Verdict

The inherited codebase (The AI Counsel v0.11.4) is a clean, well-tested
FastAPI + React monolith, but every one of the four critical unknowns
resolves to "not built yet, needs new work" rather than "already exists,
reuse it":

- **No provider does true token-by-token streaming to the caller.** All 14
  provider adapters are request/response (`query()` returns one complete
  dict). One adapter (ChatGPT OAuth) consumes an upstream SSE stream
  internally but still collapses it into a single blocking return before
  `council.py` ever sees it.
- **SSE today carries whole-model-response / stage-progress events, never
  token deltas**, has no heartbeat, no event replay, and no run ID /
  sequence number / seat ID in any event payload. Reconnect is "poll a
  snapshot endpoint every 3s," not stream resumption.
- **Active-run state (`_active_runs`) is a bare, unsynchronized, in-memory,
  process-local Python dict.** Single-process (single Uvicorn worker) is
  not just the safest alpha configuration — it is the only configuration
  the code was written to support.
- **Credentials are plaintext-in-a-permission-protected-file by default**,
  with a real (if best-effort) OS-keyring option and three genuine
  device-code OAuth flows. No encryption at rest in file mode. One real
  gap found: `get_openrouter_api_key()` bypasses the disconnect/env-ignore
  guarantee that every other provider correctly honors.

None of this blocks ModelMix. It means Mission 002 is squarely a
**provider streaming interface + SSE event schema** problem, built as new
ModelMix-owned modules that wrap the existing (working, tested) provider
and orchestration code rather than replacing it.

## 2. Repository Baseline

- **Branch (this session):** `claude/modelmix-baseline-architecture-j6vi88`
  (harness-assigned working branch for this mission).
- **HEAD commit:** `64541716352edac7afede90e7a5b36e3c44dee76` — `chore: release v0.11.4` (2026-08-13).
- **Working tree:** clean at mission start (`git status` → nothing to commit).
- **Origin remote:** `https://github.com/wpedigo1/ModelMix` (fork). No
  separate `upstream` git remote is configured; `jacob-bd/the-ai-counsel`
  is referenced only in README/CHANGELOG links (e.g. PR credit links to
  `github.com/jacob-bd/the-ai-counsel/pull/20`), confirming that is the
  origin project this fork tracks, but there is no local remote pointing
  at it to diff against.
- **`main` / `origin/main`:** both at the same commit as HEAD
  (`6454171`) — no divergence.
- **`origin/modelmix-foundation`** (referenced as the "expected branch" in
  the mission brief): also at `6454171`, identical to `main`/HEAD — it
  carries no divergent commits, so there is nothing to reconcile or lose
  by working on the harness-assigned branch instead.
- **Application version:** `0.11.4` (`pyproject.toml`, `frontend/package.json`
  both agree; `CHANGELOG.md` top entry matches).
- **Python requirement:** `>=3.10` (`pyproject.toml`); container/dev
  environment actually runs Python 3.11.15 and `uv 0.8.17`.
- **Frontend requirement:** no `engines` field is declared in
  `frontend/package.json` (unconstrained); environment has Node v22.22.2 /
  npm 10.9.7. React 19, Vite 7, FastAPI 0.115+, per README badges and
  `pyproject.toml`.

## 3. Baseline Verification

| Command | Result | Notes |
|---|---|---|
| `uv sync` | PASS | Resolved and installed full dependency set (fastapi, uvicorn, httpx, pydantic, keyring, pytest, ruff, etc.) with no errors. |
| `uv run pytest -q` | **PASS — 438 passed**, 26.07s | Full backend suite (`backend/tests/`, `the_ai_counsel_mcp/tests/`). Zero failures, zero skips reported. |
| `uv run ruff check .` | FAIL (pre-existing) — 56 findings, 22 auto-fixable | Almost entirely `F401` unused imports in test files (e.g. `backend/tests/test_provider_temperature.py`) and `E402` import-order in `the_ai_counsel_mcp/tests/*`. Inherited lint debt, not introduced by this mission, not touching product code paths. |
| `npm install --prefix frontend` | PASS, 7.5s | 300 packages installed. `npm audit` reports 12 pre-existing vulnerabilities (1 low/2 moderate/9 high) in the dependency tree — inherited, not evaluated further (out of scope: "do not upgrade dependencies"). |
| `npm run build` (frontend) | **PASS** | Vite production build succeeded, 427 modules transformed, 3.67s. Emitted chunked JS/CSS bundles normally. |
| `npm run lint` (frontend) | FAIL (pre-existing) — 26 errors, 11 warnings | Real, inherited issues: conditional hook calls in `Stage1.jsx`/`Stage2.jsx` (`react-hooks/rules-of-hooks`), `setState`-in-effect in `StageTimer.jsx`/`DebateView.jsx`, several unused vars, two fast-refresh violations in `components/settings/*.jsx`. None of these were touched or introduced this mission. |
| App launch | Not exercised live (no network-bound smoke test run in this mission) | `start.sh` / Dockerfile both launch a single `uvicorn backend.main:app` process with no `--workers` flag, confirming single-process is the deployed default (see §7). |

**No inherited test/build failures required any fix in this mission** — the
only failing checks are lint findings inherited from upstream, not
functional breakage.

## 4. Provider Streaming Reality

Abstract interface: `backend/providers/base.py:9-22` — `LLMProvider.query(model_id, messages, timeout=120.0, temperature=0.7) -> Dict[str, Any]`, an `@abstractmethod` returning one complete dict (`content`/`error`). No `stream_query`/`AsyncIterator` exists in the contract.

| Provider | True token streaming? | File / function | Notes |
|---|---|---|---|
| OpenAI | **B** — No | `backend/providers/openai.py:19 OpenAIProvider.query` | Blocking `httpx` POST, `response.json()`, no `stream` key. |
| Anthropic | **B** — No | `backend/providers/anthropic.py:19 AnthropicProvider.query` | Same pattern against `/v1/messages`. |
| Google (Gemini) | **B** — No | `backend/providers/google.py:18 GoogleProvider.query` | Calls `:generateContent`, not `:streamGenerateContent`. |
| Groq | **B** — No | `backend/providers/groq.py:18 GroqProvider.query` | Blocking POST, no `stream` key. |
| Mistral | **B** — No | `backend/providers/mistral.py:18 MistralProvider.query` | Blocking POST, no `stream` key. |
| DeepSeek | **B** — No | `backend/providers/deepseek.py:18 DeepSeekProvider.query` | Blocking POST, no `stream` key. |
| NVIDIA (NIM) | **B** — No | `backend/providers/nvidia.py:19 NvidiaProvider.query` | Blocking POST, no `stream` key. |
| Custom OpenAI-compatible | **B** — No | `backend/providers/custom_openai.py:22 CustomOpenAIProvider.query` | Blocking POST, no `stream` key. |
| GitHub Copilot (OAuth) | **B** — No | `backend/providers/github_copilot.py:196 .query` | Blocking POST, `response.json()`. |
| xAI SuperGrok (OAuth) | **B** — No | `backend/providers/xai_oauth.py:27 .query` | Blocking POST, no `stream` key. |
| OpenRouter | **B** — No | `backend/providers/openrouter.py:11` → `backend/openrouter.py:21 query_model` | No `stream` key; single `response.json()`. Has retry/backoff, not streaming. |
| Ollama | **B** — No | `backend/providers/ollama.py:11` → `backend/ollama_client.py:13 query_model` | Payload explicitly sets **`"stream": False`** (`ollama_client.py:41`) — deliberately opts out of Ollama's native streaming. |
| OpenCode (Zen/Go) | **B** — No | `backend/providers/opencode.py:112 .query` | Chat-completions path sets **`"stream": False`** (line 155); messages-protocol path has no `stream` key. |
| ChatGPT Plus/Pro (Codex Responses API OAuth) | **C** — Uncertain/indirect | `backend/providers/openai_oauth.py:78 .query`, uses `client.stream("POST", ...)` (line 122) + `response.aiter_lines()` (line 142) | The only file using real httpx SSE consumption. Sets `"stream": true`, iterates `output_text.delta` events, but **accumulates them into a list and only returns after the loop ends** (line 165-171) — one complete dict, same shape as every other provider. No partial token is ever exposed to the caller. |

**Why no streaming reaches the frontend today:** `council.py:53-61
get_provider_for_model` routes by prefix to one of the singletons above;
every call site (`council.py:67`, and the `_query_safe` closures at
`council.py:202`/`:352` inside `stage1_collect_responses` /
`stage2_collect_rankings`) does `response = await provider.query(...)` and
only proceeds once the full dict returns. The `asyncio.wait(...,
return_when=FIRST_COMPLETED)` loops parallelize *across models*, not
*within* one model's token stream. `backend/main.py`'s SSE layer confirms
this: every `stage1_progress`/`stage2_progress` event wraps one
fully-completed per-model result (`main.py:819`, `:852`); there is no
`stream=True` forwarding of provider chunks anywhere in `main.py`.

**Cleanest seam for a future `stream_query(...)`:** the abstract base class,
`backend/providers/base.py: LLMProvider`. Add an optional method there
(default implementation wraps `query()` in a single-chunk generator for
providers that don't support real streaming). `openai_oauth.py`'s existing
`client.stream()`/`aiter_lines()` block is nearly ready to be refactored
into a real generator — it already parses delta events, it just
accumulates instead of yielding. The two orchestration call sites to
extend are `council.py:64-70 query_model` and the `_query_safe` closures
in `stage1_collect_responses`/`stage2_collect_rankings` — they already
`yield`-as-they-go per model, so adding a token-level yield path is
additive, not a rewrite of those functions.

## 5. SSE / Run Flow

Three raw (`text/event-stream`, hand-rolled `yield f"data: {json.dumps(...)}\n\n"`) `StreamingResponse` endpoints in `backend/main.py`, none using the installed-but-unused `sse-starlette` package:

| Path | Handler | Purpose |
|---|---|---|
| `POST /api/conversations/{id}/message/stream` | `send_message_stream` (`main.py:730-954`) | 3-stage council run |
| `POST /api/conversations/{id}/message/debate` | `send_debate_message_stream` (`main.py:957-1191`) → `backend/debate.py: run_iterative_debate` | Multi-round iterative debate |
| `POST /api/conversations/{id}/debate/stream` | `start_debate_stream` (`main.py:1226-1357`) → `backend/advisors.py: run_debate` | Advisor persona debate |
| `GET /api/conversations/{id}/progress` | `get_conversation_progress` (`main.py:687-727`) | Non-SSE snapshot poll |

Full path: frontend `fetch(url, {method:'POST', body, signal})` in
`frontend/src/api.js` (`sendMessageStream`/`streamDebateMessage`/
`sendDebateStream`) → backend endpoint builds messages via
`_build_chat_history`/document/search context → `council.py`
`stage1_collect_responses`/`stage2_collect_rankings`/`stage3_synthesize_final`
(or `debate.py`/`advisors.py` equivalents) → each stage's per-model result
is wrapped in an SSE event dict and `yield`ed → `main.py`'s generator also
writes progress into the module-global `_active_runs[conversation_id]`
dict as it goes → on completion, `storage.add_assistant_message`/
`add_advisor_message` persists the final record and `_active_runs.pop(...)`
clears the in-memory entry → frontend's `_consumeSSEStream`
(`api.js:31-58`) parses `data:` lines and dispatches into a large
`switch(eventType)` in `App.jsx` (~lines 990-1541) that mutates React state.

**Event vocabulary** (no shared enum/registry — every producer builds a raw dict literal): council/debate path — `error, search_start, search_complete, stage1_start, stage1_init, stage1_progress, stage1_complete, stage2_start, stage2_init, stage2_progress, stage2_complete, stage3_start, stage3_complete, title_complete, complete`, plus debate-only `round_start, convergence, round_complete, stage4_start, stage4_complete, debate_complete`; advisor path — `advisor_error, advisor_debate_start, advisor_round_start, advisor_response, advisor_round_complete, advisor_tiebreaker_start, advisor_tiebreaker, advisor_verdict_start, advisor_verdict, advisor_complete, advisor_search_start, advisor_search_complete`.

**Granularity:** every event carries a *complete* model response or a
stage-boundary marker — never a token delta. `stage1_progress`'s payload
`item` is only built after `await query_model(...)` fully resolves
(`council.py:202`, `:246-255`); the frontend's `stage1_progress` handler
splices a whole entry into `stage1[]`, never appends partial text.

## 6. Reconnect / Cancellation Reality

**Works today:**
- Frontend cancellation via `AbortController` (`App.jsx:153-154`, wired to
  the "Stop Generation" button and to conversation/navigation switches) →
  aborts the `fetch` → backend's polled `request.is_disconnected()` checks
  (`main.py:767,776,786,866,999,1007,1015`; `council.py:214,364`;
  `debate.py:406,557,700,795`; `advisors.py:299,353,472`) eventually see the
  disconnect and raise `asyncio.CancelledError`.
- On cancellation, still-pending per-model tasks are explicitly
  `.cancel()`ed (`council.py:216-218,262-265,366-368`), which does abort
  in-flight `httpx` calls to providers that hadn't yet responded. Models
  that had *already* completed keep their results.
- Partial-result preservation for the **council/debate** paths:
  `_save_partial_results` (`main.py:227-261`) persists whatever stage
  results were collected so far as a new assistant message with
  `metadata.incomplete = True`.
- Reconnect/progress: `GET /progress` returns a full-snapshot read of
  `_active_runs[conversation_id]` (in-memory, one-run-per-conversation).
  Frontend's `checkForActiveRun` (`App.jsx:485-567`) polls this every 3s on
  mount/navigation and reloads the full conversation from disk once
  `{active:false}` is observed.

**Does not work / does not exist today:**
- **No heartbeat.** No `: ping` comment frames or periodic flush anywhere;
  a slow stage sends nothing until its next real event (docs even warn
  operators to disable proxy buffering because of this).
- **No missed-event replay.** No event log/ring buffer, no `id:`/
  `Last-Event-ID` semantics; a reconnecting client only ever sees "current
  full snapshot," never the sequence of events it missed.
- **No run ID or sequence number in any event payload**, and only the
  advisor path has a seat-like field (`persona_id`) — the council/debate
  path has no seat/lane concept beyond a bare `model` string.
- **Advisor persona debate has no partial-save on cancellation at all**
  (`main.py:1333-1340` only tries to save the title; `advisors.py:420-424`
  just cancels tasks and returns) — a dropped connection mid-advisor-debate
  loses all rounds collected so far.
- **Backend process restart loses everything in flight.** No
  startup/lifespan restore logic; `_active_runs` is wiped, `/progress`
  reports `{active:false}` for what was, from the frontend's perspective, a
  live run.
- Disconnect detection is **polled, not instantaneous** (bounded by ~1s
  `asyncio.wait(timeout=1.0)` loops or stage-boundary checks) — there is no
  immediate interrupt of an in-flight provider call the instant a client
  disconnects.

**Multiplexing verdict (concurrent Worker A / Worker B / Moderator
deltas):** current design **cannot** do this without a rework. It needs,
at minimum: (a) provider adapters that actually stream tokens (§4), (b) a
new SSE event envelope carrying `run_id` + `seat_id`/`role` + a per-seat
sequence number + delta/done distinction, (c) an `_active_runs`-equivalent
structure with an appendable per-seat buffer (today it's "latest full
value," not partial-text accumulation), and (d) either a real replay log
or an explicit resume-from-sequence contract on the progress endpoint.
This is additive new schema/registry work, not a drop-in extension.

## 7. Active Run / Process Model

**Decisive answer: yes, single-process (single Uvicorn worker) is the only
configuration the current code correctly supports.**

- Single global: `_active_runs: Dict[str, Dict[str, Any]] = {}`
  (`main.py:67`), with the code's own comment stating *"process-local —
  only valid for single-worker deployments."* Keyed by `conversation_id`;
  values are plain dicts mutated in place (council/debate mode) or via
  `_update_advisor_run`/`_upsert_advisor_response` (advisor mode,
  `main.py:130-224`). No lock, no external store.
- It is a bare Python dict — not Redis, not a DB row, not
  `multiprocessing.Manager`. Nothing in the codebase lets one process see
  another's `_active_runs`.
- With `--workers > 1` (or multiple replicas behind a load balancer without
  sticky sessions): `GET /progress` polling can land on a different worker
  than the one running the stream, silently returning `{"active": False}`
  for a run that is actually still live — a silent wrong-answer bug, not a
  crash.
- `GET /progress` (`main.py:687-692`) does a bare in-process
  `_active_runs.get(conversation_id)` with **no fallback** to any
  cross-process source — it unconditionally assumes the originating
  process is still alive and serving requests.
- Actual deployment confirms this design assumption: `start.sh` runs `uv
  run python -m backend.main`; the Dockerfile's `CMD` is `uvicorn
  backend.main:app --host 0.0.0.0 --port 8001` with no `--workers` flag
  anywhere in the repo.
- What already survives a restart (persisted separately, via
  `backend/storage.py` JSON-per-conversation): completed stage1/2/3
  results and cost reports (`storage.add_assistant_message`), advisor
  rounds/verdict (`add_advisor_message`), and `incomplete: True` partial
  saves from a graceful cancel (`_save_partial_results`). What is lost on
  an ungraceful crash: everything only in `_active_runs` at that instant —
  in-progress stage/round data not yet flushed to storage.

## 8. Credential / Security Reality

- **Two storage modes**, behind a facade at `backend/credentials/store.py`:
  file (`backend/credentials/file_backend.py`, plaintext
  `data/credentials.json`) and OS keyring
  (`backend/credentials/keyring_backend.py`, service name
  `"the-ai-counsel"`, wraps the `keyring` package).
- **Default mode: file** (`Settings.credential_storage = "file"`,
  `settings.py:205`).
- **Keyring is used only when**: not running in a detected container
  (`is_container_environment()` checks `LLM_COUNCIL_IN_CONTAINER`,
  `/.dockerenv`, or docker/containerd/kubepods in `/proc/1/cgroup` —
  containers **always** force file mode regardless of user setting) **and**
  the user has selected keyring **and** a live `probe_keyring()` call
  succeeds; otherwise it fails closed to file mode.
- **Fallback file location:** `<repo_root>/data/credentials.json`
  (`file_backend.py:14`).
- **Permissions restricted:** yes, best-effort `os.chmod(..., 0o600)` after
  an atomic temp-file + `os.replace` write (`file_backend.py:31-53`); the
  `chmod` failure is swallowed (`except OSError: pass`).
- **No encryption at rest in file mode** — plain `json.dump`, protected
  only by the `0600` permission bit. No `cryptography`/`fernet` import
  anywhere in `backend/credentials/`.
- **Env vars CAN repopulate credentials**, with one documented precedence
  chain and one real gap: `get_secret()` (`store.py:111-136`) checks
  `is_secret_disabled(secret_id)` first (return `None` if disabled), then
  the active backend, then `ENV_OVERRIDES[secret_id]` env var as a last
  resort — **except** `backend/config.py:15-19
  get_openrouter_api_key()`, which does `get_api_key("openrouter") or
  os.getenv("OPENROUTER_API_KEY", "")`, reintroducing the raw env var even
  when the OpenRouter secret has been explicitly disabled/disconnected.
  Every other provider getter (`openai.py`, `anthropic.py`, `google.py`,
  `mistral.py`, `deepseek.py`, `groq.py`, `nvidia.py`, `opencode.py`,
  `custom_openai.py`) correctly honors the disabled-list.
- The disable flag itself: `Settings.disabled_secret_ids`
  (`settings.py:209`), set by `delete_secret()`/"Disconnect" and cleared by
  `set_secret()`/"save a new key" (`store.py:79-162`).
- **Three real OAuth flows** (RFC 8628 device-code, with actual
  token-exchange/refresh HTTP code, not paste-a-token UI): xAI SuperGrok
  (`backend/oauth/xai.py`), ChatGPT Plus/Pro (device+PKCE,
  `backend/oauth/openai_chatgpt.py`), GitHub Copilot (device flow +
  Copilot-token exchange, `backend/oauth/github_copilot.py`), with a
  shared single-flight refresh dispatcher (`backend/oauth/refresh.py`).
- **API-key-only providers:** OpenRouter, OpenAI (direct key, distinct from
  its OAuth id), Anthropic, Google, Mistral, DeepSeek, Groq, NVIDIA,
  OpenCode, custom endpoint, plus search providers (Tavily/Brave/Serper/
  TinyFish). xAI is OAuth-only in code (no plain API-key provider file).
- **Export/backup redaction is bimodal by design:** `GET /api/settings`
  (`build_settings_response`, `settings_payload.py:41-124`) is fully
  redacted (booleans only). `GET /api/settings/export`
  (`build_admin_export`, `settings_payload.py:127-138`) **deliberately
  returns raw plaintext secret values** via `export_all_secrets()` — the
  endpoint's own docstring in `main.py:1642-1645` states this is
  intentional, protected by the admin gate rather than by redaction.
- **Admin endpoints** (`/api/settings/export`, `/import`, `/reset`,
  `/disconnect-all-providers`) are gated by `_require_admin`
  (`main.py:305-330`): if `LLM_COUNCIL_ADMIN_TOKEN` is set, a
  constant-time Bearer-token check wins outright; if unset, both the raw
  TCP peer (`request.client.host`) **and** any forwarded-for/real-IP
  headers must be loopback (`127.0.0.1`/`::1`/`localhost`) — defeating a
  proxy that silently forwards a remote caller's IP in a header while the
  TCP hop itself is loopback. One correctness note: `reset_settings()`
  also wipes stored secrets (contradicting `docs/CREDENTIALS.md`'s claim
  that Reset does not wipe keys), though it does not set
  `disabled_secret_ids`, so env vars can still repopulate keys afterward.
- **Localhost is explicitly checked** against the real TCP peer address,
  not the bind host — `_is_loopback_host()` (`main.py:275-282`).
- **Binding to `0.0.0.0`** only triggers a startup-time log warning
  (`main.py:2437-2450`); it does not change `_require_admin`'s logic —
  admin routes stay loopback-gated regardless of bind host — but every
  *other*, non-admin endpoint has no such check, so `0.0.0.0` binding does
  meaningfully widen the exposed surface for everything else.
- **CORS:** explicit allow-list from `FRONTEND_HOST` env var (empty by
  default) plus a permissive dev regex
  (`https?://(localhost|127.0.0.1|any IPv4 literal|any bracketed
  IPv6):<any port>`), `allow_credentials=True`, `allow_methods=["*"]`,
  `allow_headers=["*"]` (`main.py:337-352`) — broad for LAN/dev use, worth
  flagging as a trust-boundary decision, not a bug.

## 9. Reuse Boundary

| Subsystem | Classification | Exact code location | Reason |
|---|---|---|---|
| Provider adapters | WRAP BEHIND MODELMIX INTERFACE | `backend/providers/*.py` (14 files) | All correct, tested, request/response implementations of `LLMProvider.query()`; ModelMix needs a normalized `stream_query`-capable interface layered on top, not a rewrite. |
| Provider base interface | EXTRACT / REWORK (additive) | `backend/providers/base.py: LLMProvider` | Cleanest seam to add an optional `stream_query` method with a default single-chunk fallback (§4). |
| Model discovery | KEEP MOSTLY AS-IS | `backend/main.py: get_openrouter_models/get_direct_models/get_custom_endpoint_models`, `backend/openrouter.py` | Independent of streaming/orchestration concerns; ModelMix reuses model lists as-is. |
| Preflight | KEEP MOSTLY AS-IS | `backend/model_preflight.py: preflight_models` | Self-contained rate-limit/timeout/retry classification, orthogonal to Worker/Moderator design. |
| Cost/token normalization | KEEP MOSTLY AS-IS | `backend/costs.py: normalize_usage, provider_for_model` | Provider-format-aware usage normalization is reusable verbatim per Worker/Moderator call. |
| Credential storage | KEEP MOSTLY AS-IS | `backend/credentials/store.py`, `file_backend.py`, `keyring_backend.py` | Facade already abstracts file vs. keyring correctly; ModelMix has no reason to touch it (one known gap noted in §8 to flag upstream, not fix here). |
| OAuth | KEEP MOSTLY AS-IS | `backend/oauth/*.py` | Real device-code flows, independent of council orchestration; reusable as-is for any provider ModelMix workers use. |
| Web search | KEEP MOSTLY AS-IS | `backend/search.py` | Self-contained context-fetching step feeding into worker prompts; no coupling to Stage 2/3 concepts. |
| Document extraction | KEEP MOSTLY AS-IS | `backend/documents.py` | Pure text/PDF extraction utility, reusable for worker input context. |
| Conversation persistence | WRAP BEHIND MODELMIX INTERFACE | `backend/storage.py: create_conversation, add_assistant_message, save_conversation` | JSON-per-conversation persistence works for alpha; ModelMix needs a schema for seat-based (Worker A/B/Moderator) results rather than stage1/2/3, so it should call through a thin ModelMix-owned persistence shim rather than reuse the stage-shaped helpers directly. |
| Backend SSE endpoint | EXTRACT / REWORK | `backend/main.py: send_message_stream, send_debate_message_stream` (event_generator closures) | Structure (register run → stream per-item events → persist → clear `_active_runs`) is sound and worth keeping conceptually, but the event vocabulary and `_active_runs` value shape are Council/Advisor-specific (stage1/stage2 arrays, `persona_id`) and don't model Worker A/Worker B/Moderator seats or token deltas (§5, §6). |
| SSE consumer (frontend) | EXTRACT / REWORK | `frontend/src/api.js: _consumeSSEStream`; `frontend/src/App.jsx` event-dispatch switch | The fetch+ReadableStream parsing primitive (`_consumeSSEStream`) is reusable as-is; the giant inline `switch(eventType)` in `App.jsx` is Council/Advisor-shaped and should not gain more `case`s for ModelMix — a new dispatcher is needed. |
| Cancellation logic | KEEP MOSTLY AS-IS (pattern), REWORK (schema) | `main.py`'s `request.is_disconnected()` polling + `except asyncio.CancelledError` + `_save_partial_results` | The mechanism (poll disconnect, cancel pending tasks, save partial, clear active-run) is the right pattern to copy; the partial-save payload shape is stage-specific and needs a seat-based equivalent. |
| Reconnect/progress | REWORK | `main.py: get_conversation_progress`, `_active_runs` | Snapshot-poll pattern is fine for alpha and worth keeping, but the payload shape (`stage1/stage2/stage3` arrays) has no seat concept; needs a Worker A/B/Moderator-shaped snapshot. |
| Stage 1 parallel dispatch | BYPASS (for ModelMix) | `backend/council.py: stage1_collect_responses` | This *is* "independent workers running concurrently" almost conceptually already, but it's wired to Council's anonymization/labeling assumptions (Response A/B/C) that ModelMix's worker-doctrine (workers don't know they're in a council) must not inherit; ModelMix needs its own dispatch function modeled on this one's `asyncio.wait` pattern, not a call into it. |
| Stage 2 ranking | REMOVE LATER (not used) | `backend/council.py: stage2_collect_rankings, calculate_aggregate_rankings` | Explicitly out of scope — "NO Stage 2 peer-ranking/debate in ModelMix." Leave Council's code untouched; ModelMix simply never calls it. |
| Stage 3 Chairman | BYPASS (rename conceptually to Moderator, new module) | `backend/council.py: stage3_synthesize_final` | Conceptually the closest existing analog to "Moderator receives worker outputs and synthesizes," but it's wired to Council's anonymized Stage 1/2 text-building (`build_stage_texts`) and takes rankings as input; ModelMix needs its own moderator-synthesis function that takes two bounded worker outputs directly, modeled on this one's provider-call pattern. |
| Frontend Stage1/Stage2/Stage3 components | BYPASS | `frontend/src/components/Stage1.jsx, Stage2.jsx, Stage3.jsx` | Council-specific UI (anonymized tabs, peer-ranking heatmap, chairman verdict styling) with pre-existing rules-of-hooks bugs (§3); ModelMix's Left/Center/Right layout is a new component tree, not an extension of these. |
| Settings backend | KEEP MOSTLY AS-IS | `backend/settings.py`, `backend/settings_payload.py` | Generic config persistence/redaction pattern; ModelMix can add its own fields following the same `Settings` model + redaction convention. |
| Settings frontend | KEEP MOSTLY AS-IS | `frontend/src/components/Settings.jsx` + `components/settings/*` | Same reasoning; ModelMix settings (if any at alpha) should follow this section pattern, added as a new section rather than edits to existing ones. |
| MCP infrastructure | KEEP MOSTLY AS-IS / UNKNOWN | `the_ai_counsel_mcp/*` | Independent of the HTTP/SSE path entirely (separate `server.py`, `client.py`); whether ModelMix needs an MCP surface at all is not yet decided — flagged UNKNOWN, no evidence either way in this mission. |
| Active-run state | EXTRACT / REWORK | `backend/main.py:67 _active_runs` | Correct mechanism for alpha single-process (§7), but its value schema is Council/Advisor-shaped; ModelMix needs its own registry entry shape (or a parallel dict) for Worker A/B/Moderator seat state — reuse the *pattern* (process-local dict, register/update/pop lifecycle), not the *schema*. |

## 10. ModelMix Integration Seams

Given the monolith structure (§ below) and the reuse map above, the
concrete places to connect new `backend/modelmix/` modules are:

1. **`backend/providers/base.py`** — add the optional `stream_query`
   contract here once ModelMix needs real token streaming; every existing
   provider keeps working unchanged via a default fallback.
2. **New file, e.g. `backend/modelmix/orchestrator.py`** — houses
   worker-dispatch (modeled on `council.py:stage1_collect_responses`'s
   `asyncio.wait` pattern, but without anonymization/labeling) and
   moderator-synthesis (modeled on `council.py:stage3_synthesize_final`'s
   provider-call pattern, but taking two bounded worker outputs directly).
   This is new code, not a rewrite of `council.py`.
3. **New file, e.g. `backend/modelmix/routes.py`**, mounted from
   `backend/main.py`** via `app.include_router(...)`** (main.py does not
   currently use routers — all ~50 routes are flat `@app.get/post` on the
   single `app` object — so this is also the first real seam that would
   need introducing) — new endpoints like `POST
   /api/modelmix/{conversation_id}/run/stream`, reusing
   `_require_admin`/CORS/credential helpers already defined in `main.py`
   but not its `_active_runs` dict or its stage-shaped SSE event builders.
4. **New registry, e.g. `_active_modelmix_runs` dict in the new routes
   module** (or a small class) — copy `_active_runs`'s process-local
   dict-with-lifecycle pattern (register → mutate → pop in `finally`), but
   with a seat-keyed value shape (`{"left": {...}, "center": {...},
   "right": {...}}`) instead of `stage1_responses`/`stage2_responses`
   arrays.
5. **`backend/storage.py`** — either add new
   `add_modelmix_message`-style functions alongside the existing
   `add_assistant_message`/`add_advisor_message`, or (cleaner) a small
   `backend/modelmix/storage.py` shim that calls the existing
   low-level `save_conversation`/file-write primitives with a new message
   shape — do not overload the stage1/2/3 assumptions baked into the
   existing helpers.
6. **`frontend/src/api.js`** — reuse `_consumeSSEStream` as-is for the new
   endpoint; add new wrapper functions alongside
   `sendMessageStream`/`sendDebateStream`, not inside them.
7. **New frontend components** (`LeftWorker.jsx`/`Moderator.jsx`/
   `RightWorker.jsx` or similar) and a **new event-dispatch function** in
   `App.jsx` (or, better, extracted into its own hook rather than added as
   more `case`s to the existing 500-line switch) — see §11 for why growing
   the existing switch further is a coupling risk to avoid.

## 11. Verified Blockers

None of these block starting Mission 002; they are constraints the
implementation must design around:

1. **No provider streams tokens today.** Real per-token SSE delta events
   for ModelMix workers require new provider-layer work first (§4) — this
   is the actual size of "add streaming," not a small wrapper.
2. **`_active_runs` and the SSE event schema have zero run ID / sequence
   number / seat identity.** Multiplexing three concurrent seats
   (Worker A, Worker B, Moderator) needs a new event envelope and a new
   run-registry value shape from day one (§6, §7) — cannot be bolted onto
   the existing stage1/stage2 arrays.
3. **Single-process is a hard constraint for the alpha's in-memory
   reconnect model**, not just a recommendation (§7) — any deployment
   change to multiple Uvicorn workers before a shared-state store exists
   will silently break `/progress` for some fraction of requests.
4. **`get_openrouter_api_key()` credential gap** (§8): disconnecting
   OpenRouter does not actually stop an `OPENROUTER_API_KEY` env var from
   being used, unlike every other provider. Worth a follow-up fix in the
   inherited codebase (out of scope for this mission, which did not modify
   product code), but ModelMix implementers should not assume "disconnect"
   is airtight for OpenRouter specifically.
5. **Advisor debate path has no partial-save on cancellation at all**
   (§6) — not directly a ModelMix blocker (ModelMix doesn't use the
   advisor path), but confirms the cancellation/partial-save pattern is
   not uniformly implemented and must be deliberately built for the new
   Worker/Moderator path rather than assumed "already handled everywhere."

## 12. Assumptions We Can Now Delete

- ~~"Some provider probably already streams tokens (maybe the OpenAI or
  Anthropic SDK path) — we can wrap that."~~ **False.** Zero providers
  expose token deltas to callers; even the one that does real upstream SSE
  (ChatGPT OAuth) collapses it before returning.
- ~~"The SSE event stream might already carry enough identity/sequencing
  metadata to multiplex today."~~ **False.** No run ID, no sequence
  number, no cross-path seat concept (only the advisor path has
  `persona_id`, and even that isn't a general seat abstraction).
- ~~"`_active_runs` might already be reconnect-safe across a backend
  restart or multiple workers."~~ **False on both counts.** It is a bare
  process-local dict with no persistence and no cross-process visibility.
- ~~"Council's Stage 3 Chairman logic is probably directly reusable as the
  Moderator."~~ **Not directly** — it's coupled to Stage 1/2's
  anonymized-response text-building and ranking input; only the
  *provider-call pattern* is reusable, not the function itself.
- ~~"main.py is probably using FastAPI routers/lifespan hooks we can hook
  into."~~ **False.** All ~50 routes are flat on the single `app` object
  with no router split and no startup/lifespan hooks — introducing
  `include_router` for ModelMix's own endpoints is itself new structure,
  not an existing seam to plug into.
- ~~"The credential/OAuth system might need rework to support ModelMix."~~
  **False** — it's provider-agnostic and already correctly separated from
  Council-specific orchestration; ModelMix workers can use it unchanged.

## 13. Recommended Mission 002

**Design and implement `backend/providers/base.py`'s `stream_query`
contract for exactly one already-token-capable-upstream provider (the
ChatGPT OAuth adapter, `backend/providers/openai_oauth.py`, since it
already performs real SSE consumption in `.query()`), refactor that one
adapter to yield deltas instead of accumulating them, and wire a single
new minimal ModelMix endpoint (`POST
/api/modelmix/{conversation_id}/run/stream`, mounted via a new
`backend/modelmix/routes.py` router) that dispatches to exactly two
concurrent workers (no Moderator synthesis yet) and forwards real
token-delta SSE events — each carrying `run_id`, `seat` (`left`/`right`),
and a per-seat sequence number — to a minimal new frontend consumer.**

This is deliberately narrow: it proves the full new stack (provider
streaming → new event schema → new active-run registry shape → new SSE
endpoint → new frontend consumer) end-to-end on the one seam that needs
the least new provider-side work, before Mission 003 adds the Moderator,
the remaining providers, and Council-parity error handling / cancellation
/ partial-save behavior for the new path.
