"""Run the extension analyses (theory checks, counterfactual rules, behaviour, compositional data,
Monte-Carlo phase diagram, LLM-voter pilot) and write tables and figures.

    python scripts/run_extensions.py            # needs the OSF CSVs (see data/README.md)
    python scripts/run_extensions.py --quick    # fewer permutations / bootstrap draws

Outputs: results/extensions/tables/*.csv and results/figures/ext_*.png
The LLM-voter pilot reads data/silicon/pilot_ballots.csv (committed); it does not call any model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dao_replication import abm, behaviour, compositional, counterfactual, extensions, silicon  # noqa: E402
from dao_replication.config import REPO_ROOT, results_dir  # noqa: E402
from dao_replication.data import load_votes  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    nb = 500 if args.quick else 2000
    npm = 1000 if args.quick else 5000

    out = results_dir()
    tab = out / "extensions" / "tables"
    tab.mkdir(parents=True, exist_ok=True)
    fig = out / "figures"
    fig.mkdir(exist_ok=True)

    votes = load_votes()

    # 1-3: closed forms vs the released ballots
    pe = counterfactual.power_equalisation(votes, n_boot=nb)
    pe.to_csv(tab / "power_equalisation.csv", index=False)
    extensions.fig_power_compression(pe, fig / "ext_power_compression.png").to_csv(tab / "power_share_closed_form.csv", index=False)
    extensions.fig_minority_mass(votes, fig / "ext_minority_threshold_and_mass.png").to_csv(tab / "minority_threshold_closed_form.csv", index=False)
    extensions.fig_sybil(fig / "ext_sybil.png").to_csv(tab / "sybil_closed_form.csv", index=False)

    # 4: same ballots, different rules
    cells = counterfactual.cell_table(votes, n_boot=nb)
    cells.to_csv(tab / "counterfactual_rules.csv", index=False)
    counterfactual.agreement(cells).to_csv(tab / "counterfactual_agreement.csv", index=False)
    extensions.fig_winner_robustness(cells, fig / "ext_winner_robustness.png")

    # 5: behavioural invariance
    behaviour.ballot_measures(votes).to_csv(tab / "ballot_measures.csv", index=False)
    inv = behaviour.invariance_table(votes, n_perm=npm * 2, n_boot=nb * 2)
    inv.to_csv(tab / "behaviour_invariance.csv", index=False)
    gam = behaviour.relative_gamma(votes, n_boot=nb)
    gam.to_csv(tab / "behaviour_relative_gamma.csv", index=False)
    extensions.fig_invariance(votes, gam, fig / "ext_behavioural_invariance.png")

    # 6-7: compositional data
    tests = compositional.run_tests(votes, n_perm=npm)
    tests.to_csv(tab / "compositional_tests.csv", index=False)
    grp = compositional.power_groups(votes, n_perm=npm * 2)
    grp.to_csv(tab / "compositional_budget_groups.csv", index=False)
    extensions.fig_clr_biplot(votes, fig / "ext_clr_biplot.png")
    perm = pd.read_csv(out / "tables" / "sensitivity_permutation.csv") if (out / "tables" / "sensitivity_permutation.csv").exists() else None
    t2 = pd.read_csv(out / "tables" / "table2_manova_additive.csv") if (out / "tables" / "table2_manova_additive.csv").exists() else None
    ref_rows = []
    if t2 is not None:
        for _, r in t2.iterrows():
            term = str(r.get("term", r.get("factor", ""))).lower()
            if "quadratic" in term or "method" in term:
                rnd = int(r["round"])
                p = float(r[[c for c in t2.columns if c.lower() in ("p", "p_value", "pr > f", "pr_f")][0]])
                ref_rows.append({"round": rnd, "label": "article Table 2 (raw ratios)", "p": p})
    extensions.fig_pvalue_robustness(tests, pd.DataFrame(ref_rows, columns=["round", "label", "p"]), fig / "ext_robustness_pvalues.png")

    # 8: Monte-Carlo phase diagram
    cal = abm.calibrate(votes, rnd=1)
    fs = np.linspace(0.05, 0.50, 10)
    ratios = np.array([1, 2, 4, 8, 16, 32.0])
    grids, opts = abm.phase_grid(cal, fs, ratios, n=100, n_sims=150 if args.quick else 400)
    rows = []
    for name, g in grids.items():
        for i, r in enumerate(ratios):
            for j, f in enumerate(fs):
                rows.append({"aggregator": name, "ratio": r, "f_high": f, "p_high_modal_wins": g[i, j]})
    pd.DataFrame(rows).to_csv(tab / "phase_diagram.csv", index=False)
    pd.DataFrame([{"mu_high_%d" % (k + 1): v for k, v in enumerate(cal["mu_high"])} | {"mu_low_%d" % (k + 1): v for k, v in enumerate(cal["mu_low"])}
                  | {"kappa": cal["kappa"], "n_high": cal["n_high"], "n_low": cal["n_low"]}]).to_csv(tab / "phase_calibration.csv", index=False)
    extensions.fig_phase(grids, fs, ratios, opts, fig / "ext_phase_diagram.png")

    # 9: LLM-voter pilot (committed ballots; no model calls)
    p = REPO_ROOT / "data" / "silicon" / "pilot_ballots.csv"
    if p.exists():
        df = pd.read_csv(p)
        per, summ = silicon.analyse(df)
        per.to_csv(tab / "silicon_per_voter.csv", index=False)
        summ.to_csv(tab / "silicon_summary.csv", index=False)
        extensions.fig_silicon(df, per, fig / "ext_silicon_pilot.png")
    print("extensions written to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
