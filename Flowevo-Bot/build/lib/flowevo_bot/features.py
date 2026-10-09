"""Cheap, question-only features; no answer or solution argument exists."""
import re
from .taxonomy import detect_subject

PATTERNS = {
    'prime': r'\bprime\b|素数', 'modular': r'modulo|remainder|congruen|\\pmod|余数',
    'divisibility': r'divisi|divid|整除', 'gcd_lcm': r'\bgcd\b|\blcm\b|greatest common',
    'polynomial': r'polynomial|多项式', 'quadratic': r'quadratic|\^\{?2|平方',
    'equation': r'equation|solve.*=|方程', 'factorization': r'factor|因式',
    'rational': r'\\frac|fraction|rational', 'triangle': r'triangle|三角形',
    'circle': r'circle|圆', 'area': r'area|面积', 'counting': r'ways|choose|combination|排列',
    'probability': r'probability|概率', 'trigonometric': r'\\sin|\\cos|trigonometric',
    'unit_rate': r'per |each |每', 'ratio': r'ratio|比例', 'composition': r'composition|f\(f\(',
    'integer': r'integer|整数', 'positive': r'positive|正数', 'nonzero': r'nonzero|non-zero|非零',
}


def extract_features(task):
    text = task.problem.lower()
    return frozenset(k for k, p in PATTERNS.items() if re.search(p, text))


def matches(skill, features):
    known = set(PATTERNS)
    requested = set(skill.trigger_features + skill.preconditions + skill.negative_triggers)
    if not requested <= known:
        return False
    return (bool(set(skill.trigger_features) & features)
            and set(skill.preconditions) <= features
            and not (set(skill.negative_triggers) & features))


def normalize_problem(text, structure=False):
    text = re.sub(r'\s+', ' ', text.lower()).strip()
    return re.sub(r'\d+(?:\.\d+)?', '#', text) if structure else text


def near_duplicate(a, b):
    from difflib import SequenceMatcher
    x, y = normalize_problem(a, True), normalize_problem(b, True)
    return x == y or SequenceMatcher(None, x, y, autojunk=False).ratio() >= .9


def duplicate_keys(text):
    normalized = normalize_problem(text, True)
    return ('prefix:' + normalized[:24], 'suffix:' + normalized[-24:])
