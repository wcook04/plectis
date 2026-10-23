#!/usr/bin/env python3
"""Exercise the standalone components using only this Python installation.

Run from any directory with an installed interpreter, for example::

    /path/to/venv/bin/python -I /path/to/verify_operations_install.py --require-compatibility

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
    from plectis.compatibility import check_certificate, compare

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
    return {"matching_behaviour": "accepted", "certificate_identity_bound": True,
            "changed_output": "rejected", "continuation": rejected["continuation"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-compatibility", action="store_true",
                        help="also require and exercise the installed compatibility component")
    args = parser.parse_args(argv)
    try:
        require(bool(sys.flags.isolated), "run this check with python -I")
        modules = ["plectis.repair", "plectis.publish"]
        if args.require_compatibility:
            modules.append("plectis.compatibility")
        for module in modules:
            importlib.import_module(module)
        check_import_locations()
        with tempfile.TemporaryDirectory(prefix="plectis-operations-") as temporary:
            directory = Path(temporary)
            result = {"status": "passed", "repair": repair_example(directory),
                      "publish": publish_example(directory)}
            if args.require_compatibility:
                result["compatibility"] = compatibility_example()
        result["installed_modules"] = check_import_locations()
    except Exception as error:
        print(f"operations install check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
