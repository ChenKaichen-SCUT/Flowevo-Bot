"""Freeze public selections before any paid call; no selection uses gold labels."""
import random
from collections import defaultdict,Counter
from pathlib import Path
from code_math.loader import load_manifest
from flowevo_bot.common import jsonl,write_json,digest
from flowevo_bot.data import write_manifest
from flowevo_bot.schemas import EvaluationRecord
from flowevo_bot.provenance import assert_independent
from flowevo_bot.features import normalize_problem,duplicate_keys,near_duplicate
from runtime.config import load_config

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/math500_goldfree_20261009'

def select(tasks,n,seed,balanced=False):
    rng=random.Random(seed);groups=defaultdict(list)
    for t in tasks:groups[(t.subject,t.level)].append(t)
    for k in sorted(groups):rng.shuffle(groups[k])
    if balanced:
        chosen=[]
        for subject in sorted({t.subject for t in tasks}):
            sub=[t for t in tasks if t.subject==subject]
            chosen.extend(select(sub,n//7,seed))
        return sorted(chosen,key=lambda t:t.task_id)
    total=len(tasks)
    quotas={k:n*len(v)/total for k,v in groups.items()}
    counts={k:int(v) for k,v in quotas.items()}
    for k in sorted(groups,key=lambda k:(-(quotas[k]-counts[k]),k))[:n-sum(counts.values())]:counts[k]+=1
    chosen=[t for k in sorted(groups) for t in groups[k][:counts[k]]]
    return sorted(chosen,key=lambda t:t.task_id)

def independent_candidates(sources,targets):
    texts={normalize_problem(t.problem,True) for t in sources};blocks=defaultdict(list)
    for s in sources:
        for k in duplicate_keys(s.problem):blocks[k].append(s)
    keep=[];removed=[]
    for t in targets:
        candidates={s.task_id:s for k in duplicate_keys(t.problem) for s in blocks[k]}
        if normalize_problem(t.problem,True) in texts or any(near_duplicate(t.problem,s.problem) for s in candidates.values()):removed.append(t.task_id)
        else:keep.append(t)
    return keep,removed

def main():
    paths=ROOT/'data/manifests/math_grouped'
    infos={};alltasks={};labels={}
    for name in ('train','dev','test'):
        m,t,l=load_manifest(paths/(name+'.json'));infos[name]=m;alltasks[name]=t
        labels[name]={r['task_id']:EvaluationRecord.model_validate(r) for r in jsonl(l)}
    train=select(alltasks['train'],700,42,True)
    dev=select(alltasks['dev'],350,43,True)
    candidates,removed=independent_candidates(train+dev,alltasks['test'])
    test=select(candidates,500,44)
    for a,b in ((train,dev),(train,test),(dev,test)):assert_independent(a,b)
    for name,split,tasks in [('train','train-build',train),('dev','train-dev',dev),('test','test',test)]:
        write_manifest(OUT/'manifests',name,split,tasks,[labels[name][t.task_id] for t in tasks],
                       seed={'train':42,'dev':43,'test':44}[name],synthetic=False,source_manifest_hash=digest(infos[name]),
                       selection='subject/level proportional; train/dev balanced 100/50 per subject; test proportional to eligible pool',
                       holdout_claim=infos[name]['holdout_claim'])
    cfg=load_config(ROOT/'configs/default.yaml')
    cfg.llm.max_output_tokens=4096;cfg.llm.timeout=180;cfg.llm.max_calls=4000;cfg.llm.max_total_tokens=20000000
    cfg.evaluation.max_format_retries=0
    write_json(OUT/'config.json',cfg.model_dump())
    write_json(OUT/'protocol.json',{'seed':42,'api_workers':64,'local_workers':12,
        'train_count':700,'dev_count':350,'test_count':500,'max_distillation_candidates':12,'max_source_traces_per_skill':6,
        'max_dev_pairs_per_skill':60,'model':cfg.llm.model,'temperature':0,'max_output_tokens':4096,
        'generation_attempts_per_question':1,'gold_reflection':False,'freeze_both_libraries':True,
        'flowevo_implementation':'native CodeSkillLibrary + build_goldfree_math_prompt exported by original repo, common HTTP transport',
        'bot_mode':'subject_strategy_costaware','grader':'math-verify==0.8.0 + conservative exact match',
        'selection_counts':{n:dict(Counter(t.subject for t in ts)) for n,ts in [('train',train),('dev',dev),('test',test)]},
        'excluded_additional_near_duplicates':removed,'not_standard_math500':True,
        'no_test_based_tuning':True,'cost_reporting':'solve-only and full build+solve; common history cost charged equally'})
    print('Frozen selection:',{n:len(ts) for n,ts in [('train',train),('dev',dev),('test',test)]},'additional exclusions',len(removed))

if __name__=='__main__':main()
