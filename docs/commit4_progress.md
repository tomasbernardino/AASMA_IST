# Commit 4 — Coordination Refactor, Per-Department Actions & Incentive Alignment

## Status Summary

| Component | Status |
|---|---|
| Rule-based coordination (Independent, Voting, AdaptiveVoting, Centralized, StructuredDebate) | ✅ Complete |
| Sensitivity analysis sweep | ✅ Complete |
| Agent composition sensitivity (aggressive / standard / conservative) | ✅ Complete |
| Reward / utility functions | ✅ Complete and aligned |
| `LLMCentralizedCoordination` | ⚠️ Implemented, untested (needs API key) |
| `CrewAIDebateCoordination` | ⚠️ Work in progress — `crewai` package required, latency makes multi-seed runs impractical |
| `main_llm.py` (LLM department proposals) | ⚠️ Work in progress — requires `OPENROUTER_API_KEY` |

---

## What Changed in This Commit

### 1. Removed mechanisms
- **`DebateCoordination` (Simple Debate) — removed.** It was reserve-aware voting with two hardcoded if-statements, not a genuine debate mechanism. Renamed concept absorbed into `AdaptiveVotingCoordination`.
- **`LLMDebateCoordination` — removed.** Passed structured dicts (not language) to the LLM moderator, making it almost identical to StructuredDebate with extra API cost. Replaced by `CrewAIDebateCoordination` which uses true natural language argumentation.

### 2. New mechanism: `AdaptiveVotingCoordination`
Reserve-weighted voting. When the reserve is endangered, conservative (L) votes carry more weight, preventing structurally aggressive agent compositions from always dominating.

### 3. Per-department action model (major refactor)
Previously, every coordination mechanism (except Independent) returned the same single action for all 5 departments. Now each mechanism produces a **differentiated allocation** per department. See the full explanation in the section below.

### 4. Centralized leader is now informed
The leader no longer ignores other departments' proposals. It reads all proposals and applies group alarm signals:
- ≥4 propose L → leader steps to L regardless of own policy
- ≥3 propose L and leader proposed H → leader steps to M
- Otherwise → leader uses own policy

### 5. Bug fix: StructuredDebate `medium_high_risk_count`
Previously counted all depts with `risk_estimate ≥ 0.5` regardless of what they proposed — so a Compliance dept proposing L while sensing risk would *trigger* the L-override, which is a paradox (a conservative agent's alarm being counted as an aggression signal). Fixed to only count depts that are *both sensing risk AND proposing aggressively* (M or H).

### 6. Bug fix: redundant justification computation in `simulation.py`
The simulation was calling `dept.justify_action()` separately after coordination had already computed it. Removed the duplicate call.

### 7. Agent composition sensitivity
`main.py` now runs 3 different agent compositions:
- **Standard**: 2 profit + 1 sustainability + 1 balanced + 1 risk_averse
- **Aggressive**: 3 profit + 1 balanced + 1 risk_averse
- **Conservative**: 1 profit + 2 sustainability + 1 balanced + 1 risk_averse

We test these different sets of departments to ensure our results aren't biased by a single composition. Without this, it would be impossible to tell if a coordination mechanism performed well universally, or if it only succeeded because the specific group of departments was already easy to coordinate. By testing across these 3 variations, we successfully separate *mechanism effects* from *composition effects* — addressing a key criticism from the academic framing.

### 8. Clean separation: `main.py` vs `main_llm.py`
- `main.py` — rule-based departments only, no API key required, 20 seeds, 3 compositions, outputs to `results/raw/`
- `main_llm.py` — LLM departments, requires `OPENROUTER_API_KEY`, 5 seeds, standard composition only, outputs to `results/llm/`

### 9. Sensitivity analysis rewrite
`sensitivity_analysis.py` sweeps environmental hostility across a 3×3 grid (recovery noise × shock probability) with all rule-based mechanisms. Fixes a critical bug where it was passing `recovery_rate` (nonexistent parameter) instead of `recovery_noise_std`.

---

## Deep Explanation: Departments and the Reward Mechanism

### The Shared Pool Problem

Five departments draw from a single liquidity reserve with capacity 100. Each step, the reserve recovers logistically and then shrinks by the sum of all department withdrawals:

```
R_{t+1} = R_t + 0.3 · R_t · (1 − R_t/100) − Σ(withdrawals)
```

A **liquidity crisis** occurs when `R ≤ 5`. Once this happens, the organization is effectively insolvent. This is the classic Tragedy of the Commons: individually rational withdrawal decisions collectively deplete a shared resource.

---

### The 5 Departments

Each department has a fixed **role** that determines:
1. Its **proposal policy** — what withdrawal level it proposes based on the reserve
2. Its **utility function** — how it measures the value of outcomes

#### Growth Department & Trading/Opportunity Team (role: `profit`)

**Policy:**
```python
if reserve_level < 20: return "M"   # emergency brake
return "H"                           # always aggressive otherwise
```

**Utility function:**
```
U_profit = withdrawal
```
Pure self-interest. The profit agent cares only about how much it withdraws. It has no direct incentive to consider the reserve's health — it proposes H in almost all circumstances because higher withdrawal = higher utility. This is the agent that *creates* the commons problem.

**Incentive conflict:** Two profit agents always proposing H at healthy reserves (R>20) contribute 6 units of withdrawal per step, which when combined with other departments can outpace recovery.

---

#### Compliance Department (role: `sustainability`)

**Policy:**
```python
if reserve_level < 70: return "L"   # protect reserve when it drops
return "M"                           # only moderate spend when healthy
```

**Utility function:**
```
U_sustainability = withdrawal − 5.0 · crisis_risk
                  where crisis_risk = 1.0 if R < 20, else 0.0
```
The `α = 5.0` penalty means a crisis is worth −5 points, wiping out up to 1.67 steps of maximum withdrawal (H = 3 units). This agent is motivated to *prevent* crisis even at the cost of lower withdrawal. It proposes L whenever the reserve dips below 70% — very conservative.

---

#### Operations Department (role: `balanced`)

**Policy:**
```python
if reserve_level < 40: return "L"   # conserve when dangerous
if reserve_level > 80: return "H"   # spend more when healthy
return "M"                           # moderate otherwise
```

**Utility function:**
```
U_balanced = withdrawal − 3.0 · reserve_deficit
             where reserve_deficit = max(0, 50 − R) / 50
```
The `β = 3.0` penalty grows as the reserve falls below 50 (the midpoint). At `R=20`, deficit = 0.6 → penalty = 1.8. Operations adapts its proposals to the state of the reserve, making it the most environmentally responsive agent. It's the swing voter in the voting mechanisms.

---

#### Risk Department (role: `risk_averse`)

**Policy:**
```python
if reserve_level < 90: return "L"   # almost always conservative
return "M"                           # only moderate when near-full
```

**Utility function:**
```
U_risk_averse = withdrawal − 2.0 · volatility
                where volatility = |R_t − R_{t-1}| / capacity
```
The `γ = 2.0` penalty targets *change* in reserve level, not its absolute value. A sudden drop of 20 units produces `volatility = 0.2 → penalty = 0.4`. This agent is penalised by instability — it cares about avoiding sudden shocks more than the average level. It proposes L in almost all circumstances (R must be ≥ 90 for it to consider M).

---

### Why Incentive Divergence Matters

The four utility functions are deliberately *misaligned*:

| Role | Cares about | Ignores |
|---|---|---|
| profit | Withdrawal amount | Reserve health entirely |
| sustainability | Crisis prevention | Moderate reserve levels |
| balanced | Reserve midpoint | Sudden volatility |
| risk_averse | Reserve volatility | Absolute reserve level |

This means the same observable state (`R = 45`) leads to fundamentally different evaluations:
- Profit: "Fine, reserve is above 20, take H"
- Sustainability: "Reserve is below 70, must take L"
- Balanced: "Reserve is between 40 and 80, take M"
- Risk: "Reserve is below 90, take L"

The proposals diverge precisely because the departments have different things to protect. **This is the research problem**: how do you coordinate agents with genuinely different interests over a shared resource?

---

### Universal Crisis Penalty

All roles share one additional term:
```
reward -= 5.0 if crisis else 0
```
This creates a common floor of shared pain — everyone suffers when the reserve collapses. It represents the shared externality of a commons tragedy: even the most aggressive profit agent faces a −5 penalty in a crisis step, more than the maximum single-step withdrawal gain (H = 3). This is why even purely self-interested agents *should* coordinate — repeated crises make them worse off in expectation.

---

## Deep Explanation: How Actions Are Now Chosen

### The Old Model (before this commit)
Every mechanism except Independent returned a **single global action** for all 5 departments:
```python
final_actions = ["M", "M", "M", "M", "M"]  # all the same
```
This is a *policy* model: the coordination layer decides one rule that everyone follows equally. It simplifies implementation but is unrealistic — a real CFO or debate doesn't tell everyone to do the exact same thing.

### The New Model (after this commit)
Each mechanism now returns **per-department actions**:
```python
final_actions = ["M", "H", "L", "M", "L"]  # different per dept
```

---

### Per-Department Logic by Mechanism

#### Independent — each dept follows its own proposal
No change. Has always been per-department.
```python
return proposals, cost  # proposals IS final_actions
```

#### Voting & AdaptiveVoting — still global (intentional)
The whole point of a vote is that it produces one binding collective policy. Making voting per-department would undermine what a vote is — a collective decision that everyone follows equally. These two mechanisms remain global.

#### Centralized — leader caps aggressors, respects conservatives

The leader's informed decision acts as an **upper bound** for each department. A department that proposed *less* than the leader keeps its own lower proposal (the leader cannot force conservative depts to withdraw more). A department that proposed *more* than the leader is capped at the leader's level.

```python
action_rank = {"L": 0, "M": 1, "H": 2}
final_actions = [
    p if action_rank[p] <= action_rank[leader_action] else leader_action
    for p in proposals
]
```

**Example — profit leader (`leader_action = M` after alarm override, `proposals = [H, H, L, L, L]`):**
```
Growth     → proposed H > M → capped to M
Trading    → proposed H > M → capped to M
Compliance → proposed L ≤ M → keeps L
Operations → proposed L ≤ M → keeps L
Risk       → proposed L ≤ M → keeps L
Result: [M, M, L, L, L]
```

The leader constrains aggressive departments without overriding conservative mandates.

#### StructuredDebate — mode-based per-department application

The rule chain classifies the situation into one of three modes:

| Mode | Trigger | Effect on each dept |
|---|---|---|
| `all_L` | ≥3 depts with risk≥0.5 AND proposing M or H | Everyone gets L |
| `cap_H` | Any dept has risk=1.0 AND proposes H, OR majority=H and R<70 | H proposals become M; L and M untouched |
| `own` | None of the above | Each dept executes its own proposal |

```python
if mode == "all_L":   final_actions = ["L" for _ in proposals]
elif mode == "cap_H": final_actions = ["M" if p == "H" else p for p in proposals]
else:                 final_actions = list(proposals)
```

**Example at R=67, `proposals = [H, H, L, M, L]`:**
Majority = H, R < 70 → `cap_H` mode.
```
Growth     → H → M
Trading    → H → M
Compliance → L → L (untouched)
Operations → M → M (untouched)
Risk       → L → L (untouched)
Result: [M, M, L, M, L]
```

The debate only intervenes where needed — conservative departments are never forced upward.

#### LLMCentralized — LLM allocates individually per department
The CFO LLM receives a prompt asking for a JSON allocation with one key per department name. It can reason about role heterogeneity: "Growth has urgent investment needs; I'll allow H there but constrain Operations to compensate."

#### CrewAIDebate (⚠️ WIP) — moderator allocates individually
After hearing natural language arguments from each department agent, the CrewAI moderator allocates L/M/H to each department individually in a JSON response.

---

## Updated Mechanism Comparison

| Mechanism | Action model | LLM calls/step | API required |
|---|---|---|---|
| Independent | Per-dept (own proposal) | 0 | ❌ |
| Voting | Global policy | 0 | ❌ |
| AdaptiveVoting | Global policy (reserve-weighted) | 0 | ❌ |
| Centralized ×3 | Per-dept (leader cap) | 0 | ❌ |
| StructuredDebate | Per-dept (mode: own/cap_H/all_L) | 0 | ❌ |
| LLMCentralized | Per-dept (CFO allocates) | 1 | ✅ ⚠️ |
| CrewAIDebate | Per-dept (moderator allocates) | 6 | ✅ ⚠️ WIP |

---

## Files Changed

| File | Change |
|---|---|
| `src/coordination.py` | Removed SimpleDebate and LLMDebate; Added AdaptiveVoting; Fixed Centralized (informed leader + per-dept); Fixed StructuredDebate (mode-based per-dept + risk count bug); Fixed LLMCentralized (per-dept output) |
| `src/prompts.py` | Updated centralized leader prompt to request per-department JSON allocation |
| `src/llm_client.py` | Added `parse_per_dept_actions()` function |
| `src/crewai_coordination.py` | Updated moderator to allocate per-department; uses `parse_per_dept_actions()` |
| `src/agents.py` | No change — reward functions were already correct |
| `main.py` | Removed LLMCentralizedCoordination; Added 3 compositions loop; Added AdaptiveVoting |
| `main_llm.py` | Added all 3 centralized leader variants; Added `composition` column; Added `debate_override_rate`; Fixed docstring |
| `sensitivity_analysis.py` | Complete rewrite: fixed environment parameter, added all mechanisms, correct aggregation |

---

## Next Steps

1. **Run `python main.py`** — generates the main comparison results across 3 compositions (no API key needed, ~5 min)
2. **Run `python sensitivity_analysis.py`** — generates environment stress results (~2 min)
3. **Generate figures** — `src/plotting.py` reads the CSVs and produces plots
4. **Run `python main_llm.py`** — requires `OPENROUTER_API_KEY`, runs LLM department proposals + CrewAI debate (expensive, run last)
