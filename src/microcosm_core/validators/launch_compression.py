from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core import project_substrate
from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic
from microcosm_core.runtime_shell import RuntimeShell


CHECKER_ID = "checker.microcosm.validators.launch_compression"


def _public_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _first_lines(path: Path, count: int) -> str:
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[:count])


def _without_fenced_code_blocks(text: str) -> str:
    kept: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return "\n".join(kept)


def _private_hits(text: str) -> list[str]:
    return [
        needle
        for needle in [
            "/Users/",
            "src/ai_workflow",
            "Library/Application Support/Google/" + "Chrome",
            "sk" + "-",
        ]
        if needle in text
    ]


def _walk_state_files(project: Path) -> list[Path]:
    state = project / project_substrate.STATE_DIR
    if not state.is_dir():
        return []
    return [path for path in sorted(state.rglob("*")) if path.is_file()]


def validate_launch_compression(
    root: str | Path,
    project: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    project_path = Path(project).expanduser().resolve(strict=False)
    output_file = Path(out_path)
    readme_path = public_root / "README.md"
    pyproject_path = public_root / "pyproject.toml"
    readme_first_screen = _first_lines(readme_path, 35)
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.is_file() else ""

    compiled = project_substrate.compile_project(project_path)
    shell = RuntimeShell(public_root)
    tour = shell.tour(project_path, persist_receipt=False)
    market_boundary = shell.market_boundary()
    trace_lens = shell.trace_lens()
    repair_loop = shell.repair_loop()
    evidence_cells = shell.evidence_cells()
    proof_loop_depth = shell.proof_loop_depth()
    landing_replay = shell.landing_replay()
    view_quality = shell.view_quality()
    projection_safety = shell.projection_safety()
    projection_drift = shell.projection_drift()
    route_cleanup = shell.route_cleanup()
    projection_import_map = shell.projection_import_map()
    import_projector = shell.import_projector()
    option_surface = shell.option_surface_lens()
    stripping_guard = shell.stripping_guard()
    standards_control = shell.standards_control()
    hook_coverage = shell.hook_coverage()
    replay_gauntlet = shell.replay_gauntlet()
    benchmark_lab = shell.benchmark_lab()
    legibility_scorecard = shell.legibility_scorecard()
    observatory_html = shell._observatory_html(project_path)
    state_files = _walk_state_files(project_path)
    state_text = "\n".join(path.read_text(encoding="utf-8") for path in state_files if path.suffix in {".json", ".jsonl"})
    first_screen_lower = readme_first_screen.lower()
    launch_intro_lower = _without_fenced_code_blocks(readme_first_screen).lower()
    receipt_forward_needles = ["receipt", "adapter", "truth index", "organ registry", "reconstruction"]

    assertions = {
        "one_line_identity_present": "repo -> .microcosm" in readme_first_screen
        and "inspectable work substrate" in readme_first_screen,
        "one_command_quickstart_present": "microcosm compile ." in readme_first_screen,
        "try_it_on_your_repo_present": "try it on your repo" in first_screen_lower,
        "first_screen_not_receipt_forward": not any(
            needle in launch_intro_lower for needle in receipt_forward_needles
        ),
        "pyproject_description_compressed": "repo" in pyproject_text
        and ".microcosm" in pyproject_text,
        "compile_command_passes": compiled.get("status") == PASS,
        "compile_headline_compressed": compiled.get("headline") == "repo -> .microcosm",
        "compile_creates_local_state": (project_path / project_substrate.STATE_DIR).is_dir(),
        "compile_detects_patterns": int(compiled.get("passing_pattern_count") or 0) > 0,
        "compile_opens_routes": int(compiled.get("route_count") or 0) > 0,
        "compile_runs_work_transaction": bool(compiled.get("work_id")),
        "compile_emits_events": int(compiled.get("event_count") or 0) > 0,
        "compile_emits_evidence": int(compiled.get("evidence_count") or 0) > 0,
        "compile_does_not_mutate_source": compiled.get("source_files_mutated") is False,
        "ten_minute_tour_passes": tour.get("status") == PASS,
        "ten_minute_tour_endpoint_visible": "/tour" in (tour.get("endpoint_path") or []),
        "ten_minute_tour_command_present": "microcosm tour <project>" in (tour.get("command_path") or []),
        "verifier_trace_lens_passes": trace_lens.get("status") == PASS,
        "verifier_trace_endpoint_visible": "/trace" in (tour.get("endpoint_path") or []),
        "verifier_trace_command_present": "microcosm trace-lens" in (tour.get("command_path") or []),
        "verifier_trace_no_proof_authority": isinstance(trace_lens.get("authority_ceiling"), dict)
        and trace_lens["authority_ceiling"].get("formal_proof_authority") is False
        and trace_lens["authority_ceiling"].get("proof_bodies_exported") is False,
        "verifier_trace_first_screen_present": "Verifier Trace Repair Lens" in observatory_html,
        "verifier_repair_loop_lens_passes": repair_loop.get("status") == PASS,
        "verifier_repair_loop_endpoint_visible": "/repair-loop" in (tour.get("endpoint_path") or []),
        "verifier_repair_loop_command_present": "microcosm repair-loop" in (tour.get("command_path") or []),
        "verifier_repair_loop_no_proof_authority": isinstance(
            repair_loop.get("authority_ceiling"), dict
        )
        and repair_loop["authority_ceiling"].get("formal_proof_authority") is False
        and repair_loop["authority_ceiling"].get("proof_bodies_exported") is False
        and repair_loop["authority_ceiling"].get("oracle_needed_premise_ids_exported") is False,
        "verifier_repair_loop_first_screen_present": "Verifier Repair Loop Lens" in observatory_html,
        "formal_evidence_cell_lens_passes": evidence_cells.get("status") == PASS,
        "formal_evidence_cell_endpoint_visible": "/evidence-cells" in (tour.get("endpoint_path") or []),
        "formal_evidence_cell_command_present": "microcosm evidence-cells" in (tour.get("command_path") or []),
        "formal_evidence_cell_no_proof_authority": isinstance(
            evidence_cells.get("authority_ceiling"), dict
        )
        and evidence_cells["authority_ceiling"].get("formal_proof_authority") is False
        and evidence_cells["authority_ceiling"].get("proof_bodies_exported") is False
        and evidence_cells["authority_ceiling"].get("private_source_refs_exported") is False,
        "formal_evidence_cell_first_screen_present": "Formal Evidence Cell Lens" in observatory_html,
        "proof_loop_depth_lens_passes": proof_loop_depth.get("status") == PASS,
        "proof_loop_depth_endpoint_visible": "/proof-loop-depth" in (tour.get("endpoint_path") or []),
        "proof_loop_depth_command_present": "microcosm proof-loop-depth" in (tour.get("command_path") or []),
        "proof_loop_depth_no_proof_or_benchmark_authority": isinstance(
            proof_loop_depth.get("authority_ceiling"), dict
        )
        and proof_loop_depth["authority_ceiling"].get("formal_proof_authority") is False
        and proof_loop_depth["authority_ceiling"].get("proof_bodies_exported") is False
        and proof_loop_depth["authority_ceiling"].get("oracle_needed_premise_ids_exported") is False
        and proof_loop_depth["authority_ceiling"].get("benchmark_score_claim") is False
        and proof_loop_depth["authority_ceiling"].get("general_theorem_solution_claim") is False,
        "proof_loop_depth_first_screen_present": "Proof Loop Depth Lens" in observatory_html,
        "work_landing_replay_lens_passes": landing_replay.get("status") == PASS,
        "work_landing_replay_endpoint_visible": "/landing-replay" in (tour.get("endpoint_path") or []),
        "work_landing_replay_command_present": "microcosm landing-replay" in (tour.get("command_path") or []),
        "work_landing_replay_no_git_authority": isinstance(
            landing_replay.get("authority_ceiling"), dict
        )
        and landing_replay["authority_ceiling"].get("live_git_mutation_authorized") is False
        and landing_replay["authority_ceiling"].get("broad_checkpoint_authorized") is False
        and landing_replay["authority_ceiling"].get("source_mutation_authorized") is False,
        "work_landing_replay_first_screen_present": "Work Landing Replay Lens" in observatory_html,
        "view_quality_action_map_lens_passes": view_quality.get("status") == PASS,
        "view_quality_action_map_endpoint_visible": "/view-quality" in (tour.get("endpoint_path") or []),
        "view_quality_action_map_command_present": "microcosm view-quality" in (tour.get("command_path") or []),
        "view_quality_action_map_no_private_ui_authority": isinstance(
            view_quality.get("authority_ceiling"), dict
        )
        and view_quality["authority_ceiling"].get("private_screenshot_paths_exported") is False
        and view_quality["authority_ceiling"].get("live_browser_control_authorized") is False
        and view_quality["authority_ceiling"].get("complete_frontend_quality_claim") is False,
        "view_quality_action_map_first_screen_present": "View Quality Action Map Lens" in observatory_html,
        "projection_safety_audit_lens_passes": projection_safety.get("status") == PASS,
        "projection_safety_audit_endpoint_visible": "/projection-safety" in (tour.get("endpoint_path") or []),
        "projection_safety_audit_command_present": "microcosm projection-safety" in (tour.get("command_path") or []),
        "projection_safety_audit_no_private_exports": isinstance(
            projection_safety.get("projection_summary"), dict
        )
        and projection_safety["projection_summary"].get("private_body_export_count") == 0
        and projection_safety["projection_summary"].get("proof_body_export_count") == 0
        and projection_safety["projection_summary"].get("provider_payload_export_count") == 0,
        "projection_safety_audit_first_screen_present": "Projection Safety Audit Lens" in observatory_html,
        "market_prediction_boundary_lens_passes": market_boundary.get("status") == PASS,
        "market_prediction_boundary_endpoint_visible": "/market-boundary"
        in (tour.get("endpoint_path") or []),
        "market_prediction_boundary_command_present": "microcosm market-boundary"
        in (tour.get("command_path") or []),
        "market_prediction_boundary_no_private_exports_or_advice": isinstance(
            market_boundary.get("authority_ceiling"), dict
        )
        and market_boundary["authority_ceiling"].get("live_market_data_authorized") is False
        and market_boundary["authority_ceiling"].get("trading_advice_authorized") is False
        and market_boundary["authority_ceiling"].get("investment_recommendation_authorized")
        is False
        and market_boundary["authority_ceiling"].get("private_portfolio_exported") is False
        and market_boundary["authority_ceiling"].get("performance_guarantee_claim") is False,
        "market_prediction_boundary_rows_validated": isinstance(
            market_boundary.get("boundary_summary"), dict
        )
        and market_boundary["boundary_summary"].get("row_count") == 8
        and market_boundary["boundary_summary"].get("source_ref_count") == 8
        and market_boundary["boundary_summary"].get("decision_boundary_count") == 8
        and market_boundary["boundary_summary"].get("negative_case_count") == 8
        and market_boundary["boundary_summary"].get("private_portfolio_export_count") == 0
        and market_boundary["boundary_summary"].get("trading_advice_authorized_count") == 0,
        "market_prediction_boundary_first_screen_present": "Market Prediction Boundary Lens"
        in observatory_html,
        "projection_drift_control_lens_passes": projection_drift.get("status") == PASS,
        "projection_drift_control_endpoint_visible": "/drift-control"
        in (tour.get("endpoint_path") or []),
        "projection_drift_control_command_present": "microcosm drift-control"
        in (tour.get("command_path") or []),
        "projection_drift_control_no_live_or_source_authority": isinstance(
            projection_drift.get("authority_ceiling"), dict
        )
        and projection_drift["authority_ceiling"].get("source_authority_claim") is False
        and projection_drift["authority_ceiling"].get("live_route_repair_authorized") is False
        and projection_drift["authority_ceiling"].get("source_mutation_authorized") is False
        and projection_drift["authority_ceiling"].get("automatic_doctrine_promotion_authorized")
        is False,
        "projection_drift_control_rows_validated": isinstance(
            projection_drift.get("drift_summary"), dict
        )
        and projection_drift["drift_summary"].get("row_count") == 8
        and projection_drift["drift_summary"].get("source_ref_count") == 8
        and projection_drift["drift_summary"].get("repair_route_count") == 8
        and projection_drift["drift_summary"].get("validation_ref_count") == 8,
        "projection_drift_control_first_screen_present": "Projection Drift Control Lens"
        in observatory_html,
        "route_cleanup_contract_lens_passes": route_cleanup.get("status") == PASS,
        "route_cleanup_contract_endpoint_visible": "/route-cleanup"
        in (tour.get("endpoint_path") or []),
        "route_cleanup_contract_command_present": "microcosm route-cleanup"
        in (tour.get("command_path") or []),
        "route_cleanup_contract_no_route_or_source_mutation": isinstance(
            route_cleanup.get("authority_ceiling"), dict
        )
        and route_cleanup["authority_ceiling"].get("route_deletion_authorized") is False
        and route_cleanup["authority_ceiling"].get("source_mutation_authorized") is False
        and route_cleanup["authority_ceiling"].get("generated_region_hand_edit_authorized")
        is False
        and route_cleanup["authority_ceiling"].get("release_authorized") is False,
        "route_cleanup_contract_rows_validated": isinstance(
            route_cleanup.get("cleanup_summary"), dict
        )
        and route_cleanup["cleanup_summary"].get("row_count") == 8
        and route_cleanup["cleanup_summary"].get("source_ref_count") == 8
        and route_cleanup["cleanup_summary"].get("owner_route_count") == 8
        and route_cleanup["cleanup_summary"].get("validation_ref_count") == 8
        and route_cleanup["cleanup_summary"].get("route_deletion_authorized_count") == 0
        and route_cleanup["cleanup_summary"].get("generated_region_hand_edit_authorized_count")
        == 0,
        "route_cleanup_contract_first_screen_present": "Route Cleanup Contract Lens"
        in observatory_html,
        "projection_import_map_lens_passes": projection_import_map.get("status") == PASS,
        "projection_import_map_endpoint_visible": "/projection-import-map"
        in (tour.get("endpoint_path") or []),
        "projection_import_map_command_present": "microcosm projection-import-map"
        in (tour.get("command_path") or []),
        "projection_import_map_no_private_exports_or_auto_import": isinstance(
            projection_import_map.get("authority_ceiling"), dict
        )
        and projection_import_map["authority_ceiling"].get("private_body_export_authorized")
        is False
        and projection_import_map["authority_ceiling"].get("proof_body_export_authorized")
        is False
        and projection_import_map["authority_ceiling"].get("provider_payload_export_authorized")
        is False
        and projection_import_map["authority_ceiling"].get("automated_import_guarantee")
        is False,
        "projection_import_map_first_screen_present": "Projection Import Map Lens"
        in observatory_html,
        "import_projector_contract_lens_passes": import_projector.get("status") == PASS,
        "import_projector_contract_endpoint_visible": "/import-projector"
        in (tour.get("endpoint_path") or []),
        "import_projector_contract_command_present": "microcosm import-projector"
        in (tour.get("command_path") or []),
        "import_projector_contract_no_private_exports_or_execution": isinstance(
            import_projector.get("authority_ceiling"), dict
        )
        and import_projector["authority_ceiling"].get("private_body_export_authorized")
        is False
        and import_projector["authority_ceiling"].get("proof_body_export_authorized")
        is False
        and import_projector["authority_ceiling"].get("provider_payload_export_authorized")
        is False
        and import_projector["authority_ceiling"].get("generated_region_hand_edit_authorized")
        is False
        and import_projector["authority_ceiling"].get("automated_import_execution_authorized")
        is False
        and import_projector["authority_ceiling"].get("lossless_projection_claim") is False,
        "import_projector_contract_rows_validated": isinstance(
            import_projector.get("projector_summary"), dict
        )
        and import_projector["projector_summary"].get("row_count") == 9
        and import_projector["projector_summary"].get("stage_count") == 6
        and import_projector["projector_summary"].get("validation_ref_count") == 9
        and import_projector["projector_summary"].get("authority_ceiling_row_count") == 9
        and import_projector["projector_summary"].get("private_body_export_count") == 0
        and import_projector["projector_summary"].get("generated_region_hand_edit_authorized_count")
        == 0,
        "import_projector_contract_first_screen_present": "Import Projector Contract Lens"
        in observatory_html,
        "compression_profile_option_surface_lens_passes": option_surface.get("status") == PASS,
        "compression_profile_option_surface_endpoint_visible": "/option-surface-lens"
        in (tour.get("endpoint_path") or []),
        "compression_profile_option_surface_command_present": "microcosm option-surface-lens"
        in (tour.get("command_path") or []),
        "compression_profile_option_surface_no_private_exports_or_execution": isinstance(
            option_surface.get("authority_ceiling"), dict
        )
        and option_surface["authority_ceiling"].get("private_body_export_authorized") is False
        and option_surface["authority_ceiling"].get("provider_payload_export_authorized")
        is False
        and option_surface["authority_ceiling"].get("profile_switch_execution_authorized")
        is False
        and option_surface["authority_ceiling"].get("automatic_profile_selection_authorized")
        is False
        and option_surface["authority_ceiling"].get("lossless_projection_claim") is False,
        "compression_profile_option_surface_rows_validated": isinstance(
            option_surface.get("option_surface_summary"), dict
        )
        and option_surface["option_surface_summary"].get("row_count") == 6
        and option_surface["option_surface_summary"].get("stage_count") == 6
        and option_surface["option_surface_summary"].get("validation_ref_count") == 6
        and option_surface["option_surface_summary"].get("authority_ceiling_row_count")
        == 6
        and option_surface["option_surface_summary"].get("private_body_export_count") == 0
        and option_surface["option_surface_summary"].get(
            "profile_switch_execution_authorized_count"
        )
        == 0,
        "compression_profile_option_surface_first_screen_present": (
            "Compression Profile Option Surface Lens" in observatory_html
        ),
        "stripping_guard_lens_passes": stripping_guard.get("status") == PASS,
        "stripping_guard_endpoint_visible": "/stripping-guard"
        in (tour.get("endpoint_path") or []),
        "stripping_guard_command_present": "microcosm stripping-guard"
        in (tour.get("command_path") or []),
        "stripping_guard_no_private_exports_or_release": isinstance(
            stripping_guard.get("guard_summary"), dict
        )
        and stripping_guard["guard_summary"].get("private_body_export_count") == 0
        and stripping_guard["guard_summary"].get("proof_body_export_count") == 0
        and stripping_guard["guard_summary"].get("provider_payload_export_count") == 0
        and stripping_guard["guard_summary"].get("raw_private_path_export_count") == 0
        and stripping_guard["guard_summary"].get("secret_token_export_count") == 0
        and stripping_guard["guard_summary"].get("release_authorized") is False,
        "stripping_guard_denies_secret_completeness": isinstance(
            stripping_guard.get("authority_ceiling"), dict
        )
        and stripping_guard["authority_ceiling"].get("secret_detection_completeness_claim")
        is False
        and stripping_guard["authority_ceiling"].get("financial_advice_authorized") is False,
        "stripping_guard_first_screen_present": "Public/Private Stripping Guard Lens"
        in observatory_html,
        "standards_control_lens_passes": standards_control.get("status") == PASS,
        "standards_control_endpoint_visible": "/standards-control"
        in (tour.get("endpoint_path") or []),
        "standards_control_command_present": "microcosm standards-control"
        in (tour.get("command_path") or []),
        "standards_control_no_source_or_release_authority": isinstance(
            standards_control.get("authority_ceiling"), dict
        )
        and standards_control["authority_ceiling"].get("standards_registry_source_authority")
        is False
        and standards_control["authority_ceiling"].get("standards_completeness_claim")
        is False
        and standards_control["authority_ceiling"].get("provider_calls_authorized") is False
        and standards_control["authority_ceiling"].get("source_mutation_authorized") is False
        and standards_control["authority_ceiling"].get("release_authorized") is False,
        "standards_control_no_private_exports": isinstance(
            standards_control.get("standards_summary"), dict
        )
        and standards_control["standards_summary"].get("private_body_export_count") == 0
        and standards_control["standards_summary"].get("proof_body_export_count") == 0
        and standards_control["standards_summary"].get("provider_payload_export_count") == 0
        and standards_control["standards_summary"].get("source_authority_claim_count") == 0,
        "standards_control_first_screen_present": "Standards Control Lens"
        in observatory_html,
        "hook_intervention_coverage_lens_passes": hook_coverage.get("status") == PASS,
        "hook_intervention_coverage_endpoint_visible": "/hook-coverage" in (tour.get("endpoint_path") or []),
        "hook_intervention_coverage_command_present": "microcosm hook-coverage" in (tour.get("command_path") or []),
        "hook_intervention_coverage_no_live_authority": isinstance(
            hook_coverage.get("authority_ceiling"), dict
        )
        and hook_coverage["authority_ceiling"].get("live_operator_state_read") is False
        and hook_coverage["authority_ceiling"].get("provider_payload_read") is False
        and hook_coverage["authority_ceiling"].get("live_task_ledger_mutation_authorized") is False,
        "hook_intervention_coverage_first_screen_present": "Hook Intervention Coverage Lens" in observatory_html,
        "agent_reliability_replay_gauntlet_lens_passes": replay_gauntlet.get("status") == PASS,
        "agent_reliability_replay_gauntlet_endpoint_visible": "/replay-gauntlet"
        in (tour.get("endpoint_path") or []),
        "agent_reliability_replay_gauntlet_command_present": "microcosm replay-gauntlet"
        in (tour.get("command_path") or []),
        "agent_reliability_replay_gauntlet_no_live_authority": isinstance(
            replay_gauntlet.get("authority_ceiling"), dict
        )
        and replay_gauntlet["authority_ceiling"].get("live_agent_execution_authorized") is False
        and replay_gauntlet["authority_ceiling"].get("live_tool_calls_authorized") is False
        and replay_gauntlet["authority_ceiling"].get("real_secret_material_exported") is False
        and replay_gauntlet["authority_ceiling"].get("complete_security_claim") is False,
        "agent_reliability_replay_gauntlet_first_screen_present": "Agent Reliability Replay Gauntlet"
        in observatory_html,
        "repository_benchmark_transaction_lab_lens_passes": benchmark_lab.get("status") == PASS,
        "repository_benchmark_transaction_lab_endpoint_visible": "/benchmark-lab"
        in (tour.get("endpoint_path") or []),
        "repository_benchmark_transaction_lab_command_present": "microcosm benchmark-lab"
        in (tour.get("command_path") or []),
        "repository_benchmark_transaction_lab_no_live_authority": isinstance(
            benchmark_lab.get("authority_ceiling"), dict
        )
        and benchmark_lab["authority_ceiling"].get("live_repo_mutation_authorized") is False
        and benchmark_lab["authority_ceiling"].get("provider_call_authorized") is False
        and benchmark_lab["authority_ceiling"].get("swe_bench_performance_claim") is False
        and benchmark_lab["authority_ceiling"].get("production_delivery_rate_claim") is False,
        "repository_benchmark_transaction_lab_first_screen_present": (
            "Repository Benchmark Transaction Lab" in observatory_html
        ),
        "cold_reader_legibility_scorecard_lens_passes": legibility_scorecard.get("status")
        == PASS,
        "cold_reader_legibility_scorecard_endpoint_visible": "/legibility-scorecard"
        in (tour.get("endpoint_path") or []),
        "cold_reader_legibility_scorecard_command_present": (
            "microcosm legibility-scorecard" in (tour.get("command_path") or [])
        ),
        "cold_reader_legibility_scorecard_no_release_or_reader_guarantee": isinstance(
            legibility_scorecard.get("authority_ceiling"), dict
        )
        and legibility_scorecard["authority_ceiling"].get("release_authorized") is False
        and legibility_scorecard["authority_ceiling"].get("reader_success_guarantee") is False
        and legibility_scorecard["authority_ceiling"].get("private_data_equivalence_claim")
        is False,
        "cold_reader_legibility_scorecard_first_screen_present": (
            "Cold Reader Legibility Scorecard" in observatory_html
        ),
        "ten_minute_tour_first_screen_present": "Ten-Minute Tour" in observatory_html,
        "observatory_shows_causal_chain": "Causal Chain" in observatory_html
        and str(compiled.get("selected_route_id") or "") in observatory_html,
        "evidence_marked_drilldown": "Evidence is drilldown" in observatory_html,
        "release_ceiling_visible": "Release remains unauthorized" in observatory_html,
        "private_paths_absent": not (
            _private_hits(readme_first_screen)
            or _private_hits(json.dumps(compiled, sort_keys=True))
            or _private_hits(json.dumps(tour, sort_keys=True))
            or _private_hits(json.dumps(trace_lens, sort_keys=True))
            or _private_hits(json.dumps(repair_loop, sort_keys=True))
            or _private_hits(json.dumps(evidence_cells, sort_keys=True))
            or _private_hits(json.dumps(proof_loop_depth, sort_keys=True))
            or _private_hits(json.dumps(landing_replay, sort_keys=True))
            or _private_hits(json.dumps(view_quality, sort_keys=True))
            or _private_hits(json.dumps(projection_safety, sort_keys=True))
            or _private_hits(json.dumps(projection_drift, sort_keys=True))
            or _private_hits(json.dumps(route_cleanup, sort_keys=True))
            or _private_hits(json.dumps(projection_import_map, sort_keys=True))
            or _private_hits(json.dumps(import_projector, sort_keys=True))
            or _private_hits(json.dumps(option_surface, sort_keys=True))
            or _private_hits(json.dumps(stripping_guard, sort_keys=True))
            or _private_hits(json.dumps(standards_control, sort_keys=True))
            or _private_hits(json.dumps(hook_coverage, sort_keys=True))
            or _private_hits(json.dumps(replay_gauntlet, sort_keys=True))
            or _private_hits(json.dumps(benchmark_lab, sort_keys=True))
            or _private_hits(json.dumps(legibility_scorecard, sort_keys=True))
            or _private_hits(observatory_html)
            or _private_hits(state_text)
        ),
    }
    blocking_codes = [
        f"LAUNCH_COMPRESSION_{key.upper()}_FAILED"
        for key, ok in assertions.items()
        if not ok
    ]

    scan_inputs = [
        path
        for path in [
            readme_path,
            public_root / "AGENTS.md",
            pyproject_path,
            project_path / ".microcosm/catalog.json",
            project_path / ".microcosm/routes.json",
            project_path / ".microcosm/work_items.json",
        ]
        if path.is_file()
    ]
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(scan_inputs, forbidden_classes=policy, display_root=public_root)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan.get("blocking_hit_count"):
        blocking_codes.append("LAUNCH_COMPRESSION_PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "launch_compression_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_path.name,
        "one_line_identity": "repo -> .microcosm: turn any folder into an inspectable work substrate.",
        "quickstart_command": "microcosm compile .",
        "compiled_summary": {
            "headline": compiled.get("headline"),
            "file_count": compiled.get("file_count"),
            "passing_pattern_count": compiled.get("passing_pattern_count"),
            "route_count": compiled.get("route_count"),
            "selected_route_id": compiled.get("selected_route_id"),
            "work_id": compiled.get("work_id"),
            "event_count": compiled.get("event_count"),
            "evidence_count": compiled.get("evidence_count"),
            "open_observatory": compiled.get("open_observatory"),
        },
        "tour_summary": {
            "status": tour.get("status"),
            "time_budget_minutes": tour.get("time_budget_minutes"),
            "route_card_count": len(tour.get("route_cards", []))
            if isinstance(tour.get("route_cards"), list)
            else 0,
            "tour_ref": tour.get("tour_ref"),
            "release_authorized": tour.get("release_authorized") is True,
        },
        "trace_summary": {
            "status": trace_lens.get("status"),
            "trace_lens_ref": trace_lens.get("trace_lens_ref"),
            "trace_attempt_count": len(trace_lens.get("trace_rows", []))
            if isinstance(trace_lens.get("trace_rows"), list)
            else 0,
            "negative_case_count": len(trace_lens.get("negative_case_ids", []))
            if isinstance(trace_lens.get("negative_case_ids"), list)
            else 0,
            "formal_proof_authority": (trace_lens.get("authority_ceiling") or {}).get(
                "formal_proof_authority"
            )
            if isinstance(trace_lens.get("authority_ceiling"), dict)
            else None,
            "release_authorized": trace_lens.get("release_authorized") is True,
        },
        "repair_loop_summary": {
            "status": repair_loop.get("status"),
            "repair_loop_ref": repair_loop.get("repair_loop_ref"),
            "stage_count": len(repair_loop.get("loop_stages", []))
            if isinstance(repair_loop.get("loop_stages"), list)
            else 0,
            "transition_count": len(repair_loop.get("transition_rows", []))
            if isinstance(repair_loop.get("transition_rows"), list)
            else 0,
            "negative_case_count": len(repair_loop.get("negative_case_ids", []))
            if isinstance(repair_loop.get("negative_case_ids"), list)
            else 0,
            "formal_proof_authority": (repair_loop.get("authority_ceiling") or {}).get(
                "formal_proof_authority"
            )
            if isinstance(repair_loop.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (repair_loop.get("authority_ceiling") or {}).get(
                "proof_bodies_exported"
            )
            if isinstance(repair_loop.get("authority_ceiling"), dict)
            else None,
            "release_authorized": repair_loop.get("release_authorized") is True,
        },
        "formal_evidence_cell_summary": {
            "status": evidence_cells.get("status"),
            "evidence_cell_lens_ref": evidence_cells.get("evidence_cell_lens_ref"),
            "cell_count": len(evidence_cells.get("evidence_cells", []))
            if isinstance(evidence_cells.get("evidence_cells"), list)
            else 0,
            "negative_case_count": len(evidence_cells.get("negative_case_ids", []))
            if isinstance(evidence_cells.get("negative_case_ids"), list)
            else 0,
            "formal_proof_authority": (evidence_cells.get("authority_ceiling") or {}).get(
                "formal_proof_authority"
            )
            if isinstance(evidence_cells.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (evidence_cells.get("authority_ceiling") or {}).get(
                "proof_bodies_exported"
            )
            if isinstance(evidence_cells.get("authority_ceiling"), dict)
            else None,
            "release_authorized": evidence_cells.get("release_authorized") is True,
        },
        "proof_loop_depth_summary": {
            "status": proof_loop_depth.get("status"),
            "proof_loop_depth_ref": proof_loop_depth.get("proof_loop_depth_ref"),
            "gate_count": (proof_loop_depth.get("proof_loop_summary") or {}).get("gate_count")
            if isinstance(proof_loop_depth.get("proof_loop_summary"), dict)
            else None,
            "negative_case_count": (
                proof_loop_depth.get("proof_loop_summary") or {}
            ).get("negative_case_count")
            if isinstance(proof_loop_depth.get("proof_loop_summary"), dict)
            else None,
            "formal_proof_authority": (
                proof_loop_depth.get("authority_ceiling") or {}
            ).get("formal_proof_authority")
            if isinstance(proof_loop_depth.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (
                proof_loop_depth.get("authority_ceiling") or {}
            ).get("proof_bodies_exported")
            if isinstance(proof_loop_depth.get("authority_ceiling"), dict)
            else None,
            "benchmark_score_claim": (
                proof_loop_depth.get("authority_ceiling") or {}
            ).get("benchmark_score_claim")
            if isinstance(proof_loop_depth.get("authority_ceiling"), dict)
            else None,
            "release_authorized": proof_loop_depth.get("release_authorized") is True,
        },
        "landing_replay_summary": {
            "status": landing_replay.get("status"),
            "landing_replay_ref": landing_replay.get("landing_replay_ref"),
            "lane_count": len(landing_replay.get("lane_decision_table", []))
            if isinstance(landing_replay.get("lane_decision_table"), list)
            else 0,
            "negative_case_count": len(landing_replay.get("negative_case_ids", []))
            if isinstance(landing_replay.get("negative_case_ids"), list)
            else 0,
            "live_git_mutation_authorized": (
                landing_replay.get("authority_ceiling") or {}
            ).get("live_git_mutation_authorized")
            if isinstance(landing_replay.get("authority_ceiling"), dict)
            else None,
            "broad_checkpoint_authorized": (
                landing_replay.get("authority_ceiling") or {}
            ).get("broad_checkpoint_authorized")
            if isinstance(landing_replay.get("authority_ceiling"), dict)
            else None,
            "release_authorized": landing_replay.get("release_authorized") is True,
        },
        "view_quality_summary": {
            "status": view_quality.get("status"),
            "view_quality_lens_ref": view_quality.get("view_quality_lens_ref"),
            "action_row_count": len(view_quality.get("action_rows", []))
            if isinstance(view_quality.get("action_rows"), list)
            else 0,
            "hot_action_count": len(view_quality.get("hot_action_rollup", []))
            if isinstance(view_quality.get("hot_action_rollup"), list)
            else 0,
            "private_screenshot_paths_exported": (
                view_quality.get("authority_ceiling") or {}
            ).get("private_screenshot_paths_exported")
            if isinstance(view_quality.get("authority_ceiling"), dict)
            else None,
            "live_browser_control_authorized": (
                view_quality.get("authority_ceiling") or {}
            ).get("live_browser_control_authorized")
            if isinstance(view_quality.get("authority_ceiling"), dict)
            else None,
            "release_authorized": view_quality.get("release_authorized") is True,
        },
        "projection_safety_summary": {
            "status": projection_safety.get("status"),
            "projection_safety_lens_ref": projection_safety.get("projection_safety_lens_ref"),
            "projection_row_count": len(projection_safety.get("projection_rows", []))
            if isinstance(projection_safety.get("projection_rows"), list)
            else 0,
            "omission_receipt_count": (
                projection_safety.get("projection_summary") or {}
            ).get("omission_receipt_count")
            if isinstance(projection_safety.get("projection_summary"), dict)
            else None,
            "private_body_export_count": (
                projection_safety.get("projection_summary") or {}
            ).get("private_body_export_count")
            if isinstance(projection_safety.get("projection_summary"), dict)
            else None,
            "release_authorized": projection_safety.get("release_authorized") is True,
        },
        "market_prediction_boundary_summary": {
            "status": market_boundary.get("status"),
            "market_boundary_lens_ref": market_boundary.get("market_boundary_lens_ref"),
            "row_count": (market_boundary.get("boundary_summary") or {}).get("row_count")
            if isinstance(market_boundary.get("boundary_summary"), dict)
            else None,
            "decision_boundary_count": (
                market_boundary.get("boundary_summary") or {}
            ).get("decision_boundary_count")
            if isinstance(market_boundary.get("boundary_summary"), dict)
            else None,
            "negative_case_count": (
                market_boundary.get("boundary_summary") or {}
            ).get("negative_case_count")
            if isinstance(market_boundary.get("boundary_summary"), dict)
            else None,
            "trading_advice_authorized": (
                market_boundary.get("authority_ceiling") or {}
            ).get("trading_advice_authorized")
            if isinstance(market_boundary.get("authority_ceiling"), dict)
            else None,
            "private_portfolio_exported": (
                market_boundary.get("authority_ceiling") or {}
            ).get("private_portfolio_exported")
            if isinstance(market_boundary.get("authority_ceiling"), dict)
            else None,
            "performance_guarantee_claim": (
                market_boundary.get("authority_ceiling") or {}
            ).get("performance_guarantee_claim")
            if isinstance(market_boundary.get("authority_ceiling"), dict)
            else None,
        },
        "projection_drift_summary": {
            "status": projection_drift.get("status"),
            "projection_drift_lens_ref": projection_drift.get("projection_drift_lens_ref"),
            "row_count": (projection_drift.get("drift_summary") or {}).get("row_count")
            if isinstance(projection_drift.get("drift_summary"), dict)
            else None,
            "source_ref_count": (projection_drift.get("drift_summary") or {}).get(
                "source_ref_count"
            )
            if isinstance(projection_drift.get("drift_summary"), dict)
            else None,
            "repair_route_count": (projection_drift.get("drift_summary") or {}).get(
                "repair_route_count"
            )
            if isinstance(projection_drift.get("drift_summary"), dict)
            else None,
            "live_route_repair_authorized": (
                projection_drift.get("authority_ceiling") or {}
            ).get("live_route_repair_authorized")
            if isinstance(projection_drift.get("authority_ceiling"), dict)
            else None,
            "source_authority_claim": (
                projection_drift.get("authority_ceiling") or {}
            ).get("source_authority_claim")
            if isinstance(projection_drift.get("authority_ceiling"), dict)
            else None,
            "release_authorized": projection_drift.get("release_authorized") is True,
        },
        "route_cleanup_summary": {
            "status": route_cleanup.get("status"),
            "route_cleanup_lens_ref": route_cleanup.get("route_cleanup_lens_ref"),
            "row_count": (route_cleanup.get("cleanup_summary") or {}).get("row_count")
            if isinstance(route_cleanup.get("cleanup_summary"), dict)
            else None,
            "owner_route_count": (route_cleanup.get("cleanup_summary") or {}).get(
                "owner_route_count"
            )
            if isinstance(route_cleanup.get("cleanup_summary"), dict)
            else None,
            "validation_ref_count": (route_cleanup.get("cleanup_summary") or {}).get(
                "validation_ref_count"
            )
            if isinstance(route_cleanup.get("cleanup_summary"), dict)
            else None,
            "route_deletion_authorized": (
                route_cleanup.get("authority_ceiling") or {}
            ).get("route_deletion_authorized")
            if isinstance(route_cleanup.get("authority_ceiling"), dict)
            else None,
            "generated_region_hand_edit_authorized": (
                route_cleanup.get("authority_ceiling") or {}
            ).get("generated_region_hand_edit_authorized")
            if isinstance(route_cleanup.get("authority_ceiling"), dict)
            else None,
            "release_authorized": route_cleanup.get("release_authorized") is True,
        },
        "projection_import_map_summary": {
            "status": projection_import_map.get("status"),
            "projection_import_map_ref": projection_import_map.get("projection_import_map_ref"),
            "row_count": (projection_import_map.get("map_summary") or {}).get("row_count")
            if isinstance(projection_import_map.get("map_summary"), dict)
            else None,
            "stage_count": (projection_import_map.get("map_summary") or {}).get("stage_count")
            if isinstance(projection_import_map.get("map_summary"), dict)
            else None,
            "validation_ref_count": (
                projection_import_map.get("map_summary") or {}
            ).get("validation_ref_count")
            if isinstance(projection_import_map.get("map_summary"), dict)
            else None,
            "private_body_export_count": (
                projection_import_map.get("map_summary") or {}
            ).get("private_body_export_count")
            if isinstance(projection_import_map.get("map_summary"), dict)
            else None,
            "automated_import_guarantee": (
                projection_import_map.get("authority_ceiling") or {}
            ).get("automated_import_guarantee")
            if isinstance(projection_import_map.get("authority_ceiling"), dict)
            else None,
            "release_authorized": projection_import_map.get("release_authorized") is True,
        },
        "import_projector_summary": {
            "status": import_projector.get("status"),
            "import_projector_ref": import_projector.get("import_projector_ref"),
            "row_count": (import_projector.get("projector_summary") or {}).get("row_count")
            if isinstance(import_projector.get("projector_summary"), dict)
            else None,
            "stage_count": (import_projector.get("projector_summary") or {}).get("stage_count")
            if isinstance(import_projector.get("projector_summary"), dict)
            else None,
            "validation_ref_count": (
                import_projector.get("projector_summary") or {}
            ).get("validation_ref_count")
            if isinstance(import_projector.get("projector_summary"), dict)
            else None,
            "authority_ceiling_row_count": (
                import_projector.get("projector_summary") or {}
            ).get("authority_ceiling_row_count")
            if isinstance(import_projector.get("projector_summary"), dict)
            else None,
            "private_body_export_count": (
                import_projector.get("projector_summary") or {}
            ).get("private_body_export_count")
            if isinstance(import_projector.get("projector_summary"), dict)
            else None,
            "automated_import_execution_authorized": (
                import_projector.get("authority_ceiling") or {}
            ).get("automated_import_execution_authorized")
            if isinstance(import_projector.get("authority_ceiling"), dict)
            else None,
            "generated_region_hand_edit_authorized": (
                import_projector.get("authority_ceiling") or {}
            ).get("generated_region_hand_edit_authorized")
            if isinstance(import_projector.get("authority_ceiling"), dict)
            else None,
            "release_authorized": import_projector.get("release_authorized") is True,
        },
        "option_surface_summary": {
            "status": option_surface.get("status"),
            "option_surface_lens_ref": option_surface.get("option_surface_lens_ref"),
            "row_count": (option_surface.get("option_surface_summary") or {}).get("row_count")
            if isinstance(option_surface.get("option_surface_summary"), dict)
            else None,
            "stage_count": (option_surface.get("option_surface_summary") or {}).get(
                "stage_count"
            )
            if isinstance(option_surface.get("option_surface_summary"), dict)
            else None,
            "validation_ref_count": (
                option_surface.get("option_surface_summary") or {}
            ).get("validation_ref_count")
            if isinstance(option_surface.get("option_surface_summary"), dict)
            else None,
            "private_body_export_count": (
                option_surface.get("option_surface_summary") or {}
            ).get("private_body_export_count")
            if isinstance(option_surface.get("option_surface_summary"), dict)
            else None,
            "profile_switch_execution_authorized": (
                option_surface.get("authority_ceiling") or {}
            ).get("profile_switch_execution_authorized")
            if isinstance(option_surface.get("authority_ceiling"), dict)
            else None,
            "automatic_profile_selection_authorized": (
                option_surface.get("authority_ceiling") or {}
            ).get("automatic_profile_selection_authorized")
            if isinstance(option_surface.get("authority_ceiling"), dict)
            else None,
            "release_authorized": option_surface.get("release_authorized") is True,
        },
        "stripping_guard_summary": {
            "status": stripping_guard.get("status"),
            "stripping_guard_ref": stripping_guard.get("stripping_guard_ref"),
            "guard_row_count": (stripping_guard.get("guard_summary") or {}).get(
                "guard_row_count"
            )
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "negative_case_count": (stripping_guard.get("guard_summary") or {}).get(
                "negative_case_count"
            )
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "private_body_export_count": (
                stripping_guard.get("guard_summary") or {}
            ).get("private_body_export_count")
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "proof_body_export_count": (
                stripping_guard.get("guard_summary") or {}
            ).get("proof_body_export_count")
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "provider_payload_export_count": (
                stripping_guard.get("guard_summary") or {}
            ).get("provider_payload_export_count")
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "raw_private_path_export_count": (
                stripping_guard.get("guard_summary") or {}
            ).get("raw_private_path_export_count")
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "secret_token_export_count": (
                stripping_guard.get("guard_summary") or {}
            ).get("secret_token_export_count")
            if isinstance(stripping_guard.get("guard_summary"), dict)
            else None,
            "secret_detection_completeness_claim": (
                stripping_guard.get("authority_ceiling") or {}
            ).get("secret_detection_completeness_claim")
            if isinstance(stripping_guard.get("authority_ceiling"), dict)
            else None,
            "release_authorized": stripping_guard.get("release_authorized") is True,
        },
        "standards_control_summary": {
            "status": standards_control.get("status"),
            "standards_control_ref": standards_control.get("standards_control_ref"),
            "row_count": (standards_control.get("standards_summary") or {}).get(
                "standards_control_row_count"
            )
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "negative_case_count": (standards_control.get("standards_summary") or {}).get(
                "negative_case_count"
            )
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "standard_count": (standards_control.get("standards_summary") or {}).get(
                "standard_count"
            )
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "standard_pressure_row_count": (
                standards_control.get("standards_summary") or {}
            ).get("standard_pressure_row_count")
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "validator_receipt_ref_count": (
                standards_control.get("standards_summary") or {}
            ).get("validator_receipt_ref_count")
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "source_authority_claim_count": (
                standards_control.get("standards_summary") or {}
            ).get("source_authority_claim_count")
            if isinstance(standards_control.get("standards_summary"), dict)
            else None,
            "standards_completeness_claim": (
                standards_control.get("authority_ceiling") or {}
            ).get("standards_completeness_claim")
            if isinstance(standards_control.get("authority_ceiling"), dict)
            else None,
            "release_authorized": standards_control.get("release_authorized") is True,
        },
        "hook_intervention_coverage_summary": {
            "status": hook_coverage.get("status"),
            "hook_intervention_coverage_lens_ref": hook_coverage.get(
                "hook_intervention_coverage_lens_ref"
            ),
            "intervention_row_count": len(hook_coverage.get("intervention_rows", []))
            if isinstance(hook_coverage.get("intervention_rows"), list)
            else 0,
            "missing_authority_count": len(hook_coverage.get("missing_authority_case_ids", []))
            if isinstance(hook_coverage.get("missing_authority_case_ids"), list)
            else 0,
            "live_operator_state_read": (hook_coverage.get("authority_ceiling") or {}).get(
                "live_operator_state_read"
            )
            if isinstance(hook_coverage.get("authority_ceiling"), dict)
            else None,
            "provider_payload_read": (hook_coverage.get("authority_ceiling") or {}).get(
                "provider_payload_read"
            )
            if isinstance(hook_coverage.get("authority_ceiling"), dict)
            else None,
            "release_authorized": hook_coverage.get("release_authorized") is True,
        },
        "agent_reliability_replay_gauntlet_summary": {
            "status": replay_gauntlet.get("status"),
            "replay_gauntlet_lens_ref": replay_gauntlet.get("replay_gauntlet_lens_ref"),
            "episode_count": len(replay_gauntlet.get("episode_rows", []))
            if isinstance(replay_gauntlet.get("episode_rows"), list)
            else 0,
            "blocked_episode_count": (
                replay_gauntlet.get("coverage_summary") or {}
            ).get("blocked_episode_count")
            if isinstance(replay_gauntlet.get("coverage_summary"), dict)
            else None,
            "quarantined_episode_count": (
                replay_gauntlet.get("coverage_summary") or {}
            ).get("quarantined_episode_count")
            if isinstance(replay_gauntlet.get("coverage_summary"), dict)
            else None,
            "live_agent_execution_authorized": (
                replay_gauntlet.get("authority_ceiling") or {}
            ).get("live_agent_execution_authorized")
            if isinstance(replay_gauntlet.get("authority_ceiling"), dict)
            else None,
            "live_tool_calls_authorized": (
                replay_gauntlet.get("authority_ceiling") or {}
            ).get("live_tool_calls_authorized")
            if isinstance(replay_gauntlet.get("authority_ceiling"), dict)
            else None,
            "real_secret_material_exported": (
                replay_gauntlet.get("authority_ceiling") or {}
            ).get("real_secret_material_exported")
            if isinstance(replay_gauntlet.get("authority_ceiling"), dict)
            else None,
            "release_authorized": replay_gauntlet.get("release_authorized") is True,
        },
        "repository_benchmark_transaction_lab_summary": {
            "status": benchmark_lab.get("status"),
            "benchmark_lab_ref": benchmark_lab.get("benchmark_lab_ref"),
            "task_count": (benchmark_lab.get("scorecard") or {}).get("task_count")
            if isinstance(benchmark_lab.get("scorecard"), dict)
            else None,
            "oracle_patch_count": (benchmark_lab.get("scorecard") or {}).get("oracle_patch_count")
            if isinstance(benchmark_lab.get("scorecard"), dict)
            else None,
            "fail_to_pass_count": (benchmark_lab.get("scorecard") or {}).get("fail_to_pass_count")
            if isinstance(benchmark_lab.get("scorecard"), dict)
            else None,
            "pass_to_pass_count": (benchmark_lab.get("scorecard") or {}).get("pass_to_pass_count")
            if isinstance(benchmark_lab.get("scorecard"), dict)
            else None,
            "misleading_test_denial_count": (
                benchmark_lab.get("scorecard") or {}
            ).get("misleading_test_denial_count")
            if isinstance(benchmark_lab.get("scorecard"), dict)
            else None,
            "live_repo_mutation_authorized": (
                benchmark_lab.get("authority_ceiling") or {}
            ).get("live_repo_mutation_authorized")
            if isinstance(benchmark_lab.get("authority_ceiling"), dict)
            else None,
            "swe_bench_performance_claim": (
                benchmark_lab.get("authority_ceiling") or {}
            ).get("swe_bench_performance_claim")
            if isinstance(benchmark_lab.get("authority_ceiling"), dict)
            else None,
            "release_authorized": benchmark_lab.get("release_authorized") is True,
        },
        "cold_reader_legibility_scorecard_summary": {
            "status": legibility_scorecard.get("status"),
            "legibility_scorecard_ref": legibility_scorecard.get("legibility_scorecard_ref"),
            "checkpoint_count": (legibility_scorecard.get("scorecard") or {}).get(
                "checkpoint_count"
            )
            if isinstance(legibility_scorecard.get("scorecard"), dict)
            else None,
            "reader_question_count": (legibility_scorecard.get("scorecard") or {}).get(
                "reader_question_count"
            )
            if isinstance(legibility_scorecard.get("scorecard"), dict)
            else None,
            "time_budget_minutes": (legibility_scorecard.get("scorecard") or {}).get(
                "time_budget_minutes"
            )
            if isinstance(legibility_scorecard.get("scorecard"), dict)
            else None,
            "release_authorized": (
                legibility_scorecard.get("authority_ceiling") or {}
            ).get("release_authorized")
            if isinstance(legibility_scorecard.get("authority_ceiling"), dict)
            else None,
            "reader_success_guarantee": (
                legibility_scorecard.get("authority_ceiling") or {}
            ).get("reader_success_guarantee")
            if isinstance(legibility_scorecard.get("authority_ceiling"), dict)
            else None,
            "private_data_equivalence_claim": (
                legibility_scorecard.get("authority_ceiling") or {}
            ).get("private_data_equivalence_claim")
            if isinstance(legibility_scorecard.get("authority_ceiling"), dict)
            else None,
        },
        "assertions": assertions,
        "blocking_codes": blocking_codes,
        "private_state_scan": safe_scan,
        "authority_ceiling": {
            "release_authorized": False,
            "hosting_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": "Launch-compression validation proves that the public first screen and one-command local loop expose repo -> .microcosm without receipt-first UX and without downgrading real non-secret substrate into placeholders. It does not authorize hosted release operations, publication, credentialed provider calls, unsafe source mutation, or secret export.",
        "receipt_paths": [_public_relative(public_root, output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Microcosm launch compression")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.launch_compression "
        f"--root {args.root} --project {Path(args.project).name} --out {args.out}"
    )
    receipt = validate_launch_compression(args.root, args.project, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
