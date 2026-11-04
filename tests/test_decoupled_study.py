import csv
import json
import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.decoupled_calibration import study
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.public import Observation, Estimate, PolicyConfig, ExecutionBelief

def small_config():
    return dict(seed=33, split='test', families=['logistic'], execution_conditions={'precise':dict(intercept=0,gain=1,sd=.03)}, methods=['staircase','bayes_point'], participants_per_cell=1,budget=12,checkpoints=[10,12],tau=.7,delta=.15,policy={'midpoint_nodes':11,'slope_nodes':7})

def test_event_logic_suffix_and_lucky_hits():
    # Successful suffix must contain five estimates and begin no earlier than 10.
    e=[1]*9+[0]*5+[1]+[0]*5
    assert study.accuracy_events(e,.15)==(16,14)
    assert study.accuracy_events([0]*12,.15)==(None,10)
    assert study.accuracy_events([0]*15,.15)==(10,10)
    assert study.accuracy_events([0]*14+[1],.15)==(None,10)

def test_reproducibility_method_order_and_outputs(tmp_path):
    cfg=small_config(); a=tmp_path/'a'; b=tmp_path/'b'
    study.run_study(cfg,a)
    cfg['methods'].reverse(); study.run_study(cfg,b)
    def rows(path):
        with (path/'trials.csv').open() as f:
            return sorted(list(csv.DictReader(f)),key=lambda r:(r['method'],int(r['trial'])))
    assert rows(a)==rows(b)
    cfg['methods'].reverse(); c=tmp_path/'c'; study.run_study(cfg,c)
    assert (a/'trials.csv').read_bytes()==(c/'trials.csv').read_bytes()
    for file in ['config.json','config.sha256','effective_parameters.json','trials.csv','participants.csv','truth.json','summary.json']:
        assert (a/file).is_file()
    effective=json.loads((a/'effective_parameters.json').read_text())
    assert effective['prior_grid']['midpoint_mean']==1.2
    assert effective['prior_grid']['midpoint_nodes']==11
    assert len(effective['source_sha256']['policies.py'])==64
    assert '__main__.py' in effective['source_sha256']
    assert 'monotone_bayes.py' in effective['source_sha256']
    summary=json.loads((a/'summary.json').read_text())
    assert summary['calibration_measurements_per_participant_condition']==90
    assert summary['total_calibration_measurements']==90
    with pytest.raises(FileExistsError): study.run_study(cfg,a)

def test_truth_firewall_with_spy_policy(tmp_path,monkeypatch):
    seen=[]
    class Spy:
        def suggest(self): return 1.5
        def observe(self,o):
            assert type(o) is Observation
            assert set(vars(o))=={'trial','target','realized','acceptable'}
            seen.append(o)
        def estimate(self): return Estimate(1.2,.5,2.,'within_domain',0.)
    def factory(name,cfg,belief,rng):
        assert type(cfg) is PolicyConfig and type(belief) is ExecutionBelief
        assert isinstance(rng,np.random.Generator)
        return Spy()
    monkeypatch.setattr(study,'make_policy',factory)
    cfg=small_config(); study.run_study(cfg,tmp_path/'spy')
    assert len(seen)==24

def test_out_of_domain_truth_is_retained(tmp_path):
    cfg=small_config(); cfg['boundary_override']=-.2
    study.run_study(cfg,tmp_path/'stress')
    with (tmp_path/'stress'/'participants.csv').open() as f: rows=list(csv.DictReader(f))
    assert all(r['boundary']=='-0.2' and r['out_of_domain']=='True' for r in rows)



