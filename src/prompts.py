DEPARTMENT_ROLE_PROMPTS = {
    "profit": """You are the Growth Department. Your priority is aggressive investment and maximizing returns. You prefer high withdrawals when liquidity is available, and only reduce spending when the reserve is dangerously low.

When deciding, consider:
- Your department's growth targets require capital
- High withdrawals advance your objectives
- Only retreat to lower withdrawals when crisis is imminent""",
    
    "sustainability": """You are the Compliance Department. Your priority is protecting the reserve and ensuring long-term sustainability. You strongly prefer low withdrawals unless the reserve is very healthy.

When deciding, consider:
- Reserve protection is your mandate
- Sustainability requires conservative spending
- Only allow higher withdrawals when reserve is well above crisis threshold""",
    
    "balanced": """You are the Operations Department. You balance funding needs with reserve stability. You adapt your spending to the current state of the reserve, withdrawing more when liquidity is high and less when it is low.

When deciding, consider:
- Your operations need funding but must adapt to circumstances
- Increase withdrawals when reserve is healthy
- Decrease withdrawals as reserve approaches danger levels""",
    
    "risk_averse": """You are the Risk Department. You strongly avoid liquidity crisis. You almost always prefer low withdrawals unless the reserve is at near-full capacity.

When deciding, consider:
- Preventing crisis is your primary objective
- Err on the side of caution
- Only withdraw more when reserve is clearly safe""",
}


def build_department_prompt(
    role: str,
    reserve_level: float,
    reserve_capacity: float = 100,
    crisis_threshold: float = 5,
    history: list = None,
) -> tuple[str, str]:
    """
    Build system and user prompts for a department.
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = DEPARTMENT_ROLE_PROMPTS.get(role, DEPARTMENT_ROLE_PROMPTS["balanced"])
    
    history_text = ""
    if history:
        recent = history[-5:]
        lines = []
        for entry in recent:
            lines.append(
                f"  Step {entry['step']}: reserve={entry['reserve']:.1f}, "
                f"you chose={entry['action']}, reward={entry['reward']:.1f}"
            )
        history_text = "\nYour recent history:\n" + "\n".join(lines)
    
    user_prompt = f"""The shared liquidity reserve is currently at {reserve_level:.1f} out of {reserve_capacity:.0f} maximum. The crisis threshold is {crisis_threshold:.0f}.{history_text}

Choose your withdrawal level for this step.
Reply with exactly one letter: L (low=1), M (medium=2), or H (high=3).
Do not include any other text."""
    
    return system_prompt, user_prompt


def build_centralized_leader_prompt(
    proposals: list[str],
    departments: list,
    reserve_level: float,
    reserve_capacity: float = 100,
    crisis_threshold: float = 5,
) -> tuple[str, str]:
    """
    Build prompts for a centralized LLM leader (CFO/treasury role).
    The leader allocates a per-department action, not a single global one.

    Returns:
        (system_prompt, user_prompt)
    """
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


def build_debate_moderator_prompt(
    proposals: list[str],
    justifications: list[dict],
    departments: list,
    reserve_level: float,
    reserve_capacity: float = 100,
    crisis_threshold: float = 5,
) -> tuple[str, str]:
    """
    Build prompts for LLM debate moderator.
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = """You are the debate moderator. Your role is to facilitate discussion among departments and choose the final group action.

You have received:
- Each department's proposed action (L, M, or H)
- Each department's justification for their proposal
- The current state of the shared reserve

Your task is to synthesize the arguments and choose the action that best balances:
- Individual department needs
- Collective sustainability
- Crisis prevention

Reply in JSON format: {"action": "L/M/H", "reason": "summary of key arguments"}"""
    
    arg_lines = []
    for dept, prop, just in zip(departments, proposals, justifications):
        arg_lines.append(
            f"- {dept.name} ({dept.role}): proposes {prop}, "
            f"risk={just.get('risk_estimate', '?')}, "
            f"justification={just.get('justification_type', '?')}"
        )
    
    user_prompt = f"""Current reserve: {reserve_level:.1f} / {reserve_capacity:.0f}
Crisis threshold: {crisis_threshold:.0f}

Department arguments:
{chr(10).join(arg_lines)}

Synthesize these arguments and choose the final withdrawal level.
Output: {{"action": "L", "M", or "H", "reason": "key arguments considered"}}"""
    
    return system_prompt, user_prompt