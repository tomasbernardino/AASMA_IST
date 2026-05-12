import os
import re

from openai import OpenAI


# Shared client instance, initialized once.
_client = None


def _get_client():
    """Return a shared OpenAI client configured for OpenRouter (lazy initialization)."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client


ROLE_PROMPTS = {
    "profit": (
        "You are the Growth Department. Your priority is aggressive investment "
        "and maximizing returns. You prefer high withdrawals when liquidity is "
        "available, and only reduce spending when the reserve is dangerously low."
    ),
    "sustainability": (
        "You are the Compliance Department. Your priority is protecting the "
        "reserve and ensuring long-term sustainability. You strongly prefer "
        "low withdrawals unless the reserve is very healthy."
    ),
    "balanced": (
        "You are the Operations Department. You balance funding needs with "
        "reserve stability. You adapt your spending to the current state of "
        "the reserve, withdrawing more when liquidity is high and less when "
        "it is low."
    ),
    "risk_averse": (
        "You are the Risk Department. You strongly avoid liquidity crisis. "
        "You almost always prefer low withdrawals unless the reserve is at "
        "near-full capacity."
    ),
}


class LLMDepartment:
    """
    LLM-based department drawing from a common liquidity reserve.

    Same interface as the rule-based Department class so that it can be
    used as a drop-in replacement in the simulation loop.

    Each call to propose_action sends a prompt to OpenAI and parses
    the response as one of L, M, or H.
    """

    def __init__(self, name, role, model="gpt-4o-mini", temperature=0.3):
        """
        Parameters:

        name:
            Department name (for display and logging).

        role:
            One of: profit, sustainability, balanced, risk_averse.

        model:
            OpenAI model identifier.

        temperature:
            Sampling temperature. Lower values produce more deterministic
            behavior, higher values encourage exploration.
        """
        self.name = name
        self.role = role
        self.model = model
        self.temperature = temperature
        self.total_reward = 0.0

        # History of recent decisions for context.
        self._recent_history = []

    def reset(self):
        """Reset accumulated reward and history before a new simulation."""
        self.total_reward = 0.0
        self._recent_history = []

    def propose_action(self, reserve_level):
        """
        Ask the LLM to choose a withdrawal policy.

        Returns one of: "L", "M", "H".
        """
        system_prompt = ROLE_PROMPTS.get(self.role, ROLE_PROMPTS["balanced"])

        # Build context from recent steps (last 5).
        history_text = ""
        if self._recent_history:
            recent = self._recent_history[-5:]
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

        try:
            client = _get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=5,
            )

            raw = response.choices[0].message.content.strip().upper()

            # Parse the response: extract L, M, or H.
            match = re.search(r"[LMH]", raw)
            if match:
                return match.group(0)

            # If parsing fails, fall back to M.
            return "M"

        except Exception:
            # On API error, fall back to M to keep the simulation running.
            return "M"

    def receive_reward(self, withdrawal, reserve_level, crisis):
        """
        Reward function (identical to rule-based Department).
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

        # Store for context in future prompts.
        step = len(self._recent_history)
        self._recent_history.append({
            "step": step,
            "reserve": reserve_level,
            "action": {1.0: "L", 2.0: "M", 3.0: "H"}.get(withdrawal, "?"),
            "reward": reward,
        })

        return reward
