"""Goal → preconditions → execute → independently verify → commit.

The manual baseline formulas and mathematical verifier are human-written.
No LLM, answer labels, bank learning or natural-language feedback in this module.
"""
import itertools,time
import sympy as s
from .goals import Goal,parse_goal,restore_poly

def elementary(p):
    n=p.degree();return [s.Integer(1)]+[(-1)**k*p.nth(n-k)/p.LC() for k in range(1,n+1)]

def symmetric_value(expr,names,e):
    numerator,denominator=s.fraction(s.together(expr))
    values=[]
    for expression in (numerator,denominator):
        rewritten,remainder,mapping=s.symmetrize(s.expand(expression),names,formal=True)
        if remainder!=0:raise ValueError('not_symmetric_after_normalization')
        values.append(s.cancel(rewritten.subs({symbol:e[i+1] for i,(symbol,_) in enumerate(mapping)})))
    if values[1]==0:raise ValueError('target_denominator_zero')
    return s.cancel(values[0]/values[1])

def guards(goal):
    checks=[];p=restore_poly(goal.known_objects['polynomial']);n=p.degree()
    def require(name,value,detail=None):
        checks.append({'guard':name,'passed':bool(value),'detail':detail})
        if not value:raise ValueError(name)
    try:
        require('semantic_coverage',goal.state=='parsed' and goal.semantic_certificate.get('consumed_entire_question') is True)
        require('QQ_nonzero_leading_coefficient',p.domain==s.QQ and p.LC()!=0)
        if goal.family=='root_symmetric':
            require('degree_2_to_6',2<=n<=6)
            for condition in goal.conditions:
                kind=condition['kind']
                if kind=='squarefree_required_for_solution_set':require(kind,p.is_sqf)
                elif kind=='all_roots_real':require(kind,condition['count']==n and p.count_roots(-s.oo,s.oo)==n)
                elif kind=='all_distinct_roots_in_open_interval':
                    a,b=s.Rational(condition['left']),s.Rational(condition['right'])
                    require(kind,condition['count']==n and p.is_sqf and p.eval(a)!=0 and p.eval(b)!=0 and p.count_roots(a,b)==n)
                else:require('unknown_condition',False)
            if goal.kind=='reciprocal_sum':require('all_roots_nonzero',p.TC()!=0)
            if goal.kind=='power_sum':require('power_budget',2<=goal.target.get('power',0)<=6)
            if goal.kind=='symmetric_rational' or goal.target.get('denominators'):
                names=[s.Symbol(v) for v in goal.target.get('root_symbols',[])];e=elementary(p)
                for text in goal.target.get('denominators',[]):
                    factor=s.sympify(text)
                    # Product over all assignments is symmetric; nonzero proves
                    # the original denominator is nonzero for every assignment.
                    if factor.free_symbols:
                        require('denominator_orbit_budget',len(names)<=4)
                        symmetric=all(s.cancel(factor-factor.xreplace({names[i]:names[i+1],names[i+1]:names[i]}))==0 for i in range(len(names)-1))
                        if symmetric:val=symmetric_value(factor,names,e)
                        else:
                            fp=s.Poly(factor,*names)
                            simple=len(fp.terms())==1 or (len(factor.free_symbols)==1 and fp.total_degree()==1)
                            require('denominator_factor_scope',simple)
                            orbit=s.prod(factor.xreplace(dict(zip(names,perm))) for perm in itertools.permutations(names))
                            val=symmetric_value(orbit,names,e)
                    else:val=factor
                    require('original_denominator_nonzero',val!=0,{'factor':text,'orbit_value':str(val)})
        else:
            d=restore_poly(goal.known_objects['divisor']);require('same_variable_nonzero_divisor',d.gen==p.gen and d.LC()!=0 and 1<=d.degree()<=16)
        return True,checks,None
    except Exception as exc:return False,checks,str(exc)

def manual_execute(goal):
    p=restore_poly(goal.known_objects['polynomial']);e=elementary(p);n=p.degree();kind=goal.kind
    if kind=='root_sum':return e[1]
    if kind=='root_product':return e[n]
    if kind=='pairwise_sum':return e[2]
    if kind=='reciprocal_sum':return e[n-1]/e[n]
    if kind=='power_sum':
        powers=[]
        for k in range(1,goal.target['power']+1):
            value=sum((-1)**(j-1)*e[j]*powers[k-j-1] for j in range(1,min(k,n+1)))
            if k<=n:value+=(-1)**(k-1)*k*e[k]
            powers.append(s.cancel(value))
        return powers[-1]
    if kind=='symmetric_rational':return symmetric_value(s.sympify(goal.target['expression']),[s.Symbol(v) for v in goal.target['root_symbols']],e)
    if kind=='polynomial_remainder':return s.rem(p,restore_poly(goal.known_objects['divisor'])).as_expr()
    raise ValueError('no_manual_operator')

def companion(p):
    n=p.degree();matrix=s.zeros(n)
    for i in range(1,n):matrix[i,i-1]=1
    for i in range(n):matrix[i,n-1]=-p.nth(i)/p.LC()
    return matrix

def verify_result(goal,result):
    p=restore_poly(goal.known_objects['polynomial']);kind=goal.kind;proof={'computation_verified':False,'semantic_verified':goal.semantic_certificate.get('consumed_entire_question') is True,'scope':'full_goal','verifier':None}
    if kind in ('root_sum','root_product','pairwise_sum','power_sum','reciprocal_sum'):
        c=companion(p)
        if kind=='root_sum':expected=s.trace(c)
        elif kind=='root_product':expected=c.det()
        elif kind=='pairwise_sum':expected=(s.trace(c)**2-s.trace(c*c))/2
        elif kind=='power_sum':expected=s.trace(c**goal.target['power'])
        else:expected=s.trace(c.inv())
        proof.update(verifier='companion_matrix_spectrum_identity',expected=str(expected),residual=str(s.cancel(result-expected)),computation_verified=s.cancel(result-expected)==0)
    elif kind=='symmetric_rational':
        names=[s.Symbol(v) for v in goal.target['root_symbols']];expression=s.sympify(goal.target['expression']);n=p.degree()
        # Reduce target-result numerator modulo e_k(roots)-coefficient invariants.
        equations=[sum(s.prod(items) for items in itertools.combinations(names,k))-elementary(p)[k] for k in range(1,n+1)]
        numerator=s.fraction(s.together(expression-result))[0]
        gb=s.groebner(equations,*names,domain=s.QQ);residual=gb.reduce(s.expand(numerator))[1]
        proof.update(verifier='independent_groebner_target_residual',residual=str(residual),computation_verified=residual==0)
    elif kind=='polynomial_remainder':
        d=restore_poly(goal.known_objects['divisor']);r=s.Poly(result,p.gen,domain=s.QQ);coeff=dict((k[0],v) for k,v in p.terms());quotient={}
        for degree in range(p.degree(),d.degree()-1,-1):
            scale=coeff.get(degree,0)/d.LC();quotient[degree-d.degree()]=scale
            for (j,),v in d.terms():coeff[degree-d.degree()+j]=coeff.get(degree-d.degree()+j,0)-scale*v
        q=s.Poly(sum(v*p.gen**k for k,v in quotient.items()),p.gen,domain=s.QQ);other=s.Poly(sum(v*p.gen**k for k,v in coeff.items()),p.gen,domain=s.QQ)
        proof.update(verifier='coefficient_recurrence_and_division_identity',identity_zero=p==q*d+r,degree_bound=r.is_zero or r.degree()<d.degree(),independent_remainder_match=other==r,quotient=str(q.as_expr()),computation_verified=p==q*d+r and (r.is_zero or r.degree()<d.degree()) and other==r)
    proof['full_task_verified']=bool(proof['semantic_verified'] and proof['computation_verified']);return proof

def format_answer(result,fmt):
    result=s.cancel(result)
    if fmt['kind']=='decimal':
        if not result.is_Rational:raise ValueError('decimal_nonrational')
        scale=10**fmt['places'];v=result*scale;fraction=v-s.floor(v)
        if fraction==s.Rational(1,2):raise ValueError('rounding_tie_convention_unspecified')
        rounded=int(s.floor(v+s.Rational(1,2)));return ('-' if rounded<0 else '')+str(abs(rounded)//scale)+'.'+str(abs(rounded)%scale).zfill(fmt['places'])
    return s.latex(result)

def solve(question,method='manual',bank=None):
    start=time.perf_counter();goal=parse_goal(question);out={'goal':goal.to_dict(),'method':method,'trigger':goal.state=='parsed','guard_checks':[],'guard_pass':False,'execution_attempted':False,'execution_result':None,'verification_certificate':None,'full_task_verified':False,'partial_result':goal.state=='partial_result','fallback_reason':goal.reason,'selected_macro':None,'answer':None,'stages':['Goal'],'retrieval_seconds':0.,'execution_seconds':0.,'verification_seconds':0.}
    try:
        if goal.state!='parsed':return out
        out['stages'].append('Preconditions');ok,checks,reason=guards(goal);out['guard_checks']=checks;out['guard_pass']=ok
        if not ok:out['fallback_reason']=reason;return out
        out['stages'].append('Execute');t=time.perf_counter()
        if method=='manual':out['selected_macro']='manual_'+goal.kind;out['execution_attempted']=True;result=manual_execute(goal)
        elif method=='automatic':
            from .learning import execute_program
            candidates=[m for m in (bank or []) if m['goal_kind']==goal.kind and m.get('status')=='certified' and goal.known_objects['polynomial']['degree'] in m['certificate']['degrees']]
            out['retrieval_seconds']=time.perf_counter()-t
            if not candidates:out['fallback_reason']='no_certified_automatic_macro';return out
            macro=candidates[0];out['selected_macro']=macro['macro_id'];out['execution_attempted']=True;result=execute_program(macro['program'],restore_poly(goal.known_objects['polynomial']))
        else:raise ValueError('unknown_method')
        out['execution_seconds']=time.perf_counter()-t;out['execution_result']=str(result);out['stages'].append('Verify');t=time.perf_counter();proof=verify_result(goal,result);out['verification_certificate']=proof;out['verification_seconds']=time.perf_counter()-t
        if not proof['full_task_verified']:out['fallback_reason']='independent_verification_failed';return out
        out['answer']=format_answer(result,goal.answer_format);out['full_task_verified']=True;out['fallback_reason']=None;out['stages'].append('Commit')
    except Exception as exc:out['fallback_reason']=str(exc)[:180]
    finally:out['local_seconds']=time.perf_counter()-start
    return out
