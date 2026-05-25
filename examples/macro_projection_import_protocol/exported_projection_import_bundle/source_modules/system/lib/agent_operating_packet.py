"""Generated Type A operating packet over principles and axiom candidates.

The packet is a compact judgment frame, not a new source of doctrine. Source
authority remains in raw_seed_principles.json and system_axiom_candidates.json;
this module selects, compresses, measures, and routes those rows for agent entry.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.principle_projection import resolve_principle_capsule
from system.lib.standard_option_surface import candidate_to_runtime_packet


SCHEMA_VERSION = "agent_operating_packet_v0"
STRIP_SCHEMA_VERSION = "agent_operating_packet_strip_v0"

RAW_SEED_PRINCIPLES_REL = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/"
    "raw_seed/raw_seed_principles.json"
)
SYSTEM_AXIOM_CANDIDATES_REL = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/"
    "raw_seed/system_axiom_candidates.json"
)
STD_RAW_SEED_PRINCIPLES_REL = "codex/standards/principles/std_raw_seed_principles.json"
STD_SYSTEM_AXIOM_CANDIDATE_REL = "codex/standards/principles/std_system_axiom_candidate.json"
STD_AGENT_ENTRY_SURFACE_REL = "codex/standards/std_agent_entry_surface.json"
PRINCIPLE_SCOPE_PAPER_REL = "codex/doctrine/paper_modules/principle_scope_ontology.md"
DEFAULT_TARGET_REL = "codex/doctrine/agent_operating_packet.json"

GLOBAL_CONSTITUTIONAL_SCOPE_ID = "global.constitutional_doctrine"
DEFAULT_MAX_GLOBAL_PRINCIPLES = 7
DEFAULT_MAX_FREQUENT_PRINCIPLES = 12
DEFAULT_MAX_AGENT_PRINCIPLES = 16
DEFAULT_MAX_AXIOM_GLANCE_ROWS = 14
DEFAULT_AGENT_PRINCIPLE_SCOPE_IDS = (
    "global.integration_stewardship",
    "global.agent_action_discipline",
    "global.operational_control_plane",
    "global.agent_cognitive_architecture",
    "global.agent_pass_success",
    "global.workitem_capture_assimilation_epistemics",
    "global.multi_agent_coordination",
    "global.generated_projection_governance",
    "global.self_diagnostic_routing",
    "global.recursive_governance",
    "global.workspace_convergence",
    "global.transaction_lifecycle",
    "global.phase_subphase_supervision",
    "global.agent_evidence_stability",
)

AGENT_PRINCIPLE_LENS_BY_SITUATION: dict[str, tuple[str, ...]] = {
    "agent_principle_authoring": ("pri_144", "pri_137", "pri_143", "pri_136", "pri_140", "pri_142", "pri_153"),
    "navigation_control_boundary": ("pri_136", "pri_142", "pri_143", "pri_144"),
    "projection_closure_audit": ("pri_142", "pri_143", "pri_144", "pri_139"),
    "type_b_to_type_a_continuation_handoff": ("pri_138", "pri_140", "pri_136", "pri_139"),
    "imperative_authoring": ("pri_134", "pri_136", "pri_139", "pri_140"),
    "system_comprehension_authoring": ("pri_134", "pri_136", "pri_142", "pri_139"),
    "task_ledger_workitem": ("pri_137", "pri_140", "pri_146", "pri_139"),
    "publication_lane_push_recovery": ("pri_141", "pri_145", "pri_146", "pri_153"),
    "dissemination_agent_entry": ("pri_142", "pri_153", "pri_139"),
    "dissemination_authoring": ("pri_142", "pri_153", "pri_139", "pri_146"),
    "config_authority_plane": ("pri_142", "pri_143", "pri_136"),
    "type_a_autonomous_seed_framework": ("pri_134", "pri_137", "pri_140", "pri_143"),
    "cognitive_operator_discovery": ("pri_138", "pri_144", "pri_143"),
}

AGENT_PRINCIPLE_QUERY_TRIGGERS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("agent principle", "type a principle", "type a principles", "mint", "author", "proposal", "promote"), ("pri_144", "pri_136", "pri_140")),
    (("head", "current", "proof", "evidence", "receipt", "commit", "stale", "fingerprint"), ("pri_153", "pri_146")),
    (("dirty", "staged", "worktree", "index", "concurrent"), ("pri_145", "pri_141")),
    (("type b", "operator", "hud", "handoff", "chatgpt"), ("pri_138",)),
    (("greenfield", "invent", "existing", "sibling", "integrate"), ("pri_134", "pri_136")),
    (("generated", "projection", "freshness", "builder", "sidecar"), ("pri_142",)),
    (("failure", "diagnostic", "classify", "symptom"), ("pri_143",)),
    (("propagate", "learn", "principle", "assimilate"), ("pri_144",)),
    (("deliverable", "partial", "residual", "remaining work", "big instruction", "large instruction"), ("pri_139", "pri_137", "pri_140")),
    (("workitem", "task ledger", "todo", "capture"), ("pri_137", "pri_140")),
    (("phase", "subphase", "supervision", "wave"), ("pri_147",)),
)

PARTIAL_INSTRUCTION_RESIDUAL_TERMS: tuple[str, ...] = (
    "large instruction",
    "big instruction",
    "deliverable",
    "deliverables",
    "partial",
    "only part",
    "rest of",
    "everything else",
    "residual",
    "follow-up",
    "followup",
    "workitem",
    "work item",
    "task ledger",
    "cap",
    "caps",
    "runtime mission",
    "mission hook",
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _string(item)
        if text and text not in out:
            out.append(text)
    return out


def _truncate(text: str, *, max_chars: int) -> str:
    clean = " ".join(_string(text).split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max(0, max_chars - 3)].rstrip() + "..."


def _first_sentence(text: str, *, max_chars: int) -> str:
    clean = " ".join(_string(text).split())
    if not clean:
        return ""
    match = re.search(r"(?<=[.!?])\s+", clean)
    if match:
        clean = clean[: match.start()].strip()
    return _truncate(clean, max_chars=max_chars)


def _partial_instruction_residual_matches(task_text: str) -> list[str]:
    task_lower = _string(task_text).casefold()
    if not task_lower:
        return []
    matches = [term for term in PARTIAL_INSTRUCTION_RESIDUAL_TERMS if term in task_lower]
    if "deliverable_type=" in task_lower and "deliverable_type" not in matches:
        matches.append("deliverable_type")
    if len(matches) >= 2:
        return matches[:8]
    return []


def _json_bytes(value: Any, *, pretty: bool = False) -> int:
    kwargs: dict[str, Any] = {"ensure_ascii": False}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return len(json.dumps(value, **kwargs).encode("utf-8"))


def _scope_profile(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("scope_profile")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _principle_scope_id(row: Mapping[str, Any]) -> str:
    return _string(_scope_profile(row).get("scope_id"))


def _principle_domain(row: Mapping[str, Any]) -> str:
    return _string(_scope_profile(row).get("domain"))


def _principle_sort_key(row: Mapping[str, Any]) -> tuple[int, str]:
    kind_order = {"meta": 0, "operational": 1, "substance": 2, "architectural": 3, "strategic": 4}
    return (kind_order.get(_string(row.get("kind")), 99), _string(row.get("id")))


def _edge_refs(row: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for edge in row.get("edges") or []:
        if not isinstance(edge, Mapping):
            continue
        target = _string(edge.get("target"))
        if target and target not in refs:
            refs.append(target)
    return refs


def _refs_by_prefix(values: list[str], prefix: str) -> list[str]:
    return [value for value in values if value.startswith(prefix)]


def _agent_principle_scope_ids(config: Mapping[str, Any] | None) -> list[str]:
    configured = _string_list((config or {}).get("agent_principle_scope_ids"))
    return configured or list(DEFAULT_AGENT_PRINCIPLE_SCOPE_IDS)


def _is_agent_principle(row: Mapping[str, Any], scope_ids: set[str]) -> bool:
    return _string(row.get("status")) == "active" and _principle_scope_id(row) in scope_ids


def _classify_principle(row: Mapping[str, Any]) -> tuple[str, str]:
    if _string(row.get("status")) != "active":
        return "inactive_or_seed", "Only active principle rows enter runtime classification."
    scope_id = _principle_scope_id(row)
    if scope_id == GLOBAL_CONSTITUTIONAL_SCOPE_ID:
        return "global_always", "Active global.constitutional_doctrine principle: safe Type A runtime baseline."
    if _principle_domain(row) == "global":
        return "global_frequent", "Active global-domain principle: frequent across tasks, but routed by situation."
    return "situational", "Active scoped principle: open through context-pack, option-surface, or paper-module route when relevant."


def _principle_capsule_row(
    repo_root: Path,
    principle: Mapping[str, Any],
    *,
    related_axioms_by_principle: Mapping[str, list[str]],
    relation_role: str = "agent_operating_packet.global_principles",
    runtime_doctrine_type: str = "principle",
) -> dict[str, Any]:
    principle_id = _string(principle.get("id"))
    scope_profile = _scope_profile(principle)
    statement = _string(principle.get("statement"))
    classifier, reason = _classify_principle(principle)
    capsule = resolve_principle_capsule(
        repo_root,
        principle_id,
        requested_band="statement",
        relation_role=relation_role,
        consumer_context={"surface": "agent_operating_packet"},
    )
    edge_refs = _edge_refs(principle)
    title = _string(principle.get("title") or principle_id)
    return {
        "source_kind": "principle",
        "source_id": principle_id,
        "runtime_doctrine_type": runtime_doctrine_type,
        "title": title,
        "authority_posture": "active_principle" if _string(principle.get("status")) == "active" else "non_active_principle",
        "capsule_class": classifier,
        "runtime_priority": "always" if classifier == "global_always" else "frequent" if classifier == "global_frequent" else "situational",
        "selection_reason": reason,
        "scope": _string(principle.get("scope")),
        "scope_id": _string(scope_profile.get("scope_id")),
        "domain": _string(scope_profile.get("domain")),
        "subdomain": _string(scope_profile.get("subdomain")),
        "paper_module": _string(scope_profile.get("paper_module")),
        "principle_kind": _string(principle.get("kind")),
        "tiny": title,
        "flag": _first_sentence(statement, max_chars=180),
        "statement_band": _truncate(_string(capsule.get("projection_text") or statement), max_chars=280),
        "related_principles": _refs_by_prefix(edge_refs, "pri_")[:8],
        "related_concepts": _refs_by_prefix(edge_refs, "con_")[:8],
        "related_mechanisms": _refs_by_prefix(edge_refs, "mech_")[:8],
        "related_axiom_candidates": list(related_axioms_by_principle.get(principle_id, []))[:8],
        "teleology_refs": _string_list(principle.get("teleology_refs")),
        "route": {
            "card": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
            "tape": f"./repo-python kernel.py --option-surface principles --band tape --ids {principle_id}",
            "paper_module": (
                f"./repo-python kernel.py --paper-module {scope_profile.get('paper_module')}"
                if scope_profile.get("paper_module")
                else "./repo-python kernel.py --option-surface principles --band cluster_flag"
            ),
        },
        "projection_capsule_receipt": {
            "schema_version": _string(capsule.get("schema_version")),
            "resolved": bool(capsule.get("resolved")),
            "char_estimate": capsule.get("char_estimate"),
            "char_budget_soft": capsule.get("char_budget_soft"),
            "over_char_budget": bool(capsule.get("over_char_budget")),
            "warnings": list(capsule.get("warnings") or []),
        },
        "omission_receipt": {
            "omitted": ["full tests", "full evidence", "full edge neighborhood", "raw-seed paragraph bodies"],
            "reason": "Agent operating packet carries only entry-grade doctrine; source authority and curation evidence remain behind card/tape routes.",
        },
    }


def _principle_index_row(row: Mapping[str, Any], *, agent_scope_ids: set[str] | None = None) -> dict[str, Any]:
    classifier, reason = _classify_principle(row)
    principle_id = _string(row.get("id"))
    scope_profile = _scope_profile(row)
    runtime_doctrine_type = "agent_principle" if _is_agent_principle(row, agent_scope_ids or set()) else "principle"
    return {
        "source_id": principle_id,
        "title": _string(row.get("title") or principle_id),
        "status": _string(row.get("status")),
        "runtime_doctrine_type": runtime_doctrine_type,
        "capsule_class": classifier,
        "runtime_priority": "always" if classifier == "global_always" else "frequent" if classifier == "global_frequent" else "situational",
        "selection_reason": reason,
        "scope_id": _string(scope_profile.get("scope_id")),
        "domain": _string(scope_profile.get("domain")),
        "paper_module": _string(scope_profile.get("paper_module")),
        "route": f"./repo-python kernel.py --option-surface principles --band card --ids {principle_id}",
    }


def _axiom_glance_row(axiom: Mapping[str, Any]) -> dict[str, Any]:
    ax = dict(axiom)
    axiom_id = _string(ax.get("id"))
    bands = ax.get("compression_expansion_bands") if isinstance(ax.get("compression_expansion_bands"), Mapping) else {}
    runtime_packet = candidate_to_runtime_packet(ax)
    activation = ax.get("activation_packet_behavior") if isinstance(ax.get("activation_packet_behavior"), Mapping) else {}
    return {
        "source_kind": "axiom_candidate",
        "source_id": axiom_id,
        "title": _string(ax.get("title") or axiom_id),
        "slug": _string(ax.get("slug") or axiom_id),
        "authority_posture": _string(ax.get("authority_posture") or "candidate_not_active_doctrine"),
        "runtime_priority": "candidate_pressure",
        "use_mode": _string(runtime_packet.get("use_mode")),
        "tiny": _string(bands.get("tiny")),
        "flag": _string(bands.get("flag") or runtime_packet.get("flag_band")),
        "formal_clause": _string(ax.get("formal_clause")),
        "surface_when": _string(activation.get("surface_when")),
        "related_principles": _string_list(ax.get("related_principles"))[:12],
        "governed_planes": _string_list(ax.get("governed_planes"))[:12],
        "eligible_for_runtime_pressure": bool(runtime_packet.get("eligible")),
        "eligibility_reasons": list(runtime_packet.get("eligibility_reasons") or []),
        "eligibility_blockers": list(runtime_packet.get("eligibility_blockers") or []),
        "non_law_warning": _string(runtime_packet.get("non_law_warning")),
        "route": {
            "card": f"./repo-python kernel.py --option-surface axiom_candidates --band card --ids {axiom_id}",
            "tape": f"./repo-python kernel.py --option-surface axiom_candidates --band tape --ids {axiom_id}",
        },
    }


def _agent_lens_row(row: Mapping[str, Any], *, why_selected: str) -> dict[str, Any]:
    source_id = _string(row.get("source_id"))
    return {
        "id": source_id,
        "title": _string(row.get("title")),
        "scope_id": _string(row.get("scope_id")),
        "flag": _string(row.get("flag")),
        "why_selected": why_selected,
        "route": (row.get("route") or {}).get("card")
        if isinstance(row.get("route"), Mapping)
        else f"./repo-python kernel.py --option-surface principles --band card --ids {source_id}",
    }


def build_agent_principle_lens(
    packet: Mapping[str, Any] | None,
    *,
    task_text: str | None = None,
    recognized_situation: str | None = None,
    selected_lane_id: str | None = None,
    max_rows: int = 5,
) -> dict[str, Any]:
    """Return a compact task-conditioned lens over active agent principles."""
    raw_agent_packet = packet.get("agent_principles") if isinstance(packet, Mapping) else {}
    agent_packet = raw_agent_packet if isinstance(raw_agent_packet, Mapping) else {}
    rows = [
        row
        for row in (agent_packet.get("rows") or [])
        if isinstance(row, Mapping) and row.get("source_id")
    ]
    row_by_id = {_string(row.get("source_id")): row for row in rows}
    selected: list[tuple[str, str]] = []

    def add(source_id: str, reason: str) -> None:
        if source_id in row_by_id and all(existing_id != source_id for existing_id, _ in selected):
            selected.append((source_id, reason))

    situation = _string(recognized_situation)
    lane = _string(selected_lane_id)
    situation_ids = AGENT_PRINCIPLE_LENS_BY_SITUATION.get(situation) or AGENT_PRINCIPLE_LENS_BY_SITUATION.get(lane) or ()
    for source_id in situation_ids:
        add(source_id, f"recognized_situation:{situation or lane}")

    task_lower = _string(task_text).casefold()
    for terms, source_ids in AGENT_PRINCIPLE_QUERY_TRIGGERS:
        matched_terms = [term for term in terms if term in task_lower]
        if not matched_terms:
            continue
        reason = "task_terms:" + ",".join(matched_terms[:3])
        for source_id in source_ids:
            add(source_id, reason)

    if not selected and rows:
        for fallback_id in ("pri_136", "pri_139", "pri_142"):
            add(fallback_id, "fallback_agent_entry_lens")

    selected = selected[: max(1, max_rows)]
    selected_ids = [source_id for source_id, _ in selected]
    payload = {
        "kind": "agent_principle_lens",
        "schema_version": "agent_principle_lens_v0",
        "artifact_role": "task_conditioned_agent_principle_lens",
        "runtime_doctrine_type": "agent_principle",
        "authority_posture": "generated_projection_not_source_authority",
        "status": "matched" if selected_ids else "available_unmatched",
        "recognized_situation": situation,
        "selected_lane_id": lane,
        "selected_ids": selected_ids,
        "rows": [
            _agent_lens_row(row_by_id[source_id], why_selected=reason)
            for source_id, reason in selected
            if source_id in row_by_id
        ],
        "invocation": {
            "all_agent_principles": "./repo-python kernel.py --agent-principles --band card",
            "authoring_lane": "./repo-python kernel.py --agent-principle-authoring \"<lesson>\" --context-budget 12000",
            "agent_operating_packet": "./repo-python kernel.py --agent-operating-packet --band card",
            "selected_principle_cards": (
                "./repo-python kernel.py --option-surface principles --band card --ids "
                + ",".join(selected_ids)
                if selected_ids
                else "./repo-python kernel.py --option-surface principles --band cluster_flag"
            ),
            "failure_mode_cap_search": (
                "./repo-python tools/meta/factory/task_ledger_apply.py search "
                "--query agent_principle --tag agent_principle_candidate --tag failure_mode --limit 20"
            ),
        },
        "capture_reflex": {
            "when": (
                "If reflection finds a reusable Type A failure class but the local case is "
                "not enough for direct principle mutation, capture a rich failure-mode CAP."
            ),
            "capture_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                "--created-by <agent_id> --candidate-work-item-type agent_principle_failure_mode "
                "--tag agent_principle_candidate --tag failure_mode --payload-json '<json>' --rebuild"
            ),
            "minimum_payload_fields": [
                "local_case",
                "failure_mode",
                "triggering_context",
                "suspected_agent_principle_pressure",
                "narrower_owner_checked",
                "sibling_cases_or_absence",
                "overgeneralization_guard",
                "desired_diagnostic",
            ],
            "diagnosis_rule": "Aggregate multiple rich failure-mode CAPs before minting or activating a new agent principle.",
        },
        "unifies_with": [
            "codex/doctrine/command_cards/agent_movement.json::agent_principles_lens",
            "codex/doctrine/skills/doctrine/agent_principle_cap_assimilation.md",
            "system/lib/navigation_metabolism_ledger.py::process_audit behavior_debt",
            "system/lib/navigation_mechanism_factory.py::navigation mechanism acceptance",
        ],
        "omission_receipt": {
            "omitted": ["full principle tests", "full evidence refs", "full edge neighborhoods"],
            "reason": "Entry carries only the behavioral lens; full source authority remains in principle cards/tape and raw_seed_principles.json.",
        },
    }
    residual_matches = _partial_instruction_residual_matches(task_text or "")
    if residual_matches:
        payload["residual_deliverable_capture"] = {
            "status": "triggered",
            "match_terms": residual_matches,
            "rule": (
                "If the operator supplied a broad instruction and this runtime executes only "
                "one slice, every remaining durable deliverable must land in a matching "
                "cap_*/WorkItem, existing capture, blocker/retirement, or explicit no-op "
                "before final prose."
            ),
            "legal_closeout_states": [
                "executed_now_and_validated",
                "quick_captured_as_cap_or_workitem",
                "linked_to_existing_cap_or_workitem",
                "blocked_or_retired_with_reason",
                "explicit_no_residual_or_no_op_verdict",
            ],
            "capture_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                "--created-by <agent_id> --title '<title>' --statement '<statement>' "
                "--source-ref '<prompt/session/workitem ref>' --tag residual_deliverable "
                "--rebuild"
            ),
            "owner_selection_rule": (
                "Prefer the active mission/selected WorkItem; otherwise browse Task Ledger "
                "cluster/card surfaces before creating a new cap."
            ),
            "owning_standard": (
                "codex/standards/std_task_ledger.json::metacontrol_contract."
                "provider_native_task_affordance_boundary.partial_instruction_residual_rule"
            ),
            "no_bloat_policy": (
                "Entry carries this compact trigger only; full residual classification stays "
                "in Task Ledger organizer/report surfaces."
            ),
        }
    return payload


def build_agent_principle_authoring_packet(
    packet: Mapping[str, Any] | None,
    *,
    task_text: str | None = None,
) -> dict[str, Any]:
    """Return the governed lane for proposing or minting Type A agent principles."""
    lens = build_agent_principle_lens(
        packet,
        task_text=task_text,
        recognized_situation="agent_principle_authoring",
        selected_lane_id="agent_principle_authoring",
        max_rows=7,
    )
    return {
        "kind": "agent_principle_authoring_packet",
        "schema_version": "agent_principle_authoring_packet_v0",
        "surface_role": "CONTROL_ENTRY",
        "first_contact_allowed": False,
        "artifact_role": "governed_agent_principle_authoring_lane",
        "runtime_doctrine_type": "agent_principle",
        "authority_posture": "standard_guided_control_packet_not_source_authority",
        "task": _string(task_text),
        "agent_principle_lens": lens,
        "governing_contract": {
            "standard": (
                "codex/standards/principles/std_raw_seed_principles.json"
                "::agent_principle_authoring_contract"
            ),
            "source_authority": RAW_SEED_PRINCIPLES_REL,
            "curation_skill": "codex/doctrine/skills/doctrine/principles_curation.md",
            "cap_assimilation_skill": "codex/doctrine/skills/doctrine/agent_principle_cap_assimilation.md",
            "propagation_skill": "codex/doctrine/skills/doctrine/local_to_general_propagation.md",
            "failure_packet": "codex/doctrine/mechanisms/mech_034_failure_class_propagation_packet.json",
        },
        "cap_first_assimilation": {
            "rule": (
                "When a Type A reflection finds a principle-shaped failure but evidence is only one "
                "local case, capture a rich failure-mode CAP instead of minting active doctrine."
            ),
            "candidate_work_item_type": "agent_principle_failure_mode",
            "tags": ["agent_principle_candidate", "failure_mode"],
            "capture_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                "--created-by <agent_id> --candidate-work-item-type agent_principle_failure_mode "
                "--tag agent_principle_candidate --tag failure_mode --payload-json '<json>' --rebuild"
            ),
            "aggregate_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py search "
                "--query agent_principle --tag agent_principle_candidate --tag failure_mode --limit 20"
            ),
            "promotion_rule": (
                "Diagnose across repeated CAPs; promote only if the aggregate shows a cross-lane "
                "Type A behavior invariant that a narrower skill/standard/route patch cannot absorb."
            ),
        },
        "decision_ladder": [
            {
                "step": "scan_existing",
                "rule": "Open the active agent-principle lens and candidate neighbor cards before drafting anything new.",
                "command": "./repo-python kernel.py --agent-principles --band card",
            },
            {
                "step": "patch_narrower_owner_first",
                "rule": "If the lesson is procedure, routing, validation, command memory, or a one-surface behavior, patch the owning skill, standard, command card, test, or WorkItem instead of minting pri_*.",
            },
            {
                "step": "packetize_failure_shaped_lessons",
                "rule": "If the lesson came from a local failure, repeated workaround, route miss, or agent confusion, packetize it through mech_034 before promotion.",
                "command": "./repo-python kernel.py --option-surface mechanisms --band card --ids mech_034",
            },
            {
                "step": "refine_before_new_row",
                "rule": "If an active pri_* already carries the same force, refine or edge that row instead of creating a sibling.",
                "command": "./repo-python kernel.py --option-surface principles --band cluster_flag",
            },
            {
                "step": "mint_only_if_cross_cutting_type_a_behavior",
                "rule": "A new agent principle is justified only when the behavior governs Type A substrate work across multiple lanes and has evidence, tests, failure modes, edges, and a change condition.",
            },
        ],
        "agent_principle_spec_contract": {
            "row_type": "ordinary_principle_row_projected_as_agent_principle",
            "required_fields": [
                "slug",
                "title",
                "statement",
                "kind",
                "scope",
                "status",
                "provenance",
                "evidence",
                "tests",
                "edges",
                "failure_modes",
                "decision_examples",
                "epistemic_posture",
                "scope_profile",
            ],
            "scope_profile_rule": (
                "scope_profile.scope_id must be one of the configured agent_principle_scope_ids "
                "when the row is intended to project through --agent-principles."
            ),
            "status_rule": (
                "Use draft when evidence is local or contested; active is allowed only with explicit operator "
                "authorization or strong cross-surface evidence plus validation."
            ),
            "evidence_rule": (
                "Current-turn operator declarations may justify a governed draft/active row, but durable operator "
                "voice still routes through raw-seed lanes when the quote itself must become source authority."
            ),
        },
        "commands": {
            "entry": "./repo-python kernel.py --entry \"<task>\" --context-budget 12000",
            "authoring_packet": "./repo-python kernel.py --agent-principle-authoring \"<lesson>\" --context-budget 12000",
            "all_agent_principles": "./repo-python kernel.py --agent-principles --band card",
            "principle_clusters": "./repo-python kernel.py --option-surface principles --band cluster_flag",
            "curation_skill": "./repo-python kernel.py --option-surface skills --band card --ids principles_curation",
            "local_to_general_skill": "./repo-python kernel.py --option-surface skills --band card --ids local_to_general_propagation",
            "hand_mint_dry_run": "./repo-python tools/meta/factory/raw_seed_apply_loop.py hand-mint-principle --family 09 --spec <principle_spec.json>",
            "hand_mint_commit": "./repo-python tools/meta/factory/raw_seed_apply_loop.py hand-mint-principle --family 09 --spec <principle_spec.json> --commit --rationale \"<operator/substrate reason>\"",
            "refresh_operating_packet": "./repo-python tools/meta/factory/build_agent_bootstrap_projection.py --source-event agent_principle_authoring",
            "check_bootstrap_projection": "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py",
        },
        "validation_contract": [
            "new/refined principle card resolves through ./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
            "--agent-principles --band card includes the row only when status active and scope_profile.scope_id is configured as an agent-principle scope",
            "--entry for the triggering lesson emits an agent_principle_lens and the authoring drilldown",
            "raw_seed_apply_loop hand-mint dry-run passes before any committed source-authority mutation",
            "bootstrap projection check passes after refreshing generated entry surfaces",
        ],
        "do_not": [
            "do not hand-edit raw_seed.md",
            "do not create a parallel Type A principle file or schema",
            "do not promote a single frustrating session into active doctrine without sibling evidence or an overgeneralization guard",
            "do not inject full principle bodies into AGENTS.override.md, AGENTS.md, CODEX.md, or CLAUDE.md",
        ],
        "omission_receipt": {
            "omitted": ["full principle corpus", "raw source rows", "draft spec generation"],
            "reason": "This packet routes the authoring lane; source mutation remains in raw_seed_apply_loop/principles_curation and source authority remains in raw_seed_principles.json.",
        },
    }


def _classification_summary(principles: list[Mapping[str, Any]]) -> dict[str, Any]:
    class_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    domain_counts: Counter[str] = Counter()
    for row in principles:
        classifier, _reason = _classify_principle(row)
        class_counts[classifier] += 1
        scope_counts[_principle_scope_id(row) or "missing"] += 1
        domain_counts[_principle_domain(row) or "missing"] += 1
    return {
        "principle_count": len(principles),
        "class_counts": dict(sorted(class_counts.items())),
        "scope_id_counts": dict(sorted(scope_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
    }


def _metrics(packet: Mapping[str, Any]) -> dict[str, Any]:
    global_capsule = packet.get("global_runtime_capsule") if isinstance(packet.get("global_runtime_capsule"), Mapping) else {}
    agent_principles = packet.get("agent_principles") if isinstance(packet.get("agent_principles"), Mapping) else {}
    strip = build_agent_operating_packet_strip(packet)
    return {
        "metric": "utf8_json_bytes",
        "compact_full_packet_bytes": _json_bytes(packet, pretty=False),
        "pretty_full_packet_bytes": _json_bytes(packet, pretty=True),
        "global_runtime_capsule_bytes": _json_bytes(global_capsule, pretty=False),
        "entry_strip_bytes": _json_bytes(strip, pretty=False),
        "global_principle_count": len(global_capsule.get("principles") or []) if isinstance(global_capsule, Mapping) else 0,
        "agent_principle_count": len(agent_principles.get("rows") or []) if isinstance(agent_principles, Mapping) else 0,
        "frequent_principle_count": len(packet.get("frequent_principles") or []),
        "axiom_candidate_glance_count": len(((packet.get("candidate_axiom_pressure") or {}).get("rows") or [])) if isinstance(packet.get("candidate_axiom_pressure"), Mapping) else 0,
    }


def _finalize_metrics(packet: dict[str, Any]) -> dict[str, Any]:
    for _ in range(4):
        next_metrics = _metrics(packet)
        if packet.get("budget_metrics") == next_metrics:
            break
        packet["budget_metrics"] = next_metrics
    return packet


def build_agent_operating_packet(
    repo_root: Path,
    *,
    config: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the generated operating packet from existing doctrine sources."""
    cfg = dict(config or {})
    principles_rel = _string(cfg.get("principles_source")) or RAW_SEED_PRINCIPLES_REL
    axioms_rel = _string(cfg.get("axiom_candidates_source")) or SYSTEM_AXIOM_CANDIDATES_REL
    max_global = int(cfg.get("max_global_principles") or DEFAULT_MAX_GLOBAL_PRINCIPLES)
    max_frequent = int(cfg.get("max_frequent_principles") or DEFAULT_MAX_FREQUENT_PRINCIPLES)
    max_agent = int(cfg.get("max_agent_principles") or DEFAULT_MAX_AGENT_PRINCIPLES)
    max_axioms = int(cfg.get("max_axiom_glance_rows") or DEFAULT_MAX_AXIOM_GLANCE_ROWS)
    agent_scope_ids = _agent_principle_scope_ids(cfg)
    agent_scope_id_set = set(agent_scope_ids)
    agent_scope_order = {scope_id: index for index, scope_id in enumerate(agent_scope_ids)}

    principles_payload = _load_json(repo_root / principles_rel)
    axiom_payload = _load_json(repo_root / axioms_rel)
    principles = [row for row in (principles_payload.get("principles") or []) if isinstance(row, Mapping)]
    axioms = [row for row in (axiom_payload.get("axiom_candidates") or []) if isinstance(row, Mapping)]

    related_axioms_by_principle: dict[str, list[str]] = {}
    for axiom in axioms:
        axiom_id = _string(axiom.get("id"))
        for principle_id in _string_list(axiom.get("related_principles")):
            related_axioms_by_principle.setdefault(principle_id, []).append(axiom_id)

    active = [row for row in principles if _string(row.get("status")) == "active"]
    global_rows = sorted(
        [row for row in active if _principle_scope_id(row) == GLOBAL_CONSTITUTIONAL_SCOPE_ID],
        key=_principle_sort_key,
    )[:max_global]
    frequent_rows = sorted(
        [row for row in active if _principle_domain(row) == "global" and _principle_scope_id(row) != GLOBAL_CONSTITUTIONAL_SCOPE_ID],
        key=lambda row: (_string(_scope_profile(row).get("scope_id")), _principle_sort_key(row)),
    )[:max_frequent]
    agent_rows = sorted(
        [row for row in active if _is_agent_principle(row, agent_scope_id_set)],
        key=lambda row: (
            agent_scope_order.get(_principle_scope_id(row), 999),
            _principle_sort_key(row),
        ),
    )[:max_agent]
    axiom_rows = sorted(axioms, key=lambda row: _string(row.get("id")))[:max_axioms]

    packet: dict[str, Any] = {
        "kind": "agent_operating_packet",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_iso(),
        "authority_posture": "generated_projection_not_source_authority",
        "purpose": "Compact Type A runtime doctrine frame: always-global active principles plus routed frequent/situational principles and candidate axiom pressure.",
        "source_refs": [
            principles_rel,
            axioms_rel,
            STD_RAW_SEED_PRINCIPLES_REL,
            STD_SYSTEM_AXIOM_CANDIDATE_REL,
            STD_AGENT_ENTRY_SURFACE_REL,
            PRINCIPLE_SCOPE_PAPER_REL,
        ],
        "selection_policy": {
            "global_always": {
                "rule": "status == active and scope_profile.scope_id == global.constitutional_doctrine",
                "runtime_behavior": "Safe to project as tiny/flag rows into every Type A runtime.",
                "max_rows": max_global,
            },
            "global_frequent": {
                "rule": "status == active and scope_profile.domain == global, excluding global.constitutional_doctrine",
                "runtime_behavior": "Frequent cross-task pressure, routed by situation rather than always injected.",
                "max_rows": max_frequent,
            },
            "agent_principles": {
                "rule": "status == active and scope_profile.scope_id in configured agent_principle_scope_ids",
                "runtime_behavior": "Agent-specific runtime projection: isomorphic principle rows, injected as ids/counts in entry strips and expanded only through the packet/card routes.",
                "max_rows": max_agent,
            },
            "situational": {
                "rule": "All other active principles; non-active rows stay out of runtime guidance.",
                "runtime_behavior": "Open through --entry/--context-pack, paper modules, or explicit option-surface row drilldowns.",
            },
            "axiom_candidates": {
                "rule": "Candidates remain candidate_not_active_doctrine and surface as provisional pressure only when task evidence matches.",
                "runtime_behavior": "Never inject as active law; use candidate_runtime_pressure and tape drilldowns.",
                "max_rows": max_axioms,
            },
        },
        "global_runtime_capsule": {
            "injection_policy": "always_project_tiny_plus_flag_for_type_a",
            "authority_boundary": "Active principles only; raw-seed principle graph remains authority.",
            "principles": [
                _principle_capsule_row(
                    repo_root,
                    row,
                    related_axioms_by_principle=related_axioms_by_principle,
                )
                for row in global_rows
            ],
        },
        "frequent_principles": [
            _principle_capsule_row(
                repo_root,
                row,
                related_axioms_by_principle=related_axioms_by_principle,
                relation_role="agent_operating_packet.frequent_principles",
            )
            for row in frequent_rows
        ],
        "agent_principles": {
            "artifact_role": "agent_specific_runtime_projection",
            "runtime_doctrine_type": "agent_principle",
            "authority_boundary": "Rows are selected from raw_seed_principles.json; this packet is not a new principle source.",
            "selection_rule": "status == active and scope_profile.scope_id in configured agent_principle_scope_ids",
            "scope_ids": agent_scope_ids,
            "rows": [
                _principle_capsule_row(
                    repo_root,
                    row,
                    related_axioms_by_principle=related_axioms_by_principle,
                    relation_role="agent_operating_packet.agent_principles",
                    runtime_doctrine_type="agent_principle",
                )
                for row in agent_rows
            ],
        },
        "principle_classification_index": [
            _principle_index_row(row, agent_scope_ids=agent_scope_id_set)
            for row in sorted(principles, key=lambda r: _string(r.get("id")))
        ],
        "candidate_axiom_pressure": {
            "authority_posture": "candidate_not_active_doctrine",
            "non_law_warning": "Candidate axioms are provisional pressure, not active doctrine; promotion is operator/controller governed.",
            "rows": [_axiom_glance_row(row) for row in axiom_rows],
        },
        "classification_summary": _classification_summary(principles),
        "routing_matrix": [
            {
                "capsule_class": "global_always",
                "inject": "tiny+flag into Type A runtime and bootstrap strips",
                "expand": "./repo-python kernel.py --agent-operating-packet --band card",
            },
            {
                "capsule_class": "global_frequent",
                "inject": "ids/counts only unless task-selected",
                "expand": "./repo-python kernel.py --option-surface principles --band card --ids <pri_id>",
            },
            {
                "capsule_class": "agent_principle",
                "inject": "ids/counts into Type A entry strips; full row only through agent operating packet or principle card",
                "expand": "./repo-python kernel.py --agent-operating-packet --band card",
            },
            {
                "capsule_class": "situational",
                "inject": "not injected globally",
                "expand": "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            },
            {
                "capsule_class": "axiom_candidate_pressure",
                "inject": "candidate label only when task evidence matches",
                "expand": "./repo-python kernel.py --option-surface axiom_candidates --band tape --ids <axiom_candidate_id>",
            },
        ],
        "commands": {
            "packet": "./repo-python kernel.py --agent-operating-packet",
            "agent_principles": "./repo-python kernel.py --agent-principles --band card",
            "agent_principle_authoring": "./repo-python kernel.py --agent-principle-authoring \"<lesson>\" --context-budget 12000",
            "global_principle_tape": (
                "./repo-python kernel.py --option-surface principles --band tape --ids "
                + ",".join(_string(row.get("id")) for row in global_rows)
            ),
            "principle_clusters": "./repo-python kernel.py --option-surface principles --band cluster_flag",
            "agent_principle_cards": (
                "./repo-python kernel.py --option-surface principles --band card --ids "
                + ",".join(_string(row.get("id")) for row in agent_rows)
            ),
            "axiom_candidates": "./repo-python kernel.py --option-surface axiom_candidates --band flag",
        },
        "warnings": [],
    }
    if len(global_rows) < max_global:
        packet["warnings"].append(
            {
                "kind": "global_principle_count_below_configured_max",
                "count": len(global_rows),
                "configured_max": max_global,
            }
        )
    if not global_rows:
        packet["warnings"].append(
            {
                "kind": "missing_global_runtime_principles",
                "message": "No active global.constitutional_doctrine principles resolved.",
            }
        )
    return _finalize_metrics(packet)


def load_agent_operating_packet(
    repo_root: Path,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load the generated sidecar when available, rebuilding only as fallback."""
    cfg = dict(config or {})
    target_rel = _string(cfg.get("target_path")) or DEFAULT_TARGET_REL
    data = _load_json(repo_root / target_rel)
    if data.get("kind") == "agent_operating_packet" and data.get("schema_version") == SCHEMA_VERSION:
        return data
    return build_agent_operating_packet(repo_root, config=config)


def load_agent_operating_packet_strip(
    repo_root: Path,
    *,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load the entry-safe sidecar strip, rebuilding the packet only if needed."""
    return build_agent_operating_packet_strip(
        load_agent_operating_packet(repo_root, config=config)
    )


def build_agent_operating_packet_strip(packet: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the entry-safe projection strip for bootstrap markdown and handoff JSON."""
    if not isinstance(packet, Mapping) or not packet:
        return {
            "kind": "agent_operating_packet_strip",
            "schema_version": STRIP_SCHEMA_VERSION,
            "status": "missing",
            "source_ref": DEFAULT_TARGET_REL,
        }
    capsule = packet.get("global_runtime_capsule") if isinstance(packet.get("global_runtime_capsule"), Mapping) else {}
    principles = [row for row in (capsule.get("principles") or []) if isinstance(row, Mapping)]
    agent_packet = packet.get("agent_principles") if isinstance(packet.get("agent_principles"), Mapping) else {}
    agent_principles = [row for row in (agent_packet.get("rows") or []) if isinstance(row, Mapping)]
    metrics = packet.get("budget_metrics") if isinstance(packet.get("budget_metrics"), Mapping) else {}
    return {
        "kind": "agent_operating_packet_strip",
        "schema_version": STRIP_SCHEMA_VERSION,
        "status": "available",
        "source_ref": DEFAULT_TARGET_REL,
        "authority_posture": _string(packet.get("authority_posture") or "generated_projection_not_source_authority"),
        "global_principle_ids": [_string(row.get("source_id")) for row in principles if row.get("source_id")],
        "agent_principle_ids": [_string(row.get("source_id")) for row in agent_principles if row.get("source_id")],
        "global_principles": [
            {
                "id": _string(row.get("source_id")),
                "tiny": _string(row.get("tiny")),
                "flag": _string(row.get("flag")),
            }
            for row in principles
        ],
        "candidate_axiom_policy": "candidate_pressure_only_not_active_law",
        "metrics": {
            "global_principle_count": metrics.get("global_principle_count", len(principles)),
            "agent_principle_count": metrics.get("agent_principle_count", len(agent_principles)),
            "frequent_principle_count": metrics.get("frequent_principle_count"),
            "axiom_candidate_glance_count": metrics.get("axiom_candidate_glance_count"),
            "entry_strip_bytes": metrics.get("entry_strip_bytes"),
            "global_runtime_capsule_bytes": metrics.get("global_runtime_capsule_bytes"),
            "compact_full_packet_bytes": metrics.get("compact_full_packet_bytes"),
        },
        "route": "./repo-python kernel.py --agent-operating-packet --band card",
        "agent_principles_route": "./repo-python kernel.py --agent-principles --band card",
    }


def render_agent_operating_packet_markdown(
    packet: Mapping[str, Any] | None,
    *,
    heading: str = "**Agent operating packet:**",
    compact: bool = False,
) -> list[str]:
    """Render a compact markdown pointer without replacing the JSON sidecar."""
    if not isinstance(packet, Mapping) or not packet:
        return []
    strip = build_agent_operating_packet_strip(packet)
    if strip.get("status") != "available":
        return [
            "",
            heading,
            f"- Source: `{DEFAULT_TARGET_REL}` unavailable; refresh `./repo-python tools/meta/factory/build_agent_bootstrap_projection.py`.",
        ]
    metrics = strip.get("metrics") if isinstance(strip.get("metrics"), Mapping) else {}
    ids = ", ".join(f"`{item}`" for item in strip.get("global_principle_ids") or [])
    agent_ids = ", ".join(f"`{item}`" for item in strip.get("agent_principle_ids") or [])
    source = _string(strip.get("source_ref")) or DEFAULT_TARGET_REL
    if compact:
        return [
            "",
            heading,
            f"- Source: `{source}`; globals: {ids}; agent principles: {agent_ids or '`none`'}; axiom candidates stay `candidate_pressure_only_not_active_law`.",
            f"- Route: `{strip.get('route')}`; strip `{metrics.get('entry_strip_bytes')}` bytes, global capsule `{metrics.get('global_runtime_capsule_bytes')}` bytes.",
        ]
    return [
        "",
        heading,
        f"- Source: `{source}`; authority posture `{strip.get('authority_posture')}`.",
        f"- Always-global principles ({metrics.get('global_principle_count')}): {ids}.",
        f"- Agent principles ({metrics.get('agent_principle_count')}): {agent_ids or '`none`'}; full rows expand through `./repo-python kernel.py --agent-principles --band card` or principle card routes.",
        f"- Frequent/situational split: `{metrics.get('frequent_principle_count')}` frequent global rows; other active principles route by context-pack/option-surface.",
        f"- Axiom candidates: `{metrics.get('axiom_candidate_glance_count')}` candidate-pressure rows; never active law without promotion.",
        f"- Bytes: strip `{metrics.get('entry_strip_bytes')}`, global capsule `{metrics.get('global_runtime_capsule_bytes')}`, compact full packet `{metrics.get('compact_full_packet_bytes')}`.",
        f"- Route: `{strip.get('route')}`.",
    ]


__all__ = [
    "DEFAULT_TARGET_REL",
    "GLOBAL_CONSTITUTIONAL_SCOPE_ID",
    "SCHEMA_VERSION",
    "STRIP_SCHEMA_VERSION",
    "build_agent_operating_packet",
    "build_agent_principle_authoring_packet",
    "build_agent_principle_lens",
    "build_agent_operating_packet_strip",
    "load_agent_operating_packet",
    "load_agent_operating_packet_strip",
    "render_agent_operating_packet_markdown",
]
