# Execution misspecification and budget implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline with TDD and one final independent whole-branch review.

**Goal:** Test execution-structure misspecification and calibration-budget robustness, explain which prior conclusions survive, and publish.
**Architecture:** Separate distortion/diagnostic module; optional prepared-execution injection into existing runner; dedicated matched audit and strict comparison; archived outputs unchanged.
**Tech Stack:** Existing Python/NumPy/pandas/matplotlib/pytest; no new dependencies.
**Spec:** `docs/superpowers/specs/2026-11-04-execution-misspecification-budget-design.md`.

## Global constraints and review focus

- Baseline e06f0e2; reuse isolated publication checkout on feature/execution-misspecification-budget, then sync original directory.
- Full oracle must model structural distortion; fitted beliefs see only calibration observations. Tests inspect both interfaces and actual behavior.
- Budget arms use nested observation prefixes, unchanged feedback/acquisition and paired process RNGs. Test prefixes and fixed-policy trajectory equality.
- Preserve exact default/historical numerical behavior; run existing suite and original population/stress replay.
- All 420 main scenarios must exist; missing whole batches, duplicate rows, mismatched metadata and nonfinite metrics must fail validation.
- Statistical units are five population batches. Command-level diagnostics are separate synthetic draws, not extra passenger or independent population evidence.

## Tasks

- [ ] 1. Add `simulation/execution_misspecification.py`: frozen Distortion; distorted generator with nominal/scalar/vector methods; nested calibration commands; observation-only `prepare_stress_execution`; independent distribution diagnostics. Add tests in `long_horizon_audit/tests/test_execution_misspecification.py`, watch RED, implement, pass full suite. Extend only `run_scenario(..., prepared=None)` and audit `execute(..., prepared=None)` interfaces. Commit.
- [ ] 2. Add `long_horizon_audit/scripts/run_execution_robustness_audit.py` defining seven profiles, six arms and explicit paired seeds/configuration manifests; add strict comparison in `compare_execution_robustness.py`. Tests in `test_execution_robustness_audit.py` cover full grid, metadata tampering, paired statistics, budget prefixes and leaf streams. RED to GREEN, full suite, commit.
- [ ] 3. Run 420 main scenarios plus prior population/stress replay, independent diagnostics and comparisons. Produce synthetic CSV/JSON, figures and Chinese result/verification reports. Explain old-to-new schedule effects separately from structural and budget effects; discuss cost and adverse outcomes. Visually inspect plots.
- [ ] 4. One independent read-only review; fix substantiated Important/Critical findings once with regression tests. Final suite/integrity checks, workspace sync, fast-forward main and push; verify remote SHA. Refresh publication manifest.

## Interfaces

- Task 1 provides `Distortion(gain=0, quadratic=0, correlation=0)`, `make_truth(settings,parameters,distortion)`, `nested_commands(settings,n)`, `prepare_stress_execution(config,distortion,observations=None)` returning existing PreparedExecution, and `distribution_diagnostics(prepared,seed,n_samples=4096)`.
- Task 2 provides `build_scenarios()` with profile/arm/batch/repeat/config/distortion identity, run outputs and manifest validation; reuses existing `summarize_clusters` t intervals.
- Task 3 consumes complete output manifests and reports paired contrasts without changing experimental coefficients after seeing outcomes.

## Ledger

- Setup: clean e06f0e2 main; baseline full suite 50 passed. Existing .publish clone isolates changes from original research directory; use a feature branch here instead of creating another nested worktree. No AGENTS.md found.
- Ruling: proceed within the user's explicit implementation/run/publish authorization; routine experiment choices are documented, no extra approval round. Preserve prior native inline workflow and one final independent reviewer.
- Pre-flight: prepared execution uses the existing runner interface and metadata; new audit supplies full truth-profile fingerprints instead of pretending the old generator fingerprint includes distortion. Existing audit compatibility must remain unchanged.
- Ruling: keep current defaults/results frozen, expose new stress cases through a dedicated audit entry point. Calibration schedule changes are measured separately against prior 40-observation results.
