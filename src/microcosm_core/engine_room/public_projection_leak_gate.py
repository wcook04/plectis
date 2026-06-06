"""Public-safe projection leak gate capsule.

This is a source-faithful public refactor of
`tools/meta/dissemination/projection_secret_scan.py` plus the gitleaks witness
shape used by the portability gate. It scans a rendered public projection for
credential-shaped text, private host paths, private-state path names, symlink
escapes, and optional gitleaks findings.

Matches are reported by category, path, line, and hash only. The capsule is a
deterministic DLP-style projection gate, not a general security scanner, not a
prompt-injection defense, not sandboxing, and not an information-flow proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "engine_room_public_projection_leak_gate_v1"
ORGAN_ID = "engine_room_public_projection_leak_gate"
SOURCE_REFS = (
    "tools/meta/dissemination/projection_secret_scan.py",
    "tools/meta/dissemination/portability_gate.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Public projection DLP gate over rendered files, path names, symlink "
    "escapes, and optional gitleaks output. It is not a general security "
    "scanner, not prompt-injection defense, not sandboxing, and not an "
    "information-flow proof."
)
ANTI_CLAIMS = (
    "not_general_security_scanner",
    "not_prompt_injection_defense",
    "not_sandboxing",
    "not_information_flow_control",
)

DEFAULT_POLICY_EXCEPTION_PATHS = {
    Path("publication_manifest.yaml"),
    Path("projection_receipt.json"),
    Path("portability_gate_report.json"),
    Path("projection_secret_scan_report.json"),
    Path("docs/dissemination/public_projection_boundary_v0.md"),
    Path("docs/dissemination/safety_boundary.md"),
}
SCAN_SKIP_DIR_NAMES = {"node_modules", ".git", ".vite", "dist", "__pycache__", ".pytest_cache"}
SCAN_SKIP_SUFFIXES = {".pyc"}

CONTENT_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("credentials", "secret_literal", re.compile(r"BEGIN (?:RSA |OPENSSH |EC |)?PRIVATE KEY")),
    ("credentials", "openai_key_shape", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("credentials", "github_token_shape", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("credentials", "slack_token_shape", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("credentials", "aws_access_key_shape", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_path", "private_home_path", re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+(?:/|$)")),
    ("private_path", "private_chrome_profile", re.compile(r"Application Support/Google/Chrome")),
    ("private_path", "private_obsidian_path", re.compile(r"\.obsidian/|private Obsidian vault", re.IGNORECASE)),
    (
        "host_bound_transport",
        "browser_provider_symbol",
        re.compile(
            r"claude_app_injector|chatgpt_session_inject|claude_session_transport|"
            r"claude-in-chrome|gemini_web_session|browser_provider_session"
        ),
    ),
    ("host_bound_transport", "browser_debug_port", re.compile(r"(?:localhost|127\.0\.0\.1):922[0-9]\b")),
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
        if not path.is_absolute():
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
        "path": path.as_posix(),
        "line": line,
        "source": source,
        "policy_exception": path in policy_exception_paths,
        "match_sha256": _match_hash(matched_text),
    }


def _scan_file(path: Path, *, rel_path: Path, policy_exception_paths: set[Path]) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
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


def _resolve_gitleaks(binary: str | None) -> str | None:
    if not binary:
        return shutil.which("gitleaks")
    if "/" in binary:
        path = Path(binary)
        return str(path) if path.is_file() and path.stat().st_mode & 0o111 else None
    return shutil.which(binary)


def run_gitleaks(root: Path, *, required: bool = False, binary: str | None = None) -> dict[str, Any]:
    resolved = _resolve_gitleaks(binary)
    if not resolved:
        status = "unavailable_fail_closed" if required else "unavailable"
        return {
            "status": status,
            "finding_count": 0,
            "returncode": None,
            "required": required,
            "tool": "gitleaks",
        }
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_gitleaks_") as tmp:
        report_path = Path(tmp) / "gitleaks.json"
        proc = subprocess.run(
            [
                resolved,
                "detect",
                "--no-git",
                "--source",
                str(root),
                "--report-format",
                "json",
                "--report-path",
                str(report_path),
                "--exit-code",
                "97",
                "--no-banner",
                "--redact",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        findings: Any = []
        if report_path.is_file():
            try:
                findings = json.loads(report_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                findings = []
        finding_count = len(findings) if isinstance(findings, list) else 0
        if proc.returncode == 0:
            status = "pass"
        elif proc.returncode == 97:
            status = "red"
        else:
            status = "error"
        return {
            "status": status,
            "finding_count": finding_count,
            "returncode": proc.returncode,
            "required": required,
            "tool": "gitleaks",
            "stdout_sha256": _match_hash(proc.stdout or ""),
            "stderr_sha256": _match_hash(proc.stderr or ""),
        }


def _overall_status(
    *,
    blocking_hits: Sequence[Mapping[str, Any]],
    symlink_escapes: Sequence[Mapping[str, Any]],
    gitleaks_receipt: Mapping[str, Any],
) -> str:
    if blocking_hits or symlink_escapes:
        return "red"
    if gitleaks_receipt.get("status") in {"red", "error", "unavailable_fail_closed"}:
        return "red"
    return "green"


def scan_projection(
    root: Path,
    *,
    policy_exception_paths: Iterable[str | Path] | None = None,
    run_gitleaks_check: bool = False,
    require_gitleaks: bool = False,
    gitleaks_binary: str | None = None,
) -> dict[str, Any]:
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
                symlink_escapes.append({"path": rel.as_posix(), "target_sha256": _match_hash(str(target))})
            continue
        hits.extend(_scan_path(rel, policy_exception_paths=allowed))
        if path.is_file():
            file_count += 1
            hits.extend(_scan_file(path, rel_path=rel, policy_exception_paths=allowed))

    blocking_hits = [hit for hit in hits if not hit["policy_exception"]]
    policy_exceptions = [hit for hit in hits if hit["policy_exception"]]
    category_counts = Counter(str(hit["category"]) for hit in hits)
    blocking_category_counts = Counter(str(hit["category"]) for hit in blocking_hits)
    gitleaks_receipt = (
        run_gitleaks(output_root, required=require_gitleaks, binary=gitleaks_binary)
        if (run_gitleaks_check or require_gitleaks)
        else {"status": "not_run", "finding_count": 0, "required": require_gitleaks, "tool": "gitleaks"}
    )
    status = _overall_status(
        blocking_hits=blocking_hits,
        symlink_escapes=symlink_escapes,
        gitleaks_receipt=gitleaks_receipt,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
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
        "allowed_policy_exception_paths": sorted(path.as_posix() for path in allowed),
        "symlink_escape_count": len(symlink_escapes),
        "symlink_escapes": symlink_escapes,
        "gitleaks_status": gitleaks_receipt["status"],
        "gitleaks_finding_count": int(gitleaks_receipt.get("finding_count") or 0),
        "gitleaks_receipt": gitleaks_receipt,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
    }


def _assemble_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_assemble_value(item) for item in value)
    if isinstance(value, dict):
        if "literal" in value:
            return str(value["literal"])
        if "join_path" in value:
            parts = [str(part).strip("/") for part in value.get("join_path") or []]
            return "/" + "/".join(part for part in parts if part)
        if "join" in value:
            sep = str(value.get("sep", ""))
            return sep.join(str(part) for part in value.get("join") or [])
    return str(value)


def _safe_relative_path(raw: Any) -> Path:
    value = _assemble_value(raw)
    path = Path(value)
    if not value or path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"unsafe fixture path: {value!r}")
    return path


def _write_fixture_projection(case: Mapping[str, Any], projection_root: Path) -> None:
    for row in case.get("files") or []:
        if not isinstance(row, Mapping):
            raise ValueError("fixture file rows must be JSON objects")
        rel = _safe_relative_path(row.get("path") if "path" in row else row.get("path_parts"))
        text = _assemble_value(row.get("text_parts") if "text_parts" in row else row.get("text"))
        target = projection_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for row in case.get("symlinks") or []:
        if not isinstance(row, Mapping):
            raise ValueError("fixture symlink rows must be JSON objects")
        rel = _safe_relative_path(row.get("path") if "path" in row else row.get("path_parts"))
        target_rel = _safe_relative_path(row.get("target") or row.get("target_parts") or "target.txt")
        target = projection_root.parent / "external_targets" / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_assemble_value(row.get("target_text") or "external target\n"), encoding="utf-8")
        link = projection_root / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(target)


def evaluate_case(case: Mapping[str, Any], *, scratch: Path, path: str = "") -> dict[str, Any]:
    case_id = str(case.get("case_id") or Path(path).stem)
    projection_root = scratch / case_id / "projection"
    projection_root.mkdir(parents=True, exist_ok=True)
    _write_fixture_projection(case, projection_root)
    policy_paths = [_safe_relative_path(path_row) for path_row in case.get("policy_exception_paths") or []]
    receipt = scan_projection(
        projection_root,
        policy_exception_paths=policy_paths,
        run_gitleaks_check=bool(case.get("run_gitleaks")),
        require_gitleaks=bool(case.get("require_gitleaks")),
    )
    expected_status = str(case.get("expected_status") or "").strip().lower()
    verdict_basis = {
        "status": receipt["status"],
        "public_release_allowed_by_scan": receipt["public_release_allowed_by_scan"],
        "blocking_hit_count": receipt["blocking_hit_count"],
        "policy_exception_count": receipt["policy_exception_count"],
        "symlink_escape_count": receipt["symlink_escape_count"],
        "gitleaks_status": receipt["gitleaks_status"],
        "blocking_category_counts": receipt["blocking_category_counts"],
    }
    return {
        "case_id": case_id,
        "path": path,
        "expected_status": expected_status,
        "observed_status": receipt["status"],
        "expectation_met": bool(expected_status) and receipt["status"] == expected_status,
        "verdict_basis": verdict_basis,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_fixtures_") as tmp:
        scratch = Path(tmp)
        for path in sorted(input_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"{path} did not contain a JSON object")
            cases.append(evaluate_case(payload, scratch=scratch, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engine Room public projection leak gate capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan a rendered projection root.")
    scan.add_argument("--root", required=True)
    scan.add_argument("--policy-exception-path", action="append", default=[])
    scan.add_argument("--run-gitleaks", action="store_true")
    scan.add_argument("--require-gitleaks", action="store_true")
    scan.add_argument("--gitleaks-binary", default=None)
    scan.add_argument("--fail-on-blocking", action="store_true")
    scan.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "scan":
        try:
            payload = scan_projection(
                Path(args.root),
                policy_exception_paths=list(args.policy_exception_path or []),
                run_gitleaks_check=bool(args.run_gitleaks),
                require_gitleaks=bool(args.require_gitleaks),
                gitleaks_binary=args.gitleaks_binary,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {payload['status']}")
        return 1 if args.fail_on_blocking and payload["status"] != "green" else 0
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
