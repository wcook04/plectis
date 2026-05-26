"""Tests for the agent-entrypoint comprehension audit runtime and kernel route.

These tests intentionally build fixtures on `tmp_path` so the runtime can be
exercised without depending on the live CLAUDE.md / CODEX.md / AGENTS.md state.
They validate:

1. A fixture entrypoint missing the python/hologram axis produces a
   `missing_axis` error finding and marks the entrypoint `incomplete`.
2. A fixture entrypoint that mentions paper modules but not the derived-fact
   axis gets flagged for the specific missing axis (the real-repo drift Will
   warned about).
3. A `.claude/` / `.codex/` file declared in the dotfile inventory but not
   covered by any entrypoint or coverage paper module triggers
   `hidden_adapter_surface`.
4. The kernel route output shape matches the audit contract (same keys, same
   summary fields).
5. An axis satisfied via a kernel-command citation (not literal prose) is
   counted as covered — routes count equally with tokens.
6. Entrypoint prose that cites a non-existent doctrine file pattern such as
   `pri_*.json` is rejected and routed to the real authority surface.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Mapping

import pytest

from tools.meta.factory import build_agent_entrypoint_audit as entrypoint_audit_cli
from system.lib.agent_entrypoint_audit import (
    _expected_generated_regions,
    build_agent_entrypoint_audit,
    select_entrypoint,
    summarize_entrypoints,
)
from system.lib.agent_bootstrap_projection import (
    build_bootstrap_projection_context,
    render_live_markdown,
    render_type_a_convergence_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_agent_entrypoint_audit_cli_check_json_preserves_check_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_build_agent_entrypoint_audit(**_: object) -> dict:
        return {
            "audit": {
                "kind": "agent_entrypoint_audit",
                "summary": {"error_count": 1, "warning_count": 0},
            },
            "summary": {
                "kind": "agent_entrypoint_audit_summary",
                "summary": {"error_count": 1, "warning_count": 0},
            },
        }

    monkeypatch.setattr(entrypoint_audit_cli, "build_agent_entrypoint_audit", fake_build_agent_entrypoint_audit)

    rc = entrypoint_audit_cli.main(["--repo-root", str(tmp_path), "--check", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["kind"] == "agent_entrypoint_audit_summary"
    assert payload["summary"]["error_count"] == 1
    assert "entrypoints" not in payload


def _base_axis_registry() -> dict:
    return {
        "kind": "agent_entrypoint_axis_registry",
        "schema_version": "agent_entrypoint_axis_registry_v1",
        "axes": [
            {
                "id": "current_state",
                "title": "Current state",
                "why": "Pulse is the floor.",
                "severity_if_missing": "error",
                "resolution_methods": [
                    {"method": "kernel_command", "value": "kernel.py --pulse"},
                ],
            },
            {
                "id": "python_hologram_substrate",
                "title": "Python / hologram substrate",
                "why": "Must cite system/lib or hologram.",
                "severity_if_missing": "error",
                "resolution_methods": [
                    {"method": "paper_module_slug", "value": "system_lib_directory_index"},
                    {"method": "any_of_tokens", "values": ["codex/hologram/system", "system/lib/"]},
                ],
            },
            {
                "id": "derived_facts_anti_drift",
                "title": "Derived facts anti-drift",
                "why": "Must cite the fact hologram.",
                "severity_if_missing": "error",
                "resolution_methods": [
                    {"method": "kernel_command", "value": "kernel.py --facts"},
                    {"method": "kernel_command", "value": "kernel.py --fact-audit"},
                    {"method": "any_of_tokens", "values": ["std_derived_fact", "derived_fact_hologram"]},
                ],
            },
        ],
    }


def _seed_paper_module_index(root: Path, slugs: list[str]) -> None:
    modules = [
        {
            "slug": slug,
            "file": f"codex/doctrine/paper_modules/{slug}.md",
            "content_sha256": "0" * 64,
        }
        for slug in slugs
    ]
    _write_json(
        root / "codex/doctrine/paper_modules/_index.json",
        {"source_manifest": {"modules": modules}},
    )


def _seed_bootstrap(root: Path, actor_ids: list[str]) -> None:
    _write_json(
        root / "codex/doctrine/agent_bootstrap.json",
        {"actor_context_surfaces": [{"actor_id": actor} for actor in actor_ids]},
    )


def _seed_full_bootstrap(
    root: Path,
    *,
    claude_read_order: list[str] | None = None,
    codex_read_order: list[str] | None = None,
    extra: dict | None = None,
) -> None:
    payload = {
        "kind": "agent_bootstrap",
        "markers": {
            "begin": "<!-- BEGIN agent_bootstrap_live -->",
            "end": "<!-- END agent_bootstrap_live -->",
            "adapters": {
                "claude_md": {
                    "begin": "<!-- BEGIN claude_adapter_live -->",
                    "end": "<!-- END claude_adapter_live -->",
                },
                "codex_md": {
                    "begin": "<!-- BEGIN codex_adapter_live -->",
                    "end": "<!-- END codex_adapter_live -->",
                },
            },
        },
        "markdown_targets": {
            "agents_md": "AGENTS.md",
            "claude_md": "CLAUDE.md",
            "codex_md": "CODEX.md",
        },
        "adapter_actor_map": {
            "claude_md": "claude_code",
            "codex_md": "codex",
        },
        "actor_context_surfaces": [
            {
                "actor_id": "claude_code",
                "label": "Claude Code IDE agent",
                "read_order": claude_read_order or ["CLAUDE.md", "AGENTS.md"],
                "primary_commands": ["./repo-python kernel.py --info"],
            },
            {
                "actor_id": "codex",
                "label": "Codex IDE agent",
                "read_order": codex_read_order or ["CODEX.md", "AGENTS.md"],
                "primary_commands": ["./repo-python kernel.py --info"],
            },
        ],
    }
    if extra:
        payload.update(extra)
    _write_json(root / "codex/doctrine/agent_bootstrap.json", payload)


def _overlay_registry(required_axes: list[str]) -> dict:
    return {
        "kind": "agent_entrypoint_registry",
        "entrypoints": [
            {"id": "claude_code", "required_axes": required_axes, "companion_paths": []},
            {"id": "codex", "required_axes": required_axes, "companion_paths": []},
            {"id": "shared", "required_axes": required_axes, "companion_paths": []},
        ],
        "dotfile_tree_inventory": {},
    }


def test_missing_python_hologram_axis_is_hard_error(tmp_path: Path) -> None:
    # Adapter never mentions Python / hologram / system/lib.
    _write(
        tmp_path / "CLAUDE.md",
        "# Claude adapter\n\nRun `python3 kernel.py --pulse` before anything.\n"
        "Also run `python3 kernel.py --facts` for anti-drift.\n"
        "Read `std_derived_fact`.\n",
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        _base_axis_registry(),
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "kind": "agent_entrypoint_registry",
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": [
                        "current_state",
                        "python_hologram_substrate",
                        "derived_facts_anti_drift",
                    ],
                    "line_budget": 500,
                },
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])
    _seed_bootstrap(tmp_path, ["claude_code"])

    payload = build_agent_entrypoint_audit(repo_root=tmp_path)
    audit = payload["audit"]
    assert audit["summary"]["entrypoint_count"] == 1
    assert audit["summary"]["error_count"] >= 1
    findings = [item for item in audit["findings"] if item["rule"] == "missing_axis"]
    axis_ids = {item["axis_id"] for item in findings}
    assert "python_hologram_substrate" in axis_ids
    record = audit["entrypoints"][0]
    assert record["status"] == "incomplete"
    assert "python_hologram_substrate" in record["uncovered_axes"]
    # The facts axis IS covered in this fixture, so it must NOT be uncovered.
    assert "derived_facts_anti_drift" not in record["uncovered_axes"]


def test_paper_module_mention_without_facts_axis_is_flagged(tmp_path: Path) -> None:
    # Same shape as the real-repo drift: paper modules mentioned, facts axis missing.
    _write(
        tmp_path / "CLAUDE.md",
        "# Claude adapter\n\n"
        "Run `python3 kernel.py --pulse` for current state.\n"
        "Open `python3 kernel.py --paper-module <slug>` for subsystems.\n"
        "See `system_lib_directory_index` for python substrate.\n",
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        _base_axis_registry(),
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "kind": "agent_entrypoint_registry",
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": [
                        "current_state",
                        "python_hologram_substrate",
                        "derived_facts_anti_drift",
                    ],
                    "line_budget": 500,
                },
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])
    _seed_bootstrap(tmp_path, ["claude_code"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    findings = [item for item in audit["findings"] if item["rule"] == "missing_axis"]
    assert len(findings) == 1
    assert findings[0]["axis_id"] == "derived_facts_anti_drift"
    assert audit["summary"]["error_count"] == 1


def test_hidden_adapter_surface_detected(tmp_path: Path) -> None:
    # A .claude/ file exists on disk but no entrypoint or coverage file references it.
    _write(tmp_path / "CLAUDE.md", "run --pulse, read system_lib_directory_index, --facts\n")
    _write(tmp_path / ".claude/orphan_config.json", "{}")
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        _base_axis_registry(),
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "kind": "agent_entrypoint_registry",
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": ["current_state", "python_hologram_substrate", "derived_facts_anti_drift"],
                },
            ],
            "dotfile_tree_inventory": {
                "purpose": "test",
                ".claude/": [".claude/orphan_config.json"],
                "coverage_surfaces": ["codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md"],
            },
        },
    )
    _write(
        tmp_path / "codex/doctrine/paper_modules/host_agent_dotfile_surfaces.md",
        "# host agent dotfiles\n\nCovers settings.local.json but not the orphan.\n",
    )
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])
    _seed_bootstrap(tmp_path, ["claude_code"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    hidden_findings = [item for item in audit["findings"] if item["rule"] == "hidden_adapter_surface"]
    orphan_findings = [item for item in hidden_findings if item.get("path") == ".claude/orphan_config.json"]
    assert orphan_findings, "orphan dotfile should be flagged"
    assert orphan_findings[0]["severity"] == "error"


def test_axis_covered_by_kernel_command_not_literal_prose(tmp_path: Path) -> None:
    # The facts axis should be covered when --facts is cited, even if no literal 'derived_fact_hologram' prose exists.
    _write(
        tmp_path / "CLAUDE.md",
        "Run `python3 kernel.py --pulse`\n"
        "Run `python3 kernel.py --facts` when auditing volatile claims\n"
        "Read `system_lib_directory_index` for the python plane\n",
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        _base_axis_registry(),
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "kind": "agent_entrypoint_registry",
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": [
                        "current_state",
                        "python_hologram_substrate",
                        "derived_facts_anti_drift",
                    ],
                },
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])
    _seed_bootstrap(tmp_path, ["claude_code"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    assert audit["summary"]["error_count"] == 0
    record = audit["entrypoints"][0]
    assert record["status"] == "covered"
    assert not record["uncovered_axes"]


def test_output_contract_shape(tmp_path: Path) -> None:
    # Minimal fixture to snapshot the output shape.
    _write(tmp_path / "CLAUDE.md", "--pulse --facts system_lib_directory_index\n")
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        _base_axis_registry(),
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "kind": "agent_entrypoint_registry",
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": ["current_state", "python_hologram_substrate", "derived_facts_anti_drift"],
                },
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])
    _seed_bootstrap(tmp_path, ["claude_code"])

    payload = build_agent_entrypoint_audit(repo_root=tmp_path)
    audit = payload["audit"]
    summary = payload["summary"]
    per = payload["per_entrypoint"]

    assert audit["kind"] == "agent_entrypoint_audit"
    assert audit["schema_version"].startswith("agent_entrypoint_audit_")
    for field in ("summary", "entrypoints", "findings", "axes", "sources"):
        assert field in audit, f"audit missing field {field}"
    assert summary["kind"] == "agent_entrypoint_audit_summary"
    assert per["kind"] == "agent_entrypoint_audit_per_entrypoint"
    assert per["entrypoints"][0]["id"] == "claude_code"


def test_select_entrypoint_accepts_claude_alias(tmp_path: Path) -> None:
    audit = {
        "entrypoints": [
            {"id": "claude_code", "actor_id": "claude_code", "role": "adapter"},
            {"id": "shared", "actor_id": None, "role": "shared_hub"},
        ]
    }
    assert select_entrypoint(audit, "claude")["id"] == "claude_code"
    assert select_entrypoint(audit, "shared")["id"] == "shared"
    assert select_entrypoint(audit, "claude-code")["id"] == "claude_code"
    assert select_entrypoint(audit, "hub")["id"] == "shared"
    assert select_entrypoint(audit, "unknown") is None


def test_kernel_route_emits_audit_shape() -> None:
    # Real-repo smoke test: the route prints the declared shape.
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--agent-entrypoints"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.agent_entrypoints"
    assert "entrypoint_count" in payload["summary"]
    assert "entrypoints" in payload["payload"]
    for row in payload["payload"]["entrypoints"]:
        assert "axis_tiles" in row
        assert isinstance(row["axis_tiles"], list)


def test_kernel_route_rejects_unknown_entrypoint() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "repo-python"), "kernel.py", "--agent-entrypoint", "nonsense"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["kind"] == "kernel.navigate.agent_entrypoint"
    assert "error" in payload
    assert "alternatives" in payload
    assert any(row.get("id") == "claude_code" for row in payload["alternatives"])


def test_summarize_entrypoints_contract() -> None:
    audit = {
        "summary": {"entrypoint_count": 1},
        "entrypoints": [
            {
                "id": "claude_code",
                "role": "adapter",
                "actor_id": "claude_code",
                "label": "x",
                "status": "incomplete",
                "covered_axis_count": 1,
                "required_axis_count": 2,
                "uncovered_axes": ["derived_facts_anti_drift"],
                "axis_matrix": [
                    {"axis_id": "current_state", "covered": True, "matched_methods": ["kernel_command"]},
                    {"axis_id": "derived_facts_anti_drift", "covered": False, "matched_methods": []},
                ],
            }
        ],
    }
    summary = summarize_entrypoints(audit)
    assert summary["summary"]["entrypoint_count"] == 1
    assert summary["entrypoints"][0]["axis_tiles"][0]["axis_id"] == "current_state"
    assert summary["entrypoints"][0]["axis_tiles"][1]["covered"] is False


def test_adapter_read_scope_is_derived_from_agent_bootstrap(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "Claude adapter shell only.\n")
    _write(tmp_path / "AGENTS.md", "`python3 kernel.py --pulse` `python3 kernel.py --facts` system_lib_directory_index\n")
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", _base_axis_registry())
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        _overlay_registry(["current_state", "python_hologram_substrate", "derived_facts_anti_drift"]),
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    record = select_entrypoint(audit, "claude")
    assert record is not None
    assert record["primary_paths"] == ["CLAUDE.md"]
    assert record["read_scope_paths"] == ["CLAUDE.md", "AGENTS.md"]
    assert record["status"] == "covered"
    assert audit["summary"]["error_count"] == 0


def test_all_entrypoints_missing_axis_routes_to_shared_repair(tmp_path: Path) -> None:
    for path in ("CLAUDE.md", "CODEX.md", "AGENTS.md"):
        _write(tmp_path / path, "`python3 kernel.py --pulse` system_lib_directory_index\n")
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", _base_axis_registry())
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        _overlay_registry(["current_state", "python_hologram_substrate", "derived_facts_anti_drift"]),
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    findings = [
        item for item in audit["findings"]
        if item["rule"] == "missing_axis" and item["axis_id"] == "derived_facts_anti_drift"
    ]
    assert len(findings) == 3
    assert {item["fix_scope"] for item in findings} == {"shared"}
    assert {item["repair_kind"] for item in findings} == {"shared_projection_fix"}
    assert any(
        item["fix_scope"] == "shared"
        and item["repair_surface"] == "codex/doctrine/agent_bootstrap.json::type_a_convergence_contract.comprehension_gate"
        for item in audit["repair_plan"]["items"]
    )


def test_single_adapter_missing_axis_routes_to_adapter_repair(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "`python3 kernel.py --pulse` system_lib_directory_index\n")
    _write(tmp_path / "CODEX.md", "Codex shell.\n")
    _write(tmp_path / "AGENTS.md", "`python3 kernel.py --pulse` `python3 kernel.py --facts` system_lib_directory_index\n")
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", _base_axis_registry())
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        _overlay_registry(["current_state", "python_hologram_substrate", "derived_facts_anti_drift"]),
    )
    _seed_full_bootstrap(tmp_path, claude_read_order=["CLAUDE.md"], codex_read_order=["CODEX.md", "AGENTS.md"])
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    findings = [
        item for item in audit["findings"]
        if item["rule"] == "missing_axis" and item["axis_id"] == "derived_facts_anti_drift"
    ]
    assert len(findings) == 1
    assert findings[0]["entrypoint_id"] == "claude_code"
    assert findings[0]["fix_scope"] == "claude_only"
    assert findings[0]["repair_surface"] == "CLAUDE.md"


def test_ambient_only_axis_coverage_emits_weak_route(tmp_path: Path) -> None:
    _write(tmp_path / "CLAUDE.md", "`python3 kernel.py --pulse` derived_fact_hologram\n")
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json",
        {
            "axes": [
                {
                    "id": "derived_facts_anti_drift",
                    "title": "Derived facts",
                    "severity_if_missing": "error",
                    "resolution_methods": [
                        {"method": "kernel_command", "value": "kernel.py --facts"},
                        {"method": "any_of_tokens", "values": ["derived_fact_hologram"]},
                    ],
                }
            ]
        },
    )
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "entrypoints": [
                {"id": "claude_code", "role": "adapter", "actor_id": "claude_code", "primary_paths": ["CLAUDE.md"], "required_axes": ["derived_facts_anti_drift"]}
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_bootstrap(tmp_path, ["claude_code"])
    _seed_paper_module_index(tmp_path, [])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    weak = [item for item in audit["findings"] if item["rule"] == "weak_route"]
    assert audit["summary"]["error_count"] == 0
    assert len(weak) == 1
    assert weak[0]["repair_kind"] == "strengthen_route_citation"


def test_route_pointer_quality_accepts_standard_owner_and_freshness(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        "- `entry_control_packet`\n"
        "  - route `./repo-python kernel.py --entry \"<task>\" --context-budget 12000`; "
        "standard `codex/standards/std_agent_entry_surface.json`; "
        "freshness `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py`\n",
    )
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", {"axes": []})
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {"entrypoints": [{"id": "shared", "required_axes": []}], "dotfile_tree_inventory": {}},
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, [])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    shared = next(row for row in audit["entry_surface_topology"]["surfaces"] if row["surface_id"] == "agents_md")
    assert shared["owner_coverage"] == 1.0
    assert shared["freshness_coverage"] == 1.0
    assert not [item for item in audit["findings"] if item["rule"].startswith("route_pointer_missing")]


def test_route_pointer_quality_accepts_preceding_rosetta_owner(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        "Owner [navigation_seed.md](codex/doctrine/skills/kernel/navigation_seed.md); "
        "freshness `./repo-python tools/meta/factory/check_agent_bootstrap_projection.py`.\n"
        "Run `./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000` first.\n",
    )
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", {"axes": []})
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {"entrypoints": [{"id": "shared", "required_axes": []}], "dotfile_tree_inventory": {}},
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, [])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    shared = next(row for row in audit["entry_surface_topology"]["surfaces"] if row["surface_id"] == "agents_md")
    assert shared["owner_coverage"] == 1.0
    assert shared["freshness_coverage"] == 1.0
    assert not [item for item in audit["findings"] if item["rule"].startswith("route_pointer_missing")]


def test_generated_block_drift_compares_against_rendered_projection(tmp_path: Path) -> None:
    _write(
        tmp_path / "AGENTS.md",
        "before\n<!-- BEGIN agent_bootstrap_live -->\nstale body\n<!-- END agent_bootstrap_live -->\nafter\n",
    )
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", {"axes": []})
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {"entrypoints": [{"id": "shared", "required_axes": []}], "dotfile_tree_inventory": {}},
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, [])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    drift = [item for item in audit["findings"] if item["rule"] == "generated_block_drift"]
    assert drift
    assert drift[0]["repair_surface"] == "tools/meta/factory/build_agent_bootstrap_projection.py"


def test_generated_block_drift_uses_system_facts_projection_context(tmp_path: Path) -> None:
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", {"axes": []})
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {"entrypoints": [{"id": "shared", "required_axes": []}], "dotfile_tree_inventory": {}},
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, [])
    context = build_bootstrap_projection_context(tmp_path, refresh_orchestration=False)
    rendered = render_live_markdown(
        context["bindings"],
        per_agent_rows=context["per_agent_rows"],
        system_facts_at_a_glance=context["system_facts_at_a_glance"],
        minimum_read_sets=context["minimum_read_sets"] or None,
        bootstrap_sequence=context["bootstrap_sequence"] or None,
        situation_routes=context["situation_routes"] or None,
        actor_context_surfaces=context["actor_context_surfaces"] or None,
        runtime_control_plane=context["runtime_control_plane"] or None,
        compact_command_surface=context["compact_command_surface"] or None,
        type_a_convergence_contract=context["type_a_convergence_contract"] or None,
    )
    _write(
        tmp_path / "AGENTS.md",
        f"before\n<!-- BEGIN agent_bootstrap_live -->\n{rendered}<!-- END agent_bootstrap_live -->\nafter\n",
    )

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    drift = [item for item in audit["findings"] if item["rule"] == "generated_block_drift"]
    assert drift == []


def test_generated_block_drift_expected_regions_uses_non_refresh_projection_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from system.lib import agent_bootstrap_projection as projection

    seen_refresh_values: list[bool] = []

    def fake_load_config(_repo_root: Path) -> dict:
        return {
            "markers": {
                "begin": "<!-- BEGIN agent_bootstrap_live -->",
                "end": "<!-- END agent_bootstrap_live -->",
            },
            "markdown_targets": {"agents_md": "AGENTS.md"},
        }

    def fake_context(
        _repo_root: Path,
        *,
        config: Mapping[str, object],
        refresh_orchestration: bool = True,
    ) -> dict:
        seen_refresh_values.append(refresh_orchestration)
        return {
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
        }

    monkeypatch.setattr(projection, "load_agent_bootstrap_config", fake_load_config)
    monkeypatch.setattr(projection, "build_bootstrap_projection_context", fake_context)
    monkeypatch.setattr(projection, "render_live_markdown", lambda *args, **kwargs: "rendered")

    regions = _expected_generated_regions(tmp_path)

    assert seen_refresh_values == [False]
    assert regions[("AGENTS.md", "<!-- BEGIN agent_bootstrap_live -->", "<!-- END agent_bootstrap_live -->")] == "rendered"


def test_pri_json_pattern_is_flagged_as_incoherent_authority(tmp_path: Path) -> None:
    _write(
        tmp_path / "CLAUDE.md",
        "Never hand-edit `pri_*.json`; route doctrine through the apply lane.\n",
    )
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", {"axes": []})
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        {
            "entrypoints": [
                {
                    "id": "claude_code",
                    "role": "adapter",
                    "actor_id": "claude_code",
                    "primary_paths": ["CLAUDE.md"],
                    "required_axes": [],
                }
            ],
            "dotfile_tree_inventory": {},
        },
    )
    _seed_bootstrap(tmp_path, ["claude_code"])
    _seed_paper_module_index(tmp_path, [])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    findings = [item for item in audit["findings"] if item["rule"] == "incoherent_doctrine_file_pattern"]
    assert len(findings) == 1
    assert audit["summary"]["error_count"] == 1
    assert findings[0]["pattern"] == "pri_*.json"
    assert findings[0]["authority"] == "obsidian/**/raw_seed/raw_seed_principles.json::principles[]"
    assert findings[0]["repair_kind"] == "entrypoint_authority_pattern_fix"


def test_derived_facts_axis_passes_from_shared_projection_bucket(tmp_path: Path) -> None:
    gate = {
        "summary": "test gate",
        "required_evidence_buckets": [
            {
                "id": "derived_facts_anti_drift",
                "must_cite": "`python3 kernel.py --facts`, `python3 kernel.py --fact-audit`, and `python3 kernel.py --paper-module-facts <slug>`",
                "authority": "codex/standards/std_derived_fact.json",
            }
        ],
    }
    rendered = "\n".join(render_type_a_convergence_contract({"comprehension_gate": gate}))
    assert "--facts" in rendered
    assert "--fact-audit" in rendered
    assert "--paper-module-facts" in rendered

    _write(tmp_path / "CLAUDE.md", "Claude adapter shell only.\n")
    _write(tmp_path / "AGENTS.md", "`python3 kernel.py --pulse` system_lib_directory_index\n" + rendered)
    _write_json(tmp_path / "codex/doctrine/agent_entrypoints/axis_registry.json", _base_axis_registry())
    _write_json(
        tmp_path / "codex/doctrine/agent_entrypoints/entrypoint_registry.json",
        _overlay_registry(["current_state", "python_hologram_substrate", "derived_facts_anti_drift"]),
    )
    _seed_full_bootstrap(tmp_path)
    _seed_paper_module_index(tmp_path, ["system_lib_directory_index"])

    audit = build_agent_entrypoint_audit(repo_root=tmp_path)["audit"]
    claude = select_entrypoint(audit, "claude")
    assert claude is not None
    assert "derived_facts_anti_drift" not in claude["uncovered_axes"]
