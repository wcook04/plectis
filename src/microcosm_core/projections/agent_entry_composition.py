from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from microcosm_core.projections.concept_mechanism_read_model import (
    build_organ_doctrine_rows,
)
from microcosm_core.receipts import write_json_atomic
from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA = "microcosm_agent_entry_composition_projection_v0"
RECEIPT_SCHEMA = "microcosm_agent_entry_composition_receipt_v0"
DEFAULT_TASK = "agent-entry"
CARD_FILENAME = "agent_entry_composition_card.json"
RECEIPT_FILENAME = "agent_entry_composition_receipt.json"
TYPE_A_READER_ID = "type_a_agent"
HUMAN_VIEWER_ID = "human"
ALL_VIEWERS = "all"
VIEWER_IDS = (TYPE_A_READER_ID, HUMAN_VIEWER_ID)
SELECT_VIEWER_COMMAND = (
    "microcosm agent-entry-composition --task agent-entry "
    "--viewer {type_a_agent|human} --card"
)
SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND = (
    "PYTHONPATH=src python3 -m microcosm_core agent-entry-composition "
    "--root . --task agent-entry --viewer {type_a_agent|human} --card"
)
SOURCE_CHECKOUT_FIRST_SCREEN_CARD_COMMAND = (
    "PYTHONPATH=src python3 -m microcosm_core first-screen --card <project>"
)
SOURCE_CHECKOUT_ORGAN_SURFACE_CONTRACT_COMMAND = (
    "PYTHONPATH=src python3 -m microcosm_core "
    "organ-surface-contract --card --root ."
)
ENTRY_PACKET_REF = "atlas/entry_packet.json"
TASK_ROUTES_REF = "atlas/agent_task_routes.json"
ORGAN_GLANCE_REF = "atlas/agent_task_routes.json::organ_glance_ladder"
ORGAN_REGISTRY_REF = "core/organ_registry.json::implemented_organs"
ORGAN_ATLAS_REF = "core/organ_atlas.json::organs"
EVIDENCE_CLASSES_REF = "core/organ_evidence_classes.json::organ_evidence_classes"
DOCTRINE_ROW_REF = "microcosm_core.projections.concept_mechanism_read_model::build_organ_doctrine_rows"
ORGAN_DISCOVERABILITY_MATRIX_REF = (
    "microcosm_core.projections.organ_discoverability_matrix::"
    "build_organ_discoverability_matrix"
)
ORGAN_DISCOVERABILITY_MATRIX_COMMAND = (
    "microcosm organ-discoverability-matrix --root . --check"
)
MACRO_IMPORT_ROUTE_ORGANS = (
    "cold_reader_route_map",
    "navigation_hologram_route_plane",
    "standards_meta_diagnostics",
    "voice_to_doctrine_self_improvement_loop",
)
REQUIRED_TOP_LEVEL_SOURCE_REFS = (
    ENTRY_PACKET_REF,
    TASK_ROUTES_REF,
    ORGAN_REGISTRY_REF,
    ORGAN_ATLAS_REF,
    EVIDENCE_CLASSES_REF,
    DOCTRINE_ROW_REF,
    ORGAN_DISCOVERABILITY_MATRIX_REF,
)
PROJECTION_AUTHORITY_POSTURE = (
    "derived_projection_not_source_or_release_authority_no_source_mutation_"
    "no_provider_calls_no_private_root_equivalence"
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [item for item in _as_list(value) if isinstance(item, str) and item.strip()]


def _load_json(path: Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _rows_by_id(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(payload.get(key)):
        if not isinstance(row, dict):
            continue
        organ_id = str(row.get("organ_id") or "")
        if organ_id:
            rows[organ_id] = row
    return rows


def _route_rows_by_task(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(payload.get("routes")):
        if not isinstance(row, dict):
            continue
        task_class = str(row.get("task_class") or "")
        if task_class:
            rows[task_class] = row
    return rows


def _accepted_organ_glance(task_routes: dict[str, Any]) -> dict[str, Any]:
    families = [
        row
        for row in _as_list(task_routes.get("organ_glance_ladder"))
        if isinstance(row, dict)
    ]
    compact_families: list[dict[str, Any]] = []
    join_status_counts: dict[str, int] = {}
    organ_count = 0
    for family in families:
        organs: list[dict[str, Any]] = []
        for row in _as_list(family.get("organs")):
            if not isinstance(row, dict):
                continue
            join_status = str(row.get("capsule_join_status") or "")
            if join_status:
                join_status_counts[join_status] = (
                    join_status_counts.get(join_status, 0) + 1
                )
            authority_ceiling = row.get("authority_ceiling")
            organs.append(
                {
                    "organ_id": row.get("organ_id"),
                    "display_name": row.get("display_name"),
                    "one_line": row.get("one_line"),
                    "card": row.get("card"),
                    "authority_ceiling": authority_ceiling,
                    "claim_ceiling_restated": (
                        row.get("claim_ceiling_restated") or authority_ceiling
                    ),
                    "evidence_class": row.get("evidence_class"),
                    "first_command": row.get("first_command"),
                    "paper_module_ref": row.get("paper_module_ref"),
                    "capsule_id": row.get("capsule_id"),
                    "capsule_join_status": row.get("capsule_join_status"),
                    "card_ref": row.get("card_ref") or row.get("drilldown_target"),
                    "drilldown_target": row.get("drilldown_target"),
                }
            )
        organ_count += len(organs)
        compact_families.append(
            {
                "family_id": family.get("family_id"),
                "label": family.get("label"),
                "organ_count": len(organs),
                "organs": organs,
            }
        )
    capsule_accounting = _as_dict(task_routes.get("capsule_accounting"))
    return {
        "schema": "microcosm_agent_entry_accepted_organ_glance_v0",
        "source_ref": ORGAN_GLANCE_REF,
        "authority_boundary": (
            "Projection/read authority only; organ registry, atlas source rows, "
            "capsule compression, paper modules, receipts, and source files remain "
            "the authority."
        ),
        "family_count": len(compact_families),
        "organ_count": organ_count,
        "capsule_accounting": capsule_accounting,
        "capsule_join_status_counts": dict(sorted(join_status_counts.items())),
        "families": compact_families,
        "first_family_label": compact_families[0].get("label") if compact_families else None,
        "drilldown": "ORGANS.md#microcosm-at-a-glance--every-organ-in-one-line",
        "anti_claim": (
            "This glance is not a release, proof, maturity, source-mutation, "
            "provider-call, private-root-equivalence, or whole-system-correctness "
            "authority."
        ),
    }


def _normalize_task_class(task: str | None) -> str:
    value = (task or "").strip().lower()
    if not value:
        return DEFAULT_TASK
    if value in {
        "agent-entry",
        "agent_entry",
        "type-a-agent",
        "type a agent",
        "type_a_agent",
        "repo reading agent",
        "repo-reading-agent",
        "repo_reading_agent",
        "repo-reading agent",
        "agent path",
        "agent-path",
        "agent_path",
        "where do i patch this",
        "where-do-i-patch-this",
        "where_do_i_patch_this",
        "where do i patch a route",
        "where-do-i-patch-a-route",
        "where_do_i_patch_a_route",
        "where do i patch the route",
        "where-do-i-patch-the-route",
        "where_do_i_patch_the_route",
        "what owns this route",
        "what-owns-this-route",
        "what_owns_this_route",
        "who owns this route",
        "who-owns-this-route",
        "who_owns_this_route",
        "route owner",
        "route-owner",
        "route_owner",
        "owner surface",
        "owner-surface",
        "owner_surface",
        "owner surface to patch",
        "owner-surface-to-patch",
        "owner_surface_to_patch",
        "which file owns routes",
        "which-file-owns-routes",
        "which_file_owns_routes",
        "which file owns route selection",
        "which-file-owns-route-selection",
        "which_file_owns_route_selection",
        "where is route selection",
        "where-is-route-selection",
        "where_is_route_selection",
        "route selection owner",
        "route-selection-owner",
        "route_selection_owner",
        "route selection code",
        "route-selection-code",
        "route_selection_code",
        "agent entry owner",
        "agent-entry-owner",
        "agent_entry_owner",
        "agent entry composition",
        "agent-entry-composition",
        "agent_entry_composition",
        "agent entry composition owner",
        "agent-entry-composition-owner",
        "agent_entry_composition_owner",
        "where is agent entry composition",
        "where-is-agent-entry-composition",
        "where_is_agent_entry_composition",
        "first screen owner",
        "first-screen-owner",
        "first-screen owner",
        "first_screen_owner",
        "first screen composition",
        "first-screen-composition",
        "first_screen_composition",
        "card owner",
        "card-owner",
        "card_owner",
        "which file owns cards",
        "which-file-owns-cards",
        "which_file_owns_cards",
        "where do i patch cards",
        "where-do-i-patch-cards",
        "where_do_i_patch_cards",
        "projection boundary",
        "projection-boundary",
        "projection_boundary",
        "validator boundary",
        "validator-boundary",
        "validator_boundary",
        "mechanism boundary",
        "mechanism-boundary",
        "mechanism_boundary",
        "mechanism validator projection boundary",
        "mechanism-validator-projection-boundary",
        "mechanism_validator_projection_boundary",
        "organ surface contract",
        "organ-surface-contract",
        "organ_surface_contract",
        "route misleads",
        "route-misleads",
        "route_misleads",
        "route is wrong",
        "route-is-wrong",
        "route_is_wrong",
        "agent route is wrong",
        "agent-route-is-wrong",
        "agent_route_is_wrong",
        "route card is wrong",
        "route-card-is-wrong",
        "route_card_is_wrong",
        "what is this",
        "what is this?",
        "what-is-this",
        "what_is_this",
        "what is this repo",
        "what-is-this-repo",
        "what_is_this_repo",
        "what is this repository",
        "what-is-this-repository",
        "what_is_this_repository",
        "what is this project",
        "what-is-this-project",
        "what_is_this_project",
        "what is microcosm",
        "what-is-microcosm",
        "what_is_microcosm",
        "what does this do",
        "what-does-this-do",
        "what_does_this_do",
        "what does microcosm do",
        "what-does-microcosm-do",
        "what_does_microcosm_do",
        "what am i looking at",
        "what-am-i-looking-at",
        "what_am_i_looking_at",
        "overview",
        "project overview",
        "project-overview",
        "project_overview",
        "why does this exist",
        "why-does-this-exist",
        "why_does_this_exist",
        "what is the point",
        "what-is-the-point",
        "what_is_the_point",
        "local project substrate",
        "local-project-substrate",
        "local_project_substrate",
        "what can i ask",
        "what-can-i-ask",
        "what_can_i_ask",
        "what should i ask",
        "what-should-i-ask",
        "what_should_i_ask",
        "what questions can i ask",
        "what-questions-can-i-ask",
        "what_questions_can_i_ask",
    }:
        return "agent-entry"
    if value in {
        "getting-started",
        "getting_started",
        "get started",
        "get-started",
        "get_started",
        "getting started",
        "getting_started",
        "quickstart",
        "quick-start",
        "quick_start",
        "quick start",
        "cold clone",
        "cold-clone",
        "cold_clone",
        "cold clone path",
        "cold-clone-path",
        "cold_clone_path",
        "clone and run",
        "clone-and-run",
        "clone_and_run",
        "start",
        "start from source",
        "start-from-source",
        "start_from_source",
        "first command",
        "first-command",
        "first_command",
        "first run",
        "first-run",
        "first_run",
        "first thing to run",
        "first-thing-to-run",
        "first_thing_to_run",
        "what do i run first",
        "what-do-i-run-first",
        "what_do_i_run_first",
        "what command first",
        "what-command-first",
        "what_command_first",
        "what is the first command",
        "what-is-the-first-command",
        "what_is_the_first_command",
        "which command first",
        "which-command-first",
        "which_command_first",
        "dry run bootstrap",
        "dry-run-bootstrap",
        "dry_run_bootstrap",
        "bootstrap dry run",
        "bootstrap-dry-run",
        "bootstrap_dry_run",
        "bootstrap dry-run",
        "bootstrap first",
        "bootstrap-first",
        "bootstrap_first",
        "bootstrap",
        "bootstrap script",
        "bootstrap-script",
        "bootstrap_script",
        "bootstrap.sh",
        "run bootstrap",
        "run-bootstrap",
        "run_bootstrap",
        "bootstrap probe",
        "bootstrap-probe",
        "bootstrap_probe",
        "safe first command",
        "safe-first-command",
        "safe_first_command",
        "safe probe",
        "safe-probe",
        "safe_probe",
        "no write first",
        "no-write-first",
        "no_write_first",
        "no-write first",
        "does this write files",
        "does-this-write-files",
        "does_this_write_files",
        "what files does it write",
        "what-files-does-it-write",
        "what_files_does_it_write",
        "bounded probe",
        "bounded-probe",
        "bounded_probe",
        "bounded cold clone probe",
        "bounded-cold-clone-probe",
        "bounded_cold_clone_probe",
        "cold clone check",
        "cold-clone-check",
        "cold_clone_check",
        "cold clone probe",
        "cold-clone-probe",
        "cold_clone_probe",
        "cold clone receipt",
        "cold-clone-receipt",
        "cold_clone_receipt",
        "ignored receipts",
        "ignored-receipts",
        "ignored_receipts",
        "where did bootstrap write",
        "where-did-bootstrap-write",
        "where_did_bootstrap_write",
        ".microcosm cold clone probe",
        ".microcosm-cold-clone-probe",
        ".microcosm_cold_clone_probe",
        "before installing",
        "before-installing",
        "before_installing",
        "before install",
        "before-install",
        "before_install",
        "install",
        "installation",
        "install this",
        "install-this",
        "install_this",
        "setup",
        "set up",
        "set-up",
        "set_up",
        "setup this repo",
        "setup-this-repo",
        "setup_this_repo",
        "set up this repo",
        "set-up-this-repo",
        "set_up_this_repo",
        "how do i set this up",
        "how-do-i-set-this-up",
        "how_do_i_set_this_up",
        "dependency",
        "dependencies",
        "what dependencies",
        "what-dependencies",
        "what_dependencies",
        "what dependencies do i need",
        "what-dependencies-do-i-need",
        "what_dependencies_do_i_need",
        "python version",
        "python-version",
        "python_version",
        "what python version",
        "what-python-version",
        "what_python_version",
        "requires python",
        "requires-python",
        "requires_python",
        "python requirements",
        "python-requirements",
        "python_requirements",
        "try it",
        "try-it",
        "try_it",
        "try this",
        "try-this",
        "try_this",
        "how do i try it",
        "how-do-i-try-it",
        "how_do_i_try_it",
        "how do i try this",
        "how-do-i-try-this",
        "how_do_i_try_this",
        "can i try it",
        "can-i-try-it",
        "can_i_try_it",
        "run it",
        "run-it",
        "run_it",
        "how do i install it",
        "how-do-i-install-it",
        "how_do_i_install_it",
        "how do i install",
        "how-do-i-install",
        "how_do_i_install",
        "how do i run it",
        "how-do-i-run-it",
        "how_do_i_run_it",
        "how do i run this",
        "how-do-i-run-this",
        "how_do_i_run_this",
        "run without installing",
        "run-without-installing",
        "run_without_installing",
        "run source only",
        "run-source-only",
        "run_source_only",
        "source-only install",
        "source_only_install",
        "source only install",
        "install from source",
        "install-from-source",
        "install_from_source",
        "editable install",
        "editable-install",
        "editable_install",
        "pip install",
        "pip-install",
        "pip_install",
        "pip install editable",
        "pip-install-editable",
        "pip_install_editable",
        "install test extras",
        "install-test-extras",
        "install_test_extras",
        "make install",
        "make-install",
        "make_install",
        "venv",
        "virtualenv",
        "create venv",
        "create-venv",
        "create_venv",
        "where is venv",
        "where-is-venv",
        "where_is_venv",
        "python pip install",
        "python-pip-install",
        "python_pip_install",
        "make smoke first",
        "make-smoke-first",
        "make_smoke_first",
        "run smoke first",
        "run-smoke-first",
        "run_smoke_first",
        "smoke path first",
        "smoke-path-first",
        "smoke_path_first",
        "quickstart path",
        "quickstart-path",
        "quickstart_path",
        "one page path",
        "one-page-path",
        "one_page_path",
        "one-page path",
        "source-only run",
        "source_only_run",
        "source only run",
        "source only",
        "source-only",
        "source_only",
        "without installing",
        "without-installing",
        "without_installing",
        "no install",
        "no-install",
        "no_install",
        "can't install",
        "can't-install",
        "can't_install",
        "cannot install",
        "cannot-install",
        "cannot_install",
        "does this run",
        "does-this-run",
        "does_this_run",
        "does it work",
        "does-it-work",
        "does_it_work",
        "is it runnable",
        "is-it-runnable",
        "is_it_runnable",
        "is this runnable",
        "is-this-runnable",
        "is_this_runnable",
        "can i run this",
        "can-i-run-this",
        "can_i_run_this",
        "can i run it",
        "can-i-run-it",
        "can_i_run_it",
        "commands",
        "command list",
        "command-list",
        "command_list",
        "list commands",
        "list-commands",
        "list_commands",
        "available commands",
        "available-commands",
        "available_commands",
        "help",
        "cli",
        "cli commands",
        "cli-commands",
        "cli_commands",
        "what commands exist",
        "what-commands-exist",
        "what_commands_exist",
        "show commands",
        "show-commands",
        "show_commands",
        "show me commands",
        "show-me-commands",
        "show_me_commands",
        "cli help",
        "cli-help",
        "cli_help",
        "command surface",
        "command-surface",
        "command_surface",
        "cli surface",
        "cli-surface",
        "cli_surface",
        "run source form",
        "run-source-form",
        "run_source_form",
        "source checkout",
        "source-checkout",
        "source_checkout",
        "source-only checkout",
        "source-only-checkout",
        "source_only_checkout",
        "without install",
        "without-install",
        "without_install",
        "dev setup",
        "dev-setup",
        "dev_setup",
        "developer setup",
        "developer-setup",
        "developer_setup",
        "install editable",
        "install-editable",
        "install_editable",
        "console command missing",
        "console-command-missing",
        "console_command_missing",
        "microcosm command not found",
        "microcosm-command-not-found",
        "microcosm_command_not_found",
        "command not found",
        "command-not-found",
        "command_not_found",
        "package smoke",
        "package-smoke",
        "package_smoke",
        "make package-smoke",
        "fresh venv",
        "fresh-venv",
        "fresh_venv",
        "fresh-venv package check",
        "fresh_venv_package_check",
        "fresh venv package check",
        "installed console proof",
        "installed-console-proof",
        "installed_console_proof",
        "show cli help",
        "show-cli-help",
        "show_cli_help",
        "show me cli help",
        "show-me-cli-help",
        "show_me_cli_help",
    }:
        return "getting-started"
    if value in {
        "architecture",
        "architectural",
        "spec",
        "specs",
        "specifications",
        "show spec",
        "show-spec",
        "show_spec",
        "show specs",
        "show-specs",
        "show_specs",
        "show specifications",
        "show-specifications",
        "show_specifications",
        "show me architecture",
        "show-me-architecture",
        "show_me_architecture",
        "show me the architecture",
        "show-me-the-architecture",
        "show_me_the_architecture",
        "show me specs",
        "show-me-specs",
        "show_me_specs",
        "show me specifications",
        "show-me-specifications",
        "show_me_specifications",
        "what is the architecture",
        "what-is-the-architecture",
        "what_is_the_architecture",
        "where is the architecture",
        "where-is-the-architecture",
        "where_is_the_architecture",
        "where are the specs",
        "where-are-the-specs",
        "where_are_the_specs",
        "how is this built",
        "how-is-this-built",
        "how_is_this_built",
        "how is this organized",
        "how-is-this-organized",
        "how_is_this_organized",
        "how is this organised",
        "how-is-this-organised",
        "how_is_this_organised",
        "which files are generated",
        "which-files-are-generated",
        "which_files_are_generated",
        "generated maps",
        "generated-maps",
        "generated_maps",
        "generated surfaces",
        "generated-surfaces",
        "generated_surfaces",
        "generated atlas",
        "generated-atlas",
        "generated_atlas",
        "what is generated here",
        "what-is-generated-here",
        "what_is_generated_here",
        "what files are generated",
        "what-files-are-generated",
        "what_files_are_generated",
        "what files can i edit",
        "what-files-can-i-edit",
        "what_files_can_i_edit",
        "what can i edit",
        "what-can-i-edit",
        "what_can_i_edit",
        "is agent_routes generated",
        "is-agent-routes-generated",
        "is_agent_routes_generated",
        "is agent routes generated",
        "is-agent-routes-generated",
        "is_agent_routes_generated",
        "is agent_routes.md generated",
        "is-agent-routes-md-generated",
        "is_agent_routes_md_generated",
        "is organs generated",
        "is-organs-generated",
        "is_organs_generated",
        "is organs.md generated",
        "is-organs-md-generated",
        "is_organs_md_generated",
        "what owns generated docs",
        "what-owns-generated-docs",
        "what_owns_generated_docs",
        "generated docs owner",
        "generated-docs-owner",
        "generated_docs_owner",
        "generated atlas owner",
        "generated-atlas-owner",
        "generated_atlas_owner",
        "can i edit generated docs",
        "can-i-edit-generated-docs",
        "can_i_edit_generated_docs",
        "generated files",
        "generated-files",
        "generated_files",
        "do not hand edit",
        "do-not-hand-edit",
        "do_not_hand_edit",
        "owner data",
        "owner-data",
        "owner_data",
        "builder",
        "who owns generated docs",
        "who-owns-generated-docs",
        "who_owns_generated_docs",
        "who owns agent_routes",
        "who-owns-agent-routes",
        "who_owns_agent_routes",
        "who owns agent_routes.md",
        "who-owns-agent-routes-md",
        "who_owns_agent_routes_md",
        "who owns organs",
        "who-owns-organs",
        "who_owns_organs",
        "who owns organs.md",
        "who-owns-organs-md",
        "who_owns_organs_md",
        "who owns architecture",
        "who-owns-architecture",
        "who_owns_architecture",
        "who owns architecture.md",
        "who-owns-architecture-md",
        "who_owns_architecture_md",
        "generated docs",
        "generated-docs",
        "generated_docs",
        "generated docs drift",
        "generated-docs-drift",
        "generated_docs_drift",
        "atlas drift",
        "atlas-drift",
        "atlas_drift",
        "verify generated maps",
        "verify-generated-maps",
        "verify_generated_maps",
        "check generated maps",
        "check-generated-maps",
        "check_generated_maps",
        "build generated docs",
        "build-generated-docs",
        "build_generated_docs",
        "build organ atlas",
        "build-organ-atlas",
        "build_organ_atlas",
        "organ atlas builder",
        "organ-atlas-builder",
        "organ_atlas_builder",
        "run build_organ_atlas",
        "run-build-organ-atlas",
        "run_build_organ_atlas",
        "source of generated route table",
        "source-of-generated-route-table",
        "source_of_generated_route_table",
        "projection owner",
        "projection-owner",
        "projection_owner",
        "projection refresh",
        "projection-refresh",
        "projection_refresh",
        "regenerate generated docs",
        "regenerate-generated-docs",
        "regenerate_generated_docs",
        "regenerate routes",
        "regenerate-routes",
        "regenerate_routes",
        "regenerate maps",
        "regenerate-maps",
        "regenerate_maps",
        "refresh agent_routes",
        "refresh-agent-routes",
        "refresh_agent_routes",
        "refresh agent_routes.md",
        "refresh-agent-routes-md",
        "refresh_agent_routes_md",
        "how do i refresh agent_routes",
        "how-do-i-refresh-agent-routes",
        "how_do_i_refresh_agent_routes",
        "refresh organs",
        "refresh-organs",
        "refresh_organs",
        "refresh organs.md",
        "refresh-organs-md",
        "refresh_organs_md",
        "refresh architecture",
        "refresh-architecture",
        "refresh_architecture",
        "refresh architecture.md",
        "refresh-architecture-md",
        "refresh_architecture_md",
        "do not hand edit generated docs",
        "do-not-hand-edit-generated-docs",
        "do_not_hand_edit_generated_docs",
    }:
        return "architecture"
    if value in {
        "source authority",
        "source-authority",
        "source_authority",
        "where is source authority",
        "where-is-source-authority",
        "where_is_source_authority",
        "what is source authority",
        "what-is-source-authority",
        "what_is_source_authority",
        "show me source authority",
        "show-me-source-authority",
        "show_me_source_authority",
        "where is the code",
        "where-is-the-code",
        "where_is_the_code",
        "show me the code",
        "show-me-the-code",
        "show_me_the_code",
        "show me the source",
        "show-me-the-source",
        "show_me_the_source",
        "source code",
        "source-code",
        "source_code",
        "source files",
        "source-files",
        "source_files",
        "source commands",
        "source-commands",
        "source_commands",
        "module entrypoint",
        "module-entrypoint",
        "module_entrypoint",
        "python module",
        "python-module",
        "python_module",
        "console script",
        "console-script",
        "console_script",
        "console entrypoint",
        "console-entrypoint",
        "console_entrypoint",
        "entry point",
        "entry-point",
        "entry_point",
        "entry points",
        "entry-points",
        "entry_points",
        "where is the source",
        "where-is-the-source",
        "where_is_the_source",
        "where is the implementation",
        "where-is-the-implementation",
        "where_is_the_implementation",
        "where is implementation",
        "where-is-implementation",
        "where_is_implementation",
        "implementation",
        "runtime package",
        "runtime-package",
        "runtime_package",
        "package metadata",
        "package-metadata",
        "package_metadata",
        "pyproject",
        "makefile",
        "test files",
        "test-files",
        "test_files",
        "where are scripts",
        "where-are-scripts",
        "where_are_scripts",
        "script list",
        "script-list",
        "script_list",
        "scripts",
        "command implementation",
        "command-implementation",
        "command_implementation",
        "where is the cli",
        "where-is-the-cli",
        "where_is_the_cli",
        "where are commands defined",
        "where-are-commands-defined",
        "where_are_commands_defined",
        "where are the commands defined",
        "where-are-the-commands-defined",
        "where_are_the_commands_defined",
        "where is cli implemented",
        "where-is-cli-implemented",
        "where_is_cli_implemented",
        "where is the cli implemented",
        "where-is-the-cli-implemented",
        "where_is_the_cli_implemented",
        "how is the cli wired",
        "how-is-the-cli-wired",
        "how_is_the_cli_wired",
        "authority boundary",
        "authority-boundary",
        "authority_boundary",
        "authority boundaries",
        "authority-boundaries",
        "authority_boundaries",
        "what are the authority boundaries",
        "what-are-the-authority-boundaries",
        "what_are_the_authority_boundaries",
        "what is not allowed",
        "what-is-not-allowed",
        "what_is_not_allowed",
        "what is not authorized",
        "what-is-not-authorized",
        "what_is_not_authorized",
        "what does this not prove",
        "what-does-this-not-prove",
        "what_does_this_not_prove",
        "what does this not authorize",
        "what-does-this-not-authorize",
        "what_does_this_not_authorize",
        "can i publish this",
        "can-i-publish-this",
        "can_i_publish_this",
        "can this be published",
        "can-this-be-published",
        "can_this_be_published",
        "can i share this",
        "can-i-share-this",
        "can_i_share_this",
        "can this be shared",
        "can-this-be-shared",
        "can_this_be_shared",
        "standalone export",
        "standalone-export",
        "standalone_export",
        "release export",
        "release-export",
        "release_export",
        "export artifact",
        "export-artifact",
        "export_artifact",
        "sharing boundary",
        "sharing-boundary",
        "sharing_boundary",
        "publication authority",
        "publication-authority",
        "publication_authority",
        "release authority",
        "release-authority",
        "release_authority",
        "release ready",
        "release-ready",
        "release_ready",
        "is this release ready",
        "is-this-release-ready",
        "is_this_release_ready",
        "is release authorized",
        "is-release-authorized",
        "is_release_authorized",
        "release authorized",
        "release-authorized",
        "release_authorized",
        "is publication authorized",
        "is-publication-authorized",
        "is_publication_authorized",
        "publication authorized",
        "publication-authorized",
        "publication_authorized",
        "production ready",
        "production-ready",
        "production_ready",
        "can i deploy this",
        "can-i-deploy-this",
        "can_i_deploy_this",
        "deploy this",
        "deploy-this",
        "deploy_this",
        "can this be hosted",
        "can-this-be-hosted",
        "can_this_be_hosted",
        "hosted service",
        "hosted-service",
        "hosted_service",
        "host this",
        "host-this",
        "host_this",
        "is this a hosted service",
        "is-this-a-hosted-service",
        "is_this_a_hosted_service",
        "does this call providers",
        "does-this-call-providers",
        "does_this_call_providers",
        "provider calls",
        "provider-calls",
        "provider_calls",
        "does this use credentials",
        "does-this-use-credentials",
        "does_this_use_credentials",
        "credential boundary",
        "credential-boundary",
        "credential_boundary",
        "secret boundary",
        "secret-boundary",
        "secret_boundary",
        "private data",
        "private-data",
        "private_data",
        "private root equivalence",
        "private-root-equivalence",
        "private_root_equivalence",
        "does this prove the system",
        "does-this-prove-the-system",
        "does_this_prove_the_system",
        "whole system correctness",
        "whole-system-correctness",
        "whole_system_correctness",
        "benchmark score",
        "benchmark-score",
        "benchmark_score",
        "does this prove agent capability",
        "does-this-prove-agent-capability",
        "does_this_prove_agent_capability",
        "source boundary",
        "source-boundary",
        "source_boundary",
        "source mutation",
        "source-mutation",
        "source_mutation",
        "source mutation ceiling",
        "source-mutation-ceiling",
        "source_mutation_ceiling",
        "what can i mutate",
        "what-can-i-mutate",
        "what_can_i_mutate",
        "source mutation check",
        "source-mutation-check",
        "source_mutation_check",
        "source files mutated",
        "source-files-mutated",
        "source_files_mutated",
        "mutation check",
        "mutation-check",
        "mutation_check",
        "does this mutate source",
        "does-this-mutate-source",
        "does_this_mutate_source",
        "does microcosm mutate source",
        "does-microcosm-mutate-source",
        "does_microcosm_mutate_source",
        "will this mutate source",
        "will-this-mutate-source",
        "will_this_mutate_source",
        "will microcosm mutate source",
        "will-microcosm-mutate-source",
        "will_microcosm_mutate_source",
        "does this change source files",
        "does-this-change-source-files",
        "does_this_change_source_files",
        "will this change source files",
        "will-this-change-source-files",
        "will_this_change_source_files",
    }:
        return "authority-boundary"
    if value in {
        "navigation",
        "navigate",
        "navigating",
        "routes",
        "route map",
        "route-map",
        "route_map",
        "docs",
        "documentation",
        "show docs",
        "show-docs",
        "show_docs",
        "show documentation",
        "show-documentation",
        "show_documentation",
        "show me docs",
        "show-me-docs",
        "show_me_docs",
        "show me documentation",
        "show-me-documentation",
        "show_me_documentation",
        "show me navigation",
        "show-me-navigation",
        "show_me_navigation",
        "show me the navigation",
        "show-me-the-navigation",
        "show_me_the_navigation",
        "show me routes",
        "show-me-routes",
        "show_me_routes",
        "show me the routes",
        "show-me-the-routes",
        "show_me_the_routes",
        "what routes exist",
        "what-routes-exist",
        "what_routes_exist",
        "show route classes",
        "show-route-classes",
        "show_route_classes",
        "show me task classes",
        "show-me-task-classes",
        "show_me_task_classes",
        "task classes",
        "task-classes",
        "task_classes",
        "command map",
        "command-map",
        "command_map",
        "show command map",
        "show-command-map",
        "show_command_map",
        "show me command map",
        "show-me-command-map",
        "show_me_command_map",
        "show me the command map",
        "show-me-the-command-map",
        "show_me_the_command_map",
        "how do i find the right command",
        "how-do-i-find-the-right-command",
        "how_do_i_find_the_right_command",
        "how do i find the right route",
        "how-do-i-find-the-right-route",
        "how_do_i_find_the_right_route",
        "show me route map",
        "show-me-route-map",
        "show_me_route_map",
        "show me the route map",
        "show-me-the-route-map",
        "show_me_the_route_map",
        "how do i navigate this",
        "how-do-i-navigate-this",
        "how_do_i_navigate_this",
        "how do i navigate",
        "how-do-i-navigate",
        "how_do_i_navigate",
        "where are the docs",
        "where-are-the-docs",
        "where_are_the_docs",
        "where is the documentation",
        "where-is-the-documentation",
        "where_is_the_documentation",
    }:
        return "navigation"
    if value in {
        "frontend",
        "front-end",
        "front_end",
        "ui",
        "web ui",
        "web-ui",
        "web_ui",
        "browser ui",
        "browser-ui",
        "browser_ui",
        "web view",
        "web-view",
        "web_view",
        "local web view",
        "local-web-view",
        "local_web_view",
        "run web ui",
        "run-web-ui",
        "run_web_ui",
        "open the ui",
        "open-the-ui",
        "open_the_ui",
        "show ui",
        "show-ui",
        "show_ui",
        "show me ui",
        "show-me-ui",
        "show_me_ui",
        "show me the ui",
        "show-me-the-ui",
        "show_me_the_ui",
        "browser",
        "browser surface",
        "browser-surface",
        "browser_surface",
        "open browser",
        "open-browser",
        "open_browser",
        "open in browser",
        "open-in-browser",
        "open_in_browser",
        "view in browser",
        "view-in-browser",
        "view_in_browser",
        "show me browser",
        "show-me-browser",
        "show_me_browser",
        "local server",
        "local-server",
        "local_server",
        "serve",
        "serve locally",
        "serve-locally",
        "serve_locally",
        "start server",
        "start-server",
        "start_server",
        "start local server",
        "start-local-server",
        "start_local_server",
        "serve max requests",
        "serve-max-requests",
        "serve_max_requests",
        "serve port",
        "serve-port",
        "serve_port",
        "serve docs",
        "serve-docs",
        "serve_docs",
        "local observatory",
        "local-observatory",
        "local_observatory",
        "observatory",
        "open observatory",
        "open-observatory",
        "open_observatory",
        "observatory endpoint",
        "observatory-endpoint",
        "observatory_endpoint",
        "observatory status",
        "observatory-status",
        "observatory_status",
        "localhost",
        "localhost status",
        "localhost-status",
        "localhost_status",
        "localhost endpoint",
        "localhost-endpoint",
        "localhost_endpoint",
        "project status endpoint",
        "project-status-endpoint",
        "project_status_endpoint",
        "status endpoint",
        "status-endpoint",
        "status_endpoint",
        "served status",
        "served-status",
        "served_status",
        "served status smoke",
        "served-status-smoke",
        "served_status_smoke",
        "html pages",
        "html-pages",
        "html_pages",
        "html surface",
        "html-surface",
        "html_surface",
        "workingness endpoint",
        "workingness-endpoint",
        "workingness_endpoint",
        "max requests",
        "max-requests",
        "max_requests",
        "which port",
        "which-port",
        "which_port",
        "how do i view it",
        "how-do-i-view-it",
        "how_do_i_view_it",
        "how do i open it",
        "how-do-i-open-it",
        "how_do_i_open_it",
        "does it have a ui",
        "does-it-have-a-ui",
        "does_it_have_a_ui",
        "macos app",
        "macos-app",
        "macos_app",
        "macos capsule",
        "macos-capsule",
        "macos_capsule",
        "mac app",
        "mac-app",
        "mac_app",
    }:
        return "frontend"
    if value in {
        "red-teaming",
        "red_teaming",
        "red team evals",
        "red-team-evals",
        "red_team_evals",
        "red team evaluations",
        "red-team-evaluations",
        "red_team_evaluations",
        "show me red team evals",
        "show-me-red-team-evals",
        "show_me_red_team_evals",
        "scheming",
        "show me scheming",
        "show-me-scheming",
        "show_me_scheming",
        "sabotage",
        "show me sabotage",
        "show-me-sabotage",
        "show_me_sabotage",
        "monitoring",
        "agent monitoring",
        "agent-monitoring",
        "agent_monitoring",
        "monitoring evals",
        "monitoring-evals",
        "monitoring_evals",
        "monitor evals",
        "monitor-evals",
        "monitor_evals",
        "scheming monitor",
        "scheming-monitor",
        "scheming_monitor",
        "sabotage monitor",
        "sabotage-monitor",
        "sabotage_monitor",
    }:
        return "red-teaming"
    if value in {
        "agent-evaluation",
        "agent_evaluation",
        "benchmark",
        "benchmarks",
        "benchmark integrity",
        "benchmark-integrity",
        "benchmark_integrity",
        "show me benchmark integrity",
        "show-me-benchmark-integrity",
        "show_me_benchmark_integrity",
        "show me the benchmark integrity",
        "show-me-the-benchmark-integrity",
        "show_me_the_benchmark_integrity",
        "how do i evaluate agents",
        "how-do-i-evaluate-agents",
        "how_do_i_evaluate_agents",
        "show me benchmarks",
        "show-me-benchmarks",
        "show_me_benchmarks",
        "show me evals",
        "show-me-evals",
        "show_me_evals",
        "eval harness",
        "eval-harness",
        "eval_harness",
        "evaluation harness",
        "evaluation-harness",
        "evaluation_harness",
        "swe-bench",
        "swe_bench",
        "swe bench",
        "agent evals",
        "agent-evals",
        "agent_evals",
        "agent evaluation",
    }:
        return "agent-evaluation"
    if value in {
        "ai-safety",
        "ai_safety",
        "safety",
        "agent safety",
        "agent-safety",
        "agent_safety",
        "safety evals",
        "safety-evals",
        "safety_evals",
        "evals",
        "show safety",
        "show-safety",
        "show_safety",
        "show me safety",
        "show-me-safety",
        "show_me_safety",
        "show me safety parts",
        "show-me-safety-parts",
        "show_me_safety_parts",
        "show me the safety parts",
        "show-me-the-safety-parts",
        "show_me_the_safety_parts",
        "safety parts",
        "safety-parts",
        "safety_parts",
        "reviewer",
        "skeptical review",
        "skeptical-review",
        "skeptical_review",
        "skeptical reviewer",
        "skeptical_reviewer",
        "skeptical-reviewer",
        "ai safety",
        "ai safety evals",
        "ai-safety-evals",
        "ai_safety_evals",
        "security evals",
        "security-evals",
        "security_evals",
        "ai safety parts",
        "ai-safety-parts",
        "ai_safety_parts",
        "show me safety evals",
        "show-me-safety-evals",
        "show_me_safety_evals",
        "show me agent safety",
        "show-me-agent-safety",
        "show_me_agent_safety",
        "where is ai safety",
        "where-is-ai-safety",
        "where_is_ai_safety",
        "what are the ai safety parts",
        "what-are-the-ai-safety-parts",
        "what_are_the_ai_safety_parts",
        "show me ai safety",
        "show me the ai safety",
        "show me ai safety parts",
        "show me the ai safety parts",
        "show me ai safety stuff",
        "show-me-ai-safety",
        "show-me-the-ai-safety",
        "show-me-ai-safety-parts",
        "show-me-the-ai-safety-parts",
        "show-me-ai-safety-stuff",
        "show_me_ai_safety",
        "show_me_the_ai_safety",
        "show_me_ai_safety_parts",
        "show_me_the_ai_safety_parts",
        "show_me_ai_safety_stuff",
        "show me ai-safety",
        "show me the ai-safety",
        "show me ai-safety parts",
        "show me the ai-safety parts",
        "show me ai-safety stuff",
        "alignment",
        "alignment evaluation",
        "alignment-evaluation",
        "alignment_evaluation",
        "alignment parts",
        "alignment-parts",
        "alignment_parts",
        "show me alignment",
        "show-me-alignment",
        "show_me_alignment",
        "show me alignment parts",
        "show-me-alignment-parts",
        "show_me_alignment_parts",
        "ml",
        "machine learning",
        "machine-learning",
        "machine_learning",
        "model safety",
        "model-safety",
        "model_safety",
        "show me ml",
        "show-me-ml",
        "show_me_ml",
        "show me ai parts",
        "show-me-ai-parts",
        "show_me_ai_parts",
        "show me machine learning parts",
        "show-me-machine-learning-parts",
        "show_me_machine_learning_parts",
    }:
        return "ai-safety"
    if value in {
        "security",
        "secure",
        "security parts",
        "security-parts",
        "security_parts",
        "secret scan",
        "secret-scan",
        "secret_scan",
        "secrets scan",
        "secrets-scan",
        "secrets_scan",
        "credential scan",
        "credential-scan",
        "credential_scan",
        "credentials scan",
        "credentials-scan",
        "credentials_scan",
        "private path scan",
        "private-path scan",
        "private_path scan",
        "private path-scan",
        "private-path-scan",
        "private_path_scan",
        "private paths scan",
        "private-paths-scan",
        "private_paths_scan",
        "private state scan",
        "private-state-scan",
        "private_state_scan",
        "stripping guard",
        "stripping-guard",
        "stripping_guard",
        "show me security",
        "show-me-security",
        "show_me_security",
        "show me the security",
        "show-me-the-security",
        "show_me_the_security",
        "show me security parts",
        "show-me-security-parts",
        "show_me_security_parts",
        "show me the security parts",
        "show-me-the-security-parts",
        "show_me_the_security_parts",
        "sandbox",
        "sandbox parts",
        "sandbox-parts",
        "sandbox_parts",
        "show me sandbox",
        "show-me-sandbox",
        "show_me_sandbox",
        "show me sandbox parts",
        "show-me-sandbox-parts",
        "show_me_sandbox_parts",
        "memory poisoning",
        "memory-poisoning",
        "memory_poisoning",
        "show me memory poisoning",
        "show-me-memory-poisoning",
        "show_me_memory_poisoning",
        "prompt injection",
        "prompt-injection",
        "prompt_injection",
        "show me prompt injection",
        "show-me-prompt-injection",
        "show_me_prompt_injection",
        "is this safe",
        "is-this-safe",
        "is_this_safe",
        "is this secure",
        "is-this-secure",
        "is_this_secure",
        "security review",
        "security-review",
        "security_review",
        "red team",
        "red-team",
        "red_team",
        "red teaming",
        "red-teaming",
        "red_teaming",
    }:
        return "security"
    if value in {
        "compliance",
        "compliant",
        "show me compliance",
        "show-me-compliance",
        "show_me_compliance",
        "show me the compliance",
        "show-me-the-compliance",
        "show_me_the_compliance",
        "is this compliant",
        "is-this-compliant",
        "is_this_compliant",
        "compliance review",
        "compliance-review",
        "compliance_review",
    }:
        return "compliance"
    if value in {
        "evaluate",
        "evaluation",
        "evaluating",
        "evaluate it",
        "evaluate-it",
        "evaluate_it",
        "evaluate this repo",
        "evaluate-this-repo",
        "evaluate_this_repo",
        "review this",
        "review-this",
        "review_this",
        "what are the risks",
        "what-are-the-risks",
        "what_are_the_risks",
        "what risks exist",
        "what-risks-exist",
        "what_risks_exist",
        "what is broken",
        "what-is-broken",
        "what_is_broken",
        "what fails",
        "what-fails",
        "what_fails",
        "failure modes",
        "failure-modes",
        "failure_modes",
        "show me failure modes",
        "show-me-failure-modes",
        "show_me_failure_modes",
        "known gaps",
        "known-gaps",
        "known_gaps",
        "show me known gaps",
        "show-me-known-gaps",
        "show_me_known_gaps",
        "gaps",
        "limitations",
        "what are the limitations",
        "what-are-the-limitations",
        "what_are_the_limitations",
        "what limitations exist",
        "what-limitations-exist",
        "what_limitations_exist",
        "what are the caveats",
        "what-are-the-caveats",
        "what_are_the_caveats",
        "what caveats exist",
        "what-caveats-exist",
        "what_caveats_exist",
        "what claims are refused",
        "what-claims-are-refused",
        "what_claims_are_refused",
        "what claims does this repo refuse",
        "what-claims-does-this-repo-refuse",
        "what_claims_does_this_repo_refuse",
        "release boundaries",
        "release-boundaries",
        "release_boundaries",
        "show release boundaries",
        "show-release-boundaries",
        "show_release_boundaries",
        "show me release boundaries",
        "show-me-release-boundaries",
        "show_me_release_boundaries",
        "show me the release boundaries",
        "show-me-the-release-boundaries",
        "show_me_the_release_boundaries",
        "show me claim ceilings",
        "show-me-claim-ceilings",
        "show_me_claim_ceilings",
        "claim ceilings",
        "claim-ceilings",
        "claim_ceilings",
        "what is the public floor",
        "what-is-the-public-floor",
        "what_is_the_public_floor",
        "show me public floor",
        "show-me-public-floor",
        "show_me_public_floor",
        "show me the public floor",
        "show-me-the-public-floor",
        "show_me_the_public_floor",
        "public floor",
        "public-floor",
        "public_floor",
        "what is the verification floor",
        "what-is-the-verification-floor",
        "what_is_the_verification_floor",
        "public verification floor",
        "public-verification-floor",
        "public_verification_floor",
        "show me verification floor",
        "show-me-verification-floor",
        "show_me_verification_floor",
        "show me the verification floor",
        "show-me-the-verification-floor",
        "show_me_the_verification_floor",
        "verification floor",
        "verification-floor",
        "verification_floor",
        "is this safe to publish",
        "is-this-safe-to-publish",
        "is_this_safe_to_publish",
        "is this production ready",
        "is-this-production-ready",
        "is_this_production_ready",
        "is this production-ready",
        "how do i evaluate it",
        "how-do-i-evaluate-it",
        "how_do_i_evaluate_it",
        "how can i evaluate it",
        "how-can-i-evaluate-it",
        "how_can_i_evaluate_it",
        "how do i evaluate this",
        "how-do-i-evaluate-this",
        "how_do_i_evaluate_this",
        "how can i evaluate this",
        "how-can-i-evaluate-this",
        "how_can_i_evaluate_this",
        "how to evaluate",
        "how-to-evaluate",
        "how_to_evaluate",
        "check",
        "checks",
        "check this",
        "check-this",
        "check_this",
        "check the repo",
        "check-the-repo",
        "check_the_repo",
        "how do i check it",
        "how-do-i-check-it",
        "how_do_i_check_it",
        "test",
        "tests",
        "show me checks",
        "show-me-checks",
        "show_me_checks",
        "what checks can i run",
        "what-checks-can-i-run",
        "what_checks_can_i_run",
        "what checks should i run",
        "what-checks-should-i-run",
        "what_checks_should_i_run",
        "run checks",
        "run-checks",
        "run_checks",
        "run check",
        "run-check",
        "run_check",
        "preflight",
        "run preflight",
        "run-preflight",
        "run_preflight",
        "verify",
        "verify this",
        "verify-this",
        "verify_this",
        "verification",
        "validate",
        "validation",
        "ci",
        "pytest",
        "make check",
        "make-check",
        "make_check",
        "make validate",
        "make-validate",
        "make_validate",
        "validate repo",
        "validate-repo",
        "validate_repo",
        "run tests",
        "run-tests",
        "run_tests",
        "test this repo",
        "test-this-repo",
        "test_this_repo",
        "where are the tests",
        "where-are-the-tests",
        "where_are_the_tests",
        "where are tests",
        "where-are-tests",
        "where_are_tests",
        "test suite",
        "test-suite",
        "test_suite",
        "test it",
        "test-it",
        "test_it",
        "test this",
        "test-this",
        "test_this",
        "how do i test it",
        "how-do-i-test-it",
        "how_do_i_test_it",
        "what tests should i run",
        "what-tests-should-i-run",
        "what_tests_should_i_run",
        "smoke test",
        "smoke-test",
        "smoke_test",
        "smoke",
        "smoke path",
        "smoke-path",
        "smoke_path",
        "smoke checks",
        "smoke-checks",
        "smoke_checks",
        "run smoke checks",
        "run-smoke-checks",
        "run_smoke_checks",
        "run smoke test",
        "run-smoke-test",
        "run_smoke_test",
        "make smoke",
        "make-smoke",
        "make_smoke",
        "make ci",
        "make-ci",
        "make_ci",
        "make test",
        "make-test",
        "make_test",
        "github actions",
        "github-actions",
        "github_actions",
        "github actions floor",
        "github-actions-floor",
        "github_actions_floor",
        "run ci",
        "run-ci",
        "run_ci",
        "ci check",
        "ci-check",
        "ci_check",
        "run make ci",
        "run-make-ci",
        "run_make_ci",
        "what does make ci do",
        "what-does-make-ci-do",
        "what_does_make_ci_do",
        "run test",
        "run-test",
        "run_test",
        "how do i run checks",
        "how-do-i-run-checks",
        "how_do_i_run_checks",
        "how do i run tests",
        "how-do-i-run-tests",
        "how_do_i_run_tests",
        "how can i run checks",
        "how-can-i-run-checks",
        "how_can_i_run_checks",
        "how can i run tests",
        "how-can-i-run-tests",
        "how_can_i_run_tests",
        "verify this repo",
        "verify-this-repo",
        "verify_this_repo",
        "verify repo",
        "verify-repo",
        "verify_repo",
        "verify the repo",
        "verify-the-repo",
        "verify_the_repo",
        "verify public floor",
        "verify-public-floor",
        "verify_public_floor",
        "how do i run the checks",
        "how-do-i-run-the-checks",
        "how_do_i_run_the_checks",
        "how do i run the tests",
        "how-do-i-run-the-tests",
        "how_do_i_run_the_tests",
        "how can i run the checks",
        "how-can-i-run-the-checks",
        "how_can_i_run_the_checks",
        "how can i run the tests",
        "how-can-i-run-the-tests",
        "how_can_i_run_the_tests",
        "run the checks",
        "run-the-checks",
        "run_the_checks",
        "run the tests",
        "run-the-tests",
        "run_the_tests",
        "what should pass",
        "what-should-pass",
        "what_should_pass",
        "what is green",
        "what-is-green",
        "what_is_green",
        "green floor",
        "green-floor",
        "green_floor",
        "public green floor",
        "public-green-floor",
        "public_green_floor",
        "what commands prove it runs",
        "what-commands-prove-it-runs",
        "what_commands_prove_it_runs",
        "how do i know it works",
        "how-do-i-know-it-works",
        "how_do_i_know_it_works",
        "does it pass tests",
        "does-it-pass-tests",
        "does_it_pass_tests",
        "what is the test floor",
        "what-is-the-test-floor",
        "what_is_the_test_floor",
        "full test floor",
        "full-test-floor",
        "full_test_floor",
        "public test floor",
        "public-test-floor",
        "public_test_floor",
        "source form smoke",
        "source-form-smoke",
        "source_form_smoke",
        "package install smoke",
        "package-install-smoke",
        "package_install_smoke",
        "make package smoke",
        "make-package-smoke",
        "make_package_smoke",
        "run smoke",
        "run-smoke",
        "run_smoke",
        "flight recorder",
        "flight-recorder",
        "flight_recorder",
        "skeptic flight recorder",
        "skeptic-flight-recorder",
        "skeptic_flight_recorder",
        "make flight recorder",
        "make-flight-recorder",
        "make_flight_recorder",
        "verify flight recorder",
        "verify-flight-recorder",
        "verify_flight_recorder",
        "flight recorder verify",
        "flight-recorder-verify",
        "flight_recorder_verify",
        "proof packet",
        "proof-packet",
        "proof_packet",
        "reviewer proof packet",
        "reviewer-proof-packet",
        "reviewer_proof_packet",
        "replay packet",
        "replay-packet",
        "replay_packet",
        "command transcript",
        "command-transcript",
        "command_transcript",
        "output digests",
        "output-digests",
        "output_digests",
        "how do i test this",
        "how-do-i-test-this",
        "how_do_i_test_this",
        "receipt",
        "receipts",
        "what is a receipt",
        "what-is-a-receipt",
        "what_is_a_receipt",
        "show me receipts",
        "show-me-receipts",
        "show_me_receipts",
        "show me the receipts",
        "show-me-the-receipts",
        "show_me_the_receipts",
        "show receipt index",
        "show-receipt-index",
        "show_receipt_index",
        "what receipts exist",
        "what-receipts-exist",
        "what_receipts_exist",
        "receipt index",
        "receipt-index",
        "receipt_index",
        "what are receipts",
        "what-are-receipts",
        "what_are_receipts",
        "where are receipts",
        "where-are-receipts",
        "where_are_receipts",
        "where are the receipts",
        "where-are-the-receipts",
        "where_are_the_receipts",
        "what do receipts mean",
        "what-do-receipts-mean",
        "what_do_receipts_mean",
        "receipts meaning",
        "receipts-meaning",
        "receipts_meaning",
        "what does this receipt mean",
        "what-does-this-receipt-mean",
        "what_does_this_receipt_mean",
        "what do the receipts mean",
        "what-do-the-receipts-mean",
        "what_do_the_receipts_mean",
        "what do these receipts mean",
        "what-do-these-receipts-mean",
        "what_do_these_receipts_mean",
        "what do receipts prove",
        "what-do-receipts-prove",
        "what_do_receipts_prove",
        "what do the receipts prove",
        "what-do-the-receipts-prove",
        "what_do_the_receipts_prove",
        "what don't receipts prove",
        "what-don't-receipts-prove",
        "what_don't_receipts_prove",
        "what dont receipts prove",
        "what-dont-receipts-prove",
        "what_dont_receipts_prove",
        "do receipts prove correctness",
        "do-receipts-prove-correctness",
        "do_receipts_prove_correctness",
        "proof vs receipt",
        "proof-vs-receipt",
        "proof_vs_receipt",
        "receipt vs proof",
        "receipt-vs-proof",
        "receipt_vs_proof",
        "receipts vs proof",
        "receipts-vs-proof",
        "receipts_vs_proof",
        "are receipts proofs",
        "are-receipts-proofs",
        "are_receipts_proofs",
        "are receipts proof",
        "are-receipts-proof",
        "are_receipts_proof",
        "which receipts matter",
        "which-receipts-matter",
        "which_receipts_matter",
        "receipt authority",
        "receipt-authority",
        "receipt_authority",
        "authority receipts",
        "authority-receipts",
        "authority_receipts",
        "receipts authority",
        "receipts-authority",
        "receipts_authority",
        "receipt limits",
        "receipt-limits",
        "receipt_limits",
        "receipt limitations",
        "receipt-limitations",
        "receipt_limitations",
        "receipt caveats",
        "receipt-caveats",
        "receipt_caveats",
        "receipt replay",
        "receipt-replay",
        "receipt_replay",
        "replay receipts",
        "replay-receipts",
        "replay_receipts",
        "receipt verify",
        "receipt-verify",
        "receipt_verify",
        "verify receipts",
        "verify-receipts",
        "verify_receipts",
        "receipt drilldown",
        "receipt-drilldown",
        "receipt_drilldown",
        "drilldown receipts",
        "drilldown-receipts",
        "drilldown_receipts",
        "drill into receipts",
        "drill-into-receipts",
        "drill_into_receipts",
        "how do i inspect receipts",
        "how-do-i-inspect-receipts",
        "how_do_i_inspect_receipts",
        "how do i inspect evidence",
        "how-do-i-inspect-evidence",
        "how_do_i_inspect_evidence",
        "inspect receipts",
        "inspect-receipts",
        "inspect_receipts",
        "inspect a receipt",
        "inspect-a-receipt",
        "inspect_a_receipt",
        "inspect receipt",
        "inspect-receipt",
        "inspect_receipt",
        "open a receipt",
        "open-a-receipt",
        "open_a_receipt",
        "read a receipt",
        "read-a-receipt",
        "read_a_receipt",
        "open raw receipts",
        "open-raw-receipts",
        "open_raw_receipts",
        "raw receipts",
        "raw-receipts",
        "raw_receipts",
        "command receipts",
        "command-receipts",
        "command_receipts",
        "evidence receipt",
        "evidence-receipt",
        "evidence_receipt",
        "receipt evidence",
        "receipt-evidence",
        "receipt_evidence",
        "explain receipts",
        "explain-receipts",
        "explain_receipts",
        "explain the receipts",
        "explain-the-receipts",
        "explain_the_receipts",
        "explain receipt",
        "explain-receipt",
        "explain_receipt",
        "explain this receipt",
        "explain-this-receipt",
        "explain_this_receipt",
        "what does the evidence mean",
        "what-does-the-evidence-mean",
        "what_does_the_evidence_mean",
        "evidence",
        "what is evidence",
        "what-is-evidence",
        "what_is_evidence",
        "evidence index",
        "evidence-index",
        "evidence_index",
        "show evidence",
        "show-evidence",
        "show_evidence",
        "show me evidence",
        "show-me-evidence",
        "show_me_evidence",
        "evidence list",
        "evidence-list",
        "evidence_list",
        "list evidence",
        "list-evidence",
        "list_evidence",
        "evidence inspect",
        "evidence-inspect",
        "evidence_inspect",
        "inspect evidence",
        "inspect-evidence",
        "inspect_evidence",
        "evidence drilldown",
        "evidence-drilldown",
        "evidence_drilldown",
        "drilldown evidence",
        "drilldown-evidence",
        "drilldown_evidence",
        "are receipts authority",
        "are-receipts-authority",
        "are_receipts_authority",
        "what does status pass mean",
        "what-does-status-pass-mean",
        "what_does_status_pass_mean",
        "what does evidence pass mean",
        "what-does-evidence-pass-mean",
        "what_does_evidence_pass_mean",
        "what does a receipt prove",
        "what-does-a-receipt-prove",
        "what_does_a_receipt_prove",
        "bounded receipt index",
        "bounded-receipt-index",
        "bounded_receipt_index",
        "receipt refs",
        "receipt-refs",
        "receipt_refs",
        "evidence refs",
        "evidence-refs",
        "evidence_refs",
        "evidence handles",
        "evidence-handles",
        "evidence_handles",
        "what backs this",
        "what-backs-this",
        "what_backs_this",
        "what backs this claim",
        "what-backs-this-claim",
        "what_backs_this_claim",
        "what backs each claim",
        "what-backs-each-claim",
        "what_backs_each_claim",
        "what backs the claims",
        "what-backs-the-claims",
        "what_backs_the_claims",
        "what evidence backs this",
        "what-evidence-backs-this",
        "what_evidence_backs_this",
        "audit trail",
        "audit-trail",
        "audit_trail",
        "blocked evidence",
        "blocked-evidence",
        "blocked_evidence",
        "blocked command evidence",
        "blocked-command-evidence",
        "blocked_command_evidence",
        "nonzero command",
        "nonzero-command",
        "nonzero_command",
        "non-zero command",
        "non-zero-command",
        "non_zero_command",
        "output digest proof",
        "output-digest-proof",
        "output_digest_proof",
        "source modules evidence",
        "source-modules-evidence",
        "source_modules_evidence",
        "body import receipts",
        "body-import-receipts",
        "body_import_receipts",
        "show receipts",
        "show-receipts",
        "show_receipts",
        "show me the evidence",
        "show-me-the-evidence",
        "show_me_the_evidence",
        "what counts as evidence",
        "what-counts-as-evidence",
        "what_counts_as_evidence",
        "evidence classes",
        "evidence-classes",
        "evidence_classes",
        "evidence class",
        "evidence-class",
        "evidence_class",
        "what is evidence class",
        "what-is-evidence-class",
        "what_is_evidence_class",
        "what are evidence classes",
        "what-are-evidence-classes",
        "what_are_evidence_classes",
        "where is evidence",
        "where-is-evidence",
        "where_is_evidence",
        "where is the evidence",
        "where-is-the-evidence",
        "where_is_the_evidence",
        "explain evidence",
        "explain-evidence",
        "explain_evidence",
        "explain the evidence",
        "explain-the-evidence",
        "explain_the_evidence",
        "receipt meaning",
        "receipt-meaning",
        "receipt_meaning",
        "receipt boundary",
        "receipt-boundary",
        "receipt_boundary",
        "evidence meaning",
        "evidence-meaning",
        "evidence_meaning",
        "black box recorder",
        "black-box-recorder",
        "black_box_recorder",
    }:
        return "evaluation"
    if value in {
        "interesting",
        "interesting-parts",
        "interesting_parts",
        "demo",
        "show me demo",
        "show-me-demo",
        "show_me_demo",
        "show me a demo",
        "show-me-a-demo",
        "show_me_a_demo",
        "tour",
        "tour me",
        "tour-me",
        "tour_me",
        "walkthrough",
        "show me walkthrough",
        "show-me-walkthrough",
        "show_me_walkthrough",
        "show interesting parts",
        "show-interesting-parts",
        "show_interesting_parts",
        "show-me-interesting-stuff",
        "show_me_interesting_stuff",
        "show me interesting stuff",
        "show me something interesting",
        "show-me-something-interesting",
        "show_me_something_interesting",
        "show-me-interesting-parts",
        "show_me_interesting_parts",
        "show me interesting parts",
        "show me the interesting parts",
        "show-me-the-interesting-parts",
        "show_me_the_interesting_parts",
        "what are the interesting parts",
        "what-are-the-interesting-parts",
        "what_are_the_interesting_parts",
        "what is interesting",
        "what-is-interesting",
        "what_is_interesting",
        "what's interesting",
        "whats interesting",
        "whats-interesting",
        "whats_interesting",
        "show me interesting things",
        "show-me-interesting-things",
        "show_me_interesting_things",
        "interesting bits",
        "interesting-bits",
        "interesting_bits",
        "interesting stuff",
        "interesting-stuff",
        "interesting_stuff",
        "show me the interesting bits",
        "show-me-the-interesting-bits",
        "show_me_the_interesting_bits",
        "what's cool",
        "whats cool",
        "whats-cool",
        "whats_cool",
        "what is cool here",
        "what-is-cool-here",
        "what_is_cool_here",
        "show me cool parts",
        "cool parts",
        "cool-parts",
        "cool_parts",
        "show-me-cool-parts",
        "show_me_cool_parts",
        "show me the cool parts",
        "show-me-the-cool-parts",
        "show_me_the_cool_parts",
        "what are the cool parts",
        "what-are-the-cool-parts",
        "what_are_the_cool_parts",
        "show me highlights",
        "highlights",
        "highlight parts",
        "highlight-parts",
        "highlight_parts",
        "project highlights",
        "project-highlights",
        "project_highlights",
        "show-me-highlights",
        "show_me_highlights",
        "show highlights",
        "show-highlights",
        "show_highlights",
        "show me the highlights",
        "show-me-the-highlights",
        "show_me_the_highlights",
        "show me notable parts",
        "show-me-notable-parts",
        "show_me_notable_parts",
        "notable parts",
        "notable-parts",
        "notable_parts",
        "show notable parts",
        "show-notable-parts",
        "show_notable_parts",
        "show me the notable parts",
        "show-me-the-notable-parts",
        "show_me_the_notable_parts",
        "what is notable",
        "what-is-notable",
        "what_is_notable",
        "what's notable",
        "whats notable",
        "whats-notable",
        "whats_notable",
        "what is unusual",
        "what-is-unusual",
        "what_is_unusual",
        "what is unusual here",
        "what-is-unusual-here",
        "what_is_unusual_here",
        "what's unusual",
        "whats unusual",
        "whats-unusual",
        "whats_unusual",
        "what is different here",
        "what-is-different-here",
        "what_is_different_here",
        "what's different here",
        "whats different here",
        "whats-different-here",
        "whats_different_here",
        "what makes this useful",
        "what-makes-this-useful",
        "what_makes_this_useful",
        "why should i care",
        "why-should-i-care",
        "why_should_i_care",
        "show me what's interesting",
        "show-me-what's-interesting",
        "show_me_what's_interesting",
        "show me whats interesting",
        "show-me-whats-interesting",
        "show_me_whats_interesting",
        "what is interesting here",
        "what-is-interesting-here",
        "what_is_interesting_here",
        "what's interesting here",
        "whats interesting here",
        "whats-interesting-here",
        "whats_interesting_here",
        "what is worth looking at",
        "what-is-worth-looking-at",
        "what_is_worth_looking_at",
        "worth looking at",
        "worth-looking-at",
        "worth_looking_at",
        "what is worth inspecting",
        "what-is-worth-inspecting",
        "what_is_worth_inspecting",
        "what is worth reading",
        "what-is-worth-reading",
        "what_is_worth_reading",
        "what is worth seeing",
        "what-is-worth-seeing",
        "what_is_worth_seeing",
        "worth seeing",
        "worth-seeing",
        "worth_seeing",
        "why should i look at this",
        "why-should-i-look-at-this",
        "why_should_i_look_at_this",
        "best parts",
        "best-parts",
        "best_parts",
        "crown jewels",
        "crown-jewels",
        "crown_jewels",
        "most interesting parts",
        "most-interesting-parts",
        "most_interesting_parts",
        "most notable parts",
        "most-notable-parts",
        "most_notable_parts",
        "what should i look at",
        "what-should-i-look-at",
        "what_should_i_look_at",
        "what should i look at first",
        "what-should-i-look-at-first",
        "what_should_i_look_at_first",
        "where should i look",
        "where-should-i-look",
        "where_should_i_look",
        "where should i start looking",
        "where-should-i-start-looking",
        "where_should_i_start_looking",
        "what should i read first",
        "what-should-i-read-first",
        "what_should_i_read_first",
        "what should i inspect",
        "what-should-i-inspect",
        "what_should_i_inspect",
        "what should i inspect first",
        "what-should-i-inspect-first",
        "what_should_i_inspect_first",
        "where are the interesting parts",
        "where-are-the-interesting-parts",
        "where_are_the_interesting_parts",
        "where should i start",
        "where-should-i-start",
        "where_should_i_start",
        "which parts matter",
        "which-parts-matter",
        "which_parts_matter",
        "which parts are worth reading",
        "which-parts-are-worth-reading",
        "which_parts_are_worth_reading",
        "show me the good parts",
        "show-me-the-good-parts",
        "show_me_the_good_parts",
        "what stands out",
        "what-stands-out",
        "what_stands_out",
        "tour interesting",
        "tour-interesting",
        "tour_interesting",
        "interesting tour",
        "interesting-tour",
        "interesting_tour",
        "quick tour",
        "quick-tour",
        "quick_tour",
        "demo path",
        "demo-path",
        "demo_path",
        "demo to scale",
        "demo-to-scale",
        "demo_to_scale",
        "observatory bridge",
        "observatory-bridge",
        "observatory_bridge",
        "local demo",
        "local-demo",
        "local_demo",
        "structural scale",
        "structural-scale",
        "structural_scale",
        "proof lab",
        "proof-lab",
        "proof_lab",
        "evidence floor",
        "evidence-floor",
        "evidence_floor",
        "source tour",
        "source-tour",
        "source_tour",
        "repo tour",
        "repo-tour",
        "repo_tour",
        "show me around",
        "show-me-around",
        "show_me_around",
        "show me math finance ai safety formal methods",
        "show-me-math-finance-ai-safety-formal-methods",
        "show_me_math_finance_ai_safety_formal_methods",
        "show me domains",
        "show-me-domains",
        "show_me_domains",
        "domain routes",
        "domain-routes",
        "domain_routes",
        "show me domain routes",
        "show-me-domain-routes",
        "show_me_domain_routes",
        "domain tour",
        "domain-tour",
        "domain_tour",
    }:
        return "interesting-parts"
    if value in {
        "domain specialist",
        "domain-specialist",
        "domain_specialist",
        "show me the domain specialist path",
        "show-me-the-domain-specialist-path",
        "show_me_the_domain_specialist_path",
        "domain expert",
        "domain-expert",
        "domain_expert",
        "specialist",
        "specialists",
        "expert review",
        "expert-review",
        "expert_review",
        "show me specialty",
        "show-me-specialty",
        "show_me_specialty",
        "show me specialties",
        "show-me-specialties",
        "show_me_specialties",
        "show specialties",
        "show-specialties",
        "show_specialties",
        "specialty index",
        "specialty-index",
        "specialty_index",
        "find my specialty",
        "find-my-specialty",
        "find_my_specialty",
        "find your specialty",
        "find-your-specialty",
        "find_your_specialty",
        "which specialty",
        "which-specialty",
        "which_specialty",
        "where are specialties",
        "where-are-specialties",
        "where_are_specialties",
        "research",
        "research science",
        "research-science",
        "research_science",
        "research workflows",
        "research-workflows",
        "research_workflows",
        "research workflow",
        "research-workflow",
        "research_workflow",
        "show research",
        "show-research",
        "show_research",
        "show me research",
        "show-me-research",
        "show_me_research",
        "show me the research",
        "show-me-the-research",
        "show_me_the_research",
        "research parts",
        "research-parts",
        "research_parts",
        "show me research parts",
        "show-me-research-parts",
        "show_me_research_parts",
        "show me the research parts",
        "show-me-the-research-parts",
        "show_me_the_research_parts",
        "show me research workflows",
        "show-me-research-workflows",
        "show_me_research_workflows",
        "science",
        "science parts",
        "science-parts",
        "science_parts",
        "science workflows",
        "science-workflows",
        "science_workflows",
        "science replays",
        "science-replays",
        "science_replays",
        "science replay",
        "science-replay",
        "science_replay",
        "scientific replay",
        "scientific-replay",
        "scientific_replay",
        "scientific replays",
        "scientific-replays",
        "scientific_replays",
        "scientific workflows",
        "scientific-workflows",
        "scientific_workflows",
        "scientific workflow",
        "scientific-workflow",
        "scientific_workflow",
        "show science",
        "show-science",
        "show_science",
        "show me science",
        "show-me-science",
        "show_me_science",
        "show me science parts",
        "show-me-science-parts",
        "show_me_science_parts",
        "show me the science parts",
        "show-me-the-science-parts",
        "show_me_the_science_parts",
        "show me science workflows",
        "show-me-science-workflows",
        "show_me_science_workflows",
        "mechanistic interpretability",
        "mechanistic-interpretability",
        "mechanistic_interpretability",
        "show me mechanistic interpretability",
        "show-me-mechanistic-interpretability",
        "show_me_mechanistic_interpretability",
        "replication",
        "replication rubric",
        "replication-rubric",
        "replication_rubric",
        "paper replication",
        "paper-replication",
        "paper_replication",
        "research replication",
        "research-replication",
        "research_replication",
        "show me replication",
        "show-me-replication",
        "show_me_replication",
        "show me research replication",
        "show-me-research-replication",
        "show_me_research_replication",
        "show me paper replication",
        "show-me-paper-replication",
        "show_me_paper_replication",
        "chemistry",
        "biology",
        "materials science",
        "materials-science",
        "materials_science",
        "materials chemistry",
        "materials-chemistry",
        "materials_chemistry",
        "materials lab",
        "materials-lab",
        "materials_lab",
        "materials lab safety",
        "materials-lab safety",
        "materials lab-safety",
        "materials-lab-safety",
        "materials_lab_safety",
        "lab safety",
        "lab-safety",
        "lab_safety",
        "closed loop lab",
        "closed-loop-lab",
        "closed_loop_lab",
        "spatial world model",
        "spatial-world-model",
        "spatial_world_model",
        "show me spatial world model",
        "show-me-spatial-world-model",
        "show_me_spatial_world_model",
        "world model",
        "world-model",
        "world_model",
        "spatial simulation",
        "spatial-simulation",
        "spatial_simulation",
        "counterfactual simulation",
        "counterfactual-simulation",
        "counterfactual_simulation",
        "show me counterfactual simulation",
        "show-me-counterfactual-simulation",
        "show_me_counterfactual_simulation",
        "robotics",
        "robotics route",
        "robotics-route",
        "robotics_route",
        "robotics parts",
        "robotics-parts",
        "robotics_parts",
        "prediction reconciliation",
        "prediction-reconciliation",
        "prediction_reconciliation",
        "show me chemistry",
        "show-me-chemistry",
        "show_me_chemistry",
        "show me materials chemistry",
        "show-me-materials-chemistry",
        "show_me_materials_chemistry",
        "show me materials lab safety",
        "show-me-materials-lab-safety",
        "show_me_materials_lab_safety",
        "mech interp",
        "mech-interp",
        "mech_interp",
        "interpretability",
        "show me interpretability",
        "show-me-interpretability",
        "show_me_interpretability",
        "research replay",
        "research-replay",
        "research_replay",
        "research replays",
        "research-replays",
        "research_replays",
        "show me research replays",
        "show-me-research-replays",
        "show_me_research_replays",
        "show me scientific replays",
        "show-me-scientific-replays",
        "show_me_scientific_replays",
    }:
        return "research-workflows"
    if value in {
        "market boundary",
        "market-boundary",
        "market_boundary",
        "show market boundary",
        "show-market-boundary",
        "show_market_boundary",
        "show me market boundary",
        "show-me-market-boundary",
        "show_me_market_boundary",
        "show me the market boundary",
        "show-me-the-market-boundary",
        "show_me_the_market_boundary",
        "market claims",
        "market-claims",
        "market_claims",
        "financial claims",
        "financial-claims",
        "financial_claims",
    }:
        return "market-boundary"
    if value in {
        "audio",
        "audio rms",
        "audio-rms",
        "audio_rms",
        "rms",
        "rms level",
        "rms-level",
        "rms_level",
        "audio level",
        "audio-level",
        "audio_level",
        "audio level rms",
        "audio-level-rms",
        "audio_level_rms",
        "audio level rms port",
        "audio-level-rms-port",
        "audio_level_rms_port",
    }:
        return "audio"
    if value in {
        "finance",
        "financial",
        "forecast",
        "forecasts",
        "forecasting",
        "forecasting workflows",
        "forecasting-workflows",
        "forecasting_workflows",
        "forecast eval",
        "forecast-eval",
        "forecast_eval",
        "forecast evaluation",
        "forecast-evaluation",
        "forecast_evaluation",
        "finance eval",
        "finance-eval",
        "finance_eval",
        "finance eval spine",
        "finance-eval-spine",
        "finance_eval_spine",
        "finance forecast evaluation spine",
        "finance-forecast-evaluation-spine",
        "finance_forecast_evaluation_spine",
        "forecast spine",
        "forecast-spine",
        "forecast_spine",
        "price forecast",
        "price-forecast",
        "price_forecast",
        "where are forecasts",
        "where-are-forecasts",
        "where_are_forecasts",
        "show forecasts",
        "show-forecasts",
        "show_forecasts",
        "forecast receipts",
        "forecast-receipts",
        "forecast_receipts",
        "finance receipts",
        "finance-receipts",
        "finance_receipts",
        "forecast reconciliation",
        "forecast-reconciliation",
        "forecast_reconciliation",
        "calibration",
        "forecast calibration",
        "forecast-calibration",
        "forecast_calibration",
        "finance forecast",
        "finance-forecast",
        "finance_forecast",
        "financial forecast",
        "financial-forecast",
        "financial_forecast",
        "finance forecasts",
        "finance-forecasts",
        "finance_forecasts",
        "financial forecasts",
        "financial-forecasts",
        "financial_forecasts",
        "market",
        "markets",
        "market parts",
        "market-parts",
        "market_parts",
        "market dashboard",
        "market-dashboard",
        "market_dashboard",
        "market board",
        "market-board",
        "market_board",
        "show me markets",
        "show-me-markets",
        "show_me_markets",
        "show me the markets",
        "show-me-the-markets",
        "show_me_the_markets",
        "prediction markets",
        "prediction-markets",
        "prediction_markets",
        "prediction",
        "prediction market",
        "prediction-market",
        "prediction_market",
        "prediction market parts",
        "prediction-market-parts",
        "prediction_market_parts",
        "prediction market board",
        "prediction-market-board",
        "prediction_market_board",
        "prediction ledger",
        "prediction-ledger",
        "prediction_ledger",
        "prediction lens",
        "prediction-lens",
        "prediction_lens",
        "show me prediction markets",
        "show-me-prediction-markets",
        "show_me_prediction_markets",
        "show me the prediction markets",
        "show-me-the-prediction-markets",
        "show_me_the_prediction_markets",
        "trading",
        "trading parts",
        "trading-parts",
        "trading_parts",
        "trading advice",
        "trading-advice",
        "trading_advice",
        "is this trading advice",
        "is-this-trading-advice",
        "is_this_trading_advice",
        "not financial advice",
        "not-financial-advice",
        "not_financial_advice",
        "investment advice",
        "investment-advice",
        "investment_advice",
        "investment",
        "investing",
        "portfolio",
        "trading system",
        "trading-system",
        "trading_system",
        "market evaluation",
        "market-evaluation",
        "market_evaluation",
        "financial advice",
        "financial-advice",
        "financial_advice",
        "finance evals",
        "finance-evals",
        "finance_evals",
        "finance evaluation",
        "finance-evaluation",
        "finance_evaluation",
        "forecasting evals",
        "forecasting-evals",
        "forecasting_evals",
        "polymarket",
        "finance parts",
        "finance-parts",
        "finance_parts",
        "financial parts",
        "financial-parts",
        "financial_parts",
        "finance stuff",
        "finance-stuff",
        "finance_stuff",
        "is this financial advice",
        "is-this-financial-advice",
        "is_this_financial_advice",
        "show me finance",
        "show-me-finance",
        "show_me_finance",
        "where is finance",
        "where-is-finance",
        "where_is_finance",
        "how do i inspect finance",
        "how-do-i-inspect-finance",
        "how_do_i_inspect_finance",
        "show me forecasts",
        "show-me-forecasts",
        "show_me_forecasts",
        "show me the forecasts",
        "show-me-the-forecasts",
        "show_me_the_forecasts",
        "market forecasts",
        "market-forecasts",
        "market_forecasts",
        "show me the finance",
        "show-me-the-finance",
        "show_me_the_finance",
        "show me finance stuff",
        "show-me-finance-stuff",
        "show_me_finance_stuff",
        "show me finance parts",
        "show-me-finance-parts",
        "show_me_finance_parts",
        "show me the finance parts",
        "show-me-the-finance-parts",
        "show_me_the_finance_parts",
        "show me financial parts",
        "show-me-financial-parts",
        "show_me_financial_parts",
        "show me the financial parts",
        "show-me-the-financial-parts",
        "show_me_the_financial_parts",
        "show me trading parts",
        "show-me-trading-parts",
        "show_me_trading_parts",
        "show me the trading parts",
        "show-me-the-trading-parts",
        "show_me_the_trading_parts",
    }:
        return "finance"
    if value in {
        "lean",
        "lean proof",
        "lean-proof",
        "lean_proof",
        "lean proofs",
        "lean-proofs",
        "lean_proofs",
        "lean pipeline",
        "lean-pipeline",
        "lean_pipeline",
        "lean witness",
        "lean-witness",
        "lean_witness",
        "does lean run",
        "does-lean-run",
        "does_lean_run",
        "lean stuff",
        "lean-stuff",
        "lean_stuff",
        "show me lean",
        "show-me-lean",
        "show_me_lean",
        "show me lean stuff",
        "show-me-lean-stuff",
        "show_me_lean_stuff",
        "show me lean parts",
        "show-me-lean-parts",
        "show_me_lean_parts",
        "show me lean proofs",
        "show-me-lean-proofs",
        "show_me_lean_proofs",
        "show me the lean proofs",
        "show-me-the-lean-proofs",
        "show_me_the_lean_proofs",
    }:
        return "lean"
    if value in {
        "theorem proving",
        "theorem-proving",
        "theorem_proving",
        "show me theorem proving",
        "show-me-theorem-proving",
        "show_me_theorem_proving",
        "show me the theorem proving",
        "show-me-the-theorem-proving",
        "show_me_the_theorem_proving",
        "show me theorem proving parts",
        "show-me-theorem-proving-parts",
        "show_me_theorem_proving_parts",
        "show me the theorem proving parts",
        "show-me-the-theorem-proving-parts",
        "show_me_the_theorem_proving_parts",
        "theorem prover",
        "theorem-prover",
        "theorem_prover",
        "theorem provers",
        "theorem-provers",
        "theorem_provers",
        "theorem proof",
        "theorem-proof",
        "theorem_proof",
        "show me theorem prover",
        "show-me-theorem-prover",
        "show_me_theorem_prover",
        "show me theorem provers",
        "show-me-theorem-provers",
        "show_me_theorem_provers",
    }:
        return "theorem-proving"
    if value in {
        "formal math",
        "math",
        "mathematics",
        "math parts",
        "math-parts",
        "math_parts",
        "show math",
        "show-math",
        "show_math",
        "where is the math",
        "where-is-the-math",
        "where_is_the_math",
        "show me math",
        "show-me-math",
        "show_me_math",
        "show me the math",
        "show me math stuff",
        "show-me-math-stuff",
        "show_me_math_stuff",
        "show me math parts",
        "show-me-math-parts",
        "show_me_math_parts",
        "mathematical parts",
        "mathematical-parts",
        "mathematical_parts",
        "show me mathematical parts",
        "show-me-mathematical-parts",
        "show_me_mathematical_parts",
        "show me the mathematical parts",
        "show-me-the-mathematical-parts",
        "show_me_the_mathematical_parts",
        "formal",
        "formal-math",
        "formal_math",
        "formal-methods",
        "formal_methods",
        "formal-math-path",
        "formal_math_path",
        "formal verification",
        "formal-verification",
        "formal_verification",
        "formal proof",
        "formal-proof",
        "formal_proof",
        "formal proofs",
        "formal-proofs",
        "formal_proofs",
        "proof",
        "proof pipeline",
        "proof-pipeline",
        "proof_pipeline",
        "proof evidence",
        "proof-evidence",
        "proof_evidence",
        "math proof parts",
        "math-proof-parts",
        "math_proof_parts",
        "where are the proofs",
        "where-are-the-proofs",
        "where_are_the_proofs",
        "how do i inspect proofs",
        "how-do-i-inspect-proofs",
        "how_do_i_inspect_proofs",
        "does it prove anything",
        "does-it-prove-anything",
        "does_it_prove_anything",
        "math proof",
        "math-proof",
        "math_proof",
        "mathlib",
        "mathlib readiness",
        "mathlib-readiness",
        "mathlib_readiness",
        "certificate",
        "certificates",
        "proof certificate",
        "proof-certificate",
        "proof_certificate",
        "certificate kernel",
        "certificate-kernel",
        "certificate_kernel",
        "verifier",
        "verifier lab",
        "verifier-lab",
        "verifier_lab",
        "tactic",
        "tactics",
        "premise retrieval",
        "premise-retrieval",
        "premise_retrieval",
        "premise search",
        "premise-search",
        "premise_search",
        "formal evidence cells",
        "formal-evidence-cells",
        "formal_evidence_cells",
        "verification traces",
        "verification-traces",
        "verification_traces",
        "proof diagnostics",
        "proof-diagnostics",
        "proof_diagnostics",
        "proof search",
        "proof-search",
        "proof_search",
        "proof authority",
        "proof-authority",
        "proof_authority",
        "show-me-the-math",
        "show_me_the_math",
        "show formal methods",
        "show-formal-methods",
        "show_formal_methods",
        "show me formal math",
        "show-me-formal-math",
        "show_me_formal_math",
        "show me formal methods",
        "show me the formal methods",
        "formal methods parts",
        "formal-methods-parts",
        "formal_methods_parts",
        "show me formal methods stuff",
        "show me formal methods parts",
        "show me the formal methods parts",
        "show me formal verification",
        "show me the formal verification",
        "show me formal verification parts",
        "show me the formal verification parts",
        "show me proof stuff",
        "show me proof parts",
        "show me proofs",
        "proof parts",
        "proof-parts",
        "proof_parts",
        "proofs",
        "proof checking",
        "proof-checking",
        "proof_checking",
        "show me proof checking",
        "show-me-proof-checking",
        "show_me_proof_checking",
        "proof system",
        "proof correctness",
        "does this prove correctness",
        "is this proof correct",
        "show me proof correctness",
        "show-me-formal-methods",
        "show-me-the-formal-methods",
        "show-me-formal-methods-stuff",
        "show-me-formal-methods-parts",
        "show-me-the-formal-methods-parts",
        "show-me-formal-verification",
        "show-me-the-formal-verification",
        "show-me-formal-verification-parts",
        "show-me-the-formal-verification-parts",
        "show-me-proof-stuff",
        "show-me-proof-parts",
        "show-me-proofs",
        "proof-system",
        "proof-correctness",
        "does-this-prove-correctness",
        "is-this-proof-correct",
        "show-me-proof-correctness",
        "show_me_formal_methods",
        "show_me_the_formal_methods",
        "show_me_formal_methods_stuff",
        "show_me_formal_methods_parts",
        "show_me_the_formal_methods_parts",
        "show_me_formal_verification",
        "show_me_the_formal_verification",
        "show_me_formal_verification_parts",
        "show_me_the_formal_verification_parts",
        "show_me_proof_stuff",
        "show_me_proof_parts",
        "show_me_proofs",
        "proof_system",
        "proof_correctness",
        "does_this_prove_correctness",
        "is_this_proof_correct",
        "show_me_proof_correctness",
    }:
        return "formal-methods"
    if "agent" in value and ("entry" in value or "first" in value or "cold" in value):
        return "agent-entry"
    return value.replace("_", "-").replace(" ", "-")


def _normalize_viewer(viewer: str | None) -> str:
    value = (viewer or ALL_VIEWERS).strip().lower().replace("-", "_")
    if value in {"", ALL_VIEWERS}:
        return ALL_VIEWERS
    if value in {"type_a", "type_a_agent", "agent"}:
        return TYPE_A_READER_ID
    if value in {"human", "human_reader", "operator", "reviewer"}:
        return HUMAN_VIEWER_ID
    return value


def _type_a_reader_row(entry_packet: dict[str, Any]) -> dict[str, Any]:
    selection_card = _as_dict(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "reader_selection_card"
        )
    )
    for row in _as_list(selection_card.get("selection_rows")):
        if isinstance(row, dict) and row.get("reader_id") == TYPE_A_READER_ID:
            return row
    return {}


def _reader_rows_by_id(entry_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    selection_card = _as_dict(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "reader_selection_card"
        )
    )
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(selection_card.get("selection_rows")):
        if isinstance(row, dict) and row.get("reader_id"):
            rows[str(row["reader_id"])] = row
    return rows


def _reader_detail_rows_by_id(entry_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    route_packet = _as_dict(entry_packet.get("reader_first_screen_routes"))
    rows: dict[str, dict[str, Any]] = {}
    for row in _as_list(route_packet.get("routes")):
        if isinstance(row, dict) and row.get("reader_id"):
            rows[str(row["reader_id"])] = row
    return rows


def _source_ref(ref: str, organ_id: str) -> str:
    return f"{ref}[organ_id={organ_id}]"


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def _is_runnable_public_command(command: str, *, allow_project_placeholder: bool = False) -> bool:
    if not command or any(
        banned in command
        for banned in (
            "raw_seed.md",
            "obsidian/",
            "provider payload",
            "operator thread",
            "HUD/browser",
        )
    ):
        return False
    if "<" in command or ">" in command:
        if not allow_project_placeholder:
            return False
        if command.count("<project>") != 1:
            return False
    tokens = _command_tokens(command)
    if not tokens:
        return False
    if tokens[0] == "microcosm":
        return True
    if len(tokens) >= 5 and tokens[0].startswith("PYTHONPATH=") and tokens[1:4] == [
        "python3",
        "-m",
        "microcosm_core.organs.navigation_hologram_route_plane",
    ]:
        return True
    if len(tokens) >= 4 and tokens[0].startswith("PYTHONPATH=") and tokens[1:3] == [
        "python3",
        "-m",
    ]:
        return tokens[3].startswith("microcosm_core.")
    if len(tokens) >= 3 and tokens[0] in {"python", "python3"} and tokens[1] == "-m":
        return tokens[2].startswith("microcosm_core.")
    return False


def _source_checkout_command(command: str) -> str | None:
    command = command.strip()
    if not command:
        return None
    if command.startswith("PYTHONPATH=src "):
        return command
    if command == "microcosm":
        return "PYTHONPATH=src python3 -m microcosm_core"
    if command.startswith("microcosm "):
        return f"PYTHONPATH=src python3 -m microcosm_core {command[len('microcosm '):]}"
    return None


def _list_has_text(values: Any) -> bool:
    return any(bool(item.strip()) for item in _strings(values))


def _doctrine_rows_by_organ(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("organ_id")): row
        for row in build_organ_doctrine_rows(root)
        if isinstance(row, dict) and row.get("organ_id")
    }


def _viewer_mode(
    *,
    viewer_id: str,
    first_action: str,
    next_action: str | None,
    branch_label: str,
    viewer_question: str,
    authority_boundary: str,
    evidence_refs: list[str],
    stop_condition: str,
    reentry_condition: str,
    anti_overread_warning: str,
    drilldown_if_needed: list[str],
    source_refs: list[str],
    task_class: str,
    source_checkout_first_action: str | None = None,
    source_checkout_next_action: str | None = None,
) -> dict[str, Any]:
    return {
        "viewer": viewer_id,
        "viewer_family": viewer_id,
        "task_class": task_class,
        "branch_label": branch_label,
        "viewer_question": viewer_question,
        "first_safe_action": first_action,
        "next_action": next_action,
        "source_checkout_first_safe_action": source_checkout_first_action,
        "source_checkout_next_action": source_checkout_next_action,
        "authority_boundary": authority_boundary,
        "evidence_refs": evidence_refs,
        "stop_condition": stop_condition,
        "reentry_condition": reentry_condition,
        "anti_overread_warning": anti_overread_warning,
        "drilldown_if_needed": drilldown_if_needed,
        "source_refs": source_refs,
    }


def _entry_experience_check(mode: dict[str, Any]) -> dict[str, Any]:
    first_action = str(mode.get("first_safe_action") or "")
    authority_boundary = str(mode.get("authority_boundary") or "")
    anti_overread = str(mode.get("anti_overread_warning") or "")
    stop_condition = str(mode.get("stop_condition") or "")
    reentry_condition = str(mode.get("reentry_condition") or "")
    evidence_refs = mode.get("evidence_refs")
    branch_label = str(mode.get("branch_label") or "")
    failure_codes: list[str] = []

    first_action_visible = _is_runnable_public_command(
        first_action, allow_project_placeholder=True
    )
    if not first_action_visible:
        failure_codes.append("missing_viewer_first_action")

    authority_boundary_visible = bool(authority_boundary) and any(
        token in authority_boundary.lower()
        for token in ("not", "no ", "does not", "authority", "boundary")
    )
    if not authority_boundary_visible:
        failure_codes.append("missing_viewer_authority_boundary")

    evidence_ref_visible = _list_has_text(evidence_refs)
    if not evidence_ref_visible:
        failure_codes.append("missing_viewer_evidence_ref")

    stop_condition_visible = bool(stop_condition.strip())
    if not stop_condition_visible:
        failure_codes.append("missing_viewer_stop_condition")

    reentry_condition_visible = bool(reentry_condition.strip()) and "re-entry" in (
        reentry_condition.lower()
    )
    if not reentry_condition_visible:
        failure_codes.append("missing_viewer_reentry_condition")

    anti_overread_warning_visible = bool(anti_overread.strip()) and any(
        token in anti_overread.lower()
        for token in ("not", "do not", "does not", "no ")
    )
    if not anti_overread_warning_visible:
        failure_codes.append("missing_viewer_anti_overread_warning")

    route_scent = "strong"
    if not branch_label.strip() or "reader" in branch_label.lower():
        route_scent = "weak"
        failure_codes.append("weak_viewer_route_label")

    return {
        "schema": "microcosm_entry_experience_check_v0",
        "viewer": mode.get("viewer"),
        "task_class": mode.get("task_class"),
        "status": "pass" if not failure_codes else "blocked",
        "first_action_visible": first_action_visible,
        "authority_boundary_visible": authority_boundary_visible,
        "evidence_ref_visible": evidence_ref_visible,
        "stop_condition_visible": stop_condition_visible,
        "reentry_condition_visible": reentry_condition_visible,
        "anti_overread_warning_visible": anti_overread_warning_visible,
        "route_scent": route_scent,
        "failure_codes": failure_codes,
    }


def _viewer_route_summary(mode: dict[str, Any]) -> dict[str, Any]:
    return {
        "viewer": mode.get("viewer"),
        "branch_label": mode.get("branch_label"),
        "first_safe_action": mode.get("first_safe_action"),
        "next_action": mode.get("next_action"),
        "source_checkout_first_safe_action": mode.get(
            "source_checkout_first_safe_action"
        ),
        "source_checkout_next_action": mode.get("source_checkout_next_action"),
        "authority_boundary": mode.get("authority_boundary"),
        "evidence_refs": mode.get("evidence_refs"),
        "stop_condition": mode.get("stop_condition"),
        "reentry_condition": mode.get("reentry_condition"),
        "anti_overread_warning": mode.get("anti_overread_warning"),
        "source_refs": mode.get("source_refs"),
    }


def _selected_viewer_route(
    selected_viewer: str, viewer_modes: list[dict[str, Any]]
) -> dict[str, Any]:
    viewer_by_id = {str(row.get("viewer")): row for row in viewer_modes}
    if selected_viewer != ALL_VIEWERS:
        return _as_dict(viewer_by_id.get(selected_viewer))
    routes = {
        viewer_id: _viewer_route_summary(_as_dict(viewer_by_id.get(viewer_id)))
        for viewer_id in VIEWER_IDS
    }
    return {
        "schema": "microcosm_selected_viewer_route_set_v0",
        "viewer": ALL_VIEWERS,
        "route_kind": "viewer_route_set",
        "viewer_families": list(VIEWER_IDS),
        "requires_viewer_selection": True,
        "selection_command": SELECT_VIEWER_COMMAND,
        "source_checkout_selection_command": SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND,
        "routes": routes,
        "first_safe_actions": {
            viewer_id: route.get("first_safe_action")
            for viewer_id, route in routes.items()
        },
        "authority_boundary": (
            "Route-set projection/read authority only; select one viewer branch "
            "before treating first_action or next_action as an execution plan."
        ),
    }


def _selected_viewer_entry(selected_viewer_route: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "microcosm_selected_viewer_entry_v0",
        "viewer": selected_viewer_route.get("viewer"),
        "route_kind": selected_viewer_route.get("route_kind", "single_viewer_route"),
        "first_safe_action": selected_viewer_route.get("first_safe_action"),
        "first_safe_actions": selected_viewer_route.get("first_safe_actions"),
        "next_action": selected_viewer_route.get("next_action"),
        "source_checkout_first_safe_action": selected_viewer_route.get(
            "source_checkout_first_safe_action"
        ),
        "source_checkout_next_action": selected_viewer_route.get(
            "source_checkout_next_action"
        ),
        "authority_boundary": selected_viewer_route.get("authority_boundary"),
        "evidence_refs": selected_viewer_route.get("evidence_refs"),
        "stop_condition": selected_viewer_route.get("stop_condition"),
        "reentry_condition": selected_viewer_route.get("reentry_condition"),
        "salience_rule": (
            "Read this selected viewer entry before the Type A route body floor, "
            "macro curriculum, or broad organ inventory."
        ),
    }


def _build_read_run_order(
    *,
    selected_viewer: str,
    selected_viewer_route: dict[str, Any],
    first_screen_route: dict[str, Any],
    task_route_card: dict[str, Any],
    accepted_organ_glance: dict[str, Any],
    macro_floor: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    viewer_step = {
        "step": 1,
        "kind": "selected_viewer_route",
        "run": selected_viewer_route.get("first_safe_action")
        or selected_viewer_route.get("first_safe_actions"),
        "source_checkout_run": selected_viewer_route.get(
            "source_checkout_first_safe_action"
        )
        or {
            viewer_id: route.get("source_checkout_first_safe_action")
            for viewer_id, route in _as_dict(
                selected_viewer_route.get("routes")
            ).items()
        },
        "read": selected_viewer_route.get("source_refs")
        or {
            viewer_id: route.get("source_refs")
            for viewer_id, route in _as_dict(
                selected_viewer_route.get("routes")
            ).items()
        },
        "why": (
            "Start from the selected viewer branch so humans do not wade through "
            "Type A macro curriculum and controllers do not special-case --viewer all."
        ),
    }
    shared_steps = [
        {
            "kind": "first_screen",
            "run": first_screen_route.get("route_command"),
            "read": first_screen_route.get("source_ref"),
            "why": "Establish the Type A first-screen route and claim ceiling before mutation.",
        },
        {
            "kind": "task_route",
            "run": task_route_card.get("first_command"),
            "read": task_route_card.get("source_ref"),
            "why": "Dereference the task class into relevant organs, evidence refs, and stop conditions.",
        },
        {
            "kind": "accepted_organ_glance",
            "run": None,
            "read": [
                accepted_organ_glance.get("source_ref"),
                accepted_organ_glance.get("drilldown"),
            ],
            "why": (
                "Read one line per accepted organ before treating the matrix or "
                "macro floor as the system itself."
            ),
        },
        {
            "kind": "organ_discoverability_matrix",
            "run": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
            "read": [ORGAN_DISCOVERABILITY_MATRIX_REF],
            "why": (
                "Use the matrix to classify accepted-organ discoverability gaps "
                "before per-organ patching or generated-route work."
            ),
        },
        {
            "kind": "macro_body_floor",
            "run": [row.get("first_command") for row in macro_floor],
            "read": [row.get("standards", {}).get("paper_module_ref") for row in macro_floor],
            "why": "Use imported macro route bodies as the mechanism curriculum before broad inventory.",
        },
    ]
    if selected_viewer == HUMAN_VIEWER_ID:
        task_class = str(task_route_card.get("task_class") or DEFAULT_TASK)
        if task_class == DEFAULT_TASK:
            order = [
                viewer_step,
                {
                    "kind": "optional_drilldown_after_human_first_action",
                    "run": selected_viewer_route.get("next_action"),
                    "read": selected_viewer_route.get("drilldown_if_needed"),
                    "why": (
                        "Human entry stops at hello/tour unless the operator asks for "
                        "evidence or owner-surface drilldown."
                    ),
                },
            ]
        else:
            order = [
                viewer_step,
                {
                    "kind": "selected_task_route_after_human_entry",
                    "run": task_route_card.get("first_command"),
                    "source_checkout_run": task_route_card.get(
                        "source_checkout_first_command"
                    ),
                    "read": [
                        task_route_card.get("source_ref"),
                        task_route_card.get("drilldown_target"),
                    ],
                    "why": (
                        "A task-specific human entry should expose the selected route "
                        "command, card, and authority ceiling before broad inventory."
                    ),
                },
            ]
    else:
        order = [viewer_step, *shared_steps]
    return [{**row, "step": index + 1} for index, row in enumerate(order)]


def _build_viewer_modes(
    *,
    entry_packet: dict[str, Any],
    first_screen_route: dict[str, Any],
    task_route_card: dict[str, Any],
    omission_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    reader_rows = _reader_rows_by_id(entry_packet)
    reader_detail_rows = _reader_detail_rows_by_id(entry_packet)
    type_a_detail = _as_dict(reader_detail_rows.get(TYPE_A_READER_ID))
    public_reader = _as_dict(reader_rows.get("public_github_visitor"))
    shared_prerequisite = str(
        _as_dict(entry_packet.get("reader_first_screen_routes")).get(
            "shared_prerequisite_command"
        )
        or "microcosm tour --card <project>"
    )
    task_class = str(task_route_card.get("task_class") or DEFAULT_TASK)
    task_source_checkout_command = str(
        task_route_card.get("source_checkout_first_command") or ""
    )
    task_evidence = [
        str(task_route_card.get("source_ref") or ""),
        str(task_route_card.get("evidence_ref") or ""),
        str(task_route_card.get("receipt_ref") or ""),
    ]
    task_evidence.extend(
        str(row.get("evidence_refs", {}).get("current_authority_receipt") or "")
        for row in _as_list(task_route_card.get("relevant_organs"))
        if isinstance(row, dict)
    )
    task_evidence = [ref for ref in task_evidence if ref]

    type_a_mode = _viewer_mode(
        viewer_id=TYPE_A_READER_ID,
        task_class=task_class,
        branch_label="Type A agent entry",
        viewer_question=str(first_screen_route.get("cold_question") or ""),
        first_action=str(first_screen_route.get("route_command") or ""),
        next_action=str(
            type_a_detail.get("next_command")
            or task_route_card.get("first_command")
            or ""
        ),
        source_checkout_first_action=SOURCE_CHECKOUT_FIRST_SCREEN_CARD_COMMAND,
        source_checkout_next_action=SOURCE_CHECKOUT_ORGAN_SURFACE_CONTRACT_COMMAND,
        authority_boundary=(
            f"{first_screen_route.get('authority_ceiling')}. "
            f"{task_route_card.get('authority_boundary')}"
        ),
        evidence_refs=task_evidence,
        stop_condition=str(first_screen_route.get("stop_when") or ""),
        reentry_condition=str(omission_receipt.get("reentry_condition") or ""),
        anti_overread_warning=str(first_screen_route.get("anti_overread") or ""),
        drilldown_if_needed=[
            str(first_screen_route.get("source_ref") or ""),
            str(task_route_card.get("source_ref") or ""),
            str(task_route_card.get("drilldown_target") or ""),
            str(type_a_detail.get("followup_command") or ""),
        ],
        source_refs=[
            str(first_screen_route.get("source_ref") or ""),
            str(task_route_card.get("source_ref") or ""),
        ],
    )

    human_first_action = str(public_reader.get("route_command") or "microcosm hello <project>")
    human_stop = str(
        public_reader.get("stop_when")
        or "You can name what the card proves, what it only projects, and which authority claims it refuses."
    )
    human_anti_overread = str(
        public_reader.get("anti_overread")
        or "Do not treat an entry projection as release, proof, source, provider, or private-root authority."
    )
    human_source_ref = (
        "atlas/entry_packet.json::reader_first_screen_routes."
        "reader_selection_card.selection_rows[reader_id=public_github_visitor]"
    )
    human_next_action = shared_prerequisite
    human_stop_condition = human_stop
    if task_class != DEFAULT_TASK:
        human_next_action = str(task_route_card.get("first_command") or shared_prerequisite)
        human_stop_condition = (
            "You can name the selected task route, primary organ, evidence class, "
            "first command, and authority ceiling without claiming domain correctness."
        )
    human_mode = _viewer_mode(
        viewer_id=HUMAN_VIEWER_ID,
        task_class=task_class,
        branch_label="Human entry",
        viewer_question=(
            "What should a human read or run first, and what trust boundary should they keep?"
        ),
        first_action=human_first_action,
        next_action=human_next_action,
        source_checkout_first_action=None,
        source_checkout_next_action=task_source_checkout_command or None,
        authority_boundary=(
            "Human entry is interpretive/read authority only; it does not authorize "
            "release, proof correctness, source mutation, provider calls, hosted "
            "deployment, private-root equivalence, or whole-system correctness."
        ),
        evidence_refs=[
            human_source_ref,
            str(task_route_card.get("receipt_ref") or ""),
            str(task_route_card.get("evidence_ref") or ""),
        ],
        stop_condition=human_stop_condition,
        reentry_condition=str(omission_receipt.get("reentry_condition") or ""),
        anti_overread_warning=human_anti_overread,
        drilldown_if_needed=[
            "README.md::Public Repo Map",
            "AGENTS.md::Fast Entry For Cold Agents",
            str(task_route_card.get("source_ref") or ""),
            str(task_route_card.get("drilldown_target") or ""),
        ],
        source_refs=[
            human_source_ref,
            "README.md::Public Repo Map",
            str(task_route_card.get("source_ref") or ""),
        ],
    )
    return [type_a_mode, human_mode]


def _organ_card(
    *,
    organ_id: str,
    registry_by_id: dict[str, dict[str, Any]],
    atlas_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    doctrine_by_id: dict[str, dict[str, Any]],
    role: str,
) -> dict[str, Any]:
    registry = _as_dict(registry_by_id.get(organ_id))
    atlas = _as_dict(atlas_by_id.get(organ_id))
    evidence = _as_dict(evidence_by_id.get(organ_id))
    doctrine = _as_dict(doctrine_by_id.get(organ_id))
    surface_refs = _as_dict(doctrine.get("surface_refs"))
    first_command = str(atlas.get("first_command") or registry.get("validator_command") or "")
    receipt_refs = _strings(registry.get("generated_receipts"))
    current_authority = str(registry.get("current_authority_receipt") or "")
    if current_authority and current_authority not in receipt_refs:
        receipt_refs = [current_authority, *receipt_refs]
    return {
        "organ_id": organ_id,
        "role": role,
        "display_name": atlas.get("display_name") or organ_id.replace("_", " ").title(),
        "family": atlas.get("family"),
        "evidence_class": registry.get("evidence_class") or evidence.get("evidence_class"),
        "evidence_strength_rank": registry.get("evidence_strength_rank"),
        "first_command": first_command,
        "command_runnable_shape": _is_runnable_public_command(first_command),
        "claim_ceiling": atlas.get("claim_ceiling_restated") or registry.get("claim_ceiling"),
        "wiring_note": atlas.get("wiring_note"),
        "agent_gloss": atlas.get("agent_gloss"),
        "evidence_refs": {
            "registry": _source_ref(ORGAN_REGISTRY_REF, organ_id),
            "atlas": _source_ref(ORGAN_ATLAS_REF, organ_id),
            "evidence_class": _source_ref(EVIDENCE_CLASSES_REF, organ_id),
            "current_authority_receipt": current_authority,
            "receipt_refs": receipt_refs,
        },
        "standards": {
            "standard_ref": surface_refs.get("standard"),
            "standards_registry_ref": surface_refs.get("standards_registry"),
            "paper_module_ref": surface_refs.get("paper_module") or atlas.get("paper_module_ref"),
            "concept_ref": doctrine.get("concept_binding")
            and f"organ_doctrine_row:{organ_id}.concept_binding",
            "mechanism_ref": doctrine.get("mechanism_binding")
            and f"organ_doctrine_row:{organ_id}.mechanism_binding",
        },
        "authority_boundary": (
            "organ_card_projection_not_source_authority_"
            "read_refs_before_receipt_or_source_drilldown"
        ),
    }


def _add_error(errors: list[dict[str, str]], *, path: str, code: str, message: str) -> None:
    errors.append({"path": path, "code": code, "message": message})


def validate_agent_entry_composition(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if payload.get("schema") != SCHEMA:
        _add_error(
            errors,
            path="schema",
            code="bad_schema",
            message=f"Agent entry composition must use {SCHEMA}.",
        )
    if payload.get("authority_posture") != PROJECTION_AUTHORITY_POSTURE:
        _add_error(
            errors,
            path="authority_posture",
            code="bad_authority_posture",
            message="Projection must identify itself as non-source, non-release authority.",
        )
    source_refs = set(_strings(payload.get("source_refs")))
    for ref in REQUIRED_TOP_LEVEL_SOURCE_REFS:
        if ref not in source_refs:
            _add_error(
                errors,
                path="source_refs",
                code="missing_source_ref",
                message=f"Projection source refs must include {ref}.",
            )
    first_screen = _as_dict(payload.get("first_screen_type_a_route"))
    if first_screen.get("reader_id") != TYPE_A_READER_ID:
        _add_error(
            errors,
            path="first_screen_type_a_route.reader_id",
            code="missing_type_a_reader_route",
            message="Projection must compose the Type A first-screen reader route.",
        )
    if not _is_runnable_public_command(
        str(first_screen.get("route_command") or ""),
        allow_project_placeholder=True,
    ):
        _add_error(
            errors,
            path="first_screen_type_a_route.route_command",
            code="first_screen_command_not_runnable_shape",
            message="Type A first-screen command must be a runnable public command shape.",
        )

    task_route = _as_dict(payload.get("task_route"))
    if task_route.get("selected_task_route_found") is not True:
        _add_error(
            errors,
            path="task_route.selected_task_class",
            code="missing_selected_task_route",
            message="Projection must dereference the selected task route.",
        )
    if not _is_runnable_public_command(str(task_route.get("first_command") or "")):
        _add_error(
            errors,
            path="task_route.first_command",
            code="task_route_command_not_runnable_shape",
            message="Selected task route must preserve a runnable public command.",
        )
    glance = _as_dict(payload.get("accepted_organ_glance"))
    if glance.get("schema") != "microcosm_agent_entry_accepted_organ_glance_v0":
        _add_error(
            errors,
            path="accepted_organ_glance.schema",
            code="missing_accepted_organ_glance",
            message="Projection must expose the accepted-organ one-line glance.",
        )
    if glance.get("source_ref") != ORGAN_GLANCE_REF:
        _add_error(
            errors,
            path="accepted_organ_glance.source_ref",
            code="accepted_organ_glance_source_ref_missing",
            message="Accepted-organ glance must source from agent_task_routes organ_glance_ladder.",
        )
    if glance.get("first_family_label") != "Entry & Reveal":
        _add_error(
            errors,
            path="accepted_organ_glance.first_family_label",
            code="accepted_organ_glance_wrong_family_order",
            message="Accepted-organ glance must keep Entry & Reveal first.",
        )
    glance_organs = [
        organ
        for family in _as_list(glance.get("families"))
        if isinstance(family, dict)
        for organ in _as_list(family.get("organs"))
        if isinstance(organ, dict)
    ]
    accounting = _as_dict(glance.get("capsule_accounting"))
    accepted_count = accounting.get("accepted_organ_count")
    if accepted_count != len(glance_organs) or glance.get("organ_count") != len(glance_organs):
        _add_error(
            errors,
            path="accepted_organ_glance.organ_count",
            code="accepted_organ_glance_count_mismatch",
            message="Accepted-organ glance must preserve one row per accepted organ.",
        )
    for index, organ in enumerate(glance_organs):
        missing = [
            field
            for field in (
                "organ_id",
                "display_name",
                "one_line",
                "card",
                "authority_ceiling",
                "claim_ceiling_restated",
                "evidence_class",
                "first_command",
                "paper_module_ref",
                "capsule_id",
                "capsule_join_status",
                "card_ref",
                "drilldown_target",
            )
            if not str(organ.get(field) or "").strip()
        ]
        if missing:
            _add_error(
                errors,
                path=f"accepted_organ_glance.organs[{index}]",
                code="accepted_organ_glance_row_incomplete",
                message=f"Accepted-organ glance row is missing: {', '.join(missing)}.",
            )
    discoverability_route = _as_dict(payload.get("organ_discoverability_matrix_route"))
    if not _is_runnable_public_command(str(discoverability_route.get("run") or "")):
        _add_error(
            errors,
            path="organ_discoverability_matrix_route.run",
            code="discoverability_matrix_command_not_runnable_shape",
            message="Entry card must expose the accepted-organ discoverability matrix command.",
        )
    if ORGAN_DISCOVERABILITY_MATRIX_REF not in _strings(discoverability_route.get("read")):
        _add_error(
            errors,
            path="organ_discoverability_matrix_route.read",
            code="discoverability_matrix_source_ref_missing",
            message="Entry card must keep the matrix source projection ref visible.",
        )

    macro_floor = _as_list(payload.get("macro_import_route_body_floor"))
    macro_ids = {str(row.get("organ_id") or "") for row in macro_floor if isinstance(row, dict)}
    for organ_id in MACRO_IMPORT_ROUTE_ORGANS:
        if organ_id not in macro_ids:
            _add_error(
                errors,
                path="macro_import_route_body_floor",
                code="missing_macro_import_route_body",
                message=f"Projection must include macro route body floor organ {organ_id}.",
            )
    for index, row_value in enumerate(macro_floor):
        row = _as_dict(row_value)
        row_path = f"macro_import_route_body_floor[{row.get('organ_id') or index}]"
        if not row.get("command_runnable_shape"):
            _add_error(
                errors,
                path=f"{row_path}.first_command",
                code="macro_body_command_not_runnable_shape",
                message="Macro route body floor rows must preserve runnable public commands.",
            )
        evidence_refs = _as_dict(row.get("evidence_refs"))
        if not evidence_refs.get("current_authority_receipt") and not _strings(
            evidence_refs.get("receipt_refs")
        ):
            _add_error(
                errors,
                path=f"{row_path}.evidence_refs",
                code="macro_body_missing_evidence_refs",
                message="Macro route body floor rows must preserve receipt evidence refs.",
            )
        standards = _as_dict(row.get("standards"))
        if not standards.get("standard_ref") or not standards.get("mechanism_ref"):
            _add_error(
                errors,
                path=f"{row_path}.standards",
                code="macro_body_missing_standard_or_mechanism_ref",
                message="Macro route body floor rows must preserve standard and mechanism refs.",
            )

    omission = _as_dict(payload.get("omission_receipt"))
    if "re-entry" not in str(omission.get("reentry_condition", "")).lower():
        _add_error(
            errors,
            path="omission_receipt.reentry_condition",
            code="missing_reentry_condition",
            message="Projection must include a concrete re-entry condition.",
        )
    viewer_modes = _as_list(payload.get("viewer_modes"))
    viewer_by_id = {
        str(row.get("viewer") or ""): row
        for row in viewer_modes
        if isinstance(row, dict) and row.get("viewer")
    }
    for viewer_id in VIEWER_IDS:
        mode = _as_dict(viewer_by_id.get(viewer_id))
        if not mode:
            _add_error(
                errors,
                path="viewer_modes",
                code="missing_viewer_mode",
                message=f"Projection must include viewer mode {viewer_id}.",
            )
            continue
        check = _entry_experience_check(mode)
        if check["status"] != "pass":
            _add_error(
                errors,
                path=f"viewer_modes[{viewer_id}]",
                code="viewer_entry_experience_blocked",
                message=(
                    f"Viewer mode {viewer_id} lacks route scent fields: "
                    f"{', '.join(check['failure_codes'])}."
                ),
            )
    checks = _as_list(payload.get("entry_experience_checks"))
    check_by_viewer = {
        str(row.get("viewer") or ""): row
        for row in checks
        if isinstance(row, dict) and row.get("viewer")
    }
    for viewer_id in VIEWER_IDS:
        check = _as_dict(check_by_viewer.get(viewer_id))
        if not check or check.get("status") != "pass":
            _add_error(
                errors,
                path=f"entry_experience_checks[{viewer_id}]",
                code="viewer_entry_experience_check_not_passed",
                message=f"Entry experience check must pass for {viewer_id}.",
            )
    router = _as_dict(payload.get("viewer_first_action_router"))
    router_routes = _as_dict(router.get("routes"))
    for viewer_id in VIEWER_IDS:
        route = _as_dict(router_routes.get(viewer_id))
        if not _is_runnable_public_command(
            str(route.get("first_safe_action") or ""),
            allow_project_placeholder=True,
        ):
            _add_error(
                errors,
                path=f"viewer_first_action_router.routes[{viewer_id}]",
                code="viewer_router_missing_first_action",
                message=f"Viewer first-action router must expose {viewer_id}.",
            )
    selected_viewer = _normalize_viewer(str(payload.get("selected_viewer") or ALL_VIEWERS))
    selected_route = _as_dict(payload.get("selected_viewer_route"))
    if selected_viewer == ALL_VIEWERS:
        selected_routes = _as_dict(selected_route.get("routes"))
        if selected_route.get("viewer") != ALL_VIEWERS or not all(
            _as_dict(selected_routes.get(viewer_id)).get("viewer") == viewer_id
            for viewer_id in VIEWER_IDS
        ):
            _add_error(
                errors,
                path="selected_viewer_route.routes",
                code="selected_viewer_route_set_missing",
                message="All-viewer payload must expose a stable selected_viewer_route route set.",
            )
    else:
        if selected_route.get("viewer") != selected_viewer:
            _add_error(
                errors,
                path="selected_viewer_route.viewer",
                code="selected_viewer_route_missing",
                message="Selected viewer route must match selected_viewer.",
            )
    if payload.get("release_authority") is not False or payload.get("source_mutation_authority") is not False:
        _add_error(
            errors,
            path="authority_flags",
            code="projection_overclaims_authority",
            message="Projection must explicitly deny release and source-mutation authority.",
        )
    return {
        "schema": f"{SCHEMA}_validation_v0",
        "status": "pass" if not errors else "blocked",
        "error_count": len(errors),
        "errors": errors,
    }


def build_agent_entry_composition(
    *,
    root: str | Path | None = None,
    task: str | None = None,
    viewer: str | None = None,
    command: str = "agent-entry-composition",
) -> dict[str, Any]:
    resolved_root = Path(root).resolve() if root is not None else microcosm_root()
    entry_packet = _load_json(resolved_root / ENTRY_PACKET_REF)
    task_routes = _load_json(resolved_root / TASK_ROUTES_REF)
    registry = _load_json(resolved_root / "core/organ_registry.json")
    atlas = _load_json(resolved_root / "core/organ_atlas.json")
    evidence = _load_json(resolved_root / "core/organ_evidence_classes.json")

    registry_by_id = _rows_by_id(registry, "implemented_organs")
    atlas_by_id = _rows_by_id(atlas, "organs")
    evidence_by_id = _rows_by_id(evidence, "organ_evidence_classes")
    doctrine_by_id = _doctrine_rows_by_organ(resolved_root)
    route_by_task = _route_rows_by_task(task_routes)
    task_class = _normalize_task_class(task)
    selected_viewer = _normalize_viewer(viewer)
    selected_task_route_found = task_class in route_by_task
    selected_route = _as_dict(route_by_task.get(task_class) or route_by_task.get(DEFAULT_TASK))
    type_a_row = _type_a_reader_row(entry_packet)
    accepted_organ_glance = _accepted_organ_glance(task_routes)

    relevant_organs = [
        _organ_card(
            organ_id=str(row.get("organ_id") or ""),
            registry_by_id=registry_by_id,
            atlas_by_id=atlas_by_id,
            evidence_by_id=evidence_by_id,
            doctrine_by_id=doctrine_by_id,
            role="agent_entry_task_route_relevant_organ",
        )
        for row in _as_list(selected_route.get("relevant_organs"))
        if isinstance(row, dict) and row.get("organ_id")
    ]
    macro_floor = [
        _organ_card(
            organ_id=organ_id,
            registry_by_id=registry_by_id,
            atlas_by_id=atlas_by_id,
            evidence_by_id=evidence_by_id,
            doctrine_by_id=doctrine_by_id,
            role="macro_import_route_body_floor",
        )
        for organ_id in MACRO_IMPORT_ROUTE_ORGANS
    ]
    first_screen_route = {
        "source_ref": (
            "atlas/entry_packet.json::reader_first_screen_routes."
            "reader_selection_card.selection_rows[reader_id=type_a_agent]"
        ),
        "reader_id": type_a_row.get("reader_id"),
        "cold_question": type_a_row.get("cold_question"),
        "route_command": type_a_row.get("route_command"),
        "trust_signal": type_a_row.get("trust_signal"),
        "stop_when": type_a_row.get("stop_when"),
        "anti_overread": type_a_row.get("anti_overread"),
        "shared_prerequisite_command": _as_dict(
            entry_packet.get("reader_first_screen_routes")
        ).get("shared_prerequisite_command"),
        "authority_ceiling": _as_dict(entry_packet.get("local_first_screen_route")).get(
            "authority"
        ),
    }
    task_route_card = {
        "source_ref": (
            f"atlas/agent_task_routes.json::routes[task_class={selected_route.get('task_class')}]"
        ),
        "requested_task": task or DEFAULT_TASK,
        "selected_task_class": task_class,
        "selected_task_route_found": selected_task_route_found,
        "task_class": selected_route.get("task_class"),
        "primary_organ_id": selected_route.get("primary_organ_id"),
        "primary_display_name": selected_route.get("primary_display_name"),
        "first_command": selected_route.get("first_command"),
        "source_checkout_first_command": _source_checkout_command(
            str(selected_route.get("first_command") or "")
        ),
        "authority_ceiling": selected_route.get("allowed_authority"),
        "authority_boundary": selected_route.get("authority_boundary"),
        "drilldown_target": selected_route.get("drilldown_target"),
        "evidence_ref": selected_route.get("evidence_ref"),
        "receipt_ref": selected_route.get("receipt_ref"),
        "organ_count": selected_route.get("organ_count"),
        "relevant_organs": relevant_organs,
    }
    omission_receipt = {
        "omitted": [
            "full organ source bodies",
            "full generated public docs",
            "raw operator voice or private root state",
            "provider/HUD/browser/account/session payloads",
            "full receipt payload bodies",
        ],
        "reason": (
            "This card composes route handles, commands, evidence refs, standards, "
            "and authority ceilings for cold-agent entry. Detailed proof remains "
            "behind the named source and receipt surfaces."
        ),
        "reentry_condition": (
            "Re-entry when a task route, macro organ row, first-screen Type A row, "
            "viewer-mode route scent, or evidence/standard ref changes; rebuild "
            "this projection from the source JSON rather than editing generated "
            "docs or inventing labels."
        ),
        "drilldown": [
            ENTRY_PACKET_REF,
            TASK_ROUTES_REF,
            ORGAN_REGISTRY_REF,
            ORGAN_ATLAS_REF,
            EVIDENCE_CLASSES_REF,
        ],
    }
    viewer_modes = _build_viewer_modes(
        entry_packet=entry_packet,
        first_screen_route=first_screen_route,
        task_route_card=task_route_card,
        omission_receipt=omission_receipt,
    )
    entry_experience_checks = [_entry_experience_check(mode) for mode in viewer_modes]
    selected_viewer_route = _selected_viewer_route(selected_viewer, viewer_modes)
    selected_viewer_entry = _selected_viewer_entry(selected_viewer_route)
    read_run_order = _build_read_run_order(
        selected_viewer=selected_viewer,
        selected_viewer_route=selected_viewer_route,
        first_screen_route=first_screen_route,
        task_route_card=task_route_card,
        accepted_organ_glance=accepted_organ_glance,
        macro_floor=macro_floor,
    )
    viewer_first_action_router = {
        "schema": "microcosm_viewer_first_action_router_v0",
        "viewer_families": list(VIEWER_IDS),
        "select_viewer_command": SELECT_VIEWER_COMMAND,
        "source_checkout_select_viewer_command": SOURCE_CHECKOUT_SELECT_VIEWER_COMMAND,
        "source_checkout_boundary": (
            "Source-checkout command is a no-install invocation hint only; it "
            "does not add source-mutation, release, provider-call, proof, or "
            "private-root authority."
        ),
        "routes": {
            row["viewer"]: {
                "first_safe_action": row.get("first_safe_action"),
                "next_action": row.get("next_action"),
                "source_checkout_first_safe_action": row.get(
                    "source_checkout_first_safe_action"
                ),
                "source_checkout_next_action": row.get(
                    "source_checkout_next_action"
                ),
                "authority_boundary": row.get("authority_boundary"),
                "stop_condition": row.get("stop_condition"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in viewer_modes
            if row.get("viewer")
        },
        "anti_overread": (
            "Viewer routing is projection/read authority only; it does not "
            "grant source, proof, release, provider-call, or private-root "
            "authority."
        ),
    }

    payload = {
        "schema": SCHEMA,
        "status": "draft_pending_validation",
        "surface_role": "TASK_CONDITIONED_AGENT_ENTRY_COMPOSITION_CARD",
        "authority_posture": PROJECTION_AUTHORITY_POSTURE,
        "source_refs": list(REQUIRED_TOP_LEVEL_SOURCE_REFS),
        "task": task or DEFAULT_TASK,
        "selected_viewer": selected_viewer,
        "selected_viewer_entry": selected_viewer_entry,
        "selected_viewer_route": selected_viewer_route,
        "viewer_first_action_router": viewer_first_action_router,
        "release_authority": False,
        "source_mutation_authority": False,
        "provider_call_authority": False,
        "private_root_equivalence_authority": False,
        "first_screen_type_a_route": first_screen_route,
        "task_route": task_route_card,
        "accepted_organ_glance": accepted_organ_glance,
        "viewer_modes": viewer_modes,
        "entry_experience_checks": entry_experience_checks,
        "organ_discoverability_matrix_route": {
            "schema": "microcosm_organ_discoverability_matrix_entry_route_v0",
            "run": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
            "read": [
                ORGAN_DISCOVERABILITY_MATRIX_REF,
                ORGAN_REGISTRY_REF,
                ORGAN_ATLAS_REF,
                TASK_ROUTES_REF,
                EVIDENCE_CLASSES_REF,
            ],
            "authority_boundary": (
                "Projection/read authority only; source rows, receipts, standards, "
                "paper modules, and builders remain authority."
            ),
            "why": (
                "Before choosing an organ-specific repair, inspect the all-organ "
                "matrix for first command, authority ceiling, evidence class, "
                "paper module, proof receipt, owner route, and gap codes."
            ),
        },
        "macro_import_route_body_floor": macro_floor,
        "read_run_order": read_run_order,
        "omission_receipt": omission_receipt,
        "anti_claim": (
            "This is a route-mining and mechanism-curriculum projection. It does not "
            "replace atlas/entry_packet.json, atlas/agent_task_routes.json, organ "
            "registries, source modules, receipts, standards, or release decisions."
        ),
        "command": command,
    }
    validation = validate_agent_entry_composition(payload)
    payload["validation"] = validation
    payload["errors"] = validation["errors"]
    payload["status"] = validation["status"]
    return payload


def compact_agent_entry_card(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the first-entry view without expanding every organ row."""
    def drop_none(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: drop_none(row) for key, row in value.items() if row is not None}
        if isinstance(value, list):
            return [drop_none(row) for row in value]
        return value

    selected_viewer_route = _as_dict(payload.get("selected_viewer_route"))
    first_screen_route = _as_dict(payload.get("first_screen_type_a_route"))
    task_route = _as_dict(payload.get("task_route"))
    accepted_glance = _as_dict(payload.get("accepted_organ_glance"))
    organ_route = _as_dict(payload.get("organ_discoverability_matrix_route"))
    omission_receipt = _as_dict(payload.get("omission_receipt"))
    validation = _as_dict(payload.get("validation"))
    router = _as_dict(payload.get("viewer_first_action_router"))
    router_routes = _as_dict(router.get("routes"))
    compact_router = {
        "schema": router.get("schema"),
        "viewer_families": router.get("viewer_families"),
        "select_viewer_command": router.get("select_viewer_command"),
        "source_checkout_select_viewer_command": router.get(
            "source_checkout_select_viewer_command"
        ),
        "routes": {
            viewer_id: {
                "first_safe_action": _as_dict(route).get("first_safe_action"),
                "next_action": _as_dict(route).get("next_action"),
                "source_checkout_first_safe_action": _as_dict(route).get(
                    "source_checkout_first_safe_action"
                ),
                "source_checkout_next_action": _as_dict(route).get(
                    "source_checkout_next_action"
                ),
            }
            for viewer_id, route in router_routes.items()
        },
    }
    macro_floor = [
        {
            "organ_id": row.get("organ_id"),
            "display_name": row.get("display_name"),
            "first_command": row.get("first_command"),
            "evidence_class": row.get("evidence_class"),
            "claim_ceiling": row.get("claim_ceiling"),
            "receipt_refs": _as_dict(row.get("evidence_refs")).get("receipt_refs", []),
        }
        for row in _as_list(payload.get("macro_import_route_body_floor"))
        if isinstance(row, dict)
    ]

    return drop_none({
        "schema": "microcosm_agent_entry_composition_compact_card_v0",
        "compact_projection_of": SCHEMA,
        "status": payload.get("status"),
        "selected_viewer": payload.get("selected_viewer"),
        "selected_viewer_entry": payload.get("selected_viewer_entry"),
        "selected_viewer_route": {
            "viewer": selected_viewer_route.get("viewer"),
            "route_kind": selected_viewer_route.get("route_kind"),
            "branch_label": selected_viewer_route.get("branch_label"),
            "first_safe_action": selected_viewer_route.get("first_safe_action"),
            "next_action": selected_viewer_route.get("next_action"),
            "source_checkout_first_safe_action": selected_viewer_route.get(
                "source_checkout_first_safe_action"
            ),
            "source_checkout_next_action": selected_viewer_route.get(
                "source_checkout_next_action"
            ),
            "stop_condition": selected_viewer_route.get("stop_condition"),
            "authority_boundary": selected_viewer_route.get("authority_boundary"),
            "evidence_refs": selected_viewer_route.get("evidence_refs", []),
        },
        "viewer_first_action_router": compact_router,
        "first_screen_type_a_route": {
            "reader_id": first_screen_route.get("reader_id"),
            "route_command": first_screen_route.get("route_command"),
            "source_ref": first_screen_route.get("source_ref"),
            "anti_overread": first_screen_route.get("anti_overread"),
        },
        "task_route": {
            "requested_task": task_route.get("requested_task"),
            "selected_task_class": task_route.get("selected_task_class"),
            "selected_task_route_found": task_route.get("selected_task_route_found"),
            "task_class": task_route.get("task_class"),
            "primary_organ_id": task_route.get("primary_organ_id"),
            "primary_display_name": task_route.get("primary_display_name"),
            "first_command": task_route.get("first_command"),
            "source_checkout_first_command": task_route.get(
                "source_checkout_first_command"
            ),
            "drilldown_target": task_route.get("drilldown_target"),
            "evidence_ref": task_route.get("evidence_ref"),
            "receipt_ref": task_route.get("receipt_ref"),
            "authority_boundary": task_route.get("authority_boundary"),
            "allowed_authority": task_route.get("allowed_authority"),
            "organ_count": task_route.get("organ_count"),
        },
        "accepted_organ_glance": {
            "source_ref": accepted_glance.get("source_ref"),
            "drilldown": accepted_glance.get("drilldown"),
            "family_count": accepted_glance.get("family_count"),
            "organ_count": accepted_glance.get("organ_count"),
            "capsule_join_status_counts": accepted_glance.get(
                "capsule_join_status_counts", {}
            ),
            "authority_boundary": accepted_glance.get("authority_boundary"),
            "anti_claim": accepted_glance.get("anti_claim"),
        },
        "organ_discoverability_matrix_route": organ_route,
        "macro_import_route_body_floor": macro_floor,
        "read_run_order": payload.get("read_run_order", []),
        "authority_ceiling": {
            "release_authority": payload.get("release_authority"),
            "source_mutation_authority": payload.get("source_mutation_authority"),
            "provider_call_authority": payload.get("provider_call_authority"),
            "private_root_equivalence_authority": payload.get(
                "private_root_equivalence_authority"
            ),
        },
        "anti_claim": payload.get("anti_claim"),
        "omission_receipt": omission_receipt,
        "validation": {
            "status": validation.get("status"),
            "error_count": validation.get("error_count"),
            "errors": validation.get("errors", []),
        },
        "drilldowns": {
            "full_json": (
                "microcosm agent-entry-composition "
                f"--task {task_route.get('selected_task_class') or DEFAULT_TASK} "
                "--viewer <viewer>"
            ),
            "source_checkout_full_json": (
                "PYTHONPATH=src python3 -m microcosm_core "
                "agent-entry-composition --root . "
                f"--task {task_route.get('selected_task_class') or DEFAULT_TASK} "
                "--viewer <viewer>"
            ),
            "organ_matrix": ORGAN_DISCOVERABILITY_MATRIX_COMMAND,
        },
    })


def compile_paths(
    *,
    root: str | Path | None = None,
    task: str | None = None,
    viewer: str | None = None,
    out: str | Path | None = None,
    command: str = "agent-entry-composition",
) -> dict[str, Any]:
    payload = build_agent_entry_composition(
        root=root, task=task, viewer=viewer, command=command
    )
    if out is not None:
        out_path = Path(out)
        card_path = out_path / CARD_FILENAME
        receipt_path = out_path / RECEIPT_FILENAME
        payload["artifact_paths"] = {
            "out_dir": str(out_path),
            "card_path": str(card_path),
            "receipt_path": str(receipt_path),
        }
        write_json_atomic(card_path, payload)
        validation = _as_dict(payload.get("validation"))
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": payload["status"],
            "artifact_paths": payload["artifact_paths"],
            "card_path": str(card_path),
            "receipt_path": str(receipt_path),
            "source_refs": payload["source_refs"],
            "selected_task_class": payload["task_route"].get("task_class"),
            "selected_viewer": payload["selected_viewer"],
            "selected_viewer_route_kind": _as_dict(
                payload.get("selected_viewer_route")
            ).get("route_kind", "single_viewer_route"),
            "selected_viewer_status": _as_dict(
                payload.get("selected_viewer_route")
            ).get("viewer") or payload["selected_viewer"],
            "viewer_modes": [row.get("viewer") for row in payload["viewer_modes"]],
            "entry_experience_checks": [
                {
                    "viewer": row.get("viewer"),
                    "status": row.get("status"),
                    "failure_codes": row.get("failure_codes"),
                }
                for row in payload["entry_experience_checks"]
            ],
            "validation": {
                "status": validation.get("status"),
                "error_count": validation.get("error_count"),
                "errors": validation.get("errors", []),
            },
            "validation_errors": validation.get("errors", []),
            "accepted_organ_glance": {
                "source_ref": payload["accepted_organ_glance"].get("source_ref"),
                "family_count": payload["accepted_organ_glance"].get("family_count"),
                "organ_count": payload["accepted_organ_glance"].get("organ_count"),
                "capsule_join_status_counts": payload["accepted_organ_glance"].get(
                    "capsule_join_status_counts"
                ),
                "drilldown": payload["accepted_organ_glance"].get("drilldown"),
            },
            "macro_import_route_body_floor": [
                row.get("organ_id") for row in payload["macro_import_route_body_floor"]
            ],
            "authority_posture": payload["authority_posture"],
            "reentry_condition": payload["omission_receipt"]["reentry_condition"],
            "command": command,
        }
        write_json_atomic(receipt_path, receipt)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compose the Microcosm Type A cold-agent entry card."
    )
    parser.add_argument("--root", default=None)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--viewer", choices=(ALL_VIEWERS, *VIEWER_IDS), default=ALL_VIEWERS)
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    command = "python -m microcosm_core.projections.agent_entry_composition"
    payload = compile_paths(
        root=args.root,
        task=args.task,
        viewer=args.viewer,
        out=args.out,
        command=command,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" or not args.check else 1


if __name__ == "__main__":
    raise SystemExit(main())
