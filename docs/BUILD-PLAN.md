# JANUS — Build Plan (internal)

_Working document. Updated as phases close. This is the plan we follow; it is not
a submission artifact._

The whole game is: one scenario, end to end, nothing faked on the demo path. The
two most-scored and highest-risk pieces — the real IQ integration and the safety
spine — get built first, so by end of day 1 the things that can sink us are
proven. Everything is recorded on localhost; every external call gets captured to
a fixture so a flaky network in the final stretch can't ruin the video.

Deadline: 2026-06-14 23:59 PT.

---

## Phase 0 — de-risk and provision (half day, day 0)

Goal: kill the region / version / availability landmines before writing pipeline
code, and stand up a skeleton that already streams end to end.

- [ ] Find ONE Azure region that co-supports agentic retrieval + the GPT
      planning model + Content Safety groundedness + prompt shields. Verify
      before building — these are region-gated and don't co-locate everywhere.
- [ ] Provision Azure AI Search (Basic tier — Free has no managed identity for
      the search service to call the model). Set `knowledgeRetrieval=standard`.
- [ ] Lock dependencies: `agent-framework==1.8.1`, the tested `--pre`
      `azure-search-documents`, `neo4j-graphrag-python` (SEARCH-clause release),
      AI SDK 6, React Flow 12, `uv` 0.11.x. Commit the lockfiles.
- [ ] Neo4j 2026.05.0 in Docker. Smoke-test the exact VectorCypherRetriever
      SEARCH-clause query against it — confirm no deprecated `queryNodes`.
- [ ] Repo: push protection on, Key Vault + user-assigned managed identity,
      `docker compose` for api + web + neo4j, `.env.example` with empty keys.
- [ ] Hello-world SSE: FastAPI streams a custom data part, Next.js `useChat`
      renders it. This is the pipe everything else flows through.
- [ ] Author ~30 synthetic decision docs (transcripts, postmortems, policies,
      two CSVs). No PII. This is the corpus.

Exit: a clone-and-run skeleton that streams a placeholder step from backend to
browser, and a provisioned, region-verified Azure footprint.

## Phase 1 — IQ visible early, safety built in (day 1)

Goal: prove the mandatory integration and the riskiest axis on day 1.

- [ ] Live preview retrieve working end to end over the seeded knowledge base:
      synthesized answer + `[ref_id:N]` + activity array with the query plan +
      references + 2.5 reranker gating.
- [ ] Thin retrieval client with the GA fallback and downgrade detection.
- [ ] **Capture a real preview response to a fixture** for the recording.
- [ ] Prompt Shields + Groundedness Detection wired and returning real verdicts.
- [ ] Run the `azure-ai-evaluation` harness once over the test set; commit the
      scorecard JSON.
- [ ] Seed Neo4j with the decision → outcome → principle graph; confirm
      VectorCypherRetriever returns real paths from cited docKeys.

Exit: retrieval is real and on screen; the safety verdicts are real; the
scorecard exists in the repo.

## Phase 2 — the spine, the simulation, the trust score (day 2)

Goal: assemble the six steps into one orchestrated trace with a real score.

- [ ] Microsoft Agent Framework workflow graph wiring
      guard → retrieve → trace → lesson → grounding-gate → simulate → trust →
      HITL, with FoundryChatClient executors in the LLM steps.
- [ ] Deterministic NumPy Monte Carlo (seeded per run from the run id) + SciPy
      triangular inputs + SALib Sobol tornado → P10/P50/P90 + provenance trace +
      SHA-256 manifest.
- [ ] Ragas faithfulness as the second grounding judge.
- [ ] Composite trust score + the abstain logic.
- [ ] FastAPI run registry holding the live workflow handle across the
      pause/resume round-trip; `min-replicas=1` for the demo.
- [ ] Local PyRIT red-team scan → commit the attack-success-rate slide.

Exit: a single proposed action runs the full pipeline and pauses at the gate.

## Phase 3 — console polish and the gate (day 3, morning)

Goal: make the trace and the human gate genuinely impressive in the browser.

- [ ] Live step-by-step status via same-id data-part reconciliation; citation and
      reasoning parts; React Flow view of the traversed precedents; Recharts
      P10/P50/P90 bands; the trust panel with grounding flags and the GA-fallback
      warning.
- [ ] Hand-roll the HITL gate as a custom data part that pauses the stream;
      approve/reject re-POSTs and resumes the same workflow run. (Budget half a
      day — this is not a built-in.)
- [ ] Demonstrate the abstain path on screen (remove the precedent → JANUS
      refuses to invent a lesson, confidence drops).
- [ ] OpenTelemetry traces visible in Azure Monitor.

Exit: the killer demo runs locally, including the live input-change beat and the
abstain case.

## Phase 4 — deploy as proof, record, submit (day 3, afternoon)

Goal: cloud deploy exists as reproducible IaC; the video is recorded off the
deterministic local path; submission complete.

- [ ] `azd up` deploys the API to Container Apps (`min-replicas=1`, Key Vault,
      managed identity) and the static Next.js export to Static Web Apps.
- [ ] Record the ≤5-minute demo entirely on localhost, replaying captured
      fixtures for any flaky external call.
- [ ] README with the architecture diagram, the hybrid-retrieval rationale, the
      committed eval scorecard + red-team slide + groundedness screenshots, and
      the labeled roadmap.
- [ ] Public repo + diagram + video submitted before the deadline. Post the
      20-second teaser to the community channel.

Exit: submitted.

---

## Standing rules

- One scenario, end to end, nothing stubbed on the demo path.
- IQ and safety first; UI last.
- Every external call has a committed fixture.
- Synthetic data only; no secrets; push protection on.
- Built vs roadmap is labeled everywhere. No claim outruns what runs.
