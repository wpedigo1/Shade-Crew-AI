# Crew Chief verification — Pass 1

Product seats: **Gearhead | wider Crew Chief | Grease Monkey**.
Internal `worker_a`, `moderator`, `worker_b`, routes and persisted version 1 stay stable.

## Flow and bounds

1. Independent workers finish through the existing registry.
2. Crew Chief reviews original request, its own bounded history, and visible worker handoff. Existing 100,000-character cap per worker and truncation metadata remain. Failed-worker exclusion is unchanged.
3. A strict JSON claim review selects up to **three** important checks, including agreed claims. Pure preferences can be classified **not necessary to verify**. Empty review skips research.
4. At most **three sequential searches**, up to **three sources each**, through free Bing HTML search in the already-installed DDGS library. No API keys, paid providers, engine fallback, full-page fetch, browser agent or arbitrary URL fetch. Only focused generated queries are submitted. Query privacy depends in part on model compliance; avoid private data in research requests.
5. One batched model assessment classifies claims **verified**, **contradicted**, or **unresolved**. A source ID and nonempty exact substring quote from that claim's retrieved excerpts are required for the first two. Unknown/duplicate verdicts and invented citations cannot resolve a claim. No source or tool error stays unresolved.
6. The same Crew Chief provider/model streams the final answer with the ledger. Prompts explicitly permit rejecting both mechanics, prohibit voting, require uncertainty, and preserve the next 1–2 diagnostic actions style.

**One verification round.** At most **three model calls total** (review, optional assessment, final); no recursive research or tools chosen by sources. Review/assessment each accept at most 12,000 visible output characters. All phases share the existing cumulative seat deadline and run timeout. Searches have a 15-second async deadline, library socket timeout 10 seconds. A cancelled thread cannot be killed mid-request, but its result is discarded and never resumes the run.

Existing local router, shared endpoint queue, one resident model (`--models-max 1`), templates, timeouts configuration and exact model identities are unchanged. Streaming-capable providers use the same stream transport for every phase; nonstreaming providers retain query support.

## Evidence representation

`moderator_evidence` events carry visible decision metadata, never hidden reasoning:

```json
{
  "claim_id": "c1",
  "claim": "Supply is 24 volts",
  "query": "focused specification query",
  "result": "contradicted",
  "summary": "Brief visible finding",
  "assessment": "model_assessed",
  "sources": [{
    "source_id": "s1",
    "title": "Reference title",
    "url": "https://example.org/reference",
    "excerpt": "Retrieved text",
    "kind": "search_snippet"
  }],
  "source_id": "s1",
  "quote": "Retrieved text"
}
```

`error` appears on failed/interrupted checks. The canonical event envelope retains run ID, monotonic sequence, timestamp; the assistant projection adds `updated_at`. Pending evidence is published before research so cancellation retains unresolved claims. Events and projected assistant `evidence` persist atomically without migration. Replaying updates replaces a claim by ID and preserves deduplication. Browser reload/history retain the ledger.

`moderator_verification_started/completed` drive the small Verifying indication.
`moderator_verification_usage` stores separate review/assessment usage and calculable OpenRouter cost. Missing usage/cost stays unknown. Known review cost is added to that seat's final cost only for the existing previous-run spend-limit check; no cross-seat aggregation. An interrupted model call may not report usage. Final-stream telemetry retains its existing meaning.

## Verification and limits

Deterministic tests use scripted providers and sources to prove control flow, source binding, rejecting conflicting and falsely agreeing mechanics, final evidence input, failure/inconclusive/skip paths, bounds, cancellation, replay, persistence and UI. They do **not** prove any real model's claim-detection or source-evaluation accuracy.

A live adapter probe returned actual Bing source titles, URLs and excerpts. Those results were not sufficient to verify the unit-conversion question; retrieval success is not factual verification. DuckDuckGo and Brave probes returned no results. No live-model inference was repeated; the provider streaming path is unchanged.

The final prose is model-generated. Exact quote binding prevents invented citations but cannot prove quote relevance, authority, applicability or faithful final-answer interpretation. Malicious search text is marked untrusted in instructions; prompt injection remains a model-level risk. This is a framework, not a reliable exact-machine knowledge system. Pass 2 should add an explicitly scoped primary document source and evaluate real Crew Chief behavior against a small fixed set of claims before expanding tools. No VIN, PDF/manual parser, wiring database, training or model bakeoff was added here.
