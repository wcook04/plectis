"""Build repository and agent-facing reader projections from doctrine enrichment.

The source of record is ``core/doctrine_enrichment.json``. This module emits
typed projections only: a JSON read model for tools and a Markdown reader for
cold humans/agents. Neither surface authorizes release, hosting, proof
correctness, or an authority flip away from the enrichment source.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from microcosm_core.resource_root import microcosm_root


ENRICHMENT_REL = "core/doctrine_enrichment.json"
READER_PROJECTION_REL = "core/doctrine_reader_projection.json"
DOCTRINE_MARKDOWN_REL = "DOCTRINE.md"
SOURCE_REF = f"{ENRICHMENT_REL}::records"
READER_SURFACE_SCHEMA = "plectis_doctrine_reader_projection_v1"

REQUIRED_READER_FACETS = (
    "canonical_statement",
    "plain_meaning",
    "analogy.text",
    "analogy.maps",
    "analogy.boundary",
    "significance",
    "common_misread",
    "formal.latex",
    "formal.reads",
    "formal.symbols",
    "governs",
    "requires",
    "refuses",
    "example",
    "counterexample",
    "enforcement",
    "scope_boundary",
    "owner",
    "basis_digest",
)

INSTANCE_PATH_BY_KIND = {
    "axiom": "axioms/{id}.json",
    "principle": "principles/{id}.json",
    "anti_principle": "anti_principles/{id}.json",
}


def _root(root: str | Path | None) -> Path:
    return Path(root).resolve() if root is not None else microcosm_root()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _id_sort_key(value: str) -> tuple[str, int, str]:
    prefix, _, suffix = value.partition("-")
    try:
        return prefix, int(suffix), value
    except ValueError:
        return prefix, 9999, value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _instance_ref(root: Path, record_id: str, kind: str) -> str | None:
    template = INSTANCE_PATH_BY_KIND.get(kind)
    if not template:
        return None
    rel = template.format(id=record_id)
    return rel if (root / rel).is_file() else None


def _instance_title(root: Path, record_id: str, kind: str) -> str | None:
    rel = _instance_ref(root, record_id, kind)
    if not rel:
        return None
    payload = _as_dict(_load_json(root / rel))
    title = str(payload.get("title") or "").strip()
    return title or None


def _record_source_ref(record_id: str) -> str:
    return f"{SOURCE_REF}[id={record_id}]"


def _field_presence(record: dict[str, Any]) -> dict[str, bool]:
    ladder = _as_dict(record.get("reader_ladder"))
    analogy = _as_dict(ladder.get("analogy"))
    formal = _as_dict(record.get("formal"))
    return {
        "canonical_statement": bool(str(record.get("one_line") or "").strip()),
        "plain_meaning": bool(str(ladder.get("plain") or "").strip()),
        "analogy.text": bool(str(analogy.get("text") or "").strip()),
        "analogy.maps": bool(_as_list(analogy.get("maps"))),
        "analogy.boundary": bool(str(analogy.get("boundary") or "").strip()),
        "significance": bool(str(ladder.get("why_it_matters") or "").strip()),
        "common_misread": bool(str(ladder.get("potential_misread") or "").strip()),
        "formal.latex": bool(str(formal.get("latex") or "").strip()),
        "formal.reads": bool(str(formal.get("reads") or "").strip()),
        "formal.symbols": bool(_as_list(formal.get("symbols"))),
        "governs": bool(str(record.get("governs") or "").strip()),
        "requires": bool(str(record.get("requires") or "").strip()),
        "refuses": bool(str(record.get("refuses") or "").strip()),
        "example": bool(str(_as_dict(record.get("example")).get("text") or "").strip()),
        "counterexample": bool(
            str(_as_dict(record.get("counterexample")).get("text") or "").strip()
        ),
        "enforcement": bool(_strings(record.get("enforced_in"))),
        "scope_boundary": bool(str(record.get("does_not_prove") or "").strip()),
        "owner": bool(str(record.get("kind") or "").strip()),
        "basis_digest": True,
    }


def _reader_record(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    record_id = str(record.get("id") or "").strip()
    kind = str(record.get("kind") or "").strip()
    ladder = _as_dict(record.get("reader_ladder"))
    analogy = _as_dict(ladder.get("analogy"))
    formal = _as_dict(record.get("formal"))
    example = _as_dict(record.get("example"))
    counterexample = _as_dict(record.get("counterexample"))
    source_ref = _record_source_ref(record_id)
    instance_ref = _instance_ref(root, record_id, kind)
    original_digest = _sha256_json(record)
    projected = {
        "id": record_id,
        "kind": kind,
        "title": _instance_title(root, record_id, kind) or record_id,
        "canonical_statement": str(record.get("one_line") or ""),
        "plain_meaning": str(ladder.get("plain") or ""),
        "analogy": {
            "text": str(analogy.get("text") or ""),
            "maps": [
                {
                    "doctrine": str(_as_dict(item).get("doctrine") or ""),
                    "analogy": str(_as_dict(item).get("analogy") or ""),
                }
                for item in _as_list(analogy.get("maps"))
            ],
            "boundary": str(analogy.get("boundary") or ""),
        },
        "significance": str(ladder.get("why_it_matters") or ""),
        "common_misread": str(ladder.get("potential_misread") or ""),
        "formal_reading": {
            "latex": str(formal.get("latex") or ""),
            "reads": str(formal.get("reads") or ""),
            "symbols": [
                {
                    "sym": str(_as_dict(item).get("sym") or ""),
                    "meaning": str(_as_dict(item).get("meaning") or ""),
                }
                for item in _as_list(formal.get("symbols"))
            ],
        },
        "governs": str(record.get("governs") or ""),
        "requires": str(record.get("requires") or ""),
        "refuses": str(record.get("refuses") or ""),
        "example": {
            "text": str(example.get("text") or ""),
            "refs": _strings(example.get("refs")),
        },
        "counterexample": {"text": str(counterexample.get("text") or "")},
        "enforced_in": _strings(record.get("enforced_in")),
        "scope_boundary": str(record.get("does_not_prove") or ""),
        "source": {
            "source_of_record": ENRICHMENT_REL,
            "source_ref": source_ref,
            "instance_ref": instance_ref,
            "source_authority": "core/doctrine_enrichment.json",
        },
        "owner": {
            "semantic_owner": ENRICHMENT_REL,
            "projection_owner": "microcosm_core.doctrine_reader_projection",
            "instance_owner": instance_ref,
        },
        "basis_digest": original_digest,
        "facet_presence": _field_presence(record),
    }
    projected["projection_digest"] = _sha256_json(projected)
    return projected


def _load_enrichment(root: Path) -> dict[str, Any]:
    return _as_dict(_load_json(root / ENRICHMENT_REL))


def build_doctrine_reader_projection(
    root: str | Path | None = None,
    *,
    generated_at: str | None = None,
    command: str = "python scripts/build_doctrine_projection.py --write-reader-surfaces",
) -> dict[str, Any]:
    resolved = _root(root)
    enrichment = _load_enrichment(resolved)
    records = [
        _reader_record(resolved, record)
        for record in _as_list(enrichment.get("records"))
        if isinstance(record, dict) and record.get("id")
    ]
    records = sorted(records, key=lambda row: _id_sort_key(str(row["id"])))
    incomplete = [
        {
            "id": row["id"],
            "missing_facets": [
                facet for facet in REQUIRED_READER_FACETS if not row["facet_presence"].get(facet)
            ],
        }
        for row in records
        if any(not row["facet_presence"].get(facet) for facet in REQUIRED_READER_FACETS)
    ]
    counts_by_kind: dict[str, int] = {}
    for row in records:
        counts_by_kind[row["kind"]] = counts_by_kind.get(row["kind"], 0) + 1
    return {
        "schema_version": READER_SURFACE_SCHEMA,
        "projection_id": "plectis_public_doctrine_reader_projection",
        "status": "pass" if not incomplete else "blocked",
        "authority_boundary": (
            "Generated reader projection from core/doctrine_enrichment.json. "
            "It improves repository and agent navigability but is not source "
            "authority, proof authority, hosted publication, release approval, "
            "or permission to hand-edit generated surfaces."
        ),
        "anti_claims": [
            "Semantic source of record remains core/doctrine_enrichment.json.",
            "DOCTRINE.md and this JSON are projections and may be regenerated.",
            "Local projection freshness does not imply the public website has been deployed.",
            "A readable analogy or formal gloss does not prove correctness or support strength.",
        ],
        "source_of_record": {
            "semantic_source": ENRICHMENT_REL,
            "records_ref": SOURCE_REF,
            "source_schema_version": enrichment.get("schema_version"),
            "source_authority_boundary": enrichment.get("authority_boundary"),
        },
        "generation": {
            "generated_at": generated_at or _now(),
            "generated_by": "microcosm_core.doctrine_reader_projection.build_doctrine_reader_projection",
            "command": command,
        },
        "publication_state": {
            "local_repo_projection": "generated_when_written",
            "public_website_projection": "separate_publication_state_not_asserted_here",
            "push_or_deploy_authorized": False,
        },
        "quality_contract": {
            "required_facets": list(REQUIRED_READER_FACETS),
            "semantic_parity_rule": (
                "Repository, agent, and website readers may render different profiles, "
                "but each must trace back to the same enrichment record and digest."
            ),
            "one_fact_one_owner": (
                "A semantic fact has one owner: core/doctrine_enrichment.json. "
                "Markdown, CLI packets, website HTML, and reader JSON are typed projections."
            ),
        },
        "projection_profiles": {
            "reference": {
                "surface": READER_PROJECTION_REL,
                "renders": "all records with all required facets plus digests",
                "authority_ceiling": "machine_read_model_not_source_authority",
            },
            "explanation": {
                "surface": DOCTRINE_MARKDOWN_REL,
                "renders": "human-readable sections for all records",
                "authority_ceiling": "repository_markdown_projection_not_source_authority",
            },
            "agent": {
                "surface": "plectis comprehend --slice doctrine [--doctrine <id>]",
                "renders": "bounded JSON packet from this reader projection",
                "authority_ceiling": "navigation_context_not_release_or_correctness_authority",
            },
            "website": {
                "surface": "public site doctrine pages",
                "renders": "site-specific HTML from the same enrichment model",
                "authority_ceiling": "published_projection_not_semantic_owner",
            },
        },
        "record_count": len(records),
        "counts_by_kind": counts_by_kind,
        "incomplete": incomplete,
        "records": records,
    }


def _md_list(items: list[str]) -> list[str]:
    return [f"- `{item}`" for item in items] if items else ["- none declared"]


def render_doctrine_reader_markdown(projection: dict[str, Any]) -> str:
    lines = [
        "# Plectis Doctrine",
        "",
        "_Generated projection. Do not edit by hand._",
        "",
        (
            "Source of record: `core/doctrine_enrichment.json`. This file is a "
            "repository reader surface; it does not authorize release, hosting, "
            "proof correctness, source mutation, or a semantic authority flip."
        ),
        "",
        "Regenerate with:",
        "",
        "```bash",
        "PYTHONPATH=src python3 scripts/build_doctrine_projection.py --write-reader-surfaces",
        "PYTHONPATH=src python3 scripts/build_doctrine_projection.py --check-reader-surfaces",
        "```",
        "",
        "## Reading Contract",
        "",
        projection["quality_contract"]["one_fact_one_owner"],
        "",
        projection["quality_contract"]["semantic_parity_rule"],
        "",
        f"Records: `{projection['record_count']}`.",
        "",
    ]
    for record in projection.get("records", []):
        lines.extend(
            [
                f"## {record['id']} - {record.get('title') or record['id']}",
                "",
                f"Kind: `{record['kind']}`",
                f"Source: `{record['source']['source_ref']}`",
                f"Instance: `{record['source'].get('instance_ref') or 'none'}`",
                f"Basis digest: `{record['basis_digest'][:16]}`",
                "",
                "### Statement",
                "",
                str(record.get("canonical_statement") or ""),
                "",
                "### Ordinary Reading",
                "",
                str(record.get("plain_meaning") or ""),
                "",
                "### Analogy",
                "",
                str(_as_dict(record.get("analogy")).get("text") or ""),
                "",
                "Maps:",
            ]
        )
        for mapping in _as_list(_as_dict(record.get("analogy")).get("maps")):
            lines.append(
                f"- {str(_as_dict(mapping).get('doctrine') or '')} -> "
                f"{str(_as_dict(mapping).get('analogy') or '')}"
            )
        lines.extend(
            [
                "",
                f"Boundary: {str(_as_dict(record.get('analogy')).get('boundary') or '')}",
                "",
                "### Why It Matters",
                "",
                str(record.get("significance") or ""),
                "",
                "Common misread:",
                "",
                str(record.get("common_misread") or ""),
                "",
                "### Formal Reading",
                "",
                "```text",
                str(_as_dict(record.get("formal_reading")).get("latex") or ""),
                "```",
                "",
                str(_as_dict(record.get("formal_reading")).get("reads") or ""),
                "",
                "Symbols:",
            ]
        )
        for symbol in _as_list(_as_dict(record.get("formal_reading")).get("symbols")):
            lines.append(
                f"- `{str(_as_dict(symbol).get('sym') or '')}`: "
                f"{str(_as_dict(symbol).get('meaning') or '')}"
            )
        lines.extend(
            [
                "",
                "### Governs / Requires / Refuses",
                "",
                f"Governs: {str(record.get('governs') or '')}",
                "",
                f"Requires: {str(record.get('requires') or '')}",
                "",
                f"Refuses: {str(record.get('refuses') or '')}",
                "",
                "### Examples",
                "",
                f"Example: {str(_as_dict(record.get('example')).get('text') or '')}",
                "",
                "Example refs:",
                *_md_list(_strings(_as_dict(record.get("example")).get("refs"))),
                "",
                f"Counterexample: {str(_as_dict(record.get('counterexample')).get('text') or '')}",
                "",
                "Enforced in:",
                *_md_list(_strings(record.get("enforced_in"))),
                "",
                "### Scope Boundary",
                "",
                str(record.get("scope_boundary") or ""),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_doctrine_reader_surfaces(
    root: str | Path | None = None,
    *,
    command: str = "python scripts/build_doctrine_projection.py --write-reader-surfaces",
) -> dict[str, Any]:
    resolved = _root(root)
    projection = build_doctrine_reader_projection(resolved, command=command)
    (resolved / READER_PROJECTION_REL).write_text(
        json.dumps(projection, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (resolved / DOCTRINE_MARKDOWN_REL).write_text(
        render_doctrine_reader_markdown(projection),
        encoding="utf-8",
    )
    return projection


def validate_doctrine_reader_projection(root: str | Path | None = None) -> dict[str, Any]:
    resolved = _root(root)
    expected = build_doctrine_reader_projection(
        resolved,
        generated_at="check",
        command="python scripts/build_doctrine_projection.py --write-reader-surfaces",
    )
    errors: list[dict[str, Any]] = []
    if expected["status"] != "pass":
        for row in expected["incomplete"]:
            errors.append(
                {
                    "code": "doctrine_reader_record_incomplete",
                    "path": f"{SOURCE_REF}[id={row['id']}]",
                    "message": "Doctrine enrichment record lacks one or more required reader facets.",
                    "missing_facets": row["missing_facets"],
                }
            )
    json_path = resolved / READER_PROJECTION_REL
    if not json_path.is_file():
        errors.append(
            {
                "code": "doctrine_reader_projection_missing",
                "path": READER_PROJECTION_REL,
                "message": "Generated doctrine reader projection JSON is missing.",
            }
        )
    else:
        actual = _as_dict(_load_json(json_path))
        if isinstance(actual.get("generation"), dict):
            actual["generation"]["generated_at"] = "check"
        if actual != expected:
            errors.append(
                {
                    "code": "doctrine_reader_projection_stale",
                    "path": READER_PROJECTION_REL,
                    "message": "Doctrine reader projection is not reproducible from core/doctrine_enrichment.json.",
                }
            )
    md_path = resolved / DOCTRINE_MARKDOWN_REL
    expected_md = render_doctrine_reader_markdown(expected)
    if not md_path.is_file():
        errors.append(
            {
                "code": "doctrine_reader_markdown_missing",
                "path": DOCTRINE_MARKDOWN_REL,
                "message": "Generated repository doctrine Markdown is missing.",
            }
        )
    elif md_path.read_text(encoding="utf-8") != expected_md:
        errors.append(
            {
                "code": "doctrine_reader_markdown_stale",
                "path": DOCTRINE_MARKDOWN_REL,
                "message": "Repository doctrine Markdown is not reproducible from the reader projection.",
            }
        )
    by_id = {str(row.get("id")): row for row in expected.get("records", [])}
    ax9 = _as_dict(by_id.get("AX-9"))
    if not _as_dict(ax9.get("analogy")).get("boundary") or not _as_list(
        _as_dict(ax9.get("formal_reading")).get("symbols")
    ):
        errors.append(
            {
                "code": "doctrine_reader_ax9_contract_missing",
                "path": f"{READER_PROJECTION_REL}::records[AX-9]",
                "message": "AX-9 must retain analogy boundary and formal symbol readings.",
            }
        )
    return {
        "schema_version": "plectis_doctrine_reader_projection_validation_v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "record_count": expected.get("record_count"),
        "source_of_record": ENRICHMENT_REL,
        "checked_surfaces": [READER_PROJECTION_REL, DOCTRINE_MARKDOWN_REL],
    }
