"""Validate host-supplied observations and marshal them to the Dafny core."""

_FIELDS = {"hidden", "untrusted", "privileged", "sanitized"}
_VERDICTS = ("block", "review", "warn", "allow")


def _verdicts(rows, kernel, dafny):
    if type(rows) is not list:
        raise ValueError("rows must be a list")
    encoded = []
    for row in rows:
        if type(row) is not dict or set(row) != _FIELDS:
            raise ValueError("each row must have exactly the four policy flags")
        if any(type(row[field]) is not bool for field in _FIELDS):
            raise ValueError("policy flags must be boolean")
        encoded.append(kernel.Input_Input(row["hidden"], row["untrusted"],
                                          row["privileged"], row["sanitized"]))
    decisions = kernel.default__.DecideMany(dafny.Seq(encoded))
    return [_VERDICTS[int(decision)] for decision in decisions]


def _closure(episode, kernel, dafny):
    if type(episode) is not dict or set(episode) != {"node_count", "edges", "seeds"}:
        raise ValueError("invalid episode")
    count = episode["node_count"]
    if type(count) is not int or count < 0:
        raise ValueError("node_count must be a nonnegative integer")
    edges, seeds = episode["edges"], episode["seeds"]
    if type(edges) is not list or type(seeds) is not dict:
        raise ValueError("invalid edges or seeds")
    for edge in edges:
        if type(edge) is not dict or set(edge) != {"source", "target", "hidden"}:
            raise ValueError("invalid edge")
        source, target, hidden = edge["source"], edge["target"], edge["hidden"]
        if (type(source) is not int or type(target) is not int
                or not 0 <= source < count or not 0 <= target < count
                or type(hidden) is not bool):
            raise ValueError("invalid edge observations")
    labels = set(seeds)
    if any(type(label) is not str or not label for label in labels):
        raise ValueError("labels must be nonempty strings")
    if any(edge["hidden"] for edge in edges):
        labels.add("hidden_policy_claim")
    for members in seeds.values():
        if (type(members) is not list or any(type(node) is not int or not 0 <= node < count for node in members)):
            raise ValueError("seed nodes must belong to the episode")
    graph = dafny.Seq([kernel.FlowEdge_FlowEdge(e["source"], e["target"], e["hidden"]) for e in edges])
    result = {}
    for label in sorted(labels):
        members = seeds.get(label, [])
        reached = kernel.default__.Closure(graph, dafny.Set(members), label == "hidden_policy_claim")
        result[label] = sorted(int(node) for node in reached)
    return result


def evaluate(payload, kernel, dafny):
    if type(payload) is not dict:
        raise ValueError("expected policy payload")
    if set(payload) == {"rows"}:
        return _verdicts(payload["rows"], kernel, dafny)
    if set(payload) == {"episodes"} and type(payload["episodes"]) is list:
        return [_closure(episode, kernel, dafny) for episode in payload["episodes"]]
    raise ValueError("expected rows or episodes")
