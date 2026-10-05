"""Exploratory: induced-value LLM voters under the two aggregation rules.

Purpose. The released data show that human ballots are about equally concentrated under the
quadratic and the ranked rule (behaviour.py). Does an LLM agent that is *told* its private values
and the rule behave the same way, or does it adapt its allocation to the quadratic cost? This
matters for anyone considering LLM agents as stand-ins for participants in token-voting
experiments.

Design. Each simulated voter receives private values w_j in 0..10 for the four options
(induced values, as in experimental economics: the benchmark behaviour is computable) and 100
tokens. The same value vectors are used under both rules, so the comparison is paired. No
identity or demographic attributes are simulated. Agents are not asked to explain themselves.

Benchmarks for a voter with values w (see theory.py):
  expressive      tokens proportional to w
  QV-rational     tokens proportional to w^2   (equal pivot probabilities)
  linear-rational everything on the highest-valued option

Caveats that belong with any result: a small number of voters (24 per rule); several voters are
answered inside one agent session, so they are not independent draws; the agents see the rule
text I wrote, not the article's interface; this tests LLM behaviour, not human behaviour.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

OPTIONS = [
    "Keep using the current model as it is",
    "Use additional information about the user",
    "Track and apply each user's preferences",
    "Add specific flags or tags to requests",
]

RULE_TEXT = {
    "qv": (
        "Voting rule: the votes an option receives from you equal the square root of the tokens you place on it "
        "(for example, 4 tokens give 2 votes and 16 tokens give 4 votes). All voters' votes are added up and the "
        "option with the most votes wins."
    ),
    "linear": (
        "Voting rule: the votes an option receives from you equal the tokens you place on it. All voters' votes "
        "are added up and the option with the most votes wins."
    ),
}


def make_valuations(n: int = 24, seed: int = 20261005) -> np.ndarray:
    """n x 4 integer values in 0..10, rescaled so every voter's largest value is 10."""
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(4), size=n)
    w = np.rint(10 * w / w.max(axis=1, keepdims=True)).astype(int)
    return w


def build_prompt(rule: str, voters: list[tuple[str, np.ndarray]], budget: int = 100) -> str:
    opts = "\n".join(f"  {i + 1}. {t}" for i, t in enumerate(OPTIONS))
    blocks = "\n".join(f"  {vid}: option 1 = {w[0]}, option 2 = {w[1]}, option 3 = {w[2]}, option 4 = {w[3]}" for vid, w in voters)
    return f"""You are taking part in a decision about how a text-to-image model should handle gender bias in the images it produces. The four options are:
{opts}

There are about 100 voters. Each voter holds {budget} tokens and places them on the four options. Tokens are whole numbers, any option may receive zero, and you must place all {budget} tokens.

{RULE_TEXT[rule]}

Below are several separate voters. Each has private values from 0 to 10 for the four options (higher means that voter wants that option to win more). Treat every voter as a different person who knows nothing about the others, and decide each voter's token placement independently, as that voter would.

{blocks}

Reply with only a JSON list, one object per voter, in this form and nothing else:
[{{"voter": "<id>", "tokens": [t1, t2, t3, t4]}}, ...]"""


def parse_reply(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, flags=re.S)
    if not m:
        raise ValueError("no JSON list found")
    return json.loads(m.group(0))


def _shares(t: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    return t / t.sum(axis=-1, keepdims=True)


def analyse(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """df columns: voter, rule ('qv'|'linear'), w1..w4, t1..t4.

    Returns (per-voter table, per-rule summary). Per voter: HHI of the allocation, the HHI of
    each benchmark, a log-log slope of share on value over options with positive tokens and
    positive value, and the share of the budget on the highest-valued option(s).
    """
    from . import theory

    rows = []
    for _, r in df.iterrows():
        w = r[["w1", "w2", "w3", "w4"]].to_numpy(dtype=float)
        t = r[["t1", "t2", "t3", "t4"]].to_numpy(dtype=float)
        s = _shares(t)
        exp = _shares(w)
        qv = theory.qv_optimal_tokens(w, 1.0)
        lin = theory.linear_optimal_tokens(w, 1.0)
        pos = (t > 0) & (w > 0)
        slope = np.nan
        if pos.sum() >= 3:
            slope = float(np.polyfit(np.log(w[pos]), np.log(s[pos]), 1)[0])
        top = np.isclose(w, w.max())
        rows.append(
            {
                "voter": r["voter"],
                "rule": r["rule"],
                "budget_ok": bool(abs(t.sum() - 100) < 1e-9),
                "hhi": float((s**2).sum()),
                "hhi_expressive": float((exp**2).sum()),
                "hhi_qv_rational": float((qv**2).sum()),
                "hhi_linear_rational": float((lin**2).sum()),
                "loglog_slope": slope,
                "share_on_top_valued": float(s[top].sum()),
                "n_nonzero": int((t > 0).sum()),
            }
        )
    per = pd.DataFrame(rows)
    summ = (
        per.groupby("rule")
        .agg(
            n=("voter", "size"),
            mean_hhi=("hhi", "mean"),
            mean_hhi_expressive=("hhi_expressive", "mean"),
            mean_hhi_qv_rational=("hhi_qv_rational", "mean"),
            mean_hhi_linear_rational=("hhi_linear_rational", "mean"),
            median_slope=("loglog_slope", "median"),
            mean_top_share=("share_on_top_valued", "mean"),
            mean_nonzero=("n_nonzero", "mean"),
            all_budgets_ok=("budget_ok", "all"),
        )
        .reset_index()
    )
    return per, summ
