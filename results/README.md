# Results

Reference for everything in this directory — what each entry-point script writes and what each artifact shows.

Four entry points produce results:

| Script                          | Writes to                                       |
|---------------------------------|-------------------------------------------------|
| `main.py`                       | `results/raw/`, `results/figures/`              |
| `sensitivity_analysis.py`       | `results/raw/sensitivity_*.csv`, `results/figures/sensitivity_heatmap.png` |
| `main_llm.py`                   | `results/llm/` (and `results/llm/<model_slug>/` when `LLM_MODELS=a,b,c`) |
| `main_llm_memory_ablation.py`   | `results/llm_memory/raw/`                       |

Sweep shapes are encoded in the scripts; counts below are what a complete run produces.

---

## `results/raw/` — rule-based sweep

Written by `main.py`. Sweep shape: **20 seeds × 7 mechanisms × 3 compositions × 4 scales = 1680 runs**.

### `detailed_runs.csv` (1680 rows + header)
One row per `(mechanism, composition, scale, seed)`. Canonical analysis artifact; everything else is derived from this.

Identity columns: `mechanism`, `seed`, `composition`, `scale`.

Outcome columns (from `src/metrics.py::compute_metrics`):
- `final_reserve`, `average_reserve` — reserve at termination, and mean over the trajectory.
- `liquidity_crisis` (bool), `time_to_crisis` (step index or `NaN`), `steps_survived` — sustainability.
- `total_withdrawal` — sum of withdrawals over the run.
- `average_reward`, `social_welfare` — mean per-agent reward; sum across agents (welfare).
- `reward_inequality_gini` — Gini across the 5 agents' total rewards. Fairness.
- `reward_per_department` — dict serialised as a string, agent_name → total reward.
- `reward_profit`, `reward_sustainability`, `reward_balanced`, `reward_risk_averse` — mean reward per role for this run (averaging across the 1–2 agents holding each role).
- `total_messages`, `total_rounds` — coordination cost. `messages` and `rounds` are the contract every mechanism must populate.
- `wall_time_seconds` — runtime of the simulation loop only.
- `debate_override_rate` — fraction of steps where the debate mechanism overrode a proposed action (0 for non-debate mechanisms).

### `aggregated_comparison.csv` (252 rows + header)
One row per `(mechanism, composition, scale)`: mean and std of every numeric metric across the 20 seeds, plus `crisis_rate` (mean of the boolean `liquidity_crisis` column).

---

## `results/figures/` — rule-based figures

All PNGs in this directory come from `main.py` (which calls `src/plotting.py`) and use `composition="standard"` unless noted. Mechanism rankings are what the figures are designed to expose; error bars are ±1 std across seeds.

- **`metrics_comparison.png`** — Four-panel bar chart on `composition="standard", scale="standard"`: average reserve, steps survived, average reward, Gini coefficient (one bar per mechanism, error bars across seeds). The top-level "which mechanism wins on what" view.
- **`reserve_confidence_bands.png`** — Mean reserve trajectory ± 1 std across seeds, one line per mechanism, on `composition="standard", scale="standard"`. Shows sustainability over time, not just at termination.
- **`action_distributions.png`** — Stacked bars: proportion of `L`/`M`/`H` final actions per mechanism (pooled across all steps and seeds). Shows what coordination *actually does* to agent behaviour.
- **`per_role_rewards.png`** — One subplot per role (profit / sustainability / balanced / risk-averse) showing mean reward by mechanism. Reveals whether a mechanism wins social welfare by helping everyone or by trading roles off.
- **`metrics_by_composition.png`** — Grid: rows are compositions (standard / aggressive / conservative), columns are key metrics. Shows whether a mechanism's advantage survives a different role mix.
- **`reserve_by_composition.png`** — Like `reserve_confidence_bands.png` but one panel per composition.
- **`pareto_cost_vs_welfare.png`** — Two-panel scatter on `composition="standard"`: coordination cost (x) vs social welfare (left panel) and vs crisis-avoidance rate `1 - crisis_rate` (right panel). The Pareto frontier is drawn through non-dominated points. For LLM sweeps the cost axis switches to `llm_calls_mean`; for rule-based it's `total_messages_mean`.
- **`scale_robustness.png`** — Grouped bars on `composition="standard"`: for each mechanism, one bar per L/M/H scale (`standard`, `wide`, `asymmetric`, `compressed`). Parallel bars ⇒ ranking preserved across scales; crossings ⇒ scale-dependent ranking. Three panels: crisis rate, social welfare, average reserve.
- **`sensitivity_heatmap.png`** — Written by `sensitivity_analysis.py`. Crisis-rate heatmap per mechanism over a 3×3 grid of `recovery_noise_std × shock_probability`. Each cell averages 10 seeds.

---

## `results/raw/sensitivity_*.csv` — sensitivity sweep

Written by `sensitivity_analysis.py`. Sweep shape: **7 mechanisms × 3 noise levels × 3 shock probabilities × 10 seeds = 630 runs**, standard composition only.

- **`sensitivity_detailed.csv`** (630 rows + header) — One row per `(mechanism, noise, shock, seed)`. Same columns as `detailed_runs.csv` plus `recovery_noise_std`, `shock_probability`. No `scale` column (always standard).
- **`sensitivity_aggregated.csv`** (63 rows + header) — One row per `(mechanism, noise, shock)`: `crisis_rate`, `average_reserve_mean/std`, `steps_survived_mean`, `total_withdrawal_mean`, `override_rate_mean`, `gini_mean`.

---

## `results/llm/` — LLM track

Written by `main_llm.py`. Sweep shape per model: **1 seed × 7 mechanisms × 3 compositions = 21 runs**. Scales sweep is intentionally not run for the LLM track.

The 7 mechanisms are: `independent`, `centralized_profit`, `centralized_sustainability`, `centralized_risk_averse`, `structured_debate`, `llm_centralized`, `crewai_debate`. Voting and AdaptiveVoting are excluded (no natural LLM analog).

**Single-model mode** (`LLM_MODELS` unset → script uses `LLM_MODEL`): outputs go flat into `results/llm/raw/` and `results/llm/figures/`.

**Multi-model mode** (`LLM_MODELS=a,b,c`): each model gets its own subdirectory `results/llm/<model_slug>/{raw,figures}` containing the full per-model output, plus a top-level `results/llm/raw/multi_model_aggregated.csv` and `results/llm/figures/model_comparison.png` for cross-model comparison.

Currently on disk: three model subdirs — `deepseek_deepseek-v4-flash/`, `google_gemma-4-31b-it/`, `openai_gpt-5.4-nano/`.

### Per-model `raw/`
- **`detailed_runs.csv`** (21 rows + header) — Same columns as the rule-based version, plus:
  - `model` — model identifier this run used.
  - `llm_calls` — total LLM completions invoked over the run (departments + coordinator).
  - `llm_total_latency_ms`, `llm_avg_latency_ms` — total and mean wall time waiting on LLM responses.
- **`aggregated_comparison.csv`** — One row per `(mechanism, composition, scale)` with mean/std plus the same LLM-specific columns (`llm_calls_mean`, `llm_total_latency_ms_mean`, `llm_avg_latency_ms_mean`).

### Per-model `figures/`
Same set as `results/figures/` *except* `scale_robustness.png` (no scale sweep) and `sensitivity_heatmap.png` (rule-based only). Same semantics, but the Pareto plot's x-axis is `llm_calls_mean` instead of `total_messages_mean`.

### `results/llm/raw/multi_model_aggregated.csv`
Concatenation of every per-model `aggregated_comparison.csv` with an added `model` column. Multi-model mode only.

### `results/llm/figures/model_comparison.png`
Cross-model bar chart on `composition="standard"`: each mechanism is grouped, one bar per model. Lets you read off whether a mechanism's rank is stable across LLM choice.

---

## `results/llm_memory/raw/` — memory ablation

Written by `main_llm_memory_ablation.py`. Sweep shape: **2 memory modes × 3 mechanisms × 1 composition × 1 seed = 6 runs**, standard composition only. Isolates "the agents are LLMs" from "the agents have cross-step memory".

Memory modes: `previous` (window=1) vs `full_history` (window=5). Mechanisms: `independent`, `llm_centralized`, `crewai_debate`.

- **`memory_ablation.csv`** (6 rows + header) — Same columns as the LLM `detailed_runs.csv` plus `memory_mode` and `memory_window`.
- **`memory_ablation_summary.csv`** (6 rows + header) — Compact view: `mechanism, memory_mode, final_reserve, average_reserve, steps_survived, social_welfare, liquidity_crisis`.

No figures are written by the ablation script.

