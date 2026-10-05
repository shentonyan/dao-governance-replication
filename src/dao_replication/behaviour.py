"""How concentrated are ballots, and does the rule change that?

Under quadratic voting a vote-maximising participant who values option j at w_j spends tokens
proportional to w_j^2 (theory.qv_optimal_tokens); a participant who simply spreads tokens in
proportion to preference (the "expressive" benchmark) spends them proportional to w_j; under
linear voting a vote-maximising participant puts everything on one option. So if QV
participants responded to the quadratic cost, their ballots would be more concentrated than
ranked-arm ballots. This module measures ballot concentration and tests that.

Concentration measures use allocation shares s_j = t_j / sum(t):
  hhi        sum_j s_j^2                (1/4 = even over four options, 1 = everything on one)
  top_share  max_j s_j
  n_nonzero  number of options with at least one token
  qv_mass    sum_j sqrt(s_j)            (effective votes per unit of sqrt-budget; 1 to 2 for m = 4)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .config import CHOICES, SEED


def ballot_measures(votes: pd.DataFrame) -> pd.DataFrame:
    t = votes[CHOICES].to_numpy(dtype=float)
    alloc = t.sum(axis=1)
    ok = alloc > 0
    s = np.zeros_like(t)
    s[ok] = t[ok] / alloc[ok, None]
    out = votes[["round", "cond", "quadratic", "same", "votes_given"]].copy()
    out["hhi"] = (s**2).sum(axis=1)
    out["top_share"] = s.max(axis=1)
    out["n_nonzero"] = (t > 0).sum(axis=1)
    out["qv_mass"] = np.sqrt(s).sum(axis=1)
    out["top_choice"] = s.argmax(axis=1) + 1
    return out[ok].reset_index(drop=True)


def _perm_p(a: np.ndarray, b: np.ndarray, n_perm: int, rng) -> float:
    obs = a.mean() - b.mean()
    pool = np.r_[a, b]
    na = len(a)
    cnt = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        cnt += abs(pool[:na].mean() - pool[na:].mean()) >= abs(obs) - 1e-12
    return (cnt + 1) / (n_perm + 1)


def invariance_table(votes: pd.DataFrame, n_perm: int = 10_000, n_boot: int = 5_000, seed: int = SEED) -> pd.DataFrame:
    """Quadratic vs ranked, per round and measure: difference, permutation p, 95 % bootstrap CI,
    and an equivalence check against a margin of half a pooled SD (a "medium" effect)."""
    rng = np.random.default_rng(seed)
    m = ballot_measures(votes)
    rows = []
    for rnd, d in m.groupby("round"):
        for measure in ["hhi", "top_share", "n_nonzero", "qv_mass"]:
            q = d.loc[d["quadratic"] == 1, measure].to_numpy()
            r = d.loc[d["quadratic"] == 0, measure].to_numpy()
            diff = q.mean() - r.mean()
            sp = np.sqrt(((len(q) - 1) * q.var(ddof=1) + (len(r) - 1) * r.var(ddof=1)) / (len(q) + len(r) - 2))
            boots = np.array(
                [rng.choice(q, len(q)).mean() - rng.choice(r, len(r)).mean() for _ in range(n_boot)]
            )
            lo, hi = np.percentile(boots, [2.5, 97.5])
            margin = 0.5 * sp
            rows.append(
                {
                    "round": rnd,
                    "measure": measure,
                    "n_quadratic": len(q),
                    "n_ranked": len(r),
                    "mean_quadratic": q.mean(),
                    "mean_ranked": r.mean(),
                    "diff": diff,
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "cohen_d": diff / sp,
                    "p_perm": _perm_p(q, r, n_perm, rng),
                    "equiv_margin_half_sd": margin,
                    "ci_inside_margin": bool(lo > -margin and hi < margin),
                }
            )
    return pd.DataFrame(rows)


def _hhi_of_power(shares: np.ndarray, gamma: float) -> float:
    """Mean HHI after re-weighting each ballot's shares by s^gamma and renormalising (zeros stay zero)."""
    p = np.power(shares, gamma)
    p = p / p.sum(axis=1, keepdims=True)
    return float((p**2).sum(axis=1).mean())


def relative_gamma(votes: pd.DataFrame, n_boot: int = 2000, seed: int = SEED) -> pd.DataFrame:
    """Concentration exponent of quadratic ballots relative to ranked ballots.

    Finds gamma such that raising ranked-arm allocation shares to the power gamma (and
    renormalising) gives the quadratic arm's mean HHI. gamma = 1: same concentration;
    gamma = 2: what a vote-maximising QV voter would do relative to an expressive ranked voter
    (tokens proportional to w^2 versus w). Bootstrap 95 % interval, per round and pooled.
    Random assignment to arms is what justifies comparing the two arms' ballot distributions.
    """
    rng = np.random.default_rng(seed)
    t = votes[CHOICES].to_numpy(dtype=float)
    alloc = t.sum(axis=1)
    ok = alloc > 0
    s = np.zeros_like(t)
    s[ok] = t[ok] / alloc[ok, None]
    base = votes[ok].reset_index(drop=True)
    s = s[ok]

    def solve(sq, sr):
        target = (sq**2).sum(axis=1).mean()
        f = lambda g: _hhi_of_power(sr, g) - target  # noqa: E731
        lo, hi = 0.2, 6.0
        if f(lo) * f(hi) > 0:
            return np.nan
        return brentq(f, lo, hi)

    rows = []
    for label, mask in [("round 1", base["round"] == 1), ("round 2", base["round"] == 2), ("pooled", base["round"] > 0)]:
        sq = s[(mask & (base["quadratic"] == 1)).to_numpy()]
        sr = s[(mask & (base["quadratic"] == 0)).to_numpy()]
        g = solve(sq, sr)
        boots = []
        for _ in range(n_boot):
            gb = solve(sq[rng.integers(0, len(sq), len(sq))], sr[rng.integers(0, len(sr), len(sr))])
            if not np.isnan(gb):
                boots.append(gb)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append(
            {
                "subset": label,
                "n_quadratic": len(sq),
                "n_ranked": len(sr),
                "mean_hhi_quadratic": float((sq**2).sum(axis=1).mean()),
                "mean_hhi_ranked": float((sr**2).sum(axis=1).mean()),
                "gamma_hat": g,
                "ci_lo": lo,
                "ci_hi": hi,
                "excludes_1": bool(lo > 1 or hi < 1),
                "excludes_2": bool(lo > 2 or hi < 2),
            }
        )
    return pd.DataFrame(rows)
