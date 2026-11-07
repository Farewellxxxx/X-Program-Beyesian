"""Audit stationary probability curves against SciPy and sample production responses."""
import argparse
import hashlib
import math
from pathlib import Path
import platform
import sys

import numpy as np
import scipy
from scipy.optimize import brentq
from scipy.special import _ufuncs
from scipy.stats import _continuous_distns, _distn_infrastructure, gumbel_l, logistic, norm

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from comfort_boundary_bo_research_package.simulation.decoupled_calibration import passenger
from comfort_boundary_bo_research_package.simulation.finite_budget import population
from comfort_boundary_bo_research_package.simulation.finite_budget.study import write_json


REFERENCES = {"logistic": logistic, "probit": norm, "lapse_logistic": logistic, "gumbel": gumbel_l}
SEED = 202611073
RESPONSES_PER_CELL = 100_000
STANDARDIZED_POSITIONS = (-2, -1, 0, 1, 2)
PSIGNIFIT_REFERENCE = (
    "https://github.com/wichmann-lab/python-psignifit/blob/"
    "d244370bac3081acdbb53e291942f433093eac40/psignifit/sigmoids.py"
)


def reference_distribution(boundary, width, family, tau, lapse):
    """Derive a frozen distribution from SciPy inverse survival quantiles."""
    base = REFERENCES[family]
    q20, q80, qtau = (base.isf((p - lapse / 2) / (1 - lapse)) for p in (0.2, 0.8, tau))
    scale = width / (q20 - q80)
    return base(loc=boundary - scale * qtau, scale=scale)


def deterministic_checks():
    records = []
    cases = [(family, 0.10 if family == "lapse_logistic" else 0.0)
             for family in REFERENCES] + [("lapse_logistic", 0.20)]
    for family, lapse in cases:
        for boundary, width, tau in [(0.6, 0.35, 0.61), (1.5, 0.70, 0.70), (2.4, 1.40, 0.83)]:
            identity = dict(family=family, B=boundary, W=width, tau=tau, lapse=lapse)
            try:
                observer = population.passenger_from_latent(boundary, width, family, tau, lapse)
                reference = reference_distribution(boundary, width, family, tau, lapse)
                xs = np.linspace(boundary - 4 * width, boundary + 4 * width, 161)
                actual = np.array([observer.probability(float(x)) for x in xs])
                expected = lapse / 2 + (1 - lapse) * reference.sf(xs)
                max_error = float(np.max(np.abs(actual - expected)))
                at_boundary = observer.probability(boundary)
                roots = [brentq(lambda x: observer.probability(x) - p,
                                 boundary - 20 * width, boundary + 20 * width, xtol=1e-14)
                         for p in (0.8, 0.2)]
                reference_roots = [reference.isf((p - lapse / 2) / (1 - lapse)) for p in (0.8, 0.2)]
                measured_width = roots[1] - roots[0]
                step = width * 1e-5
                numerical = (observer.probability(boundary + step) - observer.probability(boundary - step)) / (2 * step)
                analytic = population.local_derivative(observer)
                density = -(1 - lapse) * reference.pdf(boundary)
                tails = [observer.probability(x) for x in (-sys.float_info.max, sys.float_info.max)]
                with np.errstate(over="ignore", under="ignore"):
                    reference_tails = (lapse / 2 + (1 - lapse) *
                                       reference.sf([-sys.float_info.max, sys.float_info.max]))
                checks = dict(
                    scipy_grid=max_error <= 1e-12,
                    boundary=math.isclose(at_boundary, tau, rel_tol=0, abs_tol=1e-12),
                    quantiles=np.allclose(roots, reference_roots, rtol=0, atol=1e-11),
                    width=math.isclose(measured_width, width, rel_tol=0, abs_tol=1e-11),
                    monotone=bool(np.all(np.diff(actual) <= 0)),
                    asymptotes=(np.allclose(tails, [1 - lapse / 2, lapse / 2], rtol=0, atol=1e-15)
                                and np.allclose(tails, reference_tails, rtol=0, atol=1e-15)),
                    numerical_derivative=math.isclose(analytic, numerical, rel_tol=1e-7),
                    scipy_derivative=math.isclose(analytic, density, rel_tol=1e-12),
                )
                records.append(dict(**identity, checks=checks, max_abs_scipy_error=max_error,
                                    grid_points=len(xs), probability_at_B=at_boundary,
                                    x80=roots[0], x20=roots[1], reference_x80=reference_roots[0],
                                    reference_x20=reference_roots[1], measured_width=measured_width,
                                    asymptotes=tails, analytic_derivative=analytic,
                                    finite_difference_derivative=numerical, reference_derivative=density,
                                    passed=all(checks.values())))
            except (ArithmeticError, ValueError, RuntimeError) as exc:
                records.append(dict(**identity, passed=False, error=str(exc)))
        invalid = [
            ("nonfinite_boundary", {"B": math.inf}),
            ("zero_width", {"W": 0.0}),
            ("negative_width", {"W": -0.7}),
            ("nonfinite_width", {"W": math.nan}),
            ("zero_tau", {"tau": 0.0}),
            ("unit_tau", {"tau": 1.0}),
            ("nonfinite_tau", {"tau": math.nan}),
            ("incompatible_lapse_width", {"lapse": 0.4}),
        ]
        if lapse:
            invalid.extend([("tau_at_lower_asymptote", {"tau": lapse / 2}),
                            ("tau_at_upper_asymptote", {"tau": 1 - lapse / 2})])
        for name, replacements in invalid:
            params = dict(B=1.5, W=0.7, family=family, tau=0.7, lapse=lapse)
            params.update(replacements)
            try:
                population.passenger_from_latent(**params)
            except ValueError:
                rejected = True
            else:
                rejected = False
            records.append(dict(family=family, lapse=lapse, invalid_parameter_case=name, passed=rejected))
    return records


def monte_carlo_checks():
    rng = np.random.default_rng(SEED)
    records = []
    boundary, width, tau = 1.5, 0.70, 0.70
    for family in REFERENCES:
        lapse = 0.10 if family == "lapse_logistic" else 0.0
        reference = reference_distribution(boundary, width, family, tau, lapse)
        for position in STANDARDIZED_POSITIONS:
            x = boundary + position * width
            p = float(lapse / 2 + (1 - lapse) * reference.sf(x))
            identity = dict(family=family, lapse=lapse, standardized_position=position,
                            realized=x, n_responses=RESPONSES_PER_CELL, reference_probability=p)
            try:
                observer = population.passenger_from_latent(boundary, width, family, tau, lapse=0.10)
                responses = np.fromiter((observer.respond(x, rng) for _ in range(RESPONSES_PER_CELL)),
                                        dtype=np.int64, count=RESPONSES_PER_CELL)
                pairs = responses[::2] * responses[1::2]
                mean = float(responses.mean())
                product_mean = float(pairs.mean())
                mean_se = math.sqrt(p * (1 - p) / len(responses))
                product_se = math.sqrt(p**2 * (1 - p**2) / len(pairs))
                binary = bool(((responses == 0) | (responses == 1)).all())
                mean_passed = abs(mean - p) <= 6 * mean_se
                product_passed = abs(product_mean - p**2) <= 6 * product_se
                records.append(dict(**identity, acceptance_count=int(responses.sum()), acceptance_mean=mean,
                                    mean_se=mean_se, n_adjacent_pairs=len(pairs),
                                    adjacent_both_accepted=int(pairs.sum()), adjacent_product_mean=product_mean,
                                    reference_adjacent_product=p**2, adjacent_product_se=product_se,
                                    binary=binary, mean_passed=mean_passed, adjacent_product_passed=product_passed,
                                    passed=binary and mean_passed and product_passed))
            except (ArithmeticError, ValueError, RuntimeError) as exc:
                records.append(dict(**identity, passed=False, error=str(exc)))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    deterministic = deterministic_checks()
    monte_carlo = monte_carlo_checks()
    passed = all(record["passed"] for record in deterministic + monte_carlo)
    project_files = [Path(__file__), Path(passenger.__file__), Path(population.__file__)]
    scipy_modules = [_continuous_distns, _distn_infrastructure, _ufuncs]
    report = dict(
        passed=passed, deterministic=deterministic, monte_carlo=monte_carlo,
        design=dict(seed=SEED, rng="NumPy default_rng (PCG64)", B=1.5, W=0.70, tau=0.70,
                    lapse_logistic_random_answer_probability=0.10, family_order=list(REFERENCES),
                    standardized_positions=STANDARDIZED_POSITIONS, responses_per_cell=RESPONSES_PER_CELL,
                    nominal_responses=len(REFERENCES) * len(STANDARDIZED_POSITIONS) * RESPONSES_PER_CELL,
                    check_standard_errors=6, adjacent_products="disjoint adjacent response pairs"),
        provenance=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                        platform=platform.platform(), psignifit_reference=PSIGNIFIT_REFERENCE,
                        gumbel_orientation="scipy.stats.gumbel_l.sf on increasing realized acceleration",
                        source_sha256={p.resolve().relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in project_files},
                        scipy_source_sha256={m.__name__: hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()
                                             for m in scipy_modules}),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, report)
    print(f"{'PASS' if passed else 'FAIL'} ({len(deterministic)} deterministic cases, "
          f"{len(monte_carlo)} Monte Carlo cells): {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
