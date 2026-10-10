"""Train transparent rules on discovery-train only; one fixed development gate."""
from common import *
from states import features
from collections import Counter

RULES={
 'candidate_clear':lambda f:f['explicit_candidate'] and not f['recent_unresolved'],
 'candidate_checked':lambda f:f['explicit_candidate'] and f['checks_seen']>=1 and not f['recent_unresolved'],
 'candidate_constraints':lambda f:f['explicit_candidate'] and f['constraint_check_seen'] and not f['recent_unresolved'],
 'candidate_stable':lambda f:f['explicit_candidate'] and f['stable_candidate_repeats']>=2 and not f['recent_unresolved'],
 'never':lambda f:False}

def decision(method,state,rule):
    f=features(state['reasoning_state'])
    if method=='B1_fixed':return 'B'
    if method=='B2_candidate':return 'B' if f['explicit_candidate'] else 'A'
    if method=='B3_repetition':return 'B' if f['repetitions_seen'] else 'A'
    if method=='candidate_with_C':return 'C' if f['explicit_candidate'] else 'A'
    if method=='always_C':return 'C'
    if method=='B4_counterfactual':return 'C' if RULES[rule](f) else 'A'
    return 'A'

def policy_metrics(states,outcomes,method,rule):
    selected=[outcomes[(s['state_id'],decision(method,s,rule))] for s in states]
    controls=[outcomes[(s['state_id'],'A')] for s in states]
    return dict(method=method,n=len(states),correct=sum(r['status']=='correct' for r in selected),
        incorrect=sum(r['status']=='incorrect' for r in selected),unknown=sum(r['status']=='unknown' for r in selected),
        incomplete=sum(r['status']=='prediction_incomplete' for r in selected),
        input_tokens=sum(r['input_tokens'] for r in selected),output_tokens=sum(r['output_tokens'] for r in selected),
        total_tokens=sum(r['total_tokens'] for r in selected),
        continuation_saving_vs_A=sum(a['total_tokens']-b['total_tokens'] for a,b in zip(controls,selected)),
        triggers=sum(decision(method,s,rule)!='A' for s in states),
        negative_transfers=sum(a['status']=='correct' and b['status']!='correct' for a,b in zip(controls,selected)),
        confirmed_negative_transfers=sum(a['status']=='correct' and b['status']=='incorrect' for a,b in zip(controls,selected)),
        positive_transfers=sum(a['status']!='correct' and b['status']=='correct' for a,b in zip(controls,selected)))

def main():
    for p,h in read(OUT/'evidence/COUNTERFACTUAL_SEALED.json')['files'].items():assert sha(OUT/p)==h
    states=jl(OUT/'counterfactual_states.jsonl');smap={s['state_id']:s for s in states}
    labels={r['task_id']:r['reference_raw'] for r in jl(OUT/'data/discovery_labels.jsonl')}
    records=[];raws={}
    for s in states:
        for branch in 'ABC':
            job=s['state_id']+'__'+branch;r=read(OUT/'raw'/(job+'.json'));raws[job]=r
            assert r['status']=='completed' and r['usage_known']
            records.append(dict(record_id=job,source_job_id=job,task_id=s['task_id'],branch=branch,subject=s['subject'],level=s['level'],
                question=s['problem'],reference_raw=labels[s['task_id']],prediction_raw=r['response']['choices'][0]['message']['content'],
                finish_reason=r['response']['choices'][0]['finish_reason'],response_hash=r['response_hash'],request_hash=r['request_hash'],
                source_path='raw/'+job+'.json',submission_sealed=True))
        candidate=s['reasoning_state']['current_candidate']
        if candidate:
            records.append(dict(record_id=s['state_id']+'__candidate',source_job_id=s['state_id']+'__candidate',task_id=s['task_id'],branch='candidate',
                subject=s['subject'],level=s['level'],question=s['problem'],reference_raw=labels[s['task_id']],
                prediction_raw='The answer is '+candidate+'.',finish_reason='stop',submission_sealed=True))
    scorepath=OUT/'evidence/counterfactual_v3.jsonl'
    if scorepath.exists():grades=jl(scorepath)
    else:grades=frozen_evaluator().evaluate_batch(records);lines(scorepath,grades)
    gmap={g['record_id']:g for g in grades};out=[]
    for s in states:
        candidate=gmap.get(s['state_id']+'__candidate')
        for branch in 'ABC':
            job=s['state_id']+'__'+branch;r=raws[job];g=gmap[job]
            c=g.get('prediction_normalized');prior=candidate.get('prediction_normalized') if candidate else None
            changed=(c!=prior) if c and prior else None
            out.append(dict(job_id=job,state_id=s['state_id'],task_id=s['task_id'],subject=s['subject'],discovery_split=s['discovery_split'],position_kind=s['position_kind'],
                branch=branch,status=g['status'],reason=g['reason'],prediction_extracted=g['prediction_extracted'],
                candidate_before_status=candidate['status'] if candidate else 'unobserved',
                candidate_changed=changed,candidate_change_semantics='normalized structures differ; None if either unavailable',
                omitted_constraints='not inferred from answer mismatch; requires explicit mathematical audit',
                complete=r['response']['choices'][0]['finish_reason']=='stop' and bool(r['response']['choices'][0]['message']['content'].strip()),
                **{k:r[k] for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens','response_hash','request_hash')},
                response_path='raw/'+job+'.json',prefix_generation_tokens_estimate=s['prefix_generation_tokens_estimate'],
                prefix_generation_exact_tokens='unavailable',mode=r['meta']['mode']))
    lines('counterfactual_outcomes.jsonl',out)
    omap={(r['state_id'],r['branch']):r for r in out}
    train=[s for s in states if s['discovery_split']=='train'];dev=[s for s in states if s['discovery_split']=='development']
    fit=[]
    for name in read(OUT/'config.json')['rule_family']:
        fired=[s for s in train if RULES[name](features(s['reasoning_state']))]
        m=policy_metrics(train,omap,'B4_counterfactual',name)
        m.update(rule=name,training_safe=bool(len(fired)>=2 and all(omap[(s['state_id'],'C')]['status']=='correct' for s in fired) and m['continuation_saving_vs_A']>0))
        fit.append(m)
    eligible=[m for m in fit if m['training_safe']]
    rule=max(eligible,key=lambda m:(m['continuation_saving_vs_A'],-read(OUT/'config.json')['rule_family'].index(m['rule'])))['rule'] if eligible else 'never'
    save('evidence/frozen_controller_rule.json',dict(at=now(),selected_rule=rule,fitting_tasks=sorted({s['task_id'] for s in train}),development_labels_used_to_fit=False,
        training_candidates=fit,decision='C if selected public feature rule fires, otherwise A',source_sha256=sha(Path(__file__))))
    metrics=[]
    methods=['A_normal','B1_fixed','B2_candidate','B3_repetition','candidate_with_C','always_C','B4_counterfactual']
    for split,subset in [('train',train),('development',dev),('all',states)]:
        for method in methods:metrics.append(dict(split=split,**policy_metrics(subset,omap,method,rule)))
    csvfile('early_completion_risk.csv',metrics)
    decisions=[]
    for s in states:
        for method in methods:
            branch=decision(method,s,rule)
            decisions.append(dict(state_id=s['state_id'],task_id=s['task_id'],split=s['discovery_split'],method=method,branch=branch,
                triggered=branch!='A',rule=rule if method=='B4_counterfactual' else method,
                public_features=features(s['reasoning_state']),online_execution=False,scope='offline policy audit on actual counterfactual outcomes; no end-to-end online savings claim'))
    lines('controller_decisions.jsonl',decisions)
    successful=[]
    for s in states:
        a=omap[(s['state_id'],'A')]
        for branch in 'BC':
            b=omap[(s['state_id'],branch)]
            if a['status']=='correct' and b['status']=='correct' and b['total_tokens']<=.9*a['total_tokens']:
                successful.append(dict(state_id=s['state_id'],task_id=s['task_id'],subject=s['subject'],branch=branch,saving=a['total_tokens']-b['total_tokens']))
    dm=next(m for m in metrics if m['split']=='development' and m['method']=='B4_counterfactual')
    checks=dict(paired_successful_states=len({x['state_id'] for x in successful})>=4,
        diverse_subjects=len({x['subject'] for x in successful})>=2,training_rule_improved=rule!='never',
        development_triggers=dm['triggers']>=2,development_no_negative_transfer=dm['negative_transfers']==0,
        development_continuation_cost_saving=dm['continuation_saving_vs_A']>0)
    gate=all(checks.values())
    save('evidence/online_gate.json',dict(at=now(),run_online_pilot=gate,checks=checks,development_metric=dm,
        counterfactual_positive_cases=successful,reason='All frozen discovery and development checks must pass. No threshold retuning.',
        actual_online_billing_savings_measured=False))
    taskrows=[]
    for tid in sorted({s['task_id'] for s in states}):
        ss=[s for s in states if s['task_id']==tid];rr=[r for r in out if r['task_id']==tid]
        success=[s for s in ss if any(omap[(s['state_id'],b)]['status']=='correct' for b in 'BC')]
        taskrows.append(dict(task_id=tid,subject=ss[0]['subject'],n_states=len(ss),historical_high_correct=True,
            any_early_correct=bool(success),earliest_tested_successful_fraction=min(s['observed_fraction'] for s in success) if success else None,
            any_BC_incorrect=any(r['branch'] in 'BC' and r['status']=='incorrect' for r in rr),
            any_BC_incomplete=any(r['branch'] in 'BC' and r['status']=='prediction_incomplete' for r in rr),
            any_BC_unknown=any(r['branch'] in 'BC' and r['status']=='unknown' for r in rr),
            any_A_correct_BC_wrong=any(omap[(s['state_id'],'A')]['status']=='correct' and any(omap[(s['state_id'],b)]['status']=='incorrect' for b in 'BC') for s in ss),
            wrong_candidate_submitted=sum(r['candidate_before_status']=='incorrect' and r['status']=='incorrect' and r['candidate_changed'] is False for r in rr if r['branch'] in 'BC'),
            oracle_only=True,new_research_tokens=sum(r['total_tokens'] for r in rr)))
    lines('task_results.jsonl',taskrows);csvfile('task_pairwise.csv',taskrows)
    save('evidence/counterfactual_summary.json',dict(tasks=20,states=len(states),calls=len(out),
        by_branch={b:dict(Counter(r['status'] for r in out if r['branch']==b)) for b in 'ABC'},
        any_early_correct_tasks=sum(r['any_early_correct'] for r in taskrows),
        historical_correct_to_any_BC_incorrect_tasks=sum(r['any_BC_incorrect'] for r in taskrows),
        historical_correct_to_any_BC_incomplete_tasks=sum(r['any_BC_incomplete'] for r in taskrows),
        paired_A_correct_to_BC_incorrect_tasks=sum(r['any_A_correct_BC_wrong'] for r in taskrows),
        paired_actual_continuation_saving_states=len({r['state_id'] for r in successful}),
        paired_actual_continuation_saving_tasks=len({r['task_id'] for r in successful}),
        selected_rule=rule,online_gate_passed=gate,development_metric=dm))
    print(json.dumps(read(OUT/'evidence/counterfactual_summary.json'),ensure_ascii=False))
if __name__=='__main__':main()
