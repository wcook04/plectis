#!/usr/bin/env python3
"""Check Repair's source binding; optionally rebuild its complete Dafny proof.

The default checks retained source/generated hashes only. Supply --dafny to
verify, regenerate and compare the deployed Python, then reject the negative
proof fixture. No prover is needed to use the installed Repair operation.
"""
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
GENERATED_FILES = frozenset({
    "Repair.py", "module_.py", "__main__.py",
    "System_/__init__.py", "_dafny/__init__.py",
})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_binding(root: Path, generated: Path) -> dict:
    formal = root / "formal/repair"
    metadata = json.loads((formal / "metadata.json").read_text())
    manifest = json.loads((generated / "GENERATED_SHA256.json").read_text())
    if (metadata["dafny_version"] != VERSION
            or set(manifest) != GENERATED_FILES
            or metadata["generated_python"] != manifest):
        raise ValueError("unexpected toolchain or generated-file manifest")
    for name, key in (("Repair.dfy", "source_sha256"),
                      ("negative/RepairPropagationMutant.dfy", "negative_source_sha256")):
        if digest(formal / name) != metadata[key]:
            raise ValueError("formal source identity changed: " + name)
    for name, expected in manifest.items():
        if digest(generated / name) != expected:
            raise ValueError("generated Python identity changed: " + name)
    if not (generated / "Dafny-LICENSE.txt").is_file():
        raise ValueError("Dafny runtime licence is missing")
    # Check the whole importable inventory and the loader's reviewed byte pins.
    # Hashing the named .py files alone misses a same-named package shadow.
    loader = runpy.run_path(str(ROOT / "src/plectis/_sealed_kernel.py"))
    loader["read_kernel_snapshot"](generated, "Repair")
    return {"source_sha256": metadata["source_sha256"],
            "negative_source_sha256": metadata["negative_source_sha256"],
            "generated_python": manifest}


def run(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            check=False, timeout=180)
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def reprove(root: Path, generated: Path, executable: str) -> dict:
    found = shutil.which(executable)
    if found is None:
        raise ValueError("Dafny executable not found: " + executable)
    dafny = str(Path(found).resolve())
    env = os.environ.copy()
    env.setdefault("DOTNET_GCHeapHardLimit", "0x20000000")
    formal = root / "formal/repair"
    version = run([dafny, "--version"], cwd=formal, env=env)
    if version.returncode or version.stdout.strip() != VERSION:
        raise ValueError("replay requires the exact pinned Dafny 4.11.0 build")
    with tempfile.TemporaryDirectory(prefix="plectis-repair-proof-") as directory:
        work = Path(directory)
        shutil.copyfile(formal / "Repair.dfy", work / "Repair.dfy")
        build = run([dafny, "build", "--target:py", str(work / "Repair.dfy"),
                     "--verification-time-limit", "30", "--cores", "1"],
                    cwd=work, env=env)
        if build.returncode or "21 verified, 0 errors" not in build.stdout:
            raise ValueError("complete clean proof/build failed")
        rebuilt = work / "Repair-py"
        files = {p.relative_to(rebuilt).as_posix() for p in rebuilt.rglob("*.py")}
        if files != GENERATED_FILES:
            raise ValueError("compiler generated an unexpected file set")
        for name in files:
            if (rebuilt / name).read_bytes() != (generated / name).read_bytes():
                raise ValueError("deployed Python differs from verified build: " + name)
        mutation = run([dafny, "verify",
                        str(formal / "negative/RepairPropagationMutant.dfy"),
                        "--verification-time-limit", "30", "--cores", "1"],
                       cwd=work, env=env)
        if mutation.returncode != 4 or "19 verified, 3 errors" not in mutation.stdout:
            raise ValueError("negative soundness fixture did not fail as expected")
    return {"dafny_version": VERSION, "clean_verified_tasks": 21, "clean_errors": 0,
            "negative_verified_tasks": 19, "negative_errors": 3,
            "regenerated_python_byte_identical": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--generated-root", type=Path)
    parser.add_argument("--dafny", help="Official pinned Dafny 4.11.0 executable")
    args = parser.parse_args()
    root = args.root.resolve()
    generated = (args.generated_root or root / "src/plectis/repair/_generated").resolve()
    try:
        binding = check_binding(root, generated)
        proof = reprove(root, generated, args.dafny) if args.dafny else {}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "fail", "error": str(error)}))
        return 1
    print(json.dumps({"status": "pass", "mode": "formal_replay" if proof else "hash_binding_only",
                      **binding, **proof,
                      "authority_ceiling": "supplied topological DAG decision core",
                      "anti_claim": "No proof of dependency completeness, host, callbacks, storage or external effects.",
                      "secret_exclusion_scan": "not_performed_by_this_checker",
                      "receipt_paths": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
