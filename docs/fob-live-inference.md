# FOB live local inference

Use the native llama.cpp router with one loaded model. Do not keep both large
Qwen models resident on this FOB configuration: they loaded simultaneously but
actual generation failed with `Not enough memory for command submission` and
`ErrorDeviceLost`. This was a real failure, not a theoretical capacity estimate.

## Exact existing runtime and model identity

Runtime: `/home/wes/runtime/llama.cpp/releases/b11228/llama-server`, observed
version `0.5.0-dev (build 11228, commit 4364bf723)`.
Device: `Vulkan0: AMD Radeon 780M Graphics (RADV PHOENIX)`.
The native embedded Jinja templates are preserved; thinking is off. No projector
is loaded, no model downloaded, and no speculative/MTP decoding is enabled.

| Alias | Existing file | SHA-256 verified against the existing manifest |
|---|---|---|
| `qwen38-uncensored-27b` | `/home/wes/models/qwen38-uncensored-27b/Qwen3.8-27B-Uncensored-FP8.Q4_K_M.gguf` | `73e5af89b797de4d6f3b8048744fcda364c1530a8a17c2d470315614c51bb95a` |
| `qwen36-heretic-35b` | `/home/wes/models/qwen36-heretic-35b/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-Q4_K_M.gguf` | `fc89d92377b27fe0f80eb683a5105d0921234c24f7c1d70ecc2356ddf994d781` |

These product aliases name exact files. The filename containing MTP does not
mean this mission enables speculative decoding.

## Start and connect

From this checkout, terminal 1:

```bash
./scripts/start-fob-models.sh
```

The script checks the exact existing executable/files, then executes:

```bash
/home/wes/runtime/llama.cpp/releases/b11228/llama-server \
  --models-preset "$PWD/config/fob-models.ini" \
  --models-max 1 --host 127.0.0.1 --port 18081 \
  --no-webui --metrics --log-verbosity 4
```

The launcher resolves the preset relative to itself, so launching from another
directory still uses the correct file. No service, watcher, container or custom
resource manager is installed. Router children are the same pinned executable.
Ctrl+C in terminal 1 stops the router and its children.

Terminal 2:

```bash
SHADE_CREW_SEAT_TIMEOUT_SECONDS=600 SHADE_CREW_RUN_TIMEOUT_SECONDS=1200 ./start.sh
```

The explicit deadlines include queueing, loading and generation. A real attempt
with defaults completed A at approximately 293 seconds, then B reached its
300-second deadline while loading. Do not interpret a shared-server queued seat's
RUNNING label as proof it is currently generating tokens.

Both timeout environment values must be finite and within 1–3600 seconds. Defaults
remain 300/600 if omitted; cancellation grace remains five seconds. For separate
backend/frontend terminals use the same timeout variables with
`uv run python -m backend.main`, then the normal frontend command from README.

Settings → Providers → Local servers: configure one enabled endpoint:

```json
{
  "id": "fob",
  "name": "FOB llama.cpp (one model resident)",
  "url": "http://127.0.0.1:18081/v1",
  "enabled": true
}
```

Save/discover, reload, and explicitly select:

- Mechanic A: `local:fob:qwen38-uncensored-27b`
- Mechanic B: `local:fob:qwen36-heretic-35b`
- Moderator: `local:fob:qwen36-heretic-35b`

Set Behavior temperature to `0.3`, leave Moderator guidance empty, and save seat
defaults if desired. The native server presets use 8192 context, one slot,
1536 output ceiling, F16 K/V, seed42, top-p0.95/top-k20/min-p0, repetition1 and
presence/frequency0. The browser's saved temperature takes precedence over the
server default. These are a practical integration profile, not measured winners.

## Resource and privacy boundary

Local requests to the same normalized configured URL share one in-process lock
through HTTP completion/closure. B can be scheduled without seeing A's answer:
its HTTP request waits until A's stream closes, then the router unloads A and
loads B. Moderator starts only after both worker outcomes exist and reuses B.
Different endpoint URLs still execute independently.

A submitted request snapshots endpoint configuration. A settings edit affects
later submissions rather than moving queued calls onto a differently locked
server. Use Stop before changing a running setup. Closing/cancelling a stream
releases the lock; cancelling a queued request does not start or switch a model.

Use the normal single backend process. Multiple backend processes or external
clients switching this router bypass the Python lock. Keep one endpoint URL for
this router rather than configuring localhost/127.0.0.1 aliases separately.
The server is anonymous and loopback-bound. Authenticated servers retain the
existing Custom endpoint credential path; no API key is borrowed from another
provider. Model IDs are sent exactly and reported streaming model mismatches
fail before their content is published. A server omitting `model` cannot supply
that extra identity check; the verified native router supplies it and rejects
unknown model names. No cloud fallback is added.

## Capacity observations and limits

FOB exposed about 57 GiB system RAM, 4 GiB dedicated VRAM and 28.8 GiB GTT at
inspection. Those GPU allocations share system resources; do not add counters
as independent physical RAM. RSS alone does not represent Vulkan's model memory.

Dual residency took approximately 49 GiB used, 8.5 GiB available, 2.7 GiB swap,
and exhausted GPU command submission during the test. Stop both failed servers
before restarting the one-model router; this recovered available memory.

Native single-model logs showed:

- Qwen3.8: all 66/66 layers offloaded; 15088.31 MiB Vulkan model buffer,
  512 MiB KV, 149.62 MiB recurrent state, about140 MiB compute buffer.
- Qwen3.6: all 42/42 layers offloaded; 19966.65 MiB Vulkan model buffer,
  160 MiB KV, 62.81 MiB recurrent state, about81 MiB compute buffer.

Initial standalone process-to-health observations were 16.44s for Qwen3.8 and
24.81s for Qwen3.6; server logs reported model-ready14.61s/24.68s. Native-router
single-model load observations were roughly15s/19s. Loading time includes
warmup; cached disk state and other workload affect it. Old swapped pages from
the failed dual attempt can remain in swap after pressure is gone.

Model answers are captured unchanged. This integration mission does not validate
mechanical correctness, source grounding, VIN/manual knowledge or model quality.

## Successful acceptance run — 2026-10-14

Session `7cac5905-deee-458c-8f3c-7193881d1452`, run
`430c7b61-3431-432c-a0ff-f39003478504` completed in **343.34 seconds** using the
exact user-supplied no-crank prompt. No response was manually changed.

| Seat | Actual alias | Native load to ready | Generated tokens | Native generation speed | Finish |
|---|---|---:|---:|---:|---|
| Mechanic A | `qwen38-uncensored-27b` | 15.24s | 972 | 3.83 tok/s | stop |
| Mechanic B | `qwen36-heretic-35b` | 17.80s | 450 | 21.97 tok/s | stop |
| Moderator | `qwen36-heretic-35b` | Reused B | 621 | 21.56 tok/s | stop |

Load durations are native child process clocks to model-ready, including warmup,
not a promise for later cold loads. Generation rates exclude loading and prompt
processing. A's seat elapsed about270.5s; B's elapsed about309.6s includes waiting
behind A. Moderator elapsed about33.7s including prompt processing. These are
observations from one integration run, not a model ranking.

The two actual worker HTTP payloads each contained exactly the original prompt
as a single user message. Moderator's actual payload contained both complete,
unchanged visible answers, after both workers completed. Three exact requested
model aliases reached the one native router. No cloud provider was called.
All 2048 persisted event sequence numbers were contiguous; all seats emitted
streaming deltas and provider-reported token usage.

Resource samples during that run retained at least **23.43 GiB MemAvailable**;
peak driver VRAM+GTT counters were about **21.19 GiB combined**. Those are driver
allocations and system availability, not independent memory pools. Both model
files were hashed against their existing manifests. Router catalog/child argv and
native logs trace each alias to the exact file, Vulkan device and all-layer
GPU offload. Catalog after the switch showed only Qwen3.6 loaded.

Browser active reload resumed the existing run with Stop enabled. After normal
completion, all three rendered transcripts matched before/after browser reload,
and again after backend restart. Persisted response text was exported unchanged.
A separate real Qwen3.6 request was cancelled after its first visible delta:
terminal `run_cancelled`, partial output retained, native slot idle, about1.07s
including the short generation. The waiting worker did not trigger a model switch.

For evidence capture only, a temporary local harness logged the three outbound
HTTP request bodies without changing payloads or responses. The final running
backend was restarted normally without that harness and restored the same answers.
The app's local settings/session files remain ignored by Git. No keys or model
binaries were committed.

## Validation and changes

- Focused backend coverage: 51 passed before the last parameterized snapshot
  variant; independent local/timeout review then observed33 passing tests.
- Full backend: `uv run pytest backend/tests -q` — **567 passed**, 26.74s. It ran
  from an identical isolated source copy so live data was not touched.
- Frontend: `npm test` — **234 passed**, 21 files.
- `npm run lint`, `npm run build` — exit0; production build363 modules.
- Changed backend files passed Ruff; native launcher passed `bash -n`;
  `git diff --check` was clean.
- Snapshot queue race and model-mismatch tests failed before their fixes. Tests
  cover same-URL serialization, different-URL independence, running/waiting
  cancellation, queued stream/query configuration changes and bounded deadlines.

Material changes are the local provider queue/identity checks, a configuration
snapshot helper reused by the existing custom adapter, explicit timeout environment
bounds, focused regression tests, native model INI/launcher, README and this guide.
No frontend design, orchestration rewrite, model download, dependency upgrade,
verification tool loop, training or five-worker cockpit was introduced.

The branch is suitable for merging as the **live local inference plumbing
milestone**. Main was deliberately left at its pristine baseline. Diagnostic
quality and evidence verification remain separate future work. Existing npm
transitive advisories from the first pass remain unresolved.
