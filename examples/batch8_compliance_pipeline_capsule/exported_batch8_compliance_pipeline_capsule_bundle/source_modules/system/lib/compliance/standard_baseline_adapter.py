"""
[PURPOSE]
- Teleology: Provide a read-only baseline compliance companion for standards
  that do not yet have a domain-specific scanner. This keeps Atlas/navigation
  from showing "no row exists" while preserving the stronger truth that a
  baseline companion is not full artifact-corpus validation.
- Mechanism: Resolve the standard through system.lib.standards_inventory, parse
  the standard file when it is JSON, and emit one std_compliance_coverage-shaped
  row with scanner_depth=baseline_standard_file_only.
- Non-goal: Replace domain adapters, validate each standard's governed corpus,
  author findings, or mutate source authority.

[INTERFACE]
- make_standard_baseline_scanner(standard_id): returns a scanner callable for
  registration in system.lib.compliance.ADAPTERS.
- scan_standard_baseline(repo_root, standard_id): direct scanner entry point.

[CONSTRAINTS]
- Forbid: source mutation, provider calls, network IO.
- Determinism: same standard inventory and file contents -> same finding ids
  and row shape.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from system.lib.standards_inventory import enumerate_standard_records


_STANDARD_ID = "std_compliance_coverage"
_VALIDATOR = "system/lib/compliance/standard_baseline_adapter.py::scan_standard_baseline"
_STANDARD_PATH = "codex/standards/std_compliance_coverage.json"
_FINDING_STANDARD = "codex/standards/std_compliance_finding.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finding_id(parts: list[str]) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return "fcf_" + hashlib.sha256(payload).hexdigest()[:16]


def _record_map(repo_root: Path) -> dict[str, str]:
    return {
        record.standard_id: record.source_path
        for record in enumerate_standard_records(repo_root)
    }


def _baseline_finding(
    *,
    standard_id: str,
    validated_at: str,
    artifact_path: str,
    finding_kind: str,
    severity: str,
    summary: str,
    missing_atoms: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": _finding_id([
            standard_id,
            artifact_path,
            "standard_baseline",
            finding_kind,
            summary,
        ]),
        "standard_id": standard_id,
        "validator": f"{_VALIDATOR}[{standard_id}]",
        "validated_at": validated_at,
        "finding_kind": finding_kind,
        "severity": severity,
        "artifact_path": artifact_path,
        "scope_kind": "standard_file",
        "scope_id": standard_id,
        "summary": summary,
        "missing_fields": [],
        "missing_atoms": missing_atoms or [],
        "evidence_refs": [
            artifact_path,
            _STANDARD_PATH,
            _FINDING_STANDARD,
            "system/lib/standards_inventory.py",
        ],
        "candidate_target_paths": [artifact_path],
        "candidate_target_payload": payload or {},
        "mutation_class": "repair_standard_file",
        "provider_hint": "type_a_only",
        "authority_ceiling": "authoring_agent",
        "status": "open",
    }


def scan_standard_baseline(repo_root: Path, standard_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Emit a minimal, truthful compliance row for one standard file
      when no domain-specific scanner exists.
    - Preconditions: `repo_root` points at the repository root and `standard_id`
      is the inventory id being scanned by the baseline companion lane.
    - Guarantee: Returns a std_compliance_coverage-shaped baseline row that
      never claims governed-artifact corpus compliance.
    - Fails: None; missing or unreadable standard files become findings in the
      returned row.
    """
    validated_at = _utc_now()
    records = _record_map(repo_root)
    source_path = records.get(standard_id)
    findings: list[dict[str, Any]] = []
    standard_file_status = "missing"
    id_resolution_source = "missing"
    declared_id: str | None = None
    # Baseline rows make the standard routeable; they deliberately do not
    # count as governed-artifact compliance scans.
    checked = 0
    compliant = 0

    if source_path is None:
        findings.append(_baseline_finding(
            standard_id=standard_id,
            validated_at=validated_at,
            artifact_path="codex/standards",
            finding_kind="missing_standard_file",
            severity="error",
            summary=f"Standard {standard_id} is registered for baseline scanning but is absent from the standards inventory.",
            missing_atoms=["standard_file"],
            payload={"standard_id": standard_id},
        ))
    else:
        artifact = repo_root / source_path
        if artifact.suffix == ".json":
            try:
                payload = json.loads(artifact.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                standard_file_status = "json_unreadable"
                findings.append(_baseline_finding(
                    standard_id=standard_id,
                    validated_at=validated_at,
                    artifact_path=source_path,
                    finding_kind="schema_violation",
                    severity="error",
                    summary=f"Standard {standard_id} could not be parsed as JSON for baseline compliance coverage.",
                    missing_atoms=["parseable_standard_json"],
                    payload={"error": str(exc.__class__.__name__)},
                ))
            else:
                standard_file_status = "json_parseable"
                if isinstance(payload, dict):
                    raw_id = payload.get("id")
                    if isinstance(raw_id, str) and raw_id.strip():
                        declared_id = raw_id.strip()
                        id_resolution_source = "declared_id"
                    else:
                        id_resolution_source = "filename_fallback"
                else:
                    id_resolution_source = "filename_fallback"
                if declared_id and declared_id != standard_id:
                    findings.append(_baseline_finding(
                        standard_id=standard_id,
                        validated_at=validated_at,
                        artifact_path=source_path,
                        finding_kind="schema_violation",
                        severity="warning",
                        summary=(
                            f"Standard file declares id {declared_id!r}, but inventory resolved "
                            f"it as {standard_id!r}."
                        ),
                        missing_atoms=["matching_declared_standard_id"],
                        payload={
                            "declared_id": declared_id,
                            "inventory_standard_id": standard_id,
                        },
                    ))
                else:
                    pass
        else:
            standard_file_status = "non_json_standard_file"
            id_resolution_source = "inventory_special_case"

    noncompliant = 0
    return {
        "standard_id": standard_id,
        "validator": f"{_VALIDATOR}[{standard_id}]",
        "validated_at": validated_at,
        "applicable_artifact_count": checked,
        "checked_artifact_count": checked,
        "compliant_artifact_count": compliant,
        "noncompliant_artifact_count": noncompliant,
        "compliance_rate": None,
        "top_failure_kinds": (
            [{"finding_kind": findings[0]["finding_kind"], "count": noncompliant}]
            if noncompliant and findings else []
        ),
        "findings": findings,
        "evidence_refs": [
            source_path or "codex/standards",
            _STANDARD_PATH,
            _FINDING_STANDARD,
            "system/lib/standards_inventory.py",
        ],
        "metabolism_trigger_state": "baseline_blocked" if noncompliant else "baseline_only",
        "specialization_of": "std_compliance_coverage",
        "coverage_path": source_path,
        "coverage_depth": "baseline_standard_file_only",
        "coverage_row_kind": "baseline_inventory_only",
        "baseline_companion": True,
        "scanner_adapter_present": False,
        "adapter_registered": True,
        "governed_projection_present": False,
        "compliance_claim_status": "no_compliance_claim",
        "scanner_depth_status": "missing_domain_scanner",
        "coverage_depth_gap": True,
        "baseline_reason": "standard_inventory_row_only",
        "domain_scanner_status": "missing_domain_specific_adapter",
        "standard_file_status": standard_file_status,
        "id_resolution_source": id_resolution_source,
        "declared_standard_id": declared_id,
        "notes": (
            "Baseline companion row only: the standard file was visible and "
            "parseable enough to route, but this does not validate the full "
            "artifact corpus governed by the standard."
        ),
    }


def make_standard_baseline_scanner(standard_id: str) -> Callable[[Path], dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Build a registry-compatible scanner closure for one standard.
    - Preconditions: `standard_id` is the inventory id that the generated
      closure should bind.
    - Guarantee: Returns a callable that accepts `repo_root` and delegates to
      scan_standard_baseline with the captured standard id.
    - Fails: None at construction time; scan-time degradation is owned by
      scan_standard_baseline.
    """
    def _scan(repo_root: Path) -> dict[str, Any]:
        return scan_standard_baseline(repo_root, standard_id)

    _scan.__name__ = f"scan_standard_baseline_{standard_id}"
    return _scan


__all__ = ["make_standard_baseline_scanner", "scan_standard_baseline"]
