# 理论笔记：预算制代币投票与凹聚合函数

[English](THEORY.md) | **简体中文**

本文给出 [`src/dao_replication/theory.py`](../src/dao_replication/theory.py) 所用的封闭形式。
它们是我根据文章描述的投票规则自行推导的（二次投票："4 个 token 得 2 票"；ranked/weighted 投票：选民把投票权分配到各选项；
20/80：20% 的参与者持有 80% 的 token）。每个命题都在 `tests/test_theory.py` 中与暴力计算对照。
推导都很初等，目的是让 [EXTENSIONS.zh-CN.md](EXTENSIONS.zh-CN.md) 中的比较变得精确；这里不涉及对文章作者意图的任何断言。

## 0. 设定

选民 *i* 的预算为 *B_i*，把 token 放在 *t_i = (t_i1, ..., t_im)* 上，*t_ij >= 0* 且 *sum_j t_ij <= B_i*。
指数为 *alpha*（0 < alpha <= 1）的聚合器把 token 转成有效票再加总：

    score_j = sum_i (t_ij)^alpha ，得分最高的选项获胜。

* *alpha = 1*：线性（"ranked/weighted"）投票，票数 = token 数。
* *alpha = 1/2*：二次投票（QV），票数 = sqrt(token)。
* *alpha -> 0*：只要某选项拿到至少 1 个 token，就按同样的权重计入（近似赞成票）。

记分配份额 *s_ij = t_ij / sum_k t_ik*。选民 *i* 的有效票总量（"票质量"）为

    M_i(alpha) = B_i^alpha * sum_j s_ij^alpha 。                                  (0)

当 *alpha = 1/2*、*m = 4* 时，因子 *sum_j sqrt(s_ij)* 介于 1（全部压在一个选项）与 2（平均分配）之间；线性投票的质量恒为 *B_i*，与分配方式无关。

## 1. 权力压缩

**命题 1。** 设比例为 *f* 的选民预算为 *B_H*，其余为 *B_L*，且两组选民的 token 分配方式同分布。则高预算组占总有效票的份额为

    P(f, r, alpha) = f r^alpha / ( f r^alpha + 1 - f )，  r = B_H / B_L 。          (1)

*证明。* 由 (0)，每位选民的质量等于 *B^alpha* 乘以一个在两组中同分布的分配因子；对选民求和，两组质量分别正比于 *n_H B_H^alpha* 与 *n_L B_L^alpha*。∎

特例：*alpha = 1* 为 token 份额，*alpha = 0* 为人头占比 *f*。对文章的 20/80 设计（*f* = 0.2，预算 400 与 25，*r* = 16），线性投票下 *P = 0.8*，
QV 下恰为 *P = 0.5*，因为 *r^(1/2) = 4 = (1 - f)/f*。QV 并未消除不对称，只是把 token 份额与人头占比之间的差距缩小了一半
（在 logit 尺度上恰好减半：*logit P = logit f + alpha log r*）。

若两组分配方式不同，(1) 需乘以两组平均分配因子 *E[sum_j s_ij^alpha]* 之比，所以 [EXTENSIONS.zh-CN.md](EXTENSIONS.zh-CN.md) 同时报告了实测份额。

## 2. 集中的少数派 vs 分散的多数派

**命题 2。** 所有选民预算均为 *B*。比例 *pi* 的选民把全部 token 压在选项 A；其余选民把 token 平均分给另外 *k* 个选项。则 A 获胜当且仅当

    pi > 1 / (1 + k^alpha) 。                                                     (2)

*证明。* A 得分 *pi n B^alpha*；其他每个选项得分 *(1 - pi) n (B/k)^alpha = (1 - pi) n B^alpha k^(-alpha)*。
A 获胜当且仅当 *pi / (1 - pi) > k^(-alpha)*，整理即 (2)。∎

线性：*1/(1 + k)*（*k* = 2 时为 1/3）；QV：*1/(1 + sqrt(k))*（*k* = 2 时为 0.414）；近似赞成票：1/2。
因此当选民按偏好"表达式"分配时，凹聚合器让集中的少数派*更难*获胜：把 token 分散到多个选项的选民，其总有效票更多（*m* = 4 时最多是集中者的 2 倍）。
"QV 保护强烈偏好的少数"这一常见论证，依赖于选民按在乎程度决定买多少票，这需要预算可以在不同议题间转移，或票需要付费，
而不是在单个多选项决策上给定一笔固定预算。

## 3. 拆分、钱包与女巫身份

**命题 3（拆分 token）。** 持有余额 *b* 的人把它拆成 *k* 个各 *b/k* 的钱包并投相同选项，有效票为 *k (b/k)^alpha = k^(1 - alpha) b^alpha*，
增益为 *k^(1 - alpha)*：线性为 1，QV 为 *sqrt(k)*，*alpha -> 0* 时趋近 *k*。

**命题 4。** 任何凹且 *phi(0) = 0* 的聚合函数 *phi* 都是次可加的，所以拆分绝不吃亏，除非 *phi* 为线性，否则严格获益。
*证明。* 凹性与 *phi(0) = 0* 推出 *phi(x)/x* 不增，故 *phi(x + y) <= phi(x) + phi(y)*，严格凹时为严格不等式。∎

**命题 5（新预算）。** 若每个身份都获得自己的完整预算 *B*，攻击者的增益对任何 *alpha* 都是 *k*：凹映射不提供任何保护。
因此 QV 对预算差异的压缩（命题 1）以"每人一份预算"为前提，即需要身份层。

合起来：对按余额计票的体系，"反富豪"（严格凹）与"抗拆分"（线性）不能同时成立。一篇关于 DAO 代币分布的预印本通过仿真得到相关结论
（Bennett 等，arXiv 2605.18990；据我所能确认，尚未经同行评审）。

## 4. 追求票数最大化的选民的基准

设选民对选项 *j* 的价值为 *u_j*，多一票在 *j* 上起决定作用的概率为 *q_j*，记 *w_j = u_j q_j*。投 *v_j* 票的期望收益近似为 *sum_j w_j v_j*。

**命题 6（QV）。** 在 *sum_j v_j^2 = B*（token *t_j = v_j^2*）约束下最大化 *sum_j w_j v_j*，得 *v_j ∝ w_j*，即 token 正比于 *w_j^2*。*证明。* 拉格朗日条件 *w_j = 2 lambda v_j*。∎

**命题 7（线性）。** 目标对 token 是线性的，最优解在角点：全部 token 压给 *w_j* 最大的选项。

相对于按 *w_j* 比例分配的"表达式"选民，QV 最优选民的 token 正比于 *w_j^2*，即集中度指数为 2；这就是 `behaviour.relative_gamma` 使用的基准。
（Lalley 与 Weyl 对二元决策 QV 的均衡分析表明，大样本下票数正比于价值；多选项固定预算的情形见下列文献。）

## 5. 对数比坐标与预算

成分对缩放不变，所以对分配份额的对数比分析不受选民预算影响：`compositional.py` 中的检验回答"token 是*怎样*分配的"，
`counterfactual.power_equalisation` 回答"每张选票获得*多大权重*"。把两者分开，才能用两种方式分析 20/80 因素。
当预算全部花完，四个原始比例之和为 1，其协方差矩阵奇异；等距对数比（ilr）坐标是三个自由数，基底正交，选票间的距离即 Aitchison 距离。

## 参考文献（仅列出我能确认书目信息的条目）

* Lalley, S. P. and Weyl, E. G. (2018). Quadratic Voting: How Mechanism Design Can Radicalize Democracy. *AEA Papers and Proceedings* 108.
  DOI 10.1257/pandp.20181002。长稿：*Nash Equilibria for Quadratic Voting*（作者主页 http://www.stat.uchicago.edu/~lalley/Papers/QV.pdf）。
* Goeree, J. K. and Zhang, J. (2017). One man, one bid. *Games and Economic Behavior* 101, 151-171. DOI 10.1016/j.geb.2016.10.003。
* Eguia, J., Immorlica, N., Ligett, K., Weyl, E. G. and Xefteris, D. Quadratic Voting With Multiple Alternatives. SSRN 3319508（未确认期刊版本）。
* Fixed-budget and Multiple-issue Quadratic Voting. arXiv 2409.06614（作者信息未能从所读页面确认）。
* Quarfoot, D. 等 (2017). Quadratic voting in the wild: real people, real votes. *Public Choice* 172(1). DOI 10.1007/s11127-017-0416-1。
* Casella, A. and Sanchez, L. (2019). Storable Votes and Quadratic Voting: An Experiment on Four California Propositions. NBER Working Paper 25510。
* Buterin, V., Hitzig, Z. and Weyl, E. G. (2019). A Flexible Design for Funding Public Goods. *Management Science* 65(11). arXiv 1809.06421。
* Bennett, Vander Vos, Le and Belenkiy. Concave is the New Linear: The Impossibility of Anti-Plutocratic DAO Governance. arXiv 2605.18990（预印本）。
* Aitchison, J. (1986). *The Statistical Analysis of Compositional Data*. Chapman and Hall。
* Egozcue, J. J. 等 (2003). Isometric logratio transformations for compositional data analysis. *Mathematical Geology* 35(3), 279-300. DOI 10.1023/A:1023818214614。
* Martin-Fernandez, J. A., Hron, K., Templ, M., Filzmoser, P. and Palarea-Albaladejo, J. (2015). Bayesian-multiplicative treatment of count zeros
  in compositional data sets. *Statistical Modelling* 15(2). DOI 10.1177/1471082X14535524。
