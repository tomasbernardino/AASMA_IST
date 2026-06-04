from src.agent_common import (
    WITHDRAWAL_TO_ACTION,
    build_justification,
    compute_reward,
    estimate_risk,
    justification_type,
)
from src.llm_client import call_openrouter, get_llm_model, parse_action
from src.prompts import ROLE_PROMPTS
from src.prompts import build_universalization_prompt

class LLMDepartment:
    def __init__(self, name, role, model=None, temperature=0.3,
                 memory_window=5, universalization=False, n_departments=5):
        self.name = name
        self.role = role
        self.model = model or get_llm_model()
        self.temperature = temperature
        self.memory_window = memory_window
        self.total_reward = 0.0
        self.last_llm_calls = 0
        self.last_llm_latency_ms = 0.0
        self.last_llm_model = ""
        self.universalization = universalization
        self.n_departments = n_departments
        self._recent_history = []

    def reset(self, seed=None):
        """seed is accepted for interface parity with rule-based Department;
        LLM behavior is governed by temperature, not a local RNG."""
        self.total_reward = 0.0
        self._recent_history = []
        self.last_llm_calls = 0
        self.last_llm_latency_ms = 0.0
        self.last_llm_model = ""

    def get_estimated_risk(self, reserve_level):
        return estimate_risk(self.role, reserve_level)

    def get_justification_type(self, proposed_action, reserve_level):
        return justification_type(self.role)

    def justify_action(self, proposed_action, reserve_level):
        return build_justification(self.role, proposed_action, reserve_level)

    def propose_action(self, reserve_level, context=""):
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

        univ_text = ""
        if self.universalization:
            univ_text = "\n\n" + build_universalization_prompt(reserve_level, self.n_departments)

        context_text = f"\n\nContext from coordination:\n{context}" if context else ""

        user_prompt = (
            f"The shared liquidity reserve is currently at {reserve_level:.1f} "
            f"out of 100 maximum. The crisis threshold is 5."
            f"{history_text}{univ_text}{context_text}\n\n"
            f"Choose your withdrawal level for this step.\n"
            f"Reply with exactly one letter: L (low=1), M (medium=2), or H (high=3).\n"
            f"Do not include any other text."
        )

        # max_tokens=512 gives reasoning models room
        # to think before emitting the L/M/H letter at lower caps they burn
        # the whole budget on hidden reasoning tokens and return empty content
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

    def chat(self, reserve_level, transcript):
        """Generates a short chat message during free negotiation."""
        self.last_llm_calls += 1
        self.last_llm_model = self.model

        system_prompt = ROLE_PROMPTS.get(self.role, ROLE_PROMPTS["balanced"])
        
        user_prompt = (
            f"The shared liquidity reserve is currently at {reserve_level:.1f} / 100.\n"
            f"We are in a free negotiation phase before choosing withdrawal levels.\n\n"
            f"Current conversation transcript:\n{transcript if transcript else '(No messages yet)'}\n\n"
            f"Write a short, 1-2 sentence message to the other departments. "
            f"Advocate for your department's goals or respond to others."
        )

        try:
            response = call_openrouter(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=self.temperature,
                max_tokens=150,
            )
            self.last_llm_latency_ms += response.latency_ms
            return response.content.strip()
        except Exception:
            return "(silence)"

    def receive_reward(self, withdrawal, reserve_level, crisis):
        previous_reserve = (
            self._recent_history[-1]["reserve"]
            if self._recent_history else None
        )
        reward = compute_reward(
            role=self.role,
            withdrawal=withdrawal,
            reserve_level=reserve_level,
            crisis=crisis,
            previous_reserve=previous_reserve,
            reserve_capacity=100.0,
        )
        self.total_reward += reward

        step = len(self._recent_history)
        self._recent_history.append({
            "step": step,
            "reserve": reserve_level,
            "action": WITHDRAWAL_TO_ACTION.get(withdrawal, "?"),
            "reward": reward,
        })
        return reward
