"""Split the public task surface from private labels; loading tasks never opens labels."""
from pathlib import Path
from flowevo_bot.common import digest, jsonl, read_json
from flowevo_bot.schemas import ProblemView


def load_manifest(path, expected_split=None):
    path=Path(path)
    manifest=read_json(path)
    if manifest['schema_version']!='1.0': raise ValueError('Unknown manifest schema')
    if expected_split and manifest['split']!=expected_split: raise ValueError('Manifest split mismatch')
    problem_file=path.parent/manifest['problems_file']
    tasks=[ProblemView.model_validate(row) for row in jsonl(problem_file)]
    if digest([t.model_dump(mode='json') for t in tasks])!=manifest['problems_hash']:
        raise ValueError('Problem manifest hash mismatch')
    if len(tasks)!=manifest['count'] or len({t.task_id for t in tasks})!=len(tasks):
        raise ValueError('Invalid manifest task count or repeated IDs')
    return manifest,tasks,path.parent/manifest['evaluation_file']
