"""Export the actual native frozen-library prompts for a paired experiment.
Input files contain public questions and clean train-build model traces only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from code_math.runner import CodeSkillLibrary, build_goldfree_math_prompt
from core.schemas import CodeTaskInstance


def export(problems_path, history_path, output):
    library = CodeSkillLibrary()
    history = json.loads(Path(history_path).read_text())
    for trace in history:
        p = trace['provenance']
        if not (trace['first_pass_correct'] and p['first_pass'] and p['origin_split']=='train-build'
                and p['eligible_for_skill_learning'] and not p['gold_exposed']
                and not p['reference_solution_exposed'] and not p['synthetic']):
            raise ValueError('Untrusted source history')
        task = CodeTaskInstance(task_id=trace['problem']['task_id'], benchmark='math', prompt=trace['problem']['problem'])
        library.add(task, trace['first_solution'])
    result = []
    for line in Path(problems_path).read_text().splitlines():
        p = json.loads(line)
        if set(p) - {'task_id','problem','subject','level','public_metadata'}:
            raise ValueError('Public problems must not include labels')
        task = CodeTaskInstance(task_id=p['task_id'], benchmark='math', prompt=p['problem'])
        prompt = build_goldfree_math_prompt(task, library)
        result.append({'task_id':task.task_id, 'prompt':prompt,
                       'route':'history' if library.retrieve(task)['type']=='context' else 'base'})
    artifact = {'implementation':str(Path(__file__).resolve().parents[1] / 'src/code_math/runner.py'),
                'implementation_sha256':hashlib.sha256((Path(__file__).resolve().parents[1] / 'src/code_math/runner.py').read_bytes()).hexdigest(),
                'history_size':library.size, 'gold_reflection':False, 'prompts':result}
    Path(output).write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
    Path(output).with_name('native_math_library.json').write_text(json.dumps(library.to_dict(),ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--problems',required=True);p.add_argument('--history',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();export(a.problems,a.history,a.output)
