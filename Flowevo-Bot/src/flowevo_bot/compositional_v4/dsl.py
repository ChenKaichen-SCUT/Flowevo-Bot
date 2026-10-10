"""Typed, bounded composition of four deliberately small human primitives.

Neither a modular-expression solver nor a final answer formula is a primitive.
The search chooses which tree rewrites to compose before exact fold and output.
"""
import itertools, time
from .expression import *

SIGNATURES={
    'reduce_literals':('IntegerExpression','IntegerExpression'),
    'reduce_powers':('IntegerExpression','IntegerExpression'),
    'evaluate':('IntegerExpression','Scalar'),
    'canonical_residue':('Scalar','ResidueScalar'),
}
MAX_PROGRAM_NODES=6
# Independent handwritten comparator, frozen before search/evaluation.
MANUAL_PROGRAM=('reduce_literals','reduce_powers','evaluate','canonical_residue')

def validate_program(program):
    if not isinstance(program,(list,tuple)) or not 1<=len(program)<=MAX_PROGRAM_NODES:raise ScopeError('program_size')
    typ='IntegerExpression'
    for name in program:
        if not isinstance(name,str) or name not in SIGNATURES:raise ScopeError('untrusted_DSL_operator')
        if SIGNATURES[name][0]!=typ:raise ScopeError('DSL_type_mismatch')
        typ=SIGNATURES[name][1]
    if typ!='ResidueScalar':raise ScopeError('DSL_not_complete_output')
    return typ

def reduce_literals(node,m):
    op=node[0]
    if op=='int':return ('int',node[1]%m)
    if op=='pow':return ('pow',reduce_literals(node[1],m),node[2])
    return canonical((op,*(reduce_literals(c,m) for c in node[1:])))

def reduce_powers(node,m):
    op=node[0]
    if op=='int':return node
    if op=='pow':
        base=exact_eval(reduce_powers(node[1],m))
        return ('int',pow(base,node[2],m))
    return canonical((op,*(reduce_powers(c,m) for c in node[1:])))

def execute(program,expression,modulus,timeout=3):
    validate_program(program);validate(expression)
    if type(modulus) is not int or not 2<=modulus<=MAX_MODULUS:raise ScopeError('modulus_budget')
    started=time.perf_counter();state=canonical(expression);steps=[];memo={}
    for name in program:
        if time.perf_counter()-started>timeout:raise TimeoutError('DSL_deadline')
        key=(name,state,modulus)
        if key in memo:result=memo[key]
        elif name=='reduce_literals':result=reduce_literals(state,modulus)
        elif name=='reduce_powers':result=reduce_powers(state,modulus)
        elif name=='evaluate':result=exact_eval(state)
        else:result=state%modulus
        memo[key]=result
        steps.append({'primitive':name,'input_type':SIGNATURES[name][0],'output_type':SIGNATURES[name][1],
                      'input':state,'output':result})
        state=result
    return state,steps

def enumerate_programs():
    # At most six nodes, type-check every candidate, canonical operation names,
    # no repeated rewrite: idempotent passes are provably redundant here.
    names=sorted(SIGNATURES)
    for length in range(1,min(MAX_PROGRAM_NODES,len(names))+1):
        for program in itertools.permutations(names,length):
            try:validate_program(program)
            except ScopeError:continue
            yield program
