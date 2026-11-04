"""Strict paired checks and batch-level comparisons for flexible execution fits."""
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
from long_horizon_audit.scripts import run_flexible_execution_audit as audit
from long_horizon_audit.scripts import compare_execution_robustness as prior

OUTPUT=ROOT/'results/flexible_execution_20261104'


def validate_replay(old,new):
    keys=['scenario','algorithm']
    if set(old.columns)!=set(new.columns): raise ValueError('Replay schema differs')
    if old.duplicated(keys).any() or new.duplicated(keys).any(): raise ValueError('Duplicate replay cells')
    joined=old.merge(new,on=keys,suffixes=('_old','_new'),how='outer',indicator=True,validate='one_to_one')
    if not joined._merge.eq('both').all(): raise ValueError('Replay cells differ')
    for column in old.columns.difference(keys):
        a,b=joined[column+'_old'],joined[column+'_new']
        if not (a.eq(b)|(a.isna()&b.isna())).all(): raise ValueError('Replay changed: '+column)
    return 0.


def validate_observation_pairs(old,new):
    keys=['population_block','process_repeat']
    if old.duplicated(keys).any() or new.duplicated(keys).any(): raise ValueError('Duplicate observation pair')
    joined=old.merge(new,on=keys,suffixes=('_old','_new'),how='outer',indicator=True,validate='one_to_one')
    if not joined._merge.eq('both').all() or not joined.calibration_fingerprint_old.eq(joined.calibration_fingerprint_new).all():
        raise ValueError('Calibration observations differ between estimators')


def validate_bundle(results,calibration,diagnostics,fits,old_calibration,specs,n_samples=4096):
    prior.validate_results(results,specs)
    prior.validate_calibration(calibration,specs)
    prior.validate_diagnostics(diagnostics,specs,n_samples)
    expected={s.config.scenario_name:s for s in specs}
    if fits.scenario.duplicated().any() or set(fits.scenario)!=set(expected): raise ValueError('Fit cells differ')
    for scenario,spec in expected.items():
        obs=calibration[calibration.scenario==scenario].sort_values('calibration_trial')
        old=old_calibration[old_calibration.scenario==scenario].sort_values('calibration_trial')
        fields=['calibration_trial',*audit.old.sim.CALIBRATION_FIELDS]
        if not np.array_equal(obs[fields].to_numpy(),old[fields].to_numpy()):
            raise ValueError('Calibration observations differ from frozen baseline')
        settings=audit.old.sim.ExecutionSettings(**{f.name:getattr(spec.config,f.name) for f in audit.old.sim.fields(audit.old.sim.ExecutionSettings)})
        fit=audit.model.fit_flexible_execution(obs,settings,audit.SETTINGS)
        metadata={**audit.old.expected_metadata(spec),**fit.metadata(),
            'calibration_fingerprint':audit.observation_fingerprint(obs)}
        for frame in (results,calibration,diagnostics,fits):
            rows=frame[frame.scenario==scenario]
            for key,value in metadata.items():
                if key not in rows: raise ValueError('Missing fit metadata: '+key)
                actual=rows[key]
                same=(np.allclose(actual,value,rtol=0,atol=1e-12) if isinstance(value,float) else actual.eq(value).all())
                if not same: raise ValueError('Fit/configuration differs: '+key)
    return len(expected)


def add_reference_hashes(frame,calibration):
    frame=frame.copy()
    hashes={name:audit.observation_fingerprint(rows.sort_values('calibration_trial')) for name,rows in calibration.groupby('scenario')}
    frame['calibration_fingerprint']=frame.scenario.map(hashes).fillna('none')
    return frame


def compute_tables(old,new,old_diagnostics,new_diagnostics):
    old=old.copy(); new=new.copy(); old['estimator']='simple'; new['estimator']='quadratic_covariance'
    old_diagnostics=old_diagnostics.copy(); new_diagnostics=new_diagnostics.copy()
    old_diagnostics['estimator']='simple'; new_diagnostics['estimator']='quadratic_covariance'
    all_results=pd.concat([old,new],ignore_index=True)
    all_diagnostics=pd.concat([old_diagnostics,new_diagnostics],ignore_index=True)
    summaries=[]; effects=[]; diagnostic_summaries=[]; diagnostic_effects=[]
    for (estimator,profile,arm,algorithm),rows in all_results.groupby(['estimator','profile','arm','algorithm']):
        for metric in prior.METRICS:
            summaries.append(dict(estimator=estimator,profile=profile,arm=arm,algorithm=algorithm,metric=metric,
                **prior.summarize_clusters(rows,metric)))
    def contrast(before,after,name,profile,arm,algorithm,algorithm_change=False):
        if name=='new_vs_old': validate_observation_pairs(before,after)
        for metric in prior.METRICS:
            effects.append(dict(contrast=name,profile=profile,arm=arm,algorithm=algorithm,metric=metric,
                **prior.paired_difference(before,after,metric,allow_algorithm_change=algorithm_change)))
    for profile in audit.old.PROFILES:
        for algorithm in audit.old.sim.ALGORITHM_ORDER:
            before=old[(old.profile==profile)&(old.algorithm==algorithm)]
            after=new[(new.profile==profile)&(new.algorithm==algorithm)]
            for budget in audit.old.BUDGETS:
                arm=f'cal{budget}'; current=after[after.arm==arm]
                contrast(before[before.arm==arm],current,'new_vs_old',profile,arm,algorithm)
                for ref in ('nominal','oracle'):
                    contrast(before[before.arm==ref],current,'new_vs_'+ref,profile,arm,algorithm)
                if budget!=40: contrast(after[after.arm=='cal40'],current,'new_vs_new_cal40',profile,arm,algorithm)
        for budget in audit.old.BUDGETS:
            arm=f'cal{budget}'; rows=new[(new.profile==profile)&(new.arm==arm)]
            contrast(rows[rows.algorithm=='NaiveContinuousBO'],rows[rows.algorithm=='UncertainInputBO'],
                'uncertain_vs_naive',profile,arm,'UncertainInputBO',True)
    for (estimator,profile,arm,region),rows in all_diagnostics.groupby(['estimator','profile','arm','region']):
        means=rows.groupby(['population_block','process_repeat'],as_index=False)[prior.DIAGNOSTICS].mean()
        for metric in prior.DIAGNOSTICS:
            diagnostic_summaries.append(dict(estimator=estimator,profile=profile,arm=arm,region=region,metric=metric,
                **prior.summarize_clusters(means,metric)))
    keys=['profile','arm','region','population_block','process_repeat',*prior.MATCHED,'truth_fingerprint','calibration_fingerprint']
    # Average command positions before forming batch-level paired differences.
    before=old_diagnostics[old_diagnostics.arm.str.startswith('cal')].groupby(keys,as_index=False)[prior.DIAGNOSTICS].mean()
    after=new_diagnostics.groupby(keys,as_index=False)[prior.DIAGNOSTICS].mean()
    before['algorithm']='execution_distribution'; after['algorithm']='execution_distribution'
    for (profile,arm,region),rows in after.groupby(['profile','arm','region']):
        reference=before[(before.profile==profile)&(before.arm==arm)&(before.region==region)]
        validate_observation_pairs(reference,rows)
        for metric in prior.DIAGNOSTICS:
            diagnostic_effects.append(dict(profile=profile,arm=arm,region=region,metric=metric,
                **prior.paired_difference(reference,rows,metric)))
    return tuple(map(pd.DataFrame,(summaries,effects,diagnostic_summaries,diagnostic_effects)))


def plot_tables(summary,diagnostics,out):
    budgets=list(audit.old.BUDGETS); arms=[f'cal{n}' for n in budgets]
    for metric,label,source,extra,file in [
        ('mean_boundary_error','Absolute B_tau error',summary,{'algorithm':'UncertainInputBO'},'budget_boundary_error.png'),
        ('mean_unacceptable_trials','Unacceptable feedback / 12',summary,{'algorithm':'UncertainInputBO'},'budget_unacceptable_trials.png'),
        ('mean_abs_error','Mean intensity prediction absolute error',diagnostics,{'region':'extrapolation'},'extrapolation_mean_error.png'),
        ('interval90_coverage','90% predictive interval coverage',diagnostics,{'region':'extrapolation'},'extrapolation_coverage.png')]:
        fig,axes=plt.subplots(2,4,figsize=(16,8))
        for ax,profile in zip(axes.flat,audit.old.PROFILES):
            rows=source[(source.profile==profile)&(source.metric==metric)]
            for key,value in extra.items(): rows=rows[rows[key]==value]
            for estimator,color,label_est in [('simple','#d95f02','Previous fit'),('quadratic_covariance','#2166ac','Quadratic + covariance')]:
                values=rows[(rows.estimator==estimator)&rows.arm.isin(arms)].set_index('arm').loc[arms]
                ax.errorbar(budgets,values['mean'],yerr=[values['mean']-values.ci95_low,values.ci95_high-values['mean']],
                    marker='o',capsize=2,color=color,label=label_est)
            oracle=rows[(rows.estimator=='simple')&(rows.arm=='oracle')]['mean'].iloc[0]
            ax.axhline(oracle,linestyle='--',color='#555555',label='Oracle')
            if metric=='interval90_coverage': ax.axhline(.90,linestyle=':',color='#999999',label='Nominal 90%')
            ax.set_xscale('log'); ax.set_xticks(budgets,[str(n) for n in budgets]); ax.grid(alpha=.2)
            ax.set_title(profile.replace('_',' ')); ax.set_xlabel('Calibration maneuvers'); ax.set_ylabel(label)
        axes.flat[-1].axis('off'); axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(),loc='center')
        fig.suptitle(label+' | means and 95% population-batch intervals')
        fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(out/file,dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=audit.OUTPUT)
    parser.add_argument('--baseline-dir',type=Path,default=audit.old.OUTPUT)
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    read=lambda path:pd.read_csv(path,float_precision='round_trip')
    specs=audit.old.build_scenarios(); new_specs=audit.build_scenarios()
    old_frames=[]; new_frames=[]; old_diags=[]; new_diags=[]; fits=[]
    replay_rows=0; calibration_count=0
    for profile in audit.old.PROFILES:
        full=[s for s in specs if s.profile==profile]; selected=[s for s in new_specs if s.profile==profile]
        for prefix,rows,replay in [(profile,selected,False),('replay_'+profile,full,True)]:
            actual=json.loads((args.input_dir/f'{prefix}_configurations.json').read_text(encoding='utf-8'))
            if actual!=audit.manifest(rows,5,2,replay): raise ValueError('Manifest differs: '+prefix)
        baseline_manifest=json.loads((args.baseline_dir/f'{profile}_configurations.json').read_text(encoding='utf-8'))
        if baseline_manifest['scenarios']!=[asdict(s) for s in full] or baseline_manifest['diagnostic_samples']!=4096:
            raise ValueError('Baseline manifest differs')
        before=read(args.baseline_dir/f'{profile}_per_run.csv'); prior.validate_results(before,full)
        replay=read(args.input_dir/f'replay_{profile}_per_run.csv'); validate_replay(before,replay); replay_rows+=len(replay)
        old_cal=read(args.baseline_dir/f'{profile}_calibration.csv'); prior.validate_calibration(old_cal,full)
        old_diag=read(args.baseline_dir/f'{profile}_diagnostics.csv'); prior.validate_diagnostics(old_diag,full)
        new=read(args.input_dir/f'{profile}_per_run.csv'); cal=read(args.input_dir/f'{profile}_calibration.csv')
        diag=read(args.input_dir/f'{profile}_diagnostics.csv'); fit=read(args.input_dir/f'{profile}_fits.csv')
        calibration_count+=validate_bundle(new,cal,diag,fit,old_cal,selected)
        old_frames.append(add_reference_hashes(before,old_cal)); old_diags.append(add_reference_hashes(old_diag,old_cal))
        new_frames.append(new); new_diags.append(diag); fits.append(fit)
    old=pd.concat(old_frames,ignore_index=True); new=pd.concat(new_frames,ignore_index=True)
    old_diag=pd.concat(old_diags,ignore_index=True); new_diag=pd.concat(new_diags,ignore_index=True)
    fixed_names=['RandomContinuous','GridContinuous','Staircase']
    fixed=pd.concat([old[old.arm.str.startswith('cal')],new],ignore_index=True)
    cells=fixed[fixed.algorithm.isin(fixed_names)].groupby(['profile','population_block','process_repeat','algorithm']).trajectory_fingerprint.nunique()
    if not cells.eq(1).all(): raise ValueError('Fixed-policy physical trajectories changed')
    summary,effects,diag_summary,diag_effects=compute_tables(old,new,old_diag,new_diag)
    all_fits=pd.concat(fits,ignore_index=True)
    for name,frame in [('population_summary',summary),('paired_effects',effects),('execution_diagnostics_summary',diag_summary),
                       ('execution_paired_effects',diag_effects),('execution_fit_parameters',all_fits)]:
        frame.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    plot_tables(summary,diag_summary,out)
    validation=dict(new_scenarios=len(new_specs),replay_scenarios=len(specs),new_policy_rows=len(new),replay_policy_rows=replay_rows,
        historical_max_metric_delta=0.,identical_calibration_sets=calibration_count,diagnostic_rows=len(new_diag),
        fixed_policy_cells=len(cells),unique_leaf_streams=prior.verify_streams(specs),independent_population_batches=5,process_repeats=2,
        max_clipped_calibration_observations=int(all_fits.calibration_n_clipped.max()),
        active_constraint_fits=int(all_fits.fit_active_constraints.ne('none').sum()),
        fit_settings=asdict(audit.SETTINGS),fit_settings_fingerprint=audit.SETTINGS.fingerprint(),
        interval_method='Average process repeats within population batch; paired t interval over five independent batches')
    (out/'validation_summary.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation,indent=2))


if __name__=='__main__': main()
