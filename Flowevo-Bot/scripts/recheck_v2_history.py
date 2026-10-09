"""Offline, immutable historical-score review. Never used as solver feedback."""
import csv
import concurrent.futures as cf
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
from flowevo_bot.common import read_json,write_json,jsonl
from flowevo_bot.schemas import Submission
from flowevo_bot.v2.evaluator import grade

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'experiments/math500_goldfree_20261009'
OUT=ROOT/'experiments/flowevo_bot_v2_math500'

def main():
    if hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:12])
    submissions=[]
    for method,split in [('train','train'),('flowevo','test'),('flowevo_bot','test')]:
        scores={r['task_id']:r for r in read_json(OLD/method/'rows.json')}
        for s in read_json(OLD/method/'checkpoint.json')['submissions']:
            Submission.model_validate(s).assert_frozen()
            r=scores[s['task_id']]
            submissions.append(dict(s,method=method,source_split=split,original_correct=r['final_correct'],truncated=r['truncated']))
    for skill in read_json(OLD/'real_bank.json')['skills']:
        for pair in skill['validation_stats']['pairwise']:
            for method,field in [('base','base'),(skill['skill_id'],'skill')]:
                path=OLD/'validation_v2'/method/(pair['task_id']+'.submission.json')
                s=read_json(path);Submission.model_validate(s).assert_frozen()
                calls=read_json(path.with_name(pair['task_id']+'.calls.json'))
                submissions.append(dict(s,method='dev_'+method,source_split='dev',original_correct=pair[field+'_correct'],truncated=bool(calls.get('failures'))))
    # No labels opened until every historical submission has passed its seal.
    labels={};questions={}
    for split in ['train','dev','test']:
        labels.update({r['task_id']:r['gold_answer'] for r in jsonl(OLD/'manifests'/f'{split}.labels.jsonl')})
        questions.update({r['task_id']:r['problem'] for r in jsonl(OLD/'manifests'/f'{split}.problems.jsonl')})
    items=[{**s,'gold_answer':labels[s['task_id']],'question':questions[s['task_id']]} for s in submissions]
    rows=[]
    with cf.ProcessPoolExecutor(max_workers=12,mp_context=mp.get_context('spawn')) as pool:
        for idx,(s,result) in enumerate(zip(items,pool.map(grade,items,chunksize=5))):
            rows.append({**result,'method':s['method'],'source_split':s['source_split'],'original_answer':s['final_answer'],
                         'question':s['question'],'gold_answer':s['gold_answer'],'solution':s['solution'],'original_seal':s['seal']})
            if (idx+1)%200==0:print('rechecked',idx+1,flush=True)
    write_json(OUT/'data/historical_rechecked.json',rows)
    different=[r for r in rows if r['original_correct'] is not r['rechecked_correct']]
    with (OUT/'data/scoring_disagreements.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=sorted({k for r in rows for k in r}));w.writeheader();w.writerows(different)
    summary={method:{'n':len(x:=[r for r in rows if r['method']==method]),'original_correct':sum(r['original_correct'] for r in x),
                    'rechecked_correct':sum(r['rechecked_correct'] is True for r in x),'unknown':sum(r['rechecked_correct'] is None for r in x)} for method in sorted({r['method'] for r in rows})}
    write_json(OUT/'data/scoring_summary.json',summary)
    write_json(OUT/'evidence/evaluator_frozen.json',{'sha256':hashlib.sha256((ROOT/'src/flowevo_bot/v2/evaluator.py').read_bytes()).hexdigest(),'rechecked':len(rows),'changed':len(different),'purpose':'post-hoc historical audit, not new test performance or training feedback'})
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
