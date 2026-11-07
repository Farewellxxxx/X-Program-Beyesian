"""Evaluator-side paired B/W populations, independent of inference/sampling."""
from dataclasses import dataclass
import math
from statistics import NormalDist
import numpy as np
from ..decoupled_calibration.passenger import Passenger
from .contracts import _integer


@dataclass(frozen=True)
class PopulationSpec:
    boundary_low: float = .5
    boundary_high: float = 2.5
    width_median: float = .70
    width_log_sd: float = .35
    lapse: float = .10

    def __post_init__(self):
        if (not all(math.isfinite(v) for v in (self.boundary_low,self.boundary_high,self.width_median,self.width_log_sd,self.lapse))
                or self.boundary_low>=self.boundary_high or self.width_median<=0 or self.width_log_sd<0
                or not 0<=self.lapse<.4):
            raise ValueError('invalid boundary/width population or lapse incompatible with .2/.8 crossings')


def draw_latents(n,spec,rng):
    if not _integer(n) or not isinstance(spec,PopulationSpec): raise ValueError('nonnegative n and PopulationSpec required')
    if not isinstance(rng,np.random.Generator): raise TypeError('expected NumPy Generator')
    B=rng.uniform(spec.boundary_low,spec.boundary_high,n)
    W=rng.lognormal(math.log(spec.width_median),spec.width_log_sd,n)
    return [(float(b),float(w)) for b,w in zip(B,W)]


def passenger_from_latent(B,W,family,tau=.70,lapse=.10):
    if not math.isfinite(B) or not math.isfinite(W) or W<=0:
        raise ValueError('finite B and positive W required')
    if family not in ('logistic','probit','lapse_logistic','gumbel'):
        raise ValueError('unknown passenger family')
    if not math.isfinite(lapse) or not 0<=lapse<.4:
        raise ValueError('lapse must permit both .2 and .8 crossings')
    if family == 'gumbel':
        span = math.log(-math.log(.2)) - math.log(-math.log(.8))
        return Passenger(float(B), family, span / float(W), 0., tau)
    lam=lapse if family=='lapse_logistic' else 0.
    inv=NormalDist().inv_cdf if family=='probit' else lambda q:math.log(q/(1-q))
    q2=(.2-lam/2)/(1-lam); q8=(.8-lam/2)/(1-lam)
    k=(inv(q8)-inv(q2))/W
    return Passenger(float(B),family,float(k),lam,tau)


def local_derivative(passenger):
    if passenger.family == 'gumbel':
        return passenger.slope * (passenger.tau * math.log(passenger.tau))
    q=(passenger.tau-passenger.lapse/2)/(1-passenger.lapse)
    density=(math.exp(-.5*NormalDist().inv_cdf(q)**2)/math.sqrt(2*math.pi)
             if passenger.family=='probit' else q*(1-q))
    return -(1-passenger.lapse)*passenger.slope*density
