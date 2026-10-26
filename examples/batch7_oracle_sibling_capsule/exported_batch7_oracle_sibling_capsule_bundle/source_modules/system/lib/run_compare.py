"""
[PURPOSE]
- Teleology: Provide reusable deterministic subject-vs-truth comparison helpers for Oracle v1
  and kernel cross-run diagnostics.
- Mechanism: Pure artifact reads over paired run directories; normalize stock+ETF price tables,
  Lab CP2 predictions, and compact grading/comparison summaries.

[INTERFACE]
- Reads: run_dir/artifacts/{global_stock_feed.json, global_etf_feed.json, lab_director.json}
- Writes: None.
- Exports: load_feed_prices, load_predictions, load_director_meta, combined_prices,
  equity_feed_health, compare_equity_runs, grade_predictions.

[FLOW]
- load_feed_prices(), load_predictions(), and load_director_meta() normalize run artifacts -> combined_prices() unions stock and ETF tables -> compare_equity_runs() and grade_predictions() emit deterministic subject-vs-truth summaries for kernel or Oracle diagnostics.
- When-needed: Open when Oracle or kernel diagnostics need deterministic subject-vs-truth run comparison without re-implementing artifact readers.
- Escalates-to: system/lib/artifacts.py; system/lib/schema_validator.py; system/lib/citations.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- Reads: Existing run artifact JSON; no provider or external binary calls.
- Missing feed/prediction data is normalized by local artifact loaders.

[CONSTRAINTS]
- Read-only and deterministic: no writes, no network, no runtime side effects.
- Price comparisons are equity-wide: stock + ETF union.
- Missing artifacts degrade to empty dict/list rather than raising.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return value
        try:
            return float(token)
        except Exception:
            return value
    return value


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _iter_tables(node: Any):
    if isinstance(node, dict):
        columns = node.get("columns")
        rows = node.get("rows")
        if isinstance(columns, list) and isinstance(rows, list):
            yield columns, rows
        for value in node.values():
            yield from _iter_tables(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_tables(item)


def load_feed_prices(run_dir: Path | str, feed_name: str) -> Dict[str, Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load one equity feed artifact from a run directory into a ticker-keyed price dict.
    - Guarantee: Returns a dict mapping uppercase ticker strings to their full row record, or an empty dict when the artifact is missing or unreadable.
    - Fails: None — missing or malformed artifacts degrade to an empty dict.
    """
    run_dir = Path(run_dir)
    path = run_dir / "artifacts" / f"{feed_name}.json"
    if not path.exists():
        return {}

    payload = _load_json(path)
    data = payload.get("data", {})
    result: Dict[str, Dict[str, Any]] = {}
    for columns, rows in _iter_tables(data):
        if not all(isinstance(col, str) for col in columns):
            continue
        for row in rows:
            if not isinstance(row, list):
                continue
            record = {
                str(col): _coerce_scalar(row[idx]) if idx < len(row) else None
                for idx, col in enumerate(columns)
            }
            ticker = record.get("Ticker") or record.get("ticker")
            if not ticker:
                continue
            result[str(ticker).upper().strip()] = record
    return result


def load_predictions(run_dir: Path | str, artifact_id: str = "lab_director") -> List[Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load the predictions_t list from a Lab CP2 artifact in a run directory.
    - Guarantee: Returns a list of prediction dicts, or an empty list when the artifact is missing, unreadable, or contains no predictions.
    - Fails: None — missing or malformed artifacts degrade to an empty list.
    """
    run_dir = Path(run_dir)
    path = run_dir / "artifacts" / f"{artifact_id}.json"
    if not path.exists():
        return []
    payload = _load_json(path)
    data = payload.get("data", {})
    predictions = data.get("predictions_t", []) if isinstance(data, dict) else []
    if not isinstance(predictions, list):
        return []
    return [item for item in predictions if isinstance(item, dict)]


def load_director_meta(run_dir: Path | str, artifact_id: str = "lab_director") -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load compact Lab CP2 metadata and selected top-level fields from a run directory artifact.
    - Guarantee: Returns a dict with dominant_evidence_track, pre_pricing_assessment, trade_rationale, target_time_iso, horizon_label, and as_of fields, or an empty dict when the artifact is missing or unreadable.
    - Fails: None — missing or malformed artifacts degrade to an empty dict.
    """
    run_dir = Path(run_dir)
    path = run_dir / "artifacts" / f"{artifact_id}.json"
    if not path.exists():
        return {}
    payload = _load_json(path)
    data = payload.get("data", {})
    meta = payload.get("metadata", {})
    if not isinstance(data, dict):
        data = {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "dominant_evidence_track": data.get("dominant_evidence_track"),
        "pre_pricing_assessment": data.get("pre_pricing_assessment"),
        "trade_rationale": data.get("trade_rationale"),
        "target_time_iso": meta.get("target_time_iso"),
        "horizon_label": meta.get("horizon_label"),
        "as_of": meta.get("as_of"),
    }


def combined_prices(run_dir: Path | str) -> Dict[str, Dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Union stock and ETF price tables for a run into one ticker-keyed dict.
    - Guarantee: Returns a merged dict covering both global_stock_feed and global_etf_feed tickers, with ETF rows overwriting stock rows on key collision.
    - Fails: None — missing feed artifacts degrade gracefully to empty contributions.
    """
    prices: Dict[str, Dict[str, Any]] = {}
    prices.update(load_feed_prices(run_dir, "global_stock_feed"))
    prices.update(load_feed_prices(run_dir, "global_etf_feed"))
    return prices


def _is_numeric_price(row: Dict[str, Any] | None) -> bool:
    if not isinstance(row, dict):
        return False
    return isinstance(row.get("Price"), (int, float))


def _price_count(rows: Dict[str, Dict[str, Any]]) -> int:
    return sum(1 for row in rows.values() if _is_numeric_price(row))


def equity_feed_health(subject_run_dir: Path | str, truth_run_dir: Path | str) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Summarize whether a paired subject/truth run has enough equity feed data to grade Lab CP2 targets.
    - Mechanism: Load subject and truth stock/ETF price maps, intersect their ticker universes, then compare Lab prediction targets against available numeric prices.
    - Guarantee: Returns READY when all prediction targets have subject and truth prices, DEGRADED when only some targets are comparable, and BLOCKED when no deterministic equity grading target is available.
    - Fails: None — missing artifacts degrade into counts, missing target lists, and diagnostics.
    - When-needed: Open when Oracle or Evolve needs to distinguish a real miss from missing subject/truth feed coverage.
    - Escalates-to: system/lib/run_compare.py::load_feed_prices; system/lib/run_compare.py::load_predictions
    - Navigation-group: kernel_lib
    """
    subject_run_dir = Path(subject_run_dir)
    truth_run_dir = Path(truth_run_dir)

    subject_stock = load_feed_prices(subject_run_dir, "global_stock_feed")
    subject_etf = load_feed_prices(subject_run_dir, "global_etf_feed")
    truth_stock = load_feed_prices(truth_run_dir, "global_stock_feed")
    truth_etf = load_feed_prices(truth_run_dir, "global_etf_feed")
    subject_prices = {**subject_stock, **subject_etf}
    truth_prices = {**truth_stock, **truth_etf}
    prediction_targets = sorted(
        {
            str(item.get("target_id")).upper().strip()
            for item in load_predictions(subject_run_dir)
            if item.get("target_id")
        }
    )

    missing_subject = sorted(
        target
        for target in prediction_targets
        if not _is_numeric_price(subject_prices.get(target))
    )
    missing_truth = sorted(
        target
        for target in prediction_targets
        if not _is_numeric_price(truth_prices.get(target))
    )
    comparable = sorted(
        target
        for target in prediction_targets
        if target not in missing_subject and target not in missing_truth
    )

    diagnostics: List[str] = []
    if not prediction_targets:
        diagnostics.append("no Lab CP2 prediction targets found")
    if not subject_prices:
        diagnostics.append("subject stock+ETF price universe is empty")
    if not truth_prices:
        diagnostics.append("truth stock+ETF price universe is empty")
    if missing_subject:
        diagnostics.append(
            "missing subject prices for targets: " + ", ".join(missing_subject)
        )
    if missing_truth:
        diagnostics.append(
            "missing truth prices for targets: " + ", ".join(missing_truth)
        )

    if not prediction_targets or not comparable:
        status = "BLOCKED"
    elif missing_subject or missing_truth:
        status = "DEGRADED"
    else:
        status = "READY"

    return {
        "status": status,
        "subject": {
            "stock_ticker_count": len(subject_stock),
            "etf_ticker_count": len(subject_etf),
            "stock_price_count": _price_count(subject_stock),
            "etf_price_count": _price_count(subject_etf),
            "ticker_count": len(subject_prices),
        },
        "truth": {
            "stock_ticker_count": len(truth_stock),
            "etf_ticker_count": len(truth_etf),
            "stock_price_count": _price_count(truth_stock),
            "etf_price_count": _price_count(truth_etf),
            "ticker_count": len(truth_prices),
        },
        "common_ticker_count": len(set(subject_prices.keys()) & set(truth_prices.keys())),
        "prediction_target_count": len(prediction_targets),
        "comparable_prediction_targets": comparable,
        "missing_subject_price_targets": missing_subject,
        "missing_truth_price_targets": missing_truth,
        "diagnostics": diagnostics,
    }


def compare_equity_runs(
    subject_run_dir: Path | str,
    truth_run_dir: Path | str,
    *,
    top_n: int = 20,
) -> Dict[str, Any]:
    """[ACTION]
    - Teleology: Summarize realized price movement between a subject run and a truth run across the shared equity universe.
    - Mechanism: Load stock and ETF tables for both runs, intersect tickers, compute absolute/percent deltas, and highlight which movers were explicit prediction targets.
    - Guarantee: Returns a deterministic comparison mapping ordered by descending absolute percent move.
    - Fails: None — missing artifacts degrade to empty tables and therefore empty summaries.
    - When-needed: Open when cross-run diagnostics need the canonical top-mover and prediction-target delta summary for paired equity runs.
    - Escalates-to: system/lib/artifacts.py; system/lib/schema_validator.py::validate_prediction_reconciliation
    - Navigation-group: kernel_lib
    """
    subject_run_dir = Path(subject_run_dir)
    truth_run_dir = Path(truth_run_dir)

    subject_prices = combined_prices(subject_run_dir)
    truth_prices = combined_prices(truth_run_dir)
    predictions = load_predictions(subject_run_dir)
    prediction_targets = sorted(
        {
            str(item.get("target_id")).upper().strip()
            for item in predictions
            if item.get("target_id")
        }
    )

    deltas: List[Dict[str, Any]] = []
    for ticker in sorted(set(subject_prices.keys()) & set(truth_prices.keys())):
        subject_price = subject_prices[ticker].get("Price")
        truth_price = truth_prices[ticker].get("Price")
        if not isinstance(subject_price, (int, float)) or not isinstance(truth_price, (int, float)):
            continue
        if subject_price == 0:
            continue
        abs_delta = truth_price - subject_price
        pct_delta = (abs_delta / subject_price) * 100
        deltas.append(
            {
                "ticker": ticker,
                "subject_price": subject_price,
                "truth_price": truth_price,
                "abs_delta": abs_delta,
                "pct_delta": pct_delta,
                "is_prediction_target": ticker in prediction_targets,
            }
        )

    deltas.sort(key=lambda item: abs(float(item.get("pct_delta", 0.0))), reverse=True)
    return {
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "prediction_targets": prediction_targets,
        "common_ticker_count": len(deltas),
        "top_movers": deltas[: max(0, int(top_n))],
        "prediction_target_moves": [item for item in deltas if item["is_prediction_target"]],
    }


def grade_predictions(subject_run_dir: Path | str, truth_run_dir: Path | str) -> Dict[str, Any]:
    """[ACTION]
    - Teleology: Grade Lab CP2 predictions against realized truth-run prices and return hit/miss/ungraded outcomes.
    - Mechanism: Load predictions plus truth prices, compare predicted direction and price against realized movement, and aggregate per-target rows with compact summary metrics.
    - Guarantee: Returns a deterministic grading payload with per-target results and aggregate hit-rate metadata.
    - Fails: None — missing predictions or prices degrade to ungraded rows and empty summaries instead of raising.
    - When-needed: Open when Oracle hindsight or kernel diagnostics need the canonical grading pass for CP2 predictions against a truth run.
    - Escalates-to: system/lib/schema_validator.py::validate_prediction_reconciliation; system/lib/artifacts.py
    - Navigation-group: kernel_lib
    """
    subject_run_dir = Path(subject_run_dir)
    truth_run_dir = Path(truth_run_dir)

    predictions = load_predictions(subject_run_dir)
    truth_prices = combined_prices(truth_run_dir)
    meta = load_director_meta(subject_run_dir)
    results: List[Dict[str, Any]] = []
    hits = 0
    misses = 0
    ungraded = 0

    for prediction in predictions:
        target_id = str(prediction.get("target_id", "")).upper().strip()
        pred_dir = str(prediction.get("direction", "")).upper().strip()
        snapshot_price = prediction.get("snapshot_price")
        pred_price = prediction.get("target_price")
        row = truth_prices.get(target_id)

        base = {
            "target_id": target_id,
            "predicted_direction": pred_dir,
            "snapshot_price": snapshot_price,
            "predicted_price": pred_price,
        }
        if not row or not isinstance(snapshot_price, (int, float)):
            results.append({**base, "status": "UNGRADED"})
            ungraded += 1
            continue

        realized_price = row.get("Price")
        if not isinstance(realized_price, (int, float)):
            results.append({**base, "status": "UNGRADED"})
            ungraded += 1
            continue

        realized_delta = realized_price - snapshot_price
        realized_direction = "UP" if realized_delta > 0 else "DOWN" if realized_delta < 0 else "FLAT"
        direction_hit = pred_dir == realized_direction
        pred_error_pct = None
        abs_error = None
        realized_pct_move = None
        if snapshot_price != 0:
            realized_pct_move = (realized_delta / snapshot_price) * 100
        if isinstance(pred_price, (int, float)):
            abs_error = abs(pred_price - realized_price)
            if snapshot_price != 0:
                pred_error_pct = ((pred_price - realized_price) / snapshot_price) * 100

        if direction_hit:
            hits += 1
        else:
            misses += 1

        results.append(
            {
                **base,
                "status": "GRADED",
                "realized_price": realized_price,
                "realized_direction": realized_direction,
                "direction_hit": direction_hit,
                "pred_error_pct": pred_error_pct,
                "abs_error": abs_error,
                "realized_pct_move": realized_pct_move,
            }
        )

    total_graded = hits + misses
    hit_rate = (hits / total_graded) if total_graded else None
    return {
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "horizon_label": meta.get("horizon_label"),
        "target_time_iso": meta.get("target_time_iso"),
        "dominant_evidence_track": meta.get("dominant_evidence_track"),
        "pre_pricing_assessment": meta.get("pre_pricing_assessment"),
        "results": results,
        "summary": {
            "hits": hits,
            "misses": misses,
            "ungraded": ungraded,
            "graded": total_graded,
            "hit_rate": hit_rate,
        },
    }
