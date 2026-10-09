"""Closed-world mathematical language parser. Unknown text is not discarded.

The language templates and target ontology are human-written. Matching roots
keywords only makes a problem a candidate; it never establishes goal coverage.
"""
from dataclasses import dataclass,field,asdict
import re
import sympy as s
from flowevo_bot.rmmd.macros import normalized_question,scalar

COUNTS={'two':2,'three':3,'four':4,'five':5,'six':6}
DOMAIN={'field':'QQ','root_universe':'complex','multiplicity':'counted','max_degree':6}

@dataclass
class Goal:
    kind:str='unparsed'
    family:str='none'
    state:str='fallback'
    known_objects:dict=field(default_factory=dict)
    target:dict=field(default_factory=dict)
    quantifiers:dict=field(default_factory=dict)
    conditions:list=field(default_factory=list)
    answer_format:dict=field(default_factory=lambda:{'kind':'exact'})
    semantic_certificate:dict=field(default_factory=dict)
    reason:str='no_supported_complete_grammar'
    def to_dict(self):return asdict(self)

def qq_poly(text,max_degree=128):
    text=text.strip().rstrip('.,')
    if '=' in text:
        parts=text.split('=')
        if len(parts)!=2:raise ValueError('multiple_equalities')
        lhs,rhs=parts
        named=re.fullmatch(r'[A-Za-z]\(([A-Za-z])\)',lhs.strip())
        if named:expr=scalar(rhs)
        else:expr=scalar(lhs)-scalar(rhs)
    else:expr=scalar(text)
    if len(expr.free_symbols)!=1:raise ValueError('one_variable_and_numeric_coefficients_required')
    x=next(iter(expr.free_symbols));p=s.Poly(expr,x,domain=s.QQ)
    if not 1<=p.degree()<=max_degree or len(p.terms())>130:raise ValueError('polynomial_degree_budget')
    if any(abs(v.p)>10**12 or v.q>10**6 for v in p.all_coeffs()):raise ValueError('coefficient_budget')
    return p

def polynomial_record(p):return {'expression':str(p.as_expr()),'variable':str(p.gen),'coefficients':[str(v) for v in p.all_coeffs()],'degree':p.degree(),'field':'QQ'}
def restore_poly(record):
    x=s.Symbol(record['variable']);return s.Poly.from_list([s.Rational(v) for v in record['coefficients']],x,domain=s.QQ)

def bind_roots(binding,fs,n):
    ids=list(map(int,re.findall(r'M(\d+)',binding)))
    remainder=re.sub(r'M\d+|\band\b|[\s,]','',binding,flags=re.I)
    if remainder:raise ValueError('unparsed_root_binding')
    names=[]
    for i in ids:
        text=fs[i]['text'].strip().strip('.,')
        for item in text.split(','):
            item=item.strip()
            if not item:continue
            symbol=scalar(item)
            if not isinstance(symbol,s.Symbol):raise ValueError('root_binding_not_symbol')
            names.append(symbol)
    if len(names)!=n or len(set(names))!=n:raise ValueError('root_binding_count_or_aliasing')
    return names

def scalar_target(text,names):
    expr=scalar(text)
    if not expr.free_symbols<=set(names):raise ValueError('unbound_target_symbols')
    if s.count_ops(expr)>80 or any(isinstance(v,s.Pow) and abs(v.exp)>6 for v in s.preorder_traversal(expr)):raise ValueError('target_operation_budget')
    # Preserve denominators from the unevaluated parse before simplification.
    denominators=[str(node.base) for node in s.preorder_traversal(expr) if isinstance(node,s.Pow) and node.exp.is_negative]
    if ('\\frac' in text or '/' in text) and not denominators:raise ValueError('domain_erased_by_parser')
    for i in range(len(names)-1):
        permuted=expr.xreplace({names[i]:names[i+1],names[i+1]:names[i]})
        if s.cancel(expr-permuted)!=0:raise ValueError('target_not_formally_symmetric')
    n=len(names)
    forms={'root_sum':sum(names),'root_product':s.prod(names),'pairwise_sum':sum(names[i]*names[j] for i in range(n) for j in range(i+1,n)),'reciprocal_sum':sum(1/r for r in names)}
    for kind,value in forms.items():
        if s.cancel(expr-value)==0:return kind,{'expression':str(expr),'root_symbols':list(map(str,names)),'denominators':denominators}
    for k in range(2,7):
        if s.cancel(expr-sum(r**k for r in names))==0:return 'power_sum',{'power':k,'expression':str(expr),'root_symbols':list(map(str,names)),'denominators':denominators}
    if n>4:raise ValueError('general_symmetric_target_degree_budget')
    numerator,denominator=s.fraction(s.together(expr))
    if any(s.Poly(v,*names).total_degree()>8 for v in (numerator,denominator)):raise ValueError('target_total_degree_budget')
    return 'symmetric_rational',{'expression':str(expr),'root_symbols':list(map(str,names)),'denominators':denominators}

def wording_target(words):
    words=re.sub(r'\s+',' ',words.lower()).strip()
    words=re.sub(r'\bthe\b\s*','',words)
    if words=='sum':return 'root_sum',{}
    if words=='product':return 'root_product',{}
    if words in ('sum of pairwise products','sum of products taken two at a time'):return 'pairwise_sum',{}
    if words=='sum of reciprocals':return 'reciprocal_sum',{'denominator_obligation':'all_roots_nonzero'}
    for word,k in [('squares',2),('cubes',3),('fourth powers',4),('fifth powers',5),('sixth powers',6)]:
        if words=='sum of '+word:return 'power_sum',{'power':k}
    raise ValueError('unknown_aggregate_target')

def parse_goal(question):
    goal=Goal();nq,fs=normalized_question(question);core=re.sub(r'\bthe\s+the\b','the',nq,flags=re.I)
    # Only these answer-format clauses are consumable; other trailing clauses fail.
    formats=[(r'\s*Express your answer as a common fraction(?: in lowest terms)?\.?$',{'kind':'rational'}),
             (r'\s*Express your answer as a decimal to the nearest hundredth\.?$',{'kind':'decimal','places':2})]
    for pattern,fmt in formats:
        if re.search(pattern,core,re.I):core=re.sub(pattern,'',core,flags=re.I).strip();goal.answer_format=fmt;break
    try:
        m=re.fullmatch(r'(?:Find|Determine|What is|Compute) the remainder (?:when|of) M(\d+) (?:is )?divided by M(\d+)\s*[.?]?',core,re.I)
        if m:
            p=qq_poly(fs[int(m[1])]['text']);d=qq_poly(fs[int(m[2])]['text'])
            goal.family='polynomial_remainder';goal.kind='polynomial_remainder';goal.known_objects={'polynomial':polynomial_record(p),'divisor':polynomial_record(d)};goal.quantifiers={'coefficient_field':'QQ','division':'Euclidean'}
            if p.gen!=d.gen or not 1<=d.degree()<=16:raise ValueError('divisor_variable_or_degree')
            goal.state='parsed';goal.reason=None;goal.semantic_certificate={'grammar':'complete_remainder_request','consumed_entire_question':True,'format_clause':goal.answer_format};return goal
        goal.family='root_symmetric' if re.search(r'roots|zeros|zeroes|solutions',question,re.I) else 'none'
        template=None;rootnames=None;target=None;conditions=[];poly_index=None;kind=None
        # Direct scalar aggregate of a polynomial root multiset / equation solutions.
        m=re.fullmatch(r'(?:What is|Find|Compute|Determine|Calculate) (?:the )?(.+?) of (?:all )?(?:the )?(?:(complex|real|positive|rational|distinct) )?(roots|zeros|zeroes|solutions) (?:of|to) (?:the )?(?:(?:equation|polynomial|quadratic|cubic) )?M(\d+)\s*[.?]?',core,re.I)
        if m:
            if m[2] and m[2].lower()!='complex':raise ValueError('restricted_or_distinct_root_set')
            kind,target=wording_target(m[1]);poly_index=int(m[4]);template='complete_aggregate_request';conditions=[{'kind':'squarefree_required_for_solution_set'}] if m[3].lower()=='solutions' else []
        if template is None:
            m=re.fullmatch(r'Let (.+?) be (?:all )?(?:the )?roots of (?:the )?(?:(?:cubic|quartic|polynomial|cubic polynomial|quartic polynomial) )?M(\d+)\s*\.?\s*(?:Find|Compute|Evaluate)(?: the value of)?\s*M(\d+)\s*[.?]?',core,re.I)
            if m:poly_index=int(m[2]);binding=m[1];target_index=int(m[3]);template='named_complete_root_multiset'
        if template is None:
            m=re.fullmatch(r'Let the reciprocals of the roots of M(\d+) be (.+?)\s*\.\s*Evaluate M(\d+)\s*[.?]?',core,re.I)
            if m:poly_index=int(m[1]);binding=m[2];target_index=int(m[3]);template='named_reciprocal_roots'
        if template is None:
            m=re.fullmatch(r'The (quadratic|cubic|quartic) M(\d+) has (two|three|four) real roots\.\s*What is the (.+?) of these roots\s*\??',core,re.I)
            if m:
                poly_index=int(m[2]);kind,target=wording_target(m[4]);conditions=[{'kind':'all_roots_real','count':COUNTS[m[3].lower()]}];template='complete_real_root_count'
        if template is None:
            m=re.fullmatch(r'The (two|three|four) roots of the (quadratic|cubic|quartic) M(\d+) are distinct real numbers strictly between M(\d+) and M(\d+)\s*\.\s*If the roots are (.+?),? what is the (?:sum|value of) M(\d+)\s*\??',core,re.I)
            if m:
                poly_index=int(m[3]);binding=m[6];target_index=int(m[7]);left=scalar(fs[int(m[4])]['text']);right=scalar(fs[int(m[5])]['text'])
                if not left.is_Rational or not right.is_Rational or left>=right:raise ValueError('interval_bounds')
                conditions=[{'kind':'all_distinct_roots_in_open_interval','count':COUNTS[m[1].lower()],'left':str(left),'right':str(right)}];template='complete_constrained_all_root_count'
        if template is None:raise ValueError('no_supported_complete_grammar')
        p=qq_poly(fs[poly_index]['text'],6)
        if p.degree()<2:raise ValueError('root_degree_scope')
        goal.known_objects={'polynomial':polynomial_record(p)};goal.conditions=conditions
        if kind is None:
            rootnames=bind_roots(binding,fs,p.degree());kind,target=scalar_target(fs[target_index]['text'],rootnames)
            if template=='named_reciprocal_roots':
                if kind!='root_sum':raise ValueError('reciprocal_binding_target_scope')
                kind='reciprocal_sum';target={'denominator_obligation':'all_roots_nonzero','binding_semantics':'reciprocal_roots'}
        goal.kind=kind;goal.target=target;goal.family='root_symmetric';goal.quantifiers={**DOMAIN,'root_count':p.degree()};goal.state='parsed';goal.reason=None
        goal.semantic_certificate={'grammar':template,'consumed_entire_question':True,'root_bindings':list(map(str,rootnames)) if rootnames else None,'root_semantics':'all complex roots with multiplicity, or an explicitly validated complete real-root set','format_clause':goal.answer_format}
    except Exception as exc:
        goal.reason=str(exc)[:160]
        if goal.family=='root_symmetric':
            # Partial availability is diagnostic only, never executed or injected.
            objects=[]
            for f in fs:
                try:
                    p=qq_poly(f['text'],6)
                    if p.degree()>=2:objects.append(polynomial_record(p))
                except Exception:pass
            if len(objects)==1:goal.known_objects={'polynomial':objects[0]};goal.state='partial_result';goal.semantic_certificate={'consumed_entire_question':False,'partial_only':'numeric polynomial identified; target/conditions not certified'}
    return goal
