import time

import numpy as np


ACTION_TO_WITHDRAWAL = {
    "L": 1.0,
    "M": 2.0,
    "H": 3.0,
}


def run_simulation(
    environment,
    departments,
    coordination,
    max_steps=100,
    seed=None,
    action_to_withdrawal=None,
):
    """Run one simulation episode and return per-step history plus elapsed time."""
    if action_to_withdrawal is None:
        action_to_withdrawal = ACTION_TO_WITHDRAWAL
    if seed is not None:
        environment.rng = np.random.default_rng(seed)

    start_time = time.perf_counter()

    reserve = environment.reset()

    for i, department in enumerate(departments):
        dept_seed = (seed + i + 1) if seed is not None else None
        department.reset(seed=dept_seed)

    coordination.reset()

    history = []

    for t in range(max_steps):
        proposals = [
            department.propose_action(reserve)
            for department in departments
        ]
        department_llm_calls = sum(
            getattr(department, "last_llm_calls", 0)
            for department in departments
        )
        department_llm_latency_ms = sum(
            getattr(department, "last_llm_latency_ms", 0.0)
            for department in departments
        )
        department_models = [
            getattr(department, "last_llm_model", "")
            for department in departments
            if getattr(department, "last_llm_model", "")
        ]

        final_actions, coordination_cost = coordination.decide(
            proposals=proposals,
            reserve_level=reserve,
            departments=departments,
        )

        justifications = coordination_cost.get("justifications")

        withdrawals = [
            action_to_withdrawal[action]
            for action in final_actions
        ]

        new_reserve, crisis = environment.step(withdrawals)

        rewards = []
        for department, withdrawal in zip(departments, withdrawals):
            reward = department.receive_reward(
                withdrawal=withdrawal,
                reserve_level=new_reserve,
                crisis=crisis,
            )
            rewards.append(reward)

        step_record = {
            "t": t,
            "reserve": reserve,
            "new_reserve": new_reserve,
            "proposals": proposals,
            "final_actions": final_actions,
            "withdrawals": withdrawals,
            "total_withdrawal": sum(withdrawals),
            "rewards": rewards,
            "department_names": [d.name for d in departments],
            "crisis": crisis,
            "messages": coordination_cost["messages"],
            "rounds": coordination_cost["rounds"],
            "mechanism": coordination.name,
            "justifications": justifications,
        }
        for key in ("leader_index", "leader_name", "leader_role"):
            if key in coordination_cost:
                step_record[key] = coordination_cost[key]

        total_llm_calls = department_llm_calls + coordination_cost.get("llm_calls", 0)
        if total_llm_calls > 0:
            step_record["llm_calls"] = total_llm_calls
            step_record["llm_latency_ms"] = (
                department_llm_latency_ms
                + coordination_cost.get("llm_latency_ms", 0)
            )
            step_record["rationale"] = coordination_cost.get("rationale", "")
            step_record["model"] = (
                coordination_cost.get("model", "")
                or (department_models[0] if department_models else "")
            )

        history.append(step_record)

        reserve = new_reserve

        if crisis:
            break

    elapsed_seconds = time.perf_counter() - start_time

    return history, elapsed_seconds
