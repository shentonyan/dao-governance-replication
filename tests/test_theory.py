"""Check the closed forms in theory.py against brute-force computation."""

import numpy as np
import pytest

from dao_replication import theory as T


def test_power_share_endpoints_and_article_design():
    # 20 % of voters with budget 400, 80 % with budget 25: the high group holds
    # 0.2*400 / (0.2*400 + 0.8*25) = 0.8 of the tokens. Under QV its share is exactly one half.
    assert T.power_share(0.2, 16, 1.0) == pytest.approx(0.2 * 400 / (0.2 * 400 + 0.8 * 25))
    assert T.power_share(0.2, 16, 1.0) == pytest.approx(0.8)
    assert T.power_share(0.2, 16, 0.5) == pytest.approx(0.5)
    assert T.power_share(0.2, 16, 0.0) == pytest.approx(0.2)


def test_power_share_brute_force():
    n_high, n_low, b_high, b_low = 20, 80, 400.0, 25.0
    for alpha in (1.0, 0.5, 0.25):
        w = np.r_[np.full(n_high, b_high**alpha), np.full(n_low, b_low**alpha)]
        brute = w[:n_high].sum() / w.sum()
        assert brute == pytest.approx(T.power_share(0.2, b_high / b_low, alpha))


@pytest.mark.parametrize("k", [1, 2, 3, 5])
@pytest.mark.parametrize("alpha", [1.0, 0.5, 0.25])
def test_minority_threshold_brute_force(k, alpha):
    B = 100.0
    pi_star = T.minority_threshold(k, alpha)
    for pi, expect_win in ((pi_star - 1e-3, False), (pi_star + 1e-3, True)):
        a_votes = pi * T.effective_votes(np.array([B]), alpha)[0]
        other = (1 - pi) * T.effective_votes(np.array([B / k]), alpha)[0]  # each of the k other options
        assert (a_votes > other) == expect_win


def test_minority_threshold_known_values():
    assert T.minority_threshold(2, 1.0) == pytest.approx(1 / 3)
    assert T.minority_threshold(2, 0.5) == pytest.approx(1 / (1 + np.sqrt(2)))
    assert T.minority_threshold(3, 0.5) > T.minority_threshold(3, 1.0)  # QV is stricter here


def test_sybil_gain_brute_force():
    b = 90.0
    for k in (1, 2, 4, 9):
        for alpha in (1.0, 0.5):
            split = k * (b / k) ** alpha
            assert split / b**alpha == pytest.approx(T.sybil_gain_split(k, alpha))
            full = k * b**alpha
            assert full / b**alpha == pytest.approx(T.sybil_gain_new_budgets(k, alpha))
    assert T.sybil_gain_split(4, 0.5) == pytest.approx(2.0)
    assert T.sybil_gain_split(4, 1.0) == pytest.approx(1.0)


def test_vote_mass_range_under_qv():
    m = 4
    one = np.array([[1.0, 0, 0, 0]])
    even = np.full((1, m), 1.0 / m)
    assert T.vote_mass(one, 0.5)[0] == pytest.approx(1.0)
    assert T.vote_mass(even, 0.5)[0] == pytest.approx(np.sqrt(m))
    assert T.vote_mass(one, 1.0)[0] == pytest.approx(T.vote_mass(even, 1.0)[0])


def test_optimal_tokens_are_optimal():
    rng = np.random.default_rng(7)
    B = 50.0
    for _ in range(20):
        w = rng.uniform(0.1, 1.0, size=4)
        t = T.qv_optimal_tokens(w, B)
        assert t.sum() == pytest.approx(B)
        obj = lambda tok: float((w * np.sqrt(tok)).sum())  # noqa: E731
        best = obj(t)
        for _ in range(200):
            alt = rng.dirichlet(np.ones(4)) * B
            assert obj(alt) <= best + 1e-9
        tl = T.linear_optimal_tokens(w, B)
        assert tl.max() == pytest.approx(B)
