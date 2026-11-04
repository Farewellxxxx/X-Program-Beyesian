# 个体加速度可接受上限：独立模拟乘客与自适应校准

研究问题：在车辆不能精确执行目标加速度时，如何利用“接受／不接受”反馈，以较少个人试次估计可接受上限？本仓库提供可复现的**合成乘客仿真**；尚无真人比较结果。

当前主线是 **2026-11-05 独立乘客与算法比较**。历史复杂执行模型实验保留在原目录，不作为新主入口。

本轮结果：在六个冻结仿真情景中，贝叶斯方法相对 TVCG 衍生 UCB 的平均受限达标成本降低 12.1–18.0 次（未达标按 60 次计，场景内未校正配对 95% 区间均低于零）。与 staircase 的差异、以及积分执行不确定性相对只用均值的增益均没有明确方向证据。不能据此宣称 BO 普遍最优或已证明真人优势；完整失败率和区间见中文报告。

## 阅读入口

- [研究任务与证据边界](docs/superpowers/specs/2026-11-05-decoupled-calibration-design.md)
- [模拟乘客与车辆执行](comfort_boundary_bo_research_package/docs/decoupled_simulator.md)
- [贝叶斯采集函数、UCB 与 staircase 的来源和适配](comfort_boundary_bo_research_package/docs/decoupled_algorithms.md)
- [复现、随机种子、指标和数据字段](comfort_boundary_bo_research_package/docs/decoupled_reproducibility.md)
- [中文结果报告](comfort_boundary_bo_research_package/docs/decoupled_results_zh.md)
- [后续 BO 单臂真人研究衔接](comfort_boundary_bo_research_package/docs/decoupled_human_handoff_zh.md)
- [验证与发布记录](docs/2026-11-05-decoupled-calibration-verification.md)

## 模块之间的关系

`策略提出目标 → 车辆产生实际加速度 → 模拟乘客返回二元反馈 → 策略更新`

独立评价器读取隐藏真值计算误差；策略只收到不可变的公开观测、公开配置和独立校准的执行估计。

| 模块 | 文件 | 职责 |
|---|---|---|
| 模拟乘客 | `passenger.py` | 独立接受概率、隐藏边界、二元反馈；不导入策略或拟合模型 |
| 车辆执行 | `execution.py` | 真实执行、独立校准及公开执行预测 |
| 公开接口 | `public.py` | 指令、实际测量、反馈与估计结果的白名单类型 |
| 校准策略 | `policies.py` | 贝叶斯风险减少选点、原文衍生 UCB、加权 staircase |
| 运行与评价 | `study.py` | 人群、独立随机流、真值隔离、冻结配置和逐试次评价 |
| 结果分析 | `analysis.py` | 完整性检查、乘客配对统计、图表与后处理指纹 |

这些文件位于 `comfort_boundary_bo_research_package/simulation/decoupled_calibration/`。

## 比较的含义

- `bayes_risk`：选择预计减少边界后验方差最多的指令，对可能的实际执行结果求平均。
- `bayes_point`：相同贝叶斯方法，仅使用执行预测均值，是执行不确定性的消融。
- `ucb_tvcg`：保留 TVCG 源码的符号奖励、多数投票、Q/count 探索及衰减；统一量纲后探索系数为 0.2。它是领域适配，非原研究完整复现。
- `staircase`：与接受概率标准匹配的加权上下阶梯。
- `ucb_tau`：调整拒绝惩罚的次要敏感性版本，不取代原奖励 UCB 主对照。

所有方法用自己的实际观测拟合同一个贝叶斯边界估计器。因此这里比较**采样效率**，不宣称比较了原算法整套系统，更不预设 BO 必须获胜。

主配置：3 种乘客曲线、2 种执行条件、每场景 32 人、5 方法、每条轨迹 60 次反馈。共 96 个独立乘客参数集、192 个乘客—条件案例、960 条轨迹、57,600 次反馈。每个乘客—条件另有 90 次合成车辆校准，跨方法共享，单独计入辅助数据成本。

接受标准 tau=0.70、误差容限 delta=0.15 m/s² 和 [0,3] m/s² 测试域都是仿真操作定义，不是经验证的真人标准或实车操作建议。主要“达标试次”需要事后检查到预算结束持续满足误差要求，不是可部署的在线停止规则。失败样本保留，区间以场景内的乘客为单位。

## 安装、测试与复现

使用 Python 3.12 与固定依赖：

```powershell
python -m pip install -r requirements-simulation.txt
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -m pytest -q
python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration --config configs/decoupled_pilot.json --output outputs/pilot
python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration --config configs/decoupled_heldout.json --output outputs/heldout
python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration.analysis --input outputs/heldout --output outputs/analysis
```

输出目录必须是新的或空的，运行器拒绝覆盖已有结果。开发 pilot 与正式评估使用不同种子；正式配置在结果查看前冻结。已发布结果位于 `results/decoupled_calibration_20261105/`，其中 `raw/` 保存配置、真值与完整记录，`analysis/` 保存统计和图表。

在 Windows 沙箱下，若系统临时目录报权限错误，先将当前进程的 TMP/TEMP 指向仓库内独立临时目录，再运行 pytest：

```powershell
New-Item -ItemType Directory -Force tmp/local-tests | Out-Null
$env:TMP=(Resolve-Path tmp/local-tests).Path
$env:TEMP=$env:TMP
python -m pytest -q --basetemp tmp/local-tests/pytest
```

## 历史与范围

[历史仿真入口和完整说明](comfort_boundary_bo_research_package/simulation/README.md)保留原来的边界修正、单调贝叶斯模型、执行估计分离、失配、复杂度选择及参数不确定性实验。新主线没有删除这些代码和结果。

原始真人数据、第三方论文和个人信息不在发布范围内。合成比较不能证明真人样本效率、实车安全或普遍算法优势；Poster 的后续真人阶段规划为 BO 单臂可行性研究加独立验证。
