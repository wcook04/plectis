#!/usr/bin/env python3
"""Check the replay proof/source binding; --dafny reproves and regenerates it."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
VERSION = "4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2"
GENERATED = frozenset({"ReplayAdmission.py", "module_.py", "__main__.py",
                       "System_/__init__.py", "_dafny/__init__.py"})
SOURCE = "ReplayAdmission.dfy"
MUTANTS = ("negative/MissingCoverageMutant.dfy",
           "negative/StaleInputMutant.dfy")
PROOF = runpy.run_path(str(ROOT / "scripts/check/check_component_kernels.py"))
NEGATIVE_RESULTS = {MUTANTS[0]: {"verified_tasks": 14, "errors": 2},
                    MUTANTS[1]: {"verified_tasks": 13, "errors": 3}}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mutation(source: str, name: str) -> str:
    if name == MUTANTS[0]:
        before = ("    |pending| == 0 ||\n"
                  "    (CountSpec(specs, pending[0].component) == 1 &&\n"
                  "     CountRow(rows, pending[0].component) == 1 &&\n"
                  "     FindGood(rows, pending[0], source) &&\n"
                  "     CheckSpecs(pending[1..], specs, rows, source))")
        after = ("    |pending| == 0 ||\n"
                 "    CheckSpecs(pending[1..], specs, rows, source)"
                 " // MUTANT: components disappear from the coverage check")
    else:
        before = "o.inputBefore > 0 && o.inputBefore == o.inputAfter &&"
        after = "o.inputBefore > 0 && true /* MUTANT: stale input */ &&"
        # RequiredRow is the independent postcondition; mutate only executable
        # RowDecision's second occurrence.
        if source.count(before) != 2:
            raise ValueError("stale-input guard has unexpected source count")
        first = source.index(before)
        second = source.index(before, first + len(before))
        return source[:second] + after + source[second + len(before):]
    if source.count(before) != 1:
        raise ValueError("coverage guard has unexpected source count")
    return source.replace(before, after, 1)


def _source_snapshot(formal: Path, metadata: dict) -> dict[str, bytes]:
    snapshot = {}
    for name in (SOURCE, *MUTANTS):
        expected = (metadata["source_sha256"] if name == SOURCE
                    else metadata["negative_sha256"][name])
        source = PROOF["_source_text"](formal / name).encode("utf-8")
        if hashlib.sha256(source).hexdigest() != expected:
            raise ValueError("formal replay source identity changed: " + name)
        snapshot[name] = source
    source = snapshot[SOURCE].decode("utf-8")
    for name in MUTANTS:
        if snapshot[name].decode("utf-8") != _mutation(source, name):
            raise ValueError("negative replay proof fixture changed: " + name)
    return snapshot


def check_binding(root: Path = ROOT) -> dict:
    formal = root / "formal/replay"
    generated = root / "src/plectis/replay/_generated"
    metadata = PROOF["_read_json"](formal / "metadata.json")
    manifest = PROOF["_read_json"](generated / "GENERATED_SHA256.json")
    if (type(metadata.get("schema_version")) is not int or metadata.get("schema_version") != 1
            or metadata.get("source") != SOURCE
            or metadata.get("negative_sources") != list(MUTANTS)
            or set(metadata["negative_sha256"]) != set(MUTANTS)
            or metadata.get("verified_tasks") != 16
            or metadata.get("negative_results") != NEGATIVE_RESULTS
            or metadata.get("dafny_version") != VERSION
            or metadata.get("generated_python") != manifest
            or set(manifest) != GENERATED):
        raise ValueError("unexpected replay proof metadata or generated inventory")
    _source_snapshot(formal, metadata)
    for name, expected in manifest.items():
        if digest(generated / name) != expected:
            raise ValueError("generated replay Python identity changed: " + name)
    if not (generated / "Dafny-LICENSE.txt").is_file():
        raise ValueError("Dafny runtime licence missing")
    # Inventory and private-copy import discipline are shared with all cores.
    loader = runpy.run_path(str(root / "src/plectis/_sealed_kernel.py"))
    loader["read_kernel_snapshot"](generated, "ReplayAdmission")
    return metadata


def _run(argv: list[str], cwd: Path, env: dict[str, str]):
    return PROOF["_run"](argv, cwd=cwd, env=env)


def reprove(root: Path, dafny_executable: str, metadata: dict) -> None:
    if metadata != check_binding(root):
        raise ValueError("replay metadata changed before proof snapshot")
    sources = _source_snapshot(root / "formal/replay", metadata)
    found = shutil.which(dafny_executable)
    if found is None:
        raise ValueError("Dafny executable not found")
    dafny = str(Path(found).resolve())
    env = os.environ.copy()
    env.setdefault("DOTNET_GCHeapHardLimit", "0x20000000")
    scratch_parent = root / ".microcosm" / "formal-replay"
    scratch_parent.mkdir(parents=True, exist_ok=True)
    version = _run([dafny, "--version"], root, env)
    if version.returncode or version.stdout.strip() != VERSION:
        raise ValueError("replay requires the pinned official Dafny 4.11.0 build")
    with tempfile.TemporaryDirectory(prefix="proof-", dir=scratch_parent) as directory:
        work = Path(directory)
        for name, source in sources.items():
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
        build = _run([dafny, "build", "--target:py", str(work / SOURCE),
                      "--verification-time-limit", "120", "--cores", "1"], work, env)
        PROOF["_proof_result"](build, metadata["verified_tasks"], 0)
        rebuilt = work / "ReplayAdmission-py"
        files = {path.relative_to(rebuilt).as_posix()
                 for path in rebuilt.rglob("*.py")}
        if files != GENERATED:
            raise ValueError("unexpected generated Python file set")
        generated = root / "src/plectis/replay/_generated"
        for name in files:
            if (rebuilt / name).read_bytes() != (generated / name).read_bytes():
                raise ValueError("deployed Python differs from verified build: " + name)
        for name in MUTANTS:
            negative = _run([dafny, "verify", str(work / name),
                             "--verification-time-limit", "120", "--cores", "1"], work, env)
            expected = metadata["negative_results"][name]
            PROOF["_proof_result"](negative, expected["verified_tasks"],
                                   expected["errors"], negative=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dafny", metavar="PATH")
    args = parser.parse_args(argv)
    metadata = check_binding()
    if args.dafny:
        reprove(ROOT, args.dafny, metadata)
        print("Replay kernel: verified, generated bytes match, mutants rejected")
    else:
        print("Replay kernel: hash_binding_only (proof not rerun)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
