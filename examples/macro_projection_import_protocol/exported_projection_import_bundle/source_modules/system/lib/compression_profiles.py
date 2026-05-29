"""
[PURPOSE]
- Teleology: Keep compression creation and navigation expansion on the same
  profile contract without promoting the first pass into a mature standard.
- Mechanism: Load the candidate compression profile registry, expose compact
  profile pointers for packets, and build shared raw-seed context contracts
  with drilldown refs, dynamic fact rows, and omission receipts.

[CONSTRAINTS]
- Candidate layer only. The checked-in registry is an implementation probe,
  not a global std_* authority.
- Full ancestry and raw prose stay in their home ledgers/registries. Packets
  carry ids, proof heads, counts, and reopen commands.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_REGISTRY_REL = "codex/doctrine/compression_profiles.json"
RAW_SEED_CONTEXT_PROFILE_ID = "raw_seed_voice_context_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dedupe_strings(values: Iterable[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _registry_path(repo_root: Path | str = REPO_ROOT, registry_path: str | Path | None = None) -> Path:
    raw_path = Path(registry_path) if registry_path is not None else Path(PROFILE_REGISTRY_REL)
    return raw_path if raw_path.is_absolute() else Path(repo_root) / raw_path


def _default_registry() -> dict[str, Any]:
    return {
        "kind": "compression_profile_registry",
        "schema_version": "compression_profile_registry_candidate_v1",
        "status": "candidate",
        "global_principles": [
            "Compression rows are cognitive assets: creation and navigation use the same profile id.",
            "Preserve authority, voice, reversals, evidence, next moves, and lifecycle state.",
            "Do not copy long ancestry into every row; use proof heads, counts, and drilldown refs.",
            "Volatile facts live as dynamic fact rows with observed_at, probe/source, and fingerprint.",
            "Compression depth is artifact-kind-specific: stable band names do not imply fixed sentence counts.",
            "Lower brackets win on conflict; higher brackets are re-emitted when they drift from source authority.",
        ],
        "profiles": [
            {
                "profile_id": RAW_SEED_CONTEXT_PROFILE_ID,
                "artifact_kind": "raw_seed",
                "purpose": "voice-preserving contextual compression over raw-seed paragraphs, bins, and atom shards",
                "bands": ["flag", "card", "context", "deep"],
                "source_ladder": [
                    {
                        "bracket": "raw_paragraph",
                        "role": "voice authority; never rewritten or treated as derived",
                        "source_state": "paragraph_only",
                    },
                    {
                        "bracket": "voice_normalized_statement",
                        "role": "syntax-faithful cleanup candidate; no global inference",
                        "source_state": "paragraph_only",
                    },
                    {
                        "bracket": "atomized_shard",
                        "role": "normalized lower-bracket voice claim with parent par_* and voice anchor",
                        "source_state": "sharded",
                    },
                    {
                        "bracket": "contextual_row",
                        "role": "system-context reading over paragraph and shard evidence",
                        "source_state": "sharded_or_mixed",
                    },
                    {
                        "bracket": "routing_review",
                        "role": "controller-gated proposal surface, not compression authority",
                        "source_state": "post_context",
                    },
                    {
                        "bracket": "doctrine_projection",
                        "role": "durable principle, skill, paper module, standard, or code update after apply",
                        "source_state": "post_apply",
                    },
                ],
                "band_contracts": {
                    "flag": {
                        "job": "route-card or existence signal",
                        "minimum_payload": ["one claim", "source ids", "next bracket"],
                        "forbidden": ["global coverage claim", "doctrine route decision"],
                    },
                    "card": {
                        "job": "bounded source card",
                        "minimum_payload": ["local claim", "proof head", "source state", "context-space refs"],
                        "forbidden": ["replace atomized shards", "hide missing shard coverage"],
                    },
                    "context": {
                        "job": "working-set row for a worker or navigator",
                        "minimum_payload": [
                            "paragraph/shard reading",
                            "context-space refs",
                            "dynamic facts",
                            "drilldown refs",
                            "omission receipt",
                        ],
                        "forbidden": ["copy whole neighborhoods", "apply doctrine"],
                    },
                    "deep": {
                        "job": "mini-packet for higher reasoning",
                        "minimum_payload": [
                            "local source excerpts or shard rows",
                            "context-space refs",
                            "all context-band fields",
                        ],
                        "forbidden": ["become a source archive", "duplicate ledgers"],
                    },
                },
                "creator_skill_id": "compression.raw_seed_contextual_compression",
                "navigator_skill_id": "raw_seed_navigation",
                "mandatory_preserve": [
                    "par_* authority",
                    "voice anchor",
                    "operator reversals and uncertainty",
                    "proof head",
                    "proof depth",
                    "freshness metadata",
                    "drilldown refs",
                    "next moves",
                ],
                "allowed_loss": [
                    "full sibling prose outside the focus window",
                    "full source-anchor ancestry",
                    "low-value local examples",
                    "distant edges already recoverable from ledgers",
                ],
                "forbidden_collapse": [
                    "paragraph authority into shard-only authority",
                    "voice into encyclopedia prose",
                    "volatile counts into copied prose",
                    "routing decisions into distillation packets",
                    "contradictions into a single resolved claim",
                    "shards into context-free slogans",
                    "directional gestures into overconfident implementation plans",
                ],
                "source_state_policy": {
                    "allowed": ["paragraph_only", "sharded", "mixed", "unknown"],
                    "rule": (
                        "Fresh unsharded raw-seed paragraphs are still authority; mark source_state "
                        "rather than dropping them or pretending shard coverage exists."
                    ),
                },
                "context_space_policy": {
                    "rule": (
                        "Before compressing a shard into a higher row, identify the context-space: the paper module, "
                        "skill, standard, runtime surface, profile, or cross-section that makes "
                        "the shard intelligible."
                    ),
                    "allowed_ref_kinds": [
                        "paper_module",
                        "skill",
                        "standard",
                        "runtime_surface",
                        "compression_profile",
                        "source_registry",
                    ],
                    "missing_context_behavior": "Emit a lower band or add validation_notes; do not invent system context.",
                },
                "worker_tier_policy": {
                    "cheap_selector": "embed, cluster, rank, detect freshness, and suggest candidate context-spaces",
                    "syntax_worker": "clean speech-to-text and split candidate statements without global inference",
                    "distiller": "produce atomized shards with voice anchors and gestures_towards",
                    "contextual_compressor": "create reversible profile rows using paper/module context",
                    "controller": "route, apply, author durable doctrine, or change standards",
                },
                "batching_policy": {
                    "rule": (
                        "Bridge packets may carry multiple paragraphs, but packet membership is "
                        "transport evidence only. Multi-source rows require a named shared context-space."
                    ),
                    "production_target": (
                        "Use embedding/cosine neighborhoods as semantic candidates, then fit them "
                        "chronologically into adjustable bridge-budget bins."
                    ),
                    "adaptive_signals": [
                        "json_validity",
                        "contextual_rows_returned",
                        "omitted_bands",
                        "drilldown_completeness",
                        "operator_inspection_quality",
                    ],
                },
                "evidence_policy": {
                    "packet_carries": ["ids", "proof_head", "proof_depth", "freshness", "drilldown_refs"],
                    "ledger_holds": ["full source_anchors ancestry", "long sibling lists", "registry-wide counts"],
                },
                "drilldown_policy": {
                    "default": "open the declared navigator skill, then the profile, then the cited par_* or shard refs",
                    "commands": [
                        "python3 kernel.py --resolve-raw-seed-ref {family} paragraph:{par_id}",
                        "python3 kernel.py --shards --shards-paragraph {par_id}",
                        "python3 kernel.py --raw-seed-navigation-runtime {family} --raw-seed-nav-group {group_id}",
                    ],
                },
                "dynamic_fact_policy": {
                    "required_fields": ["fact_id", "value", "observed_at", "probe_command", "source_path", "fingerprint"],
                    "rule": "Never freeze live counts as prose when a refreshable fact row can carry them.",
                },
                "validation_probe": {
                    "must": [
                        "row has profile_id and creator/navigator skill ids",
                        "row has drilldown_refs",
                        "dynamic facts include observed_at and fingerprint",
                        "source ancestry is referenced, not copied",
                        "row declares or implies a source_state",
                        "context-space is named before shard-level contextual compression",
                    ]
                },
            }
        ],
    }


def load_compression_profile_registry(
    repo_root: Path | str = REPO_ROOT,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    path = _registry_path(repo_root, registry_path)
    payload = _load_json(path) or _default_registry()
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        payload = _default_registry()
    payload.setdefault("registry_path", str(Path(PROFILE_REGISTRY_REL)))
    return payload


def get_compression_profile(
    profile_id: str = RAW_SEED_CONTEXT_PROFILE_ID,
    *,
    repo_root: Path | str = REPO_ROOT,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    registry = load_compression_profile_registry(repo_root, registry_path)
    requested = str(profile_id or RAW_SEED_CONTEXT_PROFILE_ID).strip()
    for profile in registry.get("profiles") or []:
        if isinstance(profile, Mapping) and str(profile.get("profile_id") or "").strip() == requested:
            return dict(profile)
    raise KeyError(f"Unknown compression profile: {requested}")


def compression_profile_pointer(
    profile: Mapping[str, Any],
    *,
    registry_rel: str = PROFILE_REGISTRY_REL,
) -> dict[str, Any]:
    return {
        "profile_id": _string(profile.get("profile_id")),
        "profile_kind": _string(profile.get("profile_kind")),
        "artifact_role": _string(profile.get("artifact_role")),
        "context_profile_id": _string(profile.get("context_profile_id")),
        "artifact_kind": _string(profile.get("artifact_kind")),
        "purpose": _string(profile.get("purpose")),
        "audience": _string(profile.get("audience")),
        "output_path": _string(profile.get("output_path")),
        "last_green_output_path": _string(profile.get("last_green_output_path")),
        "candidate_output_path": _string(profile.get("candidate_output_path")),
        "operator_packet_path": _string(profile.get("operator_packet_path")),
        "status_sidecar_path": _string(profile.get("status_sidecar_path")),
        "source_model": _string(profile.get("source_model")),
        "surface_family_id": _string(profile.get("surface_family_id")),
        "root_slug": _string(profile.get("root_slug")),
        "authority_contract_path": _string(profile.get("authority_contract_path")),
        "projection_not_authority": bool(profile.get("projection_not_authority")),
        "disclosure_posture": _string(profile.get("disclosure_posture")),
        "receiver_intent": _string(profile.get("receiver_intent")),
        "job_to_be_done": _string(profile.get("job_to_be_done")),
        "command_policy": _string(profile.get("command_policy")),
        "refresh_owner": _string(profile.get("refresh_owner")),
        "authority_boundary": _string(profile.get("authority_boundary")),
        "owner_routes": dict(profile.get("owner_routes") or {}),
        "source_manifest_fields_used": list(profile.get("source_manifest_fields_used") or []),
        "auxiliary_sources": list(profile.get("auxiliary_sources") or []),
        "bands": list(profile.get("bands") or []),
        "source_ladder": list(profile.get("source_ladder") or []),
        "band_contracts": dict(profile.get("band_contracts") or {}),
        "creator_skill_id": _string(profile.get("creator_skill_id")),
        "navigator_skill_id": _string(profile.get("navigator_skill_id")),
        "registry_path": registry_rel,
        "mandatory_preserve": list(profile.get("mandatory_preserve") or []),
        "allowed_loss": list(profile.get("allowed_loss") or []),
        "forbidden_collapse": list(profile.get("forbidden_collapse") or []),
        "source_state_policy": dict(profile.get("source_state_policy") or {}),
        "context_space_policy": dict(profile.get("context_space_policy") or {}),
        "worker_tier_policy": dict(profile.get("worker_tier_policy") or {}),
        "batching_policy": dict(profile.get("batching_policy") or {}),
        "evidence_policy": dict(profile.get("evidence_policy") or {}),
        "drilldown_policy": dict(profile.get("drilldown_policy") or {}),
        "dynamic_fact_policy": dict(profile.get("dynamic_fact_policy") or {}),
        "validation_probe": dict(profile.get("validation_probe") or {}),
    }


def build_dynamic_fact_row(
    *,
    fact_id: str,
    value: Any,
    observed_at: str,
    probe_command: str,
    source_path: str,
    fingerprint_material: Any,
    description: str = "",
) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "value": value,
        "observed_at": observed_at,
        "probe_command": probe_command,
        "source_path": source_path,
        "fingerprint": _stable_digest(fingerprint_material)[:16],
        "description": description,
    }


def build_raw_seed_context_contract(
    *,
    repo_root: Path | str = REPO_ROOT,
    family: str,
    family_dir: str,
    focus_cards: list[Mapping[str, Any]],
    context_rows: list[Mapping[str, Any]],
    grouping_rows: list[Mapping[str, Any]],
    packet_kind: str,
    selected_count: int,
    total_paragraph_count: int,
    total_atomized_parent_count: int,
    source_paths: Mapping[str, str] | None = None,
    observed_at: str | None = None,
    profile_id: str = RAW_SEED_CONTEXT_PROFILE_ID,
) -> dict[str, Any]:
    profile = get_compression_profile(profile_id, repo_root=repo_root)
    pointer = compression_profile_pointer(profile)
    observed = observed_at or _utc_now()
    focus_ids = _dedupe_strings(card.get("id") for card in focus_cards)
    group_ids = _dedupe_strings(
        group_id
        for row in grouping_rows
        for group_id in [row.get("group_key")]
    )
    context_ids = _dedupe_strings(row.get("paragraph_id") for row in context_rows)
    paths = dict(source_paths or {})
    raw_seed_json_path = paths.get("raw_seed_json_path") or f"{family_dir}/raw_seed.json"
    extracted_shards_path = paths.get("extracted_shards_path") or f"{family_dir}/extracted_shards.json"

    dynamic_fact_rows = [
        build_dynamic_fact_row(
            fact_id="raw_seed_focus_paragraph_count",
            value=len(focus_ids),
            observed_at=observed,
            probe_command="build_distillation_run_payload",
            source_path=raw_seed_json_path,
            fingerprint_material={"focus_ids": focus_ids, "packet_kind": packet_kind},
            description="Focus rows selected into this compression packet.",
        ),
        build_dynamic_fact_row(
            fact_id="raw_seed_selected_cohort_count",
            value=selected_count,
            observed_at=observed,
            probe_command="build_distillation_run_payload",
            source_path=raw_seed_json_path,
            fingerprint_material={"selected_count": selected_count, "family": family},
            description="Selected cohort size for this generated run.",
        ),
        build_dynamic_fact_row(
            fact_id="raw_seed_total_paragraph_count",
            value=total_paragraph_count,
            observed_at=observed,
            probe_command="build_distillation_run_payload",
            source_path=raw_seed_json_path,
            fingerprint_material={"total_paragraph_count": total_paragraph_count, "family": family},
            description="Live paragraph count at packet materialization time.",
        ),
        build_dynamic_fact_row(
            fact_id="raw_seed_atomized_parent_count",
            value=total_atomized_parent_count,
            observed_at=observed,
            probe_command="build_distillation_run_payload",
            source_path=extracted_shards_path,
            fingerprint_material={
                "total_atomized_parent_count": total_atomized_parent_count,
                "family": family,
            },
            description="Parent paragraphs with existing atomized shard descendants at packet materialization time.",
        ),
    ]

    drilldown_refs = [
        {
            "ref_id": "compression_profile",
            "kind": "compression_profile",
            "id": profile_id,
            "path": PROFILE_REGISTRY_REL,
        },
        {
            "ref_id": "creator_skill",
            "kind": "skill",
            "id": pointer["creator_skill_id"],
            "path": "codex/doctrine/skills/compression/raw_seed_contextual_compression.md",
        },
        {
            "ref_id": "navigator_skill",
            "kind": "skill",
            "id": pointer["navigator_skill_id"],
            "path": "codex/doctrine/skills/raw_seed/raw_seed_navigation.md",
        },
        {
            "ref_id": "raw_seed_registry",
            "kind": "source_registry",
            "path": raw_seed_json_path,
            "ids": focus_ids[:12],
        },
        {
            "ref_id": "raw_seed_shards",
            "kind": "source_registry",
            "path": paths.get("raw_seed_shards_path") or f"{family_dir}/raw_seed/raw_seed_shards.json",
        },
        {
            "ref_id": "extracted_shards",
            "kind": "source_registry",
            "path": extracted_shards_path,
        },
    ]

    context_horizon = {
        "schema_version": "compression_context_horizon_v1",
        "local_full": [
            {
                "kind": "focus_paragraphs",
                "ids": focus_ids,
                "band": "deep",
                "reason": "focus authority for this packet",
            }
        ],
        "authority_cards": [
            {
                "kind": "compression_profile",
                "id": profile_id,
                "band": "card",
                "path": PROFILE_REGISTRY_REL,
            },
            {
                "kind": "skill",
                "id": pointer["creator_skill_id"],
                "band": "card",
                "path": "codex/doctrine/skills/compression/raw_seed_contextual_compression.md",
            },
            {
                "kind": "skill",
                "id": pointer["navigator_skill_id"],
                "band": "card",
                "path": "codex/doctrine/skills/raw_seed/raw_seed_navigation.md",
            },
            {
                "kind": "paper_module",
                "id": "raw_seed_theory",
                "band": "flag",
                "path": "codex/doctrine/paper_modules/raw_seed_theory.md",
            },
            {
                "kind": "paper_module",
                "id": "navigation_hologram_theory",
                "band": "flag",
                "path": "codex/doctrine/paper_modules/navigation_hologram_theory.md",
            },
        ],
        "sibling_flags": [
            {
                "kind": "packet_context_row",
                "paragraph_id": row.get("paragraph_id"),
                "relationship": list(row.get("relationship") or []),
                "band": "flag",
                "emit_shards": bool(row.get("emit_shards")),
            }
            for row in context_rows[:12]
        ],
        "group_flags": [
            {
                "kind": "packet_grouping_row",
                "group_key": row.get("group_key"),
                "focus_paragraph_ids": list(row.get("focus_paragraph_ids") or [])[:12],
                "band": "flag",
                "not_a_route": bool(row.get("not_a_route")),
            }
            for row in grouping_rows[:12]
        ],
        "distant_siblings": [
            {
                "kind": "idea_group_or_context",
                "ids": group_ids[:12],
                "band": "flag",
                "reason": "Packet exposes ids and grouping hints; full sibling rows live in raw_seed registries.",
            }
        ],
        "omitted_context": [
            {
                "kind": "full_source_anchors_ancestry",
                "home": "source ledgers and registries",
                "reason": "Repeated ancestry belongs in ledgers, not every packet.",
            },
            {
                "kind": "full_raw_seed_prose_outside_focus",
                "home": raw_seed_json_path,
                "reason": "Focus paragraphs carry authority locally; outside prose is reopened by id.",
            },
            {
                "kind": "full_extracted_shards_corpus",
                "home": extracted_shards_path,
                "reason": "The worker gets counts and drilldown refs, not corpus-wide authority.",
            },
        ],
    }

    return {
        "schema_version": "compression_context_contract_v1",
        "profile_id": profile_id,
        "creator_skill_id": pointer["creator_skill_id"],
        "navigator_skill_id": pointer["navigator_skill_id"],
        "band": "context",
        "source_state": "unknown",
        "band_reason": (
            "context band because the packet combines focus paragraph authority, "
            "profile/skill context, drilldown refs, dynamic facts, and omission receipts"
        ),
        "compression_profile": pointer,
        "context_horizon": context_horizon,
        "context_space_refs": [
            *context_horizon["authority_cards"],
        ],
        "drilldown_refs": drilldown_refs,
        "dynamic_fact_rows": dynamic_fact_rows,
        "omission_receipt": {
            "schema_version": "compression_omission_receipt_v1",
            "omitted_context_count": len(context_horizon["omitted_context"]),
            "omitted_context": context_horizon["omitted_context"],
            "proof_head": focus_ids[0] if focus_ids else None,
            "proof_depth": len(focus_ids) + len(context_ids) + len(group_ids),
            "source_home_policy": "one semantic object gets one home; compact rows carry ids and drilldown refs",
        },
    }


def _raw_seed_context_next_moves(contract: Mapping[str, Any]) -> list[str]:
    source_state = _string(contract.get("source_state")) or "unknown"
    moves: list[str] = []
    if source_state == "paragraph_only":
        moves.append("needs_atomization")
    elif source_state == "sharded":
        moves.append("open_lower_bracket_shards")
    elif source_state == "mixed":
        moves.extend(["open_lower_bracket_shards", "atomize_missing_focus_paragraphs"])
    else:
        moves.append("inspect_source_state_before_compression")
    moves.extend(
        [
            "identify_context_space_before_shard_level_contextual_compression",
            "open_declared_drilldown_refs_before_route_or_apply",
        ]
    )
    return _dedupe_strings(moves)


def contextual_row_from_contract(
    *,
    row_id: str,
    source_ids: list[str],
    title: str,
    summary: str,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "row_kind": "raw_seed_contextual_compression_candidate",
        "profile_id": contract.get("profile_id"),
        "creator_skill_id": contract.get("creator_skill_id"),
        "navigator_skill_id": contract.get("navigator_skill_id"),
        "skill_id": contract.get("creator_skill_id"),
        "band": contract.get("band") or "context",
        "source_state": contract.get("source_state") or "unknown",
        "source_ids": _dedupe_strings(source_ids),
        "title": title,
        "summary": summary,
        "band_reason": contract.get("band_reason") or "",
        "context_space_refs": list(contract.get("context_space_refs") or []),
        "context_horizon": dict(contract.get("context_horizon") or {}),
        "drilldown_refs": list(contract.get("drilldown_refs") or []),
        "dynamic_fact_rows": list(contract.get("dynamic_fact_rows") or []),
        "omission_receipt": dict(contract.get("omission_receipt") or {}),
        "next_moves": _raw_seed_context_next_moves(contract),
        "up_propagation_candidates": [],
        "validation_probe": dict((contract.get("compression_profile") or {}).get("validation_probe") or {}),
    }
