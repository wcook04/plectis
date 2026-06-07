from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from microcosm_core.projections.agent_entry_composition import (
    MACRO_IMPORT_ROUTE_ORGANS,
    ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
    ORGAN_DISCOVERABILITY_MATRIX_REF,
    ORGAN_GLANCE_REF,
    PROJECTION_AUTHORITY_POSTURE,
    SELECT_VIEWER_COMMAND,
    SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND,
    build_agent_entry_composition,
    compact_agent_entry_card,
    compile_paths,
    validate_agent_entry_composition,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _build() -> dict:
    return build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="Microcosm agent entry composition projection",
        command="pytest",
    )


def test_agent_entry_card_composes_type_a_route_task_route_and_macro_floor() -> None:
    payload = _build()

    assert payload["status"] == "pass"
    assert payload["authority_posture"] == PROJECTION_AUTHORITY_POSTURE
    assert payload["release_authority"] is False
    assert payload["source_mutation_authority"] is False
    assert payload["provider_call_authority"] is False
    assert payload["private_root_equivalence_authority"] is False
    assert payload["selected_viewer"] == "all"
    assert payload["selected_viewer_entry"]["viewer"] == "all"
    assert payload["selected_viewer_route"]["route_kind"] == "viewer_route_set"
    assert set(payload["selected_viewer_route"]["routes"]) == {"type_a_agent", "human"}
    assert payload["selected_viewer_route"]["selection_command"] == SELECT_VIEWER_COMMAND
    assert payload["selected_viewer_route"]["source_checkout_selection_command"] == (
        SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND
    )
    assert payload["selected_viewer_route"]["routes"]["type_a_agent"][
        "source_checkout_first_safe_action"
    ] == "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
    assert payload["selected_viewer_route"]["routes"]["type_a_agent"][
        "source_checkout_next_action"
    ] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root ."
    )

    first_screen = payload["first_screen_type_a_route"]
    assert first_screen["reader_id"] == "type_a_agent"
    assert first_screen["route_command"] == "microcosm first-screen --card <project>"
    assert "source-mutation" in first_screen["anti_overread"]
    assert "reader_first_screen_routes" in first_screen["source_ref"]

    task_route = payload["task_route"]
    assert task_route["task_class"] == "agent-entry"
    assert task_route["primary_organ_id"] == "cold_reader_route_map"
    assert task_route["first_command"].startswith("microcosm cold-reader-route-map ")
    assert task_route["evidence_ref"].endswith("[organ_id=cold_reader_route_map]")
    assert task_route["relevant_organs"]
    assert all(row["command_runnable_shape"] for row in task_route["relevant_organs"])

    macro_by_id = {row["organ_id"]: row for row in payload["macro_import_route_body_floor"]}
    assert set(MACRO_IMPORT_ROUTE_ORGANS) <= set(macro_by_id)
    for organ_id in MACRO_IMPORT_ROUTE_ORGANS:
        row = macro_by_id[organ_id]
        assert row["command_runnable_shape"] is True
        assert row["evidence_refs"]["current_authority_receipt"]
        assert row["evidence_refs"]["receipt_refs"]
        assert row["standards"]["standard_ref"].endswith(f"{organ_id}.json")
        assert row["standards"]["mechanism_ref"] == (
            f"organ_doctrine_row:{organ_id}.mechanism_binding"
        )

    assert payload["read_run_order"][0]["kind"] == "selected_viewer_route"
    assert payload["read_run_order"][0]["run"] == {
        "type_a_agent": "microcosm first-screen --card <project>",
        "human": "microcosm hello <project>",
    }
    assert payload["read_run_order"][1]["run"] == first_screen["route_command"]
    assert payload["read_run_order"][1]["source_checkout_run"] == (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
    )
    assert payload["read_run_order"][2]["run"] == task_route["first_command"]
    assert payload["read_run_order"][2]["source_checkout_run"] == (
        task_route["source_checkout_first_command"]
    )
    organ_glance = payload["accepted_organ_glance"]
    assert organ_glance["source_ref"] == ORGAN_GLANCE_REF
    assert organ_glance["first_family_label"] == "Entry & Reveal"
    assert organ_glance["family_count"] == 7
    assert organ_glance["organ_count"] == 82
    assert organ_glance["capsule_accounting"]["accepted_organ_count"] == 82
    assert organ_glance["capsule_join_status_counts"] == {
        "direct": 75,
        "paper_module_ref_bridge": 7,
    }
    assert sum(len(family["organs"]) for family in organ_glance["families"]) == 82
    cold_reader = organ_glance["families"][0]["organs"][0]
    assert cold_reader["organ_id"] == "cold_reader_route_map"
    assert cold_reader["one_line"]
    assert cold_reader["card"]
    assert cold_reader["authority_ceiling"]
    assert cold_reader["claim_ceiling_restated"] == cold_reader["authority_ceiling"]
    assert cold_reader["first_command"].startswith("microcosm cold-reader-route-map ")
    assert cold_reader["paper_module_ref"].endswith("cold_reader_route_map.md")
    assert cold_reader["capsule_id"] == "paper_module.cold_reader_route_map"
    assert cold_reader["capsule_join_status"] == "direct"
    assert cold_reader["card_ref"] == "ORGANS.md#cold-reader-route-map"
    assert cold_reader["drilldown_target"] == "ORGANS.md#cold-reader-route-map"
    assert payload["read_run_order"][3]["kind"] == "accepted_organ_glance"
    assert payload["read_run_order"][3]["read"] == [
        ORGAN_GLANCE_REF,
        "ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line",
    ]
    discoverability_route = payload["organ_discoverability_matrix_route"]
    assert discoverability_route["run"] == ORGAN_DISCOVERABILITY_MATRIX_COMMAND
    assert ORGAN_DISCOVERABILITY_MATRIX_REF in discoverability_route["read"]
    assert payload["read_run_order"][4]["kind"] == "organ_discoverability_matrix"
    assert payload["read_run_order"][4]["run"] == ORGAN_DISCOVERABILITY_MATRIX_COMMAND
    assert payload["read_run_order"][4]["source_checkout_run"] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "organ-discoverability-matrix --root . --check"
    )
    assert payload["read_run_order"][5]["kind"] == "macro_body_floor"
    assert payload["read_run_order"][5]["source_checkout_run"][0] == (
        task_route["source_checkout_first_command"]
    )
    card = compact_agent_entry_card(payload)
    assert card["read_run_order"][1]["source_checkout_run"] == (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
    )
    assert "why" not in card["read_run_order"][1]
    assert "re-entry" in payload["omission_receipt"]["reentry_condition"].lower()


def test_agent_entry_card_dogfoods_type_a_and_human_viewer_routes() -> None:
    payload = _build()

    viewer_modes = {row["viewer"]: row for row in payload["viewer_modes"]}
    assert set(viewer_modes) == {"type_a_agent", "human"}
    router = payload["viewer_first_action_router"]
    assert router["schema"] == "microcosm_viewer_first_action_router_v0"
    assert set(router["viewer_families"]) == {"type_a_agent", "human"}
    assert router["select_viewer_command"] == SELECT_VIEWER_COMMAND
    assert router["source_checkout_select_viewer_command"] == (
        SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND
    )
    assert "no-install invocation hint" in router["source_checkout_boundary"]
    assert "release" in router["source_checkout_boundary"]
    assert router["routes"]["type_a_agent"]["first_safe_action"] == (
        "microcosm first-screen --card <project>"
    )
    assert router["routes"]["type_a_agent"]["source_checkout_first_safe_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
    )
    assert router["routes"]["type_a_agent"]["source_checkout_next_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root ."
    )
    assert router["routes"]["human"]["first_safe_action"] == "microcosm hello <project>"
    assert router["routes"]["human"]["source_checkout_first_safe_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core hello <project>"
    )

    type_a = viewer_modes["type_a_agent"]
    assert type_a["first_safe_action"] == "microcosm first-screen --card <project>"
    assert type_a["next_action"] == "microcosm organ-surface-contract --card --root ."
    assert type_a["source_checkout_first_safe_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
    )
    assert type_a["source_checkout_next_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core "
        "organ-surface-contract --card --root ."
    )
    assert "source mutation" in type_a["authority_boundary"]
    assert type_a["evidence_refs"]
    assert "re-entry" in type_a["reentry_condition"].lower()
    assert "not" in type_a["anti_overread_warning"].lower()

    human = viewer_modes["human"]
    assert human["first_safe_action"] == "microcosm hello <project>"
    assert human["source_checkout_first_safe_action"] == (
        "PYTHONPATH=src python3 -m microcosm_core hello <project>"
    )
    assert human["next_action"] == "microcosm tour --card <project>"
    assert "interpretive/read authority" in human["authority_boundary"]
    assert "README.md::Public Repo Map" in human["drilldown_if_needed"]
    assert human["evidence_refs"]

    checks = {row["viewer"]: row for row in payload["entry_experience_checks"]}
    assert set(checks) == {"type_a_agent", "human"}
    for check in checks.values():
        assert check["status"] == "pass"
        assert check["route_scent"] == "strong"
        assert check["first_action_visible"] is True
        assert check["authority_boundary_visible"] is True
        assert check["evidence_ref_visible"] is True
        assert check["stop_condition_visible"] is True
        assert check["reentry_condition_visible"] is True
        assert check["anti_overread_warning_visible"] is True
        assert check["failure_codes"] == []


def test_agent_entry_card_keeps_human_viewer_first_when_selected() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="agent-entry",
        viewer="human",
        command="pytest",
    )

    assert payload["status"] == "pass"
    assert payload["selected_viewer"] == "human"
    assert payload["selected_viewer_entry"]["viewer"] == "human"
    assert payload["selected_viewer_route"]["viewer"] == "human"
    assert payload["read_run_order"][0]["kind"] == "selected_viewer_route"
    assert payload["read_run_order"][0]["run"] == "microcosm hello <project>"
    assert payload["read_run_order"][1]["kind"] == "optional_drilldown_after_human_first_action"
    assert {
        row["kind"] for row in payload["read_run_order"][:2]
    } == {
        "selected_viewer_route",
        "optional_drilldown_after_human_first_action",
    }


def test_agent_entry_card_rejects_missing_human_viewer_route() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["viewer_modes"] = [
        row for row in bad_payload["viewer_modes"] if row["viewer"] != "human"
    ]
    bad_payload["entry_experience_checks"] = [
        row for row in bad_payload["entry_experience_checks"] if row["viewer"] != "human"
    ]

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert "missing_viewer_mode" in {error["code"] for error in result["errors"]}
    assert "viewer_entry_experience_check_not_passed" in {
        error["code"] for error in result["errors"]
    }


def test_agent_entry_card_rejects_weak_viewer_route_scent() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["viewer_modes"][0]["branch_label"] = "reader"
    bad_payload["entry_experience_checks"] = [
        row
        for row in bad_payload["entry_experience_checks"]
        if row["viewer"] != "type_a_agent"
    ]

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert "viewer_entry_experience_blocked" in {
        error["code"] for error in result["errors"]
    }
    assert "viewer_entry_experience_check_not_passed" in {
        error["code"] for error in result["errors"]
    }


def test_agent_entry_card_rejects_undereferenced_macro_body_floor() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["macro_import_route_body_floor"] = [
        row
        for row in bad_payload["macro_import_route_body_floor"]
        if row["organ_id"] != "standards_meta_diagnostics"
    ]

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert "missing_macro_import_route_body" in {error["code"] for error in result["errors"]}


def test_agent_entry_card_rejects_non_runnable_task_command() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["task_route"]["first_command"] = "see AGENT_ROUTES.md"

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert "task_route_command_not_runnable_shape" in {
        error["code"] for error in result["errors"]
    }


def test_agent_entry_card_allows_selected_public_task_route() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="ai-safety",
        viewer="human",
        command="pytest",
    )

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == "ai-safety"
    assert payload["task_route"]["selected_task_class"] == "ai-safety"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "ai-safety"
    assert payload["task_route"]["primary_organ_id"] == (
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert (
        payload["selected_viewer_route"]["stop_condition"]
        == "You can name the selected task route, primary organ, evidence class, first command, and authority ceiling without claiming domain correctness."
    )
    assert payload["read_run_order"][1]["kind"] == (
        "selected_task_route_after_human_entry"
    )
    assert payload["read_run_order"][1]["run"] == payload["task_route"]["first_command"]
    assert payload["task_route"]["source_ref"] in payload["read_run_order"][1]["read"]
    assert payload["validation"]["errors"] == []


@pytest.mark.parametrize(
    "task",
    [
        "reviewer",
        "skeptical review",
        "skeptical-review",
        "skeptical reviewer",
        "show safety",
        "show me safety",
        "safety parts",
        "AI safety evals",
        "AI safety parts",
        "show me safety evals",
        "agent safety",
        "security evals",
        "show me agent safety",
        "where is AI safety",
        "alignment evaluation",
        "safety evals",
        "model safety",
        "show me AI safety",
        "show me the AI safety",
        "show me the AI safety parts",
        "what are the AI safety parts",
        "show me AI-safety stuff",
        "show me alignment parts",
        "show me machine learning parts",
        "show me ML",
        "show me AI parts",
    ],
)
def test_agent_entry_card_aliases_safety_questions_to_safety_route(task: str) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["selected_task_class"] == "ai-safety"
    assert payload["task_route"]["task_class"] == "ai-safety"
    assert card["task_route"]["selected_task_class"] == "ai-safety"
    assert "agent-entry-composition --task ai-safety" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "show me benchmarks",
        "show me evals",
        "benchmark integrity",
        "show me benchmark integrity",
        "eval harness",
        "how do I evaluate agents",
        "SWE-bench",
        "agent evals",
        "agent evaluation",
    ],
)
def test_agent_entry_card_aliases_benchmark_questions_to_agent_evaluation_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "agent-evaluation"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "agent-evaluation"
    assert payload["task_route"]["primary_organ_id"] == (
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    assert card["task_route"]["selected_task_class"] == "agent-evaluation"
    assert (
        "agent-entry-composition --task agent-evaluation"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "scheming",
        "sabotage",
        "monitoring",
        "agent monitoring",
        "red team evals",
        "scheming monitor",
        "sabotage monitor",
    ],
)
def test_agent_entry_card_aliases_red_teaming_questions_to_red_teaming_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "red-teaming"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "red-teaming"
    assert payload["task_route"]["primary_organ_id"] == (
        "agent_benchmark_integrity_anti_gaming_replay"
    )
    assert card["task_route"]["selected_task_class"] == "red-teaming"
    assert (
        "agent-entry-composition --task red-teaming"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "what is this",
        "what is this?",
        "what is this repo",
        "what is this repository",
        "what is this project",
        "what is Microcosm",
        "what does this do",
        "what does Microcosm do",
        "what am I looking at",
        "overview",
        "project overview",
        "repo reading agent",
        "repo-reading agent",
        "type a agent",
        "agent path",
        "where do I patch this",
        "where do I patch a route",
        "where do I patch the route",
        "what owns this route",
        "who owns this route",
        "route owner",
        "owner surface",
        "owner surface to patch",
        "which file owns routes",
        "which file owns route selection",
        "where is route selection",
        "route selection owner",
        "route selection code",
        "agent entry owner",
        "agent-entry owner",
        "agent entry composition",
        "agent entry composition owner",
        "where is agent entry composition",
        "first screen owner",
        "first-screen owner",
        "first screen composition",
        "card owner",
        "which file owns cards",
        "where do I patch cards",
        "projection boundary",
        "validator boundary",
        "mechanism boundary",
        "mechanism validator projection boundary",
        "organ surface contract",
        "route misleads",
        "route is wrong",
        "agent route is wrong",
        "route card is wrong",
        "why does this exist",
        "what is the point",
        "local project substrate",
        "what can I ask",
    ],
)
def test_agent_entry_card_aliases_identity_questions_to_agent_entry_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "agent-entry"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "agent-entry"
    assert payload["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert card["task_route"]["selected_task_class"] == "agent-entry"
    assert "agent-entry-composition --task agent-entry" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "what commands exist",
        "show me commands",
        "command list",
        "list commands",
        "available commands",
        "help",
        "CLI",
        "CLI commands",
        "show me CLI help",
        "CLI help",
        "command surface",
        "CLI surface",
        "getting started",
        "get started",
        "quickstart",
        "quick start",
        "cold clone",
        "cold clone path",
        "clone and run",
        "first command",
        "first run",
        "first thing to run",
        "what do I run first",
        "what command first",
        "start from source",
        "dry run bootstrap",
        "bootstrap dry-run",
        "bootstrap first",
        "bootstrap",
        "bootstrap script",
        "bootstrap.sh",
        "run bootstrap",
        "safe first command",
        "safe probe",
        "no-write first",
        "does this write files",
        "what files does it write",
        "bootstrap probe",
        "bounded probe",
        "bounded cold clone probe",
        "cold clone check",
        "cold clone probe",
        "cold clone receipt",
        "ignored receipts",
        "where did bootstrap write",
        ".microcosm cold clone probe",
        "before installing",
        "before install",
        "install this",
        "setup",
        "setup this repo",
        "set up this repo",
        "how do I set this up",
        "dependency",
        "dependencies",
        "what dependencies",
        "what dependencies do I need",
        "python version",
        "what python version",
        "requires python",
        "python requirements",
        "how do I install it",
        "pip install",
        "pip install editable",
        "editable install",
        "install test extras",
        "make install",
        "venv",
        "virtualenv",
        "create venv",
        "where is venv",
        "make smoke first",
        "run smoke first",
        "smoke path first",
        "quickstart path",
        "one page path",
        "one-page path",
        "install from source",
        "try it",
        "try this",
        "how do I try it",
        "how do I try this",
        "can I try it",
        "how do I run it",
        "run without installing",
        "run source form",
        "source checkout",
        "source-only checkout",
        "without install",
        "source-only install",
        "dev setup",
        "developer setup",
        "package smoke",
        "fresh venv",
        "fresh-venv package check",
        "installed console proof",
        "source only",
        "no install",
        "can't install",
        "cannot install",
        "console command missing",
        "microcosm command not found",
        "command not found",
        "does this run",
        "does it work",
        "is it runnable",
        "is this runnable",
        "can I run this",
        "can I run it",
        "make package-smoke",
        "run the checks",
    ],
)
def test_agent_entry_card_aliases_command_help_questions_to_getting_started_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "getting-started"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "getting-started"
    assert payload["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "getting-started"
    assert (
        "agent-entry-composition --task getting-started"
        in card["drilldowns"]["full_json"]
    )


def test_agent_entry_card_keeps_run_the_checks_alias_traceable() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="run the checks",
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == "run the checks"
    assert payload["task_route"]["selected_task_class"] == "getting-started"
    assert payload["task_route"]["alias_resolution"]["status"] == "alias_resolved"
    assert (
        "cold-clone verification floor"
        in payload["task_route"]["alias_resolution"]["reason"]
    )
    assert card["task_route"]["alias_resolution"] == payload["task_route"][
        "alias_resolution"
    ]
    assert (
        "agent-entry-composition --task getting-started"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "show me architecture",
        "show me the architecture",
        "what is the architecture",
        "where is the architecture",
        "how is this built",
        "how is this organized",
        "show me specs",
        "where are the specs",
        "which files are generated",
        "generated maps",
        "generated surfaces",
        "generated atlas",
        "what is generated here",
        "what files can I edit",
        "is AGENT_ROUTES generated",
        "is ORGANS generated",
        "what owns generated docs",
        "generated docs owner",
        "generated atlas owner",
        "can I edit generated docs",
        "generated files",
        "do not hand edit",
        "owner data",
        "builder",
        "who owns AGENT_ROUTES",
        "who owns ORGANS",
        "who owns ARCHITECTURE",
        "generated docs drift",
        "atlas drift",
        "verify generated maps",
        "check generated maps",
        "regenerate routes",
        "regenerate maps",
        "build generated docs",
        "build organ atlas",
        "organ atlas builder",
        "run build_organ_atlas",
        "source of generated route table",
        "projection owner",
        "projection refresh",
        "refresh AGENT_ROUTES",
        "refresh ORGANS",
        "refresh ARCHITECTURE",
        "how do I refresh AGENT_ROUTES",
        "do not hand edit generated docs",
    ],
)
def test_agent_entry_card_aliases_architecture_questions_to_architecture_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "architecture"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "architecture"
    assert payload["task_route"]["primary_organ_id"] == "pattern_binding_contract"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "architecture"
    assert "agent-entry-composition --task architecture" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "source authority",
        "where is source authority",
        "what is source authority",
        "show me source authority",
        "where is the code",
        "where is the CLI",
        "where are commands defined",
        "source commands",
        "module entrypoint",
        "python module",
        "console script",
        "console entrypoint",
        "entry point",
        "entry points",
        "how is the CLI wired",
        "show me the code",
        "show me the source",
        "source code",
        "source files",
        "implementation",
        "where is implementation",
        "where is the implementation",
        "runtime package",
        "package metadata",
        "pyproject",
        "makefile",
        "test files",
        "where are scripts",
        "script list",
        "scripts",
        "command implementation",
        "authority boundary",
        "authority boundaries",
        "what are the authority boundaries",
        "what is not allowed",
        "what is not authorized",
        "what does this not prove",
        "what does this not authorize",
        "can I publish this",
        "can I share this",
        "standalone export",
        "export artifact",
        "release export",
        "release ready",
        "is this release ready",
        "is release authorized",
        "release authorized",
        "is publication authorized",
        "publication authorized",
        "production ready",
        "can I deploy this",
        "deploy this",
        "can this be hosted",
        "hosted service",
        "host this",
        "is this a hosted service",
        "does this call providers",
        "provider calls",
        "does this use credentials",
        "credential boundary",
        "secret boundary",
        "private data",
        "private root equivalence",
        "does this prove the system",
        "whole system correctness",
        "benchmark score",
        "does this prove agent capability",
        "source mutation",
        "source mutation ceiling",
        "what can I mutate",
        "source mutation check",
        "source files mutated",
        "mutation check",
        "does this mutate source",
        "does Microcosm mutate source",
        "will this mutate source",
        "does this change source files",
    ],
)
def test_agent_entry_card_aliases_source_authority_to_authority_boundary_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "authority-boundary"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "authority-boundary"
    assert payload["task_route"]["primary_organ_id"] == "batch5_authority_systems_capsule"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "authority-boundary"
    assert (
        "agent-entry-composition --task authority-boundary"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "show me navigation",
        "show me the navigation",
        "show me routes",
        "show me the routes",
        "show me route map",
        "show me the route map",
        "what routes exist",
        "show me task classes",
        "show me the command map",
        "how do I find the right command",
        "how do I navigate this",
        "how do I navigate",
        "show me docs",
        "show me documentation",
        "where are the docs",
    ],
)
def test_agent_entry_card_aliases_navigation_questions_to_navigation_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "navigation"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "navigation"
    assert payload["task_route"]["primary_organ_id"] == "pattern_binding_contract"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "navigation"
    assert "agent-entry-composition --task navigation" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "web UI",
        "web view",
        "local web view",
        "run web UI",
        "open the UI",
        "show me UI",
        "open browser",
        "browser surface",
        "open in browser",
        "view in browser",
        "local server",
        "serve locally",
        "start server",
        "start local server",
        "serve max requests",
        "serve port",
        "serve docs",
        "local observatory",
        "open observatory",
        "observatory endpoint",
        "observatory status",
        "localhost",
        "localhost status",
        "localhost endpoint",
        "project status endpoint",
        "status endpoint",
        "served status",
        "served status smoke",
        "HTML pages",
        "html surface",
        "workingness endpoint",
        "max requests",
        "which port",
        "how do I view it",
        "how do I open it",
        "does it have a UI",
        "browser UI",
        "macos app",
        "macOS capsule",
    ],
)
def test_agent_entry_card_aliases_browser_questions_to_frontend_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "frontend"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "frontend"
    assert payload["task_route"]["primary_organ_id"] == "batch7_station_runtime_capsule"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "frontend"
    assert "agent-entry-composition --task frontend" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "show me security",
        "show me the security",
        "show me security parts",
        "secret scan",
        "private path scan",
        "private-path scan",
        "credential scan",
        "stripping guard",
        "show me sandbox parts",
        "show me memory poisoning",
        "show me prompt injection",
        "is this safe",
        "is this secure",
        "security review",
        "red team",
    ],
)
def test_agent_entry_card_aliases_security_questions_to_security_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "security"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "security"
    assert (
        payload["task_route"]["primary_organ_id"]
        == "agent_memory_temporal_conflict_replay"
    )
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "security"
    assert "agent-entry-composition --task security" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "show me compliance",
        "show me the compliance",
        "is this compliant",
        "compliance review",
    ],
)
def test_agent_entry_card_aliases_compliance_questions_to_compliance_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "compliance"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "compliance"
    assert payload["task_route"]["primary_organ_id"] == "batch8_compliance_pipeline_capsule"
    assert " validate-bundle " in payload["task_route"]["first_command"]
    assert (
        "examples/batch8_compliance_pipeline_capsule/"
        "exported_batch8_compliance_pipeline_capsule_bundle"
        in payload["task_route"]["first_command"]
    )
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "compliance"
    assert "agent-entry-composition --task compliance" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "how do I evaluate it",
        "how can I evaluate it",
        "how to evaluate",
        "evaluate",
        "evaluate it",
        "evaluate this repo",
        "review this",
        "what are the risks",
        "what is broken",
        "what are the limitations",
        "what limitations exist",
        "what are the caveats",
        "what caveats exist",
        "what claims are refused",
        "show me release boundaries",
        "is this safe to publish",
        "show me claim ceilings",
        "what is the public floor",
        "show me public floor",
        "what is the verification floor",
        "public verification floor",
        "show me verification floor",
        "is this production ready",
        "show me checks",
        "check this",
        "check the repo",
        "how do I check it",
        "what checks can I run",
        "what checks should I run",
        "how do I run checks",
        "how do I run tests",
        "how can I run the checks",
        "how can I run the tests",
        "make check",
        "make validate",
        "validate repo",
        "validate",
        "preflight",
        "verify",
        "verify this",
        "verification",
        "validation",
        "CI",
        "pytest",
        "verify this repo",
        "verify the repo",
        "make ci",
        "make test",
        "github actions",
        "run make ci",
        "what does make ci do",
        "test",
        "tests",
        "run tests",
        "where are the tests",
        "test suite",
        "test it",
        "how do I test it",
        "how do I test this",
        "what tests should I run",
        "smoke",
        "smoke test",
        "smoke path",
        "make smoke",
        "make package smoke",
        "what should pass",
        "what is green",
        "green floor",
        "public green floor",
        "what commands prove it runs",
        "how do I know it works",
        "does it pass tests",
        "what is the test floor",
        "full test floor",
        "public test floor",
        "source form smoke",
        "package install smoke",
        "run smoke",
        "flight recorder",
        "skeptic flight recorder",
        "make flight recorder",
        "verify flight recorder",
        "flight recorder verify",
        "proof packet",
        "reviewer proof packet",
        "replay packet",
        "command transcript",
        "output digests",
        "run the tests",
        "run check",
        "run preflight",
        "test this repo",
        "smoke checks",
        "run smoke checks",
        "run ci",
        "ci check",
        "github actions floor",
        "verify repo",
        "verify public floor",
        "evidence",
        "show me the receipts",
        "show receipt index",
        "what receipts exist",
        "receipt index",
        "evidence index",
        "what is a receipt",
        "what are receipts",
        "what do receipts prove",
        "what don't receipts prove",
        "do receipts prove correctness",
        "are receipts proofs",
        "which receipts matter",
        "receipt authority",
        "authority receipts",
        "receipt limits",
        "receipt limitations",
        "receipt caveats",
        "receipt replay",
        "replay receipts",
        "receipt verify",
        "verify receipts",
        "receipt drilldown",
        "drilldown receipts",
        "drill into receipts",
        "how do I inspect receipts",
        "inspect receipts",
        "inspect a receipt",
        "inspect receipt",
        "open raw receipts",
        "raw receipts",
        "command receipts",
        "where are the receipts",
        "what do receipts mean",
        "receipts meaning",
        "what do these receipts mean",
        "what do the receipts prove",
        "proof vs receipt",
        "receipt vs proof",
        "receipts vs proof",
        "evidence receipt",
        "receipt evidence",
        "show receipts",
        "receipt boundary",
        "explain receipts",
        "explain the receipts",
        "what is evidence",
        "show me evidence",
        "evidence list",
        "list evidence",
        "evidence inspect",
        "inspect evidence",
        "evidence drilldown",
        "drilldown evidence",
        "bounded receipt index",
        "evidence refs",
        "evidence handles",
        "what backs this",
        "what backs this claim",
        "what backs each claim",
        "what backs the claims",
        "what evidence backs this",
        "audit trail",
        "blocked evidence",
        "blocked command evidence",
        "nonzero command",
        "non-zero command",
        "output digest proof",
        "source modules evidence",
        "body import receipts",
        "what counts as evidence",
        "evidence class",
        "evidence classes",
        "what is evidence class",
        "what are evidence classes",
        "where is the evidence",
        "explain evidence",
        "what does the evidence mean",
        "black box recorder",
        "what fails",
        "failure modes",
        "known gaps",
        "limitations",
        "what claims does this repo refuse",
    ],
)
def test_agent_entry_card_aliases_evaluation_questions_to_evaluation_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "evaluation"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "evaluation"
    assert payload["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "evaluation"
    assert "agent-entry-composition --task evaluation" in card["drilldowns"]["full_json"]


def test_agent_entry_card_keeps_receipts_alias_traceable() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="receipts",
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == "receipts"
    assert payload["task_route"]["selected_task_class"] == "evaluation"
    assert payload["task_route"]["alias_resolution"]["status"] == "alias_resolved"
    assert (
        "Receipt/evidence meaning questions use the evaluation route"
        in payload["task_route"]["alias_resolution"]["reason"]
    )
    assert card["task_route"]["alias_resolution"] == payload["task_route"][
        "alias_resolution"
    ]
    assert "agent-entry-composition --task receipts" in card["drilldowns"][
        "full_json"
    ]
    assert "agent-entry-composition --root . --task receipts" in card["drilldowns"][
        "source_checkout_full_json"
    ]


def test_agent_entry_card_keeps_receipt_proof_question_traceable() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="what do receipts prove",
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == "what do receipts prove"
    assert payload["task_route"]["selected_task_class"] == "evaluation"
    assert payload["task_route"]["alias_resolution"]["status"] == "alias_resolved"
    assert (
        "Receipt/evidence meaning questions use the evaluation route"
        in payload["task_route"]["alias_resolution"]["reason"]
    )
    assert card["task_route"]["alias_resolution"] == payload["task_route"][
        "alias_resolution"
    ]
    assert (
        "agent-entry-composition --task 'what do receipts prove'"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "interesting",
        "demo",
        "show me demo",
        "show me a demo",
        "tour",
        "tour me",
        "walkthrough",
        "show me walkthrough",
        "show interesting parts",
        "what is interesting",
        "what is interesting here",
        "what's interesting",
        "whats interesting",
        "show me interesting stuff",
        "show me something interesting",
        "show me the interesting parts",
        "what are the interesting parts",
        "show me interesting things",
        "interesting bits",
        "interesting stuff",
        "show me the interesting bits",
        "what's cool",
        "what is cool here",
        "cool parts",
        "show me cool parts",
        "show me the cool parts",
        "what are the cool parts",
        "highlights",
        "highlight parts",
        "project highlights",
        "show highlights",
        "show me the highlights",
        "notable parts",
        "show notable parts",
        "show me notable parts",
        "what's notable",
        "what's unusual",
        "what is unusual here",
        "what's different here",
        "what is different here",
        "what makes this useful",
        "why should I care",
        "show me what's interesting",
        "worth looking at",
        "what is worth looking at",
        "what is worth inspecting",
        "what is worth reading",
        "worth seeing",
        "what is worth seeing",
        "why should I look at this",
        "best parts",
        "crown jewels",
        "most interesting parts",
        "most notable parts",
        "what should I look at",
        "what should I look at first",
        "where should I look",
        "where should I start looking",
        "what should I read first",
        "what should I inspect",
        "what should I inspect first",
        "where are the interesting parts",
        "where should I start",
        "which parts matter",
        "which parts are worth reading",
        "show me the good parts",
        "what stands out",
        "tour interesting",
        "interesting tour",
        "quick tour",
        "demo path",
        "demo to scale",
        "observatory bridge",
        "local demo",
        "structural scale",
        "proof lab",
        "evidence floor",
        "source tour",
        "repo tour",
        "show me around",
        "show me math finance ai safety formal methods",
        "show me domains",
        "domain routes",
        "show me domain routes",
        "domain tour",
    ],
)
def test_agent_entry_card_aliases_interesting_to_interesting_parts_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "interesting-parts"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "interesting-parts"
    assert payload["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert card["task_route"]["selected_task_class"] == "interesting-parts"
    assert (
        "agent-entry-composition --task interesting-parts"
        in card["drilldowns"]["full_json"]
    )


def test_agent_entry_card_explains_interesting_alias_boundary() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="what is interesting here",
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["selected_task_class"] == "interesting-parts"
    assert payload["task_route"]["alias_resolution"]["status"] == "alias_resolved"
    assert (
        "bounded public first-run and reveal surfaces"
        in payload["task_route"]["alias_resolution"]["reason"]
    )
    assert "novelty" in payload["task_route"]["alias_resolution"]["reason"]
    assert "domain correctness" in payload["task_route"]["alias_resolution"]["reason"]
    assert card["task_route"]["alias_resolution"] == payload["task_route"][
        "alias_resolution"
    ]


@pytest.mark.parametrize(
    "task",
    [
        "domain specialist",
        "show me the domain specialist path",
        "domain expert",
        "specialist",
        "expert review",
        "show me specialty",
        "show me specialties",
        "show specialties",
        "specialty index",
        "find my specialty",
        "find your specialty",
        "which specialty",
        "where are specialties",
        "show me research workflows",
        "research workflow",
        "show research",
        "show me research parts",
        "show me the research",
        "research science",
        "show science",
        "show me science parts",
        "show me science workflows",
        "scientific replay",
        "science replays",
        "science replay",
        "scientific workflows",
        "show me scientific replays",
        "show me mechanistic interpretability",
        "mech interp",
        "interpretability",
        "show me interpretability",
        "biology",
        "replication",
        "replication rubric",
        "paper replication",
        "show me replication",
        "show me research replication",
        "show me paper replication",
        "show me chemistry",
        "materials science",
        "show me materials chemistry",
        "materials lab",
        "materials-lab safety",
        "show me materials lab safety",
        "lab safety",
        "closed loop lab",
        "spatial world model",
        "show me spatial world model",
        "world model",
        "spatial simulation",
        "counterfactual simulation",
        "show me counterfactual simulation",
        "robotics",
        "robotics route",
        "prediction reconciliation",
        "research replay",
        "show me research replays",
    ],
)
def test_agent_entry_card_aliases_research_specialties_to_research_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "research-workflows"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "research-workflows"
    assert (
        payload["task_route"]["primary_organ_id"]
        == "research_replication_rubric_artifact_replay"
    )
    assert card["task_route"]["selected_task_class"] == "research-workflows"
    assert (
        "agent-entry-composition --task research-workflows"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "market boundary",
        "show me market boundary",
        "show me the market boundary",
        "market claims",
        "financial claims",
    ],
)
def test_agent_entry_card_aliases_market_boundary_to_market_boundary_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "market-boundary"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "market-boundary"
    assert payload["task_route"]["primary_organ_id"] == "batch7_secondary_runtime_capsule"
    assert card["task_route"]["selected_task_class"] == "market-boundary"
    assert (
        "agent-entry-composition --task market-boundary"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "audio",
        "audio rms",
        "rms",
        "rms level",
        "audio level",
        "audio level rms",
        "audio level rms port",
    ],
)
def test_agent_entry_card_aliases_audio_phrases_to_audio_route(task: str) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "audio"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "audio"
    assert payload["task_route"]["primary_organ_id"] == "batch8_audio_level_rms_port"
    assert card["task_route"]["selected_task_class"] == "audio"
    assert "agent-entry-composition --task audio" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "math",
        "mathematics",
        "formal math",
        "show math",
        "show me math",
        "show me the math",
        "where is the math",
        "math parts",
        "show me math stuff",
        "show me math parts",
        "show me the math parts",
        "mathematical parts",
        "show me the mathematical parts",
        "formal verification",
        "formal proof",
        "formal proofs",
        "proof",
        "proof pipeline",
        "proof evidence",
        "math proof parts",
        "where are the proofs",
        "how do I inspect proofs",
        "does it prove anything",
        "math proof",
        "mathlib",
        "mathlib readiness",
        "certificate",
        "certificates",
        "proof certificate",
        "certificate kernel",
        "verifier",
        "verifier lab",
        "tactic",
        "tactics",
        "premise retrieval",
        "premise search",
        "formal evidence cells",
        "verification traces",
        "proof diagnostics",
        "proof search",
        "proof authority",
        "show formal methods",
        "show me formal math",
        "show me formal methods",
        "formal methods parts",
        "show me the formal methods",
        "show me formal methods stuff",
        "show me the formal methods parts",
        "show me formal verification",
        "show me the formal verification parts",
        "show me proof stuff",
        "show me proof parts",
        "show me proofs",
        "proof parts",
        "proofs",
        "proof checking",
        "show me proof checking",
        "proof system",
        "proof correctness",
        "does this prove correctness",
        "is this proof correct",
        "show me proof correctness",
    ],
)
def test_agent_entry_card_aliases_math_to_formal_methods_route(task: str) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)
    source_checkout_command = (
        "PYTHONPATH=src python3 -m microcosm_core proof-diagnostic-evidence-spine "
        "run --input fixtures/first_wave/proof_diagnostic_evidence_spine/input "
        "--out receipts/first_wave/proof_diagnostic_evidence_spine --card"
    )

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "formal-methods"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "formal-methods"
    assert payload["task_route"]["primary_organ_id"] == "proof_diagnostic_evidence_spine"
    assert payload["task_route"]["source_checkout_first_command"] == source_checkout_command
    assert payload["selected_viewer_route"]["source_checkout_next_action"] == (
        source_checkout_command
    )
    assert payload["viewer_first_action_router"]["routes"]["human"][
        "source_checkout_next_action"
    ] == source_checkout_command
    assert payload["read_run_order"][1]["source_checkout_run"] == source_checkout_command
    assert card["task_route"]["selected_task_class"] == "formal-methods"
    assert card["task_route"]["source_checkout_first_command"] == source_checkout_command
    assert card["selected_viewer_route"]["source_checkout_next_action"] == (
        source_checkout_command
    )
    assert (
        "agent-entry-composition --task formal-methods"
        in card["drilldowns"]["full_json"]
    )


@pytest.mark.parametrize(
    "task",
    [
        "show me finance",
        "where is finance",
        "show me finance stuff",
        "finance stuff",
        "finance parts",
        "financial parts",
        "show me the finance parts",
        "show me the financial parts",
        "is this financial advice",
        "investment advice",
        "trading advice",
        "show me trading parts",
        "show me the trading parts",
        "show me forecasts",
        "show me the forecasts",
        "forecast eval",
        "forecast evaluation",
        "finance eval",
        "finance eval spine",
        "finance forecast evaluation spine",
        "forecast spine",
        "price forecast",
        "where are forecasts",
        "show forecasts",
        "forecast receipts",
        "finance receipts",
        "forecast reconciliation",
        "calibration",
        "forecast calibration",
        "finance forecast",
        "financial forecast",
        "finance forecasts",
        "financial forecasts",
        "forecasting evals",
        "finance evals",
        "finance evaluation",
        "market forecasts",
        "market evaluation",
        "financial",
        "financial advice",
        "not financial advice",
        "forecast",
        "forecasts",
        "forecasting workflows",
        "market",
        "market parts",
        "market dashboard",
        "market board",
        "show me markets",
        "prediction markets",
        "prediction",
        "prediction market",
        "prediction market parts",
        "prediction market board",
        "prediction ledger",
        "prediction lens",
        "show me prediction markets",
        "polymarket",
        "investment",
        "investing",
        "portfolio",
        "how do I inspect finance",
        "trading",
        "trading system",
        "is this trading advice",
    ],
)
def test_agent_entry_card_aliases_finance_phrases_to_finance_route(task: str) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "finance"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "finance"
    assert payload["task_route"]["primary_organ_id"] == "finance_forecast_evaluation_spine"
    assert card["task_route"]["selected_task_class"] == "finance"
    assert "agent-entry-composition --task finance" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "receipts",
        "receipt",
        "show me receipts",
        "what do the receipts mean",
        "flight recorder",
        "proof packet",
        "receipt replay",
        "show evidence",
        "evidence inspect",
        "how do I inspect evidence",
        "open a receipt",
        "read a receipt",
        "are receipts authority",
        "what does status pass mean",
        "what does evidence pass mean",
        "what does a receipt prove",
        "black box recorder",
    ],
)
def test_agent_entry_card_aliases_receipt_questions_to_evaluation_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "evaluation"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "evaluation"
    assert payload["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert card["task_route"]["selected_task_class"] == "evaluation"
    if task in {"receipts", "receipt"}:
        assert f"agent-entry-composition --task {task}" in card["drilldowns"][
            "full_json"
        ]
    else:
        assert (
            "agent-entry-composition --task evaluation"
            in card["drilldowns"]["full_json"]
        )


@pytest.mark.parametrize(
    "task",
    [
        "Lean stuff",
        "show me Lean",
        "show me Lean stuff",
        "show me Lean parts",
        "Lean proofs",
        "Lean pipeline",
        "Lean witness",
        "does Lean run",
        "show me Lean proofs",
        "show me the Lean proofs",
    ],
)
def test_agent_entry_card_aliases_lean_questions_to_lean_route(task: str) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "lean"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "lean"
    assert payload["task_route"]["primary_organ_id"] == "proof_diagnostic_evidence_spine"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "lean"
    assert "agent-entry-composition --task lean" in card["drilldowns"]["full_json"]


@pytest.mark.parametrize(
    "task",
    [
        "theorem proving",
        "show me theorem proving",
        "show me the theorem proving",
        "show me theorem proving parts",
        "theorem prover",
        "theorem proof",
        "show me theorem prover",
    ],
)
def test_agent_entry_card_aliases_theorem_proving_questions_to_theorem_proving_route(
    task: str,
) -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task=task,
        viewer="human",
        command="pytest",
    )
    card = compact_agent_entry_card(payload)

    assert payload["status"] == "pass"
    assert payload["task_route"]["requested_task"] == task
    assert payload["task_route"]["selected_task_class"] == "theorem-proving"
    assert payload["task_route"]["selected_task_route_found"] is True
    assert payload["task_route"]["task_class"] == "theorem-proving"
    assert payload["task_route"]["primary_organ_id"] == "proof_diagnostic_evidence_spine"
    assert payload["selected_viewer_route"]["next_action"] == payload["task_route"][
        "first_command"
    ]
    assert card["task_route"]["selected_task_class"] == "theorem-proving"
    assert (
        "agent-entry-composition --task theorem-proving"
        in card["drilldowns"]["full_json"]
    )


def test_agent_entry_card_blocks_unknown_task_route_without_silent_fallback() -> None:
    payload = build_agent_entry_composition(
        root=MICROCOSM_ROOT,
        task="not-a-real-task-class",
        viewer="human",
        command="pytest",
    )

    assert payload["status"] == "blocked"
    assert payload["task_route"]["selected_task_class"] == "not-a-real-task-class"
    assert payload["task_route"]["selected_task_route_found"] is False
    assert payload["task_route"]["task_class"] == "agent-entry"
    assert "missing_selected_task_route" in {
        error["code"] for error in payload["validation"]["errors"]
    }


def test_agent_entry_card_rejects_hidden_discoverability_matrix_route() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["organ_discoverability_matrix_route"]["run"] = "see ORGANS.md"
    bad_payload["organ_discoverability_matrix_route"]["read"] = []

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert {
        "discoverability_matrix_command_not_runnable_shape",
        "discoverability_matrix_source_ref_missing",
    } <= {error["code"] for error in result["errors"]}


def test_agent_entry_card_rejects_incomplete_accepted_organ_glance() -> None:
    payload = _build()
    bad_payload = copy.deepcopy(payload)
    bad_payload["accepted_organ_glance"]["families"][0]["organs"][0]["one_line"] = ""

    result = validate_agent_entry_composition(bad_payload)

    assert result["status"] == "blocked"
    assert "accepted_organ_glance_row_incomplete" in {
        error["code"] for error in result["errors"]
    }


def test_agent_entry_card_cli_writes_projection_and_receipt(tmp_path: Path) -> None:
    payload = compile_paths(
        root=MICROCOSM_ROOT,
        task="agent-entry",
        out=tmp_path,
        command="pytest",
    )

    card_path = tmp_path / "agent_entry_composition_card.json"
    receipt_path = tmp_path / "agent_entry_composition_receipt.json"
    assert payload["status"] == "pass"
    assert card_path.exists()
    assert receipt_path.exists()

    card = json.loads(card_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert card["task_route"]["task_class"] == "agent-entry"
    assert receipt["selected_task_class"] == "agent-entry"
    assert receipt["selected_viewer"] == "all"
    assert receipt["selected_viewer_route_kind"] == "viewer_route_set"
    public_path_prefixes = ("<repo-root>/", "<host-temp>/")
    assert card["artifact_paths"]["card_path"].startswith(public_path_prefixes)
    assert card["artifact_paths"]["receipt_path"].startswith(public_path_prefixes)
    assert card["artifact_paths"]["card_path"].endswith(
        "/agent_entry_composition_card.json"
    )
    assert card["artifact_paths"]["receipt_path"].endswith(
        "/agent_entry_composition_receipt.json"
    )
    assert receipt["artifact_paths"]["card_path"].startswith(public_path_prefixes)
    assert receipt["artifact_paths"]["receipt_path"].startswith(public_path_prefixes)
    assert receipt["artifact_paths"]["card_path"].endswith(
        "/agent_entry_composition_card.json"
    )
    assert receipt["artifact_paths"]["receipt_path"].endswith(
        "/agent_entry_composition_receipt.json"
    )
    assert receipt["card_path"].startswith(public_path_prefixes)
    assert receipt["receipt_path"].startswith(public_path_prefixes)
    assert receipt["card_path"].endswith("/agent_entry_composition_card.json")
    assert receipt["receipt_path"].endswith("/agent_entry_composition_receipt.json")
    assert receipt["validation"]["status"] == "pass"
    assert receipt["validation"]["errors"] == []
    assert receipt["validation_errors"] == []
    assert receipt["accepted_organ_glance"] == {
        "source_ref": ORGAN_GLANCE_REF,
        "family_count": 7,
        "organ_count": 82,
        "capsule_join_status_counts": {
            "direct": 75,
            "paper_module_ref_bridge": 7,
        },
        "drilldown": "ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line",
    }
    assert set(receipt["viewer_modes"]) == {"type_a_agent", "human"}
    assert all(row["status"] == "pass" for row in receipt["entry_experience_checks"])
    assert receipt["macro_import_route_body_floor"] == list(MACRO_IMPORT_ROUTE_ORGANS)


def test_microcosm_cli_exposes_agent_entry_composition_card(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(MICROCOSM_ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "microcosm_core",
            "agent-entry-composition",
            "--root",
            str(MICROCOSM_ROOT),
            "--task",
            "agent-entry",
            "--viewer",
            "human",
            "--out",
            str(tmp_path),
            "--check",
        ],
        cwd=MICROCOSM_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["selected_viewer"] == "human"
    assert payload["selected_viewer_route"]["viewer"] == "human"
    assert payload["selected_viewer_route"]["first_safe_action"] == "microcosm hello <project>"
    assert payload["viewer_first_action_router"]["source_checkout_select_viewer_command"] == (
        SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND
    )
    assert payload["read_run_order"][0]["kind"] == "selected_viewer_route"
    assert payload["read_run_order"][0]["run"] == "microcosm hello <project>"
    assert payload["task_route"]["task_class"] == "agent-entry"
    assert payload["first_screen_type_a_route"]["reader_id"] == "type_a_agent"
    assert {row["viewer"] for row in payload["viewer_modes"]} == {
        "type_a_agent",
        "human",
    }
    assert "cold_reader_route_map" in {
        row["organ_id"] for row in payload["macro_import_route_body_floor"]
    }
    assert (tmp_path / "agent_entry_composition_card.json").exists()
    assert (tmp_path / "agent_entry_composition_receipt.json").exists()


def test_microcosm_cli_agent_entry_composition_card_is_compact() -> None:
    payload = _build()
    card = compact_agent_entry_card(payload)

    assert card["schema"] == "microcosm_agent_entry_composition_compact_card_v0"
    assert card["compact_projection_of"] == "microcosm_agent_entry_composition_projection_v0"
    assert card["status"] == "pass"
    assert len(json.dumps(card, sort_keys=True)) < 16000
    assert "null" not in json.dumps(card, sort_keys=True)
    assert card["viewer_first_action_router"]["select_viewer_command"] == (
        "microcosm agent-entry-composition --task agent-entry "
        "--viewer {type_a_agent|human} --card"
    )
    assert card["task_route"]["primary_organ_id"] == "cold_reader_route_map"
    assert "relevant_organs" not in card["task_route"]
    assert card["accepted_organ_glance"]["organ_count"] == 82
    assert "families" not in card["accepted_organ_glance"]
    assert {
        row["organ_id"] for row in card["macro_import_route_body_floor"]
    } == set(MACRO_IMPORT_ROUTE_ORGANS)
    assert "receipt_refs" in card["macro_import_route_body_floor"][0]
    assert card["authority_ceiling"] == {
        "release_authority": False,
        "source_mutation_authority": False,
        "provider_call_authority": False,
        "private_root_equivalence_authority": False,
    }
