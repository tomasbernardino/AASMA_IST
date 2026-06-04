# Results

Reference for everything in this directory, what each entry-point script writes and what each artifact shows.

Entry points that produce results:

| Script                              | Writes to                                       |
|-------------------------------------|-------------------------------------------------|
| `main.py`                           | `results/raw/`, `results/figures/`              |
| `sensitivity_analysis.py`           | `results/raw/sensitivity_*.csv`, `results/figures/sensitivity_heatmap.png` |
| `main_llm.py`                       | `results/llm/` (and `results/llm/<model_slug>/` when `LLM_MODEL=a,b,c`) |
| `main_llm_ablation.py memory`       | `results/llm_memory/raw/`                       |
| `main_llm_ablation.py universalization`      | `results/universalization/{off,on}/{raw,figures}/` + `universalization_ablation.csv` |
| `main_llm_ablation.py negotiation`           | `results/negotiation/{raw,figures}/`            |

Sweep shapes are encoded in the scripts; counts below are what a complete run produces.

All four compositions (`standard`, `aggressive`, `conservative`, `free_rider`) are covered by `main.py` and `main_llm.py` — `make_compositions()` returns every entry of `COMPOSITION_SPECS`. The LLM `free_rider` rows currently on disk were appended from a second OpenRouter session; with `temperature=0.3` and `n_seeds=1`, every row of the LLM CSV is already an independent draw, so the cross-session boundary doesn't introduce noise that wasn't there before. The history-based LLM figures (`reserve_confidence_bands.png`, `action_distributions.png`, `reserve_by_composition.png`) were generated from the original 3-composition session and still reflect those three compositions only — re-running `main_llm.py` end-to-end is what would refresh them.

---

## `results/raw/` — rule-based sweep

Written by `main.py`. Sweep shape: **20 seeds × 4 scales × 26 valid `(composition, mechanism)` pairs = 2080 runs**. Role-selected centralized rows are skipped when the requested leader role is absent from a composition.

### `detailed_runs.csv` (2080 rows + header)
One row per `(mechanism, composition, scale, seed)`. Canonical analysis artifact; everything else is derived from this.

Identity columns: `mechanism`, `seed`, `composition`, `scale`.

For centralized mechanisms, `leader_index`, `leader_name`, and `leader_role`
record the actual leader used in that composition.

Outcome columns (from `src/metrics.py::compute_metrics`):
- `final_reserve`, `average_reserve` — reserve at termination, and mean over the trajectory.
- `liquidity_crisis` (bool), `time_to_crisis` (step index or `NaN`), `steps_survived` — sustainability.
- `total_withdrawal` — sum of withdrawals over the run.
- `average_reward`, `social_welfare` — mean per-agent reward; sum across agents (welfare).
- `mean_absolute_reward_gap` — mean pairwise absolute gap between departments'
  total rewards. Lower means outcomes are closer together. This replaces Gini
  because total rewards can be negative.
- `reward_std`, `reward_range` — additional signed-reward dispersion metrics.
- `reward_per_department` — dict serialised as a string, agent_name → total reward.
- `reward_profit`, `reward_sustainability`, `reward_balanced`, `reward_risk_averse` — mean reward per role for this run (averaging across the 1–2 agents holding each role).
- `total_messages`, `total_rounds` — coordination cost. `messages` and `rounds` are the contract every mechanism must populate.
- `wall_time_seconds` — runtime of the simulation loop only.
- `debate_override_rate` — fraction of steps where the debate mechanism overrode a proposed action (0 for non-debate mechanisms).

### `aggregated_comparison.csv` (104 rows + header)
One row per valid `(mechanism, composition, scale)` = 26 composition/mechanism pairs × 4 scales: mean and std of every numeric metric across the 20 seeds, plus `crisis_rate` (mean of the boolean `liquidity_crisis` column).

---

## `results/figures/` — rule-based figures

All PNGs in this directory come from `main.py` (which calls `src/plotting.py`) and use `composition="standard"` unless noted. Mechanism rankings are what the figures are designed to expose; error bars are ±1 std across seeds.

- **`metrics_comparison.png`** — Four-panel bar chart on `composition="standard", scale="standard"`: average reserve, steps survived, average reward, mean absolute reward gap (one bar per mechanism, error bars across seeds). The top-level "which mechanism wins on what" view.
- **`reserve_confidence_bands.png`** — Mean reserve trajectory ± 1 std across seeds, one line per mechanism, on `composition="standard", scale="standard"`. Shows sustainability over time, not just at termination.
- **`action_distributions.png`** — Stacked bars: proportion of `L`/`M`/`H` final actions per mechanism (pooled across all steps and seeds). Shows what coordination *actually does* to agent behaviour.
- **`per_role_rewards.png`** — One subplot per role (profit / sustainability / balanced / risk-averse) showing mean reward by mechanism. Reveals whether a mechanism wins social welfare by helping everyone or by trading roles off.
- **`metrics_by_composition.png`** — Grid: rows are compositions (standard / aggressive / conservative / free_rider), columns are key metrics. Shows whether a mechanism's advantage survives a different role mix, including under a saboteur (`free_rider`).
- **`reserve_by_composition.png`** — Like `reserve_confidence_bands.png` but one panel per composition.
- **`pareto_cost_vs_welfare.png`** — Two-panel scatter on `composition="standard"`: coordination cost (x) vs social welfare (left panel) and vs crisis-avoidance rate `1 - crisis_rate` (right panel). The Pareto frontier is drawn through non-dominated points. For LLM sweeps the cost axis switches to `llm_calls_mean`; for rule-based it's `total_messages_mean`.
- **`scale_robustness.png`** — Grouped bars on `composition="standard"`: for each mechanism, one bar per L/M/H scale (`standard`, `wide`, `asymmetric`, `compressed`). Parallel bars ⇒ ranking preserved across scales; crossings ⇒ scale-dependent ranking. Three panels: crisis rate, social welfare, average reserve.
- **`sensitivity_heatmap.png`** — Written by `sensitivity_analysis.py`. Crisis-rate heatmap per mechanism over a 3×3 grid of `recovery_noise_std × shock_probability`. Each cell averages 10 seeds.

---

## `results/raw/sensitivity_*.csv` — sensitivity sweep

Written by `sensitivity_analysis.py`. Sweep shape: **7 mechanisms × 3 noise levels × 3 shock probabilities × 10 seeds = 630 runs**, standard composition only.

- **`sensitivity_detailed.csv`** (630 rows + header) — One row per `(mechanism, noise, shock, seed)`. Same columns as `detailed_runs.csv` plus `recovery_noise_std`, `shock_probability`. No `scale` column (always standard).
- **`sensitivity_aggregated.csv`** (63 rows + header) — One row per `(mechanism, noise, shock)`: `crisis_rate`, `average_reserve_mean/std`, `steps_survived_mean`, `total_withdrawal_mean`, `override_rate_mean`, `mean_absolute_reward_gap_mean`, `reward_std_mean`, `reward_range_mean`.

---

## `results/llm/` — LLM track

Written by `main_llm.py`. Sweep shape per model: **1 seed × 26 valid `(composition, mechanism)` pairs = 26 runs**. Scales sweep is intentionally not run for the LLM track.

The role-selected centralized code emits `centralized_profit`,
`centralized_sustainability`, and `centralized_risk_averse`, skipping
composition/role pairs where the leader role is absent. Voting and
AdaptiveVoting are excluded from the LLM track (no natural LLM analog).

**Single-model mode** (`LLM_MODEL` unset → script uses `LLM_MODEL`): outputs go flat into `results/llm/raw/` and `results/llm/figures/`.

**Multi-model mode** (`LLM_MODEL=a,b,c`): each model gets its own subdirectory `results/llm/<model_slug>/{raw,figures}` containing the full per-model output, plus a top-level `results/llm/raw/multi_model_aggregated.csv` and `results/llm/figures/model_comparison.png` for cross-model comparison.

Currently on disk: three model subdirs — `deepseek_deepseek-v4-flash/`, `google_gemma-4-31b-it/`, `openai_gpt-5.4-nano/`.

### Per-model `raw/`
- **`detailed_runs.csv`** (26 rows + header) — Same columns as the rule-based version, plus:
  - `model` — model identifier this run used.
  - `llm_calls` — total LLM completions invoked over the run (departments + coordinator).
  - `llm_total_latency_ms`, `llm_avg_latency_ms` — total and mean wall time waiting on LLM responses.
- **`aggregated_comparison.csv`** — One row per `(mechanism, composition, scale)` with mean/std plus the same LLM-specific columns (`llm_calls_mean`, `llm_total_latency_ms_mean`, `llm_avg_latency_ms_mean`).

### Per-model `figures/`
Same set as `results/figures/` *except* `scale_robustness.png` (no scale sweep) and `sensitivity_heatmap.png` (rule-based only). Same semantics, but the Pareto plot's x-axis is `llm_calls_mean` instead of `total_messages_mean`.

The current per-model figures were generated by a full `main_llm.py` run, so
the main figures include all four compositions, including `free_rider`. There
are no separate `_free_rider` companion figures in the current result set.

### `results/llm/raw/multi_model_aggregated.csv`
Concatenation of every per-model `aggregated_comparison.csv` with an added `model` column. Multi-model mode only. With the current three-model run this file has 78 rows.

### `results/llm/figures/model_comparison.png`
Cross-model bar chart on `composition="standard"`: each mechanism is grouped, one bar per model. Lets you read off whether a mechanism's rank is stable across LLM choice.

---

## `results/llm_memory/raw/` — memory ablation

Written by `main_llm_ablation.py memory`. Sweep shape: **2 memory modes × 3 mechanisms × 1 composition × 1 seed = 6 runs**, standard composition only. Isolates "the agents are LLMs" from "the agents have cross-step memory".

Memory modes: `previous` (window=1) vs `full_history` (window=5). Mechanisms: `independent`, `llm_centralized`, `crewai_debate`.

- **`memory_ablation.csv`** (6 rows + header) — Same columns as the LLM `detailed_runs.csv` plus `memory_mode` and `memory_window`.

No figures are written by the ablation script. (`main_llm_ablation.py memory` also writes a `memory_ablation_summary.csv` — strict column-subset of the detail CSV — but it was removed as a duplicate; it will be re-created if you re-run the script.)

---

## `results/universalization/` — universalization ablation

Written by `main_llm_ablation.py universalization`. Isolates the effect of a Kantian "universal-impact" prompt on LLM agent behaviour.

Sweep shape: **2 universalization settings × 1 mechanism (Independent) × 4 compositions × 1 seed = 8 runs**. Standard scale only. `MAX_STEPS` is controlled by `LLM_MAX_STEPS` (script default 10; the runs currently on disk were produced with `LLM_MAX_STEPS=20` from `.env`, matching `main_llm.py`).

- **`off/{raw,figures}/`** — full sweep with `universalization=False` (same code path as `main_llm.py`'s Independent row, but a fresh LLM draw — not interchangeable).
- **`on/{raw,figures}/`** — same sweep with `universalization=True`. The system prompt gains a paragraph asking the agent to reason about what would happen if every department adopted the same policy.
- **`universalization_ablation.csv`** — concatenation of both aggregated frames with a `universalization` boolean column. The paired comparison artifact.

This is *not* redundant with `main_llm.py`'s Independent row: LLMs at `temperature=0.3` are stochastic and OpenRouter does not honour `seed` for most models, so off-vs-on must be drawn under matched conditions in one script.

The runs currently on disk used `LLM_MODEL=deepseek/deepseek-v4-flash`.

---

## `results/negotiation/` — free-negotiation mechanism

Written by `main_llm_ablation.py negotiation`. Head-to-head between `IndependentCoordination` (no coordination) and `FreeNegotiationCoordination` — a GovSim-style chat-room mechanism added in the GovSim-features commit.

Sweep shape per model: **2 mechanisms × 4 compositions × 1 seed = 8 runs**. Standard scale only. `MAX_STEPS` is controlled by `LLM_MAX_STEPS` (script default 10; the runs currently on disk were produced with `LLM_MAX_STEPS=20` from `.env`).

- `raw/detailed_runs.csv` — 8 rows + header.
- `raw/aggregated_comparison.csv` — same.
- `figures/mechanism_comparison.png` — reuses the multi-model plot to compare Independent vs FreeNegotiation across the four compositions.

`main_llm_ablation.py negotiation` now writes only `aggregated_comparison.csv`; the older duplicate `negotiation_comparison.csv` was removed.

`FreeNegotiationCoordination` is *not* in `main_llm.py`'s mechanism set, so this script is the only place it runs. The Independent baseline here is a fresh LLM draw and is not interchangeable with `main_llm.py`'s Independent row.

The runs currently on disk used `LLM_MODEL=deepseek/deepseek-v4-flash`.
