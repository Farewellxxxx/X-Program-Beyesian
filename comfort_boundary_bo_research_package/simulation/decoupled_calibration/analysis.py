"""Scenario-specific participant-level paired analysis; no sequential pseudoreplication."""
import argparse
import csv
from collections import defaultdict
import json
import hashlib
from pathlib import Path
import numpy as np

METRICS = ('primary_cost','primary_observed','secondary_cost','secondary_observed',
           'final_absolute_error','final_signed_error','unacceptable_count','unacceptable_rate',
           'overestimated','interval_coverage','interval_width','out_of_domain','unidentifiable')
BOOL_FIELDS = {'primary_observed','secondary_observed','overestimated','interval_coverage',
               'out_of_domain','unidentifiable','covered'}
LOWER_BETTER = {'primary_cost','secondary_cost','final_absolute_error','unacceptable_count',
                'unacceptable_rate','overestimated','interval_width','unidentifiable'}


def paired_bootstrap(a, b, rng, replicates=2000):
    """Percentile CI for mean(a-b), resampling paired people within one cell."""
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    if a.ndim!=1 or b.ndim!=1 or a.shape!=b.shape or len(a)==0:
        raise ValueError('equal nonempty paired vectors required')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('paired values must be finite; failures may not be dropped')
    if isinstance(replicates,bool) or not isinstance(replicates,int) or replicates<1:
        raise ValueError('positive bootstrap replicate count required')
    differences=a-b
    sampled=np.mean(differences[rng.integers(0,len(a),size=(replicates,len(a)))],axis=1)
    low,high=np.quantile(sampled,[.025,.975])
    return dict(difference=float(differences.mean()),lower=float(low),upper=float(high),n_pairs=len(a))


def _read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    for row in rows:
        for key,value in row.items():
            if key in BOOL_FIELDS:
                if value not in ('True','False','1','0'):
                    raise ValueError(f'invalid boolean {key}')
                row[key]=value in ('True','1')
            elif key not in ('scenario','family','execution','method','support','primary_event_trial','secondary_event_trial'):
                if value!='': row[key]=float(value)
    return rows


def _write(path,rows):
    if not rows: return
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summarize_participants(rows):
    groups=defaultdict(list)
    seen=set()
    for r in rows:
        identity=(r['scenario'],r['method'],r['participant'])
        if identity in seen: raise ValueError('duplicate participant-method record')
        seen.add(identity)
        groups[(r['scenario'],r['method'])].append(r)
    output=[]
    for (scenario,method),people in sorted(groups.items()):
        result=dict(scenario=scenario,method=method,n=len(people))
        for endpoint in ('primary','secondary'):
            for person in people:
                cost=float(person[endpoint+'_cost']);budget=float(person['budget'])
                if not 1<=cost<=budget or (not person[endpoint+'_observed'] and cost!=budget):
                    raise ValueError('censored participants must retain budget cost')
            result[endpoint+'_success_fraction']=float(np.mean([r[endpoint+'_observed'] for r in people]))
            result[endpoint+'_censored']=sum(not r[endpoint+'_observed'] for r in people)
            result[endpoint+'_cost_mean']=float(np.mean([r[endpoint+'_cost'] for r in people]))
        for metric in METRICS[4:]:
            values=np.array([r[metric] for r in people],dtype=float)
            if not np.isfinite(values).all(): raise ValueError('nonfinite participant summary')
            result[metric+'_mean']=float(values.mean())
        output.append(result)
    return output


def _paired_effects(rows,replicates,seed):
    cells=defaultdict(lambda:defaultdict(dict))
    for r in rows: cells[r['scenario']][r['method']][r['participant']]=r
    rng=np.random.default_rng(seed)
    effects=[]
    for scenario,methods in sorted(cells.items()):
        if 'bayes_risk' not in methods: continue
        base=methods['bayes_risk']
        for comparator,other in sorted(methods.items()):
            if comparator=='bayes_risk': continue
            if set(base)!=set(other): raise ValueError('incomplete within-scenario participant pairs')
            ids=sorted(base)
            for metric in METRICS:
                stats=paired_bootstrap([base[i][metric] for i in ids],[other[i][metric] for i in ids],rng,replicates)
                effects.append(dict(scenario=scenario,comparison='bayes_risk_minus_'+comparator,
                    comparator=comparator,role='ablation' if comparator=='bayes_point' else
                    ('secondary' if comparator=='ucb_tau' else 'primary'),metric=metric,**stats))
    return effects


def _trajectories(rows):
    groups=defaultdict(list)
    seen=set()
    for r in rows:
        identity=(r['scenario'],r['method'],r['participant'],r['trial'])
        if identity in seen: raise ValueError('duplicate trial record')
        seen.add(identity)
        groups[(r['scenario'],r['method'],int(r['trial']))].append(r)
    output=[]
    for (scenario,method,trial),people in sorted(groups.items()):
        output.append(dict(scenario=scenario,method=method,trial=trial,n=len(people),
            mean_absolute_error=float(np.mean([r['absolute_error'] for r in people])),
            median_absolute_error=float(np.median([r['absolute_error'] for r in people])),
            mean_signed_error=float(np.mean([r['signed_error'] for r in people])),
            mean_interval_width=float(np.mean([r['interval_width'] for r in people])),
            coverage=float(np.mean([r['covered'] for r in people])),
            unacceptable_fraction=float(np.mean([1-r['acceptable'] for r in people])),
            mean_edge_mass=float(np.mean([r['edge_mass'] for r in people])),
            unsupported_fraction=float(np.mean([r['support']!='within_observed_range' for r in people]))))
    return output


def _figures(output,summary,trajectories):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    scenarios=sorted({r['scenario'] for r in summary})
    methods=sorted({r['method'] for r in summary})
    colors=dict(zip(methods,plt.get_cmap('tab10').colors))
    fig,axes=plt.subplots(len(scenarios),1,figsize=(9,3*len(scenarios)),squeeze=False)
    for ax,scenario in zip(axes[:,0],scenarios):
        for method in methods:
            own=[r for r in trajectories if r['scenario']==scenario and r['method']==method]
            if own: ax.plot([r['trial'] for r in own],[r['mean_absolute_error'] for r in own],label=method,color=colors[method])
        ax.set(title=scenario,xlabel='Passenger trials',ylabel='Mean absolute error (m/s²)')
        ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=3)
    fig.tight_layout();fig.savefig(output/'accuracy_trajectories.png',dpi=160);plt.close(fig)
    metrics=[('primary_success_fraction','Suffix-stable success fraction'),('primary_cost_mean','Restricted trial cost (failures=budget)'),
             ('final_absolute_error_mean','Final mean absolute error (m/s²)'),('unacceptable_rate_mean','Unacceptable trial fraction'),
             ('interval_coverage_mean','Final 95% interval coverage'),('interval_width_mean','Final interval width (m/s²)')]
    fig,axes=plt.subplots(3,2,figsize=(13,12))
    for ax,(metric,label) in zip(axes.flat,metrics):
        for j,method in enumerate(methods):
            lookup={r['scenario']:r[metric] for r in summary if r['method']==method}
            ax.plot(range(len(scenarios)),[lookup.get(s,np.nan) for s in scenarios],marker='o',label=method,color=colors[method])
        ax.set_xticks(range(len(scenarios)),scenarios,rotation=30,ha='right',fontsize=8)
        ax.set_ylabel(label);ax.grid(alpha=.2)
    axes.flat[0].legend(fontsize=8)
    fig.tight_layout();fig.savefig(output/'scenario_outcomes.png',dpi=160);plt.close(fig)


def _effect_figure(output,effects):
    import matplotlib.pyplot as plt
    selected=[r for r in effects if r['metric']=='primary_cost' and r['role']=='primary']
    if not selected: return
    fig,ax=plt.subplots(figsize=(10,max(4,len(selected)*.4)))
    for i,r in enumerate(selected):
        ax.plot([r['lower'],r['upper']],[i,i],color='tab:blue')
        ax.plot(r['difference'],i,'o',color='tab:blue')
    ax.set_yticks(range(len(selected)),[r['scenario']+' / '+r['comparator'] for r in selected],fontsize=8)
    ax.axvline(0,color='black',linewidth=1)
    ax.set_xlabel('Bayes minus comparator: restricted trial cost (95% paired bootstrap CI)')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    fig.tight_layout();fig.savefig(output/'paired_effects.png',dpi=160);plt.close(fig)


def _narrative(config,summary,effects):
    lines=['# 分情境分析（模拟）','',f"数据划分：{config.get('split','unspecified')}；随机种子：{config.get('seed','unspecified')}。",
        '','以下区间为各情境内按独立乘客重采样的配对百分位 bootstrap 95% 区间；同一乘客的逐试次记录没有当作独立样本。不同情境不混池。',
        '主比较：bayes_risk 对 ucb_tvcg、staircase；ucb_tau 仅次要敏感性分析；bayes_point 为输入不确定性消融。',
        '','## 不利或混合证据（先报告）','',
        '差值均为 bayes_risk 减去比较方法。成本/误差/暴露等负值更好；成功率正值更好。覆盖率需结合名义95%与区间宽度评估，较高也可能表示保守。区间跨零不支持明确方向；区间没有做多重比较校正。']
    selected=[r for r in effects if r['metric'] in ('primary_cost','primary_observed','final_absolute_error','unacceptable_rate')]
    for r in selected:
        unfavorable=(r['difference']>0 if r['metric'] in LOWER_BETTER else r['difference']<0)
        mixed=r['lower']<=0<=r['upper']
        if unfavorable or mixed:
            lines.append(f"- {r['scenario']} / {r['comparator']} ({r['role']}), {r['metric']}: Δ={r['difference']:.4f}, 95% [{r['lower']:.4f}, {r['upper']:.4f}]（{'不利点估计' if unfavorable else '方向不确定'}）。")
    lines += ['','## 全部情境摘要','',
        '| 情境 | 方法 | n | 主成功率 | 主成本 | 最终MAE | 不可接受比例 | 覆盖率 | 区间宽度 |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['scenario']} | {r['method']} | {r['n']} | {r['primary_success_fraction']:.3f} | {r['primary_cost_mean']:.2f} | {r['final_absolute_error_mean']:.3f} | {r['unacceptable_rate_mean']:.3f} | {r['interval_coverage_mean']:.3f} | {r['interval_width_mean']:.3f} |")
    lines += ['','主成本是预算限制成本：达标者取首次主事件试次，未达标者取预算；它不是成功者平均试次数，也不是预算外真实收敛时间的估计。主事件需要事后检查从该试次到预算末端始终达标，不能作为在线停止规则。',
        '所有失败、域外边界和不具辨识支持的记录保留在汇总。检查 scenario_summary.csv 中 censored/out_of_domain/unidentifiable 列。区间宽度较窄不代表覆盖率更好；需联合解读。',
        '完整效应及不确定性见 paired_effects.csv；逐试次描述性统计见 trajectories.csv。模拟试次不是实测耗时，亦不能证明人类比较优势。']
    return '\n'.join(lines)+'\n'


def _validate_grid(config, participants, trials):
    required=('budget','participants_per_cell','families','execution_conditions','methods')
    if not all(key in config for key in required): return
    expected={(f'{family}__{execution}',method,float(person))
        for family in config['families'] for execution in config['execution_conditions']
        for method in config['methods'] for person in range(config['participants_per_cell'])}
    actual={(r['scenario'],r['method'],r['participant']) for r in participants}
    if actual != expected or len(participants)!=len(expected):
        raise ValueError('participant grid differs from frozen config')
    trial_grid=defaultdict(list)
    for r in trials:
        trial_grid[(r['scenario'],r['method'],r['participant'])].append(r['trial'])
    expected_trials=list(range(1,config['budget']+1))
    if set(trial_grid)!=expected or any(sorted(v)!=expected_trials for v in trial_grid.values()):
        raise ValueError('trial grid differs from frozen config; incomplete or duplicate trials')


def analyze(input_dir, output_dir, bootstrap_replicates=None, bootstrap_seed=None):
    input_dir,output_dir=Path(input_dir),Path(output_dir)
    participants=_read(input_dir/'participants.csv');trials=_read(input_dir/'trials.csv')
    if not participants or not trials: raise ValueError('nonempty participant and trial data required')
    config=json.loads((input_dir/'config.json').read_text(encoding='utf-8-sig'))
    bootstrap=config.get('bootstrap',{})
    if bootstrap_replicates is None: bootstrap_replicates=bootstrap.get('replicates',2000)
    if bootstrap_seed is None: bootstrap_seed=bootstrap.get('seed',20261105)
    _validate_grid(config,participants,trials)
    summary=summarize_participants(participants)
    effects=_paired_effects(participants,bootstrap_replicates,bootstrap_seed)
    trajectories=_trajectories(trials)
    output_dir.mkdir(parents=True,exist_ok=True)
    _write(output_dir/'scenario_summary.csv',summary);_write(output_dir/'paired_effects.csv',effects)
    _write(output_dir/'trajectories.csv',trajectories)
    _figures(output_dir,summary,trajectories)
    _effect_figure(output_dir,effects)
    (output_dir/'results_summary_zh.md').write_text(_narrative(config,summary,effects),encoding='utf-8')
    metadata=dict(bootstrap_seed=bootstrap_seed,bootstrap_replicates=bootstrap_replicates,
        interval='paired participant percentile 95%; scenario-specific; unadjusted',
        effect_direction='bayes_risk minus comparator',split=config.get('split','unspecified'),
        cost='restricted event trial or budget for censored; no successful-only deletion')
    (output_dir/'analysis_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    manifest=dict(analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256={name:hashlib.sha256((input_dir/name).read_bytes()).hexdigest()
                      for name in ('trials.csv','participants.csv','config.json')},
        bootstrap_seed=bootstrap_seed,bootstrap_replicates=bootstrap_replicates,
        figures=[p.name for p in sorted(output_dir.glob('*.png'))],
        figure_data={'accuracy_trajectories.png':'trajectories.csv','scenario_outcomes.png':'scenario_summary.csv','paired_effects.png':'paired_effects.csv'})
    (output_dir/'postprocessing_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return dict(summary=summary,effects=effects,trajectories=trajectories)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.input,args.output)

if __name__=='__main__': main()
