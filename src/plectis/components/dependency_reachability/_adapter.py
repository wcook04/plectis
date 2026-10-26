"""Convert normalized graph strings into finite integer vertices for Dafny."""

def evaluate(payload, kernel, dafny):
    if type(payload) is not dict or set(payload) != {"edges", "starts"}:
        raise ValueError("expected graph edges and starts")
    edges, starts = payload["edges"], payload["starts"]
    if type(edges) is not list or type(starts) is not list:
        raise ValueError("edges and starts must be lists")
    if any(type(e) is not list or len(e) != 2 or any(type(x) is not str for x in e) for e in edges):
        raise ValueError("edges must be pairs of strings")
    if any(type(x) is not str for x in starts):
        raise ValueError("starts must be strings")
    labels = sorted(set(starts).union(x for edge in edges for x in edge))
    indices = {label: i for i, label in enumerate(labels)}
    encoded = dafny.Seq([kernel.Edge_Edge(indices[u], indices[v]) for u, v in edges])
    return [sorted(labels[i] for i in kernel.default__.Compute(encoded, indices[start]))
            for start in starts]
