# Mission 043 — Foundational Domain Documentation

Route: Big Pickle (OpenCode Zen)

Punch Board items: **7 / 9 / 12 / 13** (all drawn to **SATISFIED** by this
mission).

Base: `main` @ `b22e1f0` "chore(modelmix): remove confirmed dead code
(Mission 042)".

Result: **PASS**. Wrote four code-sourced reference docs under `docs/modelmix/`.
**Zero code changes.** Every claim in every doc is grounded in the current source
with file:line citations; no behavior was invented and no punch-board wording was
silently "corrected" into the docs — the wording discrepancies (notably item 9's
`partially_completed` vs the real `"partial"`) are called out explicitly.

## 1. The one rule that matters most

The CODE wins. The documents claim FROM real code, not from punch-board
aspirational wording. Where the punch-board wording diverges from the code, the
doc says so plainly rather than silently adopting either side.

Two places this actually mattered:

1. **Run status token (item 9).** The punch board's locked terminal-state
   vocabulary uses `partially_completed`. The real code uses **`partial`**
   (`persistence.py:21` `TERMINAL_STATUSES`; `registry.py:314`
   `final_status = "partial" if worker_failures else "completed"`). `domain-objects.md`
   and `run-state-machine.md` use `partial`, and the discrepancy is recorded in
   each doc plus `PUNCH-BOARD.md` and this report.
2. **Truthful negatives (item 12).** The capability matrix states what is real
   and what is absent — exactly one streaming provider (`openai-oauth`); only
   `openrouter` derives catalog pricing; `is_free` derived honestly per provider;
   and capabilities left unimplemented (per-query cost, vision/file/tools in the
   alpha run path) are marked absent, not advertised.

## 2. Deliverables

| File (`docs/modelmix/`) | Item | Content (code-sourced) |
|---|---|---|
| `domain-objects.md` | 7 | Versioned session doc, canonical Message, Run snapshot, RunEvent, Seat, Moderator, Provider/Model reference, ProviderStreamEvent; three persistence layers; explicit "Artifact/reference not implemented"; `partial` correction |
| `run-state-machine.md` | 9 | `RUN_STATUSES`/`TERMINAL_STATUSES`, message-vs-run status sets, `run_started`/seat lifecycle, guardrail caps, both terminal-model writers (no-moderator triage and moderator fan-in paths), cancellation, seat/run timeouts, terminal-outcome table, flow diagram |
| `provider-capability-matrix.md` | 12 | base contract, prefix/temperature rules, capability table (usage/pricing/is_free/stream/auth per provider), honest negatives, telemetry labeling |
| `privacy-and-data-routing.md` | 13 | credential storage backends, settings-API vs credential-store separation, single-flight OAuth refresh, seat-scoped history, bounded visible-only Moderator fan-in, what is not routed anywhere |

Plus this mission report and the three tracking-file updates.

## 3. What changed (files, docs only)

* `docs/modelmix/domain-objects.md` — new
* `docs/modelmix/run-state-machine.md` — new
* `docs/modelmix/provider-capability-matrix.md` — new
* `docs/modelmix/privacy-and-data-routing.md` — new
* `docs/modelmix/043-foundational-domain-documentation.md` — this report
* `docs/modelmix/PUNCH-BOARD.md` — items 7 / 9 / 12 / 13 → **SATISFIED**; item 9
  carries the `partial` vocabulary note; retries remain open on item 9
* `docs/modelmix/MISSION-INDEX.md` — row 043 + Mission 043 Result section
* `docs/modelmix/ENGINEERING-PROGRESS.md` — Mission 043 Result section

No `.py`, no frontend source, no dependency, no lockfile was touched.

## 4. Verification posture

The privacy doc (§8) and the matrix (§6) are explicit that describing intended
routing/capabilities is not a claim that security or capability behaviors work;
the relevant backend tests (credential store, OAuth gating, history isolation,
guardrails) are exercised by the suite in §5.

## 5. Validation (raw, unedited)

### Backend

The mission's literal command `uv run pytest backend/tests -q` reproduces the
same **environmental** failure as Missions 029/031/038/039/042: a corrupted ACL
on the system pytest temp root
`C:\Users\wpedi\AppData\Local\Temp\pytest-of-wpedigo`, surfacing as
`PermissionError [WinError 5] Access is denied` at `tmp_path` fixture setup. It
is unrelated to this docs-only mission (documentation cannot change test
outcomes). I reran with `--basetemp` pointed at the workspace temp dir to prove
the suite passes:

```text
485 passed in 32.52s
```

Clean, zero failures. Since this mission changed no backend code, the same
`485 passed` that passed Mission 042's removal holds.

### Frontend (unchanged code, re-asserted baseline)

```text
> the-ai-counsel@0.11.4 test
> vitest run

 Test Files  15 passed (15)
      Tests  138 passed (138)
```

```text
> the-ai-counsel@0.11.4 build
> vite build

✓ built in 2.67s
```

```text
> the-ai-counsel@0.11.4 lint
> eslint .

(clean — no output)
```

### git status --short / git diff --stat

```text
 M docs/modelmix/PUNCH-BOARD.md
 M docs/modelmix/MISSION-INDEX.md
 M docs/modelmix/ENGINEERING-PROGRESS.md
 A docs/modelmix/domain-objects.md
 A docs/modelmix/run-state-machine.md
 A docs/modelmix/provider-capability-matrix.md
 A docs/modelmix/privacy-and-data-routing.md
 A docs/modelmix/043-foundational-domain-documentation.md
```

`git diff --stat` shows only these eight files, all under `docs/modelmix/`. No
unrelated changes — consistent with the docs-only boundary.

## 6. Commit

`docs(modelmix): foundational domain documentation (Mission 043)` — committed
and pushed, verified local == origin.

## 7. Notes

* **No code changes**: no `schema_version` bump, no new dependencies, no
  lockfile, no `.py` touched.
* **Item 9 partial-vs-`partial`**: the punch board is the product memory; the
  code value `partial` is authoritative for implementation and docs. `retries`
  remain explicitly open on item 9 (the state machine doc does not claim a
  retry contract exists).
* **Item 7 artifact/reference**: recorded as not implemented in this alpha
  slice rather than invented.
* Carried-forward open items (unchanged by this mission): the item-31a/31b
  CORS/allow-list findings, the Tauri item-34 re-verification, `BROKEN_MODELS`
  and `get_sync_client` orphaned-code cleanup, and the optional
  `OPEN_SOURCE_CREDITS.md`/`THIRD-PARTY-LICENSES-frontend.txt` regeneration from
  Mission 041/042.