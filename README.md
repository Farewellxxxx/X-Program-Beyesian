# Passenger motion-boundary calibration — synthetic simulation

本仓库保存乘客运动可接受边界研究中可复现的仿真代码、测试、合成结果及研究设计。

**当前版本：2026-11-04 单调贝叶斯二元反馈模型。全部结果来自合成乘客，真人研究尚未开展。**

当前代理模型使用 Bernoulli likelihood、正斜率 logistic 曲线和显式先验，通过二维数值积分更新后验。它输出接受概率、概率的后验标准差，以及 B_tau 的后验中位数和 95% 可信区间。旧 kernel 启发式模型保留为 `legacy_kernel`，上一轮修正的边界定义和误差指标继续使用。

五过程种子下，UncertainInputBO 的平均绝对边界误差在低/高执行噪声下分别从 **0.1444 → 0.1233**、**0.1460 → 0.1327**，不可接受次数从 **4.15 → 3.88**、**3.81 → 3.65**（每人 12 次）。误差改善的配对区间均跨零；Grid 和高反馈噪声场景出现退步，不能声称新模型全面更优。

- [模型、完整前后比较与限制](docs/2026-11-04-monotone-bayes-results.md)
- [验证记录](docs/2026-11-04-monotone-bayes-verification.md)
- [运行入口与数据字段](comfort_boundary_bo_research_package/simulation/README.md)
- [历史：边界定义修正](docs/2026-11-04-boundary-correction-results.md)

![Five-seed surrogate comparison](results/monotone_bayes_20261104/surrogate_before_after.png)

## 安装与复现

验证环境 Python 3.12.7；建议使用独立虚拟环境。

```bash
python -m pip install -r requirements-simulation.txt
python -m pytest -q
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py
python long_horizon_audit/scripts/run_multiseed_simulation_audit.py --surrogate monotone_bayes --output-dir long_horizon_audit/derived/simulation_audit_bayesian_20261104 --seeds 5
python long_horizon_audit/scripts/run_multiseed_simulation_audit.py --surrogate legacy_kernel --output-dir long_horizon_audit/derived/simulation_audit_legacy_comparison_20261104 --seeds 5
python comfort_boundary_bo_research_package/simulation/compare_surrogates.py
```

前两个入口默认重建 Bayesian CSV/PNG；审计包含五种子和六个敏感性场景。比较脚本验证旧模型和固定策略轨迹，生成配对比较、相同反馈重放、积分精度、先验敏感性及覆盖率诊断。已提交全部结果，可直接查看。

旧结果保存在 `outputs_continuous/`、`outputs_continuous_poc/` 和 `simulation_audit_corrected_20261104/`。重跑历史模型必须显式添加 `--surrogate legacy_kernel`；历史边界修正比较可直接运行：

```bash
python comfort_boundary_bo_research_package/simulation/compare_boundary_results.py --baseline-root results/baseline_before_boundary_fix
```

## 目录与研究范围

| 路径 | 内容 |
|---|---|
| `comfort_boundary_bo_research_package/simulation/` | 新旧模型、仿真入口和结果 |
| `long_horizon_audit/scripts/` | 多种子仿真及可选历史数据审计 |
| `long_horizon_audit/tests/` | 数学、回归、模型和比较测试 |
| `long_horizon_audit/derived/simulation_audit_bayesian_20261104/` | 新模型五种子和敏感性结果 |
| `long_horizon_audit/derived/simulation_audit_legacy_comparison_20261104/` | 旧模型重跑，新增 Brier 指标 |
| `results/monotone_bayes_20261104/` | 新旧配对比较、数值验证、覆盖率和图表 |
| `results/boundary_correction_20261104/` | 上一轮边界指标修正的历史比较 |
| `docs/` | 当前及历史报告、研究设计、执行计划 |

代理模型现在有显式概率后验；选点仍是 BO-inspired heuristic，未实现信息增益最优化或 SafeOpt 保证。后续优先处理生成器真实执行分布与算法认知分离、独立人群种子、反馈 lapse/时间效应建模和选点分数校准。12 次反馈下区间较宽，先验影响可见，不能用这些合成结果证明实车安全或真人有效性。

历史原始 VR/实车数据、参与者信息、第三方论文、内部论文草稿、旧 PPT、环境缓存和备份均未发布。数据审计测试自行构造虚拟 ZIP/XLSX，不依赖实车资源。完整本地研究文件夹另有旧 Presentations 运行时测试，该演示系统未收录，本仓库测试范围见 `pytest.ini`。
