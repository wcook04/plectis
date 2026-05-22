from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


PASS = "pass"
BLOCKED = "blocked"
PARTIAL = "partial"

FLAGSHIP_TRANCHE_REL = Path(
    "examples/macro_projection_import_protocol/exported_projection_import_bundle/"
    "flagship_tranche.json"
)
CLAIM_CARD_REGISTRY_REL = Path("core/public_claim_cards.json")
DEPENDENCY_PREFLIGHT_REL = Path("receipts/preflight/dependency_preflight.json")

REQUIRED_CARD_FLOOR = {
    "selected_pattern_ids": "CAPABILITY_TRANSFER_PATTERN_MISSING",
    "runtime_surface_refs": "CAPABILITY_TRANSFER_RUNTIME_SURFACE_MISSING",
    "release_artifact_refs": "CAPABILITY_TRANSFER_ARTIFACT_MISSING",
    "validation_refs": "CAPABILITY_TRANSFER_VALIDATION_MISSING",
    "claim_ceiling": "CAPABILITY_TRANSFER_CLAIM_CEILING_MISSING",
}
LOW_EVIDENCE_CLASSES = {"schema_contract", "synthetic_fixture_replay"}
GLOBAL_IMPORT_CLAIM_IDS = {"macro_pattern_import_membrane"}


def public_root_for(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" and (candidate / "pyproject.toml").exists():
            return candidate
    return resolved


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _split_ref(ref: str) -> str:
    return ref.split("::", 1)[0]


def _looks_like_path(ref: str) -> bool:
    if not ref or ref.startswith(("http://", "https://", "microcosm ")):
        return False
    return "/" in ref or ref.endswith((".json", ".jsonl", ".md", ".py", ".toml"))


def _path_exists(root: Path, ref: str) -> bool:
    return (root / _split_ref(ref)).exists()


def _token_set(*values: object) -> set[str]:
    text = " ".join(str(value) for value in values if value)
    return {
        token
        for token in re.split(r"[^a-zA-Z0-9]+", text.lower())
        if len(token) >= 4 and token not in {"microcosm", "public", "runtime", "claim"}
    }


def load_flagship_tranche(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    payload = read_json_strict(public_root / FLAGSHIP_TRANCHE_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{FLAGSHIP_TRANCHE_REL.as_posix()} must be a JSON object")
    return payload


def load_claim_registry(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    payload = read_json_strict(public_root / CLAIM_CARD_REGISTRY_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{CLAIM_CARD_REGISTRY_REL.as_posix()} must be a JSON object")
    return payload


def load_dependency_preflight(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    payload = read_json_strict(public_root / DEPENDENCY_PREFLIGHT_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{DEPENDENCY_PREFLIGHT_REL.as_posix()} must be a JSON object")
    return payload


def _claim_card_refs(card: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("surface_refs", "evidence_receipt_refs", "negative_case_refs"):
        refs.extend(_strings(card.get(key)))
    demo_ref = card.get("demo_ref")
    if isinstance(demo_ref, str) and demo_ref:
        refs.append(demo_ref)
    return refs


def _claim_cards_by_relevance(
    lane: dict[str, Any],
    claim_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lane_refs = {
        _split_ref(ref)
        for ref in [
            *_strings(lane.get("runtime_surface_refs")),
            *_strings(lane.get("release_artifact_refs")),
            *_strings(lane.get("validation_refs")),
        ]
    }
    lane_tokens = _token_set(
        lane.get("lane_id"),
        lane.get("lane_label"),
        " ".join(_strings(lane.get("selected_pattern_ids"))),
        " ".join(_strings(lane.get("runtime_surface_refs"))),
        " ".join(_strings(lane.get("release_artifact_refs"))),
    )
    linked: list[dict[str, Any]] = []
    for card in claim_cards:
        card_id = str(card.get("claim_id") or "")
        if card_id in GLOBAL_IMPORT_CLAIM_IDS:
            linked.append(card)
            continue
        refs = {_split_ref(ref) for ref in _claim_card_refs(card)}
        if lane_refs & refs:
            linked.append(card)
            continue
        card_tokens = _token_set(
            card_id,
            card.get("public_render_label"),
            card.get("plain_english_claim"),
            " ".join(_claim_card_refs(card)),
            " ".join(_strings(card.get("organ_evidence_class_refs"))),
        )
        if lane_tokens & card_tokens:
            linked.append(card)
    return sorted(linked, key=lambda row: str(row.get("claim_id") or ""))


def _transfer_route(lane: dict[str, Any]) -> str:
    if _strings(lane.get("public_safe_body_material_ids")):
        return "runtime_demo_import_with_public_safe_body_material"
    return "runtime_demo_import"


def _capability_card(
    public_root: Path,
    lane: dict[str, Any],
    claim_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    for field, code in REQUIRED_CARD_FLOOR.items():
        value = lane.get(field)
        if value in (None, "", [], {}):
            blockers.append(
                {
                    "error_code": code,
                    "subject_id": str(lane.get("lane_id") or "unknown_lane"),
                    "subject_kind": "capability_transfer_lane",
                    "message": f"Lane is missing required transfer field {field}.",
                    "body_redacted": True,
                }
            )
    missing_refs = [
        ref
        for ref in _strings(lane.get("release_artifact_refs"))
        if _looks_like_path(ref) and not _path_exists(public_root, ref)
    ]
    for ref in missing_refs:
        blockers.append(
            {
                "error_code": "CAPABILITY_TRANSFER_RELEASE_REF_MISSING",
                "subject_id": f"{lane.get('lane_id')}:{ref}",
                "subject_kind": "release_artifact_ref",
                "message": "Release artifact ref must exist in the standalone Microcosm tree.",
                "body_redacted": True,
            }
        )

    linked_claims = _claim_cards_by_relevance(lane, claim_cards)
    linked_claim_ids = [str(card.get("claim_id")) for card in linked_claims]
    claim_evidence_classes = sorted(
        {
            str(card.get("evidence_class"))
            for card in linked_claims
            if isinstance(card.get("evidence_class"), str)
        }
    )
    has_strong_claim = any(
        str(card.get("evidence_class") or "") not in LOW_EVIDENCE_CLASSES
        for card in linked_claims
    )
    claim_card_status = PASS if has_strong_claim else "needs_claim_projection"
    transfer_status = PASS if not blockers else BLOCKED
    product_surface_status = (
        PASS
        if transfer_status == PASS and _strings(lane.get("runtime_surface_refs"))
        else BLOCKED
    )
    return {
        "schema_version": "microcosm_capability_transfer_card_v1",
        "capability_id": f"capability_transfer::{lane.get('lane_id')}",
        "lane_id": str(lane.get("lane_id") or ""),
        "lane_label": str(lane.get("lane_label") or ""),
        "visible_value": str(lane.get("why_external_reader_cares") or ""),
        "transfer_route": _transfer_route(lane),
        "transfer_status": transfer_status,
        "product_surface_status": product_surface_status,
        "claim_card_status": claim_card_status,
        "selected_pattern_ids": _strings(lane.get("selected_pattern_ids")),
        "selected_pattern_count": len(_strings(lane.get("selected_pattern_ids"))),
        "runtime_surface_refs": _strings(lane.get("runtime_surface_refs")),
        "release_artifact_refs": _strings(lane.get("release_artifact_refs")),
        "validation_refs": _strings(lane.get("validation_refs")),
        "public_safe_body_material_ids": _strings(
            lane.get("public_safe_body_material_ids")
        ),
        "macro_origin_refs": _strings(lane.get("source_refs")),
        "linked_claim_card_ids": linked_claim_ids,
        "claim_evidence_classes": claim_evidence_classes,
        "claim_ceiling": str(lane.get("claim_ceiling") or ""),
        "demotion_rule": (
            "Demote to metadata-only flagship listing if runtime surface refs, release "
            "artifact refs, validation refs, or a non-low-evidence claim card disappear."
        ),
        "body_redacted": bool(lane.get("body_redacted", True)),
        "blockers": blockers,
    }


def _claim_coverage(cards: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [
        card["lane_id"]
        for card in cards
        if card["claim_card_status"] != PASS
    ]
    counts = Counter(
        evidence_class
        for card in cards
        for evidence_class in card.get("claim_evidence_classes", [])
    )
    return {
        "status": PASS if not missing else PARTIAL,
        "covered_lane_count": len(cards) - len(missing),
        "uncovered_lane_count": len(missing),
        "uncovered_lane_ids": missing,
        "claim_evidence_class_counts": dict(sorted(counts.items())),
    }


def _preflight_gate(root: Path) -> dict[str, Any]:
    try:
        receipt = load_dependency_preflight(root)
    except FileNotFoundError:
        return {
            "status": BLOCKED,
            "receipt_ref": DEPENDENCY_PREFLIGHT_REL.as_posix(),
            "blocking_codes": ["DEPENDENCY_PREFLIGHT_RECEIPT_MISSING"],
            "organ_lifecycle_coverage_status": "missing",
            "coverage_counts": {},
        }
    lifecycle = receipt.get("organ_lifecycle_coverage")
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    return {
        "status": PASS
        if receipt.get("status") == PASS and lifecycle.get("status") == PASS
        else BLOCKED,
        "receipt_ref": DEPENDENCY_PREFLIGHT_REL.as_posix(),
        "blocking_codes": _strings(receipt.get("blocked_dependency_codes")),
        "organ_lifecycle_coverage_status": str(lifecycle.get("status") or "missing"),
        "coverage_counts": lifecycle.get("coverage_counts", {}),
    }


def build_receipt(
    root: str | Path,
    *,
    require_claim_card_coverage: bool = False,
) -> dict[str, Any]:
    public_root = public_root_for(root)
    tranche = load_flagship_tranche(public_root)
    registry = load_claim_registry(public_root)
    claim_cards = _rows(registry, "claim_cards")
    cards = [
        _capability_card(public_root, lane, claim_cards)
        for lane in _rows(tranche, "lanes")
    ]
    transfer_blockers = [
        blocker
        for card in cards
        for blocker in card.get("blockers", [])
    ]
    claim_coverage = _claim_coverage(cards)
    preflight = _preflight_gate(public_root)
    selected_patterns = sorted(
        {
            pattern_id
            for card in cards
            for pattern_id in card.get("selected_pattern_ids", [])
        }
    )
    transfer_status = PASS if not transfer_blockers and cards else BLOCKED
    status = PASS
    if transfer_status != PASS or preflight["status"] != PASS:
        status = BLOCKED
    if require_claim_card_coverage and claim_coverage["status"] != PASS:
        status = BLOCKED
    return {
        "schema_version": "microcosm_release_impressiveness_compiler_receipt_v1",
        "compiler_id": "release_impressiveness_compiler",
        "created_at": utc_now(),
        "status": status,
        "transfer_status": transfer_status,
        "claim_card_coverage_status": claim_coverage["status"],
        "dependency_preflight_gate_status": preflight["status"],
        "flagship_tranche_ref": FLAGSHIP_TRANCHE_REL.as_posix(),
        "claim_card_registry_ref": CLAIM_CARD_REGISTRY_REL.as_posix(),
        "selection_rule": str(tranche.get("selection_rule") or ""),
        "release_tree_surface": str(tranche.get("release_tree_surface") or ""),
        "capability_transfer_card_count": len(cards),
        "selected_pattern_count": len(selected_patterns),
        "selected_pattern_ids": selected_patterns,
        "capability_transfer_cards": cards,
        "claim_card_coverage": claim_coverage,
        "dependency_preflight_gate": preflight,
        "blocking_codes": sorted(
            {
                str(blocker.get("error_code"))
                for blocker in transfer_blockers
            }
            | (
                set(preflight["blocking_codes"])
                if preflight["status"] != PASS
                else set()
            )
            | (
                {"CAPABILITY_TRANSFER_CLAIM_CARD_COVERAGE_PARTIAL"}
                if require_claim_card_coverage and claim_coverage["status"] != PASS
                else set()
            )
        ),
        "receipt_paths": [],
        "authority_ceiling": {
            "release_authorized": False,
            "publication_authorized": False,
            "private_data_equivalence_claim": False,
            "provider_calls_authorized": False,
            "benchmark_performance_claim_authorized": False,
        },
        "anti_claim": (
            "Release impressiveness cards rank and validate visible transferred capability. "
            "They do not authorize publication, claim private-root equivalence, prove all "
            "macro claims, or turn provenance refs into runtime dependencies."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m microcosm_core.release_impressiveness_compiler"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--require-claim-card-coverage", action="store_true")
    args = parser.parse_args(argv)
    receipt = build_receipt(
        args.root,
        require_claim_card_coverage=args.require_claim_card_coverage,
    )
    if args.out:
        out_path = public_root_for(args.root) / args.out
        receipt["receipt_paths"] = [str(Path(args.out))]
        write_json_atomic(out_path, receipt)
    else:
        print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
