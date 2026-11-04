"""Regression tests for criterion-matched synthetic boundary evaluation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py"


def load_module():
    spec = importlib.util.spec_from_file_location("boundary_metrics_under_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BoundaryMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = load_module()

    def passenger(self, **changes):
        values = dict(participant_id=1, acceptability_midpoint=1.2,
                      sensitivity=0.2, noisiness=0.2, risk_tolerance=0.0,
                      carryover_sensitivity=0.04)
        values.update(changes)
        return self.sim.Passenger(**values)

    def test_run_uses_tau_truth_instead_of_half_probability_midpoint(self):
        # Fails against the old implementation before any new API is required.
        config = self.sim.Config(n_participants=1, n_trials=2, candidate_count=5, mc_samples=3)
        trials = self.sim.run_scenario(config, self.sim.make_passengers(config))
        self.assertIn("criterion_boundary_tau", trials.columns)
        self.assertNotIn("true_boundary", trials.columns)

    def test_known_crossings_include_feedback_noise_mixture(self):
        cases = [(0.5, 1.2), (0.7, 0.980277542266378), (0.8, 0.810817970188937)]
        for tau, want in cases:
            with self.subTest(tau=tau):
                boundary = self.sim.criterion_boundary_tau(self.passenger(), tau)
                self.assertAlmostEqual(boundary, want, places=12)
                feedback = self.sim.PassengerFeedbackModel(self.sim.Config(tau=tau), np.random.default_rng(4))
                result = feedback.respond(self.passenger(), {"realized_intensity": boundary,
                    "peak_accel": boundary, "peak_jerk": 1.0}, 1, 0.0)
                self.assertAlmostEqual(result["p_accept_true"], tau, places=12)

    def test_noiseless_crossing_and_clipping_ceiling(self):
        passenger = self.passenger(noisiness=0.0)
        self.assertAlmostEqual(self.sim.criterion_boundary_tau(passenger, 0.7), 1.030540427922559, places=12)
        self.assertAlmostEqual(self.sim.criterion_boundary_tau(passenger, 0.98), 0.421635940377875, places=12)

    def test_carryover_moves_truth_by_the_exact_feedback_shift(self):
        passenger = self.passenger()
        config = self.sim.Config(include_time_effects=True)
        feedback = self.sim.PassengerFeedbackModel(config, np.random.default_rng(3))
        # trial 5 and zero accumulated discomfort -> carryover = 0.004 * 5.
        boundary = self.sim.criterion_boundary_tau(passenger, 0.7, carryover_term=0.02)
        self.assertAlmostEqual(boundary, 0.960277542266378, places=12)
        result = feedback.respond(passenger, {"realized_intensity": boundary,
            "peak_accel": boundary, "peak_jerk": 1.0}, 5, 0.0)
        self.assertAlmostEqual(result["p_accept_true"], 0.7, places=12)

    def test_impossible_or_invalid_criteria_do_not_become_finite_truth(self):
        for tau in (0.0, 0.02, 0.1, 0.9, 0.99, 1.0, float("nan")):
            with self.subTest(tau=tau), self.assertRaises(ValueError):
                self.sim.criterion_boundary_tau(self.passenger(), tau)
        for changes in ({"sensitivity": 0.0}, {"noisiness": 1.0},
                        {"noisiness": -0.1}, {"acceptability_midpoint": float("nan")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.sim.criterion_boundary_tau(self.passenger(**changes), 0.7)

    def test_trial_and_summary_errors_and_overshoot_share_dynamic_truth(self):
        config = self.sim.Config(n_participants=1, n_trials=4, include_time_effects=True,
                                candidate_count=5, mc_samples=3, seed=801)
        passenger = self.passenger()
        trials = self.sim.run_scenario(config, [passenger])
        # Independently hand-derived baseline B(0.70), then subtract actual history shift.
        truth = 0.980277542266378 - trials["carryover_term"]
        np.testing.assert_allclose(trials["criterion_boundary_tau"], truth, atol=1e-12)
        np.testing.assert_allclose(trials["criterion_boundary_tau_baseline"], 0.980277542266378, atol=1e-12)
        signed = trials["estimated_boundary_so_far"] - truth
        np.testing.assert_allclose(trials["boundary_error_so_far"], np.abs(signed))
        np.testing.assert_allclose(trials["signed_boundary_error_so_far"], signed)
        np.testing.assert_allclose(trials["overshoot"], np.maximum(0, trials["realized_intensity"] - truth))
        np.testing.assert_allclose(trials["legacy_midpoint_error_so_far"],
                                   np.abs(trials["estimated_boundary_so_far"] - 1.2))
        participant, algorithm, _, _, _ = self.sim.evaluate(trials)
        final = trials[trials["trial_id"] == 4].set_index("algorithm")
        for row in algorithm.itertuples():
            self.assertAlmostEqual(row.mean_boundary_error, final.loc[row.algorithm, "boundary_error_so_far"])
        self.assertIn("criterion_boundary_tau", participant)

    def test_audit_reports_canonical_error_with_carryover(self):
        spec = importlib.util.spec_from_file_location("audit_metrics_under_test",
            ROOT / "long_horizon_audit/scripts/run_multiseed_simulation_audit.py")
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        config = self.sim.Config(n_participants=1, n_trials=3, include_time_effects=True,
                                candidate_count=5, mc_samples=3, seed=803)
        result = audit.run_one(self.sim, config).set_index("algorithm")
        trials = self.sim.run_scenario(config, self.sim.make_passengers(config))
        final = trials[trials["trial_id"] == 3].set_index("algorithm")
        self.assertIn("mean_boundary_error", result.columns)
        np.testing.assert_allclose(result.loc[final.index, "mean_boundary_error"], final["boundary_error_so_far"])
        np.testing.assert_allclose(result.loc[final.index, "mean_legacy_midpoint_error"], final["legacy_midpoint_error_so_far"])


if __name__ == "__main__":
    unittest.main()
