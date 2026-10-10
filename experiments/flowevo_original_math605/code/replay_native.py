"""Run original FlowEvo over sealed completions; no additional API calls.

The upstream math retrieval always returns none for the 605 unique task IDs, so
prefetching the initial independent calls leaves the sequential runner unchanged.
Only condition retry=False overrides upstream ours, retaining the user's gold ban.
"""
from common import *
from native import runner, task_for, score
from runtime.llm_client import LLMResponse, LLMClientError
from collections import Counter
import csv

class ReplayClient:
    def __init__(self, publics, records):
        self.by_prompt = {runner.build_prompt(task_for(p), cot=True): records[p['task_id']] for p in publics}
        assert len(self.by_prompt) == len(publics)
        self.calls = 0

    def generate(self, *, instructions, input_text, settings):
        record = self.by_prompt[input_text]
        req = record['request']
        assert req['messages'] == [{'role':'system','content':instructions}, {'role':'user','content':input_text}]
        assert req['max_tokens'] == settings.max_output_tokens
        assert req['temperature'] == settings.temperature
        self.calls += 1
        content = (record['response']['choices'][0]['message'].get('content') or '').strip()
        # Exact upstream LLMClient behavior. Usage still exists in our transport
        # ledger, even though upstream drops it on empty final content.
        if not content:
            raise LLMClientError('OpenRouter returned empty content.')
        return LLMResponse(text=content, provider='openrouter', model=req['model'],
            prompt_tokens=record['input_tokens'], completion_tokens=record['output_tokens'],
            total_tokens=record['total_tokens'], latency_ms=record['latency_seconds'] * 1000)

def summarize(rows):
    n = len(rows)
    correct = sum(r['passed'] for r in rows)
    return dict(n=n, correct=correct, incorrect=n-correct, accuracy=correct/n,
        **{k: sum(r[k] for r in rows) for k in ('input_tokens','output_tokens','reasoning_tokens','final_content_tokens','total_tokens','native_reported_tokens')},
        mean_tokens=sum(r['total_tokens'] for r in rows)/n,
        empty_final_content=sum(r['empty_final_content'] for r in rows),
        finish_reasons=dict(Counter(r['finish_reason'] for r in rows)))

def main():
    seal = read(OUT / 'GENERATION_SEALED.json')
    assert seal['n'] == 605
    for path, expected in seal['files'].items():
        assert sha(OUT/path) == expected
    public = jl(PREVIOUS / 'data/public_tasks.jsonl')
    labels = {r['task_id']: r['reference_raw'] for r in jl(PREVIOUS / 'data/offline_labels.jsonl')}
    records = {p['task_id']: read(OUT / 'raw' / (p['task_id'] + '.json')) for p in public}
    tasks = [task_for(p, labels[p['task_id']]) for p in public]
    config = read(OUT / 'config.json')
    expected = dict(runner.CONDITIONS['ours'], retry=False)
    assert config['condition_config'] == expected
    client = ReplayClient(public, records)
    native_dir = OUT / 'native_runner'
    episodes = runner.run_condition('math', 'ours', expected, client, tasks, native_dir)
    assert len(episodes) == 605
    runner.generate_report({'math': {'ours': episodes}}, native_dir)
    rows = []
    for p, episode in zip(public, episodes):
        tid = p['task_id']
        assert tid == episode['task_id'] and episode['retries'] == 0
        r = records[tid]
        content = r['response']['choices'][0]['message'].get('content') or ''
        scored = score(p, labels[tid], content)
        assert episode['passed'] == scored['passed']
        rows.append(dict(task_id=tid, split=p['split'], subject=p['subject'], level=p['level'],
            **scored, **{k:r[k] for k in ('input_tokens','output_tokens','reasoning_tokens','final_content_tokens','total_tokens','finish_reason','model_version','backend_revision','response_hash','request_hash')},
            native_reported_tokens=episode['tokens'], native_runner_feedback=episode['feedback'],
            empty_final_content=not content.strip(), response_path='raw/'+tid+'.json'))
    lines('results.jsonl', rows)
    with (OUT/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines('api_calls.jsonl', [records[p['task_id']] for p in public])
    groups={group:summarize([r for r in rows if group=='all' or r['split']==group]) for group in ('all','validation','test')}
    subjects={subject:summarize([r for r in rows if r['subject']==subject]) for subject in sorted({r['subject'] for r in rows})}
    attempts=[read(p) for p in (OUT/'attempts').glob('*.json')]
    known=sum(a.get('total_tokens',0) for a in attempts if a['usage_known'])
    save('summary.json',dict(groups=groups,subjects=subjects,model=config['model'],max_tokens=2048,
        condition='upstream ours, retry=False (gold reflection disabled)',
        http_attempts=len(attempts),known_billed_tokens=known,
        unknown_usage_attempts=sum(not a['usage_known'] for a in attempts),
        native_token_undercount=groups['all']['total_tokens']-groups['all']['native_reported_tokens'],
        score_semantics='Unmodified upstream loader extractor + runner extractor + normalization + verify; no V3 or manual corrections',
        peak_api_concurrency=seal['peak_api_concurrency'], completed_at=now()))
    print(json.dumps(groups,ensure_ascii=False))

if __name__=='__main__':
    main()
