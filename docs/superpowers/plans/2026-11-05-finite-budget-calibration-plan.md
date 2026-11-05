# Finite-Budget Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax. User approved implementation on 2026-11-05 with N=30, delta=.15, q=.80, tau=.70. Preserve the user's model preference: Astra coordinates/reviews, GPT-6.1 Sol implements if delegation is used.

**Goal:** Audit and improve finite-budget individual acceptability calibration, separating whole-pipeline performance from sampling with a common estimator.

**Architecture:** Add a small `finite_budget` package beside the frozen legacy package. Reuse immutable observations, execution calibration/quadrature and semantic RNG tools. Samplers own only public histories; a separate readout/evaluator layer produces pipeline and common-estimator outputs without changing trajectories.

**Tech Stack:** Existing Python 3.12, NumPy, SciPy, pandas, matplotlib, pytest; no new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-11-05-finite-budget-calibration-audit-design.md` (approved 2026-11-05).

**Path abbreviations:** every `finite_budget/...` below means `comfort_boundary_bo_research_package/simulation/finite_budget/...`; every `test_finite_budget_*.py` means `tests/test_finite_budget_*.py`.

## Global Constraints

- Primary proposal: tau=.70, N=30, delta=.15 m/s², supported success target .80; checkpoints10/15/20/30/40/60; horizon60. Sensitivity delta=.10/.20 cannot replace the primary result.
- Public domain[0,3],31 targets; measured acceleration assumed exact. Calibration90, separate cost. Same execution settings as legacy.
- Preserve legacy source, configs, results and entry point. Publish v2 only after tests, source freeze, independent analysis and user-authorized execution complete.
- User authorizes implementation, validation, controlled execution and a separate v2 branch; preserve v1 and its recovery tag.
- No policy receives B/W/lambda/truth probabilities/future draws. No selection on held-out outcomes. Failures remain denominators. No claim that Bayes must win.
- All implementation paths below are repository-relative under `.worktrees/finite-budget-v2` (branch `research/finite-budget-v2`); keep all v2 code/config/results in this isolated worktree; synchronize only version/recovery guidance to the workspace root after checking for user edits, never overwrite root v1 files.

**Prospective numerical amendment (2026-11-05):** Fixed public histories failed the original121×41 probability-resolution tolerance.241×41 against481×81 passed all30 checks; adopt241 B nodes /41 k nodes and7 execution nodes for new/common inference before any outcome run. Legacy81×41 is unchanged. Detailed evidence/ruling is recorded in the approved design and diagnostic artifacts.

## Execution status (final research review; publication pending)

- Tasks1–3 scientific core: implemented and lead-reviewed; all scientific formula, public-history, failure-retention and exact-prior transport gates passed source review.
- Task4 runner/configs: implemented and lead-reviewed, including freeze gate, shared calibration, strict output validation, and deterministic participant-parallel execution (`--workers 6`).
- Task5 research implementation, all planned development/heldout/seven-stress batches, full numerical reconstruction, independent raw-record audits, figures and Chinese results/reproduction documentation: complete and lead-reviewed. Git publication remains root-owned pending work.
- Latest root integrated suite:222 passed in95.89 seconds. Main69,120 and stress24,192 numerical readouts were completely reconstructed, and all raw-record/statistical audits passed; seven complete trajectories replayed exactly across420 trials. Root visually checked12main plots; lead visually checked14stress plots. Scientific and analysis sources remain frozen; selected staircase .6/.15 was independently recomputed and approved before heldout sampling.
- Final claims PASS: N30 primary evidence is insufficient in all six main scenarios; N60 is a secondary budget result. All main supported-success comparisons against staircase include zero after six-scenario adjustment. Local secondary error improvements do not establish general superiority. Stress width_wide stopping accuracy9/17 is retained as a limitation. See the tracked final research review and Chinese report.
- Checklist lines below preserve the original planned work; a line combining source/tests with final commit/publication is not marked complete prematurely.
## Review Focus

- A centered B prior changes the joint prior; exact coordinate relabeling alone must leave predictions and decisions unchanged (Task2).
- Delta-window decisions on a coarse grid can have artificial ties or endpoint mass; pin inclusive tolerance, deterministic ties, grid refinement and no clipping (Task2).
- A useful-looking staircase reversal average may target a command-marginal criterion rather than actual B_tau; retain its label and keep it outside the main B_tau ranking (Task3/4).
- Firth fitting can still be unsupported with identical intensities, constrained coefficients or all-one labels; never hide those records or assign fake intervals (Task3/4).
- Outcome definitions in JSON must be executed, not merely printed; changing readout must not alter a trajectory, and failed outputs must count against success (Task1/4).

---

### Task 1: Public contracts and finite-budget metrics

**Create:** `comfort_boundary_bo_research_package/simulation/finite_budget/{__init__.py,contracts.py,metrics.py}`; `tests/test_finite_budget_metrics.py`.

**Interfaces:** frozen `PriorSpec(kind,center,sd,b_min,b_max,b_nodes,k_min,k_max,k_nodes,log_k_mean,log_k_sd)`; `StudySpec(tau,delta,primary_budget,max_budget,checkpoints,success_target,calibration_n,seed,split)`; `Readout(boundary,lower,upper,status,edge_mass,posterior_success)` with optional interval/probability fields represented explicitly as missing. `assess(readout,history,true_boundary,delta)->dict` is evaluator-only. `wilson_interval(successes,n,confidence=.95)->tuple` and `fixed_budget_summary(rows,budget,delta)->dict` retain all participants.

- [ ] Write tests for q/CI examples, all-missing outputs, exact delta inclusion, both-answer/range support, out-of-domain reports, and n mismatch. Include a failed fit whose omission would falsely improve success.
- [ ] Run `python -m pytest tests/test_finite_budget_metrics.py -q` and verify the missing-module failure.
- [ ] Implement contracts, enum validation and primary/fixed-checkpoint summaries. Unsupported configuration fields must raise; no silent fallbacks to the legacy suffix event.
- [ ] Run focused tests, review metric interpretation, commit the tested unit.

### Task 2: Boundary posterior, comparable readouts and acquisition

**Create:** `finite_budget/boundary_model.py`, `finite_budget/acquisition.py`; tests `test_finite_budget_model.py`, `test_finite_budget_acquisition.py` (paths under simulation/tests as above).

**Interfaces:** `BoundaryPosterior(tau,prior).observe(Observation)`; immutable posterior B/k/weights arrays; `median_readout()`, `precision_readout(delta)`, `predict_acceptance(x)`; `legacy_joint_grid(tau,PriorGrid)` imports existing weights exactly; `BoundaryPosterior.from_joint_grid(tau,B,k,weights)` preserves all irregular legacy nodes/support and correlations for both tests and the old-prior precision sampler. `variance_gain(posterior,targets,belief,nodes)` and `precision_gain(posterior,targets,belief,delta,nodes)` return target-aligned arrays. The fixed decision grid is z=-5:.025:5 (401 points), separate from posterior integration nodes; use inclusive |B-z|<=delta with tolerance1e-12, ties nearest posterior median then smaller z.

- [ ] Test p(B)=tau, normalization, stable all-accept/all-reject updates, prior marginal summaries, legacy same-joint transport equivalence, and no physical-domain clipping.
- [ ] Test A_delta by explicit X×Y posterior enumeration on tiny grids; compare zero-noise integration with point input; test nonnegative expected gain within numerical tolerance and deterministic ties.
- [ ] Validate that the decision grid covers all posterior B nodes, including transported legacy nodes; reject inconsistent tau/support combinations rather than truncating nodes.
- [ ] Implement direct-B priors and both acquisitions using cached likelihoods; choose commands by acquisition maximum, exact/tolerance ties use policy RNG. Reuse the unchanged execution quadrature.
- [ ] Check predetermined public histories (empty; mixed [(.3,1),(.9,1),(1.5,0),(2.1,0)]; all-accept; all-reject; two opposing samples) with121×41 versus241×81 and7 versus15 nodes. Require boundary readout differences<=.025 and S_delta differences<=.02; record maximum acquisition differences and whether best command changes. For ambiguous maxima compare acquisition loss at the coarse choice; if it exceeds1% of the fine maximum plus1e-6, raise the resolution globally before the held-out freeze. Do not tune using algorithm outcomes.
- [ ] Run both test files, inspect diagnostic tables, commit. Record that a revised prior or objective may worsen results.

### Task 3: Population, staircase and whole-pipeline readouts

**Create:** `finite_budget/population.py`, `finite_budget/samplers.py`, `finite_budget/readouts.py`; tests `test_finite_budget_population.py`, `test_finite_budget_samplers.py`, `test_finite_budget_readouts.py`.

**Interfaces:** `PopulationSpec(boundary_low,boundary_high,width_median,width_log_sd,lapse)`; `draw_latents(n,spec,rng)->list[(B,W)]`; `passenger_from_latent(B,W,family,tau,lapse)` reuses the existing immutable Passenger after converting W to k. `StaircaseSpec(initial=.6,floor=.15,start=1.5,reversals_per_halving=2)`; `make_sampler(name,public_config,belief,rng)` exposes suggest/observe and optional private-model readout. `fit_firth(history,tau,support)->Readout`; `reversal_readout(history,reversal_indices,count=4)->dict` has explicit command/realized labels.

- [ ] Test both crossings p(B)=tau and physical x_.2-x_.8=W for every family, paired latent reuse, lambda interpretation and rejection of impossible criteria. Verify no inference imports/truth arguments reach samplers.
- [ ] Test staircase expected drift, .6→.3→.15 schedule, continuous state/projection, grid ties, clamp, start sensitivity and exact presented reversal indices. Ties/projected repeated targets cannot create false direction reversals; direction is defined by raw accept/reject update direction, as in legacy, and separately record actual command changes.
- [ ] Adapt samplers: old variance BO and UCB delegate to unchanged legacy strategies; old-prior precision sampler uses the exact transported joint grid fromTask2; new-prior BO variants useTask2 direct-B grid; staircase has configurable public parameters. Internal sampler model never consumes the evaluator or common readout.
- [ ] Implement Firth log-likelihood+.5logdet(X'WX) in linear-logit coordinates, searched over B/log k support. Deterministic starts B={.5,1.5,2.5},k={1,4,12}; SciPy bounded optimizer, retain best converged solution. Report failure if rank<2/nonfinite/no converged solution; record active bounds. Do not silently add ridge or alter the penalty. Firth emits no invented Bayesian interval.
- [ ] Verify Firth likelihood/penalty against independently calculated tiny data examples, separation with finite fit, rank-deficient inputs, constraint handling and stable answers from different starts. Data-support checks remain common Task1 rules; only finite-output MAE is explicitly conditional and always paired with failure counts.
- [ ] Run focused tests, document conventional-fit versus native-reversal distinction, commit.

### Task 4: Runner, readout separation and frozen configurations

**Create:** `finite_budget/study.py`, `finite_budget/__main__.py`, `configs/finite_budget_{development,heldout,stress}.json`, `tests/test_finite_budget_study.py`.

**Interfaces:** `run_study_v2(config,output_dir)->dict`; CLI `python -m comfort_boundary_bo_research_package.simulation.finite_budget --config PATH --output PATH`. Outputs separate trial observations, per-budget readouts (with track/readout names), participant truths, effective config, source hashes and summaries. Preserve entire histories; all post-hoc readouts see only each history prefix.

- [ ] Test method-order/reader-order invariance, stable semantic method IDs, pure prefix evaluation, paired latent reuse across families/execution and separate RNG streams, declared config consumption, failure denominators and refusal to overwrite results.
- [ ] Run a trajectory once and evaluate common and native pipeline readouts at all checkpoints. Common estimator is always the new centered B posterior with z_delta and median; Firth runs on staircase histories at checkpoints. Record the legacy-native median separately. The 2×2 dev matrix additionally cross-reads each history with old/new priors × median/z_delta (four outputs), without feeding them back to selection. Label this full factorial attribution as development evidence only.
- [ ] Implement optional public-history stop replay from t>=8 under the spec, including all subjects' capped cost, stop proportion and correctness at stop. Keep native Firth outside claims of identical posterior stopping.
- [ ] Save UCB's native argmax-Q command separately from the common B_tau estimate. If reporting its acceptability diagnostic, the evaluator alone integrates the hidden response curve over true execution using deterministic quadrature (31 nodes, verify against61 on the fixed diagnostic cases); label this oracle simulation evaluation, not new feedback or an inferred B_tau. Neither curve nor truth-based score enters the sampler.
- [ ] Encode development32×6×10×30, main128×6×5×60, stress7×64×3×60; freeze exact sampler IDs and defaults. Choose staircase using A-layer Firth supported success atN30, then capped MAE(min(error,3), missing/optimizer-failure=3), then smaller initial/floor steps. Reuse that single choice in both final layers. No hidden source defaults.
- [ ] Share latents across family/method and calibrated execution belief across family/method for each base participant+execution condition; keep method-specific response/execution randomness isolated. Main calibration counter must be128×2×90=23,040, with explicit reuse IDs.
- [ ] Add snapshot/hash tests and effective-config consistency; run focused suite and legacy suite, commit.

### Task 5: Analysis, controlled execution and research report

**Create:** `finite_budget/analysis.py`, `tests/test_finite_budget_analysis.py`; generated results in a new dated directory and report `comfort_boundary_bo_research_package/docs/finite_budget_results_zh.md`.

**Interfaces:** `analyze_v2(input_dir,output_dir)->dict` validates full data before any summaries, outputs separate pipeline/common tables, fixed-budget success/MAE/P90/exposure plots, paired effects and applicability/failure tables. User-facing method labels include both sampler and readout.

- [ ] Test incomplete runs, missing failed participants, independently constructed paired contrasts, Wilson intervals, Bonferroni confidence level, no cross-condition pooling, and unchanged main metrics when sensitivity delta changes. Use20,000 paired percentile bootstrap draws per scenario. delta=.10/.20 changes evaluation tolerance on the same z_.15 outputs; any recomputed z_.10/z_.20 is separately labeled readout sensitivity.
- [ ] Run deterministic numerical checks and a tiny independent runtime pilot. Run development once, choose staircase by the spec rule, record every candidate result, then freeze source/config/analysis definitions and n=128. Declare all plan deviations before new held-out data are viewed.
- [ ] Execute held-out once. Independently recompute each trial/checkpoint error and each support/failure classification, verify common-readout invariance and exact replay of a small subset. If a scientific implementation error requires rerun, preserve the invalidated run and record the reason; do not rerun to obtain a favorable ranking.
- [ ] Run the seven predeclared stress conditions if compute permits; if deferred, label them untested and restrict robustness statements. Prior-shift/weak-prior diagnostics only re-read fixed public/development histories, add no new feedback and remain separate development evidence.
- [ ] Produce plots and Chinese report addressing: whether BO meets N30/delta.15/q.80, comparison with staircase in each layer, where it fails, whether acquisition/prior/readout changes account for differences, and what cannot be concluded about humans. Report calibration costs separately.
- [ ] Root verifies tests/artifacts/figures; Astra reviews claims if delegated. Only after approved implementation completes, deliver v2 in its isolated worktree, synchronize only version/recovery guidance, refresh manifest, commit/push as authorized, verify remote SHA. Do not mark a performance goal achieved merely because tests pass.

## Self-review and handoff

Spec sections1/5 map toTask1/4/5; prior/acquisition toTask2; population/staircase and pipeline readout toTask3; layer separation and cost/RNG toTask4; statistics/provenance toTask5. Review-focus failures have explicit tests above. Source changes are contained in a new small package; legacy algorithms remain executable.

Approved by the user on 2026-11-05. Astra coordinates/reviews; at most two sequential GPT-6.1 Sol implementation workers. Root owns integrated execution, delivery and commits/pushes; no worker commits.
