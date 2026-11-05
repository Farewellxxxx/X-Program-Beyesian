import math
import numpy as np
import pytest
from scipy.optimize._numdiff import approx_derivative
from scipy.special import expit
from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import PriorSpec
from comfort_boundary_bo_research_package.simulation.finite_budget.readouts import fit_firth, firth_objective, reversal_readout
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation

def history(xs,ys): return tuple(Observation(i,float(round(x,1)),float(x),int(y)) for i,(x,y) in enumerate(zip(xs,ys),1))

def test_firth_penalty_in_alpha_beta_coordinates_and_analytic_gradient():
    h=history([.3,.8,1.2,1.8,2.7],[1,1,0,1,0]); tau=.7
    params=np.array([1.3,math.log(3.)]); B,logk=params; k=math.exp(logk)
    x=np.array([o.realized for o in h]); y=np.array([o.acceptable for o in h])
    eta=math.log(tau/(1-tau))+k*(B-x); p=expit(eta)
    X=np.column_stack([np.ones(len(x)),x]); I=X.T@np.diag(p*(1-p))@X
    expected=-np.sum(y*eta-np.logaddexp(0,eta))-.5*np.linalg.slogdet(I)[1]
    value,grad=firth_objective(params,h,tau)
    assert value==pytest.approx(expected,abs=1e-12)
    numeric=approx_derivative(lambda a:firth_objective(a,h,tau)[0],params).ravel()
    np.testing.assert_allclose(grad,numeric,atol=2e-7)

def test_separation_finite_fit_no_invented_interval_and_rank_failure():
    h=history([.3,.6,.9,1.5,1.8,2.1],[1,1,1,0,0,0])
    r=fit_firth(h,.7,PriorSpec())
    assert r.status=='ok' and math.isfinite(r.boundary)
    assert r.lower is r.upper is r.posterior_success is None
    assert fit_firth(history([1.,1.],[1,0]),.7,PriorSpec()).status=='rank_deficient'
    assert fit_firth((),.7,PriorSpec()).status=='no_data'
    # All-one labels may return a finite fit but remain unsupported by metrics.
    assert fit_firth(history([.2,.6,1.],[1,1,1]),.7,PriorSpec()).status=='ok'
    constrained=fit_firth(h,.7,PriorSpec(b_min=-1.,b_max=0.))
    assert constrained.status=='ok' and 'b_max' in constrained.active_bounds
    assert constrained.boundary<=0

def test_firth_order_invariance_and_nonmonotone_labels():
    h=history([0.,.5,1.,1.5,2.,2.5,3.],[0,1,1,0,1,0,1])
    a=fit_firth(h,.7,PriorSpec()); b=fit_firth(h[::-1],.7,PriorSpec())
    assert a.status==b.status=='ok'
    assert a.boundary==pytest.approx(b.boundary,abs=1e-6)

def test_reversal_presented_indices_and_labels():
    h=history([.3,.9,1.5,2.1,2.7],[1,0,1,0,1])
    h=tuple(Observation(o.trial,0.,o.realized,o.acceptable) for o in h)
    r=reversal_readout(h,(2,3,4,5))
    assert r['native_reversal_command_mean']==0
    assert r['native_reversal_realized_mean']==pytest.approx(1.8)
    assert r['criterion']=='descriptive_reversal_mean_not_B_tau'
    assert reversal_readout(h,(2,3))['native_reversal_command_mean'] is None
    with pytest.raises(ValueError): reversal_readout(h,(0,2,3,4))

def test_failed_firth_starts_are_retained_as_failure_and_all_nine_are_attempted(monkeypatch):
    import comfort_boundary_bo_research_package.simulation.finite_budget.readouts as module
    from types import SimpleNamespace
    starts=[]
    def fail(fun,start,**kwargs):
        starts.append(tuple(start))
        return SimpleNamespace(success=False,fun=math.inf,x=start)
    monkeypatch.setattr(module,'minimize',fail)
    r=fit_firth(history([.3,1.,2.],[1,1,0]),.7,PriorSpec())
    assert r.status=='no_convergence' and r.boundary is None
    assert starts==[(b,math.log(k)) for b in (.5,1.5,2.5) for k in (1.,4.,12.)]

def test_one_numerically_failed_firth_start_does_not_abort_remaining_starts(monkeypatch):
    import comfort_boundary_bo_research_package.simulation.finite_budget.readouts as module
    real=module.minimize
    starts=[]
    def sometimes_fail(fun,start,**kwargs):
        starts.append(tuple(start))
        if len(starts)==1: raise np.linalg.LinAlgError('numerical singularity')
        return real(fun,start,**kwargs)
    monkeypatch.setattr(module,'minimize',sometimes_fail)
    r=fit_firth(history([.3,.9,1.5,2.1],[1,1,0,0]),.7,PriorSpec())
    assert r.status=='ok' and len(starts)==9

def test_firth_programming_errors_are_not_masked(monkeypatch):
    import comfort_boundary_bo_research_package.simulation.finite_budget.readouts as module
    def broken(*args,**kwargs): raise TypeError('implementation bug')
    monkeypatch.setattr(module,'minimize',broken)
    with pytest.raises(TypeError): fit_firth(history([.3,2.1],[1,0]),.7,PriorSpec())
