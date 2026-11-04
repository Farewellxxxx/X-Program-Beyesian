"""Catch truth leakage, wrong covariance, nonnested budgets and sampler mismatch."""
from dataclasses import replace
import importlib
import importlib.util

import numpy as np
import pandas as pd
import pytest

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim


def module():
    name='comfort_boundary_bo_research_package.simulation.execution_misspecification'
    assert importlib.util.find_spec(name) is not None, 'Stress execution module is missing'
    return importlib.import_module(name)


def test_distortion_mean_and_validation():
    m=module()
    for values in ({'gain':float('nan')},{'quadratic':float('inf')},{'correlation':1.0},{'correlation':-1.1}):
        with pytest.raises(ValueError): m.Distortion(**values)
    truth=m.make_truth(sim.ExecutionSettings(),sim.ExecutionParameters(.15,1.55),m.Distortion(.25,.45,.75))
    assert truth.nominal_features(1.5)['target_nominal_peak_accel']==pytest.approx(1.76703125)
    assert truth.nominal_features(1.125)['target_nominal_peak_accel']==pytest.approx(1.2575)


def test_zero_distortion_is_exact_original_generator():
    m=module(); settings=sim.ExecutionSettings(); pars=sim.ExecutionParameters(.15,1.55)
    truth=m.make_truth(settings,pars,m.Distortion()); old=sim.ContinuousExecutionModel(settings,pars)
    a=np.random.default_rng(13); b=np.random.default_rng(13)
    for x in (.35,1.0,1.9): assert truth.sample_features(x,a)==old.sample_features(x,b)
    for actual,expected in zip(truth.sample_many(1.3,a,400),old.sample_many(1.3,b,400)):
        np.testing.assert_array_equal(actual,expected)


def test_standardized_residual_covariance_matches_specification():
    m=module(); rho=.75; x=1.0
    truth=m.make_truth(sim.ExecutionSettings(),sim.ExecutionParameters(0,.65),m.Distortion(correlation=rho))
    z=truth.sample_feature_arrays(x,np.random.default_rng(555),100000)
    level=(x-.35)/1.55
    a=(z['peak_accel']-(.05+.94*x))/((.045+.055*level)*.65)
    j=(z['peak_jerk']-(.58+1.74*z['peak_accel']+.10*x))/((.18+.24*level)*.65)
    d=(z['duration_s']-(3.90-.30*z['peak_accel']))/(.18*.65)
    cov=np.corrcoef([a,j,d])
    assert cov[0,1]==pytest.approx(.75,abs=.008)
    assert cov[0,2]==pytest.approx(.75,abs=.008)
    assert cov[1,2]==pytest.approx(.5625,abs=.008)
    assert np.std(a)==pytest.approx(1,abs=.012)
    assert np.std(j)==pytest.approx(1,abs=.012)


def test_scalar_and_vector_intensity_have_same_distribution():
    m=module(); settings=sim.ExecutionSettings(include_time_effects=True)
    truth=m.make_truth(settings,sim.ExecutionParameters(.15,1.55),m.Distortion(.25,.45,.75))
    rng=np.random.default_rng(998)
    scalar=np.array([truth.sample_features(1.6,rng)['realized_intensity'] for _ in range(3000)])
    vector,_=truth.sample_many(1.6,np.random.default_rng(997),60000)
    assert scalar.mean()==pytest.approx(vector.mean(),abs=.015)
    assert scalar.std()==pytest.approx(vector.std(),abs=.015)


def test_calibration_budgets_are_exact_prefixes_and_do_not_read_truth():
    m=module(); c=sim.Config(calibration_trials=8); distortion=m.Distortion(.25,.45,.75)
    small=m.prepare_stress_execution(c,distortion)
    large=m.prepare_stress_execution(replace(c,calibration_trials=160),distortion)
    pd.testing.assert_frame_equal(small.calibration_observations,large.calibration_observations.iloc[:8])
    observed=small.calibration_observations
    other=m.prepare_stress_execution(replace(c,calibration_bias=-.2,execution_noise='high'),m.Distortion(),observed)
    assert small.belief.parameters==other.belief.parameters
    assert type(small.belief) is sim.ContinuousExecutionModel
    assert not hasattr(small.belief,'distortion')
    assert small.metadata['calibration_n_observations']==8
    assert large.metadata['calibration_n_observations']==160


def test_full_oracle_uses_true_shape_but_separate_objects():
    m=module(); c=sim.Config(execution_belief='oracle'); p=m.prepare_stress_execution(c,m.Distortion(.25,.45,.75))
    assert p.truth is not p.belief
    for a,b in zip(p.truth.sample_many(1.5,np.random.default_rng(99),1000),p.belief.sample_many(1.5,np.random.default_rng(99),1000)):
        np.testing.assert_array_equal(a,b)
    d=m.distribution_diagnostics(p,123,n_samples=512)
    assert d.mean_abs_error.max()==0
    assert d.wasserstein1.max()==0
    assert d.command.nunique()==21
    assert set(d.region)=={'interior','extrapolation'}


def test_stress_runner_uses_supplied_truth_and_fixed_policies_ignore_belief():
    m=module(); c=sim.Config(n_participants=2,n_trials=4,mc_samples=8,candidate_count=7)
    distortion=m.Distortion(.25,.45,.75)
    a=sim.run_scenario(c,sim.make_passengers(c),prepared=m.prepare_stress_execution(c,distortion))
    oracle=replace(c,execution_belief='oracle')
    b=sim.run_scenario(oracle,sim.make_passengers(oracle),prepared=m.prepare_stress_execution(oracle,distortion))
    cols=['target_command_x','peak_accel','peak_jerk','duration_s','acceptable']
    fixed=['RandomContinuous','GridContinuous','Staircase']
    pd.testing.assert_frame_equal(a[a.algorithm.isin(fixed)][cols],b[b.algorithm.isin(fixed)][cols])
    old=sim.run_scenario(c,sim.make_passengers(c))
    assert not a.peak_accel.equals(old.peak_accel)


def test_nested_command_prefix_is_budget_independent():
    m=module(); settings=sim.ExecutionSettings()
    np.testing.assert_allclose(m.nested_commands(settings,4),[1.125,.8925,1.3575,.77625])
    np.testing.assert_array_equal(m.nested_commands(settings,8),m.nested_commands(settings,160)[:8])
    with pytest.raises(ValueError): m.nested_commands(settings,0)
