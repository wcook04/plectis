from __future__ import annotations

from system.lib.compression_profiles import (
    RAW_SEED_CONTEXT_PROFILE_ID,
    build_raw_seed_context_contract,
    compression_profile_pointer,
    get_compression_profile,
)


def test_raw_seed_compression_profile_declares_creator_and_navigator() -> None:
    profile = get_compression_profile(RAW_SEED_CONTEXT_PROFILE_ID)

    assert profile["profile_id"] == "raw_seed_voice_context_v1"
    assert profile["creator_skill_id"] == "compression.raw_seed_contextual_compression"
    assert profile["navigator_skill_id"] == "raw_seed_navigation"
    assert "drilldown_policy" in profile
    assert "dynamic_fact_policy" in profile
    assert profile["source_ladder"][0]["bracket"] == "raw_paragraph"
    assert profile["band_contracts"]["context"]["job"] == "working-set row for a worker or navigator"
    assert "paragraph_only" in profile["source_state_policy"]["allowed"]
    assert "context-space" in profile["context_space_policy"]["rule"]


def test_render_profile_pointer_exposes_owner_routes_and_projection_boundary() -> None:
    profile = get_compression_profile("type_b_external_grounding_v1")
    pointer = compression_profile_pointer(profile)

    assert pointer["profile_kind"] == "render_profile"
    assert pointer["artifact_role"] == "render_profile"
    assert pointer["context_profile_id"] == RAW_SEED_CONTEXT_PROFILE_ID
    assert pointer["output_path"] == "dist/type_b/TYPE_B_SYSTEM_GROUNDING_PACKET.md"
    assert pointer["status_sidecar_path"] == "state/system_atlas/type_b_grounding_packet_status.json"
    assert pointer["projection_not_authority"] is True
    assert pointer["refresh_owner"] == "type_a_or_always_on_metabolism"
    assert pointer["compression_passport"]["atom"] == "Type B grounding packet"
    assert "public_safe_projection" in pointer["compression_passport"]["cluster_keys"]
    assert "Type A verification" in pointer["compression_passport"]["when_not_to_open"]
    assert pointer["owner_routes"]["refresh_command"].endswith(
        "--render-profile type_b_external_grounding_v1"
    )
    assert pointer["owner_routes"]["check_command"].endswith(
        "--render-profile type_b_external_grounding_v1 --check"
    )
    assert pointer["owner_routes"]["root_drilldown_command"] == (
        "./repo-python kernel.py --paper-module system_self_comprehension_root"
    )


def test_raw_seed_context_contract_carries_drilldowns_dynamic_facts_and_omissions(tmp_path) -> None:
    contract = build_raw_seed_context_contract(
        repo_root=tmp_path,
        family="09",
        family_dir="obsidian/okay lets do this/09 - Demo",
        focus_cards=[
            {
                "id": "par_demo_001",
                "idea_group_ids": ["grp_demo"],
                "keywords": ["compression"],
            }
        ],
        context_rows=[
            {
                "paragraph_id": "par_demo_002",
                "relationship": ["shared_idea_group:grp_demo"],
                "emit_shards": False,
            }
        ],
        grouping_rows=[
            {
                "group_key": "idea_group:grp_demo",
                "focus_paragraph_ids": ["par_demo_001"],
                "not_a_route": True,
            }
        ],
        packet_kind="raw_seed_distillation_packet",
        selected_count=1,
        total_paragraph_count=2,
        total_atomized_parent_count=0,
        source_paths={"raw_seed_json_path": "demo/raw_seed.json"},
        observed_at="2026-04-23T00:00:00+00:00",
    )

    assert contract["profile_id"] == "raw_seed_voice_context_v1"
    assert contract["creator_skill_id"] == "compression.raw_seed_contextual_compression"
    assert contract["navigator_skill_id"] == "raw_seed_navigation"
    assert contract["source_state"] == "unknown"
    assert contract["band_reason"].startswith("context band")
    assert contract["compression_profile"]["band_contracts"]["flag"]["job"] == "route-card or existence signal"
    assert contract["compression_profile"]["worker_tier_policy"]["distiller"].startswith("produce atomized shards")
    assert contract["context_space_refs"]
    assert contract["context_horizon"]["authority_cards"][0]["path"] == "codex/doctrine/compression_profiles.json"
    assert contract["drilldown_refs"]
    assert contract["dynamic_fact_rows"][0]["observed_at"] == "2026-04-23T00:00:00+00:00"
    assert {"fact_id", "value", "observed_at", "probe_command", "source_path", "fingerprint"} <= set(
        contract["dynamic_fact_rows"][0]
    )
    assert contract["omission_receipt"]["omitted_context_count"] >= 1
