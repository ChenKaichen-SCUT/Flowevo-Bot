"""Frozen, gold-blind decisions precede every confirmation recovery and score."""
from common import *
from campaign import check_freeze,client,execute_jobs,state_from_call,barrier_score
from flowevo_recovery.public import Task,State,recovery_prompt
from flowevo_recovery.controller import METHODS,select
from flowevo_bot.v2.evaluator import seal,assert_sealed

def main():
 cap();freeze=check_freeze();rows=lines(OUT/'data/confirmation_public_states.jsonl');memory=lines(OUT/'recovery_experiences.jsonl');shuffled=lines(OUT/'data/shuffled_experiences.jsonl')
 decisions=[];jobs={};states={};flags={};ordered=[]
 for r in rows:
  s=State.model_validate(r['state']);tid=s.task.task_id;states[tid]=s;flags[tid]=r['features']
  for method in METHODS:
   choice=select(method,r['features'],shuffled if method=='C_shuffled' else memory)
   decisions.append({'task_id':tid,'domain':s.task.domain,'method':method,**choice,'public_features':r['features'],'state_hash':digest(s.model_dump()),'frozen_configuration_hash':digest(freeze)})
 # Priority is fixed before correctness access; identical action samples shared across methods.
 for methods in [('fixed_retry',),('deterministic_retry','A','C'),('C_shuffled',)]:
  for d in decisions:
   if d['method'] not in methods or not d['action']:continue
   key=(d['task_id'],d['action'])
   if key in jobs:continue
   s=states[key[0]];jobs[key]=(s.task,recovery_prompt(s,key[1],flags[key[0]]),'confirmation_recovery:'+key[0]+':'+key[1],key[1]);ordered.append(key)
 jl(OUT/'controller_decisions.jsonl',decisions)
 jl(OUT/'evidence/confirmation.decisions.sealed.jsonl',[seal(d) for d in decisions])
 write(OUT/'evidence/confirmation_decision_barrier.json',{'at':now(),'decisions_hash':sha(OUT/'controller_decisions.jsonl'),'jobs':ordered,'correctness_not_accessed':True})
 c=client();calls=[];stops=[]
 # Separate priorities avoid queued low-priority jobs claiming budget first.
 primary_keys={(d['task_id'],d['action']) for d in decisions if d['method'] in ('deterministic_retry','A','C') and d['action']}
 groups=[[k for k in ordered if k[1]=='retry'],[k for k in ordered if k[1]!='retry' and k in primary_keys],[k for k in ordered if k[1]!='retry' and k not in primary_keys]]
 for group in groups:
  selected=[jobs[k] for k in group]
  results,skips=execute_jobs(selected,'confirmation_recovery',c);calls+=results;stops+=skips
 branches=[state_from_call(states[r['task_id']].task,r) for r in calls]
 jl(OUT/'evidence/confirmation.branches.sealed.jsonl',[seal(s.model_dump()) for s in branches])
 write(OUT/'evidence/confirmation_output_barrier.json',{'at':now(),'initial_hash':sha(OUT/'evidence/confirmation.initial.sealed.jsonl'),'decision_hash':sha(OUT/'controller_decisions.jsonl'),'branches_hash':sha(OUT/'evidence/confirmation.branches.sealed.jsonl'),'before_label_access':True})
 for r in lines(OUT/'evidence/confirmation.initial.sealed.jsonl')+lines(OUT/'evidence/confirmation.branches.sealed.jsonl')+lines(OUT/'evidence/confirmation.decisions.sealed.jsonl'):assert_sealed(r)
 scored=barrier_score(list(states.values())+branches,'confirmation_all')
 bycall={r['state']['call_id']:r for r in scored};call_lookup={(r['task_id'],r['action']):r for r in calls};out=[]
 for d in decisions:
  initial=states[d['task_id']];baseline=bycall[initial.call_id];chosen=call_lookup.get((d['task_id'],d['action'])) if d['action'] else None
  complete=d['action'] is None or chosen is not None
  final=bycall[chosen['call_id']] if chosen else (baseline if not d['action'] else None)
  cost_in=initial.input_tokens+(chosen['input_tokens'] if chosen else 0);cost_out=initial.output_tokens+(chosen['output_tokens'] if chosen else 0)
  out.append({**d,'complete':complete,'initial_correct':baseline['score']['correct'],'final_correct':final['score']['correct'] if final else None,
   'initial_call_id':initial.call_id,'recovery_call_id':chosen['call_id'] if chosen else None,
   'input_tokens':cost_in,'output_tokens':cost_out,'total_tokens':cost_in+cost_out,'llm_calls':1+bool(chosen),
   'extra_tokens':chosen['total_tokens'] if chosen else 0,'initial_score':baseline['score'],'final_score':final['score'] if final else None,
   'rescued':complete and baseline['score']['correct'] is False and final['score']['correct'] is True,
   'harmed':complete and baseline['score']['correct'] is True and final['score']['correct'] is False,
   'false_trigger':d['action'] is not None and baseline['score']['correct'] is True})
 jl(OUT/'task_results.jsonl',out)
 write(OUT/'evidence/confirmation_budget.json',{'calls':c.calls,'tokens':c.actual,'skipped':stops,'unexecuted_decisions':sum(not r['complete'] for r in out)})
 check_freeze();print('confirmation_complete',len(out),'method_rows','calls',c.calls,'tokens',c.actual)
if __name__=='__main__':main()
