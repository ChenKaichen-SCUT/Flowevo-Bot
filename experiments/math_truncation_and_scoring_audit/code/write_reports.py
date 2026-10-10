from prepare import ROOT,OUT,read,sha
import json

def table(rows,keys):
 return '| '+' | '.join(keys)+' |\n| '+' | '.join('---' for k in keys)+' |\n'+''.join('| '+' | '.join(str(r.get(k,'')) for k in keys)+' |\n' for r in rows)
def save(name,s):(OUT/name).write_text(s.strip()+'\n')
def main():
 s=read(OUT/'summary.json');p=read(OUT/'preflight.json');rs=[json.loads(x) for x in (OUT/'truncation_task_results.jsonl').read_text().splitlines()];cases=[json.loads(x) for x in (OUT/'nine_scoring_cases.jsonl').read_text().splitlines()]
 first,second=s['budget_comparison'][1:3];recovered=s['category_counts'].get('recovered_correct',0);wrong=s['category_counts'].get('complete_math_wrong',0);trunc=s['category_counts'].get('still_truncated',0)
 save('00_EXECUTIVE_SUMMARY.md',f'''# 数学截断恢复与评分修复：实测结论

本轮只修改离线数学评分器，并对同一批历史 500 题中的 27 道截断题提高生成预算。模型、system/user prompt、temperature 和其他生成参数逐请求核对；没有 Skill、BoT、Memory、gold 反思或答案错误重试。

| 口径 | 正确数 | 正确率 | 含义 |
|---|---:|---:|---|
| A | {s['A_correct']}/500 | {s['A_correct']/5:.1f}% | 历史记录 |
| B | {s['B_correct']}/500 | {s['B_correct']/5:.1f}% | 同一批封存输出离线重新评分 |
| C | {s['C_correct']}/500 | {s['C_correct']/5:.1f}% | 将原 27 道截断题替换为预先规定的最后执行档位 |

9 道历史评分假阴性纠正 {s['nine_fixed']} 道，原 464 道判对题没有改判错误或 unknown，其他评分变化为 0。评分修复新增 API 调用为 0；这 {s['nine_fixed']} 道是识别收益，不是模型学习收益。

8,192 档：{first['correct']}/{first['tasks']} 正确，{first['complete_final_answers']} 份完整答案，{first['still_truncated']} 道仍截断。仅依据线上不完整状态选出的 16,384 档：{second['correct']}/{second['tasks']} 正确，{second['complete_final_answers']} 份完整答案，{second['still_truncated']} 道仍截断。最终 27 道恢复正确 {recovered} 道，完整但数学错误 {wrong} 道，仍截断 {trunc} 道。其余类别见 summary.json。

新增 {s['new_calls']} 次真实调用，输入 {s['new_input_tokens']:,}、输出 {s['new_output_tokens']:,}、合计 {s['new_total_tokens']:,} tokens；输出已包含 reasoning tokens，不重复相加。每增加一道正确答案的本轮平均研究成本为 {s['new_total_tokens']/max(1,recovered):,.1f} tokens。

**C 是固定题目集合上的探索性局部替换成绩，不是新执行的标准 MATH-500。** 使用的是本地按学科/难度分层抽取的 500 题，也不是官方标准 MATH-500。请求使用相同模型别名，但服务端后端版本无法固定。增加预算重新采样并非续写原轨迹，本轮没有 4,096 档重采样对照，因此不能把全部增益因果归于预算。

历史“36 道不会解”或“27 道截断所以不会解”均不成立；历史证据分别包含评分错误和答案未完成。仍失败也只能说明该次样本未得到正确完整解答，不能证明模型绝对不具备能力。

原始提交：6acc7335bbe6b731ef3e387d573b6689b90c0550。逐题数据、完整新请求响应、数学复核和代码/数据哈希均在本目录。发布后停止新增实验。
''')
 base=read(OUT/'evidence/baseline_500.json');tr=[x for x in base if x['truncated']]
 save('01_BASELINE_AND_TASK_AUDIT.md',f'''# 基线与任务审计

参考仓库 ChenKaichen-SCUT/Flowevo-Bot，基线提交 6acc7335bbe6b731ef3e387d573b6689b90c0550。原目录 `Flowevo-Bot/experiments/math500_goldfree_20261009/flowevo_bot/`，本轮读取的 manifests、rows、calls、checkpoint 及 500 个 provider sidecars 均已列入 `evidence/baseline_file_hashes.json`。上一发布快照全部文件哈希另存 `evidence/protected_previous_snapshot.json`，收尾逐文件复查，不覆盖历史实验数据或代码。根目录指引.txt 在本轮开始前为空（mtime 04:03 UTC，早于此次附件04:59 UTC）；已保留上一发布版指引和观测到的空状态，再将本轮附件写为当前指引。此文档更新是唯一上一快照文件变更，见 evidence/guide_version_transition.json。

500 个 task ID 唯一且逐一对应；历史正确 464，错误 36；27 道截断与 9 道非截断假阴性互不重叠。全部请求 route=base、skills=[]、retry_count=0，gold/reference_solution 暴露标记均为 false。本历史结果虽然存于 flowevo_bot 目录，但实际未触发策略注入，不能用它证明策略库有增益。

逐个核对了请求哈希、可见响应哈希、ledger/checkpoint 一致性、实际 usage、finish_reason 与旧评分标志。原请求均为 model=deepseek-flash，endpoint=https://api.deepseek.com/chat/completions，temperature=0.0，max_tokens=4096。system 为 `You are an expert programmer and mathematician.`；完整 user prompt 保存在 provider.request，统一要求 step by step 并以 The answer is 结尾。未设置 thinking/reasoning_effort，沿用服务端默认值；新请求也不增加这两个字段。

27 个真实 finish_reason 均为 length，且 completion_tokens 均等于请求上限 4096；并非仅根据输出长短猜测截断。25 道 reasoning_tokens=4096、可见正文为空。另两道如下：

{table([{'task_id':x['task_id'],'visible_chars':len(x['solution']),'reasoning_tokens':x['provider']['usage']['completion_tokens_details']['reasoning_tokens']} for x in tr if x['solution']],['task_id','visible_chars','reasoning_tokens'])}

全部 27 道都未形成完整最终答案，原始完整答案数为 0。对空正文的 25 道可直接确认预算全部耗于 reasoning；另两道分别有少量可见推导，但也在上限处中止。相关数据在 `truncated_27_task_ids.json`、`evidence/baseline_500.json` 和 `truncation_task_results.jsonl`。

**历史日志限制**：500 次的精确 request、provider_model、response_id、usage（含 reasoning token）和 finish_reason 均保留，可见正文也完整保存在 checkpoint/ledger。但原 transport 未保存完整 HTTP JSON 和 reasoning_content 文本；本轮无法还原未保存的隐藏推导内容。新调用同时保存原始 HTTP body 与解析后的完整 JSON。模型别名一致不保证后端 revision 一致；历史也无可供固定的 revision/system_fingerprint。

官方文档来源（2026-10-10 核对）：[请求 API](https://api-docs.deepseek.com/api/create-chat-completion/)、[thinking 模式](https://api-docs.deepseek.com/guides/thinking_mode/)。文档说明 thinking 默认开启，temperature 在该模式下被接受但不生效。本轮仍保留原 temperature 字段，避免混入配置变化。
''')
 explanations={
 'math_test_algebra_673':'40 / 0.02 = 2000；末尾 calories 是题目单位。',
 'math_test_algebra_884':'(3491−60)(3491+60)−3491²=−3600；题目问变化量大小，答案 3600 且明确 less。通用矩形变换验证器另验方向，more 不会放过。',
 'math_test_counting_probability_411':'4×12 / C(52,3) = 48/22100 = 12/5525；参考分母中的逗号及 LaTeX spacing 为千位分组。',
 'math_test_geometry_165':'D 是 BC 中点且与 A/B/C 等距，BC 为直径，∠A=90°；∠C=180−90−50=40°。',
 'math_test_geometry_48':'总面积4，两个阴影三角形面积1和2，百分比为75。75% 与问百分数时的数值75一致，0.75不会直接判成75。',
 'math_test_intermediate_algebra_796':'由奇函数 f(−x)=−f(x)，f(−3)=5 ⇒ f(3)=−5；(3,−5) 为另一必经点。它不等于参考 (0,0)，但可由公开条件直接证明。且一般奇函数定义域未必含0，不能无条件从奇性断言原点属于图像。',
 'math_test_prealgebra_334':'(5×13+7)/6=12 grams；gm 与 grams 为同一单位。',
 'math_test_prealgebra_435':'10×(1/4)=2.50 dollars；金额单位规范化。',
 'math_test_prealgebra_498':'正五边形内角108°，缺口360−3×108=36°；度数表达规范化。'}
 caselines=[]
 for x in cases:
  tid=x['task_id'];caselines.append(f"### {tid}\n\n旧提取：`{x['original_answer']}`；参考：`{x['gold_answer']}`；新评分：{x['new_grade']['correct']}（{x['new_grade']['status']}）。\n\n{explanations[tid]}\n")
 save('02_SCORING_FIX.md','''# 评分器修改与 9 道案例

新版本 `FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py` 继承现有 v2 的平衡括号和数学解析基础，历史版本保留；实验入口 rescore.py 使用新版本。修复前后差异见 evidence/scorer_before_after.diff。评分器中无 task ID 或特定标准答案分支。

最终答案按出现位置选取最后一个明确 marker/boxed，支持嵌套括号。单位规范化依赖公开题目，保留符号、维数、方向和变量顺序；集合与区间、矩阵分别作结构比较；数学解析禁用字符串 fallback。可能涉及有理式约分导致定义域丢失的情况保守 unknown。不同合法图像点由受限的奇偶函数条件证明，并保存 proof。无法解析、缺少必要条件或有歧义时保留 unknown。

对 500 题封存结果重新评分：473 true、27 truncated false、0 unknown。新增纠正仅为原 9 道；旧 464 true 全部保留，没有 true→false/unknown。数学判断证据包含规范化前后、解析对象、差值或公开条件证明，见 evidence/rescored_500_detailed.json。每道的完整原输出/参考推导/usage 在 nine_scoring_cases.jsonl。新增 API 调用 0。

本评分器仍是保守的答案评估器，并非通用数学证明器。与标准答案等价不意味着已机械验证整段解题推导；未覆盖的自由形式答案应复核，不应随意宽松接收。9 个 ID 仅用于以下报告定位，未进入评分算法。

'''+ '\n'.join(caselines)+'''
测试包括未见数值、错误正负号、错方向、单位维数、坐标顺序、集合漏项、区间开闭、矩阵转置、符号恒等式、根号分支、变量分母定义域、末尾更正与未闭合 boxed；另外核对全部 500 题回归和 gold-blind 升级规则。生成前 38 项通过，见 evidence/tests_pre_generation.txt。
''')
 save('03_TRUNCATION_EXPERIMENT.md',f'''# 27 道截断题的真实预算实验

实验预案 preflight.json 与生成代码哈希在调用前冻结。最大 54 个正常请求；两档总输出上界 663,552，输入以每请求 UTF-8 字节数+512 保守预留 55,024，总预留 718,576 tokens。按[官方峰时价格](https://api-docs.deepseek.com/quick_start/pricing/)输入 miss 0.30 美元/百万、输出 1.20 美元/百万估算最多约0.813美元；这是保守价格估算，非账单。当前官方接口最大输出393,216支持8192/16384；未超出本轮用户授权档位和调用数。

原始4096只读历史，无新 baseline 请求。先对全部27题执行8192，只复制原请求并改变 max_tokens。全部第一档原始响应封存后，依据 finish_reason=length 或未能提取完整明确最终答案，封存 escalation_decision.json，再执行16384。第二档参与 {second['tasks']} 道。**没有使用正确性决定升级，也没有在两个档位中按 gold 挑选较优答案。** 最终选择每题最后执行档位。

实际 API 并发上限27（低于64），本地评分12进程，HTTP读取超时600秒；超时配置只影响运输等待，不影响生成参数。无基础设施错误、无重发、无数学错误重试。每次请求先持久化 pending；不确定计费的 pending 禁止盲目重发，已完成请求可从封存结果续跑。

{table(s['budget_comparison'][:3],['group','tasks','complete_final_answers','correct','complete_wrong','unknown','still_truncated','input_tokens','output_tokens','total_tokens','reasoning_tokens'])}

16384 的分母是第一档未完成的子集，不能与8192的27题成功率直接比较。请求响应在 raw/；完整 reasoning_content 是模型内部推理输出，只作离线失败审计，不作为当前题重试反馈。api_calls.jsonl 记录实际 usage，generation_complete_seal.json 证明生成集合封存后才执行独立评分。重新执行分析时不会发起API。
''')
 failure_rows=[{'task_id':x['task_id'],'level':x['level'],'selected_budget':x['selected_budget'],'category':x['category'],'answer':x['selected']['grade']['answer'],'reasoning_tokens':x['selected']['reasoning_tokens']} for x in rs if x['category']!='recovered_correct']
 save('04_FAILURE_ANALYSIS.md',f'''# 剩余失败分类与数学证据

27 道最终分类：{json.dumps(s['category_counts'],ensure_ascii=False)}。

{table(failure_rows,['task_id','level','selected_budget','category','answer','reasoning_tokens'])}

完整且确认数学错误的候选集在 remaining_true_failures.jsonl；包括题目/难度、候选完整解答、gold、原始和新 usage、全部请求来源以及人工数学复核。截断和解析 unknown 不列入“可靠数学错误”集合。

两道剩余题均为 **16,384 reasoning tokens、可见 content 为空、finish_reason=length**，故仍按未完成计分，不从隐藏推理中捞取答案。

- `math_test_geometry_66`：菱形卷圆柱。raw reasoning 反复重审侧边接缝、螺线和圆周/高度关系，多次得到参考数值却没有切换到最终作答。独立核验：圆周6 ⇒ r=3/π，h=6 sinθ，体积6=(54/π)sinθ ⇒ sinθ=π/9。这是观察到的反复推敲和答案未输出，不是已确认不会解。
- `math_test_intermediate_algebra_253`：两条抛物线相切。隐藏推理反复讨论题意，且其疑虑有数学依据。相交条件给出(x−y)(x+y+1)=0，相同切线斜率给出4xy=1。精确求解有 k=1/4、接触点(1/2,1/2)，以及 k=−3/4、接触点(−1/2,−1/2)。后者两斜率均为−1，共同切线y=−x−1，且另有(3/2,3/2)横截交点。代入得到交点方程因式分解(2x−3)(2x+1)^3/16，显示局部三重接触。参考仅列1/4，隐含“唯一接触且不横穿”的意图；按局部微分切触定义，−3/4也成立。此项属于新增的题意/参考歧义标记，**不新增一次评分纠正**，因为模型没有提交最终答案。

这与9道已纠正案例中的奇函数题不同：后者确实提交了能从公开条件证明的合法有序对；这里的两题最终正文都为空。不能把隐藏推理中的某个值追认为最终答案，也不能把参考答案未覆盖的合理解释直接诊断为模型数学错误。

详细数学复核、证据字符位置、原始响应哈希和 SymPy 精确检查见 evidence/manual_math_review.json、manual_review_run.log。参考歧义的新标记为1，评分变化仍为0。`remaining_true_failures.jsonl` 为合法空 JSONL，表示0条可靠完整错误，而不是漏写文件。本次仅诊断，不混入新算法、提示变更或验证器重试。
''')
 save('05_ACCURACY_AND_TOKEN_ANALYSIS.md',f'''# 正确率口径与成本

A={s['A_correct']}/500={s['A_correct']/5:.1f}%；B={s['B_correct']}/500={s['B_correct']/5:.1f}%；C={s['C_correct']}/500={s['C_correct']/5:.1f}%。B−A={s['B_correct']-s['A_correct']}题为纯离线识别收益（0 API）；C−B={recovered}题为新样本恢复，不能解释为模型经过训练学会新方法。

math500_rescored.csv 逐行保存 A/B/C、原/新答案、选用来源、档位、token、model、temperature、代码哈希、基线提交。计数为500个唯一task ID的布尔正确数之和；对于27题仅取最后执行档位，其余473题保留原封存输出的新评分。

原500题实际 input={s['historical500_prompt_tokens']:,}、output={s['historical500_completion_tokens']:,}、total={s['historical500_total_tokens']:,}。本轮新增 input={s['new_input_tokens']:,}、output={s['new_output_tokens']:,}、total={s['new_total_tokens']:,}，其中 reasoning={s['new_reasoning_tokens']:,} 已含在 output 中。实际研究总消耗（历史500+本轮）为 {s['historical500_total_tokens']+s['new_total_tokens']:,}。不能删去未被选中的失败尝试成本。

仅将所选响应拼接后的500条记录 token 合计={s['selected500_total_tokens']:,}，它是记录属性，**不是该流程真实付费成本**。真实采用4096后升级的策略必须计算此前尝试。

每恢复正确一题，本轮平均 input={s['new_input_tokens']/max(1,recovered):,.1f}、output={s['new_output_tokens']/max(1,recovered):,.1f}、total={s['new_total_tokens']/max(1,recovered):,.1f} tokens。8192档成本/恢复题={first['total_tokens']/max(1,first['correct']):,.1f}；在已付第一档成本后，16384子集的新增边际成本/新增恢复题={second['total_tokens']/max(1,second['correct']):,.1f}。后者为条件子集，不能作为全测试集期望值。

固定题目上观察到预算升级有实用价值，但这是一次自适应小样本探索。temperature=0不保证服务端完全确定；第二档中 intermediate_algebra_165 和 prealgebra_131 的输出分别只用7,451和7,414 tokens（低于8192）就完成，明确提示重新采样的轨迹差异。没有新4096对照、后端revision不固定、失败子集为事后选定，不能声称纯预算的因果收益或推广到总体。
''')
 save('06_NEXT_RESEARCH_DECISION.md',f'''# 下一步研究决策

先承认并修复测量问题。原9道评分错误和27道截断不能合并为“模型不会解”。本轮在不改变方法/提示的条件下恢复{recovered}道，证明原先能力不足的归因过早。修复评分器带来的9道收益也不能算作推理算法收益。

目前可靠完整数学错误为{wrong}道，仍截断为{trunc}道。是否研发复杂推理算法，应以这些真实失败机制为依据，当前结果不足以证明 Skill/BoT/Memory 有增益或有必要。

本轮 remaining_true_failures.jsonl 为空，所以当前没有足够依据优先开发复杂数学推理算法。下一步应先针对菱形题研究推理停止/答案完成，对抛物线题明确评测语义；再在独立数据上寻找预算充分且答案完整的真实数学错误。之后若出现有可核验局部错误的完整解答，可以预注册独立失败集，分别研究计算核验、约束检查、多路径/Pass@k及验证驱动搜索；先与等token重新采样、合理预算基线比较，并严格分开训练/验证/最终评测。对于仍截断者，可单独研究推理压缩或显式答案完成；不要将其误记成数学推导错误。

应保留8192及16384预算、重新采样、答案完成机制之间的机制区分。评分器需要独立未知题的正负例验证；受限奇偶函数证明不是通用判定器。MATH这批题已用于诊断，后续confirm应使用未参与调试的封存题。

本轮所有研究和提交完成后停止新增API实验。后续建议不是已执行结果。
''')
 print('Wrote seven reports.')
if __name__=='__main__':main()
