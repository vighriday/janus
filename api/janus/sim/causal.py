"""The causal layer — a literal do() intervention over the decision's levers.

The Monte Carlo cost model produces the outcome bands. This adds the thing that
earns the word "counterfactual": a graphical causal model where we can intervene
on a single lever — do(dependency := 0.7) — and read how the outcome would
change, holding the rest of the world fixed. It's small and deterministic
(manual linear mechanisms over a fixed DAG), so it runs in milliseconds and
reproduces exactly.

DAG:  dependency_pct ─┐
      contract_value ─┼─→ resilience_loss ─┐
      discount       ─┴─→ annual_savings  ─┴─→ net_value
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import dowhy.gcm as gcm

# Reuse the same resilience knee the cost model uses, so the two agree.
from janus.sim.cost_model import _RESILIENCE_KNEE, _resilience_multiplier

_NODES = ["dependency_pct", "contract_value", "discount", "resilience_loss", "annual_savings", "net_value"]


def _build_dag() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_edges_from([
        ("dependency_pct", "resilience_loss"),
        ("contract_value", "resilience_loss"),
        ("contract_value", "annual_savings"),
        ("discount", "annual_savings"),
        ("resilience_loss", "net_value"),
        ("annual_savings", "net_value"),
    ])
    return g


def _synthetic_history(failure_cost: float, n: int = 800, seed: int = 13) -> pd.DataFrame:
    """A small synthetic 'observed history' to fit mechanisms on. Columns == nodes.

    These are the relationships the corpus encodes, expressed as data: savings
    scale with discount; resilience loss climbs past the dependency knee.
    """
    rng = np.random.default_rng(seed)
    dependency = rng.uniform(0.4, 1.0, n)
    contract = rng.uniform(2.0e6, 4.0e6, n)
    discount = rng.uniform(0.0, 0.12, n)
    savings = discount * contract + rng.normal(0, 5000, n)
    # Resilience loss is the *expected* loss: failure probability rises with
    # dependency past the knee, and the multiplier amplifies it. Using the
    # expected value (probability × multiplier × cost) rather than a hard
    # Bernoulli draw keeps the relationship smooth and monotonic, so the fitted
    # linear mechanism captures the correct sign — dependency up, loss up — every
    # time, instead of being dominated by Bernoulli/interaction noise on a small
    # sample. The do() contrast then reproduces deterministically and never flips.
    mult = np.array([_resilience_multiplier(d) for d in dependency])
    fail_prob = 0.05 + 0.30 * np.clip((dependency - _RESILIENCE_KNEE) / 0.3, 0, 1)
    resilience = fail_prob * failure_cost * mult + rng.normal(0, 2000, n)
    resilience = np.clip(resilience, 0, None)
    net = savings - resilience
    return pd.DataFrame({
        "dependency_pct": dependency, "contract_value": contract, "discount": discount,
        "resilience_loss": resilience, "annual_savings": savings, "net_value": net,
    })


class CausalModel:
    """Fitted invertible SCM over the lever DAG. do()-interventions + counterfactuals."""

    def __init__(self, failure_cost: float) -> None:
        self.scm = gcm.InvertibleStructuralCausalModel(_build_dag())
        data = _synthetic_history(failure_cost)
        # Manual mechanisms: roots empirical, downstream additive-noise linear.
        # Deterministic and fast — no model search — and invertible (counterfactuals work).
        for root in ("dependency_pct", "contract_value", "discount"):
            self.scm.set_causal_mechanism(root, gcm.EmpiricalDistribution())
        # annual_savings is linear in its parents; resilience_loss and the net it
        # feeds are non-linear in dependency (the convex knee), so a linear
        # mechanism there averages across the kink and can land near-zero slope.
        # A gradient-boosted mechanism captures the knee, so the do() contrast is
        # correctly signed and stable — still a real fitted SCM, just expressive
        # enough for the shape the corpus actually has.
        self.scm.set_causal_mechanism(
            "annual_savings", gcm.AdditiveNoiseModel(gcm.ml.create_linear_regressor())
        )
        for child in ("resilience_loss", "net_value"):
            self.scm.set_causal_mechanism(
                child,
                gcm.AdditiveNoiseModel(gcm.ml.create_hist_gradient_boost_regressor()),
            )
        gcm.config.disable_progress_bars()
        gcm.fit(self.scm, data)

    def intervene_dependency(self, dependency: float, n: int = 3000) -> dict:
        """Expected outcomes under do(dependency_pct := value).

        We report expected resilience_loss (the quantity dependency causally
        drives — monotonic past the knee, captured by the fitted mechanism)
        alongside expected net_value. The resilience effect is the headline causal
        claim; the Monte Carlo cost model supplies the downside-tail bands.

        The interventional sampling is seeded so the contrast reproduces exactly:
        same lever, same number, every run — the reproducibility the demo rests on.
        """
        np.random.seed(20260614)
        samples = gcm.interventional_samples(
            self.scm,
            interventions={"dependency_pct": lambda _d, v=dependency: v},
            num_samples_to_draw=n,
        )
        return {
            "resilience_loss": float(np.mean(samples["resilience_loss"])),
            "net_value": float(np.mean(samples["net_value"])),
        }

    def dependency_effect(self, low: float, high: float) -> dict:
        """The headline causal claim: holding everything else fixed, moving the
        top-vendor dependency from `high` down to `low` reduces expected
        resilience loss by this much — a literal do()-intervention contrast."""
        hi = self.intervene_dependency(high)
        lo = self.intervene_dependency(low)
        return {
            "dependency_high": high,
            "dependency_low": low,
            "resilience_loss_at_high": round(hi["resilience_loss"], 2),
            "resilience_loss_at_low": round(lo["resilience_loss"], 2),
            "resilience_saved": round(hi["resilience_loss"] - lo["resilience_loss"], 2),
        }
