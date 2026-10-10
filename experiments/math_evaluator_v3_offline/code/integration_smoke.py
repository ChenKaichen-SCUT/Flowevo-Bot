from common import *
import subprocess,os,tempfile

def main():
 env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join([str(ROOT/'FlowEvo/src'),str(ROOT/'Flowevo-Bot/src'),str(ROOT/'FlowEvo-Recovery/src')])
 rows=[]
 for name in ['legacy','fixed','v3']:
  path=OUT/f'evidence/native_cli_{name}.jsonl'
  if path.exists():raise RuntimeError('Smoke output already exists; choose a new evidence directory instead of overwriting')
  cmd=[sys.executable,'-m','code_math.evaluate_offline','--input',str(OUT/'evidence/native_runner_records.jsonl'),'--tasks',str(OUT/'evidence/native_loader_tasks.jsonl'),'--sealed','--output',str(path),'--workers','12']
  if name!='legacy':cmd+=['--evaluator',name]
  if name=='v3':cmd+=['--unknown-output',str(OUT/'evidence/native_unknown_queue.jsonl')]
  p=subprocess.run(cmd,env=env,cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,p.stderr
  results=jl(path);assert len(results)==6
  if name=='v3':assert all(r['status']=='correct' for r in results),results
  rows.append({'evaluator':name,'command':cmd,'stdout':p.stdout,'records':len(results),'correct':sum(r['status']=='correct' for r in results),'output':str(path.relative_to(OUT))})
 # Explicit output overwrite guard must reject without changing saved records.
 before=sha(path);reject=subprocess.run(cmd,env=env,cwd=ROOT,capture_output=True,text=True);assert reject.returncode!=0 and sha(path)==before
 save('evidence/integration_smoke.json',{'status':'PASS','native_loader_tasks':6,'native_cli':rows,'overwrite_rejected':True,'default_evaluator':'legacy','solver_imported':False,'model_calls':0})
 print('native loader + all three configured CLI evaluators PASS')
if __name__=='__main__':main()
