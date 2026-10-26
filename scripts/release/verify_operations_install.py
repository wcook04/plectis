#!/usr/bin/env python3
"""Exercise the standalone components using only this Python installation.

Run from any directory with an installed interpreter, for example::

    /path/to/venv/bin/python -I /path/to/verify_operations_install.py --require-compatibility --require-views --require-replay

This check never adds the checkout to Python's import path. Its temporary
checkpoint, journal and SQLite database are removed when the check finishes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import sysconfig
import tempfile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_import_locations() -> dict[str, str]:
    """Reject editable/source imports and accidental legacy-runtime coupling."""
    libraries = {Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        require(not (name == "microcosm_core" or name.startswith("microcosm_core.")),
                "standalone components imported the legacy microcosm_core runtime")
        if name == "plectis" or name.startswith("plectis."):
            filename = getattr(module, "__file__", None)
            require(filename is not None, f"{name} has no concrete installed source")
            origin = Path(filename).resolve()
            require(any(origin.is_relative_to(library) for library in libraries),
                    f"{name} resolved outside this Python installation: {origin}")
            origins[name] = str(origin)
    return origins


def check_generated_locations(modules: list[str]) -> dict[str, str]:
    """Locate the installed sources exercised by the isolated kernel workers.

    Workers execute sealed temporary copies of these sources. They do not add
    the generated modules to this parent process's module namespace.
    """
    libraries = {Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")}
    sources = {}
    for component, kernel in (("plectis.repair", "Repair"),
                              ("plectis.compatibility", "Compatibility"),
                              ("plectis.compatibility", "Replay"),
                              ("plectis.views", "Release"),
                              ("plectis.replay", "ReplayAdmission")):
        if component not in modules:
            continue
        source = (Path(sys.modules[component].__file__).resolve().parent
                  / "_generated" / f"{kernel}.py").resolve()
        require(source.is_file() and any(source.is_relative_to(path) for path in libraries),
                f"generated kernel source is not installed: {source}")
        sources[f"{component}._generated.{kernel}"] = str(source)
    return sources



def component_examples() -> dict[str, str]:
    """Exercise every registered public wrapper with small discriminating cases."""
    from plectis.components._registry import KERNELS
    from plectis.components import (budget_packing, dependency_reachability,
        egress_policy, evidence_diff, information_flow, mcp_authority,
        navigation_metrics, ownership_classification, premise_ranking,
        sandbox_policy, tactic_selection, walkthrough_validation)

    examples = {
        "budget_packing", "dependency_reachability", "egress_policy",
        "evidence_diff", "information_flow", "mcp_authority", "navigation_metrics",
        "ownership_classification", "premise_ranking", "sandbox_policy",
        "tactic_selection", "walkthrough_validation",
    }
    require(set(KERNELS) == examples, "component smoke cases do not cover the registered kernels")

    require(budget_packing.pack({"sizes": [6, 6, 4, 0], "budget": 10}) ==
            {"decisions": [True, False, True, True], "total": 10}, "budget packing failed")
    require(dependency_reachability.dependents(
        [["x", "b"], ["b", "c"], ["c", "x"]], ["x", "absent"])
        == [["b", "c", "x"], []], "dependency reachability failed")
    egress = egress_policy.evaluate({"text": "i ran a command", "groups": [["i ran"], ["approved"]],
                                     "policy": True})
    require(egress == {"matches": [["i ran"], []], "violations": [True], "red": True},
            "egress policy failed")
    diff = evidence_diff.diff_evidence([{"ledger_id": "shared"}, {"ledger_id": "extra"}],
                                       [{"ledger_id": "shared"}, {"ledger_id": "missed"}])
    require(diff["overlap_ledger_ids"] == ["shared"] and diff["extra_ledger_ids"] == ["extra"]
            and diff["missed_ledger_ids"] == ["missed"], "evidence partition failed")
    flags = [{"hidden": True, "untrusted": False, "privileged": False, "sanitized": False},
             {"hidden": False, "untrusted": False, "privileged": False, "sanitized": False}]
    require(information_flow.verdicts(flags) == ["block", "allow"], "information-flow decisions failed")
    episode = {"node_count": 3,
               "edges": [{"source": 0, "target": 1, "hidden": True},
                         {"source": 1, "target": 2, "hidden": False}],
               "seeds": {"untrusted_text": [0]}}
    require(information_flow.closures([episode]) == [
        {"hidden_policy_claim": [1, 2], "untrusted_text": [0, 1, 2]}],
        "information-flow propagation failed")
    write = {"declared": True, "scope": "scope/read", "broad": False, "credential": False,
             "forbiddenKey": False, "untrustedInstruction": False, "live": False,
             "finalOnly": False, "effect": "write", "approval": "approval/a", "ledger": "ledger/a",
             "rollback": "rollback/a", "bodySafe": True, "privateSafe": True,
             "fieldsPresent": True, "toolClass": "write_side_effect",
             "argumentHash": "hash/a", "sourceCapsule": "source/a",
             "instructionSplit": "split/a", "coldReplay": "replay/a"}
    read = {**write, "effect": "none", "toolClass": "readonly_lookup"}
    untrusted = {**write, "effect": "none", "toolClass": "untrusted_result"}
    authority = mcp_authority.evaluate([write, read, untrusted], [{**write, "declared": False}])
    require(authority["accepted"] is True and authority["write_count"] == 1
            and authority["untrusted_count"] == 1 and authority["negative_faults"][0][0] is True,
            "MCP authority decision failed")
    missing_citation = mcp_authority.evaluate([
        {**write, "sourceCapsule": ""}, read, untrusted], [])
    require(missing_citation["accepted"] is False
            and missing_citation["positive_faults"][0][9] is True,
            "MCP authority accepted an empty source citation")
    nav = navigation_metrics.evaluate({"expected": ["skills:*"], "selected": ["skills:a", "other"],
        "timeout": False, "error": True, "scent_fail": False, "forbidden": False,
        "wall": 10, "budget": 100})
    require(nav["found"] == [True] and nav["relevant_count"] == 1 and nav["decision"] == 2,
            "navigation metrics failed")
    ownership = ownership_classification.classify({"paths": [{"id": 7, "generated": True}],
        "claims": [{"path": 7, "live": False}, {"path": 7, "live": True}]})
    require(ownership == {"rows": [{"owner_index": 1, "kind": 2}],
                          "classification": 2, "action": 11},
            "ownership classification failed to prefer a later live claim")
    ranking = premise_ranking.rank({"query_counts": [2], "candidates": [
        {"eligible": True, "id_rank": 0, "counts": [3], "bonus": True},
        {"eligible": True, "id_rank": 1, "counts": [1], "bonus": False},
        {"eligible": False, "id_rank": 2, "counts": [9], "bonus": True}]})
    require(ranking == [[0, 3], [1, 1]], "premise ranking failed")
    safe = {"risk_class": "low_risk_public_fixture_mutation", "action_kind": "filesystem_write",
            "requested_capability": "public_fixture_write", "source_trust_label": "trusted_user_request"}
    decisions = sandbox_policy.evaluate([safe, {**safe, "source_trust_label": "unknown"}])
    require(decisions == [["allow", "rule:public_fixture_write_with_diff_receipt"],
                          ["block", "rule:sandbox_policy_fail_closed_unrecognized_action"]],
            "sandbox policy failed")
    candidates = [{"id": "a", "known": True, "available": False, "allowed": True},
                  {"id": "b", "known": True, "available": True, "allowed": True}]
    require(tactic_selection.select({"preferences": ["a", "b"], "candidates": candidates}) == [1, 1],
            "tactic selection failed")
    steps = [{"commands": [f"command-{i % 4}"], "inspect_refs": ["inspect"],
              "evidence_refs": [f"evidence-{i % 4}"]} for i in range(5)]
    require(walkthrough_validation.validate(steps, time_budget_minutes=10) ==
            {"accepted": True, "command_count": 4, "evidence_count": 4},
            "walkthrough validation failed")
    require(walkthrough_validation.validate(steps, time_budget_minutes=0)["accepted"] is False,
            "walkthrough accepted a nonpositive time budget")
    require(walkthrough_validation.validate(steps, time_budget_minutes=11)["accepted"] is False,
            "walkthrough accepted a time budget above ten minutes")
    steps[0]["inspect_refs"] = []
    require(walkthrough_validation.validate(steps, time_budget_minutes=10)["accepted"] is False,
            "walkthrough accepted a step without an inspection reference")
    return {name: "passed" for name in sorted(examples)}


def check_component_kernel_locations() -> tuple[dict[str, str], dict[str, str]]:
    """Use the installed sealed loader to verify its registered kernel inventories."""
    from plectis._sealed_kernel import read_kernel_snapshot
    from plectis.components._registry import KERNELS

    libraries = {Path(sysconfig.get_path(key)).resolve() for key in ("purelib", "platlib")}
    sources, manifests = {}, {}
    for slug, kernel in sorted(KERNELS.items()):
        package = importlib.import_module(f"plectis.components.{slug}")
        generated = Path(package.__file__).resolve().parent / "_generated"
        source = (generated / f"{kernel}.py").resolve()
        manifest = (generated / "GENERATED_SHA256.json").resolve()
        for path in (source, manifest):
            require(path.is_file() and any(path.is_relative_to(lib) for lib in libraries),
                    f"generated component file is not installed: {path}")
        # This is the same pinned inventory/hash check used by the actual worker.
        read_kernel_snapshot(generated, kernel)
        sources[f"plectis.components.{slug}._generated.{kernel}"] = str(source)
        manifests[slug] = str(manifest)
    return sources, manifests


def check_component_formal_resources() -> dict[str, dict[str, str]]:
    """Bind installed component proof resources to the reviewed generated bytes.

    This is a retained-evidence check. It does not rerun Dafny or reproduce its
    generated output; those checks belong to ``check_component_kernels.py``.
    """
    from plectis._sealed_kernel import read_kernel_snapshot
    from plectis.components._registry import KERNELS

    data = Path(sysconfig.get_path("data")).resolve()
    root = data / "share/plectis/formal/components"
    require(root.is_dir() and root.resolve().is_relative_to(data)
            and all(not path.is_symlink() for path in (root, *root.parents)
                    if path.is_relative_to(data)), "installed component formal resources are missing or nonlocal")
    require({path.name for path in root.iterdir() if path.is_dir()} == set(KERNELS),
            "installed formal component inventory differs from the registered kernels")
    result = {}
    for slug, kernel in sorted(KERNELS.items()):
        formal = root / slug
        require(not formal.is_symlink(), f"installed formal component is a symlink: {slug}")
        for path in formal.rglob("*"):
            require(not path.is_symlink() and (path.is_file() or path.is_dir()),
                    f"invalid installed formal resource: {path}")
        metadata_path = formal / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        require(type(metadata) is dict and type(metadata.get("schema_version")) is int
                and metadata.get("schema_version") == 1 and metadata.get("slug") == slug
                and metadata.get("module") == kernel and metadata.get("source") == kernel + ".dfy",
                f"invalid installed component metadata: {slug}")
        package = importlib.import_module(f"plectis.components.{slug}")
        generated = Path(package.__file__).resolve().parent / "_generated"
        snapshot = read_kernel_snapshot(generated, kernel)
        require(metadata.get("generated_python") == {
            name: hashlib.sha256(content).hexdigest() for name, content in snapshot.items()},
            f"installed formal metadata differs from reviewed generated bytes: {slug}")
        negatives = metadata.get("negative_sources")
        negative_hashes = metadata.get("negative_sha256")
        require(type(negatives) is list and bool(negatives)
                and all(type(name) is str and re.fullmatch(r"negative/[A-Za-z][A-Za-z0-9_]*\.dfy", name)
                        for name in negatives) and len(set(negatives)) == len(negatives)
                and type(negative_hashes) is dict and set(negative_hashes) == set(negatives),
                f"invalid installed negative proof inventory: {slug}")
        source_hashes = {metadata["source"]: metadata.get("source_sha256"), **negative_hashes}
        expected = {"README.md", "metadata.json", *source_hashes}
        require({path.relative_to(formal).as_posix() for path in formal.rglob("*") if path.is_file()}
                == expected, f"incomplete or unexpected installed formal resources: {slug}")
        for relative, digest in source_hashes.items():
            require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest)
                    and hashlib.sha256((formal / relative).read_bytes()).hexdigest() == digest,
                    f"installed formal source identity changed: {slug}:{relative}")
        result[slug] = {"metadata": str(metadata_path), "source": str(formal / metadata["source"]),
                        "evidence": "retained_hashes_checked"}
    return result


def repair_example(directory: Path) -> dict:
    from plectis.repair import RepairSession, Task

    def graph(version: str, *, external: bool = True):
        tasks = [
            Task("observations", code_id="install-check/observations", version="1",
                 inputs=[2, 3], contract="json-v1", environment="stdlib",
                 freshness="frozen-v1", replayable=True, fn=lambda inputs, deps: inputs),
            Task("score", code_id="install-check/score", version=version,
                 deps=("observations",), inputs=int(version), contract="json-v1",
                 environment="stdlib", freshness="frozen-v1", replayable=True,
                 fn=lambda inputs, deps: sum(deps[0]) * inputs),
        ]
        if external:
            tasks.append(Task("export", code_id="install-check/export", version="1",
                              deps=("score",), contract="json-v1", environment="local-file",
                              freshness="frozen-v1", replayable=False))
        return tasks

    checkpoint = directory / "checkpoint.json"
    first = RepairSession(graph("1"), checkpoint=checkpoint)
    initial = first.run(first.plan())
    require(initial.outputs["score"] == 5 and initial.blocked == ("export",),
            "repair did not compute the first score and block the external action")
    changed = RepairSession(graph("2"), checkpoint=checkpoint)
    updated = changed.run(changed.plan())
    require(updated.reused == ("observations",) and updated.executed == ("score",)
            and updated.outputs["score"] == 10,
            "repair did not retain observations when the scoring rule changed")
    attempt = changed.begin_effect("export")
    changed.mark_unknown(attempt, "acknowledgement unavailable")
    restarted = RepairSession(graph("2", external=False), checkpoint=checkpoint)
    result = restarted.run(restarted.plan())
    require(not result.settled and result.unresolved_effects == (
        {"attempt": attempt, "task": "export", "status": "unknown"},),
        "repair lost the unresolved external action after restart and graph removal")
    return {"reused": list(updated.reused), "recomputed": list(updated.executed),
            "score": updated.outputs["score"], "unknown_effect_retained": True}


def publish_example(directory: Path) -> dict:
    from plectis.publish import IdempotencyConflict, PublishStore, StaleTicket

    database = directory / "publications.sqlite"
    with PublishStore(database) as store:
        store.create("report", "input-v1", "score-v1")
        original = store.grant("report", "worker")
        old = store.publish(original, "old-operation", b"score=5")
        require(old.status == "published", "the first publication did not commit")
        store.change_identity("report", "input-v1", "score-v2")
        current = store.grant("report", "worker")
        try:
            store.publish(original, "late-operation", b"score=5")
        except StaleTicket:
            pass
        else:
            raise RuntimeError("publish accepted a stale worker's new operation")
        historical = store.publish(original, "old-operation", b"score=5")
        require(historical.status == "replayed" and store.read_current("report") is None,
                "an exact historical retry acquired current publication authority")
        try:
            store.publish(original, "old-operation", b"different bytes")
        except IdempotencyConflict:
            pass
        else:
            raise RuntimeError("publish accepted changed bytes for a committed operation")
        store.publish(current, "current-operation", b"score=10")
    with PublishStore(database) as restarted:
        require(restarted.read_current("report").payload == b"score=10",
                "the current publication did not survive reopening the database")
    return {"stale_worker": "rejected", "historical_retry": historical.status,
            "changed_retry": "rejected", "current_payload": "score=10"}


def compatibility_example() -> dict:
    from plectis.compatibility import check_certificate, check_counterexample, compare

    approved = {"name": "approved", "initial": "ready", "inputs": ["read"],
                "states": {"ready": {"read": {"next": "ready", "output": "ok"}}}}
    candidate = {**approved, "name": "candidate"}
    accepted = compare(approved, candidate)
    require(accepted["accepted"] is True
            and check_certificate(approved, candidate, accepted["certificate"]),
            "compatibility did not accept and independently check matching behaviour")
    renamed = {**candidate, "name": "changed-identity"}
    require(check_certificate(approved, renamed, accepted["certificate"]) is False,
            "compatibility accepted a certificate for a different model identity")
    broken = {**candidate,
              "states": {"ready": {"read": {"next": "ready", "output": "broken"}}}}
    rejected = compare(approved, broken)
    require(rejected["accepted"] is False and rejected["continuation"] == ["read"]
            and rejected["reason"] == "output_mismatch",
            "compatibility did not expose the changed observable output")
    require(check_counterexample(approved, broken, rejected["continuation"]) is True,
            "compatibility did not independently check its counterexample")
    require(check_counterexample(approved, candidate, rejected["continuation"]) is False,
            "compatibility accepted a stale counterexample after the discrepancy was removed")
    for word in ([], ["unknown"]):
        require(check_counterexample(approved, broken, word) is False,
                "compatibility accepted a word without an observable discrepancy")
    missing = {**candidate, "states": {"ready": {}}}
    require(check_counterexample(approved, missing, ["read"]) is True,
            "compatibility did not check a missing required input")
    return {"matching_behaviour": "accepted", "certificate_identity_bound": True,
            "changed_output": "rejected", "continuation": rejected["continuation"],
            "counterexample_checked": True, "stale_counterexample_rejected": True,
            "missing_required_input_checked": True}


def views_example() -> dict:
    from plectis.views import InvalidInput, RejectedPlan, compile_public, run_public, run_public_batch

    schema = {"version": 1, "fields": [
        {"name": "title", "type": "text", "visibility": "public"},
        {"name": "approved", "type": "flag", "visibility": "public"},
        {"name": "private_note", "type": "text", "visibility": "private"},
        {"name": "embargo", "type": "flag", "visibility": "private"},
    ]}

    def emit(value: dict, channel: str = "public") -> dict:
        return {"emit": {"channel": channel, "value": value}}

    plan = {"seq": [emit({"input": "title"}), {"seq": [
        {"if": {"condition": {"input": "embargo"},
                "then": emit({"input": "private_note"}, "internal"),
                "else": {"skip": True}}},
        {"if": {"condition": {"input": "approved"},
                "then": emit({"literal": "approved"}),
                "else": emit({"literal": "needs review"})}},
    ]}]}
    compiled = compile_public(plan, schema)
    require(compiled.public_fields == ("title", "approved")
            and compiled.read_fields == ("title", "approved"),
            "views did not retain exactly the declared public reads")
    public_plan = json.dumps(compiled.public_plan)
    require("private_note" not in public_plan and "embargo" not in public_plan,
            "views retained a private read in its public plan")
    row = {"title": "Report A", "approved": True}
    trace = run_public(compiled, row)
    require(trace == ("Report A", "approved"), "views changed the public report output")
    require(run_public_batch(compiled, [row, {"title": "Report B", "approved": False}])
            == (("Report A", "approved"), ("Report B", "needs review")),
            "views did not preserve the public batch order and conditional output")
    unsafe_plans = (
        emit({"input": "private_note"}),
        {"if": {"condition": {"input": "embargo"},
                "then": emit({"literal": "visible"}), "else": {"skip": True}}},
    )
    for unsafe in unsafe_plans:
        try:
            compile_public(unsafe, schema)
        except RejectedPlan:
            pass
        else:
            raise RuntimeError("views accepted public output dependent on private data")
    try:
        run_public(compiled, {**row, "private_note": "synthetic private value"})
    except InvalidInput:
        pass
    else:
        raise RuntimeError("views accepted private record values at its public-only boundary")
    return {"public_trace": list(trace), "private_reads_removed": True,
            "explicit_flow": "rejected", "private_control": "rejected",
            "private_record_values": "rejected"}


def replay_example() -> dict:
    """Exercise installed admission on explicit observations and adverse changes."""
    from plectis.replay import accept
    from hashlib import sha256

    def digest(label):
        return sha256(label.encode()).hexdigest()

    spec = {"component_id": "component", "input_ref": "input.json",
            "evidence_class": "bounded_check", "claim_digest": digest("claim-v1"), "native_kind": 0}
    observation = {"component_id": "component", "runner_component_id": "component",
                   "receipt_component_id": "component", "input_ref": "input.json",
                   "evidence_class": "bounded_check", "claim_digest": digest("claim-v1"),
                   "source_before": digest("source-v1"), "source_after": digest("source-v1"),
                   "input_before": digest("input-v1"), "input_after": digest("input-v1"),
                   "runner_payload_digest": digest("payload-v1"), "receipt_payload_digest": digest("payload-v1"),
                   "receipt_digest": digest("receipt-v1"), "runner_status": "pass",
                   "receipt_status": "pass", "runner_verdict": "pass", "receipt_verdict": "pass",
                   "runner_native_kind": 0, "receipt_native_kind": 0, "receipt_present": True}
    require(accept([spec], digest("source-v1"), [observation]), "replay rejected matching observations")
    require(not accept([spec], digest("source-v1"), []), "replay accepted missing coverage")
    require(not accept([spec], digest("source-v1"), [observation, observation]),
            "replay accepted duplicate observations")
    for field in ("receipt_component_id", "claim_digest", "source_after", "input_after",
                  "receipt_payload_digest"):
        require(not accept([spec], digest("source-v1"), [{**observation, field: digest("different")}]),
                "replay accepted changed " + field)
    return {"matching_observations": "accepted", "missing_or_duplicate": "rejected",
            "changed_identity_claim_source_input_payload": "rejected"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-compatibility", action="store_true",
                        help="also require and exercise the installed compatibility component")
    parser.add_argument("--require-views", action="store_true",
                        help="also require and exercise the installed public views component")
    parser.add_argument("--require-replay", action="store_true",
                        help="also require and exercise the installed replay admission core")
    parser.add_argument("--require-formal-resources", action="store_true",
                        help="also check the installed component source, mutant and metadata resources")
    args = parser.parse_args(argv)
    try:
        require(bool(sys.flags.isolated), "run this check with python -I")
        modules = ["plectis.repair", "plectis.publish"]
        if args.require_compatibility:
            modules.append("plectis.compatibility")
        if args.require_views:
            modules.append("plectis.views")
        if args.require_replay:
            modules.append("plectis.replay")
        for module in modules:
            importlib.import_module(module)
        check_import_locations()
        with tempfile.TemporaryDirectory(prefix="plectis-operations-") as temporary:
            directory = Path(temporary)
            result = {"status": "passed", "repair": repair_example(directory),
                      "publish": publish_example(directory), "components": component_examples()}
            if args.require_compatibility:
                result["compatibility"] = compatibility_example()
            if args.require_views:
                result["views"] = views_example()
        if args.require_replay:
            result["replay"] = replay_example()
        component_sources, component_manifests = check_component_kernel_locations()
        result["installed_modules"] = check_import_locations()
        result["generated_sources"] = {**check_generated_locations(modules), **component_sources}
        result["component_manifests"] = component_manifests
        if args.require_formal_resources:
            result["component_formal_resources"] = check_component_formal_resources()
    except Exception as error:
        print(f"operations install check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
