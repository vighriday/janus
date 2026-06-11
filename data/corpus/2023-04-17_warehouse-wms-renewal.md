---
doc_id: NW-WMS-2023-0417
doc_type: decision_memo
title: WMS Contract Renewal — Keeping Granite & Hollowpine in Parallel
date: 2023-04-17
team: Warehouse Operations & Procurement
tags: [wms, vendor-renewal, redundancy, procurement, warehouse]
synthetic: true
company: Northwind Logistics (fictional)
---

## Decision Memo: WMS Renewal

**Decision owner:** Priya Vendantham (VP, Warehouse Ops)
**Co-signed:** Marcus Bell (Procurement), Dana Okoro (IT Infrastructure)

### Decision
We are renewing both warehouse management system (WMS) contracts for a 3-year term: **Granite WMS** (Bldg A1–A4, Memphis + Reno DCs) and **Hollowpine Cloud WMS** (Bldg B1–B2, Columbus DC). We are **deliberately keeping two vendors in parallel** rather than consolidating onto one platform.

### Context
Finance flagged that running two WMS platforms costs us roughly $410K/yr in combined licensing plus ~$95K/yr in duplicated integration maintenance — call it ~$505K all-in. A single-vendor migration was modeled to save ~$180K/yr after year two. On paper, consolidation wins.

We are choosing not to do it, and here is why.

### Rationale
- **Outage isolation.** In Nov 2022, Hollowpine had a 14-hour regional outage. Because Memphis runs on Granite, we kept 61% of outbound volume moving and rerouted priority freight. A single-vendor world would have frozen everything.
- **Negotiating leverage.** Maintaining a live second integration means we can credibly threaten to shift volume. Last renewal, that leverage got us an 8% discount from Granite.
- **Different strengths.** Hollowpine's cloud API handles our e-comm parcel surge well; Granite's on-prem core is faster for palletized industrial freight. Forcing both into one tool degrades one workflow.

### Tradeoffs accepted
We accept the ~$180K/yr premium as an explicit **resilience tax**. We accept carrying two integration skill sets on the IT team (2.0 FTE). We accept that reconciliation reporting stays manual until the Q3 data-warehouse project lands.

### Conditions
Revisit in 2026. If Hollowpine's reliability SLA (currently 99.5%) does not improve to 99.9%, reopen the consolidation question — but toward Granite, not away from redundancy.

**Status: APPROVED.** Contracts countersigned 2023-04-21.
