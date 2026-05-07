

class LiquidityReserveEnvironment:
    """
    This class models a shared liquidity reserve.

    The reserve evolves over time based on:
    1. Periodic budget recovery, income, or repayments
    2. Withdrawals by multiple departments

    The system can reach a liquidity crisis if the reserve level
    falls below a critical threshold.

    This is a scalar model (no spatial dimension), designed to
    isolate the effects of decision-making and coordination.
    """

    def __init__(
        self,
        initial_reserve=100,
        reserve_capacity=100,
        recovery_rate=0.3,
        crisis_threshold=5,
    ):
        """
        Parameters:

        initial_reserve:
            Initial value of the liquidity reserve at time t = 0.

        reserve_capacity:
            Maximum possible value of the reserve (upper bound).

        recovery_rate:
            Controls how fast the reserve recovers.
            Used in a logistic growth function.

        crisis_threshold:
            If the reserve falls below this value, the system is considered
            to be in a liquidity crisis.
        """
        self.initial_reserve = initial_reserve
        self.reserve_capacity = reserve_capacity
        self.recovery_rate = recovery_rate
        self.crisis_threshold = crisis_threshold
        
        # Current state of the environment
        self.reserve = initial_reserve
        self.timestep = 0
        self.crisis = False

    def reset(self):
        self.reserve = self.initial_reserve
        self.timestep = 0
        self.crisis = False
        return self.reserve

    def budget_recovery(self):
        """
        Computes periodic recovery of the liquidity reserve.

        We use a logistic growth model:
            recovery = r * L * (1 - L / K)

        Where:
            r = recovery_rate
            L = current liquidity reserve
            K = reserve capacity

        Returns:
            Amount of liquidity recovered in this step.
        """
        return self.recovery_rate * self.reserve * (1 - self.reserve / self.reserve_capacity)

    def step(self, withdrawals):
        """
        Advances the environment by one time step.

        Parameters:
            withdrawals:
                List of withdrawal values from each department.

        Returns:
            reserve (float): updated liquidity reserve level
            crisis (bool): whether a liquidity crisis has occurred
        """

        # Sum all department withdrawals.
        total_withdrawal = sum(withdrawals)

        if self.crisis:
            return self.reserve, True

        # Apply budget recovery and update the liquidity reserve.
        self.reserve = self.reserve + self.budget_recovery() - total_withdrawal
        self.reserve = max(0, min(self.reserve_capacity, self.reserve))

        self.timestep += 1

        # Check liquidity crisis condition.
        if self.reserve <= self.crisis_threshold:
            self.crisis = True

        return self.reserve, self.crisis
