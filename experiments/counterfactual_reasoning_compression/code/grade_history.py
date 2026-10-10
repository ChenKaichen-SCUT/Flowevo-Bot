"""Grade the low-budget history once with exactly the already-frozen V3."""
from common import *
from collections import Counter
def main():
 target=OUT/'evidence/low2048_v3.jsonl'
 if target.exists():print('Completed historical grading reused');return
 public={r['task_id']:r for r in jl(HIGH/'data/public_tasks.jsonl')}
 labels={r['task_id']:r['reference_raw'] for r in jl(HIGH/'data/offline_labels.jsonl')}
 records=[]
 for row in jl(LOW/'results.jsonl'):
  tid=row['task_id'];raw=read(LOW/row['response_path']);assert raw['response_hash']==digest(raw['response'])
  p=public[tid]
  records.append(dict(record_id=tid+'__low2048',task_id=tid,branch='historical_low2048',subject=p['subject'],level=p['level'],question=p['problem'],prediction_raw=raw['response']['choices'][0]['message'].get('content') or '',reference_raw=labels[tid],finish_reason=raw['finish_reason'],source_job_id=tid+'__low2048',source_path=str((LOW/row['response_path']).relative_to(ROOT)),request_hash=raw['request_hash'],response_hash=raw['response_hash'],submission_sealed=True))
 assert len(records)==605
 results=frozen_evaluator().evaluate_batch(records)
 lines(target,results);print(json.dumps(dict(Counter(r['status'] for r in results))))
if __name__=='__main__':main()
