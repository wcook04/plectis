"""Regression coverage for entrypoint budget and stale first-contact routes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from system.lib import agent_bootstrap_projection
from system.lib import entrypoint_health
from system.lib import routing_projection
from system.lib.entrypoint_health import build_entrypoint_health


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repo_entrypoint_health_is_budget_safe_and_route_clean() -> None:
    payload = build_entrypoint_health(REPO_ROOT)

    assert payload["kind"] == "entrypoint_health"
    assert payload["summary"]["contract_status"] == "valid"
    assert payload["summary"]["over_budget_count"] == 0
    assert payload["summary"]["generated_target_scan_status"] == "available"
    assert payload["summary"]["disallowed_stale_route_hit_count"] == 0
    generated_budget_rows = [
        row
        for row in payload["instruction_files"]
        if row["budget_status"] == "over_budget"
    ]
    assert all(row["load_posture"] == "generated_or_doctrine_skill" for row in generated_budget_rows)

    by_path = {row["path"]: row for row in payload["instruction_files"]}
    assert by_path["AGENTS.md"]["bytes"] <= by_path["AGENTS.md"]["budget"]
    assert by_path["AGENTS.override.md"]["bytes"] <= by_path["AGENTS.override.md"]["budget"]
    assert by_path["CLAUDE.md"]["bytes"] <= by_path["CLAUDE.md"]["budget"]
    assert by_path["CODEX.md"]["bytes"] <= by_path["CODEX.md"]["budget"]


def test_entrypoint_health_reports_over_budget_and_stale_routes(tmp_path: Path) -> None:
    (tmp_path / "codex/standards").mkdir(parents=True)
    (tmp_path / "codex/standards/std_agent_entry_surface.json").write_text(
        json.dumps(
            {
                "compression_budgets": {
                    "agents_md": {"path": "AGENTS.md", "budget_bytes": 64},
                    "agents_override_md": {"path": "AGENTS.override.md", "budget_bytes": 256},
                    "claude_md": {"path": "CLAUDE.md", "budget_bytes": 256},
                    "codex_md": {"path": "CODEX.md", "budget_bytes": 256},
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        '# Hub\nFirst move: `./repo-python kernel.py --skill-find "<task or intent>"`\n',
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.override.md").write_text(
        './repo-python kernel.py --context-pack "<task>" --context-budget 12000\n'
        './repo-python kernel.py --navigation-metabolism "<task>" --context-budget 12000\n',
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        './repo-python kernel.py --context-pack "<task>" --context-budget 12000\n'
        './repo-python kernel.py --navigation-metabolism "<task>" --context-budget 12000\n',
        encoding="utf-8",
    )
    (tmp_path / "CODEX.md").write_text(
        './repo-python kernel.py --context-pack "<task>" --context-budget 12000\n'
        './repo-python kernel.py --navigation-metabolism "<task>" --context-budget 12000\n',
        encoding="utf-8",
    )

    payload = build_entrypoint_health(tmp_path)

    assert payload["summary"]["contract_status"] == "entrypoint_debt"
    assert payload["summary"]["over_budget_count"] == 1
    assert payload["summary"]["disallowed_stale_route_hit_count"] >= 1
    assert any(hit["kind"] == "skill_find_free_text" for hit in payload["forbidden_first_contact_hits"])


def test_entrypoint_health_catches_do_not_forget_skill_find(tmp_path: Path) -> None:
    (tmp_path / "codex/standards").mkdir(parents=True)
    (tmp_path / "codex/standards/std_agent_entry_surface.json").write_text(
        json.dumps(
            {
                "compression_budgets": {
                    "agents_md": {"path": "AGENTS.md", "budget_bytes": 4096},
                    "agents_override_md": {"path": "AGENTS.override.md", "budget_bytes": 4096},
                    "claude_md": {"path": "CLAUDE.md", "budget_bytes": 4096},
                    "codex_md": {"path": "CODEX.md", "budget_bytes": 4096},
                }
            }
        ),
        encoding="utf-8",
    )
    safe_entry = (
        './repo-python kernel.py --context-pack "<task>" --context-budget 12000\n'
        './repo-python kernel.py --navigation-metabolism "<task>" --context-budget 12000\n'
    )
    (tmp_path / "AGENTS.override.md").write_text(safe_entry, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(safe_entry, encoding="utf-8")
    (tmp_path / "CODEX.md").write_text(safe_entry, encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        safe_entry + 'Do not forget to run `--skill-find "<query>"` first.\n',
        encoding="utf-8",
    )

    payload = build_entrypoint_health(tmp_path)

    assert payload["summary"]["contract_status"] == "entrypoint_debt"
    assert any(hit["kind"] == "skill_find_free_text" for hit in payload["forbidden_first_contact_hits"])


def test_entrypoint_health_can_skip_generated_targets_for_quick_callers(tmp_path: Path) -> None:
    (tmp_path / "codex/standards").mkdir(parents=True)
    (tmp_path / "codex/doctrine/skills/demo").mkdir(parents=True)
    (tmp_path / "codex/standards/std_agent_entry_surface.json").write_text(
        json.dumps({"compression_budgets": {}}),
        encoding="utf-8",
    )
    safe_entry = (
        './repo-python kernel.py --context-pack "<task>" --context-budget 12000\n'
        './repo-python kernel.py --navigation-metabolism "<task>" --context-budget 12000\n'
    )
    for rel in ("AGENTS.override.md", "AGENTS.md", "CLAUDE.md", "CODEX.md"):
        (tmp_path / rel).write_text(safe_entry, encoding="utf-8")
    (tmp_path / "codex/doctrine/skills/demo/generated.md").write_text(
        'First move: `./repo-python kernel.py --skill-find "<task or intent>"`\n',
        encoding="utf-8",
    )

    full = build_entrypoint_health(tmp_path)
    primary_only = build_entrypoint_health(tmp_path, include_generated_targets=False)

    assert full["summary"]["contract_status"] == "entrypoint_debt"
    assert full["summary"]["generated_target_scan_status"] == "available"
    assert primary_only["summary"]["contract_status"] == "valid"
    assert primary_only["summary"]["file_count"] == 4
    assert primary_only["summary"]["generated_target_scan_status"] == "deferred_by_caller"


def test_cached_entrypoint_health_reuses_command_node_cache(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = {"count": 0}

    def fake_build(_root, *, include_generated_targets=True):
        calls["count"] += 1
        return {
            "kind": "entrypoint_health",
            "schema_version": "entrypoint_health_v0",
            "summary": {
                "contract_status": "valid",
                "file_count": 4,
                "generated_target_scan_status": (
                    "available" if include_generated_targets else "deferred_by_caller"
                ),
            },
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
        }

    monkeypatch.setattr(entrypoint_health, "build_entrypoint_health", fake_build)

    first_payload, first_status = entrypoint_health.cached_entrypoint_health(tmp_path)
    second_payload, second_status = entrypoint_health.cached_entrypoint_health(tmp_path)

    assert first_payload["kind"] == "entrypoint_health"
    assert second_payload["summary"]["contract_status"] == "valid"
    assert first_status["status"] in {"miss_built", "stale_ok_hit"}
    assert second_status["status"] == "hit"
    assert calls["count"] == 1


def test_entrypoint_health_kernel_fast_dispatch_exposes_cache_receipt() -> None:
    proc = subprocess.run(
        [sys.executable, "kernel.py", "--entrypoint-health"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["kind"] == "entrypoint_health"
    assert payload["summary"]["contract_status"] == "valid"
    assert payload["command_node_cache"]["entrypoint_health"]["status"] in {
        "hit",
        "miss_built",
        "stale_ok_hit",
    }


def test_generated_region_content_sync_reports_renderer_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text(
        "<!-- BEGIN generated_routing -->\nstale\n<!-- END generated_routing -->\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_expected_managed_regions",
        lambda _root: (
            {
                (
                    "AGENTS.md",
                    "<!-- BEGIN generated_routing -->",
                    "<!-- END generated_routing -->",
                ): "fresh\n"
            },
            {"status": "available", "expected_region_count": 1},
        ),
    )

    findings, stats = entrypoint_health._check_generated_region_content_sync(
        tmp_path,
        ["AGENTS.md"],
    )

    assert stats["renderer_content_sync"] == "drift"
    assert stats["drift_region_count"] == 1
    assert findings[0]["rule"] == "generated_region_renderer_drift"


def test_expected_managed_regions_reuses_agent_operating_packet_for_instruction_discovery(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "AGENTS.override.md").write_text(
        "<!-- BEGIN instruction_discovery_live -->\nstale\n<!-- END instruction_discovery_live -->\n",
        encoding="utf-8",
    )
    cfg = {
        "markers": {
            "begin": "<!-- BEGIN agent_bootstrap_live -->",
            "end": "<!-- END agent_bootstrap_live -->",
            "adapters": {},
        },
        "markdown_targets": {"agents_md": "AGENTS.md"},
    }
    agent_packet = {"kind": "agent_operating_packet", "budget_metrics": {"entry_strip_bytes": 1}}
    context = {
        "bindings": {},
        "per_agent_rows": [],
        "system_facts_at_a_glance": {},
        "minimum_read_sets": [],
        "bootstrap_sequence": [],
        "situation_routes": [],
        "actor_context_surfaces": [],
        "runtime_control_plane": {},
        "compact_command_surface": {},
        "type_a_convergence_contract": {},
        "instruction_discovery": {
            "markdown_target": "AGENTS.override.md",
            "begin_marker": "<!-- BEGIN instruction_discovery_live -->",
            "end_marker": "<!-- END instruction_discovery_live -->",
        },
        "instruction_discovery_facts": {},
        "agent_operating_packet": agent_packet,
    }
    seen: dict[str, object] = {}

    def fake_stabilize(*args, agent_operating_packet=None, **kwargs):
        seen["agent_operating_packet"] = agent_operating_packet
        return {}, "expected instruction\n", "projected seed\n"

    monkeypatch.setattr(agent_bootstrap_projection, "load_agent_bootstrap_config", lambda _root: cfg)
    monkeypatch.setattr(
        agent_bootstrap_projection,
        "build_bootstrap_projection_context",
        lambda _root, config=None, refresh_orchestration=False: context,
    )
    monkeypatch.setattr(agent_bootstrap_projection, "render_live_markdown", lambda *args, **kwargs: "live\n")
    monkeypatch.setattr(agent_bootstrap_projection, "render_paper_module_index_markdown", lambda _root: "paper\n")
    monkeypatch.setattr(routing_projection, "build_routing_payload", lambda _root: {})
    monkeypatch.setattr(routing_projection, "render_routing_markdown", lambda _payload: "routing\n")
    monkeypatch.setattr(agent_bootstrap_projection, "stabilize_instruction_discovery_target", fake_stabilize)

    expected, status = entrypoint_health._expected_managed_regions(tmp_path)

    assert status["status"] == "available"
    assert seen["agent_operating_packet"] is agent_packet
    assert expected[
        (
            "AGENTS.override.md",
            "<!-- BEGIN instruction_discovery_live -->",
            "<!-- END instruction_discovery_live -->",
        )
    ] == "expected instruction\n"


def test_entry_surface_diagnostic_marks_dirty_routing_source_as_visible_debt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entrypoint_health,
        "build_entrypoint_health",
        lambda _root: {
            "summary": {
                "over_budget_count": 0,
                "disallowed_stale_route_hit_count": 0,
                "contract_status": "valid",
            },
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
            "first_contact_contract": {},
        },
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_markers",
        lambda _root, _paths: (
            [],
            {
                "marker_pairs_seen": 1,
                "marker_pairs_balanced_with_body": 1,
                "marker_pairs_empty_body": 0,
                "marker_pairs_unbalanced": 0,
            },
        ),
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_content_sync",
        lambda _root, _paths: (
            [],
            {
                "renderer_content_sync": "matched",
                "routing_source_coupling": {
                    "status": "artifact_matches_dirty_source_inputs",
                    "safe_to_commit_generated_outputs_without_sources": False,
                    "dirty_source_paths": ["codex/doctrine/skills/skill_registry.json"],
                },
            },
        ),
    )

    packet = entrypoint_health.project_entry_surface_diagnostics(
        tmp_path,
        "generated projection source coupling in entry surface",
    )

    row = packet["rows"][0]
    assert row["severity"] == "visible_debt"
    assert row["observed_state"]["generated_regions_match"] is True
    assert row["observed_state"]["generated_region_landing_safe"] is False
    assert "source inputs are dirty" in row["recommended_action"]


def test_entry_surface_diagnostic_distinguishes_clean_source_artifact_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entrypoint_health,
        "build_entrypoint_health",
        lambda _root: {
            "summary": {
                "over_budget_count": 0,
                "disallowed_stale_route_hit_count": 0,
                "contract_status": "valid",
            },
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
            "first_contact_contract": {},
        },
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_markers",
        lambda _root, _paths: (
            [],
            {
                "marker_pairs_seen": 1,
                "marker_pairs_balanced_with_body": 1,
                "marker_pairs_empty_body": 0,
                "marker_pairs_unbalanced": 0,
            },
        ),
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_content_sync",
        lambda _root, _paths: (
            [
                {
                    "rule": "generated_region_renderer_drift",
                    "path": "AGENTS.md",
                    "marker": "<!-- BEGIN generated_routing -->",
                    "severity": "visible_debt",
                }
            ],
            {
                "renderer_content_sync": "drift",
                "routing_source_coupling": {
                    "status": "artifact_drift_from_clean_sources",
                    "safe_to_commit_generated_outputs_without_sources": False,
                    "dirty_source_paths": [],
                },
            },
        ),
    )

    packet = entrypoint_health.project_entry_surface_diagnostics(
        tmp_path,
        "generated projection source coupling in entry surface",
    )

    row = packet["rows"][0]
    assert row["severity"] == "visible_debt"
    assert row["observed_state"]["generated_regions_match"] is False
    assert row["observed_state"]["generated_region_landing_safe"] is False
    assert "routing source inputs are clean" in row["recommended_action"]
    assert "source inputs are dirty" not in row["recommended_action"]


def test_entry_surface_diagnostic_structural_trigger_uses_fast_source_coupling_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entrypoint_health,
        "build_entrypoint_health",
        lambda _root: {
            "summary": {
                "over_budget_count": 0,
                "disallowed_stale_route_hit_count": 0,
                "contract_status": "valid",
            },
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
            "first_contact_contract": {},
        },
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_markers",
        lambda _root, _paths: (
            [],
            {
                "marker_pairs_seen": 1,
                "marker_pairs_balanced_with_body": 1,
                "marker_pairs_empty_body": 0,
                "marker_pairs_unbalanced": 0,
            },
        ),
    )

    def fail_full_renderer_check(_root: Path, _paths: list[str]) -> tuple[list[dict[str, object]], dict[str, object]]:
        raise AssertionError("structural-only diagnostics must not render full managed regions")

    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_content_sync",
        fail_full_renderer_check,
    )
    monkeypatch.setattr(
        routing_projection,
        "routing_status",
        lambda _root: {
            "source_coupling": {
                "status": "artifact_drift_from_clean_sources",
                "safe_to_commit_generated_outputs_without_sources": False,
                "dirty_source_paths": [],
            },
            "source_worktree_state": {
                "status": "available",
                "source_dirty": False,
                "dirty_source_paths": [],
            },
        },
    )

    packet = entrypoint_health.project_entry_surface_diagnostics(
        tmp_path,
        "",
        structural_triggers=[{"trigger_id": "selected_dissemination_projected_context_rows"}],
    )

    row = packet["rows"][0]
    observed = row["observed_state"]
    assert observed["content_sync_mode"] == "source_coupling_only"
    assert observed["renderer_content_sync"] == "deferred_structural_context"
    assert observed["renderer_content_sync_deferred"] is True
    assert observed["generated_regions_match"] is None
    assert observed["generated_regions_match_status"] == "deferred"
    assert observed["generated_region_landing_safe"] is None
    assert observed["generated_region_landing_safe_status"] == "deferred"
    assert observed["renderer_content_check"]["full_renderer_check_deferred"] is True
    assert "without a full renderer diff" in row["recommended_action"]


def test_entry_surface_diagnostic_first_contact_uses_fast_source_coupling_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        entrypoint_health,
        "build_entrypoint_health",
        lambda _root: {
            "summary": {
                "over_budget_count": 0,
                "disallowed_stale_route_hit_count": 0,
                "contract_status": "valid",
            },
            "instruction_files": [],
            "forbidden_first_contact_hits": [],
            "first_contact_contract": {},
        },
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_markers",
        lambda _root, _paths: (
            [],
            {
                "marker_pairs_seen": 1,
                "marker_pairs_balanced_with_body": 1,
                "marker_pairs_empty_body": 0,
                "marker_pairs_unbalanced": 0,
            },
        ),
    )

    def fail_full_renderer_check(_root: Path, _paths: list[str]) -> tuple[list[dict[str, object]], dict[str, object]]:
        raise AssertionError("broad first-contact diagnostics must not render full managed regions")

    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_content_sync",
        fail_full_renderer_check,
    )
    monkeypatch.setattr(
        entrypoint_health,
        "_check_generated_region_source_coupling_receipt",
        lambda _root: (
            [],
            {
                "renderer_content_sync": "deferred_structural_context",
                "status": "routing_source_coupling_only",
                "checked_region_count": 0,
                "matched_region_count": 0,
                "drift_region_count": 0,
                "missing_region_count": 0,
                "unbalanced_region_count": 0,
                "empty_region_count": 0,
                "full_renderer_check_deferred": True,
                "routing_source_coupling": {
                    "status": "clean_source_inputs_and_artifacts",
                    "safe_to_commit_generated_outputs_without_sources": True,
                    "dirty_source_paths": [],
                },
            },
        ),
    )

    packet = entrypoint_health.project_entry_surface_diagnostics(
        tmp_path,
        "first-contact command latency: speed up bootstrap commands",
    )

    row = packet["rows"][0]
    observed = row["observed_state"]
    assert observed["content_sync_mode"] == "source_coupling_only"
    assert observed["renderer_content_sync_deferred"] is True
    assert observed["full_content_sync_triggered_by"] == []
