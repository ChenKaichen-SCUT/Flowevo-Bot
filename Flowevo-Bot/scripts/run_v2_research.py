"""Staged V2 study. Preparation and all selection are question-only.

Run from project root. Paid commands require --allow-paid-api; no key is printed.
This protocol is a 20-task shadow study. A failed advancement gate never launches
the 500-task experiment and does not tune thresholds to make it run.
"""
import argparse
import concurrent.futures as cf
import csv
from datetime import datetime,timezone,timedelta
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import random
import sys

from code_math.baseline import base_prompt
from flowevo_bot.common import digest,read_json,write_json,jsonl
from flowevo_bot.schemas import ProblemView,Trace
from flowevo_bot.provenance import assert_clean_traces,assert_independent
from flowevo_bot.features import normalize_problem
from flowevo_bot.token_accounting import estimate_tokens
from flowevo_bot.v2.features import extract
from flowevo_bot.v2.skills import MacroSkill,evaluate,trigger_for,guarded_obligations
from flowevo_bot.v2.distiller import transformation_evidence,distill_prompt,build_skill
from flowevo_bot.v2.client import Client,Budget
from flowevo_bot.v2.evaluator import seal,score_sealed,assert_sealed
from flowevo_bot.v2.admission import decide,route_reason,THRESHOLDS

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'experiments/math500_goldfree_20261009'
OUT=ROOT/'experiments/flowevo_bot_v2_math500'
RUN_ID='flowevo_bot_v2_math500'
FAMILIES=('S04','S07')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump_lines(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
def csv_write(path,rows,columns=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    keys=columns or sorted({k for r in rows for k in r})
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def public_features(row):return row['task_id'],extract(ProblemView.model_validate(row))
def source_code_hashes():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src/flowevo_bot/v2').glob('*.py'))}

def prepare():
    if (OUT/'evidence/solver_frozen_before_dev.json').exists():
        raise ValueError('This run is frozen; preparation cannot overwrite its manifests. Use a new experiment directory.')
    bank=read_json(OLD/'real_bank.json');history=bank['history']
    assert_clean_traces([Trace.model_validate(t) for t in history],3)
    oldskills={'S04':bank['skills'][3],'S07':bank['skills'][6]}
    pool=jsonl(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')
    olddev={r['task_id'] for r in jsonl(OLD/'manifests/dev.problems.jsonl')}
    trainpool=jsonl(ROOT/'data/manifests/math_grouped/train.problems.jsonl')
    used_train={r['task_id'] for r in jsonl(OLD/'manifests/train.problems.jsonl')}
    target_subjects={'counting_probability','intermediate_algebra'}
    fresh=[r for r in pool if r['subject'] in target_subjects and r['task_id'] not in olddev]
    supplement=[r for r in trainpool if r['subject'] in target_subjects and r['task_id'] not in used_train]
    source_questions=[t['problem'] for t in history if t['problem']['subject'] in target_subjects]
    # Question-only structure extraction. All workers share the same 12-process cap.
    cache={}
    with cf.ProcessPoolExecutor(max_workers=12,mp_context=mp.get_context('spawn')) as executor:
        cache.update(executor.map(public_features,source_questions+fresh,chunksize=5))
    clusters={};all_source_rows=[]
    for family in FAMILIES:
        candidates=[]
        for trace in history:
            tid=trace['problem']['task_id']
            if tid not in cache:continue
            ev=transformation_evidence(trace,cache[tid],family)
            if ev:candidates.append((trace,ev))
        # Diverse transformations, deterministic order, no dev/test outcomes.
        candidates.sort(key=lambda t:digest({'seed':20261010,'id':t[0]['problem']['task_id']}))
        chosen=[];seen=set()
        for pair in candidates:
            signature=digest(pair[1]['structural_signature'])
            if signature not in seen:chosen.append(pair);seen.add(signature)
        chosen=(chosen+[x for x in candidates if x not in chosen])[:6]
        if len(chosen)<3:raise RuntimeError(f'{family}: only {len(chosen)} coherent existing sources; do not manufacture a multi-trace skill')
        clusters[family]={'predecessor':oldskills[family]['skill_id'],'source_traces':[t for t,e in chosen],
                          'evidence':[e for t,e in chosen],'eligible_source_count':len(candidates),'selection':'distinct transformation signatures then hash order; max6'}
        claimed={t['problem']['task_id'] for t,e in chosen}
        for tid in sorted(set(oldskills[family]['source_task_ids'])|claimed):
            result=evaluate(trigger_for(family),cache[tid]['facts'])
            all_source_rows.append({'family':family,'task_id':tid,'old_source':tid in oldskills[family]['source_task_ids'],
                'claimed_v2_source':tid in claimed,'trigger_match':result['value'],'explanation':result,
                'cluster_decision':'retained/new coherent transformation' if tid in claimed else 'removed: outside narrower macro or no matching transformation chain'})
    selected=[];selection_logs=[]
    histories=[ProblemView.model_validate(t['problem']) for t in history]
    # First use previously unused dev. Supplement unused train only if necessary.
    for family in FAMILIES:
        eligible=[r for r in fresh if evaluate(trigger_for(family),cache[r['task_id']]['facts'])['value'] is True]
        source='grouped_dev_unused'
        if len(eligible)<10:
            missing=[r for r in supplement if r['task_id'] not in cache]
            with cf.ProcessPoolExecutor(max_workers=12,mp_context=mp.get_context('spawn')) as executor:
                cache.update(executor.map(public_features,missing,chunksize=5))
            eligible += [r for r in supplement if evaluate(trigger_for(family),cache[r['task_id']]['facts'])['value'] is True]
            source='grouped_dev_then_unused_train'
        # Prioritize dev over supplement; within each split use frozen hash order.
        fresh_ids={r['task_id'] for r in fresh}
        eligible.sort(key=lambda r:(r['task_id'] not in fresh_ids,digest({'seed':20261010,'id':r['task_id']})))
        chosen=[]
        for r in eligible:
            p=ProblemView.model_validate(r)
            try:assert_independent(histories+[ProblemView.model_validate(x['problem']) for x in selected+chosen], [p])
            except ValueError:
                selection_logs.append({'task_id':r['task_id'],'family':family,'reason':'source/selected-task near duplicate'});continue
            label_source='dev' if r['task_id'] in fresh_ids else 'train'
            chosen.append({'family':family,'problem':r,'features':cache[r['task_id']],
                           'labels_path':f'data/manifests/math_grouped/{label_source}.labels.jsonl'})
            if len(chosen)==10:break
        if len(chosen)<10:raise RuntimeError(f'{family}: insufficient independent eligible tasks ({len(chosen)})')
        selected+=chosen
        selection_logs.append({'family':family,'eligible_question_only':len(eligible),'selected':len(chosen),'pool':source})
    write_json(OUT/'data/clusters.json',clusters)
    write_json(OUT/'data/dev_tasks.json',selected)
    write_json(OUT/'evidence/feature_cache.json',cache)
    write_json(OUT/'evidence/task_selection.json',selection_logs)
    csv_write(OUT/'data/source_self_match.csv',all_source_rows)
    copied=OUT/'data/labels_for_dev.jsonl'
    # Only label paths and byte hashes are recorded here; no label parsing.
    manifest={'run_id':RUN_ID,'dev_count':len(selected),'dev_task_ids':[r['problem']['task_id'] for r in selected],
              'problems_hash':digest([r['problem'] for r in selected]),'dev_selection':'question-only, unused dev then unused train, seed20261010, no outcome-based selection',
              'labels_sources':{p:sha(ROOT/p) for p in sorted({r['labels_path'] for r in selected})},
              'test_reference':{'path':'experiments/math500_goldfree_20261009/manifests/test.problems.jsonl',
                 'sha256':sha(OLD/'manifests/test.problems.jsonl'),'count':500,'claim':'existing benchmark confirmation/regression, not pristine holdout'},
              'sources':{f:[t['problem']['task_id'] for t in c['source_traces']] for f,c in clusters.items()},
              'independence':'ID + digit-masked exact + blocked near-duplicate; not a proof of semantic independence'}
    write_json(OUT/'dataset_manifest.json',manifest)
    protocol={'run_id':RUN_ID,'timestamp':datetime.now(timezone(timedelta(hours=8))).isoformat(),'model':'deepseek-flash',
      'endpoint':'https://api.deepseek.com/chat/completions','temperature':0.,'max_tokens':4096,'thinking':'omitted, provider default enabled/high; temperature may be ignored',
      'global_api_workers':64,'local_workers':12,'max_logical_calls':64,'max_token_reservation':400000,
      'distillation_calls':{'initial':2,'repair_max':2,'max_tokens':16384},'dev_calls':60,
      'estimated_upper_usd':.48,'price_source':'https://api-docs.deepseek.com/quick_start/pricing','price_usd_per_million_peak':{'input_cache_miss':.3,'output':1.2},
      'seed':20261010,'methods':['A_NoBank','B_OriginalContent','C_RevisedContent'],
      'control_B':'original compact content with COMMON repaired question-only trigger; isolates content, not a rerun of broken legacy trigger',
      'shadow_policy':'bypass production cost router only in independent dev; conditional solver guards, no claim of machine-proved guard compliance',
      'thresholds':THRESHOLDS,'admission_cost_scope':'current candidate source calls + candidate distillation/repair + all three dev groups; full historical pipeline accounted separately at bank level',
      'noninferiority_margin':.01,'gold_feedback':False,'math_retries':0,'format_retries':0,
      'formal_gate':'at least one independently admitted active macro with interpretable positive evidence and a usable unchanged production route',
      'formal_budget_if_gate_passes':{'logical_calls':1500,'token_reservation':7000000,'peak_usd_upper':8.4},
      'code_hashes':source_code_hashes(),'dataset_manifest_hash':digest(manifest),'repository':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot'}
    write_json(OUT/'protocol.json',protocol)
    print(json.dumps({'clusters':{f:len(c['source_traces']) for f,c in clusters.items()},'selected':len(selected),'selection':selection_logs}),flush=True)

def get_client():
    key=(ROOT.parent/'miyao.txt').read_text().strip()
    return Client(OUT/'calls',key,Budget())

def distill():
    if (OUT/'evidence/solver_frozen_before_dev.json').exists():
        raise ValueError('This bank was frozen before validation; distillation cannot change it. Use a new experiment directory.')
    clusters=read_json(OUT/'data/clusters.json');client=get_client();skills=[];errors=[]
    for family,c in clusters.items():
        prompt=distill_prompt(family,c['source_traces'],c['evidence']);cost=0
        for attempt in range(2):
            response=client.complete(prompt,job_id=f'distill_{family}_{attempt}',purpose='distillation' if attempt==0 else 'skill_revision',max_tokens=16384)
            cost+=response['total_tokens']
            choice=response['response']['choices'][0]
            try:
                if choice.get('finish_reason')=='length':raise ValueError('distillation truncated')
                # Include every recorded attempt for this family, even when an
                # older response passes a corrected local schema on resume.
                cost=sum(r['total_tokens'] for p in (OUT/'calls').glob('*.json')
                         if 'response' in (r:=read_json(p)) and r['job_id'].startswith('distill_'+family+'_'))
                skill=build_skill(family,c['predecessor'],choice['message'].get('content') or '',c['source_traces'],c['evidence'],cost)
                skills.append(skill.model_dump(mode='json',by_alias=True));break
            except (ValueError,KeyError,TypeError) as exc:
                errors.append({'family':family,'attempt':attempt,'error':str(exc)[:500],'call_id':response['call_id']})
                write_json(OUT/'evidence/distillation_errors.json',errors)
                # A single structural-format repair, no dev/gold feedback.
                prompt=distill_prompt(family,c['source_traces'],c['evidence'])+'\nPrevious draft failed local schema/guard check: '+str(exc)[:300]+'. Revise once. JSON only.'
        else:raise RuntimeError(f'{family}: bounded distillation repairs exhausted; preserve failed calls')
    write_json(OUT/'data/skills_v2_full.json',skills)
    write_json(OUT/'evidence/bank_before_dev.json',{'skills':skills,'bank_hash':digest(skills),'code_hashes':source_code_hashes()})
    print(json.dumps({'skills':[{'id':s['skill_id'],'short_prompt':s['compact_prompt']} for s in skills]}),flush=True)

def solver_prompt(task,skill_text=None):
    # NoBank and V2 fallback have exactly the same base/system/output instruction.
    return (('Relevant strategy (use only after verifying its conditions; otherwise solve normally):\n'+skill_text+'\n\n') if skill_text else '')+base_prompt(task)

def solve_dev():
    protocol=read_json(OUT/'protocol.json');entries=read_json(OUT/'data/dev_tasks.json')
    skills={s['predecessor']:MacroSkill.model_validate(s) for s in read_json(OUT/'data/skills_v2_full.json')}
    old={s['skill_id']:s for s in read_json(OLD/'real_bank.json')['skills']}
    family_skills={s.skill_id.split('_')[0]:s for s in skills.values()}
    bank_hash=digest([s.model_dump(mode='json',by_alias=True) for s in skills.values()]);config_hash=digest(protocol)
    before={'run_id':RUN_ID,'bank_hash':bank_hash,'config_hash':config_hash,'code_hashes':source_code_hashes(),
            'task_manifest_hash':digest(read_json(OUT/'dataset_manifest.json')),'labels_opened':False}
    freeze_path=OUT/'evidence/solver_frozen_before_dev.json'
    if freeze_path.exists() and read_json(freeze_path)!=before:raise ValueError('Resume code/config/bank changed')
    write_json(freeze_path,before)
    client=get_client()
    # Account existing distillation reservations before launching the shared pool.
    for path in sorted((OUT/'calls').glob('*.json')):
        r=read_json(path)
        if r.get('purpose') in ('distillation','skill_revision') and 'response' in r:client.budget.reserve(r['request'])
    jobs=[(e,m) for e in entries for m in protocol['methods']];random.Random(protocol['seed']).shuffle(jobs)
    order={(e['problem']['task_id'],m):i for i,(e,m) in enumerate(jobs)}
    def worker(entry,method):
        task=ProblemView.model_validate(entry['problem']);skill=family_skills[entry['family']]
        match=evaluate(skill.trigger,entry['features']['facts']);inject=method!='A_NoBank' and match['value'] is True
        text=old[skill.predecessor]['compact_prompt'] if method=='B_OriginalContent' else skill.compact_prompt
        prompt=solver_prompt(task,text if inject else None)
        job_id=method+'__'+task.task_id;dest=OUT/'submissions'/(job_id+'.json')
        if dest.exists():
            row=read_json(dest);assert_sealed(row)
            if row['config_hash']!=config_hash or row['bank_hash']!=bank_hash:raise ValueError('Resume identity mismatch')
            # Count its request reservation through the same cached transport path.
            client.complete(prompt,job_id=job_id,purpose='shadow_validation')
            return row
        response=client.complete(prompt,job_id=job_id,purpose='shadow_validation')
        choice=response['response']['choices'][0]
        row={'run_id':RUN_ID,'task_id':task.task_id,'subject':task.subject,'level':task.level,'original_category':task.public_metadata.get('type'),
             'method':method,'task_order':order[(task.task_id,method)],'model':response['model'],
             'prompt_hash':response['prompt_hash'],'config_hash':config_hash,'bank_hash':bank_hash,
             'route':'shadow_strategy' if inject else 'base','retrieved_skill_ids':[skill.skill_id] if method!='A_NoBank' else [],
             'selected_skill_id':(skill.predecessor if method=='B_OriginalContent' else skill.skill_id) if inject else None,
             'family':entry['family'],'skill_status':'shadow' if inject else None,'trigger_result':match if method!='A_NoBank' else None,
             'guard_result':guarded_obligations(skill,entry['features']) if inject else [],
             'guard_enforcement':('original compact content; V2 obligations listed for audit only, not injected' if method=='B_OriginalContent'
                                  else 'conditional natural-language solver instructions; not machine proof') if inject else 'not_applicable',
             'router_decision_reason':'independent shadow validation bypasses cost gate' if inject else 'base/no reliable match',
             'skill_injected':inject,'skill_prompt_tokens':estimate_tokens(text) if inject else 0,'skill_prompt_tokens_method':'UTF8 bytes/3 estimate; provider input total is actual',
             **{k:response[k] for k in ['input_tokens','output_tokens','total_tokens','reasoning_tokens','latency']},
             'llm_call_count':1,'infrastructure_attempts':len(response['attempts']),'call_id':response['call_id'],
             'solution':choice['message'].get('content') or '','truncated':choice.get('finish_reason')=='length',
             'gold_exposed':False,'error_type':None,'math_retries':0}
        row=seal(row);write_json(dest,row);return row
    rows=[];errors=[]
    with cf.ThreadPoolExecutor(max_workers=64) as pool:
        futures={pool.submit(worker,e,m):(e['problem']['task_id'],m) for e,m in jobs}
        for future in cf.as_completed(futures):
            try:rows.append(future.result())
            except Exception as exc:errors.append({'job':futures[future],'error':str(exc)[:350]})
            print(json.dumps({'completed':len(rows),'errors':len(errors),'expected':len(jobs)}),flush=True)
    if errors:
        write_json(OUT/'evidence/dev_infrastructure_errors.json',errors)
        raise RuntimeError('Incomplete submissions; scoring disabled; resume only after journal reconciliation')
    for r in rows:assert_sealed(r)
    write_json(OUT/'evidence/all_dev_submissions_sealed.json',{'count':len(rows),'seals':sorted(r['seal'] for r in rows),'labels_opened':False})
    # First semantic access to new development labels: all three groups are sealed.
    manifest=read_json(OUT/'dataset_manifest.json');selected_ids={e['problem']['task_id'] for e in entries};labels=[]
    for path,expected in manifest['labels_sources'].items():
        if sha(ROOT/path)!=expected:raise ValueError('Source labels changed')
        labels += [r for r in jsonl(ROOT/path) if r['task_id'] in selected_ids]
    if len(labels)!=len(entries):raise ValueError('Missing or duplicated selected labels')
    path=OUT/'data/labels_for_dev.jsonl';dump_lines(path,labels)
    rows.sort(key=lambda r:r['task_order'])
    scores=score_sealed(rows,path,{e['problem']['task_id']:e['problem']['problem'] for e in entries},sha(path),workers=12)
    results=[{**r,**score,'correct':score['rechecked_correct']} for r,score in zip(rows,scores)]
    dump_lines(OUT/'task_results.jsonl',results)
    finalize()

def finalize():
    rows=jsonl(OUT/'task_results.jsonl');skills=[MacroSkill.model_validate(s) for s in read_json(OUT/'data/skills_v2_full.json')]
    clusters=read_json(OUT/'data/clusters.json');entries=read_json(OUT/'data/dev_tasks.json')
    tasks={e['problem']['task_id']:e for e in entries};calls=[]
    for path in sorted((OUT/'calls').glob('*.json')):
        r=read_json(path)
        if 'response' in r:calls.append(r)
    dump_lines(OUT/'api_calls.jsonl',[{k:v for k,v in c.items() if k not in ('request','response')} for c in calls])
    pairs=[]
    for tid in tasks:
        methods={r['method']:r for r in rows if r['task_id']==tid};a=methods['A_NoBank']
        for method in ['B_OriginalContent','C_RevisedContent']:
            b=methods[method];pairs.append({'run_id':RUN_ID,'task_id':tid,'family':tasks[tid]['family'],'comparison':method,
                'base_correct':a['correct'],'skill_correct':b['correct'],'base_tokens':a['total_tokens'],'skill_tokens':b['total_tokens'],
                'input_saving':a['input_tokens']-b['input_tokens'],'output_saving':a['output_tokens']-b['output_tokens'],
                'reasoning_saving':a['reasoning_tokens']-b['reasoning_tokens'] if a['reasoning_tokens'] is not None and b['reasoning_tokens'] is not None else None,
                'total_saving':a['total_tokens']-b['total_tokens'],'base_truncated':a['truncated'],'skill_truncated':b['truncated'],
                'skill_injected':b['skill_injected'],'base_seal':a['seal'],'skill_seal':b['seal'],
                'problem_tokens':estimate_tokens(tasks[tid]['problem']['problem']),
                'structurally_distinct':all(normalize_problem(tasks[tid]['problem']['problem'],True)!=normalize_problem(t['problem']['problem'],True) for t in clusters[tasks[tid]['family']]['source_traces']),
                'structural_evidence_limit':'digit-masked nonduplicate, not proof of mathematical novelty'})
    csv_write(OUT/'task_pairwise.csv',pairs)
    write_json(OUT/'data/task_pairwise.json',pairs)
    decisions=[];admitted=[];validation=[]
    historic_build=sum(c['total_tokens'] for c in read_json(OLD/'real_bank.json')['cost_calls'])
    for s in skills:
        family=s.skill_id.split('_')[0];evidence=[r for r in pairs if r['family']==family and r['comparison']=='C_RevisedContent']
        validation_cost=sum(r['total_tokens'] for r in rows if r['family']==family)
        # Same candidate-attributable cost gate as V1, including acquisition of
        # reused sources and every new control call. Full historic bank costs,
        # including unrelated failed candidates, are reported separately.
        source_cost=sum(call['total_tokens'] for t in clusters[family]['source_traces'] for call in t['calls'])
        cost=source_cost+validation_cost+s.token_history['distillation_and_revision']
        new,decision=decide(s,evidence,independent=True,build_cost=cost)
        decisions.append(decision);admitted.append(new.model_dump(mode='json',by_alias=True))
        validation.append({'family':family,'skill_id':s.skill_id,'status':new.status,'production_route':route_reason(new),
                           **{k:v for k,v in new.validation_stats.items() if k not in ('pairwise','evidence_hash')},'build_cost_full_allocated':cost})
    bank={'run_id':RUN_ID,'schema_version':'2.0','skills':admitted,'frozen':True,'test_feedback_used':False,
          'historical_bank_sha256':sha(OLD/'real_bank.json')}
    bank['bank_hash']=digest(bank);write_json(OUT/'skill_bank_v2.json',bank)
    dump_lines(OUT/'admission_decisions.jsonl',decisions);dump_lines(OUT/'data/admission_v2_decisions.jsonl',decisions)
    csv_write(OUT/'skill_validation.csv',validation);csv_write(OUT/'data/shadow_validation_summary.csv',validation)
    usable=[s['skill_id'] for s in admitted if route_reason(MacroSkill.model_validate(s)).startswith('strategy:')]
    active=[s['skill_id'] for s in admitted if s['status']=='active']
    gate={'active_skill_ids':active,'usable_production_skill_ids':usable,'passed':bool(usable),
          'reason':'No independently admitted, usable skill under unchanged admission and router thresholds' if not usable else 'qualified',
          'formal_500_executed':False,'thresholds_unchanged':True}
    write_json(OUT/'evidence/formal_gate.json',gate)
    write_json(OUT/'run_manifest.json',{'run_id':RUN_ID,'status':'shadow_complete_formal_gate_failed' if not usable else 'formal_gate_passed',
       'protocol_hash':digest(read_json(OUT/'protocol.json')),'dataset_manifest_hash':digest(read_json(OUT/'dataset_manifest.json')),
       'solver_freeze':read_json(OUT/'evidence/solver_frozen_before_dev.json'),'bank_hash':bank['bank_hash'],
       'api_calls':len(calls),'tokens':sum(c['total_tokens'] for c in calls),'real_calls':True,'formal_gate':gate,
       'repository':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot'})
    print(json.dumps({'gate':gate,'validation':validation}),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','distill','dev','finalize']);parser.add_argument('--allow-paid-api',action='store_true');args=parser.parse_args()
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    if args.stage in ('distill','dev') and not args.allow_paid_api:parser.error('Paid calls require --allow-paid-api')
    {'prepare':prepare,'distill':distill,'dev':solve_dev,'finalize':finalize}[args.stage]()

if __name__=='__main__':main()
