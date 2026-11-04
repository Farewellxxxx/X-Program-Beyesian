from pathlib import Path
import importlib.util
import unittest
import pandas as pd


class SurrogateComparisonTests(unittest.TestCase):
    def module(self):
        path=Path(__file__).resolve().parents[2]/"comfort_boundary_bo_research_package/simulation/compare_surrogates.py"
        self.assertTrue(path.exists(),"Paired model comparison must be reproducible")
        spec=importlib.util.spec_from_file_location("surrogate_comparison",path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def runs(self):
        old=pd.DataFrame({"seed":range(5),"scenario":[f"multiseed_low_{i}" for i in range(5)],
            "execution_noise":"low","algorithm":"Example","n_participants":24,
            "n_trials_per_algorithm_participant":12,"mean_boundary_error":1.,
            "tau":.7,"feedback_noise":.08,"calibration_bias":0.,"include_time_effects":False,
            "surrogate_kind":"legacy_kernel",
            "mean_unacceptable_trials":4.,"mean_cumulative_discomfort":25.,"mean_predictive_brier_score":.2})
        new=old.copy(); new["mean_boundary_error"]=[.9,.8,.7,.6,.5]
        new["surrogate_kind"]="monotone_bayes"
        return old,new

    def test_paired_differences_have_direction_and_process_seed_intervals(self):
        result=self.module().paired_effects(*self.runs())
        error=result[result.metric=="mean_boundary_error"].iloc[0]
        self.assertAlmostEqual(error.mean_change,-.3)
        self.assertLess(error.ci95_low,-.3); self.assertGreater(error.ci95_high,-.3)
        self.assertLess(error.ci95_high,0)
        self.assertEqual(error.n_seeds,5)
        self.assertEqual(result[result.metric=="mean_unacceptable_trials"].iloc[0].mean_change,0)

    def test_rejects_missing_seeds_and_unequal_budgets(self):
        module=self.module(); old,new=self.runs()
        with self.assertRaises(ValueError): module.paired_effects(old,new.iloc[:-1])
        new.loc[0,"n_trials_per_algorithm_participant"]=10
        with self.assertRaises(ValueError): module.paired_effects(old,new)

    def test_rejects_generator_changes_wrong_model_or_missing_metadata(self):
        module=self.module()
        for column,value in {"tau":.5,"feedback_noise":.49,"calibration_bias":.15,
                             "include_time_effects":True,"surrogate_kind":"legacy_kernel"}.items():
            with self.subTest(column=column):
                old,new=self.runs(); new.loc[0,column]=value
                with self.assertRaises(ValueError): module.paired_effects(old,new)
        old,new=self.runs()
        with self.assertRaises(ValueError): module.paired_effects(old.drop(columns="tau"),new)
        old.loc[0,"surrogate_kind"]="monotone_bayes"
        with self.assertRaises(ValueError): module.paired_effects(old,new)


if __name__=="__main__": unittest.main()
