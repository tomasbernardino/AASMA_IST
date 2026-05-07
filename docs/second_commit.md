# Second Commit: Batched Experiments and Stochastic Environment

## Purpose

This commit adds statistical rigor and environmental realism to the Liquidity Commons
simulation. The first commit established a single deterministic run per mechanism.
This update introduces multiple seeds, stochastic dynamics, richer visualizations,
and computation-time measurements.

The goal is to produce a solid baseline with confidence intervals before introducing
LLM-based agents or more complex coordination mechanisms.

## Changes Summary

Four areas were modified:

1. Multi-seed experiments with aggregated metrics
2. Stochastic environment (noisy recovery + random shocks)
3. Richer plotting (confidence bands, metric bars, action distributions)
4. Wall-clock timing for each simulation run

## Multi-Seed Experiments

Previously, each coordination mechanism was tested with a single run.
A single trajectory is not statistically reliable, especially once stochasticity
is introduced.

Now `main.py` runs each mechanism N times (default: 20 seeds). For each seed,
the random generator in the environment is initialized with that seed, ensuring
full reproducibility.

Two CSV files are produced:

- `results/raw/detailed_runs.csv`: one row per (mechanism, seed) combination
- `results/raw/aggregated_comparison.csv`: one row per mechanism with mean ± std

## Stochastic Environment

The `LiquidityReserveEnvironment` now accepts three new parameters:

- `recovery_noise_std`: standard deviation of Gaussian noise added to the
  recovery rate at each step. When set to 0.0, the environment behaves
  exactly as before.

- `shock_probability`: probability that a random liquidity shock occurs
  at each step (e.g. market crisis, unexpected expense).

- `shock_magnitude`: size of the reserve drop when a shock occurs.

Default values in `main.py` are:

    recovery_noise_std = 0.05
    shock_probability  = 0.05
    shock_magnitude    = 10.0

The environment also accepts an `rng` parameter (a `numpy.random.Generator`)
for reproducibility. The simulation runner seeds this generator before each run.

All default values (noise=0, shock=0) preserve backward compatibility.

## Richer Plotting

Three new plot types are generated:

### Reserve Confidence Bands

Mean reserve trajectory with shaded ±1 std bands across all seeds.
Shorter histories (those that end in crisis) are padded with their final
reserve value so that all trajectories have equal length.

Output: `results/figures/reserve_confidence_bands.png`

### Metrics Comparison Bar Chart

Side-by-side bar charts comparing four key metrics across mechanisms:
average reserve, steps survived, average reward, and Gini coefficient.
Each bar has error bars showing the standard deviation across seeds.

Output: `results/figures/metrics_comparison.png`

### Action Distribution

Stacked bar chart showing the proportion of L / M / H actions for each
mechanism, aggregated across all seeds and all time steps.

Output: `results/figures/action_distributions.png`

## Timing

`run_simulation` now measures wall-clock time using `time.perf_counter()`.
The elapsed time is returned alongside the history and included in the
metrics as `wall_time_seconds`.

This is important for future comparisons: rule-based agents run in
microseconds, while LLM-based agents will take seconds per step.

## Files Modified

- `src/environment.py`: added stochastic parameters and numpy rng
- `src/simulation.py`: added seed parameter and timing
- `src/metrics.py`: added wall_time_seconds and seed to output
- `src/plotting.py`: added three new plotting functions
- `main.py`: multi-seed loop, aggregation, new plot calls

## Early Observations

From the aggregated results across 20 seeds with the stochastic environment:

- **Independent** and **centralized** mechanisms always lead to crisis
  (100% crisis rate). Centralized is the fastest to collapse (~10 steps).
- **Voting** achieves a 60% crisis rate and survives ~71 steps on average.
- **Debate** is the most sustainable: 30% crisis rate, ~86 steps survived,
  and the highest average reserve among surviving runs.
- **Independent** is the only mechanism with non-zero Gini (0.25),
  because departments use different individual policies.
- The action distribution shows that debate and voting favor low
  withdrawals (L), while centralized (led by the Trading team) almost
  exclusively uses high withdrawals (H).

## TODO Left for Later

- Real LLM debate or CrewAI orchestration
- Adaptive or learning-based departments
- More detailed reward functions
- Sensitivity analysis (varying environment parameters)
- Formal tests
