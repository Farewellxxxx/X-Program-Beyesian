# Passenger motion-boundary calibration — synthetic simulation

本仓库保存乘客运动可接受边界研究中可复现的仿真代码、测试、合成结果及研究设计。

**当前版本：2026-11-04 执行模型失配与校准预算验证。全部结果来自合成乘客，真人研究尚未开展。**

当前接受模型使用单调 Bernoulli–logistic 后验，输出 B_tau 中位数和可信区间。执行生成器与算法持有的分布现在是独立对象：默认算法仅由 40 条额外合成执行记录拟合偏差和噪声；`oracle` 明确表示已知真实参数的对照，`nominal` 表示固定假设。策略只能看到可观测历史，不能读取乘客真值或生成参数。

人群、过程、执行校准分别使用显式种子。过程子流由种子、用途、参与者和策略标识共同派生，避免旧加法偏移的种子碰撞。新实验包含五批独立人群、每批两个过程种子，以及同过程的固定人群对照；按人群批次汇总区间，不把重复试验当成独立人群。另有未知执行偏差/低估噪声场景和上一版完整复现检查。

- [本次失配、预算比较与结论适用范围](docs/2026-11-04-execution-robustness-results.md)
- [本次验证记录](docs/2026-11-04-execution-robustness-verification.md)
- [历史：执行分布分离与独立人群](docs/2026-11-04-execution-population-results.md)
- [历史：单调贝叶斯模型替换](docs/2026-11-04-monotone-bayes-results.md)
- [运行入口与数据字段](comfort_boundary_bo_research_package/simulation/README.md)
- [历史：边界定义修正](docs/2026-11-04-boundary-correction-results.md)

新增审计在固定校准器下检验增益、非线性、相关噪声及组合失配，并比较 8、20、40、160 次校准。五批人群、每批两次过程重复，使用嵌套的校准观测和成对随机流；完整真分布 oracle 明确包含结构失配。独立执行预测检查覆盖校准范围内和范围外命令。旧默认入口和历史结果保持原样，结果解释以本次报告为准。

![Execution prediction diagnostics](results/execution_robustness_20261104/execution_prediction_diagnostics.png)

## 安装与复现

验证环境 Python 3.12.7；建议使用独立虚拟环境。

```bash
python -m pip install -r requirements-simulation.txt
python -m pytest -q
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py
python long_horizon_audit/scripts/run_execution_population_audit.py
python long_horizon_audit/scripts/compare_execution_population.py
python long_horizon_audit/scripts/run_execution_robustness_audit.py --workers 8
python long_horizon_audit/scripts/compare_execution_robustness.py
```

前两个入口默认写入 `outputs_execution_separated/` 和 `outputs_execution_separated_poc/`；同一固定人群用于单次运行示例，可用 `--population-seed` 指定另一个种子。人群审计默认运行 85 个场景；可分别用 `--suite historical|fixed_control|population|stress` 运行，四组完成后再执行比较。每组保存参数清单、个体/策略汇总、人群参数和校准观测。校准的 40 次额外合成执行不含乘客反馈，与每人 12 次反馈预算分开计算。

最新稳健性审计运行 420 个新场景和 55 个历史重放场景。可用 `--profile matched_low|matched_high|biased_high|gain_high|nonlinear_high|correlated_high|combined_high|replay` 分组运行，全部完成后比较。`--workers` 可设 1–8；建议各 worker 的 `OPENBLAS_NUM_THREADS`、`OMP_NUM_THREADS`、`MKL_NUM_THREADS` 为 1。并行调度不参与随机种子派生。新预算使用相同观测序列的前缀；与上一轮 40 次排序网格校准的差异单独报告。

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
| `long_horizon_audit/derived/execution_population_20261104/` | 85 场景的配置、校准、人群及指标 |
| `results/execution_population_20261104/` | 上一轮人群区间、配对影响和图表 |
| `long_horizon_audit/derived/execution_robustness_20261104/` | 新失配/预算审计及历史重放的配置、观测、指标和独立执行诊断 |
| `results/execution_robustness_20261104/` | 最新预算、失配和校准顺序的配对对照、执行诊断及图表 |
| `long_horizon_audit/derived/simulation_audit_bayesian_20261104/` | 新模型五种子和敏感性结果 |
| `long_horizon_audit/derived/simulation_audit_legacy_comparison_20261104/` | 旧模型重跑，新增 Brier 指标 |
| `results/monotone_bayes_20261104/` | 新旧配对比较、数值验证、覆盖率和图表 |
| `results/boundary_correction_20261104/` | 上一轮边界指标修正的历史比较 |
| `docs/` | 当前及历史报告、研究设计、执行计划 |

选点仍是 BO-inspired heuristic，未实现信息增益最优化或 SafeOpt 保证。执行估计只拟合偏差和公共噪声尺度；新实验故意让生成器偏离该结构，没有同时升级校准器。未传播执行参数估计不确定性，也未在线更新。扰动系数是预先固定的合成压力条件，未覆盖所有执行失配。五批合成人群的区间仍有限，不能证明实车安全或真人有效性。

历史原始 VR/实车数据、参与者信息、第三方论文、内部论文草稿、旧 PPT、环境缓存和备份均未发布。数据审计测试自行构造虚拟 ZIP/XLSX，不依赖实车资源。完整本地研究文件夹另有旧 Presentations 运行时测试，该演示系统未收录，本仓库测试范围见 `pytest.ini`。
