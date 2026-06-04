"""
Rule-based baseline
"""

from src.agents import Department
from src.compositions import make_compositions
from src.experiment import SCALES, run_experiment_sweep
from src.study_config import build_rule_based_mechanisms, make_default_env


def main():
    compositions = make_compositions(
        Department, reserve_capacity=100, exploration_rate=0.1,
    )

    run_experiment_sweep(
        coordination_mechanisms=build_rule_based_mechanisms(),
        compositions=compositions,
        env_factory=make_default_env,
        n_seeds=20,
        max_steps=100,
        output_dir="results",
        scales=SCALES,
    )


if __name__ == "__main__":
    main()
