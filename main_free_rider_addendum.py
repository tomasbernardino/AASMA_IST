"""Free-rider addendum: re-run only the free_rider composition for the LLM
track, then re-consolidate the canonical CSVs and save the three
history-based figures next to the existing 3-composition originals with
a `_free_rider` suffix.

When `main_llm.py` ran originally, it generated histories in RAM and used
them to render `reserve_confidence_bands.png`, `action_distributions.png`,
and `reserve_by_composition.png`. Those histories are not persisted to disk,
so once `main_llm.py` exits there is no way to reconstruct them later.
`free_rider` was then added to `COMPOSITION_SPECS`; the existing figures
therefore only reflect three of the four compositions.

This script:
  1. Re-runs `free_rider × 7 mechanisms × 1 seed` per model
     (uses `LLM_MODELS` from .env if multi-model, else `LLM_MODEL`)
  2. Replaces the existing `free_rider` rows in
     `results/llm/<model>/raw/detailed_runs.csv` with these fresh draws
     so the CSV and the new history figures come from the same session
  3. Rebuilds `aggregated_comparison.csv` per model and
     `results/llm/raw/multi_model_aggregated.csv`
  4. Regenerates the CSV-derived figures that depend on free_rider data
     (`metrics_by_composition.png`)
  5. Saves the three history-based figures alongside the originals as
     `*_free_rider.png` so they can be read side-by-side

Cost: ~3 h across deepseek + gemma + openai with all 7 mechanisms.
"""

import os
import shutil
import sys
from pathlib import Path

import pandas as pd

from src.environment import LiquidityReserveEnvironment
from src.compositions import COMPOSITION_SPECS
from src.experiment import run_experiment_sweep
from src.plotting import (
    plot_cost_vs_welfare_pareto,
    plot_metrics_by_composition,
    plot_metrics_comparison,
    plot_model_comparison,
    plot_per_role_rewards,
)


TEMP_BASE = Path("results/.tmp_free_rider_addendum")
CANONICAL_BASE = Path("results/llm")
HISTORY_FIGURES = [
    "reserve_confidence_bands.png",
    "action_distributions.png",
    "reserve_by_composition.png",
]

NUMERIC_COLS = [
    "final_reserve", "average_reserve", "steps_survived", "total_withdrawal",
    "average_reward", "social_welfare", "mean_absolute_reward_gap",
    "reward_std", "reward_range",
    "total_messages", "total_rounds", "wall_time_seconds", "debate_override_rate",
]
ROLE_REWARD_COLS = [
    "reward_profit", "reward_sustainability", "reward_balanced", "reward_risk_averse",
]
LLM_COLS = ["llm_calls", "llm_total_latency_ms", "llm_avg_latency_ms"]


def make_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )


def free_rider_only(dept_class, **dept_kwargs):
    spec = COMPOSITION_SPECS["free_rider"]
    return {
        "free_rider": lambda: [
            dept_class(name, role, **dept_kwargs) for name, role in spec
        ]
    }


def rebuild_aggregated(detailed_df):
    rows = []
    for (mech, comp, scale), g in detailed_df.groupby(
        ["mechanism", "composition", "scale"], sort=False,
    ):
        row = {"mechanism": mech, "composition": comp, "scale": scale}
        if "model" in g.columns:
            models = [m for m in g["model"].dropna().astype(str) if m]
            if models:
                row["model"] = models[0]
        for col in NUMERIC_COLS + ROLE_REWARD_COLS + LLM_COLS:
            if col in g.columns:
                row[f"{col}_mean"] = g[col].mean()
                row[f"{col}_std"] = g[col].std()
        row["crisis_rate"] = g["liquidity_crisis"].mean()
        rows.append(row)
    return pd.DataFrame(rows)


def slug(model):
    return model.replace("/", "_").replace(":", "-")


def run_sweep_for_model(model, max_steps, temperature):
    from src.coordination import (
        CentralizedRoleCoordination,
        IndependentCoordination,
        LLMCentralizedCoordination,
        StructuredDebateCoordination,
    )
    from src.crewai_coordination import CrewAIDebateCoordination
    from src.llm_agents import LLMDepartment

    mechanisms = [
        IndependentCoordination(),
        CentralizedRoleCoordination("profit"),
        CentralizedRoleCoordination("sustainability"),
        CentralizedRoleCoordination("risk_averse"),
        StructuredDebateCoordination(),
        LLMCentralizedCoordination(model=model, temperature=temperature),
        CrewAIDebateCoordination(
            model=model, temperature=temperature, allow_delegation=False,
        ),
    ]
    compositions = free_rider_only(
        LLMDepartment, model=model, temperature=temperature,
    )
    temp_dir = TEMP_BASE / slug(model)
    run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions,
        env_factory=make_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(temp_dir),
        scales=None,
        progress=True,
    )


def merge_back(model):
    s = slug(model)
    temp_dir = TEMP_BASE / s
    canon_dir = CANONICAL_BASE / s

    canon_det = pd.read_csv(canon_dir / "raw" / "detailed_runs.csv")
    new_fr = pd.read_csv(temp_dir / "raw" / "detailed_runs.csv")
    non_fr = canon_det[canon_det["composition"] != "free_rider"]
    merged = pd.concat([non_fr, new_fr], ignore_index=True)
    merged.to_csv(canon_dir / "raw" / "detailed_runs.csv", index=False)
    print(
        f"  {s}: detailed_runs.csv -> {len(merged)} rows "
        f"({len(non_fr)} kept + {len(new_fr)} new free_rider)",
        flush=True,
    )

    agg = rebuild_aggregated(merged)
    agg.to_csv(canon_dir / "raw" / "aggregated_comparison.csv", index=False)

    agg_std = agg[agg["scale"] == "standard"]
    fig_dir = canon_dir / "figures"
    plot_metrics_comparison(
        agg_std, output_path=str(fig_dir / "metrics_comparison.png"),
    )
    plot_per_role_rewards(
        agg_std, composition="standard",
        output_path=str(fig_dir / "per_role_rewards.png"),
    )
    plot_metrics_by_composition(
        agg_std, output_path=str(fig_dir / "metrics_by_composition.png"),
    )
    plot_cost_vs_welfare_pareto(
        agg_std, composition="standard",
        output_path=str(fig_dir / "pareto_cost_vs_welfare.png"),
    )

    for src_name in HISTORY_FIGURES:
        src = temp_dir / "figures" / src_name
        dst = fig_dir / src_name.replace(".png", "_free_rider.png")
        if src.exists():
            shutil.copy(src, dst)
            print(f"    addendum figure: {dst}", flush=True)

    return agg


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY", file=sys.stderr)
        sys.exit(1)

    from src.llm_client import get_llm_model

    models_env = os.environ.get("LLM_MODELS")
    models = [
        m.strip()
        for m in (models_env or get_llm_model()).split(",")
        if m.strip()
    ]
    max_steps = int(os.environ.get("LLM_MAX_STEPS", "20"))
    temperature = 0.3

    TEMP_BASE.mkdir(parents=True, exist_ok=True)

    # Phase 1: run free_rider-only sweep into temp tree
    for model in models:
        print(f"\n{'=' * 78}\n  Model: {model}\n{'=' * 78}", flush=True)
        run_sweep_for_model(model, max_steps, temperature)

    # Phase 2: merge back into canonical tree
    print("\n=== Merging back into canonical tree ===", flush=True)
    all_aggs = []
    for model in models:
        all_aggs.append(merge_back(model))

    # Phase 3: rebuild multi-model aggregate
    combined = pd.concat(all_aggs, ignore_index=True)
    combined.to_csv(
        CANONICAL_BASE / "raw" / "multi_model_aggregated.csv", index=False,
    )
    plot_model_comparison(
        combined, composition="standard",
        output_path=str(CANONICAL_BASE / "figures" / "model_comparison.png"),
    )
    print(
        f"\nmulti_model_aggregated.csv -> {len(combined)} rows", flush=True,
    )

    # Phase 4: cleanup temp tree
    shutil.rmtree(TEMP_BASE)
    print(f"Removed {TEMP_BASE}.", flush=True)


if __name__ == "__main__":
    main()
