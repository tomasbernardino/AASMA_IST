from pathlib import Path

import numpy as np
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
from src.plotting import (
    plot_liquidity_confidence_bands,
    plot_metrics_comparison,
    plot_action_distributions,
)


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


def create_environment(rng=None):
    """
    Create the liquidity reserve environment.

    Stochastic parameters are used so that different seeds produce
    different trajectories, making multi-seed analysis meaningful.
    """
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
        rng=rng,
    )


def main():
    max_steps = 100
    n_seeds = 20

    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/figures").mkdir(parents=True, exist_ok=True)

    coordination_mechanisms = [
        IndependentCoordination(),
        VotingCoordination(),
        CentralizedCoordination(leader_index=1), # For now, the Trading/Opportunity Team is the leader in the centralized mechanism.
        DebateCoordination(),
    ]

    # Collect all histories (for plotting) and all per-run metrics (for CSV).
    all_histories = {}  # mechanism_name -> list of histories
    all_metrics = []

    for mechanism in coordination_mechanisms:
        mechanism_histories = []

        for seed in range(n_seeds):
            environment = create_environment()
            departments = create_departments()

            history, elapsed = run_simulation(
                environment=environment,
                departments=departments,
                coordination=mechanism,
                max_steps=max_steps,
                seed=seed,
            )

            mechanism_histories.append(history)

            run_metrics = compute_metrics(
                history=history,
                departments=departments,
                max_steps=max_steps,
                wall_time_seconds=elapsed,
                seed=seed,
            )

            all_metrics.append(run_metrics)

        all_histories[mechanism.name] = mechanism_histories

    # --- Detailed CSV: one row per (mechanism, seed) ---

    detailed_df = pd.DataFrame(all_metrics)
    detailed_df.to_csv("results/raw/detailed_runs.csv", index=False)

    # --- Aggregated CSV: one row per mechanism (mean ± std) ---

    numeric_cols = [
        "final_reserve", "average_reserve", "steps_survived",
        "total_withdrawal", "average_reward", "reward_inequality_gini",
        "total_messages", "total_rounds", "wall_time_seconds",
    ]

    aggregated_rows = []
    for mechanism in coordination_mechanisms:
        mech_df = detailed_df[detailed_df["mechanism"] == mechanism.name]
        row = {"mechanism": mechanism.name}
        for col in numeric_cols:
            row[f"{col}_mean"] = mech_df[col].mean()
            row[f"{col}_std"] = mech_df[col].std()
        row["crisis_rate"] = mech_df["liquidity_crisis"].mean()
        aggregated_rows.append(row)

    aggregated_df = pd.DataFrame(aggregated_rows)

    print("\n=== Aggregated Metrics (mean ± std over {} seeds) ===".format(n_seeds))
    print(aggregated_df.to_string(index=False))

    aggregated_df.to_csv("results/raw/aggregated_comparison.csv", index=False)

    # --- Plots ---

    plot_liquidity_confidence_bands(
        all_histories_by_mechanism=all_histories,
        max_steps=max_steps,
        output_path="results/figures/reserve_confidence_bands.png",
    )

    plot_metrics_comparison(
        aggregated_df=aggregated_df,
        output_path="results/figures/metrics_comparison.png",
    )

    plot_action_distributions(
        all_histories_by_mechanism=all_histories,
        output_path="results/figures/action_distributions.png",
    )


if __name__ == "__main__":
    main()
