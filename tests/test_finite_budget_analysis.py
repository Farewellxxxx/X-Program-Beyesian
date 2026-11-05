import copy
import json
import numpy as np
import pytest
from comfort_boundary_bo_research_package.simulation.finite_budget.analysis import analyze_v2, paired_percentile, label_effect_scope
from comfort_boundary_bo_research_package.simulation.finite_budget.study import run_study_v2, read_jsonl, select_staircase, staircase_id
from comfort_boundary_bo_research_package.simulation.finite_budget.contracts import StaircaseSpec
from test_finite_budget_study import tiny_config


def test_paired_percentile_matches_independent_draws():
    a=np.array([1.,0.,1.,0.]); b=np.array([0.,0.,1.,1.]); seed=987
    result=paired_percentile(a,b,seed=seed)
    rng=np.random.default_rng(seed); ids=rng.integers(0,4,size=(20000,4)); samples=(a[ids]-b[ids]).mean(axis=1)
    assert result['difference']==0
    assert result['confidence_bonferroni']==pytest.approx(1-.05/6)
    assert result['lower_95']==np.quantile(samples,.025)
    assert result['upper_95']==np.quantile(samples,.975)
    assert result['lower_bonferroni']==np.quantile(samples,.05/12)
    assert result['upper_bonferroni']==np.quantile(samples,1-.05/12)
    assert paired_percentile([1,1],[0,0],seed=seed)['lower_95']==1


def test_analysis_scenario_layers_and_same_output_sensitivity(tmp_path):
    run_study_v2(tiny_config(),tmp_path/'r')
    result=analyze_v2(tmp_path/'r',tmp_path/'a',plots=False)
    main=read_jsonl(tmp_path/'a/fixed_budget.jsonl')
    sensitivity=read_jsonl(tmp_path/'a/delta_sensitivity.jsonl')
    contrasts=read_jsonl(tmp_path/'a/paired_effects.jsonl')
    assert {r['scenario'] for r in main}=={'logistic_precise','probit_precise'}
    assert all(r['n']==2 for r in main)
    assert {r['track'] for r in contrasts}=={'pipeline','common'}
    assert all(r['bootstrap_draws']==20000 for r in contrasts)
    for r in sensitivity:
        reference=next(m for m in main if all(m[k]==r[k] for k in ('scenario','method','track','estimator','budget')))
        assert r['finite_mae']==reference['finite_mae']
        assert r['finite_p90_error']==reference['finite_p90_error']
        assert r['readout_delta']==.15 and r['delta'] in (.10,.20)
    assert result['primary_budget']==2
    assert result['actual_analysis_source_hashes']==result['frozen_analysis_source_hashes']
    assert len(result['input_artifact_sha256']['observations.jsonl'])==64
    assert (tmp_path/'a/report_zh.md').exists()
    assert (tmp_path/'a/pipeline.jsonl').exists() and (tmp_path/'a/common.jsonl').exists()
    assert 'NaN' not in (tmp_path/'a/fixed_budget.jsonl').read_text()


def test_analysis_refuses_incomplete_run_before_outputs(tmp_path):
    run_study_v2(tiny_config(),tmp_path/'r')
    p=tmp_path/'r/checkpoints.jsonl'; p.write_text('\n'.join(p.read_text().splitlines()[:-1])+'\n')
    with pytest.raises(ValueError): analyze_v2(tmp_path/'r',tmp_path/'a',plots=False)
    assert not (tmp_path/'a').exists()


def test_selection_includes_all_candidates_and_failed_fit_penalty(tmp_path):
    c=tiny_config(); c['participants']=1; c['study'].update(primary_budget=1,max_budget=1,checkpoints=[1])
    c['methods']=[]
    for initial in (.3,.6,.9):
        for floor in (.1,.15):
            s=StaircaseSpec(initial=initial,floor=floor)
            c['methods'].append(dict(id=staircase_id(s),sampler='staircase',staircase=dict(initial=initial,floor=floor)))
    run_study_v2(c,tmp_path/'r'); result=select_staircase(tmp_path/'r')
    assert len(result['candidates'])==6
    assert all(r['capped_mae']==3. and r['supported_success_rate']==0 for r in result['candidates'])
    assert result['selected']['initial']==.3 and result['selected']['floor']==.1


def test_controlled_contrasts_and_stop_error_labels(tmp_path):
    c=tiny_config(); c['participants']=1; c['scenarios']=c['scenarios'][:1]
    c['methods']=[dict(id=k,sampler=k) for k in ('old_variance','new_variance','new_precision','staircase')]
    c['readouts']={'stop_replay':True}
    run_study_v2(c,tmp_path/'r'); analyze_v2(tmp_path/'r',tmp_path/'a',plots=False)
    effects=read_jsonl(tmp_path/'a/paired_effects.jsonl')
    secondary=[r for r in effects if r['role']=='secondary_controlled']
    assert {(r['method_a'],r['method_b']) for r in secondary}=={('new_precision','new_variance'),('new_variance','old_variance')}
    assert all(r['track']=='common' for r in secondary)
    stop=read_jsonl(tmp_path/'a/stop_replay.jsonl')[0]
    assert stop['true_error_failure_at_stop'] is None and stop['numerical_failure_at_stop'] is None
    assert 'conditional_mean_abs_error_at_stop' in stop


def test_stress_does_not_claim_six_scenario_familywise_correction():
    raw=paired_percentile([1,0],[0,0],seed=1)
    stress=label_effect_scope(raw,'stress')
    assert stress['lower_bonferroni'] is None and stress['upper_bonferroni'] is None
    assert stress['confidence_bonferroni'] is None and stress['evidence_scope']=='exploratory_stress'
    assert stress['lower_95']==raw['lower_95']
    assert label_effect_scope(raw,'development')['evidence_scope']=='development_only'
    assert label_effect_scope(raw,'heldout')['confidence_bonferroni']==pytest.approx(1-.05/6)
