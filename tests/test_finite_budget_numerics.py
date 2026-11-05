import json
import numpy as np
from comfort_boundary_bo_research_package.simulation.finite_budget.numerical_diagnostics import compare_public_histories

def test_public_history_diagnostics_emit_reproducible_decisions_and_loss():
    report=compare_public_histories(coarse_grid=(9,5),fine_grid=(13,7),coarse_nodes=1,fine_nodes=3,
                                   histories={'mixed':((.3,1),(2.1,0))},targets=(0.,1.5,3.))
    assert report['uses_truth'] is False
    assert len(report['comparisons'])==6  # two beliefs, three comparisons
    for row in report['comparisons']:
        assert set(row['acquisitions'])=={'variance','precision'}
        assert row['precision_boundary_difference']>=0
        for a in row['acquisitions'].values():
            assert a['fine_loss_at_coarse_choice']>=-1e-12
            assert a['fine_maximum']>=-1e-12
            assert a['coarse_command'] in (0.,1.5,3.)
    json.dumps(report,allow_nan=False)
