"""Monotone Bernoulli-logistic inference by deterministic posterior quadrature.

Each curve is p(y=1|m,b,k)=sigmoid(exp(k)*(b-m)). Priors are independent
truncated normals for b and k on an explicit trapezoidal integration grid.
No simulator truth, response labels from other people, or hidden lapse rates
enter inference. Returned probability uncertainty is epistemic posterior SD.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class PriorGrid:
    midpoint_min: float = -1.5
    midpoint_max: float = 4.0
    midpoint_nodes: int = 121
    log_slope_min: float = math.log(.25)
    log_slope_max: float = math.log(40)
    slope_nodes: int = 61
    midpoint_mean: float = 1.2
    midpoint_sd: float = .75
    log_slope_mean: float = math.log(4)
    log_slope_sd: float = .7

    def __post_init__(self):
        values = (self.midpoint_min, self.midpoint_max, self.log_slope_min,
                  self.log_slope_max, self.midpoint_mean, self.midpoint_sd,
                  self.log_slope_mean, self.log_slope_sd)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("Prior/grid parameters must be finite")
        if self.midpoint_min >= self.midpoint_max or self.log_slope_min >= self.log_slope_max:
            raise ValueError("Grid upper bounds must exceed lower bounds")
        if self.midpoint_sd <= 0 or self.log_slope_sd <= 0:
            raise ValueError("Prior standard deviations must be positive")
        for nodes in (self.midpoint_nodes, self.slope_nodes):
            if isinstance(nodes, bool) or not isinstance(nodes, int) or nodes < 2:
                raise ValueError("Grid node counts must be integers >= 2")
        if not -700 < self.log_slope_min < self.log_slope_max < 700:
            raise ValueError("Log-slope support must allow finite positive slopes")


def _readonly(array: np.ndarray) -> np.ndarray:
    array.setflags(write=False)
    return array


@lru_cache(maxsize=8)
def _parameter_grid(grid: PriorGrid):
    b = np.linspace(grid.midpoint_min, grid.midpoint_max, grid.midpoint_nodes)
    k = np.linspace(grid.log_slope_min, grid.log_slope_max, grid.slope_nodes)
    bb, kk = np.meshgrid(b, k, indexing="ij")
    wb, wk = np.ones(len(b)), np.ones(len(k))
    wb[[0, -1]] = .5
    wk[[0, -1]] = .5
    log_prior = (-.5 * ((bb-grid.midpoint_mean)/grid.midpoint_sd)**2
                 -.5 * ((kk-grid.log_slope_mean)/grid.log_slope_sd)**2
                 + np.log(wb[:, None]) + np.log(wk[None, :])).ravel()
    # Constant grid spacings and normal densities cancel on normalization.
    log_prior -= np.max(log_prior)
    weights = np.exp(log_prior)
    weights /= weights.sum()
    edge = np.zeros(bb.shape, dtype=bool)
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    return tuple(_readonly(x) for x in (bb.ravel(), np.exp(kk.ravel()),
                                        log_prior, weights, edge.ravel()))


@lru_cache(maxsize=2)
def _prediction_basis(grid: PriorGrid):
    b, beta, _, _, _ = _parameter_grid(grid)
    x = np.linspace(0., 3., 601)
    logits = beta[:, None] * (b[:, None] - x[None, :])
    probability = np.exp(-np.logaddexp(0., -logits))
    return _readonly(x), _readonly(probability), _readonly(probability**2)


class MonotoneBayesianLogistic:
    """Finite-grid approximation to a proper monotone logistic posterior."""

    def __init__(self, tau: float, grid: PriorGrid | None = None):
        if not math.isfinite(tau) or not 0 < tau < 1:
            raise ValueError("tau must be finite and strictly between zero and one")
        self.tau = float(tau)
        self.grid = grid or PriorGrid()
        (self.posterior_midpoints, self.posterior_slopes,
         self._log_prior, self._prior_weights, self._edge) = _parameter_grid(self.grid)
        self._boundary_values = self.posterior_midpoints - math.log(tau/(1-tau))/self.posterior_slopes
        self._boundary_order = np.argsort(self._boundary_values)
        self.fit([], [])

    def fit(self, intensities: Iterable[float], labels: Iterable[int]) -> "MonotoneBayesianLogistic":
        x = np.asarray(list(intensities), dtype=float)
        y = np.asarray(list(labels), dtype=float)
        if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
            raise ValueError("Intensities and binary labels must be equal-length 1-D sequences")
        if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isin(y, [0, 1]).all():
            raise ValueError("Inputs must be finite and labels must be exactly zero or one")
        log_weights = self._log_prior.copy()
        for start in range(0, len(x), 128):
            xx, yy = x[start:start+128], y[start:start+128]
            z = self.posterior_slopes[:, None] * (self.posterior_midpoints[:, None] - xx[None, :])
            log_likelihood = np.where(yy[None, :] == 1, -np.logaddexp(0., -z), -np.logaddexp(0., z))
            log_weights += log_likelihood.sum(axis=1)
        log_weights -= log_weights.max()
        weights = np.exp(log_weights)
        self.posterior_weights = _readonly(weights / weights.sum())
        self.intensities, self.labels = x, y
        self._moments = None
        return self

    def _direct_moments(self, x: np.ndarray):
        z = self.posterior_slopes[:, None] * (self.posterior_midpoints[:, None] - x[None, :])
        curves = np.exp(-np.logaddexp(0., -z))
        mean = np.einsum("ij,i->j", curves, self.posterior_weights, optimize=False)
        second = np.einsum("ij,i->j", curves**2, self.posterior_weights, optimize=False)
        return mean, second

    def predict_array(self, intensity_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(intensity_grid, dtype=float)
        if x.ndim != 1 or not np.isfinite(x).all():
            raise ValueError("Prediction intensities must be a finite 1-D array")
        if x.size == 0:
            return np.array([]), np.array([])
        if self._moments is None and len(x) < 16:
            mean, second = self._direct_moments(x)
        else:
            if self._moments is None:
                support, curves, squares = _prediction_basis(self.grid)
                self._moments = (support,
                    np.einsum("ij,i->j", curves, self.posterior_weights, optimize=False),
                    np.einsum("ij,i->j", squares, self.posterior_weights, optimize=False))
            support, means, seconds = self._moments
            mean, second = np.interp(x, support, means), np.interp(x, support, seconds)
            outside = (x < support[0]) | (x > support[-1])
            if outside.any():
                mean[outside], second[outside] = self._direct_moments(x[outside])
        mean = np.clip(mean, 0, 1)
        return mean, np.sqrt(np.maximum(second-mean**2, 0))

    def predict(self, intensity: float) -> tuple[float, float]:
        mean, sd = self.predict_array(np.array([intensity]))
        return float(mean[0]), float(sd[0])

    def _boundary_quantiles(self, quantiles):
        order = self._boundary_order
        cumulative = np.cumsum(self.posterior_weights[order])
        cumulative[-1] = 1.0
        indices = np.searchsorted(cumulative, quantiles, side="left")
        return self._boundary_values[order[indices]]

    def estimate_boundary(self) -> float:
        return float(self._boundary_quantiles([.5])[0])

    def boundary_summary(self) -> dict[str, float | str]:
        low, median, high = self._boundary_quantiles([.025, .5, .975])
        values, weights = self._boundary_values, self.posterior_weights
        mean = float(np.sum(values*weights))
        sd = float(np.sqrt(np.sum((values-mean)**2*weights)))
        below = above = float("nan")
        if not len(self.labels):
            support = "no_data"
        else:
            xmin, xmax = float(self.intensities.min()), float(self.intensities.max())
            below = float(weights[values < xmin].sum())
            above = float(weights[values > xmax].sum())
            if np.all(self.labels == 1):
                support = "all_accept"
            elif np.all(self.labels == 0):
                support = "all_reject"
            elif median < xmin:
                support = "below_observed_range"
            elif median > xmax:
                support = "above_observed_range"
            else:
                support = "within_observed_range"
        return {"boundary_ci95_lower": float(low), "boundary_ci95_upper": float(high),
                "posterior_boundary_sd": sd,
                "boundary_mass_below_observed": below, "boundary_mass_above_observed": above,
                "boundary_support": support, "posterior_grid_edge_mass": float(weights[self._edge].sum())}
