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
import argparse

from run_uncertain_input_bo_extended import BASE_SEED, Config, run_configurations


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs_bayesian_poc"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surrogate", choices=["monotone_bayes", "legacy_kernel"], default="monotone_bayes")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or (OUTPUT_DIR if args.surrogate == "monotone_bayes" else OUTPUT_DIR.parent / "outputs_continuous_poc")
    scenario = Config(
        surrogate_kind=args.surrogate,
        n_participants=18,
        n_trials=10,
        execution_noise="low",
        scenario_name="continuous_poc_low_noise",
        seed=BASE_SEED + 501,
        candidate_count=35,
        mc_samples=40,
    )
    _, _, algorithm = run_configurations([scenario], output_dir)

    print("Continuous-target POC simulation complete.")
    print(f"Output directory: {output_dir}")
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
