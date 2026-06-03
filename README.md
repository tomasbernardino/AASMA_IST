# Liquidity Commons

Multi-agent simulation comparing coordination mechanisms over a shared liquidity reserve. Five departments propose Low / Medium / High withdrawal levels at each step; a coordination mechanism decides the final per-step actions. The goal is to evaluate mechanisms on sustainability (does the reserve survive?), welfare (total reward), fairness (signed-reward dispersion across departments), and coordination cost (messages, rounds, LLM calls).

## Setup

CrewAI requires Python `>=3.10,<3.14`; the project pins `>=3.11` for NumPy compatibility. With `uv`:

```bash
uv python install 3.12
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

Then create a `.env` (see `env.example`):

```env
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_MODEL=deepseek/deepseek-v4-flash
SMOKE_MODEL=deepseek/deepseek-v4-flash
SMOKE_STEPS=1
LLM_MAX_STEPS=20
```

Only `OPENROUTER_API_KEY` and `LLM_MODEL` are required for the LLM track; the others have sensible defaults.

## Running

```bash
# Rule-based baseline (no API key needed) — sweeps mechanisms × compositions × scales × seeds
python main.py

# Environment sensitivity — 3×3 grid of (recovery_noise_std × shock_probability)
python sensitivity_analysis.py

# LLM smoke test — cheap, ~10 steps, sanity-checks the LLM coordination mechanisms
python smoke_test_llm.py

# LLM track — single model with LLM_MODEL set
python main_llm.py

# LLM track — multi-model comparison
LLM_MODELS=openai/gpt-4o-mini,anthropic/claude-haiku-4-5,deepseek/deepseek-v4-flash python main_llm.py

# Memory ablation — varies memory_window (1 vs 5) for the LLM mechanisms
python main_llm_memory_ablation.py

# Cheap smoke for any LLM run
SMOKE=1 python main_llm.py
```

All entry points write CSVs to `results/raw/` (or `results/llm/`, `results/llm_memory/`) and PNGs to `results/figures/`. See `results/README.md` for what each file shows.

## Departments and compositions

Three role mixes, each with 5 departments. Roles drive both the rule-based agents' deterministic policies in `src/agents.py` and the LLM agents' system prompts in `src/prompts.py::ROLE_PROMPTS`.

| Composition  | profit × | sustainability × | balanced × | risk_averse × |
|--------------|----------|------------------|------------|---------------|
| standard     | 2        | 1                | 1          | 1             |
| aggressive   | 3        | 0                | 1          | 1             |
| conservative | 1        | 2                | 1          | 1             |

Exact names live in `src/compositions.py::COMPOSITION_SPECS`.

## Coordination mechanisms

**Rule-based** (`src/coordination.py`):
- `Independent` — each department executes its own proposal (no coordination).
- `Voting` — majority of proposals becomes everyone's action.
- `AdaptiveVoting` — like Voting, but conservative votes count more when the reserve is low.
- `Centralized(leader_index)` — one designated department's proposal becomes the upper-bound action for everyone. `main.py` runs three variants (profit / sustainability / risk_averse leaders).
- `StructuredDebate` — rule-based aggregation that overrides toward L/M when risk signals are high.

**LLM-based** (`src/coordination.py`, `src/crewai_coordination.py`):
- `LLMCentralizedCoordination` — a CFO-style LLM allocates an action per department from all proposals + reserve state.
- `CrewAIDebateCoordination` — N+1 CrewAI agents (one per department + a moderator) run a structured debate to produce per-department final actions.

`main.py` runs the rule-based mechanisms with rule-based departments. The three centralized variants select leaders by role (`centralized_profit`, `centralized_sustainability`, `centralized_risk_averse`) and skip compositions where that role is absent. `main_llm.py` runs a paired-analog set (Independent + Centralized + StructuredDebate + LLMCentralized + CrewAIDebate) all on top of LLM departments, so the rule-based-vs-LLM comparison happens at the coordinator layer with the agent population held constant.
