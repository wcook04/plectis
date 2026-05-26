"""
Tests for PR 3 — attempt-aware stale recovery.

Each test runs against an isolated tmp_path family so it never touches the
real obsidian/, codex/, or state/ trees. The tests guard the controlling
invariants from /Users/willcook/.claude/plans/can-you-explore-a-valiant-moon.md
and codex/standards/observe_apply/std_raw_seed_attempt_recovery.json:

- attempt-aware fencing: claim_epoch is monotonic per paragraph; late writes
  with lower epoch (or with mismatched packet_digest, or against an abandoned
  attempt) MUST be rejected.
- partial-import evidence forces operator_review_required, never auto-abandon.
- packet existence alone is NOT partial-import evidence.
- duplicate import with same attempt_id + same packet_digest is a noop.
- packet_digest excludes its own field.
- preview never writes; commit writes only ledger + recovery report.
- ledger-status reports extended counts; metabolismd blackboard surfaces them.
"""
from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import raw_seed_attempt_recovery as recov
from system.lib import raw_seed_subagent_lane as lane
from system.lib import raw_seed_paragraph_ledger as ledger_mod
from system.lib.raw_seed_paragraph_ledger import (
    DistillationAttempt,
    ParagraphLedgerEntry,
    derive_attempt_status,
    load_ledger,
    next_claim_epoch_for_paragraph,
    save_ledger,
)


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------


def _build_family(tmp_path: Path, *, paragraph_ids: list[str] | None = None) -> tuple[Path, str]:
    """Create a minimal family workspace with raw_seed.json + empty ledger."""
    family_dir = tmp_path / "obsidian" / "okay lets do this" / "09 - test recovery"
    rs_dir = family_dir / "raw_seed"
    rs_dir.mkdir(parents=True)
    pids = paragraph_ids or ["par_test_001", "par_test_002"]
    raw_seed = {
        "kind": "raw_seed",
        "schema_version": "raw_seed_v1",
        "family_id": "09",
        "family_number": "09",
        "family_dir": str(family_dir.relative_to(tmp_path)),
        "paragraphs": [
            {
                "id": pid,
                "anchor": f"paragraph:{pid}",
                "section_path": ["test"],
                "line_start": idx + 1,
                "line_end": idx + 1,
                "plain_text": f"text for {pid} — bridge produces text and the system recurses.",
                "paragraph_fingerprint": f"fp_{idx:04d}",
            }
            for idx, pid in enumerate(pids)
        ],
        "updated_at": "2026-04-26T00:00:00+00:00",
    }
    # Canonical seed path is family-root, not under raw_seed/.
    (family_dir / "raw_seed.json").write_text(json.dumps(raw_seed), encoding="utf-8")
    # Family extracted_shards.json: empty until import.
    (family_dir / "extracted_shards.json").write_text(
        json.dumps({"shards": [], "extracted_at": "2026-04-26T00:00:00+00:00"}),
        encoding="utf-8",
    )
    return family_dir, str(family_dir.relative_to(tmp_path))


def _seed_ledger_with_in_flight(
    repo_root: Path,
    family_dir_rel: str,
    *,
    paragraph_id: str,
    attempt_id: str = "att_test_111",
    claim_epoch: int = 1,
    packet_digest: str = "sha256:abc123",
    started_at: str = "2026-04-26T10:00:00+00:00",
    lease_seconds: int = 1800,
) -> None:
    """Write a ledger with one in_flight attempt for the given paragraph."""
    started_dt = datetime.fromisoformat(started_at)
    expires = (started_dt + timedelta(seconds=lease_seconds)).isoformat()
    entry = ParagraphLedgerEntry(
        paragraph_id=paragraph_id,
        source_substrate="raw_seed",
        authored_by="operator",
        first_touched_at=started_at,
        last_touched_at=started_at,
        attempts=[
            DistillationAttempt(
                attempt_id=attempt_id,
                paragraph_id=paragraph_id,
                lane="subagent",
                cohort_id="cohort_test",
                started_at=started_at,
                source_substrate="raw_seed",
                authored_by="operator",
                claim_id="claim_test",
                claim_epoch=claim_epoch,
                packet_digest=packet_digest,
                lease_started_at=started_at,
                lease_expires_at=expires,
                lease_seconds=lease_seconds,
                attempt_status="in_flight",
            ),
        ],
    )
    save_ledger(repo_root, family_dir_rel, {paragraph_id: entry})


def _now_plus(seconds: int) -> str:
    return (datetime(2026, 4, 26, 10, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat()


# ---------------------------------------------------------------------------
# 1. Active in_flight attempt younger than lease stays in_flight
# ---------------------------------------------------------------------------


def test_active_in_flight_younger_than_lease_stays_in_flight(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(
        tmp_path, fam_rel, paragraph_id="par_test_001", lease_seconds=1800,
    )
    # Now is 10 minutes after lease start (still under 30-minute lease).
    _, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(600))
    assert plan.stale_attempts == []
    assert plan.actions == []


# ---------------------------------------------------------------------------
# 2. Expired attempt becomes stale_in_flight on apply
# ---------------------------------------------------------------------------


def test_expired_attempt_marked_stale_in_flight(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(
        tmp_path, fam_rel, paragraph_id="par_test_001", lease_seconds=1800,
    )
    # 60 minutes later: lease expired.
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(3600))
    assert len(plan.stale_attempts) == 1
    recov.apply_recovery(tmp_path, fam_rel, ledger, plan, commit=True)
    saved = load_ledger(tmp_path, fam_rel)
    att = saved["par_test_001"].attempts[0]
    # No partial evidence in this fixture → abandonment is the final state.
    assert derive_attempt_status(att) == "abandoned_stale_no_import_evidence"


# ---------------------------------------------------------------------------
# 3. Stale with no evidence can be abandoned
# ---------------------------------------------------------------------------


def test_stale_with_no_partial_evidence_can_abandon(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(7200))
    assert len(plan.abandonment_candidates) == 1
    assert plan.operator_review_attempts == []


# ---------------------------------------------------------------------------
# 4. Abandoned paragraph reclaim increments epoch
# ---------------------------------------------------------------------------


def test_abandoned_paragraph_reclaim_increments_epoch(tmp_path: Path) -> None:
    # Single-paragraph fixture so the dispatch can only pick par_test_001.
    _build_family(tmp_path, paragraph_ids=["par_test_001"])
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001", claim_epoch=1)
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(7200))
    recov.apply_recovery(tmp_path, fam_rel, ledger, plan, commit=True)
    # Now build a new dispatch packet and confirm epoch increments.
    payload = lane.build_subagent_dispatch_packet(
        family="09", repo_root=tmp_path, cohort_size=1, run_id="run_reclaim",
    )
    assert payload["status"] == "prepared"
    new_attempts = payload["attempts"]
    assert len(new_attempts) == 1
    assert new_attempts[0]["paragraph_id"] == "par_test_001"
    assert new_attempts[0]["claim_epoch"] == 2  # next_claim_epoch_for_paragraph


# ---------------------------------------------------------------------------
# 5/6/7. Late-import / fence rejections
# ---------------------------------------------------------------------------


def _build_packet_and_bundles(
    repo_root: Path,
    family_dir: str,
    *,
    run_id: str = "run_test",
    cohort_size: int = 1,
) -> tuple[Path, Path, dict]:
    payload = lane.build_subagent_dispatch_packet(
        family="09", repo_root=repo_root, cohort_size=cohort_size, run_id=run_id,
    )
    packet_path = repo_root / payload["packet_path"]
    # Build a trivial-but-passing bundle for the dispatched paragraphs.
    bundles = {
        "paragraphs": {
            entry["paragraph_id"]: {
                "shards": [
                    {
                        "id": f"atom_{entry['paragraph_id']}_a",
                        "clarified_statement": entry["text"][:80],
                        "support_excerpt": entry["text"][:30] or "x",
                        "voice_anchor": entry["text"][:20] or "x",
                        "raw_paragraph_ids": [entry["paragraph_id"]],
                        "parent_paragraph_id": entry["paragraph_id"],
                        "segment_ordinal": "A",
                        "compression_ratio": 0.7,
                        "distillation_confidence": 0.85,
                        "compression_notes": ["sentence_or_clause_split"],
                        "gestures_towards": [],
                    },
                ],
                "_summary": {
                    "teleology": "test",
                    "outcome": "1 shard",
                    "confidence": "MEDIUM",
                },
            }
            for entry in lane._load_json(packet_path).get("paragraphs") or []
        }
    }
    bundles_path = packet_path.parent / "bundles.json"
    bundles_path.write_text(json.dumps(bundles), encoding="utf-8")
    return packet_path, bundles_path, payload


def test_late_import_rejected_on_abandoned_attempt(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    packet_path, bundles_path, _ = _build_packet_and_bundles(tmp_path, fam_rel)
    # Manually mark the attempt abandoned (simulating recovery happening
    # before the late bundle returns).
    saved = load_ledger(tmp_path, fam_rel)
    par_id = next(iter(saved))
    saved[par_id].attempts[0].attempt_status = "abandoned_stale_no_import_evidence"
    save_ledger(tmp_path, fam_rel, saved)
    result = lane.import_subagent_bundles(
        packet_path=packet_path, bundles_path=bundles_path, repo_root=tmp_path,
    )
    assert result["status"] == "no_import"
    assert any(
        r["reason"] == "attempt_status_abandoned" for r in result["late_rejected_paragraphs"]
    )


def test_late_import_rejected_on_packet_digest_mismatch(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    packet_path, bundles_path, payload = _build_packet_and_bundles(tmp_path, fam_rel)
    # Tamper with the ledger's recorded packet_digest so on-disk and recorded
    # disagree. Importer must reject without mutating shards.
    saved = load_ledger(tmp_path, fam_rel)
    par_id = next(iter(saved))
    saved[par_id].attempts[0].packet_digest = "sha256:tampered"
    save_ledger(tmp_path, fam_rel, saved)
    result = lane.import_subagent_bundles(
        packet_path=packet_path, bundles_path=bundles_path, repo_root=tmp_path,
    )
    assert any(
        r["reason"] == "packet_digest_mismatch" for r in result["late_rejected_paragraphs"]
    )


def test_late_import_rejected_on_claim_epoch_lower(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    packet_path, bundles_path, _ = _build_packet_and_bundles(tmp_path, fam_rel)
    # Bump the ledger's recorded epoch above the packet's epoch.
    saved = load_ledger(tmp_path, fam_rel)
    par_id = next(iter(saved))
    saved[par_id].attempts[0].claim_epoch = 9
    # Reset packet_digest to match the on-disk packet so digest-mismatch does NOT
    # short-circuit the epoch check; we want to isolate the epoch path.
    on_disk = recov.compute_packet_digest(json.loads(packet_path.read_text(encoding="utf-8")))
    saved[par_id].attempts[0].packet_digest = on_disk
    save_ledger(tmp_path, fam_rel, saved)
    result = lane.import_subagent_bundles(
        packet_path=packet_path, bundles_path=bundles_path, repo_root=tmp_path,
    )
    assert any(
        r["reason"] == "claim_epoch_mismatch_lower" for r in result["late_rejected_paragraphs"]
    )


# ---------------------------------------------------------------------------
# 8. Duplicate import is idempotent
# ---------------------------------------------------------------------------


def test_duplicate_import_with_same_attempt_id_and_packet_digest_is_noop(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    packet_path, bundles_path, _ = _build_packet_and_bundles(tmp_path, fam_rel)
    r1 = lane.import_subagent_bundles(
        packet_path=packet_path, bundles_path=bundles_path, repo_root=tmp_path,
    )
    assert r1["status"] in {"imported", "no_import"}
    # Second import: every paragraph should hit duplicate_import_noop.
    r2 = lane.import_subagent_bundles(
        packet_path=packet_path, bundles_path=bundles_path, repo_root=tmp_path,
    )
    assert r2["duplicate_noop_paragraphs"], (
        f"expected duplicate_noop_paragraphs, got {r2}"
    )


# ---------------------------------------------------------------------------
# 9. Partial-import evidence forces operator_review_required
# 10. Packet existence alone does not force review
# ---------------------------------------------------------------------------


def test_partial_evidence_forces_operator_review_required(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    # Inject partial evidence: shard_count > 0 on the in_flight attempt.
    saved = load_ledger(tmp_path, fam_rel)
    saved["par_test_001"].attempts[0].shard_count = 3
    save_ledger(tmp_path, fam_rel, saved)
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(7200))
    assert len(plan.operator_review_attempts) == 1
    assert plan.abandonment_candidates == []


def test_packet_existence_alone_does_not_force_review(tmp_path: Path) -> None:
    """A packet on disk with no shard_entries / no shard_count / no extracted
    rows must NOT count as partial evidence."""
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    # Use the real dispatch path so a packet.json exists on disk.
    payload = lane.build_subagent_dispatch_packet(
        family="09", repo_root=tmp_path, cohort_size=1, run_id="run_packet_only",
    )
    assert payload["status"] == "prepared"
    # Force the lease to expire by overwriting it in the ledger.
    saved = load_ledger(tmp_path, fam_rel)
    par_id = next(iter(saved))
    saved[par_id].attempts[0].lease_expires_at = "2026-04-25T00:00:00+00:00"
    save_ledger(tmp_path, fam_rel, saved)
    _, plan = recov.plan_recovery(tmp_path, fam_rel, now="2026-04-26T12:00:00+00:00")
    assert plan.abandonment_candidates, "packet-only evidence must not block abandonment"
    assert plan.operator_review_attempts == []


# ---------------------------------------------------------------------------
# 11. Missing packet_digest legacy attempts surface as legacy
# ---------------------------------------------------------------------------


def test_missing_packet_digest_legacy_attempts_surface_as_legacy(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    # Hand-craft a legacy attempt with no packet_digest, no claim_id, no lease.
    legacy = ParagraphLedgerEntry(
        paragraph_id="par_test_001",
        attempts=[
            DistillationAttempt(
                attempt_id="att_legacy",
                paragraph_id="par_test_001",
                lane="subagent",
                cohort_id="cohort_legacy",
                started_at="2025-01-01T00:00:00+00:00",
                source_substrate="raw_seed",
                authored_by="operator",
                # No claim_id, claim_epoch=1 default, packet_digest=None,
                # lease_*=None, attempt_status=None.
            ),
        ],
    )
    save_ledger(tmp_path, fam_rel, {"par_test_001": legacy})
    saved = load_ledger(tmp_path, fam_rel)
    att = saved["par_test_001"].attempts[0]
    assert derive_attempt_status(att) == "legacy_missing_packet_digest"


# ---------------------------------------------------------------------------
# 12. New dispatch packets carry packet_digest
# 13. packet_digest excludes its own field
# ---------------------------------------------------------------------------


def test_new_dispatch_packets_carry_packet_digest(tmp_path: Path) -> None:
    _build_family(tmp_path)
    payload = lane.build_subagent_dispatch_packet(
        family="09", repo_root=tmp_path, cohort_size=1, run_id="run_digest",
    )
    assert payload["status"] == "prepared"
    pkt = json.loads((tmp_path / payload["packet_path"]).read_text(encoding="utf-8"))
    assert "packet_digest" in pkt
    assert pkt["packet_digest"].startswith("sha256:")


def test_packet_digest_excludes_its_own_field() -> None:
    base = {
        "kind": "raw_seed_subagent_dispatch_packet",
        "schema_version": "raw_seed_subagent_packet_v1",
        "run_id": "run_x",
        "paragraphs": [{"paragraph_id": "par_a", "claim_epoch": 1}],
    }
    # With and without the digest field embedded should produce the same hash.
    d1 = recov.compute_packet_digest(base)
    d2 = recov.compute_packet_digest({**base, "packet_digest": "sha256:nonsense"})
    d3 = recov.compute_packet_digest({**base, "packet_digest": "sha256:other"})
    assert d1 == d2 == d3


# ---------------------------------------------------------------------------
# 14. ledger-status reports extended counts
# ---------------------------------------------------------------------------


def test_ledger_status_reports_extended_counts(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    summary = lane.build_ledger_status_summary(
        family="09", repo_root=tmp_path,
    )
    assert "attempt_status_counts" in summary
    assert "stale_attempts_count" in summary
    assert "abandoned_count" in summary
    assert "operator_review_count" in summary
    assert "legacy_missing_packet_digest_count" in summary
    assert "type_a_recovery" in summary


def test_type_a_recovery_summary_does_not_double_count_stale_status(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    saved = load_ledger(tmp_path, fam_rel)
    saved["par_test_001"].attempts[0].attempt_status = "stale_in_flight"
    save_ledger(tmp_path, fam_rel, saved)

    summary = recov.type_a_recovery_summary(tmp_path, fam_rel, now=_now_plus(7200))

    assert summary["attempt_status_counts"]["stale_in_flight"] == 1
    assert summary["stale_attempts_count"] == 1


# ---------------------------------------------------------------------------
# 15. metabolismd blackboard surfaces stale Type A counts
# ---------------------------------------------------------------------------


def test_metabolismd_blackboard_surfaces_stale_type_a(tmp_path: Path) -> None:
    """Verify build_blackboard_projection accepts and projects type_a_recovery."""
    from system.lib import metabolism_blackboard, metabolism_store
    conn = metabolism_store.connect(tmp_path)
    sample = {
        "schema": recov.RECOVERY_REPORT_SCHEMA,
        "stale_attempts_count": 4,
        "abandoned_count": 1,
        "operator_review_count": 2,
        "legacy_missing_packet_digest_count": 0,
        "stale_pending_recovery": [
            {
                "paragraph_id": "par_x",
                "attempt_id": "att_x",
                "claim_epoch": 1,
                "lease_expires_at": "2026-04-26T01:00:00+00:00",
            }
        ],
    }
    proj = metabolism_blackboard.build_blackboard_projection(
        conn, type_a_recovery=sample,
    )
    assert proj["type_a_recovery"]["stale_attempts_count"] == 4
    md = metabolism_blackboard.render_blackboard_markdown(proj)
    assert "Type A attempt recovery" in md
    assert "stale: `4`" in md


# ---------------------------------------------------------------------------
# 16. Preview mode writes nothing
# 17. Commit writes only ledger + recovery report
# ---------------------------------------------------------------------------


def test_preview_mode_writes_nothing(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    ledger_path = (
        tmp_path / fam_rel / "raw_seed" / "raw_seed_paragraph_ledger.json"
    )
    before_bytes = ledger_path.read_bytes()
    recovery_report_path = tmp_path / "state" / "raw_seed" / "recovery" / "latest.json"
    assert not recovery_report_path.exists()
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(7200))
    recov.apply_recovery(tmp_path, fam_rel, ledger, plan, commit=False)
    # Ledger byte-identical; recovery report still absent.
    assert ledger_path.read_bytes() == before_bytes
    assert not recovery_report_path.exists()


def test_commit_writes_only_ledger_and_recovery_paths(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(tmp_path, fam_rel, paragraph_id="par_test_001")
    # Snapshot every file in the repo *except* the ledger and recovery dir.
    def snap(root: Path, *, excluded_prefixes: list[str]) -> dict[str, str]:
        out = {}
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if any(rel.startswith(pref) for pref in excluded_prefixes):
                continue
            out[rel] = recov.hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    excluded = [
        f"{fam_rel}/raw_seed/raw_seed_paragraph_ledger.json",
        "state/raw_seed/recovery/",
    ]
    before = snap(tmp_path, excluded_prefixes=excluded)
    ledger, plan = recov.plan_recovery(tmp_path, fam_rel, now=_now_plus(7200))
    recov.apply_recovery(tmp_path, fam_rel, ledger, plan, commit=True)
    after = snap(tmp_path, excluded_prefixes=excluded)
    assert before == after
    # Recovery report exists and matches schema.
    report_path = tmp_path / "state" / "raw_seed" / "recovery" / "latest.json"
    assert report_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == recov.RECOVERY_REPORT_SCHEMA
    assert report["commit"] is True


# ---------------------------------------------------------------------------
# 18. Reclaim chain: replaces_attempt_id is set
# ---------------------------------------------------------------------------


def test_reclaim_marks_replaced_by_attempt_id_chain(tmp_path: Path) -> None:
    _build_family(tmp_path)
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(
        tmp_path, fam_rel, paragraph_id="par_test_001",
        attempt_id="att_first",
    )
    # Abandon, then reclaim with explicit replaces_attempt_id.
    saved = load_ledger(tmp_path, fam_rel)
    saved["par_test_001"].attempts[0].attempt_status = "abandoned_stale_no_import_evidence"
    save_ledger(tmp_path, fam_rel, saved)
    saved = load_ledger(tmp_path, fam_rel)
    new_att = ledger_mod.record_dispatch(
        saved,
        paragraph_id="par_test_001",
        lane="subagent",
        cohort_id="cohort_reclaim",
        attempt_id="att_second",
        claim_epoch=2,
        packet_digest="sha256:second",
        replaces_attempt_id="att_first",
    )
    save_ledger(tmp_path, fam_rel, saved)
    final = load_ledger(tmp_path, fam_rel)
    first = final["par_test_001"].attempts[0]
    second = final["par_test_001"].attempts[1]
    assert first.attempt_id == "att_first"
    assert first.replaced_by_attempt_id == "att_second"
    assert second.attempt_id == "att_second"
    assert second.claim_epoch == 2
    assert next_claim_epoch_for_paragraph(final["par_test_001"]) == 3


def test_backlog_slice_reclaim_wires_replaces_attempt_id(tmp_path: Path) -> None:
    _build_family(tmp_path, paragraph_ids=["par_test_001"])
    fam_rel = "obsidian/okay lets do this/09 - test recovery"
    _seed_ledger_with_in_flight(
        tmp_path, fam_rel, paragraph_id="par_test_001", attempt_id="att_first",
    )
    saved = load_ledger(tmp_path, fam_rel)
    saved["par_test_001"].attempts[0].attempt_status = "abandoned_stale_no_import_evidence"
    save_ledger(tmp_path, fam_rel, saved)

    result = lane.build_subagent_dispatch_packet(
        family="09",
        repo_root=tmp_path,
        cohort_size=1,
        run_id="sub_reclaim_normal_path",
    )

    assert result["status"] == "prepared"
    final = load_ledger(tmp_path, fam_rel)
    first = final["par_test_001"].attempts[0]
    second = final["par_test_001"].attempts[1]
    assert first.attempt_id == "att_first"
    assert first.attempt_status == "reclaimed_by_new_attempt"
    assert first.replaced_by_attempt_id == second.attempt_id
    assert second.claim_epoch == 2


# ---------------------------------------------------------------------------
# Smoke: existing eval/gold tests still pass via cross-test sweep
#  (handled by the cross-cutting test suite — included here as a guard)
# ---------------------------------------------------------------------------


def test_existing_eval_and_gold_tests_still_load() -> None:
    """Cross-module import smoke. Catches accidental name removals."""
    from system.lib import raw_seed_eval as ev_mod  # noqa: F401
    from system.server.tests import test_raw_seed_eval as t_eval  # noqa: F401
    from system.server.tests import test_raw_seed_gold_regression as t_gold  # noqa: F401
