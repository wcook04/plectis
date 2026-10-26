#!/usr/bin/env python3
"""Build the Formal Evidence Cell Registry over registered manifests.

This projection is an operational inventory authority for formal-evidence
cells: which manifests are registered, which cell ids exist, which cells may
satisfy paper-module formal-evidence anchors, and what is failure/freshness
state. It does NOT define what a formal evidence cell is (that contract lives
in `codex/standards/std_paper_module.json::formal_evidence_cells`); it does
NOT prove mathematics; it does NOT call providers or update upstream
registries.

Registry semantics:
  - One row per registered manifest with status, fingerprint, cell_count.
  - One row per addressable cell with claim_boundary, receipt_refs,
    work_item_id, status, can_satisfy_paper_module_anchor flag.
  - Validation:
      * every registered manifest path exists;
      * cell_id is globally unique across all registered manifests;
      * every anchor-supplying cell has claim_boundary + receipt_refs +
        work_item_id and status != missing_source;
      * manifest receipt status must be PASS (or an explicit accepted
        downgrade) for cells from that manifest to satisfy anchors.
  - The registry, not std_paper_module, owns the operational inventory.
    std_paper_module remains the constitutional contract authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]

OWNER_ID = "formal_math_evidence_cell_registry_projection"
WORK_ITEM_ID = "cap_quick_mathematics_oracle_prover_evolve_lane_er_8264150e650a"
SCHEMA_VERSION = "formal_math_evidence_cell_registry_v0"
RECEIPT_SCHEMA_VERSION = "formal_math_evidence_cell_registry_receipt_v0"

REGISTRY_PATH = Path(
    "state/formal_math_research_operations/formal_evidence_cell_registry.json"
)
RECEIPT_PATH = Path(
    "state/formal_math_research_operations/formal_evidence_cell_registry_receipt.json"
)
MARKDOWN_PATH = Path(
    "docs/formal_math/generated_formal_evidence_cell_registry.md"
)
EXPERIMENT_RECEIPT_DIR = Path(
    "state/formal_math_research_operations/experiment_receipts"
)

# Source manifest inventory (the only place new pilots add entries).
# Each entry pairs a cell manifest with its receipt.
REGISTERED_MANIFESTS: tuple[dict[str, str], ...] = (
    {
        "manifest_path": (
            "state/formal_math_research_operations/pilots/erdos257_issue217/"
            "formal_evidence_cells.json"
        ),
        "manifest_receipt_path": (
            "state/formal_math_research_operations/pilots/erdos257_issue217/"
            "formal_evidence_cells_receipt.json"
        ),
        "namespace_prefix": "erdos257.issue217.",
        "owner_cap": WORK_ITEM_ID,
    },
)

ACCEPTED_MANIFEST_RECEIPT_STATUSES = {"PASS", "ok"}


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _read_json_if_exists(
    path: str | Path, *, repo_root: Path = REPO_ROOT
) -> dict[str, Any] | None:
    candidate = _repo_path(path, repo_root=repo_root)
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    text = value if isinstance(value, str) else _canonical_json(value)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str, *, repo_root: Path = REPO_ROOT) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def _load_experiment_receipts(
    *, repo_root: Path = REPO_ROOT
) -> dict[str, dict[str, Any]]:
    """Index experiment receipts by source_cell_id.

    Same shape as the queue builder's receipt loader: keyed by source_cell_id
    so the registry can join per-cell execution state without inventing
    timestamps. Deterministic selection when multiple receipts match a cell:
    sort by filename and let the lexicographically-last one win.
    """
    receipt_dir = _repo_path(EXPERIMENT_RECEIPT_DIR, repo_root=repo_root)
    index: dict[str, dict[str, Any]] = {}
    if not receipt_dir.exists():
        return index
    for path in sorted(receipt_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        cid = payload.get("source_cell_id")
        if not isinstance(cid, str):
            continue
        index[cid] = {
            "receipt_path": str(path.relative_to(repo_root)),
            "result_class": payload.get("result_class"),
            "status": payload.get("status"),
            "adapter_id": payload.get("adapter_id"),
            "receipt_sha256": _sha256(payload),
        }
    return index


def _execution_visibility_status(
    *,
    has_action_edge: bool,
    evidence_class: str | None,
    receipt: dict[str, Any] | None,
) -> str:
    """Classify per-cell execution visibility.

    boundary_cells route to boundary_unexecuted or boundary_refused based on
    whether they carry a refusal receipt. Actionable cells route to
    executed_ok / executed_refused / unexecuted_actionable based on the
    presence and status of their latest receipt.
    """
    ec = (evidence_class or "").lower()
    is_boundary = "boundary" in ec or "leakage_audit" in ec
    if is_boundary:
        if receipt is None:
            return "boundary_unexecuted"
        if receipt.get("status") == "REFUSED":
            return "boundary_refused"
        return "boundary_executed"
    if receipt is None:
        return "unexecuted_actionable" if has_action_edge else "no_action_edge_no_receipt"
    status = receipt.get("status")
    if status == "OK":
        return "executed_ok"
    if status == "REFUSED":
        return "executed_refused"
    return f"executed_other:{status}"


def _cell_anchor_present(cell: dict[str, Any]) -> dict[str, bool]:
    receipts = cell.get("receipt_refs")
    return {
        "claim_boundary": bool(cell.get("claim_boundary")),
        "receipt": bool(isinstance(receipts, list) and receipts),
        "work_item": bool(cell.get("work_item_id")),
    }


def build_registry(
    *,
    registered_manifests: tuple[dict[str, str], ...] = REGISTERED_MANIFESTS,
    repo_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build (registry, receipt) pair over registered manifests."""
    manifest_rows: list[dict[str, Any]] = []
    cell_rows: list[dict[str, Any]] = []
    namespace_prefixes: set[str] = set()
    cell_id_to_manifest: dict[str, str] = {}
    duplicate_cell_ids: list[dict[str, str]] = []
    missing_manifest_paths: list[str] = []
    missing_receipt_paths: list[str] = []
    malformed_manifest_paths: list[str] = []
    experiment_receipt_index = _load_experiment_receipts(repo_root=repo_root)

    for entry in registered_manifests:
        m_path = entry["manifest_path"]
        r_path = entry["manifest_receipt_path"]
        namespace_prefix = entry.get("namespace_prefix", "")
        owner_cap = entry.get("owner_cap", "")

        manifest_payload = _read_json_if_exists(m_path, repo_root=repo_root)
        receipt_payload = _read_json_if_exists(r_path, repo_root=repo_root)

        manifest_exists = manifest_payload is not None
        receipt_exists = receipt_payload is not None
        if not manifest_exists:
            missing_manifest_paths.append(m_path)
        else:
            namespace_prefixes.add(namespace_prefix)
        if not receipt_exists:
            missing_receipt_paths.append(r_path)

        receipt_status = (
            (receipt_payload or {}).get("status") if receipt_payload else None
        )
        receipt_status_accepted = (
            receipt_status in ACCEPTED_MANIFEST_RECEIPT_STATUSES
        )

        manifest_status = "ok"
        if not manifest_exists:
            manifest_status = "missing_manifest"
        elif not receipt_exists:
            manifest_status = "missing_receipt"
        elif not receipt_status_accepted:
            manifest_status = f"receipt_status_unaccepted:{receipt_status}"

        cells = (
            (manifest_payload or {}).get("cells", []) if manifest_payload else []
        )
        cell_count_for_manifest = 0
        for cell in cells if isinstance(cells, list) else []:
            if not isinstance(cell, dict):
                continue
            cid = cell.get("cell_id")
            if not isinstance(cid, str) or not cid:
                continue

            if cid in cell_id_to_manifest and cell_id_to_manifest[cid] != m_path:
                duplicate_cell_ids.append(
                    {
                        "cell_id": cid,
                        "first_manifest": cell_id_to_manifest[cid],
                        "duplicate_manifest": m_path,
                    }
                )
                continue
            cell_id_to_manifest[cid] = m_path
            cell_count_for_manifest += 1

            anchors = _cell_anchor_present(cell)
            anchors_complete = all(anchors.values())
            status = cell.get("status") or "evidence_present"
            can_satisfy = bool(
                anchors_complete
                and status != "missing_source"
                and receipt_status_accepted
            )

            next_experiment = cell.get("next_decisive_experiment")
            targets = cell.get("targets")
            target_count = cell.get("target_count")
            has_action_edge = bool(
                next_experiment
                or (isinstance(targets, list) and targets)
                or (isinstance(target_count, int) and target_count > 0)
            )

            latest_experiment = experiment_receipt_index.get(cid)
            execution_visibility_status = _execution_visibility_status(
                has_action_edge=has_action_edge,
                evidence_class=cell.get("evidence_class"),
                receipt=latest_experiment,
            )

            cell_rows.append(
                {
                    "cell_id": cid,
                    "namespace_prefix": namespace_prefix,
                    "manifest_path": m_path,
                    "owner_cap": owner_cap,
                    "status": status,
                    "anchor_classes_present": [
                        name for name, present in anchors.items() if present
                    ],
                    "anchor_classes_missing": [
                        name for name, present in anchors.items() if not present
                    ],
                    "claim_boundary": cell.get("claim_boundary"),
                    "receipt_refs": list(cell.get("receipt_refs") or []),
                    "work_item_id": cell.get("work_item_id"),
                    "evidence_class": cell.get("evidence_class"),
                    "non_claims": list(cell.get("non_claims") or []),
                    "can_satisfy_paper_module_anchor": can_satisfy,
                    "next_decisive_experiment": next_experiment,
                    "targets": targets if isinstance(targets, list) else None,
                    "target_count": target_count,
                    "has_action_edge": has_action_edge,
                    "obligation_node_refs": (
                        list(cell.get("obligation_node_refs") or [])
                        if isinstance(cell.get("obligation_node_refs"), list)
                        else None
                    ),
                    "obligation_node_refs_declared": (
                        bool(cell.get("obligation_node_refs_declared"))
                        if cell.get("obligation_node_refs_declared") is not None
                        else None
                    ),
                    "candidate_obligation_node_refs": (
                        list(cell.get("candidate_obligation_node_refs") or [])
                        if isinstance(
                            cell.get("candidate_obligation_node_refs"), list
                        )
                        else None
                    ),
                    "candidate_obligation_node_ref_reason": cell.get(
                        "candidate_obligation_node_ref_reason"
                    ),
                    "latest_experiment_receipt_ref": (
                        latest_experiment.get("receipt_path")
                        if latest_experiment
                        else None
                    ),
                    "latest_experiment_status": (
                        latest_experiment.get("status")
                        if latest_experiment
                        else None
                    ),
                    "latest_experiment_result_class": (
                        latest_experiment.get("result_class")
                        if latest_experiment
                        else None
                    ),
                    "latest_experiment_adapter_id": (
                        latest_experiment.get("adapter_id")
                        if latest_experiment
                        else None
                    ),
                    "latest_experiment_receipt_sha256": (
                        latest_experiment.get("receipt_sha256")
                        if latest_experiment
                        else None
                    ),
                    "execution_visibility_status": execution_visibility_status,
                }
            )

        manifest_rows.append(
            {
                "manifest_path": m_path,
                "manifest_receipt_path": r_path,
                "namespace_prefix": namespace_prefix,
                "owner_cap": owner_cap,
                "manifest_exists": manifest_exists,
                "receipt_exists": receipt_exists,
                "receipt_status": receipt_status,
                "receipt_status_accepted": receipt_status_accepted,
                "manifest_status": manifest_status,
                "cell_count": cell_count_for_manifest,
                "manifest_sha256": (
                    _sha256(manifest_payload) if manifest_payload is not None else None
                ),
                "receipt_sha256": (
                    _sha256(receipt_payload) if receipt_payload is not None else None
                ),
            }
        )

    can_satisfy_count = sum(
        1 for cell in cell_rows if cell["can_satisfy_paper_module_anchor"]
    )
    cannot_satisfy_count = len(cell_rows) - can_satisfy_count

    execution_receipt_count = sum(
        1 for cell in cell_rows if cell.get("latest_experiment_receipt_ref")
    )
    adapter_backed_cell_count = sum(
        1
        for cell in cell_rows
        if cell.get("execution_visibility_status") == "executed_ok"
    )
    refused_cell_count = sum(
        1
        for cell in cell_rows
        if cell.get("execution_visibility_status")
        in {"executed_refused", "boundary_refused"}
    )
    boundary_cell_count = sum(
        1
        for cell in cell_rows
        if cell.get("execution_visibility_status", "").startswith("boundary_")
    )
    unexecuted_actionable_cell_count = sum(
        1
        for cell in cell_rows
        if cell.get("execution_visibility_status") == "unexecuted_actionable"
    )

    validation_summary = {
        "manifest_count": len(manifest_rows),
        "cell_count": len(cell_rows),
        "namespace_prefix_count": len(namespace_prefixes),
        "can_satisfy_anchor_count": can_satisfy_count,
        "cannot_satisfy_anchor_count": cannot_satisfy_count,
        "duplicate_cell_id_count": len(duplicate_cell_ids),
        "duplicate_cell_ids": duplicate_cell_ids,
        "missing_manifest_count": len(missing_manifest_paths),
        "missing_manifest_paths": missing_manifest_paths,
        "missing_receipt_count": len(missing_receipt_paths),
        "missing_receipt_paths": missing_receipt_paths,
        "malformed_manifest_count": len(malformed_manifest_paths),
        "execution_receipt_count": execution_receipt_count,
        "adapter_backed_cell_count": adapter_backed_cell_count,
        "refused_cell_count": refused_cell_count,
        "boundary_cell_count": boundary_cell_count,
        "unexecuted_actionable_cell_count": unexecuted_actionable_cell_count,
    }

    registry = {
        "schema_version": SCHEMA_VERSION,
        "owner_id": OWNER_ID,
        "work_item_id": WORK_ITEM_ID,
        "claim_boundary": (
            "operational_cell_inventory_not_publication_authority_"
            "not_proof_authority"
        ),
        "authority_posture": (
            "registry_owns_operational_inventory_standard_owns_contract"
        ),
        "anti_claims": [
            "this registry does not claim Erdos #257 is solved",
            "this registry does not turn cell citation into proof authority",
            "this registry does not authorize provider proof generation",
            "this registry does not bypass paper-module anchor validation",
        ],
        "namespace_prefixes": sorted(namespace_prefixes),
        "manifests": manifest_rows,
        "cells": cell_rows,
        "validation_summary": validation_summary,
    }

    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "owner_id": OWNER_ID,
        "work_item_id": WORK_ITEM_ID,
        "registry_ref": str(REGISTRY_PATH),
        "markdown_ref": str(MARKDOWN_PATH),
        "registry_sha256": _sha256(registry),
        "status": _registry_status(validation_summary),
        "validation_summary": validation_summary,
        "claim_boundary": registry["claim_boundary"],
        "anti_claims": list(registry["anti_claims"]),
        "no_provider_proof_calls_for_erdos257": True,
        "no_upstream_action": True,
    }
    return registry, receipt


def _registry_status(summary: dict[str, Any]) -> str:
    if summary["duplicate_cell_id_count"] > 0:
        return "FAIL_DUPLICATE_CELL_IDS"
    if summary["missing_manifest_count"] > 0:
        return "DEGRADED_MISSING_MANIFEST"
    if summary["missing_receipt_count"] > 0:
        return "DEGRADED_MISSING_RECEIPT"
    if summary["cannot_satisfy_anchor_count"] > 0:
        return "DEGRADED_CELLS_CANNOT_SATISFY_ANCHOR"
    return "PASS"


def render_markdown(registry: dict[str, Any], receipt: dict[str, Any]) -> str:
    lines: list[str] = [
        "<!--",
        "  Generated by tools/meta/factory/build_formal_math_evidence_cell_registry.py.",
        "  Do not hand-edit; rerun the builder to refresh.",
        "-->",
        "",
        "# Formal Evidence Cell Registry",
        "",
        f"- Schema: `{registry['schema_version']}`",
        f"- Authority posture: `{registry['authority_posture']}`",
        f"- WorkItem anchor: `{registry['work_item_id']}`",
        f"- Registry status: `{receipt['status']}`",
        f"- claim_boundary: `{registry['claim_boundary']}`",
        "",
        "## Posture",
        "",
        "The registry is the operational inventory authority for formal-evidence cells. `std_paper_module.json::formal_evidence_cells` remains the constitutional contract authority; this registry says which manifests are registered, which cell ids exist, and which cells may satisfy paper-module formal-evidence anchors.",
        "",
        "## Anti-claims",
        "",
    ]
    for anti in registry.get("anti_claims", []):
        lines.append(f"- {anti}")
    lines.append("")
    lines.append("## Manifests")
    lines.append("")
    for m in registry.get("manifests", []):
        lines.append(f"### `{m['manifest_path']}`")
        lines.append("")
        lines.append(f"- Status: `{m['manifest_status']}`")
        lines.append(f"- Namespace prefix: `{m['namespace_prefix']}`")
        lines.append(f"- Owner cap: `{m['owner_cap']}`")
        lines.append(f"- Cell count: {m['cell_count']}")
        lines.append(f"- Receipt: `{m['manifest_receipt_path']}` ({m.get('receipt_status')})")
        lines.append("")
    lines.append("## Cells")
    lines.append("")
    lines.append(
        "| cell_id | status | execution_visibility | latest_adapter | latest_result_class | can_satisfy_paper_module_anchor |"
    )
    lines.append("|---|---|---|---|---|---|")
    for cell in registry.get("cells", []):
        lines.append(
            "| `{cid}` | `{st}` | `{vis}` | `{ad}` | `{rc}` | {can} |".format(
                cid=cell["cell_id"],
                st=cell["status"],
                vis=cell.get("execution_visibility_status") or "",
                ad=cell.get("latest_experiment_adapter_id") or "",
                rc=cell.get("latest_experiment_result_class") or "",
                can=cell["can_satisfy_paper_module_anchor"],
            )
        )
    lines.append("")
    lines.append("## Validation summary")
    lines.append("")
    for k, v in registry["validation_summary"].items():
        if isinstance(v, list) and len(v) > 5:
            lines.append(f"- `{k}`: (list, len={len(v)})")
        else:
            lines.append(f"- `{k}`: {v}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(
    registry: dict[str, Any],
    receipt: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> None:
    _write_json(REGISTRY_PATH, registry, repo_root=repo_root)
    _write_json(RECEIPT_PATH, receipt, repo_root=repo_root)
    _write_text(MARKDOWN_PATH, render_markdown(registry, receipt), repo_root=repo_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the current registry matches a fresh rebuild; do not write.",
    )
    args = parser.parse_args(argv)

    registry, receipt = build_registry()

    if args.check:
        current_path = _repo_path(REGISTRY_PATH)
        if not current_path.exists():
            print(json.dumps({"status": "missing_registry", "path": str(REGISTRY_PATH)}))
            return 1
        current = json.loads(current_path.read_text(encoding="utf-8"))
        if _canonical_json(current) != _canonical_json(registry):
            print(
                json.dumps(
                    {
                        "status": "stale_registry",
                        "path": str(REGISTRY_PATH),
                        "expected_sha256": receipt["registry_sha256"],
                        "actual_sha256": _sha256(current),
                    }
                )
            )
            return 1
        print(
            json.dumps(
                {
                    "status": "ok",
                    "cell_count": registry["validation_summary"]["cell_count"],
                    "registry_status": receipt["status"],
                }
            )
        )
        return 0

    write_outputs(registry, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "cell_count": registry["validation_summary"]["cell_count"],
                "manifest_count": registry["validation_summary"]["manifest_count"],
                "registry": str(REGISTRY_PATH),
                "receipt": str(RECEIPT_PATH),
                "markdown": str(MARKDOWN_PATH),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
