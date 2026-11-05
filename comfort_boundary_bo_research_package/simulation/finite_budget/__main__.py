"""Practical batch commands; running is never implicit for analysis/validation."""
import argparse
import json
from pathlib import Path
import sys
from .study import (run_study_v2,validate_run,freeze_study,select_staircase,replay_subset,
                    reread_prior_histories,canonical,write_json,oracle_diagnostics)
from .analysis import analyze_v2


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith('--'): argv.insert(0,'run')
    parser=argparse.ArgumentParser(description='Finite-budget v2: run, freeze, validate, selection and analysis')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run'); run.add_argument('--config',required=True); run.add_argument('--output',required=True); run.add_argument('--freeze')
    run.add_argument('--workers',type=int,default=1,help='Runtime process count, independent of scientific config; use6 on a suitable machine')
    freeze=sub.add_parser('freeze'); freeze.add_argument('--config',required=True); freeze.add_argument('--output',required=True)
    freeze.add_argument('--selection',required=True); freeze.add_argument('--diagnostics',required=True)
    select=sub.add_parser('select-staircase'); select.add_argument('--input',required=True); select.add_argument('--output',required=True)
    validate=sub.add_parser('validate'); validate.add_argument('--input',required=True); validate.add_argument('--verify-readouts',action='store_true')
    replay=sub.add_parser('replay'); replay.add_argument('--input',required=True); replay.add_argument('--limit',type=int,default=1)
    analyze=sub.add_parser('analyze'); analyze.add_argument('--input',required=True); analyze.add_argument('--output',required=True)
    analyze.add_argument('--no-plots',action='store_true'); analyze.add_argument('--verify-readouts',action='store_true')
    reread=sub.add_parser('reread-priors'); reread.add_argument('--input',required=True); reread.add_argument('--output',required=True)
    oracle=sub.add_parser('oracle-diagnostics'); oracle.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    if args.command=='run': result=run_study_v2(args.config,args.output,freeze_path=args.freeze,workers=args.workers)
    elif args.command=='freeze': result=freeze_study(args.config,args.output,read(args.selection),read(args.diagnostics))
    elif args.command=='select-staircase': result=select_staircase(args.input,args.output)
    elif args.command=='validate': result=validate_run(args.input,verify_readouts=args.verify_readouts)
    elif args.command=='replay': result=replay_subset(args.input,args.limit)
    elif args.command=='analyze': result=analyze_v2(args.input,args.output,plots=not args.no_plots,verify_readouts=args.verify_readouts)
    elif args.command=='reread-priors': result=reread_prior_histories(args.input,args.output)
    else:
        if Path(args.output).exists(): raise FileExistsError(args.output)
        result=oracle_diagnostics(); write_json(args.output,result)
    print(canonical(result))
    return 0


if __name__=='__main__': raise SystemExit(main())
