"""Fixture-bounded audit for public doctrine fact claims and numeric bindings.

[PURPOSE] Check that exported public doctrine fact fixtures keep fact counts,
code loci, DAG references, and volatile numeric claims tied to inspectable
public evidence instead of drifting into unsupported narrative claims.
[INTERFACE] Exposes the CrownJewel `evaluate`, `evaluate_negative_case`, fixture
runner, exported-bundle runner, and CLI entrypoint for the
`doctrine_fact_claim_audit` organ.
[FLOW] Load fact, DAG, numeric-claim, and projection-protocol fixtures; import
the copied derived-fact helper from the source manifest; verify code loci and
DAG refs; run synthetic numeric-claim binding cases; return a body-free receipt.
[DEPENDENCIES] Uses Crown Jewel organ helpers, copied `derived_fact_hologram.py`
source, strict JSON fixtures, temporary directories, and public-root source
manifest validation.
[CONSTRAINTS] This does not prove a comprehension engine, minimum read graph,
private doctrine export, release readiness, semantic truth, or whole-system
correctness.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from microcosm_core.organs._crown_jewel_common import (
    PASS,
    CrownJewelSpec,
    finding,
    load_json_object,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)


ORGAN_ID = "doctrine_fact_claim_audit"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
CONCRETE_UNBOUND_NUMERIC_CLAIM_CODE = "DOCTRINE_UNBOUND_NUMERIC_CLAIM"
AX10_VOLATILE_NUMERIC_UNBOUND_CODE = "DOCTRINE_VOLATILE_NUMERIC_UNBOUND"
EXPECTED_NEGATIVE_CASES = {
    "wrong_fact_count": ("DOCTRINE_FACT_COUNT_MISMATCH",),
    "missing_code_locus": ("DOCTRINE_CODE_LOCUS_MISSING",),
    "dead_code_locus": ("DOCTRINE_CODE_LOCUS_ANCHOR_MISSING",),
    "dead_dag_ref": ("DOCTRINE_FACT_DAG_DEAD_REF",),
    "unbound_numeric_claim": (
        CONCRETE_UNBOUND_NUMERIC_CLAIM_CODE,
        AX10_VOLATILE_NUMERIC_UNBOUND_CODE,
    ),
}
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "fact_assertion_code_loci_dag_and_numeric_claim_fixture_truth_gate_only"
    ),
    "comprehension_engine_claim_authorized": False,
    "minimum_read_graph_claim_authorized": False,
    "private_doctrine_export_authorized": False,
    "release_authorized": False,
}
ANTI_CLAIM = (
    "Doctrine fact claim audit checks only public fixture fact counts, code-loci "
    "existence, anchor presence, DAG references, and synthetic volatile numeric "
    "claim binding cases. It is not a comprehension engine, does not prove a "
    "minimum read graph, does not export private doctrine, and does not "
    "authorize release."
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Doctrine fact claim audit",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=f"{ORGAN_ID}_result.json",
    board_name=f"{ORGAN_ID}_board.json",
    validation_receipt_name=f"{ORGAN_ID}_validation_receipt.json",
    bundle_result_name=f"exported_{ORGAN_ID}_bundle_validation_result.json",
    card_schema_version=f"{ORGAN_ID}_command_card_v1",
    required_inputs=(
        "fact_assertions.json",
        "fact_dag.json",
        "numeric_claims.json",
        "projection_protocol.json",
    ),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/doctrine_fact_claim_audit/"
        "exported_doctrine_fact_claim_audit_bundle/source_module_manifest.json"
    ),
    source_required_anchors={
        "system/lib/derived_fact_hologram.py": (
            "FactAssertion",
            "fact",
            "find_unbound_numeric_claims",
        ),
        "system/lib/paper_modules.py": ("paper", "module"),
    },
    bundle_input_mode="exported_doctrine_fact_claim_audit_bundle",
)


def _manifest_base(source_manifest: dict[str, Any], input_dir: Path) -> Path:
    """[ACTION] Choose the base directory for manifest-relative public source refs."""
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and manifest_path:
        return Path(manifest_path).parent
    return input_dir


def _resolve_code_locus(locus: dict[str, Any], *, manifest_base: Path) -> Path:
    """[ACTION] Resolve a fact code-locus path without escaping absolute refs."""
    path = Path(str(locus.get("path") or ""))
    if path.is_absolute():
        return path
    return manifest_base / path


def _load_derived_fact_module(
    *,
    source_manifest: dict[str, Any],
    input_dir: Path,
    findings: list[dict[str, Any]],
) -> Any | None:
    """[ACTION] Import the copied derived-fact helper required for numeric-claim checks."""
    manifest_base = _manifest_base(source_manifest, input_dir)
    module_path = manifest_base / "source_modules/system/lib/derived_fact_hologram.py"
    if not module_path.is_file():
        findings.append(
            finding(
                "DOCTRINE_NUMERIC_CLAIM_SOURCE_MISSING",
                "Numeric-claim binding requires the copied derived_fact_hologram.py body.",
                subject_id="source_modules/system/lib/derived_fact_hologram.py",
            )
        )
        return None
    module_name = f"_microcosm_{ORGAN_ID}_derived_fact_hologram"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        findings.append(
            finding(
                "DOCTRINE_NUMERIC_CLAIM_SOURCE_IMPORT_FAILED",
                "Copied derived_fact_hologram.py could not be prepared for import.",
                subject_id="source_modules/system/lib/derived_fact_hologram.py",
            )
        )
        return None
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - copied source import errors vary.
        findings.append(
            finding(
                "DOCTRINE_NUMERIC_CLAIM_SOURCE_IMPORT_FAILED",
                "Copied derived_fact_hologram.py could not be imported.",
                subject_id="source_modules/system/lib/derived_fact_hologram.py",
                observed=type(exc).__name__,
            )
        )
        return None
    return module


def _fact_assertions_for_sections(
    module: Any,
    *,
    case_id: str,
    sections: list[str],
) -> list[Any]:
    """[ACTION] Build synthetic FactAssertion rows for numeric-claim fixture sections."""
    assertion_type = getattr(module, "FactAssertion")
    return [
        assertion_type(
            fact_id=f"fixture.{case_id}.{index}",
            expected="fixture",
            mode="current",
            as_of="fixture",
            tolerance="n/a",
            why="synthetic numeric claim binding fixture",
            section=section,
            module_slug="doctrine_fact_claim_audit_fixture",
            module_file="numeric_claims.json",
        )
        for index, section in enumerate(sections, start=1)
    ]


def _strings(value: Any) -> list[str]:
    """[ACTION] Normalize a list-valued fixture field to strings."""
    return [str(item) for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _evaluate_numeric_claims(
    *,
    input_dir: Path,
    source_manifest: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """[ACTION] Run copied numeric-claim binding logic against synthetic fixture cases."""
    payload = load_json_object(input_dir / "numeric_claims.json", findings, label="numeric claims")
    module = _load_derived_fact_module(
        source_manifest=source_manifest,
        input_dir=input_dir,
        findings=findings,
    )
    if module is None:
        return {
            "numeric_claim_case_count": 0,
            "unbound_numeric_detection_count": 0,
            "unbound_numeric_detector_case_count": 0,
            "unbound_numeric_blocking_count": 0,
            "numeric_claim_cases": [],
        }
    finder = getattr(module, "find_unbound_numeric_claims", None)
    if not callable(finder):
        findings.append(
            finding(
                "DOCTRINE_NUMERIC_CLAIM_SOURCE_FUNCTION_MISSING",
                "Copied derived_fact_hologram.py must expose find_unbound_numeric_claims.",
                subject_id="find_unbound_numeric_claims",
            )
        )
        return {
            "numeric_claim_case_count": 0,
            "unbound_numeric_detection_count": 0,
            "unbound_numeric_detector_case_count": 0,
            "unbound_numeric_blocking_count": 0,
            "numeric_claim_cases": [],
        }

    case_rows = [row for row in payload.get("cases", []) if isinstance(row, dict)]
    if not case_rows:
        findings.append(
            finding(
                "DOCTRINE_NUMERIC_CLAIM_FIXTURE_CASES_MISSING",
                "numeric_claims.json must include at least one numeric claim case.",
                subject_id="numeric_claims.json",
            )
        )
    case_receipts: list[dict[str, Any]] = []
    detection_count = 0
    detector_case_count = 0
    blocking_count = 0
    for row in case_rows:
        case_id = str(row.get("case_id") or "numeric_claim_case")
        expected_unbound = row.get("expect_unbound") is True
        asserted_sections = _strings(row.get("asserted_sections"))
        assertions = _fact_assertions_for_sections(
            module,
            case_id=case_id,
            sections=asserted_sections,
        )
        results = finder(str(row.get("markdown") or ""), assertions)
        unbound = [item for item in results if isinstance(item, dict)]
        sections = sorted({str(item.get("section") or "") for item in unbound if item.get("section")})
        numbers = sorted({str(item.get("number") or "") for item in unbound if item.get("number")})
        detection_count += len(unbound)
        if expected_unbound:
            detector_case_count += 1
            expected_section = str(row.get("expected_section") or "")
            expected_number = str(row.get("expected_number") or "")
            if not unbound:
                findings.append(
                    finding(
                        "DOCTRINE_UNBOUND_NUMERIC_CLAIM_EXPECTED_MISSING",
                        "Detector fixture must prove unbound numeric claims are surfaced.",
                        case_id=case_id,
                    )
                )
            if expected_section and expected_section not in sections:
                findings.append(
                    finding(
                        "DOCTRINE_UNBOUND_NUMERIC_CLAIM_DETECTOR_MISMATCH",
                        "Detector fixture surfaced the wrong numeric claim section.",
                        case_id=case_id,
                        expected=expected_section,
                        observed=sections,
                    )
                )
            if expected_number and expected_number not in numbers:
                findings.append(
                    finding(
                        "DOCTRINE_UNBOUND_NUMERIC_CLAIM_DETECTOR_MISMATCH",
                        "Detector fixture surfaced the wrong numeric claim number.",
                        case_id=case_id,
                        expected=expected_number,
                        observed=numbers,
                    )
                )
        elif unbound:
            blocking_count += len(unbound)
            findings.append(
                finding(
                    CONCRETE_UNBOUND_NUMERIC_CLAIM_CODE,
                    "Current state and refresh contract numeric claims require a matching fact assertion section.",
                    case_id=case_id,
                    observed={
                        "unbound_numeric_claim_count": len(unbound),
                        "sections": sections,
                        "numbers": numbers,
                    },
                )
            )
            findings.append(
                finding(
                    AX10_VOLATILE_NUMERIC_UNBOUND_CODE,
                    "AX-10 volatile numeric claims must be blocked when no freshness-binding fact assertion section exists.",
                    case_id=case_id,
                    observed={
                        "unbound_numeric_claim_count": len(unbound),
                        "sections": sections,
                        "numbers": numbers,
                    },
                )
            )
        case_receipts.append(
            {
                "case_id": case_id,
                "expected_unbound": expected_unbound,
                "asserted_section_count": len(asserted_sections),
                "observed_unbound_numeric_claim_count": len(unbound),
                "observed_sections": sections,
                "observed_numbers": numbers,
                "body_in_receipt": False,
            }
        )
    return {
        "numeric_claim_case_count": len(case_rows),
        "unbound_numeric_detection_count": detection_count,
        "unbound_numeric_detector_case_count": detector_case_count,
        "unbound_numeric_blocking_count": blocking_count,
        "numeric_claim_cases": case_receipts,
    }


def evaluate(input_dir: Path, _public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    """[ACTION] Evaluate doctrine fact count, code-locus, DAG, and numeric-claim fixtures."""
    findings: list[dict[str, Any]] = []
    assertions = load_json_object(input_dir / "fact_assertions.json", findings, label="fact assertions")
    dag = load_json_object(input_dir / "fact_dag.json", findings, label="fact DAG")
    numeric_claims = _evaluate_numeric_claims(
        input_dir=input_dir,
        source_manifest=source_manifest,
        findings=findings,
    )
    fact_rows = [row for row in assertions.get("facts", []) if isinstance(row, dict)]
    expected_count = assertions.get("expected_fact_count")
    if expected_count != len(fact_rows):
        findings.append(
            finding(
                "DOCTRINE_FACT_COUNT_MISMATCH",
                "Declared fact count must match the fact assertion table.",
                expected=expected_count,
                observed=len(fact_rows),
            )
        )
    manifest_base = _manifest_base(source_manifest, input_dir)
    fact_ids = {str(row.get("fact_id")) for row in fact_rows if row.get("fact_id")}
    code_locus_count = 0
    verified_locus_count = 0
    for row in fact_rows:
        fact_id = str(row.get("fact_id") or "")
        loci = [locus for locus in row.get("code_loci", []) if isinstance(locus, dict)]
        if not loci:
            findings.append(
                finding(
                    "DOCTRINE_CODE_LOCUS_MISSING",
                    "Every audited fact requires at least one public code locus.",
                    case_id=fact_id,
                )
            )
        for locus in loci:
            code_locus_count += 1
            path = _resolve_code_locus(locus, manifest_base=manifest_base)
            anchor = str(locus.get("anchor") or "")
            if not path.is_file():
                findings.append(
                    finding(
                        "DOCTRINE_CODE_LOCUS_MISSING",
                        "Code locus path must exist in the public source manifest bundle.",
                        case_id=fact_id,
                        subject_id=str(locus.get("path") or ""),
                    )
                )
                continue
            text = path.read_text(encoding="utf-8")
            if anchor and anchor not in text:
                findings.append(
                    finding(
                        "DOCTRINE_CODE_LOCUS_ANCHOR_MISSING",
                        "Code locus anchor must be present in the copied public body.",
                        case_id=fact_id,
                        subject_id=str(locus.get("path") or ""),
                        expected=anchor,
                    )
                )
                continue
            verified_locus_count += 1

    dag_edges = [row for row in dag.get("edges", []) if isinstance(row, dict)]
    unknown_edge_refs: list[str] = []
    for edge in dag_edges:
        for key in ("from", "to"):
            ref = str(edge.get(key) or "")
            if ref not in fact_ids:
                unknown_edge_refs.append(ref)
    if unknown_edge_refs:
        findings.append(
            finding(
                "DOCTRINE_FACT_DAG_DEAD_REF",
                "Fact DAG edges must reference audited fact ids.",
                observed=sorted(set(unknown_edge_refs)),
            )
        )

    return {
        "status": PASS if not findings else "blocked",
        "fact_count": len(fact_rows),
        "expected_fact_count": expected_count,
        "code_locus_count": code_locus_count,
        "verified_code_locus_count": verified_locus_count,
        "dag_edge_count": len(dag_edges),
        **numeric_claims,
        "truth_gate": "fact_count_code_loci_fixture_dag_and_numeric_claims_only",
        "comprehension_engine_claim_authorized": False,
        "minimum_read_graph_claim_authorized": False,
        "findings": findings,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """[ACTION] Write a deterministic JSON fixture for a negative-case replay."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _semantic_case_payloads(input_dir: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """[ACTION] Load and deep-copy the semantic fixture payloads used by mutations."""
    payloads = {
        name: load_json_object(input_dir / name, findings, label=name)
        for name in ("fact_assertions.json", "fact_dag.json", "numeric_claims.json")
    }
    return copy.deepcopy(payloads)


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> dict[str, Any]:
    """[ACTION] Mutate one doctrine fact fixture case and return observed error codes."""
    findings: list[dict[str, Any]] = []
    source_input = Path(input_dir)
    public_root = public_root_for_path(source_input)
    source_manifest = validate_source_manifest(source_input, SPEC, public_root=public_root)
    findings.extend(source_manifest.get("findings", []))
    payloads = _semantic_case_payloads(source_input, findings)

    if case_id == "wrong_fact_count":
        assertions = payloads["fact_assertions.json"]
        facts = [row for row in assertions.get("facts", []) if isinstance(row, dict)]
        assertions["expected_fact_count"] = len(facts) + 1
    elif case_id == "missing_code_locus":
        assertions = payloads["fact_assertions.json"]
        facts = [row for row in assertions.get("facts", []) if isinstance(row, dict)]
        if facts:
            facts[0]["code_loci"] = []
    elif case_id == "dead_code_locus":
        assertions = payloads["fact_assertions.json"]
        facts = [row for row in assertions.get("facts", []) if isinstance(row, dict)]
        loci = (
            [row for row in facts[0].get("code_loci", []) if isinstance(row, dict)]
            if facts
            else []
        )
        if loci:
            loci[0]["anchor"] = "not_present_in_copied_body"
    elif case_id == "dead_dag_ref":
        dag = payloads["fact_dag.json"]
        edges = [row for row in dag.get("edges", []) if isinstance(row, dict)]
        if edges:
            edges[0]["to"] = "missing_fact_id"
    elif case_id == "unbound_numeric_claim":
        numeric_claims = payloads["numeric_claims.json"]
        cases = [row for row in numeric_claims.get("cases", []) if isinstance(row, dict)]
        if cases:
            cases[0]["asserted_sections"] = []
    else:
        findings.append(
            finding(
                "CROWN_JEWEL_NEGATIVE_CASE_UNKNOWN",
                "Unknown doctrine fact claim audit negative case.",
                case_id=case_id,
            )
        )

    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_negative_") as tmp:
        case_input = Path(tmp)
        for name, payload in payloads.items():
            _write_json(case_input / name, payload)
        exercise = evaluate(case_input, public_root, source_manifest)
    findings.extend(exercise.get("findings", []))
    return {
        "status": PASS if not findings else "blocked",
        "error_codes": sorted(
            {
                str(row.get("error_code"))
                for row in findings
                if isinstance(row, dict) and row.get("error_code")
            }
        ),
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the doctrine fact claim audit organ over fixture inputs."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_doctrine_fact_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Run the exported bundle form of the doctrine fact claim audit."""
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=SPEC.bundle_input_mode,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Dispatch CLI arguments through the doctrine fact audit entrypoint."""
    return main_for_spec(
        SPEC,
        argv,
        evaluator=evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-doctrine-fact-bundle",
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
