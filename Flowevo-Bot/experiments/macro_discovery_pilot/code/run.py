"""Frozen 3-arm pilot. No scoring until all submissions have been sealed."""
import sys,argparse,time,random,zipfile
from concurrent.futures import ThreadPoolExecutor,as_completed,ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.rmmd.client import Client,Budget,SYSTEM
from flowevo_bot.rmmd.macros import inspect_question,COMPACT,trigger_logic
from flowevo_bot.schemas import ProblemView
from code_math.baseline import base_prompt
from flowevo_bot.common import digest,write_json
from flowevo_bot.v2.evaluator import seal,assert_sealed,grade
RUN_ID='rmmd_pilot_20261010'

def freeze():
    if (OUT/'evidence/prepaid_freeze.json').exists():raise RuntimeError('already_frozen')
    tasks=read(OUT/'data/dev_tasks.json');bank=read(OUT/'data/macro_skill_bank.json')
    assert tasks and len(tasks)<=36
    assert all(b['compact_estimated_tokens']<=100 for b in bank)
    assert '0 failures' in (OUT/'tests/prepaid.xml').read_text() or 'failures="0"' in (OUT/'tests/prepaid.xml').read_text()
    files=list((ROOT/'src/flowevo_bot/rmmd').glob('*.py'))+list((OUT/'code').glob('*.py'))+list((OUT/'tests').glob('*.py'))
    files +=[OUT/'data'/name for name in ['dev_tasks.json','macro_skill_bank.json','clean_success_traces.jsonl','selection_manifest.json','reasoning_operations.jsonl']]
    files +=[ROOT/'src/code_math/baseline.py',ROOT/'src/flowevo_bot/v2/evaluator.py',ROOT/'src/flowevo_bot/schemas.py',ROOT/'src/flowevo_bot/common.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    direct=sum(t['execution']['full_task_verified'] for t in tasks)
    plan={'run_id':RUN_ID,'model':'deepseek-flash','system':SYSTEM,'temperature':0.0,'max_tokens':4096,'api_workers':16,'cpu_workers':12,'max_calls':120,'max_total_tokens':200000,'planned_tasks':len(tasks),'planned_submissions':3*len(tasks),'planned_calls':3*len(tasks)-direct,'expected_direct_submissions':direct,'estimated_tokens_at_historical_700_mean':round((3*len(tasks)-direct)*795435/700),'budget_method':'provider actual usage + inflight UTF8 byte upper input bound +512 framing +4096 output; stop before exceeding; no retries','max_calls_without_retries':3*len(tasks)-direct,'group_prompts':'A identical native base; B base + compact; C base + verified intermediate, or exact certified direct answer; no arm receives brevity instruction','allocation':'all tasks all3 methods, seeded job shuffle20261010; inference stochastic even at temp0','labels_read_only_after_all_sealed':True,'root_macro_scope':'local intermediate only; no direct root answer','decision':'single pilot then stop; no MATH500 or outcome-driven revisions'}
    write(OUT/'evidence/budget_plan.json',plan)
    hashes[str((OUT/'evidence/budget_plan.json').relative_to(ROOT))]=sha(OUT/'evidence/budget_plan.json')
    labels={str(ROOT/'data/manifests/math_grouped'/name):sha(ROOT/'data/manifests/math_grouped'/name) for name in ['train.labels.jsonl','dev.labels.jsonl']}
    record={'files':hashes,'code_hash':digest(hashes),'label_files_hashes_only':labels,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'prepaid_test_report_sha256':sha(OUT/'tests/prepaid.xml')}
    write(OUT/'evidence/prepaid_freeze.json',record)
    with zipfile.ZipFile(OUT/'snapshots/runtime_before_paid.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in hashes:z.write(ROOT/name,name)
    print(plan,flush=True)

def run_paid():
    cap_cpu();frozen=read(OUT/'evidence/prepaid_freeze.json')
    assert all(sha(ROOT/p)==h for p,h in frozen['files'].items()),'frozen_code_changed'
    tasks=read(OUT/'data/dev_tasks.json');budget=Budget();key=(ROOT.parent/'miyao.txt').read_text().strip()
    client=Client(OUT/'api_calls',key,budget);jobs=[]
    for task in tasks:
        problem=ProblemView.model_validate(task['problem']);mid=task['macro_id'];execution=inspect_question(problem.problem,mid)
        assert execution['execution_verified'] and execution['output_structure']==task['execution']['output_structure']
        assert trigger_logic({'all_of':[{'feature':'trigger'},{'guard':'verified'}]},{'trigger':execution['trigger_match'],'verified':execution['guard_pass'] and execution['execution_verified']})
        for method in ['A_NoBank','B_Compact','C_Executable']:jobs.append((problem,mid,execution,method))
    random.Random(20261010).shuffle(jobs)
    def solve(job):
        problem,mid,execution,method=job;jobid=method+'__'+problem.task_id
        path=OUT/'submissions'/(jobid+'.json');prompt=base_prompt(problem)
        if method=='B_Compact':prompt+='\n\nReusable mathematical method:\n'+COMPACT[mid]
        if method=='C_Executable' and not execution['full_task_verified']:prompt+='\n\nVerified mathematical intermediate:\n'+execution['verified_context']
        if method=='C_Executable' and execution['full_task_verified']:
            solution='The answer is \\boxed{'+execution['direct_answer']+'}.';call=None;truncated=False;count=0;input_tokens=output_tokens=total_tokens=0;latency=execution['local_total_seconds'];prompt_hash=None
        else:
            call=client.complete(prompt,jobid,frozen['code_hash']);choice=call['response']['choices'][0];solution=choice['message'].get('content') or '';truncated=choice.get('finish_reason')=='length'
            count=1;input_tokens=call['input_tokens'];output_tokens=call['output_tokens'];total_tokens=call['total_tokens'];latency=call['latency'];prompt_hash=call['prompt_hash']
        result={'run_id':RUN_ID,'task_id':problem.task_id,'subject':problem.subject,'difficulty':problem.level,'method':method,'macro_id':mid,'macro_type':{'A_NoBank':'none','B_Compact':'compact_thought','C_Executable':'executable_macro'}[method],
          'trigger_match':execution['trigger_match'] if method!='A_NoBank' else False,'guard_pass':execution['guard_pass'] if method!='A_NoBank' else False,'execution_attempted':method=='C_Executable','execution_verified':method=='C_Executable' and execution['execution_verified'],'full_task_verified':method=='C_Executable' and execution['full_task_verified'],'fallback_reason':None,'scope':execution['scope'] if method=='C_Executable' else None,
          'prompt_hash':prompt_hash,'input_tokens':input_tokens,'output_tokens':output_tokens,'total_tokens':total_tokens,'api_call_count':count,'latency':latency,'solution':solution,'truncated':truncated,'gold_exposed':False,'code_hash':frozen['code_hash'],'call_id':call['call_id'] if call else None,'execution_seconds':execution.get('execution_seconds',0) if method=='C_Executable' else 0,'verification_seconds':execution.get('verification_seconds',0) if method=='C_Executable' else 0,'local_total_seconds':execution.get('local_total_seconds',0) if method=='C_Executable' else 0,'execution_certificate':execution.get('certificate') if method=='C_Executable' else None}
        if path.exists():
            previous=read(path);assert_sealed(previous)
            for k in ['solution','code_hash','prompt_hash','total_tokens']:assert previous[k]==result[k]
            return previous
        record=seal(result);write_json(path,record);print('completed',jobid,'tokens',total_tokens,flush=True);return record
    with ThreadPoolExecutor(max_workers=16) as ex:results=[f.result() for f in as_completed([ex.submit(solve,j) for j in jobs])]
    for r in results:assert_sealed(r)
    write(OUT/'evidence/submission_barrier.json',{'all_sealed':True,'count':len(results),'expected':len(jobs),'seal_hashes':{r['method']+'__'+r['task_id']:r['seal'] for r in results},'before_label_open':True,'total_tokens':budget.actual,'calls':budget.calls})
    # Private labels first enter this offline-only block after every submission.
    labels={}
    for p,h in frozen['label_files_hashes_only'].items():
        assert sha(p)==h
        labels.update({r['task_id']:r for r in lines(p)})
    qmap={t['problem']['task_id']:t['problem']['problem'] for t in tasks}
    items=[{**r,'gold_answer':labels[r['task_id']]['gold_answer'],'question':qmap[r['task_id']]} for r in results]
    with ProcessPoolExecutor(max_workers=12) as ex:scores=list(ex.map(grade,items))
    merged=[]
    for r,g in zip(results,scores):merged.append({**r,'answer':g['answer'],'offline_correct':g['rechecked_correct'],'parse_status':g['parse_status'],'grading_error_type':g['error_type']})
    write_lines(OUT/'data/task_results.jsonl',sorted(merged,key=lambda r:(r['macro_id'],r['task_id'],r['method'])))
    write(OUT/'evidence/budget_final.json',{'api_calls':budget.calls,'actual_total_tokens':budget.actual,'remaining_inflight_tokens':budget.reserved,'max_calls':120,'max_total_tokens':200000,'new_macro_build_llm_calls':0,'gold_reflection_calls':0,'correctness_retries':0,'infrastructure_retries':0,'new_sampling_rounds':1})
    print('COMPLETE',budget.calls,budget.actual,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run']);parser.add_argument('--allow-paid-api',action='store_true');args=parser.parse_args()
    if args.stage=='freeze':freeze()
    else:
        if not args.allow_paid_api:raise SystemExit('explicit --allow-paid-api required')
        run_paid()
