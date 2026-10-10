"""Explicit post-seal assistant mathematical audit of three unparsed answers; runtime grader unchanged."""
from common import *
from flowevo_bot.v2.evaluator import assert_sealed
from campaign import check_freeze

def main():
 check_freeze();source=OUT/'task_results.jsonl';backup=OUT/'snapshots/task_results_automatic.jsonl'
 if not backup.exists():backup.write_bytes(source.read_bytes())
 rows=lines(backup);states={r['state']['call_id']:r['state'] for r in lines(OUT/'evidence/confirmation_all.scored.jsonl')}
 reviewed={
  '4dda4f2258ba2110e504dac87387b44bb16c676adc3c5cc7f7e714a80a8b8824':('math_train_number_theory_198','October 30','September Mondays4,11,18,25; October Mondays2,9,16,23,30. Candidate equals textual reference date.'),
  'e0c76e98c4200ac1cda143e734ba67230cedfc3b0c011a482b545447170a6265':('math_train_number_theory_198','October 30','Same calendar computation and same textual reference date; audited independently of method label.'),
  '01db0454a9776553d59665d39538a0c14355d0352fa80a837ac9ee6a5b741221':('math_train_intermediate_algebra_501','[1, -1, i, -i]','Subtract k times the first polynomial equation from the second: a(1-k^4)=0, so k^4=1. All four roots admissible: a=b=c=d=1 for -1,i,-i; a=b=c=1,d=-3 for1. Bracketed list is a set of requested roots, not an interval.')}
 records=[]
 for cid,(tid,answer,evidence) in reviewed.items():
  s=states[cid];assert s['task']['task_id']==tid and not s['truncated'] and answer in s['solution']
  records.append({'call_id':cid,'task_id':tid,'automatic_correct':None,'adjudicated_correct':True,'reason':'explicit_unparsed_representation','candidate_answer':answer,'evidence':evidence,'state_hash':digest(s),'response_hash':read(OUT/'raw_calls'/f'{cid}.json')['response_hash'],'after_all_outputs_sealed':True,'changes_to_runtime_or_prompts':False,'reviewer':'assistant_explicit_math_audit','independent_human_review':False})
 for r in rows:
  r['automatic_initial_correct']=r['initial_correct'];r['automatic_final_correct']=r['final_correct']
  r['initial_adjudication']=r['initial_call_id'] in reviewed;r['final_adjudication']=(r['recovery_call_id'] or r['initial_call_id']) in reviewed
  if r['initial_adjudication']:assert r['initial_correct'] is None;r['initial_correct']=True
  if r['final_adjudication']:assert r['final_correct'] is None;r['final_correct']=True
  r['rescued']=r['complete'] and r['initial_correct'] is False and r['final_correct'] is True
  r['harmed']=r['complete'] and r['initial_correct'] is True and r['final_correct'] is False
  r['false_trigger']=r['action'] is not None and r['initial_correct'] is True
 jl(OUT/'evidence/manual_adjudications.jsonl',records);jl(source,rows)
 write(OUT/'evidence/adjudication_barrier.json',{'at':now(),'frozen_runtime_intact':True,'automatic_results_hash':sha(backup),'adjudications_hash':sha(OUT/'evidence/manual_adjudications.jsonl'),'adjudicated_results_hash':sha(source),'unknown_unique_outputs_reviewed':3,'policy':'all unknown unique outputs inspected; no false/true score selectively regraded; every method using the same output receives the same judgment'})
 print('adjudicated',len(records),'unique outputs; runtime untouched')
if __name__=='__main__':main()
