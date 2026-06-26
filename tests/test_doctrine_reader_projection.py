"""Doctrine reader projection keeps website-grade doctrine navigable in-repo."""
from __future__ import annotations

from pathlib import Path

from microcosm_core.doctrine_reader_projection import (
    DOCTRINE_MARKDOWN_REL,
    READER_PROJECTION_REL,
    build_doctrine_reader_projection,
    render_doctrine_reader_markdown,
    validate_doctrine_reader_projection,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_doctrine_reader_projection_preserves_rich_facets() -> None:
    projection = build_doctrine_reader_projection(MICROCOSM_ROOT)
    by_id = {row["id"]: row for row in projection["records"]}
    ax9 = by_id["AX-9"]

    assert projection["status"] == "pass"
    assert projection["record_count"] == 49
    assert projection["source_of_record"]["semantic_source"] == "core/doctrine_enrichment.json"
    assert projection["publication_state"]["push_or_deploy_authorized"] is False
    assert projection["quality_contract"]["one_fact_one_owner"].startswith(
        "A semantic fact has one owner"
    )
    assert ax9["plain_meaning"]
    assert ax9["analogy"]["maps"]
    assert ax9["analogy"]["boundary"]
    assert ax9["formal_reading"]["symbols"]
    assert ax9["governs"] == "When a mutation is allowed to count as landed."
    assert ax9["scope_boundary"]


def test_doctrine_reader_markdown_and_json_are_current() -> None:
    validation = validate_doctrine_reader_projection(MICROCOSM_ROOT)
    assert validation["status"] == "pass", validation["errors"]
    assert validation["checked_surfaces"] == [
        READER_PROJECTION_REL,
        DOCTRINE_MARKDOWN_REL,
    ]


def test_doctrine_reader_markdown_renders_ax9_contract() -> None:
    projection = build_doctrine_reader_projection(MICROCOSM_ROOT, generated_at="check")
    markdown = render_doctrine_reader_markdown(projection)

    assert "# Plectis Doctrine" in markdown
    assert "Source of record: `core/doctrine_enrichment.json`" in markdown
    assert "## AX-9" in markdown
    assert "A change to the world only counts as done" in markdown
    assert "Boundary:" in markdown
