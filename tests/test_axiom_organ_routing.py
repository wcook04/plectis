from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids_from_markdown(path: Path, prefix: str) -> set[str]:
    pattern = re.compile(rf"^## ({re.escape(prefix)}-\d+)\b", re.MULTILINE)
    return set(pattern.findall(path.read_text(encoding="utf-8")))


def _anti_principle_axiom_refs(path: Path) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("| AP-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        anti_id = cells[0].split(" ", 1)[0]
        refs[anti_id] = set(re.findall(r"\bAX-\d+\b", cells[1]))
    return refs


def _anti_principle_refs_by_axiom(path: Path) -> dict[str, set[str]]:
    refs_by_axiom: dict[str, set[str]] = {}
    for anti_id, axiom_refs in _anti_principle_axiom_refs(path).items():
        for axiom_ref in axiom_refs:
            refs_by_axiom.setdefault(axiom_ref, set()).add(anti_id)
    return refs_by_axiom


def _surface_path(ref: str) -> Path:
    return MICROCOSM_ROOT / ref.split("::", 1)[0]


def _doctrine_record_json_paths() -> list[Path]:
    return sorted(
        list((MICROCOSM_ROOT / "axioms").glob("AX-*.json"))
        + list((MICROCOSM_ROOT / "principles").glob("P-*.json"))
        + list((MICROCOSM_ROOT / "anti_principles").glob("AP-*.json"))
    )


def _json_ids(directory: str, pattern: str = "*.json") -> set[str]:
    ids: set[str] = set()
    for path in (MICROCOSM_ROOT / directory).glob(pattern):
        ids.add(_load_json(path)["id"])
    return ids


def _all_public_text() -> str:
    chunks: list[str] = []
    for base in ("src", "tests", "fixtures", "examples", "core", "paper_modules"):
        root = MICROCOSM_ROOT / base
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".json", ".md", ".lean"}:
                chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def test_axiom_routing_matches_markdown_and_registry() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    rows = routing["rows"]

    axiom_ids = {row["axiom_id"] for row in rows}
    principle_ids = {
        principle_id
        for row in rows
        for principle_id in row.get("principle_ids", [])
    }

    assert routing["axiom_count"] == len(rows) == 12
    assert routing["principle_count"] == len(principle_ids) == 20
    assert "P-20" in principle_ids
    assert axiom_ids == _ids_from_markdown(MICROCOSM_ROOT / "AXIOMS.md", "AX")
    assert principle_ids.issubset(
        _ids_from_markdown(MICROCOSM_ROOT / "PRINCIPLES.md", "P")
    )
    assert "microcosm_axiom_substrate.md" in {
        path.name for path in (MICROCOSM_ROOT / "paper_modules").glob("*.md")
    }

    registry = _load_json(MICROCOSM_ROOT / "core/organ_registry.json")
    organ_ids = {row["organ_id"] for row in registry["implemented_organs"]}
    valid_strengths = set(routing["strength_scale"])

    for row in rows:
        assert row["witness_strength"] in valid_strengths
        assert row["witness_organs"]
        assert row["witness_surfaces"]
        assert set(row.get("witness_organs", [])).issubset(organ_ids)
        for ref in row.get("witness_surfaces", []):
            if "*" in ref:
                assert list(MICROCOSM_ROOT.glob(ref)), ref
            else:
                assert _surface_path(ref).exists(), ref


def test_doctrine_records_bind_resolving_receipt_bodies() -> None:
    required_receipt_fields = {
        "validator_id",
        "result",
        "evidence_refs",
        "omissions",
        "authority_ceiling",
    }
    paths = _doctrine_record_json_paths()
    assert len([path for path in paths if path.parent.name == "axioms"]) == 12
    assert len([path for path in paths if path.parent.name == "principles"]) == 20
    assert len([path for path in paths if path.parent.name == "anti_principles"]) == 17

    for record_path in paths:
        record = _load_json(record_path)
        receipt_refs = record.get("receipt_refs", [])
        assert receipt_refs, record_path
        for receipt_ref in receipt_refs:
            assert receipt_ref.startswith("receipts/doctrine_records/")
            receipt_path = MICROCOSM_ROOT / receipt_ref
            assert receipt_path.exists(), (record_path, receipt_ref)
            receipt = _load_json(receipt_path)
            assert not required_receipt_fields - set(receipt), receipt_path
            assert receipt["record_id"] == record["id"]
            assert receipt["record_kind"] == record["kind"]
            assert receipt["result"] == "pass"
            assert receipt["evidence_refs"], receipt_path
            assert receipt["omissions"], receipt_path
            ceiling = receipt["authority_ceiling"]
            assert ceiling["release_authority"] is False
            assert ceiling["private_data_equivalence_authority"] is False
            assert ceiling["source_body_authority"] is False


def test_axiom_layer_debt_rows_bind_receipts_and_ceilings() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    debt_count = 0
    for row in routing["rows"]:
        for debt in row.get("layer_debt", []):
            debt_count += 1
            assert debt["status"] == "open_layer_debt"
            assert debt["claim_ceiling"] == "partial_capped_by_layer_debt"
            assert debt["authority_ceiling"]["release_authority"] is False
            assert debt["authority_ceiling"]["whole_system_correctness"] is False
            receipt_ref = debt["receipt_ref"]
            assert receipt_ref.startswith("receipts/doctrine_records/layer_debt/")
            receipt_path = MICROCOSM_ROOT / receipt_ref
            assert receipt_path.exists(), receipt_ref
            receipt = _load_json(receipt_path)
            assert receipt["validator_id"] == "validator.microcosm.axiom_support_cover"
            assert receipt["result"] == "residual_open"
            assert receipt["evidence_refs"]
            assert receipt["omissions"]
            assert receipt["authority_ceiling"]["release_authority"] is False
    assert debt_count == 3


def test_axiom_rows_expand_to_support_receipts() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    contract = routing["support_expansion_contract"]
    assert (
        contract["schema_version"]
        == "microcosm_axiom_routing_support_expansion_v1"
    )
    assert (
        contract["status"]
        == "all_rows_bind_claim_ceiling_and_layer_debt_receipts"
    )
    assert "strongest_allowed_claim remains computed" in contract["authority_boundary"]

    for row in routing["rows"]:
        axiom_id = row["axiom_id"]
        expansion = row["support_expansion"]
        assert (
            expansion["schema_version"]
            == "microcosm_axiom_routing_support_expansion_v1"
        )

        ceiling = expansion["claim_ceiling"]
        assert ceiling["status"] == "computed_read_model_required"
        assert ceiling["validator_id"] == "validator.microcosm.axiom_support_cover"
        assert (
            ceiling["computed_by"]
            == "checker.microcosm.validators.axiom_support_cover"
        )
        assert ceiling["result_ref"].endswith(
            f"::support_frontiers[{axiom_id}].claim_ceiling"
        )
        assert ceiling["authority_ceiling"]["release_authority"] is False
        assert ceiling["authority_ceiling"]["whole_system_correctness"] is False

        debt_receipt = expansion["layer_debt_receipt"]
        declared_receipts = [
            debt["receipt_ref"] for debt in row.get("layer_debt", [])
        ]
        assert debt_receipt["source_ref"] == (
            f"core/axiom_organ_routing.json::rows[{axiom_id}].layer_debt"
        )
        assert debt_receipt["receipt_refs"] == declared_receipts
        assert debt_receipt["status"] == (
            "open_layer_debt_declared"
            if declared_receipts
            else "no_open_layer_debt_declared"
        )
        assert debt_receipt["authority_ceiling"]["release_authority"] is False
        for receipt_ref in declared_receipts:
            receipt = _load_json(MICROCOSM_ROOT / receipt_ref)
            assert receipt["validator_id"] == "validator.microcosm.axiom_support_cover"
            assert receipt["result"] == "residual_open"


def test_axiom_routing_negative_cases_resolve_or_declare_layer_debt() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    public_text = _all_public_text()

    for row in routing["rows"]:
        debt_text = json.dumps(row.get("layer_debt", []), sort_keys=True)
        for code in row.get("negative_case_codes", []):
            assert code in public_text or code in debt_text, (
                row["axiom_id"],
                code,
            )


def test_anti_principles_map_to_current_axioms() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    axiom_ids = {row["axiom_id"] for row in routing["rows"]}
    refs_by_anti = _anti_principle_axiom_refs(
        MICROCOSM_ROOT / "ANTI_PRINCIPLES.md"
    )
    refs_by_axiom = _anti_principle_refs_by_axiom(
        MICROCOSM_ROOT / "ANTI_PRINCIPLES.md"
    )
    routed_anti_ids = {
        anti_id
        for row in routing["rows"]
        for anti_id in row.get("anti_principle_ids", [])
    }
    relation_ids = {
        row["relation_id"]
        for row in _load_json(MICROCOSM_ROOT / "core/doctrine_lattice_relations.json")[
            "relations"
        ]
    }

    assert len(refs_by_anti) >= routing["axiom_count"]
    assert routing["anti_principle_count"] == len(refs_by_anti) == 17
    assert all(refs for refs in refs_by_anti.values())
    assert routed_anti_ids == set(refs_by_anti)
    assert "anti_principle.guards.axiom" in relation_ids
    assert set(refs_by_axiom) == axiom_ids
    for anti_id, refs in refs_by_anti.items():
        assert refs.issubset(axiom_ids), (anti_id, refs - axiom_ids)
    for row in routing["rows"]:
        axiom_id = row["axiom_id"]
        assert set(row.get("anti_principle_ids", [])) == refs_by_axiom[axiom_id]


def test_doctrine_record_typed_links_and_guards_resolve() -> None:
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    axiom_ids = _json_ids("axioms", "AX-*.json")
    principle_ids = _json_ids("principles", "P-*.json")
    anti_principle_ids = _json_ids("anti_principles", "AP-*.json")
    concept_ids = _json_ids("concepts")
    mechanism_ids = _json_ids("mechanisms")
    organ_ids = _json_ids("organs")
    paper_module_ids = _json_ids("paper_modules")
    skill_ids = _json_ids("skills")
    target_ids_by_kind = {
        "anti_principle": anti_principle_ids,
        "axiom": axiom_ids,
        "concept": concept_ids,
        "mechanism": mechanism_ids,
        "organ": organ_ids,
        "paper_module": paper_module_ids,
        "principle": principle_ids,
        "skill": skill_ids,
    }

    obligation_ids = {
        obligation["obligation_id"]
        for row in routing["rows"]
        for obligation in row["obligations"]
    }
    principle_guard_ids = {principle_id: set() for principle_id in principle_ids}
    principle_payload_guard_ids = {principle_id: set() for principle_id in principle_ids}

    for row in routing["rows"]:
        assert row["axiom_id"] in axiom_ids
        assert set(row["principle_ids"]) <= principle_ids
        assert set(row["anti_principle_ids"]) <= anti_principle_ids
        assert row["witness_organs"]
        assert row["witness_surfaces"]
        assert row["negative_case_codes"] or row.get("layer_debt")
        assert row["witness_strength"] in set(routing["strength_scale"])
        for principle_id in row["principle_ids"]:
            principle_guard_ids[principle_id].update(row["anti_principle_ids"])
        for debt in row.get("layer_debt", []):
            assert debt["receipt_ref"].startswith(
                "receipts/doctrine_records/layer_debt/"
            )
            assert (MICROCOSM_ROOT / debt["receipt_ref"]).exists()
            assert debt["claim_ceiling"] == "partial_capped_by_layer_debt"
            assert debt["authority_ceiling"]["release_authority"] is False

    assert all(guards for guards in principle_guard_ids.values())
    assert len(obligation_ids) == 39

    for record_path in _doctrine_record_json_paths():
        record = _load_json(record_path)
        for edge in record.get("relationships", {}).get("edges", []):
            target_kind = edge["target_kind"]
            if str(edge.get("target_status", "")).startswith("planned_"):
                continue
            if target_kind in target_ids_by_kind:
                assert edge["target_id"] in target_ids_by_kind[target_kind], (
                    record_path,
                    edge,
                )

        if record["kind"] != "principle":
            if record["kind"] == "anti_principle":
                payload = record["anti_principle_payload"]
                guarded_principles = set(payload["guarded_principle_ids"])
                assert guarded_principles <= principle_ids
                assert set(record.get("negates", [])) == guarded_principles
                edge_principles = {
                    edge["target_id"]
                    for edge in record.get("relationships", {}).get("edges", [])
                    if edge["relation_id"]
                    == "anti_principle.negates_failure_of.principle"
                }
                assert guarded_principles == edge_principles
                for principle_id in guarded_principles:
                    principle_payload_guard_ids[principle_id].add(record["id"])
            continue
        payload = record["principle_payload"]
        assert set(payload["grounding_axiom_ids"]) <= axiom_ids
        assert set(payload["grounding_obligation_refs"]) <= obligation_ids

    assert all(guards for guards in principle_payload_guard_ids.values())
    assert principle_payload_guard_ids == principle_guard_ids


def test_anti_principle_standard_names_payload_principle_guards() -> None:
    standard = _load_json(
        MICROCOSM_ROOT / "standards/std_microcosm_anti_principle.json"
    )
    boundary = standard["anti_principle_payload_contract"][
        "rejection_mapping_boundary_contract"
    ]

    assert "anti_principle_payload.guarded_principle_ids" in boundary[
        "anti_principle_to_substrate_fields"
    ]
    assert "anti_principle_payload.guarded_principle_ids" in boundary[
        "rejection_mapping_fields"
    ]
    assert any(
        "guarded_principle_ids mirrors negates_failure_of routing"
        in rule
        for rule in boundary["non_laundering_rules"]
    )


def test_axiom_obligation_pilot_structure_resolves() -> None:
    """Obligations decompose a formal clause into checkable units bound only to
    evidence already declared on the row. coverage_tag (strong/partial/blocked)
    is intentionally NOT asserted in source -- it is computed by the planned
    cover evaluator -- so this test checks structure and binding resolution, not
    strength."""
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    rows = {row["axiom_id"]: row for row in routing["rows"]}

    pilot = routing.get("obligation_pilot")
    assert pilot, "obligation_pilot block must be present"
    allowed_status = set(pilot["coverage_status_enum"])
    assert allowed_status == {"pending_cover_evaluator", "layer_debt"}

    piloted = [axiom_id for axiom_id, row in rows.items() if row.get("obligations")]
    assert set(piloted) == {f"AX-{i}" for i in range(1, 13)}

    obligation_id_re = re.compile(r"^AX-\d+\.O\d+\.[a-z0-9_]+$")
    for axiom_id in piloted:
        row = rows[axiom_id]
        debt_ids = {debt["debt_id"] for debt in row.get("layer_debt", [])}
        row_organs = set(row.get("witness_organs", []))
        row_surfaces = set(row.get("witness_surfaces", []))
        row_negatives = set(row.get("negative_case_codes", []))
        for obligation in row["obligations"]:
            assert obligation_id_re.match(obligation["obligation_id"]), obligation
            assert obligation["obligation_id"].startswith(axiom_id + "."), obligation
            assert isinstance(obligation["predicate"], str) and obligation["predicate"].strip()
            assert isinstance(obligation["required"], bool)
            assert obligation["coverage_status"] in allowed_status, obligation
            if obligation["coverage_status"] == "layer_debt":
                assert obligation.get("layer_debt_ref") in debt_ids, obligation
            binding = obligation.get("binding", {})
            # Bindings reference only evidence already declared on the row; the
            # existing parity tests prove those organs/surfaces/codes resolve.
            assert set(binding.get("witness_organs", [])) <= row_organs, obligation
            assert set(binding.get("witness_surfaces", [])) <= row_surfaces, obligation
            assert set(binding.get("negative_case_codes", [])) <= row_negatives, obligation


def test_axiom_anti_axiom_rejection_mappings_are_source_owned_residuals() -> None:
    """Anti-axiom rejection is a separate judgment from positive support.

    The routing source must name one non-certifying mapping row for each required
    obligation, so the support evaluator can route residual pressure from source
    authority instead of inferring hidden fallback mappings.
    """
    routing = _load_json(MICROCOSM_ROOT / "core/axiom_organ_routing.json")
    relation_ids = {
        "unmapped",
        "orthogonal",
        "illustrative_only",
        "partial_overlap",
        "subsumes_obligation",
        "exact_obligation_rejection",
        "conflict_detected",
    }
    pilot = routing["obligation_pilot"]
    assert (
        pilot["anti_axiom_rejection_mapping_status"]
        == "source_owned_non_certifying_rows_for_each_required_obligation"
    )

    for row in routing["rows"]:
        required_obligation_ids = {
            obligation["obligation_id"]
            for obligation in row["obligations"]
            if obligation["required"]
        }
        mappings = {
            mapping["obligation_ref"]: mapping
            for mapping in row["anti_axiom_rejection_mappings"]
        }
        assert set(mappings) == required_obligation_ids
        for obligation_id, mapping in mappings.items():
            assert mapping["mapping_id"] == f"{obligation_id}.anti_axiom_rejection_mapping"
            assert mapping["axiom_ref"] == row["axiom_id"]
            assert mapping["anti_axiom_ref"] == row["anti_axiom"]
            assert mapping["mapping_relation"] in relation_ids
            assert mapping["mapping_verified"] is False
            assert (
                mapping["basis_env"]["source_authority_ref"]
                == f"core/axiom_organ_routing.json::rows[{row['axiom_id']}].anti_axiom_rejection_mappings[]"
            )
            assert "Generated support-cover output" in " ".join(mapping["anti_claims"])
