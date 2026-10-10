"""Phase-separated experiment: score only after every requested output is sealed."""
import argparse,concurrent.futures as cf,time
from common import *
from flowevo_recovery.public import Task,State,ACTIONS,base_prompt,recovery_prompt
from flowevo_recovery.checks import features,feature_key
from flowevo_recovery.client import Client,BudgetStop
from flowevo_recovery.grading import score
from flowevo_bot.v2.evaluator import seal,assert_sealed

def state_from_call(task,r):
 c=r['response']['choices'][0]
 return State(task=task,solution=c['message']['content'],truncated=c['finish_reason']=='length',call_id=r['call_id'],input_tokens=r['input_tokens'],output_tokens=r['output_tokens'])
def diagnostic(s):return features(State.model_validate(s))
def scoring(job):
 state,label=job;s=State.model_validate(state)
 return score(s.task,s.solution,s.truncated,label)
def client(training=False):
 config=read(OUT/'config.json')
 if training:config['max_tokens']=config['training_token_soft_cap']
 key=(ROOT/'miyao.txt').read_text().strip()
 code_hash=digest({p.name:sha(p) for p in (ROOT/'FlowEvo-Recovery/src/flowevo_recovery').glob('*.py')})
 return Client(OUT/'raw_calls',key,config,code_hash)
def execute_jobs(jobs,stage,c):
 results=[];stops=[]
 def work(job):
  task,prompt,jobid,action=job
  try:return c.complete(task,prompt,jobid,stage,action)
  except BudgetStop:return {'budget_stop':True,'job_id':jobid}
 with cf.ThreadPoolExecutor(max_workers=read(OUT/'config.json')['api_workers']) as pool:
  futures={pool.submit(work,j):j for j in jobs}
  for f in cf.as_completed(futures):
   r=f.result()
   if r.get('budget_stop'):stops.append(r)
   else:results.append(r)
   print(stage,'finished',len(results),'budget_skipped',len(stops),'paid_calls',c.calls,'paid_tokens',c.actual,flush=True)
 return results,stops
def barrier_score(states,name):
 sealed=[seal(s.model_dump()) for s in states];jl(OUT/f'evidence/{name}.sealed.jsonl',sealed)
 write(OUT/f'evidence/{name}.barrier.json',{'at':now(),'count':len(states),'hash':sha(OUT/f'evidence/{name}.sealed.jsonl'),'before_label_access':True})
 for r in sealed:assert_sealed(r)
 labels=read(OUT/'data/offline_labels.json')
 with cf.ProcessPoolExecutor(max_workers=12) as pool:
  scores=list(pool.map(scoring,[(s.model_dump(),labels[s.task.task_id]) for s in states]));fs=list(pool.map(diagnostic,[s.model_dump() for s in states]))
 records=[{'state':s.model_dump(),'score':g,'features':f} for s,g,f in zip(states,scores,fs)]
 jl(OUT/f'evidence/{name}.scored.jsonl',records);return records
def initial(stage):
 cap();name='train_code' if stage=='train_initial' else 'confirmation';path='train_code_tasks.jsonl' if stage=='train_initial' else 'confirmation_tasks.jsonl'
 if stage!='train_initial':check_freeze()
 tasks=[Task.model_validate(r) for r in lines(OUT/'data'/path)];c=client()
 jobs=[(t,base_prompt(t),stage+':'+t.task_id,'initial') for t in tasks]
 calls,stops=execute_jobs(jobs,stage,c);byid={r['task_id']:r for r in calls}
 states=[state_from_call(t,byid[t.task_id]) for t in tasks if t.task_id in byid]
 if stage=='train_initial':barrier_score(states,name)
 else:
  # Crucially, confirmation initial correctness is not computed until recovery decisions AND outputs are frozen.
  jl(OUT/'evidence/confirmation.initial.sealed.jsonl',[seal(s.model_dump()) for s in states])
  with cf.ProcessPoolExecutor(max_workers=12) as pool:fs=list(pool.map(diagnostic,[s.model_dump() for s in states]))
  jl(OUT/'data/confirmation_public_states.jsonl',[{'state':s.model_dump(),'features':f} for s,f in zip(states,fs)])
 write(OUT/f'evidence/{stage}.budget.json',{'calls':c.calls,'tokens':c.actual,'skipped':stops})
def counterfactual():
 cap();c=client(training=True);train=lines(OUT/'evidence/train_code.scored.jsonl')
 fail=[r for r in train if r['score']['correct'] is False]
 fail=sorted(fail,key=lambda r:digest(r['state']['task']['task_id']))[:read(OUT/'config.json')['train_code_failure_cap']]
 states=[State.model_validate(s) for s in lines(OUT/'data/train_math_states.jsonl')]+[State.model_validate(r['state']) for r in fail]
 with cf.ProcessPoolExecutor(max_workers=12) as pool:fs=list(pool.map(diagnostic,[s.model_dump() for s in states]))
 jl(OUT/'data/counterfactual_sources.jsonl',[{'state':s.model_dump(),'features':f} for s,f in zip(states,fs)])
 jobs=[]
 for s,f in zip(states,fs):
  for action in ACTIONS:jobs.append((s.task,recovery_prompt(s,action,f),'train_cf:'+s.task.task_id+':'+action,action))
 calls,stops=execute_jobs(jobs,'train_counterfactual',c)
 tasks={s.task.task_id:s.task for s in states};records=barrier_score([state_from_call(tasks[r['task_id']],r) for r in calls],'train_branches')
 lookup={r['call_id']:r for r in calls}
 for r in records:
  call=lookup[r['state']['call_id']];r.update(action=call['action'],additional_tokens=call['total_tokens'],source_state_hash=digest(next(s.model_dump() for s in states if s.task.task_id==call['task_id'])))
 jl(OUT/'counterfactual_branches.jsonl',records)
 csvwrite(OUT/'intervention_outcomes.csv',[{'task_id':r['state']['task']['task_id'],'domain':r['state']['task']['domain'],'action':r['action'],'correct':r['score']['correct'],'additional_tokens':r['additional_tokens'],'call_id':r['state']['call_id']} for r in records])
 write(OUT/'evidence/counterfactual_budget.json',{'calls':c.calls,'tokens':c.actual,'skipped':stops})
def check_freeze():
 record=read(OUT/'evidence/freeze.json')
 assert all(sha(ROOT/p)==h for p,h in record['files'].items()),'frozen_runtime_changed'
 return record
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['train_initial','counterfactual','confirmation_initial']);a=p.parse_args()
 counterfactual() if a.stage=='counterfactual' else initial(a.stage)
