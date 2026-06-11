"""The transparent cost model behind the counterfactual simulation.

The language model never produces a number. It proposes qualitative levers
(how aggressive the consolidation is, what the discount might be); this module
turns those levers into a distribution of outcomes with a fixed seed, so the
same inputs always reproduce the same figures and changing an input provably
moves them. Every run records its seed and an input hash so any number on screen
is auditable.

Two outcomes are modelled per scenario:
  - annual_savings: consolidation discount on the combined contract value
  - resilience_loss: expected cost of a dependency-concentration failure,
    which rises sharply once one vendor carries too much of a critical flow
    (the lesson the corpus actually teaches).
Net value = savings - resilience_loss.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

FORMULA_VERSION = "cost-model-1"


def _resilience_knee() -> float:
    """The concentration knee, from config. Above this share on one vendor a
    concentration failure stops being absorbable — the policy ceiling the corpus
    encodes, expressed as a knee in the resilience-loss curve, not a hard cliff."""
    from janus.config import get_settings

    return get_settings().concentration_knee


# Module-level snapshot for the hot loop and for callers that import the constant.
# Kept in sync with config at import; config is the single source of truth.
_RESILIENCE_KNEE = _resilience_knee()


@dataclass
class ScenarioInputs:
    """The levers for one future. The LLM proposes these; the model computes from them."""

    label: str
    vendor_count_after: int
    contract_value: float  # combined annual spend across the affected vendors
    dependency_after: float  # share of the critical flow on the top vendor, 0..1
    # Triangular discount belief: (min, likely, max) consolidation discount.
    discount_lo: float
    discount_mode: float
    discount_hi: float
    # Probability a peak-window concentration failure occurs over the term.
    failure_prob: float
    # Cost of such a failure if it happens (from the seeded incident history).
    failure_cost: float


@dataclass
class ScenarioResult:
    label: str
    p10: float
    p50: float
    p90: float
    risk_label: str
    mean_savings: float
    mean_resilience_loss: float
    drivers: dict[str, float] = field(default_factory=dict)


def _seed_from(run_id: str, label: str) -> int:
    """Deterministic per-branch seed: same run + branch always reproduces."""
    h = hashlib.sha256(f"{run_id}:{label}:{FORMULA_VERSION}".encode()).hexdigest()
    return int(h[:8], 16)


def _resilience_multiplier(dependency: float) -> float:
    """Expected-loss multiplier that climbs past the 70% concentration knee."""
    if dependency <= _RESILIENCE_KNEE:
        return dependency / _RESILIENCE_KNEE * 0.5  # 0..0.5 below the knee
    # Above the knee it accelerates: a total-dependency outage is unsurvivable.
    over = (dependency - _RESILIENCE_KNEE) / (1.0 - _RESILIENCE_KNEE)
    return 0.5 + over * over * 1.5  # 0.5..2.0, convex


def run_scenario(inputs: ScenarioInputs, run_id: str, n: int = 5000) -> ScenarioResult:
    """Monte Carlo a single future. Net value = savings - expected resilience loss."""
    rng = np.random.default_rng(_seed_from(run_id, inputs.label))

    # Savings: triangular over the believed consolidation discount.
    c = (inputs.discount_mode - inputs.discount_lo) / max(
        inputs.discount_hi - inputs.discount_lo, 1e-9
    )
    discount = stats.triang.rvs(
        c, loc=inputs.discount_lo, scale=(inputs.discount_hi - inputs.discount_lo),
        size=n, random_state=rng,
    )
    savings = discount * inputs.contract_value

    # Resilience loss: a Bernoulli failure draw times its cost, scaled by how far
    # past the concentration knee this scenario sits.
    mult = _resilience_multiplier(inputs.dependency_after)
    failed = rng.random(n) < inputs.failure_prob
    resilience_loss = failed * inputs.failure_cost * mult

    net = savings - resilience_loss
    p10, p50, p90 = (float(x) for x in np.percentile(net, [10, 50, 90]))

    # Risk is about the downside, not the spread: a future whose bad case (P10)
    # wipes out many times its expected gain is high-risk even if the median is
    # positive. This is what makes full consolidation read as risky despite a
    # decent P50 — the resilience tail.
    downside = -p10  # how bad the bad case is (positive number when P10 < 0)
    if p50 <= 0 or downside > 4 * max(p50, 1):
        risk = "high"
    elif downside > max(p50, 1):
        risk = "elevated"
    else:
        risk = "low"

    return ScenarioResult(
        label=inputs.label,
        p10=round(p10, 2), p50=round(p50, 2), p90=round(p90, 2),
        risk_label=risk,
        mean_savings=round(float(savings.mean()), 2),
        mean_resilience_loss=round(float(resilience_loss.mean()), 2),
        drivers={
            "dependency_after": inputs.dependency_after,
            "resilience_multiplier": round(mult, 3),
            "failure_prob": inputs.failure_prob,
        },
    )


def run_manifest(run_id: str, scenarios: list[ScenarioInputs]) -> str:
    """A hash of the exact inputs + formula version, so a run is reproducible."""
    payload = {
        "run_id": run_id,
        "formula_version": FORMULA_VERSION,
        "scenarios": [s.__dict__ for s in scenarios],
    }
    blob = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()
