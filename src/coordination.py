# src/coordination.py

from collections import Counter


class CoordinationMechanism:
    """
    Base class for coordination mechanisms.

    Each mechanism receives:
        proposals: list of proposed spending policies from departments
        reserve_level: current liquidity reserve
        departments: list of departments

    It returns:
        final_actions: list of final policies, one per department
        cost: coordination cost information
    """

    name = "base"

    def decide(self, proposals, reserve_level=None, departments=None):
        raise NotImplementedError


class IndependentCoordination(CoordinationMechanism):
    """
    Baseline mechanism.

    No coordination happens.
    Each department follows its own proposed spending policy.
    """

    name = "independent"

    def decide(self, proposals, reserve_level=None, departments=None):
        cost = {
            "messages": 0,
            "rounds": 0,
        }

        return proposals, cost


class VotingCoordination(CoordinationMechanism):
    """
    Voting mechanism.

    Departments vote by proposing spending policies.
    The majority policy becomes the final policy for everyone.

    Example:
        proposals = ["H", "H", "L", "M"]
        final policy = "H"
    """

    name = "voting"

    def decide(self, proposals, reserve_level=None, departments=None):
        vote_counts = Counter(proposals)

        # Most common proposal wins.
        majority_action = vote_counts.most_common(1)[0][0]

        final_actions = [majority_action for _ in proposals]

        cost = {
            "messages": len(proposals),  # each department sends one proposal
            "rounds": 1,
        }

        return final_actions, cost


class AdaptiveVotingCoordination(CoordinationMechanism):
    """
    Reserve-weighted voting.

    Like VotingCoordination but votes are re-weighted based on the reserve
    level. When the reserve is low, conservative (L) votes carry more weight,
    preventing always-aggressive agents from structurally dominating the vote
    at healthy reserves.

    Weight schedule:
      R >= 40 (safe/caution): L=1, M=1, H=1  (standard majority)
      20 <= R < 40 (danger):  L=2, M=1, H=1  (L votes count double)
      R < 20  (critical):     L=3, M=1, H=0  (H votes disqualified)

    Tie-break favours the more conservative option.
    """

    name = "adaptive_voting"

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("AdaptiveVotingCoordination requires reserve_level.")

        if reserve_level < 20:
            weights = {"L": 3, "M": 1, "H": 0}
        elif reserve_level < 40:
            weights = {"L": 2, "M": 1, "H": 1}
        else:
            weights = {"L": 1, "M": 1, "H": 1}

        vote_counts = Counter(proposals)
        weighted = {
            a: vote_counts.get(a, 0) * weights[a]
            for a in ["L", "M", "H"]
        }

        # Tie-break: prefer more conservative action (L > M > H)
        conservatism_rank = {"L": 2, "M": 1, "H": 0}
        majority_action = max(["L", "M", "H"],
                              key=lambda a: (weighted[a], conservatism_rank[a]))

        final_actions = [majority_action for _ in proposals]

        cost = {
            "messages": len(proposals),
            "rounds": 1,
        }

        return final_actions, cost


class CentralizedCoordination(CoordinationMechanism):
    """
    Centralized mechanism.
    One CFO/treasury leader decides for everyone.
    """

    name = "centralized"

    def __init__(self, leader_index=0, name_suffix=""):
        self.leader_index = leader_index
        self.name = f"centralized{name_suffix}"

    def decide(self, proposals, reserve_level=None, departments=None):
        leader_proposal = proposals[self.leader_index]

        # Leader observes all proposals and adjusts based on group signals.
        conservative_count = sum(1 for p in proposals if p == "L")

        if conservative_count >= 4:
            leader_action = "L"
        elif conservative_count >= 3 and leader_proposal == "H":
            leader_action = "M"
        else:
            leader_action = leader_proposal

        # Per-department allocation:
        # The leader's decision acts as an UPPER BOUND for each department.
        # Conservative depts that proposed less than the leader keep their own
        # (lower) proposal — the leader respects their mandate.
        # Aggressive depts that proposed more than the leader are capped.
        action_rank = {"L": 0, "M": 1, "H": 2}
        final_actions = [
            p if action_rank[p] <= action_rank[leader_action] else leader_action
            for p in proposals
        ]

        cost = {
            "messages": len(proposals) + 1,
            "rounds": 1,
        }

        return final_actions, cost





class StructuredDebateCoordination(CoordinationMechanism):
    """
    Structured rule-based debate with explicit aggregation rules.

    Per-step procedure:
    1. Each department proposes {L, M, H}
    2. Each department provides risk estimate and justification
    3. Coordinator applies aggregation rules in order:
       - If any dept estimates risk=1.0 and proposes H -> override to M
       - If >=3 departments estimate risk >= 0.5 -> override to L
       - If majority proposes H and reserve < 70 -> override to M
       - Otherwise -> use majority action
    """

    name = "structured_debate"

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("StructuredDebateCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("StructuredDebateCoordination requires departments.")

        justifications = [
            department.justify_action(proposal, reserve_level)
            for department, proposal in zip(departments, proposals)
        ]

        majority_action = Counter(proposals).most_common(1)[0][0]

        high_risk_count = sum(
            1 for j in justifications
            if j["risk_estimate"] == 1.0 and j["proposed"] == "H"
        )
        medium_high_risk_count = sum(
            1 for j in justifications
            if j["risk_estimate"] >= 0.5 and j["proposed"] in ["M", "H"]
        )

        # Determine coordination mode from priority rule chain.
        # Modes apply per-department, not as a single global override:
        #   "all_L"  — crisis: everyone gets L
        #   "cap_H"  — caution: H proposals become M, L and M stay as-is
        #   "own"    — safe: each dept executes its own proposal
        if medium_high_risk_count >= 3:
            mode = "all_L"
        elif high_risk_count >= 1 or (majority_action == "H" and reserve_level < 70):
            mode = "cap_H"
        else:
            mode = "own"

        if mode == "all_L":
            final_actions = ["L" for _ in proposals]
        elif mode == "cap_H":
            # Cap aggressive proposals: H → M, leave L and M intact
            final_actions = ["M" if p == "H" else p for p in proposals]
        else:
            # Each dept executes its own proposal
            final_actions = list(proposals)

        cost = {
            "messages": len(proposals) * 3,
            "rounds": 2,
            "justifications": justifications,
        }

        return final_actions, cost


class LLMCentralizedCoordination(CoordinationMechanism):
    """
    LLM-based centralized coordination.
    
    Departments submit proposals, an LLM acts as CFO/treasury leader
    and chooses the final action with reasoning.
    """

    name = "llm_centralized"

    def __init__(
        self,
        model: str = "openai/gpt-4o-mini",
        temperature: float = 0.3,
        crisis_threshold: float = 5,
    ):
        self.model = model
        self.temperature = temperature
        self.crisis_threshold = crisis_threshold

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("LLMCentralizedCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("LLMCentralizedCoordination requires departments.")

        from src.prompts import build_centralized_leader_prompt
        from src.llm_client import call_openrouter, parse_per_dept_actions

        dept_names = [dept.name for dept in departments]

        system_prompt, user_prompt = build_centralized_leader_prompt(
            proposals=proposals,
            departments=departments,
            reserve_level=reserve_level,
            reserve_capacity=100,
            crisis_threshold=self.crisis_threshold,
        )

        response = None
        rationale = "llm_error"
        try:
            response = call_openrouter(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                temperature=self.temperature,
                max_tokens=200,
            )
            parsed = parse_per_dept_actions(response, dept_names)
            final_actions = [parsed[name] for name in dept_names]
            rationale = parsed.get("reason", "")
        except Exception:
            final_actions = ["M" for _ in proposals]

        cost = {
            "messages": len(proposals) + 1,
            "rounds": 1,
            "llm_calls": 1,
            "llm_latency_ms": response.latency_ms if response else 0,
            "rationale": rationale,
        }

        return final_actions, cost



