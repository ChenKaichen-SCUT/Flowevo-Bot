"""Render all V2 reports from recorded calls and frozen paired evidence. No API."""
import csv
from datetime import datetime,timezone,timedelta
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from collections import Counter
from difflib import SequenceMatcher
from flowevo_bot.common import digest,read_json,write_json,jsonl
from flowevo_bot.token_accounting import estimate_tokens
from flowevo_bot.v2.skills import MacroSkill,evaluate
from run_v2_research import OUT,OLD,ROOT,csv_write,dump_lines

def md_table(headers,rows):
    clean=lambda x:str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(clean(x) for x in r)+' |' for r in rows])+'\n'

def binom_cdf(k,n,p):return sum(math.comb(n,j)*p**j*(1-p)**(n-j) for j in range(k+1))
def cp(k,n,alpha=.025):
    def invert(k,target):
        lo,hi=0.,1.
        for _ in range(70):
            mid=(lo+hi)/2
            if binom_cdf(k,n,mid)>target:lo=mid
            else:hi=mid
        return (lo+hi)/2
    return (invert(k-1,1-alpha/2) if k else 0.,invert(k,alpha/2) if k<n else 1.)

def statistics_for(pairs):
    known=[r for r in pairs if r['base_correct'] is not None and r['skill_correct'] is not None]
    n=len(known);harm=sum(r['base_correct'] and not r['skill_correct'] for r in known)
    benefit=sum(not r['base_correct'] and r['skill_correct'] for r in known)
    both=sum(r['base_correct'] and r['skill_correct'] for r in known)
    discord=harm+benefit; p=min(1.,2*sum(math.comb(discord,i) for i in range(min(harm,benefit)+1))/(2**discord)) if discord else 1.
    bci,hci=cp(benefit,n),cp(harm,n)
    savings=[r['total_saving'] for r in pairs];rng=random.Random(20261010)
    boot=sorted(statistics.mean(rng.choices(savings,k=len(savings))) for _ in range(20000))
    return {'n':n,'both_correct':both,'base_only_correct':harm,'skill_only_correct':benefit,'both_wrong':n-both-harm-benefit,
            'accuracy_delta':(benefit-harm)/n,'accuracy_delta_ci95':[bci[0]-hci[1],bci[1]-hci[0]],
            'accuracy_ci_method':'Bonferroni combination of two exact 97.5% Clopper-Pearson intervals for paired discordant-event probabilities',
            'mcnemar_exact_p':p,'mean_tokens_saved':statistics.mean(savings),'mean_saving_bootstrap_ci95':[boot[499],boot[19499]],
            'bootstrap_resamples':20000,'seed':20261010,'noninferiority_margin':.01,
            'noninferiority_established':bci[0]-hci[1]>-.01}

def write(name,text):
    (OUT/name).write_text(text.strip()+'\n')

def main():
    rows=jsonl(OUT/'task_results.jsonl');pairs=read_json(OUT/'data/task_pairwise.json');bank=read_json(OUT/'skill_bank_v2.json');skills=bank['skills']
    oldbank=read_json(OLD/'real_bank.json');clusters=read_json(OUT/'data/clusters.json');entries=read_json(OUT/'data/dev_tasks.json')
    calls=[read_json(p) for p in (OUT/'calls').glob('*.json') if 'response' in read_json(p)]
    manifest=read_json(OUT/'run_manifest.json');protocol=read_json(OUT/'protocol.json')
    summaries=[]
    for method in protocol['methods']:
        group=[r for r in rows if r['method']==method];correct=sum(r['correct'] is True for r in group)
        x={'method':method,'n':len(group),'correct':correct,'accuracy':correct/len(group),'unknown':sum(r['correct'] is None for r in group),
           **{k:sum(r[k] or 0 for r in group) for k in ['input_tokens','output_tokens','reasoning_tokens','total_tokens']},
           'api_calls':sum(r['llm_call_count'] for r in group),'injected':sum(r['skill_injected'] for r in group),'truncated':sum(r['truncated'] for r in group)}
        x.update(mean_tokens=x['total_tokens']/x['n'],tokens_per_correct=x['total_tokens']/correct);summaries.append(x)
    pair_stats={m:statistics_for([p for p in pairs if p['comparison']==m]) for m in ['B_OriginalContent','C_RevisedContent']}
    family_stats={f:statistics_for([p for p in pairs if p['comparison']=='C_RevisedContent' and p['family']==f]) for f in clusters}
    write_json(OUT/'data/aggregate_metrics.json',{'groups':summaries,'paired':pair_stats,'by_family':family_stats})
    csv_write(OUT/'data/group_metrics.csv',summaries)
    summary_table=md_table(['方法（独立开发20题）','正确','输入','输出','推理输出*','总tokens','调用','注入','截断'],
        [[s['method'],f"{s['correct']}/{s['n']} ({s['accuracy']:.0%})",s['input_tokens'],s['output_tokens'],s['reasoning_tokens'],s['total_tokens'],s['api_calls'],s['injected'],s['truncated']] for s in summaries])
    usage=[]
    for f in clusters:
        for m in protocol['methods']:
            rs=[r for r in rows if r['family']==f and r['method']==m]
            ps=[p for p in pairs if p['family']==f and p['comparison']==m]
            usage.append({'run_id':manifest['run_id'],'family':f,'method':m,'tasks':len(rs),
                          'retrieved':sum(bool(r['retrieved_skill_ids']) for r in rs),
                          'trigger_true':sum((r['trigger_result'] or {}).get('value') is True for r in rs),
                          'machine_verified_guards_passed':0,'solver_guard_obligations':sum(bool(r['guard_result']) for r in rs),
                          'router_injected':0,'shadow_experiment_injected':sum(r['skill_injected'] for r in rs),
                          'injected_correct':sum(r['skill_injected'] and r['correct'] is True for r in rs),
                          'injected_wrong':sum(r['skill_injected'] and r['correct'] is False for r in rs),
                          'base_fallback':sum(not r['skill_injected'] for r in rs),
                          'mean_saving_against_paired_nobank':statistics.mean(r['total_saving'] for r in ps) if ps else None})
    csv_write(OUT/'skill_usage.csv',usage)
    per_call=[{k:v for k,v in c.items() if k not in ('request','response')}|{
        'run_id':manifest['run_id'],'run_config_hash':manifest['solver_freeze']['config_hash'],
        'request_config_hash':digest(c['request']),
        'code_version':digest(manifest['solver_freeze']['code_hashes']) if c['purpose']=='shadow_validation' else None,
        'code_version_note':'frozen before all dev calls' if c['purpose']=='shadow_validation' else 'Per-attempt distiller code was not separately archived; raw requests and local schema corrections are preserved. Do not assign the later dev code hash to earlier distillation calls.',
        'task_id':c['job_id'].split('__',1)[1] if '__' in c['job_id'] else None,
        'log_path':'calls/'+c['call_id']+'.json'} for c in calls]
    dump_lines(OUT/'api_calls.jsonl',per_call)
    costs=[]
    for phase in ['trace_generation','distillation','skill_revision','skill_validation']:
        cs=[c for c in oldbank['cost_calls'] if c['purpose']==phase]
        costs.append({'run_id':manifest['run_id'],'scope':'historical_build','phase':phase,'calls':len(cs),
                      'input_tokens':sum(c['prompt_tokens'] for c in cs),'output_tokens':sum(c['completion_tokens'] for c in cs),'total_tokens':sum(c['total_tokens'] for c in cs)})
    for phase in ['distillation','skill_revision','shadow_validation']:
        cs=[c for c in calls if c['purpose']==phase]
        costs.append({'run_id':manifest['run_id'],'scope':'incremental','phase':phase,'calls':len(cs),
                      **{k:sum(c[k] for c in cs) for k in ['input_tokens','output_tokens','total_tokens']}})
    for phase in ['trace_processing','clustering','admission','online_retrieval','formal_test_inference']:
        costs.append({'run_id':manifest['run_id'],'scope':'incremental','phase':phase,'calls':0,'input_tokens':0,'output_tokens':0,'total_tokens':0})
    csv_write(OUT/'cost_breakdown.csv',costs)
    new_cost=sum(c['total_tokens'] for c in calls);old_cost=sum(c['total_tokens'] for c in oldbank['cost_calls'])
    estimated_usd={}
    for period,scale in [('off_peak',1),('peak',2)]:
        estimated_usd[period]=sum((c['response']['usage'].get('prompt_cache_hit_tokens',0)*.003+
          (c['input_tokens']-c['response']['usage'].get('prompt_cache_hit_tokens',0))*.15+c['output_tokens']*.6)*scale/1e6 for c in calls)
    # Coverage uses public questions only. It is potential trigger coverage, not
    # operational reuse. Production active coverage is actually zero.
    old_ids={r['task_id'] for r in jsonl(OLD/'manifests/dev.problems.jsonl')}
    unused=[r for r in jsonl(ROOT/'data/manifests/math_grouped/dev.problems.jsonl') if r['task_id'] not in old_ids]
    cache=read_json(OUT/'evidence/feature_cache.json');coverage={}
    for s in skills:
        skill=MacroSkill.model_validate(s);f=s['skill_id'].split('_')[0]
        coverage[f]=sum(evaluate(skill.trigger,cache[r['task_id']]['facts'])['value'] is True for r in unused if r['task_id'] in cache)/len(unused)
    conditional_per_task=sum(coverage[f]*family_stats[f]['mean_tokens_saved'] for f in coverage)
    projections=[{'future_tasks':n,'observed_production_coverage':0.,'current_frozen_bank_gross_saving':0,
        'if_all_shadow_skills_eventually_qualified_potential_coverage':sum(coverage.values()),
        'conditional_gross_tokens_saved':n*conditional_per_task,'conditional_net_incremental':n*conditional_per_task-new_cost,
        'conditional_net_full_reconstruction':n*conditional_per_task-new_cost-old_cost,'is_observation':False} for n in [500,1000,2000,5000]]
    csv_write(OUT/'data/amortization_scenarios.csv',projections)
    write_json(OUT/'data/cost_summary.json',{'incremental':new_cost,'full_historical_pipeline_plus_incremental':old_cost+new_cost,
        'historical_build':old_cost,'estimated_usd_range':estimated_usd,'billing_statement_observed':False,
        'potential_trigger_coverage_unused_dev':coverage,'unused_dev_denominator':len(unused),
        'bank_level_current_break_even_tasks':None,'reason':'no active production skills',
        'conditional_net_saving_definition':'N*sum(question_only_coverage*paired_mean_saving)-build_cost; not observed deployment'})
    comparison=[]
    dispositions={1:'tool menu; split before retraining',2:'OR/AND mismatch plus unrelated transformations; defer',3:'discrete/continuous/stopping-time mixture; defer',
      4:'revised partition/complement macro with equal-orbit guard',5:'geometry tool menu and composition lexical mismatch; defer',6:'apparent accuracy benefit was a unit-scoring artifact; defer',
      7:'reclustered actual denominator-reduction chains; remove hyperbola/series sources',8:'generic reduce/validate menu; defer',9:'integer constraint menu too broad; defer',
      10:'overly elementary rational arithmetic, overlap with S11; defer',11:'overly elementary with missing prefix-cycle guard; defer',12:'one historical false negative corrected, one true truncation remains; defer'}
    for idx,old in enumerate(oldbank['skills'],1):
        new=next((s for s in skills if s['predecessor']==old['skill_id']),None)
        comparison.append({'old_id':f'S{idx:02d}','old_skill_id':old['skill_id'],'old_subject':old['subject'],'old_status':old['status'],
            'old_estimated_short_tokens':estimate_tokens(old['compact_prompt']),'new_skill_id':new['skill_id'] if new else None,
            'new_status':new['status'] if new else 'not_redistilled','new_estimated_short_tokens':estimate_tokens(new['compact_prompt']) if new else None,
            'review':dispositions[idx]})
    csv_write(OUT/'data/skill_old_new_comparison.csv',comparison)
    write_json(OUT/'evidence/skill_representation_statistics.json',{'old_candidates':12,'new_candidates':len(skills),'active':0,'shadow':2,
        'estimated_short_tokens':{s['skill_id']:estimate_tokens(s['compact_prompt']) for s in skills},
        'short_prompt_sequence_similarity':SequenceMatcher(None,skills[0]['compact_prompt'],skills[1]['compact_prompt']).ratio(),
        'subjects':dict(Counter(s['subject'] for s in skills)),'source_counts':{f:len(c['source_traces']) for f,c in clusters.items()},
        'repeated_new_source_ids':len([t['problem']['task_id'] for c in clusters.values() for t in c['source_traces']])-len({t['problem']['task_id'] for c in clusters.values() for t in c['source_traces']})})
    # Save full three-group response evidence for every discordance.
    discordant_ids={p['task_id'] for p in pairs if p['base_correct'] is not p['skill_correct']}
    write_json(OUT/'evidence/discordant_cases.json',[{'task_id':tid,'problem':next(e['problem']['problem'] for e in entries if e['problem']['task_id']==tid),
        'responses':[r for r in rows if r['task_id']==tid],'interpretation':'NoBank exhausted output budget with empty visible answer; both original and revised skills completed a correct answer. Not evidence that a completed wrong derivation was corrected.'} for tid in sorted(discordant_ids)])
    historical=read_json(OUT/'data/historical_rechecked.json');diff=[r for r in historical if r['original_correct'] is not r['rechecked_correct']]
    eval_text='''# 评分器修复与历史复核

V2 使用独立离线评分入口 `v2/evaluator.py`。原始评分和旧评分器保留用于历史重放；V2 研究入口全部使用修复后的评分器。
全部提交校验 seal 后才打开标签；solver、Trigger、Router 不接收 gold 或判分反馈。新增测试包含未封存记录阻止 label IO、负号、未知表达式、集合/有序对/区间端点、截断与嵌套分数。

选择位置最后的显式最终答案或 balanced boxed，修复 first-answer 错取。题面明确给出单位时才移除对应尾随单位；数字/符号由 Math-Verify/SymPy 在最多12个进程中限时解析，禁用字符串 fallback。集合与有序对分开，不能安全判定的文本/格式记 unknown。截断记预算失败并保留所有 usage，绝不判对。

已知两例：geometry_367 的 `18 square centimeters` 对金标 `18` 经题面单位约束规范化为正确；precalculus_250 的末尾 `(A)` 被正确提取，与金标选项一致。完整例子和原始模型解答在 CSV/JSON 内。仍不支持任意自然语言、所有单位和多种选项+表达式混写；unknown 不等于数学错误。

以下是**历史离线复核**，不构成本轮新增测试成绩，原始正确数不变。保守解析新增 unknown，因此不可只看 rechecked_true 数就宣称模型准确率下降。
'''+md_table(['历史组','n','原始正确','复核确认正确','unknown'],[[m,v['n'],v['original_correct'],v['rechecked_correct'],v['unknown']] for m,v in read_json(OUT/'data/scoring_summary.json').items()])
    eval_text+=f'\n共复核 {len(historical)} 份封存答案，{len(diff)} 条评分状态不同。全部差异实例如下；完整题面、gold、解答和 seal 见 `data/scoring_disagreements.csv`。\n\n'
    eval_text+=md_table(['任务/方法','原→复核','提取答案','gold','原因'],[[r['task_id']+'/'+r['method'],str(r['original_correct'])+' → '+str(r['rechecked_correct']),r['answer'],r['gold_answer'],r['scoring_difference_reason']] for r in diff])
    write('reports/01_EVALUATOR_FIX.md',eval_text)
    write('reports/02_TRIGGER_GUARD_REDESIGN.md','''# Trigger / Guard 重设计

`v2/skills.py` 的严格 schema 支持 all_of / any_of / not / optional / guard；每个节点恰有一个操作符。三值逻辑保留 unknown，not unknown 仍为 unknown；optional 不阻断；guard 节点产生义务而不宣称已满足。

`v2/features.py` 将词面观察放在 lex 命名空间，将解析事实放在 math 命名空间。使用现有 latex2sympy2_extended 解析关系式，计算通分后分子/分母次数，识别单一重复根式代换、齐次比值代换；不再把 ^20 或含 x² 的三次多项式当作二次。保存分母原文和代换遗漏零值的检查义务。三角、模、整除、递推、顺序、重复和对称只提供有证据的事实；支持范围外的结构明确记 uncertain。

S07 触发为同学科 AND (可解析的有理方程 OR 有理不等式) AND 非三角 AND 非假设选项；低阶指通分/代换后的分子次数≤2，不代表整个题是二次。排除了题目选项中仅供判断的关系式。S04 为同学科、计数目标及约束词的交集，目前计数部分仍是可解释的语言启发式，非完整数学理解。

分母非零、乘除不等式的符号、回代与定义域、穷尽互斥分类、顺序重复、对称商的等轨道条件列为 Guard。短 prompt 明确要求求解时检查，不能验证时正常解题。实现还提供非零、符号、等轨道大小的纯数学检查函数及反例测试，但本轮没有调用可执行证明工具；日志中的 solver_obligation_unverified 不能读成 Guard 已通过。机器证明通过数为0。

来源自匹配及每题解释保存在 data/source_self_match.csv。新卡声称的9个来源全部匹配；旧卡中被移出的来源明确列出，不为追求100%保留双曲线、级数等不适用题。来源自匹配是内部一致性检查，不是泛化证明。''')
    write('reports/03_DISTILLER_IMPROVEMENTS.md',f'''# 多轨迹中粒度蒸馏

复用已有627条首轮正确、gold-free 的训练轨迹，未重跑训练。`v2/distiller.py` 同时要求题面结构匹配与成功解答中的多阶段变换证据，保存真实 span、摘录和 trace hash；不是靠单个 reduce/factor 单词聚类。

S07 保留3条：1030（不等式分母符号/排除极点）、902（重复根式代换/范围/回代）、704（齐次比值代换/通分）。S04 选6条具有分类/补集/计数修正链条的题，覆盖重复、顺序与对称。来源选择不读取开发或测试答案。两种 family、结构规则及安全条件是人工设计的先验；具体步骤和短文本由 DeepSeek 从真实轨迹提炼，不能称为从零自动发现算法。

全版本在 data/skills_v2_full.json，簇和证据在 data/clusters.json，来源路径保留。候选由12条旧卡缩为2条修订卡，不把其余10条复制进活跃库。逐条处置见 data/skill_old_new_comparison.csv。

执行了3次付费蒸馏/修订，21,573 tokens。S04 的两次输出曾被本地过严的同义词正则误拒；在开发结果产生前修复 repetition/distinguishability、all orbits equal 的识别，离线采用首次响应，未追加第三次S04调用。两次费用均保留。S07一次成功。此经历也说明字符串 guard 校验只是一道卫生检查，不能替代数学审阅。

短文本上限340 UTF-8 bytes、估计器上限120 tokens（目标约100）；实际两卡估计 {estimate_tokens(skills[0]['compact_prompt'])} / {estimate_tokens(skills[1]['compact_prompt'])}，这是 bytes/3 估计，非提供商 tokenizer 的精确长度。实际全请求输入 usage 另行记录。

两卡不同学科、不同变换链，来源无重叠。重复程度的文本相似度及来源数量见 evidence/skill_representation_statistics.json。''')
    dec=jsonl(OUT/'admission_decisions.jsonl')
    break_even=[]
    for s in skills:
        stats=s['validation_stats'];mean=stats['mean_saving'];cost=s['token_history']['admission_full_allocated_cost']
        break_even.append({'skill_id':s['skill_id'],'candidate_attributable_build_cost':cost,'mean_tokens_saved_per_use':mean,
                           'conditional_break_even_uses':math.ceil(cost/mean) if mean and mean>0 else None,
                           'reliable_break_even_demonstrated':False,'production_uses':0,
                           'qualification':'Conditional arithmetic only; saving lower bound is negative and no active admission.'})
    csv_write(OUT/'data/per_skill_amortization.csv',break_even)
    decision_table=md_table(['技能','dev n','benefit / harm','每次平均节省','节省95%下界','100次净收益（候选成本）','状态'],
        [[d['skill_id'],d['statistics']['n'],f"{d['statistics']['benefit']} / {d['statistics']['harm']}",round(d['statistics']['mean_saving'],2),round(d['statistics']['saving_lower_bound'],2),round(d['statistics']['projected_100_use_net_saving'],2),d['status']] for d in dec])
    write('reports/04_ADMISSION_V2.md','''# Admission V2 与生产路由

candidate 通过来源一致性和数学条件审阅进入 shadow。shadow 开发验证主动采集证据，不要求已有测试使用次数。缺少独立数据/unknown评分保持 shadow；确实不可靠的数学条件或观测负迁移进入 quarantine。无数据不再自动混入“有害”分类。来源不匹配退回 candidate。

数字门槛未降低：来源≥3，独立dev≥10，无已观测负迁移，有非数字换皮的文本去重证据，总token平均节省95%下界>0，平均节省×100>候选可归因建库成本。该成本含来源的原始真实API费用、本次所有蒸馏/修订、三组验证。全库历史成本另作保守端到端核算；不把所有无关旧卡成本硬摊到准入阈值。

'''+decision_table+'''
两卡均不能通过成本门槛，故冻结库为2 shadow、0 active，正式500停止。S04唯一正确率收益是完成了无策略截断的题；剔除此题仅作敏感性描述（主表仍计全部截断成本），其他9题累计多花1316 tokens，不能认定稳定收益。

生产 Router 数值规则未改：confidence=n/(n+10)≥0.8 需要 n≥40；无正负迁移时，原Wilson准确率下降上界≤1%约需381个独立样本。每卡10题 confidence=0.5，无法证明1pp非劣；此规则与20题试验目的/预算不匹配是明确限制。本轮实际零active的直接原因是成本证据，不可甩给 Router。即使出现active，只有完全符合原路由条件才有生产注入；不能用测试gold补冷启动。

Admission 统计中的 structurally_distinct 依据实际数字掩蔽文本去重计算，附带证据局限；不等同形式化证明数学结构新颖。来源跨变换的具体证据另存，未再无条件写True。''')
    skill_blocks=[]
    for s in skills:
        f=s['skill_id'].split('_')[0]
        skill_blocks.append('## '+s['skill_id']+' · '+s['name']+'\n\n'+
            '\n'.join(str(i)+'. '+step for i,step in enumerate(s['steps'],1))+'\n\n短策略：\n\n> '+s['compact_prompt']+
            '\n\n来源：'+', '.join(s['source_task_ids'])+f"。状态 **{s['status']}**；本轮实际shadow注入10次，生产注入0次。\n")
    write('02_SKILL_BANK_REPORT.md','''# Skill Bank V2

旧库12条：0 active、3 shadow、9 quarantine；全部原样保留。新库仅蒸馏2条：counting_probability 1条、intermediate_algebra 1条；均为shadow，0 active。没有足够证据展示3–5条有效技能，不补造卡片。

'''+decision_table+'\n'+'\n'.join(skill_blocks)+'\n完整 schema、trigger、guard、trace hashes、验证统计和token历史见 skill_bank_v2.json 与 data/skills_v2_full.json。')
    ci=pair_stats['C_RevisedContent'];a,b,c=summaries
    write('03_MATH500_RESULTS.md',f'''# 实验结果：开发验证完成，正式500未启动

**本轮没有新增MATH 500成绩。** 0条技能通过准入，根据《指引.txt》第7.4节及停止条件停止大规模调用。保留原500题manifest、内容hash、各学科构成；若未来运行只能称既有基准确认/回归，不能称全新holdout。

本轮结果为20道独立开发题的真实三组配对。13题来自此前未用的开发池，7题来自未使用的训练候选，均为原MATH训练拆分，不含最终测试题。S04/S07各10题，经来源/候选间近重复排除；选择只看题面结构。B组采用原内容与共同新trigger，是内容机制对照，不是原破损trigger端到端重跑。

{summary_table}
*reasoning_tokens 是输出tokens的子集，不再相加。每组平均1调用/题；新卡组20次shadow条件注入，非active生产注入。Guard机器验证通过0，20题有求解期义务；不报告虚构通过率。

新策略比NoBank **多 {c['total_tokens']-a['total_tokens']:,} tokens（{(c['total_tokens']/a['total_tokens']-1)*100:.2f}%）**；比旧策略多 {c['total_tokens']-b['total_tokens']:,}。输入增加 {c['input_tokens']-a['input_tokens']}，输出增加 {c['output_tokens']-a['output_tokens']}，推理输出增加 {c['reasoning_tokens']-a['reasoning_tokens']}。没有输出推理压缩的总体证据。每正确题tokens分别 {a['tokens_per_correct']:.2f}、{b['tokens_per_correct']:.2f}、{c['tokens_per_correct']:.2f}。

配对（C vs A）：两者正确 {ci['both_correct']}、仅NoBank正确 {ci['base_only_correct']}、仅新策略正确 {ci['skill_only_correct']}、两者失败 {ci['both_wrong']}。McNemar双侧精确p={ci['mcnemar_exact_p']:.3f}。正确率差 {ci['accuracy_delta']:.1%}，保守配对95%区间 [{ci['accuracy_delta_ci95'][0]:.1%}, {ci['accuracy_delta_ci95'][1]:.1%}]；对两个不一致事件概率使用97.5%精确二项区间并作Bonferroni组合。预先规定非劣界1pp，**未证明非劣**，不能用“不显著”替代。即便500题，也须看配对不一致数及区间，样本数本身不保证1pp精度。

平均每题节省（负数为增耗） {ci['mean_tokens_saved']:.2f}；20,000次按题配对bootstrap 95%区间 [{ci['mean_saving_bootstrap_ci95'][0]:.2f}, {ci['mean_saving_bootstrap_ci95'][1]:.2f}]。统计方法和种子固定20261010，机器结果在 data/aggregate_metrics.json。

历史500仅供背景：FlowEvo-GoldFree原始462/500，641,955tokens；旧Bot/NoBank等价请求原始464/500，523,020tokens。该组未与V2重新配对执行，不能拿开发20题成绩与其比较。历史复核另列original/rechecked/unknown，不覆盖原分数。

本轮新增成本 {new_cost:,} tokens / {len(calls)}调用；保留完整历史建库路径再计新增为 {old_cost+new_cost:,}。正式测试解题成本为未运行，不能以0成本伪称500题节省。''')
    write('04_MECHANISM_ANALYSIS.md',f'''# 机制归因与成本

两条真实多轨迹学习的短策略确实出现在20份C组请求中，具有题面trigger和求解期条件指令；不存在active生产使用。B组也注入20题。模型是否完全按策略执行无法仅凭正确答案证明；本轮未配备可执行证明工具，Guard结果保留未机器验证。

唯一正迁移为 math_train_counting_probability_306：四小三角形拼成大三角形、6种颜色、旋转反射等价。无策略在4096输出上限内只有推理、没有可见最终答案；B/C均完成中心6选×角部三重多重集56=336。新旧两种内容都成功，因此不能归因于V2修订条件，也不能说纠正了基础模型已提交的错误推导。完整三组解答、调用和用量在 evidence/discordant_cases.json。math_train_counting_probability_444 三组都截断，所有成本仍计入。

S04每题平均省85 tokens，但95%下界−389.24；唯一上述案例省2166，其余9题合计增耗1316。S07每题增耗370.1，无准确率改变。修复结构使技能获得了可验证的覆盖，尚未使宏策略稳定替代推理。实际请求相同模型别名、system、基础题面、输出格式、temp=0请求和4096上限，全组交错随机顺序在单一64线程池中执行；没有数学重试。

Provider返回 deepseek-flash 别名，当前官方文档映射V4.1-Flash，但不可变后端版本未知。thinking省略，依提供方默认enabled/high，temperature可能无效；一次独立采样不能保证因果效果可重复。题面匹配和数字掩蔽去重也不是语义泛化的充分证明。

成本：旧训练795435、首次失败蒸馏75090、旧修订94822、旧验证104384，完整旧建库1069731。新增蒸馏/修订21573，新增三组验证80743，合计 **{new_cost:,}**。轨迹整理/聚类/Admission/Router本地执行，不新增API。历史已花费用不记为零；完整研究路径重建合计 **{old_cost+new_cost:,} tokens**，不含旧500题测试消耗。包含旧测试的累计物理研究消耗另为2234706+{new_cost}={2234706+new_cost}。

按实际usage及官方缓存/非缓存费率，本轮粗估美元区间 [{estimated_usd['off_peak']:.6f}, {estimated_usd['peak']:.6f}]；这不是账户账单。价格来源 https://api-docs.deepseek.com/quick_start/pricing ，峰/谷、余额赠送、后端计费变化可影响账单。

准入使用每条候选可归因成本（来源真实采集+该候选蒸馏修订+其三组验证），S04 65302、S07 45161 tokens；全库沉没成本在上段完整披露。这两个口径不能混成“已有历史免费”。

当前冻结库active覆盖0，无有限生产回本点。500/1000/2000/5000题条件预测在 data/amortization_scenarios.csv：实际当前路由预计复用0；另给出假设所有shadow未来获准、保持观察到的结构覆盖和开发均值的情景，不能当作测试成绩。潜在trigger覆盖以未使用开发池{len(unused)}题为分母，S04={coverage['S04']:.2%}、S07={coverage['S07']:.2%}，与20题定向采样的100%注入率不同。建库支出未被本轮抵消。''')
    with (OUT/'04_MECHANISM_ANALYSIS.md').open('a') as f:
        f.write('\n单卡条件回本：若S04每次85 tokens的均值能独立复现，候选成本65302/85需向上取整为769次有效复用；由于节省区间跨0且无active资格，这不是可信或已实现的回本承诺。S07均值为负，无有限回本次数。详见 data/per_skill_amortization.csv。\n')
    write('05_NEXT_ITERATION.md','''# 下一轮建议

当前最明确的改进是修复内部一致性和观测：9条来源可自匹配、20题能开展真实对照、已知评分假象被剔除、证据不足与有害状态分开。尚未获得节省总token的有效active技能。

优先研究为什么短策略未能减少推理输出。S04平均节省被一个截断完成案例驱动，旧内容也获得同样正确率；建议下一轮先在独立开发题上重复少量交错采样，区分稳定计算捷径与随机长度变化。不要把本轮20题多次调参后的结果当作新证据。

S07覆盖从旧关键词阻断中恢复，却整体增耗。可将“直接有理不等式符号表”“重复根式代换”“齐次比值消元”拆成更具体的宏，前提是各自有至少3条真实变换来源；当前某些子族只有单例，继续保留候选，不能放宽来源数硬激活。

Guard目前只是带义务的自然语言执行。下一步可建立小型可执行代数检查来核实分母零点、符号分段、回代覆盖及对称轨道条件，求解前后均不得读取gold。不能为了省token而删去关键条件。对计数图形/自然语言复杂约束，保守回退仍合理。

Router原confidence和1pp风险门槛明显需要更多独立样本，但本轮成本本身未过关，不应立即花381题/技能证明亏损策略。先固定更窄的有潜力宏，再单独规划开发预算、风险界和精度；不得拿正式测试gold积累准入证据。500题同样不能无条件证明1pp非劣。

目前不值得默认研究多Skill组合或多次求解；单卡收益和可执行安全条件尚未成立。方法方向值得做有限、预先限定预算的进一步验证，但当前证据不足以支持论文中的成本优势或自动技能泛化主张。本轮不追加新API实验。''')
    write('01_IMPLEMENTATION_REPORT.md','''# V2 实现与验证

本轮完成独立版本的算法实现、离线测试、真实蒸馏及20题三组对照；0 active触发停止条件，未执行正式500。原FlowEvo、BoT、旧实验结果、旧银行与旧评分均保留。

新增核心模块：src/flowevo_bot/v2/evaluator.py（封存后分级评分）、features.py（词面/数学结构拆分）、skills.py（递归逻辑schema和数学guard）、distiller.py（多阶段真实变换证据蒸馏）、admission.py（shadow/准入/生产路由）、client.py（单预算、安全原始日志、429/503有界基础设施重试、待定请求日志）。执行入口 scripts/run_v2_research.py；离线历史复核 scripts/recheck_v2_history.py；报告 scripts/report_v2_research.py。

为了保留历史可重放，V2不覆盖旧v1 evaluator/runner；V2研究脚本明确调用新模块。原CLI仍为v1，使用V2必须运行此处新入口。原FlowEvo的gold-free数学路径保持关闭gold反思及正确性驱动重试，MATH/GSM技能注入此前修改保留。

各阶段技术细节在reports/01–04，完整新旧卡对照与真实来源在data/。不改Router数值门槛；独立shadow验证可绕过生产成本路由采集开发证据，但不能生产强制注入。

所有模型请求/完整响应（含服务端reasoning_content和usage）保存在calls/，无请求头/密钥。单一API线程池上限64，本地评分/结构提取进程上限12，进程CPU亲和性限制12个核。未记录任何数学重试；基础设施仅明确429/503最多3次尝试，超时/未知完成状态保留journal并停止，避免盲目重复计费。此次所有63调用一次成功，输出截断均保留并计费。

预付费测试87通过；增加蒸馏同义词/危险对称压缩回归后完整测试90通过（tests/final_tests.log及Junit）；原FlowEvo两项gold-free回归通过。0.2.0 wheel构建、隔离导入、判分smoke和compileall通过，见tests/build_verification.json。历史源代码归档 snapshots/source_before_v2.zip，实际dev运行代码归档 snapshots/runtime_used_for_dev.zip，原历史文件SHA快照及最终复核在evidence/。蒸馏各次调用前未单独归档当时全模块代码，api_calls如实保留code_version=null及原始请求hash；不能倒填后来的dev代码hash。密钥miyao.txt只用于内存授权，不发布。

局限：数学解析保守unknown、当前Guard没有执行证明、计数trigger部分词面、训练轨迹正确性依赖历史评分且数学步骤未被形式化证明、source/dev语义独立性不能完全保证、单次DeepSeek别名采样无法锁定后端版本。输出长度截断可改变表面正确率，因此逐题区分预算失败和完成后的数学错误。''')
    write('README.md','''# Flowevo-Bot V2 研究包

阅读顺序：01_IMPLEMENTATION_REPORT.md → 02_SKILL_BANK_REPORT.md → 03_MATH500_RESULTS.md → 04_MECHANISM_ANALYSIS.md → 05_NEXT_ITERATION.md。

本轮63次真实调用，20题三组对照；没有技能通过active准入，按指引停止正式500。不得将本目录名误解为已产生新的500题成绩。

机器入口：task_results.jsonl、task_pairwise.csv、skill_usage.csv、skill_bank_v2.json、skill_validation.csv、admission_decisions.jsonl、cost_breakdown.csv、api_calls.jsonl、dataset_manifest.json、run_manifest.json。

重放报告（不联网）：在Flowevo-Bot项目根目录执行 `.venv/bin/python scripts/report_v2_research.py`；完整验证 `.venv/bin/python -m pytest -q tests`，实验完整性验证 `.venv/bin/python scripts/verify_v2_research.py`。历史评分复核入口 scripts/recheck_v2_history.py，仅新增本目录文件。

复现执行阶段：`python scripts/run_v2_research.py prepare`、`distill --allow-paid-api`、`dev --allow-paid-api`。保留现有calls/submissions时使用缓存不重复请求；不要随意删除journal或修改冻结配置。为避免覆盖本次结果，开展新实验须复制脚本配置并使用新实验目录；本目录只用于同一冻结运行的恢复/审计。

报告和源码均随每轮同步到 https://github.com/ChenKaichen-SCUT/Flowevo-Bot 。API凭据与虚拟环境不随包发布。''')
    (OUT/'evidence/provider_pricing.txt').write_text('Source: https://api-docs.deepseek.com/quick_start/pricing\nRetrieved 2026-10-10 Asia/Shanghai. USD per million tokens.\nFlash peak: cache hit 0.006, cache miss 0.30, output 1.20.\nFlash off-peak: cache hit 0.003, cache miss 0.15, output 0.60.\nCost estimates are not a billing statement.\n')
    manifest['report_generated_at']=datetime.now(timezone(timedelta(hours=8))).isoformat();manifest['results_summary']=summaries
    write_json(OUT/'run_manifest.json',manifest)
    print(json.dumps({'new_tokens':new_cost,'full_cost':old_cost+new_cost,'paired_C':ci,'cost_estimate_usd':estimated_usd,'reports':'generated'}),flush=True)

if __name__=='__main__':main()
