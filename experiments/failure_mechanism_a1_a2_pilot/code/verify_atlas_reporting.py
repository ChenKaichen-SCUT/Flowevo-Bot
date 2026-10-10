"""Recompute reporting aggregates from sealed evidence without redoing extraction/grading."""
from common import *
import collections,csv

def main():
 rows=jl(OUT/'historical_records.jsonl');seal=read(OUT/'evidence/stage1_sealed.json')
 for p,h in seal['files'].items():assert sha(OUT/p)==h,p
 old=read(OUT/'evidence/atlas_summary.json');summary=dict(old);taxonomy=[]
 for item in old['taxonomy']:
  c=item['code'];rs=[r for r in rows if c in r['labels']];ids={r['task_id']for r in rs};ok=sum(any(r['task_id']==tid and r['offline_status']=='correct' for r in rows)for tid in ids)
  x=dict(item,records=len(rs),tasks=len(ids),task_fraction=len(ids)/old['tasks'],ever_historical_correct_tasks=ok,no_confirmed_correct_tasks=len(ids)-ok,subjects=dict(collections.Counter(next(r['subject']for r in rs if r['task_id']==tid)for tid in ids)),mean_output_tokens=sum(r['usage'].get('completion_tokens',0)for r in rs)/max(1,len(rs)))
  taxonomy.append(x)
 summary['taxonomy']=taxonomy;summary['reporting_aggregate_checked_at']=now();summary['sealed_sources_unchanged']=True
 save('evidence/atlas_summary_verified.json',summary)
 with (OUT/'failure_taxonomy.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(taxonomy[0]));w.writeheader();w.writerows(taxonomy)
 save('evidence/atlas_reporting_reconciliation.json',{'at':now(),'changed_aggregates':[{'code':a['code'],'before':a,'after':b}for a,b in zip(old['taxonomy'],taxonomy)if a!=b],'changed_labels_or_grades':False,'paid_calls':0,'reason':'Complete task-level subject/output aggregation after restoring V3 exponent-limit interface case; primary case evidence and all pre-call seals unchanged.'})
 print([(x['code'],x['records'],x['tasks'])for x in taxonomy])
if __name__=='__main__':main()
