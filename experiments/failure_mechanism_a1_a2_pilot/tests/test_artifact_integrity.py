import sys,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(OUT/'code'))
from common import read,jl,sha,digest

def test_all_generation_sealed_and_budget_respected():
 s=read(OUT/'checkpoints/ALL_GENERATION_SEALED.json');calls=jl(OUT/'api_calls.jsonl')
 assert s['api_calls_sha256']==sha(OUT/'api_calls.jsonl');assert s['actual_tokens']==sum(r['total_tokens']for r in calls)<=1500000;assert s['new_normal_calls']==len(calls)<=200;assert s['peak_api_concurrency']<=64
 assert not list((OUT/'raw').glob('*.pending.json'));assert s['http_attempts']<=200;assert s['safety_budget_upper_bound_tokens']<=1500000
 assert s['unavailable_usage_attempts']==1 and s['unavailable_usage_token_upper_bound']==5412

def test_frozen_generation_sources_unchanged():
 for p,h in read(OUT/'evidence/pre_api_freeze.json')['files'].items():assert sha(ROOT/p)==h,p

def test_history_unchanged():assert read(OUT/'evidence/historical_hash_verification.json')['unexpected_changes']==[]

def test_same_v3_configuration_and_responses():
 cfg=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json');calls={r['job_id']:r for r in jl(OUT/'api_calls.jsonl')}
 for r in jl(OUT/'pilot_v3_results.jsonl'):
  assert r['config_hash']==cfg['config_hash'];assert r['response_hash']==calls[r['source_job_id']]['response_hash']
 for p,h in cfg['source_files'].items():assert sha(ROOT/p)==h

def test_method_coverage_and_shared_initial_requests():
 rows=jl(OUT/'task_results.jsonl');assert len(rows)==240
 assert collections.Counter(r['method']for r in rows)=={k:40 for k in ['B0','B1','B2','B2+a1','B2+a2','B2+generic']}
 for r in rows:
  stage='b0' if r['method']in('B0','B1')else'b2';assert r['all_job_ids'][0]==r['task_id']+'__'+stage

def test_costs_reconcile():
 calls={r['job_id']:r for r in jl(OUT/'api_calls.jsonl')}
 for r in jl(OUT/'task_results.jsonl'):
  xs=[calls[j]for j in r['all_job_ids']];assert r['all_attempt_tokens']==sum(x['total_tokens']for x in xs);assert r['completed_api_call_count']==len(xs);assert r['api_call_count']==len(xs)+r['usage_unavailable_attempts']
  assert r['total_input_tokens']+r['total_output_tokens']==r['all_attempt_tokens']
 for r in calls.values():assert r['response_hash']==digest(r['response']) and r['request_hash']==digest(r['request'])

def test_no_gold_skill_or_correctness_retry():
 labels=jl(OUT/'data/offline_labels.jsonl');refs=[r['reference_raw']for r in labels]
 for r in jl(OUT/'api_calls.jsonl'):
  assert not r['gold_exposed'] and not r['skill_injected'] and r['correctness_retries']==0
  prompt=r['request']['messages'][-1]['content'];assert not any(x and len(x)>30 and x in prompt for x in refs)
  assert r['request']['stream'] is True and 'tools' not in r['request']

def test_decisions_precede_offline_grading():
 barrier=read(OUT/'evidence/offline_grading_barrier.json')['at'];seal=read(OUT/'checkpoints/ALL_GENERATION_SEALED.json')['sealed_at'];assert seal<barrier
 for r in jl(OUT/'controller_decisions.jsonl'):assert r['decided_at']<seal and not r['reference_access']
 for r in jl(OUT/'api_calls.jsonl'):assert r['finished_at']<seal

def test_stratification_and_disjoint_ids():
 new={r['task_id']for r in jl(OUT/'data/public_tasks.jsonl')};old={r['task_id']for r in jl(OUT/'historical_records.jsonl')};assert len(new)==40 and new.isdisjoint(old)
 rows=jl(OUT/'data/public_tasks.jsonl');assert len({r['subject']for r in rows})==7;assert sum(r['level']in('Level 4','Level 5')for r in rows)==26

def test_no_hidden_state_resume_or_interrupt_claim():
 for r in jl(OUT/'api_calls.jsonl'):
  evidence=read(OUT/r['stream_evidence_path']);assert evidence['observed_during_generation'] and not evidence['cancelled'];assert r['request']['messages'][0]['role']=='system'

def test_atlas_denominators_and_unique_taxonomy():
 rows=jl(OUT/'historical_records.jsonl');s=read(OUT/'evidence/atlas_summary_verified.json');assert len(rows)==1195;assert len({r['task_id']for r in rows})==1031
 for r in rows:assert len(r['labels'])==len(set(r['labels']))
 for x in s['taxonomy']:
  rs=[r for r in rows if x['code']in r['labels']];assert x['records']==len(rs);assert x['tasks']==len({r['task_id']for r in rs});assert sum(x['subjects'].values())==x['tasks']

def test_replay_uses_existing_results_only():
 from run_pilot import Runner
 def fail(req):raise AssertionError('Completed experiment must not make a new request')
 runner=Runner(read(OUT/'config.json'),transport=fail);e=jl(OUT/'data/public_prompts.jsonl')[0]
 before=runner.actual;r=runner.call(e,'b0',4096);assert runner.actual==before;assert r['job_id']==e['task_id']+'__b0'
