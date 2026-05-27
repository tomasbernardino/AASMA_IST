# Fifth Commit — Sweep Refactor, Coordinator Memory, LLM Experiments, and Cleanup

This commit closes the gap between the rule-based and LLM tracks, adds the experimental dimensions the report needs (L/M/H scale robustness, per-role fairness, multi-model comparison, memory ablation), and performs a sweeping cleanup pass on the LLM stack: consolidating the role prompts, deleting dead files, merging the single- and multi-model entry points, and centralising the dotenv usage on `python-dotenv`.

---

## Status Summary

| Component | Status |
|---|---|
| Shared experiment runner (`src/experiment.py`) | ✅ Complete |
| Shared composition factory (`src/compositions.py`) | ✅ Complete |
| L/M/H withdrawal scale sweep (rule-based) | ✅ Complete |
| Per-role reward metric | ✅ Complete |
| Cross-step memory in `LLMCentralized` and `CrewAIDebate` | ✅ Complete |
| Two-round CrewAI debate (opening + rebuttal) | ✅ Complete |
| Single + multi-model in one entry point (`main_llm.py`) | ✅ Complete, requires API key + budget |
| Memory ablation (`main_llm_memory_ablation.py`) | ✅ Complete, requires API key |
| LLM smoke test (`smoke_test_llm.py`) | ✅ Complete |
| Environmental sensitivity sweep | ✅ Complete, plotted as heatmaps |
| `python-dotenv` for env loading; consolidated `get_llm_model` in `src/llm_client.py` | ✅ Complete |
| `ROLE_PROMPTS` consolidated in `src/prompts.py` (shared with CrewAI's `ROLE_METADATA`) | ✅ Complete |

---

## 1. Sweep Refactor: `src/experiment.py` and `src/compositions.py`

Before this commit, `main.py` and `main_llm.py` each carried their own copy of the same nested loop (mechanisms × compositions × seeds), the same CSV aggregation, and the same plotting calls. The two files had drifted: the LLM entry point was missing crisis-rate aggregation, the new compositions, `debate_override_rate`, and three of the figures.

### `src/compositions.py`
Owns the three role mixes (`standard`, `aggressive`, `conservative`) as data, and exposes one factory function:

```python
make_compositions(dept_class, **kwargs)
```

Both `Department` (rule-based) and `LLMDepartment` (LLM-based) share the same composition specs. Only the constructor changes — kwargs like `exploration_rate=0.1` or `model="..."` are forwarded through. This means "aggressive composition" is the *same* role mix in both tracks, which is the precondition for any rule-vs-LLM comparison.

### `src/experiment.py`
Owns the sweep, the scale registries (`DEFAULT_SCALES`, `SCALES`), and the aggregation/plot dispatch:

```python
run_experiment_sweep(
    coordination_mechanisms,
    compositions,
    env_factory,
    n_seeds,
    max_steps,
    output_dir,
    scales=None,       # defaults to DEFAULT_SCALES; main.py passes the 4-scale SCALES
    progress=False,    # opt-in per-run prints for slow LLM sweeps
)
```

The function iterates `scale × composition × mechanism × seed`, writes `detailed_runs.csv`, computes `aggregated_comparison.csv`, and emits every figure. Both entry points are now thin: `main.py` is ~55 lines, `main_llm.py` is ~145 lines (covering both single- and multi-model modes), and any new metric or plot is added in *one* place.

### Impact
- One source of truth for the experiment pipeline.
- The LLM track automatically gets crisis_rate, per-role reward, per-composition plots, the Pareto plot, and the role-fairness plot — features that previously existed only on the baseline.
- New entry points (memory ablation, sensitivity) layer on top of `run_simulation` directly when they need a dimension `run_experiment_sweep` doesn't model (e.g. `memory_window` or an env grid).

---

## 2. L/M/H Scale Robustness Sweep (rule-based)

`main.py` sweeps four withdrawal scales:

| Scale | L | M | H | Why |
|---|---|---|---|---|
| `standard` | 1.0 | 2.0 | 3.0 | The canonical `ACTION_TO_WITHDRAWAL` mapping |
| `wide` | 1.0 | 3.0 | 5.0 | Spreads M and H further apart — penalises aggressive depts harder |
| `asymmetric` | 0.5 | 2.0 | 4.0 | Cheap L, expensive H — makes conservative strategies attractive |
| `compressed` | 1.0 | 1.5 | 2.0 | L/M/H barely differ — mechanism choice matters less |

`run_simulation` (`src/simulation.py`) accepts an optional `action_to_withdrawal` dict so callers can override the canonical mapping without monkey-patching. The canonical mapping `ACTION_TO_WITHDRAWAL = {"L": 1.0, "M": 2.0, "H": 3.0}` is defined at the top of `src/simulation.py` and referenced by `SCALES["standard"]` and `DEFAULT_SCALES["standard"]` via `is`-identity — one dict object, three names. A new `plot_scale_robustness` (`src/plotting.py`) draws grouped bars per scale so the reader can see whether mechanism rankings flip when the withdrawal numbers change.

The LLM track does **not** sweep scales — scale robustness is a rule-based research question, and paying LLM costs to verify it would burn the budget on the wrong dimension.

---

## 3. Per-Role Reward Metric

`compute_metrics` (`src/metrics.py`) emits one extra field per role present in the composition:

```
reward_profit, reward_sustainability, reward_balanced, reward_risk_averse
```

Each is the mean of `total_reward` across departments with that role (a composition may have 0, 1, or 2 members of a given role — missing roles produce NaN downstream).

### Motivation
`social_welfare` (the sum of rewards across departments) is misleading: the four utility functions are on different scales, so a "high welfare" mechanism might just be one that helps the role with the largest-magnitude utility. Per-role rewards let the report make claims like *"AdaptiveVoting raises sustainability reward by 30% with only an 8% hit to profit"*, which `social_welfare` would hide.

`plot_per_role_rewards` (`src/plotting.py`) draws one bar chart per role across mechanisms.

---

## 4. Cross-Step Memory in LLM Coordinators

Until this commit, `LLMDepartment` quietly had per-agent memory (its prompt included the last 5 of its own steps), but `LLMCentralizedCoordination` and `CrewAIDebateCoordination` treated each step as an isolated decision. That was unfair: the CFO and the debate moderator had less context than the line agents proposing to them.

### What changed
Both LLM coordinators now keep a `_memory_log` (default window: 5 steps) and prepend a textual summary to their prompt. Each log entry stores `reserve_before`, `reserve_after` (back-filled on the next call), and the chosen actions.

### `reset()` hook
- `CoordinationMechanism` defines a default no-op `reset()`.
- `LLMCentralizedCoordination` and `CrewAIDebateCoordination` override it to clear `_memory_log` and the step counter.
- `src/simulation.py::run_simulation` calls `coordination.reset()` per episode.

Stateless mechanisms (`Independent`, `Voting`, `AdaptiveVoting`, `Centralized`, `StructuredDebate`) inherit the no-op.

### Confound closed
Without this, "CrewAIDebate beats the rule-based debate" could mean "CrewAIDebate has memory and the rule-based one doesn't", not "CrewAIDebate reasons better". The memory-ablation experiment (section 7) isolates *memory* from *reasoning* by toggling `memory_window`.

---

## 5. CrewAIDebate: Two Rounds

| Round | What happens | LLM calls |
|---|---|---|
| 1 — Opening | Each dept agent argues 2-3 sentences for its proposal, in isolation. | N |
| 2 — Rebuttal | Each dept agent sees all opening arguments, may defend or revise, ends with `FINAL=L|M|H`. | N |
| Moderator | Synthesises both rounds, allocates per-dept actions as JSON. | 1 |

Cost dict reports `rounds: 3`, `llm_calls: 2N+1`, `model`.

### `allow_delegation`
The constructor takes `allow_delegation: bool = True`, but all three production callers (`main_llm.py`, `main_llm_memory_ablation.py`, `smoke_test_llm.py`) pass `allow_delegation=False` so the per-step LLM-call count stays predictable. The constructor default is preserved so an ad-hoc run can enable it for diagnostic purposes; if it's enabled, the `llm_calls` count becomes a lower bound (delegated sub-calls aren't tracked individually).

### Persona alignment
Each CrewAI agent's `backstory` field is taken directly from `src/prompts.py::ROLE_PROMPTS` by reference (`ROLE_METADATA["...."]["backstory"]`), so the persona text stays in sync with `LLMDepartment`'s system prompt. CrewAI's `role` and `goal` fields remain local to `crewai_coordination.py` because the CrewAI framework consumes them as separate fields.

---

## 6. `LLMDepartment.memory_window` Parameter

```python
LLMDepartment(name, role, model=..., temperature=0.3, memory_window=5)
```

`memory_window=0` disables history entirely — the agent sees only the current reserve. This is the lever the memory-ablation experiment pulls.

`reset()` accepts an optional `seed` argument for interface parity with `Department.reset(seed=...)`. The LLM agent doesn't use the seed (sampling temperature, not a local RNG, drives its stochasticity), but `run_simulation` calls `reset(seed=dept_seed)` on both classes uniformly.

`LLMDepartment.propose_action` was consolidated to route through `src/llm_client.py::call_openrouter` + `parse_action`. The previous duplicate `_client` singleton, manual timing, and inline regex parsing were removed; there is now a single shared OpenAI client across the LLM stack.

---

## 7. Memory Ablation (`main_llm_memory_ablation.py`)

Runs Independent + `LLMCentralized` + `CrewAIDebate` on the standard composition under two regimes:

| Regime | `memory_window` (depts + coordinators) |
|---|---|
| `previous` | 1 |
| `full_history` | 5 |

Writes `results/llm_memory/raw/memory_ablation.csv` (one row per run, tagged with `memory_mode`) and a per-mechanism × memory-mode summary table.

---

## 8. Single + Multi-Model in One Entry Point (`main_llm.py`)

The previously-separate `main_llm.py` (single-model) and `main_llm_multi.py` (multi-model) are now merged. `main_llm.py` reads `LLM_MODELS` from the environment:

- **Unset**: behaves like the old single-model script. Output goes flat to `results/llm/`.
- **Set to `a,b,c`**: loops over each model, output goes to `results/llm/<slug>/`, plus a combined `results/llm/raw/multi_model_aggregated.csv` and `results/llm/figures/model_comparison.png`.

### Mechanism set
Each model runs the full **paired-analog set** (matching `main.py`'s leader archetypes):

```
IndependentCoordination
CentralizedCoordination(profit)         ← paired analog for LLMCentralizedCoordination
CentralizedCoordination(sustainability)  ← paired analog for LLMCentralizedCoordination
CentralizedCoordination(risk_averse)    ← paired analog for LLMCentralizedCoordination
StructuredDebateCoordination             ← paired analog for CrewAIDebateCoordination
LLMCentralizedCoordination               ← LLM CFO
CrewAIDebateCoordination                 ← LLM debate
```

So the LLM CFO is compared against *every* rule-based leader archetype, not just one.

### Design choice (deliberate)
Both the department LLM and the coordinator LLM use the **same** model in each pass. We do **not** sweep them independently — that would multiply cell count by N² and the report's research question is *"does model choice X dominate Y across the LLM stack?"*, not *"which layer is the model bottleneck?"*.

### `SMOKE=1`
Restricts to the standard composition only and caps max_steps at 2. For catching CrewAI/OpenRouter wiring bugs before paying for the full sweep.

### `model` propagation
For LLM coordinators the model comes from the coordination cost dict; for rule-based coordinators paired with `LLMDepartment`, it comes from the departments' proposal calls:

```
department.propose_action() / coordination.decide()
  → simulation.py step_record["model"]
  → metrics.compute_metrics() metrics["model"] (first non-empty)
  → CSV column "model"
```

---

## 9. `smoke_test_llm.py`

Cheap end-to-end check (~10 steps × 1 composition) for the two LLM mechanisms. Prints per-step `final_actions` and `rationale`, flags `crewai_error` / `parse_failed` / `global_fallback` rationales, and summarises clean-parse rates. Used before launching any expensive sweep.

---

## 10. Environmental Sensitivity Sweep

`sensitivity_analysis.py` uses `make_compositions(Department, ...)` and emits results through `plot_sensitivity_heatmap` (one heatmap per mechanism, `recovery_noise_std × shock_probability`, cells coloured by `crisis_rate` or any other metric column). 3×3 grid: noise ∈ {0.01, 0.05, 0.15} × shock ∈ {0.0, 0.05, 0.10}, 10 seeds per cell.

---

## 11. New Plots in `src/plotting.py`

| Plot | What it shows |
|---|---|
| `plot_per_role_rewards` | One panel per role, bar = mean reward per mechanism |
| `plot_scale_robustness` | Grouped bars: mechanism × scale (crisis_rate / welfare / avg_reserve) |
| `plot_sensitivity_heatmap` | One heatmap per mechanism over the (noise, shock) grid |
| `plot_model_comparison` | Grouped bars: mechanism × model (crisis / welfare / latency) — used in multi-model mode |
| `plot_cost_vs_welfare_pareto` | Scatter: coordination cost vs welfare, with Pareto frontier overlay. Uses `llm_calls_mean` when present, falls back to `total_messages_mean`. |

---

## 12. Cleanup pass

A series of consolidations that don't change experimental claims but make the codebase honest about its dependencies and avoid drift:

- **`python-dotenv` replaces the hand-rolled `.env` loader.** The custom 38-line loader in the deleted `src/config.py` is gone; `src/llm_client.py` calls `dotenv.load_dotenv()` directly. `python-dotenv` is now a declared dependency in `requirements.txt` / `pyproject.toml`.
- **`src/config.py` deleted.** Its sole survivor (`get_llm_model`) was moved into `src/llm_client.py`, eliminating one cross-module import for the seven scripts that needed it.
- **`src/actions.py` deleted.** `ACTION_TO_WITHDRAWAL` moved into `src/simulation.py` (next to the only function that consumes it as a default).
- **`ROLE_PROMPTS` unified in `src/prompts.py`.** The previous duplicates in `src/llm_agents.py::ROLE_PROMPTS` and `src/prompts.py::DEPARTMENT_ROLE_PROMPTS` were collapsed; `crewai_coordination.py::ROLE_METADATA[*]["backstory"]` now derives from the same dict by reference. The dead `DEPARTMENT_ROLE_PROMPTS`, `build_department_prompt`, and `build_debate_moderator_prompt` helpers were removed.
- **`LLMDepartment` consolidated through `src/llm_client.py`.** Removed the duplicate OpenAI client singleton, the local `_get_client()`, the manual timing, and the inline regex parser; the department now calls `call_openrouter()` + `parse_action()`.
- **`main_llm_multi.py` merged into `main_llm.py`** (see section 8) and deleted.
- **Env-var pruning.** `LLM_N_SEEDS`, `LLM_MULTI_N_SEEDS`, `ABLATION_N_SEEDS`, `LLM_MULTI_MAX_STEPS`, `ABLATION_MAX_STEPS`, `LLM_MULTI_COMPOSITIONS`, `LLM_MECHANISMS`, `LLM_CREWAI_DELEGATION`, and (most) `LLM_COMPOSITIONS` references removed. Surviving env vars: `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_MODELS`, `LLM_MAX_STEPS`, `SMOKE_MODEL`, `SMOKE_STEPS`, `SMOKE`.
- **Seed plumbing removed from the LLM track.** LLM departments ignore seeds (sampling-temperature is server-side; reseeding is meaningless). The seed loop in `main_llm.py` and the memory-ablation script was dropped along with the env vars above. The rule-based track still uses seeds and is unaffected.

---

## Files Changed

| File | Change |
|---|---|
| `src/experiment.py` | Shared sweep runner; now also owns `SCALES` (moved from `main.py`) and `DEFAULT_SCALES`. |
| `src/compositions.py` | Class-agnostic role-mix factories used by both tracks. |
| `main.py` | Thin entry point (~55 lines). Imports `SCALES` from `experiment.py`. |
| `main_llm.py` | Single + multi-model in one file. 7 mechanisms including the three Centralized leader analogs. |
| `main_llm_memory_ablation.py` | Memory ablation experiment. |
| `smoke_test_llm.py` | Quick LLM end-to-end sanity check. |
| `sensitivity_analysis.py` | Uses `make_compositions` and `plot_sensitivity_heatmap`. |
| `src/coordination.py` | `CoordinationMechanism.reset()`; `LLMCentralizedCoordination` with `memory_window`/`_memory_log`/`reset()`; lazy `from src.llm_client import …` to keep `main.py` LLM-free. |
| `src/crewai_coordination.py` | Two-round debate; cross-step `_memory_log` with `reset()`; cached LLM object; `ROLE_METADATA["backstory"]` references `ROLE_PROMPTS`. |
| `src/llm_agents.py` | `memory_window` parameter; `propose_action` routes through `llm_client`; `reset(seed=...)` for interface parity. |
| `src/llm_client.py` | One shared OpenAI client. Houses `get_llm_model`, `call_openrouter`, `LLMResponse`, `parse_action`, `parse_json_action`, `parse_per_dept_actions`. |
| `src/prompts.py` | `ROLE_PROMPTS` (single source of truth) + `build_centralized_leader_prompt`. Dead helpers removed. |
| `src/simulation.py` | Calls `coordination.reset()` per episode; accepts optional `action_to_withdrawal`; owns the canonical `ACTION_TO_WITHDRAWAL` dict; propagates `model` into step records. |
| `src/metrics.py` | `reward_<role>` per-role metrics; surfaces the `model` field. |
| `src/plotting.py` | Adds the five new plot functions listed in section 11. |
| `src/config.py`, `src/actions.py`, `main_llm_multi.py` | **Deleted** (see section 12). |

---

## How to Run

```bash
uv python install 3.12
uv sync          # or: pip install -r requirements.txt

# Rule-based: 4 scales × 3 compositions × 7 mechanisms × 20 seeds.
python main.py

# Environmental sensitivity (3x3 grid).
python sensitivity_analysis.py

# LLM single-model (requires OPENROUTER_API_KEY + LLM_MODEL in .env).
python smoke_test_llm.py                # sanity check first
python main_llm.py                       # full LLM-track sweep

# LLM multi-model.
SMOKE=1 LLM_MODELS=a,b,c python main_llm.py    # smoke first
LLM_MODELS=a,b,c python main_llm.py            # full

# Memory ablation.
python main_llm_memory_ablation.py
```

Outputs:

- `results/raw/` and `results/figures/` — rule-based sweep + sensitivity.
- `results/llm/` — single-model LLM sweep (flat layout).
- `results/llm/<model_slug>/` — per-model results in multi-model mode; combined CSV + `model_comparison.png` at the top level.
- `results/llm_memory/raw/` — memory-ablation tables.
