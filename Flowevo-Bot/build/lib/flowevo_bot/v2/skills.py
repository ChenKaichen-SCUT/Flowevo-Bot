"""Typed three-valued triggers. Guards are obligations, never word predicates."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ..common import digest
from ..token_accounting import estimate_tokens


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,populate_by_name=True)


class Trigger(Strict):
    feature: str | None = None
    all_of: list['Trigger'] | None = None
    any_of: list['Trigger'] | None = None
    negation: 'Trigger | None' = Field(default=None,alias='not')
    optional: 'Trigger | None' = None
    guard: str | None = None

    @model_validator(mode='after')
    def one_operator(self):
        if sum(x is not None for x in [self.feature,self.all_of,self.any_of,self.negation,self.optional,self.guard])!=1:
            raise ValueError('Exactly one trigger operator required')
        if self.all_of==[] or self.any_of==[]:raise ValueError('Empty logical operator')
        return self


def evaluate(trigger, facts):
    if trigger.feature is not None:
        value=facts.get(trigger.feature)
        return {'value':value,'feature':trigger.feature,'reason':'observed' if value is not None else 'unknown'}
    if trigger.guard is not None:
        return {'value':True,'guard_obligation':trigger.guard,'guard_passed':False,'reason':'deferred_to_solver'}
    if trigger.optional is not None:
        return {'value':True,'optional_evidence':evaluate(trigger.optional,facts)}
    if trigger.negation is not None:
        child=evaluate(trigger.negation,facts)
        return {'value':None if child['value'] is None else not child['value'],'not':child}
    op='all_of' if trigger.all_of is not None else 'any_of'
    children=[evaluate(t,facts) for t in getattr(trigger,op)];values=[r['value'] for r in children]
    if op=='all_of':value=False if False in values else None if None in values else True
    else:value=True if True in values else None if None in values else False
    return {'value':value,op:children}


class Guard(Strict):
    kind: Literal['denominator_nonzero','inequality_sign','back_substitution','disjoint_exhaustive_cases','order_repetition','equal_orbit_size']
    instruction: str
    policy: Literal['verify_or_fallback']='verify_or_fallback'


class MacroSkill(Strict):
    schema_version:Literal['2.0']='2.0'
    skill_id:str
    predecessor:str
    subject:str
    name:str
    steps:list[str]=Field(min_length=2,max_length=5)
    compact_prompt:str
    trigger:Trigger
    guards:list[Guard]=Field(min_length=1)
    source_task_ids:list[str]=Field(min_length=3)
    source_trace_hashes:list[str]=Field(min_length=3)
    transformation_evidence:list[dict]
    status:Literal['candidate','shadow','active','quarantine']='candidate'
    validation_stats:dict=Field(default_factory=dict)
    token_history:dict=Field(default_factory=dict)
    admission_certificate:str=''

    @model_validator(mode='after')
    def consistent(self):
        if len(set(self.source_task_ids))!=len(self.source_task_ids) or len(self.source_task_ids)!=len(self.source_trace_hashes):
            raise ValueError('Inconsistent multi-trace provenance')
        if estimate_tokens(self.compact_prompt)>120:raise ValueError('Compact strategy exceeds approximate 100-token budget (120 cap)')
        if self.status=='active' and self.admission_certificate != self.certificate():raise ValueError('Active skill lacks bound admission certificate')
        return self

    def certificate(self):
        return digest(self.model_dump(exclude={'status','admission_certificate'},mode='json',by_alias=True))


def guarded_obligations(skill,features):
    """These are LLM-executed math guards, not fabricated machine proofs.

    The solver receives the guard-bearing short prompt. If a precondition cannot
    be verified, the strategy explicitly requests ordinary solving. No external
    verifier or gold-based retry is used; all unresolved guards remain unverified.
    """
    return [{'kind':g.kind,'status':'solver_obligation_unverified','passed':None,
             'instruction':g.instruction,'policy':g.policy,
             'public_evidence':features.get('variable_denominators',[]) if g.kind=='denominator_nonzero' else []}
            for g in skill.guards]


def check_nonzero(value):
    return None if value.is_zero is None else not bool(value.is_zero)


def multiplication_direction(value):
    if value.is_positive:return 'preserve'
    if value.is_negative:return 'reverse'
    return 'forbidden' if value.is_zero else 'split_sign_cases'


def symmetry_quotient(total,orbit_sizes):
    if not orbit_sizes or len(set(orbit_sizes))!=1 or orbit_sizes[0]<=0:return None
    from fractions import Fraction
    return Fraction(total,orbit_sizes[0])


def trigger_for(family):
    if family=='S07':
        return Trigger.model_validate({'all_of':[{'feature':'subject:intermediate_algebra'},
          {'any_of':[{'feature':'math:rational_equation'},{'feature':'math:rational_inequality'}]},
          {'not':{'feature':'lex:trigonometric'}},{'not':{'feature':'lex:hypothetical_options'}},{'guard':'denominator_nonzero'}]})
    return Trigger.model_validate({'all_of':[{'feature':'subject:counting_probability'},
        {'feature':'lex:count_request'},{'feature':'lex:count_constraints'},
        {'optional':{'feature':'lex:order'}},{'guard':'disjoint_exhaustive_cases'}]})


def guards_for(family):
    if family=='S07':
        kinds=[('denominator_nonzero','Record and exclude zeros of every original denominator.'),
               ('inequality_sign','Never multiply an inequality by an unknown-sign denominator; use sign cases or a sign chart.'),
               ('back_substitution','Retain substitution range and separately handle excluded zero cases; check solutions/endpoints in the original relation.')]
    else:
        kinds=[('order_repetition','Establish order, distinguishability, and permitted repetitions from the question.'),
               ('disjoint_exhaustive_cases','Ensure cases exhaust the valid sample space and count overlaps exactly once.'),
               ('equal_orbit_size','Divide a symmetry count only after proving equal orbit sizes or a free action; otherwise count fixed points/cases.')]
    return [Guard(kind=k,instruction=v) for k,v in kinds]
