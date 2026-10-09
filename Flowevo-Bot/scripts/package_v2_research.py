"""Package the completed study and current reproduction sources; no API calls."""
import hashlib
import json
from pathlib import Path
import zipfile
from run_v2_research import ROOT,OUT

def main():
    with zipfile.ZipFile(OUT/'snapshots/reproduction_source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in (ROOT/'src').rglob('*.py'):z.write(f,str(f.relative_to(ROOT)))
        for name in ['run_v2_research.py','report_v2_research.py','verify_v2_research.py','recheck_v2_history.py','package_v2_research.py']:
            f=ROOT/'scripts'/name;z.write(f,str(f.relative_to(ROOT)))
        z.write(ROOT/'pyproject.toml','pyproject.toml')
    files=[f for f in sorted(OUT.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.name!='PACKAGE_MANIFEST.json']
    manifest={'files':[{'path':str(f.relative_to(OUT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in files],
              'file_count':len(files),'scope':'All V2 results, safe raw calls, development questions/labels, selected source traces, reports, tests, frozen/current source snapshots. Full original datasets and old bank are in the GitHub workspace.'}
    mp=OUT/'PACKAGE_MANIFEST.json';mp.write_text(json.dumps(manifest,indent=2)+'\n')
    path=OUT.with_suffix('.zip')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files+[mp]:z.write(f,str(f.relative_to(OUT.parent)))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for entry in manifest['files']:
            assert hashlib.sha256(z.read(OUT.name+'/'+entry['path'])).hexdigest()==entry['sha256']
    sha=hashlib.sha256(path.read_bytes()).hexdigest();path.with_suffix('.zip.sha256').write_text(sha+'  '+path.name+'\n')
    print(json.dumps({'archive':str(path),'files':len(files)+1,'bytes':path.stat().st_size,'sha256':sha}),flush=True)

if __name__=='__main__':main()
