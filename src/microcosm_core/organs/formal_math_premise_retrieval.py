from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "formal_math_premise_retrieval"
FIXTURE_ID = "first_wave.formal_math_premise_retrieval"
VALIDATOR_ID = "validator.microcosm.organs.formal_math_premise_retrieval"

RESULT_NAME = "formal_math_premise_retrieval_result.json"
BOARD_NAME = "premise_retrieval_board.json"
VALIDATION_RECEIPT_NAME = "formal_math_premise_retrieval_validation_receipt.json"
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "formal_math_premise_retrieval_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_premise_retrieval_bundle_validation_result.json"

INPUT_NAMES = (
    "projection_protocol.json",
    "premise_index.json",
    "retrieval_queries.json",
    "context_recipes.json",
    "strategy_cases.json",
)
OPTIONAL_BUNDLE_SCAN_NAMES = (
    "bundle_manifest.json",
    "source_module_manifest.json",
)
NEGATIVE_INPUT_NAMES = (
    "premise_index_with_proof_body.json",
    "query_with_oracle_ids.json",
    "test_split_tuning_attempt.json",
    "context_recipe_budget_overflow.json",
    "unknown_strategy_id.json",
)

EXPECTED_NEGATIVE_CASES = {
    "premise_index_proof_body_forbidden": ["FORMAL_PREMISE_PROOF_BODY_FORBIDDEN"],
    "query_oracle_ids_forbidden": ["FORMAL_RETRIEVAL_ORACLE_IDS_FORBIDDEN"],
    "test_split_tuning_attempt": ["FORMAL_RETRIEVAL_TEST_SPLIT_TUNING_FORBIDDEN"],
    "context_recipe_budget_overflow": ["FORMAL_RETRIEVAL_CONTEXT_BUDGET_EXCEEDED"],
    "unknown_strategy_id": ["FORMAL_RETRIEVAL_UNKNOWN_STRATEGY"],
}

FORBIDDEN_BODY_KEYS = (
    "proof_body",
    "ground_truth_proof",
    "provider_output_body",
    "oracle_needed_premise_ids",
    "private_source_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "formal_math_retrieval_metadata_and_public_runtime_eval_only",
    "lean_lake_execution_authorized": False,
    "mathlib_presence_claim_authorized": False,
    "formal_proof_authority": False,
    "provider_calls_authorized": False,
    "proof_bodies_allowed": False,
    "oracle_premise_ids_allowed_in_public_inputs": False,
    "test_split_tuning_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Formal math premise retrieval validates a copied public macro Lean/Std premise "
    "index, term-scoring retrieval, context-budget recipes, and strategy gates. "
    "It does not run Lean or Lake, call providers, expose proof bodies or oracle "
    "premise ids, tune on test split truth, prove theorem correctness, authorize "
    "Mathlib-dependent proofs, or widen the formal_math_lean_proof_witness boundary."
)
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
BODY_MATERIAL_CONTRACT = {
    "status": PASS,
    "body_material_status": BODY_MATERIAL_STATUS,
    "copied_material_required": True,
    "secret_exclusion_scan_field": "secret_exclusion_scan",
    "excluded_body_classes": [
        "proof_body",
        "ground_truth_proof",
        "provider_output_body",
        "oracle_needed_premise_ids",
        "private_source_body",
    ],
}


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    return [input_dir / name for name in names]


def _scan_input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    paths = _input_paths(input_dir, include_negative=include_negative)
    for name in OPTIONAL_BUNDLE_SCAN_NAMES:
        path = input_dir / name
        if path.is_file():
            paths.append(path)
    source_modules = input_dir / "source_modules"
    if source_modules.is_dir():
        paths.extend(sorted(path for path in source_modules.rglob("*") if path.is_file()))
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


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
        "body_material_status": "forbidden_body_excluded",
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


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _tokenize(values: object) -> Counter[str]:
    tokens: Counter[str] = Counter()
    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = [str(item) for item in values]
    else:
        candidates = []
    for value in candidates:
        for token in re.findall(r"[A-Za-z0-9_]+", value.lower()):
            tokens[token] += 1
    return tokens


def _forbidden_keys(row: dict[str, Any]) -> list[str]:
    return sorted(key for key in FORBIDDEN_BODY_KEYS if key in row)


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    public_runtime_refs = _strings(protocol.get("public_runtime_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    copied_material = _rows(protocol, "copied_material")
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    body_copied_material = [
        row
        for row in copied_material
        if row.get("body_copied") is True
        and row.get("source_ref")
        and row.get("source_sha256")
        and _strings(row.get("target_refs"))
        and _strings(row.get("validation_refs"))
    ]
    stale_body_false = [row for row in copied_material if row.get("body_copied") is False]
    if len(source_refs) < 3 or len(public_runtime_refs) < 3 or len(projection_receipts) < 1:
        findings.append(
            _finding(
                "FORMAL_RETRIEVAL_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Formal retrieval import must cite macro source refs, public runtime refs, and projection receipts.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    if not body_copied_material or stale_body_false:
        findings.append(
            _finding(
                "FORMAL_RETRIEVAL_REAL_SUBSTRATE_IMPORT_MISSING",
                "Formal retrieval must copy at least one non-secret macro body with source, target, digest, and validation refs; stale body_copied=false rows are blocked.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in omitted:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "FORMAL_RETRIEVAL_OMISSION_RECEIPT_MISSING",
                    "Omitted macro formal-math material must carry an omission receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS
        if source_refs and public_runtime_refs and projection_receipts and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_runtime_refs": public_runtime_refs,
        "copied_material": copied_material,
        "copied_material_count": len(copied_material),
        "body_copied_material_count": len(body_copied_material),
        "omitted_material_count": len(omitted),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_premise_index(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    premises: list[dict[str, Any]] = []
    for row in _rows(payload, "premises"):
        premise_id = str(row.get("premise_id") or "")
        forbidden = _forbidden_keys(row)
        if forbidden:
            findings.append(
                _finding(
                    "FORMAL_PREMISE_PROOF_BODY_FORBIDDEN",
                    "Premise rows may expose retrieval metadata only, not proof/oracle bodies.",
                    case_id="premise_index_floor",
                    subject_id=premise_id or "premise",
                    subject_kind="premise_index",
                )
            )
        premises.append(
            {
                "premise_id": premise_id,
                "namespace": row.get("namespace"),
                "retrieval_terms": _strings(row.get("retrieval_terms")),
                "allowed_for_split": _strings(row.get("allowed_for_split")),
                "strategy_tags": _strings(row.get("strategy_tags")),
                "source_ref": row.get("source_ref"),
                "body_material_status": "imported_premise_index_row",
            }
        )
    if isinstance(negative_payload, dict):
        for row in _rows(negative_payload, "premises"):
            forbidden = _forbidden_keys(row)
            if forbidden:
                _record(
                    findings,
                    observed,
                    "FORMAL_PREMISE_PROOF_BODY_FORBIDDEN",
                    "Premise index rejected proof/oracle body fields.",
                    case_id=str(
                        row.get("expected_negative_case_id")
                        or "premise_index_proof_body_forbidden"
                    ),
                    subject_id=str(row.get("premise_id") or "premise"),
                    subject_kind="negative_case",
                )
    return {
        "status": PASS if premises and not any(_forbidden_keys(row) for row in _rows(payload, "premises")) else "blocked",
        "premise_count": len(premises),
        "premises": sorted(premises, key=lambda row: row["premise_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_context_recipes(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    recipes: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    for row in _rows(payload, "recipes"):
        recipe_id = str(row.get("recipe_id") or "")
        byte_budget = int(row.get("byte_budget") or 0)
        if byte_budget > 32768 or row.get("proof_bodies_allowed") is True:
            findings.append(
                _finding(
                    "FORMAL_RETRIEVAL_CONTEXT_RECIPE_BLOCKED",
                    "Context recipes must stay within budget and exclude proof bodies.",
                    case_id="context_recipe_floor",
                    subject_id=recipe_id or "recipe",
                    subject_kind="context_recipe",
                )
            )
        recipes.append(
            {
                "recipe_id": recipe_id,
                "byte_budget": byte_budget,
                "deliverable_type": row.get("deliverable_type"),
                "sections": _strings(row.get("sections")),
                "proof_bodies_allowed": row.get("proof_bodies_allowed") is True,
                "provider_calls_authorized": row.get("provider_calls_authorized") is True,
                "body_material_status": "public_context_recipe_no_provider_payload",
            }
        )
    if isinstance(negative_payload, dict):
        for row in _rows(negative_payload, "recipes"):
            if int(row.get("byte_budget") or 0) > 32768:
                _record(
                    findings,
                    observed,
                    "FORMAL_RETRIEVAL_CONTEXT_BUDGET_EXCEEDED",
                    "Context recipe exceeded the retrieval public byte ceiling.",
                    case_id=str(
                        row.get("expected_negative_case_id")
                        or "context_recipe_budget_overflow"
                    ),
                    subject_id=str(row.get("recipe_id") or "recipe"),
                    subject_kind="negative_case",
                )
    return {
        "status": PASS if recipes and not any(row["byte_budget"] > 32768 for row in recipes) else "blocked",
        "recipe_count": len(recipes),
        "recipes": sorted(recipes, key=lambda row: row["recipe_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def validate_strategy_cases(
    payload: object,
    negative_payload: object | None = None,
) -> dict[str, Any]:
    allowed = set(_strings(payload.get("allowed_strategy_ids") if isinstance(payload, dict) else []))
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    cases: list[dict[str, Any]] = []
    for row in _rows(payload, "strategy_cases"):
        strategy_id = str(row.get("strategy_id") or "")
        if strategy_id and strategy_id not in allowed:
            findings.append(
                _finding(
                    "FORMAL_RETRIEVAL_UNKNOWN_STRATEGY",
                    "Strategy id must come from the public allowed strategy set.",
                    case_id="strategy_case_floor",
                    subject_id=str(row.get("query_id") or strategy_id),
                    subject_kind="strategy_case",
                )
            )
        cases.append(
            {
                "query_id": row.get("query_id"),
                "strategy_id": strategy_id,
                "selected_pre_oracle": row.get("selected_pre_oracle") is True,
                "body_material_status": "public_strategy_gate",
            }
        )
    if isinstance(negative_payload, dict):
        for row in _rows(negative_payload, "strategy_cases"):
            strategy_id = str(row.get("strategy_id") or "")
            if strategy_id and strategy_id not in allowed:
                _record(
                    findings,
                    observed,
                    "FORMAL_RETRIEVAL_UNKNOWN_STRATEGY",
                    "Retrieval strategy gate rejected an unknown strategy id.",
                    case_id=str(row.get("expected_negative_case_id") or "unknown_strategy_id"),
                    subject_id=str(row.get("query_id") or strategy_id),
                    subject_kind="negative_case",
                )
    return {
        "status": PASS if allowed and cases else "blocked",
        "allowed_strategy_ids": sorted(allowed),
        "strategy_case_count": len(cases),
        "strategy_cases": sorted(cases, key=lambda row: str(row["query_id"])),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _score_query(
    query: dict[str, Any],
    premises: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    split = str(query.get("split") or "train")
    query_terms = _tokenize(query.get("query_terms"))
    strategy_id = str(query.get("strategy_id") or "")
    ranked: list[dict[str, Any]] = []
    for premise in premises:
        allowed = set(premise.get("allowed_for_split", []))
        if split not in allowed:
            continue
        premise_terms = _tokenize(
            [
                premise.get("premise_id", ""),
                premise.get("namespace", ""),
                *premise.get("retrieval_terms", []),
            ]
        )
        overlap = sorted(set(query_terms) & set(premise_terms))
        strategy_bonus = 1 if strategy_id in set(premise.get("strategy_tags", [])) else 0
        score = sum(min(query_terms[token], premise_terms[token]) for token in overlap)
        score += strategy_bonus
        ranked.append(
            {
                "premise_id": premise["premise_id"],
                "score": score,
                "overlap_terms": overlap,
                "strategy_bonus": strategy_bonus,
                "source_ref": premise.get("source_ref"),
                "body_material_status": "retrieval_score_over_imported_index",
            }
        )
    return sorted(ranked, key=lambda row: (-int(row["score"]), str(row["premise_id"])))


def validate_retrieval_queries(
    payload: object,
    *,
    premises: list[dict[str, Any]],
    allowed_strategy_ids: list[str],
    negative_oracle_payload: object | None = None,
    negative_test_tuning_payload: object | None = None,
) -> dict[str, Any]:
    allowed = set(allowed_strategy_ids)
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    retrievals: list[dict[str, Any]] = []
    recall_scores: list[float] = []

    def inspect_query(row: dict[str, Any], *, negative: bool = False) -> None:
        query_id = str(row.get("query_id") or "query")
        forbidden = _forbidden_keys(row)
        if forbidden:
            _record(
                findings,
                observed,
                "FORMAL_RETRIEVAL_ORACLE_IDS_FORBIDDEN",
                "Retrieval queries cannot expose oracle-needed premise ids.",
                case_id=str(row.get("expected_negative_case_id") or "query_oracle_ids_forbidden"),
                subject_id=query_id,
                subject_kind="negative_case" if negative else "retrieval_query",
            )
        if row.get("uses_test_oracle_for_tuning") is True:
            _record(
                findings,
                observed,
                "FORMAL_RETRIEVAL_TEST_SPLIT_TUNING_FORBIDDEN",
                "Test split truth cannot tune retrieval ranking.",
                case_id=str(row.get("expected_negative_case_id") or "test_split_tuning_attempt"),
                subject_id=query_id,
                subject_kind="negative_case" if negative else "retrieval_query",
            )
        strategy_id = str(row.get("strategy_id") or "")
        if strategy_id and strategy_id not in allowed:
            findings.append(
                _finding(
                    "FORMAL_RETRIEVAL_UNKNOWN_STRATEGY",
                    "Query strategy id must be one of the public allowed strategies.",
                    case_id="retrieval_query_floor",
                    subject_id=query_id,
                    subject_kind="retrieval_query",
                )
            )

    for query in _rows(payload, "queries"):
        inspect_query(query)
        ranked = _score_query(query, premises)
        top_k = max(1, int(query.get("top_k") or 3))
        top = ranked[:top_k]
        expected = set(_strings(query.get("expected_public_premise_ids")))
        retrieved = {str(row["premise_id"]) for row in top}
        recall = len(expected & retrieved) / len(expected) if expected else None
        if recall is not None:
            recall_scores.append(recall)
        retrievals.append(
            {
                "query_id": str(query.get("query_id") or ""),
                "split": query.get("split"),
                "strategy_id": query.get("strategy_id"),
                "recipe_id": query.get("recipe_id"),
                "top_k": top_k,
                "retrieved_premise_ids": [str(row["premise_id"]) for row in top],
                "expected_public_premise_count": len(expected),
                "public_retrieval_recall": recall,
                "body_material_status": "retrieval_result_over_imported_index",
            }
        )

    if isinstance(negative_oracle_payload, dict):
        for row in _rows(negative_oracle_payload, "queries"):
            inspect_query(row, negative=True)
    if isinstance(negative_test_tuning_payload, dict):
        for row in _rows(negative_test_tuning_payload, "queries"):
            inspect_query(row, negative=True)

    mean_recall = sum(recall_scores) / len(recall_scores) if recall_scores else None
    return {
        "status": PASS if retrievals else "blocked",
        "query_count": len(retrievals),
        "retrievals": sorted(retrievals, key=lambda row: row["query_id"]),
        "mean_public_retrieval_recall": mean_recall,
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _secret_exclusion_scan(scan: dict[str, Any]) -> dict[str, Any]:
    payload = dict(scan)
    payload.pop("body_redacted", None)
    excluded_fields = payload.pop("forbidden_output_fields", None)
    payload["excluded_output_fields"] = excluded_fields or ["matched_excerpt", "body"]
    payload["excluded_output_field_labels_omitted"] = True
    payload["body_material_status"] = "secret_exclusion_scan_no_payload_body_export"
    hits: list[dict[str, Any]] = []
    for hit in payload.get("hits", []):
        if not isinstance(hit, dict):
            continue
        cleaned = dict(hit)
        cleaned.pop("body_redacted", None)
        cleaned["body_material_status"] = "forbidden_material_excluded"
        hits.append(cleaned)
    payload["hits"] = hits
    return payload


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = _secret_exclusion_scan(
        scan_paths(
            _scan_input_paths(input_dir, include_negative=include_negative),
            forbidden_classes=policy,
            display_root=public_root,
        )
    )

    projection = validate_projection_protocol(payloads["projection_protocol"])
    premise_index = validate_premise_index(
        payloads["premise_index"],
        payloads.get("premise_index_with_proof_body"),
    )
    recipes = validate_context_recipes(
        payloads["context_recipes"],
        payloads.get("context_recipe_budget_overflow"),
    )
    strategies = validate_strategy_cases(
        payloads["strategy_cases"],
        payloads.get("unknown_strategy_id"),
    )
    retrieval = validate_retrieval_queries(
        payloads["retrieval_queries"],
        premises=premise_index["premises"],
        allowed_strategy_ids=strategies["allowed_strategy_ids"],
        negative_oracle_payload=payloads.get("query_with_oracle_ids"),
        negative_test_tuning_payload=payloads.get("test_split_tuning_attempt"),
    )

    observed = _merge_observed(projection, premise_index, recipes, strategies, retrieval)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, premise_index, recipes, strategies, retrieval)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = (
        read_json_strict(input_dir / "bundle_manifest.json")
        if (input_dir / "bundle_manifest.json").is_file()
        else {}
    )
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and premise_index["status"] == PASS
        and recipes["status"] == PASS
        and strategies["status"] == PASS
        and retrieval["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "formal_math_premise_retrieval_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_contract": BODY_MATERIAL_CONTRACT,
        "body_material_status": BODY_MATERIAL_STATUS,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_runtime_refs": projection["public_runtime_refs"],
        "copied_material": projection["copied_material"],
        "copied_material_count": projection["copied_material_count"],
        "body_copied_material_count": projection["body_copied_material_count"],
        "premise_count": premise_index["premise_count"],
        "query_count": retrieval["query_count"],
        "recipe_count": recipes["recipe_count"],
        "strategy_case_count": strategies["strategy_case_count"],
        "allowed_strategy_ids": strategies["allowed_strategy_ids"],
        "mean_public_retrieval_recall": retrieval["mean_public_retrieval_recall"],
        "retrievals": retrieval["retrievals"],
        "premise_retrieval_board": {
            "headline": "Lean/Std premise retrieval runs over copied public macro premise-index metadata.",
            "protocol_id": projection["protocol_id"],
            "premise_count": premise_index["premise_count"],
            "query_count": retrieval["query_count"],
            "recipe_count": recipes["recipe_count"],
            "strategy_case_count": strategies["strategy_case_count"],
            "mean_public_retrieval_recall": retrieval["mean_public_retrieval_recall"],
            "retrieval_authority": "term_scoring_fixture_not_theorem_proving",
            "next_boundary": "formal_math_lean_proof_witness now carries the bounded public witness; retrieval still does not claim theorem proof authority",
            "lean_lake_execution_authorized": False,
            "formal_proof_authority": False,
            "provider_calls_authorized": False,
            "proof_bodies_allowed": False,
            "body_material_status": BODY_MATERIAL_STATUS,
        },
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
        "expected_negative_cases",
        "observed_negative_cases",
        "missing_negative_cases",
        "error_codes",
        "findings",
        "secret_exclusion_scan",
        "authority_ceiling",
        "anti_claim",
        "body_material_contract",
        "body_material_status",
        "protocol_id",
        "source_refs",
        "source_pattern_ids",
        "projection_receipt_refs",
        "public_runtime_refs",
        "copied_material",
        "copied_material_count",
        "body_copied_material_count",
        "premise_count",
        "query_count",
        "recipe_count",
        "strategy_case_count",
        "allowed_strategy_ids",
        "mean_public_retrieval_recall",
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
        "formal_math_premise_retrieval_result": target / RESULT_NAME,
        "premise_retrieval_board": target / BOARD_NAME,
        "formal_math_premise_retrieval_validation_receipt": target / VALIDATION_RECEIPT_NAME,
        "fixture_acceptance": acceptance_path,
    }
    receipt_paths = _relative_receipt_paths(paths, public_root_path)

    result_receipt = _common_receipt(
        result,
        schema_version="formal_math_premise_retrieval_result_receipt_v1",
        receipt_paths=receipt_paths,
    )
    result_receipt["retrievals"] = result["retrievals"]
    board = _common_receipt(
        result,
        schema_version="formal_math_premise_retrieval_board_v1",
        receipt_paths=receipt_paths,
    )
    board.update(result["premise_retrieval_board"])
    validation = _common_receipt(
        result,
        schema_version="formal_math_premise_retrieval_validation_receipt_v1",
        receipt_paths=receipt_paths,
    )
    validation.update(
        {
            "negative_case_coverage_status": PASS
            if not result["missing_negative_cases"]
            else "blocked",
            "proof_bodies_excluded": True,
            "oracle_ids_excluded": True,
            "test_split_tuning_rejected": "test_split_tuning_attempt"
            in result["observed_negative_cases"],
            "context_budget_enforced": "context_recipe_budget_overflow"
            in result["observed_negative_cases"],
            "unknown_strategy_rejected": "unknown_strategy_id"
            in result["observed_negative_cases"],
            "lean_lake_execution_authorized": False,
            "provider_calls_authorized": False,
        }
    )
    acceptance = _common_receipt(
        result,
        schema_version="formal_math_premise_retrieval_fixture_acceptance_v1",
        receipt_paths=receipt_paths,
    )
    acceptance.update(
        {
            "acceptance_status": "accepted_current_authority"
            if result["status"] == PASS
            else "blocked",
            "accepted_organ_id": ORGAN_ID,
            "bounded_witness_organ_id": "formal_math_lean_proof_witness",
            "lean_witness_deferred": False,
            "lean_witness_authority": "bounded_public_witness_owned_by_formal_math_lean_proof_witness",
        }
    )

    write_json_atomic(paths["formal_math_premise_retrieval_result"], result_receipt)
    write_json_atomic(paths["premise_retrieval_board"], board)
    write_json_atomic(paths["formal_math_premise_retrieval_validation_receipt"], validation)
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
        "python -m microcosm_core.organs.formal_math_premise_retrieval run "
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


def run_retrieval_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    command_text = command or (
        "python -m microcosm_core.organs.formal_math_premise_retrieval "
        f"run-retrieval-bundle --input {input_dir} --out {out_dir}"
    )
    result = _build_result(
        input_path,
        command=command_text,
        input_mode="exported_premise_retrieval_bundle",
        include_negative=False,
    )
    target = Path(out_dir)
    if not target.is_absolute():
        target = Path.cwd() / target
    target.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(input_path)
    result_path = target / BUNDLE_RESULT_NAME
    receipt = _common_receipt(
        result,
        schema_version="exported_premise_retrieval_bundle_validation_result_v1",
        receipt_paths=[_display(result_path, public_root=public_root)],
    )
    receipt["retrievals"] = result["retrievals"]
    write_json_atomic(result_path, receipt)
    result["receipt_paths"] = [_display(result_path, public_root=public_root)]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="formal_math_premise_retrieval")
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-retrieval-bundle"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out)
    else:
        result = run_retrieval_bundle(args.input, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
