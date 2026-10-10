import sys,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from generate import Runner,request_for,BudgetStop
from common import read
def cfg():return {'model':'deepseek-flash','system_prompt':'You are an expert programmer and mathematician.','gold_feedback':False,'skill_injection':False,'gold_reflection':False,'max_total_tokens':100000,'max_http_attempts':8,'max_attempts_per_job':2}
def entry():return {'task_id':'synthetic','problem':'Compute 2+2.','subject':'algebra','level':'synthetic','prompt':'Problem: Compute 2+2.\n\nSolve step by step. End with: The answer is [your answer].'}
def response():return {'id':'fake','model':'synthetic','choices':[{'message':{'content':'The answer is [4].','reasoning_content':''},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':30,'total_tokens':50}}
def test_public_schema_rejects_gold():
 with pytest.raises(ValueError):request_for(dict(entry(),answer='4'),cfg())
@pytest.mark.parametrize('key',['gold_feedback','gold_reflection','skill_injection'])
def test_forbidden_context(key):
 c=cfg();c[key]=True
 with pytest.raises(ValueError):request_for(entry(),c)
def test_saved_success_reused_without_call(tmp_path):
 seen=[];r=Runner(cfg(),tmp_path,lambda q:(seen.append(q)or response()));a=r.call(entry(),1);b=r.call(entry(),1)
 assert a==b and len(seen)==1 and r.actual==50
 assert request_for(entry(),cfg())['max_tokens']==16384
def test_transport_recovery_has_unknown_charge(tmp_path,monkeypatch):
 monkeypatch.setattr('generate.time.sleep',lambda x:None);seen=[]
 def send(q):
  seen.append(q)
  if len(seen)==1:raise ConnectionError()
  return response()
 r=Runner(cfg(),tmp_path,send);r.call(entry(),1)
 assert r.calls==2 and r.actual==50 and r.unknown>16384
 restored=Runner(cfg(),tmp_path,lambda q:pytest.fail('unexpected call'));restored.call(entry(),1)
 assert restored.calls==2 and restored.actual==50 and restored.unknown==r.unknown
def test_hard_cap_does_not_send(tmp_path):
 c=cfg();c['max_total_tokens']=1;r=Runner(c,tmp_path,lambda q:pytest.fail('budget bypass'))
 with pytest.raises(BudgetStop):r.call(entry(),1)
def test_no_math_incorrectness_retry(tmp_path):
 seen=[]
 def send(q):
  seen.append(q);x=response();x['choices'][0]['message']['content']='The answer is [999].';return x
 r=Runner(cfg(),tmp_path,send);r.call(entry(),1)
 assert len(seen)==1
def test_truncation_does_not_retry(tmp_path):
 seen=[]
 def send(q):
  seen.append(q);x=response();x['choices'][0]['finish_reason']='length';return x
 r=Runner(cfg(),tmp_path,send);a=r.call(entry(),1)
 assert len(seen)==1 and a['completion']['retry_required']
