"""
[PURPOSE]
- Teleology: Provide deterministic set-operation diffs between Lab and Oracle CP2 artifact
  arrays. A pure measurement layer — no semantic interpretation, no blame attribution.
- Mechanism: Python set math on ledger_id and target_id arrays extracted from CP2 dicts;
  all list outputs serialized as sorted() to guarantee byte-identical JSON across environments.

[INTERFACE]
- Reads: CP2 evidence_dictionary lists and predictions_t lists (plain dicts).
- Writes: None (pure computation).
- Exports: EvidenceDiffResult, PredictionDiffResult, diff_evidence, diff_predictions.

[FLOW]
- diff_evidence: set operations on ledger_id arrays → missed, extra, overlap.
- diff_predictions: match on target_id → matching, divergent, missing_targets, extra_targets.
- to_json_dict: deterministic serialization via sorted() on all set-derived lists.

[DEPENDENCIES]
- Python stdlib: dataclasses, typing.

[CONSTRAINTS]
- All list outputs are sorted() to guarantee byte-identical JSON serialization.
- Functions are pure: no mutation of inputs, no IO, no side effects.
- missed = oracle_ids - lab_ids (Lab failed to cite these).
- extra  = lab_ids - oracle_ids (Lab cited these but Oracle did not).
- Missing/malformed entries (not dicts, no ledger_id, no target_id) are silently skipped.
- When-needed: Open when Lab-versus-Oracle CP2 comparison needs the canonical deterministic diff contract for evidence or prediction arrays before report aggregation.
- Escalates-to: system/lib/observer_report.py::generate_observation_report; tools/diff/observer_lane_diff.py::run
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Evidence Diff
# ---------------------------------------------------------------------------

@dataclass
class EvidenceDiffResult:
    """
    [ROLE]
    - Set-operation result for evidence_dictionary arrays between Lab and Oracle CP2.
    - All list fields are sorted for deterministic serialization.
    """
    missed_ledger_ids: List[str]          # oracle_ids - lab_ids
    extra_ledger_ids: List[str]           # lab_ids - oracle_ids
    overlap_ledger_ids: List[str]         # oracle_ids & lab_ids
    missed_entries: List[Dict[str, Any]]  # Full Oracle entries for missed IDs
    extra_entries: List[Dict[str, Any]]   # Full Lab entries for extra IDs

    def to_json_dict(self) -> Dict[str, Any]:
        """
        [ACTION]
        - Return a JSON-serializable dict with all list fields sorted for byte-identical output.
        """
        return {
            "missed_ledger_ids": sorted(self.missed_ledger_ids),
            "extra_ledger_ids": sorted(self.extra_ledger_ids),
            "overlap_ledger_ids": sorted(self.overlap_ledger_ids),
            "missed_entries": sorted(
                self.missed_entries, key=lambda e: e.get("ledger_id", "")
            ),
            "extra_entries": sorted(
                self.extra_entries, key=lambda e: e.get("ledger_id", "")
            ),
        }


def diff_evidence(
    lab_dict: List[Dict[str, Any]],
    oracle_dict: List[Dict[str, Any]],
) -> EvidenceDiffResult:
    """
    [ACTION]
    - Teleology: Compute the deterministic evidence-delta surface between Lab and Oracle CP2 payloads.
    - Mechanism: Index both evidence arrays by ledger_id, perform set subtraction/intersection, and project the missed/extra full-entry lists from the corresponding indexes.
    - Guarantee: Returns an EvidenceDiffResult whose list fields are sorted and whose missed/extra semantics follow oracle-minus-lab and lab-minus-oracle respectively.
    - Fails: None.
    - When-needed: Open when a report or lane-diff tool needs the authoritative evidence_dictionary diff semantics on ledger_id.
    - Escalates-to: system/lib/observer_report.py::generate_observation_report; tools/diff/observer_lane_diff.py::run
    """
    lab_idx: Dict[str, Dict] = {
        e["ledger_id"]: e
        for e in lab_dict
        if isinstance(e, dict) and e.get("ledger_id")
    }
    oracle_idx: Dict[str, Dict] = {
        e["ledger_id"]: e
        for e in oracle_dict
        if isinstance(e, dict) and e.get("ledger_id")
    }

    lab_ids = set(lab_idx)
    oracle_ids = set(oracle_idx)

    missed_ids = sorted(oracle_ids - lab_ids)
    extra_ids = sorted(lab_ids - oracle_ids)
    overlap_ids = sorted(oracle_ids & lab_ids)

    return EvidenceDiffResult(
        missed_ledger_ids=missed_ids,
        extra_ledger_ids=extra_ids,
        overlap_ledger_ids=overlap_ids,
        missed_entries=[oracle_idx[lid] for lid in missed_ids],
        extra_entries=[lab_idx[lid] for lid in extra_ids],
    )


# ---------------------------------------------------------------------------
# Prediction Diff
# ---------------------------------------------------------------------------

@dataclass
class PredictionDiffResult:
    """
    [ROLE]
    - Match-and-compare result for predictions_t arrays between Lab and Oracle CP2.
    - All list fields are sorted by target_id for deterministic serialization.
    """
    matching: List[Dict[str, Any]]         # target_id + direction both agree
    divergent: List[Dict[str, Any]]        # target_id matches, direction differs
    missing_targets: List[Dict[str, Any]]  # In Oracle, not in Lab
    extra_targets: List[Dict[str, Any]]    # In Lab, not in Oracle

    def to_json_dict(self) -> Dict[str, Any]:
        """
        [ACTION]
        - Return a JSON-serializable dict with all list fields sorted by target_id.
        """
        _key = lambda x: x.get("target_id", "")
        return {
            "matching": sorted(self.matching, key=_key),
            "divergent": sorted(self.divergent, key=_key),
            "missing_targets": sorted(self.missing_targets, key=_key),
            "extra_targets": sorted(self.extra_targets, key=_key),
        }


def diff_predictions(
    lab_preds: List[Dict[str, Any]],
    oracle_preds: List[Dict[str, Any]],
) -> PredictionDiffResult:
    """
    [ACTION]
    - Teleology: Compute the deterministic prediction-delta surface between Lab and Oracle CP2 payloads.
    - Mechanism: Index both prediction arrays by target_id, compare direction values for shared targets, and project matching/divergent/missing/extra target rows.
    - Guarantee: Returns a PredictionDiffResult whose list fields are sorted by target_id.
    - Fails: None.
    - When-needed: Open when a report or validation tool needs the canonical predictions_t diff semantics on target_id and direction.
    - Escalates-to: system/lib/observer_report.py::generate_observation_report; tools/diff/observer_diff_master.py
    """
    lab_idx: Dict[str, Dict] = {
        p["target_id"]: p
        for p in lab_preds
        if isinstance(p, dict) and p.get("target_id")
    }
    oracle_idx: Dict[str, Dict] = {
        p["target_id"]: p
        for p in oracle_preds
        if isinstance(p, dict) and p.get("target_id")
    }

    lab_targets = set(lab_idx)
    oracle_targets = set(oracle_idx)
    common = sorted(lab_targets & oracle_targets)

    matching: List[Dict] = []
    divergent: List[Dict] = []
    for tid in common:
        lp = lab_idx[tid]
        op = oracle_idx[tid]
        entry = {
            "target_id": tid,
            "lab_direction": lp.get("direction"),
            "oracle_direction": op.get("direction"),
        }
        if lp.get("direction") == op.get("direction"):
            matching.append(entry)
        else:
            divergent.append(entry)

    missing = sorted(oracle_targets - lab_targets)
    extra = sorted(lab_targets - oracle_targets)

    return PredictionDiffResult(
        matching=matching,
        divergent=divergent,
        missing_targets=[oracle_idx[t] for t in missing],
        extra_targets=[lab_idx[t] for t in extra],
    )
