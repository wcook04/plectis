"""Regression coverage for executable grammar metabolism v0."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from system.lib.artifact_projection_debt import build_artifact_projection_debt_row_jobs
from system.lib.generated_artifact_surface_summary import (
    KIND_ATLAS_SUMMARY_REL,
    check_generated_artifact_surface_summary,
    write_generated_artifact_surface_summary,
)
from system.lib.kind_atlas import build_kind_atlas
from system.lib.standard_option_surface import build_option_surface


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc if dt.tzinfo is None else dt.tzinfo).isoformat()


def test_zero_row_surface_creates_artifact_projection_debt_row(tmp_path: Path) -> None:
    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    row = rows["population:agent_observations:zero_rows"]
    assert row["debt_class"] == "population_debt"
    assert row["source_surface"] == "navigation_context_rosetta.population_honesty"
    assert row["failure_mode"] == "zero_row_surface"
    assert row["authority_ceiling"] == "candidate_authoring"


def test_standard_projection_gaps_compose_into_artifact_projection_debt(tmp_path: Path) -> None:
    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    compliance = rows["standard_projection_gap:compliance_ledger"]
    skill_map = rows["standard_projection_gap:standard_skill_map"]
    assert compliance["source_surface"] == "standard_projection_gaps"
    assert compliance["repair_class"] == "populate_missing_rows"
    assert "build_compliance_ledger.py" in compliance["safe_alternative"]
    assert skill_map["target_kind"] == "standard_skill_map"


def test_skill_compression_cluster_composes_into_artifact_projection_debt(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "codex/doctrine/skills/skill_registry.json",
        {
            "families": [
                {
                    "family_id": "kernel",
                    "skills": [
                        {
                            "id": "legacy_skill",
                            "title": "Legacy Skill",
                            "file": "codex/doctrine/skills/kernel/legacy_skill.md",
                            "description": "Legacy fallback only.",
                        }
                    ],
                }
            ]
        },
    )

    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    row = rows["skill_compression_debt:missing_compression_passport"]
    assert row["debt_class"] == "authoring_debt"
    assert row["repair_class"] == "repair_compression_contract"
    assert row["source_surface"] == "skill_compression_debt"
    assert row["expected_patch_shape"]["target_cluster_count"] == 1


def test_stale_active_claim_creates_transaction_debt_row(tmp_path: Path) -> None:
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / "state/metabolism/blackboard.json",
        {
            "generated_at": _iso(now),
            "active_agents": [
                {
                    "id": "claude:stale-claim",
                    "status": "active",
                    "agent_surface": "claude",
                    "session_id": "stale-claim",
                    "updated_at": _iso(now),
                    "last_heartbeat_at": _iso(now - timedelta(minutes=20)),
                    "claim_expires_at": _iso(now + timedelta(hours=3)),
                }
            ],
            "collisions": [],
        },
    )
    _write_json(
        tmp_path / "state/metabolism/metabolism_status.json",
        {
            "generated_at": _iso(now),
            "governor": {"effective_scheduler": {"blackboard_claim_ttl_seconds": 600}},
        },
    )

    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    row = rows["transaction:active_agent_claim:claude:stale-claim"]
    assert row["debt_class"] == "transaction_debt"
    assert row["source_surface"] == "metabolism.blackboard.active_agents"
    assert row["failure_mode"] == "stale_active_claim_treated_as_authority"
    assert row["repair_class"] == "claim_freshness_classification"
    assert row["expected_patch_shape"]["blackboard_mutation_authorized"] is False
    assert "last_heartbeat_at_older_than_live_ttl" in row["expected_patch_shape"]["stale_reasons"]


def test_fresh_current_temporal_claim_does_not_create_transaction_debt(tmp_path: Path) -> None:
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / "state/metabolism/blackboard.json",
        {
            "generated_at": _iso(now),
            "active_agents": [
                {
                    "id": "codex:fresh-claim",
                    "status": "active",
                    "agent_surface": "codex",
                    "session_id": "fresh-claim",
                    "updated_at": _iso(now),
                    "last_heartbeat_at": _iso(now),
                    "claim_expires_at": _iso(now + timedelta(minutes=10)),
                }
            ],
            "temporal_claims": [
                {
                    "claim_id": "tc_fresh",
                    "source_claim_id": "codex:fresh-claim",
                    "claim_type": "active_agent_claim",
                    "valid_at": _iso(now),
                    "invalid_at": None,
                    "expired_at": None,
                    "superseded_by": None,
                    "freshness_state": "current",
                }
            ],
            "collisions": [],
        },
    )

    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    assert "transaction:active_agent_claim:codex:fresh-claim" not in rows


def test_temporal_superseded_claim_still_in_active_agents_creates_transaction_debt(tmp_path: Path) -> None:
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / "state/metabolism/blackboard.json",
        {
            "generated_at": _iso(now),
            "active_agents": [
                {
                    "id": "codex:superseded-risk",
                    "status": "active",
                    "agent_surface": "codex",
                    "session_id": "superseded-risk",
                    "updated_at": _iso(now),
                    "last_heartbeat_at": _iso(now),
                    "claim_expires_at": _iso(now + timedelta(minutes=10)),
                }
            ],
            "temporal_claims": [
                {
                    "claim_id": "tc_old",
                    "source_claim_id": "codex:superseded-risk",
                    "claim_type": "active_agent_claim",
                    "valid_at": _iso(now - timedelta(minutes=5)),
                    "invalid_at": _iso(now),
                    "expired_at": None,
                    "superseded_by": "tc_new",
                    "freshness_state": "superseded",
                }
            ],
            "collisions": [],
        },
    )

    payload = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    row = rows["transaction:active_agent_claim:codex:superseded-risk"]
    assert row["source_surface"] == "metabolism.blackboard.temporal_claims"
    assert "temporal_claim_freshness=superseded" in row["expected_patch_shape"]["stale_reasons"]


def test_artifact_projection_debt_cluster_is_microcosm_safe() -> None:
    payload = build_option_surface(REPO_ROOT, "artifact_projection_debt", band="cluster_flag")

    assert payload["profile_status"] == "supported"
    assert payload["summary"]["query_used"] is False
    assert payload["summary"]["selection_method"] == "artifact_kind_cluster_overview"
    assert payload["summary"]["row_count"] < payload["summary"]["total_available"]
    assert payload["summary"]["row_count"] <= 12
    assert payload["navigation_boundary"]["cluster_first_for_high_cardinality"] is True
    assert all("omission_receipt" in row for row in payload["rows"])


def test_oversized_row_flag_route_appears_under_artifact_projection_debt() -> None:
    payload = build_option_surface(REPO_ROOT, "artifact_projection_debt", band="flag")

    rows = {row["row_id"]: row for row in payload["rows"]}
    row = rows["navigation_metabolism:projection:paper_modules.row_flag_all.library"]
    assert row["source_surface"] == "navigation_metabolism.quick_profile"
    assert row["debt_class"] == "projection_debt"
    assert row["active_debt"] is False
    assert row["advisory_only"] is True
    assert row["safe_alternative"].endswith("--option-surface paper_modules --band cluster_flag")


def test_system_microcosm_names_whole_runtime_ladder() -> None:
    payload = build_option_surface(REPO_ROOT, "system_microcosm", band="card")

    assert payload["profile_status"] == "supported"
    row = payload["rows"][0]
    assert row["row_id"] == "executable_grammar_metabolism_v0"
    assert row["compatibility_boundary"]["not_public_product_authority"] is True
    assert "std_microcosm.json" in " ".join(
        row["compatibility_boundary"]["current_public_microcosm_authority"]
    )
    assert set(row["layers"]) == {
        "grammar",
        "projection",
        "metabolism",
        "worker",
        "proof",
        "transaction",
    }
    assert "artifact_projection_debt --band cluster_flag" in row["drilldown_ladder"][1]
    assert "artifact-projection-debt" in row["drilldown_ladder"][3]
    assert row["compression_budget"]["raw_debt_rows_hidden_until_drilldown"] is True


def test_artifact_projection_debt_row_jobs_are_candidate_only() -> None:
    payload = build_artifact_projection_debt_row_jobs(REPO_ROOT, limit=5)

    assert payload["kind"] == "metabolism_row_jobs"
    assert payload["source"] == "artifact-projection-debt"
    assert payload["authority_ceiling"] == "candidate_authoring"
    assert 1 <= payload["summary"]["row_job_count"] <= 5
    for job in payload["row_jobs"]:
        assert job["authority_ceiling"] == "candidate_authoring"
        assert job["worker_surface"] == "type_a_or_provider_row_patch_only"
        assert job["operation"] in {
            "repair_projection_contract",
            "populate_missing_rows",
            "repair_compression_contract",
            "converge_parallel_lane",
            "repair_authoring_contract",
            "repair_route_lifecycle",
            "repair_transaction_claim_freshness",
        }
        shape = job["expected_patch_shape"]
        assert shape["patch_is_not_authorized_by_this_job"] is True
        assert shape["provider_output_targets"] == [
            "state/compute_workers/receipts/",
            "state/compute_workers/row_patches/",
        ]
        assert "direct_doctrine_authority_from_provider" in shape["forbidden_patch_targets"]


def test_generated_artifact_summary_materializes_artifact_projection_debt_count(tmp_path: Path) -> None:
    expected = build_option_surface(tmp_path, "artifact_projection_debt", band="flag")

    receipt = write_generated_artifact_surface_summary(tmp_path)
    assert receipt["ok"] is True
    assert (tmp_path / KIND_ATLAS_SUMMARY_REL).is_file()
    assert check_generated_artifact_surface_summary(tmp_path)["ok"] is True

    summary = json.loads((tmp_path / KIND_ATLAS_SUMMARY_REL).read_text(encoding="utf-8"))
    rows = {row["kind_id"]: row for row in summary["rows"]}
    artifact_row = rows["artifact_projection_debt"]
    assert artifact_row["row_count"] == expected["summary"]["row_count"]

    atlas = build_kind_atlas(tmp_path, band="flag", ids="artifact_projection_debt")
    selected = atlas["rows"][0]
    assert selected["row_count"] == artifact_row["row_count"]
    assert selected["currentness"]["status"] == "materialized_summary_available"
    assert selected["row_count_semantics"]["mode"] == "materialized"


def test_transaction_debt_row_job_is_candidate_only(tmp_path: Path) -> None:
    now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone.utc)
    _write_json(
        tmp_path / "state/metabolism/blackboard.json",
        {
            "generated_at": _iso(now),
            "active_agents": [
                {
                    "id": "codex:stale-claim",
                    "status": "active",
                    "agent_surface": "codex",
                    "session_id": "stale-claim",
                    "updated_at": _iso(now),
                    "last_heartbeat_at": _iso(now - timedelta(minutes=20)),
                    "claim_expires_at": _iso(now + timedelta(hours=3)),
                }
            ],
            "collisions": [],
        },
    )

    payload = build_artifact_projection_debt_row_jobs(tmp_path, limit=1)

    job = payload["row_jobs"][0]
    assert job["target_row_id"] == "transaction:active_agent_claim:codex:stale-claim"
    assert job["operation"] == "repair_transaction_claim_freshness"
    assert job["authority_ceiling"] == "candidate_authoring"
    assert job["expected_patch_shape"]["blackboard_mutation_authorized"] is False
