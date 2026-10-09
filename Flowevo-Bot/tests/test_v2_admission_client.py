import importlib.util
from pathlib import Path
import pytest
from flowevo_bot.v2.admission import decide,route_reason
from flowevo_bot.v2.skills import MacroSkill,trigger_for,guards_for
from flowevo_bot.v2.client import Client,Budget
from flowevo_bot.schemas import ProblemView
from code_math.baseline import base_prompt

def skill():
    return MacroSkill(skill_id='S04_test',predecessor='old',subject='counting_probability',name='Test macro',
        steps=['Partition finite objects into disjoint cases.','Multiply conditional choices, then add.'],
        compact_prompt='Check order/repeats; count disjoint exhaustive cases and overlaps; divide symmetry only with equal orbit size.',
        trigger=trigger_for('S04'),guards=guards_for('S04'),source_task_ids=['s1','s2','s3'],
        source_trace_hashes=['a','b','c'],transformation_evidence=[])

def pairs(n=10,**change):
    return [dict(task_id=str(i),base_correct=True,skill_correct=True,base_tokens=900,skill_tokens=500,
                 structurally_distinct=True,problem_tokens=80,**change) for i in range(n)]

def test_missing_evidence_shadow_and_no_router_cold_start_deadlock():
    s,d=decide(skill(),[],independent=False)
    assert s.status=='shadow' and 'independent_dev' in d['blocked_by']
    s,d=decide(skill(),pairs(),independent=True,build_cost=2000)
    assert s.status=='active'  # new skill can be validated without production usage
    assert route_reason(s).startswith('base: independent sample') # unchanged n>=40

def test_harm_unknown_and_math_failure_distinct():
    ps=pairs();ps[0]['skill_correct']=False
    s,d=decide(skill(),ps,independent=True);assert s.status=='quarantine'
    ps[0]['skill_correct']=None
    s,d=decide(skill(),ps,independent=True);assert s.status=='shadow'
    assert 'complete_scoring' in d['blocked_by']
    s,d=decide(skill(),pairs(),independent=True,mathematically_reviewed=False);assert s.status=='quarantine'

def test_cost_and_source_no_threshold_relaxation():
    ps=pairs()
    for r in ps:r['skill_tokens']=1000
    assert decide(skill(),ps,independent=True)[0].status=='shadow'
    assert decide(skill(),pairs(9),independent=True)[0].status=='shadow'
    assert decide(skill(),pairs(),independent=True,source_consistent=False)[0].status=='candidate'
    assert decide(skill(),pairs(),independent=True,build_cost=40000)[0].status=='shadow'

def test_active_certificate_tamper():
    s,_=decide(skill(),pairs(),independent=True)
    raw=s.model_dump();raw['compact_prompt']='changed'
    with pytest.raises(ValueError,match='certificate'):MacroSkill.model_validate(raw)

def mock_response(request):
    return 200,{'id':'fake','model':'unit','choices':[{'message':{'content':'The answer is 3.'},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':10,'completion_tokens':12,'total_tokens':22}}

def test_budget_resume_and_safe_logs(tmp_path):
    calls=[]
    def transport(r):calls.append(r);return mock_response(r)
    client=Client(tmp_path,'SENSITIVE_CANARY',Budget(max_calls=2,max_tokens=10000),transport)
    a=client.complete('Question only',job_id='one',purpose='shadow_validation')
    b=client.complete('Question only',job_id='one',purpose='shadow_validation')
    assert a==b and len(calls)==1
    assert 'SENSITIVE_CANARY' not in next(tmp_path.glob('*.json')).read_text()
    with pytest.raises(RuntimeError,match='budget'):client.complete('x',job_id='two',purpose='shadow_validation')

def test_uncertain_timeout_not_blindly_retried(tmp_path):
    def transport(r):raise TimeoutError('secret-bearing provider error')
    client=Client(tmp_path,'secret',Budget(),transport)
    with pytest.raises(RuntimeError,match='Transport failure'):client.complete('x',job_id='one',purpose='shadow_validation')
    client.transport=mock_response
    with pytest.raises(RuntimeError,match='Uncertain prior request'):client.complete('x',job_id='one',purpose='shadow_validation')

def test_fallback_prompt_identical_and_question_only():
    path=Path(__file__).resolve().parents[1]/'scripts/run_v2_research.py'
    spec=importlib.util.spec_from_file_location('v2_runner_test',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    p=ProblemView(task_id='test',problem='How many arrangements?',subject='counting_probability')
    assert m.solver_prompt(p,None)==base_prompt(p)
    assert 'GOLD_CANARY' not in m.solver_prompt(p,skill().compact_prompt)
