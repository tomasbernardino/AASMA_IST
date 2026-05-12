from dataclasses import dataclass


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

    def __init__(self, name, role, reserve_capacity=100):
        self.name = name
        self.role = role
        self.reserve_capacity = reserve_capacity
        self.total_reward = 0.0
        self.state = AgentState()

    def reset(self):
        """Reset accumulated reward and state before a new simulation."""
        self.total_reward = 0.0
        self.state = AgentState()

    def propose_action(self, reserve_level):
        """
        Return the withdrawal policy proposed by the department.
        """
        if self.role == "profit":
            return self._growth_policy(reserve_level)

        if self.role == "sustainability":
            return self._compliance_policy(reserve_level)

        if self.role == "balanced":
            return self._operations_policy(reserve_level)

        if self.role == "risk_averse":
            return self._risk_policy(reserve_level)

    def get_estimated_risk(self, reserve_level):
        """
        Estimate crisis risk for debate mechanism.
        Returns: 1.0 (high), 0.5 (medium), 0.0 (low)
        """
        if reserve_level < 20:
            return 1.0
        elif reserve_level < 40:
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
