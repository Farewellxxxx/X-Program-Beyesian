"""Paired execution misspecification/budget audit; no real vehicle data."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path
import sys
import time

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from comfort_boundary_bo_research_package.simulation import execution_misspecification as stress
from long_horizon_audit.scripts import run_execution_population_audit as previous
sim=previous.sim
OUTPUT=ROOT/'long_horizon_audit/derived/execution_robustness_20261104'
BUDGETS=(8,20,40,160)
ARMS=('nominal','oracle',*[f'cal{n}' for n in BUDGETS])
PROFILES={
    'matched_low':('low',0.,stress.Distortion()),
    'matched_high':('high',0.,stress.Distortion()),
    'biased_high':('high',.15,stress.Distortion()),
    'gain_high':('high',.15,stress.Distortion(gain=.25)),
    'nonlinear_high':('high',.15,stress.Distortion(quadratic=.45)),
    'correlated_high':('high',.15,stress.Distortion(correlation=.75)),
    'combined_high':('high',.15,stress.Distortion(.25,.45,.75)),
}


@dataclass(frozen=True)
class RobustnessSpec:
    profile: str
    arm: str
    population_block: int
    process_repeat: int
    config: sim.Config
    distortion: stress.Distortion


def build_scenarios(population_blocks=5,process_repeats=2):
    if isinstance(population_blocks,bool) or not isinstance(population_blocks,int) or not 2<=population_blocks<=10:
        raise ValueError('Use 2 to 10 population batches')
    if isinstance(process_repeats,bool) or not isinstance(process_repeats,int) or not 1<=process_repeats<=9:
        raise ValueError('Use 1 to 9 process repeats')
    specs=[]
    for profile,(noise,bias,distortion) in PROFILES.items():
        for block in range(1,population_blocks+1):
            for repeat in range(1,process_repeats+1):
                if profile.startswith('matched_'):
                    process=2026120000+block*100+repeat*10+(noise=='high')
                    calibration=2026130000+block*100+repeat*10
                else:
                    process=2026140000+block*100+repeat-1
                    calibration=2026150000+block*100+repeat-1
                for arm in ARMS:
                    budget=int(arm[3:]) if arm.startswith('cal') else 40
                    config=sim.Config(population_seed=2026110400+block,seed=process,calibration_seed=calibration,
                        execution_noise=noise,calibration_bias=bias,calibration_trials=budget,
                        execution_belief='calibrated' if arm.startswith('cal') else arm,
                        scenario_name=f'{profile}_p{block}_r{repeat}_{arm}')
                    specs.append(RobustnessSpec(profile,arm,block,repeat,config,distortion))
    return specs


def expected_metadata(spec):
    c=spec.config
    base=previous.experiment_metadata(previous.ScenarioSpec('robustness',spec.population_block,spec.process_repeat,c))
    truth=previous.fingerprint({'base':base['generator_fingerprint'],'distortion':asdict(spec.distortion)})
    base.update(profile=spec.profile,arm=spec.arm,scenario=c.scenario_name,
        truth_fingerprint=truth,generator_fingerprint=truth,config_fingerprint=previous.fingerprint(asdict(c)),
        population_seed=c.population_seed,process_seed=c.seed,calibration_seed=c.calibration_seed,
        process_rng_mode=c.process_rng_mode,execution_noise=c.execution_noise,execution_belief=c.execution_belief,
        n_participants=c.n_participants,n_trials_per_algorithm_participant=c.n_trials,
        calibration_budget=c.calibration_trials if c.execution_belief=='calibrated' else 0,
        calibration_design='nested_vdc2' if c.execution_belief=='calibrated' else 'none',
        truth_gain=spec.distortion.gain,truth_quadratic=spec.distortion.quadratic,
        truth_residual_correlation=spec.distortion.correlation,diagnostic_seed=c.calibration_seed)
    return base


def prepare(spec):
    return stress.prepare_stress_execution(spec.config,spec.distortion)


def diagnose(spec,prepared,diagnostic_samples=4096):
    frame=stress.distribution_diagnostics(prepared,spec.config.calibration_seed,diagnostic_samples)
    for key,value in expected_metadata(spec).items(): frame[key]=value
    return frame


def execute(spec,diagnostic_samples=4096):
    prepared=prepare(spec)
    old_spec=previous.ScenarioSpec('robustness',spec.population_block,spec.process_repeat,spec.config)
    metrics,participants,population,calibration=previous.execute(old_spec,prepared)
    metadata=expected_metadata(spec)
    for frame in (metrics,participants,calibration):
        for key,value in metadata.items(): frame[key]=value
    return metrics,participants,population,calibration,diagnose(spec,prepared,diagnostic_samples)


def execute_replay(spec):
    return previous.execute(spec)


def save_frames(outputs,profile,out,kinds):
    for index,kind in enumerate(kinds):
        frames=[result[index] for result in outputs]
        nonempty=[frame for frame in frames if not frame.empty]
        combined=pd.concat(nonempty,ignore_index=True) if nonempty else frames[0].copy()
        if kind=='populations': combined=combined.drop_duplicates().sort_values(['population_seed','participant_id'])
        combined.to_csv(out/f'{profile}_{kind}.csv',index=False,encoding='utf-8-sig')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['all','replay',*PROFILES],default='all')
    parser.add_argument('--workers',type=int,default=1)
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    parser.add_argument('--population-blocks',type=int,default=5)
    parser.add_argument('--process-repeats',type=int,default=2)
    args=parser.parse_args()
    if not 1<=args.workers<=8: parser.error('workers must be between 1 and 8')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    specs=build_scenarios(args.population_blocks,args.process_repeats)
    profiles=[*PROFILES,'replay'] if args.profile=='all' else [args.profile]
    started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for profile in profiles:
            replay=profile=='replay'
            selected=([s for s in previous.build_scenarios() if s.suite in ('population','stress')]
                if replay else [s for s in specs if s.profile==profile])
            outputs=[]
            for index,result in enumerate(pool.map(execute_replay if replay else execute,selected),1):
                outputs.append(result)
                print(f'[{profile} {index}/{len(selected)}] elapsed={time.perf_counter()-started:.1f}s',flush=True)
            kinds=('per_run','participants','populations','calibration')+(() if replay else ('diagnostics',))
            save_frames(outputs,profile,args.output_dir,kinds)
            manifest=dict(profile=profile,population_blocks=5 if replay else args.population_blocks,
                process_repeats=2 if replay else args.process_repeats,diagnostic_samples=0 if replay else 4096,
                scenarios=[asdict(s) for s in selected])
            (args.output_dir/f'{profile}_configurations.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
            print(f'WROTE {profile}: {len(selected)} scenarios',flush=True)


if __name__=='__main__': main()
