---
doc_id: NW-POL-014
doc_type: policy
title: Policy — Dependency Concentration for Critical Vendor Flows
date: 2024-01-10
owner: D. Okafor (VP Procurement)
team: Procurement
status: active
tags: [vendor, consolidation, policy, resilience, dependency, governance]
synthetic: true
company: Northwind Logistics (fictional)
related: [NW-2023-1187]
---

# Policy — Dependency Concentration for Critical Vendor Flows

## Purpose

This policy exists because of the November 2023 Tessell outage (NW-2023-1187),
which converted a one-year consolidation saving into a larger single-incident
loss. It sets a standing limit on how much of a critical flow may depend on one
external vendor.

## Scope

Applies to any vendor consolidation or sourcing decision affecting a *critical
flow* — defined as any process whose interruption during a business-critical
window causes customer-visible failure (carrier routing, payment processing,
warehouse management, customer notifications).

## The rule

1. **70% dependency ceiling.** No single external vendor may carry more than 70%
   of a critical flow's volume without an approved exception. The remaining
   volume must run on a live, warm fallback — not a contractual standby.
2. **Cost the tail, not the SLA.** Resilience tradeoffs in a consolidation
   business case must be quantified against the modeled cost of a peak-window
   failure, not against the vendor's SLA credit.
3. **Exceptions require executive sponsorship.** Exceeding the ceiling requires
   sign-off from the VP of the owning function and a documented, funded
   mitigation. "Managed risk" without a funded control is not an approved
   mitigation.

## Review

Reviewed annually. Any proposed consolidation that would breach the ceiling is
routed to procurement steering with this policy attached.
