from src.llm_client import call_openrouter, get_llm_model, parse_action
from src.prompts import ROLE_PROMPTS


class LLMDepartment:
    """Drop-in LLM replacement for the rule-based Department.

    `memory_window` of 0 disables history (agent sees only the current
    reserve); used by the memory-ablation experiment to isolate the
    contribution of cross-step history.
    """

    def __init__(self, name, role, model=None, temperature=0.3,
                 memory_window=5):
        self.name = name
        self.role = role
        self.model = model or get_llm_model()
        self.temperature = temperature
        self.memory_window = memory_window
        self.total_reward = 0.0
        self.last_llm_calls = 0
        self.last_llm_latency_ms = 0.0
        self.last_llm_model = ""
        self._recent_history = []

    def reset(self, seed=None):
        """`seed` is accepted for interface parity with rule-based Department;
        LLM behaviour is governed by temperature, not a local RNG."""
        self.total_reward = 0.0
        self._recent_history = []
        self.last_llm_calls = 0
        self.last_llm_latency_ms = 0.0
        self.last_llm_model = ""

    _RISK_THRESHOLDS = {
        "profit": (10, 25),
        "sustainability": (30, 60),
        "balanced": (20, 40),
        "risk_averse": (40, 70),
    }

    def get_estimated_risk(self, reserve_level):
        high_thresh, med_thresh = self._RISK_THRESHOLDS.get(
            self.role, (20, 40)
        )
        if reserve_level < high_thresh:
            return 1.0
        if reserve_level < med_thresh:
            return 0.5
        return 0.0

    def get_justification_type(self, proposed_action, reserve_level):
        if self.role == "profit":
            return "growth"
        if self.role == "sustainability":
            return "liquidity_protection"
        if self.role == "risk_averse":
            return "crisis_avoidance"
        return "balancing"

    def justify_action(self, proposed_action, reserve_level):
        return {
            "proposed": proposed_action,
            "risk_estimate": self.get_estimated_risk(reserve_level),
            "justification_type": self.get_justification_type(
                proposed_action, reserve_level
            ),
            "role": self.role,
        }

    def propose_action(self, reserve_level):
        """Falls back to "M" on API errors so a transient provider failure
        doesn't abort the simulation."""
        self.last_llm_calls = 1
        self.last_llm_latency_ms = 0.0
        self.last_llm_model = self.model

        system_prompt = ROLE_PROMPTS.get(self.role, ROLE_PROMPTS["balanced"])

        history_text = ""
        if self.memory_window > 0 and self._recent_history:
            recent = self._recent_history[-self.memory_window:]
            lines = []
            for entry in recent:
                lines.append(
                    f"  Step {entry['step']}: reserve={entry['reserve']:.1f}, "
                    f"you chose={entry['action']}, reward={entry['reward']:.1f}"
                )
            history_text = "\nYour recent history:\n" + "\n".join(lines)

        user_prompt = (
            f"The shared liquidity reserve is currently at {reserve_level:.1f} "
            f"out of 100 maximum. The crisis threshold is 5."
            f"{history_text}\n\n"
            f"Choose your withdrawal level for this step.\n"
            f"Reply with exactly one letter: L (low=1), M (medium=2), or H (high=3).\n"
            f"Do not include any other text."
        )

        # max_tokens=512 gives reasoning models (e.g. deepseek-v4-flash) room
        # to think before emitting the L/M/H letter — at lower caps they burn
        # the whole budget on hidden reasoning tokens and return empty content,
        # which parse_action silently maps to "M". 512 is also safely above the
        # >=16 minimum that Azure-served gpt-5.4-nano enforces. parse_action
        # extracts the first L/M/H character regardless of preceding text.
        try:
            response = call_openrouter(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=self.temperature,
                max_tokens=512,
            )
        except Exception:
            return "M"

        self.last_llm_latency_ms = response.latency_ms
        return parse_action(response)

    def receive_reward(self, withdrawal, reserve_level, crisis):
        """Reward function (identical to rule-based Department)."""
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
            if len(self._recent_history) > 0:
                prev_reserve = self._recent_history[-1]["reserve"]
                volatility = abs(reserve_level - prev_reserve) / 100.0
            else:
                volatility = 0.0
            gamma = 2.0
            reward = withdrawal - gamma * volatility
        else:
            reward = withdrawal

        if crisis:
            reward -= 5.0

        self.total_reward += reward

        step = len(self._recent_history)
        self._recent_history.append({
            "step": step,
            "reserve": reserve_level,
            "action": {1.0: "L", 2.0: "M", 3.0: "H"}.get(withdrawal, "?"),
            "reward": reward,
        })

        return reward
