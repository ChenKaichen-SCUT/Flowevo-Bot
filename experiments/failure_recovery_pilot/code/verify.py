"""Read-only artifact integrity and leakage/budget invariants; never API calls."""
from common import *
from campaign import check_freeze
from flowevo_recovery.public import Task,State,base_prompt,recovery_prompt
from flowevo_recovery.controller import METHODS,select
from flowevo_bot.v2.evaluator import assert_sealed
import collections

def main():
 freeze=check_freeze();config=read(OUT/'config.json');split=read(OUT/'dataset_split_manifest.json');labels=read(OUT/'data/offline_labels.json')
 protected=read(OUT/'snapshots/protected_history.json');assert all(sha(ROOT/r['path'])==r['sha256'] for r in protected)
 assert sha(ROOT/'指引.txt')==sha(OUT/'snapshots/指引.txt')
 assert all(sha(OUT/'data'/p)==h for p,h in split['files'].items())
 assert not set(split['train_math_source_ids']+split['train_code_ids'])&set(split['confirmation_ids'])
 first={t['task_id']:Task.model_validate(t) for n in ['train_code_tasks.jsonl','confirmation_tasks.jsonl'] for t in lines(OUT/'data'/n)}
 source={r['state']['task']['task_id']:r for n in ['counterfactual_sources.jsonl','confirmation_public_states.jsonl'] for r in lines(OUT/'data'/n)}
 calls=[read(p) for p in (OUT/'raw_calls').glob('*.json')]
 assert not list((OUT/'raw_calls').glob('*.pending.json')) and not list((OUT/'raw_calls').glob('*.error.json'))
 assert len(calls)<=config['max_calls'] and sum(r['total_tokens'] for r in calls)<=config['max_tokens']
 assert len({r['job_id'] for r in calls})==len(calls)
 for r in calls:
  assert not r['simulated'] and r['http_attempts']==1 and not r['infrastructure_retries'] and not r['correctness_retries']
  assert r['input_tokens']+r['output_tokens']==r['total_tokens']==r['response']['usage']['total_tokens']
  assert r['total_tokens']<=r['reserved_tokens']
  assert digest(r['request'])==r['request_hash'] and digest(r['response'])==r['response_hash']
  assert r['request']['temperature']==config['temperature'] and r['request']['max_tokens']==config[r['domain']+'_max_tokens']
  if r['action']=='initial':expected=base_prompt(first[r['task_id']])
  else:
   s=source[r['task_id']];expected=recovery_prompt(State.model_validate(s['state']),r['action'],s['features'])
  assert r['request']['messages'][-1]['content']==expected
 for path in (OUT/'evidence').glob('*.sealed.jsonl'):
  for r in lines(path):assert_sealed(r)
 decisions=lines(OUT/'controller_decisions.jsonl');results=lines(OUT/'task_results.jsonl');memory=lines(OUT/'recovery_experiences.jsonl');shuffled=lines(OUT/'data/shuffled_experiences.jsonl')
 assert len(results)==len(split['confirmation_ids'])*len(METHODS)
 assert all(r['complete'] and r['llm_calls']<=2 for r in results)
 assert all(set(r)<=set(['experience_id','source_id','domain','feature_key','action','recovered','additional_tokens','source_state_hash','intervention_call_id','counterfactual_verified']) for r in memory)
 assert not {r['source_id'] for r in memory}&set(split['confirmation_ids'])
 for d in decisions:
  expected=select(d['method'],d['public_features'],shuffled if d['method']=='C_shuffled' else memory)
  assert expected['action']==d['action'] and expected['memory_sources']==d['memory_sources']
 bycalls={r['call_id']:r for r in calls};consumption=[]
 for r in results:
  costs=[bycalls[r['initial_call_id']]]+([bycalls[r['recovery_call_id']]] if r['recovery_call_id'] else [])
  for key in ['input_tokens','output_tokens','total_tokens']:assert sum(c[key] for c in costs)==r[key]
 events=[]
 for r in calls:events.extend([(r['started_unix'],1),(r['started_unix']+r['seconds'],-1)])
 active=peak=0
 for t,d in sorted(events,key=lambda x:(x[0],x[1])):active+=d;peak=max(peak,active)
 assert peak<=config['api_workers']<=64
 report={'verified_at':now(),'frozen_files':len(freeze['files']),'freeze_hash':freeze['aggregate_hash'],'protected_historical_files':len(protected),'physical_calls':len(calls),'physical_tokens':sum(r['total_tokens'] for r in calls),'peak_api_concurrency_from_timestamps':peak,'local_worker_cap':12,'sealed_files':len(list((OUT/'evidence').glob('*.sealed.jsonl'))),'all_method_rows_complete':True,'gold_free_prompt_reconstruction':True,'external_memory_sources':len({r['source_id'] for r in memory}),'remote_model_names':dict(collections.Counter(r['response'].get('model') for r in calls)),'budget_ok':True,'passed':True}
 write(OUT/'evidence/integrity.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
