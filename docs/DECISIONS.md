# Decision log

Short records of the choices that shaped JANUS and, just as importantly, the
things we decided *not* to build. Newest at the top.

---

## Re-audited every component against the full field; five changed

Before committing to the build we re-checked each component against the current
field of alternatives rather than trusting the first pick. Seven components, each
surveyed wide and then challenged by a second reviewer. Five changed.

- **Graph: Neo4j → NetworkX (in-process).** This is the big one. The graph is
  ~19 hand-curated nodes. The only technical reason to run a graph server is the
  vector index — and at that scale a brute-force cosine in NumPy is exact and
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
  from a literal `do()` intervention on the lever graph — earning the word
  "counterfactual" rather than implying it. (A SALib Sobol offline sensitivity
  panel was considered and cut to keep the live path and the dependency tree
  lean.)
- **Safety: keep one Azure-native spine.** Content Safety groundedness + Prompt
  Shields on the live path; the offline scorecard uses the same Content-Safety-
  aligned groundedness via `azure-ai-evaluation`. Red-teaming (AI Red Teaming
  Agent / PyRIT) is roadmap — it needs a cloud Foundry project and risks a
  dependency clash with the agent stack, so it's planned, not on the live path.
- **Infra: drop Static Web Apps.** Host the Next.js console as a second container
  app in the same `azd` environment as the API. One deploy target, one identity
  model, fewer moving parts, and no question about Vercel's non-commercial terms
  on a public repo.
- **Observability: dual OpenTelemetry sink.** A local Arize Phoenix exporter gives
  an on-camera trace UI (App Insights has a 1–3 min ingestion lag, too slow to
  show live); Azure Monitor / App Insights is the production sink. OpenAI is
  auto-instrumented via OpenInference. Both sinks are optional — no collector
  configured means spans are recorded but not shipped, so the app runs identically
  with or without one.

Confirmed unchanged after the audit: **Microsoft Agent Framework** for
orchestration. Note: the `agent-framework-azure-ai-search` Foundry bridge turned
out not to expose the activity/citation detail, so the retrieval path is the raw
`KnowledgeBaseRetrievalClient`; the bridge survives only as a version pin. The
frontend is **Next.js + React Flow + hand-built SVG** (a charting library and AI
Elements were both dropped once the panels were hand-built — fewer dependencies,
and the hand-drawn charts render an outcome range that crosses zero).

The biggest residual risk surfaced by the audit: the agentic-retrieve API is
pre-release, and the mandatory IQ integration rides on it. Pin the SDK,
smoke-test the citation path on day one, and capture a real response as a replay
fixture for the demo.

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
only proposes bounded levers; a seeded deterministic Monte Carlo over a transparent
cost model computes everything. Same inputs reproduce the same output, and moving
the dependency lever provably moves the result across the concentration knee. That
lever is the action's actual parameter (operator-set), not an LLM output, so the
flip is a real causal response. The reproducible seed and run manifest are the
proof. A DoWhy `do()` intervention adds the literal counterfactual contrast.

### Decision graph: in-process NetworkX, not a graph server

After the re-audit (top of this log) the graph moved from Neo4j to an in-process
NetworkX `DiGraph`. At ~19 curated nodes a graph server earns nothing — the only
technical pull was a vector index, and brute-force cosine over that many vectors is
exact and sub-millisecond. Neo4j would have contributed a JVM container, a
startup health-gate, and a demo-day failure surface and nothing else. The graph
holds the decision→outcome→principle structure that flat retrieval can't express
(IQ retrieves prose; the graph holds the links), loaded from the corpus
frontmatter and rendered straight into React Flow. A `GraphStore` seam keeps a
server swap one class away if scale ever changed.

### Frontend: Next.js + React Flow + hand-built SVG

The console binds to an SSE stream of typed step events from the Python backend —
no Node agent loop, one source of run state. Panels are built on Tailwind v4, with
React Flow for the precedent graph and hand-drawn SVG for the outcome bands and the
trust gauge. A charting library (and Vercel AI Elements) were both dropped once the
panels were hand-built: fewer dependencies, and the hand-drawn band chart renders
an outcome range that crosses zero — which a stacked bar can't.

### Safety: one Microsoft-native spine

Content Safety groundedness drives abstention (binary mode today; segment-level
reasoning mode is roadmap, gated by a model-deprecation issue); Prompt Shields
screen the action *and* the retrieved docs; the offline eval harness uses a
separate LLM judge (azure-ai-evaluation's GroundednessEvaluator) over the same
lesson-vs-sources task, so the scorecard is a correlated proxy for the live gate,
not an identical measurement of it. An unaudited guardrail is a red flag, so a
committed red-team probe (`janus.scripts.red_team`) fires direct and indirect/XPIA
injections at the Prompt Shields and records the block rate
(`data/eval/redteam.json`). The cloud AI Red Teaming Agent remains roadmap — it
needs a cloud Foundry project and risks a dependency clash.

### Infra: FastAPI + uv, azd to Container Apps

FastAPI is the framework in Microsoft's own Foundry samples and its OpenAPI surface
is how a Foundry agent would call us. `azd up` makes the cloud deploy real and
reproducible — a Container Apps environment hosting both services, a user-assigned
managed identity with the data-plane roles, Key Vault, and Application Insights,
all from Bicep. The video records off localhost so a cold start is never the first
impression. Static Web Apps was dropped: hosting the console as a second container
app means one deploy target and one identity model.

---

## Things we deliberately cut

| Cut | Why it's safe |
|-----|---------------|
| Real Teams/Outlook/Fabric ingestion | Paywalled / post-deadline / undemoable; synthetic corpus is the right call anyway |
| Durable workflow checkpointing | The framework's checkpointing re-runs the first step and re-rolls the sim on resume; roadmap |
| A charting library (Recharts/Tremor) | Hand-built SVG renders a range that crosses zero and removes a dependency; Tremor is React-18-only/unmaintained |
| Vercel AI Elements | Once the panels were hand-built it added a dependency for no gain; the SSE console is native |
| PyMC / Bayesian simulation | Heavier, sampler-tuning risk; the seeded Monte Carlo is enough and is reproducible |
| Neo4j (graph server) | At ~19 nodes brute-force cosine is exact and sub-ms; the server is pure friction and a failure surface |
| Red-team ASR artifact (live) | Needs a cloud Foundry project and risks a dependency clash with the agent stack; roadmap |
| Content Safety auto-correction | Preview; we need detect-and-explain, which is GA |
| Static Web Apps | The console ships as a second container app — one deploy target, one identity model |
| Multi-scenario breadth | One polished scenario end to end beats a generic pipeline |
| Scale-to-zero for the demo | Would evict the in-memory workflow across the approval round-trip; `min-replicas=1` |
