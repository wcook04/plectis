"""
Implements organs annex knowledge routing for the public Plectis package.

Callers enter through `build_result`, `result_card`, `run`,
`run_annex_knowledge_routing_bundle`, `build_parser`, and `main`; constants such as
`ORGAN_ID`, `FIXTURE_ID`, `VALIDATOR_ID`, `SCHEMA_VERSION`, and 9 more pin local fixture
names; dependencies include `argparse`, `json`, `pathlib`, `typing`, and 1 more. It builds
public fixture, result, card, or verdict structures while keeping private substrate bodies
out of the payload.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.engine_room.annex_knowledge_router import route_catalog
from microcosm_core.receipts import utc_now, write_json_atomic


ORGAN_ID = "annex_knowledge_routing"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"
SCHEMA_VERSION = f"{ORGAN_ID}_organ_v1"
RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
ACCEPTANCE_RECEIPT_NAME = f"{ORGAN_ID}_fixture_acceptance.json"

# The planted negative cases the runner asserts on: a catalog/problem pair that
# yields no admissible match MUST recompute to the "no_match" rejection marker.
# The runner marks a case "negative" when its declared expectation is rejection
# (expected_ok is false), and asserts the capsule's observed status equals the
# expected reject marker named here.
EXPECTED_NEGATIVE_CASES = {
    "no_overlap_rejected": "no_match",
    "domain_filter_rejected": "no_match",
}

CLAIM_CEILING = (
    "Ranks a sanitized in-memory annex catalog against a problem statement using "
    "explainable tiered weighted-token retrieval over bounded public fixtures: "
    "structured routing fields score highest, family text and open-first "
    "summaries weaker, curated notes weakest, with an exact/phrase/token-overlap "
    "score per tier and a per-row match breakdown. It rejects unroutable "
    "problems by recomputation, returning no_match when no candidate scores above "
    "zero or a filter excludes every candidate. It is not BM25, not TF-IDF, not "
    "embedding or semantic search, does not clone repositories, ships no private "
    "annex corpus, and is not a license, provenance, or release authority."
)
ANTI_CLAIM = (
    "The annex knowledge routing organ ranks a sanitized fixture catalog over "
    "public fixture inputs only. It does not implement BM25, TF-IDF, embeddings, "
    "or semantic search; it does not clone third-party repositories, ship the "
    "private annex corpus, export private macro state, credentials, or raw "
    "operator threads; it does not call providers or external solvers, does not "
    "adjudicate licenses or provenance, and does not authorize release or "
    "publication. An unroutable problem cannot pass because the retriever "
    "recomputes the per-tier token scores and emits no_match whenever no "
    "candidate clears a positive score or a domain/cluster filter removes every "
    "candidate."
)
AUTHORITY_CEILING = {
    "status": "pass",
    "real_substrate_disposition": "real_substrate_capsule",
    "clones_repositories": False,
    "ships_private_corpus": False,
    "semantic_search": False,
    "license_authority": False,
    "provider_call": False,
    "oracle_or_prover": False,
    "production_ready": False,
    "release_authorized": False,
    "publication_authorized": False,
    "source_mutation_authorized": False,
}

SPEC = {
    "organ_id": ORGAN_ID,
    "title": "Annex knowledge routing",
    "fixture_id": FIXTURE_ID,
    "validator_id": VALIDATOR_ID,
    "result_name": RESULT_NAME,
    "expected_negative_cases": EXPECTED_NEGATIVE_CASES,
    "anti_claim": ANTI_CLAIM,
    "authority_ceiling": AUTHORITY_CEILING,
}


def _read_json(path: Path) -> Mapping[str, Any]:
    """
    Read read JSON for `microcosm_core.organs.annex_knowledge_routing`.

    Input comes from `path`; malformed or missing data follows the exceptions and checks
    visible in the body.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fixture_cases(input_path: str | Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """
    Return fixture cases for the organs annex knowledge routing flow.

    Inputs are `input_path`; notable helpers are `Path`, `is_file`, `FileNotFoundError`,
    `_read_json`, and 1 more; invalid cases raise from the explicit checks in the body.
    """
    path = Path(input_path)
    if path.is_file():
        return [(path, _read_json(path))]
    rows = [(item, _read_json(item)) for item in sorted(path.glob("*.json"))]
    if not rows:
        raise FileNotFoundError(f"no JSON fixture cases under {path}")
    return rows


def _evaluate_case(case: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.annex_knowledge_routing._evaluate_case` into the
    payload shape expected by organs annex knowledge routing.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    case_id = str(case.get("case_id") or "")
    case_type = str(case.get("case_type") or "positive")
    expected_ok = bool(case.get("expected_ok", True))
    catalog = case.get("catalog") if isinstance(case.get("catalog"), Mapping) else {}

    receipt = route_catalog(
        catalog,
        problem=str(case.get("problem") or ""),
        domain=case.get("domain") if case.get("domain") is not None else None,
        cluster=case.get("cluster") if case.get("cluster") is not None else None,
        include_notes=bool(case.get("include_notes", True)),
        limit=case.get("limit") if case.get("limit") is not None else None,
    )
    observed_status = str(receipt.get("status") or "")
    rows = receipt.get("rows") or []
    top_slug = str(rows[0].get("slug")) if rows else ""
    top_score = int(rows[0].get("score") or 0) if rows else 0
    matched_note_ids = list(rows[0].get("matched_note_ids", [])) if rows else []

    observed_routed = observed_status == "routed"
    expectation_met = observed_routed == expected_ok

    if case_type == "negative":
        expected_marker = EXPECTED_NEGATIVE_CASES.get(case_id, "")
        marker_present = bool(expected_marker) and observed_status == expected_marker
        observed_ok = (not observed_routed) and expectation_met and marker_present
    else:
        expected_top_slug = str(case.get("expected_top_slug") or "")
        expected_min_score = int(case.get("expected_min_score") or 0)
        expected_note_id = str(case.get("expected_note_id") or "")
        slug_ok = (not expected_top_slug) or top_slug == expected_top_slug
        score_ok = top_score >= expected_min_score
        note_ok = (not expected_note_id) or expected_note_id in matched_note_ids
        observed_ok = observed_routed and expectation_met and slug_ok and score_ok and note_ok

    return {
        "case_id": case_id,
        "case_type": case_type,
        "expected_ok": expected_ok,
        "observed_status": observed_status,
        "observed_top_slug": top_slug,
        "observed_top_score": top_score,
        "expectation_met": expectation_met,
        "observed_ok": observed_ok,
        "matched_note_ids": matched_note_ids,
        "match_breakdown": dict(rows[0].get("match_breakdown", {})) if rows else {},
    }


def build_result(input_path: str | Path) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.annex_knowledge_routing.build_result` into the payload
    shape expected by organs annex knowledge routing.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    cases = [case for _path, case in _fixture_cases(input_path)]
    rows = [_evaluate_case(case) for case in cases]

    positive_rows = [row for row in rows if row["case_type"] == "positive"]
    negative_rows = [row for row in rows if row["case_type"] == "negative"]
    positive_pass = all(row["observed_ok"] for row in positive_rows)
    negative_observed = all(row["observed_ok"] for row in negative_rows)
    negative_ids = {row["case_id"] for row in negative_rows}
    expected_negatives_present = set(EXPECTED_NEGATIVE_CASES).issubset(negative_ids)
    status = (
        "pass"
        if positive_rows
        and negative_rows
        and positive_pass
        and negative_observed
        and expected_negatives_present
        else "fail"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "status": status,
        "created_at": utc_now(),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "input_mode": "annex_knowledge_routing_fixture_cases",
        "case_count": len(rows),
        "positive_case_count": len(positive_rows),
        "negative_case_count": len(negative_rows),
        "passed_positive_case_count": sum(1 for row in positive_rows if row["observed_ok"]),
        "observed_negative_case_count": sum(1 for row in negative_rows if row["observed_ok"]),
        "expected_negative_cases": dict(EXPECTED_NEGATIVE_CASES),
        "cases": rows,
        "body_in_receipt": False,
    }


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.annex_knowledge_routing.result_card` into the payload
    shape expected by organs annex knowledge routing.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_board_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "case_count": result.get("case_count"),
        "positive_case_count": result.get("positive_case_count"),
        "negative_case_count": result.get("negative_case_count"),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
    }


def _validation_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.annex_knowledge_routing._validation_receipt` into the
    payload shape expected by organs annex knowledge routing.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_validation_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "receipt_paths": dict(receipt_paths),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _acceptance_receipt(result: Mapping[str, Any], receipt_paths: Mapping[str, str]) -> dict[str, Any]:
    """
    Serialize `microcosm_core.organs.annex_knowledge_routing._acceptance_receipt` into the
    payload shape expected by organs annex knowledge routing.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    return {
        "schema_version": f"{ORGAN_ID}_acceptance_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": result.get("status"),
        "fixture_id": FIXTURE_ID,
        "real_substrate_disposition": "real_substrate_capsule",
        "generated_receipts": list(receipt_paths.values()),
        "claim_ceiling": CLAIM_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }


def _receipt_ref(out: Path, name: str) -> str:
    """
    Return receipt ref for `microcosm_core.organs.annex_knowledge_routing`.

    Inputs are `out` and `name`; notable helpers are `as_posix`.
    """
    return (out / name).as_posix()


def run(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
    *,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    Return run for `microcosm_core.organs.annex_knowledge_routing`.

    Inputs are `input_path`, `out_dir`, `command`, and `acceptance_out`; notable helpers are
    `build_result`, `Path`, `mkdir`, `write_json_atomic`, and 5 more.
    """
    result = build_result(input_path)
    if command:
        result["command"] = command
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt_paths = {
        "result": _receipt_ref(out, RESULT_NAME),
        "board": _receipt_ref(out, BOARD_NAME),
        "validation": _receipt_ref(out, VALIDATION_RECEIPT_NAME),
    }
    write_json_atomic(out / RESULT_NAME, result)
    write_json_atomic(out / BOARD_NAME, result_card(result))
    write_json_atomic(out / VALIDATION_RECEIPT_NAME, _validation_receipt(result, receipt_paths))
    if acceptance_out is not None:
        acceptance_paths = {**receipt_paths, "acceptance": Path(acceptance_out).as_posix()}
        write_json_atomic(Path(acceptance_out), _acceptance_receipt(result, acceptance_paths))
    return result


def run_annex_knowledge_routing_bundle(
    input_path: str | Path,
    out_dir: str | Path,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Derive run annex knowledge routing bundle without touching module import state.

    Inputs are `input_path`, `out_dir`, and `command`; notable helpers are `run`.
    """
    return run(input_path, out_dir, command)


def build_parser() -> argparse.ArgumentParser:
    """
    Register CLI syntax for `microcosm_core.organs.annex_knowledge_routing.build_parser`.

    The function mutates the provided argparse object with this module's flags, subcommands,
    or defaults.
    """
    parser = argparse.ArgumentParser(
        description="Run the annex knowledge routing organ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "run-annex-knowledge-routing-bundle"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--input", required=True)
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--acceptance-out")
        subparser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the `microcosm_core.organs.annex_knowledge_routing` command-line entry point.

    It parses argv, invokes the file-local builders or validators, and returns a
    process-style status code.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command in {"run", "run-annex-knowledge-routing-bundle"}:
        result = run(args.input, args.out, acceptance_out=args.acceptance_out)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {result['status']} cases={result['case_count']}")
        return 0 if result["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
