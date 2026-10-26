#!/usr/bin/env python3
"""Check the replay proof/source binding; --dafny reproves and regenerates it."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def check_binding(root: Path = ROOT) -> dict:
    formal = root / "formal/replay"
    generated = root / "src/plectis/replay/_generated"
    metadata = json.loads((formal / "metadata.json").read_text())
    manifest = json.loads((generated / "GENERATED_SHA256.json").read_text())
    if (metadata.get("schema_version") != 1
            or metadata.get("source") != SOURCE
            or metadata.get("negative_sources") != list(MUTANTS)
            or metadata.get("dafny_version") != VERSION
            or metadata.get("generated_python") != manifest
            or set(manifest) != GENERATED):
        raise ValueError("unexpected replay proof metadata or generated inventory")
    if digest(formal / SOURCE) != metadata["source_sha256"]:
        raise ValueError("formal replay source identity changed")
    source = (formal / SOURCE).read_text()
    for name in MUTANTS:
        if (digest(formal / name) != metadata["negative_sha256"][name]
                or (formal / name).read_text() != _mutation(source, name)):
            raise ValueError("negative replay proof fixture changed: " + name)
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
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            check=False, timeout=240)
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def reprove(root: Path, dafny_executable: str, metadata: dict) -> None:
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
        shutil.copyfile(root / "formal/replay" / SOURCE, work / SOURCE)
        build = _run([dafny, "build", "--target:py", str(work / SOURCE),
                      "--verification-time-limit", "120", "--cores", "1"], work, env)
        if (build.returncode or
                f"{metadata['verified_tasks']} verified, 0 errors" not in build.stdout):
            raise ValueError("formal replay verification/build failed")
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
            negative = _run([dafny, "verify", str(root / "formal/replay" / name),
                             "--verification-time-limit", "120", "--cores", "1"], work, env)
            expected = metadata["negative_results"][name]
            summary = (f"{expected['verified_tasks']} verified, "
                       f"{expected['errors']} errors")
            if negative.returncode != 4 or summary not in negative.stdout:
                raise ValueError("negative replay specification was not rejected: " + name)


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
