---
doc_id: NW-2023-0341
doc_type: risk_note
title: Concentration Risk — Carrier Software Consolidation onto Tessell
date: 2023-03-28
author: priya nair (IT Architecture)
team: IT
tags: [vendor, consolidation, resilience, risk, dependency]
synthetic: true
company: Northwind Logistics (fictional)
related: [NW-2023-0312]
---

# Concentration Risk — Carrier Software Consolidation onto Tessell

## Summary

The proposed consolidation moves 100% of carrier routing onto a single external
vendor (Tessell). This note assesses the resilience cost of that dependency
concentration. The savings case is sound; the resilience case is not addressed by
the current plan.

## The concentration

Today our carrier-routing volume is split: Tessell ~55%, Carrowind ~30%,
Halberd ~15%. The split is accidental but it is also a hedge — when Carrowind had
a four-hour API outage last August, we rerouted critical lanes through Tessell and
Halberd and absorbed it. Customers never saw it.

After consolidation, Tessell carries ~100%. There is no reroute path. An outage
during a dispatch window is no longer absorbable.

## Why the SLA does not cover this

Tessell's 99.9% SLA credits us service fees for downtime. It does not compensate
for missed dispatch windows, expedited-freight penalties, or the customer churn
that follows a visible failure. Our own incident data puts the cost of a single
peak-window outage at roughly 30–40x the SLA credit.

## Recommendation

Do not take Tessell above ~70% of carrier-routing volume. Keep a second vendor
warm on the remaining lanes as a live fallback, even at a higher unit cost. The
delta in unit price on 30% of volume is small relative to the tail risk of a
total-dependency outage.

If the organization proceeds to full consolidation anyway, this note records that
the resilience risk was identified in advance and accepted as a tradeoff for the
savings number.
