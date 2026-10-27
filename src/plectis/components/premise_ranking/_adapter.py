"""Strictly encode normalized term counts and candidate observations for Dafny."""


def _naturals(value):
    return type(value) is list and all(type(item) is int and item >= 0 for item in value)


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"query_counts", "candidates"}:
        raise ValueError("expected query counts and candidates")
    query, candidates = payload["query_counts"], payload["candidates"]
    if not _naturals(query) or type(candidates) is not list:
        raise ValueError("invalid normalized counts or candidates")
    encoded = []
    for row in candidates:
        if type(row) is not dict or set(row) != {"eligible", "id_rank", "counts", "bonus"}:
            raise ValueError("invalid candidate")
        if (type(row["eligible"]) is not bool or type(row["bonus"]) is not bool
                or type(row["id_rank"]) is not int or row["id_rank"] < 0
                or not _naturals(row["counts"]) or len(row["counts"]) != len(query)):
            raise ValueError("invalid candidate values")
        encoded.append(kernel.Candidate_Candidate(
            row["eligible"], row["id_rank"], dafny.Seq(row["counts"]), row["bonus"]))
    result = kernel.default__.Compute(dafny.Seq(query), dafny.Seq(encoded))
    return [[entry.index, entry.score] for entry in result]
