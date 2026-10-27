"""Encode normalized tactic identities and membership observations for Dafny."""


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"preferences", "candidates"}:
        raise ValueError("expected preferences and candidates")
    preferences, candidates = payload["preferences"], payload["candidates"]
    if type(preferences) is not list or type(candidates) is not list:
        raise ValueError("expected lists")
    if any(type(item) is not str for item in preferences):
        raise ValueError("invalid preference")
    identities = {}
    def identify(value):
        if value not in identities:
            identities[value] = len(identities)
        return identities[value]
    encoded_preferences = [identify(item) for item in preferences]
    encoded_candidates = []
    for row in candidates:
        if type(row) is not dict or set(row) != {"id", "known", "available", "allowed"}:
            raise ValueError("invalid candidate")
        if type(row["id"]) is not str or any(type(row[k]) is not bool for k in ("known", "available", "allowed")):
            raise ValueError("invalid candidate fields")
        encoded_candidates.append(kernel.Candidate_Candidate(
            identify(row["id"]), row["known"], row["available"], row["allowed"]))
    index, preference = kernel.default__.Select(
        dafny.Seq(encoded_preferences), dafny.Seq(encoded_candidates))
    return [index, preference]
