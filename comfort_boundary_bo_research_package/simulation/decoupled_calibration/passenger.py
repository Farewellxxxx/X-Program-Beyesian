"""Independent synthetic passengers; no policy or likelihood imports."""
from dataclasses import dataclass
from math import isfinite, log
from statistics import NormalDist
import numpy as np

_FAMILIES = {'logistic', 'probit', 'lapse_logistic'}

@dataclass(frozen=True)
class Passenger:
    boundary: float
    family: str
    slope: float
    lapse: float = 0.0
    tau: float = .70

    def __post_init__(self):
        if self.family not in _FAMILIES:
            raise ValueError('unknown passenger family')
        if not all(isfinite(v) for v in (self.boundary,self.slope,self.lapse,self.tau)):
            raise ValueError('passenger parameters must be finite')
        if self.slope <= 0 or not 0 <= self.lapse < 1:
            raise ValueError('positive slope and lapse in [0,1) required')
        if not self.lapse/2 < self.tau < 1-self.lapse/2:
            raise ValueError('tau must lie strictly between response asymptotes')

    def probability(self, realized: float) -> float:
        if not isfinite(realized):
            raise ValueError('realized acceleration must be finite')
        q=(self.tau-self.lapse/2)/(1-self.lapse)
        offset=NormalDist().inv_cdf(q) if self.family=='probit' else log(q/(1-q))
        z=offset+self.slope*(self.boundary-realized)
        if self.family=='probit':
            s=NormalDist().cdf(z)
        elif z >= 0:
            s=1/(1+np.exp(-z))
        else:
            ez=np.exp(z); s=ez/(1+ez)
        return float(self.lapse/2+(1-self.lapse)*s)

    def respond(self, realized: float, rng: np.random.Generator) -> int:
        return int(rng.random() < self.probability(realized))


def generate_passengers(n: int, family: str, tau: float, rng: np.random.Generator) -> list[Passenger]:
    if not isinstance(n,(int,np.integer)) or isinstance(n,bool) or n < 0:
        raise ValueError('n must be a nonnegative integer')
    lapse=.10 if family=='lapse_logistic' else 0.
    # Validate even when n=0.
    Passenger(1.,family,4.,lapse,tau)
    boundaries=rng.uniform(.5,2.5,n)
    slopes=rng.lognormal(np.log(4),.35,n)
    return [Passenger(float(b),family,float(k),lapse,tau) for b,k in zip(boundaries,slopes)]
