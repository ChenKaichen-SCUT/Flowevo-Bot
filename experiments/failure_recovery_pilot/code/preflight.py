from common import *
from flowevo_recovery.checks import run_tests
from rapidfuzz.fuzz import ratio
import concurrent.futures as cf,re

def canonical(job):
 t,l=job
 return {'task_id':t['task_id'],'check':run_tests(l['reference'],t['public_tests']+l['hidden_tests'],t['setup'])}
if __name__=='__main__':
 cap();train=lines(OUT/'data/train_code_tasks.jsonl');conf=lines(OUT/'data/confirmation_tasks.jsonl');labels=read(OUT/'data/offline_labels.json')
 norm=lambda s:re.sub(r'\d+','#',re.sub(r'\s+',' ',s.lower())).strip()
 near=[]
 for t in train:
  for v in conf:
   if v['domain']=='code':
    sim=ratio(norm(t['problem']),norm(v['problem']))/100
    if sim>=.85:near.append({'train_id':t['task_id'],'confirmation_id':v['task_id'],'similarity':sim,'train':t['problem'],'confirmation':v['problem']})
 with cf.ProcessPoolExecutor(max_workers=12) as pool:checks=list(pool.map(canonical,[(t,labels[t['task_id']]) for t in train+conf if t['domain']=='code']))
 write(OUT/'evidence/preflight.json',{'created_at':now(),'code_near_pairs_085':near,'canonical_checks':checks})
 print('near_pairs',len(near));print(json.dumps(near,indent=2));print('canonical_failures',json.dumps([r for r in checks if not r['check']['passed']],indent=2))
