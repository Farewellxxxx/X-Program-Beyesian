"""Deterministic public-history resolution audit; never samples passengers.

Run as a module. Exit 2 means a prescribed numerical tolerance failed; the
JSON remains available for choosing a global resolution before source freeze.
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import numpy as np
from .contracts import PriorSpec
from .boundary_model import BoundaryPosterior
from .acquisition import precision_gain, variance_gain
from ..decoupled_calibration.public import Observation, ExecutionBelief


PUBLIC_HISTORIES = {
    'empty':(),
    'mixed':((.3,1),(.9,1),(1.5,0),(2.1,0)),
    'all_accept':((.3,1),(.9,1),(1.5,1),(2.1,1)),
    'all_reject':((.3,0),(.9,0),(1.5,0),(2.1,0)),
    'opposing':((.3,0),(2.1,1)),
}


def _snapshot(history,prior,tau,delta,targets,belief,nodes):
    posterior=BoundaryPosterior(tau,prior)
    for t,(x,y) in enumerate(history,1): posterior.observe(Observation(t,x,x,y))
    precision=posterior.precision_readout(delta)
    median=posterior.median_readout()
    return dict(median=median.boundary,precision=precision.boundary,S_delta=precision.posterior_success,
                acquisitions=dict(variance=variance_gain(posterior,targets,belief,nodes),
                                  precision=precision_gain(posterior,targets,belief,delta,nodes)))


def _acquisition_comparison(coarse,fine,targets):
    ci=np.flatnonzero(np.isclose(coarse,coarse.max(),rtol=1e-12,atol=1e-15))
    fi=np.flatnonzero(np.isclose(fine,fine.max(),rtol=1e-12,atol=1e-15))
    loss=float(max(0.,fine.max()-fine[ci[0]]))
    worst=float(max(0.,fine.max()-fine[ci].min()))
    allowed=float(.01*fine.max()+1e-6)
    return dict(max_absolute_difference=float(np.max(np.abs(coarse-fine))),
                coarse_command=float(targets[ci[0]]),fine_command=float(targets[fi[0]]),
                best_command_changed=bool(ci[0]!=fi[0]),maximizer_sets_overlap=bool(np.intersect1d(ci,fi).size),
                coarse_maximum=float(coarse.max()),fine_maximum=float(fine.max()),
                fine_loss_at_coarse_choice=loss,worst_fine_loss_over_coarse_ties=worst,
                allowed_loss=allowed,passes=bool(worst<=allowed),
                coarse_values=coarse.tolist(),fine_values=fine.tolist())


def compare_public_histories(*,coarse_grid=(121,41),fine_grid=(241,81),coarse_nodes=7,fine_nodes=15,
                             histories=None,targets=tuple(i/10 for i in range(31)),
                             prior=None,tau=.70,delta=.15):
    histories=PUBLIC_HISTORIES if histories is None else histories
    prior=PriorSpec() if prior is None else prior
    coarse_prior=replace(prior,b_nodes=coarse_grid[0],k_nodes=coarse_grid[1])
    fine_prior=replace(prior,b_nodes=fine_grid[0],k_nodes=fine_grid[1])
    rows=[]
    for name,history in histories.items():
        for label,belief in [('precise',ExecutionBelief(0.,1.,.03)),('variable',ExecutionBelief(.08,.92,.18))]:
            # Only three bases live sequentially, with each posterior released
            # after snapshot; summaries retain target arrays, not big matrices.
            coarse=_snapshot(history,coarse_prior,tau,delta,targets,belief,coarse_nodes)
            grid_fine=_snapshot(history,fine_prior,tau,delta,targets,belief,coarse_nodes)
            fine=_snapshot(history,fine_prior,tau,delta,targets,belief,fine_nodes)
            for comparison,a,b in [('grid',coarse,grid_fine),('quadrature',grid_fine,fine),('combined',coarse,fine)]:
                md=abs(a['median']-b['median']); pd=abs(a['precision']-b['precision']); sd=abs(a['S_delta']-b['S_delta'])
                acquisitions={objective:_acquisition_comparison(a['acquisitions'][objective],b['acquisitions'][objective],targets)
                              for objective in ('variance','precision')}
                passed=md<=.025+1e-12 and pd<=.025+1e-12 and sd<=.02+1e-12 and all(v['passes'] for v in acquisitions.values())
                rows.append(dict(history=name,execution=label,comparison=comparison,
                    coarse_median=a['median'],fine_median=b['median'],median_boundary_difference=md,
                    coarse_precision_boundary=a['precision'],fine_precision_boundary=b['precision'],precision_boundary_difference=pd,
                    coarse_S_delta=a['S_delta'],fine_S_delta=b['S_delta'],S_delta_difference=sd,
                    acquisitions=acquisitions,passes=bool(passed)))
    return dict(uses_truth=False,tau=tau,delta=delta,prior=asdict(prior),
                coarse_grid=list(coarse_grid),fine_grid=list(fine_grid),coarse_nodes=coarse_nodes,fine_nodes=fine_nodes,
                decision_grid=dict(lower=-5.,upper=5.,spacing=.025),targets=list(targets),
                histories={k:[list(v) for v in h] for k,h in histories.items()},
                thresholds=dict(boundary=.025,S_delta=.02,relative_acquisition_loss=.01,absolute_acquisition_loss=1e-6),
                all_pass=all(r['passes'] for r in rows),comparisons=rows)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coarse-grid',type=int,nargs=2,default=(121,41),metavar=('B','K'))
    p.add_argument('--fine-grid',type=int,nargs=2,default=(241,81),metavar=('B','K'))
    p.add_argument('--coarse-nodes',type=int,default=7)
    p.add_argument('--fine-nodes',type=int,default=15)
    p.add_argument('--prior-kind',choices=('normal','uniform'),default='normal')
    p.add_argument('--prior-center',type=float,default=1.5)
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    report=compare_public_histories(coarse_grid=args.coarse_grid,fine_grid=args.fine_grid,
        coarse_nodes=args.coarse_nodes,fine_nodes=args.fine_nodes,
        prior=PriorSpec(kind=args.prior_kind,center=args.prior_center))
    rendered=json.dumps(report,indent=2,allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered+'\n',encoding='utf-8')
        print(json.dumps(dict(output=str(args.output),all_pass=report['all_pass'],comparisons=len(report['comparisons']))))
    else: print(rendered)
    return 0 if report['all_pass'] else 2


if __name__=='__main__': raise SystemExit(main())
