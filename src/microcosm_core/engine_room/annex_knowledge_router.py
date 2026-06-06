"""Public-safe annex knowledge router capsule.

This is a source-faithful public refactor of
`system/lib/annex_registry.py::route_annexes`. It preserves the tiered routing
shape: structured routing fields score highest, family text and open-first
summaries provide weaker evidence, and curated notes add explainable supporting
matches.

The capsule routes over a sanitized in-memory catalog. It does not clone third
party repositories, does not ship the private annex corpus, and does not claim
BM25, TF-IDF, embeddings, semantic search, or license-review authority.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_annex_knowledge_router_v1"
ORGAN_ID = "engine_room_annex_knowledge_router"
SOURCE_REFS = ("system/lib/annex_registry.py::route_annexes", "annex_import.py route")
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Explainable tiered weighted-token retrieval over a sanitized annex catalog. "
    "It is not BM25, not TF-IDF, not embedding search, not repository cloning, "
    "and not license or provenance authority."
)
ANTI_CLAIMS = (
    "not_bm25",
    "not_tfidf",
    "not_embedding_search",
    "not_repository_cloner",
    "not_license_authority",
)

ROUTE_MATCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "with",
}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _normalized_query_text(value: Any) -> str:
    lowered = _string(value).lower()
    lowered = re.sub(r"[_/]+", " ", lowered)
    lowered = lowered.replace("-", " ")
    lowered = re.sub(r"[^\w\s]", " ", lowered)
    return " ".join(lowered.split())


def _query_tokens(value: Any) -> list[str]:
    return [
        token
        for token in _normalized_query_text(value).split()
        if token and token not in ROUTE_MATCH_STOPWORDS
    ]


def _dedupe_preserving_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _coerce_routing_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return _dedupe_preserving_order([_string(item) for item in value if _string(item)])


def _family_routing(family: Mapping[str, Any]) -> dict[str, list[str]]:
    routing = dict(family.get("routing") or {}) if isinstance(family.get("routing"), Mapping) else {}
    return {
        "domains": _coerce_routing_list(routing.get("domains")),
        "clusters": _coerce_routing_list(routing.get("clusters")),
        "problem_spaces": _coerce_routing_list(routing.get("problem_spaces")),
        "status": _coerce_routing_list(routing.get("status")),
    }


def _note_routing(note: Mapping[str, Any]) -> dict[str, list[str]]:
    routing = dict(note.get("routing") or {}) if isinstance(note.get("routing"), Mapping) else {}
    return {
        "problem_spaces": _coerce_routing_list(routing.get("problem_spaces")),
        "capabilities": _coerce_routing_list(routing.get("capabilities")),
    }


def _relevance_value(note: Mapping[str, Any]) -> int:
    try:
        value = int(note.get("relevance"))
    except (TypeError, ValueError):
        return 50
    return max(0, min(100, value))


def sort_notes_by_relevance(notes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(note) for note in notes]
    return sorted(rows, key=lambda note: (-_relevance_value(note), str(note.get("id") or "")))


def _route_match_score(
    query: str,
    candidate: str,
    *,
    exact_weight: int,
    phrase_weight: int,
    token_weight: int,
) -> int:
    normalized_query = _normalized_query_text(query)
    normalized_candidate = _normalized_query_text(candidate)
    if not normalized_query or not normalized_candidate:
        return 0
    if normalized_query == normalized_candidate:
        return exact_weight
    if normalized_query in normalized_candidate:
        return phrase_weight
    query_terms = _query_tokens(normalized_query)
    candidate_terms = set(_query_tokens(normalized_candidate))
    overlap = sum(1 for token in query_terms if token in candidate_terms)
    return overlap * token_weight


def _routing_summary_from_family(overview: Mapping[str, Any]) -> dict[str, Any]:
    existing = overview.get("routing_summary")
    if isinstance(existing, Mapping):
        return dict(existing)
    family = _family_routing(overview)
    notes = overview.get("notes") if isinstance(overview.get("notes"), list) else []
    problem_spaces = list(family["problem_spaces"])
    capabilities: list[str] = []
    matched_note_ids: list[str] = []
    for note in notes:
        if not isinstance(note, Mapping):
            continue
        note_routing = _note_routing(note)
        problem_spaces.extend(note_routing["problem_spaces"])
        capabilities.extend(note_routing["capabilities"])
        if note_routing["problem_spaces"] or note_routing["capabilities"]:
            note_id = _string(note.get("id"))
            if note_id:
                matched_note_ids.append(note_id)
    return {
        "domains": family["domains"],
        "clusters": family["clusters"],
        "problem_spaces": _dedupe_preserving_order(problem_spaces),
        "status": family["status"],
        "capabilities": _dedupe_preserving_order(capabilities),
        "matched_note_ids": _dedupe_preserving_order(matched_note_ids),
    }


def route_annexes(
    problem: str,
    *,
    catalog: Mapping[str, Any],
    domain: str | None = None,
    cluster: str | None = None,
    include_notes: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Rank sanitized annex rows for a problem statement."""

    normalized_problem = _normalized_query_text(problem)
    if not normalized_problem:
        return []
    domain_norm = _normalized_query_text(domain or "")
    cluster_norm = _normalized_query_text(cluster or "")
    results: list[dict[str, Any]] = []

    for overview in catalog.get("annexes", []):
        if not isinstance(overview, Mapping):
            continue
        slug = _string(overview.get("slug"))
        if not slug:
            continue
        routing_summary = _routing_summary_from_family(overview)
        domains = [str(item) for item in routing_summary.get("domains") or [] if _string(item)]
        clusters = [str(item) for item in routing_summary.get("clusters") or [] if _string(item)]
        if domain_norm and all(_normalized_query_text(item) != domain_norm for item in domains):
            continue
        if cluster_norm and all(_normalized_query_text(item) != cluster_norm for item in clusters):
            continue

        structured = 0
        family_text = 0
        open_first = 0
        notes_score = 0
        matched_note_ids: list[str] = []

        structured_fields = [
            *(routing_summary.get("problem_spaces") or []),
            *(routing_summary.get("capabilities") or []),
            *(routing_summary.get("domains") or []),
            *(routing_summary.get("clusters") or []),
        ]
        for field in structured_fields:
            structured = max(
                structured,
                _route_match_score(
                    normalized_problem,
                    str(field),
                    exact_weight=120,
                    phrase_weight=80,
                    token_weight=18,
                ),
            )

        family_fields = [
            overview.get("slug"),
            overview.get("display_name"),
            overview.get("description"),
            " ".join(str(item) for item in overview.get("tags") or []),
        ]
        for field in family_fields:
            family_text = max(
                family_text,
                _route_match_score(
                    normalized_problem,
                    str(field or ""),
                    exact_weight=32,
                    phrase_weight=24,
                    token_weight=6,
                ),
            )

        for row in overview.get("open_first") or []:
            if not isinstance(row, Mapping):
                continue
            open_first = max(
                open_first,
                _route_match_score(
                    normalized_problem,
                    str(row.get("summary") or ""),
                    exact_weight=20,
                    phrase_weight=16,
                    token_weight=4,
                ),
            )

        if include_notes:
            notes = [note for note in overview.get("notes") or [] if isinstance(note, Mapping)]
            for note in sort_notes_by_relevance(notes):
                note_routing = _note_routing(note)
                note_fields = [
                    str(note.get("note") or ""),
                    " ".join(note_routing["problem_spaces"]),
                    " ".join(note_routing["capabilities"]),
                ]
                best_note_score = 0
                for field in note_fields:
                    best_note_score = max(
                        best_note_score,
                        _route_match_score(
                            normalized_problem,
                            field,
                            exact_weight=18,
                            phrase_weight=12,
                            token_weight=3,
                        ),
                    )
                if best_note_score:
                    notes_score = max(notes_score, best_note_score)
                    note_id = _string(note.get("id"))
                    if note_id:
                        matched_note_ids.append(note_id)

        total_score = structured + family_text + open_first + notes_score
        if total_score <= 0:
            continue
        results.append(
            {
                "slug": slug,
                "display_name": overview.get("display_name") or slug,
                "score": total_score,
                "match_breakdown": {
                    "structured": structured,
                    "family_text": family_text,
                    "open_first": open_first,
                    "notes": notes_score,
                },
                "matched_note_ids": _dedupe_preserving_order(matched_note_ids)[:8],
                "routing_summary": routing_summary,
                "description": overview.get("description") or "",
                "tags": list(overview.get("tags") or []),
                "source_kind": overview.get("source_kind") or "",
            }
        )

    ranked = sorted(results, key=lambda row: (-int(row.get("score") or 0), str(row.get("slug") or "")))
    return ranked[: max(1, int(limit))] if limit else ranked


def route_catalog(
    catalog: Mapping[str, Any],
    *,
    problem: str,
    domain: str | None = None,
    cluster: str | None = None,
    include_notes: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = route_annexes(
        problem,
        catalog=catalog,
        domain=domain,
        cluster=cluster,
        include_notes=include_notes,
        limit=limit,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "status": "routed" if rows else "no_match",
        "problem": problem,
        "domain_filter": domain,
        "cluster_filter": cluster,
        "row_count": len(rows),
        "rows": rows,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
    }


def evaluate_case(case: Mapping[str, Any], *, path: str = "") -> dict[str, Any]:
    catalog = case.get("catalog") if isinstance(case.get("catalog"), Mapping) else {}
    receipt = route_catalog(
        catalog,
        problem=str(case.get("problem") or ""),
        domain=case.get("domain") if case.get("domain") is not None else None,
        cluster=case.get("cluster") if case.get("cluster") is not None else None,
        include_notes=bool(case.get("include_notes", True)),
        limit=case.get("limit") if case.get("limit") is not None else None,
    )
    rows = receipt["rows"]
    expected_top_slug = _string(case.get("expected_top_slug"))
    expected_status = _string(case.get("expected_status")) or ("routed" if expected_top_slug else "no_match")
    expected_note_id = _string(case.get("expected_note_id"))
    min_score = int(case.get("expected_min_score") or 0)
    top_slug = _string(rows[0].get("slug")) if rows else ""
    top_score = int(rows[0].get("score") or 0) if rows else 0
    note_ok = True
    if expected_note_id:
        note_ok = bool(rows and expected_note_id in rows[0].get("matched_note_ids", []))
    expectation_met = (
        receipt["status"] == expected_status
        and (not expected_top_slug or top_slug == expected_top_slug)
        and top_score >= min_score
        and note_ok
    )
    return {
        "case_id": str(case.get("case_id") or Path(path).stem),
        "path": path,
        "expected_status": expected_status,
        "observed_status": receipt["status"],
        "expected_top_slug": expected_top_slug,
        "observed_top_slug": top_slug,
        "expectation_met": expectation_met,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} did not contain a JSON object")
        cases.append(evaluate_case(payload, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engine Room annex knowledge router capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser("route", help="Route one problem through a sanitized catalog.")
    route.add_argument("--catalog", required=True)
    route.add_argument("--problem", required=True)
    route.add_argument("--domain", default=None)
    route.add_argument("--cluster", default=None)
    route.add_argument("--limit", type=int, default=None)
    route.add_argument("--no-notes", action="store_true")
    route.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "route":
        payload = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            print("catalog must be a JSON object", file=__import__("sys").stderr)
            return 2
        receipt = route_catalog(
            payload,
            problem=args.problem,
            domain=args.domain,
            cluster=args.cluster,
            include_notes=not bool(args.no_notes),
            limit=args.limit,
        )
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            top = receipt["rows"][0]["slug"] if receipt["rows"] else "none"
            print(f"{ORGAN_ID}: {receipt['status']} top={top}")
        return 0 if receipt["status"] == "routed" else 1
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
