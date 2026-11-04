# 12–16 人真实车辆 BO 舒适边界 Feasibility User Study 设计

版本：1.0  
日期：2026-08-07  
研究类型：单臂、单次、前瞻性、被试内自适应 feasibility study  
运行平台：同一真实车辆、同一固定驾驶员、封闭或低交通受控路线  

## 1. 决策摘要

### 1.1 SMART 目标

在伦理批准和 Stage 0 execution calibration 通过后，用 8–10 周完成至少 12、至多 16 名有效参与者的真实车辆测试；每人完成 1 个低风险 familiarization probe 和最多 12 个正式 probes，使 BO 闭环完成 target command、车辆执行、传感器测量、乘客反馈、模型更新和下一 command 选择，并判断该流程是否值得进入后续扩大研究。

本轮成功不等于“BO 优于 baseline”。成功表示：

- 真实车辆闭环能按预定协议运行；
- command 与 realized motion 能可靠配对；
- primary acceptability 题干能被理解；
- 个体曲线或边界能被估计、区间化或明确标为 censored；
- 参与者可以有效 preview、skip、stop；
- 不适暴露、运行负担和安全事件处于预设可接受范围；
- 数据结构足以支持下一轮方案修订。

### 1.2 研究不承担的任务

- 不做 BO 与 random/grid/staircase 的真人优效性检验。
- 不报告 population-level efficacy 或普遍安全结论。
- 不把一次 session 的点估计解释为稳定个人特质。
- 不训练历史数据 predictor。
- 不把当前 simulation 的 latent participant 当真人证据。
- 不把 tau 解释成公认舒适标准。

### 1.3 推荐算法地位

首选实现为单调 Bayesian logistic/probit boundary model 加 risk-aware acquisition。若研究团队继续使用现有 kernel 实现，论文和材料必须称其为：

> uncertain-input BO-inspired boundary-seeking policy

只有在二元 likelihood、posterior uncertainty、uncertain-input propagation 和 acquisition 均与代码一致时，才可简称 Bayesian optimization。

## 2. 研究问题与结果层级

### 2.1 Primary feasibility questions

FQ1. 真实车辆中，完整 BO 闭环能否在受控路线和固定驾驶员条件下稳定运行？

FQ2. 参与者是否理解“对未来日常自动驾驶来说可以接受”的 binary question，并能在每次 probe 后快速作答？

FQ3. 传感器、trial marker、target command、feedback timestamp 和算法日志能否在 trial level 一一对齐？

FQ4. 预注册的安全限制、preview、skip、stop 和驾驶员 override 能否被可靠执行？

FQ5. 12 个正式 probes 是否足以产生可解释的个人 acceptability curve、boundary interval 或 censored conclusion？

### 2.2 Secondary questions

- 同一 target command 的 realized motion 变异有多大？
- 两个重复 anchor probes 的 command-realized 重复性和反馈一致性如何？
- 每位参与者经历多少 unacceptable trials、累计不适和最大不适？
- 参与者如何评价 burden、control、trust、safety、personalization 和 willingness to use？
- trial order、previous discomfort、rest duration 和 cumulative discomfort 是否显示明显 carryover？

### 2.3 Exploratory outputs

- individual `B_i(tau)` posterior/credible interval；
- participant heterogeneity 的描述性分布；
- `tau=0.60/0.70/0.80` sensitivity；
- command-to-realized mapping 的 context sensitivity；
- 访谈中关于算法探索、控制权和可接受风险的主题。

## 3. 样本、soft launch 与分析人群

### 3.1 样本目标

- 招募：16–18 人。
- 有效完成目标：12–16 人。
- 最低可接受完成数：12 人。
- 前 2 人为 soft launch。

如果资源上限只能招募 16 人，应预留至少 2 个候补；不应把“招到 16 人”当作“必然得到 16 个有效数据集”。

### 3.2 Soft launch 规则

前 2 人使用完整正式流程。完成后只检查流程，不查看任何比较性“效果结果”来改规则。

以下改动属于 material protocol change：

- primary acceptability 题干或回答选项变化；
- maneuver 类型、command range 或正式 trial 数变化；
- physical safety threshold 或 participant stop rule 变化；
- realized intensity 定义、核心滤波器或边界 criterion 变化；
- anchor 选择规则变化；
- 算法模型或 acquisition 发生影响 command 的变化。

发生 material change 时，前 2 人保留在 feasibility/safety accounting 中，但不与主版本合并估计 boundary 分布，并补招相同人数。只有界面错字、说明顺序或不影响数据生成的日志修复，才允许把 soft launch 纳入主分析。

### 3.3 Analysis populations

- `enrolled_population`：签署同意并进入现场流程者。
- `started_population`：完成第一个正式 probe 者。
- `feasibility_population`：所有 started participants，包括因不适、安全或技术原因提前停止者。
- `boundary_population`：至少有 6 个有效且覆盖至少两个 realized-intensity 区域的正式 probes，且 primary response 可用者。
- `complete_population`：完成全部 12 个正式 probes 者。

提前停止者不得从完成率、安全率或不适暴露统计中删除。boundary model 无法拟合不等于参与者“无效”；它本身是 feasibility 结果。

## 4. 研究平台与最小团队

### 4.1 固定条件

- 同一车辆；
- 同一固定且完成培训的驾驶员；
- 同一受控路线或封闭测试路段；
- 同一 maneuver 方向和大体一致的初始速度；
- 参与者固定座位、坐姿和安全带条件；
- 尽量固定时段、路面和载荷；
- 不在雨雪、能见度差、路面异常或交通不可控时运行。

### 4.2 最小工作人员

1. **驾驶员/安全第一责任角色**：只负责车辆安全和执行 cue；有权否决任何 command。
2. **车内实验员**：知情同意确认、participant monitoring、反馈、stop/skip 和事件记录。
3. **数据/算法操作员**：传感器、marker、算法和数据完整性；最好不承担驾驶任务。

若只能配置两人，驾驶员不能同时操作算法或记录反馈。数据和反馈工作可由同一实验员承担，但需要自动化 logging 和逐 trial checklist。

## 5. Stage 0：无正式参与者的 Execution Calibration

Stage 0 是进入任何真人测试的硬门槛，不计入 12–16 人样本。

### 5.1 目标

- 估计 `P_hat(z|x,c)`；
- 验证 target command 与 realized motion intensity 的可辨识关系；
- 冻结 physical safety envelope；
- 验证 sensor-to-vehicle frame、时间同步、滤波、jerk 和 marker；
- 决定 continuous command 是否可继续，还是改用 calibrated stochastic templates。

### 5.2 Maneuver 和 command 维度

第一轮只研究一种短时纵向 maneuver。不要在同一个 12-trial boundary 中混合 acceleration、deceleration、转弯和复合 maneuver。

Stage 0 后由车辆安全负责人和导师选择 acceleration 或 deceleration 中的一种，依据为可控性、重复性、安全性和研究价值，而不是选择“看起来效果更显著”的方向。

算法 command 使用归一化值 `x in [0,1]`；驾驶员使用经培训的 cue card 或可执行目标。物理单位和映射保存在受控 codebook，不在参与者界面显示精确数字。

### 5.3 重复计划

- 5 个覆盖保守范围的 target commands；
- 每个 command 至少重复 8 次；
- 共至少 40 个 calibration maneuvers；
- command 顺序随机或平衡，不得固定从低到高；
- 记录 driver、vehicle、route segment、initial speed、载荷、天气/路面、trial order 和异常说明。

### 5.4 传感器和信号管线

至少记录：

- monotonic high-resolution timestamp；
- 3-axis accelerometer，目标采样率不低于 100 Hz；
- 3-axis gyroscope，目标采样率不低于 100 Hz；
- 可用时记录 CAN/OBD speed；GPS 仅作为路线/context，不作为精确 jerk 来源；
- command marker、probe start/end marker、feedback-ready marker；
- vehicle/driver override、protocol deviation 和 safety event。

在 Stage 0 冻结：

- device-to-vehicle coordinate transform；
- gravity removal 方法；
- timestamp 单位和 duplicate/drop 规则；
- low-pass filter 类型、cutoff、阶数和相位策略；
- segment window；
- acceleration/jerk 的单位和符号；
- peak、RMS、duration 和 speed change 的计算版本；
- `m(z)` 的一维 realized-intensity 定义。

### 5.5 Stage 0 go/no-go

全部满足才进入 soft launch：

- 0 个未解释的 physical safety threshold exceedance；
- 至少 95% calibration trials 有完整 command-marker-sensor 链接；
- target command 与 realized intensity 的 Spearman 相关至少为 0.70，或五个 target 的中位 realized intensity 至少有四个保持预期次序；
- 同 target 的 realized-intensity 变异可建模；建议把 CV 25% 作为黄色审查线，不作为脱离物理语境的绝对标准；
- jerk、duration 和 speed delta 没有随 target 出现不可接受的异常尾部；
- 驾驶员确认不需要为了追 command 牺牲安全；
- algorithm dry run 能从 calibration distribution 产生合法、受限的 next command；
- marker loss、sensor clipping、坐标错误和滤波异常均有确定处理规则。

若 continuous command 不通过，不允许“带着问题先做真人”。改用经过 Stage 0 校准的 stochastic templates，并在方法中说明 template 是 realized distribution，不是 exact point。

## 6. BO 闭环设计

### 6.1 Canonical variables

- `x_t`：算法给出的 target command；
- `c_t`：route、initial speed、driver、vehicle、trial order 等 context；
- `z_t`：实测 realized motion features；
- `m_t=m(z_t)`：冻结的一维 realized intensity；
- `y_t`：binary acceptability，1=acceptable，0=unacceptable；
- `r_t`：comfort、discomfort、perceived safety、smoothness 和症状等 secondary ratings；
- `P_hat(z|x,c)`：由 Stage 0 得到并在日志中版本化的 execution model；
- `p_i(m)`：参与者个人 acceptability curve。

### 6.2 推荐 response model

首选：

```text
logit P(y_t=1 | m_t, i) = alpha_i - beta_i * m_t
beta_i >= 0
```

或使用等价的 probit 模型。使用弱信息层级 prior 使少量 trial 下仍能估计不确定性，但不得把历史未对齐问卷当作个人标签 prior。

如果单调性在 observed data 中明显不成立，应停止强制输出唯一 scalar boundary，转为报告“当前 session 下的非单调 acceptability observations”或局部 frontier，不用多次 crossing 中任意一个冒充 boundary。

### 6.3 Boundary criterion

主设计 criterion：`tau=0.70`。它是本研究预注册的操作性定义，不是公认生理标准。

```text
B_i(0.70) = sup {m : P_i(acceptable | m) >= 0.70}
```

同时报告 `tau=0.60` 和 `tau=0.80` sensitivity。若 posterior curve 在安全测试范围内未 crossing：

- 全部高于 tau：报告 right-censored，`B_i` 高于已测试安全上限；
- 全部低于 tau：报告 left-censored，并检查题干、baseline 状态和初始范围；
- interval 过宽：报告 not estimable under 12-probe budget。

不允许用插值强行生成一个看似精确的点。

### 6.4 Acquisition

下一 command 的目标是减少 boundary uncertainty，同时惩罚乘客不适和安全风险：

```text
score(x) = expected reduction in Var(B_i)
           - lambda_d * expected discomfort/unacceptable exposure
           - lambda_s * physical and participant safety risk
```

候选 command 必须同时满足：

- 在 Stage 0 physical envelope 内；
- 通过 participant-specific downgrade rule；
- 不违反 driver override；
- 不因追求信息量跨过 hard safety bound；
- acquisition 输出和最终下发 command 都写入日志。

本 study 不声称 risk penalty 具有 SafeOpt 理论保证。

### 6.5 初始化、anchor 和 trial budget

每人最多 12 个正式 probes：

- Trials 1–3：预注册保守初始化。Trial 1 为 low；Trial 2 为 low-medium；Trial 3 只有在前两次未触发 downgrade/stop 时才允许进入 medium。三次都进入 participant model。
- Trials 4–7：算法自适应选择。
- Trials 8 和 12：重复 anchor probes。
- Trials 9–11：算法自适应选择。

Anchor 在 Trial 4 后按预注册规则选择：从 Trials 2–4 中选择最高 target command，要求该 trial `acceptable=yes`、discomfort 不高于 4/7、perceived safety 不低于 4/7，且没有 safety/protocol event。若无符合项，使用 Trial 1 的 low command。

Trials 8 和 12 重复同一 target anchor。重复 command 不等于重复 realized stimulus，因此分析同时检查：

- command-to-realized repeatability；
- realized intensity 差异；
- 在 realized intensity 足够接近时的 binary response 一致性；
- secondary ratings 的绝对差异。

Anchor trials 的 `(z,y,r)` 仍用于更新模型，但其 target 由 protocol 指定，不记作 acquisition-selected trial。

### 6.6 算法异常处理

- 模型或 acquisition 运行失败时，车辆保持安全状态，不执行猜测 command。
- 允许一次由预注册 low command 完成的 recovery check，但必须标记 `algorithm_recovery=true`，且不作为正常闭环成功。
- 同一参与者出现第二次算法失败则结束自适应部分。
- 不允许实验员手工选择 high command 来“补数据”。

## 7. 招募、筛选和参与者保护

### 7.1 Inclusion

- 年满 18 岁；
- 能理解研究说明并自主同意；
- 能按要求乘坐车辆、使用安全带并完成简短问卷；
- 同意短时纵向车辆运动和传感器/问卷数据采集；
- 同意在任何不适时立即报告。

不要求参与者必须高 motion-sickness susceptibility。MSSQ-Short 可作描述性协变量，不应为了“更容易产生效果”而只招募高易感人群。

### 7.2 Exclusion/re-schedule

最终筛选表必须由机构伦理委员会和具备相应资格的安全/医学顾问批准。建议触发 exclusion 或 reschedule 的项目包括：

- 自报严重或未稳定控制的 vestibular、神经、心血管或会使短时车辆运动不合适的状况；
- 当天头晕、恶心、急性疾病、明显疲劳或 baseline 已不适；
- 过去 24 小时大量饮酒、影响判断的物质或剧烈运动；
- 服用可能显著影响清醒、平衡、恶心或反应的药物，且安全审核认为不适合参与；
- 研究参与者、研究者或安全负责人认为当天不宜进行；
- 机构对妊娠或其他特定情况有明确车辆运动研究限制。

不收集不必要的诊断细节。筛选记录只保存 eligibility decision 和必要的风险类别，不把完整病史写入算法数据。

### 7.3 Compensation

- 补偿按到场和时间支付，不与完成 trial 数、是否坚持到高强度或回答内容挂钩。
- 主动退出、研究者停止或技术故障不取消已发生的合理补偿。
- 知情同意中说明交通、误工、研究相关损害处理和联系人。

## 8. 安全与伦理

### 8.1 启动前硬门槛

- 有效机构伦理或科技伦理批准和正式批准编号；
- 受控路线和车辆使用许可；
- 车辆检查、保险和应急方案；
- 固定驾驶员完成路线、cue、override 和 emergency training；
- physical thresholds 由车辆安全负责人签署；
- 知情同意、招募、补偿、隐私和损害处理文本获批；
- 研究登记或备案要求由本机构确认完成。

### 8.2 三方独立停止权

- 参与者：随时 stop/skip，无需解释、无惩罚；
- 驾驶员：因路况、车辆或操作风险取消、降级或停止；
- 实验员：因症状、传感器、协议或算法异常暂停或停止。

任何一方停止优先于算法。

### 8.3 Participant stop/downgrade

以下规则作为伦理提交的建议初稿，批准前由安全/医学顾问确认：

- participant requests stop：立即安全停车并结束；
- participant requests skip：取消当前 command，转入休息；不得重复施压；
- discomfort >= 6/7：停止 session；
- perceived safety <= 2/7：停止高强度探索并由安全负责人决定是否结束；
- 两个连续 unacceptable trials：后续 command range 强制降级；
- MISC 达到机构批准的停止阈值；现有参考协议使用 6，必须由本 study 的伦理版本正式确认；
- 新出现持续恶心、眩晕、冷汗、明显苍白或研究者认为需停止的症状：立即停止；
- discomfort=5/7 或 perceived safety=3/7：至少延长休息，并重新确认是否继续。

### 8.4 Physical safety

Stage 0 冻结：

- `a_safe`：允许的 acceleration/deceleration envelope；
- `j_safe`：允许的 jerk envelope；
- `d_safe`：单 probe 最大 duration；
- initial speed、route zone 和停止距离；
- traffic/weather/road no-go；
- vehicle warning 或 sensor failure no-go。

任何 hard threshold exceedance：

- 立即停止当前 session；
- 标记独立 `safety_event`；
- 不与 `protocol_deviation` 合并；
- 进行 incident review；
- 在安全负责人和必要的伦理 follow-up 允许前暂停后续参与者。

## 9. 单个参与者完整流程

预计总时长 65–80 分钟。

| 阶段 | 预计时间 | 内容 |
|---|---:|---|
| 到场与重新筛选 | 5–8 min | 身份核对、当天健康/用药/饮酒/症状确认 |
| 知情同意和安全 briefing | 8–10 min | 风险、stop/skip、驾驶员 override、补偿、数据 |
| 背景与 baseline | 7–10 min | demographics、乘车频率、MSSQ-Short、MISC、疲劳/焦虑/舒适 |
| 设备与同步 | 5 min | 传感器、marker、反馈界面、seat/seatbelt |
| Familiarization | 5 min | 低强度，不进入正式 boundary model |
| 12 个正式 probes | 25–35 min | maneuver、反馈、休息、算法更新、anchor |
| Post-session questionnaire | 5–7 min | burden、control、trust、safety、willingness |
| Short interview/recovery | 8–10 min | 访谈、最终 MISC、确认恢复、离场条件 |

### 9.1 每个正式 trial

1. 操作员检查 participant status、路况、vehicle state 和算法 command。
2. 向参与者提供必要的 preview；参与者选择 continue 或 skip。
3. 写入 target command 和 pre-trial marker。
4. 驾驶员执行，安全优先，不追求 exact target。
5. 写入 segment end marker；确认车辆稳定。
6. 参与者完成即时反馈。
7. 写入 response timestamp；算法用 realized `z_t` 和 feedback 更新。
8. 至少休息 30–60 秒；根据 reposition、症状和评分延长。
9. 完成下一 trial readiness check。

### 9.2 Familiarization comprehension check

进入正式 trial 前，参与者需能用自己的话确认：

- acceptable 指的是什么；
- 没有正确答案；
- 可以 skip 或 stop；
- stop 不影响补偿；
- 系统会测试不同运动，但驾驶员可以否决算法。

无法理解时重新解释一次；仍无法理解则不进入正式测试，并记录为 feasibility screening failure。

## 10. 问卷和访谈

### 10.1 Remote/arrival screening

采用最少必要信息：

1. 年龄是否达到 18 岁？
2. 是否能够理解研究说明并自主决定参加？
3. 是否有可能使短时车辆加速/减速不适合你的健康状况？若“是”，仅转入安全审核，不要求在普通研究表中写完整诊断。
4. 过去 24 小时是否出现头晕、恶心、发热、急性疾病、严重睡眠不足、大量饮酒或影响清醒的物质使用？
5. 是否正在使用可能显著影响清醒、平衡或恶心反应的药物？
6. 是否能正常使用安全带并乘坐约 80 分钟？
7. 是否愿意在任何不适时立即报告并使用 stop/skip？
8. 机构批准版本的 MSSQ-Short；只作描述性协变量或伦理批准的筛选，不自行改变标准计分。

### 10.2 Background questionnaire

- age band；
- gender（含不愿回答）；
- 每周乘车频率；
- 驾驶频率；
- 过去一年车辆不适/晕动经历频率；
- automated vehicle familiarity，1–7；
- self-rated risk tolerance，1–7；
- 对本次测试的预期焦虑，1–7。

不采集姓名、电话、IP、精确地址进入分析数据。招募联系方式保存在独立 linkage/operations 文件。

### 10.3 Pre-session baseline

- Current MISC：使用经批准的完整量表和 anchors；
- Current physical discomfort：1=完全没有，7=非常严重；
- Current comfort：1=非常不舒服，7=非常舒服；
- Current fatigue：1=完全不疲劳，7=非常疲劳；
- Current anxiety about the ride：1=完全不焦虑，7=非常焦虑；
- 是否希望现在开始：Yes/No。

### 10.4 Immediate feedback after every formal probe

Primary：

> 如果未来自动驾驶车辆在日常道路上以刚才这种方式进行这类纵向运动，你认为这次运动对你来说可以接受吗？

回答：`可以接受` / `不可接受`。不设置中间选项；若参与者确实无法判断，记录 `response_missing_reason=unable_to_judge`，不由实验员代答。

Secondary：

1. Comfort：1=非常不舒服，7=非常舒服。
2. Physical discomfort：1=完全没有不适，7=非常严重的不适。
3. Perceived safety：1=非常不安全，7=非常安全。
4. Smoothness：1=非常突然/生硬，7=非常平顺。
5. 你是否需要更长休息？Yes/No。
6. 你是否希望停止本次实验？Yes/No，始终突出显示。
7. Optional comment：刚才最影响你判断的是什么？

反馈界面目标完成时间不超过 45 秒。正式数据中保存题目版本和响应时长。

### 10.5 Symptom monitoring

- MISC 在 baseline、每 3 个正式 trials 后、任何症状出现时和 post-session 测量。
- 参与者可以随时主动报告，不等待计划提示。
- MISC 不替代 primary acceptability，也不自动定义 boundary。

### 10.6 Post-session questionnaire

全部使用 1–7，并固定 anchors：1=非常不同意，7=非常同意。

1. 回答每次运动后的问题对我来说负担很小。
2. 我觉得自己能够控制校准过程是否继续。
3. 我相信系统没有为了获取信息而忽视我的安全。
4. 我理解系统为什么要测试不同的运动强度。
5. 我觉得系统在尝试了解我的个人接受边界。
6. 如果未来车辆提供这种校准，我愿意使用。
7. 我觉得 stop 和 skip 选项容易找到并且真实有效。
8. 某些 probe 对我来说过于激进。该题反向解释，不隐藏原始方向。
9. 整个 session 的总负担是可以接受的。
10. 现在的 MISC、comfort、discomfort 和 fatigue。

### 10.7 Short interview

固定主问题：

1. 哪一次运动最影响你的接受判断？为什么？
2. 你是如何理解“可以接受”的？
3. 你有没有觉得系统为了学习你的边界而过于冒险？
4. preview、skip 和 stop 是否让你感到有控制权？
5. 如果未来车辆使用这种校准，你希望增加或减少什么？

只追问参与者主动提到的内容，不暗示 BO 应当更好或更个性化。

## 11. 数据架构与 codebook

### 11.1 数据分层

- `linkage/`：姓名、联系方式、schedule 与 participant pseudonym；加密、最小访问权限。
- `raw_sensor/`：原始传感器和 marker，只读保存。
- `raw_questionnaire/`：原始问卷响应，不含直接标识符。
- `algorithm_logs/`：模型版本、posterior/acquisition、candidate set 和下发 command。
- `processed/`：冻结 pipeline 产生的 trial features。
- `analysis/`：分析脚本和聚合结果。
- `codebook/`：schema、单位、anchors、版本和排除规则。
- `incidents/`：安全事件、protocol deviation、technical failure，权限高于普通分析数据。

原始数据不可直接覆盖。每次处理输出记录 source hash、脚本版本和处理时间。

### 11.2 Identifiers

- `participant_id=P001...`；
- `session_id=S001...`；
- `trial_id=T01...T12`；
- sensor sample 使用 monotonic time；
- analysis data 不含姓名、电话、IP、device ID 或精确 GPS route；
- exact route/GPS 仅在受控环境保留，公开数据删除或粗化。

### 11.3 Trial-level table

至少包含：

```text
study_version
participant_id
session_id
trial_id
trial_role                 # initialization/adaptive/anchor
algorithm_version
model_version
acquisition_version
target_command_x
candidate_set_version
command_issued_time
driver_override
override_reason
preview_shown
participant_skip
timestamp_start
timestamp_end
marker_quality
duration_s
rest_duration_since_last_trial_s
trial_order
previous_target_command_x
previous_realized_intensity
previous_discomfort
cumulative_discomfort_before
peak_longitudinal_acceleration
peak_longitudinal_deceleration
peak_longitudinal_jerk
rms_longitudinal_jerk
speed_start
speed_end
speed_delta
realized_motion_intensity
realization_error
acceptable
response_time_s
comfort_1_7
discomfort_1_7
perceived_safety_1_7
smoothness_1_7
needs_longer_rest
stop_requested
misc_score
protocol_deviation
protocol_deviation_type
safety_event
safety_event_type
technical_failure
algorithm_recovery
driver_operator_note
optional_comment
feature_pipeline_version
```

`protocol_deviation`、`safety_event`、`stop_requested`、`participant_skip` 和 `technical_failure` 必须是不同字段。

### 11.4 Participant-level table

```text
study_version
participant_id
soft_launch_status
age_band
gender
passenger_frequency
driving_frequency
motion_sickness_susceptibility_score
risk_tolerance_1_7
automated_vehicle_familiarity_1_7
baseline_misc
baseline_fatigue
baseline_anxiety
session_completed
stop_reason
number_of_formal_trials_started
number_of_usable_trials
number_of_unacceptable_trials
cumulative_discomfort
maximum_discomfort
minimum_perceived_safety
number_of_skips
number_of_driver_overrides
number_of_protocol_deviations
number_of_safety_events
boundary_status             # estimated/right_censored/left_censored/not_estimable
boundary_tau_070
boundary_interval_lower
boundary_interval_upper
anchor_command_repeatability
anchor_response_agreement
post_burden
post_control
post_trust
post_understanding
post_personalization
post_willingness
final_misc
```

## 12. 数据质量和排除规则

### 12.1 Trial usability

一个 trial 进入 boundary model 需要：

- command、start/end marker 和 feedback 可连接；
- primary acceptable response 有效；
- 传感器未 clipping，时间单调，segment 可提取；
- vehicle-frame conversion 和 feature pipeline 成功；
- 没有 hard physical safety event；
- trial 的实际执行与预定义 maneuver 类型一致。

不进入 boundary model 的 trial 仍保留在 feasibility、safety、burden 和 technical failure 统计中。

### 12.2 Missing data

- primary feasibility outcomes 不做数值插补，报告分母和缺失原因；
- secondary rating 缺失不由相邻 trial 填补；
- sensor segment 部分丢失时只允许按预注册 QC 决定 usable，不人工挑选“看起来合理”的区间；
- 因参与者停止造成的 missing trials 不是随机缺失，必须作为 stopping outcome 报告。

### 12.3 Version control

每个参与者 session 开始前记录：

- protocol version；
- questionnaire version；
- algorithm commit/hash 或不可变版本号；
- calibration model hash；
- feature-pipeline version；
- physical-threshold version。

正式 participant 之间不得静默修改版本。

## 13. Analysis plan

### 13.1 Primary feasibility reporting

报告计数、比例和区间，不进行 BO 优效性假设检验：

- recruited、enrolled、started、completed；
- 完成至少 10/12、完成全部 12/12 的比例；
- trial-level command-marker-sensor-feedback join rate；
- usable-trial rate；
- normal closed-loop decision rate；
- algorithm failure/recovery rate；
- participant skip/stop、driver override 和 technical failure；
- protocol deviation 与 safety event 分列；
- median/IQR feedback time、rest time 和 session duration；
- boundary estimated/censored/not-estimable 的人数。

### 13.2 Execution analysis

- target command 与 realized intensity 的 scatter、bias 和 heteroscedasticity；
- realization error 的 mean/median、SD/IQR 和 target-stratified distribution；
- anchor target 的 realized-intensity absolute difference；
- Stage 0 与 Stage 2 `P(z|x,c)` 是否漂移；
- driver override、路况和 initial speed 的描述性影响。

### 13.3 Acceptability and boundary

- participant-level monotone Bayesian logistic/probit curve；
- `B_i(0.70)` posterior median 和 credible interval；
- `tau=0.60/0.80` sensitivity；
- estimated、left/right censored 和 not estimable 分开；
- 不使用历史真实数据制造 ground-truth boundary error；
- 不把 posterior point estimate 当作 test–retest reliability。

如需要描述总体趋势，使用层级模型 partial pooling；N=12–16 时不建议拟合复杂 participant random slope 加多维 acceleration/jerk interaction 并作确认性推断。

### 13.4 Anchor repeatability

- 两次重复 anchor target 的 realized-intensity difference；
- 三次 anchor exposure（原始一次 + 两次重复）的 acceptable agreement；
- realized intensity 在预注册 tolerance 内时计算 percent agreement；
- Cohen's kappa 仅作为补充，因为小样本和高一致性 prevalence 会使其不稳定；
- comfort/discomfort/safety/smoothness 的 absolute difference 和方向。

### 13.5 User cost and UX

- unacceptable count；
- cumulative and maximum discomfort；
- minimum perceived safety；
- maximum realized overshoot，仅在 boundary 可估计时；
- post burden、control、trust、understanding、personalization、willingness 的 median/IQR 和 individual points；
- open-ended interview 采用轻量 reflexive thematic analysis，保留 coding memo 和反例。

### 13.6 Carryover sensitivity

描述或探索性建模：

```text
acceptable/discomfort ~ realized intensity
                        + trial order
                        + previous discomfort
                        + rest duration
                        + cumulative discomfort
```

若时间项明显改变曲线，本轮结论应是“需要 time-aware calibration”，而不是把该效应当作噪声删去。

## 14. Traffic-light progression criteria

Feasibility study 应在看结果前冻结 progression criteria。以下用于决定是否进入下一阶段，不是临床安全标准。

### Green：可进入扩大或比较性研究

- 0 个 serious adverse/safety incident；
- 至少 80% started participants 完成至少 10 个正式 probes；
- 至少 90% started trials 有完整 command-marker-sensor-feedback 链；
- 至少 85% started trials 满足 boundary-model usability；
- 至少 90% 需要 next command 的时点由锁定算法正常给出合法 command；
- 至少 75% participants 的结果为 estimated 或明确 censored，而不是 technical not-estimable；
- post-session burden 的中位数不高于 4/7；
- perceived control 和 perceived safety 的中位数均不低于 4/7；
- 没有反复出现同一种无法由预注册规则处理的 participant/driver override。

### Amber：修改后再次 feasibility

满足安全底线，但任一关键运行指标落在 Green 以下；或 soft launch 后需要 material change；或 boundary not-estimable 主要由 trial range、题干或同步问题造成。

### Red：暂停研究

- serious safety incident；
- 未解释的 physical threshold exceedance；
- stop/skip 未被立即执行；
- 伦理、保险、路线许可或数据泄漏事件；
- algorithm 多次产生 envelope 外 command；
- 参与者不适停止呈集中或重复模式，表明当前 range/休息/流程不适合继续。

Red 事件触发暂停、incident review 和必要的伦理报告；不能用补招参与者来“抵消”。

## 15. 伦理、隐私和来源依据

本研究涉及真实车辆运动、人体参与、问卷、健康/症状信息、算法决策和可能的精确路线数据，应在招募前完成机构伦理或科技伦理审查。

设计依据包括：

- 中国《涉及人的生命科学和医学研究伦理审查办法》要求审查风险收益、知情同意、隐私、招募公平、退出权、补偿和风险应对：https://www.nhc.gov.cn/wjw/c100375/202302/902b4a1dc3af4aba862a6387e6e376dc.shtml
- 中国《科技伦理审查办法（试行）》覆盖以人为测试、调查、观察对象以及个人信息和算法科技活动，并强调透明、可靠、可控和应急方案：https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/gfxwj2023/202310/t20231008_188309.html
- 《中华人民共和国个人信息保护法》适用于自然人个人信息处理；健康、位置和身份数据应按机构解释执行最小化、告知、授权和安全措施：https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html
- 2024 WMA Declaration of Helsinki 强调研究参与者健康、尊严、自主、隐私和权益优先：https://www.wma.net/policies-post/wma-declaration-of-helsinki/
- ISO 2631-1:1997 是 whole-body vibration exposure 的现行已发布 general requirements，ISO 页面说明其仍有效但处于修订周期；本 study 不从网页摘要自行推导 physical thresholds：https://www.iso.org/standard/7612.html
- CONSORT pilot/feasibility extension 强调预先定义 progression criteria；本 study 借用这一原则，但不是 randomized efficacy trial：https://www.bmj.com/content/355/bmj.i5239

物理 acceleration/jerk threshold、医学排除和恢复标准不得由本文件单独决定，必须由车辆安全负责人、伦理委员会和适当的医学/安全顾问结合车辆、路线、速度和机构政策签署。

## 16. 风险登记

| 风险 | 预防 | 触发后的处理 |
|---|---|---|
| continuous command 不可控 | Stage 0 40+ maneuvers、go/no-go | 改 calibrated templates，不做真人试错 |
| 算法产生高风险 command | hard envelope、risk penalty、driver veto | 不执行、记录、算法 review |
| 晕动/不适累积 | baseline、MISC、固定休息、downgrade/stop | 停止、恢复监测、incident record |
| marker/sensor 丢失 | dry run、自动 QC、逐 trial check | trial 标 invalid；重复技术故障则结束 |
| 题干理解不一致 | familiarization comprehension check | 重新解释一次；仍不理解则不开始 |
| realized intensity 非单调 | Stage 0、单调诊断 | fallback templates 或不报 scalar boundary |
| route/context 漂移 | 受控路线、固定 driver/vehicle、context log | pause/mark deviation；不静默合并 |
| PII/GPS 泄漏 | linkage 分离、加密、最小访问、公开前删除/粗化 | containment、机构数据事件流程 |
| 小样本过度解释 | feasibility endpoints、interval/censoring | 不作 efficacy/novelty claim |
| staff role conflict | 驾驶员不操作算法 | 增配操作员或自动 logging |

## 17. 启动前 checklist

### Governance

- [ ] 伦理/科技伦理批准有效且批准编号写入 protocol。
- [ ] 招募、知情同意、补偿、损害处理和隐私文本获批。
- [ ] 路线、车辆、驾驶员、保险和应急许可完备。
- [ ] 研究登记/备案义务已由机构确认。

### Algorithm

- [ ] response model、tau、acquisition 和 candidate envelope 冻结。
- [ ] tau=0.5 midpoint 与 tau=0.70 boundary 不再混用。
- [ ] `P*` 与 `P_hat` 在仿真/验证中分离。
- [ ] protocol deviation、safety event、stop/skip 分列。
- [ ] 算法、模型、calibration distribution 和 pipeline 有不可变版本号。
- [ ] fail-safe、recovery 和 driver veto 通过 dry run。

### Vehicle/sensors

- [ ] Stage 0 go/no-go 通过。
- [ ] vehicle-frame、gravity、filter、jerk、单位和 marker 冻结。
- [ ] physical thresholds 和 no-go conditions 由安全负责人签署。
- [ ] 每日 pre-drive inspection 和 sensor sync checklist 可执行。

### Participants

- [ ] screening 和 baseline 规则获批。
- [ ] familiarization comprehension check 完成。
- [ ] stop/skip 界面和 verbal cue 可立即使用。
- [ ] participant compensation 不依赖完成 trial 数。

### Data

- [ ] linkage 与 analysis data 分离。
- [ ] exact GPS、device ID 和健康信息访问受控。
- [ ] raw data 只读、hash、backup 和 retention policy 生效。
- [ ] codebook、questionnaire version 和 exclusion rules 冻结。

## 18. 交付物

在招募第一人前应具备：

1. 伦理批准版 protocol；
2. recruitment/screening form；
3. informed consent 和 safety briefing；
4. pre-trial、trial-level、post-session 问卷；
5. driver/operator SOP；
6. Stage 0 calibration report；
7. locked BO implementation 和 dry-run report；
8. data dictionary、folder policy 和 privacy plan；
9. incident/deviation form；
10. preregistered analysis 和 traffic-light progression criteria。

研究结束后应产生：

1. participant flow diagram；
2. feasibility dashboard；
3. Stage 0 vs Stage 2 execution comparison；
4. individual curves、intervals/censoring 和 anchor repeatability；
5. user-cost 与 UX summary；
6. qualitative themes；
7. deviation/safety log；
8. go/modify/stop decision memo。

