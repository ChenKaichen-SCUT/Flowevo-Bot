from common import *
from collections import Counter

def write(name,text):(OUT/name).write_text(text.strip()+'\n')
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)

def main():
    s=read(OUT/'summary.json');t=s['trace'];c=s['counterfactual'];pilot=s['independent']
    b4=next(m for m in pilot if m['method']=='B4_counterfactual')
    ptable=table(['方法','正确','输入','输出','其中 reasoning','总 tokens'],[[m['method'],str(m['correct'])+'/4',m['input_tokens'],m['output_tokens'],m['reasoning_tokens'],m['total_tokens']] for m in pilot])
    ctable=table(['干预','正确 / 28','未完成 / 28','判错','Unknown'],[[b,c['by_branch'][b].get('correct',0),c['by_branch'][b].get('prediction_incomplete',0),c['by_branch'][b].get('incorrect',0),c['by_branch'][b].get('unknown',0)] for b in 'ABC'])
    sources='''- [DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)
- [Chat Prefix Completion](https://api-docs.deepseek.com/guides/chat_prefix_completion/)
- [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)
- [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)'''
    write('00_EXECUTIVE_SUMMARY.md',f'''# 反事实驱动推理压缩：本轮结论 NO-GO

当前最小原型没有实现净 token 节省，也没有超过简单规则。4 道独立题上，B0 单次高预算和 B4 状态控制器均为4/4，B4却从2008增至3540 tokens（+1532，+76.29%）。这是本次小规模工程结果，不是“所有推理压缩都不可能”的结论；4题也不能证明正确率保持。

重要勘误：用户指引回顾表中的328/605是 FlowEvo 原始提取器成绩，597/605是数学复核成绩。统一冻结V3后，低预算461判对、高预算572判对；高预算历史复核确认597的结论仍保留。旧实验未重跑、未覆盖。

## 十个问题的直接回答

1. 在597条历史复核正确轨迹中，310条有显式候选答案表述；其中 **138条**满足“候选后仍有≥350字符且按全文usage比例估算≥128 reasoning tokens”的预先定义筛查条件。这是可观测语言线索，非数学充分性的认证。605条高低预算 reasoning 均可观察。
2. 主实验20题、28条状态记录（27个不同前缀）、84真实调用：**15/20题**至少一个早期状态经B/C完成且V3判对。与A同状态均判对且后续调用总tokens少≥10%的主实验配对覆盖 **6题、8状态**。补充的真实错误候选控制再增加1题、1状态的此类证据，合计7题、9状态；这是后续调用收益，不是端到端收益。
3. 主实验没有完整B/C答案被V3判错，但 **8/20题**至少有一次B/C未完成；其中1个状态A判对而C截断。因此不能说提前完成没有风险。补充控制的A/B/C均将错误候选14纠正成15。
4. 学到的规则是“显式候选存在且最近三段没有未解决检查的语言标记”。训练集中它与增加检查/约束特征的规则恰好同样触发，未证明更复杂状态特征提供增益；开发原按记录省108个后续调用tokens；最终去重后仅25、1个触发状态，门槛未通过，固定完成规则更好。
5. Beta支持真实文本 reasoning 前缀输入；不是内部KV状态无损恢复。关闭流连接没有最终usage，不能确认取消计费。已实现实际分阶段控制：服务器1024上限结束第一阶段，收齐usage，再按规则继续，完整计入重传前缀与第二次生成。
6. B4相对B0实际输入 **增加1095**、输出 **增加437**、总量 **增加1532**、reasoning **增加515**。没有净节省。最终回答文本少78 tokens也不构成推理压缩。
7. B4总量3540，高于固定/候选规则3512与重复规则3497；无增量优势。
8. 四道未参与设计的新题所有方法4/4；因去重门槛未通过，仅为探索性工程检查；样本过小且仅一题触发B4，不能建立无正确率损失或跨题泛化结论。
9. 存在局部可省略后缀的证据；主要障碍是状态识别没有优于简单完成提示，以及分阶段生成与前缀重传开销抵消收益。长推理并不自动代表可安全截断。
10. **NO-GO：不扩大当前控制器实验，不再跑605或旧MATH-500。** 若另立新研究，先解决状态观察/完成的成本与比简单提示更强的证据，再考虑扩大规模。本轮到此结束。

{ptable}

研究总计 **102次真实HTTP尝试**：84主反事实、3边界修复控制、11独立试验、4API审计（含1取消）。已知usage **299853 tokens**，取消请求精确值 unavailable、保守上界1247，因此总量区间 **299853–301100**，低于350000；调用数低于150。峰值未缓存价格估算已知约USD0.19149，不是账单。

证据索引：`summary.json`、`trace_alignment.csv`、`counterfactual_outcomes.jsonl`、`supplemental_negative_control_outcomes.jsonl`、`independent_results.jsonl`、`api_calls.jsonl`、`token_cost_breakdown.csv`。原始请求、响应、流及逐请求预算记录全部保存。
''')
    write('01_TRACE_ANALYSIS.md',f'''# Stage1：零API历史轨迹对齐

605对 task ID、响应哈希与usage核对一致；两次独立生成，低预算文本从未作为高预算的前缀。历史总量分别687195与1068216，所有记录提供完整 reasoning_tokens；final_content_tokens = completion_tokens - reasoning_tokens。计费子项是API整数，不由字符估计。

统一冻结MathEvaluator-V3后的状态：

{table(['预算','正确','Unknown','判错','未完成'],[['2048',461,19,8,117],['16384',572,19,8,6]])}

高预算V3判对572题中：低预算461判对、105未完成、4Unknown、2判错。高低预算均V3判错6题、均未完成6题；这些分类不是全部数学错误证明。高预算历史复核597正确、2题意/参考歧义、6未完成的记录单独保留。低预算V3未判对没有被自动人工升级为错误或正确。

事件识别仅查看问题和当前可见文本：显式“answer is/so answer”等语句、候选重述、检查语言、未处理检查、重复段落及修正语言。任意与gold相同的数字不算Candidate Formation；没有出现显式短语也不代表实际没有候选答案。事件偏重英语显式措辞，可能漏检隐式推导。

597条复核正确中310条显式候选；138条候选后还有上述较长后缀。筛查使用字符定位和全文已知reasoning token的比例估计，只决定离线文本位置；不冒充截点精确生成tokens，更不作为实际节省金额。最早候选并不等于安全提交点。

`reasoning_events.jsonl`保留605条的来源哈希、字符位置、原始证据和事件置信度。Verification discussion / possible revision是候选事件标签，未自动宣称有效数学验证或冗余。选中轨迹的数学事件复核见`evidence/manual_trace_reviews.jsonl`：例如页码题的000重复扣除被后续检查纠正，说明关键后缀不能简单删除。

完整输入、reasoning、最终文本、输出和总量的分位数，按两种预算与V3状态分别写在`token_length_distribution.csv`。已完成分布统计使用全部605对数据，而非只选成功样本。
''')
    write('02_COUNTERFACTUAL_INTERVENTIONS.md',f'''# Stage2：真实反事实干预

从历史V3与数学复核均正确的轨迹中选20题，每学科5题，覆盖长推理、修正线索、重复、晚候选和中等长度。四个长轨迹主截点约25%，其余约50%；八个额外状态覆盖25%、75%、首个候选后和检查后。28条状态记录在调用前冻结，对应27个不同前缀。12题为发现训练，8题为机制开发；同题所有状态归同一划分。历史题结果不作为独立泛化成绩。

A正常继续，B尽快完成，C仅做必要检查后完成。三者同一题、同一字面前缀、同一DeepSeek Flash与2048新增输出上限、相同默认thinking high、无gold或skill。实际mode为`beta_reasoning_prefix_replay`，前缀传入assistant.reasoning_content、prefix=true；它是文本重放，不是内部状态复原。

{ctable}

15/20题至少一次B/C判对；8题至少一次B/C截断。A也有14/28截断，所以相对历史完整高预算输出的失败并不全是提前完成动作的因果损害；在同状态对照中，`math_test_prealgebra_611__primary`的A判对、C未完成，属于观察到的负迁移。所有完整输出均V3判对；没有Unknown或完整错误。

主实验6题8状态有A与B/C均正确、且后续调用总tokens至少下降10%的配对。A组总量102408，B89649，C96455；这些都包含当前请求的前缀输入。最早成功点是**已测有限截点的反事实oracle**，不是数学上的真正最小状态，也不是在线策略。

## 必须保留的边界修复

人工审计发现页码题`number_theory_536`的“候选后”段落太长：既包含错误候选14，也包含其后纠正为15的枚举。原84次结果全部保留。另在完整句子“So answer14.”后、纠正前补做3次A/B/C调用；原因、原/新截点和请求哈希在调用前写入`negative_control_amendment.json`。没有重训规则、重跑开发门槛或改独立题目。

补充A/B/C均得到15，tokens分别1078、848、765；B仍新增419个reasoning tokens，C新增293个。因此它们并非直接复制错误候选，也不能证明当时14已经足够安全。补充结果单列，合计真实干预29条状态记录（28个不同前缀）87调用、20题；包含补充后，后续调用少≥10%的证据覆盖7题9状态。

没有删除日志冒充节省。原历史轨迹已全部生成，前缀原生成成本没有精确截点usage，故历史“前缀估计+续写”只可作为分析，不用于宣称端到端净节省。
''')
    write('03_MINIMAL_SUFFICIENT_STATE.md',f'''# Stage3：结构化状态与风险

`ReasoningState`只接受问题和已经观察到的前缀，记录当前显式候选、最近步骤、尚未解决的检查线索、验证/约束证据、候选重述和修正线索。完整证据带字符范围；“已完成步骤”代表已出现的步骤文本，不是独立数学认证。观察器不读取未来轨迹、参考答案或评分结果。

训练规则族在看新评分之前固定：candidate_clear、candidate_checked、candidate_constraints、candidate_stable。只在12个训练题的17状态选择零观察到失败、至少2触发、总续写成本下降的规则；若没有合格规则则从不触发。开发8题原有11条状态记录；其中两个位置落在同一前缀，只有10个不同状态。没有重训或调阈值。

获选`candidate_clear`：存在显式候选且最近三段没有未解决检查标记，则使用C；否则A。训练2触发、节省906。开发原按记录2触发、节省108；最终去重后只1个触发状态、节省25。原始结果保留，去重选择每组第一个声明的状态，绝不选择更好输出。增加检查或约束条件在训练恰好同样触发，无法区分它们真正的预测价值；稳定重复条件没有触发。不能将语言上没有担忧当作数学约束已解决。

按原始记录的开发结果：B4为6/11判对、5未完成、35718tokens；固定B为8/11、3未完成、32522tokens。首次候选B为7/11、34987tokens。去重开发B4为5/10、34801tokens，A为5/10、34826tokens；少25而且仅1个不同触发状态，未满足门槛。**没有发现超越固定位置/简单候选规则的跨题特征。**特征选择本身具有训练选择偏差，开发样本也很小。

页码反例揭示：显式候选14是错的，正确计数为15；状态文本可能已局部纠错但未再次使用“answer”措辞，使词法状态滞后。补充真早截点的B/C靠新推理修正14，并不是候选可直接安全提交。结构化状态在这里是可审计的观察记录，不能称作经过证明的最小充分统计量。

文件：`reasoning_state_features.csv`、`early_completion_risk.csv`、`evidence/frozen_controller_rule.json`；全部主反事实预测、状态与tokens在`counterfactual_outcomes.jsonl`。
''')
    write('04_ONLINE_FEASIBILITY.md',f'''# Stage4前置：API可行性实测

文档与2026-10-11（Asia/Shanghai）实测分开记录：

| 能力 | 证据与结论 |
|---|---|
| 观察reasoning | SSE有reasoning_content，能在最终答案前观察文本；不是全部内部计算状态 |
| Prefix输入 | Beta末尾assistant可设置prefix=true并提供reasoning_content；两项nonce测试均返回正确423，证明字段可作为可用上下文 |
| 普通多轮 | 官方说明，无tools的普通后续轮会忽略旧reasoning；本轮不把这种调用当作续接 |
| 强制最终前缀 | Beta content前缀测试被接受；只作为可行性测试，不在主实验单独改变某分支采样配置 |
| 客户端取消 | 在收到47个reasoning字符后关闭连接；未收到[DONE]或最终usage。后端实际停止时刻、实际计费token不可确认 |
| 无损状态续接 | 未证明；没有KV状态句柄或可验证的内部状态恢复，重传前缀会再次计入输入 |
| 可核算替代方案 | 服务器max_tokens完成一阶段，读取最终usage，再发完整记账的续写；已在独立题实测 |

取消测试的精确usage标记unavailable，预算预留输入UTF-8字节上界+聊天封装裕量+128输出上限，共1247。没有用47字符换算成精确token，也没有用关闭socket宣称省钱。

API正常模型返回`deepseek-flash`；实际fingerprint见summary。温度参数在thinking模式不起作用；本轮沿用默认high，未使用种子保证。价格用官方峰值未缓存输入USD0.3/M、输出USD1.2/M作保守估算，不是支付账单。

{sources}

审计证据：`evidence/api_feasibility.json`及`raw/audit_*.json/.sse.gz`。文档列出的功能只作为接口依据，实际控制能力以这里的请求响应为准。
''')
    write('05_COMPRESSION_CONTROLLER.md',f'''# Stage4：实际分阶段控制器

机制门槛在干预前冻结：至少4个状态、2学科存在≥10%的配对续写节省；训练规则改进；开发至少2次触发、没有A正确到非正确负迁移、续写总成本下降。最初按记录计数通过；最终去重审计发现仅1个不同开发状态触发，不足2，故稳健门槛未通过。已经执行的4道新题保留为探索性工程审计，不作为通过门槛的正式独立验证。此统计错误和所有原始记录均公开，没有追加调用或重调阈值。

实现位于`code/online_pilot.py`。每道新题先生成最多1024输出tokens；若自然完成则所有分阶段方法直接采用该响应。若未完成，取已观察reasoning中完整语义边界前的文本，丢弃未完成尾段但仍计入其实际生成成本。观察器仅见此文本。后续请求上限15360，因而每方法最大生成预算1024+15360=16384，与B0相同。

- B0：独立单次16384原始数学Prompt。
- B1：固定第一阶段后使用B完成。
- B2：有显式候选则B，否则A。
- B3：重复线索则B，否则A。
- B4：冻结candidate_clear规则满足则C，否则A。

所有检查都是本地确定性文本规则；无额外LLM检查、无gold、无skill，无正确性触发重试。各方法共享同题真实第一阶段，选择相同A/B/C分支时也共享该实际响应；每个方法的逻辑成本仍完整包含第一阶段+其续写。这样既能配对控制相同状态，也不重复花费完全相同的请求。

12项离线测试包括预算预留、未知取消费用、恢复不重发、前缀不能读取未来、任意数字不是候选、数学边界、空答案usage保留，以及实际两阶段逻辑成本与共享去重。冻结代码、状态、请求与输出的完整性检查单独保存。

B4在独立样本触发1题：`precalculus_141`，第一阶段已生成1024tokens，候选1/9。其余3题自然完成，B4不触发。控制器本地规则四题CPU合计约{b4['controller_cpu_ms']:.3f}ms；使用进程CPU计时，四线程间可能有重叠，不能把这个微小数值当作严格隔离的性能基准。LLM检查调用0，模型二次调用增加1。
''')
    write('06_INDEPENDENT_PILOT_RESULTS.md',f'''# Stage5：独立小规模工程验证

在规则冻结后，从本地MATH测试集筛选无已知直接/近重复研究暴露的题。排除历史注册表、605题、先前500及40题；复用全局近重复筛查并额外对近期题做去数字化文本RapidFuzz≥90筛查。独立指本项目未记录使用，不保证模型预训练未见过。最终去重审计发现原开发门槛重复计算一个前缀，因此已运行的4题降级为探索性工程检查，不能作为门槛合格的正式性能验证。

20题反事实机制研究已消耗288512tokens，剩余保守预算59834。按每题12000tokens的运行前预测，将建议30–50缩至4，每学科1题，固定种子20261011。目标四学科的Level5测试题已被先前605覆盖，因此选Level2、3、4、4；未根据新输出选择题目。所有排除证据、公开问题、标签独立文件及冻结哈希保留。

题目为counting_probability_318（容斥）、number_theory_387（模逆及剩余范围）、prealgebra_409（正整数边界）、precalculus_141（角平分线公式/几何条件）。后两项含边界或需要公式推导的结构；实际仅几何题第一阶段达限。未在观察结果后扩样，故这个验证不是强难题或候选修正行为的充分独立检验。

{ptable}

每方法4/4，负/正迁移均0。B4比B0多1532tokens，比B1/B2多28，比B3多43。增加成本主要来自几何题第二次调用和重传前缀。B0与第一阶段是独立生成，因此不能把B0轨迹视为该第一阶段的未来；相同第一阶段内B1–B4的比较才控制了状态。

只有一题实际触发B4，3题自然完成。不存在足够统计证据证明精度非劣，也不能验证复杂状态规则的普遍作用。`independent_results.jsonl`与`independent_pairwise.csv`保存所有逐题配对；11次物理调用支撑20个方法×题目逻辑结果，共8243研究tokens。
''')
    write('07_ACCURACY_AND_TOKEN_COST.md',f'''# 正确性与成本总账

{ptable}

B4相对B0的“节省”为：输入-1095、输出-437、reasoning-515、总量-1532；负数表示增加。最终文本从628减至550（少78），但这不能抵消推理和重传输入增加。最大输出预算一致不意味着实际成本一致。

| 研究阶段 | 真实请求数 | 已知tokens |
|---|---:|---:|
| API审计 |4（含1取消）|407|
| 主反事实 |84|288512|
| 边界修复负面对照 |3|2691|
| 独立在线试验 |11|8243|
| 合计 |102|299853|

取消请求的精确值不可获得，上界1247单列，因此总量保守上界301100。其余101次正常完成请求全部有API usage。完整已知输入187039、输出112814，其中reasoning99640、最终文本13174；reasoning包含在输出之内。所有实际请求与逻辑方法成本分列，不能把共享方法行再加到研究物理账本。

按峰值、未缓存估计，已知消耗约USD0.19149，取消上界再增加不超过USD0.00150；缓存/非峰时折扣未计，非账单金额。最初用户350000-token硬上限对应全按较高输出单价约USD0.42上界。运行器对活动请求同时预留保守输入上界和max_tokens，未知取消成本持续占用预算。未突破150次/350000tokens。

评分使用完全冻结的V3，无评分器改动。Unknown独立列示，不当作数学错误。本轮主反事实及独立输出没有Unknown；主反事实未完成按失败提交保留，不补用reasoning中的数字当作最终答案。真正取消那次仅是非benchmark可行性测试，不进入数学准确率。
''')
    write('08_MECHANISM_ATTRIBUTION.md','''# 机制归因

1. **可省略后缀存在局部证据。**主实验6题8状态（加负面控制修复后7题9状态）可在相同输入前缀下得到同样正确的答案且后续实际调用总量少≥10%。但这验证文本前缀重放的可完成性，不证明原模型内部状态中整段后缀无用。
2. **候选出现不等于充分。**页码14→15反例有明确数学错误：digit sum4的非负三元组本来不包含000，再减1错误。即便“立即完成”B在更早截点仍用了419个新reasoning tokens进行纠正。它不是零计算的答案抽取器。
3. **简单完成提示解释了大部分观察收益。**主28状态固定B22判对、89649tokens；B4仅14判对、101394tokens。开发B4增加约束类特征没显示独立信息；原按记录的正面门槛还存在重复前缀计数缺陷；去重后未通过，进一步削弱了状态机制证据。
4. **截断与完整错误分离。**B/C没有完整错误，但8题至少一个分支未完成；一处A正确而C未完成。新增输出cap2048可能约束A较长续写，因此不能把B>A的全部差异解释为已识别数学冗余。
5. **在线成本没有下降。**4题B4输入多1095、推理多515；前缀重传和二次生成的开销超过所观察的后缀收益。最终答案文字少78并不是推理tokens减少。
6. **采样与样本局限。**没有独立种子复现，B0与第一阶段各是新生成；共享阶段控制了B1–B4的状态，但不能消除不同提示响应的随机性。历史选择偏向潜在长/重复状态；独立n=4、仅1触发，不足以支撑稳健增益或精度非劣。

本轮没有训练复杂网络、设计Skill Bank、增加通用数学工具、使用gold选择在线动作，或对605题重新跑完整实验。没有将离线oracle或估计前缀长度算成实际节省。
''')
    write('09_NEXT_RESEARCH_DECISION.md','''# 研究决定：NO-GO

不继续扩大当前Counterfactual-Guided Completion Controller。原因是两个实际条件同时不满足：独立端到端计费tokens未低于B0；B4未优于同样分阶段的简单完成、候选和重复规则。最终去重审计还确认：原开发触发门槛重复计数，同一前缀两次采样不等于两个不同状态。已完成的4道新题因此仅作为探索性工程检查。没有通过不断调阈值、换题或修改Prompt寻找正向结果。

这不否认若干历史文本后缀可被省略，也不否认另一种API或控制方式将来可能有效。它说明当前状态线索不具备已证实的额外预测价值，当前工程完成通道成本过高。

若未来另行开展研究，进入更大实验前应先满足：计量可靠且重传更少的完成通道；在新题上超过简单“尽快完成”提示的状态证据；纳入真实错误候选和必要检查的负面控制；用更大独立样本验证精度风险。仅“日志很长”或“4题都答对”不够。

本轮102次请求后停止，不消耗剩余预算做扩样，不运行完整605、旧两批MATH-500、Pass@k扩展或其他新机制。所有旧结果保存，代码、原始请求响应、分析、完整账本和压缩包随本轮提交发布。
''')
    write('README.md','''# Counterfactual-Guided Reasoning Compression

结论与完整索引：[执行摘要](00_EXECUTIVE_SUMMARY.md)。本轮结论NO-GO；研究102次请求、已知299853tokens、取消上界1247。旧605题没有重新生成。

报告00–09依次记录轨迹、反事实、状态规则、API审计、实际控制器、独立验证、成本、归因和决策。机器可读主结果为`summary.json`，最终独立单位审计见`evidence/distinct_state_audit.json`；原门槛重复计数已更正为未通过，4题降级为探索性工程检查。所有物理请求在`api_calls.jsonl`，逐物理预算在`attempts/`，原始流在`raw/`。

运行环境沿用仓库`Flowevo-Bot/.venv`；V3依赖与哈希位于历史`experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json`。归档是工作区研究增量，历史原始轨迹在同一Git仓库保留，不在压缩包中重复拷贝。源码中的ROOT路径按仓库布局解析。

离线检查：

```bash
Flowevo-Bot/.venv/bin/python -m pytest -q experiments/counterfactual_reasoning_compression/code/test_protocol.py experiments/counterfactual_reasoning_compression/code/test_online.py
Flowevo-Bot/.venv/bin/python experiments/counterfactual_reasoning_compression/code/check_artifacts.py
```

按阶段的源码：grade_history → analyze_traces → api_audit → prepare_counterfactual → intervene → grade_and_fit → prepare_pilot → online_pilot → repair_negative_control → final_analysis → deduplicate_audit → write_reports。prepare脚本在已有冻结文件时拒绝重新选题；已封存生成脚本校验结果后复用，不重新付费。不要在发布结果上重新拟合或覆盖分析；如要新实验，应创建新目录和预算授权。

`counterfactual_outcomes.jsonl`是预注册主84次干预；`supplemental_negative_control_outcomes.jsonl`是审计发现段落过长后的3次修复对照，明确未用于重训。独立4题标签从生成进程隔离。`dataset_manifest.json`保留发现阶段冻结版本，独立扩展单列`independent_dataset_manifest.json`。
''')
    print('Wrote ten research reports and README')
if __name__=='__main__':main()
