# ModelMix Provider Capability Matrix

**Mission 043 (foundational domain documentation).** This document is a live,
code-sourced capability matrix for every provider currently in
`backend/providers/`, plus the shared `base.py` provider contract and
`temperature.py` compatibility rules. It states what the code actually
implements and reports, and it explicitly marks what is **not** implemented.
Aligned with Punch Board item **12 = SATISFIED**.

> Crossing the line on telemetry honesty: usage values shown are whatever the
> provider actually returned (`usage` / `usageMetadata`), or absent. Costs,
> token counts, plans, and free-ness are only labeled where the provider
> actually supplies them, and never invented.

---

## 1. The provider contract (`providers/base.py`)

`LLMProvider` (abstract, `base.py:20`) requires every provider to implement:

- `async query(model_id, messages, timeout=120.0, temperature=0.7)` →
  `{"content": ...} | {"error": True, "error_message": ...}` (`base.py:23-36`).
- `async get_models()` → list of model dicts with at least `id`, `name`
  (`base.py:54-62`).
- `async validate_key(api_key)` → `{"success": bool, "message": str}`
  (`base.py:64-75`).

Optional:

- `supports_streaming` property — **default `False`** for every provider unless
  overridden (`base.py:38-41`).
- `stream_query(...)` — raises `NotImplementedError` by default; callers must
  capability-check with `supports_streaming` first (`base.py:43-52`).

`ProviderStreamEvent` (`base.py:8-17`) is the provider-neutral streaming event:
`type` ∈ `{"text_delta","completed","error"}`, plus optional `delta`, `result`,
`finish_reason`, `usage`, `error_message`.

**Who streams:** the matrix below shows exactly one provider (`openai-oauth`)
sets `supports_streaming=True`. All others are non-streaming and go through the
`query` path in the orchestrator (`orchestrator.py:111-128`).

---

## 2. Prefix scheme and temperature rules (`providers/temperature.py`)

The model id prefix (the part before the first `:`) identifies the provider.
`INTERNAL_PROVIDER_PREFIXES` (`temperature.py:8-24`) lists every recognized
prefix: `anthropic, custom, deepseek, github-copilot, google, groq, mistral,
nvidia, ollama, openai, openai-oauth, opencode-go, opencode-zen, openrouter,
xai-oauth`.

Temperature is **omitted** (provider default used) for models the providers
cannot accept it on (`should_omit_temperature`, `temperature.py:63-75`):

- `openai`: `gpt-5*` and reasoning models `o1/o3/o4*`
  (`is_openai_fixed_temperature_model`, `temperature.py:47-53`).
- `anthropic`: `claude-{opus,sonnet,haiku}-[4-9]*`
  (`is_anthropic_temperature_deprecated_model`, `temperature.py:56-60`).
- `custom` and `openrouter`: omit if either rule matches (they may host either
  family) (`temperature.py:70-74`).

`add_temperature_if_supported` mutates a payload to include `temperature` only
when allowed (`temperature.py:78-88`).

---

## 3. Capability matrix

Legend: `usage` = returns provider-reported usage in `query` result; `pricing` =
parses/dollars pricing into `get_models`; `__free` = derives an `is_free` flag;
`stream` = real `supports_streaming=True`; `auth` = key type.

| Provider | file | usage in query | pricing | is_free | stream | auth |
|---|---|---|---|---|---|---|
| `openai-oauth` | `openai_oauth.py` | yes (`:106`,`:206`,`:231`) | no | no dollars | **yes** (`:79`) | OAuth (ChatGPT) |
| `openai` | `openai.py` | yes (`:54`) | no | no | no | API key |
| `google` | `google.py` | yes `usageMetadata` (`:63`) | no | no | no | API key |
| `anthropic` | `anthropic.py` | yes (`:63`) | no | no | no | API key |
| `deepseek` | `deepseek.py` | yes (`:47`) | no | no | no | API key |
| `groq` | `groq.py` | yes (`:48`) | no | no | no | API key |
| `nvidia` | `nvidia.py` | yes (`:48`) | no | no | no | API key |
| `mistral` | `mistral.py` | yes (`:47`) | no | no | no | API key |
| `openrouter` | `openrouter.py` | yes | **yes** (`:54-58`) | **derived** free (`:58`,`:64`) | no | API key |
| `ollama` | `ollama.py` | yes | no | yes always (`:43`) | no | keyless/local |
| `opencode` | `opencode.py` | yes (`:197`,`:204`,`:221`) | no | yes from listing (`:336`) | no | Bearer/x-api-key |
| `github-copilot` | `github_copilot.py` | yes (`:235`) | no | **yes from billing** | no | OAuth |
| `xai-oauth` | `xai_oauth.py` | yes (`:63`) | no | no | no | OAuth |
| `custom` | `custom_openai.py` | yes (`:64`) | no | no | no | optional Bearer (`:37-38`) |

---

## 4. Notes per column

### Provision of `usage`
All providers return provider-reported usage. Two non-standard names:
- `google` reports `usageMetadata` (`google.py:63`).
- `openai-oauth` reads `usage` from HEADER `x-usage-tokens`/event/`completed_result`
  (`openai_oauth.py:206`, `:231`, `:106`).

Sections: the code never synthesizes usage; it forwards exactly what the provider
returned or leaves `usage` unset. Token dollar-cost derivation does not exist for
any provider except `openrouter` (which parses `pricing.prompt/completion`, not
usage, and only at `get_models`/catalog time, `openrouter.py:54-64`).

### Pricing dollars
Only `openrouter` extracts real pricing fields at catalog time
(`openrouter.py:54-58`). It derives `is_free = prompt_price == 0 and
completion_price == 0` and adds `"is_free": is_free` to the model dict
(`openrouter.py:58`, `:64`). No other provider returns dollar pricing.
**Mission 044**: OpenRouter per-token pricing is no longer discarded —
`get_models()` returns `prompt_price_per_token`/`completion_price_per_token`
and caches it, so OpenRouter-routed seats get a real `cost_usd` on their
completion events when real usage tokens exist; all other cases leave cost
absent.

### is_free
Three distinct, honest derivations exist:
- `openrouter`: derived from actual pricing ($0 = free, `openrouter.py:58`).
- `ollama`: local + keyless → always `{"is_free": True}` (`ollama.py:43`).
- `opencode`: from the model listing's own `is_free` field
  (`opencode.py:336`).
- `github-copilot`: from real account billing (`is_free_plan` flag on the
  account, `github_copilot.py:243`, `:147`, `:154`; subsidy-free `· Free`
  display at `:132-134`), plus strict Free-plan allow/blocklists
  (`_copilot_model_allowed`, `github_copilot.py:75-88`).

No provider *fabricates* a paid/free status it lacks.

### Streaming
`openai-oauth` is the **only** provider with real streaming: `supports_streaming`
returning `True`, a genuine async `stream_query` parsing SSE/Deltas, and a
non-streaming `query` that arrays the stream plus usage/finish_reason
(`openai_oauth.py:79`, `:96-107` stream-driven `query`, `:206-207`
`finish_reason = resp.get("status")`). All other providers default to
`supports_streaming=False` and `stream_query` → `NotImplementedError`
(`base.py:38-51`).

### Authentication
- **OAuth**: `openai-oauth` (ChatGPT), `github-copilot`, `xai-oauth` — these
  resolve a stored OAuth credential via `get_valid_access_token`
  (`github_copilot.py`, `xai_oauth.py`).
- **API key**: `openai`, `google`, `anthropic`, `deepseek`, `groq`, `nvidia`,
  `mistral`, `openrouter`.
- **Keyless/local**: `ollama` (`validate_key` at `ollama.py:49`; local server).
- **Operation-mode composites**: `custom` is a remote user endpoint with
  optional Bearer only when a key is present and `validate_connection` +
  `validate_key` delegation (`custom_openai.py:121-163`, `:37-38`).

### Model catalog / discovery
- `openrouter` catalogs models from the remote listing including pricing
  (`openrouter.py:19`, `:54-64`).
- `groq` maps the provider `context_window` to `context_length`
  (`groq.py:81`).
- Several providers seed a static/hardcoded fallback list when the remote is
  unavailable (e.g. `deepseek.py:52` seeds `deepseek-chat`/`deepseek-reasoner`;
  `anthropic.py:68`; `github_copilot.py:23-24`; `xai_oauth` seeds; `openai-oauth`
  filters its static seeds by `CHATGPT_CODEX_UNSUPPORTED`,
  `openai_oauth.py:236-249`).

### Retry / resilience
`opencode` has explicit retry handling for HTTP/429/timeout/protocol errors at
the transport layer (`opencode.py`, response-code-driven retry). This is a
transport-level concern and is **not** part of the run state machine (see
`run-state-machine.md` — run-level terminal statuses are set by
`registry.py`/`orchestrator.py`, independent of provider transport retries).

---

## 5. Capabilities that are NOT implemented anywhere

The matrix is only as honest as its negatives. As of this writing **no
provider** implements:

- provider-reported dollar cost per query (only `openrouter` sets catalog
  pricing, which is not, and is explicitly not claimed to be, per-request usage
  cost);
- vision/file input in the alpha run path;
- tool/function-call consumption in the alpha run path;
- guaranteed streaming (only `openai-oauth` streams; a caller must treat every
  other provider as non-streaming);
- Android/Tauri surfaces (already listed as alpha non-goals in `AGENTS.md`).

These are not claims about what is possible; they are statements that the
current code does not implement them, so the UI must not advertise them as if
they exist.

---

## 6. Telemetry labels (per AGENTS.md)

- Provider-reported token usage → authoritative, and may be labeled as such
  **only** when `usage`/`usageMetadata` was actually returned.
- `openrouter` catalog pricing → authoritative provider data, but it is catalog
  price, **not** per-run cost; do not present it as your bill.
- `is_free`, `· Free` labels → derive from real provider free-ness/billing as
  above; never guessed from absence of data.
- Anything unknown (e.g. a provider that returned no usage) stays **unknown**;
  do not fold rate limits, tokens, billing, and quotas into one fake normalized
  percentage.