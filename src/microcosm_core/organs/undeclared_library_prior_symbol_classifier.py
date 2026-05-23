from __future__ import annotations

import argparse
import re
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


ORGAN_ID = "undeclared_library_prior_symbol_classifier"
FIXTURE_ID = "first_wave.undeclared_library_prior_symbol_classifier"
VALIDATOR_ID = "validator.microcosm.organs.undeclared_library_prior_symbol_classifier"

RESULT_NAME = "undeclared_library_prior_symbol_classifier_result.json"
BOARD_NAME = "undeclared_library_prior_symbol_classifier_board.json"
VALIDATION_RECEIPT_NAME = (
    "undeclared_library_prior_symbol_classifier_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "undeclared_library_prior_symbol_classifier_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_symbol_classifier_bundle_validation_result.json"

SOURCE_REFS = [
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json",
    "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_retrieval_graph_v0/run_summary.json",
    "microcosm-substrate/fixtures/first_wave/lean_std_premise_index/input/premise_index.json",
    "microcosm-substrate/receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "microcosm-substrate/receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
]
RECEIPT_ANCHOR_REFS = [
    "microcosm-substrate/receipts/first_wave/lean_std_premise_index/lean_std_premise_index_result.json",
    "microcosm-substrate/receipts/first_wave/corpus_readiness_mathlib_absence_gate/corpus_readiness_mathlib_absence_gate_result.json",
    "microcosm-substrate/receipts/first_wave/tactic_portfolio_availability_probe/tactic_portfolio_availability_result.json",
]
SOURCE_TARGET_REFS = [
    "microcosm-substrate/fixtures/first_wave/undeclared_library_prior_symbol_classifier/input/premise_index.json",
    "microcosm-substrate/fixtures/first_wave/undeclared_library_prior_symbol_classifier/input/symbol_observations.json",
    "microcosm-substrate/examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle/premise_index.json",
    "microcosm-substrate/examples/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle/symbol_observations.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_result.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_board.json",
    "microcosm-substrate/receipts/first_wave/undeclared_library_prior_symbol_classifier/undeclared_library_prior_symbol_classifier_validation_receipt.json",
    ACCEPTANCE_RECEIPT_REL,
    "microcosm-substrate/receipts/runtime_shell/demo_project/organs/undeclared_library_prior_symbol_classifier/exported_symbol_classifier_bundle_validation_result.json",
]
SOURCE_DIGESTS = {
    SOURCE_REFS[0]: "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1",
    SOURCE_REFS[1]: "sha256:93304410f32d40f5cad1c161c1d01a5d6f353ee10b7cf3fecbaaf7b068b43008",
    SOURCE_REFS[2]: "sha256:0be36ba5b75b40d2ede2d90cefa5181829420df7abbae216d18282b92a30f869",
    SOURCE_REFS[3]: "sha256:ff2a6ee61993dc2e848bec3afa692a6f21950d3c9d92d9ec11e311c0a97da9ba",
    SOURCE_REFS[4]: "sha256:2a2ea1ff7379d58673d414bc055996384b1fadd63f747aa56e1be818225b79eb",
}
BODY_MATERIAL_STATUS = "copied_non_secret_macro_body_with_provenance"
SYMBOL_BOUNDARY_STATUS = "real_lean_std_symbol_boundary_and_mathlib_absence_context"
TOOLCHAIN_BOUNDARY_STATUS = "real_lean_4_29_1_std_mathlib_absence_probe"
BODY_IN_RECEIPT = False

INPUT_NAMES = (
    "projection_protocol.json",
    "premise_index.json",
    "symbol_observations.json",
    "classifier_policy.json",
)
NEGATIVE_INPUT_NAMES = (
    "proof_body_leakage.json",
    "private_source_ref_leakage.json",
    "missing_escalation_for_undeclared_symbol.json",
    "premise_budget_precedence_violation.json",
    "allowed_symbol_false_positive.json",
    "unqualified_symbol_overclaim.json",
    "theorem_correctness_overclaim.json",
)

EXPECTED_NEGATIVE_CASES = {
    "proof_body_leakage": ["SYMBOL_CLASSIFIER_PROOF_BODY_FORBIDDEN"],
    "private_source_ref_leakage": ["SYMBOL_CLASSIFIER_PRIVATE_SOURCE_REF_FORBIDDEN"],
    "missing_escalation_for_undeclared_symbol": [
        "SYMBOL_CLASSIFIER_UNDECLARED_LIBRARY_PRIOR_NOT_ESCALATED"
    ],
    "premise_budget_precedence_violation": [
        "SYMBOL_CLASSIFIER_PREMISE_BUDGET_PRECEDENCE"
    ],
    "allowed_symbol_false_positive": ["SYMBOL_CLASSIFIER_ALLOWED_SYMBOL_FALSE_POSITIVE"],
    "unqualified_symbol_overclaim": ["SYMBOL_CLASSIFIER_UNQUALIFIED_SYMBOL_OVERCLAIM"],
    "theorem_correctness_overclaim": ["SYMBOL_CLASSIFIER_THEOREM_CORRECTNESS_OVERCLAIM"],
}

QUALIFIED_SYMBOL_RE = re.compile(r"\b(?:Nat|List|Bool|Iff|Eq)\.[A-Za-z0-9_.'+]+")
FORBIDDEN_PROOF_KEYS = (
    "proof_body",
    "candidate_proof_body",
    "ground_truth_proof",
    "private_proof_body",
)
PRIVATE_SOURCE_KEYS = (
    "private_source_ref",
    "private_source_refs",
    "raw_source_path",
    "oracle_source_ref",
)

UNDECLARED_CLASS = "UNDECLARED_LIBRARY_PRIOR"
PREMISE_BUDGET_CLASS = "PREMISE_BUDGET_VIOLATION"
BRIDGE_OUTCOME = "bridge_escalate"
RETRY_OUTCOME = "retry"

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "real_lean_std_symbol_boundary_not_theorem_authority",
    "formal_proof_authority": False,
    "theorem_correctness_authority": False,
    "lean_lake_execution_authorized": False,
    "mathlib_absence_is_probe_result": True,
    "proof_bodies_allowed": False,
    "private_source_refs_allowed": False,
    "provider_calls_authorized": False,
    "premise_budget_retry_authority": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Undeclared library prior symbol classifier validates copied non-secret "
    "Lean/Std premise rows and Ring2 symbol-boundary observations with a "
    "Mathlib-absent toolchain boundary. It does not run Lean or Lake, prove "
    "theorem correctness, expose proof bodies or private source refs, call "
    "providers, turn the whole library into an allowlist, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate":
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    return public_relative_path(path, display_root=public_root)


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


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


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
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": "negative_fixture_forbidden_material_excluded",
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


def _has_forbidden_key(row: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(key in row for key in keys)


def _private_ref_present(row: dict[str, Any]) -> bool:
    if _has_forbidden_key(row, PRIVATE_SOURCE_KEYS):
        return True
    refs = _strings(row.get("source_refs")) + _strings(row.get("source_anchor_refs"))
    return any(ref.startswith(("private:", "macro-private:", "/Users/")) for ref in refs)


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


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    source_targets = _strings(protocol.get("source_target_refs"))
    receipt_anchors = _strings(protocol.get("receipt_anchor_refs"))
    source_digests = protocol.get("source_digests", {})
    omitted = _rows(protocol, "omitted_material")
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 3
        or len(source_pattern_ids) < 3
        or len(source_targets) < 3
        or not isinstance(source_digests, dict)
        or not source_digests
    ):
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Symbol classifier projection must cite real source refs, pattern ids, target refs, and source digests.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    for row in omitted:
        if not row.get("omission_receipt_ref"):
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_OMISSION_RECEIPT_MISSING",
                    "Omitted proof/private/provider material must carry an omission receipt.",
                    case_id="projection_protocol_floor",
                    subject_id=str(row.get("material_id") or "omitted_material"),
                    subject_kind="projection_protocol",
                )
            )
    return {
        "status": PASS
        if source_refs
        and source_pattern_ids
        and projection_receipts
        and source_targets
        and isinstance(source_digests, dict)
        and source_digests
        and not findings
        else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "source_target_refs": source_targets,
        "receipt_anchor_refs": receipt_anchors,
        "source_digests": {str(key): str(value) for key, value in sorted(source_digests.items())}
        if isinstance(source_digests, dict)
        else {},
        "omitted_material_count": len(omitted),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _premise_maps(payload: object) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in _rows(payload, "premises"):
        premise_id = str(row.get("premise_id") or "")
        symbol = str(row.get("theorem_or_def_name") or "")
        if premise_id:
            by_id[premise_id] = row
        if symbol:
            by_symbol[symbol] = row
    return by_id, by_symbol


def validate_premise_index(payload: object) -> dict[str, Any]:
    rows = _rows(payload, "premises")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        premise_id = str(row.get("premise_id") or "")
        symbol = str(row.get("theorem_or_def_name") or "")
        namespace = str(row.get("namespace") or "")
        source_ref = str(row.get("source_ref") or "")
        if not premise_id or not symbol or "." not in symbol:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_PREMISE_ID_OR_SYMBOL_MISSING",
                    "Premise index rows require a premise id and qualified theorem_or_def_name.",
                    case_id="premise_index_floor",
                    subject_id=premise_id or symbol or "premise",
                    subject_kind="premise_index",
                )
            )
        if not source_ref:
            findings.append(
                _finding(
                    "SYMBOL_CLASSIFIER_PREMISE_SOURCE_REF_MISSING",
                    "Premise index rows require a public source ref.",
                    case_id="premise_index_floor",
                    subject_id=premise_id or symbol or "premise",
                    subject_kind="premise_index",
                )
            )
        exported.append(
            {
                "premise_id": premise_id,
                "theorem_or_def_name": symbol,
                "namespace": namespace,
                "source_ref": source_ref,
                "allowed_for_split": _strings(row.get("allowed_for_split")),
                "body_in_receipt": BODY_IN_RECEIPT,
                "body_material_status": str(
                    row.get("body_material_status") or "imported_premise_index_row"
                ),
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "premise_count": len(rows),
        "namespace_count": len({row["namespace"] for row in exported if row["namespace"]}),
        "premises": sorted(exported, key=lambda row: row["premise_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_classifier_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, dict) else {}
    findings: list[dict[str, Any]] = []
    if policy.get("proof_bodies_allowed") is True:
        findings.append(
            _finding(
                "SYMBOL_CLASSIFIER_POLICY_PROOF_BODY_ALLOWED",
                "The public classifier policy cannot allow proof bodies.",
                case_id="classifier_policy_floor",
                subject_id=str(policy.get("policy_id") or "classifier_policy"),
                subject_kind="classifier_policy",
            )
        )
    return {
        "status": PASS
        if policy.get("qualified_symbol_regex") == QUALIFIED_SYMBOL_RE.pattern
        and policy.get("undeclared_review_outcome") == BRIDGE_OUTCOME
        and policy.get("premise_budget_review_outcome") == RETRY_OUTCOME
        and not findings
        else "blocked",
        "policy_id": policy.get("policy_id"),
        "qualified_symbol_regex": policy.get("qualified_symbol_regex"),
        "undeclared_review_outcome": policy.get("undeclared_review_outcome"),
        "premise_budget_review_outcome": policy.get("premise_budget_review_outcome"),
        "proof_bodies_allowed": bool(policy.get("proof_bodies_allowed")),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _qualified_refs(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "proof_symbol_refs",
        "observed_symbol_refs",
        "library_priors_used",
        "undeclared_library_prior_symbols",
    ):
        values.extend(_strings(row.get(key)))
    return sorted(set(symbol for symbol in values if QUALIFIED_SYMBOL_RE.fullmatch(symbol)))


def _unqualified_refs(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "proof_symbol_refs",
        "observed_symbol_refs",
        "library_priors_used",
        "undeclared_library_prior_symbols",
    ):
        values.extend(_strings(row.get(key)))
    return sorted(set(symbol for symbol in values if symbol and not QUALIFIED_SYMBOL_RE.fullmatch(symbol)))


def _classify_row(
    row: dict[str, Any],
    *,
    premise_by_id: dict[str, dict[str, Any]],
    premise_by_symbol: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    receipt_id = str(row.get("receipt_id") or row.get("case_id") or "symbol_observation")
    case_id = str(row.get("expected_negative_case_id") or receipt_id)
    subject_kind = "negative_case" if negative else "symbol_observation"

    if _has_forbidden_key(row, FORBIDDEN_PROOF_KEYS):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PROOF_BODY_FORBIDDEN",
            "Public symbol observations may carry hashes and extracted refs, not proof bodies.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if _private_ref_present(row):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PRIVATE_SOURCE_REF_FORBIDDEN",
            "Public symbol observations may not expose private source refs.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if row.get("claims_theorem_correctness") is True:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_THEOREM_CORRECTNESS_OVERCLAIM",
            "A library-prior classifier is not theorem correctness authority.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )

    allowed_ids = _strings(row.get("allowed_premise_ids"))
    cited_unallowed_ids = _strings(row.get("cited_unallowed_premise_ids"))
    allowed_symbols = {
        str(premise_by_id[premise_id].get("theorem_or_def_name"))
        for premise_id in allowed_ids
        if premise_id in premise_by_id
    }
    cited_unallowed_symbols = {
        str(premise_by_id[premise_id].get("theorem_or_def_name"))
        for premise_id in cited_unallowed_ids
        if premise_id in premise_by_id
    }
    observed_symbols = _qualified_refs(row)
    known_symbols = [symbol for symbol in observed_symbols if symbol in premise_by_symbol]
    undeclared = sorted(
        symbol
        for symbol in known_symbols
        if symbol not in allowed_symbols and symbol not in cited_unallowed_symbols
    )
    unqualified = _unqualified_refs(row)

    computed_class = "NONE"
    computed_outcome = "accept_as_advisory"
    if cited_unallowed_ids:
        computed_class = PREMISE_BUDGET_CLASS
        computed_outcome = RETRY_OUTCOME
    elif undeclared:
        computed_class = UNDECLARED_CLASS
        computed_outcome = BRIDGE_OUTCOME

    asserted_class = str(row.get("classified_failure_class") or computed_class)
    asserted_outcome = str(row.get("review_outcome") or computed_outcome)
    if undeclared and (
        asserted_class != UNDECLARED_CLASS or asserted_outcome != BRIDGE_OUTCOME
    ):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_UNDECLARED_LIBRARY_PRIOR_NOT_ESCALATED",
            "Undeclared known library symbols must classify as UNDECLARED_LIBRARY_PRIOR and bridge-escalate.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if cited_unallowed_ids and (
        asserted_class == UNDECLARED_CLASS or asserted_outcome == BRIDGE_OUTCOME
    ):
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_PREMISE_BUDGET_PRECEDENCE",
            "cited_unallowed_premise_ids short-circuit the residual symbol classifier.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if allowed_symbols.intersection(set(observed_symbols)) and asserted_class == UNDECLARED_CLASS:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_ALLOWED_SYMBOL_FALSE_POSITIVE",
            "Symbols already admitted by allowed_premise_ids cannot be quarantined as undeclared library priors.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )
    if unqualified and asserted_class == UNDECLARED_CLASS:
        _record(
            findings,
            observed,
            "SYMBOL_CLASSIFIER_UNQUALIFIED_SYMBOL_OVERCLAIM",
            "Unqualified tokens cannot support the qualified library-prior class.",
            case_id=case_id,
            subject_id=receipt_id,
            subject_kind=subject_kind,
        )

    return {
        "receipt_id": receipt_id,
        "expected_negative_case_id": case_id if negative else None,
        "observed_qualified_symbols": observed_symbols,
        "observed_known_symbols": known_symbols,
        "allowed_premise_ids": allowed_ids,
        "cited_unallowed_premise_ids": cited_unallowed_ids,
        "allowed_symbols": sorted(allowed_symbols),
        "cited_unallowed_symbols": sorted(cited_unallowed_symbols),
        "undeclared_library_prior_symbols": undeclared,
        "computed_failure_class": computed_class,
        "computed_review_outcome": computed_outcome,
        "asserted_failure_class": asserted_class,
        "asserted_review_outcome": asserted_outcome,
        "body_in_receipt": BODY_IN_RECEIPT,
        "body_material_status": BODY_MATERIAL_STATUS,
        "symbol_boundary_status": SYMBOL_BOUNDARY_STATUS,
    }


def validate_symbol_observations(
    payload: object,
    premise_index: object,
    negative_payloads: dict[str, object],
) -> dict[str, Any]:
    premise_by_id, premise_by_symbol = _premise_maps(premise_index)
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "symbol_observations"):
        rows.append(
            _classify_row(
                row,
                premise_by_id=premise_by_id,
                premise_by_symbol=premise_by_symbol,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for payload in negative_payloads.values():
        negative_rows = _rows(payload, "symbol_observations")
        if isinstance(payload, dict) and not negative_rows:
            negative_rows = [payload]
        for row in negative_rows:
            _classify_row(
                row,
                premise_by_id=premise_by_id,
                premise_by_symbol=premise_by_symbol,
                findings=findings,
                observed=observed,
                negative=True,
            )

    floor_findings = [
        row
        for row in findings
        if row.get("negative_case_id") in {"symbol_observation_floor"}
    ]
    undeclared_rows = [
        row for row in rows if row["computed_failure_class"] == UNDECLARED_CLASS
    ]
    budget_rows = [
        row for row in rows if row["computed_failure_class"] == PREMISE_BUDGET_CLASS
    ]
    return {
        "status": PASS if rows and undeclared_rows and budget_rows and not floor_findings else "blocked",
        "classification_count": len(rows),
        "undeclared_library_prior_count": len(undeclared_rows),
        "premise_budget_precedence_count": len(budget_rows),
        "bridge_escalation_count": sum(
            1 for row in rows if row["computed_review_outcome"] == BRIDGE_OUTCOME
        ),
        "retry_count": sum(
            1 for row in rows if row["computed_review_outcome"] == RETRY_OUTCOME
        ),
        "classification_rows": sorted(rows, key=lambda row: row["receipt_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


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
    secret_scan = scan_paths(
        _input_paths(input_dir, include_negative=include_negative),
        forbidden_classes=policy,
        display_root=public_root,
    )
    secret_scan["body_material_status"] = "secret_exclusion_scan_no_proof_or_provider_bodies"

    projection = validate_projection_protocol(payloads["projection_protocol"])
    premise_index = validate_premise_index(payloads["premise_index"])
    classifier_policy = validate_classifier_policy(payloads["classifier_policy"])
    observations = validate_symbol_observations(
        payloads["symbol_observations"],
        payloads["premise_index"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
    )

    observed = _merge_observed(projection, premise_index, classifier_policy, observations)
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(case_id for case_id in expected if case_id not in observed)
    findings = _merge_findings(projection, premise_index, classifier_policy, observations)
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    status = (
        PASS
        if not missing
        and secret_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and premise_index["status"] == PASS
        and classifier_policy["status"] == PASS
        and observations["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "undeclared_library_prior_symbol_classifier_result_v1",
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
        "body_material_status": BODY_MATERIAL_STATUS,
        "symbol_boundary_status": SYMBOL_BOUNDARY_STATUS,
        "toolchain_boundary_status": TOOLCHAIN_BOUNDARY_STATUS,
        "body_in_receipt": BODY_IN_RECEIPT,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "receipt_anchor_refs": projection["receipt_anchor_refs"],
        "source_target_refs": projection["source_target_refs"],
        "source_digests": projection["source_digests"],
        "real_substrate_refs": projection["source_refs"],
        "premise_count": premise_index["premise_count"],
        "namespace_count": premise_index["namespace_count"],
        "classification_count": observations["classification_count"],
        "undeclared_library_prior_count": observations["undeclared_library_prior_count"],
        "premise_budget_precedence_count": observations["premise_budget_precedence_count"],
        "bridge_escalation_count": observations["bridge_escalation_count"],
        "retry_count": observations["retry_count"],
        "qualified_symbol_regex": classifier_policy["qualified_symbol_regex"],
        "premises": premise_index["premises"],
        "classification_rows": observations["classification_rows"],
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "undeclared_library_prior_symbol_classifier_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "undeclared_library_prior_symbol_classifier_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "mechanics": [
            {
                "mechanic_id": "closed_premise_boundary",
                "count": result["premise_count"],
                "authority": "sanctioned_library_prior_is_explicit_not_implicit",
            },
            {
                "mechanic_id": "undeclared_prior_quarantine",
                "count": result["undeclared_library_prior_count"],
                "authority": "undeclared_priors_quarantined_not_rejected",
            },
            {
                "mechanic_id": "premise_budget_precedence",
                "count": result["premise_budget_precedence_count"],
                "authority": "cited_unallowed_takes_precedence_over_symbol_regex",
            },
        ],
        "classification_rows": result["classification_rows"],
        "qualified_symbol_regex": result["qualified_symbol_regex"],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "receipt_anchor_refs": result["receipt_anchor_refs"],
        "source_target_refs": result["source_target_refs"],
        "source_digests": result["source_digests"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    board = _board_from_result(result)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "undeclared_library_prior_symbol_classifier_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**board, "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "undeclared_library_prior_symbol_classifier_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "premise_count": result["premise_count"],
        "classification_count": result["classification_count"],
        "undeclared_library_prior_count": result["undeclared_library_prior_count"],
        "premise_budget_precedence_count": result[
            "premise_budget_precedence_count"
        ],
        "bridge_escalation_count": result["bridge_escalation_count"],
        "retry_count": result["retry_count"],
        "formal_proof_authority": False,
        "theorem_correctness_authority": False,
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "receipt_anchor_refs": result["receipt_anchor_refs"],
        "source_target_refs": result["source_target_refs"],
        "source_digests": result["source_digests"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "undeclared_library_prior_symbol_classifier_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "error_codes": result["error_codes"],
        "body_material_status": result["body_material_status"],
        "symbol_boundary_status": result["symbol_boundary_status"],
        "toolchain_boundary_status": result["toolchain_boundary_status"],
        "body_in_receipt": BODY_IN_RECEIPT,
        "secret_exclusion_scan": result["secret_exclusion_scan"],
        "real_substrate_refs": result["real_substrate_refs"],
        "source_digests": result["source_digests"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "symbol_classifier_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.undeclared_library_prior_symbol_classifier run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_symbol_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.undeclared_library_prior_symbol_classifier "
        "run-symbol-bundle"
    ),
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="exported_symbol_classifier_bundle",
        include_negative=False,
    )
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_symbol_classifier_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="undeclared_library_prior_symbol_classifier")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    bundle_parser = sub.add_parser("run-symbol-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "run":
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
    elif args.action == "run-symbol-bundle":
        result = run_symbol_bundle(args.input, args.out)
    else:  # pragma: no cover
        raise ValueError(args.action)
    print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
