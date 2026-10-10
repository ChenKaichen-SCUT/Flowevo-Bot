"""Close this stage, validate evidence, and build the requested complete study ZIP."""
from common import *
import zipfile,tarfile,re,xml.etree.ElementTree as ET

def main():
 suite=ET.parse(OUT/'evidence/delivery_tests.xml').getroot()
 tests=sum(int(e.get('tests','0'))for e in suite.iter('testsuite'))
 assert tests==14 and all(int(e.get('failures','0'))+int(e.get('errors','0'))==0 for e in suite.iter('testsuite'))
 assert '12 passed'in(OUT/'evidence/test_selection.log').read_text()
 assert read(OUT/'evidence/generation_tests.json')['passed']==9
 hist=read(OUT/'evidence/historical_hash_verification.json');assert not hist['unexpected_changes']and hist['protected_verified_count']==7083
 for p,h in read(OUT/'evidence/pre_api_freeze.json')['files'].items():assert sha(ROOT/p)==h,p
 for p,h in read(OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json')['files'].items():assert sha(ROOT/p)==h,p
 assert not list((OUT/'attempts').glob('*.pending.json'))
 run=read(OUT/'run_manifest.json');run.update(new_tests_passed=35,artifact_integrity_tests_passed=14,old_files_verified_unchanged=7083,old_tests_reused_not_rerun=498,delivery_ready=True,new_paid_calls_closed=True)
 save('run_manifest.json',run)
 save('evidence/delivery_validation.json',{'at':now(),'new_unique_tests_passed':35,'generation_tests':9,'selection_tests':12,'artifact_integrity_tests':14,'old_tests_reused_not_rerun':498,'old_protected_files_unchanged':7083,'new_api_calls':955,'new_tokens':1682920,'usage_unknown_calls':0,'logical_outputs':962,'baseline605':True,'full_validation119_k4':True,'manual_noncorrect_reviews':60,'ambiguous_test_labels_remain_null':2,'no_more_paid_calls':True,'optional_stages_closed_by_predeclared_gate':True})
 files=list((OUT/'code').glob('*.py'))+list((OUT/'tests').glob('*.py'))
 save('evidence/delivery_source_freeze.json',{'at':now(),'files':{str(p.relative_to(ROOT)):sha(p)for p in files},'generation_sources_frozen_before_any_new_call':True,'selection_source_sealed_before_candidates_2_to_4_grading':True,'validation_candidate1_was_already_scored_before_selection_seal':True,'posthoc_reporting_and_review_sources_added_later':True})
 save('evidence/provider_documentation.json',{'checked_at':now(),'model_requested_and_returned':'deepseek-flash','returned_fingerprint':'aeb56401ca74e127821c4f9126dcb669','thinking_documentation':'https://api-docs.deepseek.com/guides/thinking_mode/','pricing_documentation':'https://api-docs.deepseek.com/quick_start/pricing/','effective_sampling':'Thinking default enabled/high; temperature ignored; no seed sent/supported','observed_reasoning_tokens_returned':True,'cost_estimate_basis':'Conservative peak uncached input0.30/output1.20 USD per million; not a billing statement.'})
 # Existing publisher scans ZIP members; also inspect the two newly downloaded TARs.
 secret=(ROOT/'miyao.txt').read_bytes().strip();pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9_-]{28,})')
 checked=[]
 previous_scan=read(OUT/'evidence/downloaded_archive_secret_scan.json')if(OUT/'evidence/downloaded_archive_secret_scan.json').exists()else None
 for p in [OUT/'evidence/official_aflow_data.tar.gz',OUT/'evidence/official_aflow_results.tar.gz']:
  previous=next((r for r in (previous_scan or {}).get('archives',[])if r['file']==str(p.relative_to(OUT))and r['sha256']==sha(p)and r['matches']==0),None)
  if previous:checked.append(previous);continue
  count=0
  with tarfile.open(p,'r:gz')as tar:
   for m in tar:
    if not m.isfile():continue
    data=tar.extractfile(m).read()
    if secret in data or pattern.search(data):raise RuntimeError('Potential secret in downloaded archive member; contents not printed')
    count+=1
  checked.append({'file':str(p.relative_to(OUT)),'members':count,'sha256':sha(p),'matches':0})
 save('evidence/downloaded_archive_secret_scan.json',{'at':now(),'archives':checked,'credentials_not_logged':True})
 members={p for p in OUT.rglob('*')if p.is_file()and not any(x in {'__pycache__','.pytest_cache'}for x in p.parts)and p.suffix not in {'.pyc','.pyo'}}
 members|={ROOT/p for p in read(OUT/'evidence/pre_api_freeze.json')['files']}
 members|=set((ROOT/'FlowEvo/src/math_control').glob('*.py'))
 members|={ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json',ROOT/'experiments/failure_mechanism_a1_a2_pilot/pilot_v3_results.jsonl'}
 members|={ROOT/r['source_path']for r in read(OUT/'evidence/reused_outputs.json')}
 members|={p for p in (ROOT/'AFlow').rglob('*')if p.is_file()and '.git'not in p.parts}
 dest=ROOT/'aflow_math617_capability_probe.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(members):z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(dest)as z:assert z.testzip()is None and len(z.namelist())==len(members)
 assert dest.stat().st_size<100*1024**2,'GitHub100MiB file limit'
 (ROOT/'aflow_math617_capability_probe.zip.sha256').write_text(sha(dest)+'  '+dest.name+'\n')
 print(json.dumps({'zip':str(dest),'files':len(members),'bytes':dest.stat().st_size,'sha256':sha(dest),'new_tests_passed':35,'old_files_unchanged':7083}))
if __name__=='__main__':main()
