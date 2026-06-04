"""End-to-end smoke test for the LLM coordination mechanisms.

What to look for in the output:
- Every step should print a sensible rationale (NOT "crewai_error: ..." and
  NOT "parse_failed").
- final_actions should vary across steps and across departments (a stuck
  parser returns ["M", "M", "M", "M", "M"] every step).
"""

import os
import sys

from src.llm_client import get_llm_model
from src.environment import LiquidityReserveEnvironment
from src.llm_agents import LLMDepartment
from src.coordination import LLMCentralizedCoordination
from src.crewai_coordination import CrewAIDebateCoordination
from src.compositions import make_compositions
from src.simulation import run_simulation


MODEL = get_llm_model()
TEMPERATURE = 0.3
MAX_STEPS = 1


def make_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=0.05,
        shock_probability=0.05,
        shock_magnitude=10.0,
    )


def short(text, n=90):
    if not text:
        return "<empty>"
    text = " ".join(str(text).split())
    text = text.encode("ascii", errors="replace").decode("ascii")
    return text[:n] + ("..." if len(text) > n else "")


def is_parse_failure(rationale):
    return (
        not rationale
        or rationale.startswith("llm_error")
        or rationale.startswith("crewai_error:")
        or "parse_failed" in rationale
        or "global_fallback" in rationale
    )


def smoke_run(mechanism):
    print(f"\n{'=' * 78}")
    print(f"  {mechanism.name}  (model={MODEL})")
    print('=' * 78)

    compositions = make_compositions(
        LLMDepartment, model=MODEL, temperature=TEMPERATURE,
    )
    departments = compositions["standard"]()

    history, elapsed = run_simulation(
        environment=make_env(),
        departments=departments,
        coordination=mechanism,
        max_steps=MAX_STEPS,
    )

    parse_failures = 0
    for step in history:
        actions = ",".join(step["final_actions"])
        rationale = step.get("rationale", "<no rationale>")
        failed = is_parse_failure(rationale)
        if failed:
            parse_failures += 1
        marker = "X " if failed else "OK"
        print(
            f"  {marker} t={step['t']:2d}  R={step['new_reserve']:5.1f}  "
            f"actions=[{actions}]  rationale={short(rationale)}"
        )

    n = len(history)
    print(f"\n  steps={n}  parse_failures={parse_failures}/{n}  "
          f"wall={elapsed:.1f}s")
    return parse_failures, n


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY before running.", file=sys.stderr)
        sys.exit(1)

    mechanisms = [
        LLMCentralizedCoordination(model=MODEL, temperature=TEMPERATURE),
        CrewAIDebateCoordination(
            model=MODEL,
            temperature=TEMPERATURE,
            allow_delegation=False,
        ),
    ]

    results = []
    for mech in mechanisms:
        try:
            failures, total = smoke_run(mech)
            results.append((mech.name, failures, total, None))
        except Exception as e:
            results.append((mech.name, None, None, repr(e)))
            print(f"\n  CRASH: {e!r}", file=sys.stderr)

    print(f"\n{'=' * 78}")
    print("  Summary")
    print('=' * 78)
    for name, failures, total, err in results:
        if err:
            print(f"  {name:24s}  CRASHED: {short(err, 100)}")
        else:
            ok = total - failures
            print(f"  {name:24s}  {ok}/{total} steps parsed cleanly")


if __name__ == "__main__":
    main()
