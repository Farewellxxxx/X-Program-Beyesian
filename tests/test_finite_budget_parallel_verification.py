import json
import hashlib
import subprocess
import sys
from pathlib import Path
import pytest
from scripts.verify_finite_budget_readouts_parallel import verify_readouts_parallel
from comfort_boundary_bo_research_package.simulation.finite_budget.study import (
    run_study_v2,validate_run,read_jsonl,write_json,source_hashes)
from test_finite_budget_study import tiny_config


def all_reader_config():
    c=tiny_config()
    c['methods']=[dict(id=k,sampler=k) for k in ('old_variance','old_precision','new_variance','new_precision','staircase','ucb_tvcg')]
    c['readouts']={'factorial':True,'stop_replay':True,'ucb_oracle':True}
    return c


def test_external_spawn_audit_matches_complete_serial_reader_set(tmp_path):
    run_study_v2(all_reader_config(),tmp_path/'run')
    validate_run(tmp_path/'run',verify_readouts=True)
    serial=verify_readouts_parallel(tmp_path/'run',tmp_path/'serial.json',workers=1)
    parallel=verify_readouts_parallel(tmp_path/'run',tmp_path/'parallel.json',workers=2)
    expected=read_jsonl(tmp_path/'run/checkpoints.jsonl')
    assert serial['checked_readouts']==parallel['checked_readouts']==len(expected)
    assert serial['readout_identity_sha256']==parallel['readout_identity_sha256']
    assert serial['reconstructed_fields_sha256']==parallel['reconstructed_fields_sha256']
    assert parallel['checked_fields']==len(expected)*7
    assert parallel['workers']==parallel['workers_effective']==2
    assert parallel['multiprocessing_start_method']=='spawn'
    assert parallel['by_track_estimator']==serial['by_track_estimator']
    assert parallel['scientific_source_match'] and parallel['full_validation_gate']
    assert parallel['reuse_label'].startswith('Reuses scientific evaluate_prefix')
    assert len(parallel['input_artifact_sha256']['observations.jsonl'])==64
    assert [r['participant'] for r in parallel['per_participant']]==[0,1]
    with pytest.raises(FileExistsError): verify_readouts_parallel(tmp_path/'run',tmp_path/'parallel.json',workers=2)


@pytest.mark.parametrize('field',['boundary','lower'])
def test_audit_rejects_readout_tampering_even_when_derived_outcomes_match(tmp_path,field):
    run_study_v2(all_reader_config(),tmp_path/'run')
    p=tmp_path/'run/checkpoints.jsonl'; rows=read_jsonl(p)
    row=next(r for r in rows if r['estimator']=='new_precision' and r['track']=='common')
    if field=='lower': row['lower']-=.1  # Keeps every error/support/accuracy flag valid.
    else:
        from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import Readout,Observation
        from comfort_boundary_bo_research_package.simulation.finite_budget.metrics import assess
        history=[Observation(**{k:r[k] for k in ('trial','target','realized','acceptable')})
                 for r in read_jsonl(tmp_path/'run/observations.jsonl')
                 if all(r[k]==row[k] for k in ('scenario','participant','method')) and r['trial']<=row['budget']]
        truth=next(r['B'] for r in read_jsonl(tmp_path/'run/participants.jsonl')
                   if r['scenario']==row['scenario'] and r['participant']==row['participant'])
        values={k:row[k] for k in Readout.__dataclass_fields__}; values['boundary']+=.001
        row.update(assess(Readout(**values),history,truth,.15))
    p.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    validate_run(tmp_path/'run')
    with pytest.raises(ValueError,match='reconstruction mismatch'):
        verify_readouts_parallel(tmp_path/'run',tmp_path/'audit.json',workers=2)
    assert not (tmp_path/'audit.json').exists()


def test_audit_completeness_and_source_snapshot_gates(tmp_path):
    run_study_v2(all_reader_config(),tmp_path/'run')
    p=tmp_path/'run/source_hashes.json'; source=json.loads(p.read_text())
    source['finite_budget/readouts.py']='0'*64; write_json(p,source)
    with pytest.raises(ValueError,match='scientific source'):
        verify_readouts_parallel(tmp_path/'run',tmp_path/'audit.json',workers=2)
    assert not (tmp_path/'audit.json').exists()


def test_audit_mandatory_full_gate_rejects_missing_readout(tmp_path):
    run_study_v2(tiny_config(),tmp_path/'run')
    p=tmp_path/'run/checkpoints.jsonl'; rows=read_jsonl(p)
    p.write_text('\n'.join(json.dumps(r) for r in rows[:-1])+'\n')
    with pytest.raises(ValueError,match='missing checkpoint'):
        verify_readouts_parallel(tmp_path/'run',tmp_path/'audit.json',workers=2)
    assert not (tmp_path/'audit.json').exists()


def test_direct_script_spawn_cli_preserves_all_inputs(tmp_path):
    c=tiny_config(); c['scenarios']=c['scenarios'][:1]
    run_study_v2(c,tmp_path/'run')
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'run').iterdir()}
    science=source_hashes()
    script=Path(__file__).resolve().parents[1]/'scripts/verify_finite_budget_readouts_parallel.py'
    result=subprocess.run([sys.executable,str(script),'--input',str(tmp_path/'run'),'--output',str(tmp_path/'audit.json'),'--workers','2'],
                          cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    stdout=json.loads(result.stdout)
    assert stdout['status']=='passed' and stdout['checked_readouts']==24
    assert stdout['output_sha256']==hashlib.sha256((tmp_path/'audit.json').read_bytes()).hexdigest()
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (tmp_path/'run').iterdir()}
    assert source_hashes()==science


@pytest.mark.parametrize('workers',[0,True,1.5])
def test_audit_workers_are_runtime_positive_integers(tmp_path,workers):
    with pytest.raises(ValueError,match='workers'):
        verify_readouts_parallel(tmp_path/'missing',tmp_path/'audit.json',workers=workers)
    assert not (tmp_path/'audit.json').exists()
