"""FastAPI surface for JANUS.

The pipeline streams over Server-Sent Events. `/invoke-workflow` runs the real
pipeline on the Microsoft Agent Framework workflow spine and pauses at the human
gate (resumed via `/resume/{run_id}`); `/invoke` runs the same real pipeline as
plain async orchestration without the workflow pause. `/smoke` is a no-Azure wire
check used only in development to exercise the SSE transport.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from janus import __version__
from janus.models import ProposedAction, StepKind, StepStatus, StreamEvent
from janus.pipeline.core import run_janus_pipeline
from janus.pipeline.workflow import resume_workflow, run_workflow_pipeline
from janus.telemetry import setup_telemetry


class HumanDecision(BaseModel):
    """The operator's call at the approval gate."""

    approved: bool

# Install the OpenTelemetry tracer + exporters at import. No-op when no collector
# is configured, so this is safe in every environment including tests.
setup_telemetry()

app = FastAPI(title="JANUS", version=__version__)

# Locked to the local frontend during development. Tightened to the deployed
# origin before anything goes public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


# The placeholder pipeline. Order and labels match the real six steps so the
# frontend can be built against the final shape from day one.
_SMOKE_STEPS = [
    (StepKind.guard, "Screening the proposed action for injection"),
    (StepKind.retrieve, "Searching decision history"),
    (StepKind.trace, "Tracing precedent outcomes"),
    (StepKind.lesson, "Extracting a grounded lesson"),
    (StepKind.grounding, "Checking the lesson against its sources"),
    (StepKind.simulate, "Simulating three futures"),
    (StepKind.trust, "Composing the trust score"),
    (StepKind.approval, "Waiting for human approval"),
]


async def _smoke_stream(action: ProposedAction) -> AsyncIterator[str]:
    for i, (kind, label) in enumerate(_SMOKE_STEPS):
        step_id = f"step-{i}-{kind.value}"
        # announce the step as running
        yield StreamEvent(
            id=step_id, kind=kind, status=StepStatus.running, label=label
        ).to_sse()
        await asyncio.sleep(0.4)  # placeholder for real work
        # update the same step to done (same-id reconciliation)
        yield StreamEvent(
            id=step_id,
            kind=kind,
            status=StepStatus.done,
            label=label,
            latency_ms=400,
            payload={"placeholder": True},
        ).to_sse()
    yield StreamEvent(
        id="done", kind=StepKind.done, status=StepStatus.done, label="Pipeline complete"
    ).to_sse()


@app.post("/smoke")
async def smoke(action: ProposedAction) -> StreamingResponse:
    """Stream a placeholder pipeline run. Proves the SSE wire to the frontend."""
    return StreamingResponse(
        _smoke_stream(action),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@app.post("/invoke")
async def invoke(action: ProposedAction) -> StreamingResponse:
    """Run the JANUS pipeline over SSE (plain async orchestration)."""
    return StreamingResponse(
        run_janus_pipeline(action), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@app.post("/invoke-workflow")
async def invoke_workflow(action: ProposedAction) -> StreamingResponse:
    """Run the JANUS pipeline through the Microsoft Agent Framework workflow graph
    — the deterministic spine with a real human-in-the-loop pause. Streams to the
    approval gate and stops; the run is held server-side under `run_id` until a
    POST to /resume/{run_id} resolves it."""
    run_id = uuid4().hex
    raw_dep = action.params.get("dependency_after")
    dep = float(raw_dep) if isinstance(raw_dep, (int, float)) else None
    return StreamingResponse(
        run_workflow_pipeline(action.summary, run_id=run_id, dependency_anchor=dep, auto_approve=False),
        media_type="text/event-stream",
        headers={**_SSE_HEADERS, "X-Janus-Run-Id": run_id},
    )


@app.post("/resume/{run_id}")
async def resume(run_id: str, decision: HumanDecision) -> StreamingResponse:
    """Resolve a paused workflow with the human's decision and stream the rest.
    This is the second half of the approval round-trip — the same in-memory
    workflow object, resumed via the server-side run registry."""
    return StreamingResponse(
        resume_workflow(run_id, decision.approved),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
