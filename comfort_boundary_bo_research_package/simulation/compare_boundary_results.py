"""Validate unchanged synthetic trajectories and report the metric correction.

The baseline root mirrors the project-relative paths of the saved original CSVs.
Run after regenerating extended, POC and corrected multiseed outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SIMULATION = Path("comfort_boundary_bo_research_package/simulation")
AUDIT = Path("long_horizon_audit/derived/simulation_audit_corrected_20261104")
KEYS = ["scenario", "algorithm", "participant_id", "trial_id"]
ORDER = ["UncertainInputBO", "NaiveContinuousBO", "RandomContinuous", "GridContinuous", "Staircase"]
LABELS = ["Uncertain-input", "Naive continuous", "Random", "Grid", "Staircase"]


def validate_unchanged_trials(before: pd.DataFrame, after: pd.DataFrame) -> dict:
    """Reject changed trials, RNG outcomes or estimates; allow metric corrections."""
    before = before.sort_values(KEYS).reset_index(drop=True)
    after = after.sort_values(KEYS).reset_index(drop=True)
    pd.testing.assert_frame_equal(before[KEYS], after[KEYS], check_exact=True)
    if before.duplicated(KEYS).any() or after.duplicated(KEYS).any():
        raise AssertionError("Duplicate trial keys")
    mapping = {"true_boundary": "acceptability_midpoint",
               "boundary_error_so_far": "legacy_midpoint_error_so_far",
               "overshoot": "legacy_midpoint_overshoot"}
    max_delta = 0.0
    for column in before:
        new_column = mapping.get(column, column)
        left, right = before[column], after[new_column]
        if pd.api.types.is_numeric_dtype(left) and not pd.api.types.is_bool_dtype(left):
            np.testing.assert_allclose(left, right, rtol=0, atol=1e-12,
                                       err_msg=f"Unexpected change: {column}")
            max_delta = max(max_delta, float(np.max(np.abs(left.to_numpy() - right.to_numpy()))))
        else:
            pd.testing.assert_series_equal(left, right, check_names=False, check_exact=True)
    return {"rows": len(before), "checked_columns": len(before.columns),
            "max_numeric_delta": max_delta, "allowed_absolute_roundoff": 1e-12}


def compare_summary(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    keys = ["scenario", "execution_noise", "algorithm"]
    merged = before.merge(after, on=keys, suffixes=("_before", "_after"), validate="one_to_one", how="outer", indicator=True)
    if not merged["_merge"].eq("both").all():
        raise AssertionError("Summary scenarios or algorithms differ")
    columns = keys + [f"{metric}_{version}" for metric in (
        "mean_boundary_error", "mean_max_overshoot", "mean_unacceptable_trials",
        "mean_cumulative_discomfort") for version in ("before", "after")]
    result = merged[columns].copy()
    result["boundary_error_change"] = result["mean_boundary_error_after"] - result["mean_boundary_error_before"]
    return result


def draw_comparison(summary: pd.DataFrame, output_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
    for ax, noise in zip(axes, ("low", "high")):
        rows = summary[summary["execution_noise"] == noise].set_index("algorithm").reindex(ORDER)
        x = np.arange(len(ORDER))
        old = rows["mean_legacy_midpoint_error_mean"]
        new = rows["mean_boundary_error_mean"]
        ax.bar(x - 0.18, old, width=0.36, color="#9aa5b1", label="Before: compared with 50% midpoint")
        ax.bar(x + 0.18, new, width=0.36, color="#2166ac", label="After: compared with 70% boundary")
        for offset, values in ((-0.18, old), (0.18, new)):
            for xpos, value in zip(x + offset, values):
                ax.text(xpos, value + .004, f"{value:.3f}", ha="center", fontsize=8)
        ax.set_title(f"{noise.capitalize()} execution noise")
        ax.set_xticks(x, LABELS, rotation=23, ha="right")
        ax.set_ylim(0, float(summary["mean_legacy_midpoint_error_mean"].max()) * 1.22)
        ax.grid(axis="y", alpha=.2)
    axes[0].set_ylabel("Mean absolute boundary error (synthetic intensity units)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .93), ncol=2, fontsize=9)
    fig.suptitle("Boundary metric correction | Same simulated decisions and responses", fontsize=14)
    fig.text(.5, .015, "Five process seeds; fixed population of 24 synthetic passengers; 12 trials per policy. Metric change, not algorithm improvement.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .85))
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/boundary_correction_20261104")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    validation = {"synthetic_only": True, "trajectories": {}, "baseline_sha256": {}}
    for label, directory in (("extended", "outputs_continuous"), ("poc", "outputs_continuous_poc")):
        relative = SIMULATION / directory
        before_path = args.baseline_root / relative / "continuous_trials.csv"
        before = pd.read_csv(before_path)
        after = pd.read_csv(ROOT / relative / "continuous_trials.csv")
        validation["trajectories"][label] = validate_unchanged_trials(before, after)
        validation["baseline_sha256"][str(relative / "continuous_trials.csv")] = hashlib.sha256(before_path.read_bytes()).hexdigest()
        comparison = compare_summary(pd.read_csv(args.baseline_root / relative / "continuous_algorithm_summary.csv"),
                                     pd.read_csv(ROOT / relative / "continuous_algorithm_summary.csv"))
        comparison.to_csv(args.output_dir / f"{label}_before_after.csv", index=False)
    summary = pd.read_csv(ROOT / AUDIT / "simulation_audit_multiseed_summary.csv")
    summary.to_csv(args.output_dir / "multiseed_boundary_comparison.csv", index=False)
    draw_comparison(summary, args.output_dir / "boundary_error_before_after.png")
    (args.output_dir / "trajectory_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    print(json.dumps(validation["trajectories"], indent=2))
    print(summary[["execution_noise", "algorithm", "mean_legacy_midpoint_error_mean", "mean_boundary_error_mean"]].round(6).to_string(index=False))


if __name__ == "__main__":
    main()
