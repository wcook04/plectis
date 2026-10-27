"""Strict JSON adapter for the generated ownership decision."""


def evaluate(payload, kernel, _dafny):
    if type(payload) is not dict or set(payload) != {"paths", "claims"}:
        raise ValueError("expected paths and claims")
    if type(payload["paths"]) is not list or type(payload["claims"]) is not list:
        raise ValueError("paths and claims must be lists")
    paths = []
    claims = []
    for row in payload["paths"]:
        if (type(row) is not dict or set(row) != {"id", "generated"}
                or type(row["id"]) is not int or type(row["generated"]) is not bool):
            raise ValueError("invalid path")
        paths.append(kernel.Path_Path(row["id"], row["generated"]))
    for row in payload["claims"]:
        if type(row) is not dict or type(row.get("path")) is not int:
            raise ValueError("invalid claim")
        if set(row) == {"path", "live"} and type(row["live"]) is bool:
            state = "live" if row["live"] else "stale"
        elif (set(row) == {"path", "freshness"} and type(row["freshness"]) is str
              and row["freshness"] in {"live", "stale", "unknown"}):
            state = row["freshness"]
        else:
            raise ValueError("invalid claim")
        constructors = {"live": kernel.Freshness_Live,
                        "stale": kernel.Freshness_Stale,
                        "unknown": kernel.Freshness_Unknown}
        claims.append(kernel.Claim_Claim(row["path"], constructors[state]()))
    computed, classification, action = kernel.default__.Compute(
        _dafny.Seq(paths), _dafny.Seq(claims))
    return {"rows": [{"owner_index": row.ownerIndex, "kind": row.kind} for row in computed],
            "classification": classification,
            "action": action}
