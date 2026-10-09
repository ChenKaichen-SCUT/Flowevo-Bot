"""Regenerate reports from preserved evidence, without API access or selection."""
import sys,collections,math,random,statistics,datetime
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.rmmd.macros import inspect_question,COMPACT

def report(name,body):(OUT/'reports'/name).write_text(body.strip()+'\n')
def mdtable(rows,keys):
    return '| '+' | '.join(keys)+' |\n| '+' | '.join(['---']*len(keys))+' |\n'+'\n'.join('| '+' | '.join(str(r.get(k,'')) for k in keys)+' |' for r in rows)
def interval(values):
    if not values:return [None,None]
    rng=random.Random(10210);samples=sorted(sum(rng.choices(values,k=len(values)))/len(values) for _ in range(10000))
    return [samples[250],samples[9749]]
def main():
    audit=read(OUT/'data/trace_manifest.json');sources=lines(OUT/'data/clean_success_traces.jsonl');byid={r['task_id']:r for r in sources}
    clusters=read(OUT/'data/pattern_clusters.json');ops=lines(OUT/'data/reasoning_operations.jsonl');bank=read(OUT/'data/macro_skill_bank.json');screen=read(OUT/'data/macro_candidates.json');tasks=read(OUT/'data/dev_tasks.json');selection=read(OUT/'data/selection_manifest.json')
    report('00_STATE_AND_PROTOCOL.md',f'''# RMMD 状态核对与预注册

上一轮本地与远端 main 均为 206a6caa6954283e41f219d6c61f84f6904eb5f8，开始时仅指引.txt变化。原始审计见 evidence/version_audit.json。本轮位于独立 macro_discovery_pilot，不覆盖旧实验或上游代码。snapshots/protected_files.json 固定3414个旧文件，最终逐项复核。

研究问题：从已确认首次正确的真实训练解法中，能否找出具有结构变化的数学操作，并区分短提示与确定性执行的收益？本轮是受限工程化识别器的可行性实验，不宣称自动发现新的数学定理。

硬上限120次请求、200000新API tokens；实际计划{len(tasks)}题、{3*len(tasks)}份提交，其中可直接验证的余式题无需C组API。API16并发、CPU12并发，低于用户允许的64/12。DeepSeek Flash，温度0，max_tokens4096，与基线同一system和结束格式。没有额外“简洁回答”指令，没有gold反思或正确性重试。

付费前固定代码、宏、题单、预算和标签文件hash，保存prepaid_freeze与runtime_before_paid.zip。标签内容仅在全部提交seal完成后由离线评分块读取。训练解法正确性来自独立旧评分复核；其答案或官方解答不进入新求解器。所有新API请求和完整安全响应（包括reasoning_content）保存。

禁止完整MATH500、禁止根据本轮结果再调提示或补样本；报告后停止。预算用实际usage加所有在途请求的保守上界，未知账单保留pending并停止，无盲目重发。
''')
    report('01_TRACE_CORPUS_AUDIT.md',f'''# 真实轨迹审计

原始独立求解记录{audit['total_real_trajectories']}条：MATH {audit['raw_math_solve_trajectories']}，另2条GSM8K/Game24真实smoke。可独立确认正确的MATH记录跨所有split为{audit['math_offline_confirmed_successes_all_splits']}条，但仅603条训练首次成功可用于挖掘。

旧627条“成功”中，601条得到保守评分确认，26条unknown隔离；另从原来标False的训练记录恢复2条，合计603。没有把unknown当作正确。保留所有原始评分，新的离线评分另存。

{mdtable([{'subject':k,'clean':v} for k,v in audit['subject_counts'].items()],['subject','clean'])}

排除共1237条；原因可重叠：{audit['exclusion_reasons_overlapping']}。1000测试轨迹绝不学习；旧开发78及V2开发60都排除。700原训练为795435 acquisition tokens，603成功轨迹本身518212 tokens；失败训练也属于采集成本。

总计1261个唯一task ID、579条跨方法重复任务轨迹。history、bank.history、checkpoint和逐call文件只是同一请求的复制件，不新增样本。可审计MATH中未发现gold反思暴露；2条历史smoke完整请求证据不足，gold_exposed=null，均排除。75条干净训练轨迹曾作为旧技能来源，字段保留，不声称全新来源。

统一clean/excluded JSONL记录problem、model_solution、final_answer、offline_correct、gold_exposed、truncated、实际input/output/total tokens、source_run_id、source_hash、旧评分、seal、call ID和以前使用情况；clean不包含gold_answer。重新核对原始submission seal、prompt、response和冻结评分器hash。源轨迹是来源可查的首次调用，不包含gold引导后修订。
''')
    examples=['# 真实模式例子与范围\n'];supported=[]
    for macro in bank:
        examples.append('## '+macro['macro_id'])
        for tid in macro['source_task_ids']:
            row=byid[tid];examples.append(f"### {tid}\n\n题目：{row['problem']}\n\n实际模型解法：\n\n{row['model_solution']}\n\n来源SHA：{row['source_hash']}\n")
            supported.append({'macro_id':macro['macro_id'],'task_id':tid,'self_match':inspect_question(row['problem'],macro['macro_id'])['execution_verified']})
    (OUT/'data/pattern_examples.md').write_text('\n'.join(examples));table(OUT/'data/source_self_match.csv',supported)
    status=collections.Counter(r['verification_status'] for r in ops)
    subjects=[]
    for subject in sorted(audit['subject_counts']):
        group=[r for r in ops if r['subject']==subject];subjects.append({'subject':subject,'operations':len(group),'verified':sum(r['verification_status'].startswith(('symbolically_verified','verified_operation')) for r in group),'unknown':sum(r['verification_status'].startswith('unknown') for r in group)})
    report('02_REASONING_PATTERN_MINING.md',f'''# 数学操作挖掘

603条首次正确解法逐学科处理，共{len(ops)}条IR记录。每条包含operation_type/input_structure/output_structure/assumptions/required_guards/source_step_ids/verification_status；source_step_ids指向原model_solution中数学片段的零基序号。保留原LaTeX及变量重命名后的SymPy树。

{mdtable(subjects,['subject','operations','verified','unknown'])}

验证状态：{dict(status)}。每条最多检查48个显式等式，单次符号工作最多2秒，宏识别最多5秒。无显式可验证等式、自然语言证明、语境约束方程、无法解析的图形/LaTeX保留unknown。正确的最终答案不等于整段推理自动获得证明。

一般操作先解析等式，再验证有理差恒等为0，按展开/因式分解/有理正规化/数值运算等分类；分母非零作为条件保留。受语境约束的x²=4不误当恒等式。单纯数值运算即使频繁也不自动推荐。

两个中层候选组合多个步骤：根的数值多项式→首一化→基本对称量→Newton幂和→伴随矩阵核验；余式的多项式对→商环约化→独立系数递推→P=QD+R及次数核验。宏来源要求真实解法确实讨论相关数学关系且出现公式；可执行部分另独立计算与验证。来源解法中的自然语言步骤不是形式化证明，宏实现是人工编写的确定性算法。pattern_examples.md完整保留8条实际来源以供语义复核。

根候选6条来源涵盖二/三/四/六次、两三次因子合成、e2、e2/e4、根积和用根关系构造P(x)，不是一个仅换系数的模板。余式2条来源分别为四次除非首一线性式，及两因子乘积除二次式，后者需约化x³=1再组合。已见替代方法：直接求根、逐因子根积、长除法、线性余式定理。

失败反例：仅求实/有理/正根的子集，未定系数，多变量，零除式、非多项式、题目要求余式之后再求其他量。一般方程两边相等不表示可安全除以零；本轮不将“平方去根号”升级为可执行宏，故不会未经回代提交额外根。
''')
    ranking=[]
    for family in sorted({c['family'] for c in clusters}):
        group=[c for c in clusters if c['family']==family];ids={tid for c in group for tid in c['task_ids']}
        ranking.append({'family':family,'subjects':','.join(c['subject'] for c in group),'unique_source_tasks':len(ids),'chosen':family in [b['macro_id'] for b in bank],'reason':'结构多样且可独立验证，进入小样本' if family in [b['macro_id'] for b in bank] else 'unknown/上下文未证明' if family in ('unparsed','constrained_equation') else '仅低层恒等式或数值子操作；尚无可靠问题级触发与替代预算证据，本轮不付费'})
    table(OUT/'data/all_family_ranking.csv',ranking)
    report('03_MACRO_CANDIDATE_RANKING.md',f'''# 候选排序与独立覆盖

{mdtable(ranking,['family','unique_source_tasks','chosen','reason'])}

{mdtable(screen,['macro_id','source_tasks','eligible_original_dev','eligible_supplement_train','selected','prompt_overhead_estimated'])}

完整筛选分母6430：1186条尚未使用的原dev题 +5244条尚未使用的原train题。预筛含roots/remainder的278题并运行严格识别器；不满足词面必要条件的其他题不可能命中当前实现。剔除旧700训练、350开发及20V2题；使用数字归一化+相似度≥0.9、余式多项式支撑集结构、简单根和/根积目标类型排除模板重复。选中集合内再去重复。题单按原dev优先、公开难度及ID固定排序，无label或新正确率参与筛选。根宏补充的unused train题在本轮正式保留为dev，今后不再用于建库。

覆盖率不是MATH测试总体覆盖；按当前严格问题文法和去重准则测得。宏的eligible数也不保证一定节省推理。只有{len(tasks)}题符合本轮独立性及结构多样性要求，余式未凑满10题，不放松guard补足。

Compact约96/66 tokens（UTF8 bytes/4估计，不是官方tokenizer精确值；实际API输入差额另计），阈值100。预计收益：根只可能替代对称量推导，仍要LLM解释目标；余式可替代完整求解。局部计算和核验成本以秒记录，均0额外API；宏生成由代码实现，本轮生成LLM tokens=0。完整采集成本795435 tokens，增量复用成本0。盈亏平衡需用新配对数据估计，付费前不声称收益。

高频加减乘除不推荐；仅有factor/reduce/simplify关键词不作为模式证据。其余学科的自然语言证明和组合约束尚未取得安全的中层可执行表示，因此没有为了覆盖七科而制作泛化工具菜单。
''')
    report('04_MACRO_IMPLEMENTATION.md',f'''# 宏实现

代码src/flowevo_bot/rmmd/macros.py；macro_skill_bank.json同时保存Compact和Executable、来源、触发/guard、证书scope。研究用途，未直接加入生产active库。

root_invariants：roots题且存在数量/表达式请求、唯一数值QQ多项式、次数2–6；拒绝显式根子集和未定参数。首一化→e_k→Newton幂和；用多项式重建及伴随矩阵trace分别核验。只提供ALL roots的中间量，绝不将其局部正确当成最终任务完成。若存在0根，仍可安全给e_k，但不得直接求倒数；LLM必须另检查目标分母及约束。

Compact：{COMPACT['root_invariants']}

polynomial_remainder：全题匹配“Find/Determine/What is the remainder when/of M0 is divided by M1”文法，同一变量QQ多项式、被除式次数≤128、除式次数1–16、系数/长度/操作数有界。执行除法后，独立系数递推再验证，检查精确恒等式P=QD+R和degR<degD。仅这里允许直接提交，原因是文法完整消费题目且证书覆盖完整所求余式。其余叙述如“然后代入”拒绝。更高次表达式或参数除式不在证明范围。

Compact：{COMPACT['polynomial_remainder']}

结构触发支持all_of/any_of/not/guard，未知guard按False。真实流程同时检查trigger、guard、execution_verified；冻结选择时验证，运行时重新算且与冻结结果比较。C根执行失败不能静默改成B；当前冻结题均通过，若运行时不同则中止。记录execution_attempted、verified、full_task_verified与local_total_seconds。

真实接受案例：来源1007的ab+ac+bc=11/3；742的倒数两两积和e2/e4=9/4（宏只给中间量）；738余式52；891余式3。拒绝样例及原因见tests和data/guard_examples.json。随机性质测试仅是有界回归，完整数学保证来自QQ多项式恒等式及次数判据，不声称自然语言任意题目的泛化证明。
''')
    tests=(OUT/'tests/prepaid.log').read_text()
    report('05_PREPAID_VALIDATION.md',f'''# 付费前验证

{tests.strip()}

17项新增测试含50个随机QQ余式实例及25个已知多重根实例，检查源题自匹配、题意误匹配、全题/局部证书区分、参数/变量/次数边界、重复因子、独立回代、重根和0根、不引入伪根、AND/OR与未知guard、无gold依赖、seal篡改、实际usage加在途预算、缓存不重复计费和pending不重发。另原项目90项回归。

预付费发现并修复：首一多项式重建默认ZZ域与输入QQ域的严格对象比较造成假拒绝；显式统一QQ后通过已知根性质测试。近重复扫描加速仅利用相似度上界，未改变0.9判据。没有参考任何新付费结果修正。

宏源码及调用器不读取标签，统一离线评分器沿用冻结V2保守实现；unknown与False区分，截断单独标记。所有提交seal完成是标签读取的前置条件。前期训练正确性过滤使用历史离线结果，不属于在线gold反思。
''')
    examples=[]
    for question in ['Find the remainder when $x^2+1$ is divided by $0$.','Find the remainder when $x^4+2$ is divided by $(x-2)^2$.','Find the remainder when $x^3+1$ is divided by $x+1$, then evaluate it at 2.','Find the sum of the rational roots of $x^3-x+1=0$.','Find the sum of the reciprocals of the roots of $x^3-x^2=0$.']:
        mid='root_invariants' if 'roots' in question else 'polynomial_remainder';examples.append({'question':question,**inspect_question(question,mid)})
    write(OUT/'data/guard_examples.json',examples)
    if not (OUT/'data/task_results.jsonl').exists():return
    results=lines(OUT/'data/task_results.jsonl');methods=['A_NoBank','B_Compact','C_Executable'];metrics=[];pairs=[];summaries=[]
    for family in ['ALL']+[b['macro_id'] for b in bank]:
        subset=[r for r in results if family=='ALL' or r['macro_id']==family]
        for method in methods:
            group=[r for r in subset if r['method']==method];correct=sum(r['offline_correct'] is True for r in group)
            metrics.append({'family':family,'method':method,'n':len(group),'correct':correct,'accuracy':correct/len(group),'unknown':sum(r['offline_correct'] is None for r in group),**{k:sum(r[k] for r in group) for k in ['input_tokens','output_tokens','total_tokens','api_call_count','execution_seconds','verification_seconds','local_total_seconds']},'truncated':sum(r['truncated'] for r in group)})
        base={r['task_id']:r for r in subset if r['method']=='A_NoBank'}
        for method in methods[1:]:
            deltas=[];benefit=harm=bothcorrect=bothwrong=0;indiffs=[];outdiffs=[]
            for r in [r for r in subset if r['method']==method]:
                a=base[r['task_id']];delta=a['total_tokens']-r['total_tokens'];deltas.append(delta);indiffs.append(a['input_tokens']-r['input_tokens']);outdiffs.append(a['output_tokens']-r['output_tokens'])
                ac=a['offline_correct'] is True;bc=r['offline_correct'] is True;benefit+=not ac and bc;harm+=ac and not bc;bothcorrect+=ac and bc;bothwrong+=not ac and not bc
                if family!='ALL':pairs.append({'family':family,'task_id':r['task_id'],'method':method,'base_correct':a['offline_correct'],'method_correct':r['offline_correct'],'base_truncated':a['truncated'],'method_truncated':r['truncated'],'saved_input':a['input_tokens']-r['input_tokens'],'saved_output':a['output_tokens']-r['output_tokens'],'saved_total':delta,'avoided_api_calls':a['api_call_count']-r['api_call_count'],'execution_seconds':r['execution_seconds'],'verification_seconds':r['verification_seconds']})
            summaries.append({'family':family,'method':method,'n':len(deltas),'benefit':benefit,'harm':harm,'both_correct':bothcorrect,'both_not_confirmed_correct':bothwrong,'mean_saved_input':statistics.mean(indiffs),'mean_saved_output':statistics.mean(outdiffs),'mean_saved_total':statistics.mean(deltas),'bootstrap95_mean_saved_total':interval(deltas),'total_saved':sum(deltas)})
    table(OUT/'data/group_metrics.csv',metrics);write(OUT/'data/aggregate_metrics.json',metrics);table(OUT/'data/task_pairwise.csv',pairs);write(OUT/'data/paired_summary.json',summaries)
    calls=read(OUT/'evidence/budget_final.json');current=calls['actual_total_tokens']
    costs={'new_macro_generation_api_tokens':0,'new_experiment_api_tokens':current,'new_experiment_api_calls':calls['api_calls'],'source_trace_acquisition_tokens':795435,'incremental_source_reuse_tokens':0,'full_source_plus_current_research_tokens':795435+current,'previous_v1_all_bank_build_tokens':1069731,'previous_v2_research_tokens':102316,'cumulative_research_including_failed_prior_versions_tokens':1069731+102316+current,'agent_chat_and_engineering_cost':'not available in DeepSeek ledger; excluded, not assumed free','local_mining_seconds':read(OUT/'evidence/mining_runtime.json')['wall_seconds'],'local_selection_seconds':selection['local_seconds'],'cpu_price':'not priced; execution and verification seconds reported per task'}
    scenarios=[]
    for method in methods[1:]:
        weighted=0
        for candidate in screen:
            row=next(r for r in summaries if r['family']==candidate['macro_id'] and r['method']==method)
            coverage=candidate['eligible_original_dev']/selection['original_dev_unused_denominator'];weighted+=coverage*row['mean_saved_total']
            scenarios.append({'method':method,'family':candidate['macro_id'],'coverage':coverage,'eligible_mean_saved':row['mean_saved_total'],'unconditional_mean_saved_assuming_same_effect':coverage*row['mean_saved_total'],'original_dev_denominator':selection['original_dev_unused_denominator'],'warning':'strict eligible subset + some supplemental train dev; conditional scenario not MATH-wide estimate'})
        costs[method+'_coverage_weighted_tokens_saved_per_task_scenario']=weighted
        costs[method+'_source_plus_pilot_break_even_total_tasks_scenario']=math.ceil((795435+current)/weighted) if weighted>0 else None
        costs[method+'_pilot_only_break_even_total_tasks_scenario']=math.ceil(current/weighted) if weighted>0 else None
    write(OUT/'data/cost_summary.json',costs);table(OUT/'data/coverage_amortization_scenarios.csv',scenarios)
    report('06_SMALL_BUDGET_EXPERIMENT.md',f'''# 冻结的小预算三组实验

{len(tasks)}道独立开发题，三组共{len(results)}份提交，实际{calls['api_calls']}次API、{current} tokens，0生成调用、0重试、0gold反思。硬预算120/200000均未触及。A/B/C共享题目、系统提示和输出要求；C余式以完整证书直接答题，tokens和API=0；C根提供验证中间量后仍调用同一模型。

{mdtable(metrics,['family','method','n','correct','accuracy','input_tokens','output_tokens','total_tokens','api_call_count','unknown','truncated'])}

参与率：B在全部选中题注入短思路，C全部运行本地宏；余式直接完成，根只替代中间计算。集合是经过条件筛选的14题规模附近的小样本，不能当作MATH总体正确率。源题自匹配与负例属于付费前独立检验，没有只挑正确开发结果。

记录schema含run_id/task/subject/difficulty/method/macro_id/type/trigger/guard/attempt/verified/fallback/prompt_hash、完整usage、调用数、latency、answer、offline_correct、parse_status、truncated、gold_exposed及局部计算/核验时间。api_calls保存原始请求响应；submissions保存评分前seal；submission_barrier证明先提交后读label。
''')
    report('07_PAIRED_COST_ANALYSIS.md',f'''# 配对与完整成本分析

{mdtable(summaries,['family','method','n','benefit','harm','both_correct','both_not_confirmed_correct','mean_saved_input','mean_saved_output','mean_saved_total','bootstrap95_mean_saved_total'])}

正数为相对A节省。bootstrap固定seed、10000次任务配对重采样，n很小时区间极不稳定，不是准确率非劣证明。全部任务（含截断）保留，unknown单列；benefit/harm按是否确认正确计算，不将unknown解释为确定错误。

{mdtable(scenarios,['method','family','coverage','eligible_mean_saved','unconditional_mean_saved_assuming_same_effect'])}

完整成本账：{json.dumps(costs,ensure_ascii=False,indent=2)}

余式C消耗确定性CPU并避免LLM调用；这是工具替代产生的token节省，不能归因于短提示压缩。根C仍调用LLM，因此其input/output差异检验中间量是否真正减少模型推理。B只增加紧凑思路，以真实输入增量计费；是否有节省由配对表决定。宏对题目是否有实质帮助最终仍要看harm与输出变化。

source+pilot和pilot-only均给出覆盖加权摊销；覆盖只取未使用原dev分母1186，效果由已选条件样本估计，部分样本来自保留unused train，故只作为强假设情景。MATH500上没有新测量，不报告总体提升。该轮全量A/B/C支出计入研究成本，不能只把生产C的0token当作免费建库。
''')
    tool=next(r for r in summaries if r['family']=='polynomial_remainder' and r['method']=='C_Executable')
    root=next(r for r in summaries if r['family']=='root_invariants' and r['method']=='C_Executable')
    decision='继续改进'
    verdict={'decision':decision,'reason':'可验证工具替代在严格余式文法内成立，但独立样本和覆盖不足，不能把所选题收益外推为通用BoT收益；根中间量路线按实际配对损益单独评价','tool_paired_summary':tool,'root_paired_summary':root,'next_module_if_user_authorizes':'提高问题级结构解析与验证覆盖；基于已有训练轨迹寻找更多中层变换，保持否决样例和来源审计；不自动补跑','stop_now':True,'math500_run':False,'outcome_driven_retuning':False}
    write(OUT/'data/go_no_go.json',verdict)
    strongest=max(pairs,key=lambda r:r['saved_total']);worst=min(pairs,key=lambda r:r['saved_total'])
    report('08_GO_NO_GO_AND_DELIVERABLES.md',f'''# 决策与交付

**{decision}**。余式工具路线与Compact提示路线分别看待：前者用精确恒等式覆盖完整答案，能够省去调用；后者仍由LLM推理，未因名字叫macro就获得同样的节省。最强省token个例{strongest['task_id']} / {strongest['method']}，节省{strongest['saved_total']}；最差{worst['task_id']} / {worst['method']}，节省{worst['saved_total']}（负数为增加）。正确率损伤见逐题配对，不隐去。

工具候选实际独立样本少，广泛覆盖及采集成本摊销尚不支持直接进入500题。下一阶段如获新的研究指示，应优先修改问题级结构解析/任务完成证书及中层变换覆盖，不以增删“简洁”提示或筛掉失败题来美化本轮结果。当前单轮实验已结束，没有自动扩大样本或运行MATH500。

reports/00–08完整研究报告；data/clean_success_traces.jsonl、excluded_traces.jsonl、trace_manifest.json；reasoning_operations.jsonl、pattern_clusters.json、pattern_frequency.csv、pattern_examples.md；macro_candidates.json、macro_screening.csv、macro_skill_bank.json、dev_tasks.json；task_results.jsonl、task_pairwise.csv、group_metrics.csv、cost_summary.json；api_calls/完整安全请求与响应；submissions/评分前提交；tests/本地检验；evidence/预算、版本、冻结、历史文件保护；snapshots/实际运行代码。

独立归档位于 Flowevo-Bot/macro_discovery_pilot.zip。推送前扫描凭据，不包含miyao.txt或密钥、venv、缓存。远端继续使用已确认的单连字符 ChenKaichen-SCUT/Flowevo-Bot。
''')
    print(json.dumps({'metrics':metrics,'paired':summaries,'costs':costs,'decision':verdict},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
