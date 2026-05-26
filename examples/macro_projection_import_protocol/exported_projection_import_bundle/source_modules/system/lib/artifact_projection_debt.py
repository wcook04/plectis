"""
Read-only composer for executable-grammar projection debt.

The rows here do not become source authority. They make existing pressure
visible as a bounded option surface, then hand repair work to row jobs whose
provider output is receipt/row_patch only.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "artifact_projection_debt_v0"
KIND_ID = "artifact_projection_debt"
SYSTEM_MICROCOSM_KIND_ID = "system_microcosm"

_SKILL_REGISTRY = Path("codex/doctrine/skills/skill_registry.json")
_SKILL_STANDARD = "codex/standards/std_skill.json"
_KIND_ATLAS_STANDARD = "codex/standards/std_kind_atlas.json"
_AGENT_OBSERVATIONS_LOG = Path("state/agent_observations/observations.jsonl")
_ANNEX_SYNC_DIGEST = Path("annexes/annex_sync_digest.json")
_COMPLIANCE_LEDGER = Path("codex/hologram/compliance/ledger.json")
_STANDARD_SKILL_MAP = Path("codex/hologram/skills/standard_skill_map.json")
_METABOLISM_BLACKBOARD = Path("state/metabolism/blackboard.json")
_METABOLISM_STATUS = Path("state/metabolism/metabolism_status.json")
_DEFAULT_BLACKBOARD_CLAIM_TTL_SECONDS = 600

_SKILL_PASSPORT_REQUIRED_FIELDS = [
    "cluster_keys",
    "atom",
    "flag",
    "card",
    "when_to_open",
    "when_not_to_open",
    "safe_drilldown",
]

_PROJECTION_SPECS: tuple[dict[str, str], ...] = (
    {
        "projection_id": "compliance_ledger",
        "path": str(_COMPLIANCE_LEDGER),
        "row_array_path": "by_standard",
        "governing_standard": "codex/standards/std_compliance_coverage.json",
        "build_command": "./repo-python tools/meta/factory/build_compliance_ledger.py",
        "why": "Compliance rows cannot show which standards need metabolism work.",
    },
    {
        "projection_id": "standard_skill_map",
        "path": str(_STANDARD_SKILL_MAP),
        "row_array_path": "pairings",
        "governing_standard": _SKILL_STANDARD,
        "build_command": "./repo-python tools/meta/factory/build_standard_skill_map.py",
        "why": "Standard rows cannot expose which skill authors or verifies each standard.",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _to_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _jsonl_count(path: Path) -> int:
    try:
        if not path.is_file():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _compact(value: Any, *, max_chars: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _short_hash(parts: Sequence[object], *, length: int = 12) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()[:length]


def _safe_row_id(prefix: str, *parts: object) -> str:
    raw = ":".join(str(part or "unknown") for part in parts)
    cleaned = "".join(ch if ch.isalnum() or ch in "._:-" else "_" for ch in raw)
    return f"{prefix}:{cleaned}"


def _row_array_count(payload: Mapping[str, Any], path: str) -> int:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return 0
        value = value.get(part)
    return len(value) if isinstance(value, list) else 0


def _base_debt_row(
    *,
    row_id: str,
    debt_class: str,
    source_surface: str,
    target_kind: str,
    target_row_id: str,
    failure_mode: str,
    repair_class: str,
    claim: str,
    evidence: str,
    safe_alternative: str,
    authority_ceiling: str = "candidate_authoring",
    expected_patch_shape: Mapping[str, Any] | None = None,
    validation_contract: Mapping[str, Any] | None = None,
    promotion_gate: Mapping[str, Any] | None = None,
    source_refs: Sequence[str] = (),
    target_files: Sequence[str] = (),
    priority: int = 50,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "artifact_kind": KIND_ID,
        "band": "flag",
        "debt_class": debt_class,
        "source_surface": source_surface,
        "target_kind": target_kind,
        "target_row_id": target_row_id,
        "failure_mode": failure_mode,
        "repair_class": repair_class,
        "priority": priority,
        "claim": _compact(claim, max_chars=260),
        "evidence": _compact(evidence, max_chars=320),
        "safe_alternative": safe_alternative,
        "authority_ceiling": authority_ceiling,
        "expected_patch_shape": dict(expected_patch_shape or _default_expected_patch_shape(target_files)),
        "validation_contract": dict(validation_contract or _default_validation_contract()),
        "promotion_gate": dict(promotion_gate or _default_promotion_gate()),
        "source_refs": list(source_refs),
        "target_files": list(target_files),
        "drilldown_command": f"./repo-python kernel.py --option-surface {KIND_ID} --band card --ids {row_id}",
        "row_job_command": f"./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
    }


def _default_expected_patch_shape(target_files: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "kind": "receipt_or_row_patch_only",
        "provider_output_targets": [
            "state/compute_workers/receipts/",
            "state/compute_workers/row_patches/",
        ],
        "candidate_source_targets_for_controller_only": list(target_files),
        "forbidden_patch_targets": [
            "raw_seed.md",
            "raw_seed_principles.json",
            "direct_doctrine_authority_from_provider",
            "source_authority_without_controller_promotion",
        ],
        "patch_is_not_authorized_by_this_job": True,
    }


def _default_validation_contract() -> dict[str, Any]:
    return {
        "commands": [
            "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
            "./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
        ],
        "acceptance": "Rows stay candidate-only until a validator/promoter accepts a receipt or row_patch.",
    }


def _default_promotion_gate() -> dict[str, Any]:
    return {
        "owner": "validator_or_type_a_controller",
        "gate": "manual_or_test_backed_promotion_required",
        "allowed_outcomes": [
            "record_receipt",
            "emit_row_patch",
            "promote_bounded_patch",
            "reject_with_reason",
            "defer_to_owner",
        ],
    }


def _projection_gap_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in _PROJECTION_SPECS:
        rel_path = Path(spec["path"])
        path = repo_root / rel_path
        payload = _load_json(path)
        row_count = _row_array_count(payload, spec["row_array_path"]) if path.is_file() else 0
        if path.is_file() and row_count > 0:
            continue
        status = "projection_missing" if not path.is_file() else "projection_empty"
        projection_id = spec["projection_id"]
        rows.append(
            _base_debt_row(
                row_id=_safe_row_id("standard_projection_gap", projection_id),
                debt_class="projection_debt",
                source_surface="standard_projection_gaps",
                target_kind=str(projection_id),
                target_row_id=str(projection_id),
                failure_mode=status,
                repair_class="populate_missing_rows",
                claim=f"{projection_id} {status}; {spec['why']}",
                evidence=f"path={rel_path}; row_array_path={spec['row_array_path']}; row_count={row_count}",
                safe_alternative=str(spec["build_command"]),
                source_refs=[str(rel_path), str(spec["governing_standard"])],
                target_files=[str(rel_path)],
                priority=92,
                validation_contract={
                    "commands": [
                        str(spec["build_command"]),
                        "./repo-python kernel.py --option-surface standard_projection_gaps --band flag",
                        "./repo-python kernel.py --option-surface artifact_projection_debt --band flag",
                    ],
                    "acceptance": "Generated projection exists with nonzero rows, or remains explicitly unpopulated with an omission receipt.",
                },
            )
        )
    return rows


def _zero_row_population_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        ("agent_observations", _AGENT_OBSERVATIONS_LOG, _jsonl_count(repo_root / _AGENT_OBSERVATIONS_LOG)),
        ("compliance_ledger", _COMPLIANCE_LEDGER, _row_array_count(_load_json(repo_root / _COMPLIANCE_LEDGER), "by_standard")),
        ("standard_skill_map", _STANDARD_SKILL_MAP, _row_array_count(_load_json(repo_root / _STANDARD_SKILL_MAP), "pairings")),
    ]
    for kind_id, rel_path, row_count in specs:
        if row_count > 0:
            continue
        rows.append(
            _base_debt_row(
                row_id=_safe_row_id("population", kind_id, "zero_rows"),
                debt_class="population_debt",
                source_surface="navigation_context_rosetta.population_honesty",
                target_kind=kind_id,
                target_row_id=f"{kind_id}:rows",
                failure_mode="zero_row_surface",
                repair_class="populate_missing_rows",
                claim=f"{kind_id} is selectable but currently has zero rows; keep row_ref null and emit population work.",
                evidence=f"row_count=0; population_mode=unpopulated; source={rel_path}",
                safe_alternative=f"./repo-python kernel.py --option-surface {kind_id} --band flag",
                source_refs=[str(rel_path)],
                target_files=[str(rel_path)],
                priority=86,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --navigation-context-rosetta --context-budget 1400",
                        f"./repo-python kernel.py --option-surface {kind_id} --band flag",
                    ],
                    "acceptance": "Zero-row kind remains honest as unpopulated, or gains stable row_refs after population.",
                },
            )
        )
    return rows


def _skill_debt_status(skill: Mapping[str, Any]) -> tuple[str, list[str]]:
    passport = skill.get("compression_passport")
    if not isinstance(passport, Mapping):
        return "missing_compression_passport", list(_SKILL_PASSPORT_REQUIRED_FIELDS)
    missing = [field for field in _SKILL_PASSPORT_REQUIRED_FIELDS if not passport.get(field)]
    if missing:
        return "partial_compression_passport", missing
    return "authored_compression_passport", []


def _skill_compression_cluster_rows(repo_root: Path) -> list[dict[str, Any]]:
    registry = _load_json(repo_root / _SKILL_REGISTRY)
    counts: Counter[str] = Counter()
    families: dict[str, set[str]] = {}
    top_ids: dict[str, list[str]] = {}
    for family in registry.get("families") or []:
        if not isinstance(family, Mapping):
            continue
        family_id = str(family.get("family_id") or "unknown")
        for skill in family.get("skills") or []:
            if not isinstance(skill, Mapping):
                continue
            skill_id = str(skill.get("id") or "")
            status, _missing = _skill_debt_status(skill)
            if status == "authored_compression_passport":
                continue
            counts[status] += 1
            families.setdefault(status, set()).add(family_id)
            if skill_id and len(top_ids.setdefault(status, [])) < 12:
                top_ids[status].append(skill_id)

    rows: list[dict[str, Any]] = []
    for status, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append(
            _base_debt_row(
                row_id=_safe_row_id("skill_compression_debt", status),
                debt_class="authoring_debt",
                source_surface="skill_compression_debt",
                target_kind="skills",
                target_row_id=status,
                failure_mode=status,
                repair_class="repair_compression_contract",
                claim=f"{status}: {count} skills need compression-passport repair.",
                evidence=f"families={sorted(families.get(status, set()))}; top_ids={top_ids.get(status, [])}",
                safe_alternative="./repo-python kernel.py --option-surface skill_compression_debt --band cluster_flag",
                source_refs=[str(_SKILL_REGISTRY), _SKILL_STANDARD],
                target_files=[str(_SKILL_REGISTRY)],
                priority=84,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --option-surface skill_compression_debt --band cluster_flag",
                        "./repo-python kernel.py --option-surface skills --band cluster_flag",
                    ],
                    "acceptance": "Affected skills gain authored compression_passport fields or stay visible as authoring debt.",
                },
                expected_patch_shape={
                    **_default_expected_patch_shape([str(_SKILL_REGISTRY)]),
                    "target_cluster_count": count,
                    "top_skill_ids": top_ids.get(status, []),
                },
            )
        )
    return rows


def _navigation_training_behavior_rows() -> list[dict[str, Any]]:
    try:
        from system.lib.navigation_route_intervention import ROUTE_REPAIR_SUGGESTIONS
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for anti_pattern_id, suggestion in sorted(ROUTE_REPAIR_SUGGESTIONS.items()):
        rows.append(
            _base_debt_row(
                row_id=_safe_row_id("navigation_training", anti_pattern_id),
                debt_class="behavior_debt",
                source_surface="navigation_training_emissions",
                target_kind="agent_route_behavior",
                target_row_id=anti_pattern_id,
                failure_mode=suggestion.bad_first_contact_shape,
                repair_class=suggestion.repair_class,
                claim=f"{anti_pattern_id}: {suggestion.bad_first_contact_shape} should route to {suggestion.preferred_first_surface}",
                evidence=suggestion.why,
                safe_alternative=suggestion.preferred_first_surface,
                source_refs=[
                    ".claude/hooks/runtime_hook.py",
                    "system/lib/navigation_route_intervention.py",
                ],
                target_files=[
                    ".claude/hooks/runtime_hook.py",
                    "system/lib/navigation_route_intervention.py",
                ],
                priority=78,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --option-surface navigation_training_emissions --band flag",
                        suggestion.evidence_command,
                    ],
                    "acceptance": "Route repair remains mapped and observed failures have a better first surface.",
                },
            )
        )
    return rows


def _annex_currentness_rows(repo_root: Path) -> list[dict[str, Any]]:
    digest = _load_json(repo_root / _ANNEX_SYNC_DIGEST)
    buckets = digest.get("buckets") if isinstance(digest.get("buckets"), Mapping) else {}
    if not buckets:
        return []
    attention_order = list(digest.get("attention_bucket_order") or [])
    rows: list[dict[str, Any]] = []
    for bucket in attention_order:
        slugs = buckets.get(bucket) if isinstance(buckets, Mapping) else []
        if not isinstance(slugs, list) or not slugs:
            continue
        top = [str(slug) for slug in slugs[:12]]
        rows.append(
            _base_debt_row(
                row_id=_safe_row_id("annex_currentness", bucket),
                debt_class="annex_currentness_debt",
                source_surface="annex_currentness",
                target_kind="annex_patterns",
                target_row_id=str(bucket),
                failure_mode=f"annex_bucket:{bucket}",
                repair_class="refresh_stale_projection" if bucket == "review_needed" else "populate_missing_rows",
                claim=f"{len(slugs)} annexes in {bucket}; review before mining or relying on stale annotations.",
                evidence=f"top_slugs={top}",
                safe_alternative="./repo-python kernel.py --annex-currentness --context-budget 12000",
                source_refs=[str(_ANNEX_SYNC_DIGEST), "annexes"],
                target_files=["annexes"],
                priority=70,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --annex-currentness --context-budget 12000",
                        "./repo-python kernel.py --metabolism-row-jobs annex-sync-digest --limit 5",
                    ],
                    "acceptance": "Annex currentness row is refreshed, repaired, or explicitly deferred with a receipt.",
                },
            )
        )
    return rows


def _annex_import_convergence_debt_rows(repo_root: Path) -> list[dict[str, Any]]:
    try:
        from system.lib.integration_not_greenfield_surfaces import build_annex_import_convergence_rows
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for source in build_annex_import_convergence_rows(repo_root, band="flag"):
        if str(source.get("debt_class") or "") != "parallel_lane_debt":
            continue
        row_id = str(source.get("row_id") or "unknown")
        rows.append(
            _base_debt_row(
                row_id=row_id,
                debt_class="parallel_lane_debt",
                source_surface="github_import_lane_convergence",
                target_kind=str(source.get("shadow_lane") or "github_import_lane"),
                target_row_id=row_id,
                failure_mode=str(source.get("failure_mode") or "parallel_lane_debt"),
                repair_class=str(source.get("recommended_action") or "migrate_or_demote"),
                claim=str(source.get("claim") or row_id),
                evidence=str(source.get("evidence") or source.get("safe_next_step") or ""),
                safe_alternative=str(source.get("safe_next_step") or "./repo-python annex_import.py --help"),
                authority_ceiling=str(source.get("authority_ceiling") or "candidate_authoring"),
                source_refs=[str(item) for item in source.get("source_refs") or []],
                target_files=[str(item) for item in source.get("target_files") or []],
                priority=94 if "receipts" in row_id else 82,
                validation_contract={
                    "commands": [
                        "./repo-python annex_import.py --help",
                        "./repo-python kernel.py --option-surface artifact_projection_debt --band flag --ids "
                        f"{row_id}",
                    ],
                    "acceptance": "Parallel GitHub-import lane is migrated into annex_import.py, marked fixture-only, or deleted after migration.",
                },
            )
        )
    return rows


def _compression_coverage_debt_rows(repo_root: Path) -> list[dict[str, Any]]:
    try:
        from system.lib.integration_not_greenfield_surfaces import build_compression_coverage_rows
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for source in build_compression_coverage_rows(repo_root, band="flag"):
        row_id = str(source.get("row_id") or "unknown")
        if str(source.get("target_kind") or "") == "skills":
            continue
        rows.append(
            _base_debt_row(
                row_id=row_id,
                debt_class=str(source.get("debt_class") or "compression_debt"),
                source_surface="artifact_projection_debt.compression_coverage",
                target_kind=str(source.get("target_kind") or "compression_surface"),
                target_row_id=row_id,
                failure_mode=str(source.get("failure_mode") or "compression_coverage_gap"),
                repair_class=str(source.get("repair_class") or "add_low_band_navigation_contract"),
                claim=str(source.get("claim") or row_id),
                evidence=str(source.get("evidence") or ""),
                safe_alternative=str(source.get("safe_next_step") or "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag"),
                authority_ceiling=str(source.get("authority_ceiling") or "candidate_authoring"),
                source_refs=[str(item) for item in source.get("source_refs") or []],
                target_files=[str(item) for item in source.get("target_files") or []],
                priority=83,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --option-surface skill_compression_debt --band cluster_flag",
                        "./repo-python kernel.py --option-surface authoring_contracts --band flag",
                        "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
                    ],
                    "acceptance": "Coverage gap is repaired in the owning standard/surface or remains visible as bounded debt.",
                },
            )
        )
    return rows


def _authoring_contract_debt_rows(repo_root: Path) -> list[dict[str, Any]]:
    try:
        from system.lib.integration_not_greenfield_surfaces import build_authoring_contract_rows
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for source in build_authoring_contract_rows(repo_root, band="flag"):
        if not source.get("coverage_gaps") and not str(source.get("source_authority") or "").startswith("unclear"):
            continue
        row_id = _safe_row_id("authoring_contract", source.get("row_id") or source.get("artifact_id") or "unknown")
        rows.append(
            _base_debt_row(
                row_id=row_id,
                debt_class="authoring_debt",
                source_surface="authoring_contracts",
                target_kind=str(source.get("artifact_category") or "doctrine_registry"),
                target_row_id=str(source.get("artifact_id") or source.get("row_id") or "unknown"),
                failure_mode="missing_or_unclear_authoring_contract",
                repair_class="surface_authoring_contract",
                claim=f"{source.get('artifact_id')} lacks a confirmed apply-lane authoring contract.",
                evidence=f"source_authority={source.get('source_authority')}; coverage_gaps={source.get('coverage_gaps')}",
                safe_alternative=str(source.get("safe_next_step") or "./repo-python kernel.py --option-surface authoring_contracts --band flag"),
                authority_ceiling="candidate_authoring",
                source_refs=[str(item) for item in source.get("source_refs") or []],
                target_files=[str(source.get("artifact_path") or "")],
                priority=88,
                validation_contract={
                    "commands": [
                        "./repo-python kernel.py --option-surface authoring_contracts --band flag",
                        "./repo-python tools/meta/factory/raw_seed_apply_loop.py --help",
                    ],
                    "acceptance": "Registry names a confirmed existing apply lane, or the coverage gap remains explicit before any new CLI is authored.",
                },
            )
        )
    return rows


def _status_blackboard_ttl(status: Mapping[str, Any]) -> int:
    candidates = [
        status.get("blackboard_claim_ttl_seconds"),
        (status.get("effective_scheduler") or {}).get("blackboard_claim_ttl_seconds")
        if isinstance(status.get("effective_scheduler"), Mapping)
        else None,
        (status.get("governor") or {}).get("blackboard_claim_ttl_seconds")
        if isinstance(status.get("governor"), Mapping)
        else None,
    ]
    governor = status.get("governor")
    if isinstance(governor, Mapping):
        effective_scheduler = governor.get("effective_scheduler")
        if isinstance(effective_scheduler, Mapping):
            candidates.append(effective_scheduler.get("blackboard_claim_ttl_seconds"))
    for candidate in candidates:
        try:
            value = int(candidate)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return _DEFAULT_BLACKBOARD_CLAIM_TTL_SECONDS


def _claim_stale_reasons(claim: Mapping[str, Any], *, now: datetime, ttl_seconds: int) -> list[str]:
    reasons: list[str] = []
    status = str(claim.get("status") or "")
    if status in {"closed", "expired"}:
        reasons.append(f"status={status}")
    expiry = _to_dt(claim.get("claim_expires_at"))
    if expiry and expiry < now:
        reasons.append("claim_expires_at_elapsed")
    last_heartbeat_at = _to_dt(claim.get("last_heartbeat_at"))
    if last_heartbeat_at and ttl_seconds > 0 and (now - last_heartbeat_at).total_seconds() > ttl_seconds:
        reasons.append("last_heartbeat_at_older_than_live_ttl")
    updated_at = _to_dt(claim.get("updated_at"))
    if updated_at and ttl_seconds > 0 and (now - updated_at).total_seconds() > ttl_seconds:
        reasons.append("updated_at_older_than_live_ttl")
    freshness = str(claim.get("claim_freshness") or "")
    if freshness and freshness != "active_fresh":
        reasons.append(f"claim_freshness={freshness}")
    return sorted(dict.fromkeys(reasons))


def _transaction_claim_debt_row(
    *,
    claim_id: str,
    reasons: Sequence[str],
    evidence: str,
    source_surface: str,
    priority: int = 96,
) -> dict[str, Any]:
    return _base_debt_row(
        row_id=_safe_row_id("transaction", "active_agent_claim", claim_id),
        debt_class="transaction_debt",
        source_surface=source_surface,
        target_kind="coordination_claim",
        target_row_id=claim_id,
        failure_mode="stale_active_claim_treated_as_authority",
        repair_class="claim_freshness_classification",
        claim="Active-agent claim is present but heartbeat/freshness does not justify blocking local work.",
        evidence=evidence,
        safe_alternative="./metabolism status --json | jq '.counts,.active_agents,.collisions,.stale_claims'",
        source_refs=[str(_METABOLISM_BLACKBOARD), str(_METABOLISM_STATUS)],
        target_files=[str(_METABOLISM_BLACKBOARD), str(_METABOLISM_STATUS)],
        priority=priority,
        expected_patch_shape={
            **_default_expected_patch_shape([]),
            "kind": "claim_freshness_receipt_or_cleanup_patch",
            "claim_id": claim_id,
            "stale_reasons": list(reasons),
            "blackboard_mutation_authorized": False,
        },
        validation_contract={
            "commands": [
                "./metabolism status --json | jq '.counts,.active_agents,.collisions,.stale_claims'",
                "./repo-python kernel.py --option-surface artifact_projection_debt --band flag",
            ],
            "acceptance": (
                "Only active_fresh claims with live heartbeats/collisions can constrain work; "
                "stale claims remain visible as expired/superseded history, not active authority."
            ),
        },
    )


def _transaction_claim_rows(repo_root: Path) -> list[dict[str, Any]]:
    blackboard = _load_json(repo_root / _METABOLISM_BLACKBOARD)
    if not blackboard:
        return []
    status = _load_json(repo_root / _METABOLISM_STATUS)
    generated_at = _to_dt(blackboard.get("generated_at")) or _to_dt(status.get("generated_at")) or datetime.now(timezone.utc)
    ttl_seconds = _status_blackboard_ttl(status)
    claims = blackboard.get("active_agents")
    if not isinstance(claims, list):
        return []
    rows: list[dict[str, Any]] = []
    emitted_claim_ids: set[str] = set()
    active_claim_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        claim_id = str(claim.get("id") or f"{claim.get('agent_surface') or 'agent'}:{claim.get('session_id') or 'unknown'}")
        active_claim_ids.add(claim_id)
        reasons = _claim_stale_reasons(claim, now=generated_at, ttl_seconds=ttl_seconds)
        if not reasons:
            continue
        emitted_claim_ids.add(claim_id)
        rows.append(
            _transaction_claim_debt_row(
                claim_id=claim_id,
                reasons=reasons,
                source_surface="metabolism.blackboard.active_agents",
                evidence=(
                    f"claim_id={claim_id}; ttl_seconds={ttl_seconds}; reasons={reasons}; "
                    f"last_heartbeat_at={claim.get('last_heartbeat_at')}; updated_at={claim.get('updated_at')}; "
                    f"claim_expires_at={claim.get('claim_expires_at')}"
                ),
            )
        )
    temporal_claims = blackboard.get("temporal_claims")
    if not isinstance(temporal_claims, list):
        return rows
    stale_states = {"stale", "expired", "contradicted", "superseded"}
    for temporal_claim in temporal_claims:
        if not isinstance(temporal_claim, Mapping):
            continue
        source_claim_id = str(temporal_claim.get("source_claim_id") or "")
        if not source_claim_id or source_claim_id not in active_claim_ids or source_claim_id in emitted_claim_ids:
            continue
        freshness_state = str(temporal_claim.get("freshness_state") or "")
        if freshness_state not in stale_states:
            continue
        reasons = [
            f"temporal_claim_freshness={freshness_state}",
            f"temporal_claim_id={temporal_claim.get('claim_id')}",
        ]
        emitted_claim_ids.add(source_claim_id)
        rows.append(
            _transaction_claim_debt_row(
                claim_id=source_claim_id,
                reasons=reasons,
                source_surface="metabolism.blackboard.temporal_claims",
                evidence=(
                    f"source_claim_id={source_claim_id}; freshness_state={freshness_state}; "
                    f"valid_at={temporal_claim.get('valid_at')}; invalid_at={temporal_claim.get('invalid_at')}; "
                    f"expired_at={temporal_claim.get('expired_at')}; superseded_by={temporal_claim.get('superseded_by')}"
                ),
                priority=95,
            )
        )
    return rows


def _navigation_metabolism_rows(repo_root: Path) -> list[dict[str, Any]]:
    if not (repo_root / "system/lib/navigation_metabolism_ledger.py").is_file():
        return []
    try:
        from system.lib import navigation_metabolism_ledger as ledger
    except Exception:
        return []

    sources: list[Mapping[str, Any]] = []
    try:
        sources.extend(ledger._quick_projection_debt_rows())  # noqa: SLF001 - bounded composer input.
        sources.extend(ledger._quick_authoring_debt_rows(repo_root))  # noqa: SLF001 - bounded composer input.
        sources.extend(ledger._layer_sprawl_rows(ledger._route_lifecycle_rows()))  # noqa: SLF001
        sources.extend(ledger._actor_delivery_debt_rows(ledger._actor_delivery_receipt(repo_root)))  # noqa: SLF001
    except Exception:
        return []

    wanted = {"projection_debt", "authoring_debt", "actor_delivery_debt", "layer_sprawl_debt"}
    rows: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        debt_class = str(source.get("debt_class") or "")
        if debt_class not in wanted:
            continue
        debt_id = str(source.get("debt_id") or source.get("route_id") or source.get("title") or "unknown")
        row = _base_debt_row(
            row_id=_safe_row_id("navigation_metabolism", debt_id),
            debt_class=debt_class,
            source_surface=str(source.get("source_surface") or "navigation_metabolism_ledger"),
            target_kind=str(source.get("artifact_kind") or "navigation_route"),
            target_row_id=str(source.get("artifact_id") or source.get("route_id") or debt_id),
            failure_mode=str(source.get("title") or debt_id),
            repair_class=str(source.get("repair_class") or "repair_projection_contract"),
            claim=str(source.get("title") or debt_id),
            evidence=str(source.get("evidence") or ""),
            safe_alternative=str(source.get("safe_alternative") or source.get("better_first_surface") or ""),
            source_refs=["system/lib/navigation_metabolism_ledger.py"],
            target_files=[str(path) for path in list(source.get("target_files") or [])],
            priority=int(source.get("priority") or 50),
            validation_contract={
                "commands": [
                    "./repo-python kernel.py --navigation-metabolism \"artifact projection debt executable grammar metabolism\" --metabolism-profile quick --context-budget 5000",
                    "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
                ],
                "acceptance": "Original navigation metabolism debt is repaired, deferred, or represented as a bounded row job.",
            },
        )
        for key in ("active_debt", "advisory_only", "library_reference_only"):
            if key in source:
                row[key] = source.get(key)
        rows.append(row)
    return rows[:18]


def _operation_for(row: Mapping[str, Any]) -> str:
    repair_class = str(row.get("repair_class") or "")
    debt_class = str(row.get("debt_class") or "")
    failure_mode = str(row.get("failure_mode") or "")
    if debt_class == "parallel_lane_debt":
        return "converge_parallel_lane"
    if "authoring_contract" in repair_class:
        return "repair_authoring_contract"
    if debt_class == "transaction_debt" or "claim_freshness" in repair_class:
        return "repair_transaction_claim_freshness"
    if "compression" in repair_class:
        return "repair_compression_contract"
    if "lifecycle" in repair_class or debt_class == "layer_sprawl_debt":
        return "repair_route_lifecycle"
    if "zero_row" in failure_mode or "missing_rows" in repair_class or debt_class == "population_debt":
        return "populate_missing_rows"
    return "repair_projection_contract"


def _sorted_flag_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("row_id") or "")
        if row_id and row_id not in unique:
            unique[row_id] = dict(row)
    return sorted(
        unique.values(),
        key=lambda row: (-int(row.get("priority") or 0), str(row.get("debt_class") or ""), str(row.get("row_id") or "")),
    )


def _flag_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_projection_gap_rows(repo_root))
    rows.extend(_zero_row_population_rows(repo_root))
    rows.extend(_skill_compression_cluster_rows(repo_root))
    rows.extend(_annex_import_convergence_debt_rows(repo_root))
    rows.extend(_compression_coverage_debt_rows(repo_root))
    rows.extend(_authoring_contract_debt_rows(repo_root))
    rows.extend(_navigation_training_behavior_rows())
    rows.extend(_annex_currentness_rows(repo_root))
    rows.extend(_transaction_claim_rows(repo_root))
    rows.extend(_navigation_metabolism_rows(repo_root))
    return _sorted_flag_rows(rows)


def _cluster_rows(flag_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for row in flag_rows:
        key = (str(row.get("debt_class") or "unknown"), str(row.get("repair_class") or "unknown"))
        groups.setdefault(key, []).append(row)

    cluster_rows: list[dict[str, Any]] = []
    ranked_groups = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    omitted_group_count = max(0, len(ranked_groups) - 12)
    for (debt_class, repair_class), rows in ranked_groups[:12]:
        top_ids = [str(row.get("row_id") or "") for row in rows[:8]]
        cluster_id = f"{debt_class}:{repair_class}"
        cluster_rows.append(
            {
                "row_id": cluster_id,
                "artifact_kind": "artifact_projection_debt_cluster",
                "band": "cluster_flag",
                "cluster_id": cluster_id,
                "debt_class": debt_class,
                "repair_class": repair_class,
                "count": len(rows),
                "source_surfaces": sorted({str(row.get("source_surface") or "") for row in rows}),
                "target_kinds": sorted({str(row.get("target_kind") or "") for row in rows}),
                "top_ids": top_ids,
                "claim": f"{debt_class}/{repair_class}: {len(rows)} rows of executable grammar pressure.",
                "drilldown_command": (
                    "./repo-python kernel.py --option-surface artifact_projection_debt "
                    f"--band flag --ids {','.join(top_ids)}"
                ),
                "row_job_command": "./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
                "omission_receipt": {
                    "omitted": [
                        "full debt row cards outside top_ids",
                        "raw source audit bodies",
                        "provider receipt payloads",
                        f"{omitted_group_count} lower-priority clusters",
                    ],
                    "reason": "cluster_flag is the laboratory-safe contents page; cards and row jobs are explicit drilldowns.",
                },
            }
        )
    return cluster_rows


def _card_row(row: Mapping[str, Any]) -> dict[str, Any]:
    card = dict(row)
    card["band"] = "card"
    card["operation"] = _operation_for(row)
    card["bounded_row_job"] = _row_job_for_debt_row(row, index=1)
    ladder = [
        "./repo-python kernel.py --option-surface system_microcosm --band flag",
        "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
        str(row.get("drilldown_command") or ""),
        "./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
        "state/compute_workers/receipts/<receipt>.json or state/compute_workers/row_patches/<patch>.json",
    ]
    card["system_laboratory_ladder"] = ladder
    card["system_microcosm_ladder"] = ladder
    card["omission_receipt"] = {
        "omitted": [
            "full source audit packet",
            "raw provider output",
            "direct source patch",
        ],
        "reason": "The card exposes one repair pressure and its candidate row job; authority remains with validators/promoters.",
    }
    return card


def build_artifact_projection_debt_rows(repo_root: Path | str, *, band: str = "flag") -> list[dict[str, Any]]:
    root = Path(repo_root)
    flag_rows = _flag_rows(root)
    if band == "cluster_flag":
        return _cluster_rows(flag_rows)
    if band == "card":
        return [_card_row(row) for row in flag_rows]
    return flag_rows


def _row_job_for_debt_row(row: Mapping[str, Any], *, index: int) -> dict[str, Any]:
    row_id = str(row.get("row_id") or f"row_{index:03d}")
    source_fingerprint = _short_hash(
        [
            row_id,
            row.get("claim"),
            row.get("evidence"),
            row.get("repair_class"),
            json.dumps(row.get("source_refs") or [], sort_keys=True),
        ],
        length=24,
    )
    job_hash = _short_hash([row_id, source_fingerprint])
    return {
        "job_id": f"rowjob_artifact_projection_debt_{index:03d}_{job_hash[:8]}",
        "source_pressure": {
            "kind": KIND_ID,
            "source_command": "./repo-python kernel.py --option-surface artifact_projection_debt --band flag",
            "source_surface": row.get("source_surface"),
            "finding_kind": row.get("debt_class"),
            "finding_message": row.get("claim"),
        },
        "target_row_id": row_id,
        "target_row_kind": str(row.get("target_kind") or KIND_ID),
        "operation": _operation_for(row),
        "input_band": "artifact_projection_debt.flag",
        "routed_neighborhood": {
            "debt_class": row.get("debt_class"),
            "repair_class": row.get("repair_class"),
            "target_kind": row.get("target_kind"),
            "target_row_id": row.get("target_row_id"),
            "source_surface": row.get("source_surface"),
            "safe_alternative": row.get("safe_alternative"),
            "source_refs": row.get("source_refs") or [],
        },
        "source_fingerprint": source_fingerprint,
        "authority_ceiling": str(row.get("authority_ceiling") or "candidate_authoring"),
        "worker_surface": "type_a_or_provider_row_patch_only",
        "expected_patch_shape": row.get("expected_patch_shape") or _default_expected_patch_shape(row.get("target_files") or []),
        "validation_contract": row.get("validation_contract") or _default_validation_contract(),
        "cache_key_fields": [
            "schema_version",
            "operation",
            "target_row_id",
            "source_fingerprint",
            "authority_ceiling",
        ],
        "promotion_gate": row.get("promotion_gate") or _default_promotion_gate(),
        "receipt_fields": [
            "job_id",
            "source_fingerprint",
            "operation",
            "candidate_patch_ref",
            "validation_result",
            "promotion_state",
            "rejection_or_deferral_reason",
        ],
        "navigation_boundary": {
            "read_path": "Start at the legacy system_microcosm Laboratory/control view, drill to artifact_projection_debt cluster_flag, then this row job.",
            "write_path": "Providers may emit receipts or row_patches only; source mutation requires a separate promoted controller pass.",
            "non_goals": [
                "no direct doctrine mutation",
                "no raw-seed rewrite",
                "no generated projection marked authoritative before validation",
            ],
        },
    }


def build_artifact_projection_debt_row_jobs(
    repo_root: Path | str,
    *,
    limit: int = 15,
) -> dict[str, Any]:
    root = Path(repo_root)
    bounded_limit = max(1, int(limit or 15))
    rows = build_artifact_projection_debt_rows(root, band="flag")[:bounded_limit]
    row_jobs = [_row_job_for_debt_row(row, index=index) for index, row in enumerate(rows, start=1)]
    operation_counts: Counter[str] = Counter(str(job.get("operation") or "unknown") for job in row_jobs)
    return {
        "kind": "metabolism_row_jobs",
        "schema_version": "metabolism_row_job_packet_v0",
        "generated_at": _utc_now(),
        "metabolism_class": "executable_grammar_metabolism_over_artifact_projection_debt",
        "authority_ceiling": "candidate_authoring",
        "source": "artifact-projection-debt",
        "system_laboratory": {
            "drilldown_ladder": [
                "system_microcosm (legacy Laboratory/control-view id)",
                "artifact_projection_debt.cluster_flag",
                "artifact_projection_debt.card",
                "metabolism_row_jobs.artifact-projection-debt",
                "receipt_or_row_patch_validation",
            ],
            "first_command": "./repo-python kernel.py --option-surface system_microcosm --band flag",
        },
        "system_microcosm": {
            "compatibility_note": "Legacy key; current meaning is the Laboratory/control view, not public Microcosm.",
            "drilldown_ladder": [
                "system_microcosm (legacy Laboratory/control-view id)",
                "artifact_projection_debt.cluster_flag",
                "artifact_projection_debt.card",
                "metabolism_row_jobs.artifact-projection-debt",
                "receipt_or_row_patch_validation",
            ],
            "first_command": "./repo-python kernel.py --option-surface system_microcosm --band flag",
        },
        "source_audit_summary": {
            "artifact_projection_debt_rows": len(build_artifact_projection_debt_rows(root, band="flag")),
            "cluster_count": len(build_artifact_projection_debt_rows(root, band="cluster_flag")),
        },
        "summary": {
            "row_job_count": len(row_jobs),
            "requested_limit": bounded_limit,
            "selection_strategy": "priority_then_debt_class",
            "operation_counts": dict(sorted(operation_counts.items())),
            "provider_dispatch": "not_dispatched",
            "provider_output_authority": "receipt_or_row_patch_only",
        },
        "row_job_contract_fields": [
            "job_id",
            "source_pressure",
            "target_row_id",
            "target_row_kind",
            "operation",
            "input_band",
            "routed_neighborhood",
            "source_fingerprint",
            "authority_ceiling",
            "worker_surface",
            "expected_patch_shape",
            "validation_contract",
            "cache_key_fields",
            "promotion_gate",
            "receipt_fields",
            "navigation_boundary",
        ],
        "row_jobs": row_jobs,
        "next_bounded_move": "Choose one row job, emit a receipt/row_patch candidate, validate, then promote or reject.",
    }


def build_system_microcosm_rows(repo_root: Path | str, *, band: str = "flag") -> list[dict[str, Any]]:
    flag_rows = build_artifact_projection_debt_rows(repo_root, band="flag")
    cluster_rows = build_artifact_projection_debt_rows(repo_root, band="cluster_flag")
    row = {
        "row_id": "executable_grammar_metabolism_v0",
        "artifact_kind": SYSTEM_MICROCOSM_KIND_ID,
        "band": "flag",
        "title": "Executable Grammar Laboratory Compatibility View v0",
        "claim": "The legacy system_microcosm kind is a Laboratory/control-view compatibility ladder over executable grammar, not public Microcosm product authority.",
        "compatibility_boundary": {
            "legacy_kind_id": SYSTEM_MICROCOSM_KIND_ID,
            "current_public_microcosm_authority": [
                "codex/standards/std_microcosm.json",
                "codex/doctrine/paper_modules/microcosm_substrate.md",
                "microcosm-substrate/atlas/entry_packet.json",
            ],
            "not_public_product_authority": True,
        },
        "layers": {
            "grammar": "standards",
            "projection": "kind_atlas / option surfaces / Rosetta",
            "metabolism": "audits / artifact_projection_debt / row jobs",
            "worker": "providers / agents / receipts / row_patches",
            "proof": "validation / promotion / commits",
            "transaction": "worktrees / claims / missions",
        },
        "artifact_projection_debt": {
            "flag_rows": len(flag_rows),
            "cluster_rows": len(cluster_rows),
            "cluster_command": "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
        },
        "drilldown_ladder": [
            "./repo-python kernel.py --option-surface system_microcosm --band flag",
            "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
            "./repo-python kernel.py --option-surface artifact_projection_debt --band card --ids <debt_row_id>",
            "./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
            "state/compute_workers/receipts/<receipt>.json or state/compute_workers/row_patches/<patch>.json",
        ],
        "drilldown_command": "./repo-python kernel.py --option-surface system_microcosm --band card --ids executable_grammar_metabolism_v0",
        "evidence_command": "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
    }
    if band == "card":
        row = {
            **row,
            "band": "card",
            "invariant": "A first-contact control view must show the organism before any high-cardinality debt surface expands.",
            "compression_budget": {
                "first_band_goal": "laboratory control view, not dump",
                "artifact_projection_debt_cluster_limit": len(cluster_rows),
                "raw_debt_rows_hidden_until_drilldown": True,
            },
            "proof_commands": [
                "./repo-python kernel.py --option-surface system_microcosm --band flag",
                "./repo-python kernel.py --option-surface artifact_projection_debt --band cluster_flag",
                "./repo-python kernel.py --metabolism-row-jobs artifact-projection-debt --limit 5",
            ],
            "omission_receipt": {
                "omitted": [
                    "all debt cards",
                    "full source audits",
                    "provider payloads",
                    "commit bodies",
                ],
                "reason": "The legacy Laboratory/control view proves the russian-doll ladder; public Microcosm product authority lives in std_microcosm, microcosm_substrate, and the public entry packet.",
            },
        }
    return [row]


__all__ = [
    "KIND_ID",
    "SYSTEM_MICROCOSM_KIND_ID",
    "SCHEMA_VERSION",
    "build_artifact_projection_debt_rows",
    "build_artifact_projection_debt_row_jobs",
    "build_system_microcosm_rows",
]
