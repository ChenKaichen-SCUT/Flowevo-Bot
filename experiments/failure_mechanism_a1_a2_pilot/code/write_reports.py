from common import *
import csv,collections,statistics

def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x)for x in row)+' |\n'for row in rows)
def report(name,title,body):(OUT/name).write_text('# '+title+'\n\n'+body.strip()+'\n')

def main():
 p=read(OUT/'pilot_summary.json');a=read(OUT/'evidence/pilot_manual_audit.json');h=read(OUT/'evidence/atlas_summary_verified.json');ds=read(OUT/'dataset_manifest.json');m=p['metrics'];audit=a['posthoc_math_correct_by_method'];physical=p['physical_experiment'];calls=jl(OUT/'api_calls.jsonl');hist=jl(OUT/'historical_records.jsonl');decisions=jl(OUT/'controller_decisions.jsonl');n=40
 standard=table(['方法','V3 正确','V3 Unknown','异常复核后正确','完成率','已返回总 tokens','HTTP 请求'],[[k,f"{v['correct']}/40",v['unknown'],f'{audit[k]}/40',f"{v['complete']}/40 ({v['completion_rate']:.1%})",f"{v['total_tokens']:,}"+(' + 未知≤5,412'if k=='B2+generic'else''),v['calls']]for k,v in m.items()])
 histtable=table(['机制','响应数','不同题数 / 1,031','比例','后续/其他历史分支至少一次正确','未观察到确认正确'],[[x['code']+' '+x['name'],x['records'],x['tasks'],f"{x['task_fraction']:.2%}",x['ever_historical_correct_tasks'],x['no_confirmed_correct_tasks']]for x in h['taxonomy']])
 note='冻结 V3 原始评分完全保留。异常复核仅补充 60 cents 的单位语义和 x=-1 的等价表达证明；未修改答案、标签、评分器或控制器。复核由本助手结合精确算术/SymPy 完成，没有独立人工裁决；其他正确题沿用 V3 证据。'
 budgetnote='本轮有 123 次收到完整响应的模型调用、124 次 HTTP 尝试。已返回 usage 合计 193,828 tokens；1 次 TLS 失败没有返回 usage，额外消耗未知，按请求预留上界最多 5,412 tokens 计入安全预算。总上界 199,240，低于 1,500,000；全部请求计入 200 次上限，未扩大预算。'
 decision='B2：GO（作为下一轮数学主基线，属于 40 题探索性建议）。A1：PARTIAL；A2：PARTIAL（均无触发、无新增正确，不能证明独立价值）。当前不部署或继续复杂化 A1/A2，也不组合 A1+A2。'
 report('00_EXECUTIVE_SUMMARY.md','数学失败机制与 A1/A2 独立试验',f'''
本轮实际完成历史图谱、gold-blind 控制器、40 道独立题的六组比较、异常数学复核和发布验证。此前两批500题、V3评分和460项测试直接复用，未重跑。

{standard}

{note}

数学复核后 B1/B2 都是40/40，B2少3次调用、少1,461 tokens（2.07%）。冻结V3原始统计是B1 39/40、B2 38/40+1 Unknown；这一差异来自正确渐近线的表达形式，没有观察到B2新增数学错误。单次采样与40题不能证明严格非劣。

历史1,031题中，F1候选已形成但未交付至少12题，F2重复验证7题，F3目标漂移1题，F4约束改变1题（额外假设必须精确付款），F5题意歧义2题。没有额外确认独立的算术/推导错误F6；F3/F4是实质答案问题，未重复算作F6，F8仍有68题，不能推断全体不存在数学错误。

A1/A2各触发0题、恢复0题、破坏0题、额外0调用/0 token。普通提醒额外41次HTTP（40份完成响应）、54,135已知tokens+未知≤5,412；异常复核后损失3道正确题，全部是重检查后截断。

{decision}

{budgetnote}

完整证据见01–09报告及JSONL/CSV。实际API峰值64，本地并行12，Gold feedback/Skill injection均OFF。未启动新500题，未调用BoT、SkillBank或RecoveryMemory。
''')
 report('01_FAILURE_MECHANISM_ATLAS.md','历史失败机制图谱',f'''
分析1195份不同响应，覆盖1031道题：第一批500个基础响应、第一批37个预算恢复响应、第二批577个不同预算/同预算对照响应、较早恢复试验81个数学响应（31道训练题）。本阶段模型生成调用为0；保留成功对照，按实际响应ID去重。较早恢复试验采用不同提示，只用于现象发现，不用作本轮无技能预算基线。

{histtable}

以上是**可确认的下界**，不是穷尽人工标注的发生率。主/辅标签及依据均保存在failure_cases.jsonl；重复标签已去重。一题可跨多个响应和机制。最后两列是跨历史分支是否出现过确认正确，不等于固定算法的最终成功率。所有分母均为1031，未仅以失败题为分母。

695/1195份响应保留reasoning_content，涉及558道题；第一批500份基础响应没有保存完整推理文本，因此不能判断其内部候选或循环。411份响应、342道题检出显式候选。F1中只有对已暴露候选进行离线精确类型/参考匹配或复用历史数学证明后才确认；这种正确性证明不能给在线控制器使用。12题中7题在其他历史分支成功、5题未交付确认正确的最终答案。

F2的7题来自5个已有深入审查案例和2个新增文本审查（counting_probability_42、intermediate_algebra_364）。纯“check/wait”或重复段落代理仅标记5题，不能直接当作无效循环：geometry_214虽然反复验证仍正常答对，是成功对照。确认F2的7题中2题随后成功。几何/代数较集中，但样本太少、缺失推理太多，不能推广因果。

F3：number_theory_491把四个连续整数6,7,8,9的和30替换成起点6,11,16,21的和54；可从最终描述观察对象改变。F4：prealgebra_76额外要求精确付款，回答10枚硬币；普通可支付解释只需8枚（总额32.80≥32.75）。若外部另加精确付款要求，10是正确的；因此该约束问题具有语义敏感性，不把它当算术错误。

F5：algebra_1161的非单射逆函数、intermediate_algebra_253的局部相切/唯一接触语义，复用先前精确审查。F7涉及30题31响应，包括旧评分修复和V3指数上限。F8涉及68题，保留不确定性；确认F6为0不表示F8均正确。

候选形成、重复输出和明确对象变化可以在线观察；候选是否真的正确、是否存在数学歧义还需要独立证明。当前证据支持研究A1现象，但尚不能证明控制器有效；A2仅1道明确目标漂移，缺少跨题支撑。

输出：failure_taxonomy.csv、failure_cases.jsonl、historical_records.jsonl、historical_candidate_events.jsonl、repeated_reasoning_cases.jsonl、goal_drift_cases.jsonl、online_observable_features.csv。evidence/stage1_sealed.json保留调用前证据哈希；最终报告汇总由atlas_summary_verified.json复核，个别F7学科/均值聚合修正记录在atlas_reporting_reconciliation.json，未改变封存案例。
''')
 report('02_ONLINE_OBSERVABILITY.md','API行为与实际在线可观察性',f'''
调用前查询只读/models接口，HTTP200，未产生模型生成。官方依据：[Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/)、[Chat completion](https://api-docs.deepseek.com/api/create-chat-completion/)、[Models](https://api-docs.deepseek.com/api/list-models/)、[Pricing](https://api-docs.deepseek.com/quick_start/pricing/)。检索时API说明max_tokens为上限，thinking默认enabled/high；thinking模式temperature不影响采样，保留历史temperature=0不能宣称确定性。top_p继续省略。

本轮B0、B1、B2和提醒请求全部使用同样的SSE传输及stream_options.include_usage。123份完成响应均观察到reasoning_content/content分离返回和实际usage；所有这些响应都有reasoning_tokens明细，该值已包含在completion_tokens中。final_content_tokens=completion_tokens-reasoning_tokens，未把推理重复累加。finish_reason=length判不完整，stop还必须具备可提取的最终答案。

B2在25/40题、41个候选事件中可以定位接收时刻，见pilot_stream_candidate_timing.jsonl及raw/*.stream.json。时间是客户端收到候选片段的时间，不是内部形成答案的时间。连续接收不会自动证明候选正确。B2所有40题最终完成，候选出现未触发任何提前终止。

本轮没有取消流或声称保持隐藏推理状态。A1若触发，会在B2未完成后发送独立短请求，把可见题目、候选和有限文本作为普通上下文；这会重新消耗tokens。普通无工具请求不能把重发reasoning_content当作原始内部状态续接。

历史reasoning不可用的500个基础响应显式标记不可观察。历史F1/F2确认均来自有文本的响应；gold等价证明仅用于离线标注。A2只用题面GoalSpec及提交文本，未访问reference模块或评分结果。匿名化不是本任务需求，原题及模型回答均保留；密钥文件和认证头不进入证据或上传。

一次TLS中断未收到usage，保留pending/error记录后才按用户“部分交付可重跑”要求补跑同一请求；没有变更模型、题目、阈值或思考强度。详见transport_recovery_plan.json和infrastructure_attempts.jsonl。提供方只返回deepseek-flash别名，无法据此固定后端权重版本。
''')
 report('03_HIGH_BUDGET_VS_STAGED_RETRY.md','直接高预算与分级重新生成',f'''
{standard}

B0与B1共享同一4096请求。B1仅由冻结的语法完成检测触发：geometry_75和geometry_232升至8192，后者仍未完成再升至16384。3次新增请求，全部从头生成，未加入gold、失败解释或技能。B2从同样基础提示直接以16384上限求解40题；与B0随机交错调度。

复核后B2相对B1新增正确0、丢失正确0；相对B0新增正确2、丢失正确0。冻结V3的B2相对B1为0新增/1未确认（precalculus_47，实际等价式正确）；必须区分模型损失与解析损失。

B1为43调用/70,577tokens，B2为40调用/69,116tokens，节省3调用和1,461tokens（2.07%）。B2平均每题实际1727.9tokens，未因16384上限用满额度。总output：B1 64,360，B2 63,719；B2比B0的38,123更高。直接预算仍可能出现长验证轨迹，例如intermediate_algebra_349和geometry_232；没有证据说它能完全消除过度推理。

请求彼此独立，thinking温度参数不提供确定性。没有运行额外随机种子，差值较小，不能把所有轨迹差异归因于预算。没有额外运行可选单次8192，避免在本轮添加非必要分支。普通提醒的额外4096上限只是固定对照条件，不代表全体自检方法。

建议B2作为下一轮最简单主基线，B1保留低首轮预算场景和独立重采样对照。没有覆盖历史实现或全局切换所有任务默认预算。
''')
 report('04_ANSWER_FINALIZATION_A1.md','A1：候选答案与完成控制',f'''
新增实现位于FlowEvo/src/math_control/candidates.py和prompts.py。只从API实际返回的reasoning文本提取boxed/显式answer或result标记，使用冻结V3公共解析层确认类型，限制候选长度与解析时间；不导入评分engine、reference或equivalence。

预先冻结门控：B2未完成；候选位于文本后半段；相同类型候选重复≥2或明确boxed；公开目标解析不能不确定或显示高可信对象冲突。即使满足门控，也只发送一次新的4096上限完成请求，明确候选未验证，不直接把候选计为答案。未把所有题统一加一句催促作为A1。

B2候选识别25题/41事件；触发0题，恢复0，破坏0，新增正确0，额外API0、tokens0。提前终止、正确/错误提前完成、原可正确而被打断均为0，因为实现不执行流中止。

新的未完成响应中，离线可定位正确候选的5份记录涉及3题（geometry_75、geometry_232、precalculus_47）；它们属于低预算/分级中间层或Generic分支，详见new_failure_mechanisms.jsonl。B2已经完整交付这3题，故不能用其他分支的事后候选给A1记恢复功劳，也没有给这些响应额外补发A1请求改变实验协议。

B2+A1与B2相同，复核后40/40；缺少新题实际触发和恢复证据。结论PARTIAL，当前部署NO-GO；本轮不继续增加候选阈值或额外调用来追求正结果。对错误中间结果的风险只做了协议/单测验证，没有真实触发样本可估计概率。
''')
 report('05_GOAL_CONSISTENCY_A2.md','A2：公开目标一致性',f'''
GoalSpec包含target_object、target_operation、target_variables、domain_constraints、quantity_constraints、answer_cardinality、unit_requirements、required_output_type，另保留请求句及解析置信度。实现基于题面规则，不调用模型抽取，不读标准答案。具体输出见goal_specs.jsonl。

Checker支持明确连续整数对象被起点替换、显式集合基数不符、明确请求单位/数制或实数域违规。它是保守的有限规则覆盖；“无高可信冲突”不等于全面数学验证，也没有实现通用语义级变量/所有存在性问题判定。解析不确定时不修复。

开发历史发现两次有效单位后缀误触发：题面给出单位不代表最终目标要求该维度；面积题的线性长度单位尤其易误判。已在试验前把单位触发限定为目标句中显式要求，并加入正/负回归。该修正没有使用独立40题结果。

新40题中目标漂移确认0、触发0、恢复0、误改0、额外调用0、tokens0。B2+A2复核后40/40，全部复用B2。Generic为37/40并损失3道已正确题，这只能说明本轮无条件重新检查存在风险，不能证明从未触发的结构化A2修复优于简单提醒。

历史明确F3仅number_theory_491一题；F4精确付款约束例并未被当前Checker捕捉。没有多道独立新题的目标修复证据，结论PARTIAL，当前部署NO-GO。A1/A2都未单独产生正向恢复，因此没有运行组合。
''')
 report('06_INDEPENDENT_PILOT_RESULTS.md','独立40题与执行完整性',f'''
从本地MATH测试集固定种子{ds['seed']}抽取40题，7个学科，14道一般难度（每科一题Level1–2、一题Level3）、26道Level4–5。没有按模型失败结果挑题。复用旧训练题/历史使用排除与全局近重复筛查，并补筛最近500题的公开题面；本轮新增候选池{ds['eligible_after_new_screen']}题。所有7500训练题及已知旧实验题保守排除，近重复阈值/分层清单见dataset_manifest.json。

这40题是此前未用于A1/A2设计的开发验证题，不是标准MATH-500，也不是随机500测试的可替换总体。约束基于现有公开使用记录，不能排除基础模型预训练见过MATH；这种污染未知不伪装成无污染。

{standard}

{note}

基础系统提示仍为“You are an expert programmer and mathematician.”，用户提示保留原native cot模板。DeepSeek Flash默认enabled/high thinking，temperature历史0保留但不当确定性保证，top_p省略。Gold、Skill、BoT和RecoveryMemory关闭。

{budgetnote}

TLS失败只补跑一个无完整响应的Generic请求。其余122份已完成响应均复用；已有39个Generic响应和全部B0/B1/B2不重跑。普通请求的数学length结果是已执行完的预算条件，保留为实验结果，未因看到标准答案而重试。

所有生成于ALL_GENERATION_SEALED.json封存后才加载offline_labels评分。只跑了本轮新增26项控制/隔离/预算单测和12项结果完整性检查，共38项通过；旧460项直接复用原记录。首轮新增测试发现1个单位误触发，修复后只重跑受影响项，保留失败及修复日志。

历史6572个受保护文件哈希不变；唯一授权内容替换是根目录指引.txt。冻结V3配置及源码哈希保持一致。新增public parser bridge绕过V3包入口的eager grading imports，只开放公共解析模块。
''')
 costs=table(['方法','输入','输出（含推理）','其中推理','最终正文','已知总量','请求数'],[[k,v['input_tokens'],v['output_tokens'],v['reasoning_tokens'],v['final_content_tokens'],v['total_tokens'],v['calls']]for k,v in m.items()])
 pairs=table(['左侧 vs 右侧','冻结V3新增/丢失','异常复核新增/丢失','已知token差','请求差'],[[k,str(v['gains'])+'/'+str(v['losses']),str(len(a['posthoc_paired'][k]['gained']))+'/'+str(len(a['posthoc_paired'][k]['lost']))if k in a['posthoc_paired']else'见逐题文件',v['tokens_difference'],v['calls_difference']]for k,v in p['paired'].items()])
 report('07_PAIRED_ACCURACY_AND_COST.md','逐题正确率与实际费用',f'''
{costs}

{pairs}

各方法统计是假想单独部署该策略的完整请求成本：B1包括B0，A1/A2/Generic包括B2。共同初始响应实际只调用一次，因此不可将六行相加作为实际支出。真实物理执行123个完整响应合计193,828 tokens；另一次TLS失败有usage不确定性≤5,412，HTTP总计124。

B2+Generic表内已知总量123,251，含1次无usage的请求后范围为[123,251,128,663]；其他五方法没有此不确定性。Generic额外54,135已知tokens，上界59,547；41次额外HTTP中40次返回完整响应。

USD估计按官方峰值未缓存输入$0.30/M、输出$1.20/M，B1约$0.07910，B2约$0.07808。此处是费率估计，不是账单，未断言cache或off-peak折扣。实际usage统计优先于估计。

原始V3配对：task_pairwise.csv。异常数学复核配对：task_pairwise_adjudicated.csv；二者不混为一个分数。B2与B1的唯一原始差异来自precalculus_47表达解析。无重复随机种子，配对符号检验仅探索性；0新增/0损失不证明严格非劣，40/40也不表示真实错误率为0。
''')
 report('08_FAILURE_AND_NEGATIVE_TRANSFER.md','失败、评分错误与负迁移',f'''
本轮B2完整40题，未确认真实解题错误。冻结V3有两个异常题：

- prealgebra_66：0.05*(60-48)*100=60 cents；模型正确。V3没有从“how many more cents”识别请求单位，导致currency quantity与裸数字参考类型不符。B0/B2/Generic的三份实际响应均保留incorrect原分数，另附精确复核。
- precalculus_47：x=cos(2theta)趋于-1而y=cos(2theta)tan(theta)发散，渐近线x=-1。B2正确给出x=-1及r*cos(theta)=-1的等价形式；V3拒绝括号说明，保留Unknown。

新发现已写入posthoc_adjudications.jsonl，没有修补本轮冻结评分器，也没有回头重跑生成来让格式更适合评分。

低预算geometry_75、geometry_232没有完整输出；B1/B2均补足。Generic却把B2已完成且数学正确的geometry_75、geometry_232、precalculus_47再次带入验证，4096上限内未给正文答案，数学复核后净损失3题。

geometry_75的显式CN=4与Asy的N=(5,0)坐标冲突，Generic反复讨论图示与文字；正确的文字条件解为240/13。geometry_232反复检查无滑动位移符号，候选55mm已出现；precalculus_47反复检查极坐标/直角坐标等价形式，候选x=-1已出现。new_failure_mechanisms.jsonl保存原位置和上下文，5份未完成响应/3道题可见正确候选，2份Generic响应有明显重复验证，1题有图文冲突。

Generic采用额外4096上限的新请求并选择其最终输出，没有“失败时保留原正确答案”的隐藏兜底。因此负迁移同时受额外重采样和修复预算限制影响，不能推广为任何自检提示都会更差。当前证据反对无条件替换已完整的B2回答；无需新增复杂控制器即可避免这三次退化。

A1/A2从未真实触发，观测误改0并不证明触发后安全。历史错误率低、当前题集接近上限、评分器覆盖仍不完备，是研究结论的重要限制。
''')
 report('09_NEXT_RESEARCH_DECISION.md','Go / No-Go 与研究停止点',f'''
{decision}

1. 默认预算建议：在下一轮数学比较中优先使用单次16384上限。数学复核后B2/B1均40/40，B2请求更少、实测tokens少2.07%。保留原始V3 38与39的差异和其解释，不据40题宣称稳定领先或统计非劣。本轮没有修改冻结历史实现或对其他任务做全局配置变更。
2. 分级重新生成仍保留为低首轮成本模式、截断补救和独立重采样对照；40题不足以排除多次采样在更难题上的收益。
3. A1有历史跨题现象支持，但B2已解决本轮全部完成问题，0实际触发/恢复，缺少独立算法价值证据。暂不继续工程复杂化。
4. A2只发现一个明确历史目标漂移，新题无再现，规则覆盖有限，0实际修复。暂不部署，不通过放宽阈值或挑历史失败题制造收益。
5. 当前剩余可观察问题是低预算/重复检查的交付失败、图文不一致、评分解析/单位接口缺口；B2本轮没有观察到真实数学错误。F8历史记录仍未完全解释，不能宣称数学任务已解决。
6. 下一轮若获授权，应先补足评分器cent单位和等价式列表的通用规范与独立回归，再做预注册的独立配对验证并提高更难数学题比例/来源多样性；冻结新评分口径后验证，避免在本轮结果上反复调参。当前不再扩到新的MATH-500，不运行更多预算档位或控制器组合。

本轮停止于研究交付与GitHub提交核验。此前完整工作直接复用，唯一补跑是TLS中断的未交付请求；没有根据gold补跑任何数学答案。
''')
 # A separate paired view prevents silent overwriting of frozen V3 scores.
 rows=jl(OUT/'adjudicated_task_results.jsonl');rm={(r['task_id'],r['method']):r['math_correct_after_exception_audit']for r in rows};prs=[]
 for key,v in a['posthoc_paired'].items():
  left,right=key.split(' vs ')
  for tid in sorted({r['task_id']for r in rows}):prs.append({'task_id':tid,'left':left,'right':right,'left_math_correct':rm[tid,left],'right_math_correct':rm[tid,right],'difference':int(rm[tid,left])-int(rm[tid,right]),'basis':'frozen_V3_plus_explicit_posthoc_exception_audit'})
 with(OUT/'task_pairwise_adjudicated.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(prs[0]));w.writeheader();w.writerows(prs)
 save('research_decisions.json',{'B2':'GO_as_next_exploratory_primary_baseline','A1':'PARTIAL_no_independent_trigger_or_recovery','A2':'PARTIAL_no_independent_trigger_or_recovery','deploy_more_complex_A1_A2_now':False,'run_combination':False,'expand_to_500':False,'global_existing_defaults_changed':False,'stop_after_publish':True})
 manifest={'at':now(),'reference_commit':REF,'repository':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot','guide_sha256':sha(OUT/'USER_GUIDE.txt'),'stages_completed':[0,1,2,3,4,5,6,7],'dataset_tasks':40,'physical_generation':physical,'models_and_runtime':read(OUT/'config.json'),'code_freeze_sha256':sha(OUT/'evidence/pre_api_freeze.json'),'generation_seal_sha256':sha(OUT/'checkpoints/ALL_GENERATION_SEALED.json'),'V3_config_hash':read(OUT/'evidence/pre_api_freeze.json')['v3_config_hash'],'V3_results_sha256':sha(OUT/'pilot_v3_results.jsonl'),'frozen_scores':{k:v['correct']for k,v in m.items()},'posthoc_math_correct':audit,'exception_audit_not_independent_human':True,'tests':{'new_unique_passed':38,'prior_passed_reused':460,'previous_tests_rerun':False,'unit_report':'evidence/new_test_results.json','artifact_report':'evidence/artifact_tests.xml'},'reuse':read(OUT/'evidence/reused_work.json'),'historical_hashes':read(OUT/'evidence/historical_hash_verification.json'),'decisions':read(OUT/'research_decisions.json'),'publication':'authorised; final remote commit returned separately to avoid self-referential hashes','new_code_components':['FlowEvo/src/math_control','experiments/failure_mechanism_a1_a2_pilot/code'],'artifact_indexes':['failure_taxonomy.csv','task_results.jsonl','task_pairwise.csv','task_pairwise_adjudicated.csv','api_calls.jsonl','cost_breakdown.csv','dataset_manifest.json','posthoc_adjudications.jsonl'],'infrastructure_usage_caveat':budgetnote}
 save('run_manifest.json',manifest)
 report('README.md','Failure Mechanism / A1 / A2 Pilot', '''入口：[研究摘要](00_EXECUTIVE_SUMMARY.md)。原始V3与异常复核分开保存；使用data/public_prompts.jsonl生成，全部封存后才读取offline_labels.jsonl。历史6572文件保持不变，旧实验/460项测试复用。

完成后再次执行run_pilot.py只复用封存结果，不会产生API请求。不要删除raw/checkpoints或封存文件以强行重跑。程序默认对未知计费中断停止；本轮一个TLS失败由用户明确授权、保留预留上界后通过recover_transport_and_seal.py补跑。该补跑只允许一项同请求、评分前执行。

可复核顺序：stage0.py → prepare_dataset.py → build_atlas.py → reconcile_atlas.py → complete_atlas_review.py → verify_atlas_reporting.py → 新增单测 → preflight.py → run_pilot.py → 必要且经授权的transport恢复 → analyze_pilot.py → audit_new_cases.py → artifact完整性测试 → write_reports.py。已有封存结果优先读取；stage0针对参考HEAD，已发布后不应重新把当前HEAD当成旧参考版本。

候选检测/GoalSpec位于FlowEvo/src/math_control；冻结评分器没有变更。报告及JSONL保留实际usage和1次TLS失败的未知用量上界，不能把上界冒充实测值。''')
 print({'reports':10,'new_tests_passed':38,'physical_tokens':physical['actual_unique_tokens'],'math_correct':audit})
if __name__=='__main__':main()
