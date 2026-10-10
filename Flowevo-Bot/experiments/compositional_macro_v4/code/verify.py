"""Recompute integrity, source induction, mathematical proofs, and all submissions.

Read-only by default except verification evidence in this experiment. Does not
rerun APIs or inspect unsealed gold. Historical files and runtime remain frozen.
"""
import sys,collections,csv,xml.etree.ElementTree as ET,time
from common import *
sys.path.insert(0,str(ROOT/'src'))
from evaluate import verify_freeze
from flowevo_bot.v2.evaluator import assert_sealed,grade
from flowevo_bot.compositional_v4.runtime import solve
from flowevo_bot.compositional_v4.mining import extract_trace
from flowevo_bot.compositional_v4.synthesis import synthesize
from flowevo_bot.compositional_v4.verify import universal_certificate
from flowevo_bot.compositional_v4.dsl import MANUAL_PROGRAM

def main():
    cap_cpu();start=time.perf_counter();freeze=verify_freeze()
    protected=read(OUT/'snapshots/protected_history.json')
    bad=[p['path'] for p in protected if sha(ROOT.parent/p['path'])!=p['sha256']]
    assert not bad,('historical_file_changed',bad)
    allsealed=[];allscored=[];selected=[];counts={}
    for split in ('dev-engineering','dev-selection','heldout-confirmation'):
        sealed=lines(OUT/f'evidence/{split}.sealed.jsonl');scored=lines(OUT/f'evidence/{split}.scored.jsonl')
        barrier=read(OUT/f'evidence/{split}.barrier.json')
        assert sha(OUT/f'evidence/{split}.sealed.jsonl')==barrier['sha256']
        assert barrier['all_sealed_before_labels'] and len(sealed)==barrier['count']
        assert len(sealed)==len(scored)
        for raw,after in zip(sealed,scored):
            assert_sealed(raw)
            assert {k:after[k] for k in raw}==raw,'scoring_mutated_submission'
            assert raw['gold_exposed'] is False and not raw['LLM_fallback_executed']
            assert raw['api_call_count']==0 and raw['total_tokens'] is None
            if not raw['result']['full_execution']:assert after['offline_correct'] is None
            else:selected.append(after)
        ids=[(r['task_id'],r['method']) for r in sealed];assert len(ids)==len(set(ids))
        counts[split]=len(sealed)//2;allsealed+=sealed;allscored+=scored
    assert len(allsealed)==9592
    assert lines(OUT/'offline_task_results.jsonl')==allscored
    sources=lines(RMMD/'data/clean_success_traces.jsonl');examples=[]
    for row in sources:
        _,ex=extract_trace(row);examples.append(ex)
    discovery=synthesize(examples);bank=read(OUT/'automatic_macro_bank.json')
    assert digest(discovery['bank'])==digest(bank),'bank_not_reproduced_from_training_traces'
    assert digest(discovery['candidates'])==digest(lines(OUT/'macro_candidates.jsonl'))
    assert len(bank)==1 and tuple(bank[0]['program'])==MANUAL_PROGRAM
    for cert in lines(OUT/'verification_certificates.jsonl'):
        proof=universal_certificate(cert['program']);assert proof['passed']
        assert digest(cert)==digest(proof)
    legacy=read(V3/'data/automatic_macro_bank.json')
    labels={r['task_id']:r for r in lines(ROOT/'data/manifests/math_grouped/train.labels.jsonl')+lines(ROOT/'data/manifests/math_grouped/dev.labels.jsonl')}
    replays=[]
    for row in selected:
        result=solve(row['question'],row['method'],bank,legacy)
        assert result['full_execution'] and result['answer']==row['result']['answer']
        score=grade({**row,'gold_answer':labels[row['task_id']]['gold_answer']})
        assert score['rechecked_correct'] is True and row['offline_correct'] is True
        replays.append({'task_id':row['task_id'],'method':row['method'],'answer':result['answer'],'correct':True,'module':result['module']})
    split=read(OUT/'dataset_split_manifest.json');sets={k:set(v['ids']) for k,v in split['splits'].items()}
    keys=list(sets)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:assert not sets[a]&sets[b]
    for name in keys:
        if name!='train-build':assert not sets[name]&set(split['historically_exposed_ids'])
    for edge in lines(OUT/'evidence/near_duplicate_edges.jsonl'):
        left={n for n,s in sets.items() if edge['a'] in s};right={n for n,s in sets.items() if edge['b'] in s}
        assert not left or not right or left==right
    assert all(t.startswith('math_train_') for s in sets.values() for t in s)
    gate=read(OUT/'paid_gate.json');assert gate['status']=='NOT RUN' and not all(gate['checks'].values())
    assert (OUT/'api_calls.jsonl').read_text()==''
    assert gate['new_api_calls']==gate['new_total_tokens']==0 and gate['LLM_token_savings'] is None
    root=ET.parse(OUT/'evidence/all_tests.xml').getroot()
    n=sum(int(s.get('tests',0)) for s in root.iter('testsuite'));assert n==193
    assert all(int(s.get('failures',0))==int(s.get('errors',0))==0 for s in root.iter('testsuite'))
    with (OUT/'extraction_funnel.csv').open() as f:funnel=list(csv.DictReader(f))
    assert [int(r['accepted']) for r in funnel]==[603,9,9,9,9,6,6,4,4,2]
    assert len(lines(OUT/'extraction_failures.jsonl'))==603
    summary={'at':now(),'status':'PASS','protected_historical_files':len(protected),'frozen_files':len(freeze['files']),
        'freeze_hash':freeze['freeze_hash'],'sealed_records':len(allsealed),'fresh_task_counts':counts,
        'programs_reproved':len(discovery['candidates']),'source_bank_reproduced':True,'complete_submission_replays':replays,
        'duplicate_checks':'all persisted near-duplicate edges and split intersections','tests':n,
        'new_API_calls':0,'pilot_status':'NOT RUN','wall_seconds':time.perf_counter()-start}
    write(OUT/'evidence/final_verification.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
