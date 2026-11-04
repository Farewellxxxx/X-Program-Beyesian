# Offline Simulation Plan

## Purpose

离线仿真的目的不是替代真人实验，而是在正式 user study 前回答：

- continuous target command 在不同 execution uncertainty 下是否仍有可用信息？
- uncertain-input BO 是否比 naive continuous BO 更稳健？
- BO 是否比 random/grid 或 staircase 更少造成不可接受 trial？
- target command 与 realized motion 的偏差会不会让边界估计失效？
- safety-aware acquisition 是否能减少 protocol deviations？
- 时间变量如果被弱化，会不会严重偏误？

Simulation 只能作为 pre-study design diagnostic，不证明真人实验有效。

## Simulation Components

### 1. Virtual Passenger

每个乘客有：

```text
b_i: true boundary over realized m(z)
s_i: sensitivity
eta_i: feedback noise
r_i: risk tolerance
```

反馈：

```text
P_i(acceptable_t = 1)
  = sigmoid((b_i - m(z_t)) / s_i) * (1 - eta_i) + 0.5 * eta_i
```

### 2. Continuous Target Command

算法选择 continuous target command：

```text
x_t in [x_min, x_max]
```

第一版可把 `x_t` 解释为 target acceleration/deceleration 或 target motion intensity。

### 3. Vehicle Execution Model

实际产生 motion features：

```text
z_t ~ P(z | x_t)
```

其中：

```text
z_t = [peak_accel, peak_jerk, rms_jerk, duration, speed_delta]
```

第一版可用合成分布；更好的是用 execution calibration 或学姐/真实车辆数据估计。仿真必须记录 target-vs-realized diagnostic。

### 4. Effective Motion Intensity

推荐第一版：

```text
m(z_t) = a_t + lambda_j * max(0, j_t - j0)
```

敏感性分析：

```text
m(z_t) = a_t
       + lambda_j * max(0, j_t - j0)
       + lambda_d * max(0, duration_t - d0)
```

## Algorithms to Compare

### Uncertain-Input BO

- decision space: continuous target command `x`；
- model input: realized measured features `z`；
- acquisition: Monte Carlo expectation over `P(z | x)`；
- output: boundary estimate over `m(z)`。

This is an uncertain-input BO-inspired approximation, not exact uGP-UCB.

### Naive Continuous BO

- decision space: continuous target command `x`；
- assumes `z = E[z | x]`；
- ignores execution uncertainty in acquisition。

This baseline directly tests why accounting for uncertain inputs matters.

### Random/Grid Continuous Sampling

- fixed randomized or grid command sequence；
- useful sanity baseline；
- no adaptation or weak adaptation。

### Staircase Baseline

- acceptable -> increase command；
- unacceptable -> decrease command；
- optional step-size shrink after reversals。

### Optional Legacy Level/Template Baseline

Only if needed for discussion. It should be described as fallback/legacy, not as the main method.

## Evaluation Metrics

### Accuracy

```text
final_boundary_absolute_error = |B_hat_i - B_i|
trials_to_near_boundary
posterior_uncertainty_width
recommendation_stability
```

For real user studies, boundary error is only available if there is an independent reference boundary. In simulation it is diagnostic because the latent true boundary is known by construction.

### User Cost

```text
number_of_unacceptable_trials
cumulative_discomfort
maximum_discomfort
maximum_overshoot_above_true_boundary
mean_overshoot
number_of_high_risk_probes
```

### Safety and Execution Diagnostics

```text
protocol_deviations
safety_violation_probability
target_vs_realized_error
realized_intensity_bias
execution_noise_distribution
max_realized_overshoot
```

### Robustness

```text
sensitivity_to_feedback_noise
sensitivity_to_execution_noise
sensitivity_to_tau
sensitivity_to_lambda_j
sensitivity_to_calibration_bias
sensitivity_to_nonstationary_P_z_given_x
```

## Simulation Experiments

### Experiment 1: Baseline Comparison

Compare:

- uncertain-input BO；
- naive continuous BO；
- random continuous sampling；
- grid continuous sampling；
- staircase。

Budgets:

```text
8, 10, 12, 15 trials
```

### Experiment 2: Vehicle Execution Noise

Vary `P(z | x)` noise:

```text
low execution noise
medium execution noise
high execution noise
```

Question: uncertain-input BO 是否比 naive BO 更稳定？

### Experiment 3: Target-vs-Realized Diagnostics

Report:

```text
target command vs realized intensity
target command vs peak acceleration
realization error distribution
algorithm-wise realized overshoot
```

Question: command 的可执行性是否支持 user study？

### Experiment 4: Safety-Aware Acquisition

Compare:

- boundary-seeking without risk penalty；
- boundary-seeking with discomfort penalty；
- safety probability penalty；
- hard safety constraints。

Question: 风险惩罚是否能减少 unacceptable trials 和 protocol deviations，同时保持边界精度？

### Experiment 5: Time/Cumulative Effects

Add carryover:

```text
P(acceptable_t) depends on cumulative_discomfort_{t-1}
```

Question: 如果主模型忽略时间，误差有多大？

## Expected Outputs

建议输出：

```text
continuous_trials.csv
continuous_participant_summary.csv
continuous_algorithm_summary.csv
continuous_target_realized_diagnostics.csv
continuous_safety_protocol_summary.csv
continuous_sensitivity_summary.csv
continuous_boundary_error_by_algorithm.png
continuous_unacceptable_trials_by_algorithm.png
continuous_cumulative_discomfort_by_algorithm.png
continuous_accuracy_cost_tradeoff.png
continuous_target_vs_realized_scatter.png
continuous_realization_error_by_algorithm.png
continuous_overshoot_by_algorithm.png
continuous_protocol_deviations_by_algorithm.png
continuous_example_participant_trajectory.png
```

## Current Scripts

主脚本：

```text
comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py
```

快速 POC：

```text
comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py
```

旧的 level/template 代码不再作为 active main simulation。若未来保留，应放在 legacy/fallback context，并明确它只是 backup design route。
