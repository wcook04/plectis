#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Materialize a candidate-only standard_skill_pairing campaign
  packet from the hologram-projected pairing map. Wave_004A; never authors
  skills, never edits the registry, never mutates source. Writes one packet
  under state/meta_missions/standard_skill_pairing/<slug>/campaign_packet.json
  that a controller can review and approve before any actual skill authoring
  happens.
- Mechanism: Build the standard_skill_gap signal, take the top-K missing
  standards, project each into a candidate_target with suggested_next_action
  and candidate_target_paths, write atomically.
- Non-goal: Author skills, mutate skill_registry, fire providers.

[INTERFACE]
- CLI: --check (no write; print summary), --report (print summary),
  --write (persist packet), --max-targets N, --campaign-slug SLUG.

[FLOW]
- Read signal; if not gap_high, exit 0 with no_op summary.
- Otherwise pick top-N missing standards, build packet, optionally write.

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

from system.lib.compliance_reaction_signals import build_standard_skill_gap_signal  # noqa: E402


_PACKET_ROOT = "state/meta_missions/standard_skill_pairing"


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
    signal = build_standard_skill_gap_signal(repo_root)
    sample = signal.get("sample_missing") or []
    if not signal.get("gap_high"):
        return {
            "kind": "standard_skill_pairing_campaign",
            "schema_version": "standard_skill_pairing_campaign_v1",
            "no_op": True,
            "reason": "gap_high=false; no campaign packet emitted.",
            "signal": signal,
        }
    targets_source = sample[:max_targets]
    candidate_targets = [
        {
            "standard_id": sid,
            "pairing_status": "missing_authoring_skill",
            "suggested_next_action": (
                "Classify whether this standard needs a fresh authoring skill, "
                "qualifies as tool_only_no_skill_required, or routes to an "
                "existing skill via governing_standard_ids."
            ),
            "candidate_target_paths": [
                "codex/doctrine/skills/skill_registry.json",
                f"codex/standards/{sid}.json",
            ],
        }
        for sid in targets_source
    ]
    digest = signal.get("digest") or ""
    slug = campaign_slug or f"std_skill_pairing_{digest}"
    return {
        "kind": "standard_skill_pairing_campaign",
        "schema_version": "standard_skill_pairing_campaign_v1",
        "campaign_slug": slug,
        "source_digest": digest,
        "generated_at": _utc_now(),
        "standard_ref": "codex/standards/std_skill.json",
        "source_path": signal.get("source_path"),
        "authority_tier": "authoring_agent",
        "promotion_state": "draft",
        "mutation_policy": "candidate_packet_only",
        "candidate_targets": candidate_targets,
        "candidate_target_count": len(candidate_targets),
        "missing_authoring_skill_total": signal.get("missing_authoring_skill"),
        "signal": signal,
        "forbidden_surfaces": [
            "source_writes_without_controller_review",
            "skill_registry_direct_edit_without_controller_review",
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
        "kind": "standard_skill_pairing_campaign_summary",
        "no_op": bool(packet.get("no_op")),
        "campaign_slug": packet.get("campaign_slug"),
        "candidate_target_count": packet.get("candidate_target_count") or 0,
        "missing_authoring_skill_total": packet.get("missing_authoring_skill_total"),
        "source_digest": packet.get("source_digest"),
        "wrote_packet": written,
    }
    if args.report or args.check:
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
