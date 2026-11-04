# Execution belief and population implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline with TDD and one final independent review.

**Goal:** Remove implicit oracle execution knowledge, evaluate independent populations, compare and publish.
**Architecture:** Separate parameter/settings objects, observation-only offline calibrator, restricted policy view, explicit seed metadata, dedicated nested-population audit and comparison script.
**Tech Stack:** Existing Python/NumPy/pandas/matplotlib/pytest; no new dependencies.
**Spec:** `docs/superpowers/specs/2026-11-04-execution-population-design.md`.

## Constraints and review focus

- No hidden generator/passenger fields in calibrated policies or their history; oracle is explicit.
- Preserve physical RNG/generator and default historical population for exact replay.
- Calibration budget is extra, shared, independent of response data and explicitly reported.
- Independent population clusters, paired seeds and settings must remain distinguishable in every table.
- Missing/duplicate/unbalanced comparisons must fail; no pseudoreplication or silent mixing.
- Calibration may be imperfect, clipped and misspecified; conclusions must state these limits.

## Tasks

- [x] 1. Add `execution_belief.py` with immutable parameter/settings and observation-only fit. Add statistical calibration tests (known WLS calculation, invalid/clipped data), watch RED, implement, pass tests.
- [x] 2. Integrate Config seed/mode fields, restricted policy settings/history and separate true/belief objects; expose diagnostics. Test population/process/calibration independence, same observations/no truth leakage, fixed-policy invariance, historical oracle reproduction, new summaries. Keep legacy regression tests explicit about oracle. Pass full suite and commit.
- [ ] 3. Add `run_execution_population_audit.py` and `compare_execution_population.py`. Test scenario design, paired configuration guards, population-cluster intervals and missing/duplicate blocks before implementation. Run 85 scenarios and regenerated extended/POC; compare history, population and belief effects; produce readable report and figures.
- [ ] 4. Independent read-only review, fix verified findings, final tests and integrity checks; sync original workspace; fast-forward and push main; independently verify remote SHA.

## Ledger

- Baseline 59af077; clean main, baseline 36 tests passed. Isolated publication checkout branch feature/execution-belief-population. No AGENTS.md found in workspace ancestry.
- Pre-flight: calibration consumes only execution observations and public bounds; policies consume restricted settings/history; audit consumes seed and belief diagnostics. Existing run_one/evaluate interface retained with added metadata.
- Decision: use the existing authorized scope and sensible explicit defaults; no additional approval round. Implement offline plug-in calibration rather than online learning; all response/acquisition coefficients unchanged.

- Tasks 1-2: eight new calibration/information-boundary/population tests RED to GREEN; prior 36 tests also pass (44 total before audit tests). A batch-runner test exposed reuse of the first cohort; fixed per-scenario population generation.
- Task 3 in progress: four audit/comparison tests RED to GREEN, including complete design coverage; all 85 scenarios launched in four separate processes. Extended and POC regenerated successfully.
