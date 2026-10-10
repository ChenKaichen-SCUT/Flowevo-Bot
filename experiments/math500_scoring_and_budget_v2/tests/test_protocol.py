from pathlib import Path
import sys,json,ast
import pytest
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
sys.path.insert(0,str(OUT/'code'))
from completion import detect
from run_experiment import request_for,require_public
from evaluators import FixedEvaluator

def response(text='',reason='stop',tokens=20):return {'choices':[{'message':{'content':text},'finish_reason':reason}],'usage':{'completion_tokens':tokens}}

@pytest.mark.parametrize('text,reason,tokens,retry',[
 ('The answer is 99.','stop',100,False),
 ('The answer is 99.','length',4096,True),
 ('','stop',100,True),
 ('Some reasoning but no final answer','stop',100,True),
 (r'The answer is \boxed{\frac{1}{2}}.','stop',100,False),
 (r'The answer is \boxed{\frac{1}{2}','stop',100,True),
 (r'Final answer: \(1,2\).','stop',100,False),
 ('The required result equals 8.','stop',100,True),
 ('The answer is 2.','stop',4096,True),
 ('The answer is 2.','content_filter',100,True),
])
def test_detection(text,reason,tokens,retry):assert detect('t',response(text,reason,tokens),4096)['retry_required']==retry

def test_no_correctness_input():
 for truth in (False,True,None):
  r=response('The answer is 999.');r['offline_correct']=truth
  assert not detect('t',r,4096)['retry_required']

def test_config_and_prompt_boundary():
 c=json.loads((OUT/'config.json').read_text());e={'task_id':'t','prompt':'PUBLIC_CANARY','gold_exposed':False,'skill_injected':False,'skill_retrieval_count':0}
 require_public(e)
 with pytest.raises(ValueError):require_public({**e,'reference_solution':'GOLD_CANARY'})
 for field in ('skill_injection','history_retrieval','gold_answer_feedback','gold_driven_reflection','correctness_retries'):
  with pytest.raises(ValueError):request_for(e['prompt'],{**c,field:True},4096)
 a=request_for(e['prompt'],c,4096);b=request_for(e['prompt'],c,8192)
 assert [k for k in a if a[k]!=b[k]]==['max_tokens']
 assert a['messages'][1]['content']=='PUBLIC_CANARY' and 'GOLD_CANARY' not in json.dumps(a)

def test_online_source_has_no_scorer_or_label_access():
 for name in ('run_experiment.py','completion.py'):
  text=(OUT/'code'/name).read_text();tree=ast.parse(text)
  for node in ast.walk(tree):
   if isinstance(node,(ast.Import,ast.ImportFrom)):
    assert not any(s in (getattr(node,'module','') or '') for s in ('evaluators','math_scoring','experiment_grader'))
  assert 'offline_labels' not in text and 'gold_answer]' not in text

def test_dataset_matches_historical_strata_without_known_exposure():
 d=json.loads((OUT/'dataset_manifest.json').read_text());used=set(json.loads((OUT/'evidence/exposure_registry.json').read_text())['excluded_ids'])
 assert d['count']==500 and len({x['task_id'] for x in d['tasks']})==500
 assert not used & {x['task_id'] for x in d['tasks']}
 assert all(x['historical_count']==x['new_count'] for x in d['strata'])
 assert all(x['source_split']=='test' for x in d['tasks'])

def test_regression_counts():
 assert json.loads((OUT/'evaluator_regression.json').read_text())['counts']=={'legacy_correct':464,'fixed_correct':473,'nine_fixed':9,'original_true_lost':0}

@pytest.mark.parametrize('p,g,q',[
 ('(4,7)','(7,4)','Give an ordered pair.'),
 ('[2,6)','(2,6)','Find the interval.'),
 (r'\{2,3\}',r'\{2,3,4\}','Find the set.'),
 ('-13','13','Find the value.'),
 (r'\sqrt{x^2}','x','For real x, simplify.'),
 ('x/x','1','Preserve the domain.'),
 ('0.125','12.5','What percent?'),
 ('9 kilograms','9','How many grams?'),
])
def test_extra_false_positive_counterexamples(p,g,q):
 r=FixedEvaluator.score({'task_id':'unseen','solution':'The answer is '+p+'.','gold_answer':g,'question':q,'truncated':False})
 assert r['correct'] is not True
