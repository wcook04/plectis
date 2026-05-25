from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core.runtime_shell import (
    PROOF_LAB_FIRST_SCREEN_COMMAND,
    PROOF_LAB_RECEIPT_REF,
    PROOF_LAB_ROUTE_REF,
    SOURCE_OPEN_BODY_POLICY,
    VERIFIER_EXECUTION_LENS_COMMAND,
    VERIFIER_EXECUTION_RECEIPT_REF,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "atlas", public_root / "atlas")
    shutil.copytree(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    shutil.copytree(MICROCOSM_ROOT / "skills", public_root / "skills")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    (public_root / "receipts/first_wave").mkdir(parents=True)
    return public_root


def _copy_runtime_root(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "examples", public_root / "examples")
    shutil.copytree(MICROCOSM_ROOT / "src", public_root / "src")
    shutil.copytree(
        MICROCOSM_ROOT / "receipts/first_wave",
        public_root / "receipts/first_wave",
    )
    shutil.copytree(
        MICROCOSM_ROOT / "receipts/preflight",
        public_root / "receipts/preflight",
    )
    return public_root


def _copy_workingness_root(tmp_path: Path) -> Path:
    public_root = _copy_runtime_root(tmp_path)
    shutil.copytree(MICROCOSM_ROOT / "standards", public_root / "standards")
    return public_root


def _make_scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "scratch"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_app.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_package_metadata_describes_runtime_spine() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    description = project["description"]

    assert "repo -> .microcosm" in description
    assert "inspectable work substrate" in description
    assert "first-slice" not in description
    assert project["readme"] == "README.md"
    assert project["license"] == {"file": "LICENSE"}
    assert project["authors"] == [{"name": "Microcosm Substrate Contributors"}]
    assert project["optional-dependencies"]["test"] == ["pytest>=8,<9"]
    assert "License :: OSI Approved :: Apache Software License" in project["classifiers"]
    assert payload["project"]["urls"]["Homepage"] == "https://github.com/wcook04/ai-workflow-proof"
    assert (MICROCOSM_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("Apache License")


def test_cli_help_routes_cold_readers_before_drilldown_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    first_line = output.splitlines()[0]
    assert first_line == "usage: microcosm [-h] <command> ..."
    assert "{init,index" not in first_line
    assert "First-screen route:" in output
    assert (
        "microcosm tour <project>        build .microcosm and inspect "
        "route/work/event/evidence/proof refs"
    ) in output
    assert "microcosm compile <project>     rebuild local .microcosm state" in output
    assert output.index("microcosm tour <project>") < output.index(
        "microcosm compile <project>"
    )
    assert (
        "microcosm status --card <project> read the compressed "
        "project/runtime status lens"
    ) in output
    assert "microcosm workingness           inspect behavior evidence and failure gaps" in output
    assert "microcosm serve <project>       open the local observatory" in output
    assert "microcosm proof-lab --out /tmp/microcosm-proof-lab" in output
    assert "no provider calls, source mutation, release," in output
    assert "Receipts are evidence drilldowns after the behavior route is visible." in output
    for command in [
        "compile",
        "python-lens",
        "explain",
        "status",
        "proof-lab",
        "spine",
        "tour",
        "authority",
        "serve",
        "evidence",
    ]:
        assert command in output
    for command in [
        "workingness",
        "prediction-lens",
        "market-boundary",
        "corpus-lens",
        "trace-lens",
        "repair-loop",
        "evidence-cells",
        "proof-loop-depth",
        "verifier-lab-execution-spine-lens",
        "landing-replay",
        "view-quality",
        "projection-safety",
        "drift-control",
        "spatial-simulation",
        "circuit-attribution",
        "route-cleanup",
        "projection-import-map",
        "import-projector",
        "option-surface-lens",
        "stripping-guard",
        "standards-control",
        "hook-coverage",
        "replay-gauntlet",
        "benchmark-lab",
        "legibility-scorecard",
        "intake",
        "reveal",
    ]:
        assert command in output
    for help_text in [
        "inspect proof loop depth without proving correctness",
        "show navigation route cleanup evidence",
        "show runtime projection intake board",
        "show public reveal walkthrough board",
    ]:
        assert help_text in output
    for drilldown_command in [
        "private-state-scan",
        "macro-projection-import-protocol",
        "verifier-lab-kernel",
        "agentic-vulnerability-discovery-patch-proof-replay",
    ]:
        assert drilldown_command not in output


def test_cli_status_card_can_overlay_project_route_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)

    assert cli.main(["status", "--card", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["card_command"] == "microcosm status --card <project>"
    assert payload["source_files_mutated"] is False
    assert payload["front_door"]["front_door_status_ref"] == (
        "microcosm status --card <project>::front_door_status"
    )
    front_door_status = payload["front_door_status"]
    assert front_door_status["status"] == "pass"
    assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["actionable_surface_ids"] == []
    assert front_door_status["surface_statuses"]["project_state"] == "pass"
    assert front_door_status["surface_statuses"]["route_explanation"] == "pass"
    assert (
        front_door_status["surface_statuses"]["workingness_failure_envelope"]
        == "clear"
    )
    assert (
        front_door_status["drilldown_blocked_surface_ids_ref"]
        == "microcosm tour <project>::front_door_status."
        "drilldown_blocked_surface_ids"
    )
    assert payload["front_door"]["project_state_status"] == "pass"
    assert payload["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert payload["front_door"]["route_explanation_command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    route_explanation = payload["front_door"]["route_explanation"]
    assert route_explanation["status"] == "pass"
    assert route_explanation["route_id"] == "readme_onboarding_route"
    assert route_explanation["selected_work_status"] == "closed"
    assert route_explanation["source_files_mutated"] is False
    assert route_explanation["event_ref_count"] >= 1
    assert route_explanation["evidence_ref_count"] >= 1
    assert route_explanation["reader_drilldowns"] == [
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/evidence/",
    ]
    assert "readme_onboarding_route" in payload["front_door"][
        "available_project_route_ids"
    ]
    assert payload["front_door"]["project_state"]["state_dir_exists"] is True
    body_floor = payload["front_door"]["source_open_body_import_floor"]
    assert body_floor["status"] == "pass"
    assert body_floor["summary_ref"] == (
        "microcosm status --card::macro_body_import_floor"
    )
    assert (
        body_floor["public_safe_body_material_count"]
        == payload["substrate_counts"][
            "copied_non_secret_macro_body_material_count"
        ]
    )
    assert body_floor["verified_source_module_family_count"] >= 20
    assert body_floor["body_text_exported_in_status"] is False
    assert body_floor["body_text_exported_in_receipts"] is False


def test_cli_tour_on_fresh_project_exposes_first_screen_microcosm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)
    project = _make_scratch_project(tmp_path)

    assert cli.main(["tour", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)
    first_screen = payload["first_screen"]
    front_door_status = payload["front_door_status"]

    assert payload["status"] == "pass"
    assert first_screen["schema_version"] == "microcosm_cold_reader_first_screen_v1"
    assert first_screen["intent"] == "bring_folder_run_local_path_inspect_state_then_drill_receipts"
    assert first_screen["selected_route_id"] == "readme_onboarding_route"
    assert first_screen["generated_state"]["state_dir"] == ".microcosm"
    expected_state_refs = {
        ".microcosm/project_manifest.json",
        ".microcosm/architecture.json",
        ".microcosm/state_index.json",
        ".microcosm/graph.json",
        ".microcosm/catalog.json",
        ".microcosm/python_lens.json",
        ".microcosm/patterns.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/explanations/",
        ".microcosm/evidence/",
    }
    assert set(first_screen["generated_state"]["refs"]) == expected_state_refs
    for ref in expected_state_refs:
        assert (project / ref).exists()
    assert first_screen["behavior_surfaces"] == {
        "route_state_ref": ".microcosm/routes.json",
        "work_state_ref": ".microcosm/work_items.json",
        "event_log_ref": ".microcosm/events.jsonl",
        "evidence_dir_ref": ".microcosm/evidence/",
        "graph_ref": ".microcosm/graph.json",
        "observatory_command": "microcosm serve <project> --host 127.0.0.1 --port 8765",
    }
    assert first_screen["route_explanation"]["command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert first_screen["route_explanation"]["endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert first_screen["proof_surface"]["status"] == "pass"
    assert first_screen["proof_surface"]["route_id"] == "formal_prover_context_strategy_gate"
    assert first_screen["safe_to_show"]["project_local_state_refs_visible"] is True
    assert first_screen["safe_to_show"]["credential_equivalent_payloads_exported"] is False
    assert first_screen["safe_to_show"]["receipt_refs_visible_after_behavior"] is True
    assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["drilldown_warning_surface_ids"] == [
        "authority",
        "intake",
    ]
    assert front_door_status["safe_to_show"]["blocking_surface_ids_visible"] is True
    step_ids = [row["step_id"] for row in first_screen["minimal_command_path"]]
    assert step_ids.index("inspect_first_screen") < step_ids.index(
        "drill_receipts_only_after_behavior"
    )

    assert cli.main(["status", "--card", str(project)]) == 0
    status_card = json.loads(capsys.readouterr().out)
    assert status_card["status"] == "pass"
    assert status_card["front_door_status"]["blocking_surface_ids"] == []
    assert status_card["front_door_status"]["actionable_surface_ids"] == [
        "workingness_failure_envelope"
    ]
    assert (
        status_card["front_door_status"]["surface_statuses"]["project_state"]
        == "pass"
    )
    assert status_card["front_door"]["project_state_status"] == "pass"
    assert status_card["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert status_card["front_door"]["state_dir_exists"] is True
    assert status_card["front_door"]["route_explanation"]["status"] == "pass"
    assert status_card["front_door"]["route_explanation"][
        "selected_work_status"
    ] == "closed"
    assert status_card["front_door"]["route_explanation"][
        "source_files_mutated"
    ] is False
    assert status_card["workingness"]["status"] == "actionable"
    assert status_card["proof_lab"]["status"] == "pass"
    assert status_card["macro_body_import_floor"]["source_body_imports"][
        "verified_source_module_family_count"
    ] >= 39
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_proof_lab_alias_prints_first_screen_card(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_dir = tmp_path / "proof-lab"
    status = cli.main(
        [
            "proof-lab",
            "--input",
            str(MICROCOSM_ROOT / "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"),
            "--out",
            str(out_dir),
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)
    receipt = out_dir / "exported_verifier_lab_kernel_bundle_validation_result.json"
    assert status == 0
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == f"microcosm proof-lab --out {out_dir}"
    public_input_ref = "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
    assert payload["expanded_command"] == (
        "microcosm verifier-lab-kernel run-kernel-bundle "
        f"--input {public_input_ref} --out {out_dir}"
    )
    assert payload["input_ref"] == public_input_ref
    assert payload["proof_lab_route_id"] == "formal_prover_context_strategy_gate"
    assert payload["proof_lab_route_component_count"] == 9
    assert payload["lean_lake_return_code"] == 0
    assert payload["lean_compiled_declaration_count"] == 8
    assert payload["safe_to_show"]["body_in_receipt"] is False
    assert payload["safe_to_show"]["proof_bodies_exported"] is False
    assert payload["safe_to_show"]["provider_payloads_exported"] is False
    assert receipt.is_file()
    assert payload["receipt_refs"] == [str(receipt)]
    assert payload["next_commands"] == [
        "microcosm status --card",
        "microcosm proof-loop-depth",
        f"microcosm evidence inspect {receipt}",
    ]
    assert "microcosm evidence list" not in payload["next_commands"]
    assert str(MICROCOSM_ROOT) not in output
    assert "/private/tmp" not in output


def test_cli_pattern_route_readiness_accepts_exported_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "pattern-route-readiness"
    status = cli.main(
        [
            "pattern-route-readiness",
            "validate-bundle",
            "--input",
            str(MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_route_readiness_bundle"),
            "--out",
            str(out_dir),
        ]
    )

    result = json.loads(
        (out_dir / "exported_route_readiness_bundle_validation_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert status == 0
    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_readiness_bundle"
    assert result["route_readiness_summary"]["status"] == "ok"
    assert result["selection_contract"]["selector_must_open"] == [
        "row_to_organ_router",
        "organ_route_cards",
        "organ_fixture_specs",
        "route_readiness_audit",
    ]
    assert result["authority_ceiling"]["public_leaf_authority"] is False


def test_cli_spine_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["spine"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_runtime_spine_v1"
    assert payload["status"] == "pass"
    assert payload["surface_counts"]["adapter_backed_organ_count"] == 42
    assert payload["surface_counts"]["product_path_demoted_organ_count"] == 4
    assert payload["first_run_path"][0]["command"] == "microcosm tour <project>"
    assert payload["first_run_path"][2]["command"] == "microcosm python-lens <project>"
    assert payload["first_run_path"][5]["command"] == "microcosm spine"
    assert payload["first_run_path"][6]["command"] == "microcosm authority"
    assert payload["first_run_path"][7]["command"] == "microcosm prediction-lens"
    assert payload["first_run_path"][8]["command"] == "microcosm market-boundary"
    assert payload["first_run_path"][9]["command"] == "microcosm corpus-lens"
    assert payload["first_run_path"][10]["command"] == "microcosm trace-lens"
    assert payload["first_run_path"][11]["command"] == "microcosm repair-loop"
    assert payload["first_run_path"][12]["command"] == "microcosm evidence-cells"
    assert payload["first_run_path"][13]["command"] == "microcosm proof-loop-depth"
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_run_path"][14]["command"] == PROOF_LAB_FIRST_SCREEN_COMMAND
    assert payload["first_run_path"][14]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["first_run_path"][14]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["first_run_path"][15]["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert payload["first_run_path"][15]["receipt_ref"] == VERIFIER_EXECUTION_RECEIPT_REF
    assert payload["first_run_path"][14]["route_component_count"] == 9
    assert payload["first_run_path"][16]["command"] == "microcosm landing-replay"
    assert payload["first_run_path"][17]["command"] == (
        "microcosm durable-agent-work-landing-replay run-work-landing-bundle"
    )
    assert payload["first_run_path"][18]["command"].startswith(
        "microcosm research-replication-rubric-artifact-replay"
    )
    assert payload["first_run_path"][19]["command"] == "microcosm view-quality"
    assert payload["first_run_path"][20]["command"] == "microcosm projection-safety"
    assert payload["first_run_path"][21]["command"] == "microcosm drift-control"
    assert payload["first_run_path"][22]["command"].startswith(
        "microcosm world-model-projection-drift-control-room"
    )
    assert payload["first_run_path"][23]["command"].startswith(
        "microcosm spatial-world-model-counterfactual-simulation-replay"
    )
    assert payload["first_run_path"][24]["command"].startswith(
        "microcosm mechanistic-interpretability-circuit-attribution-replay"
    )
    assert payload["first_run_path"][25]["command"] == "microcosm route-cleanup"
    assert payload["first_run_path"][26]["command"] == "microcosm projection-import-map"
    assert payload["first_run_path"][27]["command"] == "microcosm import-projector"
    assert payload["first_run_path"][28]["command"] == "microcosm option-surface-lens"
    assert payload["first_run_path"][29]["command"] == "microcosm stripping-guard"
    assert payload["first_run_path"][30]["command"] == "microcosm standards-control"
    assert payload["first_run_path"][31]["command"] == "microcosm hook-coverage"
    assert payload["first_run_path"][32]["command"] == "microcosm replay-gauntlet"
    assert payload["first_run_path"][33]["command"].startswith(
        "microcosm agent-memory-temporal-conflict-replay"
    )
    assert payload["first_run_path"][34]["command"].startswith(
        "microcosm sleeper-memory-poisoning-quarantine-replay"
    )
    assert payload["first_run_path"][35]["command"].startswith(
        "microcosm mcp-tool-authority-replay"
    )
    assert payload["first_run_path"][36]["command"].startswith(
        "microcosm proof-derived-governed-mutation-authorization"
    )
    assert payload["first_run_path"][37]["command"].startswith(
        "microcosm belief-state-process-reward-replay"
    )
    assert payload["first_run_path"][38]["command"].startswith(
        "microcosm agent-sandbox-policy-escape-replay"
    )
    assert payload["first_run_path"][39]["command"].startswith(
        "microcosm indirect-prompt-injection-information-flow-policy-replay"
    )
    assert payload["first_run_path"][40]["command"].startswith(
        "microcosm agentic-vulnerability-discovery-patch-proof-replay"
    )
    assert payload["first_run_path"][41]["command"].startswith(
        "microcosm certificate-kernel-execution-lab"
    )
    assert payload["first_run_path"][42]["command"] == "microcosm benchmark-lab"
    assert payload["first_run_path"][43]["command"] == "microcosm legibility-scorecard"
    assert payload["first_run_path"][46]["command"] == "microcosm cold-reader-route-map run-route-map-bundle"
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_authority_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_authority = (
        MICROCOSM_ROOT / "receipts/runtime_shell/public_authority_map.json"
    )
    source_reveal = (
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_reveal/public_reveal_view.json"
    )
    source_authority_before = source_authority.read_text(encoding="utf-8")
    source_reveal_before = source_reveal.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["authority"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_authority_map_v2"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm authority"
    assert payload["unsafe_payload_bodies_exported"] is False
    assert payload["payload_boundary"]["source_open_default"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["surface_counts"]["organ_authority_count"] == 42
    assert payload["surface_counts"]["surface_authority_count"] == 45
    assert payload["surface_counts"]["organ_evidence_class_count"] == 4
    assert payload["surface_counts"]["copied_non_secret_macro_body_count"] == 1
    assert payload["surface_counts"]["copied_non_secret_macro_body_material_count"] == 77
    assert payload["surface_counts"]["mixed_public_safe_macro_import_assay_status"] == "pass"
    assert payload["evidence_class_registry"]["fail_closed_no_default"] is True
    assert payload["evidence_class_counts"] == {
        "semantic_validator": 15,
        "algorithmic_projection": 23,
        "external_subprocess_witness": 3,
        "verified_macro_body_import": 1,
    }
    organ_authority_by_id = {row["organ_id"]: row for row in payload["organ_authority"]}
    assert (
        organ_authority_by_id["materials_chemistry_closed_loop_lab_safety_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agent_sandbox_policy_escape_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["formal_math_lean_proof_witness"]["evidence_class"]
        == "external_subprocess_witness"
    )
    assert (
        organ_authority_by_id["verifier_lab_kernel"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_diagnostic_evidence_spine"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["durable_agent_work_landing_replay"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_derived_governed_mutation_authorization"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["world_model_projection_drift_control_room"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["spatial_world_model_counterfactual_simulation_replay"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id[
            "mechanistic_interpretability_circuit_attribution_replay"
        ]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["research_replication_rubric_artifact_replay"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert any(row["surface_id"] == "project_python_lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/authority" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/tour" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/market-boundary" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/hook-coverage" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/replay-gauntlet" for row in payload["surface_authority"])
    assert any(
        row["surface_id"] == "public_verifier_lab_kernel_lens"
        and row["provider_hypothesis_proof_authority"] is False
        and row["route_id"] == "formal_prover_context_strategy_gate"
        and row["receipt_ref"] == PROOF_LAB_RECEIPT_REF
        and row["route_component_count"] == 9
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_lab_execution_spine_lens"
        and row["bounded_public_external_witness_only"] is True
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sabotage_scheming_monitor_replay_lens"
        and row["runtime_mode"] == "drilldown_only"
        and row["product_path_role"] == "drilldown_regression_not_runtime_spine"
        for row in payload["surface_authority"]
    )
    assert any(row["surface_id"] == "public_mcp_tool_authority_replay_lens" for row in payload["surface_authority"])
    assert any(
        row["surface_id"]
        == "public_proof_derived_governed_mutation_authorization_lens"
        for row in payload["surface_authority"]
    )
    assert source_authority.read_text(encoding="utf-8") == source_authority_before
    assert source_reveal.read_text(encoding="utf-8") == source_reveal_before
    assert any(
        row["surface_id"] == "public_belief_state_process_reward_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sandbox_policy_escape_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_indirect_prompt_injection_information_flow_policy_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/corpus" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/trace" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/repair-loop" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/evidence-cells" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/proof-loop-depth" for row in payload["surface_authority"])
    assert any(
        row["endpoint"] == "/verifier-lab-execution-spine"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/landing-replay" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/view-quality" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-safety" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/drift-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/spatial-simulation" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/circuit-attribution" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/route-cleanup" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-import-map" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/import-projector" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/option-surface-lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/stripping-guard" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/standards-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/benchmark-lab" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/legibility-scorecard" for row in payload["surface_authority"])


def test_cli_workingness_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["workingness"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_failure_map_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm workingness"
    assert payload["endpoint"] == "/workingness"
    assert payload["completeness_status"] == "complete_failure_modes"
    assert payload["surface_counts"]["mapped_organ_count"] == 46
    assert payload["surface_counts"]["missing_failure_modes_count"] == 0
    rows_by_id = {row["thing_id"]: row for row in payload["thing_failure_map"]}
    assert rows_by_id["verifier_lab_kernel"]["workingness_state"] == (
        "evidence_backed_runtime_spine"
    )
    assert rows_by_id["agent_monitor_redteam_falsification_replay"][
        "workingness_state"
    ] == "demoted_regression_drilldown"
    assert (public_root / payload["workingness_map_ref"]).is_file()


def test_cli_tour_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["tour"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm tour <project>"
    assert payload["endpoint"] == "/tour"
    assert payload["time_budget_minutes"] == 10
    assert payload["compile_summary"]["headline"] == "repo -> .microcosm"
    assert payload["snapshot_policy"]["test_runs_should_use_temp_public_root"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["first_screen"]["schema_version"] == (
        "microcosm_cold_reader_first_screen_v1"
    )
    assert payload["first_screen"]["primary_command"] == "microcosm tour <project>"
    assert payload["first_screen"]["minimal_command_path"][0]["command"] == (
        payload["first_screen"]["primary_command"]
    )
    assert payload["first_screen"]["selected_route_id"] == (
        payload["compile_summary"]["selected_route_id"]
    )
    assert payload["first_screen"]["route_explanation"]["command"] == (
        f"microcosm explain <project> {payload['first_screen']['selected_route_id']}"
    )
    assert payload["first_screen"]["generated_state"]["state_dir"] == ".microcosm"
    assert payload["first_screen"]["proof_surface"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen"]["behavior_surfaces"]["observatory_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert "microcosm status --card" in payload["command_path"]
    assert "microcosm workingness" in payload["command_path"]
    assert "/workingness" in payload["endpoint_path"]
    assert any(
        row["step_id"] == "inspect_status_and_workingness"
        for row in payload["first_screen"]["minimal_command_path"]
    )
    assert any(
        card["card_id"] == "status_and_workingness"
        and card["workingness_command"] == "microcosm workingness"
        for card in payload["route_cards"]
    )
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen_proof_lab"]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert any(
        card["card_id"] == "verifier_lab_kernel"
        and card["route_component_count"] == 9
        for card in payload["route_cards"]
    )
    assert (public_root / payload["tour_ref"]).is_file()
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_prediction_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["prediction-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_prediction_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm prediction-lens"
    assert payload["endpoint"] == "/prediction"
    assert payload["organ_id"] == "prediction_oracle_reconciliation"
    assert payload["mechanics"][2]["count"] == 2
    assert payload["authority_ceiling"]["financial_advice_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_prediction_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    assert "public_replacement_refs" not in payload


def test_cli_market_prediction_boundary_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["market-boundary"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_market_prediction_evidence_boundary_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm market-boundary"
    assert payload["endpoint"] == "/market-boundary"
    assert payload["boundary_summary"]["row_count"] == 8
    assert payload["boundary_summary"]["decision_boundary_count"] == 8
    assert payload["boundary_summary"]["trading_advice_authorized_count"] == 0
    assert payload["boundary_summary"]["private_portfolio_export_count"] == 0
    assert payload["authority_ceiling"]["synthetic_fixture_only"] is True
    assert payload["authority_ceiling"]["live_market_data_authorized"] is False
    assert payload["authority_ceiling"]["investment_recommendation_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_market_prediction_evidence_boundary_lens"
    )
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["boundary_rows"]
    )
    assert payload["safe_to_show"]["decision_policy_not_trading_advice"] is True
    assert "body_redacted" not in payload


def test_cli_corpus_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["corpus-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_corpus_readiness_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm corpus-lens"
    assert payload["endpoint"] == "/corpus"
    assert payload["organ_id"] == "corpus_readiness_mathlib_absence_gate"
    assert payload["corpus_summary"]["corpus_count"] == 7
    assert payload["corpus_summary"]["mathlib_lake_project_import_available"] is False
    assert payload["consumer_gate"]["allowed_case_ids"] == [
        "miniF2F_lean3_translation_smoke_allowed"
    ]
    assert payload["authority_ceiling"]["mathlib_dependent_proof_authority"] is False


def test_cli_trace_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["trace-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_verifier_trace_repair_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm trace-lens"
    assert payload["endpoint"] == "/trace"
    assert payload["repair_summary"]["attempt_count"] == 4
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_verifier_trace_repair_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "source-open public payload-boundary read-model" in payload["anti_claim"]
    assert "metadata-only public read-model" not in payload["anti_claim"]
    assert "body_redacted" not in payload


def test_cli_repair_loop_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["repair-loop"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_verifier_repair_loop_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm repair-loop"
    assert payload["endpoint"] == "/repair-loop"
    assert payload["repair_loop_summary"]["stage_count"] == 5
    assert payload["repair_loop_summary"]["transition_count"] == 4
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_verifier_repair_loop_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_evidence_cells_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["evidence-cells"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_formal_evidence_cell_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm evidence-cells"
    assert payload["endpoint"] == "/evidence-cells"
    assert payload["resolver_summary"]["cell_count"] == 4
    assert payload["resolver_summary"]["present_cell_count"] == 2
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["proof_bodies_exported"] is False
    assert payload["authority_ceiling"]["private_source_refs_exported"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_formal_evidence_cell_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_proof_loop_depth_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["proof-loop-depth"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_proof_loop_depth_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm proof-loop-depth"
    assert payload["endpoint"] == "/proof-loop-depth"
    assert payload["proof_loop_summary"]["gate_count"] == 12
    assert payload["proof_loop_summary"]["proof_lab_route_component_count"] == 9
    assert payload["proof_loop_summary"]["proof_lab_execution_transition_count"] == 6
    assert payload["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert payload["proof_loop_summary"]["proof_body_export_count"] == 0
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["authority_ceiling"]["benchmark_score_claim"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_proof_loop_depth_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_verifier_lab_execution_spine_lens_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(["verifier-lab-execution-spine-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_verifier_lab_execution_spine_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == VERIFIER_EXECUTION_LENS_COMMAND
    assert payload["endpoint"] == "/verifier-lab-execution-spine"
    assert payload["source_receipt_ref"] == VERIFIER_EXECUTION_RECEIPT_REF
    assert payload["execution_summary"]["transition_count"] == 6
    assert payload["execution_summary"]["accepted_transition_count"] == 4
    assert payload["execution_summary"]["cp2_downstream_effect_count"] == 1
    assert payload["execution_summary"]["evolve_accepted_count"] == 1
    assert payload["authority_ceiling"]["external_tool_witness_only"] is True
    assert payload["authority_ceiling"]["formal_proof_authority"] is False
    assert payload["payload_boundary"]["boundary_id"] == (
        "public_verifier_lab_execution_spine_lens"
    )
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_landing_replay_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["landing-replay"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_work_landing_replay_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm landing-replay"
    assert payload["endpoint"] == "/landing-replay"
    assert payload["replay_summary"]["lane_count"] == 4
    assert payload["replay_summary"]["validation_before_commit_attempt_required"] is True
    assert payload["authority_ceiling"]["live_git_mutation_authorized"] is False
    assert payload["authority_ceiling"]["broad_checkpoint_authorized"] is False


def test_cli_view_quality_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["view-quality"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_view_quality_action_map_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm view-quality"
    assert payload["endpoint"] == "/view-quality"
    assert payload["action_summary"]["action_row_count"] == 5
    assert payload["action_summary"]["hot_action_count"] == 4
    assert payload["authority_ceiling"]["private_screenshot_paths_exported"] is False
    assert payload["authority_ceiling"]["live_browser_control_authorized"] is False


def test_cli_projection_safety_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["projection-safety"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_projection_safety_audit_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm projection-safety"
    assert payload["endpoint"] == "/projection-safety"
    assert payload["projection_summary"]["omission_receipt_count"] == 42
    assert payload["projection_summary"]["private_body_export_count"] == 0
    assert payload["projection_summary"]["proof_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_mutation_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_projection_safety_audit_lens"
    assert payload["payload_boundary"]["source_open_default"] is True


def test_cli_projection_drift_control_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["drift-control"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_projection_drift_control_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm drift-control"
    assert payload["endpoint"] == "/drift-control"
    assert payload["drift_summary"]["row_count"] == 8
    assert payload["drift_summary"]["source_authority_claim_count"] == 0
    assert payload["drift_summary"]["live_repair_authorized_count"] == 0
    assert payload["drift_summary"]["public_drilldown_ref_count"] == 8
    assert payload["drift_summary"]["unsafe_payload_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert payload["authority_ceiling"]["live_route_repair_authorized"] is False
    assert payload["safe_to_show"]["repair_is_route_drilldown_only"] is True
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_projection_drift_control_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    encoded = json.dumps(payload, sort_keys=True)
    assert "public_replacement_ref" not in encoded


def test_cli_spatial_simulation_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["spatial-simulation"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (
        payload["schema_version"]
        == "microcosm_public_spatial_world_model_counterfactual_simulation_replay_lens_v1"
    )
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm spatial-simulation"
    assert payload["endpoint"] == "/spatial-simulation"
    assert payload["simulation_summary"]["replay_count"] == 6
    assert payload["simulation_summary"]["private_video_export_count"] == 0
    assert payload["simulation_summary"]["live_operation_authorized_count"] == 0
    assert payload["authority_ceiling"]["private_video_exported"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_spatial_world_model_counterfactual_simulation_replay_lens"
    )
    encoded = json.dumps(payload, sort_keys=True)
    assert "body_redacted" not in encoded
    assert "private_state_scan" not in encoded


def test_cli_route_cleanup_contract_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["route-cleanup"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_route_cleanup_contract_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm route-cleanup"
    assert payload["endpoint"] == "/route-cleanup"
    assert payload["cleanup_summary"]["row_count"] == 8
    assert payload["cleanup_summary"]["owner_route_count"] == 8
    assert payload["cleanup_summary"]["route_deletion_authorized_count"] == 0
    assert payload["cleanup_summary"]["generated_region_hand_edit_authorized_count"] == 0
    assert payload["cleanup_summary"]["public_drilldown_ref_count"] == 8
    assert payload["cleanup_summary"]["unsafe_payload_body_export_count"] == 0
    assert payload["authority_ceiling"]["source_open_drilldown_contract"] is True
    assert payload["authority_ceiling"]["route_deletion_authorized"] is False
    assert payload["safe_to_show"]["route_cleanup_is_source_open_drilldown_contract"] is True
    assert payload["source_open_body_policy"] == SOURCE_OPEN_BODY_POLICY
    assert payload["payload_boundary"]["boundary_id"] == "public_route_cleanup_contract_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload
    encoded = json.dumps(payload, sort_keys=True)
    assert "public_replacement_ref" not in encoded


def test_cli_projection_import_map_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["projection-import-map"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_projection_import_map_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm projection-import-map"
    assert payload["endpoint"] == "/projection-import-map"
    assert payload["map_summary"]["row_count"] == 6
    assert payload["map_summary"]["stage_count"] == 6
    assert payload["map_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["automated_import_guarantee"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_projection_import_map_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False


def test_cli_import_projector_contract_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["import-projector"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_import_projector_contract_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm import-projector"
    assert payload["endpoint"] == "/import-projector"
    assert payload["projector_summary"]["row_count"] == 9
    assert payload["projector_summary"]["stage_count"] == 6
    assert payload["projector_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["automated_import_execution_authorized"] is False
    assert payload["authority_ceiling"]["lossless_projection_claim"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_import_projector_contract_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False


def test_cli_option_surface_lens_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["option-surface-lens"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_compression_profile_option_surface_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm option-surface-lens"
    assert payload["endpoint"] == "/option-surface-lens"
    assert payload["option_surface_summary"]["row_count"] == 6
    assert payload["option_surface_summary"]["stage_count"] == 6
    assert payload["option_surface_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["profile_switch_execution_authorized"] is False
    assert payload["authority_ceiling"]["automatic_profile_selection_authorized"] is False
    assert payload["authority_ceiling"]["lossless_projection_claim"] is False
    assert (
        payload["payload_boundary"]["boundary_id"]
        == "public_compression_profile_option_surface_lens"
    )
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["option_rows"]
    )
    encoded = json.dumps(payload, sort_keys=True)
    assert "source_cell_redacted_flag" not in encoded
    assert "body_redacted" not in encoded
    assert "body_copied" not in encoded


def test_cli_stripping_guard_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["stripping-guard"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_private_stripping_guard_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm stripping-guard"
    assert payload["endpoint"] == "/stripping-guard"
    assert payload["guard_summary"]["guard_row_count"] == 8
    assert payload["guard_summary"]["private_body_export_count"] == 0
    assert payload["authority_ceiling"]["secret_detection_completeness_claim"] is False
    assert payload["authority_ceiling"]["financial_advice_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_stripping_guard_lens"
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["guard_rows"]
    )


def test_cli_standards_control_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["standards-control"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_standards_control_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm standards-control"
    assert payload["endpoint"] == "/standards-control"
    assert payload["standards_summary"]["standards_control_row_count"] == 8
    assert payload["standards_summary"]["negative_case_count"] == 8
    assert payload["standards_summary"]["private_body_export_count"] == 0
    assert payload["standards_summary"]["source_authority_claim_count"] == 0
    assert payload["authority_ceiling"]["standards_registry_source_authority"] is False
    assert payload["authority_ceiling"]["standards_completeness_claim"] is False
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_standards_control_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["standards_rows"]
    )


def test_cli_hook_coverage_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["hook-coverage"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_hook_intervention_coverage_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm hook-coverage"
    assert payload["endpoint"] == "/hook-coverage"
    assert payload["coverage_summary"]["intervention_row_count"] == 5
    assert payload["coverage_summary"]["missing_authority_count"] == 1
    assert payload["coverage_summary"]["hook_shadow_case_count"] == 6
    assert payload["coverage_summary"]["hook_shadow_repair_class_count"] == 6
    assert payload["coverage_summary"]["live_state_read_denial_count"] == 1
    assert payload["authority_ceiling"]["live_operator_state_read"] is False
    assert payload["authority_ceiling"]["provider_payload_read"] is False
    assert payload["authority_ceiling"]["live_task_ledger_mutation_authorized"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_hook_intervention_coverage_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert all(
        row["unsafe_payload_bodies_exported"] is False
        for row in payload["intervention_rows"]
    )


def test_cli_replay_gauntlet_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["replay-gauntlet"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_agent_reliability_replay_gauntlet_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm replay-gauntlet"
    assert payload["endpoint"] == "/replay-gauntlet"
    assert payload["coverage_summary"]["episode_count"] == 11
    assert payload["coverage_summary"]["blocked_episode_count"] == 9
    assert payload["authority_ceiling"]["live_agent_execution_authorized"] is False
    assert payload["authority_ceiling"]["complete_security_claim"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_agent_reliability_replay_gauntlet_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_benchmark_lab_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["benchmark-lab"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_repository_benchmark_transaction_lab_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm benchmark-lab"
    assert payload["endpoint"] == "/benchmark-lab"
    assert payload["scorecard"]["task_count"] == 2
    assert payload["scorecard"]["oracle_patch_count"] == 2
    assert payload["scorecard"]["fail_to_pass_count"] == 2
    assert payload["scorecard"]["pass_to_pass_count"] == 2
    assert payload["authority_ceiling"]["live_repo_mutation_authorized"] is False
    assert payload["authority_ceiling"]["swe_bench_performance_claim"] is False
    assert payload["payload_boundary"]["boundary_id"] == "public_repository_benchmark_transaction_lab_lens"
    assert payload["unsafe_payload_bodies_in_receipt"] is False
    assert "body_redacted" not in payload


def test_cli_legibility_scorecard_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["legibility-scorecard"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_cold_reader_legibility_scorecard_lens_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm legibility-scorecard"
    assert payload["endpoint"] == "/legibility-scorecard"
    assert payload["scorecard"]["checkpoint_count"] == 6
    assert payload["scorecard"]["reader_question_count"] == 5
    assert payload["scorecard"]["time_budget_minutes"] == 10
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["authority_ceiling"]["reader_success_guarantee"] is False


def test_cli_intake_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["intake"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_runtime_reveal_import_bridge_v1"
    assert payload["bridge_id"] == "runtime_reveal_import_bridge"
    assert payload["projection_cell_count"] == 31
    by_cell = {row["cell_id"]: row for row in payload["cell_status"]}
    assert by_cell["agent_observability_store_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["projection_protocol_self_host"]["projection_status"] == (
        "self_hosted_status_protocol_landed"
    )
    assert by_cell["runtime_reveal_import_bridge"]["projection_status"] == (
        "runtime_bridge_landed"
    )
    assert by_cell["finance_eval_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_landing_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["task_ledger_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert by_cell["work_ledger_control_source_modules_import"]["projection_status"] == (
        "public_runtime_import_landed"
    )
    assert payload["open_actionable_cell_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_macro_projection_plan_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(
        [
            "macro-projection-import-protocol",
            "plan",
            "--input",
            (
                MICROCOSM_ROOT
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
            ).as_posix(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert payload["projection_intake_board"]["ready_cell_count"] == 31
    assert payload["projection_intake_board"]["blocked_cell_count"] == 0
    assert payload["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert payload["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_formal_math_readiness_plan_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(
        [
            "formal-math-readiness-gate",
            "plan",
            "--input",
            (MICROCOSM_ROOT / "fixtures/first_wave/formal_math_readiness_gate/input").as_posix(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "formal_math_readiness_extension_preview_v1"
    assert payload["projection_cell_id"] == "formal_math_readiness_extensions"
    assert payload["readiness_extension_board"]["premise_index_projection"][
        "premise_count"
    ] == 11
    assert payload["readiness_extension_board"]["tactic_portfolio_projection"][
        "available_tactic_count"
    ] == 6
    assert payload["authority_ceiling"]["lean_lake_execution_authorized"] is False


def test_cli_public_entry_docs_smoke_uses_temp_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    monkeypatch.chdir(public_root)
    out = Path("receipts/first_wave/public_entry_docs_validation.json")

    status = cli.main(
        [
            "public-entry-docs",
            "--root",
            ".",
            "--out",
            out.as_posix(),
        ]
    )

    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert status == 0
    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["payload_boundary"]["source_open_default"] is True
    assert receipt["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    text = out.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
