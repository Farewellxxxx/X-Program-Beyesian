import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.passenger import Passenger, generate_passengers

@pytest.mark.parametrize('family', ['logistic', 'probit', 'lapse_logistic'])
def test_boundary_monotonicity_and_asymptotes(family):
    people = generate_passengers(15, family, .7, np.random.default_rng(8))
    for p in people:
        assert p.probability(p.boundary) == pytest.approx(.7, abs=1e-12)
        assert np.all(np.diff([p.probability(x) for x in np.linspace(-10, 10, 101)]) <= 0)
        assert p.probability(-1e6) == pytest.approx(1-p.lapse/2)
        assert p.probability(1e6) == pytest.approx(p.lapse/2)

def test_response_frequency_and_reproducibility():
    p = generate_passengers(1, 'probit', .7, np.random.default_rng(3))[0]
    a = np.random.default_rng(4)
    b = np.random.default_rng(4)
    assert [p.respond(p.boundary,a) for _ in range(100)] == [p.respond(p.boundary,b) for _ in range(100)]
    assert np.mean([p.respond(p.boundary,a) for _ in range(20000)]) == pytest.approx(.7,abs=.015)
    assert p == generate_passengers(1, 'probit', .7, np.random.default_rng(3))[0]

@pytest.mark.parametrize('n,family,tau', [(-1,'logistic',.7),(1,'bad',.7),(1,'probit',1),(1,'lapse_logistic',.99)])
def test_invalid_population(n,family,tau):
    with pytest.raises(ValueError): generate_passengers(n,family,tau,np.random.default_rng(0))

def test_nonfinite_realization():
    p=generate_passengers(1,'logistic',.7,np.random.default_rng(0))[0]
    with pytest.raises(ValueError): p.probability(float('nan'))

@pytest.mark.parametrize('kwargs', [{'slope':0},{'lapse':1},{'boundary':float('inf')},{'tau':0}])
def test_invalid_passenger_parameters(kwargs):
    parameters=dict(boundary=1,family='logistic',slope=4,lapse=0,tau=.7)
    parameters.update(kwargs)
    with pytest.raises(ValueError): Passenger(**parameters)

def test_generator_has_no_policy_inference_dependency():
    import inspect
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration import passenger
    source=inspect.getsource(passenger)
    assert 'monotone_bayes' not in source
    assert 'from .policies' not in source
