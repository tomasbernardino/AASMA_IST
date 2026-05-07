"""
Entry point for running the simulation with LLM-based departments.

This is separate from main.py so that the baseline rule-based results
remain untouched and reproducible. Both entry points use the same
simulation loop, environment, coordination mechanisms, and metrics.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.environment import LiquidityReserveEnvironment
from src.llm_agents import LLMDepartment
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


def create_llm_departments(model="gpt-4o-mini", temperature=0.3):
    """
    Create LLM-based departments with the same roles as the baseline.

    Each department uses OpenAI to decide its withdrawal policy instead
    of hard-coded rules.
    """
    return [
        LLMDepartment("Growth Department", "profit", model=model, temperature=temperature),
        LLMDepartment("Trading/Opportunity Team", "profit", model=model, temperature=temperature),
        LLMDepartment("Compliance Department", "sustainability", model=model, temperature=temperature),
        LLMDepartment("Operations Department", "balanced", model=model, temperature=temperature),
        LLMDepartment("Risk Department", "risk_averse", model=model, temperature=temperature),
    ]


def create_environment(rng=None):
    """
    Create the liquidity reserve environment.

    Uses the same stochastic parameters as the baseline for fair comparison.
    """
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
        rng=rng,
    )


def main():
    # LLM simulations are expensive, so fewer seeds than the baseline.
    max_steps = 100
    n_seeds = 5

    output_dir = Path("results/llm")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)

    coordination_mechanisms = [
        IndependentCoordination(),
        VotingCoordination(),
        CentralizedCoordination(leader_index=1),
        DebateCoordination(),
    ]

    all_histories = {}
    all_metrics = []

    for mechanism in coordination_mechanisms:
        print(f"\n--- {mechanism.name} ---")
        mechanism_histories = []

        for seed in range(n_seeds):
            print(f"  seed {seed}/{n_seeds - 1} ...", end=" ", flush=True)

            environment = create_environment()
            departments = create_llm_departments()

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
            print(f"steps={len(history)}, time={elapsed:.1f}s")

        all_histories[mechanism.name] = mechanism_histories

    # --- Detailed CSV ---

    detailed_df = pd.DataFrame(all_metrics)
    detailed_df.to_csv(output_dir / "detailed_runs.csv", index=False)

    # --- Aggregated CSV ---

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

    print("\n=== LLM Aggregated Metrics (mean ± std over {} seeds) ===".format(n_seeds))
    print(aggregated_df.to_string(index=False))

    aggregated_df.to_csv(output_dir / "aggregated_comparison.csv", index=False)

    # --- Plots ---

    plot_liquidity_confidence_bands(
        all_histories_by_mechanism=all_histories,
        max_steps=max_steps,
        output_path=str(output_dir / "figures" / "reserve_confidence_bands.png"),
    )

    plot_metrics_comparison(
        aggregated_df=aggregated_df,
        output_path=str(output_dir / "figures" / "metrics_comparison.png"),
    )

    plot_action_distributions(
        all_histories_by_mechanism=all_histories,
        output_path=str(output_dir / "figures" / "action_distributions.png"),
    )


if __name__ == "__main__":
    main()
