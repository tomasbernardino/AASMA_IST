# Liquidity Commons

Multi-agent simulation comparing coordination mechanisms over a shared liquidity reserve. Five departments propose Low / Medium / High withdrawal levels at each step; a coordination mechanism decides the final per-step actions. The goal is to evaluate mechanisms on sustainability (does the reserve survive?), welfare (total reward), fairness (signed-reward dispersion across departments), and coordination cost (messages, rounds, LLM calls).

## Setup

Use Python `>=3.11,<3.14`. The project supports either `uv` or a standard virtual environment.

With `uv`:

```bash
uv python install 3.12
uv sync
```

Run commands through `uv run`, for example:

```bash
uv run python main.py
```

Or with `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The rule-based experiments do not need an API key. For LLM experiments, copy `.env.example` to `.env` and set an OpenRouter key:

```bash
cp .env.example .env
```

Minimum `.env` for LLM runs:

```env
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_MODEL=deepseek/deepseek-v4-flash
```

Optional step-count settings are documented in `.env.example`.
For multiple model runs add the models into the LLM_MODEL variable comma separated, as documented in `.env.example`. 

## Running

If using `uv`, prefix commands with `uv run`, for example `uv run python main.py`.

```bash
# Rule-based baseline no API key needed.
# Sweeps mechanisms x compositions x withdrawal scales x seeds.
python main.py

# Environmental sensitivity; no API key needed.
# Runs a 3 x 3 grid of recovery noise x shock probability.
python sensitivity_analysis.py

# Main LLM track; requires OPENROUTER_API_KEY.
python main_llm.py

# Controlled LLM side experiments.
python main_llm_ablation.py memory
python main_llm_ablation.py universalization
python main_llm_ablation.py negotiation
```

Outputs are written under `results/`

## Departments and compositions

Four role mixes, each with 5 departments. Roles drive both the rule-based agents' deterministic policies in and the LLM agents' system prompts.

| Composition  | profit × | sustainability × | balanced × | risk_averse × | free_rider × |
|--------------|----------|------------------|------------|---------------|--------------|
| standard     | 2        | 1                | 1          | 1             | 0            |
| aggressive   | 3        | 0                | 1          | 1             | 0            |
| conservative | 1        | 2                | 1          | 1             | 0            |
| free_rider   | 2        | 1                | 1          | 0             | 1            |


## Coordination mechanisms

**Rule-based** (`src/coordination.py`):
- `Independent` - each department executes its own proposal (no coordination).
- `Voting` - majority of proposals becomes everyone's action.
- `AdaptiveVoting` - like Voting, but conservative votes count more when the reserve is low.
- `Centralized(leader_index)` - one designated department's proposal becomes the upper-bound action for everyone. `main.py` runs three variants (profit / sustainability / risk_averse leaders).
- `StructuredDebate` - rule-based aggregation that overrides toward L/M when risk signals are high.

**LLM-based** (`src/coordination.py`, `src/crewai_coordination.py`):
- `LLMCentralizedCoordination` - a CFO-style LLM allocates an action per department from all proposals + reserve state.
- `CrewAIDebateCoordination` - N+1 CrewAI agents (one per department + a moderator) run a structured debate to produce per-department final actions.

`main.py` runs the rule-based mechanisms with rule-based departments. The three centralized variants select leaders by role (`centralized_profit`, `centralized_sustainability`, `centralized_risk_averse`) and skip compositions where that role is absent. `main_llm.py` runs a paired-analog set (Independent + Centralized + StructuredDebate + LLMCentralized + CrewAIDebate) all on top of LLM departments, so the rule-based-vs-LLM comparison happens at the coordinator layer with the agent population held constant.
