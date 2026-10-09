"""Offline integrity acceptance for the completed, immutable V2 study."""
import hashlib
import json
from pathlib import Path
import zipfile
from flowevo_bot.common import digest,read_json,write_json,jsonl
from flowevo_bot.schemas import ProblemView,Trace
from flowevo_bot.provenance import assert_independent,assert_clean_traces
from flowevo_bot.v2.evaluator import assert_sealed
from flowevo_bot.v2.skills import MacroSkill,evaluate
from run_v2_research import ROOT,OLD,OUT,solver_prompt

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    checked=[]
    def check(condition,name):
        if not condition:raise AssertionError(name)
        checked.append(name)
    history=read_json(OUT/'snapshots/historical_files.json')
    altered=[r['path'] for r in history if not (ROOT/r['path']).exists() or sha(ROOT/r['path'])!=r['sha256']]
    check(not altered,'all_historical_files_unchanged')
    frozen=read_json(OUT/'evidence/solver_frozen_before_dev.json');protocol=read_json(OUT/'protocol.json')
    check(all(sha(ROOT/p)==h for p,h in frozen['code_hashes'].items()),'executed_v2_modules_unchanged')
    with zipfile.ZipFile(OUT/'snapshots/runtime_used_for_dev.zip') as z:
        check(hashlib.sha256(z.read('scripts/run_v2_research.py')).hexdigest()==protocol['runner_sha256'],'executed_runner_archived')
    check(frozen['config_hash']==digest(protocol),'frozen_configuration_matches')
    entries=read_json(OUT/'data/dev_tasks.json');tasks={e['problem']['task_id']:e for e in entries}
    original=read_json(OLD/'real_bank.json');oldskills={s['skill_id']:s for s in original['skills']}
    newskills=[MacroSkill.model_validate(s) for s in read_json(OUT/'data/skills_v2_full.json')]
    family_skills={s.skill_id.split('_')[0]:s for s in newskills}
    check(len(tasks)==20 and all(t.startswith('math_train_') for t in tasks),'twenty_training_split_validation_tasks')
    assert_independent([ProblemView.model_validate(t['problem']) for t in original['history']], [ProblemView.model_validate(e['problem']) for e in entries])
    checked.append('development_independent_of_all_627_history_traces')
    public=[ProblemView.model_validate(e['problem']) for e in entries]
    for i,p in enumerate(public):assert_independent(public[:i],[p])
    checked.append('development_pairwise_near_duplicate_check')
    cache=read_json(OUT/'evidence/feature_cache.json');clusters=read_json(OUT/'data/clusters.json')
    for s in newskills:
        sources=clusters[s.skill_id.split('_')[0]]['source_traces']
        assert_clean_traces([Trace.model_validate(t) for t in sources],3)
        check(s.source_trace_hashes==[Trace.model_validate(t).trace_hash for t in sources],s.skill_id+'_source_hashes')
        check(all(evaluate(s.trigger,cache[t]['facts'])['value'] is True for t in s.source_task_ids),s.skill_id+'_source_self_match')
    records=[read_json(p) for p in sorted((OUT/'submissions').glob('*.json'))]
    results=jsonl(OUT/'task_results.jsonl');calls={}
    for p in (OUT/'calls').glob('*.json'):
        r=read_json(p)
        if 'response' in r:calls[r['call_id']]=r
    check(len(records)==len(results)==60,'all_sixty_submissions_present')
    check(len({(r['task_id'],r['method']) for r in records})==60,'unique_task_method_pairs')
    for r in records:
        assert_sealed(r);e=tasks[r['task_id']];task=ProblemView.model_validate(e['problem']);s=family_skills[e['family']]
        text=None if r['method']=='A_NoBank' else oldskills[s.predecessor]['compact_prompt'] if r['method']=='B_OriginalContent' else s.compact_prompt
        call=calls[r['call_id']];request=call['request']
        check(request['messages'][1]['content']==solver_prompt(task,text),r['method']+'/'+r['task_id']+'_public_prompt')
        check(request['model']=='deepseek-flash' and request['max_tokens']==4096 and request['temperature']==0.,r['method']+'/'+r['task_id']+'_settings')
        check(not r['gold_exposed'] and r['math_retries']==0,r['method']+'/'+r['task_id']+'_gold_free')
        check(r['total_tokens']==call['total_tokens']==r['input_tokens']+r['output_tokens'],r['method']+'/'+r['task_id']+'_usage')
        check(r['solution']==call['response']['choices'][0]['message'].get('content',''),r['method']+'/'+r['task_id']+'_response_bound')
    check(len(calls)==63 and sum(c['total_tokens'] for c in calls.values())==102316,'actual_sixty_three_calls_and_usage_reconciled')
    check(all(not c['simulated'] and not c['estimated_usage'] for c in calls.values()),'all_calls_real_with_provider_usage')
    check(all(len(c['attempts'])==1 for c in calls.values()),'no_infrastructure_or_math_retries')
    check(not list((OUT/'calls').glob('*.pending.json')),'no_unresolved_request_journals')
    for r in results:
        if r['truncated']:check(r['correct'] is False,'truncated_not_accepted_'+r['method']+'/'+r['task_id'])
    sealed=read_json(OUT/'evidence/all_dev_submissions_sealed.json')
    check(sealed['seals']==sorted(r['seal'] for r in records) and not sealed['labels_opened'],'complete_seal_barrier_before_label_access')
    bank=read_json(OUT/'skill_bank_v2.json')
    check(bank['bank_hash']==digest({k:v for k,v in bank.items() if k!='bank_hash'}),'frozen_bank_hash')
    check(all(MacroSkill.model_validate(s).status=='shadow' for s in bank['skills']),'no_fabricated_active_skill')
    gate=read_json(OUT/'evidence/formal_gate.json')
    check(not gate['passed'] and not gate['formal_500_executed'],'formal_test_stopped_by_predeclared_gate')
    dm=read_json(OUT/'dataset_manifest.json')
    check(sha(ROOT/dm['test_reference']['path'])==dm['test_reference']['sha256'],'original_500_manifest_unchanged')
    secret=(ROOT.parent/'miyao.txt').read_bytes().strip()
    for p in OUT.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            check(not secret or secret not in p.read_bytes(),'no_runtime_credential:'+str(p.relative_to(OUT)))
    report={'passed':True,'checks':len(checked),'names':checked,'historical_files_preserved':len(history),
        'api_calls':len(calls),'total_tokens':sum(c['total_tokens'] for c in calls.values()),'gold_free':True,
        'formal_500_executed':False,'limitations':'Prompt/lineage/seal integrity does not prove semantic source independence or every mathematical guard.'}
    write_json(OUT/'evidence/INTEGRITY.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='names'}),flush=True)

if __name__=='__main__':main()
