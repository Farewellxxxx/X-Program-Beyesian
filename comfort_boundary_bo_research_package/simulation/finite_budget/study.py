"""Finite-budget trajectories, evaluator-only readers, and pre-draw provenance gates.

JSONL observations are public records. Truths/calibration and checkpoint readers
live in separate files and never enter a policy's public history.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import re
import time
import platform
import os
import tempfile
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
import numpy as np
import scipy
from .contracts import StudySpec, SamplerConfig, PriorSpec, StaircaseSpec, Readout, _integer
from .population import PopulationSpec, draw_latents, passenger_from_latent, local_derivative
from .samplers import make_sampler
from .boundary_model import BoundaryPosterior, legacy_joint_grid
from .readouts import fit_firth, reversal_readout
from .metrics import assess
from ..monotone_bayes import PriorGrid
from ..decoupled_calibration.public import Observation, ExecutionBelief
from ..decoupled_calibration.execution import ExecutionTruth, calibrate_execution, execute, execution_quadrature

EXECUTIONS = {'precise':dict(intercept=0.,gain=1.,sd=.03,lower=0.,upper=3.),
              'variable':dict(intercept=.08,gain=.92,sd=.18,lower=0.,upper=3.)}
SAMPLERS = ('old_variance','new_variance','new_precision','old_precision','staircase','ucb_tvcg')
REQUIRED_FILES = ('participants.jsonl','calibrations.jsonl','observations.jsonl','checkpoints.jsonl',
                  'diagnostics.jsonl','stops.jsonl')


def clean_json(value):
    if isinstance(value,dict): return {k:clean_json(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean_json(v) for v in value]
    if isinstance(value,(float,np.floating)): return float(value) if math.isfinite(value) else None
    if isinstance(value,np.integer): return int(value)
    if isinstance(value,np.bool_): return bool(value)
    return value


def canonical(value):
    return json.dumps(clean_json(value),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def digest(value): return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def write_json(path,value):
    Path(path).write_text(json.dumps(clean_json(value),indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _strict(data,allowed,label):
    if not isinstance(data,dict): raise TypeError(f'{label} must be an object')
    extra=set(data)-set(allowed)
    if extra: raise ValueError(f'unknown {label} fields: {sorted(extra)}')


def _record(cls,data):
    _strict(data,cls.__dataclass_fields__,cls.__name__)
    return cls(**data)


def staircase_id(spec):
    return f"staircase_i{int(round(spec.initial*100)):03d}_f{int(round(spec.floor*100)):03d}"


def effective_config(config):
    """Expand and validate every scientific field; this exact object is consumed."""
    if isinstance(config,(str,Path)): config=json.loads(Path(config).read_text(encoding='utf-8-sig'))
    _strict(config,('version','study','participants','population','sampler','methods','scenarios','readouts','analysis'),'config')
    if config.get('version',2)!=2: raise ValueError('config version must be 2')
    study=_record(StudySpec,config.get('study',{}))
    n=config.get('participants',32)
    if not _integer(n,1): raise ValueError('participants must be a positive integer')
    pop=_record(PopulationSpec,config.get('population',{}))
    s=dict(config.get('sampler',{}))
    s['prior']=_record(PriorSpec,s.get('prior',{})); s['staircase']=_record(StaircaseSpec,s.get('staircase',{}))
    s.setdefault('tau',study.tau); s.setdefault('delta',study.delta)
    sampler=_record(SamplerConfig,s)
    if sampler.tau!=study.tau or sampler.delta!=study.delta: raise ValueError('sampler and study tau/delta must agree')
    # Check both independent and transported supports before feedback generation.
    BoundaryPosterior(study.tau,sampler.prior)
    legacy_joint_grid(study.tau,PriorGrid(midpoint_nodes=sampler.midpoint_nodes,slope_nodes=sampler.slope_nodes))
    methods=[]
    for m in config.get('methods',[dict(id=k,sampler=k) for k in ('old_variance','new_variance','new_precision','staircase','ucb_tvcg')]):
        _strict(m,('id','sampler','staircase'),'method')
        name=m.get('sampler'); mid=m.get('id')
        if name not in SAMPLERS or not isinstance(mid,str) or not re.fullmatch('[a-z0-9_]+',mid): raise ValueError('invalid semantic method ID/sampler')
        st=_record(StaircaseSpec,m.get('staircase',asdict(sampler.staircase)))
        if st.start!=sampler.staircase.start: raise ValueError('method staircase start must equal public base start; scenario overrides are explicit')
        if name!='staircase' and ('staircase' in m or mid!=name): raise ValueError('non-staircase ID must equal sampler')
        if name=='staircase' and mid not in ('staircase',staircase_id(st)): raise ValueError('staircase ID must encode initial/floor')
        methods.append(dict(id=mid,sampler=name,**({'staircase':asdict(st)} if name=='staircase' else {})))
    if not methods or len({m['id'] for m in methods})!=len(methods): raise ValueError('empty/duplicate methods')
    scenarios=[]; execution_defs={}; population_defs={}
    default_scenarios=[dict(id=f'{f}_{e}',family=f,execution=e) for f in ('logistic','probit','lapse_logistic') for e in EXECUTIONS]
    for r in config.get('scenarios',default_scenarios):
        _strict(r,('id','family','execution','population','latent_group','staircase_start'),'scenario')
        sid=r.get('id'); family=r.get('family'); ex=r.get('execution'); group=r.get('latent_group','main')
        if not isinstance(sid,str) or not re.fullmatch('[a-z0-9_]+',sid) or family not in ('logistic','probit','lapse_logistic'): raise ValueError('invalid scenario')
        if not isinstance(group,str) or not re.fullmatch('[a-z0-9_]+',group): raise ValueError('invalid latent group')
        if isinstance(ex,str):
            if ex not in EXECUTIONS: raise ValueError('unknown execution condition')
            ex=dict(id=ex,**EXECUTIONS[ex])
        _strict(ex,('id','intercept','gain','sd','lower','upper'),'execution')
        eid=ex.get('id')
        if not isinstance(eid,str) or not re.fullmatch('[a-z0-9_]+',eid): raise ValueError('invalid execution ID')
        truth=_record(ExecutionTruth,{k:v for k,v in ex.items() if k!='id'})
        if (truth.lower,truth.upper)!=(sampler.lower,sampler.upper): raise ValueError('execution domain must match public domain')
        ex=dict(id=eid,**asdict(truth))
        if eid in execution_defs and execution_defs[eid]!=ex: raise ValueError('execution identity has conflicting parameters')
        execution_defs[eid]=ex
        p=_record(PopulationSpec,r.get('population',asdict(pop)))
        if group in population_defs and population_defs[group]!=asdict(p): raise ValueError('paired latent group has conflicting population')
        population_defs[group]=asdict(p)
        start=r.get('staircase_start',sampler.staircase.start)
        if not isinstance(start,(int,float)) or not math.isfinite(start) or not sampler.lower<=start<=sampler.upper: raise ValueError('invalid staircase start')
        scenarios.append(dict(id=sid,family=family,execution=ex,population=asdict(p),latent_group=group,staircase_start=start))
    if not scenarios or len({r['id'] for r in scenarios})!=len(scenarios): raise ValueError('empty/duplicate scenarios')
    readers=dict(factorial=study.split=='development',stop_replay=False,ucb_oracle=True)
    _strict(config.get('readouts',{}),readers,'readouts'); readers.update(config.get('readouts',{}))
    if any(type(v) is not bool for v in readers.values()): raise ValueError('readout switches must be boolean')
    if readers['factorial'] and study.split not in ('development','pilot','numerical'): raise ValueError('factorial is development-only')
    analysis=dict(bootstrap_draws=20000,seed=202611055,confidence=.95,bonferroni_scenarios=6,sensitivity_deltas=[.10,.20])
    _strict(config.get('analysis',{}),analysis,'analysis'); analysis.update(config.get('analysis',{}))
    if (analysis['bootstrap_draws']!=20000 or analysis['confidence']!=.95 or analysis['bonferroni_scenarios']!=6
        or analysis['sensitivity_deltas']!=[.10,.20] or not _integer(analysis['seed'])): raise ValueError('analysis definitions are predeclared and fixed')
    return clean_json(dict(version=2,study=asdict(study),participants=n,population=asdict(pop),sampler=asdict(sampler),
                           methods=methods,scenarios=scenarios,readouts=readers,analysis=analysis))


def source_hashes():
    """Consumed sampling/readout/evaluator code, separate from postprocessing."""
    root=Path(__file__).resolve().parents[1]
    names=[f'finite_budget/{name}.py' for name in ('__init__','contracts','population','samplers',
            'boundary_model','acquisition','readouts','metrics','study')]
    names += ['monotone_bayes.py']+[f'decoupled_calibration/{name}.py' for name in ('__init__','public','execution','passenger','policies')]
    if (root/'__init__.py').exists(): names.append('__init__.py')
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sorted(names)}


def analysis_hashes():
    root=Path(__file__).resolve().parent
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('analysis.py',)}


def _rng(seed,*keys):
    # UTF-8 digest words, not Python hash or list position; reorder-invariant.
    words=np.frombuffer(hashlib.sha256(canonical(keys).encode()).digest(),dtype='<u4').tolist()
    return np.random.default_rng(np.random.SeedSequence([seed,*words]))


def _sampler_config(config,method,scenario):
    s=dict(config['sampler']); s['prior']=PriorSpec(**s['prior']); s['staircase']=StaircaseSpec(**s['staircase'])
    if method['sampler']=='staircase': s['staircase']=StaircaseSpec(**{**method['staircase'],'start':scenario['staircase_start']})
    return SamplerConfig(**s)


def _old_model(s):
    return BoundaryPosterior.from_joint_grid(s.tau,*legacy_joint_grid(s.tau,PriorGrid(midpoint_nodes=s.midpoint_nodes,slope_nodes=s.slope_nodes)))


def readout_keys(config,method):
    keys=[('common','new_precision'),('common','new_median')]
    if method['sampler'] in ('old_variance','new_variance','new_precision','old_precision'):
        keys += [('pipeline',('old_' if method['sampler'].startswith('old_') else 'new_')+'precision')]
        if method['sampler']=='old_variance': keys += [('legacy_native','old_median')]
    elif method['sampler']=='staircase': keys += [('pipeline','firth')]
    if config['readouts']['factorial']:
        keys += [('development_factorial',p+'_'+e) for p in ('old','new') for e in ('median','precision')]
    return keys


def evaluate_prefix(history,config,method,*,models=None):
    """Pure reader API; constructs separate posteriors unless shadows supplied."""
    s=_sampler_config(config,method,config['scenarios'][0])
    if models is None:
        models={'new':BoundaryPosterior(s.tau,s.prior)}
        if any(e.startswith('old_') for _,e in readout_keys(config,method)): models['old']=_old_model(s)
        for o in history:
            for model in models.values(): model.observe(o)
    result={}
    for track,estimator in readout_keys(config,method):
        if estimator=='firth': r=fit_firth(history,s.tau,s.prior)
        else:
            p,decision=estimator.split('_'); model=models[p]
            r=model.precision_readout(s.delta) if decision=='precision' else model.median_readout()
        result[(track,estimator)]=r
    return result


def _freeze_payload(config,selection,diagnostics):
    c=effective_config(config)
    _strict(selection,('selected','candidates','development_manifest_sha256','development_config_sha256','rule','selected_method'),'selection')
    selected=_record(StaircaseSpec,selection.get('selected',{}))
    if not selection.get('candidates') or not selection.get('development_manifest_sha256'): raise ValueError('freeze needs recorded staircase selection provenance')
    for m in c['methods']:
        if m['sampler']=='staircase' and m['staircase']!=asdict(selected): raise ValueError('freeze staircase differs from recorded selection')
    _strict(diagnostics,('accepted','reason','resolution','artifact_sha256','artifact_path','deviations'),'diagnostics decision')
    resolution={k:c['sampler']['prior'][k] for k in ('b_nodes','k_nodes')}
    resolution['quadrature_nodes']=c['sampler']['quadrature_nodes']
    if diagnostics.get('accepted') is not True or not diagnostics.get('reason') or diagnostics.get('resolution')!=resolution:
        raise ValueError('freeze needs accepted numerical decision at effective resolution')
    if diagnostics.get('artifact_path'):
        p=Path(diagnostics['artifact_path'])
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=diagnostics.get('artifact_sha256'): raise ValueError('diagnostic evidence hash mismatch')
    return dict(version=2,effective_config=c,config_sha256=digest(c),source_hashes=source_hashes(),
                analysis_source_hashes=analysis_hashes(),selection=selection,diagnostics=diagnostics)


def freeze_study(config,path,selection,diagnostics):
    p=Path(path)
    if p.exists(): raise FileExistsError(p)
    payload=_freeze_payload(config,selection,diagnostics)
    p.parent.mkdir(parents=True,exist_ok=True); write_json(p,payload)
    return payload


def validate_freeze(config,path):
    frozen=json.loads(Path(path).read_text(encoding='utf-8'))
    expected=_freeze_payload(config,frozen['selection'],frozen['diagnostics'])
    if frozen!=expected: raise ValueError('freeze config/source equality failed before sampling')
    return frozen


def _truth(ex): return ExecutionTruth(**{k:v for k,v in ex.items() if k!='id'})


def oracle_acceptability(passenger,target,truth,nodes=31):
    """Simulation evaluator only; hidden curve and true execution never feed back."""
    belief=ExecutionBelief(**asdict(truth)); x,w=execution_quadrature(target,belief,nodes)
    return float(np.dot(w,[passenger.probability(float(v)) for v in x]))


def oracle_diagnostics():
    """Fixed public synthetic cases, independent of sampled outcome batches."""
    rows=[]
    for family in ('logistic','probit','lapse_logistic'):
        for execution,params in EXECUTIONS.items():
            for B,W,target in ((.5,.35,0.),(1.5,.70,1.5),(2.5,1.4,3.)):
                p=passenger_from_latent(B,W,family)
                a=oracle_acceptability(p,target,ExecutionTruth(**params),31)
                b=oracle_acceptability(p,target,ExecutionTruth(**params),61)
                rows.append(dict(family=family,execution=execution,B=B,W=W,target=target,nodes_31=a,nodes_61=b,abs_difference=abs(a-b)))
    return dict(label='oracle simulation evaluation, deterministic fixed cases; never sampler feedback',cases=rows,
                max_abs_difference=max(r['abs_difference'] for r in rows),nodes=31,reference_nodes=61)


def _initialize_worker(temp_root):
    """Spawn initializer: private process temp and inherited single-thread BLAS."""
    worker_tmp=Path(temp_root)/f'worker-{os.getpid()}'
    worker_tmp.mkdir(parents=True,exist_ok=True)
    for name in ('TMP','TEMP','TMPDIR'): os.environ[name]=str(worker_tmp)
    tempfile.tempdir=str(worker_tmp)
    for name in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'): os.environ[name]='1'


def _simulate_participant(c,pid):
    """One original participant across every scenario/method; no result writes."""
    study=StudySpec(**c['study']); seed=study.seed
    buffers={name:[] for name in REQUIRED_FILES}
    def emit(file,row): buffers[file+'.jsonl'].append(canonical(row)+'\n')
    feedback_count=0; calibration_count=0; latent_cache={}; calibration_cache={}
    for scenario in c['scenarios']:
        group=scenario['latent_group']; pop=PopulationSpec(**scenario['population']); truth=_truth(scenario['execution'])
        latent_id=f'{group}:{pid}'
        if latent_id not in latent_cache:
            latent_cache[latent_id]=draw_latents(1,pop,_rng(seed,'population',group,pid))[0]
        B,W=latent_cache[latent_id]
        calibration_id=f"{latent_id}:{scenario['execution']['id']}"
        if calibration_id not in calibration_cache:
            belief=calibrate_execution(truth,_rng(seed,'calibration',group,pid,scenario['execution']['id']),study.calibration_n)
            calibration_cache[calibration_id]=belief; calibration_count+=study.calibration_n
            emit('calibrations',dict(calibration_id=calibration_id,latent_id=latent_id,participant=pid,execution=scenario['execution'],n=study.calibration_n,belief=asdict(belief)))
        belief=calibration_cache[calibration_id]
        passenger=passenger_from_latent(B,W,scenario['family'],study.tau,pop.lapse)
        emit('participants',dict(scenario=scenario['id'],participant=pid,latent_id=latent_id,calibration_id=calibration_id,
             B=B,W=W,family=passenger.family,k=passenger.slope,lapse=passenger.lapse,local_derivative=local_derivative(passenger)))
        for method in c['methods']:
            mid=method['id']; s=_sampler_config(c,method,scenario)
            rngs={name:_rng(seed,name,scenario['id'],pid,mid) for name in ('execution','feedback','policy')}
            sampler=make_sampler(method['sampler'],s,belief,rngs['policy'])
            shadows={'new':BoundaryPosterior(study.tau,s.prior)}
            if any(e.startswith('old_') for _,e in readout_keys(c,method)): shadows['old']=_old_model(s)
            stopped=None
            for t in range(1,study.max_budget+1):
                target=sampler.suggest(); x=execute(target,truth,rngs['execution']); y=passenger.respond(x,rngs['feedback'])
                o=Observation(t,target,x,y); sampler.observe(o)
                for model in shadows.values(): model.observe(o)
                identity=dict(scenario=scenario['id'],participant=pid,method=mid)
                emit('observations',dict(**identity,**asdict(o))); feedback_count+=1
                if c['readouts']['stop_replay'] and t>=8 and stopped is None:
                    r=shadows['new'].precision_readout(study.delta); a=assess(r,sampler.history,B,study.delta)
                    if a['supported'] and r.posterior_success>=.90 and r.edge_mass<=.01:
                        stopped=dict(**identity,stopped=True,capped_cost=t,correct=a['accurate'],**a)
                if t not in study.checkpoints: continue
                for (track,estimator),r in evaluate_prefix(sampler.history,c,method,models=shadows).items():
                    if track in ('pipeline','legacy_native') and estimator!='firth':
                        r=sampler.median_readout() if estimator.endswith('median') else sampler.precision_readout(study.delta)
                    emit('checkpoints',dict(**identity,budget=t,sampler=method['sampler'],track=track,estimator=estimator,
                                           label=f'{mid} + {track}/{estimator}',**assess(r,sampler.history,B,study.delta)))
                diagnostic=dict(**identity,budget=t,sampler=method['sampler'])
                if method['sampler']=='staircase':
                    emit('diagnostics',dict(**diagnostic,kind='staircase_reversals',**reversal_readout(sampler.history,sampler.reversal_indices)))
                if method['sampler']=='ucb_tvcg':
                    command=sampler.native_command()
                    d=dict(**diagnostic,kind='native_ucb_command_not_B_tau',command=command)
                    if c['readouts']['ucb_oracle']:
                        d.update(oracle_acceptability_31=oracle_acceptability(passenger,command,truth,31),
                                 oracle_acceptability_61=oracle_acceptability(passenger,command,truth,61),
                                 evaluation_label='oracle simulation evaluation; no sampler feedback')
                        d['oracle_quadrature_abs_difference']=abs(d['oracle_acceptability_31']-d['oracle_acceptability_61'])
                    emit('diagnostics',d)
            if c['readouts']['stop_replay']:
                if stopped is None:
                    a=assess(shadows['new'].precision_readout(study.delta),sampler.history,B,study.delta)
                    stopped=dict(scenario=scenario['id'],participant=pid,method=mid,stopped=False,capped_cost=study.max_budget,correct=a['accurate'],**a)
                emit('stops',stopped)
    return dict(files={name:''.join(rows) for name,rows in buffers.items()},
                feedback_count=feedback_count,calibration_count=calibration_count,
                calibration_reuse_groups=len(calibration_cache),latent_draws=len(latent_cache))


def run_study_v2(config,output_dir,*,freeze_path=None,workers=1):
    """Run once, optionally parallel by original participant; parent owns writes.

    workers is execution metadata, excluded from scientific config and RNG keys.
    Windows spawn is explicit. A failed worker never produces a complete manifest.
    """
    started=time.perf_counter()
    if not _integer(workers,1): raise ValueError('workers must be a positive integer')
    c=effective_config(config); frozen=None
    if c['study']['split'] in ('heldout','stress'):
        if freeze_path is None: raise ValueError('heldout/stress requires freeze before sampling')
        frozen=validate_freeze(c,freeze_path)
    out=Path(output_dir)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True); write_json(out/'effective_config.json',c)
    sources=source_hashes(); write_json(out/'source_hashes.json',sources)
    if frozen is not None: write_json(out/'freeze.json',frozen)
    if c['readouts']['ucb_oracle']: write_json(out/'oracle_numerics.json',oracle_diagnostics())
    study=StudySpec(**c['study']); n=c['participants']; effective_workers=min(workers,n)
    handles={name:(out/name).open('w',encoding='utf-8',newline='\n') for name in REQUIRED_FILES}
    totals={key:0 for key in ('feedback_count','calibration_count','calibration_reuse_groups','latent_draws')}
    executor=None; old_threads={}; worker_temp_root=None
    try:
        if effective_workers>1:
            # Set before spawn/import, then restore the parent after pool shutdown.
            for name in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):
                old_threads[name]=os.environ.get(name); os.environ[name]='1'
            temp_root=Path(os.environ.get('TMP',str(out.parent/'tmp'))).resolve()
            temp_root.mkdir(parents=True,exist_ok=True)
            worker_temp_root=tempfile.mkdtemp(prefix='finite-budget-',dir=temp_root)
            executor=ProcessPoolExecutor(max_workers=effective_workers,mp_context=mp.get_context('spawn'),
                                         initializer=_initialize_worker,initargs=(worker_temp_root,))
            results=executor.map(_simulate_participant,repeat(c),range(n))
        else:
            results=(_simulate_participant(c,pid) for pid in range(n))
        # map returns input order: original participant ID, then scenario/method.
        for result in results:
            for name,stream in handles.items(): stream.write(result['files'][name])
            for key in totals: totals[key]+=result[key]
    finally:
        if executor is not None: executor.shutdown(wait=True,cancel_futures=True)
        for name,value in old_threads.items():
            if value is None: os.environ.pop(name,None)
            else: os.environ[name]=value
        for stream in handles.values(): stream.close()
    manifest=dict(version=2,complete=True,config_sha256=digest(c),source_hashes=sources,
                  analysis_source_hashes=analysis_hashes(),**totals,
                  elapsed_seconds=time.perf_counter()-started,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
                  workers=int(workers),workers_effective=int(effective_workers),
                  multiprocessing_start_method='spawn' if effective_workers>1 else None,worker_temp_root=worker_temp_root,
                  expected_feedback_count=n*len(c['scenarios'])*len(c['methods'])*study.max_budget)
    write_json(out/'manifest.json',manifest)
    return manifest


def _index(rows,fields,label):
    result={}
    for r in rows:
        try: key=tuple(r[f] for f in fields)
        except KeyError as exc: raise ValueError(f'missing {label} identity') from exc
        for field in ('participant','trial','budget'):
            if field in fields and not _integer(r[field],0 if field=='participant' else 1): raise ValueError(f'invalid {label} integer identity')
        if key in result: raise ValueError(f'duplicate {label}: {key}')
        result[key]=r
    return result


def _schemas(rows,fields,label):
    required=set(fields)
    for row in rows:
        if not isinstance(row,dict) or set(row)!=required: raise ValueError(f'{label} schema mismatch')


def _validate_readout(row):
    for field in ('boundary','lower','upper','edge_mass','posterior_success'):
        v=row[field]
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)):
            raise ValueError('nonfinite or invalid readout value')
    if row['lower'] is not None and row['upper'] is not None and row['lower']>row['upper']: raise ValueError('reversed interval')
    for field in ('edge_mass','posterior_success'):
        if row[field] is not None and not -1e-12<=row[field]<=1+1e-12: raise ValueError('invalid posterior probability')
    if not isinstance(row['active_bounds'],list) or any(v not in ('b_min','b_max','k_min','k_max') for v in row['active_bounds']): raise ValueError('invalid active bounds')
    for field in ('finite','supported','accurate','supported_success','overestimate','out_of_domain'):
        if type(row[field]) is not bool: raise ValueError('nonboolean outcome flag')


def _equal(a,b):
    if isinstance(a,bool) or isinstance(b,bool): return type(a) is bool and type(b) is bool and a==b
    if isinstance(a,(float,int)) and not isinstance(a,bool) and isinstance(b,(float,int)) and not isinstance(b,bool):
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)
    return clean_json(a)==clean_json(b)


def validate_run(input_dir,*,verify_readouts=False):
    """Validate exact Cartesian grids and recompute outcomes from public prefixes.

    verify_readouts additionally independently rebuilds every posterior/Firth fit;
    routine validation always recomputes errors/support/failure classifications.
    """
    root=Path(input_dir); c=effective_config(root/'effective_config.json')
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    sources=json.loads((root/'source_hashes.json').read_text(encoding='utf-8'))
    if not manifest.get('complete') or manifest.get('config_sha256')!=digest(c) or manifest.get('source_hashes')!=sources:
        raise ValueError('incomplete run or inconsistent config/source manifest')
    if c['study']['split'] in ('heldout','stress'):
        frozen=json.loads((root/'freeze.json').read_text(encoding='utf-8'))
        if frozen.get('effective_config')!=c or frozen.get('source_hashes')!=sources: raise ValueError('recorded freeze mismatch')
    n=c['participants']; horizon=c['study']['max_budget']; cps=c['study']['checkpoints']
    participants=_index(read_jsonl(root/'participants.jsonl'),('scenario','participant'),'participant')
    calibrations=_index(read_jsonl(root/'calibrations.jsonl'),('calibration_id',),'calibration')
    trials=_index(read_jsonl(root/'observations.jsonl'),('scenario','participant','method','trial'),'trial')
    checkpoints=_index(read_jsonl(root/'checkpoints.jsonl'),('scenario','participant','method','budget','track','estimator'),'checkpoint')
    diagnostics=_index(read_jsonl(root/'diagnostics.jsonl'),('scenario','participant','method','budget','kind'),'diagnostic')
    stops=_index(read_jsonl(root/'stops.jsonl'),('scenario','participant','method'),'stop')
    _schemas(participants.values(),('scenario','participant','latent_id','calibration_id','B','W','family','k','lapse','local_derivative'),'participant')
    _schemas(calibrations.values(),('calibration_id','latent_id','participant','execution','n','belief'),'calibration')
    _schemas(trials.values(),('scenario','participant','method','trial','target','realized','acceptable'),'observation')
    outcome_fields=tuple(assess(Readout(None,status='no_data'),[],1.,.15))
    _schemas(checkpoints.values(),('scenario','participant','method','budget','sampler','track','estimator','label',*outcome_fields),'checkpoint')
    _schemas(stops.values(),('scenario','participant','method','stopped','capped_cost','correct',*outcome_fields),'stop')
    for r in [*checkpoints.values(),*stops.values()]: _validate_readout(r)
    ep=set(); ec=set(); et=set(); er=set(); ed=set(); es=set(); latent_values={}; expected_latents=set(); checked_calibrations=set()
    for scenario in c['scenarios']:
        for pid in range(n):
            sid=scenario['id']; ep.add((sid,pid)); latent_id=f"{scenario['latent_group']}:{pid}"; expected_latents.add(latent_id)
            cid=f"{latent_id}:{scenario['execution']['id']}"; ec.add((cid,))
            p=participants.get((sid,pid)); cal=calibrations.get((cid,))
            if p is None or cal is None: raise ValueError('missing participant/calibration, including failures')
            expected_BW=draw_latents(1,PopulationSpec(**scenario['population']),_rng(c['study']['seed'],'population',scenario['latent_group'],pid))[0]
            if not _equal((p.get('B'),p.get('W')),expected_BW): raise ValueError('participant truth differs from semantic population draw')
            if p.get('latent_id')!=latent_id or p.get('calibration_id')!=cid: raise ValueError('participant pairing/reuse mismatch')
            if latent_id in latent_values and latent_values[latent_id]!=(p['B'],p['W']): raise ValueError('paired latents differ')
            latent_values[latent_id]=(p['B'],p['W'])
            passenger=passenger_from_latent(p['B'],p['W'],scenario['family'],c['study']['tau'],scenario['population']['lapse'])
            for field,value in [('family',passenger.family),('k',passenger.slope),('lapse',passenger.lapse),('local_derivative',local_derivative(passenger))]:
                if not _equal(p.get(field),value): raise ValueError('participant response truth mismatch')
            if cal.get('execution')!=scenario['execution'] or cal.get('n')!=c['study']['calibration_n'] or cal.get('latent_id')!=latent_id or cal.get('participant')!=pid: raise ValueError('calibration accounting mismatch')
            ExecutionBelief(**cal['belief'])
            if cid not in checked_calibrations:
                expected_belief=calibrate_execution(_truth(scenario['execution']),_rng(c['study']['seed'],'calibration',scenario['latent_group'],pid,scenario['execution']['id']),c['study']['calibration_n'])
                if cal['belief']!=asdict(expected_belief): raise ValueError('calibration differs from independent semantic draw')
                checked_calibrations.add(cid)
            for method in c['methods']:
                mid=method['id']; history=[]; reversed_trials=[]; s=_sampler_config(c,method,scenario)
                stop_model=BoundaryPosterior(s.tau,s.prior) if c['readouts']['stop_replay'] else None
                expected_stop=None
                ucb=make_sampler('ucb_tvcg',s,ExecutionBelief(**cal['belief']),_rng(c['study']['seed'],'policy',sid,pid,mid)) if method['sampler']=='ucb_tvcg' else None
                for t in range(1,horizon+1):
                    key=(sid,pid,mid,t); et.add(key); row=trials.get(key)
                    if row is None: raise ValueError('incomplete trial sequence')
                    from .contracts import validate_observation
                    o=validate_observation(Observation(t,row['target'],row['realized'],row['acceptable']),history,targets=c['sampler']['targets'])
                    if history and o.acceptable!=history[-1].acceptable: reversed_trials.append(t)
                    history.append(o)
                    if ucb is not None: ucb.observe(o)
                    if stop_model is not None:
                        stop_model.observe(o)
                        if t>=8 and expected_stop is None:
                            sr=stop_model.precision_readout(s.delta); sa=assess(sr,history,p['B'],s.delta)
                            if sa['supported'] and sr.posterior_success>=.90 and sr.edge_mass<=.01:
                                expected_stop=dict(scenario=sid,participant=pid,method=mid,stopped=True,capped_cost=t,correct=sa['accurate'],**sa)
                    if t not in cps: continue
                    expected=evaluate_prefix(history,c,method) if verify_readouts else None
                    for track,estimator in readout_keys(c,method):
                        key=(sid,pid,mid,t,track,estimator); er.add(key); r=checkpoints.get(key)
                        if r is None: raise ValueError('missing checkpoint readout, including failed fits')
                        if r.get('sampler')!=method['sampler'] or r.get('label')!=f'{mid} + {track}/{estimator}': raise ValueError('readout label mismatch')
                        value=Readout(**{k:r[k] for k in Readout.__dataclass_fields__})
                        fresh=assess(value,history,p['B'],c['study']['delta'])
                        if any(not _equal(r.get(k),v) for k,v in fresh.items()): raise ValueError('checkpoint error/support/failure classification mismatch')
                        if expected is not None and any(not _equal(getattr(value,k),getattr(expected[(track,estimator)],k)) for k in Readout.__dataclass_fields__): raise ValueError('independent readout reconstruction mismatch')
                    if method['sampler'] in ('staircase','ucb_tvcg'):
                        kind='staircase_reversals' if method['sampler']=='staircase' else 'native_ucb_command_not_B_tau'
                        dk=(sid,pid,mid,t,kind); ed.add(dk); d=diagnostics.get(dk)
                        if d is None: raise ValueError('missing diagnostic record')
                        fresh=dict(scenario=sid,participant=pid,method=mid,budget=t,sampler=method['sampler'],kind=kind)
                        if method['sampler']=='staircase': fresh.update(reversal_readout(history,reversed_trials))
                        else:
                            command=ucb.native_command(); fresh['command']=command
                            if c['readouts']['ucb_oracle']:
                                fresh.update(oracle_acceptability_31=oracle_acceptability(passenger,command,_truth(scenario['execution']),31),
                                             oracle_acceptability_61=oracle_acceptability(passenger,command,_truth(scenario['execution']),61),
                                             evaluation_label='oracle simulation evaluation; no sampler feedback')
                                fresh['oracle_quadrature_abs_difference']=abs(fresh['oracle_acceptability_31']-fresh['oracle_acceptability_61'])
                        if set(d)!=set(fresh) or any(not _equal(d.get(k),v) for k,v in fresh.items()): raise ValueError('diagnostic schema/value mismatch')
                if c['readouts']['stop_replay']:
                    sk=(sid,pid,mid); es.add(sk)
                    if expected_stop is None:
                        sa=assess(stop_model.precision_readout(s.delta),history,p['B'],s.delta)
                        expected_stop=dict(scenario=sid,participant=pid,method=mid,stopped=False,capped_cost=horizon,correct=sa['accurate'],**sa)
                    actual_stop=stops.get(sk)
                    if actual_stop is None or any(not _equal(actual_stop.get(k),v) for k,v in expected_stop.items()): raise ValueError('stop replay correctness/capped cost mismatch')
    for actual,expected,label in [(set(participants),ep,'participant'),(set(calibrations),ec,'calibration'),(set(trials),et,'trial'),(set(checkpoints),er,'checkpoint'),(set(diagnostics),ed,'diagnostic'),(set(stops),es,'stop')]:
        if actual!=expected: raise ValueError(f'incomplete or extra {label} Cartesian grid')
    if (manifest.get('feedback_count')!=len(et) or manifest.get('expected_feedback_count')!=len(et)
        or manifest.get('calibration_count')!=len(ec)*c['study']['calibration_n']
        or manifest.get('calibration_reuse_groups')!=len(ec) or manifest.get('latent_draws')!=len(expected_latents)):
        raise ValueError('manifest sample/cost counts mismatch')
    return manifest


def replay_subset(input_dir,limit=1):
    """Exactly reproduce a bounded semantic-RNG trajectory subset without writes."""
    root=Path(input_dir); validate_run(root)
    c=effective_config(root/'effective_config.json'); n=c['participants']; seed=c['study']['seed']
    trials=_index(read_jsonl(root/'observations.jsonl'),('scenario','participant','method','trial'),'trial')
    parts=_index(read_jsonl(root/'participants.jsonl'),('scenario','participant'),'participant')
    calibrations=_index(read_jsonl(root/'calibrations.jsonl'),('calibration_id',),'calibration'); matched=0
    if not _integer(limit,1): raise ValueError('positive replay limit required')
    for scenario in c['scenarios']:
        for pid in range(n):
            p=parts[(scenario['id'],pid)]; passenger=passenger_from_latent(p['B'],p['W'],scenario['family'],c['study']['tau'],scenario['population']['lapse'])
            belief=ExecutionBelief(**calibrations[(p['calibration_id'],)]['belief'])
            for method in c['methods']:
                mid=method['id']; rngs={name:_rng(seed,name,scenario['id'],pid,mid) for name in ('execution','feedback','policy')}
                sampler=make_sampler(method['sampler'],_sampler_config(c,method,scenario),belief,rngs['policy'])
                for t in range(1,c['study']['max_budget']+1):
                    target=sampler.suggest(); x=execute(target,_truth(scenario['execution']),rngs['execution']); y=passenger.respond(x,rngs['feedback'])
                    o=Observation(t,target,x,y); sampler.observe(o); row=trials[(scenario['id'],pid,mid,t)]
                    if any(row[k]!=v for k,v in asdict(o).items()): raise ValueError('exact subset replay mismatch')
                matched+=1
                if matched>=limit: return dict(matched=matched,exact=True)
    return dict(matched=matched,exact=True)


def select_staircase(input_dir,output_path=None):
    root=Path(input_dir); validate_run(root)
    c=effective_config(root/'effective_config.json')
    if c['study']['split'] not in ('development','pilot'): raise ValueError('selection requires development data')
    methods=[m for m in c['methods'] if m['sampler']=='staircase']; rows=read_jsonl(root/'checkpoints.jsonl'); results=[]
    expected={(i,f) for i in (.3,.6,.9) for f in (.10,.15)}
    if {(m['staircase']['initial'],m['staircase']['floor']) for m in methods}!=expected: raise ValueError('selection requires all six predeclared candidates')
    for m in methods:
        scenario_metrics=[]
        for scenario in c['scenarios']:
            cohort=[r for r in rows if r['scenario']==scenario['id'] and r['method']==m['id'] and r['track']=='pipeline' and r['estimator']=='firth' and r['budget']==c['study']['primary_budget']]
            scenario_metrics.append(dict(scenario=scenario['id'],supported_success_rate=sum(r['supported_success'] for r in cohort)/len(cohort),
                                         capped_mae=sum(min(r['abs_error'],3.) if r['finite'] else 3. for r in cohort)/len(cohort)))
        results.append(dict(method=m['id'],staircase=m['staircase'],scenarios=scenario_metrics,
                            supported_success_rate=float(np.mean([r['supported_success_rate'] for r in scenario_metrics])),
                            capped_mae=float(np.mean([r['capped_mae'] for r in scenario_metrics]))))
    results.sort(key=lambda r:(-r['supported_success_rate'],r['capped_mae'],r['staircase']['initial'],r['staircase']['floor']))
    selection=dict(selected=results[0]['staircase'],selected_method=results[0]['method'],candidates=results,
                   development_manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
                   development_config_sha256=digest(c),rule='A/Firth primary-budget scenario-equal supported success, capped MAE, smaller initial, smaller floor')
    if output_path:
        if Path(output_path).exists(): raise FileExistsError(output_path)
        write_json(output_path,selection)
    return selection


def reread_prior_histories(input_dir,output_path):
    """Development-only weak/shifted-prior readout sensitivity; no simulation."""
    root=Path(input_dir); validate_run(root); c=effective_config(root/'effective_config.json')
    if c['study']['split'] not in ('development','pilot'): raise ValueError('prior diagnostics are development-only')
    output=Path(output_path)
    if output.exists(): raise FileExistsError(output)
    observations=read_jsonl(root/'observations.jsonl'); grouped={}
    for r in observations: grouped.setdefault((r['scenario'],r['participant'],r['method']),[]).append(r)
    count=0
    with output.open('w',encoding='utf-8') as f:
        for identity,rows in grouped.items():
            for name,overrides in [('weak_uniform',dict(kind='uniform')),('center_075',dict(center=.75)),('center_225',dict(center=2.25))]:
                prior=PriorSpec(**{**c['sampler']['prior'],**overrides}); model=BoundaryPosterior(c['study']['tau'],prior)
                for r in sorted(rows,key=lambda r:r['trial']):
                    model.observe(Observation(**{k:r[k] for k in ('trial','target','realized','acceptable')}))
                    if r['trial'] not in c['study']['checkpoints']: continue
                    for decision,value in [('precision',model.precision_readout(c['study']['delta'])),('median',model.median_readout())]:
                        f.write(canonical(dict(scenario=identity[0],participant=identity[1],method=identity[2],budget=r['trial'],prior=name,
                                               decision=decision,track='development_readout_sensitivity_only',**asdict(value)))+'\n'); count+=1
    return dict(rows=count,new_feedback=0)
