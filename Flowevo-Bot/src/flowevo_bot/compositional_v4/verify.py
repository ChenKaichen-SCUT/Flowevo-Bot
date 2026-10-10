"""Independent mathematical checker: no DSL execution or Python modular pow.

Exact small-domain checks are tests, not universal proofs. General validity is
structural induction over IntegerExpression using congruence preservation of
integer literals, addition, multiplication and positive integer powers.
"""
from .expression import validate,MAX_MODULUS,ScopeError

def repeated_square(a,n,m):
    result=1
    while n:
        if n&1:result=(result*a)%m
        a=(a*a)%m;n//=2
    return result%m

def reference_residue(node,m):
    op=node[0]
    if op=='int':return node[1]%m
    if op=='pow':return repeated_square(reference_residue(node[1],m),node[2],m)
    result=0 if op=='add' else 1
    for child in node[1:]:
        v=reference_residue(child,m)
        result=(result+v if op=='add' else result*v)%m
    return result

def verify_execution(expression,m,result,steps):
    validate(expression)
    if type(m) is not int or not 2<=m<=MAX_MODULUS:raise ScopeError('verifier_modulus')
    checks=[];wanted=reference_residue(expression,m)
    for step in steps:
        out=step['output']
        got=out%m if type(out) is int else reference_residue(out,m)
        checks.append({'primitive':step['primitive'],'residue':got,'preserves_congruence':got==wanted})
    passed=type(result) is int and 0<=result<m and result==wanted and all(x['preserves_congruence'] for x in checks)
    return {'passed':passed,'reference_result':wanted,'checks':checks,'method':'independent binary modular exponentiation and residue ring fold; canonical interval'}

def universal_certificate(program):
    from .dsl import validate_program
    import sympy as s
    validate_program(program)
    a,b,m,q,r,t=s.symbols('a b m q r t',integer=True)
    checks={
      'addition':s.expand((a+m*q)+(b+m*t)-(a+b)-m*(q+t)),
      'multiplication':s.expand((a+m*q)*(b+m*t)-a*b-m*(a*t+b*q+m*q*t)),
      'power_induction':s.expand((b+m*q)*(r+m*t)-b*r-m*((b+m*q)*t+q*r)),
    }
    return {'passed':all(v==0 for v in checks.values()),'symbolic_residuals':{k:str(v) for k,v in checks.items()},
      'theorem':'structural congruence preservation, followed by the unique representative in [0,m)',
      'proof_obligations':['integer division a=q*m+r with 0<=r<m','add/mul algebraic identities',
        'positive power induction: a=b+m*q and a^k=b^k+m*t imply next powers congruent',
        'tree rewrite leaves exponents unchanged','exact fold either preserves the integer or refuses before exceeding bit budget'],
      'scope':'bounded IntegerExpression over int/add/mul/positive literal pow, 2<=m<=10000; no division, variables, exponent towers or arbitrary code',
      'proof_status':'human specified induction rules with recomputed symbolic obligations; not a proof assistant proof',
      'program':list(program),'manual_prior':'type signatures, primitive semantics, congruence induction and target semantics',
      'runtime_verification':'independent residue checker required for every intermediate state and final value'}
