# Finite-budget v2 implementation decisions

Prospective source decisions and subsequent review status, 2026-11-05. Decisions below were made before the indicated data stages; final review evidence is separately dated and labeled. V1 remains frozen at 5556eb4ad95259ee3a8018fd97cd96fd1f9795ca; v2 is isolated on research/finite-budget-v2.

## Decisions recorded before heldout data

- Ruling: User approval supersedes proposal-only language; updated worktree copies of spec/plan — explicit current authorization — no change to numerical design.
- Ruling: Use two sequential implementation stages (Tasks1–3, Tasks4–5), lead reviews each stage and individual task requirements; no extra reviewer agents — user model/seat/cost constraint — risks addressed by explicit review ledger.
- Ruling: All paths resolve in isolated worktree, not historical .publish path — user preservation priority — no legacy bytes edited.
- Ruling: No worker commits; root integrates after review — explicit parent allocation — uncommitted package review uses full source files.
- Ruling: Numeric diagnostics and tiny pilot hooks are source deliverables; root executes integrated diagnostic/development/heldout/stress runs — separates implementation and outcome decisions.
- Ruling: Lapse stress uses logistic link with symmetric lapse .20 via existing lapse_logistic family; other six stress cases are pure logistic — the spec names logistic+variable reference but explicitly varies lapse — avoids silently ignored config and labels this one differing response condition.
- Ruling: Freeze validation is enforced before any heldout draw and hashes all consumed scientific sources plus effective config, selected staircase and diagnostic decision — operationalizes stated sampling-before-freeze prohibition — prospective provenance is checkable rather than merely narrative.
- Ruling: raise v2 direct-B prior/common estimator B nodes from121 to241 globally; retain k nodes41 and execution quadrature7. Legacy midpoint/slope81×41 remain unchanged — fixed public-history probability resolution evidence only, no algorithm-outcome batches viewed — approximately doubles direct-B inference/acquisition compute; pilot will quantify cost. Stage2 worker instructed to update default PriorSpec and all shipped effective configs. This is a numerical integration refinement, not a change of prior density, decision grid, tau/delta or scientific ranking rule.
- Ruling: preserve root-directory v1; v2 code/config/results remain solely in isolated research worktree, and only version/recovery guidance is synchronized to root — user preservation priority overrides historical delivery wording — users must enter v2 path explicitly to run new package.
- Ruling: enable optional common-posterior stop replay for heldout/stress before freeze, as root approved; fixed-N primary unchanged — inexpensive complete secondary diagnostics — all capped nonstoppers retained and no Firth speed-equivalence claim.
- Ruling: six-scenario Bonferroni intervals apply to main comparisons, not the seven stress cases; stress remains per-scenario exploratory unless separately declared — avoids false familywise-coverage wording — stress comparisons have no joint significance guarantee.

## Scoped review evidence

- Astra lead reviewed each scientific module, runner/config interfaces, and analysis definitions; two GPT-6.1 Sol workers implemented sequentially, with no worker commits or outcome batches.
- Core scope: public contracts, failure denominators, exact old joint transport, measured-X conditional precision acquisition, B/W-matched populations, raw-direction staircase, constrained alpha/beta Firth penalty and deterministic failure retention.
- Runner/analysis scope: independent native/common readouts, semantic RNGs, shared calibration, complete Cartesian grids, pre-draw freeze verification, separate scientific/analysis provenance, fixed-estimate tolerance sensitivity, participant-paired inference, and capped stop replay.
- Final worker-scoped evidence after execution-only parallelization:56 finite-budget tests passed in18.16 seconds. Root fresh integrated suite:213 tests passed in56.01 seconds. Participant0 output rows exactly matched the pre-refactor serial pilot across all6JSONL artifacts. See docs/2026-11-05-finite-budget-verification.md for root evidence.
- Task5 data execution, independent full-data checks, actual-result interpretation and final publication remain pending at this source review checkpoint. No performance-goal attainment is inferred from tests.

## Runtime decision before development

Root serial pilot1800feedback/180calibrations took25.598seconds; parallel n6pilot10800feedback/1080calibrations took38.830seconds while pytest also ran. Exact identity checks validate participant-parallel execution; runtime timing is approximate. Root authorized all development/main/seven-stress batches at six workers with unchanged scientific n/seeds. Science and analysis source are locked once development begins. All actual-result claims remain pending until the corresponding data are analyzed and reviewed.


## Prospective heldout/stress freeze review

Before heldout sampling, the lead independently recomputed all six staircase candidate ranks from raw actual-x/response histories and Firth N30 boundary outputs. The winner was initial .6/floor .15 (start1.5; every two reversals halve), with development six-scenario equal-weight supported success .765625 and cappedMAE .11207542660297821. This is development selection evidence, not a confirmatory pooled success estimate.

Both frozen configs matched current consumed scientific and analysis fingerprints, the numerical decision artifact hash and development manifest hash. Heldout128×6×5×60 yields230,400 feedback plus23,040 shared calibration measurements; stress64×7×3×60 yields80,640 feedback plus40,320 calibration measurements. Main/stress retain the same selected staircase and unchanged seeds/criteria; optional common-reader stopping remains secondary.

The exact configuration hashes and machine-readable review proof are retained in `results/finite_budget_calibration_20261105/freeze_review.json`. Heldout began only after this review passed. Frozen scientific/analysis source is unchanged; an external parallel verification script may accelerate complete numerical readout reconstruction without changing the estimator or reducing the audited outputs.

## Final pre-results verification status

After the standalone readout verifier was added without modifying frozen science, the root fresh full suite passed222tests in95.89seconds under concurrent simulation load. All15consumed scientific files and analysis.py were independently rehashed against the heldout freeze after the external script addition and matched. Main and pre-frozen stress execution may overlap; wall-clock runtime is computational-cost metadata only, not an algorithm-efficiency endpoint.

## Final research review, 2026-11-05 — PASS; publication pending

All planned batches and Task5 research deliverables are complete. Root full numerical audits reconstructed69,120main readouts/483,840fields and24,192stress readouts/169,344fields; all matched. Separate independent raw-record/statistical audits passed for both batches. Seven complete trajectories replayed exactly across420trials. Root visually reviewed12main plots; the lead visually reviewed14stress plots. These are validation results, not evidence that the primary performance goal was achieved.

The lead reviewed the Chinese results report and reproduction guide against fixed-budget, paired-effect, failure/support, sensitivity and stopping tables. N30newprecision success76.56–85.16% has Wilson lower bounds below80% in every main scenario; evidence is insufficient rather than proof the true rate is below80%. N60passes separately in all six scenarios as a secondary fixed-budget result. A/B primary success intervals against staircase all include zero after the declared six-scenario correction; the local secondary capped-error improvement cannot establish general superiority or attribute the full pipeline benefit to sampling alone.

The report correctly distinguishes128independent main latents from768condition cases,448independent stress latents, calibration costs, old-native median versus old-prior window readout, and A/B outputs that are not independent replications. Stress comparisons are exploratory within each condition. Width-wide stop replay retains9/17correct among17/64stoppers and54.42mean capped trials: nominal90%posterior mass is not empirical90%assurance. No human efficacy, safety, universalUCB, or unmatched Firth stopping-speed claim is made.

Final review proof and document fingerprints are in `results/finite_budget_calibration_20261105/final_research_review.json`. No scientific or analysis source was changed during this review. Root still owns manifest refresh, commit/push to the separate research branch, and remote/main/tag verification; publication is not asserted here.
