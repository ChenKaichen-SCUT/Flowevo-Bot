from common import *
import statistics,collections

def main():
 if (OUT/'evidence/pre_api_freeze.json').exists():print('Existing pre-API freeze reused');return
 assert (OUT/'evidence/atlas_reconciliation.json').exists()
 test=read(OUT/'evidence/new_test_results.json');assert test['failed']==0
 entries=jl(OUT/'data/public_prompts.jsonl');n=len(entries);assert n==40
 old=jl(ROOT/'experiments/math500_scoring_and_budget_v2/api_calls.jsonl');base=[r for r in old if r['stage']=='base4096'];ups=[r for r in old if r['stage']=='upgrade8192'];top=[r for r in old if r['stage']=='upgrade16384']
 cfg={'run_id':'failure_mechanism_a1_a2_pilot','model':'deepseek-flash','endpoint':'https://api.deepseek.com/chat/completions','system_prompt':'You are an expert programmer and mathematician.','thinking':'default enabled','reasoning_effort':'default high','gold_feedback':False,'skill_injection':False,'api_workers':64,'local_workers':12,'max_calls':200,'max_total_tokens':1500000,'schedule_seed':20261020,'intervention_cap':4096,'budget_rungs':[4096,8192,16384],'B2_initial_cap':16384,'shared_requests':{'B0':['B1'],'B2':['B2+a1','B2+a2','B2+generic']},'generic_trigger':'all 40 tasks','no_cancellation':True,'no_gold_retry':True,'retry_on_transport_failure':False}
 save('config.json',cfg)
 b0mean=statistics.mean(r['total_tokens'] for r in base);rate8=len(ups)/len(base);rate16=len(top)/len(base)
 # Double historical escalation rate and allow 8 conditional interventions; explicit planning assumptions, not results.
 expcalls=3*n+2*n*rate8+2*n*rate16+8
 output= n*statistics.mean(r['output_tokens'] for r in base)+n*4096+n*4096+2*n*rate8*8192+2*n*rate16*16384+8*4096
 input_bound=3*sum(len(e['prompt'].encode())+512 for e in entries)+n*3500+8*6500
 predicted=round(output+input_bound)
 assert expcalls<=200 and predicted<=1500000,(expcalls,predicted)
 save('evidence/cost_forecast.json',{'at':now(),'n':n,'historical_mean_base_tokens':b0mean,'historical_8192_rate':rate8,'historical_16384_rate':rate16,'forecast_calls':round(expcalls,2),'forecast_actual_tokens_conservative':predicted,'forecast_output_tokens':round(output),'forecast_input_tokens_byte_bound':input_bound,'forecast_usd_peak_uncached':round(output*1.2e-6+input_bound*.3e-6,4),'assumptions':'Double historical B1 escalation frequencies; budget average 4096 for B2 and generic; eight conditional A1/A2 calls. This is a forecast, not a guarantee. Runtime reserves UTF-8 input bytes +512+output cap before every call. The full unconstrained worst-case tree can exceed the cap and will not be executed if cap prevents it. No sample enlargement.','absolute_worst_case_calls':n*7,'hard_calls_cap':200,'hard_actual_tokens_cap':1500000})
 files=list((OUT/'code').glob('*.py'))+list((OUT/'tests').glob('*.py'))+list((ROOT/'FlowEvo/src/math_control').glob('*.py'))+[OUT/'config.json',OUT/'data/public_tasks.jsonl',OUT/'data/public_prompts.jsonl',OUT/'dataset_manifest.json',OUT/'evidence/stage1_sealed.json',OUT/'evidence/cost_forecast.json',ROOT/'experiments/math500_scoring_and_budget_v2/code/completion.py']
 v3=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')
 files+=[ROOT/p for p in v3['source_files']]
 for p,h in v3['source_files'].items():assert sha(ROOT/p)==h,p
 save('evidence/pre_api_freeze.json',{'at':now(),'reference_commit':REF,'files':{str(p.relative_to(ROOT)):sha(p) for p in files},'v3_config_hash':v3['config_hash'],'no_pilot_generation_yet':not list((OUT/'raw').glob('*.json')),'old_scores_tests_reused':True,'configuration':cfg,'dataset_manifest_sha256':sha(OUT/'dataset_manifest.json'),'test_result':test})
 print({'forecast_calls':expcalls,'forecast_tokens':predicted,'frozen_files':len(files)})
if __name__=='__main__':main()
