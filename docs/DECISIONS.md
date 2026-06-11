# Decision log

Short records of the choices that shaped JANUS and, just as importantly, the
things we decided _not_ to build. Newest at the top.

---

### Re-audited every component against the full field; five changed

Before committing to the build we re-checked each component against the current
field of alternatives rather than trusting the first pick. Seven components, each
surveyed wide and then challenged by a second reviewer. Five changed.

- **Graph: Neo4j → NetworkX (in-process).** This is the big one. The graph is
  ~40 hand-curated nodes. The only technical reason to run a graph server is the
  vector index — and at 40 vectors a brute-force cosine in NumPy is exact and
  sub-millisecond, so the index earns nothing. That left Neo4j contributing only
  a JVM container, a startup health-gate, and a demo-day failure surface. An
  in-process NetworkX typed graph gives the same typed nodes, typed edges, and
  traversal, serializes straight to the React Flow render, and adds no service. A
  thin `GraphStore` interface keeps a server swap one class away if scale ever
  changed. (Kuzu, the embedded-Cypher option, was eliminated — archived October
  2025; its forks are all under a year old. Memgraph is healthy but still a
  server we don't need.)
- **Simulation: add a thin DoWhy causal layer.** The seeded Monte Carlo stays,
  but we add a small DoWhy graphical-causal-model step so the three futures come
  from literal `do()` interventions on the lever graph — earning the word
  "counterfactual" rather than implying it. SALib's global sensitivity moves to
  an optional offline panel, off the live path.
- **Safety: fold red-teaming into the eval package.** Standalone PyRIT becomes
  `azure-ai-evaluation[redteam]` (the AI Red Teaming Agent wraps PyRIT) — one
  Azure-native package instead of two tools. DeepEval added as an offline
  fallback scorer. The Foundry project is pinned to East US 2 because the
  groundedness and red-team previews are region-locked.
- **Infra: drop Static Web Apps.** Host the Next.js frontend as a second
  container app in the same `azd` environment as the API. One deploy target, one
  identity model, fewer moving parts, and no question about Vercel's
  non-commercial terms on a public repo.
- **Observability: add a local trace UI.** App Insights stays as the
  Azure-native sink but has a 1–3 minute ingestion lag — too slow to show live.
  A parallel OpenTelemetry exporter to a local Arize Phoenix container gives an
  on-camera trace UI, with OpenInference instrumentation so the LLM steps render
  richly.

Confirmed unchanged after the audit: **Microsoft Agent Framework** for
orchestration (it uniquely ships a first-party Foundry IQ bridge — the audit
actually strengthened this pick) and the **Next.js + AI Elements + React Flow +
Recharts** frontend.

The biggest residual risk surfaced by the audit: the Foundry IQ bridge package
is pre-release, and the mandatory IQ integration rides on it. Pin it exactly,
smoke-test the citation path on day one, keep the raw-SDK adapter as a fallback,
and do not upgrade it once it's green.

---

### Foundry IQ is the one real IQ integration; Work IQ and Fabric IQ are roadmap

We need at least one Microsoft IQ layer, and it has to be real — the judges built
these APIs. Foundry IQ (agentic retrieval) is GA, has a free-to-cheap path, and
runs over a corpus we control. Work IQ needs a paid Copilot add-on and its API
goes GA after our deadline; Fabric IQ needs a paid capacity and ontology setup.
Both would end up as stubs. They plug into the same knowledge base later with no
code change, so the roadmap is honest, not vaporware. One integration shown
working beats three half-wired ones.

### Reasoning Agents track, not Enterprise Agents

The Enterprise/M365 track effectively forces a Copilot-licensed tenant and the
Work IQ path. The Reasoning track maps cleanly onto our multi-step decision
pipeline on Foundry, hits the reasoning rubric directly, and is still eligible for
the IQ-tools award.

### The product is interception, not retrieval

Plenty of teams will build "ask the org's history a question." That's a crowded
bucket and it's the wrong moment — the agent has usually already decided. We
position JANUS as a guardrail that evaluates a *proposed action* before execution.
That verb is the differentiator; everything else serves it.

### Microsoft Agent Framework for orchestration

JANUS is a fixed six-step pipeline, which is the textbook "use a workflow, not an
agent" case. The Agent Framework Workflows graph API gives deterministic edges,
fan-out/fan-in for the simulation, and a human-in-the-loop primitive, and it's the
first-party Foundry SDK with free OpenTelemetry tracing. LangGraph was the runner-
up — a hair more battle-tested, but third-party, and it would demote Foundry to a
bolt-on. AutoGen and Semantic Kernel are now maintenance-only after converging
into the Agent Framework; using them directly would signal we missed that.

### The simulation computes its own numbers

Hand-authored figures are the number-one tell of a faked agent demo. So the model
only proposes levers; a seeded deterministic Monte Carlo over a transparent cost
model computes everything. Same inputs reproduce the same output, changing an
input provably moves it, and a sensitivity tornado shows which input drives the
spread. We cite the paper that inspired this as *inspiration only* — its own model
has the LLM emit the values, which is not what we do, and a judge who opens the
PDF would catch an overclaim. The reproducible seed and run manifest are the real
proof.

### Neo4j for the decision graph, kept small

A typed graph of 20–40 curated nodes, queried at action time and rendered live.
Neo4j is credible to this judge pool, has a native vector index, and a first-party
GraphRAG retriever that does exactly our embed-then-traverse move. It does not
overlap Foundry IQ — IQ retrieves prose, the graph holds causal structure. All
vector queries use the current SEARCH clause; the older procedures were deprecated
and would look dated. Memgraph is a genuine drop-in fallback. Kuzu was archived in
late 2025 — ruled out. Cosmos Gremlin is soft-deprecated — ruled out.

### Frontend: Next.js + Vercel AI Elements

AI Elements ships the exact components we need — chain-of-thought, tool calls,
source citations — on top of shadcn/ui, bound to an SSE stream from the Python
backend. It reads as native and saves days. React Flow renders the graph; Recharts
renders the bands.

### Safety: one Microsoft-native spine, all GA

Content Safety groundedness (reasoning mode) drives abstention; prompt shields
screen the action *and* the retrieved docs; the offline eval harness uses the same
groundedness service so the scorecard predicts live behavior. A local red-team
scan produces an attack-success-rate slide — we attack our own guardrail because an
unaudited one is a red flag. We added Ragas as a cheap second grounding judge and
cut Phoenix/Langfuse (Azure Monitor already covers tracing).

### Infra: FastAPI + uv, azd to Container Apps + Static Web Apps

FastAPI is the framework in Microsoft's own Foundry samples and its OpenAPI surface
is how a Foundry agent would call us. `azd up` makes the cloud deploy real and
reproducible. The video records off localhost so a cold start is never the first
impression. The Next.js front end ships as a static export — hybrid SSR on Static
Web Apps is still preview with cold-start issues we won't risk on the demo.

---

## Things we deliberately cut

| Cut | Why it's safe |
|-----|---------------|
| Real Teams/Outlook/Fabric ingestion | Paywalled / post-deadline / undemoable; synthetic corpus is the right call anyway |
| Durable workflow checkpointing | The framework's checkpointing re-runs the first step and re-rolls the sim on resume; roadmap |
| The AI SDK approval primitive | It's a Node-agent-loop feature; we hand-roll the gate as a custom data part instead of adding a second runtime |
| PyMC / Bayesian simulation | Heavier, sampler-tuning risk; the seeded Monte Carlo is enough and is reproducible |
| Neo4j NVL render | Optional on-camera flourish; React Flow is the default |
| Cloud agentic red-teaming | Region-locked and heavy; the local scan produces the same artifact |
| Content Safety auto-correction | Preview; we need detect-and-explain, which is GA |
| Hybrid SSR on Static Web Apps | Preview, cold starts; static export instead |
| Multi-scenario breadth | One polished scenario end to end beats a generic pipeline |
| Scale-to-zero for the demo | Would evict the in-memory workflow across the approval round-trip; `min-replicas=1` |
