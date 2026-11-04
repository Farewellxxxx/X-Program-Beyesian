"""
Quick proof-of-concept runner for the continuous-target uncertain-input
BO-inspired simulation.

This POC uses the same implementation as the extended script with fewer
participants and one execution-noise condition. It is meant for quick smoke
tests, not as final evidence.

Run:
    python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_poc.py
"""

from __future__ import annotations

from pathlib import Path

from run_uncertain_input_bo_extended import BASE_SEED, Config, run_configurations


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs_continuous_poc"


def main() -> None:
    scenario = Config(
        n_participants=18,
        n_trials=10,
        execution_noise="low",
        scenario_name="continuous_poc_low_noise",
        seed=BASE_SEED + 501,
        candidate_count=35,
        mc_samples=40,
    )
    _, _, algorithm = run_configurations([scenario], OUTPUT_DIR)

    print("Continuous-target POC simulation complete.")
    print(f"Output directory: {OUTPUT_DIR}")
    display_cols = [
        "scenario",
        "algorithm",
        "mean_boundary_error",
        "mean_unacceptable_trials",
        "mean_cumulative_discomfort",
        "mean_max_overshoot",
        "mean_abs_realization_error",
    ]
    print(algorithm[display_cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
