"""Monte-Carlo counterfactuals for the 20/80 design, calibrated on the released ballots.

Model (deliberately minimal). Each voter has a preference vector theta over the four options.
Ballots are *expressive*: a voter spreads the budget in proportion to theta, which is what the
released data support (behaviour.py: QV and ranked ballots are equally concentrated). High-budget
voters (fraction f, budget r times the low budget) draw theta from Dirichlet(kappa * mu_high),
the rest from Dirichlet(kappa * mu_low). The aggregator scores option j as sum_i (B_i theta_ij)^alpha.

  alpha = 1      tokens (linear)
  alpha = 1/2    sqrt(tokens) (quadratic voting)
  "equal"        every voter counts once: score_j = sum_i theta_ij (budgets ignored)

mu_high, mu_low and kappa are taken from round 1 of the 20/80 arms (the only round where the
two groups differ detectably); kappa is the fitted Dirichlet precision. These are calibration
choices, not estimates of a population; the figures are about how the rules respond, not about
the real participants. The model says nothing about strategic behaviour, which the data do not show.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CHOICES, SEED
from . import compositional as co


def calibrate(votes: pd.DataFrame, rnd: int = 1, s: float = 1.0) -> dict:
    """mu_high, mu_low (mean zero-replaced shares of >=100-token and 25-token voters in the
    20/80 arms of round `rnd`) and the Dirichlet precision kappa of the full-sample regression."""
    d = co.prepare(votes[votes["round"] == rnd], s)
    early = d[d["cond"].str.endswith("early")]
    hi = early[early["votes_given"] >= 100]
    lo = early[early["votes_given"] < 100]
    x = ["x1", "x2", "x3", "x4"]
    y = d[x].to_numpy()
    n = len(d)
    X = np.column_stack([np.ones(n), d["quadratic"], d["same"]])
    _, _, phi = co.dirichlet_fit(y, X)
    return {
        "mu_high": hi[x].mean().to_numpy(),
        "mu_low": lo[x].mean().to_numpy(),
        "kappa": phi,
        "n_high": len(hi),
        "n_low": len(lo),
    }


def _winner_scores(theta: np.ndarray, budget: np.ndarray, alpha: float | None) -> np.ndarray:
    """Scores per option for a batch: theta (sims, n, m), budget (n,) -> (sims, m)."""
    if alpha is None:  # equal weight
        return theta.sum(axis=1)
    return np.power(budget[None, :, None] * theta, alpha).sum(axis=1)


def p_high_wins(
    f: float,
    ratio: float,
    alpha: float | None,
    mu_high: np.ndarray,
    mu_low: np.ndarray,
    kappa: float,
    n: int = 100,
    n_sims: int = 400,
    rng: np.random.Generator | None = None,
    target: int | None = None,
) -> float:
    """Probability that the high-budget group's modal option wins (or option `target` if given)."""
    rng = rng or np.random.default_rng(SEED)
    n_hi = max(1, int(round(f * n)))
    budget = np.r_[np.full(n_hi, ratio), np.ones(n - n_hi)]
    th_hi = rng.dirichlet(kappa * mu_high, size=(n_sims, n_hi))
    th_lo = rng.dirichlet(kappa * mu_low, size=(n_sims, n - n_hi))
    theta = np.concatenate([th_hi, th_lo], axis=1)
    sc = _winner_scores(theta, budget, alpha)
    win = sc.argmax(axis=1)
    tgt = int(np.argmax(mu_high)) if target is None else target
    return float((win == tgt).mean())


def phase_grid(cal: dict, fs: np.ndarray, ratios: np.ndarray, n: int = 100, n_sims: int = 300, seed: int = SEED):
    """P(high group's modal option wins) on a grid of (f, ratio) for tokens, sqrt and equal weight.

    The target is the modal option of the high-budget group *when it differs from the low-budget
    group's modal option*; if both groups share a modal option the question is moot, so the
    function raises.
    """
    t_hi, t_lo = int(np.argmax(cal["mu_high"])), int(np.argmax(cal["mu_low"]))
    if t_hi == t_lo:
        raise ValueError("both groups share the modal option; choose another calibration")
    rng = np.random.default_rng(seed)
    out = {}
    for name, alpha in (("tokens", 1.0), ("qv", 0.5), ("equal", None)):
        grid = np.zeros((len(ratios), len(fs)))
        for i, r in enumerate(ratios):
            for j, f in enumerate(fs):
                grid[i, j] = p_high_wins(f, r, alpha, cal["mu_high"], cal["mu_low"], cal["kappa"], n, n_sims, rng, t_hi)
        out[name] = grid
    return out, (t_hi + 1, t_lo + 1)
