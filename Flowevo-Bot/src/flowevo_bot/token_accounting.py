"""Every call is explicit. Estimates are conservative UTF-8 byte counts / 3."""
import math
from pathlib import Path
from .common import read_json, write_json
from .schemas import TokenCall


def estimate_tokens(text):
    return max(1, math.ceil(len(text.encode('utf-8')) / 3)) if text else 0


class TokenLedger:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        data = read_json(self.path) if self.path and self.path.exists() else {'calls': [], 'responses': {}}
        self.calls = [TokenCall.model_validate(c) for c in data['calls']]
        self.responses = data['responses']
        self.failures = data.get('failures', {})
        self.prompts = data.get('prompts', {})
        if len({c.call_id for c in self.calls}) != len(self.calls):
            raise ValueError('Duplicate ledger call IDs')

    def append(self, record, text, prompt=None):
        if record.call_id in self.responses:
            raise ValueError('Call already accounted for')
        self.calls.append(record)
        self.responses[record.call_id] = text
        if prompt is not None:
            self.prompts[record.call_id] = prompt
        self.save()

    def save(self):
        if self.path:
            write_json(self.path, {'calls': [c.model_dump(mode='json') for c in self.calls], 'responses': self.responses, 'failures':self.failures, 'prompts':self.prompts})

    def for_task(self, task_id):
        return [c for c in self.calls if c.task_id == task_id]

    def totals(self, calls=None):
        calls = self.calls if calls is None else calls
        return {'prompt_tokens': sum(c.prompt_tokens for c in calls),
                'completion_tokens': sum(c.completion_tokens for c in calls),
                'total_tokens': sum(c.total_tokens for c in calls),
                'calls': len(calls), 'estimated_calls': sum(c.estimated for c in calls),
                'simulated_calls': sum(c.simulated for c in calls)}

    def by_purpose(self):
        return {p: self.totals([c for c in self.calls if c.purpose == p]) for p in sorted({c.purpose for c in self.calls})}


def amortized_cost(build_cost, validation_cost, maintenance_cost, solve_cost, paired_base_cost=None):
    overhead = build_cost + validation_cost + maintenance_cost
    return {'build_cost': build_cost, 'validation_cost': validation_cost,
            'maintenance_cost': maintenance_cost, 'solve_only_cost': solve_cost,
            'amortized_end_to_end_cost': overhead + solve_cost,
            'net_tokens_saved': None if paired_base_cost is None else paired_base_cost - solve_cost - overhead}


def break_even_uses(overhead, saving_per_use):
    return math.ceil(overhead / saving_per_use) if saving_per_use > 0 else None
