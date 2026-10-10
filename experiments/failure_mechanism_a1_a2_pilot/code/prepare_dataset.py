"""Reuse completed exposure screening; only screen the newly exposed 500 and select 40."""
from common import *
import collections,random,re
from rapidfuzz import process,fuzz
from flowevo_bot.taxonomy import normalize_subject
from flowevo_bot.features import normalize_problem
SEED=20261020

def main():
 if (OUT/'dataset_manifest.json').exists():print('Reusing frozen pilot selection; no resampling');return
 old=ROOT/'experiments/math500_scoring_and_budget_v2';registry=read(old/'evidence/exposure_registry.json');excluded=set(registry['excluded_ids']);newly_exposed={r['task_id'] for r in jl(old/'data/public_tasks.jsonl')};excluded|=newly_exposed
 # Prior V3 work only reused these two 500 cohorts; tests' native tasks map to them.
 oldscreen={r['task_id']:r for r in jl(old/'evidence/global_near_duplicate_screen.jsonl')}
 rows={};counter=collections.Counter()
 for r in jl(ROOT/'FlowEvo/data/datasets/math/test.jsonl'):
  sub=normalize_subject(r['type']);i=counter[sub];counter[sub]+=1;tid=f'math_test_{sub}_{i}';rows[tid]=dict(r,task_id=tid,subject=sub,source_subject_index=i)
 choices={tid:normalize_problem(rows[tid]['problem'],True) for tid in newly_exposed}
 additional=[];eligible=[]
 for tid,r in rows.items():
  if tid in excluded or tid not in oldscreen or oldscreen[tid]['excluded_near_duplicate']:continue
  hit=process.extractOne(normalize_problem(r['problem'],True),choices,scorer=fuzz.ratio,score_cutoff=90)
  additional.append({'task_id':tid,'new_exposure_near_duplicate':bool(hit),'nearest_id':hit[2] if hit else None,'similarity':hit[1] if hit else None})
  if not hit:eligible.append(r)
 rng=random.Random(SEED);subjects=sorted(counter);extra=set(rng.sample(subjects,5));groups=collections.defaultdict(list)
 for r in eligible:
  lv=int(r['level'][-1]);groups[(r['subject'],'general_1_2' if lv<=2 else 'general_3' if lv==3 else 'hard_4_5')].append(r)
 chosen=[];seen={};quotas=[]
 for sub in subjects:
  for band,n in [('general_1_2',1),('general_3',1),('hard_4_5',4 if sub in extra else 3)]:
   pool=sorted(groups[sub,band],key=lambda r:r['task_id']);rng.shuffle(pool);count=0
   for r in pool:
    text=normalize_problem(r['problem'],True)
    if seen and process.extractOne(text,seen,scorer=fuzz.ratio,score_cutoff=90):continue
    chosen.append(r);seen[r['task_id']]=text;count+=1
    if count==n:break
   assert count==n,(sub,band,count,n)
   quotas.append({'subject':sub,'band':band,'n':n})
 assert len(chosen)==40 and not(set(seen)&excluded)
 public=[{k:r[k] for k in ['task_id','problem','subject','level','source_subject_index']} for r in sorted(chosen,key=lambda r:r['task_id'])]
 labels=[{'task_id':r['task_id'],'reference_raw':r['solution']} for r in chosen]
 lines('data/public_tasks.jsonl',public);lines('data/offline_labels.jsonl',labels);lines('evidence/additional_exposure_screen.jsonl',additional)
 prompts=[{'task_id':r['task_id'],'problem':r['problem'],'subject':r['subject'],'level':r['level'],'prompt':f"Problem: {r['problem']}\n\nSolve step by step. End with: The answer is [your answer]."} for r in public]
 lines('data/public_prompts.jsonl',prompts)
 save('dataset_manifest.json',{'seed':SEED,'tasks':40,'general':14,'hard':26,'strata':quotas,'selection_used_labels':False,'known_exposure_exclusion_count':len(excluded),'additional_exposed_tasks':len(newly_exposed),'prior_global_screen_reused':str((old/'evidence/global_near_duplicate_screen.jsonl').relative_to(ROOT)),'prior_global_screen_sha256':sha(old/'evidence/global_near_duplicate_screen.jsonl'),'eligible_after_new_screen':len(eligible),'new_screen_rule':'digit-masked normalized text RapidFuzz ratio>=90 versus newly exposed 500 and within pilot','selected_ids':sorted(seen),'public_sha256':sha(OUT/'data/public_tasks.jsonl'),'labels_sha256':sha(OUT/'data/offline_labels.jsonl'),'source_sha256':sha(ROOT/'FlowEvo/data/datasets/math/test.jsonl'),'independence':'No recorded solve/development exposure; earlier public candidate catalogs do not count as empirical exposure; no model-pretraining independence claim.'})
 print({'selected':40,'old_screen_reused':True,'eligible':len(eligible),'labels_used_for_selection':False})
if __name__=='__main__':main()
