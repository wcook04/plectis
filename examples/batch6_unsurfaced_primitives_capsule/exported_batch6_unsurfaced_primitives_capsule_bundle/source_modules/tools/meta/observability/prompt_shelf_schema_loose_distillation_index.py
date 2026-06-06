#!/usr/bin/env python3
"""Schema-loose distillation index — learning signals from capture diagnostics where the upprop schema is absent.

Complement of ``prompt_shelf_uppropagation_index.py``. That module indexes runs
whose assistant_message contains a full ``<!-- aiw:uppropagation v=N --> ... <!-- /aiw:uppropagation -->``
block. This module indexes the diagnostics emitted when the assistant skipped
the schema, applying source-role-aware schema-loose extraction so the signal
in the operator-side paste (user_text_tail) and the brief assistant reply
(assistant_text) are not silently conflated.

Sources read:
  state/prompt_shelf/capture_diagnostics/*.json
    Each file is a ``prompt_shelf_capture_diagnostic`` payload written by
    tools/meta/observability/prompt_shelf_chatgpt_observer.py:_write_capture_diagnostic.

For each diagnostic we emit up to three records (one per source_role) where
the source carried any signal:
  - assistant_text   : the brief assistant body
  - user_tail        : the user_text tail (last 6000 chars in the diagnostic)
  - pair_combined    : the two concatenated, only when neither single role
                       was complete_enough but combined extraction yields more

Output (gitignored generated artifact):
  state/prompt_shelf/schema_loose_distillation_index.json
Optional receipt (--write-receipt):
  receipts/prompt_shelf_schema_loose_distillation_latest.json

Authority posture: distillation_projection_not_full_capture. These records
preserve learning signals. They DO NOT grant capture, doctrine, or
propagation authority. Body is never persisted — only hashes and metadata.

CLI:
  --print          emit JSON to stdout (does not write to disk)
  --write          write canonical projection
  --write-receipt  also write a receipt with coverage metrics + omissions
  --check          exit non-zero on drift vs disk
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DIAGNOSTICS_DIR = REPO_ROOT / "state" / "prompt_shelf" / "capture_diagnostics"
INDEX_PATH = REPO_ROOT / "state" / "prompt_shelf" / "schema_loose_distillation_index.json"
RECEIPT_PATH = REPO_ROOT / "receipts" / "prompt_shelf_schema_loose_distillation_latest.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt_shelf_schema_loose_distillation_index"
RECORD_KIND = "prompt_shelf_schema_loose_distillation_record"
AUTHORITY_POSTURE = "distillation_projection_not_full_capture"

# Partial-block markers: the schema is absent, but operators or assistants
# sometimes leave an opener without a closer, or vice versa. These are signal
# even when the FULL block regex would have failed.
PARTIAL_OPENER_RE = re.compile(r"<!--\s*aiw:uppropagation v=(?P<version>\d+)\s*-->", re.IGNORECASE)
PARTIAL_CLOSER_RE = re.compile(r"<!--\s*/aiw:uppropagation\s*-->", re.IGNORECASE)

# Full upprop block — when present in user_tail we should distinguish that
# from no-schema. Mirrors UPPROPAGATION_FULL_BLOCK_RE in the observer.
FULL_BLOCK_RE = re.compile(
    r"<!--\s*aiw:uppropagation v=(?P<version>\d+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/aiw:uppropagation\s*-->",
    re.IGNORECASE | re.DOTALL,
)

# Schema field names known by prompt_shelf_uppropagation_index.py. We borrow
# these names here so partial fields surviving outside an upprop block can
# still be recognized as structured signal.
KNOWN_FIELD_NAMES = (
    "prompt_received",
    "prompt_interpretation",
    "lesson",
    "self_prompting_idea",
    "information_demand",
    "prompt_friction",
    "system_friction",
    "confidence",
    "surprised",
    "deferred",
    "next_move",
    "step_word",
    "step_summary",
    "state_word",
    "hud_state",
    "operator_summary",
    "ui_badge",
)

CONFIDENCE_RE = re.compile(r"^\s*(high|medium|low)\b", re.IGNORECASE)

# Cap-id patterns. WorkItem ids in this repo use snake-case with a 12-hex tail
# (cap_quick_*) or a vN suffix (cap_*_v0). Be conservative to avoid matching
# unrelated text.
CAP_ID_RE = re.compile(r"\bcap_(?:quick_)?[a-z][a-z0-9_]{3,}_(?:[0-9a-f]{12}|v\d+)\b")

# Repo path refs: lower-case path-like sequences ending in a known file
# extension. Restricted to common substrate extensions to avoid noise.
FILE_PATH_RE = re.compile(
    r"(?<![\w./-])"
    r"(?:[a-z][a-zA-Z0-9_.-]*/){1,7}[a-zA-Z0-9_.-]+\."
    r"(?:py|md|json|jsonl|yaml|yml|tsx|ts|tsx?|sh|toml|html|css|sql|txt)\b"
)

# Section headers (markdown ## / ### lines or "Final call" type prose anchors).
SECTION_HEADER_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)
PROSE_SECTION_RE = re.compile(
    r"^\s*(Final call|Final verdict|Stronger verdict|Better .{2,60}|What .+ should (?:not )?happen|"
    r"Anti-goals|Risks|Decision|Plan|Verdict|Constitutional layer|Operational layer)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Negative-constraint lines (operator anti-claims, anti-goals).
NEGATIVE_CONSTRAINT_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:Do not|don'?t|Never|Avoid|Don'?t|do NOT|DO NOT)\b[^\n]{4,300}",
    re.IGNORECASE | re.MULTILINE,
)

# Numbered or "Next:" directives.
NEXT_ACTION_RE = re.compile(
    r"^\s*(?:\d+[.\)]\s+|Next(?: move| step| up| action)?\s*:\s*)([^\n]{4,300})",
    re.IGNORECASE | re.MULTILINE,
)

# Final-call sentence detection — last short paragraph after a "Final call" marker.
FINAL_CALL_MARKER_RE = re.compile(r"\bFinal\s+call\b\s*\n+([^\n]{8,400})", re.IGNORECASE)

# Confidence markers: "confidence: high|medium|low".
CONFIDENCE_LINE_RE = re.compile(
    r"^\s*confidence\s*:\s*(high|medium|low)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha16(text: str) -> str:
    return _sha256(text)[:16]


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _detect_structured_fields(text: str) -> dict[str, bool]:
    """Detect KNOWN_FIELD_NAMES appearing as 'fieldname: value' lines outside any block."""
    hits: dict[str, bool] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        head, _, tail = stripped.partition(":")
        key = head.strip().lower()
        if key in KNOWN_FIELD_NAMES and tail.strip():
            hits[key] = True
    return hits


def _extract_signals(text: str) -> dict:
    """Run all extraction patterns over ``text`` and return a structured signal dict."""
    if not text:
        return {
            "char_count": 0,
            "cap_ids": [],
            "file_path_refs": [],
            "section_headers": [],
            "prose_section_anchors": [],
            "negative_constraints": [],
            "next_action_directives": [],
            "structured_field_hits": {},
            "confidence": None,
            "final_call_sentence": None,
            "partial_opener_count": 0,
            "partial_closer_count": 0,
            "full_block_count": 0,
        }
    cap_ids = sorted(set(CAP_ID_RE.findall(text)))
    file_path_refs = sorted(set(FILE_PATH_RE.findall(text)))
    section_headers = [m.group(1).strip() for m in SECTION_HEADER_RE.finditer(text)]
    prose_anchors = [m.group(1).strip() for m in PROSE_SECTION_RE.finditer(text)]
    negative_constraints = [m.group(0).strip() for m in NEGATIVE_CONSTRAINT_RE.finditer(text)]
    next_actions = [m.group(1).strip() for m in NEXT_ACTION_RE.finditer(text)]
    structured_field_hits = _detect_structured_fields(text)
    confidence_match = CONFIDENCE_LINE_RE.search(text)
    confidence = confidence_match.group(1).lower() if confidence_match else None
    final_call_match = FINAL_CALL_MARKER_RE.search(text)
    final_call_sentence = final_call_match.group(1).strip()[:400] if final_call_match else None
    return {
        "char_count": len(text),
        "cap_ids": cap_ids[:50],
        "file_path_refs": file_path_refs[:80],
        "section_headers": section_headers[:80],
        "prose_section_anchors": prose_anchors[:30],
        "negative_constraints": negative_constraints[:30],
        "next_action_directives": next_actions[:30],
        "structured_field_hits": structured_field_hits,
        "confidence": confidence,
        "final_call_sentence": final_call_sentence,
        "partial_opener_count": len(PARTIAL_OPENER_RE.findall(text)),
        "partial_closer_count": len(PARTIAL_CLOSER_RE.findall(text)),
        "full_block_count": len(FULL_BLOCK_RE.findall(text)),
    }


def _classify_partialness(signals: dict) -> str:
    """Three-bucket classifier used to label record completeness."""
    structured = len(signals["structured_field_hits"])
    significant_signal = (
        len(signals["cap_ids"]) >= 2
        or len(signals["file_path_refs"]) >= 4
        or structured >= 3
        or signals["full_block_count"] >= 1
        or signals["final_call_sentence"] is not None
    )
    any_signal = (
        signals["cap_ids"]
        or signals["file_path_refs"]
        or signals["section_headers"]
        or signals["prose_section_anchors"]
        or signals["negative_constraints"]
        or signals["next_action_directives"]
        or signals["structured_field_hits"]
        or signals["confidence"]
        or signals["partial_opener_count"]
        or signals["partial_closer_count"]
    )
    if significant_signal:
        return "complete_enough"
    if any_signal:
        return "partial"
    return "tiny_schema_absent"


def _has_any_signal(signals: dict) -> bool:
    return _classify_partialness(signals) != "tiny_schema_absent"


def _structural_fingerprint(signals: dict, slot: str) -> str:
    """Stable hash over the structural signal set so identical-shape records dedupe."""
    canon = {
        "slot": slot,
        "cap_ids": signals["cap_ids"],
        "file_path_refs": signals["file_path_refs"],
        "section_headers": signals["section_headers"][:20],
        "structured_field_keys": sorted(signals["structured_field_hits"].keys()),
        "full_block_count": signals["full_block_count"],
    }
    return _sha256(json.dumps(canon, sort_keys=True, separators=(",", ":")))


def distill_diagnostic(diagnostic: dict, *, source_path: Path) -> list[dict]:
    """Return up to three records (one per source_role) for one capture diagnostic.

    pair_combined is emitted only when neither single-role record is complete_enough
    but the combination yields more signal — this preserves the operator's
    "do not silently conflate" rule.
    """
    if not isinstance(diagnostic, dict):
        return []
    if diagnostic.get("kind") != "prompt_shelf_capture_diagnostic":
        return []
    assistant_text = str(diagnostic.get("assistant_text") or "")
    user_shape = diagnostic.get("user_shape") or {}
    user_tail = str(user_shape.get("tail") or "")
    user_text_tail = str(diagnostic.get("user_text_tail") or "")
    # Prefer the long user_text_tail when present (last 6000 chars) over the
    # 480-char user_shape.tail. The diagnostic schema carries both.
    if len(user_text_tail) > len(user_tail):
        user_tail = user_text_tail
    slot = diagnostic.get("slot") or "NA"
    conversation_id = diagnostic.get("conversation_id")
    created_at = diagnostic.get("created_at")
    signature = diagnostic.get("signature")
    skipped_reason = diagnostic.get("skipped_reason")
    try:
        diag_relpath = str(source_path.relative_to(REPO_ROOT))
    except ValueError:
        diag_relpath = str(source_path)

    base = {
        "kind": RECORD_KIND,
        "schema_version": SCHEMA_VERSION,
        "authority_posture": AUTHORITY_POSTURE,
        "source_diagnostic_path": diag_relpath,
        "source_diagnostic_signature": signature,
        "slot": slot,
        "conversation_id": conversation_id,
        "diagnostic_created_at": created_at,
        "skipped_reason": skipped_reason,
        "body_persisted": False,
    }

    sig_assistant = _extract_signals(assistant_text)
    sig_user_tail = _extract_signals(user_tail)
    sig_pair = None

    records: list[dict] = []

    if _has_any_signal(sig_assistant):
        records.append({
            **base,
            "source_role": "assistant_text",
            "source_hash": {
                "assistant_text_hash": _sha256(assistant_text) if assistant_text else None,
                "user_tail_hash": None,
                "pair_hash": None,
            },
            "structural_fingerprint_hash": _structural_fingerprint(sig_assistant, slot),
            "signals": sig_assistant,
            "partialness": _classify_partialness(sig_assistant),
        })

    if _has_any_signal(sig_user_tail):
        records.append({
            **base,
            "source_role": "user_tail",
            "source_hash": {
                "assistant_text_hash": None,
                "user_tail_hash": _sha256(user_tail) if user_tail else None,
                "pair_hash": None,
            },
            "structural_fingerprint_hash": _structural_fingerprint(sig_user_tail, slot),
            "signals": sig_user_tail,
            "partialness": _classify_partialness(sig_user_tail),
        })

    # Emit pair_combined only when neither single role is complete_enough but
    # combining them yields strictly more cap_ids OR file_path_refs OR a full
    # block than either single role had alone. This keeps the role labels
    # honest: pair_combined is reserved for cases where the COMBINED signal
    # carries more than either piece, which is how cross-role pasted Type B
    # packets typically present.
    cls_a = _classify_partialness(sig_assistant)
    cls_u = _classify_partialness(sig_user_tail)
    if "complete_enough" not in (cls_a, cls_u):
        combined_text = (assistant_text + "\n\n" + user_tail) if (assistant_text or user_tail) else ""
        sig_pair = _extract_signals(combined_text)
        combined_richer = (
            len(sig_pair["cap_ids"]) > max(len(sig_assistant["cap_ids"]), len(sig_user_tail["cap_ids"]))
            or len(sig_pair["file_path_refs"]) > max(len(sig_assistant["file_path_refs"]), len(sig_user_tail["file_path_refs"]))
            or sig_pair["full_block_count"] > max(sig_assistant["full_block_count"], sig_user_tail["full_block_count"])
        )
        if combined_richer and _has_any_signal(sig_pair):
            records.append({
                **base,
                "source_role": "pair_combined",
                "source_hash": {
                    "assistant_text_hash": _sha256(assistant_text) if assistant_text else None,
                    "user_tail_hash": _sha256(user_tail) if user_tail else None,
                    "pair_hash": _sha256(combined_text),
                },
                "structural_fingerprint_hash": _structural_fingerprint(sig_pair, slot),
                "signals": sig_pair,
                "partialness": _classify_partialness(sig_pair),
            })

    return records


def _summarize_role_coverage(records: list[dict], role: str) -> dict:
    role_records = [r for r in records if r["source_role"] == role]
    if not role_records:
        return {
            "record_count": 0,
            "complete_enough_count": 0,
            "partial_count": 0,
            "any_signal_rate": 0.0,
            "cap_id_rate": 0.0,
            "file_path_ref_rate": 0.0,
            "negative_constraint_rate": 0.0,
            "section_header_rate": 0.0,
            "structured_field_rate": 0.0,
            "confidence_marker_rate": 0.0,
            "final_call_rate": 0.0,
            "full_block_rate": 0.0,
            "median_char_count": 0,
            "p90_char_count": 0,
        }
    n = len(role_records)
    char_counts = sorted(r["signals"]["char_count"] for r in role_records)
    p90_idx = max(0, int(round(0.9 * (n - 1))))
    return {
        "record_count": n,
        "complete_enough_count": sum(1 for r in role_records if r["partialness"] == "complete_enough"),
        "partial_count": sum(1 for r in role_records if r["partialness"] == "partial"),
        "any_signal_rate": 1.0,  # role_records are by definition rows that had any signal
        "cap_id_rate": round(sum(1 for r in role_records if r["signals"]["cap_ids"]) / n, 4),
        "file_path_ref_rate": round(sum(1 for r in role_records if r["signals"]["file_path_refs"]) / n, 4),
        "negative_constraint_rate": round(sum(1 for r in role_records if r["signals"]["negative_constraints"]) / n, 4),
        "section_header_rate": round(sum(1 for r in role_records if r["signals"]["section_headers"]) / n, 4),
        "structured_field_rate": round(sum(1 for r in role_records if r["signals"]["structured_field_hits"]) / n, 4),
        "confidence_marker_rate": round(sum(1 for r in role_records if r["signals"]["confidence"]) / n, 4),
        "final_call_rate": round(sum(1 for r in role_records if r["signals"]["final_call_sentence"]) / n, 4),
        "full_block_rate": round(sum(1 for r in role_records if r["signals"]["full_block_count"]) / n, 4),
        "median_char_count": int(statistics.median(char_counts)) if char_counts else 0,
        "p90_char_count": int(char_counts[p90_idx]) if char_counts else 0,
    }


def build_index(*, diagnostics_dir: Path = DIAGNOSTICS_DIR) -> dict:
    """Read every diagnostic, distill it, deduplicate by fingerprint, return the projection."""
    diagnostic_paths = sorted(diagnostics_dir.glob("*.json")) if diagnostics_dir.exists() else []
    raw_records: list[dict] = []
    skipped_unparseable = 0
    skipped_wrong_kind = 0

    for p in diagnostic_paths:
        data = _load_json(p)
        if data is None:
            skipped_unparseable += 1
            continue
        if not isinstance(data, dict) or data.get("kind") != "prompt_shelf_capture_diagnostic":
            skipped_wrong_kind += 1
            continue
        raw_records.extend(distill_diagnostic(data, source_path=p))

    # Dedup by (slot, source_role, structural_fingerprint_hash).
    seen_keys: dict[tuple[str, str, str], int] = {}
    deduped: list[dict] = []
    duplicate_count = 0
    for rec in raw_records:
        key = (rec["slot"], rec["source_role"], rec["structural_fingerprint_hash"])
        if key in seen_keys:
            duplicate_count += 1
            continue
        seen_keys[key] = len(deduped)
        deduped.append(rec)

    coverage = {
        "assistant_text": _summarize_role_coverage(deduped, "assistant_text"),
        "user_tail": _summarize_role_coverage(deduped, "user_tail"),
        "pair_combined": _summarize_role_coverage(deduped, "pair_combined"),
    }

    slot_counts: dict[str, int] = {}
    for rec in deduped:
        slot_counts[rec["slot"]] = slot_counts.get(rec["slot"], 0) + 1

    return {
        "kind": ARTIFACT_KIND,
        "schema_version": SCHEMA_VERSION,
        "authority_posture": AUTHORITY_POSTURE,
        "generated_at": _utc_now_iso(),
        "source_root": str(diagnostics_dir.relative_to(REPO_ROOT)) if diagnostics_dir.is_relative_to(REPO_ROOT) else str(diagnostics_dir),
        "diagnostic_count": len(diagnostic_paths),
        "raw_record_count": len(raw_records),
        "deduped_record_count": len(deduped),
        "duplicate_count": duplicate_count,
        "skipped_unparseable_count": skipped_unparseable,
        "skipped_wrong_kind_count": skipped_wrong_kind,
        "slot_counts": dict(sorted(slot_counts.items())),
        "coverage": coverage,
        "records": deduped,
        "omissions": [
            "Full assistant_text and user_text bodies are not persisted in this index.",
            "Records preserve learning signals (paths, ids, headers, anti-claims, directives, fingerprints), not raw bodies.",
            "This is a distillation projection, not a full capture. capture_authority remains false; cw_mod.write_capture is the only owner of full-capture semantics.",
            "Doctrine, Task Ledger, and prompt-standard mutations may not be derived directly from these records.",
            "source_role labels are non-negotiable: assistant_text and user_tail are NOT conflated; pair_combined is emitted only when single roles are partial AND the combination strictly increases signal.",
        ],
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _build_receipt(index: dict, *, index_relpath: str) -> dict:
    coverage = index["coverage"]
    return {
        "kind": "receipt",
        "schema_version": "receipt_v0",
        "id": "receipt.prompt_shelf_schema_loose_distillation",
        "generated_at": index["generated_at"],
        "owner": "tools.meta.observability.prompt_shelf_schema_loose_distillation_index",
        "claim_ref": "cap_quick_prompt_shelf_bridge_schema_loose_type_b_4b01dbd8d09f",
        "claim_tier": "distillation_projection_validated",
        "command": "PYTHONPATH=. python3 -m tools.meta.observability.prompt_shelf_schema_loose_distillation_index --write --write-receipt",
        "result": "schema-loose distillation index built; source-role-separated coverage emitted",
        "status": "ok",
        "summary": {
            "diagnostic_count": index["diagnostic_count"],
            "raw_record_count": index["raw_record_count"],
            "deduped_record_count": index["deduped_record_count"],
            "duplicate_count": index["duplicate_count"],
            "slot_counts": index["slot_counts"],
            "coverage_assistant_text": coverage["assistant_text"],
            "coverage_user_tail": coverage["user_tail"],
            "coverage_pair_combined": coverage["pair_combined"],
        },
        "evidence_refs": [
            index_relpath,
            "state/prompt_shelf/capture_diagnostics/",
            "tools/meta/observability/prompt_shelf_chatgpt_observer.py",
            "tools/meta/observability/prompt_shelf_uppropagation_index.py",
        ],
        "authority_boundary": {
            "capture_authority": False,
            "distillation_authority": True,
            "doctrine_authority": False,
            "propagation_authority": False,
            "explanation": "Records are a projection layer that preserves learning signals; cw_mod.write_capture remains the sole owner of full-capture semantics.",
        },
        "omissions": index["omissions"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the schema-loose distillation index over prompt-shelf capture diagnostics.")
    parser.add_argument("--print", dest="do_print", action="store_true", help="Emit the index JSON to stdout (no disk write).")
    parser.add_argument("--write", dest="do_write", action="store_true", help="Write the canonical index to disk.")
    parser.add_argument("--write-receipt", dest="do_write_receipt", action="store_true", help="Also write a receipt next to the index.")
    parser.add_argument("--check", dest="do_check", action="store_true", help="Exit non-zero if disk index differs from a fresh build.")
    parser.add_argument("--diagnostics-dir", default=None, help="Override source diagnostics directory.")
    parser.add_argument("--summary-only", dest="summary_only", action="store_true", help="Print only the summary section, not full records.")
    args = parser.parse_args(argv)

    if not (args.do_print or args.do_write or args.do_check):
        parser.error("must pass --print, --write, or --check")

    diagnostics_dir = Path(args.diagnostics_dir).resolve() if args.diagnostics_dir else DIAGNOSTICS_DIR
    index = build_index(diagnostics_dir=diagnostics_dir)

    if args.do_check:
        existing = _load_json(INDEX_PATH)
        if existing is None:
            print(json.dumps({"status": "missing_on_disk", "expected_path": str(INDEX_PATH.relative_to(REPO_ROOT))}), file=sys.stderr)
            return 1
        # Compare structural slice (ignore generated_at).
        existing_cmp = dict(existing)
        existing_cmp.pop("generated_at", None)
        index_cmp = dict(index)
        index_cmp.pop("generated_at", None)
        if json.dumps(existing_cmp, sort_keys=True) != json.dumps(index_cmp, sort_keys=True):
            print(json.dumps({"status": "drift", "path": str(INDEX_PATH.relative_to(REPO_ROOT))}), file=sys.stderr)
            return 1
        print(json.dumps({"status": "clean"}))
        return 0

    if args.do_write:
        _write_json(INDEX_PATH, index)
        index_relpath = str(INDEX_PATH.relative_to(REPO_ROOT))
        if args.do_write_receipt:
            receipt = _build_receipt(index, index_relpath=index_relpath)
            _write_json(RECEIPT_PATH, receipt)
            print(json.dumps({
                "status": "ok",
                "index_path": index_relpath,
                "receipt_path": str(RECEIPT_PATH.relative_to(REPO_ROOT)),
                "summary": receipt["summary"],
            }, indent=2, sort_keys=True))
        else:
            print(json.dumps({
                "status": "ok",
                "index_path": index_relpath,
                "summary": {
                    "diagnostic_count": index["diagnostic_count"],
                    "deduped_record_count": index["deduped_record_count"],
                    "coverage": index["coverage"],
                },
            }, indent=2, sort_keys=True))
        return 0

    if args.do_print:
        if args.summary_only:
            print(json.dumps({k: v for k, v in index.items() if k != "records"}, indent=2, sort_keys=True))
        else:
            print(json.dumps(index, indent=2, sort_keys=True))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
