# 执行估计扩展：验证记录

基线 `9679123801b67d03eb483abef4259dacd101f150`；隔离发布目录中的 feature/flexible-execution-estimator 分支。环境 Python 3.12.7、NumPy 1.26.4、pandas 2.2.2、matplotlib 3.9.2、pytest 7.4.4。没有新增依赖。模型常数在全量运行前固定，方法见[说明](2026-11-04-flexible-execution-method.md)。

## 数值、隔离和接口测试

基线完整测试 63 passed。第一组 11 个新测试先因缺少新模型失败，随后实现并通过；第二组 5 个新测试先因缺少 CLI/审计入口失败，随后通过。启动全量实验前完整测试 **79 passed（12.66 秒）**。测试覆盖：

- 独立计算的加权岭系数与残差协方差数值，不使用被测函数生成期望值；零噪声二次函数恢复与正定协方差下限。
- 两端单调约束分别激活、同时激活；缺列、非有限、越界、缺样本、秩不足、协方差非正定的拒绝，以及触边记录计数。
- 不同通道尺度和三个不同相关性的采样；包含时间效应时标量/批量采样的强度均值与标准差一致。
- 相同观测在改变隐藏执行真值后产生相同估计；拟合模型不含 truth Distortion/隐藏配置；适配不修改原对象。
- 相同人群与过程流下，随机/网格/阶梯策略的命令、实测运动及反馈在新旧模型间逐值相同。
- 扩展/POC 共用的显式选择器、独立输出目录、拟合表和各汇总中的来源字段；不合法的模型/认知组合拒绝。
- 280 个场景与原配置逐项相等；模型设置指纹、重算拟合参数、校准观测指纹与逐值相等、原汇总精确重放。
- 缺少完整场景或单个策略、修改种子/观测/拟合系数/设置指纹、缺少诊断命令、历史指标变化均拒绝。

约束测试中一个人为递减均值样例的初始截距使记录超过物理加速度上界；将截距从 1.2 修正为 0.9 后仍激活两个约束。这是修正无效测试输入，没有改变模型参数或方法。280 组正式校准在全量反馈运行前全部拟合成功，未排除任何失败场景。

## 全量运行

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
python -m pytest -q
python long_horizon_audit/scripts/run_flexible_execution_audit.py --workers 8
python long_horizon_audit/scripts/compare_flexible_execution.py
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py --execution-estimator quadratic_covariance
python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py --execution-estimator quadratic_covariance
```

新模型保存每个 profile 的配置、策略汇总、个体汇总、人群、校准观测、执行诊断和拟合参数。旧版重放保存逐策略汇总和原场景配置，原档案保留完整个体记录，不重复发布百万行反馈表；所有反馈可由种子和配置重建。每个独立执行诊断含 21 个命令、每点 4096 个样本，且不进入训练。检查旧汇总的全部原字段，不只检查边界误差。

扩展例生成 2880 条试验和两组拟合；POC 生成 900 条试验和一组拟合。两者各有九张图和八张 CSV，共 17 个文件，使用原单次示例的人群和等间距校准顺序，与嵌套预算主审计分开解释。

最终运行、独立审查、图表、哈希、同步和发布证据在完成后补充于本文件下方。
