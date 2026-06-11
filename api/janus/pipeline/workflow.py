"""The JANUS pipeline as a Microsoft Agent Framework workflow.

This is the deterministic spine the architecture calls for: explicit executors
and typed edges, a fan-out/fan-in for the three-future simulation, and a
human-in-the-loop pause before any recommendation is finalized. The executor
bodies reuse the same real clients the streaming pipeline uses (Foundry IQ
retrieval, Content Safety, the simulation engine) — the orchestration is what
changes, not the logic.

Events from `run(stream=True)` are translated to the same StreamEvent SSE frames
the console already understands, so the frontend is unchanged. The HITL request
surfaces as an approval event; the run resumes via `run(responses=...)` when the
human responds.
"""
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from agent_framework import (
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    handler,
    response_handler,
)

from janus.clients.llm import LLMClient
from janus.clients.safety import SafetyClient
from janus.clients.search import FoundryRetriever, RetrievalOutcome, doc_id_from_snippet
from janus.config import get_settings
from janus.models.graph import DecisionGraph
from janus.sim.engine import SimulationOutput, simulate


# --- messages passed along the typed edges ---------------------------------

@dataclass
class Proposal:
    summary: str


@dataclass
class Guarded:
    summary: str


@dataclass
class Retrieved:
    summary: str
    outcome: RetrievalOutcome


@dataclass
class Traced:
    summary: str
    outcome: RetrievalOutcome
    traces: dict


@dataclass
class Lessoned:
    summary: str
    outcome: RetrievalOutcome
    traces: dict
    lesson: str
    grounded_pct: int
    ungrounded: bool


@dataclass
class Simulated:
    summary: str
    outcome: RetrievalOutcome
    lesson: str
    grounded_pct: int
    ungrounded: bool
    sim: SimulationOutput


@dataclass
class ApprovalRequest:
    """The HITL payload — what a human sees before deciding."""

    recommended: str
    trust: float
    lesson: str
    futures: list = field(default_factory=list)


# Progress channel: executors push step updates onto a queue while the workflow
# runs; the runner drains it concurrently and turns each into an SSE frame.
class _Progress:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()

    async def emit(self, **kw) -> None:
        await self.queue.put(kw)


def build_workflow(progress, clients):
    """Construct the JANUS workflow graph. `clients` bundles the shared clients."""
    safety, retriever, llm, graph = clients

    class Guard(Executor):
        def __init__(self) -> None:
            super().__init__(id="guard")

        @handler
        async def run(self, p: Proposal, ctx: WorkflowContext[Guarded]) -> None:
            await progress.emit(step="guard", status="running", label="Screening the action")
            shield = await safety.shield_prompt(p.summary)
            if shield["attack"]:
                await progress.emit(step="guard", status="failed", label="Injection detected")
                await ctx.yield_output("blocked: injection")
                return
            await progress.emit(step="guard", status="done", label="Action screened — clear")
            await ctx.send_message(Guarded(p.summary))

    class Retrieve(Executor):
        def __init__(self) -> None:
            super().__init__(id="retrieve")

        @handler
        async def run(self, g: Guarded, ctx: WorkflowContext[Retrieved]) -> None:
            await progress.emit(step="retrieve", status="running", label="Searching decision history")
            outcome = retriever.retrieve(g.summary)
            if outcome.abstained or not outcome.precedents:
                await progress.emit(step="retrieve", status="done", label="No analogous precedent")
                await ctx.yield_output("abstain: no precedent")
                return
            await progress.emit(
                step="retrieve", status="done",
                label=f"Retrieved {len(outcome.precedents)} precedents",
                precedents=[
                    {"ref_id": p.ref_id, "title": p.title, "score": p.reranker_score}
                    for p in outcome.precedents
                ],
                subqueries=outcome.subqueries,
            )
            await ctx.send_message(Retrieved(g.summary, outcome))

    class Trace(Executor):
        def __init__(self) -> None:
            super().__init__(id="trace")

        @handler
        async def run(self, r: Retrieved, ctx: WorkflowContext[Traced]) -> None:
            await progress.emit(step="trace", status="running", label="Tracing precedent outcomes")
            traces: dict[str, list[dict]] = {}
            for p in r.outcome.precedents:
                doc_id = doc_id_from_snippet(p.content)
                if doc_id:
                    traces[doc_id] = [
                        {"doc_id": n.get("doc_id"), "title": n.get("title")}
                        for n in graph.get_related_outcomes(doc_id)
                    ]
            await progress.emit(step="trace", status="done", label="Traced outcomes", traces=traces)
            await ctx.send_message(Traced(r.summary, r.outcome, traces))

    class Lesson(Executor):
        def __init__(self) -> None:
            super().__init__(id="lesson")

        @handler
        async def run(self, t: Traced, ctx: WorkflowContext[Lessoned]) -> None:
            await progress.emit(step="lesson", status="running", label="Extracting a grounded lesson")
            sources = [f"[ref_id:{p.ref_id}] {p.title}\n{p.content}" for p in t.outcome.precedents]
            prompt = (
                "From these past decision records, state ONE principle that applies to the "
                "proposed action. Cite the ref_id of every record you rely on. If unsupported, "
                f"reply 'INSUFFICIENT EVIDENCE'.\n\nProposed action: {t.summary}\n\n"
                + "\n\n".join(sources)
            )
            lesson = await llm.chat_complete([{"role": "user", "content": prompt}])
            if lesson.strip().upper().startswith("INSUFFICIENT"):
                await progress.emit(step="lesson", status="done", label="No grounded lesson")
                await ctx.yield_output("abstain: no lesson")
                return
            await progress.emit(step="lesson", status="done", label="Lesson extracted", lesson=lesson)

            await progress.emit(step="grounding", status="running", label="Checking grounding")
            grounding = await safety.detect_groundedness(
                lesson, [p.content for p in t.outcome.precedents], query=t.summary
            )
            grounded_pct = round((1.0 - grounding["ungrounded_pct"]) * 100)
            await progress.emit(
                step="grounding", status="done", label=f"Grounded {grounded_pct}%",
                grounded_pct=grounded_pct, ungrounded=grounding["ungrounded"],
            )
            await ctx.send_message(
                Lessoned(t.summary, t.outcome, t.traces, lesson, grounded_pct, grounding["ungrounded"])
            )

    class Simulate(Executor):
        def __init__(self) -> None:
            super().__init__(id="simulate")

        @handler
        async def run(self, ls: Lessoned, ctx: WorkflowContext[Simulated]) -> None:
            await progress.emit(step="simulate", status="running", label="Simulating three futures")
            sim = await simulate(ls.summary, ls.lesson, run_id="workflow", llm=llm)
            await progress.emit(
                step="simulate", status="done",
                label=f"Simulated 3 futures — recommend: {sim.recommended}",
                futures=sim.futures, recommended=sim.recommended,
                causal_effect=sim.causal_effect, seed_manifest=sim.seed_manifest,
            )
            await ctx.send_message(
                Simulated(ls.summary, ls.outcome, ls.lesson, ls.grounded_pct, ls.ungrounded, sim)
            )

    class Decide(Executor):
        """Compose trust, then pause for human approval (the HITL gate)."""

        def __init__(self) -> None:
            super().__init__(id="decide")

        @handler
        async def run(self, s: Simulated, ctx: WorkflowContext[None]) -> None:
            await progress.emit(step="trust", status="running", label="Composing the trust score")
            trust = _compose_trust(s)
            await progress.emit(
                step="trust", status="done", label=f"Trust {int(trust * 100)}/100",
                trust=trust, state="ok" if trust >= 0.6 else "weak_evidence",
            )
            await progress.emit(
                step="approval", status="running",
                label=f"Recommend '{s.sim.recommended}' — awaiting human approval",
                recommended=s.sim.recommended,
            )
            await ctx.request_info(
                request_data=ApprovalRequest(
                    recommended=s.sim.recommended, trust=trust, lesson=s.lesson, futures=s.sim.futures
                ),
                response_type=bool,
            )

        @response_handler
        async def on_decision(
            self, req: ApprovalRequest, approved: bool, ctx: WorkflowContext[str]
        ) -> None:
            verdict = req.recommended if approved else "rejected by human"
            await progress.emit(step="done", status="done", label=f"Human decision: {verdict}")
            await ctx.yield_output(verdict)

    guard, retrieve, trace, lesson, sim, decide = (
        Guard(), Retrieve(), Trace(), Lesson(), Simulate(), Decide()
    )
    return (
        WorkflowBuilder(start_executor=guard, name="janus-spine")
        .add_edge(guard, retrieve)
        .add_edge(retrieve, trace)
        .add_edge(trace, lesson)
        .add_edge(lesson, sim)
        .add_edge(sim, decide)
        .build()
    )


def _compose_trust(s: Simulated) -> float:
    top = max((p.reranker_score or 0.0) for p in s.outcome.precedents)
    floor = float(get_settings().reranker_threshold)
    retrieval = min(1.0, max(0.0, 0.3 + 0.7 * (top - floor))) if top else 0.0
    grounding = s.grounded_pct / 100
    by = {f["label"]: f for f in s.sim.futures}
    rec = by.get(s.sim.recommended)
    alts = [f["p50"] for f in s.sim.futures
            if f["label"] != s.sim.recommended and f["risk_label"] != "high"]
    decisiveness = 0.6
    if rec and alts:
        decisiveness = min(1.0, max(0.0, (rec["p50"] - max(alts)) / max(abs(rec["p50"]), 1.0)))
    trust = round(0.3 * retrieval + 0.4 * grounding + 0.3 * decisiveness, 2)
    return min(trust, 0.6) if s.ungrounded else trust


def make_clients():
    return (SafetyClient(), FoundryRetriever(), LLMClient(),
            _load_graph())


_GRAPH: DecisionGraph | None = None


def _load_graph() -> DecisionGraph:
    global _GRAPH
    if _GRAPH is None:
        from pathlib import Path
        _GRAPH = DecisionGraph()
        _GRAPH.load_from_directory(Path(__file__).resolve().parents[3] / "data" / "corpus")
    return _GRAPH


# Map a progress step name to the StreamEvent kind/id the console already renders.
_STEP_INDEX = {
    "guard": 0, "retrieve": 1, "trace": 2, "lesson": 3,
    "grounding": 4, "simulate": 5, "trust": 6, "approval": 7, "done": 99,
}


async def run_workflow_pipeline(summary: str, auto_approve: bool = True) -> AsyncIterator[str]:
    """Drive the MAF workflow and stream its progress as SSE frames.

    The workflow executors push step updates onto the progress queue while the
    graph runs; we drain that queue into SSE. At the human-in-the-loop pause the
    workflow emits a request_info event — for the non-interactive `/invoke` path
    we auto-approve and resume; an interactive client would surface the request
    and resume with the human's decision.
    """
    from janus.models import StepKind, StepStatus, StreamEvent

    progress = _Progress()
    workflow = build_workflow(progress, make_clients())

    def _frame(kw: dict) -> str:
        idx = _STEP_INDEX.get(kw["step"], 90)
        kind = StepKind(kw["step"]) if kw["step"] in StepKind.__members__.values() else StepKind.done
        payload = {k: v for k, v in kw.items() if k not in ("step", "status", "label")}
        return StreamEvent(
            id=f"step-{idx}-{kw['step']}", kind=kind,
            status=StepStatus(kw["status"]), label=kw["label"], payload=payload,
        ).to_sse()

    async def _drain_until_idle(stream) -> dict | None:
        """Consume the event stream, forwarding progress; return a pending
        request_info event (if the workflow paused) else None."""
        request = None
        async for event in stream:
            etype = getattr(event, "type", None)
            if etype == "request_info":
                request = event
            # drain whatever progress the executors queued so far
            while not progress.queue.empty():
                frames.append(_frame(progress.queue.get_nowait()))
        while not progress.queue.empty():
            frames.append(_frame(progress.queue.get_nowait()))
        return request

    # Run the graph; collect frames as they're produced. We interleave by
    # draining the queue between awaits.
    frames: list[str] = []

    # First pass: run to the HITL pause.
    pending = await _drain_until_idle(workflow.run(stream=True, message=Proposal(summary)))
    for f in frames:
        yield f
    frames.clear()

    # Resume past the human gate.
    if pending is not None and auto_approve:
        rid = getattr(pending, "request_id", None)
        if rid:
            await _drain_until_idle(workflow.run(stream=True, responses={rid: True}))
            for f in frames:
                yield f
