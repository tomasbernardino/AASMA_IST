"""LLM experiment track for Free Negotiation.

Runs the simulation using LLM agents, comparing standard Independent 
action against the GovSim-style Free Negotiation mechanism where agents
chat before deciding.
"""

import os
import sys
from pathlib import Path
import pandas as pd

from src.llm_client import get_llm_model
from src.environment import LiquidityReserveEnvironment
from src.llm_agents import LLMDepartment
from src.coordination import IndependentCoordination, FreeNegotiationCoordination
from src.compositions import make_compositions
from src.experiment import run_experiment_sweep
from src.plotting import plot_model_comparison

MODEL = os.environ.get("LLM_MODEL", get_llm_model())
TEMPERATURE = 0.3
MAX_STEPS = int(os.environ.get("LLM_MAX_STEPS", "10"))
SMOKE = bool(os.environ.get("SMOKE"))

def make_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )

def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY before running.", file=sys.stderr)
        sys.exit(1)

    max_steps = min(MAX_STEPS, 2) if SMOKE else MAX_STEPS
    base_dir = Path("results/negotiation")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running LLM Free Negotiation Sweep: model={MODEL}, max_steps={max_steps}")

    compositions = make_compositions(
        LLMDepartment, model=MODEL, temperature=TEMPERATURE
    )

    if SMOKE:
        compositions = {"standard": compositions["standard"]}

    mechanisms = [
        IndependentCoordination(),
        FreeNegotiationCoordination(chat_rounds=1),
    ]

    print("\n--- Running mechanisms ---")
    agg_results = run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions,
        env_factory=make_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(base_dir),
        scales=None,
        progress=True,
    )
    agg_results["model"] = MODEL

    combined_path = base_dir / "raw" / "negotiation_comparison.csv"
    agg_results.to_csv(combined_path, index=False)
    print(f"\nWrote combined results to {combined_path} ({len(agg_results)} rows)")

    # Reuse the multi-model plot function since it works for mechanisms too
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

if __name__ == "__main__":
    main()
