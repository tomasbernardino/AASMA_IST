# Liquidity Commons

Simulation of departments drawing from a shared liquidity reserve. The model compares
coordination mechanisms for deciding low, medium, or high withdrawal policies while
tracking whether the reserve enters a liquidity crisis.

Departments:
- Growth Department: aggressive investment
- Trading/Opportunity Team: for now follows the Growth Department schema
- Compliance Department: reserve protection
- Operations Department: balanced funding needs
- Risk Department: avoids reserve depletion

Coordination mechanisms:
- Independent: each department follows its own policy
- Voting: departments vote on the shared spending policy
- Centralized: a CFO/treasury leader chooses the shared policy
- Debate: departments argue implicitly, with low liquidity shifting decisions toward reserve protection
