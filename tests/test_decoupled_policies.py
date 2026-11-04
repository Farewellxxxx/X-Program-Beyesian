import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation, PolicyConfig, ExecutionBelief
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.policies import make_policy

CFG = PolicyConfig(midpoint_nodes=7, slope_nodes=5, quadrature_nodes=5)
BELIEF = ExecutionBelief(0, 1, .2)

def policy(name='bayes_risk', belief=BELIEF, seed=1):
    return make_policy(name, CFG, belief, np.random.default_rng(seed))

def test_exact_conditional_risk_against_brute_force():
    p = policy()
    p.observe(Observation(1, 1.5, 1.6, 1))
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration.execution import execution_quadrature
    w, b = p.model.posterior_weights, p.model._boundary_values
    variance = np.sum(w*(b-np.sum(w*b))**2)
    brute = []
    for target in CFG.targets:
        xs, ws = execution_quadrature(target, BELIEF, CFG.quadrature_nodes)
        risk = 0.
        for x, wx in zip(xs, ws):
            l = 1/(1+np.exp(-p.model.posterior_slopes*(p.model.posterior_midpoints-x)))
            for likelihood in (l, 1-l):
                q = np.sum(w*likelihood)
                if q > 0:
                    post = w*likelihood/q
                    risk += wx*q*np.sum(post*(b-np.sum(post*b))**2)
        brute.append(variance-risk)
    np.testing.assert_allclose(p.acquisition_values(), brute, atol=2e-14)
    assert np.min(p.acquisition_values()) >= 0

def test_point_zero_noise_equivalence():
    a, b = policy(belief=ExecutionBelief(.1,.9,0)), policy('bayes_point', ExecutionBelief(.1,.9,0))
    np.testing.assert_allclose(a.acquisition_values(), b.acquisition_values())
    assert a.suggest() == b.suggest()

@pytest.mark.parametrize('name', ['bayes_risk','bayes_point','ucb_tvcg','ucb_tau','staircase'])
def test_common_estimator_and_whitelist(name):
    p, reference = policy(name), policy()
    observations = [Observation(1,.5,.6,1), Observation(2,2.,2.2,0)]
    for o in observations:
        p.observe(o); reference.observe(o)
    assert p.estimate() == reference.estimate()
    assert p.history == tuple(observations)
    assert p.suggest() in CFG.targets
    with pytest.raises(TypeError): p.observe({'realized':1,'acceptable':1,'truth':2})
    for o in [Observation(3,1,1,2), Observation(3,1,float('nan'),1), Observation(3,1,4,1)]:
        with pytest.raises(ValueError): p.observe(o)
    assert p.history == tuple(observations)

def test_history_isolation_and_reproducibility():
    a,b,c = policy(),policy(),policy()
    c.observe(Observation(1,1,1,0))
    assert a.history == b.history == ()
    assert a.suggest() == b.suggest()
    assert a.estimate() == b.estimate()

def test_staircase_continuous_drift_and_reversal_schedule():
    a,b = policy('staircase'),policy('staircase')
    initial=a.state
    a.observe(Observation(1,1.5,1.5,1)); b.observe(Observation(1,1.5,1.5,0))
    assert CFG.tau*(a.state-initial)+(1-CFG.tau)*(b.state-initial) == pytest.approx(0)
    assert a.state == pytest.approx(1.68)
    assert a.suggest() == pytest.approx(1.7)
    a.observe(Observation(2,1.7,1.7,0)); a.observe(Observation(3,1.3,1.3,1))
    assert a.step == pytest.approx(.3)

def test_ucb_target_arm_and_no_forced_minimum():
    p=policy('ucb')
    assert p.suggest() in CFG.targets
    assert p.counts.sum() == 0
    p.observe(Observation(1,1.,2.,1))
    assert p.counts[10] == 1 and p.counts[20] == 0
    assert p.q[10] == pytest.approx(.5/3)
    assert p.estimate().boundary == policy().model.fit([2.],[1]).estimate_boundary()

def test_ucb_primary_and_secondary_explicit_reward():
    primary, secondary = policy('ucb_tvcg'), policy('ucb_tau')
    for p in (primary, secondary):
        p.observe(Observation(1,1.,1.2,0))
    assert primary.q[10] == pytest.approx(-.5/3)
    assert secondary.q[10] == pytest.approx(-.5*CFG.tau/(1-CFG.tau)/3)

def test_measured_x_gain_differs_from_permanently_latent_mixture():
    p = policy(belief=ExecutionBelief(0,1,.9))
    w,b=p.model.posterior_weights,p.model._boundary_values
    averaged = p._likelihood[:,p._offsets[15]:p._offsets[16]] @ p._quadrature_weights[15]
    q=np.dot(w,averaged)
    latent=np.dot(w*(b-np.dot(w,b)),averaged)**2/(q*(1-q))
    assert abs(p.acquisition_values()[15]-latent)>1e-5

@pytest.mark.parametrize('name',['bayes_risk','bayes_point','ucb_tvcg','ucb_tau','staircase'])
def test_grid_outputs_across_many_observations_and_extreme_support(name):
    p=policy(name)
    for trial in range(1,41):
        target=p.suggest()
        assert target in CFG.targets
        p.observe(Observation(trial,target,target,1))
    assert p.estimate().support=='all_accept'
    q=policy(name)
    for trial in range(1,41):
        q.observe(Observation(trial,0.,0.,0))
    assert q.estimate().support=='all_reject'
    assert q.estimate().boundary<0  # no clipping of out-of-domain readout

def test_subclass_with_hidden_fields_is_rejected():
    class HiddenObservation(Observation):
        secret_boundary=1.2
    with pytest.raises(TypeError):
        policy().observe(HiddenObservation(1,1.,1.,1))

@pytest.mark.parametrize('name',['bayes_point','ucb_tvcg','staircase'])
def test_invalid_public_belief_rejected_by_every_policy(name):
    with pytest.raises(ValueError):
        policy(name, ExecutionBelief(0,1,-.1))

def test_ucb_majority_tie_disagreement_and_raw_estimator():
    p=policy('ucb_tvcg')
    for i,y in enumerate([1,1,0,0,0],1):
        p.observe(Observation(i,1.,1.2,y))
        # Majority signs: +,+,+,raw-minus(tie),minus.
        expected_signs=[1,1,1,-1,-1]
        expected=0.
        for sign in expected_signs[:i]:
            expected += .5*(sign/3-expected)
        assert p.q[10] == pytest.approx(expected)
    reference=policy()
    for o in p.history: reference.observe(o)
    assert p.estimate()==reference.estimate()
    assert policy('ucb').criterion_weighted is False

def test_ucb_confidence_reward_scale_invariance():
    p=policy('ucb_tvcg')
    assert p.confidence_scale == pytest.approx(.2)
    q=np.array([.1,.4,.2]); counts=np.array([2,10,5]); t=17
    normalized=q+p.confidence_scale*np.sqrt(np.log(t)/(counts+.1))
    original=10*q+2*np.sqrt(np.log(t)/(counts+.1))
    np.testing.assert_allclose(normalized,original/10)

def test_ucb_source_previous_loop_rate_indexing():
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration.policies import _source_rates
    assert _source_rates(0)==(1.,.5)
    assert _source_rates(20)[0]==pytest.approx(1.)
    assert _source_rates(21)[0]==pytest.approx(1-np.log10(21/20))
    assert _source_rates(40)[1]==pytest.approx(.5)
    assert _source_rates(41)[1]==pytest.approx(.5-np.log10(41/40))
