"""Clusterability audit for high-cardinality option surfaces.

This is a narrow input to the navigation metabolism ledger. It measures the
current high-cardinality option surfaces, checks whether a cluster_flag adapter
already exists, and classifies missing adapters by whether stable grouping keys
are already present in the governing standard or generated projection.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.kind_atlas import build_kind_atlas
from system.lib.standard_option_surface import build_option_surface

HIGH_CARDINALITY_THRESHOLD = 80

_ROUTE_SPECIFIC_CLUSTER_COMMANDS = {
    "derived_facts": {
        "command": "./repo-python kernel.py --facts --band cluster_flag",
        "grouping_keys_available": ["tag", "facet"],
        "grouping_key_provenance": "facts_navigation_route",
    }
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> int:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    return len(text.encode("utf-8"))


def _budget_relation(byte_count: int | None, budget_bytes: int) -> str:
    if byte_count is None:
        return "unknown"
    if byte_count > budget_bytes:
        return "exceeds_context_budget"
    if byte_count > int(budget_bytes * 0.6):
        return "large_but_within_budget"
    return "within_budget"


def _compact_id(row: Mapping[str, Any]) -> str:
    for key in (
        "standard_id",
        "component_id",
        "principle_id",
        "pattern_id",
        "skill_id",
        "slug",
        "file_id",
        "scope_id",
    ):
        value = row.get(key)
        if value:
            return str(value)
    row_id = str(row.get("row_id") or "")
    if ":" in row_id:
        return row_id.split(":", 1)[1].split("::", 1)[0]
    return row_id


def _group_value(kind_id: str, row: Mapping[str, Any]) -> str:
    if kind_id == "standards":
        return str(row.get("group") or "missing")
    if kind_id == "principles":
        return str(row.get("type") or "untyped")
    if kind_id == "frontend_components":
        path = str(row.get("path") or row.get("source_ref") or "missing")
        if path.startswith("system/server/ui/src/"):
            parts = path.split("/")
            if len(parts) > 5:
                return "/".join(parts[:5])
        return path.rsplit("/", 1)[0] if "/" in path else path
    if kind_id == "annex_patterns":
        return str(row.get("annex_pattern_cluster_key") or "unrouted")
    if kind_id == "annex_distillation_patterns":
        return str(row.get("annex_slug") or "missing")
    return "missing"


def _candidate_grouping(kind_id: str) -> dict[str, Any] | None:
    candidates = {
        "standards": {
            "grouping_keys_available": ["group"],
            "grouping_key_provenance": "generated_standard_index",
            "first_safe_repair": "Add standards.cluster_flag grouped by standards_registry group / source directory.",
            "repair_class": "cluster_flag_adapter_safe_now",
            "tests_to_add": [
                "standards.cluster_flag emits group rows before row expansion",
                "CLI standards --band flag redirects to cluster_flag unless --ids is explicit",
            ],
        },
        "principles": {
            "grouping_keys_available": ["type", "scope"],
            "grouping_key_provenance": "authored",
            "first_safe_repair": "Promote the existing principles type_groups metadata into principles.cluster_flag.",
            "repair_class": "cluster_flag_adapter_safe_now",
            "tests_to_add": [
                "principles.cluster_flag emits type rows",
                "principles all-row flag remains explicit-id-only first-contact debt",
            ],
        },
        "frontend_components": {
            "grouping_keys_available": ["path", "classification_confidence", "declaration_kind"],
            "grouping_key_provenance": "generated_standard_index",
            "first_safe_repair": "Add frontend_components.cluster_flag grouped by source directory, carrying confidence and declaration counts.",
            "repair_class": "cluster_flag_adapter_safe_now",
            "tests_to_add": [
                "frontend_components.cluster_flag emits source-directory rows",
                "card drilldown by component_id remains available",
            ],
        },
        "annex_patterns": {
            "grouping_keys_available": [
                "annex_pattern_cluster_key",
                "annex_catalog.routing_summary.problem_spaces[0]",
            ],
            "grouping_key_provenance": "annex_catalog_generated_routing_summary",
            "first_safe_repair": "Add annex_patterns.cluster_flag grouped by the catalog routing_summary primary problem_space, retaining an unrouted bucket for missing controlled routing.",
            "repair_class": "cluster_flag_adapter_safe_now",
            "tests_to_add": [
                "annex_patterns.cluster_flag emits problem-space rows under budget",
                "CLI annex_patterns --band flag redirects to cluster_flag unless --ids is explicit",
            ],
        },
        "annex_distillation_patterns": {
            "grouping_keys_available": ["annex_slug", "pattern_id", "axis", "adoption_status"],
            "grouping_key_provenance": "generated_standard_index",
            "first_safe_repair": "Add annex_distillation_patterns.cluster_flag grouped by annex_slug from distillation.json.",
            "repair_class": "cluster_flag_adapter_safe_now",
            "tests_to_add": [
                "annex_distillation_patterns.cluster_flag emits annex_slug rows under budget",
                "CLI annex_distillation_patterns --band flag redirects to cluster_flag unless --ids is explicit",
            ],
        },
    }
    return candidates.get(kind_id)


def _candidate_cluster_stats(
    *,
    kind_id: str,
    rows: list[Mapping[str, Any]],
    budget_bytes: int,
) -> dict[str, Any] | None:
    candidate = _candidate_grouping(kind_id)
    if candidate is None:
        return None
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_group_value(kind_id, row)].append(row)
    cluster_rows: list[dict[str, Any]] = []
    for group_id, group_rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        top_ids = [_compact_id(row) for row in group_rows[:6] if _compact_id(row)]
        cluster_rows.append(
            {
                "cluster_id": group_id,
                "count": len(group_rows),
                "top_ids": top_ids,
                "drilldown_command": f"./repo-python kernel.py --option-surface {kind_id} --band flag --ids <ids-from-{group_id}>",
            }
        )
    estimated_bytes = _json_bytes({"rows": cluster_rows})
    relation = _budget_relation(estimated_bytes, budget_bytes)
    return {
        "candidate_group_count": len(cluster_rows),
        "candidate_cluster_estimated_bytes": estimated_bytes,
        "candidate_cluster_budget_relation": relation,
        "largest_groups": [
            {"group_id": group_id, "count": len(group_rows)}
            for group_id, group_rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:8]
        ],
    }


def _implemented_cluster_summary(
    *,
    repo_root: Path,
    kind_id: str,
    budget_bytes: int,
) -> dict[str, Any]:
    try:
        payload = build_option_surface(repo_root, kind_id, band="cluster_flag")
    except Exception as exc:  # noqa: BLE001 - audit should keep classifying other kinds
        return {
            "cluster_flag_status": "blocked",
            "cluster_flag_error": f"{type(exc).__name__}: {exc}",
            "cluster_flag_measured_bytes": None,
            "cluster_flag_budget_relation": "unknown",
        }
    byte_count = _json_bytes(payload)
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    summary = payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {}
    summary_grouping_keys = [
        str(item) for item in (summary.get("grouping_keys") or []) if str(item).strip()
    ]
    status = "implemented" if payload.get("profile_status") == "supported" else "blocked"
    return {
        "cluster_flag_status": status,
        "cluster_flag_row_count": len(rows),
        "cluster_flag_measured_bytes": byte_count,
        "cluster_flag_budget_relation": _budget_relation(byte_count, budget_bytes),
        "grouping_keys_available": summary_grouping_keys
        or sorted(
            {
                str(key)
                for row in rows
                if isinstance(row, Mapping)
                for key in (row.get("grouping_keys") or [])
            }
        ),
    }


def build_navigation_clusterability_audit(
    repo_root: Path | str,
    *,
    context_budget: int = 12000,
    measure_all_rows: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    budget_bytes = budget * 4
    atlas = build_kind_atlas(root, band="card")
    atlas_rows = [dict(row) for row in atlas.get("rows", []) if isinstance(row, Mapping)]
    high_cardinality = [
        row for row in atlas_rows if int(row.get("row_count") or 0) >= HIGH_CARDINALITY_THRESHOLD
    ]

    rows: list[dict[str, Any]] = []
    for atlas_row in high_cardinality:
        kind_id = str(atlas_row.get("kind_id") or "")
        bands = [str(item) for item in atlas_row.get("bands") or []]
        flag_payload: dict[str, Any] | None = None
        flag_rows: list[Mapping[str, Any]] = []
        all_row_bytes: int | None = None
        flag_error: str | None = None
        if measure_all_rows:
            try:
                flag_payload = build_option_surface(root, kind_id, band="flag")
                all_row_bytes = _json_bytes(flag_payload)
                flag_rows = [
                    row for row in (flag_payload.get("rows") or []) if isinstance(row, Mapping)
                ]
            except Exception as exc:  # noqa: BLE001 - audit should return row-level debt
                flag_error = f"{type(exc).__name__}: {exc}"

        implemented = "cluster_flag" in bands
        row: dict[str, Any] = {
            "kind_id": kind_id,
            "row_count": int(atlas_row.get("row_count") or 0),
            "current_bands": bands,
            "governing_standard": list(atlas_row.get("governing_standard_refs") or []),
            "source_projection": list(atlas_row.get("projection_refs") or []),
            "all_row_flag_measured_bytes": all_row_bytes,
            "all_row_flag_budget_relation": _budget_relation(all_row_bytes, budget_bytes),
            "all_row_flag_error": flag_error,
        }

        route_specific = _ROUTE_SPECIFIC_CLUSTER_COMMANDS.get(kind_id)
        if implemented and route_specific and not atlas_row.get("option_surface_command"):
            row.update(
                {
                    "cluster_flag_status": "implemented",
                    "cluster_flag_row_count": None,
                    "cluster_flag_measured_bytes": None,
                    "cluster_flag_budget_relation": "route_specific",
                    "grouping_keys_available": route_specific["grouping_keys_available"],
                    "grouping_key_provenance": route_specific["grouping_key_provenance"],
                    "first_safe_repair": "No option-surface cluster adapter repair needed; use the route-specific cluster command.",
                    "repair_class": "not_needed",
                    "safe_alternative": route_specific["command"],
                }
            )
        elif implemented and not measure_all_rows:
            row.update(
                {
                    "cluster_flag_status": "implemented_unmeasured",
                    "cluster_flag_row_count": None,
                    "cluster_flag_measured_bytes": None,
                    "cluster_flag_budget_relation": "deferred_by_quick_profile",
                    "grouping_keys_available": ["implemented_adapter_specific"],
                    "grouping_key_provenance": "implemented_adapter_unmeasured",
                    "first_safe_repair": (
                        "No quick-profile cluster adapter repair needed; run --clusterability-audit "
                        "for measured cluster_flag payload bytes."
                    ),
                    "repair_class": "not_needed",
                }
            )
        elif implemented:
            row.update(_implemented_cluster_summary(repo_root=root, kind_id=kind_id, budget_bytes=budget_bytes))
            if not row.get("grouping_keys_available"):
                row["grouping_keys_available"] = ["implemented_adapter_specific"]
            row["grouping_key_provenance"] = "implemented_adapter"
            row["first_safe_repair"] = "No cluster_flag adapter repair needed; keep all-row flag as explicit-id/audit-only compatibility."
            row["repair_class"] = "not_needed"
        else:
            candidate = _candidate_grouping(kind_id)
            if candidate is None:
                row.update(
                    {
                        "cluster_flag_status": "blocked",
                        "grouping_keys_available": [],
                        "grouping_key_provenance": "missing",
                        "first_safe_repair": "Define stable grouping keys in the governing standard or generated index before adapter work.",
                        "repair_class": "standard_grouping_key_required",
                        "tests_to_add": ["clusterability audit marks this kind blocked until grouping keys exist"],
                    }
                )
            elif not measure_all_rows:
                row.update(candidate)
                row["cluster_flag_status"] = "analysis_deferred"
                row["repair_class"] = "clusterability_measurement_required"
                row["first_safe_repair"] = (
                    "Run --clusterability-audit with measured all-row payloads before deciding adapter work."
                )
            else:
                row.update(candidate)
                stats = _candidate_cluster_stats(kind_id=kind_id, rows=flag_rows, budget_bytes=budget_bytes)
                if stats:
                    row.update(stats)
                safe = (
                    bool(row.get("grouping_keys_available"))
                    and row.get("candidate_cluster_budget_relation") != "exceeds_context_budget"
                    and not flag_error
                )
                row["cluster_flag_status"] = "safe_now" if safe else "blocked"
                if not safe and row.get("repair_class") == "cluster_flag_adapter_safe_now":
                    row["repair_class"] = "generated_index_group_field_required"
                    row["first_safe_repair"] = (
                        "Existing candidate grouping is not yet budget-safe; add a coarser standard/index-owned group field."
                    )
        rows.append(row)

    status_counts = Counter(str(row.get("cluster_flag_status") or "unknown") for row in rows)
    debt_rows = [
        {
            "debt_id": f"clusterability:{row['kind_id']}",
            "debt_class": "clusterability_debt",
            "priority": 87 if row.get("cluster_flag_status") == "safe_now" else 78,
            "title": (
                f"{row['kind_id']} can safely add cluster_flag"
                if row.get("cluster_flag_status") == "safe_now"
                else f"{row['kind_id']} needs upstream grouping before cluster_flag"
            ),
            "evidence": (
                f"row_count={row.get('row_count')}; all_row_bytes={row.get('all_row_flag_measured_bytes')}; "
                f"grouping_keys={row.get('grouping_keys_available')}; candidate_cluster_bytes={row.get('candidate_cluster_estimated_bytes')}"
            ),
            "repair_class": row.get("repair_class"),
            "artifact_kind": row.get("kind_id"),
            "target_files": [
                "system/lib/standard_option_surface.py",
                "system/lib/kernel/commands/navigate.py",
                "system/lib/navigation_surface_audit.py",
            ],
            "tests": list(row.get("tests_to_add") or []),
            "source_surface": "--clusterability-audit",
            "safe_alternative": (
                f"./repo-python kernel.py --option-surface {row['kind_id']} --band cluster_flag"
                if row.get("cluster_flag_status") in {"implemented", "safe_now"}
                else row.get("first_safe_repair")
            ),
        }
        for row in rows
        if row.get("cluster_flag_status") in {"safe_now", "blocked"}
    ]

    return {
        "kind": "navigation_clusterability_audit",
        "schema_version": "navigation_clusterability_audit_v0",
        "generated_at": _utc_now(),
        "budget": {
            "context_budget_tokens": budget,
            "budget_bytes_estimate": budget_bytes,
            "measure_all_rows": measure_all_rows,
        },
        "summary": {
            "high_cardinality_kind_count": len(rows),
            "implemented_count": status_counts.get("implemented", 0) + status_counts.get("implemented_unmeasured", 0),
            "safe_now_count": status_counts.get("safe_now", 0),
            "blocked_count": status_counts.get("blocked", 0),
            "missing_cluster_adapter_count": sum(
                1 for row in rows if row.get("cluster_flag_status") in {"safe_now", "blocked"}
            ),
            "debt_count": len(debt_rows),
        },
        "rows": rows,
        "debt_rows": debt_rows,
        "next_commands": [
            "./repo-python kernel.py --navigation-metabolism \"clusterability\" --metabolism-profile full --context-budget 12000",
            "./repo-python kernel.py --navigation-surface-audit \"clusterability\" --context-budget 12000",
        ],
        "source_surfaces": [
            "system/lib/navigation_clusterability.py",
            "system/lib/standard_option_surface.py",
            "system/lib/kind_atlas.py",
        ],
    }
