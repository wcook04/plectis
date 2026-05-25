"""Regression coverage for rung-0 kind atlas navigation."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib import kind_atlas
from system.lib.kind_atlas import build_kind_atlas
from system.lib.standard_option_surface import build_option_surface


REPO_ROOT = Path(__file__).resolve().parents[3]


def _rows_by_id(payload: dict) -> dict[str, dict]:
    return {row["kind_id"]: row for row in payload["rows"]}


def test_python_scope_meta_reads_top_level_meta_without_full_index(tmp_path, monkeypatch) -> None:
    index_path = tmp_path / kind_atlas.PYTHON_SCOPE_INDEX
    index_path.parent.mkdir(parents=True)
    meta = {
        "file_count": 2,
        "scope_count": 7,
        "generated_at": "2026-05-11T00:00:00Z",
    }
    index_path.write_text(
        json.dumps(
            {
                "__meta": meta,
                "files": [{"path": "a.py"}, {"path": "b.py"}],
                "scopes": [{"symbol_id": f"s{i}"} for i in range(7)],
            }
        ),
        encoding="utf-8",
    )

    def fail_full_parse(path: Path) -> dict:
        if path == index_path:
            raise AssertionError("python scope metadata should not require full JSON parse")
        return {}

    monkeypatch.setattr(kind_atlas, "_load_json", fail_full_parse)

    assert kind_atlas._python_scope_meta(tmp_path) == meta


def test_kind_atlas_governance_lives_only_on_top_level_navigation_boundary() -> None:
    """Governance fields are static across rows and live on the top-level
    navigation_boundary, not duplicated on every row.

    Pre-fix, each of 41 rows carried surface_role, first_contact_allowed,
    control_replacement, allowed_callers, banned_callers — five fields with
    the same value across all rows, costing ~12KB of redundant bytes and
    confusing consumers about which level is the boundary authority.
    The contract: the *packet* declares the boundary; rows describe per-kind
    state. Repeating governance per row inverts that authority.
    """
    payload = build_kind_atlas(REPO_ROOT, band="flag")

    boundary = payload["navigation_boundary"]
    assert boundary["surface_role"] == "ATLAS_PROJECTION"
    assert boundary["first_contact_allowed"] is False
    assert boundary["control_replacement"].startswith(
        "./repo-python kernel.py --entry"
    )
    assert boundary["not_keyword_search"] is True

    redundant_governance_fields = (
        "surface_role",
        "first_contact_allowed",
        "control_replacement",
        "allowed_callers",
        "banned_callers",
    )
    for row in payload["rows"]:
        for field in redundant_governance_fields:
            assert field not in row, (
                f"row {row.get('kind_id')!r} carries redundant governance "
                f"field {field!r}; navigation_boundary is the sole authority"
            )


def test_kind_atlas_flag_enumerates_required_kinds_without_query() -> None:
    payload = build_kind_atlas(REPO_ROOT, band="flag")

    assert payload["kind"] == "kind_atlas"
    assert payload["profile_status"] == "supported"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_enumeration"
    assert (
        payload["summary"]["supported_option_surface_count"]
        + payload["summary"]["legacy_command_only_count"]
        + payload["summary"]["profile_gap_count"]
    ) == payload["summary"]["row_count"]
    assert payload["summary"]["legacy_command_only_count"] == 0
    assert payload["summary"]["profile_gap_count"] == 0

    rows = _rows_by_id(payload)
    assert {
        "paper_modules",
        "standards",
        "derived_facts",
        "python_files",
        "python_scopes",
        "frontend_views",
        "frontend_components",
        "skills",
        "system_terms",
        "principles",
        "teleologies",
        "principles_by_teleology",
        "anti_principles",
        "axioms_by_teleology",
        "anti_axioms",
        "axiom_candidates",
        "raw_seed_shards",
        "compression_profiles",
        "microcosm_extracted_patterns",
        "annex_patterns",
        "annex_distillation_patterns",
    } <= set(rows)


def test_kind_atlas_marks_supported_rows_and_projection_gaps() -> None:
    rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))

    assert rows["paper_modules"]["support_status"] == "option_surface_supported"
    assert rows["paper_modules"]["option_surface_command"].endswith("--option-surface paper_modules --band cluster_flag")
    assert rows["paper_modules"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["standards"]["support_status"] == "option_surface_supported"
    assert rows["standards"]["option_surface_command"].endswith("--option-surface standards --band cluster_flag")
    assert rows["standards"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["derived_facts"]["support_status"] == "option_surface_supported"
    assert rows["derived_facts"]["option_surface_command"] == "./repo-python kernel.py --facts --band cluster_flag"
    assert rows["derived_facts"]["cluster_command"] == "./repo-python kernel.py --facts --band cluster_flag"
    assert rows["derived_facts"]["evidence_command"].endswith("tools/meta/factory/build_fact_hologram.py --check")
    assert rows["derived_facts"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["derived_facts"]["row_count"] > 0
    assert rows["derived_facts"]["currentness"]["owner_surface_command"] == "./repo-python kernel.py --facts --band cluster_flag"
    assert rows["derived_facts"]["currentness"]["check_command"].endswith("build_fact_hologram.py --check")
    assert rows["derived_facts"]["currentness"]["status"] in {
        "generated_state_axis_artifact",
        "live_fact_surface_available_generated_outputs_missing",
    }
    assert rows["principles"]["support_status"] == "option_surface_supported"
    assert rows["principles"]["option_surface_command"].endswith("--option-surface principles --band cluster_flag")
    assert rows["principles"]["cluster_command"].endswith("--option-surface principles --band cluster_flag")
    assert rows["principles"]["bands"] == ["cluster_flag", "flag", "card", "tape"]
    assert rows["teleologies"]["support_status"] == "option_surface_supported"
    assert rows["teleologies"]["option_surface_command"].endswith("--option-surface teleologies --band cluster_flag")
    assert rows["teleologies"]["cluster_command"].endswith("--option-surface teleologies --band cluster_flag")
    assert rows["teleologies"]["card_command"].endswith("--option-surface teleologies --band card --ids <tel_id>")
    assert rows["teleologies"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["principles_by_teleology"]["support_status"] == "option_surface_supported"
    assert rows["principles_by_teleology"]["option_surface_command"].endswith(
        "--option-surface principles_by_teleology --band flag"
    )
    assert rows["anti_principles"]["support_status"] == "option_surface_supported"
    assert rows["anti_principles"]["option_surface_command"].endswith(
        "--option-surface anti_principles --band flag"
    )
    assert rows["axioms_by_teleology"]["support_status"] == "option_surface_supported"
    assert rows["axioms_by_teleology"]["option_surface_command"].endswith(
        "--option-surface axioms_by_teleology --band flag"
    )
    assert rows["anti_axioms"]["support_status"] == "option_surface_supported"
    assert rows["anti_axioms"]["option_surface_command"].endswith(
        "--option-surface anti_axioms --band flag"
    )
    assert rows["anti_axioms"]["card_command"].endswith(
        "--option-surface anti_axioms --band card --ids <anti_axiom_id>"
    )
    assert rows["anti_axioms"]["bands"] == ["flag", "card"]
    assert rows["axiom_candidates"]["support_status"] == "option_surface_supported"
    assert rows["axiom_candidates"]["option_surface_command"].endswith("--option-surface axiom_candidates --band flag")
    assert rows["compression_profiles"]["support_status"] == "option_surface_supported"
    assert rows["compression_profiles"]["option_surface_command"].endswith(
        "--option-surface compression_profiles --band flag"
    )
    assert rows["compression_profiles"]["card_command"].endswith(
        "--option-surface compression_profiles --band card --ids <profile_id>"
    )
    assert rows["compression_profiles"]["bands"] == ["flag", "card"]
    assert rows["compression_profiles"]["profile_gap"] is None
    assert rows["system_terms"]["support_status"] == "option_surface_supported"
    assert rows["system_terms"]["option_surface_command"].endswith("--option-surface system_terms --band flag")
    assert rows["system_terms"]["card_command"].endswith("--option-surface system_terms --band card --ids <term_id>")
    assert rows["system_terms"]["bands"] == ["flag", "card"]
    assert rows["system_terms"]["profile_gap"] is None
    assert rows["skills"]["support_status"] == "option_surface_supported"
    assert rows["skills"]["option_surface_command"].endswith("--option-surface skills --band cluster_flag")
    assert rows["skills"]["card_command"].endswith("--option-surface skills --band card --ids <skill_id>")
    assert rows["skills"]["evidence_command"].endswith("--skill-find profile_governed_compression --debug")
    assert rows["skills"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["skills"]["profile_gap"] is None
    assert rows["frontend_views"]["support_status"] == "option_surface_supported"
    assert rows["frontend_views"]["option_surface_command"].endswith("--option-surface frontend_views --band cluster_flag")
    assert rows["frontend_views"]["cluster_command"].endswith("--option-surface frontend_views --band cluster_flag")
    assert rows["frontend_views"]["card_command"].endswith(
        "--option-surface frontend_views --band card --ids <view_id>"
    )
    assert rows["frontend_views"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["frontend_views"]["profile_gap"] is None
    assert rows["raw_seed_shards"]["support_status"] == "option_surface_supported"
    assert rows["raw_seed_shards"]["option_surface_command"].endswith("--option-surface raw_seed_shards --band flag")
    assert rows["raw_seed_shards"]["card_command"].endswith(
        "--option-surface raw_seed_shards --band card --ids <shard_id>"
    )
    assert rows["raw_seed_shards"]["bands"] == ["flag", "card"]
    assert rows["raw_seed_shards"]["profile_gap"] is None
    assert rows["type_a_autonomous_seeds"]["support_status"] == "option_surface_supported"
    assert rows["type_a_autonomous_seeds"]["option_surface_command"].endswith(
        "--option-surface type_a_autonomous_seeds --band cluster_flag"
    )
    assert rows["type_a_autonomous_seeds"]["cluster_command"].endswith(
        "--option-surface type_a_autonomous_seeds --band cluster_flag"
    )
    assert rows["type_a_autonomous_seeds"]["card_command"].endswith(
        "--option-surface type_a_autonomous_seeds --band card --ids <seed_id>"
    )
    assert rows["type_a_autonomous_seeds"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["type_a_autonomous_seeds"]["profile_gap"] is None
    assert rows["annex_patterns"]["support_status"] == "option_surface_supported"
    assert rows["annex_patterns"]["option_surface_command"].endswith(
        "--option-surface annex_patterns --band cluster_flag"
    )
    assert rows["annex_patterns"]["card_command"].endswith(
        "--option-surface annex_patterns --band card --ids <slug>:<note_id>"
    )
    assert rows["annex_patterns"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["annex_patterns"]["profile_gap"] is None
    assert rows["annex_patterns"]["row_count"] > 0
    assert rows["annex_distillation_patterns"]["support_status"] == "option_surface_supported"
    assert rows["annex_distillation_patterns"]["option_surface_command"].endswith(
        "--option-surface annex_distillation_patterns --band cluster_flag"
    )
    assert rows["annex_distillation_patterns"]["card_command"].endswith(
        "--option-surface annex_distillation_patterns --band card --ids <slug>:<pNNN>"
    )
    assert rows["annex_distillation_patterns"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["annex_distillation_patterns"]["profile_gap"] is None
    assert rows["annex_distillation_patterns"]["row_count"] > 0
    assert rows["microcosm_extracted_patterns"]["support_status"] == "option_surface_supported"
    assert rows["microcosm_extracted_patterns"]["option_surface_command"].endswith(
        "--option-surface microcosm_extracted_patterns --band cluster_flag"
    )
    assert rows["microcosm_extracted_patterns"]["card_command"].endswith(
        "--option-surface microcosm_extracted_patterns --band card --ids <pattern_id>"
    )
    assert rows["microcosm_extracted_patterns"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["microcosm_extracted_patterns"]["profile_gap"] is None
    assert rows["microcosm_extracted_patterns"]["row_count"] > 0
    assert rows["python_files"]["support_status"] == "option_surface_supported"
    assert rows["python_files"]["option_surface_command"].endswith(
        "--option-surface python_files --band cluster_flag"
    )
    assert rows["python_files"]["card_command"].endswith(
        "--option-surface python_files --band card --ids <file_id>"
    )
    assert rows["python_files"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["python_files"]["profile_gap"] is None
    assert rows["python_files"]["row_count"] > 100

    assert rows["python_scopes"]["support_status"] == "option_surface_supported"
    assert rows["python_scopes"]["option_surface_command"].endswith(
        "--option-surface python_scopes --band cluster_flag"
    )
    assert rows["python_scopes"]["card_command"].endswith(
        "--option-surface python_scopes --band card --ids <symbol_id>"
    )
    assert rows["python_scopes"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["python_scopes"]["profile_gap"] is None
    assert rows["python_scopes"]["row_count"] > rows["python_files"]["row_count"]
    assert rows["frontend_components"]["support_status"] == "option_surface_supported"
    assert rows["frontend_components"]["option_surface_command"].endswith(
        "--option-surface frontend_components --band cluster_flag"
    )
    assert rows["frontend_components"]["card_command"].endswith(
        "--option-surface frontend_components --band card --ids <component_id>"
    )
    assert rows["frontend_components"]["bands"] == ["cluster_flag", "flag", "card"]
    assert rows["frontend_components"]["profile_gap"] is None
    assert rows["frontend_components"]["row_count"] > 0
    # row_count tracks high+medium-confidence primary rows; the projection's full
    # candidate count (including low-confidence helpers/constants) is intentionally
    # higher and surfaces in the option-surface adapter summary, not here.
    assert rows["frontend_components"]["row_count"] < 200


def test_kind_atlas_fast_path_keeps_source_cluster_promotions_cluster_first() -> None:
    rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag", fast=True))

    assert rows["frontend_views"]["option_surface_command"].endswith(
        "--option-surface frontend_views --band cluster_flag"
    )
    assert rows["frontend_views"]["cluster_command"].endswith(
        "--option-surface frontend_views --band cluster_flag"
    )
    assert "cluster_flag" in rows["frontend_views"]["bands"]
    assert rows["type_a_autonomous_seeds"]["option_surface_command"].endswith(
        "--option-surface type_a_autonomous_seeds --band cluster_flag"
    )
    assert rows["type_a_autonomous_seeds"]["cluster_command"].endswith(
        "--option-surface type_a_autonomous_seeds --band cluster_flag"
    )
    assert "cluster_flag" in rows["type_a_autonomous_seeds"]["bands"]


def test_kind_atlas_card_exposes_rung_support_and_omissions() -> None:
    payload = build_kind_atlas(REPO_ROOT, band="card")
    rows = _rows_by_id(payload)

    paper = rows["paper_modules"]
    assert paper["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert paper["known_next_moves"][0].endswith("--option-surface paper_modules --band cluster_flag")
    assert "full module markdown bodies" in paper["omission_receipt"]["omitted"]

    facts = rows["derived_facts"]
    assert facts["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert facts["known_next_moves"][0] == "./repo-python kernel.py --facts --band cluster_flag"
    assert "full fact ledger rows" in facts["omission_receipt"]["omitted"]

    python_scopes_card = rows["python_scopes"]
    assert python_scopes_card["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert python_scopes_card["known_next_moves"][0].endswith(
        "--option-surface python_scopes --band cluster_flag"
    )
    assert "full Python source bodies" in python_scopes_card["omission_receipt"]["omitted"]
    assert python_scopes_card["profile_gap"] is None

    principles = rows["principles"]
    assert principles["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert principles["known_next_moves"][0].endswith("--option-surface principles --band cluster_flag")

    compression = rows["compression_profiles"]
    assert compression["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert compression["known_next_moves"][0].endswith("--option-surface compression_profiles --band flag")
    assert "native context/deep profile bands are card data" in compression["omission_receipt"]["omitted"][0]

    system_terms = rows["system_terms"]
    assert system_terms["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert system_terms["known_next_moves"][0].endswith("--option-surface system_terms --band flag")
    assert "native word/phrase/context/deep term bands are card data" in system_terms["omission_receipt"]["omitted"][0]

    skills = rows["skills"]
    assert skills["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert skills["known_next_moves"][0].endswith("--option-surface skills --band cluster_flag")
    assert "native triggers/workflow/evidence skill bands are card data" in skills["omission_receipt"]["omitted"][0]

    frontend_views = rows["frontend_views"]
    assert frontend_views["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert frontend_views["known_next_moves"][0].endswith("--option-surface frontend_views --band cluster_flag")
    assert "full UI source bodies" in frontend_views["omission_receipt"]["omitted"]

    raw_seed_shards = rows["raw_seed_shards"]
    assert raw_seed_shards["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert raw_seed_shards["known_next_moves"][0].endswith("--option-surface raw_seed_shards --band flag")
    assert "raw voice paragraph bodies" in raw_seed_shards["omission_receipt"]["omitted"]

    type_a_seeds = rows["type_a_autonomous_seeds"]
    assert type_a_seeds["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert type_a_seeds["known_next_moves"][0].endswith(
        "--option-surface type_a_autonomous_seeds --band cluster_flag"
    )
    assert "row-level autonomous seed flags outside selected clusters" in type_a_seeds["omission_receipt"]["omitted"]

    annex_patterns = rows["annex_patterns"]
    assert annex_patterns["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert annex_patterns["known_next_moves"][0].endswith("--option-surface annex_patterns --band cluster_flag")
    assert "external source repository bodies" in annex_patterns["omission_receipt"]["omitted"]

    annex_distillation_patterns = rows["annex_distillation_patterns"]
    assert annex_distillation_patterns["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert annex_distillation_patterns["known_next_moves"][0].endswith(
        "--option-surface annex_distillation_patterns --band cluster_flag"
    )
    assert "adoption status mutation or pattern landing" in annex_distillation_patterns["omission_receipt"]["omitted"]

    microcosm_extracted_patterns = rows["microcosm_extracted_patterns"]
    assert microcosm_extracted_patterns["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert microcosm_extracted_patterns["known_next_moves"][0].endswith(
        "--option-surface microcosm_extracted_patterns --band cluster_flag"
    )
    assert "public release or leaf projection authorization" in microcosm_extracted_patterns["omission_receipt"]["omitted"]

    python_files = rows["python_files"]
    assert python_files["rung_support"]["rung_1_kind_option_surface"] == "option_surface_supported"
    assert python_files["known_next_moves"][0].endswith("--option-surface python_files --band cluster_flag")
    assert "full Python source bodies" in python_files["omission_receipt"]["omitted"]


def test_kind_atlas_annex_patterns_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "annex_patterns", band="flag")

    assert atlas_rows["annex_patterns"]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_annex_distillation_patterns_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "annex_distillation_patterns", band="flag")

    assert atlas_rows["annex_distillation_patterns"]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_microcosm_extracted_patterns_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "microcosm_extracted_patterns", band="flag")

    assert atlas_rows["microcosm_extracted_patterns"]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_python_files_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "python_files", band="flag")

    assert atlas_rows["python_files"]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_python_scopes_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "python_scopes", band="flag")

    assert atlas_rows["python_scopes"]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_teleology_row_counts_match_option_surface_totals() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))

    for kind in ("teleologies", "principles_by_teleology", "anti_principles", "axioms_by_teleology", "anti_axioms"):
        surface = build_option_surface(REPO_ROOT, kind, band="flag")
        assert atlas_rows[kind]["row_count"] == surface["summary"]["total_available"]


def test_kind_atlas_type_a_autonomous_seed_row_count_matches_option_surface_total() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    surface = build_option_surface(REPO_ROOT, "type_a_autonomous_seeds", band="flag")

    assert atlas_rows["type_a_autonomous_seeds"]["row_count"] == surface["summary"]["total_available"]


def test_option_surface_kinds_alias_uses_kind_atlas() -> None:
    payload = build_option_surface(REPO_ROOT, "kinds", band="flag")

    assert payload["kind"] == "kind_atlas"
    assert payload["summary"]["query_used"] is False
    assert "standards" in _rows_by_id(payload)


def test_raw_seed_alias_returns_helpful_route_card_instead_of_generic_gap() -> None:
    payload = build_option_surface(REPO_ROOT, "raw_seed", band="card")

    assert payload["profile_status"] == "profile_gap"
    assert payload["profile_gap_kind"] == "route_affordance_alias"
    assert payload["warnings"][0]["kind"] == "unsupported_alias_with_canonical_routes"
    assert payload["summary"]["selection_method"] == "route_affordance_alias_card"
    commands = [item["command"] for item in payload["next"]]
    assert "./repo-python kernel.py --option-surface skills --band card --ids raw_seed_navigation" in commands
    assert "./repo-python kernel.py --option-surface raw_seed_shards --band flag" in commands
    assert payload["route_card"]["status"] == "unsupported_by_design_helpful_route"
    assert "raw_seed" in payload["route_card"]["alias"]


def test_raw_seed_paper_alias_returns_mode_chooser_route_card() -> None:
    payload = build_option_surface(REPO_ROOT, "raw_seed_paper", band="card")

    assert payload["profile_status"] == "profile_gap"
    assert payload["profile_gap_kind"] == "route_affordance_alias"
    assert payload["warnings"][0]["kind"] == "unsupported_alias_with_canonical_routes"
    commands = [item["command"] for item in payload["next"]]
    assert "./repo-python kernel.py --option-surface paper_modules --band card --ids raw_seed_paper" in commands
    assert "./repo-python kernel.py --option-surface skills --band card --ids raw_seed_paper_authoring" in commands
    modes = {item["mode"] for item in payload["route_card"]["mode_cards"]}
    assert {
        "concept_lens_mode",
        "family_instance_mode",
        "coverage_ledger_mode",
        "work_conversion_mode",
        "propagation_mode",
    } <= modes


def test_raw_seed_alias_cli_exits_zero_for_route_affordance_card() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "raw_seed", "--band", "card"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["profile_gap_kind"] == "route_affordance_alias"
    assert payload["next"][0]["command"].endswith("--option-surface skills --band card --ids raw_seed_navigation")


def test_kind_atlas_kernel_command_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--kind-atlas", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kind_atlas"
    assert "paper_modules" in {row["kind_id"] for row in payload["rows"]}


def test_kind_atlas_kernel_command_accepts_legacy_query_with_guidance() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--kind-atlas", "git metadata sandbox", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kind_atlas"
    assert payload["selection"]["query"] == "git metadata sandbox"
    assert payload["summary"]["query_received"] is True
    assert payload["summary"]["query_used"] is False
    assert "not keyword search" in payload["summary"]["query_handling"]
    assert payload["next"][0]["command"] == (
        './repo-python kernel.py --context-pack "git metadata sandbox" --context-budget 12000'
    )


def test_kind_atlas_kernel_command_accepts_ids() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "kernel.py",
            "--kind-atlas",
            "--band",
            "flag",
            "--ids",
            "artifact_projection_debt",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kind_atlas"
    assert payload["selection"]["mode"] == "ids"
    assert payload["selection"]["ids"] == ["artifact_projection_debt"]
    assert payload["summary"]["row_count"] == 1
    assert [row["kind_id"] for row in payload["rows"]] == ["artifact_projection_debt"]


def test_option_surface_kinds_kernel_command_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "kernel.py", "--option-surface", "kinds", "--band", "flag"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kind_atlas"
    assert payload["profile_status"] == "supported"


def test_semantic_naming_remains_standard_row_not_root_kind() -> None:
    atlas_rows = _rows_by_id(build_kind_atlas(REPO_ROOT, band="flag"))
    assert "semantic_naming" not in atlas_rows
    assert "standards" in atlas_rows

    standards = build_option_surface(REPO_ROOT, "standards", band="card", ids=["std_semantic_naming"])
    assert standards["rows"][0]["standard_id"] == "std_semantic_naming"
