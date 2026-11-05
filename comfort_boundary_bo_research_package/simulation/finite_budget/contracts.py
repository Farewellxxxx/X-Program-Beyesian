"""Immutable public configuration. No participant truth enters these records."""
from dataclasses import dataclass, field
import math
import numpy as np
from ..decoupled_calibration.public import Observation, ExecutionBelief


def _integer(value, minimum=0):
    return not isinstance(value, bool) and isinstance(value, (int, np.integer)) and value >= minimum


@dataclass(frozen=True)
class PriorSpec:
    kind: str = 'normal'
    center: float = 1.5
    sd: float = 1.
    b_min: float = -1.5
    b_max: float = 4.5
    b_nodes: int = 241
    k_min: float = .25
    k_max: float = 40.
    k_nodes: int = 41
    log_k_mean: float = math.log(4)
    log_k_sd: float = .7

    def __post_init__(self):
        if self.kind not in ('normal', 'uniform'):
            raise ValueError('prior kind must be normal or uniform')
        if not all(math.isfinite(v) for v in (self.center,self.sd,self.b_min,self.b_max,
                self.k_min,self.k_max,self.log_k_mean,self.log_k_sd)):
            raise ValueError('prior parameters must be finite')
        if self.sd <= 0 or self.log_k_sd <= 0 or self.b_min >= self.b_max or not 0 < self.k_min < self.k_max:
            raise ValueError('invalid prior support or scale')
        if not _integer(self.b_nodes,2) or not _integer(self.k_nodes,2):
            raise ValueError('posterior grids require at least two nodes per axis')


@dataclass(frozen=True)
class StudySpec:
    tau: float = .70
    delta: float = .15
    primary_budget: int = 30
    max_budget: int = 60
    checkpoints: tuple[int,...] = (10,15,20,30,40,60)
    success_target: float = .80
    calibration_n: int = 90
    seed: int = 202611051
    split: str = 'development'

    def __post_init__(self):
        if not math.isfinite(self.tau) or not 0 < self.tau < 1:
            raise ValueError('tau must be in (0,1)')
        if not math.isfinite(self.delta) or self.delta <= 0:
            raise ValueError('delta must be positive')
        if not math.isfinite(self.success_target) or not 0 < self.success_target < 1:
            raise ValueError('success target must be in (0,1)')
        if self.split not in ('development','heldout','stress','pilot','numerical'):
            raise ValueError('unsupported study split')
        if not all(_integer(v,1) for v in (self.primary_budget,self.max_budget,self.calibration_n)) or self.calibration_n < 3 or not _integer(self.seed):
            raise ValueError('invalid budgets, calibration count, or seed')
        cp = tuple(self.checkpoints)
        if (not cp or not all(_integer(v,1) for v in cp) or tuple(sorted(set(cp))) != cp
                or self.primary_budget not in cp or cp[-1] != self.max_budget):
            raise ValueError('ordered checkpoints must contain primary budget and end at max budget')
        object.__setattr__(self,'checkpoints',cp)


@dataclass(frozen=True)
class Readout:
    boundary: float | None
    lower: float | None = None
    upper: float | None = None
    status: str = 'ok'
    edge_mass: float | None = None
    posterior_success: float | None = None
    active_bounds: tuple[str,...] = ()

    def __post_init__(self):
        if self.status not in ('ok','failed','rank_deficient','no_data','no_convergence','nonfinite'):
            raise ValueError('unsupported readout status')
        object.__setattr__(self,'active_bounds',tuple(self.active_bounds))


@dataclass(frozen=True)
class StaircaseSpec:
    initial: float = .6
    floor: float = .15
    start: float = 1.5
    reversals_per_halving: int = 2

    def __post_init__(self):
        if not all(math.isfinite(v) for v in (self.initial,self.floor,self.start)) or not 0 < self.floor <= self.initial or not _integer(self.reversals_per_halving,1):
            raise ValueError('invalid staircase parameters')


@dataclass(frozen=True)
class SamplerConfig:
    tau: float = .70
    delta: float = .15
    lower: float = 0.
    upper: float = 3.
    targets: tuple[float,...] = tuple(i/10 for i in range(31))
    prior: PriorSpec = field(default_factory=PriorSpec)
    midpoint_nodes: int = 81
    slope_nodes: int = 41
    quadrature_nodes: int = 7
    staircase: StaircaseSpec = field(default_factory=StaircaseSpec)

    def __post_init__(self):
        targets = tuple(self.targets)
        if (not all(math.isfinite(v) for v in (self.tau,self.delta,self.lower,self.upper))
                or not 0 < self.tau < 1 or self.delta <= 0 or self.lower >= self.upper):
            raise ValueError('invalid sampler criterion or domain')
        if self.lower != 0. or self.upper != 3.:
            raise ValueError('finite-budget v2 supports only the prescribed public domain [0,3]')
        if (not targets or not all(math.isfinite(v) and self.lower <= v <= self.upper for v in targets)
                or tuple(sorted(set(targets))) != targets):
            raise ValueError('targets must be finite, increasing distinct domain commands')
        if not isinstance(self.prior,PriorSpec) or not isinstance(self.staircase,StaircaseSpec):
            raise TypeError('expected public prior and staircase specifications')
        if not all(_integer(v,2) for v in (self.midpoint_nodes,self.slope_nodes)) or not _integer(self.quadrature_nodes,1):
            raise ValueError('invalid numerical node counts')
        if not self.lower <= self.staircase.start <= self.upper:
            raise ValueError('staircase start must lie in public domain')
        object.__setattr__(self,'targets',targets)


def validate_observation(observation, history=(), *, targets=None, lower=0., upper=3.):
    """Reject enriched/subclass records and validate before modifying any state."""
    if type(observation) is not Observation:
        raise TypeError('only exact public Observation records are accepted')
    o = observation
    if (not _integer(o.trial,1) or (history and o.trial <= history[-1].trial)
            or not math.isfinite(o.target) or not lower <= o.target <= upper
            or (targets is not None and o.target not in targets)
            or not math.isfinite(o.realized) or not lower <= o.realized <= upper
            or not _integer(o.acceptable) or o.acceptable not in (0,1)):
        raise ValueError('invalid public observation')
    return Observation(int(o.trial),float(o.target),float(o.realized),int(o.acceptable))
