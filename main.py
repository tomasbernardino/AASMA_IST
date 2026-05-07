from pathlib import Path

import pandas as pd

from src.environment import LiquidityReserveEnvironment
from src.agents import Department
from src.coordination import (
    IndependentCoordination,
    VotingCoordination,
    CentralizedCoordination,
    DebateCoordination,
)
from src.simulation import run_simulation
from src.metrics import compute_metrics
from src.plotting import plot_liquidity_histories


def create_departments():
    """
    Create the same group of departments for each mechanism.

    To compare coordination fairly, the department composition must be equal.
    """
    return [
        Department("Growth Department", "profit"),
        Department("Trading/Opportunity Team", "profit"),
        Department("Compliance Department", "sustainability"),
        Department("Operations Department", "balanced"),
        Department("Risk Department", "risk_averse"),
    ]


def create_environment():
    return LiquidityReserveEnvironment() # Using default parameters for the environment, this can be customized if needed.
  

def main():
    max_steps = 100
    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/figures").mkdir(parents=True, exist_ok=True)

    coordination_mechanisms = [
        IndependentCoordination(),
        VotingCoordination(),
        CentralizedCoordination(leader_index=1), # For now, the Trading/Opportunity Team is the leader in the centralized mechanism.
        DebateCoordination(),
    ]

    histories = {}
    metrics = []

    for mechanism in coordination_mechanisms:
        environment = create_environment()
        departments = create_departments()

        history = run_simulation(
            environment=environment,
            departments=departments,
            coordination=mechanism,
            max_steps=max_steps,
        )

        histories[mechanism.name] = history

        run_metrics = compute_metrics(
            history=history,
            departments=departments,
            max_steps=max_steps,
        )

        metrics.append(run_metrics)

    metrics_df = pd.DataFrame(metrics)

    print("\n=== Comparison Metrics ===")
    print(metrics_df)

    metrics_df.to_csv("results/raw/first_comparison.csv", index=False)

    plot_liquidity_histories(
        histories_by_mechanism=histories,
        output_path="results/figures/liquidity_comparison.png",
    )


if __name__ == "__main__":
    main()
