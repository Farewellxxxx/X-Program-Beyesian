"""Private vehicle truth and independent public execution calibration."""
from dataclasses import dataclass
from math import isfinite
import numpy as np
from .public import ExecutionBelief


def _validate(intercept, gain, sd, lower, upper):
    if not all(isfinite(v) for v in (intercept,gain,sd,lower,upper)):
        raise ValueError('execution parameters must be finite')
    if gain <= 0 or sd < 0 or lower >= upper:
        raise ValueError('positive gain, nonnegative sd, and ordered bounds required')

@dataclass(frozen=True)
class ExecutionTruth:
    intercept: float
    gain: float
    sd: float
    lower: float = 0.
    upper: float = 3.

    def __post_init__(self):
        _validate(self.intercept,self.gain,self.sd,self.lower,self.upper)


def execute(target: float, truth: ExecutionTruth, rng: np.random.Generator) -> float:
    if not isfinite(target):
        raise ValueError('target must be finite')
    return float(np.clip(truth.intercept+truth.gain*target+rng.normal(0,truth.sd),truth.lower,truth.upper))


def calibrate_execution(truth: ExecutionTruth, rng: np.random.Generator, n: int = 90) -> ExecutionBelief:
    if not isinstance(n,(int,np.integer)) or isinstance(n,bool) or n < 3:
        raise ValueError('at least three calibration observations required')
    # Interior commands reduce (but cannot eliminate) clipping bias; no truth
    # inversion or access to unobserved pre-clipping acceleration is used.
    span=truth.upper-truth.lower
    targets=np.linspace(truth.lower+.2*span,truth.upper-.2*span,n)
    measured=np.array([execute(float(t),truth,rng) for t in targets])
    design=np.column_stack((np.ones(n),targets))
    intercept,gain=np.linalg.lstsq(design,measured,rcond=None)[0]
    residual=measured-design@np.array([intercept,gain])
    sd=float(np.sqrt(np.sum(residual**2)/(n-2)))
    if gain <= 0:
        raise ValueError('calibration failed: nonpositive estimated gain')
    return ExecutionBelief(float(intercept),float(gain),sd,truth.lower,truth.upper)


def execution_quadrature(target: float, belief: ExecutionBelief, nodes: int = 7) -> tuple[np.ndarray,np.ndarray]:
    _validate(belief.intercept,belief.gain,belief.sd,belief.lower,belief.upper)
    if not isfinite(target):
        raise ValueError('target must be finite')
    if not isinstance(nodes,(int,np.integer)) or isinstance(nodes,bool) or nodes < 1:
        raise ValueError('nodes must be a positive integer')
    mean=belief.intercept+belief.gain*target
    if belief.sd == 0:
        return np.array([np.clip(mean,belief.lower,belief.upper)]),np.ones(1)
    z,w=np.polynomial.hermite.hermgauss(nodes)
    x=np.clip(mean+np.sqrt(2)*belief.sd*z,belief.lower,belief.upper)
    # Clipped nodes retain their probability weights, including boundary atoms.
    return x,w/w.sum()


def spawn_streams(seed: int, participant: int, method: int) -> dict[str,np.random.Generator]:
    """Stable semantic IDs: population=1, calibration=2, execution=3,
    feedback=4, policy=5. First two exclude method, pairing truth and calibration.
    Participant and method are nonnegative integer IDs, never Python hashes.
    """
    for value in (seed,participant,method):
        if not isinstance(value,(int,np.integer)) or isinstance(value,bool) or value < 0:
            raise ValueError('stream keys must be nonnegative integers')
    return {name:np.random.default_rng(np.random.SeedSequence([seed,participant,identifier] + ([] if identifier<=2 else [method])))
            for name,identifier in [('population',1),('execution_calibration',2),('execution',3),('feedback',4),('policy',5)]}
