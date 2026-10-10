"""Correct one audited boundary defect, without retuning rules or changing old data."""
from common import *
from states import candidate_events,observe,safe_boundary
from dataclasses import asdict
from transport import Ledger
from intervene import request_for

def main():
    tid='math_test_number_theory_536'
    original=next(s for s in jl(OUT/'counterfactual_states.jsonl') if s['task_id']==tid and s['position_kind']=='after_first_candidate')
    raw=read(ROOT/original['historical_raw_path']);text=raw['response']['choices'][0]['message']['reasoning_content']
    first=candidate_events(original['problem'],text)[0];cut=first['end']
    if text[cut:cut+1]=='.':cut+=1
    prefix=text[:cut]
    assert safe_boundary(text,cut) and 'So answer 14.' in prefix and 'I mistakenly' not in prefix
    state=dict(original,state_id=tid+'__early_wrong_candidate',position_kind='audited_sentence_boundary',
        cut_char=cut,observed_fraction=cut/len(text),prefix=prefix,prefix_sha256=digest(prefix),
        prefix_generation_tokens_estimate=raw['reasoning_tokens']*cut/len(text),
        reasoning_state=asdict(observe(tid,original['problem'],prefix)))
    save('evidence/negative_control_state.json',state)
    cfg=read(OUT/'config.json');requests={b:request_for(state,b,cfg) for b in 'ABC'}
    amendment=OUT/'evidence/negative_control_amendment.json'
    if not amendment.exists():
        save(amendment,dict(at=now(),reason='Manual audit found the paragraph selected after first candidate already contained the later correction14->15; repair this boundary using the complete sentence ending in14, before that correction.',
            original_state_preserved=original['state_id'],original_cut=original['cut_char'],corrected_cut=cut,
            additional_calls=3,rule_retuned=False,training_or_gate_rerun=False,independent_sample_changed=False,
            corrected_state_sha256=sha(OUT/'evidence/negative_control_state.json'),
            request_hashes={b:digest(r) for b,(r,_) in requests.items()},script_sha256=sha(Path(__file__))))
    ledger=Ledger();results=[]
    for b,(request,endpoint) in requests.items():
        results.append(ledger.call(state['state_id']+'__'+b,request,dict(stage='negative_control_repair',task_id=tid,state_id=state['state_id'],branch=b,mode=cfg['mode']),endpoint))
    assert all(r['status']=='completed' for r in results)
    save('evidence/NEGATIVE_CONTROL_SEALED.json',dict(at=now(),files={'raw/'+r['job_id']+'.json':sha(OUT/'raw'/(r['job_id']+'.json')) for r in results}))
if __name__=='__main__':main()
