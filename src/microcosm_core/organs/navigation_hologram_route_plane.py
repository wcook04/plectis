from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import base_receipt, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "navigation_hologram_route_plane"
FIXTURE_ID = "first_wave.navigation_hologram_route_plane"
VALIDATOR_ID = "validator.microcosm.organs.navigation_hologram_route_plane"

PREFLIGHT_REL = "receipts/preflight/navigation_hologram_route_plane.json"
CLUSTER_FLAG_NAME = "toy_kind_cluster_flag.json"
CARD_NAME = "toy_kind_card.json"
SOURCE_COUPLING_NAME = "source_coupling_result.json"
ROUTE_LEASE_NAME = "route_lease.json"
ENTRY_ADMISSION_NAME = "entry_payload_admission_receipt.json"
AFFORDANCE_NAME = "affordance_passport_selection_receipt.json"
CODE_ARCH_NAME = "code_architecture_projection_packet_receipt.json"
ROUTE_PLANE_BUNDLE_RESULT_NAME = "exported_route_plane_bundle_validation_result.json"

EXPECTED_RECEIPT_PATHS = [
    PREFLIGHT_REL,
    "receipts/first_wave/navigation_hologram_route_plane/toy_kind_cluster_flag.json",
    "receipts/first_wave/navigation_hologram_route_plane/toy_kind_card.json",
    "receipts/first_wave/navigation_hologram_route_plane/source_coupling_result.json",
    "receipts/first_wave/navigation_hologram_route_plane/route_lease.json",
    "receipts/first_wave/navigation_hologram_route_plane/entry_payload_admission_receipt.json",
    "receipts/first_wave/navigation_hologram_route_plane/affordance_passport_selection_receipt.json",
    "receipts/first_wave/navigation_hologram_route_plane/code_architecture_projection_packet_receipt.json",
]
EXPORTED_ROUTE_PLANE_BUNDLE_RECEIPT_PATH = (
    "receipts/first_wave/navigation_hologram_route_plane/"
    "exported_route_plane_bundle_validation_result.json"
)

EXPECTED_NEGATIVE_CASES = {
    "stale_source_and_banned_first_contact": [
        "BANNED_FIRST_CONTACT_ROUTE",
        "SOURCE_COUPLING_STALE",
    ],
    "route_packet_missing_omission_receipt": ["MISSING_OMISSION_RECEIPT"],
    "atlas_projection_claims_control_entry_authority": ["ATLAS_PROJECTION_NOT_CONTROL_ENTRY"],
    "route_card_private_body_leak": ["ROUTE_CARD_PRIVATE_BODY_LEAK"],
    "route_summary_overclaims_freshness": ["ROUTE_SUMMARY_OVERCLAIMS_FRESHNESS"],
    "duplicate_route_id_conflict": ["DUPLICATE_ROUTE_ID_CONFLICT"],
    "entry_admission_dropped_control_floor": ["ENTRY_ADMISSION_CONTROL_FLOOR_DROPPED"],
    "affordance_passport_antitrigger_ignored": [
        "AFFORDANCE_PASSPORT_ANTITRIGGER_IGNORED"
    ],
}

NAV_AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "navigation_receipts_are_public_toy_route_projections_not_source_authority",
    "atlas_projection_control_entry_rejected": True,
    "banned_first_contact_route_replaced": True,
    "route_lease_source_authority_rejected": True,
}
NAV_ANTI_CLAIM = (
    "Navigation route-plane receipts validate public route projections and regression fixtures; "
    "they do not prove live route freshness, grant source authority, authorize later organs, "
    "or certify whole Wave 1."
)

SOURCE_PATTERN_IDS = [
    "navigation_hologram_unified_route_plane",
    "agent_entry_surfaces_canonical_first_move",
    "omission_receipt_reversible_projection_boundary",
    "semantic_routing_plane",
    "system_atlas_source_coupling_gate",
    "entry_payload_admission_nonnegotiable_floor",
    "affordance_passport_selection_gate",
]

VALIDATOR_ASSERTED_FEEDS_PATTERNS = [
    {
        "assertion_id": "cluster_first_route_feeds_agent_entry_surface",
        "source_pattern_id": "navigation_hologram_unified_route_plane",
        "status": PASS,
    },
    {
        "assertion_id": "omission_receipt_boundary_feeds_card_drilldown",
        "source_pattern_id": "omission_receipt_reversible_projection_boundary",
        "status": PASS,
    },
    {
        "assertion_id": "affordance_passport_gate_feeds_route_selection",
        "source_pattern_id": "affordance_passport_selection_gate",
        "status": PASS,
    },
]


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _input_paths(input_dir: Path) -> list[Path]:
    names = (
        "toy_kind_rows.json",
        "std_toy_option_surface.json",
        "source_manifest_stale.json",
        "banned_route_request.json",
        "route_lease_baseline.json",
        "route_card_missing_omission_receipt.json",
        "atlas_projection_as_control_entry.json",
        "route_card_with_private_body.json",
        "stale_summary_claims_current.json",
        "duplicate_route_ids.json",
        "entry_packet_admission_floor.json",
        "affordance_passport_selection.json",
        "code_architecture_projection_packet.json",
    )
    return [input_dir / name for name in names]


def _route_plane_bundle_paths(input_dir: Path) -> list[Path]:
    names = (
        "bundle_manifest.json",
        "route_rows.json",
        "option_surface_contract.json",
        "source_coupling_manifest.json",
        "entry_packet_floor.json",
        "route_lease_policy.json",
        "affordance_passports.json",
        "code_architecture_projection_packet.json",
    )
    return [input_dir / name for name in names]


def _scan_fixture_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(_input_paths(input_dir), forbidden_classes=policy, display_root=public_root)


def _scan_bundle_inputs(input_dir: Path, public_root: Path) -> dict[str, Any]:
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    return scan_paths(
        _route_plane_bundle_paths(input_dir),
        forbidden_classes=policy,
        display_root=public_root,
    )


def _load_inputs(input_dir: Path) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir)
    }


def _load_route_plane_bundle(input_dir: Path) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _route_plane_bundle_paths(input_dir)
    }


def _stable_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def build_toy_option_surface(rows_payload: object, standard_payload: object) -> dict[str, Any]:
    rows = _rows(rows_payload, "rows")
    standard = standard_payload if isinstance(standard_payload, dict) else {}
    clusters: dict[str, dict[str, Any]] = {}
    for row in rows:
        cluster_id = str(row.get("cluster_id") or "uncategorized")
        clusters.setdefault(
            cluster_id,
            {
                "cluster_id": cluster_id,
                "row_count": 0,
                "row_ids": [],
                "drilldown_command": f"microcosm option-surface toy --cluster {cluster_id}",
            },
        )
        clusters[cluster_id]["row_count"] += 1
        clusters[cluster_id]["row_ids"].append(str(row.get("row_id") or "row"))

    selected = next(
        (row for row in rows if row.get("row_id") == standard.get("card_row_id")),
        rows[0] if rows else {},
    )
    card = {
        "row_id": str(selected.get("row_id") or "missing_row"),
        "stable_handle": f"toy:{selected.get('kind_id', 'kind')}:{selected.get('row_id', 'row')}",
        "title": selected.get("title"),
        "band_payload": (selected.get("band_payloads") or {}).get("card"),
        "source_refs": selected.get("source_refs", []),
        "omission_receipt": selected.get("omission_receipt"),
        "anti_claim": NAV_ANTI_CLAIM,
    }
    return {
        "cluster_flag": {
            "clusters": sorted(clusters.values(), key=lambda item: item["cluster_id"]),
            "row_counts": {
                cluster_id: payload["row_count"]
                for cluster_id, payload in sorted(clusters.items())
            },
            "drilldown_commands": [
                payload["drilldown_command"]
                for payload in sorted(clusters.values(), key=lambda item: item["cluster_id"])
            ],
            "source_coupling_status": "toy_fixture_current",
        },
        "card": card,
        "selected_row_ids": [card["row_id"]],
    }


def validate_exported_route_rows(
    rows_payload: object,
    contract_payload: object,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    rows = _rows(rows_payload, "rows")
    contract = contract_payload if isinstance(contract_payload, dict) else {}
    required_role = str(contract.get("required_surface_role") or "ATLAS_PROJECTION")
    card_row_id = str(contract.get("card_row_id") or "")
    selected = next((row for row in rows if row.get("row_id") == card_row_id), None)
    clusters: dict[str, dict[str, Any]] = {}

    if not rows:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_BUNDLE_ROWS_MISSING",
                "message": "Exported route-plane bundle has no route rows.",
                "subject_id": "route_rows",
                "subject_kind": "route_plane_bundle",
                "body_redacted": True,
            }
        )

    route_ids = [str(row.get("route_id") or "") for row in rows]
    duplicate_ids = sorted(
        route_id for route_id, count in Counter(route_ids).items() if route_id and count > 1
    )
    for route_id in duplicate_ids:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_BUNDLE_DUPLICATE_ROUTE_ID",
                "message": "Exported route-plane bundle contains a duplicate route id.",
                "subject_id": route_id,
                "subject_kind": "route_plane_bundle",
                "body_redacted": True,
            }
        )

    if selected is None:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_BUNDLE_CARD_ROW_MISSING",
                "message": "Exported route-plane bundle does not contain the contracted card row.",
                "subject_id": card_row_id or "missing_card_row_id",
                "subject_kind": "option_surface_contract",
                "body_redacted": True,
            }
        )
        selected = rows[0] if rows else {}

    for row in rows:
        row_id = str(row.get("row_id") or "row")
        cluster_id = str(row.get("cluster_id") or "uncategorized")
        clusters.setdefault(
            cluster_id,
            {
                "cluster_id": cluster_id,
                "row_count": 0,
                "row_ids": [],
                "drilldown_command": f"microcosm option-surface route-plane --cluster {cluster_id}",
            },
        )
        clusters[cluster_id]["row_count"] += 1
        clusters[cluster_id]["row_ids"].append(row_id)
        if row.get("surface_role") != required_role:
            findings.append(
                {
                    "error_code": "ROUTE_PLANE_BUNDLE_SURFACE_ROLE_MISMATCH",
                    "message": "Exported route row does not carry the contracted projection role.",
                    "subject_id": row_id,
                    "subject_kind": "route_row",
                    "body_redacted": True,
                }
            )
        if row.get("claims_source_authority") or row.get("claims_control_entry"):
            findings.append(
                {
                    "error_code": "ROUTE_PLANE_BUNDLE_OVERCLAIMS_AUTHORITY",
                    "message": "Exported route row attempted to act as source authority.",
                    "subject_id": row_id,
                    "subject_kind": "route_row",
                    "body_redacted": True,
                }
            )
        if not isinstance(row.get("omission_receipt"), dict):
            findings.append(
                {
                    "error_code": "ROUTE_PLANE_BUNDLE_OMISSION_RECEIPT_MISSING",
                    "message": "Exported route row lacks an omission receipt.",
                    "subject_id": row_id,
                    "subject_kind": "route_row",
                    "body_redacted": True,
                }
            )

    selected_row_id = str(selected.get("row_id") or "missing_row")
    card = {
        "row_id": selected_row_id,
        "stable_handle": f"route-plane:{selected.get('route_id', 'route')}:{selected_row_id}",
        "title": selected.get("title"),
        "band_payload": (selected.get("band_payloads") or {}).get("card"),
        "source_refs": selected.get("source_refs", []),
        "omission_receipt": selected.get("omission_receipt"),
        "anti_claim": NAV_ANTI_CLAIM,
    }
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "cluster_flag": {
            "clusters": sorted(clusters.values(), key=lambda item: item["cluster_id"]),
            "row_counts": {
                cluster_id: payload["row_count"]
                for cluster_id, payload in sorted(clusters.items())
            },
            "drilldown_commands": [
                payload["drilldown_command"]
                for payload in sorted(clusters.values(), key=lambda item: item["cluster_id"])
            ],
            "source_coupling_status": "exported_route_plane_bundle_current",
        },
        "card": card,
        "selected_row_ids": [selected_row_id] if selected_row_id != "missing_row" else [],
        "duplicate_route_ids": duplicate_ids,
        "route_rows": rows,
        "route_rows_projection_not_authority": True,
    }


def validate_exported_source_coupling(
    manifest_payload: object,
    route_rows_payload: object,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    manifest = manifest_payload if isinstance(manifest_payload, dict) else {}
    route_rows = _rows(route_rows_payload, "rows")
    expected_sha = str(manifest.get("route_rows_sha256") or "")
    observed_sha = _stable_hash(route_rows)
    expected_count = int(manifest.get("expected_route_row_count") or 0)
    status_value = str(manifest.get("source_coupling_status") or "")

    if expected_count != len(route_rows):
        findings.append(
            {
                "error_code": "ROUTE_PLANE_SOURCE_ROW_COUNT_MISMATCH",
                "message": "Source-coupling manifest row count does not match route rows.",
                "subject_id": str(manifest.get("manifest_id") or "source_coupling_manifest"),
                "subject_kind": "source_coupling_manifest",
                "body_redacted": True,
            }
        )
    if expected_sha != observed_sha:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_SOURCE_FINGERPRINT_MISMATCH",
                "message": "Source-coupling manifest fingerprint does not match route rows.",
                "subject_id": str(manifest.get("manifest_id") or "source_coupling_manifest"),
                "subject_kind": "source_coupling_manifest",
                "body_redacted": True,
            }
        )
    if status_value not in (PASS, "current"):
        findings.append(
            {
                "error_code": "ROUTE_PLANE_SOURCE_COUPLING_NOT_CURRENT",
                "message": "Source-coupling manifest does not declare current public projection state.",
                "subject_id": str(manifest.get("manifest_id") or "source_coupling_manifest"),
                "subject_kind": "source_coupling_manifest",
                "body_redacted": True,
            }
        )
    if manifest.get("projection_not_authority") is not True:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_SOURCE_AUTHORITY_NOT_REJECTED",
                "message": "Source-coupling manifest must reject projection-as-authority.",
                "subject_id": str(manifest.get("manifest_id") or "source_coupling_manifest"),
                "subject_kind": "source_coupling_manifest",
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "expected_sha256": expected_sha,
        "observed_sha256": observed_sha,
        "source_coupling_status": PASS if not findings else "blocked",
        "authority_allowed": False,
    }


def validate_source_coupling_freshness(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    expected = ""
    observed_hash = ""
    subject_id = "source_manifest_stale"
    if isinstance(payload, dict):
        subject_id = str(payload.get("manifest_id") or subject_id)
        expected = str(payload.get("rendered_source_sha256") or "")
        observed_hash = _stable_hash(payload.get("current_source_rows", []))
    if expected != observed_hash:
        _record(
            findings,
            observed,
            "SOURCE_COUPLING_STALE",
            "Source-coupling fingerprint is stale, so projection authority is denied.",
            case_id="stale_source_and_banned_first_contact",
            subject_id=subject_id,
            subject_kind="source_manifest",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "expected_sha256": expected,
        "observed_sha256": observed_hash,
        "source_coupling_status": "stale" if findings else PASS,
        "authority_allowed": not findings,
    }


def validate_banned_route_replacement(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    banned_route_replacements: list[dict[str, Any]] = []
    if isinstance(payload, dict) and payload.get("first_contact_requested"):
        route_id = str(payload.get("route_id") or "route")
        if payload.get("surface_role") != "CONTROL_ENTRY":
            replacement = str(payload.get("expected_replacement_route") or "entry_packet")
            banned_route_replacements.append(
                {
                    "route_id": route_id,
                    "replacement_route": replacement,
                    "reason_code": "BANNED_FIRST_CONTACT_ROUTE",
                    "body_redacted": True,
                }
            )
            _record(
                findings,
                observed,
                "BANNED_FIRST_CONTACT_ROUTE",
                "First contact attempted to start from a drilldown projection.",
                case_id="stale_source_and_banned_first_contact",
                subject_id=route_id,
                subject_kind="route_request",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "banned_route_replacements": banned_route_replacements,
    }


def validate_route_packet_missing_omission(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "route_card_missing_omission_receipt"
    if isinstance(payload, dict):
        subject_id = str(payload.get("route_id") or subject_id)
        if "omission_receipt" not in payload:
            _record(
                findings,
                observed,
                "MISSING_OMISSION_RECEIPT",
                "Compressed route card lacks an omission receipt.",
                case_id="route_packet_missing_omission_receipt",
                subject_id=subject_id,
                subject_kind="route_card",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_atlas_projection_authority(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "atlas_projection_as_control_entry"
    if isinstance(payload, dict):
        subject_id = str(payload.get("route_id") or subject_id)
        if payload.get("claims_control_entry") and payload.get("surface_role") != "CONTROL_ENTRY":
            _record(
                findings,
                observed,
                "ATLAS_PROJECTION_NOT_CONTROL_ENTRY",
                "Atlas projection attempted to act as first-contact control entry.",
                case_id="atlas_projection_claims_control_entry_authority",
                subject_id=subject_id,
                subject_kind="route_request",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_route_card_boundary(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "route_card_with_private_boundary_marker"
    if isinstance(payload, dict):
        subject_id = str(payload.get("route_id") or subject_id)
        if payload.get("forbidden_content_value_present") or payload.get("forbidden_content_class"):
            _record(
                findings,
                observed,
                "ROUTE_CARD_PRIVATE_BODY_LEAK",
                "Route card fixture marks a forbidden content value class and is rejected.",
                case_id="route_card_private_body_leak",
                subject_id=subject_id,
                subject_kind="route_card",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_summary_freshness(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    subject_id = "stale_summary_claims_current"
    if isinstance(payload, dict):
        subject_id = str(payload.get("summary_id") or subject_id)
        is_stale = payload.get("source_coupling_status") not in ("pass", "current")
        if payload.get("claims_current_source_authority") and is_stale:
            _record(
                findings,
                observed,
                "ROUTE_SUMMARY_OVERCLAIMS_FRESHNESS",
                "Route summary claimed current authority while source coupling is stale.",
                case_id="route_summary_overclaims_freshness",
                subject_id=subject_id,
                subject_kind="route_summary",
            )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_duplicate_route_ids(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    route_ids = [str(row.get("route_id") or "") for row in _rows(payload, "routes")]
    duplicate_ids = sorted(route_id for route_id, count in Counter(route_ids).items() if route_id and count > 1)
    for route_id in duplicate_ids:
        _record(
            findings,
            observed,
            "DUPLICATE_ROUTE_ID_CONFLICT",
            "Route table contains a duplicate route id.",
            case_id="duplicate_route_id_conflict",
            subject_id=route_id,
            subject_kind="route_table",
        )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "duplicate_route_ids": duplicate_ids,
    }


def validate_entry_payload_admission_floor(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    if not isinstance(payload, dict):
        payload = {}
    required = [str(item) for item in payload.get("required_non_negotiable_fields", [])]
    admitted = payload.get("admitted_payload", {})
    compacted_negative = payload.get("negative_compacted_payload", {})
    if not isinstance(admitted, dict):
        admitted = {}
    if not isinstance(compacted_negative, dict):
        compacted_negative = {}

    preserved = [field for field in required if _has_dotted(admitted, field)]
    dropped = [field for field in required if not _has_dotted(compacted_negative, field)]
    for field in dropped:
        _record(
            findings,
            observed,
            "ENTRY_ADMISSION_CONTROL_FLOOR_DROPPED",
            "Entry payload compaction dropped a required control-floor field.",
            case_id="entry_admission_dropped_control_floor",
            subject_id=field,
            subject_kind="entry_payload",
        )
    before_bytes = int(payload.get("before_bytes") or 0)
    after_bytes = int(payload.get("after_bytes") or 0)
    inline_target = int(payload.get("inline_target_bytes") or 0)
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "entry_payload_admission_status": "trimmed",
        "inline_target_bytes": inline_target,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "saved_bytes": max(before_bytes - after_bytes, 0),
        "preserved_non_negotiable_fields": preserved,
        "dropped_control_fields": dropped,
        "omission_receipts": payload.get("omission_receipts", []),
    }


def validate_exported_entry_packet_floor(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        payload = {}
    required = [str(item) for item in payload.get("required_non_negotiable_fields", [])]
    admitted = payload.get("admitted_payload", {})
    if not isinstance(admitted, dict):
        admitted = {}

    preserved = [field for field in required if _has_dotted(admitted, field)]
    missing = [field for field in required if not _has_dotted(admitted, field)]
    for field in missing:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_ENTRY_PACKET_FIELD_MISSING",
                "message": "Exported entry packet floor is missing a required control field.",
                "subject_id": field,
                "subject_kind": "entry_packet_floor",
                "body_redacted": True,
            }
        )
    before_bytes = int(payload.get("before_bytes") or 0)
    after_bytes = int(payload.get("after_bytes") or 0)
    inline_target = int(payload.get("inline_target_bytes") or 0)
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "entry_payload_admission_status": PASS if not missing else "blocked",
        "inline_target_bytes": inline_target,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "saved_bytes": max(before_bytes - after_bytes, 0),
        "preserved_non_negotiable_fields": preserved,
        "dropped_control_fields": missing,
        "omission_receipts": payload.get("omission_receipts", []),
    }


def _has_dotted(payload: dict[str, Any], dotted: str) -> bool:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def validate_affordance_passport_selection(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows = _rows(payload, "rows")
    selected_row_id = ""
    demoted_rows: list[dict[str, Any]] = []
    anti_trigger_hits: list[dict[str, Any]] = []
    passport_coverage: dict[str, bool] = {}
    safe_drilldown = ""

    for row in rows:
        row_id = str(row.get("row_id") or "row")
        passport = row.get("affordance_passport")
        passport_coverage[row_id] = isinstance(passport, dict)
        if isinstance(passport, dict) and passport.get("anti_trigger_hit"):
            anti_trigger_hits.append({"row_id": row_id, "body_redacted": True})
            demoted_rows.append(
                {
                    "row_id": row_id,
                    "reason_code": "AFFORDANCE_PASSPORT_ANTITRIGGER_IGNORED",
                    "body_redacted": True,
                }
            )
            _record(
                findings,
                observed,
                "AFFORDANCE_PASSPORT_ANTITRIGGER_IGNORED",
                "Anti-trigger row is demoted before similarity can select authority.",
                case_id="affordance_passport_antitrigger_ignored",
                subject_id=row_id,
                subject_kind="affordance_row",
            )
            continue
        if not isinstance(passport, dict):
            demoted_rows.append(
                {
                    "row_id": row_id,
                    "reason_code": "AFFORDANCE_PASSPORT_ABSENT",
                    "body_redacted": True,
                }
            )
            continue
        if passport.get("compatibility") == "compatible" and passport.get("safe_drilldown"):
            if not selected_row_id:
                selected_row_id = row_id
                safe_drilldown = str(passport["safe_drilldown"])
        else:
            demoted_rows.append(
                {
                    "row_id": row_id,
                    "reason_code": "AFFORDANCE_PASSPORT_NOT_COMPATIBLE",
                    "body_redacted": True,
                }
            )

    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
        "affordance_compatibility": {
            "selected_row_id": selected_row_id,
            "status": PASS if selected_row_id else "blocked",
        },
        "anti_trigger_hits": anti_trigger_hits,
        "demotion_receipt": {
            "status": PASS,
            "demoted_row_count": len(demoted_rows),
            "body_redacted": True,
        },
        "selection_decision": "select_compatible_passport_after_demotion",
        "selected_row_id": selected_row_id,
        "passport_coverage": passport_coverage,
        "demoted_rows": demoted_rows,
        "safe_drilldown": safe_drilldown,
    }


def validate_exported_affordance_passports(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "rows")
    findings: list[dict[str, Any]] = []
    selected_row_id = ""
    demoted_rows: list[dict[str, Any]] = []
    anti_trigger_hits: list[dict[str, Any]] = []
    passport_coverage: dict[str, bool] = {}
    safe_drilldown = ""

    for row in rows:
        row_id = str(row.get("row_id") or "row")
        passport = row.get("affordance_passport")
        passport_coverage[row_id] = isinstance(passport, dict)
        if isinstance(passport, dict) and passport.get("anti_trigger_hit"):
            anti_trigger_hits.append({"row_id": row_id, "body_redacted": True})
            demoted_rows.append(
                {
                    "row_id": row_id,
                    "reason_code": "AFFORDANCE_PASSPORT_ANTITRIGGER_DEMOTED",
                    "body_redacted": True,
                }
            )
            continue
        if isinstance(passport, dict) and passport.get("compatibility") == "compatible":
            safe_drilldown_value = passport.get("safe_drilldown")
            if safe_drilldown_value and not selected_row_id:
                selected_row_id = row_id
                safe_drilldown = str(safe_drilldown_value)
                continue
        demoted_rows.append(
            {
                "row_id": row_id,
                "reason_code": "AFFORDANCE_PASSPORT_NOT_SELECTED",
                "body_redacted": True,
            }
        )

    if not selected_row_id:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_AFFORDANCE_PASSPORT_MISSING_SELECTION",
                "message": "Exported route-plane bundle has no compatible affordance passport.",
                "subject_id": "affordance_passports",
                "subject_kind": "affordance_passport_table",
                "body_redacted": True,
            }
        )

    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": {},
        "affordance_compatibility": {
            "selected_row_id": selected_row_id,
            "status": PASS if selected_row_id else "blocked",
        },
        "anti_trigger_hits": anti_trigger_hits,
        "demotion_receipt": {
            "status": PASS,
            "demoted_row_count": len(demoted_rows),
            "body_redacted": True,
        },
        "selection_decision": "select_compatible_passport_after_demotion",
        "selected_row_id": selected_row_id,
        "passport_coverage": passport_coverage,
        "demoted_rows": demoted_rows,
        "safe_drilldown": safe_drilldown,
    }


def validate_exported_route_lease_policy(payload: object) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        payload = {}
    selected_lane_id = str(payload.get("selected_lane_id") or "")
    permitted = payload.get("permitted_direct_actions", [])
    invalidation = payload.get("invalidation_inputs", {})
    if not selected_lane_id:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_ROUTE_LEASE_LANE_MISSING",
                "message": "Exported route lease policy has no selected lane.",
                "subject_id": "route_lease_policy",
                "subject_kind": "route_lease_policy",
                "body_redacted": True,
            }
        )
    if not isinstance(permitted, list) or not permitted:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_ROUTE_LEASE_ACTIONS_MISSING",
                "message": "Exported route lease policy has no permitted direct actions.",
                "subject_id": selected_lane_id or "route_lease_policy",
                "subject_kind": "route_lease_policy",
                "body_redacted": True,
            }
        )
        permitted = []
    if not isinstance(invalidation, dict) or "navigation_index_currentness" not in invalidation:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_ROUTE_LEASE_INVALIDATION_MISSING",
                "message": "Exported route lease policy lacks navigation invalidation input.",
                "subject_id": selected_lane_id or "route_lease_policy",
                "subject_kind": "route_lease_policy",
                "body_redacted": True,
            }
        )
        invalidation = {}
    if payload.get("source_authority_allowed") is not False:
        findings.append(
            {
                "error_code": "ROUTE_PLANE_ROUTE_LEASE_SOURCE_AUTHORITY_NOT_REJECTED",
                "message": "Exported route lease policy must reject source authority.",
                "subject_id": selected_lane_id or "route_lease_policy",
                "subject_kind": "route_lease_policy",
                "body_redacted": True,
            }
        )
    return {
        "status": PASS if not findings else "blocked",
        "findings": findings,
        "lease_id": payload.get("lease_id"),
        "selected_lane_id": selected_lane_id,
        "route_lease_ref": payload.get("route_lease_ref"),
        "invalidation_inputs": invalidation,
        "permitted_direct_actions": permitted,
        "banned_route_replacements": payload.get("banned_route_replacements", []),
        "authority_allowed": False,
    }


def validate_code_architecture_projection_packet(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    return {
        "packet_producer_id": str(payload.get("packet_producer_id") or "toy_packet_producer"),
        "source_fingerprint": payload.get("source_fingerprint", {}),
        "omission_receipt": payload.get("omission_receipt", {}),
        "known_limits": payload.get("known_limits", []),
        "renderer_schema_match_status": str(payload.get("renderer_schema_match_status") or PASS),
        "reverse_bfs_depth_buckets": payload.get("reverse_bfs_depth_buckets", {}),
        "suggested_verification": payload.get("suggested_verification", []),
        "body_redacted": True,
    }


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(code)
    return {key: sorted(value) for key, value in sorted(merged.items())}


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [public_relative_path(path, display_root=public_root) for path in paths.values()]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _common_receipt(result: dict[str, Any], *, schema_version: str, receipt_paths: list[str]) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "private_state_scan",
        "authority_ceiling",
        "anti_claim",
        "source_pattern_ids",
        "validator_asserted_feeds_patterns",
        "input_mode",
        "bundle_id",
    )
    payload = {
        "schema_version": schema_version,
        "receipt_id": schema_version,
        "created_at": result["created_at"],
        "receipt_paths": receipt_paths,
    }
    for key in keys:
        payload[key] = result.get(key)
    return payload


def _without_common_receipt_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"findings", "observed_negative_cases"}
    }


def write_receipts(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    target = target.resolve(strict=False)
    receipt_root = public_root if _is_relative_to(target, public_root) else target.parent
    paths = {
        "preflight": receipt_root / PREFLIGHT_REL,
        "toy_kind_cluster_flag": target / CLUSTER_FLAG_NAME,
        "toy_kind_card": target / CARD_NAME,
        "source_coupling_result": target / SOURCE_COUPLING_NAME,
        "route_lease": target / ROUTE_LEASE_NAME,
        "entry_payload_admission_receipt": target / ENTRY_ADMISSION_NAME,
        "affordance_passport_selection_receipt": target / AFFORDANCE_NAME,
        "code_architecture_projection_packet_receipt": target / CODE_ARCH_NAME,
    }
    receipt_paths = _relative_receipt_paths(paths, receipt_root)

    preflight = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_preflight_v1",
        receipt_paths=receipt_paths,
    )
    preflight.update(
        {
            "source_coupling_baseline_status": validation_result["source_coupling_status"],
            "banned_route_table_status": PASS,
            "route_lease_precheck_status": PASS,
            "blocked_dependency_codes": [],
        }
    )

    cluster_flag = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_toy_kind_cluster_flag_v1",
        receipt_paths=receipt_paths,
    )
    cluster_flag.update(validation_result["cluster_flag"])

    card = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_toy_kind_card_v1",
        receipt_paths=receipt_paths,
    )
    card.update(validation_result["card"])

    source = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_source_coupling_result_v1",
        receipt_paths=receipt_paths,
    )
    source.update(
        {
            "expected_sha256": validation_result["expected_sha256"],
            "observed_sha256": validation_result["observed_sha256"],
            "source_coupling_status": validation_result["source_coupling_status"],
            "authority_allowed": validation_result["authority_allowed"],
        }
    )

    route_lease = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_route_lease_v1",
        receipt_paths=receipt_paths,
    )
    route_lease.update(validation_result["route_lease"])
    route_lease.update(
        {
            "banned_route_replacements": validation_result["banned_route_replacements"],
            "duplicate_route_ids": validation_result["duplicate_route_ids"],
        }
    )

    entry_admission = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_entry_payload_admission_v1",
        receipt_paths=receipt_paths,
    )
    entry_admission.update(
        _without_common_receipt_overrides(validation_result["entry_payload_admission"])
    )

    affordance = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_affordance_passport_selection_v1",
        receipt_paths=receipt_paths,
    )
    affordance.update(
        _without_common_receipt_overrides(validation_result["affordance_passport_selection"])
    )

    code_arch = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_code_architecture_projection_packet_v1",
        receipt_paths=receipt_paths,
    )
    code_arch.update(validation_result["code_architecture_projection_packet"])

    for key, payload in (
        ("preflight", preflight),
        ("toy_kind_cluster_flag", cluster_flag),
        ("toy_kind_card", card),
        ("source_coupling_result", source),
        ("route_lease", route_lease),
        ("entry_payload_admission_receipt", entry_admission),
        ("affordance_passport_selection_receipt", affordance),
        ("code_architecture_projection_packet_receipt", code_arch),
    ):
        write_json_atomic(paths[key], payload)

    return {key: public_relative_path(path, display_root=receipt_root) for key, path in paths.items()}


def _write_route_plane_bundle_receipt(
    out_dir: str | Path,
    validation_result: dict[str, Any],
    *,
    public_root: str | Path,
) -> str:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = Path(public_root).resolve(strict=False)
    path = target / ROUTE_PLANE_BUNDLE_RESULT_NAME
    receipt_path = public_relative_path(path, display_root=public_root)
    if Path(receipt_path).is_absolute() and "receipts" in path.parts:
        receipts_index = len(path.parts) - 1 - list(reversed(path.parts)).index("receipts")
        receipt_path = Path(*path.parts[receipts_index:]).as_posix()
    payload = _common_receipt(
        validation_result,
        schema_version="navigation_hologram_route_plane_exported_route_plane_bundle_validation_v1",
        receipt_paths=[receipt_path],
    )
    payload.update(
        {
            "bundle_manifest_schema_version": validation_result[
                "bundle_manifest_schema_version"
            ],
            "route_row_count": validation_result["route_row_count"],
            "cluster_flag": validation_result["cluster_flag"],
            "card": validation_result["card"],
            "selected_row_ids": validation_result["selected_row_ids"],
            "route_rows_projection_not_authority": validation_result[
                "route_rows_projection_not_authority"
            ],
            "expected_sha256": validation_result["expected_sha256"],
            "observed_sha256": validation_result["observed_sha256"],
            "source_coupling_status": validation_result["source_coupling_status"],
            "authority_allowed": validation_result["authority_allowed"],
            "route_lease": validation_result["route_lease"],
            "entry_payload_admission": validation_result["entry_payload_admission"],
            "affordance_passport_selection": validation_result[
                "affordance_passport_selection"
            ],
            "code_architecture_projection_packet": validation_result[
                "code_architecture_projection_packet"
            ],
            "public_replacement_refs": validation_result["public_replacement_refs"],
            "fixture_regression_required_elsewhere": True,
        }
    )
    write_json_atomic(path, payload)
    return receipt_path


def run_route_plane_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_route_plane_bundle(input_path)
    scan_result = _scan_bundle_inputs(input_path, public_root)
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    manifest = payloads["bundle_manifest"] if isinstance(payloads["bundle_manifest"], dict) else {}
    route_result = validate_exported_route_rows(
        payloads["route_rows"],
        payloads["option_surface_contract"],
    )
    source_result = validate_exported_source_coupling(
        payloads["source_coupling_manifest"],
        payloads["route_rows"],
    )
    lease_result = validate_exported_route_lease_policy(payloads["route_lease_policy"])
    entry_result = validate_exported_entry_packet_floor(payloads["entry_packet_floor"])
    affordance_result = validate_exported_affordance_passports(
        payloads["affordance_passports"]
    )
    code_arch_result = validate_code_architecture_projection_packet(
        payloads["code_architecture_projection_packet"]
    )

    all_findings = sorted(
        [
            *route_result["findings"],
            *source_result["findings"],
            *lease_result["findings"],
            *entry_result["findings"],
            *affordance_result["findings"],
        ],
        key=lambda item: (
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    status = (
        PASS
        if scan_result["status"] == PASS
        and not all_findings
        and route_result["selected_row_ids"]
        and lease_result["status"] == PASS
        and entry_result["status"] == PASS
        and affordance_result["status"] == PASS
        and code_arch_result["renderer_schema_match_status"] == PASS
        else "blocked"
    )
    bundle_id = str(
        manifest.get("bundle_id")
        or "navigation_hologram_route_plane_exported_route_plane_bundle"
    )

    result = base_receipt(
        ORGAN_ID,
        f"{FIXTURE_ID}.exported_route_plane_bundle",
        command=command,
    )
    result.update(
        {
            "status": status,
            "input_mode": "exported_route_plane_bundle",
            "bundle_id": bundle_id,
            "bundle_manifest_schema_version": manifest.get("schema_version"),
            "validator_id": VALIDATOR_ID,
            "anti_claim": (
                "The exported route-plane bundle validates public route projection metadata. "
                "It does not grant source authority, publish live operator state, authorize "
                "release, or complete later organs."
            ),
            "authority_ceiling": {
                "status": PASS,
                "authority_ceiling": (
                    "navigation_route_plane_bundle_projection_metadata_not_source_authority"
                ),
                "atlas_projection_control_entry_rejected": True,
                "route_lease_source_authority_rejected": True,
                "release_authorized": False,
            },
            "expected_negative_cases": {},
            "observed_negative_cases": {},
            "missing_negative_cases": [],
            "error_codes": sorted({str(finding["error_code"]) for finding in all_findings}),
            "findings": all_findings,
            "private_state_scan": private_scan,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
            "cluster_flag": route_result["cluster_flag"],
            "card": route_result["card"],
            "selected_row_ids": route_result["selected_row_ids"],
            "route_row_count": len(route_result["route_rows"]),
            "route_rows_projection_not_authority": route_result[
                "route_rows_projection_not_authority"
            ],
            "expected_sha256": source_result["expected_sha256"],
            "observed_sha256": source_result["observed_sha256"],
            "source_coupling_status": source_result["source_coupling_status"],
            "authority_allowed": source_result["authority_allowed"],
            "route_lease": lease_result,
            "entry_payload_admission": entry_result,
            "affordance_passport_selection": affordance_result,
            "code_architecture_projection_packet": code_arch_result,
            "public_replacement_refs": [
                public_relative_path(path, display_root=public_root)
                for path in _route_plane_bundle_paths(input_path)
            ],
        }
    )
    receipt_path = _write_route_plane_bundle_receipt(out_dir, result, public_root=public_root)
    result["receipt_paths"] = [receipt_path]
    return result


def run(input_dir: str | Path, out_dir: str | Path, command: str | None = None) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = Path.cwd() / input_path
    public_root = _public_root_for_path(input_path)
    payloads = _load_inputs(input_path)
    scan_result = _scan_fixture_inputs(input_path, public_root)

    surface_result = build_toy_option_surface(
        payloads["toy_kind_rows"],
        payloads["std_toy_option_surface"],
    )
    source_result = validate_source_coupling_freshness(payloads["source_manifest_stale"])
    banned_result = validate_banned_route_replacement(payloads["banned_route_request"])
    missing_omission_result = validate_route_packet_missing_omission(
        payloads["route_card_missing_omission_receipt"]
    )
    atlas_result = validate_atlas_projection_authority(payloads["atlas_projection_as_control_entry"])
    boundary_result = validate_route_card_boundary(payloads["route_card_with_private_body"])
    freshness_result = validate_summary_freshness(payloads["stale_summary_claims_current"])
    duplicate_result = validate_duplicate_route_ids(payloads["duplicate_route_ids"])
    entry_result = validate_entry_payload_admission_floor(payloads["entry_packet_admission_floor"])
    affordance_result = validate_affordance_passport_selection(
        payloads["affordance_passport_selection"]
    )
    code_arch_result = validate_code_architecture_projection_packet(
        payloads["code_architecture_projection_packet"]
    )

    observed = _merge_observed(
        source_result,
        banned_result,
        missing_omission_result,
        atlas_result,
        boundary_result,
        freshness_result,
        duplicate_result,
        entry_result,
        affordance_result,
    )
    missing_cases = sorted(set(EXPECTED_NEGATIVE_CASES) - set(observed))
    error_codes = sorted({code for codes in observed.values() for code in codes})
    all_findings = sorted(
        [
            *source_result["findings"],
            *banned_result["findings"],
            *missing_omission_result["findings"],
            *atlas_result["findings"],
            *boundary_result["findings"],
            *freshness_result["findings"],
            *duplicate_result["findings"],
            *entry_result["findings"],
            *affordance_result["findings"],
        ],
        key=lambda item: (
            str(item.get("negative_case_id") or ""),
            str(item.get("subject_kind") or ""),
            str(item.get("subject_id") or ""),
            str(item.get("error_code") or ""),
        ),
    )
    private_scan = dict(scan_result)
    private_scan.pop("forbidden_output_fields", None)
    private_scan["redacted_output_field_labels_omitted"] = True

    route_lease_payload = read_json_strict(input_path / "route_lease_baseline.json")
    route_lease = {
        "lease_id": route_lease_payload.get("lease_id"),
        "selected_lane_id": route_lease_payload.get("selected_lane_id"),
        "route_lease_ref": route_lease_payload.get("route_lease_ref"),
        "invalidation_inputs": route_lease_payload.get("invalidation_inputs", {}),
        "permitted_direct_actions": route_lease_payload.get("permitted_direct_actions", []),
        "banned_route_replacements": banned_result["banned_route_replacements"],
        "authority_allowed": False,
    }

    result = base_receipt(ORGAN_ID, FIXTURE_ID, command=command)
    result.update(
        {
            "status": PASS if not missing_cases and scan_result["status"] == PASS else "blocked",
            "validator_id": VALIDATOR_ID,
            "anti_claim": NAV_ANTI_CLAIM,
            "authority_ceiling": NAV_AUTHORITY_CEILING,
            "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
            "observed_negative_cases": observed,
            "missing_negative_cases": missing_cases,
            "error_codes": error_codes,
            "findings": all_findings,
            "private_state_scan": private_scan,
            "source_pattern_ids": SOURCE_PATTERN_IDS,
            "validator_asserted_feeds_patterns": VALIDATOR_ASSERTED_FEEDS_PATTERNS,
            "cluster_flag": surface_result["cluster_flag"],
            "card": surface_result["card"],
            "selected_row_ids": surface_result["selected_row_ids"],
            "expected_sha256": source_result["expected_sha256"],
            "observed_sha256": source_result["observed_sha256"],
            "source_coupling_status": source_result["source_coupling_status"],
            "authority_allowed": source_result["authority_allowed"],
            "banned_route_replacements": banned_result["banned_route_replacements"],
            "route_lease": route_lease,
            "duplicate_route_ids": duplicate_result["duplicate_route_ids"],
            "entry_payload_admission": entry_result,
            "affordance_passport_selection": affordance_result,
            "code_architecture_projection_packet": code_arch_result,
            "fixture_inputs": [
                public_relative_path(path, display_root=public_root)
                for path in _input_paths(input_path)
            ],
        }
    )
    paths = write_receipts(out_dir, result, public_root=public_root)
    result["receipt_paths"] = list(paths.values())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    bundle_parser = subparsers.add_parser("validate-route-plane-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        command = (
            "python -m microcosm_core.organs.navigation_hologram_route_plane "
            f"run --input {args.input} --out {args.out}"
        )
        result = run(args.input, args.out, command=command)
    elif args.action == "validate-route-plane-bundle":
        command = (
            "python -m microcosm_core.organs.navigation_hologram_route_plane "
            f"validate-route-plane-bundle --input {args.input} --out {args.out}"
        )
        result = run_route_plane_bundle(args.input, args.out, command=command)
    else:
        parser.error("expected subcommand: run or validate-route-plane-bundle")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
