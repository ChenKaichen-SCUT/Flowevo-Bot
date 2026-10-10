"""12-process sealed offline evaluation. Gold is loaded only after all submissions.

Confirmation cannot run until freeze.json exists and every frozen hash matches.
No API import, credential access, retry or generated-code execution occurs here.
"""
import sys,signal,time,resource,argparse,collections
from concurrent.futures import ProcessPoolExecutor
from common import *
sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.compositional_v4.runtime import solve
from flowevo_bot.v2.evaluator import seal,assert_sealed,grade

def deadline(*_):raise TimeoutError('worker_3_second_limit')
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
    signal.signal(signal.SIGALRM,deadline)
def worker(job):
    row,method,bank,legacy,split=job;signal.setitimer(signal.ITIMER_REAL,3);start=time.perf_counter()
    try:r=solve(row['problem'],method,bank,legacy)
    except (Exception,MemoryError) as exc:r={'method':method,'module':'unknown','full_execution':False,'parsed_goal':False,
        'guard_pass':False,'answer':None,'fallback_reason':'worker_'+type(exc).__name__+':'+str(exc),
        'selected_macro':None,'local_seconds':time.perf_counter()-start,'execution_seconds':0.,'verification_seconds':0.,'retrieval_seconds':0.}
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    return {'task_id':row['task_id'],'split':split,'method':method,'subject':row['subject'],'level':row['level'],
        'question':row['problem'],'result':r,'solution':('The answer is \\boxed{'+r['answer']+'}.') if r['full_execution'] else '',
        'truncated':False,'gold_exposed':False,'record_type':'offline_deterministic','LLM_fallback_executed':False,
        'api_call_count':0,'input_tokens':None,'output_tokens':None,'total_tokens':None}

def verify_freeze():
    f=read(OUT/'evidence/freeze.json')
    for path,h in f['files'].items():assert sha(ROOT/path)==h,('frozen_file_changed',path)
    return f

def run(split):
    cap_cpu();start=time.perf_counter()
    if split=='heldout-confirmation':verify_freeze()
    path=OUT/f'snapshots/{split}.problems.jsonl';tasks=lines(path)
    assert sha(path)==read(OUT/'dataset_split_manifest.json')['public_split_hashes'][split]
    bank=read(OUT/'automatic_macro_bank.json');legacy=read(V3/'data/automatic_macro_bank.json')
    jobs=[(r,method,bank,legacy,split) for r in tasks for method in (('B','C') if int(digest(r['task_id'])[:8],16)%2 else ('C','B'))]
    with ProcessPoolExecutor(max_workers=12,initializer=limits) as pool:records=list(pool.map(worker,jobs,chunksize=4))
    records=[seal(r) for r in records]
    write_lines(OUT/f'evidence/{split}.sealed.jsonl',records)
    write(OUT/f'evidence/{split}.barrier.json',{'at':now(),'all_sealed_before_labels':True,'count':len(records),
        'sha256':sha(OUT/f'evidence/{split}.sealed.jsonl'),'code_hash':digest({p.name:sha(p) for p in (ROOT/'src/flowevo_bot/compositional_v4').glob('*.py')})})
    for r in records:assert_sealed(r)
    labels={r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/train.labels.jsonl')}
    labels.update({r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/dev.labels.jsonl')})
    done=[r for r in records if r['result']['full_execution']]
    with ProcessPoolExecutor(max_workers=12) as pool:scores=list(pool.map(grade,[{**r,'gold_answer':labels[r['task_id']]['gold_answer']} for r in done]))
    scoremap={(r['task_id'],r['method']):s for r,s in zip(done,scores)}
    for r in records:
        score=scoremap.get((r['task_id'],r['method']))
        r['offline_correct']=score['rechecked_correct'] if score else None
        r['grader_result']=score
    write_lines(OUT/f'evidence/{split}.scored.jsonl',records)
    summary=[]
    for method in ('B','C'):
        for module in ('ALL','v4_integer_congruence','frozen_v3'):
            rows=[r for r in records if r['method']==method and (module=='ALL' or r['result']['module']==module)]
            full=[r for r in rows if r['result']['full_execution']]
            summary.append({'split':split,'method':method,'module':module,'denominator':len(tasks),
                'parsed':sum(r['result']['parsed_goal'] for r in rows),'guards':sum(r['result']['guard_pass'] for r in rows),
                'full':len(full),'correct':sum(r['offline_correct'] is True for r in full),'incorrect_or_unknown':sum(r['offline_correct'] is not True for r in full),
                'fallback':len(rows)-len(full),'local_seconds':sum(r['result']['local_seconds'] for r in rows),
                'rejection_reasons':dict(collections.Counter(r['result']['fallback_reason'] for r in rows if not r['result']['full_execution']))})
    write(OUT/f'evidence/{split}.summary.json',summary)
    write(OUT/f'evidence/{split}.runtime.json',{'seconds':time.perf_counter()-start,'workers':12,'api_calls':0})
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('split',choices=['dev-engineering','dev-selection','heldout-confirmation']);run(p.parse_args().split)
