"""Read-only local source discovery, never silently substitutes another checkout."""
import subprocess
import hashlib
from pathlib import Path


def audit_sources(flowevo_path,bot_path):
    result={}
    for label,raw,required in [('FlowEvo',flowevo_path,['src/code_math/runner.py','src/code_math/loader.py']),
                               ('BoT',bot_path,['bot_pipeline.py','meta_buffer.py','meta_buffer_utilis.py'])]:
        root=Path(raw).resolve()
        if not root.is_dir():raise FileNotFoundError(f'{label} repository missing: {root}')
        hashes={}
        for rel in required:
            p=root/rel
            if not p.is_file():raise FileNotFoundError(f'{label} required interface missing: {p}')
            hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
        result[label]={'path':str(root),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'status':subprocess.check_output(['git','status','--short'],cwd=root,text=True),
            'interface_hashes':hashes,'license_present':(root/'LICENSE').is_file()}
    runner=(Path(flowevo_path)/'src/code_math/runner.py').read_text()
    result['observations']={'legacy_math_verifier_uses_gold': 'gold = task.metadata.get("gold_answer"' in runner,
        'math_skill_block_present':'if task.benchmark in ("gsm8k", "math"):\n            return {"type": "none"}' in runner,
        'see_manual_audit':'docs/SOURCE_AUDIT.md'}
    return result
