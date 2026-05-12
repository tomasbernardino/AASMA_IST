# Third Commit: LLM-Based Departments (Option A)

## Purpose

This commit introduces LLM-powered departments as an alternative to the
rule-based baseline. Each department sends a prompt to OpenAI describing its
role and the current reserve state, and the LLM chooses a withdrawal level
(L, M, or H).

The implementation is fully separated from the baseline so that both can
be run independently and compared.

## Approach

Instead of modifying the existing `Department` class in `agents.py`, a new
`LLMDepartment` class is created in `src/llm_agents.py`. It exposes the
same interface (`propose_action`, `receive_reward`, `reset`) so it can be
used as a drop-in replacement in the simulation loop without modifying
`simulation.py` or `coordination.py`.

A separate entry point, `main_llm.py`, mirrors the structure of `main.py`
but creates `LLMDepartment` instances instead of `Department` instances.
Results are written to `results/llm/` to keep them separate from the
baseline results in `results/raw/`.

## LLM Department Design

Each department receives:

1. A **system prompt** describing its role and priorities (e.g. the Growth
   Department is told to prioritize aggressive investment).

2. A **user prompt** with:
   - Current reserve level and capacity
   - Crisis threshold
   - The last 5 steps of its own history (action chosen, reward received)
   - A strict instruction to reply with exactly one letter: L, M, or H

The response is parsed with a regex to extract L, M, or H. If parsing
fails or the API returns an error, the department falls back to M.

## Role Prompts

Four role-specific system prompts are defined, matching the baseline roles:

- `profit`: aggressive investment, high withdrawals unless danger
- `sustainability`: reserve protection, prefers low withdrawals
- `balanced`: adapts to the reserve level
- `risk_averse`: strongly avoids crisis, almost always low

## Configuration

- **Model**: `gpt-4o-mini` by default (fast and cheap for experiments)
- **Temperature**: 0.3 (low for consistency, but not fully deterministic)
- **Seeds**: 5 per mechanism (LLM calls are slower and cost tokens)
- **Max tokens**: 5 per call (the answer is just one letter)

## New Files

- `src/llm_agents.py`: LLMDepartment class
- `main_llm.py`: separate entry point for LLM experiments

## Modified Files

- `requirements.txt`: added `openai>=1.0.0`

## How to Run

Set your OpenRouter API key and run:

    export OPENROUTER_API_KEY="sk-..."
    python main_llm.py

Or on Windows:

    set OPENROUTER_API_KEY=sk-...
    py main_llm.py

Results will be saved to `results/llm/`.

## TODO Left for Later

- Inter-agent communication (agents exchange messages before deciding)
- CrewAI-based debate orchestration
- Comparison script: baseline vs LLM side by side
- Test with different models (GPT-4o, Claude, open-source)
- Test with different temperatures
