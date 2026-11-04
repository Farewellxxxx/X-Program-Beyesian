import importlib
from dataclasses import replace
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


class PopulationAuditTests(unittest.TestCase):
    def module(self,name):
        self.assertTrue((ROOT/'long_horizon_audit/scripts'/f'{name}.py').exists(),name+' must exist')
        return importlib.import_module('long_horizon_audit.scripts.'+name)

    def test_design_has_independent_nested_seeds_and_matched_controls(self):
        audit=self.module('run_execution_population_audit')
        specs=audit.build_scenarios()
        self.assertEqual(len(specs),85)
        self.assertEqual(len({s.config.scenario_name for s in specs}),85)
        population=[s for s in specs if s.suite=='population']
        self.assertEqual(len(population),40)
        self.assertEqual(len({s.config.population_seed for s in population}),5)
        streams={}
        for s in population:
            streams.setdefault(s.population_block,set()).add(s.config.seed)
        for left in streams:
            for right in streams:
                if left!=right: self.assertTrue(streams[left].isdisjoint(streams[right]))
        controls={(s.population_block,s.process_repeat,s.config.execution_noise):s for s in specs if s.suite=='fixed_control'}
        for s in population:
            c=controls[s.population_block,s.process_repeat,s.config.execution_noise]
            self.assertEqual((s.config.seed,s.config.calibration_seed),(c.config.seed,c.config.calibration_seed))
            self.assertNotEqual(s.config.population_seed,c.config.population_seed)
        with self.assertRaises(ValueError): audit.build_scenarios(population_blocks=0)
        for count in (1,11):
            with self.assertRaises(ValueError): audit.build_scenarios(population_blocks=count)

    def test_cluster_interval_uses_population_means_not_individual_runs(self):
        compare=self.module('compare_execution_population')
        frame=pd.DataFrame({'population_block':[1,1,2,2],'process_repeat':[1,2,1,2],'value':[0.,2.,2.,4.]})
        result=compare.summarize_clusters(frame,'value')
        self.assertEqual(result['n_population_blocks'],2)
        self.assertEqual(result['n_process_runs'],4)
        self.assertAlmostEqual(result['mean'],2.)
        self.assertAlmostEqual(result['ci95_low'],2.-12.706)
        self.assertAlmostEqual(result['ci95_high'],2.+12.706)
        with self.assertRaises(ValueError): compare.summarize_clusters(frame.iloc[:-1],'value')

    def test_saved_rows_must_cover_the_entire_declared_design(self):
        audit=self.module('run_execution_population_audit'); compare=self.module('compare_execution_population')
        self.assertTrue(hasattr(compare,'validate_design_rows'))
        spec=audit.build_scenarios()[0]
        spec=replace(spec,config=replace(spec.config,n_participants=1,n_trials=1))
        metrics,*_=audit.execute(spec)
        compare.validate_design_rows(metrics,[spec])
        for bad in (metrics.iloc[:-1],pd.concat([metrics,metrics.iloc[:1]],ignore_index=True),
                    metrics.assign(population_seed=999)):
            with self.assertRaises(ValueError): compare.validate_design_rows(bad,[spec])

    def paired_inputs(self):
        rows=[]
        for block in range(1,6):
            for repeat in (1,2):
                row=dict(population_block=block,process_repeat=repeat,execution_noise='low',algorithm='Example',
                    population_seed=100+block,process_seed=1000+block*10+repeat,calibration_seed=2000+block*10+repeat,
                    generator_fingerprint='generator',policy_fingerprint='policy',population_fingerprint=f'pop{block}',
                    n_participants=24,n_trials_per_algorithm_participant=12,execution_belief='oracle',surrogate_kind='monotone_bayes')
                for metric in self.module('compare_execution_population').METRICS: row[metric]=1.
                rows.append(row)
        old=pd.DataFrame(rows); new=old.copy(); new.execution_belief='calibrated'
        new['mean_boundary_error']-=new.population_block*.02
        return old,new

    def test_paired_population_effects_reject_noncomparable_runs(self):
        compare=self.module('compare_execution_population'); old,new=self.paired_inputs()
        result=compare.paired_effects(old,new,'calibration_vs_oracle')
        row=result[result.metric=='mean_boundary_error'].iloc[0]
        self.assertAlmostEqual(row.mean_change,-.06)
        self.assertEqual(row.n_population_blocks,5)
        self.assertEqual(row.n_process_runs,10)
        for column,value in {'population_seed':999,'process_seed':999,'generator_fingerprint':'changed',
            'policy_fingerprint':'changed','execution_belief':'nominal','n_participants':1}.items():
            with self.subTest(column=column):
                bad=new.copy(); bad.loc[0,column]=value
                with self.assertRaises(ValueError): compare.paired_effects(old,bad,'calibration_vs_oracle')
        for bad in (new.iloc[:-1],pd.concat([new,new.iloc[:1]],ignore_index=True)):
            with self.assertRaises(ValueError): compare.paired_effects(old,bad,'calibration_vs_oracle')


if __name__=='__main__': unittest.main()
