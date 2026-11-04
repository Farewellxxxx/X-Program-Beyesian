# Independent synthetic passenger and execution model

The passenger generator is evaluation-only and imports no policy likelihood or inference implementation. Policies receive binary observations and a separately calibrated public execution belief, never a Passenger or ExecutionTruth. These synthetic curves are modeling scenarios, not validated human comfort models.

For each passenger, B is uniform on [0.5, 2.5] m/s² and positive steepness k is lognormal with log mean log(4) and log SD 0.35. The decreasing response is p(x)=lapse/2+(1-lapse) S(k(location-x)), with S logistic or normal CDF. Logistic and probit scenarios have zero lapse; lapse_logistic uses 0.10. For q=(tau-lapse/2)/(1-lapse), location=B+S_inverse(q)/k, hence p(B)=tau exactly. B is the chosen operational crossing, not necessarily the curve midpoint. The finite tau must lie strictly between the response asymptotes. Feedback is an independent Bernoulli draw at the measured realized acceleration. The main stationary scenarios contain neither adaptation nor fatigue or context effects.

Vehicle execution is clip(intercept+gain*target+Gaussian(0,sd),lower,upper). The executed value is subsequently measured; execution deviation does not invalidate a trial. The private vehicle accepts a positive gain and nonnegative SD. Independently sampled calibration observations use equally spaced commands over the interior 20–80% of the physical domain; ordinary affine least squares estimates intercept/gain and residual SD uses n-2 degrees of freedom. This reduces but does not remove clipping bias. Severe clipping or non-Gaussian errors can make this public approximation inaccurate; a nonpositive fitted gain raises an explicit calibration error. Calibration uses observed clipped measurements, not hidden pre-clipping outcomes.

Public acquisition quadrature uses Gaussian Hermite nodes transformed by the calibrated affine mean and SD, then clips each prospective realized value to the physical domain while retaining its normalized weight. This preserves approximate boundary atoms instead of truncating and renormalizing the interior distribution. Seven nodes are a modest numerical approximation; finite-node atom mass and nonlinear risk integrals need not equal analytic clipped-Gaussian integrals. Zero SD yields one deterministic clipped point. Quadrature represents prospective uncertainty only: after execution the realized measurement replaces the prospective distribution in the reporting estimator.

`spawn_streams(seed, participant, method)` uses explicit SeedSequence integer keys, never language hashes or consumption-order-dependent spawning. Stable semantic IDs are population=1, execution_calibration=2, execution=3, feedback=4 and policy=5. Population and execution calibration omit the method key to support paired participants and a shared independent calibration; execution, feedback and policy include it. Drawing feedback therefore cannot change execution or future policy randomness. Generate one population per scenario and pair its members across methods, or regenerate with the same population stream and configuration; no forced equal feedback at unequal stimuli is imposed.

Focused verification from the repository root:

```powershell
$env:TMP=(Join-Path $PWD 'tmp/passenger-worker')
$env:TEMP=$env:TMP
python -m pytest tests/test_decoupled_passenger.py tests/test_decoupled_execution.py --basetemp tmp/passenger-worker/pytest-final -q
```
