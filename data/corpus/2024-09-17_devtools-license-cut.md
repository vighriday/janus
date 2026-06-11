---
doc_id: NW-2024-DEVTOOL-LIC-0392
doc_type: decision_memo
title: Trimming Underused Developer Tool Licenses for FY25 Budget
date: 2024-09-17
team: Engineering Productivity
tags: [cost, licenses, devtools, budget, saas]
synthetic: true
company: Northwind Logistics (fictional)
---

# Decision Memo: Developer Tool License Cleanup

**Author:** Priya Venkataraman, Eng Productivity Lead
**Reviewers:** Tomasz Kowalczyk (Finance), Devon Aird (Eng Manager)
**Status:** Approved

## Context

During the FY25 budget pass, Finance flagged that our SaaS developer-tooling spend grew 22% YoY to roughly $148K/yr, mostly on per-seat licenses that auto-renew. I pulled usage from our SSO logs and the vendor admin consoles. A chunk of these seats are dead weight from people who left or switched teams.

## What we found

- **CodeGrid (static analysis):** 60 seats, only 31 active in the last 90 days. $54/seat/mo.
- **FlowDraw (diagramming):** 40 seats, 12 active. Most folks just use the free tier or paste screenshots into Slack.
- **QueryBench (DB IDE):** 25 seats, 19 active. This one's actually used by the data team, keeping it.
- **PixelProbe (perf profiler):** 15 seats, 3 active. Two of those three said they'd be fine with the open-source alternative.

## Decision

Cut CodeGrid to 35 seats (true-up buffer of 4), drop FlowDraw to a single 5-seat team plan, and cancel PixelProbe entirely at renewal (Nov 30). Keep QueryBench as-is. Estimated annual savings: **~$41K**.

## Tradeoffs

PixelProbe is the only real loss — the OSS profiler is clunkier and the three users grumbled. But three seats isn't worth a $9K/yr line item. FlowDraw downgrade means occasional friction when someone needs to export a polished diagram; acceptable. None of these tools sit on the critical path for shipping or operations — worst case, someone waits a day for a reassigned seat.

## Rollout

Reclaim inactive seats via SSO this sprint. Set all remaining subscriptions to manual renewal so this doesn't silently creep back. Revisit seat counts each January.

No vendor lock-in concerns here; these are all easily swappable, low-stakes tools. This is purely a spend-hygiene cleanup.
