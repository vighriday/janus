"""Simulation orchestrator.

Ties the three pieces together for the pipeline:
  1. the model proposes levers for three futures (structured output)
  2. the seeded Monte Carlo turns each future's levers into P10/P50/P90 bands
  3. a do()-intervention quantifies the causal effect of the dependency lever

Returns one structured result the pipeline streams and the trust step reads.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from janus.clients.llm import LLMClient
from janus.config import get_settings
from janus.sim.causal import CausalModel
from janus.sim.cost_model import ScenarioResult, run_manifest, run_scenario
from janus.sim.levers import propose_levers

# From the corpus: combined carrier-routing spend and the modelled cost of a
# peak-window concentration failure (the 2023 incident).
_DEFAULT_CONTRACT_VALUE = 3_360_000.0
_DEFAULT_FAILURE_COST = 3_200_000.0


@dataclass
class SimulationOutput:
    futures: list[dict]
    recommended: str
    causal_effect: dict
    seed_manifest: str
    inputs_echo: list[dict] = field(default_factory=list)
    dependency_anchor: float | None = None


def _pick(results: list[ScenarioResult]) -> str:
    """Best risk-adjusted future: the highest median that isn't 'high' risk.

    A high-risk future is never recommended even if its median leads — the
    point of the guardrail is to refuse the catastrophic tail. Among the rest,
    take the best P50; if every future is high-risk, recommend reject.
    """
    safe = [r for r in results if r.risk_label != "high"]
    if not safe:
        return "reject"
    return max(safe, key=lambda r: r.p50).label


async def simulate(
    action_summary: str,
    lesson: str,
    run_id: str,
    llm: LLMClient,
    contract_value: float = _DEFAULT_CONTRACT_VALUE,
    failure_cost: float = _DEFAULT_FAILURE_COST,
    dependency_anchor: float | None = None,
) -> SimulationOutput:
    scenarios = await propose_levers(action_summary, lesson, contract_value, failure_cost, llm)

    # If the intercepted action carries a concrete dependency level, anchor the
    # "approve" future to it: approve means executing the action as proposed, so
    # its concentration risk should be the action's actual dependency, not the
    # model's generic guess. This is the lever the operator can move — and it's
    # what makes the recommendation provably flip: drop the dependency below the
    # ~70% resilience knee and the approve future stops being high-risk, so the
    # guardrail recommends it instead of forcing a modify.
    if dependency_anchor is not None:
        knee = get_settings().concentration_knee
        anchor = min(1.0, max(0.0, float(dependency_anchor)))
        # Failure probability rises linearly with how far past the knee the share
        # sits (base rate below the knee, climbing to ~base+0.45 at full
        # dependency). This is the corpus relationship, parameterized off the knee.
        base_fp, slope = 0.04, 0.45
        over = max(0.0, anchor - knee) / max(1.0 - knee, 1e-9)
        for s in scenarios:
            if s.label == "approve":
                # Approve = execute the action as proposed: its concentration is
                # the action's actual dependency.
                s.dependency_after = anchor
                s.failure_prob = round(base_fp + slope * over, 3)
            elif s.label == "modify":
                # Modify = consolidate but hold the top vendor just under the knee
                # with a warm fallback — the corpus lesson made concrete. Pin it so
                # it's always the survivable middle, never sliding into the tail
                # with approve when the operator pushes the dependency up.
                s.dependency_after = min(s.dependency_after, knee - 0.05)
                s.failure_prob = min(s.failure_prob, base_fp + 0.02)

    results = [run_scenario(s, run_id) for s in scenarios]
    recommended = _pick(results)

    # The causal contrast: dependency of the most- vs least-aggressive future.
    deps = [s.dependency_after for s in scenarios]
    causal = CausalModel(failure_cost).dependency_effect(low=min(deps), high=max(deps))

    return SimulationOutput(
        futures=[asdict(r) for r in results],
        recommended=recommended,
        causal_effect=causal,
        seed_manifest=run_manifest(run_id, scenarios),
        inputs_echo=[asdict(s) for s in scenarios],
        dependency_anchor=anchor if dependency_anchor is not None else None,
    )
