#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Materialize codex/hologram/compliance/ledger.json by running every
  registered cross-standard compliance adapter under system.lib.compliance and
  composing one read-only digest the metabolism daemon and reactions engine can
  consume.
- Mechanism: Walk the ADAPTERS registry, run each scanner, also stitch in the
  proven Python compliance lane via the python_std_compliance_coverage artifact,
  compute totals, write atomically.
- Non-goal: Author findings, mutate source authority, or fire reactions.

[INTERFACE]
- CLI: --check (no write; exits 1 if the registered projection artifact is
  missing or any standard has error-severity findings), --report (print summary
  to stdout), --standard-id <std_id> (refresh bounded rows against the existing
  ledger, or bootstrap a bounded projection when the ledger is missing; includes
  projection_self_audit so bounded checks cannot masquerade as full-ledger
  freshness), --ratchet-next (select and refresh the next missing registered
  row plus std_compliance_coverage as a bounded queue step), --ratchet-count N
  (with --ratchet-next, select up to N missing rows before the self-audit
  companion), default is full build-and-write, --microcosm-readiness (bounded
  no-write packet that ties std_microcosm compliance evidence to active
  Microcosm claim state and public export drilldowns).

[FLOW]
- Resolve repo root.
- For each adapter, scan and capture per-standard payload.
- Read python_std_compliance_coverage.json and project it into the ledger row
  shape so it appears alongside the new generic adapters.
- Aggregate totals (standards_with_coverage_artifact, average_known_compliance_rate).
- Compose metabolism_worklist (ready_now entries from non-compliant standards
  with task-class-formalization or autocure semantics).
- Write codex/hologram/compliance/ledger.json atomically.

[DEPENDENCIES]
- system.lib.compliance.ADAPTERS, scan_all.

[CONSTRAINTS]
- Forbid: provider calls, mutation of source authority, network IO.
- Atomicity: write via a temp file rename so concurrent readers see a complete
  ledger or the previous one.
- Determinism: same substrate -> same ledger numbers (timestamps differ).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.compliance import (  # noqa: E402
    ADAPTERS,
    BASELINE_ADAPTER_STANDARD_IDS,
    DOMAIN_ADAPTER_STANDARD_IDS,
    scan_all,
)
from system.lib.standards_inventory import enumerate_standard_ids  # noqa: E402


_LEDGER_PATH = "codex/hologram/compliance/ledger.json"
_ACTIVE_CLAIMS_SNAPSHOT_PATH = "state/work_ledger/active_claims_snapshot.json"
_MICROCOSM_READINESS_STANDARD_IDS = ["std_microcosm", "std_compliance_coverage"]
_PYTHON_COVERAGE_PATH = (
    "state/meta_missions/python_std_compliance_authoring/"
    "python_std_compliance_coverage.json"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict) -> None:
    """
    [ACTION]
    - Teleology: Write JSON atomically so concurrent ledger readers never see a
      partial file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _project_python_coverage(repo_root: Path) -> dict | None:
    """
    [ACTION]
    - Teleology: Project the existing Python compliance coverage artifact into
      the generic ledger row shape so std_python participates without forcing a
      duplicate scanner.
    """
    cov_file = repo_root / _PYTHON_COVERAGE_PATH
    if not cov_file.exists():
        return None
    try:
        cov = json.loads(cov_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    counts = cov.get("counts") or {}
    triggers = cov.get("triggers") or {}
    findings_total = int(counts.get("findings_total") or 0)
    return {
        "standard_id": "std_python",
        "validator": "tools/meta/miner.py + tools/meta/hygiene.py",
        "validated_at": cov.get("generated_at") or _utc_now(),
        "applicable_artifact_count": None,
        "checked_artifact_count": None,
        "compliant_artifact_count": None,
        "noncompliant_artifact_count": findings_total,
        "compliance_rate": None,
        "top_failure_kinds": [],
        "findings": [],
        "evidence_refs": [_PYTHON_COVERAGE_PATH, "codex/standards/std_python.py"],
        "metabolism_trigger_state": (
            "drain_ready" if triggers.get("drain_ready") else
            "preview_kickoff_ready" if triggers.get("preview_kickoff_ready") else
            "ready"
        ),
        "specialization_of": "std_compliance_coverage",
        "coverage_path": _PYTHON_COVERAGE_PATH,
        "reaction_wired": True,
        "reaction_ids": [
            "python_std_compliance_preview_kickoff",
            "python_std_compliance_drain_continue",
        ],
        "notes": "Projected from python_std_compliance_coverage; the proven Python compliance lane.",
    }


def _python_coverage_available(repo_root: Path) -> bool:
    return (repo_root / _PYTHON_COVERAGE_PATH).exists()


def _adapter_registry_snapshot(repo_root: Path) -> dict:
    """
    [ACTION]
    - Teleology: Capture the live scanner registry depth without running every
      scanner, so bounded row checks can compare materialized ledger freshness
      against the current adapter surface.
    """
    standard_ids = set(enumerate_standard_ids(repo_root))
    registered_ids = {
        str(standard_id)
        for standard_id in ADAPTERS.keys()
        if str(standard_id) in standard_ids
    }
    domain_ids = {
        str(standard_id)
        for standard_id in DOMAIN_ADAPTER_STANDARD_IDS
        if str(standard_id) in standard_ids
    }
    baseline_ids = {
        str(standard_id)
        for standard_id in BASELINE_ADAPTER_STANDARD_IDS
        if str(standard_id) in standard_ids
    }
    if _python_coverage_available(repo_root) and "std_python" in standard_ids:
        registered_ids.add("std_python")
        domain_ids.add("std_python")

    return {
        "standards_total": len(standard_ids),
        "registered_adapter_count": len(registered_ids),
        "registered_domain_adapter_count": len(domain_ids),
        "registered_baseline_adapter_count": len(baseline_ids),
        "standards_pending_domain_scanner": max(0, len(standard_ids) - len(domain_ids)),
        "registered_adapter_ids": sorted(registered_ids),
        "registered_domain_adapter_ids": sorted(domain_ids),
        "registered_baseline_adapter_ids": sorted(baseline_ids),
    }


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _row_ids(rows: list[dict]) -> set[str]:
    return {
        str(row.get("standard_id"))
        for row in rows
        if isinstance(row, dict) and row.get("standard_id")
    }


def _preview(values: list[str], limit: int = 25) -> list[str]:
    return values[:limit]


def _adapter_kind(standard_id: str | None, registry: dict) -> str | None:
    if standard_id is None:
        return None
    if standard_id in set(registry.get("registered_domain_adapter_ids") or []):
        return "domain_scanner"
    if standard_id in set(registry.get("registered_baseline_adapter_ids") or []):
        return "baseline_companion"
    return "registered_adapter"


def _choose_next_missing_registered_standard(
    *,
    missing_registered_ids: list[str],
    registry: dict,
) -> str | None:
    """
    [ACTION]
    - Teleology: Pick one next scanner-depth row for a bounded ratchet. Domain
      scanners move trust more than baseline companions, so they come first.
    """
    selected = _choose_missing_registered_standards(
        missing_registered_ids=missing_registered_ids,
        registry=registry,
        limit=1,
    )
    return selected[0] if selected else None


def _choose_missing_registered_standards(
    *,
    missing_registered_ids: list[str],
    registry: dict,
    limit: int,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Pick a bounded scanner-depth batch for ratchet refresh.
      Domain scanners move trust more than baseline companions, so the batch
      consumes domain rows first and then baseline rows.
    """
    if limit <= 0:
        return []
    missing = set(missing_registered_ids)
    missing_domain = sorted(
        missing & set(registry.get("registered_domain_adapter_ids") or [])
    )
    missing_baseline = sorted(
        missing & set(registry.get("registered_baseline_adapter_ids") or [])
    )
    ranked = missing_domain + missing_baseline
    ranked_seen = set(ranked)
    ranked.extend(
        standard_id
        for standard_id in missing_registered_ids
        if standard_id not in ranked_seen
    )
    return ranked[:limit]


def _bounded_check_command(standard_id: str | None) -> str | None:
    if standard_id is None:
        return None
    command = (
        "./repo-python tools/meta/factory/build_compliance_ledger.py "
        f"--check --report --standard-id {standard_id}"
    )
    if standard_id != "std_compliance_coverage":
        command += " --standard-id std_compliance_coverage"
    return command


def _ratchet_command() -> str:
    return (
        "./repo-python tools/meta/factory/build_compliance_ledger.py "
        "--check --report --ratchet-next"
    )


def _microcosm_readiness_command() -> str:
    return (
        "./repo-python tools/meta/factory/build_compliance_ledger.py "
        "--check --report --microcosm-readiness"
    )


def _ratchet_standard_ids_from_rows(
    repo_root: Path,
    existing_rows: list[dict],
    *,
    limit: int = 1,
) -> list[str]:
    registry = _adapter_registry_snapshot(repo_root)
    source_ids = _row_ids(existing_rows)
    source_missing_registered = sorted(
        set(registry.get("registered_adapter_ids") or []) - source_ids
    )
    next_standard_ids = _choose_missing_registered_standards(
        missing_registered_ids=source_missing_registered,
        registry=registry,
        limit=limit,
    )
    if not next_standard_ids:
        return []
    selected = list(next_standard_ids)
    if (
        "std_compliance_coverage" not in selected
        and "std_compliance_coverage" in set(registry.get("registered_adapter_ids") or [])
    ):
        selected.append("std_compliance_coverage")
    return selected


def _ratchet_next_standard_ids(repo_root: Path, *, limit: int = 1) -> list[str]:
    try:
        existing_ledger = _load_existing_ledger(repo_root)
    except FileNotFoundError:
        existing_rows = []
    else:
        existing_rows_raw = existing_ledger.get("by_standard")
        if existing_rows_raw is None:
            existing_rows = []
        elif not isinstance(existing_rows_raw, list):
            raise ValueError(f"{_LEDGER_PATH} is missing by_standard rows")
        else:
            existing_rows = [row for row in existing_rows_raw if isinstance(row, dict)]
    return _ratchet_standard_ids_from_rows(repo_root, existing_rows, limit=limit)


def _ratchet_noop_ledger(repo_root: Path) -> dict:
    """
    [ACTION]
    - Teleology: Let --ratchet-next report an empty queue without falling back
      to a full scanner pass or broad generated-ledger write.
    """
    source_projection_present = (repo_root / _LEDGER_PATH).exists()
    try:
        existing_ledger = _load_existing_ledger(repo_root)
    except FileNotFoundError:
        existing_ledger = None
        existing_rows = []
    else:
        existing_rows_raw = existing_ledger.get("by_standard")
        if existing_rows_raw is None:
            existing_rows = []
        elif not isinstance(existing_rows_raw, list):
            raise ValueError(f"{_LEDGER_PATH} is missing by_standard rows")
        else:
            existing_rows = [row for row in existing_rows_raw if isinstance(row, dict)]
    ledger = dict(existing_ledger) if existing_ledger is not None else _compose_ledger(repo_root, [])
    ledger["refresh_scope"] = {
        "mode": "bounded_ratchet_noop",
        "selected_standard_ids": [],
        "source_projection_present": source_projection_present,
        "source_row_count": len(existing_rows),
        "updated_row_count": 0,
        "merged_row_count": len(_row_ids(existing_rows)),
        "standards_total": _as_int((ledger.get("totals") or {}).get("standards_total")),
        "partial_projection": False,
        "full_build_command": "./repo-python tools/meta/factory/build_compliance_ledger.py",
        "truth_boundary": (
            "No registered adapter row is missing from the materialized ledger; "
            "--ratchet-next did not run a broad scanner pass."
        ),
    }
    ledger["projection_self_audit"] = _projection_self_audit(
        repo_root,
        existing_ledger=existing_ledger,
        existing_rows=existing_rows,
        merged_rows=existing_rows,
        selected_standard_ids=[],
        updated_rows=[],
    )
    return ledger


def _projection_self_audit(
    repo_root: Path,
    *,
    existing_ledger: dict | None,
    existing_rows: list[dict],
    merged_rows: list[dict],
    selected_standard_ids: list[str],
    updated_rows: list[dict],
) -> dict:
    """
    [ACTION]
    - Teleology: Make bounded compliance checks tell the truth about what the
      materialized ledger proves, what the live adapter registry can now see,
      and what the bounded refresh deliberately did not touch.
    """
    registry = _adapter_registry_snapshot(repo_root)
    registry_ids = set(registry.get("registered_adapter_ids") or [])
    baseline_ids = set(registry.get("registered_baseline_adapter_ids") or [])
    source_ids = _row_ids(existing_rows)
    merged_ids = _row_ids(merged_rows)
    source_missing_registered = sorted(registry_ids - source_ids)
    merged_missing_registered = sorted(registry_ids - merged_ids)
    source_missing_domain = sorted(
        set(registry.get("registered_domain_adapter_ids") or []) - source_ids
    )
    source_missing_baseline = sorted(
        set(registry.get("registered_baseline_adapter_ids") or []) - source_ids
    )

    source_totals = (existing_ledger or {}).get("totals") or {}
    source_scanned = _as_int(source_totals.get("scanned_standards"), len(source_ids))
    registered_count = _as_int(registry.get("registered_adapter_count"), len(registry_ids))
    source_projection_present = existing_ledger is not None
    if not source_projection_present:
        materialized_status = "materialized_ledger_missing"
    elif source_missing_registered or source_scanned < registered_count:
        materialized_status = "materialized_ledger_stale_or_partial"
    else:
        materialized_status = "materialized_ledger_aligned_with_registered_adapters"

    source_ratchet_standard_id = _choose_next_missing_registered_standard(
        missing_registered_ids=source_missing_registered,
        registry=registry,
    )
    next_standard_id = _choose_next_missing_registered_standard(
        missing_registered_ids=merged_missing_registered,
        registry=registry,
    )
    next_exact_check_command = _bounded_check_command(next_standard_id)
    closed_selected_ids = sorted(
        set(selected_standard_ids)
        & set(source_missing_registered)
        - set(merged_missing_registered)
    )
    ratchet_closed = (
        source_ratchet_standard_id is not None
        and source_ratchet_standard_id in set(selected_standard_ids)
        and source_ratchet_standard_id in set(source_missing_registered)
        and source_ratchet_standard_id not in set(merged_missing_registered)
    )

    return {
        "schema_version": "compliance_projection_self_audit_v0",
        "status": materialized_status,
        "materialized_ledger_status": materialized_status,
        "source_projection_present": source_projection_present,
        "source_projection_generated_at": (existing_ledger or {}).get("generated_at"),
        "source_materialized_scanned_standards": source_scanned,
        "source_materialized_row_count": len(source_ids),
        "registered_adapter_count": registered_count,
        "registered_domain_adapter_count": registry.get("registered_domain_adapter_count"),
        "registered_baseline_adapter_count": registry.get("registered_baseline_adapter_count"),
        "standards_total": registry.get("standards_total"),
        "standards_pending_domain_scanner": registry.get("standards_pending_domain_scanner"),
        "source_missing_registered_rows_count": len(source_missing_registered),
        "source_missing_registered_rows_preview": _preview(source_missing_registered),
        "source_missing_domain_rows_count": len(source_missing_domain),
        "source_missing_domain_rows_preview": _preview(source_missing_domain),
        "source_missing_baseline_rows_count": len(source_missing_baseline),
        "source_missing_baseline_rows_preview": _preview(source_missing_baseline),
        "post_refresh_missing_registered_rows_count": len(merged_missing_registered),
        "post_refresh_missing_registered_rows_preview": _preview(merged_missing_registered),
        "bounded_check": {
            "mode": "selected_standard_rows_only",
            "selected_standard_ids": selected_standard_ids,
            "updated_row_count": len(updated_rows),
            "merged_row_count": len(merged_ids),
            "partial_projection": bool(merged_missing_registered),
            "did_refresh": "selected_standard_ids_only",
            "did_not_refresh": (
                "Unselected registered adapter rows, unselected baseline companion "
                "rows, and unselected standards remain whatever the materialized "
                "ledger already carried."
            ),
            "unrefreshed_registered_adapter_count": len(
                registry_ids - set(selected_standard_ids)
            ),
        },
        "scanner_depth_ratchet": {
            "schema_version": "compliance_scanner_depth_ratchet_v0",
            "status": (
                "closed_batch"
                if len(closed_selected_ids) > 1 else
                "closed_one_row"
                if ratchet_closed or closed_selected_ids else
                "ready_next_row"
                if source_ratchet_standard_id else
                "registered_adapter_rows_materialized"
            ),
            "candidate_standard_id": source_ratchet_standard_id,
            "candidate_adapter_kind": _adapter_kind(source_ratchet_standard_id, registry),
            "selection_reason": (
                "Prioritize missing registered domain scanner rows before "
                "baseline companion rows; choose lexical order inside the "
                "same adapter-depth class for deterministic bounded work."
                if source_ratchet_standard_id else
                "No registered adapter rows are missing from the materialized ledger."
            ),
            "source_queue_remaining": len(source_missing_registered),
            "source_missing_domain_rows_count": len(source_missing_domain),
            "source_missing_baseline_rows_count": len(source_missing_baseline),
            "selected_standard_ids": selected_standard_ids,
            "closed_standard_ids": closed_selected_ids,
            "closed_standard_count": len(closed_selected_ids),
            "closed_by_this_bounded_check": ratchet_closed,
            "post_refresh_queue_remaining": len(merged_missing_registered),
            "post_refresh_next_standard_id": next_standard_id,
            "post_refresh_next_adapter_kind": _adapter_kind(next_standard_id, registry),
            "ratchet_next_command": _ratchet_command(),
            "candidate_bounded_command": _bounded_check_command(source_ratchet_standard_id),
            "post_refresh_next_command": next_exact_check_command,
            "expected_effect": (
                "Refresh exactly one missing registered row and the "
                "std_compliance_coverage self-audit companion; do not imply "
                "system-wide ledger freshness."
            ),
        },
        "next_exact_standard_id": next_standard_id,
        "next_exact_check_command": next_exact_check_command,
        "next_option_surface_command": (
            f"./repo-python kernel.py --option-surface compliance_ledger "
            f"--band card --ids {next_standard_id}"
            if next_standard_id else None
        ),
        "truth_boundary": (
            "A bounded --standard-id refresh proves only the selected rows plus "
            "this self-audit comparison. It is not system-wide compliance until "
            "the materialized ledger row set matches the live registered adapter "
            "surface and scanner-depth gaps remain explicitly labeled."
        ),
    }


def _row_for_standard(ledger: dict, standard_id: str) -> dict | None:
    rows = ledger.get("by_standard")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("standard_id") == standard_id:
            return row
    return None


def _standard_readiness_summary(ledger: dict, standard_id: str) -> dict:
    row = _row_for_standard(ledger, standard_id)
    if row is None:
        return {
            "standard_id": standard_id,
            "row_present": False,
            "status": "missing_from_bounded_projection",
        }
    findings = row.get("findings") or []
    if not isinstance(findings, list):
        findings = []
    return {
        "standard_id": standard_id,
        "row_present": True,
        "coverage_row_kind": row.get("coverage_row_kind"),
        "coverage_depth": row.get("coverage_depth"),
        "coverage_depth_gap": row.get("coverage_depth_gap"),
        "scanner_depth_status": row.get("scanner_depth_status"),
        "compliance_claim_status": row.get("compliance_claim_status"),
        "compliance_rate": row.get("compliance_rate"),
        "finding_count": len(findings),
        "error_finding_count": sum(
            1 for finding in findings
            if isinstance(finding, dict) and finding.get("severity") == "error"
        ),
        "metabolism_trigger_state": row.get("metabolism_trigger_state"),
        "evidence_refs": _preview(
            [
                str(ref)
                for ref in (row.get("evidence_refs") or [])
                if ref
            ],
            limit=10,
        ),
    }


def _microcosm_claim_matches(claim: dict) -> bool:
    path = str(claim.get("path") or claim.get("scope_id") or "")
    work_item_id = str(claim.get("work_item_id") or "")
    if path.startswith("microcosm-substrate/"):
        return True
    if path == "codex/standards/std_microcosm.json":
        return True
    if path.startswith("codex/doctrine/skills/doctrine/public_microcosm"):
        return True
    if path.startswith(".agents/skills/public-microcosm"):
        return True
    return "microcosm" in work_item_id.lower()


def _active_microcosm_claim_summary(repo_root: Path) -> dict:
    """
    [ACTION]
    - Teleology: Let the compliance readiness packet state whether live
      Microcosm substrate lanes are actively owned before suggesting source
      mutation or public-readiness conclusions.
    """
    snapshot_path = repo_root / _ACTIVE_CLAIMS_SNAPSHOT_PATH
    refresh_command = (
        "./repo-python tools/meta/factory/work_ledger.py "
        "session-claims --refresh --session-summary --limit 30 --cards-only"
    )
    if not snapshot_path.exists():
        return {
            "status": "snapshot_missing",
            "source_ref": _ACTIVE_CLAIMS_SNAPSHOT_PATH,
            "active_claim_count": None,
            "active_session_count": None,
            "refresh_command": refresh_command,
        }
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "snapshot_unreadable",
            "source_ref": _ACTIVE_CLAIMS_SNAPSHOT_PATH,
            "error": str(exc),
            "active_claim_count": None,
            "active_session_count": None,
            "refresh_command": refresh_command,
        }

    raw_claims = payload.get("active_claims") or []
    if not isinstance(raw_claims, list):
        raw_claims = []
    microcosm_claims = [
        claim
        for claim in raw_claims
        if (
            isinstance(claim, dict)
            and not claim.get("released_at")
            and not claim.get("expired_at")
            and _microcosm_claim_matches(claim)
        )
    ]

    sessions: dict[str, dict] = {}
    path_preview: list[str] = []
    for claim in microcosm_claims:
        session_id = str(claim.get("session_id") or "<unknown>")
        session = sessions.setdefault(
            session_id,
            {
                "session_id": session_id,
                "claim_count": 0,
                "path_preview": [],
                "leased_until": claim.get("leased_until"),
            },
        )
        session["claim_count"] += 1
        leased_until = claim.get("leased_until")
        if leased_until and (
            not session.get("leased_until")
            or str(leased_until) > str(session.get("leased_until"))
        ):
            session["leased_until"] = leased_until
        path = str(claim.get("path") or "")
        if path:
            path_preview.append(path)
            if len(session["path_preview"]) < 6:
                session["path_preview"].append(path)

    session_preview = sorted(
        sessions.values(),
        key=lambda item: (-int(item.get("claim_count") or 0), str(item.get("session_id"))),
    )
    return {
        "status": (
            "active_microcosm_claims_visible"
            if microcosm_claims else
            "no_active_microcosm_claims_visible"
        ),
        "source_ref": _ACTIVE_CLAIMS_SNAPSHOT_PATH,
        "snapshot_generated_at": payload.get("generated_at"),
        "snapshot_counts": payload.get("counts"),
        "active_claim_count": len(microcosm_claims),
        "active_path_claim_count": sum(
            1 for claim in microcosm_claims if claim.get("path")
        ),
        "active_session_count": len(sessions),
        "path_preview": _preview(sorted(set(path_preview)), limit=20),
        "sessions_preview": _preview(session_preview, limit=8),
        "refresh_command": refresh_command,
        "truth_boundary": (
            "Claim data is a live coordination snapshot. Treat active paths as "
            "owned until the Work Ledger refresh shows release or expiry."
        ),
    }


def _microcosm_public_substrate_readiness_packet(repo_root: Path, ledger: dict) -> dict:
    """
    [ACTION]
    - Teleology: Spend the generic compliance self-audit on Microcosm public
      trust by joining bounded std_microcosm evidence, scanner-depth freshness,
      and live claim state into one first-contact packet.
    """
    self_audit = ledger.get("projection_self_audit") or {}
    std_microcosm = _standard_readiness_summary(ledger, "std_microcosm")
    std_compliance_coverage = _standard_readiness_summary(
        ledger,
        "std_compliance_coverage",
    )
    active_claims = _active_microcosm_claim_summary(repo_root)
    active_claim_count = active_claims.get("active_claim_count")
    microcosm_error_count = int(std_microcosm.get("error_finding_count") or 0)
    projection_status = self_audit.get("materialized_ledger_status")

    if not std_microcosm.get("row_present"):
        status = "std_microcosm_bounded_row_missing"
    elif microcosm_error_count:
        status = "std_microcosm_findings_present"
    elif isinstance(active_claim_count, int) and active_claim_count > 0:
        status = "microcosm_substrate_actively_owned"
    elif projection_status in {
        "materialized_ledger_missing",
        "materialized_ledger_stale_or_partial",
    }:
        status = "bounded_microcosm_evidence_materialized_ledger_partial"
    else:
        status = "bounded_microcosm_compliance_probe_green"

    return {
        "schema_version": "microcosm_public_substrate_readiness_v0",
        "status": status,
        "selected_standard_ids": list(_MICROCOSM_READINESS_STANDARD_IDS),
        "std_microcosm": std_microcosm,
        "std_compliance_coverage": std_compliance_coverage,
        "compliance_projection": {
            "materialized_ledger_status": projection_status,
            "source_materialized_scanned_standards": self_audit.get(
                "source_materialized_scanned_standards"
            ),
            "registered_adapter_count": self_audit.get("registered_adapter_count"),
            "source_missing_registered_rows_count": self_audit.get(
                "source_missing_registered_rows_count"
            ),
            "post_refresh_missing_registered_rows_count": self_audit.get(
                "post_refresh_missing_registered_rows_count"
            ),
            "bounded_check": self_audit.get("bounded_check"),
            "truth_boundary": self_audit.get("truth_boundary"),
        },
        "active_microcosm_claims": active_claims,
        "public_substrate_trust_boundary": {
            "trusted_now": [
                "std_microcosm can be checked through a bounded no-write scanner row.",
                "The packet reports live Microcosm claim ownership before naming write lanes.",
                "The compliance projection freshness is explicitly partial or stale when the materialized ledger lags registered adapters.",
            ],
            "not_trusted_from_this_packet": [
                "System-wide standards compliance.",
                "Microcosm public release approval.",
                "Fixture-only evidence as accepted substrate authority.",
                "Any active import, disposition, engine-room, or flight-recorder path as safe to mutate.",
            ],
        },
        "microcosm_drilldowns": {
            "std_microcosm_card": (
                "./repo-python kernel.py --option-surface standards "
                "--band card --ids std_microcosm"
            ),
            "public_export_type_plane": (
                "./repo-python kernel.py --option-surface navigation_type_plane "
                "--band card --ids public_microcosm_exports"
            ),
            "microcosm_substrate_module": "./repo-python kernel.py --paper-module microcosm_substrate",
        },
        "next_proofs": {
            "readiness_command": _microcosm_readiness_command(),
            "bounded_compliance_command": (
                "./repo-python tools/meta/factory/build_compliance_ledger.py "
                "--check --report --standard-id std_microcosm "
                "--standard-id std_compliance_coverage"
            ),
            "active_claims_command": active_claims.get("refresh_command"),
            "public_export_boundary_command": (
                "./repo-python kernel.py --option-surface navigation_type_plane "
                "--band card --ids public_microcosm_exports"
            ),
            "claim_safe_mutation_rule": (
                "If active_microcosm_claims.active_claim_count is nonzero, mutate "
                "only disjoint compliance/reporting surfaces or coordinate handoff."
            ),
        },
        "truth_boundary": (
            "--microcosm-readiness is a bounded first-contact packet. It makes "
            "Microcosm compliance evidence, scanner-depth freshness, and claim "
            "ownership visible; it does not refresh the full generated ledger or "
            "certify public-substrate release readiness."
        ),
    }


def _build_metabolism_worklist(rows: list[dict]) -> dict:
    ready_now: list[dict] = []
    deferred: list[str] = []
    for row in rows:
        sid = row.get("standard_id") or "<unknown>"
        if row.get("metabolism_trigger_state") in ("baseline_only", "baseline_blocked"):
            deferred.append(sid)
        elif (row.get("noncompliant_artifact_count") or 0) > 0 and row.get("metabolism_trigger_state") in (
            "scanner_partial", "preview_kickoff_ready", "drain_ready"
        ):
            ready_now.append({
                "standard_id": sid,
                "operation_kind": "compliance_autocure_campaign",
                "rationale": (
                    f"{row.get('noncompliant_artifact_count')} noncompliant artifacts "
                    f"with trigger_state={row.get('metabolism_trigger_state')}"
                ),
                "authority_tier": "authoring_agent",
                "notes": "Controller-gated; provider lanes return only candidate evidence.",
            })
        elif row.get("metabolism_trigger_state") == "scanner_input_missing":
            deferred.append(sid)
    return {
        "rule": (
            "tools/meta/control/metabolismd.py reads this worklist and queues "
            "bounded compliance autocure work via reactions.yaml::compliance_coverage_low."
        ),
        "ready_now": ready_now,
        "deferred_until_scanner_authored": deferred,
    }


def _setdefault_non_null(row: dict, key: str, value: object) -> None:
    if row.get(key) is None:
        row[key] = value


def _normalize_scanner_depth_metadata(row: dict) -> dict:
    """
    [ACTION]
    - Teleology: Make every ledger row directly consumable by Atlas/navigation
      without requiring option-surface fallback inference for scanner-depth
      posture.
    """
    normalized = dict(row)
    if not normalized.get("standard_id"):
        return normalized

    if normalized.get("coverage_row_kind") == "scanner_coverage_self_audit":
        _setdefault_non_null(normalized, "coverage_depth_gap", bool(normalized.get("findings")))
        return normalized

    if normalized.get("baseline_companion") is True:
        _setdefault_non_null(normalized, "coverage_depth", "baseline_standard_file_only")
        _setdefault_non_null(normalized, "coverage_row_kind", "baseline_inventory_only")
        _setdefault_non_null(normalized, "compliance_claim_status", "no_compliance_claim")
        _setdefault_non_null(normalized, "scanner_depth_status", "missing_domain_scanner")
        _setdefault_non_null(normalized, "coverage_depth_gap", True)
        return normalized

    _setdefault_non_null(normalized, "coverage_depth", "domain_runtime_or_projection_scan")
    _setdefault_non_null(normalized, "coverage_row_kind", "domain_scanner")
    _setdefault_non_null(normalized, "compliance_claim_status", "domain_scanner_claim")
    _setdefault_non_null(normalized, "scanner_depth_status", "domain_scanner_present")
    _setdefault_non_null(normalized, "coverage_depth_gap", False)
    return normalized


def _compose_ledger(repo_root: Path, payloads: list[dict]) -> dict:
    """
    [ACTION]
    - Teleology: Compose the shared compliance ledger shape from already-built
      row payloads.
    """
    normalized_payloads = [
        _normalize_scanner_depth_metadata(row)
        for row in payloads
        if isinstance(row, dict)
    ]
    rows_by_standard = {
        str(r.get("standard_id")): r
        for r in normalized_payloads
        if r.get("standard_id")
    }
    standards_with_coverage = sum(
        1 for r in rows_by_standard.values()
        if r.get("compliance_rate") is not None or r.get("coverage_path")
    )
    baseline_companion_count = sum(
        1 for r in rows_by_standard.values()
        if r.get("baseline_companion") is True
    )
    domain_scanner_count = sum(
        1 for r in rows_by_standard.values()
        if r.get("baseline_companion") is not True
    )
    rates = [
        r["compliance_rate"]
        for r in rows_by_standard.values()
        if isinstance(r.get("compliance_rate"), (int, float))
        and r.get("baseline_companion") is not True
    ]
    average = (sum(rates) / len(rates)) if rates else None
    # Resolve standards_total from the shared standards inventory helper so
    # this builder agrees with build_standard_skill_map.py and any future
    # comprehension-snapshot consumer. Hardcoded totals are exactly the
    # quiet-projection drift pri_001 (JSON is contract) and pri_133
    # (ceremony is advisory; fix the deep cause) named in their failure modes.
    standards_total = len(enumerate_standard_ids(repo_root))

    return {
        "kind": "compliance_ledger",
        "schema_version": "compliance_ledger_v1",
        "generated_at": _utc_now(),
        "generated_by": "tools/meta/factory/build_compliance_ledger.py",
        "standard_ref": "codex/standards/std_compliance_coverage.json",
        "rule": (
            "Aggregates per-standard coverage entries into one read-only digest. "
            "The metabolism daemon reads this ledger to schedule cross-standard "
            "compliance autocure campaigns; the reactions engine fires "
            "compliance_coverage_low when the per-standard floor is breached."
        ),
        "by_standard": normalized_payloads,
        "totals": {
            "standards_with_coverage_artifact": standards_with_coverage,
            "standards_total": standards_total,
            "standards_pending_coverage": max(0, standards_total - len(rows_by_standard)),
            "scanned_standards": len(rows_by_standard),
            "domain_scanner_count": min(domain_scanner_count, standards_total),
            "baseline_companion_count": baseline_companion_count,
            "standards_pending_domain_scanner": max(0, standards_total - domain_scanner_count),
            "coverage_depth_counts": {
                "domain_or_projected_scanner": min(domain_scanner_count, standards_total),
                "baseline_standard_file_only": baseline_companion_count,
            },
            "average_known_compliance_rate": average,
            "known_compliance_rate_population": len(rates),
        },
        "metabolism_worklist": _build_metabolism_worklist(normalized_payloads),
        "non_goals": [
            "This ledger does not author compliance findings; per-standard scanners do that.",
            "This ledger does not authorize source mutation; it queues bounded work for controller-gated apply.",
            "This ledger is generated; do not hand-edit (it will be overwritten by the next builder run).",
        ],
    }


def build_ledger(repo_root: Path) -> dict:
    """
    [ACTION]
    - Teleology: Compose the cross-standard compliance ledger payload without
      writing it.
    """
    payloads = scan_all(repo_root)
    py_row = _project_python_coverage(repo_root)
    if py_row is not None:
        payloads = [py_row] + payloads
    return _compose_ledger(repo_root, payloads)


def _payload_for_standard(repo_root: Path, standard_id: str) -> dict:
    """
    [ACTION]
    - Teleology: Build one per-standard compliance payload through the same
      adapter authority used by the full ledger builder.
    """
    if standard_id == "std_python":
        py_row = _project_python_coverage(repo_root)
        if py_row is None:
            raise KeyError("std_python coverage artifact is missing")
        return py_row
    scanner = ADAPTERS.get(standard_id)
    if scanner is None:
        raise KeyError(f"No compliance adapter registered for {standard_id}")
    return scanner(repo_root)


def _load_existing_ledger(repo_root: Path) -> dict:
    path = repo_root / _LEDGER_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"{_LEDGER_PATH} is missing; run a full build before bounded row refresh"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{_LEDGER_PATH} must contain a JSON object")
    return payload


def _load_existing_rows_or_empty(repo_root: Path) -> list[dict]:
    """
    [ACTION]
    - Teleology: Let bounded row refresh materialize a selected compliance row
      even when the shared generated ledger has not yet been built.
    """
    try:
        existing = _load_existing_ledger(repo_root)
    except FileNotFoundError:
        return []
    existing_rows = existing.get("by_standard")
    if not isinstance(existing_rows, list):
        raise ValueError(f"{_LEDGER_PATH} is missing by_standard rows")
    return [row for row in existing_rows if isinstance(row, dict)]


def _merge_payloads(existing_rows: list[dict], updated_rows: list[dict]) -> list[dict]:
    updated_by_standard = {
        str(row.get("standard_id")): row
        for row in updated_rows
        if row.get("standard_id")
    }
    seen: set[str] = set()
    merged: list[dict] = []
    for row in existing_rows:
        standard_id = str(row.get("standard_id") or "")
        if standard_id in updated_by_standard:
            merged.append(updated_by_standard[standard_id])
            seen.add(standard_id)
        else:
            merged.append(row)
    for standard_id, row in updated_by_standard.items():
        if standard_id not in seen:
            merged.append(row)
    return merged


def refresh_ledger_rows(repo_root: Path, standard_ids: list[str]) -> dict:
    """
    [ACTION]
    - Teleology: Refresh selected generated ledger rows without forcing a
      whole-corpus scanner pass. If the generated ledger is absent, compose a
      bounded projection from the selected rows so the option surface can expose
      the chosen standard while totals still show partial coverage.
    """
    source_projection_present = (repo_root / _LEDGER_PATH).exists()
    try:
        existing_ledger = _load_existing_ledger(repo_root)
    except FileNotFoundError:
        existing_ledger = None
    existing_rows_raw = (existing_ledger or {}).get("by_standard")
    if existing_rows_raw is None:
        existing_rows = []
    elif not isinstance(existing_rows_raw, list):
        raise ValueError(f"{_LEDGER_PATH} is missing by_standard rows")
    else:
        existing_rows = [row for row in existing_rows_raw if isinstance(row, dict)]
    deduped_ids = list(dict.fromkeys(standard_ids))
    updated_rows = [_payload_for_standard(repo_root, standard_id) for standard_id in deduped_ids]
    merged_rows = _merge_payloads(
        existing_rows,
        updated_rows,
    )
    ledger = _compose_ledger(repo_root, merged_rows)
    totals = ledger.get("totals") or {}
    scanned = int(totals.get("scanned_standards") or 0)
    standards_total = int(totals.get("standards_total") or 0)
    partial_projection = standards_total > 0 and scanned < standards_total
    ledger["refresh_scope"] = {
        "mode": "bounded_standard_refresh",
        "selected_standard_ids": deduped_ids,
        "source_projection_present": source_projection_present,
        "source_row_count": len(existing_rows),
        "updated_row_count": len(updated_rows),
        "merged_row_count": scanned,
        "standards_total": standards_total,
        "partial_projection": partial_projection,
        "full_build_command": "./repo-python tools/meta/factory/build_compliance_ledger.py",
        "truth_boundary": (
            "Bounded refresh rows are valid for the selected standards only; "
            "run the full build before treating by_standard as complete."
            if partial_projection else
            "Bounded refresh preserved a complete by_standard row set."
        ),
    }
    ledger["projection_self_audit"] = _projection_self_audit(
        repo_root,
        existing_ledger=existing_ledger,
        existing_rows=existing_rows,
        merged_rows=merged_rows,
        selected_standard_ids=deduped_ids,
        updated_rows=updated_rows,
    )
    return ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build but do not write; exit 1 if the projection artifact is missing or error-severity findings exist.",
    )
    parser.add_argument("--report", action="store_true", help="Print summary to stdout.")
    parser.add_argument(
        "--standard-id",
        action="append",
        default=[],
        help=(
            "Refresh only the named standard row against the existing ledger. "
            "If the ledger is missing, bootstrap a bounded projection containing "
            "the selected rows. Repeatable. Uses the same adapter registry as "
            "the full builder."
        ),
    )
    parser.add_argument(
        "--ratchet-next",
        action="store_true",
        help=(
            "Bounded next-row mode: select the first missing registered domain "
            "scanner row from the materialized ledger, include "
            "std_compliance_coverage as the self-audit companion, and refresh "
            "only those rows. Pair with --check for first-contact no-write use."
        ),
    )
    parser.add_argument(
        "--ratchet-count",
        type=int,
        default=1,
        help=(
            "With --ratchet-next, refresh up to this many missing registered "
            "rows before adding the std_compliance_coverage self-audit "
            "companion. Default: 1."
        ),
    )
    parser.add_argument(
        "--microcosm-readiness",
        action="store_true",
        help=(
            "Bounded no-write packet for Microcosm public-substrate compliance "
            "readiness. Refreshes only std_microcosm and std_compliance_coverage "
            "in memory, then joins scanner-depth self-audit with active Work "
            "Ledger claim state and exact drilldowns."
        ),
    )
    args = parser.parse_args(argv)
    if args.ratchet_count < 1:
        parser.error("--ratchet-count must be >= 1")
    if args.ratchet_count != 1 and not args.ratchet_next:
        parser.error("--ratchet-count can only be used with --ratchet-next")
    if args.ratchet_next and args.standard_id:
        parser.error("--ratchet-next cannot be combined with explicit --standard-id")
    if args.microcosm_readiness and (args.ratchet_next or args.standard_id):
        parser.error(
            "--microcosm-readiness cannot be combined with --ratchet-next or --standard-id"
        )
    if args.microcosm_readiness and not args.check:
        parser.error(
            "--microcosm-readiness requires --check so it never broad-writes generated ledger state"
        )

    selected_standard_ids = (
        list(_MICROCOSM_READINESS_STANDARD_IDS)
        if args.microcosm_readiness else
        _ratchet_next_standard_ids(REPO_ROOT, limit=args.ratchet_count)
        if args.ratchet_next else
        args.standard_id
    )

    if args.ratchet_next:
        ledger = (
            refresh_ledger_rows(REPO_ROOT, selected_standard_ids)
            if selected_standard_ids else
            _ratchet_noop_ledger(REPO_ROOT)
        )
    else:
        ledger = (
            refresh_ledger_rows(REPO_ROOT, selected_standard_ids)
            if selected_standard_ids else
            build_ledger(REPO_ROOT)
        )
    if args.microcosm_readiness:
        ledger["microcosm_public_substrate_readiness"] = (
            _microcosm_public_substrate_readiness_packet(REPO_ROOT, ledger)
        )
    path = REPO_ROOT / _LEDGER_PATH
    projection_missing = args.check and not path.exists()

    error_findings = 0
    for row in ledger["by_standard"]:
        for f in row.get("findings") or []:
            if f.get("severity") == "error":
                error_findings += 1

    if not args.check:
        _atomic_write_json(path, ledger)

    check_failure_reasons: list[str] = []
    if projection_missing:
        check_failure_reasons.append("artifact_missing")
    if error_findings:
        check_failure_reasons.append("error_findings")

    if args.report or args.check:
        refresh_scope = ledger.get("refresh_scope") or {}
        self_audit = ledger.get("projection_self_audit") or {}
        microcosm_readiness = ledger.get("microcosm_public_substrate_readiness") or {}
        microcosm_claims = (
            microcosm_readiness.get("active_microcosm_claims")
            if isinstance(microcosm_readiness, dict) else
            {}
        ) or {}
        bounded_check = self_audit.get("bounded_check") or {}
        ratchet = self_audit.get("scanner_depth_ratchet") or {}
        summary = {
            "kind": "compliance_ledger_summary",
            "scanned_standards": ledger["totals"]["scanned_standards"],
            "standards_with_coverage_artifact": ledger["totals"]["standards_with_coverage_artifact"],
            "registered_adapter_count": self_audit.get("registered_adapter_count"),
            "registered_domain_adapter_count": self_audit.get("registered_domain_adapter_count"),
            "registered_baseline_adapter_count": self_audit.get("registered_baseline_adapter_count"),
            "standards_pending_domain_scanner": self_audit.get("standards_pending_domain_scanner"),
            "source_materialized_scanned_standards": self_audit.get("source_materialized_scanned_standards"),
            "source_missing_registered_rows_count": self_audit.get("source_missing_registered_rows_count"),
            "source_missing_domain_rows_count": self_audit.get("source_missing_domain_rows_count"),
            "source_missing_baseline_rows_count": self_audit.get("source_missing_baseline_rows_count"),
            "post_refresh_missing_registered_rows_count": self_audit.get("post_refresh_missing_registered_rows_count"),
            "average_known_compliance_rate": ledger["totals"]["average_known_compliance_rate"],
            "ready_now_count": len(ledger["metabolism_worklist"]["ready_now"]),
            "deferred_count": len(ledger["metabolism_worklist"]["deferred_until_scanner_authored"]),
            "error_findings": error_findings,
            "wrote_ledger": not args.check,
            "ledger_path": _LEDGER_PATH,
            "projection_status": "artifact_missing" if not path.exists() else "artifact_present",
            "projection_missing": projection_missing,
            "check_status": "failed" if check_failure_reasons else "ok",
            "check_failure_reasons": check_failure_reasons,
            "refreshed_standard_ids": selected_standard_ids,
            "ratchet_next": args.ratchet_next,
            "ratchet_count": args.ratchet_count if args.ratchet_next else None,
            "microcosm_readiness": args.microcosm_readiness,
            "microcosm_readiness_status": microcosm_readiness.get("status"),
            "microcosm_active_claim_count": microcosm_claims.get("active_claim_count"),
            "microcosm_active_session_count": microcosm_claims.get("active_session_count"),
            "microcosm_readiness_command": (
                (microcosm_readiness.get("next_proofs") or {}).get("readiness_command")
                if isinstance(microcosm_readiness, dict) else
                None
            ),
            "refresh_scope_mode": refresh_scope.get("mode"),
            "partial_projection": refresh_scope.get("partial_projection"),
            "projection_self_audit_status": self_audit.get("status"),
            "bounded_check_partial": bounded_check.get("partial_projection"),
            "bounded_check_did_refresh": bounded_check.get("did_refresh"),
            "bounded_check_did_not_refresh": bounded_check.get("did_not_refresh"),
            "scanner_depth_ratchet_status": ratchet.get("status"),
            "ratchet_candidate_standard_id": ratchet.get("candidate_standard_id"),
            "ratchet_candidate_adapter_kind": ratchet.get("candidate_adapter_kind"),
            "ratchet_closed_by_this_bounded_check": ratchet.get("closed_by_this_bounded_check"),
            "ratchet_selection_reason": ratchet.get("selection_reason"),
            "ratchet_next_standard_id": ratchet.get("post_refresh_next_standard_id"),
            "ratchet_next_command": ratchet.get("ratchet_next_command"),
            "ratchet_post_refresh_next_command": ratchet.get("post_refresh_next_command"),
            "next_exact_standard_id": self_audit.get("next_exact_standard_id"),
            "next_exact_check_command": self_audit.get("next_exact_check_command"),
        }
        if args.microcosm_readiness:
            summary["microcosm_public_substrate_readiness"] = microcosm_readiness
        print(json.dumps(summary, indent=2))

    return 1 if check_failure_reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
