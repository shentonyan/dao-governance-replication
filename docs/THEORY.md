# Theory notes: budgeted token voting under a concave aggregator

**English** | [简体中文](THEORY.zh-CN.md)

These notes give the closed forms used in [`src/dao_replication/theory.py`](../src/dao_replication/theory.py).
They are my own derivations from the voting rules as the article describes them (quadratic: "4 tokens
give 2 votes"; ranked/weighted: a voter spreads voting power over options; 20/80: 20 % of participants
hold 80 % of the tokens). Each proposition is checked against brute-force computation in
`tests/test_theory.py`. They are elementary; the point is to make the comparisons in
[EXTENSIONS.md](EXTENSIONS.md) exact. Nothing here is a claim about the article's authors' intentions.

## 0. Setup

A voter *i* has budget *B_i* and places tokens *t_i = (t_i1, ..., t_im)*, with *t_ij >= 0* and
*sum_j t_ij <= B_i*. An aggregator with exponent *alpha* in (0, 1] turns tokens into effective votes
and adds them up:

    score_j = sum_i (t_ij)^alpha ,  the option with the largest score wins.

* *alpha = 1*: linear ("ranked/weighted") voting, votes = tokens.
* *alpha = 1/2*: quadratic voting (QV), votes = sqrt(tokens).
* *alpha -> 0*: every option with at least one token counts the same (approval-like).

Write *s_ij = t_ij / sum_k t_ik* for allocation shares. Voter *i*'s total effective votes ("vote mass") are

    M_i(alpha) = B_i^alpha * sum_j s_ij^alpha .                                   (0)

For *alpha = 1/2* and *m = 4* the factor *sum_j sqrt(s_ij)* lies between 1 (all tokens on one option) and
2 (even split). Linear voting has mass *B_i* whatever the split.

## 1. Power compression

**Proposition 1.** Let a fraction *f* of voters have budget *B_H* and the rest *B_L*, and suppose both groups
split their tokens in the same way (same distribution of shares). Then the high-budget group's share of
total effective votes is

    P(f, r, alpha) = f r^alpha / ( f r^alpha + 1 - f ),    r = B_H / B_L.          (1)

*Proof.* By (0) each voter's mass is *B^alpha* times a spread factor with the same distribution in both groups;
summing over voters gives group masses proportional to *n_H B_H^alpha* and *n_L B_L^alpha*. ∎

Special cases: *alpha = 1* is the token share, *alpha = 0* the head count *f*. With the article's 20/80 design
(*f* = 0.2, budgets 400 and 25, so *r* = 16), *P = 0.8* under linear voting and *P = 0.5* exactly under QV, because
*r^(1/2) = 4 = (1 - f)/f*. QV does not remove the asymmetry; it halves the distance between the token share and
the head count (on a log-odds scale, it halves it exactly: *logit P = logit f + alpha log r*).

If the two groups spread differently, (1) is multiplied by the ratio of their mean spread factors
*E[sum_j s_ij^alpha]*, which is why [EXTENSIONS.md](EXTENSIONS.md) also reports the measured share.

## 2. A concentrated minority against a diffuse majority

**Proposition 2.** All voters have budget *B*. A fraction *pi* puts everything on option A. The other voters
split their tokens evenly over *k* other options. Then A wins iff

    pi > 1 / (1 + k^alpha) .                                                      (2)

*Proof.* A scores *pi n B^alpha*. Each other option scores *(1 - pi) n (B/k)^alpha = (1 - pi) n B^alpha k^(-alpha)*.
A wins iff *pi / (1 - pi) > k^(-alpha)*, which rearranges to (2). ∎

Linear: *1/(1 + k)* (1/3 for *k* = 2). QV: *1/(1 + sqrt(k))* (0.414 for *k* = 2). Approval-like: 1/2. A concave
aggregator therefore makes it *harder* for a concentrated minority to win when voters allocate expressively,
because a voter who spreads tokens over several options casts more total effective votes (up to twice as many for
*m* = 4) than one who concentrates. The usual argument that QV protects intense minorities relies on voters
choosing how many votes to buy according to how much they care, which needs a budget that can move across
issues or a price that is paid, not a fixed budget on one multi-option decision.

## 3. Splitting, wallets and Sybil identities

**Proposition 3 (token splitting).** A holder of balance *b* splits it into *k* wallets of *b/k* that vote alike.
Their effective votes are *k (b/k)^alpha = k^(1 - alpha) b^alpha*, a gain of *k^(1 - alpha)*: 1 for linear, *sqrt(k)*
for QV, approaching *k* as *alpha -> 0*.

**Proposition 4.** Every aggregator *phi* that is concave with *phi(0) = 0* is subadditive, so splitting never
loses and strictly gains unless *phi* is linear. *Proof.* Concavity and *phi(0) = 0* give *phi(x)/x* non-increasing,
hence *phi(x + y) <= phi(x) + phi(y)*, strictly for strictly concave *phi*. ∎

**Proposition 5 (new budgets).** If each identity receives its own budget *B*, the attacker's gain is *k* for every
*alpha*: the concave map gives no protection. QV's compression of budget differences (Proposition 1) therefore
presupposes one budget per person, i.e. an identity layer.

Together: with a token-weighted balance, being anti-plutocratic (strictly concave) and being split-proof (linear)
cannot both hold. A preprint on DAO token distributions reaches a related conclusion by simulation
(Bennett et al., arXiv 2605.18990; not peer-reviewed as far as I could confirm).

## 4. Benchmarks for a vote-maximising voter

Suppose a voter values option *j* at *u_j* and the chance that an extra vote on *j* is pivotal is *q_j*; set *w_j = u_j q_j*.
The expected gain from votes *v_j* is approximately *sum_j w_j v_j*.

**Proposition 6 (QV).** Maximising *sum_j w_j v_j* subject to *sum_j v_j^2 = B* (tokens *t_j = v_j^2*) gives *v_j ∝ w_j*,
so tokens are proportional to *w_j^2*. *Proof.* Lagrange: *w_j = 2 lambda v_j*. ∎

**Proposition 7 (linear).** The objective is linear in tokens, so the optimum is a corner: all tokens on the option with the
largest *w_j*.

Relative to an "expressive" voter who spends tokens in proportion to *w_j*, a QV-optimal voter's tokens are
proportional to *w_j^2*, i.e. concentration exponent 2. This is the benchmark in `behaviour.relative_gamma`.
(Lalley and Weyl's equilibrium analysis for QV with a binary decision has votes proportional to values in large
populations; the multi-option fixed-budget case is the subject of the papers listed below.)

## 5. Log-ratio coordinates and the budget

A composition is invariant to scaling, so a log-ratio analysis of allocation shares is unaffected by a voter's budget:
the composition tests in `compositional.py` ask *how* tokens were split, and the power results in
`counterfactual.power_equalisation` ask *how much weight* each ballot gets. Keeping the two apart is what lets the
20/80 factor be analysed in both ways. When all budget is spent the four raw ratios sum to one, so their covariance
matrix is singular; the isometric log-ratio (ilr) coordinates are three free numbers with an orthonormal basis, so
distances between ballots are the Aitchison distances.

## References (only items whose bibliographic details I could confirm)

* Lalley, S. P. and Weyl, E. G. (2018). Quadratic Voting: How Mechanism Design Can Radicalize Democracy.
  *AEA Papers and Proceedings* 108. DOI 10.1257/pandp.20181002. Longer manuscript: *Nash Equilibria for Quadratic Voting*
  (author's copy at http://www.stat.uchicago.edu/~lalley/Papers/QV.pdf).
* Goeree, J. K. and Zhang, J. (2017). One man, one bid. *Games and Economic Behavior* 101, 151-171. DOI 10.1016/j.geb.2016.10.003.
* Eguia, J., Immorlica, N., Ligett, K., Weyl, E. G. and Xefteris, D. Quadratic Voting With Multiple Alternatives.
  SSRN 3319508 (journal version not confirmed).
* Fixed-budget and Multiple-issue Quadratic Voting. arXiv 2409.06614 (authors not confirmed from the page I read).
* Quarfoot, D., Kohorn, D. von, Slavin, K., Sutherland, R., Goldstein, D. and Konar, E. (2017). Quadratic voting in the wild.
  *Public Choice* 172(1). DOI 10.1007/s11127-017-0416-1.
* Casella, A. and Sanchez, L. (2019). Storable Votes and Quadratic Voting: An Experiment on Four California Propositions.
  NBER Working Paper 25510.
* Buterin, V., Hitzig, Z. and Weyl, E. G. (2019). A Flexible Design for Funding Public Goods. *Management Science* 65(11).
  arXiv 1809.06421.
* Bennett, Vander Vos, Le and Belenkiy. Concave is the New Linear: The Impossibility of Anti-Plutocratic DAO Governance.
  arXiv 2605.18990 (preprint).
* Aitchison, J. (1986). *The Statistical Analysis of Compositional Data*. Chapman and Hall.
* Egozcue, J. J. et al. (2003). Isometric logratio transformations for compositional data analysis. *Mathematical Geology* 35(3), 279-300.
  DOI 10.1023/A:1023818214614.
* Martin-Fernandez, J. A., Hron, K., Templ, M., Filzmoser, P. and Palarea-Albaladejo, J. (2015). Bayesian-multiplicative treatment of
  count zeros in compositional data sets. *Statistical Modelling* 15(2). DOI 10.1177/1471082X14535524.
