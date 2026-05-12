# Mechanism Design — Q&A Clarifications

---

## Q: Are only the LLM mechanisms per-department?

**No.** Multiple rule-based mechanisms also produce per-department actions.

| Mechanism | Per-dept? | How |
|---|---|---|
| Independent | ✅ | Each dept executes its own proposal |
| Voting | ❌ | Global policy — majority winner for all |
| AdaptiveVoting | ❌ | Global policy — weighted majority for all |
| Centralized ×3 | ✅ | Leader caps aggressors; conservatives keep their own proposal |
| StructuredDebate | ✅ | Mode applied per proposal (side effect of rule chain) |
| LLMCentralized | ✅ | LLM explicitly allocates per department |
| CrewAIDebate | ✅ (WIP) | Moderator explicitly allocates per department |

**Only Voting and AdaptiveVoting remain global** — intentionally, because a democratic vote produces one collective rule that everyone follows equally. Making voting per-department would undermine what a vote conceptually is.

---

## Q: What is the difference between AdaptiveVoting and Centralized?

They answer fundamentally different governance questions.

### AdaptiveVoting — *"What does the group want, with safety weighting?"*
- **Democratic**: every department has one vote, equal authority
- Reserve level affects **vote weights**, not who decides
- At R=35: L votes count ×2 → three L votes beat two H votes even with an aggressive majority
- Output: **one action for all 5 departments**
- No single authority — the group moderates itself collectively

### Centralized — *"What does the leader decide, informed by the group?"*
- **Hierarchical**: one leader has authority, others are advisors
- Reserve level affects **the leader's own proposal** through their role policy
- The leader can be overridden only by near-unanimous alarm (≥3–4 depts propose L)
- Output: **different actions per department** — aggressors are capped, conservatives keep their own proposal

### Concrete example at R=35, proposals = `[H, H, L, L, L]`

**AdaptiveVoting** (R in 20–40 range → L weight = 2):
```
Weighted: H = 2×1 = 2,  L = 3×2 = 6
Winner: L
final = [L, L, L, L, L]   ← everyone gets L, including Growth and Trading
```

**Centralized_profit** (leader = Trading/index=1, proposes H):
```
conservative_count = 3  →  leader steps H → M
Per-dept cap at M:
  Growth     H > M → capped to M
  Trading    H > M → capped to M  (leader)
  Compliance L ≤ M → keeps L
  Operations L ≤ M → keeps L
  Risk       L ≤ M → keeps L
final = [M, M, L, L, L]
```

**Key practical differences:**
1. AdaptiveVoting forces Growth and Trading all the way to L; Centralized (profit leader) only brings them to M
2. AdaptiveVoting treats all departments symmetrically (they're all just votes); Centralized respects each dept's mandate individually
3. With a different leader (sustainability or risk), Centralized produces a completely different result — leader identity matters as much as the mechanism

---

## Q: Is plain Voting still needed if we have AdaptiveVoting?

**Yes — keep it as the naïve democratic baseline.**

AdaptiveVoting is only meaningfully different from Voting when **R < 40**. When R ≥ 40, both use identical weights `{L:1, M:1, H:1}` and produce the same result. The only improvement AdaptiveVoting adds is reserve-awareness in the danger/crisis zone.

This means the Voting → AdaptiveVoting comparison directly isolates **one variable**: the effect of reserve-weighted votes. Without plain Voting in the results, you cannot make the claim "AdaptiveVoting is better by X% because of reserve-awareness" — you lose the controlled comparison.

Think of the ladder:
```
Independent → Voting → AdaptiveVoting → Centralized → StructuredDebate
   (none)      (naïve   (reserve-aware   (authority)    (structured
               democracy)  democracy)                    argumentation)
```
Each step should show measurable improvement over the previous. Removing Voting collapses two improvements (adding coordination + adding reserve-awareness) into one jump, making it harder to explain what's driving the gain.

---

## Q: What is StructuredDebate?

StructuredDebate is the richest rule-based mechanism. The key difference from all voting mechanisms:

**Every voting mechanism only sees the proposal (L/M/H).** StructuredDebate sees a richer justification object per department:
```python
{
    "proposed": "H",
    "risk_estimate": 0.5,          # how dangerous does THIS dept think it is?
    "justification_type": "growth", # why are they proposing this?
    "role": "profit"
}
```

This separates **what a department wants** from **what it thinks about the situation**. A profit department can want H but simultaneously acknowledge medium risk — that signal is more meaningful than just the vote "H".

The coordinator applies a **priority rule chain**:

| Priority | Condition | Mode |
|---|---|---|
| 1 | ≥3 depts sensing risk AND proposing aggressively (M or H) | `all_L`: everyone gets L |
| 2 | Any dept sensing high risk AND proposing H, OR majority=H with R<70 | `cap_H`: H proposals become M |
| 3 (fallback) | None of the above | `own`: each dept uses its own proposal |

Compared to other mechanisms:

| Mechanism | What it reads |
|---|---|
| Voting | Proposal only |
| AdaptiveVoting | Proposal + reserve level (for weighting) |
| Centralized | All proposals + reserve level (through leader policy) |
| **StructuredDebate** | **Proposal + risk estimate + justification type per dept** |

The key insight: **an aggressive department's alarm signal carries different weight than a conservative department's alarm signal.** If Growth (profit) proposes H but estimates medium risk — that's a stronger crisis signal than Compliance sensing risk (Compliance always thinks risk is high). Voting mechanisms cannot capture this distinction.

---

## Q: Does StructuredDebate choose an action per department based on needs, or one overall action?

**Per-department — but not based on individual needs.**

StructuredDebate picks a mode based on the overall situation, then applies it mechanically to each proposal:
```
cap_H mode:  H → M,   L → L,   M → M
```
Growth (proposed H) gets M and Compliance (proposed L) gets L — but that's a **side effect of the rule**, not a deliberate decision *about* Growth or Compliance specifically.

The mechanism doesn't say *"Growth deserves M because of its investment mandate."* It says *"H is too aggressive right now — cap all H proposals to M."*

**Contrast with LLMCentralized**, which is truly needs-aware:
> *"Growth has time-sensitive investment needs — allow H. But Operations must reduce spending to compensate — give them L."*

The LLM reasons about each department individually and deliberately assigns an action to each one.

### The critical distinction:

| Mechanism | How per-dept actions arise |
|---|---|
| **StructuredDebate** | Mode fires globally → proposals filtered mechanically → departments get different outcomes as a side effect |
| **Centralized** | Leader decision is a cap → aggressors get capped, conservatives keep own → different outcomes as a side effect |
| **LLMCentralized / CrewAI** | Coordinator reasons about each dept's role and need → deliberately assigns an action to each one |

**StructuredDebate and Centralized are per-department by consequence.**  
**LLM mechanisms are per-department by design.**

This is a valid research distinction worth stating in the presentation: rule-based mechanisms can only produce differentiated allocations as a side effect of aggregate rules, while LLM-based mechanisms can reason about individual department mandates directly — which is both their strength and their cost.
