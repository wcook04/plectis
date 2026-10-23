#!/usr/bin/env python3
"""Exercise the standalone components using only this Python installation.

Run from any directory with an installed interpreter, for example::

    /path/to/venv/bin/python -I /path/to/verify_operations_install.py --require-compatibility --require-views

This check never adds the checkout to Python's import path. Its temporary
checkpoint, journal and SQLite database are removed when the check finishes.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
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
                              ("plectis.views", "Release")):
        if component not in modules:
            continue
        source = (Path(sys.modules[component].__file__).resolve().parent
                  / "_generated" / f"{kernel}.py").resolve()
        require(source.is_file() and any(source.is_relative_to(path) for path in libraries),
                f"generated kernel source is not installed: {source}")
        sources[f"{component}._generated.{kernel}"] = str(source)
    return sources


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-compatibility", action="store_true",
                        help="also require and exercise the installed compatibility component")
    parser.add_argument("--require-views", action="store_true",
                        help="also require and exercise the installed public views component")
    args = parser.parse_args(argv)
    try:
        require(bool(sys.flags.isolated), "run this check with python -I")
        modules = ["plectis.repair", "plectis.publish"]
        if args.require_compatibility:
            modules.append("plectis.compatibility")
        if args.require_views:
            modules.append("plectis.views")
        for module in modules:
            importlib.import_module(module)
        check_import_locations()
        with tempfile.TemporaryDirectory(prefix="plectis-operations-") as temporary:
            directory = Path(temporary)
            result = {"status": "passed", "repair": repair_example(directory),
                      "publish": publish_example(directory)}
            if args.require_compatibility:
                result["compatibility"] = compatibility_example()
            if args.require_views:
                result["views"] = views_example()
        result["installed_modules"] = check_import_locations()
        result["generated_sources"] = check_generated_locations(modules)
    except Exception as error:
        print(f"operations install check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
