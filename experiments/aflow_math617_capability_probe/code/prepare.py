"""Recover the author's files unchanged; audit metadata without designing from labels."""
from common import *
import collections,csv,random
sys.path.insert(0,str(ROOT/'Flowevo-Bot/src'))
from flowevo_bot.taxonomy import normalize_subject
from flowevo_bot.features import normalize_problem
from rapidfuzz import process,fuzz

def main():
 if (OUT/'dataset_manifest.json').exists():
  print('Dataset already frozen; reuse');return
 local={};byhash=collections.defaultdict(list)
 for split in ('train','test'):
  counter=collections.Counter()
  for row in jl(ROOT/f'FlowEvo/data/datasets/math/{split}.jsonl'):
   sub=normalize_subject(row['type']);idx=counter[sub];counter[sub]+=1
   tid=f'math_{split}_{sub}_{idx}';local[tid]=dict(row,task_id=tid,subject=sub)
   byhash[digest(norm(row['problem']))].append(tid)
 prior=ROOT/'experiments/math500_scoring_and_budget_v2'
 registry=read(prior/'evidence/exposure_registry.json')
 screen={r['task_id']:r for r in jl(prior/'evidence/global_near_duplicate_screen.jsonl')}
 index=read(prior/'evidence/exposure_artifact_index.json')
 history=jl(ROOT/'experiments/failure_mechanism_a1_a2_pilot/historical_records.jsonl')
 old_actual={r['task_id']for r in history}
 recent=jl(prior/'data/public_tasks.jsonl')+jl(ROOT/'experiments/failure_mechanism_a1_a2_pilot/data/public_tasks.jsonl')
 recent_ids={r['task_id']for r in recent};old_actual|=recent_ids
 recent_choices={r['task_id']:normalize_problem(r['problem'],True)for r in recent}
 bank_ids={tid for a in index if ('bank' in a['path'].lower() or 'skill' in a['path'].lower()) and not a['path'].endswith('.py') for tid in a['ids']}
 excluded=set(registry['excluded_ids']);pub=[];labels=[];items=[]
 for split,filename in [('validation','math_validate.jsonl'),('test','math_test.jsonl')]:
  for idx,row in enumerate(jl(OUT/'data/official'/filename)):
   h=digest(norm(row['problem']));matches=[tid for tid in byhash[h]if tid.startswith('math_test_')]
   assert len(matches)==1,(idx,matches)
   tid=matches[0];original=local[tid]
   assert row=={k:original[k]for k in row},tid
   sub=original['subject'];public={'task_id':tid,'problem':row['problem'],'subject':sub,'level':row['level'],'split':split,'official_row_index':idx}
   pub.append(public);labels.append({'task_id':tid,'reference_raw':row['solution']})
   hit=process.extractOne(normalize_problem(row['problem'],True),{k:v for k,v in recent_choices.items()if k!=tid},scorer=fuzz.ratio,score_cutoff=90)
   src=[a['path']for a in index if tid in a['ids']]
   exact_training=[x for x in byhash[h]if x.startswith('math_train_')]
   previous=screen.get(tid)
   exposure={'known_previous_solve_or_analysis':tid in old_actual,'conservative_prior_registry_flag':tid in excluded,'historical_source_paths':src,'previous_near_screen_reused':previous,'new_near_duplicate':{'task_id':hit[2],'ratio':hit[1]}if hit else None,'exact_text_training_matches':exact_training,'exact_skill_bank_id':tid in bank_ids,'exact_skill_bank_text_matches':[x for x in byhash[h]if x in bank_ids]}
   exposure['no_recorded_direct_exposure']=not exposure['known_previous_solve_or_analysis'] and not exposure['conservative_prior_registry_flag']
   exposure['strict_clean_of_recorded_and_near_exposure']=exposure['no_recorded_direct_exposure'] and not exact_training and not hit and not(previous and previous['excluded_near_duplicate'])
   items.append({k:public[k]for k in public if k!='problem'}|{'problem_sha256':digest(row['problem']),'normalized_problem_sha256':h,'reference_sha256':digest(row['solution']),'official_row_sha256':digest(row),'exposure':exposure})
 assert len(items)==605 and len({x['task_id']for x in items})==605
 csv_checks=[]
 for p in sorted((OUT/'evidence/official_results/results/MATH').rglob('*.csv')):
  with p.open()as f:rs=list(csv.DictReader(f))
  hashes={digest(norm(r['question']))for r in rs}
  expected={x['normalized_problem_sha256']for x in items if x['split']==('test'if len(rs)==486 else 'validation')}
  csv_checks.append({'path':str(p.relative_to(OUT)),'rows':len(rs),'unique_questions':len(hashes),'equals_current_official_split':hashes==expected,'sha256':sha(p)})
 lines('data/public_tasks.jsonl',pub);lines('data/offline_labels.jsonl',labels)
 lines('data/public_prompts.jsonl',[{'task_id':r['task_id'],'problem':r['problem'],'subject':r['subject'],'level':r['level'],'prompt':f"Problem: {r['problem']}\n\nSolve step by step. End with: The answer is [your answer]."}for r in pub])
 lines('evidence/official_csv_partition_checks.jsonl',csv_checks)
 summary={split:{'n':sum(x['split']==split for x in items),'subjects':dict(collections.Counter(x['subject']for x in items if x['split']==split)),'known_prior':sum(x['exposure']['known_previous_solve_or_analysis']for x in items if x['split']==split),'registry_flagged':sum(x['exposure']['conservative_prior_registry_flag']for x in items if x['split']==split),'strict_clean':sum(x['exposure']['strict_clean_of_recorded_and_near_exposure']for x in items if x['split']==split)}for split in ('validation','test')}
 manifest={'created_at':now(),'reference_commit':REF,'paper_claimed_n':617,'recovered_n':605,'missing_from_paper_claim':12,'same_617_verified':False,'author_current_download_restored_exactly':True,'partition':summary,'task_id_policy':'Local normalized MATH subject-order identifiers mapped by exact text and all fields; official JSONL has no native IDs. All official row indices retained.','seed':{'paper_reported':42,'split_generator_available':False,'reproduced_from_seed':False,'actual_partition':'Preserved verbatim from author archive; archived 2024 result CSVs cross-checked. Subject counts agree with floor(20% n_subject), not proof of exact seed algorithm.'},'high_variance_subset':{'paper_describes':'5 blank-template validation runs followed by high-variance selection','current_evaluator_va_list':None,'applied_here':False,'reason':'No uniquely identified retained-index artifact; preserve full published validation 119.'},'near_duplicate_rule':'Reuse prior digit-masked RapidFuzz>=90 screen; additionally compare against recent 500+40 public tasks. Exact ID and normalized text maps include all local train/test; potential train-catalog overlap distinguished from known solves.','prior_screen_path':str((prior/'evidence/global_near_duplicate_screen.jsonl').relative_to(ROOT)),'prior_screen_sha256':sha(prior/'evidence/global_near_duplicate_screen.jsonl'),'source_files':{str(p.relative_to(ROOT)):sha(p)for p in [OUT/'data/official/math_validate.jsonl',OUT/'data/official/math_test.jsonl',ROOT/'FlowEvo/data/datasets/math/test.jsonl',ROOT/'FlowEvo/data/datasets/math/train.jsonl',prior/'evidence/exposure_registry.json',prior/'evidence/exposure_artifact_index.json']},'tasks':items,'limitations':['Cannot claim the exact paper 617 population.','Prior solver/evaluator development exposure is flagged, so official test is not wholly research-independent.','No assurance of absence of model pretraining contamination.','Digit-masked fuzzy matches are warnings, not proof of semantic identity.']}
 save('dataset_manifest.json',manifest)
 print(json.dumps({'partition':summary,'archived_csv_counts':dict(collections.Counter(x['rows']for x in csv_checks)),'all_archived_partitions_match':all(x['equals_current_official_split']for x in csv_checks)},ensure_ascii=False))
if __name__=='__main__':main()
