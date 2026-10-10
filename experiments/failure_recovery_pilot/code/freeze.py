from common import *
if __name__=='__main__':
 assert not (OUT/'evidence/freeze.json').exists()
 assert not (OUT/'data/confirmation_public_states.jsonl').exists()
 for r in (OUT/'raw_calls').glob('*.json'):assert not read(r).get('stage','').startswith('confirmation')
 files=list((ROOT/'FlowEvo-Recovery').rglob('*.py'))+list((OUT/'code').glob('*.py'))
 files +=[OUT/n for n in ['config.json','dataset_split_manifest.json','recovery_experiences.jsonl','data/shuffled_experiences.jsonl','data/train_math_states.jsonl','data/train_code_tasks.jsonl','data/confirmation_tasks.jsonl','data/offline_labels.json']]
 frozen={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
 write(OUT/'evidence/freeze.json',{'at':now(),'files':frozen,'aggregate_hash':digest(frozen),'purpose':'controller, memory, shuffled control, split, prompts, limits and scoring frozen before independent first passes','adapter_audit':'zero-call first public-entrypoint-defining block; diagnostic on ALL sealed code outputs, never selected by hidden results'})
 print('frozen',len(frozen),'files',digest(frozen))
