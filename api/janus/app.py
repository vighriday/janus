"""FastAPI surface for JANUS.

Right now this exposes a health check and a smoke-test stream that walks a
placeholder version of the six-step pipeline. The smoke stream exists to prove
the wire end to end — the frontend renders these events live — before the real
pipeline steps are plugged in. Each real step will replace its placeholder here.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from janus import __version__
from janus.models import ProposedAction, StepKind, StepStatus, StreamEvent

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

from janus.pipeline.core import run_janus_pipeline

@app.post("/invoke")
async def invoke(action: ProposedAction) -> StreamingResponse:
    """Run the real JANUS pipeline steps over SSE."""
    return StreamingResponse(
        run_janus_pipeline(action),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
