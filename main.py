from pathlib import Path

import numpy as np
import pandas as pd

from src.environment import LiquidityReserveEnvironment
from src.agents import Department
from src.coordination import (
    IndependentCoordination,
    VotingCoordination,
    AdaptiveVotingCoordination,
    CentralizedCoordination,
    StructuredDebateCoordination,
)
from src.simulation import run_simulation
from src.metrics import compute_metrics
from src.plotting import (
    plot_liquidity_confidence_bands,
    plot_metrics_comparison,
    plot_action_distributions,
)


def create_departments():
    """Standard composition: 2 profit + 1 sustainability + 1 balanced + 1 risk_averse."""
    return [
        Department("Growth Department", "profit", reserve_capacity=100),
        Department("Trading/Opportunity Team", "profit", reserve_capacity=100),
        Department("Compliance Department", "sustainability", reserve_capacity=100),
        Department("Operations Department", "balanced", reserve_capacity=100),
        Department("Risk Department", "risk_averse", reserve_capacity=100),
    ]


def create_departments_aggressive():
    """Aggressive composition: 3 profit + 1 balanced + 1 risk_averse."""
    return [
        Department("Growth Department", "profit", reserve_capacity=100),
        Department("Trading/Opportunity Team", "profit", reserve_capacity=100),
        Department("Investment Department", "profit", reserve_capacity=100),
        Department("Operations Department", "balanced", reserve_capacity=100),
        Department("Risk Department", "risk_averse", reserve_capacity=100),
    ]


def create_departments_conservative():
    """Conservative composition: 1 profit + 2 sustainability + 1 balanced + 1 risk_averse."""
    return [
        Department("Growth Department", "profit", reserve_capacity=100),
        Department("Compliance Department", "sustainability", reserve_capacity=100),
        Department("ESG Department", "sustainability", reserve_capacity=100),
        Department("Operations Department", "balanced", reserve_capacity=100),
        Department("Risk Department", "risk_averse", reserve_capacity=100),
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
        AdaptiveVotingCoordination(),
        CentralizedCoordination(leader_index=1, name_suffix="_profit"),
        CentralizedCoordination(leader_index=2, name_suffix="_sustainability"),
        CentralizedCoordination(leader_index=4, name_suffix="_risk_averse"),
        StructuredDebateCoordination(),
    ]

    compositions = {
        "standard": create_departments,
        "aggressive": create_departments_aggressive,
        "conservative": create_departments_conservative,
    }

    # Collect all histories (for plotting) and all per-run metrics (for CSV).
    all_histories = {}  # mechanism_name -> list of histories
    all_metrics = []

    for composition_name, dept_factory in compositions.items():
        for mechanism in coordination_mechanisms:
            mechanism_histories = []

            for seed in range(n_seeds):
                environment = create_environment()
                departments = dept_factory()

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
                run_metrics["composition"] = composition_name
                all_metrics.append(run_metrics)

            key = f"{composition_name}/{mechanism.name}"
            all_histories[key] = mechanism_histories

    # --- Detailed CSV: one row per (mechanism, seed) ---

    detailed_df = pd.DataFrame(all_metrics)
    detailed_df.to_csv("results/raw/detailed_runs.csv", index=False)

    # --- Aggregated CSV: one row per mechanism (mean ± std) ---

    numeric_cols = [
        "final_reserve", "average_reserve", "steps_survived",
        "total_withdrawal", "average_reward", "reward_inequality_gini",
        "total_messages", "total_rounds", "wall_time_seconds", "debate_override_rate",
    ]

    llm_cols = ["llm_calls", "llm_total_latency_ms", "llm_avg_latency_ms"]

    aggregated_rows = []
    for composition_name in compositions:
        for mechanism in coordination_mechanisms:
            mech_df = detailed_df[
                (detailed_df["mechanism"] == mechanism.name) &
                (detailed_df["composition"] == composition_name)
            ]
            row = {"mechanism": mechanism.name, "composition": composition_name}
            for col in numeric_cols:
                if col in mech_df.columns:
                    row[f"{col}_mean"] = mech_df[col].mean()
                    row[f"{col}_std"] = mech_df[col].std()
            row["crisis_rate"] = mech_df["liquidity_crisis"].mean()
            for col in llm_cols:
                if col in mech_df.columns:
                    row[f"{col}_mean"] = mech_df[col].mean()
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
