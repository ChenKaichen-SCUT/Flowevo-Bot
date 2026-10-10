from common import *
import collections,random
sys.path.insert(0,str(ROOT/'Flowevo-Bot/src'))
from flowevo_bot.taxonomy import normalize_subject
from flowevo_bot.features import normalize_problem
from rapidfuzz import process,fuzz

def main():
    assert read(OUT/'evidence/online_gate.json')['run_online_pilot']
    assert not (OUT/'evidence/pilot_freeze.json').exists()
    registry=read(ROOT/'experiments/math500_scoring_and_budget_v2/evidence/exposure_registry.json')
    excluded=set(registry['excluded_ids'])
    recent=[]
    for file in [HIGH/'data/public_tasks.jsonl',ROOT/'experiments/math500_scoring_and_budget_v2/data/public_tasks.jsonl',ROOT/'experiments/failure_mechanism_a1_a2_pilot/data/public_tasks.jsonl']:
        recent+=jl(file)
    excluded.update(r['task_id'] for r in recent)
    prior_screen={r['task_id']:r for r in jl(ROOT/'experiments/math500_scoring_and_budget_v2/evidence/global_near_duplicate_screen.jsonl')}
    comparisons={r['task_id']:normalize_problem(r['problem'],True) for r in recent}
    local=[];count=collections.Counter()
    for row in jl(ROOT/'FlowEvo/data/datasets/math/test.jsonl'):
        sub=normalize_subject(row['type']);tid=f'math_test_{sub}_{count[sub]}';count[sub]+=1
        if tid in excluded or tid not in prior_screen or prior_screen[tid]['excluded_near_duplicate']:continue
        local.append(dict(row,task_id=tid,subject=sub))
    selected=[];audit=[]
    strata=[('counting_probability','Level 2'),('number_theory','Level 3'),('prealgebra','Level 4'),('precalculus','Level 4')]
    for i,(subject,level) in enumerate(strata):
        candidates=sorted([r for r in local if r['subject']==subject and r['level']==level],key=lambda r:r['task_id'])
        random.Random(20261011+i).shuffle(candidates)
        for row in candidates:
            hit=process.extractOne(normalize_problem(row['problem'],True),comparisons,scorer=fuzz.ratio,score_cutoff=90)
            audit.append(dict(task_id=row['task_id'],subject=subject,level=level,near_match=hit,accepted=hit is None))
            if hit is None:
                selected.append(row);comparisons[row['task_id']]=normalize_problem(row['problem'],True);break
        else:raise RuntimeError('No clean task in stratum '+subject+' '+level)
    public=[{k:r[k] for k in ('task_id','subject','level','problem')} for r in selected]
    labels=[dict(task_id=r['task_id'],reference_raw=r['solution']) for r in selected]
    lines('data/independent_public.jsonl',public);lines('data/independent_labels.jsonl',labels)
    lines('evidence/independent_exposure_screen.jsonl',audit)
    manifest=read(OUT/'dataset_manifest.json')
    manifest['independent_n']=4;manifest['independent_tasks']=[dict(task_id=r['task_id'],subject=r['subject'],level=r['level'],problem_sha256=digest(r['problem']),no_known_solve_exposure=True,prior_screen=prior_screen[r['task_id']]) for r in public]
    # Preserve the discovery-frozen original manifest; add a separate extension.
    save('independent_dataset_manifest.json',manifest)
    attempts=[read(p) for p in (OUT/'attempts').glob('*.json')]
    used=sum(a.get('total_tokens',0) for a in attempts if a['usage_known'])
    unknown=sum(a['reserved_tokens'] for a in attempts if not a['usage_known'])
    config=dict(n=4,selection_seed=20261011,baseline_max_tokens=16384,first_stage_max_tokens=1024,
        continuation_max_tokens=15360,per_method_output_cap=16384,
        methods=['B0_high','B1_fixed','B2_candidate','B3_repetition','B4_counterfactual'],
        selected_rule=read(OUT/'evidence/frozen_controller_rule.json')['selected_rule'],
        source='Fresh independently generated first stage, never a historical low-budget trace or B0 prefix',
        sharing='Identical first-stage responses and identical chosen continuation branches reused across B1-B4; logical method cost includes own share once. B0 is a separate independent call.',
        exact_billing='Never cancel inference; use server max_tokens, consume terminal usage, then optionally make another full logged call.',
        available_tokens_conservative=350000-used-unknown,forecast_allowance_per_task=12000,forecast_total=48000,
        size_reason='Discovery used most of350000-token cap; shrink suggested30-50 to4 (one per subject, levels2/3/4/4) before seeing pilot outputs. All target-subject Level5 test tasks are already exposed; no clean Level5 precalculus task passed screening, so use Level4. Engineering check only; cannot establish accuracy preservation.',
        rule_frozen_before_selection=True)
    assert config['forecast_total']<config['available_tokens_conservative']
    save('pilot_config.json',config)
    sources=[OUT/'pilot_config.json',OUT/'data/independent_public.jsonl',OUT/'data/independent_labels.jsonl',OUT/'evidence/frozen_controller_rule.json']+list((OUT/'code').glob('*.py'))
    save('evidence/pilot_freeze.json',dict(at=now(),files={str(p.relative_to(ROOT)):sha(p) for p in sources},pilot_results_read=False))
    print(json.dumps(dict(tasks=public,config=config),ensure_ascii=False))
if __name__=='__main__':main()
