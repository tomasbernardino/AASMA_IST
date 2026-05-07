import numpy as np


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

    Optionally, the environment can introduce stochasticity via:
    - Noise on the recovery rate (Gaussian perturbation each step)
    - Random liquidity shocks (sudden drops in reserve)
    """

    def __init__(
        self,
        initial_reserve=100,
        reserve_capacity=100,
        recovery_rate=0.3,
        crisis_threshold=5,
        recovery_noise_std=0.0,
        shock_probability=0.0,
        shock_magnitude=10.0,
        rng=None,
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

        recovery_noise_std:
            Standard deviation of Gaussian noise added to the recovery rate
            at each step. Set to 0.0 for deterministic behavior.

        shock_probability:
            Probability of a sudden liquidity shock at each step.
            Set to 0.0 to disable shocks.

        shock_magnitude:
            Size of the reserve drop when a shock occurs.

        rng:
            A numpy random Generator for reproducibility.
            If None, a default generator is created.
        """
        self.initial_reserve = initial_reserve
        self.reserve_capacity = reserve_capacity
        self.recovery_rate = recovery_rate
        self.crisis_threshold = crisis_threshold
        self.recovery_noise_std = recovery_noise_std
        self.shock_probability = shock_probability
        self.shock_magnitude = shock_magnitude
        self.rng = rng if rng is not None else np.random.default_rng()

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

        When recovery_noise_std > 0, the rate r is perturbed each step
        by additive Gaussian noise (clamped so that r stays non-negative).

        Returns:
            Amount of liquidity recovered in this step.
        """
        rate = self.recovery_rate

        if self.recovery_noise_std > 0:
            noise = self.rng.normal(0, self.recovery_noise_std)
            rate = max(0.0, rate + noise)

        return rate * self.reserve * (1 - self.reserve / self.reserve_capacity)

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

        # Apply random liquidity shock (market crisis, unexpected expense).
        if self.shock_probability > 0 and self.rng.random() < self.shock_probability:
            self.reserve -= self.shock_magnitude

        self.reserve = max(0, min(self.reserve_capacity, self.reserve))

        self.timestep += 1

        # Check liquidity crisis condition.
        if self.reserve <= self.crisis_threshold:
            self.crisis = True

        return self.reserve, self.crisis
