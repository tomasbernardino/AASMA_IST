from dataclasses import dataclass

import numpy as np


@dataclass
class AgentState:
    """Stores per-agent state for utility computation and justification."""
    prev_reserve: float = 100.0
    justification_type: str = "balancing"


class Department:
    """
    Role-based department drawing from a common liquidity reserve.

    Each department has:
        - name
        - role
        - accumulated reward
        - agent state for memory and utility computation
    """

    def __init__(self, name, role, reserve_capacity=100, exploration_rate=0.0):
        self.name = name
        self.role = role
        self.reserve_capacity = reserve_capacity
        self.exploration_rate = exploration_rate
        self.total_reward = 0.0
        self.state = AgentState()
        self.rng = np.random.default_rng()

    def reset(self, seed=None):
        """Reset accumulated reward and state before a new simulation."""
        self.total_reward = 0.0
        self.state = AgentState()
        if seed is not None:
            self.rng = np.random.default_rng(seed)

    def propose_action(self, reserve_level):
        """
        Return the withdrawal policy proposed by the department.

        With probability `exploration_rate`, the agent ignores its
        deterministic policy and picks a uniformly random action.
        This prevents lock-in and adds bounded rationality.
        """
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

    # Per-role risk perception thresholds.
    # Format: (high_risk_below, medium_risk_below)
    _RISK_THRESHOLDS = {
        "profit":         (10, 25),   # high tolerance — only panics at very low reserves
        "sustainability": (30, 60),   # perceives danger earlier
        "balanced":       (20, 40),   # moderate (same as original global thresholds)
        "risk_averse":    (40, 70),   # most cautious — sees risk when others don't
    }

    def get_estimated_risk(self, reserve_level):
        """
        Estimate crisis risk for debate mechanism.

        Returns: 1.0 (high), 0.5 (medium), 0.0 (low)

        The thresholds depend on the department's role: profit-oriented
        departments tolerate lower reserves before signalling danger,
        while risk-averse departments raise the alarm much earlier.
        """
        high_thresh, med_thresh = self._RISK_THRESHOLDS.get(
            self.role, (20, 40)
        )
        if reserve_level < high_thresh:
            return 1.0
        elif reserve_level < med_thresh:
            return 0.5
        return 0.0

    def get_justification_type(self, proposed_action, reserve_level):
        """
        Return the justification type for the proposed action.
        """
        if self.role == "profit":
            return "growth"
        elif self.role == "sustainability":
            return "liquidity_protection"
        elif self.role == "risk_averse":
            return "crisis_avoidance"
        else:
            return "balancing"

    def justify_action(self, proposed_action, reserve_level):
        """
        Return structured justification for the proposed action.
        Used for debate mechanism.
        """
        risk = self.get_estimated_risk(reserve_level)
        justification_type = self.get_justification_type(proposed_action, reserve_level)
        return {
            "proposed": proposed_action,
            "risk_estimate": risk,
            "justification_type": justification_type,
            "role": self.role,
        }

    def receive_reward(self, withdrawal, reserve_level, crisis):
        """
        Role-specific utility function.
        """
        if self.role == "profit":
            reward = withdrawal

        elif self.role == "sustainability":
            crisis_risk = 1.0 if reserve_level < 20 else 0.0
            alpha = 5.0
            reward = withdrawal - alpha * crisis_risk

        elif self.role == "balanced":
            reserve_deficit = max(0, 50 - reserve_level) / 50
            beta = 3.0
            reward = withdrawal - beta * reserve_deficit

        elif self.role == "risk_averse":
            if self.state.prev_reserve > 0:
                volatility = abs(reserve_level - self.state.prev_reserve) / self.reserve_capacity
            else:
                volatility = 0.0
            gamma = 2.0
            reward = withdrawal - gamma * volatility

        else:
            reward = withdrawal

        if crisis:
            reward -= 5.0

        self.total_reward += reward

        self.state.prev_reserve = reserve_level

        return reward

    def _growth_policy(self, reserve_level):
        """
        Growth prioritizes aggressive investment while liquidity is available.
        """
        if reserve_level < 20:
            return "M"
        return "H"

    def _compliance_policy(self, reserve_level):
        """
        Compliance prioritizes reserve protection and sustainability.
        """
        if reserve_level < 70:
            return "L"
        return "M"

    def _operations_policy(self, reserve_level):
        """
        Operations adapts spending to the state of the reserve.
        """
        if reserve_level < 40:
            return "L"
        if reserve_level > 80:
            return "H"
        return "M"

    def _risk_policy(self, reserve_level):
        """
        Risk strongly avoids liquidity crisis.
        """
        if reserve_level < 90:
            return "L"
        return "M"
