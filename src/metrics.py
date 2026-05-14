# src/metrics.py

import numpy as np
from collections import Counter


def gini(values):
    """
    Compute Gini coefficient for inequality.

    0 means perfect equality.
    Higher values mean more inequality.
    """
    values = np.array(values, dtype=float)

    # If every department received zero reward, there is no inequality to report.
    if np.all(values == 0):
        return 0.0

    values = np.sort(values)
    n = len(values)

    cumulative = np.cumsum(values)

    return (n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n


def compute_metrics(history, departments, max_steps=100, wall_time_seconds=None, seed=None):
    """
    Compute summary metrics for one simulation run.
    """
    # Reserve metrics capture the system-level sustainability outcome.
    reserves = [step["new_reserve"] for step in history]
    total_withdrawals = [step["total_withdrawal"] for step in history]

    crisis = any(step["crisis"] for step in history)

    # Time to crisis is only defined when the reserve crosses the crisis threshold.
    if crisis:
        time_to_crisis = next(
            step["t"] for step in history if step["crisis"]
        )
    else:
        time_to_crisis = None

    final_reserve = reserves[-1] if reserves else None
    average_reserve = float(np.mean(reserves)) if reserves else 0.0

    # Department rewards are used for efficiency and fairness comparisons.
    total_reward_per_department = [department.total_reward for department in departments]

    # Message and round counts approximate the cost of coordination.
    total_messages = sum(step["messages"] for step in history)
    total_rounds = sum(step["rounds"] for step in history)

    override_steps = sum(
        1 for step in history
        if step.get("final_actions") and step.get("proposals")
        and any(p != f for p, f in zip(step["proposals"], step["final_actions"]))
    )
    debate_override_rate = override_steps / len(history) if history else 0.0

    metrics = {
        "mechanism": history[0]["mechanism"] if history else "unknown",
        "seed": seed,
        "final_reserve": final_reserve,
        "average_reserve": average_reserve,
        "liquidity_crisis": crisis,
        "time_to_crisis": time_to_crisis,
        "steps_survived": len(history),
        "total_withdrawal": sum(total_withdrawals),
        "average_reward": float(np.mean(total_reward_per_department)),
        "social_welfare": float(np.sum(total_reward_per_department)),
        "reward_inequality_gini": gini(total_reward_per_department),
        "total_messages": total_messages,
        "total_rounds": total_rounds,
        "wall_time_seconds": wall_time_seconds,
        "debate_override_rate": debate_override_rate,
        "reward_per_department": {
            dept.name: dept.total_reward for dept in departments
        },
    }
    
    llm_calls = sum(step.get("llm_calls", 0) for step in history)
    llm_latency = sum(step.get("llm_latency_ms", 0) for step in history)
    
    if llm_calls > 0:
        metrics["llm_calls"] = llm_calls
        metrics["llm_total_latency_ms"] = llm_latency
        metrics["llm_avg_latency_ms"] = llm_latency / llm_calls
    
    return metrics
