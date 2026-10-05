# Extensions: what the released ballots say beyond the article's tables

**English** | [简体中文](EXTENSIONS.zh-CN.md)

Everything here is exploratory analysis of the released OSF data, added after the reproduction in
[REPRODUCIBILITY.md](REPRODUCIBILITY.md). It is not part of the article's claims and not a re-test of them.
Cells are small (18 to 27 voters per round and condition; 177 voters in total), nothing below is corrected for
the number of analyses run, and every result depends on assumptions stated next to it.
Closed forms are derived in [THEORY.md](THEORY.md). Code: `scripts/run_extensions.py`
(`python scripts\run_extensions.py`, about 75 s; `--quick` for a faster pass). Tables are in `results/extensions/tables/`.

| # | Question | Short answer |
|---|---|---|
| 1 | How much weight does the high-budget group get under each rule? | 81 to 91 % of tokens, 56 to 71 % of sqrt-votes; matches the closed form |
| 2 | Do winners depend on the aggregation rule, using the same ballots? | Not in the equal-power cells; yes in two of the four 20/80 cells |
| 3 | Do people spend tokens differently under the quadratic rule? | No detectable difference in how concentrated ballots are |
| 4 | Does QV favour a concentrated minority in this design? | In theory the opposite, unless budgets can move across issues |
| 5 | Is the round-1 method effect robust to a compositional treatment? | Depends on the test; round 2 is null throughout |
| 6 | Do high-budget voters allocate differently from low-budget voters? | Strongly in round 1, not in round 2 (assignment not random as far as I can tell) |
| 7 | What would other designs do? | Monte-Carlo phase diagram, calibrated on round 1 |
| 8 | Do LLM voters adapt to the rule? | Mostly not (small pilot, 8 sessions) |

## 1. Power compression: closed form and data

The article's 20/80 arms give a high-budget group (400 tokens) much more weight than the rest (25 tokens).
In the released files that group is 16 of 49 voters in round 1 and 11 of 37 in round 2 (22 to 37.5 % per cell),
not the nominal 20 %. I could not confirm from the article text I could read how group membership was set
(the excerpt I could access says only that 20 % of participants get 80 % of tokens).

![Power compression](../results/figures/ext_power_compression.png)

| Cell | High-budget share of voters | Share of tokens (95 % CI) | Share of sqrt-votes (95 % CI) | Closed form, sqrt-votes |
|---|---:|---:|---:|---:|
| Round 1, quadratic 20/80 | 0.375 | 0.912 (0.786 to 0.961) | 0.692 (0.444 to 0.843) | 0.706 |
| Round 1, ranked 20/80 | 0.280 | 0.874 (0.703 to 0.939) | 0.610 (0.342 to 0.776) | 0.609 |
| Round 2, quadratic 20/80 | 0.368 | 0.899 (0.750 to 0.957) | 0.705 (0.435 to 0.861) | 0.700 |
| Round 2, ranked 20/80 | 0.222 | 0.813 (0.471 to 0.924) | 0.559 (0.202 to 0.773) | 0.533 |

Taking square roots moves the high-budget share down by 0.19 to 0.26 but leaves every point estimate above one half.
The closed form (THEORY.md, Proposition 1) evaluated at each cell's realised head share lies within 0.03 of the measured value.

## 2. Same ballots, different aggregation rules

Seven aggregators (tokens, sqrt tokens, equal-weight shares, sqrt of shares, plurality of top choice, Borda, Copeland)
applied to each cell's ballots, with 2,000 bootstrap resamples per cell. This treats ballots as exchangeable across the
quadratic and ranked arms, which section 3 supports but cannot prove.

![Winner robustness](../results/figures/ext_winner_robustness.png)

* In all four equal-power cells and in round 2 ranked 20/80, every aggregator picks the same option. In round 2
  quadratic 20/80, six aggregators pick option 4 and Copeland ends in an exact tie.
* **Round 1, ranked 20/80:** the two token-weighted rules (tokens, sqrt tokens) pick option 2 (bootstrap probability
  0.98 and 0.95); all five rules that give each voter equal weight or use only ordinal information pick option 3
  (0.69 to 0.91, depending on the rule). Square-root counting did not undo the effect of the 20/80 budgets here.
* **Round 1, quadratic 20/80:** tokens pick option 4 (0.69); sqrt tokens and every other rule pick option 3 (0.66 to 1.00).
* The round 2 cells other than ranked 20/80 are fragile: the winner's bootstrap probability is 0.46 to 0.81, below 0.8 in 19 of 20 rule-cell pairs.

Reading: the voting-power factor, not the quadratic-versus-linear factor, is where winners become rule dependent.
The article reports that the power factor had little effect on how tokens were spent; this shows it can still matter for what is decided.

## 3. Ballot concentration does not differ by rule

A vote-maximising QV voter would spend tokens in proportion to the square of her values; an expressive voter in proportion to the values;
a vote-maximising linear voter would put everything on one option (THEORY.md, section 4).
So if people respond to the quadratic cost, QV ballots should be more concentrated than ranked ballots.

![Behavioural invariance](../results/figures/ext_behavioural_invariance.png)

| Round | Mean Herfindahl index, quadratic | ranked | Difference (95 % CI) |
|---|---:|---:|---:|
| 1 | 0.423 | 0.416 | 0.007 (-0.054 to 0.067) |
| 2 | 0.405 | 0.439 | -0.033 (-0.095 to 0.025) |

The concentration exponent of quadratic ballots relative to ranked ballots is 0.94 pooled (95 % CI 0.72 to 1.23); the interval
excludes 2 in both rounds and pooled, and includes 1. Round 1 passes an equivalence check at half a pooled SD for all four measures
(Herfindahl, top share, number of options used, QV vote mass); round 2 is inconclusive for three of them (intervals wider than the margin).
The mean ranked-arm Herfindahl index of 0.42 to 0.44 also rules out the corner behaviour that a vote-maximising linear voter would show.

Assumptions: random assignment to arms; the ranked arm as the expressive baseline; whatever the interface showed participants about
cost is unknown to me.

## 4. Who does a concave rule favour: a concentrated minority or a diffuse majority?

![Minority threshold and vote mass](../results/figures/ext_minority_threshold_and_mass.png)

If a fraction *pi* of voters put all tokens on option A and the rest spread evenly over *k* other options, A wins when
*pi* exceeds 1/(1 + k) under linear voting but only when it exceeds 1/(1 + sqrt(k)) under QV (for *k* = 2: 33 % versus 41 %).
The right panel shows why: a ballot spread over four options carries up to twice the QV vote mass of a concentrated one;
on the released ballots the mean mass is 1.75 (range 1.0 to 2.0), the same in both arms. The intuition that QV protects intense minorities
needs voters to be able to buy more votes where they care more. Experiments that let budgets move across issues
(Casella and Sanchez 2019, storable votes and QV; the fixed-budget multi-issue analysis in arXiv 2409.06614) are the right place to look;
this single-decision design is not.

## 5. Compositional re-analysis

Token shares are compositions. Zeros (39 % of ballots give nothing to at least one option) are replaced with the Bayesian-multiplicative rule;
tests use isometric log-ratio coordinates. P-values for the voting-method effect, with the article's own Table 2 value for reference:

![Robustness of p-values](../results/figures/ext_robustness_pvalues.png)

| Test | Round 1 | Round 2 |
|---|---:|---:|
| Article's Table 2 (raw ratios, Pillai) | 0.023 | 0.379 |
| MANOVA on ilr coordinates (zero prior 0.25 / 1 / 4) | 0.077 / 0.046 / 0.024 | 0.80 / 0.75 / 0.71 |
| PERMANOVA on Aitchison distances | 0.154 / 0.102 / 0.056 | 0.77 / 0.76 / 0.78 |
| Dirichlet regression, likelihood ratio | 0.021 / 0.020 / 0.019 | 0.86 / 0.85 / 0.86 |

Round 2 shows nothing under any treatment. For round 1, whether the difference clears 0.05 depends on the test and, for the first two,
on how zeros are replaced; the Dirichlet regression is stable at about 0.02. I would not call the round-1 method effect robust.

![clr biplot](../results/figures/ext_clr_biplot.png)

## 6. High-budget versus low-budget voters inside the 20/80 arms

On Aitchison distances, high-budget voters differ strongly from low-budget voters in round 1 (pseudo-F 18.9, permutation p < 0.001,
16 versus 33 voters): 37.5 % of the high-budget voters have option 4 as their top choice against 9 % of the low-budget voters, and 61 % of the
low-budget voters have option 3. In round 2 there is no difference (pseudo-F 0.11, p 0.96; 11 versus 26 voters).
The grouping is not randomised as far as I can tell (the article describes the high-budget group as early adopters), so this describes who the
high-budget voters were; it does not show that holding power changed what they wanted.

## 7. Monte-Carlo phase diagram

Voters draw preferences from Dirichlet distributions calibrated on the round-1 20/80 arms (high-budget mean shares
0.04 / 0.29 / 0.30 / 0.37, low-budget 0.14 / 0.21 / 0.42 / 0.22, precision 4.3), spend tokens in proportion to preferences, and the aggregator counts them.
The map shows the probability that the high-budget group's favourite (option 4) wins, as the group's size and budget ratio vary.

![Phase diagram](../results/figures/ext_phase_diagram.png)

At a 16:1 budget ratio the probability is 0.55 (f = 0.20) to 0.72 (f = 0.30) with tokens, 0.07 to 0.27 with sqrt tokens, and 0 when each voter counts once.
At 4:1 it is 0.08 to 0.29 with tokens and at most 0.02 with sqrt tokens. This is a statement about the calibrated model, not about the participants.

## 8. Sybil identities

![Sybil](../results/figures/ext_sybil.png)

Splitting one balance over *k* wallets multiplies QV influence by sqrt(*k*) and linear influence by 1; an identity that comes with its own budget
multiplies influence by *k* under any rule (THEORY.md, section 3). The compression in section 1 therefore holds only with one budget per person.
These are closed forms with no data behind them; a preprint (Bennett et al., arXiv 2605.18990) reports simulations on real DAO token distributions with large amplification.

## 9. LLM voters (small exploratory pilot)

Twenty-four induced-value voters (private values 0 to 10 over the four options, 100 tokens, same values under both rules) were answered by
Claude Haiku agents, six voters per session, four sessions per rule. No demographic or identity attributes were simulated.
Ballots are in `data/silicon/pilot_ballots.csv`; the code in `silicon.py` builds the prompts and analyses them, and does not call a model.

![LLM pilot](../results/figures/ext_silicon_pilot.png)

For 18 of the 24 paired voters (three sessions per rule) the allocations are identical or differ by one token, with tokens proportional to values (median
log-log slope 1.02 under both rules); the linear-rule agents never put everything on one option. One quadratic-rule session concentrated
(mean Herfindahl 0.77), overshooting the QV-optimal benchmark of 0.53. So, in this pilot, session-to-session variation is larger than any rule effect. This says
something about one model family under one prompt and nothing about people; any stand-in for human participants would need many independent sessions.

## Directions not attempted here

Ideas, not results: a fixed-budget multi-issue design in which strategic reallocation is possible; social-graph weighting of votes
(the connection-oriented cluster match of Miller, Weyl and Erichsen) and anti-collusion infrastructure such as MACI as responses to the identity problem in section 8;
generative social choice (Fish et al., arXiv 2309.01291) applied to the Human-AI chat messages; delegation (liquid democracy, Kahng, Mackenzie and Procaccia, AAAI 2018);
and many-session LLM-voter experiments with repeated draws per prompt.

## Further reading (details I confirmed)

Collective Constitutional AI (Huang et al., FAccT 2024, arXiv 2406.07814); AI-mediated deliberation (Tessler et al., *Science* 386(6719), 2024);
social choice and alignment (Conitzer et al., arXiv 2404.10271; Sorensen et al., ICML 2024, arXiv 2402.05070);
simulated survey respondents (Argyle et al., *Political Analysis* 2023, arXiv 2209.06899);
voting-power concentration in token DAOs (Fritsch, Müller and Wattenhofer, *Blockchain: Research and Applications* 5(3), 2024; Feichtinger et al., arXiv 2302.12125);
cumulative voting experiments (Gerber, Morton and Rietz, *APSR* 92(1), 1998).
