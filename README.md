# Shade Crew AI

A personal, local-first multi-model mechanic and repair console.

**Gearhead | Crew Chief | Grease Monkey** — independent answers, then a wider
center seat synthesizes the two visible outputs. Workers never see each other.
All three seats can research a durable named Case with read-only tools. Crew Chief
receives both mechanic answers and work trails, can independently check them, and
gives the final ruling. Agreement is not proof.
Search snippets and model assessments have limits; exact-machine evidence may remain unresolved.

## Run the browser console

Use the existing Python 3.10+ / uv and Node/npm toolchain:

```bash
uv sync --group dev
npm --prefix frontend ci
./start.sh
```

Open http://localhost:5173. Backend: http://localhost:8001. The launcher binds
both servers to loopback. Ctrl+C stops them. Root and the old `/modelmix` URL
both show the cockpit; the Council/Advisor UI is no longer an entry point.
For separate terminals:

```bash
uv run python -m backend.main
npm --prefix frontend run dev -- --host 127.0.0.1
```

Production frontend validation/preview:

```bash
npm --prefix frontend run build
npm --prefix frontend run preview -- --host 127.0.0.1 --port 5173
```

Keep the backend running for preview. Existing `VITE_API_URL` and runtime
`window.__AI_COUNSEL_CONFIG__.apiUrl` overrides remain supported. Internal
`modelmix` routes, seat IDs, storage keys and package identifiers are retained
to avoid a migration in this first pass.

## Connect FOB / llama.cpp

No model download, training or Ollama installation is required. Start your
existing llama.cpp servers separately using your established runtime and models.
The console does not manage their processes or choose which models to run.

1. Settings → Providers → **Local servers (llama.cpp / FOB)**.
2. Add a stable ID (for example `fob-a`), display name (`FOB Gearhead`) and
   API base URL including `/v1` (`http://127.0.0.1:8080/v1`). The URL is relative
   to the backend host, not the browser machine. Use FOB's reachable address
   when the backend runs elsewhere. This example does not assert a live port.
3. Enable the server, then **Save and discover local models**. Discovery uses
   `/models`, and reports failed endpoints separately.
4. Reload the console, select models in all three seats, then enter a repair
   question and Send. Save your chosen seats under Settings → Defaults.

Named local servers are anonymous HTTP(S) endpoints. Their configuration cannot
contain keys or credentials embedded in URLs. For authenticated servers use the
existing **Custom endpoint** provider, which retains its secure credential path.
Cloud providers remain available. No cloud provider is required for local use.

Model IDs are `local:<stable-id>:<exact-server-model-id>`. Identical model names
on two servers remain distinct. Model strings (including colons) are passed
unchanged to their selected server. Missing/disabled local endpoints fail
explicitly; there is no cloud fallback. Keep IDs stable because seat defaults
and historical sessions refer to them. If you move a server to a new model,
rediscover/reselect it rather than assuming an old selection is still valid.

The local adapter sends streaming `/chat/completions` requests, forwards visible
content, reported usage and finish reasons, and excludes `reasoning_content`.
It closes its HTTP stream on cancellation. No model-specific chat template is
installed or overridden. The FOB live integration uses the native one-model router documented below.
Other OpenAI-compatible variants retain deterministic fixture coverage.

## Preserved behavior

- Mix uses two independent workers and one Crew Chief; existing Compare/Solo
  modes remain secondary choices. No five-worker cockpit.
- Each seat keeps its own history across model changes.
- Ordered multiplexed SSE, replay/reconnect, separate Send/Stop controls,
  partial results, guardrails, model selectors and session controls remain.
- Sessions persist as versioned atomic JSON under this checkout's
  `data/modelmix/` (see the persistence implementation for exact files).
- Provider credentials remain outside prompts and ordinary session/settings data.
- Shared legacy backend/provider code is retained where the cockpit depends on
  it. Historical design docs under `docs/modelmix/` remain reference material.

## Cases and crew research

Use the Case strip to create a named repair Case, reopen one, rename it, or
explicitly import a legacy session. Case details accept facts/measurements with
status and provenance. New runs freeze the Case context; later edits do not
rewrite history. Existing session files stay readable and untouched.

Each Case lives in `data/modelmix/cases/<id>/case.json`, using the existing atomic
JSON persistence. It contains records, snapshots, conversations, model identities,
research/evidence and final rulings. Attachments are hash-addressed shared objects;
only authorized plain-text resources can be read in this pass.

Gearhead and Grease Monkey independently choose read-only research actions while
finite time/output budgets remain. Crew Chief gets both work trails, can salvage
sources without accepting conclusions, and can re-check independently with a
broader allowance. Tools: free public Bing search, frozen Case read, authorized
text-resource read, and work read. There is no normal three-search limit.

Defaults: each mechanic 600 seconds / 64,000 generated characters; Crew Chief
900 seconds / 96,000 characters; whole run 2,400 seconds. Reported-token thresholds
and prompt-size budgets also apply; 75% of seat time/output is reserved for
research, leaving room for the final answer. Emergency action ceilings 128/256
are failsafes. Model usage adds cost for existing cloud providers; local use needs
no paid API. Queries can leave the device; avoid private data in public research.

Research records and source findings stay in expandable seat details. Malformed
control output, failed research and ambiguous findings remain unresolved/partial.
Only an explicit acceptance of a completed Chief's structured proposal updates
Case records. Measurements and official verification cannot be invented through
promotion; unsupported conclusions never become verified facts automatically.

See [Cases and research](docs/cases-and-research.md) for schema, APIs, budgets,
compatibility and limits. [Pass 1 verification](docs/crew-chief-verification.md)
records the earlier framework. Internal `session_id` remains the Case transport ID.

## Validation

```bash
uv run pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

No dependency upgrades are part of this pass. `npm ci` currently reports three
inherited advisories; consult the mission report for exact observed validation
results and limits.

## Provenance and license

Bootstrapped from ModelMix commit `8050e61e6bb0e550260ccdb3f6323c55bf0145ad`.
Shade Crew baseline: `d7adbb8246678302adfb6457b75272e348b88766`.
See [PROVENANCE.md](PROVENANCE.md), [LICENSE](LICENSE) and
[OPEN_SOURCE_CREDITS.md](OPEN_SOURCE_CREDITS.md). Those records are preserved.

## FOB live inference profile

The verified FOB configuration uses llama.cpp's native router, **one model
resident at a time**. Simultaneous Qwen3.8 + Qwen3.6 residency loaded, but failed
at generation with GPU command-submission memory exhaustion/device loss.

```bash
# Terminal 1 — existing GGUFs, pinned Vulkan b11228 runtime
./scripts/start-fob-models.sh

# Terminal 2 — local queue/load/generation needs a longer bounded deadline
SHADE_CREW_SEAT_TIMEOUT_SECONDS=600 SHADE_CREW_RUN_TIMEOUT_SECONDS=1200 ./start.sh
```

Configure one enabled local endpoint with ID `fob`, name `FOB llama.cpp`, URL
`http://127.0.0.1:18081/v1`. Pick `qwen38-uncensored-27b` for Gearhead,
`qwen36-heretic-35b` for Grease Monkey and Crew Chief. The router unloads A before
loading B; Crew Chief then reuses B. No separate manager or background service.

Local requests sharing a URL now serialize across the complete HTTP stream.
Different URLs still run independently. This resource queue does not transmit
answers between workers. A queued request keeps the endpoint configuration it
was submitted with; use Stop before reconfiguring an in-flight run. Serialization
is process-local: use the normal single backend process, not multiple backend
workers or separate clients issuing model switches during a run.

Deadlines include queueing, loading and generation. Default direct backend bounds
remain 300 seconds per seat / 600 per run for the legacy executor. Case runs use the documented 600/900/2,400-second research budgets. The explicit FOB launch settings above
are finite; values outside 1–3600 seconds or non-numbers fail startup. Cancellation
grace remains five seconds. The native model preset caps output at 1536 tokens;
this is a ceiling, not a completion guarantee. See `docs/fob-live-inference.md`
for observed load/speed/memory evidence and real limitations.
