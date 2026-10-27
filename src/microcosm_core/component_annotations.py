"""Validate explicit review and clause mappings without inferring claim coverage.

Optional authored records are collected at build time. Runtime readers only
check these detached values, their target identities and their evidence links.
"""
from __future__ import annotations

from datetime import date, datetime
import copy
import hashlib
import re


def claim_text_sha256(claim):
    return hashlib.sha256(claim["claim_ceiling"].encode("utf-8")).hexdigest()


def validate_annotations(index):
    from microcosm_core.component_index import _keys, _path, _safe

    extension = index.get("explorer", {})
    reviews = extension.get("requirements_reviews", [])
    mappings = extension.get("claim_clause_coverage", [])
    if type(reviews) is not list or len(reviews) > 1000 or type(mappings) is not list or len(mappings) > 1000:
        raise ValueError("unbounded claim annotations")
    claims = {row["organ_id"]: row for row in index["nodes"]["claim"]}
    targets = {row["claim_id"] for row in claims.values()} | {
        row["subclaim_id"] for row in index["nodes"]["subclaim"]}
    facts = {row["artifact_id"]: row for row in index["nodes"]["artifact"]}
    _safe({"reviews": reviews, "mappings": mappings})

    def text(value, limit=2000):
        if type(value) is not str or not value.strip() or len(value) > limit:
            raise ValueError("invalid annotation text")

    def refs(values, required=False):
        if type(values) is not list or len(values) > 50 or any(type(value) is not str for value in values) or len(set(values)) != len(values) or (required and not values):
            raise ValueError("invalid annotation evidence")
        for ref in values:
            _path(ref)
            if ref not in facts or facts[ref]["availability"] != "available":
                raise ValueError("annotation evidence must name an available indexed artifact")

    seen = set()
    for row in reviews:
        _keys(row, {"review_id", "target_id", "requirement", "reviewer", "reviewed_at", "outcome", "limits", "evidence_refs"}, "requirements review")
        identity = row["review_id"]
        if type(identity) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,99}", identity) or identity in seen:
            raise ValueError("invalid requirements review identity")
        seen.add(identity)
        if type(row["target_id"]) is not str or type(row["outcome"]) is not str or row["target_id"] not in targets or row["outcome"] not in {"adequate_for_stated_requirement", "requires_revision", "inconclusive"}:
            raise ValueError("invalid review target or outcome")
        for field in ("requirement", "reviewer", "reviewed_at", "limits"):
            text(row[field])
        try:
            value = row["reviewed_at"]
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                date.fromisoformat(value)
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                raise ValueError("review date must be ISO date or timezone-qualified timestamp")
        except ValueError as exc:
            raise ValueError("invalid requirements review date") from exc
        refs(row["evidence_refs"], required=True)

    seen = set()
    for row in mappings:
        _keys(row, {"component_id", "claim_text_sha256", "clauses"}, "claim clause mapping")
        identity = row["component_id"]
        if type(identity) is not str or identity not in claims or identity in seen or row["claim_text_sha256"] != claim_text_sha256(claims[identity]):
            raise ValueError("stale or unknown claim clause mapping")
        seen.add(identity)
        clauses = row["clauses"]
        if type(clauses) is not list or not 1 <= len(clauses) <= 100:
            raise ValueError("invalid clause collection")
        ids = set()
        for clause in clauses:
            _keys(clause, {"clause_id", "text", "evidence_refs", "limits"}, "claim clause")
            text(clause["clause_id"], 100)
            if clause["clause_id"] in ids:
                raise ValueError("duplicate clause identity")
            ids.add(clause["clause_id"])
            text(clause["text"])
            text(clause["limits"])
            refs(clause["evidence_refs"])


def component_annotation_view(index, component_id):
    claim = next(row for row in index["nodes"]["claim"] if row["organ_id"] == component_id)
    extension = index.get("explorer", {})
    targets = {claim["claim_id"], *claim["card"]["formal_subclaim_ids"]}
    reviews = [row for row in extension.get("requirements_reviews", []) if row["target_id"] in targets]
    mapping = next((row for row in extension.get("claim_clause_coverage", []) if row["component_id"] == component_id), None)
    return {"requirements_reviews": {"status": "recorded" if reviews else "unrecorded", "records": copy.deepcopy(reviews)},
            "claim_clause_coverage": {"status": "recorded_mapping" if mapping else "unknown",
                                      "claim_text_sha256": claim_text_sha256(claim),
                                      "clauses": copy.deepcopy(mapping["clauses"]) if mapping else [],
                                      "mapped_clause_count": sum(bool(row["evidence_refs"]) for row in mapping["clauses"]) if mapping else None,
                                      "whole_claim_coverage": "unknown"}}
