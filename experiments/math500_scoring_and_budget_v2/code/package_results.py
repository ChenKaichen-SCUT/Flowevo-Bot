"""Create a research archive with hash-bound evidence and reused source; no credentials."""
from common import *
from audit_artifacts import audit
import zipfile

def allowed(p):
 return p.is_file() and not p.is_symlink() and not any(x in p.parts for x in ['.git','.venv','__pycache__','.pytest_cache']) and p.suffix not in ['.pyc','.pyo']
def main():
 result=audit();save('evidence/final_integrity_audit.json',result)
 tests=(OUT/'evidence/tests_final.txt').read_text();assert '67 passed' in tests and 'failed' not in tests
 files={p for p in OUT.rglob('*') if allowed(p) and p.name!='run_manifest.json'}
 for name in ['Flowevo-Bot/src','FlowEvo-Recovery/src','FlowEvo/src']:
  files.update(p for p in (ROOT/name).rglob('*') if allowed(p))
 for name in ['指引.txt','Flowevo-Bot/pyproject.toml','FlowEvo/pyproject.toml','FlowEvo/requirements.txt','FlowEvo/data/datasets/math/train.jsonl','FlowEvo/data/datasets/math/test.jsonl','experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json','experiments/math_truncation_and_scoring_audit/tests/test_scoring.py']:
  p=ROOT/name
  if p.exists():files.add(p)
 assert sha(ROOT/'指引.txt')==sha(OUT/'USER_GUIDE.txt')
 entries=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
 manifest={'run_id':cfg['run_id'] if (cfg:=read(OUT/'config.json')) else '', 'created_at':now(),'reference_commit':REF,'files':entries,'file_count':len(entries),'primary_scores':{'A':456,'B':449,'C':485,'D':476},'primary_unknowns':{'A':0,'B':16,'C':0,'D':18},'actual_calls':577,'actual_total_tokens':978566,'decision':'PARTIAL','posthoc_sensitivity_only':{'base':467,'adaptive':496},'tests':'67 passed; pre-API 59 passed','manifest_self_excluded':True,'archive_layout':'workspace-relative experiment, reused code, source math dataset, and historical regression fixture; full publication audit additionally needs the repository historical files','publication_commit':'See GitHub main/final delivery; commit not embedded in its own contents'}
 save('run_manifest.json',manifest)
 archive=ROOT/'math500_scoring_and_budget_v2.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(files|{OUT/'run_manifest.json'}):z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for item in entries:assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
 checksum=sha(archive);(ROOT/'math500_scoring_and_budget_v2.zip.sha256').write_text(checksum+'  '+archive.name+'\n')
 print(json.dumps({'file_count':len(entries),'archive_bytes':archive.stat().st_size,'archive_sha256':checksum,'integrity':result['status']},indent=2))
if __name__=='__main__':main()
