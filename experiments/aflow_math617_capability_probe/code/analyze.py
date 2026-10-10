"""Join sealed generations, immutable V3 judgments and explicit posthoc reviews."""
from common import *
import csv,collections,math

def csvfile(name,rows,fields=None):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w')as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

def metric(rs):
 n=len(rs);known=sum(r['mathematical_correct']is True for r in rs);unknown=sum(r['mathematical_correct']is None for r in rs)
 return {'n':n,'v3_correct':sum(r['v3_status']=='correct'for r in rs),'v3_status_counts':dict(collections.Counter(r['v3_status']for r in rs)),'reviewed_math_correct':known,'math_unresolved':unknown,'math_accuracy_lower':known/n if n else None,'math_accuracy_upper':(known+unknown)/n if n else None,'complete_math_errors':sum(r['complete_math_error']for r in rs),'incomplete':sum(not r['answer_complete']for r in rs),'input_tokens':sum(r['input_tokens']for r in rs),'output_tokens':sum(r['output_tokens']for r in rs),'reasoning_tokens':sum(r['reasoning_tokens']for r in rs)if all(isinstance(r['reasoning_tokens'],int)for r in rs)else None,'tokens':sum(r['total_tokens']for r in rs),'logical_calls':n,'reused_calls':sum(r['reused']for r in rs),'new_completed_calls':sum(not r['reused']for r in rs)}

def main():
 for stage in ['validation1','validation4','test1']:
  seal=read(OUT/'checkpoints'/f'{stage}_SEALED.json')
  for p,h in seal['files'].items():assert sha(OUT/p)==h
 for p,h in read(OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json')['files'].items():assert sha(ROOT/p)==h,p
 meta={r['task_id']:r for r in read(OUT/'dataset_manifest.json')['tasks']}
 public={r['task_id']:r for r in jl(OUT/'data/public_tasks.jsonl')}
 calls=sorted([read(p)for p in (OUT/'raw').glob('*__c*.json')],key=lambda r:r['job_id']);assert len(calls)==962
 scores={r['source_job_id']:r for stage in ['validation1','validation4','test1']for r in jl(OUT/'grading'/f'{stage}.jsonl')}
 reviews={r['job_id']:r for stage in ['validation1','validation4','test1']for r in jl(OUT/f'{stage}_adjudications.jsonl')}
 rows=[];failure=[]
 for r in calls:
  t=meta[r['task_id']];s=scores[r['job_id']];a=reviews.get(r['job_id']);complete=not r['completion']['retry_required']
  if a:assert a['response_hash']==r['response_hash']
  correct=a['mathematical_correct']if a else True if s['status']=='correct'else False if not complete else None
  row={'task_id':r['task_id'],'split':t['split'],'subject':t['subject'],'level':t['level'],'candidate':r['candidate'],'job_id':r['job_id'],'response_path':f"raw/{r['job_id']}.json",'request_hash':r['request_hash'],'response_hash':r['response_hash'],'final_answer':s['prediction_extracted'],'finish_reason':r['finish_reason'],'answer_complete':complete,'is_truncated':r['finish_reason']=='length','v3_status':s['status'],'v3_reason':s['reason'],'mathematical_correct':correct,'adjudication_category':a['category']if a else None,'complete_math_error':bool(a and a['complete_math_error']),'audit_proof':a['proof']if a else None,'model_version':r['model_version'],'backend_revision':r['backend_revision'],'thinking':'enabled (default)','reasoning_effort':'high (default)','sampling_effective':'Provider-default thinking sampler; temperature=0 ignored, seed unavailable','input_tokens':r['input_tokens'],'output_tokens':r['output_tokens'],'reasoning_tokens':r['reasoning_tokens'],'final_content_tokens':r['final_content_tokens'],'total_tokens':r['total_tokens'],'reused':r['reused'],'historical_source':r.get('source_path')if r['reused']else None,'known_historical_exposure':t['exposure']['known_previous_solve_or_analysis'],'conservative_registry_flag':t['exposure']['conservative_prior_registry_flag'],'strict_clean_of_recorded_and_near_exposure':t['exposure']['strict_clean_of_recorded_and_near_exposure']}
  rows.append(row)
  if s['status']!='correct':
   assert a is not None,'Unreviewed noncorrect: '+r['job_id']
   failure.append({**row,'question':public[r['task_id']]['problem'],'model_final_text':r['response']['choices'][0]['message'].get('content')or '','proof_source':'Explicit response-hash-bound posthoc mathematical audit; not a change to frozen V3 or to public selectors'})
 baseline=[r for r in rows if r['candidate']==1];validation=[r for r in rows if r['split']=='validation'];rmap={r['job_id']:r for r in rows}
 lines('baseline_results.jsonl',baseline);lines('candidate_generations.jsonl',validation);lines('failure_cases.jsonl',failure);lines('api_calls.jsonl',calls)
 stats={split:metric([r for r in baseline if split=='all'or r['split']==split])for split in ('validation','test','all')}
 subjects={split:{sub:metric([r for r in baseline if r['subject']==sub and (split=='all'or r['split']==split)])for sub in sorted({r['subject']for r in baseline})}for split in ('validation','test','all')}
 exposure={split:{stratum:metric([r for r in baseline if r['split']==split and (r['strict_clean_of_recorded_and_near_exposure']if stratum=='strict_clean'else not r['strict_clean_of_recorded_and_near_exposure'])])for stratum in ['strict_clean','recorded_or_near_exposure_risk']}for split in ['validation','test']}
 passrows=[];sels=[];gap=[];pairs=[]
 choices={r['task_id']:r for r in jl(OUT/'selection_public_k4.jsonl')}
 for tid,choice in choices.items():
  cs=[rmap[f'{tid}__c{k}']for k in range(1,5)];first=cs[0];oracle=any(c['mathematical_correct']is True for c in cs);voracle=any(c['v3_status']=='correct'for c in cs)
  for method,n in choice['selections'].items():
   chosen=cs[n-1];sels.append({'task_id':tid,'subject':first['subject'],'k':4,'method':method,'selected_candidate':n,'selected_job_id':chosen['job_id'],'v3_status':chosen['v3_status'],'mathematical_correct':chosen['mathematical_correct'],'oracle_math_correct':oracle,'oracle_v3_correct':voracle,'math_generation_selection_gap':int(oracle)-int(chosen['mathematical_correct']is True),'selection_record_path':'selection_public_k4.jsonl','new_selection_api_calls':0,'new_selection_tokens':0,'candidate_pool_tokens':sum(c['total_tokens']for c in cs),'public_certificate_applied':choice['certificate_applicable'],'gold_used_to_select':False})
  maj=next(r for r in sels if r['task_id']==tid and r['method']=='majority');ver=next(r for r in sels if r['task_id']==tid and r['method']=='verification')
  pairs.append({'task_id':tid,'subject':first['subject'],'first_correct':first['mathematical_correct'],'pass4_correct':oracle,'majority_correct':maj['mathematical_correct'],'verification_correct':ver['mathematical_correct'],'new_math_recovery':oracle and first['mathematical_correct']is not True,'new_complete_error_recovery':oracle and first['complete_math_error'],'first_tokens':first['total_tokens'],'pass4_tokens':sum(c['total_tokens']for c in cs),'extra_calls':3,'extra_tokens':sum(c['total_tokens']for c in cs[1:]),'answer_equivalence_groups':json.dumps(choice['equivalence_groups']),'structure_tag_variants':len({tuple(v)for v in choice.get('structure_tags',{}).values()}),'any_complete_wrong_candidate':any(c['complete_math_error']for c in cs),'all_four_without_confirmed_correct':not oracle})
 for sub in ['all']+sorted({r['subject']for r in validation}):
  tasks=[r for r in pairs if sub=='all'or r['subject']==sub];ids={r['task_id']for r in tasks}
  for k in (1,4,8):
   rs=[r for r in validation if r['task_id']in ids and r['candidate']<=k];vcorrect=sum(any(c['v3_status']=='correct'for c in rs if c['task_id']==tid)for tid in ids);mcorrect=sum(any(c['mathematical_correct']is True for c in rs if c['task_id']==tid)for tid in ids)
   passrows.append({'split':'validation','subject':sub,'k':k,'n':len(ids),'measured':k!=8,'v3_correct':vcorrect if k!=8 else 'NA','v3_accuracy':vcorrect/len(ids)if k!=8 else 'NA','math_correct':mcorrect if k!=8 else 'NA','math_accuracy':mcorrect/len(ids)if k!=8 else 'NA','logical_calls':len(rs)if k!=8 else 0,'tokens':sum(c['total_tokens']for c in rs)if k!=8 else 0,'new_recoveries_over_first':sum(r['new_math_recovery']for r in tasks)if k==4 else 0 if k==1 else 'NA','note':'Oracle existence over ordered independent candidates; full119 validation'if k!=8 else 'Not run: predeclared complementarity gate not met'})
  for method in ('first','majority','verification'):
   ss=[r for r in sels if r['task_id']in ids and r['method']==method];gap.append({'subject':sub,'k':4,'method':method,'n':len(ids),'oracle_math_correct':sum(r['oracle_math_correct']for r in ss),'selected_math_correct':sum(r['mathematical_correct']is True for r in ss),'gap_tasks':sum(r['math_generation_selection_gap']for r in ss),'gap_percentage_points':100*sum(r['math_generation_selection_gap']for r in ss)/len(ids),'oracle_v3_correct':sum(r['oracle_v3_correct']for r in ss),'selected_v3_correct':sum(r['v3_status']=='correct'for r in ss)})
 lines('selection_results.jsonl',sels);csvfile('task_pairwise.csv',pairs);csvfile('pass_at_k.csv',passrows);csvfile('generation_selection_gap.csv',gap)
 tax=[]
 for scope,rs in [('validation_baseline',[r for r in failure if r['split']=='validation'and r['candidate']==1]),('validation_all_candidates',[r for r in failure if r['split']=='validation']),('test_baseline',[r for r in failure if r['split']=='test'])]:
  for sub in ['all']+sorted({r['subject']for r in rows}):
   for category in 'ABCDEFGHI':
    fs=[r for r in rs if r['adjudication_category']==category and (sub=='all'or r['subject']==sub)];tax.append({'scope':scope,'subject':sub,'category':category,'response_count':len(fs),'unique_tasks':len({r['task_id']for r in fs}),'confirmed_complete_math_errors':sum(r['complete_math_error']for r in fs)})
 csvfile('failure_taxonomy.csv',tax)
 attempts=[read(p)for p in (OUT/'attempts').glob('*.json')if not p.name.endswith('.pending.json')]
 assert not list((OUT/'attempts').glob('*.pending.json'))
 successful={a['job_id']:a for a in attempts if a['usage_known']}
 assert set(successful)=={r['job_id']for r in calls if not r['reused']}
 for r in calls:
  if not r['reused']:assert successful[r['job_id']]['total_tokens']==r['total_tokens']
 costs=[]
 groups={'validation_single16384':[r for r in rows if r['split']=='validation'and r['candidate']==1],'validation_pass4_pool':validation,'validation_pass4_extra':[r for r in validation if r['candidate']>1],'test_single16384':[r for r in baseline if r['split']=='test'],'all605_single16384':baseline,'physical_new_experiment':[r for r in rows if not r['reused']]}
 for method,rs in groups.items():
  m=metric(rs);failed=[a for a in attempts if not a['usage_known']and a['job_id']in {r['job_id']for r in rs}]
  costs.append({'method':method,'logical_completed_calls':len(rs),'new_completed_calls':m['new_completed_calls'],'reused_calls':m['reused_calls'],'new_http_attempts':m['new_completed_calls']+len(failed),'input_tokens':m['input_tokens'],'output_tokens':m['output_tokens'],'reasoning_tokens':m['reasoning_tokens'],'total_tokens':m['tokens'],'usage_unknown_attempts':len(failed),'unknown_token_upper_bound':sum(a['reserved_tokens']for a in failed),'peak_uncached_usd_estimate':round(m['input_tokens']*.3e-6+m['output_tokens']*1.2e-6,6)})
 for method in ('majority_selection_only','verification_selection_only','pass8_not_run','official_aflow_not_run'):
  costs.append(dict.fromkeys(costs[0],0)|{'method':method})
 csvfile('cost_breakdown.csv',costs)
 generation_signals={'initial_validation_noncorrect_v3_tasks':7,'initial_math_not_correct_tasks':sum(r['mathematical_correct']is not True for r in baseline if r['split']=='validation'),'math_recovered_tasks':[r['task_id']for r in pairs if r['new_math_recovery']],'all_four_failed_tasks':[r['task_id']for r in pairs if r['all_four_without_confirmed_correct']],'complete_math_error_recoveries':[r['task_id']for r in pairs if r['new_complete_error_recovery']],'majority_gaps':[r['task_id']for r in sels if r['method']=='majority'and r['math_generation_selection_gap']],'verification_gaps':[r['task_id']for r in sels if r['method']=='verification'and r['math_generation_selection_gap']],'certificate_tasks':sum(r['certificate_applicable']for r in choices.values()),'certified_candidates':sum(d['verification_status']=='certified_answer'for r in choices.values()for d in r['candidate_diagnostics']),'unsupported_candidates':sum(d['parse_status']=='unsupported'for r in choices.values()for d in r['candidate_diagnostics']),'symbolic_timeouts':sum(r.get('selection_status')=='public_symbolic_timeout_first_fallback'for r in choices.values())}
 statsall={'created_at':now(),'baseline':stats,'baseline_by_subject':subjects,'exposure_strata':exposure,'pass_at_k':passrows,'selection_gap':gap,'generation_signals':generation_signals,'costs':costs,'validation_candidate_status_counts':dict(collections.Counter(r['v3_status']for r in validation)),'failure_category_counts':dict(collections.Counter(r['adjudication_category']for r in failure)),'models':dict(collections.Counter(r['model_version']for r in calls)),'backend_fingerprints':dict(collections.Counter(r['backend_revision']for r in calls)),'actual_physical_new_http_attempts':len(attempts),'physical_new_known_tokens':sum(a.get('total_tokens',0)for a in attempts),'physical_unknown_token_upper_bound':sum(a['reserved_tokens']for a in attempts if not a['usage_known']),'reused_calls':sum(r['reused']for r in calls),'reused_tokens':sum(r['total_tokens']for r in calls if r['reused'])}
 save('summary.json',statsall);print(json.dumps({k:statsall[k]for k in ['baseline','generation_signals','physical_new_known_tokens','actual_physical_new_http_attempts']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
