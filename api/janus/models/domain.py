"""Domain contracts for the JANUS pipeline.

The types here enforce the safety rules at the boundary rather than at runtime.
A Lesson cannot exist without at least one citation; a recommendation always
carries a trust score and the evidence behind it.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


# --- input ---------------------------------------------------------------

class ProposedAction(BaseModel):
    """What an autonomous agent wants to do, handed to JANUS before execution."""

    action: str = Field(..., description="e.g. 'consolidate_vendors'")
    summary: str = Field(..., description="one-line natural-language description")
    params: dict = Field(default_factory=dict)
    rationale: str | None = None


# --- retrieval -----------------------------------------------------------

class Citation(BaseModel):
    ref_id: int
    doc_id: str
    doc_type: str
    title: str
    snippet: str
    reranker_score: float


class RetrievalResult(BaseModel):
    """Output of the Foundry IQ retrieve step."""

    subqueries: list[str] = Field(default_factory=list, description="the decomposed query plan")
    citations: list[Citation] = Field(default_factory=list)
    near_misses: list[Citation] = Field(default_factory=list, description="below-threshold hits, shown but not grounding")
    synthesized_answer: str | None = None
    ga_fallback: bool = Field(False, description="true if we degraded to the GA extractive path")

    @property
    def has_precedent(self) -> bool:
        return len(self.citations) > 0


# --- lesson --------------------------------------------------------------

class Lesson(BaseModel):
    """A grounded principle. Cannot be constructed without citations."""

    principle: str
    citations: Annotated[list[Citation], Field(min_length=1)]
    source_count: int = Field(..., ge=2, description="distinct sources; >=2 by policy")
    groundedness: float = Field(..., ge=0.0, le=1.0)
    ungrounded_spans: list[str] = Field(default_factory=list)


# --- simulation ----------------------------------------------------------

class FutureName(str, Enum):
    approve = "approve"
    modify = "modify"
    reject = "reject"


class Future(BaseModel):
    name: FutureName
    narrative: str
    p10: float
    p50: float
    p90: float
    risk_label: str
    drivers: dict[str, float] = Field(default_factory=dict, description="Sobol sensitivity per input")


class SimulationResult(BaseModel):
    futures: list[Future]
    seed: int
    formula_version: str
    input_snapshot_hash: str


# --- decision ------------------------------------------------------------

class RiskState(str, Enum):
    ok = "ok"
    weak_evidence = "weak_evidence"
    abstained = "abstained"


class TrustScore(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    retrieval_confidence: float
    grounding: float
    simulation_agreement: float
    state: RiskState


class Recommendation(BaseModel):
    """The final output. JANUS never executes — this goes to a human."""

    run_id: str
    verdict: FutureName | None = Field(None, description="None when abstaining")
    state: RiskState
    headline: str
    lesson: Lesson | None = None
    retrieval: RetrievalResult
    simulation: SimulationResult | None = None
    trust: TrustScore
    requires_human_approval: bool = True
