"""Reproducible paired evaluation of legacy and monotone Bayesian surrogates."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from comfort_boundary_bo_research_package.simulation import run_uncertain_input_bo_extended as sim
from comfort_boundary_bo_research_package.simulation.monotone_bayes import MonotoneBayesianLogistic, PriorGrid
from long_horizon_audit.scripts.run_multiseed_simulation_audit import t_interval_95

KEYS=["seed","scenario","execution_noise","algorithm"]
METRICS=["mean_boundary_error","mean_unacceptable_trials","mean_cumulative_discomfort","mean_predictive_brier_score"]
MATCHED_SETTINGS=["n_participants","n_trials_per_algorithm_participant","tau",
                  "feedback_noise","calibration_bias","include_time_effects"]
SIM_DIR=ROOT/"comfort_boundary_bo_research_package/simulation"
AUDIT_DIR=ROOT/"long_horizon_audit/derived"


def paired_effects(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    required=set(KEYS+METRICS+MATCHED_SETTINGS+["surrogate_kind"])
    for frame,expected in ((old,"legacy_kernel"),(new,"monotone_bayes")):
        if not required.issubset(frame.columns):
            raise ValueError(f"Missing comparison columns: {sorted(required-set(frame.columns))}")
        if frame[KEYS+MATCHED_SETTINGS].isna().any().any():
            raise ValueError("Comparison settings must not be missing")
        if not frame.surrogate_kind.eq(expected).all():
            raise ValueError(f"Expected model identity {expected}")
    paired=old.merge(new,on=KEYS,suffixes=("_old","_new"),how="outer",validate="one_to_one",indicator=True)
    if not paired["_merge"].eq("both").all(): raise ValueError("All scenario/seed/algorithm pairs must match")
    for setting in MATCHED_SETTINGS:
        if not paired[f"{setting}_old"].eq(paired[f"{setting}_new"]).all():
            raise ValueError(f"Comparison setting differs: {setting}")
    paired=paired[paired.scenario.str.startswith("multiseed_")]
    rows=[]
    for (noise,algorithm),group in paired.groupby(["execution_noise","algorithm"]):
        for metric in METRICS:
            change=group[f"{metric}_new"]-group[f"{metric}_old"]
            lo,hi=t_interval_95(change)
            rows.append(dict(execution_noise=noise,algorithm=algorithm,metric=metric,
                n_seeds=len(group),legacy_mean=float(group[f"{metric}_old"].mean()),
                bayesian_mean=float(group[f"{metric}_new"].mean()),mean_change=float(change.mean()),
                ci95_low=lo,ci95_high=hi))
    return pd.DataFrame(rows)


def same_history_replay(trials: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (scenario,pid,algorithm),group in trials.groupby(["scenario","participant_id","algorithm"]):
        group=group.sort_values("trial_id")
        history=[]; briers={kind:[] for kind in ("legacy_kernel","monotone_bayes")}
        models={}
        for row in group.to_dict("records"):
            for kind in briers:
                models[kind]=sim.fit_surrogate_from_history(sim.Config(tau=row["tau"],surrogate_kind=kind),history)
                prediction,_=models[kind].predict(row["realized_intensity"])
                briers[kind].append((prediction-int(row["acceptable"]))**2)
            history.append(row)
        truth=float(group.criterion_boundary_tau.iloc[-1])
        item=dict(scenario=scenario,execution_noise=group.execution_noise.iloc[0],participant_id=pid,algorithm=algorithm)
        for kind in briers:
            model=sim.fit_surrogate_from_history(sim.Config(tau=float(group.tau.iloc[-1]),surrogate_kind=kind),history)
            item[f"{kind}_boundary_error"]=abs(model.estimate_boundary()-truth)
            item[f"{kind}_brier"]=float(np.mean(briers[kind]))
        rows.append(item)
    return pd.DataFrame(rows)


def numerical_and_prior_checks(trials: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    fine_grid=PriorGrid(midpoint_nodes=241,slope_nodes=121)
    broad_grid=PriorGrid(midpoint_sd=1.,log_slope_sd=1.)
    for (scenario,pid,algorithm),group in trials.groupby(["scenario","participant_id","algorithm"]):
        group=group.sort_values("trial_id"); tau=float(group.tau.iloc[-1])
        x,y=group.realized_intensity.to_numpy(),group.acceptable.astype(int).to_numpy()
        base=MonotoneBayesianLogistic(tau).fit(x,y)
        fine=MonotoneBayesianLogistic(tau,grid=fine_grid).fit(x,y)
        broad=MonotoneBayesianLogistic(tau,grid=broad_grid).fit(x,y)
        a,b=base.boundary_summary(),fine.boundary_summary()
        check_x=np.linspace(.2,2.35,13)
        p,_=base.predict_array(check_x); q,_=fine.predict_array(check_x)
        truth=float(group.criterion_boundary_tau.iloc[-1])
        rows.append(dict(scenario=scenario,participant_id=pid,algorithm=algorithm,
            boundary_grid_delta=abs(base.estimate_boundary()-fine.estimate_boundary()),
            ci_lower_grid_delta=abs(a["boundary_ci95_lower"]-b["boundary_ci95_lower"]),
            ci_upper_grid_delta=abs(a["boundary_ci95_upper"]-b["boundary_ci95_upper"]),
            max_probability_grid_delta=float(np.max(abs(p-q))),
            posterior_grid_edge_mass=a["posterior_grid_edge_mass"],
            default_boundary_error=abs(base.estimate_boundary()-truth),
            broad_prior_boundary_error=abs(broad.estimate_boundary()-truth),
            broad_prior_boundary_shift=broad.estimate_boundary()-base.estimate_boundary()))
    return pd.DataFrame(rows)


def prior_predictive_check(repeats: int=100) -> pd.DataFrame:
    """Coverage diagnostic under the actual finite-grid model, not vehicle data."""
    rng=np.random.default_rng(20261104)
    prior=MonotoneBayesianLogistic(.7)
    x=np.linspace(.35,1.9,12); rows=[]
    for repeat in range(repeats):
        index=int(rng.choice(len(prior.posterior_weights),p=prior.posterior_weights))
        midpoint=float(prior.posterior_midpoints[index]); beta=float(prior.posterior_slopes[index])
        p=1/(1+np.exp(-beta*(midpoint-x)))
        y=(rng.random(len(x))<p).astype(int)
        fit=MonotoneBayesianLogistic(.7).fit(x,y); summary=fit.boundary_summary()
        truth=midpoint-math.log(.7/.3)/beta
        rows.append(dict(replicate=repeat+1,true_boundary=truth,estimate=fit.estimate_boundary(),
            ci95_lower=summary["boundary_ci95_lower"],ci95_upper=summary["boundary_ci95_upper"],
            covered=summary["boundary_ci95_lower"]<=truth<=summary["boundary_ci95_upper"],
            support=summary["boundary_support"]))
    return pd.DataFrame(rows)


def check_fixed_policies(old: pd.DataFrame,new: pd.DataFrame) -> dict:
    fixed=["RandomContinuous","GridContinuous","Staircase"]
    keys=["scenario","algorithm","participant_id","trial_id"]
    cols=keys+["target_command_x","realized_intensity","acceptable","discomfort","p_accept_true"]
    a=old.loc[old.algorithm.isin(fixed),cols].sort_values(keys).reset_index(drop=True)
    b=new.loc[new.algorithm.isin(fixed),cols].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b,check_exact=False,rtol=0,atol=1e-12)
    return {"rows":len(a),"invariant":True}


def figures(effects: pd.DataFrame,trials: pd.DataFrame,out: Path) -> None:
    labels=["Uncertain-input","Naive continuous","Random","Grid","Staircase"]
    fig,axes=plt.subplots(2,2,figsize=(13,9))
    for col,noise in enumerate(("low","high")):
        for row,(metric,ylabel) in enumerate((("mean_boundary_error","Mean absolute boundary error"),("mean_unacceptable_trials","Unacceptable trials / 12"))):
            ax=axes[row,col]
            sub=effects[(effects.execution_noise==noise)&(effects.metric==metric)].set_index("algorithm").reindex(sim.ALGORITHM_ORDER)
            x=np.arange(5)
            ax.bar(x-.18,sub.legacy_mean,width=.36,color="#8d99a6",label="Legacy kernel")
            ax.bar(x+.18,sub.bayesian_mean,width=.36,color="#2166ac",label="Monotone Bayesian")
            ax.set_xticks(x,labels,rotation=20,ha="right"); ax.set_ylabel(ylabel)
            ax.set_title(f"{noise.capitalize()} execution noise"); ax.grid(axis="y",alpha=.2)
    handles,legends=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,legends,loc="upper center",bbox_to_anchor=(.5,.96),ncol=2)
    fig.suptitle("Surrogate replacement | Five process seeds, fixed synthetic population",fontsize=15)
    fig.text(.5,.01,"Same budgets and generator; Bayesian models may change adaptive decisions. Lower is better on both axes.",ha="center",fontsize=10)
    fig.tight_layout(rect=(0,.04,1,.91)); fig.savefig(out/"surrogate_before_after.png",dpi=170); plt.close(fig)

    group=trials[(trials.scenario=="continuous_low_noise")&(trials.participant_id==1)&(trials.algorithm=="UncertainInputBO")].sort_values("trial_id")
    model=MonotoneBayesianLogistic(.7).fit(group.realized_intensity,group.acceptable.astype(int))
    x=np.linspace(.2,2.35,200); mean,sd=model.predict_array(x)
    fig,ax=plt.subplots(figsize=(8,5))
    ax.plot(x,mean,label="Posterior mean P(accept)",color="#2166ac")
    ax.fill_between(x,np.clip(mean-sd,0,1),np.clip(mean+sd,0,1),alpha=.18,label="Probability mean +/- posterior SD")
    ax.scatter(group.realized_intensity,group.acceptable.astype(int),c="#333333",s=25,label="Observed binary feedback")
    ax.axhline(.7,ls=":",color="black",label="tau = 0.70")
    summary=model.boundary_summary()
    ax.axvspan(summary["boundary_ci95_lower"],summary["boundary_ci95_upper"],color="#e69f00",alpha=.14,label="95% boundary credible interval")
    ax.axvline(model.estimate_boundary(),color="#e69f00",ls="--",label="Posterior median boundary")
    ax.set(xlabel="Realized intensity",ylabel="Acceptance probability",ylim=(-.05,1.05),title="Example synthetic passenger: monotone posterior and boundary uncertainty")
    ax.legend(fontsize=8,loc="lower left"); ax.grid(alpha=.15)
    fig.tight_layout(); fig.savefig(out/"example_monotone_posterior.png",dpi=180); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=ROOT/"results/monotone_bayes_20261104")
    args=parser.parse_args(); out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    old=pd.read_csv(AUDIT_DIR/"simulation_audit_legacy_comparison_20261104/simulation_audit_per_run_metrics.csv")
    new=pd.read_csv(AUDIT_DIR/"simulation_audit_bayesian_20261104/simulation_audit_per_run_metrics.csv")
    effects=paired_effects(old,new); effects.to_csv(out/"paired_seed_effects.csv",index=False)
    original=pd.read_csv(AUDIT_DIR/"simulation_audit_corrected_20261104/simulation_audit_per_run_metrics.csv")
    merged=original.merge(old,on=KEYS,suffixes=("_archived","_rerun"),validate="one_to_one")
    for metric in ["mean_boundary_error","mean_unacceptable_trials","mean_cumulative_discomfort"]:
        np.testing.assert_allclose(merged[f"{metric}_archived"],merged[f"{metric}_rerun"],rtol=0,atol=1e-12)
    baseline=pd.read_csv(SIM_DIR/"outputs_continuous/continuous_trials.csv")
    bayes=pd.read_csv(SIM_DIR/"outputs_bayesian/continuous_trials.csv")
    invariance=check_fixed_policies(baseline,bayes)
    print("Replaying identical legacy histories...",flush=True)
    replay=same_history_replay(baseline); replay.to_csv(out/"same_history_replay.csv",index=False)
    replay.groupby(["execution_noise","algorithm"]).mean(numeric_only=True).to_csv(out/"same_history_summary.csv")
    print("Checking all extended final posteriors against doubled grid and broader prior...",flush=True)
    checks=numerical_and_prior_checks(bayes); checks.to_csv(out/"numerical_and_prior_checks.csv",index=False)
    calibration=prior_predictive_check(); calibration.to_csv(out/"prior_predictive_coverage.csv",index=False)
    numerical_limits={"boundary_grid_delta":.03,"ci_lower_grid_delta":.04,"ci_upper_grid_delta":.04,"max_probability_grid_delta":.005}
    maxima={key:float(checks[key].max()) for key in numerical_limits}
    numerical_pass=all(maxima[key]<=limit for key,limit in numerical_limits.items())
    summary={"synthetic_only":True,"fixed_policy_trajectory_check":invariance,
        "legacy_audit_rows_reproduced":len(merged),"same_history_fits":len(replay),
        "resolution_checks":len(checks),"resolution_limits":numerical_limits,
        "resolution_maxima":maxima,"resolution_pass":numerical_pass,
        "max_posterior_grid_edge_mass":float(checks.posterior_grid_edge_mass.max()),
        "mean_absolute_broad_prior_shift":float(checks.broad_prior_boundary_shift.abs().mean()),
        "prior_predictive_replicates":len(calibration),"prior_predictive_coverage":float(calibration.covered.mean())}
    (out/"validation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    figures(effects,bayes,out)
    print(json.dumps(summary,indent=2),flush=True)
    print(effects[effects.metric=="mean_boundary_error"].round(6).to_string(index=False))
    if not numerical_pass: raise SystemExit("Posterior grid precision thresholds failed; refine before interpreting results")


if __name__=="__main__": main()
