"""Common offline symbolic grader; invoked only after submissions are sealed.
Math-Verify runs in process workers so its signal-based timeouts remain enabled.
"""
import logging
from .evaluator import normalize

def grade_one(item):
    task_id, predicted, gold, truncated = item
    strict = predicted is not None and normalize(predicted)==normalize(gold)
    equivalent = False
    error = None
    if not truncated and predicted is not None:
        if strict:
            equivalent = True
        else:
            from math_verify import parse,verify,LatexExtractionConfig
            logging.getLogger('math_verify').setLevel(logging.ERROR)
            def boxed(value):
                value=value.strip().strip('$').strip()
                # Remove only outer presentation marks, never alter inner math.
                if value.startswith('**') and value.endswith('**'):value=value[2:-2].strip()
                return r'\boxed{'+value+'}'
            try:
                g=parse(boxed(gold),extraction_config=[LatexExtractionConfig()],parsing_timeout=3)
                p=parse(boxed(predicted),extraction_config=[LatexExtractionConfig()],parsing_timeout=3)
                equivalent=bool(g and p and verify(g,p,timeout_seconds=3))
            except Exception as exc:
                error=type(exc).__name__
    return {'task_id':task_id,'strict_correct':bool(strict and not truncated),
            'first_pass_correct':bool(equivalent),'final_correct':bool(equivalent),
            'feedback':'correct' if equivalent else 'incorrect','grader_error':error}
