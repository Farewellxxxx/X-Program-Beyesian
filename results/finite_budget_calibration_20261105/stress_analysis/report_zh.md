# 有限预算校准：逐场景仿真结果

固定主预算 N=30，容限 δ=0.15，目标支持成功率 80%。每场景 64 个配对基础参与者。
反馈 80640 次；另有执行校准 40320 次。本压力批次使用7个独立参数组，共448份独立基础参数；每个场景内部的方法共享同一参与者参数。跨压力场景不作配对宽度或起点因果效应推断。

成功必须同时满足数值正常、两种回答、估计在已观测实际强度范围内及误差不超过容限。全部失败仍在分母。仅当双侧95% Wilson下限达到目标才通过。

|场景|采样器 + 读出|支持成功率 [95% Wilson]|失败/总数|有限输出 MAE / P90|是否通过|
|---|---|---|---|---|---|
|boundary_high|new_precision + common/new_median|0.703 [0.582, 0.801]|0/64|0.114 / 0.220|证据不足|
|boundary_high|new_precision + common/new_precision|0.703 [0.582, 0.801]|0/64|0.110 / 0.220|证据不足|
|boundary_high|new_precision + pipeline/new_precision|0.703 [0.582, 0.801]|0/64|0.110 / 0.220|证据不足|
|boundary_high|new_variance + common/new_median|0.672 [0.550, 0.774]|0/64|0.118 / 0.218|证据不足|
|boundary_high|new_variance + common/new_precision|0.672 [0.550, 0.774]|0/64|0.117 / 0.218|证据不足|
|boundary_high|new_variance + pipeline/new_precision|0.672 [0.550, 0.774]|0/64|0.117 / 0.218|证据不足|
|boundary_high|staircase + common/new_median|0.656 [0.534, 0.761]|0/64|0.106 / 0.200|证据不足|
|boundary_high|staircase + common/new_precision|0.688 [0.566, 0.788]|0/64|0.104 / 0.188|证据不足|
|boundary_high|staircase + pipeline/firth|0.672 [0.550, 0.774]|0/64|0.214 / 0.337|证据不足|
|boundary_low|new_precision + common/new_median|0.859 [0.754, 0.924]|0/64|0.089 / 0.158|证据不足|
|boundary_low|new_precision + common/new_precision|0.859 [0.754, 0.924]|0/64|0.087 / 0.158|证据不足|
|boundary_low|new_precision + pipeline/new_precision|0.859 [0.754, 0.924]|0/64|0.087 / 0.158|证据不足|
|boundary_low|new_variance + common/new_median|0.781 [0.666, 0.865]|0/64|0.098 / 0.223|证据不足|
|boundary_low|new_variance + common/new_precision|0.781 [0.666, 0.865]|0/64|0.097 / 0.213|证据不足|
|boundary_low|new_variance + pipeline/new_precision|0.781 [0.666, 0.865]|0/64|0.097 / 0.213|证据不足|
|boundary_low|staircase + common/new_median|0.719 [0.599, 0.814]|0/64|0.108 / 0.240|证据不足|
|boundary_low|staircase + common/new_precision|0.719 [0.599, 0.814]|0/64|0.105 / 0.240|证据不足|
|boundary_low|staircase + pipeline/firth|0.672 [0.550, 0.774]|0/64|0.129 / 0.238|证据不足|
|lapse_020|new_precision + common/new_median|0.672 [0.550, 0.774]|0/64|0.132 / 0.286|证据不足|
|lapse_020|new_precision + common/new_precision|0.703 [0.582, 0.801]|0/64|0.129 / 0.288|证据不足|
|lapse_020|new_precision + pipeline/new_precision|0.703 [0.582, 0.801]|0/64|0.129 / 0.288|证据不足|
|lapse_020|new_variance + common/new_median|0.797 [0.683, 0.877]|0/64|0.105 / 0.191|证据不足|
|lapse_020|new_variance + common/new_precision|0.797 [0.683, 0.877]|0/64|0.101 / 0.191|证据不足|
|lapse_020|new_variance + pipeline/new_precision|0.797 [0.683, 0.877]|0/64|0.101 / 0.191|证据不足|
|lapse_020|staircase + common/new_median|0.703 [0.582, 0.801]|0/64|0.115 / 0.259|证据不足|
|lapse_020|staircase + common/new_precision|0.703 [0.582, 0.801]|0/64|0.115 / 0.259|证据不足|
|lapse_020|staircase + pipeline/firth|0.656 [0.534, 0.761]|0/64|0.121 / 0.214|证据不足|
|staircase_start_high|new_precision + common/new_median|0.812 [0.700, 0.889]|0/64|0.089 / 0.198|证据不足|
|staircase_start_high|new_precision + common/new_precision|0.797 [0.683, 0.877]|0/64|0.090 / 0.198|证据不足|
|staircase_start_high|new_precision + pipeline/new_precision|0.797 [0.683, 0.877]|0/64|0.090 / 0.198|证据不足|
|staircase_start_high|new_variance + common/new_median|0.844 [0.736, 0.913]|0/64|0.094 / 0.175|证据不足|
|staircase_start_high|new_variance + common/new_precision|0.875 [0.772, 0.935]|0/64|0.089 / 0.175|证据不足|
|staircase_start_high|new_variance + pipeline/new_precision|0.875 [0.772, 0.935]|0/64|0.089 / 0.175|证据不足|
|staircase_start_high|staircase + common/new_median|0.844 [0.736, 0.913]|0/64|0.092 / 0.214|证据不足|
|staircase_start_high|staircase + common/new_precision|0.828 [0.718, 0.901]|0/64|0.090 / 0.187|证据不足|
|staircase_start_high|staircase + pipeline/firth|0.797 [0.683, 0.877]|0/64|0.103 / 0.198|证据不足|
|staircase_start_low|new_precision + common/new_median|0.688 [0.566, 0.788]|0/64|0.119 / 0.228|证据不足|
|staircase_start_low|new_precision + common/new_precision|0.688 [0.566, 0.788]|0/64|0.118 / 0.240|证据不足|
|staircase_start_low|new_precision + pipeline/new_precision|0.688 [0.566, 0.788]|0/64|0.118 / 0.240|证据不足|
|staircase_start_low|new_variance + common/new_median|0.781 [0.666, 0.865]|0/64|0.100 / 0.220|证据不足|
|staircase_start_low|new_variance + common/new_precision|0.781 [0.666, 0.865]|0/64|0.099 / 0.220|证据不足|
|staircase_start_low|new_variance + pipeline/new_precision|0.781 [0.666, 0.865]|0/64|0.099 / 0.220|证据不足|
|staircase_start_low|staircase + common/new_median|0.688 [0.566, 0.788]|0/64|0.113 / 0.240|证据不足|
|staircase_start_low|staircase + common/new_precision|0.734 [0.615, 0.827]|0/64|0.115 / 0.256|证据不足|
|staircase_start_low|staircase + pipeline/firth|0.688 [0.566, 0.788]|0/64|0.197 / 0.273|证据不足|
|width_narrow|new_precision + common/new_median|0.984 [0.917, 0.997]|0/64|0.051 / 0.098|是|
|width_narrow|new_precision + common/new_precision|0.984 [0.917, 0.997]|0/64|0.055 / 0.108|是|
|width_narrow|new_precision + pipeline/new_precision|0.984 [0.917, 0.997]|0/64|0.055 / 0.108|是|
|width_narrow|new_variance + common/new_median|0.984 [0.917, 0.997]|0/64|0.044 / 0.092|是|
|width_narrow|new_variance + common/new_precision|0.984 [0.917, 0.997]|0/64|0.045 / 0.111|是|
|width_narrow|new_variance + pipeline/new_precision|0.984 [0.917, 0.997]|0/64|0.045 / 0.111|是|
|width_narrow|staircase + common/new_median|0.969 [0.893, 0.991]|0/64|0.055 / 0.117|是|
|width_narrow|staircase + common/new_precision|0.969 [0.893, 0.991]|0/64|0.054 / 0.117|是|
|width_narrow|staircase + pipeline/firth|0.953 [0.871, 0.984]|0/64|0.057 / 0.114|是|
|width_wide|new_precision + common/new_median|0.500 [0.381, 0.619]|0/64|0.182 / 0.345|证据不足|
|width_wide|new_precision + common/new_precision|0.516 [0.396, 0.634]|0/64|0.183 / 0.345|证据不足|
|width_wide|new_precision + pipeline/new_precision|0.516 [0.396, 0.634]|0/64|0.183 / 0.345|证据不足|
|width_wide|new_variance + common/new_median|0.562 [0.441, 0.677]|0/64|0.170 / 0.371|证据不足|
|width_wide|new_variance + common/new_precision|0.562 [0.441, 0.677]|0/64|0.172 / 0.389|证据不足|
|width_wide|new_variance + pipeline/new_precision|0.562 [0.441, 0.677]|0/64|0.172 / 0.389|证据不足|
|width_wide|staircase + common/new_median|0.562 [0.441, 0.677]|0/64|0.175 / 0.344|证据不足|
|width_wide|staircase + common/new_precision|0.562 [0.441, 0.677]|0/64|0.172 / 0.340|证据不足|
|width_wide|staircase + pipeline/firth|0.562 [0.441, 0.677]|0/64|0.232 / 0.526|证据不足|

A层是完整流程；B层是共同新先验估计器。UCB最大Q命令和阶梯反转均值另存诊断，未混入实际边界误差排名。原版BO原生旧先验中位数另存历史参照。
压力条件仅报告各场景95%探索性配对区间；不把六主场景Bonferroni修正用于七压力条件。
不跨场景混池，不将区间包含零解释为等效。共同层另有新精度减新方差、新方差减旧方差的预定次要受控对比。
δ=.10/.20仅改变同一主点估计的评价容限。开发先验/读出拆解是开发证据；整体先验变化不能归因于单独居中。
本结果来自固定、静态合成反应曲线及无额外误差的实际强度测量，不能证明真人、道路安全或TVCG原系统性能。压力条件仅在对应独立输出存在时视为已测试。

图中MAE/P90单位为m/s²；成功率的.80虚线仅表示点率参照，是否达标以表中95% Wilson下限为准。

编者修订：仅纠正压力批次的参数复用说明及补充图注，冻结统计定义、数值表、分析源和图均未改变。
