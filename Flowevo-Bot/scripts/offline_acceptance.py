"""Run all public dry-run entrypoints. No network or paid API is used."""
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run(*args):
    result=subprocess.run([sys.executable,'-m','flowevo_bot.cli',*args],cwd=ROOT,text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    return result.stdout


def main():
    suffix=sys.argv[1] if len(sys.argv)>1 else 'offline_final'
    root=ROOT/'runs'/suffix
    if root.exists():raise FileExistsError('Choose a fresh acceptance run name')
    bank=ROOT/'data/skill_banks'/f'{suffix}_bank.json'
    run('build-bank','--config','configs/math_strategy.yaml',
        '--train-manifest','data/manifests/train.json','--dev-manifest','data/manifests/dev.json',
        '--output',str(bank),'--dry-run')
    from runtime.config import MODES
    for mode in MODES:
        output=run('evaluate','--config','configs/experiment_modes.yaml','--mode',mode,'--split','test',
                   '--bank',str(bank),'--output-dir',str(root/mode),'--dry-run')
        summary=json.loads(output)
        assert summary['n']==3 and summary['real_api_calls']==0 and summary['simulated']
        print(mode, 'OK', flush=True)
    run('analyze','--runs-dir',str(root),'--output',str(root/'EXPERIMENT_REPORT.md'))
    pairs=json.loads((root/'EXPERIMENT_REPORT.pairwise.json').read_text())
    assert len(pairs)==18
    print(f'Acceptance passed: 7 modes, 18 paired records, 0 real API calls. {root}',flush=True)


if __name__=='__main__':main()
