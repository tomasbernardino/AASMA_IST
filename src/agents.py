class Department:
    """
    Role-based department drawing from a common liquidity reserve.

    Each department has:
        - name
        - role
        - accumulated reward
    """

    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.total_reward = 0.0

    def reset(self):
        """Reset accumulated reward before a new simulation."""
        self.total_reward = 0.0

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

    def receive_reward(self, withdrawal, reserve_level, crisis):
        """
        Reward function.
        """
        reward = withdrawal

        if crisis:
            reward -= 5.0

        self.total_reward += reward
        return reward

    # Department-specific policies

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
