# 执行模型复杂度选择与参数不确定性传播

本轮只使用合成执行和合成乘客，基线为 `33e0123`。响应层仍是单调 Bernoulli–logistic 边界后验，策略采集分数仍是启发式。修改发生在算法持有的执行分布，真实执行生成器、乘客模型、反馈预算和成对随机流不变。

## 三种均值模型与完整协方差

均值候选为仅偏差、偏差加增益、偏差加增益和二次曲率，阶数 k=0/1/2。所有候选均有完整三通道残差协方差。命令 x 的中心化值 d=x−1.125，加速度均值为 `clip(0.05+0.94x+b+g d+q d²,0.20,2.35)`；缺失的高阶系数固定为零。所有候选在完整命令范围 0.35–1.90 上满足 `0.94+g >= 1.55|q|`，不是仅在校准点上单调。

与前版一样，用公共通道尺度 s_a=0.045+0.055 level、s_j=0.18+0.24 level 和 s_t=0.18 标准化观测。定义 y=(a−0.05−0.94x)/s_a，W 两列分别为 `(j−0.58−1.74a−0.10x)/s_j` 与 `(t−3.90+0.30a)/0.18`，X 为 `[1,d,d²]/s_a` 中当前候选使用的列。联合高斯残差通过条件分解表示：

```
W_i ~ N(0, Lambda)
y_i | W_i ~ N(X_i beta + W_i c, sigma²)
eta = [beta, c]
Sigma_aa = sigma² + c' Lambda c
Sigma_aW = c' Lambda
Sigma_WW = Lambda
```

该分解只用于统计推断；它不是在实际执行之前观测 jerk/duration 的控制策略。预测时从恢复的联合协方差生成三通道残差，再按照原物理关系和裁剪规则生成运动。因而可表达非等方差及三个不同的同期相关系数；尚未表示时间相关噪声。

## 固定的适当先验、证据和模型概率

先验为 `eta|sigma² ~ N(0,sigma² V0)`，beta 三个先验尺度分别 0.50/0.50/0.75，c 两个尺度均为 1；`sigma² ~ IG(shape=2,rate=1)`；`Lambda ~ IW(df=4,scale=I_2)`。未施加单调条件前，两个噪声先验的均值均为单位尺度。模型先验概率各 1/3。设置在正式结果出现前固定，未根据结果调参。

令 H=[X,W]，精度 A=V0⁻¹+H'H，则 V=A⁻¹、m=VH'y、a=2+n/2、b=1+0.5[(y−Hm)'(y−Hm)+m'V0⁻¹m]。这是正规化共轭更新，证据包括行列式和 Gamma 正规化常数；W 的边际密度及标准化雅可比对三个候选相同，比较时消去。可参考[共轭贝叶斯线性模型推导](https://arxiv.org/html/2406.01819v1)。

每个先验和后验均以全域单调事件为条件。模型证据必须乘以 `Z_posterior / Z_prior`，不能仅截断后验或把投影后的点估计当作后验。k=1 使用单变量 Student-t 尾概率；k=2 对曲率积分，以条件 Student-t 尾概率计算二维单调区域的概率。积分以标准化曲率为坐标，在 q=0 处分开，绝对和相对容差均为 1e−9。当该分点离 Student-t 密度中心超过八个尺度时，另在密度中心分段复核；若两种积分相差超过绝对容差或原积分失效，采用中心分段的值，避免集中后验的概率质量被无限区间积分器漏掉。数值下溢至零的模型权重按 0 log 0=0 计算熵。概率经 log-sum-exp 正规化得到模型权重。

预测使用这些权重进行贝叶斯模型平均；MAP 阶数只是报告字段，不作为硬切换。小预算分不清模型时保留模型选择的不确定性，不能把较高模型概率当成已证明真实物理阶数。

## 联合抽样与可复现性

每个候选默认保留 2,048 个联合后验抽样：先抽 sigma²，再条件抽 eta，若 beta 不单调则联合拒绝这对参数；Lambda 独立从更新后的逆 Wishart 后验抽样，之后恢复 Sigma。每次提议最多 256 个，单候选最多 200,000 次提议；超出上限明确失败，不投影、不丢弃失败候选。实现使用固定版本 [SciPy 1.13.1 的 inverse-Wishart](https://docs.scipy.org/doc/scipy-1.13.1/reference/generated/scipy.stats.invwishart.html)。

抽样种子只由有序的四列可观测校准记录、公共执行设置和先验设置派生，不使用 profile、真实参数、乘客或仿真过程种子。抽样数不进入种子，固定批次使 8,192 次抽样保留前 2,048 次的精确前缀。每个模型的参数数组不可写；设置、种子来源、抽样内容和校准记录均有 SHA-256 指纹。保存观测和参数摘要即可重建抽样，不额外发布大数组。

一次未来执行预测先抽模型，再抽一组 beta/Sigma，最后抽执行噪声。因此包含模型选择、均值参数、协方差估计和执行本身的随机性。当前策略只使用单次未来执行的边际预测；没有加入跨多次未来执行共享参数的联合规划，也没有使用乘客反馈在线更新执行参数。NaiveContinuousBO 继续使用模型平均参数的名义运动特征；UncertainInputBO 积分新的预测分布。

## 校准数据和边界

只读取命令、峰值加速度、峰值 jerk、duration；至少八条有限且不触裁剪边界的记录。检查公共范围、三列设计满秩及条件数不超过 1e8。触边记录沿用前版排除规则并计数，没有加入删失/截断似然。即使零残差，适当先验仍保证正定预测噪声。对裁剪频繁、边界饱和或缺少命令覆盖的数据，现有拟合规则仍有限制。

`belief_execution_noise_scale` 继续只是兼容标量 sqrt(trace(E Sigma)/3)，不是完整预测标准差。`fit_cov_*` 是模型加权的 E Sigma，也不包含 beta 和模型均值变化带来的额外预测方差。强度/风险预测实际使用完整混合分布。辅助 RMS jerk/speed 字段保持原兼容标量处理，不进入当前边界或风险目标。

## 验证设计和指标

沿用七种真实执行条件，预算 8/20/40/160，五批独立人群、每批两个过程重复；280 个新场景，以及前版固定二次点估计的 280 个精确重放场景。每场景 24 人×5 策略×12 次反馈，共 806,400 次反馈；另跑扩展示例 2,880 次和 POC 900 次。校准次数是额外的无乘客反馈预算。

每组校准观测比较六种执行预测：前版 `quadratic_covariance`；新后验参数均值构成的 `quadratic_plugin` 和 `adaptive_plugin`；固定二次的 `quadratic_posterior`；完整 `adaptive_posterior`；已知真实分布的 oracle。中间四种形成复杂度选择×参数传播的 2×2 消融。插件使用 E beta 和 E Sigma；其方差不额外加入均值参数的变化。旧模型到新模型还包含先验和协方差拟合方法的改变，不能把全部收益归因于单个开关。完整反馈实验只跑新旧两端，执行诊断消融不能证明反馈层的因果分解。

六种诊断共用该校准单元的新后验来源字段：诊断表的 `execution_estimator`/`fit_*` 记录父级 adaptive 拟合，实际使用的预测分布由 `variant` 和 `variant_fingerprint` 标识。不能把 oracle 或旧二次行上的共享 `fit_cov_*` 当成该行预测器的协方差。比较汇总中的 `estimator` 直接取自 `variant`。

每种预测在完整范围的 21 个命令点生成 4,096 个样本；校准只覆盖中间 60%，外推区为两侧共八个命令点。保留前版同创新样本的诊断列用于精确复核，同时新增独立真实未来抽样计算主要覆盖率；未来样本不用于拟合、分位数计算或策略。预测 RNG namespace 为 0xD1A6，未来评估为 0xA11C，不同预测方式共享相同真实未来样本。

同时报告均值误差、标准差误差、W1、协议越界概率误差、独立 90% 区间覆盖率、宽度和区间评分。评分为 `upper−lower + 20 max(lower−y,0) + 20 max(y−upper,0)` 的未来样本均值，越低越好；它惩罚过宽区间，也惩罚漏覆盖，见 [Gneiting 与 Raftery 的适当评分规则](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)。训练加速度均值 RMSE 单列报告，训练误差下降本身不是外推改善。

先平均每个过程重复中的命令点，再平均同一人群批次的两个重复，最后对五个批次做成对 t 区间。沿用历史脚本四舍五入的临界值 2.776。区间未做多重比较调整，五批样本的结果应作有限合成证据解释。执行校准流按场景重复，与人群编号关联用于配对，不表示校准数据含有人群反馈。

预先固定 14 个敏感性单元：七类条件×预算 8/40×第一人群/第一重复；比较抽样数 2,048/8,192，以及 beta 先验尺度 1×/2×。其余先验保持不变，不能把这 14 个单点检查当成独立人群验证。

## 运行

```bash
python -m pip install -r requirements-simulation.txt
python -m pytest -q
python long_horizon_audit/scripts/run_adaptive_execution_audit.py --workers 8
python long_horizon_audit/scripts/compare_adaptive_execution.py
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py --execution-estimator adaptive_posterior
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py --execution-estimator adaptive_posterior
```

每 worker 的 OPENBLAS_NUM_THREADS/OMP_NUM_THREADS/MKL_NUM_THREADS 建议均为 1。审计 `--suite adaptive|replay|sensitivity` 可分开运行，前两者支持按 profile 分组；全部完成后运行严格比较。原默认 simple、旧输出目录和旧档案保持冻结。新输出使用 `outputs_adaptive_execution[_legacy_kernel][_poc]`、`derived/adaptive_execution_20261104` 和 `results/adaptive_execution_20261104`。
