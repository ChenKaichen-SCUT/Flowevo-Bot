from common import *
from generate import request_for
import collections,subprocess,importlib.metadata

def main():
 cfg={'model':'deepseek-flash','endpoint':'https://api.deepseek.com/chat/completions','system_prompt':'You are an expert programmer and mathematician.','max_tokens':16384,'gold_feedback':False,'gold_reflection':False,'skill_injection':False,'api_workers':64,'local_workers':12,'max_http_attempts':1500,'max_total_tokens':10000000,'max_attempts_per_job':2,'schedule_seed':20261010,'pass8_gate':{'additional_mathematically_verified_tasks_min':3,'subjects_with_recovery_min':2,'scope':'All 119 validation tasks; gate based on held-out candidate results only, never influences candidate content or per-task retries.'},'pricing_forecast':{'input_uncached_usd_per_million':0.3,'output_usd_per_million':1.2,'method':'Conservative documented peak uncached estimate, not invoice; cache and off-peak discounts not assumed.'},'thinking':'Default enabled; parameter omitted','reasoning_effort':'Default high; parameter omitted','temperature_sent':0,'temperature_effective':'Ignored in thinking mode according to official docs','seed_sent':None,'seed_effective':'Unsupported; independent requests, hidden provider randomness/version not pinned'}
 if (OUT/'config.json').exists():assert read(OUT/'config.json')==cfg
 else:save('config.json',cfg)
 manifest=read(OUT/'dataset_manifest.json');pub={r['task_id']:r for r in jl(OUT/'data/public_prompts.jsonl')}
 old=ROOT/'experiments/failure_mechanism_a1_a2_pilot';reuse=[]
 for r in jl(old/'api_calls.jsonl'):
  if r['stage']!='b2'or r['task_id']not in pub:continue
  req=request_for(pub[r['task_id']],cfg)
  assert r['request']==req and r['response_hash']==digest(r['response'])
  source=old/'raw'/f"{r['job_id']}.json";assert read(source)['response_hash']==r['response_hash']
  job=r['task_id']+'__c1';target=OUT/'raw'/f'{job}.json'
  reused={**r,'job_id':job,'candidate':1,'reused':True,'source_job_id':r['job_id'],'source_path':str(source.relative_to(ROOT)),'source_file_sha256':sha(source),'new_api_calls':0,'comparability':'Prior unconditional direct 16384 arm, exact same request, no correctness-based selection. Other adaptive retries excluded.'}
  if target.exists():assert read(target)==reused
  else:save(target,reused)
  reuse.append({'job_id':job,'source_path':str(source.relative_to(ROOT)),'source_sha256':sha(source),'response_hash':r['response_hash'],'tokens_avoided':r['total_tokens']})
 save('evidence/reused_outputs.json',reuse)
 forecast=[]
 for stage,n in [('validation_baseline',119),('validation_pass4_extra',357),('test_baseline',486),('validation_pass8_optional_extra',476)]:
  reuse_count=sum(next(x['split']for x in manifest['tasks']if x['task_id']==r['job_id'].split('__')[0])==('validation'if stage.startswith('validation')else 'test')for r in reuse)if stage.endswith('baseline')else 0
  nc=n-reuse_count;inp=300*nc;out=4000*nc
  forecast.append({'stage':stage,'requested_outputs':n,'reused_outputs':reuse_count,'new_calls_forecast':nc,'assumed_input_per_call':300,'assumed_output_per_call':4000,'forecast_tokens':inp+out,'forecast_peak_uncached_usd':round(inp*.3e-6+out*1.2e-6,5),'optional':stage.startswith('validation_pass8'),'upper_output_tokens':nc*16384})
 save('evidence/pre_run_budget_forecast.json',{'created_at':now(),'stages':forecast,'base_plus_pass4_new_calls':sum(x['new_calls_forecast']for x in forecast if not x['optional']),'base_plus_pass4_forecast_tokens':sum(x['forecast_tokens']for x in forecast if not x['optional']),'base_plus_pass4_forecast_peak_usd':sum(x['forecast_peak_uncached_usd']for x in forecast if not x['optional']),'safety_caps':{'http_attempts':1500,'total_tokens_including_unknown_upper_bounds':10000000},'optional_aflow':'No automatic calls; assess only after validation. Full MCTS forbidden.','automatic_failure_recovery':'Only transport failure, at most 2 attempts per public job; failure upper bound charged against safety cap.'})
 v3=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')
 for p,h in v3['source_files'].items():assert sha(ROOT/p)==h,p
 files=[OUT/'config.json',OUT/'dataset_manifest.json',OUT/'data/public_tasks.jsonl',OUT/'data/public_prompts.jsonl',OUT/'data/offline_labels.jsonl',OUT/'code/common.py',OUT/'code/generate.py',OUT/'code/preflight.py',ROOT/'experiments/math500_scoring_and_budget_v2/code/completion.py']
 freeze={'at':now(),'reference_commit':REF,'files':{str(p.relative_to(ROOT)):sha(p)for p in files}|v3['source_files'],'evaluator_source_sha256':v3['source_tree_sha256'],'evaluator_config_hash':v3['config_hash'],'no_paid_calls_before_freeze':not list((OUT/'attempts').glob('*.json')),'dependencies':{k:importlib.metadata.version(k)for k in ['requests','sympy','math-verify','rapidfuzz']}}
 if (OUT/'evidence/pre_api_freeze.json').exists():
  for p,h in read(OUT/'evidence/pre_api_freeze.json')['files'].items():assert sha(ROOT/p)==h
 else:save('evidence/pre_api_freeze.json',freeze)
 print(json.dumps({'reused':len(reuse),'avoided_tokens':sum(x['tokens_avoided']for x in reuse),'forecast':read(OUT/'evidence/pre_run_budget_forecast.json')},ensure_ascii=False))
if __name__=='__main__':main()
