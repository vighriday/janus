"""The JANUS multi-agent reasoning system on a Microsoft Agent Framework workflow.

JANUS is a team of six single-responsibility reasoning agents that collaborate
over typed message edges to turn one intercepted action into a gated
recommendation. Each agent owns one reasoning step and hands its typed output to
the next; several can refuse and halt the chain (abstain, block). The roster maps
onto the reasoning patterns the track values — a Planner→Executor decomposition
with two Critic/Verifier agents guarding the output:

    GuardAgent      screens the action for injection              (Verifier)
    RetrieverAgent  agentic retrieval over the decision history   (Executor)  ← Foundry IQ
    TracerAgent     walks each precedent's outcomes in the graph  (Executor)
    LessonAgent     synthesises one grounded, cited principle and
                    self-verifies it against its sources (Content
                    Safety groundedness)                          (Executor + Critic)
    SimulatorAgent  models three futures, computes the causal do() (Executor)
    DecisionAgent   composes trust, then pauses for a human        (Planner / HITL)

The agent bodies use the same real clients the streaming pipeline uses (Foundry
IQ retrieval, Content Safety, the simulation engine) — the orchestration is the
deterministic part; the reasoning inside each agent is real.

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
from janus.clients.search import (
    FoundryRetriever,
    RetrievalOutcome,
    doc_id_from_snippet,
    strip_frontmatter,
)
from janus.config import get_settings
from janus.models.graph import DecisionGraph
from janus.sim.engine import SimulationOutput, simulate


# --- messages passed along the typed edges ---------------------------------

@dataclass
class Proposal:
    summary: str
    dependency_anchor: float | None = None


@dataclass
class Guarded:
    summary: str
    dependency_anchor: float | None = None


@dataclass
class Retrieved:
    summary: str
    outcome: RetrievalOutcome
    dependency_anchor: float | None = None


@dataclass
class Traced:
    summary: str
    outcome: RetrievalOutcome
    traces: dict
    dependency_anchor: float | None = None


@dataclass
class Lessoned:
    summary: str
    outcome: RetrievalOutcome
    traces: dict
    lesson: str
    grounded_pct: int
    ungrounded: bool
    dependency_anchor: float | None = None


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

    class GuardAgent(Executor):
        """Verifier — screens the action for prompt injection before any work."""

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
            await ctx.send_message(Guarded(p.summary, p.dependency_anchor))

    class RetrieverAgent(Executor):
        """Executor — Foundry IQ agentic retrieval over the decision history."""

        def __init__(self) -> None:
            super().__init__(id="retrieve")

        @handler
        async def run(self, g: Guarded, ctx: WorkflowContext[Retrieved]) -> None:
            await progress.emit(step="retrieve", status="running", label="Searching decision history")
            # Retrieval is a synchronous SDK call; run it off the event loop so it
            # doesn't block other requests for the duration of the Azure round-trip.
            outcome = await asyncio.to_thread(retriever.retrieve, g.summary)
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
            await ctx.send_message(Retrieved(g.summary, outcome, g.dependency_anchor))

    class TracerAgent(Executor):
        """Executor — walks each precedent's decision→outcome links in the graph."""

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
            await ctx.send_message(Traced(r.summary, r.outcome, traces, r.dependency_anchor))

    class LessonAgent(Executor):
        """Executor + Critic — synthesises one cited principle, then self-verifies
        it against its sources with Content Safety groundedness before passing on."""

        def __init__(self) -> None:
            super().__init__(id="lesson")

        @handler
        async def run(self, t: Traced, ctx: WorkflowContext[Lessoned]) -> None:
            await progress.emit(step="lesson", status="running", label="Extracting a grounded lesson")
            sources = [f"[ref_id:{p.ref_id}] {p.title}\n{p.content}" for p in t.outcome.precedents]
            prompt = (
                "From these past decision records, write a single principle (one or two "
                "sentences) that applies to the proposed action. State it directly — do "
                "NOT begin with 'One principle' or 'The principle is'. Cite every record "
                "you rely on inline, in the exact form [ref_id:N] right after the claim it "
                "supports; do NOT list the ref_ids at the end. If the records do not "
                f"support a principle, reply exactly 'INSUFFICIENT EVIDENCE'.\n\n"
                f"Proposed action: {t.summary}\n\n" + "\n\n".join(sources)
            )
            lesson = await llm.chat_complete([{"role": "user", "content": prompt}])
            if lesson.strip().upper().startswith("INSUFFICIENT"):
                await progress.emit(step="lesson", status="done", label="No grounded lesson")
                await ctx.yield_output("abstain: no lesson")
                return
            await progress.emit(step="lesson", status="done", label="Lesson extracted", lesson=lesson)

            await progress.emit(step="grounding", status="running", label="Checking grounding")
            grounding = await safety.detect_groundedness(
                lesson,
                [strip_frontmatter(p.content) for p in t.outcome.precedents],
                query=t.summary,
            )
            grounded_pct = round((1.0 - grounding["ungrounded_pct"]) * 100)
            # Binary groundedness flags paraphrased-but-supported lessons readily,
            # often with no spans. Only hard-flag when genuinely low or the service
            # named specific unsupported spans; otherwise the grounding component
            # already reflects the conservative score without alarming the verdict.
            has_spans = bool(grounding.get("details"))
            ungrounded = grounding["ungrounded"] and (
                grounded_pct < get_settings().groundedness_flag_threshold or has_spans
            )
            await progress.emit(
                step="grounding", status="done", label=f"Grounded {grounded_pct}%",
                grounded_pct=grounded_pct, ungrounded=ungrounded,
            )
            await ctx.send_message(
                Lessoned(t.summary, t.outcome, t.traces, lesson, grounded_pct,
                         ungrounded, t.dependency_anchor)
            )

    class SimulatorAgent(Executor):
        """Executor — models three futures with a seeded Monte Carlo and a DoWhy
        do() intervention; proposes only bounded levers, never authored numbers."""

        def __init__(self) -> None:
            super().__init__(id="simulate")

        @handler
        async def run(self, ls: Lessoned, ctx: WorkflowContext[Simulated]) -> None:
            await progress.emit(step="simulate", status="running", label="Simulating three futures")
            sim = await simulate(
                ls.summary, ls.lesson, run_id="workflow", llm=llm,
                dependency_anchor=ls.dependency_anchor,
            )
            await progress.emit(
                step="simulate", status="done",
                label=f"Simulated 3 futures — recommend: {sim.recommended}",
                futures=sim.futures, recommended=sim.recommended,
                causal_effect=sim.causal_effect, seed_manifest=sim.seed_manifest,
                dependency_anchor=sim.dependency_anchor,
                concentration_knee=get_settings().concentration_knee,
            )
            await ctx.send_message(
                Simulated(ls.summary, ls.outcome, ls.lesson, ls.grounded_pct, ls.ungrounded, sim)
            )

    class DecisionAgent(Executor):
        """Planner / HITL — composes the trust score from the upstream agents'
        signals, then pauses the whole team for a human to approve or override."""

        def __init__(self) -> None:
            super().__init__(id="decide")

        @handler
        async def run(self, s: Simulated, ctx: WorkflowContext[None]) -> None:
            await progress.emit(step="trust", status="running", label="Composing the trust score")
            trust, components = _compose_trust(s)
            cfg = get_settings()
            await progress.emit(
                step="trust", status="done", label=f"Trust {int(trust * 100)}/100",
                trust=trust, floor=cfg.trust_floor,
                state="ok" if trust >= cfg.trust_floor else "weak_evidence",
                components=components,
                weights={
                    "retrieval": cfg.trust_weight_retrieval,
                    "grounding": cfg.trust_weight_grounding,
                    "decisiveness": cfg.trust_weight_decisiveness,
                },
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

    # The agent team. Each is a single-responsibility reasoning agent; the edges
    # are the hand-offs along which they collaborate.
    guard, retrieve, trace, lesson, sim, decide = (
        GuardAgent(), RetrieverAgent(), TracerAgent(),
        LessonAgent(), SimulatorAgent(), DecisionAgent(),
    )
    return (
        WorkflowBuilder(start_executor=guard, name="janus-agents")
        .add_edge(guard, retrieve)
        .add_edge(retrieve, trace)
        .add_edge(trace, lesson)
        .add_edge(lesson, sim)
        .add_edge(sim, decide)
        .build()
    )


def _compose_trust(s: Simulated) -> tuple[float, dict]:
    """Return the composed trust score and the three component signals behind it."""
    cfg = get_settings()
    top = max((p.reranker_score or 0.0) for p in s.outcome.precedents)
    floor = float(cfg.reranker_threshold)
    retrieval = min(1.0, max(0.0, 0.3 + 0.7 * (top - floor))) if top else 0.0
    # A supported lesson earns at least the supported floor — binary groundedness
    # understates faithful paraphrases. A hard-flagged lesson keeps its raw score
    # and additionally caps the composed trust below.
    grounding = s.grounded_pct / 100 if s.ungrounded else max(s.grounded_pct / 100, cfg.grounding_supported_floor)
    by = {f["label"]: f for f in s.sim.futures}
    rec = by.get(s.sim.recommended)
    alts = [f["p50"] for f in s.sim.futures
            if f["label"] != s.sim.recommended and f["risk_label"] != "high"]
    decisiveness = 0.6
    if rec and alts:
        decisiveness = min(1.0, max(0.0, (rec["p50"] - max(alts)) / max(abs(rec["p50"]), 1.0)))
    trust = round(
        cfg.trust_weight_retrieval * retrieval
        + cfg.trust_weight_grounding * grounding
        + cfg.trust_weight_decisiveness * decisiveness,
        2,
    )
    if s.ungrounded:
        trust = min(trust, cfg.trust_floor)
    components = {
        "retrieval": round(retrieval, 2),
        "grounding": round(grounding, 2),
        "decisiveness": round(decisiveness, 2),
    }
    return trust, components


# Clients are built once and shared (each holds a credential + an httpx client).
# Rebuilding them per request leaks connections and credentials.
_CLIENTS: tuple | None = None
_GRAPH: DecisionGraph | None = None


def make_clients():
    global _CLIENTS
    if _CLIENTS is None:
        _CLIENTS = (SafetyClient(), FoundryRetriever(), LLMClient(), _load_graph())
    return _CLIENTS


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


def _frame(kw: dict) -> str:
    from janus.models import StepKind, StepStatus, StreamEvent

    idx = _STEP_INDEX.get(kw["step"], 90)
    kind = StepKind(kw["step"]) if kw["step"] in StepKind.__members__.values() else StepKind.done
    payload = {k: v for k, v in kw.items() if k not in ("step", "status", "label")}
    return StreamEvent(
        id=f"step-{idx}-{kw['step']}", kind=kind,
        status=StepStatus(kw["status"]), label=kw["label"], payload=payload,
    ).to_sse()


def _error_frame(message: str) -> str:
    from janus.models import StepKind, StepStatus, StreamEvent

    return StreamEvent(
        id="step-90-error", kind=StepKind.error, status=StepStatus.failed, label=message
    ).to_sse()


@dataclass
class _PausedRun:
    """A workflow paused at the human gate, held server-side until the operator
    decides. The same in-memory workflow object is required to resume, so it
    lives in the registry keyed by run id across the two HTTP requests."""

    workflow: object
    progress: "_Progress"
    request_id: str


# The run registry — the answer to "workflow state across the approval
# round-trip." Keyed by run id; entries are popped on resume or timed out.
_RUNS: dict[str, _PausedRun] = {}
_MAX_RUNS = 32


async def _drain(stream, progress, frames: list[str]) -> object | None:
    """Forward queued progress as SSE frames; return a pending request_info
    event if the workflow paused, else None. Never raises — an executor error
    becomes a terminal error frame so the stream always closes cleanly."""
    request = None
    try:
        async for event in stream:
            if getattr(event, "type", None) == "request_info":
                request = event
            while not progress.queue.empty():
                frames.append(_frame(progress.queue.get_nowait()))
    except Exception as exc:  # noqa: BLE001 - surface, don't drop the stream
        frames.append(_error_frame(f"Pipeline error: {exc}"))
        return None
    while not progress.queue.empty():
        frames.append(_frame(progress.queue.get_nowait()))
    return request


async def run_workflow_pipeline(
    summary: str, run_id: str, dependency_anchor: float | None = None, auto_approve: bool = False
) -> AsyncIterator[str]:
    """Drive the MAF workflow to the human gate and stream its progress as SSE.

    Runs to the request_info pause and stops there, registering the paused
    workflow under `run_id` so a second request (`resume_workflow`) can resume it
    with the human's decision. When `auto_approve` is set the gate is resolved
    in-process (used by the plain `/invoke` path, which has no separate gate UI).
    """
    progress = _Progress()
    workflow = build_workflow(progress, make_clients())

    frames: list[str] = []
    pending = await _drain(
        workflow.run(stream=True, message=Proposal(summary, dependency_anchor)), progress, frames
    )
    for f in frames:
        yield f
    frames.clear()

    if pending is None:
        return  # abstained / blocked / errored before the gate

    rid = getattr(pending, "request_id", None)
    if rid is None:
        return

    if auto_approve:
        await _drain(workflow.run(stream=True, responses={rid: True}), progress, frames)
        for f in frames:
            yield f
        return

    # Real HITL: hold the paused workflow for a second request to resume, and
    # tell the client which run id to resume.
    if len(_RUNS) >= _MAX_RUNS:
        _RUNS.pop(next(iter(_RUNS)))  # evict the oldest; this is a demo-scale cap
    _RUNS[run_id] = _PausedRun(workflow=workflow, progress=progress, request_id=rid)
    yield _frame({"step": "approval", "status": "running",
                  "label": "Awaiting human approval", "run_id": run_id, "awaiting": True})


async def resume_workflow(run_id: str, approved: bool) -> AsyncIterator[str]:
    """Resume a paused run with the human's decision and stream the rest.

    Idempotent: a second call for the same run id (a double-click) finds no
    entry and yields a single already-resolved frame rather than erroring."""
    paused = _RUNS.pop(run_id, None)
    if paused is None:
        yield _frame({"step": "done", "status": "done", "label": "This decision was already recorded."})
        return
    frames: list[str] = []
    await _drain(
        paused.workflow.run(stream=True, responses={paused.request_id: approved}),
        paused.progress,
        frames,
    )
    for f in frames:
        yield f
