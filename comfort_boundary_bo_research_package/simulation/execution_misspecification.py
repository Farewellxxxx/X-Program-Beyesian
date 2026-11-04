"""Synthetic structural perturbations; fitted execution beliefs stay unchanged.

Only the explicit oracle receives Distortion. These coefficients are stress
choices, not estimates of real vehicle dynamics.
"""
from dataclasses import dataclass, fields
import math

import numpy as np
import pandas as pd

from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim


@dataclass(frozen=True)
class Distortion:
    gain: float = 0.0
    quadratic: float = 0.0
    correlation: float = 0.0

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.gain,self.quadratic,self.correlation)):
            raise ValueError('Distortion coefficients must be finite')
        if not -1 < self.correlation < 1:
            raise ValueError('Residual correlation must be strictly between -1 and 1')


class DistortedExecutionModel(sim.ContinuousExecutionModel):
    def __init__(self, settings, parameters, distortion: Distortion):
        super().__init__(settings,parameters)
        self.distortion=distortion

    def nominal_features(self,target_x):
        x=sim.clip(target_x,self.config.x_min,self.config.x_max)
        d=x-(self.config.x_min+self.config.x_max)/2
        bias=self.parameters.bias+self.distortion.gain*d+self.distortion.quadratic*d*d
        # Reuse the original nominal feature/clipping definitions at the altered mean.
        nominal=sim.ContinuousExecutionModel(self.config,sim.ExecutionParameters(bias,self.noise_scale))
        return nominal.nominal_features(x)

    def sample_feature_arrays(self,target_x,rng,n_samples,cumulative_discomfort=0.0):
        if isinstance(n_samples,bool) or not isinstance(n_samples,int) or n_samples<1:
            raise ValueError('Sample count must be a positive integer')
        nominal=self.nominal_features(target_x); x=float(nominal['target_command_x'])
        level=(x-self.config.x_min)/(self.config.x_max-self.config.x_min)
        rho=self.distortion.correlation; independent=math.sqrt(1-rho*rho)
        za=rng.standard_normal(n_samples)
        zj=rho*za+independent*rng.standard_normal(n_samples)
        accel=np.clip(float(nominal['target_nominal_peak_accel'])+(.045+.055*level)*self.noise_scale*za,.20,2.40)
        jerk=np.clip(.58+1.74*accel+.10*x+(.18+.24*level)*self.noise_scale*zj,.25,5.70)
        rms=np.clip(rng.normal(.55*jerk,.08*self.noise_scale),.10,3.50)
        zd=rho*za+independent*rng.standard_normal(n_samples)
        duration=np.clip(3.90-.30*accel+.18*self.noise_scale*zd,2.20,4.85)
        speed=np.clip(rng.normal(accel*duration,.22*self.noise_scale),.25,8.50)
        intensity=accel+self.config.jerk_penalty_weight*np.maximum(0,jerk-self.config.jerk_penalty_threshold)
        if self.config.include_time_effects:
            intensity+=self.config.duration_penalty_weight*np.maximum(0,duration-self.config.duration_penalty_threshold)
            intensity+=.004*cumulative_discomfort
        violation=(accel>self.config.safe_peak_accel)|(jerk>self.config.safe_peak_jerk)|(duration>self.config.safe_duration)
        error=intensity-float(nominal['target_nominal_intensity'])
        return dict(peak_accel=accel,peak_jerk=jerk,rms_jerk=rms,duration_s=duration,speed_delta=speed,
            realized_intensity=intensity,realization_error=error,abs_realization_error=np.abs(error),
            command_tracking_error=accel-x,safety_violation=violation,protocol_deviation=violation)

    def sample_features(self,target_x,rng,cumulative_discomfort=0.0):
        arrays=self.sample_feature_arrays(target_x,rng,1,cumulative_discomfort)
        return {**self.nominal_features(target_x),**{key:value[0].item() for key,value in arrays.items()}}

    def sample_many(self,target_x,rng,n_samples,cumulative_discomfort=0.0):
        arrays=self.sample_feature_arrays(target_x,rng,n_samples,cumulative_discomfort)
        return arrays['realized_intensity'],arrays['safety_violation']


def make_truth(settings,parameters,distortion: Distortion):
    if distortion==Distortion():
        return sim.ContinuousExecutionModel(settings,parameters)
    return DistortedExecutionModel(settings,parameters,distortion)


def nested_commands(settings,n: int) -> np.ndarray:
    """Fixed radical-inverse ordering: more budget adds observations, not redesign."""
    if isinstance(n,bool) or not isinstance(n,int) or n<1:
        raise ValueError('Calibration count must be a positive integer')
    points=[]
    for index in range(1,n+1):
        value=0.; denominator=1.; integer=index
        while integer:
            denominator*=2; integer,remainder=divmod(integer,2); value+=remainder/denominator
        points.append(value)
    return settings.x_min+(settings.x_max-settings.x_min)*(.20+.60*np.array(points))


def prepare_stress_execution(config,distortion: Distortion,observations=None):
    settings=sim.ExecutionSettings(**{f.name:getattr(config,f.name) for f in fields(sim.ExecutionSettings)})
    parameters=sim.ExecutionParameters(config.calibration_bias,{'low':.65,'medium':1.,'high':1.55}[config.execution_noise])
    truth=make_truth(settings,parameters,distortion)
    if config.execution_belief=='calibrated' and observations is None:
        rng=np.random.default_rng(np.random.SeedSequence([config.calibration_seed,0xCA1B]))
        observations=pd.DataFrame([truth.sample_features(float(x),rng)
            for x in nested_commands(settings,config.calibration_trials)])[sim.CALIBRATION_FIELDS]
    prepared=sim.prepare_execution(config,calibration_observations=observations)
    prepared.truth=truth
    if config.execution_belief=='oracle':
        prepared.belief=make_truth(settings,sim.ExecutionParameters(parameters.bias,parameters.noise_scale),distortion)
    prepared.metadata['calibration_design']='nested_vdc2' if config.execution_belief=='calibrated' else 'none'
    return prepared


def distribution_diagnostics(prepared,seed: int,n_samples: int=4096) -> pd.DataFrame:
    """Independent holdout command grid; draws never enter fitting or policies.

    Common true/belief innovations reduce MC noise. Empirical quantiles and W1
    are finite-sample approximations; these are not passenger-level outcomes.
    """
    if isinstance(seed,bool) or not isinstance(seed,int) or seed<0:
        raise ValueError('Diagnostic seed must be a nonnegative integer')
    if isinstance(n_samples,bool) or not isinstance(n_samples,int) or n_samples<32:
        raise ValueError('At least 32 diagnostic samples are required')
    settings=prepared.truth.config; span=settings.x_max-settings.x_min
    rows=[]
    for index,x in enumerate(np.linspace(settings.x_min,settings.x_max,21)):
        key=[0xD1A6,index,seed]
        true,viol_true=prepared.truth.sample_many(float(x),np.random.default_rng(np.random.SeedSequence(key)),n_samples)
        belief,viol_belief=prepared.belief.sample_many(float(x),np.random.default_rng(np.random.SeedSequence(key)),n_samples)
        lo,hi=np.quantile(belief,[.05,.95])
        interior=settings.x_min+.2*span-1e-12<=x<=settings.x_min+.8*span+1e-12
        rows.append(dict(command=float(x),region='interior' if interior else 'extrapolation',
            diagnostic_seed=seed,diagnostic_samples=n_samples,
            true_mean=float(true.mean()),belief_mean=float(belief.mean()),mean_abs_error=float(abs(true.mean()-belief.mean())),
            true_sd=float(true.std()),belief_sd=float(belief.std()),sd_abs_error=float(abs(true.std()-belief.std())),
            wasserstein1=float(np.abs(np.sort(true)-np.sort(belief)).mean()),
            interval90_coverage=float(((true>=lo)&(true<=hi)).mean()),
            true_protocol_probability=float(viol_true.mean()),belief_protocol_probability=float(viol_belief.mean()),
            protocol_probability_abs_error=float(abs(viol_true.mean()-viol_belief.mean()))))
    return pd.DataFrame(rows)
