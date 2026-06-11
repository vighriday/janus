---
doc_id: NW-2023-1187
doc_type: postmortem
title: Incident Postmortem — Tessell Outage, Peak Dispatch Window
date: 2023-11-22
author: R. Lindqvist (Ops) with IT on-call
team: Operations
severity: SEV-1
tags: [vendor, outage, incident, resilience, dependency, consolidation]
synthetic: true
company: Northwind Logistics (fictional)
related: [NW-2023-0312, NW-2023-0341]
---

# Incident Postmortem — Tessell Outage, Peak Dispatch Window

## What happened

On 2023-11-21, between 06:10 and 11:40, Tessell's routing API was unavailable in
our region. This fell across the morning peak dispatch window. Because carrier
routing had been fully consolidated onto Tessell in June 2023, there was no
fallback path. 2,300+ dispatches were delayed; 410 missed their committed
delivery windows.

## Impact

- Expedited-freight penalties and make-good costs: ~$1.7M
- Two enterprise accounts escalated; one paused expansion
- Estimated revenue impact including churn risk: ~$3.0–3.4M

This single incident erased the better part of one year's consolidation savings.

## Root cause

Direct cause: a Tessell regional failover bug. We could not have prevented their
outage.

Contributing cause — and the one that is ours: total dependency. Before
consolidation, an outage in any one carrier-routing vendor was absorbable by
rerouting through the other two. After consolidation onto Tessell at ~100% of
volume, the same class of outage became unsurvivable. We removed our own hedge.

## What we got wrong

The concentration risk was identified in writing before the decision (see the
March 2023 risk note) and was accepted as a tradeoff for the savings number. The
savings were real but they were front-loaded and visible; the tail risk was real
but deferred and invisible — until it wasn't. We optimized for the number the
board could see.

## Lessons

1. Vendor consolidation that pushes a single external dependency past roughly 70%
   of a critical flow trades a known, recurring resilience hedge for a one-time
   savings number. Below that threshold, savings dominate. Above it, the tail
   risk dominates and the SLA does not cover it.
2. A resilience objection raised before a decision should be costed against the
   tail event, not against the SLA credit. We costed it against the credit.
3. "Managed risk" is not a control. The concentration was labeled a managed risk
   and then no control was put in place.

## Follow-up

Ops and Procurement to draft a standing policy on dependency concentration for
critical vendor flows. (See policy NW-POL-014.)
