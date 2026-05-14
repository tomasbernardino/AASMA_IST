# Fourth Commit: Intermediate Presentation Improvements

This document summarizes the improvements made to the baseline simulation in preparation for the intermediate presentation.

## 1. Exploration Noise (Bounded Rationality)

- **Implementation**: Added an `exploration_rate` parameter to the `Department` class (default set to `0.1` in `main.py`).
- **Mechanism**: Instead of strictly following their deterministic policy, departments now have a 10% chance (ε-greedy) of picking a uniformly random action (`L`, `M`, or `H`) at each step.
- **Reproducibility**: To ensure results remain deterministic given a specific seed, each department now maintains its own initialized random number generator (`np.random.default_rng(seed)`), rather than relying on the global numpy RNG.
- **Impact**: Prevents rigid deterministic lock-ins and models bounded rationality (e.g., departments making suboptimal or unexpected decisions), which is more realistic for multi-agent systems.

## 2. Per-Department Risk Perception

- **Implementation**: Replaced the global risk thresholds in `get_estimated_risk()` with role-specific thresholds in the `Department` class.
- **Mechanism**:
  - `profit`: High tolerance (only signals risk 1.0 when reserve < 10).
  - `sustainability`: Perceives danger earlier (risk 1.0 when reserve < 30).
  - `balanced`: Moderate risk perception (risk 1.0 when reserve < 20).
  - `risk_averse`: Extremely cautious (signals risk 1.0 when reserve < 40).
- **Impact**: The `StructuredDebateCoordination` mechanism now produces much more dynamic outcomes. Previously, all departments agreed on the level of risk simultaneously. Now, risk-averse departments will raise alarms and attempt to override aggressive policies much earlier than growth departments.

## 3. Metrics and Analytics Improvements

- **Fixed Debate Override Rate**: The previous logic for `debate_override_rate` was flawed for non-uniform mechanisms (like Centralized or Debate) as it only compared the majority proposal to the first element of `final_actions`. It now correctly checks if *any* department's proposed action was overridden in the final decision.
- **Social Welfare Metric**: Added `social_welfare` (the sum of all department rewards) to evaluate the collective efficiency of the system. This is a standard metric in multi-agent systems (AASMA) to assess whether a coordination mechanism improves global utility.
- **Per-Department Tracking**: 
  - Added a `reward_per_department` breakdown to the detailed metrics dictionary for granular fairness analysis.
  - Added `department_names` to the simulation step records to allow for detailed downstream tracing.

## 4. Visualizations by Composition

- **Implementation**: Added two new plotting functions in `plotting.py` (`plot_reserve_by_composition` and `plot_metrics_by_composition`).
- **Mechanism**: Instead of plotting all compositions (Standard, Aggressive, Conservative) together in a single tangled chart, the new functions generate distinct subplots for each composition. 
- **Impact**: Makes it drastically easier to compare the performance of different coordination mechanisms *within* a specific department composition (e.g., "How does Debate perform when the composition is Aggressive?").

## Note on LLM Agents
The `main_llm.py` file was deliberately left untouched during these improvements as per the current scope. It is important to note that `main_llm.py` currently contains a minor import bug (`DebateCoordination` instead of `StructuredDebateCoordination`) which should be resolved before finalizing the LLM portion for the final delivery.
