import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'FlowEvo/src'))
from dataclasses import replace
import pytest
from math_evaluation import MathEvaluatorV3,AnswerSpec,EvaluatorConfig
from math_evaluation.extraction import extract_model
from math_evaluation.reference import build_reference
from math_evaluation.normalization import normalize
from math_evaluation.equivalence import compare

CFG=EvaluatorConfig()

def assess(pred,gold,spec=None,question='Compute the requested value.',**kwargs):
    rec=dict(task_id='synthetic',question=question,prediction_raw='The answer is '+pred,reference_raw=r'The result is \boxed{'+gold+'}.',finish_reason='stop',submission_sealed=True)
    rec.update(kwargs)
    return MathEvaluatorV3().evaluate(rec,spec or AnswerSpec(kind='expression'))

@pytest.mark.parametrize('pred,gold,spec',[
    ('13',r'\text{13}',AnswerSpec(kind='expression')),
    ('odd',r'\text{odd}',AnswerSpec(kind='choice',choices=('odd','even','neither'))),
    (r'\{-2,1\pm\sqrt{5}\}',r'\{1-\sqrt{5},-2,1+\sqrt{5}\}',AnswerSpec(kind='finite_set',all_solutions=True)),
    (r'-4\le k<0','[-4,0)',AnswerSpec(kind='interval',target='k')),
    ('45 mph',r'45\text{ mph}',AnswerSpec(kind='quantity',unit='mi/h')),
    ('100 cm','1 m',AnswerSpec(kind='quantity',unit='m',allow_unit_conversion=True)),
    ('20%','20',AnswerSpec(kind='percentage',percent_mode='percent_number')),
    ('20%','0.2',AnswerSpec(kind='expression')),
    ('(A)','A',AnswerSpec(kind='choice',choices=('A','B','C'))),
    ('2(x+1)','2x+2',AnswerSpec(kind='polynomial')),
    (r'\frac{x^2-1}{x-1}',r'\frac{(x-1)(x+1)}{x-1}',AnswerSpec(kind='expression')),
    ('(1,2)','(1,2)',AnswerSpec(kind='tuple')),
    (r'\frac12\begin{pmatrix}2\\4\end{pmatrix}',r'\begin{bmatrix}1\\2\end{bmatrix}',AnswerSpec(kind='matrix')),
    ('y=2x+3','2y=4x+6',AnswerSpec(kind='equation')),
    (r'25\(_6\)','25_6',AnswerSpec(kind='base_numeral',base=6)),
    ('1.36','1.363636',AnswerSpec(kind='expression',decimal_places=2)),
])
def test_equivalent(pred,gold,spec):
    r=assess(pred,gold,spec);assert r['status']=='correct',r

@pytest.mark.parametrize('pred,gold,spec',[
    ('[-4,0]','[-4,0)',AnswerSpec(kind='interval')),
    ('{1}','{1,2}',AnswerSpec(kind='finite_set',all_solutions=True)),
    ('1+sqrt(5)',r'1\pm\sqrt5',AnswerSpec(kind='finite_set',all_solutions=True)),
    ('20%','20',AnswerSpec(kind='expression')),
    ('0.2','20',AnswerSpec(kind='percentage',percent_mode='percent_number')),
    ('45 km/h','45 mph',AnswerSpec(kind='quantity',unit='mi/h')),
    ('45 km/h','45 mph',AnswerSpec(kind='quantity',allow_unit_conversion=True)),
    ('(2,1)','(1,2)',AnswerSpec(kind='tuple')),
    ('x/x','1',AnswerSpec(kind='expression')),
    ('sqrt(x^2)','x',AnswerSpec(kind='expression')),
    ('log(x^2)','2 log(x)',AnswerSpec(kind='expression')),
    ('13 garbage','13',AnswerSpec(kind='expression')),
    ("__import__('os').system('echo nope')",'1',AnswerSpec(kind='expression')),
    ('999999!','1',AnswerSpec(kind='expression')),
    ('25_7','25_6',AnswerSpec(kind='base_numeral',base=6)),
    ('x=1','y=1',AnswerSpec(kind='equation')),
])
def test_reject_near_misses(pred,gold,spec):assert assess(pred,gold,spec)['status']!='correct'

def test_final_visible_wrong():
    r=assess('1','1',prediction_raw='Intermediate value: 1.\nThe answer is 2.')
    assert r['status']=='incorrect'

def test_length_never_credits_even_box():assert assess(r'\boxed{1}','1',finish_reason='length')['status']=='prediction_incomplete'
def test_reasoning_hidden():assert assess('','1',prediction_raw='',reasoning_content='The answer is 1')['status']=='prediction_incomplete'
def test_unsealed():assert assess('1','1',submission_sealed=False)['status']=='unknown'
def test_example_only():assert assess('','1',prediction_raw='For example the answer is 1')['status']!='correct'
def test_nested_box():assert assess(r'\boxed{\frac{1}{2}}',r'\frac12')['status']=='correct'
def test_all_reference_roots():
    ref='We solve and obtain $x=\\boxed{3}$ or $x=\\boxed{2/5}$.'
    spec=AnswerSpec(kind='finite_set',target='x',all_solutions=True)
    r=assess('{2/5,3}','',spec,reference_raw=ref);assert r['status']=='correct',r
    assert assess('3','',spec,reference_raw=ref)['status']=='incorrect'
def test_intermediate_box_not_final():
    r=assess('3','',reference_raw='An intermediate value is \\boxed{9}.\nThe answer is 3.')
    assert r['status']=='correct',r

def test_ambiguous_disconnected_boxes():
    r=assess('{1,2}','',AnswerSpec(kind='finite_set',all_solutions=True),reference_raw='One thing is \\boxed{1}.\n\nAnother is \\boxed{2}.')
    assert r['status']=='reference_ambiguous'
def test_different_variable_intermediate_not_merged():
    r=assess('{1,2}','',AnswerSpec(kind='finite_set',target='x',all_solutions=True),reference_raw=r'An intermediate $y=\boxed{9}$. The roots are $x=\boxed{1}$ or $x=\boxed{2}$.')
    assert r['status']=='correct',r

def test_unknown_question():
    r=assess('1','1',AnswerSpec());assert r['status']=='unknown'
def test_extractor_has_no_gold_parameter():
    import inspect
    assert tuple(inspect.signature(extract_model).parameters)==('text','finish_reason','spec')
def test_task_id_invariance():
    a=assess('2','2',task_id='math_test_secret_99');b=assess('2','2',task_id='anything')
    assert a['status']==b['status']=='correct'
def test_batch_network_and_limit():
    records=[dict(task_id=str(i),question='Compute 1+1.',prediction_raw='The answer is 2.',reference_raw=r'\boxed{2}',finish_reason='stop',submission_sealed=True) for i in range(4)]
    assert all(x['status']=='correct' for x in MathEvaluatorV3(EvaluatorConfig(workers=2)).evaluate_batch(records))

@pytest.mark.parametrize('text,expected',[
    ('Therefore 1.\n\nThe final result is \\boxed{2}.','incorrect'),
    ('For example, \\boxed{1}.','unknown'),
    ('<think>The answer is 1</think>\nThe answer is 2.','incorrect'),
    ('The answer is \\boxed{1','prediction_incomplete'),
])
def test_final_submission_boundaries(text,expected):assert assess('','1',prediction_raw=text)['status']==expected

def test_multiline_roots():
    r=assess('','{1,2}',AnswerSpec(kind='finite_set',target='x',all_solutions=True),prediction_raw='Answer:\nx=\\boxed{1}\nx=\\boxed{2}')
    assert r['status']=='correct',r

def test_explicit_intermediate_reference_box():
    assert assess('2','',reference_raw='Intermediate sum is \\boxed{9}.\n\nThe final result is \\boxed{2}.')['status']=='correct'

@pytest.mark.parametrize('x,y',[(3,5),(7,-2),(-3,9),(-11,-6)])
def test_public_parity_witness(x,y):
    q=f'The graph passes through the point ({x},{y}). If f is an odd function, what other point must the graph pass through?'
    assert assess(f'({-x},{-y})','(0,0)',AnswerSpec(kind='tuple'),question=q)['status']=='correct'
    assert assess(f'({-x},{y})','(0,0)',AnswerSpec(kind='tuple'),question=q)['status']!='correct'

def test_wrong_area_direction():
    q='A 101 by 101 square has its length decreased by 7 and its width increased by 7. By how much does its area change?'
    spec=AnswerSpec(kind='quantity',unit='unit^2')
    assert assess('49 square units less','49',spec,question=q)['status']=='correct'
    assert assess('49 square units more','49',spec,question=q)['status']=='incorrect'

def test_unknown_spec_safety():
    from math_evaluation.spec import infer_spec
    assert infer_spec('How many ordered pairs (x,y) satisfy these constraints?').kind=='expression'
    assert infer_spec('What is the area of triangle ABC?').kind=='quantity'
    assert infer_spec('Find the equation of the curve. (Enter it in standard form.)').kind=='equation'
    assert infer_spec('Find the maximum angle between two vectors, in degrees.').kind=='quantity'
    assert infer_spec('Use your judgment.').uncertain

def test_native_adapter_complete_solution():
    from math_evaluation.adapters import from_flowevo_task,OfflineScoringConfig
    from types import SimpleNamespace
    task=SimpleNamespace(task_id='native',benchmark='math',prompt='Find all real roots x.',text='',canonical_solution=r'The roots are $x=\boxed{1}$ and $x=\boxed{2}$.',metadata={'gold_answer':'2'})
    rec=from_flowevo_task(task,{'task_id':'native','solution':'The answer is {1,2}.'},submission_sealed=True)
    assert MathEvaluatorV3().evaluate(rec)['status']=='correct'
    assert rec['finish_reason'] is None and rec['source_metadata']['finish_reason_available'] is False
    assert OfflineScoringConfig().evaluator=='legacy'
    assert MathEvaluatorV3().evaluate(from_flowevo_task(task,{'task_id':'native','solution':'The answer is {1,2}.'}))['status']=='unknown'

def test_bounded_runtime():
    r=MathEvaluatorV3(EvaluatorConfig(timeout_seconds=0.000001)).evaluate(dict(task_id='timeout',question='Compute 1+1.',prediction_raw='2',reference_raw=r'\boxed{2}',submission_sealed=True))
    assert r['status']=='unknown' and r['elapsed_seconds']<1

@pytest.mark.parametrize('a,b',[(2,3),(7,11),(-5,13),(19,-2)])
def test_nontrivial_identity_and_counterexample(a,b):
    assert assess(f'(x+({a}))*(x+({b}))',f'x^2+({a+b})*x+({a*b})')['status']=='correct'
    assert assess(f'(x+({a}))*(x+({b}))',f'x^2+({a+b})*x+({a*b+1})')['status']=='incorrect'
