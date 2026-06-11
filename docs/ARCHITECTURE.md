# JANUS — Architecture

_Last updated: 2026-06-11. Versions verified current as of June 2026._

This document pins the stack, explains why each piece was chosen over its closest
alternative, and records the edge cases and integration seams that the design has
to respect. It is the reference the build follows.

## 1. Shape of the system

JANUS is a deterministic six-step pipeline that sits between an autonomous agent
and the action it wants to take. A Python service runs the pipeline; a Next.js
console renders it as it happens. Foundry IQ is the one real Microsoft
intelligence layer. Everything else is chosen to keep that integration central
and the reasoning visible.

```
                         JANUS interception pipeline
  ┌──────────────────────────────────────────────────────────────────────┐
  │  proposed action (JSON: action, params, rationale)                     │
  │        │                                                               │
  │        ▼                                                               │
  │  [1] GUARD ─ Content Safety Prompt Shields (direct + indirect/XPIA)    │
  │        │     screens the action AND the docs we're about to read       │
  │        ▼                                                               │
  │  [2] RETRIEVE ─ Foundry IQ knowledge base / Azure AI Search agentic    │
  │        │        retrieval. Query planning → ranked precedents +        │
  │        │        reranker scores + [ref_id:N] citations. (THE IQ BEAT)  │
  │        │        below 2.5 floor → ABSTAIN                              │
  │        ▼                                                               │
  │  [3] TRACE ─ Neo4j (neo4j-graphrag-python, Cypher 25 SEARCH clause).   │
  │        │     resolve cited docKeys → traverse decision→outcome→lesson  │
  │        ▼                                                               │
  │  [4] LESSON ─ Microsoft Agent Framework executor (FoundryChatClient).  │
  │        │      one principle, ≥2 sources, every claim cited.            │
  │        ▼                                                               │
  │  [5] GROUNDING GATE ─ Content Safety Groundedness Detection            │
  │        │      (reasoning mode) + Ragas faithfulness (2nd judge)        │
  │        ▼                                                               │
  │  [6] SIMULATE ─ fan out 3 futures. LLM emits levers only; NumPy        │
  │        │        seeded Monte Carlo + SciPy triangular compute numbers; │
  │        │        SALib Sobol tornado. P10/P50/P90 + SHA-256 manifest.   │
  │        ▼                                                               │
  │  [7] TRUST SCORE ─ reranker confidence + grounding + sim agreement     │
  │        ▼                                                               │
  │  [8] HITL GATE ─ pause. human approves / rejects. NEVER auto-executes. │
  └──────────────────────────────────────────────────────────────────────┘

  Orchestration spine:  Microsoft Agent Framework Workflows (graph API)
  Backend:              FastAPI + Pydantic v2, managed with uv
  Frontend:             Next.js 15 + shadcn/ui + AI Elements + React Flow 12
  Observability:        OpenTelemetry → Azure Monitor / Application Insights
  Roadmap (drawn, not built): Work IQ + Fabric IQ as added knowledge sources;
                              durable checkpointing; probabilistic simulation
```

## 2. The chosen stack

_Every choice below was re-audited against the full field of current alternatives
(see `docs/DECISIONS.md`). Five components changed in that audit; those rows are
marked ‡._

| Layer | Choice | Pinned | Closest alternative (and why not) |
|-------|--------|--------|-----------------------------------|
| Orchestration | Microsoft Agent Framework, Workflows graph API; FoundryChatClient executors; first-party `agent-framework-azure-ai-search` Foundry bridge | `agent-framework==1.8.x`, bridge pinned `--pre` | LangGraph 1.2 — co-equal on graphs/HITL, but third-party with no Foundry bridge; demotes Foundry to a bolt-on |
| Retrieval (the IQ layer) | Foundry IQ knowledge base on Azure AI Search agentic retrieval, 2026-05-01-preview retrieve action | pinned `--pre azure-search-documents` build | Hand-rolled hybrid pipeline — loses the mandatory-IQ point. Kept as the fallback adapter behind the retrieval interface. |
| Decision graph ‡ | **NetworkX in-process typed DiGraph + NumPy brute-force cosine** | `networkx>=3.4` | Neo4j/Memgraph — a graph server earns nothing at 40 nodes (brute-force cosine is exact and sub-ms); pure setup friction + a demo-failure surface. Kuzu archived Oct 2025. Thin `GraphStore` interface keeps a server swap one class away. |
| Simulation ‡ | LLM emits levers only + deterministic NumPy Monte Carlo, SciPy triangular; thin **DoWhy GCM** for literal `do()` counterfactuals | NumPy 2.x, SciPy 1.15, DoWhy 0.12+ | SALib Sobol kept as an optional offline panel, off the live path; PyMC Bayesian is roadmap |
| Frontend | Next.js 15 + shadcn/ui + Vercel AI Elements (AI SDK 6) + React Flow 12 + Recharts v3 | AI SDK 6 GA, `@xyflow/react` 12.11 | assistant-ui — strong, but AI Elements ships the citation/chain-of-thought/tool components we need out of the box. Tremor excluded; Recharts is the sole chart lib. |
| Safety + eval ‡ | Content Safety Groundedness + Prompt Shields + **azure-ai-evaluation `[redteam]`** (wraps PyRIT) + Ragas + DeepEval fallback | `azure-ai-evaluation>=1.17` | Standalone PyRIT folded into the eval package; NeMo/Guardrails-AI lose the Azure-native narrative. Foundry project pinned to East US 2 (region-locked previews). |
| Backend / infra ‡ | FastAPI + Pydantic v2 + uv; azd → Container Apps hosting **both** services; Key Vault + managed identity | FastAPI 0.136.x, uv 0.7.x | Static Web Apps dropped — hosting the frontend as a second container app means one deploy target, one identity model, and no Vercel-ToS question |
| Observability ‡ | OpenTelemetry, dual sink: Azure Monitor/App Insights + local **Arize Phoenix** trace UI | `arize-phoenix-otel`, `openinference-instrumentation-openai` | App Insights alone has 1–3 min ingestion lag — too slow for a live demo; Phoenix is the on-camera trace UI, App Insights the cited production sink |

## 3. Why these, specifically

**Orchestration — Microsoft Agent Framework.** JANUS is a fixed six-step
pipeline, not an open-ended autonomous agent. That is exactly the case
Microsoft's own docs say to model as a *workflow*, not an agent: well-defined
steps, explicit control over execution order. The graph API gives typed message
routing, conditional edges (the abstain branch), fan-out/fan-in (the three-future
simulation), and a human-in-the-loop request primitive that maps one-to-one onto
"never auto-executes." It is the first-party SDK for Azure AI Foundry Agent
Service, it emits OpenTelemetry traces into Foundry Observability with no extra
wiring, and it is the GA successor that absorbed AutoGen and Semantic Kernel
(both now maintenance-only — reaching for them would signal we missed the
convergence). For a panel of Microsoft product teams on the Foundry track, this
keeps Foundry at the architectural center rather than bolting it on.

**Retrieval — Foundry IQ agentic retrieval.** This *is* Foundry IQ's engine, so
using it is the most authentic possible integration, not a wrapper around one.
One API call delivers four things the rubric rewards: query planning (visible
subquery decomposition — the multi-step reasoning beat), grounded synthesis with
inline `[ref_id:N]` citations (accuracy), reranker scores in the activity array
(the ranked-list-with-near-misses beat), and a documented abstention pattern
(reliability). The synthesis and planning visibility are preview-only; the client
is built behind an interface that degrades to the GA extractive path, and the
recorded demo replays a real captured response so a preview hiccup can't ruin it.

**Decision graph — Neo4j, kept deliberately small.** The graph is 20–40
hand-curated typed nodes (decision / failure / principle / lesson) with typed
edges (caused / prevented / contradicted / reinforced) and temporal properties
(`valid_from` / `valid_until` / `superseded_by`) that make contradiction
detection and staleness first-class. It does not overlap Foundry IQ: IQ does
unstructured semantic retrieval over prose; Neo4j holds the structured
decision→outcome→principle causality that flat retrieval can't express. The flow
is IQ-first (find candidate precedents) then graph-second (traverse their
outcomes). All vector retrieval is written against the Cypher 25 SEARCH clause —
the legacy `db.index.vector.queryNodes` procedures were deprecated in 2026.04 and
would look dated on camera.

**Simulation — numbers the judges can't dismiss as fake.** The failure mode to
avoid is hand-authored figures. So the language model never emits a final number;
it emits qualitative levers and bounded parameters under a JSON schema, and a
seeded deterministic Monte Carlo over a transparent cost model computes
everything. Identical inputs reproduce identical output; changing an input
provably moves the result; a SALib Sobol tornado shows which input drives the
spread. Every run is hashed into a manifest. This is the rare hackathon claim
that is independently reproducible.

**Frontend — the biggest accelerant available.** Vercel AI Elements ships, on top
of shadcn/ui, exactly the components JANUS needs: a chain-of-thought step log,
tool-call display, source pills with inline citations, task progress. They bind
directly to an SSE stream of custom data parts coming from the Python backend, so
the console reads as native and there's no Node agent loop to maintain. React
Flow renders the decision graph; Recharts renders the confidence bands.

**Safety — one Microsoft-native story, all GA.** Content Safety Groundedness
Detection (reasoning mode) flags ungrounded segments of an extracted principle
and drives abstention. Prompt Shields screen both the action and the retrieved
docs. The offline azure-ai-evaluation harness uses the *same* Content-Safety
backed groundedness service, so the README scorecard and the live gate measure
the same thing — no drift between eval and production. A local PyRIT red-team scan
produces an attack-success-rate slide: a guardrail that hasn't been attacked is a
red flag, so we attack our own.

**Infra — Microsoft-native and demo-proof.** FastAPI is the framework in
Microsoft's own Foundry Agent Service Python samples; its OpenAPI surface is how
a Foundry agent would call JANUS. `azd up` provisions Container Apps + Static Web
Apps + Key Vault + managed identity from one command, so the repo demonstrates
real, reproducible IaC. The deployed app exists for credibility; the recorded
video runs off localhost so a cold start can never be the first impression.

## 4. The non-obvious integration seams

These are the places where two layers interact in a way that isn't visible from
either one alone. The build must respect all of them.

1. **One agent loop only.** The Microsoft Agent Framework workflow in Python is
   the sole orchestrator. Next.js is a pure presentation client over SSE. We do
   not add a Node agent loop to borrow the AI SDK's approval primitive — that
   would create two sources of run state and a second runtime.

2. **Workflow state across the approval round-trip (the #1 risk).** Resuming a
   paused workflow needs the *same in-memory workflow object*. But "approve" is a
   second HTTP request, and scale-to-zero or a second replica would evict that
   object between the two requests. Solution: FastAPI holds a server-side run
   registry keyed by run id; the demo runs with `min-replicas=1` and a single
   revision; the recording runs on localhost. We do **not** rely on workflow
   checkpointing for this — it re-runs the first executor on resume and re-rolls
   the simulation, so it is roadmap, not a demo feature.

3. **Preview vs GA silent downgrade.** Query-planning visibility and synthesized
   citations exist only in the preview API. If the client falls back to GA, those
   two beats vanish. The client detects the missing activity records and visibly
   flags "GA fallback" rather than showing a quietly degraded trace. The
   citation array and reranker gating exist in both, so those beats survive a
   fallback.

4. **Deterministic seeding under fan-out.** Each simulation branch seeds its RNG
   from the run id, not a global seed, so if the framework re-executes a branch
   the numbers reproduce exactly. The seed goes in the run manifest.

5. **Package fragility.** Pin `agent-framework==1.8.1`, the tested `--pre`
   `azure-search-documents` build that exposes the messages-input client, and a
   `neo4j-graphrag-python` release that has adopted the SEARCH clause. Keep the
   alpha CodeAct/hyperlight packages out of the critical path.

## 5. Edge cases the system must handle

- **No precedent.** Retrieval returns nothing above the reranker floor → abstain,
  depress the trust score, recommend human review. Never fabricate a lesson. This
  is the single most important credibility moment.
- **Hallucinated lesson.** The grounding gate (Groundedness Detection + Ragas)
  flags ungrounded segments; the UI surfaces the flagged span rather than
  presenting the lesson as authoritative.
- **Indirect prompt injection via org history.** Retrieved decision docs are
  untrusted; Prompt Shields screen them, not just the action.
- **Partial retrieval.** A knowledge source error returns partial content; for
  compliance-critical sources, fail loud and abstain rather than ground on an
  incomplete evidence set.
- **Conflicting precedents.** Two equally-similar past decisions with opposite
  outcomes → surface both with their weights; do not average them into a
  misleading single answer.
- **Contradiction and staleness.** A new outcome that opposes a prior principle
  creates a `contradicted` edge; expired/superseded principles are down-weighted
  and badged in the UI; lineage stays auditable.
- **HITL abandonment / double-click.** The run registry is idempotent on resume
  and times out abandoned runs.
- **Demo-day failure.** Defense in depth: record on localhost; every external
  call has a committed real-captured fixture; `min-replicas=1`; the eval
  scorecard, red-team slide, and groundedness screenshots are committed so the
  reliability artifacts exist even if a live run is flaky.

## 6. Risk register (load-bearing first)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Workflow state lost across the approval round-trip | High | Server-side run registry; `min-replicas=1`; record on localhost |
| Headline reasoning beat depends on a no-SLA preview API | High | Replay a real captured fixture in the video; keep live path wired; detect + flag GA downgrade |
| Azure region / quota / RBAC friction in the final 72h | High | Verify one region supports all services on day 0; run eval + red-team day 1; commit artifacts |
| Package fragility across the Python agent stack | Medium | Pin all three; write SEARCH-clause Cypher from line one; smoke-test day 0 |
| Custom HITL gate under-budgeted (~half a day) | Medium | Explicit Phase-3 budget; not promised as a built-in |
| Overclaiming the simulation citation to a panel that will read it | Medium | Cite the paper as inspiration; the seeded RNG + manifest is the real proof |
| Indirect injection through org history | Medium | Prompt Shields on retrieved docs; synthetic-only corpus |
| Scope creep across six layers in three days | Medium | Enforce the cut list; one scenario end to end beats breadth |

## 7. What is explicitly cut (and why it's safe to cut)

Recorded in `docs/DECISIONS.md`. In short: Work IQ / Fabric IQ (roadmap, plug
into the same knowledge base later), durable checkpointing (roadmap), the AI SDK
approval primitive (hand-rolled instead), PyMC (roadmap), Neo4j NVL (optional
flourish), cloud red-teaming (local scan instead), hybrid SSR on Static Web Apps
(static export instead), and multi-scenario breadth (one polished scenario plus
one or two canned secondaries).

## 8. Verdict

The stack is coherent, current as of June 2026, and maps directly onto the
rubric. There is exactly one non-obvious load-bearing seam — workflow state
across the approval round-trip — and the design respects it. With the cut list
enforced and the IQ and safety beats built first, this is buildable in three days
and competitive on Reasoning, Reliability & Safety, and Creativity.
