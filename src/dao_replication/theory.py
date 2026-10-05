"""Closed-form results for budgeted token voting under a power-law aggregator.

A voter's ballot is a vector of token counts t = (t_1, ..., t_m) with a budget B.
The aggregator turns tokens into effective votes with the map  t -> t**alpha:

    alpha = 1     linear / "ranked (weighted)" voting: votes = tokens
    alpha = 1/2   quadratic voting: votes = sqrt(tokens)   (the article's "4 tokens give 2 votes")
    alpha -> 0    approval-like: every option that gets any token counts the same

Everything here is arithmetic on that map; the derivations are in docs/THEORY.md.
The functions are used by tests/test_theory.py (which checks them against brute force)
and by extensions.py (which draws the figures).
"""

from __future__ import annotations

import numpy as np

ALPHA_LINEAR = 1.0
ALPHA_QV = 0.5


def effective_votes(tokens: np.ndarray, alpha: float) -> np.ndarray:
    """Element-wise t**alpha (tokens must be >= 0)."""
    return np.power(np.asarray(tokens, dtype=float), alpha)


def vote_mass(shares: np.ndarray, alpha: float, budget: float = 1.0) -> np.ndarray:
    """Total effective votes a voter casts, sum_j (budget * share_j)**alpha.

    Under QV (alpha = 1/2) the mass lies in [sqrt(B), sqrt(m B)]: a voter who puts everything
    on one option casts sqrt(B) votes, one who spreads evenly over m options casts sqrt(m B).
    Under linear voting it is B whatever the spread.
    """
    s = np.atleast_2d(np.asarray(shares, dtype=float))
    return np.power(budget * s, alpha).sum(axis=1)


def power_share(f_high: float, ratio: float, alpha: float) -> float:
    """Share of total effective votes held by the high-budget group.

    f_high  fraction of voters in the high-budget group (e.g. 0.2)
    ratio   B_high / B_low (e.g. 400 / 25 = 16)
    Voters in a group are assumed to spread their budget identically, so that group members'
    mass differs only through B**alpha. Result: f r^a / (f r^a + 1 - f).
    alpha = 1 gives the token share, alpha = 0 the head-count share.
    """
    w = ratio**alpha
    return f_high * w / (f_high * w + 1.0 - f_high)


def minority_threshold(k: int, alpha: float) -> float:
    """Smallest population share pi at which a concentrated minority beats a diffuse majority.

    The minority puts its whole budget on option A. The other 1 - pi voters split their budget
    evenly over k other options. A wins iff  pi B^a > (1 - pi) (B/k)^a,  i.e. pi > 1 / (1 + k^a).
    Linear: 1/(1+k); QV: 1/(1+sqrt(k)); approval-like (alpha -> 0): 1/2.
    """
    return 1.0 / (1.0 + float(k) ** alpha)


def sybil_gain_split(k: int, alpha: float) -> float:
    """Gain from splitting one balance b into k wallets of b/k, all voting alike.

    k (b/k)^a / b^a = k^(1-a): 1 for linear voting, sqrt(k) for QV, k as alpha -> 0.
    """
    return float(k) ** (1.0 - alpha)


def sybil_gain_new_budgets(k: int, alpha: float) -> float:
    """Gain when each of k identities receives its own full budget B (one person, one budget
    assumed): k B^a / B^a = k for every alpha. The concave map gives no protection here."""
    return float(k)


def attacker_share_split(attacker_fraction: float, k: int, alpha: float) -> float:
    """Attacker's share of effective votes when a fraction a of the (equal-balance) voters
    split their balance over k wallets and everyone else votes with a single wallet.

    Each honest voter casts 1 vote-unit^a = 1 (balance normalised to 1, all on their own
    option); an attacker casts k^(1-a). Share = a g / (a g + 1 - a), g = k^(1-a).
    """
    g = sybil_gain_split(k, alpha)
    return attacker_fraction * g / (attacker_fraction * g + 1.0 - attacker_fraction)


def qv_optimal_tokens(values: np.ndarray, budget: float, pivot: np.ndarray | None = None) -> np.ndarray:
    """Benchmark for a vote-maximising QV voter with marginal values w_j = u_j q_j.

    Maximise sum_j w_j v_j subject to sum_j v_j^2 = B (tokens t_j = v_j^2): the first-order
    condition gives v_j proportional to w_j, so tokens are proportional to w_j^2.
    `pivot` (q_j) defaults to equal pivot probabilities.
    """
    w = np.asarray(values, dtype=float)
    if pivot is not None:
        w = w * np.asarray(pivot, dtype=float)
    t = w**2
    return budget * t / t.sum()


def linear_optimal_tokens(values: np.ndarray, budget: float, pivot: np.ndarray | None = None) -> np.ndarray:
    """Benchmark for a linear-voting voter: the objective is linear in tokens, so the whole
    budget goes to the option with the largest w_j (ties split evenly)."""
    w = np.asarray(values, dtype=float)
    if pivot is not None:
        w = w * np.asarray(pivot, dtype=float)
    top = np.isclose(w, w.max())
    t = np.zeros_like(w)
    t[top] = budget / top.sum()
    return t
