"""
[PURPOSE]
- Teleology: Cross-standard compliance adapter registry. Per-standard scanners
  emit std_compliance_finding-shaped rows from substrate evidence; the registry
  is consumed by tools/meta/factory/build_compliance_ledger.py to compose
  codex/hologram/compliance/ledger.json without each standard re-implementing
  scanner conventions.
- Mechanism: Each adapter exposes a `scan(repo_root: Path) -> dict` callable
  returning a per-standard coverage payload with applicable_artifact_count,
  checked_artifact_count, compliant_artifact_count, compliance_rate,
  top_failure_kinds, and findings (each shaped per
  codex/standards/std_compliance_finding.json).
- Non-goal: Adapters never mutate source authority. They read substrate and
  emit candidate evidence; promotion is controller-gated.

[INTERFACE]
- ADAPTERS: dict[standard_id, callable] mapping each supported standard to its
  scanner function.
- scan_all(repo_root): convenience helper that runs every adapter and returns
  a list of per-standard coverage payloads.

[FLOW]
- build_compliance_ledger imports ADAPTERS, walks each entry, calls scan,
  collects payloads, computes the cross-standard digest, writes
  codex/hologram/compliance/ledger.json.

[DEPENDENCIES]
- stdlib only; per-adapter modules under system.lib.compliance.

[CONSTRAINTS]
- Forbid: provider calls, source mutation, network IO. Adapters are pure
  filesystem readers.
- Atomicity: each adapter is independent; one failing adapter must not break
  the cross-standard digest (the builder catches and records adapter errors).
- Determinism: same substrate input -> same finding ids and same coverage
  numbers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping

from system.lib.compliance.aiw_movement_adapter import scan_aiw_movement
from system.lib.compliance.annex_standards_adapter import (
    scan_annex_catalog,
    scan_annex_contents,
    scan_annex_distillation,
    scan_annex_distillation_run_receipt,
    scan_annex_family,
    scan_annex_index,
    scan_annex_notes,
    scan_annex_pending,
    scan_annex_sync_report,
)
from system.lib.compliance.agent_bootstrap_adapter import scan_agent_bootstrap
from system.lib.compliance.agent_entrypoint_audit_adapter import scan_agent_entrypoint_audit
from system.lib.compliance.agent_execution_trace_adapter import scan_agent_execution_trace
from system.lib.compliance.agent_entry_surface_adapter import scan_agent_entry_surface
from system.lib.compliance.agent_seed_adapter import scan_agent_seed
from system.lib.compliance.agent_trace_lossless_clip_adapter import scan_agent_trace_lossless_clip
from system.lib.compliance.apply_adapter import scan_apply
from system.lib.compliance.approval_adapter import (
    scan_approval_decision_event,
    scan_approval_record,
)
from system.lib.compliance.architectural_projection_adapter import scan_architectural_projection
from system.lib.compliance.artifact_ontology_adapter import scan_artifact_ontology
from system.lib.compliance.axiom_candidate_adapter import scan_axiom_candidate
from system.lib.compliance.autonomous_seed_adapter import scan_autonomous_seed
from system.lib.compliance.autonomous_seed_prompt_adapter import scan_autonomous_seed_prompt
from system.lib.compliance.autonomy_plan_adapter import scan_autonomy_plan
from system.lib.compliance.autonomy_runtime_adapter import scan_autonomy_runtime
from system.lib.compliance.authority_reconciled_status_adapter import (
    scan_authority_reconciled_status,
)
from system.lib.compliance.bridge_campaign_adapter import scan_bridge_campaign
from system.lib.compliance.bridge_failure_class_adapter import scan_bridge_failure_class
from system.lib.compliance.bridge_info_request_adapter import scan_bridge_info_request
from system.lib.compliance.bridge_receipt_adapter import scan_bridge_receipt
from system.lib.compliance.bridge_response_validation_adapter import (
    scan_bridge_response_validation,
)
from system.lib.compliance.bridge_window_identity_adapter import scan_bridge_window_identity
from system.lib.compliance.campaign_state_adapter import (
    scan_campaign_state,
    scan_campaign_transition,
)
from system.lib.compliance.command_output_projection_adapter import scan_command_output_projection
from system.lib.compliance.compliance_coverage_adapter import scan_compliance_coverage
from system.lib.compliance.compliance_finding_adapter import scan_compliance_findings
from system.lib.compliance.config_authority_registry_adapter import scan_config_authority_registry
from system.lib.compliance.constitution_workspace_adapter import scan_constitution_workspace
from system.lib.compliance.continuation_packet_adapter import scan_continuation_packet
from system.lib.compliance.continuity_protocol_adapter import scan_continuity_protocol
from system.lib.compliance.controller_heartbeat_adapter import scan_controller_heartbeat
from system.lib.compliance.cycle_assimilation_adapter import scan_cycle_assimilation
from system.lib.compliance.cycle_summary_adapter import scan_cycle_summary
from system.lib.compliance.compute_provider_adapter import scan_compute_provider
from system.lib.compliance.cognitive_operator_adapter import scan_cognitive_operator
from system.lib.compliance.demo_take_package_adapter import scan_demo_take_package
from system.lib.compliance.demo_take_scene_plan_adapter import scan_demo_take_scene_plan
from system.lib.compliance.demo_take_story_package_adapter import scan_demo_take_story_package
from system.lib.compliance.doctrine_concept_adapter import scan_doctrine_concept
from system.lib.compliance.derived_fact_adapter import scan_derived_fact
from system.lib.compliance.documentation_meta_adapter import scan_documentation_meta
from system.lib.compliance.doc_registry_adapter import scan_doc_registry
from system.lib.compliance.doctrine_approved_overlay_adapter import scan_doctrine_approved_overlay
from system.lib.compliance.doctrine_derivation_adapter import scan_doctrine_derivation
from system.lib.compliance.doctrine_mechanism_adapter import scan_doctrine_mechanism
from system.lib.compliance.doctrine_reference_bundle_adapter import scan_doctrine_reference_bundle
from system.lib.compliance.doctrine_section_unit_adapter import scan_doctrine_section_unit
from system.lib.compliance.doctrine_subdomains_adapter import scan_doctrine_subdomains
from system.lib.compliance.doctrine_triple_adapter import scan_doctrine_triple
from system.lib.compliance.execution_map_adapter import scan_execution_map
from system.lib.compliance.extracted_pattern_adapter import (
    scan_extracted_pattern_route_readiness,
    scan_extracted_pattern_substrate_bindings,
)
from system.lib.compliance.frontend_component_index_adapter import scan_frontend_component_index
from system.lib.compliance.hidden_substrate_integration_manifest_adapter import (
    scan_hidden_substrate_integration_manifest,
)
from system.lib.compliance.host_skill_surface_adapter import scan_host_skill_surface
from system.lib.compliance.imagination_adapter import scan_imagination
from system.lib.compliance.idea_packet_adapter import scan_idea_packet
from system.lib.compliance.json_facets_adapter import scan_json_facets
from system.lib.compliance.kind_atlas_adapter import scan_kind_atlas
from system.lib.compliance.laboratory_adapter import scan_laboratory
from system.lib.compliance.lattice_event_adapter import scan_lattice_event
from system.lib.compliance.lattice_registry_adapter import scan_lattice_registry
from system.lib.compliance.launchable_operation_contract_adapter import (
    scan_launchable_operation_contract,
)
from system.lib.compliance.legacy_reference_snapshot_adapter import scan_legacy_reference_snapshot
from system.lib.compliance.lifecycle_surface_budget_adapter import scan_lifecycle_surface_budget
from system.lib.compliance.live_projection_salience_gate_adapter import (
    scan_live_projection_salience_gate,
)
from system.lib.compliance.microcosm_adapter import scan_microcosm
from system.lib.compliance.navigation_contract_adapter import scan_navigation_contract
from system.lib.compliance.navigation_mechanism_acceptance_adapter import (
    scan_navigation_mechanism_acceptance,
)
from system.lib.compliance.navigation_rosetta_grammar_adapter import scan_navigation_rosetta_grammar
from system.lib.compliance.paper_module_adapter import scan_paper_module
from system.lib.compliance.principle_projection_adapter import scan_principle_projection
from system.lib.compliance.prompt_ledger_adapter import scan_prompt_ledger
from system.lib.compliance.skill_registry_adapter import scan_skill_registry
from system.lib.compliance.standard_baseline_adapter import make_standard_baseline_scanner
from system.lib.compliance.standards_registry_adapter import scan_standards_registry
from system.lib.compliance.standard_type_plane_adapter import scan_standard_type_plane
from system.lib.compliance.system_atlas_adapter import scan_system_atlas
from system.lib.compliance.task_ledger_adapter import scan_task_ledger
from system.lib.compliance.transform_job_adapter import scan_transform_jobs
from system.lib.standards_inventory import enumerate_standard_ids


_STATIC_ADAPTERS: Mapping[str, Callable[[Path], dict]] = {
    "std_aiw_movement_v1": scan_aiw_movement,
    "std_annex_catalog": scan_annex_catalog,
    "std_annex_contents": scan_annex_contents,
    "std_annex_distillation": scan_annex_distillation,
    "std_annex_distillation_run_receipt": scan_annex_distillation_run_receipt,
    "std_annex_family": scan_annex_family,
    "std_annex_index": scan_annex_index,
    "std_annex_notes": scan_annex_notes,
    "std_annex_pending": scan_annex_pending,
    "std_annex_sync_report": scan_annex_sync_report,
    "std_agent_bootstrap": scan_agent_bootstrap,
    "std_agent_entrypoint_audit": scan_agent_entrypoint_audit,
    "std_agent_execution_trace": scan_agent_execution_trace,
    "std_agent_entry_surface": scan_agent_entry_surface,
    "std_agent_seed": scan_agent_seed,
    "std_agent_trace_lossless_clip": scan_agent_trace_lossless_clip,
    "std_apply": scan_apply,
    "std_approval_decision_event": scan_approval_decision_event,
    "std_approval_record": scan_approval_record,
    "std_architectural_projection": scan_architectural_projection,
    "std_artifact_ontology": scan_artifact_ontology,
    "std_axiom_candidate": scan_axiom_candidate,
    "std_autonomous_seed": scan_autonomous_seed,
    "std_autonomous_seed_prompt": scan_autonomous_seed_prompt,
    "std_autonomy_plan": scan_autonomy_plan,
    "std_autonomy_runtime": scan_autonomy_runtime,
    "std_authority_reconciled_status": scan_authority_reconciled_status,
    "std_bridge_campaign": scan_bridge_campaign,
    "std_bridge_failure_class": scan_bridge_failure_class,
    "std_bridge_info_request_v1": scan_bridge_info_request,
    "std_bridge_receipt": scan_bridge_receipt,
    "std_bridge_response_validation": scan_bridge_response_validation,
    "std_bridge_window_identity": scan_bridge_window_identity,
    "std_campaign_state": scan_campaign_state,
    "std_campaign_transition": scan_campaign_transition,
    "std_command_output_projection": scan_command_output_projection,
    "std_compliance_coverage": scan_compliance_coverage,
    "std_compliance_finding": scan_compliance_findings,
    "std_config_authority_registry": scan_config_authority_registry,
    "std_constitution_workspace": scan_constitution_workspace,
    "std_continuation_packet": scan_continuation_packet,
    "std_continuity_protocol": scan_continuity_protocol,
    "std_controller_heartbeat": scan_controller_heartbeat,
    "std_cycle_assimilation": scan_cycle_assimilation,
    "std_cycle_summary": scan_cycle_summary,
    "std_demo_take_package": scan_demo_take_package,
    "std_demo_take_scene_plan": scan_demo_take_scene_plan,
    "std_demo_take_story_package": scan_demo_take_story_package,
    "std_compute_provider": scan_compute_provider,
    "std_cognitive_operator": scan_cognitive_operator,
    "std_concept": scan_doctrine_concept,
    "std_derived_fact": scan_derived_fact,
    "std_documentation_meta": scan_documentation_meta,
    "std_doc_registry": scan_doc_registry,
    "std_doctrine_approved_overlay": scan_doctrine_approved_overlay,
    "std_doctrine_derivation": scan_doctrine_derivation,
    "std_mechanism": scan_doctrine_mechanism,
    "std_doctrine_reference_bundle": scan_doctrine_reference_bundle,
    "std_doctrine_section_unit": scan_doctrine_section_unit,
    "std_doctrine_subdomains": scan_doctrine_subdomains,
    "std_doctrine_triple": scan_doctrine_triple,
    "std_execution_map": scan_execution_map,
    "std_extracted_pattern_substrate_bindings": scan_extracted_pattern_substrate_bindings,
    "std_extracted_pattern_route_readiness": scan_extracted_pattern_route_readiness,
    "std_frontend_component_index": scan_frontend_component_index,
    "std_hidden_substrate_integration_manifest": scan_hidden_substrate_integration_manifest,
    "std_host_skill_surface": scan_host_skill_surface,
    "std_imagination": scan_imagination,
    "std_idea_packet": scan_idea_packet,
    "std_json_facets": scan_json_facets,
    "std_kind_atlas": scan_kind_atlas,
    "std_laboratory": scan_laboratory,
    "std_lattice_event": scan_lattice_event,
    "std_lattice_registry": scan_lattice_registry,
    "std_launchable_operation_contract": scan_launchable_operation_contract,
    "std_legacy_reference_snapshot": scan_legacy_reference_snapshot,
    "std_lifecycle_surface_budget": scan_lifecycle_surface_budget,
    "std_live_projection_salience_gate": scan_live_projection_salience_gate,
    "std_microcosm": scan_microcosm,
    "std_navigation_contract": scan_navigation_contract,
    "std_navigation_mechanism_acceptance": scan_navigation_mechanism_acceptance,
    "std_navigation_rosetta_grammar": scan_navigation_rosetta_grammar,
    "std_paper_module": scan_paper_module,
    "std_prompt_ledger": scan_prompt_ledger,
    "std_raw_seed_principles": scan_principle_projection,
    "std_skill": scan_skill_registry,
    "std_standards_registry": scan_standards_registry,
    "std_standard_type_plane": scan_standard_type_plane,
    "std_system_atlas": scan_system_atlas,
    "std_task_ledger": scan_task_ledger,
    "std_transform_job": scan_transform_jobs,
}

_PYTHON_COVERAGE_PATH = (
    "state/meta_missions/python_std_compliance_authoring/"
    "python_std_compliance_coverage.json"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _build_baseline_adapters() -> dict[str, Callable[[Path], dict]]:
    """
    [ACTION]
    - Teleology: Give every otherwise-uncovered standard a read-only baseline
      companion row so Atlas/navigation can route it without overclaiming full
      domain-scanner coverage.
    - Preconditions: The repo root resolves and standards inventory can be
      enumerated; inventory failures degrade to an empty baseline map.
    - Guarantee: Returns deterministic scanner closures for uncovered standards
      only, excluding domain adapters and the active std_python coverage lane.
    - Fails: None; inventory errors are contained as an empty mapping.
    """
    root = _repo_root()
    try:
        standard_ids = enumerate_standard_ids(root)
    except Exception:
        return {}
    excluded = {
        standard_id
        for standard_id in ("std_python",)
        if (root / _PYTHON_COVERAGE_PATH).exists()
    }
    return {
        standard_id: make_standard_baseline_scanner(standard_id)
        for standard_id in standard_ids
        if standard_id not in _STATIC_ADAPTERS
        and standard_id not in excluded
    }


class _LazyBaselineAdapters(dict[str, Callable[[Path], dict]]):
    """
    Load generated baseline companions only when a caller needs the full
    registry. Import-only diagnostics should not parse every standard file.
    """

    def __init__(self) -> None:
        super().__init__()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        super().update(_build_baseline_adapters())
        self._loaded = True

    def __contains__(self, key: object) -> bool:
        self._ensure_loaded()
        return super().__contains__(key)

    def __getitem__(self, key: str) -> Callable[[Path], dict]:
        self._ensure_loaded()
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        self._ensure_loaded()
        return super().__iter__()

    def __len__(self) -> int:
        self._ensure_loaded()
        return super().__len__()

    def get(self, key: str, default: object = None) -> object:
        self._ensure_loaded()
        return super().get(key, default)

    def items(self):
        self._ensure_loaded()
        return super().items()

    def keys(self):
        self._ensure_loaded()
        return super().keys()

    def values(self):
        self._ensure_loaded()
        return super().values()

    def copy(self) -> dict[str, Callable[[Path], dict]]:
        self._ensure_loaded()
        return dict(self)


class _LazyBaselineIdSet:
    def __init__(self, baseline_adapters: _LazyBaselineAdapters) -> None:
        self._baseline_adapters = baseline_adapters
        self._ids: set[str] = set()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._ids.update(self._baseline_adapters.keys())
        self._loaded = True

    def __contains__(self, item: object) -> bool:
        self._ensure_loaded()
        return item in self._ids

    def __iter__(self) -> Iterator[str]:
        self._ensure_loaded()
        return iter(self._ids)

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._ids)

    def __repr__(self) -> str:
        self._ensure_loaded()
        return repr(self._ids)

    def copy(self) -> set[str]:
        self._ensure_loaded()
        return set(self._ids)

    def issubset(self, other: Iterable[object]) -> bool:
        self._ensure_loaded()
        return self._ids.issubset(other)


class _LazyComplianceAdapters(dict[str, Callable[[Path], dict]]):
    def __init__(
        self,
        static_adapters: Mapping[str, Callable[[Path], dict]],
        baseline_adapters: _LazyBaselineAdapters,
    ) -> None:
        super().__init__(static_adapters)
        self._baseline_adapters = baseline_adapters
        self._baseline_loaded = False

    def _ensure_baseline_loaded(self) -> None:
        if self._baseline_loaded:
            return
        self._baseline_adapters._ensure_loaded()
        super().update(self._baseline_adapters)
        self._baseline_loaded = True

    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        self._ensure_baseline_loaded()
        return super().__contains__(key)

    def __getitem__(self, key: str) -> Callable[[Path], dict]:
        if super().__contains__(key):
            return super().__getitem__(key)
        self._ensure_baseline_loaded()
        return super().__getitem__(key)

    def __iter__(self) -> Iterator[str]:
        self._ensure_baseline_loaded()
        return super().__iter__()

    def __len__(self) -> int:
        self._ensure_baseline_loaded()
        return super().__len__()

    def get(self, key: str, default: object = None) -> object:
        if super().__contains__(key):
            return super().get(key, default)
        self._ensure_baseline_loaded()
        return super().get(key, default)

    def items(self):
        self._ensure_baseline_loaded()
        return super().items()

    def keys(self):
        self._ensure_baseline_loaded()
        return super().keys()

    def values(self):
        self._ensure_baseline_loaded()
        return super().values()

    def copy(self) -> dict[str, Callable[[Path], dict]]:
        self._ensure_baseline_loaded()
        return dict(self)


_BASELINE_ADAPTERS = _LazyBaselineAdapters()
BASELINE_ADAPTERS: Mapping[str, Callable[[Path], dict]] = _BASELINE_ADAPTERS
BASELINE_ADAPTER_STANDARD_IDS: Iterable[str] = _LazyBaselineIdSet(_BASELINE_ADAPTERS)
DOMAIN_ADAPTER_STANDARD_IDS: frozenset[str] = frozenset(_STATIC_ADAPTERS.keys())

ADAPTERS: Mapping[str, Callable[[Path], dict]] = _LazyComplianceAdapters(_STATIC_ADAPTERS, _BASELINE_ADAPTERS)


def scan_all(repo_root: Path) -> list[dict]:
    """
    [ACTION]
    - Teleology: Run every registered adapter and return a list of per-standard
      coverage payloads suitable for build_compliance_ledger to merge.
    - Preconditions: `repo_root` points at an ai_workflow checkout with readable
      standard and substrate files for any adapter that needs them.
    - Guarantee: Returns one payload per registered adapter and converts adapter
      exceptions into scan_error payloads instead of aborting the ledger build.
    - Fails: None; individual adapter failures are represented in returned rows.
    """
    payloads: list[dict] = []
    for standard_id, scanner in ADAPTERS.items():
        try:
            payload = scanner(repo_root)
        except Exception as exc:
            payload = {
                "standard_id": standard_id,
                "scan_error": str(exc),
                "scan_error_kind": exc.__class__.__name__,
                "applicable_artifact_count": None,
                "checked_artifact_count": 0,
                "compliant_artifact_count": 0,
                "compliance_rate": None,
                "top_failure_kinds": [],
                "findings": [],
            }
        payloads.append(payload)
    return payloads


__all__ = [
    "ADAPTERS",
    "BASELINE_ADAPTERS",
    "BASELINE_ADAPTER_STANDARD_IDS",
    "DOMAIN_ADAPTER_STANDARD_IDS",
    "scan_all",
]
