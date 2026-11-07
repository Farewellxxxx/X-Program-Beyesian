# 有限预算校准：逐场景仿真结果

固定主预算 N=30，容限 δ=0.15，目标支持成功率 80%。每场景 64 个配对基础参与者。
反馈 69120 次；另有执行校准 23040 次。跨反应族复用基础 B/W，不将条件案例数解释为独立人数。

成功必须同时满足数值正常、两种回答、估计在已观测实际强度范围内及误差不超过容限。全部失败仍在分母。仅当双侧95% Wilson下限达到目标才通过。

|场景|采样器 + 读出|支持成功率 [95% Wilson]|失败/总数|有限输出 MAE / P90|是否通过|
|---|---|---|---|---|---|
|gumbel_precise|new_precision + common/new_median|0.781 [0.666, 0.865]|0/64|0.108 / 0.217|证据不足|
|gumbel_precise|new_precision + common/new_precision|0.781 [0.666, 0.865]|0/64|0.106 / 0.214|证据不足|
|gumbel_precise|new_precision + pipeline/new_precision|0.781 [0.666, 0.865]|0/64|0.106 / 0.214|证据不足|
|gumbel_precise|staircase + common/new_median|0.766 [0.649, 0.853]|0/64|0.100 / 0.198|证据不足|
|gumbel_precise|staircase + common/new_precision|0.797 [0.683, 0.877]|0/64|0.100 / 0.199|证据不足|
|gumbel_precise|staircase + pipeline/firth|0.688 [0.566, 0.788]|0/64|0.124 / 0.239|证据不足|
|gumbel_precise|ucb_tvcg + common/new_median|0.656 [0.534, 0.761]|0/64|0.153 / 0.297|证据不足|
|gumbel_precise|ucb_tvcg + common/new_precision|0.656 [0.534, 0.761]|0/64|0.143 / 0.270|证据不足|
|gumbel_variable|new_precision + common/new_median|0.766 [0.649, 0.853]|0/64|0.109 / 0.238|证据不足|
|gumbel_variable|new_precision + common/new_precision|0.766 [0.649, 0.853]|0/64|0.110 / 0.238|证据不足|
|gumbel_variable|new_precision + pipeline/new_precision|0.766 [0.649, 0.853]|0/64|0.110 / 0.238|证据不足|
|gumbel_variable|staircase + common/new_median|0.656 [0.534, 0.761]|0/64|0.115 / 0.234|证据不足|
|gumbel_variable|staircase + common/new_precision|0.656 [0.534, 0.761]|0/64|0.120 / 0.239|证据不足|
|gumbel_variable|staircase + pipeline/firth|0.625 [0.503, 0.733]|0/64|0.124 / 0.255|证据不足|
|gumbel_variable|ucb_tvcg + common/new_median|0.500 [0.381, 0.619]|0/64|0.169 / 0.341|证据不足|
|gumbel_variable|ucb_tvcg + common/new_precision|0.516 [0.396, 0.634]|0/64|0.160 / 0.314|证据不足|
|logistic_precise|new_precision + common/new_median|0.734 [0.615, 0.827]|0/64|0.105 / 0.238|证据不足|
|logistic_precise|new_precision + common/new_precision|0.734 [0.615, 0.827]|0/64|0.105 / 0.221|证据不足|
|logistic_precise|new_precision + pipeline/new_precision|0.734 [0.615, 0.827]|0/64|0.105 / 0.221|证据不足|
|logistic_precise|staircase + common/new_median|0.734 [0.615, 0.827]|0/64|0.105 / 0.232|证据不足|
|logistic_precise|staircase + common/new_precision|0.750 [0.632, 0.840]|0/64|0.107 / 0.242|证据不足|
|logistic_precise|staircase + pipeline/firth|0.750 [0.632, 0.840]|0/64|0.108 / 0.228|证据不足|
|logistic_precise|ucb_tvcg + common/new_median|0.641 [0.518, 0.747]|0/64|0.136 / 0.264|证据不足|
|logistic_precise|ucb_tvcg + common/new_precision|0.625 [0.503, 0.733]|0/64|0.132 / 0.274|证据不足|
|logistic_variable|new_precision + common/new_median|0.812 [0.700, 0.889]|0/64|0.094 / 0.194|证据不足|
|logistic_variable|new_precision + common/new_precision|0.812 [0.700, 0.889]|0/64|0.091 / 0.192|证据不足|
|logistic_variable|new_precision + pipeline/new_precision|0.812 [0.700, 0.889]|0/64|0.091 / 0.192|证据不足|
|logistic_variable|staircase + common/new_median|0.750 [0.632, 0.840]|0/64|0.112 / 0.209|证据不足|
|logistic_variable|staircase + common/new_precision|0.766 [0.649, 0.853]|0/64|0.109 / 0.180|证据不足|
|logistic_variable|staircase + pipeline/firth|0.719 [0.599, 0.814]|0/64|0.145 / 0.220|证据不足|
|logistic_variable|ucb_tvcg + common/new_median|0.531 [0.411, 0.648]|0/64|0.156 / 0.355|证据不足|
|logistic_variable|ucb_tvcg + common/new_precision|0.562 [0.441, 0.677]|0/64|0.150 / 0.317|证据不足|
|width_narrow_variable|new_precision + common/new_median|0.953 [0.871, 0.984]|0/64|0.056 / 0.101|是|
|width_narrow_variable|new_precision + common/new_precision|0.953 [0.871, 0.984]|0/64|0.061 / 0.120|是|
|width_narrow_variable|new_precision + pipeline/new_precision|0.953 [0.871, 0.984]|0/64|0.061 / 0.120|是|
|width_narrow_variable|staircase + common/new_median|0.969 [0.893, 0.991]|0/64|0.058 / 0.109|是|
|width_narrow_variable|staircase + common/new_precision|0.969 [0.893, 0.991]|0/64|0.059 / 0.110|是|
|width_narrow_variable|staircase + pipeline/firth|0.969 [0.893, 0.991]|0/64|0.061 / 0.119|是|
|width_narrow_variable|ucb_tvcg + common/new_median|0.734 [0.615, 0.827]|0/64|0.104 / 0.210|证据不足|
|width_narrow_variable|ucb_tvcg + common/new_precision|0.766 [0.649, 0.853]|0/64|0.097 / 0.199|证据不足|
|width_wide_variable|new_precision + common/new_median|0.547 [0.426, 0.663]|0/64|0.168 / 0.329|证据不足|
|width_wide_variable|new_precision + common/new_precision|0.547 [0.426, 0.663]|0/64|0.168 / 0.327|证据不足|
|width_wide_variable|new_precision + pipeline/new_precision|0.547 [0.426, 0.663]|0/64|0.168 / 0.327|证据不足|
|width_wide_variable|staircase + common/new_median|0.625 [0.503, 0.733]|0/64|0.135 / 0.328|证据不足|
|width_wide_variable|staircase + common/new_precision|0.641 [0.518, 0.747]|0/64|0.137 / 0.312|证据不足|
|width_wide_variable|staircase + pipeline/firth|0.578 [0.456, 0.691]|0/64|0.210 / 0.430|证据不足|
|width_wide_variable|ucb_tvcg + common/new_median|0.547 [0.426, 0.663]|0/64|0.198 / 0.439|证据不足|
|width_wide_variable|ucb_tvcg + common/new_precision|0.562 [0.441, 0.677]|0/64|0.195 / 0.440|证据不足|

A层是完整流程；B层是共同新先验估计器。UCB最大Q命令和阶梯反转均值另存诊断，未混入实际边界误差排名。原版BO原生旧先验中位数另存历史参照。
压力条件仅报告各场景95%探索性配对区间；不把六主场景Bonferroni修正用于七压力条件。
不跨场景混池，不将区间包含零解释为等效。共同层另有新精度减新方差、新方差减旧方差的预定次要受控对比。
δ=.10/.20仅改变同一主点估计的评价容限。开发先验/读出拆解是开发证据；整体先验变化不能归因于单独居中。
本结果来自固定、静态合成反应曲线及无额外误差的实际强度测量，不能证明真人、道路安全或TVCG原系统性能。压力条件仅在对应独立输出存在时视为已测试。
