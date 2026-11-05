import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.boundary_model import BoundaryPosterior, DECISION_GRID
from comfort_boundary_bo_research_package.simulation.finite_budget.acquisition import variance_gain,precision_gain
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import ExecutionBelief
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.execution import execution_quadrature

@pytest.mark.parametrize('which',['precision','variance'])
def test_conditional_measured_x_enumeration(which):
    p=BoundaryPosterior.from_joint_grid(.7,[-.2,.8,1.8],[1.,3.,7.],[.2,.5,.3])
    targets=(.2,1.,2.5); belief=ExecutionBelief(.08,.92,.4)
    w=p.weights; b=p.B
    score=lambda v: max(v[np.abs(b-z)<=.15+1e-12].sum() for z in DECISION_GRID)
    base=score(w) if which=='precision' else np.sum(w*(b-w@b)**2)
    brute=[]
    for u in targets:
        xs,ws=execution_quadrature(u,belief,5)
        expected=0.
        for x,wx in zip(xs,ws):
            l=p.curve_probabilities(x)
            for likelihood in (l,1-l):
                q=w@likelihood
                post=w*likelihood/q
                future=score(post) if which=='precision' else np.sum(post*(b-post@b)**2)
                expected+=wx*q*future
        brute.append(expected-base if which=='precision' else base-expected)
    actual=(precision_gain(p,targets,belief,.15,5) if which=='precision' else variance_gain(p,targets,belief,5))
    np.testing.assert_allclose(actual,brute,atol=3e-15)
    assert actual.min()>=-2e-15

def test_point_integration_and_target_alignment():
    p=BoundaryPosterior.from_joint_grid(.7,[0.,1.,2.],[1.,2.,3.],[.3,.4,.3])
    belief=ExecutionBelief(.1,.9,0)
    for fn in (lambda n:variance_gain(p,[2.,0.,1.],belief,n),lambda n:precision_gain(p,[2.,0.,1.],belief,.15,n)):
        np.testing.assert_allclose(fn(1),fn(15),atol=2e-15)
    a=variance_gain(p,[0.,1.,2.],belief,1)
    np.testing.assert_allclose(a[[2,0,1]],variance_gain(p,[2.,0.,1.],belief,1))

def test_measured_x_is_not_permanently_latent():
    p=BoundaryPosterior.from_joint_grid(.7,[0.,1.,2.],[1.,2.,3.],[.3,.4,.3])
    b=ExecutionBelief(0,1,.9); xs,ws=execution_quadrature(1.,b,7)
    mixed=p.curve_probabilities(xs)@ws
    cov=np.dot(p.weights*(p.B-p.weights@p.B),mixed)
    q=p.weights@mixed
    assert abs(variance_gain(p,[1.],b,7)[0]-cov**2/(q*(1-q)))>1e-5
