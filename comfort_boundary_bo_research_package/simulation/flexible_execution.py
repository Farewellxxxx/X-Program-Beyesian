"""Observation-only quadratic mean and full residual-covariance plug-in fit.

Regularization stabilizes small samples; coefficient/covariance uncertainty is
not propagated. True simulation profiles and participant labels are not inputs.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
from itertools import combinations
import json
import math

import numpy as np
import pandas as pd

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim

ESTIMATOR='quadratic_covariance'


@dataclass(frozen=True)
class FitSettings:
    bias_prior_sd: float = .50
    gain_prior_sd: float = .50
    quadratic_prior_sd: float = .75
    covariance_pseudocount: float = 3.
    covariance_floor: float = 1e-8
    max_design_condition: float = 1e8

    def __post_init__(self):
        if not all(math.isfinite(v) and v>0 for v in asdict(self).values()):
            raise ValueError('Fit settings must be finite and strictly positive')

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class FlexibleParameters:
    coefficients: tuple[float,float,float]
    covariance: tuple[tuple[float,float,float],tuple[float,float,float],tuple[float,float,float]]

    def __post_init__(self):
        beta=np.asarray(self.coefficients,dtype=float); covariance=np.asarray(self.covariance,dtype=float)
        if beta.shape!=(3,) or covariance.shape!=(3,3) or not np.isfinite(beta).all() or not np.isfinite(covariance).all():
            raise ValueError('Require three finite coefficients and a finite 3x3 covariance')
        if not np.allclose(covariance,covariance.T,rtol=0,atol=1e-12):
            raise ValueError('Residual covariance must be symmetric')
        covariance=(covariance+covariance.T)/2
        if np.linalg.eigvalsh(covariance).min()<=0: raise ValueError('Residual covariance must be positive definite')
        object.__setattr__(self,'coefficients',tuple(map(float,beta)))
        object.__setattr__(self,'covariance',tuple(tuple(map(float,row)) for row in covariance))


@dataclass(frozen=True)
class FlexibleFit:
    parameters: FlexibleParameters
    n_observations: int
    n_used: int
    n_clipped: int
    residual_dof: int
    design_condition: float
    covariance_shrinkage: float
    active_constraints: tuple[str,...]
    settings: FitSettings

    def metadata(self):
        b,g,q=self.parameters.coefficients; cov=np.asarray(self.parameters.covariance)
        metadata=dict(execution_estimator=ESTIMATOR,fit_settings_fingerprint=self.settings.fingerprint(),
            fit_bias=b,fit_gain=g,fit_quadratic=q,fit_residual_dof=self.residual_dof,
            fit_design_condition=self.design_condition,fit_covariance_shrinkage=self.covariance_shrinkage,
            fit_active_constraints=','.join(self.active_constraints) or 'none',
            calibration_n_observations=self.n_observations,calibration_n_used=self.n_used,calibration_n_clipped=self.n_clipped,
            belief_execution_bias=b,belief_execution_noise_scale=float(np.sqrt(np.trace(cov)/3)))
        for i in range(3):
            for j in range(i,3):
                metadata[f'fit_cov_{i}{j}']=float(cov[i,j])
                if i!=j: metadata[f'fit_corr_{i}{j}']=float(cov[i,j]/np.sqrt(cov[i,i]*cov[j,j]))
        return metadata


def _monotone_solution(hessian,score,span):
    unconstrained=np.linalg.solve(hessian,score)
    constraints=np.array([[0.,1.,-span],[0.,1.,span]])
    lower=np.full(2,-.94); candidates=[]
    for count in range(3):
        for active in combinations(range(2),count):
            beta=unconstrained.copy()
            if active:
                a=constraints[list(active)]; target=lower[list(active)]
                correction=np.linalg.solve(hessian,a.T)
                beta+=correction@np.linalg.solve(a@correction,target-a@unconstrained)
            if np.all(constraints@beta>=lower-1e-9):
                objective=float(.5*beta@hessian@beta-score@beta)
                candidates.append((objective,beta,tuple(('lower','upper')[i] for i in active)))
    if not candidates: raise ValueError('Unable to solve monotone quadratic mean')
    _,beta,active=min(candidates,key=lambda item:item[0])
    return beta,active


def fit_flexible_execution(observations,settings,fit_settings=FitSettings()):
    if not set(sim.CALIBRATION_FIELDS).issubset(observations.columns):
        raise ValueError('Calibration requires command, acceleration, jerk and duration')
    values=observations[sim.CALIBRATION_FIELDS].to_numpy(dtype=float)
    if len(values)<8 or not np.isfinite(values).all(): raise ValueError('At least eight finite observations are required')
    lower=np.array([settings.x_min,.20,.25,2.20]); upper=np.array([settings.x_max,2.40,5.70,4.85])
    if ((values<lower)|(values>upper)).any(): raise ValueError('Calibration observations outside supported bounds')
    interior=((values[:,1:]>lower[1:])&(values[:,1:]<upper[1:])).all(axis=1)
    x,a,j,t=values[interior].T; n=len(x)
    if n<8: raise ValueError('At least eight observations away from clipping bounds are required')
    span=settings.x_max-settings.x_min; d=x-(settings.x_max+settings.x_min)/2
    level=(x-settings.x_min)/span; sa=.045+.055*level; sj=.18+.24*level
    design=np.column_stack([np.ones(n),d,d*d])/sa[:,None]
    condition=float(np.linalg.cond(design))
    if np.linalg.matrix_rank(design)!=3 or condition>fit_settings.max_design_condition:
        raise ValueError('Calibration command design cannot identify a stable quadratic')
    response=np.column_stack([(a-.05-.94*x)/sa,(j-.58-1.74*a-.10*x)/sj,(t-3.90+.30*a)/.18])
    projection=np.linalg.lstsq(design,response,rcond=None)[0]
    residual=response-design@projection
    raw_covariance=residual.T@residual/(n-3)
    weight=fit_settings.covariance_pseudocount/(n-3+fit_settings.covariance_pseudocount)
    covariance=(1-weight)*raw_covariance+weight*np.diag(np.diag(raw_covariance))+fit_settings.covariance_floor*np.eye(3)
    prior_sd=np.array([fit_settings.bias_prior_sd,fit_settings.gain_prior_sd,fit_settings.quadratic_prior_sd])
    hessian=design.T@design+max(raw_covariance[0,0],fit_settings.covariance_floor)*np.diag(1/prior_sd**2)
    coefficients,active=_monotone_solution(hessian,design.T@response[:,0],span)
    parameters=FlexibleParameters(tuple(coefficients),tuple(map(tuple,covariance)))
    return FlexibleFit(parameters,len(values),n,int((~interior).sum()),n-3,condition,weight,active,fit_settings)


class FlexibleExecutionModel(sim.ContinuousExecutionModel):
    def __init__(self,settings,parameters: FlexibleParameters):
        b,g,q=parameters.coefficients; span=settings.x_max-settings.x_min
        if min(.94+g-span*q,.94+g+span*q)<-1e-8:
            raise ValueError('Fitted acceleration mean must be nondecreasing over command bounds')
        self.fit_parameters=parameters
        covariance=np.asarray(parameters.covariance)
        self._cholesky=np.linalg.cholesky(covariance)
        self._cholesky.setflags(write=False)
        # Compatibility scalar for the auxiliary RMS/speed fields only; the
        # three fitted motion channels use the full covariance below.
        super().__init__(settings,sim.ExecutionParameters(b,float(np.sqrt(np.trace(covariance)/3))))

    def _acceleration_mean(self,x):
        b,g,q=self.fit_parameters.coefficients; d=x-(self.config.x_min+self.config.x_max)/2
        return float(np.clip(.05+.94*x+b+g*d+q*d*d,.20,2.35))

    def nominal_features(self,target_x):
        x=sim.clip(target_x,self.config.x_min,self.config.x_max)
        b,g,q=self.fit_parameters.coefficients; d=x-(self.config.x_min+self.config.x_max)/2
        model=sim.ContinuousExecutionModel(self.config,sim.ExecutionParameters(b+g*d+q*d*d,self.noise_scale))
        return model.nominal_features(x)

    def _channels(self,target_x,rng,n_samples):
        if isinstance(n_samples,bool) or not isinstance(n_samples,int) or n_samples<1:
            raise ValueError('Sample count must be a positive integer')
        x=sim.clip(target_x,self.config.x_min,self.config.x_max)
        level=(x-self.config.x_min)/(self.config.x_max-self.config.x_min)
        residual=self._cholesky@rng.standard_normal((3,n_samples))
        accel=np.clip(self._acceleration_mean(x)+(.045+.055*level)*residual[0],.20,2.40)
        jerk=np.clip(.58+1.74*accel+.10*x+(.18+.24*level)*residual[1],.25,5.70)
        duration=np.clip(3.90-.30*accel+.18*residual[2],2.20,4.85)
        return x,accel,jerk,duration

    def _intensity_and_violation(self,a,j,t,cumulative):
        intensity=a+self.config.jerk_penalty_weight*np.maximum(0,j-self.config.jerk_penalty_threshold)
        if self.config.include_time_effects:
            intensity+=self.config.duration_penalty_weight*np.maximum(0,t-self.config.duration_penalty_threshold)+.004*cumulative
        violation=(a>self.config.safe_peak_accel)|(j>self.config.safe_peak_jerk)|(t>self.config.safe_duration)
        return intensity,violation

    def sample_many(self,target_x,rng,n_samples,cumulative_discomfort=0.0):
        _,a,j,t=self._channels(target_x,rng,n_samples)
        return self._intensity_and_violation(a,j,t,cumulative_discomfort)

    def sample_feature_arrays(self,target_x,rng,n_samples,cumulative_discomfort=0.0):
        x,a,j,t=self._channels(target_x,rng,n_samples)
        intensity,violation=self._intensity_and_violation(a,j,t,cumulative_discomfort)
        nominal=self.nominal_features(x); error=intensity-nominal['target_nominal_intensity']
        return dict(peak_accel=a,peak_jerk=j,duration_s=t,
            rms_jerk=np.clip(rng.normal(.55*j,.08*self.noise_scale),.10,3.50),
            speed_delta=np.clip(rng.normal(a*t,.22*self.noise_scale),.25,8.50),
            realized_intensity=intensity,realization_error=error,abs_realization_error=np.abs(error),
            command_tracking_error=a-x,safety_violation=violation,protocol_deviation=violation)

    def sample_features(self,target_x,rng,cumulative_discomfort=0.0):
        arrays=self.sample_feature_arrays(target_x,rng,1,cumulative_discomfort)
        return {**self.nominal_features(target_x),**{key:value[0].item() for key,value in arrays.items()}}


def upgrade_prepared(prepared,fit_settings=FitSettings()):
    if prepared.metadata['execution_belief']!='calibrated': raise ValueError('Flexible estimator requires calibrated execution belief')
    observations=prepared.calibration_observations.copy()
    fit=fit_flexible_execution(observations,prepared.belief.config,fit_settings)
    belief=FlexibleExecutionModel(prepared.belief.config,fit.parameters)
    return sim.PreparedExecution(prepared.truth,belief,observations,{**prepared.metadata,**fit.metadata()})


def prepare_flexible_execution(config,observations=None,fit_settings=FitSettings()):
    if config.execution_belief!='calibrated': raise ValueError('Flexible estimator requires calibrated execution belief')
    prepared=sim.prepare_execution(replace(config,execution_belief='nominal'))
    if observations is None:
        rng=np.random.default_rng(np.random.SeedSequence([config.calibration_seed,0xCA1B]))
        span=config.x_max-config.x_min
        commands=np.linspace(config.x_min+.20*span,config.x_min+.80*span,config.calibration_trials)
        observations=pd.DataFrame([prepared.truth.sample_features(float(x),rng) for x in commands])[sim.CALIBRATION_FIELDS]
    prepared.calibration_observations=observations.copy()
    prepared.metadata['execution_belief']='calibrated'
    return upgrade_prepared(prepared,fit_settings)
