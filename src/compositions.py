"""
Class-agnostic department compositions.

Both rule-based (`Department`) and LLM-based (`LLMDepartment`) experiments
share the same role mixes.
"""


# (display_name, role) tuples for each composition. 
# The total number of departments is always 5, only the role mix changes.
COMPOSITION_SPECS = {
    "standard": [
        ("Growth Department", "profit"),
        ("Trading/Opportunity Team", "profit"),
        ("Compliance Department", "sustainability"),
        ("Operations Department", "balanced"),
        ("Risk Department", "risk_averse"),
    ],
    "aggressive": [
        ("Growth Department", "profit"),
        ("Trading/Opportunity Team", "profit"),
        ("Investment Department", "profit"),
        ("Operations Department", "balanced"),
        ("Risk Department", "risk_averse"),
    ],
    "conservative": [
        ("Growth Department", "profit"),
        ("Compliance Department", "sustainability"),
        ("ESG Department", "sustainability"),
        ("Operations Department", "balanced"),
        ("Risk Department", "risk_averse"),
    ],
    "free_rider": [
        ("Growth Department", "profit"),
        ("Trading/Opportunity Team", "profit"),
        ("Compliance Department", "sustainability"),
        ("Operations Department", "balanced"),
        ("Saboteur Department", "free_rider"),
    ],
}


def make_compositions(dept_class, **dept_kwargs):
    def make_factory(spec):
        def factory():
            return [dept_class(name, role, **dept_kwargs) for name, role in spec]
        return factory

    return {name: make_factory(spec) for name, spec in COMPOSITION_SPECS.items()}
