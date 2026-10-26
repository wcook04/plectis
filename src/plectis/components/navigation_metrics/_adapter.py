"""Strict adapter from normalized packet observations to the Dafny core."""


def evaluate(payload, kernel, dafny):
    fields = {"expected", "selected", "timeout", "error", "scent_fail", "forbidden", "wall", "budget"}
    if type(payload) is not dict or set(payload) != fields:
        raise ValueError("invalid navigation metrics payload")
    for name in ("expected", "selected"):
        value = payload[name]
        if type(value) is not list or any(type(item) is not str for item in value):
            raise ValueError("artifact IDs must be string lists")
        if len(value) != len(set(value)):
            raise ValueError("artifact IDs must be distinct")
    if any(type(payload[name]) is not bool for name in ("timeout", "error", "scent_fail", "forbidden")):
        raise ValueError("decision flags must be booleans")
    if any(type(payload[name]) is not int for name in ("wall", "budget")):
        raise ValueError("latency values must be integers")
    expected = dafny.Seq([dafny.Seq(s) for s in payload["expected"]])
    selected = dafny.Seq([dafny.Seq(s) for s in payload["selected"]])
    core = kernel.default__
    flags, found, relevant, decision, latency = core.Compute(
        expected, selected, payload["timeout"], payload["error"],
        payload["scent_fail"], payload["forbidden"], payload["wall"], payload["budget"])
    return {"found": [bool(hit) for hit in flags], "found_count": found,
            "relevant_count": relevant, "decision": decision, "latency": latency}
