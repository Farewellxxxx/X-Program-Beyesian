"""Constrained Firth curve fit and explicitly descriptive staircase readouts."""
import math
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from .contracts import PriorSpec, Readout, _integer
from ..decoupled_calibration.public import Observation


def _data(history):
    if any(type(o) is not Observation for o in history): raise TypeError('exact public observations required')
    x=np.array([o.realized for o in history],dtype=float)
    y=np.array([o.acceptable for o in history],dtype=float)
    if not np.isfinite(x).all() or not np.isin(y,[0,1]).all(): raise ValueError('invalid fitting data')
    return x,y


def _objective(params,x,y,tau):
    B,logk=params; k=math.exp(logk)
    eta=math.log(tau/(1-tau))+k*(B-x)
    p=expit(eta); w=p*expit(-eta)
    # Centering X has determinant-one coordinate transform and hence leaves
    # the alpha/beta Jeffreys determinant unchanged, while reducing cancellation.
    X=np.column_stack([np.ones(len(x)),x-x.mean()])
    I=X.T@(w[:,None]*X)
    sign,logdet=np.linalg.slogdet(I)
    if sign<=0 or not math.isfinite(logdet): return math.inf,np.zeros(2)
    inv=np.linalg.solve(I,np.eye(2))
    leverage=w*np.einsum('ij,jk,ik->i',X,inv,X,optimize=False)
    score=y-p+.5*leverage*(1-2*p)
    ll=np.sum(np.where(y==1,-np.logaddexp(0.,-eta),-np.logaddexp(0.,eta)))
    gradient=-np.array([k*score.sum(),np.dot(score,k*(B-x))])
    return float(-ll-.5*logdet),gradient


def firth_objective(params,history,tau=.70):
    """Negative penalized log likelihood and B/log-k gradient, for audit use."""
    if not math.isfinite(tau) or not 0<tau<1: raise ValueError('invalid tau')
    x,y=_data(history)
    if len(x)<2 or np.ptp(x)==0: return math.inf,np.zeros(2)
    return _objective(params,x,y,tau)


def fit_firth(history,tau=.70,support=None):
    if not math.isfinite(tau) or not 0<tau<1: raise ValueError('invalid tau')
    support=PriorSpec() if support is None else support
    bounds4=(support.b_min,support.b_max,support.k_min,support.k_max) if isinstance(support,PriorSpec) else tuple(support)
    if len(bounds4)!=4 or not all(math.isfinite(v) for v in bounds4): raise ValueError('invalid fitting support')
    blo,bhi,klo,khi=bounds4
    if blo>=bhi or not 0<klo<khi: raise ValueError('invalid fitting support')
    x,y=_data(history)
    if not len(x): return Readout(None,status='no_data')
    if len(x)<2 or np.linalg.matrix_rank(np.column_stack([np.ones(len(x)),x]))<2:
        return Readout(None,status='rank_deficient')
    bounds=((blo,bhi),(math.log(klo),math.log(khi)))
    converged=[]
    for b in (.5,1.5,2.5):
        for k in (1.,4.,12.):
            start=np.array([np.clip(b,blo,bhi),np.clip(math.log(k),*bounds[1])])
            try:
                result=minimize(_objective,start,args=(x,y,tau),method='L-BFGS-B',jac=True,bounds=bounds,
                                options=dict(maxiter=500,ftol=1e-12,gtol=1e-8))
            except (np.linalg.LinAlgError,FloatingPointError,OverflowError):
                # A numerical failure of one prescribed start is not a missing
                # participant. Continue the other starts, then emit explicit
                # no_convergence if none supplied a valid finite solution.
                continue
            if result.success and np.isfinite(result.fun) and np.isfinite(result.x).all():
                converged.append(result)
    if not converged: return Readout(None,status='no_convergence')
    best=min(converged,key=lambda r:r.fun)
    active=[]
    for value,(low,high),names in zip(best.x,bounds,(('b_min','b_max'),('k_min','k_max'))):
        if abs(value-low)<=1e-6*max(1.,abs(low)): active.append(names[0])
        if abs(value-high)<=1e-6*max(1.,abs(high)): active.append(names[1])
    return Readout(float(best.x[0]),active_bounds=tuple(active))


def reversal_readout(history,reversal_indices,count=4):
    """Indices are actual presented trial IDs, recorded when response reverses."""
    if not _integer(count,1): raise ValueError('positive reversal count required')
    _data(history)
    by_trial={o.trial:o for o in history}
    indices=tuple(reversal_indices)
    if any(not _integer(i,1) or i not in by_trial for i in indices) or tuple(sorted(set(indices)))!=indices:
        raise ValueError('reversal indices must be distinct ordered presented trial IDs')
    selected=[by_trial[i] for i in indices[-count:]] if len(indices)>=count else []
    return dict(native_reversal_command_mean=float(np.mean([o.target for o in selected])) if selected else None,
                native_reversal_realized_mean=float(np.mean([o.realized for o in selected])) if selected else None,
                reversal_count=len(indices),used_reversal_indices=tuple(o.trial for o in selected),
                criterion='descriptive_reversal_mean_not_B_tau')
