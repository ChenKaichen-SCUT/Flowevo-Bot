from common import *
from transport import Ledger,base_request
import concurrent.futures as cf,random

def request_for(state,branch,config):
    prefix=state['prefix'];assert digest(prefix)==state['prefix_sha256']
    instruction=config['instructions'][branch]
    messages=[dict(role='system',content='You are an expert programmer and mathematician.'),
              dict(role='user',content='Problem: '+state['problem']+'\n\n'+instruction)]
    if config['mode']=='beta_reasoning_prefix_replay':
        messages.append(dict(role='assistant',content='',reasoning_content=prefix,prefix=True))
        endpoint='https://api.deepseek.com/beta/chat/completions'
    else:
        messages[-1]['content']+='\n\nPartial reasoning from a prior attempt (may contain mistakes):\n'+prefix
        endpoint='https://api.deepseek.com/chat/completions'
    return base_request(messages,config['max_tokens']),endpoint

def main():
    for p,h in read(OUT/'evidence/counterfactual_freeze.json')['files'].items():assert sha(ROOT/p)==h,p
    seal=OUT/'evidence/COUNTERFACTUAL_SEALED.json'
    if seal.exists():
        for p,h in read(seal)['files'].items():assert sha(OUT/p)==h
        print('Counterfactual stage already complete; zero API calls.');return
    config=read(OUT/'config.json');states=jl(OUT/'counterfactual_states.jsonl');ledger=Ledger()
    jobs=[(state,branch) for state in states for branch in 'ABC'];random.Random(20261011).shuffle(jobs)
    results=[]
    with cf.ThreadPoolExecutor(max_workers=config['api_workers']) as pool:
        futures=[]
        for state,branch in jobs:
            req,endpoint=request_for(state,branch,config)
            futures.append(pool.submit(ledger.call,state['state_id']+'__'+branch,req,
                dict(stage='counterfactual',state_id=state['state_id'],task_id=state['task_id'],branch=branch,mode=config['mode']),endpoint))
        for future in cf.as_completed(futures):results.append(future.result())
    errors=[r['job_id'] for r in results if r['status']!='completed']
    save('evidence/counterfactual_progress.json',dict(n=len(results),expected=84,errors=errors,known_tokens=ledger.used,unknown_bound=ledger.unknown,calls=ledger.calls,peak_concurrency=ledger.peak))
    assert len(results)==84 and not errors,errors
    save(seal,dict(at=now(),n=84,labels_read=False,files={'raw/'+r['job_id']+'.json':sha(OUT/'raw'/(r['job_id']+'.json')) for r in results}))
    print('SEALED 84 counterfactual calls')
if __name__=='__main__':main()
