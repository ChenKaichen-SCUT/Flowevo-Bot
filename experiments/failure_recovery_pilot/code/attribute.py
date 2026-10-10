from common import *
from flowevo_recovery.checks import extract_code
from flowevo_bot.v2.evaluator import extract
import collections

def main():
 cases=[r for r in lines(OUT/'failure_cases.jsonl') if r.get('stage')=='historical_audit']
 adapters={r['call_id']:r for r in lines(OUT/'evidence/adapter_sensitivity.jsonl')}
 initial={r['task_id']:r for r in lines(OUT/'task_results.jsonl') if r['method']=='single'}
 sources=[]
 for s in lines(OUT/'data/train_math_states.jsonl'):sources.append(('train_math',s,None,None))
 for r in lines(OUT/'evidence/train_code.scored.jsonl'):
  if r['score']['correct'] is False:sources.append(('train_code',r['state'],r['features'],r['score']))
 for r in lines(OUT/'data/confirmation_public_states.jsonl'):
  tid=r['state']['task']['task_id']
  if initial[tid]['initial_correct'] is False:sources.append(('confirmation',r['state'],r['features'],initial[tid]['initial_score']))
 for stage,s,f,g in sources:
  tid=s['task']['task_id'];domain=s['task']['domain'];primary='Unknown';secondary=[];location='not localizable from available evidence';evidence=[];unknown='No demonstrated algorithmic root cause.'
  if s['truncated']:primary='Truncation Failure';secondary=['Answer/Format Failure'];location='provider output budget';evidence=[{'finish_reason':'length','visible_characters':len(s['solution'])}];unknown='Missing final output is observable; empty math response cannot support continuation of visible reasoning.'
  elif domain=='code' and adapters[s['call_id']]['changed_extraction'] and adapters[s['call_id']]['check']['passed']:
   primary='Answer/Format Failure';secondary=['Evaluator/Environment Issue'];location='native first-code-block extraction';evidence=[adapters[s['call_id']]];unknown='No algorithm-recovery need demonstrated; zero-call extraction passes offline tests.'
  elif tid=='math_train_prealgebra_76':
   primary='Constraint Failure';location='adds unrequested exact-payment constraint';evidence=['30+8*.25=32, leaving.75; eight dimes suffice if change is allowed. Candidate requires exact payment, uses seven quarters and ten dimes.'];unknown='Payment wording admits pragmatic ambiguity; a semantic assumption failure relative to dataset reference, not a verified arithmetic error.'
  elif tid=='mbpp_train_968':
   primary='Unknown';secondary=['Strategy Failure','Evaluator/Environment Issue'];location='underspecified periodic function; hidden mismatch with one public example';evidence=['Candidate chooses min(a,b,c), public(11,10,9)=9 passes; hidden(5,7,4) expects2, returns4. Task text omits formula and parameter meanings.'];unknown='Cannot distinguish model strategy weakness from insufficient public specification; do not inject hidden counterexample.'
  elif domain=='code':
   primary='Verification Failure';secondary=['Unknown'];location='offline code tests';evidence=[g];unknown='Test failure established, but local bug versus strategy versus specification ambiguity unresolved.'
  cases.append({'task_id':tid,'domain':domain,'stage':stage,'subject':s['task']['subject'],'level':s['task']['level'],'problem':s['task']['problem'],'original_solution':s['solution'],
   'original_final_answer':extract(s['solution'])[0] if domain=='math' else extract_code(s['solution']),'original_offline_correct':False,'reviewed_correct':False,'truncated':s['truncated'],'primary':primary,'secondary':secondary,'failure_location':location,'evidence':evidence,'unknowns':unknown,'local_error_verified':False,'public_features':f,'call_id':s['call_id'],'state_hash':digest(s),'use':'training_only' if stage.startswith('train') else 'postseal_confirmation_analysis','gold_free_first_pass':True})
 jl(OUT/'failure_cases.jsonl',cases)
 csvwrite(OUT/'failure_labels.csv',[{k:v for k,v in r.items() if k in ['task_id','domain','stage','primary','secondary','truncated','reviewed_correct','failure_location','unknowns']} for r in cases])
 summaries={stage:{d:dict(collections.Counter(r['primary'] for r in cases if r['stage']==stage and r['domain']==d)) for d in ('math','code')} for stage in sorted({r['stage'] for r in cases})}
 write(OUT/'evidence/taxonomy_summary.json',summaries)
 rs=lines(OUT/'task_results.jsonl');by=collections.defaultdict(dict)
 for r in rs:by[r['task_id']][r['method']]=r
 attribution=[]
 for tid,rows in sorted(by.items()):
  first=rows['single'];f=rows['fixed_retry'];a=rows['A']
  if first['initial_correct']:kind='unnecessary_retry_harmed' if f['harmed'] else 'correct_control'
  elif f['final_correct']:kind='retry_suffices_observed'
  elif a['final_correct']:kind='A_only_observed'
  else:kind='no_recovery_in_tested_actions'
  adapter=adapters.get(first['initial_call_id']);artifact=bool(adapter and adapter['changed_extraction'] and adapter['check']['passed'])
  attribution.append({'task_id':tid,'domain':first['domain'],'initial_correct':first['initial_correct'],'class':kind,'A_final':a['final_correct'],'retry_final':f['final_correct'],'deterministic_final':rows['deterministic_retry']['final_correct'],'C_changes_A':rows['C']['action']!=a['action'],'extraction_artifact':artifact,'initial_output_empty':len(next(r['state']['solution'] for r in lines(OUT/'data/confirmation_public_states.jsonl') if r['state']['task']['task_id']==tid))==0,
    'mechanism':'zero_call_adapter_already_suffices' if artifact else 'budget_limited_resampling_no_visible_trace' if first['public_features']['truncated'] else 'no_observable_failure' if not a['action'] else 'public_diagnostic_repair'})
 csvwrite(OUT/'evidence/confirmation_attribution.csv',attribution);write(OUT/'evidence/confirmation_attribution.json',attribution)
 print('failure_cases',len(cases),'confirmation_classes',dict(collections.Counter(r['class'] for r in attribution)))
if __name__=='__main__':main()
