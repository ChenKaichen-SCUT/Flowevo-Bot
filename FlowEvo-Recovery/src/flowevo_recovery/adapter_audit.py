"""Predeclared zero-call sensitivity: select the first block defining the PUBLIC entrypoint.
This never checks hidden tests to pick a block and is not part of A/C routing.
"""
import ast,re
from .checks import extract_code,run_tests

def extract_public_entrypoint(solution,public_tests):
 names=[]
 for t in public_tests:
  try:
   tree=ast.parse(t)
   names.extend(n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name))
  except SyntaxError:pass
 for block in re.findall(r'```(?:python|py)?\s*\n(.*?)```',solution,re.S|re.I):
  try:tree=ast.parse(block)
  except SyntaxError:continue
  defined={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
  if defined & set(names):return block.strip()
 return extract_code(solution)

def audit(state,label):
 code=extract_public_entrypoint(state.solution,state.task.public_tests)
 return {'changed_extraction':code!=extract_code(state.solution),'check':run_tests(code,label['hidden_tests'],state.task.setup)}
