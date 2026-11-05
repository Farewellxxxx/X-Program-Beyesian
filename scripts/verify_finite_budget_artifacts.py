"""Independent raw-record audit; imports no simulation or analysis implementation.

Run after the scientific analysis. Recompute classifications and all sensitivity
success counts directly from saved observations, estimates and evaluator truths.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def check_equal(a, b, context):
    if isinstance(a, float) and isinstance(b, (float, int)):
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (context, a, b)
    else:
        assert a == b, (context, a, b)


def verify(run, analysis):
    config = read(run / 'effective_config.json')
    manifest = read(run / 'manifest.json')
    n = config['participants']
    horizon = config['study']['max_budget']
    delta = config['study']['delta']
    scenario_ids = {s['id'] for s in config['scenarios']}
    method_ids = {m['id'] for m in config['methods']}
    people = rows(run / 'participants.jsonl')
    truths = {(p['scenario'], p['participant']): p['B'] for p in people}
    assert len(truths) == len(people) == n * len(scenario_ids)
    histories = defaultdict(list)
    for o in rows(run / 'observations.jsonl'):
        histories[o['scenario'], o['participant'], o['method']].append(o)
    expected_keys = {(s, p, m) for s in scenario_ids for p in range(n) for m in method_ids}
    assert set(histories) == expected_keys
    for key, history in histories.items():
        history.sort(key=lambda r: r['trial'])
        assert [o['trial'] for o in history] == list(range(1, horizon + 1)), key
    checkpoints = rows(run / 'checkpoints.jsonl')
    groups = defaultdict(list)
    for r in checkpoints:
        identity = r['scenario'], r['participant'], r['method']
        history = histories[identity][:r['budget']]
        xs = [o['realized'] for o in history]
        ys = {o['acceptable'] for o in history}
        z = r['boundary']
        finite = r['status'] == 'ok' and z is not None and math.isfinite(z)
        err = z - truths[identity[:2]] if finite else None
        support = finite and ys == {0, 1} and min(xs)-1e-12 <= z <= max(xs)+1e-12
        accurate = finite and abs(err) <= delta+1e-12
        expected = dict(finite=finite, error=err, abs_error=abs(err) if finite else None,
                        supported=support, accurate=accurate, supported_success=support and accurate,
                        overestimate=finite and err > 0, out_of_domain=finite and not 0 <= z <= 3)
        for field, value in expected.items():
            check_equal(r[field], value, (identity, r['budget'], field))
        key = (r['scenario'], r['method'], r['track'], r['estimator'], r['budget'])
        groups[key].append(r)
    expected_groups = set()
    for m in config['methods']:
        name = m['sampler']
        readers = [('common', 'new_precision'), ('common', 'new_median')]
        if name in ('old_variance', 'old_precision', 'new_variance', 'new_precision'):
            readers.append(('pipeline', ('old_' if name.startswith('old_') else 'new_')+'precision'))
        if name == 'old_variance':
            readers.append(('legacy_native', 'old_median'))
        if name == 'staircase':
            readers.append(('pipeline', 'firth'))
        if config['readouts']['factorial']:
            readers.extend(('development_factorial', p+'_'+d) for p in ('old', 'new') for d in ('median', 'precision'))
        expected_groups.update((s, m['id'], track, estimator, budget)
                               for s in scenario_ids for track, estimator in readers
                               for budget in config['study']['checkpoints'])
    assert set(groups) == expected_groups
    for key, group in groups.items():
        assert sorted(r['participant'] for r in group) == list(range(n)), key
    summaries_checked = 0
    for file in ('fixed_budget.jsonl', 'delta_sensitivity.jsonl'):
        summary_rows = rows(analysis / file)
        tolerances = [delta] if file == 'fixed_budget.jsonl' else [.10, .20]
        actual_summary_keys = [(s['scenario'], s['method'], s['track'], s['estimator'], s['budget'], s['delta']) for s in summary_rows]
        assert len(set(actual_summary_keys)) == len(actual_summary_keys)
        assert set(actual_summary_keys) == {(*k, tolerance) for k in expected_groups for tolerance in tolerances}
        for s in summary_rows:
            key = (s['scenario'], s['method'], s['track'], s['estimator'], s['budget'])
            group = groups[key]
            tolerance = s['delta']
            successes = sum(r['supported'] and r['abs_error'] <= tolerance+1e-12 for r in group)
            check_equal(s['n'], n, (file, key, 'n'))
            check_equal(s['supported_successes'], successes, (file, key, 'successes'))
            check_equal(s['supported_success_rate'], successes/n, (file, key, 'rate'))
            check_equal(s['failure_count'], sum(not r['finite'] for r in group), (file, key, 'failures'))
            errors = sorted(r['abs_error'] for r in group if r['finite'])
            def quantile(q):
                if not errors:
                    return None
                index = (len(errors)-1)*q
                lower = math.floor(index)
                upper = math.ceil(index)
                return errors[lower]+(errors[upper]-errors[lower])*(index-lower)
            derived = dict(finite_count=len(errors), failure_rate=(n-len(errors))/n,
                           finite_mae=sum(errors)/len(errors) if errors else None,
                           finite_median_error=quantile(.5), finite_p90_error=quantile(.9),
                           support_rate=sum(r['supported'] for r in group)/n,
                           accurate_rate=sum(r['finite'] and r['abs_error'] <= tolerance+1e-12 for r in group)/n,
                           overestimate_rate=sum(r['finite'] and r['error'] > 0 for r in group)/n,
                           active_bound_count=sum(bool(r['active_bounds']) for r in group))
            for field, value in derived.items():
                check_equal(s[field], value, (file, key, field))
            zcrit = NormalDist().inv_cdf(.975)
            p = successes/n
            center = (p+zcrit*zcrit/(2*n))/(1+zcrit*zcrit/n)
            radius = zcrit*math.sqrt(p*(1-p)/n+zcrit*zcrit/(4*n*n))/(1+zcrit*zcrit/n)
            check_equal(s['wilson_lower'], max(0., center-radius), (file, key, 'wilson_lower'))
            check_equal(s['wilson_upper'], min(1., center+radius), (file, key, 'wilson_upper'))
            check_equal(s['meets_target'], max(0., center-radius) >= config['study']['success_target'], (file, key, 'target'))
            if file == 'delta_sensitivity.jsonl':
                assert s['readout_delta'] == delta
            summaries_checked += 1
    stop_rows = rows(run / 'stops.jsonl')
    stop_keys = [(r['scenario'], r['participant'], r['method']) for r in stop_rows]
    assert len(set(stop_keys)) == len(stop_keys)
    assert set(stop_keys) == (expected_keys if config['readouts']['stop_replay'] else set())
    for r in stop_rows:
        identity = r['scenario'], r['participant'], r['method']
        t = r['capped_cost']
        assert 1 <= t <= horizon
        history = histories[identity][:t]
        z = r['boundary']
        finite = r['status'] == 'ok' and z is not None and math.isfinite(z)
        err = z-truths[identity[:2]] if finite else None
        xs = [o['realized'] for o in history]
        support = finite and {o['acceptable'] for o in history} == {0, 1} and min(xs)-1e-12 <= z <= max(xs)+1e-12
        check_equal(r['error'], err, (identity, 'stop_error'))
        check_equal(r['correct'], finite and abs(err) <= delta+1e-12, (identity, 'stop_correct'))
        if r['stopped']:
            assert t >= 8 and support and r['posterior_success'] >= .90 and r['edge_mass'] <= .01
        else:
            assert t == horizon
    calibration = rows(run / 'calibrations.jsonl')
    calibration_ids = {r['calibration_id'] for r in calibration}
    assert len(calibration_ids) == len(calibration)
    assert {p['calibration_id'] for p in people} == calibration_ids
    assert sum(c['n'] for c in calibration) == manifest['calibration_count']
    latent_values = defaultdict(set)
    for p in people:
        latent_values[p['latent_id']].add((p['B'], p['W']))
    assert all(len(values) == 1 for values in latent_values.values())
    assert len(latent_values) == manifest['latent_draws']
    assert sum(len(h) for h in histories.values()) == manifest['feedback_count'] == len(expected_keys)*horizon
    return dict(passed=True, independent_of_simulation_imports=True,
                observations=manifest['feedback_count'], checkpoints=len(checkpoints),
                recomputed_summary_rows=summaries_checked, condition_cases=len(people),
                stop_rows=len(stop_rows), stop_scope='recorded-prefix eligibility/error/cost; package validator reconstructs earliest stop',
                independent_latent_draws=len(latent_values), calibration_measurements=manifest['calibration_count'],
                statuses=dict(Counter(r['status'] for r in checkpoints)),
                raw_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(run.iterdir()) if p.suffix in ('.json', '.jsonl')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.input, args.analysis)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'raw_sha256'}))
