"""
[PURPOSE]
- Teleology: Run the deterministic Lab contract audit over persisted node artifacts so the runtime can gate on machine-checkable RED conditions before any semantic interpretation layer weighs in.
- Mechanism: Read Lab artifact envelopes from disk, normalize the relevant payload fragments, and apply hard-coded structural checks for question-mark bans, tuple formatting, thesis inheritance, target grounding, reconciliation completeness, and CP2 policy invariants.
- Non-goal: Semantic market interpretation or judgment of thesis quality; those remain outside this deterministic audit lane.

[INTERFACE]
- Exports: compute_lab_contract_audit.
- Reads: `artifacts_dir/<node_id>.json` payloads for the Lab node ids referenced by this audit.
- Writes: None.
- Schema: `compute_lab_contract_audit()` returns a dict with `status`, `hard_fails`, `soft_violations`, and `details`.

[FLOW]
- Load node artifacts from disk -> scan compute-node outputs for banned question marks -> validate tuple and annotation rules -> compare thesis inheritance and target grounding -> check contradiction and CP2 policy invariants -> emit a green/red audit report with details.
- When-needed: Open when the Lab runtime needs deterministic failure evidence from persisted node artifacts instead of the full engine loop or LLM-side integrity reasoning.
- When-needed: Open when audit evaluation nodes previously referencing `audit_shadow_extractor` need a deterministic Python replacement that gates on hard-fail categories without the deprecated shadow pipeline.
- Escalates-to: system/core/engine.py; system/server/tests/test_lab_contract_audit.py
- Couples: `system/core/engine.py` consumes this report as a runtime gate, and `system/server/tests/test_lab_contract_audit.py` encodes the audited contract examples.
- Navigation-group: kernel_lib

[DEPENDENCIES]
- json: Deserialize persisted Lab artifact envelopes.
- difflib.SequenceMatcher: Detect near-duplicate two-sentence annotations in phase-2 miner tuples.
- pathlib.Path: Resolve artifact payload paths under the supplied artifacts directory.
- re: Split and normalize sentence- and token-shaped fields for deterministic checks.

[CONSTRAINTS]
- Guarantee: Missing or unreadable node artifacts degrade to absent evidence instead of crashing the audit, and the exported function always returns one structured audit dict.
- Orders: Hard-fail categories accumulate in a fixed audit order so repeated runs over identical artifacts emit stable results.
- Fails: None from the exported audit surface for malformed or missing artifacts; helper readers suppress decode/read failures and treat them as missing inputs.
- Non-goal: This module does not mutate artifacts, repair bad payloads, or invoke any external model.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from system.lib.market_fusion_readiness import preflight_consumer_claims

PHASE1_MINERS: Tuple[str, ...] = (
    "lab_miner_stock",
    "lab_miner_etf",
    "lab_miner_macro",
    "lab_miner_news",
    "lab_miner_poly",
    "lab_miner_calc",
    "lab_miner_stockgrid",
)

PHASE2_MINERS: Tuple[str, ...] = (
    "lab_miner_v2_stock",
    "lab_miner_v2_etf",
    "lab_miner_v2_macro",
    "lab_miner_v2_news",
    "lab_miner_v2_poly",
    "lab_miner_v2_calc",
    "lab_miner_v2_stockgrid",
)

QUESTION_MARK_SCAN_NODES: Tuple[str, ...] = (
    "lab_seed_state",
    *PHASE1_MINERS,
    "lab_cross_corr_v1",
    "lab_orient",
    *PHASE2_MINERS,
    "lab_cross_corr_v2",
)

CROSS_FEED_CLAIM_ARTIFACT_IDS: Tuple[str, ...] = (
    "lab_cross_feed_claims",
    "market_fusion_candidate_situations",
)

CROSS_FEED_CLAIM_FIELDS: Tuple[str, ...] = (
    "candidate_situation_claims",
    "cross_feed_claims",
    "market_fusion_claims",
)


def _load_artifact_data(artifacts_dir: Path, node_id: str) -> Any:
    path = artifacts_dir / f"{node_id}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload.get("data")
    return payload


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
        return
    if isinstance(value, list):
        for v in value:
            yield from _iter_strings(v)


def _extract_tuple_lines(data: Any) -> List[str]:
    if isinstance(data, str):
        return [line.strip() for line in data.splitlines() if line.strip()]
    if isinstance(data, list):
        return [str(line).strip() for line in data if str(line).strip()]
    return []


def _split_tuple_fields(line: str) -> Optional[List[str]]:
    token = line.strip()
    if not token.startswith("{") or not token.endswith("}"):
        return None
    body = token[1:-1].strip()
    parts = [p.strip() for p in body.split(",")]
    if len(parts) not in (3, 4):
        return None
    if not parts[0]:
        return None
    return parts


def _split_sentences(text: str) -> List[str]:
    raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if len(raw) >= 2:
        return raw
    # Fallback for terse styles using semicolon separators.
    semi = [s.strip() for s in text.split(";") if s.strip()]
    return semi if len(semi) >= 2 else raw


def _normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", text.lower())).strip()


def _collect_valid_targets(cross_corr_v2_data: Any) -> Set[str]:
    targets: Set[str] = set()
    if not isinstance(cross_corr_v2_data, dict):
        return targets

    explicit = cross_corr_v2_data.get("valid_prediction_targets")
    if isinstance(explicit, list):
        for token in explicit:
            t = str(token).upper().strip()
            if t and t != "NONE":
                targets.add(t)
    if targets:
        return targets

    for field in ("target_swarms", "solo_targets"):
        entries = cross_corr_v2_data.get(field)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            tickers = entry.get("tickers")
            if not isinstance(tickers, list):
                continue
            for token in tickers:
                t = str(token).upper().strip()
                if t and t != "NONE":
                    targets.add(t)
    return targets


def _resolve_cp2_data(data: Any) -> Any:
    """
    Accept both direct CP2 payload and split-wrapper payloads.
    For split wrappers, prefer cp2_resolved.
    """
    if isinstance(data, dict):
        resolved = data.get("cp2_resolved")
        if isinstance(resolved, dict):
            return resolved
    return data


def compute_lab_contract_audit(artifacts_dir: Path) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Evaluate the deterministic Lab contract over one artifacts directory and emit the machine-checkable pass/fail report consumed by runtime gates.
    - Mechanism: Load the relevant node payloads, run the question-mark, tuple, inheritance, grounding, reconciliation, and CP2 invariants in sequence, and collapse the findings into a green/red audit envelope.
    - Reads: `artifacts_dir` plus the node-specific JSON files named by `QUESTION_MARK_SCAN_NODES`, `PHASE1_MINERS`, `PHASE2_MINERS`, and the explicit downstream node ids referenced in this function.
    - Writes: None.
    - Guarantee: Returns a dict containing `status`, `hard_fails`, `soft_violations`, and `details`; `status` is `red` whenever any hard-fail category is recorded, otherwise `green`.
    - Fails: None for missing or unreadable artifact files; those inputs are treated as absent evidence by the helper readers.
    - Orders: Audit categories are evaluated in a fixed sequence so identical artifact sets yield stable hard-fail ordering and detail buckets.
    - When-needed: Open when debugging why Lab artifacts tripped a deterministic RED gate or when adding a new audit rule to the runtime contract.
    - Escalates-to: system/core/engine.py; system/server/tests/test_lab_contract_audit.py
    - Navigation-group: kernel_lib
    """
    hard_fails: List[str] = []
    soft_violations: Dict[str, int] = {}
    details: Dict[str, Any] = {}

    # --- Question mark ban in compute-node outputs ---
    question_hits: List[str] = []
    for node_id in QUESTION_MARK_SCAN_NODES:
        data = _load_artifact_data(artifacts_dir, node_id)
        if data is None:
            continue
        for text in _iter_strings(data):
            if "?" in text:
                question_hits.append(node_id)
                break
    if question_hits:
        hard_fails.append("QUESTION_MARK_OUTPUT")
        details["question_mark_nodes"] = sorted(set(question_hits))
        soft_violations["question_mark_output"] = len(question_hits)

    # --- Tuple syntax + annotation checks ---
    tuple_format_violations: List[str] = []
    two_sentence_violations: List[str] = []
    annotation_collapse_violations: List[str] = []

    for node_id in (*PHASE1_MINERS, *PHASE2_MINERS):
        data = _load_artifact_data(artifacts_dir, node_id)
        for line in _extract_tuple_lines(data):
            fields = _split_tuple_fields(line)
            if fields is None:
                tuple_format_violations.append(f"{node_id}: {line[:200]}")
                continue
            annotation = fields[2]
            sentences = _split_sentences(annotation)
            if len(sentences) < 2:
                two_sentence_violations.append(f"{node_id}: {line[:200]}")
                continue
            if node_id in PHASE2_MINERS:
                s1 = _normalize_sentence(sentences[0])
                s2 = _normalize_sentence(sentences[1])
                if s1 and s2:
                    ratio = SequenceMatcher(a=s1, b=s2).ratio()
                    if ratio >= 0.90:
                        annotation_collapse_violations.append(f"{node_id}: {line[:200]}")

    if tuple_format_violations:
        hard_fails.append("TUPLE_FORMAT_VIOLATION")
        soft_violations["tuple_format"] = len(tuple_format_violations)
        details["tuple_format_violations"] = tuple_format_violations[:25]
    if two_sentence_violations:
        hard_fails.append("ANNOTATION_MISSING_TWO_SENTENCES")
        soft_violations["annotation_two_sentence"] = len(two_sentence_violations)
        details["annotation_two_sentence_violations"] = two_sentence_violations[:25]
    if annotation_collapse_violations:
        hard_fails.append("ANNOTATION_COLLAPSE")
        soft_violations["annotation_collapse"] = len(annotation_collapse_violations)
        details["annotation_collapse_violations"] = annotation_collapse_violations[:25]

    # --- Thesis inheritance exact match ---
    decide = _load_artifact_data(artifacts_dir, "lab_decide")
    director = _resolve_cp2_data(_load_artifact_data(artifacts_dir, "lab_director"))
    decide_thesis = decide.get("epicentre_thesis") if isinstance(decide, dict) else None
    director_thesis = director.get("epicentre_thesis") if isinstance(director, dict) else None
    if (
        isinstance(decide_thesis, str)
        and isinstance(director_thesis, str)
        and decide_thesis != director_thesis
    ):
        hard_fails.append("THESIS_INHERITANCE")
        soft_violations["thesis_inheritance"] = 1

    # --- Prediction grounding against cross_corr_v2 valid targets ---
    cross_corr_v2 = _load_artifact_data(artifacts_dir, "lab_cross_corr_v2")
    valid_targets = _collect_valid_targets(cross_corr_v2)
    ungrounded: List[str] = []
    if isinstance(director, dict):
        predictions = director.get("predictions_t")
        if isinstance(predictions, list):
            for pred in predictions:
                if not isinstance(pred, dict):
                    continue
                target_id = str(pred.get("target_id", "")).upper().strip()
                if not target_id:
                    continue
                if valid_targets and target_id not in valid_targets:
                    ungrounded.append(target_id)
    if ungrounded:
        hard_fails.append("UNGROUNDED_TARGET")
        soft_violations["ungrounded_target"] = len(ungrounded)
        details["ungrounded_targets"] = sorted(set(ungrounded))

    # --- Market-fusion readiness gate for candidate cross-feed claims ---
    readiness_preflights: List[Dict[str, Any]] = []
    for node_id in CROSS_FEED_CLAIM_ARTIFACT_IDS:
        data = _load_artifact_data(artifacts_dir, node_id)
        if data is None:
            continue
        readiness_preflights.extend(
            preflight_consumer_claims(data, default_consumer_name=node_id)
        )

    if isinstance(director, dict):
        for field in CROSS_FEED_CLAIM_FIELDS:
            claims = director.get(field)
            if claims is None:
                continue
            readiness_preflights.extend(
                preflight_consumer_claims(
                    {
                        "consumer_name": "lab_director",
                        "claims": claims,
                    },
                    default_consumer_name="lab_director",
                )
            )

    refused_preflights = [
        row for row in readiness_preflights if row.get("decision") == "refuse"
    ]
    if refused_preflights:
        hard_fails.append("MARKET_FUSION_READINESS_REFUSAL")
        soft_violations["market_fusion_readiness_refusal"] = len(refused_preflights)
        details["market_fusion_readiness_refusals"] = refused_preflights

    # --- Contradiction reconciliation completeness ---
    unresolved_bifurcations: List[str] = []
    cross_corr_v1 = _load_artifact_data(artifacts_dir, "lab_cross_corr_v1")
    bifurcation_ids: Set[str] = set()
    if isinstance(cross_corr_v1, dict):
        for entry in cross_corr_v1.get("bifurcations", []):
            if not isinstance(entry, dict):
                continue
            bid = str(entry.get("id") or "").strip()
            if bid:
                bifurcation_ids.add(bid)

    resolved_ids: Set[str] = set()
    if isinstance(decide, dict):
        resolutions = decide.get("bifurcation_resolutions")
        if isinstance(resolutions, list):
            for res in resolutions:
                if not isinstance(res, dict):
                    continue
                rid = str(res.get("bifurcation_id") or res.get("id") or "").strip()
                if rid:
                    resolved_ids.add(rid)

    if bifurcation_ids:
        missing = sorted(bifurcation_ids - resolved_ids)
        if missing:
            unresolved_bifurcations.extend(missing)

    if unresolved_bifurcations:
        hard_fails.append("CONTRADICTION_AMNESIA")
        soft_violations["contradiction_amnesia"] = len(unresolved_bifurcations)
        details["unresolved_bifurcations"] = unresolved_bifurcations

    # Stable deterministic ordering
    hard_fails = sorted(set(hard_fails))
    soft_violations = {k: int(soft_violations[k]) for k in sorted(soft_violations.keys())}

    return {
        "version": "1.0.0",
        "status": "red" if hard_fails else "green",
        "hard_fails": hard_fails,
        "soft_violations": soft_violations,
        "details": details,
    }
