"""Run in FlowEvo's environment: native cot prompt with no skill library."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'FlowEvo/src'))
from code_math.runner import build_goldfree_math_prompt,CONDITIONS
from core.schemas import CodeTaskInstance

def main():
 c=CONDITIONS['cot_baseline'];assert c['cot'] and not c['compile'] and not c['use_skill'] and not c['retry']
 tasks=[json.loads(x) for x in (OUT/'data/public_tasks.jsonl').read_text().splitlines()];out=[]
 for p in tasks:
  assert not {'gold_answer','reference_solution','solution','correct'}&p.keys()
  t=CodeTaskInstance(task_id=p['task_id'],benchmark='math',prompt=p['problem'])
  prompt=build_goldfree_math_prompt(t,library=None,cot=True)
  assert prompt==f"Problem: {p['problem']}\n\nSolve step by step. End with: The answer is [your answer]."
  out.append({'task_id':p['task_id'],'prompt':prompt,'skill_injected':False,'skill_retrieval_count':0,'gold_exposed':False})
 artifact={'implementation':'FlowEvo/src/code_math/runner.py','implementation_sha256':hashlib.sha256((ROOT/'FlowEvo/src/code_math/runner.py').read_bytes()).hexdigest(),'condition':'cot_baseline','library':None,'prompts':out}
 (OUT/'data/native_prompts.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
 print('Native FlowEvo CoT prompts exported:',len(out),'No library or gold.')
if __name__=='__main__':main()
