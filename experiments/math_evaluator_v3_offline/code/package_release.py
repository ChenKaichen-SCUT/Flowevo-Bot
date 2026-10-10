from common import *
import zipfile

def main():
 paths=[]
 for directory in [OUT,OLD,ROOT/'FlowEvo/src',ROOT/'Flowevo-Bot/src',ROOT/'FlowEvo-Recovery/src']:
  paths.extend(p for p in directory.rglob('*') if p.is_file() and not any(part in {'.git','.venv','__pycache__','.pytest_cache'} for part in p.parts) and p.suffix not in {'.pyc','.pyo'})
 paths.extend(ROOT/p for p in ['FlowEvo/requirements-math-evaluator-v3.txt','FlowEvo/pyproject.toml','Flowevo-Bot/pyproject.toml','FlowEvo-Recovery/pyproject.toml','experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json'])
 paths=sorted(set(paths));entries={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
 archive=ROOT/'math_evaluator_v3_offline.zip'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in paths:z.write(p,str(p.relative_to(ROOT)))
  z.writestr('ARCHIVE_CONTENTS.json',json.dumps({'files':entries,'scope':'current research stage, replay sources, and previous sealed evidence; no credentials or virtual environments'},ensure_ascii=False,indent=2)+'\n')
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for p,metadata in entries.items():assert hashlib.sha256(z.read(p)).hexdigest()==metadata['sha256'],p
 # Receipt is beside ZIP, not inside the hashed content (no recursive hashes).
 (ROOT/'math_evaluator_v3_offline.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
 print({'zip':str(archive),'files':len(paths),'bytes':archive.stat().st_size,'sha256':sha(archive)})
if __name__=='__main__':main()
