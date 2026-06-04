"""LLM experiment track.

Each LLM mechanism is paired with its closest rule-based analog so we can
claim "the LLM coordinator beats/ties/loses to the rule-based one":
    CentralizedRoleCoordination(profit|sustainability|risk_averse)
                                 <-> LLMCentralizedCoordination
    StructuredDebateCoordination <-> CrewAIDebateCoordination
"""

import os
from pathlib import Path

import pandas as pd

from src.llm_client import get_llm_models
from src.llm_agents import LLMDepartment
from src.compositions import make_compositions
from src.experiment import run_experiment_sweep
from src.plotting import plot_model_comparison
from src.study_config import (
    DEFAULT_TEMPERATURE,
    build_llm_mechanisms,
    make_default_env,
    model_slug,
    require_openrouter_key,
)


MODELS = get_llm_models()
MAX_STEPS = int(os.environ.get("LLM_MAX_STEPS", "20"))


def main():
    require_openrouter_key()

    multi_model = len(MODELS) > 1
    base_dir = Path("results/llm")
    base_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Running LLM sweep: {len(MODELS)} model{'s' if multi_model else ''}, "
        f"max_steps={MAX_STEPS}"
    )

    per_model_dfs = []
    for model in MODELS:
        if multi_model:
            print(f"\n{'=' * 78}")
            print(f"  Model: {model}")
            print('=' * 78)

        compositions = make_compositions(
            LLMDepartment, model=model, temperature=DEFAULT_TEMPERATURE,
        )
        run_dir = base_dir / model_slug(model) if multi_model else base_dir
        agg = run_experiment_sweep(
            coordination_mechanisms=build_llm_mechanisms(
                model, temperature=DEFAULT_TEMPERATURE,
            ),
            compositions=compositions,
            env_factory=make_default_env,
            n_seeds=1,
            max_steps=MAX_STEPS,
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
