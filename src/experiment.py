"""
Shared experiment sweep runner.

Both main.py (rule-based) and main_llm.py (LLM-based) sweep the same
Cartesian product of (scale x composition x mechanism x seed), aggregate the
same way, and produce the same plots. This module owns that pipeline so the
entry points can stay thin.
"""

from pathlib import Path

import pandas as pd

from src.simulation import ACTION_TO_WITHDRAWAL, run_simulation
from src.metrics import compute_metrics
from src.plotting import (
    plot_liquidity_confidence_bands,
    plot_metrics_comparison,
    plot_action_distributions,
    plot_reserve_by_composition,
    plot_metrics_by_composition,
    plot_scale_robustness,
    plot_per_role_rewards,
    plot_cost_vs_welfare_pareto,
)


DEFAULT_SCALES = {"standard": ACTION_TO_WITHDRAWAL}

# Multi-scale registry for the rule-based scale-robustness experiment.
# `standard` matches the runtime default; the others widen / asymmetrize /
# compress the L→M→H spread to test whether mechanism rankings hold up.
SCALES = {
    "standard":   ACTION_TO_WITHDRAWAL,
    "wide":       {"L": 1.0, "M": 3.0, "H": 5.0},
    "asymmetric": {"L": 0.5, "M": 2.0, "H": 4.0},
    "compressed": {"L": 1.0, "M": 1.5, "H": 2.0},
}

NUMERIC_COLS = [
    "final_reserve", "average_reserve", "steps_survived",
    "total_withdrawal", "average_reward", "social_welfare",
    "reward_inequality_gini",
    "total_messages", "total_rounds", "wall_time_seconds", "debate_override_rate",
]

# Per-role reward columns, surfaced by metrics.py from each composition. Not
# every composition contains every role (e.g. "aggressive" has no sustainability
# member), so missing roles simply produce NaN in the aggregation.
ROLE_REWARD_COLS = [
    "reward_profit", "reward_sustainability", "reward_balanced", "reward_risk_averse",
]

LLM_COLS = ["llm_calls", "llm_total_latency_ms", "llm_avg_latency_ms"]


def run_experiment_sweep(
    coordination_mechanisms,
    compositions,
    env_factory,
    n_seeds,
    max_steps,
    output_dir,
    scales=None,
    progress=False,
):
    """
    Run a full sweep and produce CSVs + figures.

    Parameters
    ----------
    coordination_mechanisms : list[CoordinationMechanism]
    compositions : dict[str, callable]
        Maps composition name to a factory returning a fresh list of departments.
    env_factory : callable
        Zero-arg callable returning a fresh LiquidityReserveEnvironment.
    n_seeds : int
    max_steps : int
    output_dir : str | Path
        Directory under which `raw/` (CSVs) and `figures/` (PNGs) are written.
    scales : dict[str, dict[str, float]] | None
        Maps scale name to {"L": x, "M": y, "H": z}. Defaults to a single
        "standard" scale of {1, 2, 3}. The legacy single-scale plots are fed
        the scale-"standard" slice so they remain meaningful.
    progress : bool
        If True, prints a one-line update per run (useful for slow LLM sweeps).

    Returns
    -------
    aggregated_df : pandas.DataFrame
    """
    scales = scales or DEFAULT_SCALES
    sweep_scales = len(scales) > 1

    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw"
    fig_dir = output_dir / "figures"
    raw_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Single-scale histories (standard scale only) feed the time-series plots,
    # which were designed before the scale dimension existed.
    all_histories = {}
    all_metrics = []

    for scale_name, scale_map in scales.items():
        for composition_name, dept_factory in compositions.items():
            for mechanism in coordination_mechanisms:
                mechanism_histories = []

                for seed in range(n_seeds):
                    if progress:
                        print(
                            f"  [{scale_name}/{composition_name}/{mechanism.name}] "
                            f"seed={seed}",
                            flush=True,
                        )

                    environment = env_factory()
                    departments = dept_factory()

                    history, elapsed = run_simulation(
                        environment=environment,
                        departments=departments,
                        coordination=mechanism,
                        max_steps=max_steps,
                        seed=seed,
                        action_to_withdrawal=scale_map,
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
                    run_metrics["scale"] = scale_name
                    all_metrics.append(run_metrics)

                if scale_name == "standard":
                    key = f"{composition_name}/{mechanism.name}"
                    all_histories[key] = mechanism_histories

    detailed_df = pd.DataFrame(all_metrics)
    detailed_df.to_csv(raw_dir / "detailed_runs.csv", index=False)

    aggregated_df = _aggregate(detailed_df, scales, compositions, coordination_mechanisms)
    aggregated_df.to_csv(raw_dir / "aggregated_comparison.csv", index=False)

    print(
        f"\n=== Aggregated Metrics (mean +/- std over {n_seeds} seeds, "
        f"standard scale) ==="
    )
    print(
        aggregated_df[aggregated_df["scale"] == "standard"].to_string(index=False)
    )

    aggregated_standard = aggregated_df[aggregated_df["scale"] == "standard"].copy()

    plot_liquidity_confidence_bands(
        all_histories_by_mechanism=all_histories,
        max_steps=max_steps,
        output_path=str(fig_dir / "reserve_confidence_bands.png"),
    )
    plot_metrics_comparison(
        aggregated_df=aggregated_standard,
        output_path=str(fig_dir / "metrics_comparison.png"),
    )
    plot_action_distributions(
        all_histories_by_mechanism=all_histories,
        output_path=str(fig_dir / "action_distributions.png"),
    )
    plot_reserve_by_composition(
        all_histories_by_mechanism=all_histories,
        max_steps=max_steps,
        output_path=str(fig_dir / "reserve_by_composition.png"),
    )
    plot_metrics_by_composition(
        aggregated_df=aggregated_standard,
        output_path=str(fig_dir / "metrics_by_composition.png"),
    )

    plot_per_role_rewards(
        aggregated_df=aggregated_standard,
        composition="standard",
        output_path=str(fig_dir / "per_role_rewards.png"),
    )
    plot_cost_vs_welfare_pareto(
        aggregated_df=aggregated_standard,
        composition="standard",
        output_path=str(fig_dir / "pareto_cost_vs_welfare.png"),
    )

    if sweep_scales:
        plot_scale_robustness(
            aggregated_df=aggregated_df,
            composition="standard",
            output_path=str(fig_dir / "scale_robustness.png"),
        )

    return aggregated_df


def _aggregate(detailed_df, scales, compositions, coordination_mechanisms):
    rows = []
    for scale_name in scales:
        for composition_name in compositions:
            for mechanism in coordination_mechanisms:
                mech_df = detailed_df[
                    (detailed_df["mechanism"] == mechanism.name) &
                    (detailed_df["composition"] == composition_name) &
                    (detailed_df["scale"] == scale_name)
                ]
                row = {
                    "mechanism": mechanism.name,
                    "composition": composition_name,
                    "scale": scale_name,
                }
                if "model" in mech_df.columns:
                    models = [
                        model for model in mech_df["model"].dropna().astype(str)
                        if model
                    ]
                    if models:
                        row["model"] = models[0]
                for col in NUMERIC_COLS:
                    if col in mech_df.columns:
                        row[f"{col}_mean"] = mech_df[col].mean()
                        row[f"{col}_std"] = mech_df[col].std()
                row["crisis_rate"] = mech_df["liquidity_crisis"].mean()
                for col in ROLE_REWARD_COLS:
                    if col in mech_df.columns:
                        row[f"{col}_mean"] = mech_df[col].mean()
                        row[f"{col}_std"] = mech_df[col].std()
                for col in LLM_COLS:
                    if col in mech_df.columns:
                        row[f"{col}_mean"] = mech_df[col].mean()
                rows.append(row)
    return pd.DataFrame(rows)
