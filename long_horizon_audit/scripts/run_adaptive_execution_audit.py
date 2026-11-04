"""Paired adaptive execution study, fixed-quadratic replay and predictive ablations."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from comfort_boundary_bo_research_package.simulation import adaptive_execution as model
from comfort_boundary_bo_research_package.simulation import execution_predictive_diagnostics as diagnostic
from long_horizon_audit.scripts import run_flexible_execution_audit as baseline
old=baseline.old
OUTPUT=ROOT/'long_horizon_audit/derived/adaptive_execution_20261104'
SETTINGS=model.core.PosteriorSettings()
VARIANTS=('quadratic_covariance',*model.MODES,'oracle')
SENSITIVITY={'default':SETTINGS,'draws8192':replace(SETTINGS,posterior_draws=8192),
    'prior2x':replace(SETTINGS,bias_prior_sd=1.,gain_prior_sd=1.,quadratic_prior_sd=1.5)}
build_scenarios=baseline.build_scenarios


def sensitivity_specs():
    return [s for s in build_scenarios() if s.population_block==1 and s.process_repeat==1 and s.arm in ('cal8','cal40')]


def manifest(specs,blocks=5,repeats=2,replay=False):
    return dict(population_blocks=blocks,process_repeats=repeats,execution_estimator='quadratic_covariance_replay' if replay else model.ESTIMATOR,
        posterior_settings=asdict(SETTINGS),posterior_settings_fingerprint=SETTINGS.fingerprint(),
        diagnostic_samples=0 if replay else 4096,holdout_namespace=diagnostic.HOLDOUT_NAMESPACE,
        variants=[] if replay else list(VARIANTS),scenarios=[asdict(s) for s in specs])


def prediction_models(prepared):
    posterior=prepared.belief.posterior; public=prepared.belief.config
    fitted=baseline.model.fit_flexible_execution(prepared.calibration_observations,public)
    return {'quadratic_covariance':baseline.model.FlexibleExecutionModel(public,fitted.parameters),
        **{mode:model.PosteriorExecutionModel(public,posterior,mode) for mode in model.MODES},'oracle':prepared.truth}


def variant_metadata(variant,belief,prepared):
    if variant=='oracle':
        identity=dict(parameters=asdict(belief.parameters),distortion=asdict(getattr(belief,'distortion',old.stress.Distortion())))
    elif variant=='quadratic_covariance': identity=asdict(belief.fit_parameters)
    else: identity=dict(draws=belief.posterior.draw_fingerprint,settings=belief.posterior.settings.fingerprint(),mode=variant)
    obs=prepared.calibration_observations
    mean=np.array([belief.nominal_features(x)['target_nominal_peak_accel'] for x in obs.target_command_x])
    return dict(variant=variant,variant_fingerprint=model.core.fingerprint(identity),
        training_accel_mean_rmse=float(np.sqrt(np.mean((mean-obs.peak_accel.to_numpy())**2))))


def metadata_for(spec,prepared):
    return {**old.expected_metadata(spec),**prepared.metadata,
        'calibration_fingerprint':baseline.observation_fingerprint(prepared.calibration_observations)}


def attach(frame,metadata):
    # Rebuild once instead of repeatedly fragmenting wide provenance tables.
    return pd.concat([frame.drop(columns=list(set(frame.columns)&set(metadata))),
        pd.DataFrame([metadata]*len(frame),index=frame.index)],axis=1)


def execute(spec,diagnostic_samples=4096):
    prepared=model.upgrade_prepared(old.prepare(spec),SETTINGS); metadata=metadata_for(spec,prepared)
    base=old.previous.ScenarioSpec('robustness',spec.population_block,spec.process_repeat,spec.config)
    metrics,participants,population,calibration=old.previous.execute(base,prepared)
    diags=[]
    for variant,belief in prediction_models(prepared).items():
        probe=old.sim.PreparedExecution(prepared.truth,belief,prepared.calibration_observations,prepared.metadata)
        rows=diagnostic.predictive_diagnostics(probe,spec.config.calibration_seed,diagnostic_samples)
        diags.append(attach(rows,{**metadata,**variant_metadata(variant,belief,prepared)}))
    return (attach(metrics,metadata),attach(participants,metadata),population,attach(calibration,metadata),
        pd.concat(diags,ignore_index=True),pd.DataFrame([metadata]))


def execute_replay(spec):
    return baseline.execute(spec,32)[0]


def execute_sensitivity(spec):
    original=old.prepare(spec); diags=[]; fits=[]
    for name,settings in SENSITIVITY.items():
        prepared=model.upgrade_prepared(original,settings)
        metadata={**metadata_for(spec,prepared),'sensitivity':name}
        rows=diagnostic.predictive_diagnostics(prepared,spec.config.calibration_seed)
        diags.append(attach(rows,{**metadata,**variant_metadata(model.ESTIMATOR,prepared.belief,prepared)}))
        fits.append(metadata)
    return pd.concat(diags,ignore_index=True),pd.DataFrame(fits)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['all','adaptive','replay','sensitivity'],default='all')
    parser.add_argument('--profile',choices=['all',*old.PROFILES],default='all')
    parser.add_argument('--workers',type=int,default=1); parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=parser.parse_args()
    if not 1<=args.workers<=8: parser.error('workers must be between 1 and 8')
    args.output_dir.mkdir(parents=True,exist_ok=True); started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for suite in (['adaptive','replay','sensitivity'] if args.suite=='all' else [args.suite]):
            if suite=='sensitivity':
                specs=sensitivity_specs(); outputs=list(pool.map(execute_sensitivity,specs))
                old.save_frames(outputs,'sensitivity',args.output_dir,('diagnostics','fits'))
                (args.output_dir/'sensitivity_configurations.json').write_text(json.dumps(dict(
                    settings={k:asdict(v) for k,v in SENSITIVITY.items()},scenarios=[asdict(s) for s in specs],diagnostic_samples=4096),indent=2),encoding='utf-8')
                print('WROTE sensitivity: 14 paired cells',flush=True); continue
            for profile in (list(old.PROFILES) if args.profile=='all' else [args.profile]):
                replay=suite=='replay'; specs=[s for s in build_scenarios() if s.profile==profile]; outputs=[]
                for index,result in enumerate(pool.map(execute_replay if replay else execute,specs),1):
                    outputs.append(result); print(f'[{suite}/{profile} {index}/{len(specs)}] elapsed={time.perf_counter()-started:.1f}s',flush=True)
                prefix='replay_'+profile if replay else profile
                if replay: pd.concat(outputs,ignore_index=True).to_csv(args.output_dir/f'{prefix}_per_run.csv',index=False,encoding='utf-8-sig')
                else: old.save_frames(outputs,prefix,args.output_dir,('per_run','participants','populations','calibration','diagnostics','fits'))
                (args.output_dir/f'{prefix}_configurations.json').write_text(json.dumps(manifest(specs,replay=replay),indent=2),encoding='utf-8')
                print(f'WROTE {prefix}: {len(specs)} scenarios',flush=True)


if __name__=='__main__': main()
