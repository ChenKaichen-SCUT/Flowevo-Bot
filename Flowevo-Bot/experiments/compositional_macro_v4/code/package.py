"""Create a hashed, source-inclusive V4 research archive; never include credentials."""
import sys,zipfile,importlib.metadata,platform
from common import *

def main():
    result=read(OUT/'evidence/final_verification.json');assert result['status']=='PASS'
    write(OUT/'evidence/environment.json',{'python':platform.python_version(),
        'packages':sorted([{'name':d.metadata['Name'],'version':d.version} for d in importlib.metadata.distributions()],key=lambda x:x['name'].lower()),
        'compileall':'PASS: src/flowevo_bot/compositional_v4 and experiments/compositional_macro_v4/code',
        'additional_dependency':'rapidfuzz==3.14.1','runtime':'existing Python 3.10 venv; no new model installation'})
    files=[p for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='artifact_inventory.json']
    files+=list((ROOT/'src/flowevo_bot').rglob('*.py'))
    files+=[ROOT/'tests/test_compositional_v4.py',ROOT/'pyproject.toml',ROOT/'NOTICE.md']
    files+=list((ROOT/'licenses').glob('*'))
    files+=[RMMD/'data/clean_success_traces.jsonl',V3/'data/automatic_macro_bank.json']
    files=sorted(set(p for p in files if p.is_file()))
    inventory={'created_at':now(),'scope':'all V4 reports/data/evidence/code + complete flowevo_bot Python sources + V4 tests + original603 traces + frozen V3 bank',
        'full_historical_replay':'Use the GitHub workspace checkout for protected_history and historical dataset files; this archive is the complete V4 deliverable, not a second copy of all upstream datasets.',
        'files':[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
    write(OUT/'artifact_inventory.json',inventory)
    archive=ROOT/'compositional_macro_v4.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[OUT/'artifact_inventory.json']:z.write(p,str(p.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in inventory['files']:
            import hashlib
            assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
        assert not any('miyao' in name or '__pycache__' in name or '.venv' in name for name in z.namelist())
    (ROOT/'compositional_macro_v4.zip.sha256').write_text(sha(archive)+'  compositional_macro_v4.zip\n')
    print({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(files)+1,'sha256':sha(archive)})
if __name__=='__main__':main()
