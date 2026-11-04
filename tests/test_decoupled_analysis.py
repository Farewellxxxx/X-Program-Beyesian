import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.decoupled_calibration.analysis import paired_bootstrap, summarize_participants, analyze

def row(participant,method,cost,observed,error):
    return dict(scenario='logistic__precise',family='logistic',execution='precise',participant=participant,
        method=method,budget=60,primary_cost=cost,primary_observed=observed,
        secondary_cost=cost,secondary_observed=observed,final_absolute_error=error,final_signed_error=error,
        unacceptable_count=10,unacceptable_rate=1/6,interval_coverage=True,interval_width=.5,
        overestimated=False,out_of_domain=False,unidentifiable=False)

def test_paired_bootstrap_resamples_people_not_trials():
    a=np.array([1.,2.,4.]); b=a+3
    effect=paired_bootstrap(a,b,np.random.default_rng(4),replicates=100)
    assert effect==dict(difference=-3.,lower=-3.,upper=-3.,n_pairs=3)

def test_censoring_keeps_failures_and_budget_cost():
    s=summarize_participants([row(0,'bayes_risk',12,True,.1),row(1,'bayes_risk',60,False,.5)])[0]
    assert s['n']==2 and s['primary_censored']==1
    assert s['primary_success_fraction']==.5
    assert s['primary_cost_mean']==36
    assert s['final_absolute_error_mean']==.3

def test_analysis_pairs_within_scenario_and_preserves_unfavorable_evidence(tmp_path):
    import csv,json
    records=[row(0,'bayes_risk',30,True,.3),row(1,'bayes_risk',60,False,.5),
             row(0,'staircase',10,True,.1),row(1,'staircase',40,True,.2)]
    def write(name, rows):
        with (tmp_path/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write('participants.csv',records)
    write('trials.csv',[dict(scenario=r['scenario'],participant=r['participant'],method=r['method'],trial=60,
        absolute_error=r['final_absolute_error'],signed_error=r['final_signed_error'],interval_width=.5,
        covered=True,acceptable=1,edge_mass=.01,support='within_observed_range') for r in records])
    (tmp_path/'config.json').write_text(json.dumps({'split':'test','seed':17}))
    result=analyze(tmp_path,tmp_path/'analysis',bootstrap_replicates=100)
    cost=next(r for r in result['effects'] if r['metric']=='primary_cost')
    assert cost['difference']==20 and cost['lower']==cost['upper']==20
    assert cost['scenario']=='logistic__precise'
    assert (tmp_path/'analysis'/'scenario_summary.csv').exists()
    assert (tmp_path/'analysis'/'accuracy_trajectories.png').exists()
    assert '不利' in (tmp_path/'analysis'/'results_summary_zh.md').read_text(encoding='utf-8')

def test_unpaired_or_duplicate_people_rejected():
    with pytest.raises(ValueError): paired_bootstrap([1],[1,2],np.random.default_rng(1))

def test_missing_participant_pair_and_duplicate_records_rejected():
    from comfort_boundary_bo_research_package.simulation.decoupled_calibration.analysis import _paired_effects
    records=[row(0,'bayes_risk',30,True,.2),row(1,'bayes_risk',40,True,.2),row(0,'staircase',30,True,.2)]
    with pytest.raises(ValueError): _paired_effects(records,100,7)
    with pytest.raises(ValueError): summarize_participants([records[0],records[0]])

def test_postprocessing_manifest_hashes_actual_inputs(tmp_path):
    import csv,json,hashlib
    rows=[row(0,'bayes_risk',10,True,.1),row(0,'staircase',20,True,.2)]
    for filename,data in [('participants.csv',rows),('trials.csv',[dict(scenario=r['scenario'],participant=0,method=r['method'],trial=1,
            absolute_error=.1,signed_error=.1,interval_width=.5,covered=True,acceptable=1,edge_mass=.01,support='within_observed_range') for r in rows])]:
        with (tmp_path/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    (tmp_path/'config.json').write_text('{}')
    analyze(tmp_path,tmp_path/'analysis',bootstrap_replicates=10)
    manifest=json.loads((tmp_path/'analysis'/'postprocessing_manifest.json').read_text())
    assert manifest['input_sha256']['participants.csv']==hashlib.sha256((tmp_path/'participants.csv').read_bytes()).hexdigest()
    assert manifest['bootstrap_replicates']==10
    assert 'accuracy_trajectories.png' in manifest['figures']

def test_bootstrap_uses_frozen_settings_and_rejects_incomplete_trial_grid(tmp_path):
    import csv,json
    rows=[row(0,'bayes_risk',10,True,.1),row(0,'staircase',20,True,.2)]
    for filename,data in [('participants.csv',rows),('trials.csv',[dict(scenario=r['scenario'],participant=0,method=r['method'],trial=1,
            absolute_error=.1,signed_error=.1,interval_width=.5,covered=True,acceptable=1,edge_mass=.01,support='within_observed_range') for r in rows])]:
        with (tmp_path/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    config={'bootstrap':{'seed':314159,'replicates':25}}
    (tmp_path/'config.json').write_text(json.dumps(config))
    analyze(tmp_path,tmp_path/'analysis')
    metadata=json.loads((tmp_path/'analysis'/'analysis_metadata.json').read_text())
    assert metadata['bootstrap_seed']==314159 and metadata['bootstrap_replicates']==25
    config.update(budget=2,participants_per_cell=1,methods=['bayes_risk','staircase'],families=['logistic'],execution_conditions={'precise':{}})
    (tmp_path/'config.json').write_text(json.dumps(config))
    with pytest.raises(ValueError,match='trial grid'):
        analyze(tmp_path,tmp_path/'analysis')
