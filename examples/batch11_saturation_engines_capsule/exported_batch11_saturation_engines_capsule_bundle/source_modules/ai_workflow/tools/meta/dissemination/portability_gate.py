#!/usr/bin/env python3
"""Run the publication portability gate over a fresh public projection."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tools.meta.dissemination import projection_secret_scan


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = Path("publication_manifest.yaml")
DEFAULT_OUTPUT_ROOT = Path(
    os.environ.get(
        "AIW_PUBLIC_PROJECTION_OUTPUT_ROOT",
        Path.home() / ".cache" / "ai_workflow" / "public_projection",
    )
)
DEFAULT_REPORT_NAME = "portability_gate_report.json"
PROJECTION_SECRET_SCAN_REPORT_NAME = projection_secret_scan.DEFAULT_REPORT_NAME
STANDARD_PATH = Path("codex/standards/std_publication_manifest.json")
RENDER_SCRIPT = Path("tools/meta/dissemination/render_public_projection.py")
PROJECTION_RECEIPT_NAME = "projection_receipt.json"
DEFAULT_MIN_FREE_MB = int(os.environ.get("AIW_PORTABILITY_MIN_FREE_MB", "2048"))
DEFAULT_TMP_RETENTION_HOURS = int(os.environ.get("AIW_PORTABILITY_TMP_RETENTION_HOURS", "12"))
DEFAULT_SETUP_TIMEOUT_SECONDS = int(os.environ.get("AIW_PORTABILITY_SETUP_TIMEOUT_SECONDS", "300"))

BASE_POLICY_EXCEPTION_PATHS = {
    Path("publication_manifest.yaml"),
    Path("docs/dissemination/public_projection_boundary_v0.md"),
    Path("docs/dissemination/release_coverage_manifest_v0.md"),
    Path("docs/dissemination/release_file_boundary_manifest_v0.md"),
    Path("docs/dissemination/private_artifact_exclusion_storage_audit_v0.md"),
    Path("docs/dissemination/public_privacy_boundary_for_contributors_v0.md"),
    Path("docs/dissemination/all_code_release_path_audit_v0.md"),
    Path("docs/dissemination/safety_boundary.md"),
    Path("docs/dissemination/public_trust_packet_v0.md"),
    Path("docs/dissemination/release_ip_license_gate_v0.md"),
    Path("codex/standards/std_publication_manifest.json"),
    Path(PROJECTION_SECRET_SCAN_REPORT_NAME),
}

PRIVATE_MARKER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_home_path", re.compile("/" + r"Users/[A-Za-z0-9_.-]+")),
    ("operator_identity", re.compile(r"operator_account_alias|operator_handle_placeholder", re.IGNORECASE)),
    ("private_email", re.compile(r"operator_account@example\.invalid", re.IGNORECASE)),
    ("private_chrome_profile", re.compile(r"Library/Application Support/Google/Chrome")),
    ("private_obsidian_path", re.compile(r"\.obsidian/|private Obsidian vault", re.IGNORECASE)),
    ("private_raw_seed_family_path", re.compile(r"operator_seed_root_placeholder", re.IGNORECASE)),
    (
        "browser_provider_symbol",
        re.compile(
            r"claude_app_injector|chatgpt_session_inject|claude_session_transport|"
            r"claude-in-chrome|gemini_web_session|browser_provider_session"
        ),
    ),
    ("secret_literal", re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY")),
    ("openai_key_shape", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("github_token_shape", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("slack_token_shape", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("aws_access_key_shape", re.compile(r"AKIA[0-9A-Z]{16}")),
)

PRIVATE_REFERENCE_PATTERNS = {
    "private_home_path",
    "operator_identity",
    "private_email",
    "private_chrome_profile",
    "private_obsidian_path",
}

BROWSER_PROVIDER_PATTERNS = {"browser_provider_symbol"}
SCAN_SKIP_DIR_NAMES = {"node_modules", ".git", ".vite", "dist", "__pycache__", ".pytest_cache"}
SCAN_SKIP_SUFFIXES = {".pyc"}
DISPOSABLE_TMP_PROJECTION_PREFIX = "ai_workflow_public_projection_"
DISPOSABLE_TMP_PROJECTION_MARKERS = ("current", "worktree", "after", "next", "preflight")


class GateError(ValueError):
    """Raised when the gate cannot produce a report."""


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GateError(f"{path} is not a JSON object")
    return payload


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GateError(f"{path} is not a YAML object")
    return payload


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def _run_command(command: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _short(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]..."


def _short_process_output(output: str | bytes | None, limit: int = 4000) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return _short(output.decode("utf-8", errors="replace"), limit=limit)
    return _short(output, limit=limit)


def _relative_to(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _directory_size(path: Path) -> int:
    total = 0
    for current, dirs, files in os.walk(path):
        if ".git" in dirs:
            dirs.remove(".git")
        for filename in files:
            file_path = Path(current) / filename
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def _is_disposable_tmp_projection_root(path: Path) -> bool:
    name = path.name
    if not path.is_dir() or not name.startswith(DISPOSABLE_TMP_PROJECTION_PREFIX):
        return False
    suffix = name[len(DISPOSABLE_TMP_PROJECTION_PREFIX) :]
    return any(suffix == marker or suffix.startswith(f"{marker}_") for marker in DISPOSABLE_TMP_PROJECTION_MARKERS)


def _disposable_tmp_projection_candidates(tmp_root: Path, *, min_age_seconds: int) -> list[dict[str, Any]]:
    if not tmp_root.exists():
        return []
    now = time.time()
    candidates: list[dict[str, Any]] = []
    for child in sorted(tmp_root.iterdir()):
        if not _is_disposable_tmp_projection_root(child):
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        age_seconds = max(0, int(now - stat.st_mtime))
        if age_seconds < min_age_seconds:
            continue
        candidates.append(
            {
                "path": str(child),
                "name": child.name,
                "age_seconds": age_seconds,
                "size_bytes": _directory_size(child),
            }
        )
    return candidates


def _delete_tmp_projection_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deleted: list[dict[str, Any]] = []
    for row in candidates:
        path = Path(str(row.get("path", "")))
        if not _is_disposable_tmp_projection_root(path):
            continue
        shutil.rmtree(path, ignore_errors=True)
        deleted.append(row)
    return deleted


def _tmp_retention_guard(
    *,
    output_root: Path,
    report_path: Path,
    min_free_mb: int,
    clean_stale_tmp_projections: bool,
    tmp_retention_hours: int,
) -> dict[str, Any]:
    guard_root = output_root.parent.resolve()
    guard_root.mkdir(parents=True, exist_ok=True)
    min_free_bytes = max(0, min_free_mb) * 1024 * 1024
    min_age_seconds = max(0, tmp_retention_hours) * 60 * 60
    candidates = _disposable_tmp_projection_candidates(guard_root, min_age_seconds=min_age_seconds)
    usage_before = shutil.disk_usage(guard_root)
    deleted: list[dict[str, Any]] = []
    if clean_stale_tmp_projections and usage_before.free < min_free_bytes:
        deleted = _delete_tmp_projection_candidates(candidates)
    usage_after = shutil.disk_usage(guard_root)
    status = "pass" if min_free_bytes == 0 or usage_after.free >= min_free_bytes else "fail"
    if status == "pass" and deleted:
        summary = "tmp retention guard pruned disposable projection roots before render"
    elif status == "pass":
        summary = "tmp retention guard has enough free space for render"
    else:
        summary = "tmp retention guard found insufficient free space before render"
    return _result(
        "tmp_retention_guard",
        status,
        summary=summary,
        hard_blocker=status == "fail",
        output_root=str(output_root),
        report_path=str(report_path),
        guard_root=str(guard_root),
        min_free_mb=min_free_mb,
        free_before_bytes=usage_before.free,
        free_after_bytes=usage_after.free,
        free_after_mb=round(usage_after.free / (1024 * 1024), 2),
        clean_stale_tmp_projections=clean_stale_tmp_projections,
        tmp_retention_hours=tmp_retention_hours,
        disposable_candidate_count=len(candidates),
        disposable_candidate_bytes=sum(int(row.get("size_bytes", 0)) for row in candidates),
        deleted_count=len(deleted),
        deleted_bytes=sum(int(row.get("size_bytes", 0)) for row in deleted),
        candidate_paths=[row["path"] for row in candidates[:10]],
    )


def _tmp_retention_failure_message(result: dict[str, Any]) -> str:
    return (
        "tmp retention guard failed before render: "
        f"free_after_mb={result.get('free_after_mb')} "
        f"min_free_mb={result.get('min_free_mb')} "
        f"guard_root={result.get('guard_root')} "
        f"disposable_candidate_count={result.get('disposable_candidate_count')}. "
        "Rerun with --clean-stale-tmp-projections, choose an output root on a larger volume, "
        "or remove obsolete projection roots manually."
    )


def _create_clean_worktree(repo_root: Path, head: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix="ai-workflow-portability-clean-"))
    shutil.rmtree(root)
    result = _run_command(["git", "worktree", "add", "--detach", "--force", str(root), head], cwd=repo_root)
    if result.returncode != 0:
        raise GateError(f"git worktree add failed: {result.stderr.strip() or result.stdout.strip()}")
    return root


def _remove_clean_worktree(repo_root: Path, clean_root: Path) -> None:
    _run_command(["git", "worktree", "remove", "--force", str(clean_root)], cwd=repo_root, timeout=60)


def _render_projection(clean_root: Path, manifest: Path, output_root: Path) -> dict[str, Any]:
    manifest_arg = str(manifest)
    if manifest.is_absolute():
        try:
            manifest_arg = str(manifest.relative_to(clean_root))
        except ValueError:
            pass
    command = [
        sys.executable,
        str(clean_root / RENDER_SCRIPT),
        "--manifest",
        manifest_arg,
        "--output-root",
        str(output_root),
    ]
    result = _run_command(command, cwd=clean_root, timeout=180)
    if result.returncode != 0:
        raise GateError(f"render_public_projection failed: {result.stderr.strip() or result.stdout.strip()}")
    receipt_path = output_root / PROJECTION_RECEIPT_NAME
    return _read_json(receipt_path)


def _allowed_policy_paths(report_path: Path, output_root: Path) -> set[Path]:
    allowed = set(BASE_POLICY_EXCEPTION_PATHS)
    allowed.add(Path(PROJECTION_RECEIPT_NAME))
    try:
        allowed.add(report_path.relative_to(output_root))
    except ValueError:
        pass
    return allowed


def _scan_file(path: Path, *, rel_path: Path, allowed_policy_paths: set[Path]) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    hits: list[dict[str, Any]] = []
    for name, pattern in PRIVATE_MARKER_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(
                {
                    "pattern": name,
                    "path": str(rel_path),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "policy_exception": rel_path in allowed_policy_paths,
                }
            )
    return hits


def _scan_output(output_root: Path, report_path: Path) -> dict[str, Any]:
    allowed = _allowed_policy_paths(report_path, output_root)
    hits: list[dict[str, Any]] = []
    symlink_escapes: list[dict[str, str]] = []
    file_count = 0
    skipped_file_count = 0
    for path in sorted(output_root.rglob("*")):
        rel = path.relative_to(output_root)
        if any(part in SCAN_SKIP_DIR_NAMES for part in rel.parts) or rel.suffix in SCAN_SKIP_SUFFIXES:
            if path.is_file():
                skipped_file_count += 1
            continue
        if path.is_symlink():
            target = path.resolve()
            try:
                target.relative_to(output_root)
            except ValueError:
                symlink_escapes.append({"path": str(rel), "target": str(target)})
            continue
        if path.is_file():
            file_count += 1
            hits.extend(_scan_file(path, rel_path=rel, allowed_policy_paths=allowed))
    blocking = [hit for hit in hits if not hit["policy_exception"]]
    exceptions = [hit for hit in hits if hit["policy_exception"]]
    return {
        "patterns_checked": [name for name, _pattern in PRIVATE_MARKER_PATTERNS],
        "file_count": file_count,
        "skipped_file_count": skipped_file_count,
        "skipped_dir_names": sorted(SCAN_SKIP_DIR_NAMES),
        "hit_count": len(hits),
        "blocking_hit_count": len(blocking),
        "policy_exception_count": len(exceptions),
        "blocking_hits": blocking,
        "policy_exceptions": exceptions,
        "allowed_policy_exception_paths": sorted(str(path) for path in allowed),
        "symlink_escape_count": len(symlink_escapes),
        "symlink_escapes": symlink_escapes,
    }


def _boundary_policy_supersession_results(scan_summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Use the structured boundary scan to supersede legacy grep smoke rows.

    The manifest grep checks are intentionally conservative, but they cannot
    distinguish a forbidden symbol used as a policy example from one emitted as
    public runtime material. The boundary scanner owns that distinction through
    policy_exception flags, so these later results become the effective state
    for duplicate check ids in _compute_status().
    """
    blocking_hits = scan_summary.get("blocking_hits") or []
    policy_exceptions = scan_summary.get("policy_exceptions") or []

    def shaped_result(
        check_id: str,
        patterns: set[str],
        *,
        pass_summary: str,
        fail_summary: str,
    ) -> dict[str, Any]:
        blocking = [hit for hit in blocking_hits if hit.get("pattern") in patterns]
        exceptions = [hit for hit in policy_exceptions if hit.get("pattern") in patterns]
        return _result(
            check_id,
            "pass" if not blocking else "fail",
            summary=pass_summary if not blocking else fail_summary,
            hard_blocker=bool(blocking),
            source_check="structured_boundary_scan",
            supersedes_manifest_grep=True,
            blocking_hit_count=len(blocking),
            policy_exception_count=len(exceptions),
            blocking_hits=blocking[:25],
        )

    return [
        shaped_result(
            "no_private_only_references",
            PRIVATE_REFERENCE_PATTERNS,
            pass_summary="structured boundary scan found no blocking private-reference hits",
            fail_summary="structured boundary scan found blocking private-reference hits",
        ),
        shaped_result(
            "no_browser_automation_provider_calls",
            BROWSER_PROVIDER_PATTERNS,
            pass_summary="structured boundary scan found no blocking browser/provider automation symbols",
            fail_summary="structured boundary scan found blocking browser/provider automation symbols",
        ),
    ]


def _run_projection_secret_path_scan(output_root: Path, *, report_path: Path) -> dict[str, Any]:
    scan_report_path = output_root / PROJECTION_SECRET_SCAN_REPORT_NAME
    policy_paths = set(_allowed_policy_paths(report_path, output_root))
    policy_paths.add(Path(PROJECTION_SECRET_SCAN_REPORT_NAME))
    report = projection_secret_scan.scan_projection(
        output_root,
        policy_exception_paths=policy_paths,
    )
    projection_secret_scan.write_report(scan_report_path, report)
    passed = report["status"] == "green"
    return _result(
        "projection_secret_path_scan",
        "pass" if passed else "fail",
        summary=(
            "projection secret/path scan found no blocking private markers"
            if passed
            else "projection secret/path scan found blocking private markers"
        ),
        hard_blocker=not passed,
        tool="projection_secret_scan",
        implementation="tools/meta/dissemination/projection_secret_scan.py::scan_projection",
        report_path=str(scan_report_path),
        blocking_hit_count=report["blocking_hit_count"],
        policy_exception_count=report["policy_exception_count"],
        blocking_category_counts=report["blocking_category_counts"],
        symlink_escape_count=report["symlink_escape_count"],
        scan_summary={
            "schema_version": report["schema_version"],
            "status": report["status"],
            "file_count": report["file_count"],
            "blocking_hit_count": report["blocking_hit_count"],
            "policy_exception_count": report["policy_exception_count"],
            "blocking_category_counts": report["blocking_category_counts"],
            "blocking_hits": report["blocking_hits"],
            "symlink_escape_count": report["symlink_escape_count"],
        },
    )


def _run_gitleaks_scan(output_root: Path, *, report_dir: Path) -> dict[str, Any]:
    """Run the gitleaks CLI over the rendered public projection output.

    Fails closed when:
    - the gitleaks binary is unavailable on PATH;
    - gitleaks exits with an error other than the documented "leaks found" code (1);
    - the JSON report cannot be parsed;
    - any leaks are found.

    The receipt is shaped to satisfy the manifest's `no_secret_scan_hits` hard
    blocker. The manifest declares this row as gate-owned because the scan must
    run after the projection is materialized.
    """
    check_id = "no_secret_scan_hits"
    gitleaks_path = shutil.which("gitleaks")
    if not gitleaks_path:
        return _result(
            check_id,
            "fail",
            summary="gitleaks CLI not available on PATH; secret-scan gate cannot run",
            hard_blocker=True,
            tool="gitleaks",
            tool_available=False,
        )

    try:
        version = subprocess.check_output(
            [gitleaks_path, "version"], text=True, stderr=subprocess.STDOUT, timeout=10
        ).strip()
    except (subprocess.SubprocessError, OSError) as exc:
        return _result(
            check_id,
            "fail",
            summary=f"gitleaks version probe failed: {exc}",
            hard_blocker=True,
            tool="gitleaks",
        )

    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "gitleaks_report.json"
    cmd = [
        gitleaks_path,
        "detect",
        "--source", str(output_root),
        "--no-git",
        "--redact",
        "--report-format", "json",
        "--report-path", str(report_path),
        "--exit-code", "1",
    ]
    try:
        completed = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _result(
            check_id,
            "fail",
            summary="gitleaks scan timed out",
            hard_blocker=True,
            tool="gitleaks",
            tool_version=version,
            stderr=_short(exc.stderr or ""),
        )

    # gitleaks exit codes: 0 = no leaks, 1 = leaks found, others = error
    if completed.returncode not in (0, 1):
        return _result(
            check_id,
            "fail",
            summary=f"gitleaks exited with error code {completed.returncode}",
            hard_blocker=True,
            tool="gitleaks",
            tool_version=version,
            exit_code=completed.returncode,
            stderr=_short(completed.stderr),
        )

    leak_count = 0
    findings: list[dict[str, Any]] = []
    if report_path.exists():
        try:
            raw = report_path.read_text(encoding="utf-8")
            parsed = json.loads(raw) if raw.strip() else []
            if isinstance(parsed, list):
                findings = parsed
                leak_count = len(parsed)
            else:
                return _result(
                    check_id,
                    "fail",
                    summary="gitleaks report is not a JSON array",
                    hard_blocker=True,
                    tool="gitleaks",
                    tool_version=version,
                )
        except json.JSONDecodeError as exc:
            return _result(
                check_id,
                "fail",
                summary=f"gitleaks report unparseable: {exc}",
                hard_blocker=True,
                tool="gitleaks",
                tool_version=version,
            )

    passed = leak_count == 0 and completed.returncode == 0
    return _result(
        check_id,
        "pass" if passed else "fail",
        summary=(
            f"gitleaks scanned {output_root} with no leaks"
            if passed
            else f"gitleaks reported {leak_count} leak(s) over {output_root}"
        ),
        hard_blocker=not passed,
        tool="gitleaks",
        tool_version=version,
        source=str(output_root),
        report_path=str(report_path),
        redacted=True,
        no_git=True,
        exit_code=completed.returncode,
        leak_count=leak_count,
        # Cap finding details to bound the receipt; full report is on disk.
        finding_excerpt=findings[:10],
    )


def _result(
    check_id: str,
    status: str,
    *,
    summary: str,
    hard_blocker: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        "id": check_id,
        "status": status,
        "summary": summary,
        "hard_blocker": hard_blocker,
    }
    payload.update(extra)
    return payload


def _receipt_integrity_results(
    *,
    receipt: dict[str, Any],
    standard: dict[str, Any],
    manifest_path: Path,
    head: str,
    output_root: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    required = standard.get("receipt_contract", {}).get("projection_receipt_required_fields", [])
    missing = [field for field in required if field not in receipt]
    results.append(
        _result(
            "receipt_required_fields",
            "pass" if not missing else "fail",
            summary="projection receipt required fields present" if not missing else f"missing fields: {missing}",
            hard_blocker=bool(missing),
            missing_fields=missing,
        )
    )
    expected_hash = _sha256_file(manifest_path)
    hash_ok = receipt.get("manifest_hash") == expected_hash
    results.append(
        _result(
            "receipt_manifest_hash_matches",
            "pass" if hash_ok else "fail",
            summary="receipt manifest hash matches current manifest" if hash_ok else "receipt manifest hash is stale",
            hard_blocker=not hash_ok,
            expected=expected_hash,
            actual=receipt.get("manifest_hash"),
        )
    )
    revision_ok = receipt.get("source_revision") == head
    results.append(
        _result(
            "receipt_source_revision_matches_head",
            "pass" if revision_ok else "fail",
            summary="receipt source revision matches clean HEAD" if revision_ok else "receipt source revision does not match clean HEAD",
            hard_blocker=not revision_ok,
            expected=head,
            actual=receipt.get("source_revision"),
        )
    )
    missing_outputs = []
    for item in receipt.get("included_paths", []):
        rel = item.get("output")
        if rel and not (output_root / rel).exists():
            missing_outputs.append(rel)
    for item in receipt.get("synthetic_fixtures", []):
        rel = item.get("output")
        if rel and not (output_root / rel).exists():
            missing_outputs.append(rel)
    results.append(
        _result(
            "receipt_outputs_exist",
            "pass" if not missing_outputs else "fail",
            summary="all receipted included and fixture outputs exist" if not missing_outputs else "receipted outputs missing",
            hard_blocker=bool(missing_outputs),
            missing_outputs=missing_outputs,
        )
    )
    blocking_hits = receipt.get("scan_summary", {}).get("blocking_hit_count")
    results.append(
        _result(
            "receipt_scan_blocking_hits_zero",
            "pass" if blocking_hits == 0 else "fail",
            summary="A4 receipt reports zero emitted-output blocking hits" if blocking_hits == 0 else "A4 receipt reports blocking hits",
            hard_blocker=blocking_hits != 0,
            blocking_hit_count=blocking_hits,
        )
    )
    output_root_value = str(receipt.get("output_root") or "")
    local_diag = output_root_value.startswith(("/tmp/", "/private/tmp/", "/Users/"))
    results.append(
        _result(
            "receipt_output_root_public_normalization",
            "warn" if local_diag else "pass",
            summary="receipt carries local diagnostic output_root; public-normalized field is still needed"
            if local_diag
            else "receipt output_root is public-normalized",
            hard_blocker=False,
            output_root=output_root_value,
        )
    )
    return results


def _run_manifest_smokes(manifest: dict[str, Any], output_root: Path) -> list[dict[str, Any]]:
    gate = manifest.get("portability_gate") or {}
    hard_ids = set(gate.get("hard_blockers_for_public_toggle") or [])
    results: list[dict[str, Any]] = []
    for row in gate.get("smoke_battery") or []:
        check_id = str(row.get("id") or "unnamed_smoke")
        command = str(row.get("command") or "")
        expect = str(row.get("expect") or "")
        is_hard = check_id in hard_ids
        if row.get("status") == "planned":
            results.append(
                _result(
                    check_id,
                    "skipped",
                    summary="smoke row is planned and has no runnable local implementation",
                    hard_blocker=is_hard,
                    command=command,
                    expect=expect,
                    manifest_status=row.get("status"),
                )
            )
            continue
        if row.get("status") == "gate_owned":
            results.append(
                _result(
                    f"{check_id}_manifest_delegation",
                    "pass",
                    summary="manifest smoke is delegated to a gate-owned implementation",
                    hard_blocker=False,
                    delegated_check_id=check_id,
                    implementation=row.get("implementation"),
                    tool=row.get("tool"),
                    expect=expect,
                    manifest_status=row.get("status"),
                )
            )
            continue
        if not command:
            results.append(
                _result(check_id, "fail", summary="smoke row has no command", hard_blocker=is_hard, expect=expect)
            )
            continue
        if "serves_within_30s" in expect:
            results.append(
                _run_serving_smoke(
                    check_id=check_id,
                    command=command,
                    expect=expect,
                    output_root=output_root,
                    is_hard=is_hard,
                )
            )
            continue
        try:
            completed = subprocess.run(
                command,
                cwd=output_root,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            if "zero_hits" in expect:
                passed = completed.returncode == 0 and stdout.strip() == ""
            elif "exit_zero" in expect:
                passed = completed.returncode == 0 and stdout.strip() != "" if "nonempty_stdout" in expect else completed.returncode == 0
            elif "serves_within_30s" in expect:
                passed = completed.returncode == 0
            else:
                passed = completed.returncode == 0
            results.append(
                _result(
                    check_id,
                    "pass" if passed else "fail",
                    summary="manifest smoke passed" if passed else "manifest smoke failed in projected output root",
                    hard_blocker=is_hard and not passed,
                    command=command,
                    expect=expect,
                    exit_code=completed.returncode,
                    stdout=_short(stdout),
                    stderr=_short(stderr),
                )
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                _result(
                    check_id,
                    "fail",
                    summary="manifest smoke timed out",
                    hard_blocker=is_hard,
                    command=command,
                    expect=expect,
                    stdout=_short(exc.stdout or ""),
                    stderr=_short(exc.stderr or ""),
                    timeout_seconds=30,
                )
            )
    return results


def _latest_results_by_id(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return final check states, letting later runnable receipts supersede placeholders."""
    by_id: dict[str, dict[str, Any]] = {}
    id_order: list[str] = []
    for index, item in enumerate(results):
        check_id = str(item.get("id") or f"__anonymous_{index}")
        if check_id not in by_id:
            id_order.append(check_id)
        by_id[check_id] = item
    return [by_id[check_id] for check_id in id_order]


def _compute_status(results: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    final_results = _latest_results_by_id(results)
    hard_blockers = [item for item in final_results if item.get("hard_blocker")]
    failed_checks = [item for item in final_results if item.get("status") in {"fail", "skipped"}]
    if hard_blockers:
        return "red", hard_blockers, failed_checks
    if any(item.get("status") == "warn" for item in final_results):
        return "amber", hard_blockers, failed_checks
    return "green", hard_blockers, failed_checks


def _next_required_action(status: str, failed_checks: list[dict[str, Any]]) -> str:
    if status == "green":
        return "Proceed to later Wave A proof artifacts; A5 alone does not authorize public toggle."
    if not failed_checks:
        return "Resolve warnings or explicitly accept amber diagnostic posture before public toggle."
    ids = [item.get("id") for item in failed_checks[:8]]
    return "Resolve or explicitly reroute failed/skipped gate checks before public toggle: " + ", ".join(map(str, ids))


def _port_from_command(command: str) -> int:
    match = re.search(r"--port\s+(\d+)", command)
    if match:
        return int(match.group(1))
    match = re.search(r"http\.server\s+(\d+)", command)
    if match:
        return int(match.group(1))
    return 5173


def _serving_command_phases(command: str) -> tuple[list[str], str]:
    segments = [segment.strip() for segment in command.split("&&") if segment.strip()]
    if len(segments) < 2:
        return [], command

    prefix: list[str] = []
    runnable_segments = segments
    if segments[0].startswith("cd "):
        prefix = [segments[0]]
        runnable_segments = segments[1:]
    if len(runnable_segments) < 2:
        return [], command

    setup_commands = [" && ".join(prefix + [segment]) for segment in runnable_segments[:-1]]
    server_command = " && ".join(prefix + [runnable_segments[-1]])
    return setup_commands, server_command


def _server_timeout_from_expect(expect: str, fallback_seconds: int) -> int:
    match = re.search(r"serves_within_(\d+)s", expect)
    if not match:
        return fallback_seconds
    return min(fallback_seconds, int(match.group(1)))


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            if hasattr(os, "killpg"):
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass


def _run_serving_smoke(
    *,
    check_id: str,
    command: str,
    expect: str,
    output_root: Path,
    is_hard: bool,
    timeout_seconds: int = 120,
    setup_timeout_seconds: int = DEFAULT_SETUP_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    port = _port_from_command(command)
    ready_url = f"http://127.0.0.1:{port}/"
    setup_commands, server_command = _serving_command_phases(command)
    setup_results: list[dict[str, Any]] = []
    setup_start = time.monotonic()
    for setup_command in setup_commands:
        command_start = time.monotonic()
        try:
            completed = subprocess.run(
                setup_command,
                cwd=output_root,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=setup_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = round(time.monotonic() - command_start, 3)
            return _result(
                check_id,
                "fail",
                summary="manifest serving setup timed out before dev server launch",
                hard_blocker=is_hard,
                command=command,
                setup_command=setup_command,
                server_command=server_command,
                phase="setup_timeout",
                expect=expect,
                ready_url=ready_url,
                setup_timeout_seconds=setup_timeout_seconds,
                setup_elapsed_seconds=elapsed,
                stdout=_short_process_output(exc.stdout),
                stderr=_short_process_output(exc.stderr),
            )
        elapsed = round(time.monotonic() - command_start, 3)
        setup_result = {
            "command": setup_command,
            "exit_code": completed.returncode,
            "elapsed_seconds": elapsed,
            "stdout": _short_process_output(completed.stdout),
            "stderr": _short_process_output(completed.stderr),
        }
        setup_results.append(setup_result)
        if completed.returncode != 0:
            return _result(
                check_id,
                "fail",
                summary="manifest serving setup failed before dev server launch",
                hard_blocker=is_hard,
                command=command,
                setup_command=setup_command,
                server_command=server_command,
                phase="setup_failed",
                expect=expect,
                exit_code=completed.returncode,
                ready_url=ready_url,
                setup_timeout_seconds=setup_timeout_seconds,
                setup_elapsed_seconds=elapsed,
                setup_results=setup_results,
                stdout=_short_process_output(completed.stdout),
                stderr=_short_process_output(completed.stderr),
            )

    setup_elapsed = round(time.monotonic() - setup_start, 3)
    server_timeout_seconds = _server_timeout_from_expect(expect, timeout_seconds)
    start = time.monotonic()
    process = subprocess.Popen(
        server_command,
        cwd=output_root,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if hasattr(os, "setsid") else None,
    )
    try:
        probe_attempts = 0
        last_probe_error = ""
        while time.monotonic() - start < server_timeout_seconds:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=5)
                return _result(
                    check_id,
                    "fail",
                    summary="manifest serving smoke exited before serving HTTP",
                    hard_blocker=is_hard,
                    command=command,
                    setup_commands=setup_commands,
                    setup_results=setup_results,
                    setup_elapsed_seconds=setup_elapsed,
                    server_command=server_command,
                    phase="server_process_exited",
                    expect=expect,
                    exit_code=process.returncode,
                    ready_url=ready_url,
                    stdout=_short_process_output(stdout),
                    stderr=_short_process_output(stderr),
                    setup_timeout_seconds=setup_timeout_seconds,
                    server_timeout_seconds=server_timeout_seconds,
                )
            try:
                probe_attempts += 1
                with urllib.request.urlopen(ready_url, timeout=1) as response:
                    if response.status < 500:
                        elapsed = round(time.monotonic() - start, 3)
                        _terminate_process_tree(process)
                        stdout, stderr = process.communicate(timeout=5)
                        return _result(
                            check_id,
                            "pass",
                            summary="manifest serving smoke reached HTTP endpoint",
                            hard_blocker=False,
                            command=command,
                            setup_commands=setup_commands,
                            setup_results=setup_results,
                            setup_elapsed_seconds=setup_elapsed,
                            server_command=server_command,
                            expect=expect,
                            ready_url=ready_url,
                            ready_within_seconds=elapsed,
                            setup_timeout_seconds=setup_timeout_seconds,
                            server_timeout_seconds=server_timeout_seconds,
                            probe_attempts=probe_attempts,
                            stdout=_short_process_output(stdout),
                            stderr=_short_process_output(stderr),
                        )
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_probe_error = str(exc)
                time.sleep(0.5)
        _terminate_process_tree(process)
        stdout, stderr = process.communicate(timeout=5)
        return _result(
            check_id,
            "fail",
            summary="manifest serving smoke server command did not become reachable before readiness timeout",
            hard_blocker=is_hard,
            command=command,
            setup_commands=setup_commands,
            setup_results=setup_results,
            setup_elapsed_seconds=setup_elapsed,
            server_command=server_command,
            phase="server_ready_probe_timeout",
            expect=expect,
            ready_url=ready_url,
            setup_timeout_seconds=setup_timeout_seconds,
            server_timeout_seconds=server_timeout_seconds,
            probe_attempts=probe_attempts,
            last_probe_error=last_probe_error,
            stdout=_short_process_output(stdout),
            stderr=_short_process_output(stderr),
        )
    finally:
        _terminate_process_tree(process)


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _run_gate(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    report_path = Path(args.report).resolve() if args.report else output_root / DEFAULT_REPORT_NAME
    source_head = _git_head(repo_root)
    standard = _read_json(repo_root / STANDARD_PATH)
    manifest = _read_yaml(repo_root / args.manifest)

    clean_root: Path | None = None
    render_root = repo_root
    try:
        retention_result = _tmp_retention_guard(
            output_root=output_root,
            report_path=report_path,
            min_free_mb=int(args.min_free_mb),
            clean_stale_tmp_projections=bool(args.clean_stale_tmp_projections),
            tmp_retention_hours=int(args.tmp_retention_hours),
        )
        if retention_result["status"] == "fail":
            raise GateError(_tmp_retention_failure_message(retention_result))
        if not args.no_clean_worktree:
            clean_root = _create_clean_worktree(repo_root, source_head)
            render_root = clean_root
        clean_manifest = render_root / args.manifest
        receipt = _render_projection(render_root, clean_manifest, output_root)

        receipt_path = output_root / PROJECTION_RECEIPT_NAME
        results: list[dict[str, Any]] = []
        results.append(
            _result(
                "gate_clean_worktree_used",
                "pass" if not args.no_clean_worktree else "warn",
                summary="gate rendered from detached clean worktree"
                if not args.no_clean_worktree
                else "gate rendered from current working tree",
                hard_blocker=False,
                clean_worktree_mode=not args.no_clean_worktree,
            )
        )
        results.append(retention_result)
        outside_repo = True
        try:
            output_root.relative_to(repo_root)
            outside_repo = False
        except ValueError:
            outside_repo = True
        results.append(
            _result(
                "output_root_outside_private_repo",
                "pass" if outside_repo else "fail",
                summary="output root is outside private repo" if outside_repo else "output root is inside private repo",
                hard_blocker=not outside_repo,
                output_root=str(output_root),
            )
        )
        results.extend(
            _receipt_integrity_results(
                receipt=receipt,
                standard=standard,
                manifest_path=render_root / args.manifest if clean_root else repo_root / args.manifest,
                head=source_head,
                output_root=output_root,
            )
        )
        smoke_results = _run_manifest_smokes(manifest, output_root)
        results.extend(smoke_results)

        pre_report_scan = _scan_output(output_root, report_path)
        results.append(
            _result(
                "output_boundary_scan",
                "pass" if pre_report_scan["blocking_hit_count"] == 0 and pre_report_scan["symlink_escape_count"] == 0 else "fail",
                summary="output boundary scan has no blocking hits or symlink escapes"
                if pre_report_scan["blocking_hit_count"] == 0 and pre_report_scan["symlink_escape_count"] == 0
                else "output boundary scan found blockers",
                hard_blocker=pre_report_scan["blocking_hit_count"] > 0 or pre_report_scan["symlink_escape_count"] > 0,
                scan_summary=pre_report_scan,
            )
        )
        results.extend(_boundary_policy_supersession_results(pre_report_scan))

        results.append(_run_projection_secret_path_scan(output_root, report_path=report_path))

        # L5.5 secret-scan gate: run gitleaks over the rendered output.
        # Report is written adjacent to output_root (in its parent) so the
        # in-tree regex scanner does not pick up the JSON report as a scannable
        # artifact on the next pass.
        results.append(_run_gitleaks_scan(output_root, report_dir=output_root.parent))

        status, hard_blockers, failed_checks = _compute_status(results)
        report = {
        "schema_version": "portability_gate_report_v0",
        "repo_path": str(output_root),
        "source_repo_path": str(repo_root),
        "source_revision": source_head,
        "gate_generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "manifest_path": args.manifest,
        "manifest_hash": receipt.get("manifest_hash"),
        "projection_receipt_ref": str(receipt_path),
        "receipt_source_revision": receipt.get("source_revision"),
        "receipt_manifest_hash": receipt.get("manifest_hash"),
        "resolver_command": [
            str(render_root / RENDER_SCRIPT),
            "--manifest",
            args.manifest,
            "--output-root",
            str(output_root),
        ],
        "output_root": str(output_root),
        "public_output_root": ".",
        "clean_worktree_used": not args.no_clean_worktree,
        "clean_worktree_root": str(clean_root) if clean_root and args.keep_clean_worktree else "removed_after_render",
        "smoke_results": results,
        "hard_blockers": hard_blockers,
        "overall_status": status,
        "publication_status": status,
        "tool_execution_status": "report_emitted",
        "failed_checks": failed_checks,
        "next_required_action": _next_required_action(status, failed_checks),
        "projection_receipt_summary": {
            "included_count": len(receipt.get("included_paths", [])),
            "blocked_count": receipt.get("omission_receipt", {}).get("blocked_count"),
            "omitted_count": receipt.get("omission_receipt", {}).get("omitted_count"),
            "blocking_hit_count": receipt.get("scan_summary", {}).get("blocking_hit_count"),
            "policy_exception_count": receipt.get("scan_summary", {}).get("policy_exception_count"),
            "public_toggle_status": receipt.get("public_toggle_status"),
        },
        }
        _write_report(report_path, report)

        final_scan = _scan_output(output_root, report_path)
        report["report_scan_summary"] = final_scan
        if final_scan["blocking_hit_count"] or final_scan["symlink_escape_count"]:
            report["smoke_results"].append(
                _result(
                    "report_inclusive_boundary_scan",
                    "fail",
                    summary="boundary scan including gate report found blockers",
                    hard_blocker=True,
                    scan_summary=final_scan,
                )
            )
        else:
            report["smoke_results"].append(
                _result(
                    "report_inclusive_boundary_scan",
                    "pass",
                    summary="boundary scan including gate report has no blockers",
                    hard_blocker=False,
                    scan_summary=final_scan,
                )
            )
        report["smoke_results"].extend(_boundary_policy_supersession_results(final_scan))
        status, hard_blockers, failed_checks = _compute_status(report["smoke_results"])
        report["hard_blockers"] = hard_blockers
        report["overall_status"] = status
        report["publication_status"] = status
        report["failed_checks"] = failed_checks
        report["next_required_action"] = _next_required_action(status, failed_checks)
        _write_report(report_path, report)
        return report
    finally:
        if clean_root and not args.keep_clean_worktree:
            _remove_clean_worktree(repo_root, clean_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the public projection portability gate.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Private repo root.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Manifest path relative to repo root.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Projection output root.")
    parser.add_argument("--report", default=None, help="Gate report path. Defaults to <output-root>/portability_gate_report.json.")
    parser.add_argument("--no-clean-worktree", action="store_true", help="Render from the current tree instead of a clean detached worktree.")
    parser.add_argument("--keep-clean-worktree", action="store_true", help="Do not remove the temporary clean worktree.")
    parser.add_argument(
        "--min-free-mb",
        type=int,
        default=DEFAULT_MIN_FREE_MB,
        help="Minimum free space required on the output-root volume before render; set 0 to disable.",
    )
    parser.add_argument(
        "--clean-stale-tmp-projections",
        action="store_true",
        help=(
            "Before render, prune stale disposable ai_workflow_public_projection roots "
            "(current/worktree/after/next/preflight) under the output-root parent if "
            "free space is below --min-free-mb."
        ),
    )
    parser.add_argument(
        "--tmp-retention-hours",
        type=int,
        default=DEFAULT_TMP_RETENTION_HOURS,
        help="Minimum age for disposable tmp projection roots eligible for --clean-stale-tmp-projections.",
    )
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 if a report was emitted.")
    parser.add_argument("--fail-on-red", action="store_true", help="Exit nonzero when the report is red.")
    args = parser.parse_args()

    try:
        report = _run_gate(args)
    except (GateError, subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"portability_gate: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.fail_on_red and report.get("overall_status") == "red":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
