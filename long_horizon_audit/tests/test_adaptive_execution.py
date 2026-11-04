from dataclasses import replace
import importlib
import importlib.util
import numpy as np
import pandas as pd
import pytest
from long_horizon_audit.tests.test_flexible_execution import fixture
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim
from comfort_boundary_bo_research_package.simulation import execution_misspecification as stress
from comfort_boundary_bo_research_package.simulation import execution_posterior as core


def module():
    name='comfort_boundary_bo_research_package.simulation.adaptive_execution'
    assert importlib.util.find_spec(name), 'Posterior predictive adapter is missing'
    return importlib.import_module(name)


def test_predictive_variance_contains_mean_uncertainty_and_matches_total_variance():
    m=module(); public=sim.ExecutionSettings(); posterior=core.fit_execution_posterior(fixture(coefficients=(0,0,0)),public)
    plugin=m.PosteriorExecutionModel(public,posterior,'adaptive_plugin')
    full=m.PosteriorExecutionModel(public,posterior,'adaptive_posterior'); x=.7; d=x-1.125; h=np.array([1,d,d*d])
    mean,cov=posterior.moments(); means=np.array([c.coefficients@h for c in posterior.components]); w=posterior.weights
    epistemic=float(w@(means**2).mean(1)-(w@means.mean(1))**2)
    sa=.045+.055*(x-.35)/1.55
    actual=full._channels(x,np.random.default_rng(942),150000)[1]
    assert actual.var()==pytest.approx(sa**2*cov[0,0]+epistemic,rel=.025)
    assert actual.var()>plugin._channels(x,np.random.default_rng(942),150000)[1].var()
    assert full.fit_parameters==plugin.fit_parameters


def test_adapter_uses_only_observations_keeps_truth_and_fixed_trajectories():
    m=module(); c=sim.Config(n_participants=2,n_trials=4,mc_samples=8,candidate_count=7)
    old=stress.prepare_stress_execution(c,stress.Distortion(.25,.45,.75)); new=m.upgrade_prepared(old)
    changed=stress.prepare_stress_execution(replace(c,execution_noise='high',calibration_bias=-.1),stress.Distortion(),old.calibration_observations)
    assert m.upgrade_prepared(changed).belief.posterior.draw_fingerprint==new.belief.posterior.draw_fingerprint
    assert new.truth is old.truth and not hasattr(new.belief.config,'calibration_bias')
    before=sim.run_scenario(c,sim.make_passengers(c),old); after=sim.run_scenario(c,sim.make_passengers(c),new)
    fixed=['RandomContinuous','GridContinuous','Staircase']; cols=['target_command_x','peak_accel','peak_jerk','duration_s','acceptable']
    pd.testing.assert_frame_equal(before[before.algorithm.isin(fixed)][cols],after[after.algorithm.isin(fixed)][cols])
    assert 'fit_weight_0' in sim.evaluate(after)[1]
    pd.testing.assert_frame_equal(sim.prepare_execution(c).calibration_observations,m.prepare_adaptive_execution(c).calibration_observations)


def test_scalar_vector_time_effects_and_output_paths():
    m=module(); public=sim.ExecutionSettings(include_time_effects=True)
    posterior=core.fit_execution_posterior(fixture(),public)
    model=m.PosteriorExecutionModel(public,posterior,'adaptive_posterior'); rng=np.random.default_rng(12)
    scalar=np.array([model.sample_features(1.3,rng,.5)['realized_intensity'] for _ in range(3000)])
    vector=model.sample_many(1.3,np.random.default_rng(32),60000,.5)[0]
    assert scalar.mean()==pytest.approx(vector.mean(),abs=.01)
    assert scalar.std()==pytest.approx(vector.std(),abs=.01)
    paths=[sim.default_output_dir(s,'calibrated',p,execution_estimator=e) for s in ['monotone_bayes','legacy_kernel'] for p in [False,True] for e in ['simple','quadratic_covariance','adaptive_posterior']]
    assert len(set(paths))==12
    for invalid in [0,True,1.5]:
        with pytest.raises(ValueError): model.sample_many(1.,rng,invalid)


def test_interval_score_and_independent_holdout_reproduces_direct_calculation():
    module(); name='comfort_boundary_bo_research_package.simulation.execution_predictive_diagnostics'
    assert importlib.util.find_spec(name), 'Independent predictive diagnostics are missing'
    diag=importlib.import_module(name)
    assert diag.interval_score(np.array([-1,1,3]),0,2)==pytest.approx(46/3)
    c=sim.Config(execution_belief='oracle'); prepared=sim.prepare_execution(c); seed=128
    rows=diag.predictive_diagnostics(prepared,seed,256)
    assert len(rows)==21
    row=rows.iloc[0]
    future=prepared.truth.sample_many(float(row.command),np.random.default_rng(np.random.SeedSequence([diag.HOLDOUT_NAMESPACE,0,seed])),256)[0]
    assert row.holdout_interval90_coverage==((future>=row.interval90_lower)&(future<=row.interval90_upper)).mean()
    assert row.interval90_score==diag.interval_score(future,row.interval90_lower,row.interval90_upper)
    assert diag.HOLDOUT_NAMESPACE!=0xD1A6
    # Oracle intervals no longer get artificially identical prediction/target samples.
    assert not np.allclose(rows.holdout_interval90_coverage,rows.interval90_coverage)
