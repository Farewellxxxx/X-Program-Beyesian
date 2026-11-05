"""Sampling uses only immutable public observations and public calibration."""
import numpy as np
from .contracts import SamplerConfig, StaircaseSpec, validate_observation, Readout
from .boundary_model import BoundaryPosterior, legacy_joint_grid
from .acquisition import variance_gain, precision_gain
from ..monotone_bayes import PriorGrid
from ..decoupled_calibration.public import PolicyConfig, ExecutionBelief
from ..decoupled_calibration.policies import make_policy
from ..decoupled_calibration.execution import execution_quadrature


class _Staircase:
    def __init__(self,config):
        self.config=config; self._history=()
        self.state=config.staircase.start; self.step=config.staircase.initial
        self._direction=0; self._reversal_indices=(); self._command_change_indices=()

    @property
    def history(self): return self._history
    @property
    def reversal_indices(self): return self._reversal_indices
    @property
    def command_change_indices(self): return self._command_change_indices
    @property
    def reversals(self): return len(self._reversal_indices)

    def suggest(self):
        targets=np.asarray(self.config.targets)
        distance=np.abs(targets-self.state)
        # Lower command resolves geometric projection ties, including roundoff.
        return float(targets[np.flatnonzero(np.isclose(distance,distance.min(),rtol=0,atol=1e-12))[0]])

    def observe(self,observation):
        o=validate_observation(observation,self.history,targets=self.config.targets,lower=self.config.lower,upper=self.config.upper)
        if self.history and o.target!=self.history[-1].target:
            self._command_change_indices+=(o.trial,)
        direction=1 if o.acceptable else -1
        if self._direction and direction!=self._direction:
            self._reversal_indices+=(o.trial,)
            if self.reversals%self.config.staircase.reversals_per_halving==0:
                self.step=max(self.config.staircase.floor,self.step/2)
        self._direction=direction
        self.state=float(np.clip(self.state+self.step*(o.acceptable-self.config.tau),self.config.lower,self.config.upper))
        self._history+=(o,)


class _Bayes:
    def __init__(self,config,belief,rng,old=False,precision=False):
        self.config,self.belief,self.rng=config,belief,rng
        self.model=(BoundaryPosterior.from_joint_grid(config.tau,*legacy_joint_grid(config.tau,
                    PriorGrid(midpoint_nodes=config.midpoint_nodes,slope_nodes=config.slope_nodes)))
                    if old else BoundaryPosterior(config.tau,config.prior))
        self.precision=precision

    @property
    def history(self): return self.model.history

    def acquisition_values(self):
        args=(self.model,self.config.targets,self.belief)
        return (precision_gain(*args,self.config.delta,self.config.quadrature_nodes) if self.precision
                else variance_gain(*args,self.config.quadrature_nodes))

    def suggest(self):
        values=self.acquisition_values()
        tied=np.flatnonzero(np.isclose(values,values.max(),rtol=1e-12,atol=1e-15))
        return float(self.config.targets[int(self.rng.choice(tied))])

    def observe(self,observation):
        o=validate_observation(observation,self.history,targets=self.config.targets,lower=self.config.lower,upper=self.config.upper)
        self.model.observe(o)

    def median_readout(self): return self.model.median_readout()
    def precision_readout(self,delta=None): return self.model.precision_readout(self.config.delta if delta is None else delta)


class _Legacy:
    def __init__(self,name,config,belief,rng):
        self.config=config
        legacy=PolicyConfig(config.tau,config.lower,config.upper,config.targets,
                            config.midpoint_nodes,config.slope_nodes,config.quadrature_nodes)
        self.delegate=make_policy(name,legacy,belief,rng)

    @property
    def history(self): return self.delegate.history
    @property
    def model(self): return self.delegate.model
    def suggest(self): return self.delegate.suggest()
    def observe(self,o): self.delegate.observe(o)
    def estimate(self): return self.delegate.estimate()
    def acquisition_values(self): return self.delegate.acquisition_values()
    def median_readout(self):
        e=self.delegate.estimate()
        return Readout(e.boundary,e.lower,e.upper,edge_mass=e.edge_mass)
    def precision_readout(self,delta=None):
        p=BoundaryPosterior.from_joint_grid(self.config.tau,self.model._boundary_values,
                                           self.model.posterior_slopes,self.model.posterior_weights)
        return p.precision_readout(self.config.delta if delta is None else delta)
    def native_command(self):
        if not hasattr(self.delegate,'q'): raise TypeError('native command applies to UCB')
        return float(self.config.targets[int(np.argmax(self.delegate.q))])


def make_sampler(name,public_config,belief,rng):
    if not isinstance(public_config,SamplerConfig) or not isinstance(belief,ExecutionBelief):
        raise TypeError('expected public SamplerConfig and ExecutionBelief')
    if not isinstance(rng,np.random.Generator): raise TypeError('expected NumPy Generator')
    execution_quadrature(public_config.lower,belief,public_config.quadrature_nodes)
    if name in ('old_variance','bayes_risk'):
        return _Legacy('bayes_risk',public_config,belief,rng)
    if name=='ucb_tvcg': return _Legacy('ucb_tvcg',public_config,belief,rng)
    if name=='staircase': return _Staircase(public_config)
    if name in ('new_variance','new_precision','old_precision'):
        return _Bayes(public_config,belief,rng,old=name=='old_precision',precision=name.endswith('precision'))
    raise ValueError(f'unsupported sampler: {name}')
