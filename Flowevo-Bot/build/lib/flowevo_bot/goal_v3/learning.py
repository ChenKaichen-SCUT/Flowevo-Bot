"""Bounded scalar DSL induction from extracted successful trajectory targets.

Human priors: goal grammar, coefficient terminals, arithmetic DSL and universal
root semantics verifier. Learned: the arithmetic program and admitted routing
entries. No prewritten Vieta formula is inserted into the synthesized bank.
"""
from dataclasses import dataclass,asdict
from functools import lru_cache
import hashlib,json,itertools,re,time
import sympy as s
from .goals import parse_goal,restore_poly
from flowevo_bot.rmmd.macros import fragments,scalar
from flowevo_bot.v2.evaluator import extract,presentation,parse_scalar

TERMINALS=('lead','top1','top2','constant','linear','parity','one')
OPS=('add','sub','mul','div')
MAX_NODES=5

@dataclass
class ReasoningOperation:
    task_id:str
    operation_type:str
    input_structure:dict
    output_goal:dict
    observed_output:str
    source_step_ids:list
    source_steps:list
    preconditions:list
    verification_rule:str
    provenance:dict
    extraction_status:str
    def to_dict(self):return asdict(self)

def features(p):
    n=p.degree();return {'lead':p.LC(),'top1':p.nth(n-1),'top2':p.nth(n-2),'constant':p.TC(),'linear':p.nth(1),'parity':s.Integer((-1)**n),'one':s.Integer(1)}

def validate_program(program,depth=0):
    if depth>5 or not isinstance(program,(list,tuple)) or not program:raise ValueError('invalid_DSL_AST')
    op=program[0]
    if op=='feature':
        if len(program)!=2 or program[1] not in TERMINALS:raise ValueError('unknown_feature')
        return 1
    arity=1 if op=='neg' else 2 if op in OPS else None
    if arity is None or len(program)!=arity+1:raise ValueError('untrusted_or_wrong_arity_operator')
    count=1+sum(validate_program(c,depth+1) for c in program[1:])
    if count>MAX_NODES:raise ValueError('program_size_budget')
    return count

def execute_program(program,p):
    validate_program(program);f=features(p)
    def run(node):
        op=node[0]
        if op=='feature':return f[node[1]]
        a=run(node[1])
        if op=='neg':return -a
        b=run(node[2])
        if op=='add':return a+b
        if op=='sub':return a-b
        if op=='mul':return a*b
        if b==0:raise ValueError('DSL_division_by_zero')
        return a/b
    return s.cancel(run(program))

def extract_operations(traces):
    operations=[];excluded=[]
    for row in traces:
        goal=parse_goal(row['problem'])
        if goal.state!='parsed':
            excluded.append({'task_id':row['task_id'],'reason':goal.reason,'stage':'goal_extraction','goal_state':goal.state});continue
        answer,status=extract(row['model_solution'])
        try:
            value=parse_scalar(presentation(answer))
            if value is None:raise ValueError('unparsed_observed_output')
            if not value.is_Rational:raise ValueError('observed_target_not_exact_rational')
        except Exception as exc:excluded.append({'task_id':row['task_id'],'reason':str(exc),'stage':'observed_output_extraction'});continue
        mathsteps=fragments(row['model_solution']);steps=[f for f in mathsteps if '=' in f['text'] or '\\equiv' in f['text']]
        if not steps:excluded.append({'task_id':row['task_id'],'reason':'no_explicit_transformation_evidence','stage':'trajectory_evidence'});continue
        p=restore_poly(goal.known_objects['polynomial'])
        operations.append(ReasoningOperation(row['task_id'],'polynomial_goal_to_observed_scalar',goal.known_objects,{'kind':goal.kind,'target':goal.target,'conditions':goal.conditions},str(value),[f['step_id'] for f in steps],[f['text'] for f in steps],['clean first-pass success','QQ nonzero leading coefficient','full question grammar consumed','observed model final is exact rational'],'all-coefficient symbolic root-multiset identity',{'source_hash':row['source_hash'],'source_run_id':row['source_run_id'],'goal_parser':'human-written','math_steps':'automatically copied, not fully semantically parsed','feature_vector':{k:str(v) for k,v in features(p).items()},'input_syntax': 'nonzero_rhs_equation' if re.search(r'=\s*\d*[1-9]\d*\s*\$',row['problem']) else 'factored' if ')(' in row['problem'] else 'expanded','degree':p.degree()},'target and mathematical spans extracted automatically').to_dict())
    return operations,excluded

def certificate(program,kind):
    # The checker knows the definition of the requested target, not its formula
    # in polynomial coefficients. It forms a polynomial from arbitrary roots.
    if kind not in ('root_sum','root_product','pairwise_sum','reciprocal_sum'):return {'passed':False,'reason':'unimplemented_universal_target_semantics'}
    checks=[];x=s.Symbol('x');lead=s.Symbol('L',nonzero=True)
    for n in range(2,7):
        roots=s.symbols('r0:'+str(n),**({'nonzero':True} if kind=='reciprocal_sum' else {}))
        p=s.Poly(lead*s.prod(x-r for r in roots),x)
        try:
            def inspect_divisions(node):
                if node[0]=='feature':return []
                records=[]
                if node[0]=='div':
                    denominator=s.factor(execute_program(node[2],p));allowed={lead}|(set(roots) if kind=='reciprocal_sum' else set())
                    permitted=denominator!=0 and all((base.is_Rational and base!=0 or base in allowed) and exponent.is_Integer for base,exponent in denominator.as_powers_dict().items())
                    records.append({'denominator':str(denominator),'nonzero_on_declared_domain':bool(permitted)})
                    if not permitted:raise ValueError('DSL_denominator_not_proven_nonzero_on_full_domain')
                for child in node[1:]:records.extend(inspect_divisions(child))
                return records
            domains=inspect_divisions(program)
            got=execute_program(program,p)
            wanted=sum(roots) if kind=='root_sum' else s.prod(roots) if kind=='root_product' else sum(roots[i]*roots[j] for i in range(n) for j in range(i+1,n)) if kind=='pairwise_sum' else sum(1/r for r in roots)
            residual=s.cancel(got-wanted)
            checks.append({'degree':n,'residual':str(residual),'identically_zero':residual==0,'denominator_certificates':domains})
            if residual!=0:
                concrete=residual.subs({lead:2,**{r:i+1 for i,r in enumerate(roots)}})
                return {'passed':False,'reason':'symbolic_counterexample','checks':checks,'counterexample':{'leading_coefficient':2,'roots':list(range(1,n+1)),'residual':str(concrete)}}
        except Exception as exc:return {'passed':False,'reason':str(exc),'checks':checks}
    return {'passed':True,'degrees':list(range(2,7)),'checks':checks,'scope':'arbitrary complex roots with multiplicity and nonzero leading coefficient; QQ is a subdomain','proof_method':'substitute coefficients of L*product(x-r_i), cancel output minus semantic target to zero','human_prior':'formal definition of target plus exact symbolic algebra'}

def enumerate_programs():
    bysize={1:[('feature',name) for name in TERMINALS]}
    for size in range(1,MAX_NODES+1):
        if size>1:
            entries=[('neg',p) for p in bysize[size-1]]
            for left in range(1,size-1):
                right=size-1-left
                for a in bysize[left]:
                    for b in bysize[right]:
                        for op in OPS:
                            if op in ('add','mul') and repr(a)>repr(b):continue
                            entries.append((op,a,b))
            bysize[size]=entries
        yield from bysize[size]

def discover(traces):
    started=time.perf_counter();ops,exclusions=extract_operations(traces);groups={}
    for row in ops:groups.setdefault(row['output_goal']['kind'],[]).append(row)
    bank=[];failures=[];candidates=[];search=[]
    for kind,rows in sorted(groups.items()):
        ids=sorted({r['task_id'] for r in rows});structures={(r['provenance']['degree'],r['provenance']['input_syntax']) for r in rows}
        if len(ids)<2 or len(structures)<2:
            failures.append({'goal_kind':kind,'reason':'at_least_two_distinct_tasks_and_structures_required','source_ids':ids,'structural_classes':list(structures)});continue
        if kind not in ('root_sum','root_product','pairwise_sum','reciprocal_sum'):
            failures.append({'goal_kind':kind,'reason':'bounded_scalar_DSL_has_no_admitted_polynomial_program_or_target_prover','source_ids':ids,'note':'Do not turn a manually preset remainder operator into an alleged learned program.'});continue
        polys=[restore_poly(r['input_structure']['polynomial']) for r in rows];targets=[s.Rational(r['observed_output']) for r in rows]
        feature_rows=[features(p) for p in polys]
        @lru_cache(maxsize=50000)
        def vector(program):
            op=program[0]
            if op=='feature':return tuple(f[program[1]] for f in feature_rows)
            a=vector(program[1])
            if a is None:return None
            if op=='neg':return tuple(-v for v in a)
            b=vector(program[2])
            if b is None or op=='div' and any(v==0 for v in b):return None
            if op=='add':return tuple(x+y for x,y in zip(a,b))
            if op=='sub':return tuple(x-y for x,y in zip(a,b))
            if op=='mul':return tuple(x*y for x,y in zip(a,b))
            return tuple(x/y for x,y in zip(a,b))
        enumerated=fit=0;found=None;t=time.perf_counter()
        for program in enumerate_programs():
            enumerated+=1
            if vector(program)!=tuple(targets):continue
            fit+=1;proof=certificate(program,kind);item={'goal_kind':kind,'program':program,'source_ids':ids,'training_exact_fit':True,'universal_certificate':proof};candidates.append(item)
            if proof['passed']:
                identity=hashlib.sha256(json.dumps(program).encode()).hexdigest()[:12]
                found={'macro_id':'auto_'+kind+'_'+identity,'goal_kind':kind,'status':'certified','program':program,'program_origin':'enumerated_and_selected_from_trace_targets','source_task_ids':ids,'structural_classes':list(structures),'certificate':proof,'manual_components':['Goal grammar and target ontology','raw coefficient/parity features','arithmetic DSL','formal target verification rules'],'learned_components':['arithmetic AST','which goal families meet multi-source admission'],'new_llm_calls':0};bank.append(found);break
        search.append({'goal_kind':kind,'enumerated_programs':enumerated,'training_fit_programs':fit,'certified_found':found is not None,'seconds':time.perf_counter()-t,'max_nodes':MAX_NODES,'memoization':'AST exact vector cache, no lossy output-equivalence pruning'})
        if found is None:failures.append({'goal_kind':kind,'reason':'no_universally_certified_program_within_grammar_budget','source_ids':ids})
    return {'operations':ops,'excluded_source_extractions':exclusions,'bank':bank,'candidate_attempts':candidates,'failed_families':failures,'search_statistics':search,'wall_seconds':time.perf_counter()-started,'new_api_calls':0}
