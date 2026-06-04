import os
import sys

from src.environment import LiquidityReserveEnvironment
from src.coordination import (
    AdaptiveVotingCoordination,
    CentralizedRoleCoordination,
    IndependentCoordination,
    LLMCentralizedCoordination,
    StructuredDebateCoordination,
    VotingCoordination,
)
from src.crewai_coordination import CrewAIDebateCoordination



DEFAULT_TEMPERATURE = 0.3
DEFAULT_RECOVERY_NOISE_STD = 0.05
DEFAULT_SHOCK_PROBABILITY = 0.05
DEFAULT_SHOCK_MAGNITUDE = 10.0


def make_default_env():
    return LiquidityReserveEnvironment(
        recovery_noise_std=DEFAULT_RECOVERY_NOISE_STD,
        shock_probability=DEFAULT_SHOCK_PROBABILITY,
        shock_magnitude=DEFAULT_SHOCK_MAGNITUDE,
    )


def build_rule_based_mechanisms():
    return [
        IndependentCoordination(),
        VotingCoordination(),
        AdaptiveVotingCoordination(),
        CentralizedRoleCoordination("profit"),
        CentralizedRoleCoordination("sustainability"),
        CentralizedRoleCoordination("risk_averse"),
        StructuredDebateCoordination(),
    ]


def build_llm_mechanisms(model, temperature=DEFAULT_TEMPERATURE):
    return [
        IndependentCoordination(),
        CentralizedRoleCoordination("profit"),
        CentralizedRoleCoordination("sustainability"),
        CentralizedRoleCoordination("risk_averse"),
        StructuredDebateCoordination(),
        LLMCentralizedCoordination(model=model, temperature=temperature),
        CrewAIDebateCoordination(
            model=model,
            temperature=temperature,
            allow_delegation=False,
        ),
    ]


def require_openrouter_key():
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: set OPENROUTER_API_KEY before running.", file=sys.stderr)
        sys.exit(1)


def model_slug(model_name):
    return model_name.replace("/", "_").replace(":", "-")
