import numpy as np
import pytest


SCENARIOS = (
    "logistic_precise", "logistic_variable", "probit_precise", "probit_variable",
    "lapse_logistic_precise", "lapse_logistic_variable",
)


@pytest.fixture
def cohort():
    # Columns are scenarios and rows are participants. The first and last
    # participants show why resampling condition cases gives a different interval.
    a = np.array([[1, 1, 1, 1, 1, 1], [1, 0, 1, 0, 1, 0],
                  [1, 1, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]])
    b = np.array([[0, 0, 0, 0, 0, 0], [0, 1, 0, 1, 0, 1],
                  [1, 0, 0, 1, 0, 0], [1, 1, 1, 1, 1, 1]])
    rows = []
    for method, estimator, matrix in (("bo", "new_precision", a), ("stairs", "firth", b)):
        for participant, outcomes in enumerate(matrix):
            for scenario, success in zip(SCENARIOS, outcomes):
                rows.append(dict(scenario=scenario, participant=participant, method=method,
                                 estimator=estimator, track="pipeline", budget=30,
                                 finite=True, supported=True, supported_success=bool(success),
                                 abs_error=0.1 if success else 0.3))
    return rows, a, b


def cluster(rows, scenarios=SCENARIOS, metric="supported_success"):
    from scripts.analyze_observer_clusters import cluster_paired_effect

    return cluster_paired_effect(rows, scenarios, "bo", "stairs", "pipeline",
                                 "new_precision", "firth", 30, metric, 1234)


def test_cluster_bootstrap_matches_independent_complete_matrix(cohort):
    rows, a, b = cohort
    result = cluster(rows)
    picks = np.random.default_rng(1234).integers(0, 4, size=(20000, 4))
    samples = (a[picks] - b[picks]).mean(axis=(1, 2))
    assert result["difference"] == pytest.approx((a - b).mean())
    assert result["lower_95"] == pytest.approx(np.quantile(samples, 0.025))
    assert result["upper_95"] == pytest.approx(np.quantile(samples, 0.975))
    assert result["n_clusters"] == 4
    assert result["n_condition_cases"] == 24
    assert result["bootstrap_draws"] == 20000
    assert "lower_bonferroni" not in result


def test_cluster_result_is_invariant_to_rows_and_scenarios_order(cohort):
    rows, _, _ = cohort
    order = np.random.default_rng(22).permutation(len(rows))
    assert cluster(rows) == cluster([rows[i] for i in order], SCENARIOS[::-1])


@pytest.mark.parametrize("damage", ["missing", "duplicate", "unpaired", "missing_scenario", "extra_scenario"])
def test_cluster_rejects_incomplete_or_mismatched_grid(cohort, damage):
    rows, _, _ = cohort
    if damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows.append(rows[-1].copy())
    elif damage == "unpaired":
        rows[-1]["participant"] = 99
    elif damage == "missing_scenario":
        rows = [r for r in rows if r["scenario"] != SCENARIOS[0]]
    else:
        rows.append(dict(rows[-1], scenario="gumbel_precise"))
    with pytest.raises(ValueError):
        cluster(rows)


@pytest.mark.parametrize("scenarios", [SCENARIOS[:-1], SCENARIOS[:-1] + (SCENARIOS[0],)])
def test_cluster_rejects_non_original_scenario_list(cohort, scenarios):
    with pytest.raises(ValueError):
        cluster(cohort[0], scenarios)


def test_cluster_keeps_unsupported_and_nonfinite_rows_in_both_denominators():
    rows = []
    for scenario in SCENARIOS:
        for participant, supported, finite, abs_error in [(0, False, True, 0.1), (1, False, False, None)]:
            rows.append(dict(scenario=scenario, participant=participant, method="bo", estimator="new_precision",
                             track="pipeline", budget=30, finite=finite, supported=supported,
                             supported_success=False, abs_error=abs_error))
            rows.append(dict(scenario=scenario, participant=participant, method="stairs", estimator="firth",
                             track="pipeline", budget=30, finite=True, supported=True,
                             supported_success=True, abs_error=0.0))
    successes = cluster(rows)
    errors = cluster(rows, metric="capped_absolute_error")
    assert successes["difference"] == -1
    assert errors["difference"] == pytest.approx(1.55)
    assert successes["n_clusters"] == errors["n_clusters"] == 2
