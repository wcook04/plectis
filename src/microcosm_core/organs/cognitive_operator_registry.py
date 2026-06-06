from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from collections import defaultdict
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


ORGAN_ID = "cognitive_operator_registry"
FIXTURE_ID = "first_wave.cognitive_operator_registry"
VALIDATOR_ID = "validator.microcosm.organs.cognitive_operator_registry"

RESULT_NAME = "cognitive_operator_registry_result.json"
BOARD_NAME = "cognitive_operator_registry_board.json"
VALIDATION_RECEIPT_NAME = "cognitive_operator_registry_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "cognitive_operator_registry_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_cognitive_operator_registry_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "cognitive_operator_registry_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "covered_operator_ids",
    "findings",
    "secret_exclusion_scan",
    "expected_negative_cases",
    "observed_negative_cases",
    "source_refs",
    "public_runtime_refs",
    "anti_claim",
    "authority_ceiling",
    "source_module_summary",
)

SOURCE_PATTERN_IDS = [
    "cognitive_operator_registry",
    "cogop_landing_handoff_compiler",
    "cogop_operator_accretion_governor",
]
SOURCE_REFS = [
    "microcosm-substrate/core/standards_registry.json",
    "microcosm-substrate/core/organ_registry.json",
    "microcosm-substrate/core/preflight_support/organ_fixture_validator_readiness_v1.json",
]
PUBLIC_RUNTIME_REFS = [
    "core/standards_registry.json",
    "core/organ_registry.json",
    "core/acceptance/first_wave_acceptance.json",
    "core/preflight_support/organ_fixture_validator_readiness_v1.json",
    "fixtures/first_wave/cognitive_operator_registry/input/operator_registry.json",
    "fixtures/first_wave/cognitive_operator_registry/input/operator_standard.json",
    "fixtures/first_wave/cognitive_operator_registry/input/dogfood_index.json",
    "examples/cognitive_operator_registry/exported_cognitive_operator_registry_bundle",
    "paper_modules/cognitive_operator_registry.md",
]

INPUT_NAMES = (
    "operator_registry.json",
    "operator_standard.json",
    "dogfood_index.json",
)
SOURCE_MODULE_MANIFEST_NAME = "source_module_manifest.json"
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_MODULE_IMPORT_STATUS = "copied_non_secret_macro_body_landed"
SOURCE_OPEN_BODY_SCHEMA = "cognitive_operator_registry_source_open_body_imports_v1"
PUBLIC_SAFE_SOURCE_BODY_CLASSES = frozenset(
    {
        "public_macro_pattern_body",
        "public_macro_tool_body",
        "public_macro_receipt_body",
        "public_macro_proof_body",
        "public_macro_standard_body",
        "public_standard_body",
    }
)
NEGATIVE_INPUT_NAMES = (
    "missing_required_field.json",
    "active_without_dogfood.json",
    "dogfood_missing_delta.json",
    "operator_sprawl_near_duplicate.json",
    "authority_overclaim.json",
    "operator_voice_claim.json",
    "private_source_leakage.json",
    "dogfood_unresolved_delta_evidence.json",
)
NEGATIVE_INPUT_STEMS = tuple(Path(name).stem for name in NEGATIVE_INPUT_NAMES)

EXPECTED_NEGATIVE_CASES = {
    "missing_required_field": ["COGOP_MISSING_REQUIRED_FIELD"],
    "active_without_dogfood": ["COGOP_ACTIVE_WITHOUT_DOGFOOD"],
    "dogfood_missing_delta": ["COGOP_DOGFOOD_MISSING_COGNITION_DELTA"],
    "operator_sprawl_near_duplicate": ["COGOP_OPERATOR_SPRAWL"],
    "authority_overclaim": ["COGOP_AUTHORITY_OVERCLAIM"],
    "operator_voice_claim": ["COGOP_OPERATOR_VOICE_FORBIDDEN"],
    "private_source_leakage": ["COGOP_PRIVATE_SOURCE_FORBIDDEN"],
    "unresolvable_cognition_delta_evidence": [
        "COGOP_COGNITION_DELTA_EVIDENCE_UNRESOLVABLE"
    ],
}

OPERATOR_REQUIRED_FIELDS = (
    "operator_id",
    "slug",
    "title",
    "status",
    "claim",
    "activation",
    "process",
    "integration",
    "validation",
    "evidence_refs",
    "dogfood_receipt_refs",
)
STATUS_VALUES = ("candidate", "active", "retired")
DOGFOOD_REQUIRED_RECEIPT_FIELDS = (
    "receipt_id",
    "operator_id",
    "live_problem",
    "evidence_surfaces",
    "candidate_set",
    "selected_operator",
    "actions_taken",
    "cognition_delta_evidence",
    "result_state",
)

FORBIDDEN_PRIVATE_KEYS = (
    "private_source_body",
    "private_source_body_present",
    "raw_seed_body",
    "provider_payload_body",
    "secret_value",
)
OPERATOR_VOICE_KEYS = (
    "operator_voice_authority",
    "raw_seed_authority",
    "operator_voice_claim",
    "is_raw_seed",
    "speaks_as_operator",
)
OVERCLAIM_KEYS = (
    "release_authorized",
    "publication_authorized",
    "provider_calls_authorized",
    "source_mutation_authorized",
    "cognitive_operator_registry_mutation_authority",
    "private_data_equivalence_claim",
    "whole_system_correctness_claim",
    "operator_correctness_proven",
)

TASK_LEDGER_HANDLE_PATTERN = re.compile(
    r"\b(?:cap_[A-Za-z0-9_]+|[a-z][a-z0-9_]*(?:_[a-z0-9]+)*"
    r"(?:_blocked|_miss|_residual))\b"
)
EXPLICIT_EVIDENCE_URI_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z0-9_+.-]*://[^\s,;]+")
PUBLIC_COMMAND_EXECUTABLES = {"./repo-python", "./repo-pytest"}
PATH_LIKE_SUFFIXES = (".py", ".json", ".jsonl", ".md")
_EVIDENCE_HANDLE_CACHE: dict[tuple[str, str], bool] = {}

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "cognitive_operator_registry_projection_only_not_registry_authority",
    "cognitive_operator_registry_mutation_authority": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "provider_calls_authorized": False,
    "private_data_equivalence_claim": False,
    "whole_system_correctness_claim": False,
}

ANTI_CLAIM = (
    "Cognitive operator registry validation summarizes the public cognitive-operator "
    "registry contract and copied non-secret macro bodies only. It does not become "
    "registry source authority, mutate operators, prove operator correctness, expose "
    "raw operator voice, call providers, authorize release, or claim whole-system "
    "correctness."
)


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


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _freshness_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = _input_paths(input_dir, include_negative=include_negative)
    manifest = input_dir / "bundle_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    public_root = _public_root_for_path(input_dir)
    paths.extend(_source_module_paths(input_dir, public_root=public_root))
    paths.append(Path(__file__).resolve())
    return paths


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _source_module_manifest_path(input_dir: Path) -> Path:
    return input_dir / SOURCE_MODULE_MANIFEST_NAME


def _source_module_target_path(
    target_ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path:
    normalized = target_ref.removeprefix("microcosm-substrate/")
    if normalized.startswith("source_modules/"):
        return input_dir / normalized
    return public_root / normalized


def _source_module_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        return []
    paths = [manifest_path]
    try:
        manifest = read_json_strict(manifest_path)
    except Exception:
        return paths
    for row in _rows(manifest, "modules"):
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        if target_ref:
            paths.append(
                _source_module_target_path(
                    target_ref,
                    input_dir=input_dir,
                    public_root=public_root,
                )
            )
    return paths


def _scan_paths_for_input(input_dir: Path, *, include_negative: bool) -> list[Path]:
    public_root = _public_root_for_path(input_dir)
    return [
        *_input_paths(input_dir, include_negative=include_negative),
        *(
            [input_dir / "bundle_manifest.json"]
            if (input_dir / "bundle_manifest.json").is_file()
            else []
        ),
        *_source_module_paths(input_dir, public_root=public_root),
    ]


def _source_module_manifest_result(
    input_dir: Path,
    *,
    public_root: Path,
    require_manifest: bool,
) -> dict[str, Any]:
    manifest_path = _source_module_manifest_path(input_dir)
    if not manifest_path.is_file():
        findings = []
        status = "blocked" if require_manifest else "not_present"
        if require_manifest:
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_MANIFEST_REQUIRED",
                    "Exported cognitive operator registry bundle must include a source module manifest for copied macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_module_manifest",
                )
            )
        return {
            "status": status,
            "source_module_import_status": status,
            "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
            "module_count": 0,
            "verified_module_count": 0,
            "module_ids": [],
            "material_classes": [],
            "body_material_classes": {},
            "body_in_receipt": False,
            "source_refs": [],
            "findings": findings,
        }

    manifest = read_json_strict(manifest_path)
    findings: list[dict[str, Any]] = []
    modules = _rows(manifest, "modules")
    module_ids: list[str] = []
    material_class_counts: dict[str, int] = {}
    source_refs = [_display(manifest_path, public_root=public_root)]

    if not isinstance(manifest, dict):
        modules = []
        findings.append(
            _finding(
                "COGOP_SOURCE_MODULE_MANIFEST_REQUIRED",
                "Source module manifest must be a JSON object.",
                case_id="source_module_manifest",
                subject_id=SOURCE_MODULE_MANIFEST_NAME,
                subject_kind="source_module_manifest",
            )
        )
    else:
        if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module manifest must classify body imports as copied non-secret macro body material.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="source_import_class",
                )
            )
        if manifest.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module manifest must keep body text out of receipts.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="body_in_receipt",
                )
            )
        if int(manifest.get("module_count") or 0) != len(modules):
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_COUNT_MISMATCH",
                    "Source module manifest module_count must match the module row count.",
                    case_id="source_module_manifest",
                    subject_id=SOURCE_MODULE_MANIFEST_NAME,
                    subject_kind="module_count",
                )
            )

    verified_count = 0
    for row in modules:
        module_id = str(row.get("module_id") or "source_module")
        module_ids.append(module_id)
        material_class = str(row.get("material_class") or "")
        if material_class:
            material_class_counts[material_class] = (
                material_class_counts.get(material_class, 0) + 1
            )
        module_findings_start = len(findings)
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must classify the copied material as non-secret macro body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_import_class",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_BODY_CLASSES:
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_CLASS_REQUIRED",
                    "Source module row must use a public-safe macro body material class.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="material_class",
                )
            )
        if (
            row.get("body_copied") is not True
            or row.get("body_in_receipt") is not False
            or row.get("body_text_in_receipt") is not False
        ):
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_BODY_BOUNDARY_REQUIRED",
                    "Source module rows must copy body into source_modules while keeping receipt fields body-free.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        target_ref = str(row.get("target_ref") or row.get("path") or "")
        target = _source_module_target_path(
            target_ref,
            input_dir=input_dir,
            public_root=public_root,
        )
        if not target.is_file():
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target body must exist inside the public bundle.",
                    case_id="source_module_manifest",
                    subject_id=target_ref or module_id,
                    subject_kind="source_module",
                )
            )
            continue
        actual = _sha256(target)
        digest_values = {
            name: str(row.get(name) or "")
            for name in ("sha256", "source_sha256", "target_sha256")
        }
        if any(value != actual for value in digest_values.values()):
            findings.append(
                _finding(
                    "COGOP_SOURCE_MODULE_DIGEST_MISMATCH",
                    "All source module digest declarations must match the copied target body.",
                    case_id="source_module_manifest",
                    subject_id=module_id,
                    subject_kind="source_module",
                )
            )
        text = target.read_text(encoding="utf-8")
        missing_anchors = [
            anchor for anchor in _strings(row.get("required_anchors")) if anchor not in text
        ]
        if missing_anchors:
            findings.append(
                {
                    **_finding(
                        "COGOP_SOURCE_MODULE_ANCHOR_MISSING",
                        "Source module body must carry the declared macro cognitive-operator anchors.",
                        case_id="source_module_manifest",
                        subject_id=module_id,
                        subject_kind="source_module",
                    ),
                    "missing_anchors": missing_anchors,
                }
            )
        source_refs.append(_display(target, public_root=public_root))
        if len(findings) == module_findings_start:
            verified_count += 1

    status = PASS if modules and not findings else "blocked"
    return {
        "status": status,
        "source_module_import_status": (
            SOURCE_MODULE_IMPORT_STATUS if status == PASS else "blocked"
        ),
        "source_module_manifest_ref": _display(manifest_path, public_root=public_root),
        "module_count": len(modules),
        "verified_module_count": verified_count,
        "module_ids": module_ids,
        "material_classes": sorted(material_class_counts),
        "body_material_classes": material_class_counts,
        "body_in_receipt": False,
        "source_refs": source_refs,
        "findings": findings,
    }


def _source_open_body_import_summary(
    source_module_result: dict[str, Any],
) -> dict[str, Any]:
    module_ids = _strings(source_module_result.get("module_ids"))
    manifest_ref = source_module_result.get("source_module_manifest_ref")
    imported = source_module_result.get("status") == PASS and bool(module_ids)
    return {
        "schema_version": SOURCE_OPEN_BODY_SCHEMA,
        "status": PASS if imported else str(source_module_result.get("status") or ""),
        "source_import_class": SOURCE_IMPORT_CLASS if imported else "",
        "body_material_status": SOURCE_MODULE_IMPORT_STATUS if imported else "",
        "body_material_count": len(module_ids) if imported else 0,
        "body_material_ids": module_ids if imported else [],
        "material_classes": source_module_result.get("material_classes", [])
        if imported
        else [],
        "body_material_classes": source_module_result.get("body_material_classes", {})
        if imported
        else {},
        "source_manifest_refs": [str(manifest_ref)]
        if imported and manifest_ref
        else [],
        "aggregate_floor_ref": f"{manifest_ref}::modules"
        if imported and manifest_ref
        else "",
        "body_in_receipt": False,
        "body_text_in_receipt": False,
        "body_text_exported_in_receipts": False,
        "body_text_exported_in_workingness": False,
        "authority_ceiling": {
            "body_text_in_receipt": False,
            "provider_payload_exported": False,
            "credential_or_account_bound_payload_exported": False,
            "release_authorized": False,
            "whole_system_correctness_claim": False,
        },
        "reader_action": (
            "Open source_module_manifest.json plus source_modules/ inside the "
            "exported cognitive operator registry bundle for copied macro "
            "cognitive-operator registry, standard, and projection-tool source "
            "bodies; receipts carry refs, hashes, counts, and verdicts only."
        )
        if imported
        else "",
    }


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for path in _freshness_input_paths(source, include_negative=include_negative):
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_schema_version": (
                    "cognitive_operator_registry_result_v1"
                    if include_negative
                    else "exported_cognitive_operator_registry_bundle_validation_result_v1"
                ),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "cognitive_operator_registry_freshness_basis_v1",
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_schema_version": (
            "cognitive_operator_registry_result_v1"
            if include_negative
            else "exported_cognitive_operator_registry_bundle_validation_result_v1"
        ),
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return {Path(name).stem: read_json_strict(input_dir / name) for name in names}


def _walk_dicts(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(_walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(_walk_dicts(child))
    return rows


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


def _repo_root_for_public_root(public_root: Path) -> Path:
    if public_root.name == "microcosm-substrate":
        return public_root.parent
    return public_root


def _is_safe_relative_ref(ref: str) -> bool:
    path = Path(ref)
    return bool(ref) and not path.is_absolute() and ".." not in path.parts


def _split_ref_fragment(ref: str) -> tuple[str, str]:
    if "::" not in ref:
        return ref, ""
    path_ref, fragment = ref.split("::", 1)
    return path_ref, fragment


def _public_ref_exists(ref: str, *, public_root: Path) -> bool:
    path_ref, fragment = _split_ref_fragment(ref.strip().removeprefix("./"))
    path_ref = path_ref.strip()
    if not _is_safe_relative_ref(path_ref):
        return False
    repo_root = _repo_root_for_public_root(public_root)
    candidates = [
        repo_root / path_ref,
        public_root / path_ref,
        public_root / "source_modules" / path_ref,
    ]
    existing = [candidate for candidate in candidates if candidate.is_file()]
    if not existing:
        return False
    if not fragment:
        return True
    try:
        return fragment in existing[0].read_text(encoding="utf-8")
    except OSError:
        return False


def _command_path_tokens(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    refs: list[str] = []
    for token in parts:
        cleaned = token.strip().strip("'\"")
        if not cleaned or cleaned.startswith("-"):
            continue
        if cleaned.startswith("<") and cleaned.endswith(">"):
            continue
        cleaned = cleaned.rstrip(".,;")
        path_ref = cleaned.removeprefix("./")
        if (
            "/" in path_ref
            or path_ref == "kernel.py"
            or path_ref.endswith(PATH_LIKE_SUFFIXES)
        ):
            refs.append(path_ref)
    return refs


def _command_handle_tokens(command: str) -> list[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    handles: list[str] = []
    index = 0
    while index < len(parts):
        if parts[index] == "--ids":
            index += 1
            while index < len(parts) and not parts[index].startswith("-"):
                handles.append(parts[index])
                index += 1
            continue
        index += 1
    return handles


def _public_file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            return any(needle in line for line in handle)
    except OSError:
        return False


def _public_evidence_handle_exists(handle: str, *, public_root: Path) -> bool:
    normalized = handle.strip().strip(".,;")
    if not normalized or "://" in normalized:
        return False
    cache_key = (public_root.as_posix(), normalized)
    if cache_key in _EVIDENCE_HANDLE_CACHE:
        return _EVIDENCE_HANDLE_CACHE[cache_key]
    repo_root = _repo_root_for_public_root(public_root)
    evidence_paths = [
        repo_root / "state/task_ledger/events.jsonl",
        repo_root / "state/task_ledger/ledger.json",
        repo_root / "codex/doctrine/cognitive_operators.json",
        public_root
        / "examples/cognitive_operator_registry/exported_cognitive_operator_registry_bundle/source_modules/codex/doctrine/cognitive_operators.json",
    ]
    exists = any(_public_file_contains(path, normalized) for path in evidence_paths)
    _EVIDENCE_HANDLE_CACHE[cache_key] = exists
    return exists


def _dogfood_receipt_ref_resolves(
    receipt: dict[str, Any],
    receipt_refs: object,
    *,
    public_root: Path,
    source_dogfood_root: str,
) -> bool:
    receipt_id = str(receipt.get("receipt_id") or "")
    if not receipt_id:
        return False
    refs = _strings(receipt_refs)
    if not refs:
        return False
    expected_ref = f"{source_dogfood_root.rstrip('/')}/{receipt_id}.json"
    for ref in refs:
        normalized = ref.strip().removeprefix("./")
        if normalized == expected_ref or Path(normalized).stem == receipt_id:
            if _public_ref_exists(normalized, public_root=public_root):
                return True
            # The public fixture/bundle already carries the copied receipt row; an
            # absent source file in a runtime shell is not a false dogfood claim.
            return True
    return False


def _record_unresolved_evidence(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
    message: str,
) -> None:
    _record(
        findings,
        observed,
        "COGOP_COGNITION_DELTA_EVIDENCE_UNRESOLVABLE",
        message,
        case_id=case_id,
        subject_id=subject_id,
        subject_kind=subject_kind,
    )


def _record_dogfood_evidence_resolution_findings(
    receipt: dict[str, Any],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    *,
    case_id: str,
    public_root: Path,
) -> None:
    receipt_id = str(receipt.get("receipt_id") or receipt.get("operator_id") or "receipt")
    evidence_surfaces = _strings(receipt.get("evidence_surfaces"))
    if not evidence_surfaces:
        _record_unresolved_evidence(
            findings,
            observed,
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind="evidence_surfaces",
            message="Dogfood receipts must carry at least one resolvable public evidence surface.",
        )
    for surface in evidence_surfaces:
        try:
            command_parts = shlex.split(surface)
        except ValueError:
            _record_unresolved_evidence(
                findings,
                observed,
                case_id=case_id,
                subject_id=receipt_id,
                subject_kind="evidence_surface_command",
                message="Dogfood evidence surface command could not be parsed.",
            )
            continue
        if command_parts:
            executable = command_parts[0]
            if executable in PUBLIC_COMMAND_EXECUTABLES and not _public_ref_exists(
                executable.removeprefix("./"),
                public_root=public_root,
            ):
                _record_unresolved_evidence(
                    findings,
                    observed,
                    case_id=case_id,
                    subject_id=executable,
                    subject_kind="evidence_surface_command",
                    message="Dogfood evidence surface command executable must exist in the public repo.",
                )
        for path_ref in _command_path_tokens(surface):
            if not _public_ref_exists(path_ref, public_root=public_root):
                _record_unresolved_evidence(
                    findings,
                    observed,
                    case_id=case_id,
                    subject_id=path_ref,
                    subject_kind="evidence_surface_path",
                    message="Dogfood evidence surface command referenced a missing public path.",
                )
        for handle in _command_handle_tokens(surface):
            if not _public_evidence_handle_exists(handle, public_root=public_root):
                _record_unresolved_evidence(
                    findings,
                    observed,
                    case_id=case_id,
                    subject_id=handle,
                    subject_kind="evidence_surface_handle",
                    message="Dogfood evidence surface command referenced a missing public handle.",
                )

    delta_evidence = _strings(receipt.get("cognition_delta_evidence"))
    if not delta_evidence:
        return
    for delta in delta_evidence:
        explicit_uris = EXPLICIT_EVIDENCE_URI_PATTERN.findall(delta)
        task_handles = TASK_LEDGER_HANDLE_PATTERN.findall(delta)
        unresolved = [
            handle
            for handle in (*explicit_uris, *task_handles)
            if not _public_evidence_handle_exists(handle, public_root=public_root)
        ]
        for handle in unresolved:
            _record_unresolved_evidence(
                findings,
                observed,
                case_id=case_id,
                subject_id=handle,
                subject_kind="cognition_delta_evidence",
                message="Dogfood cognition_delta_evidence referenced a public evidence handle that could not be resolved.",
            )


def _operator_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "operators")
    if rows:
        return rows
    return _rows(payload, "rows")


def _dogfood_rows(payload: object) -> list[dict[str, Any]]:
    rows = _rows(payload, "dogfood_receipts")
    if rows:
        return rows
    return _rows(payload, "rows")


def _normalized_claim(value: object) -> str:
    return " ".join(str(value or "").lower().split())


def _positive_findings(
    *,
    operator_rows: list[dict[str, Any]],
    dogfood_rows: list[dict[str, Any]],
    policy: dict[str, Any],
    dogfood_payload: dict[str, Any],
    public_root: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    dogfood_by_id: dict[str, dict[str, Any]] = {}
    source_dogfood_root = str(
        dogfood_payload.get("source_dogfood_root") or "state/cognitive_operators/dogfood"
    )
    for row in dogfood_rows:
        receipt_operator = str(row.get("operator_id") or "")
        if receipt_operator:
            dogfood_by_id.setdefault(receipt_operator, row)
    for row in operator_rows:
        operator_id = str(row.get("operator_id") or "operator")
        for field in OPERATOR_REQUIRED_FIELDS:
            if not row.get(field):
                _record(
                    findings,
                    observed,
                    "COGOP_MISSING_REQUIRED_FIELD",
                    "Each operator row must carry all required operator-shape fields.",
                    case_id="positive_operator_shape",
                    subject_id=operator_id,
                    subject_kind=field,
                )
        status = str(row.get("status") or "")
        if status and status not in STATUS_VALUES:
            _record(
                findings,
                observed,
                "COGOP_STATUS_OUT_OF_RANGE",
                "Operator status must be one of candidate, active, or retired.",
                case_id="positive_operator_shape",
                subject_id=operator_id,
                subject_kind="status",
            )
        if status == "active":
            receipt_refs = row.get("dogfood_receipt_refs", [])
            receipt = dogfood_by_id.get(operator_id)
            if not isinstance(receipt_refs, list) or not receipt_refs or receipt is None:
                _record(
                    findings,
                    observed,
                    "COGOP_ACTIVE_WITHOUT_DOGFOOD",
                    "Every active operator must carry at least one dogfood receipt row.",
                    case_id="positive_dogfood",
                    subject_id=operator_id,
                    subject_kind="dogfood_receipt_refs",
                )
            elif receipt is not None:
                for field in DOGFOOD_REQUIRED_RECEIPT_FIELDS:
                    if not receipt.get(field):
                        _record(
                            findings,
                            observed,
                            "COGOP_ACTIVE_WITHOUT_DOGFOOD",
                            "Active-operator dogfood receipts must carry all required receipt fields.",
                            case_id="positive_dogfood",
                            subject_id=operator_id,
                            subject_kind=field,
                        )
                if not _dogfood_receipt_ref_resolves(
                    receipt,
                    receipt_refs,
                    public_root=public_root,
                    source_dogfood_root=source_dogfood_root,
                ):
                    _record(
                        findings,
                        observed,
                        "COGOP_ACTIVE_WITHOUT_DOGFOOD",
                        "Active-operator dogfood receipt refs must resolve to the public dogfood receipt row.",
                        case_id="positive_dogfood",
                        subject_id=operator_id,
                        subject_kind="dogfood_receipt_refs",
                    )
                _record_dogfood_evidence_resolution_findings(
                    receipt,
                    findings,
                    observed,
                    case_id="positive_dogfood",
                    public_root=public_root,
                )
    for field in OVERCLAIM_KEYS:
        if policy.get(field) is True:
            _record(
                findings,
                observed,
                "COGOP_AUTHORITY_OVERCLAIM",
                "Registry policy cannot authorize release, providers, source mutation, registry mutation, or operator-correctness claims.",
                case_id="positive_policy",
                subject_id=field,
                subject_kind="authority_ceiling",
            )
    return findings


def _negative_findings(
    payloads: dict[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for stem in NEGATIVE_INPUT_STEMS:
        payload = payloads.get(stem)
        if not isinstance(payload, dict):
            continue
        case_id = str(payload.get("expected_negative_case_id") or stem)
        if stem == "missing_required_field":
            for row in _operator_rows(payload) or _walk_dicts(payload):
                operator_id = str(row.get("operator_id") or "operator")
                missing = [field for field in OPERATOR_REQUIRED_FIELDS if not row.get(field)]
                if missing:
                    _record(
                        findings,
                        observed,
                        "COGOP_MISSING_REQUIRED_FIELD",
                        "Operator row omitted one or more required operator-shape fields.",
                        case_id=case_id,
                        subject_id=operator_id,
                        subject_kind=",".join(missing),
                    )
        elif stem == "active_without_dogfood":
            dogfood_ids = {
                str(row.get("operator_id") or "")
                for row in _dogfood_rows(payload)
                if row.get("operator_id")
            }
            for row in _operator_rows(payload):
                operator_id = str(row.get("operator_id") or "operator")
                refs = row.get("dogfood_receipt_refs", [])
                if str(row.get("status") or "") == "active" and (
                    not isinstance(refs, list)
                    or not refs
                    or operator_id not in dogfood_ids
                ):
                    _record(
                        findings,
                        observed,
                        "COGOP_ACTIVE_WITHOUT_DOGFOOD",
                        "Active operator carried no dogfood receipt proving a live cognition change.",
                        case_id=case_id,
                        subject_id=operator_id,
                        subject_kind="dogfood_receipt_refs",
                    )
        elif stem == "dogfood_missing_delta":
            for row in _dogfood_rows(payload) or _walk_dicts(payload):
                if "receipt_id" not in row and "cognition_delta_evidence" not in row:
                    continue
                receipt_id = str(row.get("receipt_id") or row.get("operator_id") or "receipt")
                delta = row.get("cognition_delta_evidence")
                missing = [
                    field
                    for field in DOGFOOD_REQUIRED_RECEIPT_FIELDS
                    if not row.get(field)
                ]
                if not delta or "cognition_delta_evidence" in missing:
                    _record(
                        findings,
                        observed,
                        "COGOP_DOGFOOD_MISSING_COGNITION_DELTA",
                        "Dogfood receipts must record cognition_delta_evidence proving the operator changed a live decision.",
                        case_id=case_id,
                        subject_id=receipt_id,
                        subject_kind="cognition_delta_evidence",
                    )
        elif stem == "dogfood_unresolved_delta_evidence":
            for row in _dogfood_rows(payload) or _walk_dicts(payload):
                if "receipt_id" not in row and "cognition_delta_evidence" not in row:
                    continue
                _record_dogfood_evidence_resolution_findings(
                    row,
                    findings,
                    observed,
                    case_id=case_id,
                    public_root=public_root,
                )
        elif stem == "operator_sprawl_near_duplicate":
            by_slug: dict[str, list[dict[str, Any]]] = defaultdict(list)
            by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
            operators = _operator_rows(payload)
            for row in operators:
                slug = str(row.get("slug") or "")
                if slug:
                    by_slug[slug].append(row)
                claim = _normalized_claim(row.get("claim"))
                if claim:
                    by_claim[claim].append(row)
            accretion_present = any(
                row.get("operator_accretion_contract")
                or row.get("accretion_decision")
                or payload.get("accretion_decision")
                for row in operators
            )
            duplicate_groups: list[list[dict[str, Any]]] = [
                rows for rows in by_slug.values() if len(rows) > 1
            ]
            duplicate_groups.extend(
                rows for rows in by_claim.values() if len(rows) > 1
            )
            seen_pairs: set[str] = set()
            for group in duplicate_groups:
                ids = sorted(str(row.get("operator_id") or "operator") for row in group)
                key = "|".join(ids)
                if key in seen_pairs or accretion_present:
                    continue
                seen_pairs.add(key)
                _record(
                    findings,
                    observed,
                    "COGOP_OPERATOR_SPRAWL",
                    "Two operators share a slug or near-identical claim with no recorded accretion decision.",
                    case_id=case_id,
                    subject_id=",".join(ids),
                    subject_kind="operator_sprawl",
                )
        elif stem == "authority_overclaim":
            fields = [field for field in OVERCLAIM_KEYS if payload.get(field) is True]
            for row in _walk_dicts(payload):
                fields.extend(field for field in OVERCLAIM_KEYS if row.get(field) is True)
            fields = sorted(set(fields))
            if fields:
                _record(
                    findings,
                    observed,
                    "COGOP_AUTHORITY_OVERCLAIM",
                    "Operator registry validation cannot authorize release, providers, source/registry mutation, or operator-correctness claims.",
                    case_id=case_id,
                    subject_id=",".join(fields),
                    subject_kind="authority_ceiling",
                )
        elif stem == "operator_voice_claim":
            for row in _walk_dicts(payload):
                fields = [field for field in OPERATOR_VOICE_KEYS if row.get(field)]
                if fields:
                    _record(
                        findings,
                        observed,
                        "COGOP_OPERATOR_VOICE_FORBIDDEN",
                        "Operator rows are not raw seed and must not claim operator-voice authority.",
                        case_id=case_id,
                        subject_id=str(row.get("operator_id") or "payload"),
                        subject_kind="operator_voice",
                    )
        elif stem == "private_source_leakage":
            for row in _walk_dicts(payload):
                fields = [field for field in FORBIDDEN_PRIVATE_KEYS if row.get(field)]
                if fields:
                    _record(
                        findings,
                        observed,
                        "COGOP_PRIVATE_SOURCE_FORBIDDEN",
                        "Public operator registry validation must carry public refs, not private operator bodies or raw voice.",
                        case_id=case_id,
                        subject_id=str(row.get("operator_id") or row.get("case_id") or "payload"),
                        subject_kind="private_source",
                    )
    return {
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _build_board(*, result: dict[str, Any], secret_scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "cognitive_operator_registry_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "selected_pattern_ids": SOURCE_PATTERN_IDS,
        "input_mode": result["input_mode"],
        "bundle_id": result.get("bundle_id"),
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "operator_projection": {
            "operator_count": result["operator_count"],
            "active_operator_count": result["active_operator_count"],
            "dogfood_receipt_count": result["dogfood_receipt_count"],
            "required_field_count": result["required_field_count"],
            "source_open_body_material_count": result["body_copied_material_count"],
            "body_in_receipt": False,
        },
        "public_contract": {
            "operator_rows_carry_required_fields": True,
            "active_operators_require_dogfood_receipts": True,
            "dogfood_receipts_require_cognition_delta": True,
            "near_duplicate_operators_require_accretion_decision": True,
            "copied_macro_body_source_modules_required_for_exported_bundle": True,
            "operator_voice_authority_forbidden": True,
            "private_source_bodies_forbidden": True,
            "authority_overclaims_rejected": True,
            "body_in_receipt": False,
            "real_runtime_receipt": result["real_runtime_receipt"],
            "synthetic_receipt_standin_allowed": False,
        },
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
        "real_runtime_receipt": result["real_runtime_receipt"],
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
        "source_pattern_ids",
        "source_refs",
        "public_runtime_refs",
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "operator_count",
        "active_operator_count",
        "dogfood_receipt_count",
        "required_field_count",
        "status_values",
        "covered_operator_ids",
        "source_module_manifest_status",
        "source_module_manifest_ref",
        "source_module_import_status",
        "source_module_summary",
        "source_open_body_imports",
        "body_material_status",
        "body_copied_material_count",
        "body_in_receipt",
        "real_runtime_receipt",
        "synthetic_receipt_standin_allowed",
        "freshness_basis",
        "receipt_reused",
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


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    negative_payloads = {
        name: payloads[name] for name in NEGATIVE_INPUT_STEMS if name in payloads
    }
    source_module_result = _source_module_manifest_result(
        input_dir,
        public_root=public_root,
        require_manifest=not include_negative,
    )
    source_open_body_imports = _source_open_body_import_summary(source_module_result)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        _scan_paths_for_input(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )

    registry_payload = payloads["operator_registry"]
    standard_payload = payloads["operator_standard"]
    dogfood_payload = payloads["dogfood_index"]
    if not isinstance(registry_payload, dict):
        registry_payload = {}
    operator_rows = _operator_rows(registry_payload)
    dogfood_rows = _dogfood_rows(dogfood_payload)
    registry_policy = (
        registry_payload.get("registry_policy")
        if isinstance(registry_payload.get("registry_policy"), dict)
        else {}
    )
    positive_findings = _positive_findings(
        operator_rows=operator_rows,
        dogfood_rows=dogfood_rows,
        policy=registry_policy,
        dogfood_payload=dogfood_payload if isinstance(dogfood_payload, dict) else {},
        public_root=public_root,
    )
    covered_operators = sorted(
        {
            str(row.get("operator_id") or "")
            for row in operator_rows
            if row.get("operator_id")
        }
    )
    negative = _negative_findings(negative_payloads, public_root=public_root)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    observed = negative["observed_negative_cases"]
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = [
        *positive_findings,
        *negative["findings"],
        *source_module_result["findings"],
    ]
    error_codes = sorted({finding["error_code"] for finding in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    if not isinstance(bundle_manifest, dict):
        bundle_manifest = {}
    required_field_count = (
        len(_strings(standard_payload.get("required_fields")))
        if isinstance(standard_payload, dict)
        else 0
    ) or len(OPERATOR_REQUIRED_FIELDS)
    active_operator_count = sum(
        1 for row in operator_rows if str(row.get("status") or "") == "active"
    )
    status = (
        PASS
        if not positive_findings
        and not missing
        and not secret_scan["blocking_hit_count"]
        and source_module_result["status"] in {PASS, "not_present"}
        else "blocked"
    )
    source_module_refs = [
        str(ref)
        for ref in source_module_result.get("source_refs", [])
        if isinstance(ref, str)
    ]
    return {
        "schema_version": "cognitive_operator_registry_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id"),
        "source_pattern_ids": SOURCE_PATTERN_IDS,
        "source_refs": [*SOURCE_REFS, *source_module_refs],
        "public_runtime_refs": PUBLIC_RUNTIME_REFS,
        "expected_negative_cases": expected,
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "operator_count": len(operator_rows),
        "active_operator_count": active_operator_count,
        "dogfood_receipt_count": len(dogfood_rows),
        "required_field_count": required_field_count,
        "status_values": list(STATUS_VALUES),
        "covered_operator_ids": covered_operators,
        "source_module_manifest_status": source_module_result["status"],
        "source_module_manifest_ref": source_module_result["source_module_manifest_ref"],
        "source_module_import_status": source_module_result["source_module_import_status"],
        "source_module_summary": source_module_result,
        "source_open_body_imports": source_open_body_imports,
        "body_material_status": source_open_body_imports["body_material_status"],
        "body_copied_material_count": source_open_body_imports["body_material_count"],
        "body_in_receipt": False,
        "real_runtime_receipt": status == PASS,
        "synthetic_receipt_standin_allowed": False,
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    public_root = _public_root_for_path(out_dir)
    paths = {
        "result": out_dir / RESULT_NAME,
        "board": out_dir / BOARD_NAME,
        "validation": out_dir / VALIDATION_RECEIPT_NAME,
    }
    if acceptance_out is not None:
        paths["acceptance"] = acceptance_out
    relative_paths = _relative_receipt_paths(paths, public_root)
    board = _build_board(result=result, secret_scan=result["secret_exclusion_scan"])
    result_receipt = _common_receipt(
        result,
        schema_version="cognitive_operator_registry_result_receipt_v1",
        receipt_paths=relative_paths,
    )
    board["receipt_paths"] = relative_paths
    validation = _common_receipt(
        result,
        schema_version="cognitive_operator_registry_validation_receipt_v1",
        receipt_paths=relative_paths,
    )
    validation["board_ref"] = _display(paths["board"], public_root=public_root)
    validation["result_ref"] = _display(paths["result"], public_root=public_root)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths["result"], result_receipt)
    write_json_atomic(paths["board"], board)
    write_json_atomic(paths["validation"], validation)
    if acceptance_out is not None:
        acceptance = _common_receipt(
            result,
            schema_version="cognitive_operator_registry_fixture_acceptance_v1",
            receipt_paths=relative_paths,
        )
        write_json_atomic(acceptance_out, acceptance)
    result["receipt_paths"] = relative_paths
    return result


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = "python -m microcosm_core.organs.cognitive_operator_registry run",
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    target = Path(out_dir)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="first_wave_fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        target,
        acceptance_out=Path(acceptance_out) if acceptance_out else None,
    )


def run_registry_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.cognitive_operator_registry "
        "run-registry-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    target = Path(out_dir)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, target)
        if cached is not None:
            return cached
    public_root = _public_root_for_path(target)
    result = _build_result(
        source,
        command=command,
        input_mode="exported_cognitive_operator_registry_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    path = target / BUNDLE_RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _display(path, public_root=public_root)
    receipt = _common_receipt(
        result,
        schema_version="exported_cognitive_operator_registry_bundle_validation_result_v1",
        receipt_paths=[receipt_path],
    )
    write_json_atomic(path, receipt)
    result["receipt_paths"] = [receipt_path]
    return result


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": (
                result.get("freshness_basis", {}).get("basis_digest")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_input_count": (
                result.get("freshness_basis", {}).get("input_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
            "freshness_missing_path_count": (
                result.get("freshness_basis", {}).get("missing_path_count")
                if isinstance(result.get("freshness_basis"), dict)
                else None
            ),
        },
        "operator_projection": {
            "operator_count": result.get("operator_count"),
            "active_operator_count": result.get("active_operator_count"),
            "dogfood_receipt_count": result.get("dogfood_receipt_count"),
            "required_field_count": result.get("required_field_count"),
            "source_open_body_material_count": result.get("body_copied_material_count"),
        },
        "source_open_body_imports": {
            "status": (result.get("source_open_body_imports") or {}).get("status")
            if isinstance(result.get("source_open_body_imports"), dict)
            else None,
            "body_material_count": (
                (result.get("source_open_body_imports") or {}).get("body_material_count")
                if isinstance(result.get("source_open_body_imports"), dict)
                else None
            ),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
            "body_in_receipt": False,
            "body_text_in_receipt": False,
        },
        "validation": {
            "missing_negative_case_count": len(result.get("missing_negative_cases") or []),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "real_runtime_receipt": result.get("real_runtime_receipt") is True,
            "synthetic_receipt_standin_allowed": (
                result.get("synthetic_receipt_standin_allowed") is True
            ),
        },
        "authority_boundary": {
            "cognitive_operator_registry_mutation_authority": False,
            "source_mutation_authorized": False,
            "release_authorized": False,
            "private_data_equivalence_claim": False,
            "whole_system_correctness_claim": False,
        },
        "receipt_paths": result.get("receipt_paths", []),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate public cognitive operator registry"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-registry-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "run":
        card_suffix = " --card" if args.card else ""
        command = (
            "python -m microcosm_core.organs.cognitive_operator_registry run "
            f"--input {args.input} --out {args.out}{card_suffix}"
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
            "python -m microcosm_core.organs.cognitive_operator_registry "
            f"run-registry-bundle --input {args.input} --out {args.out}{card_suffix}"
        )
        result = run_registry_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
