# Shade Crew AI

A personal, local-first multi-model mechanic and repair console.

**Mechanic A | Moderator | Mechanic B** — independent answers, then a wider
center seat synthesizes the two visible outputs. Workers never see each other.
The Moderator currently makes one model call. Tool/search/manual/VIN verification
is future work; current answers are not independently verified by this app.

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
2. Add a stable ID (for example `fob-a`), display name (`FOB Mechanic A`) and
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
installed or overridden. Compatibility is covered with deterministic
OpenAI-compatible fixtures; live FOB models are the next integration mission.

## Preserved behavior

- Mix uses two independent workers and one Moderator; existing Compare/Solo
  modes remain secondary choices. No five-worker cockpit.
- Each seat keeps its own history across model changes.
- Ordered multiplexed SSE, replay/reconnect, separate Send/Stop controls,
  partial results, guardrails, model selectors and session controls remain.
- Sessions persist as versioned atomic JSON under this checkout's
  `data/modelmix/` (see the persistence implementation for exact files).
- Provider credentials remain outside prompts and ordinary session/settings data.
- Shared legacy backend/provider code is retained where the cockpit depends on
  it. Historical design docs under `docs/modelmix/` remain reference material.

## Future Moderator boundary

`RunRegistry(moderator_runner=...)` in `backend/modelmix/registry.py` accepts a
replacement executor with the current `run_moderator` signature. It receives
bounded visible worker input, the chosen provider, and the canonical event
factory. Registry ownership of timeouts, cancellation, event sequencing and
persistence stays intact. The default executor is still `run_moderator`.

Do not implement tool authority by putting worker outputs into worker histories
or creating a second competing stream. See `docs/shade-crew-first-pass.md`.

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
