"""
[PURPOSE]
- Teleology: Pin the EmbeddingSubstrate contract: content-hash-gated upserts, schema-hash drift re-embed, deterministic cosine ranking, disk persistence across instances.
- Mechanism: Injects a fake embed function so tests never hit the network; validates refresh bookkeeping + search + status + schema-drift re-embed without requiring NVIDIA credentials.

[INTERFACE]
- Exports: none (pytest discovery only).
- Reads: nothing on disk beyond tmp_path fixtures.
- Writes: tmp_path only.

[FLOW]
- Build fake adapter -> fake embed_fn -> run refresh -> assert counts + vectors -> re-run and assert no re-embed -> mutate one item + re-run -> assert exactly one re-embed -> search -> assert ranking.

[DEPENDENCIES]
- Required:
  - pytest (test runner)
  - system.lib.embedding_substrate

[CONSTRAINTS]
- Guarantee: tests never hit the network; fake embed_fn is pure and deterministic.
- Non-goal: does not exercise NVIDIA NIM or the pipeline CLI.
- Scope: library-level invariants only.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from system.lib.embedding_sources import build_adapter
from system.lib.embedding_substrate import (
    EmbeddingSubstrate,
    FacetedItem,
    MAX_EMBED_TEXT_CHARS,
    SourceAdapter,
)


def _fake_embed(texts):
    out = []
    for text in texts:
        keywords = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
        vec = [1.0 if kw in text else 0.0 for kw in keywords]
        if not any(vec):
            vec[0] = 0.1
        out.append(vec)
    return out


def _item(id_, **facets):
    return FacetedItem(id=id_, source_path=f"{id_}.txt", facets=facets, metadata={"kind": "toy"})


class ToyAdapter(SourceAdapter):
    source_kind = "toy"

    def __init__(self, items, schema_hash="schema-v1"):
        self._items = items
        self._schema_hash = schema_hash

    def iter_items(self):
        for item in self._items:
            yield item

    def schema_hash(self):
        return self._schema_hash


def _substrate(tmp_path):
    return EmbeddingSubstrate(tmp_path, state_root="state/embeddings", embed_fn=_fake_embed)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_refresh_embeds_all_facet_rows(tmp_path):
    adapter = ToyAdapter([
        _item("a", title="alpha", statement="alpha beta"),
        _item("b", title="beta", statement="gamma"),
    ])
    sub = _substrate(tmp_path)
    report = sub.refresh(adapter)
    assert report["embedded"] == 4  # 2 items × 2 facets each
    assert report["total_records"] == 4
    assert sorted(report["facets_seen"]) == ["statement", "title"]


def test_refresh_is_content_hash_gated_per_facet(tmp_path):
    adapter = ToyAdapter([_item("a", title="alpha", statement="alpha gamma")])
    sub = _substrate(tmp_path)
    sub.refresh(adapter)
    second = sub.refresh(adapter)
    assert second["embedded"] == 0
    assert second["kept"] == 2


def test_changing_one_facet_reembeds_only_that_facet(tmp_path):
    adapter1 = ToyAdapter([_item("a", title="alpha", statement="beta")])
    sub = _substrate(tmp_path)
    sub.refresh(adapter1)
    adapter2 = ToyAdapter([_item("a", title="alpha", statement="gamma delta")])
    report = sub.refresh(adapter2)
    assert report["embedded"] == 1  # only statement changed
    assert report["kept"] == 1  # title stayed the same


def test_schema_drift_forces_full_reembed(tmp_path):
    items = [_item("a", title="alpha")]
    sub = _substrate(tmp_path)
    sub.refresh(ToyAdapter(items, schema_hash="v1"))
    report = sub.refresh(ToyAdapter(items, schema_hash="v2"))
    assert report["embedded"] == 1
    assert report["schema_hash"] == "v2"


class ToyTextVersionAdapter(SourceAdapter):
    """Adapter that uses text_version (no schema_hash) to gate re-embed."""

    source_kind = "toy_versioned"

    def __init__(self, items, text_version):
        self._items = items
        self.text_version = text_version

    def iter_items(self):
        for item in self._items:
            yield item


def test_text_version_drift_forces_full_reembed(tmp_path):
    items = [_item("a", title="alpha"), _item("b", title="beta")]
    sub = _substrate(tmp_path)
    first = sub.refresh(ToyTextVersionAdapter(items, text_version="v1"))
    assert first["embedded"] == 2
    assert first["text_version"] == "v1"
    # No drift: same text_version + same content_hash -> 0 re-embeds
    second = sub.refresh(ToyTextVersionAdapter(items, text_version="v1"))
    assert second["embedded"] == 0
    assert second["kept"] == 2
    # Bump text_version -> all rows re-embed even though content_hash unchanged
    third = sub.refresh(ToyTextVersionAdapter(items, text_version="v2"))
    assert third["embedded"] == 2
    assert third["text_version"] == "v2"


def test_text_version_none_to_value_does_not_force_drift(tmp_path):
    """Conservative semantics: opting in (None -> v1) is not drift; only v1 -> v2 is."""
    items = [_item("a", title="alpha")]
    sub = _substrate(tmp_path)
    first = sub.refresh(ToyTextVersionAdapter(items, text_version=None))
    assert first["embedded"] == 1
    assert first["text_version"] is None
    # Adapter opts in to text_version="v1" — content unchanged, gate still says no drift
    second = sub.refresh(ToyTextVersionAdapter(items, text_version="v1"))
    assert second["embedded"] == 0  # opt-in is not drift; rows survive
    assert second["text_version"] == "v1"
    # Now real drift: v1 -> v2 with both sides non-None
    third = sub.refresh(ToyTextVersionAdapter(items, text_version="v2"))
    assert third["embedded"] == 1
    assert third["text_version"] == "v2"


def test_opt_in_adapters_carry_text_version_v1():
    """All adapters lacking a schema_hash escape hatch must opt in to text_version='v1'.

    Adapters that already define schema_hash() (DoctrineSource, StandardsJsonFacetedSource,
    AnnexNotesSource, RawSeedNavigationSource, PythonHolographicSource) do NOT need
    text_version because their drift signal already exists. The 5 below have no schema_hash,
    so text_version is their only extraction-logic-versioning escape hatch.
    """
    from system.lib.embedding_sources import (
        ArchaeologyShardSource,
        PaperModuleSource,
        RawSeedParagraphSource,
        RawSeedShardSource,
        SkillSource,
    )

    assert PaperModuleSource.text_version == "v1"
    assert SkillSource.text_version == "v1"
    assert RawSeedShardSource.text_version == "v1"
    assert RawSeedParagraphSource.text_version == "v1"
    assert ArchaeologyShardSource.text_version == "v1"


def test_substrate_status_carries_text_version(tmp_path):
    items = [_item("a", title="alpha")]
    sub = _substrate(tmp_path)
    sub.refresh(ToyTextVersionAdapter(items, text_version="v1"))
    status = sub.status(ToyTextVersionAdapter(items, text_version="v1"))
    assert status.text_version == "v1"


def test_search_scopes_by_facet(tmp_path):
    adapter = ToyAdapter([
        _item("a", title="alpha", statement="zeta"),
        _item("b", title="zeta", statement="alpha"),
    ])
    sub = _substrate(tmp_path)
    sub.refresh(adapter)
    title_hits = sub.search("alpha", source_kinds=["toy"], facets=["title"], top_k=5)
    assert title_hits[0].record.id == "a"
    assert title_hits[0].record.facet == "title"
    statement_hits = sub.search("alpha", source_kinds=["toy"], facets=["statement"], top_k=5)
    assert statement_hits[0].record.id == "b"
    assert statement_hits[0].record.facet == "statement"


def test_search_ladder_narrows_via_activation_gradient(tmp_path):
    adapter = ToyAdapter([
        _item("alpha_doc", title="alpha", statement="zeta"),
        _item("alpha_decoy", title="alpha", statement="epsilon"),
        _item("beta_doc", title="beta", statement="zeta"),
    ])
    sub = _substrate(tmp_path)
    sub.refresh(adapter)
    ladder = sub.search_ladder(
        "alpha zeta",
        source_kinds=["toy"],
        ladder=["title", "statement"],
        k_per_rung=[2, 1],
    )
    assert len(ladder.rung_trace) == 2
    assert ladder.final_hits[0].record.id == "alpha_doc"


def test_alignment_emits_per_facet_pair_scores(tmp_path):
    adapter = ToyAdapter([
        _item("a", title="alpha", statement="alpha beta"),
        _item("b", title="alpha gamma", statement="zeta"),
    ])
    sub = _substrate(tmp_path)
    sub.refresh(adapter)
    pairs = sub.alignment("a", "b", source_kinds=["toy"])
    same_axis_titles = next(p for p in pairs if p.facet_a == "title" and p.facet_b == "title")
    assert same_axis_titles.same_axis is True
    # title vs title for ("alpha" vs "alpha gamma") should be > 0
    assert same_axis_titles.score > 0


def test_status_reports_stale_count_across_facets(tmp_path):
    adapter = ToyAdapter([_item("a", title="alpha", statement="beta")])
    sub = _substrate(tmp_path)
    sub.refresh(adapter)
    mutated = ToyAdapter([
        _item("a", title="alpha", statement="zeta"),  # statement drifted
        _item("b", title="beta", statement="gamma"),  # whole new item
    ])
    status = sub.status(mutated)
    assert status.record_count == 2
    # a.statement drifted; b.title and b.statement missing -> 3
    assert status.stale_or_missing == 3
    assert status.facet_count == 2
    assert [row["reason"] for row in status.stale_preview] == [
        "hash_changed",
        "missing",
        "missing",
    ]
    assert status.stale_preview[0]["id"] == "a"
    assert status.stale_preview[0]["facet"] == "statement"
    assert status.stale_preview[0]["source_path"] == "a.txt"
    limited = sub.status(mutated, stale_preview_limit=2)
    assert len(limited.stale_preview) == 2
    assert limited.stale_preview_truncated is True


def test_fast_status_short_circuits_empty_cache_scan(tmp_path):
    class ExplodingAdapter(SourceAdapter):
        source_kind = "cold"

        def iter_items(self):
            raise AssertionError("fast status should not scan adapter items for an empty cache")

        def schema_hash(self):
            return "schema-v1"

    sub = _substrate(tmp_path)
    status = sub.status(ExplodingAdapter(), fast=True)
    assert status.record_count == 0
    assert status.stale_or_missing == 1
    assert status.stale_or_missing_is_estimate is True
    assert status.stale_preview[0]["reason"] == "cache_missing_or_empty_fast_estimate"
    assert status.facet_count == 0


def test_refresh_clips_overlong_text_before_embedding_but_hashes_original(tmp_path):
    seen: list[str] = []

    def embed_fn(texts):
        seen.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]

    long_text = " ".join(f"token_{index}" for index in range(2500))
    adapter = ToyAdapter([_item("a", body=long_text)])
    substrate = EmbeddingSubstrate(tmp_path, state_root="state/embeddings", embed_fn=embed_fn)

    report = substrate.refresh(adapter)
    assert report["embedded"] == 1
    assert len(seen) == 1
    assert seen[0] != long_text
    assert len(seen[0]) <= MAX_EMBED_TEXT_CHARS

    data = substrate.load("toy")
    record = data["records"][0]
    assert record["content_hash"] == hashlib.sha256(long_text.encode("utf-8")).hexdigest()
    assert record["metadata"]["embedding_text_truncated"] is True
    assert record["text_preview"] == seen[0][:400]


def test_refresh_retries_with_smaller_text_when_provider_rejects_length(tmp_path):
    attempts: list[int] = []

    def embed_fn(texts):
        for text in texts:
            attempts.append(len(text))
            if len(text) > 2000:
                raise RuntimeError("Input length 4303 exceeds maximum allowed token size 4096")
        return [[1.0, 0.0] for _ in texts]

    long_text = " ".join(f"token_{index}" for index in range(2500))
    adapter = ToyAdapter([_item("a", body=long_text)])
    substrate = EmbeddingSubstrate(tmp_path, state_root="state/embeddings", embed_fn=embed_fn)

    report = substrate.refresh(adapter)
    assert report["embedded"] == 1
    assert attempts[0] > 2000
    assert attempts[-1] <= 2000


def test_raw_seed_navigation_source_indexes_runtime_groups(tmp_path):
    family_dir = tmp_path / "obsidian/okay lets do this/09 - Demo"
    runtime_path = family_dir / "raw_seed/raw_seed_navigation_runtime.json"
    _write_json(
        family_dir / "phase_family.json",
        {
            "family_number": "09",
            "family_dir": "obsidian/okay lets do this/09 - Demo",
        },
    )
    _write_json(
        runtime_path,
        {
            "kind": "raw_seed_navigation_runtime",
            "family": {"family_number": "09"},
            "groups": [
                {
                    "group_id": "grp_kernel_navigation",
                    "title": "Kernel Navigation",
                    "gloss": "Expose grouped response facts through the kernel.",
                    "paragraph_ids_top": ["par_demo_001"],
                    "keyword_hints_top": ["grouped", "facts"],
                    "mechanism_hints_top": ["observe plan"],
                    "source_sections_top": [{"heading": "Bridge facts", "section_path": "demo/bridge-facts"}],
                    "representative_shards": [
                        {
                            "id": "atom_demo",
                            "statement": "The kernel should expose facts by pass and group.",
                            "voice_anchor": "give me all facts from pass 2",
                        }
                    ],
                    "neighbor_groups_top": [{"group_id": "grp_observe_apply_loop"}],
                    "target_cards_top": [{"target_key": "principle:pri_demo"}],
                    "compression": {
                        "compression_mode": "adaptive_seed",
                        "seed_sentences": ["Cached seed sentence for local lookup."],
                        "why_this_size": "Small enough for heartbeat.",
                        "neighbor_group_ids": ["grp_observe_apply_loop"],
                        "paragraph_ref_ids": ["par_demo_001"],
                        "target_keys": ["principle:pri_demo"],
                        "source_result_path": "state/demo/local_nvidia_compression.json",
                    },
                    "entrypoint": {
                        "is_starting_group": True,
                        "why_start_here": "This is the lookup seam.",
                        "next_group_ids": ["grp_observe_apply_loop"],
                    },
                    "commands": {"open_group": "python3 kernel.py --raw-seed-navigation-runtime 09 --raw-seed-nav-group grp_kernel_navigation"},
                }
            ],
        },
    )

    adapter = build_adapter("raw_seed_navigation", tmp_path)
    items = list(adapter.iter_items())

    assert len(items) == 1
    item = items[0]
    assert item.id == "family_09__grp_kernel_navigation"
    assert item.source_path.endswith("raw_seed_navigation_runtime.json")
    assert item.facets["compression"].startswith("Cached seed sentence")
    assert "observe plan" in item.facets["graph_context"]
    assert "atom_demo" in item.facets["lineage"]
    assert item.metadata["group_id"] == "grp_kernel_navigation"
    assert item.metadata["cached"] is True


def test_std_python_atom_parser_splits_contract_atoms():
    from system.lib.embedding_sources import parse_std_python_atoms

    docstring = """
[PURPOSE]
- Teleology: Do the thing.
- Mechanism: Read disk.
- Guarantee: Returns int.

[INTERFACE]
- Exports: foo, bar.
- Reads: state/x.json.
- Writes: state/y.json.

[CONSTRAINTS]
- Non-goal: not for production.
- Couples: system.lib.other.
"""
    atoms = parse_std_python_atoms(docstring)
    assert atoms.get("teleology", "").startswith("Do the thing")
    assert atoms.get("mechanism") == "Read disk."
    assert atoms.get("guarantee") == "Returns int."
    assert "foo, bar" in atoms.get("interface", "")
    assert atoms.get("reads") == "state/x.json."
    assert atoms.get("writes") == "state/y.json."
    assert atoms.get("non_goal") == "not for production."
    assert atoms.get("couples") == "system.lib.other."


def test_atomic_write_persists_across_instances(tmp_path):
    adapter = ToyAdapter([_item("a", title="alpha", statement="beta")])
    _substrate(tmp_path).refresh(adapter)
    sub2 = _substrate(tmp_path)
    data = sub2.load("toy")
    assert len(data["records"]) == 2
    facets = {r["facet"] for r in data["records"]}
    assert facets == {"title", "statement"}


def test_doctrine_source_emits_expanded_json_facets(tmp_path):
    _write_json(
        tmp_path / "codex/standards/std_json_facets.json",
        {
            "kind": "standard",
            "schema_version": "std_json_facets_v1",
            "id": "std_json_facets",
        },
    )
    _write_json(
        tmp_path / "codex/doctrine/concepts/con_001_demo.json",
        {
            "id": "con_001",
            "slug": "demo",
            "title": "Demo Concept",
            "statement": "claim route semantic doctrine graph",
            "status": "active",
            "tags": ["route", "semantic"],
            "note": "Mechanism note for doctrine routing.",
            "principle_edges": [
                {"target": "pri_001", "relation": "implements", "gloss": "Guarantee doctrine remains queryable."}
            ],
            "mechanism_edges": [
                {"target": "mech_001", "relation": "grounded_by", "gloss": "Mechanism is routed through a graph."}
            ],
        },
    )
    adapter = build_adapter("doctrine", tmp_path)
    items = list(adapter.iter_items())
    assert len(items) == 1
    facets = items[0].non_empty_facets()
    assert facets["title"] == "Demo Concept"
    assert facets["statement"] == "claim route semantic doctrine graph"
    assert facets["teleology"] == "claim route semantic doctrine graph"
    assert "Mechanism note" in facets["mechanism"]
    assert "Guarantee doctrine remains queryable" in facets["guarantee"]
    assert "implements:pri_001" in facets["couples"]
    assert "grounded_by:mech_001" in facets["couples"]
    assert adapter.schema_hash() is not None


def test_standards_json_and_annex_notes_adapters_extract_facets(tmp_path):
    _write_json(
        tmp_path / "codex/standards/std_json_facets.json",
        {
            "kind": "standard",
            "schema_version": "std_json_facets_v1",
            "id": "std_json_facets",
        },
    )
    _write_json(
        tmp_path / "codex/standards/std_demo.json",
        {
            "kind": "standard",
            "schema_version": "std_demo_v1",
            "id": "std_demo",
            "title": "Demo Standard",
            "purpose": "Schema intent for routing.",
            "scope": {"does_not_apply_to": ["Generated caches."]},
            "governance": {"consumers": ["system/lib/demo.py"]},
            "anti_patterns": ["Blob everything into one field."],
        },
    )
    _write_json(
        tmp_path / "annexes/demo/annex_notes.json",
        {
            "kind": "annex_notes",
            "schema_version": "annex_notes_v1",
            "slug": "demo",
            "notes": [
                {
                    "id": "n001",
                    "note": "NAVIGATION MAP — Start here.\n\nai_workflow: map this onto the local router.",
                    "routing": {
                        "problem_spaces": ["runtime-control", "bridge-routing"],
                        "ai_workflow_surfaces": ["bridge", "annex-routing"],
                    },
                }
            ],
        },
    )

    standard_items = {
        item.id: item.non_empty_facets()
        for item in build_adapter("standards_json", tmp_path).iter_items()
    }
    assert set(standard_items) == {"std_demo", "std_json_facets"}
    standard_facets = standard_items["std_demo"]
    assert standard_facets["title"] == "Demo Standard"
    assert standard_facets["schema_intent"] == "Schema intent for routing."
    assert "Generated caches." in standard_facets["constraints"]
    assert "system/lib/demo.py" in standard_facets["consumers"]
    assert "Blob everything into one field." in standard_facets["anti_patterns"]

    annex_item = list(build_adapter("annex_notes", tmp_path).iter_items())
    assert len(annex_item) == 1
    assert annex_item[0].id == "demo::n001"
    annex_facets = annex_item[0].non_empty_facets()
    assert annex_facets["title"] == "NAVIGATION MAP"
    assert "Start here." in annex_facets["pattern_intent"]
    assert "local router" in annex_facets["local_translation"]
    assert "runtime-control" in annex_facets["problem_spaces"]
    assert "ai_workflow_surfaces" not in annex_facets
    assert "bridge" not in annex_facets["local_translation"]


def test_json_facet_standard_schema_drift_forces_full_reembed(tmp_path):
    _write_json(
        tmp_path / "codex/standards/std_json_facets.json",
        {
            "kind": "standard",
            "schema_version": "std_json_facets_v1",
            "id": "std_json_facets",
            "purpose": "v1",
        },
    )
    _write_json(
        tmp_path / "codex/standards/std_demo.json",
        {
            "kind": "standard",
            "schema_version": "std_demo_v1",
            "id": "std_demo",
            "title": "Demo Standard",
            "purpose": "Schema intent for routing.",
            "scope": {"does_not_apply_to": ["Generated caches."]},
            "governance": {"consumers": ["system/lib/demo.py"]},
            "anti_patterns": ["Blob everything into one field."],
        },
    )
    substrate = _substrate(tmp_path)
    adapter = build_adapter("standards_json", tmp_path)
    first = substrate.refresh(adapter)
    assert first["embedded"] == 7

    _write_json(
        tmp_path / "codex/standards/std_json_facets.json",
        {
            "kind": "standard",
            "schema_version": "std_json_facets_v1",
            "id": "std_json_facets",
            "purpose": "v2 drift",
        },
    )
    second = substrate.refresh(build_adapter("standards_json", tmp_path))
    assert second["embedded"] == 7


def test_raw_seed_paragraph_adapter_emits_paragraph_facets_and_lineage_metadata(tmp_path):
    family_rel = "obsidian/family-09"
    paragraph_id = "par_phase_09_raw_seed__source_11_001"
    section_id = "sec_phase_09_raw_seed__source_11"
    _write_json(
        tmp_path / f"{family_rel}/phase_family.json",
        {
            "kind": "phase_family",
            "family_number": "09",
            "family_dir": family_rel,
            "raw_seed_path": f"{family_rel}/raw_seed.md",
            "raw_seed_json_path": f"{family_rel}/raw_seed.json",
            "active_phase_dir": f"{family_rel}/09.35 - Active Phase",
        },
    )
    _write_json(
        tmp_path / f"{family_rel}/raw_seed.json",
        {
            "kind": "raw_seed_registry",
            "family_id": "09",
            "family_number": "09",
            "family_dir": family_rel,
            "raw_seed_path": f"{family_rel}/raw_seed.md",
            "sections": [
                {
                    "id": section_id,
                    "heading": "source 11 nvidia navigation",
                    "path": "phase-09-raw-seed/source-11-nvidia-navigation",
                }
            ],
            "paragraphs": [
                {
                    "id": paragraph_id,
                    "section_id": section_id,
                    "section_path": "phase-09-raw-seed/source-11-nvidia-navigation",
                    "plain_text": "NVIDIA can help navigate raw-seed paragraphs cheaply.",
                    "keyword_hints": ["nvidia", "navigation"],
                    "mechanism_hints": ["vector", "kernel"],
                    "idea_group_ids": ["grp_navigation"],
                    "fingerprint": "fp_demo_001",
                    "paragraph_fingerprint": "fp_demo_001",
                    "source_substrate": "raw_seed",
                    "authored_by": "operator",
                }
            ],
        },
    )
    _write_json(
        tmp_path / f"{family_rel}/09.35 - Active Phase/extracted_shards.json",
        {
            "kind": "extracted_shards",
            "shards": [
                {
                    "id": "seed_09_35_001",
                    "parent_paragraph_id": paragraph_id,
                    "raw_paragraph_ids": [paragraph_id],
                }
            ],
        },
    )

    items = list(build_adapter("raw_seed_paragraphs", tmp_path).iter_items())
    assert len(items) == 1
    item = items[0]
    assert item.id == paragraph_id
    assert item.source_path == f"{family_rel}/raw_seed.md"
    facets = item.non_empty_facets()
    assert facets["section_heading"] == "source 11 nvidia navigation"
    assert "nvidia" in facets["keywords"]
    assert "vector" in facets["mechanisms"]
    assert facets["body"] == "NVIDIA can help navigate raw-seed paragraphs cheaply."
    assert item.metadata["raw_shard_ids"] == ["sh_fp_demo_001"]
    assert item.metadata["extracted_shard_ids"] == ["seed_09_35_001"]


def test_raw_seed_shard_adapter_indexes_family_root_extracted_shards(tmp_path):
    family_rel = "obsidian/family-09"
    _write_json(
        tmp_path / f"{family_rel}/phase_family.json",
        {
            "kind": "phase_family",
            "family_number": "09",
            "family_dir": family_rel,
            "active_phase_dir": f"{family_rel}/09.35 - Active Phase",
        },
    )
    _write_json(
        tmp_path / f"{family_rel}/extracted_shards.json",
        {
            "kind": "extracted_shards",
            "shards": [
                {
                    "id": "atom_demo_001",
                    "parent_paragraph_id": "par_demo_001",
                    "raw_paragraph_ids": ["par_demo_001"],
                    "clarified_statement": "Raw-seed shards should index from the family backlog.",
                    "voice_anchor": "same thing conceptually",
                    "gestures_towards": ["family backlog", "routing substrate"],
                    "atomization_source": "raw_seed_distillation_bridge_v1",
                    "distillation_confidence": 0.91,
                }
            ],
        },
    )

    items = list(build_adapter("raw_seed_shards", tmp_path).iter_items())

    assert len(items) == 1
    item = items[0]
    assert item.id == "atom_demo_001"
    assert item.source_path == f"{family_rel}/extracted_shards.json"
    assert item.facets["clarified"] == "Raw-seed shards should index from the family backlog."
    assert item.facets["voice_anchor"] == "same thing conceptually"
    assert "routing substrate" in item.facets["gestures"]
    assert item.metadata["family_number"] == "09"
    assert item.metadata["source_scope"] == "family_root"
    assert item.metadata["parent_paragraph_id"] == "par_demo_001"
