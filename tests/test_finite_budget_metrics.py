import math
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import PriorSpec, StudySpec, Readout
from comfort_boundary_bo_research_package.simulation.finite_budget.metrics import assess, wilson_interval, fixed_budget_summary
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation

H = (Observation(1, .3, .3, 1), Observation(2, 2.1, 2.1, 0))

def test_wilson_known_examples_and_invalid_counts():
    assert wilson_interval(0, 10) == pytest.approx((0, .2775327999))
    assert wilson_interval(8, 10) == pytest.approx((.4901624715, .9433178485))
    assert all(math.isnan(x) for x in wilson_interval(0, 0))
    for pair in [(3,2), (-1,2), (1,1.5)]:
        with pytest.raises(ValueError): wilson_interval(*pair)

def test_inclusive_delta_support_and_domain_reporting():
    r = assess(Readout(1.15), H, 1., .15)
    assert r['accurate'] and r['supported_success']
    assert not assess(Readout(2.5), H, 2.5, .15)['supported_success']
    outside = assess(Readout(-.2), H, -.2, .15)
    assert outside['accurate'] and outside['out_of_domain'] and not outside['supported']
    one_label = (Observation(1,0.,0.,1), Observation(2,3.,3.,1))
    assert not assess(Readout(1.), one_label, 1., .15)['supported']
    assert not assess(Readout(1.,status='failed'), H, 1., .15)['finite']

def test_missing_outputs_remain_in_denominator():
    rows = [dict(assess(Readout(1.), H, 1., .15), budget=30),
            dict(assess(Readout(None,status='failed'), H, 1., .15), budget=30)]
    s = fixed_budget_summary(rows,30,.15)
    assert s['n'] == 2 and s['supported_success_rate'] == .5
    assert s['failure_count'] == 1 and s['finite_mae'] == 0
    with pytest.raises(ValueError): fixed_budget_summary(rows,30,.15,n=3)
    missing = fixed_budget_summary([dict(rows[1]),dict(rows[1])],30,.15)
    assert missing['supported_success_rate'] == 0 and math.isnan(missing['finite_mae'])

def test_contracts_validate_enums_and_configuration():
    assert StudySpec().primary_budget == 30
    assert PriorSpec().center == 1.5
    with pytest.raises(ValueError): PriorSpec(kind='unknown')
    with pytest.raises(ValueError): StudySpec(split='legacy_suffix')
    with pytest.raises(ValueError): StudySpec(checkpoints=(10,20))
    with pytest.raises(TypeError): StudySpec(event='suffix')
