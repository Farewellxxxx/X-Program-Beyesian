from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "comfort_boundary_bo_research_package"
    / "simulation"
    / "run_uncertain_input_bo_extended.py"
)


def load_simulation_module():
    spec = importlib.util.spec_from_file_location("extended_simulation_under_audit", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load simulation source: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ExtendedSimulationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim = load_simulation_module()

    def test_equal_budget_row_count_for_every_algorithm(self):
        config = self.sim.Config(
            n_participants=2,
            n_trials=4,
            candidate_count=7,
            mc_samples=5,
            seed=901,
            scenario_name="unit_equal_budget",
        )
        passengers = self.sim.make_passengers(config)
        trials = self.sim.run_scenario(config, passengers)

        counts = trials.groupby("algorithm").size().to_dict()
        self.assertEqual(set(counts.values()), {config.n_participants * config.n_trials})

    def test_repeated_run_with_same_config_is_bytewise_equivalent_as_records(self):
        config = self.sim.Config(
            n_participants=2,
            n_trials=4,
            candidate_count=7,
            mc_samples=5,
            seed=902,
            scenario_name="unit_reproducibility",
        )
        passengers = self.sim.make_passengers(config)
        first = self.sim.run_scenario(config, passengers)
        second = self.sim.run_scenario(config, passengers)

        self.assertEqual(first.to_csv(index=False), second.to_csv(index=False))

    def test_named_midpoint_is_the_half_probability_point_not_tau_point(self):
        config = self.sim.Config(tau=0.70, feedback_noise=0.06)
        passenger = self.sim.make_passengers(config)[0]
        rng = np.random.default_rng(7)
        feedback = self.sim.PassengerFeedbackModel(config, rng)
        features = {
            "realized_intensity": passenger.acceptability_midpoint,
            "peak_accel": passenger.acceptability_midpoint,
            "peak_jerk": 1.0,
        }

        result = feedback.respond(passenger, features, trial_id=1, cumulative_discomfort=0.0)

        self.assertAlmostEqual(float(result["p_accept_true"]), 0.5, places=12)
        self.assertNotAlmostEqual(float(result["p_accept_true"]), config.tau, places=6)

    def test_kernel_surrogate_can_violate_required_monotonicity(self):
        surrogate = self.sim.KernelAcceptanceSurrogate(tau=0.70).fit(
            intensities=[0.55, 0.85, 1.15, 1.45, 1.75],
            labels=[1, 0, 1, 0, 1],
        )
        grid = np.linspace(0.35, 1.95, 400)
        probabilities, _ = surrogate.predict_array(grid)

        self.assertGreater(float(np.max(np.diff(probabilities))), 1e-4)

    def test_protocol_deviation_is_currently_identical_to_safety_violation(self):
        config = self.sim.Config(
            n_participants=1,
            n_trials=5,
            candidate_count=7,
            mc_samples=5,
            seed=903,
            scenario_name="unit_protocol_alias",
        )
        trials = self.sim.run_scenario(config, self.sim.make_passengers(config))

        self.assertTrue(
            np.array_equal(
                trials["protocol_deviation"].to_numpy(),
                trials["safety_violation"].to_numpy(),
            )
        )


if __name__ == "__main__":
    unittest.main()
