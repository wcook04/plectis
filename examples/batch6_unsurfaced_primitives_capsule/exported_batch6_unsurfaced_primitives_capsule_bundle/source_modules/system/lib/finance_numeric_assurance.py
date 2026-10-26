"""
[PURPOSE]
- Teleology: Evaluate frontend-visible finance numbers before they are shown
  confidently in Intelligence / Market cockpit surfaces.
- Mechanism: Inspect the existing backend-owned market display contracts for
  semantic numeric invariants: finite values, declared units, source lineage,
  probability/confidence bounds, Stockgrid unit scale, and entity-level dedupe.
- Non-goal: This module does not fetch market data, format React UI, or invent
  finance semantics outside the generated mart / cockpit contracts.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "finance_numeric_assurance_v0"

SEVERITY_BLOCK = "block"
SEVERITY_DEMOTE = "demote"
SEVERITY_WARN = "warn"
SEVERITY_INFO = "info"

BLOCKING_SEVERITIES = {SEVERITY_BLOCK}
DISPLAY_DEMOTION_SEVERITIES = {SEVERITY_BLOCK, SEVERITY_DEMOTE}

STOCKGRID_FLOW_UNITS = {"usd", "usd_millions"}


def _records(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number(value: Any) -> float | None:
    if not _is_number(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _has_source_refs(row: Mapping[str, Any]) -> bool:
    refs = row.get("source_refs")
    if not isinstance(refs, list):
        return False
    return any(isinstance(ref, Mapping) and ref.get("kind") and ref.get("path") for ref in refs)


def _add_finding(
    findings: list[dict[str, Any]],
    *,
    check_id: str,
    severity: str,
    surface: str,
    path: str,
    field: str | None,
    problem: str,
    action: str,
    evidence: Mapping[str, Any] | None = None,
) -> None:
    finding: dict[str, Any] = {
        "finding_id": f"{check_id}:{path}:{field or '_'}",
        "check_id": check_id,
        "severity": severity,
        "surface": surface,
        "path": path,
        "problem": problem,
        "action": action,
    }
    if field:
        finding["field"] = field
    if evidence:
        finding["evidence"] = dict(evidence)
    findings.append(finding)


def _check_declared_number(
    findings: list[dict[str, Any]],
    *,
    surface: str,
    path: str,
    field: str,
    value: Any,
    required: bool = False,
) -> float | None:
    if value is None:
        if required:
            _add_finding(
                findings,
                check_id="declared_numeric_missing",
                severity=SEVERITY_BLOCK,
                surface=surface,
                path=path,
                field=field,
                problem=f"{field} is required for confident numeric display",
                action="block confident display until the producer emits the declared metric",
            )
        return None
    if not _is_number(value):
        _add_finding(
            findings,
            check_id="declared_numeric_not_number",
            severity=SEVERITY_BLOCK,
            surface=surface,
            path=path,
            field=field,
            problem=f"{field} is present but is not a numeric value",
            action="block confident display until the producer emits a finite number or demotes the row",
            evidence={"value_type": type(value).__name__},
        )
        return None
    number = float(value)
    if not math.isfinite(number):
        _add_finding(
            findings,
            check_id="non_finite_numeric_value",
            severity=SEVERITY_BLOCK,
            surface=surface,
            path=path,
            field=field,
            problem=f"{field} is NaN or Infinity",
            action="block confident display until the producer removes or demotes the non-finite value",
        )
        return None
    return number


def _check_ratio(
    findings: list[dict[str, Any]],
    *,
    surface: str,
    path: str,
    field: str,
    value: Any,
    min_value: float = 0.0,
    max_value: float = 1.0,
    required: bool = False,
) -> float | None:
    number = _check_declared_number(
        findings,
        surface=surface,
        path=path,
        field=field,
        value=value,
        required=required,
    )
    if number is None:
        return None
    if number < min_value or number > max_value:
        _add_finding(
            findings,
            check_id=f"{field}_bounds",
            severity=SEVERITY_BLOCK,
            surface=surface,
            path=path,
            field=field,
            problem=f"{field} must be in [{min_value}, {max_value}] for its declared representation",
            action="normalize 0..100 values to 0..1, correct the producer, or demote the row before confident display",
            evidence={"value": number, "min": min_value, "max": max_value},
        )
    return number


def _check_non_negative(
    findings: list[dict[str, Any]],
    *,
    surface: str,
    path: str,
    field: str,
    value: Any,
) -> float | None:
    number = _check_declared_number(findings, surface=surface, path=path, field=field, value=value)
    if number is not None and number < 0:
        _add_finding(
            findings,
            check_id=f"{field}_non_negative",
            severity=SEVERITY_BLOCK,
            surface=surface,
            path=path,
            field=field,
            problem=f"{field} must be non-negative",
            action="correct the producer or demote the row before confident display",
            evidence={"value": number},
        )
    return number


def _check_score_map(findings: list[dict[str, Any]], *, surface: str, path: str, score: Mapping[str, Any]) -> None:
    for field in ("interestingness", "confidence", "display_readiness"):
        if field in score:
            _check_ratio(findings, surface=surface, path=path, field=f"score.{field}", value=score.get(field))


def _check_prediction_event_board(findings: list[dict[str, Any]], rows: Sequence[Mapping[str, Any]]) -> None:
    surface = "latest_quant_presentation_mart.prediction_market_event_board"
    for index, row in enumerate(rows):
        path = f"prediction_market_event_board[{index}]"
        if "probability" in row:
            _check_ratio(findings, surface=surface, path=path, field="probability", value=row.get("probability"))
        if "probability_change" in row:
            _check_ratio(
                findings,
                surface=surface,
                path=path,
                field="probability_change",
                value=row.get("probability_change"),
                min_value=-1.0,
                max_value=1.0,
            )
        if "spread" in row:
            _check_ratio(findings, surface=surface, path=path, field="spread", value=row.get("spread"))
        if "volume" in row:
            _check_non_negative(findings, surface=surface, path=path, field="volume", value=row.get("volume"))


def _check_stockgrid_flow_board(findings: list[dict[str, Any]], rows: Sequence[Mapping[str, Any]]) -> None:
    surface = "latest_quant_presentation_mart.stockgrid_flow_board"
    tickers: list[str] = []
    for index, row in enumerate(rows):
        path = f"stockgrid_flow_board[{index}]"
        ticker = str(row.get("ticker") or "").strip()
        if ticker:
            tickers.append(ticker)
        flow = _check_declared_number(findings, surface=surface, path=path, field="flow", value=row.get("flow"))
        flow_usd = _check_declared_number(
            findings,
            surface=surface,
            path=path,
            field="flow_usd",
            value=row.get("flow_usd"),
        )
        for field in ("net_usd", "flow_score", "conviction", "signal_value", "win_rate"):
            if field in row:
                _check_declared_number(findings, surface=surface, path=path, field=field, value=row.get(field))

        if flow_usd is None and (flow is not None or _number(row.get("signal_value")) is not None):
            _add_finding(
                findings,
                check_id="stockgrid_flow_missing_raw_usd",
                severity=SEVERITY_DEMOTE,
                surface=surface,
                path=path,
                field="flow_usd",
                problem="Stockgrid row has flow signal but no raw USD flow",
                action="demote from primary flow panels until raw USD flow or an explicit non-flow signal contract is present",
                evidence={"ticker": ticker or None},
            )
            continue

        if flow_usd is not None:
            flow_unit = str(row.get("flow_unit") or "").strip()
            if flow_unit not in STOCKGRID_FLOW_UNITS:
                _add_finding(
                    findings,
                    check_id="stockgrid_flow_unit_missing",
                    severity=SEVERITY_BLOCK,
                    surface=surface,
                    path=path,
                    field="flow_unit",
                    problem="Stockgrid raw flow is visible without a controlled flow_unit",
                    action="declare flow_unit as usd or usd_millions before confident display",
                    evidence={"ticker": ticker or None, "flow_unit": flow_unit or None},
                )
            if not _has_source_refs(row):
                _add_finding(
                    findings,
                    check_id="source_lineage_missing",
                    severity=SEVERITY_BLOCK,
                    surface=surface,
                    path=path,
                    field="source_refs",
                    problem="Visible Stockgrid flow row lacks source_refs",
                    action="block confident display until source-column lineage points at the feed artifact row",
                    evidence={"ticker": ticker or None},
                )
            if flow is not None and flow_unit == "usd_millions":
                expected = flow * 1_000_000.0
                tolerance = max(500_000.0, abs(flow_usd) * 0.001)
                if abs(expected - flow_usd) > tolerance:
                    _add_finding(
                        findings,
                        check_id="stockgrid_flow_unit_scale_mismatch",
                        severity=SEVERITY_BLOCK,
                        surface=surface,
                        path=path,
                        field="flow_usd",
                        problem="Stockgrid compact flow and raw USD flow disagree beyond tolerance",
                        action="fix producer normalization or demote the row before confident display",
                        evidence={
                            "ticker": ticker or None,
                            "flow": flow,
                            "flow_unit": flow_unit,
                            "flow_usd": flow_usd,
                            "expected_flow_usd": expected,
                            "tolerance": tolerance,
                        },
                    )

    for ticker, count in Counter(tickers).items():
        if count > 1:
            _add_finding(
                findings,
                check_id="stockgrid_duplicate_ticker",
                severity=SEVERITY_BLOCK,
                surface=surface,
                path=f"stockgrid_flow_board[ticker={ticker}]",
                field="ticker",
                problem="Stockgrid flow board contains duplicate ticker rows",
                action="merge source rows by ticker or demote duplicates before confident display",
                evidence={"ticker": ticker, "count": count},
            )


def _check_features(findings: list[dict[str, Any]], rows: Sequence[Mapping[str, Any]]) -> None:
    surface = "latest_quant_presentation_mart.features"
    for index, row in enumerate(rows):
        metrics = _mapping(row.get("metrics"))
        family = str(row.get("feature_family") or "")
        path = f"features[{index}].metrics"
        if family == "event_market":
            if "probability" in metrics:
                _check_ratio(findings, surface=surface, path=path, field="probability", value=metrics.get("probability"))
            if "change" in metrics:
                _check_ratio(
                    findings,
                    surface=surface,
                    path=path,
                    field="change",
                    value=metrics.get("change"),
                    min_value=-1.0,
                    max_value=1.0,
                )
            if "spread" in metrics:
                _check_ratio(findings, surface=surface, path=path, field="spread", value=metrics.get("spread"))
            if "volume" in metrics:
                _check_non_negative(findings, surface=surface, path=path, field="volume", value=metrics.get("volume"))
        elif family == "stockgrid_flow":
            if "flow_usd" in metrics:
                _check_declared_number(findings, surface=surface, path=path, field="flow_usd", value=metrics.get("flow_usd"))
            if "flow_unit" not in metrics:
                _add_finding(
                    findings,
                    check_id="stockgrid_feature_flow_unit_missing",
                    severity=SEVERITY_BLOCK,
                    surface=surface,
                    path=path,
                    field="flow_unit",
                    problem="Stockgrid feature metrics lack flow_unit",
                    action="declare feature metric units before downstream display contracts consume the feature",
                )


def _check_ranked_observations(findings: list[dict[str, Any]], rows: Sequence[Mapping[str, Any]]) -> None:
    surface = "latest_quant_presentation_mart.ranked_observations"
    for index, row in enumerate(rows):
        path = f"ranked_observations[{index}]"
        score = row.get("score")
        if isinstance(score, Mapping):
            _check_score_map(findings, surface=surface, path=path, score=score)
        primary_metric = _mapping(row.get("primary_metric"))
        if _is_number(primary_metric.get("value")):
            _check_declared_number(
                findings,
                surface=surface,
                path=f"{path}.primary_metric",
                field="value",
                value=primary_metric.get("value"),
            )
        if row.get("display_state") == "ready" and not _has_source_refs(row):
            _add_finding(
                findings,
                check_id="source_lineage_missing",
                severity=SEVERITY_BLOCK,
                surface=surface,
                path=path,
                field="source_refs",
                problem="Ready ranked observation lacks source_refs",
                action="block confident display until the observation cites source artifacts",
            )


def _check_visual_plane_metric(
    findings: list[dict[str, Any]],
    *,
    plane_id: str,
    row_index: int,
    metric_id: str,
    unit: str,
    value: Any,
) -> None:
    surface = "human_market_cockpit.visual_planes"
    path = f"visual_planes[{plane_id}].rows[{row_index}].metrics"
    if metric_id in {"probability_change", "change"}:
        _check_ratio(
            findings,
            surface=surface,
            path=path,
            field=metric_id,
            value=value,
            min_value=-1.0,
            max_value=1.0,
        )
    elif unit in {"ratio", "probability"} or metric_id == "probability":
        _check_ratio(findings, surface=surface, path=path, field=metric_id, value=value)
    elif metric_id in {"volume", "flow_usd", "price"} or unit in {"usd_compact", "price"}:
        number = _check_declared_number(findings, surface=surface, path=path, field=metric_id, value=value)
        if metric_id in {"volume", "price"} and number is not None and number < 0:
            _add_finding(
                findings,
                check_id=f"{metric_id}_non_negative",
                severity=SEVERITY_BLOCK,
                surface=surface,
                path=path,
                field=metric_id,
                problem=f"{metric_id} must be non-negative in visible cockpit planes",
                action="correct the producer or demote the row before confident display",
                evidence={"value": number},
            )
    elif unit == "percent":
        number = _check_declared_number(findings, surface=surface, path=path, field=metric_id, value=value)
        if number is not None and abs(number) > 1000:
            _add_finding(
                findings,
                check_id="percent_display_bound",
                severity=SEVERITY_DEMOTE,
                surface=surface,
                path=path,
                field=metric_id,
                problem="Visible percent value is outside the display-safe bound",
                action="demote until the producer verifies the representation is percent points, not a ratio/scale mix",
                evidence={"value": number, "display_safe_abs_bound": 1000},
            )
    else:
        _check_declared_number(findings, surface=surface, path=path, field=metric_id, value=value)


def _check_human_market_cockpit(findings: list[dict[str, Any]], hmc: Mapping[str, Any]) -> None:
    for index, cell in enumerate(_records(_mapping(hmc.get("market_field")).get("cells"))):
        path = f"market_field.cells[{index}]"
        surface = "human_market_cockpit.market_field.cells"
        for field in ("value", "normalized", "direction", "metric_value", "confidence", "completeness"):
            if field in cell:
                number = _check_declared_number(findings, surface=surface, path=path, field=field, value=cell.get(field))
                if number is None:
                    continue
                if field == "normalized" and not (-1.0 <= number <= 1.0):
                    _add_finding(
                        findings,
                        check_id="normalized_bounds",
                        severity=SEVERITY_BLOCK,
                        surface=surface,
                        path=path,
                        field=field,
                        problem="normalized must be in [-1, 1]",
                        action="correct or demote the cockpit cell before confident display",
                        evidence={"value": number},
                    )
                if field in {"confidence", "completeness"} and not (0.0 <= number <= 1.0):
                    _add_finding(
                        findings,
                        check_id=f"{field}_bounds",
                        severity=SEVERITY_BLOCK,
                        surface=surface,
                        path=path,
                        field=field,
                        problem=f"{field} must be in [0, 1]",
                        action="correct or demote the cockpit cell before confident display",
                        evidence={"value": number},
                    )
                if field == "direction" and not (-1.0 <= number <= 1.0):
                    _add_finding(
                        findings,
                        check_id="direction_bounds",
                        severity=SEVERITY_BLOCK,
                        surface=surface,
                        path=path,
                        field=field,
                        problem="direction must be in [-1, 1]",
                        action="correct or demote the cockpit cell before confident display",
                        evidence={"value": number},
                    )
        if cell.get("metric_name") == "probability":
            _check_ratio(findings, surface=surface, path=path, field="metric_value", value=cell.get("metric_value"))

    for plane in _records(hmc.get("visual_planes")):
        plane_id = str(plane.get("id") or "unknown")
        specs = {
            str(spec.get("id") or ""): str(spec.get("unit") or "")
            for spec in _records(plane.get("metric_specs"))
            if spec.get("id")
        }
        for row_index, row in enumerate(_records(plane.get("rows"))):
            metrics = _mapping(row.get("metrics"))
            for metric_id, value in metrics.items():
                if value is None:
                    continue
                _check_visual_plane_metric(
                    findings,
                    plane_id=plane_id,
                    row_index=row_index,
                    metric_id=str(metric_id),
                    unit=specs.get(str(metric_id), ""),
                    value=value,
                )


def _summary(findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    severity_counts = Counter(str(row.get("severity") or SEVERITY_INFO) for row in findings)
    check_counts = Counter(str(row.get("check_id") or "unknown") for row in findings)
    blocking_count = sum(severity_counts.get(severity, 0) for severity in BLOCKING_SEVERITIES)
    demoted_count = severity_counts.get(SEVERITY_DEMOTE, 0)
    warning_count = severity_counts.get(SEVERITY_WARN, 0)
    if blocking_count:
        display_state = "blocked"
    elif demoted_count or warning_count:
        display_state = "degraded"
    else:
        display_state = "trusted"
    return {
        "display_state": display_state,
        "finding_count": len(findings),
        "blocking_count": blocking_count,
        "demoted_count": demoted_count,
        "warning_count": warning_count,
        "severity_counts": dict(sorted(severity_counts.items())),
        "check_counts": dict(sorted(check_counts.items())),
    }


def build_finance_numeric_assurance(
    *,
    quant_mart: Mapping[str, Any] | None = None,
    human_market_cockpit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checked_surfaces: list[str] = []
    quant_payload = _mapping(quant_mart)
    if quant_payload:
        checked_surfaces.extend(
            [
                "latest_quant_presentation_mart.ranked_observations",
                "latest_quant_presentation_mart.features",
                "latest_quant_presentation_mart.stockgrid_flow_board",
                "latest_quant_presentation_mart.prediction_market_event_board",
            ]
        )
        _check_ranked_observations(findings, _records(quant_payload.get("ranked_observations")))
        _check_features(findings, _records(quant_payload.get("features")))
        _check_stockgrid_flow_board(findings, _records(quant_payload.get("stockgrid_flow_board")))
        _check_prediction_event_board(findings, _records(quant_payload.get("prediction_market_event_board")))
    hmc_payload = _mapping(human_market_cockpit)
    if hmc_payload:
        checked_surfaces.extend(
            [
                "human_market_cockpit.market_field.cells",
                "human_market_cockpit.visual_planes",
            ]
        )
        _check_human_market_cockpit(findings, hmc_payload)

    summary = _summary(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "display_state": summary["display_state"],
        "summary": summary,
        "checked_surfaces": checked_surfaces,
        "contract": {
            "unit_declared": True,
            "scale_consistent": True,
            "source_lineage_required": True,
            "finite_numbers_only": True,
            "probability_representation": "ratio_0_to_1",
            "confidence_representation": "ratio_0_to_1",
            "stockgrid_entity_granularity": "one_row_per_ticker",
        },
        "findings": findings,
    }


def blocking_numeric_contract_errors(quant_mart: Mapping[str, Any]) -> list[str]:
    receipt = build_finance_numeric_assurance(quant_mart=quant_mart)
    errors: list[str] = []
    for finding in receipt.get("findings") or []:
        if not isinstance(finding, Mapping) or finding.get("severity") not in BLOCKING_SEVERITIES:
            continue
        field = f".{finding.get('field')}" if finding.get("field") else ""
        errors.append(
            "finance_numeric_assurance: "
            f"{finding.get('check_id')} at {finding.get('path')}{field}: "
            f"{finding.get('problem')}"
        )
    return errors


def data_quality_rows_from_numeric_assurance(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for finding in receipt.get("findings") or []:
        if not isinstance(finding, Mapping):
            continue
        if finding.get("severity") not in DISPLAY_DEMOTION_SEVERITIES:
            continue
        groups[str(finding.get("check_id") or "numeric_assurance")].append(finding)
    rows: list[dict[str, Any]] = []
    for check_id, findings in sorted(groups.items()):
        blocking = any(row.get("severity") == SEVERITY_BLOCK for row in findings)
        example = findings[0]
        rows.append(
            {
                "lane": f"finance_numeric_{check_id}",
                "state": "blocked" if blocking else "incomplete",
                "rows": len(findings),
                "problem": str(example.get("problem") or check_id),
                "action": str(example.get("action") or "demote or correct before confident display"),
            }
        )
    return rows
