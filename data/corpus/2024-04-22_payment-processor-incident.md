---
doc_id: NW-2024-PAYOPS-PM-0417
doc_type: postmortem
title: "Postmortem: Payabridge Outage During Driver Settlement Run (Apr 17, 2024)"
date: 2024-04-22
team: Payment Operations
tags: [postmortem, payments, resilience, fallback, settlement]
synthetic: true
company: Northwind Logistics (fictional)
---

# Postmortem: Payabridge Outage During Driver Settlement Run

**Author:** Renata Okonkwo, Payment Operations Lead
**Reviewers:** D. Halvorsen (Treasury), Sam Iyer (Platform SRE)
**Severity:** SEV-2 (downgraded from initial SEV-1)

## Summary
On Apr 17 between 13:02 and 15:48 ET, our primary payment processor, **Payabridge**, returned 5xx errors on ~94% of ACH authorization calls. This coincided with the Wednesday driver-settlement run, where we disburse to ~2,300 owner-operators. Despite the outage, **zero settlements were delayed past their SLA window.** We failed over to our warm secondary, **Continental Pay Rails (CPR)**, in 19 minutes.

## Impact
- 1,140 settlement transactions ($2.41M) queued during the outage window.
- 1,140 reprocessed via CPR; all cleared by 16:30 ET, well inside the same-day cutoff.
- ~$310 in duplicate-fee exposure from 4 double-submitted payments (refunded Apr 19).
- No driver complaints logged. Support fielded 3 "is my pay late?" tickets.

## Why this went fine
This is the policy working. After the Q3-2023 Treasury review (see RISK-PAYOPS-2023-11), we mandated a **warm dual-processor posture** for any flow moving >$1M/day: CPR stays continuously reconciled, holds 8% of weekly volume in steady state, and credentials are rotated and tested monthly. Our quarterly failover drill on Mar 2 ran the exact runbook we executed live. Mean time to failover in the drill was 22 min; live was 19.

## What still hurt
- The 19 minutes weren't free. CPR's lower default rate limit (40 req/s vs Payabridge's 200) forced us to throttle, stretching the batch.
- Our duplicate-detection idempotency key didn't span both processors — hence the 4 doubles.
- Alerting fired on error *rate*, not on settlement-run lag, so on-call noticed 6 min later than they should have.

## Action items
1. Raise CPR contracted rate limit to 120 req/s — *Treasury, due May 31.*
2. Make idempotency keys processor-agnostic — *Platform, due May 15.*
3. Add settlement-run lag SLO + page — *SRE, due May 10.*
4. Document this as the reference example for the dual-processor mandate in onboarding.

**Lesson:** the warm-fallback investment we debated as "expensive insurance" cost us roughly $9K/quarter and just saved a $2.4M run. Worth it.
