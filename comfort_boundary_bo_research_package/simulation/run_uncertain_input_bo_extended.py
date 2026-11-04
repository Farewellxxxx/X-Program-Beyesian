"""
Continuous-target uncertain-input BO-inspired simulation.

Research context:
- BO proposes a continuous target motion command x.
- The driver/vehicle executes imperfectly, producing measured features z ~ P(z | x).
- Passenger feedback depends on realized z, not the nominal target x.
- The surrogate and boundary estimate update with realized z and feedback y.

This script uses a transparent Monte Carlo acquisition approximation:
for each candidate command x, it samples possible realized z values from P(z | x)
and scores boundary proximity, posterior uncertainty, discomfort risk, and
safety risk. The default response surrogate is a monotone Bayesian logistic
model. The acquisition remains heuristic, not expected information gain or
exact uGP-UCB.

Run:
    python comfort_boundary_bo_research_package/simulation/run_uncertain_input_bo_extended.py

Outputs:
    comfort_boundary_bo_research_package/simulation/outputs_execution_separated/
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import argparse
from pathlib import Path
import sys
from typing import Iterable, Protocol

import math

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Support both direct CLI execution and importlib-loaded audit/test modules.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from comfort_boundary_bo_research_package.simulation.monotone_bayes import MonotoneBayesianLogistic, PriorGrid
from comfort_boundary_bo_research_package.simulation.execution_belief import (
    ExecutionParameters, ExecutionSettings, CALIBRATION_FIELDS, fit_execution_parameters,
)

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs_execution_separated"
BASE_SEED = 20260703

ALGORITHM_ORDER = [
    "UncertainInputBO",
    "NaiveContinuousBO",
    "RandomContinuous",
    "GridContinuous",
    "Staircase",
]

COLORS = {
    "UncertainInputBO": "#1f77b4",
    "NaiveContinuousBO": "#ff7f0e",
    "RandomContinuous": "#2ca02c",
    "GridContinuous": "#7f7f7f",
    "Staircase": "#9467bd",
}


@dataclass(frozen=True)
class Config:
    """One simulation scenario.

    x is a continuous target motion command. In this version it can be read as
    target acceleration / deceleration magnitude or target motion intensity.
    """

    n_participants: int = 24
    n_trials: int = 12
    tau: float = 0.70
    x_min: float = 0.35
    x_max: float = 1.90
    execution_noise: str = "low"  # low, medium, high
    calibration_bias: float = 0.0
    feedback_noise: float = 0.06
    include_time_effects: bool = False
    scenario_name: str = "continuous_low_noise"
    seed: int = BASE_SEED
    process_rng_mode: str = "independent"  # legacy only for historical replay
    population_seed: int = BASE_SEED + 101
    calibration_seed: int = BASE_SEED + 303
    execution_belief: str = "calibrated"  # calibrated, nominal, oracle
    calibration_trials: int = 40
    assumed_execution_bias: float = 0.0
    assumed_execution_noise_scale: float = 0.65
    candidate_count: int = 35
    mc_samples: int = 35
    surrogate_kind: str = "monotone_bayes"
    bayes_grid: PriorGrid = PriorGrid()

    jerk_penalty_threshold: float = 2.30
    jerk_penalty_weight: float = 0.10
    duration_penalty_threshold: float = 4.10
    duration_penalty_weight: float = 0.035
    safe_peak_accel: float = 2.20
    safe_peak_jerk: float = 4.80
    safe_duration: float = 4.70

    def __post_init__(self):
        if self.surrogate_kind not in ("monotone_bayes", "legacy_kernel"):
            raise ValueError("surrogate_kind must be monotone_bayes or legacy_kernel")
        if self.execution_belief not in ('calibrated','nominal','oracle'):
            raise ValueError('execution_belief must be calibrated, nominal or oracle')
        if self.process_rng_mode not in ('independent','legacy'):
            raise ValueError('process_rng_mode must be independent or legacy')
        if self.execution_noise not in ('low','medium','high'):
            raise ValueError('execution_noise must be low, medium or high')
        for name in ('seed','population_seed','calibration_seed'):
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,int) or value<0:
                raise ValueError(f'{name} must be a nonnegative integer')
        if isinstance(self.calibration_trials,bool) or not isinstance(self.calibration_trials,int) or self.calibration_trials<4:
            raise ValueError('calibration_trials must be an integer >= 4')
        ExecutionParameters(self.calibration_bias,1.)
        ExecutionParameters(self.assumed_execution_bias,self.assumed_execution_noise_scale)
        ExecutionSettings(x_min=self.x_min,x_max=self.x_max)


@dataclass(frozen=True)
class PolicySettings:
    tau: float
    x_min: float
    x_max: float
    candidate_count: int
    mc_samples: int
    surrogate_kind: str
    bayes_grid: PriorGrid


def policy_settings(config: Config) -> PolicySettings:
    return PolicySettings(**{field.name:getattr(config,field.name) for field in fields(PolicySettings)})


OBSERVED_HISTORY_FIELDS = ('target_command_x','peak_accel','peak_jerk','duration_s',
                           'realized_intensity','acceptable','discomfort')
EXECUTION_METADATA = ('population_seed','process_seed','process_rng_mode','calibration_seed','execution_belief',
    'true_execution_bias','true_execution_noise_scale','belief_execution_bias',
    'belief_execution_noise_scale','calibration_n_observations','calibration_n_used','calibration_n_clipped')


@dataclass(frozen=True)
class Passenger:
    participant_id: int
    acceptability_midpoint: float
    sensitivity: float
    noisiness: float
    risk_tolerance: float
    carryover_sensitivity: float


def criterion_boundary_tau(
    passenger: Passenger, tau: float, carryover_term: float = 0.0
) -> float:
    """Invert the simulator's noisy acceptance curve at the requested criterion.

    P(accept | m, history) = clip((1-eta) * sigmoid((midpoint-m-carryover)/s)
                                + eta/2, 0.02, 0.98).
    Return a finite crossing on the realized-intensity axis; do not clip truth
    to the command range or manufacture a crossing for unattainable criteria.
    """
    midpoint, slope, eta = (passenger.acceptability_midpoint,
                            passenger.sensitivity, passenger.noisiness)
    if not all(math.isfinite(value) for value in (midpoint, slope, eta, tau, carryover_term)):
        raise ValueError("Boundary inputs must be finite")
    if slope <= 0.0 or not 0.0 <= eta < 1.0:
        raise ValueError("Boundary requires positive sensitivity and 0 <= noisiness < 1")
    if not 0.02 < tau <= 0.98:
        raise ValueError("Criterion has no finite boundary under the clipped response model")
    probability = (tau - 0.5 * eta) / (1.0 - eta)
    if not 0.0 < probability < 1.0:
        raise ValueError("Criterion has no finite crossing under the feedback-noise mixture")
    return float(midpoint - carryover_term - slope * math.log(probability / (1.0 - probability)))


def sigmoid(x: float | np.ndarray) -> float | np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60, 60)))


def clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def likert(value: float) -> int:
    return int(np.clip(round(value), 1, 7))


def effective_intensity(
    peak_accel: float,
    peak_jerk: float,
    duration_s: float,
    config: Config,
    cumulative_discomfort: float = 0.0,
) -> float:
    jerk_penalty = config.jerk_penalty_weight * max(0.0, peak_jerk - config.jerk_penalty_threshold)
    duration_penalty = 0.0
    if config.include_time_effects:
        duration_penalty = config.duration_penalty_weight * max(0.0, duration_s - config.duration_penalty_threshold)
        duration_penalty += 0.004 * cumulative_discomfort
    return float(peak_accel + jerk_penalty + duration_penalty)


def make_passengers(config: Config) -> list[Passenger]:
    """Draw a reproducible population independently of process/calibration RNGs."""

    rng = np.random.default_rng(config.population_seed)
    passengers: list[Passenger] = []
    for pid in range(1, config.n_participants + 1):
        passengers.append(
            Passenger(
                participant_id=pid,
                acceptability_midpoint=clip(rng.normal(1.22, 0.27), 0.62, 1.88),
                sensitivity=clip(rng.uniform(0.10, 0.20), 0.08, 0.24),
                noisiness=clip(rng.uniform(0.03, 0.11) + config.feedback_noise, 0.03, 0.22),
                risk_tolerance=clip(rng.normal(0.0, 0.55), -1.25, 1.25),
                carryover_sensitivity=clip(rng.uniform(0.00, 0.05), 0.0, 0.08),
            )
        )
    return passengers


class ContinuousExecutionModel:
    """Continuous target command x -> realized measured motion features z."""

    def __init__(self, config: ExecutionSettings, parameters: ExecutionParameters):
        self.config = config
        self.parameters = parameters
        self.noise_scale = parameters.noise_scale

    def nominal_features(self, target_x: float) -> dict[str, float | bool]:
        target_x = clip(target_x, self.config.x_min, self.config.x_max)
        peak_accel = clip(0.05 + 0.94 * target_x + self.parameters.bias, 0.20, 2.35)
        peak_jerk = clip(0.58 + 1.74 * peak_accel + 0.10 * target_x, 0.30, 5.60)
        duration_s = clip(3.90 - 0.30 * peak_accel, 2.25, 4.65)
        rms_jerk = clip(0.55 * peak_jerk, 0.10, 3.40)
        speed_delta = clip(peak_accel * duration_s, 0.30, 8.20)
        intensity = effective_intensity(peak_accel, peak_jerk, duration_s, self.config)
        safety_violation = bool(
            peak_accel > self.config.safe_peak_accel
            or peak_jerk > self.config.safe_peak_jerk
            or duration_s > self.config.safe_duration
        )
        return {
            "target_command_x": target_x,
            "target_nominal_peak_accel": peak_accel,
            "target_nominal_peak_jerk": peak_jerk,
            "target_nominal_duration_s": duration_s,
            "target_nominal_intensity": intensity,
            "nominal_safety_violation": safety_violation,
            "nominal_speed_delta": speed_delta,
            "nominal_rms_jerk": rms_jerk,
        }

    def sample_features(
        self,
        target_x: float,
        rng: np.random.Generator,
        cumulative_discomfort: float = 0.0,
    ) -> dict[str, float | bool]:
        nominal = self.nominal_features(target_x)
        level = (target_x - self.config.x_min) / max(self.config.x_max - self.config.x_min, 1e-6)
        accel_sd = (0.045 + 0.055 * level) * self.noise_scale
        jerk_sd = (0.18 + 0.24 * level) * self.noise_scale
        duration_sd = 0.18 * self.noise_scale

        peak_accel = clip(
            rng.normal(float(nominal["target_nominal_peak_accel"]), accel_sd),
            0.20,
            2.40,
        )
        peak_jerk = clip(
            rng.normal(0.58 + 1.74 * peak_accel + 0.10 * target_x, jerk_sd),
            0.25,
            5.70,
        )
        rms_jerk = clip(rng.normal(0.55 * peak_jerk, 0.08 * self.noise_scale), 0.10, 3.50)
        duration_s = clip(
            rng.normal(3.90 - 0.30 * peak_accel, duration_sd),
            2.20,
            4.85,
        )
        speed_delta = clip(rng.normal(peak_accel * duration_s, 0.22 * self.noise_scale), 0.25, 8.50)
        intensity = effective_intensity(peak_accel, peak_jerk, duration_s, self.config, cumulative_discomfort)
        safety_violation = bool(
            peak_accel > self.config.safe_peak_accel
            or peak_jerk > self.config.safe_peak_jerk
            or duration_s > self.config.safe_duration
        )

        return {
            **nominal,
            "peak_accel": peak_accel,
            "peak_jerk": peak_jerk,
            "rms_jerk": rms_jerk,
            "duration_s": duration_s,
            "speed_delta": speed_delta,
            "realized_intensity": intensity,
            "realization_error": intensity - float(nominal["target_nominal_intensity"]),
            "abs_realization_error": abs(intensity - float(nominal["target_nominal_intensity"])),
            "command_tracking_error": peak_accel - target_x,
            "safety_violation": safety_violation,
            "protocol_deviation": safety_violation,
        }

    def sample_many(
        self,
        target_x: float,
        rng: np.random.Generator,
        n_samples: int,
        cumulative_discomfort: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        nominal = self.nominal_features(target_x)
        level = (target_x - self.config.x_min) / max(self.config.x_max - self.config.x_min, 1e-6)
        accel_sd = (0.045 + 0.055 * level) * self.noise_scale
        jerk_sd = (0.18 + 0.24 * level) * self.noise_scale
        duration_sd = 0.18 * self.noise_scale

        peak_accel = np.clip(
            rng.normal(float(nominal["target_nominal_peak_accel"]), accel_sd, n_samples),
            0.20,
            2.40,
        )
        peak_jerk = np.clip(
            rng.normal(0.58 + 1.74 * peak_accel + 0.10 * target_x, jerk_sd),
            0.25,
            5.70,
        )
        duration_s = np.clip(
            rng.normal(3.90 - 0.30 * peak_accel, duration_sd),
            2.20,
            4.85,
        )
        jerk_penalty = self.config.jerk_penalty_weight * np.maximum(
            0.0,
            peak_jerk - self.config.jerk_penalty_threshold,
        )
        duration_penalty = np.zeros(n_samples, dtype=float)
        if self.config.include_time_effects:
            duration_penalty = self.config.duration_penalty_weight * np.maximum(
                0.0,
                duration_s - self.config.duration_penalty_threshold,
            )
            duration_penalty += 0.004 * cumulative_discomfort
        intensities = peak_accel + jerk_penalty + duration_penalty
        violations = (
            (peak_accel > self.config.safe_peak_accel)
            | (peak_jerk > self.config.safe_peak_jerk)
            | (duration_s > self.config.safe_duration)
        )
        return intensities.astype(float), violations.astype(bool)


@dataclass
class PreparedExecution:
    truth: ContinuousExecutionModel
    belief: ContinuousExecutionModel
    calibration_observations: pd.DataFrame
    metadata: dict


def prepare_execution(config: Config, calibration_observations: pd.DataFrame | None = None) -> PreparedExecution:
    settings=ExecutionSettings(**{field.name:getattr(config,field.name) for field in fields(ExecutionSettings)})
    truth_parameters=ExecutionParameters(config.calibration_bias,{'low':.65,'medium':1.,'high':1.55}[config.execution_noise])
    truth=ContinuousExecutionModel(settings,truth_parameters)
    observations=pd.DataFrame(columns=CALIBRATION_FIELDS)
    n_used=n_clipped=0
    if config.execution_belief=='oracle':
        estimated=ExecutionParameters(truth_parameters.bias,truth_parameters.noise_scale)
    elif config.execution_belief=='nominal':
        estimated=ExecutionParameters(config.assumed_execution_bias,config.assumed_execution_noise_scale)
    else:
        if calibration_observations is None:
            rng=np.random.default_rng(np.random.SeedSequence([config.calibration_seed,0xCA1B]))
            span=config.x_max-config.x_min
            commands=np.linspace(config.x_min+.20*span,config.x_min+.80*span,config.calibration_trials)
            observations=pd.DataFrame([truth.sample_features(float(x),rng) for x in commands])[CALIBRATION_FIELDS]
        else:
            observations=calibration_observations.copy()
        fit=fit_execution_parameters(observations,settings)
        estimated=fit.parameters; n_used=fit.n_used; n_clipped=fit.n_clipped
        observations=observations[CALIBRATION_FIELDS].copy()
    belief=ContinuousExecutionModel(settings,estimated)
    metadata=dict(population_seed=config.population_seed,process_seed=config.seed,process_rng_mode=config.process_rng_mode,
        calibration_seed=config.calibration_seed,execution_belief=config.execution_belief,
        true_execution_bias=truth_parameters.bias,true_execution_noise_scale=truth_parameters.noise_scale,
        belief_execution_bias=estimated.bias,belief_execution_noise_scale=estimated.noise_scale,
        calibration_n_observations=len(observations),calibration_n_used=n_used,calibration_n_clipped=n_clipped)
    return PreparedExecution(truth,belief,observations,metadata)


class PassengerFeedbackModel:
    def __init__(self, config: Config, rng: np.random.Generator):
        self.config = config
        self.rng = rng

    def respond(
        self,
        passenger: Passenger,
        features: dict[str, float | bool],
        trial_id: int,
        cumulative_discomfort: float,
    ) -> dict[str, float | int | bool]:
        intensity = float(features["realized_intensity"])
        carryover = 0.0
        if self.config.include_time_effects:
            carryover = passenger.carryover_sensitivity * math.tanh(cumulative_discomfort / 25.0)
            carryover += 0.004 * trial_id

        latent = (passenger.acceptability_midpoint - intensity - carryover) / passenger.sensitivity
        p_accept = float(sigmoid(latent))
        p_accept = p_accept * (1.0 - passenger.noisiness) + 0.5 * passenger.noisiness
        p_accept = clip(p_accept, 0.02, 0.98)
        acceptable = bool(self.rng.random() < p_accept)

        peak_accel = float(features["peak_accel"])
        peak_jerk = float(features["peak_jerk"])
        comfort_raw = (
            7.25
            - 3.25 * max(0.0, intensity - 0.38) / 1.65
            - 0.22 * max(0.0, peak_jerk - 2.10)
            + 0.38 * passenger.risk_tolerance
            + self.rng.normal(0.0, 0.48)
        )
        comfort = likert(comfort_raw)
        discomfort = likert(
            8.05
            - comfort
            + 0.40 * max(0.0, intensity - passenger.acceptability_midpoint)
            + self.rng.normal(0, 0.42)
        )
        smoothness = likert(7.55 - 1.10 * max(0.0, peak_jerk - 0.85) + self.rng.normal(0, 0.45))
        perceived_safety = likert(
            comfort
            + 0.45 * passenger.risk_tolerance
            - 0.50 * max(0.0, intensity - passenger.acceptability_midpoint)
            - 0.08 * max(0.0, peak_accel - 1.70)
            + self.rng.normal(0, 0.45)
        )

        return {
            "p_accept_true": p_accept,
            "acceptable": acceptable,
            "comfort": comfort,
            "discomfort": discomfort,
            "smoothness": smoothness,
            "perceived_safety": perceived_safety,
            "carryover_term": carryover,
        }


class KernelAcceptanceSurrogate:
    """Historical kernel heuristic, retained only as an explicit comparison."""

    def __init__(self, tau: float):
        self.tau = tau
        self.intensities = np.array([], dtype=float)
        self.labels = np.array([], dtype=float)

    def fit(self, intensities: Iterable[float], labels: Iterable[int]) -> "KernelAcceptanceSurrogate":
        self.intensities = np.asarray(list(intensities), dtype=float)
        self.labels = np.asarray(list(labels), dtype=float)
        return self

    def predict_array(self, intensity_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_grid = np.asarray(intensity_grid, dtype=float)
        prior_boundary = 1.24
        prior = np.asarray(sigmoid((prior_boundary - x_grid) / 0.30), dtype=float)
        if len(self.intensities) == 0:
            return prior, np.full_like(x_grid, 0.42, dtype=float)

        bandwidth = 0.24
        distances = np.abs(x_grid[:, None] - self.intensities[None, :])
        weights = np.exp(-0.5 * (distances / bandwidth) ** 2)
        n_eff = weights.sum(axis=1)
        prior_strength = 1.25
        p = (weights @ self.labels + prior_strength * prior) / (n_eff + prior_strength)

        nearest = distances.min(axis=1)
        uncertainty_from_distance = np.minimum(0.35, nearest / 0.80)
        uncertainty_from_probability = np.sqrt(np.maximum(p * (1.0 - p), 1e-6) / (n_eff + 1.0))
        uncertainty = np.clip(uncertainty_from_distance + uncertainty_from_probability, 0.03, 0.55)
        return np.clip(p, 0.01, 0.99), uncertainty

    def predict(self, intensity: float) -> tuple[float, float]:
        p, u = self.predict_array(np.array([intensity], dtype=float))
        return float(p[0]), float(u[0])

    def estimate_boundary(self) -> float:
        grid = np.linspace(0.25, 2.35, 180)
        probabilities, _ = self.predict_array(grid)
        feasible = grid[probabilities >= self.tau]
        if len(feasible) == 0:
            return float(grid[np.argmin(np.abs(probabilities - self.tau))])
        return float(feasible.max())


class Policy(Protocol):
    name: str

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        ...


def fit_surrogate_from_history(config: Config | PolicySettings, history: list[dict[str, float | int | bool | str]]) -> KernelAcceptanceSurrogate | MonotoneBayesianLogistic:
    surrogate = (MonotoneBayesianLogistic(config.tau, grid=config.bayes_grid)
                 if config.surrogate_kind == "monotone_bayes"
                 else KernelAcceptanceSurrogate(config.tau))
    return surrogate.fit(
        [float(row["realized_intensity"]) for row in history],
        [int(bool(row["acceptable"])) for row in history],
    )


def recent_high_discomfort(history: list[dict[str, float | int | bool | str]]) -> bool:
    return bool(history and int(history[-1]["discomfort"]) >= 6)


class UncertainInputBO:
    name = "UncertainInputBO"

    def __init__(
        self,
        config: PolicySettings,
        execution_model: ContinuousExecutionModel,
        rng: np.random.Generator,
    ):
        self.config = config
        self.execution_model = execution_model
        self.rng = rng
        self.candidates = np.linspace(config.x_min, config.x_max, config.candidate_count)

    def _initial_design(self) -> list[float]:
        return [
            self.config.x_min + 0.12 * (self.config.x_max - self.config.x_min),
            self.config.x_min + 0.42 * (self.config.x_max - self.config.x_min),
            self.config.x_min + 0.66 * (self.config.x_max - self.config.x_min),
        ]

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        initial = self._initial_design()
        if trial_id <= len(initial):
            return float(initial[trial_id - 1])

        surrogate = fit_surrogate_from_history(self.config, history)
        cumulative_discomfort = float(sum(float(row["discomfort"]) for row in history))
        last_target = float(history[-1]["target_command_x"]) if history else self.config.x_min

        best_x = float(self.candidates[0])
        best_score = -float("inf")
        for target_x in self.candidates:
            sampled_intensities, violations = self.execution_model.sample_many(
                float(target_x),
                self.rng,
                self.config.mc_samples,
                cumulative_discomfort,
            )
            p_values, uncertainties = surrogate.predict_array(sampled_intensities)
            boundary_info = float(np.mean(-np.abs(p_values - self.config.tau)))
            uncertainty = float(np.mean(uncertainties))
            discomfort_risk = float(np.mean(np.maximum(0.0, self.config.tau - p_values)))
            safety_risk = float(np.mean(violations))
            repeat_penalty = 0.03 * sum(
                1 for row in history[-3:] if abs(float(row["target_command_x"]) - float(target_x)) < 0.08
            )
            downgrade_penalty = 0.0
            if recent_high_discomfort(history) and target_x >= last_target:
                downgrade_penalty = 0.75
            jitter = float(self.rng.normal(0.0, 0.002))

            score = (
                boundary_info
                + 0.40 * uncertainty
                - 0.70 * discomfort_risk
                - 1.20 * safety_risk
                - repeat_penalty
                - downgrade_penalty
                + jitter
            )
            if score > best_score:
                best_score = score
                best_x = float(target_x)
        return best_x


class NaiveContinuousBO:
    """Continuous BO baseline that ignores execution uncertainty in acquisition."""

    name = "NaiveContinuousBO"

    def __init__(
        self,
        config: PolicySettings,
        execution_model: ContinuousExecutionModel,
        rng: np.random.Generator,
    ):
        self.config = config
        self.execution_model = execution_model
        self.rng = rng
        self.candidates = np.linspace(config.x_min, config.x_max, config.candidate_count)

    def _initial_design(self) -> list[float]:
        return [
            self.config.x_min + 0.12 * (self.config.x_max - self.config.x_min),
            self.config.x_min + 0.42 * (self.config.x_max - self.config.x_min),
            self.config.x_min + 0.66 * (self.config.x_max - self.config.x_min),
        ]

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        initial = self._initial_design()
        if trial_id <= len(initial):
            return float(initial[trial_id - 1])

        surrogate = fit_surrogate_from_history(self.config, history)
        last_target = float(history[-1]["target_command_x"]) if history else self.config.x_min
        best_x = float(self.candidates[0])
        best_score = -float("inf")

        for target_x in self.candidates:
            nominal = self.execution_model.nominal_features(float(target_x))
            p_accept, uncertainty = surrogate.predict(float(nominal["target_nominal_intensity"]))
            boundary_info = -abs(p_accept - self.config.tau)
            discomfort_risk = max(0.0, self.config.tau - p_accept)
            safety_risk = 1.0 if bool(nominal["nominal_safety_violation"]) else 0.0
            downgrade_penalty = 0.0
            if recent_high_discomfort(history) and target_x >= last_target:
                downgrade_penalty = 0.75
            jitter = float(self.rng.normal(0.0, 0.002))

            score = boundary_info + 0.40 * uncertainty - 0.70 * discomfort_risk - 0.70 * safety_risk - downgrade_penalty + jitter
            if score > best_score:
                best_score = score
                best_x = float(target_x)
        return best_x


class RandomContinuous:
    name = "RandomContinuous"

    def __init__(self, config: PolicySettings, rng: np.random.Generator):
        self.config = config
        self.rng = rng

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        del history, trial_id
        return float(self.rng.uniform(self.config.x_min, self.config.x_max))


class GridContinuous:
    name = "GridContinuous"

    def __init__(self, config: PolicySettings):
        self.grid = np.linspace(config.x_min, config.x_max, 7)

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        del history
        return float(self.grid[(trial_id - 1) % len(self.grid)])


class Staircase:
    name = "Staircase"

    def __init__(self, config: PolicySettings):
        self.config = config
        self.current = 0.48 * config.x_min + 0.52 * config.x_max
        self.step = 0.22 * (config.x_max - config.x_min)
        self.last_direction = 0

    def choose(self, history: list[dict[str, float | int | bool | str]], trial_id: int) -> float:
        if trial_id == 1 or not history:
            return float(self.current)

        direction = 1 if bool(history[-1]["acceptable"]) else -1
        if self.last_direction and direction != self.last_direction:
            self.step = max(0.06, self.step * 0.72)
        self.last_direction = direction
        self.current = clip(self.current + direction * self.step, self.config.x_min, self.config.x_max)
        return float(self.current)


def build_policies(
    config: PolicySettings,
    execution_model: ContinuousExecutionModel,
    policy_rngs: list[np.random.Generator],
) -> list[Policy]:
    if len(policy_rngs)!=3:
        raise ValueError('Provide one explicit RNG for each randomized policy')
    return [
        UncertainInputBO(config, execution_model, policy_rngs[0]),
        NaiveContinuousBO(config, execution_model, policy_rngs[1]),
        RandomContinuous(config, policy_rngs[2]),
        GridContinuous(config),
        Staircase(config),
    ]


def run_algorithm(
    config: Config,
    passenger: Passenger,
    policy: Policy,
    execution_model: ContinuousExecutionModel,
    execution_rng: np.random.Generator,
    feedback_rng: np.random.Generator,
) -> list[dict[str, float | int | bool | str]]:
    rows: list[dict[str, float | int | bool | str]] = []
    history: list[dict[str, float | int | bool | str]] = []
    feedback_model = PassengerFeedbackModel(config, feedback_rng)
    cumulative_discomfort = 0.0
    baseline_boundary = criterion_boundary_tau(passenger, config.tau)
    surrogate = fit_surrogate_from_history(config, [])

    for trial_id in range(1, config.n_trials + 1):
        target_x = policy.choose(history, trial_id)
        motion = execution_model.sample_features(target_x, execution_rng, cumulative_discomfort)
        predicted_acceptability, probability_sd = surrogate.predict(float(motion["realized_intensity"]))
        feedback = feedback_model.respond(passenger, motion, trial_id, cumulative_discomfort)
        cumulative_discomfort += float(feedback["discomfort"])

        row: dict[str, float | int | bool | str] = {
            "scenario": config.scenario_name,
            "execution_noise": config.execution_noise,
            "calibration_bias": config.calibration_bias,
            "participant_id": passenger.participant_id,
            "algorithm": policy.name,
            "surrogate_kind": config.surrogate_kind,
            "trial_id": trial_id,
            "tau": config.tau,
            "acceptability_midpoint": passenger.acceptability_midpoint,
            "criterion_boundary_tau_baseline": baseline_boundary,
            "criterion_boundary_tau": criterion_boundary_tau(
                passenger, config.tau, float(feedback["carryover_term"])
            ),
            "passenger_sensitivity": passenger.sensitivity,
            "passenger_noisiness": passenger.noisiness,
            "passenger_risk_tolerance": passenger.risk_tolerance,
            **motion,
            **feedback,
            "predicted_acceptability_before_trial": predicted_acceptability,
            "predicted_probability_sd_before_trial": probability_sd,
        }
        row["predictive_brier_score"] = (predicted_acceptability - int(feedback["acceptable"]))**2
        row["overshoot"] = max(0.0, float(row["realized_intensity"]) - float(row["criterion_boundary_tau"]))
        row["legacy_midpoint_overshoot"] = max(
            0.0, float(row["realized_intensity"]) - passenger.acceptability_midpoint
        )
        row["cumulative_discomfort_after_trial"] = cumulative_discomfort

        history.append({key:row[key] for key in OBSERVED_HISTORY_FIELDS})
        surrogate = fit_surrogate_from_history(config, history)
        row["estimated_boundary_so_far"] = surrogate.estimate_boundary()
        if isinstance(surrogate, MonotoneBayesianLogistic):
            row.update(surrogate.boundary_summary())
            row["boundary_ci95_width"] = float(row["boundary_ci95_upper"]) - float(row["boundary_ci95_lower"])
            row["boundary_ci95_covers_truth"] = float(
                float(row["boundary_ci95_lower"]) <= float(row["criterion_boundary_tau"]) <= float(row["boundary_ci95_upper"])
            )
        else:
            for field in ("boundary_ci95_lower", "boundary_ci95_upper", "posterior_boundary_sd",
                          "boundary_mass_below_observed", "boundary_mass_above_observed",
                          "posterior_grid_edge_mass", "boundary_ci95_width", "boundary_ci95_covers_truth"):
                row[field] = float("nan")
            row["boundary_support"] = "legacy_no_posterior"
        row["signed_boundary_error_so_far"] = (
            float(row["estimated_boundary_so_far"]) - float(row["criterion_boundary_tau"])
        )
        row["boundary_error_so_far"] = abs(float(row["signed_boundary_error_so_far"]))
        row["legacy_midpoint_error_so_far"] = abs(
            float(row["estimated_boundary_so_far"]) - passenger.acceptability_midpoint
        )
        rows.append(row)

    return rows


def process_rng(config: Config, role: str, participant_id: int, algorithm_index: int) -> np.random.Generator:
    roles={'policy':1,'execution':2,'feedback':3}
    if role not in roles or participant_id<1 or not 0<=algorithm_index<5:
        raise ValueError('Invalid process stream identity')
    if config.process_rng_mode=='legacy':
        if role=='policy':
            seed=config.seed+participant_id*10000+(algorithm_index+1)*11
        else:
            seed=config.seed+participant_id*1009+algorithm_index*9176+(101 if role=='execution' else 202)
        return np.random.default_rng(seed)
    # Namespace and logical identities precede the root seed; no additive offsets.
    seed_sequence=np.random.SeedSequence([0x58505247,roles[role],participant_id,algorithm_index,config.seed])
    return np.random.default_rng(seed_sequence)


def run_scenario(config: Config, passengers: list[Passenger], prepared: PreparedExecution | None = None) -> pd.DataFrame:
    if prepared is None:
        prepared = prepare_execution(config)
    execution_model = prepared.truth
    rows: list[dict[str, float | int | bool | str]] = []

    for passenger in passengers:
        policy_rngs=[process_rng(config,'policy',passenger.participant_id,index) for index in range(3)]
        policies = build_policies(policy_settings(config), prepared.belief, policy_rngs)
        for algorithm_index, policy in enumerate(policies):
            execution_rng = process_rng(config,'execution',passenger.participant_id,algorithm_index)
            feedback_rng = process_rng(config,'feedback',passenger.participant_id,algorithm_index)
            rows.extend(run_algorithm(config, passenger, policy, execution_model, execution_rng, feedback_rng))
    trials = pd.DataFrame(rows)
    for key,value in prepared.metadata.items():
        trials[key]=value
    trials.attrs['calibration_observations']=prepared.calibration_observations.to_dict('records')
    return trials


def evaluate(trials: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if trials.empty or trials.surrogate_kind.isna().any() or trials.surrogate_kind.nunique() != 1:
        raise ValueError("Evaluate one nonempty surrogate dataset at a time")
    surrogate_kind = str(trials.surrogate_kind.iloc[0])
    provenance=trials[['scenario',*EXECUTION_METADATA]].drop_duplicates()
    if provenance.scenario.duplicated().any():
        raise ValueError('Each scenario must have one execution/population configuration')
    final = trials.sort_values("trial_id").groupby(["scenario", "participant_id", "algorithm"]).tail(1)
    participant = (
        trials.groupby(["scenario", "execution_noise", "participant_id", "algorithm"])
        .agg(
            n_trials=("trial_id", "max"),
            unacceptable_trials=("acceptable", lambda s: int((~s.astype(bool)).sum())),
            cumulative_discomfort=("discomfort", "sum"),
            max_discomfort=("discomfort", "max"),
            max_overshoot=("overshoot", "max"),
            mean_overshoot=("overshoot", "mean"),
            protocol_deviations=("protocol_deviation", lambda s: int(s.astype(bool).sum())),
            mean_abs_realization_error=("abs_realization_error", "mean"),
            mean_command_tracking_error=("command_tracking_error", "mean"),
            mean_predictive_brier_score=("predictive_brier_score", "mean"),
        )
        .reset_index()
        .merge(
            final[
                [
                    "scenario",
                    "participant_id",
                    "algorithm",
                    "tau",
                    "acceptability_midpoint",
                    "criterion_boundary_tau_baseline",
                    "criterion_boundary_tau",
                    "estimated_boundary_so_far",
                    "boundary_error_so_far",
                    "signed_boundary_error_so_far",
                    "legacy_midpoint_error_so_far",
                    "surrogate_kind",
                    "boundary_ci95_lower",
                    "boundary_ci95_upper",
                    "boundary_ci95_width",
                    "boundary_ci95_covers_truth",
                    "posterior_boundary_sd",
                    "posterior_grid_edge_mass",
                    "boundary_mass_below_observed",
                    "boundary_mass_above_observed",
                    "boundary_support",
                ]
            ],
            on=["scenario", "participant_id", "algorithm"],
            how="left",
        )
    )

    algorithm = (
        participant.groupby(["scenario", "execution_noise", "algorithm"])
        .agg(
            mean_boundary_error=("boundary_error_so_far", "mean"),
            median_boundary_error=("boundary_error_so_far", "median"),
            sd_boundary_error=("boundary_error_so_far", "std"),
            mean_signed_boundary_error=("signed_boundary_error_so_far", "mean"),
            mean_legacy_midpoint_error=("legacy_midpoint_error_so_far", "mean"),
            mean_predictive_brier_score=("mean_predictive_brier_score", "mean"),
            mean_boundary_ci95_width=("boundary_ci95_width", "mean"),
            boundary_ci95_coverage=("boundary_ci95_covers_truth", "mean"),
            max_posterior_grid_edge_mass=("posterior_grid_edge_mass", "max"),
            mean_unacceptable_trials=("unacceptable_trials", "mean"),
            mean_cumulative_discomfort=("cumulative_discomfort", "mean"),
            mean_max_discomfort=("max_discomfort", "mean"),
            mean_max_overshoot=("max_overshoot", "mean"),
            mean_protocol_deviations=("protocol_deviations", "mean"),
            mean_abs_realization_error=("mean_abs_realization_error", "mean"),
        )
        .reset_index()
    )

    diagnostics = (
        trials.groupby(["scenario", "execution_noise", "algorithm"])
        .agg(
            mean_realization_error=("realization_error", "mean"),
            mean_abs_realization_error=("abs_realization_error", "mean"),
            sd_realization_error=("realization_error", "std"),
            command_tracking_rmse=("command_tracking_error", lambda s: float(np.sqrt(np.mean(np.square(s))))),
            mean_target_command=("target_command_x", "mean"),
            mean_realized_intensity=("realized_intensity", "mean"),
        )
        .reset_index()
    )

    safety = (
        trials.groupby(["scenario", "execution_noise", "algorithm"])
        .agg(
            protocol_deviation_trials=("protocol_deviation", lambda s: int(s.astype(bool).sum())),
            safety_violation_trials=("safety_violation", lambda s: int(s.astype(bool).sum())),
            high_discomfort_trials=("discomfort", lambda s: int((s >= 6).sum())),
            total_trials=("trial_id", "count"),
            max_peak_accel=("peak_accel", "max"),
            max_peak_jerk=("peak_jerk", "max"),
        )
        .reset_index()
    )
    safety["protocol_deviation_rate"] = safety["protocol_deviation_trials"] / safety["total_trials"]

    sensitivity_rows: list[dict[str, float | str]] = []
    for (scenario,algorithm_name), group in participant.groupby(["scenario","algorithm"]):
        for execution_noise, sub in group.groupby("execution_noise"):
            sensitivity_rows.append(
                {
                    "scenario": scenario,
                    "sensitivity_type": "execution_noise",
                    "condition": str(execution_noise),
                    "algorithm": algorithm_name,
                    "mean_boundary_error": float(sub["boundary_error_so_far"].mean()),
                    "mean_unacceptable_trials": float(sub["unacceptable_trials"].mean()),
                    "mean_cumulative_discomfort": float(sub["cumulative_discomfort"].mean()),
                    "mean_abs_realization_error": float(sub["mean_abs_realization_error"].mean()),
                }
            )
    sensitivity = pd.DataFrame(sensitivity_rows)
    for table in (participant, algorithm, diagnostics, safety, sensitivity):
        table["surrogate_kind"] = surrogate_kind
    return tuple(table.merge(provenance,on='scenario',how='left',validate='many_to_one')
                 for table in (participant, algorithm, diagnostics, safety, sensitivity))


def sorted_algorithms(df: pd.DataFrame) -> list[str]:
    present = set(df["algorithm"].unique())
    return [algorithm for algorithm in ALGORITHM_ORDER if algorithm in present]


def default_participant_slice(participant: pd.DataFrame) -> pd.DataFrame:
    first_scenario = str(participant["scenario"].iloc[0])
    return participant[participant["scenario"] == first_scenario]


def plot_bar_metric(participant: pd.DataFrame, metric: str, ylabel: str, title: str, output_path: Path) -> None:
    default = default_participant_slice(participant)
    order = sorted_algorithms(default)
    means = default.groupby("algorithm")[metric].mean().reindex(order)
    ses = default.groupby("algorithm")[metric].sem().reindex(order)
    x = np.arange(len(order))
    plt.figure(figsize=(9, 5.2))
    plt.bar(x, means.values, yerr=ses.values, capsize=4, color=[COLORS[a] for a in order])
    plt.xticks(x, order, rotation=15, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def plot_box_metric(participant: pd.DataFrame, metric: str, ylabel: str, title: str, output_path: Path) -> None:
    default = default_participant_slice(participant)
    order = sorted_algorithms(default)
    data = [default[default["algorithm"] == algorithm][metric].values for algorithm in order]
    plt.figure(figsize=(9, 5.2))
    plt.boxplot(data, tick_labels=order)
    plt.xticks(rotation=15, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_tradeoff_plot(participant: pd.DataFrame, output_path: Path) -> None:
    means = (
        participant.groupby(["algorithm", "execution_noise"])
        .agg(
            boundary_error=("boundary_error_so_far", "mean"),
            cumulative_discomfort=("cumulative_discomfort", "mean"),
        )
        .reset_index()
    )

    plt.figure(figsize=(8.8, 5.6))
    for algorithm_name, sub in means.groupby("algorithm"):
        plt.scatter(
            sub["boundary_error"],
            sub["cumulative_discomfort"],
            s=72,
            label=algorithm_name,
            color=COLORS.get(algorithm_name),
            alpha=0.82,
        )
        for _, row in sub.iterrows():
            plt.annotate(
                str(row["execution_noise"]),
                (row["boundary_error"], row["cumulative_discomfort"]),
                fontsize=8,
                xytext=(4, 4),
                textcoords="offset points",
            )
    plt.xlabel("Mean absolute error against criterion boundary B(tau)")
    plt.ylabel("Mean cumulative discomfort")
    plt.title("Continuous simulation: accuracy-cost tradeoff")
    plt.grid(alpha=0.25)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_target_realized_scatter(trials: pd.DataFrame, output_path: Path) -> None:
    first_scenario = str(trials["scenario"].iloc[0])
    sub = trials[trials["scenario"] == first_scenario].copy()
    if len(sub) > 1200:
        sub = sub.sample(1200, random_state=BASE_SEED)

    plt.figure(figsize=(8.7, 5.6))
    for algorithm_name, group in sub.groupby("algorithm"):
        plt.scatter(
            group["target_command_x"],
            group["realized_intensity"],
            s=20,
            alpha=0.45,
            label=algorithm_name,
            color=COLORS.get(algorithm_name),
        )
    lo = min(float(sub["target_command_x"].min()), float(sub["realized_intensity"].min()))
    hi = max(float(sub["target_command_x"].max()), float(sub["realized_intensity"].max()))
    plt.plot([lo, hi], [lo, hi], color="#333333", linestyle="--", linewidth=1, label="target = realized")
    plt.xlabel("Target command x")
    plt.ylabel("Realized intensity m(z)")
    plt.title("Target command vs realized motion intensity")
    plt.grid(alpha=0.25)
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_example_trajectory(trials: pd.DataFrame, output_path: Path) -> None:
    first_scenario = str(trials["scenario"].iloc[0])
    participant_id = int(trials[trials["scenario"] == first_scenario]["participant_id"].min())
    sub = trials[(trials["scenario"] == first_scenario) & (trials["participant_id"] == participant_id)]
    order = sorted_algorithms(sub)
    fig, axes = plt.subplots(3, 2, figsize=(11, 9), sharex=True, sharey=True)
    axes = axes.ravel()

    for ax, algorithm_name in zip(axes, order):
        df = sub[sub["algorithm"] == algorithm_name].sort_values("trial_id")
        accepted = df[df["acceptable"].astype(bool)]
        rejected = df[~df["acceptable"].astype(bool)]

        ax.plot(df["trial_id"], df["estimated_boundary_so_far"], color="#1f77b4", linewidth=2, label="estimated boundary")
        if df["boundary_ci95_lower"].notna().any():
            ax.fill_between(df["trial_id"], df["boundary_ci95_lower"], df["boundary_ci95_upper"],
                            color="#1f77b4", alpha=.15, label="95% credible interval")
        ax.plot(df["trial_id"], df["criterion_boundary_tau"], color="#d62728", linestyle="--", linewidth=1.5, label="true B(tau, history)")
        ax.scatter(accepted["trial_id"], accepted["realized_intensity"], color="#2ca02c", label="acceptable", zorder=3)
        ax.scatter(rejected["trial_id"], rejected["realized_intensity"], color="#e45756", marker="x", s=55, label="unacceptable", zorder=3)
        ax.plot(df["trial_id"], df["target_command_x"], color="#777777", linestyle=":", linewidth=1.2, label="target x")
        ax.set_title(algorithm_name)
        ax.grid(alpha=0.22)
        ax.set_ylim(0.20, 2.35)

    for ax in axes[len(order) :]:
        ax.axis("off")
    axes[0].legend(loc="upper right", fontsize=7)
    fig.supxlabel("Trial")
    fig.supylabel("Motion intensity")
    fig.suptitle(f"Synthetic passenger {participant_id}, tau={float(sub['tau'].iloc[0]):.2f}", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_plots(trials: pd.DataFrame, participant: pd.DataFrame, output_dir: Path) -> None:
    plot_box_metric(
        participant,
        metric="boundary_error_so_far",
        ylabel="Final absolute error against B(tau)",
        title="Synthetic simulation: criterion-matched boundary error",
        output_path=output_dir / "continuous_boundary_error_by_algorithm.png",
    )
    plot_bar_metric(
        participant,
        metric="unacceptable_trials",
        ylabel="Unacceptable trials per participant",
        title="Continuous simulation: unacceptable trials by algorithm",
        output_path=output_dir / "continuous_unacceptable_trials_by_algorithm.png",
    )
    plot_bar_metric(
        participant,
        metric="cumulative_discomfort",
        ylabel="Cumulative discomfort score",
        title="Continuous simulation: cumulative discomfort by algorithm",
        output_path=output_dir / "continuous_cumulative_discomfort_by_algorithm.png",
    )
    save_tradeoff_plot(participant, output_dir / "continuous_accuracy_cost_tradeoff.png")
    save_target_realized_scatter(trials, output_dir / "continuous_target_vs_realized_scatter.png")
    plot_box_metric(
        participant,
        metric="mean_abs_realization_error",
        ylabel="Mean absolute realization error",
        title="Continuous simulation: realization error by algorithm",
        output_path=output_dir / "continuous_realization_error_by_algorithm.png",
    )
    plot_box_metric(
        participant,
        metric="max_overshoot",
        ylabel="Max realized overshoot above B(tau)",
        title="Synthetic simulation: criterion-boundary overshoot",
        output_path=output_dir / "continuous_overshoot_by_algorithm.png",
    )
    plot_bar_metric(
        participant,
        metric="protocol_deviations",
        ylabel="Protocol deviations per participant",
        title="Continuous simulation: safety/protocol deviations by algorithm",
        output_path=output_dir / "continuous_protocol_deviations_by_algorithm.png",
    )
    save_example_trajectory(trials, output_dir / "continuous_example_participant_trajectory.png")


def run_configurations(scenarios: list[Config], output_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not scenarios or len({s.surrogate_kind for s in scenarios}) != 1:
        raise ValueError("Provide non-empty scenarios for exactly one surrogate per output directory")
    if len({s.scenario_name for s in scenarios}) != len(scenarios):
        raise ValueError("Scenario names must be unique within an output directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_trials = []
    calibration_rows = []
    for scenario in scenarios:
        print(f"Running scenario: {scenario.scenario_name}")
        frame=run_scenario(scenario, make_passengers(scenario))
        for index,observation in enumerate(frame.attrs['calibration_observations'],start=1):
            calibration_rows.append({'scenario':scenario.scenario_name,'calibration_trial':index,
                'calibration_seed':scenario.calibration_seed,**observation})
        all_trials.append(frame)

    trials = pd.concat(all_trials, ignore_index=True)
    participant, algorithm, diagnostics, safety, sensitivity = evaluate(trials)

    trials.to_csv(output_dir / "continuous_trials.csv", index=False, encoding="utf-8-sig")
    participant.to_csv(output_dir / "continuous_participant_summary.csv", index=False, encoding="utf-8-sig")
    algorithm.to_csv(output_dir / "continuous_algorithm_summary.csv", index=False, encoding="utf-8-sig")
    diagnostics.to_csv(output_dir / "continuous_target_realized_diagnostics.csv", index=False, encoding="utf-8-sig")
    safety.to_csv(output_dir / "continuous_safety_protocol_summary.csv", index=False, encoding="utf-8-sig")
    sensitivity.to_csv(output_dir / "continuous_sensitivity_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(calibration_rows,columns=['scenario','calibration_trial','calibration_seed',*CALIBRATION_FIELDS]).to_csv(
        output_dir / 'continuous_execution_calibration.csv',index=False,encoding='utf-8-sig')
    save_plots(trials, participant, output_dir)
    return trials, participant, algorithm


def add_execution_cli_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--execution-belief',choices=['calibrated','nominal','oracle'],default='calibrated')
    parser.add_argument('--process-rng-mode',choices=['independent','legacy'],default='independent')
    parser.add_argument('--population-seed',type=int,default=BASE_SEED+101)
    parser.add_argument('--calibration-seed',type=int,default=BASE_SEED+303)
    parser.add_argument('--calibration-trials',type=int,default=40)
    parser.add_argument('--assumed-execution-bias',type=float,default=0.)
    parser.add_argument('--assumed-execution-noise-scale',type=float,default=.65)
    parser.add_argument('--true-execution-bias',type=float,default=0.)


def execution_cli_config(args) -> dict:
    return dict(execution_belief=args.execution_belief,process_rng_mode=args.process_rng_mode,population_seed=args.population_seed,
        calibration_seed=args.calibration_seed,calibration_trials=args.calibration_trials,
        assumed_execution_bias=args.assumed_execution_bias,assumed_execution_noise_scale=args.assumed_execution_noise_scale,
        calibration_bias=args.true_execution_bias)


def default_output_dir(surrogate: str, belief: str, poc: bool = False, rng_mode: str = 'independent') -> Path:
    suffix='_poc' if poc else ''
    if belief=='oracle' and rng_mode=='legacy':
        return ROOT/('outputs_bayesian'+suffix if surrogate=='monotone_bayes' else 'outputs_continuous'+suffix)
    if belief=='calibrated' and surrogate=='monotone_bayes':
        return ROOT/('outputs_execution_separated'+suffix)
    return ROOT/f'outputs_{surrogate}_{belief}{suffix}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surrogate", choices=["monotone_bayes", "legacy_kernel"], default="monotone_bayes")
    parser.add_argument("--output-dir", type=Path)
    add_execution_cli_arguments(parser)
    args = parser.parse_args()
    output_dir = args.output_dir or default_output_dir(args.surrogate,args.execution_belief,rng_mode=args.process_rng_mode)
    scenarios = [
        Config(execution_noise="low", scenario_name="continuous_low_noise", seed=BASE_SEED + 1, surrogate_kind=args.surrogate,**execution_cli_config(args)),
        Config(execution_noise="high", scenario_name="continuous_high_noise", seed=BASE_SEED + 2, surrogate_kind=args.surrogate,**execution_cli_config(args)),
    ]
    _, _, algorithm = run_configurations(scenarios, output_dir)

    print("Continuous-target uncertain-input simulation complete.")
    print(f"Output directory: {output_dir}")
    display_cols = [
        "scenario",
        "algorithm",
        "mean_boundary_error",
        "mean_unacceptable_trials",
        "mean_cumulative_discomfort",
        "mean_max_overshoot",
        "mean_abs_realization_error",
    ]
    print(algorithm[display_cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
