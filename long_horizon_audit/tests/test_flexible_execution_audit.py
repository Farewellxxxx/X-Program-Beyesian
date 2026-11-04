from dataclasses import replace
import argparse
import importlib
import importlib.util

import pandas as pd
import pytest

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim
from comfort_boundary_bo_research_package.simulation import flexible_execution as model
from long_horizon_audit.scripts import run_execution_robustness_audit as old


def module(name):
    name='long_horizon_audit.scripts.'+name
    assert importlib.util.find_spec(name) is not None, 'Missing '+name
    return importlib.import_module(name)


def tiny_spec():
    s=next(s for s in old.build_scenarios() if s.profile=='combined_high' and s.arm=='cal8')
    return replace(s,config=replace(s.config,n_participants=2,n_trials=2,mc_samples=5,candidate_count=5))


def test_cli_selector_exports_fit_and_preserves_old_output_defaults(tmp_path,monkeypatch):
    parser=argparse.ArgumentParser(); sim.add_execution_cli_arguments(parser)
    assert parser.parse_args([]).execution_estimator=='simple'
    assert parser.parse_args(['--execution-estimator','quadratic_covariance']).execution_estimator==model.ESTIMATOR
    assert sim.default_output_dir('monotone_bayes','calibrated').name=='outputs_execution_separated'
    assert sim.default_output_dir('monotone_bayes','calibrated',execution_estimator=model.ESTIMATOR).name=='outputs_flexible_execution'
    monkeypatch.setattr(sim,'save_plots',lambda *args:None)
    c=tiny_spec().config
    frames=sim.run_configurations([c],tmp_path,execution_estimator=model.ESTIMATOR)
    for frame in frames:
        assert frame.execution_estimator.eq(model.ESTIMATOR).all()
        assert frame.fit_settings_fingerprint.eq(model.FitSettings().fingerprint()).all()
    fit=pd.read_csv(tmp_path/'continuous_execution_fit.csv')
    assert len(fit)==1 and fit.calibration_n_observations.iloc[0]==8
    with pytest.raises(ValueError): sim.run_configurations([replace(c,execution_belief='oracle')],tmp_path,execution_estimator=model.ESTIMATOR)
    with pytest.raises(ValueError): sim.run_configurations([c],tmp_path,execution_estimator='unknown')


def test_complete_design_keeps_original_configs_and_fixed_settings():
    audit=module('run_flexible_execution_audit')
    specs=audit.build_scenarios()
    assert len(specs)==280
    assert specs==[s for s in old.build_scenarios() if s.arm.startswith('cal')]
    assert audit.manifest(specs[:1],5,2)['fit_settings']==vars(model.FitSettings())


def test_bundle_rejects_missing_cells_changed_observations_or_fits():
    audit=module('run_flexible_execution_audit'); compare=module('compare_flexible_execution')
    spec=tiny_spec(); outputs=audit.execute(spec,diagnostic_samples=64)
    before=old.prepare(spec).calibration_observations.copy()
    before['scenario']=spec.config.scenario_name; before['calibration_trial']=range(1,len(before)+1)
    compare.validate_bundle(outputs[0],outputs[3],outputs[4],outputs[5],before,[spec],64)
    pd.testing.assert_frame_equal(outputs[3][sim.CALIBRATION_FIELDS],before[sim.CALIBRATION_FIELDS])
    mutations=[(0,outputs[0].iloc[:-1]),(0,outputs[0].assign(fit_settings_fingerprint='wrong')),
               (0,outputs[0].assign(process_seed=1)),(4,outputs[4].iloc[:-1]),
               (5,outputs[5].assign(fit_gain=999.))]
    changed=outputs[3].copy(); changed.loc[0,'peak_accel']+=.001; mutations.append((3,changed))
    for index,frame in mutations:
        bad=list(outputs); bad[index]=frame
        with pytest.raises(ValueError): compare.validate_bundle(bad[0],bad[3],bad[4],bad[5],before,[spec],64)
    missing=replace(spec,config=replace(spec.config,scenario_name='missing'))
    with pytest.raises(ValueError): compare.validate_bundle(outputs[0],outputs[3],outputs[4],outputs[5],before,[spec,missing],64)


def test_replay_is_exact_and_rejects_incomplete_or_modified_results():
    audit=module('run_flexible_execution_audit'); compare=module('compare_flexible_execution')
    spec=tiny_spec()
    expected=old.execute(spec,diagnostic_samples=32)[0]; replay=audit.execute_replay(spec)
    assert compare.validate_replay(expected,replay)==0
    for bad in (replay.iloc[:-1],replay.assign(mean_boundary_error=0.)):
        with pytest.raises(ValueError): compare.validate_replay(expected,bad)


def test_pairing_rejects_mismatched_calibration_observation_hash():
    compare=module('compare_flexible_execution')
    frame=pd.DataFrame(dict(population_block=[1,2],process_repeat=[1,1],calibration_fingerprint=['a','b']))
    compare.validate_observation_pairs(frame,frame.copy())
    with pytest.raises(ValueError): compare.validate_observation_pairs(frame,frame.assign(calibration_fingerprint='changed'))
