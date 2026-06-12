# JANUS

**A decision guardrail for autonomous enterprise agents. Everyone else builds a
librarian — this is the guardrail in front of the action.**

Before an AI agent executes a proposed action, JANUS *intercepts* it and hands it
to a **team of six reasoning agents** on a Microsoft Agent Framework workflow.
They retrieve analogous past org decisions and their outcomes through **Foundry
IQ**, trace what happened, ground a cited lesson, simulate three futures, and
return a recommendation — approve, modify, or reject — for a human to sign off.
Knowledge tools answer questions *when asked*; by then the agent has already
decided. JANUS doesn't wait. It is decision support with a human in the loop, and
**by construction it never executes anything on its own.**

![track](https://img.shields.io/badge/Agents_League-Reasoning_Agents-6366f1)
![iq](https://img.shields.io/badge/Microsoft_IQ-Foundry_IQ-22c55e)
![auth](https://img.shields.io/badge/auth-keyless_·_managed_identity-0a3d62)
![license](https://img.shields.io/badge/license-MIT-555)

> Built for the Microsoft Agents League @ AI Skills Fest 2026 — Reasoning Agents
> track. **Foundry IQ** (Azure AI Search agentic retrieval) is the real,
> load-bearing intelligence layer.
> Repo: **[github.com/vighriday/janus](https://github.com/vighriday/janus)**

![The JANUS console at the moment the recommendation is gated — the dependency lever sits past the 70% concentration knee, the futures panel shows the catastrophic tail on full consolidation, a cited lesson with reranker-scored precedents is on the left, and the human approval gate is still pending.](docs/assets/console.png)

## At a glance

- **A multi-agent reasoning team** — six single-responsibility agents (Guard,
  Retriever, Tracer, Lesson, Simulator, Decision) collaborate over typed edges on
  a Microsoft Agent Framework workflow, following a Planner→Executor +
  Critic/Verifier pattern. Any agent can abstain and halt the team.
- **Real Foundry IQ agentic retrieval** — query planning, reranker scores, and a
  `[ref_id]` citation on every claim. Below the reranker floor, it abstains rather
  than guess.
- **A real human-in-the-loop gate** — the Microsoft Agent Framework workflow pauses
  server-side at `request_info`; a second HTTP request resumes the *same* workflow
  object. Double-clicks are idempotent.
- **A provable causal flip** — move one input across the 70% concentration knee and
  the recommendation changes, driven by the simulated tail, not a script.
- **Measured safety, not asserted** — a committed red-team probe: **84.6% injection
  block rate** (direct + indirect/XPIA), **zero false positives** on clean inputs.
- **Grounded and evaluated** — a 22-case scorecard: **4.68 / 5 groundedness** (100%
  pass), **4.36 / 5 relevance** (91% pass).
- **Keyless and deployable** — `DefaultAzureCredential` throughout; `azd up`
  provisions the whole stack from Bicep.

---

## Why this exists

Enterprises are starting to hand operational decisions to autonomous agents. Those
agents inherit the company's documents and data — but not the lessons it learned
the hard way, the constraints that only became visible after something broke. So
they confidently repeat mistakes the organization already paid for, with no memory
that the bill was already settled once.

A retrieval tool would let you *ask* whether this has gone wrong before. JANUS
doesn't wait to be asked — it checks the proposed action against what actually
happened last time, before the agent acts.

**Everyone else builds a librarian. This is a guardrail.**

## What it does — a team of reasoning agents

JANUS is a **multi-agent reasoning system**: six single-responsibility agents
collaborate over typed message edges on a Microsoft Agent Framework workflow,
each owning one reasoning step and handing its typed output to the next. The
roster follows the reasoning patterns the track rewards — a Planner→Executor
decomposition with built-in Critic/Verifier checks — and several agents can
*refuse and halt the team* (abstain, block) rather than push a weak answer
through.

| Agent | Pattern | What it reasons about |
|-------|---------|-----------------------|
| **GuardAgent** | Verifier | Content Safety Prompt Shields screen the action *and* the documents about to be read (direct + indirect/XPIA injection). |
| **RetrieverAgent** | Executor | **Foundry IQ** agentic retrieval plans subqueries, ranks precedents with reranker scores, returns `[ref_id]` citations. Below the floor → abstain. |
| **TracerAgent** | Executor | For each cited precedent, walks its decision → outcome links in the in-process decision graph. |
| **LessonAgent** | Executor + Critic | Synthesises one grounded principle, every claim cited — then *self-verifies* it with Content Safety Groundedness. No support → abstain. |
| **SimulatorAgent** | Executor | Three futures (approve / modify / reject). It proposes only bounded levers; a seeded Monte Carlo computes every number, and a DoWhy `do()` intervention quantifies the causal effect. |
| **DecisionAgent** | Planner / HITL | Composes a trust score from the upstream agents' signals, then **pauses the whole team** for a human to approve or override. Nothing proceeds to execution. |

### The headline beat — why the recommendation flips

The intercepted action carries one bounded lever: **single-vendor dependency
concentration**. The cost model has a non-linear knee at ~70% — below it, a vendor
disruption is absorbable; above it, the seeded Monte Carlo's loss distribution
grows a fat tail that dominates the *approve* branch.

So the flip is mechanical, not theatrical:

| Lever | Simulated tail | Recommendation |
|-------|----------------|----------------|
| dependency **100%** | tail risk above threshold | **MODIFY** (cap below the knee) |
| dependency **60%** | tail risk collapses | **APPROVE** |

Same seed, same code path, one input moved across the knee. The model only
proposes *which* levers exist; every number is computed by the Monte Carlo, and a
DoWhy `do()` intervention isolates the causal effect of the lever. That's the
difference between a guardrail that reasons and a demo that animates.

## Architecture

```mermaid
flowchart TD
    A([Proposed action<br/>from an autonomous agent]) --> G

    subgraph spine["Six reasoning agents · Microsoft Agent Framework workflow"]
        direction TB
        G["GuardAgent<br/>verifier"]
        R["RetrieverAgent<br/>query plan · ranked precedents · citations"]
        T["TracerAgent<br/>decision → outcome graph"]
        L["LessonAgent<br/>cited principle · self-verifies grounding"]
        SIM["SimulatorAgent<br/>3 futures · seeded Monte Carlo · DoWhy do()"]
        H{{"DecisionAgent<br/>trust score · human gate · never auto-executes"}}
        G --> R --> T --> L --> SIM --> H
    end

    CS["Azure AI Content Safety<br/>Prompt Shields · Groundedness"]
    IQ["Foundry IQ<br/>Azure AI Search agentic retrieval"]
    AOAI["Azure OpenAI<br/>gpt-4o-mini · embeddings"]

    CS -. screens .-> G
    IQ == "the IQ integration" ==> R
    AOAI -. extracts .-> L
    CS -. grounds .-> L

    R -- "no precedent" --> AB([ABSTAIN<br/>escalate to a human])
    L -- "insufficient evidence" --> AB
    H --> OUT([Recommendation<br/>for human review])

    classDef azure fill:#0a3d62,stroke:#4a90d9,color:#fff;
    classDef iq fill:#1b4332,stroke:#22c55e,color:#fff;
    classDef gate fill:#3d2c00,stroke:#f59e0b,color:#fff;
    classDef abstain fill:#3d1414,stroke:#ef4444,color:#fff;
    class CS,AOAI azure;
    class IQ iq;
    class H gate;
    class AB abstain;
```

| Layer | Choice |
|-------|--------|
| **Orchestration** | Microsoft Agent Framework — six reasoning agents as typed executors over a Workflows graph, collaborating along typed message edges, with a real `request_info` human-in-the-loop pause |
| **Retrieval (the IQ layer)** | Foundry IQ / Azure AI Search agentic retrieval — query planning, reranker scores, `[ref_id]` citations |
| **Decision graph** | In-process NetworkX (at this scale a graph server is pure friction) |
| **Simulation** | Seeded NumPy Monte Carlo over a transparent cost model + a DoWhy `do()` causal contrast |
| **Safety** | Azure AI Content Safety (Groundedness + Prompt Shields) + a 22-case eval scorecard + a red-team ASR probe |
| **Backend** | FastAPI + Pydantic v2 on uv |
| **Frontend** | Next.js 15 + Tailwind v4 + React Flow, hand-built SVG charts, over Server-Sent Events |
| **Observability** | OpenTelemetry → Arize Phoenix (local) + Azure Monitor (production) |
| **Auth** | Keyless throughout — `DefaultAzureCredential` / user-assigned managed identity |

Full detail and rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
product spec: [`docs/PRD.md`](docs/PRD.md) · decisions:
[`docs/DECISIONS.md`](docs/DECISIONS.md).

### Roadmap (labeled as roadmap throughout)

- **Work IQ** and **Fabric IQ** plug into the same knowledge base as additional
  sources, with no pipeline change.
- Durable, crash-resumable workflow state; probabilistic (Bayesian) simulation;
  groundedness reasoning-mode (gated by a model-deprecation issue); the cloud AI
  Red Teaming Agent. One real integration shown working beats three half-wired.

## Safety & reliability

- **Never executes.** JANUS has no execution capability by construction — it emits
  a recommendation. "Never auto-executes" is structural, not a flag.
- **Abstains on thin evidence.** No precedent above the reranker floor, or a lesson
  the model can't ground, → abstain with a depressed trust score. It never
  fabricates a precedent.
- **Real human gate.** The workflow pauses server-side at the approval gate; the
  console resumes the same run over a second request. Double-clicks are idempotent.
- **Measured, not asserted.** A committed red-team probe
  ([`data/eval/redteam.json`](data/eval/redteam.json)) fires direct and
  indirect/XPIA injections at the shields: **84.6% block rate, zero false
  positives** on clean inputs (a service error counts as *not blocked*, so that's
  a lower bound). The groundedness scorecard
  ([`data/eval/scorecard.json`](data/eval/scorecard.json)) scores **4.68 / 5
  groundedness and 4.36 / 5 relevance** across 22 cases, including the abstain
  ones.

## Data

The decision corpus is **entirely synthetic** — a fictional logistics company,
fictional vendors, generated transcripts, postmortems, and policies. No real
organizational data, no PII, no secrets are committed. Credentials are resolved at
runtime through managed identity; nothing sensitive lives in this repo.

## Running it locally

> Requires Python 3.11+ (managed with [`uv`](https://docs.astral.sh/uv/)), Node
> 20+, and an Azure subscription with Azure AI Search, Azure OpenAI, and Azure AI
> Content Safety. No Docker required for the core demo — the decision graph runs
> in-process.

```bash
# 1. configure — copy the template and fill in your endpoints
cp .env.example .env

# 2. backend (FastAPI) on :8000
cd api && uv run uvicorn janus.app:app --port 8000

# 3. console (Next.js) on :3100, in a second terminal
cd web && npm install && npm run dev
```

Open the console at `http://localhost:3100`. The backend authenticates to Azure
with `DefaultAzureCredential`, so `az login` is enough locally — there are no keys
in the repo or in `.env`.

To index the corpus into a Foundry IQ knowledge base and run the evidence scripts:

```bash
cd api
uv run python -m janus.scripts.index_corpus   # build the knowledge base
uv run python -m janus.scripts.run_eval       # groundedness + relevance scorecard
uv run python -m janus.scripts.red_team       # injection block-rate probe
```

## Deploying to Azure

```bash
azd up
```

provisions, from the Bicep in [`infra/`](infra/), a Container Apps environment
hosting both services behind a **user-assigned managed identity** with the keyless
data-plane role assignments, **Key Vault**, **Application Insights**, and a
container registry — one reproducible command. The existing AI service endpoints
are passed in via `azd env set` (see [`infra/main.parameters.json`](infra/main.parameters.json)).
The deployed app exists for credibility; the demo is recorded on localhost so a
cold start is never the first impression.

## Repository layout

```text
api/     FastAPI service — the JANUS pipeline, clients, simulation, scripts
web/     Next.js console
infra/   Bicep + azure.yaml for `azd up`
data/    synthetic decision corpus + the eval scorecard + the red-team artifact
docs/    PRD, architecture, decisions, changelog
```

## License

[MIT](LICENSE).
