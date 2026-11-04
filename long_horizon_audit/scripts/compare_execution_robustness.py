"""Validate complete robustness experiments and compute paired batch contrasts."""
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
from long_horizon_audit.scripts import run_execution_robustness_audit as audit
from long_horizon_audit.scripts.compare_execution_population import summarize_clusters

METRICS=['mean_boundary_error','mean_unacceptable_trials','mean_cumulative_discomfort',
         'mean_predictive_brier_score','mean_boundary_ci95_width','boundary_ci95_coverage','protocol_deviation_rate']
DIAGNOSTICS=['mean_abs_error','sd_abs_error','wasserstein1','interval90_coverage','protocol_probability_abs_error']
MATCHED=['population_seed','process_seed','calibration_seed','process_rng_mode','population_fingerprint',
         'policy_fingerprint','n_participants','n_trials_per_algorithm_participant']


def validate_results(frame,specs):
    expected=pd.DataFrame([{**audit.expected_metadata(s),'algorithm':a} for s in specs for a in audit.sim.ALGORITHM_ORDER])
    keys=['scenario','algorithm']
    if expected.empty or not set(expected.columns).issubset(frame.columns) or frame.duplicated(keys).any():
        raise ValueError('Missing metadata or duplicate scenario/algorithm')
    merged=expected.merge(frame,on=keys,how='outer',suffixes=('_expected','_actual'),indicator=True,validate='one_to_one')
    if not merged._merge.eq('both').all(): raise ValueError('Incomplete or extra experiment cells')
    for column in expected.columns.difference(keys):
        if not merged[column+'_expected'].eq(merged[column+'_actual']).all(): raise ValueError('Metadata differs: '+column)
    if not set(METRICS).issubset(frame.columns) or not np.isfinite(frame[METRICS].to_numpy()).all():
        raise ValueError('Nonfinite or missing metrics')
    counts=frame[['calibration_n_observations','calibration_n_used','calibration_n_clipped']]
    if not counts.notna().all().all() or not frame.calibration_n_observations.eq(frame.calibration_budget).all():
        raise ValueError('Calibration budget was not honored')
    if not (frame.calibration_n_used+frame.calibration_n_clipped).eq(frame.calibration_n_observations).all():
        raise ValueError('Calibration accounting is inconsistent')


def verify_streams(specs):
    # Unique process roots represent intentional common-random-number groups.
    roots={}
    for s in specs:
        c=s.config
        if c.process_rng_mode!='independent': raise ValueError('Independent streams required')
        identity=(s.population_block,s.process_repeat,'matched_'+c.execution_noise if s.profile.startswith('matched_') else 'biased')
        if c.seed in roots and roots[c.seed][0]!=identity: raise ValueError('Process root shared by independent cells')
        roots[c.seed]=(identity,c)
    states=set()
    for _,c in roots.values():
        for pid in range(1,c.n_participants+1):
            for algorithm in range(5):
                for role in ['execution','feedback']+(['policy'] if algorithm<3 else []):
                    state=json.dumps(audit.sim.process_rng(c,role,pid,algorithm).bit_generator.state,sort_keys=True)
                    if state in states: raise ValueError('Actual leaf stream collision')
                    states.add(state)
    return len(states)


def validate_calibration(frame,specs):
    expected={s.config.scenario_name:s for s in specs if s.arm.startswith('cal')}
    if set(frame.scenario.unique())!=set(expected): raise ValueError('Calibration scenario set differs')
    groups={}
    for scenario,spec in expected.items():
        rows=frame[frame.scenario==scenario].sort_values('calibration_trial')
        n=spec.config.calibration_trials
        if rows.calibration_trial.tolist()!=list(range(1,n+1)): raise ValueError('Missing/duplicate calibration observations')
        values=rows[audit.sim.CALIBRATION_FIELDS].to_numpy(float)
        if not np.isfinite(values).all(): raise ValueError('Nonfinite calibration observations')
        expected_commands=audit.stress.nested_commands(audit.sim.ExecutionSettings(x_min=spec.config.x_min,x_max=spec.config.x_max),n)
        if not np.allclose(values[:,0],expected_commands,rtol=0,atol=1e-12): raise ValueError('Calibration command design differs')
        groups.setdefault((spec.profile,spec.population_block,spec.process_repeat),[]).append(values)
    for rows in groups.values():
        largest=max(rows,key=len)
        for values in rows:
            if not np.allclose(values,largest[:len(values)],rtol=0,atol=1e-12): raise ValueError('Calibration budgets are not nested prefixes')
    return len(expected)


def validate_diagnostics(frame,specs,n_samples=4096):
    expected={s.config.scenario_name:s for s in specs}
    if set(frame.scenario.unique())!=set(expected): raise ValueError('Diagnostic scenario set differs')
    for scenario,spec in expected.items():
        rows=frame[frame.scenario==scenario].sort_values('command')
        grid=np.linspace(spec.config.x_min,spec.config.x_max,21)
        if len(rows)!=21 or not np.allclose(rows.command,grid,rtol=0,atol=1e-12): raise ValueError('Incomplete diagnostic command grid')
        span=spec.config.x_max-spec.config.x_min
        regions=np.where((grid>=spec.config.x_min+.2*span-1e-12)&(grid<=spec.config.x_min+.8*span+1e-12),'interior','extrapolation')
        if not np.array_equal(rows.region.to_numpy(),regions): raise ValueError('Diagnostic command regions differ')
        for key,value in audit.expected_metadata(spec).items():
            if key not in rows or not rows[key].eq(value).all(): raise ValueError('Diagnostic metadata differs: '+key)
        if not rows.diagnostic_samples.eq(n_samples).all(): raise ValueError('Diagnostic sample budget differs')
    if not np.isfinite(frame[DIAGNOSTICS].to_numpy()).all(): raise ValueError('Nonfinite diagnostic')
    if (frame[DIAGNOSTICS]<0).any().any() or (frame.interval90_coverage>1).any(): raise ValueError('Invalid diagnostic range')


def paired_difference(old,new,metric,allow_truth_change=False,allow_algorithm_change=False):
    keys=['population_block','process_repeat']
    for frame in (old,new):
        if frame.empty or frame.duplicated(keys).any(): raise ValueError('Missing/duplicate paired cells')
        if frame.algorithm.nunique()!=1 or not np.isfinite(frame[metric]).all(): raise ValueError('Invalid paired algorithm/metric')
        seeds=frame.groupby('population_block').population_seed.unique()
        if any(len(v)!=1 for v in seeds) or len({v[0] for v in seeds})!=len(seeds):
            raise ValueError('Each independent batch must have one distinct population seed')
    paired=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one')
    if not paired._merge.eq('both').all(): raise ValueError('Unmatched paired cells')
    matched=MATCHED+([] if allow_truth_change else ['truth_fingerprint'])+([] if allow_algorithm_change else ['algorithm'])
    for field in matched:
        if not paired[field+'_old'].eq(paired[field+'_new']).all(): raise ValueError('Pair setting differs: '+field)
    paired['change']=paired[metric+'_new']-paired[metric+'_old']
    summary=summarize_clusters(paired,'change')
    return dict(old_mean=float(paired[metric+'_old'].mean()),new_mean=float(paired[metric+'_new'].mean()),
        mean_change=summary.pop('mean'),**summary)


def compute_tables(frame,diagnostics):
    absolute=[]; contrasts=[]; diagnostic_rows=[]
    for (profile,arm,algorithm),group in frame.groupby(['profile','arm','algorithm']):
        for metric in METRICS:
            absolute.append(dict(profile=profile,arm=arm,algorithm=algorithm,metric=metric,**summarize_clusters(group,metric)))
    def contrast(old,new,name,profile,arm,algorithm,truth=False,alg=False):
        for metric in METRICS:
            contrasts.append(dict(contrast=name,profile=profile,arm=arm,algorithm=algorithm,metric=metric,
                **paired_difference(old,new,metric,truth,alg)))
    for profile in audit.PROFILES:
        for algorithm in audit.sim.ALGORITHM_ORDER:
            selected=frame[(frame.profile==profile)&(frame.algorithm==algorithm)]
            for arm in audit.ARMS:
                current=selected[selected.arm==arm]
                if arm.startswith('cal'):
                    for ref in ('oracle','nominal','cal40'):
                        if arm!=ref: contrast(selected[selected.arm==ref],current,'vs_'+ref,profile,arm,algorithm)
                if profile in ('gain_high','nonlinear_high','correlated_high','combined_high'):
                    base=frame[(frame.profile=='biased_high')&(frame.arm==arm)&(frame.algorithm==algorithm)]
                    contrast(base,current,'vs_biased_high',profile,arm,algorithm,truth=True)
        for arm in audit.ARMS:
            selected=frame[(frame.profile==profile)&(frame.arm==arm)]
            contrast(selected[selected.algorithm=='NaiveContinuousBO'],selected[selected.algorithm=='UncertainInputBO'],
                'uncertain_vs_naive',profile,arm,'UncertainInputBO',alg=True)
    for (profile,arm,region),group in diagnostics.groupby(['profile','arm','region']):
        means=group.groupby(['population_block','process_repeat'],as_index=False)[DIAGNOSTICS].mean()
        for metric in DIAGNOSTICS:
            diagnostic_rows.append(dict(profile=profile,arm=arm,region=region,metric=metric,**summarize_clusters(means,metric)))
    return pd.DataFrame(absolute),pd.DataFrame(contrasts),pd.DataFrame(diagnostic_rows)


def plot_tables(summary,diagnostics,out):
    profiles=list(audit.PROFILES); budgets=list(audit.BUDGETS)
    fig,axes=plt.subplots(2,4,figsize=(16,8))
    for ax,profile in zip(axes.flat,profiles):
        rows=summary[(summary.profile==profile)&(summary.algorithm=='UncertainInputBO')]
        for metric,color,label in [('mean_boundary_error','#2166ac','Boundary error')]:
            values=rows[(rows.metric==metric)&rows.arm.str.startswith('cal')].set_index('arm').loc[[f'cal{n}' for n in budgets]]
            ax.errorbar(budgets,values['mean'],yerr=[values['mean']-values.ci95_low,values.ci95_high-values['mean']],marker='o',capsize=3,color=color,label=label)
            for arm,style,c in [('oracle','--','#666666'),('nominal',':','#d95f02')]:
                ax.axhline(rows[(rows.metric==metric)&(rows.arm==arm)]['mean'].iloc[0],color=c,linestyle=style,label=arm)
        ax.set_xscale('log'); ax.set_xticks(budgets,[str(n) for n in budgets]); ax.set_title(profile.replace('_',' ')); ax.grid(alpha=.2)
        ax.set_xlabel('Extra calibration maneuvers'); ax.set_ylabel('Absolute B_tau error')
    axes.flat[-1].axis('off'); axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(),loc='center')
    fig.suptitle('Uncertain-input BO | calibration budget and boundary error (95% batch intervals)')
    fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(out/'budget_boundary_error.png',dpi=160); plt.close(fig)
    fig,axes=plt.subplots(2,4,figsize=(16,8))
    for ax,profile in zip(axes.flat,profiles):
        rows=summary[(summary.profile==profile)&(summary.algorithm=='UncertainInputBO')&(summary.metric=='mean_unacceptable_trials')].set_index('arm')
        arms=list(audit.ARMS); selected=rows.loc[arms]
        ax.bar(range(6),selected['mean'],color=['#d95f02','#999999',*['#2166ac']*4],
            yerr=[selected['mean']-selected.ci95_low,selected.ci95_high-selected['mean']],capsize=2)
        ax.set_xticks(range(6),['nominal','oracle','8','20','40','160'],rotation=25)
        ax.set_title(profile.replace('_',' ')); ax.set_ylabel('Unacceptable trials / 12'); ax.grid(axis='y',alpha=.2)
    axes.flat[-1].axis('off')
    fig.suptitle('Uncertain-input BO | exposure versus calibration cost (95% batch intervals)')
    fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(out/'budget_unacceptable_trials.png',dpi=160); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    for row,(metric,label) in enumerate([('mean_abs_error','Mean intensity prediction absolute error'),('wasserstein1','Empirical Wasserstein-1 distance')]):
        for ax,region in zip(axes[row],['interior','extrapolation']):
            for profile in profiles:
                rows=diagnostics[(diagnostics.profile==profile)&(diagnostics.region==region)&(diagnostics.metric==metric)].set_index('arm')
                ax.plot(budgets,rows.loc[[f'cal{n}' for n in budgets],'mean'],marker='o',label=profile.replace('_',' '))
            ax.set_xscale('log'); ax.set_xticks(budgets,[str(n) for n in budgets]); ax.set_title(region+' commands')
            ax.set_xlabel('Extra calibration maneuvers'); ax.set_ylabel(label); ax.grid(alpha=.2)
    axes[0,1].legend(fontsize=8); fig.suptitle('Independent execution diagnostics | check both location and distribution shape')
    fig.tight_layout(rect=(0,0,1,.94)); fig.savefig(out/'execution_prediction_diagnostics.png',dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=audit.OUTPUT)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/execution_robustness_20261104')
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    manifests={p:json.loads((args.input_dir/f'{p}_configurations.json').read_text(encoding='utf-8')) for p in audit.PROFILES}
    shapes={(m['population_blocks'],m['process_repeats']) for m in manifests.values()}
    if len(shapes)!=1: raise ValueError('Profile study shapes differ')
    blocks,repeats=shapes.pop(); specs=audit.build_scenarios(blocks,repeats)
    frames=[]; diagnostic_frames=[]; calibration_frames=[]
    read=lambda path:pd.read_csv(path,float_precision='round_trip')
    for profile in audit.PROFILES:
        selected=[s for s in specs if s.profile==profile]; manifest=manifests[profile]
        if manifest['scenarios']!=[asdict(s) for s in selected] or manifest['diagnostic_samples']!=4096:
            raise ValueError('Manifest differs from declared design')
        frame=read(args.input_dir/f'{profile}_per_run.csv'); validate_results(frame,selected); frames.append(frame)
        calibration=read(args.input_dir/f'{profile}_calibration.csv'); validate_calibration(calibration,selected); calibration_frames.append(calibration)
        diagnostics=read(args.input_dir/f'{profile}_diagnostics.csv'); validate_diagnostics(diagnostics,selected); diagnostic_frames.append(diagnostics)
    frame=pd.concat(frames,ignore_index=True); diagnostics=pd.concat(diagnostic_frames,ignore_index=True)
    fixed=frame[frame.algorithm.isin(['RandomContinuous','GridContinuous','Staircase'])]
    cells=fixed.groupby(['profile','population_block','process_repeat','algorithm']).trajectory_fingerprint.nunique()
    if not cells.eq(1).all(): raise ValueError('Fixed strategy trajectories changed across beliefs/budgets')
    replay=read(args.input_dir/'replay_per_run.csv')
    old=pd.concat([read(audit.previous.OUTPUT/f'{suite}_per_run.csv') for suite in ('population','stress')],ignore_index=True)
    replay_manifest=json.loads((args.input_dir/'replay_configurations.json').read_text(encoding='utf-8'))
    replay_specs=[s for s in audit.previous.build_scenarios() if s.suite in ('population','stress')]
    if replay_manifest['scenarios']!=[asdict(s) for s in replay_specs]: raise ValueError('Replay manifest differs')
    keys=['scenario','algorithm']; joined=old.merge(replay,on=keys,suffixes=('_old','_new'),how='outer',indicator=True,validate='one_to_one')
    if not joined._merge.eq('both').all(): raise ValueError('Historical replay missing rows')
    max_delta=0.
    for column in old.columns.difference(keys):
        a,b=joined[column+'_old'],joined[column+'_new']
        if pd.api.types.is_numeric_dtype(a) and not pd.api.types.is_bool_dtype(a):
            delta=float(np.abs(a-b).max()); max_delta=max(max_delta,delta)
            if delta!=0: raise ValueError('Historical numerical replay differs: '+column)
        elif not a.eq(b).all(): raise ValueError('Historical replay differs: '+column)
    summary,contrasts,diag_summary=compute_tables(frame,diagnostics)
    # Isolate the change from sorted linspace to nested calibration commands.
    schedule=[]
    for profile,suite,noise in [('matched_low','population','low'),('matched_high','population','high'),('biased_high','stress','high')]:
        for algorithm in audit.sim.ALGORITHM_ORDER:
            before=old[(old.experiment_suite==suite)&(old.execution_noise==noise)&(old.execution_belief=='calibrated')&(old.algorithm==algorithm)].copy()
            before['truth_fingerprint']=[audit.expected_metadata(next(s for s in specs if s.profile==profile))['truth_fingerprint']]*len(before)
            after=frame[(frame.profile==profile)&(frame.arm=='cal40')&(frame.algorithm==algorithm)]
            after=after[after.process_repeat.isin(before.process_repeat.unique())]
            for metric in METRICS:
                schedule.append(dict(profile=profile,algorithm=algorithm,metric=metric,**paired_difference(before,after,metric)))
    parameters=frame.drop_duplicates('scenario')[['scenario','profile','arm','population_block','process_repeat',
        'true_execution_bias','true_execution_noise_scale','belief_execution_bias','belief_execution_noise_scale',
        'calibration_n_observations','calibration_n_used','calibration_n_clipped']]
    validation=dict(main_scenarios=len(specs),main_policy_rows=len(frame),replay_scenarios=len(replay_specs),
        replay_policy_rows=len(replay),historical_max_metric_delta=max_delta,independent_population_batches=blocks,
        process_repeats=repeats,unique_leaf_streams=verify_streams(specs),fixed_policy_cells=len(cells),
        nested_calibrations=sum(s.arm.startswith('cal') for s in specs),diagnostic_rows=len(diagnostics),
        max_clipped_calibration_observations=int(frame.calibration_n_clipped.max()),
        interval_method='Average process repeats within population batch; paired t interval over independent batches')
    for name,data in [('population_summary',summary),('paired_effects',contrasts),('execution_diagnostics_summary',diag_summary),
                      ('calibration_schedule_effects',pd.DataFrame(schedule)),('calibration_parameters',parameters)]:
        data.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    plot_tables(summary,diag_summary,out)
    (out/'validation_summary.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation,indent=2))


if __name__=='__main__': main()
