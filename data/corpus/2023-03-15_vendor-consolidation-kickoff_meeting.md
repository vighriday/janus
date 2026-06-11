---
doc_id: NW-2023-0312
doc_type: meeting_transcript
title: Procurement Steering — Vendor Consolidation Kickoff
date: 2023-03-15
team: Procurement
attendees: [D. Okafor (VP Procurement), R. Lindqvist (Ops), M. Chen (Finance), priya nair (IT)]
tags: [vendor, consolidation, procurement, cost-reduction]
synthetic: true
company: Northwind Logistics (fictional)
---

# Procurement Steering — Vendor Consolidation Kickoff

**Okafor:** Thanks all. The mandate from the board is clear — Finance wants 12%
off indirect spend this fiscal year. The fastest lever we have is consolidating
the carrier-management software vendors. Right now we run three: Tessell,
Carrowind, and Halberd Systems. Three contracts, three integrations, three
support lines.

**Chen:** If we move everything onto one of them we get volume pricing and we cut
two contracts. My back-of-envelope says we save somewhere north of three million
over the term.

**Lindqvist:** Which one do we consolidate onto?

**Okafor:** Tessell is the obvious pick. Biggest footprint, best feature parity.
They've already quoted us an aggressive rate if we bring the other two volumes
over.

**Nair:** I want to flag something before we get excited. If we put all carrier
routing through Tessell, that's basically our entire fulfilment dependency on one
external vendor. We don't have a fallback if they go down.

**Okafor:** They have a 99.9% SLA.

**Nair:** SLA isn't the same as resilience. 99.9% is eight hours a year. During
peak that's a very expensive eight hours, and the SLA pays us pennies on what an
outage actually costs us in missed dispatch windows.

**Chen:** Noted, but the savings are real and the board wants the number. Can we
make the dependency concentration a managed risk rather than a blocker?

**Okafor:** Let's proceed with Tessell as the consolidation target. Priya, put
together a risk note on the concentration question for the next review. We're not
going to let one objection stall a three-million-dollar win.

**Nair:** I'll write it up. I just want it on the record.

_Action items:_
- Okafor: open commercial negotiation with Tessell for combined volume
- Nair: resilience / concentration risk note by next steering
- Chen: firm up the savings model
