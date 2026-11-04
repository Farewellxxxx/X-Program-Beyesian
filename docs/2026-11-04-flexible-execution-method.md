# 增益、非线性与相关噪声的执行估计

本轮基线为 `9679123801b67d03eb483abef4259dacd101f150`。只使用合成执行记录，保留真实执行生成器、二元响应后验和启发式选点规则。原来的偏差/公共噪声尺度估计器作为 `simple` 基线保留；新增 `quadratic_covariance` 估计器由公开命令和实测加速度、jerk、时长拟合，不接收真实扰动系数或乘客标签。

## 估计的量

令 d=x−(x_min+x_max)/2。加速度均值为 clip(0.05+0.94x+b+gd+qd², 0.20, 2.35)。b、g、q 分别描述偏差、相对原有斜率的增益变化和二次非线性。要求 0.94+g±(x_max−x_min)q≥0，因此整个命令范围的均值单调不减；裁剪也保持单调性。这不是任意非线性系统辨识。

条件 jerk 均值仍为 0.58+1.74a+0.10x，时长均值为 3.90−0.30a。三个通道的已知基础标准差形状保持原样：s_a=0.045+0.055·level、s_j=0.18+0.24·level、s_t=0.18，level=(x−x_min)/(x_max−x_min)。在此标准化后学习完整 3×3 残差协方差 Σ，包括三个方差和三种两两相关性。因此模型能表示不同通道尺度和非对称的相关系数组合，并不只拟合生成器使用的单一 ρ。

这些是**同一次执行中三个通道的相关噪声**，并未建模不同执行之间的时间自相关。RMS jerk 和速度变化只是辅助输出，继续使用兼容尺度 sqrt(trace(Σ)/3)；它们不参与本次强度/协议风险计算或拟合。导出字段 `belief_execution_noise_scale` 在新模型中也仅表示这个兼容尺度，不能把它当成完整分布；完整 Σ 在 `fit_cov_00/01/02/11/12/22` 中。

## 拟合与小预算正则化

拟合只读取 `target_command_x`、`peak_accel`、`peak_jerk`、`duration_s`。拒绝缺列、非有限值和超出公开边界的记录；恰在实测裁剪边界上的记录排除并计数。至少需要八条剩余记录，三列加权二次设计必须满秩、条件数不超过 1e8。不能辨识时明确报错，不静默跳过场景。

设计矩阵 X=[1,d,d²]/s_a。三列响应 Y 分别为相对原始线性均值的加速度残差/s_a、相对条件 jerk 均值的残差/s_j、相对条件时长均值的残差/0.18。先计算 R=Y−X·lstsq(X,Y)，再取 S=RᵀR/(n−3)。这给三通道残差乘积共同的自由度；jerk/时长的投影仅用于协方差估计，不把样本投影当作新增条件均值参数。

协方差使用固定收缩：Σ=(1−λ)S+λ·diag(S)+1e−8 I，λ=3/n。系数使用零中心岭惩罚，先验尺度 b/g/q 分别固定为 0.50/0.50/0.75；H=XᵀX+max(S_aa,1e−8)diag(1/prior_sd²)，score=XᵀY_a。枚举两个端点导数约束的四种活动集，选择可行的二次目标最小值。采样对标准正态向量作 Cholesky 变换，再执行原有条件均值与实测裁剪。

这些常数在看结果前固定，没有根据本轮曲线调优。收缩是简单固定规则，不称为 Ledoit–Wolf 最优估计；系数与协方差均作为点估计使用。加权拟合的一般依据见 [NIST 加权最小二乘](https://www.itl.nist.gov/div898/handbook/pmd/section4/pmd432.htm)，正则化和协方差收缩的通用说明见 [Ridge 文档](https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification)与[协方差收缩文档](https://scikit-learn.org/stable/modules/covariance.html#shrunk-covariance)。本仓库使用 NumPy 实现，不新增 scikit-learn 依赖。

## 成对实验

沿用上一轮七个真实执行条件：结构正确低/高噪声、仅偏差、增益、二次非线性、通道相关噪声、组合扰动。预算为 8/20/40/160，五批独立合成人群、每批两个过程重复，每场景 24 人×五策略×12 次二元反馈。新增模型共 280 个场景；旧版 simple、oracle、nominal 共 420 个场景全部重放。700 个场景合计 1,008,000 次反馈试验；执行校准次数是每场景共享的额外成本，不从每人的 12 次预算扣除。

使用与上一版逐值相同的嵌套校准观测、公开设置、人群、过程种子和诊断流。配置和拟合设置分别记录 SHA-256 指纹，校准记录按原顺序编码为 little-endian float64 后计算指纹。比较脚本重算拟合参数，并检查新旧记录逐值相等、预算前缀一致、全部场景/策略存在、诊断网格完整、固定策略真实轨迹不变。重放检查全部原汇总字段，不能只比较主指标。

执行分布另用 21 个命令点、每点 4096 个样本诊断；范围内/外相对中央 20%–80% 校准命令区间定义。这些诊断不进入拟合或选点。报告强度均值误差、标准差误差、Wasserstein-1 距离、名义 90% 预测区间覆盖和协议超阈概率误差。两个模型使用相同诊断根种子；加速度/jerk 共用基础创新，时长的抽样顺序可能因实现而不同。这保留有效的成对比较，但不意味着每个辅助通道逐样本对应。

区间先平均同一人群批次的两个过程重复，再以五个批次计算 t 区间。没有增加独立人群数，七种压力条件也不是七批额外人群。区间未作多重比较校正；跨零不是等效证明，显著的执行预测改善也不自动推出最终边界误差改善。

## 仍然没有解决的内容

- 执行参数点估计的不确定性没有传播到预测或选点；小预算时可有过拟合和预测区间覆盖不足。执行分布的 90% 区间与响应 B_tau 的 95% 后验区间含义不同。
- 已知条件 jerk/时长均值、异方差形状、裁剪边界和强度映射均未学习；排除触边记录不是一般删失似然。协方差估计用未约束投影，模型结构违反单调性或均值裁剪在校准区间明显生效时，不具备一般校正保证。
- 当前七种压力条件的均值/协方差都在扩展模型族内；这里检验的是能否从有限数据恢复更合适的结构。不能外推到高阶非线性、滞后、在线漂移、跨次自相关、重尾或未知条件均值。
- 响应模型、12 次反馈预算和选点启发式均未重设计；精度、不可接受反馈和校准成本仍需分别衡量。协议超阈率不是事故概率，没有实车安全保证。
- 全部人群和执行均为合成数据，本轮没有实车或真人验证。

## 运行新模型

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py --execution-estimator quadratic_covariance
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py --execution-estimator quadratic_covariance
python long_horizon_audit/scripts/run_flexible_execution_audit.py --workers 8
python long_horizon_audit/scripts/compare_flexible_execution.py
```

新入口要求 `--execution-belief calibrated`（原默认值）。显式选择后写入 `outputs_flexible_execution/` 和 `_poc/`，另导出 `continuous_execution_fit.csv`。若同时选择 `--surrogate legacy_kernel`，目录改为 `outputs_flexible_execution_legacy_kernel/` 或其 `_poc/` 版本，避免覆盖 Bayesian 示例。直接运行不带新参数的历史入口仍使用 simple；这避免无意覆盖已发布快照，不表示简单模型经过本轮验证仍普遍合适。新审计可用 `--suite flexible|replay` 和 `--profile` 分组运行；全量比较要求全部七组和全部旧版重放完成。完整结果见[结果报告](2026-11-04-flexible-execution-results.md)。
