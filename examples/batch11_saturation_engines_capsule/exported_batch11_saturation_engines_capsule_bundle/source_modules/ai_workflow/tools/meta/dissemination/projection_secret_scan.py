#!/usr/bin/env python3
"""Scan a rendered public projection for private paths, secrets, and host-bound state."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REPORT_NAME = "projection_secret_scan_report.json"

DEFAULT_POLICY_EXCEPTION_PATHS = {
    Path("publication_manifest.yaml"),
    Path("projection_receipt.json"),
    Path("portability_gate_report.json"),
    Path(DEFAULT_REPORT_NAME),
    Path("docs/dissemination/public_projection_lockfile_v0.json"),
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
}

SCAN_SKIP_DIR_NAMES = {"node_modules", ".git", ".vite", "dist", "__pycache__", ".pytest_cache"}
SCAN_SKIP_SUFFIXES = {".pyc"}

CONTENT_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("credentials", "secret_literal", re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY")),
    ("credentials", "openai_key_shape", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("credentials", "github_token_shape", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("credentials", "slack_token_shape", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("credentials", "aws_access_key_shape", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_path", "private_home_path", re.compile("/" + r"Users/[A-Za-z0-9_.-]+")),
    (
        "operator_identity",
        "operator_identity",
        re.compile(r"operator_account_alias|operator_handle_placeholder", re.IGNORECASE),
    ),
    ("operator_identity", "private_email", re.compile(r"operator_account@example\.invalid", re.IGNORECASE)),
    ("private_path", "private_chrome_profile", re.compile(r"Library/Application Support/Google/Chrome")),
    ("private_path", "private_obsidian_path", re.compile(r"\.obsidian/|private Obsidian vault", re.IGNORECASE)),
    (
        "host_bound_transport",
        "browser_provider_symbol",
        re.compile(
            r"claude_app_injector|chatgpt_session_inject|claude_session_transport|"
            r"claude-in-chrome|gemini_web_session|browser_provider_session"
        ),
    ),
    (
        "host_bound_transport",
        "browser_debug_port",
        re.compile(r"(?:localhost|127\.0\.0\.1):922[0-9]\b"),
    ),
    (
        "private_path",
        "private_raw_seed_family_path",
        re.compile(r"operator_seed_root_placeholder", re.IGNORECASE),
    ),
)

PATH_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("raw_voice", "raw_seed_file_path", re.compile(r"(^|/)raw_seed(?:/|\.md$)", re.IGNORECASE)),
    ("private_history", "private_task_ledger_path", re.compile(r"(^|/)state/task_ledger/", re.IGNORECASE)),
    ("private_history", "private_prompt_ledger_path", re.compile(r"(^|/)state/prompt_ledger/", re.IGNORECASE)),
    ("private_path", "private_obsidian_tree_path", re.compile(r"(^|/)obsidian/", re.IGNORECASE)),
    (
        "host_bound_transport",
        "browser_provider_file_path",
        re.compile(r"claude_app_injector|chatgpt_session_inject|claude_session_transport|gemini_web_session", re.IGNORECASE),
    ),
)


def _normalise_policy_paths(paths: Iterable[str | Path] | None) -> set[Path]:
    normalised = set(DEFAULT_POLICY_EXCEPTION_PATHS)
    for raw in paths or ():
        path = Path(raw)
        if path.is_absolute():
            continue
        normalised.add(path)
    return normalised


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _match_hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _hit(
    *,
    category: str,
    pattern: str,
    path: Path,
    line: int | None,
    matched_text: str,
    policy_exception_paths: set[Path],
    source: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "pattern": pattern,
        "path": str(path),
        "line": line,
        "source": source,
        "policy_exception": path in policy_exception_paths,
        "match_sha256": _match_hash(matched_text),
    }


def _scan_file(path: Path, *, rel_path: Path, policy_exception_paths: set[Path]) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    hits: list[dict[str, Any]] = []
    for category, name, pattern in CONTENT_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(
                _hit(
                    category=category,
                    pattern=name,
                    path=rel_path,
                    line=_line_number(text, match.start()),
                    matched_text=match.group(0),
                    policy_exception_paths=policy_exception_paths,
                    source="content",
                )
            )
    return hits


def _scan_path(rel_path: Path, *, policy_exception_paths: set[Path]) -> list[dict[str, Any]]:
    rel_text = rel_path.as_posix()
    hits: list[dict[str, Any]] = []
    for category, name, pattern in PATH_PATTERNS:
        match = pattern.search(rel_text)
        if match:
            hits.append(
                _hit(
                    category=category,
                    pattern=name,
                    path=rel_path,
                    line=None,
                    matched_text=match.group(0),
                    policy_exception_paths=policy_exception_paths,
                    source="path",
                )
            )
    return hits


def scan_projection(root: Path, *, policy_exception_paths: Iterable[str | Path] | None = None) -> dict[str, Any]:
    """Return a deterministic scan report for a rendered public projection root."""
    output_root = root.resolve()
    if not output_root.exists() or not output_root.is_dir():
        raise ValueError(f"projection root does not exist or is not a directory: {root}")

    allowed = _normalise_policy_paths(policy_exception_paths)
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
                symlink_escapes.append({"path": str(rel), "target_sha256": _match_hash(str(target))})
            continue
        hits.extend(_scan_path(rel, policy_exception_paths=allowed))
        if path.is_file():
            file_count += 1
            hits.extend(_scan_file(path, rel_path=rel, policy_exception_paths=allowed))

    blocking_hits = [hit for hit in hits if not hit["policy_exception"]]
    policy_exceptions = [hit for hit in hits if hit["policy_exception"]]
    category_counts = Counter(str(hit["category"]) for hit in hits)
    blocking_category_counts = Counter(str(hit["category"]) for hit in blocking_hits)
    status = "green" if not blocking_hits and not symlink_escapes else "red"

    return {
        "schema_version": "projection_secret_scan_report_v0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "projection_root": ".",
        "status": status,
        "public_release_allowed_by_scan": status == "green",
        "patterns_checked": [
            {"category": category, "name": name}
            for category, name, _pattern in (*CONTENT_PATTERNS, *PATH_PATTERNS)
        ],
        "file_count": file_count,
        "skipped_file_count": skipped_file_count,
        "skipped_dir_names": sorted(SCAN_SKIP_DIR_NAMES),
        "hit_count": len(hits),
        "blocking_hit_count": len(blocking_hits),
        "policy_exception_count": len(policy_exceptions),
        "category_counts": dict(sorted(category_counts.items())),
        "blocking_category_counts": dict(sorted(blocking_category_counts.items())),
        "blocking_hits": blocking_hits[:50],
        "policy_exceptions": policy_exceptions[:100],
        "allowed_policy_exception_paths": sorted(str(path) for path in allowed),
        "symlink_escape_count": len(symlink_escapes),
        "symlink_escapes": symlink_escapes,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a rendered public projection for private leakage.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Rendered public projection root.")
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report path.")
    parser.add_argument(
        "--policy-exception-path",
        action="append",
        default=[],
        help="Projection-relative path allowed to mention scanner/boundary policy strings.",
    )
    parser.add_argument("--fail-on-blocking", action="store_true", help="Exit nonzero when blocking hits exist.")
    args = parser.parse_args()

    try:
        policy_paths: list[str | Path] = list(args.policy_exception_path)
        if args.report:
            try:
                policy_paths.append(args.report.resolve().relative_to(args.root.resolve()))
            except ValueError:
                pass
        report = scan_projection(args.root, policy_exception_paths=policy_paths)
    except ValueError as exc:
        print(f"projection_secret_scan: error: {exc}", file=sys.stderr)
        return 2

    if args.report:
        write_report(args.report, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_blocking and report["status"] != "green":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
