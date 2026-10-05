"""Figures for the extension analyses (theory.py, counterfactual.py, behaviour.py,
compositional.py, abm.py, silicon.py). Same visual conventions as figures.py."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import compositional as co  # noqa: E402
from . import theory as T  # noqa: E402
from .behaviour import ballot_measures  # noqa: E402
from .config import CHOICES, CONDITION_LABELS, CONDITIONS  # noqa: E402
from .counterfactual import AGGREGATORS, LABELS  # noqa: E402
from .figures import GRID, INK, INK2, SURFACE, _base, _fig  # noqa: E402

QV_C, LIN_C, EQ_C = "#2a78d6", "#1baf7a", "#52514e"
ORANGE, YELLOW = "#eb6834", "#eda100"
OPT = ["1 Current", "2 Extra info", "3 Track prefs", "4 Flags/tags"]


def _save(fig, path: Path):
    fig.savefig(path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def _leg(ax, **kw):
    kw.setdefault("fontsize", 8.5)
    return ax.legend(frameon=False, labelcolor=INK2, **kw)


# ------------------------------------------------------------------ 1. power compression
def fig_power_compression(pe: pd.DataFrame, path: Path) -> pd.DataFrame:
    fig, (a, b) = _fig(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1, 1.1]})
    for ax in (a, b):
        _base(ax)
    alphas = np.linspace(0, 1, 101)
    rows = []
    for f, c, ls, lab in [
        (0.20, INK2, ":", "design: 20 % high-budget"),
        (0.28, ORANGE, "-", "realised, ranked 20/80 round 1 (28 %)"),
        (0.375, QV_C, "-", "realised, quadratic 20/80 round 1 (37.5 %)"),
    ]:
        y = [T.power_share(f, 16.0, al) for al in alphas]
        a.plot(alphas, y, color=c, ls=ls, lw=2, label=lab)
        for al in (0.5, 1.0):
            a.plot([al], [T.power_share(f, 16.0, al)], "o", color=c, ms=7, mec=SURFACE, mew=1.2)
            rows.append({"f": f, "alpha": al, "high_group_share": T.power_share(f, 16.0, al)})
    a.set_xlabel("exponent alpha in votes = tokens^alpha\n(0 = head count, 1/2 = quadratic, 1 = linear)", color=INK2, fontsize=9)
    a.set_ylabel("share of effective votes held by the\nhigh-budget group (budget ratio 16:1)", color=INK2, fontsize=9)
    a.set_ylim(0, 1)
    a.set_title("Closed form: f·r^α / (f·r^α + 1 − f)", fontsize=10, color=INK, loc="left")
    _leg(a, loc="lower right")

    x = np.arange(len(pe))
    lab = [f"R{r}\n{CONDITION_LABELS[c].split(',')[0]}" for r, c in zip(pe["round"], pe["cond"])]
    b.errorbar(x - 0.12, pe["token_share"], yerr=[pe["token_share"] - pe["token_share_lo"], pe["token_share_hi"] - pe["token_share"]],
               fmt="^", color=LIN_C, ms=7, capsize=3, label="measured, tokens (linear)")
    b.errorbar(x + 0.12, pe["qv_share"], yerr=[pe["qv_share"] - pe["qv_share_lo"], pe["qv_share_hi"] - pe["qv_share"]],
               fmt="o", color=QV_C, ms=7, capsize=3, label="measured, sqrt(tokens) (QV)")
    b.plot(x - 0.12, pe["theory_linear_at_realised_f"], "x", color=INK, ms=8, mew=1.6, label="closed form at realised head share")
    b.plot(x + 0.12, pe["theory_qv_at_realised_f"], "x", color=INK, ms=8, mew=1.6)
    b.plot(x, pe["head_share"], "_", color=INK2, ms=18, mew=2, label="head share (one voter, one vote)")
    b.set_xticks(x, lab, fontsize=8.5)
    b.set_ylim(0, 1.02)
    b.set_title("Measured on the released 20/80 ballots (95 % bootstrap)", fontsize=10, color=INK, loc="left")
    _leg(b, loc="lower left", ncol=1)
    fig.tight_layout()
    _save(fig, path)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 2. minority threshold + vote mass
def fig_minority_mass(votes: pd.DataFrame, path: Path) -> pd.DataFrame:
    fig, (a, b) = _fig(1, 2, figsize=(11.5, 4.5))
    for ax in (a, b):
        _base(ax)
    ks = np.arange(1, 7)
    rows = []
    for al, c, ls, mk, lab in [(1.0, LIN_C, "--", "^", "linear (tokens)"), (0.5, QV_C, "-", "o", "quadratic (sqrt tokens)"),
                               (0.05, EQ_C, ":", "s", "approval-like (alpha = 0.05)")]:
        y = [T.minority_threshold(k, al) for k in ks]
        a.plot(ks, y, color=c, ls=ls, marker=mk, lw=2, ms=6, mec=SURFACE, mew=1, label=lab)
        rows += [{"k": k, "alpha": al, "threshold": v} for k, v in zip(ks, y)]
    a.set_xlabel("k = number of options the majority spreads its tokens over", color=INK2, fontsize=9)
    a.set_ylabel("population share a concentrated minority\nneeds in order to win", color=INK2, fontsize=9)
    a.set_title("Concentration is penalised by a concave rule", fontsize=10, color=INK, loc="left")
    a.set_ylim(0, 0.6)
    _leg(a, loc="lower right")

    m = ballot_measures(votes)
    for q, c, mk, lab in [(1, QV_C, "o", "quadratic arm"), (0, LIN_C, "^", "ranked arm")]:
        d = m[m["quadratic"] == q]
        rng = np.random.default_rng(3)
        b.scatter(d["hhi"] + rng.normal(0, 0.004, len(d)), d["qv_mass"] + rng.normal(0, 0.004, len(d)), s=26, color=c, marker=mk,
                  alpha=0.65, edgecolor=SURFACE, linewidth=0.5, label=f"{lab} (n = {len(d)})")
    xs = np.linspace(0.25, 1, 50)
    b.plot([0.25, 1.0], [2.0, 1.0], color=INK2, ls=":", lw=1)
    b.annotate("even over 4 options:\nQV mass 2.0 per sqrt-budget", (0.25, 2.0), xytext=(0.5, 1.9), fontsize=8, color=INK2)
    b.annotate("all on one option: 1.0", (1.0, 1.0), xytext=(0.72, 1.1), fontsize=8, color=INK2)
    b.set_xlabel("ballot concentration (Herfindahl index of allocation shares)", color=INK2, fontsize=9)
    b.set_ylabel("effective votes cast under QV, sum_j sqrt(share_j)", color=INK2, fontsize=9)
    b.set_title("A spread ballot carries up to twice the QV vote mass", fontsize=10, color=INK, loc="left")
    _leg(b, loc="upper right")
    fig.tight_layout()
    _save(fig, path)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 3. Sybil
def fig_sybil(path: Path) -> pd.DataFrame:
    fig, (a, b) = _fig(1, 2, figsize=(11.5, 4.5))
    for ax in (a, b):
        _base(ax)
    ks = np.arange(1, 65)
    a.plot(ks, [T.sybil_gain_new_budgets(k, 0.5) for k in ks], color=ORANGE, lw=2, label="each identity gets its own budget (any rule)")
    a.plot(ks, [T.sybil_gain_split(k, 0.5) for k in ks], color=QV_C, lw=2, label="one balance split over k wallets, QV: sqrt(k)")
    a.plot(ks, [T.sybil_gain_split(k, 1.0) for k in ks], color=LIN_C, lw=2, ls="--", label="one balance split over k wallets, linear: 1")
    a.set_xscale("log")
    a.set_yscale("log")
    a.set_xlabel("k = number of identities / wallets", color=INK2, fontsize=9)
    a.set_ylabel("multiplier on the attacker's effective votes", color=INK2, fontsize=9)
    a.set_title("QV needs one-person-one-budget to work", fontsize=10, color=INK, loc="left")
    _leg(a, loc="upper left")
    fr = np.linspace(0.0, 0.4, 81)
    rows = []
    for k, c, ls in [(4, "#1d4f8c", "-"), (16, QV_C, "-"), (1, INK2, ":")]:
        y = [T.attacker_share_split(x, k, 0.5) for x in fr]
        b.plot(fr, y, color=c, ls=ls, lw=2, label=(f"QV, wallets per attacker k = {k}" if k > 1 else "QV, k = 1 (= linear)"))
        rows += [{"attacker_fraction": x, "k": k, "rule": "qv", "attacker_share": v} for x, v in zip(fr, y)]
    b.plot(fr, fr, color=LIN_C, ls="--", lw=2, label="linear, any k (splitting changes nothing)")
    b.plot(fr, [T.attacker_share_split(x, 3, 0.0) for x in fr], color=ORANGE, lw=1.5, ls="-.", label="own budget per identity, k = 3 (any rule)")
    b.set_xlabel("fraction of honest-looking voters who are the attacker", color=INK2, fontsize=9)
    b.set_ylabel("attacker's share of effective votes", color=INK2, fontsize=9)
    b.set_title("Token splitting under a token-weighted DAO", fontsize=10, color=INK, loc="left")
    _leg(b, loc="upper left")
    fig.tight_layout()
    _save(fig, path)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 4. winner robustness
def fig_winner_robustness(cells: pd.DataFrame, path: Path):
    keys = [(r, c) for r in (1, 2) for c in CONDITIONS]
    fig, ax = _fig(1, 1, figsize=(11.5, 5.2))
    ax.set_facecolor(SURFACE)
    P = np.zeros((len(keys), len(AGGREGATORS)))
    W = np.zeros_like(P, dtype=int)
    TIE = np.zeros_like(P, dtype=bool)
    for i, (r, c) in enumerate(keys):
        for j, ag in enumerate(AGGREGATORS):
            row = cells[(cells["round"] == r) & (cells["cond"] == c) & (cells["aggregator"] == ag)].iloc[0]
            P[i, j], W[i, j], TIE[i, j] = row["p_win_winner"], row["winner"], row["tie"]
    im = ax.imshow(P, cmap="Blues", vmin=0.3, vmax=1.0, aspect="auto")
    for i in range(len(keys)):
        modal = np.bincount(W[i][~TIE[i]]).argmax()
        for j in range(len(AGGREGATORS)):
            if TIE[i, j]:
                ax.text(j, i, "exact\ntie", ha="center", va="center", fontsize=9, style="italic", color=INK2)
                continue
            flip = W[i, j] != modal
            ax.text(j, i, f"{W[i, j]}", ha="center", va="center", fontsize=13, fontweight="bold" if flip else "normal",
                    color="#b3261e" if flip else INK)
            if flip:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="#b3261e", lw=2))
    ax.set_xticks(range(len(AGGREGATORS)), [LABELS[a].replace(" (", "\n(") for a in AGGREGATORS], fontsize=8)
    ax.set_yticks(range(len(keys)), [f"Round {r}, {CONDITION_LABELS[c]}" for r, c in keys], fontsize=9)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("bootstrap probability that this winner wins", fontsize=9, color=INK2)
    ax.set_title("Winning option (number) under seven aggregation rules applied to the same ballots; red = differs from the modal winner; italic = exact tie",
                 fontsize=10, color=INK, loc="left")
    fig.tight_layout()
    _save(fig, path)


# ------------------------------------------------------------------ 5. behavioural invariance
def fig_invariance(votes: pd.DataFrame, gam: pd.DataFrame, path: Path):
    fig, (a, b) = _fig(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1.2, 1]})
    for ax in (a, b):
        _base(ax)
    m = ballot_measures(votes)
    rng = np.random.default_rng(5)
    pos = {(1, 1): 0.8, (1, 0): 1.2, (2, 1): 2.8, (2, 0): 3.2}
    for (rnd, q), x0 in pos.items():
        d = m[(m["round"] == rnd) & (m["quadratic"] == q)]["hhi"].to_numpy()
        c, mk = (QV_C, "o") if q else (LIN_C, "^")
        a.scatter(x0 + rng.uniform(-0.12, 0.12, len(d)), d, s=16, color=c, marker=mk, alpha=0.5, linewidth=0)
        a.plot([x0 - 0.17, x0 + 0.17], [d.mean()] * 2, color=INK, lw=2.5)
    a.axhline(0.25, color=GRID, lw=1)
    a.set_xticks([1, 3], ["Round 1", "Round 2"])
    a.set_ylabel("ballot concentration (Herfindahl index)", color=INK2, fontsize=9)
    a.scatter([], [], color=QV_C, marker="o", label="quadratic")
    a.scatter([], [], color=LIN_C, marker="^", label="ranked")
    a.plot([], [], color=INK, lw=2.5, label="mean")
    a.set_title("Ballots are equally concentrated under both rules", fontsize=10, color=INK, loc="left")
    _leg(a, loc="upper right")
    y = np.arange(len(gam))[::-1]
    b.errorbar(gam["gamma_hat"], y, xerr=[gam["gamma_hat"] - gam["ci_lo"], gam["ci_hi"] - gam["gamma_hat"]], fmt="o", color=QV_C, capsize=4, ms=8)
    b.axvline(1.0, color=LIN_C, ls="--", lw=1.8)
    b.axvline(2.0, color=ORANGE, ls="-", lw=1.8)
    b.text(1.02, len(gam) - 0.35, "1: same concentration", color=LIN_C, fontsize=8.5)
    b.text(2.02, len(gam) - 0.35, "2: vote-maximising\nQV vs expressive", color=ORANGE, fontsize=8.5, va="top")
    b.set_yticks(y, gam["subset"])
    b.set_xlim(0.2, 3.0)
    b.set_ylim(-0.6, len(gam) - 0.2)
    b.set_xlabel("relative concentration exponent gamma (95 % bootstrap)", color=INK2, fontsize=9)
    b.set_title("Quadratic ballots relative to ranked ballots", fontsize=10, color=INK, loc="left")
    fig.tight_layout()
    _save(fig, path)


# ------------------------------------------------------------------ 6. clr biplot
def fig_clr_biplot(votes: pd.DataFrame, path: Path, s: float = 1.0):
    d = co.prepare(votes, s)
    x = d[["x1", "x2", "x3", "x4"]].to_numpy()
    z = co.clr(x)
    zc = z - z.mean(axis=0)
    U, S, Vt = np.linalg.svd(zc, full_matrices=False)
    scores = U[:, :2] * S[:2]
    load = Vt[:2].T
    var = S**2 / (S**2).sum()
    d["pc1"], d["pc2"] = scores[:, 0], scores[:, 1]
    sc = 0.42 * np.abs(scores).max() / max(np.abs(load).max(), 1e-9)
    fig, axes = _fig(1, 3, figsize=(14, 4.6), sharex=True, sharey=True)
    panels = [
        ("Round 1: by voting method", d[d["round"] == 1], "quadratic"),
        ("Round 1, 20/80 arms: by budget", d[(d["round"] == 1) & d["cond"].str.endswith("early")], "high"),
        ("Round 2, 20/80 arms: by budget", d[(d["round"] == 2) & d["cond"].str.endswith("early")], "high"),
    ]
    for ax, (title, dd, key) in zip(axes, panels):
        _base(ax)
        dd = dd.copy()
        if key == "high":
            dd["high"] = (dd["votes_given"] >= 100).astype(int)
            groups = [(1, ORANGE, "s", "400 tokens"), (0, "#7a7975", "o", "25 tokens")]
        else:
            groups = [(1, QV_C, "o", "quadratic"), (0, LIN_C, "^", "ranked")]
        for val, c, mk, lab in groups:
            g = dd[dd[key] == val]
            ax.scatter(g["pc1"], g["pc2"], s=34, color=c, marker=mk, alpha=0.7, edgecolor=SURFACE, linewidth=0.6, label=f"{lab} (n = {len(g)})")
            ax.scatter([g["pc1"].mean()], [g["pc2"].mean()], s=170, color=c, marker=mk, edgecolor=INK, linewidth=1.8, zorder=5)
        for j in range(4):
            ax.annotate("", xy=(load[j, 0] * sc, load[j, 1] * sc), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=INK2, lw=1.1))
            ax.text(load[j, 0] * sc * 1.12, load[j, 1] * sc * 1.12, OPT[j], fontsize=8, color=INK2, ha="center")
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_xlabel(f"clr PC1 ({var[0]:.0%} of variance)", color=INK2, fontsize=9)
        _leg(ax, loc="lower right")
    axes[0].set_ylabel(f"clr PC2 ({var[1]:.0%})", color=INK2, fontsize=9)
    fig.tight_layout()
    _save(fig, path)


# ------------------------------------------------------------------ 7. p-value robustness
def fig_pvalue_robustness(tests: pd.DataFrame, ref: pd.DataFrame, path: Path):
    fig, axes = _fig(1, 2, figsize=(11.5, 4.2), sharex=True)
    meth = [("ilr_manova_p", "MANOVA on ilr coordinates"), ("permanova_p", "PERMANOVA, Aitchison distance"), ("dirichlet_lr_p", "Dirichlet regression, LR test")]
    cols = {0.25: "#7ab0ec", 1.0: QV_C, 4.0: "#1d4f8c"}
    for ax, rnd in zip(axes, (1, 2)):
        _base(ax)
        ax.grid(axis="x", color=GRID)
        ax.grid(axis="y", visible=False)
        d = tests[(tests["round"] == rnd) & tests["term"].str.startswith("voting method")]
        for i, (col, lab) in enumerate(meth):
            for s, c in cols.items():
                v = d[d["zero_prior_s"] == s][col].iloc[0]
                ax.plot(v, len(meth) - i, "o", color=c, ms=9, mec=SURFACE, mew=1.2, label=f"zero prior s = {s}" if i == 0 else None)
        for k, (_, rr) in enumerate(ref[ref["round"] == rnd].iterrows()):
            ax.plot(rr["p"], k + 0.35 - 0.0, "D", color=ORANGE, ms=8, mec=SURFACE, label=rr["label"] if rnd == 1 else None)
        ax.axvline(0.05, color=INK2, ls="--", lw=1)
        ax.set_xscale("log")
        ax.set_xlim(0.01, 1.0)
        ax.set_yticks([len(meth) - i for i in range(len(meth))] + [0.35], [m[1] for m in meth] + ["article's Table 2 / raw ratios"], fontsize=8.5)
        ax.set_xlabel("p-value for the voting-method effect (log scale; dashed = 0.05)", color=INK2, fontsize=9)
        ax.set_title(f"Round {rnd}", fontsize=10, color=INK, loc="left")
    _leg(axes[0], loc="upper right", fontsize=7.5)
    fig.tight_layout()
    _save(fig, path)


# ------------------------------------------------------------------ 8. ABM phase diagram
def fig_phase(grids: dict, fs: np.ndarray, ratios: np.ndarray, opts: tuple[int, int], path: Path):
    fig, axes = _fig(1, 3, figsize=(14, 4.4), sharey=True)
    names = {"tokens": "Tokens (linear)", "qv": "sqrt(tokens) (QV)", "equal": "One voter, one unit of influence"}
    for ax, k in zip(axes, ("tokens", "qv", "equal")):
        im = ax.imshow(grids[k], origin="lower", aspect="auto", cmap="Oranges", vmin=0, vmax=1,
                       extent=[fs[0] - (fs[1] - fs[0]) / 2, fs[-1] + (fs[1] - fs[0]) / 2, -0.5, len(ratios) - 0.5])
        cs = ax.contour(fs, np.arange(len(ratios)), grids[k], levels=[0.5], colors=[INK], linewidths=1.6)
        ax.plot([0.28], [list(ratios).index(16.0)], "*", color=QV_C, ms=15, mec=SURFACE, mew=1, label="article-like design (f ≈ 0.28, r = 16)")
        ax.set_yticks(range(len(ratios)), [f"{int(r)}:1" for r in ratios])
        ax.set_xlabel("fraction of voters with the high budget", color=INK2, fontsize=9)
        ax.set_title(names[k], fontsize=10, color=INK, loc="left")
        for s_ in ax.spines.values():
            s_.set_visible(False)
    axes[0].set_ylabel("budget ratio, high : low", color=INK2, fontsize=9)
    axes[2].text(0.5, 0.78, "≈ 0 everywhere: with one unit per voter\nthe majority's option 3 wins", transform=axes[2].transAxes, ha="center", fontsize=8.5, color=INK2)
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.55, -0.16), frameon=False, fontsize=8.5, labelcolor=INK2)
    cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cb.set_label(f"P(option {opts[0]}, the high-budget group's modal choice, wins)", fontsize=9, color=INK2)
    _save(fig, path)


# ------------------------------------------------------------------ 9. silicon pilot
def fig_silicon(df: pd.DataFrame, per: pd.DataFrame, path: Path):
    fig, (a, b) = _fig(1, 2, figsize=(11.5, 4.5), gridspec_kw={"width_ratios": [1, 1.1]})
    for ax in (a, b):
        _base(ax)
    w = df[["w1", "w2", "w3", "w4"]].to_numpy(float)
    t = df[["t1", "t2", "t3", "t4"]].to_numpy(float)
    ws, ts = w / w.sum(1, keepdims=True), t / t.sum(1, keepdims=True)
    for rule, c, mk, lab in [("linear", LIN_C, "^", "linear rule"), ("qv", QV_C, "o", "quadratic rule")]:
        mask = (df["rule"] == rule).to_numpy()
        a.scatter(ws[mask].ravel(), ts[mask].ravel(), s=22, color=c, marker=mk, alpha=0.55, linewidth=0, label=lab)
    odd = ((df["rule"] == "qv") & (df["session"] == "A4")).to_numpy()
    a.scatter(ws[odd].ravel(), ts[odd].ravel(), s=70, facecolors="none", edgecolors=ORANGE, linewidths=1.5, label="the one session that concentrated (QV, A4)")
    a.plot([0, 0.7], [0, 0.7], color=INK2, ls=":", lw=1.2)
    a.text(0.5, 0.43, "tokens ∝ value", fontsize=8.5, color=INK2, rotation=33)
    a.set_xlabel("voter's value for the option, as a share of the voter's total value", color=INK2, fontsize=9)
    a.set_ylabel("share of the 100 tokens placed on the option", color=INK2, fontsize=9)
    a.set_title("Induced-value LLM voters, 24 per rule (paired values)", fontsize=10, color=INK, loc="left")
    _leg(a, loc="upper left", fontsize=8)
    ses = per.copy()
    ses["session"] = df["session"].values
    g = ses.groupby(["rule", "session"])["hhi"].mean().reset_index()
    bench = ses[["hhi_expressive", "hhi_qv_rational", "hhi_linear_rational"]].mean()
    xs = np.arange(len(g))
    cols = [QV_C if r == "qv" else LIN_C for r in g["rule"]]
    b.bar(xs, g["hhi"], color=cols, width=0.62)
    b.set_xticks(xs, [f"{'QV' if r == 'qv' else 'linear'}\nsession {s}" for r, s in zip(g["rule"], g["session"])], fontsize=8)
    for y, lab, c, ls in [(bench["hhi_expressive"], "tokens ∝ value", INK2, ":"), (bench["hhi_qv_rational"], "QV-rational (tokens ∝ value²)", ORANGE, "-"),
                          (bench["hhi_linear_rational"], "linear-rational (all on top option)", "#b3261e", "--")]:
        b.axhline(y, color=c, ls=ls, lw=1.6)
        b.text(len(g) - 0.5, y + 0.012, lab, color=c, fontsize=8, ha="right")
    b.set_ylim(0, 1.08)
    b.set_ylabel("mean ballot concentration (Herfindahl index)", color=INK2, fontsize=9)
    b.set_title("Concentration by agent session vs. benchmarks", fontsize=10, color=INK, loc="left")
    fig.tight_layout()
    _save(fig, path)
