"""Conservative post-submission grading; never called by solver or routing code.

Unknown is distinct from false. Exact equality is trusted only after structural
parsing, not after arbitrary prose stripping. Math-Verify's fallback strings are
explicitly excluded. All symbolic work runs in bounded process workers.
"""
import logging
import re
from pathlib import Path
from ..common import digest, jsonl


def balanced(text, start, left='{', right='}'):
    depth = 1
    for i in range(start, len(text)):
        depth += (text[i] == left) - (text[i] == right)
        if depth == 0:
            return text[start:i], i + 1
    return None, len(text)


def extract(text):
    candidates = []
    for m in re.finditer(r'\\(?:boxed|fbox)\s*\{', text):
        value, end = balanced(text, m.end())
        candidates.append((m.start(), value, 'boxed' if value is not None else 'incomplete_box'))
    for m in re.finditer(r'(?:The answer is|Final answer\s*:)\s*([^\n]*)', text, re.I):
        value = m.group(1).strip().strip('*').strip().removesuffix('.')
        # A boxed answer inside this same line is handled by the later marker.
        candidates.append((m.start(), value or None, 'final_marker' if value else 'incomplete_answer'))
    if not candidates:
        return None, 'missing_final_answer'
    _, value, status = max(candidates, key=lambda x: x[0])
    return value, status


def presentation(value):
    s = value.strip().strip('$').strip().strip('*').strip()
    s = s.replace('\\left', '').replace('\\right', '').replace('\\dfrac', '\\frac').replace('\\tfrac', '\\frac')
    for left, right in [('\\(', '\\)'), ('\\[', '\\]')]:
        if s.startswith(left) and s.endswith(right): s = s[len(left):-len(right)].strip()
    s = re.sub(r'\\(?:,|!|;|quad|qquad)\s*', '', s)
    return s.strip()


def normalize_units(value, question):
    # Only strip a trailing unit that the public question itself supplies.
    s = value.strip()
    unit = r'(?:square |cubic )?(?:centimeters?|meters?|inches|inch|feet|foot|miles?|seconds?|minutes?|hours?|degrees?)'
    m = re.search(r'\s+(?:\\text\{)?(' + unit + r')\}?\.?$', s, re.I)
    if m and re.search(r'\b' + re.escape(m.group(1)) + r'\b', question, re.I):
        return s[:m.start()].strip(), 'question_unit_removed'
    return s, None


def split_top(s, separator=','):
    depth = 0; start = 0; parts = []
    for i, c in enumerate(s):
        if c in '([{': depth += 1
        elif c in ')]}': depth -= 1
        elif c == separator and depth == 0:
            parts.append(s[start:i].strip()); start = i + 1
    return parts + [s[start:].strip()]


def parse_scalar(s):
    from math_verify import parse, LatexExtractionConfig
    from sympy import Basic
    logging.getLogger('math_verify').setLevel(logging.ERROR)
    s = presentation(s)
    # Do not let parsers select an incidental number from prose or malformed math.
    if not s or s.count('{') != s.count('}') or '\\text' in s:
        return None
    if re.search(r'\b[A-Za-z]{3,}\b', re.sub(r'\\[A-Za-z]+', '', s)):
        return None
    values = parse(r'\boxed{' + s + '}', extraction_config=[LatexExtractionConfig()],
                   fallback_mode='no_fallback', parsing_timeout=2)
    return next((x for x in values if isinstance(x, Basic)), None)


def parse_value(value, question=''):
    from sympy import FiniteSet, Interval, Tuple, Union
    s = presentation(value)
    if '\\cup' in s:
        items = [parse_value(x, question) for x in s.split('\\cup')]
        if any(x is None for x in items): return None
        return Union(*items)
    set_marked = s.startswith(r'\{') and s.endswith(r'\}')
    if set_marked:
        parts = split_top(s[2:-2]); values = [parse_scalar(x) for x in parts]
        return None if any(x is None for x in values) else FiniteSet(*values)
    if len(s) >= 2 and s[0] in '([' and s[-1] in ')]':
        parts = split_top(s[1:-1])
        if len(parts) >= 2:
            values = [parse_scalar(x) for x in parts]
            if any(x is None for x in values): return None
            is_interval = bool(re.search(r'interval|inequalit|solution set|range of|domain', question, re.I)) or s[0] == '[' or s[-1] == ']' or any('infty' in x for x in parts)
            if is_interval:
                if len(values) != 2: return None
                return Interval(*values, left_open=s[0]=='(', right_open=s[-1]==')')
            return Tuple(*values)  # ordered unless the question explicitly asks for a set
    parts = split_top(s)
    if len(parts) > 1:
        if re.fullmatch(r'[+-]?\d{1,3}(,\d{3})+(\.\d+)?', s): return parse_scalar(s.replace(',', ''))
        if re.search(r'roots|solutions|set of|values of', question, re.I):
            values = [parse_scalar(x) for x in parts]
            return None if any(x is None for x in values) else FiniteSet(*values)
        return None
    return parse_scalar(s)


def grade(item):
    """Input is an OFFLINE record containing the already-sealed response and label."""
    from sympy import Set, Tuple
    from math_verify import verify
    answer, extraction = extract(item['solution'])
    out = {'task_id': item['task_id'], 'answer': answer, 'original_correct': item.get('original_correct'),
           'rechecked_correct': None, 'parse_status': extraction, 'truncation_status': bool(item.get('truncated')),
           'scoring_difference_reason': None, 'error_type': None}
    if out['truncation_status']:
        out.update(rechecked_correct=False, parse_status='truncated', error_type='output_limit')
    elif answer is None:
        out['error_type'] = 'incomplete_or_missing_answer'
    else:
        try:
            question = item.get('question', '')
            p, unit_reason = normalize_units(answer, question)
            p = presentation(p)
            g = presentation(item['gold_answer'])
            # Option labels are only recognized for a question with explicit options.
            option_question = bool(re.search(r'(?:\([A-E]\)|\\text\s*\{\([A-E]\)\})', question))
            option = lambda s: re.fullmatch(r'(?:\\text\{)?\(?([A-E])\)?\}?', s)
            pm, gm = option(p), option(g)
            if option_question and pm and gm:
                out.update(rechecked_correct=pm[1]==gm[1], parse_status='option_label')
            else:
                pv, gv = parse_value(p, question), parse_value(g, question)
                if pv is None or gv is None:
                    out.update(parse_status='unknown', error_type='unparsed_expression')
                elif isinstance(pv, (Set, Tuple)) or isinstance(gv, (Set, Tuple)):
                    if type(pv) is not type(gv):
                        out.update(parse_status='unknown', error_type='answer_type_ambiguity')
                    else:
                        result = pv == gv
                        if isinstance(pv, Tuple): result = len(pv)==len(gv) and all(verify(y,x,timeout_seconds=2,strict=True) for x,y in zip(pv,gv))
                        out.update(rechecked_correct=bool(result), parse_status='structured')
                else:
                    out.update(rechecked_correct=bool(verify(gv,pv,timeout_seconds=2,strict=True)), parse_status='symbolic')
            if unit_reason: out['normalization_note'] = unit_reason
        except Exception as exc:
            out.update(parse_status='unknown', error_type=type(exc).__name__)
    if item.get('original_correct') != out['rechecked_correct']:
        out['scoring_difference_reason'] = out.get('normalization_note') or out['error_type'] or ('last_final_answer_and_structured_equivalence:' + out['parse_status'])
    return out


def seal(record):
    return {**record, 'seal': digest(record)}


def assert_sealed(record):
    if record.get('seal') != digest({k:v for k,v in record.items() if k!='seal'}):
        raise ValueError('Unsealed or modified submission')


def score_sealed(submissions, labels_path, questions, expected_labels_hash, workers=12):
    """The only V2 scoring entry point. ALL seals are verified before label IO."""
    import concurrent.futures as cf
    import multiprocessing as mp
    if not 1 <= workers <= 12: raise ValueError('local worker limit')
    for row in submissions: assert_sealed(row)
    raw = Path(labels_path).read_bytes()
    import hashlib
    if hashlib.sha256(raw).hexdigest() != expected_labels_hash: raise ValueError('Label file changed')
    labels = {r['task_id']:r for r in jsonl(labels_path)}
    items = [{**r, 'gold_answer': labels[r['task_id']]['gold_answer'], 'question': questions[r['task_id']]} for r in submissions]
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as pool:
        return list(pool.map(grade, items, chunksize=1))
