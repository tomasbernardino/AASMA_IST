"""
Environmental sensitivity sweep.
Shows how robust each mechanism is to noisier recovery and more
frequent liquidity shocks.

"""

from pathlib import Path

import pandas as pd

from src.environment import LiquidityReserveEnvironment
from src.agents import Department
from src.compositions import make_compositions
from src.simulation import run_simulation
from src.metrics import compute_metrics
from src.plotting import plot_sensitivity_heatmap
from src.study_config import DEFAULT_SHOCK_MAGNITUDE, build_rule_based_mechanisms


create_departments = make_compositions(
    Department, reserve_capacity=100, exploration_rate=0.1,
)["standard"]


RECOVERY_NOISE_LEVELS = [0.01, 0.05, 0.15]
SHOCK_PROBABILITIES = [0.0, 0.05, 0.10]


def main():
    max_steps = 100
    n_seeds = 10

    Path("results/raw").mkdir(parents=True, exist_ok=True)
    Path("results/figures").mkdir(parents=True, exist_ok=True)

    mechanisms = build_rule_based_mechanisms()
    all_metrics = []

    for noise in RECOVERY_NOISE_LEVELS:
        for shock in SHOCK_PROBABILITIES:
            for mechanism in mechanisms:
                for seed in range(n_seeds):
                    environment = LiquidityReserveEnvironment(
                        recovery_noise_std=noise,
                        shock_probability=shock,
                        shock_magnitude=DEFAULT_SHOCK_MAGNITUDE,
                    )
                    departments = create_departments()

                    history, elapsed = run_simulation(
                        environment=environment,
                        departments=departments,
                        coordination=mechanism,
                        max_steps=max_steps,
                        seed=seed,
                    )

                    run_metrics = compute_metrics(
                        history=history,
                        departments=departments,
                        max_steps=max_steps,
                        wall_time_seconds=elapsed,
                        seed=seed,
                    )
                    run_metrics["recovery_noise_std"] = noise
                    run_metrics["shock_probability"] = shock
                    run_metrics["composition"] = "standard"
                    all_metrics.append(run_metrics)

    detailed_df = pd.DataFrame(all_metrics)
    detailed_df.to_csv("results/raw/sensitivity_detailed.csv", index=False)

    # Aggregate per (mechanism, cell).
    agg_rows = []
    for noise in RECOVERY_NOISE_LEVELS:
        for shock in SHOCK_PROBABILITIES:
            for mechanism in mechanisms:
                cell = detailed_df[
                    (detailed_df["mechanism"] == mechanism.name) &
                    (detailed_df["recovery_noise_std"] == noise) &
                    (detailed_df["shock_probability"] == shock)
                ]
                agg_rows.append({
                    "mechanism": mechanism.name,
                    "recovery_noise_std": noise,
                    "shock_probability": shock,
                    "crisis_rate": cell["liquidity_crisis"].mean(),
                    "average_reserve_mean": cell["average_reserve"].mean(),
                    "average_reserve_std": cell["average_reserve"].std(),
                    "steps_survived_mean": cell["steps_survived"].mean(),
                    "total_withdrawal_mean": cell["total_withdrawal"].mean(),
                    "override_rate_mean": cell["debate_override_rate"].mean(),
                    "mean_absolute_reward_gap_mean": cell["mean_absolute_reward_gap"].mean(),
                    "reward_std_mean": cell["reward_std"].mean(),
                    "reward_range_mean": cell["reward_range"].mean(),
                    "leader_index": (
                        cell["leader_index"].dropna().iloc[0]
                        if "leader_index" in cell and cell["leader_index"].notna().any()
                        else None
                    ),
                    "leader_name": (
                        cell["leader_name"].dropna().iloc[0]
                        if "leader_name" in cell and cell["leader_name"].notna().any()
                        else None
                    ),
                    "leader_role": (
                        cell["leader_role"].dropna().iloc[0]
                        if "leader_role" in cell and cell["leader_role"].notna().any()
                        else None
                    ),
                })

    aggregated_df = pd.DataFrame(agg_rows)
    aggregated_df.to_csv("results/raw/sensitivity_aggregated.csv", index=False)

    print("\n=== Sensitivity crisis_rate by mechanism x (noise, shock) ===")
    pivot = aggregated_df.pivot_table(
        index="mechanism",
        columns=["recovery_noise_std", "shock_probability"],
        values="crisis_rate",
    )
    print(pivot.to_string())

    plot_sensitivity_heatmap(
        aggregated_df=aggregated_df,
        value_col="crisis_rate",
        output_path="results/figures/sensitivity_heatmap.png",
    )


if __name__ == "__main__":
    main()
