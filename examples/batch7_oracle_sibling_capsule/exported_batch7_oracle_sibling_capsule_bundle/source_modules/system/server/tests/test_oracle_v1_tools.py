"""
[PURPOSE]
- Teleology: Verify Oracle v1 tool payloads for subject indexing, subject snapshots, and subject-versus-truth diff tools across the server backend contract surface.
- Mechanism: Seed compact subject and truth artifacts under `tmp_path`, invoke the Oracle tool entrypoints directly, and assert on the emitted success envelopes and ranked payload fields.

[INTERFACE]
- Tests: `subject_index.run`, `subject_snapshot.run`, `truth_diff_equity.run`, and `truth_diff_macro.run`.

[FLOW]
- Write compact subject and truth artifacts plus runtime context fixtures.
- Call the tool entrypoints with runtime config pointing at those fixtures.
- Assert on stable payload fields for admissible evidence, provenance metadata, reconciliation rows, and macro diff summaries.

[DEPENDENCIES]
- tools.oracle.subject_index: Subject-side grounding map builder.
- tools.oracle.subject_snapshot: Subject artifact re-exposure tool.
- tools.oracle.truth_diff_equity and tools.oracle.truth_diff_macro: Oracle truth-diff emitters.

[CONSTRAINTS]
- Tests are read/write isolated to `tmp_path` fixture directories.
- Assertions target stable contract fields instead of incidental ordering beyond the documented ranking behavior.
- When-needed: Open when an Oracle v1 tool regression touches subject grounding maps, snapshot provenance, or truth-diff payload shape.
- Escalates-to: tools/oracle/subject_index.py::run; tools/oracle/subject_snapshot.py::run; tools/oracle/truth_diff_equity.py::run; tools/oracle/truth_diff_macro.py::run
- Navigation-group: server_backend
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.oracle import subject_index, subject_snapshot, truth_diff_equity, truth_diff_macro


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _feed(columns: list[str], rows: list[list[object]], *, as_of: str = "2026-03-03T14:00:00+00:00") -> dict:
    return {
        "metadata": {"as_of": as_of},
        "data": {
            "topic": {
                "row": {
                    "columns": columns,
                    "rows": rows,
                }
            }
        },
    }


def _lab_director_payload() -> dict:
    return {
        "metadata": {
            "as_of": "2026-03-03T14:00:00+00:00",
            "target_time_iso": "2026-03-03T21:00:00+00:00",
            "horizon_label": "Custom target",
        },
        "data": {
            "evidence_dictionary": [
                {"ref_id": "[1]", "ledger_id": "S_CAFEBABE", "subject": "XOM", "signal_summary": "Stock support."},
                {"ref_id": "[2]", "ledger_id": "E_DEADBEEF", "subject": "XLE", "signal_summary": "ETF support."},
            ],
            "epicentre_thesis": "word " * 160,
            "trade_rationale": "word " * 120,
            "predictions_t": [
                {
                    "target_id": "XOM",
                    "direction": "UP",
                    "snapshot_price": 100.0,
                    "target_price": 110.0,
                    "invalidation": "Lose trend support.",
                }
            ],
        },
    }


def _lab_decide_payload() -> dict:
    return {
        "metadata": {"as_of": "2026-03-03T14:00:00+00:00"},
        "data": {
            "evidence_dictionary": [
                {"ref_id": "[1]", "ledger_id": "S_CAFEBABE", "subject": "XOM", "signal_summary": "Stock support."},
            ],
            "epicentre_thesis": "word " * 160,
            "dominant_evidence_track": "FLOW_LED",
            "pre_pricing_assessment": "Most headline continuation was already visible in flow.",
        },
    }


def test_oracle_subject_index_builds_subject_grounding_map(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    lab_director = _lab_director_payload()
    lab_director["data"]["evidence_dictionary"].append(
        {
            "ref_id": "[3]",
            "ledger_id": "M_FEEDBEEF",
            "subject": "TLT",
            "signal_summary": "Macro context only; no admissible T-n ETF grounding.",
        }
    )
    _write_json(
        subject_run / "runtime_context.json",
        {
            "as_of": "2026-03-03T14:00:00+00:00",
            "temporal_contract": {"target_time_iso": "2026-03-03T21:00:00+00:00"},
        },
    )
    _write_json(subject_run / "artifacts" / "lab_decide.json", _lab_decide_payload())
    _write_json(subject_run / "artifacts" / "lab_director.json", lab_director)
    _write_json(
        subject_run / "artifacts" / "lab_cross_corr_v2.json",
        {
            "metadata": {},
            "data": {
                "valid_prediction_targets": ["XOM", "XLE", "TLT"],
            },
        },
    )
    _write_json(
        subject_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["XOM", "100.0"]]),
    )
    _write_json(
        subject_run / "artifacts" / "global_etf_feed.json",
        _feed(["Ticker", "Price"], [["XLE", "90.0"]]),
    )

    result = subject_index.run({"runtime": {"oracle_subject_run_dir": str(subject_run)}})
    data = result["data"]

    assert data["valid_prediction_targets"] == ["TLT", "XLE", "XOM"]
    assert "S_CAFEBABE" in data["eligible_ledger_ids"]
    assert "E_DEADBEEF" in data["eligible_ledger_ids"]
    assert data["subject_equity_price_map"]["XOM"] == 100.0
    assert data["subject_equity_price_map"]["XLE"] == 90.0
    assert data["evidence_by_subject"]["XOM"][0]["ledger_id"] == "S_CAFEBABE"
    assert data["admissible_evidence_by_subject"]["XOM"][0]["ledger_id"] == "S_CAFEBABE"
    assert data["admissible_evidence_by_subject"]["XLE"][0]["ledger_id"] == "E_DEADBEEF"
    assert data["contextual_evidence_by_subject"]["TLT"][0]["ledger_id"] == "M_FEEDBEEF"
    assert data["missing_admissible_support_targets"] == ["TLT"]


def test_oracle_subject_snapshot_loads_subject_artifact(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    _write_json(subject_run / "artifacts" / "lab_director.json", _lab_director_payload())

    result = subject_snapshot.run(
        {
            "artifact_id": "lab_director",
            "runtime": {"oracle_subject_run_dir": str(subject_run)},
        }
    )

    assert result["metadata"]["tool"] == "oracle_subject_snapshot"
    assert result["metadata"]["source_artifact_id"] == "lab_director"
    assert result["metadata"]["subject_run_id"] == "subject"
    assert result["data"]["predictions_t"][0]["target_id"] == "XOM"


def test_oracle_truth_diff_equity_emits_prediction_reconciliation(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(subject_run / "artifacts" / "lab_director.json", _lab_director_payload())
    _write_json(
        subject_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["XOM", "100.0"]]),
    )
    _write_json(
        subject_run / "artifacts" / "global_etf_feed.json",
        _feed(["Ticker", "Price"], [["XLE", "90.0"]]),
    )
    _write_json(
        truth_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["XOM", "105.0"]], as_of="2026-03-03T22:00:00+00:00"),
    )
    _write_json(
        truth_run / "artifacts" / "global_etf_feed.json",
        _feed(["Ticker", "Price"], [["XLE", "93.0"]], as_of="2026-03-03T22:00:00+00:00"),
    )
    _write_json(subject_run / "runtime_context.json", {"as_of": "2026-03-03T14:00:00+00:00"})
    _write_json(truth_run / "runtime_context.json", {"as_of": "2026-03-03T22:00:00+00:00"})

    result = truth_diff_equity.run(
        {
            "runtime": {
                "oracle_subject_run_dir": str(subject_run),
                "oracle_truth_run_dir": str(truth_run),
            }
        }
    )
    data = result["data"]

    assert data["status"] == "AVAILABLE"
    assert data["subject_run_id"] == "subject"
    assert data["truth_run_id"] == "truth"
    assert "macro_rows" not in data
    contract_row = data["rows"][0]
    assert contract_row["target_id"] == "XOM"
    assert contract_row["asset_class"] == "STOCK"
    assert contract_row["prediction_direction"] == "UP"
    assert contract_row["subject_snapshot_price"] == 100.0
    assert contract_row["predicted_target_price"] == 110.0
    assert contract_row["realized_truth_price"] == 105.0
    assert contract_row["directional_correct"] is True
    assert contract_row["rank"] == 1
    assert data["summary"]["row_count"] == 1
    assert data["summary"]["directionally_correct_count"] == 1
    assert data["summary"]["directionally_incorrect_count"] == 0
    assert data["summary"]["largest_absolute_miss_target"] == "XOM"
    assert data["summary"]["largest_percent_miss_target"] == "XOM"
    assert data["feed_health"]["status"] == "READY"
    assert data["feed_health"]["prediction_target_count"] == 1
    assert data["feed_health"]["comparable_prediction_targets"] == ["XOM"]
    assert data["feed_health"]["missing_truth_price_targets"] == []


def test_oracle_truth_diff_equity_surfaces_feed_health_gaps(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(subject_run / "artifacts" / "lab_director.json", _lab_director_payload())
    _write_json(
        subject_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["XOM", "100.0"]]),
    )
    _write_json(
        truth_run / "artifacts" / "global_stock_feed.json",
        _feed(["Ticker", "Price"], [["CVX", "160.0"]], as_of="2026-03-03T22:00:00+00:00"),
    )

    result = truth_diff_equity.run(
        {
            "runtime": {
                "oracle_subject_run_dir": str(subject_run),
                "oracle_truth_run_dir": str(truth_run),
            }
        }
    )
    data = result["data"]
    feed_health = data["feed_health"]

    assert data["rows"] == []
    assert feed_health["status"] == "BLOCKED"
    assert feed_health["prediction_target_count"] == 1
    assert feed_health["comparable_prediction_targets"] == []
    assert feed_health["missing_subject_price_targets"] == []
    assert feed_health["missing_truth_price_targets"] == ["XOM"]
    assert "missing truth prices for targets: XOM" in feed_health["diagnostics"]
    assert result["metadata"]["diagnostics"]["warnings"] == feed_health["diagnostics"]


def test_oracle_truth_diff_macro_emits_changed_series_without_as_of_equality(tmp_path: Path) -> None:
    subject_run = tmp_path / "subject"
    truth_run = tmp_path / "truth"
    _write_json(
        subject_run / "artifacts" / "global_macro_feed.json",
        _feed(
            ["slug", "value"],
            [["US10Y", "4.10"], ["DXY", "104.0"]],
            as_of="2026-03-03T14:00:00+00:00",
        ),
    )
    _write_json(
        truth_run / "artifacts" / "global_macro_feed.json",
        _feed(
            ["slug", "value"],
            [["US10Y", "4.35"], ["DXY", "104.0"]],
            as_of="2026-03-03T22:00:00+00:00",
        ),
    )

    result = truth_diff_macro.run(
        {
            "runtime": {
                "oracle_subject_run_dir": str(subject_run),
                "oracle_truth_run_dir": str(truth_run),
            }
        }
    )
    data = result["data"]

    assert data["subject_as_of"] == "2026-03-03T14:00:00+00:00"
    assert data["truth_as_of"] == "2026-03-03T22:00:00+00:00"
    assert data["changed_series"][0]["series_id"] == "US10Y"
    assert data["changed_series"][0]["changes"][0]["field"] == "value"
