---
doc_id: NW-2024-TELEM-RFP-0417
doc_type: project_review
title: Fleet Telematics Hardware RFP — Bidder Evaluation and Award Recommendation
date: 2024-09-12
team: Procurement & Fleet Engineering
tags: [rfp, telematics, hardware, sourcing, fleet, evaluation]
synthetic: true
company: Northwind Logistics (fictional)
---

# Telematics Hardware RFP — Evaluation Summary

**Scope:** Replace end-of-life telematics control units (TCUs) across 612 tractors and 140 spotter trucks. Hardware only — GPS/ELD-capable units, CAN bus harnesses, and 4-year cellular hardware warranty. Backend platform (RouteVision) is unchanged and out of scope for this RFP.

## Bidders
Three vendors responded to RFP-FE-24-09:

- **Atlas Telemetrics** — ruggedized TCU-7 unit, $214/unit, 18-month field MTBF claim, 8-week lead time.
- **Greywater Devices** — TCU "Vanguard," $169/unit, 12-month MTBF, 4-week lead time, but no built-in accelerometer (needed for harsh-braking scoring).
- **Cordell Hardware Group** — incumbent on our reefer units, $231/unit, 24-month MTBF, dual-SIM failover, 11-week lead time.

## Evaluation (weighted)
Scoring: reliability 35%, total cost 30%, lead time 20%, integration effort 15%.

| Vendor | Reliability | Cost | Lead | Integration | Total |
|---|---|---|---|---|---|
| Atlas | 7.5 | 8.0 | 7.0 | 8.5 | **7.68** |
| Greywater | 6.0 | 9.5 | 9.0 | 5.0 | **7.28** |
| Cordell | 9.0 | 6.5 | 4.0 | 9.0 | **7.18** |

Greywater's price was tempting (~$28K savings fleet-wide), but bench testing showed the missing onboard accelerometer would force a separate sensor add-on, eating the savings and adding a wiring failure point. Cordell scored highest on reliability but the 11-week lead time collides with our Q1 reefer refresh window.

## Decision
**Award split: Atlas Telemetrics for the 612 tractors; Cordell retained for the 140 reefer-adjacent spotter units** where dual-SIM failover matters. We are deliberately *not* consolidating to a single hardware vendor — Fleet Engineering wants a second qualified source to avoid a repeat of the 2022 single-supplier shortage. Maria Ostrander (Fleet Eng lead) and the procurement desk signed off. PO issued for a 50-unit pilot batch first; full rollout pending 60-day burn-in.

Next review: pilot results, 2024-11-15.
