import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from select_candidates import choose,public_certificate

def c(n,answer,finish='stop'):
 return {'job_id':f'synthetic_c{n}','candidate':n,'response_hash':str(n),'content':f'The answer is \\boxed{{{answer}}}.','reasoning':'','finish_reason':finish,'syntactic_complete':finish=='stop'}
def test_math_equivalent_majority_not_string_vote():
 r=choose('What is the value?', [c(1,'3'),c(2,r'\frac{1}{2}'),c(3,'0.5'),c(4,r'\frac{2}{4}')])
 assert r['selections']['majority']==2 and [2,3,4]in r['equivalence_groups']
def test_full_public_expression_certificate_overrides_wrong_majority():
 r=choose('Compute $2+2$.',[c(1,'9'),c(2,'9'),c(3,'9'),c(4,'4')])
 assert r['selections']=={'first':1,'majority':1,'verification':4}
 assert r['candidate_diagnostics'][-1]['verification_status']=='certified_answer'
def test_embedded_expression_is_not_full_problem_certificate():
 assert public_certificate('A student computes $2+2$. What is the number of students?')is None
def test_incomplete_excluded_from_majority():
 r=choose('What is the value?',[c(1,'9','length'),c(2,'9','length'),c(3,'4'),c(4,'4')])
 assert r['selections']['first']==1 and r['selections']['majority']==3
 assert r['candidate_diagnostics'][0]['parse_status']=='incomplete'
def test_unsupported_text_not_claimed_verified():
 r=choose('How many objects?', [c(1,'possibly'),c(2,'4')])
 assert r['selections']['majority']==2
 assert all(d['verification_status']=='insufficient_evidence'for d in r['candidate_diagnostics'])
@pytest.mark.parametrize('field',['reference_raw','gold','correct','evaluator_status'])
def test_label_fields_rejected(field):
 with pytest.raises(ValueError):choose('What is the value?',[dict(c(1,'1'),**{field:'CANARY'})])
def test_tie_earliest_candidate():
 r=choose('What is the value?', [c(4,'2'),c(3,'1'),c(2,'2'),c(1,'1')]);assert r['selections']['majority']==1
def test_reference_engine_not_imported():
 assert 'math_evaluation.engine'not in sys.modules and 'math_evaluation.reference'not in sys.modules
 assert '_flowevo_v3_public_parser.reference'not in sys.modules
def test_untrusted_answer_rejected_without_execution():
 r=choose('What is the value?',[c(1,"__import__('os').system('false')"),c(2,'4')])
 assert r['selections']['majority']==2
