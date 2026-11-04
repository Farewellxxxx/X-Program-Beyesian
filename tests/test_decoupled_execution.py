import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.execution import ExecutionTruth, execute, calibrate_execution, execution_quadrature, spawn_streams
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import ExecutionBelief

def test_execution_clips_and_reproduces():
    truth=ExecutionTruth(.1,1.1,.2)
    assert execute(-100,truth,np.random.default_rng(0)) == 0
    assert execute(100,truth,np.random.default_rng(0)) == 3
    assert execute(1,truth,np.random.default_rng(0)) == execute(1,truth,np.random.default_rng(0))

def test_calibration_recovers_affine_model():
    truth=ExecutionTruth(.1,.9,.06)
    b=calibrate_execution(truth,np.random.default_rng(2),n=10000)
    assert b.intercept == pytest.approx(.1,abs=.006)
    assert b.gain == pytest.approx(.9,abs=.006)
    assert b.sd == pytest.approx(.06,abs=.003)

def test_quadrature_normalization_clipping_and_moments():
    x,w=execution_quadrature(1,ExecutionBelief(.1,.9,.2),nodes=9)
    assert np.sum(w) == pytest.approx(1)
    assert np.sum(x*w) == pytest.approx(1,abs=1e-10)
    assert np.sum((x-1)**2*w) == pytest.approx(.04,abs=1e-10)
    x,w=execution_quadrature(0,ExecutionBelief(-.5,1,.3))
    assert np.any(x==0) and np.all((x>=0)&(x<=3))
    x,w=execution_quadrature(9,ExecutionBelief(0,1,0))
    assert x.tolist()==[3] and w.tolist()==[1]

def test_semantic_rng_stream_isolation():
    a=spawn_streams(12,4,0); b=spawn_streams(12,4,1); c=spawn_streams(12,4,0)
    for name in ['population','execution_calibration']:
        assert a[name].random() == b[name].random() == c[name].random()
    a['feedback'].random(200)
    assert a['execution'].random() == c['execution'].random()
    assert b['policy'].random() != c['policy'].random()

@pytest.mark.parametrize('args', [(0,1,-1),(0,0,.1),(float('nan'),1,.1),(0,1,.1,3,0)])
def test_invalid_truth(args):
    with pytest.raises(ValueError): ExecutionTruth(*args)

def test_invalid_quadrature_and_calibration():
    with pytest.raises(ValueError): execution_quadrature(1,ExecutionBelief(0,1,-.1))
    with pytest.raises(ValueError): execution_quadrature(1,ExecutionBelief(0,1,.1),nodes=0)
    with pytest.raises(ValueError): calibrate_execution(ExecutionTruth(0,1,.1),np.random.default_rng(0),n=2)

@pytest.mark.parametrize('keys', [(-1,0,0),(0,-1,0),(0,0,-1),(0,0,1.5)])
def test_invalid_stream_keys(keys):
    with pytest.raises(ValueError): spawn_streams(*keys)

def test_calibration_is_reproducible_and_population_is_method_independent():
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration.passenger import generate_passengers
    a=spawn_streams(71,0,1); b=spawn_streams(71,0,5)
    assert generate_passengers(20,'probit',.7,a['population']) == generate_passengers(20,'probit',.7,b['population'])
    truth=ExecutionTruth(.1,.9,.1)
    assert calibrate_execution(truth,a['execution_calibration']) == calibrate_execution(truth,b['execution_calibration'])
