---
doc_id: NW-ERP-2024-FIN-0473
doc_type: decision_memo
title: Decision to Defer Atlas Finance Module Upgrade (v9 to v11) to Q2 FY26
date: 2024-09-17
team: Finance Systems / IT
tags: [erp, finance, upgrade, integration-risk, scheduling]
synthetic: true
company: Northwind Logistics (fictional)
---

# Decision Memo: Defer Atlas ERP Finance-Module Upgrade

**Author:** Priya Okonkwo-Reyes, Director of Finance Systems
**Reviewers:** Dev Hartmann (Controller), Lena Sokolova (IT Integration Lead)

## Decision
We are deferring the Atlas ERP finance-module upgrade from v9.4 to v11.2 until **Q2 FY26 (target April 2026)**. We are NOT changing ERP vendors and NOT consolidating systems — this is purely about upgrade timing. Atlas stays our system of record.

## Why now is the wrong window
The v11 jump rewrites the GL-posting API and deprecates the legacy SOAP connector that our freight-billing system (FreightDesk) and the TMS settlement export both depend on. We have **14 active integrations** touching the finance module; 6 of them use the SOAP path slated for removal in v11.

Lena's team ran a discovery pass over three weeks. Findings:
- FreightDesk's nightly invoice sync would need a full rewrite to the new REST/JSON endpoints — estimated 7-9 dev-weeks.
- The TMS settlement export uses an undocumented field mapping that broke in our sandbox v11 test (412 of 1,180 test invoices failed to post).
- Our close calendar is brutal Oct-Jan (peak season volume up ~38% YoY); a botched cutover during close would risk the month-end and the year-end audit.

## Cost / tradeoff
Staying on v9.4 costs us an extra **$31k/year** in extended-support fees and we forgo the v11 multi-entity tax automation (would save ~120 finance-team hours/quarter). We judged that real but not worth a close-season integration failure. v9.4 is supported through Dec 2026, so we have runway.

## Conditions to revisit
1. FreightDesk and TMS connectors migrated to REST in a sandbox with a clean 1,180-invoice test pass.
2. Cutover scheduled in a low-volume window (April/May), not during close.
3. Rollback plan validated end-to-end.

We accept the carrying cost to buy integration certainty. Revisit at January FY26 planning.
