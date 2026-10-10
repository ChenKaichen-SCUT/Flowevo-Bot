"""Run every discovered project test directory, with network denied and logs retained."""
from common import *
import subprocess,os,time,tempfile,xml.etree.ElementTree as ET

def main():
 groups=sorted({p.parent for p in ROOT.rglob('test*.py') if not any(x in {'.venv','.wheelcheck','.git','__pycache__'} for x in p.parts)})
 # Use isolated subprocesses: historical experiments contain identically named
 # common.py modules and tests; a single shared import cache is not appropriate.
 results=[]
 with tempfile.TemporaryDirectory(prefix='v3_offline_tests_') as td:
  Path(td,'sitecustomize.py').write_text('import socket\ndef denied(*a,**k): raise RuntimeError("network prohibited in offline research tests")\nsocket.socket.connect=denied\nsocket.socket.connect_ex=denied\nsocket.create_connection=denied\n')
  env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join([td,str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo/src'),str(ROOT/'FlowEvo-Recovery/src')]);env['HF_DATASETS_OFFLINE']='1';env['HF_HUB_OFFLINE']='1';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
  for i,group in enumerate(groups):
   rel=str(group.relative_to(ROOT));log=OUT/f'evidence/test_group_{i:02d}.log';xml=OUT/f'evidence/test_group_{i:02d}.xml';start=time.monotonic()
   cmd=[sys.executable,'-m','pytest',str(group),'-q','--tb=short','--import-mode=prepend',f'--junitxml={xml}']
   with log.open('w') as f:p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
   suites=ET.parse(xml).getroot();attrs=[x.attrib for x in suites.iter('testsuite')]
   counts={k:sum(int(a.get(k,0)) for a in attrs) for k in ['tests','failures','errors','skipped']}
   item={'group':rel,'exit_code':p.returncode,'wall_seconds':time.monotonic()-start,'counts':counts,'log':str(log.relative_to(OUT)),'command':cmd,'network':'denied by sitecustomize'}
   results.append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
  status=all(r['exit_code']==0 or r['exit_code']==5 and r['counts']['tests']==0 for r in results)
  save('regression_test_results.json',{'passed':status,'groups':results,'total_tests':sum(r['counts']['tests'] for r in results),'new_llm_calls':0,'no_test_file_suites':'BoT test_templates.py are string constants; pytest exit5 means no tests, not a skipped executable test.'})
  if not status:raise SystemExit(1)
if __name__=='__main__':main()
