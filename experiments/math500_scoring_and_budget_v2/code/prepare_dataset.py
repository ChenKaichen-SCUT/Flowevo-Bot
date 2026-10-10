"""Question-only selection, conservative exposure exclusion, global fuzzy screen."""
from common import *
import re,random,collections,concurrent.futures as cf,shutil,time
from flowevo_bot.taxonomy import normalize_subject
from flowevo_bot.features import normalize_problem
from flowevo_bot.evaluator import extract_answer
from rapidfuzz import process,fuzz
SEED=20261010
PAT=re.compile(r'math_(?:train|test)_(?:algebra|prealgebra|intermediate_algebra|number_theory|counting_probability|geometry|precalculus)_\d+')
NATIVE=re.compile(r'\bmath_(algebra|prealgebra|intermediate_algebra|number_theory|counting_and_probability|counting_probability|geometry|precalculus)_(\d+)\b')
ROOTS=['Flowevo-Bot/experiments','experiments/failure_recovery_pilot','experiments/math_truncation_and_scoring_audit','FlowEvo/runs','Flowevo-Bot/runs','Flowevo-Bot/data/candidates','Flowevo-Bot/data/skill_banks','buffer-of-thought-llm']
CHOICES=None

def screen(item):
 tid,text=item;found=process.extractOne(text,CHOICES,scorer=fuzz.ratio,score_cutoff=90)
 return {'task_id':tid,'excluded_near_duplicate':found is not None,'nearest_exposed_id':found[2] if found else None,'similarity':found[1] if found else None}

def main():
 global CHOICES
 assert not (OUT/'dataset_manifest.json').exists(),'Selection is immutable; do not resample.'
 assert read(OUT/'evaluator_regression.json')['counts']['fixed_correct']==473
 shutil.copyfile(ROOT/'指引.txt',OUT/'USER_GUIDE.txt');save('evidence/protected_previous_snapshot.json',read(ROOT/'UPLOAD_MANIFEST.json'))
 allrows={};labels={};counts={}
 for split in ('train','test'):
  counter=collections.Counter()
  for row in jl(ROOT/f'FlowEvo/data/datasets/math/{split}.jsonl'):
   sub=normalize_subject(row['type']);i=counter[sub];counter[sub]+=1;tid=f'math_{split}_{sub}_{i}'
   allrows[tid]={'task_id':tid,'problem':row['problem'],'subject':sub,'level':row['level'],'source_dataset':'EleutherAI/hendrycks_math','source_split':split,'source_subject_index':i}
   labels[tid]=row
  counts[split]=sum(counter.values())
 used={tid for tid in allrows if '_train_' in tid};reasons=collections.defaultdict(set)
 for tid in used:reasons[tid].add('Conservatively exclude entire original train pool including all V1–V4 dev/confirmation and Recovery data')
 for i in range(500):tid=f'math_test_algebra_{i}';used.add(tid);reasons[tid].add('historical known/potential first500 algebra exposure exclusion')
 artifacts=[]
 for root in ROOTS:
  for path in sorted((ROOT/root).rglob('*')):
   if not path.is_file() or any(s in path.parts for s in ('.git','.venv','__pycache__','.pytest_cache','node_modules')) or path.suffix not in ('.json','.jsonl','.csv','.md','.txt','.log','.py'):continue
   text=path.read_text(errors='replace');ids=set(PAT.findall(text))
   for sub,i in NATIVE.findall(text):ids.add('math_test_'+sub.replace('counting_and_probability','counting_probability')+'_'+i)
   ids &= set(allrows)
   if ids:
    rel=str(path.relative_to(ROOT));artifacts.append({'path':rel,'sha256':sha(path),'id_count':len(ids),'ids':sorted(ids)})
    used.update(ids)
    for tid in ids:reasons[tid].add(rel)
 # Raw datasets/catalogs are availability inventories, not execution evidence.
 # All train rows are excluded regardless, so only unexecuted test catalogs matter.
 save('evidence/exposure_artifact_index.json',artifacts)
 save('evidence/exposure_registry.json',{'excluded_ids':sorted(used),'reasons':{k:sorted(v) for k,v in reasons.items()},'catalog_only_paths':['Flowevo-Bot/data/manifests/test.problems.jsonl','Flowevo-Bot/data/manifests/math_grouped/test.problems.jsonl','Flowevo-Bot/docs/development_artifacts/initial_exact_only_manifests/test.problems.jsonl'],'catalog_note':'Creating raw question inventories is not a solve/dev/confirmation run. Their IDs are not automatically labelled exposed; actual experiment records, all train/development pools, native aliases and prior known algebra exposure are excluded.'})
 candidates=[x for tid,x in allrows.items() if x['source_split']=='test' and tid not in used]
 CHOICES={tid:normalize_problem(allrows[tid]['problem'],True) for tid in sorted(used)}
 t=time.time()
 with cf.ProcessPoolExecutor(max_workers=12) as pool:checks=list(pool.map(screen,[(x['task_id'],normalize_problem(x['problem'],True)) for x in candidates],chunksize=16))
 lines('evidence/global_near_duplicate_screen.jsonl',checks)
 accepted={x['task_id'] for x in checks if not x['excluded_near_duplicate']};pool=[x for x in candidates if x['task_id'] in accepted]
 old=read(ROOT/'experiments/math_truncation_and_scoring_audit/evidence/baseline_500.json');quotas=collections.Counter((x['subject'],x['level']) for x in old)
 groups=collections.defaultdict(list)
 for x in pool:groups[(x['subject'],x['level'])].append(x)
 rng=random.Random(SEED)
 for k in sorted(groups):rng.shuffle(groups[k])
 chosen=[];chosen_text={};rejected_within=[]
 for key in sorted(quotas):
  n=0
  for x in groups[key]:
   text=normalize_problem(x['problem'],True);match=process.extractOne(text,chosen_text,scorer=fuzz.ratio,score_cutoff=90) if chosen_text else None
   if match:rejected_within.append({'task_id':x['task_id'],'duplicate_of':match[2],'similarity':match[1]});continue
   chosen.append(x);chosen_text[x['task_id']]=text;n+=1
   if n==quotas[key]:break
  if n<quotas[key]:raise RuntimeError(f'Insufficient independent stratum {key}: {n}/{quotas[key]}; no API permitted')
 assert len(chosen)==500 and not (set(x['task_id'] for x in chosen)&used)
 chosen.sort(key=lambda x:x['task_id']);public=[];evaluation=[]
 for x in chosen:
  tid=x['task_id'];entry={**x,'problem_hash':hashlib.sha256(x['problem'].encode()).hexdigest(),'selection_seed':SEED,'prior_exposure_status':'no project exposure found; all known used/development pools excluded; global masked-text ratio<0.90 to excluded pool and other selected tasks'}
  public.append(entry)
  # Labels are materialized only after selection; never used in stratification/filtering.
  evaluation.append({'task_id':tid,'gold_answer':extract_answer(labels[tid]['solution']),'reference_solution':labels[tid]['solution']})
  assert evaluation[-1]['gold_answer'] is not None
 lines('data/public_tasks.jsonl',public);lines('data/offline_labels.jsonl',evaluation)
 manifest={'created_at':now(),'selection_seed':SEED,'source_counts':counts,'known_or_conservatively_excluded_count':len(used),'excluded_test_ids':sum('_test_' in x for x in used),'candidate_test_count':len(candidates),'near_duplicate_exclusions':sum(x['excluded_near_duplicate'] for x in checks),'eligible_after_near_screen':len(pool),'within_sample_exclusions':rejected_within,'near_duplicate_rule':'global RapidFuzz normalized Indel/LCS ratio>=90 over lowercased, whitespace-normalized, digit-masked question strings; no blocking; all excluded train/test questions; plus within-sample screen','near_screen_seconds':time.time()-t,'strata':[{'subject':k[0],'level':k[1],'historical_count':quotas[k],'new_count':sum((x['subject'],x['level'])==k for x in chosen),'eligible':len(groups[k])} for k in sorted(quotas)],'sampling':'fixed-seed shuffled strata; exact match to old500 subject×level counts; labels and historical correctness not selection inputs','count':500,'public_tasks_sha256':sha(OUT/'data/public_tasks.jsonl'),'offline_labels_sha256':sha(OUT/'data/offline_labels.jsonl'),'source_hashes':{s:sha(ROOT/f'FlowEvo/data/datasets/math/{s}.jsonl') for s in ('train','test')},'tasks':[{k:v for k,v in x.items() if k!='problem'} for x in public],'limitations':['Independence is with respect to recorded project exposure, not model pretraining.','Unlogged external usage cannot be ruled out; lexical near-duplicate screening is not a proof of semantic uniqueness.','Static raw test catalogs previously existed; these are excluded from the definition of empirical exposure, explicitly distinguished from dev/confirmation pools.']}
 save('dataset_manifest.json',manifest)
 print(json.dumps({k:manifest[k] for k in ['count','known_or_conservatively_excluded_count','excluded_test_ids','candidate_test_count','near_duplicate_exclusions','eligible_after_near_screen','near_screen_seconds']},indent=2),flush=True)
if __name__=='__main__':main()
