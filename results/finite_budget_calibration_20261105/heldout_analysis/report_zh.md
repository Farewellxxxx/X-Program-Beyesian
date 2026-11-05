# 有限预算校准：逐场景仿真结果

固定主预算 N=30，容限 δ=0.15，目标支持成功率 80%。每场景 128 个配对基础参与者。
反馈 230400 次；另有执行校准 23040 次。跨反应族复用基础 B/W，不将条件案例数解释为独立人数。

成功必须同时满足数值正常、两种回答、估计在已观测实际强度范围内及误差不超过容限。全部失败仍在分母。仅当双侧95% Wilson下限达到目标才通过。

|场景|采样器 + 读出|支持成功率 [95% Wilson]|失败/总数|有限输出 MAE / P90|是否通过|
|---|---|---|---|---|---|
|lapse_logistic_precise|new_precision + common/new_median|0.805 [0.728, 0.864]|0/128|0.095 / 0.205|证据不足|
|lapse_logistic_precise|new_precision + common/new_precision|0.805 [0.728, 0.864]|0/128|0.094 / 0.207|证据不足|
|lapse_logistic_precise|new_precision + pipeline/new_precision|0.805 [0.728, 0.864]|0/128|0.094 / 0.207|证据不足|
|lapse_logistic_precise|new_variance + common/new_median|0.750 [0.668, 0.817]|0/128|0.105 / 0.221|证据不足|
|lapse_logistic_precise|new_variance + common/new_precision|0.750 [0.668, 0.817]|0/128|0.105 / 0.227|证据不足|
|lapse_logistic_precise|new_variance + pipeline/new_precision|0.750 [0.668, 0.817]|0/128|0.105 / 0.227|证据不足|
|lapse_logistic_precise|old_variance + common/new_median|0.758 [0.677, 0.824]|0/128|0.102 / 0.208|证据不足|
|lapse_logistic_precise|old_variance + common/new_precision|0.773 [0.694, 0.837]|0/128|0.103 / 0.219|证据不足|
|lapse_logistic_precise|old_variance + pipeline/old_precision|0.781 [0.702, 0.844]|0/128|0.108 / 0.230|证据不足|
|lapse_logistic_precise|staircase + common/new_median|0.750 [0.668, 0.817]|0/128|0.097 / 0.211|证据不足|
|lapse_logistic_precise|staircase + common/new_precision|0.781 [0.702, 0.844]|0/128|0.095 / 0.202|证据不足|
|lapse_logistic_precise|staircase + pipeline/firth|0.727 [0.644, 0.796]|0/128|0.106 / 0.224|证据不足|
|lapse_logistic_precise|ucb_tvcg + common/new_median|0.508 [0.422, 0.593]|0/128|0.199 / 0.422|证据不足|
|lapse_logistic_precise|ucb_tvcg + common/new_precision|0.492 [0.407, 0.578]|0/128|0.193 / 0.409|证据不足|
|lapse_logistic_variable|new_precision + common/new_median|0.750 [0.668, 0.817]|0/128|0.107 / 0.214|证据不足|
|lapse_logistic_variable|new_precision + common/new_precision|0.766 [0.685, 0.831]|0/128|0.103 / 0.214|证据不足|
|lapse_logistic_variable|new_precision + pipeline/new_precision|0.766 [0.685, 0.831]|0/128|0.103 / 0.214|证据不足|
|lapse_logistic_variable|new_variance + common/new_median|0.703 [0.619, 0.775]|0/128|0.122 / 0.260|证据不足|
|lapse_logistic_variable|new_variance + common/new_precision|0.719 [0.635, 0.789]|0/128|0.122 / 0.258|证据不足|
|lapse_logistic_variable|new_variance + pipeline/new_precision|0.719 [0.635, 0.789]|0/128|0.122 / 0.258|证据不足|
|lapse_logistic_variable|old_variance + common/new_median|0.711 [0.627, 0.782]|0/128|0.117 / 0.244|证据不足|
|lapse_logistic_variable|old_variance + common/new_precision|0.719 [0.635, 0.789]|0/128|0.115 / 0.241|证据不足|
|lapse_logistic_variable|old_variance + pipeline/old_precision|0.695 [0.611, 0.768]|0/128|0.122 / 0.246|证据不足|
|lapse_logistic_variable|staircase + common/new_median|0.727 [0.644, 0.796]|0/128|0.106 / 0.212|证据不足|
|lapse_logistic_variable|staircase + common/new_precision|0.727 [0.644, 0.796]|0/128|0.108 / 0.201|证据不足|
|lapse_logistic_variable|staircase + pipeline/firth|0.695 [0.611, 0.768]|0/128|0.132 / 0.295|证据不足|
|lapse_logistic_variable|ucb_tvcg + common/new_median|0.570 [0.484, 0.653]|0/128|0.168 / 0.358|证据不足|
|lapse_logistic_variable|ucb_tvcg + common/new_precision|0.578 [0.492, 0.660]|0/128|0.161 / 0.329|证据不足|
|logistic_precise|new_precision + common/new_median|0.820 [0.745, 0.877]|0/128|0.086 / 0.178|证据不足|
|logistic_precise|new_precision + common/new_precision|0.836 [0.762, 0.890]|0/128|0.084 / 0.175|证据不足|
|logistic_precise|new_precision + pipeline/new_precision|0.836 [0.762, 0.890]|0/128|0.084 / 0.175|证据不足|
|logistic_precise|new_variance + common/new_median|0.742 [0.660, 0.810]|0/128|0.111 / 0.220|证据不足|
|logistic_precise|new_variance + common/new_precision|0.742 [0.660, 0.810]|0/128|0.109 / 0.220|证据不足|
|logistic_precise|new_variance + pipeline/new_precision|0.742 [0.660, 0.810]|0/128|0.109 / 0.220|证据不足|
|logistic_precise|old_variance + common/new_median|0.797 [0.719, 0.857]|0/128|0.101 / 0.225|证据不足|
|logistic_precise|old_variance + common/new_precision|0.805 [0.728, 0.864]|0/128|0.100 / 0.222|证据不足|
|logistic_precise|old_variance + pipeline/old_precision|0.820 [0.745, 0.877]|0/128|0.099 / 0.227|证据不足|
|logistic_precise|staircase + common/new_median|0.758 [0.677, 0.824]|0/128|0.102 / 0.219|证据不足|
|logistic_precise|staircase + common/new_precision|0.766 [0.685, 0.831]|0/128|0.101 / 0.213|证据不足|
|logistic_precise|staircase + pipeline/firth|0.750 [0.668, 0.817]|0/128|0.140 / 0.244|证据不足|
|logistic_precise|ucb_tvcg + common/new_median|0.594 [0.507, 0.675]|0/128|0.160 / 0.297|证据不足|
|logistic_precise|ucb_tvcg + common/new_precision|0.570 [0.484, 0.653]|0/128|0.159 / 0.299|证据不足|
|logistic_variable|new_precision + common/new_median|0.812 [0.736, 0.871]|0/128|0.098 / 0.190|证据不足|
|logistic_variable|new_precision + common/new_precision|0.812 [0.736, 0.871]|0/128|0.097 / 0.200|证据不足|
|logistic_variable|new_precision + pipeline/new_precision|0.812 [0.736, 0.871]|0/128|0.097 / 0.200|证据不足|
|logistic_variable|new_variance + common/new_median|0.773 [0.694, 0.837]|0/128|0.099 / 0.187|证据不足|
|logistic_variable|new_variance + common/new_precision|0.773 [0.694, 0.837]|0/128|0.100 / 0.187|证据不足|
|logistic_variable|new_variance + pipeline/new_precision|0.773 [0.694, 0.837]|0/128|0.100 / 0.187|证据不足|
|logistic_variable|old_variance + common/new_median|0.789 [0.710, 0.851]|0/128|0.099 / 0.200|证据不足|
|logistic_variable|old_variance + common/new_precision|0.789 [0.710, 0.851]|0/128|0.098 / 0.196|证据不足|
|logistic_variable|old_variance + pipeline/old_precision|0.781 [0.702, 0.844]|0/128|0.100 / 0.205|证据不足|
|logistic_variable|staircase + common/new_median|0.773 [0.694, 0.837]|0/128|0.099 / 0.210|证据不足|
|logistic_variable|staircase + common/new_precision|0.789 [0.710, 0.851]|0/128|0.096 / 0.196|证据不足|
|logistic_variable|staircase + pipeline/firth|0.781 [0.702, 0.844]|0/128|0.105 / 0.224|证据不足|
|logistic_variable|ucb_tvcg + common/new_median|0.602 [0.515, 0.682]|0/128|0.141 / 0.288|证据不足|
|logistic_variable|ucb_tvcg + common/new_precision|0.602 [0.515, 0.682]|0/128|0.141 / 0.285|证据不足|
|probit_precise|new_precision + common/new_median|0.812 [0.736, 0.871]|0/128|0.098 / 0.201|证据不足|
|probit_precise|new_precision + common/new_precision|0.812 [0.736, 0.871]|0/128|0.096 / 0.200|证据不足|
|probit_precise|new_precision + pipeline/new_precision|0.812 [0.736, 0.871]|0/128|0.096 / 0.200|证据不足|
|probit_precise|new_variance + common/new_median|0.820 [0.745, 0.877]|0/128|0.089 / 0.174|证据不足|
|probit_precise|new_variance + common/new_precision|0.820 [0.745, 0.877]|0/128|0.089 / 0.174|证据不足|
|probit_precise|new_variance + pipeline/new_precision|0.820 [0.745, 0.877]|0/128|0.089 / 0.174|证据不足|
|probit_precise|old_variance + common/new_median|0.734 [0.652, 0.803]|0/128|0.105 / 0.213|证据不足|
|probit_precise|old_variance + common/new_precision|0.750 [0.668, 0.817]|0/128|0.104 / 0.199|证据不足|
|probit_precise|old_variance + pipeline/old_precision|0.781 [0.702, 0.844]|0/128|0.099 / 0.213|证据不足|
|probit_precise|staircase + common/new_median|0.836 [0.762, 0.890]|0/128|0.087 / 0.172|证据不足|
|probit_precise|staircase + common/new_precision|0.859 [0.789, 0.909]|0/128|0.084 / 0.159|证据不足|
|probit_precise|staircase + pipeline/firth|0.820 [0.745, 0.877]|0/128|0.121 / 0.191|证据不足|
|probit_precise|ucb_tvcg + common/new_median|0.648 [0.562, 0.726]|0/128|0.136 / 0.290|证据不足|
|probit_precise|ucb_tvcg + common/new_precision|0.633 [0.547, 0.711]|0/128|0.138 / 0.290|证据不足|
|probit_variable|new_precision + common/new_median|0.836 [0.762, 0.890]|0/128|0.092 / 0.179|证据不足|
|probit_variable|new_precision + common/new_precision|0.852 [0.780, 0.903]|0/128|0.091 / 0.179|证据不足|
|probit_variable|new_precision + pipeline/new_precision|0.852 [0.780, 0.903]|0/128|0.091 / 0.179|证据不足|
|probit_variable|new_variance + common/new_median|0.750 [0.668, 0.817]|0/128|0.104 / 0.224|证据不足|
|probit_variable|new_variance + common/new_precision|0.750 [0.668, 0.817]|0/128|0.103 / 0.218|证据不足|
|probit_variable|new_variance + pipeline/new_precision|0.750 [0.668, 0.817]|0/128|0.103 / 0.218|证据不足|
|probit_variable|old_variance + common/new_median|0.789 [0.710, 0.851]|0/128|0.100 / 0.202|证据不足|
|probit_variable|old_variance + common/new_precision|0.781 [0.702, 0.844]|0/128|0.101 / 0.204|证据不足|
|probit_variable|old_variance + pipeline/old_precision|0.773 [0.694, 0.837]|0/128|0.101 / 0.219|证据不足|
|probit_variable|staircase + common/new_median|0.773 [0.694, 0.837]|0/128|0.096 / 0.198|证据不足|
|probit_variable|staircase + common/new_precision|0.789 [0.710, 0.851]|0/128|0.095 / 0.187|证据不足|
|probit_variable|staircase + pipeline/firth|0.758 [0.677, 0.824]|0/128|0.100 / 0.212|证据不足|
|probit_variable|ucb_tvcg + common/new_median|0.625 [0.539, 0.704]|0/128|0.139 / 0.275|证据不足|
|probit_variable|ucb_tvcg + common/new_precision|0.625 [0.539, 0.704]|0/128|0.139 / 0.287|证据不足|

A层是完整流程；B层是共同新先验估计器。UCB最大Q命令和阶梯反转均值另存诊断，未混入实际边界误差排名。原版BO原生旧先验中位数另存历史参照。
主对比为新精度BO减阶梯，每场景、每层分别进行20,000次参与者配对百分位bootstrap，保存95%及六主场景Bonferroni99.1667%区间；开发拆解仍仅属于开发证据。
不跨场景混池，不将区间包含零解释为等效。共同层另有新精度减新方差、新方差减旧方差的预定次要受控对比。
δ=.10/.20仅改变同一主点估计的评价容限。开发先验/读出拆解是开发证据；整体先验变化不能归因于单独居中。
本结果来自固定、静态合成反应曲线及无额外误差的实际强度测量，不能证明真人、道路安全或TVCG原系统性能。压力条件仅在对应独立输出存在时视为已测试。
