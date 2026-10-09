import sys,json,random
from pathlib import Path
import pytest
import sympy as s
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.rmmd.macros import inspect_question,trigger_logic,COMPACT
from flowevo_bot.rmmd.client import Budget,Client
from flowevo_bot.v2.evaluator import seal,assert_sealed

def test_source_self_match():
    rows=[json.loads(x) for x in (ROOT/'experiments/macro_discovery_pilot/data/clean_success_traces.jsonl').read_text().splitlines()];byid={r['task_id']:r for r in rows}
    bank=json.loads((ROOT/'experiments/macro_discovery_pilot/data/macro_skill_bank.json').read_text())
    for macro in bank:
        assert len(macro['source_task_ids'])>=2
        assert (len(COMPACT[macro['macro_id']].encode())+3)//4<=100
        for tid in macro['source_task_ids']:assert inspect_question(byid[tid]['problem'],macro['macro_id'])['execution_verified']

@pytest.mark.parametrize('question',[
 'Find the remainder when $x^2+1$ is divided by $0$.',
 'Find the remainder when $x^2+1$ is divided by $y+1$.',
 'Find the remainder when $x^2+a$ is divided by $x+1$.',
 'Find the remainder when $1/x$ is divided by $x+1$.',
 'Find the remainder when $x^{10000}$ is divided by $x+1$.',
 'Find the remainder when $x^3+1$ is divided by $x+1$, then evaluate it at 2.',
 'If $x^2=4$, find $x$.',
 'Find the remainder when $x^2$ is divided by $(x+1)^{20}$.',
])
def test_remainder_reject(question):assert not inspect_question(question,'polynomial_remainder')['full_task_verified']

def test_repeated_factor_not_value_only():
    r=inspect_question('Find the remainder when $x^4+2$ is divided by $(x-2)^2$.','polynomial_remainder')
    assert r['full_task_verified'] and s.sympify(r['output_structure']['remainder'])==32*s.Symbol('x')-46
    assert r['certificate']['independent_recurrence']

def test_root_domain_and_local_scope():
    for q in ['Find the sum of the roots of $x^2-4x+3=0$.','Find the sum of the reciprocals of the roots of $x^3-x^2=0$.']:
        r=inspect_question(q,'root_invariants');assert r['execution_verified'];assert not r['full_task_verified'];assert r['direct_answer'] is None
    for q in ['Find the sum of the rational roots of $x^3-x+1=0$.','Find the sum of the roots of $a*x^2+x+1=0$.','Find the sum of the real roots of $x^4-x+1=0$.']:
        assert not inspect_question(q,'root_invariants')['execution_verified']

def test_property_remainders_qq_and_backsubstitution():
    rng=random.Random(1701);x=s.Symbol('x')
    for _ in range(50):
        degree=rng.randrange(1,9);dd=rng.randrange(1,5)
        p=sum(s.Rational(rng.randrange(-8,9),rng.randrange(1,4))*x**i for i in range(degree+1))+x**degree
        d=x**dd+sum(rng.randrange(-4,5)*x**i for i in range(dd))
        if p==0 or not p.has(x):continue
        r=inspect_question(f'Find the remainder when ${s.latex(p)}$ is divided by ${s.latex(d)}$.','polynomial_remainder')
        assert r['full_task_verified'],r
        answer=s.sympify(r['output_structure']['remainder']);q=s.sympify(r['output_structure']['quotient'])
        for value in [-3,0,2,s.Rational(1,3)]:assert s.expand(p-q*d-answer).subs(x,value)==0

def test_property_root_sums_known_multisets_no_extraneous_roots():
    rng=random.Random(41);x=s.Symbol('x')
    for n in range(2,7):
        for _ in range(5):
            roots=[rng.randrange(-4,5) for i in range(n)];p=s.prod(x-r for r in roots)
            r=inspect_question(f'Find the sum of all the roots of ${s.latex(s.expand(p))}=0$.','root_invariants')
            assert r['execution_verified'],r
            assert list(map(s.sympify,r['output_structure']['power_sums']))==[sum(v**k for v in roots) for k in range(1,n+1)]
            assert not r['full_task_verified']

def test_and_or_guards():
    node={'all_of':[{'feature':'a'},{'any_of':[{'feature':'b'},{'feature':'c'}]},{'guard':'verified'}]}
    assert trigger_logic(node,dict(a=True,c=True,verified=True))
    assert not trigger_logic(node,dict(a=True,c=True))
    assert not trigger_logic(node,dict(a=False,b=True,verified=True))

def test_no_gold_dependency():
    import inspect,flowevo_bot.rmmd.macros as m
    source=inspect.getsource(m)
    assert 'gold_answer' not in source and 'labels.jsonl' not in source
    q='Find the remainder when $x^3+1$ is divided by $x+1$.'
    r=m.inspect_question(q,'polynomial_remainder');assert r['direct_answer']=='0'
    sealed=seal({'solution':'The answer is 0.','task_id':'test'})
    assert_sealed(sealed);sealed['solution']='wrong'
    with pytest.raises(ValueError):assert_sealed(sealed)

def test_budget_actual_plus_inflight_and_resume(tmp_path):
    b=Budget(max_calls=2,max_tokens=6000)
    def transport(request):return 200,{'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30},'choices':[{'message':{'content':'ok'},'finish_reason':'stop'}]}
    c=Client(tmp_path,'FAKE',b,transport);r=c.complete('p','job','frozen');assert b.actual==30 and b.reserved==0
    r2=c.complete('p','job','frozen');assert r2==r and b.calls==1 and b.actual==30
    c.complete('p2','job2','frozen');assert b.calls==2
    with pytest.raises(RuntimeError):c.complete('p3','job3','frozen')
    tight=Budget(max_tokens=10)
    with pytest.raises(RuntimeError):tight.reserve({'messages':[{'content':'q'}],'max_tokens':4096})

def test_pending_not_retried(tmp_path):
    def transport(request):raise TimeoutError()
    c=Client(tmp_path,'FAKE',Budget(),transport)
    with pytest.raises(RuntimeError):c.complete('p','job','frozen')
    with pytest.raises(RuntimeError,match='unknown_prior'):c.complete('p','job','frozen')
    assert c.budget.calls==1 and c.budget.reserved>0
