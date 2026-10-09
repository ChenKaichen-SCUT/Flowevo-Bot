"""Reproducible stratified train-build/dev split and explicit test contamination registry."""
import json
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path
from .common import digest,write_json,jsonl
from .schemas import ProblemView,EvaluationRecord
from .taxonomy import normalize_subject
from .evaluator import extract_answer
from .features import normalize_problem, near_duplicate, duplicate_keys


def write_manifest(directory,name,split,problems,labels,**metadata):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if (directory/(name+'.json')).exists():raise FileExistsError('Manifest already exists')
    for suffix,rows in [('problems',problems),('labels',labels)]:
        with (directory/f'{name}.{suffix}.jsonl').open('x',encoding='utf-8') as f:
            for row in rows:f.write(json.dumps(row.model_dump(mode='json'),ensure_ascii=False)+'\n')
    manifest={'schema_version':'1.0','split':split,'count':len(problems),
        'problems_file':f'{name}.problems.jsonl','evaluation_file':f'{name}.labels.jsonl',
        'problems_hash':digest([p.model_dump(mode='json') for p in problems]),
        'labels_hash':digest([p.model_dump(mode='json') for p in labels]),**metadata}
    write_json(directory/(name+'.json'),manifest)
    return directory/(name+'.json')


def prepare_math(source,output,seed=42,dev_fraction=.2,excluded_algebra=500):
    if not 0<dev_fraction<1:raise ValueError('dev_fraction must be between 0 and 1')
    source=Path(source);output=Path(output)
    groups=defaultdict(list)
    def convert(rows,split):
        counters=defaultdict(int);result=[]
        for row in rows:
            subject=normalize_subject(row['type'])
            if subject is None:raise ValueError('Unknown MATH type')
            index=counters[subject];counters[subject]+=1
            tid=f'math_{split}_{subject}_{index}'
            answer=extract_answer(row['solution'])
            if answer is None:raise ValueError(f'Missing boxed answer for {tid}')
            p=ProblemView(task_id=tid,problem=row['problem'],subject=subject,level=row.get('level',''),public_metadata={'type':row['type'],'benchmark':'math'})
            result.append((p,EvaluationRecord(task_id=tid,gold_answer=answer,reference_solution=row['solution']),index))
        return result
    train=convert(jsonl(source/'train.jsonl'),'train')
    # Group exact normalized and obvious near duplicates globally BEFORE stratification.
    # Cross-subject or different-level duplicates must not cross build/dev either.
    parents=list(range(len(train)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    exact={};blocks=defaultdict(list)
    for i,(p,e,_) in enumerate(train):
        normalized=normalize_problem(p.problem,True)
        if normalized in exact:
            parents[find(i)]=find(exact[normalized])
        exact[normalized]=i
        candidates=set(j for key in duplicate_keys(p.problem) for j in blocks[key])
        for j in candidates:
            if find(i)!=find(j) and near_duplicate(p.problem,train[j][0].problem):
                parents[find(i)]=find(j)
        for key in duplicate_keys(p.problem):blocks[key].append(i)
    for i,(p,e,_) in enumerate(train):groups[find(i)].append((p,e))
    strata=defaultdict(list)
    for group in groups.values():
        p=group[0][0];strata[(p.subject,p.level)].append(group)
    rng=random.Random(seed);build=[];dev=[]
    for key,group_list in sorted(strata.items()):
        rng.shuffle(group_list)
        n=max(1,round(len(group_list)*dev_fraction)) if len(group_list)>1 else 0
        dev.extend(pair for group in group_list[:n] for pair in group)
        build.extend(pair for group in group_list[n:] for pair in group)
    # No assertion that formal test is previously unseen; conservative exclusions are recorded.
    test=[];excluded=[]
    for p,e,index in convert(jsonl(source/'test.jsonl'),'test'):
        if p.subject=='algebra' and index<excluded_algebra:excluded.append(p.task_id)
        else:test.append((p,e))
    meta={'seed':seed,'source':'EleutherAI/hendrycks_math','source_local_sha256':{
        n:__import__('hashlib').sha256((source/n).read_bytes()).hexdigest() for n in ['train.jsonl','test.jsonl']},
        'split_method':'subject/level stratification after global duplicate components; digit-masked exact and prefix/suffix blocked SequenceMatcher >=0.9',
        'holdout_claim':'not pristine; known/potential algebra first 500 test tasks excluded; other exposure unknown'}
    for name,split,pairs in [('train','train-build',build),('dev','train-dev',dev),('test','test',test)]:
        write_manifest(output,name,split,[p for p,e in pairs],[e for p,e in pairs],**meta)
    write_json(output/'excluded_test_ids.json',{'reason':'previous debugging exposure/potential exposure; conservative registry',
        'ids':excluded,'not_math500':True,'source':'user instructions plus local prior smoke audit'})
    return {'train-build':len(build),'train-dev':len(dev),'test':len(test),'excluded':len(excluded)}
