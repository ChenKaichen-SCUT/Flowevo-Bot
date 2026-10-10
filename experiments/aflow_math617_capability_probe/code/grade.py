"""Frozen V3, offline scoring after stage seal and public selection seal."""
from common import *
import argparse,collections

def main():
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['validation1','validation4','validation8','test1']);stage=ap.parse_args().stage
 seal=read(OUT/'checkpoints'/f'{stage}_SEALED.json')
 for p,h in seal['files'].items():assert sha(OUT/p)==h
 if stage in ('validation4','validation8'):
  choice=read(OUT/'checkpoints'/f'selection_k{stage[-1]}_SEALED.json');assert sha(OUT/choice['path'])==choice['sha256']
 if stage=='test1':assert (OUT/'checkpoints/METHOD_FROZEN_FOR_TEST.json').exists()
 target=OUT/'grading'/f'{stage}.jsonl'
 if target.exists():print('Frozen completed grading reused');return
 from math_evaluation.engine import MathEvaluatorV3
 from math_evaluation.models import EvaluatorConfig
 freeze=read(ROOT/'experiments/math_evaluator_v3_offline/evidence/evaluator_freeze.json')
 for p,h in freeze['source_files'].items():assert sha(ROOT/p)==h
 cfg=EvaluatorConfig(**freeze['config']);assert cfg.hash()==freeze['config_hash']
 public={t['task_id']:t for t in jl(OUT/'data/public_tasks.jsonl')};labels={r['task_id']:r['reference_raw']for r in jl(OUT/'data/offline_labels.jsonl')}
 oldscores={r['source_job_id']:r for r in jl(ROOT/'experiments/failure_mechanism_a1_a2_pilot/pilot_v3_results.jsonl')};records=[];scores=[]
 for path in seal['files']:
  r=read(OUT/path);t=public[r['task_id']]
  if r['reused']:
   old=oldscores[r['source_job_id']];assert old['response_hash']==r['response_hash']
   scores.append(dict(old,record_id=r['job_id'],source_job_id=r['job_id'],reused_grading=True,source_grade_job_id=r['source_job_id']))
  else:records.append({'record_id':r['job_id'],'task_id':r['task_id'],'branch':'candidate_'+str(r['candidate']),'subject':t['subject'],'level':t['level'],'question':t['problem'],'prediction_raw':r['response']['choices'][0]['message'].get('content')or '','reference_raw':labels[r['task_id']],'finish_reason':r['finish_reason'],'source_job_id':r['job_id'],'source_path':path,'request_hash':r['request_hash'],'response_hash':r['response_hash'],'submission_sealed':True})
 save(f'evidence/{stage}_grading_barrier.json',{'at':now(),'seal_sha256':sha(OUT/'checkpoints'/f'{stage}_SEALED.json'),'new_records':len(records),'reused_grades':len(scores),'frozen_evaluator_config_hash':cfg.hash(),'generation_complete':True})
 scores+=MathEvaluatorV3(cfg).evaluate_batch(records)
 lines(target,sorted(scores,key=lambda r:r['source_job_id']));lines(f'grading/{stage}_noncorrect.jsonl',[r for r in scores if r['status']!='correct'])
 print(json.dumps({'stage':stage,'n':len(scores),'statuses':dict(collections.Counter(r['status']for r in scores))},ensure_ascii=False))
if __name__=='__main__':main()
