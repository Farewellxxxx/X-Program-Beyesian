"""Plot the four predeclared stationary probability curves at matched B and W."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))

from comfort_boundary_bo_research_package.simulation.decoupled_calibration import passenger
from comfort_boundary_bo_research_package.simulation.finite_budget import population


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    if output.suffix.lower() != ".png":
        parser.error("--output must be a PNG path")

    boundary, width, tau, lapse = 1.5, 0.70, 0.70, 0.10
    xs = np.linspace(0, 3, 601)
    styles = [
        ("logistic", "Logistic", "#0072B2", "-"),
        ("probit", "Probit", "#009E73", "--"),
        ("lapse_logistic", "Logistic, lapse .10", "#D55E00", "-."),
        ("gumbel", "Gumbel survival", "#7A4D91", ":"),
    ]
    fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
    derivatives = {}
    for family, name, color, linestyle in styles:
        observer = population.passenger_from_latent(boundary, width, family, tau, lapse)
        derivative = population.local_derivative(observer)
        derivatives[family] = derivative
        ax.plot(xs, [observer.probability(float(x)) for x in xs], color=color,
                linestyle=linestyle, linewidth=2.3, label=f"{name}  ({derivative:.3f})")
    ax.vlines(boundary, 0, tau, linestyle="--", color="#777777", linewidth=1)
    ax.hlines(tau, 0, boundary, linestyle="--", color="#777777", linewidth=1)
    ax.scatter(boundary, tau, color="#222222", s=24, zorder=5)
    ax.annotate(r"$B=1.5,\ \tau=0.70$", xy=(boundary, tau), xytext=(1.68, 0.83),
                arrowprops={"arrowstyle": "-", "color": "#777777"}, fontsize=11)
    ax.set(xlim=(0, 3), ylim=(0, 1.02), xlabel=r"Realized acceleration (m/s$^2$)",
           ylabel="Probability of acceptance", title=r"Stationary observers at matched boundary and $W=0.70$")
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.7, 0.8, 1.0])
    ax.grid(alpha=0.16)
    ax.legend(loc="lower left", title="Observer  (derivative at B)", framealpha=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    files = [Path(__file__), Path(passenger.__file__), Path(population.__file__)]
    provenance = dict(
        generator=Path(__file__).resolve().relative_to(ROOT).as_posix(),
        source_sha256={p.resolve().relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in files},
        output_name=output.name, output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        matplotlib=matplotlib.__version__, numpy=np.__version__,
        B=boundary, W=width, tau=tau, lapse_logistic_random_answer_probability=lapse,
        x_range=[0, 3], x_points=len(xs), derivative_at_B=derivatives,
    )
    output.with_name(output.stem + "_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    main()
