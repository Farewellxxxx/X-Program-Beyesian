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
