# 有限预算 v2 的复现与读表

本版本位于 `research/finite-budget-v2`。完整 v1 固定在标签 `baseline-decoupled-v1-20261105`；不要用本版本的配置覆盖 v1 输出。

## 定义与成本

目标是实际加速度下接受概率为 .70 的个体边界。主终点固定在第30次反馈，误差容限 .15 m/s²；“支持成功”还要求数值输出正常、已有接受和拒绝两种回答、估计落在实际观测强度范围内。全部参与者都在成功率分母中。仅当逐场景95% Wilson区间下限达到 .80，才记为达到预定目标。

开发32份基础 B/W 参数、六场景、十条策略轨迹、30次：57,600次反馈。正式128份参数、六场景、五策略、60次：230,400次反馈。正式是128个独立基础参数对、768个条件案例，不是768名独立参与者。另有23,040次合成执行校准，跨曲线族和策略共享，不能省略此成本。七项压力条件每项64份参数、三策略、60次：80,640次反馈，独立于主结果。

新模型使用241×41积分网格与7个执行积分节点；历史模型81×41保持不变。数值加密来自结果生成前的固定公共历史诊断。模拟种子与各阶段配置均保存，正式结果不会因观察到输赢而加样本或换种子。

## 两层比较

- `pipeline`：各采样器及其指定读出。新BO使用其后验容限窗口中心；阶梯使用受约束的Firth逻辑曲线拟合。
- `common`：每种采样器的自身历史都交给同一个新先验估计器。主读出 `new_precision`，后验中位数 `new_median` 为另存参照。这个估计器不影响阶梯或UCB的采样。
- `legacy_native`：原版BO方差选点加旧先验中位数，供同一新测试人群上的前后比较。
- `development_factorial`：仅开发集上的先验与读出拆解，不能作为未见测试结果。
- 原生UCB最大Q指令与阶梯反转均值在 `diagnostics.jsonl`；它们不是同一个实际边界估计目标，不混入主误差排名。

## 运行与验证

从仓库根目录运行，使用Python3.12和 `requirements-simulation.txt`。目标输出目录必须尚未存在。并行仅按原参与者ID分任务，`--workers 6` 不改变科学配置或随机流。

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
New-Item -ItemType Directory -Force tmp/local-runtime | Out-Null
$env:TMP=(Resolve-Path tmp/local-runtime).Path
$env:TEMP=$env:TMP
$fb='comfort_boundary_bo_research_package.simulation.finite_budget'
$art='results/finite_budget_calibration_20261105'
python -m pytest -q --basetemp tmp/local-runtime/pytest
python -m $fb run --config "$art/heldout_config.selected.json" --freeze "$art/heldout_freeze.json" --output outputs/finite-budget-heldout --workers 6
python -m $fb analyze --input outputs/finite-budget-heldout --output outputs/finite-budget-analysis
python scripts/verify_finite_budget_readouts_parallel.py --input outputs/finite-budget-heldout --output outputs/finite-budget-numerical-audit.json --workers 6
python scripts/verify_finite_budget_artifacts.py --input outputs/finite-budget-heldout --analysis outputs/finite-budget-analysis --output outputs/finite-budget-independent-audit.json
```

正式/压力入口会在任何人群抽样前核对冻结配置、源码、阶梯选择和数值证据。必须保持冻结科学源的原始字节；仓库 `.gitattributes` 保留原字节。若修改了算法，就应进行新的开发与冻结，不能把新实现冒充为本批次的复现。

压力复现对应使用 `stress_config.selected.json` 与 `stress_freeze.json`。开发重跑使用 `configs/finite_budget_development.json`，再调用 `select-staircase`；选型规则、六候选分数和开发清单哈希保存在 `staircase_selection.json`。`reread-priors` 只对开发历史换先验重新读出，不增加反馈，也不等于运行了相应先验的完整采样策略。

## 工件与统计解释

每个运行目录分开存放：隐藏真值 `participants.jsonl`，执行校准 `calibrations.jsonl`，公开试次 `observations.jsonl`，分预算读出 `checkpoints.jsonl`，原生诊断 `diagnostics.jsonl`，公共规则停止回放 `stops.jsonl`。另有实际配置、源指纹、运行清单及冻结记录。

分析表 `fixed_budget.jsonl` 保留全部层与读出；`pipeline.jsonl`、`common.jsonl` 分层列出。`paired_effects.jsonl` 是场景内配对比较，不跨六场景混池。主比较使用20,000次配对bootstrap，报告95%和六场景Bonferroni99.1667%区间；压力比较仅为逐场景探索性95%区间。条件有限输出MAE/P90必须与失败数一起看。

`delta_sensitivity.jsonl` 只以 .10/.20 重新评价同一轨迹和同一个主点估计，未将中心改成 z_.10/z_.20。`stop_replay.jsonl` 包含所有人的截尾试次数与实际停下者的正确率；模型的90%后验窗口概率不是已经获得的真实90%保证，也不能用该回放宣称BO比没有同等后验停止规则的Firth阶梯更快。

`analysis_manifest.json` 记录原始输入哈希及实际分析源哈希。独立复核脚本不导入仿真实现，检查完整记录组合、原始误差/数据支持、失败分母、Wilson区间、条件误差分位数及固定估计的容限敏感性。包内 `--verify-readouts` 可从每个前缀串行重建全部数值读出；上例的独立并行执行脚本复用同一个科学读出函数、核对全部读出字段，以节省运行时间，它不是另一个估计器。该检查的完整计数和源/输入指纹在单独的 `numerical-audit.json` 中，不修改分析清单里的串行重建开关。`replay --limit 5` 检查限定数量的完整采样轨迹。

本轮仍是静态合成人、实际加速度被准确测量的仿真。结果不能直接证明真人效果、实车执行安全或原TVCG系统的性能。
