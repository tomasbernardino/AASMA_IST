import time

import numpy as np

from src.actions import ACTION_TO_WITHDRAWAL


def run_simulation(environment, departments, coordination, max_steps=100, seed=None):
    """
    Run one simulation episode.

    Parameters:
        environment: LiquidityReserveEnvironment
        departments: list of Department objects
        coordination: coordination mechanism object
        max_steps: number of time steps
        seed: optional integer seed for reproducibility

    Returns:
        history: list of dictionaries with all relevant data
        elapsed_seconds: wall-clock time of the simulation
    """
    # Seed the environment random generator for reproducibility.
    if seed is not None:
        environment.rng = np.random.default_rng(seed)

    start_time = time.perf_counter()

    # Reset environment and departments.
    reserve = environment.reset()

    for department in departments:
        department.reset()

    history = []

    for t in range(max_steps):
        # Departments observe the reserve and propose spending policies.
        proposals = [
            department.propose_action(reserve)
            for department in departments
        ]

        # Coordination mechanism decides final spending policies.
        final_actions, coordination_cost = coordination.decide(
            proposals=proposals,
            reserve_level=reserve,
            departments=departments,
        )

        # Convert policies into actual withdrawal values.
        withdrawals = [
            ACTION_TO_WITHDRAWAL[action]
            for action in final_actions
        ]

        # Update environment
        new_reserve, crisis = environment.step(withdrawals)

        # Give rewards to departments based on their withdrawals and the new state.
        rewards = []
        for department, withdrawal in zip(departments, withdrawals):
            reward = department.receive_reward(
                withdrawal=withdrawal,
                reserve_level=new_reserve,
                crisis=crisis,
            )
            rewards.append(reward)

        # Store everything important for analysis
        history.append({
            "t": t,
            "reserve": reserve,
            "new_reserve": new_reserve,
            "proposals": proposals,
            "final_actions": final_actions,
            "withdrawals": withdrawals,
            "total_withdrawal": sum(withdrawals),
            "rewards": rewards,
            "crisis": crisis,
            "messages": coordination_cost["messages"],
            "rounds": coordination_cost["rounds"],
            "mechanism": coordination.name,
        })

        # Move to next state
        reserve = new_reserve

        if crisis:
            break

    elapsed_seconds = time.perf_counter() - start_time

    return history, elapsed_seconds
