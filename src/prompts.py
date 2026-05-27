"""Prompt material shared across the LLM coordination paths."""


# Source of truth for per-role personas (consumed by LLMDepartment and by
# ROLE_METADATA in src/crewai_coordination.py). Wording must stay aligned
# with the rule-based policies in src/agents.py to keep the LLM-vs-rule-based
# comparison apples-to-apples.
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
    "free_rider": (
        "You are an extremely aggressive free-rider. You do NOT care about the "
        "common reserve. Your ONLY goal is to extract maximum value for your "
        "department. You believe others will be conservative enough to "
        "compensate for your aggression. You ALWAYS prefer high withdrawals."
    ),
}

def build_universalization_prompt(reserve_level: float, n_departments: int, reserve_capacity: float = 100.0) -> str:
    """Inject Kantian universalization reasoning based on GovSim paper."""
    # Rough estimate of recovery: 30% of current level * capacity factor
    recovery = 0.3 * reserve_level * (1 - reserve_level / reserve_capacity)
    sustainable_total = recovery
    sustainable_per_dept = sustainable_total / n_departments
    
    if sustainable_per_dept <= 1.5:
        level = "L"
    elif sustainable_per_dept <= 2.5:
        level = "M"
    else:
        level = "H"
        
    return (
        f"Consider the universal impact: if ALL {n_departments} departments chose level '{level}' "
        f"or lower, the reserve would remain stable or grow. "
        f"If everyone chose a higher level, the reserve would shrink. "
        f"Think about what would happen if every department acted as you plan to."
    )


def build_centralized_leader_prompt(
    proposals: list[str],
    departments: list,
    reserve_level: float,
    reserve_capacity: float = 100,
    crisis_threshold: float = 5,
) -> tuple[str, str]:
    """Build (system, user) prompts for the CFO/treasury leader. The leader
    allocates a per-department action, not a single global one."""
    dept_names = [dept.name for dept in departments]
    names_list = ", ".join(f'"{n}"' for n in dept_names)

    system_prompt = f"""You are the CFO/Treasury leader. Your role is to allocate a withdrawal budget level to EACH department individually.

You must consider:
- The overall health of the organization's liquidity reserve
- Each department's role, objective, and current proposal
- The potential for crisis if the reserve is depleted

You may give different departments different levels (e.g. allow Growth to take H while forcing Risk to take L).
This lets you balance individual needs against collective sustainability.

Reply in JSON format with one key per department name, plus a reason:
{{
  {chr(10).join(f'  "{n}": "L or M or H",' for n in dept_names)}
  "reason": "brief explanation"
}}"""

    dept_info = []
    for dept, prop in zip(departments, proposals):
        dept_info.append(f"- {dept.name} ({dept.role}): proposes {prop}")

    user_prompt = f"""Current reserve: {reserve_level:.1f} / {reserve_capacity:.0f}
Crisis threshold: {crisis_threshold:.0f}

Department proposals:
{chr(10).join(dept_info)}

Allocate a withdrawal level (L, M, or H) to EACH department.
Output JSON with keys: {names_list}, "reason"."""

    return system_prompt, user_prompt
