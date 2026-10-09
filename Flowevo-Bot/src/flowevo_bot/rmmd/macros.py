"""Question-only, bounded polynomial macros. No labels, retrieval or API access.

Certificates prove a polynomial identity over QQ; natural-language coverage is
separate, and direct submission requires the exact accepted question grammar.
"""
import re
import time
from functools import lru_cache
import sympy as s
from latex2sympy2_extended import latex2sympy

IDS = ('root_invariants', 'polynomial_remainder')
COMPACT = {
 'root_invariants': 'For all roots with multiplicity, Vieta gives e_k=(-1)^k a_(n-k)/a_n. Rewrite the requested symmetric expression in these elementary sums; use Newton identities for power sums. Reciprocal expressions require nonzero denominators. Coefficients alone do not determine a restricted subset of real, positive or rational roots. Verify the requested quantity after computing the invariants.',
 'polynomial_remainder': 'Reduce powers and products modulo the nonzero polynomial divisor over the coefficient field. For ax+b evaluate at -b/a; repeated factors require multiplicity. Verify P=QD+R exactly and deg(R)<deg(D). Submit R only if the question asks precisely for this remainder.'}
MATH = re.compile(r'\$\$(.*?)\$\$|\$(.*?)\$|\\\[(.*?)\\\]|\\\((.*?)\\\)', re.S)

def fragments(text):
    return [{'step_id':i,'text':next(g for g in m.groups() if g is not None).strip(),
             'start':m.start(),'end':m.end()} for i,m in enumerate(MATH.finditer(text))]

@lru_cache(maxsize=8192)
def scalar(text):
    text=text.strip().rstrip('.,').replace('\\left','').replace('\\right','')
    if not text or len(text)>600 or re.search(r'\\(?:begin|end|text|boxed|sum|prod|cdots|ldots)|[<>;]',text):
        raise ValueError('unsupported_latex')
    # Bound degree before expansion (including power towers).
    if re.search(r'\^\s*\{?\s*\d{4,}|\^\s*\{[^}]*\^',text):raise ValueError('exponent_budget')
    expr=latex2sympy(text)
    if not isinstance(expr,s.Expr) or s.count_ops(expr)>180:raise ValueError('not_scalar_or_too_complex')
    for node in s.preorder_traversal(expr):
        if isinstance(node,s.Pow) and (not node.exp.is_Integer or abs(node.exp)>128):raise ValueError('power_scope')
    return expr

def polynomial(text, max_degree=128):
    expr=scalar(text)
    if len(expr.free_symbols)!=1:raise ValueError('one_variable_required')
    x=next(iter(expr.free_symbols));p=s.Poly(expr,x,domain=s.QQ)
    if not 1<=p.degree()<=max_degree or len(p.terms())>130:raise ValueError('degree_scope')
    if any(abs(v.p)>10**12 or v.q>10**6 for v in p.all_coeffs()):raise ValueError('coefficient_budget')
    return p

def normalized_question(question):
    fs=fragments(question);result=[];at=0
    for i,f in enumerate(fs):result.extend([question[at:f['start']],f' M{i} ']);at=f['end']
    result.append(question[at:]);return re.sub(r'\s+',' ',' '.join(result)).strip(),fs

def inspect_question(question, macro_id):
    start=time.perf_counter();out={'macro_id':macro_id,'trigger_match':False,'guard_pass':False,
      'execution_attempted':False,'execution_verified':False,'full_task_verified':False,
      'fallback_reason':'outside_trigger','scope':'none','steps':[],'direct_answer':None}
    try:
        nq,fs=normalized_question(question)
        if macro_id=='polynomial_remainder':
            # Entire question is consumed. Two explicit polynomial expressions.
            m=re.fullmatch(r'(?:Find|Determine|What is) the remainder (?:when|of) M(\d+) (?:is )?divided by M(\d+)\s*[.?]?',nq,re.I)
            if not m:return out
            out['trigger_match']=True
            p=polynomial(fs[int(m[1])]['text']);d=polynomial(fs[int(m[2])]['text'])
            if p.gen!=d.gen or d.degree()>16:raise ValueError('divisor_variable_or_degree')
            out['guard_pass']=True;out['execution_attempted']=True
            t=time.perf_counter();q,r=s.div(p,d);out['execution_seconds']=time.perf_counter()-t
            # Independent coefficient recurrence, not a second call to div/rem.
            t=time.perf_counter();coeff={int(k[0]):v for k,v in p.terms()}
            for degree in range(p.degree(),d.degree()-1,-1):
                scale=coeff.get(degree,0)/d.LC()
                for (j,),v in d.terms():coeff[degree-d.degree()+j]=coeff.get(degree-d.degree()+j,0)-scale*v
            independent=s.Poly(sum(v*p.gen**k for k,v in coeff.items()),p.gen,domain=s.QQ)
            verified=(p==q*d+r and (r.is_zero or r.degree()<d.degree()) and independent==r)
            out['verification_seconds']=time.perf_counter()-t
            out.update(execution_verified=bool(verified),full_task_verified=bool(verified),scope='full_task',
              fallback_reason=None if verified else 'identity_failed',direct_answer=s.latex(r.as_expr()) if verified else None,
              input_structure={'dividend':str(p.as_expr()),'divisor':str(d.as_expr()),'degrees':[p.degree(),d.degree()]},
              output_structure={'quotient':str(q.as_expr()),'remainder':str(r.as_expr())},
              certificate={'identity_zero':bool(p==q*d+r),'degree_bound':bool(r.is_zero or r.degree()<d.degree()),'independent_recurrence':bool(independent==r)},
              steps=['parse_two_QQ_polynomials','quotient_ring_reduction','independent_coefficient_recurrence','identity_and_degree_verification'])
        elif macro_id=='root_invariants':
            if not re.search(r'\broots\b',question,re.I):return out
            out['trigger_match']=True
            if not re.search(r'sum|product|Evaluate|Find (?:the value of )?\s*(?:\$|\\\[)',question,re.I):raise ValueError('no_symmetric_quantity_request')
            if re.search(r'(?:rational|integral|integer|positive|non.real) roots|roots.*(?:positive imaginary|that have)|real roots of',question,re.I):raise ValueError('subset_roots_not_supported')
            polys=[]
            for f in fs:
                text=f['text'].rstrip('.,')
                if '=' in text:
                    lhs,rhs=text.split('=',1)
                    if rhs.strip()!='0':continue
                    text=lhs
                try:
                    p=polynomial(text,6)
                    if p.degree()>=2:polys.append((p,f))
                except Exception:pass
            if len(polys)!=1:raise ValueError('unique_numeric_polynomial_required')
            p,f=polys[0];n=p.degree();out['guard_pass']=True;out['execution_attempted']=True
            t=time.perf_counter();e=[s.Integer(1)]+[(-1)**k*p.nth(n-k)/p.LC() for k in range(1,n+1)]
            powers=[]
            for k in range(1,n+1):
                value=sum((-1)**(j-1)*e[j]*powers[k-j-1] for j in range(1,k))+(-1)**(k-1)*k*e[k]
                powers.append(s.cancel(value))
            out['execution_seconds']=time.perf_counter()-t;t=time.perf_counter()
            rebuilt=s.Poly(sum((-1)**k*e[k]*p.gen**(n-k) for k in range(n+1)),p.gen,domain=s.QQ)
            # Formal product coefficients establish Vieta; Newton recurrence is
            # independently checked by the trace of the companion matrix powers.
            companion=s.zeros(n)
            for i in range(1,n):companion[i,i-1]=1
            for i in range(n):companion[i,n-1]=-p.nth(i)/p.LC()
            valid=rebuilt==p.monic() and all(s.trace(companion**k)==powers[k-1] for k in range(1,n+1))
            out['verification_seconds']=time.perf_counter()-t
            out.update(execution_verified=bool(valid),scope='verified_intermediate',fallback_reason=None if valid else 'certificate_failed',
              input_structure={'polynomial':str(p.as_expr()),'degree':n,'variable':str(p.gen)},
              output_structure={'elementary_sums':[str(v) for v in e[1:]],'power_sums':[str(v) for v in powers]},
              certificate={'monic_reconstruction':bool(rebuilt==p.monic()),'companion_trace_check':bool(valid)},
              steps=['numeric_polynomial_normalization','coefficient_to_elementary_sums','newton_power_sums','reconstruction_and_companion_verification'])
            out['verified_context']='For ALL '+str(n)+' roots, counted with multiplicity: '+', '.join(f'e{k}={v}' for k,v in enumerate(e[1:],1))+'. Power sums: '+', '.join(f'p{k}={v}' for k,v in enumerate(powers,1))+'. Coefficients and Newton sums verified exactly. These are intermediate invariants; determine the requested expression and check any extra constraints.'
        else:raise ValueError('unknown_macro')
    except Exception as exc:out['fallback_reason']=str(exc)[:150]
    out['local_total_seconds']=time.perf_counter()-start
    return out

def trigger_logic(node,features):
    """Explicit AND/OR/NOT; an unknown guard never authorizes execution."""
    if len(node)!=1:raise ValueError('one_operator_required')
    op,arg=next(iter(node.items()))
    if op in ('feature','guard'):return features.get(arg) is True
    if op=='all_of':return bool(arg) and all(trigger_logic(n,features) for n in arg)
    if op=='any_of':return any(trigger_logic(n,features) for n in arg)
    if op=='not':return not trigger_logic(arg,features)
    raise ValueError('unknown_operator')
