# 有限预算校准：逐场景仿真结果

固定主预算 N=30，容限 δ=0.15，目标支持成功率 80%。每场景 256 个配对基础参与者。
反馈 276480 次；另有执行校准 46080 次。跨反应族复用基础 B/W，不将条件案例数解释为独立人数。

成功必须同时满足数值正常、两种回答、估计在已观测实际强度范围内及误差不超过容限。全部失败仍在分母。仅当双侧95% Wilson下限达到目标才通过。

|场景|采样器 + 读出|支持成功率 [95% Wilson]|失败/总数|有限输出 MAE / P90|是否通过|
|---|---|---|---|---|---|
|lapse_logistic_precise|new_precision + common/new_median|0.859 [0.811, 0.897]|0/256|0.081 / 0.168|是|
|lapse_logistic_precise|new_precision + common/new_precision|0.859 [0.811, 0.897]|0/256|0.080 / 0.170|是|
|lapse_logistic_precise|new_precision + pipeline/new_precision|0.859 [0.811, 0.897]|0/256|0.080 / 0.170|是|
|lapse_logistic_precise|staircase + common/new_median|0.766 [0.710, 0.813]|0/256|0.105 / 0.225|证据不足|
|lapse_logistic_precise|staircase + common/new_precision|0.770 [0.714, 0.817]|0/256|0.104 / 0.218|证据不足|
|lapse_logistic_precise|staircase + pipeline/firth|0.750 [0.694, 0.799]|0/256|0.126 / 0.237|证据不足|
|lapse_logistic_precise|ucb_tvcg + common/new_median|0.531 [0.470, 0.591]|0/256|0.187 / 0.409|证据不足|
|lapse_logistic_precise|ucb_tvcg + common/new_precision|0.543 [0.482, 0.603]|0/256|0.183 / 0.419|证据不足|
|lapse_logistic_variable|new_precision + common/new_median|0.785 [0.731, 0.831]|0/256|0.099 / 0.218|证据不足|
|lapse_logistic_variable|new_precision + common/new_precision|0.793 [0.739, 0.838]|0/256|0.098 / 0.216|证据不足|
|lapse_logistic_variable|new_precision + pipeline/new_precision|0.793 [0.739, 0.838]|0/256|0.098 / 0.216|证据不足|
|lapse_logistic_variable|staircase + common/new_median|0.746 [0.689, 0.796]|0/256|0.111 / 0.240|证据不足|
|lapse_logistic_variable|staircase + common/new_precision|0.754 [0.698, 0.803]|0/256|0.111 / 0.240|证据不足|
|lapse_logistic_variable|staircase + pipeline/firth|0.715 [0.657, 0.767]|0/256|0.137 / 0.272|证据不足|
|lapse_logistic_variable|ucb_tvcg + common/new_median|0.465 [0.405, 0.526]|0/256|0.204 / 0.462|证据不足|
|lapse_logistic_variable|ucb_tvcg + common/new_precision|0.473 [0.412, 0.534]|0/256|0.198 / 0.442|证据不足|
|logistic_precise|new_precision + common/new_median|0.805 [0.752, 0.849]|0/256|0.091 / 0.200|证据不足|
|logistic_precise|new_precision + common/new_precision|0.809 [0.756, 0.852]|0/256|0.091 / 0.189|证据不足|
|logistic_precise|new_precision + pipeline/new_precision|0.809 [0.756, 0.852]|0/256|0.091 / 0.189|证据不足|
|logistic_precise|staircase + common/new_median|0.781 [0.727, 0.828]|0/256|0.100 / 0.235|证据不足|
|logistic_precise|staircase + common/new_precision|0.793 [0.739, 0.838]|0/256|0.099 / 0.235|证据不足|
|logistic_precise|staircase + pipeline/firth|0.754 [0.698, 0.803]|0/256|0.112 / 0.241|证据不足|
|logistic_precise|ucb_tvcg + common/new_median|0.594 [0.533, 0.652]|0/256|0.151 / 0.319|证据不足|
|logistic_precise|ucb_tvcg + common/new_precision|0.598 [0.537, 0.656]|0/256|0.148 / 0.321|证据不足|
|logistic_variable|new_precision + common/new_median|0.801 [0.748, 0.845]|0/256|0.094 / 0.194|证据不足|
|logistic_variable|new_precision + common/new_precision|0.797 [0.743, 0.842]|0/256|0.094 / 0.190|证据不足|
|logistic_variable|new_precision + pipeline/new_precision|0.797 [0.743, 0.842]|0/256|0.094 / 0.190|证据不足|
|logistic_variable|staircase + common/new_median|0.809 [0.756, 0.852]|0/256|0.090 / 0.189|证据不足|
|logistic_variable|staircase + common/new_precision|0.809 [0.756, 0.852]|0/256|0.091 / 0.187|证据不足|
|logistic_variable|staircase + pipeline/firth|0.750 [0.694, 0.799]|0/256|0.114 / 0.213|证据不足|
|logistic_variable|ucb_tvcg + common/new_median|0.574 [0.513, 0.633]|0/256|0.152 / 0.302|证据不足|
|logistic_variable|ucb_tvcg + common/new_precision|0.594 [0.533, 0.652]|0/256|0.146 / 0.307|证据不足|
|probit_precise|new_precision + common/new_median|0.836 [0.786, 0.876]|0/256|0.089 / 0.198|证据不足|
|probit_precise|new_precision + common/new_precision|0.836 [0.786, 0.876]|0/256|0.088 / 0.198|证据不足|
|probit_precise|new_precision + pipeline/new_precision|0.836 [0.786, 0.876]|0/256|0.088 / 0.198|证据不足|
|probit_precise|staircase + common/new_median|0.801 [0.748, 0.845]|0/256|0.096 / 0.203|证据不足|
|probit_precise|staircase + common/new_precision|0.797 [0.743, 0.842]|0/256|0.094 / 0.199|证据不足|
|probit_precise|staircase + pipeline/firth|0.770 [0.714, 0.817]|0/256|0.107 / 0.207|证据不足|
|probit_precise|ucb_tvcg + common/new_median|0.562 [0.501, 0.622]|0/256|0.156 / 0.309|证据不足|
|probit_precise|ucb_tvcg + common/new_precision|0.582 [0.521, 0.641]|0/256|0.154 / 0.309|证据不足|
|probit_variable|new_precision + common/new_median|0.820 [0.769, 0.862]|0/256|0.093 / 0.198|证据不足|
|probit_variable|new_precision + common/new_precision|0.820 [0.769, 0.862]|0/256|0.091 / 0.190|证据不足|
|probit_variable|new_precision + pipeline/new_precision|0.820 [0.769, 0.862]|0/256|0.091 / 0.190|证据不足|
|probit_variable|staircase + common/new_median|0.797 [0.743, 0.842]|0/256|0.098 / 0.221|证据不足|
|probit_variable|staircase + common/new_precision|0.801 [0.748, 0.845]|0/256|0.095 / 0.217|证据不足|
|probit_variable|staircase + pipeline/firth|0.789 [0.735, 0.835]|0/256|0.116 / 0.224|证据不足|
|probit_variable|ucb_tvcg + common/new_median|0.668 [0.608, 0.723]|0/256|0.135 / 0.279|证据不足|
|probit_variable|ucb_tvcg + common/new_precision|0.660 [0.600, 0.715]|0/256|0.133 / 0.270|证据不足|

A层是完整流程；B层是共同新先验估计器。UCB最大Q命令和阶梯反转均值另存诊断，未混入实际边界误差排名。原版BO原生旧先验中位数另存历史参照。
主对比为新精度BO减阶梯，每场景、每层分别进行20,000次参与者配对百分位bootstrap，保存95%及六主场景Bonferroni99.1667%区间；开发拆解仍仅属于开发证据。
不跨场景混池，不将区间包含零解释为等效。共同层另有新精度减新方差、新方差减旧方差的预定次要受控对比。
δ=.10/.20仅改变同一主点估计的评价容限。开发先验/读出拆解是开发证据；整体先验变化不能归因于单独居中。
本结果来自固定、静态合成反应曲线及无额外误差的实际强度测量，不能证明真人、道路安全或TVCG原系统性能。压力条件仅在对应独立输出存在时视为已测试。
