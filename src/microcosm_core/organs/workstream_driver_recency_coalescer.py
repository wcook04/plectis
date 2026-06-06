from __future__ import annotations

import json
from functools import cmp_to_key
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    load_json_object,
    main_for_spec,
    run_crown_jewel_organ,
)


ORGAN_ID = "workstream_driver_recency_coalescer"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

SOURCE_REF = "system/server/ui/src/components/cockpit/WorkstreamBoard.tsx"
ENGINE_ID = "workstream_driver_recency_coalescer"

EXPECTED_NEGATIVE_CASES = {
    "driver_key_not_normalized": ("WDRC_DRIVER_KEY_NOT_NORMALIZED",),
    "newest_event_not_refreshed": ("WDRC_NEWEST_EVENT_NOT_REFRESHED",),
    "recency_sort_wrong": ("WDRC_RECENCY_SORT_DESC_REQUIRED",),
    "unclassified_not_last": ("WDRC_UNCLASSIFIED_SENTINEL_LAST_REQUIRED",),
    "release_overclaim": ("WDRC_AUTHORITY_OVERCLAIM",),
}
GROUPING_NEGATIVE_CASES = {
    "driver_key_not_normalized",
    "newest_event_not_refreshed",
    "recency_sort_wrong",
    "unclassified_not_last",
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "workstream_driver_recency_coalescer_not_live_frontend_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "live_browser_state_read": False,
    "frontend_release_authorized": False,
    "source_mutation_authorized": False,
    "provider_dispatch": False,
    "publication_authorized": False,
    "whole_system_correctness_claim": False,
}
AUTHORITY_FALSE_FLAGS = (
    "live_browser_state_read",
    "frontend_release_authorized",
    "source_mutation_authorized",
    "provider_dispatch",
    "publication_authorized",
    "whole_system_correctness_claim",
)

ANTI_CLAIM = (
    "Workstream driver recency coalescer validates the public grouping semantics "
    "copied from WorkstreamBoard.tsx over synthetic AttentionRecentChange rows. "
    "It does not read live cockpit state, authorize frontend release, mutate the "
    "source UI, prove workstream classification correctness, dispatch providers, "
    "or claim whole-system correctness."
)

SOURCE_REQUIRED_ANCHORS = {
    SOURCE_REF: (
        "function groupByDriver(changes: AttentionRecentChange[]): WorkstreamRow[]",
        "const driver = key === 'unclassified' ? 'unclassified' : rawDriver;",
        "existing.latestSummary = change.summary ?? existing.latestSummary;",
        "// sort by recency desc; unclassified always last",
        "return bTs.localeCompare(aTs);",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Workstream Driver Recency Coalescer",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/workstream_driver_recency_coalescer/"
        "exported_workstream_driver_recency_coalescer_bundle/"
        "source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def group_by_driver(changes: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    order: list[str] = []
    rows: dict[str, dict[str, Any]] = {}
    for change in changes:
        raw_driver = change.get("active_driver")
        driver = str(raw_driver).strip() if raw_driver is not None else ""
        driver = driver or "unclassified"
        key = driver.lower()
        if key == "unclassified":
            driver = "unclassified"
        recorded_at = _string_or_none(change.get("recorded_at"))
        summary = _string_or_none(change.get("summary"))
        gate_reason = _string_or_none(change.get("gate_reason"))
        existing = rows.get(key)
        if existing is not None:
            existing["count"] += 1
            if recorded_at and (
                not existing["latestIso"] or recorded_at > existing["latestIso"]
            ):
                existing["latestIso"] = recorded_at
                existing["latestSummary"] = (
                    summary if summary is not None else existing["latestSummary"]
                )
                existing["gateReason"] = (
                    gate_reason if gate_reason is not None else existing["gateReason"]
                )
            continue
        order.append(key)
        rows[key] = {
            "key": key,
            "driver": driver,
            "count": 1,
            "latestIso": recorded_at,
            "latestSummary": summary,
            "gateReason": gate_reason,
        }

    def compare(a: Mapping[str, Any], b: Mapping[str, Any]) -> int:
        a_unclassified = a.get("driver") == "unclassified"
        b_unclassified = b.get("driver") == "unclassified"
        if a_unclassified and not b_unclassified:
            return 1
        if not a_unclassified and b_unclassified:
            return -1
        a_ts = str(a.get("latestIso") or "")
        b_ts = str(b.get("latestIso") or "")
        if b_ts > a_ts:
            return 1
        if b_ts < a_ts:
            return -1
        return 0

    return sorted((rows[key] for key in order), key=cmp_to_key(compare))


def _semantic_negative_cases(input_dir: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed_cases: list[dict[str, Any]] = []
    observed_codes: list[str] = []
    for case_id, expected_codes in sorted(EXPECTED_NEGATIVE_CASES.items()):
        path = input_dir / f"{case_id}.json"
        payload = load_json_object(path, findings, label=f"semantic negative case {case_id}")
        if not payload:
            continue
        expected_code = expected_codes[0]
        if case_id in GROUPING_NEGATIVE_CASES:
            changes = payload.get("recent_changes")
            declared_rows = payload.get("declared_rows")
            if not isinstance(changes, list) or not isinstance(declared_rows, list):
                findings.append(
                    finding(
                        "WDRC_SEMANTIC_NEGATIVE_DATA_MISSING",
                        "Grouping negative cases must carry recent_changes and declared_rows so rejection is recomputed.",
                        case_id=case_id,
                        subject_id=path.name,
                    )
                )
                continue
            observed_rows = group_by_driver(
                [row for row in changes if isinstance(row, Mapping)]
            )
            rejected = observed_rows != declared_rows
            observed_cases.append(
                {
                    "case_id": case_id,
                    "expected_code": expected_code,
                    "semantic_probe": "declared_group_projection_mismatch",
                    "status": "rejected" if rejected else "not_rejected",
                    "observed_rows": observed_rows,
                    "declared_rows": declared_rows,
                    "body_in_receipt": False,
                }
            )
            if rejected:
                observed_codes.append(expected_code)
                continue
            findings.append(
                finding(
                    "WDRC_SEMANTIC_NEGATIVE_NOT_REJECTED",
                    "Grouping negative case declared rows matched recomputed rows; it no longer proves a wrong projection is rejected.",
                    case_id=case_id,
                    subject_id=path.name,
                    observed=observed_rows,
                )
            )
            continue
        if case_id == "release_overclaim":
            claims = (
                payload.get("authority_claims")
                if isinstance(payload.get("authority_claims"), Mapping)
                else {}
            )
            overclaimed = {
                flag: claims.get(flag)
                for flag in AUTHORITY_FALSE_FLAGS
                if claims.get(flag) is not False
            }
            rejected = bool(overclaimed)
            observed_cases.append(
                {
                    "case_id": case_id,
                    "expected_code": expected_code,
                    "semantic_probe": "authority_claim_floor",
                    "status": "rejected" if rejected else "not_rejected",
                    "overclaimed_flags": overclaimed,
                    "body_in_receipt": False,
                }
            )
            if rejected:
                observed_codes.append(expected_code)
                continue
            findings.append(
                finding(
                    "WDRC_SEMANTIC_NEGATIVE_NOT_REJECTED",
                    "Authority negative case did not exceed the public claim ceiling.",
                    case_id=case_id,
                    subject_id=path.name,
                    observed=claims,
                )
            )
            continue
        findings.append(
            finding(
                "WDRC_SEMANTIC_NEGATIVE_UNKNOWN_CASE",
                "Negative case has no semantic evaluator.",
                case_id=case_id,
                subject_id=path.name,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "observed_negative_cases": [row["case_id"] for row in observed_cases],
        "observed_negative_case_count": len(observed_cases),
        "error_codes": sorted(set(observed_codes)),
        "cases": observed_cases,
        "findings": findings,
        "body_in_receipt": False,
    }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    semantic_cases = _semantic_negative_cases(input_dir)
    for row in semantic_cases["cases"]:
        if row.get("case_id") != case_id:
            continue
        if row.get("status") != "rejected":
            break
        return {
            "status": "blocked",
            "error_codes": [str(row.get("expected_code") or "")],
            "body_in_receipt": False,
        }
    return {"status": "pass", "error_codes": [], "body_in_receipt": False}


def _load_manifest(input_dir: Path) -> dict[str, Any]:
    try:
        payload = json.loads((input_dir / PROBE_MANIFEST_NAME).read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_rows(
    input_dir: Path,
    public_root: Path,
) -> dict[str, Mapping[str, Any]]:
    local = input_dir / "source_module_manifest.json"
    manifest_path = local if local.is_file() else public_root / SPEC.source_manifest_ref
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rows = payload.get("modules")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("module_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("module_id")
    }


def evaluate(
    input_dir: Path,
    public_root: Path,
    _source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    manifest = _load_manifest(input_dir)
    authority_claims = (
        manifest.get("authority_claims")
        if isinstance(manifest.get("authority_claims"), Mapping)
        else {}
    )
    for flag in AUTHORITY_FALSE_FLAGS:
        if authority_claims.get(flag) is not False:
            findings.append(
                finding(
                    "WDRC_AUTHORITY_OVERCLAIM",
                    "Probe manifest authority claims must not exceed fixture-level validation.",
                    subject_id=flag,
                    observed=authority_claims.get(flag),
                )
            )
    mechanisms = manifest.get("mechanisms")
    if not isinstance(mechanisms, list):
        mechanisms = []
        findings.append(
            finding(
                "WDRC_PROBE_MANIFEST_INVALID",
                "Probe manifest must include a mechanisms list.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    fixture = manifest.get("positive_fixture")
    if not isinstance(fixture, Mapping):
        fixture = {}
        findings.append(
            finding(
                "WDRC_POSITIVE_FIXTURE_MISSING",
                "Probe manifest must include positive_fixture object.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    source_rows = _source_rows(input_dir, public_root)
    mechanism_rows = []
    for row in mechanisms:
        if not isinstance(row, Mapping):
            continue
        module_ids = [
            str(item)
            for item in row.get("source_module_ids", [])
            if isinstance(item, str) and item
        ]
        missing_modules = [module_id for module_id in module_ids if module_id not in source_rows]
        mechanism_rows.append(
            {
                "mechanism_id": str(row.get("mechanism_id") or ""),
                "status": "pass" if not missing_modules else "blocked",
                "source_module_ids": module_ids,
                "missing_modules": missing_modules,
                "evidence_class": row.get("evidence_class"),
                "source_to_target_relation": row.get("source_to_target_relation"),
                "claim_ceiling": row.get("claim_ceiling"),
                "public_exercise": row.get("public_exercise"),
                "body_in_receipt": False,
            }
        )
    if ENGINE_ID not in {row.get("mechanism_id") for row in mechanism_rows}:
        findings.append(
            finding(
                "WDRC_MECHANISM_MISSING",
                "Probe manifest must name the workstream driver coalescer mechanism.",
                expected=ENGINE_ID,
                observed=[row.get("mechanism_id") for row in mechanism_rows],
            )
        )

    changes = fixture.get("recent_changes")
    if not isinstance(changes, list):
        changes = []
        findings.append(
            finding(
                "WDRC_RECENT_CHANGES_MISSING",
                "Positive fixture must include recent_changes list.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    normalized_changes = [row for row in changes if isinstance(row, Mapping)]
    observed_rows = group_by_driver(normalized_changes)
    expected_rows = fixture.get("expected_rows")
    if not isinstance(expected_rows, list):
        expected_rows = []
        findings.append(
            finding(
                "WDRC_EXPECTED_ROWS_MISSING",
                "Positive fixture must include expected_rows list.",
                subject_id=PROBE_MANIFEST_NAME,
            )
        )
    if observed_rows != expected_rows:
        findings.append(
            finding(
                "WDRC_PUBLIC_EXERCISE_MISMATCH",
                "Python port of groupByDriver must match the declared fixture rows.",
                expected=expected_rows,
                observed=observed_rows,
            )
        )

    by_key = {row["key"]: row for row in observed_rows}
    codex_row = by_key.get("codex", {})
    unclassified_index = next(
        (
            index
            for index, row in enumerate(observed_rows)
            if row.get("key") == "unclassified"
        ),
        None,
    )
    runtime_exercise = {
        "exercise_id": ENGINE_ID,
        "status": "pass" if not findings else "blocked",
        "row_count": len(observed_rows),
        "rows": observed_rows,
        "driver_fold_count": codex_row.get("count"),
        "newest_summary": codex_row.get("latestSummary"),
        "newest_gate_reason": codex_row.get("gateReason"),
        "order_keys": [row["key"] for row in observed_rows],
        "unclassified_pinned_last": unclassified_index == len(observed_rows) - 1,
        "body_in_receipt": False,
    }
    if runtime_exercise["unclassified_pinned_last"] is not True:
        findings.append(
            finding(
                "WDRC_UNCLASSIFIED_SENTINEL_LAST_REQUIRED",
                "Unclassified bucket must remain last even when it has the newest timestamp.",
                observed=runtime_exercise["order_keys"],
            )
        )
    semantic_negative_cases = _semantic_negative_cases(input_dir)
    findings.extend(semantic_negative_cases["findings"])
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": len(mechanism_rows),
        "mechanisms": mechanism_rows,
        "runtime_exercises": {ENGINE_ID: runtime_exercise},
        "runtime_exercise_count": 1,
        "semantic_negative_case_status": semantic_negative_cases["status"],
        "semantic_negative_case_count": semantic_negative_cases[
            "observed_negative_case_count"
        ],
        "semantic_negative_cases": semantic_negative_cases["cases"],
        "copied_macro_source_module_count": len(source_rows),
        "authority_claims": {flag: authority_claims.get(flag) for flag in AUTHORITY_FALSE_FLAGS},
        "error_codes": semantic_negative_cases["error_codes"],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_workstream_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    return card_for_result(SPEC, result)


def main(argv: list[str] | None = None) -> int:
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="validate-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
