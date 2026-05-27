"""
Class-agnostic department compositions.

Both rule-based (`Department`) and LLM-based (`LLMDepartment`) experiments
share the same role mixes.
"""


# (display_name, role) tuples for each composition. The total number of
# departments is always 5 — only the role mix changes.
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
}


def make_compositions(dept_class, **dept_kwargs):
    """
    Return a dict {composition_name: factory()} for the given Department class.

    Each factory returns a fresh list of 5 dept_class instances built with the
    composition's (name, role) pairs and the caller's extra kwargs (e.g.
    reserve_capacity / exploration_rate for `Department`, or model / temperature
    for `LLMDepartment`).
    """
    def make_factory(spec):
        def factory():
            return [dept_class(name, role, **dept_kwargs) for name, role in spec]
        return factory

    return {name: make_factory(spec) for name, spec in COMPOSITION_SPECS.items()}
