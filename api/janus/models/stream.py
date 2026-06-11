"""Stream event contract.

The backend emits these as Server-Sent Events. The frontend renders each step
of the pipeline as it arrives. The shape mirrors the AI SDK UI Message Stream
"data part" convention: a typed `kind`, a stable `id` for same-id reconciliation,
and a `status` so a step can update in place (running -> done) without emitting a
new card.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepKind(str, Enum):
    guard = "guard"
    retrieve = "retrieve"
    trace = "trace"
    lesson = "lesson"
    grounding = "grounding"
    simulate = "simulate"
    trust = "trust"
    approval = "approval"
    done = "done"
    error = "error"


class StepStatus(str, Enum):
    running = "running"
    done = "done"
    skipped = "skipped"
    failed = "failed"


class StreamEvent(BaseModel):
    """One data part on the wire. Re-emitting with the same id updates the step."""

    id: str = Field(..., description="stable per pipeline step, for same-id reconciliation")
    kind: StepKind
    status: StepStatus
    label: str = Field(..., description="human-readable step label for the live log")
    latency_ms: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict, description="step-specific data for the UI")

    def to_sse(self) -> str:
        """Serialize as an SSE `data:` line (single event, JSON body)."""
        return f"data: {self.model_dump_json()}\n\n"
