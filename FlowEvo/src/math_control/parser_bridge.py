"""Import only V3's public parsing layer, bypassing its eager evaluator __init__.

No reference builder, grading engine, labels or correctness values are exposed.
The enclosing experiment freezes the exact original V3 source hashes.
"""
import importlib,sys,types
from pathlib import Path
NAME='_flowevo_v3_public_parser'
if NAME not in sys.modules:
    package=types.ModuleType(NAME);package.__path__=[str(Path(__file__).resolve().parents[1]/'math_evaluation')];sys.modules[NAME]=package

def module(name):
    if name not in {'models','spec','text','normalization','parsing','units'}:raise ValueError('Only public parsing modules are allowed')
    return importlib.import_module(NAME+'.'+name)

AnswerSpec=module('models').AnswerSpec
EvaluatorConfig=module('models').EvaluatorConfig
infer_spec=module('spec').infer_spec
normalize=module('normalization').normalize
boxes=module('text').boxes
math_spans=module('text').math_spans
presentation=module('text').presentation
CFG=EvaluatorConfig()

def parse_public(value,question):
    spec=infer_spec(question)
    if spec.uncertain:raise ValueError('uncertain public answer specification')
    return normalize(value,spec,CFG)
