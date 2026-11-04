# Out-of-domain development stress check

Separate diagnostic only; these 20 participant-method records (600 trials) are not pooled with the main held-out comparison. Scientific simulator, policy and inference source files were unchanged. Both configurations retain the same public grid, prior and five methods, with two logistic passengers, precise execution, 30 trials and 90 auxiliary vehicle calibration measurements per passenger-condition. The seeds are development/stress110501 (below) and110502 (above), separate from held-out271828.

| Case | Truth | Final estimate range | All accept histories | All reject histories | Primary observed | Final CI covers truth |
|---|---:|---:|---:|---:|---:|---:|
| below | -0.5 | -0.586 to 0.052 | 0/10 | 0/10 | 4/10 | 10/10 |
| above | 3.5 | 2.940 to 3.404 | 6/10 | 0/10 | 3/10 | 9/10 |

All20 rows retain out_of_domain=True and unidentifiable=True, including constant-response histories. Estimates are reported directly from the common estimator, without clipping to [0,3]; the CSV also records whether any trajectory estimate lies outside that domain. This is not evidence that an out-of-domain true boundary was measured or identified: limited stimuli and potentially constant feedback leave strong prior influence. Interval coverage is final95% interval inclusion of the actual overridden truth, not relative to a clipped boundary. Primary/secondary events retain the unchanged retrospective suffix-stable/rolling-five definitions, delta=.15, earliest trial10 and minimum five estimates. Blank event trials are censored with cost30, never removed.

## Exact commands

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration --config configs/decoupled_stress_below.json --output results/decoupled_calibration_20261105/stress/below
python -m comfort_boundary_bo_research_package.simulation.decoupled_calibration --config configs/decoupled_stress_above.json --output results/decoupled_calibration_20261105/stress/above
```

## Frozen-config hashes

- below: 337452128a0da90468b8beb70966d93a1db855e0052e508902ba7bbdf806691e
- above: 7f8068f0f4b1515d1ed11dbd0ddc4925f4b3d0a03c66953972dee3eb109d4334

Each run also stores effective_parameters.json with complete effective priors/configuration and SHA256 hashes of the scientific source files. stress_summary.csv is a direct deterministic projection of saved participant/trial records, including all methods and failures.

Source audit against main raw/effective_parameters.json: __init__.py, __main__.py, execution.py, monotone_bayes.py, passenger.py, policies.py, public.py and study.py hashes match exactly. analysis.py differs because analysis work continued after the main scientific freeze; analysis.py is not imported by the runner and did not generate stress trials. Both stress runs have identical effective parameters/source hashes. This difference is retained in the per-run manifests rather than hidden.
