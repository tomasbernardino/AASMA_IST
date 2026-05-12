"""
src/crewai_coordination.py

CrewAI-based debate coordination mechanism.

Each department is mapped to a CrewAI Agent with a role, goal, and backstory
derived from the existing prompts.py role descriptions. A Moderator agent
synthesizes all arguments and returns the final group action (L, M, or H).

Process: Sequential
  - Each department agent produces a proposal + justification.
  - The moderator agent reads all outputs and decides the final action.

This is intentionally the ONLY mechanism that uses CrewAI, because debate
is the only mechanism that genuinely has N interacting agents with distinct
roles — exactly what CrewAI was designed to orchestrate.
"""

import os
import re
import time

from src.coordination import CoordinationMechanism
from src.prompts import DEPARTMENT_ROLE_PROMPTS


# ---------------------------------------------------------------------------
# Role metadata for CrewAI agent construction
# ---------------------------------------------------------------------------

ROLE_METADATA = {
    "profit": {
        "role": "Growth & Trading Department Head",
        "goal": "Maximize the department's withdrawal to fund aggressive investment and growth.",
        "backstory": (
            "You lead the Growth and Trading departments. Your mandate is to maximize "
            "returns and capture opportunities. You push for high capital deployment "
            "when liquidity allows, and only back down when crisis is truly imminent."
        ),
    },
    "sustainability": {
        "role": "Compliance Department Head",
        "goal": "Protect the liquidity reserve and ensure the organization's long-term survival.",
        "backstory": (
            "You lead the Compliance department. Your mandate is to safeguard the "
            "shared reserve. You advocate for conservative withdrawals and raise the "
            "alarm when the reserve approaches dangerous levels."
        ),
    },
    "balanced": {
        "role": "Operations Department Head",
        "goal": "Balance operational funding needs with reserve health.",
        "backstory": (
            "You lead Operations. You need steady funding but understand that the "
            "reserve must remain healthy. You adapt your ask to the current state "
            "of the reserve: more when liquidity is high, less when it is low."
        ),
    },
    "risk_averse": {
        "role": "Risk Department Head",
        "goal": "Prevent a liquidity crisis at all costs.",
        "backstory": (
            "You lead the Risk department. Your primary objective is crisis avoidance. "
            "You almost always advocate for low withdrawals unless the reserve is at "
            "near-full capacity. A liquidity crisis is unacceptable on your watch."
        ),
    },
}

MODERATOR_METADATA = {
    "role": "Treasury Debate Moderator",
    "goal": (
        "Synthesize the arguments from all departments and choose the single withdrawal "
        "level (L, M, or H) that best balances individual needs with collective sustainability."
    ),
    "backstory": (
        "You are the neutral moderator of the treasury committee debate. "
        "You listen to every department's argument, weigh the risk to the shared "
        "reserve, and produce a final binding decision for the whole organization. "
        "Your decision must be one of: L (low withdrawal), M (medium), or H (high)."
    ),
}


class CrewAIDebateCoordination(CoordinationMechanism):
    """
    CrewAI-based debate coordination.

    Each department is modelled as a CrewAI Agent. A sequential Crew runs:
      1. Each department agent produces a short argument defending its proposal.
      2. A moderator agent reads all arguments and outputs the final action.

    Returns the same interface as all other CoordinationMechanism subclasses:
      final_actions (list), cost (dict)

    Requires:
      - crewai package installed  (pip install crewai)
      - OPENROUTER_API_KEY environment variable set
      - Or set OPENAI_API_KEY if using OpenAI directly
    """

    name = "crewai_debate"

    def __init__(
        self,
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.3,
    ):
        self.model = model
        self.temperature = temperature

    def _build_llm(self):
        """Build a CrewAI-compatible LLM object pointing at OpenRouter."""
        from crewai import LLM
        return LLM(
            model=self.model,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            temperature=self.temperature,
        )

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("CrewAIDebateCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("CrewAIDebateCoordination requires departments.")

        from crewai import Agent, Task, Crew, Process

        start_time = time.perf_counter()
        llm = self._build_llm()

        # ------------------------------------------------------------------
        # 1. Build one CrewAI Agent per department
        # ------------------------------------------------------------------
        dept_agents = []
        for dept in departments:
            meta = ROLE_METADATA.get(dept.role, ROLE_METADATA["balanced"])
            agent = Agent(
                role=meta["role"],
                goal=meta["goal"],
                backstory=meta["backstory"],
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )
            dept_agents.append(agent)

        # ------------------------------------------------------------------
        # 2. Build the Moderator Agent
        # ------------------------------------------------------------------
        moderator_agent = Agent(
            role=MODERATOR_METADATA["role"],
            goal=MODERATOR_METADATA["goal"],
            backstory=MODERATOR_METADATA["backstory"],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        # ------------------------------------------------------------------
        # 3. Build one Task per department agent
        # ------------------------------------------------------------------
        reserve_pct = reserve_level / 100.0
        crisis_proximity = "CRITICAL" if reserve_level < 20 else \
                           "DANGEROUS" if reserve_level < 40 else \
                           "MODERATE" if reserve_level < 70 else "SAFE"

        dept_tasks = []
        for dept, agent, proposal in zip(departments, dept_agents, proposals):
            task = Task(
                description=(
                    f"The shared liquidity reserve is currently at {reserve_level:.1f}/100 "
                    f"({reserve_pct*100:.0f}%). Status: {crisis_proximity}.\n\n"
                    f"Your department's ({dept.name}) rule-based policy proposes: {proposal}.\n\n"
                    f"In 2-3 sentences, argue WHY this withdrawal level ({proposal}) is the right "
                    f"choice for the organization given the current reserve state. "
                    f"Be specific about the risk level and your department's rationale."
                ),
                expected_output=(
                    f"A short argument (2-3 sentences) from the {dept.name} supporting "
                    f"withdrawal level {proposal}, with risk reasoning."
                ),
                agent=agent,
            )
            dept_tasks.append(task)

        # ------------------------------------------------------------------
        # 4. Build the Moderator Task (depends on all dept tasks)
        # ------------------------------------------------------------------
        dept_summary = "\n".join(
            f"- {dept.name} ({dept.role}): proposes {proposal}"
            for dept, proposal in zip(departments, proposals)
        )
        dept_names = [dept.name for dept in departments]
        names_json = ", ".join(f'"{n}": "L or M or H"' for n in dept_names)

        moderator_task = Task(
            description=(
                f"You have just heard arguments from all {len(departments)} departments.\n\n"
                f"Summary of proposals:\n{dept_summary}\n\n"
                f"Reserve level: {reserve_level:.1f}/100. Crisis threshold: 5.\n\n"
                f"Read all preceding arguments and allocate a withdrawal level to EACH department "
                f"individually. You may give different departments different levels.\n"
                f"Output ONLY valid JSON in this exact format:\n"
                f"{{{{{names_json}, \"reason\": \"one sentence\"}}}}"
            ),
            expected_output=(
                f"JSON with keys: {', '.join(dept_names)}, reason"
            ),
            agent=moderator_agent,
            context=dept_tasks,
        )

        # ------------------------------------------------------------------
        # 5. Run the Crew sequentially
        # ------------------------------------------------------------------
        crew = Crew(
            agents=dept_agents + [moderator_agent],
            tasks=dept_tasks + [moderator_task],
            process=Process.sequential,
            verbose=False,
        )

        final_action = "M"  # safe default
        rationale = ""

        try:
            from src.llm_client import parse_per_dept_actions, LLMResponse
            result = crew.kickoff()
            raw_output = str(result)

            # Build a fake LLMResponse so we can reuse parse_per_dept_actions
            fake_response = LLMResponse(
                content=raw_output, model=self.model, latency_ms=0
            )
            parsed = parse_per_dept_actions(fake_response, dept_names)
            final_actions = [parsed[name] for name in dept_names]
            rationale = parsed.get("reason", raw_output[:120])

        except Exception as e:
            final_actions = ["M" for _ in proposals]
            rationale = f"crewai_error: {str(e)[:80]}"

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        # final_actions already set per-department by parse_per_dept_actions

        # N dept tasks + 1 moderator task = N+1 LLM calls
        cost = {
            "messages": len(proposals) * 2 + 1,
            "rounds": 2,
            "llm_calls": len(departments) + 1,
            "llm_latency_ms": elapsed_ms,
            "rationale": rationale,
        }

        return final_actions, cost
