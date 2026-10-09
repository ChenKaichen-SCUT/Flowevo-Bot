"""Post-run read-only audit of frozen code, histories, bank and offline records."""
import sys,json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/goal_aware_macro_v3';WORK=ROOT.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(OUT/'code'))
from common import read,write,lines,sha
from artifact_schema import MacroSkill
from flowevo_bot.v2.evaluator import assert_sealed
from flowevo_bot.goal_v3.engine import solve
from flowevo_bot.goal_v3.learning import certificate

def main():
    freeze=read(OUT/'evidence/pre_reserved_freeze.json');assert all(sha(ROOT/p)==h for p,h in freeze['files'].items()),'frozen runtime changed'
    history=read(OUT/'snapshots/protected_files.json');modified=[r['path'] for r in history if not (WORK/r['path']).exists() or sha(WORK/r['path'])!=r['sha256']];assert not modified,modified
    suites=list(ET.parse(OUT/'tests/offline.xml').getroot().iter('testsuite'));assert sum(int(r.get('tests')) for r in suites)==132;assert all(int(r.get('failures'))==0 and int(r.get('errors'))==0 for r in suites)
    split=read(OUT/'data/split_manifest.json');eng=read(OUT/'data/engineering_dev_tasks.json');fresh=read(OUT/'data/reserved_dev_tasks.json')
    assert len(eng)==434 and len(fresh)==1115
    engids={r['task_id'] for r in eng};freshids={r['task_id'] for r in fresh};assert not engids&freshids
    assert engids|freshids=={r['task_id'] for r in lines(ROOT/'data/manifests/math_grouped/dev.problems.jsonl')}
    sourceids={r['task_id'] for r in lines(ROOT/'experiments/macro_discovery_pilot/data/clean_success_traces.jsonl')};assert not (engids|freshids)&sourceids
    testids={r['task_id'] for r in lines(ROOT/'data/manifests/math_grouped/test.problems.jsonl')};assert not (engids|freshids)&testids
    screened={r['task_id'] for r in lines(ROOT/'experiments/macro_discovery_pilot/data/coverage_screen.jsonl')};assert not freshids&screened
    bank=read(OUT/'data/automatic_macro_bank.json')
    assert len(bank)==2
    for entry in bank:
        MacroSkill.model_validate(entry);proof=certificate(entry['program'],entry['goal_kind']);assert proof==entry['certificate'];assert set(entry['source_task_ids'])<=sourceids
    candidates=lines(OUT/'data/macro_candidates.jsonl');assert len(candidates)==14
    for c in candidates:assert certificate(c['program'],c['goal_kind'])==c['universal_certificate']
    sealed_count=0
    for name in ['engineering_manual','engineering_automatic','reserved_manual_automatic']:
        records=lines(OUT/'data'/(name+'_sealed.jsonl'));barrier=read(OUT/'evidence'/(name+'_submission_barrier.json'))
        assert barrier['all_sealed'] and barrier['before_label_read'] and barrier['count']==len(records)
        assert sha(OUT/'data'/(name+'_sealed.jsonl'))==barrier['submission_file_hash']
        for record in records:assert_sealed(record)
        sealed_count+=len(records)
    rows=lines(OUT/'data/task_results.jsonl');assert len(rows)==1549*3
    groups={m:[r for r in rows if r['method']==m] for m in ['A_NoBank','B_Manual','C_Automatic']}
    assert all(len(g)==1549 for g in groups.values());assert all(r['status']=='NOT_RUN' and r['offline_correct'] is None and r['total_tokens'] is None for r in groups['A_NoBank'])
    counts={m:sum(r['full_task_verified'] for r in g) for m,g in groups.items()};assert counts=={'A_NoBank':0,'B_Manual':20,'C_Automatic':2}
    for r in rows:
        assert r['api_call_count']==0 and r['gold_exposed'] is False
        if r['full_task_verified']:
            rerun=solve(r['question'],'manual' if r['method']=='B_Manual' else 'automatic',bank)
            assert rerun['full_task_verified'] and rerun['answer']==r['answer']
            assert r['offline_correct'] is True and r['verification_certificate']['full_task_verified']
        else:assert r['offline_correct'] is None
    b={r['task_id'] for r in groups['B_Manual'] if r['full_task_verified']};c={r['task_id'] for r in groups['C_Automatic'] if r['full_task_verified']};assert c<=b
    gate=read(OUT/'data/paid_gate.json');assert not gate['eligible'] and not gate['correctness_labels_used_for_gate'] and gate['independent_eligible_after_dedup']==1
    assert read(OUT/'data/pilot_tasks.json')==[] and (OUT/'data/api_calls.jsonl').read_text()==''
    assert not (OUT/'api_calls').exists() or not list((OUT/'api_calls').glob('*'))
    status=read(OUT/'evidence/paid_status.json');assert status['new_api_calls']==status['new_total_tokens']==0
    barrier=read(OUT/'evidence/reserved_label_barrier.json');assert barrier['paid_gate_closed_or_all_paid_submissions_sealed'] and barrier['code_unchanged']
    with zipfile.ZipFile(ROOT/'dist/flowevo_bot-0.4.0-py3-none-any.whl') as z:
        for p in (ROOT/'src/flowevo_bot/goal_v3').glob('*.py'):assert z.read('flowevo_bot/goal_v3/'+p.name)==p.read_bytes()
    result={'passed':True,'frozen_files_unchanged':len(freeze['files']),'historical_files_unchanged':len(history),'sealed_offline_records':sealed_count,'flat_task_records':len(rows),'bank_programs_and_14_candidate_proofs_recomputed':True,'all22_direct_submissions_replayed':True,'manual_full':20,'automatic_full':2,'automatic_extra_coverage_over_manual':0,'fresh_development_full_each':1,'no_source_or_test_overlap':True,'paid_gate_failed_and_no_calls':True,'new_api_calls':0,'new_total_tokens':0,'wheel_source_bytes_match':True,'test_count':132}
    write(OUT/'evidence/final_integrity_verification.json',result);print(json.dumps(result))
if __name__=='__main__':main()
