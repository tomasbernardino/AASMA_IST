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


class CentralizedCoordination(CoordinationMechanism):
    """
    Centralized mechanism.
    One CFO/treasury leader decides for everyone.
    """

    name = "centralized"

    def __init__(self, leader_index=0):
        self.leader_index = leader_index

    def decide(self, proposals, reserve_level=None, departments=None):
        leader_action = proposals[self.leader_index]

        final_actions = [leader_action for _ in proposals]

        cost = {
            "messages": len(proposals) + 1,
            # departments send proposals, CFO/treasury sends final decision
            "rounds": 1,
        }

        return final_actions, cost


class DebateCoordination(CoordinationMechanism):
    """
    Simplified rule-based debate.
    """

    name = "debate"

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("DebateCoordination requires reserve_level.")

        # Count initial preferences.
        vote_counts = Counter(proposals)
        
        majority_action = vote_counts.most_common(1)[0][0]

        # Debate rule:
        # If liquidity is low, reserve-protection arguments dominate.
        if reserve_level < 40:
            final_action = "L"

        # If liquidity is moderately low, avoid high withdrawals.
        elif reserve_level < 70 and majority_action == "H":
            final_action = "M"

        # Otherwise, accept the majority proposal.
        else:
            final_action = majority_action

        final_actions = [final_action for _ in proposals]

        cost = {
            "messages": len(proposals) * 2,
            # proposal + critique/argument per department
            "rounds": 2,
        }

        return final_actions, cost
