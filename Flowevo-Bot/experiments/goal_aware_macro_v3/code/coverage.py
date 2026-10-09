"""Development coverage and a separately frozen, previously uninspected pool.

No label is read by routing/execution. All deterministic submissions are sealed
before optional offline scoring; no LLM fallback is run in coverage mode.
"""
import sys,time,signal,argparse,collections
from concurrent.futures import ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.goal_v3.engine import solve
from flowevo_bot.common import digest
from flowevo_bot.v2.evaluator import seal,assert_sealed,grade

def prepare_split():
    old=ROOT/'experiments/math500_goldfree_20261009';v2=ROOT/'experiments/flowevo_bot_v2_math500'
    previous_ids={r['task_id'] for r in lines(old/'manifests/dev.problems.jsonl')}
    previous_ids|={r['problem']['task_id'] for r in read(v2/'data/dev_tasks.json')}
    previous_ids|={r['problem']['task_id'] for r in read(PREVIOUS/'data/dev_tasks.json')}
    screened_ids={r['task_id'] for r in lines(PREVIOUS/'data/coverage_screen.jsonl')}
    original=lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')
    engineering=[r for r in original if r['task_id'] in previous_ids|screened_ids]
    fresh=[r for r in original if r['task_id'] not in previous_ids|screened_ids]
    write(OUT/'data/engineering_dev_tasks.json',engineering)
    write(OUT/'data/reserved_dev_tasks.json',fresh)
    record={'original_dev_count':len(original),'engineering_dev_count':len(engineering),'reserved_dev_count':len(fresh),'engineering_ids':sorted(r['task_id'] for r in engineering),'reserved_ids':sorted(r['task_id'] for r in fresh),'previous_screened_across_pools':len(screened_ids),'prior_used_ids_across_pools':len(previous_ids),'engineering_file_hash':sha(OUT/'data/engineering_dev_tasks.json'),'reserved_file_hash':sha(OUT/'data/reserved_dev_tasks.json'),'policy':'Original dev only; previously used or prior goal-family predicate-screened questions are engineering; reserved pool is never used to revise this-round parser or programs.'}
    write(OUT/'data/split_manifest.json',record);print({k:v for k,v in record.items() if not k.endswith('_ids')},flush=True)

def timeout(*args):raise TimeoutError('local_10_second_budget')
def worker(job):
    row,method,bank,split=job;signal.signal(signal.SIGALRM,timeout);start=time.perf_counter();signal.alarm(10)
    try:r=solve(row['problem'],method,bank)
    except Exception as exc:r={'full_task_verified':False,'partial_result':False,'execution_attempted':False,'goal':{},'guard_pass':False,'guard_checks':[],'fallback_reason':str(exc),'answer':None,'selected_macro':None,'local_seconds':time.perf_counter()-start,'execution_seconds':0.,'verification_seconds':0.,'retrieval_seconds':0.}
    finally:signal.alarm(0)
    return {'task_id':row['task_id'],'subject':row['subject'],'difficulty':row['level'],'source_split':split,'question':row['problem'],'method':'B_Manual' if method=='manual' else 'C_Automatic','record_type':'offline_deterministic_coverage','solver_result':r,'solution':'The answer is \\boxed{'+r['answer']+'}.' if r['full_task_verified'] else '', 'truncated':False,'gold_exposed':False,'input_tokens':0,'output_tokens':0,'total_tokens':0,'api_call_count':0,'online_fallback_executed':False}

def run(split,methods):
    cap_cpu();start=time.perf_counter();tasks=read(OUT/'data'/('engineering_dev_tasks.json' if split=='engineering' else 'reserved_dev_tasks.json'))
    if split=='reserved':
        freeze=read(OUT/'evidence/pre_reserved_freeze.json');assert all(sha(ROOT/p)==h for p,h in freeze['files'].items()),'frozen_source_changed'
    bank=read(OUT/'data/automatic_macro_bank.json') if 'automatic' in methods else []
    jobs=[(r,m,bank,split) for r in tasks for m in methods]
    with ProcessPoolExecutor(max_workers=12) as pool:records=list(pool.map(worker,jobs,chunksize=4))
    label=split+'_'+('_'.join(methods));sealed=[seal(r) for r in records]
    write_lines(OUT/'data'/(label+'_sealed.jsonl'),sealed)
    write(OUT/'evidence'/(label+'_submission_barrier.json'),{'all_sealed':True,'count':len(sealed),'before_label_read':True,'submission_file_hash':sha(OUT/'data'/(label+'_sealed.jsonl'))})
    for r in sealed:assert_sealed(r)
    code_version=digest({p.name:sha(p) for p in (ROOT/'src/flowevo_bot/goal_v3').glob('*.py')})
    config_hash=sha(OUT/'configs/protocol.json')
    done=[r for r in sealed if r['solver_result']['full_task_verified']]
    scored=[]
    if split=='engineering':
        ids={item['task_id'] for item in sealed};labels={r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/dev.labels.jsonl') if r['task_id'] in ids}
        with ProcessPoolExecutor(max_workers=12) as pool:scored=list(pool.map(grade,[{**r,'gold_answer':labels[r['task_id']]['gold_answer']} for r in done]))
    scores={(r['task_id'],r['method']):score for r,score in zip(done,scored)}
    for r in records:
        score=scores.get((r['task_id'],r['method']));r['offline_correct']=score['rechecked_correct'] if score else None;r['parse_status']=score['parse_status'] if score else 'not_submitted_fallback_not_executed';r['code_version']=code_version;r['config_hash']=config_hash
    write_lines(OUT/'data'/(label+'_results.jsonl'),records)
    summary=[]
    for method in sorted({r['method'] for r in records}):
        group=[r for r in records if r['method']==method];n=len(group)
        for family in ['ALL','root_symmetric','polynomial_remainder']:
            g=group if family=='ALL' else [r for r in group if r['solver_result'].get('goal',{}).get('family')==family]
            full=sum(r['solver_result']['full_task_verified'] for r in g);partial=sum(r['solver_result']['partial_result'] for r in g)
            summary.append({'split':split,'method':method,'family':family,'pool_denominator':n,'family_candidates':len(g),'parsed_goals':sum(r['solver_result'].get('goal',{}).get('state')=='parsed' for r in g),'guard_pass':sum(r['solver_result']['guard_pass'] for r in g),'full_solved':full,'partial_available_not_injected':partial,'other_fallback':len(g)-full-partial,'total_needing_llm':len(g)-full,'full_coverage':full/n,'correct_among_full':sum(r['offline_correct'] is True for r in g) if split=='engineering' else None,'false_or_unknown_full':sum(r['solver_result']['full_task_verified'] and r['offline_correct'] is not True for r in g) if split=='engineering' else None,'new_api_calls':0})
    write(OUT/'data'/(label+'_coverage.json'),summary)
    write(OUT/'evidence'/(label+'_runtime.json'),{'seconds':time.perf_counter()-start,'workers':12,'api_calls':0});print(summary,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','engineering','reserved']);parser.add_argument('--methods',nargs='+',choices=['manual','automatic'],default=['manual','automatic']);args=parser.parse_args()
    if args.stage=='prepare':prepare_split()
    else:run(args.stage,args.methods)
