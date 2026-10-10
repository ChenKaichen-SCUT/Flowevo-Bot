"""Post-seal descriptive analysis; never launches API requests or changes routing."""
from common import *
from flowevo_recovery.public import State,Task,ACTIONS
from flowevo_recovery.controller import METHODS
from flowevo_recovery.adapter_audit import audit,extract_public_entrypoint
from flowevo_recovery.checks import extract_code,run_tests
from flowevo_bot.v2.evaluator import extract
import collections,concurrent.futures as cf,math,random,itertools,shutil

def adapter_job(job):
 s,label=job;s=State.model_validate(s)
 return {'call_id':s.call_id,'task_id':s.task.task_id,**audit(s,label)}
def paired(a,b):
 n=len(a);wins=sum(x is True and y is False for x,y in zip(a,b));losses=sum(x is False and y is True for x,y in zip(a,b));unknown=sum(x is None or y is None for x,y in zip(a,b))
 if unknown:return {'n':n,'wins':wins,'losses':losses,'unknown_pairs':unknown,'delta_pp':None,'ci95_pp':None}
 delta=[int(x)-int(y) for x,y in zip(a,b)];rng=random.Random(20261010)
 samples=sorted(100*sum(rng.choices(delta,k=n))/n for _ in range(10000)) if n else [0]
 p=min(1,2*sum(math.comb(wins+losses,k) for k in range(min(wins,losses)+1))/(2**(wins+losses))) if wins+losses else 1
 return {'n':n,'wins':wins,'losses':losses,'unknown_pairs':0,'delta_pp':100*(wins-losses)/n if n else None,'ci95_pp':[samples[int(.025*(len(samples)-1))],samples[int(.975*(len(samples)-1))]],'exact_mcnemar_two_sided':p}
def main():
 cap();from campaign import check_freeze
 check_freeze();results=lines(OUT/'task_results.jsonl');calls=[read(p) for p in sorted((OUT/'raw_calls').glob('*.json'))]
 assert not any('.pending.' in str(p) or '.error.' in str(p) for p in (OUT/'raw_calls').glob('*.json'))
 assert all(not r['simulated'] and r['http_attempts']==1 for r in calls)
 jl(OUT/'api_calls.jsonl',[{k:v for k,v in r.items() if k not in ('request','response')}|{'raw_path':'raw_calls/'+r['call_id']+'.json','reasoning_tokens':r['response']['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0),'finish_reason':r['response']['choices'][0]['finish_reason']} for r in calls])
 allstates={}
 for name in ['train_code','train_branches','confirmation_all']:
  for r in lines(OUT/f'evidence/{name}.scored.jsonl'):allstates[r['state']['call_id']]=r['state']
 for s in lines(OUT/'data/train_math_states.jsonl'):allstates[s['call_id']]=s
 labels=read(OUT/'data/offline_labels.json')
 with cf.ProcessPoolExecutor(max_workers=12) as pool:adapters=list(pool.map(adapter_job,[(s,labels[s['task']['task_id']]) for s in allstates.values() if s['task']['domain']=='code']))
 jl(OUT/'evidence/adapter_sensitivity.jsonl',adapters);ad={r['call_id']:r for r in adapters}
 method_stats=[]
 for domain in ('all','math','code'):
  for method in METHODS:
   rr=[r for r in results if r['method']==method and (domain=='all' or r['domain']==domain)];complete=[r for r in rr if r['complete']];known=[r for r in complete if r['final_correct'] is not None]
   sums={k:sum(r[k] for r in complete) for k in ['input_tokens','output_tokens','total_tokens','llm_calls','extra_tokens','rescued','harmed','false_trigger']}
   correct=sum(r['final_correct'] is True for r in complete);rescued=sums['rescued'];tokens=sums['total_tokens']
   m={'domain':domain,'method':method,'n_planned':len(rr),'n_complete':len(complete),'initial_correct':sum(r['initial_correct'] is True for r in rr),'final_correct':correct,'unknown':len(complete)-len(known),'accuracy_lower_bound':correct/len(rr) if rr else None,**sums,
    'triggered':sum(r['action'] is not None for r in rr),'mean_tokens':tokens/len(complete) if complete else None,'extra_tokens_per_rescue':sums['extra_tokens']/rescued if rescued else None,
    'adapter_correct':sum((ad[r['recovery_call_id'] or r['initial_call_id']]['check']['passed'] if r['domain']=='code' else r['final_correct'] is True) for r in complete),
    'memory_consulted':sum(bool(r['memory_sources']) for r in rr),'memory_overrides':sum(r['reason']=='memory_override' for r in rr)}
   method_stats.append(m)
 csvwrite(OUT/'token_costs.csv',method_stats)
 tasks=[]
 for tid in sorted({r['task_id'] for r in results}):
  rows={r['method']:r for r in results if r['task_id']==tid};first=rows['single'];t={'task_id':tid,'domain':first['domain'],'initial_correct':first['initial_correct'],'public_features':first['public_features']}
  for m,r in rows.items():
   for key in ['final_correct','action','total_tokens','rescued','harmed','complete']:t[m+'_'+key]=r[key]
   if first['domain']=='code':t[m+'_adapter_correct']=ad[r['recovery_call_id'] or r['initial_call_id']]['check']['passed'] if r['complete'] else None
  t['A_vs_fixed']=None if not rows['A']['complete'] or not rows['fixed_retry']['complete'] or rows['A']['final_correct'] is None or rows['fixed_retry']['final_correct'] is None else int(rows['A']['final_correct'])-int(rows['fixed_retry']['final_correct'])
  t['C_vs_A']=None if not rows['C']['complete'] or not rows['A']['complete'] or rows['C']['final_correct'] is None or rows['A']['final_correct'] is None else int(rows['C']['final_correct'])-int(rows['A']['final_correct'])
  tasks.append(t)
 csvwrite(OUT/'task_pairwise.csv',tasks)
 pairwise=[]
 for domain in ('all','math','code'):
  for x,y in [('A','single'),('A','fixed_retry'),('A','deterministic_retry'),('C','A'),('C','C_shuffled')]:
   ids=[t['task_id'] for t in tasks if (domain=='all' or t['domain']==domain) and t[x+'_complete'] and t[y+'_complete']]
   ar={r['task_id']:r['final_correct'] for r in results if r['method']==x};br={r['task_id']:r['final_correct'] for r in results if r['method']==y}
   pairwise.append({'domain':domain,'method':x,'reference':y,**paired([ar[t] for t in ids],[br[t] for t in ids])})
 write(OUT/'evidence/paired_uncertainty.json',pairwise)
 branches=lines(OUT/'counterfactual_branches.jsonl');cf_tasks=[]
 for r in lines(OUT/'data/counterfactual_sources.jsonl'):
  s=r['state'];tid=s['task']['task_id'];by={x['action']:x for x in branches if x['state']['task']['task_id']==tid};good=[a for a,x in by.items() if x['score']['correct'] is True]
  complete=set(by)==set(ACTIONS) and all(x['score']['correct'] is not None for x in by.values())
  cls='retry_suffices_observed' if 'retry' in good else 'targeted_only_observed' if good and 'retry' in by and by['retry']['score']['correct'] is False else 'none_recovered_under_budget' if complete else 'incomplete_no_claim'
  cf_tasks.append({'task_id':tid,'domain':s['task']['domain'],'complete_four_actions':complete,'classification':cls,'successful_actions':good,'observed_actions':list(by),'tokens':sum(x['additional_tokens'] for x in by.values()),'source_visible_chars':len(s['solution']),'observable_features':r['features'],
   'adapter_initial_correct':ad[s['call_id']]['check']['passed'] if s['task']['domain']=='code' else None,
   'adapter_successful_actions':[a for a,x in by.items() if ad[x['state']['call_id']]['check']['passed']] if s['task']['domain']=='code' else None})
 csvwrite(OUT/'evidence/counterfactual_task_attribution.csv',cf_tasks);write(OUT/'evidence/counterfactual_summary.json',cf_tasks)
 diagnostics=[]
 for domain in ('math','code'):
  rr=[r for r in results if r['method']=='single' and r['domain']==domain]
  for flag in ['truncated','missing_final','local_contradiction','compile_failed','public_failed']:
   tp=sum(r['public_features'][flag] and r['initial_correct'] is False for r in rr);fp=sum(r['public_features'][flag] and r['initial_correct'] is True for r in rr);fn=sum(not r['public_features'][flag] and r['initial_correct'] is False for r in rr);tn=sum(not r['public_features'][flag] and r['initial_correct'] is True for r in rr)
   diagnostics.append({'domain':domain,'signal':flag,'true_failure_trigger':tp,'correct_trigger':fp,'missed_failure':fn,'correct_no_trigger':tn,'unknown':sum(r['initial_correct'] is None for r in rr),'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None})
 csvwrite(OUT/'evidence/diagnostic_signals.csv',diagnostics)
 physical=[]
 for stage in sorted({r['stage'] for r in calls}):
  rr=[r for r in calls if r['stage']==stage]
  physical.append({'stage':stage,'calls':len(rr),**{k:sum(r[k] for r in rr) for k in ['input_tokens','output_tokens','total_tokens']},'reasoning_tokens':sum(r['response']['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in rr)})
 write(OUT/'evidence/physical_costs.json',physical)
 historical_prefix=[s for s in allstates.values() if s['call_id'] not in {r['call_id'] for r in calls}]
 write(OUT/'evidence/analysis_summary.json',{'method_stats':method_stats,'physical_costs':physical,'total_physical_calls':len(calls),'total_physical_tokens':sum(r['total_tokens'] for r in calls),'counterfactual_classes':dict(collections.Counter(x['classification'] for x in cf_tasks)),'counterfactual_complete_by_domain':dict(collections.Counter(x['domain'] for x in cf_tasks if x['complete_four_actions'])),
  'historical_prefix_calls':len(historical_prefix),'historical_prefix_tokens':sum(s['input_tokens']+s['output_tokens'] for s in historical_prefix),'unknown_final_rows':sum(r['complete'] and r['final_correct'] is None for r in results),'incomplete_method_rows':sum(not r['complete'] for r in results)})
 print(json.dumps(read(OUT/'evidence/analysis_summary.json'),indent=2))
if __name__=='__main__':main()
