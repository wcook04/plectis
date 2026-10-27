"""Absent pre-flip views are source-derived; broken materializations stay errors."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from microcosm_core import doctrine_lattice as d

SOURCE_ROOT = Path(os.environ.get("PLECTIS_TEST_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
COUNTS = {"axiom":12, "principle":20, "anti_principle":17, "concept":11, "mechanism":95, "organ":88}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value)+"\n")


def rows(kind, flip="not_flipped"):
    return {key: {"id":key,"kind":kind,"title":key,"relationships":{"source_routing_row_ref":"core/source.json::"+key,"edges":[]},
                  f"{kind}_payload":{"migration_contract":{"authority_flip_status":flip}}}
            for key in ("first","second")}


def fixture_family(monkeypatch, kind, expected):
    monkeypatch.setattr(d, f"expected_{kind}_instances", lambda root:deepcopy(expected))
    monkeypatch.setattr(d,"_instance_required_fields", lambda root, selected:{"id","kind","relationships",f"{selected}_payload"})


@pytest.mark.parametrize("kind,count",COUNTS.items())
def test_real_absent_corpus_counts_disk_and_derivation_separately(kind,count):
    validate=getattr(d,f"validate_{kind}_instance_corpus")
    result=validate(SOURCE_ROOT)
    assert result["status"] == "pass"
    assert result["json_instance_count"] == result["materialized_json_file_count"] == 0
    assert result["effective_instance_count"] == result["derived_instance_count"] == count
    assert len(result["missing_json_ids"]) == count
    assert result["parity_status"] == "not_materialized"
    assert result["validation_basis"] == "canonical_source_derivation"
    corpus=getattr(d,f"build_{kind}_instance_corpus")(SOURCE_ROOT)
    assert corpus["validation_status"] == "pass"
    assert corpus["parity_status"] == "not_materialized"
    assert corpus["source_refs"]["json_instances"] is None


@pytest.mark.parametrize("kind",COUNTS)
@pytest.mark.parametrize("mode",["partial","stale","md_only","wrong_filename","missing_id"])
def test_partial_stale_or_malformed_materialization_never_falls_back(tmp_path,monkeypatch,kind,mode):
    expected=rows(kind); fixture_family(monkeypatch,kind,expected)
    path_for=getattr(d,f"_{kind}_instance_rel")
    if mode=="md_only":
        path=tmp_path/Path(path_for("first")).with_suffix(".md");path.parent.mkdir(parents=True);path.write_text("partial view")
    elif mode=="missing_id": write(tmp_path/path_for("first"),{"kind":kind})
    elif mode=="wrong_filename": write(tmp_path/Path(path_for("first")).parent/"wrong.json",expected["first"])
    else:
        write(tmp_path/path_for("first"),expected["first"])
        if mode=="stale":
            stale=deepcopy(expected["second"]);stale["title"]="stale";write(tmp_path/path_for("second"),stale)
    result=getattr(d,f"validate_{kind}_instance_corpus")(tmp_path)
    assert result["status"] == "blocked"
    assert result["derived_instance_count"] == 0
    assert result["validation_basis"] == "materialized_json_parity"
    assert result["errors"]


@pytest.mark.parametrize("kind",COUNTS)
def test_authority_flipped_corpus_requires_materialized_instances(tmp_path,monkeypatch,kind):
    fixture_family(monkeypatch,kind,rows(kind,flip="flipped"))
    result=getattr(d,f"validate_{kind}_instance_corpus")(tmp_path)
    assert result["status"] == "blocked"
    assert result["derived_instance_count"] == 0
    assert {error["code"] for error in result["errors"]} == {f"{kind}_json_instance_missing"}


@pytest.mark.parametrize("kind",COUNTS)
def test_full_materialization_still_requires_exact_canonical_parity(tmp_path,monkeypatch,kind):
    expected=rows(kind);fixture_family(monkeypatch,kind,expected)
    for key,row in expected.items():write(tmp_path/getattr(d,f"_{kind}_instance_rel")(key),row)
    result=getattr(d,f"validate_{kind}_instance_corpus")(tmp_path)
    assert result["status"] == result["parity_status"] == "pass"
    assert result["json_instance_count"] == result["materialized_json_file_count"] == result["effective_instance_count"] == 2
    assert result["derived_instance_count"] == 0


def test_missing_or_changed_malformed_canonical_source_cannot_use_cached_derivation(tmp_path):
    for rel in [d.AXIOM_ROUTING_REL,*[d._standard_rel(kind) for kind in d.KIND_STANDARD_IDS]]:
        target=tmp_path/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((SOURCE_ROOT/rel).read_bytes())
    assert d.validate_axiom_instance_corpus(tmp_path)["effective_instance_count"] == 12
    source=tmp_path/d.AXIOM_ROUTING_REL
    source.write_text('{"invalid":')
    with pytest.raises(ValueError):d.validate_axiom_instance_corpus(tmp_path)
    source.unlink()
    with pytest.raises(FileNotFoundError):d.validate_axiom_instance_corpus(tmp_path)
    write(source,{"rows":[]})
    result=d.validate_axiom_instance_corpus(tmp_path)
    assert result["status"]=="blocked"
    assert any(error["code"]=="axiom_canonical_source_empty" for error in result["errors"])


def test_malformed_materialized_json_is_not_treated_as_absence(tmp_path,monkeypatch):
    fixture_family(monkeypatch,"axiom",rows("axiom"))
    path=tmp_path/d._axiom_instance_rel("first");path.parent.mkdir(parents=True);path.write_text('{"id":')
    with pytest.raises(ValueError):d.validate_axiom_instance_corpus(tmp_path)


def test_principle_governance_preserves_planned_and_distinguishes_unknown(tmp_path):
    write(tmp_path/"core/organ_atlas.json",{"organs":[{"organ_id":"foo","principle_refs":["P-1"],"mechanism_refs":[
        {"ref":"mechanism.planned","resolution_status":"planned_unresolved"},
        {"ref":"mechanism.unknown","resolution_status":"resolved"},
        {"ref":"mechanism.known","resolution_status":"resolved"},
    ]}]})
    write(tmp_path/d.MECHANISM_REGISTRY_REL,{"mechanisms":[{"id":"mechanism.known"}]})
    lifted=d._principle_mechanism_governance_from_organ_atlas(tmp_path)["P-1"]
    principle=d.build_principle_instance_from_source_row({"id":"P-1","governs_mechanisms":lifted})
    statuses={edge["target_id"]:edge["target_status"] for edge in principle["relationships"]["edges"]}
    assert statuses == {"mechanism.planned":"planned_unresolved_mechanism","mechanism.unknown":"unresolved_json_instance","mechanism.known":"resolved_json_instance"}


def test_real_projection_has_truthful_source_refs_and_all_derived_nodes():
    projection=d.build_doctrine_projection(SOURCE_ROOT,generated_at="focused_check")
    assert projection["status"] == "pass"
    nodes={(node["kind"],node["id"]):node for node in projection["nodes"]}
    for kind,count in COUNTS.items():
        selected=[node for node in nodes.values() if node["kind"]==kind]
        assert len(selected)==count
        for node in selected:
            assert node["materialization_status"] == "source_derived_not_materialized"
            assert node["materialized_json_ref"] is None
            assert (SOURCE_ROOT/node["source_ref"].split("::",1)[0]).is_file()
        assert projection["source_refs"][f"{kind}_instances"] is None
    assert not [edge for edge in projection["edges"] if edge.get("target_status")=="unresolved_json_instance" and edge.get("target_kind")=="mechanism"]
    for edge in projection["edges"]:
        if edge.get("target_status")=="resolved_source_instance":
            target=nodes[(edge["target_kind"],edge["target_id"])]
            assert edge["target_source_ref"]==target["source_ref"]
    planned=[edge for edge in projection["edges"] if edge["relation_id"]=="principle.governs.mechanism" and edge["target_status"]=="planned_unresolved_mechanism"]
    assert len(planned)==13


def test_unknown_unplanned_target_remains_a_blocking_projection_error(monkeypatch):
    original=d.build_doctrine_projection
    def corrupt(*args,**kwargs):
        result=original(*args,**kwargs)
        result["edges"].append({"source_kind":"principle","source_id":"P-1","relation_id":"principle.governs.mechanism",
            "target_kind":"mechanism","target_id":"mechanism.unknown","target_status":"unresolved_json_instance",
            "justification":{"source_ref":"core/organ_atlas.json::organs[0]","summary":"Unplanned unknown target."}})
        return result
    monkeypatch.setattr(d,"build_doctrine_projection",corrupt)
    result=d.validate_doctrine_projection(SOURCE_ROOT)
    assert result["status"]=="blocked"
    assert any(error["code"]=="doctrine_projection_unplanned_target_unresolved" and error["target_id"]=="mechanism.unknown" for error in result["errors"])


def test_graph_writer_uses_effective_source_instances(tmp_path,monkeypatch):
    for kind in COUNTS:
        monkeypatch.setattr(d,f"expected_{kind}_instances",lambda root,kind=kind:rows(kind) if kind=="axiom" else {})
    for kind in ("paper_module","skill"):
        monkeypatch.setattr(d,f"expected_{kind}_instances",lambda root:{})
    monkeypatch.setattr(d,"expected_standard_instances",lambda root:{})
    monkeypatch.setattr(d,"load_standard_instances",lambda root,**kwargs:{})
    monkeypatch.setattr(d,"build_doctrine_projection",lambda *args,**kwargs:{"coverage_health":{},"status":"pass"})
    d.write_doctrine_projection(tmp_path)
    graph=(tmp_path/d.DOCTRINE_GRAPH_REL).read_text()
    assert "axiom:first" in graph and "axiom:second" in graph
    assert not (tmp_path/d.AXIOM_INSTANCE_DIR_REL).exists()
