from collections import Counter


class CoordinationMechanism:
    """Base interface for coordination mechanisms."""

    name = "base"

    def reset(self):
        pass

    def decide(self, proposals, reserve_level=None, departments=None):
        raise NotImplementedError


class IndependentCoordination(CoordinationMechanism):
    """No-coordination baseline."""

    name = "independent"

    def decide(self, proposals, reserve_level=None, departments=None):
        cost = {
            "messages": 0,
            "rounds": 0,
        }

        return proposals, cost


class VotingCoordination(CoordinationMechanism):
    """Majority proposal becomes every department's final action."""

    name = "voting"

    def decide(self, proposals, reserve_level=None, departments=None):
        vote_counts = Counter(proposals)

        majority_action = vote_counts.most_common(1)[0][0]

        final_actions = [majority_action for _ in proposals]

        cost = {
            "messages": len(proposals),
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
    """One selected leader sets an upper-bound action for everyone."""

    name = "centralized"

    def __init__(self, leader_index=0, name_suffix=""):
        self.leader_index = leader_index
        self.name = f"centralized{name_suffix or f'_leader_idx{leader_index}'}"

    def decide(self, proposals, reserve_level=None, departments=None):
        leader_proposal = proposals[self.leader_index]
        leader = departments[self.leader_index] if departments else None

        conservative_count = sum(1 for p in proposals if p == "L")

        if conservative_count >= 4:
            leader_action = "L"
        elif conservative_count >= 3 and leader_proposal == "H":
            leader_action = "M"
        else:
            leader_action = leader_proposal

        # The leader action caps aggressive proposals but preserves lower ones.
        action_rank = {"L": 0, "M": 1, "H": 2}
        final_actions = [
            p if action_rank[p] <= action_rank[leader_action] else leader_action
            for p in proposals
        ]

        cost = {
            "messages": len(proposals) + 1,
            "rounds": 1,
            "leader_index": self.leader_index,
            "leader_name": getattr(leader, "name", ""),
            "leader_role": getattr(leader, "role", ""),
        }

        return final_actions, cost


class CentralizedRoleCoordination(CentralizedCoordination):
    """Centralized variant with leader selected by department role."""

    def __init__(self, target_role):
        self.target_role = target_role
        self.leader_index = None
        self.name = f"centralized_{target_role}"

    def supports(self, departments):
        return any(dept.role == self.target_role for dept in departments)

    def _resolve_leader_index(self, departments):
        for i, dept in enumerate(departments):
            if dept.role == self.target_role:
                return i
        raise ValueError(
            f"{self.name} requires a department with role={self.target_role!r}."
        )

    def decide(self, proposals, reserve_level=None, departments=None):
        if departments is None:
            raise ValueError(f"{self.name} requires departments.")
        self.leader_index = self._resolve_leader_index(departments)
        return super().decide(proposals, reserve_level, departments)


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

        if medium_high_risk_count >= 3:
            mode = "all_L"
        elif high_risk_count >= 1 or (majority_action == "H" and reserve_level < 70):
            mode = "cap_H"
        else:
            mode = "own"

        if mode == "all_L":
            final_actions = ["L" for _ in proposals]
        elif mode == "cap_H":
            final_actions = ["M" if p == "H" else p for p in proposals]
        else:
            final_actions = list(proposals)

        cost = {
            "messages": len(proposals) * 3,
            "rounds": 2,
            "justifications": justifications,
        }

        return final_actions, cost


class LLMCentralizedCoordination(CoordinationMechanism):
    """LLM-based centralized coordination: an LLM acts as CFO/treasury
    leader and allocates a per-department action from the proposals."""

    name = "llm_centralized"

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.3,
        crisis_threshold: float = 5,
        memory_window: int = 5,
    ):
        from src.llm_client import get_llm_model

        self.model = model or get_llm_model()
        self.temperature = temperature
        self.crisis_threshold = crisis_threshold
        self.memory_window = memory_window
        self._memory_log = []
        self._step_counter = 0

    def reset(self):
        self._memory_log = []
        self._step_counter = 0

    def _build_memory_blurb(self):
        """Mirrors CrewAIDebateCoordination's memory context so a memory
        advantage doesn't confound the mechanism comparison."""
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
                f"{after}, you decided actions=[{actions}]"
            )
        return (
            "Recent decision history (last "
            f"{len(recent)} steps, oldest first):\n"
            + "\n".join(lines)
            + "\n\nFactor this trajectory in: are recent decisions holding "
            "the reserve steady or is it trending toward crisis?\n\n"
        )

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("LLMCentralizedCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("LLMCentralizedCoordination requires departments.")

        from src.prompts import build_centralized_leader_prompt
        from src.llm_client import call_openrouter, parse_per_dept_actions

        if self._memory_log:
            self._memory_log[-1]["reserve_after"] = reserve_level

        dept_names = [dept.name for dept in departments]

        system_prompt, user_prompt = build_centralized_leader_prompt(
            proposals=proposals,
            departments=departments,
            reserve_level=reserve_level,
            reserve_capacity=100,
            crisis_threshold=self.crisis_threshold,
        )

        memory_blurb = self._build_memory_blurb()
        if memory_blurb:
            user_prompt = memory_blurb + user_prompt

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
        except Exception as e:
            final_actions = ["M" for _ in proposals]
            rationale = f"llm_error: {str(e)[:120]}"

        self._memory_log.append({
            "step": self._step_counter,
            "reserve_before": reserve_level,
            "reserve_after": None,
            "actions": list(final_actions),
        })
        self._step_counter += 1

        cost = {
            "messages": len(proposals) + 1,
            "rounds": 1,
            "llm_calls": 1,
            "llm_latency_ms": response.latency_ms if response else 0,
            "rationale": rationale,
            "model": self.model,
        }

        return final_actions, cost


class FreeNegotiationCoordination(CoordinationMechanism):
    """
    GovSim-style free negotiation.
    
    Ignores initial proposals. Instead, runs a chat round where each
    department speaks in turn. Afterwards, each department decides its
    final action in light of the transcript.
    """
    name = "free_negotiation"

    def __init__(self, chat_rounds=1):
        self.chat_rounds = chat_rounds

    def decide(self, proposals, reserve_level=None, departments=None):
        if reserve_level is None:
            raise ValueError("FreeNegotiationCoordination requires reserve_level.")
        if departments is None:
            raise ValueError("FreeNegotiationCoordination requires departments.")

        transcript = ""
        llm_latency = 0.0

        for r in range(self.chat_rounds):
            for dept in departments:
                if hasattr(dept, "chat"):
                    msg = dept.chat(reserve_level, transcript)
                    transcript += f"{dept.name} ({dept.role}): {msg}\n"
                    llm_latency += getattr(dept, "last_llm_latency_ms", 0.0)
                else:
                    transcript += f"{dept.name} ({dept.role}): (Cannot chat, rule-based)\n"

        final_actions = []
        for dept in departments:
            if hasattr(dept, "propose_action") and 'context' in dept.propose_action.__code__.co_varnames:
                action = dept.propose_action(reserve_level, context=transcript)
                llm_latency += getattr(dept, "last_llm_latency_ms", 0.0)
            else:
                action = dept.propose_action(reserve_level)
            final_actions.append(action)

        cost = {
            "messages": len(departments) * self.chat_rounds + len(departments),
            "rounds": self.chat_rounds + 1,
            "llm_calls": len(departments) * self.chat_rounds + len(departments),
            "llm_latency_ms": llm_latency,
            "rationale": transcript,
            "model": getattr(departments[0], "model", "rule-based"),
        }

        return final_actions, cost
