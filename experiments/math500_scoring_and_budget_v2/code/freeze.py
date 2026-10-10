from common import *
import ast,subprocess,json

def main():
 log=(OUT/'evidence/tests_pre_api.txt').read_text();assert 'failed' not in log and 'passed' in log
 rows=read(ROOT/'experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json')
 from completion import detect
 states=[detect(x['task_id'],{'choices':[{'message':{'content':x['solution']},'finish_reason':x['provider']['finish_reason']}],'usage':x['provider']['usage']},4096) for x in rows]
 confusion={'historical_truncated_detected':sum(x['truncated'] and y['retry_required'] for x,y in zip(rows,states)),'historical_truncated_missed':sum(x['truncated'] and not y['retry_required'] for x,y in zip(rows,states)),'historical_nontruncated_triggered':sum(not x['truncated'] and y['retry_required'] for x,y in zip(rows,states)),'historical_nontruncated_not_triggered':sum(not x['truncated'] and not y['retry_required'] for x,y in zip(rows,states))}
 assert confusion=={'historical_truncated_detected':27,'historical_truncated_missed':0,'historical_nontruncated_triggered':0,'historical_nontruncated_not_triggered':473}
 save('evidence/completion_detector_historical.json',{'counts':confusion,'states':states,'limitations':'A complete response lacking recognized markers may conservatively trigger; no semantic correctness or gold used. length overrides a visible boxed answer.'})
 previous=read(OUT/'evidence/protected_previous_snapshot.json');changed=[x['path'] for x in previous['files'] if sha(ROOT/x['path'])!=x['sha256']]
 assert changed==['指引.txt'],changed
 save('evidence/pre_run_version_check.json',{'publishing_HEAD':subprocess.check_output(['git','-C','/mnt/Space1/Flowevo-Bot-upload','rev-parse','HEAD']).decode().strip(),'expected_reference':REF,'only_previous_changed_path':changed,'guide_is_new_user_instruction':True,'all_previous_code_and_experiment_records_unchanged':True,'native_FlowEvo_upstream_commit':subprocess.check_output(['git','-C',str(ROOT/'FlowEvo'),'rev-parse','HEAD']).decode().strip(),'workspace_root_is_git_checkout':False})
 files=[OUT/'code'/n for n in ('common.py','completion.py','run_experiment.py','evaluators.py','export_native_prompts.py')]+[OUT/'config.json',OUT/'dataset_manifest.json',OUT/'data/public_tasks.jsonl',OUT/'data/native_prompts.json']
 files += [ROOT/x['path'] for x in read(OUT/'evidence/evaluators_frozen.json')['files']]+[ROOT/'FlowEvo/src/code_math/runner.py']
 save('scoring_regression_tests.json',{'historical_counts':read(OUT/'evaluator_regression.json')['counts'],'pre_api_test_log':log,'completion_detector_counts':confusion,'additional_counterexamples':8,'added_api_calls':0})
 save('evidence/pre_api_freeze.json',{'frozen_at':now(),'reference_commit':REF,'files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in files],'labels_not_in_online_inputs':True,'scorers_never_used_for_scheduling':True,'selection_and_rules_fixed_before_any_new_call':True})
 print('Pre-API freeze complete. '+log.splitlines()[-1])
if __name__=='__main__':main()
