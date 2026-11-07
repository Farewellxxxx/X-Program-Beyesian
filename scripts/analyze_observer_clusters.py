"""Report secondary equal-weight effects across the original six scenarios."""
import argparse
import hashlib
import math
from numbers import Integral
from pathlib import Path
import platform
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from comfort_boundary_bo_research_package.simulation.finite_budget import analysis, study


ORIGINAL_SCENARIOS = tuple(
    f"{family}_{execution}"
    for family in ("logistic", "probit", "lapse_logistic")
    for execution in ("precise", "variable")
)
METRICS = ("supported_success", "capped_absolute_error")
BOOTSTRAP_SEED = 202611075
BOOTSTRAP_DRAWS = 20_000
SCOPE = "secondary_original_six_scenario_clustered"
INTERVAL = "unadjusted 95% participant-cluster percentile interval"


def _metric_value(row, metric):
    if metric == "supported_success":
        return float(row["finite"] and row["supported"] and row["supported_success"])
    if not row["finite"]:
        return 3.0
    error = row["abs_error"]
    if error is None or not math.isfinite(error) or error < 0:
        raise ValueError("finite checkpoint must have a finite, nonnegative absolute error")
    return min(error, 3.0)


def cluster_paired_effect(rows, scenarios, method_a, method_b, track, estimator_a, estimator_b,
                          budget, metric, seed, draws=BOOTSTRAP_DRAWS):
    """Resample paired participant means from a complete original-six-scenario grid."""
    scenarios = tuple(sorted(scenarios))
    if scenarios != tuple(sorted(ORIGINAL_SCENARIOS)):
        raise ValueError("the original six unique scenarios are required")
    if method_a == method_b or metric not in METRICS:
        raise ValueError("distinct methods and a predeclared metric are required")
    if isinstance(draws, bool) or not isinstance(draws, Integral) or draws <= 0:
        raise ValueError("bootstrap draws must be a positive integer")

    a, b = {}, {}
    arms = {(method_a, estimator_a): a, (method_b, estimator_b): b}
    for row in rows:
        if row["track"] != track or row["budget"] != budget:
            continue
        arm = arms.get((row["method"], row["estimator"]))
        if arm is None:
            continue
        scenario, participant = row["scenario"], row["participant"]
        if scenario not in scenarios or isinstance(participant, bool) or not isinstance(participant, Integral) or participant < 0:
            raise ValueError("unexpected scenario or invalid participant identity")
        key = (scenario, participant)
        if key in arm:
            raise ValueError(f"duplicate checkpoint for {row['method']}, {scenario}, participant {participant}")
        arm[key] = _metric_value(row, metric)

    participants = sorted({participant for _, participant in a})
    expected = {(scenario, participant) for scenario in scenarios for participant in participants}
    if not expected or a.keys() != expected or b.keys() != expected:
        raise ValueError("complete and paired participant IDs in all six scenarios are required")
    cluster_means = np.array([[a[s, p] - b[s, p] for s in scenarios] for p in participants]).mean(axis=1)
    rng = np.random.default_rng(seed)
    values = np.empty(draws)
    for start in range(0, draws, 1000):
        end = min(start + 1000, draws)
        sampled = rng.integers(0, len(participants), size=(end - start, len(participants)))
        values[start:end] = cluster_means[sampled].mean(axis=1)
    lower, upper = np.quantile(values, [0.025, 0.975])
    return dict(difference=float(cluster_means.mean()), lower_95=float(lower), upper_95=float(upper),
                n_clusters=len(participants), n_condition_cases=len(expected), confidence=0.95,
                bootstrap_draws=int(draws), bootstrap_seed=seed, role="secondary",
                evidence_scope=SCOPE, interval_scope=INTERVAL, adjustment_scope="none")


def _sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def analyze_clusters(input_dir, output_dir):
    root = Path(input_dir)
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError(out)
    config = study.effective_config(root / "effective_config.json")
    original_config_path = ROOT / "configs" / "finite_budget_heldout.json"
    original = study.effective_config(original_config_path)
    if (config["study"]["split"] != "heldout"
            or {s["id"]: s for s in config["scenarios"]} != {s["id"]: s for s in original["scenarios"]}
            or not {30, 60}.issubset(config["study"]["checkpoints"])):
        raise ValueError("a heldout run with the original six scenario definitions and N30/N60 is required")
    verified = study.validate_run(root)
    staircase = [method["id"] for method in config["methods"] if method["sampler"] == "staircase"]
    if len(staircase) != 1 or not any(method["id"] == "new_precision" for method in config["methods"]):
        raise ValueError("one staircase and the new_precision method are required")

    rows = study.read_jsonl(root / "checkpoints.jsonl")
    effects = []
    for budget in (30, 60):
        for track, track_label, estimator_b in (("pipeline", "A", "firth"), ("common", "B", "new_precision")):
            for metric in METRICS:
                seed = analysis._bootstrap_seed(BOOTSTRAP_SEED, [track, metric, budget])
                effect = cluster_paired_effect(rows, ORIGINAL_SCENARIOS, "new_precision", staircase[0], track,
                                               "new_precision", estimator_b, budget, metric, seed)
                effects.append(dict(
                    **effect, budget=budget, study_budget_role="primary" if budget == 30 else "secondary",
                    track=track, track_label=track_label, metric=metric, method_a="new_precision",
                    method_b=staircase[0], estimator_a="new_precision", estimator_b=estimator_b,
                    direction="A minus B (method_a minus method_b)",
                ))

    artifacts = {p.name: _sha256(p) for p in sorted(root.iterdir())
                 if p.is_file() and p.suffix in (".json", ".jsonl")}
    source_paths = [Path(__file__), Path(study.__file__), Path(analysis.__file__), original_config_path]
    out.mkdir(parents=True)
    effects_path = out / "clustered_effects.jsonl"
    with effects_path.open("w", encoding="utf-8", newline="\n") as stream:
        for effect in effects:
            stream.write(study.canonical(effect) + "\n")
    manifest = dict(
        version=1, input_dir=str(root.resolve()), input_config_sha256=verified["config_sha256"],
        input_source_hashes=verified["source_hashes"], input_artifact_sha256=artifacts,
        analysis_source_sha256={p.resolve().relative_to(ROOT).as_posix(): _sha256(p) for p in source_paths},
        output_artifact_sha256={effects_path.name: _sha256(effects_path)},
        scenarios=list(ORIGINAL_SCENARIOS), n_clusters=config["participants"],
        n_condition_cases=config["participants"] * len(ORIGINAL_SCENARIOS),
        cluster_unit="base participant with all six paired scenario differences",
        scenario_weights="equal weights within each base participant",
        outcome_verification="complete run grids and outcome classifications validated from raw prefixes",
        capped_error="min(abs_error, 3) for finite estimates; 3 for nonfinite estimates",
        bootstrap_seed=BOOTSTRAP_SEED, bootstrap_draws=BOOTSTRAP_DRAWS,
        seed_substream_key=["track", "metric", "budget"], contrast_rows=len(effects),
        role="secondary", evidence_scope=SCOPE, interval_scope=INTERVAL, adjustment_scope="none",
        python=platform.python_version(), numpy=np.__version__,
    )
    study.write_json(out / "cluster_manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = analyze_clusters(args.input, args.output)
    print(f"{manifest['contrast_rows']} secondary contrasts from {manifest['n_clusters']} participant clusters")


if __name__ == "__main__":
    main()
