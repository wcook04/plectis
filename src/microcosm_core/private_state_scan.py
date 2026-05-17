"""Private-state scan for public fixture bodies."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from microcosm_core.receipts import make_receipt, write_json


DEFAULT_FORBIDDEN = Path("core/private_state_forbidden_classes.json")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "dist", "build"}


@dataclass(frozen=True)
class Hit:
    path: str
    class_id: str
    pattern: str
    line_number: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "class_id": self.class_id,
            "pattern": self.pattern,
            "line_number": self.line_number,
            "error_code": "FORBIDDEN_PRIVATE_STATE_CLASS",
        }


def load_policy(root: Path, policy_path: Path | None = None) -> dict[str, Any]:
    resolved = policy_path or root / DEFAULT_FORBIDDEN
    with resolved.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def is_body_sensitive(rel: Path, policy: dict[str, Any]) -> bool:
    roots = set(policy.get("body_sensitive_roots", []))
    return bool(rel.parts and rel.parts[0] in roots)


def is_rule_carrier(rel: Path, policy: dict[str, Any]) -> bool:
    rel_posix = rel.as_posix()
    if rel_posix in set(policy.get("rule_carrier_paths", [])):
        return True
    return rel_posix.startswith("src/microcosm_core/")


def scan_text(rel: Path, text: str, policy: dict[str, Any]) -> list[Hit]:
    hits: list[Hit] = []
    lowered_lines = [line.lower() for line in text.splitlines()]
    for rule in policy.get("classes", []):
        class_id = str(rule["class_id"])
        for pattern in rule.get("patterns", []):
            needle = str(pattern).lower()
            for index, line in enumerate(lowered_lines, start=1):
                if needle in line:
                    hits.append(Hit(rel.as_posix(), class_id, pattern, index))
    return hits


def run_scan(root: Path, policy_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    policy = load_policy(root, policy_path)
    scanned_files: list[str] = []
    sensitive_files: list[str] = []
    rule_carrier_files: list[str] = []
    forbidden_hits: list[Hit] = []
    unreadable_files: list[dict[str, str]] = []

    for path in iter_files(root):
        rel = path.relative_to(root)
        rel_posix = rel.as_posix()
        scanned_files.append(rel_posix)

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            unreadable_files.append({"path": rel_posix, "reason": "non_utf8_skipped"})
            continue

        if is_rule_carrier(rel, policy):
            rule_carrier_files.append(rel_posix)
            continue

        if is_body_sensitive(rel, policy):
            sensitive_files.append(rel_posix)
            forbidden_hits.extend(scan_text(rel, text, policy))

    status = "pass" if not forbidden_hits else "fail"
    return make_receipt(
        receipt_type="private_state_scan",
        status=status,
        command="python -m microcosm_core.validators.private_state_scan --root . --out receipts/first_wave/private_state_scan.json",
        payload={
            "root": str(root),
            "scanned_file_count": len(scanned_files),
            "body_sensitive_file_count": len(sensitive_files),
            "rule_carrier_file_count": len(rule_carrier_files),
            "unreadable_files": unreadable_files,
            "forbidden_class_hits": [hit.as_dict() for hit in forbidden_hits],
            "body_sensitive_roots": policy.get("body_sensitive_roots", []),
            "rule_carrier_files": rule_carrier_files,
            "anti_claim": "The scan checks configured body-sensitive public roots for forbidden class terms; it does not prove future organs are safe.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan public microcosm fixture bodies for forbidden private-state classes.")
    parser.add_argument("--root", default=".", help="Root to scan.")
    parser.add_argument("--out", required=True, help="Receipt output path.")
    parser.add_argument("--forbidden-classes", default=None, help="Optional policy JSON path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root)
    policy_path = Path(args.forbidden_classes) if args.forbidden_classes else None
    receipt = run_scan(root, policy_path)
    write_json(args.out, receipt)
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

