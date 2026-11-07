# 静态观察者验证：复现说明

本轮基于 `4b9e7e3`，旧版保存点为 `baseline-finite-budget-v2-20261107`；新工作位于 `research/observer-validation-v3-study`。运行前固定的协议提交 `054171f` 在新自适应实验结果生成前保存了样本数、种子、场景、统计定义与来源审计。该Git记录不是OSF等第三方平台的外部注册。完整协议见 [设计协议](../../docs/superpowers/specs/2026-11-07-observer-validation-design.md)，来源和后续真人预试见 [来源审计](../../docs/observer-validation-sources-20261107.md)。

## 固定实验定义

- 新主批次：256组独立B/W参数，跨原有六场景复用；new_precision、staircase和ucb_tvcg三种采样；每条60次反馈。276480次合成反馈，另有46080次合成执行校准。
- 探索批次：64组基础参数对应的logistic/Gumbel两曲线×两执行条件完全匹配B/W；窄/宽W各有独立参数组。六场景共69120次反馈，另有23040次执行校准。各方法在同一场景内配对。不能将独立宽度组解释成同一人的配对变化。
- tau=.70、delta=.15、N30主终点、N60次要终点、success_target=.80、calibration_n=90以及全部失败定义保持不变。读取方法与采样器不随结果调优。
- 原六场景逐场景N30主比较保留20000次配对bootstrap及六场景Bonferroni99.1667%区间。新增总体统计先对同一基础参与者的六场景差值取等权均值，再重抽基础参与者；95%区间只标为预设次要分析，不是涵盖所有层、预算和终点的全局校正。

## 环境与执行

Python3.12及 `requirements-simulation.txt`。Windows沙盒中将临时目录放在项目 `tmp` 下，并为pytest显式指定新的 `--basetemp`。运行目录不得已存在。并行仅影响运行时，不改变固定随机流。每次启动新的PowerShell进程都须重新设置这些环境变量；不同工具调用的环境不自动继承。

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


## 本轮实际记录

正式主批次使用seed202611071，探索批次202611072；Monte Carlo审计202611073、主场景分析202611074、整体簇bootstrap202611075、探索分析202611076、纯耗时试跑202611079。观察者族、反射方向、样本数和预算均未按结果调整。

`before_sampling_audit.json`于2026-11-07 10:03:30.856 UTC记录正式目录尚不存在、两份冻结文件、新簇分析及观察者核验脚本的SHA256；正式主批次于10:03:34.905 UTC启动。代码审阅版本为729c013。该额外记录覆盖原运行器的analysis_hashes未自动包含的新分析脚本。

主批次276480反馈/46080校准，1002.46秒；探索批次69120反馈/23040校准，273.23秒。探索共有192组独立B/W（64组匹配形状人群、64组窄W、64组宽W），不是384个独立参与者。主批次1536个场景案例是256个独立基础参与者簇。纯耗时试跑6480反馈/1080校准，26.36秒；运行耗时不含后处理核验。

曲线图可独立复现，未增加实验反馈：

```powershell
python scripts/plot_stationary_observers.py --output outputs/observer_curves.png
```

图的源与输出指纹在`observer_curves_provenance.json`。正式分析清单分别为`main_analysis/analysis_manifest.json`、`exploratory_analysis/analysis_manifest.json`和`cluster_analysis/cluster_manifest.json`；完整数值重建与独立原始核验结果在各批次的`*_numerical_audit.json`和`*_independent_audit.json`。

额外的旧历史全量CLI烟雾检查在8分钟时因预算限制中止，未生成分析输出；不把它标成通过。它没有生成或中止任何新正式轨迹，新增单元测试、观察者审计与正式新批次的完整核验分别记录，后者不能用旧烟雾检查替代。


## 本轮核验结果

主批次和探索批次的独立原始记录核验均通过。数值重建分别覆盖73728/18432条读出、516096/129024个字段，总计92160条读出、645120个字段，全部与保存结果一致。每批次另有1条完整60反馈轨迹精确回放（`main_replay.json`、`exploratory_replay.json`）；这不等于重放了每条完整采样轨迹。

正式8条整体区间使用256个参与者簇，95%区间为次要且未全局校正；与报告数据逐字段一致。`report_data_audit.json`、`release_integrity_audit.json`与`legacy_preservation_audit.json`分别记录报告数值、发布来源完整性及旧版保留状态。

基准的外推边界也须保留：冻结推断仍为logistic，主logistic人群的k中位数约3.96接近先验中心4；边界人群在测试域内部，阶梯起点为1.5。共同读出不消除BO在选点阶段使用先验的差别。所有公式与源码核验都不能把这些人为设定变成已实测的人群规律；本轮没有据此重新调参。
