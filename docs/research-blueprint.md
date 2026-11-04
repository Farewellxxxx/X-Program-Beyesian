# Canonical Paper Blueprint

## 结论先行

### 推荐方向

推荐保留方向 A：

> 真实车辆执行不确定性下的个体化 maximum acceptable motion-boundary calibration，以 realized-motion acceptability model、execution calibration、探索不适成本和真人 feasibility study 为核心。

### 一个主论文还是拆分

推荐一个主论文、两个有明确接口的模块，而不是现在拆成两篇：

1. **离线 prior 模块**：使用历史真实车辆数据学习运动分布、安全范围或群体级 acceptability prior；只有在标签对齐成立时才训练 predictor。
2. **在线 calibration 模块**：在 `P(z|x,c)` 下选择 probe，以尽量少且尽量低的乘客不适暴露估计个人边界。

两模块通过 prior/initialization 接口连接。历史数据 predictor 不是主贡献；若真实数据没有可对齐的 trial-level acceptability 标签，它只提供运动范围、execution prior 或实验设计证据，不进入 efficacy 结果。

不推荐现在拆成两篇的原因：

- 真实数据能否提供可辩护 threshold 标签尚未验证。
- 在线 calibration 的 execution calibration 和真人数据尚未完成。
- 现在拆成两篇会迫使两个尚不完整的证据包各自承担过强 claim。

如果未来真实数据存在可重复、可对齐的 participant × motion segment × acceptability 标签，并有独立验证集，再考虑把 predictor 发展为独立工作。

## 论文核心故事

车辆运动个性化不是寻找“最舒服”的最低运动强度，而是校准每位乘客在日常自动驾驶语境中仍愿意接受的最大纵向运动强度。真实车辆无法精确执行算法给出的连续目标，乘客体验的是传感器测得的 realized motion，而不是 nominal command。因此，校准系统必须区分 command、realized stimulus 和 feedback，在执行不确定性下选择有信息量但不过度暴露乘客于不适的 probe。论文的 HCI 贡献是把 exploration cost 具体化为乘客不适、感知安全、控制感与负担；计算贡献是一个经 execution calibration 支撑的边界搜索框架。仿真只用于预实验压力测试，真人 feasibility study 才能支持交互体验和实际校准结论。

## 唯一术语表

| 符号/术语 | Canonical 定义 | 禁止替代 |
|---|---|---|
| `i` | participant/passenger index | 不用姓名或原始 device ID |
| `t` | calibration trial index | 不与传感器 sample index 混用 |
| `x_t` | 算法给驾驶员/车辆的 target motion command；可为标量或明确维度的向量 | 不称 actual stimulus |
| `c_t` | route、initial speed、traffic、driver、vehicle、trial order 等 execution context | 不把 context 隐含进噪声后忽略 |
| `z_t` | 该 trial 的 realized measured motion-feature vector | 不称 command，不与 level 混用 |
| `m_t=m(z_t)` | 从 realized features 得到的一维、单位和权重已冻结的 realized motion intensity | 不用未校准的任意加权和作为物理事实 |
| `y_t` | primary binary acceptability，`1=acceptable`、`0=unacceptable` | 不把 comfort、MISC 和所有评分都塞入 `y_t` |
| `r_t` | secondary ratings vector：comfort、discomfort、perceived safety、smoothness 等 | 不作为 ground-truth boundary 的自动替代 |
| `P(z|x,c)` | command 和 context 下的 execution distribution | 不假定算法已精确知道真实分布 |
| `\hat P_t(z|x,c)` | 算法在 trial `t` 的 execution model | 不与数据生成真值使用同一符号 |
| `p_i(z)` | `P(y=1|z,i)`，个人 acceptability function | 不解释为“舒适程度” |
| `tau` | 定义 probabilistic boundary 的 criterion；主分析值需在 pilot/理论依据后冻结 | `0.70` 目前不是已验证标准 |
| `B_i(tau)` | realized-intensity domain 上满足 acceptability criterion 的上边界 | 不定义在 command 或 level 上 |
| `D_i` | calibration dataset `{x_t,c_t,z_t,y_t,r_t}` | 不遗漏 command-realized 配对 |
| protocol deviation | 未按计划完成 probe、route/traffic/driver 改变或标记缺失等协议偏离 | 不自动等同 safety violation |
| safety violation | 明确定义的 acceleration/jerk/duration/participant stop 等安全阈值被触发 | 不把所有执行误差都计为 violation |

## 数学定义

### 数据生成与算法认知分离

真实但未知的数据生成过程：

```text
z_t ~ P*(z | x_t, c_t)
y_t ~ Bernoulli(p_i*(z_t, h_t))
```

其中 `h_t` 可表示 carryover、fatigue 或 non-stationarity。

算法使用：

```text
z_t ~ P_hat_t(z | x_t, c_t)
y_t ~ Bernoulli(p_hat_i,t(z_t, h_t))
```

`P*` 与 `P_hat_t`、`p_i*` 与 `p_hat_i,t` 必须在仿真中分开；否则不能检验 model misspecification。

### Realized-intensity boundary

一维 intensity 且 acceptability 对强度单调不增时：

```text
B_i(tau) = sup {m in M : P_i(y=1 | m) >= tau}
```

高维 `z` 时，除非先定义可解释且经验证的 `m(z)`，否则不应声称存在唯一 scalar boundary。可改报 iso-acceptability frontier：

```text
F_i(tau) = {z : P_i(y=1 | z) = tau}
```

### Exploration discomfort cost

主分析应预先冻结一种可解释定义，例如：

```text
C_i = sum_t g(r_t, y_t, stop_t)
```

其中 `g` 的权重不能根据结果选择。至少同时报告未加权原始量：

- unacceptable trial count；
- cumulative discomfort rating；
- maximum discomfort；
- maximum realized overshoot；
- participant stop/skip；
- perceived-safety threshold event。

### Query policy

当前代码在被证明实现正式 probabilistic BO 前，称为：

> uncertain-input BO-inspired boundary-seeking policy

目标形式可写为：

```text
x_{t+1} = argmax_x [
  expected boundary information under P_hat_t(z|x,c)
  - lambda_d * expected discomfort cost
  - lambda_s * safety risk
]
```

正式称为 Bayesian optimization 的最低要求：

- 明确概率 surrogate 与 posterior uncertainty；
- 二元反馈使用 Bernoulli-compatible likelihood 或有理论说明的近似；
- acquisition 依赖 posterior，而非只用核平滑均值；
- `P(z|x,c)` 在 acquisition 中以可复验方式传播；
- 与生成真值分离；
- 方法名、公式和代码一致。

## 研究问题

### RQ1：边界可识别性

在重复、短时纵向 motion probes 下，participant-specific acceptability curves 是否存在可辨识差异，且该差异超过 session/feedback noise？

### RQ2：执行不确定性

`P(z|x,c)` 的方差、偏差和 non-stationarity 多大？显式考虑 execution uncertainty 是否改变 probe 选择或 boundary estimate？

### RQ3：accuracy–exposure trade-off

在相同 trial budget 和相同安全规则下，各策略如何权衡 boundary error、posterior uncertainty、unacceptable exposure 和 cumulative discomfort？

### RQ4：真人 feasibility 与体验

参与者是否理解并接受边界探索？该流程如何影响 perceived control、safety、burden、trust 和 willingness to use？

### RQ5：prior 的增量价值

在标签可用时，群体/历史 prior 是否在 participant/session-level held-out 评估中改善早期 calibration，而不损害 calibration 与 subgroup fairness？

RQ5 为可选；若真实数据标签不能对齐，则从主论文删除。

## 假设

只有在 preregistration 或 analysis plan 冻结后使用确认性措辞：

- H1：participant random effects 对 acceptability 显著，且留一参与者评估显示个体化优于 population-only baseline。
- H2：在执行噪声足够大且 execution model 有校准能力时，uncertainty-aware policy 的 boundary error 或不适暴露优于忽略执行误差的 policy。
- H3：boundary-seeking policy 与 grid/staircase 存在 accuracy–exposure trade-off；不预设某策略在所有指标上支配。
- H4：可解释的 preview/skip/stop 控制提高 perceived control；需要真人条件对比支持。

当前这些是假设，不是事实。

## 三阶段证据管线

不再称“两阶段”：

### Stage 0：Execution calibration

- 无正式参与者或 pilot-safe 条件下重复执行 commands。
- 估计 `P(z|x,c)`、monotonicity、heteroscedasticity 和 context dependence。
- 冻结安全 envelope、segment marker、filter、coordinate frame 和 feature extraction。
- Go/no-go：continuous command 不可识别时转为 calibrated stochastic templates。

### Stage 1：Simulation and offline validation

- 使用分离的生成/认知模型、多随机种子和多 misspecification 场景。
- 比较 equal-budget 与 protocol-budget。
- 只支持算法诊断和 study design，不支持真人有效性。

### Stage 2：Human feasibility study

- 先验证同步、标签和 stop rule，再评估体验和 boundary repeatability。
- 小样本只支持 feasibility，不做 population efficacy claim。

## 数据来源与证据边界

| 数据 | 可支持 | 不可支持 |
|---|---|---|
| 原 TVCG VR 数据 | adaptive detection-threshold 与 staircase/UCB 先例 | 车辆舒适构念、真实车辆 execution uncertainty |
| `new_idea` 合成数据 | 指标和仿真管线开发 | 真人差异、真实安全 |
| 当前 extended simulation | 在代码和多种子复验后支持 modeled-scenario 诊断 | 真人效果、真实 `P(z|x)` |
| IEEE THMS 真实车辆归档 | 实测运动范围、session 结构；标签对齐成立时支持 acceptability model | 未对齐前不支持个人 threshold |
| Stage 0 calibration | `P(z|x,c)` 与 command feasibility | 乘客边界 |
| Stage 2 user study | feasibility、体验、重复性与 trial-level acceptability | 超出样本/协议范围的普遍安全或 efficacy |

## 推荐方法

1. 先完成 execution calibration 和信号管线冻结。
2. acceptability 使用 logistic/probit、monotone GAM、ordinal/mixed-effects baseline；数据足够后才考虑 GP classification。
3. participant/session/group 为 split unit；共享同一车辆轨迹的乘客使用 session/group cluster 或 random effect。
4. boundary 从可校准概率曲线 criterion crossing 得出。
5. uncertainty-aware query policy 与 naive、randomized grid、staircase 在同预算、同安全规则下比较。
6. 主要结果报告 participant-level generalization、calibration、AUPRC/AUROC、boundary MAE/interval coverage 和 discomfort exposure。

## Contributions

### 可主张但需数据支持

1. 把真实车辆个体 motion-boundary calibration 定义为一个 exploration 有身体成本和控制感成本的 HCI 问题。
2. 建立 command–realized stimulus–feedback 分离的可审计研究管线。
3. 在真实 execution calibration 支撑下，评估 uncertainty-aware boundary-seeking policy 的 accuracy–exposure trade-off。
4. 提供面向参与者控制、预览、跳过和停止的交互设计证据。

### 当前只能称设计贡献

- user-study protocol；
- simulation stress-test framework；
- predictor-as-prior architecture；
- safety and measurement checklist。

## Claims to avoid

- “首次把 BO 用于自动驾驶个性化。”
- “首次发现 acceleration/jerk 影响舒适。”
- “OptiCarVis 证明 BO 可优化车辆运动舒适度。”
- “VR detection threshold 等于车辆舒适边界。”
- “算法精确执行连续 acceleration/jerk command。”
- “仿真证明方法对真人有效。”
- “`tau=0.70` 是公认舒适标准。”
- “历史真实车辆数据已经提供 ground-truth personal threshold。”
- “所有 protocol deviation 都是 safety violation。”
- “KernelAcceptanceSurrogate 本身证明实现了 Bayesian optimization。”

## Limitations

- acceptability 是语境依赖构念，受措辞、route、初始速度、持续时间和记忆效应影响。
- 一次 ride 无法分离稳定个体差异与 session 状态。
- driver/traffic context 可能使 `P(z|x,c)` non-stationary。
- 一维 `m(z)` 会压缩 acceleration、jerk、duration 和方向的交互。
- 二元反馈信息量有限且可能不满足单调性。
- 小样本真人研究不能提供强 population generalization。
- Safe BO 的理论保证不能自动转移到启发式风险惩罚。

## 论文章节结构

1. Introduction：boundary calibration、exploration cost、real execution uncertainty。
2. Related Work：AV comfort；personalized driving/PBO；uncertain-input/safe BO；threshold calibration；HITL calibration UX。
3. Formulation：`x,c,z,m,y,r`、boundary、cost、安全和证据边界。
4. Stage 0 Execution Calibration：车辆、路线、传感器、信号处理、`P(z|x,c)`。
5. Calibration Policies：probabilistic acceptability model、query policy、baselines、公平预算。
6. Simulation Stress Test：生成/认知模型分离、多种子、misspecification。
7. Human Feasibility Study：设计、伦理、measures、统计模型。
8. Results：先 execution validity，再算法/体验；仿真与真人分开。
9. Discussion：何时需要 predictor prior、设计含义、安全与可部署边界。
10. Limitations and Conclusion。

## Decision log

| 决策 | 推荐 | 状态 |
|---|---|---|
| 主方向 | A；predictor 仅作可选 prior | 审计推荐，待导师确认 |
| 论文数量 | 一个主论文、两个模块 | 审计推荐，待数据对齐后复核 |
| boundary domain | realized intensity 或 iso-acceptability frontier | canonical |
| `tau` | 暂定；pilot 前不冻结为 0.70 | 待导师/数据决定 |
| command type | continuous command 为假设；Stage 0 go/no-go | 尚未验证 |
| 方法名 | 当前先称 BO-inspired policy | 待代码审计决定 |
| predictor | 标签对齐失败则不训练 | 待数据审计决定 |
| human comparison | feasibility 优先，强算法对比后置 | 待伦理、预算与导师确认 |

