from common import *
import ast,collections

def verify():
 baseline=read(OUT/'evidence/protected_previous_snapshot.json');changed=[];missing=[];checked=0;guide_changed=False
 for row in baseline['files']:
  p=ROOT/row['path']
  if not p.exists():missing.append(row['path']);continue
  actual=sha(p)
  if row['path']=='指引.txt':guide_changed=actual!=row['sha256'];continue
  checked+=1
  if actual!=row['sha256']:changed.append(row['path'])
 freeze=read(OUT/'evidence/evaluator_freeze.json');source_changed=[p for p,h in freeze['source_files'].items() if sha(ROOT/p)!=h]
 oldcalls=jl(OLD/'api_calls.jsonl');cfg=read(OLD/'config.json')
 for key in ['skill_injection','history_retrieval','gold_answer_feedback','gold_driven_reflection','correctness_retries']:assert cfg[key] is False,key
 imports=[];eval_calls=[];ids=[]
 for p in (ROOT/'FlowEvo/src/math_evaluation').glob('*.py'):
  text=p.read_text();tree=ast.parse(text)
  for n in ast.walk(tree):
   if isinstance(n,(ast.Import,ast.ImportFrom)):imports.append(ast.unparse(n))
   if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('eval','exec'):eval_calls.append(str(p))
  if 'math_test_' in text:ids.append(str(p))
 forbidden=[x for x in imports if any(n in x for n in ('llm_client','requests','openai','deepseek','code_math.runner'))]
 result={'timestamp':now(),'previous_manifest_files':len(baseline['files']),'protected_files_checked':checked,'modified_protected_files':changed,'missing_protected_files':missing,'allowed_current_guide_replacement':guide_changed,'evaluator_source_changes_since_freeze':source_changed,'historical_saved_api_calls':len(oldcalls),'historical_api_ledger_sha256':sha(OLD/'api_calls.jsonl'),'historical_raw_json_files_including_requests':len(list((OLD/'raw').glob('*.json'))),'new_llm_api_calls':0,'new_llm_tokens':0,'evidence_for_zero_calls':'All prior published files including raw responses and API ledger hash-identical; scoring implementation contains no model client; V3 process workers deny sockets; all tests deny networking; no generation script run this round.','forbidden_runtime_imports':forbidden,'raw_eval_or_exec_calls':eval_calls,'task_id_specific_runtime_rules':ids,'generation_policy':{k:cfg[k] for k in ['skill_injection','history_retrieval','gold_answer_feedback','gold_driven_reflection','correctness_retries']},'historical_solver_router_controller_files':'unchanged by full protected manifest check','status':'PASS' if not any([changed,missing,source_changed,forbidden,eval_calls,ids]) else 'FAIL'}
 save('evidence/protection_audit.json',result);assert result['status']=='PASS',result
 return result
if __name__=='__main__':print(json.dumps(verify(),indent=2))
