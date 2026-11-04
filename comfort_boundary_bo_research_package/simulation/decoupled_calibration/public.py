"""Policy information whitelist. No simulation truth belongs in this module.

Acceleration units are m/s². Responses are 1=acceptable, 0=unacceptable.
Realized acceleration is observed without additional measurement error.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Observation:
    trial: int
    target: float
    realized: float
    acceptable: int


@dataclass(frozen=True)
class Estimate:
    boundary: float
    lower: float
    upper: float
    support: str
    edge_mass: float


@dataclass(frozen=True)
class ExecutionBelief:
    """Public independently calibrated affine Gaussian execution estimate.

    Actual X is clipped to [lower, upper]. Acquisition quadrature must preserve
    clipping atoms. This object contains estimates, never true vehicle fields.
    """
    intercept: float
    gain: float
    sd: float
    lower: float = 0.0
    upper: float = 3.0


@dataclass(frozen=True)
class PolicyConfig:
    tau: float = 0.70
    lower: float = 0.0
    upper: float = 3.0
    targets: tuple[float, ...] = tuple(i / 10 for i in range(31))
    midpoint_nodes: int = 81
    slope_nodes: int = 41
    quadrature_nodes: int = 7


class Policy(Protocol):
    def suggest(self) -> float: ...
    def observe(self, observation: Observation) -> None: ...
    def estimate(self) -> Estimate: ...
