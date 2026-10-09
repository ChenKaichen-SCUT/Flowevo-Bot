"""Bounded real-bank construction and paired native-FlowEvo comparison."""
import concurrent.futures as cf
import multiprocessing
import subprocess
from collections import defaultdict,Counter
from pathlib import Path
from .common import read_json,write_json,jsonl,digest,now
from .schemas import Trace,SkillRecord,Submission,EvaluationRecord
from .strategy_bank import StrategyBank
from .thought_distiller import ThoughtDistiller,cluster_traces
from .skill_validator import SkillValidator
from .provenance import eligible,assert_independent
from .features import matches,extract_features,normalize_problem
from .token_accounting import TokenLedger,estimate_tokens
from .parallel_experiment import RecordedClient,run_parallel
from .math_solver import MathSolver
from .experiment_grader import grade_one
from code_math.loader import load_manifest


def selected_clusters(history,limit=12):
    groups=defaultdict(list)
    for c in cluster_traces(history,3):groups[c[0].problem.subject].append(c)
    for subject in groups:groups[subject].sort(key=lambda c:(-len(c),c[0].problem.task_id))
    result=[]
    while any(groups.values()) and len(result)<limit:
        for subject in sorted(groups):
            if groups[subject] and len(result)<limit:result.append(groups[subject].pop(0)[:6])
    return result


def all_ledgers(directory):
    ledger=TokenLedger()
    for path in sorted(Path(directory).rglob('*.calls.json')):
        child=TokenLedger(path)
        for c in child.calls:
            if c.call_id not in ledger.responses:ledger.append(c,child.responses[c.call_id],child.prompts.get(c.call_id))
        ledger.failures.update(child.failures)
    return ledger


def validate_batch(config,candidates,dev_manifest,directory):
    directory=Path(directory)
    info,dev,labels=load_manifest(dev_manifest,'train-dev')
    identity={'config':digest(config.model_dump()),'candidates':digest([s.model_dump(mode='json') for s in candidates]),'dev':digest(info)}
    if (directory/'identity.json').exists():
        if read_json(directory/'identity.json')!=identity:raise ValueError('Validation resume identity mismatch')
    else:write_json(directory/'identity.json',identity)
    selected={}
    for s in candidates:
        unique={}
        for t in dev:
            if t.subject==s.subject and matches(s,extract_features(t)):
                unique.setdefault(normalize_problem(t.problem,True),t)
        selected[s.skill_id]=list(unique.values())[:60]
    union={t.task_id:t for tasks in selected.values() for t in tasks}
    jobs=[('base',t,StrategyBank(frozen=True),'base_onepass') for t in union.values()]
    for s in candidates:
        bank=StrategyBank([s],frozen=True)
        jobs.extend((s.skill_id,t,bank,'subject_strategy') for t in selected[s.skill_id])
    def paths(key,tid):return directory/key/(tid+'.submission.json'),directory/key/(tid+'.calls.json')
    def worker(job):
        key,task,bank,mode=job
        subpath,callpath=paths(key,task.task_id)
        if subpath.exists():
            sub=Submission.model_validate(read_json(subpath));sub.assert_frozen()
            if sub.bank_hash!=bank.bank_hash:raise ValueError('Validation bank mismatch')
            return sub
        client=RecordedClient(config.llm,TokenLedger(callpath),allow_paid=True)
        sub=MathSolver(client,config,bank,mode).solve(task,split='train-dev',purpose='skill_validation')
        write_json(subpath,sub.model_dump(mode='json'))
        return sub
    submissions={};errors={}
    with cf.ThreadPoolExecutor(max_workers=64) as pool:
        futures={pool.submit(worker,job):(job[0],job[1].task_id) for job in jobs}
        for f in cf.as_completed(futures):
            key=futures[f]
            try:submissions[key]=f.result()
            except Exception as exc:errors['/'.join(key)]=str(exc)[:300]
            if len(submissions)%25==0 or errors:
                print('VALIDATION',len(submissions),'/',len(jobs),'errors',len(errors),flush=True)
    if errors:
        write_json(directory/'errors.json',errors)
        raise RuntimeError('Validation requests failed; inspect saved journals')
    # No evaluation record was opened until all paired responses were durable.
    evaluations=[EvaluationRecord.model_validate(x) for x in jsonl(labels)]
    if digest([e.model_dump(mode='json') for e in evaluations])!=info['labels_hash']:raise ValueError('Validation label hash mismatch')
    index={e.task_id:e for e in evaluations}
    keys=sorted(submissions)
    items=[];ledgers={}
    for key in keys:
        sub=submissions[key];sub.assert_frozen()
        ledger=TokenLedger(paths(*key)[1]);ledgers[key]=ledger
        items.append((sub.task_id,sub.final_answer,index[sub.task_id].gold_answer,bool(ledger.failures)))
    with cf.ProcessPoolExecutor(max_workers=12,mp_context=multiprocessing.get_context('spawn')) as pool:
        scores=dict(zip(keys,pool.map(grade_one,items,chunksize=4)))
    validated=[]
    for skill in candidates:
        rows=[]
        for t in selected[skill.skill_id]:
            b=('base',t.task_id);s=(skill.skill_id,t.task_id)
            bc=ledgers[b].totals();sc=ledgers[s].totals()
            rows.append({'task_id':t.task_id,'problem_hash':digest(normalize_problem(t.problem)),
                'problem_tokens':estimate_tokens(t.problem),'base_correct':scores[b]['final_correct'],
                'skill_correct':scores[s]['final_correct'],'base_tokens':bc['total_tokens'],'skill_tokens':sc['total_tokens'],
                'base_input_tokens':bc['prompt_tokens'],'base_output_tokens':bc['completion_tokens'],
                'skill_input_tokens':sc['prompt_tokens'],'skill_output_tokens':sc['completion_tokens'],
                'fallback_tokens':0,'calls':bc['calls']+sc['calls'],'base_seal':submissions[b].seal,'skill_seal':submissions[s].seal,
                'structurally_distinct':True})
        validator=SkillValidator(config)
        stats=validator.summarize(rows,len(dev),False)
        data=skill.model_dump()
        data.update(validation_stats=stats.model_dump(),status='shadow',admission_certificate='',
                    estimated_coverage=len(rows)/len(dev),token_stats={**skill.token_stats,'validation':sum(r['base_tokens']+r['skill_tokens'] for r in rows)})
        result=validator.admit(SkillRecord.model_validate(data))
        validated.append(result)
        write_json(directory/(skill.skill_id+'.validation.json'),result.model_dump(mode='json'))
    return validated,all_ledgers(directory)


def build_experiment_bank(config,out):
    out=Path(out);bank_path=out/'real_bank.json'
    if bank_path.exists():return StrategyBank.load(bank_path)
    traces=[Trace.model_validate(t) for t in read_json(out/'train/traces.json')]
    history=[t for t in traces if eligible(t)]
    _,dev,_=load_manifest(out/'manifests/dev.json','train-dev')
    _,test,_=load_manifest(out/'manifests/test.json','test')
    assert_independent([t.problem for t in history],dev+test)
    clusters=selected_clusters(history)
    work=out/'distillation_v2';work.mkdir(exist_ok=True)
    write_json(work/'cluster_manifest.json',[[t.problem.task_id for t in c] for c in clusters])
    def distill(cluster):
        key=digest([t.trace_hash for t in cluster])[:16]
        path=work/(key+'.candidate.json')
        if path.exists():
            result=read_json(path)
            return SkillRecord.model_validate(result) if result else None
        # Distillation is a separate construction cost; test generation remains
        # capped at 4096 for BOTH methods. Keep the first rejected attempt too.
        distill_config=config.llm.model_copy(update={'max_output_tokens':16384,'timeout':300})
        client=RecordedClient(distill_config,TokenLedger(work/(key+'.calls.json')),allow_paid=True)
        try:
            skill=ThoughtDistiller(client,config).distill(cluster,purpose='skill_revision',
                revision_note='Earlier construction attempt failed JSON completion or feature-vocabulary validation. Return complete schema-compliant JSON and obey trigger_contract. No evaluation labels are available.')
            if skill:
                skill=skill.model_copy(update={'skill_id':cluster[0].problem.subject+'_'+key})
            write_json(path,skill.model_dump(mode='json') if skill else None)
            return skill
        except (ValueError,TypeError,KeyError) as exc:
            # Malformed candidates are rejected, not repaired using labels or hand-written strategies.
            write_json(work/(key+'.rejected.json'),{'error_type':type(exc).__name__,'message':str(exc)[:1000]})
            write_json(path,None)
            return None
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        candidates=[s for s in pool.map(distill,clusters) if s is not None]
    write_json(out/'candidates.json',[s.model_dump(mode='json') for s in candidates])
    print('DISTILLATION',len(history),'clean traces',len(clusters),'clusters',len(candidates),'valid candidates',flush=True)
    # Dedup before dev validation; rejected candidates still count in ledger costs.
    temporary=StrategyBank();unique=[];duplicates=[]
    for s in candidates:
        if temporary.duplicate(s):duplicates.append(s.skill_id)
        else:temporary.add(s);unique.append(s)
    validated,validation_ledger=validate_batch(config,unique,out/'manifests/dev.json',out/'validation_v2')
    bank=StrategyBank(validated);bank.history=history
    source=TokenLedger(out/'train/calls.json');distillation=all_ledgers(out/'distillation');revision=all_ledgers(work)
    bank.cost_calls=source.calls+distillation.calls+revision.calls+validation_ledger.calls
    if len({c.call_id for c in bank.cost_calls})!=len(bank.cost_calls):raise ValueError('Duplicate bank cost IDs')
    bank.build_costs={'trace_generation':source.totals()['total_tokens'],'distillation':distillation.totals()['total_tokens'],
                      'validation':validation_ledger.totals()['total_tokens'],'maintenance':revision.totals()['total_tokens']}
    bank.save(bank_path)
    write_json(out/'history.json',[t.model_dump(mode='json') for t in history])
    write_json(out/'bank_summary.json',{'clean_traces':len(history),'source_questions':len(traces),'clusters':len(clusters),
        'candidates':len(candidates),'duplicate_candidates':duplicates,'skills':len(bank.skills),
        'statuses':dict(Counter(s.status for s in bank.skills.values())),'build_costs':bank.build_costs,
        'build_token_totals':{'prompt_tokens':sum(c.prompt_tokens for c in bank.cost_calls),
                            'completion_tokens':sum(c.completion_tokens for c in bank.cost_calls),
                            'total_tokens':sum(c.total_tokens for c in bank.cost_calls),'calls':len(bank.cost_calls)},
        'skills_detail':[{'skill_id':s.skill_id,'name':s.name,'status':s.status,'dev_cases':s.validation_stats.eligible_cases,
            'harmful_cases':s.validation_stats.base_only_correct,'beneficial_cases':s.validation_stats.skill_only_correct,
            'saving_lower_bound':s.validation_stats.saving_lower_bound,'confidence':s.validation_stats.confidence} for s in bank.skills.values()],
        'bank_hash':bank.bank_hash,'frozen_at':now()})
    return bank


def compare_experiment(config,out,native_root):
    out=Path(out);native_root=Path(native_root)
    bank=StrategyBank.load(out/'real_bank.json')
    promptpath=out/'native_prompts.json'
    if not promptpath.exists():
        subprocess.run([str(native_root/'.venv/bin/python'),str(native_root/'scripts/export_goldfree_math_prompts.py'),
            '--problems',str(out/'manifests/test.problems.jsonl'),'--history',str(out/'history.json'),'--output',str(promptpath)],check=True)
    artifact=read_json(promptpath)
    # Verify native source has not changed since prompt export.
    import hashlib
    if hashlib.sha256(Path(artifact['implementation']).read_bytes()).hexdigest()!=artifact['implementation_sha256']:
        raise ValueError('Native FlowEvo changed after prompt export')
    exported={r['task_id']:r for r in artifact['prompts']}
    first,_=run_parallel(config,out/'manifests/test.json',bank,'native_flowevo_goldfree',out/'flowevo',
                         exported=exported,resume=(out/'flowevo/checkpoint.json').exists())
    second,_=run_parallel(config,out/'manifests/test.json',bank,'subject_strategy_costaware',out/'flowevo_bot',
                          resume=(out/'flowevo_bot/checkpoint.json').exists())
    report_comparison(out,first,second,bank)


def report_comparison(out,first,second,bank):
    a=read_json(out/'flowevo/rows.json');b=read_json(out/'flowevo_bot/rows.json')
    if [r['task_id'] for r in a]!=[r['task_id'] for r in b]:raise ValueError('Paired test IDs differ')
    if first['manifest_hash']!=second['manifest_hash']:raise ValueError('Manifest mismatch')
    for k in ('model','temperature','max_output_tokens'):
        if first[k]!=second[k]:raise ValueError('Model settings differ')
    pairs=[{'task_id':x['task_id'],'subject':x['subject'],'level':x['level'],
            'flowevo_correct':x['final_correct'],'bot_correct':y['final_correct'],
            'flowevo_tokens':x['total_tokens'],'bot_tokens':y['total_tokens'],
            'tokens_saved':x['total_tokens']-y['total_tokens']} for x,y in zip(a,b)]
    saving=first['total_tokens']-second['total_tokens']
    build=bank.build_costs
    common=build['trace_generation'];extra=sum(build.values())-common
    result={'flowevo':first,'flowevo_bot':second,'paired_count':len(pairs),
        'both_correct':sum(r['flowevo_correct'] and r['bot_correct'] for r in pairs),
        'flowevo_only_correct':sum(r['flowevo_correct'] and not r['bot_correct'] for r in pairs),
        'bot_only_correct':sum(not r['flowevo_correct'] and r['bot_correct'] for r in pairs),
        'both_wrong':sum(not r['flowevo_correct'] and not r['bot_correct'] for r in pairs),
        'accuracy_difference_percentage_points':100*(second['accuracy']-first['accuracy']),
        'solve_tokens_saved':saving,'solve_token_reduction_fraction':saving/first['total_tokens'],
        'shared_history_build_tokens':common,'bot_extra_build_tokens':extra,
        'flowevo_end_to_end_tokens':first['total_tokens']+common,
        'bot_end_to_end_tokens':second['total_tokens']+common+extra,
        'end_to_end_tokens_saved':saving-extra,'build_breakdown':build,
        'selection':read_json(out/'protocol.json'),'bank':read_json(out/'bank_summary.json')}
    write_json(out/'comparison.json',result);write_json(out/'paired_results.json',pairs)
    import csv
    with (out/'paired_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    lines=['# FlowEvo 无 gold 反思 vs Flowevo-Bot：MATH 500 题实测','',
        '本地 MATH 测试集按学科和难度分层抽样，非标准 MATH-500。两者使用同一批题、相同模型设置和冻结训练历史。',
        '', '| 方法 | 正确题数 | 正确率 | 输入 token | 输出 token | 测试总 token | 每题平均 token |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for name,s in [('FlowEvo（关闭 gold 反思）',first),('Flowevo-Bot（成本感知模式）',second)]:
        lines.append(f"| {name} | {s['correct']}/{s['count']} | {s['accuracy']:.2%} | {s['prompt_tokens']:,} | {s['completion_tokens']:,} | {s['total_tokens']:,} | {s['mean_tokens']:.2f} |")
    lines+=['',f"Flowevo-Bot 正确率差值 {result['accuracy_difference_percentage_points']:+.2f} 个百分点；测试 token 节省 {saving:,}（{result['solve_token_reduction_fraction']:.2%}）。",'',
        f"共同训练历史生成：{common:,} token；Bot 额外蒸馏与验证：{extra:,} token。包括建库后，FlowEvo 共 {result['flowevo_end_to_end_tokens']:,}，Bot 共 {result['bot_end_to_end_tokens']:,} token。",'',
        f"训练题 700，独立验证题 350；首次正确且无 gold 暴露的历史 {len(bank.history)} 条；策略状态 {dict(Counter(s.status for s in bank.skills.values()))}。",'',
        f"FlowEvo 路由：{first['routes']}；Flowevo-Bot 路由：{second['routes']}。未使用策略的题由原始模型直接求解，不代表策略复用有效。",'',
        '每题只生成一次，不依据 gold 重试，不从测试题入库。API 并发上限 64，评分进程 12，本地 CPU affinity 12 核；temperature=0，max_output_tokens=4096。',
        'FlowEvo 使用原仓库 CodeSkillLibrary 与 build_goldfree_math_prompt 导出的原生 prompt，共用 API 传输及评分器，避免客户端和评分差异。',
        '评分：math-verify 0.8.0 的符号等价验证，加保守文本/分数相等；评分只在提交封存后执行。另保留严格字符串归一化分数。',
        '模型输出被截断的题按错误统计，token 全部计入。每次 API usage 的输入和输出 token 都保存，缺失 usage 会显式标为估算。',
        '本次为单次配对样本结果，不能据此断言普遍显著优势；测试集曾经的其他暴露情况未知。',
        '', '逐题 CSV：paired_results.csv；完整设置和成本：comparison.json；逐请求 prompt/response/usage：flowevo/calls.json 和 flowevo_bot/calls.json。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print('COMPARISON FINISHED', {k:result[k] for k in ('accuracy_difference_percentage_points','solve_tokens_saved','end_to_end_tokens_saved')},flush=True)
