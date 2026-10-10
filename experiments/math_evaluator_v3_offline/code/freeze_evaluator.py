from common import *
from math_evaluation import EvaluatorConfig
from math_evaluation.engine import check_versions
paths=sorted((ROOT/'FlowEvo/src/math_evaluation').glob('*.py'))+[ROOT/'FlowEvo/src/code_math/evaluate_offline.py',ROOT/'FlowEvo/requirements-math-evaluator-v3.txt']
files={str(p.relative_to(ROOT)):sha(p) for p in paths}
save('evidence/evaluator_freeze.json',{'timestamp':now(),'reference_commit':REF,'source_files':files,'source_tree_sha256':digest(files),'config':EvaluatorConfig().to_dict(),'config_hash':EvaluatorConfig().hash(),'dependencies':check_versions(),'scope':'Retrospective engineering: three full development passes and historical regression cases preceded this freeze; not independent held-out evaluation.'})
print(digest(files))
