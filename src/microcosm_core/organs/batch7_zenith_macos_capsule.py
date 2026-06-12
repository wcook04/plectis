from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    display,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "batch7_zenith_macos_capsule"
FIXTURE_ID = "first_wave.batch7_zenith_macos_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_zenith_macos_capsule"

RESULT_NAME = "batch7_zenith_macos_capsule_result.json"
BOARD_NAME = "batch7_zenith_macos_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_zenith_macos_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_zenith_macos_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_zenith_macos_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_zenith_macos_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_zenith_exercise_manifest.json"
NEGATIVE_CASE_PROBE_SCHEMA = "batch7_zenith_macos_capsule_negative_probe_v1"

EXPECTED_ENGINES: tuple[str, ...] = (
    "zenith_route_identity_catalog",
    "zenith_backend_boot_policy",
    "zenith_recording_telemetry_contract",
    "zenith_swiftpm_witness",
)

EXPECTED_NEGATIVE_CASES = {
    "missing_web_latch": ("BATCH7_ZENITH_WEB_LATCH_REQUIRED",),
    "missing_shutdown_command_gate": ("BATCH7_ZENITH_SHUTDOWN_POLICY_REQUIRED",),
    "missing_recording_snake_case": ("BATCH7_ZENITH_RECORDING_TELEMETRY_KEYS_REQUIRED",),
    "missing_swiftpm_witness": ("BATCH7_ZENITH_SWIFTPM_WITNESS_REQUIRED",),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_zenith_macos_capsule_not_app_launch_or_host_control_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "native_app_launch_authorized": False,
    "source_mutation_authorized": False,
    "operator_thread_authority": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 Zenith macOS imports public-safe Swift source bodies and keeps the "
    "full SwiftPM package as an original test witness. It is not an app launch, "
    "not macOS permission authority, not backend control, not browser/provider "
    "authority, and not proof that every UI path is covered."
)

SOURCE_REQUIRED_ANCHORS = {
    "apps/zenith-macos/Package.swift": (
        '.executable(name: "ZenithApp"',
        ".testTarget(",
    ),
    "apps/zenith-macos/Sources/ZenithApp/ZenithModels.swift": (
        "enum ZenithWindowIdentity",
        "struct RecordingViewEventBody",
        "static func disconnected(repoRoot: String)",
    ),
    "apps/zenith-macos/Sources/ZenithApp/ZenithAppModel.swift": (
        "struct ZenithBackendSurfaceAvailability",
        "struct ZenithManagedBackendShutdownPolicy",
        "apiClient.postRecordingViewEvent",
    ),
    "apps/zenith-macos/Sources/ZenithApp/ZenithAPIClient.swift": (
        "func postRecordingViewEvent",
        '"/api/recording/view-event"',
        "keyEncodingStrategy = .convertToSnakeCase",
    ),
    "apps/zenith-macos/Sources/ZenithApp/EmbeddedLensWebView.swift": (
        "WKWebView",
        "markWebViewLoaded",
        "recordingViewChanged",
    ),
    "apps/zenith-macos/Sources/ZenithApp/RuntimeSupervisor.swift": (
        "@MainActor",
        "func replace(with snapshot: RuntimeSnapshot)",
    ),
    "apps/zenith-macos/Sources/ZenithApp/GlobalHotKeyCenter.swift": (
        "RegisterEventHotKey",
        "onTrigger",
    ),
    "apps/zenith-macos/Tests/ZenithAppTests/ZenithAppTests.swift": (
        "windowIdentityCanonicalizesStationNativeAndWebRoutes",
        "recordingViewEventUsesSnakeCaseAPIKeys",
        "managedBackendShutdownPolicyDoesNotKillExternalOrUnrecognizedProcesses",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Zenith macOS Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_zenith_macos_capsule/"
        "exported_batch7_zenith_macos_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    return public_root.parent


def _default_public_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _batch7_public_root(path: Path) -> Path:
    public_root = public_root_for_path(path)
    if (public_root / "core/private_state_forbidden_classes.json").is_file():
        return public_root
    return _default_public_root()


def _canonical_bundle(public_root: Path) -> Path:
    return (
        public_root
        / "examples/batch7_zenith_macos_capsule/"
        "exported_batch7_zenith_macos_capsule_bundle"
    )


def _source_root(input_path: Path, public_root: Path) -> Path:
    if (input_path / "source_modules").is_dir():
        return input_path / "source_modules"
    return _canonical_bundle(public_root) / "source_modules"


def _copied_source(input_path: Path, public_root: Path, source_ref: str) -> Path:
    return (
        _source_root(input_path, public_root)
        / source_ref
    )


def _read(input_path: Path, public_root: Path, source_ref: str) -> str:
    return _copied_source(input_path, public_root, source_ref).read_text(encoding="utf-8")


SWIFTPM_WITNESS_TIMEOUT_SECONDS = 240
# Measured cold-compile truth (no .build, no .swiftpm, scratch copy of the
# full package): swift test passes 17/17 in ~49s on the reference machine, so
# the 240s budget carries ~5x cold margin. The receipt records observed
# duration against this budget so a future timeout is diagnosable.


def _public_witness_ref(package_root: Path, repo_root: Path) -> str:
    # The original package lives OUTSIDE the public root (a sibling app tree in
    # the private macro checkout), so display() cannot relativize it: its
    # fallback chain ends at the operator-absolute path unless cwd happens to
    # be the macro root — a cwd-dependent receipt that flips the body scan.
    # Render repo-relative by construction: deterministic, cwd-free, public-safe.
    try:
        return package_root.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return package_root.name


def _run_swiftpm_package(package_root: Path, *, witness_ref: str) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            ["swift", "test"],
            cwd=package_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=SWIFTPM_WITNESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_ZENITH_SWIFT_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "witness_package_ref": witness_ref,
            "duration_seconds": round(time.monotonic() - started, 1),
            "timeout_budget_seconds": SWIFTPM_WITNESS_TIMEOUT_SECONDS,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_ZENITH_SWIFTPM_WITNESS_TIMEOUT",
            "witness_package_ref": witness_ref,
            "duration_seconds": round(time.monotonic() - started, 1),
            "timeout_budget_seconds": SWIFTPM_WITNESS_TIMEOUT_SECONDS,
            "body_in_receipt": False,
        }
    text = f"{completed.stdout}\n{completed.stderr}"
    return {
        "status": "pass" if completed.returncode == 0 and "17 tests passed" in text else "blocked",
        "returncode": completed.returncode,
        "witness_package_ref": witness_ref,
        "expected_test_count": 17,
        "passed_test_count_observed": 17 if "17 tests passed" in text else None,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "duration_seconds": round(time.monotonic() - started, 1),
        "timeout_budget_seconds": SWIFTPM_WITNESS_TIMEOUT_SECONDS,
        "body_in_receipt": False,
    }


def _run_swiftpm_witness(public_root: Path) -> dict[str, Any]:
    repo_root = _repo_root(public_root)
    witness_package_root = repo_root / "apps/zenith-macos"
    if not witness_package_root.is_dir():
        repo_root = _repo_root(_default_public_root())
        witness_package_root = repo_root / "apps/zenith-macos"
    witness_ref = _public_witness_ref(witness_package_root, repo_root)
    if not (witness_package_root / "Package.swift").is_file():
        # Severed-clone truth: the public slice ships copied source bodies plus
        # digest/anchor witnesses, never the private macro app tree. Type that
        # honestly instead of letting subprocess raise a misleading
        # command-missing error from a nonexistent cwd.
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_ZENITH_ORIGINAL_PACKAGE_UNREACHABLE",
            "witness_package_ref": witness_ref,
            "witness_source": "original_swiftpm_package",
            "unreachable_reason": (
                "original SwiftPM package absent from this checkout; "
                "copied-source digest/anchor witnesses remain the load-bearing "
                "evidence in severed context"
            ),
            "body_in_receipt": False,
        }
    result = _run_swiftpm_package(witness_package_root, witness_ref=witness_ref)
    result["witness_source"] = "original_swiftpm_package"
    return result


def _probe_copied_swiftpm_package(input_path: Path, public_root: Path) -> dict[str, Any]:
    copied_package_root = _source_root(input_path, public_root) / "apps/zenith-macos"
    if not (copied_package_root / "Package.swift").is_file():
        return {
            "status": "blocked",
            "witness_source": "copied_exported_swiftpm_source_modules",
            "error_code": "BATCH7_ZENITH_COPIED_SWIFTPM_PACKAGE_MISSING",
            "body_in_receipt": False,
        }
    # Probe in a scratch copy: running SwiftPM inside the exported bundle would
    # regenerate .build compiler output (with absolute host paths) inside the
    # committed source_modules payload — the recontamination loop the export
    # contamination gate exists to block. The bundle copy stays byte-identical.
    with tempfile.TemporaryDirectory(prefix="b7-zenith-copied-probe.") as scratch:
        scratch_package_root = Path(scratch) / "zenith-macos"
        shutil.copytree(copied_package_root, scratch_package_root)
        result = _run_swiftpm_package(
            scratch_package_root,
            witness_ref=display(copied_package_root, public_root=public_root),
        )
    result["witness_source"] = "copied_exported_swiftpm_source_modules"
    result["authority_ceiling"] = (
        "copied_package_probe_only_public_safe_entry_body_intentionally_excluded"
    )
    result["expected_blocked_reason"] = (
        "ZenithApp.swift is intentionally excluded by the public-safe carveout; "
        "copied source-body evidence remains load-bearing through digest, line, "
        "anchor, and semantic mutation checks."
    )
    return result


def _route_identity_engine(input_path: Path, public_root: Path) -> dict[str, Any]:
    models = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithModels.swift")
    tests = _read(input_path, public_root, "apps/zenith-macos/Tests/ZenithAppTests/ZenithAppTests.swift")
    required = {
        "root_defaults_to_station": 'trimmed.isEmpty || trimmed == "/"' in models
        and 'return "/station"' in models,
        "station_maps_to_cockpit": 'if normalized == "/station"' in models
        and "ZenithSceneID.cockpit.rawValue" in models,
        "native_lenses_have_scene_ids": all(
            token in models for token in ("rawSeedCapture", "gateQueue", "runtimePanel")
        ),
        "swift_tests_cover_route_identity": all(
            token in tests
            for token in (
                "windowIdentityCanonicalizesStationNativeAndWebRoutes",
                "quickLensRouteCatalogExposesPrimaryNativeAndWebLenses",
                "nativeLensMapsToExpectedScene",
            )
        ),
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "zenith_route_identity_catalog",
        **required,
        "claim_ceiling": "Route/window identity catalog only; not a UI launch or navigation authority.",
    }


def _backend_boot_policy_engine(input_path: Path, public_root: Path) -> dict[str, Any]:
    model = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithAppModel.swift")
    models = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithModels.swift")
    tests = _read(input_path, public_root, "apps/zenith-macos/Tests/ZenithAppTests/ZenithAppTests.swift")
    required = {
        "web_latch_suppresses_boot_overlay": "loadedWebViewWindowIDs.contains(windowID)" in model
        and "webLensLoadLatchSuppressesBootOverlayForLoadedWindow" in tests,
        "shutdown_policy_gates_external_processes": "commandLooksLikeZenithBackend" in model
        and "managedBackendShutdownPolicyDoesNotKillExternalOrUnrecognizedProcesses" in tests,
        "runtime_snapshot_has_repo_local_command": '#"cd "\\#(repoRoot)" && ./repo-python run_server.py"#'
        in models,
        "boot_diagnostic_surfaces_evidence": all(
            token in model
            for token in (
                "BootDiagnostic",
                "recoveryReason",
                "lastProbeFailureMessage",
                "backendLaunchInFlight",
            )
        ),
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "zenith_backend_boot_policy",
        **required,
        "claim_ceiling": "Backend boot evidence policy only; does not start or terminate a process.",
    }


def _recording_telemetry_engine(input_path: Path, public_root: Path) -> dict[str, Any]:
    models = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithModels.swift")
    model = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithAppModel.swift")
    api = _read(input_path, public_root, "apps/zenith-macos/Sources/ZenithApp/ZenithAPIClient.swift")
    tests = _read(input_path, public_root, "apps/zenith-macos/Tests/ZenithAppTests/ZenithAppTests.swift")
    required = {
        "recording_body_declared_sendable": "struct RecordingViewEventBody: Codable, Sendable" in models,
        "api_encodes_snake_case": "keyEncodingStrategy = .convertToSnakeCase" in api,
        "api_posts_view_event_endpoint": '"/api/recording/view-event"' in api,
        "host_and_web_events_are_stamped": "hostStampedWebRecordingEvent" in model
        and "makeWebRecordingEvent" in model
        and "zenith_host" in model,
        "swift_tests_cover_snake_case": "recordingViewEventUsesSnakeCaseAPIKeys" in tests,
    }
    return {
        "status": "pass" if all(required.values()) else "blocked",
        "engine_id": "zenith_recording_telemetry_contract",
        **required,
        "claim_ceiling": "Telemetry schema and host stamping contract only; no event is posted.",
    }


def _engine_map(engines: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("engine_id")): row for row in engines}


def _package_test_target_anchor_missing(source_manifest: Mapping[str, Any]) -> bool:
    modules = source_manifest.get("modules")
    if not isinstance(modules, list):
        return False
    for row in modules:
        if not isinstance(row, Mapping):
            continue
        if row.get("source_ref") != "apps/zenith-macos/Package.swift":
            continue
        missing = row.get("missing_required_anchors")
        return isinstance(missing, list) and ".testTarget(" in missing
    return False


def _batch7_contract_findings(
    source_manifest: Mapping[str, Any],
    engines: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_engine = _engine_map(engines)
    findings: list[dict[str, Any]] = []
    backend = by_engine.get("zenith_backend_boot_policy", {})
    telemetry = by_engine.get("zenith_recording_telemetry_contract", {})
    swiftpm = by_engine.get("zenith_swiftpm_witness", {})
    if backend.get("web_latch_suppresses_boot_overlay") is not True:
        findings.append(
            finding(
                "BATCH7_ZENITH_WEB_LATCH_REQUIRED",
                "Zenith backend policy must suppress boot overlay for loaded web lenses.",
                subject_id="zenith_backend_boot_policy.web_latch_suppresses_boot_overlay",
                observed=backend.get("web_latch_suppresses_boot_overlay"),
            )
        )
    if backend.get("shutdown_policy_gates_external_processes") is not True:
        findings.append(
            finding(
                "BATCH7_ZENITH_SHUTDOWN_POLICY_REQUIRED",
                "Zenith managed-backend shutdown policy must gate external or unrecognized processes.",
                subject_id="zenith_backend_boot_policy.shutdown_policy_gates_external_processes",
                observed=backend.get("shutdown_policy_gates_external_processes"),
            )
        )
    if (
        telemetry.get("api_encodes_snake_case") is not True
        or telemetry.get("swift_tests_cover_snake_case") is not True
    ):
        findings.append(
            finding(
                "BATCH7_ZENITH_RECORDING_TELEMETRY_KEYS_REQUIRED",
                "Zenith recording telemetry must encode snake_case keys and keep a Swift witness.",
                subject_id="zenith_recording_telemetry_contract.snake_case_keys",
                observed={
                    "api_encodes_snake_case": telemetry.get("api_encodes_snake_case"),
                    "swift_tests_cover_snake_case": telemetry.get("swift_tests_cover_snake_case"),
                },
            )
        )
    if swiftpm.get("status") == "blocked" or _package_test_target_anchor_missing(source_manifest):
        findings.append(
            finding(
                "BATCH7_ZENITH_SWIFTPM_WITNESS_REQUIRED",
                "Zenith capsule requires a SwiftPM test-target witness.",
                subject_id="zenith_swiftpm_witness",
                observed={
                    "swiftpm_status": swiftpm.get("status"),
                    "package_test_target_anchor_missing": _package_test_target_anchor_missing(source_manifest),
                },
            )
        )
    return findings


def _source_body_witness_summary(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    modules = [
        row
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    ]
    digest_mismatch_refs = [
        str(row.get("source_ref") or row.get("path") or "")
        for row in modules
        if row.get("digest_status") != "match"
    ]
    anchor_missing_refs = [
        str(row.get("source_ref") or row.get("path") or "")
        for row in modules
        if row.get("missing_required_anchors")
    ]
    line_count_mismatch_refs = [
        str(row.get("source_ref") or row.get("path") or "")
        for row in modules
        if row.get("line_count_status") != "match"
    ]
    return {
        "schema_version": "batch7_zenith_source_body_witness_summary_v1",
        "module_count": len(modules),
        "body_copied_count": sum(1 for row in modules if row.get("body_copied") is True),
        "digest_match_count": sum(
            1 for row in modules if row.get("digest_status") == "match"
        ),
        "line_count_match_count": sum(
            1 for row in modules if row.get("line_count_status") == "match"
        ),
        "anchor_complete_count": sum(
            1 for row in modules if not row.get("missing_required_anchors")
        ),
        "all_expected_digests_matched": source_manifest.get(
            "all_expected_digests_matched"
        )
        is True,
        "all_expected_line_counts_matched": source_manifest.get(
            "all_expected_line_counts_matched"
        )
        is True,
        "all_required_anchors_present": source_manifest.get(
            "all_required_anchors_present"
        )
        is True,
        "digest_mismatch_refs": digest_mismatch_refs,
        "line_count_mismatch_refs": line_count_mismatch_refs,
        "anchor_missing_refs": anchor_missing_refs,
        "witness_authority": "copied_swiftpm_source_module_manifest_and_body_digest_checks",
        "body_in_receipt": False,
    }


def _negative_case_payload(input_dir: Path, case_id: str) -> dict[str, Any]:
    path = input_dir / f"{case_id}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_bundle_for_probe(input_dir: Path, public_root: Path) -> Path:
    if (input_dir / "source_module_manifest.json").is_file() and (
        input_dir / "source_modules"
    ).is_dir():
        return input_dir
    return _canonical_bundle(public_root)


def _remove_tokens_from_bundle(bundle: Path, tokens: list[str]) -> dict[str, Any]:
    changed_refs: set[str] = set()
    missing_tokens: list[str] = []
    total_removal_count = 0
    files = [path for path in bundle.rglob("*") if path.is_file()]
    for token in tokens:
        removal_count = 0
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if token not in text:
                continue
            removal_count += text.count(token)
            path.write_text(text.replace(token, ""), encoding="utf-8")
            changed_refs.add(path.relative_to(bundle).as_posix())
        if removal_count == 0:
            missing_tokens.append(token)
        total_removal_count += removal_count
    return {
        "changed_refs": sorted(changed_refs),
        "missing_tokens": missing_tokens,
        "removed_token_count": total_removal_count,
        "declared_token_count": len(tokens),
        "body_in_receipt": False,
    }


def _case_contract_codes(
    case_id: str,
    source_manifest: Mapping[str, Any],
    engines: list[dict[str, Any]],
) -> list[str]:
    by_engine = _engine_map(engines)
    backend = by_engine.get("zenith_backend_boot_policy", {})
    telemetry = by_engine.get("zenith_recording_telemetry_contract", {})
    codes: list[str] = []
    if case_id == "missing_web_latch" and (
        backend.get("web_latch_suppresses_boot_overlay") is not True
    ):
        codes.append("BATCH7_ZENITH_WEB_LATCH_REQUIRED")
    if case_id == "missing_shutdown_command_gate" and (
        backend.get("shutdown_policy_gates_external_processes") is not True
    ):
        codes.append("BATCH7_ZENITH_SHUTDOWN_POLICY_REQUIRED")
    if case_id == "missing_recording_snake_case" and (
        telemetry.get("api_encodes_snake_case") is not True
        or telemetry.get("swift_tests_cover_snake_case") is not True
    ):
        codes.append("BATCH7_ZENITH_RECORDING_TELEMETRY_KEYS_REQUIRED")
    if case_id == "missing_swiftpm_witness" and _package_test_target_anchor_missing(
        source_manifest
    ):
        codes.append("BATCH7_ZENITH_SWIFTPM_WITNESS_REQUIRED")
    return codes


def _compute_negative_case_probe(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    payload = _negative_case_payload(input_dir, case_id)
    tokens = [
        str(token)
        for token in (
            payload.get("mutant", {}).get("remove_tokens", [])
            if isinstance(payload.get("mutant"), Mapping)
            else []
        )
        if isinstance(token, str) and token
    ]
    public_root = _batch7_public_root(input_dir)
    with tempfile.TemporaryDirectory(prefix="batch7_zenith_negative_") as tmp:
        source_bundle = _source_bundle_for_probe(input_dir, public_root)
        mutant_bundle = Path(tmp) / "bundle"
        shutil.copytree(source_bundle, mutant_bundle)
        mutation = _remove_tokens_from_bundle(mutant_bundle, tokens)
        source_manifest = validate_source_manifest(mutant_bundle, SPEC, public_root=public_root)
        engines = [
            _route_identity_engine(mutant_bundle, public_root),
            _backend_boot_policy_engine(mutant_bundle, public_root),
            _recording_telemetry_engine(mutant_bundle, public_root),
        ]
        error_codes = _case_contract_codes(case_id, source_manifest, engines)
        rejected = all(code in error_codes for code in expected_codes)
        by_engine = _engine_map(engines)
        backend = by_engine.get("zenith_backend_boot_policy", {})
        telemetry = by_engine.get("zenith_recording_telemetry_contract", {})
        return {
            "schema_version": NEGATIVE_CASE_PROBE_SCHEMA,
            "case_id": case_id,
            "status": "blocked" if rejected else "pass",
            "fixture_role": "negative_case_label_not_verdict_authority",
            "verdict_authority": "semantic_mutation_probe",
            "source_bundle_ref": (
                "input_bundle" if source_bundle == input_dir else "canonical_public_bundle"
            ),
            "mutation": mutation,
            "source_manifest_status": source_manifest.get("status"),
            "package_test_target_anchor_missing": _package_test_target_anchor_missing(
                source_manifest
            ),
            "observed_contracts": {
                "web_latch_suppresses_boot_overlay": backend.get(
                    "web_latch_suppresses_boot_overlay"
                ),
                "shutdown_policy_gates_external_processes": backend.get(
                    "shutdown_policy_gates_external_processes"
                ),
                "api_encodes_snake_case": telemetry.get("api_encodes_snake_case"),
                "swift_tests_cover_snake_case": telemetry.get(
                    "swift_tests_cover_snake_case"
                ),
            },
            "error_codes": sorted(set(error_codes)),
            "expected_codes": list(expected_codes),
            "body_in_receipt": False,
        }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        return _compute_negative_case_probe(case_id, input_dir, expected_codes)
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return {
            "case_id": case_id,
            "status": "blocked",
            "error_codes": [
                f"BATCH7_ZENITH_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
            ],
            "body_in_receipt": False,
        }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    swift_witness = _run_swiftpm_witness(public_root)
    copied_swiftpm_probe = _probe_copied_swiftpm_package(input_path, public_root)
    engines = [
        _route_identity_engine(input_path, public_root),
        _backend_boot_policy_engine(input_path, public_root),
        _recording_telemetry_engine(input_path, public_root),
        {
            "status": "pass" if swift_witness.get("status") == "pass" else "blocked",
            "engine_id": "zenith_swiftpm_witness",
            "original_witness": swift_witness,
            "claim_ceiling": "Original SwiftPM test witness only; receipt stores no stdout/stderr body.",
        },
    ]
    findings: list[dict[str, Any]] = []
    if source_manifest.get("status") != "pass":
        findings.append(
            finding(
                "BATCH7_ZENITH_SOURCE_MANIFEST_BLOCKED",
                "Zenith macOS source manifest must validate before exercise can pass.",
                observed=source_manifest.get("status"),
            )
        )
    findings.extend(_batch7_contract_findings(source_manifest, engines))
    if swift_witness.get("status") != "pass":
        findings.append(
            finding(
                "BATCH7_ZENITH_SWIFTPM_WITNESS_REQUIRED",
                "Zenith macOS capsule requires the original swift test witness to pass.",
                observed=swift_witness.get("returncode"),
            )
        )
    for engine in engines:
        if engine.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_ZENITH_ENGINE_BLOCKED",
                    "Zenith macOS capsule engine did not satisfy its public contract.",
                    subject_id=str(engine.get("engine_id")),
                    observed=engine.get("status"),
                )
            )
    negative_case_probes = [
        _compute_negative_case_probe(case_id, input_path, expected_codes)
        for case_id, expected_codes in sorted(EXPECTED_NEGATIVE_CASES.items())
    ]
    computed_probe_count = sum(
        1
        for row in negative_case_probes
        if row.get("status") == "blocked"
        and all(
            code in row.get("error_codes", [])
            for code in EXPECTED_NEGATIVE_CASES[str(row.get("case_id"))]
        )
    )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(engines),
        "engine_ids": [str(row["engine_id"]) for row in engines],
        "engines": engines,
        "negative_case_probe_summary": {
            "schema_version": NEGATIVE_CASE_PROBE_SCHEMA,
            "probe_count": len(negative_case_probes),
            "computed_probe_count": computed_probe_count,
            "fixture_verdict_echo_risk_count": sum(
                1
                for row in negative_case_probes
                if row.get("verdict_authority") != "semantic_mutation_probe"
            ),
            "body_in_receipt": False,
        },
        "negative_case_probes": negative_case_probes,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "source_body_witness_summary": _source_body_witness_summary(source_manifest),
        "swiftpm_witness": swift_witness,
        "copied_swiftpm_package_probe": copied_swiftpm_probe,
        "public_safe_carveout_ref": "cap_quick_batch_7_zenith_macos_capsule_needs_narro_c099bd13f9ca",
        "body_in_receipt": False,
        "findings": findings,
        "error_codes": [str(row["error_code"]) for row in findings if row.get("error_code")],
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


def run_batch7_zenith_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["engine_count"] = exercise.get("engine_count")
    card["swiftpm_witness_status"] = exercise.get("swiftpm_witness", {}).get("status")
    card["copied_macro_source_module_count"] = exercise.get("copied_macro_source_module_count")
    card["source_body_witness_summary"] = exercise.get("source_body_witness_summary")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "release_authorized": ceiling.get("release_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "provider_dispatch": ceiling.get("provider_dispatch"),
        "model_dispatch": ceiling.get("model_dispatch"),
        "browser_or_wallet_access": ceiling.get("browser_or_wallet_access"),
        "native_app_launch_authorized": ceiling.get("native_app_launch_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "operator_thread_authority": ceiling.get("operator_thread_authority"),
        "semantic_truth_authority": ceiling.get("semantic_truth_authority"),
        "test_completeness_proof": ceiling.get("test_completeness_proof"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "swiftpm_stdout_in_receipt": False,
        "swiftpm_stderr_in_receipt": False,
        "source_bodies_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle", "run-batch7-zenith-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action in {"validate-bundle", "run-batch7-zenith-bundle"}
            else "fixture_input"
        ),
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
