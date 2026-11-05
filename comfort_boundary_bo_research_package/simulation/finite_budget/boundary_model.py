"""Logistic posterior in actual-acceleration boundary B and positive slope k."""
from functools import lru_cache
import math
import numpy as np
from scipy.special import expit, logsumexp
from .contracts import PriorSpec, Readout, validate_observation
from ..monotone_bayes import MonotoneBayesianLogistic, PriorGrid


def _immutable(values,dtype=float):
    a=np.ascontiguousarray(values,dtype=dtype)
    return np.frombuffer(a.tobytes(),dtype=a.dtype).reshape(a.shape)


DECISION_GRID = _immutable(np.arange(-200,201)/40)


def _validate_tau(tau):
    if not math.isfinite(tau) or not 0 < tau < 1:
        raise ValueError('tau must be in (0,1)')


@lru_cache(maxsize=8)
def _direct_grid(prior):
    b=np.linspace(prior.b_min,prior.b_max,prior.b_nodes)
    logk=np.linspace(math.log(prior.k_min),math.log(prior.k_max),prior.k_nodes)
    B,K=np.meshgrid(b,np.exp(logk),indexing='ij')
    wb,wk=np.ones(len(b)),np.ones(len(logk))
    wb[[0,-1]]=.5; wk[[0,-1]]=.5
    logw=-.5*((logk[None,:]-prior.log_k_mean)/prior.log_k_sd)**2+np.log(wb[:,None])+np.log(wk[None,:])
    if prior.kind=='normal': logw=logw-.5*((B-prior.center)/prior.sd)**2
    w=np.exp(logw-logsumexp(logw))
    return _immutable(B.ravel()),_immutable(K.ravel()),_immutable(w.ravel())


def legacy_joint_grid(tau,prior_grid=None):
    """Transport every old node and its original weight, with no regridding."""
    old=MonotoneBayesianLogistic(tau,prior_grid or PriorGrid(midpoint_nodes=81,slope_nodes=41))
    b=old._boundary_values
    _validate_support(b)
    return _immutable(b),_immutable(old.posterior_slopes),_immutable(old.posterior_weights)


def _validate_support(b):
    if np.min(b)<DECISION_GRID[0]-1e-12 or np.max(b)>DECISION_GRID[-1]+1e-12:
        raise ValueError('decision grid [-5,5] must cover all posterior B nodes; adjust explicitly before execution')


class BoundaryPosterior:
    def __init__(self,tau,prior=None):
        prior=prior or PriorSpec()
        if not isinstance(prior,PriorSpec): raise TypeError('expected PriorSpec')
        self.prior=prior
        self._initialize(tau,*_direct_grid(prior))

    @classmethod
    def from_joint_grid(cls,tau,B,k,weights):
        obj=cls.__new__(cls)
        obj.prior=None
        obj._initialize(tau,B,k,weights)
        return obj

    def _initialize(self,tau,B,k,weights):
        _validate_tau(tau)
        b,slopes,w=(np.asarray(a,dtype=float) for a in (B,k,weights))
        if (b.ndim!=1 or slopes.shape!=b.shape or w.shape!=b.shape or not len(b)
                or not np.isfinite(b).all() or not np.isfinite(slopes).all() or not np.isfinite(w).all()
                or np.any(slopes<=0) or np.any(w<0) or not math.isfinite(w.sum()) or w.sum()<=0):
            raise ValueError('joint grid must contain aligned finite B,k and nonnegative weights')
        _validate_support(b)
        self.tau=float(tau); self._offset=math.log(tau/(1-tau))
        self._B,self._k=_immutable(b),_immutable(slopes)
        w=w/w.sum()
        self._weights=_immutable(w)
        with np.errstate(divide='ignore'): self._log_weights=_immutable(np.log(w))
        self._order=np.argsort(b,kind='stable')
        self._sorted_b=b[self._order]
        # Strip endpoints preserve the integration-edge definition under exact
        # legacy transport (the B extremes differ for each slope).
        edge=(slopes==slopes.min())|(slopes==slopes.max())
        for slope in np.unique(slopes):
            indices=np.flatnonzero(slopes==slope)
            v=b[indices]
            edge[indices[(v==v.min())|(v==v.max())]]=True
        self._edge=_immutable(edge,dtype=bool)
        self._history=()
        self._basis_cache=None
        self._window_cache=None

    @property
    def B(self): return self._B
    @property
    def k(self): return self._k
    @property
    def weights(self): return self._weights
    @property
    def history(self): return self._history

    def observe(self,observation):
        o=validate_observation(observation,self.history)
        z=self._offset+self.k*(self.B-o.realized)
        ll=-np.logaddexp(0.,-z if o.acceptable else z)
        logw=self._log_weights+ll
        logw=logw-logsumexp(logw)
        self._log_weights=_immutable(logw)
        self._weights=_immutable(np.exp(logw))
        self._history+=(o,)
        return self

    def curve_probabilities(self,x,*,paired=False):
        x=np.asarray(x,dtype=float)
        if not np.isfinite(x).all(): raise ValueError('prediction inputs must be finite')
        if paired:
            if x.shape!=self.B.shape: raise ValueError('paired inputs must match posterior nodes')
            return expit(self._offset+self.k*(self.B-x))
        if x.ndim==0: return expit(self._offset+self.k*(self.B-float(x)))
        if x.ndim!=1: raise ValueError('prediction inputs must be scalar or 1-D')
        return expit(self._offset+self.k[:,None]*(self.B[:,None]-x[None,:]))

    def predict_acceptance(self,x):
        values=self.curve_probabilities(x)
        out=np.einsum('i,i...->...',self.weights,values,optimize=False)
        return float(out) if np.ndim(out)==0 else out

    def quantiles(self,qs=(.025,.5,.975)):
        cumulative=np.cumsum(self.weights[self._order]); cumulative[-1]=1.
        return self._sorted_b[np.searchsorted(cumulative,qs,side='left')]

    def window_indices(self,delta):
        if not math.isfinite(delta) or delta<=0: raise ValueError('positive delta required')
        if self._window_cache is None or self._window_cache[0]!=delta:
            left=np.searchsorted(self._sorted_b,DECISION_GRID-delta-1e-12,side='left')
            right=np.searchsorted(self._sorted_b,DECISION_GRID+delta+1e-12,side='right')
            self._window_cache=(delta,left,right)
        return self._window_cache[1:]

    def window_masses(self,delta,weights=None):
        left,right=self.window_indices(delta)
        w=self.weights if weights is None else weights
        cumulative=np.concatenate(([0.],np.cumsum(w[self._order])))
        return cumulative[right]-cumulative[left]

    def median_readout(self):
        low,median,high=self.quantiles()
        return Readout(float(median),float(low),float(high),edge_mass=float(self.weights[self._edge].sum()))

    def precision_readout(self,delta):
        masses=self.window_masses(delta)
        candidates=np.flatnonzero(np.isclose(masses,masses.max(),rtol=0,atol=1e-12))
        low,median,high=self.quantiles()
        distances=np.abs(DECISION_GRID[candidates]-median)
        nearest=candidates[np.isclose(distances,distances.min(),rtol=0,atol=1e-12)]
        z=float(DECISION_GRID[nearest[0]])
        return Readout(z,float(low),float(high),edge_mass=float(self.weights[self._edge].sum()),posterior_success=float(masses.max()))
