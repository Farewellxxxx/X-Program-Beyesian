# 静态观察者验证：复现说明

本轮基于 `4b9e7e3`，旧版保存点为 `baseline-finite-budget-v2-20261107`；新工作位于 `research/observer-validation-v3-study`。预注册提交 `054171f` 在新自适应实验结果生成前保存了样本数、种子、场景、统计定义与来源审计。完整协议见 [设计协议](../../docs/superpowers/specs/2026-11-07-observer-validation-design.md)，来源和后续真人预试见 [来源审计](../../docs/observer-validation-sources-20261107.md)。

## 固定实验定义

- 新主批次：256组独立B/W参数，跨原有六场景复用；new_precision、staircase和ucb_tvcg三种采样；每条60次反馈。276480次合成反馈，另有46080次合成执行校准。
- 探索批次：64组基础参数对应的logistic/Gumbel两曲线×两执行条件完全匹配B/W；窄/宽W各有独立参数组。六场景共69120次反馈，另有23040次执行校准。各方法在同一场景内配对。不能将独立宽度组解释成同一人的配对变化。
- tau=.70、delta=.15、N30主终点、N60次要终点、success_target=.80、calibration_n=90以及全部失败定义保持不变。读取方法与采样器不随结果调优。
- 原六场景逐场景N30主比较保留20000次配对bootstrap及六场景Bonferroni99.1667%区间。新增总体统计先对同一基础参与者的六场景差值取等权均值，再重抽基础参与者；95%区间只标为预设次要分析，不是涵盖所有层、预算和终点的全局校正。

## 环境与执行

Python3.12及 `requirements-simulation.txt`。Windows沙盒中将临时目录放在项目 `tmp` 下，并为pytest显式指定新的 `--basetemp`。运行目录不得已存在。并行仅影响运行时，不改变固定随机流。

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
New-Item -ItemType Directory -Force tmp/observer-runtime | Out-Null
$env:TMP=(Resolve-Path tmp/observer-runtime).Path
$env:TEMP=$env:TMP
$env:TMPDIR=$env:TMP
$fb='comfort_boundary_bo_research_package.simulation.finite_budget'
$art='results/observer_validation_20261107'
python -m pytest -q --basetemp tmp/observer-pytest-reproduction
python scripts/validate_stationary_observers.py --output outputs/observer-audit.json
python -m $fb run --config configs/observer_validation_main.json --freeze "$art/main_freeze.json" --output outputs/observer-main --workers 6
python -m $fb analyze --input outputs/observer-main --output outputs/observer-main-analysis --no-plots
python scripts/analyze_observer_clusters.py --input outputs/observer-main --output outputs/observer-cluster-analysis
python scripts/verify_finite_budget_artifacts.py --input outputs/observer-main --analysis outputs/observer-main-analysis --output outputs/observer-main-independent-audit.json
python scripts/verify_finite_budget_readouts_parallel.py --input outputs/observer-main --output outputs/observer-main-numerical-audit.json --workers 6
python -m $fb run --config configs/observer_validation_exploratory.json --freeze "$art/exploratory_freeze.json" --output outputs/observer-exploratory --workers 6
python -m $fb analyze --input outputs/observer-exploratory --output outputs/observer-exploratory-analysis --no-plots
python scripts/verify_finite_budget_artifacts.py --input outputs/observer-exploratory --analysis outputs/observer-exploratory-analysis --output outputs/observer-exploratory-independent-audit.json
python scripts/verify_finite_budget_readouts_parallel.py --input outputs/observer-exploratory --output outputs/observer-exploratory-numerical-audit.json --workers 6
```

冻结文件包含当次实际源哈希、配置、历史阶梯选型与原数值网格决策；源码字节必须吻合，否则运行应拒绝。正式保留目录是本轮 `results/observer_validation_20261107`，上述 `outputs` 目录仅是避免覆盖的复现示例。runtime_pilot只用于耗时记录，MC观察者审计只用于概率/随机流正确性验证，都不作为新主批次效果证据。

## 审计及统计含义

`frozen_algorithm_proof.json`对照旧批次冻结的12个受保护科学模块，证明选点、先验、读出、执行代码字节一致；仅观察者与family白名单扩展。新旧批次点率的差别是独立Monte Carlo复现差异，不能称作算法改善。

独立观察者脚本使用SciPy1.13.1概率分布与解析分位数作外部数值参照，记录版本、源码指纹和固定Monte Carlo设计。Gumbel使用gumbel_l的生存函数；其偏斜方向与简单刺激轴反射不同。Monte Carlo检验通过只能支持程序实现符合指定静态Bernoulli模型，不能验证真人分布。

原始工件保存隐藏真值、执行校准、实际观测试次、全部预算读出和停止回放。独立artifact脚本不导入仿真实现，复算分类、分母与汇总。parallel readout脚本从每个真实前缀重建全部读出；它复用科学读出函数，不是第二个独立估计器。所有数值失败都保留在成功率分母；有限但不受数据支持的估计仍保留其有限封顶误差，非有限输出的封顶误差为3。

总体分析的1536个条件案例只有256个基础参与者簇。A与B的新BO输出相同，两层不是两次独立复现；八个总体区间（两预算×两层×两指标）未作全局多重校正。探索条件、匹配曲线的描述性差异和旧历史压力结果均不替代六主场景的原校正比较。
