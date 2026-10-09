import json,sys,random
from pathlib import Path
import sympy as s
import pytest
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.goal_v3.learning import discover,execute_program,certificate
from flowevo_bot.goal_v3.engine import solve
from flowevo_bot.goal_v3.runtime import solve_task
from flowevo_bot.schemas import ProblemView
from flowevo_bot.common import digest
from code_math.baseline import base_prompt

@pytest.fixture(scope='module')
def learned():
    rows=[json.loads(x) for x in (ROOT/'experiments/macro_discovery_pilot/data/clean_success_traces.jsonl').read_text().splitlines()]
    return rows,discover(rows)

def test_multisource_synthesis_and_replay(learned):
    traces,result=learned;bank=result['bank'];byid={r['task_id']:r for r in traces}
    assert {b['goal_kind'] for b in bank}=={'root_sum','root_product'}
    assert any(not c['universal_certificate']['passed'] for c in result['candidate_attempts'])
    for macro in bank:
        assert len(macro['source_task_ids'])>=2 and len(macro['structural_classes'])>=2
        assert certificate(macro['program'],macro['goal_kind'])['passed']
        for tid in macro['source_task_ids']:
            r=solve(byid[tid]['problem'],'automatic',bank);assert r['full_task_verified'],r

def test_learned_program_properties_zero_and_repeated_roots(learned):
    _,result=learned;rng=random.Random(570);x=s.Symbol('x')
    for macro in result['bank']:
        for n in range(2,7):
            for _ in range(12):
                roots=[rng.randrange(-5,6) for i in range(n)];lead=s.Rational(rng.choice([-5,-2,1,3]),rng.randrange(1,4));p=s.Poly(lead*s.prod(x-r for r in roots),x)
                wanted=sum(roots) if macro['goal_kind']=='root_sum' else s.prod(roots)
                assert execute_program(macro['program'],p)==wanted

def test_no_one_source_macro_admission(learned):
    _,result=learned;failed={r['goal_kind']:r['reason'] for r in result['failed_families']}
    assert 'pairwise_sum' in failed and 'polynomial_remainder' in failed
    assert not any(b['goal_kind']=='polynomial_remainder' for b in result['bank'])

class FakeClient:
    def __init__(self):self.prompts=[]
    def complete(self,prompt,job_id,code_hash):
        self.prompts.append(prompt)
        return {'response':{'choices':[{'message':{'content':'The answer is 0.'},'finish_reason':'stop'}]},'input_tokens':10,'output_tokens':20,'total_tokens':30,'latency':0.,'prompt_hash':digest(prompt),'call_id':'simulated_test'}

def problem(q):return ProblemView(task_id='synthetic_runtime_test',problem=q,subject='algebra',level='Level 1',public_metadata={'benchmark':'math'})

def test_abc_fallback_prompts_identical_and_partial_not_injected():
    p=problem('Find the positive roots of $x^3-x+1=0$.');client=FakeClient()
    for method in ['A_NoBank','B_Manual','C_Automatic']:
        record=solve_task(p,method,[],client,'fake');assert record['api_call_count']==1 and not record['full_task_verified']
    assert client.prompts==[base_prompt(p)]*3

def test_c_does_not_impersonate_b(learned):
    _,result=learned;p=problem('Find the remainder when $x^3+1$ is divided by $x+1$.');client=FakeClient()
    b=solve_task(p,'B_Manual',result['bank'],client,'fake');c=solve_task(p,'C_Automatic',result['bank'],client,'fake')
    assert b['full_task_verified'] and b['api_call_count']==0
    assert not c['full_task_verified'] and c['api_call_count']==1 and c['fallback_reason']=='no_certified_automatic_macro'

def test_c_qualified_goal_skips_llm(learned):
    _,result=learned;p=problem('Find the product of the roots of $2x^3-3x+4=0$.');client=FakeClient()
    record=solve_task(p,'C_Automatic',result['bank'],client,'fake')
    assert record['full_task_verified'] and record['api_call_count']==0 and not client.prompts and record['answer']=='-2'
