"""Compositional-data re-analysis of token allocations.

A ballot's allocation shares are a composition: non-negative, summing to one. Treating the four
ratios as free coordinates (as MANOVA on raw ratios does) ignores that constraint and, when a
voter spends the whole budget, makes the covariance matrix singular. The standard remedy is to
work in log-ratio coordinates (Aitchison; Egozcue et al. 2003). Two practical issues:

* Zeros. 39 % of ballots give no tokens to at least one option. Log-ratios need positive
  entries, so zeros are replaced with the Bayesian-multiplicative rule (Martin-Fernandez et al.
  2015): a zero count c_j = 0 becomes (s * p_j) / (n + s), with prior weights p_j = 1/m and prior
  strength s; non-zero entries are rescaled to keep the sum at one. Because n is the number of
  tokens actually spent, a voter with a 25-token budget has a coarser grid than one with 400,
  and the replacement value reflects that. Results are reported for several s.
* Slack. Shares here are of tokens actually spent (the article's ratio uses the budget; the
  budget-slack effect is analysed separately in sensitivity.py).

Tests, all for the effect of the voting method (quadratic vs ranked) with voting power in the
model, by round:
  ilr_manova    MANOVA (Pillai) on the three isometric log-ratio coordinates
  permanova     distance-based test on Aitchison distances, labels permuted within power strata
  dirichlet_lr  likelihood-ratio test of a Dirichlet regression (mean via softmax, common precision)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import gammaln, softmax
from statsmodels.multivariate.manova import MANOVA

from .config import CHOICES, SEED


def bm_replace(counts: np.ndarray, s: float = 1.0) -> np.ndarray:
    """Bayesian-multiplicative zero replacement for rows of counts (n, m); returns compositions."""
    c = np.asarray(counts, dtype=float)
    n = c.sum(axis=1, keepdims=True)
    m = c.shape[1]
    x = c / n
    zero = c == 0
    rep = (s / m) / (n + s)  # (n, 1), same for every zero in the row
    mass_zero = (zero * rep).sum(axis=1, keepdims=True)
    out = np.where(zero, rep, x * (1.0 - mass_zero))
    return out / out.sum(axis=1, keepdims=True)


def clr(x: np.ndarray) -> np.ndarray:
    lx = np.log(x)
    return lx - lx.mean(axis=1, keepdims=True)


def helmert_basis(m: int) -> np.ndarray:
    """Orthonormal basis (m-1, m) of the clr hyperplane (a Helmert contrast matrix)."""
    V = np.zeros((m - 1, m))
    for i in range(1, m):
        V[i - 1, :i] = 1.0 / i
        V[i - 1, i] = -1.0
        V[i - 1] *= np.sqrt(i / (i + 1.0))
    return V


def ilr(x: np.ndarray) -> np.ndarray:
    return clr(x) @ helmert_basis(x.shape[1]).T


def aitchison_dist(x: np.ndarray) -> np.ndarray:
    z = clr(x)
    d2 = ((z[:, None, :] - z[None, :, :]) ** 2).sum(axis=2)
    return np.sqrt(d2)


def prepare(votes: pd.DataFrame, s: float = 1.0) -> pd.DataFrame:
    """Rows with at least one token spent, plus zero-replaced composition columns x1..x4 and ilr columns."""
    d = votes[votes[CHOICES].sum(axis=1) > 0].reset_index(drop=True).copy()
    x = bm_replace(d[CHOICES].to_numpy(dtype=float), s)
    z = ilr(x)
    for j in range(4):
        d[f"x{j + 1}"] = x[:, j]
    for j in range(3):
        d[f"z{j + 1}"] = z[:, j]
    return d


# ---------------------------------------------------------------- tests
def ilr_manova(d: pd.DataFrame) -> dict:
    res = MANOVA.from_formula("z1 + z2 + z3 ~ quadratic + same", data=d).mv_test()
    out = {}
    for term in ("quadratic", "same"):
        r = res.results[term]["stat"].loc["Pillai's trace"]
        out[term] = (float(r["Value"]), float(r["Pr > F"]))
    return out


def _hat(X: np.ndarray) -> np.ndarray:
    return X @ np.linalg.pinv(X.T @ X) @ X.T


def _gower(dist: np.ndarray) -> np.ndarray:
    n = dist.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    return J @ (-0.5 * dist**2) @ J


def permanova_term(d: pd.DataFrame, x: np.ndarray, term: str, n_perm: int, seed: int = SEED) -> tuple[float, float]:
    """Pseudo-F for `term` given the other factor; labels permuted within strata of the other factor."""
    rng = np.random.default_rng(seed)
    other = "same" if term == "quadratic" else "quadratic"
    G = _gower(aitchison_dist(x))
    n = len(d)
    ones = np.ones((n, 1))
    z_other = d[[other]].to_numpy(dtype=float)
    z_term = d[term].to_numpy(dtype=float)
    I = np.eye(n)

    def pseudo_f(t):
        Xf = np.hstack([ones, z_other, t[:, None]])
        Xr = np.hstack([ones, z_other])
        Hf, Hr = _hat(Xf), _hat(Xr)
        ss_term = np.trace((Hf - Hr) @ G)
        ss_res = np.trace((I - Hf) @ G)
        return ss_term / (ss_res / (n - Xf.shape[1]))

    obs = pseudo_f(z_term)
    strata = [np.where(d[other].to_numpy() == v)[0] for v in np.unique(d[other])]
    cnt = 0
    for _ in range(n_perm):
        t = z_term.copy()
        for ix in strata:
            t[ix] = rng.permutation(t[ix])
        cnt += pseudo_f(t) >= obs - 1e-12
    return float(obs), (cnt + 1) / (n_perm + 1)


def dirichlet_fit(y: np.ndarray, X: np.ndarray) -> tuple[float, np.ndarray, float]:
    """Dirichlet regression, mean = softmax(X B) with the last option as reference, precision exp(g).
    Returns (log-likelihood, B, precision)."""
    n, p = X.shape
    m = y.shape[1]
    ly = np.log(y)

    def unpack(theta):
        B = np.zeros((p, m))
        B[:, : m - 1] = theta[: p * (m - 1)].reshape(p, m - 1)
        return B, theta[-1]

    def nll(theta):
        B, g = unpack(theta)
        mu = softmax(X @ B, axis=1)
        phi = np.exp(g)
        a = phi * mu
        ll = gammaln(phi) - gammaln(a).sum(axis=1) + ((a - 1.0) * ly).sum(axis=1)
        return -ll.sum()

    best = None
    for start in (0.0, 0.5):
        theta0 = np.r_[np.zeros(p * (m - 1)), np.log(5.0) + start]
        r = optimize.minimize(nll, theta0, method="BFGS")
        if best is None or r.fun < best.fun:
            best = r
    B, g = unpack(best.x)
    return -best.fun, B, float(np.exp(g))


def dirichlet_lr(d: pd.DataFrame, term: str) -> tuple[float, float, float]:
    """LR test dropping `term` (3 df). Returns (chi2, p, fitted precision of the full model)."""
    y = d[["x1", "x2", "x3", "x4"]].to_numpy()
    other = "same" if term == "quadratic" else "quadratic"
    n = len(d)
    Xf = np.column_stack([np.ones(n), d[other], d[term]])
    Xr = np.column_stack([np.ones(n), d[other]])
    llf, _, phi = dirichlet_fit(y, Xf)
    llr, _, _ = dirichlet_fit(y, Xr)
    chi2 = 2 * (llf - llr)
    return float(chi2), float(stats.chi2.sf(chi2, df=3)), phi


def run_tests(votes: pd.DataFrame, s_grid=(0.25, 1.0, 4.0), n_perm: int = 5_000) -> pd.DataFrame:
    rows = []
    for s in s_grid:
        d_all = prepare(votes, s)
        for rnd, d in d_all.groupby("round"):
            d = d.reset_index(drop=True)
            x = d[["x1", "x2", "x3", "x4"]].to_numpy()
            mv = ilr_manova(d)
            for term in ("quadratic", "same"):
                pf, pp = permanova_term(d, x, term, n_perm)
                chi2, plr, phi = dirichlet_lr(d, term)
                rows.append(
                    {
                        "round": rnd,
                        "zero_prior_s": s,
                        "term": "voting method (quadratic)" if term == "quadratic" else "voting power (equal)",
                        "n": len(d),
                        "ilr_pillai": mv[term][0],
                        "ilr_manova_p": mv[term][1],
                        "permanova_F": pf,
                        "permanova_p": pp,
                        "dirichlet_chi2": chi2,
                        "dirichlet_lr_p": plr,
                        "dirichlet_precision": phi,
                    }
                )
    return pd.DataFrame(rows)


def power_groups(votes: pd.DataFrame, n_perm: int = 10_000, s: float = 1.0, seed: int = SEED) -> pd.DataFrame:
    """Within the 20/80 cells: do high-budget voters (400) allocate differently from low-budget (25)?"""
    d = prepare(votes[votes["cond"].str.endswith("early")], s)
    d["high"] = (d["votes_given"] >= 100).astype(int)
    rng = np.random.default_rng(seed)
    rows = []
    for rnd, g in list(d.groupby("round")) + [("pooled", d)]:
        g = g.reset_index(drop=True)
        x = g[["x1", "x2", "x3", "x4"]].to_numpy()
        G = _gower(aitchison_dist(x))
        n = len(g)
        h = g["high"].to_numpy(dtype=float)
        ones = np.ones((n, 1))
        Xr = np.hstack([ones, g[["quadratic"]].to_numpy(dtype=float)])
        I = np.eye(n)

        def pf(hv):
            Xf = np.hstack([Xr, hv[:, None]])
            Hf, Hr = _hat(Xf), _hat(Xr)
            return np.trace((Hf - Hr) @ G) / (np.trace((I - Hf) @ G) / (n - Xf.shape[1]))

        obs = pf(h)
        cnt = sum(pf(rng.permutation(h)) >= obs - 1e-12 for _ in range(n_perm))
        top_hi = g.loc[g["high"] == 1, CHOICES].to_numpy().argmax(axis=1) + 1
        top_lo = g.loc[g["high"] == 0, CHOICES].to_numpy().argmax(axis=1) + 1
        rows.append(
            {
                "round": rnd,
                "n_high": int(h.sum()),
                "n_low": int(n - h.sum()),
                "permanova_F": float(obs),
                "p_perm": (cnt + 1) / (n_perm + 1),
                **{f"top_choice_{j}_high": float((top_hi == j).mean()) for j in range(1, 5)},
                **{f"top_choice_{j}_low": float((top_lo == j).mean()) for j in range(1, 5)},
            }
        )
    return pd.DataFrame(rows)
