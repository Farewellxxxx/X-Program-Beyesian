from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


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


def run_one(sim, config) -> pd.DataFrame:
    passengers = sim.make_passengers(config)
    trials = sim.run_scenario(config, passengers)
    participant, _, _, safety, _ = sim.evaluate(trials)
    output = participant.groupby("algorithm", as_index=False).agg(
        mean_boundary_error=("boundary_error_so_far", "mean"),
        mean_legacy_midpoint_error=("legacy_midpoint_error_so_far", "mean"),
        mean_signed_boundary_error=("signed_boundary_error_so_far", "mean"),
        mean_unacceptable_trials=("unacceptable_trials", "mean"),
        mean_cumulative_discomfort=("cumulative_discomfort", "mean"),
        mean_protocol_deviations=("protocol_deviations", "mean"),
        mean_predictive_brier_score=("mean_predictive_brier_score", "mean"),
        mean_boundary_ci95_width=("boundary_ci95_width", "mean"),
        boundary_ci95_coverage=("boundary_ci95_covers_truth", "mean"),
        max_posterior_grid_edge_mass=("posterior_grid_edge_mass", "max"),
    )
    safety_summary = safety[
        ["algorithm", "protocol_deviation_rate", "safety_violation_trials"]
    ].copy()
    output = output.merge(safety_summary, on="algorithm", how="left")
    output.insert(0, "seed", config.seed)
    output.insert(1, "scenario", config.scenario_name)
    output.insert(2, "execution_noise", config.execution_noise)
    output.insert(3, "tau", config.tau)
    output.insert(4, "feedback_noise", config.feedback_noise)
    output.insert(5, "calibration_bias", config.calibration_bias)
    output.insert(6, "include_time_effects", config.include_time_effects)
    output["n_participants"] = config.n_participants
    output["n_trials_per_algorithm_participant"] = config.n_trials
    output["surrogate_kind"] = config.surrogate_kind
    return output


def t_interval_95(series: pd.Series) -> tuple[float, float]:
    values = series.dropna().to_numpy(dtype=float)
    if len(values) < 2:
        return math.nan, math.nan
    critical = {
        2: 12.706,
        3: 4.303,
        4: 3.182,
        5: 2.776,
        6: 2.571,
        7: 2.447,
        8: 2.365,
        9: 2.306,
        10: 2.262,
    }.get(len(values), 1.96)
    half_width = critical * float(np.std(values, ddof=1)) / math.sqrt(len(values))
    mean = float(np.mean(values))
    return mean - half_width, mean + half_width


def summarize_multiseed(per_run: pd.DataFrame) -> pd.DataFrame:
    base = per_run[per_run["scenario"].str.startswith("multiseed_")].copy()
    rows: list[dict[str, float | int | str]] = []
    metrics = [
        "mean_legacy_midpoint_error",
        "mean_boundary_error",
        "mean_unacceptable_trials",
        "mean_cumulative_discomfort",
        "protocol_deviation_rate",
        "mean_predictive_brier_score",
        "mean_boundary_ci95_width",
        "boundary_ci95_coverage",
    ]
    for (noise, algorithm), group in base.groupby(["execution_noise", "algorithm"]):
        row: dict[str, float | int | str] = {
            "execution_noise": str(noise),
            "algorithm": str(algorithm),
            "n_seeds": int(group["seed"].nunique()),
            "population_repeated_across_seeds": "yes",
            "surrogate_kind": str(group["surrogate_kind"].iloc[0]),
        }
        for metric in metrics:
            low, high = t_interval_95(group[metric])
            row[f"{metric}_mean"] = float(group[metric].mean())
            row[f"{metric}_ci95_low"] = low
            row[f"{metric}_ci95_high"] = high
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independent multi-seed and sensitivity audit of the existing extended simulation."
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--surrogate", choices=["monotone_bayes", "legacy_kernel"], default="monotone_bayes")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sim = load_simulation_module()
    configs = []
    for repeat in range(args.seeds):
        for noise in ("low", "high"):
            seed = 20268000 + repeat * 10 + (0 if noise == "low" else 1)
            configs.append(
                sim.Config(
                    surrogate_kind=args.surrogate,
                    execution_noise=noise,
                    scenario_name=f"multiseed_{noise}_{repeat + 1}",
                    seed=seed,
                )
            )

    sensitivity_specs = [
        {"tau": 0.50, "scenario_name": "sensitivity_tau_050"},
        {"tau": 0.80, "scenario_name": "sensitivity_tau_080"},
        {"feedback_noise": 0.02, "scenario_name": "sensitivity_feedback_002"},
        {"feedback_noise": 0.14, "scenario_name": "sensitivity_feedback_014"},
        {"calibration_bias": 0.15, "scenario_name": "sensitivity_known_bias_015"},
        {"include_time_effects": True, "scenario_name": "sensitivity_time_effects_on"},
    ]
    for index, overrides in enumerate(sensitivity_specs):
        configs.append(sim.Config(seed=20269000 + index, surrogate_kind=args.surrogate, **overrides))

    rows = []
    for index, config in enumerate(configs, start=1):
        print(f"[{index}/{len(configs)}] {config.scenario_name}", flush=True)
        rows.append(run_one(sim, config))

    per_run = pd.concat(rows, ignore_index=True)
    summary = summarize_multiseed(per_run)
    per_run.to_csv(
        args.output_dir / "simulation_audit_per_run_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        args.output_dir / "simulation_audit_multiseed_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(
        f"WROTE {len(per_run)} per-run rows and {len(summary)} multi-seed summary rows",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
