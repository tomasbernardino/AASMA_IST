from dataclasses import dataclass

import numpy as np

from src.agent_common import (
    build_justification,
    compute_reward,
    estimate_risk,
    justification_type,
)


@dataclass
class AgentState:
    prev_reserve: float = 100.0
    justification_type: str = "balancing"


class Department:
    """Rule-based department with a role-specific withdrawal policy."""

    def __init__(self, name, role, reserve_capacity=100, exploration_rate=0.0):
        self.name = name
        self.role = role
        self.reserve_capacity = reserve_capacity
        self.exploration_rate = exploration_rate
        self.total_reward = 0.0
        self.state = AgentState()
        self.rng = np.random.default_rng()

    def reset(self, seed=None):
        self.total_reward = 0.0
        self.state = AgentState()
        if seed is not None:
            self.rng = np.random.default_rng(seed)

    def propose_action(self, reserve_level):
        if self.exploration_rate > 0 and self.rng.random() < self.exploration_rate:
            return self.rng.choice(["L", "M", "H"])

        if self.role == "profit":
            return self._growth_policy(reserve_level)

        if self.role == "sustainability":
            return self._compliance_policy(reserve_level)

        if self.role == "balanced":
            return self._operations_policy(reserve_level)

        if self.role == "risk_averse":
            return self._risk_policy(reserve_level)

        if self.role == "free_rider":
            return self._free_rider_policy(reserve_level)

    def get_estimated_risk(self, reserve_level):
        return estimate_risk(self.role, reserve_level)

    def get_justification_type(self, proposed_action, reserve_level):
        return justification_type(self.role)

    def justify_action(self, proposed_action, reserve_level):
        return build_justification(self.role, proposed_action, reserve_level)

    def receive_reward(self, withdrawal, reserve_level, crisis):
        reward = compute_reward(
            role=self.role,
            withdrawal=withdrawal,
            reserve_level=reserve_level,
            crisis=crisis,
            previous_reserve=self.state.prev_reserve,
            reserve_capacity=self.reserve_capacity,
        )
        self.total_reward += reward
        self.state.prev_reserve = reserve_level
        return reward

    def _growth_policy(self, reserve_level):
        if reserve_level < 20:
            return "M"
        return "H"

    def _compliance_policy(self, reserve_level):
        if reserve_level < 70:
            return "L"
        return "M"

    def _operations_policy(self, reserve_level):
        if reserve_level < 40:
            return "L"
        if reserve_level > 80:
            return "H"
        return "M"

    def _risk_policy(self, reserve_level):
        if reserve_level < 90:
            return "L"
        return "M"

    def _free_rider_policy(self, reserve_level):
        return "H"
