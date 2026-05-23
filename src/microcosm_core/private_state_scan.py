from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schemas import read_json_strict


PASS = "pass"
BLOCKED_PRIVATE = "blocked_private_state"
BLOCKED_PUBLIC_WRITE = "blocked_public_write_attempt"
BLOCKED_CASE_REVIEW = "blocked_case_review_required"

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
}

PUBLIC_ROOT_DIR_NAME = "microcosm-substrate"
PUBLIC_ROOT_RELATIVE_PREFIXES = (
    "AGENTS.md",
    "ANTI_PRINCIPLES.md",
    "AXIOMS.md",
    "CONSTITUTION.md",
    "PRINCIPLES.md",
    "README.md",
    "bootstrap.sh",
    "core/",
    "examples/",
    "fixtures/",
    "pyproject.toml",
    "receipts/",
    "src/",
    "tests/",
)


def load_forbidden_classes(path: str | Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: forbidden class policy must be a JSON object")
    return payload


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _public_root_for_path(path: str | Path) -> Path | None:
    raw_path = Path(path)
    resolved = _resolved(raw_path)
    start = resolved if raw_path.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == PUBLIC_ROOT_DIR_NAME:
            return candidate

    cwd = Path.cwd().resolve(strict=False)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        return None
    return cwd


def public_relative_path(path: str | Path, *, display_root: str | Path | None = None) -> str:
    raw_path = Path(path)
    if not raw_path.is_absolute():
        return raw_path.as_posix()

    resolved = _resolved(raw_path)
    roots: list[Path] = []
    if display_root is not None:
        roots.append(_resolved(Path(display_root)))
    inferred_root = _public_root_for_path(raw_path)
    if inferred_root is not None:
        roots.append(inferred_root)

    for root in roots:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    return resolved.as_posix()


def _infer_display_root(paths: list[Path]) -> Path | None:
    for path in paths:
        root = _public_root_for_path(path)
        if root is not None:
            return root
    return None


def _terms(forbidden_classes: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cls in forbidden_classes.get("classes", []):
        if not isinstance(cls, dict):
            continue
        class_id = str(cls.get("class_id") or "forbidden_content_body")
        remediation = str(
            cls.get("remediation") or "exclude credential/account-bound material"
        )
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


def _import_policy(forbidden_classes: dict[str, Any]) -> dict[str, Any]:
    policy = forbidden_classes.get("public_safe_macro_import", {})
    return policy if isinstance(policy, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _bool_from_row(row: dict[str, Any], key: str) -> bool:
    if key in row:
        return row.get(key) is True
    ceiling = row.get("authority_ceiling")
    if isinstance(ceiling, dict):
        return ceiling.get(key) is True
    return False


def classify_public_safe_macro_import(
    row: dict[str, Any],
    *,
    forbidden_classes: dict[str, Any],
) -> dict[str, Any]:
    """Classify one requested macro import without exposing credential-bound bodies."""

    policy = _import_policy(forbidden_classes)
    material_class = str(row.get("material_class") or "").strip()
    private_state_risk = str(
        row.get("credential_exposure_risk")
        or row.get("private_state_risk")
        or ""
    ).strip().lower()
    risk_routing = policy.get("risk_routing", {})
    if not isinstance(risk_routing, dict):
        risk_routing = {}
    route = str(risk_routing.get(private_state_risk) or "case_review")

    true_forbidden = set(_string_list(policy.get("true_forbidden_material_classes")))
    public_safe_classes = set(_string_list(policy.get("public_safe_body_material_classes")))
    required_fields = _string_list(policy.get("required_public_body_fields"))
    allowed_modes = set(_string_list(policy.get("allowed_public_safe_modes")))
    forbidden_flags = _string_list(policy.get("claim_ceiling_forbidden_flags"))

    findings: list[dict[str, Any]] = []
    if material_class in true_forbidden:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_TRUE_FORBIDDEN_CLASS",
                "message": "Credential-bound, operator, provider, or raw-seed material classes cannot enter verified macro import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )
    elif material_class not in public_safe_classes:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_UNKNOWN_BODY_CLASS",
                "message": "Body-bearing material must declare a verified public macro body class.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    if route in {"case_review", "case_review_for_secret_risk"}:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_CASE_REVIEW_REQUIRED",
                "message": "Medium or unclassified secret/account-bound risk requires case review before body import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )
    elif route in {"synthetic_only", "credential_or_account_bound_exclusion"}:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_SYNTHETIC_ONLY",
                "message": "High credential/account-bound risk is excluded from real macro import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    public_safe_mode = str(row.get("public_safe_mode") or "").strip()
    if public_safe_mode not in allowed_modes:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_MODE_UNSUPPORTED",
                "message": "Verified macro body import must use an allowed real-substrate mode.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    missing_fields: list[str] = []
    for field in required_fields:
        value = row.get(field)
        if isinstance(value, list):
            if not _string_list(value):
                missing_fields.append(field)
        elif value in (None, "", False):
            missing_fields.append(field)
    if missing_fields:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_PROVENANCE_MISSING",
                "message": "Verified macro body import requires source, provenance, validation, risk, mode, claim floor, and body verification fields.",
                "missing_fields": missing_fields,
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    forbidden_claim_flags = [flag for flag in forbidden_flags if _bool_from_row(row, flag)]
    if row.get("claims_source_authority") is True:
        forbidden_claim_flags.append("claims_source_authority")
    if forbidden_claim_flags:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_AUTHORITY_OVERCLAIM",
                "message": "Verified macro body import cannot upgrade itself into hosted publication, account/root mirror, or whole-system authority.",
                "forbidden_flags": sorted(set(forbidden_claim_flags)),
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    if findings:
        status = BLOCKED_CASE_REVIEW if route == "case_review" else BLOCKED_PRIVATE
    else:
        status = PASS

    return {
        "status": status,
        "route": route,
        "material_class": material_class,
        "credential_exposure_risk": private_state_risk,
        "public_safe_mode": public_safe_mode,
        "flow_allowed": status == PASS,
        "findings": findings,
        "body_redacted": True,
    }


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
    is_public_root_path = "microcosm-substrate" in normalized or any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in PUBLIC_ROOT_RELATIVE_PREFIXES
    )
    if is_public_root_path:
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
    display_root: str | Path | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    scanned = 0
    scan_paths = [Path(raw_path) for raw_path in paths]
    root = Path(display_root).resolve(strict=False) if display_root is not None else _infer_display_root(scan_paths)
    for path in scan_paths:
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        scanned += 1
        results.append(
            scan_text(
                path.read_text(encoding="utf-8"),
                path=public_relative_path(path, display_root=root),
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
