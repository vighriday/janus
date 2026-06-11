# JANUS

**A decision guardrail for autonomous enterprise agents.**

Before an AI agent acts, JANUS checks the proposed action against your
organization's recorded past decisions and their outcomes, then warns, modifies,
or blocks it — with every claim cited back to its source. It is decision support,
with a human in the loop. It never executes anything on its own.

> Built for the Agents League hackathon (Reasoning Agents track, Microsoft
> Foundry). Foundry IQ is the real, load-bearing intelligence layer.

---

## Why this exists

Enterprises are starting to hand decisions to autonomous agents. Those agents
inherit the company's documents and data — but not the lessons it learned the
hard way. So they confidently repeat mistakes the organization already paid for.

Most enterprise-knowledge tools answer questions *when asked*. That's the wrong
moment — by then the agent has usually already decided. JANUS doesn't wait. It
sits in front of the action and intercepts it.

Everyone else builds a librarian. This is a guardrail.

## What it does

When an agent proposes an action, JANUS runs six steps:

1. **Guard** — screen the action and the documents it's about to read for prompt
   injection.
2. **Retrieve** — search the organization's decision history with Foundry IQ.
   You can see the query get planned, the ranked precedents with their scores,
   and the near-misses get rejected.
3. **Trace** — for each cited precedent, walk its decision → outcome → lesson
   links to see what actually happened.
4. **Lesson** — extract one grounded principle, supported by at least two
   sources, every claim cited. If the evidence isn't there, it abstains.
5. **Simulate** — model three futures (approve / modify / reject). The model
   proposes the levers; a transparent, seeded cost model computes every number.
   Change an input and the recommendation changes.
6. **Score & gate** — combine the signals into a trust score and pause for a
   human to approve or reject.

## Architecture

```
proposed action
      │
      ▼
[guard] → [retrieve · Foundry IQ] → [trace · graph] → [lesson] →
[grounding gate] → [simulate · 3 futures] → [trust score] → [human approval]
```

- **Orchestration** — Microsoft Agent Framework (Workflows graph API)
- **Retrieval** — Foundry IQ / Azure AI Search agentic retrieval _(the one real Microsoft IQ integration)_
- **Decision graph** — Neo4j
- **Simulation** — seeded NumPy Monte Carlo over a transparent cost model
- **Safety** — Azure AI Content Safety (groundedness + prompt shields) + an eval harness
- **Backend** — FastAPI (Python)
- **Frontend** — Next.js + Vercel AI Elements + React Flow

Full detail and rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Product spec: [`docs/PRD.md`](docs/PRD.md).

### Roadmap (drawn on the diagram, not built here)

- **Work IQ** and **Fabric IQ** plug into the same knowledge base as additional
  sources, with no pipeline change.
- Durable, crash-resumable workflow state.
- Probabilistic (Bayesian) simulation.

One real integration shown working beats three half-wired ones. The roadmap is
labeled as roadmap throughout.

## Data

The decision corpus is **entirely synthetic** — a fictional company, fictional
vendors, generated transcripts, postmortems, and policies. No real organizational
data, no PII, and no secrets are committed. Credentials are resolved at runtime
through managed identity; nothing sensitive lives in this repo.

## Running it locally

> Requires Docker, Python 3.11+ (managed with `uv`), Node 20+, and an Azure
> subscription with access to Azure AI Search and Azure AI Content Safety.

```bash
# bring up the backend, frontend, and graph
docker compose up

# the console is served at http://localhost:3000
```

Configuration goes in `.env` (see `.env.example` for the keys). The backend
authenticates to Azure with `DefaultAzureCredential`, so `az login` is enough
locally — no keys in the repo.

## Deploying

```bash
azd up
```

provisions the API on Azure Container Apps, the console on Azure Static Web Apps,
and the secrets in Key Vault behind a managed identity. The deployment is real
and reproducible; it exists so the system isn't just a local demo.

## Repository layout

```
api/     FastAPI service — the JANUS pipeline
web/     Next.js console
infra/   Bicep + azure.yaml for `azd up`
data/    synthetic decision corpus + the graph seed
docs/    PRD, architecture, decisions, changelog
```

## License

MIT.
