# Changelog

Notable changes, newest first. Dates are when the work landed.

## [Unreleased]

### Planning — 2026-06-11

- Settled the architecture and the stack after a full pass over the available
  options. Wrote up the product spec, the architecture, and the decision log.
- Scoped the build down to one scenario, end to end, on Foundry IQ. Work IQ and
  Fabric IQ moved to the roadmap.
- Rewrote the concept around interception (guardrail) rather than retrieval
  (librarian) — that's the part that's actually different.
- Drafted the phased build plan: de-risk and provision first, then IQ and safety,
  then the spine, then the console, then deploy and record.

### Phase 0 — provisioning — 2026-06-11

- Stood up the Azure footprint in an isolated resource group (`janus-rg`, East US):
  AI Search (Basic) for retrieval, Content Safety (S0) for the groundedness and
  injection guards, and an Azure OpenAI account with `gpt-4o-mini` and
  `text-embedding-3-large` deployed.
- Wired keyless auth: the search service's managed identity can call the model
  for query planning, and the dev account has the data-plane roles it needs.
  Nothing uses keys; `DefaultAzureCredential` handles it.
- Initialized the repo and the working tree (`api`, `web`, `infra`, `data`,
  `fixtures`).

- Wrote the synthetic corpus: the Northwind Logistics vendor-consolidation
  precedent thread (kickoff, risk note, outage postmortem, policy) plus a
  spend-history CSV and fifteen unrelated decision documents as realistic
  retrieval noise.
- Stood up the backend skeleton: FastAPI app, the domain models (a lesson can't
  exist without a citation), the stream-event contract, and a smoke endpoint that
  streams a placeholder run end to end. Verified the SSE wire to a client.

### Component re-audit — 2026-06-11

Re-checked every component against the current field before building further.
Five changed:

- Decision graph moved from Neo4j to an in-process NetworkX graph with NumPy
  cosine — at ~19 nodes a graph server is pure friction, so this removes a Docker
  service entirely. Tore down the Neo4j container and image.
- Added a thin DoWhy causal layer to the simulation for real `do()` futures.
- Folded red-teaming into `azure-ai-evaluation[redteam]`; added DeepEval as an
  offline fallback.
- Dropped Static Web Apps — the frontend will deploy as a second container app.
- Added a local Arize Phoenix trace UI alongside App Insights.

Updated dependencies and re-locked. Orchestration (Agent Framework) and the
frontend stack were confirmed unchanged.

### Phase 0 complete — 2026-06-11

- Built the Next.js console (App Router, Tailwind v4): it POSTs the intercepted
  action and renders each pipeline step live as it streams in, with the
  running → done reconciliation matching the backend contract.
- Wrote the SSE client as a streamed fetch reader over the plain `data:` frame
  format — the raw transport the architecture calls for, and a clean seam for
  richer stream rendering later.
- Verified the whole local pipe end to end: browser console → backend → the
  six-step stream → live render, with CORS scoped to the dev origin. The
  placeholder pipeline runs guard → retrieve → trace → lesson → grounding →
  simulate → trust → approval → done.
- Patched the Next.js security advisory and moved to Recharts 3. Ran the console
  on port 3100 to avoid a collision with another local app.

Phase 0 exit met: a clone-and-run skeleton that streams end to end, on a
region-verified Azure footprint. Next up is Phase 1 — the live Foundry IQ
retrieval and the safety spine.

### Phase 1 — the live pipeline — 2026-06-11

- Wired the real pipeline end to end on Azure: Content Safety prompt shields
  (direct + indirect), Foundry IQ agentic retrieval over the blob knowledge base
  (query planning, reranked precedents, citations), the in-process graph trace,
  gpt-4o-mini lesson extraction, and the Content Safety groundedness gate.
  Abstains when there's no precedent. All keyless.
- Reviewed and corrected an earlier key-based detour: stripped the keys, switched
  the search service to RBAC auth, went fully keyless.
- Composed an initial trust score from retrieval confidence + grounding.

### Phase 2 — reasoning depth — 2026-06-11

- Built the counterfactual simulation: the model proposes scenario levers under a
  strict schema (never figures), a seeded Monte Carlo over a transparent cost
  model produces P10/P50/P90 bands, and a DoWhy causal model quantifies the
  do()-effect of the dependency lever. The recommendation refuses any high-risk
  future and picks the best risk-adjusted one — the guardrail declining the
  catastrophic tail even when its median leads. Every run carries a seed manifest.
- Completed the trust score with a third signal (how decisively the recommended
  future beats the safe alternatives).
- Re-expressed the pipeline as a Microsoft Agent Framework workflow graph — six
  typed executors, edges, and a human-in-the-loop pause via ctx.request_info —
  exposed at /invoke-workflow alongside the plain-async /invoke.
- Added an evaluation scorecard (Azure AI Evaluation, keyless): groundedness
  ~4.2/5 and relevance ~4.4/5 over a fixed set of decision cases, both passing.
  Committed so the reliability evidence is in the repo.
- Red-teaming deferred: the AI Red Teaming Agent needs a cloud Foundry project
  and pulls PyRIT, which risks a clash with the agent stack. Roadmap.

### Phase 3 — the console — 2026-06-11

- Rebuilt the frontend from the single live step-list into a command-center
  grid: the cited lesson (with the [ref_id] citations rendered as chips that
  highlight the precedent they rest on), a React Flow graph of the retrieved
  precedents and the outcomes they led to, the three-futures simulation as
  P10–P90 range bands with the recommended future called out, a trust gauge that
  shows the three weighted signals behind the score, and the human approval gate.
- Made the headline beat real rather than scripted: the intercepted action
  carries a dependency level, and that number now drives the simulation — it
  anchors the "approve" future's concentration risk. Drag the lever across the
  70% knee, re-run, and the recommendation flips (modify → approve) because the
  tail risk actually changes. Verified end to end through Azure: full
  consolidation gets a "modify", capping below the knee gets an "approve".
- Drew the outcome bands ourselves in SVG instead of through the chart library.
  A future's bad case can be deeply negative while its good case is a modest
  gain, and a stacked bar can't render a range that crosses zero — the
  catastrophic tail was rendering invisible. The hand-drawn scale shows it.
- Trimmed the frontend dependencies to what's actually imported (dropped the
  charting library and the icon set once the panels were hand-built), which also
  cleared a transitive advisory. Bumped PostCSS off the flagged version.
- Re-checked the frontend stack against the current field before building:
  React Flow and the rest held; the one charting alternative worth considering
  was unmaintained, so it was a non-starter.
