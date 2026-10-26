from __future__ import annotations

import json
from pathlib import Path

from system.lib.raw_seed_paragraph_ledger import (
    compute_paragraph_state,
    load_ledger,
    record_dispatch,
    record_rejection,
    save_ledger,
)
from system.lib.raw_seed_subagent_lane import (
    build_subagent_dispatch_packet,
    import_subagent_bundles,
)


def _write_json(root: Path, rel_path: str, payload: object) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _read_json(root: Path, rel_path: str) -> dict:
    return json.loads((root / rel_path).read_text(encoding="utf-8"))


def _family_fixture(root: Path) -> str:
    family_rel = "obsidian/okay lets do this/09 - Subagent Lane Family"
    _write_json(
        root,
        f"{family_rel}/raw_seed.json",
        {
            "kind": "raw_seed_registry",
            "family_id": "09",
            "family_number": "09",
            "family_title": "Subagent Lane Family",
            "family_dir": family_rel,
            "paragraphs": [
                {
                    "id": "par_retry_001",
                    "plain_text": "We're gesturing towards preserving the raw voice before it gets too cleaned up.",
                    "line_start": 10,
                    "line_end": 10,
                    "paragraph_fingerprint": "fp_retry_001",
                },
                {
                    "id": "par_fresh_002",
                    "plain_text": "The point isn't perfect polish, the point is preserving the actual intent.",
                    "line_start": 12,
                    "line_end": 12,
                    "paragraph_fingerprint": "fp_fresh_002",
                },
            ],
        },
    )
    _write_json(
        root,
        f"{family_rel}/raw_seed/raw_seed_shards.json",
        {
            "kind": "raw_seed_shards",
            "schema_version": "raw_seed_shards_v1",
            "shards": [
                {
                    "shard_id": "bin_par_retry_001",
                    "parent_paragraph_id": "par_retry_001",
                    "status": "open",
                },
                {
                    "shard_id": "bin_par_fresh_002",
                    "parent_paragraph_id": "par_fresh_002",
                    "status": "open",
                },
            ],
        },
    )
    return family_rel


def test_backlog_slice_prefers_untouched_then_retries_fully_rejected(tmp_path: Path) -> None:
    root = tmp_path
    family_rel = _family_fixture(root)

    ledger = {}
    prior_attempt = record_dispatch(
        ledger,
        paragraph_id="par_retry_001",
        lane="subagent",
        cohort_id="cohort_prior",
    )
    record_rejection(
        ledger,
        paragraph_id="par_retry_001",
        attempt_id=prior_attempt.attempt_id,
        reason="no_bundle_returned",
    )
    save_ledger(root, family_rel, ledger)

    persisted = load_ledger(root, family_rel)
    assert compute_paragraph_state(persisted["par_retry_001"]) == "fully_rejected"

    first_packet = build_subagent_dispatch_packet(
        family="09",
        repo_root=root,
        cohort_size=1,
        run_id="run_first",
    )
    assert first_packet["selected_paragraph_ids"] == ["par_fresh_002"]

    second_packet = build_subagent_dispatch_packet(
        family="09",
        repo_root=root,
        cohort_size=1,
        run_id="run_second",
    )
    assert second_packet["selected_paragraph_ids"] == ["par_retry_001"]


def test_import_subagent_bundles_drops_validator_rejected_shards_in_advisory_mode(
    tmp_path: Path,
) -> None:
    root = tmp_path
    family_rel = _family_fixture(root)

    packet = build_subagent_dispatch_packet(
        family="09",
        repo_root=root,
        cohort_size=1,
        run_id="run_import",
    )
    assert len(packet["selected_paragraph_ids"]) == 1
    selected_paragraph_id = packet["selected_paragraph_ids"][0]
    if selected_paragraph_id == "par_fresh_002":
        good_shard = {
            "id": "atom_good_001",
            "parent_paragraph_id": "par_fresh_002",
            "segment_ordinal": "A",
            "clarified_statement": "The point isn't perfect polish, the point is preserving the actual intent.",
            "voice_anchor": "The point isn't perfect polish",
            "support_excerpt": "The point isn't perfect polish, the point is preserving the actual intent.",
            "compression_ratio": 0.88,
            "distillation_confidence": 0.75,
            "gestures_towards": [],
            "compression_notes": ["whitespace_normalized"],
        }
        bad_shard = {
            "id": "atom_bad_002",
            "parent_paragraph_id": "par_fresh_002",
            "segment_ordinal": "B",
            "clarified_statement": "We should build a system that preserves the actual intent.",
            "voice_anchor": "preserving the actual intent",
            "support_excerpt": "the point is preserving the actual intent",
            "compression_ratio": 0.76,
            "distillation_confidence": 0.72,
            "gestures_towards": [],
            "compression_notes": ["whitespace_normalized"],
        }
    else:
        assert selected_paragraph_id == "par_retry_001"
        good_shard = {
            "id": "atom_good_001",
            "parent_paragraph_id": "par_retry_001",
            "segment_ordinal": "A",
            "clarified_statement": "We're gesturing towards preserving the raw voice before it gets too cleaned up.",
            "voice_anchor": "gesturing towards preserving the raw voice",
            "support_excerpt": "We're gesturing towards preserving the raw voice before it gets too cleaned up.",
            "compression_ratio": 0.90,
            "distillation_confidence": 0.74,
            "gestures_towards": [],
            "compression_notes": ["whitespace_normalized"],
        }
        bad_shard = {
            "id": "atom_bad_002",
            "parent_paragraph_id": "par_retry_001",
            "segment_ordinal": "B",
            "clarified_statement": "We should build a system that preserves the raw voice.",
            "voice_anchor": "preserving the raw voice",
            "support_excerpt": "preserving the raw voice before it gets too cleaned up",
            "compression_ratio": 0.72,
            "distillation_confidence": 0.70,
            "gestures_towards": [],
            "compression_notes": ["whitespace_normalized"],
        }

    bundles_rel = "state/raw_seed_subagent/run_import/bundles.json"
    _write_json(
        root,
        bundles_rel,
        {
            "paragraphs": {
                selected_paragraph_id: {
                    "shards": [
                        good_shard,
                        bad_shard,
                    ],
                    "_summary": {
                        "teleology": "distill one paragraph into two candidate shards",
                        "outcome": "1 clean shard, 1 architecture-leak shard",
                        "confidence": "MEDIUM",
                    },
                }
            }
        },
    )

    result = import_subagent_bundles(
        packet_path=packet["packet_path"],
        bundles_path=bundles_rel,
        repo_root=root,
        strict=False,
    )

    extracted = _read_json(root, f"{family_rel}/extracted_shards.json")
    assert len(extracted["shards"]) == 1
    assert extracted["shards"][0]["clarified_statement"] == good_shard["clarified_statement"]

    ledger = load_ledger(root, family_rel)
    entry = ledger[selected_paragraph_id]
    shard_states = sorted(shard.state for shard in entry.shard_entries.values())
    assert shard_states == ["imported", "rejected"]

    paragraph_result = result["per_paragraph_results"][0]
    assert paragraph_result["outcome"] == "imported"
    assert paragraph_result["accepted"] == 1
    assert paragraph_result["rejected"] == 1
