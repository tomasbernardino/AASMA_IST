# GovSim Features: Universalization, Free-Rider, and Free Negotiation

This commit introduces three major features inspired by the GovSim paper to enhance the LLM agents' behavior and test the robustness of coordination mechanisms.

## Changes:
- **Universalization Reasoning**: Added a Kantian "universal impact" prompt to `LLMDepartment` to encourage sustainable behavior (can be toggled on/off). Created `main_llm_universalization.py` for ablation studies.
- **Free-Rider Composition**: Introduced a new `free_rider` role (Saboteur) in both rule-based and LLM agents. This role always maximizes withdrawal and ignores the common reserve. Added a `free_rider` composition to test mechanism vulnerabilities.
- **Free Negotiation Mechanism**: Implemented `FreeNegotiationCoordination` (Chat Room). LLM agents now have a `chat()` method to discuss and advocate for their goals in a shared transcript before making their final withdrawal proposals. Created `main_llm_negotiation.py` to test this feature.
- **Files Modified**: `src/prompts.py`, `src/llm_agents.py`, `src/agents.py`, `src/compositions.py`, `src/coordination.py`.
