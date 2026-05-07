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
