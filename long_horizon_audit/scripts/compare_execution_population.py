"""Validate matched experiments and summarize independent population batches."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from long_horizon_audit.scripts.run_multiseed_simulation_audit import t_interval_95
from long_horizon_audit.scripts.run_execution_population_audit import OUTPUT, SUITES, build_scenarios, experiment_metadata
from comfort_boundary_bo_research_package.simulation.run_uncertain_input_bo_extended import ALGORITHM_ORDER

METRICS=['mean_boundary_error','mean_unacceptable_trials','mean_cumulative_discomfort',
         'mean_predictive_brier_score','mean_boundary_ci95_width','boundary_ci95_coverage']
KEYS=['population_block','process_repeat','execution_noise','algorithm']
MATCHED=['process_seed','calibration_seed','generator_fingerprint','policy_fingerprint',
         'n_participants','n_trials_per_algorithm_participant','surrogate_kind']
CONTRASTS={'calibration_vs_oracle':('oracle','calibrated'),
           'population_vs_fixed':('oracle','oracle'),
           'nominal_vs_oracle':('oracle','nominal'),
           'calibration_vs_nominal':('nominal','calibrated')}


def validate_design_rows(frame: pd.DataFrame, specs) -> None:
    """Reject missing whole batches/policies, including when both paired inputs omit them."""
    expected=[]
    for spec in specs:
        c=spec.config
        row=dict(scenario=c.scenario_name,execution_noise=c.execution_noise,population_seed=c.population_seed,
            process_seed=c.seed,calibration_seed=c.calibration_seed,execution_belief=c.execution_belief,
            tau=c.tau,feedback_noise=c.feedback_noise,calibration_bias=c.calibration_bias,
            include_time_effects=c.include_time_effects,n_participants=c.n_participants,
            n_trials_per_algorithm_participant=c.n_trials,surrogate_kind=c.surrogate_kind,
            **experiment_metadata(spec))
        expected.extend({**row,'algorithm':algorithm} for algorithm in ALGORITHM_ORDER)
    expected=pd.DataFrame(expected); keys=['scenario','algorithm']
    if expected.empty or not set(expected.columns).issubset(frame.columns):
        raise ValueError('Results do not contain the declared experiment metadata')
    if frame.duplicated(keys).any(): raise ValueError('Duplicate declared scenario/policy')
    merged=expected.merge(frame,on=keys,how='outer',suffixes=('_expected','_actual'),indicator=True,validate='one_to_one')
    if not merged._merge.eq('both').all(): raise ValueError('Incomplete or extra declared scenario/policy')
    for column in expected.columns.difference(keys):
        if not merged[column+'_expected'].eq(merged[column+'_actual']).all():
            raise ValueError('Result disagrees with experiment manifest: '+column)
    if not set(METRICS).issubset(frame.columns) or not np.isfinite(frame[METRICS].to_numpy()).all():
        raise ValueError('Metrics must be complete and finite')


def summarize_clusters(frame: pd.DataFrame, metric: str) -> dict:
    if frame.empty or frame[['population_block','process_repeat',metric]].isna().any().any():
        raise ValueError('Cluster summaries need nonempty, complete finite data')
    if not np.isfinite(frame[metric]).all() or frame.duplicated(['population_block','process_repeat']).any():
        raise ValueError('Each population/process cell must have exactly one finite value')
    repeats=frame.groupby('population_block').process_repeat.apply(lambda x:tuple(sorted(x)))
    if repeats.nunique()!=1: raise ValueError('Every population block must contain the same process repeats')
    means=frame.groupby('population_block')[metric].mean()
    lo,hi=t_interval_95(means)
    return dict(mean=float(means.mean()),ci95_low=lo,ci95_high=hi,
        n_population_blocks=len(means),n_process_runs=len(frame))


def paired_effects(old: pd.DataFrame, new: pd.DataFrame, contrast: str) -> pd.DataFrame:
    if contrast not in CONTRASTS: raise ValueError('Unknown contrast')
    population_change=contrast=='population_vs_fixed'
    matched=MATCHED+([] if population_change else ['population_seed','population_fingerprint'])
    required=set(KEYS+matched+METRICS+['population_seed','execution_belief'])
    for frame,mode in zip((old,new),CONTRASTS[contrast]):
        if frame.empty or not required.issubset(frame.columns): raise ValueError('Missing comparison inputs')
        if frame[list(required)].isna().any().any() or not frame.execution_belief.eq(mode).all():
            raise ValueError('Missing metadata or wrong execution belief')
        if frame.duplicated(KEYS).any(): raise ValueError('Duplicate comparison cell')
        populations=frame.groupby('population_block').population_seed.nunique()
        if not populations.eq(1).all(): raise ValueError('Each batch must contain one population seed')
    if new[['population_block','population_seed']].drop_duplicates().population_seed.duplicated().any():
        raise ValueError('Independent population batches require distinct population seeds')
    paired=old.merge(new,on=KEYS,how='outer',suffixes=('_old','_new'),validate='one_to_one',indicator=True)
    if not paired._merge.eq('both').all(): raise ValueError('Unmatched population/process cells')
    for field in matched:
        if not paired[field+'_old'].eq(paired[field+'_new']).all(): raise ValueError('Comparison setting differs: '+field)
    rows=[]
    for (noise,algorithm),group in paired.groupby(['execution_noise','algorithm']):
        for metric in METRICS:
            group=group.copy(); group['change']=group[metric+'_new']-group[metric+'_old']
            summary=summarize_clusters(group,'change')
            rows.append(dict(contrast=contrast,execution_noise=noise,algorithm=algorithm,metric=metric,
                old_mean=float(group[metric+'_old'].mean()),new_mean=float(group[metric+'_new'].mean()),
                mean_change=summary.pop('mean'),**summary))
    return pd.DataFrame(rows)


def absolute_summaries(frame: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (suite,noise,mode,algorithm),group in frame[frame.experiment_suite!='historical'].groupby(
            ['experiment_suite','execution_noise','execution_belief','algorithm']):
        for metric in METRICS:
            rows.append(dict(experiment_suite=suite,execution_noise=noise,execution_belief=mode,algorithm=algorithm,
                metric=metric,n_distinct_populations=group.population_seed.nunique(),
                interval_unit='process_block_fixed_population' if suite=='fixed_control' else 'independent_population_batch',
                **summarize_clusters(group,metric)))
    return pd.DataFrame(rows)


def plot_comparison(summary: pd.DataFrame, archive: pd.DataFrame, out: Path):
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    stages=[('Archive: fixed / oracle','#a5a5a5'),('New batches / oracle','#67a9cf'),('New batches / calibrated','#2166ac')]
    for col,noise in enumerate(('low','high')):
        for row,(metric,label) in enumerate((('mean_boundary_error','Absolute boundary error'),
                                           ('mean_unacceptable_trials','Unacceptable trials / 12'))):
            ax=axes[row,col]; x=np.arange(5)
            old=archive[archive.execution_noise==noise].groupby('algorithm')[metric].mean().reindex(ALGORITHM_ORDER)
            for i,(name,color) in enumerate(stages):
                if i==0: values=old
                else:
                    mode='oracle' if i==1 else 'calibrated'
                    subset=summary[(summary.experiment_suite=='population')&(summary.execution_noise==noise)&
                        (summary.execution_belief==mode)&(summary.metric==metric)]
                    values=subset.set_index('algorithm')['mean'].reindex(ALGORITHM_ORDER)
                ax.bar(x+(i-1)*.25,values,width=.24,label=name,color=color)
            ax.set_xticks(x,['Uncertain-input','Naive','Random','Grid','Staircase'],rotation=15)
            ax.set_title(noise.capitalize()+' execution noise'); ax.set_ylabel(label); ax.grid(axis='y',alpha=.2)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.95),ncol=3)
    fig.suptitle('Execution belief and population changes | synthetic study',fontsize=15)
    fig.text(.5,.015,'New results: 5 independent population batches, 2 process seeds each. Archive uses a fixed population; intervals and paired controls are in CSV/report.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.90)); fig.savefig(out/'execution_population_comparison.png',dpi=170); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=OUTPUT)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/execution_population_20261104')
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    suites={suite:pd.read_csv(args.input_dir/f'{suite}_per_run.csv') for suite in SUITES}
    manifests={suite:json.loads((args.input_dir/f'{suite}_configurations.json').read_text(encoding='utf-8')) for suite in SUITES}
    shapes={(m['population_blocks'],m['process_repeats']) for m in manifests.values()}
    if len(shapes)!=1: raise ValueError('Suites use different population/process designs')
    n_blocks,n_repeats=shapes.pop()
    specs=build_scenarios(n_blocks,n_repeats)
    for suite,frame in suites.items():
        selected=[s for s in specs if s.suite==suite]
        expected=[{'population_block':s.population_block,'process_repeat':s.process_repeat,'config':asdict(s.config)} for s in selected]
        if manifests[suite]['scenarios']!=expected: raise ValueError('Configuration manifest differs from declared design')
        validate_design_rows(frame,selected)
    all_runs=pd.concat(suites.values(),ignore_index=True)
    archive=pd.read_csv(ROOT/'long_horizon_audit/derived/simulation_audit_bayesian_20261104/simulation_audit_per_run_metrics.csv')
    archive=archive[archive.scenario.str.startswith('multiseed_')]
    replay=suites['historical'].merge(archive,on=['scenario','algorithm','seed'],suffixes=('_new','_old'),how='outer',indicator=True,validate='one_to_one')
    if not replay._merge.eq('both').all(): raise ValueError('Historical replay incomplete')
    max_delta=0.
    for metric in archive.columns.difference(['scenario','algorithm','seed']):
        if pd.api.types.is_numeric_dtype(archive[metric]) and not pd.api.types.is_bool_dtype(archive[metric]):
            np.testing.assert_allclose(replay[metric+'_new'],replay[metric+'_old'],rtol=0,atol=1e-12)
            max_delta=max(max_delta,float(abs(replay[metric+'_new']-replay[metric+'_old']).max()))
        elif not replay[metric+'_new'].eq(replay[metric+'_old']).all():
            raise ValueError('Historical metadata differs: '+metric)
    population=suites['population']; oracle=population[population.execution_belief=='oracle']; calibrated=population[population.execution_belief=='calibrated']
    stress=suites['stress']; stress_oracle=stress[stress.execution_belief=='oracle']; nominal=stress[stress.execution_belief=='nominal']; stress_cal=stress[stress.execution_belief=='calibrated']
    comparisons=[paired_effects(oracle,calibrated,'calibration_vs_oracle'),
        paired_effects(suites['fixed_control'],oracle,'population_vs_fixed')]
    for frame in comparisons: frame['experiment_suite']='population'
    for left,right,contrast in ((stress_oracle,nominal,'nominal_vs_oracle'),(stress_oracle,stress_cal,'calibration_vs_oracle'),(nominal,stress_cal,'calibration_vs_nominal')):
        result=paired_effects(left,right,contrast); result['experiment_suite']='stress'; comparisons.append(result)
    effects=pd.concat(comparisons,ignore_index=True); effects.to_csv(out/'paired_population_effects.csv',index=False)
    summary=absolute_summaries(all_runs); summary.to_csv(out/'population_cluster_summary.csv',index=False)
    fixed=['RandomContinuous','GridContinuous','Staircase']; invariance_count=0
    for frame in (population,stress):
        for _,group in frame[frame.algorithm.isin(fixed)].groupby(KEYS):
            if group.trajectory_fingerprint.nunique()!=1: raise ValueError('Fixed-policy trajectory changed with execution belief')
            invariance_count+=1
    calibration=all_runs[all_runs.execution_belief=='calibrated'].drop_duplicates('scenario').copy()
    calibration['bias_error']=calibration.belief_execution_bias-calibration.true_execution_bias
    calibration['noise_scale_error']=calibration.belief_execution_noise_scale-calibration.true_execution_noise_scale
    calibration.to_csv(out/'calibration_estimates.csv',index=False)
    validation=dict(historical_rows=len(replay),historical_max_metric_delta=max_delta,
        total_scenarios=all_runs.scenario.nunique(),total_policy_summaries=len(all_runs),
        independent_population_batches=population.population_seed.nunique(),
        fixed_policy_cells_verified=invariance_count,
        interval_method=f'Mean over {n_repeats} process seeds per population batch (one in stress), then t interval over {n_blocks} independent batches',
        mean_absolute_bias_estimation_error=float(calibration.bias_error.abs().mean()),
        mean_absolute_noise_scale_estimation_error=float(calibration.noise_scale_error.abs().mean()),
        max_clipped_calibration_observations=int(calibration.calibration_n_clipped.max()))
    (out/'validation_summary.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    plot_comparison(summary,archive,out)
    print(json.dumps(validation,indent=2))
    print(effects[(effects.algorithm=='UncertainInputBO')&(effects.metric=='mean_boundary_error')].round(6).to_string(index=False))


if __name__=='__main__': main()
