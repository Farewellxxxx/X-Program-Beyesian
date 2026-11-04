"""Independent numerical fixtures for the richer observation-only estimator."""
from dataclasses import replace
import importlib
import importlib.util

import numpy as np
import pandas as pd
import pytest

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim
from comfort_boundary_bo_research_package.simulation import execution_misspecification as stress


def module():
    name='comfort_boundary_bo_research_package.simulation.flexible_execution'
    assert importlib.util.find_spec(name) is not None, 'Flexible execution estimator is missing'
    return importlib.import_module(name)


def fixture(coefficients=(.12,.25,.45),noise=.4):
    x=np.repeat([.6,1.1,1.6],4); d=x-1.125; level=(x-.35)/1.55
    # Within each command these four residual vectors have zero sums and unit
    # second moments. Thus all three weighted design projections vanish.
    ua=np.tile([-1.,-1.,1.,1.],3)
    uj=np.tile([-1.,1.,-1.,1.],3)
    ud=np.tile([1.,-1.,-1.,1.],3)
    za=ua; zj=.5*ua+np.sqrt(.75)*uj; zd=-.25*ua+np.sqrt(.9375)*ud
    b,g,q=coefficients
    a=.05+.94*x+b+g*d+q*d*d+(.045+.055*level)*noise*za
    j=.58+1.74*a+.10*x+(.18+.24*level)*noise*zj
    t=3.90-.30*a+.18*noise*zd
    return pd.DataFrame(dict(target_command_x=x,peak_accel=a,peak_jerk=j,duration_s=t))


def test_fit_matches_independent_weighted_ridge_and_covariance_fixture():
    m=module(); fit=m.fit_flexible_execution(fixture(),sim.ExecutionSettings())
    np.testing.assert_allclose(fit.parameters.coefficients,
        [.12075737295336854,.24867787452426224,.444355779964395],rtol=0,atol=1e-11)
    # Raw residual cross-products / (12-3), then 25% shrinkage toward diagonal.
    want=np.array([[.2133333433333333,.08,-.04],[.08,.2133333433333333,-.02],[-.04,-.02,.2133333433333333]])
    np.testing.assert_allclose(fit.parameters.covariance,want,rtol=0,atol=1e-11)
    assert fit.n_used==12 and fit.n_clipped==0 and fit.residual_dof==9
    assert fit.covariance_shrinkage==.25


def test_noiseless_quadratic_recovers_coefficients_with_finite_sampling_covariance():
    m=module(); fit=m.fit_flexible_execution(fixture(noise=0),sim.ExecutionSettings())
    np.testing.assert_allclose(fit.parameters.coefficients,[.12,.25,.45],atol=1e-8)
    assert np.linalg.eigvalsh(fit.parameters.covariance).min()>0


@pytest.mark.parametrize('coefficients,active',[( (.1,-.5,1.),('lower',)),((.1,-.5,-1.),('upper',)),((.9,-1.5,0.),('lower','upper'))])
def test_constraint_solver_enforces_global_monotonicity(coefficients,active):
    m=module(); fit=m.fit_flexible_execution(fixture(coefficients,noise=0),sim.ExecutionSettings())
    b,g,q=fit.parameters.coefficients
    assert .94+g-1.55*q>=-1e-9 and .94+g+1.55*q>=-1e-9
    assert set(fit.active_constraints)==set(active)
    model=m.FlexibleExecutionModel(sim.ExecutionSettings(),fit.parameters)
    values=[model.nominal_features(x)['target_nominal_peak_accel'] for x in np.linspace(.35,1.9,301)]
    assert np.diff(values).min()>=-1e-10


def test_fitter_rejects_invalid_or_unidentifiable_observations_and_counts_clipping():
    m=module(); good=fixture()
    bads=[good.iloc[:7],good.drop(columns='duration_s'),good.assign(peak_jerk=np.nan),
          good.assign(target_command_x=1.1),good.assign(target_command_x=2.0),good.assign(duration_s=8.)]
    for bad in bads:
        with pytest.raises(ValueError): m.fit_flexible_execution(bad,sim.ExecutionSettings())
    clipped=good.copy(); clipped.loc[0,'peak_accel']=.20
    fit=m.fit_flexible_execution(clipped,sim.ExecutionSettings())
    assert (fit.n_observations,fit.n_used,fit.n_clipped)==(12,11,1)
    for field in ['bias_prior_sd','gain_prior_sd','quadratic_prior_sd','covariance_pseudocount','covariance_floor']:
        with pytest.raises(ValueError): m.FitSettings(**{field:0})
    with pytest.raises(ValueError): m.FlexibleParameters((0,0,0),((1,2,0),(2,1,0),(0,0,1)))


def test_sampler_supports_unequal_scales_and_asymmetric_correlations():
    m=module(); covariance=np.array([[.16,.04,-.02],[.04,.24,.03],[-.02,.03,.12]])
    params=m.FlexibleParameters((.12,.25,.45),tuple(map(tuple,covariance)))
    model=m.FlexibleExecutionModel(sim.ExecutionSettings(),params); x=.9
    arrays=model.sample_feature_arrays(x,np.random.default_rng(391),100000)
    level=(x-.35)/1.55; d=x-1.125
    a=(arrays['peak_accel']-(.05+.94*x+.12+.25*d+.45*d*d))/(.045+.055*level)
    j=(arrays['peak_jerk']-(.58+1.74*arrays['peak_accel']+.1*x))/(.18+.24*level)
    t=(arrays['duration_s']-(3.90-.30*arrays['peak_accel']))/.18
    np.testing.assert_allclose(np.cov([a,j,t],bias=True),covariance,atol=.003)


def test_scalar_vector_moments_match_including_time_effects():
    m=module(); settings=sim.ExecutionSettings(include_time_effects=True)
    params=m.FlexibleParameters((.15,.25,.45),((2.4,1.7,1.5),(1.7,2.5,1.2),(1.5,1.2,2.2)))
    model=m.FlexibleExecutionModel(settings,params)
    rng=np.random.default_rng(984)
    scalar=np.array([model.sample_features(1.4,rng,.3)['realized_intensity'] for _ in range(3000)])
    vector,_=model.sample_many(1.4,np.random.default_rng(23),60000,.3)
    assert scalar.mean()==pytest.approx(vector.mean(),abs=.015)
    assert scalar.std()==pytest.approx(vector.std(),abs=.015)


def test_upgrade_uses_only_observations_without_mutating_the_old_world():
    m=module(); c=sim.Config(calibration_trials=40)
    old=stress.prepare_stress_execution(c,stress.Distortion(.25,.45,.75))
    old_parameters=old.belief.parameters; old_metadata=old.metadata.copy()
    new=m.upgrade_prepared(old)
    assert old.belief.parameters==old_parameters and old.metadata==old_metadata
    assert new.truth is old.truth and new.belief is not old.belief
    pd.testing.assert_frame_equal(new.calibration_observations,old.calibration_observations)
    changed=stress.prepare_stress_execution(replace(c,execution_noise='high',calibration_bias=-.1),stress.Distortion(),old.calibration_observations)
    assert m.upgrade_prepared(changed).belief.fit_parameters==new.belief.fit_parameters
    assert not hasattr(new.belief,'distortion') and not hasattr(new.belief.config,'calibration_bias')
    assert new.metadata['execution_estimator']=='quadratic_covariance'


def test_identical_observations_keep_fixed_policy_physical_trajectories_unchanged():
    m=module(); c=sim.Config(n_participants=2,n_trials=4,mc_samples=8,candidate_count=7)
    old=stress.prepare_stress_execution(c,stress.Distortion(.25,.45,.75)); new=m.upgrade_prepared(old)
    before=sim.run_scenario(c,sim.make_passengers(c),old); after=sim.run_scenario(c,sim.make_passengers(c),new)
    names=['RandomContinuous','GridContinuous','Staircase']; fields=['target_command_x','peak_accel','peak_jerk','duration_s','acceptable']
    pd.testing.assert_frame_equal(before[before.algorithm.isin(names)][fields],after[after.algorithm.isin(names)][fields])


def test_standard_preparation_uses_original_command_schedule_and_supports_zero_noise_data():
    m=module(); c=sim.Config(calibration_trials=40)
    old=sim.prepare_execution(c); new=m.prepare_flexible_execution(c)
    pd.testing.assert_frame_equal(old.calibration_observations,new.calibration_observations)
    exact=m.prepare_flexible_execution(c,fixture(noise=0))
    np.testing.assert_allclose(exact.belief.fit_parameters.coefficients,[.12,.25,.45],atol=1e-8)
    with pytest.raises(ValueError): m.prepare_flexible_execution(replace(c,execution_belief='oracle'))
