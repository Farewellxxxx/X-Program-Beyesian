# Stationary Observer Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate existing stationary observers independently, add one sourced asymmetric observer, and complete a fixed fresh replication with cluster-correct secondary summaries.
**Architecture:** Minimal observer extension in the existing runner; separate audit and cluster-analysis scripts. Existing sampling, inference and failure logic remain byte-identical. The coordinator freezes the protocol before outcomes, Sol implements and executes, root reviews and publishes.
**Tech Stack:** Python3.12, NumPy1.26.4, SciPy1.13.1, pytest7.4.4; existing finite_budget runner.
**Spec:** docs/superpowers/specs/2026-11-07-observer-validation-design.md

## Global Constraints
- N30 primary, N60 secondary, tau=.70, delta=.15, success_target=.80, calibration_n=90; preserve failure denominators.
- Never edit frozen samplers, acquisition, priors, readouts or execution; no dynamic state.
- Main n256/seed202611071, exploratory n64/seed202611072; no outcome-driven extension.
- Six-scenario overall summaries must cluster by base participant, equal scenario weights; new family/sensitivity separate exploratory scope.
- One Sol implementation agent at a time; no worker subagents, no push/merge. Root performs independent final review.

## Review Focus
- Gumbel orientation and tails must match gumbel_l.sf at extreme finite inputs without overflow.
- Existing three family outputs must remain identical at representative points and historical deterministic streams.
- Unsupported/nonfinite outputs remain supported-success failures; capped error=min(abs_error,3) for finite output (including unsupported), and3 for nonfinite output.
- Missing, duplicated or permuted scenario/participant records cannot silently change cluster weights.
- New exploratory scenarios cannot inherit confirmatory six-scenario adjustment labels.

### Task 1: Implement observer validation and cluster analysis
**Files:** Modify simulation/decoupled_calibration/passenger.py, simulation/finite_budget/population.py, simulation/finite_budget/study.py under comfort_boundary_bo_research_package; create scripts/validate_stationary_observers.py and scripts/analyze_observer_clusters.py; create tests/test_stationary_observer_validation.py and tests/test_observer_cluster_analysis.py. Config generation helper permitted if it simply applies this protocol.
**Interfaces:** Existing passenger_from_latent(B,W,family,tau=.70,lapse=.10) additionally accepts gumbel; Passenger.probability/respond unchanged interface. Audit CLI --output FILE writes deterministic/MonteCarlo results and provenance and exits nonzero on any failed check. Cluster CLI --input RUN --output DIR reads verified complete original-six-scenario run, writes clustered_effects.jsonl and manifest; pure helper cluster_paired_effect(rows, scenarios, method_a, method_b, track, estimator_a, estimator_b, budget, metric, seed, draws=20000) returns cluster summary and validates complete pairing. No current analysis.py changes needed.
- [ ] Write failing tests for source-distribution agreement, tails/roots/derivatives, regression of old families, invalid widths/tau; tests for exact cluster bootstrap against independently built complete matrix, order invariance, rejection of missing/duplicate/unpaired records and denominator failure treatment.
- [ ] Run targeted tests and confirm relevant failures before implementation.
- [ ] Implement minimal Gumbel extension with stable exp tail handling and analytic derivative; independent audit uses scipy.stats distributions and fixed MonteCarlo design from spec.
- [ ] Implement cluster helper/CLI with20000 resamples of participant means,95% intervals, precise secondary labels, provenance hashes and N30/N60 A/B success/capped-error contrasts.
- [ ] Run targeted tests then full pytest with local TEMP/TMP and a new explicit --basetemp; report commands/counts. Run observer audit and inspect artifact.
- [ ] Provide changed-file list and concise report in this plan workspace. Coordinator performs scoped review and root independent final review. Do not commit/push unless root asks.

### Task 2: Freeze, execute and report (coordinator + same Sol executor)
**Files:** configs/observer_validation_main.json, configs/observer_validation_exploratory.json, results/observer_validation_20261107/**, comfort_boundary_bo_research_package/docs/observer_validation_results_zh.md and observer_validation_reproducibility.md.
**Interfaces:** Existing finite_budget freeze/run/analyze commands; existing verify_finite_budget_artifacts.py independent verifier; task1 observer/cluster scripts.
- [ ] Create exact configs from selected heldout config, enforce source-byte equality of all protected scientific modules, and freeze against existing selection/numerical decision; save protocol/config/source fingerprints before any run.
- [ ] Execute both fixed batches with6workers and project-owned TEMP/TMP; no outcome-driven reruns/extensions.
- [ ] Run existing analysis and independent artifact verification, new cluster analysis, existing parallel numerical readout verifier for both batches and a bounded deterministic trajectory replay. Save every result and provenance artifact.
- [ ] Interpret predeclared comparisons and prepare Chinese report plus complete reproduction commands, including derivative and MonteCarlo evidence, sample/runtime counts, uncertainty and human-study limits. Link root-owned sources/human-pilot document.
- [ ] Verify manifests and full scientific-source invariants; hand complete review package to root. Mark completion only with observed verification evidence.
