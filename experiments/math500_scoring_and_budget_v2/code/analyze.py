"""All gold access is offline, after every branch is sealed; no API calls."""
from common import *
from evaluators import both
from paired_statistics import paired,distribution
import concurrent.futures as cf,csv,time,collections

def csvwrite(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r)) if rows else ['task_id']
 with (OUT/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def truth(x):return x is True

def estimate_cost(c):
 u=c['response']['usage'];hit=u.get('prompt_cache_hit_tokens');miss=u.get('prompt_cache_miss_tokens')
 if hit is None or miss is None:return {'usd_estimate':None,'reason':'cache usage unavailable','rate_regime':'unknown'}
 dt=__import__('datetime').datetime.fromisoformat(c['started_at']);weekend=dt.weekday()>=5
 regime='offpeak' if weekend else ('peak' if 1<=dt.hour<4 or 6<=dt.hour<10 else 'offpeak')
 rate=read(OUT/'evidence/pricing.json')['usd_per_million_tokens'][regime]
 return {'usd_estimate':(hit*rate['input_cache_hit']+miss*rate['input_cache_miss']+u['completion_tokens']*rate['output'])/1000000,'rate_regime':regime,'cache_hit_tokens':hit,'cache_miss_tokens':miss,'billing':'list-price estimate, not invoice'}

def main():
 seal=read(OUT/'checkpoints/ALL_GENERATION_SEALED.json')
 for name,key in [('api_calls.jsonl','api_calls_sha256'),('first_pass_results.jsonl','first_pass_sha256'),('adaptive_results.jsonl','adaptive_sha256'),('same_budget_retry.jsonl','control_sha256')]:assert sha(OUT/name)==seal[key]
 tasks=jl(OUT/'data/public_tasks.jsonl');labels={x['task_id']:x for x in jl(OUT/'data/offline_labels.jsonl')};tm={x['task_id']:x for x in tasks};calls=jl(OUT/'api_calls.jsonl')
 assert len(tasks)==500 and len({x['task_id'] for x in tasks})==500
 items=[]
 for c in calls:
  assert c['response_hash']==digest(c['response']);tid=c['task_id']
  items.append({'task_id':tid,'solution':c['response']['choices'][0]['message'].get('content') or '','question':tm[tid]['problem'],'gold_answer':labels[tid]['gold_answer'],'truncated':c['finish_reason']=='length'})
 start=time.perf_counter()
 with cf.ProcessPoolExecutor(max_workers=12) as pool:scores=list(pool.map(both,items))
 scoring_wall=time.perf_counter()-start
 sm={c['job_id']:s for c,s in zip(calls,scores)};base={x['task_id']:x for x in jl(OUT/'first_pass_results.jsonl')};adaptive={x['task_id']:x for x in jl(OUT/'adaptive_results.jsonl')};control={x['task_id']:x for x in jl(OUT/'same_budget_retry.jsonl')}
 costs={c['job_id']:estimate_cost(c) for c in calls}
 for version in ('legacy','fixed'):lines(version+'_scoring_results.jsonl',[{'task_id':c['task_id'],'job_id':c['job_id'],'stage':c['stage'],'scorer':version,'grade':s[version],'gold_answer':labels[c['task_id']]['gold_answer'],'raw_evidence':f"raw/{c['job_id']}.json",'response_hash':c['response_hash']} for c,s in zip(calls,scores)])
 rows=[];disagreements=[];failure_candidates=[];recovery=[]
 for task in tasks:
  tid=task['task_id'];b=base[tid];d=adaptive[tid];bs=sm[b['job_id']];ds=sm[d['job_id']]
  ac=[x for x in calls if x['task_id']==tid and x['stage']!='control4096'];allstages={x['stage'] for x in ac}
  row={'task_id':tid,'subject':task['subject'],'level':task['level'],'base_answer':bs['fixed']['answer'],'adaptive_answer':ds['fixed']['answer'],'base_legacy_correct':bs['legacy']['correct'],'base_fixed_correct':bs['fixed']['correct'],'adaptive_legacy_correct':ds['legacy']['correct'],'adaptive_fixed_correct':ds['fixed']['correct'],'base_complete':not b['retry_required'],'adaptive_complete':not d['retry_required'],'first_pass_truncated':b['finish_reason']=='length','retry_8192_used':'upgrade8192' in allstages,'retry_16384_used':'upgrade16384' in allstages,'base_input_tokens':b['input_tokens'],'base_output_tokens':b['output_tokens'],'base_total_tokens':b['total_tokens'],'adaptive_input_tokens':sum(x['input_tokens'] for x in ac),'adaptive_output_tokens':sum(x['output_tokens'] for x in ac),'adaptive_total_tokens':sum(x['total_tokens'] for x in ac),'adaptive_calls':len(ac),'scoring_fix_effect':int(truth(bs['fixed']['correct']))-int(truth(bs['legacy']['correct'])),'adaptive_budget_effect':int(truth(ds['fixed']['correct']))-int(truth(bs['fixed']['correct'])),'base_fixed_status':bs['fixed']['status'],'adaptive_fixed_status':ds['fixed']['status'],'base_source':f"raw/{b['job_id']}.json",'adaptive_source':f"raw/{d['job_id']}.json",'selected_budget':d['max_tokens'],'base_cost_usd_estimate':costs[b['job_id']]['usd_estimate'],'adaptive_cost_usd_estimate':sum(costs[x['job_id']]['usd_estimate'] for x in ac),'fixed_evaluator_sha256':sha(ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py'),'reference_commit':REF}
  rows.append(row)
  if b['retry_required']:
   stages={x['stage']:x for x in ac};rc={'task_id':tid,'subject':task['subject'],'level':task['level'],'base_finish_reason':b['finish_reason'],'base_completion_reason':b['retry_reason'],'base_fixed_correct':bs['fixed']['correct'],'adaptive_fixed_correct':ds['fixed']['correct'],'adaptive_complete':not d['retry_required'],'selected_budget':d['max_tokens'],'extra_tokens':row['adaptive_total_tokens']-b['total_tokens']}
   for stage in ('upgrade8192','upgrade16384','control4096'):
    x=control.get(tid) if stage=='control4096' else stages.get(stage)
    rc.update({stage+'_used':x is not None,stage+'_complete':not x['retry_required'] if x else None,stage+'_correct':sm[x['job_id']]['fixed']['correct'] if x else None,stage+'_total_tokens':x['total_tokens'] if x else None})
   recovery.append(rc)
  if ds['fixed']['correct'] is not True:
   category='still_truncated' if d['finish_reason']=='length' else 'parse_or_equivalence_unknown' if ds['fixed']['correct'] is None else 'complete_potential_math_error' if not d['retry_required'] else 'incomplete_or_uncertain'
   failure_candidates.append({'task_id':tid,'subject':task['subject'],'level':task['level'],'category_before_manual_review':category,'question':task['problem'],'solution':d['response']['choices'][0]['message'].get('content') or '','gold_answer':labels[tid]['gold_answer'],'reference_solution':labels[tid]['reference_solution'],'fixed_grade':ds['fixed'],'legacy_grade':ds['legacy'],'selected_budget':d['max_tokens'],'finish_reason':d['finish_reason'],'completion':d['completion'],'raw_evidence':row['adaptive_source'],'usage':d['response']['usage'],'mathematical_error_confirmed':False,'manual_review_required':True})
 for c,s,item in zip(calls,scores,items):
  if s['legacy']['correct']!=s['fixed']['correct']:
   disagreements.append({'task_id':c['task_id'],'job_id':c['job_id'],'stage':c['stage'],'question':item['question'],'solution':item['solution'],'legacy_answer':s['legacy']['answer'],'fixed_answer':s['fixed']['answer'],'gold_answer':item['gold_answer'],'legacy_correct':s['legacy']['correct'],'fixed_correct':s['fixed']['correct'],'fixed_status':s['fixed']['status'],'math_evidence':json.dumps(s['fixed'].get('evidence',{}),ensure_ascii=False),'raw_evidence':f"raw/{c['job_id']}.json",'manual_review_required':True,'ambiguous':'pending review'})
 csvwrite('four_way_task_comparison.csv',rows);csvwrite('scoring_disagreements.csv',disagreements);csvwrite('truncation_recovery.csv',recovery);lines('remaining_failures.jsonl',failure_candidates)
 summaries=[]
 for name,key,methodcalls in [('A','base_legacy_correct',list(base.values())),('B','base_fixed_correct',list(base.values())),('C','adaptive_legacy_correct',[x for x in calls if x['stage']!='control4096']),('D','adaptive_fixed_correct',[x for x in calls if x['stage']!='control4096'])]:
  correct=sum(truth(x[key]) for x in rows);token=sum(x['total_tokens'] for x in methodcalls)
  summaries.append({'method':name,'correct':correct,'count':500,'accuracy':correct/500,'unknown':sum(x[key] is None for x in rows),'api_calls':len(methodcalls),'input_tokens':sum(x['input_tokens'] for x in methodcalls),'output_tokens':sum(x['output_tokens'] for x in methodcalls),'total_tokens':token,'cost_usd_estimate':sum(costs[x['job_id']]['usd_estimate'] for x in methodcalls),'tokens_per_correct':token/correct if correct else None})
 save('four_way_summary.json',summaries)
 paired_bd=paired([truth(x['base_fixed_correct']) for x in rows],[truth(x['adaptive_fixed_correct']) for x in rows])
 ab=paired([truth(x['base_legacy_correct']) for x in rows],[truth(x['base_fixed_correct']) for x in rows],repetitions=20000)
 cd=paired([truth(x['adaptive_legacy_correct']) for x in rows],[truth(x['adaptive_fixed_correct']) for x in rows],repetitions=20000)
 e_high=paired([truth(x['control4096_correct']) for x in recovery],[truth(x['upgrade8192_correct']) for x in recovery])
 by_group=[]
 for field in ('subject','level'):
  for value in sorted({x[field] for x in rows}):
   rs=[x for x in rows if x[field]==value]
   by_group.append({'group_type':field,'group':value,'count':len(rs),**{k:sum(truth(x[v]) for x in rs) for k,v in [('A','base_legacy_correct'),('B','base_fixed_correct'),('C','adaptive_legacy_correct'),('D','adaptive_fixed_correct')]},'extra_tokens':sum(x['adaptive_total_tokens']-x['base_total_tokens'] for x in rs)})
 csvwrite('group_metrics.csv',by_group)
 stages=[]
 for stage in ('base4096','upgrade8192','upgrade16384','control4096'):
  cs=[x for x in calls if x['stage']==stage]
  stages.append({'stage':stage,'calls':len(cs),'complete':sum(not x['retry_required'] for x in cs),'correct_fixed':sum(truth(sm[x['job_id']]['fixed']['correct']) for x in cs),'unknown_fixed':sum(sm[x['job_id']]['fixed']['correct'] is None for x in cs),'truncated':sum(x['finish_reason']=='length' for x in cs),'missing_final':sum(not x['completion']['final_answer_present'] for x in cs),'complete_automatically_wrong':sum(not x['retry_required'] and sm[x['job_id']]['fixed']['correct'] is False for x in cs),'input_tokens':sum(x['input_tokens'] for x in cs),'output_tokens':sum(x['output_tokens'] for x in cs),'total_tokens':sum(x['total_tokens'] for x in cs),'usd_estimate':sum(costs[x['job_id']]['usd_estimate'] for x in cs)})
 csvwrite('stage_metrics.csv',stages)
 csvwrite('token_costs.csv',[{k:c[k] for k in ('task_id','job_id','stage','max_tokens','input_tokens','output_tokens','reasoning_tokens_if_available','total_tokens','http_attempts','infrastructure_retries','started_at','finished_at')}|costs[c['job_id']] for c in calls])
 summary={'four_way':summaries,'contributions':{'B_minus_A':summaries[1]['correct']-summaries[0]['correct'],'D_minus_B':summaries[3]['correct']-summaries[1]['correct'],'D_minus_A':summaries[3]['correct']-summaries[0]['correct'],'D_minus_C':summaries[3]['correct']-summaries[2]['correct']},'paired_B_vs_D':paired_bd,'paired_A_vs_B':ab,'paired_C_vs_D':cd,'paired_E_vs_8192':e_high,'stages':stages,'actual_unique_normal_calls':len(calls),'actual_http_attempts':sum(c['http_attempts'] for c in calls),'actual_input_tokens':sum(c['input_tokens'] for c in calls),'actual_output_tokens':sum(c['output_tokens'] for c in calls),'actual_total_tokens':sum(c['total_tokens'] for c in calls),'actual_cost_usd_estimate':sum(x['usd_estimate'] for x in costs.values()),'adaptive_extra_tokens':summaries[3]['total_tokens']-summaries[1]['total_tokens'],'adaptive_extra_cost_usd_estimate':summaries[3]['cost_usd_estimate']-summaries[1]['cost_usd_estimate'],'scoring_extra_api_tokens':0,'scoring_local_wall_seconds':scoring_wall,'legacy_sum_worker_seconds':sum(s['legacy']['local_seconds'] for s in scores),'fixed_sum_worker_seconds':sum(s['fixed']['local_seconds'] for s in scores),'scoring_unique_responses':len(scores),'token_increment_distribution_all500':distribution([x['adaptive_total_tokens']-x['base_total_tokens'] for x in rows]),'token_increment_distribution_upgraded':distribution([x['extra_tokens'] for x in recovery]),'group_metrics':by_group,'failure_candidates':len(failure_candidates),'disagreement_responses':len(disagreements),'scoring_performed_after_generation_seal':True,'generation_seal_sha256':sha(OUT/'checkpoints/ALL_GENERATION_SEALED.json')}
 save('summary.json',summary)
 print(json.dumps({k:summary[k] for k in ('four_way','contributions','stages','actual_unique_normal_calls','actual_total_tokens','failure_candidates','disagreement_responses','paired_B_vs_D','paired_E_vs_8192')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
