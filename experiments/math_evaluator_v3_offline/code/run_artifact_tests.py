from common import *
import socket,time,xml.etree.ElementTree as ET

def deny(*args,**kwargs):raise RuntimeError('Artifact tests are offline')
socket.socket.connect=deny;socket.create_connection=deny
import pytest
start=time.monotonic();xml=OUT/'evidence/artifact_tests.xml'
rc=pytest.main([str(OUT/'tests/test_artifacts.py'),'-q','--tb=short',f'--junitxml={xml}']);assert rc==0
attrs=[x.attrib for x in ET.parse(xml).getroot().iter('testsuite')];counts={k:sum(int(a.get(k,0)) for a in attrs) for k in ['tests','failures','errors','skipped']}
r=read(OUT/'regression_test_results.json');r['groups']=[x for x in r['groups'] if x.get('kind')!='v3_artifact_invariants']
r['groups'].append({'group':'experiments/math_evaluator_v3_offline/tests/test_artifacts.py','kind':'v3_artifact_invariants','exit_code':0,'counts':counts,'wall_seconds':time.monotonic()-start,'log':'evidence/artifact_tests.log','command':[sys.executable,'experiments/math_evaluator_v3_offline/code/run_artifact_tests.py'],'network':'denied by socket hooks'})
r['total_tests']=sum(g['counts']['tests'] for g in r['groups']);r['passed']=all(g['exit_code']==0 or g['exit_code']==5 and g['counts']['tests']==0 for g in r['groups']);save('regression_test_results.json',r)
