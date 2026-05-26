"""
[PURPOSE]
- Teleology: Orchestrate the Type A (Claude subagent) raw-seed distillation
  lane. Slice backlog into dispatch packets, validate and import worker
  bundles, surface ledger status. The actual subagent spawn happens in the
  live conductor session via the Agent tool; this library owns everything
  the CLI touches on either side of that seam.

[INTERFACE]
- Exports:
  - build_subagent_dispatch_packet
  - import_subagent_bundles
  - build_ledger_status_summary
  - SUBAGENT_RUN_ROOT_REL, DEFAULT_SUBAGENT_COHORT_SIZE, DEFAULT_SUBAGENT_WAVE_WIDTH
- Reads: raw_seed.json, raw_seed_shards.json, raw_seed_coverage.json, the
  paragraph ledger, and worker bundle JSON files.
- Writes: `state/raw_seed_subagent/<run_id>/packet.json`, the paragraph
  ledger, and (via import_distilled_shards) the family extracted_shards.json.

[FLOW]
- build_subagent_dispatch_packet: picks N paragraphs by strategy, marks each
  in_flight in the ledger, writes a self-contained packet the conductor
  hands to each Agent call.
- import_subagent_bundles: loads worker bundles, runs the validator, imports
  accepted shards via the shared import lane, records ledger transitions.
- build_ledger_status_summary: per-state counts + a sample of in-flight
  paragraphs so the operator can see what is outstanding.

[CONSTRAINTS]
- The lane does not dispatch subagents itself. The Agent tool is only
  available inside a live Claude session; the CLI prepares packets and
  ingests drops.
- Packet writes are idempotent per run_id; re-running with the same
  run_id overwrites the packet but preserves prior ledger attempts.
- `atomization_source` is always DISTILLATION_SUBAGENT_SOURCE from this
  import path; callers must not pass other values through this lane.
"""
from __future__ import annotations

import json
import random
import re
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from system.lib.raw_seed_atomization import (
    REPO_ROOT,
    family_extracted_shards_path,
    _load_json,
    _resolve_family_dir,
)
from system.lib.raw_seed_distillation import (
    DISTILLATION_SUBAGENT_SOURCE,
    _stable_atom_id,
    import_distilled_shards,
)
from system.lib.raw_seed_distillation_validator import (
    validate_distillation_bundle,
)
from system.lib.raw_seed_paragraph_ledger import (
    DEFAULT_LEASE_SECONDS,
    PARAGRAPH_STATES,
    compute_paragraph_state,
    derive_attempt_status,
    load_ledger,
    lookup_attempt,
    next_claim_epoch_for_paragraph,
    paragraph_ledger_path_for_family,
    paragraph_state_counts,
    record_dispatch,
    record_import,
    record_rejection,
    record_validator_result,
    save_ledger,
)
from system.lib.raw_seed_attempt_recovery import (
    compute_packet_digest,
    lease_expires_iso,
    log_late_import_rejection,
    type_a_recovery_summary,
)
from system.lib.raw_seed_registry import (
    agent_seed_json_path_for_family,
    raw_seed_json_path_for_family,
)

SUBAGENT_RUN_ROOT_REL = "state/raw_seed_subagent"
DEFAULT_SUBAGENT_COHORT_SIZE = 6
DEFAULT_SUBAGENT_WAVE_WIDTH = 2

Strategy = Literal["simple_first", "complex_last", "random"]

_REVERSAL_MARKERS = (
    "but actually",
    "wait no",
    "or maybe",
    "actually wait",
    "no wait",
    "hmm actually",
    "or actually",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_attempt_id_for_paragraph() -> str:
    return f"att_{uuid.uuid4().hex[:16]}"


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"sub_{stamp}_{uuid.uuid4().hex[:8]}"


def _paragraph_complexity_score(paragraph: Mapping[str, Any]) -> int:
    """Higher = more complex. Used by strategy to prefer simple or complex."""
    text = _paragraph_text(paragraph).lower()
    length = len(text)
    reversal_hits = sum(marker in text for marker in _REVERSAL_MARKERS)
    caps_run = sum(1 for word in text.split() if len(word) > 3 and word.isupper())
    hedge_hits = len(
        re.findall(
            r"\b(maybe|I guess|kind of|I don'?t know|I think|sort of)\b",
            text,
            flags=re.IGNORECASE,
        )
    )
    return reversal_hits * 3 + caps_run + hedge_hits + (length // 400)


def _select_paragraphs(
    paragraphs: list[dict[str, Any]],
    *,
    ledger,
    cohort_size: int,
    strategy: Strategy,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    untouched: list[dict[str, Any]] = []
    retryable_rejected: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        par_id = str(paragraph.get("id") or "")
        if not par_id:
            continue
        entry = ledger.get(par_id)
        if entry is None:
            untouched.append(paragraph)
            continue
        # PR 3: a paragraph whose only attempts are abandoned/reclaimed (no
        # shard evidence) reduces to 'untouched' via compute_paragraph_state.
        # That is the reclaim-eligibility test — include it in the untouched
        # bucket so the next dispatch picks it up with a higher claim_epoch.
        state = compute_paragraph_state(entry)
        if state == "untouched":
            untouched.append(paragraph)
            continue
        if state == "fully_rejected":
            retryable_rejected.append(paragraph)

    def _ordered(bucket: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if strategy == "random":
            rng = random.Random(seed)
            ordered = list(bucket)
            rng.shuffle(ordered)
            return ordered
        scored = [(p, _paragraph_complexity_score(p)) for p in bucket]
        if strategy == "simple_first":
            scored.sort(key=lambda row: row[1])
        else:  # complex_last → same sort, but we keep it explicit for readability
            scored.sort(key=lambda row: row[1])
        return [p for p, _score in scored]

    ordered = [*_ordered(untouched), *_ordered(retryable_rejected)]
    return ordered[:cohort_size]


def _latest_reclaimable_attempt_id(entry: Any) -> str | None:
    """Return the latest abandoned attempt that a new dispatch should replace."""
    for att in reversed(getattr(entry, "attempts", []) or []):
        if derive_attempt_status(att) == "abandoned_stale_no_import_evidence":
            return str(att.attempt_id or "").strip() or None
    return None


def _packet_path(repo_root: Path, run_id: str) -> Path:
    return repo_root / SUBAGENT_RUN_ROOT_REL / run_id / "packet.json"


def _normalize_text(text: str) -> str:
    return str(text or "").strip()


def _paragraph_text(paragraph: Mapping[str, Any]) -> str:
    for key in ("text", "plain_text", "raw_markdown", "source_text", "body"):
        value = paragraph.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _seed_json_path_for_substrate(family_dir: str, *, substrate: str) -> str:
    return (
        raw_seed_json_path_for_family(family_dir)
        if substrate == "raw_seed"
        else agent_seed_json_path_for_family(family_dir)
    )


def _normalize_substrate(value: str | None) -> str:
    token = str(value or "").strip()
    return token or "raw_seed"


def _paragraph_authored_by(paragraph: Mapping[str, Any], *, substrate: str) -> str:
    token = str(paragraph.get("authored_by") or "").strip()
    if token:
        return token
    return "operator" if substrate == "raw_seed" else "agent_collective"


def build_subagent_dispatch_packet(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    cohort_size: int = DEFAULT_SUBAGENT_COHORT_SIZE,
    strategy: Strategy = "simple_first",
    wave_width: int = DEFAULT_SUBAGENT_WAVE_WIDTH,
    run_id: str | None = None,
    seed: int | None = None,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    """Pick N paragraphs, mark them in_flight, write a dispatch packet."""
    family_token = str(family).strip() or "09"
    substrate_token = _normalize_substrate(substrate)
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(
            f"Could not resolve family dir for family={family_token!r}"
        )

    seed_payload = _load_json(
        repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate_token)
    )
    if not seed_payload:
        raise FileNotFoundError(f"{substrate_token}.json missing for family {family_token}")

    paragraphs = [
        dict(p)
        for p in seed_payload.get("paragraphs") or []
        if isinstance(p, Mapping) and p.get("id")
    ]
    ledger = load_ledger(repo_root, family_dir)

    cohort = _select_paragraphs(
        paragraphs,
        ledger=ledger,
        cohort_size=max(1, int(cohort_size)),
        strategy=strategy,
        seed=seed,
    )
    if not cohort:
        return {
            "ok": True,
            "status": "noop",
            "family": family_token,
            "substrate": substrate_token,
            "reason": "no_untouched_paragraphs",
            "cohort_size_requested": cohort_size,
        }

    run_id = run_id or _new_run_id()
    cohort_id = f"cohort_{run_id}"
    claim_id = f"claim_{run_id}"
    lease_seconds = DEFAULT_LEASE_SECONDS
    now_iso = _utc_now()
    lease_expires = lease_expires_iso(now_iso, lease_seconds)

    # PR 3: allocate attempt_ids upfront so the packet payload — including
    # attempt_id on every paragraph — is the byte-equal input both to the
    # digest computation here and to compute_packet_digest in the importer.
    # Otherwise the on-disk packet (with attempt_id) would not match the
    # digest computed from the pre-attempt_id payload, producing spurious
    # packet_digest_mismatch rejections on duplicate import.
    packet_paragraphs: list[dict[str, Any]] = []
    paragraph_epochs: dict[str, int] = {}
    paragraph_attempt_ids: dict[str, str] = {}
    paragraph_replaces_attempt_ids: dict[str, str] = {}
    for paragraph in cohort:
        par_id = str(paragraph.get("id"))
        existing_entry = ledger.get(par_id)
        epoch = (
            next_claim_epoch_for_paragraph(existing_entry)
            if existing_entry is not None
            else 1
        )
        paragraph_epochs[par_id] = epoch
        if existing_entry is not None:
            replaces_attempt_id = _latest_reclaimable_attempt_id(existing_entry)
            if replaces_attempt_id:
                paragraph_replaces_attempt_ids[par_id] = replaces_attempt_id
        attempt_id = _new_attempt_id_for_paragraph()
        paragraph_attempt_ids[par_id] = attempt_id
        packet_paragraphs.append({
            "paragraph_id": par_id,
            "attempt_id": attempt_id,
            "text": _normalize_text(_paragraph_text(paragraph)),
            "raw_seed_anchor": paragraph.get("anchor"),
            "section_path": paragraph.get("section_path"),
            "line_start": paragraph.get("line_start"),
            "line_end": paragraph.get("line_end"),
            "fingerprint": paragraph.get("paragraph_fingerprint")
            or paragraph.get("fingerprint"),
            "source_substrate": substrate_token,
            "authored_by": _paragraph_authored_by(paragraph, substrate=substrate_token),
            "claim_id": claim_id,
            "claim_epoch": epoch,
            "lease_started_at": now_iso,
            "lease_expires_at": lease_expires,
            "lease_seconds": lease_seconds,
        })

    pre_digest_payload = {
        "kind": "raw_seed_subagent_dispatch_packet",
        "schema_version": "raw_seed_subagent_packet_v1",
        "run_id": run_id,
        "cohort_id": cohort_id,
        "claim_id": claim_id,
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "generated_at": now_iso,
        "strategy": strategy,
        "wave_width": int(wave_width),
        "cohort_size": len(cohort),
        "lease_seconds": lease_seconds,
        "paragraphs": packet_paragraphs,
    }
    packet_digest = compute_packet_digest(pre_digest_payload)

    dispatch_records: list[dict[str, Any]] = []
    for paragraph_entry in packet_paragraphs:
        par_id = paragraph_entry["paragraph_id"]
        attempt = record_dispatch(
            ledger,
            paragraph_id=par_id,
            lane="subagent",
            cohort_id=cohort_id,
            attempt_id=paragraph_attempt_ids[par_id],
            source_substrate=substrate_token,
            authored_by=paragraph_entry["authored_by"],
            claim_id=claim_id,
            claim_epoch=paragraph_epochs[par_id],
            packet_digest=packet_digest,
            lease_started_at=now_iso,
            lease_expires_at=lease_expires,
            lease_seconds=lease_seconds,
            replaces_attempt_id=paragraph_replaces_attempt_ids.get(par_id),
        )
        dispatch_records.append(asdict(attempt))

    save_ledger(repo_root, family_dir, ledger)

    packet_path = _packet_path(repo_root, run_id)
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_payload = {
        **pre_digest_payload,
        "packet_digest": packet_digest,
    }
    packet_path.write_text(
        json.dumps(packet_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "ok": True,
        "status": "prepared",
        "family": family_token,
        "substrate": substrate_token,
        "run_id": run_id,
        "cohort_id": cohort_id,
        "claim_id": claim_id,
        "packet_digest": packet_digest,
        "lease_seconds": lease_seconds,
        "lease_expires_at": lease_expires,
        "cohort_size": len(cohort),
        "wave_width": int(wave_width),
        "strategy": strategy,
        "packet_path": str(packet_path.relative_to(repo_root.resolve())),
        "ledger_path": paragraph_ledger_path_for_family(family_dir),
        "selected_paragraph_ids": [p["paragraph_id"] for p in packet_paragraphs],
        "attempts": dispatch_records,
    }


def _collect_bundle_for_paragraph(
    bundles_payload: Mapping[str, Any], paragraph_id: str
) -> Mapping[str, Any] | None:
    # Accept either {paragraphs: {par_id: bundle}} or a flat bundle with all shards.
    if "paragraphs" in bundles_payload and isinstance(
        bundles_payload["paragraphs"], Mapping
    ):
        candidate = bundles_payload["paragraphs"].get(paragraph_id)
        if isinstance(candidate, Mapping):
            return candidate
        return None
    # Flat bundle: filter shards by parent_paragraph_id.
    shards = [
        shard
        for shard in bundles_payload.get("shards") or []
        if isinstance(shard, Mapping)
        and str(shard.get("parent_paragraph_id") or "") == paragraph_id
    ]
    if not shards:
        return None
    summary = bundles_payload.get("_summary") or {
        "teleology": "subagent_flat_bundle_reshape",
        "outcome": f"{len(shards)} shard(s) reshaped for paragraph",
        "confidence": "MEDIUM",
    }
    return {"shards": shards, "_summary": summary}


def _write_per_paragraph_artifact(
    *, repo_root: Path, run_id: str, paragraph_id: str, bundle: Mapping[str, Any]
) -> Path:
    artifact_dir = repo_root / SUBAGENT_RUN_ROOT_REL / run_id / "bundles_normalized"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{paragraph_id}.json"
    artifact_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return artifact_path


def _canonicalize_shard_id(shard: Mapping[str, Any]) -> str:
    return _stable_atom_id(
        str(shard.get("parent_paragraph_id") or ""),
        str(shard.get("segment_ordinal") or ""),
        str(shard.get("clarified_statement") or ""),
        voice_anchor=str(shard.get("voice_anchor") or ""),
        support_excerpt=str(shard.get("support_excerpt") or ""),
    )


def _canonicalize_shard(shard: Mapping[str, Any]) -> dict[str, Any]:
    canonical = dict(shard)
    canonical["id"] = _canonicalize_shard_id(canonical)
    return canonical


def import_subagent_bundles(
    *,
    packet_path: str | Path,
    bundles_path: str | Path,
    repo_root: Path = REPO_ROOT,
    strict: bool = False,
    substrate: str | None = None,
) -> dict[str, Any]:
    """Validate and import subagent-returned bundles, record ledger transitions.

    V1 posture:
    - In non-strict (advisory) mode, shards flagged only are imported; shards
      rejected by the validator are dropped from the subagent lane even in
      advisory — the subagent is cheap and can re-dispatch, so quality bar
      here is higher than the bridge lane's.
    - In strict mode, any paragraph with ≥ 1 rejected shard is fully dropped
      from this import (all shards skipped) and the paragraph stays available
      for a retry attempt.
    """
    packet_path_resolved = Path(packet_path)
    if not packet_path_resolved.is_absolute():
        packet_path_resolved = repo_root / packet_path_resolved
    bundles_path_resolved = Path(bundles_path)
    if not bundles_path_resolved.is_absolute():
        bundles_path_resolved = repo_root / bundles_path_resolved

    packet_payload = _load_json(packet_path_resolved)
    if not packet_payload:
        raise FileNotFoundError(f"Packet not found or unreadable: {packet_path}")

    bundles_payload = _load_json(bundles_path_resolved) or {}

    family_token = str(packet_payload.get("family") or "09")
    substrate_token = _normalize_substrate(
        substrate or str(packet_payload.get("substrate") or "raw_seed")
    )
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(
            f"Could not resolve family dir for family={family_token!r}"
        )
    seed_payload = _load_json(
        repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate_token)
    ) or {}
    paragraphs_by_id = {
        str(p.get("id")): p
        for p in seed_payload.get("paragraphs") or []
        if isinstance(p, Mapping) and p.get("id")
    }
    ledger = load_ledger(repo_root, family_dir)

    per_paragraph_results: list[dict[str, Any]] = []
    imported_artifacts: list[Path] = []
    no_bundle_paragraphs: list[str] = []
    rejected_paragraphs: list[str] = []
    late_rejected_paragraphs: list[dict[str, Any]] = []
    duplicate_noop_paragraphs: list[str] = []
    accepted_shards_by_paragraph: dict[str, list[str]] = {}
    attempt_ids_by_paragraph: dict[str, str] = {}

    # PR 3: recompute the packet's digest from disk and compare against the
    # ledger-recorded digest for each attempt. Mismatch / abandoned / lower-epoch
    # bundles are rejected with an audit row before any import side-effect.
    on_disk_packet_digest = compute_packet_digest(packet_payload)
    declared_packet_digest = packet_payload.get("packet_digest")

    for packet_entry in packet_payload.get("paragraphs") or []:
        if not isinstance(packet_entry, Mapping):
            continue
        par_id = str(packet_entry.get("paragraph_id") or "")
        attempt_id = str(packet_entry.get("attempt_id") or "")
        if not par_id or not attempt_id:
            continue

        # Late-import / duplicate-import / fence-token check ----------------
        ledger_entry = ledger.get(par_id)
        ledger_attempt = lookup_attempt(ledger_entry, attempt_id) if ledger_entry else None
        recorded_status = (
            derive_attempt_status(ledger_attempt) if ledger_attempt is not None else None
        )
        recorded_digest = ledger_attempt.packet_digest if ledger_attempt else None
        recorded_epoch = ledger_attempt.claim_epoch if ledger_attempt else None
        packet_epoch_raw = packet_entry.get("claim_epoch")
        try:
            packet_epoch = int(packet_epoch_raw) if packet_epoch_raw is not None else None
        except (TypeError, ValueError):
            packet_epoch = None

        rejection_reason: str | None = None
        if ledger_attempt is None:
            rejection_reason = "no_attempt_in_ledger"
        elif recorded_status == "abandoned_stale_no_import_evidence":
            rejection_reason = "attempt_status_abandoned"
        elif recorded_status == "reclaimed_by_new_attempt":
            rejection_reason = "attempt_status_reclaimed"
        elif (
            recorded_digest is not None
            and on_disk_packet_digest is not None
            and recorded_digest != on_disk_packet_digest
        ):
            # If the importer is replaying the same packet bytes (declared
            # digest matches on-disk digest), then a recorded mismatch means
            # the attempt was reclaimed under a newer packet — reject.
            rejection_reason = "packet_digest_mismatch"
        elif (
            recorded_epoch is not None
            and packet_epoch is not None
            and packet_epoch < recorded_epoch
        ):
            rejection_reason = "claim_epoch_mismatch_lower"

        if rejection_reason is not None:
            log_late_import_rejection(
                repo_root,
                paragraph_id=par_id,
                attempt_id_in_packet=attempt_id,
                packet_digest_in_packet=declared_packet_digest if isinstance(declared_packet_digest, str) else None,
                ledger_attempt_status=recorded_status,
                ledger_packet_digest=recorded_digest,
                ledger_claim_epoch=recorded_epoch,
                rejection_reason=rejection_reason,
            )
            late_rejected_paragraphs.append({
                "paragraph_id": par_id,
                "attempt_id": attempt_id,
                "reason": rejection_reason,
            })
            per_paragraph_results.append({
                "paragraph_id": par_id,
                "outcome": "late_import_rejected",
                "reason": rejection_reason,
            })
            continue

        # Idempotent duplicate: this attempt already imported with the same
        # digest. Skip without mutating anything.
        if (
            recorded_status == "imported"
            and (
                recorded_digest is None
                or recorded_digest == on_disk_packet_digest
            )
        ):
            duplicate_noop_paragraphs.append(par_id)
            per_paragraph_results.append({
                "paragraph_id": par_id,
                "outcome": "duplicate_import_noop",
            })
            continue

        source = paragraphs_by_id.get(par_id) or {"id": par_id}
        paragraph_substrate = _normalize_substrate(
            packet_entry.get("source_substrate")
            or source.get("source_substrate")
            or substrate_token
        )
        paragraph_author = _paragraph_authored_by(
            {
                **dict(source),
                "authored_by": packet_entry.get("authored_by") or source.get("authored_by"),
            },
            substrate=paragraph_substrate,
        )
        bundle = _collect_bundle_for_paragraph(bundles_payload, par_id)
        if bundle is None:
            no_bundle_paragraphs.append(par_id)
            record_rejection(
                ledger,
                paragraph_id=par_id,
                attempt_id=attempt_id,
                reason="no_bundle_returned",
                source_substrate=paragraph_substrate,
                authored_by=paragraph_author,
            )
            per_paragraph_results.append(
                {"paragraph_id": par_id, "outcome": "no_bundle"}
            )
            continue

        result = validate_distillation_bundle(
            bundle, source, strict=strict, force_accept=False
        )

        if result.bundle_rejected:
            rejected_paragraphs.append(par_id)
            record_rejection(
                ledger,
                paragraph_id=par_id,
                attempt_id=attempt_id,
                reason=result.bundle_rejection_reason or "bundle_rejected",
                source_substrate=paragraph_substrate,
                authored_by=paragraph_author,
            )
            per_paragraph_results.append(
                {
                    "paragraph_id": par_id,
                    "outcome": "bundle_rejected",
                    "reason": result.bundle_rejection_reason,
                }
            )
            continue

        accepted_canonical = [_canonicalize_shard(shard) for shard in result.accepted]
        flagged_canonical = [
            (_canonicalize_shard(shard), reason) for shard, reason in result.flagged
        ]
        rejected_canonical = [
            (_canonicalize_shard(shard), reason) for shard, reason in result.rejected
        ]
        flagged_ids = [str(shard.get("id") or "") for shard, _reason in flagged_canonical]
        rejected_ids = [str(shard.get("id") or "") for shard, _reason in rejected_canonical]
        rejected_reasons = {
            str(shard.get("id") or ""): reason
            for shard, reason in rejected_canonical
        }
        rejected_id_set = {shard_id for shard_id in rejected_ids if shard_id}
        accepted_for_import = [
            dict(shard)
            for shard in accepted_canonical
            if str(shard.get("id") or shard.get("segment_ordinal") or "")
            not in rejected_id_set
        ]
        accepted_ids = [
            str(shard.get("id") or shard.get("segment_ordinal") or "")
            for shard in accepted_for_import
        ]
        record_validator_result(
            ledger,
            paragraph_id=par_id,
            attempt_id=attempt_id,
            lane="subagent",
            accepted_shard_ids=accepted_ids,
            flagged_shard_ids=flagged_ids,
            rejected_shard_ids=rejected_ids,
            rejected_reasons=rejected_reasons,
            source_substrate=paragraph_substrate,
            authored_by=paragraph_author,
        )
        # In strict mode, drop the whole paragraph if any shard was rejected.
        if strict and rejected_ids:
            record_rejection(
                ledger,
                paragraph_id=par_id,
                attempt_id=attempt_id,
                reason="strict_mode_dropped_rejected_shards",
                source_substrate=paragraph_substrate,
                authored_by=paragraph_author,
            )
            per_paragraph_results.append(
                {
                    "paragraph_id": par_id,
                    "outcome": "strict_drop",
                    "accepted": len(accepted_ids),
                    "flagged": len(flagged_ids),
                    "rejected": len(rejected_ids),
                    "rejected_reasons": list(rejected_reasons.values()),
                }
            )
            continue

        if not accepted_for_import:
            record_rejection(
                ledger,
                paragraph_id=par_id,
                attempt_id=attempt_id,
                reason="no_shards_accepted",
                source_substrate=paragraph_substrate,
                authored_by=paragraph_author,
            )
            per_paragraph_results.append(
                {
                    "paragraph_id": par_id,
                    "outcome": "all_rejected",
                    "flagged": len(flagged_ids),
                    "rejected": len(rejected_ids),
                    "rejected_reasons": list(rejected_reasons.values()),
                }
            )
            continue

        accept_bundle = {
            "shards": accepted_for_import,
            "_summary": bundle.get("_summary") or {
                "teleology": "subagent_lane_import",
                "outcome": f"{len(accepted_for_import)} shard(s) accepted for {par_id}",
                "confidence": "MEDIUM",
            },
        }
        artifact_path = _write_per_paragraph_artifact(
            repo_root=repo_root,
            run_id=str(packet_payload.get("run_id")),
            paragraph_id=par_id,
            bundle=accept_bundle,
        )
        imported_artifacts.append(artifact_path)
        accepted_shards_by_paragraph[par_id] = accepted_ids
        attempt_ids_by_paragraph[par_id] = attempt_id
        per_paragraph_results.append(
            {
                "paragraph_id": par_id,
                "outcome": "imported",
                "accepted": len(accepted_ids),
                "flagged": len(flagged_ids),
                "rejected": len(rejected_ids),
                "rejected_reasons": list(rejected_reasons.values()),
                "artifact": str(artifact_path.relative_to(repo_root.resolve())),
            }
        )

    if not imported_artifacts:
        save_ledger(repo_root, family_dir, ledger)
        return {
            "ok": True,
            "status": "no_import",
            "family": family_token,
            "substrate": substrate_token,
            "packet_path": str(
                packet_path_resolved.relative_to(repo_root.resolve())
            ),
            "no_bundle_paragraphs": no_bundle_paragraphs,
            "rejected_paragraphs": rejected_paragraphs,
            "late_rejected_paragraphs": late_rejected_paragraphs,
            "duplicate_noop_paragraphs": duplicate_noop_paragraphs,
            "per_paragraph_results": per_paragraph_results,
            "totals": _totals_from_results(per_paragraph_results),
        }

    # import_distilled_shards expects either a run_root or an artifact_path per call.
    # Call it once per accepted artifact and collect imported shard ids.
    import_summaries: list[dict[str, Any]] = []
    for artifact_path in imported_artifacts:
        summary = import_distilled_shards(
            family=family_token,
            repo_root=repo_root,
            artifact_path=artifact_path,
            atomization_source=DISTILLATION_SUBAGENT_SOURCE,
            substrate=substrate_token,
        )
        import_summaries.append({"artifact": str(artifact_path.name), **_compact_import_summary(summary)})

    # Walk extracted_shards to find which ids made it in; mark ledger.
    extracted_payload = _load_json(
        repo_root / family_extracted_shards_path(family_dir)
    ) or {"shards": []}
    all_extracted_ids_by_parent: dict[str, set[str]] = {}
    for shard in extracted_payload.get("shards") or []:
        if not isinstance(shard, Mapping):
            continue
        par_id = str(shard.get("parent_paragraph_id") or "")
        shard_id = str(shard.get("id") or "")
        if par_id and shard_id:
            all_extracted_ids_by_parent.setdefault(par_id, set()).add(shard_id)

    for par_id, _accepted_ordinals in accepted_shards_by_paragraph.items():
        extracted_ids = all_extracted_ids_by_parent.get(par_id, set())
        attempt_id = attempt_ids_by_paragraph.get(par_id)
        if not attempt_id:
            continue
        record_import(
            ledger,
            paragraph_id=par_id,
            attempt_id=attempt_id,
            imported_shard_ids=sorted(extracted_ids),
            lane="subagent",
            source_substrate=substrate_token,
            authored_by=_paragraph_authored_by(
                paragraphs_by_id.get(par_id) or {},
                substrate=substrate_token,
            ),
        )

    save_ledger(repo_root, family_dir, ledger)

    return {
        "ok": True,
        "status": "imported",
        "family": family_token,
        "substrate": substrate_token,
        "packet_path": str(packet_path_resolved.relative_to(repo_root.resolve())),
        "bundles_path": str(bundles_path_resolved.relative_to(repo_root.resolve())),
        "strict": strict,
        "no_bundle_paragraphs": no_bundle_paragraphs,
        "rejected_paragraphs": rejected_paragraphs,
        "late_rejected_paragraphs": late_rejected_paragraphs,
        "duplicate_noop_paragraphs": duplicate_noop_paragraphs,
        "per_paragraph_results": per_paragraph_results,
        "totals": _totals_from_results(per_paragraph_results),
        "import_summaries": import_summaries,
    }


def _totals_from_results(per_paragraph_results: list[dict[str, Any]]) -> dict[str, int]:
    counter: dict[str, int] = {}
    for entry in per_paragraph_results:
        outcome = str(entry.get("outcome") or "unknown")
        counter[outcome] = counter.get(outcome, 0) + 1
    return counter


def _compact_import_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "imported_count": summary.get("imported_count"),
        "replaced_count": summary.get("replaced_count"),
        "merge_note": summary.get("merge_note"),
        "validator_report_totals": (
            summary.get("extracted_payload", {})
            .get("validator_report", {})
            .get("totals")
            if isinstance(summary.get("extracted_payload"), Mapping)
            else None
        ),
    }


def build_ledger_status_summary(
    *,
    family: str,
    repo_root: Path = REPO_ROOT,
    sample_size: int = 5,
    substrate: str = "raw_seed",
) -> dict[str, Any]:
    family_token = str(family).strip() or "09"
    substrate_token = _normalize_substrate(substrate)
    family_dir = _resolve_family_dir(repo_root, family_token)
    if not family_dir:
        raise FileNotFoundError(
            f"Could not resolve family dir for family={family_token!r}"
        )
    seed_payload = _load_json(
        repo_root / _seed_json_path_for_substrate(family_dir, substrate=substrate_token)
    )
    known_paragraph_ids = [
        str(p.get("id"))
        for p in (seed_payload or {}).get("paragraphs") or []
        if isinstance(p, Mapping) and p.get("id")
    ]
    ledger = load_ledger(repo_root, family_dir)
    counts = paragraph_state_counts(ledger, known_paragraph_ids=known_paragraph_ids)

    # Sample in_flight paragraphs (these are the ones a conductor might want to chase).
    in_flight_sample: list[dict[str, Any]] = []
    for par_id, entry in ledger.items():
        state = compute_paragraph_state(entry)
        if state == "in_flight" and len(in_flight_sample) < sample_size:
            last_attempt = entry.attempts[-1] if entry.attempts else None
            in_flight_sample.append(
                {
                    "paragraph_id": par_id,
                    "last_attempt_id": last_attempt.attempt_id if last_attempt else None,
                    "lane": last_attempt.lane if last_attempt else None,
                    "started_at": last_attempt.started_at if last_attempt else None,
                }
            )

    # PR 3 — attempt-aware histogram + recovery summary surface.
    attempt_status_counts: dict[str, int] = {}
    for entry in ledger.values():
        for att in entry.attempts:
            status = derive_attempt_status(att)
            attempt_status_counts[status] = attempt_status_counts.get(status, 0) + 1

    recovery_summary = type_a_recovery_summary(repo_root, family_dir)

    return {
        "ok": True,
        "family": family_token,
        "family_dir": family_dir,
        "substrate": substrate_token,
        "ledger_path": paragraph_ledger_path_for_family(family_dir),
        "known_paragraph_count": len(known_paragraph_ids),
        "tracked_paragraph_count": len(ledger),
        "state_counts": counts,
        "state_enum": list(PARAGRAPH_STATES),
        "in_flight_sample": in_flight_sample,
        "attempt_status_counts": attempt_status_counts,
        "stale_attempts_count": recovery_summary.get("stale_attempts_count", 0),
        "abandoned_count": recovery_summary.get("abandoned_count", 0),
        "operator_review_count": recovery_summary.get("operator_review_count", 0),
        "legacy_missing_packet_digest_count": recovery_summary.get(
            "legacy_missing_packet_digest_count", 0
        ),
        "type_a_recovery": recovery_summary,
    }


__all__ = [
    "SUBAGENT_RUN_ROOT_REL",
    "DEFAULT_SUBAGENT_COHORT_SIZE",
    "DEFAULT_SUBAGENT_WAVE_WIDTH",
    "build_subagent_dispatch_packet",
    "import_subagent_bundles",
    "build_ledger_status_summary",
]
