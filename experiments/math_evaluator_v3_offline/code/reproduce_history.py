from common import *
import concurrent.futures as cf,time,importlib.metadata as md,shutil
from flowevo_bot.evaluator import extract_answer
from flowevo_bot.experiment_grader import grade_one
from flowevo_recovery.math_scoring_v2 import grade

def evaluate(r):
 start=time.perf_counter();a=extract_answer(r['prediction_raw']);l=grade_one((r['task_id'],a,r['frozen_gold_answer'],r['finish_reason']=='length'));lt=time.perf_counter()-start
 start=time.perf_counter();f=grade({'task_id':r['task_id'],'solution':r['prediction_raw'],'question':r['question'],'gold_answer':r['frozen_gold_answer'],'truncated':r['finish_reason']=='length'});ft=time.perf_counter()-start
 return dict(r,legacy=l,fixed=f,legacy_seconds=lt,fixed_seconds=ft)
def main():
 tasks={x['task_id']:x for x in jl(OLD/'data/public_tasks.jsonl')};labels={x['task_id']:x for x in jl(OLD/'data/offline_labels.jsonl')};records=[]
 for branch,file in [('base','first_pass_results.jsonl'),('adaptive','adaptive_results.jsonl')]:
  for c in jl(OLD/file):
   tid=c['task_id'];records.append({'record_id':branch+':'+tid,'branch':branch,'task_id':tid,'subject':tasks[tid]['subject'],'level':tasks[tid]['level'],'question':tasks[tid]['problem'],'reference_raw':labels[tid]['reference_solution'],'frozen_gold_answer':labels[tid]['gold_answer'],'prediction_raw':c['response']['choices'][0]['message'].get('content') or '', 'finish_reason':c['finish_reason'],'source_job_id':c['job_id'],'source_path':str((OLD/'raw'/f"{c['job_id']}.json").relative_to(ROOT)),'request_hash':c['request_hash'],'response_hash':c['response_hash'],'submission_sealed':True})
 start=time.perf_counter()
 with cf.ProcessPoolExecutor(max_workers=12) as p:rs=list(p.map(evaluate,records))
 counts={b:{'legacy':sum(x['legacy']['final_correct'] for x in rs if x['branch']==b),'fixed':sum(x['fixed']['correct'] is True for x in rs if x['branch']==b)} for b in ('base','adaptive')}
 assert counts=={'base':{'legacy':456,'fixed':449},'adaptive':{'legacy':485,'fixed':476}},counts
 oldl={x['job_id']:x['grade'] for x in jl(OLD/'legacy_scoring_results.jsonl')};oldf={x['job_id']:x['grade'] for x in jl(OLD/'fixed_scoring_results.jsonl')}
 for r in rs:assert r['legacy']['final_correct']==oldl[r['source_job_id']]['correct'] and r['fixed']['correct'] is oldf[r['source_job_id']]['correct']
 lines('evidence/input_records.jsonl',records);lines('evidence/legacy_fixed_reproduced.jsonl',rs)
 save('evidence/history_reproduction.json',{'counts':counts,'records':len(rs),'distinct_tasks':len({r['task_id'] for r in rs}),'wall_seconds':time.perf_counter()-start,'workers':12,'matches_frozen_per_record':True,'added_llm_calls':0})
 deps=[]
 for name in ['math-verify','sympy','latex2sympy2_extended','antlr4-python3-runtime','mpmath']:
  d=md.distribution(name);ls=[f for f in d.files if 'license' in str(f).lower() and not str(f).endswith('/')];deps.append({'name':name,'version':d.version,'license':d.metadata.get('License'),'requires':d.requires,'license_files':[str(x) for x in ls]})
  for i,lf in enumerate(ls):
   src=d.locate_file(lf)
   if src.is_file():shutil.copyfile(src,OUT/'evidence'/f'{name}_license_{i}.txt')
 save('evidence/dependency_audit.json',{'packages':deps,'math_verify_use':'Bounded ANTLR-derived numeric objects and comparison diagnostics; no raw ExprExtractionConfig or string fallback. Final decisions require typed exact equivalence and domain proof.','known_limitations':['Math-Verify default unit stripping is unsuitable for dimension checks.','Default numeric tolerance is not an identity proof.','Default interval/relation comparison is asymmetric.','ANTLR accepts some notation with lost annotations; V3 validates tokens and handles base subscripts separately.'],'sources':['https://github.com/huggingface/Math-Verify','https://github.com/huggingface/latex2sympy2_extended','https://docs.sympy.org/latest/modules/parsing.html']})
 print(counts,flush=True)
if __name__=='__main__':main()
