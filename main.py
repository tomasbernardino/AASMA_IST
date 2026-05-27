"""
Rule-based baseline: sweeps mechanisms x compositions x L/M/H scales x seeds
and writes CSVs + figures under results/.
"""

from src.environment import LiquidityReserveEnvironment
from src.agents import Department
from src.coordination import (
    IndependentCoordination,
    VotingCoordination,
    AdaptiveVotingCoordination,
    CentralizedCoordination,
    StructuredDebateCoordination,
)
from src.compositions import make_compositions
from src.experiment import SCALES, run_experiment_sweep


def make_env():
    """Stochastic env: different seeds produce meaningfully different runs."""
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )


def main():
    coordination_mechanisms = [
        IndependentCoordination(),
        VotingCoordination(),
        AdaptiveVotingCoordination(),
        CentralizedCoordination(leader_index=1, name_suffix="_profit"),
        CentralizedCoordination(leader_index=2, name_suffix="_sustainability"),
        CentralizedCoordination(leader_index=4, name_suffix="_risk_averse"),
        StructuredDebateCoordination(),
    ]

    compositions = make_compositions(
        Department, reserve_capacity=100, exploration_rate=0.1,
    )

    run_experiment_sweep(
        coordination_mechanisms=coordination_mechanisms,
        compositions=compositions,
        env_factory=make_env,
        n_seeds=20,
        max_steps=100,
        output_dir="results",
        scales=SCALES,
    )


if __name__ == "__main__":
    main()
