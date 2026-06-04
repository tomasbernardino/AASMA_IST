# Results

This directory contains generated CSV summaries and figures for the study. Every artifact here is reproducible from the current entry-point scripts.

## Entry Points

| Command | Main outputs |
|---|---|
| `python main.py` | `results/raw/`, `results/figures/` |
| `python sensitivity_analysis.py` | `results/raw/sensitivity_*.csv`, `results/figures/sensitivity_heatmap.png` |
| `python main_llm.py` | `results/llm/` |
| `python main_llm_ablation.py memory` | `results/llm_memory/raw/memory_ablation.csv` |
| `python main_llm_ablation.py universalization` | `results/universalization/` |
| `python main_llm_ablation.py negotiation` | `results/negotiation/` |

`main_llm.py` treats a comma-separated `LLM_MODEL` as a multi-model sweep. In that case each model writes to `results/llm/<model>/`, and the combined comparison writes to `results/llm/raw/` and `results/llm/figures/`.

## Common CSVs

Most sweep outputs use the same two raw files:

- `detailed_runs.csv`: one row per individual run.
- `aggregated_comparison.csv`: mean/std aggregation over runs for each mechanism, composition, and scale where applicable.

Important metric columns:

- `final_reserve`, `average_reserve`, `liquidity_crisis`, `time_to_crisis`, `steps_survived`: sustainability outcomes.
- `total_withdrawal`, `average_reward`, `social_welfare`: efficiency and reward outcomes.
- `mean_absolute_reward_gap`, `reward_std`, `reward_range`: fairness/dispersion over signed rewards.
- `reward_<role>`: mean reward for a role within that run.
- `total_messages`, `total_rounds`: coordination cost.
- `llm_calls`, `llm_total_latency_ms`, `llm_avg_latency_ms`: LLM cost columns, present only for LLM-backed runs.

## Rule-Based Results

Written by `python main.py`.

- `results/raw/detailed_runs.csv`: full rule-based sweep over mechanisms, compositions, withdrawal scales, and seeds.
- `results/raw/aggregated_comparison.csv`: aggregated rule-based comparison.
- `results/figures/action_distributions.png`: final action proportions by mechanism.
- `results/figures/metrics_comparison.png`: key metric bars for the standard composition and standard scale.
- `results/figures/metrics_by_composition.png`: key metrics across all compositions.
- `results/figures/pareto_cost_vs_welfare.png`: coordination cost vs social welfare and crisis avoidance.
- `results/figures/per_role_rewards.png`: reward by role and mechanism.
- `results/figures/reserve_by_composition.png`: reserve trajectories by composition.
- `results/figures/reserve_confidence_bands.png`: reserve trajectory confidence bands for the standard composition.
- `results/figures/scale_robustness.png`: mechanism robustness across withdrawal scales.

## Sensitivity Results

Written by `python sensitivity_analysis.py`.

- `results/raw/sensitivity_detailed.csv`: one row per mechanism, noise level, shock probability, and seed.
- `results/raw/sensitivity_aggregated.csv`: aggregated sensitivity grid.
- `results/figures/sensitivity_heatmap.png`: crisis-rate heatmap over recovery noise and shock probability.

## LLM Results

Written by `python main_llm.py`.

Per-model outputs:

- `results/llm/<model_slug>/raw/detailed_runs.csv`
- `results/llm/<model_slug>/raw/aggregated_comparison.csv`
- `results/llm/<model_slug>/figures/*.png`

Multi-model outputs:

- `results/llm/raw/multi_model_aggregated.csv`: concatenated per-model aggregate table.
- `results/llm/figures/model_comparison.png`: cross-model comparison for the standard composition.

The LLM track does not run the withdrawal-scale sweep, so it does not create `scale_robustness.png`.

## Memory Ablation

Written by `python main_llm_ablation.py memory`.

- `results/llm_memory/raw/memory_ablation.csv`: compares `previous` memory (`memory_window=1`) with `full_history` memory (`memory_window=5`) for `independent`, `llm_centralized`, and `crewai_debate` on the standard composition.

## Universalization Ablation

Written by `python main_llm_ablation.py universalization`.

- `results/universalization/off/raw/detailed_runs.csv`
- `results/universalization/off/raw/aggregated_comparison.csv`
- `results/universalization/off/figures/*.png`
- `results/universalization/on/raw/detailed_runs.csv`
- `results/universalization/on/raw/aggregated_comparison.csv`
- `results/universalization/on/figures/*.png`
- `results/universalization/universalization_ablation.csv`: combined on/off aggregate table with a `universalization` column.

This experiment isolates the effect of adding the universalization prompt to LLM departments.

## Negotiation Ablation

Written by `python main_llm_ablation.py negotiation`.

- `results/negotiation/raw/detailed_runs.csv`
- `results/negotiation/raw/aggregated_comparison.csv`
- `results/negotiation/figures/*.png`

This experiment compares `IndependentCoordination` against `FreeNegotiationCoordination`. The negotiation run uses the same standard `aggregated_comparison.csv` name as the other sweeps; there is no separate duplicate comparison CSV.
