from common import *
from collections import Counter,defaultdict

def grade_pilot():
    for p,h in read(OUT/'evidence/PILOT_SEALED.json')['files'].items():assert sha(OUT/p)==h
    rows=jl(OUT/'independent_ungraded.jsonl')
    labels={r['task_id']:r['reference_raw'] for r in jl(OUT/'data/independent_labels.jsonl')}
    public={r['task_id']:r for r in jl(OUT/'data/independent_public.jsonl')}
    # Identical shared outputs are graded once, then referenced by each method.
    unique={r['response_path']:r for r in rows};records=[]
    for path,r in unique.items():
        raw=read(OUT/path);p=public[r['task_id']]
        records.append(dict(record_id=path,task_id=r['task_id'],branch=r['method'],subject=p['subject'],level=p['level'],
            question=p['problem'],reference_raw=labels[r['task_id']],prediction_raw=r['final_text'],finish_reason=r['finish_reason'],
            response_hash=r['response_hash'],source_path=path,submission_sealed=True))
    target=OUT/'evidence/independent_v3.jsonl'
    if target.exists():scores=jl(target)
    else:scores=frozen_evaluator().evaluate_batch(records);lines(target,scores)
    mapping={s['record_id']:s for s in scores}
    for r in rows:
        g=mapping[r['response_path']];r.update(status=g['status'],grade_reason=g['reason'],final_answer=g['prediction_extracted'])
    lines('independent_results.jsonl',rows)
    metrics=[];pairs=[]
    for method in read(OUT/'pilot_config.json')['methods']:
        rs=[r for r in rows if r['method']==method]
        baseline={r['task_id']:r for r in rows if r['method']=='B0_high'}
        m=dict(method=method,n=len(rs),correct=sum(r['status']=='correct' for r in rs),status_counts=dict(Counter(r['status'] for r in rs)),
            **{k:sum(r[k] for r in rs) for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens','logical_calls','controller_cpu_ms')},
            early_completion_tasks=sum(r['early_completion_triggered'] for r in rs),
            controller_not_triggered=sum(not r['early_completion_triggered'] for r in rs),
            additional_calls_over_single=sum(r['logical_calls']-1 for r in rs),
            negative_transfers=sum(baseline[r['task_id']]['status']=='correct' and r['status']!='correct' for r in rs),
            positive_transfers=sum(baseline[r['task_id']]['status']!='correct' and r['status']=='correct' for r in rs))
        for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens'):
            m[k+'_saved_vs_B0']=sum(baseline[r['task_id']][k]-r[k] for r in rs)
        metrics.append(m)
        for r in rs:
            b=baseline[r['task_id']]
            pairs.append(dict(task_id=r['task_id'],method=method,baseline_status=b['status'],status=r['status'],
                input_saved=b['input_tokens']-r['input_tokens'],output_saved=b['output_tokens']-r['output_tokens'],
                total_saved=b['total_tokens']-r['total_tokens'],first_stage_generated_tokens=r['first_stage_generated_tokens'],
                early_trigger=r['early_completion_triggered'],decision_branch=r['decision_branch']))
    csvfile('independent_pairwise.csv',pairs)
    save('evidence/independent_summary.json',dict(n=4,metrics=metrics,all_costs_are_measured_api_usage=True,
        pilot_size_limitation='Four fresh tasks; no claim of accuracy non-inferiority or statistical generalization',
        source_controls='Shared first stages and identical branch outputs reduce study physical calls, not a discount to logical method cost'))
    return metrics

def grade_negative():
    state=read(OUT/'evidence/negative_control_state.json')
    label=next(r['reference_raw'] for r in jl(OUT/'data/discovery_labels.jsonl') if r['task_id']==state['task_id'])
    rows=[];records=[]
    for branch in 'ABC':
        job=state['state_id']+'__'+branch;r=read(OUT/'raw'/(job+'.json'));rows.append(r)
        records.append(dict(record_id=job,task_id=state['task_id'],branch=branch,subject=state['subject'],level=state['level'],
            question=state['problem'],prediction_raw=r['response']['choices'][0]['message']['content'],reference_raw=label,
            finish_reason=r['response']['choices'][0]['finish_reason'],response_hash=r['response_hash'],submission_sealed=True))
    path=OUT/'evidence/negative_control_v3.jsonl'
    if path.exists():scores=jl(path)
    else:scores=frozen_evaluator().evaluate_batch(records);lines(path,scores)
    out=[]
    for score,r in zip(scores,rows):
        assert score['record_id']==r['job_id']
        out.append(dict(task_id=state['task_id'],state_id=state['state_id'],branch=score['branch'],status=score['status'],
            prediction=score['prediction_extracted'],**{k:r[k] for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens')},
            trained_on=False,original_wrong_candidate='14',correct_answer='15',
            proof='Stars-and-bars counts15 nonnegative digit triples of sum4;000 has sum0 and was never counted, so subtracting it is an error. Page1000 has digit sum1.'))
    lines('supplemental_negative_control_outcomes.jsonl',out)
    return out

def main():
    pilot=grade_pilot();negative=grade_negative()
    calls=sorted([read(p) for p in (OUT/'raw').glob('*.json')],key=lambda r:r['job_id'])
    attempts=[read(p) for p in (OUT/'attempts').glob('*.json')]
    assert len(attempts)==len(calls)<=150
    known=sum(r['total_tokens'] for r in calls if r['usage_known'])
    unknown=sum(a['reserved_tokens'] for a in attempts if not a['usage_known'])
    assert known+unknown<=350000
    for r in calls:
        assert r['response_hash']==digest(r['response'])
        if r['usage_known'] and r['http_status']==200:assert r['input_tokens']+r['output_tokens']==r['total_tokens']
    lines('api_calls.jsonl',calls)
    costs=[]
    for stage in sorted({r['meta']['stage'] for r in calls}):
        rr=[r for r in calls if r['meta']['stage']==stage];valid=[r for r in rr if r['usage_known']]
        costs.append(dict(scope=stage,kind='physical_research_calls',calls=len(rr),
            input_tokens=sum(r['input_tokens'] or 0 for r in valid),output_tokens=sum(r['output_tokens'] or 0 for r in valid),
            reasoning_tokens=sum(r['reasoning_tokens'] or 0 for r in valid),total_tokens=sum(r['total_tokens'] for r in valid),
            unknown_usage_calls=sum(not r['usage_known'] for r in rr),unknown_token_upper_bound=sum(r['reserved_tokens'] for r in rr if not r['usage_known'])))
    for m in pilot:
        costs.append(dict(scope=m['method'],kind='logical_independent_method',calls=m['logical_calls'],
            **{k:m[k] for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens')},unknown_usage_calls=0,unknown_token_upper_bound=0))
    csvfile('token_cost_breakdown.csv',costs)
    # Keep the primary protocol results immutable in their original files;
    # augment the required combined task/decision tables with scope labels.
    discovery=jl(OUT/'task_results.jsonl')
    if discovery and 'scope' not in discovery[0]:
        lines('discovery_task_results.jsonl',discovery)
        lines('task_results.jsonl',[dict(scope='historical_counterfactual',**r) for r in discovery]+[dict(scope='independent_online',**r) for r in jl(OUT/'independent_results.jsonl')])
    existing=jl(OUT/'controller_decisions.jsonl')
    if not any(r.get('online_execution') for r in existing):
        for r in jl(OUT/'independent_results.jsonl'):
            existing.append(dict(task_id=r['task_id'],method=r['method'],branch=r['decision_branch'],triggered=r['early_completion_triggered'],
                online_execution=True,gold_used=False,observed_state=r['observed_state'],controller_cpu_ms=r['controller_cpu_ms'],
                first_stage_generated_tokens=r['first_stage_generated_tokens'],scope='independent actual staged execution'))
        lines('controller_decisions.jsonl',existing)
    b4=next(m for m in pilot if m['method']=='B4_counterfactual')
    b1=next(m for m in pilot if m['method']=='B1_fixed')
    decision='NO-GO' if b4['total_tokens_saved_vs_B0']<=0 or b4['total_tokens']>=b1['total_tokens'] or b4['negative_transfers'] else 'PARTIAL'
    save('summary.json',dict(at=now(),decision=decision,trace=read(OUT/'evidence/trace_summary.json'),
        counterfactual=read(OUT/'evidence/counterfactual_summary.json'),supplemental_negative_control=negative,
        independent=pilot,physical_calls=len(calls),known_tokens=known,unknown_token_upper_bound=unknown,
        total_tokens_upper_bound=known+unknown,known_input_tokens=sum(r['input_tokens'] or 0 for r in calls if r['usage_known']),
        known_output_tokens=sum(r['output_tokens'] or 0 for r in calls if r['usage_known']),
        known_reasoning_tokens=sum(r['reasoning_tokens'] or 0 for r in calls if r['usage_known']),
        peak_uncached_known_cost_estimate_usd=sum((r['input_tokens'] or 0)*.3e-6+(r['output_tokens'] or 0)*1.2e-6 for r in calls if r['usage_known']),
        model_versions=dict(Counter((r['response'] or {}).get('model') for r in calls)),
        backend_fingerprints=dict(Counter((r['response'] or {}).get('system_fingerprint') for r in calls)),
        no_more_api_calls=True))
    print(json.dumps(read(OUT/'summary.json'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
