---
doc_id: NW-2022-DRES-0061
doc_type: decision_memo
title: EU Data Residency for the Customer Portal — Phase 1 Approval (Frankfurt)
date: 2022-09-19
team: Data Platform & Compliance
tags: [gdpr, data-residency, customer-portal, eu, compliance]
synthetic: true
company: Northwind Logistics (fictional)
---

# Decision Memo: EU Data Residency for the Customer Portal

**Author:** Marta Ostrowski (Data Platform Lead)
**Approvers:** Devon Achebe (DPO), Priya Vellani (VP Engineering)
**Status:** Approved — Phase 1 only

## Decision

We will host the EU customer portal's primary datastore in our cloud provider's **eu-central-1 (Frankfurt)** region, with all customer profile, shipment-history, and consignee contact data resident in-region. US-based analytics access continues via a pseudonymized replica with consignee names and addresses stripped. This is a **data-residency** decision, not a vendor change — we stay on our current provider and current portal stack.

## Why now

Three EU shippers (Brüggemann GmbH among them) flagged during Q2 onboarding that their data was landing in us-east-1. Legal confirmed our DPAs commit to EU-resident storage for these accounts. We were out of compliance for roughly 4,100 active EU consignee records.

## What delayed us

We had targeted an August cutover. The **regional compliance review** ran long: our DPO required a documented review of every cross-border data flow before migrating, including the SendGrid email path and the support-ticket integration (Zendesk), both of which were egressing EU PII to US endpoints. That review took six weeks and surfaced two flows nobody had mapped. We chose to delay the migration rather than cut over with unreviewed egress paths. Net slip: ~5 weeks.

## Scope and tradeoffs

- **In scope:** portal DB, object storage for proof-of-delivery scans, transactional email routing.
- **Out of scope (Phase 2):** the carrier-rate cache and the mobile driver app — these hold no consignee PII, so residency is not required yet.
- **Cost:** ~$3,400/mo incremental for the Frankfurt footprint plus cross-region replication egress. Accepted.
- **Latency:** US support agents see +90ms on portal reads. Acceptable per Support.

## Risks

Single-region for now means a Frankfurt outage takes the EU portal down with no warm failover. We accept this for Phase 1 and will revisit multi-AZ-within-EU in Q1 2023.

**Next review:** 2023-02-15.
