"""Scoring after frozen submission only. No scorer is passed to the solver."""
import re
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from .common import jsonl, digest
from .schemas import EvaluationRecord


def extract_answer(text):
    # Balanced braces avoid the upstream nested-\\frac truncation bug.
    starts = [m.end() for m in re.finditer(r'\\boxed\{', text)]
    for start in reversed(starts):
        depth = 1
        for i in range(start, len(text)):
            depth += (text[i] == '{') - (text[i] == '}')
            if depth == 0:
                return text[start:i].strip()
    unbraced = re.search(r'\\boxed\s+(-?\d+(?:\.\d+)?)', text)
    if unbraced:
        return unbraced.group(1)
    match = re.search(r'(?:The answer is|Final answer\s*:)\s*(.+)', text, re.I)
    return match.group(1).strip().rstrip('.') if match else None


def normalize(answer):
    if answer is None:
        return None
    a = answer.strip().strip('$').replace('\\left', '').replace('\\right', '').replace('\\dfrac', '\\frac')
    a = re.sub(r'\\(?:,|!|;|quad)', '', a)
    if re.fullmatch(r'-?\d{1,3}(,\d{3})+(\.\d+)?', a):
        a = a.replace(',', '')
    m = re.fullmatch(r'\\frac\{(-?\d+)\}\{(-?\d+)\}', a)
    try:
        if m: return str(Fraction(int(m[1]), int(m[2])))
        if re.fullmatch(r'-?\d+\s*/\s*-?\d+', a): return str(Fraction(a.replace(' ', '')))
        return str(Fraction(Decimal(a)))
    except (ValueError, ZeroDivisionError, InvalidOperation):
        # Conservative textual match, not an unbounded symbolic equivalence claim.
        return re.sub(r'\s+', '', a)


def verify(prediction, evaluation):
    passed = normalize(prediction) == normalize(evaluation.gold_answer) and prediction is not None
    return passed, 'correct' if passed else 'incorrect'  # never emit gold or reference


class Evaluator:
    def __init__(self, labels_path, expected_hash=None):
        self.path = Path(labels_path)
        self.read_count = 0
        self.expected_hash = expected_hash

    def score(self, submissions):
        for submission in submissions:
            submission.assert_frozen()
        # The label file is not opened until ALL submitted work is sealed.
        labels = [EvaluationRecord.model_validate(r) for r in jsonl(self.path)]
        self.read_count += 1
        if self.expected_hash and digest([r.model_dump(mode="json") for r in labels]) != self.expected_hash:
            raise ValueError("Evaluation manifest hash mismatch")
        index = {r.task_id: r for r in labels}
        if len(index) != len(labels):
            raise ValueError('Duplicate evaluation IDs')
        results = []
        for s in submissions:
            if s.task_id not in index:
                raise ValueError('Missing label for sealed submission')
            e = index[s.task_id]
            first, _ = verify(s.first_answer, e)
            final, message = verify(s.final_answer, e)
            results.append({'task_id': s.task_id, 'first_pass_correct': first,
                            'final_correct': final, 'feedback': message})
        return results
