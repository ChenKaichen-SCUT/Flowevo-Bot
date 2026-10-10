"""Gold-blind exact-request replay; only max_tokens changes. No automatic resends."""
import concurrent.futures as cf,json,sys,time,hashlib,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'FlowEvo-Recovery/src'),str(ROOT/'Flowevo-Bot/src')]
from flowevo_recovery.math_scoring_v2 import complete
from flowevo_bot.common import digest,write_json,now
import requests

def read(p):return json.loads(p.read_text())
def eligible(record):
    choice=record['response']['choices'][0]
    return choice.get('finish_reason')=='length' or not complete(choice['message'].get('content') or '')

def request_for(task,budget):
    req={**task['request'],'max_tokens':budget}
    assert {k:v for k,v in req.items() if k!='max_tokens'}=={k:v for k,v in task['request'].items() if k!='max_tokens'}
    return req

class Runner:
 def __init__(self,transport=None):
    self.config=read(OUT/'preflight.json');self.transport=transport
    self.key=(ROOT/'miyao.txt').read_text().strip() if transport is None else None
    self.code_hashes=read(OUT/'evidence/frozen_experiment_code.json')
    for f in self.code_hashes:
        assert hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest()==f['sha256']
    self.lock=threading.Lock();self.abort=False
    if list((OUT/'raw').glob('*.pending.json')):raise RuntimeError('Pending request: billing unknown; no blind resend')
 def call(self,task,budget):
    tid=task['task_id'];dest=OUT/'raw'/f'{tid}_{budget}.json';req=request_for(task,budget)
    if dest.exists():
        r=read(dest);assert r['request']==req and r['response_hash']==digest(r['response']);return r
    bound=sum(len(x['content'].encode()) for x in req['messages'])+512+budget
    pending=dest.with_suffix('.pending.json')
    with self.lock:
        if self.abort:raise RuntimeError('Stopped after infrastructure error')
        existing=len(list((OUT/'raw').glob('*.json')))
        if existing>=self.config['max_normal_calls']:raise RuntimeError('Call cap reached')
        write_json(pending,{'task_id':tid,'budget':budget,'request':req,'endpoint':self.config['endpoint'],'started':now(),'reserved_tokens':bound,'code_hashes':self.code_hashes})
    start=time.monotonic()
    try:
        if self.transport:data=self.transport(req);http_status=200;raw_body=json.dumps(data)
        else:
            response=requests.post(self.config['endpoint'],headers={'Authorization':'Bearer '+self.key},json=req,timeout=(30,600))
            http_status=response.status_code;raw_body=response.text
            # Persist body before parsing, including unsuccessful provider replies.
            dest.with_suffix('.http.txt').write_text(raw_body)
            if http_status!=200:raise RuntimeError('Provider HTTP status '+str(http_status))
            data=response.json()
        usage=data['usage'];assert usage['total_tokens']==usage['prompt_tokens']+usage['completion_tokens']
        record={'task_id':tid,'budget':budget,'request':req,'endpoint':self.config['endpoint'],'response':data,'request_hash':digest(req),'response_hash':digest(data),'code_hashes':self.code_hashes,'finished':now(),'latency_seconds':time.monotonic()-start,'http_status':http_status,'input_tokens':usage['prompt_tokens'],'output_tokens':usage['completion_tokens'],'total_tokens':usage['total_tokens'],'reasoning_tokens':usage.get('completion_tokens_details',{}).get('reasoning_tokens'),'infrastructure_retries':0,'correctness_retries':0,'gold_feedback':False,'reserved_tokens':bound}
        write_json(dest,record);pending.unlink()
        if usage['total_tokens']>bound:
            self.abort=True;raise RuntimeError('Actual usage exceeded conservative reservation')
        print(json.dumps({'task_id':tid,'budget':budget,'finish_reason':data['choices'][0]['finish_reason'],'total_tokens':record['total_tokens'],'needs_more_budget':eligible(record)}),flush=True)
        return record
    except Exception as e:
        with self.lock:self.abort=True
        write_json(dest.with_suffix('.error.json'),{'task_id':tid,'budget':budget,'exception_type':type(e).__name__,'billing_unknown':not dest.exists(),'automatic_resend':False,'finished':now()})
        raise RuntimeError('Infrastructure failure; no retry and pending evidence retained') from None

def main():
 tasks=read(OUT/'evidence/public_27.json');assert len(tasks)==27 and len({x['task_id'] for x in tasks})==27
 # These inputs contain no labels, solutions or correctness fields.
 assert all(set(x)=={'task_id','question','subject','level','request','historical_call_id','historical_tokens'} for x in tasks)
 r=Runner()
 with cf.ThreadPoolExecutor(max_workers=min(27,r.config['api_global_limit'])) as pool:
    first=list(pool.map(lambda task:r.call(task,8192),tasks))
 first_seal={'records':[{'task_id':x['task_id'],'request_hash':x['request_hash'],'response_hash':x['response_hash']} for x in first],'sealed_at':now()}
 write_json(OUT/'evidence/rung_8192_seal.json',first_seal)
 selected=[t for t,x in zip(tasks,first) if eligible(x)]
 selection={'rule':'finish_reason=length OR missing complete explicit final answer; independent of gold','eligible_task_ids':[x['task_id'] for x in selected],'first_seal_hash':digest(first_seal),'decided_at':now(),'offline_evaluator_invoked':False}
 write_json(OUT/'evidence/escalation_decision.json',selection)
 print('SEALED first rung; escalating '+str(len(selected))+' by observable completeness only',flush=True)
 with cf.ThreadPoolExecutor(max_workers=min(27,r.config['api_global_limit'])) as pool:
    second=list(pool.map(lambda task:r.call(task,16384),selected))
 allrecords=first+second
 assert len(allrecords)<=54 and sum(x['total_tokens'] for x in allrecords)<=r.config['max_total_token_reservation']
 with (OUT/'api_calls.jsonl').open('w') as f:
    for x in allrecords:f.write(json.dumps(x,ensure_ascii=False)+'\n')
 write_json(OUT/'evidence/generation_complete_seal.json',{'sealed_at':now(),'api_calls_sha256':hashlib.sha256((OUT/'api_calls.jsonl').read_bytes()).hexdigest(),'normal_calls':len(allrecords),'all_submitted_before_offline_evaluation':True,'selection_hash':digest(selection),'actual_total_tokens':sum(x['total_tokens'] for x in allrecords)})
 print('GENERATION COMPLETE '+str(len(allrecords))+' calls; '+str(sum(x['total_tokens'] for x in allrecords))+' tokens.',flush=True)
if __name__=='__main__':main()
