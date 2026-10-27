"""Strict adapter from JSON string lists to the generated walkthrough core."""
from fractions import Fraction


def evaluate(payload, kernel, _dafny):
    if type(payload) is not dict or set(payload) != {"steps", "time_budget_minutes"} or type(payload["steps"]) is not list:
        raise ValueError("expected steps and a numeric minute budget")
    budget = payload["time_budget_minutes"]
    if type(budget) not in (int, float):
        raise ValueError("expected a numeric minute budget")
    try:
        exact_budget = Fraction(budget)
    except (ValueError, OverflowError) as error:
        raise ValueError("expected a finite numeric minute budget") from error
    keys = {"commands", "inspect_refs", "evidence_refs"}
    strings = set()
    for row in payload["steps"]:
        if type(row) is not dict or set(row) != keys:
            raise ValueError("invalid step")
        for field in keys:
            if type(row[field]) is not list or any(type(v) is not str or not v.strip() for v in row[field]):
                raise ValueError("expected nonblank string references")
            strings.update(row[field])
    ranks = {value: i for i, value in enumerate(sorted(strings))}
    steps = _dafny.Seq([
        kernel.Step_Step(*[_dafny.Seq([ranks[v] for v in row[field]])
                           for field in ("commands", "inspect_refs", "evidence_refs")])
        for row in payload["steps"]
    ])
    accepted, command_count, evidence_count = kernel.default__.Evaluate(
        steps, exact_budget.numerator, exact_budget.denominator,
    )
    return {"accepted": accepted, "command_count": command_count,
            "evidence_count": evidence_count}
