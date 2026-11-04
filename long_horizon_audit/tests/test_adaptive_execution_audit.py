from dataclasses import replace
import importlib
import importlib.util
import pandas as pd
import pytest
from long_horizon_audit.tests.test_flexible_execution_audit import tiny_spec
from long_horizon_audit.scripts import run_flexible_execution_audit as baseline
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim


def module(name):
    name='long_horizon_audit.scripts.'+name
    assert importlib.util.find_spec(name), 'Missing '+name
    return importlib.import_module(name)


def test_design_replay_and_sensitivity_cells_are_fixed():
    audit=module('run_adaptive_execution_audit'); compare=module('compare_adaptive_execution')
    assert audit.build_scenarios()==baseline.build_scenarios()
    assert len(audit.build_scenarios())==280 and len(audit.sensitivity_specs())==14
    assert len(audit.VARIANTS)==6
    spec=tiny_spec(); expected=baseline.execute(spec,32)[0]; replay=audit.execute_replay(spec)
    compare.previous.validate_replay(expected,replay)


def test_complete_bundle_rejects_missing_variants_scenarios_corruption_and_wrong_holdout():
    audit=module('run_adaptive_execution_audit'); compare=module('compare_adaptive_execution')
    spec=tiny_spec(); frames=audit.execute(spec,64)
    reference=baseline.old.prepare(spec).calibration_observations.copy()
    reference['scenario']=spec.config.scenario_name; reference['calibration_trial']=range(1,len(reference)+1)
    assert compare.validate_bundle(frames[0],frames[3],frames[4],frames[5],reference,[spec],64)==1
    mutations=[(0,frames[0].iloc[:-1]),(0,frames[0].assign(fit_draw_fingerprint='wrong')),
        (4,frames[4][frames[4].variant!='oracle']),(4,frames[4].iloc[:-1]),(4,frames[4].assign(holdout_namespace=0)),
        (4,frames[4].assign(interval90_width=-1)),(5,frames[5].assign(fit_weight_0=.123)),
        (5,frames[5].assign(fit_gain=900.))]
    for index,frame in mutations:
        bad=list(frames); bad[index]=frame
        with pytest.raises(ValueError): compare.validate_bundle(bad[0],bad[3],bad[4],bad[5],reference,[spec],64)
    missing=replace(spec,config=replace(spec.config,scenario_name='missing'))
    with pytest.raises(ValueError): compare.validate_bundle(frames[0],frames[3],frames[4],frames[5],reference,[spec,missing],64)


def test_cli_exports_model_weights_and_posterior_hash(tmp_path,monkeypatch):
    module('run_adaptive_execution_audit'); monkeypatch.setattr(sim,'save_plots',lambda *a:None)
    c=tiny_spec().config
    trials,participants,metrics=sim.run_configurations([c],tmp_path,execution_estimator='adaptive_posterior')
    for frame in (trials,participants,metrics,pd.read_csv(tmp_path/'continuous_execution_fit.csv')):
        assert frame.execution_estimator.eq('adaptive_posterior').all()
        assert frame.fit_weight_0.notna().all() and frame.fit_draw_fingerprint.str.len().eq(64).all()
    with pytest.raises(ValueError): sim.run_configurations([replace(c,execution_belief='oracle')],tmp_path,execution_estimator='adaptive_posterior')
