from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[2] / "comfort_boundary_bo_research_package/simulation/monotone_bayes.py"


class MonotoneBayesTests(unittest.TestCase):
    def model_module(self):
        self.assertTrue(SOURCE.exists(), "Monotone binary Bayesian model is missing")
        name = "monotone_bayes_test_module"
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, SOURCE)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        return sys.modules[name]

    def model(self, **kwargs):
        return self.model_module().MonotoneBayesianLogistic(tau=0.7, **kwargs)

    def test_exact_four_point_bayes_update_uses_bernoulli_likelihood(self):
        module = self.model_module()
        # Symmetric two-node normal priors give equal prior mass at each corner.
        # At x=0, likelihoods for (b,beta)=(0,1),(0,2),(log3,1),(log3,2)
        # are 1/2,1/2,3/4,9/10. After y=1 the exact weights are 10,10,15,18 / 53.
        grid = module.PriorGrid(midpoint_min=0, midpoint_max=float(np.log(3)), midpoint_nodes=2,
            log_slope_min=0, log_slope_max=float(np.log(2)), slope_nodes=2,
            midpoint_mean=float(np.log(3)/2), midpoint_sd=1,
            log_slope_mean=float(np.log(2)/2), log_slope_sd=1)
        model = self.model(grid=grid).fit([0], [1])
        np.testing.assert_allclose(model.posterior_weights, np.array([10,10,15,18])/53, atol=1e-14)

    def test_contradictory_feedback_still_gives_monotone_probabilities(self):
        model = self.model().fit([.55,.85,1.15,1.45,1.75], [1,0,1,0,1])
        p, sd = model.predict_array(np.linspace(-1,4,501))
        self.assertTrue(np.all(np.diff(p) <= 1e-12))
        self.assertTrue(np.all((p >= 0) & (p <= 1)))
        self.assertTrue(np.all(np.isfinite(sd) & (sd >= 0)))
        self.assertAlmostEqual(model.posterior_weights.sum(), 1, places=13)

    def test_all_accept_reject_empty_and_unobserved_range_are_explicit(self):
        empty = self.model().fit([], [])
        accept = self.model().fit([1.0]*12, [1]*12)
        reject = self.model().fit([1.0]*12, [0]*12)
        self.assertGreater(accept.estimate_boundary(), empty.estimate_boundary())
        self.assertLess(reject.estimate_boundary(), empty.estimate_boundary())
        for model, label in [(empty,"no_data"),(accept,"all_accept"),(reject,"all_reject")]:
            summary = model.boundary_summary()
            self.assertEqual(summary["boundary_support"], label)
            self.assertLess(summary["boundary_ci95_lower"], summary["boundary_ci95_upper"])
            self.assertGreater(summary["posterior_boundary_sd"], 0)
        self.assertGreater(accept.boundary_summary()["boundary_mass_above_observed"], .5)
        self.assertLess(reject.estimate_boundary(), 1.0)  # no clamp to the observed point

    def test_epistemic_variance_is_distinct_from_binary_observation_variance(self):
        prior = self.model()
        posterior = self.model().fit([1.2]*40, [1,0]*20)
        p0, s0 = prior.predict(1.2)
        p, sd = posterior.predict(1.2)
        self.assertLess(sd, s0)
        self.assertLess(sd*sd, p*(1-p))
        self.assertGreater(p*(1-p), .20)

    def test_fit_resets_prior_and_is_order_invariant_and_deterministic(self):
        x, y = [.5,.8,1.0,1.4,1.8], [1,1,0,1,0]
        model = self.model().fit(x,y)
        first = model.posterior_weights.copy()
        model.fit(x,y)
        np.testing.assert_array_equal(first, model.posterior_weights)
        reverse = self.model().fit(x[::-1],y[::-1])
        np.testing.assert_allclose(first, reverse.posterior_weights, atol=1e-14)
        model.fit([],[])
        np.testing.assert_allclose(model.posterior_weights, self.model().posterior_weights)

    def test_input_validation_rejects_nonbinary_nonfinite_and_mismatched_data(self):
        for x,y in [([1],[.2]),([1],[2]),([1],[float("nan")]),([float("nan")],[1]),([1,2],[1]),([[1]],[1])]:
            with self.subTest(x=x,y=y), self.assertRaises(ValueError):
                self.model().fit(x,y)
        module=self.model_module()
        for tau in [0,1,float("nan")]:
            with self.subTest(tau=tau), self.assertRaises(ValueError):
                module.MonotoneBayesianLogistic(tau=tau)
        with self.assertRaises(ValueError):
            self.model().predict_array([float("inf")])

    def test_interpolated_moments_match_direct_posterior_integration(self):
        model=self.model().fit([.5,.9,1.3,1.7],[1,1,0,0])
        model.predict_array(np.linspace(0,3,100))
        x=np.array([-.3, .123456, .99999, 1.23456, 2.9999, 3.7, 100])
        p,sd=model.predict_array(x)
        logits=model.posterior_slopes[:,None]*(model.posterior_midpoints[:,None]-x[None,:])
        curves=np.exp(-np.logaddexp(0,-logits))
        exact=np.sum(curves*model.posterior_weights[:,None],axis=0)
        exact_var=np.sum((curves-exact)**2*model.posterior_weights[:,None],axis=0)
        np.testing.assert_allclose(p,exact,atol=2e-5,rtol=0)
        np.testing.assert_allclose(sd,np.sqrt(exact_var),atol=2e-5,rtol=0)

    def test_tau_boundary_quantiles_order_and_grid_refinement(self):
        module=self.model_module()
        x=[.4,.55,.7,.85,1,1.1,1.2,1.3,1.45,1.6,1.8,1.9]
        y=[1,1,1,1,1,0,1,0,0,0,0,0]
        coarse=self.model().fit(x,y)
        fine=self.model(grid=module.PriorGrid(midpoint_nodes=241,slope_nodes=121)).fit(x,y)
        c,f=coarse.boundary_summary(),fine.boundary_summary()
        self.assertLess(abs(coarse.estimate_boundary()-fine.estimate_boundary()),.03)
        for key in ["boundary_ci95_lower","boundary_ci95_upper"]:
            self.assertLess(abs(c[key]-f[key]),.04)
        p,_=coarse.predict_array(np.linspace(.2,2.3,51))
        q,_=fine.predict_array(np.linspace(.2,2.3,51))
        np.testing.assert_allclose(p,q,atol=.005,rtol=0)
        high=module.MonotoneBayesianLogistic(tau=.8).fit(x,y)
        low=module.MonotoneBayesianLogistic(tau=.6).fit(x,y)
        self.assertLess(high.estimate_boundary(),coarse.estimate_boundary())
        self.assertGreater(low.estimate_boundary(),coarse.estimate_boundary())


if __name__ == "__main__":
    unittest.main()
