# Seventh Commit — Coordination and Metrics Corrections

This commit series fixes several issues found during a codebase/results audit
and refreshes the affected outputs.

## Centralized Coordination

The previous centralized experiment used fixed department indices while naming
the mechanisms by role. That made some labels false when role ordering changed
across compositions.

The corrected mechanism is role-selected:

- `centralized_profit` selects the first department with role `profit`.
- `centralized_sustainability` selects the first department with role
  `sustainability`.
- `centralized_risk_averse` selects the first department with role
  `risk_averse`.

If a composition lacks the requested role, that composition/mechanism pair is
skipped rather than silently substituting another role. For example:

- `aggressive` has no sustainability department, so
  `centralized_sustainability` is skipped.
- `free_rider` has no risk-averse department, so
  `centralized_risk_averse` is skipped.

Centralized result rows now include `leader_index`, `leader_name`, and
`leader_role` so the actual leader is explicit.

## Fairness Metric

The old `reward_inequality_gini` metric was invalid for this project because
department rewards are signed utilities. Crisis and risk penalties can make
some total rewards negative, while standard Gini assumes non-negative values.
This produced impossible values above 1 in previous CSVs.

Gini was removed from current outputs and replaced with signed-reward-safe
dispersion metrics:

- `mean_absolute_reward_gap`
- `reward_std`
- `reward_range`

Plots that previously showed Gini now use mean absolute reward gap.

## LLM and CrewAI Fixes

The CrewAI debate metadata now includes the `free_rider` role, so
`free_rider / crewai_debate` no longer falls back to a balanced persona.

`parse_action()` now handles common non-exact LLM responses such as
`"My choice is H"` without incorrectly parsing the first letter in the prose.

`LLM_MODELS` handling is now lazy, so the documented command works without also
requiring `LLM_MODEL` to be set.

## Free Negotiation Cost Accounting

`FreeNegotiationCoordination` now counts both chat calls and post-chat action
proposal calls. For the current one-chat-round setup, `free_negotiation` uses:

- 5 initial department proposal calls from `run_simulation`
- 5 chat calls
- 5 post-chat proposal calls

So the correct total is `15 * steps_survived`.

## Results Refresh

Rule-based outputs were regenerated with:

```bash
python main.py
python sensitivity_analysis.py
```

The refreshed rule-based results now use role-selected centralized mechanisms,
the new fairness metrics, and regenerated figures.

The LLM results were rerun after the centralized and CrewAI fixes. Per model,
the LLM track now has 26 rows:

- 7 rows for `standard`
- 6 rows for `aggressive`
- 7 rows for `conservative`
- 6 rows for `free_rider`

The missing rows are intentional skipped role/composition pairs. The main LLM
figures now include the `free_rider` composition directly; stale
`*_free_rider.png` companion figures from the old addendum workflow were
removed.

## Remaining Notes

`main_llm_negotiation.py`, `main_llm_universalization.py`, and
`main_llm_memory_ablation.py` do not need behavioral reruns for the centralized
role-selection fix. Negotiation outputs were regenerated under the corrected
call accounting in the latest results.
