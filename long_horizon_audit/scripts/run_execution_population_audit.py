"""Independent population batches, paired execution beliefs and fixed controls."""
from dataclasses import asdict, dataclass, replace
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim
from long_horizon_audit.scripts.run_multiseed_simulation_audit import summarize_trials

OUTPUT=ROOT/'long_horizon_audit/derived/execution_population_20261104'
SUITES=('historical','fixed_control','population','stress')


@dataclass(frozen=True)
class ScenarioSpec:
    suite: str
    population_block: int
    process_repeat: int
    config: sim.Config


def build_scenarios(population_blocks: int=5, process_repeats: int=2) -> list[ScenarioSpec]:
    for count in (population_blocks,process_repeats):
        if isinstance(count,bool) or not isinstance(count,int) or count<1:
            raise ValueError('Population/process counts must be positive integers')
    # Keep seed roles disjoint and avoid collisions in the explicit nested layout.
    if not 2<=population_blocks<=10:
        raise ValueError('Use 2 to 10 population blocks, matching the tabulated small-sample t intervals')
    if process_repeats>9:
        raise ValueError('This explicit seed layout supports at most nine process repeats')
    specs=[]
    for repeat in range(5):
        for index,noise in enumerate(('low','high')):
            config=sim.Config(seed=20268000+repeat*10+index,execution_noise=noise,
                execution_belief='oracle',scenario_name=f'multiseed_{noise}_{repeat+1}')
            specs.append(ScenarioSpec('historical',0,repeat+1,config))
    for block in range(1,population_blocks+1):
        population_seed=2026110400+block
        for repeat in range(1,process_repeats+1):
            for index,noise in enumerate(('low','high')):
                base=sim.Config(population_seed=population_seed,seed=2026120000+block*100+repeat*10+index,
                    calibration_seed=2026130000+block*100+repeat*10,execution_noise=noise)
                for mode in ('oracle','calibrated'):
                    config=replace(base,execution_belief=mode,scenario_name=f'population_p{block}_r{repeat}_{noise}_{mode}')
                    specs.append(ScenarioSpec('population',block,repeat,config))
                config=replace(base,population_seed=sim.BASE_SEED+101,execution_belief='oracle',
                    scenario_name=f'fixed_p{block}_r{repeat}_{noise}_oracle')
                specs.append(ScenarioSpec('fixed_control',block,repeat,config))
        for mode in ('oracle','nominal','calibrated'):
            config=sim.Config(population_seed=population_seed,seed=2026140000+block*100,
                calibration_seed=2026150000+block*100,execution_noise='high',calibration_bias=.15,
                execution_belief=mode,scenario_name=f'stress_p{block}_high_{mode}')
            specs.append(ScenarioSpec('stress',block,1,config))
    return specs


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def experiment_metadata(spec: ScenarioSpec, passengers=None) -> dict:
    config=spec.config
    if passengers is None: passengers=sim.make_passengers(config)
    public_settings={field.name:getattr(config,field.name) for field in sim.fields(sim.ExecutionSettings)}
    generator={**public_settings,'execution_noise':config.execution_noise,
        'calibration_bias':config.calibration_bias,'feedback_noise':config.feedback_noise}
    return dict(experiment_suite=spec.suite,population_block=spec.population_block,process_repeat=spec.process_repeat,
        generator_fingerprint=fingerprint(generator),policy_fingerprint=fingerprint(asdict(sim.policy_settings(config))),
        population_fingerprint=fingerprint([asdict(p) for p in passengers]),
        calibration_budget=config.calibration_trials)


def execute(spec: ScenarioSpec):
    config=spec.config; passengers=sim.make_passengers(config)
    trials=sim.run_scenario(config,passengers)
    participant,*_=sim.evaluate(trials)
    metrics=summarize_trials(sim,config,trials)
    metadata=experiment_metadata(spec,passengers)
    for frame in (metrics,participant):
        for key,value in metadata.items(): frame[key]=value
    motion_fields=['participant_id','trial_id','target_command_x','peak_accel','peak_jerk','duration_s',
                   'realized_intensity','acceptable','discomfort','p_accept_true']
    trajectories={name:hashlib.sha256(group.sort_values(['participant_id','trial_id'])[motion_fields]
        .to_csv(index=False,float_format='%.17g').encode()).hexdigest() for name,group in trials.groupby('algorithm')}
    metrics['trajectory_fingerprint']=metrics.algorithm.map(trajectories)
    population=pd.DataFrame([asdict(p) for p in passengers])
    population['population_seed']=config.population_seed; population['feedback_noise']=config.feedback_noise
    calibration=pd.DataFrame(trials.attrs['calibration_observations'],columns=sim.CALIBRATION_FIELDS)
    calibration.insert(0,'calibration_trial',range(1,len(calibration)+1))
    calibration.insert(0,'scenario',config.scenario_name)
    calibration['calibration_seed']=config.calibration_seed
    return metrics,participant,population,calibration


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['all',*SUITES],default='all')
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    parser.add_argument('--population-blocks',type=int,default=5)
    parser.add_argument('--process-repeats',type=int,default=2)
    args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
    specs=build_scenarios(args.population_blocks,args.process_repeats)
    for suite in (SUITES if args.suite=='all' else [args.suite]):
        selected=[s for s in specs if s.suite==suite]; outputs=[[],[],[],[]]
        for index,spec in enumerate(selected,start=1):
            print(f'[{suite} {index}/{len(selected)}] {spec.config.scenario_name}',flush=True)
            for frames,frame in zip(outputs,execute(spec)): frames.append(frame)
        for frames,kind in zip(outputs,('per_run','participants','populations','calibration')):
            nonempty=[frame for frame in frames if not frame.empty]
            combined=pd.concat(nonempty,ignore_index=True) if nonempty else frames[0].copy()
            if kind=='populations': combined=combined.drop_duplicates().sort_values(['population_seed','participant_id'])
            combined.to_csv(args.output_dir/f'{suite}_{kind}.csv',index=False,encoding='utf-8-sig')
        manifest={'suite':suite,'population_blocks':args.population_blocks,'process_repeats':args.process_repeats,
            'scenarios':[{'population_block':s.population_block,'process_repeat':s.process_repeat,
                          'config':asdict(s.config)} for s in selected]}
        (args.output_dir/f'{suite}_configurations.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(f'WROTE {suite}: {len(selected)} scenarios, {len(selected)*5} policy summaries',flush=True)


if __name__=='__main__': main()
