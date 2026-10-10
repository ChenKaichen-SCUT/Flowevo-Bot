"""Independent arithmetic/semantic/counterexample/resource tests, not snapshots of implementation."""
import json,random,subprocess,sys,os
from pathlib import Path
import pytest
from flowevo_bot.compositional_v4.expression import parse_expression,ScopeError,exact_eval,structure
from flowevo_bot.compositional_v4.goals import parse_goal
from flowevo_bot.compositional_v4.dsl import execute,validate_program,MANUAL_PROGRAM,enumerate_programs
from flowevo_bot.compositional_v4.verify import verify_execution,universal_certificate,reference_residue
from flowevo_bot.compositional_v4.mining import extract_trace,anti_unify
from flowevo_bot.compositional_v4.synthesis import synthesize

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/compositional_macro_v4'

@pytest.mark.parametrize('question,answer',[
    ('Find the remainder when $8^6+7^7+6^8$ is divided by 5.',3),
    ('What is the units digit of $13^{2003}$?',7),
    ('Determine the remainder of $(11+3)(9-5)$ divided by $7$.',0),
    ('Find the remainder when $8\\cdot10^{18}+1^{18}$ is divided by 9.',0),
    ('What is the remainder when the product $1734\\times5389\\times80,\\!607$ is divided by 10?',2),
    ('Find the remainder when $-7+2$ is divided by 3.',1),
    ('Find the remainder when $(2^5+7)^9$ is divided by 35.',pow(39,9,35)),
])
def test_full_semantics(question,answer):
    goal=parse_goal(question);assert goal.parsed
    got,steps=execute(MANUAL_PROGRAM,goal.expression,goal.modulus)
    assert got==answer and verify_execution(goal.expression,goal.modulus,got,steps)['passed']

@pytest.mark.parametrize('question',[
    'Find the remainder when $x^2+1$ is divided by 9.',
    'Find the remainder when $2^{3^4}$ is divided by 9.',
    'Find the remainder when $7/2$ is divided by 3.',
    'Find the remainder when $0^0$ is divided by 5.',
    'Find the remainder when $4^{-1}$ is divided by 7.',
    'Find the remainder when $2^9$ is divided by 0.',
    'Find the remainder when $2^9$ is divided by 1.',
    'Find the remainder when $2^9$ is divided by 10001.',
    'Find the remainder when $2^9$ is divided by 7, then add one.',
    'What is the units digit of $-13^{2003}$?',
    'What is the tens digit of $13^{2003}$?',
    'What is the remainder when the sum $2*3$ is divided by 5?',
    'Find the remainder when $2+4+\\cdots+100$ is divided by 7.',
    'What is the units digit of $13^{2003}$ in base 7?',
])
def test_semantic_negatives_never_take_over(question):assert not parse_goal(question).parsed

def test_all_programs_against_exact_arithmetic_on_diverse_small_structures():
    rng=random.Random(410)
    for _ in range(240):
        a,b,c=[rng.randrange(-25,26) for i in range(3)];n=rng.randrange(1,10);m=rng.randrange(2,40)
        text=f'({a}+({b})*({c}))^{n}+({b})^{n+1}'
        node=parse_expression(text);expected=((a+b*c)**n+b**(n+1))%m
        for program in enumerate_programs():
            got,steps=execute(program,node,m)
            assert got==expected
            assert verify_execution(node,m,got,steps)['passed']

def test_large_power_solved_without_materializing_large_integer():
    node=parse_expression('13^{1000000}+17^{999999}')
    with pytest.raises(ScopeError):exact_eval(node)
    got,steps=execute(MANUAL_PROGRAM,node,97)
    assert got==(pow(13,1000000,97)+pow(17,999999,97))%97
    assert verify_execution(node,97,got,steps)['passed']

def test_counterexample_exponent_must_not_be_reduced_mod_m():
    # 2^5 mod5=2, but incorrectly reducing exponent gives 2^0 mod5=1.
    node=parse_expression('2^5')
    assert not verify_execution(node,5,1,[{'primitive':'forged','output':1}])['passed']
    assert not verify_execution(node,5,7,[])['passed'] # congruent but not canonical
    assert not verify_execution(node,5,2,[{'primitive':'forged','output':3}])['passed']

@pytest.mark.parametrize('program',[['eval'],['__import__'],['evaluate','reduce_literals','canonical_residue'],
    ['reduce_literals'],['evaluate','canonical_residue','canonical_residue'],['reduce_literals']*7,[],['feature','constant']])
def test_untrusted_programs_and_type_confusion_rejected(program):
    with pytest.raises(ScopeError):validate_program(program)

@pytest.mark.parametrize('text',['__import__("os")','2.5+1','2**3','2^1000001','('*20+'2'+')'*20,'+'.join(['1']*110),'2^{2^2}'])
def test_expression_limits(text):
    with pytest.raises(ScopeError):parse_expression(text)

def test_unknown_or_false_trace_relation_is_not_verified():
    row={'task_id':'training_fixture','problem':'Unknown target','model_solution':r'We reason. $2+2=5$. $x+1=4$.',
        'source_hash':'fixture','source_run_id':'fixture'}
    ops,ex=extract_trace(row)
    assert any(x['verification_status']=='rejected' for x in ops)
    assert any(x['verification_status']=='unknown' for x in ops)
    assert not ex['io_verified']

def test_anti_unification_keeps_structure_and_does_not_claim_vacuous_pattern():
    a=parse_expression('2^3+4^5');b=parse_expression('7^9+8^2')
    assert anti_unify(a,b)[0]=='add'
    assert anti_unify(a,parse_expression('2*3'))[0]=='IntegerExpressionHole'

def test_actual_source_induction_has_intermediates_and_no_manual_plan_dependency(monkeypatch):
    import flowevo_bot.compositional_v4.dsl as dsl
    examples=json.loads((OUT/'evidence/source_extractions.json').read_text())
    monkeypatch.setattr(dsl,'MANUAL_PROGRAM',('UNAVAILABLE_TO_SEARCH',))
    r=synthesize(examples);assert len(r['bank'])==1
    bank=r['bank'][0];assert bank['source_count']>=2 and len(bank['program'])>=3
    assert len({json.dumps(s) for s in bank['source_structures']})>=2
    assert all(bank['source_step_ids'][tid] for tid in bank['source_task_ids'])
    for c in r['candidates']:assert c['universal_certificate']['passed']
    assert not synthesize([next(x for x in examples if x['task_id']==bank['source_task_ids'][0])])['bank']

def test_worker_enforces_memory_and_wall_limits():
    code="""
import resource,signal,time
resource.setrlimit(resource.RLIMIT_AS,(536870912,536870912))
try:
    x=bytearray(700*1024*1024)
    raise AssertionError('memory cap failed')
except MemoryError:pass
def deadline(*_):raise TimeoutError()
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,.03)
try:
    time.sleep(.15)
    raise AssertionError('time cap failed')
except TimeoutError:pass
"""
    p=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=5)
    assert p.returncode==0,p.stderr.decode()

def test_split_independence_and_no_math_test():
    manifest=json.loads((OUT/'dataset_split_manifest.json').read_text())
    sets={k:set(v['ids']) for k,v in manifest['splits'].items()}
    keys=list(sets)
    for i,a in enumerate(keys):
        assert all(t.startswith('math_train_') for t in sets[a])
        for b in keys[i+1:]:assert not sets[a]&sets[b]
    historical=set(manifest['historically_exposed_ids'])
    for name in keys:
        if name!='train-build':assert not sets[name]&historical
    for edge in [json.loads(l) for l in (OUT/'evidence/near_duplicate_edges.jsonl').read_text().splitlines()]:
        sa=[n for n,s in sets.items() if edge['a'] in s];sb=[n for n,s in sets.items() if edge['b'] in s]
        assert not sa or not sb or sa==sb
