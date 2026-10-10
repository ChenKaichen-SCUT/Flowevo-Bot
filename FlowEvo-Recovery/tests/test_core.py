import sys,json,threading
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'FlowEvo-Recovery/src'),str(ROOT/'Flowevo-Bot/src')]
from flowevo_recovery.public import Task,State,ACTIONS,base_prompt,recovery_prompt
from flowevo_recovery.checks import features,run_tests
from flowevo_recovery.grading import score,normalize
from flowevo_recovery.client import Client,BudgetStop

def task(**kw):return Task(task_id='x',domain='math',problem='What is 2+2?',**kw)
def state(**kw):return State(task=task(),solution='The answer is 4.',truncated=False,call_id='old',**kw)
def cfg(**kw):return dict(model='deepseek-flash',temperature=0,math_max_tokens=4096,code_max_tokens=2048,max_calls=2,max_tokens=12000,**kw)
def response(_):return {'choices':[{'message':{'content':'The answer is 4.'},'finish_reason':'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}}

@pytest.mark.parametrize('field',['gold_answer','correct','hidden_tests','reference'])
def test_public_boundary(field):
 with pytest.raises(ValueError):task(**{field:'SECRET'})
 with pytest.raises(ValueError):state(**{field:'SECRET'})
def test_retry_no_previous():
 s=State(task=task(),solution='OLD_STATE',truncated=True,call_id='x')
 assert recovery_prompt(s,'retry',{'evidence':[]})==base_prompt(task())
 assert 'OLD_STATE' in recovery_prompt(s,'continue',{'evidence':[]})
def test_legal_and_hidden_tests_separated():
 t=Task(task_id='c',domain='code',problem='Identity',public_tests=['assert f(1)==1'])
 s=State(task=t,solution='def f(x): return 1',truncated=False,call_id='x')
 assert not features(s)['public_failed']
 assert score(t,s.solution,False,{'hidden_tests':['assert f(2)==2']})['correct'] is False
 assert 'f(2)' not in base_prompt(t)
def test_sandbox():
 assert run_tests('def f(x): return x+1',['assert f(2)==3'])['passed']
 assert not run_tests('def f(:',['assert True'])['compile_ok']
 assert not run_tests("open('/mnt/Space1/FlowEvo+BoT/miyao.txt').read()",['assert True'])['passed']
 assert not run_tests('while True: pass',['assert True'])['passed']
 assert run_tests('import os',['assert True'])['environment_issue']
@pytest.mark.parametrize('prediction,gold,question',[
 ('75%','75','What percent is shaded?'),('36°',r'36^\circ','Find the angle in degrees.'),
 ('2.50 dollars',r'\$2.50','How many dollars?'),('12 grams',r'12\text{gm}','How many grams?'),
 (r'\frac{12}{5525}',r'\frac{12}{5,\!525}','Find the probability.')])
def test_presentation_adjudication(prediction,gold,question):
 t=Task(task_id='t',domain='math',problem=question)
 assert score(t,'The answer is '+prediction,False,{'gold_answer':gold})['correct'] is True

def test_no_truncation_credit():assert score(task(),'The answer is 4',True,{'gold_answer':'4'})['correct'] is False

def test_durable_call_budget(tmp_path):
 c=Client(tmp_path,'neverprint',cfg(),'code',transport=response)
 x=c.complete(task(),'x','1','test','retry')
 assert c.complete(task(),'x','1','test','retry')==x and c.calls==1
 d=Client(tmp_path,'neverprint',cfg(),'code',transport=response)
 d.complete(task(),'x','2','test','retry')
 with pytest.raises(BudgetStop):d.complete(task(),'x','3','test','retry')
 assert d.actual==240 and d.calls==2
 assert 'neverprint' not in ''.join(p.read_text() for p in tmp_path.glob('*.json'))

def test_ambiguous_attempt_prohibits_retry(tmp_path):
 def bad(_):raise TimeoutError()
 c=Client(tmp_path,'secret',cfg(),'code',transport=bad)
 with pytest.raises(RuntimeError):c.complete(task(),'x','1','test','retry')
 with pytest.raises(RuntimeError):Client(tmp_path,'secret',cfg(),'code',transport=response)

def test_reservation_prevents_overrun(tmp_path):
 config=cfg();config['max_tokens']=4600
 c=Client(tmp_path,'secret',config,'code',transport=response)
 with pytest.raises(BudgetStop):c.complete(task(),'long'*100,'1','test','retry')
 assert c.calls==0

def test_controller_public_only_and_no_oracle():
 from flowevo_recovery.controller import select
 f=features(state())
 assert select('A',f)['action'] is None
 with pytest.raises(ValueError):select('A',{**f,'correct':False})
 f['truncated']=True
 assert select('A',f)['action']=='continue'
 assert select('fixed_retry',f)['action']=='retry'
 assert select('deterministic_retry',f)['action']=='retry'
 assert select('C',f)['action']=='continue'

def test_memory_changes_action_only_with_repeated_external_evidence():
 from flowevo_recovery.controller import select
 from flowevo_recovery.checks import feature_key
 f=features(state());f['truncated']=True
 rows=[dict(source_id=tid,feature_key=feature_key(f),action=a,recovered=a=='replan',additional_tokens=100) for tid in ('other1','other2') for a in ACTIONS]
 assert select('C',f,rows)['action']=='replan'
 assert len(select('C',f,rows)['memory_sources'])==2
 assert select('C',f,rows[:4])['action']=='continue'
 f['truncated']=False
 assert select('C',f,rows)['action'] is None

def test_free_adapter_uses_public_entrypoint_not_hidden_results():
 from flowevo_recovery.adapter_audit import extract_public_entrypoint
 text='```python\nassert f(1)==1\n```\n```python\ndef f(x): return x\n```\n```python\ndef f(x): return 0\n```'
 assert extract_public_entrypoint(text,['assert f(1)==1'])=='def f(x): return x'
 assert run_tests(extract_public_entrypoint(text,['assert f(1)==1']),['assert f(2)==2'])['passed']

def test_parallel_call_cap(tmp_path):
 import concurrent.futures as cf
 c=Client(tmp_path,'secret',cfg(),'code',transport=response)
 def work(i):
  try:c.complete(task(),'short',str(i),'test','retry');return True
  except BudgetStop:return False
 with cf.ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(work,range(12)))
 assert sum(out)==2 and c.calls==2 and c.actual==240
