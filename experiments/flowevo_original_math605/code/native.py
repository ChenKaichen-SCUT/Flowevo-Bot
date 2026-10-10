"""Import the exact upstream runner and loader snapshots, without code patches."""
from common import *
import ast
import importlib.util
from core.schemas import CodeTaskInstance

def load_snapshot(name):
    path = OUT / 'evidence' / ('upstream_' + name + '.py')
    expected = read(OUT / 'evidence/source_provenance.json')['files'][str(path.relative_to(ROOT))]
    assert sha(path) == expected
    spec = importlib.util.spec_from_file_location('original_flowevo_' + name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

runner = load_snapshot('runner')
loader = load_snapshot('loader')

def task_for(public, reference=''):
    return CodeTaskInstance(
        task_id=public['task_id'], benchmark='math', prompt=public['problem'],
        text=public['problem'], canonical_solution=reference,
        metadata={'gold_answer': loader._extract_math_answer(reference),
                  'level': public['level'], 'type': public['subject']})

def score(public, reference, text):
    task = task_for(public, reference)
    passed, feedback = runner.verify(task, text.strip(), None)
    predicted = runner.extract_math_answer(text.strip())
    gold = task.metadata['gold_answer']
    return dict(passed=passed, extracted_prediction=predicted, extracted_reference=gold,
                normalized_prediction=runner._normalize_answer(predicted),
                normalized_reference=runner._normalize_answer(gold), native_feedback=feedback)

def assert_local_extractors_unchanged():
    checks = {}
    for module, functions, constants in (
        ('runner', ['extract_math_answer', '_normalize_answer', '_build_math_prompt'],
         ['_NUMBER_RE', '_ANSWER_IS_RE', '_BOXED_RE']),
        ('loader', ['_extract_math_answer'], ['_BOXED_RE'])):
        def nodes(path):
            result = {}
            for node in ast.parse(Path(path).read_text()).body:
                if isinstance(node, ast.FunctionDef) and node.name in functions:
                    result[node.name] = ast.dump(node, include_attributes=False)
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in constants:
                            result[target.id] = ast.dump(node, include_attributes=False)
            return result
        original = nodes(OUT / 'evidence' / ('upstream_' + module + '.py'))
        current = nodes(ROOT / 'FlowEvo/src/code_math' / (module + '.py'))
        assert original == current
        checks[module] = {name: digest(value) for name, value in original.items()}
    return checks
