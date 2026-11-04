# Monotone Bayesian surrogate implementation plan

> **For agentic workers:** Use superpowers:executing-plans task by task, with TDD and one final independent review.

**Goal:** Implement, validate and compare a monotone Bayesian binary surrogate and publish the update.

**Architecture:** New standalone grid-posterior model integrates through the existing surrogate interface; a config switch preserves corrected legacy behavior. New output directories preserve old results. A reproducible comparison program separates same-history inference from changed adaptive trajectories.

**Tech Stack:** Existing Python 3.12 / NumPy / pandas / matplotlib / pytest, no additional inference dependency.

**Spec:** `docs/superpowers/specs/2026-11-04-monotone-bayes-design.md`.

## Global constraints

- Binary likelihood and positive slope; no generator truth or participant labels supplied to inference.
- Keep corrected metric, generator, population, seeds, budgets and acquisition coefficients unchanged.
- Preserve prior outputs and raw local data; publish only code, docs and synthetic artifacts.
- Numerical approximation and model misspecification must be measured and reported.

## Review focus

- All-one/all-zero samples and separated responses must have proper finite posteriors.
- Epistemic uncertainty must not be Bernoulli observation noise.
- No-clipping boundary summaries must expose unsupported extrapolation and prior truncation.
- Grid/interpolation errors must be smaller than reported effects, or reported as limiting them.
- Legacy reproducibility and fixed-policy invariance distinguish implementation changes from randomness.

## Tasks

- [x] 1. Write failing statistical tests; implement `monotone_bayes.py` with `PriorGrid`, `MonotoneBayesianLogistic.fit`, `predict_array`, `predict`, `estimate_boundary`, `boundary_summary`, and posterior diagnostics. Verify small-grid Bayes calculation independently.
- [x] 2. Add config/CLI selection and posterior fields; tests verify default monotonicity, legacy replay, unchanged fixed policies, dynamic tau truth and deterministic records. Run full published suite.
- [x] 3. Regenerate extended/POC and five-seed+sensitivity Bayesian results. Produce same-history, paired-seed, numerical-resolution, prior-sensitivity comparisons and readable figures/report.
- [ ] 4. Independent review, final verification, documentation/manifest update, sync modified source back to original workspace, fast-forward main and push; verify remote SHA.

## Ledger

- Baseline: e071a7a; remote main confirmed through GitHub connector. Standalone repository suite 20 passed before edits.
- Working branch: feature/monotone-bayes in the established isolated publication checkout.
- Decision: deterministic posterior grid, with measured resolution and prior sensitivity, rather than adding MCMC. New score uncertainty uses posterior SD; score weights are held fixed to expose this change.

- Task 1 complete: exact posterior and edge-case tests RED→GREEN; core commit 9ab12d3.
- Task 2 complete: integration regressions RED→GREEN; published suite 31 passed before added numerical guards/comparison tests.
- Task 3 complete: 34 tests passed; extended/POC and both 16-scenario audits exit 0; comparison exit 0, all 240 doubled-grid checks passed. Same-history replay and broader prior sensitivity are reported, including worse Brier scores and 91/100 internal coverage.
- Decision: the overflow fixture must overflow all supported slopes; the initial fixture left valid mass at low slopes, so rejecting it would be incorrect. No valid-data inference changed.
