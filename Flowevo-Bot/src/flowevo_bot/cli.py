"""All real inference needs opt-in. --dry-run always installs the mock transport."""
import argparse
from pathlib import Path
import json
from runtime.config import load_config,MODES
from .common import write_json
from .strategy_bank import StrategyBank
from .workflows import build_bank,evaluate_manifest
from .reporting import analyze
from .data import prepare_math


def main(argv=None):
    parser=argparse.ArgumentParser(prog='flowevo-bot')
    commands=parser.add_subparsers(dest='command',required=True)
    audit=commands.add_parser('audit');audit.add_argument('--flowevo-path',required=True);audit.add_argument('--bot-path',required=True)
    audit.add_argument('--output',default='docs/AUDIT_REFRESH.json')
    prepare=commands.add_parser('prepare-data');prepare.add_argument('--math-dir',required=True)
    prepare.add_argument('--output-dir',default='data/manifests/math');prepare.add_argument('--seed',type=int,default=42)
    prepare.add_argument('--dev-fraction',type=float,default=.2);prepare.add_argument('--exclude-algebra-first',type=int,default=500)
    for name in ['build-bank','evaluate']:
        p=commands.add_parser(name);p.add_argument('--config',required=True)
        p.add_argument('--dry-run',action='store_true');p.add_argument('--allow-paid-api',action='store_true')
        p.add_argument('--resume',action='store_true');p.add_argument('--model');p.add_argument('--seed',type=int)
        p.add_argument('--max-calls',type=int);p.add_argument('--max-total-tokens',type=int)
        if name=='build-bank':
            p.add_argument('--train-manifest',required=True);p.add_argument('--dev-manifest',required=True);p.add_argument('--output',required=True)
        else:
            p.add_argument('--manifest');p.add_argument('--mode',choices=MODES,required=True)
            p.add_argument('--split',choices=['train-build','train-dev','test'],default='test')
            p.add_argument('--bank',required=True);p.add_argument('--output-dir',required=True)
    report=commands.add_parser('analyze');report.add_argument('--runs-dir',required=True);report.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if args.command=='audit':
        from .audit import audit_sources
        result=audit_sources(args.flowevo_path,args.bot_path)
        write_json(args.output,result);print(json.dumps(result,ensure_ascii=False,indent=2));return
    if args.command=='prepare-data':
        print(json.dumps(prepare_math(args.math_dir,args.output_dir,args.seed,args.dev_fraction,args.exclude_algebra_first)));return
    if args.command=='analyze':
        pairs=analyze(args.runs_dir,args.output);print(f'Wrote report with {len(pairs)} paired rows');return
    config=load_config(args.config)
    if args.model:config.llm.model=args.model
    if args.seed is not None:config.seed=args.seed
    if args.max_calls is not None:config.llm.max_calls=args.max_calls
    if args.max_total_tokens is not None:config.llm.max_total_tokens=args.max_total_tokens
    # Revalidate overrides to reject invalid budgets.
    config=type(config).model_validate(config.model_dump())
    if args.command=='build-bank':
        bank=build_bank(config,args.train_manifest,args.dev_manifest,args.output,dry_run=args.dry_run,allow_paid=args.allow_paid_api,resume=args.resume)
        print(json.dumps({'bank_hash':bank.bank_hash,'skills':len(bank.skills),'synthetic':bank.synthetic}));return
    bank=StrategyBank.load(args.bank,frozen=True,allow_synthetic=args.dry_run)
    summary,_=evaluate_manifest(config,args.manifest or config.manifest,bank,args.mode,args.output_dir,
        split=args.split,dry_run=args.dry_run,allow_paid=args.allow_paid_api,resume=args.resume)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
