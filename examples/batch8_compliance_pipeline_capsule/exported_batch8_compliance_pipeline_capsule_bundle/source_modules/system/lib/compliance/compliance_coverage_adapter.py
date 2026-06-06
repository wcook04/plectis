"""
[PURPOSE]
- Teleology: Scan compliance scanner coverage itself so the compliance ledger
  can say, in the same Atlas/navigation surface, which standards have a
  scanner row and which still lack one.
- Mechanism: Compare the canonical standards inventory against registered
  compliance adapters plus the projected std_python coverage artifact, then
  emit one compact std_compliance_finding-shaped summary finding when coverage
  is incomplete.
- Non-goal: Generate one finding per missing standard, author new adapters,
  mutate standards, or claim system-wide compliance from partial coverage.

[INTERFACE]
- scan_compliance_coverage(repo_root): returns the per-standard coverage row
  for std_compliance_coverage.

[CONSTRAINTS]
- Forbid: source mutation, provider calls, network IO.
- Determinism: same adapter registry and standards inventory -> same finding id
  and counts.
"""
from __future__ import annotations

import hashlib
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from system.lib.standards_inventory import enumerate_standard_records


_STANDARD_ID = "std_compliance_coverage"
_VALIDATOR = "system/lib/compliance/compliance_coverage_adapter.py::scan_compliance_coverage"
_STANDARD_PATH = "codex/standards/std_compliance_coverage.json"
_FINDING_STANDARD = "codex/standards/std_compliance_finding.json"
_ADAPTER_REGISTRY_PATH = "system/lib/compliance/__init__.py"
_LEDGER_BUILDER_PATH = "tools/meta/factory/build_compliance_ledger.py"
_PYTHON_COVERAGE_PATH = (
    "state/meta_missions/python_std_compliance_authoring/"
    "python_std_compliance_coverage.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_id(parts: list[str]) -> str:
    payload = "|".join(str(p) for p in parts).encode("utf-8")
    return "fcf_" + hashlib.sha256(payload).hexdigest()[:16]


def _registered_adapter_standard_ids() -> set[str]:
    package = sys.modules.get("system.lib.compliance")
    adapters = getattr(package, "ADAPTERS", {}) if package is not None else {}
    if not isinstance(adapters, dict):
        return set()
    return {str(standard_id) for standard_id in adapters.keys() if standard_id}


def _baseline_adapter_standard_ids() -> set[str]:
    package = sys.modules.get("system.lib.compliance")
    ids = getattr(package, "BASELINE_ADAPTER_STANDARD_IDS", set()) if package is not None else set()
    if isinstance(ids, (str, bytes)) or not isinstance(ids, Iterable):
        return set()
    return {str(standard_id) for standard_id in ids if standard_id}


def _domain_adapter_standard_ids() -> set[str]:
    package = sys.modules.get("system.lib.compliance")
    ids = getattr(package, "DOMAIN_ADAPTER_STANDARD_IDS", set()) if package is not None else set()
    if not isinstance(ids, (set, frozenset, list, tuple)):
        return set()
    return {str(standard_id) for standard_id in ids if standard_id}


def _python_coverage_available(repo_root: Path) -> bool:
    return (repo_root / _PYTHON_COVERAGE_PATH).exists()


def _missing_scanner_finding(
    *,
    validated_at: str,
    missing_standard_ids: list[str],
    missing_paths: dict[str, str],
    covered_standard_ids: list[str],
    standards_total: int,
) -> dict[str, Any]:
    preview = missing_standard_ids[:25]
    return {
        "finding_id": _finding_id([
            _STANDARD_ID,
            _ADAPTER_REGISTRY_PATH,
            "scope",
            "standards_without_scanner",
            "missing_required_atom",
            str(len(missing_standard_ids)),
        ]),
        "standard_id": _STANDARD_ID,
        "validator": _VALIDATOR,
        "validated_at": validated_at,
        "finding_kind": "missing_required_atom",
        "severity": "warning",
        "artifact_path": _ADAPTER_REGISTRY_PATH,
        "scope_kind": "scope",
        "scope_id": "standards_without_scanner",
        "summary": (
            f"{len(missing_standard_ids)} of {standards_total} standards do not yet "
            "have a compliance scanner row. The compliance ledger is therefore "
            "partial and must not be cited as system-wide compliance."
        ),
        "missing_fields": [],
        "missing_atoms": ["scanner_adapter"],
        "evidence_refs": [
            _STANDARD_PATH,
            _FINDING_STANDARD,
            _ADAPTER_REGISTRY_PATH,
            _LEDGER_BUILDER_PATH,
            "system/lib/standards_inventory.py",
        ],
        "candidate_target_paths": [_ADAPTER_REGISTRY_PATH],
        "candidate_target_payload": {
            "missing_standard_count": len(missing_standard_ids),
            "standards_total": standards_total,
            "covered_standard_count": len(covered_standard_ids),
            "missing_standard_ids_preview": preview,
            "missing_standard_paths_preview": {
                sid: missing_paths[sid]
                for sid in preview
                if sid in missing_paths
            },
            "covered_standard_ids": covered_standard_ids,
            "rule": (
                "Add a read-only scanner under system/lib/compliance/ and register "
                "it in ADAPTERS, or provide a governed projected coverage artifact "
                "for standards with an existing owner lane."
            ),
        },
        "mutation_class": "add_required_field",
        "provider_hint": "type_a_only",
        "authority_ceiling": "authoring_agent",
        "status": "open",
    }


def _baseline_companion_finding(
    *,
    validated_at: str,
    baseline_standard_ids: list[str],
    missing_paths: dict[str, str],
    domain_standard_ids: list[str],
    standards_total: int,
) -> dict[str, Any]:
    preview = baseline_standard_ids[:25]
    return {
        "finding_id": _finding_id([
            _STANDARD_ID,
            _ADAPTER_REGISTRY_PATH,
            "scope",
            "baseline_companion_standards",
            "baseline_companion_only",
            str(len(baseline_standard_ids)),
        ]),
        "standard_id": _STANDARD_ID,
        "validator": _VALIDATOR,
        "validated_at": validated_at,
        "finding_kind": "baseline_companion_only",
        "severity": "info",
        "artifact_path": _ADAPTER_REGISTRY_PATH,
        "scope_kind": "scope",
        "scope_id": "standards_with_baseline_companion_only",
        "summary": (
            f"{len(baseline_standard_ids)} of {standards_total} standards now have "
            "baseline compliance companion rows but still lack domain-specific "
            "artifact scanners."
        ),
        "missing_fields": [],
        "missing_atoms": ["domain_specific_scanner_adapter"],
        "evidence_refs": [
            _STANDARD_PATH,
            _FINDING_STANDARD,
            _ADAPTER_REGISTRY_PATH,
            _LEDGER_BUILDER_PATH,
            "system/lib/compliance/standard_baseline_adapter.py",
            "system/lib/standards_inventory.py",
        ],
        "candidate_target_paths": [
            _ADAPTER_REGISTRY_PATH,
            "system/lib/compliance/standard_baseline_adapter.py",
            *[
                missing_paths[sid]
                for sid in preview[:23]
                if sid in missing_paths
            ],
        ],
        "candidate_target_payload": {
            "baseline_companion_count": len(baseline_standard_ids),
            "standards_total": standards_total,
            "domain_scanner_count": len(domain_standard_ids),
            "baseline_standard_ids_preview": preview,
            "baseline_standard_paths_preview": {
                sid: missing_paths[sid]
                for sid in preview
                if sid in missing_paths
            },
            "domain_standard_ids": domain_standard_ids,
            "repair_targets_preview": [
                {
                    "standard_id": sid,
                    "standard_path": missing_paths[sid],
                    "adapter_registry_path": _ADAPTER_REGISTRY_PATH,
                    "suggested_adapter_path": "system/lib/compliance/<standard_domain>_adapter.py",
                    "validation_command": (
                        "./repo-python tools/meta/factory/build_compliance_ledger.py --report"
                    ),
                    "option_surface_command": (
                        f"./repo-python kernel.py --option-surface compliance_ledger --band card --ids {sid}"
                    ),
                }
                for sid in preview[:12]
                if sid in missing_paths
            ],
            "rule": (
                "Baseline rows close navigation coverage only. Add or bind a "
                "domain-specific scanner before citing full compliance for the "
                "standard's governed artifact corpus."
            ),
        },
        "mutation_class": "add_required_field",
        "provider_hint": "type_a_only",
        "authority_ceiling": "authoring_agent",
        "status": "open",
    }


def scan_compliance_coverage(repo_root: Path) -> dict[str, Any]:
    validated_at = _utc_now()
    records = enumerate_standard_records(repo_root)
    standard_ids = sorted(record.standard_id for record in records)
    source_paths = {record.standard_id: record.source_path for record in records}

    baseline_ids = _baseline_adapter_standard_ids()
    domain_ids = _domain_adapter_standard_ids()
    covered_ids = _registered_adapter_standard_ids()
    if _python_coverage_available(repo_root):
        covered_ids.add("std_python")
        domain_ids.add("std_python")
    covered_standard_ids = sorted(standard_id for standard_id in covered_ids if standard_id in standard_ids)
    baseline_standard_ids = sorted(standard_id for standard_id in baseline_ids if standard_id in standard_ids)
    domain_standard_ids = sorted(standard_id for standard_id in domain_ids if standard_id in standard_ids)
    missing_standard_ids = sorted(set(standard_ids) - set(covered_standard_ids))
    domain_missing_standard_ids = sorted(set(standard_ids) - set(domain_standard_ids))

    findings: list[dict[str, Any]] = []
    if missing_standard_ids:
        findings.append(_missing_scanner_finding(
            validated_at=validated_at,
            missing_standard_ids=missing_standard_ids,
            missing_paths=source_paths,
            covered_standard_ids=covered_standard_ids,
            standards_total=len(standard_ids),
        ))
    elif baseline_standard_ids:
        findings.append(_baseline_companion_finding(
            validated_at=validated_at,
            baseline_standard_ids=baseline_standard_ids,
            missing_paths=source_paths,
            domain_standard_ids=domain_standard_ids,
            standards_total=len(standard_ids),
        ))

    checked = len(standard_ids)
    compliant = len(covered_standard_ids)
    noncompliant = max(0, checked - compliant)
    compliance_rate = float(compliant) / float(max(checked, 1)) if checked else None
    domain_scanner_coverage_rate = (
        float(len(domain_standard_ids)) / float(max(checked, 1))
        if checked else None
    )

    return {
        "standard_id": _STANDARD_ID,
        "validator": _VALIDATOR,
        "validated_at": validated_at,
        "applicable_artifact_count": checked,
        "checked_artifact_count": checked,
        "compliant_artifact_count": compliant,
        "noncompliant_artifact_count": noncompliant,
        "compliance_rate": compliance_rate,
        "top_failure_kinds": (
            [{"finding_kind": "missing_required_atom", "count": noncompliant}]
            if noncompliant else []
        ),
        "findings": findings,
        "evidence_refs": [
            _STANDARD_PATH,
            _FINDING_STANDARD,
            _ADAPTER_REGISTRY_PATH,
            _LEDGER_BUILDER_PATH,
            "system/lib/standards_inventory.py",
        ],
        "metabolism_trigger_state": "scanner_partial" if missing_standard_ids else "ready_compliant",
        "specialization_of": "std_compliance_coverage",
        "coverage_path": "codex/hologram/compliance/ledger.json::totals",
        "coverage_depth": "ledger_row_coverage_with_domain_depth_gap" if baseline_standard_ids else "domain_scanner_coverage_complete",
        "coverage_row_kind": "scanner_coverage_self_audit",
        "compliance_claim_status": (
            "row_coverage_complete_domain_scanner_partial"
            if baseline_standard_ids else
            "row_coverage_complete_domain_scanner_complete"
        ),
        "scanner_depth_status": (
            "missing_domain_scanners"
            if baseline_standard_ids else
            "domain_scanner_ready"
        ),
        "coverage_depth_gap": bool(baseline_standard_ids),
        "ledger_row_coverage": {
            "covered_standard_count": len(covered_standard_ids),
            "pending_standard_count": len(missing_standard_ids),
            "coverage_rate": compliance_rate,
        },
        "domain_scanner_coverage": {
            "domain_scanner_count": len(domain_standard_ids),
            "baseline_companion_count": len(baseline_standard_ids),
            "pending_domain_scanner_count": len(domain_missing_standard_ids),
            "coverage_rate": domain_scanner_coverage_rate,
            "baseline_standard_ids_preview": baseline_standard_ids[:25],
        },
        "notes": (
            "Self-audits scanner coverage over the standards inventory. This row "
            "separates ledger-row coverage from domain-scanner depth: baseline "
            "companions make standards routeable in Atlas/navigation, but they "
            "are not full compliance proof for a standard's governed corpus."
        ),
    }
