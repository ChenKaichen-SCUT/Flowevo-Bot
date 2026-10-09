"""Reproducible paid experiment; API key is read from the parent miyao.txt only.
Run with --stage train|build|compare|all; all stages resume durable completed work.
"""
import argparse
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/math500_goldfree_20261009'

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['train','build','compare','all'],required=True);a=p.parse_args()
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:12])
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='1'
    os.environ['DEEPSEEK_API_KEY']=(ROOT.parent/'miyao.txt').read_text().strip()
    from runtime.config import Config
    from flowevo_bot.common import read_json,write_json
    from flowevo_bot.strategy_bank import StrategyBank
    from flowevo_bot.parallel_experiment import run_parallel
    cfg=Config.model_validate(read_json(OUT/'config.json'))
    if a.stage in ('train','all'):
        summary,_=run_parallel(cfg,OUT/'manifests/train.json',StrategyBank(frozen=True),'base_onepass',OUT/'train',
                              split='train-build',resume=(OUT/'train/checkpoint.json').exists())
        print('TRAIN FINISHED',summary,flush=True)
    if a.stage in ('build','all'):
        from flowevo_bot.experiment_bank import build_experiment_bank
        bank=build_experiment_bank(cfg,OUT)
        print('BANK FINISHED',len(bank.history),{k:s.status for k,s in bank.skills.items()},flush=True)
    if a.stage in ('compare','all'):
        from flowevo_bot.experiment_bank import compare_experiment
        compare_experiment(cfg,OUT,ROOT.parent/'FlowEvo')

if __name__=='__main__':main()
