"""Manually specified whole-question semantics, shared without differences by B/C."""
import re
from dataclasses import dataclass,asdict
from flowevo_bot.rmmd.macros import normalized_question
from .expression import parse_expression,ScopeError,MAX_MODULUS,structure

@dataclass
class Goal:
    parsed:bool=False
    expression:tuple|None=None
    modulus:int|None=None
    kind:str|None=None
    reason:str='semantic_unsupported_whole_question'
    grammar:str|None=None
    def to_dict(self):return asdict(self)

def parse_goal(question):
    if not isinstance(question,str) or len(question)>10000:return Goal(reason='question_size_budget')
    nq,fs=normalized_question(question)
    def literal(token):
        t=fs[int(token[1:])]['text'] if token.startswith('M') else token
        t=t.strip().rstrip('.,?')
        if not re.fullmatch(r'\d+',t) or len(t)>5:raise ScopeError('positive_integer_modulus_required')
        m=int(t)
        if not 2<=m<=MAX_MODULUS:raise ScopeError('modulus_budget')
        return m
    residue=re.fullmatch(r'(?:Find|Determine|What is) the remainder (?:when|of|upon dividing) (?:(?:the )?(number|sum|product) )?M(\d+) (?:is )?divided by (M\d+|\d+)\s*[.?]?',nq,re.I)
    units=re.fullmatch(r'(?:Find|Determine|What is) the (?:units|last) digit of M(\d+)\s*[.?]?',nq,re.I)
    if not residue and not units:return Goal()
    try:
        index=int(residue[2] if residue else units[1]);expr=parse_expression(fs[index]['text'])
        m=literal(residue[3]) if residue else 10
        if residue and residue[1] in ('sum','product') and expr[0]!=('add' if residue[1]=='sum' else 'mul'):raise ScopeError('noun_expression_mismatch')
        if units and '-' in fs[index]['text']:raise ScopeError('signed_units_digit_outside_semantic_scope')
        return Goal(True,expr,m,'integer_remainder','ok','explicit_remainder' if residue else 'decimal_units_digit')
    except (ScopeError,IndexError,ValueError) as exc:return Goal(reason='guard_'+str(exc))
