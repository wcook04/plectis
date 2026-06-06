"""
[PURPOSE]
- Teleology: Build the subject-side Oracle v1 index from the paired Lab run.
- Mechanism: Read compact Lab artifacts plus subject raw feeds when needed; emit a
  subject-only grounding map for downstream Oracle reasoning.

[INTERFACE]
- Inputs: `config.runtime.oracle_subject_run_dir` pointing at the subject run.
- Outputs: Success envelope carrying subject evidence maps, predictions, price tables, and lane summaries.
- Exports: `run`.

[FLOW]
- Resolve the subject run directory and optional runtime context.
- Load Lab CP1/CP2 artifacts plus cross-correlation targets.
- Partition evidence into admissible versus contextual subject buckets.
- Attach subject price maps, predictions, and compact Phase-2 lane summaries.
- Return a success envelope for downstream Oracle tools.

[DEPENDENCIES]
- system.lib.artifacts: Load subject-run artifacts and compact lane outputs.
- system.lib.run_compare: Reuse shared prediction and price-table loaders.

[CONSTRAINTS]
- Read-only over subject-run artifacts; this module does not mutate subject state.
- Missing or malformed optional artifacts degrade to empty structures via helper defaults.
- When-needed: Open when Oracle needs the subject-side grounding map built from a paired Lab run, including admissible evidence, target prices, and lane summaries.
- Escalates-to: tools/oracle/subject_index.py::run; tools/oracle/truth_diff_equity.py::run; tools/calculator/calculator.py::run
- Navigation-group: market_intelligence
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from system.lib.artifacts import load_artifact, load_artifact_data
from system.lib.run_compare import combined_prices, load_predictions


_PHASE2_IDS = {
    "stock": "lab_miner_v2_stock",
    "etf": "lab_miner_v2_etf",
    "macro": "lab_miner_v2_macro",
    "news": "lab_miner_v2_news",
    "poly": "lab_miner_v2_poly",
    "calc": "lab_miner_v2_calc",
    "stockgrid": "lab_miner_v2_stockgrid",
}


def _require_subject_run_dir(config: Dict[str, Any]) -> Path:
    runtime = config.get("runtime", {}) if isinstance(config, dict) else {}
    raw = runtime.get("oracle_subject_run_dir")
    if not raw:
        raise ValueError("oracle_subject_run_dir is required for oracle_subject_index")
    run_dir = Path(str(raw))
    if not run_dir.exists():
        raise ValueError(f"oracle_subject_run_dir does not exist: {run_dir}")
    return run_dir


def _load_runtime_context(run_dir: Path) -> Dict[str, Any]:
    path = run_dir / "runtime_context.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _clip(value: Any, limit: int = 1800) -> str:
    if isinstance(value, str):
        text = value.strip()
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except Exception:
            text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...[truncated]"


def _compact_evidence(entries: Any) -> List[Dict[str, Any]]:
    if not isinstance(entries, list):
        return []
    result: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        result.append(
            {
                "ref_id": entry.get("ref_id"),
                "ledger_id": entry.get("ledger_id"),
                "subject": entry.get("subject"),
                "signal_summary": entry.get("signal_summary"),
            }
        )
    return result


def _is_admissible_target_entry(entry: Dict[str, Any], valid_targets: set[str]) -> bool:
    subject = str(entry.get("subject") or "").upper().strip()
    ledger_id = str(entry.get("ledger_id") or "").upper().strip()
    if not subject or subject not in valid_targets:
        return False
    return ledger_id.startswith(("S_", "E_"))


def run(config: Dict[str, Any], run_dir: str | None = None) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the subject-side Oracle index payload from subject-run artifacts and paired Lab outputs.
    - Mechanism: Resolve the subject run directory, hydrate runtime context plus Lab artifacts, partition evidence into admissible and contextual buckets, merge prices and predictions, and emit a success envelope.
    - Reads: `config.runtime.oracle_subject_run_dir`, subject artifacts, and shared run-compare helpers.
    - Writes: None.
    - Guarantee: Returns a success payload with evidence maps, target lists, price maps, and compact Phase-2 lane summaries derived from the subject run.
    - Fails: Raises ValueError when `oracle_subject_run_dir` is missing or invalid; optional artifact read failures degrade to empty structures via helper defaults.
    - When-needed: Open when a caller needs the exact subject-index payload shape, admissible-support rules, or lane-summary hydration behavior.
    - Escalates-to: tools/oracle/subject_snapshot.py::run; tools/oracle/truth_diff_equity.py::run; tools/calculator/calculator.py::run
    """
    subject_run_dir = _require_subject_run_dir(config)
    ctx = _load_runtime_context(subject_run_dir)
    lab_decide = load_artifact(subject_run_dir, "lab_decide") or {}
    lab_director = load_artifact(subject_run_dir, "lab_director") or {}
    lab_cross_corr_v2 = load_artifact(subject_run_dir, "lab_cross_corr_v2") or {}
    lab_decide_data = lab_decide.get("data", {}) if isinstance(lab_decide, dict) else {}
    lab_director_data = lab_director.get("data", {}) if isinstance(lab_director, dict) else {}
    cross_corr_data = lab_cross_corr_v2.get("data", {}) if isinstance(lab_cross_corr_v2, dict) else {}
    if not isinstance(lab_decide_data, dict):
        lab_decide_data = {}
    if not isinstance(lab_director_data, dict):
        lab_director_data = {}
    if not isinstance(cross_corr_data, dict):
        cross_corr_data = {}

    evidence_dictionary = _compact_evidence(
        lab_director_data.get("evidence_dictionary") or lab_decide_data.get("evidence_dictionary") or []
    )
    evidence_by_subject: Dict[str, List[Dict[str, Any]]] = {}
    for entry in evidence_dictionary:
        subject = str(entry.get("subject") or "").upper().strip()
        if not subject:
            continue
        evidence_by_subject.setdefault(subject, []).append(entry)

    valid_prediction_targets = []
    raw_targets = cross_corr_data.get("valid_prediction_targets") if isinstance(cross_corr_data, dict) else None
    if isinstance(raw_targets, list):
        valid_prediction_targets = [
            str(token).upper().strip()
            for token in raw_targets
            if str(token).strip() and str(token).upper().strip() != "NONE"
        ]

    price_rows = combined_prices(subject_run_dir)
    target_subset = set(valid_prediction_targets)
    for pred in load_predictions(subject_run_dir):
        target_id = str(pred.get("target_id") or "").upper().strip()
        if target_id:
            target_subset.add(target_id)
    admissible_evidence_by_subject: Dict[str, List[Dict[str, Any]]] = {}
    contextual_evidence_by_subject: Dict[str, List[Dict[str, Any]]] = {}
    for subject, entries in evidence_by_subject.items():
        for entry in entries:
            target = (
                admissible_evidence_by_subject
                if _is_admissible_target_entry(entry, target_subset)
                else contextual_evidence_by_subject
            )
            target.setdefault(subject, []).append(entry)
    missing_admissible_support_targets = sorted(
        target
        for target in target_subset
        if target and target not in admissible_evidence_by_subject
    )
    subject_equity_rows_by_ticker = {
        ticker: row
        for ticker, row in price_rows.items()
        if ticker in target_subset
    }
    subject_equity_price_map = {
        ticker: row.get("Price")
        for ticker, row in price_rows.items()
        if isinstance(row, dict) and isinstance(row.get("Price"), (int, float))
    }

    phase2_lane_summaries: Dict[str, str] = {}
    for lane, artifact_id in _PHASE2_IDS.items():
        phase2_lane_summaries[lane] = _clip(load_artifact_data(subject_run_dir, artifact_id))

    data = {
        "subject_run_id": subject_run_dir.name,
        "subject_run_dir": str(subject_run_dir),
        "subject_snapshot_time": ctx.get("as_of") or ctx.get("time_anchor") or ctx.get("timestamp"),
        "target_time_iso": (
            (ctx.get("temporal_contract") or {}).get("target_time_iso")
            if isinstance(ctx.get("temporal_contract"), dict)
            else ctx.get("target_time_iso")
        ),
        "eligible_ledger_ids": sorted(
            {
                str(entry.get("ledger_id"))
                for entry in evidence_dictionary
                if entry.get("ledger_id")
            }
        ),
        "valid_prediction_targets": sorted(set(valid_prediction_targets)),
        "lab_predictions": load_predictions(subject_run_dir),
        "lab_cp1": {
            "epicentre_thesis": lab_decide_data.get("epicentre_thesis"),
            "dominant_evidence_track": lab_decide_data.get("dominant_evidence_track"),
            "pre_pricing_assessment": lab_decide_data.get("pre_pricing_assessment"),
        },
        "lab_cp2": {
            "epicentre_thesis": lab_director_data.get("epicentre_thesis"),
            "trade_rationale": lab_director_data.get("trade_rationale"),
            "predictions_t": lab_director_data.get("predictions_t"),
        },
        "evidence_dictionary": evidence_dictionary,
        "evidence_by_subject": dict(sorted(evidence_by_subject.items())),
        "admissible_evidence_by_subject": dict(sorted(admissible_evidence_by_subject.items())),
        "contextual_evidence_by_subject": dict(sorted(contextual_evidence_by_subject.items())),
        "missing_admissible_support_targets": missing_admissible_support_targets,
        "subject_equity_price_map": dict(sorted(subject_equity_price_map.items())),
        "subject_equity_rows_by_ticker": dict(sorted(subject_equity_rows_by_ticker.items())),
        "phase2_lane_summaries": phase2_lane_summaries,
    }
    return {
        "metadata": {
            "tool": "oracle_subject_index",
            "status": "success",
            "subject_run_id": subject_run_dir.name,
            "diagnostics": {
                "input_rows": 0,
                "output_rows": len(evidence_dictionary),
                "dropped_rows": 0,
                "warnings": [],
            },
        },
        "data": data,
    }
