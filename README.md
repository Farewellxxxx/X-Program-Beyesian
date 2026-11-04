# Passenger motion-boundary calibration — synthetic simulation

本仓库保存乘客运动可接受边界研究中可复现的仿真代码、测试、合成结果及研究设计。

**当前版本：2026-11-04 执行模型复杂度选择与参数不确定性传播。全部结果来自合成乘客，真人研究尚未开展。**

当前接受模型使用单调 Bernoulli–logistic 后验，输出 B_tau 中位数和可信区间。新增 `adaptive_posterior` 对仅偏差、线性增益、二次曲率三种单调执行模型进行贝叶斯模型平均，并传播均值参数和完整噪声协方差的不确定性。执行生成器与算法持有的分布现在是独立对象：原 simple 模型由 40 条额外合成执行记录拟合偏差和公共噪声；前版 `quadratic_covariance` 从同样的可观测记录估计偏差、增益、二次曲率和三通道残差协方差；`oracle` 明确表示已知真实参数的对照，`nominal` 表示固定假设。策略只能看到可观测历史，不能读取乘客真值或生成参数。

人群、过程、执行校准分别使用显式种子。过程子流由种子、用途、参与者和策略标识共同派生，避免旧加法偏移的种子碰撞。新实验包含五批独立人群、每批两个过程种子，以及同过程的固定人群对照；按人群批次汇总区间，不把重复试验当成独立人群。另有未知执行偏差/低估噪声场景和上一版完整复现检查。

- [本次小预算过拟合、覆盖率与前后结果](docs/2026-11-04-adaptive-execution-results.md)
- [本次模型方法与复现说明](docs/2026-11-04-adaptive-execution-method.md)
- [本次验证记录](docs/2026-11-04-adaptive-execution-verification.md)
- [历史：增益、非线性和相关噪声估计](docs/2026-11-04-flexible-execution-results.md)
- [历史：执行模型失配与校准预算](docs/2026-11-04-execution-robustness-results.md)
- [历史：执行分布分离与独立人群](docs/2026-11-04-execution-population-results.md)
- [历史：单调贝叶斯模型替换](docs/2026-11-04-monotone-bayes-results.md)
- [运行入口与数据字段](comfort_boundary_bo_research_package/simulation/README.md)
- [历史：边界定义修正](docs/2026-11-04-boundary-correction-results.md)

新审计沿用七种压力条件和 8、20、40、160 次校准，运行 280 个新场景及 280 个前版重放场景。五批人群、每批两次过程重复，新旧使用逐值相同的校准观测和成对随机流。六种执行预测方式拆分复杂度选择与参数传播；独立未来样本评估 90% 区间覆盖率，同时报告宽度和适当区间评分，防止把单纯放宽区间当作改进。另有固定的抽样数与先验敏感性检查。

![Independent future predictive coverage](results/adaptive_execution_20261104/extrapolation_coverage.png)

## 安装与复现

验证环境 Python 3.12.7；建议使用独立虚拟环境。

```bash
python -m pip install -r requirements-simulation.txt
python -m pytest -q
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py --execution-estimator adaptive_posterior
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py --execution-estimator adaptive_posterior
python long_horizon_audit/scripts/run_adaptive_execution_audit.py --workers 8
python long_horizon_audit/scripts/compare_adaptive_execution.py
```

上面两个示例显式选择新模型，写入 `outputs_adaptive_execution/` 和 `outputs_adaptive_execution_poc/`，并导出拟合系数、完整协方差及诊断。省略 `--execution-estimator adaptive_posterior` 时仍运行历史 simple 默认值，写入原来的 `outputs_execution_separated/` 和 `_poc/`，以保留可复现性。同一固定人群用于单次运行示例，可用 `--population-seed` 指定另一个种子。人群审计默认运行 85 个场景；可分别用 `--suite historical|fixed_control|population|stress` 运行，四组完成后再执行比较。每组保存参数清单、个体/策略汇总、人群参数和校准观测。校准的 40 次额外合成执行不含乘客反馈，与每人 12 次反馈预算分开计算。

最新审计共 560 个反馈场景，可用 `--suite adaptive|replay|sensitivity` 分组运行；前两组支持 `--profile matched_low|matched_high|biased_high|gain_high|nonlinear_high|correlated_high|combined_high`。全部完成后比较。`--workers` 可设 1–8，建议各 worker 的 `OPENBLAS_NUM_THREADS`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS` 为 1。新旧观测、模型设置、后验抽样、实际过程流和历史重放均校验。旧执行扩展审计仍使用 `run_flexible_execution_audit.py` 和 `compare_flexible_execution.py`；更早失配审计仍使用 `run_execution_robustness_audit.py` 和 `compare_execution_robustness.py`。

旧结果保留。历史 kernel 重跑须使用 `--surrogate legacy_kernel --execution-belief oracle --process-rng-mode legacy`；上一版 Bayesian 重跑使用 `--surrogate monotone_bayes --execution-belief oracle --process-rng-mode legacy`。历史审计入口 `run_multiseed_simulation_audit.py` 默认仍为 oracle/固定人群/legacy 子流。旧比较脚本继续读取旧快照：

```bash
python comfort_boundary_bo_research_package/simulation/compare_boundary_results.py --baseline-root results/baseline_before_boundary_fix
python comfort_boundary_bo_research_package/simulation/compare_surrogates.py
```

## 目录与研究范围

| 路径 | 内容 |
|---|---|
| `comfort_boundary_bo_research_package/simulation/` | 新旧模型、仿真入口和结果 |
| `long_horizon_audit/scripts/` | 多种子仿真及可选历史数据审计 |
| `long_horizon_audit/tests/` | 数学、回归、模型和比较测试 |
| `long_horizon_audit/derived/adaptive_execution_20261104/` | 新后验模型、六种执行诊断、敏感性与前版重放 |
| `results/adaptive_execution_20261104/` | 批次配对比较、模型权重与覆盖率/宽度/评分图 |
| `long_horizon_audit/derived/execution_population_20261104/` | 85 场景的配置、校准、人群及指标 |
| `results/execution_population_20261104/` | 上一轮人群区间、配对影响和图表 |
| `long_horizon_audit/derived/execution_robustness_20261104/` | 新失配/预算审计及历史重放的配置、观测、指标和独立执行诊断 |
| `results/execution_robustness_20261104/` | 历史：简单校准器的预算、失配和校准顺序对照 |
| `long_horizon_audit/derived/flexible_execution_20261104/` | 新模型 280 场景完整记录、拟合与诊断，及旧版 420 场景重放汇总 |
| `results/flexible_execution_20261104/` | 历史：固定二次点估计与简单校准器的配对比较及图表 |
| `long_horizon_audit/derived/simulation_audit_bayesian_20261104/` | 新模型五种子和敏感性结果 |
| `long_horizon_audit/derived/simulation_audit_legacy_comparison_20261104/` | 旧模型重跑，新增 Brier 指标 |
| `results/monotone_bayes_20261104/` | 新旧配对比较、数值验证、覆盖率和图表 |
| `results/boundary_correction_20261104/` | 上一轮边界指标修正的历史比较 |
| `docs/` | 当前及历史报告、研究设计、执行计划 |

选点仍是 BO-inspired heuristic，未实现信息增益最优化或 SafeOpt 保证。新估计器在三种单调均值之间做模型平均并传播执行参数不确定性，但仍假定已知条件 jerk/时长均值、异方差形状和强度映射；尚未在线更新执行后验。相关性指同一次执行的通道相关性，不包括跨次时间自相关。当前压力条件位于扩展模型族内，不能代表一般高阶非线性、滞后、漂移或重尾失配。五批合成人群的区间仍有限，不能证明实车安全或真人有效性。

历史原始 VR/实车数据、参与者信息、第三方论文、内部论文草稿、旧 PPT、环境缓存和备份均未发布。数据审计测试自行构造虚拟 ZIP/XLSX，不依赖实车资源。完整本地研究文件夹另有旧 Presentations 运行时测试，该演示系统未收录，本仓库测试范围见 `pytest.ini`。
