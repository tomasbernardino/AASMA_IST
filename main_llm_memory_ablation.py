"""Memory-ablation sweep for the LLM track.

Isolates the contribution of cross-step memory from "the agents are LLMs"
by running the LLM mechanisms under two memory regimes (window=1 vs
window=5). Without this ablation the two effects are confounded.
"""

import os
import sys
from pathlib import Path

import pandas as pd

from src.llm_client import get_llm_model
from src.environment import LiquidityReserveEnvironment
from src.llm_agents import LLMDepartment
from src.coordination import (
    IndependentCoordination,
    LLMCentralizedCoordination,
)
from src.crewai_coordination import CrewAIDebateCoordination
from src.compositions import make_compositions
from src.simulation import run_simulation
from src.metrics import compute_metrics


MODEL = get_llm_model("ABLATION_MODEL")
TEMPERATURE = 0.3
MAX_STEPS = int(os.environ.get("LLM_MAX_STEPS", "20"))

MEMORY_MODES = {
    "previous": 1,
    "full_history": 5,
}


def make_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )


def build_mechanisms_for_window(memory_window):
    """Ablate the coord mechanisms' memory in lock-step with the departments
    so 'no history anywhere' really means no history."""
    return [
        IndependentCoordination(),
        LLMCentralizedCoordination(
            model=MODEL, temperature=TEMPERATURE, memory_window=memory_window,
        ),
        CrewAIDebateCoordination(
            model=MODEL,
            temperature=TEMPERATURE,
            memory_window=memory_window,
            allow_delegation=False,
        ),
    ]


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY before running.", file=sys.stderr)
        sys.exit(1)

    output_dir = Path("results/llm_memory")
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_metrics = []

    for mode_name, memory_window in MEMORY_MODES.items():
        print(f"\n=== memory_mode={mode_name} (window={memory_window}) ===")

        compositions = make_compositions(
            LLMDepartment,
            model=MODEL,
            temperature=TEMPERATURE,
            memory_window=memory_window,
        )
        dept_factory = compositions["standard"]
        mechanisms = build_mechanisms_for_window(memory_window)

        for mechanism in mechanisms:
            print(f"  [{mode_name}/{mechanism.name}]", flush=True)
            departments = dept_factory()
            history, elapsed = run_simulation(
                environment=make_env(),
                departments=departments,
                coordination=mechanism,
                max_steps=MAX_STEPS,
            )
            run_metrics = compute_metrics(
                history=history,
                departments=departments,
                max_steps=MAX_STEPS,
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


if __name__ == "__main__":
    main()
