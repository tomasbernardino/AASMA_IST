# Coordination Mechanisms — Final Reference
### Accurate as of current codebase

---

## Setup

At every step, 5 departments observe the reserve `R` and each proposes a withdrawal level:

| Dept | Role | Policy | Utility |
|---|---|---|---|
| Growth | profit | H always; M if R<20 | U = withdrawal |
| Trading | profit | H always; M if R<20 | U = withdrawal |
| Compliance | sustainability | L if R<70; else M | U = w − 5·crisis_risk |
| Operations | balanced | L if R<40; H if R>80; else M | U = w − 3·reserve_deficit |
| Risk | risk_averse | L if R<90; else M | U = w − 2·volatility |

Withdrawals: `L=1, M=2, H=3`. Total per step: min=5 (all L), max=15 (all H). Reserve update per step:
```
R_{t+1} = R_t + 0.3·R_t·(1 − R_t/100) − Σ withdrawals
```
Crisis if `R ≤ 5`. Each mechanism receives `proposals`, `reserve_level`, `departments` and returns `final_actions` (one per dept) and `cost`.

**Proposal snapshots:**
- At R=80 (healthy): proposals = `[H, H, L, H, L]` → strong withdrawal pressure, total = 11, net drain ≈ −6.2/step
- At R=30 (danger): proposals = `[M, M, L, L, L]` → natural convergence toward conservation, total = 7

---

## Action Models

| Mechanism | Action model | Who decides |
|---|---|---|
| Independent | **Per-dept** — own proposal | Each dept itself |
| Voting | **Global** — one policy for all | Majority arithmetic |
| AdaptiveVoting | **Global** — one policy for all | Reserve-weighted majority |
| Centralized (×3) | **Per-dept** — leader caps aggressors | Informed leader |
| StructuredDebate | **Per-dept** — mode applied per proposal | Priority rule chain |
| LLMCentralized | **Per-dept** — individual allocation | LLM CFO |
| CrewAIDebate | **Per-dept** — individual allocation | CrewAI Moderator Agent |

---

## Mechanism 1 — Independent

**Concept:** The Tragedy of the Commons baseline. No governance, no communication. Each department acts entirely on its own.

**Action model:** Per-dept.

**Logic:** Each dept's proposal is its own final action. No aggregation happens.

**At R=80:** `final = [H, H, L, H, L]` → total withdrawal = 10. Net drain ≈ 5.2/step → collapse expected within ~20 steps.

```python
def decide(self, proposals, ...):
    return proposals, {"messages": 0, "rounds": 0}
```

**Cost:** 0 messages · 0 rounds · 0 LLM calls.

---

## Mechanism 2 — Voting

**Concept:** Democratic majority rule. All departments vote; the most common proposal becomes a binding collective policy that everyone follows equally.

**Action model:** Global — voting produces a *policy*, not an *allocation*. Everyone follows the same rule.

**Logic:**
1. Count votes: `Counter(["H","H","L","M","L"]) → {H:2, L:2, M:1}`
2. Most common wins (tie-break: first proposal encountered among tied actions,
   matching Python `Counter.most_common`)
3. All 5 departments execute the winner

**Composition note:** With 2 profit agents always voting H, and Operations voting H when R>80, the vote is structurally 3-H vs 2-L at healthy reserves. Results may reflect composition as much as mechanism.

```python
def decide(self, proposals, ...):
    majority_action = Counter(proposals).most_common(1)[0][0]
    return [majority_action for _ in proposals], {"messages": 5, "rounds": 1}
```

**Cost:** 5 messages · 1 round · 0 LLM calls.

---

## Mechanism 3 — AdaptiveVoting

**Concept:** Reserve-weighted democratic voting. Conservative votes carry more weight when reserves are endangered, preventing structurally aggressive compositions from dominating at healthy reserves.

**Action model:** Global — still produces a single collective policy.

**Logic:**
1. Determine weights from reserve level:
   - R ≥ 40: `{L:1, M:1, H:1}` — standard majority
   - 20 ≤ R < 40: `{L:2, M:1, H:1}` — L votes double
   - R < 20: `{L:3, M:1, H:0}` — H votes disqualified
2. Multiply each action's count by its weight
3. Winner = highest weighted total; ties broken toward more conservative option

**Example at R=30 with `[H,H,L,L,L]`:**
Weighted: H=1×2=2, L=3×2=6 → winner: **L** ✅ (plain voting would give L=3 > H=2 → same here, but at R=70 with aggressive comp the difference matters more)

```python
if reserve_level < 20:    weights = {"L": 3, "M": 1, "H": 0}
elif reserve_level < 40:  weights = {"L": 2, "M": 1, "H": 1}
else:                     weights = {"L": 1, "M": 1, "H": 1}

weighted = {a: Counter(proposals).get(a, 0) * weights[a] for a in ["L","M","H"]}
conservatism_rank = {"L": 2, "M": 1, "H": 0}
winner = max(["L","M","H"], key=lambda a: (weighted[a], conservatism_rank[a]))
return [winner for _ in proposals], {"messages": 5, "rounds": 1}
```

**Cost:** 5 messages · 1 round · 0 LLM calls.

---

## Mechanism 4 — Centralized (3 variants)

**Concept:** Authority-based governance. One leader reviews all proposals, forms an informed decision, then acts as an **upper bound** for each department — aggressive departments are capped, conservative departments keep their own (lower) proposals.

**Action model:** Per-dept.

**Three role-selected leader variants:**
- `centralized_profit` — first department whose role is `profit`
- `centralized_sustainability` — first department whose role is `sustainability`
- `centralized_risk_averse` — first department whose role is `risk_averse`

If a composition lacks the requested role, that mechanism/composition row is
skipped rather than silently substituting another role. Result CSVs include
`leader_index`, `leader_name`, and `leader_role` columns for centralized rows
so the actual leader identity is explicit.

**Logic:**
1. Leader forms its own proposal from its role policy
2. Count how many others proposed L (conservative alarm):
   - `≥ 4` → leader steps to L (near-unanimous alarm)
   - `≥ 3 AND leader proposed H` → leader steps to M
   - Otherwise → leader keeps own proposal
3. **Per-dept allocation:** leader's decision = cap. Each dept gets `min(their proposal, leader's decision)` in rank terms

**Example — profit leader at R=30:**
Leader proposes H. Conservative count = 3 (Compliance=L, Operations=L, Risk=L). Step 2: H→M.
`proposals=[H,H,L,L,L]` → cap at M: `final=[M, M, L, L, L]`
Growth/Trading capped at M. Compliance/Operations/Risk keep their L. ✅

**Example — sustainability leader at R=80:**
Leader proposes M (sustainability policy). No alarm. Cap at M:
`proposals=[H,H,L,H,L]` → `final=[M, M, L, M, L]`

```python
action_rank = {"L": 0, "M": 1, "H": 2}
# ... compute leader_action with alarm override ...
final_actions = [
    p if action_rank[p] <= action_rank[leader_action] else leader_action
    for p in proposals
]
```

**Cost:** 6 messages · 1 round · 0 LLM calls.

---

## Mechanism 5 — StructuredDebate

**Concept:** Multi-attribute argumentation with a deterministic rule chain. Each department produces a structured justification (not just a vote), and the coordinator classifies the situation into one of three **modes**, each applied per department rather than as a single global override.

**Action model:** Per-dept.

**Step 1 — Justifications:** Each dept produces:
```python
{"proposed": "H", "risk_estimate": 0.5, "justification_type": "growth", "role": "profit"}
# risk_estimate: 1.0 if R<20, 0.5 if R<40, 0.0 otherwise
```

**Step 2 — Signals:**
- `high_risk_h` = depts with risk=1.0 **and** proposed H (an aggressive agent worried about its own aggression)
- `med_high_risk` = depts with risk≥0.5 **and** proposed M or H

**Step 3 — Mode determination (priority order):**

| Priority | Condition | Mode | Meaning |
|---|---|---|---|
| 1 | `med_high_risk ≥ 3` | `all_L` | Crisis: everyone gets L |
| 2 | `high_risk_h ≥ 1` OR `majority==H and R<70` | `cap_H` | Caution: H→M, L and M stay |
| 3 (fallback) | None of the above | `own` | Safe: each dept uses its own proposal |

> **Bug fix note:** Previously `med_high_risk` counted all depts with risk≥0.5 *regardless of their proposal* — so Compliance proposing L while estimating risk=0.5 would trigger the L-override. This is paradoxical: a conservative agent's alarm was being counted as an aggression signal. Fixed to only count depts that are *both sensing risk AND proposing aggressively* (M or H) — i.e. a dept worried about its own aggression.

**Step 4 — Per-dept application:**
```python
if mode == "all_L":   final_actions = ["L" for _ in proposals]
elif mode == "cap_H": final_actions = ["M" if p == "H" else p for p in proposals]
else:                 final_actions = list(proposals)
```

**Example at R=67, `proposals=[H,H,L,M,L]`:**
majority=H, R<70 → `cap_H` mode.
`final=[M, M, L, M, L]` — Growth/Trading capped, Compliance/Operations/Risk unchanged. ✅

**Why this is per-dept:** A conservative Compliance dept proposing L is never forced to M just because aggressive depts are being capped. The debate only intervenes where it needs to.

**Cost:** 15 messages (3 per dept: proposal + risk + justification type) · 2 rounds · 0 LLM calls.

---

## Mechanism 6 — LLMCentralized

**Concept:** An LLM acting as CFO/Treasury Chair. Reviews all proposals, reserve state, and each department's role — then allocates a **different budget level to each department individually**, not a single policy for all.

**Action model:** Per-dept.

**Logic:**
1. All depts propose via rule-based policies
2. Prompt built with: reserve level, crisis threshold, each dept's name + role + proposal
3. One LLM call → expects per-department JSON:
```json
{
  "Growth Department": "M",
  "Trading/Opportunity Team": "H",
  "Compliance Department": "L",
  "Operations Department": "M",
  "Risk Department": "L",
  "reason": "Allowing trading to capture opportunity while protecting reserve via conservative depts"
}
```
4. `parse_per_dept_actions()` extracts each dept's allocation; falls back to `"M"` per dept or a global action if JSON is malformed

**Why this is richer than Centralized:** The LLM can reason about role heterogeneity in natural language — e.g. "Growth has time-sensitive investment needs; I'll allow H there but constrain Operations to compensate." Rule-based Centralized cannot make this distinction.

**System prompt (key instruction):**
> *"You may give different departments different levels. This lets you balance individual needs against collective sustainability."*

```python
parsed = parse_per_dept_actions(response, dept_names)
final_actions = [parsed[name] for name in dept_names]
```

**Coordination cost:** 6 messages · 1 round · **1 coordinator LLM call** · ~500-2000ms.

**LLM-track total:** when paired with `LLMDepartment`, add 5 department proposal
LLM calls per step, so the measured run-level cost is 6 LLM calls/step for this
mechanism.

---

## Mechanism 7 — CrewAI Debate

**Concept:** Genuine multi-agent orchestration. Each department is a CrewAI Agent
with role/goal/backstory. Agents now argue in two rounds (opening argument, then
rebuttal after seeing the openings), and a Moderator Agent synthesizes the debate
into a **per-department budget level**.

**Action model:** Per-dept.

**Process (Sequential):**

1. **5 Department Agents** built with role metadata from `ROLE_METADATA` dict
2. **1 Moderator Agent** built with neutral synthesis role
3. **5 Opening Tasks** — each department defends its proposed action in 2-3 sentences
4. **5 Rebuttal Tasks** — each department reads all opening arguments, may ask one clarifying delegated question, and either defends or revises its action
5. **1 Moderator Task** — reads openings + rebuttals via context, then:
   > *"Allocate a withdrawal level to EACH department individually. Output JSON: {"Growth Department": "L or M or H", ..., "reason": "..."}"*
6. Output parsed with `parse_per_dept_actions()` — same parser as LLMCentralized

**Key difference from LLMCentralized:**
- LLMCentralized: 1 coordinator call, structured data input, CFO decides all at once
- CrewAI: 11 coordinator calls before optional delegation, natural language arguments, each dept has its own agent context

**Current limitation:** CrewAI delegation can trigger additional sub-calls that
are not individually counted by the coordination object, so `llm_calls` is a
lower bound for CrewAI debate. Wall-clock latency is still measured directly.

**Coordination cost:** 11 messages · 3 rounds · **11 coordinator LLM calls plus
optional delegation** · latency depends heavily on provider and delegation.

**LLM-track total:** when paired with `LLMDepartment`, add 5 department proposal
LLM calls per step, so the measured run-level lower bound is 16 LLM calls/step.

---

## Full Comparison Table

| Mechanism | Per-dept? | LLM calls | Messages | Rounds | Estimated latency |
|---|---|---|---|---|---|
| Independent | ✅ (own) | 0 | 0 | 0 | < 1ms |
| Voting | ❌ (global policy) | 0 | 5 | 1 | < 1ms |
| AdaptiveVoting | ❌ (global policy) | 0 | 5 | 1 | < 1ms |
| Centralized ×3 | ✅ (leader cap) | 0 | 6 | 1 | < 1ms |
| StructuredDebate | ✅ (mode per prop) | 0 | 15 | 2 | < 1ms |
| LLMCentralized | ✅ (CFO allocates) | 1 coord / 6 with LLM depts | 6 | 1 | ~1s+ |
| CrewAIDebate | ✅ (moderator allocs) | 11 coord / 16+ with LLM depts | 11 | 3 | provider-dependent |

---

## Research Ladder

```
Complexity / Cost →

Independent → Voting → AdaptiveVoting → Centralized → StructuredDebate → LLMCentralized → CrewAIDebate
    ↑              ↑          ↑               ↑               ↑                  ↑               ↑
Per-dept,      Global     Reserve-aware    Per-dept,      Per-dept,          Per-dept,       Per-dept,
no coord.      policy     global policy    informed       rule-mode          LLM reasons     agents argue
                                           leader cap     per proposal       about roles     in natural
                                                                                             language

Coord calls:  0          0          0              0              0                1               11+
```

**Core question:** Does each step up this ladder improve sustainability enough to justify the added coordination cost?  
**Composition dimension:** Is the benefit robust across aggressive / standard / conservative agent compositions, or does it only appear under certain conditions?
