"""Public execution settings and an observation-only plug-in calibration fit.

The functional form is assumed known; bias and a common heteroscedastic noise
scale are estimated without passenger feedback or simulator truth parameters.
"""
from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExecutionParameters:
    bias: float
    noise_scale: float

    def __post_init__(self):
        if not math.isfinite(self.bias) or not math.isfinite(self.noise_scale) or self.noise_scale <= 0:
            raise ValueError('Execution bias must be finite and noise scale finite and positive')


@dataclass(frozen=True)
class ExecutionSettings:
    x_min: float = .35
    x_max: float = 1.90
    include_time_effects: bool = False
    jerk_penalty_threshold: float = 2.30
    jerk_penalty_weight: float = .10
    duration_penalty_threshold: float = 4.10
    duration_penalty_weight: float = .035
    safe_peak_accel: float = 2.20
    safe_peak_jerk: float = 4.80
    safe_duration: float = 4.70

    def __post_init__(self):
        if not math.isfinite(self.x_min) or not math.isfinite(self.x_max) or self.x_min >= self.x_max:
            raise ValueError('Execution command bounds must be finite and increasing')


@dataclass(frozen=True)
class CalibrationFit:
    parameters: ExecutionParameters
    n_observations: int
    n_used: int
    n_clipped: int


CALIBRATION_FIELDS = ['target_command_x','peak_accel','peak_jerk','duration_s']


def fit_execution_parameters(observations: pd.DataFrame, settings: ExecutionSettings) -> CalibrationFit:
    """Weighted bias and residual-scale fit; clipping exclusion is approximate.

    The denominator 3*n-1 accounts for one fitted bias across three independent
    standardized residual channels. No posterior uncertainty is propagated.
    """
    if not set(CALIBRATION_FIELDS).issubset(observations.columns):
        raise ValueError('Calibration requires command, acceleration, jerk and duration')
    values=observations[CALIBRATION_FIELDS].to_numpy(dtype=float)
    if len(values)<4 or not np.isfinite(values).all():
        raise ValueError('Calibration requires at least four finite observations')
    lower=np.array([settings.x_min,.20,.25,2.20])
    upper=np.array([settings.x_max,2.40,5.70,4.85])
    if ((values<lower)|(values>upper)).any():
        raise ValueError('Calibration observations fall outside supported bounds')
    interior=((values[:,1:]>lower[1:])&(values[:,1:]<upper[1:])).all(axis=1)
    x,accel,jerk,duration=values[interior].T
    n=len(x)
    if n<4:
        raise ValueError('Calibration needs at least four observations away from clipping bounds')
    level=(x-settings.x_min)/(settings.x_max-settings.x_min)
    accel_sd=.045+.055*level
    jerk_sd=.18+.24*level
    weights=1/accel_sd**2
    bias=float(np.sum(weights*(accel-.05-.94*x))/weights.sum())
    residuals=np.concatenate(((accel-.05-.94*x-bias)/accel_sd,
        (jerk-.58-1.74*accel-.10*x)/jerk_sd,(duration-3.90+.30*accel)/.18))
    scale=float(np.sqrt(np.sum(residuals**2)/(3*n-1)))
    return CalibrationFit(ExecutionParameters(bias,scale),len(values),n,int((~interior).sum()))
