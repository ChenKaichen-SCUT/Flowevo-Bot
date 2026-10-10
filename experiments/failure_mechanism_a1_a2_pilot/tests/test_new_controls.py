import sys,json,subprocess,threading,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3];CODE=Path(__file__).resolve().parents[1]/'code';sys.path.insert(0,str(CODE))
from common import read,jl,save,digest
from run_pilot import Runner,BudgetStop,request_for,require_public,consume_sse,decide
from math_control import goal_spec,check_goal,candidate_events,finalization_decision
from math_control.prompts import intervention_prompt

def config(**kwargs):return dict({'max_total_tokens':30000,'max_calls':10,'api_workers':4,'gold_feedback':False,'skill_injection':False,'model':'test','system_prompt':'You are an expert programmer and mathematician.'},**kwargs)
def entry(q='Compute $2+2$.'):return {'task_id':'new_test','problem':q,'subject':'algebra','level':'Level 1','prompt':'Problem: '+q+'\n\nSolve step by step. End with: The answer is [your answer].'}
def response(reason='',text='The answer is 4.',finish='stop'):return {'id':'fixture','model':'fixture','choices':[{'message':{'content':text,'reasoning_content':reason},'finish_reason':finish}],'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30,'completion_tokens_details':{'reasoning_tokens':10}}}

@pytest.mark.parametrize('field',['gold','reference_raw','correct','solution','reference_answer'])
def test_reject_nonpublic_fields(field):
 e=entry();e[field]='GOLD_CANARY'
 with pytest.raises(ValueError):require_public(e)

def test_public_parser_does_not_import_grading():
 code="import sys;sys.path.insert(0,"+repr(str(ROOT/'FlowEvo/src'))+");import math_control;assert not any(x.endswith(('.reference','.engine','.equivalence')) for x in sys.modules if 'math_evaluation' in x or '_flowevo_v3_public' in x)"
 subprocess.run([sys.executable,'-c',code],check=True)

@pytest.mark.parametrize('key',['gold_feedback','skill_injection'])
def test_forbidden_config(key):
 cfg=config();cfg[key]=True
 with pytest.raises(ValueError):request_for('prompt',cfg,4096)

def test_goal_object_drift():
 q='The product of four consecutive positive integers is 24 more than a perfect square. What is the sum of the four smallest such integers with product greater than 1000?'
 g=goal_spec(q);assert g.target_object=='4 consecutive integers';assert g.target_operation=='sum';assert g.answer_cardinality==1
 assert check_goal(q,'The four smallest such starting integers are 6, 11, 16, 21. Their sum is 54. The answer is 54.')['high_confidence_mismatch']
 assert not check_goal(q,'Do not sum the starting integers. The smallest starting value is 6; the required sum is 6+7+8+9=30. The answer is 30.')['high_confidence_mismatch']

@pytest.mark.parametrize('q,answer', [('A rope is 280 m and can be reduced to 120 m. Determine the greatest length of rope that can be saved.','The answer is \\(\\boxed{160}\\) m.'),('A rectangle has length 12 meters. What is the area of the shaded regions? Express your answer in simplest radical form.','The answer is \\(\\boxed{8\\sqrt3}\\) square meters.')])
def test_optional_units_do_not_trigger(q,answer):assert not check_goal(q,answer)['high_confidence_mismatch']

def test_late_candidate_finalization_is_new_request():
 q=entry()['problem'];reason='Derive 2+2. '*50+'The answer is 4.\nLet me verify.\nThe answer is 4.';r=response(reason,'','length')
 d=finalization_decision(q,r,{'retry_required':True});assert d['trigger'];assert not d['interrupted_generation'];assert d['candidate_is_not_verified_correct']
 p=intervention_prompt(entry()['prompt'],'a1','',reason,d);assert 'NEW request' in p and 'may be wrong' in p

def test_completed_answers_not_interrupted():assert not finalization_decision(entry()['problem'],response('The answer is 4.'),{'retry_required':False})['trigger']

def test_untyped_prose_not_candidate():assert not finalization_decision(entry()['problem'],response('The answer is perhaps undecidable.','','length'),{'retry_required':True})['trigger']

def test_early_candidate_not_triggered():assert not finalization_decision(entry()['problem'],response('The answer is 4.\n'+'Consider a new issue. '*100,'','length'),{'retry_required':True})['trigger']

def test_resume_does_not_repeat_request(tmp_path):
 calls=[];runner=Runner(config(),lambda p:calls.append(p) or response(),tmp_path,False)
 a=runner.call(entry(),'b0',4096);b=runner.call(entry(),'b0',4096);assert a==b;assert len(calls)==1;assert runner.actual==30
 runner2=Runner(config(),lambda p:pytest.fail('duplicate HTTP'),tmp_path,False);runner2.call(entry(),'b0',4096);assert runner2.actual==30
 with pytest.raises(ValueError):runner2.call(entry(),'b0',8192)

def test_pending_ambiguous_billing_blocks_resume(tmp_path):
 (tmp_path/'raw').mkdir();(tmp_path/'raw/x.pending.json').write_text('{}')
 with pytest.raises(RuntimeError):Runner(config(),lambda p:response(),tmp_path,False)

@pytest.mark.parametrize('lim,value',[('max_calls',1),('max_total_tokens',4800)])
def test_global_caps(tmp_path,lim,value):
 cfg=config();cfg[lim]=value;r=Runner(cfg,lambda p:response(),tmp_path,False);r.call(entry(),'b0',4096)
 with pytest.raises(BudgetStop):r.call(entry(),'b2',16384)
 assert r.calls==1 and r.actual==30

def test_failure_does_not_silently_retry(tmp_path):
 calls=[]
 def fail(req):calls.append(req);raise TimeoutError()
 r=Runner(config(),fail,tmp_path,False)
 with pytest.raises(RuntimeError):r.call(entry(),'b0',4096)
 assert len(calls)==1 and list((tmp_path/'raw').glob('*.pending.json'))

def test_concurrent_identical_job_is_deduplicated(tmp_path):
 import concurrent.futures as cf
 calls=[]
 def transport(p):calls.append(p);time.sleep(.05);return response()
 r=Runner(config(),transport,tmp_path,False)
 with cf.ThreadPoolExecutor(4) as pool:results=list(pool.map(lambda _:r.call(entry(),'b0',4096),range(4)))
 assert len(calls)==1 and r.actual==30

def test_api_concurrency_reservation(tmp_path):
 import concurrent.futures as cf
 cfg=config();cfg['api_workers']=2
 def transport(p):time.sleep(.03);return response()
 r=Runner(cfg,transport,tmp_path,False)
 with cf.ThreadPoolExecutor(6) as pool:list(pool.map(lambda i:r.call(entry(),str(i),100),range(6)))
 assert r.peak<=2 and r.calls==6

def test_stream_separate_text_and_actual_usage(tmp_path):
 class Stream:
  def iter_lines(self,decode_unicode=True):
   parts=[{'id':'s','choices':[{'delta':{'reasoning_content':'The answer is 4.'}}]}, {'choices':[{'delta':{'content':'The answer is 4.'},'finish_reason':'stop'}]}, {'choices':[],'usage':response()['usage']}]
   return iter(['data: '+json.dumps(p) for p in parts]+['data: [DONE]'])
 data,ev=consume_sse(Stream(),tmp_path/'stream.txt',time.perf_counter());assert data['usage']['total_tokens']==30;assert ev['observed_during_generation'] and not ev['cancelled'];assert ev['events'][0]['content_chars']==0

def test_missing_stream_usage_is_failure(tmp_path):
 class Stream:
  def iter_lines(self,decode_unicode=True):return iter(['data: [DONE]'])
 with pytest.raises(RuntimeError):consume_sse(Stream(),tmp_path/'s',time.perf_counter())

def test_no_label_file_reads_in_online_decision_or_request(tmp_path,monkeypatch):
 original=Path.read_text
 def guarded(path,*a,**kw):
  assert not any(x in str(path) for x in ['offline_labels','evaluator_v3_results','test.jsonl','train.jsonl']);return original(path,*a,**kw)
 monkeypatch.setattr(Path,'read_text',guarded)
 e=entry();rr={'response':response(),'completion':{'retry_required':False},'response_hash':'sealed'}
 d=decide((e,rr));assert not d['reference_access'];r=Runner(config(),lambda p:response(),tmp_path,False);r.call(e,'b0',4096)
 assert 'GOLD_CANARY' not in json.dumps(r.config)

def test_explicit_unit_constraint_still_detected():
 assert check_goal('Find the length in meters.','The answer is 4 feet.')['high_confidence_mismatch']
