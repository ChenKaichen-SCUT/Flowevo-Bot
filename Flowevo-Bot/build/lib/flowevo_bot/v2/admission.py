"""Shadow admission and production routing remain separate, with old thresholds."""
import math
import statistics
from ..common import digest
from ..skill_validator import wilson
from .skills import MacroSkill

THRESHOLDS={'min_source_traces':3,'min_dev_eligible_cases':10,'reject_observed_harm':True,
            'saving_lower_bound_gt':0,'expected_future_uses':100,'router_min_confidence':0.8,
            'router_max_accuracy_drop':0.01}


def decide(skill,pairs,*,source_consistent=True,mathematically_reviewed=True,independent=False,build_cost=0):
    n=len(pairs);known=[r for r in pairs if r['base_correct'] is not None and r['skill_correct'] is not None]
    harm=sum(r['base_correct'] is True and r['skill_correct'] is False for r in known)
    benefit=sum(r['base_correct'] is False and r['skill_correct'] is True for r in known)
    savings=[r['base_tokens']-r['skill_tokens'] for r in pairs]
    mean=statistics.mean(savings) if n else None
    lower=mean-1.96*statistics.stdev(savings)/math.sqrt(n) if n>1 else None
    stats={'n':n,'independent':independent,'unknown_pairs':n-len(known),'harm':harm,'benefit':benefit,
           'mean_saving':mean,'saving_lower_bound':lower,'confidence':n/(n+10),
           'accuracy_drop_upper':max(0,wilson(harm,len(known))[1]-wilson(benefit,len(known))[0]),
           'projected_100_use_net_saving':mean*100-build_cost if n else None,
           'pairwise':pairs,'evidence_hash':digest(pairs)}
    gates={'math_conditions':mathematically_reviewed,'source_consistency':source_consistent,
        'sources':len(set(skill.source_task_ids))>=3,'independent_dev':independent and n>0,
        'no_observed_harm':harm==0,'dev_count':n>=10,'complete_scoring':len(known)==n and n>0,
        'structural_variation':any(r.get('structurally_distinct',False) for r in pairs),
        'positive_saving_lower_bound':lower is not None and lower>0,
        'positive_100_use_net_saving':mean is not None and mean*100>build_cost}
    reasons=[k for k,v in gates.items() if not v]
    if not mathematically_reviewed or harm:state='quarantine'
    elif not source_consistent:state='candidate'
    elif reasons:state='shadow'
    else:state='active'
    raw=skill.model_dump(mode='json',by_alias=True)
    raw.update(status='shadow',admission_certificate='',validation_stats=stats,
               token_history={**skill.token_history,'admission_full_allocated_cost':build_cost})
    prepared=MacroSkill.model_validate(raw)
    raw.update(status=state,admission_certificate=prepared.certificate() if state=='active' else '')
    return MacroSkill.model_validate(raw),{'skill_id':skill.skill_id,'status':state,'gates':gates,'blocked_by':reasons,'statistics':stats,'thresholds':THRESHOLDS}


def route_reason(skill,problem_tokens=None):
    s=skill.validation_stats
    if skill.status!='active':return 'base: no admitted active skill'
    if s['confidence']<.8:return 'base: independent sample confidence below 0.8'
    if s['accuracy_drop_upper']>.01:return 'base: correctness risk above 1 percentage point'
    if s['mean_saving']<=0 or s['saving_lower_bound']<=0:return 'base: no reliable positive saving'
    lengths=[p['problem_tokens'] for p in s['pairwise']]
    if problem_tokens is not None and not min(lengths)*.5<=problem_tokens<=max(lengths)*2:
        return 'base: query length outside calibrated range'
    return 'strategy: validated positive saving within unchanged risk budget'
