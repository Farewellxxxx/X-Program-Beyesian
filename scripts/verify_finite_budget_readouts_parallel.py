"""Reconstruct EVERY saved checkpoint reader using the frozen evaluate_prefix.

This external audit does not change or replace any estimator. It reuses the
scientific reader and compares every Readout field at the package tolerance.
Only the parent writes the final audit, after the complete verification passes.
"""
from dataclasses import asdict
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import sys
import tempfile

# Direct `python scripts/...py` and Windows spawn both resolve the repository.
REPO_ROOT=Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path: sys.path.insert(0,str(REPO_ROOT))


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)


def _digest_lines(lines):
    return hashlib.sha256(''.join(line+'\n' for line in sorted(lines)).encode('utf-8')).hexdigest()


def _initialize_worker(temp_root):
    process_tmp=Path(temp_root)/f'worker-{os.getpid()}'
    process_tmp.mkdir(parents=True,exist_ok=True)
    for name in ('TMP','TEMP','TMPDIR'): os.environ[name]=str(process_tmp)
    tempfile.tempdir=str(process_tmp)
    for name in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'): os.environ[name]='1'


def _verify_participant(task):
    # Imports follow the child initializer; no new science or optimizer options.
    from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import Readout
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation
    from comfort_boundary_bo_research_package.simulation.finite_budget.study import evaluate_prefix, _equal
    c,pid,observations,checkpoints=task
    histories=defaultdict(list)
    for row in observations: histories[(row['scenario'],row['method'])].append(row)
    recorded={}
    for row in checkpoints:
        key=(row['scenario'],row['method'],row['budget'],row['track'],row['estimator'])
        if key in recorded: raise ValueError('duplicate checkpoint in participant audit')
        recorded[key]=row
    checked=set(); identities=[]; reconstructed=[]; types=Counter(); checkpoint_ids=set()
    for scenario in c['scenarios']:
        for method in c['methods']:
            history=[]
            for row in sorted(histories[(scenario['id'],method['id'])],key=lambda r:r['trial']):
                history.append(Observation(**{field:row[field] for field in ('trial','target','realized','acceptable')}))
                budget=row['trial']
                if budget not in c['study']['checkpoints']: continue
                # Full prefix is the only data supplied to the scientific reader.
                expected=evaluate_prefix(tuple(history),c,method)
                checkpoint_ids.add((scenario['id'],method['id'],budget))
                for (track,estimator),readout in expected.items():
                    key=(scenario['id'],method['id'],budget,track,estimator)
                    saved=recorded.get(key)
                    if saved is None: raise ValueError(f'missing reader in participant audit: {pid}/{key}')
                    for field in Readout.__dataclass_fields__:
                        if not _equal(saved[field],getattr(readout,field)):
                            raise ValueError(f'readout reconstruction mismatch: participant={pid}, key={key}, field={field}')
                    identity=[scenario['id'],pid,method['id'],budget,track,estimator]
                    identities.append(_canonical(identity))
                    reconstructed.append(_canonical(dict(identity=identity,readout=asdict(readout))))
                    checked.add(key); types[f'{track}/{estimator}']+=1
    if checked!=set(recorded): raise ValueError('incomplete participant reader coverage')
    return dict(participant=pid,trials=len(observations),checkpoints=len(checkpoint_ids),readouts=len(checked),
                identities=identities,reconstructed=reconstructed,by_track_estimator=dict(types))


def verify_readouts_parallel(input_dir,output_path,*,workers=6):
    """Full data gate, frozen-source equality, then every reader; never a subset."""
    if isinstance(workers,bool) or not isinstance(workers,int) or workers<1:
        raise ValueError('workers must be a positive integer')
    root=Path(input_dir).resolve(); output=Path(output_path)
    if output.exists(): raise FileExistsError(output)
    thread_names=('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS')
    old_threads={name:os.environ.get(name) for name in thread_names}
    for name in thread_names: os.environ[name]='1'
    executor=None
    try:
        import numpy as np
        import scipy
        from comfort_boundary_bo_research_package.simulation.finite_budget.study import (
            effective_config,validate_run,source_hashes,read_jsonl)
        snapshot=json.loads((root/'source_hashes.json').read_text(encoding='utf-8'))
        if source_hashes()!=snapshot: raise ValueError('scientific source differs from saved run snapshot')
        # Mandatory full Cartesian/schema/error/support/cost/stop/diagnostic gate.
        run_manifest=validate_run(root)
        c=effective_config(root/'effective_config.json'); n=c['participants']; used=min(workers,n)
        observations=defaultdict(list); checkpoints=defaultdict(list)
        for row in read_jsonl(root/'observations.jsonl'): observations[row['participant']].append(row)
        for row in read_jsonl(root/'checkpoints.jsonl'): checkpoints[row['participant']].append(row)
        expected_rows=sum(len(rows) for rows in checkpoints.values())
        tasks=((c,pid,observations[pid],checkpoints[pid]) for pid in range(n))
        if used>1:
            temp_root=Path(os.environ.get('TMP',str(REPO_ROOT/'tmp'/'finite-budget-verifier'))).resolve()
            temp_root.mkdir(parents=True,exist_ok=True)
            private_root=tempfile.mkdtemp(prefix='verify-readouts-',dir=temp_root)
            executor=ProcessPoolExecutor(max_workers=used,mp_context=mp.get_context('spawn'),
                                         initializer=_initialize_worker,initargs=(private_root,))
            results=executor.map(_verify_participant,tasks)
        else: results=map(_verify_participant,tasks)
        per_participant=[]; identities=[]; reconstructed=[]; types=Counter()
        for result in results:  # map preserves original participant ID order.
            identities.extend(result.pop('identities')); reconstructed.extend(result.pop('reconstructed'))
            types.update(result.pop('by_track_estimator')); per_participant.append(result)
        checked=sum(row['readouts'] for row in per_participant)
        if checked!=expected_rows: raise ValueError('incomplete overall readout coverage')
        from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import Readout
        artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir())
                   if p.is_file() and p.suffix in ('.json','.jsonl')}
        summary=dict(version=1,status='passed',input_dir=str(root),workers=workers,workers_effective=used,
                     multiprocessing_start_method='spawn' if used>1 else None,
                     full_validation_gate=True,scientific_source_match=True,scientific_source_hashes=snapshot,
                     verifier_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     input_artifact_sha256=artifacts,config_sha256=run_manifest['config_sha256'],
                     checked_participants=n,checked_trials=sum(row['trials'] for row in per_participant),
                     checked_checkpoints=sum(row['checkpoints'] for row in per_participant),
                     checked_readouts=checked,checked_fields=checked*len(Readout.__dataclass_fields__),
                     readout_fields=list(Readout.__dataclass_fields__),comparison_rtol=1e-10,comparison_atol=1e-10,
                     by_track_estimator=dict(sorted(types.items())),per_participant=per_participant,
                     readout_identity_sha256=_digest_lines(identities),reconstructed_fields_sha256=_digest_lines(reconstructed),
                     reuse_label='Reuses scientific evaluate_prefix; complete numerical reconstruction, not an independent new estimator',
                     python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)
        summary['audit_payload_sha256']=hashlib.sha256(_canonical(summary).encode('utf-8')).hexdigest()
        output.parent.mkdir(parents=True,exist_ok=True)
        # Exclusive creation also prevents a concurrent caller overwriting it.
        with output.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        return summary
    finally:
        if executor is not None: executor.shutdown(wait=True,cancel_futures=True)
        for name,value in old_threads.items():
            if value is None: os.environ.pop(name,None)
            else: os.environ[name]=value


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True); parser.add_argument('--output',required=True)
    parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args(argv)
    summary=verify_readouts_parallel(args.input,args.output,workers=args.workers)
    print(_canonical(dict(status=summary['status'],checked_readouts=summary['checked_readouts'],
                          checked_fields=summary['checked_fields'],workers_effective=summary['workers_effective'],
                          output=str(Path(args.output).resolve()),output_sha256=hashlib.sha256(Path(args.output).read_bytes()).hexdigest())))
    return 0


if __name__=='__main__': raise SystemExit(main())
