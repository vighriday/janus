# JANUS — Product Requirements

## 1. Summary

JANUS is a decision guardrail for autonomous enterprise agents. When an agent
proposes an action, JANUS intercepts it, retrieves analogous past decisions and
their outcomes from the organization's history, extracts a grounded principle,
simulates the likely futures, scores its own confidence, and hands a
recommendation to a human for approval. It never executes anything itself.

The product is built for the Agents League hackathon (Reasoning Agents track,
Microsoft Foundry). Foundry IQ is the one real intelligence layer. The
submission is a single workflow shown end to end with nothing faked on the demo
path.

## 2. Problem

Organizations are starting to delegate operational decisions to autonomous
agents. Those agents are given the company's documents and structured data, but
not the lessons the company learned through failure — the constraints that only
became visible after something broke. The predictable result is agents that
repeat expensive mistakes with full confidence.

Existing "enterprise knowledge" and "agent memory" tools are retrieval-shaped:
they answer questions when asked. That is the wrong moment. By the time anyone
queries, the agent has usually already chosen. The gap in the market is a system
that sits *in front of* the action rather than waiting to be consulted.

## 3. The one thing that makes this different

Interception, not retrieval. JANUS is an agent-to-agent guardrail: it evaluates
a *proposed action* against recorded outcomes before execution and returns a
warn / modify / block recommendation. "Ask the archive a question" is a crowded
category. "Stop an agent from repeating a known failure" is not.

Everything in the product serves that one verb.

## 4. Goals

| # | Goal | How we know it's met |
|---|------|----------------------|
| G1 | The mandatory Microsoft IQ integration is real and visibly load-bearing | Live Foundry IQ retrieval with visible query planning, scored hits, and citations |
| G2 | The demo cannot be mistaken for a scripted slide deck | Changing an input on screen changes the recommendation, live |
| G3 | Every recommendation is auditable | Every principle and number traces to a source or a seeded formula |
| G4 | The system is safe by construction | Abstains on weak evidence; human-in-the-loop gate; no execution path exists |
| G5 | Buildable and demoable by the deadline | One scenario, end to end, on localhost, nothing stubbed |

## 5. Non-goals (this submission)

- Real ingestion of live Teams / Outlook / SharePoint / Fabric data. The corpus
  is synthetic and seeded. Work IQ and Fabric IQ are roadmap, drawn as roadmap.
- A general ingestion pipeline for arbitrary org data.
- Autonomous execution of any kind. JANUS is decision support.
- Durable, crash-resumable workflow state. Checkpointing is roadmap.
- Bayesian/probabilistic-programming simulation. The shipped engine is a
  seeded deterministic Monte Carlo.

## 6. Users

- **Primary — the agent owner / operator.** A human responsible for an
  autonomous agent's actions. JANUS gives them a defensible reason to approve,
  modify, or reject what their agent wants to do.
- **Secondary — the autonomous agent itself.** JANUS exposes an interception
  endpoint an agent calls before acting; the call returns a recommendation, not
  a green light.
- **Evaluator — the hackathon judge.** Needs to see, in five minutes, that the
  intelligence is real, the reasoning is multi-step, and the safety is genuine.

## 7. The workflow (functional spec)

The product is a six-step pipeline triggered by a proposed action. Each step has
a hard requirement.

1. **Guard.** Screen the proposed action and the retrieved documents for direct
   and indirect prompt injection. Retrieved org-history documents are untrusted
   input — a poisoned record is a real attack surface, not a hypothetical.
2. **Retrieve.** Query the Foundry IQ knowledge base over the seeded decision
   corpus. Must surface: the decomposed subqueries, the ranked precedents with
   their reranker scores, the rejected near-misses, and inline citations. Below
   the confidence floor → abstain.
3. **Trace.** For each cited precedent, traverse its decision → outcome →
   principle links in the decision graph to recover what actually happened
   afterward.
4. **Extract a lesson.** Produce exactly one principle, grounded in at least two
   independent sources, every claim cited. A principle with no supporting
   evidence must be structurally impossible, not merely discouraged.
5. **Simulate.** Generate three futures (approve / modify / reject). The model
   proposes only qualitative levers and bounded parameters; a transparent,
   seeded cost model computes every figure, reported as a P10/P50/P90 band with a
   per-number provenance trace. Identical inputs reproduce identical output.
6. **Score and gate.** Compose a trust score from retrieval confidence,
   grounding, and cross-future agreement. Pause for explicit human approval. No
   path proceeds to execution.

## 8. Hard requirements (the things that win or lose points)

- **R1 — Real IQ.** Foundry IQ retrieval is live and on the critical path. No
  stub stands in for it.
- **R2 — Visible reasoning.** The query plan, the ranked hits, the traversal,
  and the simulation drivers are all rendered, not summarized after the fact.
- **R3 — Input sensitivity.** The recommendation provably responds to input
  changes during the demo.
- **R4 — Grounding and abstention.** Lessons cite their sources; a groundedness
  check runs on every extracted principle; weak evidence lowers the trust score
  and triggers an explicit "insufficient precedent" state.
- **R5 — Human-in-the-loop.** A real pause-and-approve gate. The architecture
  has no execution branch.
- **R6 — No secrets, no PII.** Synthetic corpus only. All credentials
  server-side via managed identity. Push protection on.
- **R7 — Honest scope.** README and diagram mark built vs roadmap. No claim
  outruns what runs.

## 9. Success metrics (judge-facing)

| Rubric axis | Weight | How JANUS earns it |
|-------------|--------|--------------------|
| Accuracy & Relevance | 20% | Real Foundry IQ integration, grounded answers, meets the track |
| Reasoning & Multi-step | 20% | Visible six-step pipeline: query decomposition, graph traversal, a seeded simulation, and a DoWhy `do()` causal contrast |
| Reliability & Safety | 20% | Grounding gate, abstention, direct + indirect injection screening, a real HITL pause-and-resume, a committed 22-case eval scorecard, and a red-team ASR probe |
| Creativity & Originality | 15% | Interception (not retrieval); the live input-change beat |
| UX & Presentation | 15% | One clean console; reasoning shown as it happens |
| Community vote | 10% | A 20-second "agent avoids repeating a $3M mistake" teaser posted early |

## 10. The killer demo (storyboard target)

1. Cold open (10s): an organization already learned this lesson and paid for it;
   everyone who knew it has left; a new agent is about to repeat it.
2. The agent proposes the consolidation. JANUS intercepts.
3. Retrieval runs live — subqueries, ranked hits, near-misses, citations.
4. The traced precedent's outcome appears; the grounded principle is extracted
   with its sources shown.
5. Three futures compute on screen with confidence bands. One number is expanded
   to show its derivation.
6. **The beat:** change the proposal (fewer vendors, lower dependency). The
   recommendation flips, live.
7. Show the abstain case: remove the precedent, watch JANUS refuse to invent a
   lesson and drop its confidence.
8. Human approves at the gate. Close on the counterfactual: this is the failure
   you would have repeated.

## 11. Risks and mitigations

See `docs/ARCHITECTURE.md` §"Risk register" for the full list. The load-bearing
ones:

- **Workflow state across the approval round-trip** — solved with a server-side
  run registry and a single warm replica for the demo.
- **Preview retrieval API on the headline beat** — live path stays wired;
  the recorded video replays a real captured response so a network hiccup can't
  ruin it.
- **Azure region / quota / preview flakiness in the final stretch** — every
  external call is captured to a committed fixture on day one.

## 12. Out of scope, on purpose

The vision is an organization-wide wisdom layer every agent consults before
acting. This submission proves the kernel. The roadmap (Work IQ and Fabric IQ as
additional knowledge sources, durable workflow state, multi-scenario coverage,
probabilistic simulation) is documented and labeled, never demoed as if built.
