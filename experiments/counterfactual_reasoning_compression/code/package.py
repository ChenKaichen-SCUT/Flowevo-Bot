"""Seal the completed study and create the requested archive, without API calls."""
from common import *
import zipfile,re

def main():
    required=['00_EXECUTIVE_SUMMARY.md','01_TRACE_ANALYSIS.md','02_COUNTERFACTUAL_INTERVENTIONS.md','03_MINIMAL_SUFFICIENT_STATE.md','04_ONLINE_FEASIBILITY.md','05_COMPRESSION_CONTROLLER.md','06_INDEPENDENT_PILOT_RESULTS.md','07_ACCURACY_AND_TOKEN_COST.md','08_MECHANISM_ATTRIBUTION.md','09_NEXT_RESEARCH_DECISION.md',
        'trace_alignment.csv','reasoning_events.jsonl','counterfactual_states.jsonl','counterfactual_outcomes.jsonl',
        'reasoning_state_features.csv','controller_decisions.jsonl','task_results.jsonl','task_pairwise.csv',
        'api_calls.jsonl','token_cost_breakdown.csv','dataset_manifest.json','token_length_distribution.csv','early_completion_risk.csv']
    assert all((OUT/name).is_file() for name in required)
    summary=read(OUT/'summary.json');checks=read(OUT/'evidence/artifact_checks.json')
    assert checks['passed']==checks['total']==24 and summary['no_more_api_calls']
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and not(set(p.parts)&{'__pycache__','.pytest_cache'}) and p.name!='run_manifest.json')
    manifest=dict(at=now(),reference_commit='e218ae68407bbeaf2dd2e81ab6bf952d3d7942f1',repository='https://github.com/ChenKaichen-SCUT/Flowevo-Bot',
        decision=summary['decision'],physical_http_attempts=summary['physical_calls'],known_tokens=summary['known_tokens'],
        unknown_token_upper_bound=summary['unknown_token_upper_bound'],max_calls=150,max_tokens=350000,
        guide_sha256=sha(OUT/'USER_GUIDE.txt'),unit_tests_passed=12,artifact_checks_passed=24,
        historical_files_protected=checks['historical_files_protected'],required_files=required,
        sources_and_results={str(p.relative_to(OUT)):sha(p) for p in files},
        supplemental_boundary_repair='3 calls; original84 preserved; controller and independent sample not retuned',no_more_api_calls=True)
    save('run_manifest.json',manifest);files.append(OUT/'run_manifest.json')
    secret=(ROOT/'miyao.txt').read_bytes().strip()
    pattern=re.compile(rb'(?:sk-[A-Za-z0-9_-]{28,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)')
    archive=ROOT/'counterfactual_reasoning_compression.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            data=p.read_bytes();assert not secret or secret not in data;assert not pattern.search(data),p
            z.writestr('counterfactual_reasoning_compression/'+str(p.relative_to(OUT)),data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and len(z.namelist())==len(files)
        for p in files:assert z.read('counterfactual_reasoning_compression/'+str(p.relative_to(OUT)))==p.read_bytes()
    archive.with_suffix('.zip.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print(json.dumps(dict(files=len(files),zip_bytes=archive.stat().st_size,sha256=sha(archive),required_files_present=True,archive_bytes_verified=True)))
if __name__=='__main__':main()
