"""Tests for the extension modules. Toy-input checks need no data; the pipeline checks run on the
SYNTHETIC files from test_smoke.py (they say nothing about the article or the real ballots)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dao_replication import abm, behaviour, compositional as co, counterfactual as cf, silicon
from dao_replication.config import CHOICES, REPO_ROOT

from test_smoke import synth  # noqa: F401  (fixture)


# ---------------------------------------------------------------- compositional
def test_zero_replacement_keeps_composition_and_orders_values():
    c = np.array([[0, 10, 15, 0], [5, 5, 5, 5.0], [0, 0, 0, 25.0]])
    x = co.bm_replace(c, 1.0)
    assert np.allclose(x.sum(axis=1), 1.0)
    assert (x > 0).all()
    assert x[0, 0] < x[0, 1] < x[0, 2]
    assert np.allclose(x[1], 0.25)


def test_ilr_is_an_isometry_of_aitchison_distance():
    rng = np.random.default_rng(0)
    x = rng.dirichlet(np.ones(4), size=12)
    V = co.helmert_basis(4)
    assert np.allclose(V @ V.T, np.eye(3))
    z = co.ilr(x)
    d_ilr = np.sqrt(((z[:, None] - z[None]) ** 2).sum(-1))
    assert np.allclose(d_ilr, co.aitchison_dist(x))


def test_dirichlet_fit_recovers_precision():
    rng = np.random.default_rng(1)
    n = 600
    mu = np.array([0.1, 0.2, 0.3, 0.4])
    y = rng.dirichlet(8.0 * mu, size=n)
    ll, B, phi = co.dirichlet_fit(y, np.ones((n, 1)))
    assert phi == pytest.approx(8.0, rel=0.15)


# ---------------------------------------------------------------- counterfactual
def test_aggregator_scores_on_toy_ballots():
    t = np.array([[10, 0, 0, 0], [0, 4, 4, 0], [0, 0, 9, 0.0]])
    assert cf.scores(t, "tokens").tolist() == [10, 4, 13, 0]
    assert np.allclose(cf.scores(t, "qv_votes"), [np.sqrt(10), 2, 5, 0])
    assert np.allclose(cf.scores(t, "plurality"), [1, 0.5, 1.5, 0])
    assert cf.winner(cf.scores(t, "tokens")) == 3
    assert cf.winner(cf.scores(t, "borda")) == 3
    assert cf.scores(t, "copeland").sum() == pytest.approx(6.0)  # 6 ordered pairs, each decided or split


def test_exact_tie_is_flagged_not_counted_as_a_flip():
    t = np.array([[10, 0, 0, 0], [0, 10, 0, 0.0]])
    assert cf.is_tie(cf.scores(t, "tokens"))
    assert not cf.is_tie(np.array([3.0, 2.0, 1.0, 0.0]))


def test_concave_aggregator_flips_a_concentrated_minority():
    # 4 voters on option 1 (budget 100 each) vs 6 voters spreading 50/50 on options 2 and 3
    t = np.array([[100, 0, 0, 0]] * 4 + [[0, 50, 50, 0]] * 6, dtype=float)
    assert cf.winner(cf.scores(t, "tokens")) == 1  # 400 vs 300 each
    assert cf.winner(cf.scores(t, "qv_votes")) == 2  # 40 vs 42.4 each


# ---------------------------------------------------------------- behaviour / abm / silicon
def test_pipeline_on_synthetic_data(synth, monkeypatch):  # noqa: F811
    monkeypatch.setenv("DAO_DATA_DIR", str(synth))
    from dao_replication.data import load_votes

    votes = load_votes()
    cells = cf.cell_table(votes, n_boot=30)
    assert set(cells["aggregator"]) == set(cf.AGGREGATORS)
    assert cells["winner"].between(1, 4).all()
    assert len(cf.agreement(cells)) == 8
    pe = cf.power_equalisation(votes, n_boot=30)
    assert (pe["token_share"] >= pe["qv_share"] - 0.2).all()

    m = behaviour.ballot_measures(votes)
    assert m["hhi"].between(0.25, 1.0).all()
    inv = behaviour.invariance_table(votes, n_perm=50, n_boot=50)
    assert {"hhi", "qv_mass"} <= set(inv["measure"])
    gam = behaviour.relative_gamma(votes, n_boot=20)
    assert len(gam) == 3

    tests = co.run_tests(votes, s_grid=(1.0,), n_perm=30)
    assert tests["ilr_manova_p"].between(0, 1).all()
    assert tests["dirichlet_lr_p"].between(0, 1).all()
    assert len(co.power_groups(votes, n_perm=30)) == 3


def test_abm_responds_to_budget_ratio():
    mu_hi, mu_lo = np.array([0.1, 0.1, 0.1, 0.7]), np.array([0.1, 0.1, 0.7, 0.1])
    rng = np.random.default_rng(0)
    p1 = abm.p_high_wins(0.15, 1.0, 1.0, mu_hi, mu_lo, 6.0, n=60, n_sims=100, rng=rng, target=3)
    p16 = abm.p_high_wins(0.15, 16.0, 1.0, mu_hi, mu_lo, 6.0, n=60, n_sims=100, rng=rng, target=3)
    pq = abm.p_high_wins(0.15, 16.0, 0.5, mu_hi, mu_lo, 6.0, n=60, n_sims=100, rng=rng, target=3)
    assert p1 < 0.1 and p16 > 0.8 and pq < 0.5


def test_silicon_analysis_on_committed_pilot():
    df = pd.read_csv(REPO_ROOT / "data" / "silicon" / "pilot_ballots.csv")
    assert len(df) == 48 and (df[["t1", "t2", "t3", "t4"]].sum(axis=1) == 100).all()
    per, summ = silicon.analyse(df)
    assert set(summ["rule"]) == {"qv", "linear"}
    assert per["hhi"].between(0.25, 1.0).all()
    parsed = silicon.parse_reply('```json\n[{"voter": "V01", "tokens": [25, 25, 25, 25]}]\n```')
    assert parsed[0]["tokens"] == [25, 25, 25, 25]
