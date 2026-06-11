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

_Remaining Phase 0: synthetic corpus, backend skeleton, docker-compose, the
end-to-end SSE smoke test._
