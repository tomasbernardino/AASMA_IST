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


def plot_sensitivity_heatmap(
    aggregated_df,
    value_col="crisis_rate",
    output_path=None,
):
    """
    One heatmap per mechanism, showing how `value_col` varies across the
    environmental sensitivity grid (recovery_noise_std × shock_probability).

    aggregated_df must have columns: mechanism, recovery_noise_std,
    shock_probability, and `value_col`.
    """
    required = {"mechanism", "recovery_noise_std", "shock_probability", value_col}
    if not required.issubset(aggregated_df.columns):
        return

    mechanisms = sorted(aggregated_df["mechanism"].unique())
    noise_levels = sorted(aggregated_df["recovery_noise_std"].unique(), reverse=True)
    shock_levels = sorted(aggregated_df["shock_probability"].unique())

    n = len(mechanisms)
    ncols = 4
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(3.4 * ncols, 3.2 * nrows), squeeze=False)

    vmin, vmax = (0.0, 1.0) if value_col == "crisis_rate" else (
        float(aggregated_df[value_col].min()),
        float(aggregated_df[value_col].max()),
    )

    last_im = None
    for idx, mech in enumerate(mechanisms):
        ax = axes[idx // ncols][idx % ncols]
        sub = aggregated_df[aggregated_df["mechanism"] == mech]
        grid = np.full((len(noise_levels), len(shock_levels)), np.nan)
        for _, row in sub.iterrows():
            i = noise_levels.index(row["recovery_noise_std"])
            j = shock_levels.index(row["shock_probability"])
            grid[i, j] = row[value_col]

        im = ax.imshow(grid, cmap="Reds", vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(range(len(shock_levels)))
        ax.set_xticklabels([f"{s:g}" for s in shock_levels], fontsize=8)
        ax.set_yticks(range(len(noise_levels)))
        ax.set_yticklabels([f"{n:g}" for n in noise_levels], fontsize=8)
        ax.set_title(mech, fontsize=10)
        ax.set_xlabel("shock prob", fontsize=8)
        ax.set_ylabel("recovery noise", fontsize=8)

        for i in range(len(noise_levels)):
            for j in range(len(shock_levels)):
                v = grid[i, j]
                if not np.isnan(v):
                    color = "white" if v > (vmin + vmax) / 2 else "black"
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                            color=color, fontsize=8)
        last_im = im

    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    fig.suptitle(
        f"Environmental sensitivity: {value_col} per mechanism",
        fontsize=13,
    )
    if last_im is not None:
        fig.colorbar(last_im, ax=axes.ravel().tolist(), shrink=0.6, label=value_col)

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()


def plot_model_comparison(aggregated_df, composition="standard", output_path=None):
    """Three-panel grouped-bar comparison across (mechanism x model):
    crisis rate, social welfare, mean LLM latency per call.

    Rows with a null/empty `model` are dropped — those are rule-based
    mechanisms with no model dimension to compare across.
    """
    if "model" not in aggregated_df.columns or "composition" not in aggregated_df.columns:
        return

    df = aggregated_df[aggregated_df["composition"] == composition].copy()
    df = df[df["model"].notna() & (df["model"].astype(str) != "")]
    if df.empty:
        return

    metric_specs = [
        ("crisis_rate", None, "Crisis rate (lower is better)"),
        ("social_welfare_mean", "social_welfare_std", "Social welfare (higher is better)"),
        ("llm_avg_latency_ms_mean", None, "Mean LLM latency per call (ms)"),
    ]
    metric_specs = [
        (m, s, lbl) for m, s, lbl in metric_specs
        if m in df.columns and df[m].notna().any()
    ]
    if not metric_specs:
        return

    models = sorted(df["model"].unique())
    mechanisms = list(dict.fromkeys(df["mechanism"].tolist()))

    fig, axes = plt.subplots(1, len(metric_specs),
                             figsize=(5.0 * len(metric_specs), 5.0))
    if len(metric_specs) == 1:
        axes = [axes]

    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
              "#3ba272", "#fc8452"]
    bar_width = 0.8 / max(len(models), 1)
    x = np.arange(len(mechanisms))

    for ax, (mean_col, std_col, label) in zip(axes, metric_specs):
        for i, model in enumerate(models):
            sub = df[df["model"] == model].set_index("mechanism")
            means = [
                sub.loc[m, mean_col] if m in sub.index else np.nan
                for m in mechanisms
            ]
            stds = None
            if std_col and std_col in sub.columns:
                stds = [
                    sub.loc[m, std_col] if m in sub.index else 0.0
                    for m in mechanisms
                ]
            offset = (i - (len(models) - 1) / 2) * bar_width
            ax.bar(
                x + offset,
                means,
                width=bar_width,
                yerr=stds,
                capsize=2,
                color=colors[i % len(colors)],
                label=model.split("/")[-1],
                alpha=0.9,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(mechanisms, rotation=45, ha="right", fontsize=8)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", alpha=0.3)

    axes[0].legend(title="Model", fontsize=8, title_fontsize=9, loc="best")
    plt.suptitle(
        f"Multi-model comparison ({composition} composition)",
        fontsize=13,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()


def plot_cost_vs_welfare_pareto(aggregated_df, composition="standard", output_path=None):
    """
    Two-panel Pareto-style scatter: coordination cost on x, benefit on y.

    Left panel:  cost (total_messages) vs social welfare.
    Right panel: cost (total_messages) vs crisis avoidance (1 - crisis_rate).

    A mechanism is Pareto-dominated if some other mechanism is cheaper AND
    better on the same axis. The Pareto frontier is drawn as a polyline
    through non-dominated points.

    For LLM-heavy runs prefer `cost_col="llm_calls_mean"` (passed via
    aggregated_df produced by the LLM sweep) so the cost reflects what
    actually matters there. Falls back to total_messages_mean.
    """
    if "composition" not in aggregated_df.columns:
        return
    df = aggregated_df[aggregated_df["composition"] == composition].copy()
    if df.empty:
        return

    if "llm_calls_mean" in df.columns and df["llm_calls_mean"].notna().any() \
            and df["llm_calls_mean"].fillna(0).max() > 0:
        cost_col = "llm_calls_mean"
        cost_label = "Mean LLM calls per run"
    else:
        cost_col = "total_messages_mean"
        cost_label = "Mean coordination messages per run"

    df["crisis_avoid"] = 1.0 - df["crisis_rate"]

    panels = [
        ("social_welfare_mean", "social_welfare_std", "Social welfare"),
        ("crisis_avoid", None, "Crisis-avoidance rate (1 - crisis_rate)"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
              "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc"]
    mechanisms = list(dict.fromkeys(df["mechanism"].tolist()))

    for ax, (y_col, y_err_col, y_label) in zip(axes, panels):
        if y_col not in df.columns:
            ax.set_visible(False)
            continue

        x = df[cost_col].to_numpy(dtype=float)
        y = df[y_col].to_numpy(dtype=float)
        y_err = (
            df[y_err_col].to_numpy(dtype=float)
            if y_err_col and y_err_col in df.columns else None
        )

        for i, (mech, xi, yi) in enumerate(zip(df["mechanism"], x, y)):
            ax.errorbar(
                xi, yi,
                yerr=(y_err[i] if y_err is not None else 0),
                fmt="o", markersize=9, color=colors[i % len(colors)],
                capsize=3, alpha=0.9,
            )
            ax.annotate(
                mech, (xi, yi),
                xytext=(6, 6), textcoords="offset points",
                fontsize=8, color="black",
            )

        # Pareto frontier: lower x is better, higher y is better.
        order = np.argsort(x)
        front_x, front_y = [], []
        best_y = -np.inf
        for idx in order:
            if y[idx] >= best_y:
                front_x.append(x[idx])
                front_y.append(y[idx])
                best_y = y[idx]
        if len(front_x) >= 2:
            ax.plot(front_x, front_y, "--", color="gray", alpha=0.6,
                    linewidth=1.5, label="Pareto frontier")
            ax.legend(loc="lower right", fontsize=9)

        ax.set_xlabel(cost_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        ax.grid(alpha=0.3)

    plt.suptitle(
        f"Coordination cost vs benefit ({composition} composition) — "
        f"upper-left is best",
        fontsize=13,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()


def plot_per_role_rewards(aggregated_df, composition="standard", output_path=None):
    """
    One subplot per role showing mean reward per mechanism on the chosen
    composition. The point of this view: social_welfare (a sum across roles
    whose utility functions are on different scales) hides whether a
    mechanism is winning by helping everyone or by trading off one role
    against another. Per-role bars make that explicit.

    aggregated_df must contain 'reward_<role>_mean' columns (added by
    metrics.compute_metrics + experiment.run_experiment_sweep).
    """
    if "composition" not in aggregated_df.columns:
        return

    df = aggregated_df[aggregated_df["composition"] == composition]
    if df.empty:
        return

    role_specs = [
        ("reward_profit", "Profit"),
        ("reward_sustainability", "Sustainability"),
        ("reward_balanced", "Balanced"),
        ("reward_risk_averse", "Risk-averse"),
    ]
    role_specs = [
        (key, label) for key, label in role_specs
        if f"{key}_mean" in df.columns and df[f"{key}_mean"].notna().any()
    ]
    if not role_specs:
        return

    mechanisms = list(dict.fromkeys(df["mechanism"].tolist()))
    n_roles = len(role_specs)
    ncols = min(n_roles, 4)
    nrows = (n_roles + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.0 * ncols, 3.8 * nrows),
                             squeeze=False)

    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272", "#fc8452"]
    x = np.arange(len(mechanisms))

    for idx, (key, label) in enumerate(role_specs):
        ax = axes[idx // ncols][idx % ncols]
        sub = df.set_index("mechanism")
        means = [sub.loc[m, f"{key}_mean"] if m in sub.index else np.nan for m in mechanisms]
        stds = [sub.loc[m, f"{key}_std"] if m in sub.index else 0.0 for m in mechanisms]
        bar_colors = [colors[i % len(colors)] for i in range(len(mechanisms))]

        ax.bar(x, means, yerr=stds, capsize=3, alpha=0.85, color=bar_colors)
        ax.set_xticks(x)
        ax.set_xticklabels(mechanisms, rotation=45, ha="right", fontsize=8)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", alpha=0.3)
        ax.axhline(0, color="black", linewidth=0.6)

    for idx in range(n_roles, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    plt.suptitle(
        f"Mean reward per role and mechanism ({composition} composition)",
        fontsize=13,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()


def plot_scale_robustness(aggregated_df, composition="standard", output_path=None):
    """
    Grouped bars showing whether the mechanism ranking is preserved across
    L/M/H withdrawal scales.

    For the chosen composition (default 'standard'), plot crisis_rate,
    social_welfare and average_reserve as grouped bars: x=mechanism,
    one bar per scale within each mechanism group. Parallel bars across
    scales = ranking preserved; crossings = scale-dependent ranking.

    aggregated_df must contain 'scale' and 'composition' columns.
    """
    if "scale" not in aggregated_df.columns or "composition" not in aggregated_df.columns:
        return

    df = aggregated_df[aggregated_df["composition"] == composition]
    if df.empty:
        return

    metrics = [
        ("crisis_rate", None, "Crisis rate"),
        ("social_welfare_mean", "social_welfare_std", "Social welfare"),
        ("average_reserve_mean", "average_reserve_std", "Avg reserve"),
    ]

    scales = sorted(df["scale"].unique())
    mechanisms = list(dict.fromkeys(df["mechanism"].tolist()))

    fig, axes = plt.subplots(1, len(metrics), figsize=(5.5 * len(metrics), 5))

    colors = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
    bar_width = 0.8 / len(scales)
    x = np.arange(len(mechanisms))

    for ax, (mean_col, std_col, label) in zip(axes, metrics):
        if mean_col not in df.columns:
            ax.set_visible(False)
            continue

        for i, scale_name in enumerate(scales):
            scale_df = df[df["scale"] == scale_name].set_index("mechanism")
            means = [scale_df.loc[m, mean_col] if m in scale_df.index else np.nan for m in mechanisms]
            stds = None
            if std_col and std_col in scale_df.columns:
                stds = [scale_df.loc[m, std_col] if m in scale_df.index else 0.0 for m in mechanisms]

            offset = (i - (len(scales) - 1) / 2) * bar_width
            ax.bar(
                x + offset,
                means,
                width=bar_width,
                yerr=stds,
                capsize=2,
                color=colors[i % len(colors)],
                label=scale_name,
                alpha=0.9,
            )

        ax.set_xticks(x)
        ax.set_xticklabels(mechanisms, rotation=45, ha="right", fontsize=8)
        ax.set_title(label, fontsize=11)
        ax.grid(axis="y", alpha=0.3)

    axes[0].legend(title="L/M/H scale", fontsize=8, title_fontsize=9, loc="best")
    plt.suptitle(
        f"Robustness of mechanism ranking to L/M/H scale ({composition} composition)",
        fontsize=13,
    )
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, bbox_inches="tight", dpi=150)

    plt.close()
