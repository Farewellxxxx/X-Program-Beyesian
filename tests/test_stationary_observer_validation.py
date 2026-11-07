import sys

import numpy as np
import pytest
from scipy.optimize import brentq
from scipy.stats import gumbel_l

from comfort_boundary_bo_research_package.simulation.finite_budget.population import (
    local_derivative,
    passenger_from_latent,
)
from comfort_boundary_bo_research_package.simulation.finite_budget.study import effective_config


@pytest.mark.parametrize("tau,width", [(0.61, 0.35), (0.70, 0.70), (0.83, 1.40)])
def test_gumbel_matches_left_gumbel_survival_and_physical_width(tau, width):
    boundary = 1.5
    passenger = passenger_from_latent(boundary, width, "gumbel", tau)
    scale = width / (gumbel_l.isf(0.2) - gumbel_l.isf(0.8))
    loc = boundary - scale * gumbel_l.isf(tau)
    xs = np.linspace(boundary - 3 * width, boundary + 3 * width, 61)
    actual = np.array([passenger.probability(x) for x in xs])
    np.testing.assert_allclose(actual, gumbel_l.sf(xs, loc=loc, scale=scale), atol=2e-15)
    assert np.all(np.diff(actual) <= 0)
    assert passenger.probability(boundary) == pytest.approx(tau)
    roots = [
        brentq(lambda x: passenger.probability(x) - p, xs[0], xs[-1])
        for p in (0.8, 0.2)
    ]
    assert roots[1] - roots[0] == pytest.approx(width)
    assert local_derivative(passenger) == pytest.approx(-gumbel_l.pdf(boundary, loc=loc, scale=scale))
    step = width * 1e-5
    difference = (passenger.probability(boundary + step) - passenger.probability(boundary - step))
    assert local_derivative(passenger) == pytest.approx(difference / (2 * step), rel=1e-8)


def test_gumbel_finite_extreme_inputs_are_warning_free():
    passenger = passenger_from_latent(1.5, 0.7, "gumbel")
    with np.errstate(over="raise", invalid="raise", under="raise"):
        assert passenger.probability(-np.float64(sys.float_info.max)) == 1.0
        assert passenger.probability(np.float64(sys.float_info.max)) == 0.0
        assert passenger.probability(1000.0) == 0.0
    assert passenger.probability(3.0) > 0.0


def test_gumbel_scales_finite_inputs_when_physical_difference_overflows():
    passenger = passenger_from_latent(-1e308, 1e308, "gumbel")
    expected_z = gumbel_l.isf(0.70) + 2 * (gumbel_l.isf(0.2) - gumbel_l.isf(0.8))
    assert passenger.probability(1e308) == pytest.approx(gumbel_l.sf(expected_z), rel=1e-13, abs=0)


@pytest.mark.parametrize("width", [0.0, -0.1, float("nan"), float("inf"), 5e-324])
def test_gumbel_rejects_invalid_width_or_nonfinite_slope(width):
    with pytest.raises(ValueError):
        passenger_from_latent(1.5, width, "gumbel")


@pytest.mark.parametrize("tau", [0.0, 1.0, float("nan"), float("inf")])
def test_gumbel_rejects_invalid_tau(tau):
    with pytest.raises(ValueError):
        passenger_from_latent(1.5, 0.7, "gumbel", tau)


@pytest.mark.parametrize(
    "family,probabilities,derivative,responses",
    [
        ("logistic", (0.9998076935772263, 0.980833654539172, 0.7299999999999999,
                      0.38327047254544844, 0.004933723194288601),
         -0.8279958138688802, "111001111011010110001100011000"),
        ("probit", (0.9999999022015751, 0.9917591458486987, 0.7299999999999999,
                    0.3898094950890379, 0.0006573806672285909),
         -0.8432675465849006, "111001111011010110001100011010"),
        ("lapse_logistic", (0.9499551697682252, 0.9405181539459442, 0.73,
                            0.37334706150343583, 0.0518462925424152),
         -0.8106798373742136, "111011111011010110001100011000"),
    ],
)
def test_existing_probability_and_response_stream_match_baseline(family, probabilities, derivative, responses):
    passenger = passenger_from_latent(1.3, 0.66, family, 0.73, 0.1)
    xs = [-0.5, 0.6, 1.3, 1.65, 2.8]
    # Baseline 4b9e7e3 on the study runtime. Allow roundoff across platforms.
    np.testing.assert_allclose([passenger.probability(x) for x in xs], probabilities, rtol=1e-14)
    assert local_derivative(passenger) == pytest.approx(derivative, rel=1e-14)
    rng = np.random.default_rng(202611052)
    assert "".join(str(passenger.respond(xs[i % len(xs)], rng)) for i in range(30)) == responses


def test_gumbel_is_explicitly_configurable_and_original_defaults_remain_six():
    config = effective_config({
        "scenarios": [{"id": "gumbel_precise", "family": "gumbel", "execution": "precise"}],
    })
    assert config["scenarios"][0]["family"] == "gumbel"
    assert [s["id"] for s in effective_config({})["scenarios"]] == [
        "logistic_precise", "logistic_variable", "probit_precise", "probit_variable",
        "lapse_logistic_precise", "lapse_logistic_variable",
    ]


def test_deterministic_audit_covers_four_observers_and_lapse_sensitivity():
    from scripts.validate_stationary_observers import deterministic_checks

    results = deterministic_checks()
    assert all(record["passed"] for record in results)
    assert {record["family"] for record in results} == {"logistic", "probit", "lapse_logistic", "gumbel"}
    assert any(record["family"] == "lapse_logistic" and record.get("lapse") == 0.2 for record in results)
