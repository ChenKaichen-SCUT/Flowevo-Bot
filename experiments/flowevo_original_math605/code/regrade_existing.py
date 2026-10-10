"""Separate historical 16384-token regrade; this never submits an API request."""
from common import *
from native import score, assert_local_extractors_unchanged
from collections import Counter

def main():
    public = {row['task_id']: row for row in jl(PREVIOUS / 'data/public_tasks.jsonl')}
    labels = {row['task_id']: row['reference_raw'] for row in jl(PREVIOUS / 'data/offline_labels.jsonl')}
    rows = []
    for previous in jl(PREVIOUS / 'baseline_results.jsonl'):
        tid = previous['task_id']
        path = PREVIOUS / previous['response_path']
        raw = read(path)
        assert raw['response_hash'] == digest(raw['response'])
        assert raw['max_tokens'] == 16384 and raw['candidate'] == 1
        text = raw['response']['choices'][0]['message'].get('content') or ''
        rows.append(dict(task_id=tid, split=public[tid]['split'], subject=public[tid]['subject'],
                         **score(public[tid], labels[tid], text),
                         input_tokens=raw['input_tokens'], output_tokens=raw['output_tokens'],
                         total_tokens=raw['total_tokens'], reasoning_tokens=raw['reasoning_tokens'],
                         finish_reason=raw['finish_reason'], response_path=str(path.relative_to(ROOT)),
                         response_hash=raw['response_hash'], max_tokens=16384,
                         historical_v3_status=previous['v3_status'],
                         historical_mathematical_correct=previous['mathematical_correct']))
    assert len(rows) == len({row['task_id'] for row in rows}) == 605
    groups = {}
    for group in ('all', 'validation', 'test'):
        selected = [row for row in rows if group == 'all' or row['split'] == group]
        groups[group] = dict(n=len(selected), correct=sum(row['passed'] for row in selected),
            **{k: sum(row[k] for row in selected) for k in ('input_tokens','output_tokens','reasoning_tokens','total_tokens')},
            finish_reasons=dict(Counter(row['finish_reason'] for row in selected)))
    lines('historical_16384/results.jsonl', rows)
    save('historical_16384/summary.json', dict(groups=groups, new_api_calls=0, new_tokens=0,
        mode='Historical outputs regraded with unmodified upstream extractor and verifier; not a new solve run',
        extractors_unchanged=assert_local_extractors_unchanged()))
    print(json.dumps(groups, ensure_ascii=False))

if __name__ == '__main__':
    main()
