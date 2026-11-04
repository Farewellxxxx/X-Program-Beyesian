"""Independent identities for constrained conjugate execution inference."""
from dataclasses import replace
import importlib
import importlib.util
import math
import numpy as np
import pytest
from scipy import stats
from long_horizon_audit.tests.test_flexible_execution import fixture
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim


def module():
    name='comfort_boundary_bo_research_package.simulation.execution_posterior'
    assert importlib.util.find_spec(name), 'Posterior execution inference is missing'
    return importlib.import_module(name)


def test_conjugate_update_and_evidence_matches_independent_marginal_density():
    m=module(); h=np.array([[1.,-.5],[1.,0],[1.,.5],[1.,1.]])
    y=np.array([.2,.9,.8,1.4]); sd=np.array([.5,1.2])
    p=m.fit_regression(h,y,sd,m.PosteriorSettings())
    v=np.linalg.inv(np.diag(1/sd**2)+h.T@h); mean=v@h.T@y
    np.testing.assert_allclose(p.mean,mean,atol=1e-12)
    np.testing.assert_allclose(p.v,v,atol=1e-12)
    assert p.a==4 and p.b==pytest.approx(1+.5*(y@y-mean@np.linalg.solve(v,mean)))
    # Integrating a NIG prior gives this multivariate t prior-predictive density.
    expected=stats.multivariate_t.logpdf(y,loc=np.zeros(4),shape=.5*(np.eye(4)+h@np.diag(sd**2)@h.T),df=4)
    assert p.log_evidence==pytest.approx(expected,abs=1e-12)


def test_monotone_probability_matches_independent_joint_t_monte_carlo():
    m=module(); mean=np.array([.1,-.15,.30,0,0]); scale=np.diag([.2,.4,.3,.1,.1])
    scale[1,2]=scale[2,1]=.08
    p=m.monotone_probability(mean,scale,7,2,1.55)
    draws=stats.multivariate_t.rvs(mean,scale,df=7,size=250000,random_state=np.random.default_rng(1984))
    empirical=(.94+draws[:,1]>=1.55*np.abs(draws[:,2])).mean()
    assert p==pytest.approx(empirical,abs=.003)
    assert m.monotone_probability(mean[:2],scale[:2,:2],7,1,1.55)==pytest.approx(stats.t.sf((-.94-mean[1])/math.sqrt(scale[1,1]),7))


def test_posterior_is_joint_monotone_spd_deterministic_and_has_nested_draw_prefixes():
    m=module(); settings=m.PosteriorSettings(posterior_draws=256)
    one=m.fit_execution_posterior(fixture(),sim.ExecutionSettings(),settings)
    two=m.fit_execution_posterior(fixture(),sim.ExecutionSettings(),replace(settings,posterior_draws=512))
    assert np.isfinite(one.weights).all() and one.weights.sum()==pytest.approx(1)
    assert all(one.weights>0)
    for c,d in zip(one.components,two.components):
        np.testing.assert_array_equal(c.coefficients,d.coefficients[:256])
        np.testing.assert_array_equal(c.covariances,d.covariances[:256])
        assert np.all(.94+c.coefficients[:,1]>=1.55*np.abs(c.coefficients[:,2])-1e-12)
        assert np.linalg.eigvalsh(c.covariances).min()>0
        assert c.log_evidence==pytest.approx(c.regression.log_evidence+math.log(c.posterior_constraint_mass)-math.log(c.prior_constraint_mass))
        with pytest.raises(ValueError): c.coefficients[0,0]=100
    assert one.seed_fingerprint==two.seed_fingerprint
    assert one.draw_fingerprint!=two.draw_fingerprint


def test_joint_sigma_coefficient_moments_and_covariance_orientation():
    m=module(); posterior=m.fit_execution_posterior(fixture(),sim.ExecutionSettings(),m.PosteriorSettings(posterior_draws=16000))
    c=posterior.components[0]; r=c.regression
    np.testing.assert_allclose(c.eta.mean(0),r.mean,atol=.015)
    expected=r.b/(r.a-1)*r.v; df=2*r.a
    # Independent multivariate-t fourth moment gives the MC covariance error.
    variance=((df-2)/(df-4)*(np.outer(np.diag(expected),np.diag(expected))+2*expected**2)-expected**2)/len(c.eta)
    assert np.all(np.abs(np.cov(c.eta,rowvar=False)-expected)<5*np.sqrt(variance))
    assert c.sigma2.mean()==pytest.approx(r.b/(r.a-1),rel=.035)
    # sigma2 is the conditional acceleration variance, not marginal variance.
    cross=c.covariances[:,0,1:]; lam=c.covariances[:,1:,1:]
    np.testing.assert_allclose(cross,np.einsum('ni,nij->nj',c.eta[:,1:],lam),atol=1e-12)
    np.testing.assert_allclose(c.covariances[:,0,0],c.sigma2+np.einsum('ni,ni->n',cross,c.eta[:,1:]),atol=1e-12)


def test_rejects_invalid_data_and_supports_noiseless_data():
    m=module(); good=fixture(); public=sim.ExecutionSettings()
    for bad in [good.iloc[:7],good.assign(peak_jerk=np.nan),good.assign(target_command_x=1.),good.assign(duration_s=8.)]:
        with pytest.raises(ValueError): m.fit_execution_posterior(bad,public)
    p=m.fit_execution_posterior(fixture(noise=0),public,m.PosteriorSettings(posterior_draws=32))
    assert all(np.linalg.eigvalsh(c.covariances).min()>0 for c in p.components)
    assert p.n_used==12
    for field,value in [('posterior_draws',0),('posterior_draws',True),('sigma_shape',1),('lambda_df',3),('bias_prior_sd',float('nan'))]:
        with pytest.raises(ValueError): m.PosteriorSettings(**{field:value})
