# src/plotting.py

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_liquidity_histories(histories_by_mechanism, output_path=None):
    """
    Plot liquidity reserve level over time for several mechanisms.

    histories_by_mechanism:
        dictionary where:
            key = mechanism name
            value = simulation history
    """

    plt.figure(figsize=(10, 6))

    for mechanism_name, history in histories_by_mechanism.items():
        timesteps = [step["t"] for step in history]
        reserves = [step["new_reserve"] for step in history]

        plt.plot(timesteps, reserves, label=mechanism_name)

    plt.xlabel("Time step")
    plt.ylabel("Liquidity reserve level")
    plt.title("Liquidity reserve sustainability by coordination mechanism")
    plt.legend()
    plt.grid(True)

    if output_path:
        plt.savefig(output_path, bbox_inches="tight")

    plt.close()


def plot_liquidity_confidence_bands(all_histories_by_mechanism, max_steps, output_path=None):
    """
    Plot mean reserve trajectory with shaded confidence bands (± 1 std)
    across multiple seeds for each mechanism.

    all_histories_by_mechanism:
        dictionary where:
            key = mechanism name
            value = list of histories (one per seed)

    max_steps:
        Maximum number of time steps (used to align trajectories).
    """

    plt.figure(figsize=(10, 6))

    for mechanism_name, histories_list in all_histories_by_mechanism.items():
        # Pad shorter histories to max_steps using their last reserve value.
        reserves_matrix = []
        for history in histories_list:
            reserves = [step["new_reserve"] for step in history]
            last_value = reserves[-1] if reserves else 0
            padded = reserves + [last_value] * (max_steps - len(reserves))
            reserves_matrix.append(padded)

        reserves_matrix = np.array(reserves_matrix)
        mean_reserves = np.mean(reserves_matrix, axis=0)
        std_reserves = np.std(reserves_matrix, axis=0)
        timesteps = np.arange(max_steps)

        plt.plot(timesteps, mean_reserves, label=mechanism_name)
        plt.fill_between(
            timesteps,
            mean_reserves - std_reserves,
            mean_reserves + std_reserves,
            alpha=0.2,
        )

    plt.xlabel("Time step")
    plt.ylabel("Liquidity reserve level")
    plt.title("Reserve trajectory by mechanism (mean ± 1 std)")
    plt.legend()
    plt.grid(True)

    if output_path:
        plt.savefig(output_path, bbox_inches="tight")

    plt.close()


def plot_metrics_comparison(aggregated_df, output_path=None):
    """
    Bar chart comparing key metrics across mechanisms, with error bars.

    aggregated_df:
        DataFrame with columns: mechanism, metric_name_mean, metric_name_std
        (one row per mechanism).
    """

    metric_keys = [
        ("average_reserve_mean", "average_reserve_std", "Average reserve"),
        ("steps_survived_mean", "steps_survived_std", "Steps survived"),
        ("average_reward_mean", "average_reward_std", "Average reward"),
        ("reward_inequality_gini_mean", "reward_inequality_gini_std", "Gini coefficient"),
    ]

    fig, axes = plt.subplots(1, len(metric_keys), figsize=(5 * len(metric_keys), 5))

    mechanisms = aggregated_df["mechanism"].tolist()
    x = np.arange(len(mechanisms))

    for ax, (mean_col, std_col, label) in zip(axes, metric_keys):
        means = aggregated_df[mean_col].values
        stds = aggregated_df[std_col].values

        ax.bar(x, means, yerr=stds, capsize=4, alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(mechanisms, rotation=30, ha="right", fontsize=9)
        ax.set_title(label)
        ax.grid(axis="y", alpha=0.3)

    plt.suptitle("Metric comparison by coordination mechanism", fontsize=13)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight")

    plt.close()


def plot_action_distributions(all_histories_by_mechanism, output_path=None):
    """
    Stacked bar chart showing the proportion of L / M / H actions
    for each coordination mechanism (aggregated across all seeds and steps).

    all_histories_by_mechanism:
        dictionary where:
            key = mechanism name
            value = list of histories (one per seed)
    """

    action_labels = ["L", "M", "H"]
    mechanism_names = list(all_histories_by_mechanism.keys())
    proportions = {label: [] for label in action_labels}

    for mechanism_name in mechanism_names:
        histories_list = all_histories_by_mechanism[mechanism_name]

        # Count all final actions across all seeds and all steps.
        counts = {"L": 0, "M": 0, "H": 0}
        total = 0
        for history in histories_list:
            for step in history:
                for action in step["final_actions"]:
                    counts[action] += 1
                    total += 1

        for label in action_labels:
            proportions[label].append(counts[label] / total if total > 0 else 0)

    x = np.arange(len(mechanism_names))
    width = 0.6

    fig, ax = plt.subplots(figsize=(8, 5))

    bottom = np.zeros(len(mechanism_names))
    colors = ["#4caf50", "#ff9800", "#f44336"]  # green, orange, red

    for label, color in zip(action_labels, colors):
        values = np.array(proportions[label])
        ax.bar(x, values, width, bottom=bottom, label=label, color=color, alpha=0.85)
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels(mechanism_names, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Proportion of actions")
    ax.set_title("Action distribution by coordination mechanism")
    ax.legend(title="Action")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight")

    plt.close()


def plot_reserve_by_composition(all_histories_by_mechanism, max_steps, output_path=None):
    """
    Plot mean reserve trajectories grouped by composition.

    Produces one subplot per composition (e.g. standard, aggressive,
    conservative), each showing all mechanisms overlaid with confidence
    bands.

    Keys in all_histories_by_mechanism must be formatted as
    "composition/mechanism".
    """
    # Group keys by composition.
    compositions = {}
    for key in all_histories_by_mechanism:
        if "/" not in key:
            continue
        comp, mech = key.split("/", 1)
        compositions.setdefault(comp, []).append(key)

    if not compositions:
        return

    n_comps = len(compositions)
    fig, axes = plt.subplots(1, n_comps, figsize=(7 * n_comps, 5), squeeze=False)
    axes = axes[0]

    for ax, (comp_name, keys) in zip(axes, sorted(compositions.items())):
        for key in keys:
            mech_name = key.split("/", 1)[1]
            histories_list = all_histories_by_mechanism[key]

            reserves_matrix = []
            for history in histories_list:
                reserves = [step["new_reserve"] for step in history]
                last_value = reserves[-1] if reserves else 0
                padded = reserves + [last_value] * (max_steps - len(reserves))
                reserves_matrix.append(padded)

            reserves_matrix = np.array(reserves_matrix)
            mean_r = np.mean(reserves_matrix, axis=0)
            std_r = np.std(reserves_matrix, axis=0)
            timesteps = np.arange(max_steps)

            ax.plot(timesteps, mean_r, label=mech_name)
            ax.fill_between(timesteps, mean_r - std_r, mean_r + std_r, alpha=0.15)

        ax.set_title(f"{comp_name.capitalize()} composition", fontsize=12)
        ax.set_xlabel("Time step")
        ax.set_ylabel("Reserve level")
        ax.legend(fontsize=7, loc="lower left")
        ax.grid(True, alpha=0.3)

    plt.suptitle("Reserve trajectory by composition (mean ± 1 std)", fontsize=14)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()


def plot_metrics_by_composition(aggregated_df, output_path=None):
    """
    Bar chart comparing key metrics across mechanisms, with one row of
    subplots per composition.

    aggregated_df must contain a 'composition' column.
    """
    metric_keys = [
        ("average_reserve_mean", "average_reserve_std", "Avg reserve"),
        ("steps_survived_mean", "steps_survived_std", "Steps survived"),
        ("social_welfare_mean", "social_welfare_std", "Social welfare"),
        ("reward_inequality_gini_mean", "reward_inequality_gini_std", "Gini"),
        ("debate_override_rate_mean", "debate_override_rate_std", "Override rate"),
    ]

    if "composition" not in aggregated_df.columns:
        return

    compositions = sorted(aggregated_df["composition"].unique())
    n_comps = len(compositions)
    n_metrics = len(metric_keys)

    fig, axes = plt.subplots(
        n_comps, n_metrics,
        figsize=(4 * n_metrics, 4.5 * n_comps),
        squeeze=False,
    )

    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452"]

    for row, comp_name in enumerate(compositions):
        comp_df = aggregated_df[aggregated_df["composition"] == comp_name]
        mechanisms = comp_df["mechanism"].tolist()
        x = np.arange(len(mechanisms))

        for col, (mean_col, std_col, label) in enumerate(metric_keys):
            ax = axes[row][col]
            means = comp_df[mean_col].values
            stds = comp_df[std_col].values

            bar_colors = [colors[i % len(colors)] for i in range(len(mechanisms))]
            ax.bar(x, means, yerr=stds, capsize=3, alpha=0.85, color=bar_colors)
            ax.set_xticks(x)
            ax.set_xticklabels(mechanisms, rotation=45, ha="right", fontsize=7)
            ax.grid(axis="y", alpha=0.3)

            if row == 0:
                ax.set_title(label, fontsize=11)
            if col == 0:
                ax.set_ylabel(comp_name.capitalize(), fontsize=11, fontweight="bold")

    plt.suptitle("Metrics comparison by composition and mechanism", fontsize=14)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()
