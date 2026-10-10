from common import *
from states import *
import random

INSTRUCTIONS={
 'A':'Continue the mathematical analysis normally from the supplied partial reasoning. Resolve unfinished work and submit a complete answer. End with: The answer is [your answer].',
 'B':'Use the result already supported by the supplied partial reasoning and finish the answer immediately. Avoid restarting the derivation or adding optional checks. If essential computation is missing, complete only what is needed to answer. End with: The answer is [your answer].',
 'C':'Before finishing, briefly check only the essential mathematical conditions, critical arithmetic, and the exact quantity requested. Correct any detected error, then submit the answer without redundant re-derivation. End with: The answer is [your answer].'}

def main():
    assert not (OUT/'evidence/counterfactual_freeze.json').exists()
    inventory=jl(OUT/'evidence/trace_inventory.jsonl')
    events={r['task_id']:r for r in jl(OUT/'reasoning_events.jsonl')}
    public={r['task_id']:r for r in jl(HIGH/'data/public_tasks.jsonl')}
    high={r['task_id']:r for r in jl(HIGH/'baseline_results.jsonl')}
    labels={r['task_id']:r['reference_raw'] for r in jl(HIGH/'data/offline_labels.jsonl')}
    chosen=[]
    revision_override={'counting_probability':'math_test_counting_probability_126','number_theory':'math_test_number_theory_536','prealgebra':'math_test_prealgebra_3','precalculus':'math_test_precalculus_99'}
    for subject in sorted({r['subject'] for r in inventory}):
        pool=[r for r in inventory if r['subject']==subject and r['high_v3']=='correct' and r['high_math_confirmed'] is True]
        used=set();group=[]
        for category in ('long','revision','repeat','late_candidate','medium'):
            eligible=[r for r in pool if r['task_id'] not in used]
            if category=='long':selected=max(eligible,key=lambda r:r['reasoning_tokens'])
            elif category=='revision':selected=next(r for r in eligible if r['task_id']==revision_override[subject])
            elif category=='repeat':
                candidates=[r for r in eligible if r['stable_candidate_repeats']>=2 and r['reasoning_tokens']<=4500]
                selected=max(candidates,key=lambda r:r['reasoning_tokens'])
            elif category=='late_candidate':
                candidates=[r for r in eligible if 1800<=r['reasoning_tokens']<=4200 and (r['first_candidate_fraction'] is None or r['first_candidate_fraction']>.85)]
                selected=max(candidates,key=lambda r:r['reasoning_tokens'])
            else:selected=min([r for r in eligible if 600<=r['reasoning_tokens']<=1800],key=lambda r:abs(r['reasoning_tokens']-1200))
            used.add(selected['task_id']);group.append(dict(selected,selection_category=category))
        order=list(range(5));random.Random(20261011+len(chosen)).shuffle(order)
        for i,r in enumerate(group):r['discovery_split']='train' if i in order[:3] else 'development'
        chosen+=group
    states=[]
    for selected in chosen:
        tid=selected['task_id'];h=high[tid];raw=read(HIGH/h['response_path']);text=raw['response']['choices'][0]['message']['reasoning_content'];p=public[tid]
        primary_fraction=.25 if selected['selection_category']=='long' else .5
        planned=[('primary',boundary_near(text,primary_fraction),primary_fraction)]
        # Two extra states per subject: explicit candidate/check boundaries and
        # 25/75% positions, chosen before any new answer exists.
        if selected['selection_category']=='revision' and selected['subject'] in ('number_theory','counting_probability'):
            candidates=events[tid]['explicit_candidates']
            if candidates:
                end=next((end for _,end,_ in paragraphs(text) if end>=candidates[0]['end'] and safe_boundary(text,end)),None)
                planned.append(('after_first_candidate',end,None))
        if selected['selection_category']=='repeat' and selected['subject'] in ('number_theory','prealgebra'):
            candidates=events[tid]['explicit_candidates'];first=candidates[0]['end'] if candidates else 0
            check=next((e for e in events[tid]['events'] if e['event']=='verification_discussion' and e.get('start',0)>=first and e['end']<len(text) and safe_boundary(text,e['end'])),None)
            planned.append(('after_check' if check else 'three_quarters',check['end'] if check else boundary_near(text,.75),None if check else .75))
        if selected['selection_category']=='repeat' and selected['subject'] in ('counting_probability','precalculus'):
            planned.append(('three_quarters',boundary_near(text,.75),.75))
        if selected['selection_category']=='medium' and selected['subject'] in ('prealgebra','precalculus'):
            planned.append(('one_quarter',boundary_near(text,.25),.25))
        for label,pos,fraction in planned:
            assert pos and 0<pos<len(text) and safe_boundary(text,pos),(tid,label,pos)
            prefix=text[:pos];state=observe(tid,p['problem'],prefix)
            states.append(dict(state_id=tid+'__'+label,task_id=tid,problem=p['problem'],subject=p['subject'],level=p['level'],
                position_kind=label,target_fraction=fraction,cut_char=pos,total_trace_chars=len(text),observed_fraction=pos/len(text),
                prefix=prefix,prefix_sha256=digest(prefix),historical_response_hash=raw['response_hash'],
                historical_raw_path=str((HIGH/h['response_path']).relative_to(ROOT)),
                prefix_generation_tokens_estimate=h['reasoning_tokens']*pos/len(text),
                prefix_token_estimate_method='character fraction of full exact reasoning token count; not a billing measurement',
                discovery_split=selected['discovery_split'],selection_category=selected['selection_category'],
                reasoning_state=asdict(state)))
    assert len(chosen)==20 and len(states)==28
    lines('counterfactual_states.jsonl',states);lines('data/discovery_labels.jsonl',[dict(task_id=r['task_id'],reference_raw=labels[r['task_id']]) for r in chosen])
    csvfile('reasoning_state_features.csv',[dict(state_id=s['state_id'],discovery_split=s['discovery_split'],position_kind=s['position_kind'],**features(s['reasoning_state'])) for s in states])
    save('dataset_manifest.json',dict(created_at=now(),historical_n=605,discovery_n=20,discovery_states=28,
        independent_n=0,discovery_is_not_independent=True,selected_tasks=chosen,
        historical_data={str(p.relative_to(ROOT)):sha(p) for p in [HIGH/'data/public_tasks.jsonl',HIGH/'data/offline_labels.jsonl',HIGH/'baseline_results.jsonl',LOW/'results.jsonl']},
        selection='Five strata per subject; long at25%, others50%;8 additional semantic/25/75% states. All chosen before interventions. Selection intentionally enriched for potential compression and negative controls.',
        negative_controls='Wrong candidate14 before15: number_theory_536; long dodecahedron trajectory considers1 before10/19; late-candidate strata before key computations. Revision cue strata alone do not certify a real correction.'))
    cfg=dict(model='deepseek-flash',mode=read(OUT/'evidence/api_feasibility.json')['mode'],max_tokens=2048,
        api_workers=64,local_workers=12,gold_feedback=False,skill_injection=False,max_calls=150,max_total_tokens=350000,
        instructions=INSTRUCTIONS,planned_counterfactual_calls=84,maximum_conditional_pilot_tasks=8,
        stage4_gate=dict(min_successful_cost_saving_states=4,min_subjects=2,min_paired_continuation_saving_fraction=.10,
            development_positive_transfers_min=0,development_negative_transfers_max=0,development_triggers_min=2,
            require_public_state_rule_train_savings=True,require_known_usage=True),
        rule_family=['candidate_clear','candidate_checked','candidate_constraints','candidate_stable'],
        fitting='Fit on train tasks only. Choose safe rule with maximal total continuation savings; if no safe improving rule, always continue. Evaluate once on development tasks; do not retune.',
        conditional_pilot='Only if discovery and development gates pass; at most8 new tasks, shrunk from30-50 to fit150/350000. A paired shared measured first stage for B1-B4; logical per-method costs include that stage each time. B0 fresh16384.')
    save('config.json',cfg)
    prefix_est=sum(s['prefix_generation_tokens_estimate']*3 for s in states)
    forecast=dict(counterfactual_calls=84,prefix_input_tokens_estimate=round(prefix_est),prompt_overhead_tokens_estimate=84*250,
        suffix_output_tokens_typical_estimate=84*600,suffix_output_tokens_max=84*2048,
        typical_counterfactual_total=round(prefix_est+84*850),
        warning='Prefix estimates are not exact API usage. Scheduler reserves UTF8-byte input upper bounds and max_output_tokens; all stages stop before user cap. Independent size will be chosen before its outputs based on remaining budget.',
        peak_uncached_typical_usd=round((prefix_est+84*250)*.3e-6+(84*600)*1.2e-6,6))
    save('evidence/counterfactual_cost_forecast.json',forecast)
    sources=list((OUT/'code').glob('*.py'))+[OUT/'config.json',OUT/'counterfactual_states.jsonl',OUT/'data/discovery_labels.jsonl',OUT/'dataset_manifest.json']
    save('evidence/counterfactual_freeze.json',dict(at=now(),files={str(p.relative_to(ROOT)):sha(p) for p in sources},counterfactual_results_read=False))
    print(json.dumps(dict(tasks=[(s['task_id'],s['selection_category'],s['discovery_split']) for s in chosen],states=len(states),forecast=forecast)))
if __name__=='__main__':main()
