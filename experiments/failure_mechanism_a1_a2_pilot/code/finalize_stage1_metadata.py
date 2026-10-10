"""Documented pre-call serialization reconciliation; never redo extraction/grades.

This captures the exact metadata-only operation used before the pilot. Frozen
stage-1 code is preserved. It is unnecessary and refused on a completed run.
"""
from common import *
import collections,csv

def main():
 assert not list((OUT/'raw').glob('*.json')),'Completed/new generation present: reuse sealed atlas, do not rewrite it'
 rows=jl(OUT/'historical_records.jsonl')
 for r in rows:
  if r['task_id']=='math_test_precalculus_187' and r['offline_status']=='unknown' and 'F7' not in r['labels']:r['labels'].append('F7')
  r['labels']=list(dict.fromkeys(r['labels']))
  r['primary']=next((c for c in ['F5','F3','F4','F6','F7','F1','F2','F8'] if c in r['labels']),None);r['secondary']=[c for c in r['labels']if c!=r['primary']]
 lines('historical_records.jsonl',rows);lines('failure_cases.jsonl',[r for r in rows if r['labels']]);lines('goal_drift_cases.jsonl',[r for r in rows if 'F3'in r['labels']or r['goal_check'].get('high_confidence_mismatch')])
 summary=read(OUT/'evidence/atlas_summary.json')
 for item in summary['taxonomy']:
  rs=[r for r in rows if item['code']in r['labels']];ids={r['task_id']for r in rs};ok=sum(any(r['task_id']==t and r['offline_status']=='correct'for r in rows)for t in ids)
  item.update(records=len(rs),tasks=len(ids),task_fraction=len(ids)/summary['tasks'],ever_historical_correct_tasks=ok,no_confirmed_correct_tasks=len(ids)-ok,subjects=dict(collections.Counter(next(r['subject']for r in rs if r['task_id']==t)for t in ids)),mean_output_tokens=sum(r['usage'].get('completion_tokens',0)for r in rs)/max(1,len(rs)))
 save('evidence/atlas_summary.json',summary)
 seal=read(OUT/'evidence/stage1_sealed.json');seal.update(sealed_at=now(),files={p:sha(OUT/p)for p in seal['files']});save('evidence/stage1_sealed.json',seal)
 print('Pre-call metadata reconciled; freeze this result before any generation.')
if __name__=='__main__':main()
