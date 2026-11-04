"""Execution predictions integrating model, coefficient and covariance uncertainty."""
from dataclasses import replace
import numpy as np
import pandas as pd
from comfort_boundary_bo_research_package.simulation import flexible_execution as flexible
from comfort_boundary_bo_research_package.simulation import execution_posterior as core
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim

ESTIMATOR='adaptive_posterior'
MODES=('quadratic_plugin','adaptive_plugin','quadratic_posterior','adaptive_posterior')


class PosteriorExecutionModel(flexible.FlexibleExecutionModel):
    def __init__(self,settings,posterior,mode=ESTIMATOR):
        if mode not in MODES: raise ValueError('Unknown posterior predictive mode')
        self.posterior=posterior; self.mode=mode
        self._weights=posterior.weights if mode.startswith('adaptive') else core.frozen_array([0,0,1])
        beta,cov=posterior.moments(mode.startswith('adaptive'))
        super().__init__(settings,flexible.FlexibleParameters(tuple(beta),tuple(map(tuple,cov))))
        self._betas=core.frozen_array(np.stack([c.coefficients for c in posterior.components]))
        self._choleskys=core.frozen_array(np.linalg.cholesky(np.stack([c.covariances for c in posterior.components])))

    def _channels(self,target_x,rng,n_samples):
        if self.mode.endswith('plugin'): return super()._channels(target_x,rng,n_samples)
        if isinstance(n_samples,bool) or not isinstance(n_samples,int) or n_samples<1: raise ValueError('Sample count must be a positive integer')
        x=sim.clip(target_x,self.config.x_min,self.config.x_max)
        level=(x-self.config.x_min)/(self.config.x_max-self.config.x_min); d=x-(self.config.x_min+self.config.x_max)/2
        which=rng.choice(3,size=n_samples,p=self._weights)
        index=rng.integers(self.posterior.settings.posterior_draws,size=n_samples)
        beta=self._betas[which,index]; chol=self._choleskys[which,index]
        residual=np.einsum('nij,nj->ni',chol,rng.standard_normal((n_samples,3)))
        mean=np.clip(.05+.94*x+beta@np.array([1.,d,d*d]),.20,2.35)
        a=np.clip(mean+(.045+.055*level)*residual[:,0],.20,2.40)
        j=np.clip(.58+1.74*a+.10*x+(.18+.24*level)*residual[:,1],.25,5.70)
        t=np.clip(3.90-.30*a+.18*residual[:,2],2.20,4.85)
        return x,a,j,t


def upgrade_prepared(prepared,posterior_settings=core.PosteriorSettings()):
    if prepared.metadata['execution_belief']!='calibrated': raise ValueError('Posterior estimator requires calibrated execution belief')
    observations=prepared.calibration_observations.copy()
    posterior=core.fit_execution_posterior(observations,prepared.belief.config,posterior_settings)
    belief=PosteriorExecutionModel(prepared.belief.config,posterior)
    return sim.PreparedExecution(prepared.truth,belief,observations,{**prepared.metadata,**posterior.metadata()})


def prepare_adaptive_execution(config,observations=None,posterior_settings=core.PosteriorSettings()):
    if config.execution_belief!='calibrated': raise ValueError('Posterior estimator requires calibrated execution belief')
    prepared=sim.prepare_execution(replace(config,execution_belief='nominal'))
    if observations is None:
        rng=np.random.default_rng(np.random.SeedSequence([config.calibration_seed,0xCA1B]))
        span=config.x_max-config.x_min
        commands=np.linspace(config.x_min+.20*span,config.x_min+.80*span,config.calibration_trials)
        observations=pd.DataFrame([prepared.truth.sample_features(float(x),rng) for x in commands])[sim.CALIBRATION_FIELDS]
    prepared.calibration_observations=observations.copy(); prepared.metadata['execution_belief']='calibrated'
    return upgrade_prepared(prepared,posterior_settings)
