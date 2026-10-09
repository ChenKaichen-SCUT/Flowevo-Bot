"""Question-only lexical observations and separately parsed mathematical facts."""
import re
from ..schemas import ProblemView
from .evaluator import balanced


def math_fragments(text):
    pattern = r'\$([^$]+)\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)'
    return [next(g for g in m.groups() if g is not None).strip().rstrip('.,') for m in re.finditer(pattern, text)]


def denominator_texts(text):
    out = []
    for m in re.finditer(r'\\(?:d?frac|tfrac)\s*\{', text):
        _, end = balanced(text, m.end())
        k = end
        while k < len(text) and text[k].isspace(): k += 1
        if k < len(text) and text[k]=='{':
            den, _ = balanced(text,k+1)
            if den is not None: out.append(den)
    return out


def extract(task):
    if type(task) is not ProblemView: raise TypeError('Features accept only public ProblemView')
    import sympy as sp
    from sympy.core.relational import Relational, Equality
    from latex2sympy2_extended import latex2sympy
    text=task.problem; low=text.lower()
    lexical={
        'count_request': bool(re.search(r'how many|number of (?:ways|possible|distinct|different)',low)),
        'count_constraints': bool(re.search(r'\b(?:must|cannot|not|without|exactly|least|most|different|distinct|same|order|repeat|adjacent|consecutive|either|both|neither|odd|even)\b',low)),
        'order': bool(re.search(r'\b(?:order|arrang\w*|sequence|digit\w*|president|position\w*)\b',low)),
        'repetition': bool(re.search(r'\b(?:repeat\w*|identical|same|replacement)\b',low)),
        'symmetry_action': bool(re.search(r'\b(?:rotation\w*|reflection\w*|necklace|circular|keychain)\b',low)),
        'modular': bool(re.search(r'\\(?:pmod|bmod|mod)\b|\b(?:remainder|modulo)\b',text,re.I)),
        'divisibility': bool(re.search(r'\bdivisib\w*\b|\\mid',low)),
        'recurrence': bool(re.search(r'\brecurr\w*\b|a_\{?n\s*\+\s*1',low)),
        'trigonometric': bool(re.search(r'\\(?:sin|cos|tan|cot|sec|csc)\b',text)),
        'hypothetical_options': bool(re.search(r'which of the following|options that are always true',low)),
    }
    facts={'subject:'+task.subject:True, **{'lex:'+k:v for k,v in lexical.items()}}
    parsed=[]; failures=[]; degrees=[]; rational=[]; variable_den=[]; factorization=False; symmetry=False
    for den in denominator_texts(text):
        try:
            expr=latex2sympy(den)
            if getattr(expr,'free_symbols',None):variable_den.append({'latex':den,'symbols':sorted(str(s) for s in expr.free_symbols)})
        except Exception: failures.append({'latex':den,'reason':'denominator_parse_failure'})
    for fragment in math_fragments(text):
        if len(fragment)>1500 or re.search(r'\\(?:begin|text|sum|int)',fragment):
            failures.append({'latex':fragment,'reason':'unsupported_structure'});continue
        try:
            expr=latex2sympy(fragment)
            entry={'latex':fragment,'expression':str(expr),'kind':type(expr).__name__}
            if isinstance(expr,Relational):
                difference=expr.lhs-expr.rhs; symbols=difference.free_symbols
                # Recognize a concrete reduction, not the word "substitute".
                reduced=difference; substitution=None
                if len(symbols)==2:
                    a,b=sorted(symbols,key=str);t=sp.Symbol('_ratio')
                    trial=sp.cancel(difference.subs(a,t*b))
                    if trial.free_symbols=={t}:
                        reduced=trial;substitution={'kind':'homogeneous_ratio','replace':str(a)+'/'+str(b),'domain_obligation':str(b)+' != 0; handle '+str(b)+' = 0 separately'}
                elif len(symbols)==1:
                    roots=[p for p in difference.atoms(sp.Pow) if p.exp==sp.Rational(1,2)]
                    if len(roots)==1:
                        t=sp.Symbol('_root');trial=sp.simplify(difference.subs(roots[0],t))
                        if trial.free_symbols=={t}:
                            reduced=trial;substitution={'kind':'repeated_radical','replace':str(roots[0]),'domain_obligation':'retain radical range, exclude zero denominator, back-substitute'}
                symbols=reduced.free_symbols
                if len(symbols)==1:
                    symbol=next(iter(symbols)); numerator,denominator=sp.fraction(sp.together(reduced))
                    if numerator.is_polynomial(symbol) and denominator.is_polynomial(symbol):
                        deg=int(sp.degree(numerator,symbol)) if numerator!=0 else 0
                        degree_den=int(sp.degree(denominator,symbol)) if denominator!=0 else -1
                        entry.update(numerator_degree=deg,denominator_degree=degree_den,variable=str(symbol),substitution=substitution)
                        if degree_den>0:
                            rational.append({**entry,'relation':'equation' if isinstance(expr,Equality) else 'inequality'})
                        elif degree_den==0:degrees.append(deg)
            elif isinstance(expr,sp.Expr):
                symbols=expr.free_symbols
                if len(symbols)==1 and expr.is_polynomial(*symbols):degrees.append(int(sp.degree(expr)))
                factorization |= isinstance(expr,sp.Mul) and any(isinstance(a,sp.Add) for a in expr.args)
                if len(symbols)==2:
                    a,b=sorted(symbols,key=str)
                    symmetry |= sp.expand(expr-expr.xreplace({a:b,b:a})) == 0
            parsed.append(entry)
        except Exception as exc:failures.append({'latex':fragment,'reason':type(exc).__name__})
    facts.update({
        'math:rational_equation':any(r['relation']=='equation' and r['numerator_degree']<=2 for r in rational),
        'math:rational_inequality':any(r['relation']=='inequality' and r['numerator_degree']<=2 for r in rational),
        'math:variable_denominator':bool(variable_den) or bool(rational),
        'math:quadratic':max(degrees)==2 if degrees else None,
        'math:factorization':factorization,
        'math:symmetric_two_variables':symmetry,
    })
    # Unparsed mathematics cannot produce a confident negative structural claim.
    if failures and not rational:
        facts['math:rational_equation']=facts['math:rational_inequality']=None
    return {'facts':facts,'lexical':lexical,'parsed':parsed,'rational_relations':rational,
            'variable_denominators':variable_den,'polynomial_degrees':degrees,'uncertain':failures}
