import copy
import json
from pathlib import Path
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.study import (
    effective_config, run_study_v2, validate_run, freeze_study, read_jsonl,
    replay_subset, select_staircase, source_hashes)


def tiny_config():
    return dict(version=2, participants=2,
        study=dict(split='pilot', seed=81234, primary_budget=2, max_budget=3,
                   checkpoints=[2,3], calibration_n=3),
        sampler=dict(prior=dict(b_nodes=13,k_nodes=5),midpoint_nodes=5,slope_nodes=3,
                     quadrature_nodes=1,targets=[0.,1.5,3.]),
        methods=[dict(id='new_precision',sampler='new_precision'),
                 dict(id='staircase',sampler='staircase')],
        scenarios=[dict(id='logistic_precise',family='logistic',execution='precise'),
                   dict(id='probit_precise',family='probit',execution='precise')])


def test_strict_config_and_consumed_defaults():
    c=effective_config(tiny_config())
    assert c['sampler']['delta']==c['study']['delta']==.15
    assert c['sampler']['prior']['b_nodes']==13
    for path in [('bogus',),('sampler','bogus'),('sampler','prior','bogus'),
                 ('readouts','bogus'),('analysis','bogus')]:
        bad=copy.deepcopy(c); p=bad
        for k in path[:-1]: p=p[k]
        p[path[-1]]=1
        with pytest.raises((TypeError,ValueError)): effective_config(bad)
    bad=copy.deepcopy(c); bad['sampler']['delta']=.2
    with pytest.raises(ValueError): effective_config(bad)


def test_trajectory_order_reader_invariance_pairing_and_complete_rows(tmp_path):
    c=tiny_config(); run_study_v2(c,tmp_path/'a')
    b=copy.deepcopy(c); b['methods'].reverse(); b['readouts']={'factorial':True}
    run_study_v2(b,tmp_path/'b')
    key=lambda r:(r['scenario'],r['participant'],r['method'],r.get('trial',0))
    assert sorted(read_jsonl(tmp_path/'a/observations.jsonl'),key=key)==sorted(read_jsonl(tmp_path/'b/observations.jsonl'),key=key)
    p=read_jsonl(tmp_path/'a/participants.jsonl')
    paired=[r for r in p if r['participant']==0]
    assert paired[0]['B']==paired[1]['B'] and paired[0]['W']==paired[1]['W']
    assert paired[0]['calibration_id']==paired[1]['calibration_id']
    manifest=validate_run(tmp_path/'a')
    assert manifest['feedback_count']==24
    assert manifest['calibration_count']==6
    assert replay_subset(tmp_path/'a',limit=1)['matched']==1
    with pytest.raises(FileExistsError): run_study_v2(c,tmp_path/'a')


def test_validation_rejects_missing_failure_and_corrupted_flags(tmp_path):
    run_study_v2(tiny_config(),tmp_path/'r')
    p=tmp_path/'r/checkpoints.jsonl'; rows=read_jsonl(p)
    original=p.read_text()
    p.write_text('\n'.join(json.dumps(r) for r in rows[:-1])+'\n')
    with pytest.raises(ValueError): validate_run(tmp_path/'r')
    p.write_text(original)
    rows[0]['supported_success']=not rows[0]['supported_success']
    p.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    with pytest.raises(ValueError): validate_run(tmp_path/'r')


def test_freeze_refuses_tampering_before_latents(tmp_path,monkeypatch):
    import comfort_boundary_bo_research_package.simulation.finite_budget.study as s
    c=tiny_config(); c['study']['split']='heldout'
    # Tiny heldout fixture deliberately exercises freeze, without sampling.
    selection={'selected':dict(initial=.6,floor=.15,start=1.5,reversals_per_halving=2),
               'candidates':[{'method':'staircase','supported_success_rate':0.}],
               'development_manifest_sha256':'abc'}
    diagnostics={'accepted':True,'reason':'tiny fixture',
                 'resolution':dict(b_nodes=13,k_nodes=5,quadrature_nodes=1)}
    freeze_study(c,tmp_path/'freeze.json',selection,diagnostics)
    c['study']['seed']+=1
    monkeypatch.setattr(s,'draw_latents',lambda *a: pytest.fail('latent drawn before freeze validation'))
    with pytest.raises(ValueError,match='freeze'): run_study_v2(c,tmp_path/'r',freeze_path=tmp_path/'freeze.json')
    c['study']['seed']-=1
    monkeypatch.setattr(s,'source_hashes',lambda:{'tampered':'sha'})
    with pytest.raises(ValueError,match='freeze'): run_study_v2(c,tmp_path/'r2',freeze_path=tmp_path/'freeze.json')


def test_prefix_readouts_and_failures_are_retained(tmp_path):
    c=tiny_config(); c['participants']=1; c['study'].update(primary_budget=1,max_budget=1,checkpoints=[1])
    c['methods']=[dict(id='staircase',sampler='staircase')]
    run_study_v2(c,tmp_path/'r')
    rows=read_jsonl(tmp_path/'r/checkpoints.jsonl')
    firth=[r for r in rows if r['estimator']=='firth']
    assert len(firth)==2 and all(r['status']=='rank_deficient' and not r['supported_success'] for r in firth)
    validate_run(tmp_path/'r',verify_readouts=True)


def test_no_ignored_method_start_and_strict_row_schemas(tmp_path):
    c=tiny_config(); c['methods'][1]['staircase']={'start':.3}
    with pytest.raises(ValueError,match='start'): effective_config(c)
    run_study_v2(tiny_config(),tmp_path/'r')
    p=tmp_path/'r/observations.jsonl'; rows=read_jsonl(p); rows[0]['truth_leak']=1
    p.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    with pytest.raises(ValueError,match='schema'): validate_run(tmp_path/'r')


def test_prefix_cannot_see_future_and_configuration_snapshots(tmp_path):
    c=tiny_config(); c['participants']=1
    run_study_v2(c,tmp_path/'long')
    c['study'].update(max_budget=2,checkpoints=[2])
    run_study_v2(c,tmp_path/'short')
    long=[r for r in read_jsonl(tmp_path/'long/checkpoints.jsonl') if r['budget']==2]
    assert long==read_jsonl(tmp_path/'short/checkpoints.jsonl')
    for name,count,calibrations in [('development',57600,32*2*90),('heldout',230400,128*2*90),('stress',80640,64*7*90)]:
        full=effective_config(Path('configs')/f'finite_budget_{name}.json')
        assert effective_config(full)==full
        assert full['participants']*len(full['scenarios'])*len(full['methods'])*full['study']['max_budget']==count
        assert full['sampler']['prior']['b_nodes']==241
        if name=='stress':
            lapse=next(r for r in full['scenarios'] if r['id']=='lapse_020')
            assert lapse['family']=='lapse_logistic' and lapse['population']['lapse']==.20
    hashes=source_hashes()
    assert 'finite_budget/study.py' in hashes and 'finite_budget/metrics.py' in hashes
    assert 'finite_budget/analysis.py' not in hashes
    assert 'finite_budget/numerical_diagnostics.py' not in hashes
    assert all(len(v)==64 for v in hashes.values())


def test_all_native_shadow_readers_diagnostics_and_capped_stops(tmp_path):
    c=tiny_config(); c['participants']=1; c['scenarios']=c['scenarios'][:1]
    c['methods']=[dict(id=k,sampler=k) for k in ('old_variance','old_precision','new_variance','new_precision','staircase','ucb_tvcg')]
    c['readouts']={'factorial':True,'stop_replay':True,'ucb_oracle':True}
    run_study_v2(c,tmp_path/'r')
    validate_run(tmp_path/'r',verify_readouts=True)
    stops=read_jsonl(tmp_path/'r/stops.jsonl')
    assert len(stops)==6 and all(not r['stopped'] and r['capped_cost']==3 for r in stops)
    diagnostic=read_jsonl(tmp_path/'r/diagnostics.jsonl')
    assert len(diagnostic)==4
    assert all('command' in r and 'oracle_acceptability_61' in r for r in diagnostic if r['sampler']=='ucb_tvcg')
    p=tmp_path/'r/stops.jsonl'; stops[0]['capped_cost']=2
    p.write_text('\n'.join(json.dumps(r) for r in stops)+'\n')
    with pytest.raises(ValueError,match='stop'): validate_run(tmp_path/'r')


def test_cli_compatibility_full_grid_tiny_roundtrip(tmp_path,capsys):
    from comfort_boundary_bo_research_package.simulation.finite_budget.__main__ import main
    c=tiny_config(); c['participants']=1; c['scenarios']=c['scenarios'][:1]
    c['sampler']['prior']={}; c['methods']=[dict(id='staircase',sampler='staircase')]
    c['study'].update(primary_budget=1,max_budget=1,checkpoints=[1])
    config=tmp_path/'config.json'; config.write_text(json.dumps(c))
    assert main(['--config',str(config),'--output',str(tmp_path/'r'),'--workers','6'])==0
    manifest=json.loads((tmp_path/'r/manifest.json').read_text())
    assert manifest['workers']==6 and manifest['workers_effective']==1
    assert main(['validate','--input',str(tmp_path/'r'),'--verify-readouts'])==0
    assert main(['replay','--input',str(tmp_path/'r'),'--limit','1'])==0
    assert main(['analyze','--input',str(tmp_path/'r'),'--output',str(tmp_path/'a')])==0
    assert len(list((tmp_path/'a').glob('*.png')))==2
    assert '"feedback_count":1' in capsys.readouterr().out


def test_positive_stop_at_earliest_eight_preserves_full_trajectory(tmp_path):
    c=tiny_config(); c['participants']=1; c['scenarios']=c['scenarios'][:1]
    c['methods']=[dict(id='staircase',sampler='staircase')]
    c['sampler'].pop('targets'); c['sampler']['prior'].update(b_min=1.4,b_max=1.6,center=1.5,sd=.01)
    c['population']={'boundary_low':1.49,'boundary_high':1.51}
    c['study'].update(primary_budget=8,max_budget=10,checkpoints=[8,10])
    c['readouts']={'stop_replay':True}
    run_study_v2(c,tmp_path/'r'); validate_run(tmp_path/'r')
    stop=read_jsonl(tmp_path/'r/stops.jsonl')[0]
    assert stop['stopped'] and stop['capped_cost']==8 and stop['correct']
    assert len(read_jsonl(tmp_path/'r/observations.jsonl'))==10


@pytest.mark.parametrize('seed',[81234,202611054])
def test_spawn_parallel_matches_serial_original_ids_all_outputs(tmp_path,seed):
    c=tiny_config(); c['study']['seed']=seed; c['participants']=3
    c['methods']=[dict(id=k,sampler=k) for k in ('old_variance','old_precision','new_variance','new_precision','staircase','ucb_tvcg')]
    c['readouts']={'factorial':True,'stop_replay':True,'ucb_oracle':True}
    serial=run_study_v2(c,tmp_path/'serial',workers=1)
    parallel=run_study_v2(c,tmp_path/'parallel',workers=2)
    for name in ('participants','calibrations','observations','checkpoints','diagnostics','stops'):
        assert (tmp_path/f'serial/{name}.jsonl').read_bytes()==(tmp_path/f'parallel/{name}.jsonl').read_bytes()
    assert parallel['workers']==2 and parallel['workers_effective']==2 and parallel['multiprocessing_start_method']=='spawn'
    assert serial['config_sha256']==parallel['config_sha256']
    assert serial['feedback_count']==parallel['feedback_count']==108
    assert serial['calibration_count']==parallel['calibration_count']==9
    assert {r['participant'] for r in read_jsonl(tmp_path/'parallel/participants.jsonl')}=={0,1,2}
    worker_dirs=list(Path(parallel['worker_temp_root']).glob('worker-*'))
    assert len(worker_dirs)==2 and len({p.name for p in worker_dirs})==2
    validate_run(tmp_path/'parallel',verify_readouts=True)
    assert replay_subset(tmp_path/'parallel',limit=1)['exact']


def fail_participant_fixture(config,pid):
    raise RuntimeError('fixture participant error')


def test_parallel_worker_failure_never_writes_complete_manifest(tmp_path,monkeypatch):
    import comfort_boundary_bo_research_package.simulation.finite_budget.study as s
    monkeypatch.setattr(s,'_simulate_participant',fail_participant_fixture)
    with pytest.raises(RuntimeError,match='fixture participant error'):
        run_study_v2(tiny_config(),tmp_path/'failed',workers=2)
    assert not (tmp_path/'failed/manifest.json').exists()


@pytest.mark.parametrize('workers',[0,-1,True,1.5,'2'])
def test_runtime_workers_strictly_positive_integer(tmp_path,workers):
    with pytest.raises(ValueError,match='workers'): run_study_v2(tiny_config(),tmp_path/'r',workers=workers)
    assert not (tmp_path/'r').exists()
