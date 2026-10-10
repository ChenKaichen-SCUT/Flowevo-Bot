from common import *
from transport import token_bound
from intervene import request_for
from collections import Counter

def main():
    summary=read(OUT/'summary.json');calls=jl(OUT/'api_calls.jsonl');states=jl(OUT/'counterfactual_states.jsonl')
    checks={}
    checks['physical_102_unique_calls']=len(calls)==len({r['job_id'] for r in calls})==102
    checks['hard_call_token_limits']=len(calls)<=150 and summary['total_tokens_upper_bound']<=350000
    checks['cancel_usage_not_fabricated']=sum(not r['usage_known'] for r in calls)==1 and summary['unknown_token_upper_bound']==1247
    checks['all_usage_identity']=all(r['input_tokens']+r['output_tokens']==r['total_tokens'] for r in calls if r['usage_known'])
    checks['full_usage_ledger']=sum(r['total_tokens'] for r in calls if r['usage_known'])==summary['known_tokens']==299853
    checks['all_response_hashes']=all(r['response_hash']==digest(r['response']) for r in calls)
    checks['upper_bounds_cover_responses']=all(r['total_tokens']<=token_bound(r['request']) for r in calls if r['usage_known'])
    checks['source_freezes']=all(sha(ROOT/p)==h for file in ('counterfactual_freeze.json','pilot_freeze.json','api_audit_source_freeze.json') for p,h in read(OUT/'evidence'/file)['files'].items())
    checks['analysis_policy_freeze']=sha(OUT/'code/grade_and_fit.py')==read(OUT/'evidence/analysis_policy_freeze.json')['source_sha256']
    checks['sealed_responses_and_pilot']=all(sha(OUT/p)==h for file in ('COUNTERFACTUAL_SEALED.json','PILOT_SEALED.json','NEGATIVE_CONTROL_SEALED.json') for p,h in read(OUT/'evidence'/file)['files'].items())
    checks['full_states_are_exact_historical_prefixes']=all(read(ROOT/s['historical_raw_path'])['response']['choices'][0]['message']['reasoning_content'][:s['cut_char']]==s['prefix'] for s in states)
    cmap={r['job_id']:r for r in calls};config=read(OUT/'config.json')
    checks['all84_public_requests_reconstruct']=all(cmap[s['state_id']+'__'+b]['request']==request_for(s,b,config)[0] for s in states for b in 'ABC')
    train={s['task_id'] for s in states if s['discovery_split']=='train'};dev={s['task_id'] for s in states if s['discovery_split']=='development'}
    checks['taskwise_train_development_disjoint']=len(train)==12 and len(dev)==8 and not(train&dev)
    public=jl(OUT/'data/independent_public.jsonl');old={r['task_id'] for r in jl(HIGH/'data/public_tasks.jsonl')}
    registry=set(read(ROOT/'experiments/math500_scoring_and_budget_v2/evidence/exposure_registry.json')['excluded_ids'])
    checks['independent_ids_clean']=len(public)==4 and all(r['task_id'] not in old|registry for r in public)
    rows=jl(OUT/'independent_results.jsonl')
    checks['all20_method_results_with_actual_costs']=len(rows)==20 and all(sum(cmap[j]['total_tokens'] for j in r['jobs'])==r['total_tokens'] for r in rows)
    checks['paired_controller_all_public']=all(r['gold_access'] is False and r['controller_llm_calls']==0 for r in rows)
    checks['no_gold_feedback_or_skills']=config['gold_feedback'] is False and config['skill_injection'] is False
    checks['all_methods_comparable_output_cap']=all(r['max_generated_tokens']==16384 and sum(cmap[j]['request']['max_tokens'] for j in r['jobs'])==16384 if r['logical_calls']==2 else r['max_generated_tokens']==16384 for r in rows)
    checks['native_v3_unchanged']=all(sha(ROOT/p)==h for p,h in read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')['source_files'].items())
    previous=read(OUT/'evidence/previous_upload_manifest.json')
    protected=[e for e in previous['files'] if e['path']!='指引.txt']
    checks['historical_files_unchanged']=all(sha(ROOT/e['path'])==e['sha256'] for e in protected)
    checks['current_guide_snapshot']=sha(ROOT/'指引.txt')==sha(OUT/'USER_GUIDE.txt')
    checks['required_reports']=all((OUT/name).exists() for name in ['00_EXECUTIVE_SUMMARY.md','01_TRACE_ANALYSIS.md','02_COUNTERFACTUAL_INTERVENTIONS.md','03_MINIMAL_SUFFICIENT_STATE.md','04_ONLINE_FEASIBILITY.md','05_COMPRESSION_CONTROLLER.md','06_INDEPENDENT_PILOT_RESULTS.md','07_ACCURACY_AND_TOKEN_COST.md','08_MECHANISM_ATTRIBUTION.md','09_NEXT_RESEARCH_DECISION.md'])
    checks['frozen_decision_no_go']=summary['decision']=='NO-GO' and next(m for m in summary['independent'] if m['method']=='B4_counterfactual')['total_tokens_saved_vs_B0']==-1532
    audit=read(OUT/'evidence/distinct_state_audit.json')
    checks['duplicate_state_gate_corrected']=audit['unique_primary_prefix_states']==27 and audit['unique_trigger_states']==1 and audit['audited_distinct_state_gate_passed'] is False and summary['counterfactual']['online_gate_passed'] is False
    assert all(checks.values()),{k:v for k,v in checks.items() if not v}
    save('evidence/artifact_checks.json',dict(at=now(),passed=len(checks),total=len(checks),checks=checks,
        historical_files_protected=len(protected),only_authorized_old_file_changed='指引.txt'))
    print(json.dumps(dict(passed=len(checks),historical_files_protected=len(protected),known_tokens=summary['known_tokens'],tokens_upper_bound=summary['total_tokens_upper_bound'])))
if __name__=='__main__':main()
