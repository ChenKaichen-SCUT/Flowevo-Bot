"""Export real native MATH loader tasks paired with existing sealed responses.
Run with FlowEvo/.venv/bin/python (its original datasets installation).
"""
from common import *
import socket,os
os.environ['HF_DATASETS_OFFLINE']='1';os.environ['HF_HUB_OFFLINE']='1'
def blocked(*a,**kw):raise RuntimeError('native loader smoke is offline')
socket.socket.connect=blocked;socket.create_connection=blocked
from code_math.loader import load_math
ids=['algebra_1020','intermediate_algebra_409','intermediate_algebra_516','intermediate_algebra_563','prealgebra_598','precalculus_380']
sealed={r['question']:r for r in jl(OUT/'evidence/input_records.jsonl') if r['branch']=='adaptive' and r['task_id'].removeprefix('math_test_') in ids}
tasks=[];responses=[]
for task in load_math():
 if task.prompt not in sealed:continue
 r=sealed[task.prompt];tasks.append(task.model_dump());responses.append({'task_id':task.task_id,'solution':r['prediction_raw'],'finish_reason':r['finish_reason'],'request_hash':r['request_hash'],'response_hash':r['response_hash'],'source_path':r['source_path']})
assert len(tasks)==len(ids)
lines('evidence/native_loader_tasks.jsonl',tasks);lines('evidence/native_runner_records.jsonl',responses)
save('evidence/native_loader_export.json',{'native_tasks':len(tasks),'dataset':'local original MATH Parquet via unmodified load_math()','new_solver_runs':0,'new_api_calls':0,'responses':'previous sealed adaptive responses; ID mapping by exact public question'})
print(len(tasks))
