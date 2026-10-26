#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Materialize a candidate-only compliance_autocure campaign packet
  from the hologram-projected compliance ledger. Wave_004A; never mutates
  source. Writes one packet under
  state/meta_missions/compliance_autocure/<slug>/campaign_packet.json that a
  controller can review and approve before any actual compliance fixup.
- Mechanism: Build the compliance_coverage signal, project each ready_now
  worklist entry plus any per-standard rows below the floor into
  candidate_targets, write atomically.
- Non-goal: Author findings, mutate any standard, fire providers.

[INTERFACE]
- CLI: --check, --report, --write, --max-targets N, --campaign-slug SLUG.

[FLOW]
- Read signal; if not coverage_low, exit 0 with no_op summary.
- Otherwise pick ready_now + below_floor entries, build packet, optionally write.

[CONSTRAINTS]
- Forbid: source mutation, provider dispatch.
- Determinism: same signal digest -> same campaign_packet content.
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

from system.lib.compliance_reaction_signals import build_compliance_coverage_signal  # noqa: E402


_PACKET_ROOT = "state/meta_missions/compliance_autocure"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def build_campaign_packet(
    repo_root: Path,
    *,
    max_targets: int = 12,
    campaign_slug: str | None = None,
) -> dict:
    signal = build_compliance_coverage_signal(repo_root)
    if not signal.get("coverage_low"):
        return {
            "kind": "compliance_autocure_campaign",
            "schema_version": "compliance_autocure_campaign_v1",
            "no_op": True,
            "reason": "coverage_low=false; no campaign packet emitted.",
            "signal": signal,
        }
    ready_now = list(signal.get("ready_now") or [])
    below_floor = list(signal.get("below_floor") or [])
    candidate_targets: list[dict] = []
    for entry in ready_now[:max_targets]:
        if not isinstance(entry, dict):
            continue
        sid = str(entry.get("standard_id") or "")
        if not sid:
            continue
        candidate_targets.append({
            "standard_id": sid,
            "operation_kind": str(entry.get("operation_kind") or "compliance_autocure_campaign"),
            "rationale": str(entry.get("rationale") or "ready_now metabolism worklist entry"),
            "candidate_target_paths": [f"codex/standards/{sid}.json"],
            "source": "ready_now",
        })
    remaining = max_targets - len(candidate_targets)
    if remaining > 0:
        for entry in below_floor[:remaining]:
            if not isinstance(entry, dict):
                continue
            sid = str(entry.get("standard_id") or "")
            if not sid:
                continue
            candidate_targets.append({
                "standard_id": sid,
                "operation_kind": "compliance_autocure_campaign",
                "rationale": (
                    f"compliance_rate={entry.get('compliance_rate')} below floor; "
                    f"trigger_state={entry.get('metabolism_trigger_state')}"
                ),
                "candidate_target_paths": [f"codex/standards/{sid}.json"],
                "source": "below_floor",
            })
    digest = signal.get("digest") or ""
    slug = campaign_slug or f"compliance_autocure_{digest}"
    return {
        "kind": "compliance_autocure_campaign",
        "schema_version": "compliance_autocure_campaign_v1",
        "campaign_slug": slug,
        "source_digest": digest,
        "generated_at": _utc_now(),
        "standard_ref": "codex/standards/std_compliance_coverage.json",
        "source_path": signal.get("source_path"),
        "authority_tier": "authoring_agent",
        "promotion_state": "draft",
        "mutation_policy": "candidate_packet_only",
        "ready_now": ready_now,
        "candidate_targets": candidate_targets,
        "candidate_target_count": len(candidate_targets),
        "signal": signal,
        "forbidden_surfaces": [
            "source_writes_without_controller_review",
            "provider_direct_mutation",
        ],
    }


def write_packet(repo_root: Path, packet: dict) -> str | None:
    if packet.get("no_op"):
        return None
    slug = str(packet.get("campaign_slug") or "")
    if not slug:
        return None
    path = repo_root / _PACKET_ROOT / slug / "campaign_packet.json"
    _atomic_write_json(path, packet)
    return path.relative_to(repo_root).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-targets", type=int, default=12)
    parser.add_argument("--campaign-slug", type=str, default=None)
    args = parser.parse_args(argv)
    packet = build_campaign_packet(REPO_ROOT, max_targets=args.max_targets, campaign_slug=args.campaign_slug)
    written: str | None = None
    if args.write and not args.check:
        written = write_packet(REPO_ROOT, packet)
    summary = {
        "kind": "compliance_autocure_campaign_summary",
        "no_op": bool(packet.get("no_op")),
        "campaign_slug": packet.get("campaign_slug"),
        "candidate_target_count": packet.get("candidate_target_count") or 0,
        "ready_now_count": len(packet.get("ready_now") or []),
        "source_digest": packet.get("source_digest"),
        "wrote_packet": written,
    }
    if args.report or args.check:
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
