"""Evaluator-only fixed-budget endpoints; failures always remain denominators."""
import math
from statistics import NormalDist
import numpy as np
from .contracts import Readout, _integer


def assess(readout, history, true_boundary, delta):
    if not isinstance(readout, Readout):
        raise TypeError('expected Readout')
    if not math.isfinite(true_boundary) or not math.isfinite(delta) or delta <= 0:
        raise ValueError('finite truth and positive delta required')
    finite = readout.status == 'ok' and readout.boundary is not None and math.isfinite(readout.boundary)
    xs = [o.realized for o in history]
    labels = {o.acceptable for o in history}
    supported = bool(finite and labels == {0,1} and min(xs)-1e-12 <= readout.boundary <= max(xs)+1e-12)
    error = float(readout.boundary-true_boundary) if finite else None
    accurate = bool(finite and abs(error) <= delta+1e-12)
    return dict(boundary=readout.boundary,lower=readout.lower,upper=readout.upper,
                status=readout.status,edge_mass=readout.edge_mass,posterior_success=readout.posterior_success,
                active_bounds=readout.active_bounds,finite=finite,supported=supported,
                accurate=accurate,supported_success=supported and accurate,error=error,
                abs_error=abs(error) if finite else None,overestimate=bool(finite and error>0),
                out_of_domain=bool(finite and not 0 <= readout.boundary <= 3))


def wilson_interval(successes, n, confidence=.95):
    if not _integer(n) or not _integer(successes) or successes > n or not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError('invalid binomial counts or confidence')
    if n == 0:
        return (math.nan,math.nan)
    z = NormalDist().inv_cdf((1+confidence)/2)
    p = successes/n
    center = (p+z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return max(0.,center-radius),min(1.,center+radius)


def fixed_budget_summary(rows,budget,delta,*,n=None,success_target=.80):
    """One row per participant at a checkpoint; recompute tolerance from errors.

    Pass n when the caller knows the cohort size; absent participants are an
    error, never silently removed. Explicit failed rows are required.
    """
    if not _integer(budget,1) or not math.isfinite(delta) or delta <= 0:
        raise ValueError('positive budget and delta required')
    if not math.isfinite(success_target) or not 0 < success_target < 1:
        raise ValueError('invalid success target')
    selected = [r for r in rows if r.get('budget',r.get('trial')) == budget]
    if n is not None and (not _integer(n) or len(selected) != n):
        raise ValueError('participant count does not match expected n')
    if selected and all('participant' in r for r in selected) and len({r['participant'] for r in selected}) != len(selected):
        raise ValueError('duplicate participant at fixed budget')
    count = len(selected)
    finite = [r for r in selected if r['finite']]
    errors = np.array([abs(r['error']) for r in finite],dtype=float)
    accurate = sum(abs(r['error']) <= delta+1e-12 for r in finite)
    successes = sum(r['supported'] and abs(r['error']) <= delta+1e-12 for r in finite)
    low,high = wilson_interval(successes,count)
    rate = lambda k: k/count if count else math.nan
    return dict(budget=budget,delta=delta,n=count,supported_successes=successes,
                supported_success_rate=rate(successes),wilson_lower=low,wilson_upper=high,
                meets_target=bool(count and low >= success_target),accurate_rate=rate(accurate),
                support_rate=rate(sum(r['supported'] for r in selected)),finite_count=len(finite),
                failure_count=count-len(finite),failure_rate=rate(count-len(finite)),
                finite_mae=float(errors.mean()) if errors.size else math.nan,
                finite_median_error=float(np.median(errors)) if errors.size else math.nan,
                finite_p90_error=float(np.quantile(errors,.90)) if errors.size else math.nan,
                overestimate_rate=rate(sum(r['error']>0 for r in finite)),
                active_bound_count=sum(bool(r.get('active_bounds')) for r in selected))
