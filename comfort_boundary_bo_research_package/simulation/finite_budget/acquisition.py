"""One-step gains condition on measured X before averaging execution noise."""
import numpy as np
from ..decoupled_calibration.execution import execution_quadrature
from ..decoupled_calibration.public import ExecutionBelief


def _basis(posterior,targets,belief,nodes):
    targets=tuple(float(u) for u in targets)
    if not isinstance(belief,ExecutionBelief): raise TypeError('expected public ExecutionBelief')
    if not targets or not np.isfinite(targets).all(): raise ValueError('finite nonempty commands required')
    key=(targets,belief,nodes)
    cached=posterior._basis_cache
    if cached is None or cached[0]!=key:
        pairs=[execution_quadrature(u,belief,nodes) for u in targets]
        xs=np.concatenate([x for x,w in pairs])
        offsets=np.cumsum([0]+[len(x) for x,w in pairs])
        likelihood=posterior.curve_probabilities(xs)
        likelihood.setflags(write=False)
        cached=(key,likelihood,tuple(w for x,w in pairs),offsets)
        # Exactly one basis per active posterior, never an unbounded/shared
        # collection of ~75 MB refined-grid execution matrices.
        posterior._basis_cache=cached
    return cached[1:]


def _integrate(gains,quadrature,offsets):
    return np.array([np.dot(w,gains[a:z]) for w,a,z in zip(quadrature,offsets[:-1],offsets[1:])])


def variance_gain(posterior,targets,belief,nodes=7):
    likelihood,quadrature,offsets=_basis(posterior,targets,belief,nodes)
    w,b=posterior.weights,posterior.B
    q=np.einsum('i,ij->j',w,likelihood,optimize=False)
    covariance=np.einsum('i,ij->j',w*(b-np.dot(w,b)),likelihood,optimize=False)
    gain=np.divide(covariance**2,q*(1-q),out=np.zeros_like(q),where=(q>0)&(q<1))
    return _integrate(gain,quadrature,offsets)


def precision_gain(posterior,targets,belief,delta,nodes=7):
    likelihood,quadrature,offsets=_basis(posterior,targets,belief,nodes)
    left,right=posterior.window_indices(delta)
    order=posterior._order
    # Joint (window,Y=1) masses suffice: Y=0 is the current mass minus
    # that joint mass. Normalizing each conditional posterior cancels with
    # P(Y|X), so zero-probability outcomes need no special pseudo-update.
    weighted=likelihood[order,:]*posterior.weights[order,None]
    cumulative=np.empty((len(order)+1,weighted.shape[1]))
    cumulative[0]=0.
    np.cumsum(weighted,axis=0,out=cumulative[1:])
    joint_one=cumulative[right]-cumulative[left]
    current=posterior.window_masses(delta)
    expected=np.max(joint_one,axis=0)+np.max(current[:,None]-joint_one,axis=0)
    gain=expected-current.max()
    if np.any(gain < -1e-10): raise ArithmeticError('precision gain violates expected-information inequality')
    return _integrate(np.maximum(gain,0.),quadrature,offsets)
