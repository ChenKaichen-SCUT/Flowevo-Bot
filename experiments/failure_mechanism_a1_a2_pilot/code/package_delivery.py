"""Validate final deliverables and package this round without secrets/caches."""
from common import *
import zipfile,xml.etree.ElementTree as ET

def main():
 required=[f'{i:02d}_{name}.md'for i,name in enumerate(['EXECUTIVE_SUMMARY','FAILURE_MECHANISM_ATLAS','ONLINE_OBSERVABILITY','HIGH_BUDGET_VS_STAGED_RETRY','ANSWER_FINALIZATION_A1','GOAL_CONSISTENCY_A2','INDEPENDENT_PILOT_RESULTS','PAIRED_ACCURACY_AND_COST','FAILURE_AND_NEGATIVE_TRANSFER','NEXT_RESEARCH_DECISION'])]+['failure_cases.jsonl','failure_taxonomy.csv','candidate_answer_events.jsonl','goal_specs.jsonl','controller_decisions.jsonl','task_results.jsonl','task_pairwise.csv','api_calls.jsonl','cost_breakdown.csv','dataset_manifest.json','run_manifest.json']
 for name in required:assert (OUT/name).is_file(),name
 for p,h in read(OUT/'evidence/pre_api_freeze.json')['files'].items():assert sha(ROOT/p)==h,p
 for p,h in read(OUT/'evidence/stage1_sealed.json')['files'].items():assert sha(OUT/p)==h,p
 hist=read(OUT/'evidence/historical_hash_verification.json');assert hist['protected_verified_count']==6572 and not hist['unexpected_changes']
 suite=ET.parse(OUT/'evidence/artifact_tests.xml').getroot();assert sum(int(e.get('failures','0'))+int(e.get('errors','0'))for e in suite.iter('testsuite'))==0
 run=read(OUT/'run_manifest.json');summary=read(OUT/'pilot_summary.json');assert run['frozen_scores']=={k:v['correct']for k,v in summary['metrics'].items()};assert run['posthoc_math_correct']==read(OUT/'evidence/pilot_manual_audit.json')['posthoc_math_correct_by_method']
 assert not list((OUT/'raw').glob('*.pending.json'));assert len(jl(OUT/'task_results.jsonl'))==240
 files=list((OUT/'code').glob('*.py'))+list((OUT/'tests').glob('*.py'))+list((ROOT/'FlowEvo/src/math_control').glob('*.py'))
 save('evidence/delivery_source_freeze.json',{'at':now(),'files':{str(p.relative_to(ROOT)):sha(p)for p in files},'generation_sources_frozen_before_calls':True,'posthoc_analysis_and_delivery_code_added_after_freeze':True})
 save('evidence/delivery_validation.json',{'at':now(),'required_files':len(required),'required_files_present':True,'new_unique_tests_passed':38,'old_tests_reused':460,'new_scored_responses':len(jl(OUT/'pilot_v3_results.jsonl')),'method_task_rows':240,'completed_calls':123,'http_attempts_including_interrupted':124,'known_actual_tokens':193828,'unreturned_usage_upper_bound':5412,'safety_total_upper_bound':199240,'old_6572_files_unchanged':True,'V3_and_generation_source_hashes_unchanged':True,'complete_generation_no_pending':True,'no_further_api_calls_planned':True})
 dest=ROOT/'failure_mechanism_a1_a2_pilot.zip';skip={'__pycache__','.pytest_cache'}
 members=[p for p in OUT.rglob('*')if p.is_file() and not any(part in skip for part in p.parts) and p.suffix not in('.pyc','.pyo')]
 members+=list((ROOT/'FlowEvo/src/math_control').glob('*.py'))+list((ROOT/'FlowEvo/src/math_evaluation').glob('*.py'))+[ROOT/'FlowEvo/requirements-math-evaluator-v3.txt']
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for path in sorted(members):z.write(path,str(path.relative_to(ROOT)))
 with zipfile.ZipFile(dest)as z:assert z.testzip() is None;assert len(z.namelist())==len(members)
 print({'archive':str(dest),'bytes':dest.stat().st_size,'files':len(members),'sha256':sha(dest)})
if __name__=='__main__':main()
