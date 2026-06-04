import numpy as np


class LiquidityReserveEnvironment:
    """Shared liquidity reserve with logistic recovery and optional shocks."""

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
        self.initial_reserve = initial_reserve
        self.reserve_capacity = reserve_capacity
        self.recovery_rate = recovery_rate
        self.crisis_threshold = crisis_threshold
        self.recovery_noise_std = recovery_noise_std
        self.shock_probability = shock_probability
        self.shock_magnitude = shock_magnitude
        self.rng = rng if rng is not None else np.random.default_rng()

        self.reserve = initial_reserve
        self.timestep = 0
        self.crisis = False

    def reset(self):
        self.reserve = self.initial_reserve
        self.timestep = 0
        self.crisis = False
        return self.reserve

    def budget_recovery(self):
        rate = self.recovery_rate
        if self.recovery_noise_std > 0:
            rate = max(0.0, rate + self.rng.normal(0, self.recovery_noise_std))
        return rate * self.reserve * (1 - self.reserve / self.reserve_capacity)

    def step(self, withdrawals):
        if self.crisis:
            return self.reserve, True

        self.reserve = self.reserve + self.budget_recovery() - sum(withdrawals)

        if self.shock_probability > 0 and self.rng.random() < self.shock_probability:
            self.reserve -= self.shock_magnitude

        self.reserve = max(0, min(self.reserve_capacity, self.reserve))
        self.timestep += 1

        if self.reserve <= self.crisis_threshold:
            self.crisis = True

        return self.reserve, self.crisis
