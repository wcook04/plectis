"""
Read-only diagnostics for navigation route size and overflow risk.

The audit is a meta layer over the navigation control plane: it measures a
small, curated set of surfaces in memory, classifies risk against a context
budget, and names bounded replacement commands. It must never print the bulky
payloads it is measuring.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from system.lib.kind_atlas import build_kind_atlas
from system.lib.navigation_context_pack import HIGH_CARDINALITY_THRESHOLD, build_navigation_context_pack
from system.lib.standard_option_surface import build_option_surface


DEFAULT_QUERY = "navigation context compression and command output bloat"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any, *, pretty: bool = True) -> int:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    return len(text.encode("utf-8"))


BOUNDED_ENTRY_PACKET_BUDGET_TOKENS = 12000


def _effective_budget_bytes(*, expectation: str, caller_budget_bytes: int) -> int:
    """Pick the intended budget for the route's contract.

    `bounded_entry` routes have a fixed intended packet size (~12000 tokens).
    Their contract must NOT be measured against the caller's trim budget,
    because the caller's budget reflects the metabolism ledger's own packet
    target — a different packet with different intent. Mixing them is a
    category error and produces false `violates_entry_contract` rows whenever
    a small caller budget is used (kernel CLI default --context-budget=1400).
    """
    if expectation == "bounded_entry":
        return BOUNDED_ENTRY_PACKET_BUDGET_TOKENS * 4
    return caller_budget_bytes


def _budget_relation(byte_count: int | None, budget_bytes: int) -> str:
    if byte_count is None:
        return "unknown"
    if byte_count > budget_bytes:
        return "exceeds_context_budget"
    if byte_count > int(budget_bytes * 0.6):
        return "large_but_within_budget"
    return "within_budget"


def _contract_status(
    *,
    byte_count: int | None,
    budget_bytes: int,
    expectation: str,
    forced: str | None = None,
) -> str:
    if forced:
        return forced
    relation = _budget_relation(byte_count, budget_bytes)
    if expectation == "evidence_or_substrate":
        return "valid_large_surface" if relation == "exceeds_context_budget" else "valid"
    if expectation == "known_unsafe_reference":
        return "violates_entry_contract"
    if expectation == "bounded_entry" and relation == "exceeds_context_budget":
        return "violates_entry_contract"
    if expectation == "contents_page" and relation == "exceeds_context_budget":
        return "contents_page_too_large"
    return "valid"


def _measure_route(
    *,
    route_id: str,
    command: str,
    role: str,
    budget_bytes: int,
    builder: Callable[[], Mapping[str, Any]],
    safe_alternative: str | None = None,
    expectation: str = "bounded_entry",
    forced_contract_status: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    try:
        payload = builder()
    except Exception as exc:  # noqa: BLE001 - diagnostics should keep running
        return {
            "route_id": route_id,
            "command": command,
            "role": role,
            "budget_relation": "unknown",
            "contract_status": "sample_error",
            "contract_expectation": expectation,
            "error": f"{type(exc).__name__}: {exc}",
            "safe_alternative": safe_alternative,
            "notes": notes or [],
        }
    pretty_bytes = _json_bytes(payload, pretty=True)
    compact_bytes = _json_bytes(payload, pretty=False)
    effective_budget_bytes = _effective_budget_bytes(
        expectation=expectation,
        caller_budget_bytes=budget_bytes,
    )
    return {
        "route_id": route_id,
        "command": command,
        "role": role,
        "pretty_json_bytes": pretty_bytes,
        "compact_json_bytes": compact_bytes,
        "estimated_tokens": max(1, (pretty_bytes + 3) // 4),
        "budget_relation": _budget_relation(pretty_bytes, effective_budget_bytes),
        "contract_expectation": expectation,
        "contract_status": _contract_status(
            byte_count=pretty_bytes,
            budget_bytes=effective_budget_bytes,
            expectation=expectation,
            forced=forced_contract_status,
        ),
        "safe_alternative": safe_alternative,
        "notes": notes or [],
    }


def _atlas_rows(repo_root: Path) -> list[dict[str, Any]]:
    atlas = build_kind_atlas(repo_root, band="card")
    return [dict(row) for row in atlas.get("rows", []) if isinstance(row, Mapping)]


def _high_cardinality_rows(atlas_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in atlas_rows:
        kind_id = str(row.get("kind_id") or "")
        row_count = int(row.get("row_count") or 0)
        if row_count < HIGH_CARDINALITY_THRESHOLD:
            continue
        bands = [str(item) for item in row.get("bands") or []]
        cluster_status = "implemented" if "cluster_flag" in bands else "missing"
        default_route = str(row.get("option_surface_command") or "")
        safe_drilldown = (
            default_route
            if cluster_status == "implemented" and "--band cluster_flag" in default_route
            else f"./repo-python kernel.py --option-surface {kind_id} --band cluster_flag"
            if cluster_status == "implemented"
            else row.get("card_command") or row.get("option_surface_command")
        )
        rows.append(
            {
                "kind_id": kind_id,
                "title": row.get("title"),
                "row_count": row_count,
                "cluster_adapter_status": cluster_status,
                "default_route": row.get("option_surface_command"),
                "safe_drilldown": safe_drilldown,
                "risk": (
                    "bounded_by_cluster_flag"
                    if cluster_status == "implemented"
                    else "high_cardinality_unclustered"
                ),
            }
        )
    return rows


def build_navigation_surface_audit(
    repo_root: Path | str,
    *,
    query: str | None = None,
    context_budget: int = 12000,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    budget_bytes = budget * 4
    task_query = str(query or DEFAULT_QUERY)
    atlas_rows = _atlas_rows(root)

    from system.lib.kernel.commands import navigate as _navigate

    try:
        _navigate.state.init(root)
    except Exception:
        pass

    route_map = [
        _measure_route(
            route_id="phase.summary_default",
            command="./repo-python kernel.py --phase",
            role="default phase reentry control packet",
            budget_bytes=budget_bytes,
            builder=lambda: _navigate._phase_output_mode_packet(
                _navigate.KernelNavigation(_navigate.state.REPO_ROOT).build_phase(None),
                output_mode="summary",
            ),
            safe_alternative="./repo-python kernel.py --phase --warnings-only",
            expectation="bounded_entry",
        ),
        _measure_route(
            route_id="kind_atlas.flag",
            command="./repo-python kernel.py --kind-atlas",
            role="rung-0 artifact-kind map before row expansion",
            budget_bytes=budget_bytes,
            builder=lambda: build_kind_atlas(root, band="flag"),
            safe_alternative="./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            expectation="contents_page",
        ),
        _measure_route(
            route_id="context_pack.semantic_disabled_sample",
            command=f"./repo-python kernel.py --context-pack {json.dumps(task_query)} --context-budget {budget}",
            role="task-conditioned mixed-band composer with semantic routing disabled for deterministic size audit",
            budget_bytes=budget_bytes,
            builder=lambda: build_navigation_context_pack(
                root,
                task_query,
                context_budget=budget,
                include_semantic=False,
            ),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="paper_modules.cluster_flag",
            command="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            role="cluster-level paper-module overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "paper_modules", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="paper_modules.row_flag_all.library",
            command="build_option_surface(repo_root, 'paper_modules', band='flag')",
            role="library-only measurement of the unsafe all-row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "paper_modules", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row paper-module flag to cluster_flag."],
        ),
        _measure_route(
            route_id="standards.cluster_flag",
            command="./repo-python kernel.py --option-surface standards --band cluster_flag",
            role="group-level standards overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "standards", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="standards.row_flag_all.library",
            command="build_option_surface(repo_root, 'standards', band='flag')",
            role="library-only measurement of the unsafe all-standards row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "standards", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface standards --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row standards flag to cluster_flag."],
        ),
        _measure_route(
            route_id="task_ledger.cluster_flag",
            command="./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            role="view-level Task Ledger overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "task_ledger", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="task_ledger.row_flag_all.library",
            command="build_option_surface(repo_root, 'task_ledger', band='flag')",
            role="library-only measurement of the unsafe all-WorkItem row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "task_ledger", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row Task Ledger flag to cluster_flag."],
        ),
        _measure_route(
            route_id="skills.cluster_flag",
            command="./repo-python kernel.py --option-surface skills --band cluster_flag",
            role="family-level all-skills contents page",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "skills", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="skills.row_flag_all.library",
            command="build_option_surface(repo_root, 'skills', band='flag')",
            role="library-only measurement of the unsafe all-skill row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "skills", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface skills --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row skill flag to cluster_flag."],
        ),
        _measure_route(
            route_id="python_files.cluster_flag",
            command="./repo-python kernel.py --option-surface python_files --band cluster_flag",
            role="group-level Python file overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "python_files", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="python_files.row_flag_all.library",
            command="build_option_surface(repo_root, 'python_files', band='flag')",
            role="library-only measurement of the unsafe all-Python-file row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "python_files", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface python_files --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row Python file flag to cluster_flag."],
        ),
        _measure_route(
            route_id="python_scopes.cluster_flag",
            command="./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
            role="group-and-kind-level Python scope overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "python_scopes", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="python_scopes.row_flag_all.library",
            command="build_option_surface(repo_root, 'python_scopes', band='flag')",
            role="library-only measurement of the unsafe all-Python-scope row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "python_scopes", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row Python scope flag to cluster_flag."],
        ),
        _measure_route(
            route_id="frontend_components.cluster_flag",
            command="./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
            role="source-directory-level frontend component overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "frontend_components", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="frontend_components.row_flag_all.library",
            command="build_option_surface(repo_root, 'frontend_components', band='flag')",
            role="library-only measurement of the unsafe all-frontend-component row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "frontend_components", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row frontend component flag to cluster_flag."],
        ),
        _measure_route(
            route_id="principles.cluster_flag",
            command="./repo-python kernel.py --option-surface principles --band cluster_flag",
            role="type-level principle overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "principles", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="principles.row_flag_all.library",
            command="build_option_surface(repo_root, 'principles', band='flag')",
            role="library-only measurement of the unsafe all-principle row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "principles", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface principles --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row principles flag to cluster_flag."],
        ),
        _measure_route(
            route_id="annex_patterns.cluster_flag",
            command="./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            role="problem-space-level annex note overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "annex_patterns", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="annex_patterns.row_flag_all.library",
            command="build_option_surface(repo_root, 'annex_patterns', band='flag')",
            role="library-only measurement of the unsafe all-annex-note row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "annex_patterns", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row annex pattern flag to cluster_flag."],
        ),
        _measure_route(
            route_id="annex_distillation_patterns.cluster_flag",
            command="./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
            role="annex_slug-level extracted annex distillation overview",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "annex_distillation_patterns", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="annex_distillation_patterns.row_flag_all.library",
            command="build_option_surface(repo_root, 'annex_distillation_patterns', band='flag')",
            role="library-only measurement of the unsafe all-annex-distillation row flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "annex_distillation_patterns", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; the CLI redirects all-row annex distillation flag to cluster_flag."],
        ),
        _measure_route(
            route_id="row_patches.cluster_flag",
            command="./repo-python kernel.py --option-surface row_patches --band cluster_flag",
            role="target-facet row-patch contents page",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "row_patches", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="row_patches.row_flag_all.library",
            command="build_option_surface(repo_root, 'row_patches', band='flag')",
            role="library-only measurement of the unsafe all-row-patch flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "row_patches", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface row_patches --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; cluster_flag is the target_facet contents page."],
        ),
        _measure_route(
            route_id="transform_job_receipts.cluster_flag",
            command="./repo-python kernel.py --option-surface transform_job_receipts --band cluster_flag",
            role="task-class provider-receipt contents page",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "transform_job_receipts", band="cluster_flag"),
            safe_alternative=None,
            expectation="contents_page",
        ),
        _measure_route(
            route_id="transform_job_receipts.row_flag_all.library",
            command="build_option_surface(repo_root, 'transform_job_receipts', band='flag')",
            role="library-only measurement of the unsafe all-provider-receipt flag payload",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(root, "transform_job_receipts", band="flag"),
            safe_alternative="./repo-python kernel.py --option-surface transform_job_receipts --band cluster_flag",
            expectation="known_unsafe_reference",
            notes=["Measured in memory only; cluster_flag is the task_class contents page."],
        ),
        _measure_route(
            route_id="paper_modules.row_flag_one",
            command="./repo-python kernel.py --option-surface paper_modules --band flag --ids navigation_hologram_theory",
            role="explicit row-level paper-module flag drilldown",
            budget_bytes=budget_bytes,
            builder=lambda: build_option_surface(
                root,
                "paper_modules",
                band="flag",
                ids=["navigation_hologram_theory"],
            ),
            safe_alternative=None,
            expectation="bounded_entry",
        ),
        _measure_route(
            route_id="paper_module.output_band_flag_browse",
            command="./repo-python kernel.py --paper-module <slug> --output-band flag",
            role="retrofitted command-output flag projection after cluster-first repair",
            budget_bytes=budget_bytes,
            builder=lambda: _navigate.build_paper_module_projection_envelope(band="flag", slug=None),
            safe_alternative="./repo-python kernel.py --paper-module <slug> --output-band card",
            expectation="bounded_entry",
        ),
    ]

    measured_by_id = {row["route_id"]: row for row in route_map}
    paper_all = measured_by_id.get("paper_modules.row_flag_all.library", {})
    paper_cluster = measured_by_id.get("paper_modules.cluster_flag", {})
    findings: list[dict[str, Any]] = []
    if paper_all.get("contract_status") == "violates_entry_contract":
        findings.append(
            {
                "finding_id": "paper_modules_all_flag_over_budget",
                "severity": "high",
                "surface": "paper_modules.row_flag_all",
                "observed_pretty_json_bytes": paper_all.get("pretty_json_bytes"),
                "budget_bytes": budget_bytes,
                "safe_alternative": "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            }
        )
    if int(paper_cluster.get("pretty_json_bytes") or 0) < int(paper_all.get("pretty_json_bytes") or 0):
        findings.append(
            {
                "finding_id": "paper_modules_cluster_flag_compresses_global_overview",
                "severity": "info",
                "cluster_bytes": paper_cluster.get("pretty_json_bytes"),
                "row_flag_all_bytes": paper_all.get("pretty_json_bytes"),
            }
        )
    skills_all = measured_by_id.get("skills.row_flag_all.library", {})
    skills_cluster = measured_by_id.get("skills.cluster_flag", {})
    if skills_all.get("contract_status") == "violates_entry_contract":
        findings.append(
            {
                "finding_id": "skills_all_flag_over_budget",
                "severity": "high",
                "surface": "skills.row_flag_all",
                "observed_pretty_json_bytes": skills_all.get("pretty_json_bytes"),
                "budget_bytes": budget_bytes,
                "safe_alternative": "./repo-python kernel.py --option-surface skills --band cluster_flag",
            }
        )
    if int(skills_cluster.get("pretty_json_bytes") or 0) < int(skills_all.get("pretty_json_bytes") or 0):
        findings.append(
            {
                "finding_id": "skills_cluster_flag_compresses_global_overview",
                "severity": "info",
                "cluster_bytes": skills_cluster.get("pretty_json_bytes"),
                "row_flag_all_bytes": skills_all.get("pretty_json_bytes"),
            }
        )
    for kind_id in (
        "standards",
        "python_files",
        "python_scopes",
        "frontend_components",
        "principles",
        "annex_patterns",
        "annex_distillation_patterns",
        "row_patches",
        "transform_job_receipts",
    ):
        all_rows = measured_by_id.get(f"{kind_id}.row_flag_all.library", {})
        cluster = measured_by_id.get(f"{kind_id}.cluster_flag", {})
        if all_rows.get("contract_status") == "violates_entry_contract":
            findings.append(
                {
                    "finding_id": f"{kind_id}_all_flag_over_budget",
                    "severity": "high",
                    "surface": f"{kind_id}.row_flag_all",
                    "observed_pretty_json_bytes": all_rows.get("pretty_json_bytes"),
                    "budget_bytes": budget_bytes,
                    "safe_alternative": f"./repo-python kernel.py --option-surface {kind_id} --band cluster_flag",
                }
            )
        if int(cluster.get("pretty_json_bytes") or 0) < int(all_rows.get("pretty_json_bytes") or 0):
            findings.append(
                {
                    "finding_id": f"{kind_id}_cluster_flag_compresses_global_overview",
                    "severity": "info",
                    "cluster_bytes": cluster.get("pretty_json_bytes"),
                    "row_flag_all_bytes": all_rows.get("pretty_json_bytes"),
                }
            )

    high_cardinality = _high_cardinality_rows(atlas_rows)
    missing_cluster = [row["kind_id"] for row in high_cardinality if row["cluster_adapter_status"] == "missing"]
    if missing_cluster:
        findings.append(
            {
                "finding_id": "high_cardinality_cluster_adapters_missing",
                "severity": "medium",
                "kinds": missing_cluster,
                "recommendation": "Add cluster_flag adapters or keep these kinds behind context-pack kind_flag signposts plus explicit id drilldown.",
            }
        )

    return {
        "kind": "navigation_surface_audit",
        "schema_version": "navigation_surface_audit_v0",
        "generated_at": _utc_now(),
        "query": task_query,
        "budget": {
            "context_budget_tokens": budget,
            "budget_bytes_estimate": budget_bytes,
            "classification": "budget_relation is measurement only; contract_status decides whether the size violates the surface role",
        },
        "summary": {
            "route_count": len(route_map),
            "budget_exceeds_count": sum(1 for row in route_map if row.get("budget_relation") == "exceeds_context_budget"),
            "contract_violation_count": sum(
                1 for row in route_map if str(row.get("contract_status") or "").startswith("violates_")
            ),
            "high_cardinality_kind_count": len(high_cardinality),
            "missing_cluster_adapter_count": len(missing_cluster),
        },
        "route_map": route_map,
        "high_cardinality_kinds": high_cardinality,
        "findings": findings,
        "next_commands": [
            "./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000",
            "./repo-python kernel.py --option-surface paper_modules --band cluster_flag",
            "./repo-python kernel.py --option-surface standards --band cluster_flag",
            "./repo-python kernel.py --option-surface python_files --band cluster_flag",
            "./repo-python kernel.py --option-surface python_scopes --band cluster_flag",
            "./repo-python kernel.py --option-surface frontend_components --band cluster_flag",
            "./repo-python kernel.py --option-surface principles --band cluster_flag",
            "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            "./repo-python kernel.py --option-surface annex_distillation_patterns --band cluster_flag",
            "./repo-python kernel.py --option-surface row_patches --band cluster_flag",
            "./repo-python kernel.py --option-surface transform_job_receipts --band cluster_flag",
            "./repo-python kernel.py --clusterability-audit --context-budget 12000",
            "./repo-python kernel.py --navigation-surface-audit \"<task>\" --context-budget 12000",
        ],
        "source_surfaces": [
            "system/lib/navigation_context_pack.py",
            "system/lib/standard_option_surface.py",
            "system/lib/kind_atlas.py",
            "system/lib/kernel/commands/navigate.py",
        ],
    }
