"""LLM experiment track.

Each LLM mechanism is paired with its closest rule-based analog so we can
claim "the LLM coordinator beats/ties/loses to the rule-based one":
    CentralizedRoleCoordination(profit|sustainability|risk_averse)
                                 <-> LLMCentralizedCoordination
    StructuredDebateCoordination <-> CrewAIDebateCoordination
The three Centralized variants mirror main.py as role-selected leaders. If a
composition lacks the requested leader role, that row is skipped rather than
silently substituting a different role. Independent is the no-coordination
baseline. Voting/AdaptiveVoting are excluded: no natural LLM analog and they'd
pay LLM-department cost for no new insight.

Multi-model: set LLM_MODELS=a,b,c to sweep models; each gets its own subdir
under results/llm/ plus a combined comparison CSV + figure. Single-model
mode (LLM_MODELS unset) writes flat to results/llm/.
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
    CentralizedRoleCoordination,
    StructuredDebateCoordination,
    LLMCentralizedCoordination,
)
from src.crewai_coordination import CrewAIDebateCoordination
from src.compositions import make_compositions
from src.experiment import run_experiment_sweep
from src.plotting import plot_model_comparison


MODELS_ENV = os.environ.get("LLM_MODELS")
MODELS = [
    model.strip()
    for model in (MODELS_ENV or get_llm_model()).split(",")
    if model.strip()
]

TEMPERATURE = 0.3
MAX_STEPS = int(os.environ.get("LLM_MAX_STEPS", "20"))
SMOKE = bool(os.environ.get("SMOKE"))


def slug(model_name):
    return model_name.replace("/", "_").replace(":", "-")


def make_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )


def build_mechanisms_for_model(model):
    # Three role-selected Centralized variants (matching main.py). Unsupported
    # role/composition pairs are skipped by the sweep runner.
    return [
        IndependentCoordination(),
        CentralizedRoleCoordination("profit"),
        CentralizedRoleCoordination("sustainability"),
        CentralizedRoleCoordination("risk_averse"),
        StructuredDebateCoordination(),
        LLMCentralizedCoordination(model=model, temperature=TEMPERATURE),
        CrewAIDebateCoordination(
            model=model,
            temperature=TEMPERATURE,
            allow_delegation=False,
        ),
    ]


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY before running.", file=sys.stderr)
        sys.exit(1)

    multi_model = len(MODELS) > 1
    max_steps = min(MAX_STEPS, 2) if SMOKE else MAX_STEPS
    base_dir = Path("results/llm")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Running LLM sweep: {len(MODELS)} model{'s' if multi_model else ''}, "
        f"max_steps={max_steps}"
        + ("  (SMOKE mode)" if SMOKE else "")
    )

    per_model_dfs = []
    for model in MODELS:
        if multi_model:
            print(f"\n{'=' * 78}")
            print(f"  Model: {model}")
            print('=' * 78)

        compositions = make_compositions(
            LLMDepartment, model=model, temperature=TEMPERATURE,
        )
        if SMOKE:
            compositions = {"standard": compositions["standard"]}

        mechanisms = build_mechanisms_for_model(model)

        run_dir = base_dir / slug(model) if multi_model else base_dir
        agg = run_experiment_sweep(
            coordination_mechanisms=mechanisms,
            compositions=compositions,
            env_factory=make_env,
            n_seeds=1,
            max_steps=max_steps,
            output_dir=str(run_dir),
            scales=None,
            progress=True,
        )
        agg["model"] = model
        per_model_dfs.append(agg)

    if multi_model:
        combined = pd.concat(per_model_dfs, ignore_index=True)
        raw_dir = base_dir / "raw"
        fig_dir = base_dir / "figures"
        raw_dir.mkdir(exist_ok=True)
        fig_dir.mkdir(exist_ok=True)

        combined_path = raw_dir / "multi_model_aggregated.csv"
        combined.to_csv(combined_path, index=False)
        print(f"\nWrote {combined_path} ({len(combined)} rows)")

        plot_path = fig_dir / "model_comparison.png"
        plot_model_comparison(
            aggregated_df=combined,
            composition="standard",
            output_path=str(plot_path),
        )
        print(f"Wrote {plot_path}")


if __name__ == "__main__":
    main()
