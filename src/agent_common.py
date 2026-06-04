RISK_THRESHOLDS = {
    "profit": (10, 25),
    "sustainability": (30, 60),
    "balanced": (20, 40),
    "risk_averse": (40, 70),
    "free_rider": (0, 0),
}

WITHDRAWAL_TO_ACTION = {
    1.0: "L",
    2.0: "M",
    3.0: "H",
}


def estimate_risk(role, reserve_level):
    high_threshold, medium_threshold = RISK_THRESHOLDS.get(role, (20, 40))
    if reserve_level < high_threshold:
        return 1.0
    if reserve_level < medium_threshold:
        return 0.5
    return 0.0


def justification_type(role):
    if role == "profit":
        return "growth"
    if role == "sustainability":
        return "liquidity_protection"
    if role == "risk_averse":
        return "crisis_avoidance"
    if role == "free_rider":
        return "exploitation"
    return "balancing"


def build_justification(role, proposed_action, reserve_level):
    return {
        "proposed": proposed_action,
        "risk_estimate": estimate_risk(role, reserve_level),
        "justification_type": justification_type(role),
        "role": role,
    }


def compute_reward(
    role,
    withdrawal,
    reserve_level,
    crisis,
    previous_reserve=None,
    reserve_capacity=100,
):
    if role == "profit":
        reward = withdrawal
    elif role == "sustainability":
        crisis_risk = 1.0 if reserve_level < 20 else 0.0
        reward = withdrawal - 5.0 * crisis_risk
    elif role == "balanced":
        reserve_deficit = max(0, 50 - reserve_level) / 50
        reward = withdrawal - 3.0 * reserve_deficit
    elif role == "risk_averse":
        if previous_reserve is not None and previous_reserve > 0:
            volatility = abs(reserve_level - previous_reserve) / reserve_capacity
        else:
            volatility = 0.0
        reward = withdrawal - 2.0 * volatility
    elif role == "free_rider":
        reward = withdrawal * 1.5
    else:
        reward = withdrawal

    if crisis:
        reward -= 5.0

    return reward
