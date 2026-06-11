---
doc_id: NW-2021-0917-FUELCARD
doc_type: decision_memo
title: Single-Sourcing Fleet Fuel Cards to FleetPath — Procurement Decision
date: 2021-09-17
team: Procurement & Fleet Operations
tags: [fuel-cards, procurement, vendor-selection, fleet, cost-savings]
synthetic: true
company: Northwind Logistics (fictional)
---

# Decision Memo: Consolidate Fleet Fuel Cards onto FleetPath

**Decision owner:** Renata Soltys (Director, Fleet Operations)
**Reviewers:** Darnell Whitcomb (Procurement), Priya Anand (Treasury)
**Status:** APPROVED

## Background

We currently run three fuel-card programs across our 214-truck fleet: FleetPath (Western lanes), CardLink Regional (Midwest depots), and a legacy Voss Petroleum card still active at the Tucson yard. Reconciliation takes Treasury roughly 11 hours a month across the three statements, and our rebate tiers are split, so none of the programs hits the volume threshold for the top discount band.

## Proposal

Move all three onto FleetPath, our largest existing program (already ~62% of fuel spend, ~$4.1M annually). Cancel CardLink and Voss at renewal.

## Analysis

- **Rebate:** Consolidated volume pushes us into FleetPath's Tier 3 band — an estimated $58–71K/year in additional rebates versus today's split tiers.
- **Admin:** One statement, one API feed into our expense system. Treasury estimates reconciliation drops from ~11 hours to ~3 hours monthly.
- **Coverage:** FleetPath's network covers 96% of the stations our drivers already use. The Tucson gap (two stations) is covered by a manual reimbursement fallback — low volume, ~6 fill-ups/month.

## Risk discussion

We explicitly raised single-vendor concentration in the review. The consensus: **fuel cards are a low-criticality payment convenience, not an operational dependency.** If FleetPath has an outage, drivers pay by corporate card or cash and we reconcile later — annoying, not stopping. There is no routing, dispatch, or customer-facing function tied to this. We are not setting a precedent that single-sourcing is acceptable for systems that actually move freight; this is a billing-and-rebate optimization, full stop.

Priya noted the contract has a 60-day exit clause and no minimum-spend penalty, so switching back is cheap if service degrades.

## Decision

Consolidate to FleetPath effective 2021-11-01. Darnell to issue cancellation notices to CardLink and Voss. Revisit at the 2022 contract renewal.

*No concentration-resilience review required — flow criticality assessed as Low.*
