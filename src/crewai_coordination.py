"""CrewAI-based debate coordination.

This is intentionally the ONLY mechanism that uses CrewAI, because debate
is the only mechanism that genuinely has N interacting agents with distinct
roles exactly what CrewAI was designed to orchestrate.
"""

import os
import time

from dotenv import load_dotenv

from src.llm_client import LLMResponse, get_llm_model, parse_per_dept_actions
from src.coordination import CoordinationMechanism
from src.prompts import ROLE_PROMPTS


load_dotenv()


# `backstory` is shared with LLMDepartment via ROLE_PROMPTS so the persona
# `role` and `goal` stay local
# because CrewAI's Agent constructor takes them as separate fields.
ROLE_METADATA = {
    "profit": {
        "role": "Growth & Trading Department Head",
        "goal": "Maximize the department's withdrawal to fund aggressive investment and growth.",
        "backstory": ROLE_PROMPTS["profit"],
    },
    "sustainability": {
        "role": "Compliance Department Head",
        "goal": "Protect the liquidity reserve and ensure the organization's long-term survival.",
        "backstory": ROLE_PROMPTS["sustainability"],
    },
    "balanced": {
        "role": "Operations Department Head",
        "goal": "Balance operational funding needs with reserve health.",
        "backstory": ROLE_PROMPTS["balanced"],
    },
    "risk_averse": {
        "role": "Risk Department Head",
        "goal": "Prevent a liquidity crisis at all costs.",
        "backstory": ROLE_PROMPTS["risk_averse"],
    },
    "free_rider": {
        "role": "Saboteur Department Head",
        "goal": "Extract the maximum possible withdrawal for your department regardless of the shared reserve.",
        "backstory": ROLE_PROMPTS["free_rider"],
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
    """Two-round department debate adjudicated by a moderator agent. Each
    department is one CrewAI Agent; the moderator allocates a per-department
    action from the synthesised arguments."""

    name = "crewai_debate"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        memory_window: int = 5,
        allow_delegation: bool = True,
    ):
        self.model = model or get_llm_model()
        self.temperature = temperature
        self.memory_window = memory_window
        self.allow_delegation = allow_delegation
        self._llm = None
        self._memory_log = []
        self._step_counter = 0

    def reset(self):
        self._memory_log = []
        self._step_counter = 0

    def _get_llm(self):
        if self._llm is None:
            from crewai import LLM

            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("CrewAIDebateCoordination requires OPENROUTER_API_KEY.")

            crewai_model = (
                self.model
                if self.model.startswith("openrouter/")
                else f"openrouter/{self.model}"
            )
            self._llm = LLM(
                model=crewai_model,
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=self.temperature,
                timeout=45,
                max_retries=0,
            )
        return self._llm

    def _build_memory_context(self):
        """Textual summary of recent debate outcomes. Without this, agents
        treat every step in isolation and can't track whether the reserve
        is drifting toward crisis."""
        if not self._memory_log:
            return ""
        recent = self._memory_log[-self.memory_window:]
        lines = []
        for entry in recent:
            actions = ",".join(entry["actions"])
            after = (
                f"{entry['reserve_after']:.1f}"
                if entry["reserve_after"] is not None
                else "?"
            )
            lines.append(
                f"  Step {entry['step']}: reserve {entry['reserve_before']:.1f} -> "
                f"{after}, decided actions=[{actions}]"
            )
        return (
            "Recent debate history (last "
            f"{len(recent)} steps, oldest first):\n"
            + "\n".join(lines)
            + "\n\nFactor this trajectory into your reasoning: do recent "
            "decisions appear to be working, or is the reserve drifting "
            "toward crisis?\n\n"
        )

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("CrewAIDebateCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("CrewAIDebateCoordination requires departments.")

        from crewai import Agent, Task, Crew, Process

        start_time = time.perf_counter()
        llm = self._get_llm()

        if self._memory_log:
            self._memory_log[-1]["reserve_after"] = reserve_level

        memory_blurb = self._build_memory_context()

        # Delegation is disabled in production runs so LLM-call counts stay comparable.
        dept_agents = []
        for dept in departments:
            meta = ROLE_METADATA.get(dept.role, ROLE_METADATA["balanced"])
            agent = Agent(
                role=meta["role"],
                goal=meta["goal"],
                backstory=meta["backstory"],
                llm=llm,
                memory=False,
                max_iter=3,
                verbose=False,
                allow_delegation=self.allow_delegation,
            )
            dept_agents.append(agent)

        moderator_agent = Agent(
            role=MODERATOR_METADATA["role"],
            goal=MODERATOR_METADATA["goal"],
            backstory=MODERATOR_METADATA["backstory"],
            llm=llm,
            memory=False,
            max_iter=3,
            verbose=False,
            allow_delegation=self.allow_delegation,
        )

        reserve_pct = reserve_level / 100.0
        crisis_proximity = (
            "CRITICAL" if reserve_level < 20 else
            "DANGEROUS" if reserve_level < 40 else
            "MODERATE" if reserve_level < 70 else "SAFE"
        )
        crew_inputs = {
            "memory_context": memory_blurb,
            "reserve_level": f"{reserve_level:.1f}",
            "reserve_percent": f"{reserve_pct * 100:.0f}",
            "crisis_proximity": crisis_proximity,
            "crisis_threshold": "5",
            "department_count": str(len(departments)),
        }

        opening_tasks = []
        for dept, agent, proposal in zip(departments, dept_agents, proposals):
            task = Task(
                description=(
                    "{memory_context}"
                    f"OPENING ARGUMENT (round 1 of 2).\n"
                    "Reserve: {reserve_level}/100 ({reserve_percent}%). "
                    "Status: {crisis_proximity}.\n\n"
                    f"Your department ({dept.name}) proposes withdrawal level {proposal}.\n\n"
                    f"In 2-3 sentences, argue WHY {proposal} is the right choice for the "
                    f"organization given the current reserve state. Be specific about the "
                    f"risk and your department's mandate.\n\n"
                    f"For opening arguments, just state your position do NOT delegate or "
                    f"consult other departments. They will hear you in due course."
                ),
                expected_output=(
                    f"A 2-3 sentence opening argument from {dept.name} defending {proposal}."
                ),
                agent=agent,
            )
            opening_tasks.append(task)

        rebuttal_tasks = []
        for dept, agent, proposal in zip(departments, dept_agents, proposals):
            task = Task(
                description=(
                    f"REBUTTAL (round 2 of 2).\n"
                    "You have now heard the opening arguments from all {department_count} "
                    f"departments (provided as context).\n\n"
                    f"Your department ({dept.name}) opened with withdrawal level {proposal}.\n\n"
                    f"BEFORE writing your rebuttal, you MAY consult ONE specific department "
                    f"by delegating a single clarifying question to them (e.g. ask Risk "
                    f"Department Head what volatility threshold they consider unacceptable). "
                    f"Use this only if the answer would actually change your "
                    f"position. Do not delegate just to fill space.\n\n"
                    f"Then, in 2-3 sentences: (a) acknowledge the strongest counter-argument "
                    f"you heard, and (b) either defend {proposal} or update to a different "
                    f"level (L, M, or H). End your response with one of the literal tokens "
                    f"FINAL=L, FINAL=M, or FINAL=H on its own line."
                ),
                expected_output=(
                    f"A 2-3 sentence rebuttal from {dept.name}, ending with "
                    f"FINAL=L, FINAL=M, or FINAL=H."
                ),
                agent=agent,
                context=opening_tasks,
            )
            rebuttal_tasks.append(task)

        dept_summary = "\n".join(
            f"- {dept.name} ({dept.role}): originally proposed {proposal}"
            for dept, proposal in zip(departments, proposals)
        )
        dept_names = [dept.name for dept in departments]
        json_lines = ",\n  ".join(f'"{n}": "L or M or H"' for n in dept_names)
        json_template = "{{\n  " + json_lines + ',\n  "reason": "one sentence"\n}}'

        moderator_task = Task(
            description=(
                "{memory_context}"
                "You have observed two full rounds of debate among "
                "{department_count} departments (opening arguments + rebuttals, "
                f"provided as context).\n\n"
                f"Original proposals:\n{dept_summary}\n\n"
                "Reserve level: {reserve_level}/100. "
                "Crisis threshold: {crisis_threshold}.\n\n"
                f"You MAY delegate a single clarifying question to one specific department "
                f"if a critical point is still unclear from their arguments.\n\n"
                f"Then synthesize the arguments and rebuttals and allocate a final "
                f"withdrawal level to EACH department individually. You may give "
                f"different departments different levels.\n\n"
                f"Output ONLY valid JSON in exactly this shape:\n"
                f"{json_template}"
            ),
            expected_output=(
                f"Valid JSON with keys: {', '.join(dept_names)}, reason."
            ),
            agent=moderator_agent,
            context=opening_tasks + rebuttal_tasks,
        )

        crew = Crew(
            agents=dept_agents + [moderator_agent],
            tasks=opening_tasks + rebuttal_tasks + [moderator_task],
            process=Process.sequential,
            verbose=False,
        )

        try:
            result = crew.kickoff(inputs=crew_inputs)
            raw_output = getattr(result, "raw", str(result))

            fake_response = LLMResponse(
                content=raw_output, model=self.model, latency_ms=0,
            )
            parsed = parse_per_dept_actions(fake_response, dept_names)
            final_actions = [parsed[name] for name in dept_names]
            rationale = parsed.get("reason", raw_output[:120])
            if rationale == "parse_failed":
                rationale = f"parse_failed: {raw_output[:200]}"
        except Exception as e:
            final_actions = ["M" for _ in proposals]
            rationale = f"crewai_error: {str(e)[:240]}"

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self._memory_log.append({
            "step": self._step_counter,
            "reserve_before": reserve_level,
            "reserve_after": None,
            "actions": list(final_actions),
        })
        self._step_counter += 1

        cost = {
            "messages": 2 * len(proposals) + 1,
            "rounds": 3,
            "llm_calls": 2 * len(departments) + 1,
            "llm_latency_ms": elapsed_ms,
            "rationale": rationale,
            "model": self.model,
        }

        return final_actions, cost
