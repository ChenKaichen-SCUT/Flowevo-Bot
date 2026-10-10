"""Finalize reproducible local artifacts; publishing is a separate explicit command."""
from common import *
from campaign import check_freeze
import zipfile

def main():
 check_freeze();summary=read(OUT/'evidence/analysis_summary.json');integrity=read(OUT/'evidence/integrity.json')
 paths=[p for directory in [ROOT/'FlowEvo-Recovery',OUT] for p in directory.rglob('*') if p.is_file() and not any(x in p.parts for x in ['__pycache__','.pytest_cache']) and p.suffix not in ['.pyc','.pyo'] and p.name!='run_manifest.json']
 manifest={'study':'failure_recovery_pilot','completed_at':now(),'status':'complete_and_stopped','reference_commit':read(OUT/'config.json')['reference_commit'],
  'decision':{'A':'NO-GO','C':'NO-GO','scope':'do not scale current design; extraction and budget confounds dominate'},
  'physical_calls':summary['total_physical_calls'],'physical_tokens':summary['total_physical_tokens'],'physical_input_tokens':sum(x['input_tokens'] for x in summary['physical_costs']),'physical_output_tokens':sum(x['output_tokens'] for x in summary['physical_costs']),
  'hard_limits':{'calls':240,'tokens':300000,'api_workers':64,'local_workers':12},'actual_api_peak':integrity['peak_api_concurrency_from_timestamps'],
  'training_new_calls':81,'training_new_tokens':153819,'historical_prefix_tokens_separate':27793,'confirmation_new_calls':108,'confirmation_new_tokens':137522,
  'training_planned_branches':60,'training_observed_branches':49,'training_unexecuted_branches':11,'training_memory_sources':11,'training_memory_records':44,
  'confirmation_tasks':48,'confirmation_methods':6,'confirmation_method_rows':288,'incomplete_confirmation_method_rows':0,
  'mathematics_manual_adjudication':{'unique_outputs':3,'runtime_grader_unchanged':True,'automatic_results_preserved':'snapshots/task_results_automatic.jsonl'},
  'code_extraction_sensitivity':{'predeclared_before_confirmation':True,'no_hidden_tests_in_block_selection':True,'changes_to_online_controller':False,'zero_call_single_correct':42,'A_and_deterministic_correct':43},
  'tests':{'passed':20,'log':'evidence/tests_final.log','compileall':'passed'},'integrity':integrity,
  'publication':{'repository':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot','branch':'main','verification':'push then compare git ls-remote with local HEAD; external receipt stored in publishing clone .git/failure_recovery_publication.json'},
  'artifacts':{str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(paths)}}
 write(OUT/'run_manifest.json',manifest);paths.append(OUT/'run_manifest.json')
 target=ROOT/'failure_recovery_pilot.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(paths):z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  for p in paths:assert z.read(str(p.relative_to(ROOT)))==p.read_bytes()
 print(json.dumps({'zip':str(target),'files':len(paths),'bytes':target.stat().st_size,'sha256':sha(target),'all_members_verified':True}))
if __name__=='__main__':main()
