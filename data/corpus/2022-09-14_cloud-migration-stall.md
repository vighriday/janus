---
doc_id: NW-2022-CLOUDMIG-0417
doc_type: project_review
title: Q3 Project Review — "Skyhook" AWS Migration (Wave 2 Stall)
date: 2022-09-14
team: Cloud Platform / PMO
tags: [cloud-migration, ownership, governance, aws, stall]
synthetic: true
company: Northwind Logistics (fictional)
---

# Skyhook Wave 2 — Project Review

**Reviewer:** Priya Anand (PMO) · **Attendees:** D. Okafor (Infra), M. Reyes (App Dev), T. Lindqvist (Data Eng), S. Whitlock (Security)

## Where we are
Skyhook was supposed to move 14 on-prem workloads (warehouse scheduling, the EDI gateway, two reporting stacks, and the driver-app backend) into AWS by end of Q3. We are at 5 of 14. Wave 1 (the easy lift-and-shift boxes) landed in May. Wave 2 has not moved meaningfully since late June.

This is not a technology problem. We tested the landing zone; it works. This is an ownership problem.

## What actually happened
The driver-app backend migration needs a decision on whether to re-platform onto RDS Postgres or keep self-managed on EC2. That single decision has been "owned" by four teams at once:

- **Infra** says it's an App Dev call because schema lifecycle is theirs.
- **App Dev** says Data Eng owns the database, so it's their call.
- **Data Eng** says they only own the warehouse, not transactional DBs, and Security has to sign off on the data-at-rest config first.
- **Security** has been waiting three weeks for someone to file the review ticket. Nobody did, because nobody believed it was theirs to file.

We counted 31 Slack threads and 4 meetings on this one decision. Estimated burn: ~$48K in loaded eng time and a $9K/month overlap where we're paying for both the old hardware lease and the new reserved instances. We are now projecting Q4, best case, and the dual-running cost compounds at roughly $9K/month until cutover.

## Root cause
There is no single accountable owner (DRI) for Skyhook. The steering group is a committee of equals, which means every cross-team decision deadlocks. RACI was drafted in the kickoff deck and never ratified.

## Decision
Effective immediately, we are appointing **D. Okafor as the single Skyhook DRI** with explicit authority to make the RDS-vs-EC2 call and any future cross-team tie-breaks. Steering becomes advisory, not approving. Priya to publish a ratified RACI by 2022-09-21. Re-baseline Wave 2 dates at the 9/28 checkpoint.

**This was a governance failure, not a vendor or architecture failure. We are fixing who decides, not what we bought.**
