from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import read_json_strict


PASS = "pass"
BLOCKED_PRIVATE = "blocked_private_state"
BLOCKED_PUBLIC_WRITE = "blocked_public_write_attempt"

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
}


def load_forbidden_classes(path: str | Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: forbidden class policy must be a JSON object")
    return payload


def _terms(forbidden_classes: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cls in forbidden_classes.get("classes", []):
        if not isinstance(cls, dict):
            continue
        class_id = str(cls.get("class_id") or "forbidden_content_body")
        remediation = str(cls.get("remediation") or "replace with synthetic fixture")
        for term in cls.get("terms", []):
            if not isinstance(term, dict):
                continue
            token = str(term.get("token") or "").strip()
            term_id = str(term.get("term_id") or token).strip()
            if token:
                rows.append(
                    {
                        "forbidden_class": class_id,
                        "term_id": term_id,
                        "token": token,
                        "remediation": remediation,
                    }
                )
    return rows


def _allowed_synthetic_negative(path: str, text: str) -> bool:
    lowered = path.lower()
    if lowered.endswith("core/private_state_forbidden_classes.json"):
        return True
    if lowered.endswith("private_state_forbidden_terms.json"):
        return True
    if lowered.startswith("tests/") or "/tests/" in lowered:
        return True
    if "pattern_binding_contract/input" not in lowered:
        return False
    markers = (
        '"expected_negative_case": true',
        '"expected_negative_case_id"',
        '"negative_case_id"',
        '"synthetic_negative_fixture": true',
    )
    return any(marker in text for marker in markers)


def _path_hit(path: str, source_context: str) -> dict[str, Any] | None:
    if source_context == "target":
        return None
    normalized = path.replace("\\", "/")
    if "microcosm-substrate" in normalized:
        return {
            "path": path,
            "forbidden_class": "target_only_not_source",
            "term_id": "microcosm_substrate_as_source_authority",
            "body_redacted": True,
            "remediation": "treat public root paths as target paths, not source authority",
        }
    return None


def scan_text(
    text: str,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    path_based = _path_hit(path, source_context)
    if path_based is not None:
        hits.append(path_based)

    allowed_negative = _allowed_synthetic_negative(path, text)
    for term in _terms(forbidden_classes):
        if term["token"] not in text:
            continue
        hit = {
            "path": path,
            "forbidden_class": term["forbidden_class"],
            "term_id": term["term_id"],
            "body_redacted": True,
            "remediation": term["remediation"],
        }
        if allowed_negative:
            hit["expected_negative_case"] = True
        hits.append(hit)

    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_PRIVATE
    else:
        status = PASS
    return {
        "status": status,
        "hits": hits,
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
    }


def _merge_scan_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for result in results:
        hits.extend(result.get("hits", []))
    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_PRIVATE
    else:
        status = PASS
    return {
        "status": status,
        "hits": hits,
        "hit_count": len(hits),
        "blocking_hit_count": len(blocking_hits),
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
    }


def scan_paths(
    paths: list[str | Path],
    *,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    scanned = 0
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        scanned += 1
        results.append(
            scan_text(
                path.read_text(encoding="utf-8"),
                path=path.as_posix(),
                forbidden_classes=forbidden_classes,
                source_context=source_context,
            )
        )
    merged = _merge_scan_results(results)
    merged["scanned_path_count"] = scanned
    return merged


def scan_json_payload(
    payload: object,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return scan_text(text, path=path, forbidden_classes=forbidden_classes, source_context=source_context)
