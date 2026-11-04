from dataclasses import replace
import importlib
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))


class CalibrationTests(unittest.TestCase):
    def module(self):
        self.assertTrue((ROOT/'comfort_boundary_bo_research_package/simulation/execution_belief.py').exists(),
                        'An observation-only execution estimator must exist')
        return importlib.import_module('comfort_boundary_bo_research_package.simulation.execution_belief')

    def observations(self):
        x=np.ones(8); sign=np.array([-1.,1.]*4)
        accel=.05+.94*x+.12+.04*sign
        return pd.DataFrame(dict(target_command_x=x,peak_accel=accel,
            peak_jerk=.58+1.74*accel+.10*x+.20*sign,
            duration_s=3.90-.30*accel+.10*sign))

    def test_calibration_matches_hand_computed_weighted_fit(self):
        mod=self.module(); fit=mod.fit_execution_parameters(self.observations(),mod.ExecutionSettings())
        level=(1-.35)/(1.90-.35)
        expected=np.sqrt(8*((.04/(.045+.055*level))**2+(.20/(.18+.24*level))**2+(.10/.18)**2)/23)
        self.assertAlmostEqual(fit.parameters.bias,.12,places=12)
        self.assertAlmostEqual(fit.parameters.noise_scale,expected,places=12)
        self.assertEqual((fit.n_observations,fit.n_used,fit.n_clipped),(8,8,0))

    def test_clipping_is_reported_and_bad_observations_fail(self):
        mod=self.module(); data=self.observations(); data.loc[0,'peak_accel']=.2
        fit=mod.fit_execution_parameters(data,mod.ExecutionSettings())
        self.assertEqual((fit.n_used,fit.n_clipped),(7,1))
        for bad in (data.iloc[:2],data.drop(columns='peak_jerk'),data.assign(peak_accel=np.nan)):
            with self.assertRaises(ValueError): mod.fit_execution_parameters(bad,mod.ExecutionSettings())
        with self.assertRaises(ValueError): mod.ExecutionParameters(bias=0,noise_scale=0)
        with self.assertRaises(ValueError): mod.ExecutionParameters(bias=float('nan'),noise_scale=1)


class ExecutionSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim=importlib.import_module('comfort_boundary_bo_research_package.simulation.run_uncertain_input_bo_extended')

    def test_population_seed_is_independent_of_process_and_calibration(self):
        self.assertIn('population_seed',self.sim.Config.__dataclass_fields__)
        config=self.sim.Config(n_participants=3,population_seed=19,seed=10,calibration_seed=23)
        people=self.sim.make_passengers(config)
        self.assertEqual(people,self.sim.make_passengers(replace(config,seed=11,calibration_seed=24)))
        self.assertNotEqual(people,self.sim.make_passengers(replace(config,population_seed=20)))
        a=self.sim.prepare_execution(config); b=self.sim.prepare_execution(replace(config,population_seed=20,seed=11))
        self.assertEqual(a.belief.parameters,b.belief.parameters)

    def test_belief_uses_only_observations_and_policy_view_has_no_truth(self):
        self.assertTrue(hasattr(self.sim,'prepare_execution'))
        observations=CalibrationTests().observations()
        config=self.sim.Config(calibration_bias=.15,execution_noise='high')
        first=self.sim.prepare_execution(config,calibration_observations=observations)
        second=self.sim.prepare_execution(replace(config,calibration_bias=-.15,execution_noise='low'),
                                          calibration_observations=observations)
        self.assertEqual(first.belief.parameters,second.belief.parameters)
        self.assertNotEqual(first.truth.parameters,second.truth.parameters)
        self.assertIsNot(first.belief,first.truth)
        policies=self.sim.build_policies(self.sim.policy_settings(config),first.belief,100)
        for policy in policies[:2]:
            self.assertFalse(hasattr(policy.config,'calibration_bias'))
            self.assertFalse(hasattr(policy.config,'execution_noise'))
            self.assertFalse(hasattr(policy.execution_model.config,'calibration_bias'))
            self.assertEqual(policy.execution_model.parameters,first.belief.parameters)

    def test_policy_history_contains_only_observations(self):
        self.assertTrue(hasattr(self.sim,'prepare_execution'))
        sim=self.sim; config=sim.Config(n_participants=1,n_trials=3)
        prepared=sim.prepare_execution(config)
        seen=[]
        class Probe:
            name='Probe'
            def choose(self,history,trial_id):
                seen.extend(history)
                return 1.
        sim.run_algorithm(config,sim.make_passengers(config)[0],Probe(),prepared.truth,
                          np.random.default_rng(1),np.random.default_rng(2))
        self.assertTrue(seen)
        for row in seen:
            self.assertEqual(set(row),set(sim.OBSERVED_HISTORY_FIELDS))
            self.assertNotIn('p_accept_true',row)
            self.assertNotIn('criterion_boundary_tau',row)

    def test_oracle_replays_old_bayesian_records_and_fixed_policies_ignore_belief(self):
        self.assertIn('execution_belief',self.sim.Config.__dataclass_fields__)
        config=self.sim.Config(n_participants=1,n_trials=4,seed=self.sim.BASE_SEED+1,
            scenario_name='continuous_low_noise',execution_belief='oracle')
        old=pd.read_csv(ROOT/'comfort_boundary_bo_research_package/simulation/outputs_bayesian/continuous_trials.csv')
        old=old[(old.scenario==config.scenario_name)&(old.participant_id==1)&(old.trial_id<=4)]
        actual=self.sim.run_scenario(config,self.sim.make_passengers(config))
        keys=['algorithm','trial_id']
        pd.testing.assert_frame_equal(old.sort_values(keys).reset_index(drop=True),
            actual[old.columns].sort_values(keys).reset_index(drop=True),check_exact=False,rtol=0,atol=1e-12)
        calibrated=self.sim.run_scenario(replace(config,execution_belief='calibrated'),self.sim.make_passengers(config))
        cols=['algorithm','trial_id','target_command_x','realized_intensity','acceptable','discomfort']
        fixed=['RandomContinuous','GridContinuous','Staircase']
        pd.testing.assert_frame_equal(actual.loc[actual.algorithm.isin(fixed),cols].reset_index(drop=True),
            calibrated.loc[calibrated.algorithm.isin(fixed),cols].reset_index(drop=True),check_exact=True)

    def test_seed_and_belief_provenance_is_retained_in_every_summary(self):
        self.assertIn('execution_belief',self.sim.Config.__dataclass_fields__)
        config=self.sim.Config(n_participants=1,n_trials=2,population_seed=19,calibration_seed=23)
        trials=self.sim.run_scenario(config,self.sim.make_passengers(config))
        fields=['population_seed','process_seed','calibration_seed','execution_belief',
                'true_execution_bias','true_execution_noise_scale','belief_execution_bias',
                'belief_execution_noise_scale','calibration_n_used']
        for table in [trials,*self.sim.evaluate(trials)]:
            for field in fields: self.assertIn(field,table)
        self.assertTrue(trials.execution_belief.eq('calibrated').all())
        self.assertTrue(trials.calibration_n_used.le(40).all())

    def test_batch_runner_draws_each_requested_population(self):
        configs=[self.sim.Config(n_participants=1,n_trials=1,population_seed=seed,scenario_name=f'pop_{seed}')
                 for seed in (19,20)]
        with tempfile.TemporaryDirectory() as folder, patch.object(self.sim,'save_plots'):
            trials,_,_=self.sim.run_configurations(configs,Path(folder))
        for config in configs:
            observed=trials[trials.scenario==config.scenario_name].acceptability_midpoint.unique()
            np.testing.assert_array_equal(observed,[self.sim.make_passengers(config)[0].acceptability_midpoint])


if __name__=='__main__': unittest.main()
