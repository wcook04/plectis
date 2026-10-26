#!/usr/bin/env python3
"""Check registered component proof bindings; --dafny also reproves and rebuilds.

Hash-only mode checks retained evidence and reviewed generated-code inventory;
it does not claim that the Dafny proof has just been rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
VERSION = "4.11.0+fcb2042d6d043a2634f0854338c08feeaaaf4ae2"
SLUG = re.compile(r"[a-z][a-z0-9_]*\Z")
MODULE = re.compile(r"[A-Z][A-Za-z0-9_]*\Z")
NEGATIVE = re.compile(r"negative/[A-Za-z][A-Za-z0-9_]*\.dfy\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
PROOF_SUMMARY = re.compile(
    r"^Dafny program verifier finished with (\d+) verified, (\d+) errors?\s*$",
    re.MULTILINE,
)
INCOMPLETE_PROOF = re.compile(
    r"timed? out|time ?outs?|inconclusive|out of (?:memory|resource)|"
    r"verification (?:was )?(?:skipped|disabled)|not verified",
    re.IGNORECASE,
)
PROOF_FAILURE = re.compile(
    r"could not be proved|might not hold|might not decrease|"
    r"possible violation of postcondition|index out of range|"
    r"possible division by zero|divisor must be non-zero|"
    r"array may be null|target object may be null",
    re.IGNORECASE,
)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate metadata key: " + key)
        result[key] = value
    return result


def _constant(_value):
    raise ValueError("non-finite metadata value")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("non-finite metadata number")
    return result


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object,
                      parse_constant=_constant, parse_float=_float)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value, *, positive=False):
    return type(value) is int and (value > 0 if positive else value >= 0)


def _mutation(source: str, declaration: dict) -> str:
    if type(declaration) is not dict or set(declaration) != {
        "before", "after", "occurrence", "expected_occurrences"
    }:
        raise ValueError("invalid mutation declaration")
    before, after = declaration["before"], declaration["after"]
    occurrence, count = declaration["occurrence"], declaration["expected_occurrences"]
    if (type(before) is not str or not before or type(after) is not str or before == after
            or not _integer(occurrence) or not _integer(count, positive=True)
            or source.count(before) != count or occurrence >= count):
        raise ValueError("mutation target count or replacement invalid")
    start = 0
    for _ in range(occurrence + 1):
        start = source.index(before, start)
        if _ != occurrence:
            start += len(before)
    return source[:start] + after + source[start + len(before):]


def _source_tokens(source: str) -> str:
    """Remove Dafny comments/literals without hiding following executable tokens."""
    output = []
    i = 0
    while i < len(source):
        if source.startswith("//", i):
            end = source.find("\n", i + 2)
            i = len(source) if end < 0 else end
            output.append(" ")
        elif source.startswith("/*", i):
            depth = 1
            i += 2
            while depth and i < len(source):
                if source.startswith("/*", i):
                    depth += 1
                    i += 2
                elif source.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise ValueError("unterminated formal source comment")
            output.append(" ")
        elif source.startswith('@"', i) or source[i] == '"':
            verbatim = source.startswith('@"', i)
            i += 2 if verbatim else 1
            while i < len(source):
                if verbatim and source.startswith('""', i):
                    i += 2
                elif not verbatim and source[i] == "\\":
                    i += 2
                elif source[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("unterminated formal source string")
            output.append(" ")
        else:
            # Apostrophes are also legal in identifiers; consume only complete
            # single-character/escape literals, never text between prime names.
            character = re.match(r"'(?:\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|.)|[^'\\\n])'",
                                 source[i:]) if source[i] == "'" else None
            if character:
                i += len(character.group())
                output.append(" ")
            else:
                output.append(source[i])
                i += 1
    return "".join(output)


def _source_text(path: Path, *, includes=()) -> str:
    """Read a self-contained source within the reviewed proof policy.

    This gate rejects explicit trust/verification escapes and unpinned includes.
    It is not a parser or a proof that preconditions are consistent; theorem
    statements and mutation locations still require mathematical review.
    """
    if path.is_symlink() or not path.is_file():
        raise ValueError("formal source must be a local regular file: " + str(path))
    # The returned text is also used by hash-bound immutable proof snapshots.
    # Preserve CRLF bytes instead of universal-newline normalization.
    with path.open(encoding="utf-8", newline="") as stream:
        source = stream.read()
    if (type(includes) is not tuple
            or any(type(name) is not str for name in includes)
            or len(includes) != len(set(includes))):
        raise ValueError("invalid reviewed formal include inventory")
    policy_source = source
    if includes:
        # Legacy Compatibility has one independently hash-bound dependency.
        # Permit only complete, literal, exactly enumerated directives; after
        # removing them the ordinary token policy still rejects every include.
        directive = re.compile(r'^[ \t]*include[ \t]+"([^"\\\n]*)"[ \t]*(?://[^\n]*)?$',
                               re.MULTILINE)
        found = directive.findall(source)
        if sorted(found) != sorted(includes):
            raise ValueError("formal include inventory differs from reviewed targets")
        policy_source = directive.sub("", source)
    tokens = _source_tokens(policy_source)
    # Prefix attributes rewrite to legacy proof escapes. Unknown classic
    # attributes may suppress checks too; only reviewed unfolding fuel is used.
    attributes = re.findall(r"\{\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", tokens)
    if (re.search(r"\b(?:assume|include)\b", tokens)
            or "@" in tokens
            or any(attribute != "fuel" for attribute in attributes)
            or re.search(r"\bdecreases\s*\*", tokens)):
        raise ValueError("unsafe or unpinned formal source directive: " + str(path))
    return source


def _proof_result(result, verified: int, errors: int, *, negative=False) -> None:
    """Accept one complete verifier summary and only genuine proof failures."""
    summaries = PROOF_SUMMARY.findall(result.stdout)
    error_lines = [line for line in result.stdout.splitlines() if "Error:" in line]
    if (not _integer(verified) or not _integer(errors)
            or (not negative and (verified == 0 or errors != 0 or error_lines))
            or (negative and errors == 0)
            or result.returncode != (4 if negative else 0)
            or len(summaries) != 1
            or tuple(map(int, summaries[0])) != (verified, errors)
            or INCOMPLETE_PROOF.search(result.stdout)
            or (negative and (len(error_lines) != errors or any(
                not PROOF_FAILURE.search(line) for line in error_lines)))):
        raise ValueError("incomplete or unexpected Dafny proof diagnostic")


def _directories(path: Path) -> set[str]:
    if not path.is_dir() or path.is_symlink():
        raise ValueError("missing or invalid component directory: " + str(path))
    result = set()
    for item in path.iterdir():
        if item.is_symlink():
            raise ValueError("symlink in component inventory: " + str(item))
        if item.is_dir() and item.name != "__pycache__":
            result.add(item.name)
    return result


def discover(root: Path) -> dict[str, str]:
    path = root / "src/plectis/components/_registry.py"
    kernels = runpy.run_path(str(path)).get("KERNELS")
    if type(kernels) is not dict or not kernels:
        raise ValueError("component kernel registry is empty or invalid")
    if (any(type(s) is not str or not SLUG.fullmatch(s) or type(n) is not str
            or not MODULE.fullmatch(n) for s, n in kernels.items())
            or len(set(kernels.values())) != len(kernels)):
        raise ValueError("invalid or duplicate registered component identity")
    for relative in ("formal/components", "src/plectis/components"):
        actual = _directories(root / relative)
        if actual != set(kernels):
            raise ValueError(f"component directory inventory mismatch: {relative}: {sorted(actual ^ set(kernels))}")
    return kernels


def check_binding(root: Path, slug: str, module: str) -> dict:
    if not SLUG.fullmatch(slug) or not MODULE.fullmatch(module):
        raise ValueError("invalid registered component identity")
    formal = root / "formal/components" / slug
    package = root / "src/plectis/components" / slug
    generated = package / "_generated"
    if (package.is_symlink() or not package.is_dir()
            or any(path.is_symlink() or not path.is_file()
                   for path in (package / "__init__.py", package / "_adapter.py"))):
        raise ValueError("component package or adapter missing or nonlocal: " + slug)
    if not (formal / "README.md").is_file():
        raise ValueError("component proof README missing: " + slug)
    metadata = _read_json(formal / "metadata.json")
    manifest = _read_json(generated / "GENERATED_SHA256.json")
    expected = {module + ".py", "module_.py", "__main__.py",
                "System_/__init__.py", "_dafny/__init__.py"}
    if (type(metadata) is not dict or type(metadata.get("schema_version")) is not int
            or metadata.get("schema_version") != 1
            or metadata.get("slug") != slug or metadata.get("module") != module
            or metadata.get("source") != module + ".dfy"
            or metadata.get("dafny_version") != VERSION
            or not _integer(metadata.get("verified_tasks"), positive=True)
            or type(manifest) is not dict or set(manifest) != expected
            or metadata.get("generated_python") != manifest
            or any(type(v) is not str or not SHA256.fullmatch(v) for v in manifest.values())):
        raise ValueError("invalid component metadata or generated inventory: " + slug)
    source_path = formal / metadata["source"]
    source_hash = metadata.get("source_sha256")
    if type(source_hash) is not str or not SHA256.fullmatch(source_hash) or _digest(source_path) != source_hash:
        raise ValueError("component formal source identity changed: " + slug)
    negative = metadata.get("negative_sources")
    negative_hash = metadata.get("negative_sha256")
    negative_results = metadata.get("negative_results")
    mutations = metadata.get("mutations")
    if (type(negative) is not list or not negative
            or any(type(n) is not str or not NEGATIVE.fullmatch(n) for n in negative)
            or len(set(negative)) != len(negative)
            or any(type(x) is not dict or set(x) != set(negative)
                   for x in (negative_hash, negative_results, mutations))):
        raise ValueError("invalid negative proof inventory: " + slug)
    actual_negative = _directories(formal)  # no undiscovered extra negative directories
    if actual_negative != {"negative"}:
        raise ValueError("unexpected formal component directories: " + slug)
    negatives = formal / "negative"
    if {p.name for p in negatives.iterdir()} != {Path(n).name for n in negative}:
        raise ValueError("negative proof file inventory mismatch: " + slug)
    source = _source_text(source_path)
    for name in negative:
        expected_hash = negative_hash[name]
        result = negative_results[name]
        if (type(expected_hash) is not str or not SHA256.fullmatch(expected_hash)
                or _digest(formal / name) != expected_hash
                or _source_text(formal / name) != _mutation(source, mutations[name])
                or type(result) is not dict or set(result) != {"verified_tasks", "errors"}
                or not _integer(result["verified_tasks"]) or not _integer(result["errors"], positive=True)):
            raise ValueError("invalid source-linked negative proof: " + slug + ":" + name)
    for name, expected_hash in manifest.items():
        if _digest(generated / name) != expected_hash:
            raise ValueError("generated component bytes changed: " + slug + ":" + name)
    if not (generated / "Dafny-LICENSE.txt").is_file():
        raise ValueError("Dafny runtime licence missing: " + slug)
    loader = runpy.run_path(str(root / "src/plectis/_sealed_kernel.py"))
    loader["read_kernel_snapshot"](generated, module)
    return metadata


def _run(argv: list[str], *, cwd: Path, env: dict[str, str]):
    print("Dafny command: " + json.dumps(argv), flush=True)
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                check=False, timeout=240)
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        print(partial, end="" if partial.endswith("\n") else "\n", flush=True)
        raise ValueError("Dafny process timed out before complete proof evidence") from error
    print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
    return result


def reprove(root: Path, slug: str, module: str, metadata: dict, executable: str) -> None:
    found = shutil.which(executable)
    if found is None:
        raise ValueError("Dafny executable not found")
    dafny = str(Path(found).resolve())
    env = os.environ.copy()
    env.setdefault("DOTNET_GCHeapHardLimit", "0x20000000")
    version = _run([dafny, "--version"], cwd=root, env=env)
    if version.returncode or version.stdout.strip() != VERSION:
        raise ValueError("component proof requires pinned Dafny 4.11.0")
    formal = root / "formal/components" / slug
    generated = root / "src/plectis/components" / slug / "_generated"
    with tempfile.TemporaryDirectory(prefix="plectis-component-proof-") as directory:
        work = Path(directory)
        # Verify the same retained bytes that were bound, including mutants;
        # later cooperative source edits cannot change this job's proof inputs.
        snapshots = {name: (formal / name).read_bytes() for name in
                     [metadata["source"], *metadata["negative_sources"]]}
        expected_hashes = {metadata["source"]: metadata["source_sha256"],
                           **metadata["negative_sha256"]}
        for name, data in snapshots.items():
            if hashlib.sha256(data).hexdigest() != expected_hashes[name]:
                raise ValueError("formal source changed before reproof: " + slug + ":" + name)
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        build = _run([dafny, "build", "--target:py", str(work / metadata["source"]),
                      "--verification-time-limit", "120", "--cores", "1"], cwd=work, env=env)
        _proof_result(build, metadata["verified_tasks"], 0)
        rebuilt = work / (Path(metadata["source"]).stem + "-py")
        files = {p.relative_to(rebuilt).as_posix() for p in rebuilt.rglob("*.py")}
        if files != set(metadata["generated_python"]):
            raise ValueError("unexpected rebuilt Python inventory: " + slug)
        for name in files:
            if (rebuilt / name).read_bytes() != (generated / name).read_bytes():
                raise ValueError("generated Python differs from verified build: " + slug + ":" + name)
        for name in metadata["negative_sources"]:
            negative = _run([dafny, "verify", str(work / name),
                             "--verification-time-limit", "120", "--cores", "1"], cwd=work, env=env)
            expected = metadata["negative_results"][name]
            _proof_result(negative, expected["verified_tasks"], expected["errors"], negative=True)
    check_binding(root, slug, module)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--component", help="Check one registered component")
    parser.add_argument("--dafny", metavar="PATH", help="Reprove with pinned Dafny 4.11.0")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    kernels = discover(root)
    if args.component and args.component not in kernels:
        raise ValueError("component is not registered")
    selected = [args.component] if args.component else sorted(kernels)
    for slug in selected:
        metadata = check_binding(root, slug, kernels[slug])
        if args.dafny:
            reprove(root, slug, kernels[slug], metadata, args.dafny)
            print(f"{slug}: verified, generated bytes match, source-linked mutants rejected")
        else:
            print(f"{slug}: hash_binding_only (proof not rerun)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
