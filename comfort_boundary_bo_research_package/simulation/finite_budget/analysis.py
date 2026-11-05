"""Validated per-scenario analysis. All failures remain in the paired cohort."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import numpy as np
from .metrics import fixed_budget_summary
from .study import effective_config, validate_run, read_jsonl, canonical, write_json, digest, analysis_hashes


def paired_percentile(a,b,*,seed,draws=20000,confidence=.95,scenarios=6):
    """Participant-paired percentile intervals; no pooling across conditions."""
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('complete finite paired arrays required')
    if draws!=20000 or confidence!=.95 or scenarios!=6: raise ValueError('predeclared bootstrap definitions required')
    rng=np.random.default_rng(seed); values=np.empty(draws); difference=a-b
    # Bound temporary workspace while preserving the single semantic RNG stream.
    for begin in range(0,draws,1000):
        end=min(begin+1000,draws); ids=rng.integers(0,len(a),size=(end-begin,len(a)))
        values[begin:end]=difference[ids].mean(axis=1)
    alpha=1-confidence; adjusted=1-alpha/scenarios
    low,high=np.quantile(values,[alpha/2,1-alpha/2]); blo,bhi=np.quantile(values,[alpha/(2*scenarios),1-alpha/(2*scenarios)])
    return dict(n=len(a),difference=float(difference.mean()),lower_95=float(low),upper_95=float(high),
                lower_bonferroni=float(blo),upper_bonferroni=float(bhi),confidence=confidence,
                confidence_bonferroni=adjusted,bootstrap_draws=draws)


def label_effect_scope(result,split):
    """Six-main-scenario adjustment never becomes a seven-stress family claim."""
    result=dict(result)
    result['evidence_scope']={'development':'development_only','heldout':'heldout_confirmatory',
                              'stress':'exploratory_stress','pilot':'runtime_or_test_pilot','numerical':'numerical_only'}[split]
    result['adjustment_scope']='six main scenarios only'
    if split=='stress':
        for key in ('lower_bonferroni','upper_bonferroni','confidence_bonferroni'): result[key]=None
        result['adjustment_scope']='not applied; per-scenario 95% exploratory stress intervals'
    return result


def _write_rows(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='\n') as stream:
        for r in rows: stream.write(canonical(r)+'\n')


def _bootstrap_seed(seed,key):
    return int.from_bytes(hashlib.sha256(canonical([seed,key]).encode()).digest()[:8],'little')


def analyze_v2(input_dir,output_dir,*,plots=True,verify_readouts=False):
    """Validate full participant/trial/checkpoint grids before creating summaries.

    Optional verify_readouts reconstructs every numerical reader in addition to
    mandatory independent error/support/failure verification from raw prefixes.
    """
    root=Path(input_dir); manifest=validate_run(root,verify_readouts=verify_readouts)
    c=effective_config(root/'effective_config.json'); out=Path(output_dir)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    rows=read_jsonl(root/'checkpoints.jsonl'); grouped=defaultdict(list)
    for r in rows: grouped[(r['scenario'],r['method'],r['track'],r['estimator'],r['budget'])].append(r)
    summaries=[]; sensitivity=[]; failures=[]; primary=c['study']['primary_budget']; delta=c['study']['delta']
    for key,cohort in sorted(grouped.items()):
        sid,mid,track,estimator,budget=key
        identity=dict(scenario=sid,method=mid,track=track,estimator=estimator,budget=budget,label=cohort[0]['label'])
        summary=fixed_budget_summary(cohort,budget,delta,n=c['participants'],success_target=c['study']['success_target'])
        summaries.append(dict(**identity,**{k:v for k,v in summary.items() if k!='budget'},finite_error_condition='conditional on finite numerical output'))
        for tolerance in c['analysis']['sensitivity_deltas']:
            s=fixed_budget_summary(cohort,budget,tolerance,n=c['participants'],success_target=c['study']['success_target'])
            sensitivity.append(dict(**identity,**{k:v for k,v in s.items() if k!='budget'},readout_delta=delta,
                                    sensitivity='evaluation tolerance only; unchanged fixed point estimate and trajectory'))
        status_counts={status:sum(r['status']==status for r in cohort) for status in sorted({r['status'] for r in cohort})}
        failures.append(dict(**identity,n=len(cohort),status_counts=status_counts,failed_count=sum(not r['finite'] for r in cohort),
                             unsupported_count=sum(not r['supported'] for r in cohort),active_bound_count=sum(bool(r['active_bounds']) for r in cohort),
                             out_of_domain_count=sum(r['out_of_domain'] for r in cohort)))
    effects=[]; contrasts=[]; method_ids={m['id'] for m in c['methods']}
    staircase=[m['id'] for m in c['methods'] if m['sampler']=='staircase']
    # Development six-way selection is not a confirmatory primary comparison.
    if 'new_precision' in method_ids and len(staircase)==1:
        contrasts += [('new_precision',staircase[0],track,'primary','new_precision','firth' if track=='pipeline' else 'new_precision') for track in ('pipeline','common')]
    for a,b in [('new_precision','new_variance'),('new_variance','old_variance')]:
        if a in method_ids and b in method_ids: contrasts.append((a,b,'common','secondary_controlled','new_precision','new_precision'))
    if contrasts:
        for scenario in c['scenarios']:
            for method_a,method_b,track,role,estimator_a,estimator_b in contrasts:
                a=grouped.get((scenario['id'],method_a,track,estimator_a,primary))
                b=grouped.get((scenario['id'],method_b,track,estimator_b,primary))
                if a is None or b is None: raise ValueError('missing primary paired contrast')
                a=sorted(a,key=lambda r:r['participant']); b=sorted(b,key=lambda r:r['participant'])
                if [r['participant'] for r in a]!=[r['participant'] for r in b]: raise ValueError('unpaired participants')
                for metric in ('supported_success','capped_absolute_error'):
                    value=lambda r: float(r['supported_success']) if metric=='supported_success' else min(r['abs_error'],3.) if r['finite'] else 3.
                    key=[scenario['id'],track,metric,method_a,method_b]
                    result=paired_percentile([value(r) for r in a],[value(r) for r in b],seed=_bootstrap_seed(c['analysis']['seed'],key))
                    result=label_effect_scope(result,c['study']['split'])
                    effects.append(dict(scenario=scenario['id'],track=track,budget=primary,metric=metric,method_a=method_a,method_b=method_b,
                                        estimator_a=estimator_a,estimator_b=estimator_b,role=role,direction='A minus B',**result))
    observations=read_jsonl(root/'observations.jsonl'); participants={(r['scenario'],r['participant']):r for r in read_jsonl(root/'participants.jsonl')}
    trajectories=defaultdict(list)
    for r in observations: trajectories[(r['scenario'],r['participant'],r['method'])].append(r)
    exposure=[]
    for scenario in c['scenarios']:
        for method in c['methods']:
            for budget in c['study']['checkpoints']:
                per_subject=[]
                for pid in range(c['participants']):
                    prefix=[r for r in trajectories[(scenario['id'],pid,method['id'])] if r['trial']<=budget]
                    B=participants[(scenario['id'],pid)]['B']
                    per_subject.append(dict(rejection_rate=np.mean([1-r['acceptable'] for r in prefix]),
                                            mean_realized=np.mean([r['realized'] for r in prefix]),
                                            above_true_boundary_rate=np.mean([r['realized']>B for r in prefix])))
                exposure.append(dict(scenario=scenario['id'],method=method['id'],budget=budget,n=c['participants'],
                                     **{k:float(np.mean([r[k] for r in per_subject])) for k in per_subject[0]},
                                     label='simulation exposure diagnostic; truth never enters policy'))
    stop_summaries=[]
    stop_groups=defaultdict(list)
    for r in read_jsonl(root/'stops.jsonl'): stop_groups[(r['scenario'],r['method'])].append(r)
    for (sid,mid),cohort in sorted(stop_groups.items()):
        stopped=[r for r in cohort if r['stopped']]
        stop_summaries.append(dict(scenario=sid,method=mid,n=len(cohort),stop_count=len(stopped),stop_proportion=len(stopped)/len(cohort),
                                   all_participant_mean_capped_cost=float(np.mean([r['capped_cost'] for r in cohort])),
                                   correctness_at_stop=sum(r['correct'] for r in stopped)/len(stopped) if stopped else None,
                                   numerical_failure_at_stop=sum(not r['finite'] for r in stopped)/len(stopped) if stopped else None,
                                   true_error_failure_at_stop=sum(not r['correct'] for r in stopped)/len(stopped) if stopped else None,
                                   conditional_mean_abs_error_at_stop=float(np.mean([r['abs_error'] for r in stopped if r['finite']])) if stopped else None,
                                   label='common posterior replay; Firth has no matched posterior stopping rule'))
    _write_rows(out/'fixed_budget.jsonl',summaries)
    _write_rows(out/'pipeline.jsonl',[r for r in summaries if r['track']=='pipeline'])
    _write_rows(out/'common.jsonl',[r for r in summaries if r['track']=='common'])
    _write_rows(out/'delta_sensitivity.jsonl',sensitivity); _write_rows(out/'paired_effects.jsonl',effects)
    _write_rows(out/'applicability_failures.jsonl',failures); _write_rows(out/'exposure.jsonl',exposure); _write_rows(out/'stop_replay.jsonl',stop_summaries)
    frozen=json.loads((root/'freeze.json').read_text(encoding='utf-8')) if (root/'freeze.json').exists() else manifest
    artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file() and p.suffix in ('.json','.jsonl')}
    result=dict(version=2,input_dir=str(root.resolve()),input_config_sha256=digest(c),input_source_hashes=manifest['source_hashes'],
                actual_analysis_source_hashes=analysis_hashes(),frozen_analysis_source_hashes=frozen['analysis_source_hashes'],input_artifact_sha256=artifacts,
                primary_budget=primary,delta=delta,success_target=c['study']['success_target'],participants_per_scenario=c['participants'],
                condition_cases=c['participants']*len(c['scenarios']),independent_latent_draws=manifest['latent_draws'],
                feedback_count=manifest['feedback_count'],separate_calibration_count=manifest['calibration_count'],
                bootstrap_draws=20000,confidence=.95,bonferroni_confidence=None if c['study']['split']=='stress' else 1-.05/6,
                evidence_scope=label_effect_scope({},c['study']['split'])['evidence_scope'],
                adjustment_scope=label_effect_scope({},c['study']['split'])['adjustment_scope'],
                independent_readouts_reconstructed=verify_readouts,all_outcome_classifications_recomputed=True,
                sensitivity='same frozen trajectory and fixed point estimate; precision readers retain primary z_.15; tolerance only',plots=[])
    if plots: result['plots']=_plots(out,summaries,exposure,c)
    write_json(out/'analysis_manifest.json',result)
    _report(out,c,summaries,effects,result)
    return result


def _plots(out,summaries,exposure,c):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    paths=[]
    for track in ('pipeline','common'):
        for scenario in c['scenarios']:
            fig,axes=plt.subplots(2,2,figsize=(11,7))
            for method in c['methods']:
                series=[r for r in summaries if r['scenario']==scenario['id'] and r['method']==method['id'] and r['track']==track
                        and (track!='common' or r['estimator']=='new_precision')]
                series.sort(key=lambda r:r['budget'])
                if not series: continue
                x=[r['budget'] for r in series]; label=series[0]['label']
                for ax,metric in zip(axes.flat[:3],('supported_success_rate','finite_mae','finite_p90_error')):
                    ax.plot(x,[r[metric] for r in series],marker='o',label=label)
                exp=sorted([r for r in exposure if r['scenario']==scenario['id'] and r['method']==method['id']],key=lambda r:r['budget'])
                axes.flat[3].plot([r['budget'] for r in exp],[r['rejection_rate'] for r in exp],marker='o',label=label)
            titles=('Supported success (all participants)','MAE | finite output (see failure table)','P90 | finite output (see failure table)','Observed rejection exposure')
            for ax,title in zip(axes.flat,titles): ax.set(title=title,xlabel='Feedback budget'); ax.grid(alpha=.2)
            axes.flat[0].axhline(c['study']['success_target'],linestyle='--',color='gray')
            axes.flat[0].set_ylim(0,1); axes.flat[3].set_ylim(0,1)
            handles,labels=axes.flat[0].get_legend_handles_labels()
            if handles: fig.legend(handles,labels,loc='lower center',fontsize=6,ncol=2)
            fig.suptitle(f"{scenario['id']} / {track}"); fig.tight_layout(rect=(0,.12,1,.95))
            name=f"{track}_{scenario['id']}.png"; fig.savefig(out/name,dpi=150); plt.close(fig); paths.append(name)
    return paths


def _report(out,c,summaries,effects,result):
    primary=c['study']['primary_budget']; main=[r for r in summaries if r['budget']==primary and r['track'] in ('pipeline','common')]
    lines=['# 有限预算校准：逐场景仿真结果','',
           f"固定主预算 N={primary}，容限 δ={c['study']['delta']}，目标支持成功率 {c['study']['success_target']:.0%}。每场景 {c['participants']} 个配对基础参与者。",
           f"反馈 {result['feedback_count']} 次；另有执行校准 {result['separate_calibration_count']} 次。跨反应族复用基础 B/W，不将条件案例数解释为独立人数。",'',
           '成功必须同时满足数值正常、两种回答、估计在已观测实际强度范围内及误差不超过容限。全部失败仍在分母。仅当双侧95% Wilson下限达到目标才通过。','',
           '|场景|采样器 + 读出|支持成功率 [95% Wilson]|失败/总数|有限输出 MAE / P90|是否通过|',
           '|---|---|---|---|---|---|']
    fmt=lambda v:'缺失' if v is None or not np.isfinite(v) else f'{v:.3f}'
    for r in main:
        lines.append(f"|{r['scenario']}|{r['label']}|{r['supported_success_rate']:.3f} [{r['wilson_lower']:.3f}, {r['wilson_upper']:.3f}]|{r['failure_count']}/{r['n']}|{fmt(r['finite_mae'])} / {fmt(r['finite_p90_error'])}|{'是' if r['meets_target'] else '证据不足'}|")
    lines += ['', 'A层是完整流程；B层是共同新先验估计器。UCB最大Q命令和阶梯反转均值另存诊断，未混入实际边界误差排名。原版BO原生旧先验中位数另存历史参照。',
              ('压力条件仅报告各场景95%探索性配对区间；不把六主场景Bonferroni修正用于七压力条件。' if c['study']['split']=='stress' else
               '主对比为新精度BO减阶梯，每场景、每层分别进行20,000次参与者配对百分位bootstrap，保存95%及六主场景Bonferroni99.1667%区间；开发拆解仍仅属于开发证据。'),
              '不跨场景混池，不将区间包含零解释为等效。共同层另有新精度减新方差、新方差减旧方差的预定次要受控对比。',
              'δ=.10/.20仅改变同一主点估计的评价容限。开发先验/读出拆解是开发证据；整体先验变化不能归因于单独居中。',
              '本结果来自固定、静态合成反应曲线及无额外误差的实际强度测量，不能证明真人、道路安全或TVCG原系统性能。压力条件仅在对应独立输出存在时视为已测试。','']
    (out/'report_zh.md').write_text('\n'.join(lines),encoding='utf-8')
