# CrewAI Usage

This project uses CrewAI only for the LLM debate coordination mechanism: `CrewAIDebateCoordination` in `src/crewai_coordination.py`.

CrewAI is not the main application runtime. The liquidity simulation already owns its own timestep loop, reserve state, reward accounting, crisis termination, metrics, and plotting. CrewAI is embedded inside one coordination mechanism so the experiment can compare a genuine multi-agent debate against the rule-based debate and the centralized LLM coordinator.

## Why CrewAI Is Used

Most mechanisms in the project are simple decision policies:

- `IndependentCoordination`: each department keeps its own proposal.
- `VotingCoordination` / `AdaptiveVotingCoordination`: departments vote (the latter weights conservative votes more when the reserve is low).
- `CentralizedCoordination`: one leader chooses the outcome.
- `StructuredDebateCoordination`: rule-based risk/justification aggregation.
- `LLMCentralizedCoordination`: one LLM acts as a CFO-style allocator.

`CrewAIDebateCoordination` is different. It models several department heads with distinct goals, arguments, and rebuttals. That maps well to CrewAI because CrewAI provides first-class `Agent`, `Task`, `Crew`, and `Process` primitives for coordinating multiple LLM-backed roles.

The research question:

> Does a real multi-agent LLM debate produce better liquidity decisions than a single centralized LLM allocator or a rule-based structured debate?

## Why This Is Not a CrewAI Flow App

The CrewAI quickstart recommends Flow projects for production apps where CrewAI owns state and execution order. That is not the best fit here.

The simulation loop in `src/simulation.py` already owns: current reserve level, department proposals, reward updates, stochastic recovery and shocks, per-step history, early termination on crisis, and metric aggregation.

So this project embeds CrewAI *inside* `CrewAIDebateCoordination.decide(...)` instead of using `crewai create flow` or `crewai run`. Each simulation step calls the coordinator, the coordinator runs one CrewAI crew for that decision, then returns normal project actions:

```python
final_actions, cost = coordination.decide(
    proposals=proposals,
    reserve_level=environment.reserve,
    departments=departments,
)
```

This keeps all mechanisms comparable because every mechanism implements the same `CoordinationMechanism.decide(...)` interface.

## How The Crew Is Built

For each simulation step, `CrewAIDebateCoordination` creates:

- one CrewAI `Agent` per department,
- one moderator `Agent`,
- opening-argument `Task`s,
- rebuttal `Task`s,
- one moderator allocation `Task`,
- one sequential `Crew`.

### Persona alignment (shared with `LLMDepartment`)

Each agent's `role`, `goal`, and `backstory` come from `ROLE_METADATA` in `src/crewai_coordination.py`. The `backstory` field is **not** duplicated text — it's taken directly from `src/prompts.py::ROLE_PROMPTS` by reference, so a CrewAI agent's persona description is the exact same string used in `LLMDepartment`'s system prompt:

```python
ROLE_METADATA = {
    "profit": {
        "role": "Growth & Trading Department Head",
        "goal": "Maximize the department's withdrawal to fund aggressive investment ...",
        "backstory": ROLE_PROMPTS["profit"],   # same dict entry LLMDepartment uses
    },
    ...
}
```

`role` and `goal` stay local to `crewai_coordination.py` because the CrewAI framework consumes them as separate fields. The `backstory` is the part that overlaps with the standalone LLM department's worldview, so unifying it kills a drift risk we had earlier (two near-identical persona descriptions that had silently diverged in wording).

### Process

The process is sequential:

1. Each department gives an opening argument defending its proposed action.
2. Each department reads the openings and gives a rebuttal, optionally updating its preferred action.
3. The moderator reads both rounds and allocates a final action to each department individually.

The expected moderator output is JSON with one key per department plus a `reason` field. The output is parsed by `parse_per_dept_actions(...)` from `src/llm_client.py`.

## Runtime Inputs

Following the CrewAI quickstart pattern, dynamic simulation values are passed through `crew.kickoff(inputs=...)`. The current inputs include: reserve level, reserve percentage, crisis proximity label, crisis threshold, department count, and a short memory context from previous debate outcomes (see "Memory" below).

## Memory

`CrewAIDebateCoordination` carries a `_memory_log` of recent decisions across simulation steps (default `memory_window=5`). The log is summarised and injected into the prompt so the moderator and dept agents have the same kind of cross-step context that `LLMDepartment` has had since day one. This is the confound the `main_llm_ablation.py memory` experiment isolates by toggling `memory_window` between 1 and 5.

`reset()` clears the log between simulation episodes — `run_simulation` calls it once per seed so different seeds are actually independent.

## `allow_delegation`

The constructor takes `allow_delegation: bool = True`, but every production caller (`main_llm.py`, `main_llm_ablation.py memory`, `smoke_test_llm.py`) passes `allow_delegation=False`. Why:

- **With delegation off**, each step is exactly `2N + 1` LLM calls (`N` opening + `N` rebuttal + `1` moderator). For `N=5` that's 11 coordinator-level calls.
- **With delegation on**, CrewAI lets one agent issue mid-task sub-calls to "ask" another. Token cost balloons unpredictably, and `llm_calls` in the cost dict becomes a *lower bound* (sub-calls aren't tracked individually). Wall-clock latency stays accurate.

So delegation is disabled in production runs to keep the per-step LLM-call count predictable for the cost ballparks the report quotes. The constructor default of `True` is preserved for ad-hoc diagnostic runs where you might want emergent inter-agent questioning.

## Model Configuration

CrewAI uses its own `LLM` object:

```python
from crewai import LLM

LLM(
    model="openrouter/<your-openrouter-model>",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
```

The public experiment configuration uses the bare OpenRouter model name in `.env`:

```env
LLM_MODEL=deepseek/deepseek-v4-flash
```

`CrewAIDebateCoordination` normalises that name internally by adding the `openrouter/` provider prefix required by CrewAI/LiteLLM if it isn't already present.

The rest of the LLM path (`LLMDepartment`, `LLMCentralizedCoordination`) routes through `src/llm_client.py::call_openrouter`, which uses the OpenAI SDK against OpenRouter's OpenAI-compatible API. One shared OpenAI client; CrewAI brings its own.

## Environment Setup

CrewAI requires Python `>=3.10,<3.14`. The project pins Python `>=3.11,<3.14` (NumPy compatibility), and `uv` is the recommended toolchain:

```bash
uv python install 3.12
uv sync
```

Secrets go in `.env`:

```env
OPENROUTER_API_KEY=sk-or-your-key-here
LLM_MODEL=deepseek/deepseek-v4-flash
LLM_MAX_STEPS=20
```

The dependency is pinned in `pyproject.toml` and `requirements.txt`:

```text
crewai[litellm]==1.14.3
```

The `litellm` extra is required because CrewAI's OpenRouter provider uses LiteLLM under the hood.

## Cost Accounting

For `N` departments with `allow_delegation=False`:

| Component | Calls |
|---|---|
| Opening tasks | N |
| Rebuttal tasks | N |
| Moderator allocation | 1 |
| **Total per step** | **2N + 1** |

With `N=5` that's 11 calls per step at the coordinator layer. Add the `N=5` LLM-department proposal calls and CrewAIDebate is ~16 calls/step total — the most expensive mechanism in the LLM track by far.

If `allow_delegation=True`, CrewAI may perform additional sub-calls; the `llm_calls` field becomes a lower bound and wall-clock latency is the more reliable cost signal.

## Verification

Use the one-step smoke test before launching any full LLM sweep:

```bash
python smoke_test_llm.py
```

A healthy run reports both LLM mechanisms parsing cleanly:

```text
llm_centralized           1/1 steps parsed cleanly
crewai_debate             1/1 steps parsed cleanly
```

For the full LLM-track sweep (including multi-model comparison), use `main_llm.py`:

```bash
python main_llm.py                                # single model from LLM_MODEL
LLM_MODEL=a,b,c python main_llm.py               # multi-model sweep
```

Free OpenRouter models are useful for smoke tests, but they're not ideal for the full sweep because rate limits and latency can dominate the experiment. For practical LLM runs, keep `LLM_MAX_STEPS` modest unless you're using a fast, high-rate endpoint.

## Current Design Boundary

CrewAI is intentionally limited to the debate mechanism. Don't replace the baseline simulation loop with CrewAI Flow orchestration: that would make results harder to compare against the non-CrewAI mechanisms and would mix application orchestration concerns with the experimental coordination mechanism being measured.
