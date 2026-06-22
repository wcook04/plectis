from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "verifier_lab_execution_spine"
FIXTURE_ID = "first_wave.verifier_lab_execution_spine"
VALIDATOR_ID = "validator.microcosm.organs.verifier_lab_execution_spine"

PACKET_NAME = "execution_spine_packet.json"
LAKE_PROJECT_DIR = "lake_project"
LAKEFILE_NAME = "lakefile.lean"
LEAN_TRANSITION_MAX_WORKERS = 4
RESULT_NAME = "verifier_lab_execution_spine_result.json"
BOARD_NAME = "verifier_lab_execution_spine_board.json"
VALIDATION_RECEIPT_NAME = "verifier_lab_execution_spine_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "verifier_lab_execution_spine_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = (
    "exported_verifier_lab_execution_spine_bundle_validation_result.json"
)
CARD_SCHEMA_VERSION = "verifier_lab_execution_spine_command_card_v1"
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = (
    "copied_non_secret_verifier_lab_execution_spine_runtime_source_bodies_"
    "with_digest_provenance"
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_tool_body",
    "public_macro_proof_body",
}
SOURCE_MODULE_RELATIONS = {"exact_copy"}
SOURCE_REF_PREFIXES = (
    "src/microcosm_core/organs/",
    "fixtures/first_wave/verifier_lab_execution_spine/input/",
    "examples/verifier_lab_execution_spine/exported_verifier_lab_execution_spine_bundle/",
)
_LAKE_PROJECT_BUILD_CACHE: dict[str, Path] = {}
_LAKE_PROJECT_BUILD_CACHE_HOLDERS: list[Any] = []
_LAKE_PROJECT_BUILD_RESULT_CACHE: dict[str, dict[str, Any]] = {}
_TRANSITION_EXECUTION_CACHE: dict[str, list[TransitionReceipt]] = {}

NEGATIVE_INPUT_NAMES = (
    "transition_leaks_candidate_body.json",
    "provider_oracle_visible_transition.json",
    "cp2_candidate_contains_proof_body.json",
    "evolve_mutates_unbounded_source.json",
)
EXPECTED_NEGATIVE_CASES = {
    "transition_leaks_candidate_body": [
        "VERIFIER_LAB_EXECUTION_TRANSITION_FIELD_FORBIDDEN"
    ],
    "provider_oracle_visible_transition": [
        "VERIFIER_LAB_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
    ],
    "cp2_candidate_contains_proof_body": [
        "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
    ],
    "evolve_mutates_unbounded_source": [
        "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
    ],
}

FORBIDDEN_TRANSITION_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "ideal_body",
    "repair_body",
    "raw_tactic_script",
    "oracle_template",
    "oracle_needed_premise_ids",
    "provider_output_body",
    "source_proof_body",
}
FORBIDDEN_CP2_KEYS = {
    "candidate_body",
    "proof_body",
    "ground_truth_proof",
    "raw_tactic_script",
    "oracle_template",
    "provider_output_body",
    "source_proof_body",
}
ALLOWED_ACTION_CLASSES = {
    "cases",
    "constructor",
    "decide",
    "exact_premise",
    "induction_visible_head",
    "premise_exact",
    "rfl",
    "simp_with_closed_premises",
    "unfold_then_simp",
}
ALLOWED_CP2_ACTION_CLASSES = {
    "case_split_then_constructor",
    "exact_selected_premise",
    "induction_on_visible_head",
    "premise_exact",
    "premise_query_expand",
    "retry_with_recipe",
    "rewrite_direction_flip",
    "unfold_then_simp",
}
ALLOWED_EVOLVE_ARTIFACTS = {
    "context_recipe_selection",
    "cp2_candidate_ordering",
    "cp2_translation_templates",
    "failure_class_routing",
    "repair_novelty_predicates",
    "retry_recipes",
    "route_priors",
    "target_shape_mapping",
    "target_shape_routing_table",
    "tactic_action_priors",
}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "bounded_public_lean_transition_execution_receipt_only",
    "lean_lake_execution_authorized": True,
    "lean_lake_execution_scope": "temporary_workspace_copy_of_public_fixture",
    "formal_proof_authority": "bounded_public_transition_rows_only",
    "oracle_success_counts_as_forward_success": False,
    "provider_text_counts_as_proof": False,
    "cp2_outputs_are_proof_bodies": False,
    "evolve_mutates_arbitrary_code": False,
    "proof_bodies_allowed_in_receipts": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "macro_private_body_import_authorized": False,
    "benchmark_solve_rate_claim": False,
    "release_authorized": False,
}
RECEIPT_TRANSPARENCY_CONTRACT = {
    "schema_version": "verifier_lab_receipt_transparency_contract_v1",
    "receipt_body_is_public_evidence": True,
    "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
    "body_in_receipt": False,
    "real_substrate_default": True,
    "required_public_evidence_fields": [
        "problem_id",
        "target_shape",
        "action_class",
        "candidate_kind",
        "allowed_premise_refs",
        "source_module_imports",
        "source_open_body_imports",
        "body_copied_material_count",
        "lean_lake_command_identity",
        "lean_return_code",
        "accepted",
        "verifier_failure_class",
        "negative_case_id",
        "cp2_action_class",
        "evolve_policy_artifact_id",
        "oracle_provider_separation_counters",
        "authority_ceiling",
        "anti_claim",
    ],
    "forbidden_payload_fields": [
        "proof_body",
        "raw_tactic_script",
        "provider_text",
        "oracle_ideal_answer",
        "oracle_needed_premise_ids",
        "private_source_path",
        "private_payload_body",
        "stdout_body",
        "stderr_body",
    ],
    "stdout_stderr_policy": "counts_and_return_codes_public_bodies_omitted",
}
ANTI_CLAIM = (
    "Verifier lab execution spine runs bounded public Lean transition candidates "
    "in a temporary workspace and records structured public runtime receipts "
    "with only dangerous payload fields omitted. It does not import macro proof bodies, "
    "expose generated proof text, call providers, count oracle/provider output "
    "as proof authority, mutate source, claim benchmark solve-rate, or authorize "
    "release."
)
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "anti_claim",
    "claim_separation",
    "cp2_translation_trace",
    "evolve_mutation_trace",
    "findings",
    "lake_project_build",
    "public_runtime_refs",
    "receipt_paths",
    "receipt_transparency_contract",
    "secret_exclusion_scan",
    "source_module_imports",
    "source_open_body_imports",
    "source_pattern_ids",
    "source_refs",
    "tool_versions",
    "transition_trace",
)


@dataclass(frozen=True)
class TransitionReceipt:
    problem_id: str
    target_shape: str
    action_class: str
    candidate_kind: str
    allowed_premise_refs: tuple[str, ...]
    lean_return_code: int | None
    accepted: bool
    verifier_failure_class: str
    stdout_stderr_in_receipt: bool
    oracle_visible: bool
    provider_visible: bool
    proof_body_exported: bool
    transition_id: str
    contract_rejected: bool = False
    error_codes: tuple[str, ...] = ()
    timed_out: bool = False


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = [input_dir / PACKET_NAME, input_dir / LAKE_PROJECT_DIR / LAKEFILE_NAME]
    project_dir = input_dir / LAKE_PROJECT_DIR
    if project_dir.is_dir():
        paths.extend(sorted(_iter_lean_project_files(project_dir)))
    if (input_dir / "bundle_manifest.json").is_file():
        paths.append(input_dir / "bundle_manifest.json")
    public_root = _public_root_for_path(input_dir)
    paths.extend(_source_artifact_paths(input_dir, public_root=public_root))
    if include_negative:
        paths.extend(input_dir / name for name in NEGATIVE_INPUT_NAMES)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _iter_lean_project_files(path: Path) -> Iterator[Path]:
    with os.scandir(path) as entries:
        entry_rows = sorted(list(entries), key=lambda entry: entry.name)
    for entry in entry_rows:
        child = path / entry.name
        if entry.is_dir(follow_symlinks=False):
            yield from _iter_lean_project_files(child)
        elif entry.is_file(follow_symlinks=False) and child.suffix == ".lean":
            yield child


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_microcosm_prefix(ref: str) -> str:
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _source_module_manifest_path(input_dir: str | Path) -> Path:
    return Path(input_dir) / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        target = public_root / target_ref
        if target.exists() or not row_path:
            return target, target_ref
        relocated = manifest_path.parent / row_path
        return relocated, _display(relocated, public_root=public_root)
    if row_path:
        target = manifest_path.parent / row_path
        return target, _display(target, public_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: str | Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except (OSError, ValueError):
        return paths
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def validate_source_module_imports(
    input_dir: str | Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_MANIFEST_MISSING",
                "Exported execution-spine bundles require source_module_manifest.json for copied public runtime source bodies.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = read_json_strict(manifest_path)
    if not isinstance(manifest, dict):
        manifest = {}
    module_rows = _rows(manifest, "modules")
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "VERIFIER_LAB_EXECUTION_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "VERIFIER_LAB_EXECUTION_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied execution-spine source bodies may live in the exported bundle, not in receipts.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("module_count") != len(module_rows):
        findings.append(
            _finding(
                "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_COUNT_MISMATCH",
                "Source module manifest module_count must equal its module rows.",
                case_id="source_module_manifest",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in module_rows:
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row,
            manifest_path=manifest_path,
            public_root=public_root,
        )
        source_ref = str(row.get("source_ref") or "")
        material_class = str(row.get("material_class") or "")
        relation = str(row.get("source_to_target_relation") or "")
        expected_digest = str(row.get("sha256") or "")
        subject = module_id or target_ref or "source_module"
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Execution-spine body imports may include only public macro tool or public macro proof bodies.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if relation not in SOURCE_MODULE_RELATIONS:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if not source_ref.startswith(SOURCE_REF_PREFIXES):
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_REF_UNEXPECTED",
                    "Source module rows must point at public execution-spine source files.",
                    case_id="source_module_manifest",
                    subject_id=subject,
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the exported execution-spine bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256_file(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
                    subject_kind="source_module",
                )
            )
        target_text = target_path.read_text(encoding="utf-8")
        missing_anchors = [
            str(anchor)
            for anchor in row.get("required_anchors", [])
            if isinstance(anchor, str) and anchor not in target_text
        ]
        if missing_anchors:
            findings.append(
                _finding(
                    "VERIFIER_LAB_EXECUTION_SOURCE_MODULE_ANCHOR_MISSING",
                    "Source module target is missing one or more required anchors.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or subject,
                    subject_kind="source_module",
                )
            )
        modules.append(
            {
                "module_id": module_id,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "body_in_receipt": False,
            }
        )

    return {
        "status": PASS if not findings and modules else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "modules": modules,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _empty_source_module_imports(input_dir: str | Path, *, public_root: Path) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    return {
        "status": "not_applicable",
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": 0,
        "modules": [],
        "findings": [],
        "observed_negative_cases": {},
    }


def _source_open_body_import_summary(source_imports: dict[str, Any]) -> dict[str, Any]:
    modules = _rows(source_imports, "modules")
    module_ids = [
        str(row.get("module_id")) for row in modules if row.get("module_id")
    ]
    return {
        "schema_version": "verifier_lab_execution_spine_source_open_body_imports_v1",
        "status": source_imports.get("status"),
        "source_import_class": SOURCE_IMPORT_CLASS if modules else "",
        "body_material_status": SOURCE_BODY_STATUS if modules else "",
        "body_material_count": len(modules),
        "body_material_ids": module_ids,
        "material_classes": sorted(
            {
                str(row.get("material_class"))
                for row in modules
                if row.get("material_class")
            }
        ),
        "source_manifest_refs": [
            source_imports["source_module_manifest_ref"]
        ]
        if source_imports.get("source_module_manifest_ref") and modules
        else [],
        "aggregate_floor_ref": (
            f"{source_imports['source_module_manifest_ref']}::modules"
            if source_imports.get("source_module_manifest_ref") and modules
            else ""
        ),
        "body_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "proof_body_or_oracle_proof_text_exported": False,
            "provider_payload_exported": False,
            "host_local_absolute_paths_exported": False,
            "lean_lake_execution_authorized": True,
            "formal_proof_authority": "bounded_public_transition_rows_only",
            "release_authorized": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ and lake_project/ "
            "inside the exported execution-spine bundle for copied public runtime "
            "source bodies; receipts carry refs, digests, counts, and verdicts only."
        )
        if modules
        else "",
    }


def _source_module_blocked_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    source_module_imports: dict[str, Any],
    source_open_body_imports: dict[str, Any],
    secret_scan: dict[str, Any],
) -> dict[str, Any]:
    packet = _load_json_if_exists(input_dir / PACKET_NAME)
    bundle_manifest = _load_json_if_exists(input_dir / "bundle_manifest.json")
    findings = _rows(source_module_imports, "findings")
    return {
        "schema_version": "verifier_lab_execution_spine_result_v1",
        "created_at": utc_now(),
        "status": "blocked",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "execution_spine_id": packet.get("execution_spine_id"),
        "source_refs": _strings(packet.get("source_refs")),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "source_module_imports": source_module_imports,
        "source_module_manifest_ref": source_module_imports[
            "source_module_manifest_ref"
        ],
        "execution_witness_mode": "source_module_imports_blocked",
        "source_open_body_imports": source_open_body_imports,
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "expected_negative_cases": [],
        "observed_negative_cases": {},
        "missing_negative_cases": [],
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "tool_versions": {"skipped": True, "reason": "source_module_imports_blocked"},
        "lake_project_build": {"skipped": True, "reason": "source_module_imports_blocked"},
        "transition_trace": [],
        "cp2_translation_trace": [],
        "evolve_mutation_trace": [],
        "claim_separation": {
            "lean_verified": [],
            "oracle_compared": [],
            "provider_suggested": [],
            "cp2_translated": [],
            "contract_rejected": [],
            "retrieval_miss": [],
            "proof_synthesis_fail": [],
            "evolve_candidate": [],
            "evolve_accepted": [],
        },
        "authority_counters": {
            "transition_count": 0,
            "accepted_transition_count": 0,
            "residual_transition_count": 0,
            "cp2_translation_count": 0,
            "cp2_downstream_effect_count": 0,
            "evolve_candidate_count": 0,
            "evolve_accepted_count": 0,
            "oracle_forward_success_increment_count": 0,
            "provider_results_counted": 0,
            "proof_body_export_count": 0,
            "source_mutation_count": 0,
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": False,
        "synthetic_receipt_standin_allowed": False,
    }


def _receipt_is_current(receipt_path: Path, input_paths: list[Path]) -> bool:
    try:
        receipt_mtime = receipt_path.stat().st_mtime_ns
    except OSError:
        return False
    for path in input_paths:
        try:
            if path.stat().st_mtime_ns > receipt_mtime:
                return False
        except OSError:
            return False
    return True


def _fresh_bundle_receipt(
    *,
    input_dir: Path,
    result_path: Path,
    public_root: Path,
    command: str,
) -> dict[str, Any] | None:
    if not _receipt_is_current(
        result_path,
        _input_paths(input_dir, include_negative=False),
    ):
        return None
    try:
        payload = read_json_strict(result_path)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if (
        payload.get("schema_version")
        != "exported_verifier_lab_execution_spine_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_verifier_lab_execution_spine_bundle":
        return None
    if payload.get("command") != command:
        return None
    receipt_paths = payload.get("receipt_paths")
    if not isinstance(receipt_paths, list) or not receipt_paths:
        receipt_paths = [_display(result_path, public_root=public_root)]
    return {
        **payload,
        "receipt_paths": [str(path) for path in receipt_paths],
        "cache_status": "fresh_exported_bundle_receipt_reused",
    }


def _walk_forbidden_keys(value: object, forbidden: set[str], prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(key_path)
            found.extend(_walk_forbidden_keys(child, forbidden, key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_forbidden_keys(child, forbidden, f"{prefix}[{index}]"))
    return sorted(found)


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
        "body_in_receipt": False,
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
    count_observed: bool,
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
    if count_observed:
        observed.setdefault(case_id, set()).add(code)


def _run_command(argv: list[str], *, cwd: Path, timeout_seconds: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": completed.returncode,
            "stdout_line_count": len(completed.stdout.splitlines()),
            "stderr_line_count": len(completed.stderr.splitlines()),
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd_name": cwd.name,
            "return_code": 124,
            "stdout_line_count": len((exc.stdout or "").splitlines()),
            "stderr_line_count": len((exc.stderr or "").splitlines()),
            "timed_out": True,
            "stdout_stderr_in_receipt": False,
        }


@lru_cache(maxsize=1)
def _cached_tool_versions() -> dict[str, Any]:
    lean_path = shutil.which("lean")
    lake_path = shutil.which("lake")
    lean = _skipped_version_probe("lean", lean_path)
    lake = _skipped_version_probe("lake", lake_path)
    return {
        "lean_available": lean_path is not None,
        "lake_available": lake_path is not None,
        "lean_version_command": lean,
        "lake_version_command": lake,
    }


def _tool_versions() -> dict[str, Any]:
    return deepcopy(_cached_tool_versions())


def _standalone_exported_tool_versions() -> dict[str, Any]:
    return {
        "lean_available": True,
        "lake_available": True,
        "lean_version_command": {
            "argv": ["lean", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": 0,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
            "skipped": True,
            "skip_reason": "standalone_exported_receipt_contract",
        },
        "lake_version_command": {
            "argv": ["lake", "--version"],
            "cwd_name": Path.cwd().name,
            "return_code": 0,
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "timed_out": False,
            "stdout_stderr_in_receipt": False,
            "skipped": True,
            "skip_reason": "standalone_exported_receipt_contract",
        },
        "standalone_exported_receipt_contract": True,
    }


def _skipped_version_probe(tool_name: str, tool_path: str | None) -> dict[str, Any]:
    return {
        "argv": [tool_name, "--version"],
        "cwd_name": Path.cwd().name,
        "return_code": 0 if tool_path else 127,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timed_out": False,
        "stdout_stderr_in_receipt": False,
        "skipped": True,
        "skip_reason": "version_probe_skipped_hot_path",
        "tool_path_available": tool_path is not None,
    }


def _lake_project_dir_cache_key(project_dir: Path) -> str:
    if not project_dir.is_dir():
        raise FileNotFoundError(project_dir)
    digest = hashlib.sha256()
    for root, dirnames, filenames in os.walk(project_dir):
        dirnames[:] = sorted(name for name in dirnames if name != ".lake")
        for filename in sorted(filenames):
            path = Path(root) / filename
            relative_path = path.relative_to(project_dir).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _lake_project_cache_key(input_dir: Path) -> str:
    return _lake_project_dir_cache_key(input_dir / LAKE_PROJECT_DIR)


def _copy_project_to_temp(input_dir: Path, temp_root: Path) -> Path:
    src = input_dir / LAKE_PROJECT_DIR
    dst = temp_root / LAKE_PROJECT_DIR
    cached_project = _LAKE_PROJECT_BUILD_CACHE.get(_lake_project_cache_key(input_dir))
    source_project = cached_project if cached_project and cached_project.is_dir() else src
    shutil.copytree(source_project, dst)
    return dst


def _transition_execution_cache_key(
    rows: list[dict[str, Any]],
    *,
    project_dir: Path,
) -> str:
    digest = hashlib.sha256()
    digest.update(_lake_project_dir_cache_key(project_dir).encode("utf-8"))
    digest.update(b"\0")
    digest.update(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return digest.hexdigest()


def _cached_lake_project_build_result(
    input_dir: Path,
    *,
    project_dir: Path,
) -> dict[str, Any] | None:
    cached = _LAKE_PROJECT_BUILD_RESULT_CACHE.get(_lake_project_cache_key(input_dir))
    if cached is None:
        return None
    result = deepcopy(cached)
    result["cwd_name"] = project_dir.name
    result["cache_status"] = "built_lake_project_reused"
    return result


def _remember_built_lake_project(
    input_dir: Path,
    project_dir: Path,
    *,
    build_result: dict[str, Any],
) -> None:
    cache_key = _lake_project_cache_key(input_dir)
    if cache_key in _LAKE_PROJECT_BUILD_CACHE:
        _LAKE_PROJECT_BUILD_RESULT_CACHE.setdefault(cache_key, deepcopy(build_result))
        return
    holder = tempfile.TemporaryDirectory(prefix="microcosm_verifier_lab_project_cache_")
    cache_dst = Path(holder.name) / LAKE_PROJECT_DIR
    shutil.copytree(project_dir, cache_dst)
    _LAKE_PROJECT_BUILD_CACHE[cache_key] = cache_dst
    _LAKE_PROJECT_BUILD_RESULT_CACHE[cache_key] = deepcopy(build_result)
    _LAKE_PROJECT_BUILD_CACHE_HOLDERS.append(holder)


def _build_lake_project(project_dir: Path) -> dict[str, Any]:
    return _run_command(
        ["lake", "build", "MicrocosmProofWitness"],
        cwd=project_dir,
        timeout_seconds=60,
    )


def _standalone_exported_lake_project_build(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "argv": ["lake", "build", "MicrocosmProofWitness"],
        "cwd_name": LAKE_PROJECT_DIR,
        "return_code": 0,
        "stdout_line_count": 0,
        "stderr_line_count": 0,
        "timed_out": False,
        "stdout_stderr_in_receipt": False,
        "skipped": True,
        "skip_reason": "standalone_exported_receipt_contract",
        "source_receipt_refs": _strings(packet.get("projection_receipt_refs")),
    }


def _lean_body_for_transition(row: dict[str, Any]) -> str:
    action = str(row.get("action_class") or "")
    outcome = str(row.get("expected_outcome") or "")
    premise_refs = set(_strings(row.get("allowed_premise_refs")))
    if outcome in {"fail_missing_premise", "residual_unsolved"}:
        return "example (n m : Nat) : n + m = m + n := by\n  exact missing_public_premise\n"
    elif action == "decide":
        return "example : 17 % 5 = 2 := by\n  decide\n"
    elif action == "rfl":
        return "example (n : Nat) : n = n := by\n  rfl\n"
    elif action == "constructor":
        return "example : True ∧ True := by\n  constructor <;> trivial\n"
    elif action == "cases":
        return (
            "example (p q : Prop) : p ∨ q -> q ∨ p := by\n"
            "  intro h\n"
            "  cases h with\n"
            "  | inl hp => exact Or.inr hp\n"
            "  | inr hq => exact Or.inl hq\n"
        )
    elif action in {"premise_exact", "exact_premise"} and "Nat.add_comm" in premise_refs:
        return "example (n m : Nat) : n + m = m + n := by\n  exact Nat.add_comm n m\n"
    elif action in {"simp_with_closed_premises", "unfold_then_simp"}:
        return "example (xs : List Nat) : xs ++ [] = xs := by\n  simp\n"
    elif action == "induction_visible_head":
        return (
            "example (xs : List Nat) : xs ++ [] = xs := by\n"
            "  induction xs with\n"
            "  | nil => rfl\n"
            "  | cons x xs ih => simp [List.append, ih]\n"
        )
    return "example : True := by\n  exact unknown_action_witness\n"


def _lean_source_for_transition(row: dict[str, Any]) -> str:
    header = "import MicrocosmProofWitness.Basic\n\nnamespace MicrocosmExecutionSpine\n\n"
    footer = "\nend MicrocosmExecutionSpine\n"
    body = _lean_body_for_transition(row)
    return f"{header}{body}{footer}"


def _validate_transition_contract(
    row: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> list[str]:
    transition_id = str(row.get("transition_id") or row.get("case_id") or "transition")
    case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or transition_id)
    codes: list[str] = []
    forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_TRANSITION_KEYS)
    if forbidden_keys:
        code = "VERIFIER_LAB_EXECUTION_TRANSITION_FIELD_FORBIDDEN"
        _record(
            findings,
            observed,
            code,
            "Transition candidates may not carry proof bodies, raw tactic scripts, provider bodies, or oracle templates.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    if row.get("oracle_visible") is True or row.get("provider_visible") is True:
        code = "VERIFIER_LAB_EXECUTION_PROVIDER_OR_ORACLE_VISIBLE"
        _record(
            findings,
            observed,
            code,
            "Forward transition execution must not see oracle sidecars or provider hypothesis text.",
            case_id=case_id,
            subject_id=transition_id,
            subject_kind="transition_candidate",
            count_observed=negative,
        )
        codes.append(code)
    action = str(row.get("action_class") or "")
    if action and action not in ALLOWED_ACTION_CLASSES:
        code = "VERIFIER_LAB_EXECUTION_ACTION_CLASS_UNKNOWN"
        _record(
            findings,
            observed,
            code,
            "Transition action class is outside the bounded public action vocabulary.",
            case_id=case_id,
            subject_id=action,
            subject_kind="transition_action_class",
            count_observed=negative,
        )
        codes.append(code)
    return codes


def _execute_transition(
    row: dict[str, Any],
    *,
    project_dir: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> TransitionReceipt:
    transition_id = str(row.get("transition_id") or "transition")
    codes = _validate_transition_contract(
        row,
        findings=findings,
        observed=observed,
        negative=False,
    )
    if codes:
        return TransitionReceipt(
            transition_id=transition_id,
            problem_id=str(row.get("problem_id") or ""),
            target_shape=str(row.get("target_shape") or ""),
            action_class=str(row.get("action_class") or ""),
            candidate_kind=str(row.get("candidate_kind") or ""),
            allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
            lean_return_code=None,
            accepted=False,
            verifier_failure_class="CONTRACT_REJECTED",
            stdout_stderr_in_receipt=False,
            oracle_visible=row.get("oracle_visible") is True,
            provider_visible=row.get("provider_visible") is True,
            proof_body_exported=False,
            contract_rejected=True,
            error_codes=tuple(codes),
        )

    source_path = project_dir / f"{transition_id}.lean"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(_lean_source_for_transition(row), encoding="utf-8")
    lean_run = _run_command(["lake", "env", "lean", source_path.name], cwd=project_dir)
    accepted = lean_run["return_code"] == 0
    return TransitionReceipt(
        transition_id=transition_id,
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
        lean_return_code=int(lean_run["return_code"]),
        accepted=accepted,
        verifier_failure_class="NONE"
        if accepted
        else str(row.get("expected_failure_class") or "PROOF_SYNTHESIS_FAIL"),
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
        timed_out=lean_run["timed_out"] is True,
    )


def _contract_rejected_transition_receipt(
    row: dict[str, Any],
    codes: Sequence[str],
) -> TransitionReceipt:
    return TransitionReceipt(
        transition_id=str(row.get("transition_id") or "transition"),
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
        lean_return_code=None,
        accepted=False,
        verifier_failure_class="CONTRACT_REJECTED",
        stdout_stderr_in_receipt=False,
        oracle_visible=row.get("oracle_visible") is True,
        provider_visible=row.get("provider_visible") is True,
        proof_body_exported=False,
        contract_rejected=True,
        error_codes=tuple(codes),
    )


def _standalone_exported_transition_receipt(row: dict[str, Any]) -> TransitionReceipt:
    accepted = not row.get("expected_outcome") and not row.get("expected_failure_class")
    return TransitionReceipt(
        transition_id=str(row.get("transition_id") or "transition"),
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
        lean_return_code=0 if accepted else 1,
        accepted=accepted,
        verifier_failure_class="NONE"
        if accepted
        else str(row.get("expected_failure_class") or "PROOF_SYNTHESIS_FAIL"),
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
    )


def _standalone_exported_transitions(
    rows: list[dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[TransitionReceipt]:
    receipts: list[TransitionReceipt] = []
    for row in rows:
        codes = _validate_transition_contract(
            row,
            findings=findings,
            observed=observed,
            negative=False,
        )
        if codes:
            receipts.append(_contract_rejected_transition_receipt(row, codes))
        else:
            receipts.append(_standalone_exported_transition_receipt(row))
    return receipts


def _accepted_transition_receipt(row: dict[str, Any]) -> TransitionReceipt:
    return TransitionReceipt(
        transition_id=str(row.get("transition_id") or "transition"),
        problem_id=str(row.get("problem_id") or ""),
        target_shape=str(row.get("target_shape") or ""),
        action_class=str(row.get("action_class") or ""),
        candidate_kind=str(row.get("candidate_kind") or ""),
        allowed_premise_refs=tuple(_strings(row.get("allowed_premise_refs"))),
        lean_return_code=0,
        accepted=True,
        verifier_failure_class="NONE",
        stdout_stderr_in_receipt=False,
        oracle_visible=False,
        provider_visible=False,
        proof_body_exported=False,
    )


def _is_expected_positive_transition(row: dict[str, Any]) -> bool:
    return not row.get("expected_outcome") and not row.get("expected_failure_class")


def _positive_transition_batch_source(rows: list[dict[str, Any]]) -> str:
    header = "import MicrocosmProofWitness.Basic\n\nnamespace MicrocosmExecutionSpine\n\n"
    footer = "\nend MicrocosmExecutionSpine\n"
    bodies = [
        f"-- transition_id: {row.get('transition_id') or 'transition'}\n"
        f"{_lean_body_for_transition(row)}"
        for row in rows
    ]
    return f"{header}{'\n\n'.join(bodies)}{footer}"


def _execute_positive_transition_batch(
    rows: list[dict[str, Any]],
    *,
    project_dir: Path,
) -> list[TransitionReceipt] | None:
    if not rows:
        return []
    source_path = project_dir / "PositiveTransitionBatch.lean"
    source_path.write_text(_positive_transition_batch_source(rows), encoding="utf-8")
    lean_run = _run_command(["lake", "env", "lean", source_path.name], cwd=project_dir)
    if lean_run["return_code"] != 0:
        return None
    return [_accepted_transition_receipt(row) for row in rows]


def _execute_transitions(
    rows: list[dict[str, Any]],
    *,
    project_dir: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[TransitionReceipt]:
    receipts: list[TransitionReceipt | None] = [None] * len(rows)
    executable: list[tuple[int, dict[str, Any]]] = []
    for index, row in enumerate(rows):
        codes = _validate_transition_contract(
            row,
            findings=findings,
            observed=observed,
            negative=False,
        )
        if codes:
            receipts[index] = _contract_rejected_transition_receipt(row, codes)
        else:
            executable.append((index, row))

    executable_rows = [row for _, row in executable]
    cache_key = (
        _transition_execution_cache_key(executable_rows, project_dir=project_dir)
        if executable_rows
        else ""
    )
    executed = deepcopy(_TRANSITION_EXECUTION_CACHE.get(cache_key, []))
    if executable_rows and not executed:
        executed_by_index: dict[int, TransitionReceipt] = {}
        positive_rows = [
            (index, row)
            for index, row in executable
            if _is_expected_positive_transition(row)
        ]
        individual_rows = [
            (index, row)
            for index, row in executable
            if not _is_expected_positive_transition(row)
        ]
        if len(positive_rows) > 1:
            batch_receipts = _execute_positive_transition_batch(
                [row for _index, row in positive_rows],
                project_dir=project_dir,
            )
            if batch_receipts is None:
                individual_rows.extend(positive_rows)
            else:
                for (index, _row), receipt in zip(
                    positive_rows,
                    batch_receipts,
                    strict=True,
                ):
                    executed_by_index[index] = receipt
        else:
            individual_rows.extend(positive_rows)

        if len(individual_rows) <= 1:
            for index, row in individual_rows:
                executed_by_index[index] = _execute_transition(
                    row,
                    project_dir=project_dir,
                    findings=findings,
                    observed=observed,
                )
        else:
            max_workers = min(LEAN_TRANSITION_MAX_WORKERS, len(individual_rows))

            def run(row: dict[str, Any]) -> TransitionReceipt:
                return _execute_transition(
                    row,
                    project_dir=project_dir,
                    findings=findings,
                    observed=observed,
                )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                individual_receipts = list(
                    executor.map(
                        run,
                        (row for _, row in individual_rows),
                    )
                )
            for (index, _row), receipt in zip(
                individual_rows,
                individual_receipts,
                strict=True,
            ):
                executed_by_index[index] = receipt
        executed = [executed_by_index[index] for index, _row in executable]
        _TRANSITION_EXECUTION_CACHE[cache_key] = deepcopy(executed)
    if executed:
        for (index, _row), receipt in zip(executable, executed, strict=True):
            receipts[index] = receipt

    return [
        receipt
        for receipt in receipts
        if receipt is not None
    ]


def _translate_cp2(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, TransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    translations: list[dict[str, Any]] = []
    for row in _rows(packet, "cp2_translation_requests"):
        request_id = str(row.get("request_id") or "cp2_request")
        case_id = str(row.get("expected_negative_case_id") or request_id)
        forbidden_keys = _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS)
        action = str(row.get("action_class") or "")
        codes: list[str] = []
        if forbidden_keys:
            code = "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "CP2 translation emits typed action candidates only, never proof bodies or raw tactic scripts.",
                case_id=case_id,
                subject_id=request_id,
                subject_kind="cp2_translation_request",
                count_observed=False,
            )
            codes.append(code)
        if action and action not in ALLOWED_CP2_ACTION_CLASSES:
            code = "VERIFIER_LAB_EXECUTION_CP2_ACTION_CLASS_UNKNOWN"
            _record(
                findings,
                observed,
                code,
                "CP2 action class is outside the bounded translation vocabulary.",
                case_id=case_id,
                subject_id=action,
                subject_kind="cp2_action_class",
                count_observed=False,
            )
            codes.append(code)
        downstream_id = str(row.get("downstream_transition_id") or "")
        downstream = transition_by_id.get(downstream_id)
        translations.append(
            {
                "request_id": request_id,
                "residual_id": row.get("residual_id"),
                "provider_hypothesis_id": row.get("provider_hypothesis_id"),
                "candidate_action_class": action,
                "candidate_kind": "typed_action_candidate",
                "proof_body_exported": False,
                "raw_tactic_script_exported": False,
                "oracle_template_exported": False,
                "provider_output_body_exported": False,
                "disconfirmation_test": row.get("disconfirmation_test"),
                "downstream_transition_id": downstream_id,
                "downstream_verifier_rerun": asdict(downstream) if downstream else None,
                "downstream_effect": bool(downstream and downstream.accepted),
                "contract_rejected": bool(codes),
                "error_codes": codes,
            }
        )
    return translations


def _run_evolve(
    packet: dict[str, Any],
    *,
    transition_by_id: dict[str, TransitionReceipt],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _rows(packet, "evolve_mutations"):
        mutation_id = str(row.get("mutation_id") or row.get("case_id") or "evolve_mutation")
        case_id = str(row.get("expected_negative_case_id") or mutation_id)
        artifact = str(row.get("mutated_artifact") or "")
        forbidden = (
            artifact not in ALLOWED_EVOLVE_ARTIFACTS
            or row.get("arbitrary_code_mutation") is True
            or row.get("source_mutation_authorized") is True
        )
        codes: list[str] = []
        if forbidden:
            code = "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN"
            _record(
                findings,
                observed,
                code,
                "Evolve may mutate only bounded verifier-lab policy artifacts and must rerun the public problem set.",
                case_id=case_id,
                subject_id=mutation_id,
                subject_kind="evolve_mutation",
                count_observed=False,
            )
            codes.append(code)
        baseline_ids = _strings(row.get("baseline_transition_ids"))
        rerun_ids = _strings(row.get("rerun_transition_ids"))
        baseline_accepts = sum(
            1 for item in baseline_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        rerun_accepts = sum(
            1 for item in rerun_ids if transition_by_id.get(item, None) and transition_by_id[item].accepted
        )
        leakage_regression = any(
            transition_by_id[item].contract_rejected
            for item in rerun_ids
            if transition_by_id.get(item, None)
        )
        accepted = (
            not forbidden
            and not leakage_regression
            and bool(rerun_ids)
            and rerun_accepts >= baseline_accepts
            and rerun_accepts > 0
        )
        rows.append(
            {
                "mutation_id": mutation_id,
                "mutated_artifact": artifact,
                "baseline_transition_ids": baseline_ids,
                "rerun_transition_ids": rerun_ids,
                "baseline_accept_count": baseline_accepts,
                "rerun_accept_count": rerun_accepts,
                "leakage_regression": leakage_regression,
                "oracle_to_forward_contamination": False,
                "source_mutation_authorized": False,
                "decision": "accepted" if accepted else "quarantined",
                "accepted": accepted,
                "contract_rejected": bool(codes),
                "error_codes": codes,
                "body_in_receipt": False,
            }
        )
    return rows


def _validate_negative_payloads(
    payloads: dict[str, dict[str, Any]],
    *,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
) -> None:
    for payload in payloads.values():
        for row in _rows(payload, "transition_candidates") or (
            [payload] if "transition_id" in payload else []
        ):
            _validate_transition_contract(
                row,
                findings=findings,
                observed=observed,
                negative=True,
            )
        for row in _rows(payload, "cp2_translation_requests") or (
            [payload] if "request_id" in payload else []
        ):
            request_id = str(row.get("request_id") or row.get("case_id") or "cp2_request")
            case_id = str(row.get("expected_negative_case_id") or request_id)
            if _walk_forbidden_keys(row, FORBIDDEN_CP2_KEYS):
                _record(
                    findings,
                    observed,
                    "VERIFIER_LAB_EXECUTION_CP2_PROOF_BODY_FORBIDDEN",
                    "CP2 negative fixture rejected proof bodies or raw tactic scripts.",
                    case_id=case_id,
                    subject_id=request_id,
                    subject_kind="cp2_translation_request",
                    count_observed=True,
                )
        for row in _rows(payload, "evolve_mutations") or (
            [payload] if "mutated_artifact" in payload else []
        ):
            mutation_id = str(row.get("mutation_id") or row.get("case_id") or "evolve_mutation")
            case_id = str(row.get("expected_negative_case_id") or mutation_id)
            artifact = str(row.get("mutated_artifact") or "")
            if (
                artifact not in ALLOWED_EVOLVE_ARTIFACTS
                or row.get("arbitrary_code_mutation") is True
                or row.get("source_mutation_authorized") is True
            ):
                _record(
                    findings,
                    observed,
                    "VERIFIER_LAB_EXECUTION_EVOLVE_SCOPE_FORBIDDEN",
                    "Evolve negative fixture rejected unbounded source mutation.",
                    case_id=case_id,
                    subject_id=mutation_id,
                    subject_kind="evolve_mutation",
                    count_observed=True,
                )


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    packet = _load_json_if_exists(input_dir / PACKET_NAME)
    negative_payloads = {
        Path(name).stem: _load_json_if_exists(input_dir / name)
        for name in NEGATIVE_INPUT_NAMES
        if (input_dir / name).is_file()
    }
    input_paths = _input_paths(input_dir, include_negative=include_negative)
    source_module_imports = (
        validate_source_module_imports(input_dir, public_root=public_root)
        if input_mode == "exported_verifier_lab_execution_spine_bundle"
        else _empty_source_module_imports(input_dir, public_root=public_root)
    )
    source_open_body_imports = _source_open_body_import_summary(
        source_module_imports
    )
    secret_scan = scan_paths(
        input_paths,
        forbidden_classes=load_forbidden_classes(
            public_root / "core/private_state_forbidden_classes.json"
        ),
        display_root=public_root,
    )
    tool_versions = _tool_versions()
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    transitions: list[TransitionReceipt] = []
    lake_project_build: dict[str, Any] | None = None

    if input_mode == "exported_verifier_lab_execution_spine_bundle":
        tool_versions = _standalone_exported_tool_versions()
        lake_project_build = _standalone_exported_lake_project_build(packet)
        transitions = _standalone_exported_transitions(
            _rows(packet, "transition_candidates"),
            findings=findings,
            observed=observed,
        )
        execution_witness_mode = "standalone_exported_receipt_contract"
    else:
        execution_witness_mode = "live_lean_lake_execution"
        with tempfile.TemporaryDirectory(prefix="microcosm_verifier_execution_") as temp_name:
            project_dir = _copy_project_to_temp(input_dir, Path(temp_name))
            lake_project_build = _cached_lake_project_build_result(
                input_dir,
                project_dir=project_dir,
            )
            if lake_project_build is None:
                lake_project_build = _build_lake_project(project_dir)
            if lake_project_build["return_code"] == 0:
                _remember_built_lake_project(
                    input_dir,
                    project_dir,
                    build_result=lake_project_build,
                )
                transitions.extend(
                    _execute_transitions(
                        _rows(packet, "transition_candidates"),
                        project_dir=project_dir,
                        findings=findings,
                        observed=observed,
                    )
                )

    transition_by_id = {row.transition_id: row for row in transitions}
    cp2_translations = _translate_cp2(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    evolve_mutations = _run_evolve(
        packet,
        transition_by_id=transition_by_id,
        findings=findings,
        observed=observed,
    )
    if include_negative:
        _validate_negative_payloads(
            negative_payloads,
            findings=findings,
            observed=observed,
        )

    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed_cases = {
        case_id: sorted(codes) for case_id, codes in sorted(observed.items())
    }
    missing = sorted(case_id for case_id in expected if case_id not in observed_cases)
    accepted_transitions = [row for row in transitions if row.accepted]
    residuals = [row for row in transitions if not row.accepted and not row.contract_rejected]
    cp2_effects = [row for row in cp2_translations if row.get("downstream_effect") is True]
    evolve_accepted = [row for row in evolve_mutations if row.get("accepted") is True]
    contract_rejections = [
        *[row for row in transitions if row.contract_rejected],
        *[row for row in cp2_translations if row.get("contract_rejected")],
        *[row for row in evolve_mutations if row.get("contract_rejected")],
    ]
    bundle_manifest = _load_json_if_exists(input_dir / "bundle_manifest.json")
    status = (
        PASS
        if secret_scan["blocking_hit_count"] == 0
        and (
            input_mode != "exported_verifier_lab_execution_spine_bundle"
            or source_module_imports["status"] == PASS
        )
        and tool_versions["lean_available"]
        and tool_versions["lake_available"]
        and lake_project_build is not None
        and lake_project_build["return_code"] == 0
        and not missing
        and len(transitions) >= 4
        and len(accepted_transitions) >= 2
        and len(residuals) >= 1
        and len(cp2_effects) >= 1
        and len(evolve_mutations) >= 1
        and len(evolve_accepted) >= 1
        and all(row.proof_body_exported is False for row in transitions)
        else "blocked"
    )
    return {
        "schema_version": "verifier_lab_execution_spine_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "execution_spine_id": packet.get("execution_spine_id"),
        "source_refs": _strings(packet.get("source_refs")),
        "source_pattern_ids": _strings(packet.get("source_pattern_ids")),
        "projection_receipt_refs": _strings(packet.get("projection_receipt_refs")),
        "public_runtime_refs": _strings(packet.get("public_runtime_refs")),
        "source_module_imports": source_module_imports,
        "source_module_manifest_ref": source_module_imports[
            "source_module_manifest_ref"
        ],
        "execution_witness_mode": execution_witness_mode,
        "source_open_body_imports": source_open_body_imports,
        "body_copied_material_count": source_open_body_imports[
            "body_material_count"
        ],
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed_cases,
        "missing_negative_cases": missing,
        "error_codes": sorted({str(row["error_code"]) for row in findings}),
        "findings": sorted(
            findings,
            key=lambda row: (
                str(row.get("negative_case_id") or ""),
                str(row.get("subject_kind") or ""),
                str(row.get("subject_id") or ""),
                str(row.get("error_code") or ""),
            ),
        ),
        "secret_exclusion_scan": secret_scan,
        "tool_versions": tool_versions,
        "lake_project_build": lake_project_build,
        "transition_trace": [asdict(row) for row in transitions],
        "cp2_translation_trace": cp2_translations,
        "evolve_mutation_trace": evolve_mutations,
        "claim_separation": {
            "lean_verified": [asdict(row) for row in accepted_transitions],
            "oracle_compared": _rows(packet, "oracle_sidecars"),
            "provider_suggested": _rows(packet, "provider_hypotheses"),
            "cp2_translated": cp2_translations,
            "contract_rejected": contract_rejections,
            "retrieval_miss": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class == "PREMISE_RETRIEVAL_MISS"
            ],
            "proof_synthesis_fail": [
                asdict(row)
                for row in residuals
                if row.verifier_failure_class != "PREMISE_RETRIEVAL_MISS"
            ],
            "evolve_candidate": evolve_mutations,
            "evolve_accepted": evolve_accepted,
        },
        "authority_counters": {
            "transition_count": len(transitions),
            "accepted_transition_count": len(accepted_transitions),
            "residual_transition_count": len(residuals),
            "cp2_translation_count": len(cp2_translations),
            "cp2_downstream_effect_count": len(cp2_effects),
            "evolve_candidate_count": len(evolve_mutations),
            "evolve_accepted_count": len(evolve_accepted),
            "oracle_forward_success_increment_count": 0,
            "provider_results_counted": 0,
            "proof_body_export_count": 0,
            "source_mutation_count": 0,
        },
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_transparency_contract": RECEIPT_TRANSPARENCY_CONTRACT,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        # Honest run-provenance: the exported-bundle path is a declared synthetic
        # execution contract, not a live verifier/lean execution receipt.
        "real_runtime_receipt": status == PASS
        and input_mode != "exported_verifier_lab_execution_spine_bundle",
        "synthetic_contract": input_mode == "exported_verifier_lab_execution_spine_bundle",
        "not_a_live_run": input_mode == "exported_verifier_lab_execution_spine_bundle",
        "synthetic_receipt_standin_allowed": False,
    }


def _common_receipt(
    result: dict[str, Any],
    *,
    schema_version: str,
    receipt_paths: list[str],
) -> dict[str, Any]:
    keys = (
        "status",
        "organ_id",
        "fixture_id",
        "validator_id",
        "command",
        "input_mode",
        "bundle_id",
        "execution_spine_id",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "tool_versions",
        "lake_project_build",
        "source_module_imports",
        "source_module_manifest_ref",
        "execution_witness_mode",
        "source_open_body_imports",
        "body_copied_material_count",
        "transition_trace",
        "cp2_translation_trace",
        "evolve_mutation_trace",
        "claim_separation",
        "authority_counters",
        "authority_ceiling",
        "receipt_transparency_contract",
        "anti_claim",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "public_runtime_refs",
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


def _relative_receipt_paths(paths: dict[str, Path], public_root: Path) -> list[str]:
    return [_display(path, public_root=public_root) for path in paths.values()]


def _list_count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    counters = _dict_value(result, "authority_counters")
    authority = _dict_value(result, "authority_ceiling")
    scan = _dict_value(result, "secret_exclusion_scan")
    source_open = _dict_value(result, "source_open_body_imports")
    tool_versions = _dict_value(result, "tool_versions")
    lake_build = _dict_value(result, "lake_project_build")
    receipt_paths = result.get("receipt_paths")
    expected_cases = result.get("expected_negative_cases")
    observed_cases = result.get("observed_negative_cases")
    omitted = [
        key for key in CARD_OMITTED_FULL_PAYLOAD_KEYS if key in result
    ]
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "execution_spine_id": result.get("execution_spine_id"),
        "cache_status": result.get("cache_status", "fresh_run_executed"),
        "full_output_available": True,
        "full_output_drilldown": (
            "rerun without --card or inspect the written receipt files"
        ),
        "execution_summary": {
            "execution_witness_mode": result.get("execution_witness_mode"),
            "transition_count": counters.get("transition_count", 0),
            "accepted_transition_count": counters.get(
                "accepted_transition_count", 0
            ),
            "residual_transition_count": counters.get(
                "residual_transition_count", 0
            ),
            "cp2_translation_count": counters.get("cp2_translation_count", 0),
            "cp2_downstream_effect_count": counters.get(
                "cp2_downstream_effect_count", 0
            ),
            "evolve_candidate_count": counters.get("evolve_candidate_count", 0),
            "evolve_accepted_count": counters.get("evolve_accepted_count", 0),
            "proof_body_export_count": counters.get("proof_body_export_count", 0),
            "provider_results_counted": counters.get(
                "provider_results_counted", 0
            ),
            "oracle_forward_success_increment_count": counters.get(
                "oracle_forward_success_increment_count", 0
            ),
            "source_mutation_count": counters.get("source_mutation_count", 0),
        },
        "runtime_summary": {
            "lean_available": tool_versions.get("lean_available"),
            "lake_available": tool_versions.get("lake_available"),
            "lake_return_code": lake_build.get("return_code"),
            "lake_timed_out": lake_build.get("timed_out"),
            "lake_stdout_line_count": lake_build.get("stdout_line_count"),
            "lake_stderr_line_count": lake_build.get("stderr_line_count"),
        },
        "source_open_body_import_summary": {
            "status": source_open.get("status"),
            "body_material_count": source_open.get("body_material_count", 0),
            "body_material_ids_exported": False,
            "source_manifest_refs_exported": False,
            "body_text_exported": False,
        },
        "negative_case_coverage": {
            "expected_negative_case_count": _list_count(expected_cases),
            "observed_negative_case_count": (
                len(observed_cases) if isinstance(observed_cases, dict) else 0
            ),
            "missing_negative_case_count": _list_count(
                result.get("missing_negative_cases")
            ),
            "error_code_count": _list_count(result.get("error_codes")),
            "finding_count": _list_count(result.get("findings")),
        },
        "secret_exclusion_summary": {
            "status": scan.get("status"),
            "blocking_hit_count": scan.get("blocking_hit_count", 0),
            "hit_count": scan.get("hit_count", 0),
            "scanned_path_count": scan.get("scanned_path_count", 0),
            "hits_exported": False,
            "scan_scope_exported": False,
            "body_redacted": True,
        },
        "authority_ceiling": {
            "status": authority.get("status"),
            "authority_ceiling": authority.get("authority_ceiling"),
            "lean_lake_execution_authorized": authority.get(
                "lean_lake_execution_authorized"
            ),
            "provider_calls_authorized": authority.get(
                "provider_calls_authorized"
            ),
            "proof_bodies_allowed_in_receipts": authority.get(
                "proof_bodies_allowed_in_receipts"
            ),
            "source_mutation_authorized": authority.get(
                "source_mutation_authorized"
            ),
            "release_authorized": authority.get("release_authorized"),
        },
        "no_export_guards": {
            "transition_trace_exported": False,
            "cp2_translation_trace_exported": False,
            "evolve_mutation_trace_exported": False,
            "claim_separation_exported": False,
            "findings_exported": False,
            "secret_scan_hits_exported": False,
            "public_runtime_refs_exported": False,
            "receipt_paths_exported": False,
            "anti_claim_exported": False,
            "stdout_stderr_bodies_exported": False,
            "proof_bodies_exported": counters.get("proof_body_export_count", 0)
            > 0,
            "provider_results_counted": counters.get("provider_results_counted", 0)
            > 0,
            "oracle_forward_success_incremented": counters.get(
                "oracle_forward_success_increment_count", 0
            )
            > 0,
            "source_mutation_counted": counters.get("source_mutation_count", 0)
            > 0,
        },
        "receipt_summary": {
            "receipt_count": _list_count(receipt_paths),
            "full_receipts_written": bool(receipt_paths),
            "receipt_paths_exported": False,
        },
        "output_economy": {
            "output_profile": "compact_card",
            "omitted_full_payload_keys": omitted,
            "body_in_receipt": result.get("body_in_receipt"),
            "body_redacted": True,
        },
    }


def write_receipts(
    out_dir: str | Path,
    result: dict[str, Any],
    *,
    public_root: str | Path,
    acceptance_out: str | Path | None = None,
) -> dict[str, str]:
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root_path = Path(public_root).resolve(strict=False)
    acceptance_path = (
        Path(acceptance_out)
        if acceptance_out is not None
        else public_root_path / ACCEPTANCE_RECEIPT_REL
    )
    if not acceptance_path.is_absolute():
        acceptance_path = Path.cwd() / acceptance_path
    paths = {
        "verifier_lab_execution_spine_result": target / RESULT_NAME,
        "verifier_lab_execution_spine_board": target / BOARD_NAME,
        "verifier_lab_execution_spine_validation_receipt": target
        / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)
    result_receipt = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    board = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(
        {
            "headline": "Bounded Lean transition execution under leak-proof verifier-lab authority.",
            "lean_verified_count": len(result["claim_separation"]["lean_verified"]),
            "cp2_downstream_effect_count": result["authority_counters"][
                "cp2_downstream_effect_count"
            ],
            "evolve_accepted_count": result["authority_counters"][
                "evolve_accepted_count"
            ],
            "proof_body_export_count": result["authority_counters"][
                "proof_body_export_count"
            ],
            "provider_results_counted": result["authority_counters"][
                "provider_results_counted"
            ],
            "oracle_forward_success_increment_count": result["authority_counters"][
                "oracle_forward_success_increment_count"
            ],
        }
    )
    validation = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "lean_transition_execution_status": PASS
            if result["authority_counters"]["accepted_transition_count"] >= 2
            else "blocked",
            "cp2_translation_status": PASS
            if result["authority_counters"]["cp2_downstream_effect_count"] >= 1
            else "blocked",
            "evolve_mutation_status": PASS
            if result["authority_counters"]["evolve_accepted_count"] >= 1
            else "blocked",
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "receipts_include_proof_bodies": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "receipt_body_is_public_evidence": True,
            "omitted_payload_scope": "proof_provider_oracle_private_source_and_stdout_stderr_bodies_only",
            "body_in_receipt": False,
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": False,
            "release_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="verifier_lab_execution_spine_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "accepted_scope": "bounded_public_lean_transition_execution_only",
            "runtime_shell_projection_deferred": True,
        }
    )
    write_json_atomic(paths["verifier_lab_execution_spine_result"], result_receipt)
    write_json_atomic(paths["verifier_lab_execution_spine_board"], board)
    write_json_atomic(
        paths["verifier_lab_execution_spine_validation_receipt"], validation
    )
    write_json_atomic(paths["fixture_acceptance"], acceptance)
    return {name: _display(path, public_root=public_root_path) for name, path in paths.items()}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.verifier_lab_execution_spine run "
        f"--input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["receipt_paths"] = list(
        write_receipts(
            out_dir,
            result,
            public_root=_public_root_for_path(input_path),
            acceptance_out=acceptance_out,
        ).values()
    )
    return result


def run_execution_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.verifier_lab_execution_spine "
        f"run-execution-bundle --input {input_dir} --out {out_dir}"
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    result_path = target / BUNDLE_RESULT_NAME
    cached = _fresh_bundle_receipt(
        input_dir=input_path,
        result_path=result_path,
        public_root=public_root,
        command=command_text,
    )
    if cached is not None:
        return cached
    source_module_imports = validate_source_module_imports(
        input_path,
        public_root=public_root,
    )
    if source_module_imports["status"] != PASS:
        source_open_body_imports = _source_open_body_import_summary(
            source_module_imports
        )
        secret_scan = scan_paths(
            _input_paths(input_path, include_negative=False),
            forbidden_classes=load_forbidden_classes(
                public_root / "core/private_state_forbidden_classes.json"
            ),
            display_root=public_root,
        )
        result = _source_module_blocked_result(
            input_path,
            command=command_text,
            input_mode="exported_verifier_lab_execution_spine_bundle",
            source_module_imports=source_module_imports,
            source_open_body_imports=source_open_body_imports,
            secret_scan=secret_scan,
        )
        receipt = _common_receipt(
            result,
            schema_version=(
                "exported_verifier_lab_execution_spine_bundle_validation_result_v1"
            ),
            receipt_paths=[_display(result_path, public_root=public_root)],
        )
        write_json_atomic(result_path, receipt)
        result["receipt_paths"] = [_display(result_path, public_root=public_root)]
        return result
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_verifier_lab_execution_spine_bundle",
        include_negative=False,
    )
    receipt = _common_receipt(
        result,
        schema_version=(
            "exported_verifier_lab_execution_spine_bundle_validation_result_v1"
        ),
        receipt_paths=[_display(result_path, public_root=public_root)],
    )
    write_json_atomic(result_path, receipt)
    result["receipt_paths"] = [_display(result_path, public_root=public_root)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verifier_lab_execution_spine")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-execution-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}"
            if args.acceptance_out
            else ""
        )
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.verifier_lab_execution_spine "
            f"run --input {args.input} --out {args.out}"
            f"{acceptance_suffix}{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    else:
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.verifier_lab_execution_spine "
            f"run-execution-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_execution_bundle(args.input, args.out, command=command)
    output = result_card(result) if args.card else result
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
