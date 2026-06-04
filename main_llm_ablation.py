"""Controlled LLM side experiments.

Modes:
    memory            Compare short vs fuller cross-step memory.
    universalization  Compare normal prompts vs universalization prompts.
    negotiation       Compare independent action vs free negotiation.
"""

import argparse
import os
from pathlib import Path

import pandas as pd

from src.compositions import make_compositions
from src.coordination import FreeNegotiationCoordination, IndependentCoordination
from src.experiment import run_experiment_sweep
from src.llm_agents import LLMDepartment
from src.llm_client import get_llm_model
from src.metrics import compute_metrics
from src.plotting import plot_model_comparison
from src.simulation import run_simulation
from src.study_config import (
    DEFAULT_TEMPERATURE,
    make_default_env,
    require_openrouter_key,
)
from src.coordination import LLMCentralizedCoordination
from src.crewai_coordination import CrewAIDebateCoordination

MEMORY_MODES = {
    "previous": 1,
    "full_history": 5,
}


def build_memory_mechanisms(model, memory_window):


    return [
        IndependentCoordination(),
        LLMCentralizedCoordination(
            model=model,
            temperature=DEFAULT_TEMPERATURE,
            memory_window=memory_window,
        ),
        CrewAIDebateCoordination(
            model=model,
            temperature=DEFAULT_TEMPERATURE,
            memory_window=memory_window,
            allow_delegation=False,
        ),
    ]


def run_memory(model, max_steps):
    output_dir = Path("results/llm_memory")
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_metrics = []
    for mode_name, memory_window in MEMORY_MODES.items():
        print(f"\n=== memory_mode={mode_name} (window={memory_window}) ===")

        compositions = make_compositions(
            LLMDepartment,
            model=model,
            temperature=DEFAULT_TEMPERATURE,
            memory_window=memory_window,
        )
        dept_factory = compositions["standard"]

        for mechanism in build_memory_mechanisms(model, memory_window):
            print(f"  [{mode_name}/{mechanism.name}]", flush=True)
            departments = dept_factory()
            history, elapsed = run_simulation(
                environment=make_default_env(),
                departments=departments,
                coordination=mechanism,
                max_steps=max_steps,
            )
            run_metrics = compute_metrics(
                history=history,
                departments=departments,
                max_steps=max_steps,
                wall_time_seconds=elapsed,
            )
            run_metrics["memory_mode"] = mode_name
            run_metrics["memory_window"] = memory_window
            all_metrics.append(run_metrics)

    df = pd.DataFrame(all_metrics)
    df.to_csv(raw_dir / "memory_ablation.csv", index=False)

    summary_cols = [
        "final_reserve", "average_reserve", "steps_survived",
        "social_welfare", "liquidity_crisis",
    ]
    summary = (
        df.groupby(["mechanism", "memory_mode"])[summary_cols]
        .mean()
        .round(3)
    )
    print("\n=== Memory ablation summary ===")
    print(summary.to_string())
    summary.to_csv(raw_dir / "memory_ablation_summary.csv")


def run_universalization(model, max_steps):
    base_dir = Path("results/universalization")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running LLM Universalization Sweep: model={model}, max_steps={max_steps}")

    compositions_off = make_compositions(
        LLMDepartment,
        model=model,
        temperature=DEFAULT_TEMPERATURE,
        universalization=False,
    )
    compositions_on = make_compositions(
        LLMDepartment,
        model=model,
        temperature=DEFAULT_TEMPERATURE,
        universalization=True,
    )

    mechanisms = [IndependentCoordination()]

    print("\n--- Running without Universalization ---")
    agg_off = run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions_off,
        env_factory=make_default_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(base_dir / "off"),
        scales=None,
        progress=True,
    )
    agg_off["universalization"] = False

    print("\n--- Running WITH Universalization ---")
    agg_on = run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions_on,
        env_factory=make_default_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(base_dir / "on"),
        scales=None,
        progress=True,
    )
    agg_on["universalization"] = True

    combined = pd.concat([agg_off, agg_on], ignore_index=True)
    combined_path = base_dir / "universalization_ablation.csv"
    combined.to_csv(combined_path, index=False)
    print(f"\nWrote combined results to {combined_path} ({len(combined)} rows)")


def run_negotiation(model, max_steps):
    base_dir = Path("results/negotiation")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running LLM Free Negotiation Sweep: model={model}, max_steps={max_steps}")

    compositions = make_compositions(
        LLMDepartment,
        model=model,
        temperature=DEFAULT_TEMPERATURE,
    )
    agg_results = run_experiment_sweep(
        coordination_mechanisms=[
            IndependentCoordination(),
            FreeNegotiationCoordination(chat_rounds=1),
        ],
        compositions=compositions,
        env_factory=make_default_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(base_dir),
        scales=None,
        progress=True,
    )
    agg_results["model"] = model


    plot_path = base_dir / "figures" / "mechanism_comparison.png"
    try:
        plot_model_comparison(
            aggregated_df=agg_results,
            composition="standard",
            output_path=str(plot_path),
        )
        print(f"Wrote {plot_path}")
    except Exception as e:
        print(f"Could not generate plot: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=["memory", "universalization", "negotiation"],
        help="Side experiment to run.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    require_openrouter_key()
    model = get_llm_model()

    if args.mode == "memory":
        max_steps = int(os.environ.get("LLM_MAX_STEPS", "20"))
        run_memory(model, max_steps)
    elif args.mode == "universalization":
        max_steps = int(os.environ.get("LLM_MAX_STEPS", "10"))
        run_universalization(model, max_steps)
    elif args.mode == "negotiation":
        max_steps = int(os.environ.get("LLM_MAX_STEPS", "10"))
        run_negotiation(model, max_steps)


if __name__ == "__main__":
    main()
