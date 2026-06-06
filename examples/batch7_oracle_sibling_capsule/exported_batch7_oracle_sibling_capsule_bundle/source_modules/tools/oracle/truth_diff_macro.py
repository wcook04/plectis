"""
[PURPOSE]
- Teleology: Emit a compact deterministic macro before/after diff for Oracle v1.
- Mechanism: Compare subject and truth macro feed rows by identity and summarize changed fields.

[INTERFACE]
- Inputs: `config.runtime.oracle_subject_run_dir` and `config.runtime.oracle_truth_run_dir`.
- Outputs: Success envelope carrying changed macro series, new series, and dropped series between the paired runs.
- Exports: `run`.

[FLOW]
- Resolve both run directories from runtime config.
- Load subject/truth `global_macro_feed` artifacts and normalize rows by record identity.
- Compare overlapping series field-by-field, rank changed series by strongest absolute delta, and emit the top slice.

[DEPENDENCIES]
- system.lib.artifacts: Load `global_macro_feed` artifacts from both run directories.

[CONSTRAINTS]
- Read-only over the paired run artifacts; this tool does not mutate subject or truth state.
- Identity fallback order is `_ID_KEYS`, then first non-empty field in the record.
- When-needed: Open when Oracle needs the subject-versus-truth macro diff payload, including changed series ranking plus new and dropped series detection.
- Escalates-to: tools/oracle/subject_index.py::run; tools/calculator/calculator.py::run
- Navigation-group: market_intelligence
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from system.lib.artifacts import load_artifact


_ID_KEYS = ("slug", "Slug", "Ticker", "ticker", "Series", "series", "Indicator", "indicator")


def _require_run_dir(config: Dict[str, Any], key: str) -> Path:
    runtime = config.get("runtime", {}) if isinstance(config, dict) else {}
    raw = runtime.get(key)
    if not raw:
        raise ValueError(f"{key} is required for oracle_truth_diff_macro")
    run_dir = Path(str(raw))
    if not run_dir.exists():
        raise ValueError(f"{key} does not exist: {run_dir}")
    return run_dir


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


def _iter_tables(node: Any) -> Iterable[Tuple[List[Any], List[Any]]]:
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


def _load_macro_rows(run_dir: Path) -> Tuple[Any, Dict[str, Dict[str, Any]]]:
    artifact = load_artifact(run_dir, "global_macro_feed") or {}
    metadata = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
    data = artifact.get("data", {}) if isinstance(artifact, dict) else {}
    rows_by_id: Dict[str, Dict[str, Any]] = {}
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
            record_id = None
            for key in _ID_KEYS:
                value = record.get(key)
                if value is not None and str(value).strip():
                    record_id = str(value).strip()
                    break
            if record_id is None:
                for value in record.values():
                    if value is not None and str(value).strip():
                        record_id = str(value).strip()
                        break
            if record_id:
                rows_by_id[record_id] = record
    as_of = metadata.get("as_of") if isinstance(metadata, dict) else None
    return as_of, rows_by_id


def _compare_record(subject: Dict[str, Any], truth: Dict[str, Any]) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []
    for field in sorted(set(subject.keys()) | set(truth.keys())):
        if field in _ID_KEYS:
            continue
        before = subject.get(field)
        after = truth.get(field)
        if before == after:
            continue
        change: Dict[str, Any] = {
            "field": field,
            "subject_value": before,
            "truth_value": after,
        }
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            delta = after - before
            change["delta"] = delta
            if before != 0:
                change["pct_delta"] = (delta / before) * 100
        changes.append(change)
    return changes


def run(config: Dict[str, Any], run_dir: str | None = None) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the compact Oracle macro truth-diff envelope from paired subject and truth runs.
    - Mechanism: Resolve both run directories, load macro rows, compare overlapping series, rank material changes, and return a success payload with change summaries.
    - Reads: `config.runtime.oracle_subject_run_dir`, `config.runtime.oracle_truth_run_dir`, and both runs' `global_macro_feed` artifacts.
    - Writes: None.
    - Guarantee: Returns a success envelope containing compared series counts plus changed, new, and dropped series lists.
    - Fails: Raises ValueError when either runtime run directory is missing or invalid; missing macro artifacts degrade to empty row maps through helper defaults.
    - When-needed: Open when a caller needs the exact Oracle macro diff shape or the ranking rule for material changes between subject and truth runs.
    - Escalates-to: tools/oracle/subject_index.py::run; tools/calculator/calculator.py::run
    - Navigation-group: market_intelligence
    """
    subject_run_dir = _require_run_dir(config, "oracle_subject_run_dir")
    truth_run_dir = _require_run_dir(config, "oracle_truth_run_dir")
    subject_as_of, subject_rows = _load_macro_rows(subject_run_dir)
    truth_as_of, truth_rows = _load_macro_rows(truth_run_dir)

    common_ids = sorted(set(subject_rows.keys()) & set(truth_rows.keys()))
    changed_series: List[Dict[str, Any]] = []
    for series_id in common_ids:
        changes = _compare_record(subject_rows[series_id], truth_rows[series_id])
        if not changes:
            continue
        changed_series.append(
            {
                "series_id": series_id,
                "changes": changes,
            }
        )

    def _rank(entry: Dict[str, Any]) -> float:
        best = 0.0
        for change in entry.get("changes", []):
            if isinstance(change.get("pct_delta"), (int, float)):
                best = max(best, abs(float(change["pct_delta"])))
            elif isinstance(change.get("delta"), (int, float)):
                best = max(best, abs(float(change["delta"])))
            else:
                best = max(best, 0.001)
        return best

    changed_series.sort(key=_rank, reverse=True)
    data = {
        "subject_run_id": subject_run_dir.name,
        "truth_run_id": truth_run_dir.name,
        "subject_as_of": subject_as_of,
        "truth_as_of": truth_as_of,
        "series_compared": len(common_ids),
        "changed_series": changed_series[:50],
        "new_series": sorted(set(truth_rows.keys()) - set(subject_rows.keys())),
        "dropped_series": sorted(set(subject_rows.keys()) - set(truth_rows.keys())),
    }
    return {
        "metadata": {
            "tool": "oracle_truth_diff_macro",
            "status": "success",
            "subject_run_id": subject_run_dir.name,
            "truth_run_id": truth_run_dir.name,
            "diagnostics": {
                "input_rows": len(common_ids),
                "output_rows": len(data["changed_series"]),
                "dropped_rows": len(data["dropped_series"]),
                "warnings": [],
            },
        },
        "data": data,
    }
