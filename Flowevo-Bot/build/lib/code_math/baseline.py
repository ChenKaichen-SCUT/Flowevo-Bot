"""Adapted from FlowEvo runner (Apache-2.0). Gold-free boundary added here."""
from flowevo_bot.features import normalize_problem

OUTPUT_INSTRUCTION = 'Solve step by step. End with: The answer is [your answer].'


def base_prompt(problem):
    # Byte-for-byte equivalent to FlowEvo's cot=True mathematical base prompt.
    return f'Problem: {problem.problem}\n\n{OUTPUT_INSTRUCTION}'


class HistoryLibrary:
    """Read-only clean train-build history; no live test admission or label access."""
    def __init__(self, traces=()):
        self.entries = []
        for trace in traces:
            p = trace.provenance
            if p.eligible_for_skill_learning and not p.gold_exposed and not p.reference_solution_exposed:
                self.entries.append(trace)

    def retrieve(self, task):
        candidates = []
        words = set(task.problem.lower().split())
        for t in self.entries:
            if t.problem.task_id == task.task_id or normalize_problem(t.problem.problem) == normalize_problem(task.problem):
                continue
            score = len(set(t.problem.problem[:200].lower().split()) & words)
            if score > 3:
                candidates.append((score, t.problem.task_id, t))
        if not candidates:
            return ''
        t = sorted(candidates, key=lambda x: (-x[0], x[1]))[0][2]
        return f'Example:\nProblem: {t.problem.problem[:200]}\nSolution:\n{t.first_solution[:500]}'
