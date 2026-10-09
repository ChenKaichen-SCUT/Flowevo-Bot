"""Read-only independent artifact checks; writes only its verification result."""
import sys,json,hashlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/macro_discovery_pilot';WORK=ROOT.parent
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(OUT/'code'))
from common import read,write,lines,sha
from flowevo_bot.v2.evaluator import assert_sealed
from flowevo_bot.common import digest
from flowevo_bot.schemas import ProblemView
from code_math.baseline import base_prompt
from flowevo_bot.rmmd.macros import COMPACT,inspect_question
from flowevo_bot.rmmd.client import SYSTEM

def main():
    frozen=read(OUT/'evidence/prepaid_freeze.json');changed=[p for p,h in frozen['files'].items() if sha(ROOT/p)!=h];assert not changed,changed
    assert sha(OUT/'tests/prepaid.xml')==frozen['prepaid_test_report_sha256']
    protected=read(OUT/'snapshots/protected_files.json')
    if isinstance(protected,dict):protected=protected['files']
    modified=[r['path'] for r in protected if not (WORK/r['path']).exists() or sha(WORK/r['path'])!=r['sha256']];assert not modified,modified
    rows=lines(OUT/'data/task_results.jsonl');tasks=read(OUT/'data/dev_tasks.json');byid={t['problem']['task_id']:t for t in tasks}
    api={r['call_id']:r for r in (read(p) for p in (OUT/'api_calls').glob('*.json'))}
    assert len(api)==38 and len(rows)==42 and len(byid)==14
    assert not list((OUT/'api_calls').glob('*.pending.json')) and not list((OUT/'api_calls').glob('*.error.json'))
    seen=set()
    for row in rows:
        tid=row['task_id'];method=row['method'];key=method+'__'+tid;assert key not in seen;seen.add(key)
        original=read(OUT/'submissions'/(key+'.json'));assert_sealed(original)
        for k,v in original.items():assert row[k]==v
        assert not row['gold_exposed'] and row['code_hash']==frozen['code_hash']
        assert row['total_tokens']==row['input_tokens']+row['output_tokens']
        task=byid[tid];p=ProblemView.model_validate(task['problem']);mid=task['macro_id'];execution=inspect_question(p.problem,mid)
        if row['api_call_count']==0:
            assert method=='C_Executable' and mid=='polynomial_remainder' and execution['full_task_verified']
            assert row['solution']=='The answer is \\boxed{'+execution['direct_answer']+'}.' and row['total_tokens']==0
        else:
            call=api[row['call_id']];assert not call['simulated'];request=call['request'];response=call['response'];choice=response['choices'][0]
            prompt=base_prompt(p)
            if method=='B_Compact':prompt+='\n\nReusable mathematical method:\n'+COMPACT[mid]
            if method=='C_Executable':prompt+='\n\nVerified mathematical intermediate:\n'+execution['verified_context']
            assert request=={'model':'deepseek-flash','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],'temperature':0.0,'max_tokens':4096}
            assert row['solution']==(choice['message'].get('content') or '') and row['truncated']==(choice.get('finish_reason')=='length')
            assert row['prompt_hash']==digest(request)==call['prompt_hash'] and digest(response)==call['response_hash']
            assert call['http_attempts']==1 and call['correctness_retries']==0
            for k in ['input_tokens','output_tokens','total_tokens']:assert row[k]==call[k]
            assert call['total_tokens']<=call['reserved_tokens']
    assert sum(r['total_tokens'] for r in rows)==sum(c['total_tokens'] for c in api.values())==34896
    assert sum(r['api_call_count'] for r in rows)==38
    sourceids={r['task_id'] for r in lines(OUT/'data/clean_success_traces.jsonl')};assert not sourceids&set(byid)
    forbidden={r['task_id'] for r in lines(ROOT/'experiments/math500_goldfree_20261009/manifests/test.problems.jsonl')};assert not forbidden&set(byid)
    barrier=read(OUT/'evidence/submission_barrier.json');assert barrier['count']==42 and barrier['all_sealed']
    for r in rows:assert barrier['seal_hashes'][r['method']+'__'+r['task_id']]==r['seal']
    wheel=ROOT/'dist/flowevo_bot-0.3.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel) as z:
        for p in (ROOT/'src/flowevo_bot/rmmd').glob('*.py'):assert z.read('flowevo_bot/rmmd/'+p.name)==p.read_bytes()
    result={'passed':True,'frozen_files_unchanged':len(frozen['files']),'old_files_unchanged':len(protected),'raw_api_calls':len(api),'sealed_submissions':len(rows),'actual_total_tokens':34896,'prompt_reconstruction_all_matched':True,'response_and_usage_all_matched':True,'no_source_or_test_task_overlap':True,'all_global_budget_limits_satisfied':True,'wheel_source_bytes_match':True,'new_api_calls_by_verifier':0}
    write(OUT/'evidence/final_integrity_verification.json',result);print(json.dumps(result))
if __name__=='__main__':main()
