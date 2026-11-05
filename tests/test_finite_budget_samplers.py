from dataclasses import replace
import inspect
import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import SamplerConfig, PriorSpec, StaircaseSpec
from comfort_boundary_bo_research_package.simulation.finite_budget.samplers import make_sampler
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation, ExecutionBelief, PolicyConfig
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.policies import make_policy

CFG=SamplerConfig(prior=PriorSpec(b_nodes=13,k_nodes=7),midpoint_nodes=9,slope_nodes=7,quadrature_nodes=3)
BELIEF=ExecutionBelief(0,1,.1)

def sampler(name='staircase',cfg=CFG,seed=1): return make_sampler(name,cfg,BELIEF,np.random.default_rng(seed))

def test_staircase_drift_halving_clamp_and_presented_reversals():
    a,b=sampler(),sampler()
    a.observe(Observation(1,1.5,1.6,1)); b.observe(Observation(1,1.5,1.6,0))
    assert .7*(a.state-1.5)+.3*(b.state-1.5)==pytest.approx(0)
    assert a.state==pytest.approx(1.68) and a.suggest()==pytest.approx(1.7)
    for t,y in enumerate([0,1,0,1],2): a.observe(Observation(t,a.suggest(),a.suggest(),y))
    assert a.step==.15 and a.reversal_indices==(2,3,4,5)
    assert a.command_change_indices==(2,3,5)  # trial 4 repeats projected 1.3
    for t in range(6,30): a.observe(Observation(t,a.suggest(),a.suggest(),0))
    assert a.state==0. and a.suggest()==0.
    # Repeated projected commands are not themselves reversals.
    c=sampler(cfg=replace(CFG,staircase=StaircaseSpec(initial=.1,floor=.1,start=0.)))
    for t in range(1,5): c.observe(Observation(t,c.suggest(),c.suggest(),0))
    assert c.reversal_indices==() and c.command_change_indices==()
    c.observe(Observation(5,0.,0.,1))
    assert c.reversal_indices==(5,) and c.command_change_indices==()

def test_staircase_projection_tie_start_and_readout_isolation():
    c=sampler(cfg=replace(CFG,staircase=StaircaseSpec(start=.35)))
    assert c.suggest()==pytest.approx(.3)
    with pytest.raises(TypeError): c.observe({'truth':1.})
    assert c.history==()
    a,b=sampler('new_precision'),sampler('new_precision')
    for t,y in enumerate([1,0,1],1):
        assert a.suggest()==b.suggest()
        o=Observation(t,1.,1.2,y); a.observe(o); b.observe(o)
        a.precision_readout(.1); a.median_readout()
    assert a.history==b.history
    assert a.suggest()==b.suggest()

@pytest.mark.parametrize('name,legacy',[('old_variance','bayes_risk'),('ucb_tvcg','ucb_tvcg')])
def test_legacy_delegation_exact(name,legacy):
    p=sampler(name)
    config=PolicyConfig(tau=CFG.tau,targets=CFG.targets,midpoint_nodes=9,slope_nodes=7,quadrature_nodes=3)
    old=make_policy(legacy,config,BELIEF,np.random.default_rng(1))
    for t,y in enumerate([1,1,0,1,0],1):
        assert p.suggest()==old.suggest()
        o=Observation(t,1.,1.2,y); p.observe(o); old.observe(o)
    assert p.median_readout().boundary==old.estimate().boundary
    if name=='ucb_tvcg': assert p.native_command()==CFG.targets[int(np.argmax(old.q))]

def test_all_sampler_names_public_histories_and_no_truth_signature():
    import comfort_boundary_bo_research_package.simulation.finite_budget.samplers as module
    assert 'population' not in inspect.getsource(module) and 'metrics' not in inspect.getsource(module)
    for name in ['old_variance','old_precision','new_variance','new_precision','staircase','ucb_tvcg']:
        p=sampler(name)
        p.observe(Observation(1,1.,1.,1))
        assert isinstance(p.history,tuple) and p.suggest() in CFG.targets
        class Hidden(Observation): secret=1.
        with pytest.raises(TypeError): p.observe(Hidden(2,1.,1.,0))
    with pytest.raises(ValueError): sampler('unregistered')

def test_nonprimary_domain_is_rejected_explicitly():
    with pytest.raises(ValueError): SamplerConfig(upper=4.)
