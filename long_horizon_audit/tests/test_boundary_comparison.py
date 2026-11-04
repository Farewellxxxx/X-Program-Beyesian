from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import pandas as pd


class BoundaryComparisonTests(unittest.TestCase):
    def load_comparison(self):
        path = Path(__file__).resolve().parents[2] / "comfort_boundary_bo_research_package/simulation/compare_boundary_results.py"
        self.assertTrue(path.exists(), "Reproducible comparison tool must exist")
        spec = importlib.util.spec_from_file_location("boundary_comparison", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def pair(self):
        before = pd.DataFrame({"scenario": ["s"], "algorithm": ["a"], "participant_id": [1],
            "trial_id": [1], "target_command_x": [0.7], "acceptable": [True],
            "true_boundary": [1.2], "estimated_boundary_so_far": [0.95],
            "boundary_error_so_far": [0.25], "overshoot": [0.0]})
        after = before.drop(columns=["true_boundary"]).assign(acceptability_midpoint=1.2,
            boundary_error_so_far=0.03, overshoot=0.1,
            legacy_midpoint_error_so_far=0.25, legacy_midpoint_overshoot=0.0)
        return before, after

    def test_accepts_only_metric_changes(self):
        module = self.load_comparison()
        result = module.validate_unchanged_trials(*self.pair())
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["max_numeric_delta"], 0.0)

    def test_rejects_changes_to_commands_feedback_or_row_identity(self):
        module = self.load_comparison()
        for column, value in [("target_command_x", 0.8), ("acceptable", False), ("trial_id", 2)]:
            before, after = self.pair()
            after.loc[0, column] = value
            with self.subTest(column=column), self.assertRaises(AssertionError):
                module.validate_unchanged_trials(before, after)


if __name__ == "__main__":
    unittest.main()
