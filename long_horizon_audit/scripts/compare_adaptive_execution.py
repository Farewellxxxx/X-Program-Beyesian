"""Strict validation and population-batch comparisons for posterior execution."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from long_horizon_audit.scripts import run_adaptive_execution_audit as audit
from long_horizon_audit.scripts import compare_flexible_execution as previous
prior=previous.prior
OUTPUT=ROOT/'results/adaptive_execution_20261104'
DIAGNOSTICS=[*prior.DIAGNOSTICS,'holdout_interval90_coverage','interval90_width','interval90_score','training_accel_mean_rmse']


def check_metadata(rows,metadata):
    if rows.empty: raise ValueError('Missing metadata rows')
    for key,value in metadata.items():
        if key not in rows: raise ValueError('Missing metadata: '+key)
        same=np.allclose(rows[key],value,rtol=0,atol=1e-12) if isinstance(value,float) else rows[key].eq(value).all()
        if not same: raise ValueError('Metadata differs: '+key)


def validate_predictive(rows,specs,n_samples):
    prior.validate_diagnostics(rows,specs,n_samples)
    check_metadata(rows,dict(holdout_samples=n_samples,holdout_namespace=audit.diagnostic.HOLDOUT_NAMESPACE))
    columns=['interval90_lower','interval90_upper',*DIAGNOSTICS]
    if not np.isfinite(rows[columns]).all().all(): raise ValueError('Nonfinite predictive diagnostic')
    if (rows[DIAGNOSTICS]<0).any().any() or (rows.holdout_interval90_coverage>1).any(): raise ValueError('Invalid predictive range')
    if not np.allclose(rows.interval90_width,rows.interval90_upper-rows.interval90_lower,atol=1e-12,rtol=0): raise ValueError('Inconsistent interval width')
    if (rows.interval90_score<rows.interval90_width-1e-12).any(): raise ValueError('Invalid interval score')


def validate_bundle(results,calibration,diagnostics,fits,old_calibration,specs,n_samples=4096):
    prior.validate_results(results,specs); prior.validate_calibration(calibration,specs)
    if set(diagnostics.variant)!=set(audit.VARIANTS): raise ValueError('Diagnostic variant set differs')
    for variant in audit.VARIANTS: validate_predictive(diagnostics[diagnostics.variant==variant],specs,n_samples)
    expected={s.config.scenario_name:s for s in specs}
    if fits.scenario.duplicated().any() or set(fits.scenario)!=set(expected): raise ValueError('Fit scenario set differs')
    for scenario,spec in expected.items():
        obs=calibration[calibration.scenario==scenario].sort_values('calibration_trial')
        reference=old_calibration[old_calibration.scenario==scenario].sort_values('calibration_trial')
        if not np.array_equal(obs[audit.old.sim.CALIBRATION_FIELDS].to_numpy(),reference[audit.old.sim.CALIBRATION_FIELDS].to_numpy()): raise ValueError('Calibration differs from baseline')
        prepared=audit.model.upgrade_prepared(audit.old.stress.prepare_stress_execution(spec.config,spec.distortion,obs),audit.SETTINGS)
        metadata=audit.metadata_for(spec,prepared)
        for frame in (results,calibration,diagnostics,fits): check_metadata(frame[frame.scenario==scenario],metadata)
        for variant,belief in audit.prediction_models(prepared).items():
            rows=diagnostics[(diagnostics.scenario==scenario)&(diagnostics.variant==variant)]
            check_metadata(rows,audit.variant_metadata(variant,belief,prepared))
    return len(expected)


def paired(before,after,metric,algorithm_change=False):
    columns=list(dict.fromkeys(['population_block','process_repeat','algorithm',*prior.MATCHED,'truth_fingerprint',metric]))
    return prior.paired_difference(before[columns],after[columns],metric,allow_algorithm_change=algorithm_change)


def compute_tables(old,new,diagnostics):
    old=old.assign(estimator='quadratic_covariance'); new=new.assign(estimator='adaptive_posterior')
    summary=[]; effects=[]; diagnostic_summary=[]; diagnostic_effects=[]
    for (estimator,profile,arm,algorithm),rows in pd.concat([old,new]).groupby(['estimator','profile','arm','algorithm']):
        for metric in prior.METRICS:
            summary.append(dict(estimator=estimator,profile=profile,arm=arm,algorithm=algorithm,metric=metric,**prior.summarize_clusters(rows,metric)))
    for (profile,arm,algorithm),rows in new.groupby(['profile','arm','algorithm']):
        refs=[('new_vs_old',old[(old.profile==profile)&(old.arm==arm)&(old.algorithm==algorithm)],False)]
        if arm!='cal40': refs.append(('new_vs_new_cal40',new[(new.profile==profile)&(new.arm=='cal40')&(new.algorithm==algorithm)],False))
        if algorithm=='UncertainInputBO': refs.append(('uncertain_vs_naive',new[(new.profile==profile)&(new.arm==arm)&(new.algorithm=='NaiveContinuousBO')],True))
        for label,reference,alg_change in refs:
            if label=='new_vs_old': previous.validate_observation_pairs(reference,rows)
            for metric in prior.METRICS:
                effects.append(dict(contrast=label,profile=profile,arm=arm,algorithm=algorithm,metric=metric,**paired(reference,rows,metric,alg_change)))
    keys=['variant','profile','arm','region','population_block','process_repeat',*prior.MATCHED,'truth_fingerprint','calibration_fingerprint']
    means=diagnostics.groupby(keys,as_index=False)[DIAGNOSTICS].mean(); means['algorithm']='execution_distribution'
    for (variant,profile,arm,region),rows in means.groupby(['variant','profile','arm','region']):
        for metric in DIAGNOSTICS:
            diagnostic_summary.append(dict(estimator=variant,profile=profile,arm=arm,region=region,metric=metric,**prior.summarize_clusters(rows,metric)))
    pairs=[('new_vs_old','quadratic_covariance','adaptive_posterior'),
        ('posterior_family_plugin','quadratic_covariance','quadratic_plugin'),
        ('complexity_plugin','quadratic_plugin','adaptive_plugin'),
        ('complexity_posterior','quadratic_posterior','adaptive_posterior'),
        ('uncertainty_quadratic','quadratic_plugin','quadratic_posterior'),
        ('uncertainty_adaptive','adaptive_plugin','adaptive_posterior'),
        ('new_vs_oracle','oracle','adaptive_posterior')]
    for (profile,arm,region),group in means.groupby(['profile','arm','region']):
        for label,before,after in pairs:
            a=group[group.variant==before]; b=group[group.variant==after]
            previous.validate_observation_pairs(a,b)
            for metric in DIAGNOSTICS:
                diagnostic_effects.append(dict(contrast=label,profile=profile,arm=arm,region=region,metric=metric,**paired(a,b,metric)))
    return tuple(map(pd.DataFrame,(summary,effects,diagnostic_summary,diagnostic_effects)))


def validate_sensitivity(directory,calibration):
    specs=audit.sensitivity_specs()
    expected=dict(settings={k:asdict(v) for k,v in audit.SENSITIVITY.items()},scenarios=[asdict(s) for s in specs],diagnostic_samples=4096)
    actual=json.loads((directory/'sensitivity_configurations.json').read_text(encoding='utf-8'))
    if expected!=actual: raise ValueError('Sensitivity manifest differs')
    fits=pd.read_csv(directory/'sensitivity_fits.csv',float_precision='round_trip')
    diagnostics=pd.read_csv(directory/'sensitivity_diagnostics.csv',float_precision='round_trip')
    if set(fits.sensitivity)!=set(audit.SENSITIVITY) or set(diagnostics.sensitivity)!=set(audit.SENSITIVITY): raise ValueError('Sensitivity setting set differs')
    for name,settings in audit.SENSITIVITY.items():
        fit=fits[fits.sensitivity==name]; diag=diagnostics[diagnostics.sensitivity==name]
        expected_scenarios={s.config.scenario_name for s in specs}
        if fit.scenario.duplicated().any() or set(fit.scenario)!=expected_scenarios: raise ValueError('Sensitivity fit cells differ')
        validate_predictive(diag,specs,4096)
        for spec in specs:
            obs=calibration[calibration.scenario==spec.config.scenario_name].sort_values('calibration_trial')
            prepared=audit.model.upgrade_prepared(audit.old.stress.prepare_stress_execution(spec.config,spec.distortion,obs),settings)
            metadata=audit.metadata_for(spec,prepared)
            check_metadata(fit[fit.scenario==spec.config.scenario_name],metadata)
            check_metadata(diag[diag.scenario==spec.config.scenario_name],{**metadata,**audit.variant_metadata(audit.model.ESTIMATOR,prepared.belief,prepared)})
    means=diagnostics.groupby(['sensitivity','scenario','profile','arm','region'],as_index=False)[DIAGNOSTICS].mean()
    effects=[]
    for (scenario,profile,arm,region),group in means.groupby(['scenario','profile','arm','region']):
        reference=group[group.sensitivity=='default'].iloc[0]
        for _,row in group[group.sensitivity!='default'].iterrows():
            for metric in DIAGNOSTICS:
                effects.append(dict(scenario=scenario,profile=profile,arm=arm,region=region,sensitivity=row.sensitivity,metric=metric,
                    old_mean=reference[metric],new_mean=row[metric],change=row[metric]-reference[metric]))
    return fits,pd.DataFrame(effects)


def plot_tables(summary,diagnostics,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    budgets=list(audit.old.BUDGETS); arms=[f'cal{n}' for n in budgets]
    jobs=[('mean_boundary_error','Absolute B_tau error',summary,{'algorithm':'UncertainInputBO'},'budget_boundary_error.png'),
        ('mean_unacceptable_trials','Unacceptable feedback / 12',summary,{'algorithm':'UncertainInputBO'},'budget_unacceptable_trials.png'),
        ('mean_abs_error','Mean intensity prediction absolute error',diagnostics,{'region':'extrapolation'},'extrapolation_mean_error.png'),
        ('holdout_interval90_coverage','Independent 90% predictive coverage',diagnostics,{'region':'extrapolation'},'extrapolation_coverage.png'),
        ('interval90_width','90% predictive interval width',diagnostics,{'region':'extrapolation'},'extrapolation_width.png'),
        ('interval90_score','90% interval score (lower is better)',diagnostics,{'region':'extrapolation'},'extrapolation_score.png')]
    for metric,label,source,extra,file in jobs:
        fig,axes=plt.subplots(2,4,figsize=(16,8))
        for ax,profile in zip(axes.flat,audit.old.PROFILES):
            rows=source[(source.profile==profile)&(source.metric==metric)]
            for key,value in extra.items(): rows=rows[rows[key]==value]
            variants=[('quadratic_covariance','#d95f02','Previous quadratic fit'),('adaptive_posterior','#2166ac','Adaptive posterior')]
            if source is diagnostics: variants += [('quadratic_posterior','#7570b3','Fixed quadratic posterior'),('oracle','#555555','Oracle')]
            for estimator,color,name in variants:
                values=rows[rows.estimator==estimator].set_index('arm').loc[arms]
                ax.errorbar(budgets,values['mean'],yerr=[values['mean']-values.ci95_low,values.ci95_high-values['mean']],
                    marker='o',capsize=2,color=color,label=name,linestyle='--' if estimator=='oracle' else '-')
            if metric=='holdout_interval90_coverage': ax.axhline(.9,color='#999999',linestyle=':')
            ax.set_xscale('log'); ax.set_xticks(budgets,[str(n) for n in budgets]); ax.grid(alpha=.2)
            ax.set_title(profile.replace('_',' ')); ax.set_xlabel('Calibration maneuvers'); ax.set_ylabel(label)
        axes.flat[-1].axis('off'); axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(),loc='center')
        fig.suptitle(label+' | means and 95% population-batch intervals')
        fig.tight_layout(rect=(0,0,1,.95)); fig.savefig(out/file,dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',type=Path,default=audit.OUTPUT)
    parser.add_argument('--baseline-dir',type=Path,default=audit.baseline.OUTPUT)
    parser.add_argument('--output-dir',type=Path,default=OUTPUT)
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    read=lambda p:pd.read_csv(p,float_precision='round_trip')
    specs=audit.build_scenarios(); old_frames=[]; new_frames=[]; diags=[]; fits=[]; calibrations=[]; count=0
    for profile in audit.old.PROFILES:
        selected=[s for s in specs if s.profile==profile]
        for prefix,replay in [(profile,False),('replay_'+profile,True)]:
            actual=json.loads((args.input_dir/f'{prefix}_configurations.json').read_text(encoding='utf-8'))
            if actual!=audit.manifest(selected,replay=replay): raise ValueError('Manifest differs: '+prefix)
        baseline_manifest=json.loads((args.baseline_dir/f'{profile}_configurations.json').read_text(encoding='utf-8'))
        if baseline_manifest!=audit.baseline.manifest(selected,5,2): raise ValueError('Baseline manifest differs')
        before=read(args.baseline_dir/f'{profile}_per_run.csv'); prior.validate_results(before,selected)
        replay=read(args.input_dir/f'replay_{profile}_per_run.csv'); previous.validate_replay(before,replay)
        old_cal=read(args.baseline_dir/f'{profile}_calibration.csv')
        new=read(args.input_dir/f'{profile}_per_run.csv'); cal=read(args.input_dir/f'{profile}_calibration.csv')
        diag=read(args.input_dir/f'{profile}_diagnostics.csv'); fit=read(args.input_dir/f'{profile}_fits.csv')
        count+=validate_bundle(new,cal,diag,fit,old_cal,selected)
        # Original paired-innovation metrics must reproduce the frozen diagnostic table exactly.
        baseline_diag=read(args.baseline_dir/f'{profile}_diagnostics.csv').sort_values(['scenario','command'])
        current_diag=diag[diag.variant=='quadratic_covariance'].sort_values(['scenario','command'])
        fields=['scenario','command',*prior.DIAGNOSTICS]
        if not np.array_equal(baseline_diag[fields].to_numpy(),current_diag[fields].to_numpy()): raise ValueError('Historical diagnostic changed')
        old_frames.append(before); new_frames.append(new); diags.append(diag); fits.append(fit); calibrations.append(cal)
        print(f'VALIDATED {profile}',flush=True)
    old=pd.concat(old_frames,ignore_index=True); new=pd.concat(new_frames,ignore_index=True)
    diagnostics=pd.concat(diags,ignore_index=True); all_fits=pd.concat(fits,ignore_index=True)
    fixed=pd.concat([old,new]); fixed=fixed[fixed.algorithm.isin(['RandomContinuous','GridContinuous','Staircase'])]
    cells=fixed.groupby(['profile','population_block','process_repeat','algorithm']).trajectory_fingerprint.nunique()
    if not cells.eq(1).all(): raise ValueError('Fixed physical trajectories changed')
    summary,effects,diag_summary,diag_effects=compute_tables(old,new,diagnostics)
    sensitivity_fits,sensitivity_effects=validate_sensitivity(args.input_dir,pd.concat(calibrations,ignore_index=True))
    selection=[]
    for (profile,arm),group in all_fits.groupby(['profile','arm']):
        for degree in range(3):
            metric=f'fit_weight_{degree}'
            selection.append(dict(profile=profile,arm=arm,degree=degree,map_count=int(group.fit_map_degree.eq(degree).sum()),
                n_fits=len(group),**prior.summarize_clusters(group,metric)))
    for name,frame in [('population_summary',summary),('paired_effects',effects),('execution_diagnostics_summary',diag_summary),
        ('execution_paired_effects',diag_effects),('execution_fit_parameters',all_fits),('model_selection',pd.DataFrame(selection)),
        ('sensitivity_fit_parameters',sensitivity_fits),('sensitivity_effects',sensitivity_effects)]:
        frame.to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    plot_tables(summary,diag_summary,out)
    validation=dict(new_scenarios=len(specs),replay_scenarios=len(specs),new_policy_rows=len(new),replay_policy_rows=len(old),
        historical_max_metric_delta=0.,historical_max_diagnostic_delta=0.,identical_calibration_sets=count,
        diagnostic_rows=len(diagnostics),diagnostic_variants=list(audit.VARIANTS),holdout_namespace=audit.diagnostic.HOLDOUT_NAMESPACE,
        sensitivity_cells=14,sensitivity_settings=3,fixed_policy_cells=len(cells),unique_leaf_streams=prior.verify_streams(specs),
        independent_population_batches=5,process_repeats=2,max_clipped_calibration_observations=int(all_fits.calibration_n_clipped.max()),
        posterior_settings=asdict(audit.SETTINGS),posterior_settings_fingerprint=audit.SETTINGS.fingerprint(),
        interval_method='Average two repeats within batch; paired t interval across five independent population batches')
    (out/'validation_summary.json').write_text(json.dumps(validation,indent=2),encoding='utf-8'); print(json.dumps(validation,indent=2))


if __name__=='__main__': main()
