from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import secret_exclusion_scan
from .organs import macro_projection_import_protocol
from .receipts import utc_now, write_json_atomic


ARTIFACT_DIR_NAME = "microcosm-substrate"
RELEASE_RECEIPT_REF = "receipts/release/release_export_receipt.json"
PROJECTION_FRESHNESS_RECEIPT_REF = (
    "receipts/first_wave/macro_projection_import_protocol/"
    "exported_projection_import_bundle_validation_result.json"
)
DEFAULT_INCLUDE_REFS = (
    ".gitignore",
    "AGENTS.md",
    "ANTI_PRINCIPLES.md",
    "AXIOMS.md",
    "CONSTITUTION.md",
    "LICENSE",
    "PRINCIPLES.md",
    "README.md",
    "atlas",
    "bootstrap.sh",
    "core",
    "examples",
    "fixtures",
    "paper_modules",
    "pyproject.toml",
    "receipts",
    "scripts",
    "skills",
    "src",
    "standards",
    "tests",
)
SKIPPED_DIR_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
SKIPPED_ROOT_NAMES = {
    ".DS_Store",
    ".microcosm",
    ".pytest_cache",
    ARTIFACT_DIR_NAME,
}
SKIPPED_FILE_SUFFIXES = {".pyc", ".pyo"}
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ROOT_FORBIDDEN_PREFIXES = (
    ".codex/",
    ".claude/",
    "obsidian/",
    "state/",
    "tools/",
)
STRONG_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*=\s*['\"][^'\"]{12,}['\"]"),
)
HOST_TEMP_ROOT_NEEDLE = "/private/" + "var/folders/"
HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE = HOST_TEMP_ROOT_NEEDLE + "wn/example/"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def _public_role(rel: str) -> str:
    top = rel.split("/", 1)[0]
    if rel.endswith("pyproject.toml"):
        return "package_metadata"
    if rel in {"README.md", "AGENTS.md", "ANTI_PRINCIPLES.md", "AXIOMS.md", "CONSTITUTION.md", "PRINCIPLES.md", "LICENSE"}:
        return "public_entry_document"
    if top == "atlas":
        return "entry_packet"
    if top == "core":
        return "authority_or_registry"
    if top == "examples":
        if "/.microcosm/" in f"/{rel}":
            return "intentional_example_generated_state"
        return "example_evidence"
    if top == "fixtures":
        return "fixture"
    if top == "paper_modules":
        return "public_paper_module"
    if top == "receipts":
        return "receipt_evidence"
    if top == "scripts":
        return "utility_script"
    if top == "skills":
        return "public_skill"
    if top == "src":
        return "runtime_source"
    if top == "standards":
        return "public_standard"
    if top == "tests":
        return "test_or_regression_guard"
    return "public_artifact_member"


def _skip_reason(rel: Path, *, is_dir: bool) -> str | None:
    parts = rel.parts
    if not parts:
        return None
    if parts[0] in SKIPPED_ROOT_NAMES:
        return "root_local_or_nested_release_residue"
    if any(part in SKIPPED_DIR_NAMES for part in parts):
        return "cache_or_build_directory"
    if not is_dir and rel.suffix in SKIPPED_FILE_SUFFIXES:
        return "bytecode_cache"
    if not is_dir and rel.name == ".DS_Store":
        return "os_metadata_file"
    return None


def _source_residue_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in sorted(SKIPPED_ROOT_NAMES):
        candidate = root / name
        if candidate.exists():
            rows.append(
                {
                    "path": name,
                    "status": "excluded",
                    "reason": "root_local_or_nested_release_residue",
                }
            )
    return rows


def _iter_allowed_files(root: Path) -> tuple[list[Path], list[dict[str, str]], list[str]]:
    files: list[Path] = []
    excluded: list[dict[str, str]] = _source_residue_rows(root)
    missing: list[str] = []
    for include_ref in DEFAULT_INCLUDE_REFS:
        source = root / include_ref
        if not source.exists():
            missing.append(include_ref)
            continue
        if source.is_symlink():
            excluded.append(
                {
                    "path": include_ref,
                    "status": "excluded",
                    "reason": "symlink_not_exported",
                }
            )
            continue
        if source.is_file():
            reason = _skip_reason(Path(include_ref), is_dir=False)
            content_reason = (
                _source_receipt_private_path_exclusion(source, root)
                if reason is None
                else None
            )
            if content_reason is not None:
                excluded.append(
                    {"path": include_ref, "status": "excluded", "reason": content_reason}
                )
            elif reason is None:
                files.append(source)
            else:
                excluded.append({"path": include_ref, "status": "excluded", "reason": reason})
            continue
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(root)
            if path.is_symlink():
                excluded.append(
                    {
                        "path": rel.as_posix(),
                        "status": "excluded",
                        "reason": "symlink_not_exported",
                    }
                )
                continue
            reason = _skip_reason(rel, is_dir=path.is_dir())
            if reason is not None:
                if path.is_dir() or path.is_file():
                    excluded.append({"path": rel.as_posix(), "status": "excluded", "reason": reason})
                continue
            if path.is_file():
                content_reason = _source_receipt_private_path_exclusion(path, root)
                if content_reason is not None:
                    excluded.append(
                        {
                            "path": rel.as_posix(),
                            "status": "excluded",
                            "reason": content_reason,
                        }
                    )
                    continue
                files.append(path)
    return files, excluded, missing


def _copy_allowed_files(files: list[Path], *, root: Path, target: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for source in files:
        rel = source.relative_to(root).as_posix()
        destination = target / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        stat = destination.stat()
        inventory.append(
            {
                "path": rel,
                "role": _public_role(rel),
                "size_bytes": stat.st_size,
                "sha256": _sha256_file(destination),
            }
        )
    return sorted(inventory, key=lambda row: row["path"])


def _artifact_payload_hash(inventory: list[dict[str, Any]]) -> str:
    serialized = json.dumps(inventory, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return _sha256_bytes(serialized)


def _read_text_if_small(path: Path, *, max_bytes: int = 2_000_000) -> str | None:
    if path.suffix not in TEXT_SUFFIXES:
        return None
    try:
        if path.stat().st_size > max_bytes:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _source_receipt_private_path_exclusion(path: Path, root: Path) -> str | None:
    rel = path.relative_to(root)
    if not rel.parts or rel.parts[0] != "receipts":
        return None
    text = _read_text_if_small(path)
    if text is None:
        return None
    if root.as_posix() in text:
        return "receipt_absolute_source_root_excluded"
    if HOST_TEMP_ROOT_NEEDLE in text and HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE not in text:
        return "receipt_host_temp_path_excluded"
    return None


def _strong_private_path_hits(target: Path, *, source_root: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    source_root_text = source_root.as_posix()
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(target).as_posix()
        text = _read_text_if_small(path)
        if text is None:
            continue
        if source_root_text and source_root_text in text:
            hits.append({"path": rel, "needle": "<source-root>", "kind": "absolute_source_root"})
        if HOST_TEMP_ROOT_NEEDLE in text and HOST_TEMP_SYNTHETIC_EXAMPLE_NEEDLE not in text:
            hits.append({"path": rel, "needle": HOST_TEMP_ROOT_NEEDLE, "kind": "host_temp_root"})
    return hits


def _strong_secret_hits(target: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(target).as_posix()
        text = _read_text_if_small(path)
        if text is None:
            continue
        for pattern in STRONG_SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(
                    {
                        "path": rel,
                        "pattern": pattern.pattern,
                        "body_in_receipt": False,
                    }
                )
    return hits


def _artifact_residue_violations(target: Path) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in sorted(target.rglob("*")):
        rel = path.relative_to(target)
        rel_text = rel.as_posix()
        parts = rel.parts
        if not parts:
            continue
        if any(rel_text.startswith(prefix) for prefix in ROOT_FORBIDDEN_PREFIXES):
            violations.append({"path": rel_text, "reason": "forbidden_private_root"})
        if parts[0] == ".microcosm":
            violations.append({"path": rel_text, "reason": "root_local_microcosm_state"})
        if parts[0] == ARTIFACT_DIR_NAME:
            violations.append({"path": rel_text, "reason": "nested_self_export"})
        if rel.name == ".DS_Store":
            violations.append({"path": rel_text, "reason": "os_metadata_file"})
        if any(part in {".pytest_cache", "__pycache__"} for part in parts):
            violations.append({"path": rel_text, "reason": "cache_or_bytecode"})
        if rel.suffix in SKIPPED_FILE_SUFFIXES:
            violations.append({"path": rel_text, "reason": "bytecode_cache"})
    return violations


def _expected_sentinel_fixture_path(path_ref: object) -> bool:
    path = str(path_ref)
    return (
        path == "core/private_state_forbidden_classes.json"
        or path.startswith("tests/")
        or "private_state_forbidden_terms.json" in path
        or path.endswith("fixtures/first_wave/pattern_binding_contract/input/reference_capsules.json")
    )


def _expected_bounded_secret_scan_hit(hit: dict[str, Any]) -> bool:
    if hit.get("forbidden_class") == "target_only_not_source":
        return True
    return _expected_sentinel_fixture_path(hit.get("path"))


def _secret_scan(target: Path) -> dict[str, Any]:
    policy_path = target / "core/private_state_forbidden_classes.json"
    if not policy_path.is_file():
        return {
            "status": "blocked",
            "blocking_codes": ["MISSING_SECRET_EXCLUSION_POLICY"],
            "blocking_hit_count": 1,
            "body_in_receipt": False,
        }
    forbidden_classes = secret_exclusion_scan.load_forbidden_classes(policy_path)
    files = [path for path in sorted(target.rglob("*")) if path.is_file()]
    scan = secret_exclusion_scan.scan_paths(
        files,
        forbidden_classes=forbidden_classes,
        source_context="release_artifact",
        display_root=target,
    )
    hits = scan.get("hits") if isinstance(scan.get("hits"), list) else []
    unexpected_hits = [
        hit
        for hit in hits
        if isinstance(hit, dict)
        and not _expected_bounded_secret_scan_hit(hit)
    ]
    if not unexpected_hits:
        return {
            **scan,
            "status": "pass",
            "blocking_hit_count": 0,
            "expected_bounded_hit_count": len(hits),
            "expected_sentinel_hit_count": sum(
                1
                for hit in hits
                if isinstance(hit, dict)
                and _expected_sentinel_fixture_path(hit.get("path"))
            ),
            "unexpected_hit_count": 0,
            "unexpected_hit_paths": [],
        }
    return {
        **scan,
        "status": "blocked",
        "blocking_hit_count": len(unexpected_hits),
        "expected_bounded_hit_count": len(hits) - len(unexpected_hits),
        "expected_sentinel_hit_count": sum(
            1
            for hit in hits
            if isinstance(hit, dict)
            and _expected_sentinel_fixture_path(hit.get("path"))
        ),
        "unexpected_hit_count": len(unexpected_hits),
        "unexpected_hit_paths": sorted(
            str(hit.get("path")) for hit in unexpected_hits if isinstance(hit, dict)
        ),
    }


def _projection_freshness(target: Path) -> dict[str, Any]:
    receipt_path = target / PROJECTION_FRESHNESS_RECEIPT_REF
    if not receipt_path.is_file():
        return {
            "status": "blocked",
            "receipt_ref": PROJECTION_FRESHNESS_RECEIPT_REF,
            "blocking_codes": ["MISSING_PROJECTION_FRESHNESS_RECEIPT"],
            "release_authorized": False,
        }
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    error_codes = payload.get("error_codes")
    if not isinstance(error_codes, list):
        error_codes = []
    bundle_dir = (
        target / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
    )
    runtime_shape: dict[str, Any]
    if bundle_dir.is_dir():
        with tempfile.TemporaryDirectory(prefix="microcosm-projection-freshness-") as tmp:
            validation = macro_projection_import_protocol.run_projection_bundle(
                bundle_dir,
                Path(tmp) / "macro_projection_import_protocol",
                command="release-export projection freshness check",
            )
        validation_error_codes = validation.get("error_codes")
        if not isinstance(validation_error_codes, list):
            validation_error_codes = []
        runtime_shape = {
            "status": "pass"
            if validation.get("status") == "pass" and not validation_error_codes
            else "blocked",
            "source_status": validation.get("status"),
            "error_codes": validation_error_codes,
            "finding_count": len(validation.get("findings") or []),
            "runtime_severance_status": validation.get("runtime_severance_status"),
            "dependency_preflight_gate_status": validation.get(
                "dependency_preflight_gate_status"
            ),
            "organ_lifecycle_coverage_status": validation.get(
                "organ_lifecycle_coverage_status"
            ),
            "macro_runtime_dependency_count": validation.get(
                "macro_runtime_dependency_count"
            ),
        }
    else:
        runtime_shape = {
            "status": "not_run",
            "reason": "exported_projection_import_bundle_not_present",
        }
    status = (
        "pass"
        if payload.get("status") == "pass"
        and not error_codes
        and runtime_shape.get("status") in {"pass", "not_run"}
        else "blocked"
    )
    return {
        "status": status,
        "receipt_ref": PROJECTION_FRESHNESS_RECEIPT_REF,
        "source_status": payload.get("status"),
        "error_codes": error_codes,
        "runtime_shape_validation": runtime_shape,
        "runtime_severance_status": payload.get("runtime_severance_status"),
        "dependency_preflight_gate_status": payload.get("dependency_preflight_gate_status"),
        "organ_lifecycle_coverage_status": payload.get("organ_lifecycle_coverage_status"),
        "macro_runtime_dependency_count": payload.get("macro_runtime_dependency_count"),
        "release_authorized": False,
        "body_in_receipt": False,
    }


def _redact_local(text: str, *, target: Path, source_root: Path) -> str:
    redacted = text.replace(target.as_posix(), "<release-artifact>")
    redacted = redacted.replace(source_root.as_posix(), "<source-root>")
    return redacted


def _run_smoke(target: Path, *, source_root: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    commands = [
        ("hello", ["hello", "<smoke-project>"]),
        ("first_screen", ["first-screen", "<smoke-project>"]),
    ]
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="microcosm-release-smoke-") as tmp:
        project = Path(tmp) / "scratch_project"
        project.mkdir()
        (project / "README.md").write_text("# Smoke Project\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(target / "src")
        for command_id, display_args in commands:
            runtime_args = [
                sys.executable,
                "-m",
                "microcosm_core.cli",
                display_args[0],
                str(project),
            ]
            completed = subprocess.run(
                runtime_args,
                cwd=target,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout = _redact_local(completed.stdout, target=target, source_root=source_root)
            stderr = _redact_local(completed.stderr, target=target, source_root=source_root)
            rows.append(
                {
                    "command_id": command_id,
                    "argv": ["python3", "-m", "microcosm_core.cli", *display_args],
                    "cwd": ARTIFACT_DIR_NAME,
                    "return_code": completed.returncode,
                    "status": "pass" if completed.returncode == 0 else "blocked",
                    "stdout_bytes": len(completed.stdout.encode("utf-8")),
                    "stderr_bytes": len(completed.stderr.encode("utf-8")),
                    "stdout_private_path_hit": "<source-root>" in stdout or "<release-artifact>" in stdout,
                    "stderr_private_path_hit": "<source-root>" in stderr or "<release-artifact>" in stderr,
                    "body_in_receipt": False,
                }
            )
    blocked = [
        row
        for row in rows
        if row["status"] != "pass"
        or row["stdout_private_path_hit"]
        or row["stderr_private_path_hit"]
    ]
    return {
        "status": "pass" if not blocked else "blocked",
        "mode": "outside_source_root_py_module",
        "command_count": len(rows),
        "commands": rows,
        "source_tree_cwd_used": False,
        "source_tree_pythonpath_used": False,
        "release_artifact_pythonpath_used": True,
        "body_in_receipt": False,
    }


def _prepare_target(root: Path, out: Path, *, force: bool) -> Path:
    source_root = root.resolve(strict=True)
    output_root = out.expanduser().resolve(strict=False)
    if _is_relative_to(output_root, source_root):
        raise ValueError("release export output must not be inside the source root")
    target = output_root / ARTIFACT_DIR_NAME
    if target.resolve(strict=False) == source_root:
        raise ValueError("release export target must not be the source root")
    if target.exists():
        if not force:
            raise FileExistsError(f"{target} already exists; pass --force to replace it")
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def build_release_export(
    root: str | Path,
    out: str | Path,
    *,
    force: bool = False,
    run_smoke: bool = True,
    command: str = "release-export",
) -> dict[str, Any]:
    source_root = Path(root).expanduser().resolve(strict=True)
    target = _prepare_target(source_root, Path(out), force=force)
    allowed_files, excluded_rows, missing_include_refs = _iter_allowed_files(source_root)
    inventory = _copy_allowed_files(allowed_files, root=source_root, target=target)
    artifact_payload_hash = _artifact_payload_hash(inventory)
    residue_violations = _artifact_residue_violations(target)
    private_path_hits = _strong_private_path_hits(target, source_root=source_root)
    strong_secret_hits = _strong_secret_hits(target)
    bounded_secret_scan = _secret_scan(target)
    projection_freshness = _projection_freshness(target)
    runnable_receipt = (
        _run_smoke(target, source_root=source_root) if run_smoke else {"status": "not_run"}
    )
    blocking_codes: list[str] = []
    if missing_include_refs:
        blocking_codes.append("RELEASE_EXPORT_INCLUDE_REFS_MISSING")
    if residue_violations:
        blocking_codes.append("RELEASE_EXPORT_ARTIFACT_RESIDUE_PRESENT")
    if private_path_hits:
        blocking_codes.append("RELEASE_EXPORT_PRIVATE_PATH_LEAK")
    if strong_secret_hits:
        blocking_codes.append("RELEASE_EXPORT_STRONG_SECRET_PATTERN")
    if bounded_secret_scan.get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_SECRET_EXCLUSION_SCAN_BLOCKED")
    if projection_freshness.get("status") != "pass":
        blocking_codes.append("RELEASE_EXPORT_PROJECTION_FRESHNESS_BLOCKED")
    if runnable_receipt.get("status") not in {"pass", "not_run"}:
        blocking_codes.append("RELEASE_EXPORT_RUNNABLE_SMOKE_BLOCKED")

    receipt = {
        "schema_version": "microcosm_release_export_receipt_v1",
        "receipt_id": "microcosm_release_export_receipt",
        "generated_at": utc_now(),
        "status": "pass" if not blocking_codes else "blocked",
        "command": command,
        "artifact": {
            "artifact_dir": ARTIFACT_DIR_NAME,
            "mode": "generated_standalone_folder",
            "artifact_payload_hash_sha256": artifact_payload_hash,
            "file_count": len(inventory),
            "payload_bytes": sum(int(row["size_bytes"]) for row in inventory),
            "release_receipt_ref": RELEASE_RECEIPT_REF,
            "receipt_generated_after_inventory": True,
        },
        "inventory_receipt": {
            "status": "pass",
            "manifest_policy": "allowlisted_public_tree",
            "include_refs": list(DEFAULT_INCLUDE_REFS),
            "missing_include_refs": missing_include_refs,
            "file_count": len(inventory),
            "role_counts": {
                role: sum(1 for row in inventory if row["role"] == role)
                for role in sorted({str(row["role"]) for row in inventory})
            },
            "files": inventory,
        },
        "exclusion_receipt": {
            "status": (
                "pass"
                if not residue_violations and not private_path_hits and not strong_secret_hits
                else "blocked"
            ),
            "source_residue_excluded": excluded_rows,
            "artifact_residue_violations": residue_violations,
            "private_path_hits": private_path_hits,
            "strong_secret_hits": strong_secret_hits,
            "bounded_secret_exclusion_scan": {
                "status": bounded_secret_scan.get("status"),
                "blocking_hit_count": bounded_secret_scan.get("blocking_hit_count"),
                "expected_sentinel_hit_count": bounded_secret_scan.get(
                    "expected_sentinel_hit_count"
                ),
                "expected_bounded_hit_count": bounded_secret_scan.get(
                    "expected_bounded_hit_count"
                ),
                "unexpected_hit_count": bounded_secret_scan.get("unexpected_hit_count"),
                "unexpected_hit_paths": bounded_secret_scan.get("unexpected_hit_paths"),
                "body_in_receipt": bounded_secret_scan.get("body_in_receipt"),
                "scan_purpose": bounded_secret_scan.get("scan_purpose"),
                "anti_claim": bounded_secret_scan.get("anti_claim"),
            },
            "body_in_receipt": False,
        },
        "authority_receipt": {
            "status": "pass",
            "release_authorized": False,
            "publish_authorized": False,
            "hosted_launch_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
            "supported_public_mode": "generated_standalone_folder",
            "wheel_install_supported": False,
            "wheel_install_authority": (
                "unsupported_until_package_data_importlib_resources_and_outside_repo_wheel_smoke_pass"
            ),
            "standalone_run_command": (
                "PYTHONPATH=src python3 -m microcosm_core.cli hello <project>"
            ),
        },
        "runnable_receipt": runnable_receipt,
        "projection_freshness_receipt": projection_freshness,
        "blocking_codes": blocking_codes,
        "anti_claim": (
            "This receipt validates export shape for a generated public folder. "
            "It is not release, publication, hosted launch, private-root equivalence, "
            "or complete secret-audit authority."
        ),
        "receipt_paths": [RELEASE_RECEIPT_REF],
    }
    write_json_atomic(target / RELEASE_RECEIPT_REF, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.release_export",
        description="Generate a standalone public Microcosm folder with a bounded release-export receipt.",
    )
    parser.add_argument("--root", default=".", help="microcosm-substrate source root")
    parser.add_argument("--out", required=True, help="output directory that will receive microcosm-substrate/")
    parser.add_argument("--force", action="store_true", help="replace an existing generated artifact directory")
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="write the export and receipts without running the outside-root first-screen smoke",
    )
    args = parser.parse_args(argv)
    command_parts = [
        "python",
        "-m",
        "microcosm_core.release_export",
        "--root",
        "<microcosm-root>",
        "--out",
        "<release-out>",
    ]
    if args.force:
        command_parts.append("--force")
    if args.skip_smoke:
        command_parts.append("--skip-smoke")
    command = " ".join(command_parts)
    receipt = build_release_export(
        args.root,
        args.out,
        force=args.force,
        run_smoke=not args.skip_smoke,
        command=command,
    )
    print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if receipt.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
