"""Seal the final runtime, bank, sources, split, protocol and test evidence before holdout."""
import sys,zipfile,xml.etree.ElementTree as ET
from common import *

def main():
    if (OUT/'evidence/freeze.json').exists():raise RuntimeError('already frozen; cannot silently refreeze')
    for split in ('dev-engineering','dev-selection'):
        assert (OUT/f'evidence/{split}.scored.jsonl').exists()
    root=ET.parse(OUT/'evidence/all_tests.xml').getroot()
    suites=list(root.iter('testsuite'))
    assert suites and all(int(s.get('failures',0))==0 and int(s.get('errors',0))==0 for s in suites)
    paths=list((ROOT/'src/flowevo_bot/compositional_v4').glob('*.py'))
    paths+=list((ROOT/'src/flowevo_bot/goal_v3').glob('*.py'))
    paths+=list((OUT/'code').glob('*.py'))
    paths+=[OUT/n for n in ['config.json','dataset_split_manifest.json','automatic_macro_bank.json','synthesis_search.json','macro_candidates.jsonl',
                           'reasoning_operations.jsonl','evidence/source_extractions.json','evidence/local_cost_gate.json',
                           'evidence/all_tests.xml','evidence/all_tests.log']]
    paths+=list((OUT/'snapshots').glob('*.problems.jsonl'))
    paths+=[ROOT/'tests/test_compositional_v4.py',RMMD/'data/clean_success_traces.jsonl',V3/'data/automatic_macro_bank.json',
        ROOT/'src/flowevo_bot/rmmd/macros.py',ROOT/'src/flowevo_bot/v2/evaluator.py']
    record={'created_at':now(),'reference_commit':'ebe50279392e8a6d0ad717ef0cd33922115552ca',
            'config_sha256':sha(OUT/'config.json'),'bank_sha256':sha(OUT/'automatic_macro_bank.json'),
            'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))},
            'confirmation_read_for_solver':False,'test_count':sum(int(s.get('tests',0)) for s in suites),
            'no_post_confirmation_parser_or_bank_tuning':True,'new_api_calls':0}
    record['freeze_hash']=digest(record)
    write(OUT/'evidence/freeze.json',record)
    with zipfile.ZipFile(OUT/'snapshots/frozen_runtime.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(paths)):z.write(p,str(p.relative_to(ROOT)))
    print(record['freeze_hash'],len(paths),'frozen files')
if __name__=='__main__':main()
