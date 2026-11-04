from dataclasses import replace
import importlib
import importlib.util

import numpy as np
import pandas as pd
import pytest


def module(name):
    path='long_horizon_audit.scripts.'+name
    assert importlib.util.find_spec(path) is not None, name+' is missing'
    return importlib.import_module(path)


def test_complete_robustness_grid_and_actual_stream_identities():
    audit=module('run_execution_robustness_audit'); compare=module('compare_execution_robustness')
    specs=audit.build_scenarios()
    assert len(specs)==420
    assert len({s.config.scenario_name for s in specs})==420
    assert {s.arm for s in specs}=={'oracle','nominal','cal8','cal20','cal40','cal160'}
    assert len({s.config.population_seed for s in specs})==5
    assert compare.verify_streams(specs)==9360
    for count in (1,11):
        with pytest.raises(ValueError): audit.build_scenarios(population_blocks=count)
    with pytest.raises(ValueError): audit.build_scenarios(process_repeats=10)


def test_real_output_metadata_and_completeness_guard():
    audit=module('run_execution_robustness_audit'); compare=module('compare_execution_robustness')
    spec=next(s for s in audit.build_scenarios() if s.profile=='combined_high' and s.arm=='cal8')
    spec=replace(spec,config=replace(spec.config,n_participants=1,n_trials=2,mc_samples=5,candidate_count=5))
    outputs=audit.execute(spec,diagnostic_samples=64)
    frame=outputs[0]; compare.validate_results(frame,[spec])
    assert frame.calibration_n_observations.eq(8).all()
    assert len(outputs[4])==21
    for bad in (frame.iloc[:-1],pd.concat([frame,frame.iloc[:1]]),frame.assign(process_seed=7),
                frame.assign(truth_fingerprint='wrong'),frame.assign(mean_boundary_error=np.nan)):
        with pytest.raises(ValueError): compare.validate_results(bad,[spec])
    other=replace(spec,config=replace(spec.config,scenario_name='missing-whole-scenario'))
    with pytest.raises(ValueError): compare.validate_results(frame,[spec,other])


def test_paired_difference_uses_batch_means_and_rejects_mispairing():
    compare=module('compare_execution_robustness')
    frame=pd.DataFrame(dict(population_block=[1,1,2,2],process_repeat=[1,2,1,2],
        population_seed=[101,101,102,102],process_seed=[1,2,3,4],calibration_seed=[11,12,13,14],
        process_rng_mode=['independent']*4,truth_fingerprint=['truth']*4,policy_fingerprint=['policy']*4,
        population_fingerprint=['a','a','b','b'],n_participants=[24]*4,
        n_trials_per_algorithm_participant=[12]*4,algorithm=['UncertainInputBO']*4,value=[0.,0.,0.,0.]))
    new=frame.copy(); new['value']=[0.,2.,2.,4.]
    result=compare.paired_difference(frame,new,'value')
    assert result['mean_change']==2
    assert result['ci95_low']==pytest.approx(2-12.706)
    assert result['n_population_blocks']==2
    for bad in (new.iloc[:-1],new.assign(process_seed=1),new.assign(truth_fingerprint='wrong')):
        with pytest.raises(ValueError): compare.paired_difference(frame,bad,'value')


def test_calibration_validation_rejects_replaced_prefix_or_missing_observations():
    audit=module('run_execution_robustness_audit'); compare=module('compare_execution_robustness')
    specs=[s for s in audit.build_scenarios() if s.profile=='gain_high' and s.population_block==1 and s.process_repeat==1]
    frames=[]
    for s in specs:
        if not s.arm.startswith('cal'): continue
        p=audit.prepare(s); frame=p.calibration_observations.copy()
        frame['scenario']=s.config.scenario_name; frame['calibration_trial']=range(1,len(frame)+1)
        frames.append(frame)
    frame=pd.concat(frames,ignore_index=True)
    assert compare.validate_calibration(frame,specs)==4
    with pytest.raises(ValueError): compare.validate_calibration(frame.iloc[:-1],specs)
    changed=frame.copy(); changed.loc[0,'peak_accel']+=.001
    with pytest.raises(ValueError): compare.validate_calibration(changed,specs)


def test_holdout_manifest_rejects_missing_grid_and_wrong_diagnostic_seed():
    audit=module('run_execution_robustness_audit'); compare=module('compare_execution_robustness')
    spec=audit.build_scenarios()[0]
    diagnostics=audit.diagnose(spec,audit.prepare(spec),64)
    compare.validate_diagnostics(diagnostics,[spec],64)
    for bad in (diagnostics.iloc[:-1],diagnostics.assign(diagnostic_seed=1),diagnostics.assign(region='interior'),
                diagnostics.assign(wasserstein1=float('nan'))):
        with pytest.raises(ValueError): compare.validate_diagnostics(bad,[spec],64)
