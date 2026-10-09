"""Opt-in HTTP client with a durable per-request ledger and a separate mock transport."""
import os
import time
from pathlib import Path
from dataclasses import dataclass
from flowevo_bot.common import digest, write_json, read_json
from flowevo_bot.schemas import TokenCall
from flowevo_bot.token_accounting import TokenLedger, estimate_tokens

SYSTEM = 'You are an expert programmer and mathematician.'


@dataclass(frozen=True)
class Reply:
    text: str
    call: TokenCall


class LLMClient:
    def __init__(self, config, ledger=None, *, allow_paid=False, mock_handler=None):
        self.config = config
        self.ledger = ledger if ledger is not None else TokenLedger()
        self.mock_handler = mock_handler
        self.simulated = mock_handler is not None
        self.allow_paid = allow_paid or config.allow_paid_api
        self.prompts = []

    def complete(self, prompt, *, task_id, purpose, route='base', skill_ids=(), system=SYSTEM):
        request = {'model': self.config.model, 'messages': [
            {'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}],
            'temperature': self.config.temperature, 'max_tokens': self.config.max_output_tokens}
        call_id = digest({'request': request, 'base_url': self.config.base_url,
                          'task_id': task_id, 'purpose': purpose, 'route': route,
                          'skill_ids': list(skill_ids), 'simulated': self.simulated})
        if call_id in self.ledger.responses:
            if call_id in self.ledger.failures:
                raise RuntimeError(self.ledger.failures[call_id])
            return Reply(self.ledger.responses[call_id], next(c for c in self.ledger.calls if c.call_id == call_id))
        if not self.simulated and not self.allow_paid:
            raise PermissionError('Paid API disabled: explicit --allow-paid-api is required')
        if len(self.ledger.calls) >= self.config.max_calls:
            raise RuntimeError('Declared model call budget exhausted')
        estimated_input = estimate_tokens(system + '\n' + prompt)
        if self.ledger.totals()['total_tokens'] + estimated_input + self.config.max_output_tokens > self.config.max_total_tokens:
            raise RuntimeError('Declared token budget insufficient for this request reservation')
        pending = self.ledger.path.with_suffix('.pending.json') if self.ledger.path else None
        if pending and pending.exists() and not self.simulated:
            raise RuntimeError('Unresolved request journal: provider billing/completion is uncertain; reconcile before resuming')
        if pending:
            write_json(pending, {'call_id': call_id, 'task_id': task_id, 'request_hash': digest(request)})
        self.prompts.append(prompt)
        start = time.monotonic()
        if self.simulated:
            result = self.mock_handler(prompt, purpose)
            if isinstance(result, str):
                result = {'text': result}
        else:
            import requests
            key = os.environ.get(self.config.api_key_env, '')
            if not key:
                if pending: pending.unlink(missing_ok=True)
                raise ValueError('API key environment variable is unset')
            try:
                response = requests.post(self.config.base_url.rstrip('/') + '/chat/completions',
                    headers={'Authorization': 'Bearer ' + key}, json=request, timeout=self.config.timeout)
                if not response.ok:
                    raise RuntimeError(f'Provider HTTP {response.status_code}; response body withheld')
                data = response.json()
                result = {'text': data['choices'][0]['message'].get('content') or '',
                          'usage': data.get('usage'), 'finish_reason': data['choices'][0].get('finish_reason')}
                if self.ledger.path:
                    # Preserve provider usage (including cache/reasoning fields)
                    # and exact requested settings without headers or secrets.
                    write_json(self.ledger.path.parent / (self.ledger.path.stem + '.provider') / (call_id + '.json'),
                        {'call_id':call_id,'request':request,'provider_model':data.get('model'),
                         'response_id':data.get('id'),'usage':data.get('usage'),
                         'finish_reason':result['finish_reason']})
            except Exception as exc:
                # Do not repeat an uncertain paid call automatically or disclose response bodies/secrets.
                raise RuntimeError('Model request failed; inspect the pending journal before retrying') from None
        text = result['text']
        usage = result.get('usage') or {}
        estimated = any(usage.get(k) is None for k in ('prompt_tokens', 'completion_tokens'))
        pin = usage.get('prompt_tokens')
        pout = usage.get('completion_tokens')
        pin = estimated_input if pin is None else int(pin)
        pout = estimate_tokens(text) if pout is None else int(pout)
        record = TokenCall(call_id=call_id, task_id=task_id, purpose=purpose, model=self.config.model,
            route=route, skill_ids=list(skill_ids), prompt_tokens=pin, completion_tokens=pout,
            total_tokens=pin + pout, latency=time.monotonic()-start,
            estimated=estimated, estimation_method='missing fields estimated by utf8_bytes/3 (includes system)' if estimated else None,
            simulated=self.simulated, prompt_hash=digest(request), response_hash=digest(text))
        self.ledger.append(record, text, prompt=prompt)
        if pending: pending.unlink(missing_ok=True)
        if result.get('finish_reason') == 'length':
            error='Response truncated; usage recorded, do not treat as a solution'
            self.ledger.failures[call_id]=error
            self.ledger.save()
            raise RuntimeError(error)
        return Reply(text, record)
