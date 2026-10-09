from code_math.baseline import base_prompt, OUTPUT_INSTRUCTION
from .token_accounting import estimate_tokens


def compact_prompt(task, skills, budget=100):
    blocks = []
    for skill in skills:
        if estimate_tokens(skill.compact_prompt) > budget:
            raise ValueError('Over-budget strategy needs recompression and validation')
        blocks.append(skill.compact_prompt)
    return ('Relevant strategy:\n' + '\n\n'.join(blocks) + '\n\nCurrent problem:\n' + task.problem
            + '\n\nApply the strategy only if its conditions hold. Otherwise solve normally.\n\n'
            + OUTPUT_INSTRUCTION)


def history_prompt(task, context):
    return ('Here is a similar solved problem for reference:\n' + context + '\n\n' if context else '') + base_prompt(task)


def repair_prompt(task, previous, context=''):
    # Triggered ONLY by missing final-answer format; no score or gold argument exists.
    return (('Relevant strategy:\n' + context + '\n\n') if context else '') + (
        f'Problem: {task.problem}\nYour previous output:\n{previous}\n'
        'The required final-answer field is missing. Check the response format.\n' + OUTPUT_INSTRUCTION)
