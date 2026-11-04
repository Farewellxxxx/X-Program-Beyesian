# 分情境分析（模拟）

数据划分：held-out；随机种子：271828。

以下区间为各情境内按独立乘客重采样的配对百分位 bootstrap 95% 区间；同一乘客的逐试次记录没有当作独立样本。不同情境不混池。
主比较：bayes_risk 对 ucb_tvcg、staircase；ucb_tau 仅次要敏感性分析；bayes_point 为输入不确定性消融。

## 不利或混合证据（先报告）

差值均为 bayes_risk 减去比较方法。成本/误差/暴露等负值更好；成功率正值更好。覆盖率需结合名义95%与区间宽度评估，较高也可能表示保守。区间跨零不支持明确方向；区间没有做多重比较校正。
- lapse_logistic__precise / bayes_point (ablation), primary_cost: Δ=-0.3125, 95% [-8.0312, 7.3766]（方向不确定）。
- lapse_logistic__precise / bayes_point (ablation), primary_observed: Δ=0.1875, 95% [0.0000, 0.3750]（方向不确定）。
- lapse_logistic__precise / bayes_point (ablation), final_absolute_error: Δ=-0.0017, 95% [-0.0371, 0.0338]（方向不确定）。
- lapse_logistic__precise / bayes_point (ablation), unacceptable_rate: Δ=0.0036, 95% [-0.0036, 0.0109]（不利点估计）。
- lapse_logistic__precise / staircase (primary), primary_cost: Δ=0.4688, 95% [-7.5320, 8.0625]（不利点估计）。
- lapse_logistic__precise / staircase (primary), primary_observed: Δ=0.1250, 95% [-0.0312, 0.2812]（方向不确定）。
- lapse_logistic__precise / staircase (primary), final_absolute_error: Δ=0.0005, 95% [-0.0280, 0.0308]（不利点估计）。
- lapse_logistic__precise / staircase (primary), unacceptable_rate: Δ=-0.0026, 95% [-0.0141, 0.0115]（方向不确定）。
- lapse_logistic__variable / bayes_point (ablation), primary_cost: Δ=0.9688, 95% [-6.8438, 8.5000]（不利点估计）。
- lapse_logistic__variable / bayes_point (ablation), primary_observed: Δ=-0.0938, 95% [-0.3125, 0.1250]（不利点估计）。
- lapse_logistic__variable / bayes_point (ablation), final_absolute_error: Δ=0.0068, 95% [-0.0251, 0.0406]（不利点估计）。
- lapse_logistic__variable / bayes_point (ablation), unacceptable_rate: Δ=-0.0089, 95% [-0.0250, 0.0052]（方向不确定）。
- lapse_logistic__variable / staircase (primary), primary_cost: Δ=-5.1250, 95% [-13.4727, 3.4688]（方向不确定）。
- lapse_logistic__variable / staircase (primary), primary_observed: Δ=-0.0312, 95% [-0.2500, 0.1875]（不利点估计）。
- lapse_logistic__variable / staircase (primary), final_absolute_error: Δ=-0.0177, 95% [-0.0501, 0.0151]（方向不确定）。
- lapse_logistic__variable / staircase (primary), unacceptable_rate: Δ=-0.0104, 95% [-0.0260, 0.0052]（方向不确定）。
- lapse_logistic__variable / ucb_tau (secondary), unacceptable_rate: Δ=-0.0589, 95% [-0.1235, 0.0006]（方向不确定）。
- logistic__precise / bayes_point (ablation), primary_cost: Δ=-7.9062, 95% [-16.1250, 0.4070]（方向不确定）。
- logistic__precise / bayes_point (ablation), primary_observed: Δ=0.0625, 95% [-0.0938, 0.2188]（方向不确定）。
- logistic__precise / bayes_point (ablation), final_absolute_error: Δ=-0.0167, 95% [-0.0422, 0.0087]（方向不确定）。
- logistic__precise / bayes_point (ablation), unacceptable_rate: Δ=0.0031, 95% [-0.0052, 0.0115]（不利点估计）。
- logistic__precise / staircase (primary), primary_cost: Δ=-3.0000, 95% [-10.9086, 4.7188]（方向不确定）。
- logistic__precise / staircase (primary), primary_observed: Δ=0.0312, 95% [-0.0625, 0.1562]（方向不确定）。
- logistic__precise / staircase (primary), final_absolute_error: Δ=-0.0055, 95% [-0.0257, 0.0149]（方向不确定）。
- logistic__precise / staircase (primary), unacceptable_rate: Δ=-0.0073, 95% [-0.0193, 0.0047]（方向不确定）。
- logistic__variable / bayes_point (ablation), primary_cost: Δ=-4.3750, 95% [-10.1875, 1.0945]（方向不确定）。
- logistic__variable / bayes_point (ablation), primary_observed: Δ=0.0938, 95% [0.0000, 0.2188]（方向不确定）。
- logistic__variable / bayes_point (ablation), final_absolute_error: Δ=-0.0154, 95% [-0.0369, 0.0039]（方向不确定）。
- logistic__variable / bayes_point (ablation), unacceptable_rate: Δ=-0.0010, 95% [-0.0130, 0.0099]（方向不确定）。
- logistic__variable / staircase (primary), primary_cost: Δ=-0.3438, 95% [-6.8133, 6.0312]（方向不确定）。
- logistic__variable / staircase (primary), primary_observed: Δ=0.0312, 95% [0.0000, 0.0938]（方向不确定）。
- logistic__variable / staircase (primary), final_absolute_error: Δ=-0.0099, 95% [-0.0271, 0.0045]（方向不确定）。
- logistic__variable / staircase (primary), unacceptable_rate: Δ=-0.0057, 95% [-0.0208, 0.0094]（方向不确定）。
- probit__precise / bayes_point (ablation), primary_cost: Δ=1.0625, 95% [-2.1250, 4.5000]（不利点估计）。
- probit__precise / bayes_point (ablation), primary_observed: Δ=0.0000, 95% [0.0000, 0.0000]（方向不确定）。
- probit__precise / bayes_point (ablation), final_absolute_error: Δ=0.0025, 95% [-0.0116, 0.0169]（不利点估计）。
- probit__precise / bayes_point (ablation), unacceptable_rate: Δ=0.0000, 95% [-0.0073, 0.0062]（方向不确定）。
- probit__precise / staircase (primary), primary_cost: Δ=-1.1250, 95% [-5.2500, 2.8445]（方向不确定）。
- probit__precise / staircase (primary), primary_observed: Δ=0.0000, 95% [0.0000, 0.0000]（方向不确定）。
- probit__precise / staircase (primary), final_absolute_error: Δ=-0.0010, 95% [-0.0133, 0.0123]（方向不确定）。
- probit__precise / staircase (primary), unacceptable_rate: Δ=-0.0010, 95% [-0.0115, 0.0094]（方向不确定）。
- probit__variable / bayes_point (ablation), primary_cost: Δ=-1.7188, 95% [-6.5945, 3.1258]（方向不确定）。
- probit__variable / bayes_point (ablation), primary_observed: Δ=0.0000, 95% [0.0000, 0.0000]（方向不确定）。
- probit__variable / bayes_point (ablation), final_absolute_error: Δ=-0.0088, 95% [-0.0242, 0.0059]（方向不确定）。
- probit__variable / staircase (primary), primary_cost: Δ=0.6562, 95% [-3.7188, 5.2508]（不利点估计）。
- probit__variable / staircase (primary), primary_observed: Δ=0.0000, 95% [0.0000, 0.0000]（方向不确定）。
- probit__variable / staircase (primary), final_absolute_error: Δ=-0.0010, 95% [-0.0138, 0.0127]（方向不确定）。
- probit__variable / staircase (primary), unacceptable_rate: Δ=-0.0083, 95% [-0.0208, 0.0057]（方向不确定）。

## 全部情境摘要

| 情境 | 方法 | n | 主成功率 | 主成本 | 最终MAE | 不可接受比例 | 覆盖率 | 区间宽度 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| lapse_logistic__precise | bayes_point | 32 | 0.719 | 33.53 | 0.084 | 0.272 | 0.938 | 0.446 |
| lapse_logistic__precise | bayes_risk | 32 | 0.906 | 33.22 | 0.082 | 0.276 | 0.938 | 0.440 |
| lapse_logistic__precise | staircase | 32 | 0.781 | 32.75 | 0.082 | 0.279 | 0.875 | 0.417 |
| lapse_logistic__precise | ucb_tau | 32 | 0.406 | 46.41 | 0.193 | 0.366 | 0.812 | 0.750 |
| lapse_logistic__precise | ucb_tvcg | 32 | 0.406 | 51.25 | 0.218 | 0.364 | 0.781 | 0.730 |
| lapse_logistic__variable | bayes_point | 32 | 0.812 | 34.62 | 0.074 | 0.285 | 0.969 | 0.414 |
| lapse_logistic__variable | bayes_risk | 32 | 0.719 | 35.59 | 0.080 | 0.277 | 1.000 | 0.461 |
| lapse_logistic__variable | staircase | 32 | 0.750 | 40.72 | 0.098 | 0.287 | 0.812 | 0.459 |
| lapse_logistic__variable | ucb_tau | 32 | 0.344 | 53.88 | 0.167 | 0.335 | 0.844 | 0.737 |
| lapse_logistic__variable | ucb_tvcg | 32 | 0.406 | 51.81 | 0.192 | 0.345 | 0.844 | 0.714 |
| logistic__precise | bayes_point | 32 | 0.875 | 31.59 | 0.076 | 0.283 | 0.906 | 0.374 |
| logistic__precise | bayes_risk | 32 | 0.938 | 23.69 | 0.060 | 0.286 | 1.000 | 0.347 |
| logistic__precise | staircase | 32 | 0.906 | 26.69 | 0.065 | 0.293 | 1.000 | 0.376 |
| logistic__precise | ucb_tau | 32 | 0.656 | 39.84 | 0.104 | 0.407 | 0.844 | 0.530 |
| logistic__precise | ucb_tvcg | 32 | 0.625 | 40.12 | 0.116 | 0.418 | 0.844 | 0.513 |
| logistic__variable | bayes_point | 32 | 0.906 | 25.50 | 0.055 | 0.297 | 0.906 | 0.348 |
| logistic__variable | bayes_risk | 32 | 1.000 | 21.12 | 0.040 | 0.296 | 1.000 | 0.346 |
| logistic__variable | staircase | 32 | 0.969 | 21.47 | 0.050 | 0.302 | 1.000 | 0.380 |
| logistic__variable | ucb_tau | 32 | 0.656 | 39.69 | 0.103 | 0.405 | 0.969 | 0.496 |
| logistic__variable | ucb_tvcg | 32 | 0.812 | 33.25 | 0.094 | 0.407 | 0.938 | 0.532 |
| probit__precise | bayes_point | 32 | 1.000 | 12.88 | 0.030 | 0.289 | 0.969 | 0.254 |
| probit__precise | bayes_risk | 32 | 1.000 | 13.94 | 0.033 | 0.289 | 1.000 | 0.240 |
| probit__precise | staircase | 32 | 1.000 | 15.06 | 0.034 | 0.290 | 1.000 | 0.285 |
| probit__precise | ucb_tau | 32 | 0.875 | 29.66 | 0.064 | 0.443 | 0.938 | 0.385 |
| probit__precise | ucb_tvcg | 32 | 0.812 | 30.00 | 0.077 | 0.446 | 0.969 | 0.374 |
| probit__variable | bayes_point | 32 | 1.000 | 16.91 | 0.040 | 0.310 | 1.000 | 0.238 |
| probit__variable | bayes_risk | 32 | 1.000 | 15.19 | 0.031 | 0.293 | 1.000 | 0.268 |
| probit__variable | staircase | 32 | 1.000 | 14.53 | 0.032 | 0.301 | 1.000 | 0.231 |
| probit__variable | ucb_tau | 32 | 0.875 | 27.12 | 0.069 | 0.426 | 0.969 | 0.357 |
| probit__variable | ucb_tvcg | 32 | 0.875 | 29.69 | 0.077 | 0.434 | 0.938 | 0.387 |

主成本是预算限制成本：达标者取首次主事件试次，未达标者取预算；它不是成功者平均试次数，也不是预算外真实收敛时间的估计。主事件需要事后检查从该试次到预算末端始终达标，不能作为在线停止规则。
所有失败、域外边界和不具辨识支持的记录保留在汇总。检查 scenario_summary.csv 中 censored/out_of_domain/unidentifiable 列。区间宽度较窄不代表覆盖率更好；需联合解读。
完整效应及不确定性见 paired_effects.csv；逐试次描述性统计见 trajectories.csv。模拟试次不是实测耗时，亦不能证明人类比较优势。
