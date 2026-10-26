from __future__ import annotations

import random
from collections import defaultdict

import pytest

from microcosm_core.organs.batch5_authority_systems_capsule import _blast_radius_exercise
from plectis.components.dependency_reachability import dependents
from plectis.components.dependency_reachability._adapter import evaluate


def _reference(edges, start):
    adjacency = defaultdict(list)
    for source, target in edges:
        adjacency[source].append(target)
    seen = set()
    queue = list(adjacency[start])
    while queue:
        node = queue.pop()
        if node not in seen:
            seen.add(node)
            queue.extend(adjacency[node])
    return sorted(seen)


def test_paths_cycles_and_positive_length():
    edges = [["x", "b"], ["b", "c"], ["c", "b"], ["b", "x"], ["z", "z"]]
    assert dependents(edges, ["x", "z", "missing"]) == [["b", "c", "x"], ["z"], []]
    assert dependents([["x", "b"], ["b", "c"]], ["x"]) == [["b", "c"]]


def test_small_graphs_match_independent_traversal():
    rng = random.Random(14073)
    labels = ["", "a", "b", "c", "z"]
    for _ in range(15):
        edges = [[a, b] for a in labels for b in labels if rng.randrange(4) == 0]
        assert dependents(edges, labels) == [_reference(edges, start) for start in labels]


def test_long_cycle_duplicate_edges_and_repeated_unicode_starts():
    labels = [f"node-{i}" for i in range(75)]
    edges = [[a, b] for a, b in zip(labels, labels[1:])]
    edges += [[labels[-1], labels[0]], ["", "é"], ["", "é"]]
    starts = [labels[0], labels[-1], "", "é", "absent", labels[0]]
    expected = [sorted(labels), sorted(labels), ["é"], [], [], sorted(labels)]
    assert dependents(edges, starts) == expected
    assert dependents(list(reversed(edges)), starts) == expected
    assert dependents([], ["", "absent", ""]) == [[], [], []]
    assert dependents(edges, []) == []


def test_real_evaluator_normalizes_and_invokes_verified_route(monkeypatch):
    import plectis.components.dependency_reachability as package
    calls = []

    def spy(edges, starts):
        calls.append((edges, starts))
        return [_reference(edges, start) for start in starts]

    monkeypatch.setattr(package, "dependents", spy)
    result = _blast_radius_exercise({"target": "x", "leaf_target": "unused",
        "graph": {"b": ["x"], "c": ["b"], 42: ["c"], "ignored": "x"}})
    assert calls == [([["x", "b"], ["b", "c"], ["c", "42"]], ["x", "unused"])]
    assert result["target_transitive_dependents"] == ["42", "b", "c"]
    assert result["leaf_transitive_dependents"] == []
    assert result["status"] == "pass"


def test_real_evaluator_with_generated_core():
    result = _blast_radius_exercise({"target": "x", "leaf_target": "z",
        "graph": {"b": ["x"], "c": ["b"], "z": []}})
    assert result["target_transitive_dependents"] == ["b", "c"]
    assert result["leaf_transitive_dependents"] == []
    assert result["status"] == "pass"


def test_real_evaluator_has_no_python_fallback(monkeypatch):
    import plectis.components.dependency_reachability as package

    def unavailable(_edges, _starts):
        raise RuntimeError("verified reachability unavailable")

    monkeypatch.setattr(package, "dependents", unavailable)
    with pytest.raises(RuntimeError, match="verified reachability unavailable"):
        _blast_radius_exercise({"target": "x", "graph": {"b": ["x"]}})


@pytest.mark.parametrize("payload", [None, {}, {"edges": [], "starts": [], "extra": 1},
    {"edges": [["a", 1]], "starts": []}, {"edges": [("a", "b")], "starts": []},
    {"edges": [], "starts": [True]}])
def test_adapter_rejects_malformed_inputs(payload):
    with pytest.raises(ValueError):
        evaluate(payload, None, None)


def test_adapter_encodes_nodes_and_decodes_sorted_results():
    class FakeDafny:
        Seq = staticmethod(list)

    class Kernel:
        Edge_Edge = staticmethod(lambda u, v: (u, v))

        class default__:
            @staticmethod
            def Compute(edges, start):
                assert edges == [(2, 0), (0, 1)]
                assert start == 2
                return {1, 0}

    assert evaluate({"edges": [["z", "a"], ["a", "m"]], "starts": ["z"]},
                    Kernel, FakeDafny) == [["a", "m"]]
