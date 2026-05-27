"""LLM experiment track for Universalization Ablation.

Runs the simulation using LLM agents, comparing standard LLM behavior
against LLM agents using GovSim-style universalization reasoning.
"""

import os
import sys
from pathlib import Path
import pandas as pd

from src.llm_client import get_llm_model
from src.environment import LiquidityReserveEnvironment
from src.llm_agents import LLMDepartment
from src.coordination import IndependentCoordination
from src.compositions import make_compositions
from src.experiment import run_experiment_sweep

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
    base_dir = Path("results/universalization")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running LLM Universalization Sweep: model={MODEL}, max_steps={max_steps}")

    # Standard agents (Universalization OFF)
    compositions_off = make_compositions(
        LLMDepartment, model=MODEL, temperature=TEMPERATURE, universalization=False
    )
    
    # Universalization agents (Universalization ON)
    compositions_on = make_compositions(
        LLMDepartment, model=MODEL, temperature=TEMPERATURE, universalization=True
    )

    if SMOKE:
        compositions_off = {"standard": compositions_off["standard"], "free_rider": compositions_off["free_rider"]}
        compositions_on = {"standard": compositions_on["standard"], "free_rider": compositions_on["free_rider"]}

    mechanisms = [IndependentCoordination()]

    # Run without universalization
    print("\n--- Running without Universalization ---")
    agg_off = run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions_off,
        env_factory=make_env,
        n_seeds=1,
        max_steps=max_steps,
        output_dir=str(base_dir / "off"),
        scales=None,
        progress=True,
    )
    agg_off["universalization"] = False

    # Run with universalization
    print("\n--- Running WITH Universalization ---")
    agg_on = run_experiment_sweep(
        coordination_mechanisms=mechanisms,
        compositions=compositions_on,
        env_factory=make_env,
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

if __name__ == "__main__":
    main()
