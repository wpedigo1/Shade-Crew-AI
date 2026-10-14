# Mission 033 — PyInstaller Backend Bundle (Standalone, Pre-Sidecar)

Route: Big Pickle (OpenCode Zen)
Punch Board item: 34 (advance — standalone backend bundling only)
Date: 2026-08-31 CT
Base: `main @ 781e99bf14405980cf3c39572422cfd835e6f886`
Result: **PASS (LOCAL)**

## Outcome

Mission 033 freezes the existing Python backend as a Windows PyInstaller
`onedir` bundle and proves the copied frozen executable can run without an
ambient Python, uv, or virtual environment. The real frozen process served the
health, ModelMix session, settings, and MCP SSE routes; used the real Windows
keyring across a process restart; used the file credential backend across a
second restart; applied the expected non-inherited current-user Windows ACL;
and shut down without an orphan, invalid JSON, credential temp file, or change
to repository `data/`.

This advances Punch Board item 34 but does not close it. The bundle was run
directly, not from Tauri. Rust sidecar spawning/lifecycle, `externalBin`, a
production installer, and final credential behavior in the delivered Tauri
package remain open.

## 1. Base, entrypoint finding, and frozen toolchain

The exact starting SHA was
`781e99bf14405980cf3c39572422cfd835e6f886`. Before PyInstaller was added,
`uv run python backend/main.py` exited 1 with:

```text
Traceback (most recent call last):
  File "C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\backend\main.py", line 20, in <module>
    from . import storage
ImportError: attempted relative import with no known parent package
```

That is a direct-script package-context failure, not a backend application
failure. The packaging-only `packaging/backend_entry.py` therefore executes
`backend.main` through
`runpy.run_module("backend.main", run_name="__main__", alter_sys=True)`. It
does not copy Uvicorn launch logic or change `backend/main.py`.

Observed frozen toolchain:

```text
PYINSTALLER=6.22.2
HOOKS_CONTRIB=2026.7
HOOK=C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.venv\lib\site-packages\PyInstaller\hooks\hook-keyring.py
```

The installed keyring hook was inspected directly. Its complete text was:

```python
#-----------------------------------------------------------------------------
# Copyright (c) 2014-2023, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License (version 2
# or later) with exception for distributing the bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
#
# SPDX-License-Identifier: (GPL-2.0-or-later WITH Bootloader-exception)
#-----------------------------------------------------------------------------

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Collect backends
hiddenimports = collect_submodules('keyring.backends')

# Keyring performs backend plugin discovery using setuptools entry points, which are listed in the metadata. Therefore,
# we need to copy the metadata, otherwise no backends will be found at run-time.
datas = copy_metadata('keyring')
```

Both required mechanisms were present, so the spec did not add a competing
keyring collection. Runtime proof below confirms that the hook worked in the
frozen executable.

## 2. Build history, fixes, warnings, and artifact size

The exact build command was:

```powershell
uv run pyinstaller --clean --noconfirm packaging/modelmix-backend.spec
```

The initial spec used `Path(SPECPATH).resolve().parent.parent`. The first build
exited 1 before analysis because PyInstaller looked for the nonexistent
`C:\Users\wpedi\ModelMix\.worktrees\packaging\backend_entry.py`. The observed
`SPECPATH` was already the worktree's `packaging` directory, so the durable
spec uses `Path(SPECPATH).resolve().parent`.

The build then completed, but the first frozen startup exposed a separate
metadata fallback failure. Installed distribution metadata for
`the-ai-counsel` was unavailable and
`the_ai_counsel_mcp.__init__` fell back to reading
`_internal\pyproject.toml`, which had not been bundled. The exact terminal
exception was:

```text
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.tmp\\mission033-runtime\\modelmix-backend\\_internal\\pyproject.toml'
```

The narrow packaging-only fix was
`datas=[(str(PROJECT_ROOT / "pyproject.toml"), ".")]`. The corrected build
placed the 727-byte file at `_internal\pyproject.toml`; its SHA-256 matched the
source:
`33351015CA6F1C8412A2059489CC2965EBB5DD88DFCD0812DA48FF75E1730C4A`.
The corrected frozen log then contained `MCP server mounted at /mcp` and no
`PackageNotFoundError`, `FileNotFoundError`, or MCP-unavailable message.

The successful build emitted exactly one `WARNING` line. It is reproduced
verbatim here:

```text
24098 WARNING: Hidden import "tzdata" not found!
```

PyInstaller also emitted the informational line
`Warnings written to C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\warn-modelmix-backend.txt`.
That generated analysis file lists conditional, platform-specific, and
optional missing imports; it is not an additional emitted `WARNING` line.
The exercised frozen runtime paths succeeded, including keyring, MCP, and
file-ACL behavior. The complete successful PyInstaller console output is
embedded in Appendix A.

Final artifact measurements observed from the corrected bundle:

```text
Mode        : onedir
ExePath     : C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\dist\modelmix-backend\modelmix-backend.exe
ExeBytes    : 12629354
ExeMiB      : 12.04
BundleBytes : 122797389
BundleMiB   : 117.11
ExeSha256   : 5B3296BBF124CB73A39104F9CA0EEB9170BBFC71C843CEDDA7CBF12702B3C177
```

`onedir` was selected because this mission proves a directly inspectable
standalone backend, not a distributable installer. It keeps the embedded
runtime and module-relative data at stable visible paths and avoids the
onefile bootloader/extraction-child shutdown complication that would obscure
later Tauri lifecycle work. The tradeoff is a 117.11 MiB directory rather than
one distributable file.

## 3. Isolated frozen process and no ambient Python help

The corrected bundle was copied to:

```text
C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.tmp\mission033-runtime\modelmix-backend
```

The retained immediately-before-exec child environment was:

```text
TIMESTAMP_UTC=2026-09-01T00:59:47.3826377Z
PATH=C:\WINDOWS\System32;C:\WINDOWS
VIRTUAL_ENV=
PYTHONHOME=
PYTHONPATH=
UV=
UV_PROJECT_ENVIRONMENT=
```

The managed hidden PowerShell wrapper directly invoked this command target:

```text
C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.tmp\mission033-runtime\modelmix-backend\modelmix-backend.exe
```

Windows listener/process inspection observed PID `17452` as
`modelmix-backend.exe` at that exact copied path, listening on
`127.0.0.1:8133`. Its embedded Python modules were loaded from the copied
bundle:

```text
...\modelmix-backend\_internal\python310.dll
...\modelmix-backend\_internal\python3.DLL
```

No loaded Python DLL came from outside the copied bundle. The corrected
process initially had zero descendants; later restart proofs recorded
`NEW_BAD_PYTHON_MODULE_COUNT=0`, `NEW_BAD_CHILD_COUNT=0`, and
`SANITIZED_ENV_MATCH=True`. No `python.exe`, `uv.exe`, or venv interpreter
assisted the frozen backend.

Corrected startup output:

```text
[08/31/26 19:59:50] INFO     MCP server mounted at /mcp (SSE at    main.py:2439
                             /mcp/sse, messages at /mcp/messages)
INFO:     Started server process [17452]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8133 (Press CTRL+C to quit)
```

## 4. Raw HTTP route evidence

### `GET /api/health`

```http
HTTP/1.1 200 OK
date: Tue, 01 Sep 2026 01:06:10 GMT
server: uvicorn
content-length: 107
content-type: application/json

{"status":"ok","service":"The AI Counsel API","mcp":{"sse_url":"http://127.0.0.1:8133/mcp/sse","tools":10}}
```

### `GET /api/modelmix/sessions/latest`

The isolated runtime truthfully had no persisted ModelMix session:

```http
HTTP/1.1 404 Not Found
date: Tue, 01 Sep 2026 01:06:10 GMT
server: uvicorn
content-length: 42
content-type: application/json

{"detail":"No persisted ModelMix session"}
```

### `GET /api/settings`

The complete response is reproduced below with its full JSON structure. The
product response contains only redacted `*_api_key_set` flags and connection/
storage status, never raw credential values. Inspection found no potentially
sensitive non-credential local scalar, so no additional report-time redaction
was applied.

```http
HTTP/1.1 200 OK
date: Tue, 01 Sep 2026 01:06:10 GMT
server: uvicorn
content-length: 9589
content-type: application/json

{"search_provider":"duckduckgo","search_keyword_extraction":"direct","search_result_count":8,"search_hybrid_mode":true,"ollama_base_url":"http://localhost:11434","full_content_results":3,"custom_endpoint_name":null,"custom_endpoint_url":null,"serper_api_key_set":false,"tavily_api_key_set":false,"brave_api_key_set":false,"tinyfish_api_key_set":false,"openrouter_api_key_set":false,"openai_api_key_set":false,"anthropic_api_key_set":false,"google_api_key_set":false,"mistral_api_key_set":false,"deepseek_api_key_set":false,"groq_api_key_set":false,"nvidia_api_key_set":false,"opencode_api_key_set":false,"custom_endpoint_api_key_set":false,"xai_oauth_connected":false,"openai_oauth_connected":false,"github_copilot_connected":false,"github_copilot_plan":null,"github_copilot_sku":null,"github_copilot_is_free_plan":null,"github_copilot_login":null,"credential_storage":"file","credential_storage_preferred":"file","credential_storage_available":{"file":true,"keyring":true},"credential_storage_unavailable_reason":null,"credential_storage_effective":"file","relay_ai_import_dismissed":false,"enabled_providers":{"openrouter":true,"ollama":false,"groq":false,"direct":false,"custom":false,"xai-oauth":false,"openai-oauth":false,"github-copilot":false},"direct_provider_toggles":{"openai":false,"anthropic":false,"google":false,"mistral":false,"deepseek":false,"groq":false,"nvidia":false,"opencode-zen":false,"opencode-go":false},"council_models":["",""],"chairman_model":"","council_member_filters":null,"chairman_filter":null,"search_query_filter":null,"council_temperature":0.5,"chairman_temperature":0.4,"stage2_temperature":0.3,"stage1_prompt":"You are a helpful AI assistant.\n{search_context_block}\nQuestion: {user_query}","stage2_prompt":"You are evaluating different responses to the following question:\n\nQuestion: {user_query}\n\n{search_context_block}\nHere are the responses from different models (anonymized):\n\n{responses_text}\n\nYour task:\n1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.\n2. Then, at the very end of your response, provide a final ranking.\n\nIMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:\n- Start with the line \"FINAL RANKING:\" (all caps, with colon)\n- Then list the responses from best to worst as a numbered list\n- Each line should be: number, period, space, then ONLY the response label (e.g., \"1. Response A\")\n- Do not add any other text or explanations in the ranking section\n\nExample of the correct format for your ENTIRE response:\n\nResponse A provides good detail on X but misses Y...\nResponse B is accurate but lacks depth on Z...\n\nFINAL RANKING:\n1. Response A\n2. Response B\n\nRank ONLY the responses listed above. Do not invent labels that were not provided.\n\nNow provide your evaluation and ranking:","stage3_prompt":"You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.\n\nOriginal Question: {user_query}\n\n{search_context_block}\nSTAGE 1 - Individual Responses:\n{stage1_text}\n\nSTAGE 2 - Peer Rankings:\n{stage2_text}\n\nYour task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:\n- The individual responses and their insights\n- The peer rankings and what they reveal about response quality\n- Any patterns of agreement or disagreement\n\nProvide a clear, well-reasoned final answer that represents the council's collective wisdom:","stage4_prompt":"You are the Chairman of an LLM Council. After {total_rounds} rounds of deliberation, the council has produced a final verdict with specific claim corrections.\n\nYour task: produce a CORRECTED DRAFT of the original document that incorporates ALL corrections, fixes flawed claims, strengthens weak claims, and applies every recommendation from the verdict.\n\nORIGINAL DOCUMENT:\n{original_text}\n\nCOUNCIL'S FINAL VERDICT (with claim corrections):\n{verdict_text}\n\nInstructions:\n- Rewrite the original document incorporating every correction identified in the verdict\n- Fix all claims marked FLAWED (replace with the corrected versions if provided)\n- Strengthen all claims marked WEAK with proper qualification or sourcing\n- Incorporate adopted improvements from the deliberation\n- Preserve the original document's structure, tone, and intent\n- Mark significant changes with [REVISED] or [NEW] inline so the author can see what changed\n- Do NOT add commentary or meta-discussion — produce only the corrected document","title_prompt":"Generate a very short title (3-5 words maximum) that summarizes the following question.\nThe title should be concise and descriptive. Do not use quotes or punctuation in the title.\n\nQuestion: {user_query}\n\nTitle:","query_prompt":"Extract the core search terms from the following question to use in a web search engine.\nReturn ONLY the search query, with no quotes, punctuation, or conversational text.\n\nQuestion: {user_query}\n\nSearch Query:","advisor_default_model":"","advisor_tiebreaker_model":"","advisor_temperature":0.7,"advisor_default_rounds":3,"advisor_round1_prompt":"{search_context_block}You are participating in a structured debate as an advisor.\n\nThe question being debated:\n{question}\n\nRound 1 is for your opening position. Do not rebut other advisors yet.\n\nTarget response length: 150 words maximum. Follow this exact structure:\n- Position (~100 words): State your position clearly and support it with reasoning.\n- Consensus Signal (~50 words): State your CONSENSUS_SCORE (1-5) and explain it in one sentence.\n\nBe direct and concise. If you exceed 150 words, the response may be flagged with a warning.{consensus_tag}","advisor_followup_prompt":"{search_context_block}You are participating in a structured debate as an advisor.\n\nThe question being debated:\n{question}\n\nThis is Round {round_number}. You are responding to the debate as it has evolved, not re-answering the original question from scratch.\n\nCross-pollination extract from Round {previous_round_number} (your primary argumentation target):\n{cross_pollination_extract}\n\nBackground transcript so far (secondary context only):\n\n{transcript}\n\nYou must address at least one specific claim from the cross-pollination extract. Name the advisor you are rebutting or conceding to. Do not rebut your own claims; choose a claim made by another advisor.\n\nTarget response length: 250 words maximum. Follow this exact structure:\n- Position/Update (~100 words): State your current position or how it shifted since the last round.\n- Rebuttal (~100 words): Pick the single strongest peer argument and argue against it specifically. Name the advisor you're rebutting.\n- Consensus Signal (~50 words): State your CONSENSUS_SCORE (1-5) and explain it in one sentence.\n\nIf you exceed 250 words, the response may be flagged with a warning. Do not skip the rebuttal.{consensus_tag}","advisor_cross_pollination_prompt":"You are preparing a cross-pollination extract for a structured advisor debate.\n\nOriginal question:\n{question}\n\nRound {round_number} transcript:\n{round_transcript}\n\nReturn a brief structured extract. For each advisor, include:\n- Overall position: one line\n- Strongest claims: 2-3 bullets containing reasoned points, not vague assertions\n\nKeep it lightweight. Do not write essays. Use the advisor names from the transcript.","advisor_verdict_prompt":"You are a neutral analyst reviewing a structured debate between advisors.\n\nThe original question:\n{question}\n\nDebate arc signal:\n{debate_arc}\n\nFull debate transcript:\n{transcript}\n\nProduce a structured verdict in the following exact format. Use markdown formatting.\n\n## Summary\n2-3 sentences capturing the key insight from this debate.\n\n## Consensus Points\nBulleted list of points where all advisors agreed.\n\n## Disagreements\nFor each disagreement, create a row with: the point of contention, each side's position, and which argument had stronger evidence. Use a markdown table with columns: Point | Position A | Position B | Stronger Argument.\n\n## Verdict\nState which overall position was strongest and why, naming the advisor(s) who made the most compelling case. If the debate reached consensus, say so.\n\n## Recommended Next Steps\n3-5 concrete, actionable next steps based on the debate outcome.\n\n## Open Uncertainties\nBulleted list of questions that remain unresolved after the debate.","advisor_tiebreaker_prompt":"You are a neutral tiebreaker called in because the advisors could not reach agreement.\n\nThe original question:\n{question}\n\nFull debate transcript:\n{transcript}\n\nThe advisors' positions are evenly split. Your job is to:\n1. Identify the strongest arguments from each side\n2. Weigh the evidence and reasoning\n3. Deliver a clear decision — which position should prevail and why\n4. If appropriate, propose a synthesis that takes the best from both sides\n\nBe decisive. Do not equivocate.","advisor_presets":[],"council_presets":[],"date_format":"auto","response_language":"English","font_size":"default","valid_response_languages":["English","Spanish","French","German","Italian","Portuguese","Dutch","Polish","Russian","Ukrainian","Arabic","Hebrew","Hindi","Japanese","Korean","Chinese (Simplified)","Chinese (Traditional)","Greek"],"response_language_default":"English","critique_mode":"freeform","debate_rounds":1,"auto_converge":true,"convergence_threshold":2,"show_free_only":false,"execution_mode":"full"}
```

No settings export endpoint was called.

### `GET /mcp/sse`

The route returned HTTP 200 and an SSE endpoint event before the deliberate
two-second client timeout:

```http
HTTP/1.1 200 OK
date: Tue, 01 Sep 2026 01:06:10 GMT
server: uvicorn
cache-control: no-store
connection: keep-alive
x-accel-buffering: no
content-type: text/event-stream; charset=utf-8
transfer-encoding: chunked

event: endpoint
data: /mcp/messages/?session_id=2149ce6c3de743318f55997cf83849a8
```

Curl reported `Operation timed out after 2006 milliseconds with 85 bytes
received` and exited 28 after the successful streaming connection. Health,
sessions/latest, and settings curl invocations each exited 0.

## 5. Frozen Windows keyring proof

The canonical bounded rerun selected `nvidia_api_key` only after its redacted
flag was false and `NVIDIA_API_KEY` was absent from process, user, and machine
environment scopes. The only written value was the fixed fake sentinel
`mission033-frozen-keyring-sentinel-not-a-secret`; it was not a real
credential.

The effective-mode response was:

```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"ok","mode":"keyring","moved":0,"ids":[],"availability":{"file":true,"keyring":true,"unavailable_reason":null,"in_container":false,"preferred":"keyring","effective":"keyring"}}
```

The exact redacted flags parsed from the raw HTTP responses were:

```text
PRECONDITION_STATUS=HTTP/1.1 200 OK
PRECONDITION_FIELD=nvidia_api_key
PRECONDITION_FLAG_NAME=nvidia_api_key_set
PRECONDITION_FLAG=False
PRECONDITION_EFFECTIVE=keyring
ENV_NVIDIA_API_KEY_PROCESS_ABSENT=True
ENV_NVIDIA_API_KEY_USER_ABSENT=True
ENV_NVIDIA_API_KEY_MACHINE_ABSENT=True

SET_STATUS=HTTP/1.1 200 OK
SET_CREDENTIAL_STORAGE_EFFECTIVE=keyring
SET_NVIDIA_API_KEY_SET=true

RESTART_STATUS=HTTP/1.1 200 OK
RESTART_CREDENTIAL_STORAGE_EFFECTIVE=keyring
RESTART_NVIDIA_API_KEY_SET=true

CLEAR_STATUS=HTTP/1.1 200 OK
CLEAR_CREDENTIAL_STORAGE_EFFECTIVE=keyring
CLEAR_NVIDIA_API_KEY_SET=false

INDEPENDENT_CLEANUP_STATUS=HTTP/1.1 200 OK
INDEPENDENT_CREDENTIAL_STORAGE_EFFECTIVE=keyring
INDEPENDENT_NVIDIA_API_KEY_SET=false
```

PID `19220` received Ctrl+C and exited; the port was released; Uvicorn logged
`Application shutdown complete` and `Finished server process [19220]`. The
same sanitized wrapper launched PID `20008`. The true flag on the new process
is the cross-process retrieval proof. Exactly one storage POST, one fake
sentinel PUT, and one clear PUT occurred in the canonical rerun. The final
independent GET proves the fake keyring sentinel was cleared.

## 6. Frozen file credential and Windows ACL proof

The file-mode run selected a different initially empty field,
`mistral_api_key`, only after its redacted flag was false and
`MISTRAL_API_KEY` was absent from process, user, and machine scopes. The only
written value was the fixed fake sentinel
`mission033-frozen-file-sentinel-not-a-secret`.

Raw mode-switch response:

```http
HTTP/1.1 200 OK
date: Tue, 01 Sep 2026 01:34:53 GMT
server: uvicorn
content-length: 177
content-type: application/json

{"status":"ok","mode":"file","moved":0,"ids":[],"availability":{"file":true,"keyring":true,"unavailable_reason":null,"in_container":false,"preferred":"file","effective":"file"}}
```

The raw-response proof fields were:

```text
PRECONDITION_STATUS=HTTP/1.1 200 OK
PRECONDITION_FIELD=mistral_api_key
PRECONDITION_FLAG_NAME=mistral_api_key_set
PRECONDITION_FLAG=False
PRECONDITION_EFFECTIVE=keyring
ENV_MISTRAL_API_KEY_PROCESS_ABSENT=True
ENV_MISTRAL_API_KEY_USER_ABSENT=True
ENV_MISTRAL_API_KEY_MACHINE_ABSENT=True

SENTINEL_SET_STATUS=HTTP/1.1 200 OK
SENTINEL_SET_FLAG=True
SENTINEL_SET_EFFECTIVE=file

RESTART_STATUS=HTTP/1.1 200 OK
RESTART_FLAG=True
RESTART_EFFECTIVE=file

CLEAR_STATUS=HTTP/1.1 200 OK
CLEAR_FLAG=False
CLEAR_EFFECTIVE=file

INDEPENDENT_CLEANUP_STATUS=HTTP/1.1 200 OK
INDEPENDENT_CLEANUP_FLAG=False
INDEPENDENT_CLEANUP_EFFECTIVE=file
FILE_SENTINEL_CLEARED=True
```

Exactly one isolated file existed, at:

```text
C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.tmp\mission033-runtime\modelmix-backend\_internal\data\credentials.json
```

Its contents were never read, printed, hashed, exported, or reverse-inspected.
Raw `icacls` output:

```text
C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.tmp\mission033-runtime\modelmix-backend\_internal\data\credentials.json MSI\wpedigo:(F)

Successfully processed 1 files; Failed processing 0 files
```

Structured ACL output:

```text
IdentityReference FileSystemRights IsInherited AccessControlType
----------------- ---------------- ----------- -----------------
MSI\wpedigo            FullControl       False             Allow
```

The frozen process also logged the whitespace-wrapped message
`Restricted ... credentials.json to the current user account.`; no ACL-failure
warning appeared. PID `20008` shut down normally, the port was released, and
PID `14296` retrieved the true file-backed flag after restart. Exactly one
storage POST, one fake sentinel PUT, and one clear PUT occurred. The sentinel
was cleared, then Task 9 deleted the entire isolated runtime, including this
isolated credential file.

## 7. Shutdown, integrity, and repository isolation

Final Ctrl+C evidence for PID `14296`:

```text
LISTENER_COUNT=0
RUNTIME_OR_BACKUP_PROCESS_COUNT=0
SHUTDOWN_MATCH_COUNT=4
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [14296]
```

All isolated JSON and atomic-write checks passed before deletion:

```text
JSON_FILE_COUNT=13
JSON_OK_COUNT=13
JSON_PARSE_FAILURE_COUNT=0
CREDENTIAL_TEMP_COUNT=0
```

Repository live-data hashes were recorded before the corrected runtime copy
and compared after shutdown:

```text
PRE_COPY_HASH_COUNT=2
POST_SHUTDOWN_HASH_COUNT=2
HASH_DIFFERENCE_COUNT=0
```

The two unchanged SHA-256 values were:

```text
0C31BCA8F0E673ED70B38E2E1E99F4F9F70F2443C7334EEBB00BA71C33CFF83B  data\conversations\model_pricing_cache.json
F54375FC4C538C5A5ABD058C1613E345B8A9A6EFB497FC8DC7C32EE9AB3FB341  data\settings.json
```

After exact-path validation, scoped cleanup removed the active runtime, its
recoverable pre-fix backup, and the mission-created baseline temp directory.
The final evidence recorded `.tmp` absent, `data/` and `dist/` present, no
listener, no orphan, zero live-data hash differences, and empty tracked/staged
diffs at that checkpoint.

## 8. Regression validation actually observed

The exact first backend command reproduced the established Windows temp-root
failure:

```powershell
uv run pytest backend/tests -q
```

```text
E               PermissionError: [WinError 5] Access is denied: 'C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo'
247 passed, 214 errors in 12.55s
EXIT_CODE=1
ELAPSED_SECONDS=14.015
```

The unchanged suite was rerun with shell-local `TEMP` and `TMP` plus a
worktree-local base temp:

```powershell
uv run pytest backend/tests -q --basetemp C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.tmp\mission033-pytest\pytest-basetemp
```

```text
461 passed in 30.69s
EXIT_CODE=0
ELAPSED_SECONDS=31.963
```

Frontend, Rust, and focused Python validation:

```text
cd frontend; npm test
Test Files  15 passed (15)
Tests       138 passed (138)
EXIT_CODE=0

cd frontend; npm run build
vite v7.3.6
439 modules transformed
built in 1.67s
EXIT_CODE=0

cd frontend; npm run lint
EXIT_CODE=0

cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
EXIT_CODE=0

cargo check --manifest-path src-tauri/Cargo.toml
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.46s
EXIT_CODE=0

uv run ruff check packaging/backend_entry.py backend/tests/test_packaging_entrypoint.py
All checks passed!
EXIT_CODE=0
```

The worktree-local pytest temp root was removed after a scoped dry run.

## 9. Precise committed scope and remaining work

Mission 033 implementation scope is limited to:

- `pyproject.toml` and `uv.lock` for the PyInstaller dev toolchain;
- `packaging/backend_entry.py` and `packaging/modelmix-backend.spec`;
- `backend/tests/test_packaging_entrypoint.py`;
- the approved Mission 032 metadata corrections in
  `src-tauri/tauri.conf.json` and `src-tauri/Cargo.toml`;
- this report plus `PUNCH-BOARD.md`, `MISSION-INDEX.md`, and
  `ENGINEERING-PROGRESS.md`.

There are no frontend source changes, backend application-logic changes,
`backend/main.py` changes, credential-backend changes, Tauri Rust changes,
sidecar configuration, `externalBin`, installer output, or generated build
artifacts in the intended tracked scope.

Punch Board item 34 remains **IN PROGRESS**. The standalone backend bundling
half is proven. Still open: Tauri sidecar configuration; Rust process start,
readiness, shutdown, crash, and orphan handling; production
`cargo tauri build` installer delivery; packaged frontend/backend integration;
and final credential packaging/re-verification in the actual delivered Tauri
application.

## Appendix A — Complete successful PyInstaller console output

Command:

```powershell
uv run pyinstaller --clean --noconfirm packaging/modelmix-backend.spec
```

```text
151 INFO: PyInstaller: 6.22.2, contrib hooks: 2026.7
152 INFO: Python: 3.10.20
164 INFO: Platform: Windows-10-10.0.26200-SP0
164 INFO: Python environment: C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.venv
169 INFO: Removing temporary files and cleaning cache in C:\Users\wpedi\AppData\Local\pyinstaller
180 INFO: Module search paths (PYTHONPATH):
['C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\Scripts\\pyinstaller.exe',
 'C:\\Users\\wpedi\\AppData\\Roaming\\uv\\python\\cpython-3.10-windows-x86_64-none\\python310.zip',
 'C:\\Users\\wpedi\\AppData\\Roaming\\uv\\python\\cpython-3.10-windows-x86_64-none\\DLLs',
 'C:\\Users\\wpedi\\AppData\\Roaming\\uv\\python\\cpython-3.10-windows-x86_64-none\\lib',
 'C:\\Users\\wpedi\\AppData\\Roaming\\uv\\python\\cpython-3.10-windows-x86_64-none',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\win32',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\win32\\lib',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\Pythonwin',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\packaging',
 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033']
568 INFO: Appending 'datas' from .spec
568 INFO: checking Analysis
568 INFO: Building Analysis because Analysis-00.toc is non existent
568 INFO: Looking for Python shared library...
568 INFO: Using Python shared library: C:\Users\wpedi\AppData\Roaming\uv\python\cpython-3.10-windows-x86_64-none\python310.dll
568 INFO: Running Analysis Analysis-00.toc
568 INFO: Target bytecode optimization level: 0
568 INFO: Initializing module dependency graph...
570 INFO: Initializing module graph hook caches...
586 INFO: Analyzing modules for base_library.zip ...
1288 INFO: Processing standard module hook 'hook-heapq.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
1334 INFO: Processing standard module hook 'hook-encodings.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
2245 INFO: Processing standard module hook 'hook-math.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
2357 INFO: Processing standard module hook 'hook-pickle.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
3176 INFO: Caching module dependency graph...
3211 INFO: Analyzing C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\packaging\backend_entry.py
3240 INFO: Analyzing hidden import 'backend.main'
3408 INFO: Processing standard module hook 'hook-anyio.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
4116 INFO: Processing standard module hook 'hook-multiprocessing.util.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
4212 INFO: Processing standard module hook 'hook-xml.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
4361 INFO: Processing standard module hook 'hook-_ctypes.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
4538 INFO: Processing pre-safe-import-module hook 'hook-typing_extensions.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
4539 INFO: SetuptoolsInfo: initializing cached setuptools info...
5388 INFO: Processing standard module hook 'hook-pydantic.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
5862 INFO: Processing standard module hook 'hook-platform.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
6008 INFO: Processing standard module hook 'hook-rich.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
6603 INFO: Processing standard module hook 'hook-pygments.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
8338 INFO: Processing standard module hook 'hook-sysconfig.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
8400 INFO: Processing standard module hook 'hook-webbrowser.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
8630 INFO: Processing standard module hook 'hook-zoneinfo.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
9506 INFO: Processing standard module hook 'hook-keyring.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
10082 INFO: Processing pre-safe-import-module hook 'hook-jaraco.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10082 INFO: Setuptools: 'jaraco' appears to be a partial setuptools-vendored copy - extending search paths to ['C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\jaraco', 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\setuptools\\_vendor\\jaraco']!
10084 INFO: Processing pre-safe-import-module hook 'hook-jaraco.context.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10212 INFO: Processing pre-safe-import-module hook 'hook-backports.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10213 INFO: Setuptools: 'backports' appears to be a partial setuptools-vendored copy - extending search paths to ['C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\backports', 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\setuptools\\_vendor\\backports']!
10214 INFO: Processing pre-safe-import-module hook 'hook-backports.tarfile.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10257 INFO: Processing standard module hook 'hook-backports.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
10263 INFO: Processing pre-safe-import-module hook 'hook-jaraco.functools.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10269 INFO: Processing pre-safe-import-module hook 'hook-more_itertools.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10348 INFO: Processing pre-safe-import-module hook 'hook-importlib_metadata.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10363 INFO: Processing standard module hook 'hook-importlib_metadata.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
10379 INFO: Processing pre-safe-import-module hook 'hook-zipp.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
10444 INFO: Processing standard module hook 'hook-ddgs.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
11248 INFO: Processing standard module hook 'hook-lxml.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
11602 INFO: Processing standard module hook 'hook-lxml.etree.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
11734 INFO: Processing standard module hook 'hook-certifi.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
12384 INFO: Processing standard module hook 'hook-difflib.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
12528 INFO: Processing standard module hook 'hook-numpy.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
13953 INFO: Processing standard module hook 'hook-charset_normalizer.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
14269 INFO: Processing standard module hook 'hook-pytest.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
14546 INFO: Processing standard module hook 'hook-py.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
14790 INFO: Processing pre-safe-import-module hook 'hook-packaging.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
14893 INFO: Processing pre-safe-import-module hook 'hook-tomli.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
16663 INFO: Processing standard module hook 'hook-xml.etree.cElementTree.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
16790 INFO: Processing standard module hook 'hook-PIL.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
16894 INFO: Processing standard module hook 'hook-PIL.Image.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
17307 INFO: Processing standard module hook 'hook-PIL.ImageFilter.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
17509 INFO: Processing standard module hook 'hook-regex.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
17873 INFO: Processing standard module hook 'hook-pdfminer.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
18237 INFO: Processing standard module hook 'hook-cryptography.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
20041 INFO: hook-cryptography: cryptography does not seem to be using dynamically linked OpenSSL.
20259 INFO: Processing standard module hook 'hook-pypdfium2.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
20278 INFO: Processing standard module hook 'hook-pypdfium2_raw.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
20774 INFO: Processing standard module hook 'hook-opentelemetry.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
21117 INFO: Processing standard module hook 'hook-uvicorn.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
21999 INFO: Processing standard module hook 'hook-websockets.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
23045 INFO: Processing standard module hook 'hook-pywintypes.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
23241 INFO: Processing standard module hook 'hook-jsonschema.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
23332 INFO: Processing standard module hook 'hook-jsonschema_specifications.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
23355 INFO: Processing pre-safe-import-module hook 'hook-importlib_resources.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
23459 INFO: Processing module hooks (post-graph stage)...
23582 INFO: Processing standard module hook 'hook-fake_useragent.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
23717 INFO: Processing standard module hook 'hook-lxml.isoschematron.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
24098 WARNING: Hidden import "tzdata" not found!
24116 INFO: Processing standard module hook 'hook-win32ctypes.core.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
25076 INFO: Processing standard module hook 'hook-pycparser.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
25385 INFO: Processing standard module hook 'hook-setuptools.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
25394 INFO: Processing pre-safe-import-module hook 'hook-distutils.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
25394 INFO: Processing pre-find-module-path hook 'hook-distutils.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_find_module_path'
25767 INFO: Processing standard module hook 'hook-distutils.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
25780 INFO: Processing standard module hook 'hook-distutils.util.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
25851 INFO: Processing standard module hook 'hook-_osx_support.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
25890 INFO: Processing pre-safe-import-module hook 'hook-jaraco.text.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
25891 INFO: Setuptools: 'jaraco.text' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.jaraco.text'!
25896 INFO: Processing standard module hook 'hook-setuptools._vendor.jaraco.text.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
26381 INFO: Processing pre-safe-import-module hook 'hook-wheel.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
26382 INFO: Setuptools: 'wheel' appears to be a setuptools-vendored copy - creating alias to 'setuptools._vendor.wheel'!
26528 INFO: Processing pre-safe-import-module hook 'hook-gi.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\pre_safe_import_module'
26726 INFO: Processing standard module hook 'hook-PIL.SpiderImagePlugin.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks'
28370 INFO: Processing standard module hook 'hook-lxml.objectify.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\stdhooks'
28389 INFO: Performing binary vs. data reclassification (232 entries)
28419 INFO: Looking for ctypes DLLs
28476 INFO: Analyzing run-time hooks ...
28485 INFO: Including run-time hook 'pyi_rth_inspect.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\rthooks'
28486 INFO: Including run-time hook 'pyi_rth_pkgutil.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\rthooks'
28490 INFO: Including run-time hook 'pyi_rth_multiprocessing.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\rthooks'
28492 INFO: Including run-time hook 'pyi_rth_pywintypes.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\rthooks'
28492 INFO: Including run-time hook 'pyi_rth_cryptography_openssl.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\_pyinstaller_hooks_contrib\\rthooks'
28493 INFO: Including run-time hook 'pyi_rth_setuptools.py' from 'C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\PyInstaller\\hooks\\rthooks'
28529 INFO: Creating base_library.zip...
28563 INFO: Looking for dynamic libraries
31347 INFO: Extra DLL search directories (AddDllDirectory): ['C:\\Users\\wpedi\\ModelMix\\.worktrees\\codex-mission-033\\.venv\\lib\\site-packages\\numpy.libs']
31348 INFO: Extra DLL search directories (PATH): []
32474 INFO: Warnings written to C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\warn-modelmix-backend.txt
32713 INFO: Graph cross-reference written to C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\xref-modelmix-backend.html
32791 INFO: checking PYZ
32791 INFO: Building PYZ because PYZ-00.toc is non existent
32791 INFO: Building PYZ (ZlibArchive) C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\PYZ-00.pyz
33916 INFO: Building PYZ (ZlibArchive) C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\PYZ-00.pyz completed successfully.
33970 INFO: checking PKG
33970 INFO: Building PKG because PKG-00.toc is non existent
33970 INFO: Building PKG (CArchive) modelmix-backend.pkg
33998 INFO: Building PKG (CArchive) modelmix-backend.pkg completed successfully.
34000 INFO: Bootloader C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\.venv\lib\site-packages\PyInstaller\bootloader\Windows-64bit-intel\run.exe
34000 INFO: checking EXE
34000 INFO: Building EXE because EXE-00.toc is non existent
34000 INFO: Building EXE from EXE-00.toc
34000 INFO: Copying bootloader EXE to C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\build\modelmix-backend\modelmix-backend.exe
34062 INFO: Copying icon to EXE
34099 INFO: Copying 0 resources to EXE
34100 INFO: Embedding manifest in EXE
34134 INFO: Appending PKG archive to EXE
34181 INFO: Fixing EXE headers
34442 INFO: Building EXE from EXE-00.toc completed successfully.
34447 INFO: checking COLLECT
34447 INFO: Building COLLECT because COLLECT-00.toc is non existent
34447 INFO: Removing dir C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\dist\modelmix-backend
34539 INFO: Building COLLECT COLLECT-00.toc
35340 INFO: Building COLLECT COLLECT-00.toc completed successfully.
35357 INFO: Build complete! The results are available in: C:\Users\wpedi\ModelMix\.worktrees\codex-mission-033\dist
```
