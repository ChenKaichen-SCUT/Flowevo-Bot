"""Render evidence-backed research reports; no inference or network usage."""
import csv,json
from pathlib import Path
P=Path(__file__).resolve().parents[1];PROJECT=P.parents[1];EXP=PROJECT/'experiments/math500_goldfree_20261009'
R=P/'reports'
def load(path):return json.loads(Path(path).read_text())
def readcsv(path):
 with Path(path).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(name,text):(R/name).write_text(text.strip()+'\n')
def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(x).replace('|','\\|').replace('\n',' ') for x in row)+' |' for row in rows)+'\n'
def fmt(v):return 'missing / 未执行' if v is None else str(round(v,3) if isinstance(v,float) else v)

def main():
 skills=load(P/'data/skills_full.json');stats=load(P/'data/evidence/skill_statistics.json');notes=load(P/'scripts/quality_notes.json');summary=load(P/'data/audit_summary.json');examples=load(P/'data/evidence/trigger_examples.json')
 sources={t['problem']['task_id']:t for t in load(P/'data/evidence/source_traces.json')}
 report='# 全部 12 个真实 Skill\n\n原始来源：`experiments/math500_goldfree_20261009/real_bank.json`。本文件不生成、改写或补全策略。S01–S12 是按原 bank 顺序添加的审计编号，原 ID 保留。下方完整 JSON 保留全部字段、完整 provenance 和每条开发配对记录；原始缺失字段应标 missing，而 null optional_executor 表示已知没有执行器。\n'
 for i,s in enumerate(skills,1):
  sid=f'S{i:02}';st=stats[sid]
  report+=f"\n## {sid} · {s['name']}\n\n```json\n{json.dumps(s,ensure_ascii=False,indent=2)}\n```\n\n"
  report+=f"来源 {st['source_n']} 题，均为 train-build 首轮轨迹；标准化题面不同数 {st['source_normalized_unique']}，明显近重复对 {st['source_near_duplicate_pairs']}。多题来源成立；是否在数学结构上独立不能仅据文本不同判断。源码没有单独的 human_verified_math_quality 字段：missing。\n\n"
  report+=f"来源自匹配 {st['source_matches']}/{st['source_n']}；开发同学科/Trigger/前置/排除/eligible/实际调用：{st['dev_subject']}/{st['dev_trigger']}/{st['dev_precondition']}/{st['dev_negative_excluded']}/{st['dev_eligible']}/{st['dev_actual_uses']}。base正确 {fmt(st['base_correct'])}，skill正确 {fmt(st['skill_correct'])}。首阻断：`{st['first_rejection_gate']}`。\n\n"
  report+='学习记录：初次12个蒸馏均失败（9截断、3特征不合法）；第二次12个均通过 schema、词汇及长度检查。每条最终卡使用5或6条轨迹，直接生成compact文本，未见独立压缩调用。实际预算实验没有执行合并重蒸馏；duplicate_candidates=[]。config merge_duplicates=true 不能当作已发生合并的证据。\n\n'
  report+='来源题面及模型首轮解答完整保存在 `data/evidence/source_traces.json`：\n\n'
  for tid in s['source_task_ids']:
   report+=f"- `{tid}`（{sources[tid]['problem']['subject']}）：{sources[tid]['problem']['problem']}\n"
 save('01_ALL_SKILLS.md',report)
 report='# Skill 抽象质量逐条审查\n\n质量判定与 schema 合规分开：12/12 schema合规，0/12获得足够证据证明可靠、经济的跨题复用。S04/S06/S07值得保留核心再验证，不是合格 active 的认定。所有有效性判断都标 insufficient_evidence 或单次观察。\n'
 for i,s in enumerate(skills,1):
  sid=f'S{i:02}';n=notes[sid];st=stats[sid]
  report+=f"\n## {sid} {n['name_zh']}\n\n**诊断：** {n['assessment']}。\n\n**具体性、宽泛性与粒度：** {n['specificity']}。没有证据表明任一条只记忆单题答案；问题更多是多个策略的菜单式聚合和过窄词面条件。\n\n**适用性与数学条件：** {n['math']}。\n\n**原始证据：** {n['evidence']}。原卡原文见01报告，完整来源见source_traces。\n\n**成本潜力：** 独立使用 {st['dev_actual_uses']} 次；每次平均节省 {fmt(st['mean_saving'])} token，正数才表示节省。完整卡没有可执行算子（optional_executor=null），目前增加的是提示，没有直接消除API调用的机制。\n\n**未验证疑点：** {n['uncertainty']}。实质结构泛化：insufficient_evidence。\n\n**下一步：** {n['priority']}。\n"
 report+='''
## 重复性与组合

S10/S11为跨学科的同一“精确有理/循环节归一化”家族；当前 duplicate 先检查 subject 相同，因此不会合并它们。S01/S02/S07/S08均有二次式/代换工具重叠，S05/S06共同采用几何转方程，但不能把这种重叠当作可无损合并。基于完整原卡逐条审读，未见12张卡完全相同。

理论上“定义域核验→有理式变换”和“同一具体几何构型→代数求解”可组合，前提是变量、目标与域条件兼容；不能叠加多个宽泛工具菜单。原实现要求 `candidate.strategy_pattern in selected.composition_tags` 且反向成立，而本批 strategy_pattern 是长描述、tags 是短关键词，66对候选中0对兼容。默认 max_injected_skills=1，本次不会触发组合分支；这是潜在数据契约问题，不是此次零复用的主因。

S04 的对称商反例是本轮纯本地构造的数学核验，不是新增模型数据：3位二进制标号串8个，旋转轨道4个，不能直接8/3。它证明缺条件的普适写法有风险，不证明现有18对执行中发生了该错误。S12 的两个失败是评分/截断事件，不应记为两次数学推理错误。
'''
 save('02_SKILL_QUALITY_REVIEW.md',report)
 report='''# Admission 逐关诊断

入口 `src/flowevo_bot/skill_validator.py:SkillValidator.admit`；配置来自真实实验 config.json，而非默认示例。阈值来源：项目配置与程序常量；没有找到以独立数据校准这些阈值的记录（missing）。本次离线重放12/12与历史状态一致，没有发现状态计算结果与代码不一致。

执行顺序：

1. 需要独立证据：independent=true、evidence_hash正确、pairwise非空。空列表即 quarantine。
2. 任何 base_only_correct>0 即 quarantine。
3. 来源至少3、来源provenance/哈希数量有效、dev至少10、structurally_distinct_cases>0，否则shadow。
4. 平均节省的正态近似95%下界>0，并且平均节省×expected_future_uses(100)>sum(token_stats)，才可active；否则shadow。
5. active还要取得与字段内容绑定的证书。

这些判断是顺序短路的；下表是首次阻断，JSONL同时保留后续可计算门槛。无执行数据时，原始统计的0不等于测得零收益，导出均值/净收益留空并写unknown。

'''
 rows=[]
 for i,s in enumerate(skills,1):
  k=f'S{i:02}';x=stats[k]
  rows.append([k,x['source_n'],x['dev_actual_uses'],f"{fmt(x['base_correct'])} → {fmt(x['skill_correct'])}",fmt(x['mean_saving']),fmt(x['estimated_net_saving']),x['first_rejection_gate'],s['status']])
 report+=table(['ID','来源','dev对数','base→skill正确','每次节省token','100次预计净节省','首次阻断','状态'],rows)
 report+='''
首次阻断互斥统计：独立证据为空8个、观察到harm1个、dev样本不足1个、正节省下界不成立2个。解释分类：8个应归入覆盖/证据不足，不是已证伪的低质量数学规则；S07为n=1样本不足；S04/S06已观测到平均增加token；S12由一例评分假阴性及一例截断触发harm。

可重叠原因：dev不足10个样本共9条（其中8条0样本）；平均成本增加3条；所有12条在当前真实数据下都不能通过成本证据要求（8条未知而非已证成本增加、S07下界人为0、3条平均负节省）；9条连来源题也无法词面匹配；10条有表示/条件语义问题；S04存在明确的对称商适用条件遗漏风险。不要将这些重叠数量相加。

## 实现与统计问题

- S02 明确 OR文字/AND机器条件失配。Distiller校验只要求preconditions属于词汇表、出现在compact中，不要求它们在来源题或独立题可满足；9条来源自匹配为0仍通过schema。
- 空pairwise的 independent 字段仍设true，admit再用非空检查隔离；决策防护实际生效，但状态语义混合了“缺数据”和“有害”。
- S12一次评分假阴性不是Admission布尔逻辑错误，却污染其输入。不得据此认定应该放宽reject_observed_harmful_patterns。
- 预算实验 `experiment_bank.validate_batch` 直接写 structurally_distinct=True；之前确实做过全局近重复检查，但这不能证明数学结构独立。该字段证据强度过高。
- 单卡token_stats未纳入第一次失败蒸馏及未入库训练题成本，而全局bank.cost_calls和成本报告包含这些支出。全局总数正确；单卡摊销估计不是全局总成本分摊。
- n=1时saving_lower_bound=0是程序默认值，不能当作估计置信区间。

不修改任何阈值、银行快照或历史分数。全部门槛输入、阈值、短路位置和额外失败项见 `data/admission_decisions.jsonl`。
'''
 save('03_ADMISSION_DIAGNOSIS.md',report)
 report='# 学科、Trigger 与未来复用机会\n\n所有在线特征均来自 ProblemView.problem，不读取标准解答；类别来自原MATH type→标准七类映射。训练每类100、开发每类50，候选轮转选取上限12；不是Algebra采样占优。全部7类有候选，只有4类有eligible验证。\n\n'
 rows=readcsv(P/'data/subject_coverage.csv');report+=table(['学科','训练','正确轨迹','候选','开发','trigger匹配对','eligible对','实际配对'],[[r[k] for k in ['subject','training_tasks','correct_traces','candidate_skills','dev_tasks','trigger_pairs','eligible_pairs','actual_pairs']] for r in rows])
 report+='\nRetrieval Coverage在此定义为同学科且至少一个trigger命中的题，不要求最终状态active：155/350=44.29%。Eligible Coverage（完整机器前置/负触发条件）39/350=11.14%。生产检索器active_only的实际检索覆盖为0。语义上的“真正满足数学条件”未被这些词面特征证明；eligible只代表现实现有调用资格。\n\n已有skill-on开发日志覆盖39道，每题1对共78调用。观察到2道由错转对、2道由对转错；Useful Coverage若定义为观测到准确率增益，则2/350=0.57%，仅单次观察，不能等同稳定帮助。若按token节省定义，须读取dev_pairwise的逐题差值，不把匹配当收益。\n'
 for i,s in enumerate(skills,1):
  k=f'S{i:02}';x=stats[k]
  report+=f"\n## {k} {s['name']}\n\n同学科 {x['dev_subject']} → trigger {x['dev_trigger']} → 全前置 {x['dev_precondition']} → 负条件排除 {x['dev_negative_excluded']} → eligible {x['dev_eligible']} →实际 {x['dev_actual_uses']}。欠缺前置词频：`{x['missing_preconditions']}`。\n"
  for category,e in examples[k].items():
   report+=f'\n### {category}\n\n'
   report+=str(e['status'])+'\n' if 'status' in e else f"`{e['task_id']}`；特征 {e['features']}；缺少 {e['missing_preconditions']}。\n\n{e['problem']}\n"
 report+='''
## 为什么覆盖损失不能简单归因于题太少

S01把“二次表达式”又要求题面显式写polynomial，19道命中全部被拒；S02把多种任选工具变成全部必须存在；S05用composition表示几何组合，但特征只识别函数复合；S09要求先写equation，而策略本身正是将文字转成方程。6张卡把nonzero作为必备题面词而非可推导的域条件。这些都是可先离线核实的契约问题。

`quadratic`正则能命中x^20及包含x²项的高次式，`ratio`可命中rational。源码提供的是启发式候选特征，不能当作经过数学验证的适用性判定。负触发如circle、polynomial是无条件排除，但compact里有“unless reduced”“polynomial-only”等更细条件。未更改这些规则。
'''
 save('04_TRIGGER_COVERAGE.md',report)
 report='''# Router 与规则敏感性

本次直接责任链：12候选全部未active → active_only检索为空 → Router无可估计候选 →500题走base。不能声称Router在这500题上“错误拒绝了12个有价值active技能”，因为从未到达那一步。

预测器读取独立dev配对的输入+输出总token（含fallback），以及题面长度、样本数、准确率差、saving下界。预测base和skill成本都是同卡dev均值，不是逐题学习的回归模型。题面长度超出[0.5×dev最短, 2×dev最长]即unknown；少于10样本、缺pairwise也unknown。置信度为n/(n+10)，阈值0.8意味着n>=40；这是一条样本量启发式，不是统计置信概率。

需要正平均节省、正saving下界、准确率下降上界<=1%。该上界取 max(0, -[Wilson(benefit).lower-Wilson(harm).upper])。在没有benefit和harm时，要n>=381才能通过1%上界；本次每学科开发候选池仅50，且单卡最多60对。因此存在明确的潜在保守性/预算不匹配，但不是本轮直接零复用原因。置信规则和准确率界也不是统一校准过的配对检验。

历史测试使用次数门槛不存在。数据来自主动train-dev配对，理论上无需先在测试集使用即可打破冷启动；若本次验证后不增加独立dev证据，冻结测试库也不会自发晋升，这是设计结果。不能通过收集测试gold去解决冷启动。

'''
 scenario=summary['counterfactual_active'];report+=table(['仅移除的门槛','规则上active','实际效果结论'],[['不移除',scenario['keep_all'],'无'],['最低来源数',scenario['disable_min_source'],'来源均已>=3，故无影响'],['最低开发样本数',scenario['disable_min_dev'],'S07仍被0下界挡住'],['正成本收益',scenario['disable_positive_cost'],'S04/S06可规则晋升，但均已观察到平均更贵'],['历史使用量',scenario['disable_historical_usage'],'不存在此门槛，not_applicable']])
 report+='\n在仅移除Admission成本门槛的反事实里，S04/S06仍不会通过原Router：样本置信度不足、平均节省为负、下界为负、准确率风险上界也远大于1%。这只是对现有统计的规则敏感性，不创建active证书、不改变原库，不预测新题效果。\n\n证据不足不能当作负收益：8个零样本策略的未来价值unknown；S07只有1对，虽省1162 token但不足以可靠预测。S04/S06的平均成本增加则是真实执行证据。模型调用的输入和输出都被计入，没有发现把短prompt直接当作总成本降低的代码；但每卡总成本均值不按题复杂度建模，数据范围很窄。\n'
 save('05_ROUTER_AND_GATE_ANALYSIS.md',report)
 report='''# 成本与基线公平性审计

逐请求重算与原报告完全一致，保留原分数。账本不按跨方法相同call_id去重，因为那些是独立付费请求。原实验实际1802调用、2,234,706 tokens；共同历史在物理消耗中只计一次，按每套方法独立部署报告时各计一次。

'''
 cr=readcsv(P/'data/cost_breakdown.csv');report+=table(['阶段','用途','调用','输入','输出','总token'],[[r[k] for k in ['stage','purpose','calls','input_tokens','output_tokens','total_tokens']] for r in cr])
 report+='''
轨迹收集本身为本地封存/评分，额外模型调用0；其所依赖历史解题700次计795,435 token。初次失败蒸馏75,090、修订94,822、验证104,384均未丢弃。检索/路由调用0、测试retry0、未知其他调用0（以已有完整账本为边界）。FlowEvo的原始purpose标签把500次均记skill_solve，但实际只有461次注入历史，39次base；不能把标签直接解读成500次skill复用。

| 口径 | FlowEvo | Bot |
|---|---:|---:|
| 测试 | 641,955 | 523,020 |
| 共同历史生成 | 795,435 | 795,435 |
| Bot额外蒸馏/修订/验证 | 0 | 274,296 |
| 按方法独立部署的总token | 1,437,390 | 1,592,751 |

测试省118,935（18.53%），额外建库花274,296，差额为多花155,361（相对FlowEvo总成本约10.81%）。固定库场景中训练、蒸馏、修订和此次dev验证是一次性支出；每新题的解题消耗持续增加。若继续学习/重验证，这些开销也会再次发生，不能永远当常数。不能把本次未使用skill的测试节省外推为skill摊销收益。

## 实际prompt差异的归因

逐题检查1000份provider原始request：同模型别名、同system、同基础题面和末尾格式、同输出上限4096、同请求temperature=0、同配置并发64，每套恰500次、无retry。FlowEvo461题仅比Bot多原生历史解答前缀，另39题user prompt逐字相同。输入差107,014 token全部来自这461题，39题差为0。不是system变更、题目变化、输出上限或retry不同造成。

Bot输入62,237，FlowEvo169,251；输出460,783对472,704，少11,921。89.98%的总节省来自输入去掉历史。输出中的服务端reasoning_tokens为370,503对384,102；仅看到总量小幅变化，未见任何策略被使用，因此没有“BoT压缩推理”的执行证据。

模型精确不可变版本unknown，provider只返回deepseek-flash别名。thinking参数没有显式设置；依据当时保存的官方接口说明默认enabled/high，temperature在此模式无效，因此不能保证确定性。两组顺序执行，未交错随机化；缓存命中输入22,016对128，负载/服务端随机性及截断30对27是需披露的混杂。这里比较token数量，不据此推断人民币账单。数学评分器相同不等于无误，S12开发题已发现格式假阴性。

## Bot-NoBank 等价范围

对现有500题做零API离线重放：移除整个bank后，Router决策、单次请求的prompt、purpose、route、输出预算都与真实Bot请求一致；500/500通过。真实bank内没有active，执行器关闭、格式retry=0，因此银行内容对本批模型输入没有影响。两者的审计bank_hash/构建成本当然不同。

这严格证明本批“模型请求路径”与Bot-NoBank等价；不能证明再发一次随机模型请求仍得到相同答案/token。重放使用已有响应，并不制造新模型证据。无需为了证明相同请求路径再花500次API；后续若要估计独立采样效果，应该做小样本随机交错、预先固定协议。

配对变化：454题都对、8题仅FlowEvo对、10题仅Bot对、28题都错。原+0.4个百分点差值并不显著（既有McNemar p=0.8145），不是由两条总正确数推测出的结论。机器表见 task_pairwise.csv、prompt_config_comparison.csv、nobank_replay.csv。
'''
 save('06_COST_AND_BASELINE_AUDIT.md',report)
 report='''# Provenance、Gold 与重复检查

审计并非只信provenance布尔值：将12卡的71个来源ID逐条链接到真实train-build问题、首轮封存答案、prompt及调用账本，复算trace哈希。71/71均只有1次trace_generation，无retry；首轮内容与bank来源一致；真实prompt逐字等于仅含题面的base_prompt；不是过去FlowEvo经gold-feedback修正的轨迹。12次最终蒸馏的examples仅包含task_id、problem、model_first_solution，未传标准答案或参考解答。正确性标签仅用于训练后选择成功历史，这是本研究允许的训练筛选，并非让模型看gold反思。

训练700、开发350、测试500三组ID和数字掩蔽后的规范化文本检查通过；按既有prefix/suffix分块及SequenceMatcher>=0.9进行明显近重复检查也通过。该算法不是全语义去重：不能排除语义等价题、重写题或模型预训练污染。source内部文本差异不等于数学结构差异，预算验证脚本的structurally_distinct=True不应被过度解读。

测试gold只供全部答案封存后的评分；solver接受ProblemView，router/匹配仅看题面与类别。两方法共用同一manifest，学科来自MATH type，无需答案推断；FlowEvo原生检索按benchmark而不按学科，Bot才按学科，这是算法差异，不是标签来源不同。

测试前source_frozen_before_test记录与现存代码一致，bank哈希在所有1000份封存提交中一致；bank来源都是train-build，没有测试题进入冻结库。revision在正式测试开始前进行，日志原因是JSON截断/词汇不合规。没发现用这500题的表现选择更优skill或调整阈值的证据。

未知边界：更早会话是否曾看过其他测试题、提供方不可变模型版本、预训练污染，以及日志之外的人工调参历史为unknown。此前已排除潜在调试过的代数前500题，本批不能宣称绝对干净的标准MATH-500。

本次新增脚本禁用网络，测试集结果只用于离线配对/成本审计，未传给任何真实solver调用。没有新的模型调用，也没有覆盖原实验、银行、核心源码或分数。`tests/read_only_check.json`和manifest提供完整输入哈希证据。
'''
 save('07_PROVENANCE_AND_LEAKAGE_AUDIT.md',report)
 report='''# 下一步建议与最小实验（本轮不实施）

## 优先级1：修复 Skill 表示与 Distiller 的可观察条件契约

依据：9/12来源自匹配为0；8/12没有eligible开发题；S02 OR/AND直接冲突，S05函数composition误用，6张卡依赖题面nonzero。涉及features.matches、thought_distiller.distill、schemas.SkillRecord以及按特征精确签名+推导关键词的cluster_traces。

建议明确any/all/禁止条件，区分“检索时可直接观察”与“求解中需要验证”的数学前提；蒸馏后先检查每个来源及独立题的条件可满足性，再考虑付费验证。按实际变换聚类而非把工具菜单压缩成短文本。不要删除必要的数学条件或仅降低阈值。S04必须保留自由作用/固定点条件，S07清不等式分母必须保留符号条件。

预期改善有效覆盖；失败风险为检索变宽导致负迁移或遗漏定义域。消融：原卡原条件 vs 同一数学核心的结构化条件，先零API重放，再做独立开发配对。离线契约检查本身不增加API；重新蒸馏会增加。

## 并列必要前置：修复评价与诊断输入

依据S12的precalculus_250：两边都求得y-x=1即A，skill输出 `(A) Line` 后又输出 `(A)`；extract_answer用首次匹配，评分器不接受前者，形成假阴性。precalculus_88则为空响应、4096token截断。涉及evaluator.extract_answer、experiment_grader.grade_one、parallel_experiment.RecordedClient与validate_batch。

先离线测试最后答案提取、选择题选项规范化及截断分型，保留原score字段、另加诊断标签，不能悄悄修改历史结果。检查所有证据门槛的输入之前，不应因这两例去放宽Admission。风险是过宽答案提取误接受矛盾答案，需对错/多答案/复合集合的负例。

## 优先级2：有针对性的 shadow 开发验证及成本证据

优先S07的可逆有理式降阶核心（1对少1162但不可靠），其次S06的窄三角结构、S04的分类计数核心（分别10/18对弱准确率增益但更贵）。使用独立且适用条件明确的题，不从测试集选题；先检查来源/新题是否实质结构不同。

Admission目前的状态重放无计算错误。empty→quarantine的命名可改成“无证据”，但那不提升效能。将n/(n+10)与Wilson界的含义记录清楚；全局成本与单卡成本分摊分开。只有证据支持之后才能研究分阶段晋升，不应为active数量而降门槛。涉及skill_validator、experiment_bank与token_accounting。会增加少量API验证成本；消融应同时报告总token和正确率，非只看prompt长度。

## 优先级3：紧凑策略注入与局部执行

S04/S06平均增加74.94/119token，且都没有executor。即使覆盖修好，普通提示仍可能只加输入。可对同一核心比较“原紧凑卡/更明确的局部宏步骤/无卡”，必要时只对可形式核验的小算子研究执行器。先证明输入和输出合计有收益；失败风险为过度压缩抹去符号、边界或可逆性条件。涉及prompt_builder、math_executor。新增API由下一轮批准范围决定。

## 优先级4：Router 校准，当前不先重写

本次没有任何active候选给Router；重写它不能修复空候选。独立零API敏感性表明即便只去成本门槛让S04/S06晋升，原Router也因负节省和不确定拒绝。未来有真实active和足够dev数据后，才校准按难度/题型的成本预测以及配对风险界。不能把历史测试使用量当不存在的门槛，也不能用测试gold在线积累证据。

不建议：直接降低所有阈值、强行激活12卡、扩大测试到更多500题、开启任意跨学科组合、重写整个算法。S10/S11语义重叠可先做离线家族整理，组合字段契约另作离线修复，因本次max_injected_skills=1不是最迫切事项。

## 下一轮最小真实实验建议

前置为上述零API契约与评分核验；本轮仅提出方案，需用户明确同意后才执行。

- 新训练题0：复用已有S07的6条清洁首轮轨迹；不新增训练解题。若重新蒸馏其窄核心，最多2次（候选+一次修订）。
- 新开发题20：从尚未执行的独立train-dev剩余题，仅按题面/结构选出清分母或重复有理块的合适题；至少4类边界（分母恒正/符号分段/代换不一一/域排除），与来源及正式测试均去重。若找不到20道真正适用的独立题，停止并改粒度，不拿不适用题凑数。
- 三组：Bot-NoBank、原S07卡（固定注入但模型仍检查条件）、修复条件且保留完整数学限制的紧凑卡。20×3=60次解题，组别随机交错，同模型/输出预算，所有提交封存后评分。只在影子开发实验使用，不进入正式active库。
- 最多62次API。规划上界：解题每次4096输出+至多约500输入，60次约275,760；蒸馏2次×(16384输出+约4000输入)=40,768；总预留约320,000 token。估计必须在固定prompt后再核对；并非保证能耗。按既有单次平均尺度，实际可能约80,000–140,000，但构造题难度、思考长度及截断均未知。
- 观察：真正结构适用率、独立首次正确率、base_only/skill_only、输入/输出/思考token、截断、每题节省与配对区间、条件误匹配、摊销成本，保留每次usage。
- 继续条件：修复后能覆盖预定结构、无已确认数学条件错误/新增负迁移、同时观察到平均正总token节省，且不是少数截断差异所驱动。20对只能决定是否值得扩验证，不能认证1%精度风险。
- 停止或改方向：不能找到足够适用独立题；仍只是宽泛建议；节省下界不支持收益；正确性退化；域/符号条件反复遗漏。若准确率有益但token更高，转为准确率目标而不是宣称省token。
'''
 save('08_RECOMMENDATIONS.md',report)
 report='''# 研究摘要

本轮完成12个真实策略的离线诊断，新增LLM调用0、token0、API成本0；原500题分数、核心实现与策略库均未改动。

最优先应改 Skill 表示/Distiller 的条件契约，并先修复评分诊断输入，而非直接放宽Admission或重写Router。12/12通过形式schema，0/12有充分证据成为可靠经济的active；S04/S06/S07有值得保留的局部核心，但证据不够且S04需补对称条件。

9条策略连来源题都不匹配，8条开发eligible为0；另外S07仅1对，S04/S06因成本增加失败，S12因一例评分假阴性+一例截断触发harm。S12的观察不能证明两次数学推导错误。Admission状态按代码重放12/12一致；数据契约、评价和structural证据字段存在已复现问题。Router本轮未收到active候选，潜在保守界是次级问题。

'''
 rows=[]
 for i,s in enumerate(skills,1):
  k=f'S{i:02}';x=stats[k];rows.append([k,s['subject'],notes[k]['name_zh'],f"{x['dev_eligible']}/50",x['first_rejection_gate'],notes[k]['priority']])
 report+=table(['ID','学科','真实套路（中文释义）','eligible','首阻断','建议'],rows)
 report+='''
开发题155/350被trigger检索，完整条件只留下39/350。七学科均有候选；不平衡来自结构/条件而非缺学科样本。单关反事实只有去成本门槛使S04/S06规则上active，但两者更贵且仍过不了Router，不是有效性证据。

成本精确核对：测试省118,935（18.53%）；其中107,014是去掉历史注入导致的输入下降，11,921是输出差。Bot额外蒸馏、修订与验证274,296，使总成本多155,361。500题Bot请求路径与空库离线重放逐字一致；不能推断再运行随机输出相同，也不能把节省归因于策略复用。配对454都对、8仅FlowEvo、10仅Bot、28都错。

建议下一轮0新训练、20独立开发题×3组、最多2次重新蒸馏，总计不超过62次请求，token规划上限约320,000；本轮不执行。先以S07窄核心验证条件表示能否带来真实覆盖和总token收益；没有足够适用题或数学条件可靠性则停止/改粒度。

所有原文、门槛、匹配示例、逐请求成本与未确定事项见01–08报告及data目录。未知事项包括不可变模型版本、完整历史测试暴露和文本去重以外的语义重复。
'''
 save('00_EXECUTIVE_SUMMARY.md',report)
 (P/'README.md').write_text('''# Skill Admission 离线诊断包

阅读顺序：reports/00_EXECUTIVE_SUMMARY.md → 01_ALL_SKILLS.md → 03_ADMISSION_DIAGNOSIS.md → 08_RECOMMENDATIONS.md。

- reports：9份完整中文报告。
- data/skills_full.json：12个真实Skill的完整原记录。
- data/skill_diagnostics.csv、admission_decisions.jsonl：逐Skill、逐关数据。
- data/skill_task_matches.csv：12×350=4200条开发匹配记录；不使用标签生成特征。
- data/task_pairwise.csv：500题实际配对，不修改历史分数。
- data/cost_breakdown.csv、prompt_config_comparison.csv：账本与公平性审计。
- data/evidence：71条必要来源轨迹、4个准确率不一致开发题、真实prompt示例和provenance证据，未打包整个历史响应库。
- scripts：可复现的只读诊断/渲染及人工质量评注。
- tests：网络禁用、契约/反例/账本/历史哈希验证。
- manifest.json：源commit、哈希、数据/模型与unknown项。报告时间使用Asia/Shanghai。

从Flowevo-Bot目录复现：

```bash
.venv/bin/python diagnostics/skill_admission_audit/scripts/analyze.py
.venv/bin/python diagnostics/skill_admission_audit/scripts/render_reports.py
.venv/bin/python -m pytest diagnostics/skill_admission_audit/tests -q
```

需要原experiments目录及当前项目依赖。analyze.py主动禁用socket连接，不调用模型；输出限制在本诊断目录。独立zip可直接阅读全部报告及必要证据；完整重算还需manifest引用的大日志。

本轮新增API调用0，token0，成本0。所有反事实仅重放规则；所有数学反例是明确标注的本地构造，不是模型实验数据。已有生产核心代码与历史结果全部保留。
''')
 print('Rendered 9 reports and README')

if __name__=='__main__':main()
