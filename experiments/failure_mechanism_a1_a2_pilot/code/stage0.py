from common import *
import subprocess,requests,collections

def main():
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT.parent/'Flowevo-Bot-upload',text=True).strip();assert head==REF,head
 frozen=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')
 for p,h in frozen['source_files'].items():assert sha(ROOT/p)==h,p
 previous=read(ROOT/'experiments/math_evaluator_v3_offline/run_manifest.json')
 # Reuse sealed results, no regeneration or historical regrading/test rerun.
 reused={'V3_prior_run_manifest':sha(ROOT/'experiments/math_evaluator_v3_offline/run_manifest.json'),'v3_results':sha(ROOT/'experiments/math_evaluator_v3_offline/evaluator_v3_results.jsonl'),'historical_four_scores':{'base_legacy':456,'base_fixed':449,'adaptive_legacy':485,'adaptive_fixed':476},'v3_scores':{'base':466,'adaptive':495},'previous_passed_tests_reused':previous['tests']['total_tests'],'prior_experiments_rerun':False}
 model_file=OUT/'evidence/models_capabilities.json'
 if not model_file.exists():
  key=(ROOT/'miyao.txt').read_text().strip()
  r=requests.get('https://api.deepseek.com/models',headers={'Authorization':'Bearer '+key},timeout=(20,60));r.raise_for_status()
  save(model_file,{'retrieved_at':now(),'url':'https://api.deepseek.com/models','http_status':r.status_code,'generation_calls':0,'response':r.json()})
 hist=jl(ROOT/'experiments/math500_scoring_and_budget_v2/api_calls.jsonl')
 cases=[r for r in hist if r['response']['choices'][0]['message'].get('reasoning_content')]
 usage_details=sum('reasoning_tokens' in r['response']['usage'].get('completion_tokens_details',{}) for r in hist)
 evidence={'timestamp':now(),'head':head,'evaluator_frozen':frozen,'reuse':reused,'official_sources':['https://api-docs.deepseek.com/api/create-chat-completion/','https://api-docs.deepseek.com/guides/thinking_mode/','https://api-docs.deepseek.com/api/list-models/','https://api-docs.deepseek.com/quick_start/pricing/'],'capabilities':{'max_tokens':'upper bound; generation may stop earlier','reasoning_content':'separate visible API field; streamed delta or completed response, not inferred internal state','content':'final delivered text','finish_reason':'stop natural termination; length limit; other values treated incomplete','reasoning_output_accounting':'reasoning_tokens is a subset of completion_tokens when usage detail supplied','streaming':'documented SSE reasoning_content/content deltas and final usage; pilot B2 streams to verify without a separate probe','pause_resume':'No documented paused internal state for ordinary Chat Completions. Closing stream is cancellation, not resumable thinking. Not used.','prior_reasoning':'without tools, historical reasoning_content field is ignored by subsequent calls; explicitly supplied excerpts in a new user message are ordinary new context','thinking':'enabled/high default; omit parameters exactly as historical requests','temperature':'historical 0 retained for payload consistency; documented ignored in thinking mode','top_p':'omitted, same as old payload; documented thinking effective range .95..1','A1_implementation':'post-completion short fresh finalization request only after incomplete B2 and a typed observed candidate; no stream interruption','model_revision':'alias not pinned; record actual response model and fingerprint; no zero-randomness claim'},'historical_actual_evidence':{'saved_calls':len(hist),'reasoning_text_available_calls':len(cases),'reasoning_usage_detail_calls':usage_details,'finish_reason_counts':dict(collections.Counter(r['finish_reason'] for r in hist)),'stop_below_requested_cap':sum(r['finish_reason']=='stop' and r['output_tokens']<r['max_tokens'] for r in hist),'source':'experiments/math500_scoring_and_budget_v2/api_calls.jsonl','source_sha256':sha(ROOT/'experiments/math500_scoring_and_budget_v2/api_calls.jsonl')},'new_generation_calls':0,'pricing_per_million_usd':{'input_cache_miss_peak':.30,'input_cache_hit_peak':.006,'output_peak':1.20,'off_peak_multiplier':.5},'limits':{'new_normal_calls':200,'total_actual_tokens':1500000,'api_workers':64,'local_workers':12}}
 save('evidence/stage0_capabilities.json',evidence);save('evidence/reused_work.json',reused)
 print({'head':head,'prior_tests_reused':reused['previous_passed_tests_reused'],'generation_calls':0,'metadata_http_status':read(model_file)['http_status']})
if __name__=='__main__':main()
