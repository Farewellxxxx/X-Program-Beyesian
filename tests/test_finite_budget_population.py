import numpy as np
import pytest
from scipy.optimize import brentq
from comfort_boundary_bo_research_package.simulation.finite_budget.population import PopulationSpec, draw_latents, passenger_from_latent, local_derivative

@pytest.mark.parametrize('family,lapse',[('logistic',0.),('probit',0.),('lapse_logistic',.1),('lapse_logistic',.2)])
def test_paired_boundary_and_physical_transition_width(family,lapse):
    for B,W in draw_latents(4,PopulationSpec(),np.random.default_rng(3)):
        p=passenger_from_latent(B,W,family,.7,lapse)
        assert p.probability(B)==pytest.approx(.7)
        x2=brentq(lambda x:p.probability(x)-.2,B-10,B+10)
        x8=brentq(lambda x:p.probability(x)-.8,B-10,B+10)
        assert x2-x8==pytest.approx(W)
        numeric=(p.probability(B+1e-5)-p.probability(B-1e-5))/2e-5
        assert local_derivative(p)==pytest.approx(numeric,rel=1e-7)
    a=draw_latents(3,PopulationSpec(),np.random.default_rng(7))
    assert a==draw_latents(3,PopulationSpec(),np.random.default_rng(7))

def test_lapse_random_answer_interpretation_and_impossible_criteria():
    p=passenger_from_latent(1.,.7,'lapse_logistic',.7,.1)
    assert p.probability(100.)==pytest.approx(.05)
    assert p.probability(-100.)==pytest.approx(.95)
    with pytest.raises(ValueError): passenger_from_latent(1.,.7,'lapse_logistic',.95,.1)
    with pytest.raises(ValueError): passenger_from_latent(1.,.7,'lapse_logistic',.7,.4)
    with pytest.raises(ValueError): PopulationSpec(boundary_low=2.,boundary_high=1.)
