"""Actual staged controller with exact usage; no cancellation or gold access."""
from common import *
from states import observe,paragraphs,safe_boundary,features
from dataclasses import asdict
from transport import Ledger,base_request
from intervene import request_for
from grade_and_fit import decision
import concurrent.futures as cf,time

def run_task(public,ledger,pilot_config,counterfactual_config):
    tid=public['task_id'];target=OUT/'online'/(tid+'.json')
    if target.exists():return read(target)
    prompt='Problem: '+public['problem']+'\n\nSolve step by step. End with: The answer is [your answer].'
    messages=[dict(role='system',content='You are an expert programmer and mathematician.'),dict(role='user',content=prompt)]
    high=ledger.call(tid+'__online_B0',base_request(messages,16384),dict(stage='independent',task_id=tid,branch='B0'))
    first=ledger.call(tid+'__online_first',base_request(messages,1024),dict(stage='independent',task_id=tid,branch='shared_first'))
    assert high['status']==first['status']=='completed'
    message=first['response']['choices'][0]['message'];finish=first['response']['choices'][0]['finish_reason']
    start=time.process_time();trace=message.get('reasoning_content') or ''
    ends=[end for _,end,_ in paragraphs(trace) if safe_boundary(trace,end) and (end<len(trace) or trace.rstrip().endswith(('.','!','?')))]
    pos=max(ends) if ends else 0
    prefix=trace[:pos];state=dict(state_id=tid+'__online_state',task_id=tid,problem=public['problem'],prefix=prefix,prefix_sha256=digest(prefix),reasoning_state=asdict(observe(tid,public['problem'],prefix)))
    completed=finish=='stop' and bool(message.get('content','').strip())
    choices={method:('finished' if completed else decision(method,state,pilot_config['selected_rule'])) for method in pilot_config['methods'] if method!='B0_high'}
    cpu_ms=(time.process_time()-start)*1000
    continuations={}
    config=dict(counterfactual_config,max_tokens=pilot_config['continuation_max_tokens'])
    for branch in sorted(set(choices.values())-{'finished'}):
        req,endpoint=request_for(state,branch,config)
        continuations[branch]=ledger.call(tid+'__online_'+branch,req,dict(stage='independent',task_id=tid,branch=branch,first_stage_job=first['job_id']),endpoint)
        assert continuations[branch]['status']=='completed'
    def record(method,last,calls):
        return dict(task_id=tid,subject=public['subject'],level=public['level'],method=method,
            jobs=[c['job_id'] for c in calls],response_path='raw/'+last['job_id']+'.json',response_hash=last['response_hash'],
            final_text=last['response']['choices'][0]['message'].get('content') or '',finish_reason=last['response']['choices'][0]['finish_reason'],
            **{k:sum(c[k] for c in calls) for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens')},
            logical_calls=len(calls),first_stage_tokens=first['total_tokens'] if method!='B0_high' else 0,
            first_stage_generated_tokens=first['output_tokens'] if method!='B0_high' else 0,
            decision_branch=choices.get(method,'B0'),early_completion_triggered=choices.get(method) in ('B','C'),
            controller_cpu_ms=cpu_ms if method!='B0_high' else 0,controller_llm_calls=0,
            discarded_tail_chars=len(trace)-pos if method!='B0_high' else 0,
            observed_state=state['reasoning_state'] if method!='B0_high' else None,gold_access=False,
            max_generated_tokens=16384)
    results=[record('B0_high',high,[high])]
    for method,branch in choices.items():
        results.append(record(method,first if branch=='finished' else continuations[branch],[first] if branch=='finished' else [first,continuations[branch]]))
    output=dict(task_id=tid,state=state,completed_in_first_stage=completed,choices=choices,results=results)
    save(target,output);return output

def main():
    for p,h in read(OUT/'evidence/pilot_freeze.json')['files'].items():assert sha(ROOT/p)==h,p
    if (OUT/'evidence/PILOT_SEALED.json').exists():
        for p,h in read(OUT/'evidence/PILOT_SEALED.json')['files'].items():assert sha(OUT/p)==h
        print('Independent pilot complete; no API calls.');return
    assert read(OUT/'evidence/online_gate.json')['run_online_pilot']
    ledger=Ledger();pilot=read(OUT/'pilot_config.json');cfg=read(OUT/'config.json');tasks=jl(OUT/'data/independent_public.jsonl')
    # Four tasks concurrently, each has only one HTTP request active at a time.
    with cf.ThreadPoolExecutor(max_workers=4) as pool:outputs=list(pool.map(lambda p:run_task(p,ledger,pilot,cfg),tasks))
    assert len(outputs)==4
    save('evidence/PILOT_SEALED.json',dict(at=now(),n=4,labels_read=False,peak_http_concurrency=ledger.peak,
        files={'online/'+r['task_id']+'.json':sha(OUT/'online'/(r['task_id']+'.json')) for r in outputs}))
    lines('independent_ungraded.jsonl',[r for o in outputs for r in o['results']])
    print(json.dumps(dict(tasks=4,cumulative_known_tokens=ledger.used,unknown_bound=ledger.unknown,total_calls=ledger.calls)))
if __name__=='__main__':main()
