"""Independent future-draw coverage and a proper interval score (alpha=.10)."""
import numpy as np
from comfort_boundary_bo_research_package.simulation import execution_misspecification as stress

HOLDOUT_NAMESPACE=0xA11C


def interval_score(observed,lower,upper):
    if upper<lower: raise ValueError('Reversed prediction interval')
    y=np.asarray(observed)
    return float(np.mean(upper-lower+20*np.maximum(lower-y,0)+20*np.maximum(y-upper,0)))


def predictive_diagnostics(prepared,seed,n_samples=4096):
    rows=stress.distribution_diagnostics(prepared,seed,n_samples)
    additions=[]
    for index,row in rows.iterrows():
        x=float(row.command)
        prediction=prepared.belief.sample_many(x,np.random.default_rng(np.random.SeedSequence([0xD1A6,index,seed])),n_samples)[0]
        future=prepared.truth.sample_many(x,np.random.default_rng(np.random.SeedSequence([HOLDOUT_NAMESPACE,index,seed])),n_samples)[0]
        lo,hi=np.quantile(prediction,[.05,.95])
        additions.append(dict(holdout_namespace=HOLDOUT_NAMESPACE,holdout_samples=n_samples,
            interval90_lower=float(lo),interval90_upper=float(hi),interval90_width=float(hi-lo),
            holdout_interval90_coverage=float(((future>=lo)&(future<=hi)).mean()),interval90_score=interval_score(future,lo,hi)))
    for key in additions[0]: rows[key]=[r[key] for r in additions]
    return rows
