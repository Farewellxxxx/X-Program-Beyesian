# Criterion boundary and metric correction implementation plan

> **For agentic workers:** Use superpowers:executing-plans to execute this authorized repair task by task.

**Goal:** Correct the active continuous simulator's boundary truth, error and overshoot; regenerate and compare results; publish reproducible code and synthetic artifacts to the user's GitHub repository.

**Architecture:** Keep policies, passenger population and random draws unchanged. Rename the latent 50% midpoint; derive the criterion boundary from the exact noisy response model, including trial-specific carryover. Share that definition between production metrics and the audit runner. Preserve the prior outputs locally and export a before/after comparison.

**Tech Stack:** Existing Python, NumPy, pandas, matplotlib and pytest/unittest; Git.

**Spec:** User request of 2026-11-04; `long_horizon_audit/08_prioritized_issue_ledger.md` P1-07 and `paper_draft_internal/sections/05_synthetic.tex`.

## Global constraints

- Work only on active extended/POC simulation and its audit integration; legacy `new_idea` is historical.
- Do not change acquisition, RNG, feedback generation, surrogate, execution-model assumptions or physical safety thresholds.
- Do not publish raw participant files, archives, third-party PDFs, credentials or local backups.
- Keep existing historical audit evidence and manuscript artifacts; document supersession explicitly.
- Full-suite environment failures must be reported separately, never silently hidden.

## Review focus

- Noisy Bernoulli mixture rather than noiseless logistic inversion.
- Carryover shifts the trial-specific truth before that trial's discomfort is added.
- Impossible criteria must not silently produce a finite clipped boundary.
- Error and overshoot must use the same target as the estimate.
- Generated tables, plots and audit columns must not retain misleading midpoint labels.

## Task 1: Definition and metrics

- [x] Add failing tests for known 50/70/80% crossings, noisy feedback inversion, carryover, invalid/unattainable criteria and trial aggregation.
- [x] Rename `Passenger.true_boundary` to `acceptability_midpoint`; add `criterion_boundary_tau(passenger, tau, carryover_term=0.0)`.
- [x] Record baseline and trial-specific criterion boundaries; correct signed/absolute error and overshoot, retain explicitly named legacy midpoint metrics for comparison.
- [x] Update summary schema, plots and audit runner to consume canonical truth.
- [x] Run relevant tests, then the full project suite.

## Task 2: Reproduce and compare

- [x] Run extended, POC and five-seed plus sensitivity audit with original configurations.
- [x] Check equality of target commands, realized motion, acceptance, ratings and estimates against archived runs.
- [x] Produce CSV and PNG before/after comparisons and a Chinese results report, distinguishing metric correction from algorithm improvement.
- [x] Inspect generated figures and record commands, environment and limitations.

## Task 3: Review and publish

- [x] Obtain one independent review of code, tests and scientific interpretation; address substantive findings.
- [x] Prepare repository README, pinned environment and explicit publication allowlist, with synthetic-only outputs.
- [x] Verify the publication copy, commit, push without force, and confirm remote commit/file state.

## Progress

- Baseline: original suite 9 passed / 3 failed: two sandbox temporary-directory permission errors and one pre-existing legacy presentation-runtime discovery failure.
- GitHub connector transport unavailable; authorized Git CLI fallback reached an empty remote repository.
- Existing source and output files backed up with SHA256 under `tmp/boundary_fix_20261104/`.
- Scope ruling: preserve acquisition and response generation to isolate metric effects. Broader model repairs remain separate work.
- Task 1 complete: definition, noisy/history-aware truth, error/overshoot, schema and audit repaired. New tests observed RED then GREEN.
- Task 2 complete: 3,780 archived trial rows validated, max delta 0.0; 30 extended/POC artifacts regenerated, 80 audit rows, 10 multiseed rows and comparison outputs created.
- Final review: one independent reviewer; no actionable findings. Broader model validity, empirical superiority and old PPT runtime remain documented limitations; publication/remote checks handled by main executor.
- Verification: original workspace 20 passed / 1 pre-existing presentation-runtime failure; standalone publication 20 passed. Data temporary-directory permissions resolved through environment configuration.

- Publication complete: initial commit `5b489baff6190b79294feec8a9550a114c6e226d` pushed to `Farewellxxxx/X-Program-Beyesian` main; remote SHA matched, worktree clean, 65 manifest entries verified with 0 mismatches.
