"""Read-only corpus construction; distinguish calls, tasks and duplicated artifacts."""
from collections import Counter
from pathlib import Path
from common import ROOT,OUT,OLD,V2,read,write,write_lines,lines,sha,cap_cpu
from flowevo_bot.common import digest
from flowevo_bot.schemas import Submission,ProblemView
from code_math.baseline import base_prompt

def main():
    cap_cpu();historical=read(V2/'data/historical_rechecked.json')
    grader=read(V2/'evidence/evaluator_frozen.json')
    assert sha(ROOT/'src/flowevo_bot/v2/evaluator.py')==grader['sha256']
    # Scores are reused only for byte-frozen historical outputs, not recomputed
    # in a solver. The complete original score/recheck distinction is retained.
    new_rows=[]
    problem_lookup={}
    for split in ['train','dev','test']:
        problem_lookup.update({r['task_id']:r for r in lines(OLD/'manifests'/f'{split}.problems.jsonl')})
    index={method:{s['task_id']:s for s in read(OLD/method/'checkpoint.json')['submissions']} for method in ['train','flowevo','flowevo_bot']}
    oldbank=read(OLD/'real_bank.json');source_used={t for s in oldbank['skills'] for t in s['source_task_ids']}
    for c in read(V2/'data/clusters.json').values():source_used.update(t['problem']['task_id'] for t in c['source_traces'])
    history_ids={t['problem']['task_id'] for t in read(OLD/'history.json')}
    for h in historical:
        tid=h['task_id'];method=h['method'];q=problem_lookup[tid]
        if method in index:
            s=index[method][tid];source=OLD/method/'checkpoint.json';ledger_path=OLD/method/'task_calls'/(tid+'.json')
        else:
            group=method.removeprefix('dev_');source=OLD/'validation_v2'/group/(tid+'.submission.json')
            s=read(source);ledger_path=source.with_name(tid+'.calls.json')
        submission=Submission.model_validate(s);submission.assert_frozen()
        assert s['seal']==h['original_seal'] and s['solution']==h['solution']
        ledger=read(ledger_path);calls=[c for c in ledger['calls'] if c['call_id'] in s['call_ids']]
        exact_base=len(calls)==1 and ledger['prompts'][calls[0]['call_id']]==base_prompt(ProblemView.model_validate(q))
        matches_response=len(calls)==1 and ledger['responses'][calls[0]['call_id']]==s['first_solution']
        split='train-build' if method=='train' else 'test' if method in ('flowevo','flowevo_bot') else 'train-dev'
        gold=s['provenance']['gold_exposed'];reasons=[]
        if split!='train-build':reasons.append('test_set_excluded' if split=='test' else 'previous_dev_used_for_selection_excluded')
        if h['rechecked_correct'] is not True:reasons.append('offline_unknown' if h['rechecked_correct'] is None else 'offline_incorrect_or_truncated')
        if gold or s['provenance']['reference_solution_exposed']:reasons.append('gold_or_reference_exposure')
        if s['retry_count'] or len(calls)!=1:reasons.append('not_single_first_pass')
        if any(c['simulated'] for c in calls):reasons.append('simulated')
        if split=='train-build' and not (exact_base and matches_response):reasons.append('unproven_question_only_prompt_or_response')
        row={'task_id':tid,'source_split':split,'subject':q['subject'],'level':q['level'],'problem':q['problem'],
             'public_metadata':q['public_metadata'],'model_solution':s['first_solution'],'final_answer':h['answer'],
             'offline_correct':h['rechecked_correct'],'original_correct':h['original_correct'],'gold_exposed':gold,'truncated':h['truncation_status'],
             'first_pass':s['retry_count']==0 and len(calls)==1,'input_tokens':sum(c['prompt_tokens'] for c in calls),
             'output_tokens':sum(c['completion_tokens'] for c in calls),'total_tokens':sum(c['total_tokens'] for c in calls),
             'source_run_id':OLD.name+'/'+method,'source_hash':digest(s),'source_path':str(source.relative_to(ROOT)),
             'call_ids':s['call_ids'],'calls_path':str(ledger_path.relative_to(ROOT)),'submission_seal':s['seal'],
             'prior_history_pool':tid in history_ids,'previous_skill_source':tid in source_used,'used_in_prior_bank_search':split=='train-build',
             'question_only_first_pass_verified':exact_base and matches_response,'parse_status':h['parse_status'],
             'offline_grade_source':str((V2/'data/historical_rechecked.json').relative_to(ROOT)),'exclusion_reasons':reasons}
        new_rows.append(row)
    for s in lines(V2/'task_results.jsonl'):
        q=next(e['problem'] for e in read(V2/'data/dev_tasks.json') if e['problem']['task_id']==s['task_id'])
        new_rows.append({'task_id':s['task_id'],'source_split':'train-dev','subject':s['subject'],'level':s['level'],
            'problem':q['problem'],'model_solution':s['solution'],'final_answer':s['answer'],'offline_correct':s['correct'],
            'gold_exposed':s['gold_exposed'],'truncated':s['truncated'],'first_pass':True,
            **{k:s[k] for k in ['input_tokens','output_tokens','total_tokens']},'source_run_id':V2.name+'/'+s['method'],
            'source_hash':digest(s),'source_path':str((V2/'task_results.jsonl').relative_to(ROOT)),
            'call_ids':[s['call_id']],'exclusion_reasons':['previous_dev_used_for_selection_excluded']})
    extra=[{'task_id':'gsm8k_0','source_path':'../FlowEvo/runs/deepseek_gsm8k_one_20261009_170111_336099/_checkpoint_gsm8k_ours.json',
            'benchmark':'gsm8k','historical_passed':True,'gold_exposed':None,'exclusion_reasons':['outside_MATH_scope','legacy_v1_no_complete_request_provenance']},
           {'task_id':'game24_2_5_8_11','source_path':'../buffer-of-thought-llm/test_results/deepseek_gameof24_one.jsonl',
            'benchmark':'game24','historical_passed':True,'gold_exposed':None,'exclusion_reasons':['outside_MATH_scope','different_benchmark'] }]
    for r in extra:r.update(source_hash=sha(ROOT/r['source_path']),source_split='smoke_test',offline_correct=None)
    eligible=[r for r in new_rows if not r['exclusion_reasons']]
    assert len({r['task_id'] for r in eligible})==len(eligible)
    excluded=[r for r in new_rows if r['exclusion_reasons']]+extra
    write_lines(OUT/'data/clean_success_traces.jsonl',eligible);write_lines(OUT/'data/excluded_traces.jsonl',excluded)
    all_ids=[r['task_id'] for r in new_rows+extra]
    manifest={'raw_math_solve_trajectories':len(new_rows),'other_real_smoke_trajectories':len(extra),'total_real_trajectories':len(new_rows)+len(extra),
      'math_offline_confirmed_successes_all_splits':sum(r['offline_correct'] is True for r in new_rows),
      'clean_training_first_pass_successes':len(eligible),'excluded_trajectories':len(excluded),'unique_task_ids_all_splits':len(set(all_ids)),
      'repeated_task_trajectories_across_methods':len(all_ids)-len(set(all_ids)),
      'historical_claimed_history_count':len(history_ids),'claimed_pool_reconfirmed':sum(r['prior_history_pool'] for r in eligible),
      'newly_recovered_original_false_negatives':sum(not r['original_correct'] for r in eligible),
      'claimed_pool_unknown_excluded':len(history_ids)-sum(r['prior_history_pool'] for r in eligible),
      'subject_counts':dict(sorted(Counter(r['subject'] for r in eligible).items())),
      'exclusion_reasons_overlapping':dict(Counter(reason for r in excluded for reason in r['exclusion_reasons'])),
      'actual_gold_exposure_found_in_auditable_MATH_records':sum(r['gold_exposed'] is True for r in new_rows),
      'smoke_provenance_unknown':2,'previous_skill_sources_in_clean_corpus':sum(r['previous_skill_source'] for r in eligible),
      'acquisition_cost_tokens_700_training_calls':795435,'selected_success_call_tokens':sum(r['total_tokens'] for r in eligible),
      'duplicate_artifact_policy':'history.json, real_bank.history, trace files, checkpoint copies and per-task call copies reference the same calls, not additional trajectories',
      'scores_reused_after_hash_and_seal_verification':True,'grader_sha256':grader['sha256'],'new_api_calls':0,
      'clean_corpus_sha256':sha(OUT/'data/clean_success_traces.jsonl')}
    write(OUT/'data/trace_manifest.json',manifest);print(manifest,flush=True)

if __name__=='__main__':main()
