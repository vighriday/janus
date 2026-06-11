"""Scenario levers — the only thing the language model is allowed to produce.

The model reads the proposed action and the grounded lesson, then proposes
qualitative levers and bounded beliefs for three futures. It never emits a final
figure; the cost model turns these levers into numbers. Structured output (a
strict JSON schema generated from the Pydantic model) guarantees the shape.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from janus.clients.llm import LLMClient
from janus.sim.cost_model import ScenarioInputs


class FutureLevers(BaseModel):
    """The levers for one future. Bounded; the model cannot emit money here."""

    label: str = Field(description="one of: approve, modify, reject")
    vendor_count_after: int = Field(ge=1, le=10)
    dependency_after: float = Field(ge=0.0, le=1.0, description="top-vendor share of the flow")
    discount_lo: float = Field(ge=0.0, le=1.0)
    discount_mode: float = Field(ge=0.0, le=1.0)
    discount_hi: float = Field(ge=0.0, le=1.0)
    failure_prob: float = Field(ge=0.0, le=1.0, description="chance of a concentration failure")


class ScenarioLevers(BaseModel):
    futures: list[FutureLevers] = Field(description="exactly three: approve, modify, reject")


_SYSTEM = (
    "You are a risk analyst proposing scenario LEVERS for a procurement decision. "
    "You never state dollar figures. You output three futures — approve (full "
    "consolidation), modify (partial), reject (status quo) — each with the share "
    "of the critical flow that would sit on the top vendor (dependency_after), a "
    "triangular belief about the consolidation discount, and the probability of a "
    "dependency-concentration failure. Higher dependency means higher failure "
    "probability. Reflect the lesson you are given."
)


async def propose_levers(
    action_summary: str,
    lesson: str,
    contract_value: float,
    failure_cost: float,
    llm: LLMClient,
) -> list[ScenarioInputs]:
    """Ask the model for levers, then bind them to the fixed cost-model inputs."""
    user = (
        f"Proposed action: {action_summary}\n\n"
        f"Grounded lesson from past decisions: {lesson}\n\n"
        "Propose the three futures' levers."
    )
    completion = await llm.client.chat.completions.parse(
        model=llm.settings.azure_openai_chat_deployment,
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
        response_format=ScenarioLevers,
        temperature=0,
    )
    msg = completion.choices[0].message
    if msg.refusal or not msg.parsed:
        return _fallback(contract_value, failure_cost)

    out: list[ScenarioInputs] = []
    for f in msg.parsed.futures:
        lo, mode, hi = sorted((f.discount_lo, f.discount_mode, f.discount_hi))
        out.append(
            ScenarioInputs(
                label=f.label,
                vendor_count_after=f.vendor_count_after,
                contract_value=contract_value,
                dependency_after=f.dependency_after,
                discount_lo=lo, discount_mode=mode, discount_hi=hi,
                failure_prob=f.failure_prob,
                failure_cost=failure_cost,
            )
        )
    return out or _fallback(contract_value, failure_cost)


def _fallback(contract_value: float, failure_cost: float) -> list[ScenarioInputs]:
    """If the model refuses or returns nothing, use conservative defaults so the
    pipeline still produces a real (labeled) simulation rather than crashing."""
    return [
        # approve: full consolidation onto one vendor — the action as proposed.
        ScenarioInputs("approve", 1, contract_value, 1.00, 0.05, 0.08, 0.12, 0.30, failure_cost),
        # modify: consolidate but keep the top vendor just under the 70% knee with
        # a warm fallback on the rest — the lesson the corpus teaches. It keeps
        # most of the saving while staying out of the catastrophic tail, so it
        # reads as the safe middle the guardrail can recommend.
        ScenarioInputs("modify", 2, contract_value, 0.65, 0.05, 0.08, 0.12, 0.06, failure_cost),
        ScenarioInputs("reject", 3, contract_value, 0.55, 0.00, 0.00, 0.01, 0.04, failure_cost),
    ]
