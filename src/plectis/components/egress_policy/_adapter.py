"""Strict host conversion for the verified egress matcher and policy.

Python's case normalization and isalnum remain outside the Dafny theorem.
"""


def evaluate(payload, kernel, _dafny):
    if type(payload) is not dict or set(payload) != {"text", "groups", "policy"}:
        raise ValueError("invalid egress request")
    text, groups, policy = payload["text"], payload["groups"], payload["policy"]
    if type(text) is not str or type(groups) is not list or type(policy) is not bool:
        raise ValueError("invalid egress request types")
    if policy and (not groups or len(groups) % 2):
        raise ValueError("policy requires pairs of phrase groups")
    if not policy and len(groups) != 1:
        raise ValueError("scan requires one phrase group")
    if any(type(group) is not list or any(type(p) is not str for p in group) for group in groups):
        raise ValueError("groups must contain string lists")
    text_points = _dafny.Seq([ord(c) for c in text])
    matches = []
    for group in groups:
        found = []
        for phrase in group:
            points = _dafny.Seq([ord(c) for c in phrase])
            match = kernel.default__.Find(text_points, points, phrase[:1].isalnum(), phrase[-1:].isalnum())
            if type(match) is not bool:
                raise ValueError("matcher did not return a boolean")
            if match:
                found.append(phrase)
        matches.append(found)
    result = {"matches": matches}
    if policy:
        flags = _dafny.Seq([bool(group) for group in matches])
        violations, red = kernel.default__.EvaluatePolicy(flags)
        violations = list(violations)
        if type(red) is not bool or any(type(v) is not bool for v in violations):
            raise ValueError("policy did not return boolean decisions")
        result.update({"violations": violations, "red": red})
    return result
