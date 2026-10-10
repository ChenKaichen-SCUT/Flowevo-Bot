"""Retrospective parser attribution; all original MBPP tests were public."""
from common import *
from flowevo_recovery.adapter_audit import extract_public_entrypoint
from flowevo_recovery.checks import extract_code,run_tests
import concurrent.futures as cf,collections,shutil

def work(job):
 r,t=job;s=r['response']['choices'][0]['message']['content'];native=r['observation']['candidate'];fixed=extract_public_entrypoint(s,t['test_list'])
 return {'task_id':r['task_id'],'original_first_passed':r['observation']['passed'],'native_candidate_same_as_current':native.strip()==extract_code(s).strip(),'changed_extraction':native.strip()!=fixed.strip(),'adapter_check':run_tests(fixed,t['test_list'],t.get('test_setup_code','')),'native_candidate_chars':len(native),'full_output_chars':len(s)}
if __name__=='__main__':
 cap();src=EXTERNAL/'experiments/flowevo_native_mbpp500_20261008/tasks.json';dst=OUT/'snapshots/native_code_tasks.json';shutil.copy2(src,dst)
 tasks={r['task_id']:r for r in read(dst)};rows=[r for r in lines(OUT/'snapshots/native_code_first_passes.jsonl') if not r['observation']['passed']]
 with cf.ProcessPoolExecutor(max_workers=12) as pool:results=list(pool.map(work,[(r,tasks[r['task_id']]) for r in rows]))
 jl(OUT/'evidence/historical_code_adapter_audit.jsonl',results)
 cases=lines(OUT/'failure_cases.jsonl');by={r['task_id']:r for r in results}
 for r in cases:
  r['stage']='historical_audit'
  if r['domain']=='code':
   a=by[r['task_id']];r['adapter_audit']=a
   if a['changed_extraction'] and a['adapter_check']['passed']:
    r['primary']='Answer/Format Failure';r['secondary']=['Evaluator/Environment Issue'];r['failure_location']='native first-code-block extraction';r['unknowns']='Complete function exists elsewhere in the same sealed output; zero-call public-entrypoint extraction passes all original public tests. No reasoning-repair claim.'
 jl(OUT/'failure_cases.jsonl',cases)
 csvwrite(OUT/'failure_labels.csv',[{k:v for k,v in r.items() if k in ['task_id','domain','stage','primary','secondary','truncated','reviewed_correct','failure_location','unknowns']} for r in cases])
 write(OUT/'evidence/historical_adapter_summary.json',{'audited_original_failures':len(results),'changed_extraction':sum(r['changed_extraction'] for r in results),'zero_call_rescued':sum(r['changed_extraction'] and r['adapter_check']['passed'] for r in results),'native_extractor_match':sum(r['native_candidate_same_as_current'] for r in results),'taxonomy_counts':{d:dict(collections.Counter(r['primary'] for r in cases if r['domain']==d)) for d in ('math','code')}})
 print(json.dumps(read(OUT/'evidence/historical_adapter_summary.json'),indent=2))
