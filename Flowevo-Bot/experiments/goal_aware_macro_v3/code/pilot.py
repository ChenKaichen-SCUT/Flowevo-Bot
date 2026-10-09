"""Preregistered feasibility gate; no paid call unless all conditions pass."""
import sys,json,time,zipfile,random,argparse
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
from difflib import SequenceMatcher
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.common import digest
from flowevo_bot.v2.evaluator import seal,assert_sealed,grade
from flowevo_bot.schemas import ProblemView
from flowevo_bot.goal_v3.runtime import solve_task
from flowevo_bot.rmmd.client import Client,Budget
from flowevo_bot.features import normalize_problem

def freeze():
    assert not (OUT/'evidence/pre_reserved_freeze.json').exists()
    import xml.etree.ElementTree as ET
    xml=ET.parse(OUT/'tests/offline.xml');suites=list(xml.getroot().iter('testsuite'));assert suites and all(int(s.get('failures',0))==0 and int(s.get('errors',0))==0 for s in suites)
    assert (OUT/'data/engineering_automatic_results.jsonl').exists()
    files=list((ROOT/'src/flowevo_bot/goal_v3').glob('*.py'))+list((OUT/'code').glob('*.py'))+list((OUT/'tests').glob('*.py'))
    files +=[OUT/'configs/protocol.json',OUT/'data/automatic_macro_bank.json',OUT/'data/split_manifest.json',OUT/'data/engineering_dev_tasks.json',OUT/'data/reserved_dev_tasks.json',OUT/'tests/offline.xml',PREVIOUS/'data/clean_success_traces.jsonl',ROOT/'src/flowevo_bot/rmmd/client.py',ROOT/'src/flowevo_bot/rmmd/macros.py',ROOT/'src/code_math/baseline.py',ROOT/'src/flowevo_bot/v2/evaluator.py']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
    record={'files':hashes,'code_hash':digest(hashes),'configuration_hash':sha(OUT/'configs/protocol.json'),'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'dev_label_hash_only':sha(ROOT/'data/manifests/math_grouped/dev.labels.jsonl'),'fresh_pool_not_inspected_by_new_parser':True,'paid_calls':0}
    write(OUT/'evidence/pre_reserved_freeze.json',record)
    with zipfile.ZipFile(OUT/'snapshots/runtime_before_reserved.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT))
    print({'frozen_files':len(files),'code_hash':record['code_hash']},flush=True)

def near(a,b):
    a=normalize_problem(a,True);b=normalize_problem(b,True);m=SequenceMatcher(None,a,b,autojunk=False)
    return m.real_quick_ratio()>=.9 and m.quick_ratio()>=.9 and m.ratio()>=.9

def gate():
    frozen=read(OUT/'evidence/pre_reserved_freeze.json');assert all(sha(ROOT/p)==h for p,h in frozen['files'].items())
    cfg=read(OUT/'configs/protocol.json');rows=lines(OUT/'data/reserved_manual_automatic_results.jsonl');byid={}
    for r in rows:byid.setdefault(r['task_id'],{})[r['method']]=r
    prior=[r['problem'] for r in read(OUT/'data/engineering_dev_tasks.json')]+[r['problem'] for r in lines(PREVIOUS/'data/clean_success_traces.jsonl')]
    chosen=[];rejected=[];classes=set()
    for tid,pair in sorted(byid.items()):
        b,c=pair['B_Manual'],pair['C_Automatic'];q=b['question']
        if not b['solver_result']['full_task_verified']:continue
        if any(near(q,p) for p in prior) or any(near(q,r['problem']['problem']) for r in chosen):rejected.append({'task_id':tid,'reason':'near_duplicate_or_digit_template'});continue
        goal=b['solver_result']['goal'];structure=(goal['kind'],goal['known_objects']['polynomial']['degree'])
        classes.add(structure)
        chosen.append({'problem':next(t for t in read(OUT/'data/reserved_dev_tasks.json') if t['task_id']==tid),'automatic_full':c['solver_result']['full_task_verified'],'goal_kind':goal['kind'],'structure':list(structure)})
    minimum=cfg['paid_gate'];bank=read(OUT/'data/automatic_macro_bank.json')
    checks={'offline_tests_passed':True,'certified_automatic_macros':len(bank)>=minimum['minimum_certified_automatic_macros'],'fresh_eligible_tasks':len(chosen)>=minimum['minimum_fresh_eligible_dev_tasks'],'fresh_automatic_tasks':sum(t['automatic_full'] for t in chosen)>=minimum['minimum_fresh_automatic_macro_tasks'],'structural_diversity':len(classes)>=minimum['minimum_fresh_structural_classes']}
    accepted=all(checks.values());selected=chosen[:minimum['maximum_selected_eligible']]
    if accepted:
        controls=[]
        for tid,pair in sorted(byid.items()):
            if not pair['B_Manual']['solver_result']['full_task_verified']:
                controls.append({'problem':next(t for t in read(OUT/'data/reserved_dev_tasks.json') if t['task_id']==tid),'automatic_full':False,'goal_kind':'noneligible_control','structure':None})
            if len(controls)==minimum['maximum_noneligible_controls']:break
        selected+=controls
    record={'eligible':accepted,'checks':checks,'raw_fresh_B_full':sum(p['B_Manual']['solver_result']['full_task_verified'] for p in byid.values()),'raw_fresh_C_full':sum(p['C_Automatic']['solver_result']['full_task_verified'] for p in byid.values()),'independent_eligible_after_dedup':len(chosen),'independent_automatic_after_dedup':sum(t['automatic_full'] for t in chosen),'structural_classes':list(classes),'rejected':rejected,'selected_if_eligible':len(selected) if accepted else 0,'correctness_labels_used_for_gate':False,'paid_call_count_before_gate':0,'stop_reason':None if accepted else 'insufficient independent eligible development tasks under preregistered counts; no paid experiment','thresholds':minimum}
    write(OUT/'data/paid_gate.json',record);write(OUT/'data/pilot_tasks.json',selected if accepted else []);write(OUT/'data/fresh_eligible_candidates.json',chosen)
    if not accepted:
        write_lines(OUT/'data/api_calls.jsonl',[]);write(OUT/'evidence/paid_status.json',{'status':'NOT_RUN_GATE_FAILED','new_api_calls':0,'new_total_tokens':0,'new_math500':False,'reason':record['stop_reason']})
    print(record,flush=True)

def grade_reserved_after_gate():
    decision=read(OUT/'data/paid_gate.json')
    if decision['eligible']:assert (OUT/'evidence/paid_submission_barrier.json').exists(),'paid submissions not yet complete'
    rows=lines(OUT/'data/reserved_manual_automatic_sealed.jsonl')
    for r in rows:assert_sealed(r)
    freeze=read(OUT/'evidence/pre_reserved_freeze.json');assert sha(ROOT/'data/manifests/math_grouped/dev.labels.jsonl')==freeze['dev_label_hash_only']
    ids={r['task_id'] for r in rows};labels={r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/dev.labels.jsonl') if r['task_id'] in ids}
    full=[r for r in rows if r['solver_result']['full_task_verified']]
    with ProcessPoolExecutor(max_workers=12) as pool:scores=list(pool.map(grade,[{**r,'gold_answer':labels[r['task_id']]['gold_answer']} for r in full]))
    lookup={(r['task_id'],r['method']):g for r,g in zip(full,scores)}
    out=[]
    for r in rows:
        g=lookup.get((r['task_id'],r['method']));out.append({**r,'offline_correct':g['rechecked_correct'] if g else None,'parse_status':g['parse_status'] if g else 'not_submitted_fallback_not_executed','code_version':freeze['code_hash'],'config_hash':freeze['configuration_hash']})
    write_lines(OUT/'data/reserved_scored_results.jsonl',out);write(OUT/'evidence/reserved_label_barrier.json',{'paid_gate_closed_or_all_paid_submissions_sealed':True,'sealed_records':len(rows),'scored_direct_submissions':len(full),'code_unchanged':all(sha(ROOT/p)==h for p,h in freeze['files'].items()),'label_hash_matches':True})
    print({'reserved_direct_scored':len(full),'correct':sum(g['rechecked_correct'] is True for g in scores),'new_calls':0},flush=True)

def paid():
    cap_cpu();decision=read(OUT/'data/paid_gate.json');assert decision['eligible'],'paid gate rejected'
    freeze=read(OUT/'evidence/pre_reserved_freeze.json');assert all(sha(ROOT/p)==h for p,h in freeze['files'].items())
    cfg=read(OUT/'configs/protocol.json');bank=read(OUT/'data/automatic_macro_bank.json');tasks=read(OUT/'data/pilot_tasks.json')
    budget=Budget(cfg['max_new_api_calls'],cfg['max_new_total_tokens']);client=Client(OUT/'api_calls',(ROOT.parent/'miyao.txt').read_text().strip(),budget)
    jobs=[(t,m) for t in tasks for m in ['A_NoBank','B_Manual','C_Automatic']];random.Random(4401).shuffle(jobs)
    def job(j):
        task,method=j;r=solve_task(ProblemView.model_validate(task['problem']),method,bank,client,freeze['code_hash']);r['config_hash']=freeze['configuration_hash'];r['run_id']='goal_aware_macro_v3';r=seal(r);write(OUT/'submissions'/(method+'__'+r['task_id']+'.json'),r);print('completed',method,r['task_id'],r['total_tokens'],flush=True);return r
    with ThreadPoolExecutor(max_workers=cfg['api_workers_planned']) as pool:records=list(pool.map(job,jobs))
    for r in records:assert_sealed(r)
    write(OUT/'evidence/paid_submission_barrier.json',{'all_sealed':True,'count':len(records),'before_label_read':True})
    labels={r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/dev.labels.jsonl')};questions={t['problem']['task_id']:t['problem']['problem'] for t in tasks}
    with ProcessPoolExecutor(max_workers=12) as pool:scores=list(pool.map(grade,[{**r,'question':questions[r['task_id']],'gold_answer':labels[r['task_id']]['gold_answer']} for r in records]))
    write_lines(OUT/'data/paid_task_results.jsonl',[{**r,'answer':g['answer'],'offline_correct':g['rechecked_correct'],'parse_status':g['parse_status']} for r,g in zip(records,scores)])
    calls=[read(p) for p in (OUT/'api_calls').glob('*.json')];write_lines(OUT/'data/api_calls.jsonl',calls)
    write(OUT/'evidence/paid_status.json',{'status':'COMPLETE','new_api_calls':budget.calls,'new_total_tokens':budget.actual,'reserved_tokens':budget.reserved,'new_math500':False})

if __name__=='__main__':
    cap_cpu();parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','gate','grade-reserved','paid']);parser.add_argument('--allow-paid-api',action='store_true');args=parser.parse_args()
    if args.stage=='freeze':freeze()
    elif args.stage=='gate':gate()
    elif args.stage=='grade-reserved':grade_reserved_after_gate()
    elif not args.allow_paid_api:raise SystemExit('explicit flag required')
    else:paid()
