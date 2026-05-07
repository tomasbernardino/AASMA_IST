# First Commit: Liquidity Commons Basic Simulation

## Purpose

This commit adds the initial rule-based simulation setup for the Liquidity Commons scenario.
The model represents several departments drawing from a shared liquidity reserve and compares
how different coordination structures affect sustainability, efficiency, fairness, and
coordination cost.

This is a simple baseline. It is meant to establish the simulation architecture
before adding more advanced reasoning, richer debate, learning, and/or LLM-based orchestration.

## Narrative Mapping

The original shared-resource dilemma is framed as a shared financial reserve:

- Shared resource: common liquidity reserve
- Agents: departments or teams drawing from the reserve
- Consumption: withdrawal or investment level
- Regeneration: budget recovery, income, repayments, or periodic liquidity replenishment
- Collapse: liquidity crisis or reserve exhaustion

The actions remain discrete:

- `L`: low withdrawal
- `M`: medium withdrawal
- `H`: high withdrawal

## Departments

The current setup uses five rule-based departments:

- Growth Department: prefers aggressive investment when liquidity is available
- Trading/Opportunity Team: for now follows the Growth Department schema, in the future might invest more depending on whether the reserve conditions are good or not.
- Compliance Department: protects the reserve and prefers conservative spending
- Operations Department: balances funding needs with reserve stability
- Risk Department: strongly avoids liquidity crisis

These departments are intentionally heterogeneous so that their preferences can conflict.
That conflict is what makes coordination mechanisms meaningful to compare.

## Coordination Mechanisms

Four mechanisms are implemented:

- Independent: each department follows its own proposed policy
- Voting: departments vote, and the majority policy is applied to all
- Centralized: a CFO/treasury-style leader chooses the policy for all departments
- Debate: a simple rule-based debate model shifts decisions toward reserve protection when liquidity is low

The debate mechanism is currently not LLM-based. It is a transparent rule-based placeholder
that captures the idea of structured argumentation without adding orchestration complexity yet.

## Basic System Flow

The simulation starts in `main.py`, where the environment, departments, and coordination
mechanisms are created. For each mechanism, `run_simulation` executes the same repeated flow:

1. The liquidity reserve environment is reset.
2. Each department observes the current reserve level.
3. Each department proposes an action: `L`, `M`, or `H`.
4. The coordination mechanism receives all proposals and chooses the final policy or policies.
5. The simulation converts final actions into withdrawal amounts.
6. The environment applies budget recovery, subtracts withdrawals, and checks for liquidity crisis.
7. Departments receive rewards based on their withdrawals and whether a crisis occurred.
8. The step is stored in the history for later plotting and metric computation.

After the run finishes, metrics are computed and `main.py` saves the comparison CSV and reserve
trajectory plot.

## Metrics

The simulation records system-level, department-level, and coordination-cost metrics:

- Final reserve
- Average reserve
- Whether a liquidity crisis occurred
- Time to crisis
- Steps survived
- Total withdrawal
- Average reward
- Reward inequality using Gini coefficient
- Total messages
- Total coordination rounds

## Current Scope

Included in this first commit:

- Scalar liquidity reserve environment
- Rule-based department policies
- Four coordination mechanisms
- Repeated simulation loop
- Summary metrics
- CSV output
- Plot of liquidity reserve over time

TODO left for later:

- Multiple random seeds or batched experiments
- Stochastic environments
- Real LLM debate or CrewAI orchestration
- Adaptive or learning-based departments
- More detailed reward functions
- Computation-time measurements
- Formal tests
- ...
