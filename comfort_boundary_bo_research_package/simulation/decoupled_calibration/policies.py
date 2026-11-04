"""Public-history-only sampling policies with one shared Bayesian readout."""
from functools import lru_cache
import math
import numpy as np
from ..monotone_bayes import MonotoneBayesianLogistic, PriorGrid
from .public import Observation, Estimate, PolicyConfig, ExecutionBelief
from .execution import execution_quadrature


@lru_cache(maxsize=32)
def _basis(config, belief, point):
    model = MonotoneBayesianLogistic(config.tau, PriorGrid(
        midpoint_nodes=config.midpoint_nodes, slope_nodes=config.slope_nodes))
    xs, ws = [], []
    for target in config.targets:
        if point:
            x = np.array([np.clip(belief.intercept+belief.gain*target, belief.lower, belief.upper)])
            w = np.ones(1)
        else:
            x, w = execution_quadrature(target, belief, config.quadrature_nodes)
        xs.append(x); ws.append(w)
    sizes = [len(x) for x in xs]
    flat = np.concatenate(xs)
    z = model.posterior_slopes[:,None]*(model.posterior_midpoints[:,None]-flat)
    likelihood = np.exp(-np.logaddexp(0.,-z))
    likelihood.setflags(write=False)
    return likelihood, tuple(ws), tuple(np.cumsum([0]+sizes))


class _Base:
    def __init__(self, config, belief, rng):
        if not isinstance(config, PolicyConfig) or not isinstance(belief, ExecutionBelief):
            raise TypeError('Expected public config and execution belief')
        if not all(math.isfinite(v) for v in (config.lower, config.upper)):
            raise ValueError('Config domain must be finite')
        # Validate even samplers which do not otherwise use execution quadrature.
        execution_quadrature(config.lower, belief, config.quadrature_nodes)
        targets = np.asarray(config.targets, dtype=float)
        if (targets.ndim != 1 or len(targets) == 0 or not np.isfinite(targets).all()
                or len(np.unique(targets)) != len(targets)
                or np.any(np.diff(targets) <= 0) or config.lower >= config.upper
                or np.any(targets < config.lower) or np.any(targets > config.upper)):
            raise ValueError('Targets must be distinct increasing finite domain commands')
        if not isinstance(rng, np.random.Generator):
            raise TypeError('rng must be a NumPy Generator')
        self.config, self.belief, self.rng = config, belief, rng
        self.targets = targets.copy()
        self.model = MonotoneBayesianLogistic(config.tau, PriorGrid(
            midpoint_nodes=config.midpoint_nodes, slope_nodes=config.slope_nodes))
        self._history = ()

    @property
    def history(self):
        return self._history

    def observe(self, observation):
        # Reject subclasses too: never retain records carrying simulator fields.
        if type(observation) is not Observation:
            raise TypeError('Only exact public Observation records are accepted')
        o = observation
        if (isinstance(o.trial, bool) or not isinstance(o.trial, (int, np.integer))
                or o.trial < 1 or (self._history and o.trial <= self._history[-1].trial)
                or not math.isfinite(o.target) or o.target not in self.config.targets
                or not math.isfinite(o.realized) or not self.config.lower <= o.realized <= self.config.upper
                or isinstance(o.acceptable, bool) or not isinstance(o.acceptable, (int,np.integer))
                or o.acceptable not in (0,1)):
            raise ValueError('Invalid trial, command, measured acceleration, or binary response')
        copied = Observation(int(o.trial),float(o.target),float(o.realized),int(o.acceptable))
        self._history += (copied,)
        self.model.fit([x.realized for x in self._history], [x.acceptable for x in self._history])
        self._update(copied)

    def _update(self, o):
        pass

    def estimate(self):
        s = self.model.boundary_summary()
        return Estimate(self.model.estimate_boundary(), s['boundary_ci95_lower'],
                        s['boundary_ci95_upper'], s['boundary_support'], s['posterior_grid_edge_mass'])


class _Bayes(_Base):
    def __init__(self, config, belief, rng, point=False):
        super().__init__(config, belief, rng)
        self._likelihood, self._quadrature_weights, self._offsets = _basis(config,belief,point)

    def acquisition_values(self):
        # Law of total variance: gain at measured x = Cov(B,p(y=1|x))² / q(1-q).
        # This equals Var(B)-sum_y p(y|x) Var(B|x,y), without subtractive cancellation.
        w, b = self.model.posterior_weights, self.model._boundary_values
        q = np.einsum('i,ij->j', w, self._likelihood, optimize=False)
        covariance = np.einsum('i,ij->j', w*(b-np.dot(w,b)), self._likelihood, optimize=False)
        gain = np.divide(covariance**2, q*(1-q), out=np.zeros_like(q), where=(q>0)&(q<1))
        return np.array([np.dot(ws,gain[a:z]) for ws,a,z in zip(
            self._quadrature_weights,self._offsets[:-1],self._offsets[1:])])

    def suggest(self):
        gains = self.acquisition_values()
        tied = np.flatnonzero(np.isclose(gains,gains.max(),rtol=1e-12,atol=1e-15))
        return float(self.targets[self.rng.choice(tied)])


def _source_rates(completed):
    # Source loop schedules decay(i) only after updating the previous trial.
    if completed == 0:
        return 1., .5
    return (float(np.clip(1.-math.log10(completed/20),.01,1.)),
            float(np.clip(.5-math.log10(completed/40),.001,.5)))


class _UCB(_Base):
    def __init__(self, config, belief, rng, criterion_weighted=False):
        super().__init__(config,belief,rng)
        self.criterion_weighted = criterion_weighted
        self.confidence_scale = .2
        self.q = np.zeros(len(self.targets))
        self.counts = np.zeros(len(self.targets),dtype=int)
        self.positive_counts = np.zeros(len(self.targets),dtype=int)

    def suggest(self):
        t = len(self.history)
        epsilon, _ = _source_rates(t)
        if t == 0 or self.rng.random() < epsilon:
            arm = self.rng.integers(len(self.targets))
        else:
            score = self.q+self.confidence_scale*np.sqrt(math.log(t)/(self.counts+.1))
            arm = np.argmax(score)
        return float(self.targets[arm])

    def _update(self,o):
        arm = self.config.targets.index(o.target)
        u = (o.target-self.config.lower)/(self.config.upper-self.config.lower)
        penalty = self.config.tau/(1-self.config.tau) if self.criterion_weighted else 1.
        self.positive_counts[arm] += o.acceptable
        positive = self.positive_counts[arm]
        negative = self.counts[arm]+1-positive
        sign = o.acceptable if positive == negative else int(positive > negative)
        reward = u if sign else -penalty*u
        t = len(self.history)-1
        _, learning_rate = _source_rates(t)
        self.counts[arm] += 1
        self.q[arm] += learning_rate*(reward-self.q[arm])


class _Staircase(_Base):
    def __init__(self,config,belief,rng):
        super().__init__(config,belief,rng)
        self.state = (config.lower+config.upper)/2
        self.step, self.reversals, self._direction = .6, 0, 0

    def suggest(self):
        return float(self.targets[np.argmin(np.abs(self.targets-self.state))])

    def _update(self,o):
        direction = 1 if o.acceptable else -1
        if self._direction and direction != self._direction:
            self.reversals += 1
            if self.reversals % 2 == 0:
                self.step = max(.15,self.step/2)
        self._direction = direction
        self.state = float(np.clip(self.state+self.step*(o.acceptable-self.config.tau),
                                   self.config.lower,self.config.upper))


def make_policy(name: str, config: PolicyConfig, belief: ExecutionBelief, rng: np.random.Generator):
    if name in ('bayes_risk','bayes_point'):
        return _Bayes(config,belief,rng,point=name=='bayes_point')
    if name in ('ucb','ucb_tvcg','ucb_tau'):
        return _UCB(config,belief,rng,criterion_weighted=name == 'ucb_tau')
    if name == 'staircase':
        return _Staircase(config,belief,rng)
    raise ValueError(f'Unknown policy: {name}')
