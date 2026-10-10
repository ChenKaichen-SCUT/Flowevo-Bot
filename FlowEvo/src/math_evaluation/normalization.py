"""Typed normalization, with exact values and preserved semantic annotations."""
import re
from dataclasses import replace
import sympy as s
from sympy.core.relational import Relational
from .models import Normalized,Unsupported,Invalid
from .text import presentation,split_top
from .parsing import scalar,domain_set
from .units import split_unit,UNITS


def _parts(t):
    # Natural-language conjunction is a separator only in a requested answer list.
    return split_top(re.sub(r'\s+(?:or|and)\s+',',',t,flags=re.I))


def normalize(text,spec,config):
    t=presentation(text)
    if not t:raise Unsupported('empty_candidate')
    if spec.kind in ('choice','text'):
        t=re.sub(r'^\\overline\{([A-Za-z]+)\}$',r'\1',t)
        t=re.sub(r'^(?:option|choice)\s*', '',t,flags=re.I).strip(' ()[]')
        if not re.fullmatch(r'[A-Za-z]+',t):raise Unsupported('choice_not_a_single_label')
        allowed={x.casefold():x for x in spec.choices}
        if allowed and t.casefold() not in allowed:raise Invalid('answer_outside_public_choice_vocabulary')
        if not allowed and len(t)!=1:raise Unsupported('unspecified_text_vocabulary')
        return Normalized(spec.kind,t.casefold(),notes=['public vocabulary; case insensitive'])
    if spec.base:
        t=t.replace(r'\(', '').replace(r'\)','').replace('$','')
        m=re.fullmatch(r'([+-]?[0-9A-Za-z]+)(?:_\{?(\d+)\}?)?',t)
        if not m:raise Unsupported('invalid_base_numeral')
        base=int(m[2]) if m[2] else spec.base
        if base!=spec.base:raise Invalid('wrong_requested_numeral_base')
        try:value=s.Integer(int(m[1],base))
        except ValueError:raise Invalid('digit_outside_numeral_base')
        return Normalized('base_numeral',value,notes=[f'base={base}'])
    # Strip only a requested-variable assignment, never arbitrary variable names.
    if spec.kind!='equation':
        m=re.match(r'^([A-Za-z])\s*=\s*(.*)$',t,re.S)
        if m and spec.target==m[1]:t=m[2]
    # Brace sets and +/- roots must never become nested scalar containers.
    set_syntax=t.startswith(r'\{') and t.endswith(r'\}') or t.startswith('{') and t.endswith('}')
    pm=r'\pm' in t or '±' in t
    if spec.kind=='finite_set' or set_syntax or pm:
        if set_syntax:t=t[2:-2] if t.startswith('\\') else t[1:-1]
        if not t.strip() or t in (r'\emptyset',r'\varnothing','∅'):return Normalized('finite_set',s.EmptySet,domain=(str(s.S.Complexes if spec.domain=='complex' else s.S.Integers if spec.domain=='integer' else s.S.Reals),))
        vals=[];domains=[]
        for part in _parts(t):
            m=re.match(r'^([A-Za-z])\s*=\s*(.*)$',part,re.S)
            if m:
                if not spec.target or m[1]!=spec.target:raise Unsupported('unrequested_assignment_in_set')
                part=m[2]
            # A single +/- operator denotes both branches, including inside parentheses.
            part=part.replace('±',r'\pm ')
            if part.count(r'\pm')>1:raise Unsupported('correlation_of_multiple_plus_minus_symbols')
            expansions=[part.replace(r'\pm','+'),part.replace(r'\pm','-')] if r'\pm' in part else [part]
            for item in expansions:
                v,o=scalar(item,spec,config)
                if isinstance(v,s.FiniteSet):vals.extend(v)
                elif isinstance(v,(s.Set,Relational,s.MatrixBase)):raise Unsupported('invalid_finite_set_member')
                else:vals.append(v)
                domains.append(domain_set(v,o,spec))
        return Normalized('finite_set',s.FiniteSet(*vals),domain=tuple(sorted(set(map(str,domains)))))
    # Intervals are distinguished from ordered tuples by the public contract or
    # unambiguous half-open brackets / union notation.
    interval=spec.kind=='interval' or r'\cup' in t or bool(re.match(r'^\[.*\)$|^\(.*\]$',t))
    if interval:
        pieces=t.split(r'\cup');sets=[]
        for piece in pieces:
            piece=piece.strip()
            if len(piece)>2 and piece[0] in '[(' and piece[-1] in '])' and len(split_top(piece[1:-1]))==2:
                endpoints=split_top(piece[1:-1]);a,oa=scalar(endpoints[0],spec,config);b,ob=scalar(endpoints[1],spec,config)
                if a.free_symbols or b.free_symbols:raise Unsupported('symbolic_interval_endpoints')
                if a>b:raise Invalid('reversed_interval')
                sets.append(s.Interval(a,b,left_open=piece[0]=='(',right_open=piece[-1]==')'))
            else:
                v,o=scalar(piece,spec,config)
                if len(v.free_symbols)!=1:raise Unsupported('inequality_requires_one_variable')
                var=next(iter(v.free_symbols))
                if spec.target and str(var)!=spec.target:raise Unsupported('inequality_target_variable_mismatch')
                if not isinstance(v,(Relational,s.And,s.Or)):raise Unsupported('expected_interval_or_inequality')
                sets.append(v.as_set().intersect(domain_set(v,o,spec)))
        return Normalized('interval',s.Union(*sets).intersect(s.S.Integers) if spec.domain=='integer' else s.Union(*sets),domain=spec.domain)
    if spec.kind=='tuple' or (t.startswith('(') and t.endswith(')') and len(split_top(t[1:-1]))>1):
        if not (t.startswith('(') and t.endswith(')')):raise Unsupported('ordered_tuple_requires_delimiters')
        values=[];domains=[]
        for p in split_top(t[1:-1]):
            v,o=scalar(p,spec,config);values.append(v);domains.append(str(domain_set(v,o,spec)))
        return Normalized('tuple',s.Tuple(*values),domain=tuple(domains))
    if r'\begin{' in t or spec.kind=='matrix':
        v,o=scalar(t,spec,config)
        if not isinstance(v,s.MatrixBase):raise Unsupported('expected_matrix')
        return Normalized('matrix',v,domain=domain_set(v,o,spec))
    # Percent meaning depends on what quantity the question asks to report.
    is_percent=bool(re.search(r'(?:\\?%|percent)$',t,re.I))
    if is_percent:t=re.sub(r'\s*(?:\\?%|percent)$','',t,flags=re.I)
    numeric,unit,direction=split_unit(t)
    # Remove complete math delimiters from the numeric part only.
    numeric=presentation(numeric)
    v,o=scalar(numeric,spec,config)
    if isinstance(v,Relational):
        if spec.kind!='equation' or not isinstance(v,s.Equality):raise Unsupported('unexpected_relation')
        return Normalized('equation',v,domain=domain_set(v,o,spec))
    if isinstance(v,(s.Set,s.MatrixBase,s.Tuple)):raise Unsupported('unexpected_structured_value')
    if v.has(s.zoo,s.nan):raise Invalid('undefined_mathematical_value')
    domain=domain_set(v,o,spec)
    if domain==s.EmptySet:raise Invalid('empty_expression_domain')
    if spec.domain=='real' and not v.free_symbols and v.is_real is False:raise Invalid('nonreal_answer_in_real_domain')
    if unit or spec.unit:
        if is_percent:raise Unsupported('percent_with_physical_unit')
        effective=unit or spec.unit
        if spec.unit and effective!=spec.unit and not spec.allow_unit_conversion:raise Invalid('wrong_requested_unit')
        u=UNITS[effective]
        return Normalized('quantity',v*u.scale,domain=domain,unit=effective,dimension=u.dimension,notes=[f'direction={direction}' if direction else 'direction=unspecified'])
    if direction:raise Unsupported('uninterpreted_direction_of_change')
    if is_percent or spec.percent_mode=='percent_number':v=v/100
    return Normalized('expression',v,domain=domain,notes=['exact percentage fraction'] if is_percent or spec.percent_mode else [])
