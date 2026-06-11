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
  cosine — at ~40 nodes a graph server is pure friction, so this removes a Docker
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
