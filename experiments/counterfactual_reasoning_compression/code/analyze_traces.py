from common import *
from states import *
from collections import Counter
import statistics,math

def quantile(values,q):
    values=sorted(values);index=(len(values)-1)*q;left=int(index);right=math.ceil(index)
    return values[left]*(right-index)+values[right]*(index-left) if left!=right else values[left]

def main():
    public={r['task_id']:r for r in jl(HIGH/'data/public_tasks.jsonl')}
    high={r['task_id']:r for r in jl(HIGH/'baseline_results.jsonl')}
    low={r['task_id']:r for r in jl(LOW/'results.jsonl')}
    low_scores={r['task_id']:r for r in jl(OUT/'evidence/low2048_v3.jsonl')}
    assert set(public)==set(high)==set(low)==set(low_scores) and len(public)==605
    align=[];events=[];inventory=[]
    for tid,p in public.items():
        h,l=high[tid],low[tid];hr=read(HIGH/h['response_path']);lr=read(LOW/l['response_path'])
        assert hr['response_hash']==digest(hr['response']) and lr['response_hash']==digest(lr['response'])
        text=hr['response']['choices'][0]['message'].get('reasoning_content')
        lt=lr['response']['choices'][0]['message'].get('reasoning_content')
        observable=isinstance(text,str) and bool(text)
        candidates=candidate_events(p['problem'],text or '')
        st=observe(tid,p['problem'],text or '')
        first=candidates[0] if candidates else None
        after=(len(text)-first['end']) if first and observable else None
        after_est=h['reasoning_tokens']*after/len(text) if first and observable else None
        clear=bool(h['mathematical_correct'] is True and first and after>=350 and after_est>=128)
        item=dict(task_id=tid,split=p['split'],subject=p['subject'],high_math_confirmed=h['mathematical_correct'],
            high_v3=h['v3_status'],low_v3=low_scores[tid]['status'],low_native_passed=l['passed'],
            independent_generations=True,high_reasoning_observable=observable,low_reasoning_observable=bool(lt),
            first_explicit_candidate_char=first['start'] if first else None,candidate_followed_by_substantial_reasoning=clear,
            continuation_chars_after_candidate=after,continuation_tokens_estimate=after_est,
            continuation_token_method='character-position fraction of exact full reasoning usage; NOT billed prefix tokens',
            high_finish=h['finish_reason'],low_finish=l['finish_reason'],high_truncated=h['is_truncated'],low_truncated=l['finish_reason']=='length',
            **{prefix+'_'+key:r[key] for prefix,r in [('high',h),('low',l)] for key in ('input_tokens','reasoning_tokens','final_content_tokens','total_tokens','output_tokens')})
        align.append(item)
        task_events=[]
        for c in candidates:task_events.append(dict(event='candidate_formation_or_restating',**c,certainty='observable explicit target claim; not a correctness or sufficiency certificate'))
        for e in st.revision_evidence:task_events.append(dict(event='possible_candidate_revision',**e,certainty='linguistic cue only; manual review required'))
        for e in st.check_evidence:task_events.append(dict(event='verification_discussion',**e,certainty='useful vs redundant not mechanically identifiable'))
        for e in st.repetition_evidence:task_events.append(dict(event='observable_repetition',**e,certainty='lexical/claim repetition, not proof of semantic redundancy'))
        task_events.append(dict(event='finalization',channel='content',reasoning_end_char=len(text or ''),finish_reason=h['finish_reason'],content_present=bool(hr['response']['choices'][0]['message'].get('content'))))
        events.append(dict(task_id=tid,observable=observable,response_hash=hr['response_hash'],reasoning_sha256=digest(text),
            high_confirmed_correct=h['mathematical_correct'],explicit_candidates=candidates,events=task_events,
            first_candidate_sufficiency='unproven until counterfactual intervention',final_state=asdict(st)))
        inventory.append(dict(task_id=tid,subject=p['subject'],reasoning_tokens=h['reasoning_tokens'],high_math_confirmed=h['mathematical_correct'],
            high_v3=h['v3_status'],low_v3=low_scores[tid]['status'],**{k:v for k,v in features(st).items() if k!='task_id'},
            first_candidate_fraction=first['end']/len(text) if first and observable else None))
    distributions=[]
    for budget in ('high','low'):
        for status in ('all','correct','incorrect','unknown','prediction_incomplete'):
            selected=[r for r in align if status=='all' or r[budget+'_v3']==status]
            if not selected:continue
            for key in ('input_tokens','reasoning_tokens','final_content_tokens','output_tokens','total_tokens'):
                values=[r[budget+'_'+key] for r in selected if isinstance(r[budget+'_'+key],int)]
                distributions.append(dict(budget=budget,status=status,metric=key,n=len(selected),available=len(values),
                    minimum=min(values),p25=quantile(values,.25),median=quantile(values,.5),p75=quantile(values,.75),p90=quantile(values,.9),maximum=max(values),total=sum(values)))
    csvfile('trace_alignment.csv',align);csvfile('token_length_distribution.csv',distributions)
    lines('reasoning_events.jsonl',events);lines('evidence/trace_inventory.jsonl',inventory)
    paired=Counter((r['high_v3'],r['low_v3']) for r in align)
    summary=dict(n=605,high_confirmed_correct=sum(r['high_math_confirmed'] is True for r in align),
        high_v3=dict(Counter(r['high_v3'] for r in align)),low_v3=dict(Counter(r['low_v3'] for r in align)),
        high_observable=sum(r['high_reasoning_observable'] for r in align),low_observable=sum(r['low_reasoning_observable'] for r in align),
        correct_with_explicit_candidate=sum(r['high_math_confirmed'] is True and r['first_explicit_candidate_char'] is not None for r in align),
        correct_with_candidate_then_substantial_reasoning=sum(r['candidate_followed_by_substantial_reasoning'] for r in align),
        paired_v3=[dict(high=a,low=b,n=n) for (a,b),n in sorted(paired.items())],
        high_tokens=sum(r['high_total_tokens'] for r in align),low_tokens=sum(r['low_total_tokens'] for r in align),
        exact_prefix_billing_tokens_available=False,zero_new_api_calls=True)
    save('evidence/trace_summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
