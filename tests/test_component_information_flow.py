"""Behavioral checks for the verified information-flow policy decision."""
from itertools import product

import pytest

from microcosm_core.organs import indirect_prompt_injection_information_flow_policy_replay as flow
from plectis.components.information_flow import verdicts
from plectis.components.information_flow._adapter import evaluate


def test_all_policy_decisions_match_the_policy_table():
    rows = [dict(zip(("hidden", "untrusted", "privileged", "sanitized"), values))
            for values in product((False, True), repeat=4)]
    # Order is (hidden, untrusted, privileged, sanitized), False before True.
    assert verdicts(rows) == [
        "allow", "allow", "allow", "allow",
        "review", "warn", "block", "review",
        "block", "block", "block", "block",
        "block", "block", "block", "block",
    ]


def test_adapter_rejects_non_boolean_and_unexpected_fields():
    class NeverCalled:
        def __getattr__(self, _):
            raise AssertionError("invalid input reached the generated kernel")

    good = {"hidden": False, "untrusted": True, "privileged": True, "sanitized": False}
    for invalid in ({**good, "hidden": 1}, {**good, "sanitized": None},
                    {**good, "extra": False}, {"hidden": False}, [good]):
        with pytest.raises(ValueError):
            evaluate({"rows": [invalid]}, NeverCalled(), NeverCalled())
    with pytest.raises(ValueError):
        evaluate({"rows": [], "extra": 1}, NeverCalled(), NeverCalled())


def test_runtime_normalization_keeps_python_boolean_and_case_semantics():
    assert flow._derived_policy_verdict({"privileged_sink": True}, ["untrusted_web"]) == "block"
    assert flow._derived_policy_verdict({"privileged_sink": 1}, ["untrusted_web"]) == "review"
    assert flow._derived_policy_verdict({"privileged_sink": True, "sanitization_applied": 1}, ["untrusted_web"]) == "block"
    assert flow._derived_policy_verdict({"sink_kind": "instruction_channel"}, []) == "block"
    assert flow._derived_policy_verdict({"proposed_action_ref": "promote_policy"}, []) == "block"
    assert flow._derived_policy_verdict({"proposed_action_ref": "Promote_policy"}, []) == "allow"
    assert flow._derived_policy_verdict({}, ["hidden_policy_claim"]) == "block"
    assert flow._derived_policy_verdict({}, ["Untrusted_web"]) == "allow"


def test_real_propagation_path_calls_verified_batch(monkeypatch):
    import plectis.components.information_flow as policy

    calls = []
    real_verdicts = policy.verdicts

    def observed(rows):
        calls.append(rows)
        return real_verdicts(rows)

    monkeypatch.setattr(policy, "verdicts", observed)
    rows = [
        {"episode_id": "e", "flow_id": "one", "from_source_id": "a", "to_sink_id": "b",
         "sink_kind": "external_action", "privileged_sink": True, "sanitization_applied": False,
         "taint_labels": ["untrusted_web"], "policy_verdict": "block"},
        {"episode_id": "e", "flow_id": "two", "from_source_id": "a", "to_sink_id": "c",
         "sink_kind": "answer", "taint_labels": ["untrusted_web"], "policy_verdict": "review"},
    ]
    result, findings = flow._taint_propagation_receipt(rows, {"a": {"episode_id": "e", "taint_labels": ["untrusted_web"]}})
    assert len(calls) == 1 and len(calls[0]) == 2
    assert [row["derived_policy_verdict"] for row in result["flow_path_rows"]] == ["block", "review"]
    assert result["status"] == "pass" and findings == []


def test_out_of_order_chain_cannot_pass_an_unsanitized_privileged_flow():
    """A trusted intermediate must not erase untrusted upstream data."""
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input"
    source_rows = flow.validate_source_documents(
        json.loads((fixture / "source_documents.json").read_text())
    )["source_rows"]
    source_rows += [
        {"source_id": "chain_a", "episode_id": "0_chain", "trust_label": "untrusted_web", "taint_labels": ["untrusted_text"]},
        {"source_id": "chain_b", "episode_id": "0_chain", "trust_label": "trusted_user_intent", "taint_labels": ["trusted_instruction"]},
    ]
    graph = json.loads((fixture / "information_flow_graph.json").read_text())
    graph["information_flows"] += [
        {"body_redacted": True, "episode_id": "0_chain", "flow_id": "01_b_c",
         "from_source_id": "chain_b", "to_sink_id": "chain_c", "sink_kind": "external_action",
         "source_trust_label": "trusted_user_intent", "taint_labels": ["trusted_instruction"],
         "sanitization_applied": False, "proposed_action_ref": "action", "privileged_sink": True,
         "policy_verdict": "allow"},
        {"body_redacted": True, "episode_id": "0_chain", "flow_id": "02_a_b",
         "from_source_id": "chain_a", "to_sink_id": "chain_b", "sink_kind": "answer",
         "source_trust_label": "untrusted_web", "taint_labels": ["untrusted_text"],
         "sanitization_applied": False, "proposed_action_ref": "read", "privileged_sink": False,
         "policy_verdict": "review"},
    ]
    result = flow.validate_information_flow_graph(graph, source_rows)
    by_id = {r["flow_id"]: r for r in result["flow_rows"]}
    assert result["status"] == "blocked"
    assert by_id["01_b_c"]["derived_taint_labels"] == ["trusted_instruction", "untrusted_text"]
    assert by_id["01_b_c"]["derived_policy_verdict"] == "block"
    assert {f["error_code"] for f in result["findings"]} >= {
        "PROMPT_INJECTION_TAINT_PROPAGATION_MISMATCH",
        "PROMPT_INJECTION_POLICY_VERDICT_DERIVATION_MISMATCH",
    }


def test_cycles_terminate_and_episode_labels_do_not_leak():
    sources = {"a": {"episode_id": "one", "taint_labels": ["untrusted_text"]},
               "b": {"episode_id": "one", "taint_labels": ["trusted_instruction"]},
               "other": {"episode_id": "two", "taint_labels": ["trusted_instruction"]}}
    rows = [
        {"episode_id": "one", "flow_id": "01", "from_source_id": "b", "to_sink_id": "c",
         "privileged_sink": True, "policy_verdict": "block", "taint_labels": ["trusted_instruction", "untrusted_text"]},
        {"episode_id": "one", "flow_id": "02", "from_source_id": "a", "to_sink_id": "b",
         "policy_verdict": "review", "taint_labels": ["trusted_instruction", "untrusted_text"]},
        {"episode_id": "one", "flow_id": "03", "from_source_id": "b", "to_sink_id": "a",
         "policy_verdict": "review", "taint_labels": ["trusted_instruction", "untrusted_text"]},
        {"episode_id": "two", "flow_id": "04", "from_source_id": "other", "to_sink_id": "b",
         "policy_verdict": "allow", "taint_labels": ["trusted_instruction"]},
        {"episode_id": "two", "flow_id": "05", "from_source_id": "b", "to_sink_id": "d",
         "privileged_sink": True, "policy_verdict": "allow", "taint_labels": ["trusted_instruction"]},
    ]
    result, findings = flow._taint_propagation_receipt(rows, sources)
    by_id = {r["flow_id"]: r for r in result["flow_path_rows"]}
    assert result["status"] == "pass" and not findings
    assert by_id["01"]["derived_policy_verdict"] == "block"
    assert by_id["05"]["derived_taint_labels"] == ["trusted_instruction"]
    assert by_id["05"]["derived_policy_verdict"] == "allow"
    assert all(len(path) <= 5 for r in result["flow_path_rows"] for path in r["source_to_sink_paths"])
    for output in result["flow_path_rows"]:
        source = next(row for row in rows if row["flow_id"] == output["flow_id"])
        edges = {(row["from_source_id"], row["to_sink_id"]) for row in rows
                 if row["episode_id"] == source["episode_id"]}
        for path in output["source_to_sink_paths"]:
            assert all(pair in edges for pair in zip(path, path[1:]))
            assert path[-2:] == [source["from_source_id"], source["to_sink_id"]]


def test_hidden_policy_taint_reaches_downstream_even_when_sorted_first():
    sources = {"a": {"episode_id": "e", "taint_labels": ["untrusted_text"]},
               "b": {"episode_id": "e", "taint_labels": ["trusted_instruction"]}}
    rows = [
        {"episode_id": "e", "flow_id": "01", "from_source_id": "b", "to_sink_id": "c",
         "policy_verdict": "block", "taint_labels": ["hidden_policy_claim", "trusted_instruction", "untrusted_text"]},
        {"episode_id": "e", "flow_id": "02", "from_source_id": "a", "to_sink_id": "b",
         "sink_kind": "instruction_channel", "policy_verdict": "block",
         "taint_labels": ["hidden_policy_claim", "untrusted_text"]},
    ]
    result, findings = flow._taint_propagation_receipt(rows, sources)
    by_id = {r["flow_id"]: r for r in result["flow_path_rows"]}
    assert result["status"] == "pass" and not findings
    assert by_id["01"]["derived_taint_labels"] == ["hidden_policy_claim", "trusted_instruction", "untrusted_text"]
    assert by_id["01"]["derived_policy_verdict"] == "block"
    assert ["a", "b", "c"] in by_id["01"]["source_to_sink_paths"]
    hidden = next(w for w in by_id["01"]["taint_witnesses"] if w["label"] == "hidden_policy_claim")
    assert hidden["origin"] == "hidden_edge" and hidden["seed_flow_id"] == "02"
    assert hidden["flow_ids"] == ["02", "01"]


def test_closure_adapter_rejects_bad_graphs_before_calling_kernel():
    class NeverCalled:
        def __getattr__(self, _):
            raise AssertionError("invalid input reached the generated kernel")

    good = {"node_count": 2, "edges": [{"source": 0, "target": 1, "hidden": False}],
            "seeds": {"untrusted_text": [0]}}
    invalid = [
        {**good, "node_count": True},
        {**good, "edges": [{"source": 0, "target": 2, "hidden": False}]},
        {**good, "edges": [{"source": 0, "target": 1, "hidden": 1}]},
        {**good, "seeds": {"untrusted_text": [True]}},
        {**good, "seeds": {"": [0]}},
        {**good, "seeds": {"untrusted_text": [2]}},
    ]
    for episode in invalid:
        with pytest.raises(ValueError):
            evaluate({"episodes": [episode]}, NeverCalled(), NeverCalled())


def test_verified_closure_exhausts_two_node_graphs_and_hidden_seeds():
    from plectis.components.information_flow import closures

    pairs = [(0, 0), (0, 1), (1, 0), (1, 1)]
    episodes = []
    expected = []
    # Each edge is absent, present, or present with a hidden-policy injection.
    for states in product(range(3), repeat=4):
        edges = [{"source": a, "target": b, "hidden": state == 2}
                 for (a, b), state in zip(pairs, states) if state]
        for mask in range(4):
            source_seeds = {node for node in range(2) if mask & (1 << node)}
            episodes.append({"node_count": 2, "edges": edges,
                             "seeds": {"untrusted_text": sorted(source_seeds),
                                       "hidden_policy_claim": sorted(source_seeds)}})
            hidden_seeds = source_seeds | {edge["target"] for edge in edges if edge["hidden"]}
            # On two vertices every reachable vertex is a seed or its direct successor.
            def expected_nodes(initial):
                return sorted(initial | {edge["target"] for edge in edges if edge["source"] in initial})
            expected.append({"untrusted_text": expected_nodes(source_seeds),
                             "hidden_policy_claim": expected_nodes(hidden_seeds)})
    assert closures(episodes) == expected


def test_graph_projection_keeps_duplicate_flow_ids_separate_by_episode():
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input"
    sources = flow.validate_source_documents(json.loads((fixture / "source_documents.json").read_text()))["source_rows"]
    sources += [
        {"source_id": "dup_a", "episode_id": "one", "trust_label": "untrusted_web", "taint_labels": ["untrusted_text", "prompt_injection"]},
        {"source_id": "dup_b", "episode_id": "two", "trust_label": "trusted_user_intent", "taint_labels": ["trusted_instruction"]},
    ]
    graph = json.loads((fixture / "information_flow_graph.json").read_text())
    graph["information_flows"] += [
        {"body_redacted": True, "episode_id": "one", "flow_id": "same",
         "from_source_id": "dup_a", "to_sink_id": "sink_one", "sink_kind": "answer",
         "source_trust_label": "untrusted_web", "taint_labels": ["untrusted_text", "prompt_injection"],
         "sanitization_applied": False, "proposed_action_ref": "read", "privileged_sink": False,
         "policy_verdict": "review"},
        {"body_redacted": True, "episode_id": "two", "flow_id": "same",
         "from_source_id": "dup_b", "to_sink_id": "sink_two", "sink_kind": "answer",
         "source_trust_label": "trusted_user_intent", "taint_labels": ["trusted_instruction"],
         "sanitization_applied": False, "proposed_action_ref": "read", "privileged_sink": False,
         "policy_verdict": "allow"},
    ]
    result = flow.validate_information_flow_graph(graph, sources)
    duplicate_rows = {row["episode_id"]: row for row in result["flow_rows"] if row["flow_id"] == "same"}
    assert result["status"] == "blocked"
    assert "PROMPT_INJECTION_DUPLICATE_FLOW_ID" in {f["error_code"] for f in result["findings"]}
    assert duplicate_rows["one"]["derived_policy_verdict"] == "review"
    assert duplicate_rows["two"]["derived_policy_verdict"] == "allow"
    assert duplicate_rows["one"]["derived_taint_labels"] == ["prompt_injection", "untrusted_text"]
    assert duplicate_rows["two"]["derived_taint_labels"] == ["trusted_instruction"]


def test_duplicate_source_ids_cannot_replace_trust_labels():
    import copy
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input"
    sources = json.loads((fixture / "source_documents.json").read_text())
    original = next(row for row in sources["source_documents"] if row["source_id"] == "src_web_page_injection")
    duplicate = copy.deepcopy(original)
    duplicate.update(trust_label="trusted_user_intent", taint_labels=["trusted_instruction"], instruction_authority=True)
    sources["source_documents"].append(duplicate)
    source_result = flow.validate_source_documents(sources)
    assert source_result["status"] == "blocked"
    assert "PROMPT_INJECTION_DUPLICATE_SOURCE_ID" in {f["error_code"] for f in source_result["findings"]}
    graph = json.loads((fixture / "information_flow_graph.json").read_text())
    graph_result = flow.validate_information_flow_graph(graph, source_result["source_rows"])
    assert graph_result["status"] == "blocked"
    assert "PROMPT_INJECTION_DUPLICATE_SOURCE_ID" in {f["error_code"] for f in graph_result["findings"]}


def test_generated_closure_handles_a_chain_longer_than_python_recursion_limit():
    from plectis.components.information_flow import closures

    episode = {
        "node_count": 1101,
        "edges": [{"source": i, "target": i + 1, "hidden": False} for i in range(1100)],
        "seeds": {"untrusted_text": [0]},
    }
    assert closures([episode]) == [{"untrusted_text": list(range(1101))}]


def test_production_witnesses_match_independent_episode_reachability():
    import random

    rng = random.Random(517)
    nodes = ["n0", "n1", "n2", "n3"]
    sources = {"n0": {"episode_id": "ep00", "taint_labels": ["untrusted_text"]},
               "n1": {"episode_id": "ep01", "taint_labels": ["trusted_instruction"]},
               "n2": {"episode_id": "ep02", "taint_labels": []},
               "n3": {"episode_id": "ep03", "taint_labels": []}}
    rows = []
    for episode in range(32):
        for index in range(7):
            rows.append({"episode_id": f"ep{episode:02d}", "flow_id": f"f{episode:02d}_{index}",
                         "from_source_id": rng.choice(nodes), "to_sink_id": rng.choice(nodes),
                         "sink_kind": "instruction_channel" if rng.randrange(5) == 0 else "answer",
                         "privileged_sink": True, "taint_labels": [], "policy_verdict": ""})
    result, _ = flow._taint_propagation_receipt(rows, sources)
    by_key = {(r["episode_id"], r["flow_id"]): r for r in rows}
    for output in result["flow_path_rows"]:
        episode = output["episode_id"]
        flow_row = by_key[(episode, output["flow_id"])]
        graph = [r for r in rows if r["episode_id"] == episode]
        adjacency = {(r["from_source_id"], r["to_sink_id"]) for r in graph}
        # Floyd-Warshall supplies an independent path oracle, including cycles.
        reachable = {(n, n) for n in nodes} | adjacency
        for middle in nodes:
            reachable |= {(a, b) for a in nodes for b in nodes
                          if (a, middle) in reachable and (middle, b) in reachable}
        source = flow_row["from_source_id"]
        expected = {label for n in nodes for label in sources[n]["taint_labels"]
                    if sources[n]["episode_id"] == episode and (n, source) in reachable}
        if (flow_row["sink_kind"] == "instruction_channel" or
                any(r["sink_kind"] == "instruction_channel" and
                    (r["to_sink_id"], source) in reachable for r in graph)):
            expected.add("hidden_policy_claim")
        assert output["derived_taint_labels"] == sorted(expected)
        for witness in output["taint_witnesses"]:
            path = witness["nodes"]
            edge_ids = witness["flow_ids"]
            assert len(edge_ids) == len(path) - 1
            assert len(path) <= len(nodes) + 2
            for a, b, edge_id in zip(path, path[1:], edge_ids):
                edge = by_key[(episode, edge_id)]
                assert (edge["from_source_id"], edge["to_sink_id"]) == (a, b)
            if witness["origin"] == "source":
                assert sources[path[0]]["episode_id"] == episode
                assert witness["label"] in sources[path[0]]["taint_labels"]
            else:
                seed = by_key[(episode, witness["seed_flow_id"])]
                assert witness["label"] == "hidden_policy_claim"
                assert seed["sink_kind"] == "instruction_channel"
                assert edge_ids[0] == seed["flow_id"]


def test_source_record_from_another_episode_is_blocked_and_not_seeded():
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input"
    sources = flow.validate_source_documents(json.loads((fixture / "source_documents.json").read_text()))["source_rows"]
    graph = json.loads((fixture / "information_flow_graph.json").read_text())
    graph["information_flows"].append({
        "body_redacted": True, "episode_id": "different_episode", "flow_id": "mismatched_episode",
        "from_source_id": "src_web_page_injection", "to_sink_id": "sink_mismatch",
        "sink_kind": "external_action", "source_trust_label": "untrusted_web",
        "taint_labels": ["prompt_injection", "untrusted_text"], "sanitization_applied": False,
        "proposed_action_ref": "action", "privileged_sink": True, "policy_verdict": "block",
    })
    result = flow.validate_information_flow_graph(graph, sources)
    row = next(r for r in result["flow_rows"] if r["flow_id"] == "mismatched_episode")
    assert result["status"] == "blocked"
    assert "PROMPT_INJECTION_SOURCE_EPISODE_MISMATCH" in {f["error_code"] for f in result["findings"]}
    assert row["derived_taint_labels"] == []
    assert row["derived_policy_verdict"] == "allow"


def test_production_propagation_checks_verified_closure_before_policy(monkeypatch):
    """Host witnesses cannot silently replace a missing generated closure."""
    import plectis.components.information_flow as policy

    rows = [{"episode_id": "e", "flow_id": "f", "from_source_id": "a", "to_sink_id": "b",
             "taint_labels": ["untrusted_text"], "policy_verdict": "review"}]
    sources = {"a": {"episode_id": "e", "taint_labels": ["untrusted_text"]}}
    calls = []
    real_closures = policy.closures

    def observed(episodes):
        calls.append(episodes)
        return real_closures(episodes)

    monkeypatch.setattr(policy, "closures", observed)
    result, findings = flow._taint_propagation_receipt(rows, sources)
    assert result["status"] == "pass" and not findings
    assert calls == [[{"node_count": 2, "edges": [{"source": 0, "target": 1, "hidden": False}],
                       "seeds": {"untrusted_text": [0]}}]]

    monkeypatch.setattr(policy, "closures", lambda _episodes: [{"untrusted_text": [0]}])
    with pytest.raises(RuntimeError, match="host witness search does not match verified closure"):
        flow._taint_propagation_receipt(rows, sources)


def test_duplicate_flow_ids_within_episode_preserve_row_diagnostics():
    import json
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[1] / "fixtures/first_wave/indirect_prompt_injection_information_flow_policy_replay/input"
    sources = flow.validate_source_documents(json.loads((fixture / "source_documents.json").read_text()))["source_rows"]
    graph = json.loads((fixture / "information_flow_graph.json").read_text())
    original = next(row for row in graph["information_flows"] if row["flow_id"] == "flow_allow_user_to_summary")
    duplicate = {**original, "from_source_id": "src_web_page_injection", "to_sink_id": "other_sink",
                 "source_trust_label": "untrusted_web", "taint_labels": ["prompt_injection", "untrusted_text"],
                 "policy_verdict": "warn"}
    graph["information_flows"].insert(0, duplicate)
    result = flow.validate_information_flow_graph(graph, sources)
    duplicates = [row for row in result["flow_rows"] if row["flow_id"] == original["flow_id"]]
    assert result["status"] == "blocked"
    assert "PROMPT_INJECTION_DUPLICATE_FLOW_ID" in {row["error_code"] for row in result["findings"]}
    assert [(row["from_source_id"], row["derived_policy_verdict"]) for row in duplicates] == [
        ("src_web_page_injection", "warn"), ("src_user_task", "allow")]
    assert result["derived_policy_verdict_mismatch_count"] == 0


def test_supplied_bundle_out_of_order_taint_changes_exported_result(tmp_path):
    """The public bundle API must analyze supplied edges rather than canonical ones."""
    import json
    from pathlib import Path
    import shutil

    root = Path(__file__).resolve().parents[1]
    canonical = root / "examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle"
    supplied = tmp_path / "supplied_bundle"
    shutil.copytree(canonical, supplied)
    manifest_path = supplied / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for row in manifest["modules"]:
        row["target_ref"] = "microcosm-substrate/" + row["path"]
    manifest_path.write_text(json.dumps(manifest))
    graph_path = supplied / "information_flow_graph.json"
    graph = json.loads(graph_path.read_text())
    by_id = {row["flow_id"]: row for row in graph["information_flows"]}
    by_id["flow_block_web_to_email"]["to_sink_id"] = "src_user_task"
    by_id["flow_allow_user_to_summary"].update(privileged_sink=True, sanitization_applied=False)
    graph_path.write_text(json.dumps(graph))

    result = flow.run_prompt_injection_bundle(supplied, tmp_path / "receipts", command="pytest")
    current = next(row for row in result["flow_rows"] if row["flow_id"] == "flow_allow_user_to_summary")
    assert result["status"] == "blocked"
    assert result["source_module_manifest_status"] == "pass"
    assert result["public_agent_execution_trace"]["status"] == "pass"
    assert current["policy_verdict"] == "allow"
    assert current["derived_policy_verdict"] == "block"
    assert current["derived_taint_labels"] == ["prompt_injection", "trusted_instruction", "untrusted_text"]
    assert ["src_web_page_injection", "src_user_task", "sink_answer_summary"] in current["source_to_sink_paths"]


@pytest.mark.parametrize("tampered", ["adapter", "generated", "manifest"])
def test_cached_bundle_receipt_checks_current_kernel_integrity(tmp_path, monkeypatch, tampered):
    """A warm receipt cannot conceal changed host code or damaged generated bytes."""
    import json
    from pathlib import Path
    import shutil
    from plectis.components import _bridge

    root = Path(__file__).resolve().parents[1]
    canonical = root / "examples/indirect_prompt_injection_information_flow_policy_replay/exported_prompt_injection_flow_bundle"
    components = Path(_bridge.__file__).resolve().parent
    copied = tmp_path / "plectis/components"
    copied.mkdir(parents=True)
    for name in ("__init__.py", "_bridge.py", "_worker.py", "_registry.py"):
        shutil.copy2(components / name, copied / name)
    shutil.copy2(components.parent / "_sealed_kernel.py", copied.parent / "_sealed_kernel.py")
    shutil.copytree(components / "information_flow", copied / "information_flow",
                    ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(_bridge, "__file__", str(copied / "_bridge.py"))

    out = tmp_path / "receipts"
    out.mkdir()
    basis = flow._freshness_basis(canonical, include_negative=False)
    assert basis["component_kernel"]["slug"] == "information_flow"
    cached = {"schema_version": "exported_prompt_injection_flow_bundle_validation_result_v1",
              "organ_id": flow.ORGAN_ID, "status": "pass", "input_mode": "exported_prompt_injection_flow_bundle",
              "command": "pytest", "freshness_basis": basis}
    (out / flow.BUNDLE_RESULT_NAME).write_text(json.dumps(cached))
    assert flow._fresh_prompt_injection_bundle_receipt(canonical, out, command="pytest")["receipt_reused"] is True

    if tampered == "adapter":
        adapter = copied / "information_flow/_adapter.py"
        adapter.write_bytes(adapter.read_bytes() + b"\n# changed trusted adapter\n")
        assert flow._fresh_prompt_injection_bundle_receipt(canonical, out, command="pytest") is None
    else:
        target = copied / "information_flow/_generated" / (
            "InformationFlow.py" if tampered == "generated" else "GENERATED_SHA256.json")
        target.write_bytes(target.read_bytes() + b"\n# invalid generated bytes\n")
        with pytest.raises((ValueError, OSError)):
            flow._fresh_prompt_injection_bundle_receipt(canonical, out, command="pytest")
