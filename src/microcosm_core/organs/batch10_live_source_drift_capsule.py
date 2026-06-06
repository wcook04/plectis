from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch10_live_source_drift_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"
SOURCE_MANIFEST_NAME = "source_module_manifest.json"

STANDARD_OPTION_SURFACE_SOURCE = "system/lib/standard_option_surface.py"
MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE = (
    "system/lib/mission_transaction_landing_preflight.py"
)
WORK_LANDING_SOURCE = "tools/meta/control/work_landing.py"
WORK_LEDGER_SOURCE = "tools/meta/factory/work_ledger.py"

EXPECTED_ENGINES: tuple[str, ...] = (
    "live_source_drift_digest_refresh_matrix",
    "copied_python_source_compile_gate",
    "control_surface_anchor_matrix",
    "claim_ceiling_gate",
)

EXPECTED_NEGATIVE_CASES = {
    "stale_digest_replay": ("BATCH10_LIVE_SOURCE_DRIFT_STALE_DIGEST_REPLAY_REFUSED",),
    "compile_bypass": ("BATCH10_LIVE_SOURCE_DRIFT_COMPILE_BYPASS_REFUSED",),
    "private_runtime_state_export": (
        "BATCH10_LIVE_SOURCE_DRIFT_PRIVATE_RUNTIME_EXPORT_REFUSED",
    ),
    "live_mutation_authority_claim": (
        "BATCH10_LIVE_SOURCE_DRIFT_MUTATION_AUTHORITY_REFUSED",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch10_live_source_drift_import_not_mutation_or_route_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "route_authority_authorized": False,
    "work_ledger_mutation_authorized": False,
    "task_ledger_mutation_authorized": False,
    "mission_transaction_execution_authorized": False,
    "git_staging_or_commit_authorized": False,
    "macro_source_mutation_authorized": False,
    "private_runtime_state_export_authorized": False,
    "provider_dispatch": False,
    "publication_authorized": False,
    "release_authorized": False,
    "source_mutation_authorized": False,
}

ANTI_CLAIM = (
    "Batch 10 Live Source Drift imports exact current Python bodies for the "
    "option-surface router, mission-transaction landing preflight, work landing "
    "controller, and Work Ledger controller after macro source drift. It proves "
    "byte-copy freshness, anchors, Python compileability, and claim ceilings. It "
    "is not route authority, not Work Ledger or Task Ledger mutation authority, "
    "not mission-transaction execution, not git staging/commit approval, and not "
    "permission to export private runtime state."
)

SOURCE_REQUIRED_ANCHORS = {
    STANDARD_OPTION_SURFACE_SOURCE: (
        "standard_owned_option_surface",
        "def build_option_surface",
        "authority_posture",
        "governing_standard",
        "surface_role",
        "cluster_flag",
        "def build_task_ledger_option_surface",
        "option_surface_lens_packet_v0",
    ),
    MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE: (
        "mission_transaction_landing_preflight_v0",
        "def build_mission_transaction_landing_preflight",
        "dirty_tree_classification",
        "landing_decision",
        "work_ledger_session_id",
        "claim_requirements",
    ),
    WORK_LANDING_SOURCE: (
        "def build_parser",
        "admission-check",
        "status",
        "reconcile",
        "begin",
        "build_work_landing_attempt_binding",
        "build_work_landing_reconcile_plan",
    ),
    WORK_LEDGER_SOURCE: (
        "Mutation ordering",
        "session-preflight",
        "session-finalize",
        "session-heartbeat",
        "read_receipt_id",
        "def cmd_session_finalize",
        "def cmd_session_claims",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 10 Live Source Drift Capsule",
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
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _manifest_path(input_path: Path, public_root: Path) -> Path:
    local = input_path / SOURCE_MANIFEST_NAME
    if local.is_file():
        return local
    return public_root / SPEC.source_manifest_ref


def _manifest_rows(input_path: Path, public_root: Path) -> tuple[Path, list[dict[str, Any]]]:
    manifest_path = _manifest_path(input_path, public_root)
    if not manifest_path.is_file():
        return manifest_path, []
    manifest = _load_json(manifest_path)
    rows = [
        dict(row)
        for row in manifest.get("modules", [])
        if isinstance(row, Mapping)
    ]
    return manifest_path, rows


def _source_texts(input_path: Path, public_root: Path) -> dict[str, str]:
    manifest_path, rows = _manifest_rows(input_path, public_root)
    texts: dict[str, str] = {}
    for row in rows:
        source_ref = str(row.get("source_ref") or "")
        rel_path = str(row.get("path") or "")
        target = manifest_path.parent / rel_path
        if source_ref and rel_path and target.is_file():
            texts[source_ref] = target.read_text(encoding="utf-8")
    return texts


def _as_record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _digest_refresh_matrix(
    probe_manifest: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    modules = {
        str(row.get("source_ref") or ""): row
        for row in _as_records(source_manifest.get("modules"))
    }
    matrix_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    seen_source_refs: set[str] = set()
    for row in _as_records(probe_manifest.get("digest_drift_rows")):
        source_ref = str(row.get("source_ref") or "")
        module = _as_record(modules.get(source_ref))
        current_sha = str(row.get("current_sha256") or "")
        stale_sha = str(row.get("stale_recorded_sha256") or "")
        copied_sha = str(module.get("sha256") or "")
        target_sha = str(module.get("target_sha256") or module.get("expected_sha256") or "")
        target_digest_matches = (
            module.get("sha256_match") is True
            or module.get("digest_status") == "match"
        )
        current_matches_copy = bool(
            current_sha
            and copied_sha == current_sha
            and target_sha == current_sha
            and target_digest_matches
        )
        stale_differs_from_current = bool(stale_sha and stale_sha != current_sha)
        matrix_rows.append(
            {
                "material_id": row.get("material_id"),
                "source_ref": source_ref,
                "target_ref": row.get("target_ref"),
                "current_sha256": current_sha,
                "stale_recorded_sha256": stale_sha,
                "copied_target_sha256": copied_sha,
                "current_matches_copy": current_matches_copy,
                "stale_differs_from_current": stale_differs_from_current,
                "body_in_receipt": False,
            }
        )
        if not current_matches_copy:
            findings.append(
                finding(
                    "BATCH10_LIVE_SOURCE_DRIFT_CURRENT_DIGEST_MISMATCH",
                    "Copied source body must match the current macro source digest.",
                    subject_id=source_ref,
                    expected=current_sha,
                    observed=copied_sha,
                )
            )
        if not stale_differs_from_current:
            findings.append(
                finding(
                    "BATCH10_LIVE_SOURCE_DRIFT_STALE_DIGEST_NOT_DETECTED",
                    "The drift capsule must preserve the stale-vs-current digest proof.",
                    subject_id=source_ref,
                    expected="stale_digest_to_differ_from_current",
                    observed=stale_sha,
                )
            )
        if source_ref in seen_source_refs:
            findings.append(
                finding(
                    "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_DUPLICATE",
                    "Each imported live-source-drift body needs exactly one digest matrix row.",
                    subject_id=source_ref,
                )
            )
        seen_source_refs.add(source_ref)
    expected_refs = set(SOURCE_REQUIRED_ANCHORS)
    observed_refs = {row["source_ref"] for row in matrix_rows}
    missing = sorted(expected_refs - observed_refs)
    if missing:
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_MISSING",
                "Every imported live-source-drift body needs a digest matrix row.",
                expected=sorted(expected_refs),
                observed=sorted(observed_refs),
            )
        )
    unexpected = sorted(observed_refs - expected_refs)
    if unexpected:
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_UNEXPECTED",
                "Digest matrix rows must only reference imported live-source-drift bodies.",
                expected=sorted(expected_refs),
                observed=unexpected,
            )
        )
    if len(matrix_rows) != len(expected_refs):
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_MATRIX_ROW_COUNT_MISMATCH",
                "Digest matrix row count must match the imported live-source-drift body count.",
                expected=len(expected_refs),
                observed=len(matrix_rows),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "live_source_drift_digest_refresh_matrix",
        "row_count": len(matrix_rows),
        "stale_digest_count": sum(
            1 for row in matrix_rows if row["stale_differs_from_current"]
        ),
        "all_current_digests_match": all(
            row["current_matches_copy"] for row in matrix_rows
        ),
        "all_stale_digests_differ": all(
            row["stale_differs_from_current"] for row in matrix_rows
        ),
        "rows": matrix_rows,
        "body_in_receipt": False,
        "findings": findings,
    }


def _compile_gate(input_path: Path, public_root: Path) -> dict[str, Any]:
    manifest_path, rows = _manifest_rows(input_path, public_root)
    compiled: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_pyc_") as tmp:
        pyc_root = Path(tmp)
        for row in rows:
            source_ref = str(row.get("source_ref") or "")
            target = manifest_path.parent / str(row.get("path") or "")
            module_id = str(row.get("module_id") or source_ref.replace("/", "_"))
            status = "pass"
            if not target.is_file():
                status = "blocked"
                findings.append(
                    finding(
                        "BATCH10_LIVE_SOURCE_DRIFT_COMPILE_FAILED",
                        "Copied Python source target is missing before py_compile.",
                        subject_id=source_ref,
                    )
                )
            elif target.suffix != ".py":
                status = "blocked"
                findings.append(
                    finding(
                        "BATCH10_LIVE_SOURCE_DRIFT_NON_PYTHON_BODY",
                        "The live-source-drift compile gate only accepts copied Python modules.",
                        subject_id=source_ref,
                    )
                )
            else:
                try:
                    py_compile.compile(
                        str(target),
                        cfile=str(pyc_root / f"{module_id}.pyc"),
                        doraise=True,
                    )
                except py_compile.PyCompileError:
                    status = "blocked"
                    findings.append(
                        finding(
                            "BATCH10_LIVE_SOURCE_DRIFT_COMPILE_FAILED",
                            "Copied Python source did not pass py_compile.",
                            subject_id=source_ref,
                        )
                    )
            compiled.append(
                {
                    "source_ref": source_ref,
                    "module_id": module_id,
                    "status": status,
                    "compiled_without_import": status == "pass",
                    "body_in_receipt": False,
                }
            )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "copied_python_source_compile_gate",
        "module_count": len(rows),
        "compiled_module_count": sum(
            1 for row in compiled if row["compiled_without_import"]
        ),
        "compiled_modules": compiled,
        "import_executed": False,
        "body_in_receipt": False,
        "findings": findings,
    }


def _control_surface_anchor_matrix(texts: Mapping[str, str]) -> dict[str, Any]:
    checks = {
        STANDARD_OPTION_SURFACE_SOURCE: {
            "option_surface_entrypoint": "def build_option_surface" in texts.get(STANDARD_OPTION_SURFACE_SOURCE, ""),
            "standard_projection_packet": "standard_owned_option_surface" in texts.get(STANDARD_OPTION_SURFACE_SOURCE, ""),
            "lens_packet": "option_surface_lens_packet_v0" in texts.get(STANDARD_OPTION_SURFACE_SOURCE, ""),
            "task_ledger_option_surface": "def build_task_ledger_option_surface" in texts.get(STANDARD_OPTION_SURFACE_SOURCE, ""),
        },
        MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE: {
            "preflight_entrypoint": "def build_mission_transaction_landing_preflight" in texts.get(MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE, ""),
            "dirty_tree_classification": "dirty_tree_classification" in texts.get(MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE, ""),
            "landing_decision": "landing_decision" in texts.get(MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE, ""),
            "claim_requirements": "claim_requirements" in texts.get(MISSION_TRANSACTION_LANDING_PREFLIGHT_SOURCE, ""),
        },
        WORK_LANDING_SOURCE: {
            "parser_entrypoint": "def build_parser" in texts.get(WORK_LANDING_SOURCE, ""),
            "status_command": "\"status\"" in texts.get(WORK_LANDING_SOURCE, ""),
            "reconcile_command": "\"reconcile\"" in texts.get(WORK_LANDING_SOURCE, ""),
            "begin_command": "\"begin\"" in texts.get(WORK_LANDING_SOURCE, ""),
            "admission_check_command": "\"admission-check\"" in texts.get(WORK_LANDING_SOURCE, ""),
        },
        WORK_LEDGER_SOURCE: {
            "mutation_ordering": "Mutation ordering" in texts.get(WORK_LEDGER_SOURCE, ""),
            "session_preflight": "session-preflight" in texts.get(WORK_LEDGER_SOURCE, ""),
            "session_finalize": "def cmd_session_finalize" in texts.get(WORK_LEDGER_SOURCE, ""),
            "session_claims": "def cmd_session_claims" in texts.get(WORK_LEDGER_SOURCE, ""),
            "read_receipt_boundary": "read_receipt_id" in texts.get(WORK_LEDGER_SOURCE, ""),
        },
    }
    failed = [
        f"{source_ref}:{check_id}"
        for source_ref, source_checks in checks.items()
        for check_id, passed in source_checks.items()
        if not passed
    ]
    findings = [
        finding(
            "BATCH10_LIVE_SOURCE_DRIFT_CONTROL_ANCHOR_MISSING",
            "Copied control surface body is missing a required behavioral anchor.",
            subject_id=subject,
        )
        for subject in failed
    ]
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "control_surface_anchor_matrix",
        "surface_count": len(checks),
        "check_count": sum(len(row) for row in checks.values()),
        "checks": checks,
        "body_in_receipt": False,
        "findings": findings,
    }


def _claim_ceiling_gate(probe_manifest: Mapping[str, Any]) -> dict[str, Any]:
    policy = _as_record(probe_manifest.get("authority_ceiling_policy"))
    forbidden_flags = [
        "route_authority_authorized",
        "work_ledger_mutation_authorized",
        "task_ledger_mutation_authorized",
        "mission_transaction_execution_authorized",
        "git_staging_or_commit_authorized",
        "macro_source_mutation_authorized",
        "private_runtime_state_export_authorized",
        "provider_dispatch",
        "publication_authorized",
        "release_authorized",
        "source_mutation_authorized",
    ]
    checks = {f"{flag}_is_false": policy.get(flag) is False for flag in forbidden_flags}
    checks["body_in_receipt_false"] = policy.get("body_in_receipt") is False
    checks["exact_copy_only"] = policy.get("body_import_authority") == "copied_source_body_only"
    findings = [
        finding(
            "BATCH10_LIVE_SOURCE_DRIFT_AUTHORITY_CEILING_BROKEN",
            "The live-source-drift capsule must stay a copied-body validator only.",
            subject_id=flag,
            observed=policy.get(flag),
        )
        for flag in forbidden_flags
        if not checks[f"{flag}_is_false"]
    ]
    if not checks["body_in_receipt_false"]:
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_AUTHORITY_CEILING_BROKEN",
                "The live-source-drift capsule must keep receipt bodies out.",
                subject_id="body_in_receipt",
                observed=policy.get("body_in_receipt"),
            )
        )
    if not checks["exact_copy_only"]:
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_AUTHORITY_CEILING_BROKEN",
                "The live-source-drift capsule must stay an exact-copy body validator.",
                subject_id="body_import_authority",
                observed=policy.get("body_import_authority"),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "claim_ceiling_gate",
        "checks": checks,
        "forbidden_authority_flags": forbidden_flags,
        "body_in_receipt": False,
        "findings": findings,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    probe_manifest = _load_json(input_path / PROBE_MANIFEST_NAME)
    texts = _source_texts(input_path, public_root)
    engines = [
        _digest_refresh_matrix(probe_manifest, source_manifest),
        _compile_gate(input_path, public_root),
        _control_surface_anchor_matrix(texts),
        _claim_ceiling_gate(probe_manifest),
    ]
    findings: list[dict[str, Any]] = []
    for engine in engines:
        findings.extend(engine.get("findings", []))
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH10_LIVE_SOURCE_DRIFT_ENGINE_BLOCKED",
                    "A Batch-10 live-source-drift engine did not pass.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in engines}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_ENGINE_MISSING",
                "Expected live-source-drift engines were not observed.",
                expected=list(EXPECTED_ENGINES),
                observed=sorted(observed),
            )
        )
    if source_manifest.get("module_count") != len(SOURCE_REQUIRED_ANCHORS):
        findings.append(
            finding(
                "BATCH10_LIVE_SOURCE_DRIFT_SOURCE_MODULE_COUNT_MISMATCH",
                "The live-source-drift capsule must import all expected source bodies.",
                expected=len(SOURCE_REQUIRED_ANCHORS),
                observed=source_manifest.get("module_count"),
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": [
            {key: value for key, value in engine.items() if key != "findings"}
            for engine in engines
        ],
        "error_codes": [str(code) for codes in EXPECTED_NEGATIVE_CASES.values() for code in codes],
        "body_in_receipt": False,
        "findings": findings,
    }


def _engine_by_id(exercise: Mapping[str, Any], engine_id: str) -> dict[str, Any]:
    engines = exercise.get("engines")
    if not isinstance(engines, list):
        return {}
    for row in engines:
        if isinstance(row, Mapping) and row.get("engine_id") == engine_id:
            return dict(row)
    return {}


def _semantic_negative_result(case_id: str, error_codes: tuple[str, ...]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": observed,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH10_LIVE_SOURCE_DRIFT_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _copy_bundle_for_negative_case(input_dir: Path, work_dir: Path) -> tuple[Path, Path]:
    input_path = input_dir.resolve(strict=False)
    source_public_root = public_root_for_path(input_path)
    target_public_root = work_dir / "microcosm-substrate"
    shutil.copytree(source_public_root / "core", target_public_root / "core")
    source_bundle = (
        input_path
        if (input_path / SOURCE_MANIFEST_NAME).is_file()
        else (source_public_root / SPEC.source_manifest_ref).parent
    )
    target_bundle = target_public_root / source_bundle.relative_to(source_public_root)
    target_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_bundle, target_bundle)
    return target_public_root, target_bundle


def _refresh_bundle_manifest_digest_for_body(
    bundle: Path,
    *,
    row_index: int,
    body: str,
) -> tuple[dict[str, Any], str]:
    manifest_path = bundle / SOURCE_MANIFEST_NAME
    manifest = _load_json(manifest_path)
    rows = _as_records(manifest.get("modules"))
    row = rows[row_index]
    target = bundle / str(row.get("path") or "")
    target.write_text(body, encoding="utf-8")
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    row["sha256"] = sha
    row["source_sha256"] = sha
    row["target_sha256"] = sha
    row["byte_count"] = target.stat().st_size
    row["line_count"] = len(body.splitlines()) or 1
    row["sha256_match"] = True
    manifest["modules"][row_index] = row
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return row, sha


def _evaluate_bundle_negative_case(bundle: Path, public_root: Path) -> dict[str, Any]:
    source_manifest = validate_source_manifest(bundle, SPEC, public_root=public_root)
    return _evaluate(bundle, public_root, source_manifest)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_negative_") as tmp:
            public_root, bundle = _copy_bundle_for_negative_case(input_dir, Path(tmp))
            probe_path = bundle / PROBE_MANIFEST_NAME
            probe = _load_json(probe_path)

            if case_id == "stale_digest_replay":
                row = _as_records(probe.get("digest_drift_rows"))[0]
                row["stale_recorded_sha256"] = row["current_sha256"]
                probe["digest_drift_rows"][0] = row
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                digest_engine = _engine_by_id(
                    exercise, "live_source_drift_digest_refresh_matrix"
                )
                if digest_engine.get("all_stale_digests_differ") is False:
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, digest_engine)

            if case_id == "compile_bypass":
                manifest_row, digest = _refresh_bundle_manifest_digest_for_body(
                    bundle,
                    row_index=2,
                    body=(
                        "# def build_parser\n"
                        "# admission-check\n"
                        "# status\n"
                        "# reconcile\n"
                        "# begin\n"
                        "# build_work_landing_attempt_binding\n"
                        "# build_work_landing_reconcile_plan\n"
                        "def broken_batch10_source(:\n"
                        "    return 'not valid python'\n"
                    ),
                )
                for row in _as_records(probe.get("digest_drift_rows")):
                    if row.get("source_ref") == manifest_row.get("source_ref"):
                        row["current_sha256"] = digest
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                compile_engine = _engine_by_id(
                    exercise, "copied_python_source_compile_gate"
                )
                if compile_engine.get("compiled_module_count", 0) < compile_engine.get(
                    "module_count", 0
                ):
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, compile_engine)

            if case_id == "private_runtime_state_export":
                policy = _as_record(probe.get("authority_ceiling_policy"))
                policy["private_runtime_state_export_authorized"] = True
                probe["authority_ceiling_policy"] = policy
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                claim_engine = _engine_by_id(exercise, "claim_ceiling_gate")
                if (
                    claim_engine.get("checks", {}).get(
                        "private_runtime_state_export_authorized_is_false"
                    )
                    is False
                ):
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, claim_engine)

            if case_id == "live_mutation_authority_claim":
                policy = _as_record(probe.get("authority_ceiling_policy"))
                policy["work_ledger_mutation_authorized"] = True
                policy["macro_source_mutation_authorized"] = True
                policy["mission_transaction_execution_authorized"] = True
                probe["authority_ceiling_policy"] = policy
                probe_path.write_text(
                    json.dumps(probe, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                exercise = _evaluate_bundle_negative_case(bundle, public_root)
                claim_engine = _engine_by_id(exercise, "claim_ceiling_gate")
                checks = claim_engine.get("checks", {})
                if (
                    checks.get("work_ledger_mutation_authorized_is_false") is False
                    and checks.get("macro_source_mutation_authorized_is_false") is False
                    and checks.get(
                        "mission_transaction_execution_authorized_is_false"
                    )
                    is False
                ):
                    return _semantic_negative_result(case_id, expected_codes)
                return _semantic_negative_not_rejected(case_id, claim_engine)
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)

    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH10_LIVE_SOURCE_DRIFT_UNKNOWN_NEGATIVE_CASE_{case_id.upper()}"
        ],
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch10_live_source_drift_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    engines = exercise.get("engines") if isinstance(exercise.get("engines"), list) else []
    by_engine = {
        str(row.get("engine_id")): row
        for row in engines
        if isinstance(row, Mapping)
    }
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    digest_engine = _as_record(by_engine.get("live_source_drift_digest_refresh_matrix"))
    compile_engine = _as_record(by_engine.get("copied_python_source_compile_gate"))
    card["stale_digest_count"] = digest_engine.get("stale_digest_count")
    card["compiled_module_count"] = compile_engine.get("compiled_module_count")
    return card


def main(argv: list[str] | None = None) -> int:
    return main_for_spec(
        SPEC,
        argv,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-batch10-live-source-drift-bundle",
    )


if __name__ == "__main__":
    raise SystemExit(main())
