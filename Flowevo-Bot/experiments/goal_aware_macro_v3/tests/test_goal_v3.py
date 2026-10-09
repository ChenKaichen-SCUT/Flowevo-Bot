import sys,json,random,itertools
from pathlib import Path
import pytest
import sympy as s
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'src'))
from flowevo_bot.goal_v3.goals import parse_goal,restore_poly
from flowevo_bot.goal_v3.engine import solve,verify_result,guards
from flowevo_bot.goal_v3.learning import execute_program,certificate,validate_program,discover

@pytest.mark.parametrize('question,expected',[
 ('Find the sum of all solutions to the equation $(x-6)^2=25$.','12'),
 ('What is the sum of the roots of $x^2-4x+3=0$?','4'),
 ('Find the product of the roots of $(2x^3+x^2-8x+20)(5x^3-25x^2+19)=0$.','38'),
 ('Find the sum of the squares of the roots of $3x^2+4x-9$.',r'\frac{70}{9}'),
 ('Find the sum of the cubes of the roots of $x^2-3x+2$.','9'),
 ('Find the sum of the reciprocals of the roots of $x^2-13x+4=0$.',r'\frac{13}{4}'),
 (r'Let $a,$ $b,$ $c$ be the roots of $3x^3-3x^2+11x-8=0.$ Find $ab+ac+bc.$',r'\frac{11}{3}'),
 ('Find the remainder when $x^4+2$ is divided by $(x-2)^2$.','32 x - 46'),
 ('What is the sum of the the roots of $4x^3+5x^2-8x=0$? Express your answer as a decimal to the nearest hundredth.','-1.25'),
])
def test_complete_targets(question,expected):
    r=solve(question);assert r['full_task_verified'],r
    assert r['answer']==expected
    assert r['stages']==['Goal','Preconditions','Execute','Verify','Commit']
    assert r['verification_certificate']['semantic_verified'] and r['verification_certificate']['computation_verified']

@pytest.mark.parametrize('question',[
 'Find the sum of the positive roots of $x^2-4x+3=0$.',
 'Find the sum of the real roots of $x^4-1=0$.',
 'Find the product of the rational roots of $x^3-x-1=0$.',
 'Find the sum of the distinct roots of $(x-1)^2(x-2)=0$.',
 'Find the sum of all solutions to the equation $(x-1)^2=0$.',
 'Find the sum of the roots of $(x-1)^2=0$.',
 'Find the sum of the roots of $a*x^2+x+1=0$.',
 'Find the sum of the roots of $x^2-y=0$.',
 'Find the sum of the roots of $x^2-4x+3=0$, but only count the largest.',
 'Find the remainder when $x^3+1$ is divided by $x+1$, then evaluate at 3.',
 'Find the remainder when $x^3+1$ is divided by $0$.',
 'Find the remainder when $x^3+1$ is divided by $y+1$.',
 'Find the remainder when $1/x$ is divided by $x+1$.',
 'Find the sum of the reciprocals of the roots of $x^3-x=0$.',
 'Find the sum of the roots of $x^{100}=1$.',
 'Let $a$ and $b$ be the roots of $x^2-1=0$. Find $a-b$.',
 'Let $a$ and $b$ be the roots of $x^2-1=0$. Find $(a-b)/(a-b)$.',
 'Let $a$ and $a$ be the roots of $x^2-1=0$. Find $a+a$.',
 'Find the sum of the roots of $x^2+x+1=0$. Also give the largest root.',
])
def test_negative_semantics_or_domain(question):
    r=solve(question);assert not r['full_task_verified'],r
    assert r['answer'] is None and 'Commit' not in r['stages']

def test_real_count_and_interval_conditions():
    q='The quadratic $3x^2+4x-9$ has two real roots. What is the sum of the squares of these roots? Express your answer as a common fraction in lowest terms.'
    assert solve(q)['full_task_verified']
    assert not solve(q.replace('3x^2+4x-9','3x^2+4x+9'))['full_task_verified']
    q=r'The three roots of the cubic $30x^3-50x^2+22x-1$ are distinct real numbers strictly between $0$ and $1$. If the roots are $p$, $q$, and $r$, what is the sum $1/(1-p)+1/(1-q)+1/(1-r)$?'
    r=solve(q);assert r['full_task_verified'] and r['answer']=='12',r
    assert solve(q.replace('$?','?$'))['full_task_verified']
    assert not solve(q.replace('between $0$ and $1$','between $2$ and $3$'))['full_task_verified']

def test_original_denominator_preserved():
    q='Let $a$ and $b$ be the roots of $x^2-x=0$. Find $a/b+b/a$.'
    r=solve(q);assert not r['full_task_verified'] and r['fallback_reason']=='original_denominator_nonzero'
    r=solve('Let $a$ and $b$ be the roots of $x^2-3x+2=0$. Find $a/b+b/a$.')
    assert r['full_task_verified'] and r['answer']==r'\frac{5}{2}'

def test_property_known_root_multisets():
    rng=random.Random(3301);x=s.Symbol('x')
    for n in range(2,7):
        for _ in range(8):
            roots=[rng.randrange(-4,5) for i in range(n)];p=s.expand(rng.choice([-3,-2,1,2,5])*s.prod(x-r for r in roots))
            for phrase,wanted in [('sum',sum(roots)),('product',s.prod(roots)),('sum of the squares',sum(r*r for r in roots)),('sum of the cubes',sum(r**3 for r in roots))]:
                r=solve(f'Find the {phrase} of the roots (counting multiplicity) of ${s.latex(p)}=0$.')
                assert r['full_task_verified'] and r['answer']==s.latex(wanted),r

def test_property_remainder_identity_and_substitution():
    rng=random.Random(503);x=s.Symbol('x')
    for _ in range(30):
        p=x**rng.randrange(2,9)+sum(rng.randrange(-4,5)*x**k for k in range(4));d=x**rng.randrange(1,4)+rng.randrange(1,5)*x+rng.randrange(-3,4)
        r=solve(f'Find the remainder when ${s.latex(p)}$ is divided by ${s.latex(d)}$.')
        assert r['full_task_verified'],r
        rem=s.sympify(r['execution_result']);quot=s.sympify(r['verification_certificate']['quotient'])
        for v in [-2,0,3,s.Rational(1,2)]:assert (p-quot*d-rem).subs(x,v)==0

def test_no_partial_prompt_or_implicit_manual_fallback():
    q='Find the roots of $x^3-x+1=0$.';r=solve(q,'automatic',[])
    assert r['partial_result'] and not r['execution_attempted'] and r['answer'] is None
    q='Find the remainder when $x^3+1$ is divided by $x+1$.';r=solve(q,'automatic',[])
    assert r['fallback_reason']=='no_certified_automatic_macro' and not r['execution_attempted']

def test_corrupted_program_cannot_commit():
    q='Find the sum of the roots of $x^2-4x+3=0$.'
    bank=[{'goal_kind':'root_sum','status':'certified','macro_id':'bad','program':['feature','constant'],'certificate':{'degrees':[2]}}]
    r=solve(q,'automatic',bank);assert r['execution_attempted'] and not r['full_task_verified'] and r['answer'] is None

def test_dsl_no_arbitrary_code_and_denominator_certificate():
    for program in [('__import__','os'),('eval','x'),('feature','gold'),('neg',('feature','one'),('feature','one'))]:
        with pytest.raises(ValueError):validate_program(program)
    # Training-fit shortcut -a_(n-1) fails as soon as leading coefficient !=1.
    result=certificate(('neg',('feature','top1')),'root_sum');assert not result['passed']
    result=certificate(('div',('feature','top1'),('feature','top1')),'root_sum');assert not result['passed']

def test_no_runtime_gold_or_solver_api_access():
    import inspect
    import flowevo_bot.goal_v3.engine as engine
    import flowevo_bot.goal_v3.goals as goals
    for module in (engine,goals):
        source=inspect.getsource(module)
        for forbidden in ['gold_answer','labels.jsonl','requests.post','miyao.txt']:assert forbidden not in source
