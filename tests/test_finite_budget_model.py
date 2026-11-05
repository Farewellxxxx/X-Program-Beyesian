from dataclasses import replace
import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import PriorSpec
from comfort_boundary_bo_research_package.simulation.finite_budget.boundary_model import BoundaryPosterior, legacy_joint_grid, DECISION_GRID
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation
from comfort_boundary_bo_research_package.simulation.monotone_bayes import MonotoneBayesianLogistic, PriorGrid
from comfort_boundary_bo_research_package.simulation.finite_budget.acquisition import variance_gain
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import PolicyConfig,ExecutionBelief
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.policies import make_policy

def test_crossing_prior_marginals_and_immutable_arrays():
    p = BoundaryPosterior(.7,PriorSpec(b_nodes=121,k_nodes=41))
    assert np.sum(p.weights) == pytest.approx(1)
    assert np.dot(p.B,p.weights) == pytest.approx(1.5)
    assert p.median_readout().boundary == pytest.approx(1.5)
    np.testing.assert_allclose(p.curve_probabilities(p.B,paired=True),.7)
    for a in (p.B,p.k,p.weights):
        with pytest.raises(ValueError): a[0]=2
    weak=BoundaryPosterior(.7,PriorSpec(kind='uniform',b_nodes=9,k_nodes=5))
    assert weak.weights.reshape(9,5).sum(axis=1)[0] == pytest.approx(.5/8)

def test_exact_old_joint_transport_predictions_updates_and_decisions():
    g=PriorGrid(midpoint_nodes=13,slope_nodes=9)
    old=MonotoneBayesianLogistic(.7,g)
    B,k,w=legacy_joint_grid(.7,g)
    p=BoundaryPosterior.from_joint_grid(.7,B,k,w)
    assert len(B)==117 and B.min() < -1.5
    for trial,(x,y) in enumerate([(.3,1),(.9,1),(1.5,0),(2.1,0)],1):
        p.observe(Observation(trial,x,x,y))
    old.fit([.3,.9,1.5,2.1],[1,1,0,0])
    np.testing.assert_allclose(p.weights,old.posterior_weights,atol=2e-16)
    np.testing.assert_allclose(p.predict_acceptance([0.,1.,2.,3.]),old.predict_array(np.array([0.,1.,2.,3.]))[0],atol=2e-15)
    assert p.median_readout().boundary == old.estimate_boundary()
    assert p.median_readout().edge_mass == pytest.approx(old.boundary_summary()['posterior_grid_edge_mass'])

def test_stable_extreme_histories_no_clipping_and_truth_firewall():
    for y in (0,1):
        p=BoundaryPosterior(.7,PriorSpec(b_nodes=17,k_nodes=9))
        for t in range(1,101): p.observe(Observation(t,0. if y==0 else 3.,0. if y==0 else 3.,y))
        assert np.isfinite(p.weights).all() and p.weights.sum()==pytest.approx(1)
        assert p.median_readout().boundary < 0 if y==0 else p.median_readout().boundary > 3
    class Hidden(Observation): secret=1.
    with pytest.raises(TypeError): p.observe(Hidden(101,1.,1.,1))
    assert len(p.history)==100

def test_decision_grid_inclusion_ties_and_support_validation():
    p=BoundaryPosterior.from_joint_grid(.7,[-.15,.15],[1.,1.],[.5,.5])
    assert p.precision_readout(.15).boundary == pytest.approx(0.)
    assert p.precision_readout(.15).posterior_success == pytest.approx(1.)
    # Equal isolated windows: nearest posterior median, then smaller center.
    q=BoundaryPosterior.from_joint_grid(.7,[0.,1.],[1.,1.],[.5,.5])
    assert q.precision_readout(.01).boundary == pytest.approx(0.)
    assert len(DECISION_GRID)==401
    with pytest.raises(ValueError): BoundaryPosterior.from_joint_grid(.7,[-5.01,1.],[1.,1.],[.5,.5])
    with pytest.raises(ValueError): legacy_joint_grid(.99,PriorGrid())

def test_transport_preserves_legacy_variance_acquisition_and_decisions():
    config=PolicyConfig(midpoint_nodes=13,slope_nodes=9,quadrature_nodes=5)
    belief=ExecutionBelief(.08,.92,.18)
    old=make_policy('bayes_risk',config,belief,np.random.default_rng(4))
    posterior=BoundaryPosterior.from_joint_grid(.7,*legacy_joint_grid(.7,PriorGrid(midpoint_nodes=13,slope_nodes=9)))
    for t,(x,y) in enumerate([(.3,1),(.9,1),(1.5,0),(2.1,0)],1):
        o=Observation(t,x,x,y); old.observe(o); posterior.observe(o)
    a=old.acquisition_values()
    b=variance_gain(posterior,config.targets,belief,config.quadrature_nodes)
    np.testing.assert_allclose(a,b,atol=2e-15,rtol=2e-13)
    np.testing.assert_array_equal(np.flatnonzero(np.isclose(a,a.max(),rtol=1e-12,atol=1e-15)),
                                  np.flatnonzero(np.isclose(b,b.max(),rtol=1e-12,atol=1e-15)))
