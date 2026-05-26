from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic
from microcosm_core.runtime_shell import RuntimeShell


CHECKER_ID = "checker.microcosm.validators.observatory_legibility"


def _public_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _html_private_hits(html: str) -> list[str]:
    return [
        needle
        for needle in [
            "/Users/",
            "src/ai_workflow",
            "Library/Application Support/Google/" + "Chrome",
            "sk" + "-",
        ]
        if needle in html
    ]


def validate_legibility(
    root: str | Path,
    project: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    project_path = Path(project).expanduser().resolve(strict=False)
    output_file = Path(out_path)
    shell = RuntimeShell(public_root)
    model = shell.project_observatory(project_path)
    html = shell._observatory_html(project_path)
    causal = model.get("causal_chain", {}) if isinstance(model.get("causal_chain"), dict) else {}
    observatory_card = (
        model.get("observatory_card", {})
        if isinstance(model.get("observatory_card"), dict)
        else {}
    )
    first_screen_composition = (
        model.get("first_screen_composition", {})
        if isinstance(model.get("first_screen_composition"), dict)
        else {}
    )
    landing_frame = (
        first_screen_composition.get("observatory_landing_frame", {})
        if isinstance(first_screen_composition.get("observatory_landing_frame"), dict)
        else {}
    )
    browser_landing_reuse = (
        landing_frame.get("browser_landing_reuse", {})
        if isinstance(landing_frame.get("browser_landing_reuse"), dict)
        else {}
    )
    required_landing_handles = landing_frame.get("required_visible_handles", [])
    if not isinstance(required_landing_handles, list):
        required_landing_handles = []
    required_landing_handle_set = {str(row) for row in required_landing_handles}
    evidence_class_legend = (
        first_screen_composition.get("evidence_class_legend", {})
        if isinstance(first_screen_composition.get("evidence_class_legend"), dict)
        else {}
    )
    evidence_classes = evidence_class_legend.get("classes", [])
    if not isinstance(evidence_classes, list):
        evidence_classes = []
    observatory_reader_sequence = observatory_card.get("reader_sequence", [])
    if not isinstance(observatory_reader_sequence, list):
        observatory_reader_sequence = []
    runtime_bridge = model.get("runtime_bridge", {}) if isinstance(model.get("runtime_bridge"), dict) else {}
    tour = model.get("tour", {}) if isinstance(model.get("tour"), dict) else {}
    source_open_body_import_floor = (
        model.get("source_open_body_import_floor", {})
        if isinstance(model.get("source_open_body_import_floor"), dict)
        else {}
    )
    authority_map = model.get("authority_map", {}) if isinstance(model.get("authority_map"), dict) else {}
    prediction_lens = (
        model.get("prediction_lens", {}) if isinstance(model.get("prediction_lens"), dict) else {}
    )
    market_boundary_lens = (
        model.get("market_boundary_lens", {})
        if isinstance(model.get("market_boundary_lens"), dict)
        else {}
    )
    corpus_lens = model.get("corpus_lens", {}) if isinstance(model.get("corpus_lens"), dict) else {}
    trace_lens = model.get("trace_lens", {}) if isinstance(model.get("trace_lens"), dict) else {}
    repair_loop_lens = (
        model.get("repair_loop_lens", {})
        if isinstance(model.get("repair_loop_lens"), dict)
        else {}
    )
    evidence_cell_lens = (
        model.get("evidence_cell_lens", {})
        if isinstance(model.get("evidence_cell_lens"), dict)
        else {}
    )
    proof_loop_depth_lens = (
        model.get("proof_loop_depth_lens", {})
        if isinstance(model.get("proof_loop_depth_lens"), dict)
        else {}
    )
    landing_replay_lens = (
        model.get("landing_replay_lens", {})
        if isinstance(model.get("landing_replay_lens"), dict)
        else {}
    )
    view_quality_lens = (
        model.get("view_quality_lens", {})
        if isinstance(model.get("view_quality_lens"), dict)
        else {}
    )
    projection_safety_lens = (
        model.get("projection_safety_lens", {})
        if isinstance(model.get("projection_safety_lens"), dict)
        else {}
    )
    projection_drift_lens = (
        model.get("projection_drift_lens", {})
        if isinstance(model.get("projection_drift_lens"), dict)
        else {}
    )
    route_cleanup_lens = (
        model.get("route_cleanup_lens", {})
        if isinstance(model.get("route_cleanup_lens"), dict)
        else {}
    )
    projection_import_map_lens = (
        model.get("projection_import_map_lens", {})
        if isinstance(model.get("projection_import_map_lens"), dict)
        else {}
    )
    import_projector_lens = (
        model.get("import_projector_lens", {})
        if isinstance(model.get("import_projector_lens"), dict)
        else {}
    )
    option_surface_lens = (
        model.get("option_surface_lens", {})
        if isinstance(model.get("option_surface_lens"), dict)
        else {}
    )
    stripping_guard_lens = (
        model.get("stripping_guard_lens", {})
        if isinstance(model.get("stripping_guard_lens"), dict)
        else {}
    )
    standards_control_lens = (
        model.get("standards_control_lens", {})
        if isinstance(model.get("standards_control_lens"), dict)
        else {}
    )
    hook_coverage_lens = (
        model.get("hook_coverage_lens", {})
        if isinstance(model.get("hook_coverage_lens"), dict)
        else {}
    )
    replay_gauntlet_lens = (
        model.get("replay_gauntlet_lens", {})
        if isinstance(model.get("replay_gauntlet_lens"), dict)
        else {}
    )
    benchmark_lab_lens = (
        model.get("benchmark_lab_lens", {})
        if isinstance(model.get("benchmark_lab_lens"), dict)
        else {}
    )
    legibility_scorecard_lens = (
        model.get("legibility_scorecard_lens", {})
        if isinstance(model.get("legibility_scorecard_lens"), dict)
        else {}
    )
    route = causal.get("route", {}) if isinstance(causal.get("route"), dict) else {}
    work = causal.get("work_transaction", {}) if isinstance(causal.get("work_transaction"), dict) else {}
    pattern_bindings = causal.get("pattern_bindings", [])
    standard_bindings = causal.get("standard_bindings", [])
    events = causal.get("events", [])
    evidence = causal.get("evidence", [])
    bridge_cells = runtime_bridge.get("cell_status", [])
    if not isinstance(pattern_bindings, list):
        pattern_bindings = []
    if not isinstance(standard_bindings, list):
        standard_bindings = []
    if not isinstance(events, list):
        events = []
    if not isinstance(evidence, list):
        evidence = []
    if not isinstance(bridge_cells, list):
        bridge_cells = []

    html_assertions = {
        "root_is_not_raw_json_only": "Causal Chain" in html and "JSON Drilldowns" in html,
        "first_screen_card_endpoint_visible": "/project/first-screen" in html,
        "observatory_card_endpoint_visible": "/project/observatory-card" in html,
        "first_screen_text_card_visible": "Microcosm first screen" in html
        and "Open card:" in html,
        "first_screen_reader_branches_visible": "Reader branches:" in html
        and "Safety/evals:" in html
        and "Hiring:" in html
        and "Peer developer:" in html,
        "first_screen_reader_route_cards_visible": "Reader Route Choices" in html
        and "First action" in html
        and "Proof surface" in html
        and "Success criterion" in html,
        "first_screen_reader_route_questions_visible": (
            "Does the evidence discipline survive contact with scale?" in html
            and "Is this real, inspectable, and built with the judgment" in html
            and "Can I clone it, run it, and understand the first useful path" in html
        ),
        "first_screen_reader_exit_cards_visible": "Exit when" in html
        and "Can name evidence-class ceilings" in html
        and "Can distinguish runnable local behavior" in html
        and "Can find .microcosm state refs" in html,
        "first_screen_exit_rule_visible": (
            "exit when you can choose a drilldown without the command inventory"
            in html
        ),
        "first_screen_hello_command_visible": (
            "microcosm hello &lt;project&gt;" in html
            or "microcosm hello <project>" in html
        ),
        "first_screen_authority_ceiling_visible": "No release, hosted publication"
        in html,
        "raw_observatory_model_not_embedded": "Raw observatory model" not in html
        and "<pre>" not in html,
        "observatory_html_under_first_screen_budget": len(html.encode("utf-8")) < 500_000,
        "causal_chain_section_present": "Causal Chain" in html,
        "route_id_visible": bool(route.get("route_id")) and str(route.get("route_id")) in html,
        "pattern_binding_visible": any(
            isinstance(row, dict) and row.get("resolved") is True and str(row.get("pattern_id")) in html
            for row in pattern_bindings
        ),
        "standard_binding_visible": any(
            isinstance(row, dict) and row.get("resolved") is True and str(row.get("standard_id")) in html
            for row in standard_bindings
        ),
        "work_state_history_visible": (
            "created -> selected -> planned -> executed_simulation -> closed" in html
            or "created -&gt; selected -&gt; planned -&gt; executed_simulation -&gt; closed" in html
        ),
        "event_refs_visible": bool(events) and any(str(row.get("event_id")) in html for row in events if isinstance(row, dict)),
        "evidence_refs_visible": bool(evidence)
        and any(str(row.get("evidence_ref")) in html for row in evidence if isinstance(row, dict)),
        "evidence_marked_drilldown": "Evidence is drilldown" in html,
        "ten_minute_tour_section_present": "Ten-Minute Tour" in html,
        "source_open_body_import_floor_section_present": (
            "Source-Open Body Import Floor" in html
            and "source_open_body_import_floor" in html
        ),
        "source_open_body_material_count_visible": (
            source_open_body_import_floor.get("public_safe_body_material_count")
            is not None
            and str(
                source_open_body_import_floor.get("public_safe_body_material_count")
            )
            in html
        ),
        "source_open_body_text_exclusion_visible": (
            "Body text exported in status" in html
            and "Body text exported in receipts" in html
        ),
        "runtime_bridge_section_present": "Spine / Intake / Reveal Bridge" in html,
        "market_prediction_boundary_lens_section_present": "Market Prediction Boundary Lens"
        in html,
        "corpus_lens_section_present": "Corpus Readiness Lens" in html,
        "verifier_trace_lens_section_present": "Verifier Trace Repair Lens" in html,
        "verifier_repair_loop_lens_section_present": "Verifier Repair Loop Lens" in html,
        "formal_evidence_cell_lens_section_present": "Formal Evidence Cell Lens" in html,
        "proof_loop_depth_lens_section_present": "Proof Loop Depth Lens" in html,
        "work_landing_replay_lens_section_present": "Work Landing Replay Lens" in html,
        "view_quality_action_map_lens_section_present": "View Quality Action Map Lens" in html,
        "projection_safety_audit_lens_section_present": "Projection Safety Audit Lens" in html,
        "projection_drift_control_lens_section_present": "Projection Drift Control Lens"
        in html,
        "route_cleanup_contract_lens_section_present": "Route Cleanup Contract Lens"
        in html,
        "projection_import_map_lens_section_present": "Projection Import Map Lens" in html,
        "import_projector_contract_lens_section_present": "Import Projector Contract Lens"
        in html,
        "compression_profile_option_surface_lens_section_present": (
            "Compression Profile Option Surface Lens" in html
        ),
        "stripping_guard_lens_section_present": "Public/Private Stripping Guard Lens" in html,
        "standards_control_lens_section_present": "Standards Control Lens" in html,
        "hook_intervention_coverage_lens_section_present": "Hook Intervention Coverage Lens" in html,
        "agent_reliability_replay_gauntlet_lens_section_present": "Agent Reliability Replay Gauntlet"
        in html,
        "repository_benchmark_transaction_lab_lens_section_present": (
            "Repository Benchmark Transaction Lab" in html
        ),
        "cold_reader_legibility_scorecard_lens_section_present": (
            "Cold Reader Legibility Scorecard" in html
        ),
        "runtime_bridge_endpoints_visible": all(
            token in html
            for token in [
                "/tour",
                "/spine",
                "/authority",
                "/prediction",
                "/market-boundary",
                "/corpus",
                "/trace",
                "/repair-loop",
                "/evidence-cells",
                "/proof-loop-depth",
                "/landing-replay",
                "/view-quality",
                "/projection-safety",
                "/drift-control",
                "/route-cleanup",
                "/projection-import-map",
                "/import-projector",
                "/option-surface-lens",
                "/stripping-guard",
                "/standards-control",
                "/hook-coverage",
                "/replay-gauntlet",
                "/benchmark-lab",
                "/legibility-scorecard",
                "/intake",
                "/reveal",
            ]
        ),
        "projection_status_counts_visible": "self_hosted_status_protocol_landed" in html,
        "closed_intake_cells_visible": "runtime_reveal_import_bridge" in html,
        "release_ceiling_visible": "Release remains unauthorized" in html,
        "provider_ceiling_visible": "Provider calls authorized" in html,
        "source_mutation_ceiling_visible": "Source mutation authorized" in html,
        "private_paths_absent": not _html_private_hits(html),
    }
    model_assertions = {
        "model_status_pass": model.get("status") == PASS,
        "observatory_card_first_screen_endpoint_present": (
            observatory_card.get("html_endpoint") == "/"
            and observatory_card.get("first_screen_endpoint") == "/project/first-screen"
            and any(
                isinstance(row, dict)
                and row.get("step_id") == "read_first_screen_composition"
                and row.get("endpoint") == "/project/first-screen"
                for row in observatory_reader_sequence
            )
        ),
        "first_screen_composition_status_pass": (
            first_screen_composition.get("status") == PASS
        ),
        "first_screen_landing_frame_targets_browser_root": (
            landing_frame.get("role")
            == "make_the_hello_first_screen_card_the_browser_landing_frame"
            and landing_frame.get("human_first_command") == "microcosm hello <project>"
            and landing_frame.get("shared_first_command")
            == "microcosm tour --card <project>"
            and browser_landing_reuse.get("default_endpoint") == "/"
            and browser_landing_reuse.get("card_endpoint") == "/project/first-screen"
            and browser_landing_reuse.get("source_projection")
            == "microcosm_core.first_screen_composition.first_screen_text_card"
        ),
        "first_screen_landing_handles_present": all(
            handle in required_landing_handle_set
            for handle in [
                "human_first_command",
                "text_projection",
                "shared_first_command",
                "behavioral_proof_command",
                "reader_route_ids",
                "public_scale_counts",
                "evidence_count_interpretation",
                "evidence_class_legend",
                "authority_ceiling",
                "omission_receipt",
            ]
        ),
        "first_screen_evidence_class_legend_present": {
            row.get("evidence_class")
            for row in evidence_classes
            if isinstance(row, dict)
        }
        >= {
            "verified_macro_body_import",
            "external_subprocess_witness",
            "semantic_validator",
            "algorithmic_projection",
            "fixture_schema_replay",
            "fixture_echo_smoke",
        },
        "source_open_body_import_floor_present": (
            source_open_body_import_floor.get("status") == PASS
            and source_open_body_import_floor.get("public_safe_body_material_count", 0)
            > 0
            and source_open_body_import_floor.get("body_text_exported_in_status")
            is False
            and source_open_body_import_floor.get("body_text_exported_in_receipts")
            is False
        ),
        "route_pattern_refs_present": bool(route.get("pattern_refs")),
        "route_standard_refs_present": bool(route.get("standard_pressure_refs")),
        "pattern_bindings_resolve": bool(pattern_bindings)
        and all(isinstance(row, dict) and row.get("resolved") is True for row in pattern_bindings),
        "standard_bindings_resolve": bool(standard_bindings)
        and all(isinstance(row, dict) and row.get("resolved") is True for row in standard_bindings),
        "work_transaction_present": bool(work.get("work_id")),
        "work_state_history_present": bool(work.get("state_history")),
        "events_present": bool(events),
        "evidence_present": bool(evidence),
        "ten_minute_tour_status_pass": tour.get("status") == PASS,
        "ten_minute_tour_endpoint_present": "/tour" in (tour.get("endpoint_path") or []),
        "runtime_bridge_warning_status_bounded": runtime_bridge.get("status")
        in {PASS, "blocked"}
        and runtime_bridge.get("open_actionable_cell_count") == 0,
        "authority_map_warning_status_bounded": authority_map.get("status")
        in {PASS, "blocked"}
        and all(
            value is False
            for value in (
                authority_map.get("authority_ceiling", {})
                if isinstance(authority_map.get("authority_ceiling"), dict)
                else {}
            ).values()
        ),
        "prediction_lens_status_pass": prediction_lens.get("status") == PASS,
        "market_prediction_boundary_lens_status_pass": market_boundary_lens.get("status")
        == PASS,
        "corpus_lens_status_pass": corpus_lens.get("status") == PASS,
        "verifier_trace_lens_status_pass": trace_lens.get("status") == PASS,
        "verifier_repair_loop_lens_status_pass": repair_loop_lens.get("status") == PASS,
        "formal_evidence_cell_lens_status_pass": evidence_cell_lens.get("status") == PASS,
        "proof_loop_depth_lens_status_pass": proof_loop_depth_lens.get("status") == PASS,
        "work_landing_replay_lens_status_pass": landing_replay_lens.get("status") == PASS,
        "view_quality_action_map_lens_status_pass": view_quality_lens.get("status") == PASS,
        "projection_safety_audit_lens_status_pass": projection_safety_lens.get("status") == PASS,
        "projection_drift_control_lens_status_pass": projection_drift_lens.get("status")
        == PASS,
        "route_cleanup_contract_lens_status_pass": route_cleanup_lens.get("status") == PASS,
        "projection_import_map_lens_status_pass": projection_import_map_lens.get("status")
        == PASS,
        "import_projector_contract_lens_status_pass": import_projector_lens.get("status")
        == PASS,
        "compression_profile_option_surface_lens_status_pass": option_surface_lens.get(
            "status"
        )
        == PASS,
        "stripping_guard_lens_status_pass": stripping_guard_lens.get("status") == PASS,
        "standards_control_lens_status_pass": standards_control_lens.get("status") == PASS,
        "hook_intervention_coverage_lens_status_pass": hook_coverage_lens.get("status") == PASS,
        "agent_reliability_replay_gauntlet_lens_status_pass": replay_gauntlet_lens.get("status")
        == PASS,
        "repository_benchmark_transaction_lab_lens_status_pass": benchmark_lab_lens.get("status")
        == PASS,
        "cold_reader_legibility_scorecard_lens_status_pass": legibility_scorecard_lens.get(
            "status"
        )
        == PASS,
        "verifier_trace_lens_no_proof_authority": (
            isinstance(trace_lens.get("authority_ceiling"), dict)
            and trace_lens["authority_ceiling"].get("formal_proof_authority") is False
            and trace_lens["authority_ceiling"].get("proof_bodies_exported") is False
            and trace_lens["authority_ceiling"].get("oracle_needed_premise_ids_exported") is False
        ),
        "verifier_repair_loop_lens_no_proof_authority": (
            isinstance(repair_loop_lens.get("authority_ceiling"), dict)
            and repair_loop_lens["authority_ceiling"].get("formal_proof_authority") is False
            and repair_loop_lens["authority_ceiling"].get("proof_bodies_exported") is False
            and repair_loop_lens["authority_ceiling"].get("oracle_needed_premise_ids_exported") is False
            and repair_loop_lens["authority_ceiling"].get("provider_calls_authorized") is False
        ),
        "formal_evidence_cell_lens_no_proof_authority": (
            isinstance(evidence_cell_lens.get("authority_ceiling"), dict)
            and evidence_cell_lens["authority_ceiling"].get("formal_proof_authority") is False
            and evidence_cell_lens["authority_ceiling"].get("proof_bodies_exported") is False
            and evidence_cell_lens["authority_ceiling"].get("private_source_refs_exported") is False
            and evidence_cell_lens["authority_ceiling"].get("general_theorem_solution_claim") is False
        ),
        "proof_loop_depth_lens_no_proof_or_benchmark_authority": (
            isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict)
            and proof_loop_depth_lens["authority_ceiling"].get("formal_proof_authority")
            is False
            and proof_loop_depth_lens["authority_ceiling"].get("proof_bodies_exported")
            is False
            and proof_loop_depth_lens["authority_ceiling"].get(
                "oracle_needed_premise_ids_exported"
            )
            is False
            and proof_loop_depth_lens["authority_ceiling"].get("benchmark_score_claim")
            is False
            and proof_loop_depth_lens["authority_ceiling"].get(
                "general_theorem_solution_claim"
            )
            is False
        ),
        "work_landing_replay_lens_no_git_authority": (
            isinstance(landing_replay_lens.get("authority_ceiling"), dict)
            and landing_replay_lens["authority_ceiling"].get("live_git_mutation_authorized") is False
            and landing_replay_lens["authority_ceiling"].get("broad_checkpoint_authorized") is False
            and landing_replay_lens["authority_ceiling"].get("source_mutation_authorized") is False
        ),
        "view_quality_action_map_lens_no_private_ui_authority": (
            isinstance(view_quality_lens.get("authority_ceiling"), dict)
            and view_quality_lens["authority_ceiling"].get("private_screenshot_paths_exported") is False
            and view_quality_lens["authority_ceiling"].get("live_browser_control_authorized") is False
            and view_quality_lens["authority_ceiling"].get("complete_frontend_quality_claim") is False
        ),
        "projection_safety_audit_lens_no_private_exports": (
            isinstance(projection_safety_lens.get("projection_summary"), dict)
            and projection_safety_lens["projection_summary"].get("private_body_export_count") == 0
            and projection_safety_lens["projection_summary"].get("proof_body_export_count") == 0
            and projection_safety_lens["projection_summary"].get("provider_payload_export_count") == 0
            and projection_safety_lens["projection_summary"].get("release_authorized_count") == 0
        ),
        "market_prediction_boundary_no_private_exports_or_advice": (
            isinstance(market_boundary_lens.get("authority_ceiling"), dict)
            and market_boundary_lens["authority_ceiling"].get("live_market_data_authorized")
            is False
            and market_boundary_lens["authority_ceiling"].get("trading_advice_authorized")
            is False
            and market_boundary_lens["authority_ceiling"].get(
                "investment_recommendation_authorized"
            )
            is False
            and market_boundary_lens["authority_ceiling"].get("private_portfolio_exported")
            is False
            and market_boundary_lens["authority_ceiling"].get("performance_guarantee_claim")
            is False
        ),
        "projection_drift_control_lens_no_live_or_source_authority": (
            isinstance(projection_drift_lens.get("authority_ceiling"), dict)
            and projection_drift_lens["authority_ceiling"].get("source_authority_claim")
            is False
            and projection_drift_lens["authority_ceiling"].get("live_route_repair_authorized")
            is False
            and projection_drift_lens["authority_ceiling"].get("source_mutation_authorized")
            is False
            and projection_drift_lens["authority_ceiling"].get(
                "automatic_doctrine_promotion_authorized"
            )
            is False
        ),
        "projection_drift_control_lens_rows_validated": (
            isinstance(projection_drift_lens.get("drift_summary"), dict)
            and projection_drift_lens["drift_summary"].get("row_count") == 8
            and projection_drift_lens["drift_summary"].get("source_ref_count") == 8
            and projection_drift_lens["drift_summary"].get("repair_route_count") == 8
            and projection_drift_lens["drift_summary"].get("validation_ref_count") == 8
        ),
        "route_cleanup_contract_lens_no_route_or_source_mutation": (
            isinstance(route_cleanup_lens.get("authority_ceiling"), dict)
            and route_cleanup_lens["authority_ceiling"].get("route_deletion_authorized")
            is False
            and route_cleanup_lens["authority_ceiling"].get("source_mutation_authorized")
            is False
            and route_cleanup_lens["authority_ceiling"].get(
                "generated_region_hand_edit_authorized"
            )
            is False
            and route_cleanup_lens["authority_ceiling"].get("private_body_exported")
            is False
        ),
        "route_cleanup_contract_lens_rows_validated": (
            isinstance(route_cleanup_lens.get("cleanup_summary"), dict)
            and route_cleanup_lens["cleanup_summary"].get("row_count") == 8
            and route_cleanup_lens["cleanup_summary"].get("source_ref_count") == 8
            and route_cleanup_lens["cleanup_summary"].get("owner_route_count") == 8
            and route_cleanup_lens["cleanup_summary"].get("validation_ref_count") == 8
            and route_cleanup_lens["cleanup_summary"].get("route_deletion_authorized_count")
            == 0
            and route_cleanup_lens["cleanup_summary"].get(
                "generated_region_hand_edit_authorized_count"
            )
            == 0
        ),
        "projection_import_map_lens_no_private_exports_or_auto_import": (
            isinstance(projection_import_map_lens.get("authority_ceiling"), dict)
            and projection_import_map_lens["authority_ceiling"].get(
                "private_body_export_authorized"
            )
            is False
            and projection_import_map_lens["authority_ceiling"].get(
                "proof_body_export_authorized"
            )
            is False
            and projection_import_map_lens["authority_ceiling"].get(
                "provider_payload_export_authorized"
            )
            is False
            and projection_import_map_lens["authority_ceiling"].get("automated_import_guarantee")
            is False
        ),
        "import_projector_contract_lens_no_private_exports_or_execution": (
            isinstance(import_projector_lens.get("authority_ceiling"), dict)
            and import_projector_lens["authority_ceiling"].get(
                "private_body_export_authorized"
            )
            is False
            and import_projector_lens["authority_ceiling"].get(
                "proof_body_export_authorized"
            )
            is False
            and import_projector_lens["authority_ceiling"].get(
                "provider_payload_export_authorized"
            )
            is False
            and import_projector_lens["authority_ceiling"].get(
                "generated_region_hand_edit_authorized"
            )
            is False
            and import_projector_lens["authority_ceiling"].get(
                "automated_import_execution_authorized"
            )
            is False
            and import_projector_lens["authority_ceiling"].get("lossless_projection_claim")
            is False
        ),
        "import_projector_contract_lens_rows_validated": (
            isinstance(import_projector_lens.get("projector_summary"), dict)
            and import_projector_lens["projector_summary"].get("row_count") == 9
            and import_projector_lens["projector_summary"].get("stage_count") == 6
            and import_projector_lens["projector_summary"].get("validation_ref_count") == 9
            and import_projector_lens["projector_summary"].get("authority_ceiling_row_count")
            == 9
            and import_projector_lens["projector_summary"].get("private_body_export_count")
            == 0
            and import_projector_lens["projector_summary"].get(
                "generated_region_hand_edit_authorized_count"
            )
            == 0
        ),
        "compression_profile_option_surface_no_private_exports_or_execution": (
            isinstance(option_surface_lens.get("authority_ceiling"), dict)
            and option_surface_lens["authority_ceiling"].get("private_body_export_authorized")
            is False
            and option_surface_lens["authority_ceiling"].get(
                "provider_payload_export_authorized"
            )
            is False
            and option_surface_lens["authority_ceiling"].get(
                "profile_switch_execution_authorized"
            )
            is False
            and option_surface_lens["authority_ceiling"].get(
                "automatic_profile_selection_authorized"
            )
            is False
            and option_surface_lens["authority_ceiling"].get("lossless_projection_claim")
            is False
        ),
        "compression_profile_option_surface_rows_validated": (
            isinstance(option_surface_lens.get("option_surface_summary"), dict)
            and option_surface_lens["option_surface_summary"].get("row_count") == 6
            and option_surface_lens["option_surface_summary"].get("stage_count") == 6
            and option_surface_lens["option_surface_summary"].get("validation_ref_count")
            == 6
            and option_surface_lens["option_surface_summary"].get(
                "authority_ceiling_row_count"
            )
            == 6
            and option_surface_lens["option_surface_summary"].get(
                "private_body_export_count"
            )
            == 0
            and option_surface_lens["option_surface_summary"].get(
                "profile_switch_execution_authorized_count"
            )
            == 0
        ),
        "stripping_guard_lens_no_private_exports_or_release": (
            isinstance(stripping_guard_lens.get("guard_summary"), dict)
            and stripping_guard_lens["guard_summary"].get("private_body_export_count") == 0
            and stripping_guard_lens["guard_summary"].get("proof_body_export_count") == 0
            and stripping_guard_lens["guard_summary"].get("provider_payload_export_count") == 0
            and stripping_guard_lens["guard_summary"].get("raw_private_path_export_count") == 0
            and stripping_guard_lens["guard_summary"].get("secret_token_export_count") == 0
            and stripping_guard_lens["guard_summary"].get("release_authorized") is False
        ),
        "stripping_guard_lens_denies_secret_and_finance_claims": (
            isinstance(stripping_guard_lens.get("authority_ceiling"), dict)
            and stripping_guard_lens["authority_ceiling"].get(
                "secret_detection_completeness_claim"
            )
            is False
            and stripping_guard_lens["authority_ceiling"].get("financial_advice_authorized")
            is False
            and stripping_guard_lens["authority_ceiling"].get("source_mutation_authorized")
            is False
            and stripping_guard_lens["authority_ceiling"].get(
                "private_data_equivalence_claim"
            )
            is False
        ),
        "standards_control_lens_no_source_or_release_authority": (
            isinstance(standards_control_lens.get("authority_ceiling"), dict)
            and standards_control_lens["authority_ceiling"].get(
                "standards_registry_source_authority"
            )
            is False
            and standards_control_lens["authority_ceiling"].get(
                "standards_completeness_claim"
            )
            is False
            and standards_control_lens["authority_ceiling"].get("provider_calls_authorized")
            is False
            and standards_control_lens["authority_ceiling"].get("source_mutation_authorized")
            is False
            and standards_control_lens["authority_ceiling"].get("release_authorized") is False
        ),
        "standards_control_lens_no_private_exports": (
            isinstance(standards_control_lens.get("standards_summary"), dict)
            and standards_control_lens["standards_summary"].get("private_body_export_count")
            == 0
            and standards_control_lens["standards_summary"].get("proof_body_export_count")
            == 0
            and standards_control_lens["standards_summary"].get(
                "provider_payload_export_count"
            )
            == 0
            and standards_control_lens["standards_summary"].get(
                "source_authority_claim_count"
            )
            == 0
        ),
        "hook_intervention_coverage_lens_no_live_authority": (
            isinstance(hook_coverage_lens.get("authority_ceiling"), dict)
            and hook_coverage_lens["authority_ceiling"].get("live_operator_state_read") is False
            and hook_coverage_lens["authority_ceiling"].get("provider_payload_read") is False
            and hook_coverage_lens["authority_ceiling"].get("live_task_ledger_mutation_authorized")
            is False
            and hook_coverage_lens["authority_ceiling"].get("pattern_assimilation_authorized")
            is False
        ),
        "agent_reliability_replay_gauntlet_lens_no_live_authority": (
            isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict)
            and replay_gauntlet_lens["authority_ceiling"].get("live_agent_execution_authorized")
            is False
            and replay_gauntlet_lens["authority_ceiling"].get("live_tool_calls_authorized")
            is False
            and replay_gauntlet_lens["authority_ceiling"].get("real_secret_material_exported")
            is False
            and replay_gauntlet_lens["authority_ceiling"].get("complete_security_claim") is False
        ),
        "repository_benchmark_transaction_lab_lens_no_live_authority": (
            isinstance(benchmark_lab_lens.get("authority_ceiling"), dict)
            and benchmark_lab_lens["authority_ceiling"].get("live_repo_mutation_authorized")
            is False
            and benchmark_lab_lens["authority_ceiling"].get("provider_call_authorized") is False
            and benchmark_lab_lens["authority_ceiling"].get("swe_bench_performance_claim") is False
            and benchmark_lab_lens["authority_ceiling"].get("production_delivery_rate_claim")
            is False
        ),
        "cold_reader_legibility_scorecard_lens_no_release_or_reader_guarantee": (
            isinstance(legibility_scorecard_lens.get("authority_ceiling"), dict)
            and legibility_scorecard_lens["authority_ceiling"].get("release_authorized")
            is False
            and legibility_scorecard_lens["authority_ceiling"].get("reader_success_guarantee")
            is False
            and legibility_scorecard_lens["authority_ceiling"].get(
                "private_data_equivalence_claim"
            )
            is False
            and legibility_scorecard_lens["authority_ceiling"].get("benchmark_score_claim")
            is False
        ),
        "corpus_lens_mathlib_absence_visible": (
            isinstance(corpus_lens.get("corpus_summary"), dict)
            and corpus_lens["corpus_summary"].get("mathlib_lake_project_import_available") is False
        ),
        "runtime_bridge_id_present": runtime_bridge.get("bridge_id") == "intake_observatory_bridge",
        "runtime_bridge_open_actionable_zero": runtime_bridge.get("open_actionable_cell_count") == 0,
        "runtime_bridge_closed_cells_present": len(bridge_cells) >= 3
        and all(isinstance(row, dict) and row.get("action_required") is False for row in bridge_cells[:3]),
        "runtime_bridge_endpoints_present": all(
            endpoint in (runtime_bridge.get("endpoints") or {})
            for endpoint in [
                "tour",
                "spine",
                "authority",
                "prediction",
                "corpus",
                "trace",
                "repair_loop",
                "evidence_cells",
                "proof_lab",
                "proof_loop_depth",
                "landing_replay",
                "view_quality",
                "projection_safety",
                "projection_drift",
                "projection_import_map",
                "import_projector",
                "option_surface",
                "stripping_guard",
                "standards_control",
                "hook_coverage",
                "replay_gauntlet",
                "benchmark_lab",
                "legibility_scorecard",
                "intake",
                "reveal",
                "evidence",
            ]
        ),
        "release_authorized": model.get("release_authorized") is True,
        "provider_calls_authorized": model.get("provider_calls_authorized") is True,
        "source_mutation_authorized": model.get("source_mutation_authorized") is True,
    }
    blocking_codes: list[str] = []
    for key, ok in html_assertions.items():
        if not ok:
            blocking_codes.append(f"OBSERVATORY_HTML_{key.upper()}_FAILED")
    for key, ok in model_assertions.items():
        if key in {"release_authorized", "provider_calls_authorized", "source_mutation_authorized"}:
            if ok:
                blocking_codes.append(f"OBSERVATORY_MODEL_{key.upper()}_FAILED")
            continue
        if not ok:
            blocking_codes.append(f"OBSERVATORY_MODEL_{key.upper()}_FAILED")

    state = project_path / ".microcosm"
    scan_paths_input = [
        path
        for path in [
            public_root / "README.md",
            public_root / "src/microcosm_core/runtime_shell.py",
            state / "graph.json",
            state / "work_items.json",
        ]
        if path.is_file()
    ]
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(scan_paths_input, forbidden_classes=policy, display_root=public_root)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan.get("blocking_hit_count"):
        blocking_codes.append("OBSERVATORY_PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "observatory_legibility_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_path.name,
        "selected_route_id": model.get("selected_route_id"),
        "html_sections_present": {
            "project_summary": "Project" in html,
            "causal_chain": "Causal Chain" in html,
            "ten_minute_tour": "Ten-Minute Tour" in html,
            "corpus_lens": "Corpus Readiness Lens" in html,
            "verifier_trace_lens": "Verifier Trace Repair Lens" in html,
            "verifier_repair_loop_lens": "Verifier Repair Loop Lens" in html,
            "formal_evidence_cell_lens": "Formal Evidence Cell Lens" in html,
            "proof_loop_depth_lens": "Proof Loop Depth Lens" in html,
            "work_landing_replay_lens": "Work Landing Replay Lens" in html,
            "view_quality_action_map_lens": "View Quality Action Map Lens" in html,
            "projection_safety_audit_lens": "Projection Safety Audit Lens" in html,
            "projection_drift_control_lens": "Projection Drift Control Lens" in html,
            "route_cleanup_contract_lens": "Route Cleanup Contract Lens" in html,
            "projection_import_map_lens": "Projection Import Map Lens" in html,
            "import_projector_contract_lens": "Import Projector Contract Lens" in html,
            "compression_profile_option_surface_lens": (
                "Compression Profile Option Surface Lens" in html
            ),
            "stripping_guard_lens": "Public/Private Stripping Guard Lens" in html,
            "standards_control_lens": "Standards Control Lens" in html,
            "hook_intervention_coverage_lens": "Hook Intervention Coverage Lens" in html,
            "agent_reliability_replay_gauntlet_lens": "Agent Reliability Replay Gauntlet"
            in html,
            "repository_benchmark_transaction_lab_lens": (
                "Repository Benchmark Transaction Lab" in html
            ),
            "cold_reader_legibility_scorecard_lens": (
                "Cold Reader Legibility Scorecard" in html
            ),
            "runtime_bridge": "Spine / Intake / Reveal Bridge" in html,
            "project_graph": "Project Graph" in html,
            "work_transaction": "Work Transaction" in html,
            "events_and_evidence": "Events and Evidence" in html,
            "kernel_and_standards": "Kernel and Standards" in html,
            "json_drilldowns": "JSON Drilldowns" in html,
        },
        "endpoint_summary": model.get("json_drilldowns", {}),
        "first_screen_landing_proof": {
            "status": first_screen_composition.get("status"),
            "html_endpoint": observatory_card.get("html_endpoint"),
            "first_screen_endpoint": observatory_card.get("first_screen_endpoint"),
            "observatory_card_endpoint": observatory_card.get("endpoint"),
            "human_first_command": first_screen_composition.get(
                "human_first_command"
            ),
            "shared_first_command": first_screen_composition.get(
                "shared_first_command"
            ),
            "browser_landing_reuse": browser_landing_reuse,
            "required_visible_handles": required_landing_handles,
            "evidence_class_ids": [
                row.get("evidence_class")
                for row in evidence_classes
                if isinstance(row, dict)
            ],
            "reader_route_ids": [
                row.get("reader_route_id")
                for row in first_screen_composition.get("reader_routes", [])
                if isinstance(first_screen_composition.get("reader_routes"), list)
                and isinstance(row, dict)
            ],
            "authority_boundary": landing_frame.get("authority_boundary"),
            "projection_rule": landing_frame.get("projection_rule"),
        },
        "causal_chain_proof": {
            "route_id": route.get("route_id"),
            "pattern_binding_ids": [
                row.get("pattern_id") for row in pattern_bindings if isinstance(row, dict)
            ],
            "standard_binding_ids": [
                row.get("standard_id") for row in standard_bindings if isinstance(row, dict)
            ],
            "work_id": work.get("work_id"),
            "state_history": [
                row.get("state")
                for row in work.get("state_history", [])
                if isinstance(row, dict)
            ]
            if isinstance(work.get("state_history"), list)
            else [],
            "event_count": len(events),
            "evidence_count": len(evidence),
        },
        "runtime_bridge_proof": {
            "bridge_id": runtime_bridge.get("bridge_id"),
            "projection_status_counts": runtime_bridge.get("projection_status_counts", {}),
            "open_actionable_cell_count": runtime_bridge.get("open_actionable_cell_count"),
            "closed_cell_count": runtime_bridge.get("closed_cell_count"),
            "endpoints": runtime_bridge.get("endpoints", {}),
            "cell_ids": [
                row.get("cell_id")
                for row in bridge_cells
                if isinstance(row, dict)
            ],
        },
        "tour_proof": {
            "tour_id": tour.get("tour_id"),
            "status": tour.get("status"),
            "time_budget_minutes": tour.get("time_budget_minutes"),
            "route_card_count": len(tour.get("route_cards", []))
            if isinstance(tour.get("route_cards"), list)
            else 0,
            "tour_ref": tour.get("tour_ref"),
        },
        "verifier_trace_proof": {
            "lens_id": trace_lens.get("lens_id"),
            "status": trace_lens.get("status"),
            "trace_attempt_count": len(trace_lens.get("trace_rows", []))
            if isinstance(trace_lens.get("trace_rows"), list)
            else 0,
            "negative_case_ids": trace_lens.get("negative_case_ids", []),
            "formal_proof_authority": (trace_lens.get("authority_ceiling") or {}).get(
                "formal_proof_authority"
            )
            if isinstance(trace_lens.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (trace_lens.get("authority_ceiling") or {}).get(
                "proof_bodies_exported"
            )
            if isinstance(trace_lens.get("authority_ceiling"), dict)
            else None,
        },
        "verifier_repair_loop_proof": {
            "lens_id": repair_loop_lens.get("lens_id"),
            "status": repair_loop_lens.get("status"),
            "stage_count": len(repair_loop_lens.get("loop_stages", []))
            if isinstance(repair_loop_lens.get("loop_stages"), list)
            else 0,
            "transition_count": len(repair_loop_lens.get("transition_rows", []))
            if isinstance(repair_loop_lens.get("transition_rows"), list)
            else 0,
            "negative_case_ids": repair_loop_lens.get("negative_case_ids", []),
            "formal_proof_authority": (repair_loop_lens.get("authority_ceiling") or {}).get(
                "formal_proof_authority"
            )
            if isinstance(repair_loop_lens.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (repair_loop_lens.get("authority_ceiling") or {}).get(
                "proof_bodies_exported"
            )
            if isinstance(repair_loop_lens.get("authority_ceiling"), dict)
            else None,
            "oracle_needed_premise_ids_exported": (
                repair_loop_lens.get("authority_ceiling") or {}
            ).get("oracle_needed_premise_ids_exported")
            if isinstance(repair_loop_lens.get("authority_ceiling"), dict)
            else None,
        },
        "formal_evidence_cell_proof": {
            "lens_id": evidence_cell_lens.get("lens_id"),
            "status": evidence_cell_lens.get("status"),
            "cell_count": len(evidence_cell_lens.get("evidence_cells", []))
            if isinstance(evidence_cell_lens.get("evidence_cells"), list)
            else 0,
            "negative_case_ids": evidence_cell_lens.get("negative_case_ids", []),
            "formal_proof_authority": (
                evidence_cell_lens.get("authority_ceiling") or {}
            ).get("formal_proof_authority")
            if isinstance(evidence_cell_lens.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (
                evidence_cell_lens.get("authority_ceiling") or {}
            ).get("proof_bodies_exported")
            if isinstance(evidence_cell_lens.get("authority_ceiling"), dict)
            else None,
            "private_source_refs_exported": (
                evidence_cell_lens.get("authority_ceiling") or {}
            ).get("private_source_refs_exported")
            if isinstance(evidence_cell_lens.get("authority_ceiling"), dict)
            else None,
        },
        "proof_loop_depth_proof": {
            "lens_id": proof_loop_depth_lens.get("lens_id"),
            "status": proof_loop_depth_lens.get("status"),
            "gate_count": (proof_loop_depth_lens.get("proof_loop_summary") or {}).get(
                "gate_count"
            )
            if isinstance(proof_loop_depth_lens.get("proof_loop_summary"), dict)
            else None,
            "negative_case_count": (
                proof_loop_depth_lens.get("proof_loop_summary") or {}
            ).get("negative_case_count")
            if isinstance(proof_loop_depth_lens.get("proof_loop_summary"), dict)
            else None,
            "formal_proof_authority": (
                proof_loop_depth_lens.get("authority_ceiling") or {}
            ).get("formal_proof_authority")
            if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict)
            else None,
            "proof_bodies_exported": (
                proof_loop_depth_lens.get("authority_ceiling") or {}
            ).get("proof_bodies_exported")
            if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict)
            else None,
            "oracle_needed_premise_ids_exported": (
                proof_loop_depth_lens.get("authority_ceiling") or {}
            ).get("oracle_needed_premise_ids_exported")
            if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict)
            else None,
            "benchmark_score_claim": (
                proof_loop_depth_lens.get("authority_ceiling") or {}
            ).get("benchmark_score_claim")
            if isinstance(proof_loop_depth_lens.get("authority_ceiling"), dict)
            else None,
        },
        "work_landing_replay_proof": {
            "lens_id": landing_replay_lens.get("lens_id"),
            "status": landing_replay_lens.get("status"),
            "lane_count": len(landing_replay_lens.get("lane_decision_table", []))
            if isinstance(landing_replay_lens.get("lane_decision_table"), list)
            else 0,
            "negative_case_ids": landing_replay_lens.get("negative_case_ids", []),
            "live_git_mutation_authorized": (
                landing_replay_lens.get("authority_ceiling") or {}
            ).get("live_git_mutation_authorized")
            if isinstance(landing_replay_lens.get("authority_ceiling"), dict)
            else None,
            "broad_checkpoint_authorized": (
                landing_replay_lens.get("authority_ceiling") or {}
            ).get("broad_checkpoint_authorized")
            if isinstance(landing_replay_lens.get("authority_ceiling"), dict)
            else None,
        },
        "view_quality_action_map_proof": {
            "lens_id": view_quality_lens.get("lens_id"),
            "status": view_quality_lens.get("status"),
            "action_row_count": len(view_quality_lens.get("action_rows", []))
            if isinstance(view_quality_lens.get("action_rows"), list)
            else 0,
            "hot_action_count": len(view_quality_lens.get("hot_action_rollup", []))
            if isinstance(view_quality_lens.get("hot_action_rollup"), list)
            else 0,
            "negative_case_ids": view_quality_lens.get("negative_case_ids", []),
            "private_screenshot_paths_exported": (
                view_quality_lens.get("authority_ceiling") or {}
            ).get("private_screenshot_paths_exported")
            if isinstance(view_quality_lens.get("authority_ceiling"), dict)
            else None,
            "live_browser_control_authorized": (
                view_quality_lens.get("authority_ceiling") or {}
            ).get("live_browser_control_authorized")
            if isinstance(view_quality_lens.get("authority_ceiling"), dict)
            else None,
        },
        "projection_safety_audit_proof": {
            "lens_id": projection_safety_lens.get("lens_id"),
            "status": projection_safety_lens.get("status"),
            "projection_row_count": len(projection_safety_lens.get("projection_rows", []))
            if isinstance(projection_safety_lens.get("projection_rows"), list)
            else 0,
            "negative_case_ids": projection_safety_lens.get("negative_case_ids", []),
            "omission_receipt_count": (
                projection_safety_lens.get("projection_summary") or {}
            ).get("omission_receipt_count")
            if isinstance(projection_safety_lens.get("projection_summary"), dict)
            else None,
            "private_body_export_count": (
                projection_safety_lens.get("projection_summary") or {}
            ).get("private_body_export_count")
            if isinstance(projection_safety_lens.get("projection_summary"), dict)
            else None,
        },
        "market_prediction_boundary_proof": {
            "lens_id": market_boundary_lens.get("lens_id"),
            "status": market_boundary_lens.get("status"),
            "row_count": (market_boundary_lens.get("boundary_summary") or {}).get("row_count")
            if isinstance(market_boundary_lens.get("boundary_summary"), dict)
            else None,
            "decision_boundary_count": (
                market_boundary_lens.get("boundary_summary") or {}
            ).get("decision_boundary_count")
            if isinstance(market_boundary_lens.get("boundary_summary"), dict)
            else None,
            "negative_case_ids": market_boundary_lens.get("negative_case_ids", []),
            "trading_advice_authorized": (
                market_boundary_lens.get("authority_ceiling") or {}
            ).get("trading_advice_authorized")
            if isinstance(market_boundary_lens.get("authority_ceiling"), dict)
            else None,
            "private_portfolio_exported": (
                market_boundary_lens.get("authority_ceiling") or {}
            ).get("private_portfolio_exported")
            if isinstance(market_boundary_lens.get("authority_ceiling"), dict)
            else None,
            "performance_guarantee_claim": (
                market_boundary_lens.get("authority_ceiling") or {}
            ).get("performance_guarantee_claim")
            if isinstance(market_boundary_lens.get("authority_ceiling"), dict)
            else None,
        },
        "projection_drift_control_proof": {
            "lens_id": projection_drift_lens.get("lens_id"),
            "status": projection_drift_lens.get("status"),
            "row_count": (projection_drift_lens.get("drift_summary") or {}).get("row_count")
            if isinstance(projection_drift_lens.get("drift_summary"), dict)
            else None,
            "source_ref_count": (projection_drift_lens.get("drift_summary") or {}).get(
                "source_ref_count"
            )
            if isinstance(projection_drift_lens.get("drift_summary"), dict)
            else None,
            "repair_route_count": (projection_drift_lens.get("drift_summary") or {}).get(
                "repair_route_count"
            )
            if isinstance(projection_drift_lens.get("drift_summary"), dict)
            else None,
            "negative_case_ids": projection_drift_lens.get("negative_case_ids", []),
            "source_authority_claim": (
                projection_drift_lens.get("authority_ceiling") or {}
            ).get("source_authority_claim")
            if isinstance(projection_drift_lens.get("authority_ceiling"), dict)
            else None,
            "live_route_repair_authorized": (
                projection_drift_lens.get("authority_ceiling") or {}
            ).get("live_route_repair_authorized")
            if isinstance(projection_drift_lens.get("authority_ceiling"), dict)
            else None,
        },
        "route_cleanup_contract_proof": {
            "lens_id": route_cleanup_lens.get("lens_id"),
            "status": route_cleanup_lens.get("status"),
            "row_count": (route_cleanup_lens.get("cleanup_summary") or {}).get("row_count")
            if isinstance(route_cleanup_lens.get("cleanup_summary"), dict)
            else None,
            "owner_route_count": (
                route_cleanup_lens.get("cleanup_summary") or {}
            ).get("owner_route_count")
            if isinstance(route_cleanup_lens.get("cleanup_summary"), dict)
            else None,
            "validation_ref_count": (
                route_cleanup_lens.get("cleanup_summary") or {}
            ).get("validation_ref_count")
            if isinstance(route_cleanup_lens.get("cleanup_summary"), dict)
            else None,
            "negative_case_ids": route_cleanup_lens.get("negative_case_ids", []),
            "route_deletion_authorized": (
                route_cleanup_lens.get("authority_ceiling") or {}
            ).get("route_deletion_authorized")
            if isinstance(route_cleanup_lens.get("authority_ceiling"), dict)
            else None,
            "generated_region_hand_edit_authorized": (
                route_cleanup_lens.get("authority_ceiling") or {}
            ).get("generated_region_hand_edit_authorized")
            if isinstance(route_cleanup_lens.get("authority_ceiling"), dict)
            else None,
        },
        "projection_import_map_proof": {
            "lens_id": projection_import_map_lens.get("lens_id"),
            "status": projection_import_map_lens.get("status"),
            "row_count": (projection_import_map_lens.get("map_summary") or {}).get(
                "row_count"
            )
            if isinstance(projection_import_map_lens.get("map_summary"), dict)
            else None,
            "stage_count": (projection_import_map_lens.get("map_summary") or {}).get(
                "stage_count"
            )
            if isinstance(projection_import_map_lens.get("map_summary"), dict)
            else None,
            "validation_ref_count": (
                projection_import_map_lens.get("map_summary") or {}
            ).get("validation_ref_count")
            if isinstance(projection_import_map_lens.get("map_summary"), dict)
            else None,
            "negative_case_ids": projection_import_map_lens.get("negative_case_ids", []),
            "private_body_export_count": (
                projection_import_map_lens.get("map_summary") or {}
            ).get("private_body_export_count")
            if isinstance(projection_import_map_lens.get("map_summary"), dict)
            else None,
            "automated_import_guarantee": (
                projection_import_map_lens.get("authority_ceiling") or {}
            ).get("automated_import_guarantee")
            if isinstance(projection_import_map_lens.get("authority_ceiling"), dict)
            else None,
        },
        "import_projector_contract_proof": {
            "lens_id": import_projector_lens.get("lens_id"),
            "status": import_projector_lens.get("status"),
            "row_count": (import_projector_lens.get("projector_summary") or {}).get(
                "row_count"
            )
            if isinstance(import_projector_lens.get("projector_summary"), dict)
            else None,
            "stage_count": (import_projector_lens.get("projector_summary") or {}).get(
                "stage_count"
            )
            if isinstance(import_projector_lens.get("projector_summary"), dict)
            else None,
            "validation_ref_count": (
                import_projector_lens.get("projector_summary") or {}
            ).get("validation_ref_count")
            if isinstance(import_projector_lens.get("projector_summary"), dict)
            else None,
            "negative_case_ids": import_projector_lens.get("negative_case_ids", []),
            "private_body_export_count": (
                import_projector_lens.get("projector_summary") or {}
            ).get("private_body_export_count")
            if isinstance(import_projector_lens.get("projector_summary"), dict)
            else None,
            "generated_region_hand_edit_authorized": (
                import_projector_lens.get("authority_ceiling") or {}
            ).get("generated_region_hand_edit_authorized")
            if isinstance(import_projector_lens.get("authority_ceiling"), dict)
            else None,
            "automated_import_execution_authorized": (
                import_projector_lens.get("authority_ceiling") or {}
            ).get("automated_import_execution_authorized")
            if isinstance(import_projector_lens.get("authority_ceiling"), dict)
            else None,
            "lossless_projection_claim": (
                import_projector_lens.get("authority_ceiling") or {}
            ).get("lossless_projection_claim")
            if isinstance(import_projector_lens.get("authority_ceiling"), dict)
            else None,
        },
        "compression_profile_option_surface_proof": {
            "lens_id": option_surface_lens.get("lens_id"),
            "status": option_surface_lens.get("status"),
            "row_count": (option_surface_lens.get("option_surface_summary") or {}).get(
                "row_count"
            )
            if isinstance(option_surface_lens.get("option_surface_summary"), dict)
            else None,
            "stage_count": (option_surface_lens.get("option_surface_summary") or {}).get(
                "stage_count"
            )
            if isinstance(option_surface_lens.get("option_surface_summary"), dict)
            else None,
            "validation_ref_count": (
                option_surface_lens.get("option_surface_summary") or {}
            ).get("validation_ref_count")
            if isinstance(option_surface_lens.get("option_surface_summary"), dict)
            else None,
            "negative_case_ids": option_surface_lens.get("negative_case_ids", []),
            "private_body_export_count": (
                option_surface_lens.get("option_surface_summary") or {}
            ).get("private_body_export_count")
            if isinstance(option_surface_lens.get("option_surface_summary"), dict)
            else None,
            "profile_switch_execution_authorized": (
                option_surface_lens.get("authority_ceiling") or {}
            ).get("profile_switch_execution_authorized")
            if isinstance(option_surface_lens.get("authority_ceiling"), dict)
            else None,
            "automatic_profile_selection_authorized": (
                option_surface_lens.get("authority_ceiling") or {}
            ).get("automatic_profile_selection_authorized")
            if isinstance(option_surface_lens.get("authority_ceiling"), dict)
            else None,
            "lossless_projection_claim": (
                option_surface_lens.get("authority_ceiling") or {}
            ).get("lossless_projection_claim")
            if isinstance(option_surface_lens.get("authority_ceiling"), dict)
            else None,
        },
        "stripping_guard_proof": {
            "lens_id": stripping_guard_lens.get("lens_id"),
            "status": stripping_guard_lens.get("status"),
            "guard_row_count": (stripping_guard_lens.get("guard_summary") or {}).get(
                "guard_row_count"
            )
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "negative_case_count": (stripping_guard_lens.get("guard_summary") or {}).get(
                "negative_case_count"
            )
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "private_body_export_count": (
                stripping_guard_lens.get("guard_summary") or {}
            ).get("private_body_export_count")
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "proof_body_export_count": (
                stripping_guard_lens.get("guard_summary") or {}
            ).get("proof_body_export_count")
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "provider_payload_export_count": (
                stripping_guard_lens.get("guard_summary") or {}
            ).get("provider_payload_export_count")
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "raw_private_path_export_count": (
                stripping_guard_lens.get("guard_summary") or {}
            ).get("raw_private_path_export_count")
            if isinstance(stripping_guard_lens.get("guard_summary"), dict)
            else None,
            "secret_detection_completeness_claim": (
                stripping_guard_lens.get("authority_ceiling") or {}
            ).get("secret_detection_completeness_claim")
            if isinstance(stripping_guard_lens.get("authority_ceiling"), dict)
            else None,
        },
        "standards_control_proof": {
            "lens_id": standards_control_lens.get("lens_id"),
            "status": standards_control_lens.get("status"),
            "row_count": (standards_control_lens.get("standards_summary") or {}).get(
                "standards_control_row_count"
            )
            if isinstance(standards_control_lens.get("standards_summary"), dict)
            else None,
            "negative_case_count": (
                standards_control_lens.get("standards_summary") or {}
            ).get("negative_case_count")
            if isinstance(standards_control_lens.get("standards_summary"), dict)
            else None,
            "standard_count": (standards_control_lens.get("standards_summary") or {}).get(
                "standard_count"
            )
            if isinstance(standards_control_lens.get("standards_summary"), dict)
            else None,
            "validator_receipt_ref_count": (
                standards_control_lens.get("standards_summary") or {}
            ).get("validator_receipt_ref_count")
            if isinstance(standards_control_lens.get("standards_summary"), dict)
            else None,
            "source_authority_claim_count": (
                standards_control_lens.get("standards_summary") or {}
            ).get("source_authority_claim_count")
            if isinstance(standards_control_lens.get("standards_summary"), dict)
            else None,
            "standards_registry_source_authority": (
                standards_control_lens.get("authority_ceiling") or {}
            ).get("standards_registry_source_authority")
            if isinstance(standards_control_lens.get("authority_ceiling"), dict)
            else None,
            "standards_completeness_claim": (
                standards_control_lens.get("authority_ceiling") or {}
            ).get("standards_completeness_claim")
            if isinstance(standards_control_lens.get("authority_ceiling"), dict)
            else None,
            "release_authorized": (
                standards_control_lens.get("authority_ceiling") or {}
            ).get("release_authorized")
            if isinstance(standards_control_lens.get("authority_ceiling"), dict)
            else None,
        },
        "hook_intervention_coverage_proof": {
            "lens_id": hook_coverage_lens.get("lens_id"),
            "status": hook_coverage_lens.get("status"),
            "intervention_row_count": len(hook_coverage_lens.get("intervention_rows", []))
            if isinstance(hook_coverage_lens.get("intervention_rows"), list)
            else 0,
            "negative_case_ids": hook_coverage_lens.get("negative_case_ids", []),
            "missing_authority_count": len(
                hook_coverage_lens.get("missing_authority_case_ids", [])
            )
            if isinstance(hook_coverage_lens.get("missing_authority_case_ids"), list)
            else 0,
            "live_operator_state_read": (
                hook_coverage_lens.get("authority_ceiling") or {}
            ).get("live_operator_state_read")
            if isinstance(hook_coverage_lens.get("authority_ceiling"), dict)
            else None,
            "provider_payload_read": (
                hook_coverage_lens.get("authority_ceiling") or {}
            ).get("provider_payload_read")
            if isinstance(hook_coverage_lens.get("authority_ceiling"), dict)
            else None,
        },
        "agent_reliability_replay_gauntlet_proof": {
            "lens_id": replay_gauntlet_lens.get("lens_id"),
            "status": replay_gauntlet_lens.get("status"),
            "episode_count": len(replay_gauntlet_lens.get("episode_rows", []))
            if isinstance(replay_gauntlet_lens.get("episode_rows"), list)
            else 0,
            "negative_case_ids": replay_gauntlet_lens.get("negative_case_ids", []),
            "blocked_episode_count": (
                replay_gauntlet_lens.get("coverage_summary") or {}
            ).get("blocked_episode_count")
            if isinstance(replay_gauntlet_lens.get("coverage_summary"), dict)
            else None,
            "quarantined_episode_count": (
                replay_gauntlet_lens.get("coverage_summary") or {}
            ).get("quarantined_episode_count")
            if isinstance(replay_gauntlet_lens.get("coverage_summary"), dict)
            else None,
            "live_agent_execution_authorized": (
                replay_gauntlet_lens.get("authority_ceiling") or {}
            ).get("live_agent_execution_authorized")
            if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict)
            else None,
            "real_secret_material_exported": (
                replay_gauntlet_lens.get("authority_ceiling") or {}
            ).get("real_secret_material_exported")
            if isinstance(replay_gauntlet_lens.get("authority_ceiling"), dict)
            else None,
        },
        "repository_benchmark_transaction_lab_proof": {
            "lens_id": benchmark_lab_lens.get("lens_id"),
            "status": benchmark_lab_lens.get("status"),
            "task_count": (benchmark_lab_lens.get("scorecard") or {}).get("task_count")
            if isinstance(benchmark_lab_lens.get("scorecard"), dict)
            else None,
            "oracle_patch_count": (
                benchmark_lab_lens.get("scorecard") or {}
            ).get("oracle_patch_count")
            if isinstance(benchmark_lab_lens.get("scorecard"), dict)
            else None,
            "fail_to_pass_count": (
                benchmark_lab_lens.get("scorecard") or {}
            ).get("fail_to_pass_count")
            if isinstance(benchmark_lab_lens.get("scorecard"), dict)
            else None,
            "pass_to_pass_count": (
                benchmark_lab_lens.get("scorecard") or {}
            ).get("pass_to_pass_count")
            if isinstance(benchmark_lab_lens.get("scorecard"), dict)
            else None,
            "negative_case_ids": benchmark_lab_lens.get("negative_case_ids", []),
            "live_repo_mutation_authorized": (
                benchmark_lab_lens.get("authority_ceiling") or {}
            ).get("live_repo_mutation_authorized")
            if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict)
            else None,
            "swe_bench_performance_claim": (
                benchmark_lab_lens.get("authority_ceiling") or {}
            ).get("swe_bench_performance_claim")
            if isinstance(benchmark_lab_lens.get("authority_ceiling"), dict)
            else None,
        },
        "cold_reader_legibility_scorecard_proof": {
            "lens_id": legibility_scorecard_lens.get("lens_id"),
            "status": legibility_scorecard_lens.get("status"),
            "checkpoint_count": (
                legibility_scorecard_lens.get("scorecard") or {}
            ).get("checkpoint_count")
            if isinstance(legibility_scorecard_lens.get("scorecard"), dict)
            else None,
            "reader_question_count": (
                legibility_scorecard_lens.get("scorecard") or {}
            ).get("reader_question_count")
            if isinstance(legibility_scorecard_lens.get("scorecard"), dict)
            else None,
            "time_budget_minutes": (
                legibility_scorecard_lens.get("scorecard") or {}
            ).get("time_budget_minutes")
            if isinstance(legibility_scorecard_lens.get("scorecard"), dict)
            else None,
            "negative_case_ids": legibility_scorecard_lens.get("negative_case_ids", []),
            "release_authorized": (
                legibility_scorecard_lens.get("authority_ceiling") or {}
            ).get("release_authorized")
            if isinstance(legibility_scorecard_lens.get("authority_ceiling"), dict)
            else None,
            "reader_success_guarantee": (
                legibility_scorecard_lens.get("authority_ceiling") or {}
            ).get("reader_success_guarantee")
            if isinstance(legibility_scorecard_lens.get("authority_ceiling"), dict)
            else None,
        },
        "html_assertions": html_assertions,
        "model_assertions": model_assertions,
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
        "anti_claim": "Observatory legibility validates the local browser/read model over public project state. It does not authorize hosted release operations, credentialed provider calls, unsafe source mutation, secret export, live Task Ledger mutation, or production deployment.",
        "receipt_paths": [_public_relative(public_root, output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Microcosm observatory legibility")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.observatory_legibility "
        f"--root {args.root} --project {Path(args.project).name} --out {args.out}"
    )
    receipt = validate_legibility(args.root, args.project, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
