from __future__ import annotations

import argparse
import errno
import importlib
import json
import os
import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

from microcosm_core import __version__


class _LazyModule:
    def __init__(self, module_name: str) -> None:
        object.__setattr__(self, "_module_name", module_name)
        object.__setattr__(self, "_module", None)

    @property
    def loaded(self) -> bool:
        return object.__getattribute__(self, "_module") is not None

    def _load(self):
        module = object.__getattribute__(self, "_module")
        if module is None:
            module = importlib.import_module(object.__getattribute__(self, "_module_name"))
            object.__setattr__(self, "_module", module)
        return module

    def __getattr__(self, name: str):
        return getattr(self._load(), name)

    def __setattr__(self, name: str, value) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        setattr(self._load(), name, value)


class _LazyPath:
    def __init__(self, path_loader) -> None:
        object.__setattr__(self, "_path_loader", path_loader)
        object.__setattr__(self, "_path", None)

    def _load(self) -> Path:
        path = object.__getattribute__(self, "_path")
        if path is None:
            path = Path(object.__getattribute__(self, "_path_loader")())
            object.__setattr__(self, "_path", path)
        return path

    def __fspath__(self) -> str:
        return str(self._load())

    def __truediv__(self, other):
        return self._load() / other

    def __getattr__(self, name: str):
        return getattr(self._load(), name)

    def __str__(self) -> str:
        return str(self._load())

    def __repr__(self) -> str:
        return repr(self._load())

    def __eq__(self, other: object) -> bool:
        try:
            return self._load() == Path(other)  # type: ignore[arg-type]
        except TypeError:
            return False

    def __hash__(self) -> int:
        return hash(self._load())


TEXT_READER_CHOICES = (
    "all",
    "public_github_visitor",
    "safety_evals_engineer",
    "hiring_reviewer",
    "peer_developer",
    "domain_specialist",
    "type_a_agent",
    "cold_cloner",
    "cold-cloner",
    "interesting_parts",
    "interesting-parts",
    "skeptical_reviewer",
    "skeptical-reviewer",
    "reviewer",
    "agent",
    "type-a-agent",
    "domain-specialist",
)


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


first_screen_composition = _LazyModule("microcosm_core.first_screen_composition")
project_substrate = _LazyModule("microcosm_core.project_substrate")
runtime_shell = _LazyModule("microcosm_core.runtime_shell")
runtime_evidence_index = _LazyModule("microcosm_core.runtime_evidence_index")
resource_root = _LazyModule("microcosm_core.resource_root")
crown_jewel_demo = _LazyModule("microcosm_core.crown_jewel_demo")
macro_engines_gallery = _LazyModule("microcosm_core.macro_engines_gallery")
engine_room_demo = _LazyModule("microcosm_core.organs.engine_room_demo")
finance_eval_spine = _LazyModule("microcosm_core.macro_tools.finance_eval_spine")
organ_surface_contract = _LazyModule(
    "microcosm_core.projections.organ_surface_contract"
)
agent_entry_composition = _LazyModule(
    "microcosm_core.projections.agent_entry_composition"
)
organ_discoverability_matrix = _LazyModule(
    "microcosm_core.projections.organ_discoverability_matrix"
)
work_landing_control_spine = _LazyModule(
    "microcosm_core.macro_tools.work_landing_control_spine"
)
agent_closeout_faithfulness_audit = _LazyModule(
    "microcosm_core.organs.agent_closeout_faithfulness_audit"
)
agent_benchmark_integrity_anti_gaming_replay = _LazyModule(
    "microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay"
)
agent_memory_temporal_conflict_replay = _LazyModule(
    "microcosm_core.organs.agent_memory_temporal_conflict_replay"
)
agent_monitor_redteam_falsification_replay = _LazyModule(
    "microcosm_core.organs.agent_monitor_redteam_falsification_replay"
)
agent_route_observability_runtime = _LazyModule(
    "microcosm_core.organs.agent_route_observability_runtime"
)
agent_sabotage_scheming_monitor_replay = _LazyModule(
    "microcosm_core.organs.agent_sabotage_scheming_monitor_replay"
)
agent_sandbox_policy_escape_replay = _LazyModule(
    "microcosm_core.organs.agent_sandbox_policy_escape_replay"
)
agentic_vulnerability_discovery_patch_proof_replay = _LazyModule(
    "microcosm_core.organs.agentic_vulnerability_discovery_patch_proof_replay"
)
belief_state_process_reward_replay = _LazyModule(
    "microcosm_core.organs.belief_state_process_reward_replay"
)
bounded_autonomy_campaign_packet = _LazyModule(
    "microcosm_core.organs.bounded_autonomy_campaign_packet"
)
batch4_proof_authority_runtime = _LazyModule(
    "microcosm_core.organs.batch4_proof_authority_runtime"
)
batch5_authority_systems_capsule = _LazyModule(
    "microcosm_core.organs.batch5_authority_systems_capsule"
)
batch6_unsurfaced_primitives_capsule = _LazyModule(
    "microcosm_core.organs.batch6_unsurfaced_primitives_capsule"
)
batch7_demo_take_console_capsule = _LazyModule(
    "microcosm_core.organs.batch7_demo_take_console_capsule"
)
batch7_macro_engines_capsule = _LazyModule(
    "microcosm_core.organs.batch7_macro_engines_capsule"
)
batch7_oracle_sibling_capsule = _LazyModule(
    "microcosm_core.organs.batch7_oracle_sibling_capsule"
)
batch7_secondary_runtime_capsule = _LazyModule(
    "microcosm_core.organs.batch7_secondary_runtime_capsule"
)
batch7_station_runtime_capsule = _LazyModule(
    "microcosm_core.organs.batch7_station_runtime_capsule"
)
batch8_tools_tail_primitives_capsule = _LazyModule(
    "microcosm_core.organs.batch8_tools_tail_primitives_capsule"
)
batch8_policy_engines_capsule = _LazyModule(
    "microcosm_core.organs.batch8_policy_engines_capsule"
)
batch8_audio_level_rms_port = _LazyModule(
    "microcosm_core.organs.batch8_audio_level_rms_port"
)
batch8_station_surface_atlas_layout_port = _LazyModule(
    "microcosm_core.organs.batch8_station_surface_atlas_layout_port"
)
batch8_structural_theses_capsule = _LazyModule(
    "microcosm_core.organs.batch8_structural_theses_capsule"
)
batch8_compliance_pipeline_capsule = _LazyModule(
    "microcosm_core.organs.batch8_compliance_pipeline_capsule"
)
batch8_validator_checker_capsule = _LazyModule(
    "microcosm_core.organs.batch8_validator_checker_capsule"
)
concurrency_mission_control = _LazyModule(
    "microcosm_core.organs.concurrency_mission_control"
)
batch9_macro_engines_capsule = _LazyModule(
    "microcosm_core.organs.batch9_macro_engines_capsule"
)
batch10_governance_compilers_capsule = _LazyModule(
    "microcosm_core.organs.batch10_governance_compilers_capsule"
)
batch10_frontend_work_market_cockpit_capsule = _LazyModule(
    "microcosm_core.organs.batch10_frontend_work_market_cockpit_capsule"
)
batch10_live_source_drift_capsule = _LazyModule(
    "microcosm_core.organs.batch10_live_source_drift_capsule"
)
batch10_cold_eval_honesty_capsule = _LazyModule(
    "microcosm_core.organs.batch10_cold_eval_honesty_capsule"
)
batch11_saturation_engines_capsule = _LazyModule(
    "microcosm_core.organs.batch11_saturation_engines_capsule"
)
batch12_market_dashboard_read_model_capsule = _LazyModule(
    "microcosm_core.organs.batch12_market_dashboard_read_model_capsule"
)
batch12_prediction_market_board_capsule = _LazyModule(
    "microcosm_core.organs.batch12_prediction_market_board_capsule"
)
batch12_release_claim_language_gate = _LazyModule(
    "microcosm_core.organs.batch12_release_claim_language_gate"
)
bridge_phase_continuity_runtime = _LazyModule(
    "microcosm_core.organs.bridge_phase_continuity_runtime"
)
certificate_kernel_execution_lab = _LazyModule(
    "microcosm_core.organs.certificate_kernel_execution_lab"
)
cold_reader_route_map = _LazyModule("microcosm_core.organs.cold_reader_route_map")
corpus_readiness_mathlib_absence_gate = _LazyModule(
    "microcosm_core.organs.corpus_readiness_mathlib_absence_gate"
)
executable_doctrine_grammar = _LazyModule(
    "microcosm_core.organs.executable_doctrine_grammar"
)
doctrine_fact_claim_audit = _LazyModule(
    "microcosm_core.organs.doctrine_fact_claim_audit"
)
doctrine_lattice = _LazyModule("microcosm_core.doctrine_lattice")
finance_forecast_evaluation_spine = _LazyModule(
    "microcosm_core.organs.finance_forecast_evaluation_spine"
)
formal_math_lean_proof_witness = _LazyModule(
    "microcosm_core.organs.formal_math_lean_proof_witness"
)
formal_evidence_cell_anchor_resolver = _LazyModule(
    "microcosm_core.organs.formal_evidence_cell_anchor_resolver"
)
formal_math_premise_retrieval = _LazyModule(
    "microcosm_core.organs.formal_math_premise_retrieval"
)
formal_math_readiness_gate = _LazyModule(
    "microcosm_core.organs.formal_math_readiness_gate"
)
formal_math_verifier_trace_repair_loop = _LazyModule(
    "microcosm_core.organs.formal_math_verifier_trace_repair_loop"
)
indirect_prompt_injection_information_flow_policy_replay = _LazyModule(
    "microcosm_core.organs.indirect_prompt_injection_information_flow_policy_replay"
)
lean_std_premise_index = _LazyModule("microcosm_core.organs.lean_std_premise_index")
macro_projection_import_protocol = _LazyModule(
    "microcosm_core.organs.macro_projection_import_protocol"
)
materials_chemistry_closed_loop_lab_safety_replay = _LazyModule(
    "microcosm_core.organs.materials_chemistry_closed_loop_lab_safety_replay"
)
mathematical_strategy_atlas_hypothesis_scorer = _LazyModule(
    "microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer"
)
mcp_tool_authority_replay = _LazyModule(
    "microcosm_core.organs.mcp_tool_authority_replay"
)
mechanistic_interpretability_circuit_attribution_replay = _LazyModule(
    "microcosm_core.organs.mechanistic_interpretability_circuit_attribution_replay"
)
durable_agent_work_landing_replay = _LazyModule(
    "microcosm_core.organs.durable_agent_work_landing_replay"
)
mission_transaction_work_spine = _LazyModule(
    "microcosm_core.organs.mission_transaction_work_spine"
)
navigation_hologram_route_plane = _LazyModule(
    "microcosm_core.organs.navigation_hologram_route_plane"
)
pattern_binding_contract = _LazyModule("microcosm_core.organs.pattern_binding_contract")
prediction_oracle_reconciliation = _LazyModule(
    "microcosm_core.organs.prediction_oracle_reconciliation"
)
proof_diagnostic_evidence_spine = _LazyModule(
    "microcosm_core.organs.proof_diagnostic_evidence_spine"
)
proof_derived_governed_mutation_authorization = _LazyModule(
    "microcosm_core.organs.proof_derived_governed_mutation_authorization"
)
provider_context_recipe_budget_policy = _LazyModule(
    "microcosm_core.organs.provider_context_recipe_budget_policy"
)
public_reveal_walkthrough = _LazyModule(
    "microcosm_core.organs.public_reveal_walkthrough"
)
research_replication_rubric_artifact_replay = _LazyModule(
    "microcosm_core.organs.research_replication_rubric_artifact_replay"
)
ring2_premise_retrieval_precision_recall_harness = _LazyModule(
    "microcosm_core.organs.ring2_premise_retrieval_precision_recall_harness"
)
sleeper_memory_poisoning_quarantine_replay = _LazyModule(
    "microcosm_core.organs.sleeper_memory_poisoning_quarantine_replay"
)
self_ignorance_coverage_ledger = _LazyModule(
    "microcosm_core.organs.self_ignorance_coverage_ledger"
)
spatial_world_model_counterfactual_simulation_replay = _LazyModule(
    "microcosm_core.organs.spatial_world_model_counterfactual_simulation_replay"
)
cognitive_operator_registry = _LazyModule(
    "microcosm_core.organs.cognitive_operator_registry"
)
routing_anti_patterns_registry = _LazyModule(
    "microcosm_core.organs.routing_anti_patterns_registry"
)
tool_server_pressure_inventory = _LazyModule(
    "microcosm_core.organs.tool_server_pressure_inventory"
)
workstream_driver_recency_coalescer = _LazyModule(
    "microcosm_core.organs.workstream_driver_recency_coalescer"
)
standards_meta_diagnostics = _LazyModule(
    "microcosm_core.organs.standards_meta_diagnostics"
)
tactic_portfolio_availability_probe = _LazyModule(
    "microcosm_core.organs.tactic_portfolio_availability_probe"
)
target_shape_tactic_routing_gate = _LazyModule(
    "microcosm_core.organs.target_shape_tactic_routing_gate"
)
undeclared_library_prior_symbol_classifier = _LazyModule(
    "microcosm_core.organs.undeclared_library_prior_symbol_classifier"
)
verifier_lab_execution_spine = _LazyModule(
    "microcosm_core.organs.verifier_lab_execution_spine"
)
verifier_lab_kernel = _LazyModule("microcosm_core.organs.verifier_lab_kernel")
voice_to_doctrine_self_improvement_loop = _LazyModule(
    "microcosm_core.organs.voice_to_doctrine_self_improvement_loop"
)
world_model_projection_drift_control_room = _LazyModule(
    "microcosm_core.organs.world_model_projection_drift_control_room"
)
acceptance = _LazyModule("microcosm_core.validators.acceptance")
dependency_preflight = _LazyModule("microcosm_core.validators.dependency_preflight")
fixture_freshness = _LazyModule("microcosm_core.validators.fixture_freshness")
launch_compression = _LazyModule("microcosm_core.validators.launch_compression")
observatory_legibility = _LazyModule("microcosm_core.validators.observatory_legibility")
private_state_scan = _LazyModule("microcosm_core.validators.private_state_scan")
public_entry_docs = _LazyModule("microcosm_core.validators.public_entry_docs")
research_kernel_density = _LazyModule("microcosm_core.validators.research_kernel_density")
secret_exclusion_scan = _LazyModule("microcosm_core.validators.secret_exclusion_scan")
standards_registry = _LazyModule("microcosm_core.validators.standards_registry")
transaction_evidence_stability = _LazyModule(
    "microcosm_core.validators.transaction_evidence_stability"
)


def _read_json_strict(path: Path):
    from microcosm_core.schemas import read_json_strict

    return read_json_strict(path)


def _write_json_atomic(path: Path, payload: dict) -> None:
    from microcosm_core.receipts import write_json_atomic

    write_json_atomic(path, payload)


def _public_root_for_project(project: str | None) -> Path | None:
    return resource_root.project_public_root(project)


def _runtime_project_arg(project: str | None) -> str | None:
    if project is None:
        return None

    path = Path(project).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return str(path.resolve(strict=False))


def _runtime_root_for_project_arg(project: str | None) -> Path | None:
    return _public_root_for_project(project)


def _cli_project_command_ref(project: str | None) -> str | None:
    if project is None:
        return None
    text = str(project).strip()
    if not text:
        return "<project>"
    path = Path(text)
    if text.startswith("~") or path.is_absolute() or ".." in path.parts:
        return "<project>"
    return text


def _replace_project_placeholder(value, project_ref: str):
    if isinstance(value, str):
        return value.replace("<project>", project_ref)
    if isinstance(value, list):
        return [_replace_project_placeholder(item, project_ref) for item in value]
    if isinstance(value, dict):
        return {
            key: _replace_project_placeholder(item, project_ref)
            for key, item in value.items()
        }
    return value


def _status_card_project_ref(payload: dict) -> str:
    front_door = payload.get("front_door")
    front_door_project_ref = (
        front_door.get("project_ref") if isinstance(front_door, dict) else None
    )
    project_ref = payload.get("project_ref") or front_door_project_ref
    return str(project_ref or "<project>")


MICROCOSM_ROOT = _LazyPath(lambda: resource_root.microcosm_root())
DEFAULT_PROJECT_REL = "examples/runtime_shell/demo_project"
PROOF_LAB_BUNDLE_REF = "examples/verifier_lab_kernel/exported_verifier_lab_kernel_bundle"
PROOF_LAB_ROUTE_REF = f"{PROOF_LAB_BUNDLE_REF}/proof_lab_route.json"
PROOF_LAB_RECEIPT_REF = (
    "receipts/first_wave/verifier_lab_kernel/"
    "exported_verifier_lab_kernel_bundle_validation_result.json"
)
DEFAULT_PROOF_LAB_INPUT = _LazyPath(lambda: MICROCOSM_ROOT / PROOF_LAB_BUNDLE_REF)
DEFAULT_PROOF_LAB_OUT = "/tmp/microcosm-proof-lab"
PROOF_LAB_INPUT_PLACEHOLDER = "<proof-lab-input>"
PROOF_LAB_OUT_PLACEHOLDER = "<proof-lab-out>"
OBSERVATORY_SERVE_COMMAND = (
    "microcosm serve <project> --host 127.0.0.1 --port 8765"
)
OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT = 7
OBSERVATORY_BOUNDED_VALIDATION_COMMAND = (
    f"{OBSERVATORY_SERVE_COMMAND} "
    f"--max-requests {OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT}"
)
OBSERVATORY_BOUNDED_VALIDATION_RULE = (
    "Use bounded_validation_command for route smokes; use command for interactive sessions."
)
PROOF_LAB_FIRST_SCREEN_AUTHORITY = (
    "first-screen proof-lab route and receipt-status card only; not proof "
    "correctness, provider execution, source mutation, release, publication, "
    "or credential-equivalent live-access authority"
)
PROOF_LAB_FIRST_SCREEN_ANTI_CLAIMS = {
    "proof_correctness_claim": False,
    "provider_calls_authorized": False,
    "source_mutation_authorized": False,
    "release_or_publication_authorized": False,
    "credential_equivalent_live_access_exported": False,
    "proof_bodies_or_provider_payloads_exported": False,
}

FIRST_SCREEN_HELP = """First-screen route:
  microcosm hello <project>      print the cold-entry one-screen card (--card accepted)
  microcosm hello --reader {cold_cloner|skeptical_reviewer|agent|domain_specialist} <project> branch by reader
  reader aliases: cold-cloner, interesting-parts, skeptical-reviewer, reviewer, type-a-agent, domain-specialist
  microcosm tour --card <project> build .microcosm and read route/state/proof refs
  microcosm first-screen --card <project> emit the compact JSON first-screen card
  microcosm agent-entry-composition --task {agent-entry|getting-started|evaluation|receipts|agent-evaluation|ai-safety|finance|formal-methods|lean|theorem-proving|interesting-parts|architecture|navigation|security|compliance|reviewer} emit Type A/human route card
  microcosm status --card <project> read the compressed project/runtime status lens
  microcosm status-card <project> alias for the compact status lens
  microcosm spine --card          read the compact runtime spine lens
  microcosm run --card examples/runtime_shell/demo_project replay the public runtime demo
  microcosm authority --card      read the compact authority ceiling lens
  microcosm intake --card         read the compact intake/projection bridge lens
  microcosm workingness --card    read the compact behavior/failure lens
  microcosm workingness           inspect behavior evidence and failure gaps
  microcosm proof-lab --card      read the cached verifier-lab receipt card
  microcosm proof-lab --out /tmp/microcosm-proof-lab
  microcosm observe --card <project> read compact route/work/event/evidence refs
  microcosm observe <project>     inspect route/work/event/evidence chain
  microcosm serve <project>       open the local observatory
  microcosm compile --card <project> read cached .microcosm state; stale cache exits 1
  microcosm compile <project>     rebuild local .microcosm state after the first-screen check
  microcosm tour <project>        inspect full route cards, endpoint path, and evidence refs
Boundaries: local-first only; no provider calls, source mutation, release,
hosting, proof-correctness, or credential-equivalent live-access authority.
Receipts are evidence drilldowns after the behavior route is visible.
"""

STATUS_CARD_HELP = """Reads the compact project/runtime status lens.

Equivalent command:
  microcosm status --card <project>

Next command:
  microcosm tour --card <project>

Boundaries: local-first only; no provider calls, source mutation, release,
hosting, proof-correctness, or credential-equivalent live-access authority.
"""

STATUS_HELP_EPILOG = """Cold-clone check path:
  microcosm status --card <project>
  make check
  make smoke
  make ci

Interpretation:
  The status card is the compact route/state/evidence lens after the first
  local run. `make check` is the fast preflight, `make smoke` validates the
  public smoke route, and `make ci` is the public green floor. None of these
  commands authorize release, provider calls, source mutation, proof
  correctness, private-root equivalence, or whole-system correctness.
"""

EVIDENCE_INSPECT_HELP = """Reads one evidence card.

Interpretation:
  status=pass means the inspect command produced the card; it is not release,
  proof-correctness, trading, security, or private-root equivalence authority.
  payload_summary is the safe shape/ref summary of the underlying receipt;
  inspect cards do not export source bodies.
  Use full_payload_drilldown.command when you need the complete local JSON
  behind the compact card, then use evidence_ref and schema_version to decide
  whether you need the owning validator/builder.
"""

EVIDENCE_LIST_HELP = """Lists compact evidence refs.

Reviewer path:
  microcosm evidence list <project> --limit 25
  microcosm evidence inspect --project <project> <evidence_ref>

Interpretation:
  The list is a bounded receipt index after behavior is visible, not a release
  badge or proof of correctness. Use evidence_ref plus schema_version to choose
  the next inspect card or owning validator/builder.
"""

EVIDENCE_HELP_EPILOG = """Reviewer path:
  microcosm evidence list <project> --limit 25
  microcosm evidence inspect --project <project> <evidence_ref>

Interpretation:
  Receipts are evidence drilldowns after behavior is visible. They can show
  source refs, schema versions, command witnesses, and boundary fields; they do
  not by themselves authorize release, provider calls, source mutation, proof
  correctness, trading advice, private-root equivalence, or whole-system
  correctness.
"""

PUBLIC_LENS_COMMAND_HELP = (
    ("workingness", "show behavior evidence and failure modes"),
    ("prediction-lens", "inspect prediction ledger behavior and receipts"),
    ("market-boundary", "show source-open market-boundary anti-claim lens"),
    ("corpus-lens", "inspect corpus readiness and evidence density"),
    ("trace-lens", "inspect route/event trace evidence"),
    ("repair-loop", "show verifier trace repair-loop surface"),
    ("evidence-cells", "show formal evidence cell status"),
    ("proof-loop-depth", "inspect proof loop depth without proving correctness"),
    ("verifier-lab-execution-spine-lens", "show verifier lab execution spine lens"),
    ("landing-replay", "replay durable work-landing control behavior"),
    ("view-quality", "check observatory/read-model quality gates"),
    ("projection-safety", "inspect projection safety and exclusion guards"),
    ("drift-control", "show world-model projection drift controls"),
    ("spatial-simulation", "replay spatial world-model simulation specimen"),
    ("circuit-attribution", "replay mechanistic circuit attribution specimen"),
    ("route-cleanup", "show navigation route cleanup evidence"),
    ("projection-import-map", "map macro projection import cells"),
    ("import-projector", "run source-open projection import preview"),
    ("option-surface-lens", "inspect local option-surface routing lens"),
    ("stripping-guard", "show credential stripping boundary checks"),
    ("standards-control", "inspect standards control-plane diagnostics"),
    ("hook-coverage", "show hook coverage and guardrail evidence"),
    ("replay-gauntlet", "run accepted replay gauntlet surface"),
    ("benchmark-lab", "show benchmark integrity replay lab"),
    ("legibility-scorecard", "inspect first-screen legibility and boundary gaps"),
    ("intake", "show runtime projection intake board"),
    ("reveal", "show public reveal walkthrough board"),
)
PUBLIC_LENS_COMMANDS = frozenset(command for command, _ in PUBLIC_LENS_COMMAND_HELP)
PUBLIC_LENS_CARD_AWARE_COMMANDS = frozenset(
    {"circuit-attribution", "intake", "workingness"}
)
PUBLIC_LENS_EPILOGS = {
    "workingness": """Skeptical-reviewer route:
  microcosm workingness --card
  microcosm workingness

Boundary: status describes map generation, while card_status describes bounded
failure-envelope debt. Accepted status and source-body counts are not evidence
strength, release readiness, score progress, or whole-system correctness.
""",
    "evidence-cells": """Formal-methods reader route:
  microcosm evidence-cells --card .

Boundary: resolves proof-language claims to public evidence-cell metadata and
receipt refs. It does not run Lean/Lake, expose proof bodies, certify theorem
correctness, call providers, mutate source, or authorize release.
""",
    "proof-loop-depth": """Formal-methods reader route:
  microcosm proof-loop-depth --card .

Boundary: maps the public formal-math gate chain and receipt refs as metadata.
It does not run Lean/Lake, prove theorem correctness, export proof bodies,
claim benchmark performance, call providers, mutate source, or authorize
release.
""",
    "legibility-scorecard": """Repo-reading agent route:
  microcosm legibility-scorecard
  PYTHONPATH=src python3 -m microcosm_core legibility-scorecard

Boundary: reports first-screen legibility and boundary gaps as a public
read-model. It does not prove reader comprehension, authorize release or
publication, claim private-root equivalence, call providers, mutate source,
prove mathematical correctness, create benchmark/score progress authority, or
certify production readiness.
""",
}

AUTHORITY_HELP_EPILOG = """Skeptical-reviewer route:
  microcosm authority --card
  microcosm authority

Boundary: the authority card exposes false ceilings and count scopes before the
full map. A passing card does not authorize release, provider calls, source
mutation, proof correctness, trading advice, private-root equivalence, or
whole-system correctness.
"""

AGENT_ENTRY_COMPOSITION_HELP_EPILOG = """Task selector examples:
  microcosm agent-entry-composition --task agent-entry --viewer human --card --check
  microcosm agent-entry-composition --task evaluation --viewer human --card --check
  microcosm agent-entry-composition --task ai-safety --viewer human --card --check

Alias note: reviewer, skeptical-reviewer, and skeptical-review route to the
ai-safety task route. Use evaluation for the cold route-map/receipt evaluator
path; receipt/evidence meaning, review, risk, and brokenness questions route
there too. Use agent-entry for the general cold-agent entry path; "What is
this?" routes there too. "What is interesting here?" routes to
interesting-parts. "Show me formal methods" routes to formal-methods. "Show me
AI safety" routes to ai-safety.

Boundary: this card selects public route metadata and first commands; it does
not authorize release, provider calls, source mutation, private-root
equivalence, proof correctness, trading advice, or whole-system correctness.
"""

PUBLIC_BUNDLE_COMMAND_HELP = {
    "pattern-binding": "validate exported pattern/source-route bundles",
    "pattern-route-readiness": "validate pattern route-readiness bundle",
    "crown-jewel-demo": "run the Crown Jewel import demo sequence",
    "macro-engines-gallery": "run accepted macro engines gallery",
    "engine-room-demo": "run the Engine Room composition demo",
    "agent-closeout-faithfulness-audit": "run closeout faithfulness audit bundle",
    "doctrine-fact-claim-audit": "run doctrine fact-claim audit bundle",
    "self-ignorance-coverage-ledger": "run self-ignorance coverage ledger bundle",
    "bounded-autonomy-campaign-packet": "run bounded autonomy campaign packet bundle",
    "batch4-proof-authority-runtime": "run Batch 4 proof authority runtime bundle",
    "batch5-authority-systems-capsule": "run Batch 5 authority systems capsule",
    "batch6-unsurfaced-primitives-capsule": "run Batch 6 unsurfaced primitives capsule",
    "batch7-demo-take-console-capsule": "run Batch 7 Demo Take console capsule",
    "batch7-macro-engines-capsule": "run Batch 7 macro engines capsule",
    "batch7-oracle-sibling-capsule": "run Batch 7 oracle sibling capsule",
    "batch7-secondary-runtime-capsule": "run Batch 7 secondary runtime capsule",
    "batch7-station-runtime-capsule": "run Batch 7 station runtime capsule",
    "batch8-tools-tail-primitives-capsule": "run Batch 8 tools-tail primitives capsule",
    "batch8-policy-engines-capsule": "run Batch 8 policy engines capsule",
    "batch8-audio-level-rms-port": "run Batch 8 audio RMS normalized-level port",
    "batch8-station-surface-atlas-layout-port": "run Batch 8 StationSurfaceAtlas layout port",
    "batch8-structural-theses-capsule": "run Batch 8 structural theses capsule",
    "batch8-compliance-pipeline-capsule": "run Batch 8 compliance pipeline capsule",
    "batch8-validator-checker-capsule": "run Batch 8 validator checker capsule",
    "concurrency-mission-control": "run concurrency mission-control capsule",
    "batch9-macro-engines-capsule": "run Batch 9 macro engines capsule",
    "batch10-governance-compilers-capsule": "run Batch 10 governance compilers capsule",
    "batch10-frontend-work-market-cockpit-capsule": "run Batch 10 frontend work-market cockpit capsule",
    "batch10-live-source-drift-capsule": "run Batch 10 live source drift capsule",
    "batch10-cold-eval-honesty-capsule": "run Batch 10 cold eval honesty capsule",
    "batch11-saturation-engines-capsule": "run Batch 11 saturation engines capsule",
    "batch12-market-dashboard-read-model-capsule": "run Batch 12 market dashboard read-model capsule",
    "batch12-prediction-market-board-capsule": "run Batch 12 prediction market board capsule",
    "batch12-release-claim-language-gate": "run Batch 12 release claim-language gate",
    "finance-forecast-evaluation-spine": "run finance forecast-evaluation bundle",
    "finance-eval-spine": "validate finance-evaluation fixture bundle",
    "work-landing-control-spine": "validate work-landing control bundle",
    "executable-doctrine-grammar": "validate executable doctrine bundles",
    "proof-diagnostic-evidence-spine": "run proof diagnostic evidence bundle",
    "formal-math-readiness-gate": "run formal math readiness bundle",
    "corpus-readiness-mathlib-absence-gate": "run corpus readiness bundle",
    "mathematical-strategy-atlas-hypothesis-scorer": "run strategy atlas bundle",
    "tactic-portfolio-availability-probe": "run tactic availability bundle",
    "target-shape-tactic-routing-gate": "run target-shape routing bundle",
    "formal-math-lean-proof-witness": "run Lean proof witness bundle",
    "formal-math-premise-retrieval": "run premise retrieval bundle",
    "formal-math-verifier-trace-repair-loop": "run verifier trace repair bundle",
    "verifier-lab-kernel": "run verifier lab kernel bundle",
    "verifier-lab-execution-spine": "run verifier lab execution bundle",
    "certificate-kernel-execution-lab": "run certificate kernel lab bundle",
    "formal-evidence-cell-anchor-resolver": "run evidence-cell anchor bundle",
    "undeclared-library-prior-symbol-classifier": "run symbol classifier bundle",
    "agent-benchmark-integrity-anti-gaming-replay": "run benchmark integrity replay bundle",
    "agent-monitor-redteam-falsification-replay": "run monitor red-team replay bundle",
    "agent-sabotage-scheming-monitor-replay": "run sabotage monitor replay bundle",
    "agent-sandbox-policy-escape-replay": "run sandbox policy replay bundle",
    "indirect-prompt-injection-information-flow-policy-replay": "run prompt-injection replay bundle",
    "agentic-vulnerability-discovery-patch-proof-replay": "run patch-proof replay bundle",
    "agent-memory-temporal-conflict-replay": "run memory conflict replay bundle",
    "sleeper-memory-poisoning-quarantine-replay": "run sleeper-memory quarantine bundle",
    "mcp-tool-authority-replay": "run MCP tool-authority replay bundle",
    "proof-derived-governed-mutation-authorization": "run governed mutation bundle",
    "belief-state-process-reward-replay": "run belief-state reward replay bundle",
    "lean-std-premise-index": "run Lean std premise index bundle",
    "provider-context-recipe-budget-policy": "run provider context budget bundle",
    "ring2-premise-retrieval-precision-recall-harness": "run Ring 2 precision/recall bundle",
    "durable-agent-work-landing-replay": "run durable work-landing replay bundle",
    "research-replication-rubric-artifact-replay": "run research replication bundle",
    "world-model-projection-drift-control-room": "run projection drift-control bundle",
    "spatial-world-model-counterfactual-simulation-replay": "run spatial simulation bundle",
    "materials-chemistry-closed-loop-lab-safety-replay": "run materials lab-safety bundle",
    "mechanistic-interpretability-circuit-attribution-replay": "run circuit attribution bundle",
    "public-reveal-walkthrough": "run public reveal walkthrough bundle",
    "macro-projection-import-protocol": "run macro projection import bundle",
    "prediction-oracle-reconciliation": "run prediction reconciliation bundle",
    "standards-meta-diagnostics": "run standards meta-diagnostics bundle",
    "cold-reader-route-map": "run cold-reader route-map bundle",
    "navigation-hologram-route-plane": "validate navigation route-plane bundle",
    "mission-transaction-work-spine": "validate mission transaction bundle",
    "agent-route-observability-runtime": "validate route observability bundles",
    "bridge-phase-continuity-runtime": "run bridge continuity bundle",
    "pattern-assimilation-step": "validate pattern assimilation bundle",
    "voice-to-doctrine-self-improvement-loop": "run voice-to-doctrine bundle",
    "cognitive-operator-registry": "run cognitive-operator-registry bundle",
    "routing-anti-patterns-registry": "run routing anti-patterns registry bundle",
    "tool-server-pressure-inventory": "run tool-server pressure inventory bundle",
    "workstream-driver-recency-coalescer": "run workstream driver recency coalescer bundle",
}

PUBLIC_BUNDLE_COMMAND_EPILOGS = {
    "cold-reader-route-map": """Runnable fixture example:
  microcosm cold-reader-route-map run-route-map-bundle --input examples/cold_reader_route_map/exported_cold_reader_route_map_bundle --out /tmp/microcosm-cold-reader-route-map

Boundary: validates the declared public route-map bundle and writes receipts.
It is projection-only route metadata, not route-registry authority, source
mutation permission, provider-call authority, release/publication authority,
financial advice, private-data equivalence, or whole-system correctness.
""",
    "finance-forecast-evaluation-spine": """Runnable fixture example:
  microcosm finance-forecast-evaluation-spine run --input fixtures/first_wave/finance_forecast_evaluation_spine/input --out /tmp/microcosm-finance-forecast-evaluation-spine

Boundary: validates synthetic forecast-evaluation fixtures and writes receipts.
It is not investment or trading advice, uses no live market data, claims no
track record or performance result, mutates no optimizer, and does not
authorize release.
""",
    "proof-diagnostic-evidence-spine": """Runnable fixture example:
  microcosm proof-diagnostic-evidence-spine run --input fixtures/first_wave/proof_diagnostic_evidence_spine/input --out /tmp/microcosm-proof-diagnostic-evidence-spine

Boundary: validates declared proof-diagnostic evidence metadata and writes
receipts. It does not run Lean/Lake, prove theorem correctness, expose proof
bodies, call providers, mutate source, turn a passing check into proof
authority, or authorize release/publication.
""",
    "formal-math-readiness-gate": """Runnable fixture example:
  microcosm formal-math-readiness-gate run --input fixtures/first_wave/formal_math_readiness_gate/input --out /tmp/microcosm-formal-readiness-gate

Boundary: validates declared formal-math readiness metadata and writes receipts.
It does not run Lean/Lake, claim Mathlib availability beyond probe status,
prove theorem correctness, expose proof bodies, call providers, mutate source,
or authorize release.
""",
    "public-reveal-walkthrough": """Runnable fixture example:
  microcosm public-reveal-walkthrough run --input fixtures/first_wave/public_reveal_walkthrough/input --out /tmp/microcosm-public-reveal-walkthrough

Boundary: validates bounded public reveal behavior and writes receipts. It does
not authorize release, hosted deployment, publication, recipient work, provider
calls, secret export, private-data equivalence, proof correctness, trading
advice, or whole-system correctness.
""",
    "agent-benchmark-integrity-anti-gaming-replay": """Runnable fixture example:
  microcosm agent-benchmark-integrity-anti-gaming-replay run-benchmark-integrity-bundle --input examples/agent_benchmark_integrity_anti_gaming_replay/exported_benchmark_integrity_bundle --out /tmp/microcosm-agent-benchmark-integrity

Boundary: validates a public benchmark-integrity replay bundle and writes
receipts. It does not run a live benchmark, score agent capability, call
providers, access private or hidden-gold bodies, mutate source, claim product
progress, or authorize release.
""",
}


def _add_root_out(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", required=True)


def _add_input_out(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)


def _add_input_out_acceptance(parser: argparse.ArgumentParser) -> None:
    _add_input_out(parser)
    parser.add_argument("--acceptance-out")


def _organ_command_args(args: argparse.Namespace) -> list[str]:
    organ_args = [args.action, "--input", args.input, "--out", args.out]
    acceptance_out = getattr(args, "acceptance_out", None)
    if acceptance_out:
        organ_args.extend(["--acceptance-out", acceptance_out])
    return organ_args


def _add_preflight(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--readiness", required=True)
    parser.add_argument("--negative-matrix", required=True)
    parser.add_argument("--out", required=True)


def _add_public_lens_parsers(subparsers) -> None:
    compact_card_help = {
        "spine": "emit the compact first-screen spine lens",
        "workingness": "emit the compact first-screen workingness lens",
        "intake": "emit the compact first-screen intake lens",
        "projection-import-map": "emit the compact public projection import map lens",
        "import-projector": "emit the compact public import-projector contract lens",
    }
    for command, help_text in PUBLIC_LENS_COMMAND_HELP:
        kwargs = {"help": help_text}
        epilog = PUBLIC_LENS_EPILOGS.get(command)
        if epilog:
            kwargs["description"] = help_text
            kwargs["epilog"] = epilog
            kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
        parser = subparsers.add_parser(command, **kwargs)
        parser.add_argument(
            "--card",
            action="store_true",
            help=compact_card_help.get(
                command,
                "accepted as a public lens alias; this command already emits JSON",
            ),
        )
        parser.add_argument(
            "project",
            nargs="?",
            help=(
                "accepted for first-screen parity; this public lens remains "
                "Microcosm-rooted"
            ),
        )


ROOT_HELP_BUNDLE_COMMANDS: frozenset[str] = frozenset(
    {
        "pattern-route-readiness",
        "finance-forecast-evaluation-spine",
        "finance-eval-spine",
        "executable-doctrine-grammar",
        "formal-math-readiness-gate",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "macro-projection-import-protocol",
        "agent-route-observability-runtime",
        "bridge-phase-continuity-runtime",
        "voice-to-doctrine-self-improvement-loop",
        "routing-anti-patterns-registry",
    }
)


def _add_bundle_parser(subparsers, command: str) -> argparse.ArgumentParser:
    help_text = PUBLIC_BUNDLE_COMMAND_HELP[command]
    kwargs = {"description": help_text}
    epilog = PUBLIC_BUNDLE_COMMAND_EPILOGS.get(command)
    if epilog:
        kwargs["epilog"] = epilog
        kwargs["formatter_class"] = argparse.RawDescriptionHelpFormatter
    if command in ROOT_HELP_BUNDLE_COMMANDS:
        kwargs["help"] = help_text
    return subparsers.add_parser(command, **kwargs)


def _print_json(payload: dict, *, exit_code: int | None = None) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    if exit_code is not None:
        return exit_code
    return 0 if payload.get("status") == "pass" else 1


def _status_card_exit_code(payload: dict) -> int:
    if payload.get("status") == "pass":
        return 0
    front_door_status = payload.get("front_door_status")
    front_door = payload.get("front_door")
    if not isinstance(front_door_status, dict) or not isinstance(front_door, dict):
        return 1
    blocking_surface_ids = set(front_door_status.get("blocking_surface_ids") or [])
    if not blocking_surface_ids:
        return 1
    if not blocking_surface_ids.issubset({"project_state", "state_write_proof"}):
        return 1
    project_state = front_door.get("project_state")
    project_recovery = front_door.get("project_recovery")
    if not isinstance(project_state, dict) or not isinstance(project_recovery, dict):
        return 1
    if project_state.get("status") != "missing_state":
        return 1
    if project_recovery.get("status") != "actionable":
        return 1
    primary_command = project_recovery.get("primary_command")
    if not (
        isinstance(primary_command, str)
        and primary_command.startswith("microcosm tour --card ")
    ):
        return 1
    return 0


def _proof_lab_card_exit_code(payload: dict) -> int:
    if payload.get("status") == "pass":
        return 0
    cache_action = payload.get("cache_action")
    if (
        payload.get("status") == "stale_cached_receipt"
        and isinstance(cache_action, dict)
        and cache_action.get("status") == "actionable"
    ):
        return 0
    return 1


def _project_evidence_state_boundary(project_arg: str) -> dict | None:
    project = Path(project_arg).expanduser()
    if not _path_exists(project):
        return {
            "schema_version": "microcosm_project_evidence_state_boundary_v1",
            "status": "missing_project",
            "project_id": project.name or project_arg,
            "project_ref": project_arg,
            "state_ref": ".microcosm",
            "state_dir_exists": False,
            "evidence_count": 0,
            "evidence": [],
            "release_authorized": False,
            "receipts_are_drilldown_evidence": True,
            "reader_action": (
                "Pass an existing project path, then run microcosm tour --card "
                "<project> before evidence drilldown."
            ),
        }
    state_dir = project / ".microcosm"
    if not _path_is_dir(state_dir):
        return {
            "schema_version": "microcosm_project_evidence_state_boundary_v1",
            "status": "missing_state",
            "project_id": project.name or project_arg,
            "project_ref": project_arg,
            "state_ref": ".microcosm",
            "state_dir_exists": False,
            "evidence_count": 0,
            "evidence": [],
            "release_authorized": False,
            "receipts_are_drilldown_evidence": True,
            "reader_action": (
                "Run microcosm tour --card <project> to create .microcosm "
                "state before evidence drilldown."
            ),
        }
    return None


def _proof_lab_first_screen_boundary() -> dict:
    return {
        "authority": PROOF_LAB_FIRST_SCREEN_AUTHORITY,
        "anti_claims": dict(PROOF_LAB_FIRST_SCREEN_ANTI_CLAIMS),
    }


def _proof_lab_cache_action_hint(cache_status: object) -> dict:
    if cache_status == "stale_cached_receipt":
        return {
            "status": "actionable",
            "command": f"microcosm proof-lab --out {DEFAULT_PROOF_LAB_OUT}",
            "boundary": "fresh_tmp_receipt_not_canonical_or_proof_authority",
        }
    if cache_status == "missing_cached_receipt":
        return {
            "status": "missing_cached_receipt",
            "command": f"microcosm proof-lab --out {DEFAULT_PROOF_LAB_OUT}",
            "boundary": "fresh_tmp_receipt_not_canonical_or_proof_authority",
        }
    return {
        "status": "not_needed",
    }


def _proof_lab_fresh_receipt_required(cache_status: object) -> bool:
    return cache_status in {"stale_cached_receipt", "missing_cached_receipt"}


def _proof_lab_status_scope(cache_status: object) -> str:
    if _proof_lab_fresh_receipt_required(cache_status):
        return "route_presence_not_cache_freshness"
    return "route_presence_and_cache_freshness"


def _emit_hello(project: str, reader: str) -> int:
    payload = first_screen_composition.first_screen_composition_card(
        project_label=project
    )
    print(
        first_screen_composition.first_screen_text_card(
            payload,
            reader_id=reader,
        ),
        end="",
    )
    return 0 if payload.get("status") == "pass" else 1


def _emit_first_screen(project: str, *, output_format: str, full: bool, reader: str) -> int:
    payload = first_screen_composition.first_screen_composition_card(
        project_label=project
    )
    if output_format == "text":
        print(
            first_screen_composition.first_screen_text_card(
                payload,
                reader_id=reader,
            ),
            end="",
        )
        return 0 if payload.get("status") == "pass" else 1
    if full:
        return _print_json(payload)
    return _print_json(first_screen_composition.first_screen_compact_card(payload))


def _first_screen_fast_path(argv: list[str] | None) -> int | None:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if not raw_argv:
        return None

    if raw_argv[0] == "hello":
        parser = argparse.ArgumentParser(
            prog="microcosm hello",
            description="Print the cold-entry first-screen card.",
        )
        parser.add_argument(
            "--reader",
            choices=TEXT_READER_CHOICES,
            default="all",
            help="focus the terminal projection on one reader branch",
        )
        parser.add_argument(
            "--format",
            choices=("text",),
            default="text",
            help="accepted for first-screen parity; hello always emits text",
        )
        parser.add_argument(
            "--card",
            action="store_true",
            help="accepted for first-screen parity; hello always emits text",
        )
        parser.add_argument("project", nargs="?", default="<project>")
        args = parser.parse_args(raw_argv[1:])
        return _emit_hello(args.project, args.reader)

    if raw_argv[0] == "first-screen":
        parser = argparse.ArgumentParser(
            prog="microcosm first-screen",
            description="Preview the one-screen reader route map.",
        )
        parser.add_argument(
            "--format",
            choices=("json", "text"),
            default="json",
            help="emit the JSON machine card or terminal projection",
        )
        parser.add_argument(
            "--card",
            action="store_true",
            help="accepted as a compact JSON card alias",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="emit the full first-screen contract JSON instead of the compact projection",
        )
        parser.add_argument(
            "--reader",
            choices=TEXT_READER_CHOICES,
            default="all",
            help="focus the terminal projection on one reader branch",
        )
        parser.add_argument("project", nargs="?", default="<project>")
        args = parser.parse_args(raw_argv[1:])
        return _emit_first_screen(
            args.project,
            output_format=args.format,
            full=args.full,
            reader=args.reader,
        )

    return None


def _public_ref(path_ref: str) -> str:
    path = Path(path_ref)
    try:
        relative = path.resolve(strict=False).relative_to(MICROCOSM_ROOT)
    except ValueError:
        return path_ref
    return relative.as_posix()


def _display_local_ref(path_ref: str, *, placeholder: str) -> str:
    public_ref = _public_ref(path_ref)
    if public_ref != path_ref:
        return public_ref

    path = Path(path_ref)
    if not path.is_absolute():
        return path_ref

    raw_ref = path.as_posix()
    if raw_ref == "/private/tmp":
        return "/tmp"
    if raw_ref.startswith("/private/tmp/"):
        return f"/tmp/{raw_ref.removeprefix('/private/tmp/')}"
    if raw_ref == "/tmp" or raw_ref.startswith("/tmp/"):
        return raw_ref
    return placeholder


def _proof_lab_input_ref(input_path: str) -> str:
    return _display_local_ref(input_path, placeholder=PROOF_LAB_INPUT_PLACEHOLDER)


def _proof_lab_output_ref(out_dir: str) -> str:
    return _display_local_ref(out_dir, placeholder=PROOF_LAB_OUT_PLACEHOLDER)


def _proof_lab_command(input_path: str, out_dir: str) -> str:
    display_input = _proof_lab_input_ref(input_path)
    display_out = _proof_lab_output_ref(out_dir)
    if display_input == _public_ref(str(DEFAULT_PROOF_LAB_INPUT)):
        return f"microcosm proof-lab --out {display_out}"
    return f"microcosm proof-lab --input {display_input} --out {display_out}"


def _proof_lab_card_command(input_path: str, out_dir: str) -> str:
    display_input = _proof_lab_input_ref(input_path)
    display_out = _proof_lab_output_ref(out_dir)
    if display_input == _public_ref(str(DEFAULT_PROOF_LAB_INPUT)):
        return f"microcosm proof-lab --card --out {display_out}"
    return f"microcosm proof-lab --card --input {display_input} --out {display_out}"


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _path_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _path_mtime_ns(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _path_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _iter_proof_lab_input_files(input_path: str) -> Iterator[Path]:
    input_ref = Path(input_path)
    if not _path_exists(input_ref):
        return
    if _path_is_file(input_ref):
        yield input_ref
        return
    pending = [input_ref]
    while pending:
        current = pending.pop()
        child_dirs: list[Path] = []
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        entry_path = Path(entry.path)
                        if entry.is_dir(follow_symlinks=False):
                            child_dirs.append(entry_path)
                        elif entry.is_file(follow_symlinks=False):
                            yield entry_path
                    except OSError:
                        continue
        except OSError:
            continue
        pending.extend(reversed(sorted(child_dirs)))


def _proof_lab_input_files(input_path: str) -> list[Path]:
    return sorted(_iter_proof_lab_input_files(input_path))


def _proof_lab_cache_freshness(input_path: str, receipt_path: Path) -> dict:
    input_ref = Path(input_path)
    receipt_mtime_ns = _path_mtime_ns(receipt_path)
    if receipt_mtime_ns is None:
        return {
            "schema_version": "microcosm_proof_lab_cache_freshness_v1",
            "status": "missing_cached_receipt",
            "input_status": "unreadable_cached_receipt",
            "receipt_mtime_ns": None,
            "tracked_input_count": 0,
            "stale_input_count": 0,
            "latest_input_mtime_ns": None,
            "input_refs_exported": False,
        }
    if not _path_exists(input_ref):
        return {
            "schema_version": "microcosm_proof_lab_cache_freshness_v1",
            "status": "stale",
            "input_status": "missing_input",
            "receipt_mtime_ns": receipt_mtime_ns,
            "tracked_input_count": 0,
            "stale_input_count": 0,
            "latest_input_mtime_ns": None,
            "input_refs_exported": False,
        }

    if (
        input_ref.resolve(strict=False)
        == (
            resource_root.installed_microcosm_root() / PROOF_LAB_BUNDLE_REF
        ).resolve(strict=False)
    ):
        tracked_input_count = sum(1 for _ in _iter_proof_lab_input_files(input_path))
        if tracked_input_count:
            return {
                "schema_version": "microcosm_proof_lab_cache_freshness_v1",
                "status": "current",
                "input_status": "packaged_public_data",
                "receipt_mtime_ns": receipt_mtime_ns,
                "tracked_input_count": tracked_input_count,
                "stale_input_count": 0,
                "latest_input_mtime_ns": None,
                "input_refs_exported": False,
            }

    latest_input_mtime_ns: int | None = None
    stale_input_count = 0
    tracked_input_count = 0
    for input_file in _iter_proof_lab_input_files(input_path):
        try:
            input_mtime_ns = input_file.stat().st_mtime_ns
        except OSError:
            continue
        latest_input_mtime_ns = (
            input_mtime_ns
            if latest_input_mtime_ns is None
            else max(latest_input_mtime_ns, input_mtime_ns)
        )
        tracked_input_count += 1
        if input_mtime_ns > receipt_mtime_ns:
            stale_input_count += 1

    input_status = "stale" if stale_input_count else "current"
    return {
        "schema_version": "microcosm_proof_lab_cache_freshness_v1",
        "status": "stale" if stale_input_count else "current",
        "input_status": input_status,
        "receipt_mtime_ns": receipt_mtime_ns,
        "tracked_input_count": tracked_input_count,
        "stale_input_count": stale_input_count,
        "latest_input_mtime_ns": latest_input_mtime_ns,
        "input_refs_exported": False,
    }


def _proof_lab_cached_result(input_path: str, out_dir: str) -> dict:
    receipt_path = Path(out_dir) / verifier_lab_kernel.BUNDLE_RESULT_NAME
    if not _path_is_file(receipt_path):
        fallback = _proof_lab_canonical_receipt_result(
            input_path=input_path,
            out_dir=out_dir,
            cache_status="canonical_receipt_read",
            live_receipt_rebuild_status="not_requested_card_mode",
        )
        if fallback is not None:
            return fallback
        return {
            "status": "missing_cached_receipt",
            "proof_lab_component_metrics": {},
            "receipt_paths": [],
            "body_in_receipt": False,
            "authority_ceiling": {
                "status": "missing_cached_receipt",
                "run_required": "microcosm proof-lab --out <out>",
            },
            "anti_claim": (
                "Cached proof-lab cards read public receipts only; run the "
                "full proof-lab route when the receipt is missing or stale."
            ),
            "cache_status": "missing_cached_receipt",
            "cached_receipt_ref": str(receipt_path),
            "cached_receipt_bytes": 0,
            "cache_freshness": {
                "schema_version": "microcosm_proof_lab_cache_freshness_v1",
                "status": "missing_cached_receipt",
                "input_status": "not_checked",
                "receipt_mtime_ns": None,
                "tracked_input_count": 0,
                "stale_input_count": 0,
                "latest_input_mtime_ns": None,
                "input_refs_exported": False,
            },
        }
    payload = _read_json_strict(receipt_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Proof-lab receipt must be a JSON object: {receipt_path}")
    receipt_paths = payload.get("receipt_paths")
    if not isinstance(receipt_paths, list) or not receipt_paths:
        payload = {**payload, "receipt_paths": [str(receipt_path)]}
    cache_freshness = _proof_lab_cache_freshness(input_path, receipt_path)
    cache_status = "cached_receipt_read"
    status = payload.get("status")
    if cache_freshness["status"] == "stale":
        cache_status = "stale_cached_receipt"
        status = "stale_cached_receipt"
    elif cache_freshness["status"] == "missing_cached_receipt":
        cache_status = "missing_cached_receipt"
        status = "missing_cached_receipt"
    return {
        **payload,
        "status": status,
        "cache_status": cache_status,
        "cached_receipt_ref": str(receipt_path),
        "cached_receipt_bytes": _path_size(receipt_path),
        "cache_freshness": cache_freshness,
    }


def _canonical_proof_lab_receipt_path() -> Path:
    return MICROCOSM_ROOT / PROOF_LAB_RECEIPT_REF


def _proof_lab_canonical_receipt_result(
    *,
    input_path: str,
    out_dir: str,
    cache_status: str,
    live_receipt_rebuild_status: str,
    tool_versions: dict | None = None,
) -> dict | None:
    canonical_path = _canonical_proof_lab_receipt_path()
    if not _path_is_file(canonical_path):
        return None
    payload = _read_json_strict(canonical_path)
    if not isinstance(payload, dict):
        raise ValueError(
            f"Canonical proof-lab receipt must be a JSON object: {canonical_path}"
        )
    target = Path(out_dir) / verifier_lab_kernel.BUNDLE_RESULT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        **payload,
        "command": _proof_lab_command(input_path, out_dir),
        "cache_status": cache_status,
        "cached_receipt_ref": PROOF_LAB_RECEIPT_REF,
        "cached_receipt_bytes": _path_size(canonical_path),
        "canonical_receipt_ref": PROOF_LAB_RECEIPT_REF,
        "canonical_receipt_bytes": _path_size(canonical_path),
        "live_receipt_rebuild_status": live_receipt_rebuild_status,
        "local_toolchain_status": (
            "missing_lean_lake" if tool_versions is not None else "not_checked"
        ),
        "tool_versions": tool_versions,
        "fallback_reason": (
            "Local Lean/Lake is not available; the first-screen route uses "
            "the bundled canonical public receipt and exposes this fallback "
            "instead of claiming a live proof rebuild."
            if tool_versions is not None
            else "Cached card read the bundled canonical public receipt."
        ),
        "receipt_paths": [str(target)],
    }
    _write_json_atomic(target, receipt)
    cache_freshness = _proof_lab_cache_freshness(input_path, canonical_path)
    status = receipt.get("status")
    if (
        cache_freshness.get("status") != "current"
        and cache_status != "canonical_receipt_fallback_toolchain_missing"
    ):
        status = "stale_cached_receipt"
    return {
        **receipt,
        "status": status,
        "cache_freshness": cache_freshness,
    }


def _proof_lab_toolchain_ready(tool_versions: dict) -> bool:
    return (
        tool_versions.get("lean_available") is True
        and tool_versions.get("lake_available") is True
    )


def _receipt_ref_for_out(receipt_path: object, out_dir: str) -> str | None:
    name = Path(str(receipt_path)).name
    if not name:
        return None
    base = _proof_lab_output_ref(out_dir)
    trimmed_base = base.rstrip("/")
    if trimmed_base:
        return f"{trimmed_base}/{name}"
    if base.startswith("/"):
        return f"/{name}"
    return name


def _receipt_refs_for_out(result: dict, out_dir: str) -> list[str]:
    refs: list[str] = []
    for receipt_path in result.get("receipt_paths") or []:
        receipt_ref = _receipt_ref_for_out(receipt_path, out_dir)
        if receipt_ref is not None:
            refs.append(receipt_ref)
    return refs


def _evidence_inspect_command(receipt_ref: str) -> str:
    if "<" in receipt_ref and ">" in receipt_ref:
        return f"microcosm evidence inspect {receipt_ref}"
    return f"microcosm evidence inspect {shlex.quote(receipt_ref)}"


def _cached_receipt_ref_for_card(result: dict, out_dir: str) -> object:
    receipt_ref = result.get("cached_receipt_ref")
    if not isinstance(receipt_ref, str) or not receipt_ref:
        return receipt_ref
    public_ref = _public_ref(receipt_ref)
    if public_ref != receipt_ref:
        return public_ref
    if not Path(receipt_ref).is_absolute():
        return receipt_ref
    return _receipt_ref_for_out(receipt_ref, out_dir) or PROOF_LAB_OUT_PLACEHOLDER


def _proof_lab_first_screen_card(
    result: dict,
    *,
    input_path: str,
    out_dir: str,
    command: str,
) -> dict:
    metrics = result.get("proof_lab_component_metrics") or {}
    status = result.get("status")
    cache_status = result.get("cache_status", "live_receipt_rebuild")
    cache_action_status = (
        status
        if status in {"stale_cached_receipt", "missing_cached_receipt"}
        else cache_status
    )
    receipt_refs = _receipt_refs_for_out(result, out_dir)
    if receipt_refs:
        evidence_drilldown = _evidence_inspect_command(receipt_refs[0])
    else:
        evidence_drilldown = "microcosm evidence inspect <proof-lab-receipt>"
    input_ref = _proof_lab_input_ref(input_path)
    out_ref = _proof_lab_output_ref(out_dir)
    return {
        "schema_version": "microcosm_proof_lab_first_screen_card_v1",
        "card_id": "first_screen_verifier_lab_kernel",
        "status": status,
        "command": command,
        "expanded_command": (
            "microcosm verifier-lab-kernel run-kernel-bundle "
            f"--input {input_ref} --out {out_ref}"
        ),
        "endpoint": "/proof-lab",
        "alias_endpoints": ["/verifier-lab-kernel"],
        "source_lens_endpoint": "/proof-loop-depth",
        "cache_status": cache_status,
        "status_scope": _proof_lab_status_scope(cache_action_status),
        "fresh_receipt_required": _proof_lab_fresh_receipt_required(
            cache_action_status
        ),
        "cache_action": _proof_lab_cache_action_hint(cache_action_status),
        "cached_receipt_ref": _cached_receipt_ref_for_card(result, out_dir),
        "cached_receipt_bytes": result.get("cached_receipt_bytes"),
        "cache_freshness": result.get("cache_freshness"),
        "canonical_receipt_ref": result.get("canonical_receipt_ref")
        or PROOF_LAB_RECEIPT_REF,
        "live_receipt_rebuild_status": result.get("live_receipt_rebuild_status"),
        "local_toolchain_status": result.get("local_toolchain_status"),
        "fallback_reason": result.get("fallback_reason"),
        "input_ref": input_ref,
        "out_ref": out_ref,
        "bundle_ref": PROOF_LAB_BUNDLE_REF,
        "route_id": result.get("proof_lab_route_id"),
        "route_ref": PROOF_LAB_ROUTE_REF,
        "receipt_ref": receipt_refs[0] if receipt_refs else None,
        "receipt_refs": receipt_refs,
        "proof_lab_route_id": result.get("proof_lab_route_id"),
        "proof_lab_route_component_count": result.get(
            "proof_lab_route_component_count"
        ),
        "lean_lake_return_code": result.get("lean_lake_return_code"),
        "lean_compiled_declaration_count": result.get(
            "lean_compiled_declaration_count"
        ),
        "component_metrics": {
            "corpus_count": metrics.get("corpus_count"),
            "retrieval_query_count": metrics.get("retrieval_query_count"),
            "ring2_mean_precision_at_k": metrics.get("ring2_mean_precision_at_k"),
            "proof_diagnostic_accepted_count": metrics.get(
                "proof_diagnostic_accepted_count"
            ),
        },
        "safe_to_show": {
            "body_in_receipt": result.get("body_in_receipt"),
            "proof_bodies_exported": False,
            "proof_correctness_claim": False,
            "provider_payloads_exported": False,
            "credential_equivalent_payloads_exported": False,
            "input_refs_exported": False,
            "host_private_paths_exported": False,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
        },
        **_proof_lab_first_screen_boundary(),
        "local_path_policy": {
            "host_private_paths_exported": False,
            "repo_paths_are_repo_relative": True,
            "private_tmp_normalized_to_tmp": True,
            "other_host_private_roots_use_placeholders": True,
            "input_placeholder": PROOF_LAB_INPUT_PLACEHOLDER,
            "out_placeholder": PROOF_LAB_OUT_PLACEHOLDER,
        },
        "authority_ceiling": result.get("authority_ceiling"),
        "anti_claim": result.get("anti_claim"),
        "reader_action": (
            "Use route_id, route_ref, and receipt_ref to verify the bounded "
            "proof-lab route, then drill into the receipt only after the "
            "first-screen card is visible."
        ),
        "next_commands": [
            "microcosm status --card",
            "microcosm proof-loop-depth",
            evidence_drilldown,
        ],
    }


def _status_card_proof_lab_front_door_ref(payload: dict) -> dict | None:
    proof_lab = payload.get("proof_lab")
    if not isinstance(proof_lab, dict):
        return None
    current_default_card = _status_card_current_default_proof_lab_card(proof_lab)
    if current_default_card is not None:
        proof_lab = _overlay_current_proof_lab_cache_status(
            proof_lab,
            current_default_card,
        )
    safe_to_show = proof_lab.get("safe_to_show")
    if not isinstance(safe_to_show, dict):
        safe_to_show = {}
    cache_status = proof_lab.get("cache_status")
    return {
        "schema_version": "microcosm_status_card_proof_lab_ref_v1",
        "status": proof_lab.get("status"),
        "endpoint": proof_lab.get("endpoint") or "/proof-lab",
        "route_id": proof_lab.get("route_id"),
        "receipt_ref": proof_lab.get("receipt_ref"),
        "current_receipt_ref": proof_lab.get("current_receipt_ref"),
        "route_component_count": proof_lab.get("route_component_count")
        or proof_lab.get("proof_lab_route_component_count"),
        "proof_bodies_exported": safe_to_show.get("proof_bodies_exported", False),
        "proof_correctness_claim": safe_to_show.get("proof_correctness_claim", False),
        "cache_status": cache_status,
        "status_scope": _proof_lab_status_scope(cache_status),
        "fresh_receipt_required": _proof_lab_fresh_receipt_required(cache_status),
        "cache_action": proof_lab.get("cache_action")
        if isinstance(proof_lab.get("cache_action"), dict)
        else _proof_lab_cache_action_hint(cache_status),
    }


def _overlay_current_proof_lab_cache_status(
    proof_lab: dict,
    current_default_card: dict,
) -> dict:
    for key in (
        "status",
        "endpoint",
        "route_id",
        "proof_lab_route_id",
        "proof_lab_route_component_count",
        "cache_status",
        "cache_action",
        "cached_receipt_ref",
        "cached_receipt_bytes",
        "cache_freshness",
        "live_receipt_rebuild_status",
        "local_toolchain_status",
        "fallback_reason",
    ):
        if key in current_default_card:
            proof_lab[key] = current_default_card[key]
    current_receipt_ref = current_default_card.get("receipt_ref")
    if isinstance(current_receipt_ref, str) and current_receipt_ref:
        proof_lab["current_receipt_ref"] = current_receipt_ref
    return proof_lab


def _status_card_current_default_proof_lab_card(proof_lab: dict) -> dict | None:
    if proof_lab.get("cache_status") != "stale_cached_receipt":
        return None
    receipt_path = Path(DEFAULT_PROOF_LAB_OUT) / verifier_lab_kernel.BUNDLE_RESULT_NAME
    if not _path_is_file(receipt_path):
        return None
    result = _proof_lab_cached_result(
        str(DEFAULT_PROOF_LAB_INPUT),
        DEFAULT_PROOF_LAB_OUT,
    )
    if result.get("cache_status") in {
        "stale_cached_receipt",
        "missing_cached_receipt",
    }:
        return None
    return _proof_lab_first_screen_card(
        result,
        input_path=str(DEFAULT_PROOF_LAB_INPUT),
        out_dir=DEFAULT_PROOF_LAB_OUT,
        command=_proof_lab_command(str(DEFAULT_PROOF_LAB_INPUT), DEFAULT_PROOF_LAB_OUT),
    )


def _status_card_observatory_front_door_ref(payload: dict) -> dict | None:
    front_door = payload.get("front_door")
    if not isinstance(front_door, dict):
        return None
    route_selection_proof = front_door.get("route_selection_proof")
    if not isinstance(route_selection_proof, dict):
        route_selection_proof = {}
    project_ref = _status_card_project_ref(payload)
    bounded_command = _replace_project_placeholder(
        front_door.get("observatory_bounded_validation_command")
        or front_door.get("observatory_command"),
        project_ref,
    )
    interactive_command = _replace_project_placeholder(
        front_door.get("observatory_interactive_command")
        or OBSERVATORY_SERVE_COMMAND,
        project_ref,
    )
    raw_selected_route_id = front_door.get("selected_route_id")
    selected_route_id = raw_selected_route_id or "<selected_route_id>"
    route_proof_status = route_selection_proof.get("status")
    status = (
        "actionable"
        if bounded_command and route_proof_status == "pass"
        else "actionable"
        if bounded_command and not raw_selected_route_id
        else "missing_route_proof"
        if bounded_command
        else "missing_command"
    )
    return {
        "schema_version": "microcosm_status_card_observatory_ref_v1",
        "status": status,
        "command": bounded_command,
        "bounded_validation_command": bounded_command,
        "interactive_command": interactive_command,
        "bounded_validation_request_count": OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT,
        "bounded_validation_rule": OBSERVATORY_BOUNDED_VALIDATION_RULE,
        "endpoint": "/project/observatory",
        "compact_endpoint": "/project/observatory-card",
        "status_card_endpoint": "/project/status",
        "project_observe_command": f"microcosm observe --card {project_ref}",
        "project_observe_endpoint": "/project/observe",
        "route_explanation_endpoint": f"/project/explain/{selected_route_id}",
        "first_screen_route_proof_ref": route_selection_proof.get(
            "observatory_route_proof_ref"
        ),
        "status_card_ref": payload.get("card_command")
        or f"microcosm status --card {project_ref}",
        "related_endpoint_count": 9,
        "model_field_count": 13,
        "validation_status": (
            "not_evaluated_in_status_card"
            if status == "actionable"
            else status
        ),
        "reader_action": (
            "Run bounded_validation_command or open compact_endpoint before "
            "treating the observatory card itself as pass/fail."
        ),
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_authorized": False,
        "proof_correctness_claim": False,
    }


def _status_card_surface_is_nonblocking(status: object) -> bool:
    return status in {"pass", "clear", "actionable"}


def _attach_status_card_front_door_refs(payload: dict) -> dict:
    front_door = payload.get("front_door")
    if not isinstance(front_door, dict):
        return payload
    proof_lab_ref = _status_card_proof_lab_front_door_ref(payload)
    observatory_ref = _status_card_observatory_front_door_ref(payload)
    if proof_lab_ref is not None:
        front_door["proof_lab"] = proof_lab_ref
    if observatory_ref is not None:
        front_door["observatory"] = observatory_ref

    front_door_status = payload.get("front_door_status")
    if not isinstance(front_door_status, dict):
        return payload
    surface_statuses = front_door_status.get("surface_statuses")
    if not isinstance(surface_statuses, dict):
        surface_statuses = {}
    if proof_lab_ref is not None and proof_lab_ref.get("status") is not None:
        surface_statuses["proof_lab"] = proof_lab_ref.get("status")
        cache_status = proof_lab_ref.get("cache_status")
        if cache_status == "stale_cached_receipt":
            surface_statuses["proof_lab_cache"] = "actionable"
        elif cache_status == "missing_cached_receipt":
            surface_statuses["proof_lab_cache"] = cache_status
        elif cache_status is not None:
            surface_statuses["proof_lab_cache"] = "pass"
    if observatory_ref is not None and observatory_ref.get("status") is not None:
        surface_statuses["observatory"] = observatory_ref.get("status")
    front_door_status["surface_statuses"] = surface_statuses
    front_door_status["blocking_surface_ids"] = [
        surface_id
        for surface_id, surface_status in surface_statuses.items()
        if not _status_card_surface_is_nonblocking(surface_status)
    ]
    front_door_status["actionable_surface_ids"] = [
        surface_id
        for surface_id, surface_status in surface_statuses.items()
        if surface_status == "actionable"
    ]
    front_door_status["status"] = (
        "pass" if not front_door_status["blocking_surface_ids"] else "blocked"
    )
    return payload


def _pick(source: object, keys: list[str]) -> dict:
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in keys if key in source}


def _compact_blocking_surface_details_for_cli(details: object) -> dict:
    if not isinstance(details, dict):
        return {}
    compacted: dict[str, object] = {}
    for surface_id, detail in details.items():
        if not isinstance(detail, dict):
            compacted[surface_id] = detail
            continue
        if surface_id != "macro_body_import_floor":
            compacted[surface_id] = detail
            continue
        compact_detail = _pick(
            detail,
            [
                "status",
                "defect_count",
                "full_defects_ref",
            ],
        )
        preview_rows = detail.get("defect_preview")
        if isinstance(preview_rows, list):
            compact_detail["defect_preview_count"] = len(preview_rows)
            compact_detail["defect_preview_compacted"] = True
            compact_detail["defect_preview"] = [
                _pick(
                    row,
                    [
                        "material_id",
                        "material_class",
                        "target_ref",
                        "defect_codes",
                        "body_text_in_receipt",
                    ],
                )
                for row in preview_rows[:1]
                if isinstance(row, dict)
            ]
        compacted[surface_id] = compact_detail
    return compacted


def _compact_project_status_card_for_cli(payload: dict) -> dict:
    front_door = payload.get("front_door")
    if not isinstance(front_door, dict):
        return payload

    front_door_status = payload.get("front_door_status")
    if isinstance(front_door_status, dict):
        payload["front_door_status"] = _pick(
            front_door_status,
            [
                "status",
                "surface_statuses",
                "blocking_surface_ids",
                "blocking_surface_details",
                "actionable_surface_ids",
                "drilldown_warning_surface_ids",
                "drilldown_blocked_surface_ids_ref",
            ],
        )
        details = payload["front_door_status"].get("blocking_surface_details")
        if isinstance(details, dict):
            payload["front_door_status"]["blocking_surface_details"] = (
                _compact_blocking_surface_details_for_cli(details)
            )

    workingness = payload.get("workingness")
    if isinstance(workingness, dict):
        gap_preview = workingness.get("gap_preview")
        compact_gap_preview = _pick(gap_preview, ["status", "drilldown_command"])
        if isinstance(gap_preview, dict) and isinstance(gap_preview.get("rows"), list):
            compact_gap_preview["row_count"] = len(gap_preview["rows"])
        payload["workingness"] = {
            **_pick(
                workingness,
                [
                    "status",
                    "map_generation_status",
                    "failure_envelope_status",
                    "command",
                    "endpoint",
                    "workingness_map_ref",
                    "source_open_body_material_count",
                    "source_body_count_kind",
                    "missing_standard_count",
                    "missing_failure_modes_count",
                ],
            ),
            "gap_preview": compact_gap_preview,
        }

    macro_body_floor = payload.get("macro_body_import_floor")
    if isinstance(macro_body_floor, dict):
        payload["macro_body_import_floor"] = _pick(
            macro_body_floor,
            [
                "schema_version",
                "status",
                "ref",
                "public_safe_body_material_count",
                "public_safe_body_material_counts_by_class",
                "direct_source_module_manifest_count",
                "direct_source_module_manifest_material_count",
                "verified_source_module_family_count",
                "source_module_family_spotlights",
                "body_text_exported_in_status",
                "body_text_exported_in_receipts",
                "project_mode_compacted",
            ],
        )

    payload_boundary_audit = payload.get("payload_boundary_audit")
    if isinstance(payload_boundary_audit, dict):
        payload["payload_boundary_audit"] = _pick(
            payload_boundary_audit,
            [
                "schema_version",
                "status",
                "omitted_payload_schema_terms_exported",
                "omitted_payload_schema_hit_count",
            ],
        )

    project_state = front_door.get("project_state")
    if isinstance(project_state, dict):
        compact_project_state = _pick(
            project_state,
            [
                "status",
                "state_dir_exists",
                "existing_state_ref_count",
                "route_count",
                "recovery_command",
                "status_after_recovery_command",
                "state_write_result_ref",
                "state_write_status_ref",
                "status_card_writes_microcosm_state",
                "available_project_route_id_count",
                "available_project_route_ids",
            ],
        )
        recovery = project_state.get("recovery")
        if isinstance(recovery, dict):
            compact_project_state["recovery"] = recovery
        front_door["project_state"] = compact_project_state

    state_write_proof = front_door.get("state_write_proof")
    if isinstance(state_write_proof, dict):
        compact_state_write_proof = _pick(
            state_write_proof,
            [
                "status",
                "state_write_result_ref",
                "state_write_status_ref",
                "project_state_ref",
                "observe_ref",
                "observe_writes_microcosm_state",
                "status_card_writes_microcosm_state",
            ],
        )
        safe_to_show = state_write_proof.get("safe_to_show")
        if isinstance(safe_to_show, dict):
            compact_state_write_proof["safe_to_show"] = _pick(
                safe_to_show,
                ["source_files_mutated"],
            )
        front_door["state_write_proof"] = compact_state_write_proof

    body_floor = front_door.get("source_open_body_import_floor")
    if isinstance(body_floor, dict):
        front_door["source_open_body_import_floor"] = _pick(
            body_floor,
            [
                "status",
                "summary_ref",
                "public_safe_body_material_count",
                "public_safe_body_material_counts_by_class",
                "direct_source_module_manifest_count",
                "direct_source_module_manifest_material_count",
                "verified_source_module_family_count",
                "latest_verified_source_module_family_ids",
                "source_module_family_spotlights",
                "body_text_exported_in_status",
                "body_text_exported_in_receipts",
            ],
        )

    observatory = front_door.get("observatory")
    if isinstance(observatory, dict):
        front_door["observatory"] = _pick(
            observatory,
            [
                "status",
                "schema_version",
                "command",
                "bounded_validation_command",
                "interactive_command",
                "bounded_validation_request_count",
                "bounded_validation_rule",
                "endpoint",
                "compact_endpoint",
                "status_card_endpoint",
                "project_observe_command",
                "project_observe_endpoint",
                "route_explanation_endpoint",
                "first_screen_route_proof_ref",
                "status_card_ref",
                "model_field_count",
                "validation_status",
                "reader_action",
                "source_files_mutated",
                "provider_calls_authorized",
                "release_authorized",
                "proof_correctness_claim",
            ],
        )

    proof_lab = front_door.get("proof_lab")
    if isinstance(proof_lab, dict):
        front_door["proof_lab"] = _pick(
            proof_lab,
            [
                "status",
                "endpoint",
                "route_id",
                "receipt_ref",
                "current_receipt_ref",
                "route_component_count",
                "proof_bodies_exported",
                "proof_correctness_claim",
                "cache_status",
                "status_scope",
                "fresh_receipt_required",
                "cache_action",
            ],
        )
    top_level_proof_lab = payload.get("proof_lab")
    if isinstance(top_level_proof_lab, dict):
        payload["proof_lab"] = _pick(
            top_level_proof_lab,
            [
                "status",
                "endpoint",
                "route_id",
                "receipt_ref",
                "current_receipt_ref",
                "route_component_count",
                "proof_lab_route_component_count",
                "cache_status",
                "status_scope",
                "fresh_receipt_required",
                "cache_action",
            ],
        )

    return payload


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv == ["--version"]:
        print(f"microcosm {__version__}")
        return 0

    fast_path_status = _first_screen_fast_path(raw_argv)
    if fast_path_status is not None:
        return fast_path_status

    parser = argparse.ArgumentParser(
        prog="microcosm",
        description=(
            "Local-first project substrate: repo -> .microcosm without provider "
            "calls or source mutation."
        ),
        epilog=FIRST_SCREEN_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    init_parser = subparsers.add_parser(
        "init",
        help="create project-local .microcosm state",
    )
    init_parser.add_argument("project")
    index_parser = subparsers.add_parser(
        "index",
        help="classify project files into public repo roles",
    )
    index_parser.add_argument("project")
    catalog_parser = subparsers.add_parser(
        "catalog",
        help="emit the project file-role catalog",
    )
    catalog_parser.add_argument("project")
    architecture_parser = subparsers.add_parser(
        "architecture",
        help="show project architecture-kernel primitives",
    )
    architecture_parser.add_argument("project")
    compile_parser = subparsers.add_parser(
        "compile",
        help="build local .microcosm project state",
    )
    compile_parser.add_argument(
        "--card",
        action="store_true",
        help="read cached .microcosm compile state without rebuilding",
    )
    compile_parser.add_argument("project")
    python_lens_parser = subparsers.add_parser(
        "python-lens",
        help="inspect public Python route/readiness metadata",
    )
    python_lens_parser.add_argument(
        "--full",
        action="store_true",
        help="emit full source-span, symbol, import, and graph rows",
    )
    python_lens_parser.add_argument("project")
    graph_parser = subparsers.add_parser(
        "graph",
        help="show project route/work/event/evidence graph",
    )
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser(
        "explain",
        help="show route -> work -> event -> evidence chain",
    )
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    status_parser = subparsers.add_parser(
        "status",
        help="show runtime status or compact first-screen card",
        description="Show runtime status or compact first-screen card.",
        epilog=STATUS_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-screen status lens",
    )
    status_parser.add_argument("project", nargs="?")
    status_card_parser = subparsers.add_parser(
        "status-card",
        help="alias for status --card",
        description="Alias for the compact first-screen project/runtime status lens.",
        epilog=STATUS_CARD_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_card_parser.add_argument(
        "project",
        nargs="?",
        metavar="project",
        help="project path with .microcosm state; omit for runtime-only status",
    )
    proof_lab_parser = subparsers.add_parser(
        "proof-lab",
        help="run the first-screen verifier proof lab",
    )
    proof_lab_parser.add_argument(
        "--card",
        action="store_true",
        help="read the cached first-screen proof-lab receipt without rerunning",
    )
    proof_lab_parser.add_argument(
        "--input",
        default=str(DEFAULT_PROOF_LAB_INPUT),
        help="exported verifier lab bundle",
    )
    proof_lab_parser.add_argument(
        "--out",
        default=DEFAULT_PROOF_LAB_OUT,
        help="directory for proof-lab receipts",
    )
    proof_lab_parser.add_argument(
        "project",
        nargs="?",
        help=(
            "accepted for first-screen parity; proof-lab input/output flags "
            "remain the authority for this route"
        ),
    )
    spine_parser = subparsers.add_parser(
        "spine",
        help="show accepted public runtime spine",
    )
    spine_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-screen runtime spine lens",
    )
    spine_parser.add_argument(
        "project",
        nargs="?",
        help=(
            "accepted for first-screen parity; the spine card remains a "
            "Microcosm-rooted runtime lens"
        ),
    )
    tour_parser = subparsers.add_parser(
        "tour",
        help="run the compressed cold-reader route",
    )
    tour_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-screen tour lens",
    )
    tour_parser.add_argument("project", nargs="?")
    hello_parser = subparsers.add_parser(
        "hello",
        help="print the cold-entry first-screen card",
    )
    hello_parser.add_argument(
        "--reader",
        choices=TEXT_READER_CHOICES,
        default="all",
        help="focus the terminal projection on one reader branch",
    )
    hello_parser.add_argument(
        "--card",
        action="store_true",
        help="accepted for first-screen parity; hello always emits text",
    )
    hello_parser.add_argument("project", nargs="?", default="<project>")
    first_screen_parser = subparsers.add_parser(
        "first-screen",
        help="preview the one-screen reader route map",
    )
    first_screen_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="emit the JSON machine card or terminal projection",
    )
    first_screen_parser.add_argument(
        "--card",
        action="store_true",
        help="accepted as a compact JSON card alias",
    )
    first_screen_parser.add_argument(
        "--full",
        action="store_true",
        help="emit the full first-screen contract JSON instead of the compact projection",
    )
    first_screen_parser.add_argument(
        "--reader",
        choices=TEXT_READER_CHOICES,
        default="all",
        help="focus the terminal projection on one reader branch",
    )
    first_screen_parser.add_argument("project", nargs="?", default="<project>")
    agent_entry_parser = subparsers.add_parser(
        "agent-entry-composition",
        help="emit the Type A/human agent entry composition card",
        description=(
            "Compose viewer-aware Type A and human first-action routes, the "
            "task route, organ evidence, standards, and macro route body floor "
            "into one runnable entry card."
        ),
        epilog=AGENT_ENTRY_COMPOSITION_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    agent_entry_parser.add_argument(
        "--task",
        default="agent-entry",
        help="task string to normalize into an agent task route",
    )
    agent_entry_parser.add_argument(
        "--viewer",
        choices=("all", "type_a_agent", "human"),
        default="all",
        help="select one viewer route while still emitting the shared card",
    )
    agent_entry_parser.add_argument(
        "--root",
        default=None,
        help="Microcosm root; defaults to the installed package root",
    )
    agent_entry_parser.add_argument(
        "--out",
        default=None,
        help="optional output directory for card and receipt JSON",
    )
    agent_entry_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-entry card instead of the full projection",
    )
    agent_entry_parser.add_argument(
        "--check",
        action="store_true",
        help="return nonzero when the composed card is blocked",
    )
    organ_discoverability_parser = subparsers.add_parser(
        "organ-discoverability-matrix",
        help="build the accepted-organ discoverability matrix",
        description=(
            "Map every accepted organ to first command, authority ceiling, "
            "evidence class, paper-module handle, proof receipts, task routes, "
            "owner build route, and explicit discoverability gaps."
        ),
    )
    organ_discoverability_parser.add_argument(
        "--root",
        default=None,
        help="Microcosm root; defaults to the installed package root",
    )
    organ_discoverability_parser.add_argument(
        "--out",
        default=None,
        help="optional output directory for matrix and receipt JSON",
    )
    organ_discoverability_parser.add_argument(
        "--check",
        action="store_true",
        help="return nonzero when the matrix validator is blocked",
    )
    authority_parser = subparsers.add_parser(
        "authority",
        help="show authority ceilings and anti-claims",
        description="show authority ceilings and anti-claims",
        epilog=AUTHORITY_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    authority_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact first-screen authority lens",
    )
    authority_parser.add_argument(
        "project",
        nargs="?",
        help=(
            "accepted for first-screen parity; the authority card remains a "
            "Microcosm authority lens"
        ),
    )
    _add_public_lens_parsers(subparsers)
    run_parser = subparsers.add_parser(
        "run",
        help="replay the local public runtime demo",
    )
    run_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact runtime demo card",
    )
    run_parser.add_argument(
        "project",
        nargs="?",
        default=DEFAULT_PROJECT_REL,
        help="runtime demo project path; defaults to examples/runtime_shell/demo_project",
    )
    serve_parser = subparsers.add_parser(
        "serve",
        help="serve the local observatory over project state",
    )
    serve_parser.add_argument("project", nargs="?")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument(
        "--max-requests",
        type=int,
        help="serve at most N HTTP requests, then exit cleanly",
    )
    patterns_parser = subparsers.add_parser(
        "patterns",
        help="inspect project pattern observations",
    )
    patterns_parser.add_argument("project", nargs="?")
    route_parser = subparsers.add_parser(
        "route",
        help="list runtime routes or project route candidates",
    )
    route_parser.add_argument("route_args", nargs="*")
    work_parser = subparsers.add_parser(
        "work",
        help="create or run project-local reversible work transactions",
    )
    work_subparsers = work_parser.add_subparsers(dest="work_command")
    work_subparsers.add_parser(
        "demo",
        help="show the runtime work transaction demo",
    )
    work_create_parser = work_subparsers.add_parser(
        "create",
        help="record a project-local work transaction from a selected route",
    )
    work_create_parser.add_argument("project")
    work_create_parser.add_argument(
        "--route",
        help="route id to snapshot; defaults to the first selected project route",
    )
    work_run_parser = work_subparsers.add_parser(
        "run",
        help="execute the project-local work transaction simulation",
    )
    work_run_parser.add_argument("project")
    work_run_parser.add_argument(
        "--work-id",
        help="work id to run; defaults to the latest project-local work item",
    )
    observe_parser = subparsers.add_parser(
        "observe",
        help="inspect compact route/work/event/evidence chain",
    )
    observe_parser.add_argument(
        "--card",
        action="store_true",
        help="emit compact observe card instead of full event rows",
    )
    observe_parser.add_argument("project")
    evidence_parser = subparsers.add_parser(
        "evidence",
        help="list or inspect evidence after behavior is visible",
        description="List or inspect evidence refs after behavior is visible.",
        epilog=EVIDENCE_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_list_parser = evidence_subparsers.add_parser(
        "list",
        help="list compact evidence refs; omit project for runtime receipts",
        description="List compact evidence refs without opening receipt bodies.",
        epilog=EVIDENCE_LIST_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    evidence_list_parser.add_argument(
        "project",
        nargs="?",
        help="project path with .microcosm state; omit for runtime receipts",
    )
    evidence_list_parser.add_argument(
        "--limit",
        type=_nonnegative_int,
        default=25,
        help="maximum rows to print; use 0 for the full list",
    )
    evidence_list_parser.add_argument(
        "--json",
        action="store_true",
        help="accepted for explicit JSON output; evidence list already prints JSON",
    )
    evidence_inspect_parser = evidence_subparsers.add_parser(
        "inspect",
        help="inspect one runtime receipt or project evidence ref",
        description="Inspect one runtime receipt or project evidence ref as a safe evidence card.",
        epilog=EVIDENCE_INSPECT_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    evidence_inspect_parser.add_argument(
        "--project",
        help="project path for .microcosm evidence refs",
    )
    evidence_inspect_parser.add_argument(
        "receipt_ref",
        help="receipt ref, project path when followed by a project evidence ref, or .microcosm evidence ref from the project root",
    )
    evidence_inspect_parser.add_argument(
        "project_evidence_ref",
        nargs="?",
        help="project evidence ref for shorthand: microcosm evidence inspect <project> <ref>",
    )

    scan_parser = subparsers.add_parser("private-state-scan")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--out", required=True)
    scan_parser.add_argument("--policy")
    secret_scan_parser = subparsers.add_parser("secret-exclusion-scan")
    secret_scan_parser.add_argument("--root", required=True)
    secret_scan_parser.add_argument("--out", required=True)
    secret_scan_parser.add_argument("--policy")

    public_entry_parser = subparsers.add_parser("public-entry-docs")
    _add_root_out(public_entry_parser)
    organ_surface_parser = subparsers.add_parser(
        "organ-surface-contract",
        help="audit accepted organ surface wiring",
    )
    organ_surface_parser.add_argument("--root", default=str(MICROCOSM_ROOT))
    organ_surface_parser.add_argument("--out")
    organ_surface_parser.add_argument(
        "--card",
        action="store_true",
        help="emit compact counts instead of full per-organ rows",
    )
    organ_topology_parser = subparsers.add_parser(
        "organ-topology",
        help="query typed accepted-organ relationship edges",
    )
    organ_topology_parser.add_argument("--root", default=str(MICROCOSM_ROOT))
    organ_topology_parser.add_argument("--out")
    organ_topology_parser.add_argument(
        "--organ",
        help="filter topology edges to one organ_id",
    )
    organ_topology_parser.add_argument(
        "--relation-type",
        help="filter topology edges to one relation_type",
    )
    organ_topology_parser.add_argument(
        "--source-ref",
        help="filter topology edges to one source_ref",
    )
    organ_topology_parser.add_argument(
        "--target-ref",
        help="filter topology edges to one target_ref or peer_target_ref",
    )
    organ_topology_parser.add_argument(
        "--manifest-ref",
        help="filter topology edges to one source-module manifest ref",
    )
    organ_topology_parser.add_argument(
        "--shard-ref",
        help="filter topology edges to one source_shard_ref or target_shard_ref",
    )
    organ_topology_parser.add_argument(
        "--validation-ref",
        help="filter topology edges to one authored validation_ref",
    )
    density_parser = subparsers.add_parser("research-kernel-density")
    _add_root_out(density_parser)
    density_parser.add_argument("--project")
    stability_parser = subparsers.add_parser("transaction-evidence-stability")
    _add_root_out(stability_parser)
    stability_parser.add_argument("--project", required=True)
    observatory_parser = subparsers.add_parser("observatory-legibility")
    _add_root_out(observatory_parser)
    observatory_parser.add_argument("--project", required=True)
    launch_parser = subparsers.add_parser("launch-compression")
    _add_root_out(launch_parser)
    launch_parser.add_argument("--project", required=True)

    standards_parser = subparsers.add_parser("standards-registry")
    standards_parser.add_argument("--registry", required=True)
    standards_parser.add_argument("--standards-dir", required=True)
    standards_parser.add_argument("--acceptance", required=True)
    standards_parser.add_argument("--out", required=True)

    doctrine_lattice_parser = subparsers.add_parser(
        "doctrine-lattice",
        help="check, write, or summarize doctrine-lattice coverage and entry cards",
    )
    doctrine_lattice_parser.add_argument(
        "action",
        choices=[
            "check",
            "write",
            "status",
            "entry-card",
            "write-entry-card",
            "check-entry-card",
        ],
    )
    doctrine_lattice_parser.add_argument("--root", default=str(MICROCOSM_ROOT))
    doctrine_lattice_parser.add_argument("--out")

    dependency_parser = subparsers.add_parser("dependency-preflight")
    _add_preflight(dependency_parser)

    freshness_parser = subparsers.add_parser("fixture-freshness")
    _add_preflight(freshness_parser)
    freshness_parser.add_argument("--mission-dag", required=True)
    freshness_parser.add_argument("--receipt-coverage", required=True)

    organ_parser = _add_bundle_parser(subparsers, "pattern-binding")
    organ_parser.add_argument(
        "action",
        choices=[
            "validate",
            "validate-substrate-bundle",
            "validate-route-readiness-bundle",
        ],
    )
    _add_input_out(organ_parser)
    route_readiness_parser = _add_bundle_parser(subparsers, "pattern-route-readiness")
    route_readiness_parser.add_argument("action", choices=["validate-bundle"])
    _add_input_out(route_readiness_parser)

    crown_jewel_parser = _add_bundle_parser(subparsers, "crown-jewel-demo")
    crown_jewel_parser.add_argument("action", choices=["run"])
    crown_jewel_parser.add_argument("--out")

    macro_gallery_parser = _add_bundle_parser(subparsers, "macro-engines-gallery")
    macro_gallery_parser.add_argument("action", choices=["run"])
    macro_gallery_parser.add_argument("--out")

    engine_room_demo_parser = _add_bundle_parser(subparsers, "engine-room-demo")
    engine_room_demo_parser.add_argument(
        "action", choices=["run", "run-engine-room-demo-bundle"]
    )
    _add_input_out(engine_room_demo_parser)
    engine_room_demo_parser.add_argument("--acceptance-out")

    closeout_audit_parser = _add_bundle_parser(
        subparsers, "agent-closeout-faithfulness-audit"
    )
    closeout_audit_parser.add_argument(
        "action", choices=["run", "run-agent-closeout-bundle"]
    )
    _add_input_out_acceptance(closeout_audit_parser)

    doctrine_fact_parser = _add_bundle_parser(subparsers, "doctrine-fact-claim-audit")
    doctrine_fact_parser.add_argument(
        "action", choices=["run", "run-doctrine-fact-bundle"]
    )
    _add_input_out_acceptance(doctrine_fact_parser)

    self_ignorance_parser = _add_bundle_parser(
        subparsers, "self-ignorance-coverage-ledger"
    )
    self_ignorance_parser.add_argument(
        "action", choices=["run", "run-self-ignorance-bundle"]
    )
    _add_input_out_acceptance(self_ignorance_parser)

    bounded_autonomy_parser = _add_bundle_parser(
        subparsers, "bounded-autonomy-campaign-packet"
    )
    bounded_autonomy_parser.add_argument(
        "action", choices=["run", "run-bounded-autonomy-bundle"]
    )
    _add_input_out_acceptance(bounded_autonomy_parser)

    finance_forecast_parser = _add_bundle_parser(
        subparsers, "finance-forecast-evaluation-spine"
    )
    finance_forecast_parser.add_argument(
        "action", choices=["run", "run-finance-forecast-bundle"]
    )
    _add_input_out_acceptance(finance_forecast_parser)

    finance_eval_parser = _add_bundle_parser(subparsers, "finance-eval-spine")
    finance_eval_parser.add_argument("action", choices=["validate-finance-eval-bundle"])
    _add_input_out(finance_eval_parser)
    work_landing_control_parser = _add_bundle_parser(
        subparsers, "work-landing-control-spine"
    )
    work_landing_control_parser.add_argument("action", choices=["validate-control-bundle"])
    _add_input_out(work_landing_control_parser)

    grammar_parser = _add_bundle_parser(subparsers, "executable-doctrine-grammar")
    grammar_parser.add_argument(
        "action",
        choices=[
            "validate",
            "validate-standards-bundle",
            "validate-executable-grammar-metabolism-bundle",
        ],
    )
    _add_input_out(grammar_parser)

    proof_parser = _add_bundle_parser(subparsers, "proof-diagnostic-evidence-spine")
    proof_parser.add_argument("action", choices=["run", "run-evidence-bundle"])
    _add_input_out(proof_parser)
    proof_parser.add_argument("--card", action="store_true")

    formal_math_parser = _add_bundle_parser(subparsers, "formal-math-readiness-gate")
    formal_math_parser.add_argument("action", choices=["run", "run-readiness-bundle", "plan"])
    formal_math_parser.add_argument("--input", required=True)
    formal_math_parser.add_argument("--out")

    corpus_readiness_parser = _add_bundle_parser(
        subparsers, "corpus-readiness-mathlib-absence-gate"
    )
    corpus_readiness_parser.add_argument("action", choices=["run", "run-projection-bundle"])
    _add_input_out(corpus_readiness_parser)

    strategy_atlas_parser = _add_bundle_parser(
        subparsers, "mathematical-strategy-atlas-hypothesis-scorer"
    )
    strategy_atlas_parser.add_argument("action", choices=["run", "run-strategy-bundle"])
    _add_input_out(strategy_atlas_parser)

    tactic_portfolio_parser = _add_bundle_parser(
        subparsers, "tactic-portfolio-availability-probe"
    )
    tactic_portfolio_parser.add_argument("action", choices=["run", "run-availability-bundle"])
    _add_input_out(tactic_portfolio_parser)

    target_shape_parser = _add_bundle_parser(
        subparsers, "target-shape-tactic-routing-gate"
    )
    target_shape_parser.add_argument("action", choices=["run", "run-routing-bundle"])
    _add_input_out(target_shape_parser)

    lean_witness_parser = _add_bundle_parser(
        subparsers, "formal-math-lean-proof-witness"
    )
    lean_witness_parser.add_argument("action", choices=["run", "run-witness-bundle"])
    _add_input_out(lean_witness_parser)

    premise_retrieval_parser = _add_bundle_parser(
        subparsers, "formal-math-premise-retrieval"
    )
    premise_retrieval_parser.add_argument("action", choices=["run", "run-retrieval-bundle"])
    _add_input_out(premise_retrieval_parser)

    verifier_trace_parser = _add_bundle_parser(
        subparsers, "formal-math-verifier-trace-repair-loop"
    )
    verifier_trace_parser.add_argument("action", choices=["run", "run-loop-bundle"])
    _add_input_out(verifier_trace_parser)

    verifier_lab_parser = _add_bundle_parser(subparsers, "verifier-lab-kernel")
    verifier_lab_parser.add_argument("action", choices=["run", "run-kernel-bundle"])
    _add_input_out(verifier_lab_parser)
    verifier_lab_parser.add_argument("--acceptance-out")

    verifier_lab_execution_parser = _add_bundle_parser(
        subparsers,
        "verifier-lab-execution-spine"
    )
    verifier_lab_execution_parser.add_argument(
        "action", choices=["run", "run-execution-bundle"]
    )
    _add_input_out(verifier_lab_execution_parser)
    verifier_lab_execution_parser.add_argument("--acceptance-out")

    certificate_kernel_parser = _add_bundle_parser(
        subparsers, "certificate-kernel-execution-lab"
    )
    certificate_kernel_parser.add_argument(
        "action", choices=["run", "run-certificate-bundle"]
    )
    _add_input_out(certificate_kernel_parser)
    certificate_kernel_parser.add_argument("--acceptance-out")

    batch6_parser = _add_bundle_parser(
        subparsers, "batch6-unsurfaced-primitives-capsule"
    )
    batch6_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch6_parser)
    batch6_parser.add_argument("--acceptance-out")

    batch5_parser = _add_bundle_parser(
        subparsers, "batch5-authority-systems-capsule"
    )
    batch5_parser.add_argument("action", choices=["run", "run-batch5-bundle"])
    _add_input_out(batch5_parser)
    batch5_parser.add_argument("--acceptance-out")

    batch7_demo_parser = _add_bundle_parser(
        subparsers, "batch7-demo-take-console-capsule"
    )
    batch7_demo_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch7_demo_parser)
    batch7_demo_parser.add_argument("--acceptance-out")

    batch7_oracle_parser = _add_bundle_parser(
        subparsers, "batch7-oracle-sibling-capsule"
    )
    batch7_oracle_parser.add_argument(
        "action",
        choices=["run", "validate-bundle", "run-batch7-oracle-sibling-bundle"],
    )
    _add_input_out(batch7_oracle_parser)
    batch7_oracle_parser.add_argument("--acceptance-out")

    batch7_secondary_parser = _add_bundle_parser(
        subparsers, "batch7-secondary-runtime-capsule"
    )
    batch7_secondary_parser.add_argument(
        "action", choices=["run", "run-batch7-secondary-bundle"]
    )
    _add_input_out(batch7_secondary_parser)
    batch7_secondary_parser.add_argument("--acceptance-out")

    batch8_tools_parser = _add_bundle_parser(
        subparsers, "batch8-tools-tail-primitives-capsule"
    )
    batch8_tools_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_tools_parser)
    batch8_tools_parser.add_argument("--acceptance-out")

    batch8_policy_parser = _add_bundle_parser(
        subparsers, "batch8-policy-engines-capsule"
    )
    batch8_policy_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_policy_parser)
    batch8_policy_parser.add_argument("--acceptance-out")

    batch8_audio_parser = _add_bundle_parser(
        subparsers, "batch8-audio-level-rms-port"
    )
    batch8_audio_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_audio_parser)
    batch8_audio_parser.add_argument("--acceptance-out")

    batch8_station_parser = _add_bundle_parser(
        subparsers, "batch8-station-surface-atlas-layout-port"
    )
    batch8_station_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_station_parser)
    batch8_station_parser.add_argument("--acceptance-out")

    batch8_structural_parser = _add_bundle_parser(
        subparsers, "batch8-structural-theses-capsule"
    )
    batch8_structural_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_structural_parser)
    batch8_structural_parser.add_argument("--acceptance-out")

    batch8_compliance_parser = _add_bundle_parser(
        subparsers, "batch8-compliance-pipeline-capsule"
    )
    batch8_compliance_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_compliance_parser)
    batch8_compliance_parser.add_argument("--acceptance-out")

    batch8_validator_parser = _add_bundle_parser(
        subparsers, "batch8-validator-checker-capsule"
    )
    batch8_validator_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch8_validator_parser)
    batch8_validator_parser.add_argument("--acceptance-out")

    concurrency_mission_control_parser = _add_bundle_parser(
        subparsers, "concurrency-mission-control"
    )
    concurrency_mission_control_parser.add_argument(
        "action", choices=["run", "run-concurrency-mission-control-bundle"]
    )
    _add_input_out(concurrency_mission_control_parser)
    concurrency_mission_control_parser.add_argument("--acceptance-out")

    batch7_parser = _add_bundle_parser(
        subparsers, "batch7-macro-engines-capsule"
    )
    batch7_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch7_parser)
    batch7_parser.add_argument("--acceptance-out")

    batch7_station_parser = _add_bundle_parser(
        subparsers, "batch7-station-runtime-capsule"
    )
    batch7_station_parser.add_argument(
        "action", choices=["run", "run-batch7-station-bundle"]
    )
    _add_input_out(batch7_station_parser)
    batch7_station_parser.add_argument("--acceptance-out")

    batch9_parser = _add_bundle_parser(
        subparsers, "batch9-macro-engines-capsule"
    )
    batch9_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch9_parser)
    batch9_parser.add_argument("--acceptance-out")

    batch10_governance_parser = _add_bundle_parser(
        subparsers, "batch10-governance-compilers-capsule"
    )
    batch10_governance_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch10_governance_parser)
    batch10_governance_parser.add_argument("--acceptance-out")

    batch10_frontend_parser = _add_bundle_parser(
        subparsers, "batch10-frontend-work-market-cockpit-capsule"
    )
    batch10_frontend_parser.add_argument(
        "action", choices=["run", "run-batch10-frontend-work-market-bundle"]
    )
    _add_input_out(batch10_frontend_parser)
    batch10_frontend_parser.add_argument("--acceptance-out")

    batch10_live_drift_parser = _add_bundle_parser(
        subparsers, "batch10-live-source-drift-capsule"
    )
    batch10_live_drift_parser.add_argument(
        "action", choices=["run", "validate-bundle"]
    )
    _add_input_out(batch10_live_drift_parser)
    batch10_live_drift_parser.add_argument("--acceptance-out")

    batch10_cold_eval_parser = _add_bundle_parser(
        subparsers, "batch10-cold-eval-honesty-capsule"
    )
    batch10_cold_eval_parser.add_argument(
        "action", choices=["run", "run-batch10-cold-eval-bundle"]
    )
    _add_input_out(batch10_cold_eval_parser)
    batch10_cold_eval_parser.add_argument("--acceptance-out")

    batch11_saturation_parser = _add_bundle_parser(
        subparsers, "batch11-saturation-engines-capsule"
    )
    batch11_saturation_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch11_saturation_parser)
    batch11_saturation_parser.add_argument("--acceptance-out")

    batch12_market_dashboard_parser = _add_bundle_parser(
        subparsers, "batch12-market-dashboard-read-model-capsule"
    )
    batch12_market_dashboard_parser.add_argument(
        "action", choices=["run", "run-market-dashboard-bundle"]
    )
    _add_input_out(batch12_market_dashboard_parser)
    batch12_market_dashboard_parser.add_argument("--acceptance-out")

    batch12_prediction_parser = _add_bundle_parser(
        subparsers, "batch12-prediction-market-board-capsule"
    )
    batch12_prediction_parser.add_argument(
        "action", choices=["run", "run-prediction-market-board-bundle"]
    )
    _add_input_out(batch12_prediction_parser)
    batch12_prediction_parser.add_argument("--acceptance-out")

    batch12_release_gate_parser = _add_bundle_parser(
        subparsers, "batch12-release-claim-language-gate"
    )
    batch12_release_gate_parser.add_argument(
        "action", choices=["run", "run-release-claim-language-gate-bundle"]
    )
    _add_input_out(batch12_release_gate_parser)
    batch12_release_gate_parser.add_argument("--acceptance-out")

    batch4_parser = _add_bundle_parser(
        subparsers, "batch4-proof-authority-runtime"
    )
    batch4_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(batch4_parser)
    batch4_parser.add_argument("--acceptance-out")

    evidence_cell_parser = _add_bundle_parser(
        subparsers, "formal-evidence-cell-anchor-resolver"
    )
    evidence_cell_parser.add_argument("action", choices=["run", "run-anchor-bundle"])
    _add_input_out(evidence_cell_parser)

    symbol_classifier_parser = _add_bundle_parser(
        subparsers, "undeclared-library-prior-symbol-classifier"
    )
    symbol_classifier_parser.add_argument("action", choices=["run", "run-symbol-bundle"])
    _add_input_out(symbol_classifier_parser)
    symbol_classifier_parser.add_argument("--acceptance-out")

    benchmark_integrity_parser = _add_bundle_parser(
        subparsers,
        "agent-benchmark-integrity-anti-gaming-replay"
    )
    benchmark_integrity_parser.add_argument(
        "action", choices=["run", "run-benchmark-integrity-bundle"]
    )
    _add_input_out(benchmark_integrity_parser)
    benchmark_integrity_parser.add_argument("--acceptance-out")

    monitor_redteam_parser = _add_bundle_parser(
        subparsers,
        "agent-monitor-redteam-falsification-replay"
    )
    monitor_redteam_parser.add_argument(
        "action", choices=["run", "run-monitor-bundle"]
    )
    _add_input_out(monitor_redteam_parser)
    monitor_redteam_parser.add_argument("--acceptance-out")

    sabotage_monitor_parser = _add_bundle_parser(
        subparsers,
        "agent-sabotage-scheming-monitor-replay"
    )
    sabotage_monitor_parser.add_argument(
        "action", choices=["run", "run-sabotage-bundle"]
    )
    _add_input_out(sabotage_monitor_parser)
    sabotage_monitor_parser.add_argument("--acceptance-out")

    sandbox_policy_parser = _add_bundle_parser(
        subparsers,
        "agent-sandbox-policy-escape-replay"
    )
    sandbox_policy_parser.add_argument(
        "action", choices=["run", "run-sandbox-bundle"]
    )
    _add_input_out(sandbox_policy_parser)
    sandbox_policy_parser.add_argument("--acceptance-out")

    prompt_injection_parser = _add_bundle_parser(
        subparsers,
        "indirect-prompt-injection-information-flow-policy-replay"
    )
    prompt_injection_parser.add_argument(
        "action", choices=["run", "run-prompt-injection-bundle"]
    )
    _add_input_out(prompt_injection_parser)
    prompt_injection_parser.add_argument("--acceptance-out")

    agentic_vuln_parser = _add_bundle_parser(
        subparsers,
        "agentic-vulnerability-discovery-patch-proof-replay"
    )
    agentic_vuln_parser.add_argument(
        "action", choices=["run", "run-patch-proof-bundle"]
    )
    _add_input_out(agentic_vuln_parser)
    agentic_vuln_parser.add_argument("--acceptance-out")

    memory_conflict_parser = _add_bundle_parser(
        subparsers,
        "agent-memory-temporal-conflict-replay"
    )
    memory_conflict_parser.add_argument(
        "action", choices=["run", "run-memory-bundle"]
    )
    _add_input_out(memory_conflict_parser)
    memory_conflict_parser.add_argument("--acceptance-out")

    sleeper_memory_parser = _add_bundle_parser(
        subparsers,
        "sleeper-memory-poisoning-quarantine-replay"
    )
    sleeper_memory_parser.add_argument(
        "action", choices=["run", "run-quarantine-bundle"]
    )
    _add_input_out(sleeper_memory_parser)
    sleeper_memory_parser.add_argument("--acceptance-out")

    mcp_tool_parser = _add_bundle_parser(subparsers, "mcp-tool-authority-replay")
    mcp_tool_parser.add_argument(
        "action", choices=["run", "run-tool-authority-bundle"]
    )
    _add_input_out(mcp_tool_parser)
    mcp_tool_parser.add_argument("--acceptance-out")

    governed_mutation_parser = _add_bundle_parser(
        subparsers,
        "proof-derived-governed-mutation-authorization"
    )
    governed_mutation_parser.add_argument(
        "action", choices=["run", "run-authorization-bundle"]
    )
    _add_input_out(governed_mutation_parser)
    governed_mutation_parser.add_argument("--acceptance-out")

    belief_reward_parser = _add_bundle_parser(
        subparsers,
        "belief-state-process-reward-replay"
    )
    belief_reward_parser.add_argument("action", choices=["run", "run-reward-bundle"])
    _add_input_out(belief_reward_parser)
    belief_reward_parser.add_argument("--acceptance-out")

    lean_std_index_parser = _add_bundle_parser(subparsers, "lean-std-premise-index")
    lean_std_index_parser.add_argument("action", choices=["run", "run-index-bundle"])
    _add_input_out(lean_std_index_parser)

    provider_context_parser = _add_bundle_parser(
        subparsers, "provider-context-recipe-budget-policy"
    )
    provider_context_parser.add_argument("action", choices=["run", "run-budget-bundle"])
    _add_input_out(provider_context_parser)

    ring2_parser = _add_bundle_parser(
        subparsers, "ring2-premise-retrieval-precision-recall-harness"
    )
    ring2_parser.add_argument("action", choices=["run", "run-precision-recall-bundle"])
    _add_input_out(ring2_parser)

    durable_landing_parser = _add_bundle_parser(
        subparsers, "durable-agent-work-landing-replay"
    )
    durable_landing_parser.add_argument("action", choices=["run", "run-work-landing-bundle"])
    _add_input_out(durable_landing_parser)
    durable_landing_parser.add_argument("--acceptance-out")

    research_replication_parser = _add_bundle_parser(
        subparsers,
        "research-replication-rubric-artifact-replay"
    )
    research_replication_parser.add_argument(
        "action", choices=["run", "run-replication-bundle"]
    )
    _add_input_out(research_replication_parser)
    research_replication_parser.add_argument("--acceptance-out")

    drift_control_room_parser = _add_bundle_parser(
        subparsers,
        "world-model-projection-drift-control-room"
    )
    drift_control_room_parser.add_argument(
        "action", choices=["run", "run-drift-control-bundle"]
    )
    _add_input_out(drift_control_room_parser)
    drift_control_room_parser.add_argument("--acceptance-out")

    spatial_simulation_parser = _add_bundle_parser(
        subparsers,
        "spatial-world-model-counterfactual-simulation-replay"
    )
    spatial_simulation_parser.add_argument(
        "action", choices=["run", "run-simulation-bundle"]
    )
    _add_input_out(spatial_simulation_parser)
    spatial_simulation_parser.add_argument("--acceptance-out")

    materials_lab_safety_parser = _add_bundle_parser(
        subparsers,
        "materials-chemistry-closed-loop-lab-safety-replay"
    )
    materials_lab_safety_parser.add_argument(
        "action", choices=["run", "run-lab-bundle"]
    )
    _add_input_out(materials_lab_safety_parser)
    materials_lab_safety_parser.add_argument("--acceptance-out")

    circuit_attribution_parser = _add_bundle_parser(
        subparsers,
        "mechanistic-interpretability-circuit-attribution-replay"
    )
    circuit_attribution_parser.add_argument(
        "action", choices=["run", "run-attribution-bundle"]
    )
    _add_input_out(circuit_attribution_parser)
    circuit_attribution_parser.add_argument("--acceptance-out")

    public_reveal_parser = _add_bundle_parser(subparsers, "public-reveal-walkthrough")
    public_reveal_parser.add_argument("action", choices=["run", "run-reveal-bundle"])
    _add_input_out(public_reveal_parser)

    macro_projection_parser = _add_bundle_parser(
        subparsers, "macro-projection-import-protocol"
    )
    macro_projection_parser.add_argument(
        "action",
        choices=[
            "run",
            "run-projection-bundle",
            "plan",
            "refresh-exact-copy-source-modules",
        ],
    )
    macro_projection_parser.add_argument("--input", required=True)
    macro_projection_parser.add_argument("--out")
    macro_projection_parser.add_argument("--source-root")
    macro_projection_parser.add_argument("--material-id", action="append", default=[])
    macro_projection_parser.add_argument(
        "--all-examples",
        action="store_true",
        help="scan all public example source-module manifests during exact-copy refresh",
    )
    macro_projection_parser.add_argument(
        "--write",
        action="store_true",
        help="apply exact-copy source-module refreshes instead of reporting drift only",
    )
    macro_projection_parser.add_argument(
        "--card",
        action="store_true",
        help="read cached projection-bundle validation state without rerunning",
    )

    prediction_parser = _add_bundle_parser(
        subparsers, "prediction-oracle-reconciliation"
    )
    prediction_parser.add_argument("action", choices=["run", "run-prediction-bundle"])
    _add_input_out(prediction_parser)

    cognitive_operator_parser = _add_bundle_parser(
        subparsers, "cognitive-operator-registry"
    )
    cognitive_operator_parser.add_argument(
        "action", choices=["run", "run-registry-bundle"]
    )
    _add_input_out(cognitive_operator_parser)
    cognitive_operator_parser.add_argument("--acceptance-out")

    routing_anti_patterns_parser = _add_bundle_parser(
        subparsers, "routing-anti-patterns-registry"
    )
    routing_anti_patterns_parser.add_argument("action", choices=["run", "run-bundle"])
    _add_input_out(routing_anti_patterns_parser)
    routing_anti_patterns_parser.add_argument("--acceptance-out")

    tool_server_pressure_parser = _add_bundle_parser(
        subparsers, "tool-server-pressure-inventory"
    )
    tool_server_pressure_parser.add_argument(
        "action", choices=["run", "run-pressure-bundle"]
    )
    _add_input_out(tool_server_pressure_parser)
    tool_server_pressure_parser.add_argument("--acceptance-out")

    workstream_driver_parser = _add_bundle_parser(
        subparsers, "workstream-driver-recency-coalescer"
    )
    workstream_driver_parser.add_argument("action", choices=["run", "validate-bundle"])
    _add_input_out(workstream_driver_parser)
    workstream_driver_parser.add_argument("--acceptance-out")

    standards_meta_parser = _add_bundle_parser(subparsers, "standards-meta-diagnostics")
    standards_meta_parser.add_argument("action", choices=["run", "run-diagnostics-bundle"])
    _add_input_out(standards_meta_parser)
    standards_meta_parser.add_argument("--acceptance-out")

    cold_reader_parser = _add_bundle_parser(subparsers, "cold-reader-route-map")
    cold_reader_parser.add_argument("action", choices=["run", "run-route-map-bundle"])
    _add_input_out(cold_reader_parser)
    cold_reader_parser.add_argument("--card", action="store_true")

    navigation_parser = _add_bundle_parser(
        subparsers, "navigation-hologram-route-plane"
    )
    navigation_parser.add_argument("action", choices=["run", "validate-route-plane-bundle"])
    _add_input_out(navigation_parser)

    mission_parser = _add_bundle_parser(subparsers, "mission-transaction-work-spine")
    mission_parser.add_argument("action", choices=["run", "validate-mission-transaction-bundle"])
    _add_input_out(mission_parser)

    observability_parser = _add_bundle_parser(
        subparsers, "agent-route-observability-runtime"
    )
    observability_parser.add_argument(
        "action",
        choices=[
            "run",
            "validate-observability-bundle",
            "validate-computer-use-bundle",
            "validate-session-attribution-bundle",
            "validate-harness-configuration-bundle",
            "validate-multi-agent-fanin-bundle",
            "validate-bridge-dispatch-yield-resume-bundle",
            "validate-controller-heartbeat-bundle",
            "validate-agent-trace-route-repair-bundle",
            "validate-agent-observability-store-bundle",
        ],
    )
    _add_input_out(observability_parser)

    bridge_continuity_parser = _add_bundle_parser(
        subparsers, "bridge-phase-continuity-runtime"
    )
    bridge_continuity_parser.usage = (
        "%(prog)s run --input INPUT --out OUT [--card]"
    )
    bridge_continuity_parser.add_argument("action", choices=["run"])
    _add_input_out(bridge_continuity_parser)
    bridge_continuity_parser.add_argument(
        "--card",
        action="store_true",
        help="emit the compact bridge continuity card",
    )

    assimilation_parser = _add_bundle_parser(subparsers, "pattern-assimilation-step")
    assimilation_parser.add_argument("action", nargs="?", choices=["run", "validate-assimilation-bundle"], default="run")
    _add_input_out(assimilation_parser)

    voice_to_doctrine_parser = _add_bundle_parser(
        subparsers,
        "voice-to-doctrine-self-improvement-loop"
    )
    voice_to_doctrine_parser.add_argument("action", choices=["run", "run-bundle"])
    _add_input_out(voice_to_doctrine_parser)
    voice_to_doctrine_parser.add_argument("--acceptance-out")

    args = parser.parse_args(argv)
    if args.command == "init":
        return project_substrate.main(["init", args.project])
    if args.command == "index":
        return project_substrate.main(["index", args.project])
    if args.command == "catalog":
        return project_substrate.main(["catalog", args.project])
    if args.command == "architecture":
        return project_substrate.main(["architecture", args.project])
    if args.command == "compile":
        if args.card:
            return _print_json(project_substrate.compile_project_card(args.project))
        return project_substrate.main(["compile", args.project])
    if args.command == "python-lens":
        command_args = ["python-lens"]
        if args.full:
            command_args.append("--full")
        command_args.append(args.project)
        return project_substrate.main(command_args)
    if args.command == "graph":
        return project_substrate.main(["graph", args.project])
    if args.command == "explain":
        return project_substrate.main(["explain", args.project, args.route_id])
    if args.command in {"status", "status-card"}:
        runtime_project = _runtime_project_arg(args.project)
        command_args = ["status"]
        card_requested = args.command == "status-card" or args.card
        if card_requested:
            project_public_root = _public_root_for_project(args.project)
            shell = (
                runtime_shell.RuntimeShell(root=project_public_root)
                if project_public_root is not None
                else runtime_shell.RuntimeShell()
            )
            project_ref = _cli_project_command_ref(args.project)
            payload = shell.status_card(
                args.project or runtime_project,
                project_ref=project_ref,
            )
            if args.project:
                payload = _attach_status_card_front_door_refs(payload)
                payload = _compact_project_status_card_for_cli(payload)
            return _print_json(payload, exit_code=_status_card_exit_code(payload))
        if args.project:
            project_public_root = _public_root_for_project(args.project)
            shell = (
                runtime_shell.RuntimeShell(root=project_public_root)
                if project_public_root is not None
                else runtime_shell.RuntimeShell()
            )
            return _print_json(
                shell.status(
                    runtime_project or args.project,
                    project_ref="<project>",
                )
            )
        return runtime_shell.main(command_args, root=None)
    if args.command == "proof-lab":
        if args.card:
            command = _proof_lab_card_command(args.input, args.out)
            result = _proof_lab_cached_result(args.input, args.out)
        else:
            command = _proof_lab_command(args.input, args.out)
            tool_versions = formal_math_lean_proof_witness._tool_versions()
            if _proof_lab_toolchain_ready(tool_versions):
                result = verifier_lab_kernel.run_kernel_bundle(
                    args.input,
                    args.out,
                    command=command,
                )
            else:
                result = _proof_lab_canonical_receipt_result(
                    input_path=args.input,
                    out_dir=args.out,
                    cache_status="canonical_receipt_fallback_toolchain_missing",
                    live_receipt_rebuild_status="skipped_toolchain_missing",
                    tool_versions=tool_versions,
                )
                if result is None:
                    result = verifier_lab_kernel.run_kernel_bundle(
                        args.input,
                        args.out,
                        command=command,
                    )
        proof_lab_card = _proof_lab_first_screen_card(
            result,
            input_path=args.input,
            out_dir=args.out,
            command=command,
        )
        return _print_json(
            proof_lab_card,
            exit_code=_proof_lab_card_exit_code(proof_lab_card),
        )
    if args.command == "spine":
        command_args = ["spine"]
        if args.card:
            command_args.append("--card")
        return runtime_shell.main(
            command_args,
            root=_runtime_root_for_project_arg(args.project),
        )
    if args.command == "tour":
        command_args = ["tour"]
        if args.card:
            command_args.append("--card")
        if args.project:
            command_args.append(_runtime_project_arg(args.project) or args.project)
        return runtime_shell.main(command_args, root=_public_root_for_project(args.project))
    if args.command == "hello":
        return _emit_hello(args.project, args.reader)
    if args.command == "first-screen":
        return _emit_first_screen(
            args.project,
            output_format=args.format,
            full=args.full,
            reader=args.reader,
        )
    if args.command == "agent-entry-composition":
        payload = agent_entry_composition.compile_paths(
            root=args.root,
            task=args.task,
            viewer=args.viewer,
            out=args.out,
            command="microcosm agent-entry-composition",
        )
        if args.card:
            payload = agent_entry_composition.compact_agent_entry_card(payload)
        return _print_json(
            payload,
            exit_code=0 if payload.get("status") == "pass" or not args.check else 1,
        )
    if args.command == "organ-discoverability-matrix":
        payload = organ_discoverability_matrix.compile_paths(
            root=args.root,
            out=args.out,
        )
        validation = payload.get("validation") if isinstance(payload, dict) else {}
        validation_status = (
            validation.get("status") if isinstance(validation, dict) else None
        )
        return _print_json(
            payload,
            exit_code=0 if validation_status == "pass" or not args.check else 1,
        )
    if args.command == "authority":
        command_args = ["authority"]
        if args.card:
            command_args.append("--card")
        return runtime_shell.main(
            command_args,
            root=_runtime_root_for_project_arg(args.project),
        )
    if args.command in PUBLIC_LENS_COMMANDS:
        command_args = [args.command]
        if args.command in PUBLIC_LENS_CARD_AWARE_COMMANDS and args.card:
            command_args.append("--card")
        return runtime_shell.main(
            command_args,
            root=_runtime_root_for_project_arg(args.project),
        )
    if args.command == "run":
        command_args = ["run"]
        if args.card:
            command_args.append("--card")
        command_args.append(args.project)
        return runtime_shell.main(command_args)
    if args.command == "serve":
        serve_args = ["serve", "--host", args.host, "--port", str(args.port)]
        if args.max_requests is not None:
            serve_args.extend(["--max-requests", str(args.max_requests)])
        if args.project:
            serve_args.append(_runtime_project_arg(args.project) or args.project)
        try:
            return runtime_shell.main(
                serve_args,
                root=_public_root_for_project(args.project),
            )
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
            print(
                (
                    f"microcosm serve could not bind http://{args.host}:{args.port}: "
                    "address already in use. Choose a free port, for example "
                    f"`microcosm serve {args.project or '<project>'} "
                    f"--host {args.host} --port {args.port + 1} --max-requests "
                    f"{args.max_requests or 7}`."
                ),
                file=sys.stderr,
            )
            return 2
    if args.command == "patterns":
        if args.project:
            return project_substrate.main(["patterns", args.project])
        return runtime_shell.main(["patterns"])
    if args.command == "route":
        if args.route_args == ["list"]:
            return runtime_shell.main(["route", "list"])
        if len(args.route_args) == 2 and args.route_args[0] == "inspect":
            return runtime_shell.main(["route", "inspect", args.route_args[1]])
        if len(args.route_args) == 3 and args.route_args[0] == "inspect":
            return project_substrate.main(["explain", args.route_args[1], args.route_args[2]])
        if len(args.route_args) == 1:
            return project_substrate.main(["route", args.route_args[0]])
    if args.command == "work":
        if args.work_command == "demo":
            return runtime_shell.main(["work", "demo"])
        if args.work_command == "create":
            work_args = ["work", "create", args.project]
            if args.route:
                work_args.extend(["--route", args.route])
            return project_substrate.main(work_args)
        if args.work_command == "run":
            work_args = ["work", "run", args.project]
            if args.work_id:
                work_args.extend(["--work-id", args.work_id])
            return project_substrate.main(work_args)
    if args.command == "observe":
        observe_args = ["observe", args.project]
        if args.card:
            observe_args = ["observe", "--card", args.project]
        return project_substrate.main(observe_args)
    if args.command == "evidence":
        if args.evidence_command == "list":
            evidence_limit = None if args.limit == 0 else args.limit
            if args.project:
                boundary = _project_evidence_state_boundary(args.project)
                if boundary is not None:
                    return _print_json(boundary)
                return _print_json(
                    project_substrate.list_evidence(
                        args.project,
                        limit=evidence_limit,
                    )
                )
            return _print_json(
                runtime_evidence_index.list_runtime_evidence(
                    MICROCOSM_ROOT,
                    limit=evidence_limit,
                )
            )
        if args.evidence_command == "inspect":
            project_arg = args.project
            receipt_ref = args.receipt_ref
            if args.project_evidence_ref:
                if args.project:
                    print(
                        (
                            "microcosm evidence inspect accepts either "
                            "`--project <project> <ref>` or `<project> <ref>`, not both."
                        ),
                        file=sys.stderr,
                    )
                    return 2
                project_arg = args.receipt_ref
                receipt_ref = args.project_evidence_ref
            elif (
                not project_arg
                and args.receipt_ref.startswith(f"{project_substrate.STATE_DIR}/")
            ):
                project_arg = "."
            if project_arg:
                boundary = _project_evidence_state_boundary(project_arg)
                if boundary is not None:
                    return _print_json({**boundary, "evidence_ref": receipt_ref})
                payload = project_substrate.inspect_evidence(project_arg, receipt_ref)
                payload["project_ref"] = project_arg
                return _print_json(payload)
            return runtime_shell.main(["evidence", "inspect", receipt_ref])
    if args.command == "private-state-scan":
        return private_state_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "secret-exclusion-scan":
        return secret_exclusion_scan.main(["--root", args.root, "--out", args.out] + (["--policy", args.policy] if args.policy else []))
    if args.command == "public-entry-docs":
        return public_entry_docs.main(["--root", args.root, "--out", args.out])
    if args.command == "organ-surface-contract":
        contract_args = ["--root", args.root]
        if args.out:
            contract_args.extend(["--out", args.out])
        if args.card:
            contract_args.append("--card")
        return organ_surface_contract.main(contract_args)
    if args.command == "organ-topology":
        contract_args = ["--root", args.root, "--topology"]
        if args.out:
            contract_args.extend(["--out", args.out])
        if args.organ:
            contract_args.extend(["--organ", args.organ])
        if args.relation_type:
            contract_args.extend(["--relation-type", args.relation_type])
        if args.source_ref:
            contract_args.extend(["--source-ref", args.source_ref])
        if args.target_ref:
            contract_args.extend(["--target-ref", args.target_ref])
        if args.manifest_ref:
            contract_args.extend(["--manifest-ref", args.manifest_ref])
        if args.shard_ref:
            contract_args.extend(["--shard-ref", args.shard_ref])
        if args.validation_ref:
            contract_args.extend(["--validation-ref", args.validation_ref])
        return organ_surface_contract.main(contract_args)
    if args.command == "research-kernel-density":
        density_args = ["--root", args.root, "--out", args.out]
        if args.project:
            density_args.extend(["--project", args.project])
        return research_kernel_density.main(density_args)
    if args.command == "transaction-evidence-stability":
        return transaction_evidence_stability.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "observatory-legibility":
        return observatory_legibility.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "launch-compression":
        return launch_compression.main(
            ["--root", args.root, "--project", args.project, "--out", args.out]
        )
    if args.command == "standards-registry":
        return standards_registry.main(
            [
                "--registry",
                args.registry,
                "--standards-dir",
                args.standards_dir,
                "--acceptance",
                args.acceptance,
                "--out",
                args.out,
            ]
        )
    if args.command == "doctrine-lattice":
        lattice_args = ["--root", args.root]
        if args.out:
            lattice_args.extend(["--out", args.out])
        if args.action == "check":
            lattice_args.append("--check")
        elif args.action == "write":
            lattice_args.append("--write")
        elif args.action == "status":
            lattice_args.append("--status")
        elif args.action == "entry-card":
            lattice_args.append("--entry-card")
        elif args.action == "write-entry-card":
            lattice_args.append("--write-entry-card")
        elif args.action == "check-entry-card":
            lattice_args.append("--check-entry-card")
        return doctrine_lattice.main(lattice_args)
    if args.command == "dependency-preflight":
        return dependency_preflight.main(
            [
                "--readiness",
                args.readiness,
                "--negative-matrix",
                args.negative_matrix,
                "--out",
                args.out,
            ]
        )
    if args.command == "fixture-freshness":
        return fixture_freshness.main(
            [
                "--readiness",
                args.readiness,
                "--negative-matrix",
                args.negative_matrix,
                "--mission-dag",
                args.mission_dag,
                "--receipt-coverage",
                args.receipt_coverage,
                "--out",
                args.out,
            ]
        )
    if args.command == "pattern-binding":
        return pattern_binding_contract.main([args.action, "--input", args.input, "--out", args.out])
    if args.command == "pattern-route-readiness":
        return pattern_binding_contract.main(
            [
                "validate-route-readiness-bundle",
                "--input",
                args.input,
                "--out",
                args.out,
            ]
        )
    if args.command == "crown-jewel-demo":
        demo_args = [args.action]
        if args.out:
            demo_args.extend(["--out", args.out])
        return crown_jewel_demo.main(demo_args)
    if args.command == "macro-engines-gallery":
        gallery_args = [args.action]
        if args.out:
            gallery_args.extend(["--out", args.out])
        return macro_engines_gallery.main(gallery_args)
    if args.command == "engine-room-demo":
        demo_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            demo_args.extend(["--acceptance-out", args.acceptance_out])
        return engine_room_demo.main(demo_args)
    if args.command == "agent-closeout-faithfulness-audit":
        return agent_closeout_faithfulness_audit.main(_organ_command_args(args))
    if args.command == "doctrine-fact-claim-audit":
        return doctrine_fact_claim_audit.main(_organ_command_args(args))
    if args.command == "self-ignorance-coverage-ledger":
        return self_ignorance_coverage_ledger.main(_organ_command_args(args))
    if args.command == "bounded-autonomy-campaign-packet":
        return bounded_autonomy_campaign_packet.main(_organ_command_args(args))
    if args.command == "finance-forecast-evaluation-spine":
        return finance_forecast_evaluation_spine.main(_organ_command_args(args))
    if args.command == "finance-eval-spine":
        return finance_eval_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "work-landing-control-spine":
        return work_landing_control_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "executable-doctrine-grammar":
        return executable_doctrine_grammar.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "proof-diagnostic-evidence-spine":
        proof_args = [args.action, "--input", args.input, "--out", args.out]
        if args.card:
            proof_args.append("--card")
        return proof_diagnostic_evidence_spine.main(proof_args)
    if args.command == "formal-math-readiness-gate":
        formal_math_args = [args.action, "--input", args.input]
        if args.out:
            formal_math_args.extend(["--out", args.out])
        elif args.action != "plan":
            parser.error("--out is required for formal math readiness receipt-writing actions")
        return formal_math_readiness_gate.main(formal_math_args)
    if args.command == "corpus-readiness-mathlib-absence-gate":
        return corpus_readiness_mathlib_absence_gate.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "mathematical-strategy-atlas-hypothesis-scorer":
        return mathematical_strategy_atlas_hypothesis_scorer.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "tactic-portfolio-availability-probe":
        return tactic_portfolio_availability_probe.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "target-shape-tactic-routing-gate":
        return target_shape_tactic_routing_gate.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-lean-proof-witness":
        return formal_math_lean_proof_witness.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-premise-retrieval":
        return formal_math_premise_retrieval.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "formal-math-verifier-trace-repair-loop":
        return formal_math_verifier_trace_repair_loop.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "verifier-lab-kernel":
        verifier_lab_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            verifier_lab_args.extend(["--acceptance-out", args.acceptance_out])
        return verifier_lab_kernel.main(verifier_lab_args)
    if args.command == "verifier-lab-execution-spine":
        verifier_lab_execution_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            verifier_lab_execution_args.extend(
                ["--acceptance-out", args.acceptance_out]
            )
        return verifier_lab_execution_spine.main(verifier_lab_execution_args)
    if args.command == "certificate-kernel-execution-lab":
        certificate_kernel_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            certificate_kernel_args.extend(["--acceptance-out", args.acceptance_out])
        return certificate_kernel_execution_lab.main(certificate_kernel_args)
    if args.command == "batch4-proof-authority-runtime":
        batch4_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch4_args.extend(["--acceptance-out", args.acceptance_out])
        return batch4_proof_authority_runtime.main(batch4_args)
    if args.command == "batch5-authority-systems-capsule":
        batch5_args = _organ_command_args(args)
        return batch5_authority_systems_capsule.main(batch5_args)
    if args.command == "batch6-unsurfaced-primitives-capsule":
        batch6_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch6_args.extend(["--acceptance-out", args.acceptance_out])
        return batch6_unsurfaced_primitives_capsule.main(batch6_args)
    if args.command == "batch7-demo-take-console-capsule":
        batch7_demo_args = _organ_command_args(args)
        return batch7_demo_take_console_capsule.main(batch7_demo_args)
    if args.command == "batch7-oracle-sibling-capsule":
        batch7_oracle_args = _organ_command_args(args)
        return batch7_oracle_sibling_capsule.main(batch7_oracle_args)
    if args.command == "batch7-secondary-runtime-capsule":
        batch7_secondary_args = _organ_command_args(args)
        return batch7_secondary_runtime_capsule.main(batch7_secondary_args)
    if args.command == "batch8-tools-tail-primitives-capsule":
        batch8_tools_args = _organ_command_args(args)
        return batch8_tools_tail_primitives_capsule.main(batch8_tools_args)
    if args.command == "batch8-policy-engines-capsule":
        batch8_policy_args = _organ_command_args(args)
        return batch8_policy_engines_capsule.main(batch8_policy_args)
    if args.command == "batch8-audio-level-rms-port":
        batch8_audio_args = _organ_command_args(args)
        return batch8_audio_level_rms_port.main(batch8_audio_args)
    if args.command == "batch8-station-surface-atlas-layout-port":
        batch8_station_args = _organ_command_args(args)
        return batch8_station_surface_atlas_layout_port.main(batch8_station_args)
    if args.command == "batch8-structural-theses-capsule":
        batch8_structural_args = _organ_command_args(args)
        return batch8_structural_theses_capsule.main(batch8_structural_args)
    if args.command == "batch7-macro-engines-capsule":
        batch7_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch7_args.extend(["--acceptance-out", args.acceptance_out])
        return batch7_macro_engines_capsule.main(batch7_args)
    if args.command == "batch7-station-runtime-capsule":
        batch7_station_args = _organ_command_args(args)
        return batch7_station_runtime_capsule.main(batch7_station_args)
    if args.command == "batch9-macro-engines-capsule":
        batch9_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch9_args.extend(["--acceptance-out", args.acceptance_out])
        return batch9_macro_engines_capsule.main(batch9_args)
    if args.command == "batch10-governance-compilers-capsule":
        batch10_governance_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch10_governance_args.extend(["--acceptance-out", args.acceptance_out])
        return batch10_governance_compilers_capsule.main(batch10_governance_args)
    if args.command == "batch10-frontend-work-market-cockpit-capsule":
        batch10_frontend_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch10_frontend_args.extend(["--acceptance-out", args.acceptance_out])
        return batch10_frontend_work_market_cockpit_capsule.main(batch10_frontend_args)
    if args.command == "batch11-saturation-engines-capsule":
        batch11_saturation_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out:
            batch11_saturation_args.extend(["--acceptance-out", args.acceptance_out])
        return batch11_saturation_engines_capsule.main(batch11_saturation_args)
    if args.command == "batch12-market-dashboard-read-model-capsule":
        batch12_market_dashboard_args = _organ_command_args(args)
        return batch12_market_dashboard_read_model_capsule.main(
            batch12_market_dashboard_args
        )
    if args.command == "batch12-prediction-market-board-capsule":
        batch12_prediction_args = _organ_command_args(args)
        return batch12_prediction_market_board_capsule.main(batch12_prediction_args)
    if args.command == "batch12-release-claim-language-gate":
        batch12_release_gate_args = _organ_command_args(args)
        return batch12_release_claim_language_gate.main(batch12_release_gate_args)
    if args.command == "formal-evidence-cell-anchor-resolver":
        return formal_evidence_cell_anchor_resolver.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "undeclared-library-prior-symbol-classifier":
        symbol_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            symbol_args.extend(["--acceptance-out", args.acceptance_out])
        return undeclared_library_prior_symbol_classifier.main(symbol_args)
    if args.command == "agent-benchmark-integrity-anti-gaming-replay":
        benchmark_integrity_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            benchmark_integrity_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_benchmark_integrity_anti_gaming_replay.main(
            benchmark_integrity_args
        )
    if args.command == "agent-monitor-redteam-falsification-replay":
        monitor_redteam_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            monitor_redteam_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_monitor_redteam_falsification_replay.main(monitor_redteam_args)
    if args.command == "agent-sabotage-scheming-monitor-replay":
        sabotage_monitor_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sabotage_monitor_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_sabotage_scheming_monitor_replay.main(sabotage_monitor_args)
    if args.command == "agent-sandbox-policy-escape-replay":
        sandbox_policy_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sandbox_policy_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_sandbox_policy_escape_replay.main(sandbox_policy_args)
    if args.command == "indirect-prompt-injection-information-flow-policy-replay":
        prompt_injection_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            prompt_injection_args.extend(["--acceptance-out", args.acceptance_out])
        return indirect_prompt_injection_information_flow_policy_replay.main(
            prompt_injection_args
        )
    if args.command == "agentic-vulnerability-discovery-patch-proof-replay":
        agentic_vuln_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            agentic_vuln_args.extend(["--acceptance-out", args.acceptance_out])
        return agentic_vulnerability_discovery_patch_proof_replay.main(
            agentic_vuln_args
        )
    if args.command == "agent-memory-temporal-conflict-replay":
        memory_conflict_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            memory_conflict_args.extend(["--acceptance-out", args.acceptance_out])
        return agent_memory_temporal_conflict_replay.main(memory_conflict_args)
    if args.command == "sleeper-memory-poisoning-quarantine-replay":
        sleeper_memory_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            sleeper_memory_args.extend(["--acceptance-out", args.acceptance_out])
        return sleeper_memory_poisoning_quarantine_replay.main(sleeper_memory_args)
    if args.command == "mcp-tool-authority-replay":
        mcp_tool_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            mcp_tool_args.extend(["--acceptance-out", args.acceptance_out])
        return mcp_tool_authority_replay.main(mcp_tool_args)
    if args.command == "proof-derived-governed-mutation-authorization":
        governed_mutation_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            governed_mutation_args.extend(["--acceptance-out", args.acceptance_out])
        return proof_derived_governed_mutation_authorization.main(
            governed_mutation_args
        )
    if args.command == "belief-state-process-reward-replay":
        belief_reward_args = [
            args.action,
            "--input",
            args.input,
            "--out",
            args.out,
        ]
        if args.acceptance_out and args.action == "run":
            belief_reward_args.extend(["--acceptance-out", args.acceptance_out])
        return belief_state_process_reward_replay.main(belief_reward_args)
    if args.command == "lean-std-premise-index":
        return lean_std_premise_index.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "provider-context-recipe-budget-policy":
        return provider_context_recipe_budget_policy.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "ring2-premise-retrieval-precision-recall-harness":
        return ring2_premise_retrieval_precision_recall_harness.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "durable-agent-work-landing-replay":
        durable_landing_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            durable_landing_args.extend(["--acceptance-out", args.acceptance_out])
        return durable_agent_work_landing_replay.main(durable_landing_args)
    if args.command == "research-replication-rubric-artifact-replay":
        research_replication_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            research_replication_args.extend(["--acceptance-out", args.acceptance_out])
        return research_replication_rubric_artifact_replay.main(
            research_replication_args
        )
    if args.command == "world-model-projection-drift-control-room":
        drift_control_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            drift_control_args.extend(["--acceptance-out", args.acceptance_out])
        return world_model_projection_drift_control_room.main(drift_control_args)
    if args.command == "spatial-world-model-counterfactual-simulation-replay":
        spatial_simulation_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            spatial_simulation_args.extend(["--acceptance-out", args.acceptance_out])
        return spatial_world_model_counterfactual_simulation_replay.main(
            spatial_simulation_args
        )
    if args.command == "materials-chemistry-closed-loop-lab-safety-replay":
        materials_lab_safety_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            materials_lab_safety_args.extend(["--acceptance-out", args.acceptance_out])
        return materials_chemistry_closed_loop_lab_safety_replay.main(
            materials_lab_safety_args
        )
    if args.command == "mechanistic-interpretability-circuit-attribution-replay":
        circuit_attribution_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            circuit_attribution_args.extend(["--acceptance-out", args.acceptance_out])
        return mechanistic_interpretability_circuit_attribution_replay.main(
            circuit_attribution_args
        )
    if args.command == "public-reveal-walkthrough":
        return public_reveal_walkthrough.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "macro-projection-import-protocol":
        macro_args = [args.action, "--input", args.input]
        if args.action == "refresh-exact-copy-source-modules":
            if args.source_root:
                macro_args.extend(["--source-root", args.source_root])
            for material_id in args.material_id:
                macro_args.extend(["--material-id", material_id])
            if args.all_examples:
                macro_args.append("--all-examples")
            if args.write:
                macro_args.append("--write")
            return macro_projection_import_protocol.main(macro_args)
        if args.card:
            if args.action != "run-projection-bundle":
                parser.error(
                    "--card is only supported with "
                    "macro-projection-import-protocol run-projection-bundle"
                )
            macro_args.append("--card")
        if args.out:
            macro_args.extend(["--out", args.out])
        elif args.action != "plan":
            parser.error("--out is required for macro projection receipt-writing actions")
        return macro_projection_import_protocol.main(macro_args)
    if args.command == "prediction-oracle-reconciliation":
        return prediction_oracle_reconciliation.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "cognitive-operator-registry":
        cognitive_operator_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            cognitive_operator_args.extend(["--acceptance-out", args.acceptance_out])
        return cognitive_operator_registry.main(cognitive_operator_args)
    if args.command == "routing-anti-patterns-registry":
        routing_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            routing_args.extend(["--acceptance-out", args.acceptance_out])
        return routing_anti_patterns_registry.main(routing_args)
    if args.command == "tool-server-pressure-inventory":
        pressure_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            pressure_args.extend(["--acceptance-out", args.acceptance_out])
        return tool_server_pressure_inventory.main(pressure_args)
    if args.command == "workstream-driver-recency-coalescer":
        workstream_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            workstream_args.extend(["--acceptance-out", args.acceptance_out])
        return workstream_driver_recency_coalescer.main(workstream_args)
    if args.command == "batch8-compliance-pipeline-capsule":
        batch8_compliance_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            batch8_compliance_args.extend(["--acceptance-out", args.acceptance_out])
        return batch8_compliance_pipeline_capsule.main(batch8_compliance_args)
    if args.command == "batch8-validator-checker-capsule":
        batch8_validator_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            batch8_validator_args.extend(["--acceptance-out", args.acceptance_out])
        return batch8_validator_checker_capsule.main(batch8_validator_args)
    if args.command == "concurrency-mission-control":
        concurrency_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            concurrency_args.extend(["--acceptance-out", args.acceptance_out])
        return concurrency_mission_control.main(concurrency_args)
    if args.command == "batch10-live-source-drift-capsule":
        batch10_live_drift_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            batch10_live_drift_args.extend(["--acceptance-out", args.acceptance_out])
        return batch10_live_source_drift_capsule.main(batch10_live_drift_args)
    if args.command == "batch10-cold-eval-honesty-capsule":
        batch10_cold_eval_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            batch10_cold_eval_args.extend(["--acceptance-out", args.acceptance_out])
        return batch10_cold_eval_honesty_capsule.main(batch10_cold_eval_args)
    if args.command == "standards-meta-diagnostics":
        standards_meta_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            standards_meta_args.extend(["--acceptance-out", args.acceptance_out])
        return standards_meta_diagnostics.main(standards_meta_args)
    if args.command == "cold-reader-route-map":
        cold_reader_args = [args.action, "--input", args.input, "--out", args.out]
        if args.card:
            cold_reader_args.append("--card")
        return cold_reader_route_map.main(cold_reader_args)
    if args.command == "navigation-hologram-route-plane":
        return navigation_hologram_route_plane.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "mission-transaction-work-spine":
        return mission_transaction_work_spine.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "agent-route-observability-runtime":
        return agent_route_observability_runtime.main(
            [args.action, "--input", args.input, "--out", args.out]
        )
    if args.command == "bridge-phase-continuity-runtime":
        bridge_continuity_args = [args.action, "--input", args.input, "--out", args.out]
        if args.card:
            bridge_continuity_args.append("--card")
        return bridge_phase_continuity_runtime.main(bridge_continuity_args)
    if args.command == "voice-to-doctrine-self-improvement-loop":
        voice_to_doctrine_args = [args.action, "--input", args.input, "--out", args.out]
        if args.acceptance_out and args.action == "run":
            voice_to_doctrine_args.extend(["--acceptance-out", args.acceptance_out])
        return voice_to_doctrine_self_improvement_loop.main(voice_to_doctrine_args)
    if args.command == "pattern-assimilation-step":
        if args.action == "validate-assimilation-bundle":
            return acceptance.main(
                [
                    "validate-assimilation-bundle",
                    "--input",
                    args.input,
                    "--out",
                    args.out,
                ]
            )
        return acceptance.main(
            [
                "--only",
                "pattern_assimilation_step",
                "--input",
                args.input,
                "--out",
                args.out,
            ]
        )
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
