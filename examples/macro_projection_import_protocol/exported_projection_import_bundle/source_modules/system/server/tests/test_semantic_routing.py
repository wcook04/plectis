from __future__ import annotations

import json
from pathlib import Path

import yaml

from system.lib.embedding_substrate import EmbeddingRecord, SearchHit
from system.lib.launchable_operations import PreparedLaunch
from system.lib import semantic_routing
from system.lib.kernel.commands import embed as kernel_embed
from tools.meta.control import reactions_engine
from tools.meta.control import semantic_route_quality_audit


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_jsonl_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _cosine(u, v) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = sum(a * a for a in u) ** 0.5
    nv = sum(b * b for b in v) ** 0.5
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return dot / (nu * nv)


class FakeEmbeddingSubstrate:
    def __init__(self, repo_root: Path, **_kwargs) -> None:
        self.repo_root = Path(repo_root)

    def _path_for(self, source_kind: str) -> Path:
        return self.repo_root / "state" / "embeddings" / f"{source_kind}.json"

    def _embed_text(self, text: str) -> list[float]:
        lowered = text.lower()
        keywords = [
            "identity",
            "claim",
            "mechanism",
            "contract",
            "trigger",
            "voice",
            "novelty",
            "route",
            "python",
            "archaeology",
            "semantic",
            "drift",
            "standard",
            "annex",
            "seed",
        ]
        vec = [1.0 if token in lowered else 0.0 for token in keywords]
        if not any(vec):
            vec[0] = 0.1
        return vec

    def load(self, source_kind: str) -> dict:
        path = self._path_for(source_kind)
        if not path.exists():
            return {
                "schema_version": "embedding_substrate_v2_faceted",
                "source_kind": source_kind,
                "records": [],
                "model": "fake",
                "dims": 12,
                "schema_hash": None,
                "last_refresh_at": None,
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, source_kind: str, payload: dict) -> None:
        _write_json(self._path_for(source_kind), payload)

    def status(self, adapter, *, fast: bool = False):
        data = self.load(adapter.source_kind)
        existing_keys = {(r["id"], r.get("facet")) for r in data.get("records", [])}
        if fast and not data.get("records"):
            stale = 1
            class _Status:
                def __init__(self, path: Path, record_count: int, stale_or_missing: int, schema_hash):
                    self.source_kind = adapter.source_kind
                    self.record_count = record_count
                    self.stale_or_missing = stale_or_missing
                    self.path = str(path)
                    self.schema_hash = schema_hash
                    self.stale_preview = [
                        {
                            "reason": "cache_missing_or_empty_fast_estimate",
                            "id": "*",
                            "facet": "*",
                        }
                    ]
                    self.stale_preview_truncated = False
                    self.stale_or_missing_is_estimate = True

            return _Status(self._path_for(adapter.source_kind), 0, stale, data.get("schema_hash"))
        stale = 0
        seen_keys = set()
        stale_preview = []

        def _preview(reason: str, item_id: str, facet: str, source_path: str = "") -> None:
            if len(stale_preview) >= 10:
                return
            row = {"reason": reason, "id": item_id, "facet": facet}
            if source_path:
                row["source_path"] = source_path
            stale_preview.append(row)

        for item in adapter.iter_items():
            recs = [r for r in data.get("records", []) if r.get("id") == item.id]
            for facet, text in item.non_empty_facets().items():
                seen_keys.add((item.id, facet))
                matching = next((r for r in recs if r.get("facet") == facet), None)
                if matching is None:
                    stale += 1
                    _preview("missing", item.id, facet, item.source_path)
                    continue
                if matching.get("content_hash") != semantic_routing._sha_text(text):  # type: ignore[attr-defined]
                    stale += 1
                    _preview("hash_changed", item.id, facet, item.source_path)
            if adapter.schema_hash() != data.get("schema_hash"):
                stale += len(item.non_empty_facets())
                for facet in item.non_empty_facets().keys():
                    _preview("schema_changed", item.id, facet, item.source_path)
        stale += len(existing_keys - seen_keys)
        for item_id, facet in sorted(existing_keys - seen_keys):
            _preview("removed", item_id, facet)

        class _Status:
            def __init__(
                self,
                path: Path,
                record_count: int,
                stale_or_missing: int,
                schema_hash,
                preview: list[dict],
            ):
                self.source_kind = adapter.source_kind
                self.record_count = record_count
                self.stale_or_missing = stale_or_missing
                self.path = str(path)
                self.schema_hash = schema_hash
                self.stale_preview = preview
                self.stale_preview_truncated = len(preview) < stale_or_missing
                self.stale_or_missing_is_estimate = False

        return _Status(
            self._path_for(adapter.source_kind),
            len(data.get("records", [])),
            stale,
            data.get("schema_hash"),
            stale_preview,
        )

    def refresh(self, adapter, force: bool = False, progress=None):
        previous_records = self.load(adapter.source_kind).get("records", [])
        previous_keys = {(r["id"], r.get("facet")) for r in previous_records}
        records = []
        for item in adapter.iter_items():
            for facet, text in item.non_empty_facets().items():
                vector = self._embed_text(text)
                records.append(
                    EmbeddingRecord(
                        id=item.id,
                        facet=facet,
                        source_kind=adapter.source_kind,
                        source_path=item.source_path,
                        content_hash=semantic_routing._sha_text(text),  # type: ignore[attr-defined]
                        text_preview=text[:400],
                        metadata=dict(item.metadata),
                        vector=vector,
                        model="fake",
                        dims=len(vector),
                        updated_at="2026-04-19T00:00:00Z",
                    ).as_dict()
                )
        payload = {
            "schema_version": "embedding_substrate_v2_faceted",
            "source_kind": adapter.source_kind,
            "records": sorted(records, key=lambda r: (r["id"], r["facet"])),
            "model": "fake",
            "dims": 12,
            "schema_hash": adapter.schema_hash(),
            "last_refresh_at": "2026-04-19T00:00:00Z",
        }
        self.save(adapter.source_kind, payload)
        return {
            "source_kind": adapter.source_kind,
            "embedded": len(records),
            "kept": 0,
            "removed": len(previous_keys - {(r["id"], r.get("facet")) for r in records}),
            "total_records": len(records),
            "distinct_ids": len({r["id"] for r in records}),
            "facets_seen": sorted({r["facet"] for r in records}),
            "dims": 12,
            "schema_hash": adapter.schema_hash(),
        }

    def search(self, query: str, source_kinds=None, facets=None, top_k: int = 10):
        kinds = list(source_kinds or [])
        qvec = self._embed_text(query)
        hits = []
        for kind in kinds:
            data = self.load(kind)
            for raw in data.get("records", []):
                if facets and raw.get("facet") not in facets:
                    continue
                score = _cosine(qvec, raw.get("vector", []))
                hits.append(
                    SearchHit(
                        record=EmbeddingRecord(
                            id=raw["id"],
                            facet=raw["facet"],
                            source_kind=raw["source_kind"],
                            source_path=raw["source_path"],
                            content_hash=raw["content_hash"],
                            text_preview=raw["text_preview"],
                            metadata=raw.get("metadata", {}),
                            vector=raw.get("vector", []),
                            model=raw.get("model", "fake"),
                            dims=raw.get("dims", 12),
                            updated_at=raw.get("updated_at", ""),
                        ),
                        score=score,
                    )
                )
        hits.sort(key=lambda h: (-float(h.score), h.record.source_kind, h.record.id, h.record.facet))
        return hits[:top_k]


def _standard() -> dict:
    return {
        "kind": "standard",
        "schema_version": "std_semantic_routing_v1",
        "id": "std_semantic_routing",
        "included_source_kinds": [
            "doctrine",
            "paper_modules",
            "skills",
            "raw_seed_paragraphs",
            "raw_seed_shards",
            "archaeology_shards",
            "standards_json",
            "annex_notes",
            "python_holographic",
        ],
        "adjacency_limits": {"same_kind": 3, "cross_kind_per_target": 5},
        "axis_families": ["identity", "claim", "mechanism", "contract", "triggers", "voice", "novelty"],
        "facet_to_axis_family": {
            "doctrine": {
                "title": "identity",
                "statement": "claim",
                "teleology": "claim",
                "mechanism": "mechanism",
                "guarantee": "contract",
                "couples": "contract",
                "tags": "triggers",
            },
            "paper_modules": {
                "title": "identity",
                "tldr": "claim",
                "intent": "claim",
                "current_state": "claim",
                "shape": "mechanism",
                "deliverables": "contract",
                "gap": "contract",
            },
            "skills": {
                "title": "identity",
                "summary": "claim",
                "description": "claim",
                "triggers": "triggers",
            },
            "raw_seed_paragraphs": {
                "section_heading": "identity",
                "keywords": "triggers",
                "mechanisms": "mechanism",
                "body": "claim",
            },
            "raw_seed_shards": {
                "clarified": "claim",
                "voice_anchor": "voice",
                "gestures": "triggers",
            },
            "archaeology_shards": {
                "clarified": "claim",
                "voice_anchor": "voice",
                "gestures": "triggers",
                "new_dimension": "novelty",
            },
            "standards_json": {
                "title": "identity",
                "schema_intent": "claim",
                "constraints": "contract",
                "consumers": "triggers",
                "anti_patterns": "contract",
            },
            "annex_notes": {
                "title": "identity",
                "pattern_intent": "claim",
                "local_translation": "mechanism",
                "problem_spaces": "triggers",
            },
            "python_holographic": {
                "purpose": "claim",
                "teleology": "claim",
                "mechanism": "mechanism",
                "flow": "mechanism",
                "signatures": "mechanism",
                "constraints": "contract",
                "guarantee": "contract",
                "fails": "contract",
                "reads": "contract",
                "writes": "contract",
                "couples": "contract",
                "non_goal": "contract",
                "when_needed": "triggers",
                "escalates_to": "triggers",
                "navigation_group": "triggers",
            },
        },
        "expected_bridge_families": [
            {
                "bridge_id": "python_claim_chain",
                "source": {"source_kind": "python_holographic", "source_facets": ["purpose", "teleology"]},
                "targets": [
                    {"target_kind": "paper_modules", "target_facets": ["tldr", "intent", "current_state"], "min_score": 0.45},
                    {"target_kind": "doctrine", "target_facets": ["statement"], "min_score": 0.4},
                    {"target_kind": "skills", "target_facets": ["summary", "description"], "min_score": 0.38},
                    {"target_kind": "archaeology_shards", "target_facets": ["clarified", "new_dimension"], "min_score": 0.35},
                ],
            }
        ],
        "evidence_contract": {
            "allowed_kinds": ["confirmation", "rejected", "operation_success"],
            "boost_cap_fraction": 0.1,
            "boost_formula": {"confirmation": 0.02, "operation_success": 0.03, "rejected": -0.03},
        },
    }


def _seed_repo(tmp_path: Path) -> None:
    _write_json(tmp_path / "codex/standards/std_semantic_routing.json", _standard())
    _write_json(
        tmp_path / "codex/standards/std_json_facets.json",
        {
            "kind": "standard",
            "schema_version": "std_json_facets_v1",
            "id": "std_json_facets",
            "title": "JSON Facet Vocabulary Standard",
            "purpose": "Schema intent for route-ready JSON facets.",
        },
    )
    _write(
        tmp_path / "codex/standards/std_python.py",
        '"""\n[PURPOSE]\n- Teleology: test standard.\n[INTERFACE]\n- Exports: none.\n[FLOW]\n- Mechanism: parse things.\n[DEPENDENCIES]\n- None.\n[CONSTRAINTS]\n- Guarantee: deterministic.\n"""\n',
    )
    _write_json(
        tmp_path / "codex/standards/std_demo.json",
        {
            "kind": "standard",
            "schema_version": "std_demo_v1",
            "id": "std_demo",
            "title": "Demo Standard",
            "purpose": "claim route standard schema intent",
            "scope": {"does_not_apply_to": ["generated state"]},
            "governance": {"consumers": ["system/lib/routing_file.py"]},
            "anti_patterns": ["contract drift without refresh"],
        },
    )
    _write_json(
        tmp_path / "codex/doctrine/concepts/con_001_semantic_routes.json",
        {
            "id": "con_001",
            "slug": "semantic-routes",
            "title": "Semantic Routes",
            "statement": "claim route semantic doctrine graph",
            "status": "active",
            "tags": ["route", "semantic", "claim"],
            "note": "Mechanism note for doctrine routing.",
            "principle_edges": [
                {"target": "pri_001", "relation": "implements", "gloss": "Guarantee doctrine remains queryable."}
            ],
            "mechanism_edges": [
                {"target": "mech_001", "relation": "grounded_by", "gloss": "Mechanism is routed through a graph."}
            ],
        },
    )
    _write_json(
        tmp_path / "codex/doctrine/concepts/con_002_other.json",
        {
            "id": "con_002",
            "slug": "other",
            "title": "Other Concept",
            "statement": "different claim other",
            "status": "active",
            "tags": ["other"],
        },
    )
    _write_json(
        tmp_path / "codex/doctrine/mechanisms/mech_001_alignment.json",
        {
            "id": "mech_001",
            "slug": "alignment",
            "title": "Alignment",
            "statement": "mechanism route alignment",
            "status": "active",
            "tags": ["mechanism", "route"],
        },
    )
    _write(
        tmp_path / "codex/doctrine/paper_modules/voice_archaeology.md",
        "# Voice Archaeology\n\n## TLDR\nclaim route archaeology semantic paper module\n\n## Intent\nclaim route intent archaeology\n\n## Shape\nmechanism route graph shape\n\n## Current state\nclaim current state route plane\n\n## Deliverables\ncontract deliverables refresh route graph\n\n## Gap\ncontract gap drift ledger\n",
    )
    _write(
        tmp_path / "codex/doctrine/paper_modules/unrelated.md",
        "# Unrelated\n\n## TLDR\nfrontend color palette layout animation\n\n## Shape\nshape frontend layout visuals\n",
    )
    _write(
        tmp_path / "codex/doctrine/skills/raw_seed/archaeological_voice_mining.md",
        "---\nid: \"archaeological_voice_mining\"\nfamily: \"raw_seed\"\ntitle: \"Archaeological Voice Mining\"\nsummary: \"claim route archaeology mining summary\"\ndescription: \"claim route skill description semantic archaeology\"\ntriggers:\n  - \"archaeology trigger route\"\n---\n",
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
                    "note": "NAVIGATION MAP — claim route annex pattern.\n\nai_workflow: mechanism local translation for the route plane.",
                    "routing": {
                        "problem_spaces": ["runtime-control", "bridge-routing"],
                        "ai_workflow_surfaces": ["annex-routing", "bridge"],
                    },
                }
            ],
        },
    )
    _write_json(
        tmp_path / "obsidian/okay lets do this/09 Demo/raw_seed/extracted_shards.json",
        {
            "shards": [
                {
                    "id": "atom_111111111111",
                    "clarified_statement": "claim route seed shard navigator",
                    "voice_anchor": "voice seed anchor",
                    "gestures_towards": ["route", "seed", "navigation"],
                }
            ]
        },
    )
    _write_json(
        tmp_path / "obsidian/okay lets do this/09 Demo/phase_family.json",
        {
            "family_number": "09",
            "family_dir": "obsidian/okay lets do this/09 Demo",
            "raw_seed_json_path": "obsidian/okay lets do this/09 Demo/raw_seed.json",
            "raw_seed_path": "obsidian/okay lets do this/09 Demo/raw_seed.md",
            "active_phase_dir": "obsidian/okay lets do this/09 Demo",
        },
    )
    _write(
        tmp_path / "obsidian/okay lets do this/09 Demo/raw_seed.md",
        "# Demo Raw Seed\n\ncontroller heartbeat mission board bridge route proof\n",
    )
    _write_json(
        tmp_path / "obsidian/okay lets do this/09 Demo/raw_seed.json",
        {
            "family_number": "09",
            "raw_seed_path": "obsidian/okay lets do this/09 Demo/raw_seed.md",
            "sections": [
                {
                    "id": "sec_demo_001",
                    "heading": "Controller heartbeat",
                }
            ],
            "paragraphs": [
                {
                    "id": "par_demo_001",
                    "section_id": "sec_demo_001",
                    "section_path": "controller/heartbeat",
                    "plain_text": "controller heartbeat mission board bridge route proof",
                    "keyword_hints": ["controller heartbeat", "mission board"],
                    "mechanism_hints": ["bridge routing", "continuity projection"],
                    "source_substrate": "raw_seed",
                    "authored_by": "operator",
                    "line_start": 3,
                    "line_end": 3,
                },
                {
                    "id": "par_demo_002",
                    "section_id": "sec_demo_001",
                    "section_path": "controller/heartbeat",
                    "plain_text": "frontend palette animation layout notes",
                    "keyword_hints": ["frontend", "layout"],
                    "mechanism_hints": ["visual polish"],
                    "source_substrate": "raw_seed",
                    "authored_by": "operator",
                    "line_start": 5,
                    "line_end": 5,
                },
            ],
        },
    )
    _write_json(
        tmp_path / "obsidian/okay lets do this/09 Demo/extracted_shards.json",
        {
            "shards": [
                {
                    "id": "extracted_heartbeat_001",
                    "raw_paragraph_ids": ["par_demo_001"],
                    "parent_paragraph_id": "par_demo_001",
                    "clarified_statement": "claim route seed shard navigator",
                    "voice_anchor": "voice seed anchor",
                    "gestures_towards": ["route", "seed", "navigation"],
                }
            ]
        },
    )
    _write_json(
        tmp_path / "state/voice_archaeology/archaeological_shards.json",
        {
            "shards": [
                {
                    "id": "shard_arch_111111111111",
                    "source_file_path": "obsidian/idea/a.md",
                    "source_file_domain": "system_architecture",
                    "clarified_statement": "claim route archaeology shard clarified",
                    "voice_anchor": "voice anchor archaeology",
                    "gestures_towards": ["route", "semantic"],
                    "coverage_check": {"new_dimension": "novelty route shard", "decision": "emit"},
                    "voice_date": "2026-03-01",
                    "archaeological_depth": "medium",
                }
            ]
        },
    )
    _write(
        tmp_path / "system/lib/routing_file.py",
        '"""\n[PURPOSE]\n- Teleology: claim route semantic python file.\n- Mechanism: mechanism route matching.\n[INTERFACE]\n- Reads: contract route reads.\n- Writes: contract route writes.\n[FLOW]\n- Mechanism: flow route semantic.\n[DEPENDENCIES]\n- None.\n[CONSTRAINTS]\n- Guarantee: contract route deterministic.\n- When-needed: trigger route.\n- Escalates-to: paper module.\n- Navigation-group: routes.\n"""\n\ndef route_file() -> None:\n    """[ACTION]\n    - Teleology: claim route operation.\n    """\n    return None\n',
    )


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_reactions_config(repo_root: Path, reactions: list[dict]) -> None:
    (repo_root / "reactions.yaml").write_text(
        yaml.safe_dump(
            {
                "kind": "reactions_config",
                "schema_version": "reactions_config_v1",
                "reactions": reactions,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_refresh_routes_builds_deterministic_bounded_graph(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    first = semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    graph = semantic_routing.load_route_graph(tmp_path)
    assert first["refresh_mode"] == "full"
    assert graph["statistics"]["node_count"] > 0
    for node in graph["nodes"].values():
        assert len(node["same_kind_neighbors"]) <= 3
        for edges in node["neighbors_by_target_kind"].values():
            assert len(edges) <= 5

    no_op_messages: list[str] = []
    second = semantic_routing.refresh_routes(
        tmp_path,
        source="all",
        force=False,
        auto_refresh_embeddings=True,
        progress=no_op_messages.append,
    )
    status = semantic_routing.load_route_status(tmp_path)
    assert second["refresh_mode"] == "incremental"
    assert second["result_summary"]["refreshed_rows"] == 0
    assert any("route graph already current" in message for message in no_op_messages)
    assert status["route_graph_fingerprint"] == semantic_routing.load_route_status(tmp_path)["route_graph_fingerprint"]


def test_refresh_routes_skips_before_graph_build_when_disk_headroom_is_low(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    monkeypatch.setattr(
        semantic_routing,
        "route_refresh_disk_headroom",
        lambda _repo_root: {
            "ok": False,
            "free_bytes": 10,
            "required_bytes": 100,
            "current_graph_bytes": 50,
        },
    )
    messages: list[str] = []

    payload = semantic_routing.refresh_routes(
        tmp_path,
        source="all",
        force=True,
        auto_refresh_embeddings=True,
        progress=messages.append,
    )

    assert payload["status"] == "skipped_low_disk_headroom"
    assert payload["result_summary"]["route_refreshed"] is False
    assert any("low disk headroom" in message for message in messages)
    assert not (tmp_path / "state/semantic_routing/route_graph.json").exists()


def test_noop_refresh_rewrites_status_with_live_staleness(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    _write(
        tmp_path / "codex/doctrine/skills/kernel/nvidia_runtime.md",
        "---\n"
        "id: \"nvidia_runtime\"\n"
        "family: \"kernel\"\n"
        "title: \"NVIDIA Runtime\"\n"
        "summary: \"claim route nvidia runtime summary\"\n"
        "description: \"claim route nvidia semantic embedding runtime\"\n"
        "triggers:\n"
        "  - \"nvidia route trigger\"\n"
        "---\n",
    )

    payload = semantic_routing.refresh_routes(
        tmp_path,
        source="archaeology_shards",
        force=False,
        auto_refresh_embeddings=True,
    )
    status = semantic_routing.load_route_status(tmp_path)

    assert payload["result_summary"]["refreshed_rows"] == 0
    assert "skills" in status["stale_sources"]
    assert status["embedding_staleness"]["skills"]["stale"] is True
    assert status["embedding_staleness"]["skills"]["stale_or_missing"] > 0


def test_refresh_routes_reports_rebuild_progress(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    messages: list[str] = []

    semantic_routing.refresh_routes(
        tmp_path,
        source="all",
        force=True,
        auto_refresh_embeddings=True,
        progress=messages.append,
    )

    assert any("route refresh start" in message for message in messages)
    assert any("building route nodes" in message for message in messages)
    assert any("writing route projections" in message for message in messages)


def test_large_incremental_refresh_promotes_to_full_rebuild(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    monkeypatch.setattr(semantic_routing, "LARGE_INCREMENTAL_ROW_THRESHOLD", 1)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    _write_json(
        tmp_path / "codex/doctrine/concepts/con_001_semantic_routes.json",
        {
            "id": "con_001",
            "slug": "semantic-routes",
            "title": "Semantic Routes",
            "statement": "claim route semantic doctrine graph archaeology python paper module",
            "status": "active",
            "tags": ["route", "semantic", "claim", "python"],
        },
    )
    messages: list[str] = []

    payload = semantic_routing.refresh_routes(
        tmp_path,
        source="doctrine",
        force=False,
        auto_refresh_embeddings=True,
        progress=messages.append,
    )

    assert payload["refresh_mode"] == "full"
    assert any("large route invalidation promoted to full rebuild" in message for message in messages)


def test_drift_fires_then_clears_after_claim_alignment_refresh(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    # Start with an unrelated paper module so the bridge family drifts.
    _write(
        tmp_path / "codex/doctrine/paper_modules/voice_archaeology.md",
        "# Voice Archaeology\n\n## TLDR\nfrontend color palette layout animation\n\n## Intent\nfrontend styling intent\n",
    )
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    drift = semantic_routing.load_route_drift(tmp_path)
    assert drift["drift_count"] > 0

    _write(
        tmp_path / "codex/doctrine/paper_modules/voice_archaeology.md",
        "# Voice Archaeology\n\n## TLDR\nclaim route semantic python file paper module\n\n## Intent\nclaim route semantic intent\n\n## Current state\nclaim route current state\n",
    )
    semantic_routing.refresh_routes(tmp_path, source="paper_modules", force=False, auto_refresh_embeddings=True)
    drift_after = semantic_routing.load_route_drift(tmp_path)
    assert drift_after["drift_count"] == 0


def test_incremental_refresh_tracks_changed_ids_and_impacted_neighbors(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    _write_json(
        tmp_path / "codex/doctrine/concepts/con_001_semantic_routes.json",
        {
            "id": "con_001",
            "slug": "semantic-routes",
            "title": "Semantic Routes",
            "statement": "claim route semantic doctrine graph archaeology python paper module",
            "status": "active",
            "tags": ["route", "semantic", "claim", "python"],
        },
    )
    payload = semantic_routing.refresh_routes(tmp_path, source="doctrine", force=False, auto_refresh_embeddings=True)
    status = semantic_routing.load_route_status(tmp_path)
    assert payload["refresh_mode"] == "incremental"
    assert status["changed_sources"]["doctrine"] == ["con_001"]
    assert 0 < status["refreshed_row_count"] < status["statistics"]["node_count"]


def test_incremental_refresh_prunes_removed_source_rows_and_edges(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    graph_before = semantic_routing.load_route_graph(tmp_path)
    removed_row_keys = {
        key
        for key, node in graph_before["nodes"].items()
        if node.get("source_kind") == "doctrine" and node.get("artifact_id") == "con_002"
    }
    assert removed_row_keys

    (tmp_path / "codex/doctrine/concepts/con_002_other.json").unlink()
    payload = semantic_routing.refresh_routes(tmp_path, source="doctrine", force=False, auto_refresh_embeddings=True)
    graph_after = semantic_routing.load_route_graph(tmp_path)
    status = semantic_routing.load_route_status(tmp_path)

    assert payload["refresh_mode"] == "incremental"
    assert status["changed_sources"]["doctrine"] == ["con_002"]
    assert status["embedding_refresh"]["doctrine"]["report"]["removed"] == len(removed_row_keys)
    assert removed_row_keys.isdisjoint(graph_after["nodes"].keys())

    remaining_targets = {
        str(edge.get("target_row_key") or "")
        for node in graph_after["nodes"].values()
        for edge in (node.get("same_kind_neighbors") or [])
    }
    for node in graph_after["nodes"].values():
        for edges in (node.get("neighbors_by_target_kind") or {}).values():
            remaining_targets.update(str(edge.get("target_row_key") or "") for edge in edges)
    assert removed_row_keys.isdisjoint(remaining_targets)


def test_confirm_route_updates_evidence_without_creating_new_edges(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)

    graph_before = semantic_routing.load_route_graph(tmp_path)
    edge_count_before = graph_before["statistics"]["edge_count"]
    confirm = semantic_routing.confirm_route(
        tmp_path,
        source_token="python_holographic:system/lib/routing_file.py",
        target_token="paper_modules:voice_archaeology",
    )
    assert confirm["edge_summary"]["counts"]["confirmation"] == 1
    assert float(confirm["edge_summary"]["boost_fraction"]) > 0.0

    graph_after = semantic_routing.load_route_graph(tmp_path)
    assert graph_after["statistics"]["edge_count"] == edge_count_before

    node = semantic_routing.describe_route_node(tmp_path, artifact_token="python_holographic:system/lib/routing_file.py")
    boosted = [
        edge
        for row in node["rows"]
        for edges in row["neighbors_by_target_kind"].values()
        for edge in edges
        if edge["target_kind"] == "paper_modules" and edge["target_id"] == "voice_archaeology"
    ]
    assert boosted
    assert any(float(edge["adjusted_score"]) > float(edge["semantic_score"]) for edge in boosted)


def test_query_routes_falls_back_when_python_routes_are_stale(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)

    fresh = semantic_routing.query_routes(tmp_path, query="claim route semantic python", source_kinds=["python_holographic"], top_k=5)
    assert fresh["route_hits"]
    assert not fresh["fallback_hits"]

    _write(
        tmp_path / "codex/standards/std_python.py",
        '"""\n[PURPOSE]\n- Teleology: changed standard.\n[INTERFACE]\n- Exports: none.\n[FLOW]\n- Mechanism: changed parse.\n[DEPENDENCIES]\n- None.\n[CONSTRAINTS]\n- Guarantee: changed deterministic.\n"""\n',
    )
    stale = semantic_routing.current_route_staleness(tmp_path, source_kinds=["python_holographic"])
    assert stale["python_holographic"]["stale"] is True

    fallback = semantic_routing.query_routes(tmp_path, query="claim route semantic python", source_kinds=["python_holographic"], top_k=5)
    assert fallback["stale_source_kinds"] == ["python_holographic"]
    assert fallback["fallback_hits"]

    refreshed = semantic_routing.refresh_routes(tmp_path, source="python_holographic", force=False, auto_refresh_embeddings=True)
    assert refreshed["embedding_refresh"]["python_holographic"]["refreshed"] is True


def test_query_routes_covers_raw_seed_standards_and_annex_sources(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)

    result = semantic_routing.query_routes(
        tmp_path,
        query="claim route navigator",
        source_kinds=["raw_seed_paragraphs", "raw_seed_shards", "standards_json", "annex_notes"],
        top_k=10,
    )
    seed_source_kinds = {row["source_kind"] for row in result["seed_hits"]}
    assert {"raw_seed_paragraphs", "raw_seed_shards", "standards_json", "annex_notes"} <= seed_source_kinds
    assert result["route_hits"]
    assert result["stale_source_kinds"] == []


def test_query_routes_falls_back_to_live_raw_seed_paragraphs_when_stale(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)

    raw_seed_path = tmp_path / "obsidian/okay lets do this/09 Demo/raw_seed.json"
    payload = _load_json(raw_seed_path)
    payload["paragraphs"][0]["plain_text"] = "controller heartbeat lexical rescue proof mission board"
    payload["paragraphs"][0]["keyword_hints"] = ["lexical rescue", "controller heartbeat"]
    payload["paragraphs"][0]["mechanism_hints"] = ["mission board routing"]
    _write_json(raw_seed_path, payload)

    stale = semantic_routing.current_route_staleness(tmp_path, source_kinds=["raw_seed_paragraphs"])
    assert stale["raw_seed_paragraphs"]["stale"] is True

    result = semantic_routing.query_routes(
        tmp_path,
        query="lexical rescue heartbeat",
        source_kinds=["raw_seed_paragraphs"],
        top_k=5,
    )
    assert result["seed_hits"] == []
    assert result["stale_source_kinds"] == ["raw_seed_paragraphs"]
    assert result["fallback_hits"]
    assert result["fallback_hits"][0]["source_kind"] == "raw_seed_paragraphs"
    assert result["fallback_hits"][0]["id"] == "par_demo_001"
    assert result["fallback_hits"][0]["match_backend"] == "raw_seed_index_lexical"
    assert "lexical rescue" in result["fallback_hits"][0]["preview"].lower()


def test_query_routes_uses_bm25_lite_for_stale_annex_notes(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)

    annex_notes_path = tmp_path / "annexes/demo/annex_notes.json"
    payload = _load_json(annex_notes_path)
    payload["notes"][0]["note"] = (
        "NAVIGATION MAP - weighted retrieval beacon zettel.\n\n"
        "ai_workflow: lexical fallback should surface annex notes before stale embeddings refresh."
    )
    _write_json(annex_notes_path, payload)

    stale = semantic_routing.current_route_staleness(tmp_path, source_kinds=["annex_notes"])
    assert stale["annex_notes"]["stale"] is True
    assert stale["annex_notes"]["stale_preview"][0]["reason"] == "hash_changed"
    assert stale["annex_notes"]["stale_preview"][0]["id"] == "demo::n001"

    result = semantic_routing.query_routes(
        tmp_path,
        query="retrieval beacon zettel",
        source_kinds=["annex_notes"],
        top_k=5,
    )
    assert result["seed_hits"] == []
    assert result["stale_source_kinds"] == ["annex_notes"]
    assert result["fallback_hits"]
    assert result["fallback_hits"][0]["source_kind"] == "annex_notes"
    assert result["fallback_hits"][0]["id"] == "demo::n001"
    assert result["fallback_hits"][0]["match_backend"] == "lexical_bm25_lite"
    assert "retrieval beacon zettel" in result["fallback_hits"][0]["preview"].lower()


def test_archaeology_refresh_adds_nodes_without_touching_unrelated_sources(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)
    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    before = semantic_routing.load_route_status(tmp_path)
    before_nodes = before["statistics"]["node_count"]

    payload = _load_json(tmp_path / "state/voice_archaeology/archaeological_shards.json")
    payload["shards"].append(
        {
            "id": "shard_arch_222222222222",
            "source_file_path": "obsidian/idea/b.md",
            "source_file_domain": "system_architecture",
            "clarified_statement": "claim route archaeology second shard",
            "voice_anchor": "voice anchor second",
            "gestures_towards": ["route"],
            "coverage_check": {"new_dimension": "novelty second shard", "decision": "emit"},
            "voice_date": "2026-03-02",
            "archaeological_depth": "medium",
        }
    )
    _write_json(tmp_path / "state/voice_archaeology/archaeological_shards.json", payload)

    refreshed = semantic_routing.refresh_routes(tmp_path, source="archaeology_shards", force=False, auto_refresh_embeddings=True)
    status = semantic_routing.load_route_status(tmp_path)
    assert refreshed["refresh_mode"] == "incremental"
    assert "archaeology_shards" in status["changed_sources"]
    assert "doctrine" not in status["changed_sources"]
    assert status["statistics"]["node_count"] > before_nodes


def test_route_status_persists_per_source_refresh_details(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(semantic_routing, "EmbeddingSubstrate", FakeEmbeddingSubstrate)

    semantic_routing.refresh_routes(tmp_path, source="all", force=True, auto_refresh_embeddings=True)
    status = semantic_routing.load_route_status(tmp_path)
    skills = status["embedding_staleness"]["skills"]

    assert status["refresh_ledger_path"] == "state/embeddings/refresh_ledger.jsonl"
    assert status["pending_refresh_path"] == "state/embeddings/pending_refresh.jsonl"
    assert skills["status"] == "fresh"
    assert skills["total_rows"] >= skills["record_count"]
    assert skills["missing_rows"] == 0
    assert "last_refresh_at" in skills
    assert isinstance(skills["stale_reason_counts"], dict)


def test_reactions_engine_fires_semantic_route_refresh_after_embed_refresh(tmp_path: Path, monkeypatch) -> None:
    _write_reactions_config(
        tmp_path,
        [
            {
                "reaction_id": "semantic_routes_after_embed_refresh",
                "label": "semantic routes after embed refresh",
                "source": {"kind": "operation_event", "operation_id": "kernel_embed_refresh"},
                "predicate": {"field": "returncode", "operator": "eq", "value": 0},
                "action": {
                    "operation_id": "semantic_route_refresh",
                    "parameters": {"source": "{signal.resolved_parameters.source}"},
                },
                "gate": {
                    "single_flight": True,
                    "cooldown_minutes": 0,
                    "dedupe_by": "signal_digest",
                    "barrier_kind": "operation_completion",
                },
                "priority": "high",
                "enabled_by_default": True,
                "provenance": {"annexes": ["restate", "agent-orchestrator"]},
            }
        ],
    )

    fake_signal = {
        "kind": "operation_event",
        "operation_id": "kernel_embed_refresh",
        "returncode": 0,
        "resolved_parameters": {"source": "doctrine"},
        "stable_signal_digest": "abc123",
    }
    monkeypatch.setattr(reactions_engine, "_load_latest_operation_event", lambda *_args, **_kwargs: fake_signal)
    monkeypatch.setattr(
        reactions_engine,
        "prepare_launch_operation",
        lambda repo_root, operation_id, parameters=None: PreparedLaunch(
            operation={"operation_id": operation_id, "meta_mission_id": None},
            command=f"echo {operation_id}",
            execution_mode="sync",
            resolved_parameters={key: str(value) for key, value in (parameters or {}).items()},
        ),
    )
    fired = []

    def fake_spawn(repo_root, *, reaction_id, operation_id, parameters, signal_digest, signal, started_at):
        fired.append((reaction_id, operation_id, dict(parameters)))
        return 4321, "state/launcher_ops/semantic_route_refresh.log"

    monkeypatch.setattr(reactions_engine, "_spawn_action_runner", fake_spawn)
    monkeypatch.setattr(reactions_engine, "_pid_running", lambda pid: isinstance(pid, int) and pid > 0)
    reactions_engine.set_engine_armed_state(tmp_path, True)

    snapshot = reactions_engine.tick_engine(tmp_path)
    assert fired == [("semantic_routes_after_embed_refresh", "semantic_route_refresh", {"source": "doctrine"})]
    assert snapshot["active_reaction_id"] == "semantic_routes_after_embed_refresh"


def test_run_action_appends_operation_route_evidence_results(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        reactions_engine,
        "prepare_launch_operation",
        lambda repo_root, operation_id, parameters=None: PreparedLaunch(
            operation={"operation_id": operation_id, "meta_mission_id": None},
            command="echo semantic_route_refresh",
            execution_mode="sync",
            resolved_parameters={},
        ),
    )
    monkeypatch.setattr(reactions_engine, "start_meta_mission_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(reactions_engine, "launcher_meta_mission_env", lambda **kwargs: {})
    monkeypatch.setattr(reactions_engine, "finalize_meta_mission_run", lambda *args, **kwargs: None)

    appended = []

    def fake_append(repo_root, *, evidence_rows, actor_id, operation_id):
        appended.append(
            {
                "repo_root": str(repo_root),
                "evidence_rows": list(evidence_rows),
                "actor_id": actor_id,
                "operation_id": operation_id,
            }
        )
        return [{"status": "recorded", "count": len(evidence_rows)}]

    monkeypatch.setattr(semantic_routing, "append_operation_route_evidence", fake_append)

    class _Proc:
        returncode = 0
        stdout = json.dumps(
            {
                "route_evidence": [
                    {
                        "source_artifact": "doctrine:con_024",
                        "target_artifact": "doctrine:pri_056",
                        "evidence_kind": "operation_success",
                        "note": "auto-confirmed by operation",
                    }
                ],
                "result_summary": {"refreshed_rows": 5},
                "stable_signal_digest": "digest-route-evidence",
            }
        )
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: _Proc())

    exit_code = reactions_engine.run_action(
        tmp_path,
        reaction_id="semantic_routes_after_embed_refresh",
        operation_id="semantic_route_refresh",
        parameters_json=json.dumps({"source": "doctrine"}),
        signal_digest="signal-digest",
        signal_json=json.dumps({"kind": "operation_event"}),
        started_at="2026-04-19T00:00:00+00:00",
    )

    assert exit_code == 0
    assert appended == [
        {
            "repo_root": str(tmp_path),
            "evidence_rows": [
                {
                    "source_artifact": "doctrine:con_024",
                    "target_artifact": "doctrine:pri_056",
                    "evidence_kind": "operation_success",
                    "note": "auto-confirmed by operation",
                }
            ],
            "actor_id": reactions_engine.ENGINE_ACTOR_ID,
            "operation_id": "semantic_route_refresh",
        }
    ]

    operation_events = [
        row
        for row in _load_jsonl_rows(reactions_engine.orchestration_events_path(tmp_path))
        if row["kind"] == "operation_launched"
    ]
    assert len(operation_events) == 1
    assert operation_events[0]["route_evidence_results"] == [{"status": "recorded", "count": 1}]


def _sample_route_drift_payload(**overrides) -> dict:
    payload = {
        "kind": "semantic_route_drift",
        "schema_version": "semantic_route_drift_v1",
        "generated_at": "2026-04-21T00:00:00Z",
        "axis_registry_hash": "axis-1",
        "evidence_summary_fingerprint": "evidence-a",
        "drift_count": 1,
        "drifts": [
            {
                "bridge_id": "python_claim_chain",
                "source_row_key": "python_holographic:system/lib/example.py:purpose",
                "source_kind": "python_holographic",
                "source_id": "system/lib/example.py",
                "source_facet": "purpose",
                "target_kind": "paper_modules",
                "expected_target_facets": ["tldr"],
                "min_score": 0.45,
                "best_match": {
                    "target_row_key": "paper_modules:semantic_routing_plane:tldr",
                    "target_kind": "paper_modules",
                    "target_id": "semantic_routing_plane",
                    "target_facet": "tldr",
                    "target_source_path": "codex/doctrine/paper_modules/semantic_routing_plane.md",
                    "semantic_score": 0.42,
                    "adjusted_score": 0.37,
                },
                "drift_reason": "below_threshold",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_route_drift_snapshot_digest_ignores_timestamp_and_evidence_output_churn() -> None:
    baseline = _sample_route_drift_payload()
    same_work = _sample_route_drift_payload(
        generated_at="2026-04-22T00:00:00Z",
        evidence_summary_fingerprint="evidence-b",
        drifts=[
            {
                **baseline["drifts"][0],
                "best_match": {
                    **baseline["drifts"][0]["best_match"],
                    "adjusted_score": 0.11,
                    "target_source_path": "changed/generated/path.md",
                },
            }
        ],
    )
    changed_work = _sample_route_drift_payload(
        drifts=[
            {
                **baseline["drifts"][0],
                "best_match": {
                    **baseline["drifts"][0]["best_match"],
                    "semantic_score": 0.12,
                },
            }
        ],
    )

    assert semantic_routing.route_drift_snapshot_digest(baseline) == semantic_routing.route_drift_snapshot_digest(same_work)
    assert semantic_routing.route_drift_snapshot_digest(baseline) != semantic_routing.route_drift_snapshot_digest(changed_work)


def test_route_quality_audit_reuses_completed_report_for_same_drift_digest(tmp_path: Path, monkeypatch) -> None:
    drift = _sample_route_drift_payload()
    digest = semantic_routing.route_drift_snapshot_digest(drift)[:16]
    _write_json(tmp_path / "state/semantic_routing/route_drift.json", drift)
    report_dir = tmp_path / "state/semantic_routing/route_quality_audit"
    _write_json(
        report_dir / f"{digest}_2026-04-21T00-00-00-000000Z.json",
        {
            "kind": "semantic_route_quality_audit",
            "status": "ok",
            "dry_run": False,
            "operation_id": f"semantic_route_quality_audit_{digest}",
            "finished_at": "2026-04-21T00:01:00Z",
            "totals": {"confirmations_written": 1, "rejections_written": 0, "nim_errors": 0, "parse_errors": 0},
        },
    )

    monkeypatch.setattr(semantic_route_quality_audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(semantic_route_quality_audit, "AUDIT_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        semantic_route_quality_audit,
        "audit_node_with_k2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("K2 should not be called")),
    )

    result = semantic_route_quality_audit.run_audit(
        sample=8,
        model="kimi-k2-thinking",
        max_neighbors=5,
        max_tokens=1800,
        dry_run=False,
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "drift_snapshot_already_audited"
    assert result["drift_snapshot_digest"] == digest


def test_routing_metabolism_status_reports_digest_cache_and_runner_health(tmp_path: Path, monkeypatch) -> None:
    drift = _sample_route_drift_payload()
    digest = semantic_routing.route_drift_snapshot_digest(drift)[:16]
    _write_json(
        tmp_path / "state/semantic_routing/route_status.json",
        {
            "kind": "semantic_route_status",
            "generated_at": "2026-04-21T00:00:00Z",
            "route_graph_fingerprint": "graph-a",
            "statistics": {"node_count": 3, "edge_count": 7},
        },
    )
    _write_json(tmp_path / "state/semantic_routing/route_drift.json", drift)
    _write_json(
        tmp_path / "state/semantic_routing/route_quality_audit" / f"{digest}_2026-04-21T00-00-00-000000Z.json",
        {
            "kind": "semantic_route_quality_audit",
            "status": "ok",
            "dry_run": False,
            "operation_id": f"semantic_route_quality_audit_{digest}",
            "totals": {"confirmations_written": 1, "rejections_written": 0},
        },
    )
    _write(
        tmp_path / "codex/ledger/semantic_routing/route_evidence.jsonl",
        json.dumps({"note": "quality_audit_confirm conf=0.9: correct", "recorded_at": "2026-04-21T00:01:00Z"}) + "\n",
    )

    monkeypatch.setattr(
        semantic_routing,
        "current_route_staleness",
        lambda _repo_root: {
            "skills": {"stale": True, "record_count": 2, "stale_or_missing": 1, "path": "state/embeddings/skills.json"},
            "doctrine": {"stale": False, "record_count": 10, "stale_or_missing": 0, "path": "state/embeddings/doctrine.json"},
        },
    )
    monkeypatch.setattr(
        kernel_embed,
        "_routing_reaction_snapshot",
        lambda _repo_root: {"engine_status": "armed_waiting_runner", "last_tick_at": "2026-04-20T00:00:00+00:00"},
    )
    monkeypatch.setattr(
        kernel_embed,
        "_routing_provider_budget_status",
        lambda probe_live=False: {"primary_available": True, "policy": {"primary": "NVIDIA NIM"}},
    )

    payload = kernel_embed.build_routing_metabolism_status(tmp_path)

    assert payload["summary"]["current_drift_already_audited"] is True
    assert payload["routing"]["route_drift_digest"] == digest
    assert payload["summary"]["stale_source_count"] == 1
    assert payload["summary"]["quality_audit_evidence_rows"] == 1
    assert payload["summary"]["next_recommended_command"] == "./repo-python tools/meta/control/reactions_engine.py run"
