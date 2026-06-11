"""The JANUS pipeline.

Six steps from an intercepted action to a gated recommendation. Each step
streams its own status (running -> done) so the console renders the reasoning as
it happens. Retrieval is real Foundry IQ; grounding and injection screening are
real Content Safety. Simulation and the composed trust score are wired in
Phase 2 and are labeled as placeholders until then.

Clients are created lazily on first run, not at import, so the app can boot (and
serve /health) even if Azure is briefly unreachable.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from janus.clients.llm import LLMClient
from janus.clients.safety import SafetyClient
from janus.clients.search import FoundryRetriever, RetrievalOutcome, doc_id_from_snippet
from janus.config import get_settings
from janus.models import ProposedAction, StepKind, StepStatus, StreamEvent
from janus.models.graph import DecisionGraph

logger = logging.getLogger(__name__)

_CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"


@lru_cache
def _graph() -> DecisionGraph:
    g = DecisionGraph()
    g.load_from_directory(_CORPUS_DIR)
    return g


@lru_cache
def _retriever() -> FoundryRetriever:
    return FoundryRetriever()


@lru_cache
def _llm() -> LLMClient:
    return LLMClient()


@lru_cache
def _safety() -> SafetyClient:
    return SafetyClient()


def _ev(idx: int, kind: StepKind, status: StepStatus, label: str, **payload) -> str:
    return StreamEvent(
        id=f"step-{idx}-{kind.value}", kind=kind, status=status, label=label, payload=payload
    ).to_sse()


async def run_janus_pipeline(action: ProposedAction) -> AsyncIterator[str]:
    """Run the pipeline over an intercepted action, yielding SSE frames."""
    safety = _safety()
    retriever = _retriever()
    llm = _llm()

    # --- 1. GUARD: screen the proposed action for injection -------------------
    yield _ev(0, StepKind.guard, StepStatus.running, "Screening the proposed action")
    try:
        shield = await safety.shield_prompt(action.summary)
        if shield["attack"]:
            yield _ev(0, StepKind.guard, StepStatus.failed, "Injection detected — blocked")
            yield _ev(99, StepKind.done, StepStatus.done, "Stopped: the proposed action was flagged")
            return
        yield _ev(0, StepKind.guard, StepStatus.done, "Action screened — clear")
    except Exception as exc:
        logger.exception("guard failed")
        yield _ev(0, StepKind.guard, StepStatus.failed, f"Screening unavailable: {exc}")
        return

    # --- 2. RETRIEVE: Foundry IQ agentic retrieval ----------------------------
    yield _ev(1, StepKind.retrieve, StepStatus.running, "Searching the decision history")
    try:
        # A concise topical query retrieves far better than the verbose action text.
        question = action.summary
        outcome: RetrievalOutcome = await asyncio.to_thread(retriever.retrieve, question)
    except Exception as exc:
        logger.exception("retrieve failed")
        yield _ev(1, StepKind.retrieve, StepStatus.failed, f"Retrieval unavailable: {exc}")
        return

    # Screen the retrieved documents for indirect injection (XPIA) before reading them.
    doc_texts = [p.content for p in outcome.precedents if p.content]
    if doc_texts:
        try:
            doc_shield = await safety.shield_prompt(action.summary, documents=doc_texts)
            if any(doc_shield["doc_attacks"]):
                flagged = [i for i, a in enumerate(doc_shield["doc_attacks"]) if a]
                outcome.precedents = [
                    p for i, p in enumerate(outcome.precedents) if i not in flagged
                ]
        except Exception:
            logger.warning("document injection screen failed; proceeding with caution")

    if outcome.abstained or not outcome.precedents:
        yield _ev(1, StepKind.retrieve, StepStatus.done, "No analogous precedent found")
        yield _ev(6, StepKind.trust, StepStatus.done, "Low confidence — no precedent to ground on",
                  trust=0.2, state="abstained")
        yield _ev(99, StepKind.done, StepStatus.done,
                  "JANUS abstains: no grounded precedent. Escalate to a human.")
        return

    yield _ev(
        1, StepKind.retrieve, StepStatus.done,
        f"Retrieved {len(outcome.precedents)} precedents",
        subqueries=outcome.subqueries,
        precedents=[
            {"ref_id": p.ref_id, "title": p.title, "score": p.reranker_score}
            for p in outcome.precedents
        ],
    )

    # --- 3. TRACE: walk each precedent's outcomes in the decision graph --------
    yield _ev(2, StepKind.trace, StepStatus.running, "Tracing precedent outcomes")
    graph = _graph()
    traces: dict[str, list[dict]] = {}
    for p in outcome.precedents:
        doc_id = doc_id_from_snippet(p.content)
        if doc_id:
            traces[doc_id] = [
                {"doc_id": n.get("doc_id"), "doc_type": n.get("doc_type"), "title": n.get("title")}
                for n in graph.get_related_outcomes(doc_id)
            ]
    yield _ev(2, StepKind.trace, StepStatus.done, "Traced precedent outcomes", traces=traces)

    # --- 4. LESSON: one grounded, cited principle -----------------------------
    yield _ev(3, StepKind.lesson, StepStatus.running, "Extracting a grounded lesson")
    sources = [f"[ref_id:{p.ref_id}] {p.title}\n{p.content}" for p in outcome.precedents]
    lesson_prompt = (
        "From these past decision records, state ONE principle that applies to the "
        "proposed action. Cite the ref_id of every record you rely on. If the records "
        "do not support a principle, reply exactly 'INSUFFICIENT EVIDENCE'.\n\n"
        f"Proposed action: {action.summary}\n\nRecords:\n" + "\n\n".join(sources)
    )
    try:
        lesson = await llm.chat_complete([{"role": "user", "content": lesson_prompt}])
    except Exception:
        logger.exception("lesson extraction failed")
        lesson = "INSUFFICIENT EVIDENCE"
    if lesson.strip().upper().startswith("INSUFFICIENT"):
        yield _ev(3, StepKind.lesson, StepStatus.done, "No grounded lesson — abstaining")
        yield _ev(99, StepKind.done, StepStatus.done, "JANUS abstains: evidence too thin.")
        return
    yield _ev(3, StepKind.lesson, StepStatus.done, "Lesson extracted", lesson=lesson)

    # --- 5. GROUNDING GATE: is the lesson supported by its sources? -----------
    yield _ev(4, StepKind.grounding, StepStatus.running, "Checking the lesson against its sources")
    try:
        grounding = await safety.detect_groundedness(
            lesson, [p.content for p in outcome.precedents], query=action.summary
        )
        ungrounded = grounding["ungrounded"]
        grounded_pct = round((1.0 - grounding["ungrounded_pct"]) * 100)
    except Exception:
        logger.exception("groundedness check failed")
        ungrounded, grounded_pct = False, 0
    yield _ev(
        4, StepKind.grounding, StepStatus.done,
        f"Grounded {grounded_pct}%" + (" — some claims flagged" if ungrounded else ""),
        ungrounded=ungrounded, grounded_pct=grounded_pct,
    )

    # --- 6. SIMULATE (Phase 2 — placeholder, labeled) -------------------------
    yield _ev(5, StepKind.simulate, StepStatus.running, "Simulating three futures")
    yield _ev(5, StepKind.simulate, StepStatus.skipped, "Simulation arrives in Phase 2",
              placeholder=True)

    # --- 7. TRUST: compose the real signals we have so far --------------------
    # Two components, each in [0,1]: retrieval confidence (how far the top
    # precedent cleared the 2.5 reranker floor) and grounding (how much of the
    # lesson the sources support). A partial-ungrounded flag caps the score
    # rather than zeroing it — 90%-grounded is not no-confidence. The simulation
    # adds a third component in Phase 2.
    top_score = max((p.reranker_score or 0.0) for p in outcome.precedents)
    floor = float(get_settings().reranker_threshold)
    retrieval_conf = min(1.0, max(0.0, (top_score - floor) / floor)) if top_score else 0.0
    grounding_conf = grounded_pct / 100
    trust = round(0.4 * retrieval_conf + 0.6 * grounding_conf, 2)
    if ungrounded:
        trust = min(trust, 0.6)  # cap, don't zero, when some claims are unsupported
    state = "ok" if trust >= 0.6 else "weak_evidence"
    yield _ev(6, StepKind.trust, StepStatus.done,
              f"Provisional trust {int(trust * 100)}/100 "
              f"(retrieval {int(retrieval_conf * 100)}%, grounding {grounded_pct}%)",
              trust=trust, state=state,
              components={"retrieval": round(retrieval_conf, 2), "grounding": round(grounding_conf, 2)})

    # --- 8. HITL GATE ---------------------------------------------------------
    yield _ev(7, StepKind.approval, StepStatus.running, "Awaiting human approval")
    yield _ev(99, StepKind.done, StepStatus.done, "Recommendation ready for human review")
