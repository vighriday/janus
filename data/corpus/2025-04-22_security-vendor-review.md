---
doc_id: NW-2025-SECOPS-MSSP-AR07
doc_type: project_review
title: 2025 Annual Review — Managed Security Services Vendor (Sentryline)
date: 2025-04-22
team: Security & IT Risk
tags: [mssp, soc, vendor-review, dependency-exception, governance]
synthetic: true
company: Northwind Logistics (fictional)
---

# 2025 Annual Review: Managed Security Services Provider (Sentryline)

**Prepared by:** Devorah Asante, Director of Security & IT Risk
**Reviewers:** Marcus Pell (IT Ops), Lena Quist (Procurement), J. Okafor (Internal Audit observer)

## Scope
Annual performance and risk review of Sentryline, our sole managed-security provider covering 24/7 SOC monitoring, SIEM tuning, and incident triage across the corporate network and the three regional dispatch hubs. Contract value FY25: $418,000 (up 6.1% from FY24's $394,000).

## Performance summary
Sentryline met SLA on alert acknowledgement (median 4.2 min vs. 15 min target) for 11 of 12 months. The miss was September, when a SIEM connector outage on our side delayed log ingestion — root cause was ours, not theirs. Mean time to triage held at 38 min against a 60 min target. They flagged the February phishing cluster correctly (47 mailboxes, contained in under 3 hours). No critical incidents went undetected per our quarterly purple-team checks.

## The single-vendor question
We monitor security through one provider. That triggers our **Critical Dependency Policy (CDP-04)**, which presumes dual-sourcing or a documented fallback for tier-1 services. Sentryline is a deliberate, governed exception. The exception (ref: **CDP-EX-2024-11**, renewed this cycle) rests on three points:
1. SOC monitoring is not commodity-swappable mid-incident — splitting it across two MSSPs measurably *raised* mean-time-to-detect in our 2023 pilot.
2. We hold an internal break-glass runbook: 90 days of warm log retention in our own S3-equivalent, plus a pre-signed statement of work with a backup MSSP (Halcyon Defense) for 30-day spin-up.
3. Exit data portability is contractually guaranteed (CEF/JSON export, 30-day window).

## Decision
**Renew Sentryline for 12 months and re-certify exception CDP-EX-2024-11.** This is governed under CDP-04 but is *not* a precedent for relaxing the dual-source rule elsewhere — each exception stands on its own evidence. Procurement to renegotiate the September SLA-credit clause. Re-review April 2026.

**Action items:** (1) Quist to close pricing by 2025-05-15. (2) Pell to test the Halcyon break-glass SOW in Q3. (3) Asante to file the re-certified exception with Audit.
