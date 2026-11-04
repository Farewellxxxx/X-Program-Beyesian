"""Paired richer execution fits and exact replay of the frozen simple-estimator study."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from comfort_boundary_bo_research_package.simulation import flexible_execution as model
from long_horizon_audit.scripts import run_execution_robustness_audit as old

OUTPUT=ROOT/'long_horizon_audit/derived/flexible_execution_20261104'
SETTINGS=model.FitSettings()


def build_scenarios(population_blocks=5,process_repeats=2):
    return [s for s in old.build_scenarios(population_blocks,process_repeats) if s.arm.startswith('cal')]


def observation_fingerprint(observations):
    # Canonical ordered little-endian float64 values; metadata is checked separately.
    values=observations[old.sim.CALIBRATION_FIELDS].to_numpy(dtype='<f8')
    return hashlib.sha256(values.tobytes(order='C')).hexdigest()


def manifest(specs,blocks,repeats,replay=False):
    return dict(population_blocks=blocks,process_repeats=repeats,
        execution_estimator='original_replay' if replay else model.ESTIMATOR,
        fit_settings=None if replay else asdict(SETTINGS),
        fit_settings_fingerprint=None if replay else SETTINGS.fingerprint(),
        diagnostic_samples=0 if replay else 4096,scenarios=[asdict(s) for s in specs])


def execute(spec,diagnostic_samples=4096):
    prepared=model.upgrade_prepared(old.prepare(spec),SETTINGS)
    base=old.previous.ScenarioSpec('robustness',spec.population_block,spec.process_repeat,spec.config)
    metrics,participants,population,calibration=old.previous.execute(base,prepared)
    diagnostics=old.diagnose(spec,prepared,diagnostic_samples)
    metadata={**old.expected_metadata(spec),**prepared.metadata,
        'calibration_fingerprint':observation_fingerprint(prepared.calibration_observations)}
    for frame in (metrics,participants,calibration,diagnostics):
        for key,value in metadata.items(): frame[key]=value
    return metrics,participants,population,calibration,diagnostics,pd.DataFrame([metadata])


def execute_replay(spec):
    base=old.previous.ScenarioSpec('robustness',spec.population_block,spec.process_repeat,spec.config)
    metrics=old.previous.execute(base,old.prepare(spec))[0]
    for key,value in old.expected_metadata(spec).items(): metrics[key]=value
    return metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['all','flexible','replay'],default='all')
    parser.add_argument('--profile',choices=['all',*old.PROFILES],default='all')
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    parser.add_argument('--population-blocks',type=int,default=5)
    parser.add_argument('--process-repeats',type=int,default=2)
    args=parser.parse_args()
    if not 1<=args.workers<=8: parser.error('workers must be between 1 and 8')
    specs=old.build_scenarios(args.population_blocks,args.process_repeats)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for suite in (['flexible','replay'] if args.suite=='all' else [args.suite]):
            for profile in (list(old.PROFILES) if args.profile=='all' else [args.profile]):
                replay=suite=='replay'
                selected=[s for s in specs if s.profile==profile and (replay or s.arm.startswith('cal'))]
                outputs=[]
                for index,result in enumerate(pool.map(execute_replay if replay else execute,selected),1):
                    outputs.append(result)
                    print(f'[{suite}/{profile} {index}/{len(selected)}] elapsed={time.perf_counter()-started:.1f}s',flush=True)
                prefix=f'replay_{profile}' if replay else profile
                if replay:
                    pd.concat(outputs,ignore_index=True).to_csv(args.output_dir/f'{prefix}_per_run.csv',index=False,encoding='utf-8-sig')
                else:
                    old.save_frames(outputs,prefix,args.output_dir,('per_run','participants','populations','calibration','diagnostics','fits'))
                (args.output_dir/f'{prefix}_configurations.json').write_text(
                    json.dumps(manifest(selected,args.population_blocks,args.process_repeats,replay),indent=2),encoding='utf-8')
                print(f'WROTE {prefix}: {len(selected)} scenarios',flush=True)


if __name__=='__main__': main()
