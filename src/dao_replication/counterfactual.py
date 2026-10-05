"""Same ballots, different aggregation rules.

The article studies how participants spent tokens. A decision, however, depends on how the
ballots are added up. This module applies several aggregators to the *released ballots* of each
(round, condition) cell and bootstraps the winner.

It treats ballots as exchangeable across the quadratic and ranked arms, i.e. it assumes people
would have spent their tokens the same way under another rule. That is itself tested in
behaviour.py; where it fails the counterfactual should be read as "what these ballots would
decide", not as "what the other arm would have decided".

Aggregators (scores per option, higher wins):
  tokens            sum of token counts                       (linear, budget-weighted)
  qv_votes          sum of sqrt(token count)                  (the article's QV rule)
  tokens_equalised  sum of each voter's allocation shares     (linear, one voter one unit)
  qv_equalised      sum of sqrt(allocation share)             (QV with equal budgets)
  plurality         one vote for the option(s) with most tokens (ties split)
  borda             rank points from each voter's token order  (ties get average rank)
  copeland          pairwise majority wins between options     (ties count one half)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .config import CHOICES, CONDITIONS, SEED

AGGREGATORS = ["tokens", "qv_votes", "tokens_equalised", "qv_equalised", "plurality", "borda", "copeland"]

LABELS = {
    "tokens": "Tokens (linear)",
    "qv_votes": "sqrt(tokens) (QV)",
    "tokens_equalised": "Shares (linear, equal weight)",
    "qv_equalised": "sqrt(shares) (QV, equal budgets)",
    "plurality": "Plurality of top choice",
    "borda": "Borda",
    "copeland": "Copeland (pairwise)",
}


def scores(t: np.ndarray, agg: str) -> np.ndarray:
    """Score vector (length m) for ballots t of shape (n, m) of non-negative token counts."""
    t = np.asarray(t, dtype=float)
    alloc = t.sum(axis=1, keepdims=True)
    keep = alloc[:, 0] > 0
    t, alloc = t[keep], alloc[keep]
    if agg == "tokens":
        return t.sum(axis=0)
    if agg == "qv_votes":
        return np.sqrt(t).sum(axis=0)
    if agg == "tokens_equalised":
        return (t / alloc).sum(axis=0)
    if agg == "qv_equalised":
        return np.sqrt(t / alloc).sum(axis=0)
    if agg == "plurality":
        top = np.isclose(t, t.max(axis=1, keepdims=True))
        return (top / top.sum(axis=1, keepdims=True)).sum(axis=0)
    if agg == "borda":
        return np.vstack([rankdata(row, method="average") - 1.0 for row in t]).sum(axis=0)
    if agg == "copeland":
        m = t.shape[1]
        pair = np.zeros((m, m))
        for j in range(m):
            for k in range(m):
                if j != k:
                    pair[j, k] = (t[:, j] > t[:, k]).sum() + 0.5 * (t[:, j] == t[:, k]).sum()
        wins = np.zeros(m)
        for j in range(m):
            for k in range(m):
                if j != k:
                    wins[j] += 1.0 if pair[j, k] > pair[k, j] else (0.5 if pair[j, k] == pair[k, j] else 0.0)
        return wins
    raise ValueError(agg)


def winner(sc: np.ndarray) -> int:
    """1-based index of the winner; exact ties go to the lowest index (see is_tie)."""
    return int(np.argmax(sc)) + 1


def is_tie(sc: np.ndarray) -> bool:
    """True when the two highest scores are equal (the reported winner is then arbitrary)."""
    top2 = np.sort(np.asarray(sc, dtype=float))[::-1][:2]
    return bool(np.isclose(top2[0], top2[1]))


def cell_table(votes: pd.DataFrame, n_boot: int = 2000, seed: int = SEED) -> pd.DataFrame:
    """Winner, shares and bootstrap win probabilities per (round, cond, aggregator)."""
    rng = np.random.default_rng(seed)
    rows = []
    for (rnd, cond), d in votes.groupby(["round", "cond"]):
        t = d[CHOICES].to_numpy(dtype=float)
        n = len(t)
        idx = rng.integers(0, n, size=(n_boot, n))
        for agg in AGGREGATORS:
            sc = scores(t, agg)
            share = sc / sc.sum() if sc.sum() > 0 else sc
            wins = np.zeros(4)
            for b in range(n_boot):
                wins[winner(scores(t[idx[b]], agg)) - 1] += 1
            wins /= n_boot
            srt = np.sort(share)[::-1]
            rows.append(
                {
                    "round": rnd,
                    "cond": cond,
                    "n": n,
                    "aggregator": agg,
                    **{f"share_{j + 1}": share[j] for j in range(4)},
                    "winner": winner(sc),
                    "tie": is_tie(sc),
                    "margin_top2": srt[0] - srt[1],
                    **{f"p_win_{j + 1}": wins[j] for j in range(4)},
                    "p_win_winner": wins[winner(sc) - 1],
                }
            )
    out = pd.DataFrame(rows)
    out["cond"] = pd.Categorical(out["cond"], CONDITIONS, ordered=True)
    return out.sort_values(["round", "cond", "aggregator"]).reset_index(drop=True)


def agreement(cells: pd.DataFrame) -> pd.DataFrame:
    """For each (round, cond): number of distinct winners across aggregators and the modal winner.
    Aggregators that end in an exact tie are left out of the count and reported in n_ties."""
    rows = []
    for (rnd, cond), d in cells.groupby(["round", "cond"], observed=True):
        n_ties = int(d["tie"].sum())
        w = d.loc[~d["tie"], "winner"].to_numpy()
        vals, counts = np.unique(w, return_counts=True)
        rows.append(
            {
                "round": rnd,
                "cond": cond,
                "distinct_winners": len(vals),
                "modal_winner": int(vals[counts.argmax()]),
                "aggregators_agreeing_with_modal": int(counts.max()),
                "n_aggregators": len(w),
                "n_ties": n_ties,
            }
        )
    return pd.DataFrame(rows)


def power_equalisation(votes: pd.DataFrame, n_boot: int = 2000, seed: int = SEED) -> pd.DataFrame:
    """Realised power of the high-budget group in the 20/80 cells, under linear and QV counting.

    High-budget = votes_given >= 100 inside an `early` cell (the article's 20/80 arm; budgets 400
    versus 25). Reported: head-count share, share of tokens, share of sqrt-votes (QV mass), and
    the closed-form predictions from theory.power_share at the realised head-count share.
    """
    from . import theory

    rng = np.random.default_rng(seed)
    rows = []
    for (rnd, cond), d in votes[votes["cond"].str.endswith("early")].groupby(["round", "cond"]):
        hi = (d["votes_given"] >= 100).to_numpy()
        t = d[CHOICES].to_numpy(dtype=float)

        def shares(ix):
            tt, hh = t[ix], hi[ix]
            lin = tt.sum(axis=1)
            qv = np.sqrt(tt).sum(axis=1)
            return hh.mean(), lin[hh].sum() / lin.sum(), qv[hh].sum() / qv.sum()

        f, s_lin, s_qv = shares(np.arange(len(d)))
        boots = np.array([shares(rng.integers(0, len(d), len(d))) for _ in range(n_boot)])
        lo, hi_ = np.nanpercentile(boots, [2.5, 97.5], axis=0)
        rows.append(
            {
                "round": rnd,
                "cond": cond,
                "n": len(d),
                "n_high": int(hi.sum()),
                "head_share": f,
                "token_share": s_lin,
                "token_share_lo": lo[1],
                "token_share_hi": hi_[1],
                "qv_share": s_qv,
                "qv_share_lo": lo[2],
                "qv_share_hi": hi_[2],
                "theory_linear_at_realised_f": theory.power_share(f, 16.0, 1.0),
                "theory_qv_at_realised_f": theory.power_share(f, 16.0, 0.5),
            }
        )
    return pd.DataFrame(rows)
