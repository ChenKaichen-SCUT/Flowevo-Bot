"""Offline evidence audit; no credentials and no API calls."""
from common import *
from completion import detect
from run_experiment import request_for,require_public
import collections,csv,datetime

def audit():
 cfg=read(OUT/'config.json');freeze=read(OUT/'evidence/pre_api_freeze.json');seal=read(OUT/'checkpoints/ALL_GENERATION_SEALED.json')
 for x in freeze['files']:assert sha(ROOT/x['path'])==x['sha256'],x['path']
 for file,key in [('api_calls.jsonl','api_calls_sha256'),('first_pass_results.jsonl','first_pass_sha256'),('adaptive_results.jsonl','adaptive_sha256'),('same_budget_retry.jsonl','control_sha256')]:assert sha(OUT/file)==seal[key]
 dataset=read(OUT/'dataset_manifest.json')
 assert sha(OUT/'data/offline_labels.jsonl')==dataset['offline_labels_sha256']
 for split,value in dataset['source_hashes'].items():assert sha(ROOT/'FlowEvo/data/datasets/math'/f'{split}.jsonl')==value
 assert cfg['local_workers']<=12 and cfg['api_workers']<=64
 previous=read(OUT/'evidence/protected_previous_snapshot.json')
 changes=[x['path'] for x in previous['files'] if sha(ROOT/x['path'])!=x['sha256']]
 assert changes==['指引.txt'],changes
 tasks={x['task_id']:x for x in jl(OUT/'data/public_tasks.jsonl')};prompts={x['task_id']:x for x in read(OUT/'data/native_prompts.json')['prompts']}
 calls=jl(OUT/'api_calls.jsonl');jobs={x['job_id']:x for x in calls};by_stage=collections.defaultdict(dict)
 assert len(calls)==len(jobs)==577 and len({c['request_id'] for c in calls})==577
 events=[]
 for c in calls:
  p=prompts[c['task_id']];require_public(p)
  assert p['prompt']==f"Problem: {tasks[c['task_id']]['problem']}\n\nSolve step by step. End with: The answer is [your answer]."
  assert c['request']==request_for(p['prompt'],cfg,c['max_tokens'])
  assert c['request_hash']==digest(c['request']) and c['response_hash']==digest(c['response'])
  assert read(OUT/'raw'/f"{c['job_id']}.json")==c
  assert read(OUT/'raw'/f"{c['job_id']}.http1.txt")==c['response']
  assert read(OUT/'raw'/f"{c['job_id']}.attempts.json")==c['raw_attempts']
  assert c['completion']==detect(c['task_id'],c['response'],c['max_tokens'])
  assert not c['gold_exposed'] and not c['skill_injected'] and c['skill_retrieval_count']==0 and c['correctness_retries']==0
  assert c['api_status']==200 and c['http_attempts']==1 and c['infrastructure_retries']==0
  u=c['response']['usage'];assert c['input_tokens']==u['prompt_tokens'] and c['output_tokens']==u['completion_tokens'] and c['total_tokens']==u['total_tokens']==c['input_tokens']+c['output_tokens']
  assert c['output_tokens']<=c['max_tokens'] and c['total_tokens']<=c['reserved_tokens']
  assert freeze['frozen_at']<=c['started_at']<=c['finished_at']<=seal['sealed_at']
  by_stage[c['stage']][c['task_id']]=c;events.extend([(c['started_at'],1),(c['finished_at'],-1)])
 assert set(by_stage['base4096'])==set(tasks)
 inc={k for k,v in by_stage['base4096'].items() if v['retry_required']}
 assert set(by_stage['upgrade8192'])==set(by_stage['control4096'])==inc
 assert set(by_stage['upgrade16384'])=={k for k,v in by_stage['upgrade8192'].items() if v['retry_required']}
 adaptive=jl(OUT/'adaptive_results.jsonl');assert len(adaptive)==500
 for c in adaptive:
  tid=c['task_id'];expected=by_stage['upgrade16384'].get(tid) or by_stage['upgrade8192'].get(tid) or by_stage['base4096'][tid]
  assert c==expected
  for stage in ('base4096','upgrade8192','upgrade16384','control4096'):
   if tid in by_stage[stage]:assert by_stage[stage][tid]['request']['messages']==c['request']['messages']
 active=peak=0
 for _,change in sorted(events):active+=change;peak=max(peak,active)
 assert active==0 and peak<=64 and peak==seal['peak_api_concurrency']
 assert not list((OUT/'raw').glob('*.pending.json')) and not list((OUT/'raw').glob('*.error.json'))
 summary=read(OUT/'summary.json');assert sum(c['total_tokens'] for c in calls)==summary['actual_total_tokens']==978566<cfg['max_total_token_reservation']
 assert {x['method']:x['correct'] for x in summary['four_way']}=={'A':456,'B':449,'C':485,'D':476}
 assert read(OUT/'manual_audit_summary.json')['sensitivity_only']=={'base':467,'adaptive':496,'E':10,'upgrade8192':21}
 # Complete incorrect 8192 response must not receive a correctness-driven 16384 retry.
 error='math_test_number_theory_491';assert error in inc and not by_stage['upgrade8192'][error]['retry_required'] and error not in by_stage['upgrade16384']
 return {'status':'PASS','audited_at':now(),'unique_responses':len(calls),'actual_tokens':sum(c['total_tokens'] for c in calls),'observed_peak_api_concurrency':peak,'local_workers':cfg['local_workers'],'raw_http_and_ledger_identical':True,'freeze_and_generation_seals_unchanged':True,'gold_and_skill_context_absent_by_exact_prompt_reconstruction':True,'retry_sets_equal_completion_only_sets':True,'no_infrastructure_retries_or_ambiguous_calls':True,'protected_previous_file_count':len(previous['files']),'previous_changed_paths':changes,'note':'Only root guide changed by new user instruction; all historical code/results unchanged. This audit verifies request contents, not model pretraining contamination.'}
if __name__=='__main__':
 r=audit();save('evidence/final_integrity_audit.json',r);print(json.dumps(r,ensure_ascii=False,indent=2))
