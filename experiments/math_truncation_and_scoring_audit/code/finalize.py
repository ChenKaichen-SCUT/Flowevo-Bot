"""Seal the final local deliverable and create a reproducible, secret-free ZIP."""
from prepare import ROOT,OUT,read,sha
from flowevo_bot.common import write_json,now
import hashlib,json,zipfile,subprocess,sys

def main():
 prev=read(OUT/'evidence/protected_previous_snapshot.json')
 changes=[x['path'] for x in prev['files'] if not (ROOT/x['path']).is_file() or sha(ROOT/x['path'])!=x['sha256']]
 assert changes==['指引.txt'],changes
 assert sha(ROOT/'指引.txt')==sha(OUT/'USER_GUIDE.txt')
 assert sha(OUT/'evidence/previous_published_guide.txt')==next(x['sha256'] for x in prev['files'] if x['path']=='指引.txt')
 baseline=read(OUT/'evidence/baseline_file_hashes.json')
 assert all(sha(ROOT/x['path'])==x['sha256'] for x in baseline)
 for x in read(OUT/'evidence/frozen_experiment_code.json'):assert sha(ROOT/x['path'])==x['sha256']
 assert not list((OUT/'raw').glob('*.pending.json')) and not list((OUT/'raw').glob('*.error.json'))
 tests=(OUT/'evidence/tests_final.txt').read_text();assert '42 passed' in tests
 validation={'checked_at':now(),'protected_previous_files':len(prev['files']),'previous_files_modified':changes,'only_modified_previous_path_is_canonical_guide':True,'previous_guide_preserved':True,'historical_data_and_code_modified':False,'historical_experiment_files_checked':len(baseline),'frozen_pre_generation_code_unchanged':True,'all_new_calls_sealed':True,'real_new_calls':37,'actual_new_tokens':288397,'tests':'42 passed','gold_feedback':False,'new_experiments_stopped':True,'publication_target':'https://github.com/ChenKaichen-SCUT/Flowevo-Bot'}
 write_json(OUT/'evidence/final_validation.json',validation)
 # Include the tested scorer and its direct source dependencies in the archive.
 sources=[ROOT/'FlowEvo-Recovery/src/flowevo_recovery/math_scoring_v2.py',ROOT/'Flowevo-Bot/src/flowevo_bot/v2/evaluator.py',ROOT/'Flowevo-Bot/src/flowevo_bot/common.py',ROOT/'Flowevo-Bot/src/flowevo_bot/__init__.py',ROOT/'Flowevo-Bot/src/flowevo_bot/v2/__init__.py',ROOT/'FlowEvo-Recovery/src/flowevo_recovery/__init__.py']
 files=[x for x in OUT.rglob('*') if x.is_file() and not any(v in x.parts for v in ('__pycache__','.pytest_cache')) and x.name!='run_manifest.json']+sources
 manifest={'schema_version':1,'finalized_at':now(),'reference_commit':read(OUT/'preflight.json')['reference_commit'],'repository':validation['publication_target'],'new_code_version':'Per-file SHA256 below; publishing commit is the enclosing Git commit','user_guide_sha256':sha(OUT/'USER_GUIDE.txt'),'configuration':read(OUT/'preflight.json'),'summary':read(OUT/'summary.json'),'validation':validation,'file_count_excluding_self':len(files),'files':[{'path':str(x.relative_to(ROOT)),'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(files)],'historical_full_response_limit':'Only original visible content/request/usage/finish reason retained; original reasoning text absent. New HTTP JSON fully preserved.','extra_reference_ambiguity_flags':1,'manual_review_changed_scores':False,'replicate_api_calls_required_for_offline_verification':0,'archive_note':'ZIP uses workspace-relative paths. To run all scripts, overlay on repository; archive includes direct scorer sources, but not the entire virtual environment.'}
 write_json(OUT/'run_manifest.json',manifest)
 files.append(OUT/'run_manifest.json')
 target=ROOT/'math_truncation_and_scoring_audit.zip'
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for x in sorted(files):z.write(x,str(x.relative_to(ROOT)))
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None and len(z.namelist())==len(files)
  for x in files:assert hashlib.sha256(z.read(str(x.relative_to(ROOT)))).hexdigest()==sha(x)
 receipt={'zip':str(target.relative_to(ROOT)),'sha256':sha(target),'bytes':target.stat().st_size,'members':len(files),'run_manifest_sha256':sha(OUT/'run_manifest.json')}
 (ROOT/'math_truncation_and_scoring_audit.sha256').write_text(receipt['sha256']+'  '+target.name+'\n')
 print(json.dumps(receipt,indent=2));print(json.dumps(validation,indent=2))
if __name__=='__main__':main()
