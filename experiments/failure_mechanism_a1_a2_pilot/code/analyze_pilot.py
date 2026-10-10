"""Offline-only grading/paired costs; impossible to enter before full generation seal."""
from common import *
import csv,collections,math

def write_csv(name,rows):
 if not rows:return
 with (OUT/name).open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 seal=read(OUT/'checkpoints/ALL_GENERATION_SEALED.json');assert seal['api_calls_sha256']==sha(OUT/'api_calls.jsonl');assert seal['selected_sha256']==sha(OUT/'selected_responses.jsonl');assert seal['controller_sha256']==sha(OUT/'controller_decisions.jsonl')
 frozen=read(OUT/'evidence/pre_api_freeze.json')
 for p,h in frozen['files'].items():assert sha(ROOT/p)==h,p
 if not (OUT/'evidence/offline_grading_barrier.json').exists():save('evidence/offline_grading_barrier.json',{'at':now(),'generation_seal_verified':True,'generation_seal_sha256':sha(OUT/'checkpoints/ALL_GENERATION_SEALED.json'),'no_more_generation':True})
 # First label access occurs only after all base, retry, and intervention requests are sealed.
 labels={r['task_id']:r['reference_raw'] for r in jl(OUT/'data/offline_labels.jsonl')};tasks={r['task_id']:r for r in jl(OUT/'data/public_tasks.jsonl')}
 failed=jl(OUT/'evidence/infrastructure_attempts.jsonl') if (OUT/'evidence/infrastructure_attempts.jsonl').exists() else []
 calls=jl(OUT/'api_calls.jsonl');cmap={r['job_id']:r for r in calls};selected=jl(OUT/'selected_responses.jsonl');decisions={r['task_id']:r for r in jl(OUT/'controller_decisions.jsonl')}
 from math_evaluation.engine import MathEvaluatorV3
 from math_evaluation.models import EvaluatorConfig
 v3=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json');cfg=EvaluatorConfig(**v3['config']);assert cfg.hash()==v3['config_hash']
 scorepath=OUT/'pilot_v3_results.jsonl'
 if scorepath.exists():scores=jl(scorepath);assert {r['source_job_id'] for r in scores}==set(cmap)
 else:
  records=[{'record_id':r['job_id'],'task_id':r['task_id'],'branch':r['stage'],'subject':tasks[r['task_id']]['subject'],'level':tasks[r['task_id']]['level'],'question':tasks[r['task_id']]['problem'],'prediction_raw':r['response']['choices'][0]['message'].get('content') or '', 'reference_raw':labels[r['task_id']],'finish_reason':r['finish_reason'],'source_job_id':r['job_id'],'source_path':'raw/'+r['job_id']+'.json','request_hash':r['request_hash'],'response_hash':r['response_hash'],'submission_sealed':True} for r in calls]
  scores=MathEvaluatorV3(cfg).evaluate_batch(records);lines(scorepath,scores)
 smap={r['source_job_id']:r for r in scores};rows=[]
 for x in selected:
  tid=x['task_id'];r=cmap[x['final_job_id']];t=tasks[tid];d=decisions[tid];s=smap[r['job_id']];attempts=[cmap[j]for j in x['all_job_ids']];failed_attempts=[f for f in failed if f['job_id'] in x['all_job_ids']];unknown_bound=sum(f['conservative_token_upper_bound']for f in failed_attempts)
  rows.append({**x,'subject':t['subject'],'level':t['level'],'model':r['model'],'model_version':r['model_version'],'reasoning_effort':r['reasoning_effort'],'requested_max_tokens':r['max_tokens'],'finish_reason':r['finish_reason'],'reasoning_tokens':sum(a['reasoning_tokens'] for a in attempts) if all(isinstance(a['reasoning_tokens'],int)for a in attempts) else 'unavailable','final_content_tokens':sum(a['final_content_tokens']for a in attempts) if all(isinstance(a['final_content_tokens'],int)for a in attempts) else 'unavailable','total_input_tokens':sum(a['input_tokens']for a in attempts),'total_output_tokens':sum(a['output_tokens']for a in attempts),'api_call_count':len(attempts)+len(failed_attempts),'completed_api_call_count':len(attempts),'usage_unavailable_attempts':len(failed_attempts),'all_attempt_tokens_upper_bound':x['all_attempt_tokens']+unknown_bound,'token_usage_is_exact':not failed_attempts,'candidate_detected':bool(d['a1']['events']),'candidate_detection_evidence':d['a1']['events'],'finalization_triggered':x['method']=='B2+a1' and d['a1']['trigger'],'goal_spec':d['a2']['goal_spec'],'goal_mismatch_detected':d['a2']['high_confidence_mismatch'],'goal_repair_triggered':x['method']=='B2+a2' and d['a2']['trigger'],'final_answer':s['prediction_extracted'],'answer_complete':not r['completion']['retry_required'],'offline_correct':True if s['status']=='correct' else False if s['status'] in ('incorrect','incomplete','prediction_incomplete','prediction_missing') else None,'evaluator_status':s['status'],'evaluator_reason':s['reason'],'source_response_hash':r['response_hash'],'grading_after_all_generation':True})
 lines('task_results.jsonl',rows)
 methods=['B0','B1','B2','B2+a1','B2+a2','B2+generic'];stats={}
 for m in methods:
  rs=[r for r in rows if r['method']==m];stats[m]={'n':len(rs),'correct':sum(r['offline_correct'] is True for r in rs),'complete':sum(r['answer_complete']for r in rs),'unknown':sum(r['offline_correct']is None for r in rs),'incomplete':sum(not r['answer_complete']for r in rs),'status_counts':dict(collections.Counter(r['evaluator_status']for r in rs)),'input_tokens':sum(r['total_input_tokens']for r in rs),'output_tokens':sum(r['total_output_tokens']for r in rs),'total_tokens':sum(r['all_attempt_tokens']for r in rs),'calls':sum(r['api_call_count']for r in rs),'completed_calls':sum(r['completed_api_call_count']for r in rs),'usage_unavailable_attempts':sum(r['usage_unavailable_attempts']for r in rs),'total_tokens_upper_bound':sum(r['all_attempt_tokens_upper_bound']for r in rs),'reasoning_tokens':sum(r['reasoning_tokens']for r in rs) if all(isinstance(r['reasoning_tokens'],int)for r in rs)else 'unavailable','final_content_tokens':sum(r['final_content_tokens']for r in rs) if all(isinstance(r['final_content_tokens'],int)for r in rs)else 'unavailable'}
  stats[m]['accuracy']=stats[m]['correct']/len(rs);stats[m]['completion_rate']=stats[m]['complete']/len(rs)
  stats[m]['estimated_peak_usd_uncached']=round(stats[m]['input_tokens']*.3e-6+stats[m]['output_tokens']*1.2e-6,6)
 pairs=[];paired={};rmap={(r['task_id'],r['method']):r for r in rows}
 for left,right in [('B2','B0'),('B2','B1'),('B2+a1','B2'),('B2+a2','B2'),('B2+generic','B2'),('B2+a1','B2+generic'),('B2+a2','B2+generic')]:
  gains=[];losses=[];unk=0
  for tid in tasks:
   a,b=rmap[tid,left],rmap[tid,right];av=a['offline_correct']is True;bv=b['offline_correct']is True
   if av and not bv:gains.append(tid)
   if bv and not av:losses.append(tid)
   unk+=int(a['offline_correct']is None or b['offline_correct']is None)
   pairs.append({'task_id':tid,'left_method':left,'right_method':right,'left_status':a['evaluator_status'],'right_status':b['evaluator_status'],'left_confirmed_correct':av,'right_confirmed_correct':bv,'net_confirmed_correct':int(av)-int(bv),'left_tokens':a['all_attempt_tokens'],'right_tokens':b['all_attempt_tokens'],'token_difference':a['all_attempt_tokens']-b['all_attempt_tokens'],'left_calls':a['api_call_count'],'right_calls':b['api_call_count'],'unknown_in_pair':a['offline_correct']is None or b['offline_correct']is None})
  k=len(gains)+len(losses);p=min(1,2*sum(math.comb(k,i) for i in range(min(len(gains),len(losses))+1))/2**k) if k else 1
  paired[left+' vs '+right]={'gains':len(gains),'losses':len(losses),'net':len(gains)-len(losses),'gained_tasks':gains,'lost_tasks':losses,'unknown_pairs':unk,'exploratory_exact_sign_p':p,'tokens_difference':stats[left]['total_tokens']-stats[right]['total_tokens'],'calls_difference':stats[left]['calls']-stats[right]['calls']}
 write_csv('task_pairwise.csv',pairs);write_csv('cost_breakdown.csv',[{'method':m,**{k:v for k,v in stats[m].items() if k!='status_counts'}} for m in methods])
 events=[]
 for tid,d in decisions.items():
  call=cmap[tid+'__b2'];ev=read(OUT/call['stream_evidence_path'])
  for e in d['a1']['events']:
   reached=next((v['seconds']for v in ev.get('events',[]) if v['reasoning_chars']>=e['end']),None)
   events.append({'task_id':tid,'candidate':e,'first_available_seconds':reached,'trigger_decided_after_completion':True,'interrupted_generation':False})
 lines('pilot_stream_candidate_timing.jsonl',events)
 incomplete=[s for s in scores if s['status']!='correct'];lines('pilot_cases_to_review.jsonl',incomplete)
 limits={'actual_unique_calls':len(calls),'total_HTTP_attempts':len(calls)+len(failed),'unknown_usage_attempts':len(failed),'unknown_usage_token_upper_bound':sum(f['conservative_token_upper_bound']for f in failed),'safety_budget_upper_bound_tokens':sum(r['total_tokens']for r in calls)+sum(f['conservative_token_upper_bound']for f in failed),'actual_unique_tokens':sum(r['total_tokens']for r in calls),'peak_api_concurrency':seal['peak_api_concurrency'],'local_workers':12,'http_attempts':seal['http_attempts'],'reasoning_detail_available_calls':sum(isinstance(r['reasoning_tokens'],int)for r in calls),'streamed_calls':len(calls),'model_versions':dict(collections.Counter(r['model_version']for r in calls)),'cost_method':'USD upper estimate at documented peak uncached rates, not provider bill; cache/off-peak discounts not asserted.'}
 control={}
 for key in ('a1','a2','generic'):
  branch='B2+'+key;delta=paired[branch+' vs B2'];extra=[r for r in calls if r['stage']==key]
  control[key]={'triggered_tasks':len(extra),'new_confirmed_correct':delta['gains'],'harmed_confirmed_correct':delta['losses'],'net_new_correct':delta['net'],'extra_calls':len(extra)+sum(f['stage']==key for f in failed),'extra_completed_calls':len(extra),'extra_tokens':sum(r['total_tokens']for r in extra),'extra_tokens_unknown_upper_bound':sum(f['conservative_token_upper_bound']for f in failed if f['stage']==key),'early_terminations':0,'correct_early_finalizations':0,'wrong_early_finalizations':0,'would_have_been_correct_but_interrupted':0,'candidate_events':sum(len(d['a1']['events'])for d in decisions.values()) if key=='a1' else None}
 summary={'at':now(),'metrics':stats,'paired':paired,'controls':control,'physical_experiment':limits,'unknown_is_not_a_math_error':True,'no_score_feedback':True,'candidate_detection_tasks':sum(bool(d['a1']['events'])for d in decisions.values()),'candidate_detected_before_response_end':sum(e['first_available_seconds'] is not None for e in events),'generation_seal_sha256':sha(OUT/'checkpoints/ALL_GENERATION_SEALED.json'),'scoring_output_sha256':sha(scorepath),'scoring_reused_on_resume':True}
 save('pilot_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
