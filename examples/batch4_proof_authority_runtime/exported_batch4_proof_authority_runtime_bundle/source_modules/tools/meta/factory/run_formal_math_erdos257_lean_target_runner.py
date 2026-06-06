#!/usr/bin/env python3
"""Run an exact Lean target check for the Erdos257 period-noncollapse project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.factory import run_formal_math_erdos257_period_noncollapse_strike as strike


SCHEMA_VERSION = "formal_math_erdos257_lean_target_runner_receipt_v1"
CHECK_SCHEMA_VERSION = "formal_math_erdos257_lean_target_runner_check_v0"
OWNER_ID = "formal_math_erdos257_lean_target_runner"
CLAIM_BOUNDARY = (
    "exact_generated_target_typecheck_and_axiom_audit_only_not_universal_theorem"
)
ALLOWED_FOUNDATIONAL_AXIOMS = ("Classical.choice", "Quot.sound", "propext")
RECEIPT_PATH = strike.LEAN_TARGET_RUNNER_RECEIPT_PATH
FRONTIER_CONVEYOR_RECEIPT_PATH = strike.FRONTIER_CONVEYOR_RECEIPT_PATH
PUBLIC_PACKET_PATH = Path(
    "docs/formal_math/generated_erdos257_period_noncollapse_reproducibility_packet.md"
)
GENERATED_MODULE_IMPORT = "Erdos257PeriodNoncollapse.GeneratedCertificates"
NAMESPACE = "Erdos257PeriodNoncollapse"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _run(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    proc = subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "args": list(args),
        "cwd": _rel(cwd),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _strike_state(repo_root: Path) -> dict[str, Any]:
    return _read_json(_repo_path(strike.STRIKE_PATH, repo_root=repo_root))


def _lean_microkernel(strike_state: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = strike_state.get("lean_microkernel")
    if isinstance(direct, Mapping):
        return direct
    proof_kernel = strike_state.get("proof_kernel_split")
    if isinstance(proof_kernel, Mapping) and isinstance(
        proof_kernel.get("lean_microkernel"), Mapping
    ):
        return proof_kernel["lean_microkernel"]
    return {}


def _latest_target(strike_state: Mapping[str, Any]) -> str:
    microkernel = _lean_microkernel(strike_state)
    latest = microkernel.get("latest_real_target_binding")
    if isinstance(latest, Mapping) and latest.get("target_id"):
        return str(latest["target_id"])
    residual = microkernel.get("explicit_target_runner_residual")
    if isinstance(residual, Mapping) and residual.get("latest_real_target_binding"):
        return str(residual["latest_real_target_binding"])
    raise ValueError("could not resolve latest real target binding")


def _namespaced(theorem: str) -> str:
    return theorem if theorem.startswith(f"{NAMESPACE}.") else f"{NAMESPACE}.{theorem}"


def _unnamespaced(theorem: str) -> str:
    return theorem.split(".")[-1]


def _target_source(theorem: str) -> str:
    namespaced = _namespaced(theorem)
    return "\n".join(
        [
            f"import {GENERATED_MODULE_IMPORT}",
            "",
            f"#check {namespaced}",
            f"#print axioms {namespaced}",
            "",
        ]
    )


def _parse_axiom_dependencies(stdout: str) -> list[str]:
    if "does not depend on any axioms" in stdout:
        return []
    match = re.search(r"depends on axioms:\s*\[(?P<body>.*?)\]", stdout, re.S)
    if not match:
        return []
    body = match.group("body")
    return [
        item.strip()
        for item in body.replace("\n", " ").split(",")
        if item.strip()
    ]


def _source_scan(repo_root: Path) -> dict[str, Any]:
    pattern = re.compile(r"\b(sorry|admit|axiom)\b")
    hits: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for source_ref in strike.LEAN_MICROKERNEL_SOURCE_FILES:
        path = _repo_path(source_ref, repo_root=repo_root)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        file_hits = [
            {
                "source_ref": source_ref.as_posix(),
                "line": line_number,
                "token": match.group(1),
            }
            for line_number, line in enumerate(text.splitlines(), start=1)
            for match in pattern.finditer(line)
        ]
        hits.extend(file_hits)
        rows.append(
            {
                "source_ref": source_ref.as_posix(),
                "present": path.is_file(),
                "sha256": _sha256_file(path),
                "banned_token_hit_count": len(file_hits),
            }
        )
    return {
        "status": "PASS" if not hits and all(row["present"] for row in rows) else "FAIL",
        "banned_token_hit_count": len(hits),
        "hits": hits,
        "source_files": rows,
    }


def _target_line(repo_root: Path, theorem: str) -> int | None:
    needle = f"theorem {_unnamespaced(theorem)} "
    for source_ref in strike.LEAN_MICROKERNEL_SOURCE_FILES:
        path = _repo_path(source_ref, repo_root=repo_root)
        if not path.is_file():
            continue
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.startswith(needle):
                return line_number
    return None


def _targets_from_frontier_conveyor_receipt(
    *, repo_root: Path = REPO_ROOT
) -> list[str]:
    receipt = _read_json(_repo_path(FRONTIER_CONVEYOR_RECEIPT_PATH, repo_root=repo_root))
    targets: list[str] = []
    for action in receipt.get("applied_actions", []):
        if not isinstance(action, Mapping):
            continue
        if action.get("action_class") != "bind_semantic_spec":
            continue
        target = action.get("expected_period_target")
        if isinstance(target, str) and target:
            targets.append(_unnamespaced(target))
    if not targets:
        raise ValueError(
            "frontier conveyor receipt has no bind_semantic_spec actions with "
            "expected_period_target"
        )
    return targets


def _git_value(args: Sequence[str], repo_root: Path) -> str | None:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _skipped_module_build_result(project_root: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "args": ["lake", "build", GENERATED_MODULE_IMPORT],
        "cwd": _rel(project_root, repo_root=repo_root),
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "skipped": True,
    }


def _run_module_build(
    *,
    repo_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    return _run(
        ["lake", "build", GENERATED_MODULE_IMPORT],
        cwd=project_root,
        timeout_seconds=timeout_seconds,
    )


def _module_build_receipt(build_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if build_result["returncode"] == 0 else "FAIL",
        "command": "cd formal_math/erdos257_period_noncollapse && lake build Erdos257PeriodNoncollapse.GeneratedCertificates",
        "returncode": build_result["returncode"],
        "stdout_sha256": _sha256_text(str(build_result["stdout"])),
        "stderr_sha256": _sha256_text(str(build_result["stderr"])),
    }


def build_receipt(
    *,
    target_theorem: str | None,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    strike_state = _strike_state(repo_root)
    target = target_theorem or _latest_target(strike_state)
    namespaced = _namespaced(target)
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)

    build_result = (
        _skipped_module_build_result(project_root, repo_root)
        if skip_build
        else _run_module_build(repo_root=repo_root, timeout_seconds=timeout_seconds)
    )

    lean_source = _target_source(target)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", prefix="erdos257_target_runner_", suffix=".lean", delete=False
    ) as handle:
        handle.write(lean_source)
        temp_path = Path(handle.name)
    try:
        lean_result = _run(
            ["lake", "env", "lean", temp_path.as_posix()],
            cwd=project_root,
            timeout_seconds=timeout_seconds,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    stdout = str(lean_result["stdout"])
    axiom_dependencies = _parse_axiom_dependencies(stdout)
    allowed = set(ALLOWED_FOUNDATIONAL_AXIOMS)
    custom_axioms = [dep for dep in axiom_dependencies if dep not in allowed]
    sorry_like = any(dep in {"sorryAx", "Lean.sorryAx"} for dep in axiom_dependencies)
    target_check_status = (
        "PASS" if lean_result["returncode"] == 0 and namespaced in stdout else "FAIL"
    )
    print_axioms_status = (
        "PASS"
        if lean_result["returncode"] == 0
        and ("depends on axioms:" in stdout or "does not depend on any axioms" in stdout)
        else "FAIL"
    )
    axiom_dependency_class = (
        "none"
        if not axiom_dependencies
        else "foundational_axioms_only"
        if not custom_axioms and not sorry_like
        else "custom_or_sorry_axiom_dependency"
    )
    source_scan = _source_scan(repo_root)
    status = (
        "PASS"
        if build_result["returncode"] == 0
        and lean_result["returncode"] == 0
        and target_check_status == "PASS"
        and print_axioms_status == "PASS"
        and axiom_dependency_class in {"none", "foundational_axioms_only"}
        and source_scan["status"] == "PASS"
        else "FAIL"
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "owner_id": OWNER_ID,
        "generated_at": _utc_now(),
        "status": status,
        "audit_mode": "single_target",
        "target_count": 1,
        "target_theorem": _unnamespaced(target),
        "namespaced_target_theorem": namespaced,
        "target_line": _target_line(repo_root, target),
        "target_check_status": target_check_status,
        "print_axioms_status": print_axioms_status,
        "axiom_dependency_class": axiom_dependency_class,
        "axiom_dependencies": axiom_dependencies,
        "allowed_foundational_axioms": list(ALLOWED_FOUNDATIONAL_AXIOMS),
        "custom_axiom_dependencies": custom_axioms,
        "sorry_like_axiom_dependency_detected": sorry_like,
        "module_import": GENERATED_MODULE_IMPORT,
        "lean_source_sha256": _sha256_text(lean_source),
        "module_build": _module_build_receipt(build_result),
        "target_runner": {
            "status": "PASS" if lean_result["returncode"] == 0 else "FAIL",
            "command": (
                "cd formal_math/erdos257_period_noncollapse && "
                "lake env lean <generated-target-runner-temp-file>"
            ),
            "returncode": lean_result["returncode"],
            "stdout": stdout,
            "stderr": lean_result["stderr"],
            "stdout_sha256": _sha256_text(stdout),
            "stderr_sha256": _sha256_text(str(lean_result["stderr"])),
        },
        "static_placeholder_scan": source_scan,
        "source_refs": {
            "strike_json": strike.STRIKE_PATH.as_posix(),
            "generated_certificates": strike.DIRECT_PRIME_GENERATED_LEAN_MODULE.as_posix(),
            "generated_certificate_modules": [
                path.as_posix()
                for path in strike.LEAN_MICROKERNEL_SOURCE_FILES
                if "GeneratedCertificates" in path.as_posix()
            ],
            "receipt": RECEIPT_PATH.as_posix(),
            "public_packet": PUBLIC_PACKET_PATH.as_posix(),
        },
        "git": {
            "head": _git_value(["rev-parse", "HEAD"], repo_root),
            "origin_main": _git_value(["rev-parse", "origin/main"], repo_root),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "non_claims": [
            "not_universal_finite_theorem",
            "not_primitive_divisor_existence",
            "not_arbitrary_generated_row_existence",
            "not_erdos_257_solution",
            "not_publication_authority",
        ],
    }


def _target_audit_row(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "target_theorem": receipt.get("target_theorem"),
        "namespaced_target_theorem": receipt.get("namespaced_target_theorem"),
        "target_line": receipt.get("target_line"),
        "target_check_status": receipt.get("target_check_status"),
        "print_axioms_status": receipt.get("print_axioms_status"),
        "axiom_dependency_class": receipt.get("axiom_dependency_class"),
        "axiom_dependencies": receipt.get("axiom_dependencies", []),
        "custom_axiom_dependencies": receipt.get("custom_axiom_dependencies", []),
        "sorry_like_axiom_dependency_detected": receipt.get(
            "sorry_like_axiom_dependency_detected"
        ),
        "status": receipt.get("status"),
    }


def build_receipt_from_frontier_conveyor_receipt(
    *,
    skip_build: bool,
    timeout_seconds: int,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    targets = _targets_from_frontier_conveyor_receipt(repo_root=repo_root)
    project_root = _repo_path(strike.LEAN_MICROKERNEL_ROOT, repo_root=repo_root)
    build_result = (
        _skipped_module_build_result(project_root, repo_root)
        if skip_build
        else _run_module_build(repo_root=repo_root, timeout_seconds=timeout_seconds)
    )
    target_receipts = [
        build_receipt(
            target_theorem=target,
            skip_build=True,
            timeout_seconds=timeout_seconds,
            repo_root=repo_root,
        )
        for target in targets
    ]
    target_rows = [_target_audit_row(receipt) for receipt in target_receipts]
    primary = dict(target_receipts[-1])
    all_targets_foundational_or_none = all(
        row.get("status") == "PASS"
        and row.get("target_check_status") == "PASS"
        and row.get("print_axioms_status") == "PASS"
        and row.get("axiom_dependency_class") in {"none", "foundational_axioms_only"}
        and not row.get("custom_axiom_dependencies")
        and not row.get("sorry_like_axiom_dependency_detected")
        for row in target_rows
    )
    primary.update(
        {
            "audit_mode": "frontier_conveyor_applied_direct_targets",
            "target_count": len(target_rows),
            "targets": target_rows,
            "all_targets_foundational_or_none": all_targets_foundational_or_none,
            "frontier_conveyor_receipt_ref": FRONTIER_CONVEYOR_RECEIPT_PATH.as_posix(),
            "module_build": _module_build_receipt(build_result),
            "status": (
                "PASS"
                if build_result["returncode"] == 0
                and primary.get("status") == "PASS"
                and all_targets_foundational_or_none
                else "FAIL"
            ),
        }
    )
    return primary


def _target_runner_receipt_summary(
    receipt: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(receipt, Mapping):
        return None
    target_rows = [
        row for row in receipt.get("targets", []) if isinstance(row, Mapping)
    ]
    target_theorems = [
        str(row["target_theorem"])
        for row in target_rows
        if isinstance(row.get("target_theorem"), str)
    ]
    if not target_theorems and isinstance(receipt.get("target_theorem"), str):
        target_theorems = [str(receipt["target_theorem"])]
    return {
        "schema_version": receipt.get("schema_version"),
        "generated_at": receipt.get("generated_at"),
        "status": receipt.get("status"),
        "audit_mode": receipt.get("audit_mode"),
        "target_count": receipt.get("target_count"),
        "target_theorem": receipt.get("target_theorem"),
        "target_theorems": target_theorems,
        "target_check_status": receipt.get("target_check_status"),
        "print_axioms_status": receipt.get("print_axioms_status"),
        "axiom_dependency_class": receipt.get("axiom_dependency_class"),
        "all_targets_foundational_or_none": receipt.get(
            "all_targets_foundational_or_none"
        ),
        "frontier_conveyor_receipt_ref": receipt.get(
            "frontier_conveyor_receipt_ref"
        ),
        "claim_boundary": receipt.get("claim_boundary"),
    }


def _with_receipt_lineage(
    receipt: Mapping[str, Any],
    existing: Mapping[str, Any] | None,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    enriched = dict(receipt)
    lineage: list[dict[str, Any]] = []
    summary = _target_runner_receipt_summary(existing)
    if summary:
        lineage.append(summary)
    if isinstance(existing, Mapping):
        for row in existing.get("recent_target_runner_receipt_lineage", []):
            if isinstance(row, Mapping):
                lineage.append(dict(row))
            if len(lineage) >= limit:
                break
    enriched["previous_target_runner_receipt_summary"] = (
        lineage[0] if lineage else None
    )
    enriched["recent_target_runner_receipt_lineage"] = lineage[:limit]
    return enriched


def _markdown_list(items: Sequence[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "`none`"


def build_public_packet(receipt: Mapping[str, Any]) -> str:
    target = str(receipt["target_theorem"])
    axiom_dependencies = [str(item) for item in receipt.get("axiom_dependencies", [])]
    custom_axioms = [str(item) for item in receipt.get("custom_axiom_dependencies", [])]
    target_rows = [
        row
        for row in receipt.get("targets", [])
        if isinstance(row, Mapping)
    ]
    tranche_section: list[str] = []
    if target_rows:
        tranche_section = [
            "## Conveyor-Applied Direct Target Audit",
            "",
            f"- Audit mode: `{receipt.get('audit_mode')}`",
            f"- Target count: `{receipt.get('target_count')}`",
            f"- All targets foundational-or-none: `{receipt.get('all_targets_foundational_or_none')}`",
            f"- Frontier conveyor receipt: `{receipt.get('frontier_conveyor_receipt_ref')}`",
            "",
        ]
        for row in target_rows:
            row_axioms = [str(item) for item in row.get("axiom_dependencies", [])]
            tranche_section.extend(
                [
                    f"- `{row.get('target_theorem')}`: `#check` `{row.get('target_check_status')}`, `#print axioms` `{row.get('print_axioms_status')}`, axiom class `{row.get('axiom_dependency_class')}`, dependencies {_markdown_list(row_axioms)}",
                ]
            )
        tranche_section.append("")

    lineage_rows = [
        row
        for row in receipt.get("recent_target_runner_receipt_lineage", [])
        if isinstance(row, Mapping)
    ]
    lineage_section: list[str] = []
    if lineage_rows:
        lineage_section = [
            "## Recent Target-Runner Audit Lineage",
            "",
            "These rows summarize prior receipt-applied audits before the current live receipt was refreshed. They are provenance rows, not proof authority.",
            "",
        ]
        for row in lineage_rows:
            row_targets = [
                str(item)
                for item in row.get("target_theorems", [])
                if isinstance(item, str)
            ]
            lineage_section.extend(
                [
                    f"- `{row.get('generated_at')}`: audit `{row.get('audit_mode')}`, status `{row.get('status')}`, target count `{row.get('target_count')}`, targets {_markdown_list(row_targets)}",
                ]
            )
        lineage_section.append("")

    runner_command = (
        "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
        "--from-frontier-conveyor-receipt --check"
        if receipt.get("audit_mode") == "frontier_conveyor_applied_direct_targets"
        else (
            "./repo-python tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py "
            f"--target {target} --check"
        )
    )
    return "\n".join(
        [
            "# Lean-Backed Period-Noncollapse Certificate Engine",
            "",
            "_Generated by `tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py`. Do not edit by hand._",
            "",
            "This packet is a public-safe reproducibility surface for exact concrete Lean targets in the Erdos257 period-noncollapse pilot. It is intentionally scoped to generated certificate-table targets and explicit non-claims.",
            "",
            "## Exact Target Runner",
            "",
            f"- Target theorem: `{target}`",
            f"- Namespaced theorem: `{receipt['namespaced_target_theorem']}`",
            f"- Target line: `{receipt.get('target_line')}`",
            f"- `#check`: `{receipt.get('target_check_status')}`",
            f"- `#print axioms`: `{receipt.get('print_axioms_status')}`",
            f"- Axiom dependency class: `{receipt.get('axiom_dependency_class')}`",
            f"- Axiom dependencies: {_markdown_list(axiom_dependencies)}",
            f"- Custom axiom dependencies: {_markdown_list(custom_axioms)}",
            f"- Static placeholder scan: `{receipt.get('static_placeholder_scan', {}).get('status')}`",
            "",
            *tranche_section,
            *lineage_section,
            "## Reproduction Commands",
            "",
            "```bash",
            "./repo-python tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py --check",
            "cd formal_math/erdos257_period_noncollapse && lake build Erdos257PeriodNoncollapse.GeneratedCertificates",
            "cd ../../..",
            runner_command,
            "./repo-pytest system/server/tests/test_formal_math_erdos257_lean_target_runner.py system/server/tests/test_formal_math_erdos257_period_noncollapse_strike.py",
            "```",
            "",
            "## Proof Boundary",
            "",
            "- Verified concrete certificate-table period targets are Lean-checked generated instances.",
            "- The generated consumer layer depends on the hand-written certificate kernel.",
            "- The frontier/scout layer recommends concrete factory actions; it is not proof authority.",
            "- Bounded selector evidence remains distinct from candidate universal paper/referee/Lean closure.",
            "",
            "## Explicit Non-Claims",
            "",
            "- This is not a proof of the universal finite theorem.",
            "- This is not a primitive-divisor existence proof.",
            "- This is not arbitrary generated-row existence.",
            "- This is not a solution of Erdos #257.",
            "- This is not publication authority.",
            "",
            "## Receipt Refs",
            "",
            f"- Target-runner receipt: `{RECEIPT_PATH.as_posix()}`",
            f"- Strike state: `{strike.STRIKE_PATH.as_posix()}`",
            f"- Generated certificates: `{strike.DIRECT_PRIME_GENERATED_LEAN_MODULE.as_posix()}`",
            f"- Claim boundary: `{receipt.get('claim_boundary')}`",
            "",
        ]
    )


def _receipt_current(existing: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    keys = [
        "status",
        "audit_mode",
        "target_count",
        "target_theorem",
        "target_check_status",
        "print_axioms_status",
        "axiom_dependency_class",
        "axiom_dependencies",
        "custom_axiom_dependencies",
        "sorry_like_axiom_dependency_detected",
        "all_targets_foundational_or_none",
        "targets",
    ]
    return all(existing.get(key) == current.get(key) for key in keys)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=None)
    parser.add_argument(
        "--from-frontier-conveyor-receipt",
        action="store_true",
        help=(
            "Audit every bind_semantic_spec period theorem named by the latest "
            "frontier conveyor receipt."
        ),
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args(argv)

    receipt_path = _repo_path(RECEIPT_PATH)
    packet_path = _repo_path(PUBLIC_PACKET_PATH)
    existing = _read_json(receipt_path) if receipt_path.exists() else {}
    from_frontier_conveyor_receipt = bool(args.from_frontier_conveyor_receipt)
    if (
        args.check
        and not args.target
        and existing.get("audit_mode") == "frontier_conveyor_applied_direct_targets"
    ):
        from_frontier_conveyor_receipt = True
    receipt = (
        build_receipt_from_frontier_conveyor_receipt(
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
        if from_frontier_conveyor_receipt
        else build_receipt(
            target_theorem=args.target,
            skip_build=args.skip_build,
            timeout_seconds=args.timeout_seconds,
        )
    )
    receipt_current = _receipt_current(existing, receipt) if existing else False
    check_payload = {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if receipt["status"] == "PASS" and (not args.check or receipt_current) else "FAIL",
        "receipt_status": receipt["status"],
        "receipt_current": receipt_current,
        "audit_mode": receipt.get("audit_mode"),
        "target_count": receipt.get("target_count"),
        "all_targets_foundational_or_none": receipt.get(
            "all_targets_foundational_or_none"
        ),
        "target_theorem": receipt["target_theorem"],
        "receipt_ref": RECEIPT_PATH.as_posix(),
        "public_packet_ref": PUBLIC_PACKET_PATH.as_posix(),
        "claim_boundary": CLAIM_BOUNDARY,
    }

    if args.write:
        receipt = _with_receipt_lineage(receipt, existing)
        _write_json(receipt_path, receipt)
        _write_text(packet_path, build_public_packet(receipt))
        check_payload["status"] = "PASS" if receipt["status"] == "PASS" else "FAIL"
        check_payload["receipt_current"] = True

    output = check_payload if args.check else receipt
    if args.json or args.check:
        print(json.dumps(output, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(f"{output['status']} {receipt['target_theorem']}")
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
