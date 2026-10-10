"""Deterministic pre-call exclusions, preserved alongside the initial split."""
from common import *
from flowevo_recovery.public import Task
from flowevo_recovery.checks import run_tests
from rapidfuzz.fuzz import ratio
import re
if __name__=='__main__':
 assert not list((OUT/'raw_calls').glob('*.json')),'only before paid calls'
 assert not (OUT/'snapshots/preflight_original_split.json').exists()
 train=lines(OUT/'data/train_code_tasks.jsonl');conf=lines(OUT/'data/confirmation_tasks.jsonl');labels=read(OUT/'data/offline_labels.json')
 write(OUT/'snapshots/preflight_original_split.json',{'manifest':read(OUT/'dataset_split_manifest.json'),'train':train,'confirmation':conf})
 audit=read(OUT/'evidence/preflight.json');bad_train={r['task_id'] for r in audit['canonical_checks'] if not r['check']['passed']};bad_conf={r['confirmation_id'] for r in audit['code_near_pairs_085']}
 used={t['task_id'] for t in train+conf};norm=lambda s:re.sub(r'\d+','#',' '.join(s.lower().split()))
 rows=sorted([r for r in lines(EXTERNAL/'data/raw/mbpp/mbpp.jsonl') if r['task_id']>=601 and len(r['test_list'])>=3],key=lambda r:digest(['recovery-code',norm(r['text'])]))
 replacements=[]
 for pool,bad in [(train,bad_train),(conf,bad_conf)]:
  for i,t in enumerate(pool):
   if t['task_id'] not in bad:continue
   for r in rows:
    tid='mbpp_train_'+str(r['task_id'])
    if tid in used:continue
    if any(ratio(norm(r['text']),norm(x['problem']))>=85 for x in train+conf if x['domain']=='code' and x['task_id'] not in bad_train|bad_conf):continue
    if not run_tests(r['code'],r['test_list'],r.get('test_setup_code',''))['passed']:continue
    pool[i]=Task(task_id=tid,domain='code',problem=r['text'],public_tests=r['test_list'][:1],setup=r.get('test_setup_code','')).model_dump()
    labels[tid]={'hidden_tests':r['test_list'][1:],'reference':r['code']};labels.pop(t['task_id']);used.add(tid)
    replacements.append({'old':t['task_id'],'new':tid,'reason':'reference_environment' if t['task_id'] in bad_train else 'cross_split_similarity_ge085'});break
   else:raise RuntimeError('no eligible replacement')
 jl(OUT/'data/train_code_tasks.jsonl',train);jl(OUT/'data/confirmation_tasks.jsonl',conf);write(OUT/'data/offline_labels.json',labels)
 m=read(OUT/'dataset_split_manifest.json');m.update(train_code_ids=[t['task_id'] for t in train],confirmation_ids=[t['task_id'] for t in conf],pre_call_replacements=replacements,deduplication='disjoint IDs; digit-masked exact groups; reject cross-split text ratio>=0.85; canonical reference sandbox preflight; no universal semantic disjointness claim')
 m['files']={n:sha(OUT/'data'/n) for n in m['files']};write(OUT/'dataset_split_manifest.json',m)
 write(OUT/'evidence/precall_refinement.json',{'at':now(),'replacements':replacements,'paid_calls_so_far':0,'training_math_states':7,'math_selection_note':'Only six subjects had truncated training states; plus one audited genuine arithmetic failure. All retained without invented eighth case.'})
 print(replacements)
