"""Strict JSON adapter for the generated SandboxPolicy decision."""
_FIELDS = frozenset({"risk_class", "action_kind", "requested_capability", "source_trust_label"})


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"rows"} or type(payload["rows"]) is not list:
        raise ValueError("expected an object containing a list of rows")
    output = []
    for row in payload["rows"]:
        if type(row) is not dict or set(row) != _FIELDS or any(type(value) is not str for value in row.values()):
            raise ValueError("expected four normalized string fields")
        result = kernel.default__.Evaluate(*(
            dafny.Seq(row[field]) for field in
            ("risk_class", "action_kind", "requested_capability", "source_trust_label")
        ))
        if type(result) is not tuple or len(result) != 2 or any(not isinstance(item, dafny.Seq) for item in result):
            raise ValueError("invalid generated policy result")
        output.append(["".join(item.Elements) for item in result])
    return output
