"""Independent evaluator and reproducible, frozen-config study runner."""
from dataclasses import asdict, replace
import csv
import hashlib
import json
from pathlib import Path
import math
import numpy as np
from .execution import ExecutionTruth, execute, calibrate_execution, spawn_streams
from .passenger import generate_passengers
from .public import Observation, PolicyConfig
from .policies import make_policy
from ..monotone_bayes import PriorGrid

FAMILY_IDS={'logistic':1,'probit':2,'lapse_logistic':3}
EXECUTION_IDS={'precise':1,'variable':2}
METHOD_IDS={'bayes_risk':1,'bayes_point':2,'ucb_tvcg':3,'ucb_tau':4,'staircase':5}


def accuracy_events(absolute_errors, delta, earliest=10, window=5):
    """Retrospective suffix-stable primary and rolling-window secondary trials."""
    good=np.asarray(absolute_errors,dtype=float)<=delta
    n=len(good)
    primary=next((t for t in range(earliest,n-window+2) if good[t-1:].all()),None)
    secondary=next((t for t in range(max(earliest,window),n+1) if good[t-window:t].all()),None)
    return primary,secondary


def _csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def _validate(config):
    n=config.get('participants_per_cell',2); budget=config.get('budget',60)
    for key,value in [('participants_per_cell',n),('budget',budget),('seed',config['seed'])]:
        if not isinstance(value,int) or isinstance(value,bool) or value < (0 if key=='seed' else 1):
            raise ValueError(f'invalid {key}')
    if n>=10000: raise ValueError('participant ID allocation requires n < 10000')
    for field,known in [('families',FAMILY_IDS),('methods',METHOD_IDS),('execution_conditions',EXECUTION_IDS)]:
        values=config[field]
        if not values or len(values)!=len(set(values)) or any(v not in known for v in values):
            raise ValueError(f'invalid or duplicate {field}')
    if not math.isfinite(config.get('delta',.15)) or config.get('delta',.15)<=0:
        raise ValueError('positive finite delta required')
    return n,budget


def run_study(config: dict, output_dir: Path) -> dict:
    n,budget=_validate(config)
    output_dir=Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError('refusing nonempty output directory; choose a new provenance path')
    output_dir.mkdir(parents=True,exist_ok=True)
    # Normalize a detached JSON snapshot and freeze it before any random draws.
    config=json.loads(json.dumps(config,allow_nan=False))
    frozen=json.dumps(config,sort_keys=True,indent=2,allow_nan=False)+'\n'
    digest=hashlib.sha256(frozen.encode('utf-8')).hexdigest()
    (output_dir/'config.json').write_text(frozen,encoding='utf-8')
    (output_dir/'config.sha256').write_text(digest+'\n',encoding='ascii')
    public_parameters=dict(config.get('policy',{}))
    public_parameters['tau']=config.get('tau',.7)
    if 'targets' in public_parameters: public_parameters['targets']=tuple(public_parameters['targets'])
    policy_config=PolicyConfig(**public_parameters)
    # Pin effective scientific defaults as well as user input before draws.
    source_dir=Path(__file__).resolve().parent
    sources=sorted(source_dir.glob('*.py'))
    sources.append(source_dir.parent/'monotone_bayes.py')
    effective=dict(policy=asdict(policy_config),
                   prior_grid=asdict(PriorGrid(midpoint_nodes=policy_config.midpoint_nodes,
                                              slope_nodes=policy_config.slope_nodes)),
                   population=dict(boundary_uniform=[.5,2.5],log_slope_mean=float(np.log(4)),
                                   log_slope_sd=.35,lapse_logistic=.10),
                   source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (output_dir/'effective_parameters.json').write_text(json.dumps(effective,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    delta=config.get('delta',.15)
    trials=[]; participants=[]; truths=[]
    for family in config['families']:
        for execution_name,vehicle_parameters in config['execution_conditions'].items():
            truth=ExecutionTruth(**vehicle_parameters)
            if (truth.lower,truth.upper)!=(policy_config.lower,policy_config.upper):
                raise ValueError('vehicle and public domain bounds must agree')
            scenario=f'{family}__{execution_name}'
            for participant in range(n):
                population_id=FAMILY_IDS[family]*1000000+participant
                paired_id=population_id+EXECUTION_IDS[execution_name]*10000
                population_stream=spawn_streams(config['seed'],population_id,0)['population']
                passenger=generate_passengers(1,family,policy_config.tau,population_stream)[0]
                if 'boundary_override' in config:
                    passenger=replace(passenger,boundary=float(config['boundary_override']))
                calibration_stream=spawn_streams(config['seed'],paired_id,0)['execution_calibration']
                calibration_n=config.get('calibration_n',90)
                belief=calibrate_execution(truth,calibration_stream,n=calibration_n)
                truths.append(dict(scenario=scenario,participant=participant,passenger=asdict(passenger),
                                   vehicle=asdict(truth),execution_belief=asdict(belief),
                                   calibration_measurements=calibration_n))
                for method in config['methods']:
                    streams=spawn_streams(config['seed'],paired_id,METHOD_IDS[method])
                    # Exact public whitelist: no passenger, truth, probabilities or evaluator state.
                    policy=make_policy(method,policy_config,belief,streams['policy'])
                    identity=dict(scenario=scenario,family=family,execution=execution_name,
                                  participant=participant,method=method)
                    own=[]
                    for trial in range(1,budget+1):
                        target=float(policy.suggest())
                        if target not in policy_config.targets:
                            raise ValueError('policy suggested a command outside the common target grid')
                        realized=execute(target,truth,streams['execution'])
                        acceptable=passenger.respond(realized,streams['feedback'])
                        policy.observe(Observation(trial,target,realized,acceptable))
                        estimate=policy.estimate()
                        signed=estimate.boundary-passenger.boundary
                        row=dict(**identity,trial=trial,target=target,realized=realized,acceptable=acceptable,
                                 estimate=estimate.boundary,lower=estimate.lower,upper=estimate.upper,
                                 support=estimate.support,edge_mass=estimate.edge_mass,absolute_error=abs(signed),
                                 signed_error=signed,covered=estimate.lower<=passenger.boundary<=estimate.upper,
                                 interval_width=estimate.upper-estimate.lower)
                        trials.append(row); own.append(row)
                    primary,secondary=accuracy_events([r['absolute_error'] for r in own],delta)
                    last=own[-1]; unacceptable=sum(1-r['acceptable'] for r in own)
                    out=not policy_config.lower<=passenger.boundary<=policy_config.upper
                    unidentifiable=(all(r['acceptable']==own[0]['acceptable'] for r in own)
                                    or last['support']!='within_observed_range' or out)
                    participants.append(dict(**identity,boundary=passenger.boundary,slope=passenger.slope,
                        lapse=passenger.lapse,tau=passenger.tau,budget=budget,
                        primary_event_trial=primary,primary_observed=primary is not None,
                        primary_cost=primary if primary is not None else budget,
                        secondary_event_trial=secondary,secondary_observed=secondary is not None,
                        secondary_cost=secondary if secondary is not None else budget,
                        final_absolute_error=last['absolute_error'],final_signed_error=last['signed_error'],
                        overestimated=last['signed_error']>delta,unacceptable_count=unacceptable,
                        unacceptable_rate=unacceptable/budget,interval_coverage=last['covered'],
                        interval_width=last['interval_width'],out_of_domain=out,unidentifiable=unidentifiable))
    _csv(output_dir/'trials.csv',trials)
    _csv(output_dir/'participants.csv',participants)
    (output_dir/'truth.json').write_text(json.dumps(truths,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    summary=dict(config_sha256=digest,split=config.get('split','unspecified'),
                 scenarios=len(config['families'])*len(config['execution_conditions']),
                 participants_per_cell=n,participant_method_rows=len(participants),trial_rows=len(trials),
                 primary_endpoint='suffix_stable',secondary_endpoint='rolling_five',
                 calibration_measurements_per_participant_condition=config.get('calibration_n',90),
                 total_calibration_measurements=config.get('calibration_n',90)*len(truths),
                 calibration_excluded_from_passenger_trial_counts=True)
    (output_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary



