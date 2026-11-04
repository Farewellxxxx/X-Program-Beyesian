from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

SOURCE = Path(__file__).resolve().parents[2] / "comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py"


class BayesianIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location("bayesian_sim_integration",SOURCE)
        cls.sim=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=cls.sim
        spec.loader.exec_module(cls.sim)

    def test_default_surrogate_is_monotone_under_contradictory_labels(self):
        history=[{"realized_intensity":x,"acceptable":y} for x,y in zip([.5,.8,1.1,1.4,1.7],[1,0,1,0,1])]
        model=self.sim.fit_surrogate_from_history(self.sim.Config(),history)
        self.assertTrue(hasattr(model,"boundary_summary"),"Default must expose a Bayesian boundary posterior")
        p,_=model.predict_array(np.linspace(.2,2.3,200))
        self.assertLessEqual(np.max(np.diff(p)),1e-12)

    def test_legacy_mode_replays_committed_corrected_records(self):
        config=self.sim.Config(n_participants=1,n_trials=4,seed=self.sim.BASE_SEED+1,
            scenario_name="continuous_low_noise",surrogate_kind="legacy_kernel")
        actual=self.sim.run_scenario(config,self.sim.make_passengers(config))
        old=pd.read_csv(SOURCE.parent/"outputs_continuous/continuous_trials.csv")
        old=old[(old.scenario==config.scenario_name)&(old.participant_id==1)&(old.trial_id<=4)]
        keys=["algorithm","trial_id"]
        pd.testing.assert_frame_equal(old.sort_values(keys).reset_index(drop=True),
            actual[old.columns].sort_values(keys).reset_index(drop=True),check_exact=False,rtol=0,atol=1e-12)

    def test_fixed_policy_paths_unchanged_and_bayesian_interval_fields_aggregate(self):
        config=self.sim.Config(n_participants=1,n_trials=5,candidate_count=5,mc_samples=3,seed=901)
        passengers=self.sim.make_passengers(config)
        new=self.sim.run_scenario(config,passengers)
        old=self.sim.run_scenario(replace(config,surrogate_kind="legacy_kernel"),passengers)
        fixed=["RandomContinuous","GridContinuous","Staircase"]
        cols=["algorithm","trial_id","target_command_x","realized_intensity","acceptable","discomfort"]
        pd.testing.assert_frame_equal(new.loc[new.algorithm.isin(fixed),cols].reset_index(drop=True),
            old.loc[old.algorithm.isin(fixed),cols].reset_index(drop=True),check_exact=True)
        self.assertTrue(new.boundary_ci95_width.gt(0).all())
        self.assertTrue(old.boundary_ci95_lower.isna().all())
        expected=(new.boundary_ci95_lower<=new.criterion_boundary_tau)&(new.criterion_boundary_tau<=new.boundary_ci95_upper)
        np.testing.assert_array_equal(new.boundary_ci95_covers_truth,expected.astype(float))
        np.testing.assert_allclose(new.predictive_brier_score,
            (new.predicted_acceptability_before_trial-new.acceptable.astype(int))**2)
        participant,algorithm,_,_,_=self.sim.evaluate(new)
        self.assertIn("mean_boundary_ci95_width",algorithm)
        self.assertIn("mean_predictive_brier_score",algorithm)
        self.assertEqual(len(participant),5)


if __name__=="__main__":
    unittest.main()
