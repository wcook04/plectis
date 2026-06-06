"""
[PURPOSE]
- Teleology: Materialize the legacy shadow envelope from miner, spine, and prediction node artifacts so downstream review surfaces can inspect parse coverage and hard-failure reasons without replaying node runs.
- Mechanism: Load required artifact envelopes, parse miner/spine/prediction payloads into normalized structures, accumulate parse stats, and return a status-marked shadow result.

[INTERFACE]
- Exports: load_env, run.
- Reads: `<run_dir>/artifacts/*.json` envelopes selected by REQUIRED_NODE_IDS.
- Writes: None.

[FLOW]
- Orders: run() resolves artifact paths and node maps -> load_env() reads each envelope -> parser passes normalize miner/spine/prediction payloads -> run() emits metadata, data, and strict-failure state.
- When-needed: Open when a lab run needs its shadow parse layer rebuilt or debugged from artifact JSON instead of re-running the original node graph.
- Escalates-to: tools/shadow/shadow.py::run; tools/shadow/shadow.py::load_env
- Navigation-group: python_misc_runtime

[DEPENDENCIES]
- json: Load artifact envelopes and serialize raw prediction blocks for diagnostics.
- re: Parse spine edges and prediction blocks.
- pathlib.Path: Resolve run and artifact paths.

[CONSTRAINTS]
- Guarantee: Strict-mode failure comes only from missing required artifacts or zero parsed_ok coverage in passes that are actually present.
- Non-goal: This module does not execute lab nodes or repair malformed artifacts.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple



_DEFAULT_MINER_NODE_TO_LANE = {
    "lab_miner_v2_stock": "STOCK",
    "lab_miner_v2_macro": "MACRO",
    "lab_miner_v2_news": "NEWS",
    "lab_miner_v2_poly": "POLYMARKET",
    "lab_miner_v2_calc": "CALCULATOR",
    "lab_miner_v2_stockgrid": "STOCKGRID",
}

_DEFAULT_SPINE_NODE_ID = "lab_decide"

_DEFAULT_PREDICT_NODE_TO_LANE = {
    "lab_director": "STOCK",
}

# Backward-compat aliases (used by internal parse functions)
MINER_NODE_TO_LANE = _DEFAULT_MINER_NODE_TO_LANE
SPINE_NODE_ID = _DEFAULT_SPINE_NODE_ID
PREDICT_NODE_TO_LANE = _DEFAULT_PREDICT_NODE_TO_LANE

REQUIRED_NODE_IDS = tuple(
    list(MINER_NODE_TO_LANE.keys()) + [SPINE_NODE_ID] + list(PREDICT_NODE_TO_LANE.keys())
)

OPERATOR_TOKENS = ("<<>>", "<< >>", "x--x", "-->", ">|", ">>", "===", "...")
_OPERATOR_MAP = {"<< >>": "<<>>"}

TUPLE_LINE_RE = re.compile(r"^\s*\{[^{}]*\}\s*$")
SLUG_RE = re.compile(r"\[H:([a-z0-9_]+)\]")
VERDICT_RE = re.compile(r"(?:\bCONFIRMED\b|\bREVISED\b|x--x)")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_run_paths(run_dir: str) -> Tuple[Path, Path]:
    run_path = Path(run_dir)
    if run_path.name == "artifacts":
        return run_path.parent, run_path
    return run_path, run_path / "artifacts"


def _parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _parse_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        try:
            parsed = int(value.strip())
            return parsed if parsed > 0 else None
        except ValueError:
            return None
    return None


def _merge_failures(into: Dict[str, int], new_items: Dict[str, int]) -> None:
    for key, count in new_items.items():
        into[key] = into.get(key, 0) + count


def _append_example(
    examples: List[Dict[str, Any]],
    emit_examples: bool,
    err_type: str,
    raw_line: str,
    extra: Optional[Dict[str, Any]] = None,
    limit: int = 5,
) -> None:
    if not emit_examples or len(examples) >= limit:
        return
    payload: Dict[str, Any] = {"err_type": err_type, "raw_line": raw_line}
    if extra:
        payload.update(extra)
    examples.append(payload)


def _operator_regex_pattern() -> str:
    escaped = [re.escape(token) for token in sorted(OPERATOR_TOKENS, key=len, reverse=True)]
    return "(?:" + "|".join(escaped) + ")"


OPERATOR_RE_PART = _operator_regex_pattern()
EDGE_RE = re.compile(
    rf"^\s*(\{{[^{{}}]+\}})\s*({OPERATOR_RE_PART})\s*(\[[^\[\]]+\])\s*({OPERATOR_RE_PART})\s*(\{{[^{{}}]+\}})\s*$"
)
PREDICTION_RE = re.compile(
    rf"^\{{T:(.*?)\}}\s*({OPERATOR_RE_PART})\s*\[L:(.*?)\]\s*({OPERATOR_RE_PART})\s*\{{T\+1:(.*?)\}}$"
)


def _normalize_operator(op: str) -> str:
    return _OPERATOR_MAP.get(op, op)


def _line_looks_ignorable(line: str) -> bool:
    if not line:
        return True
    if line.startswith("```"):
        return True
    if "{" not in line and "}" not in line:
        return True
    return False


def load_env(artifacts_dir: Path, node_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[str]]:
    """[ACTION]
    - Teleology: Read one node artifact envelope and normalize the file/schema failure state before parse passes consume it.
    - Mechanism: Resolve `<artifacts_dir>/<node_id>.json`, JSON-load it, validate the envelope shape, note id mismatch warnings, and return `(env, error, warnings)`.
    - Reads: artifacts_dir / f"{node_id}.json".
    - Guarantee: Returns warnings for id mismatches, an error dict for missing or invalid envelopes, and a populated env mapping only when the `data` field exists.
    - Fails: None.
    - When-needed: Open when shadow output shows `missing_artifacts` or `artifact_issues` and you need the exact envelope gate.
    - Escalates-to: tools/shadow/shadow.py::run
    """
    path = artifacts_dir / f"{node_id}.json"
    warnings: List[str] = []

    if not path.exists():
        return None, {"code": "missing_file", "detail": str(path)}, warnings

    try:
        env = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, {"code": "json_parse_error", "detail": str(exc)}, warnings

    if not isinstance(env, dict):
        return None, {"code": "invalid_envelope", "detail": "artifact is not a JSON object"}, warnings

    env_id = env.get("id")
    if env_id is not None and env_id != node_id:
        warnings.append(f"id_mismatch:{env_id}")

    if "data" not in env:
        return None, {"code": "missing_data_field", "detail": "envelope missing data"}, warnings

    return env, None, warnings


def _init_miner_stats() -> Dict[str, Any]:
    return {
        "total_lines": 0,
        "ignored_lines": 0,
        "candidates": 0,
        "parsed_ok": 0,
        "failures": 0,
        "failures_by_type": {},
        "examples_failed": [],
    }


def _parse_miner_text(
    lane: str,
    data: Any,
    max_lines_per_artifact: Optional[int],
    emit_examples: bool,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    stats = _init_miner_stats()

    if not isinstance(data, str):
        stats["failures"] = 1
        stats["failures_by_type"]["unexpected_type"] = 1
        _append_example(
            stats["examples_failed"],
            emit_examples,
            "unexpected_type",
            f"<NON_STRING_DATA:{type(data).__name__}>",
        )
        records.append(
            {
                "lane": lane,
                "subject": None,
                "metric": None,
                "context": None,
                "raw_line": f"<NON_STRING_DATA:{type(data).__name__}>",
                "parse_ok": False,
                "err_type": "unexpected_type",
                "fields_count": None,
            }
        )
        return records, stats

    text = data.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if max_lines_per_artifact is not None:
        lines = lines[:max_lines_per_artifact]

    stats["total_lines"] = len(lines)

    for raw in lines:
        line = raw.strip()

        if _line_looks_ignorable(line):
            stats["ignored_lines"] += 1
            continue

        stats["candidates"] += 1

        if not TUPLE_LINE_RE.match(line):
            stats["failures"] += 1
            stats["failures_by_type"]["brace_grammar"] = stats["failures_by_type"].get("brace_grammar", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "brace_grammar", raw)
            records.append(
                {
                    "lane": lane,
                    "subject": None,
                    "metric": None,
                    "context": None,
                    "raw_line": raw,
                    "parse_ok": False,
                    "err_type": "brace_grammar",
                    "fields_count": None,
                }
            )
            continue

        inside = line[1:-1]
        parts = [part.strip() for part in inside.split(",")]

        if len(parts) != 3:
            stats["failures"] += 1
            stats["failures_by_type"]["comma_arity"] = stats["failures_by_type"].get("comma_arity", 0) + 1
            _append_example(
                stats["examples_failed"],
                emit_examples,
                "comma_arity",
                raw,
                {"fields_count": len(parts)},
            )
            records.append(
                {
                    "lane": lane,
                    "subject": None,
                    "metric": None,
                    "context": None,
                    "raw_line": raw,
                    "parse_ok": False,
                    "err_type": "comma_arity",
                    "fields_count": len(parts),
                }
            )
            continue

        if any(not part for part in parts):
            stats["failures"] += 1
            stats["failures_by_type"]["empty_field"] = stats["failures_by_type"].get("empty_field", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "empty_field", raw)
            records.append(
                {
                    "lane": lane,
                    "subject": None,
                    "metric": None,
                    "context": None,
                    "raw_line": raw,
                    "parse_ok": False,
                    "err_type": "empty_field",
                    "fields_count": 3,
                }
            )
            continue

        stats["parsed_ok"] += 1
        records.append(
            {
                "lane": lane,
                "subject": parts[0],
                "metric": parts[1],
                "context": parts[2],
                "raw_line": line,
                "parse_ok": True,
                "err_type": None,
                "fields_count": 3,
            }
        )

    return records, stats


def _parse_miner_pass(
    env_by_id: Dict[str, Dict[str, Any]],
    max_lines_per_artifact: Optional[int],
    emit_examples: bool,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    shadow_miners: Dict[str, List[Dict[str, Any]]] = {lane: [] for lane in MINER_NODE_TO_LANE.values()}
    global_stats: Dict[str, Any] = _init_miner_stats()
    global_stats["per_lane"] = {}

    for node_id, lane in MINER_NODE_TO_LANE.items():
        env = env_by_id.get(node_id)
        if env is None:
            global_stats["per_lane"][lane] = _init_miner_stats()
            continue

        records, lane_stats = _parse_miner_text(
            lane=lane,
            data=env.get("data"),
            max_lines_per_artifact=max_lines_per_artifact,
            emit_examples=emit_examples,
        )

        shadow_miners[lane] = records
        global_stats["per_lane"][lane] = lane_stats
        global_stats["total_lines"] += lane_stats["total_lines"]
        global_stats["ignored_lines"] += lane_stats["ignored_lines"]
        global_stats["candidates"] += lane_stats["candidates"]
        global_stats["parsed_ok"] += lane_stats["parsed_ok"]
        global_stats["failures"] += lane_stats["failures"]
        _merge_failures(global_stats["failures_by_type"], lane_stats["failures_by_type"])

        for example in lane_stats["examples_failed"]:
            _append_example(
                global_stats["examples_failed"],
                emit_examples,
                example["err_type"],
                example["raw_line"],
                {"lane": lane},
            )

    return shadow_miners, global_stats


def _find_verdict(current_line: str, next_line: Optional[str]) -> Optional[str]:
    same = VERDICT_RE.search(current_line)
    if same:
        return same.group(0)
    if next_line:
        looked = VERDICT_RE.search(next_line)
        if looked:
            return looked.group(0)
    return None


def _line_has_operator(line: str) -> bool:
    return any(token in line for token in OPERATOR_TOKENS)


def _parse_spine_pass(
    env_by_id: Dict[str, Dict[str, Any]],
    max_lines_per_artifact: Optional[int],
    emit_examples: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    shadow_spine: Dict[str, Any] = {"hypotheses": {}, "edges": []}
    stats: Dict[str, Any] = {
        "total_lines": 0,
        "hypotheses_found": 0,
        "hypotheses_unknown": 0,
        "adjudication_missing": 0,
        "edges_found": 0,
        "edge_failures": 0,
        "parsed_ok": 0,
        "failures_by_type": {},
        "examples_failed": [],
    }

    env = env_by_id.get(SPINE_NODE_ID)
    if env is None:
        return shadow_spine, stats

    data = env.get("data")
    if not isinstance(data, str):
        stats["failures_by_type"]["unexpected_type"] = 1
        stats["edge_failures"] = 1
        _append_example(
            stats["examples_failed"],
            emit_examples,
            "unexpected_type",
            f"<NON_STRING_DATA:{type(data).__name__}>",
        )
        return shadow_spine, stats

    text = data.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if max_lines_per_artifact is not None:
        lines = lines[:max_lines_per_artifact]
    stats["total_lines"] = len(lines)

    hypotheses: Dict[str, str] = {}

    for idx, line in enumerate(lines):
        if "[H:" not in line:
            continue
        slugs = SLUG_RE.findall(line)
        if not slugs:
            continue
        lookahead = lines[idx + 1] if idx + 1 < len(lines) else None
        for slug in slugs:
            verdict = _find_verdict(line, lookahead)
            if verdict is None:
                verdict = "UNKNOWN"
                stats["adjudication_missing"] += 1
                stats["failures_by_type"]["adjudication_missing"] = (
                    stats["failures_by_type"].get("adjudication_missing", 0) + 1
                )
                _append_example(
                    stats["examples_failed"],
                    emit_examples,
                    "adjudication_missing",
                    line,
                    {"slug": slug},
                )
            old = hypotheses.get(slug)
            if old is None or (old == "UNKNOWN" and verdict != "UNKNOWN"):
                hypotheses[slug] = verdict

    edges: List[Dict[str, Any]] = []
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if "{" not in trimmed or "}" not in trimmed:
            continue
        if not _line_has_operator(trimmed):
            continue

        match = EDGE_RE.match(trimmed)
        if not match:
            stats["edge_failures"] += 1
            stats["failures_by_type"]["edge_regex_miss"] = stats["failures_by_type"].get("edge_regex_miss", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "edge_regex_miss", line)
            continue

        x, op1, logic, op2, z = match.groups()
        edges.append(
            {
                "x": x,
                "op1": _normalize_operator(op1),
                "logic": logic,
                "op2": _normalize_operator(op2),
                "z": z,
                "raw_line": line,
                "parse_ok": True,
            }
        )
        stats["edges_found"] += 1

    stats["hypotheses_found"] = len(hypotheses)
    stats["hypotheses_unknown"] = sum(1 for verdict in hypotheses.values() if verdict == "UNKNOWN")
    known_hypotheses = stats["hypotheses_found"] - stats["hypotheses_unknown"]
    stats["parsed_ok"] = max(0, known_hypotheses) + stats["edges_found"]

    shadow_spine["hypotheses"] = hypotheses
    shadow_spine["edges"] = edges
    return shadow_spine, stats


def _init_prediction_stats() -> Dict[str, Any]:
    return {
        "blocks_total": 0,
        "parsed_ok": 0,
        "failures": 0,
        "failures_by_type": {},
        "examples_failed": [],
    }


def _parse_prediction_text(
    lane: str,
    data: Any,
    max_lines_per_artifact: Optional[int],
    emit_examples: bool,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    stats = _init_prediction_stats()

    if isinstance(data, dict):
        predictions_t = data.get("predictions_t")
        if not isinstance(predictions_t, list):
            stats["failures"] = 1
            stats["failures_by_type"]["missing_predictions_t"] = 1
            _append_example(
                stats["examples_failed"],
                emit_examples,
                "missing_predictions_t",
                "<CP2_DATA_WITHOUT_PREDICTIONS_T>",
            )
            records.append(
                {
                    "lane": lane,
                    "current_state": None,
                    "op1": None,
                    "logic_bridge": None,
                    "op2": None,
                    "projected_state": None,
                    "hypothesis_refs": [],
                    "raw_block": "<CP2_DATA_WITHOUT_PREDICTIONS_T>",
                    "parse_ok": False,
                    "err_type": "missing_predictions_t",
                }
            )
            return records, stats

        stats["blocks_total"] = len(predictions_t)
        for prediction in predictions_t:
            if not isinstance(prediction, dict):
                stats["failures"] += 1
                stats["failures_by_type"]["invalid_prediction_type"] = (
                    stats["failures_by_type"].get("invalid_prediction_type", 0) + 1
                )
                _append_example(
                    stats["examples_failed"],
                    emit_examples,
                    "invalid_prediction_type",
                    f"<NON_OBJECT_PREDICTION:{type(prediction).__name__}>",
                )
                records.append(
                    {
                        "lane": lane,
                        "current_state": None,
                        "op1": None,
                        "logic_bridge": None,
                        "op2": None,
                        "projected_state": None,
                        "hypothesis_refs": [],
                        "raw_block": f"<NON_OBJECT_PREDICTION:{type(prediction).__name__}>",
                        "parse_ok": False,
                        "err_type": "invalid_prediction_type",
                    }
                )
                continue

            target_id = prediction.get("target_id")
            if not isinstance(target_id, str) or not target_id.strip():
                stats["failures"] += 1
                stats["failures_by_type"]["missing_target_id"] = (
                    stats["failures_by_type"].get("missing_target_id", 0) + 1
                )
                raw_prediction = json.dumps(prediction, ensure_ascii=False)
                _append_example(
                    stats["examples_failed"],
                    emit_examples,
                    "missing_target_id",
                    raw_prediction,
                )
                records.append(
                    {
                        "lane": lane,
                        "current_state": None,
                        "op1": None,
                        "logic_bridge": None,
                        "op2": None,
                        "projected_state": None,
                        "hypothesis_refs": [],
                        "raw_block": raw_prediction,
                        "parse_ok": False,
                        "err_type": "missing_target_id",
                    }
                )
                continue

            direction = prediction.get("direction")
            direction_text = str(direction).strip() if direction is not None else "UNKNOWN"
            raw_prediction = json.dumps(prediction, ensure_ascii=False)
            stats["parsed_ok"] += 1
            records.append(
                {
                    "lane": lane,
                    "current_state": target_id.strip(),
                    "op1": "->",
                    "logic_bridge": "CP2 prediction",
                    "op2": "->",
                    "projected_state": direction_text or "UNKNOWN",
                    "hypothesis_refs": [],
                    "raw_block": raw_prediction,
                    "parse_ok": True,
                    "err_type": None,
                }
            )

        return records, stats

    if not isinstance(data, str):
        stats["failures"] = 1
        stats["failures_by_type"]["unexpected_type"] = 1
        _append_example(
            stats["examples_failed"],
            emit_examples,
            "unexpected_type",
            f"<NON_STRING_DATA:{type(data).__name__}>",
        )
        records.append(
            {
                "lane": lane,
                "current_state": None,
                "op1": None,
                "logic_bridge": None,
                "op2": None,
                "projected_state": None,
                "hypothesis_refs": [],
                "raw_block": f"<NON_STRING_DATA:{type(data).__name__}>",
                "parse_ok": False,
                "err_type": "unexpected_type",
            }
        )
        return records, stats

    text = data.replace("\r\n", "\n").replace("\r", "\n")
    if max_lines_per_artifact is not None:
        text = "\n".join(text.split("\n")[:max_lines_per_artifact])

    raw_blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    normalized_blocks = [re.sub(r"\s+", " ", block).strip() for block in raw_blocks]

    stats["blocks_total"] = len(normalized_blocks)

    for raw_block, block in zip(raw_blocks, normalized_blocks):
        t_pos = block.find("{T:")
        l_pos = block.find("[L:")
        t1_pos = block.find("{T+1:")

        if t_pos == -1 or l_pos == -1 or t1_pos == -1:
            stats["failures"] += 1
            stats["failures_by_type"]["missing_anchor"] = stats["failures_by_type"].get("missing_anchor", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "missing_anchor", raw_block)
            records.append(
                {
                    "lane": lane,
                    "current_state": None,
                    "op1": None,
                    "logic_bridge": None,
                    "op2": None,
                    "projected_state": None,
                    "hypothesis_refs": [],
                    "raw_block": raw_block,
                    "parse_ok": False,
                    "err_type": "missing_anchor",
                }
            )
            continue

        if not (t_pos < l_pos < t1_pos):
            stats["failures"] += 1
            stats["failures_by_type"]["anchor_order"] = stats["failures_by_type"].get("anchor_order", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "anchor_order", raw_block)
            records.append(
                {
                    "lane": lane,
                    "current_state": None,
                    "op1": None,
                    "logic_bridge": None,
                    "op2": None,
                    "projected_state": None,
                    "hypothesis_refs": [],
                    "raw_block": raw_block,
                    "parse_ok": False,
                    "err_type": "anchor_order",
                }
            )
            continue

        match = PREDICTION_RE.match(block)
        if not match:
            stats["failures"] += 1
            stats["failures_by_type"]["regex_miss"] = stats["failures_by_type"].get("regex_miss", 0) + 1
            _append_example(stats["examples_failed"], emit_examples, "regex_miss", raw_block)
            records.append(
                {
                    "lane": lane,
                    "current_state": None,
                    "op1": None,
                    "logic_bridge": None,
                    "op2": None,
                    "projected_state": None,
                    "hypothesis_refs": [],
                    "raw_block": raw_block,
                    "parse_ok": False,
                    "err_type": "regex_miss",
                }
            )
            continue

        current_state, op1, logic_bridge, op2, projected_state = match.groups()
        hypothesis_refs = SLUG_RE.findall(logic_bridge)

        stats["parsed_ok"] += 1
        records.append(
            {
                "lane": lane,
                "current_state": current_state.strip(),
                "op1": _normalize_operator(op1),
                "logic_bridge": logic_bridge.strip(),
                "op2": _normalize_operator(op2),
                "projected_state": projected_state.strip(),
                "hypothesis_refs": hypothesis_refs,
                "raw_block": raw_block,
                "parse_ok": True,
                "err_type": None,
            }
        )

    return records, stats


def _parse_prediction_pass(
    env_by_id: Dict[str, Dict[str, Any]],
    max_lines_per_artifact: Optional[int],
    emit_examples: bool,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    shadow_predictions: Dict[str, List[Dict[str, Any]]] = {lane: [] for lane in PREDICT_NODE_TO_LANE.values()}
    global_stats: Dict[str, Any] = _init_prediction_stats()
    global_stats["per_lane"] = {}

    for node_id, lane in PREDICT_NODE_TO_LANE.items():
        env = env_by_id.get(node_id)
        if env is None:
            global_stats["per_lane"][lane] = _init_prediction_stats()
            continue

        records, lane_stats = _parse_prediction_text(
            lane=lane,
            data=env.get("data"),
            max_lines_per_artifact=max_lines_per_artifact,
            emit_examples=emit_examples,
        )

        shadow_predictions[lane] = records
        global_stats["per_lane"][lane] = lane_stats
        global_stats["blocks_total"] += lane_stats["blocks_total"]
        global_stats["parsed_ok"] += lane_stats["parsed_ok"]
        global_stats["failures"] += lane_stats["failures"]
        _merge_failures(global_stats["failures_by_type"], lane_stats["failures_by_type"])

        for example in lane_stats["examples_failed"]:
            _append_example(
                global_stats["examples_failed"],
                emit_examples,
                example["err_type"],
                example["raw_line"],
                {"lane": lane},
            )

    return shadow_predictions, global_stats


def _pass_presence(env_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
    return {
        "miners": all(node_id in env_by_id for node_id in MINER_NODE_TO_LANE),
        "spine": SPINE_NODE_ID in env_by_id,
        "predictions": all(node_id in env_by_id for node_id in PREDICT_NODE_TO_LANE),
    }


def run(config: dict, run_dir: str) -> Dict[str, Any]:
    """[ACTION]
    - Teleology: Build the full shadow summary for one run directory from artifact JSON and strictness config.
    - Mechanism: Apply optional node-map overrides, load each required envelope, parse miner/spine/prediction passes, compute hard-failure reasons, and return metadata plus normalized data payloads.
    - Reads: config, run_dir, load_env(), and the parser-pass helpers.
    - Guarantee: Returns a dict with `metadata` and `data`; `metadata.hard_failure` reflects strict mode, artifact presence, and parsed_ok coverage.
    - Fails: None.
    - When-needed: Open when a run's shadow envelope, strict-failure reason, or parse_stats must be explained without reading every parser helper.
    - Escalates-to: tools/shadow/shadow.py::load_env; tools/shadow/shadow.py::_parse_miner_pass; tools/shadow/shadow.py::_parse_spine_pass; tools/shadow/shadow.py::_parse_prediction_pass
    - Navigation-group: python_misc_runtime
    """
    global MINER_NODE_TO_LANE, SPINE_NODE_ID, PREDICT_NODE_TO_LANE, REQUIRED_NODE_IDS

    tool_cfg = {}
    if isinstance(config, dict):
        raw_cfg = config.get("config", {})
        if isinstance(raw_cfg, dict):
            tool_cfg = raw_cfg

    strict = _parse_bool(tool_cfg.get("strict", True), default=True)
    emit_examples = _parse_bool(tool_cfg.get("emit_examples", True), default=True)
    max_lines_per_artifact = _parse_optional_int(tool_cfg.get("max_lines_per_artifact"))

    # [PHASE 3] Schema-driven node maps (backward-compatible defaults)
    node_map = tool_cfg.get("node_map", None)
    if node_map and isinstance(node_map, dict):
        MINER_NODE_TO_LANE = node_map.get("miners", _DEFAULT_MINER_NODE_TO_LANE)
        SPINE_NODE_ID = node_map.get("spine", _DEFAULT_SPINE_NODE_ID)
        PREDICT_NODE_TO_LANE = node_map.get("predictions", _DEFAULT_PREDICT_NODE_TO_LANE)
        REQUIRED_NODE_IDS = tuple(
            list(MINER_NODE_TO_LANE.keys()) + [SPINE_NODE_ID] + list(PREDICT_NODE_TO_LANE.keys())
        )
    else:
        # Reset to defaults for safety
        MINER_NODE_TO_LANE = _DEFAULT_MINER_NODE_TO_LANE
        SPINE_NODE_ID = _DEFAULT_SPINE_NODE_ID
        PREDICT_NODE_TO_LANE = _DEFAULT_PREDICT_NODE_TO_LANE
        REQUIRED_NODE_IDS = tuple(
            list(MINER_NODE_TO_LANE.keys()) + [SPINE_NODE_ID] + list(PREDICT_NODE_TO_LANE.keys())
        )

    run_root, artifacts_dir = _normalize_run_paths(run_dir)

    env_by_id: Dict[str, Dict[str, Any]] = {}
    missing_artifacts: List[str] = []
    artifact_issues: Dict[str, Dict[str, Any]] = {}

    for node_id in REQUIRED_NODE_IDS:
        env, error, warnings = load_env(artifacts_dir, node_id)
        issue: Dict[str, Any] = {}
        if warnings:
            issue["warnings"] = warnings
        if error is not None:
            issue["error"] = error
            missing_artifacts.append(node_id)
        else:
            env_by_id[node_id] = env  # type: ignore[assignment]
        if issue:
            artifact_issues[node_id] = issue

    shadow_miners, miner_stats = _parse_miner_pass(
        env_by_id=env_by_id,
        max_lines_per_artifact=max_lines_per_artifact,
        emit_examples=emit_examples,
    )
    shadow_spine, spine_stats = _parse_spine_pass(
        env_by_id=env_by_id,
        max_lines_per_artifact=max_lines_per_artifact,
        emit_examples=emit_examples,
    )
    shadow_predictions, prediction_stats = _parse_prediction_pass(
        env_by_id=env_by_id,
        max_lines_per_artifact=max_lines_per_artifact,
        emit_examples=emit_examples,
    )

    pass_presence = _pass_presence(env_by_id)
    hard_failure_reasons: List[str] = []

    if strict and missing_artifacts:
        hard_failure_reasons.append("missing_required_artifacts")
    if pass_presence["miners"] and miner_stats["parsed_ok"] == 0:
        hard_failure_reasons.append("miners_pass_parsed_ok_zero")
    if pass_presence["spine"] and spine_stats["parsed_ok"] == 0:
        hard_failure_reasons.append("spine_pass_parsed_ok_zero")
    if pass_presence["predictions"] and prediction_stats["parsed_ok"] == 0:
        hard_failure_reasons.append("predictions_pass_parsed_ok_zero")

    hard_failure = len(hard_failure_reasons) > 0
    reason = "; ".join(hard_failure_reasons)

    metadata = {
        "tool": "shadow",
        "shadow_version": "v2.1",
        "strict": strict,
        "missing_artifacts": sorted(missing_artifacts),
        "hard_failure": hard_failure,
        "reason": reason,
        "timestamp": _now_iso(),
    }

    data = {
        "shadow_miners": shadow_miners,
        "shadow_spine": shadow_spine,
        "shadow_predictions": shadow_predictions,
        "parse_stats": {
            "miners": miner_stats,
            "spine": spine_stats,
            "predictions": prediction_stats,
            "pass_presence": pass_presence,
            "artifact_issues": artifact_issues,
            "artifacts_dir": str(artifacts_dir),
            "run_root": str(run_root),
        },
    }

    return {"metadata": metadata, "data": data}
