"""Explicit user-authorized repair of incomplete transport only, before any grading.

The frozen runner intentionally stops on ambiguous transport failure. This separate
operator recovery retains the unknown attempt and reserves its full token bound.
No completed response or mathematical truncation is rerun, no algorithm is changed.
"""
from common import *
from run_pilot import Runner
import shutil

def main():
 if (OUT/'checkpoints/ALL_GENERATION_SEALED.json').exists():print('Already sealed; no API call');return
 assert not (OUT/'pilot_v3_results.jsonl').exists(),'No retry after scoring'
 pending=list((OUT/'raw').glob('*.pending.json'));path=OUT/'evidence/infrastructure_attempts.jsonl'
 if not path.exists():
  assert len(pending)==1,[p.name for p in pending]
  p=pending[0];d=read(p);job=d['job_id'];err=read(OUT/'raw'/f'{job}.error.json');assert err['error_type']=='SSLError' and err['billing_unknown']
  assert not (OUT/'raw'/f'{job}.json').exists()
  archive=OUT/'evidence/interrupted_transport';archive.mkdir(exist_ok=True)
  row={'attempt_id':job+'__interrupted_transport_1','task_id':d['job_id'].split('__')[0],'job_id':job,'stage':'generic','request':d['request'],'request_hash':digest(d['request']),'started_at':d['started_at'],'failure_at':err['at'],'error_type':err['error_type'],'actual_tokens':'unavailable','conservative_token_upper_bound':d['reserved_tokens'],'completed_response_available':False,'retry_reason':'User explicitly authorized rerunning partially delivered work; one transport-only retry before grading. All valid completed responses reused.','authorized_at':now()}
  lines(path,[row]);shutil.move(str(p),str(archive/p.name));shutil.move(str(OUT/'raw'/f'{job}.error.json'),str(archive/f'{job}.error.json'))
  save('evidence/transport_recovery_plan.json',{'at':now(),'original_run_stopped':read(OUT/'checkpoints/stopped.json'),'one_time_retry_attempts_max':1,'completed_responses_rerun':0,'labels_accessed':False,'frozen_algorithm_prompt_budget_unchanged':True,'failed_request_token_bound_charged_to_safety_budget':d['reserved_tokens'],'no_automatic_retry_policy_changed':True})
 failed=jl(path);assert len(failed)==1
 if list((OUT/'raw').glob('*.pending.json')):raise RuntimeError('Replacement also ambiguous; do not repeat')
 runner=Runner(read(OUT/'config.json'));unknown_bound=sum(r['conservative_token_upper_bound']for r in failed)
 runner.actual+=unknown_bound;runner.calls+=len(failed);runner.http_attempts+=len(failed)
 assert runner.actual<1500000 and runner.calls<200
 tasks={e['task_id']:e for e in jl(OUT/'data/public_prompts.jsonl')}
 for f in failed:
  e=tasks[f['task_id']];prompt=f['request']['messages'][-1]['content'];r=runner.call(e,'generic',4096,prompt);assert r['request_hash']==f['request_hash']
 # All previous successful requests remain byte-for-byte untouched, including
 # requests marked BudgetStop after an unrelated concurrent request failed.
 calls=[read(p)for p in(OUT/'raw').glob('*.json')if not p.name.endswith(('.stream.json','.error.json','.pending.json'))]
 by={(r['task_id'],r['stage']):r for r in calls};selected=[]
 for tid in tasks:
  assert (tid,'b0')in by and(tid,'b2')in by and(tid,'generic')in by
  b1=[by[tid,'b0']]+[by[tid,s]for s in('b1_8192','b1_16384')if(tid,s)in by]
  branches={'B0':[by[tid,'b0']],'B1':b1,'B2':[by[tid,'b2']]}
  for k in('a1','a2','generic'):branches['B2+'+k]=[by[tid,'b2']]+([by[tid,k]]if(tid,k)in by else[])
  for method,rs in branches.items():selected.append({'task_id':tid,'method':method,'final_job_id':rs[-1]['job_id'],'all_job_ids':[r['job_id']for r in rs],'all_attempt_tokens':sum(r['total_tokens']for r in rs)})
 lines('api_calls.jsonl',sorted(calls,key=lambda r:r['job_id']));lines('selected_responses.jsonl',selected)
 # Derive peak in-flight requests from durable timestamps including the failure.
 timeline=[]
 for r in calls:timeline.extend([(r['started_at'],1),(r['finished_at'],-1)])
 for r in failed:timeline.extend([(r['started_at'],1),(r['failure_at'],-1)])
 active=peak=0
 for _,delta in sorted(timeline):active+=delta;peak=max(peak,active)
 assert peak<=64
 measured=sum(r['total_tokens']for r in calls)
 save('checkpoints/ALL_GENERATION_SEALED.json',{'sealed_at':now(),'api_calls_sha256':sha(OUT/'api_calls.jsonl'),'selected_sha256':sha(OUT/'selected_responses.jsonl'),'controller_sha256':sha(OUT/'controller_decisions.jsonl'),'new_normal_calls':len(calls),'http_attempts':len(calls)+len(failed),'actual_tokens':measured,'actual_tokens_scope':'sum of provider-returned usage; one transport-failed request has unavailable usage','unavailable_usage_attempts':len(failed),'unavailable_usage_token_upper_bound':unknown_bound,'safety_budget_upper_bound_tokens':measured+unknown_bound,'peak_api_concurrency':peak,'offline_scoring_not_yet_started':True,'no_stream_cancellations':True,'no_gold_or_skill':True,'partial_delivery_repaired_before_scoring':True})
 print({'completed_calls':len(calls),'HTTP_attempts':len(calls)+len(failed),'measured_tokens':measured,'unknown_usage_max':unknown_bound,'peak':peak},flush=True)
if __name__=='__main__':main()
