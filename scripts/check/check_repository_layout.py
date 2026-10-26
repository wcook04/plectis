#!/usr/bin/env python3
"""Check maintained program placement, using Git's index rather than build trees."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
POLICY = "docs/maintainers/repository-layout.json"
RELEASE_RECEIPT = "receipts/release/release_export_receipt.json"


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"{RELEASE_RECEIPT}: duplicate JSON key {key!r}")
        result[key] = value
    return result


def _invalid_json_constant(value: str) -> None:
    raise ValueError(f"{RELEASE_RECEIPT}: invalid JSON constant {value}")


def _export_inventory_paths(root: Path) -> set[str] | None:
    """Check export metadata for corruption, without authenticating its origin."""
    receipt_path = root / RELEASE_RECEIPT
    if not receipt_path.exists():
        return None
    receipt = json.loads(
        receipt_path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_json_object,
        parse_constant=_invalid_json_constant,
    )
    if not isinstance(receipt, dict):
        raise ValueError(f"{RELEASE_RECEIPT}: invalid release inventory")
    artifact = receipt.get("artifact")
    inventory = receipt.get("inventory_receipt")
    if (
        receipt.get("schema_version") != "microcosm_release_export_receipt_v1"
        or receipt.get("status") != "pass"
        or not isinstance(artifact, dict)
        or artifact.get("mode") != "generated_standalone_folder"
        or not isinstance(inventory, dict)
        or inventory.get("status") != "pass"
        or inventory.get("manifest_policy") != "allowlisted_public_tree"
        or not isinstance(inventory.get("files"), list)
        or not inventory["files"]
    ):
        raise ValueError(f"{RELEASE_RECEIPT}: invalid release inventory")

    paths: set[str] = set()
    file_metadata: dict[str, tuple[int, str, str]] = {}
    for row in inventory["files"]:
        raw = row.get("path") if isinstance(row, dict) else None
        if not isinstance(raw, str):
            raise ValueError(f"{RELEASE_RECEIPT}: invalid inventory path")
        path = PurePosixPath(raw)
        if (
            not raw or path.is_absolute() or ".." in path.parts
            or "\\" in raw or path.as_posix() != raw or raw in paths
        ):
            raise ValueError(f"{RELEASE_RECEIPT}: invalid inventory path {raw!r}")
        size = row.get("size_bytes")
        digest = row.get("sha256")
        mode = row.get("git_mode")
        if (
            type(size) is not int or size < 0
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(mode, str) or mode not in {"100644", "100755"}
        ):
            raise ValueError(f"{RELEASE_RECEIPT}: invalid inventory metadata for {raw!r}")
        paths.add(raw)
        file_metadata[raw] = (size, digest, mode)
    if (
        type(inventory.get("file_count")) is not int
        or type(artifact.get("file_count")) is not int
        or inventory.get("file_count") != len(paths)
        or artifact.get("file_count") != len(paths)
    ):
        raise ValueError(f"{RELEASE_RECEIPT}: inventory count mismatch")
    serialized = json.dumps(inventory["files"], ensure_ascii=True, sort_keys=True).encode("utf-8")
    if artifact.get("artifact_payload_hash_sha256") != hashlib.sha256(serialized).hexdigest():
        raise ValueError(f"{RELEASE_RECEIPT}: inventory hash mismatch")
    for raw, (size, expected_digest, expected_mode) in file_metadata.items():
        path = root / raw
        current = root
        for part in PurePosixPath(raw).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"{RELEASE_RECEIPT}: listed file uses a symlink: {raw}")
        if not path.is_file():
            raise ValueError(f"{RELEASE_RECEIPT}: listed files missing: {raw}")
        actual_mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        if actual_mode != expected_mode:
            raise ValueError(f"{RELEASE_RECEIPT}: listed file mode changed: {raw}")
        digest = hashlib.sha256()
        actual_size = 0
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                actual_size += len(chunk)
                digest.update(chunk)
        if actual_size != size or digest.hexdigest() != expected_digest:
            raise ValueError(f"{RELEASE_RECEIPT}: listed file changed: {raw}")
    return paths


def candidate_paths(root: Path) -> list[str]:
    """Include staged additions, omit staged deletions and ignored local output.

    A source distribution has no Git index. The release receipt records the
    shipped inventory; it is not authenticated against deliberate modification.
    Unlisted cache bytecode is treated as generated after export.
    Never fall back after a Git failure in a checkout, which could hide a failure.
    """
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            check=True, capture_output=True,
        )
        return sorted(set(result.stdout.decode().split("\0")) - {""})
    shipped = _export_inventory_paths(root)
    present = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if shipped is None:
        return sorted(present)
    missing = shipped - present
    if missing:
        raise ValueError(f"{RELEASE_RECEIPT}: listed files missing: {sorted(missing)[:5]}")
    return sorted(
        raw for raw in present
        if raw in shipped
        or not (
            "__pycache__" in PurePosixPath(raw).parts
            and PurePosixPath(raw).suffix in {".pyc", ".pyo"}
        )
    )


def violations(paths: list[str], policy: dict) -> list[str]:
    failures = []
    groups = policy["script_groups"]
    exceptions = policy.get("exceptions", {})
    for raw in paths:
        p = PurePosixPath(raw)
        if raw in exceptions:
            continue
        if p.suffix in {".pyc", ".pyo"}:
            failures.append(f"{raw}: generated bytecode is not source")
        if p.parts[0] == "docs" and p.suffix in {".py", ".js", ".sh"}:
            failures.append(f"{raw}: maintained programs belong in scripts/<role>/")
        if p.parts[0] == "scripts" and p.suffix == ".py":
            if len(p.parts) != 3 or p.parts[1] not in groups:
                failures.append(f"{raw}: choose a declared scripts/<role>/ directory")
            elif p.name.startswith("test_"):
                failures.append(f"{raw}: regression tests belong in tests/")
            elif p.name.startswith("build_") and p.parts[1] not in {"build", "papers"}:
                failures.append(f"{raw}: builders belong in scripts/build/ or scripts/papers/")
            elif p.name.startswith("check_") and p.parts[1] not in {"check", "papers"}:
                failures.append(f"{raw}: checks belong in scripts/check/ or scripts/papers/")
    for required in policy["required_paths"]:
        if required not in paths:
            failures.append(f"{required}: missing required layout owner or entry")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        policy = json.loads((root / POLICY).read_text())
        failures = violations(candidate_paths(root), policy)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Repository layout: fail: {exc}")
        return 1
    for failure in failures:
        print(f"- {failure}")
    print(f"Repository layout: {'fail' if failures else 'pass'}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
