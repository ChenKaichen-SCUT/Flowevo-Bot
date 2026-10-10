"""One independent call per public task; labels never enter this process."""
from common import *
from native import runner, task_for
import concurrent.futures as cf
import gzip, threading, time, random
import requests

def request_for(public, config):
    assert set(public) == {'task_id', 'problem', 'subject', 'level', 'split', 'official_row_index'}
    assert config['max_tokens'] == runner._GEN_SETTINGS.max_output_tokens == 2048
    assert config['gold_reflection'] is False and config['condition_config']['retry'] is False
    return dict(model=config['model'], messages=[
        {'role': 'system', 'content': 'You are an expert programmer and mathematician.'},
        {'role': 'user', 'content': runner.build_prompt(task_for(public), cot=True)}],
        temperature=runner._GEN_SETTINGS.temperature, max_tokens=config['max_tokens'],
        stream=True, stream_options={'include_usage': True})

def consume(response, path):
    result, reasoning, content = {}, [], []
    usage = finish = None
    done = False
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        for line in response.iter_lines(decode_unicode=True):
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            stream.write((line or '') + '\n')
            if not line or not line.startswith('data:'):
                continue
            payload = line[5:].strip()
            if payload == '[DONE]':
                done = True
                break
            part = json.loads(payload)
            if 'error' in part:
                raise RuntimeError('Provider stream error')
            for key in ('id', 'model', 'created', 'system_fingerprint'):
                if key in part:
                    result[key] = part[key]
            if part.get('usage'):
                usage = part['usage']
            for choice in part.get('choices', []):
                if choice.get('finish_reason') is not None:
                    finish = choice['finish_reason']
                delta = choice.get('delta', {})
                reasoning.append(delta.get('reasoning_content') or '')
                content.append(delta.get('content') or '')
    if not done or usage is None or finish is None:
        raise RuntimeError('Incomplete response or missing usage')
    result.update(object='chat.completion', usage=usage, choices=[{
        'index': 0, 'finish_reason': finish,
        'message': {'role': 'assistant', 'content': ''.join(content),
                    'reasoning_content': ''.join(reasoning)}}])
    return result

class Generator:
    def __init__(self, config, out=OUT, transport=None):
        self.config, self.out, self.transport = config, Path(out), transport
        self.key = (ROOT / 'miyao.txt').read_text().strip() if transport is None else None
        for name in ('raw', 'attempts'):
            (self.out / name).mkdir(parents=True, exist_ok=True)
        for pending in (self.out / 'attempts').glob('*.pending.json'):
            final = pending.with_name(pending.name.replace('.pending.json', '.json'))
            if not final.exists():
                save(final, dict(read(pending), status='unknown_after_crash', usage_known=False))
            pending.unlink()
        previous = [read(p) for p in (self.out / 'attempts').glob('*.json')]
        self.calls = len(previous)
        self.tokens = sum(a.get('total_tokens', 0) for a in previous if a['usage_known'])
        self.unknown = sum(a['reserved_tokens'] for a in previous if not a['usage_known'])
        self.active = self.peak = self.reserved = 0
        self.lock = threading.Lock()

    def call(self, public):
        req = request_for(public, self.config)
        tid = public['task_id']
        path = self.out / 'raw' / (tid + '.json')
        if path.exists():
            record = read(path)
            assert record['request'] == req and record['response_hash'] == digest(record['response'])
            return record
        bound = sum(len(m['content'].encode()) for m in req['messages']) + 512 + req['max_tokens']
        prior = list((self.out / 'attempts').glob(tid + '__a*.json'))
        for number in range(len(prior) + 1, self.config['max_transport_attempts_per_task'] + 1):
            with self.lock:
                if self.calls >= self.config['max_http_attempts'] or self.tokens + self.unknown + self.reserved + bound > self.config['max_total_tokens']:
                    raise RuntimeError('Frozen call/token budget reached')
                self.calls += 1
                self.active += 1
                self.peak = max(self.peak, self.active)
                self.reserved += bound
            aid = tid + '__a' + str(number)
            pending = self.out / 'attempts' / (aid + '.pending.json')
            ap = self.out / 'attempts' / (aid + '.json')
            attempt = dict(attempt_id=aid, task_id=tid, reserved_tokens=bound,
                request_hash=digest(req), started_at=now(),
                trigger='scheduled' if number == 1 else 'transport_failure_only')
            save(pending, dict(attempt, request=req))
            started = time.perf_counter()
            data = None
            try:
                if self.transport:
                    data = self.transport(req)
                else:
                    with requests.post(self.config['endpoint'], json=req,
                        headers={'Authorization': 'Bearer ' + self.key}, stream=True,
                        timeout=(30, 900)) as response:
                        attempt['http_status'] = response.status_code
                        if response.status_code != 200:
                            raise RuntimeError('HTTP rejection')
                        response.encoding = 'utf-8'
                        data = consume(response, self.out / 'raw' / (aid + '.sse.gz'))
                usage = data['usage']
                actual = usage['total_tokens']
                assert actual == usage['prompt_tokens'] + usage['completion_tokens']
                reason = usage.get('completion_tokens_details', {}).get('reasoning_tokens')
                record = dict(task_id=tid, request=req, request_hash=digest(req), response=data,
                    response_hash=digest(data), input_tokens=usage['prompt_tokens'],
                    output_tokens=usage['completion_tokens'], total_tokens=actual,
                    reasoning_tokens=reason,
                    final_content_tokens=usage['completion_tokens'] - reason if reason is not None else None,
                    finish_reason=data['choices'][0]['finish_reason'],
                    model_version=data.get('model'), backend_revision=data.get('system_fingerprint'),
                    max_tokens=req['max_tokens'], gold_reflection=False, skill_injected=False,
                    actual_attempt_id=aid, started_at=attempt['started_at'], finished_at=now(),
                    latency_seconds=time.perf_counter() - started, raw_stream='raw/' + aid + '.sse.gz')
                save(path, record)
                save(ap, dict(attempt, status='completed', usage_known=True, **{
                    k: record[k] for k in ('total_tokens', 'input_tokens', 'output_tokens', 'response_hash', 'finished_at')}))
                pending.unlink()
                with self.lock:
                    self.tokens += actual
                    self.active -= 1
                    self.reserved -= bound
                print(json.dumps(dict(task_id=tid, finish=record['finish_reason'], tokens=actual)), flush=True)
                return record
            except Exception as error:
                usage = (data or {}).get('usage') or {}
                known = isinstance(usage.get('total_tokens'), int)
                save(ap, dict(attempt, status='failed', usage_known=known,
                    total_tokens=usage.get('total_tokens', 0), error_type=type(error).__name__, finished_at=now()))
                if pending.exists():
                    pending.unlink()
                with self.lock:
                    self.tokens += usage.get('total_tokens', 0) if known else 0
                    self.unknown += 0 if known else bound
                    self.active -= 1
                    self.reserved -= bound
                print(json.dumps(dict(task_id=tid, attempt=number, error_type=type(error).__name__)), flush=True)
                if number < self.config['max_transport_attempts_per_task']:
                    time.sleep(2)
        raise RuntimeError('Transport recovery exhausted for ' + tid)

def main():
    for path, expected in read(OUT / 'evidence/pre_api_freeze.json')['files'].items():
        assert sha(ROOT / path) == expected, path
    seal_path = OUT / 'GENERATION_SEALED.json'
    if seal_path.exists():
        for path, expected in read(seal_path)['files'].items():
            assert sha(OUT / path) == expected
        print('All 605 jobs complete; zero new API calls.')
        return
    config = read(OUT / 'config.json')
    tasks = jl(PREVIOUS / 'data/public_tasks.jsonl')
    assert len(tasks) == len({t['task_id'] for t in tasks}) == 605
    random.Random(config['schedule_seed']).shuffle(tasks)
    generator = Generator(config)
    results, errors = [], []
    with cf.ThreadPoolExecutor(max_workers=config['api_workers']) as pool:
        futures = {pool.submit(generator.call, task): task['task_id'] for task in tasks}
        for future in cf.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                errors.append(dict(task_id=futures[future], error_type=type(error).__name__))
    save('generation_progress.json', dict(at=now(), completed=len(results), expected=605,
        errors=errors, http_attempts=generator.calls, tokens=generator.tokens,
        unknown_token_bound=generator.unknown, peak_api_concurrency=generator.peak))
    if errors:
        raise RuntimeError('Incomplete run; inspect progress. Finished jobs are immutable.')
    save(seal_path, dict(sealed_at=now(), n=len(results), labels_read=False,
        peak_api_concurrency=generator.peak,
        files={'raw/' + r['task_id'] + '.json': sha(OUT / 'raw' / (r['task_id'] + '.json')) for r in results}))
    print('SEALED 605', flush=True)

if __name__ == '__main__':
    main()
