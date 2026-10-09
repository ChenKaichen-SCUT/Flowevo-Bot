"""Auditable multi-trace macro mining, followed by paid textual distillation.

Family templates and safety guards are engineered priors, not claimed as learned.
The macro steps/short prompt are learned from recorded transformation evidence.
"""
import re
from ..common import digest
from ..provenance import assert_clean_traces
from ..schemas import Trace
from .skills import MacroSkill,trigger_for,guards_for,evaluate


def transformation_evidence(trace,features,family):
    solution=trace['first_solution']
    patterns = ([('denominator_elimination',r'(?:multiply(?:ing)? (?:both sides|by)|combine the fractions|common denominator)'),
                 ('reduce_or_solve',r'(?:factor|expanding|thus|so\b|quadratic)'),
                 ('domain_recovery',r'(?:denominator|since|valid|original|ne(?:q)?|substitut)')]
                if family=='S07' else
                [('decomposition',r'(?:cases?|subtract|with no\b|ignoring|fix\b|by length|no nontrivial)'),
                 ('count_operation',r'(?:choices|\\times|\\cdot|\\binom|\d!|arrangements)'),
                 ('recombine',r'(?:total|therefore|thus|so\b|subtract|divide|sum)')])
    evidence=[]
    for stage,pattern in patterns:
        m=re.search(pattern,solution,re.I)
        if not m:return None
        evidence.append({'stage':stage,'span':[m.start(),m.end()],
                         'excerpt':solution[max(0,m.start()-65):min(len(solution),m.end()+130)]})
    if evaluate(trigger_for(family),features['facts'])['value'] is not True:return None
    # Reject an incidental reciprocal relation if no actual denominator-elimination
    # operation occurred in the successful trajectory.
    return {'task_id':trace['problem']['task_id'],'trace_hash':Trace.model_validate(trace).trace_hash,'stages':evidence,
            'structural_signature':[(r['relation'],r['numerator_degree'],(r.get('substitution') or {}).get('kind','direct')) for r in features['rational_relations']]
                    if family=='S07' else {'order':features['lexical']['order'],'repetition':features['lexical']['repetition'],'symmetry':features['lexical']['symmetry_action']}}


def distill_prompt(family,sources,evidence):
    assert_clean_traces([Trace.model_validate(t) for t in sources],3)
    import json
    guards=guards_for(family)
    return ('Learn ONE medium-grained reusable mathematical macro from the successful FIRST-PASS model traces below. '
            'These are training examples; do not memorize numeric answers or return a menu of unrelated tools. '
            'The common transformation sequence is recorded with exact spans. Explain only that common method. '
            'Return JSON only, with fields name (string), steps (2 to 5 strings), compact_prompt (string). '
            'The compact prompt must be AT MOST 340 UTF-8 bytes (~100 tokens), including necessary safeguards. '
            'Start with the method directly. No generic exhortations. '
            'The short prompt MUST express every guard below; do not sacrifice mathematical conditions for brevity. '
            + ('Include denominator nonzero, sign handling, substitution range/zero cases, original-relation check. '
               if family=='S07' else 'Include order/repeats, disjoint/exhaustive cases or complement, overlap checks, and symmetry division ONLY for equal orbit size/free action; otherwise case count. ')
            +'Guards: '+json.dumps([g.model_dump() for g in guards])+'\n'
            +'Examples: '+json.dumps([{'task_id':t['problem']['task_id'],'problem':t['problem']['problem'],
                                     'model_first_solution':t['first_solution'],'transformations':e} for t,e in zip(sources,evidence)],ensure_ascii=False))


def build_skill(family,predecessor,raw,sources,evidence,call_cost):
    import json
    data=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()))
    if set(data)!={'name','steps','compact_prompt'}:raise ValueError('Unexpected distillation fields')
    compact=data['compact_prompt'];low=compact.lower()
    required=([r'denomin|nonzero',r'sign',r'zero',r'range|domain',r'original|back.sub'] if family=='S07' else
              [r'order',r'repeat|repetit|identical|distin(?:ct|guish)',r'disjoint',r'exhaust|complement',r'overlap',r'equal.orbit|orbits.{0,12}equal|free.action|uniform.*orbit'])
    if len(compact.encode())>340 or any(not re.search(p,low) for p in required):
        raise ValueError('Short prompt omitted a necessary guard or exceeds 340 bytes')
    return MacroSkill(skill_id=family+'_v2_'+digest(data)[:12],predecessor=predecessor,
        subject=sources[0]['problem']['subject'],name=data['name'],steps=data['steps'],compact_prompt=compact,
        trigger=trigger_for(family),guards=guards_for(family),source_task_ids=[t['problem']['task_id'] for t in sources],
        source_trace_hashes=[Trace.model_validate(t).trace_hash for t in sources],transformation_evidence=evidence,status='shadow',
        token_history={'distillation_and_revision':call_cost})
