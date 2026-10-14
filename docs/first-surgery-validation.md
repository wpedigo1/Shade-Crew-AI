# First surgery validation — 2026-10-14

Branch: `shade-crew/first-surgery`.
Base: `d7adbb8246678302adfb6457b75272e348b88766` (verified remote main before work).

## Outcome

Root browser console visibly brands **Shade Crew AI** with **Mechanic A |
Moderator | Mechanic B**. Center panel measured approximately 518 px versus
357 px for each worker at the observed 1280 px viewport. Council navigation
is absent. Both root and existing `/modelmix` paths use the cockpit.

Named local server configuration is entered through Settings → Providers.
Two actual loopback HTTP fixtures advertised the same model name and were
independently discovered, selected and queried through the real backend.
This proves OpenAI-compatible plumbing with fixtures, not live FOB inference.

The Moderator default remains one model call. Its future executor seam uses
canonical event input/output and registry lifecycle ownership. No verification
system or model-selection bakeoff was implemented.

## Validation actually observed

| Command | Result |
|---|---|
| `uv sync --group dev` | Existing locked dependencies installed; no dependency changes |
| `npm --prefix frontend ci` | Existing locked dependencies installed; three inherited advisories |
| `uv run pytest backend/tests/test_modelmix_moderator.py backend/tests/test_modelmix_streaming.py backend/tests/test_provider_temperature.py -q` | Untouched baseline: 44 passed |
| `npm test -- src/components/ModelMixObserver.test.jsx src/configuredModels.test.js` (frontend directory) | Untouched baseline: 9 passed |
| `uv run pytest backend/tests/test_local_openai.py backend/tests/test_modelmix_timeouts.py backend/tests/test_modelmix_moderator.py -q` | 42 passed at that stage |
| `npm --prefix frontend test -- src/modelmixState.test.js src/components/ModelMixCompletion.test.jsx` | 55 passed |
| `MODELMIX_DATA_DIR=../../work/final-test-sessions uv run pytest backend/tests -q` | **560 passed** in 24.16 s |
| `npm --prefix frontend test` | **234 passed**, 21 test files |
| `npm --prefix frontend run lint` | Exit 0, no diagnostics |
| `npm --prefix frontend run build` | Exit 0; Vite 7.3.6, 363 modules, built in 1.53 s |
| `uv run ruff check backend/providers/local_openai.py backend/settings.py backend/modelmix/registry.py backend/tests/test_local_openai.py` | All checks passed |
| `uv run python -m compileall -q backend` | Exit 0 |
| `bash -n start.sh` | Exit 0 |
| `git diff --check` | Clean |

Commands reflect the existing project toolchain. Python 3.10.20 was installed
by uv per the repository's existing `.python-version`. No models were downloaded.
A project packaging warning about skipped legacy console entry points was emitted
by uv; browser startup does not use that optional MCP console entry point.

## Browser and real HTTP observations

Backend launched with `uv run python -m backend.main` and isolated test session
storage. Frontend served its production output using
`npm run preview -- --host 127.0.0.1 --port 5173`.

- Browser title/header: Shade Crew AI. Three named panels; wider Moderator.
- Configured two named local servers from the browser form; Save/discovery
  reported two models. Both exact local identities appeared in selectors.
- Send produced independent worker deltas before Moderator output. Send was
  disabled and Stop enabled during execution; selectors/session changes locked.
- Completed runs returned to enabled Send and disabled Stop.
- Inspected actual fixture request bodies: workers saw only prompt and their
  own history; neither saw the other's text or Moderator text. Moderator received
  both completed visible answers. Exact server model name was preserved.
- Active reload resumed through the existing replay feed and kept Stop enabled.
- Stop cancelled a restored active run, retained partial output, and restored Send.
- New Session cleared history. A subsequent clean three-seat run completed.
- Persisted event sequences were contiguous. Browser did not display fixture
  `reasoning_content`. Completion and cancellation persisted honestly.

## Defects caught and corrected

The initial patch's missing Field import and accidental editor insertion in
Defaults were caught by broader checks and corrected. No unresolved test failure
is being presented as passing.

Runtime verification exposed three **inherited** defects:

1. React's queued state updater left the observer reference stale at SSE EOF,
   allowing a completed run to be overwritten as reconnecting. Reference updates
   now occur synchronously before rendering. Added completion regression fails
   against a clean archive of the exact baseline and passes after the fix.
2. CORS exposed the existing run ID header but omitted the existing session ID
   header, so the browser lost session identity. Both headers are now exposed.
3. Persisted backend status `active` was copied directly into frontend controls
   expecting `running`, disabling Stop on active reload. Hydration now maps it.

Independent review also caught timeout classification in the new local adapter.
Transport timeouts now propagate to existing canonical timeout handlers, with
worker and Moderator regression coverage. Reviewer retested the final fixes.

## Material files

- Browser entry/metadata: `frontend/src/main.jsx`, `frontend/index.html`,
  `frontend/package.json`, `pyproject.toml`.
- Cockpit/controls: `frontend/src/components/ModelMixObserver.jsx` and CSS;
  `frontend/src/modelmixState.js`; branded request errors in `modelmixApi.js`.
- Local configuration: new `frontend/src/components/LocalEndpoints.jsx`,
  `frontend/src/configuredModels.js`, `frontend/src/api.js`.
- Backend configuration/discovery: `backend/settings.py`,
  `backend/settings_payload.py`, `backend/main.py`.
- Exact routing/streaming: `backend/council.py`, new
  `backend/providers/local_openai.py`.
- Moderator seam/identity: `backend/modelmix/registry.py`,
  `backend/modelmix/moderator.py`.
- Focused new/updated tests: local provider/API, Moderator seam, local editor,
  configured sources/catalog, cockpit branding, completion, active hydration,
  existing seat/telemetry/settings expectations.
- Product instructions/docs/launcher: `AGENTS.md`, `CLAUDE.md`, `README.md`,
  `frontend/README.md`, `docs/shade-crew-first-pass.md`, `start.sh`.

## Limits and next mission

No live FOB model was started or evaluated. Real endpoint addresses, model IDs,
performance and provider-specific compatibility remain to be checked by connecting
the existing FOB llama.cpp servers. Local servers here are anonymous; authenticated
servers retain the existing single custom endpoint and secure credential path.
Settings save instructs a console reload to refresh model selectors.

Inherited npm audit: `@humanfs/node` (moderate), `brace-expansion` (high),
`source-map-js` (high), all transitive. Lockfiles and dependency versions are
unchanged. No dependency remediation is claimed.

Canonical timeout messages still report the seat bound even if a shorter
transport timeout triggers; the failure reason is correctly `timeout`.
Historical/shared legacy backend and desktop packaging remain outside this pass.
The original ModelMix repository, LICENSE, OPEN_SOURCE_CREDITS.md and PROVENANCE.md
were not modified. Internal package/API/storage names are intentionally preserved.
