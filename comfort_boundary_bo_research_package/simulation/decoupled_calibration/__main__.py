"""Run a frozen, independent passenger calibration comparison."""
import argparse
import json
from pathlib import Path
from .study import run_study


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/decoupled_pilot.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    summary=run_study(json.loads(args.config.read_text(encoding='utf-8')),args.output)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
