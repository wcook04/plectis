"""
Coverage evaluator for the agent observability animation contract.

This module is intentionally a consumer of the semantic-camera scene/delta
payloads, not a second classifier. It lets backend tests answer whether a live
visual instrument can render from backend-owned primitives without parsing
event summaries or command strings in frontend code.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


KIND = "agent_observability.animation_coverage"
SCHEMA_VERSION = "agent_observability_animation_coverage_v0"

EVENT_SEMANTIC_FIELDS = (
    "animation_channel",
    "animation_directive",
    "semantic_token",
    "coalesce_key",
    "quality",
)
ACTOR_IDENTITY_FIELDS = ("id", "session_id", "provider", "status", "heartbeat")
SPAN_FIELDS = ("id", "session_id", "event_id", "channel", "kind", "status", "quality")
FLOW_FIELDS = ("id", "type", "quality")
FILE_IMPACT_FIELDS = ("id", "path", "operation", "claim_state", "generated_state", "quality")
PROOF_RECEIPT_FIELDS = ("id", "kind", "status", "scope", "quality")
COUNTER_FIELDS = ("id", "name", "value", "unit", "quality")
QUALITY_FIELDS = ("authority", "confidence", "missingness", "source")

REQUIRED_PRIMITIVE_FAMILIES = {
    "actors",
    "spans",
    "flows",
    "counters",
    "file_impacts",
    "proof_receipts",
    "quality",
}
REQUIRED_DELTA_OPS = {
    "event_append",
    "span_upsert",
    "flow_upsert",
    "counter_update",
    "file_impact_upsert",
    "proof_receipt_upsert",
    "quality_update",
}


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _mapping_rows(value: object) -> list[Mapping[str, Any]]:
    return [row for row in _as_list(value) if isinstance(row, Mapping)]


def _pct(part: int, total: int) -> float:
    if total <= 0:
        return 1.0 if part == 0 else 0.0
    return round(part / total, 4)


def _row_id(row: Mapping[str, Any]) -> str:
    return str(row.get("id") or row.get("event_id") or row.get("session_id") or row.get("name") or "unknown")


def _counter(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "unknown") for row in rows).items()))


def _missing_fields(row: Mapping[str, Any], fields: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for field in fields:
        value = row.get(field)
        if value is None or value == "" or value == [] or value == {}:
            missing.append(field)
    return missing


def _field_coverage(rows: Sequence[Mapping[str, Any]], fields: Sequence[str], *, sample_limit: int = 8) -> dict[str, Any]:
    complete = 0
    missing_by_field: Counter[str] = Counter()
    missing_examples: list[dict[str, Any]] = []
    for row in rows:
        missing = _missing_fields(row, fields)
        if not missing:
            complete += 1
            continue
        missing_by_field.update(missing)
        if len(missing_examples) < sample_limit:
            missing_examples.append({"id": _row_id(row), "missing": missing})
    return {
        "row_count": len(rows),
        "complete_count": complete,
        "coverage": _pct(complete, len(rows)),
        "missing_by_field": dict(sorted(missing_by_field.items())),
        "missing_examples": missing_examples,
    }


def _quality_rows(*groups: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for group in groups:
        for row in group:
            quality = _as_mapping(row.get("quality"))
            if quality:
                rows.append(quality)
    return rows


def _quality_stats(*groups: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    qualities = _quality_rows(*groups)
    missingness: Counter[str] = Counter()
    for quality in qualities:
        missingness.update(str(item) for item in _as_list(quality.get("missingness")) if item)
    return {
        "quality_row_count": len(qualities),
        "quality_field_coverage": _field_coverage(qualities, QUALITY_FIELDS),
        "authority_counts": _counter(qualities, "authority"),
        "confidence_counts": _counter(qualities, "confidence"),
        "source_counts": _counter(qualities, "source"),
        "missingness_counts": dict(sorted(missingness.items())),
    }


def _event_ids(rows: Sequence[Mapping[str, Any]], *fields: str) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        for field in fields:
            value = row.get(field)
            if value is not None and value != "":
                ids.add(str(value))
    return ids


def _requirement(requirements: list[dict[str, Any]], requirement_id: str, passed: bool, detail: str) -> None:
    requirements.append({
        "id": requirement_id,
        "status": "pass" if passed else "fail",
        "detail": detail,
    })


def _expectation_status(name: str, required: Sequence[str], observed: set[str]) -> dict[str, Any]:
    required_set = {str(item) for item in required if item}
    missing = sorted(required_set - observed)
    return {
        "name": name,
        "required": sorted(required_set),
        "observed": sorted(observed),
        "missing": missing,
        "status": "pass" if not missing else "fail",
    }


def build_agent_observability_animation_coverage(
    *,
    scene: Mapping[str, Any],
    delta: Mapping[str, Any] | None = None,
    expectations: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Evaluate whether scene/delta primitives are sufficient for a visual consumer.

    The evaluator only reads already-normalized semantic-camera fields. It does
    not classify from summaries, commands, raw payload text, or natural
    language trace prose.
    """
    scene_map = _as_mapping(scene)
    delta_map = _as_mapping(delta)
    expectations_map = _as_mapping(expectations)

    actors = _mapping_rows(scene_map.get("actors"))
    events = _mapping_rows(scene_map.get("events"))
    channels = _mapping_rows(scene_map.get("channels"))
    spans = _mapping_rows(scene_map.get("spans"))
    flows = _mapping_rows(scene_map.get("flows"))
    counters = _mapping_rows(scene_map.get("counters"))
    file_impacts = _mapping_rows(scene_map.get("file_impacts"))
    proof_receipts = _mapping_rows(scene_map.get("proof_receipts"))
    attention = _mapping_rows(scene_map.get("attention"))
    data_quality = _as_mapping(scene_map.get("data_quality"))
    stream_contract = _as_mapping(scene_map.get("stream_contract"))
    primitive_families = {str(item) for item in _as_list(stream_contract.get("primitive_families"))}

    event_id_set = _event_ids(events, "id")
    span_event_ids = _event_ids(spans, "event_id")
    flow_event_ids = _event_ids(flows, "event_id", "from_event_id", "to_event_id")
    file_event_ids = _event_ids(file_impacts, "event_id")
    proof_event_ids = _event_ids(proof_receipts, "event_id")
    attention_event_ids = _event_ids(attention, "event_id")

    channel_ids = {str(row.get("id")) for row in channels if row.get("id")}
    event_channels = {str(row.get("animation_channel")) for row in events if row.get("animation_channel")}
    unmanifested_channels = sorted(event_channels - channel_ids)

    delta_ops = _mapping_rows(delta_map.get("ops"))
    delta_op_types = {str(op.get("op")) for op in delta_ops if op.get("op")}

    requirements: list[dict[str, Any]] = []
    _requirement(
        requirements,
        "scene_kind",
        scene_map.get("kind") == "agent_observability.animation_scene",
        "scene payload identifies the animation scene contract",
    )
    _requirement(
        requirements,
        "primitive_families_declared",
        REQUIRED_PRIMITIVE_FAMILIES <= primitive_families,
        "stream contract declares backend-owned live visual primitive families",
    )
    _requirement(
        requirements,
        "actors_have_identity",
        bool(actors) and _field_coverage(actors, ACTOR_IDENTITY_FIELDS)["coverage"] == 1.0,
        "actors expose provider/session/status/heartbeat identity without frontend inference",
    )
    _requirement(
        requirements,
        "events_semantically_classified",
        bool(events) and _field_coverage(events, EVENT_SEMANTIC_FIELDS)["coverage"] == 1.0,
        "events carry channel/directive/token/coalesce key/quality fields",
    )
    _requirement(
        requirements,
        "channels_manifest_event_semantics",
        bool(event_channels) and not unmanifested_channels,
        "channel manifest covers every event animation_channel",
    )
    _requirement(
        requirements,
        "spans_available",
        bool(spans) and _field_coverage(spans, SPAN_FIELDS)["coverage"] == 1.0,
        "time-bounded spans are present and event-backed",
    )
    _requirement(
        requirements,
        "flows_available",
        bool(flows) and _field_coverage(flows, FLOW_FIELDS)["coverage"] == 1.0,
        "causal or sequence flows are present and quality-tagged",
    )
    _requirement(
        requirements,
        "counters_available",
        bool(counters) and _field_coverage(counters, COUNTER_FIELDS)["coverage"] == 1.0,
        "backend emits counters for live instrumentation and quality overlays",
    )
    _requirement(
        requirements,
        "file_impacts_available",
        bool(file_impacts) and _field_coverage(file_impacts, FILE_IMPACT_FIELDS)["coverage"] == 1.0,
        "file impacts are normalized as backend primitives",
    )
    _requirement(
        requirements,
        "proof_receipts_available",
        bool(proof_receipts) and _field_coverage(proof_receipts, PROOF_RECEIPT_FIELDS)["coverage"] == 1.0,
        "proof receipts are typed and scoped by the backend",
    )
    _requirement(
        requirements,
        "quality_surface_available",
        bool(data_quality) and "snapshot_required" in data_quality,
        "global quality/missingness state is present",
    )
    if delta is not None:
        _requirement(
            requirements,
            "delta_primitive_ops_available",
            REQUIRED_DELTA_OPS <= delta_op_types,
            "delta emits replayable primitive operations for the live visual consumer",
        )
        _requirement(
            requirements,
            "delta_cursor_and_backpressure_available",
            bool(_as_mapping(delta_map.get("cursor"))) and bool(_as_mapping(delta_map.get("backpressure"))),
            "delta carries cursor and backpressure control signals",
        )

    expectation_rows = [
        _expectation_status(
            "providers",
            expectations_map.get("providers") or [],
            {str(actor.get("provider")) for actor in actors if actor.get("provider")},
        ),
        _expectation_status("channels", expectations_map.get("channels") or [], event_channels),
        _expectation_status(
            "file_operations",
            expectations_map.get("file_operations") or [],
            {str(impact.get("operation")) for impact in file_impacts if impact.get("operation")},
        ),
        _expectation_status(
            "claim_states",
            expectations_map.get("claim_states") or [],
            {str(impact.get("claim_state")) for impact in file_impacts if impact.get("claim_state")},
        ),
        _expectation_status(
            "generated_states",
            expectations_map.get("generated_states") or [],
            {str(impact.get("generated_state")) for impact in file_impacts if impact.get("generated_state")},
        ),
        _expectation_status(
            "proof_kinds",
            expectations_map.get("proof_kinds") or [],
            {str(receipt.get("kind")) for receipt in proof_receipts if receipt.get("kind")},
        ),
        _expectation_status(
            "proof_statuses",
            expectations_map.get("proof_statuses") or [],
            {str(receipt.get("status")) for receipt in proof_receipts if receipt.get("status")},
        ),
        _expectation_status(
            "actor_statuses",
            expectations_map.get("actor_statuses") or [],
            {str(actor.get("status")) for actor in actors if actor.get("status")},
        ),
        _expectation_status(
            "span_statuses",
            expectations_map.get("span_statuses") or [],
            {str(span.get("status")) for span in spans if span.get("status")},
        ),
        _expectation_status(
            "attention_kinds",
            expectations_map.get("attention_kinds") or [],
            {str(item.get("kind")) for item in attention if item.get("kind")},
        ),
        _expectation_status("delta_op_types", expectations_map.get("delta_op_types") or [], delta_op_types),
    ]
    expectation_failures = [row for row in expectation_rows if row["status"] == "fail"]

    failed_requirements = [row for row in requirements if row["status"] == "fail"]
    ready = not failed_requirements and not expectation_failures
    missing_backend_semantics = [
        row["id"] for row in failed_requirements
    ] + [
        f"expected_{row['name']}:{','.join(row['missing'])}" for row in expectation_failures
    ]

    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "authority_boundary": (
            "coverage_over_semantic_camera_scene_delta_only; evaluator does not parse summaries, "
            "commands, raw payload prose, or trace text"
        ),
        "readiness": {
            "ready_for_first_live_visual_consumer": ready,
            "frontend_string_heuristics_required": not ready,
            "missing_backend_semantics": missing_backend_semantics,
            "passed_requirement_count": len(requirements) - len(failed_requirements),
            "failed_requirement_count": len(failed_requirements),
            "failed_expectation_count": len(expectation_failures),
        },
        "requirements": requirements,
        "expectations": expectation_rows,
        "coverage": {
            "actors": {
                "count": len(actors),
                "identity": _field_coverage(actors, ACTOR_IDENTITY_FIELDS),
                "provider_counts": _counter(actors, "provider"),
                "status_counts": _counter(actors, "status"),
                "heartbeat_counts": _counter(actors, "heartbeat"),
            },
            "events": {
                "count": len(events),
                "semantic_fields": _field_coverage(events, EVENT_SEMANTIC_FIELDS),
                "channel_counts": _counter(events, "animation_channel"),
                "directive_counts": _counter(events, "animation_directive"),
                "status_counts": _counter(events, "status"),
            },
            "channels": {
                "count": len(channels),
                "manifest_ids": sorted(channel_ids),
                "event_channels": sorted(event_channels),
                "unmanifested_event_channels": unmanifested_channels,
            },
            "spans": {
                "count": len(spans),
                "fields": _field_coverage(spans, SPAN_FIELDS),
                "status_counts": _counter(spans, "status"),
                "channel_counts": _counter(spans, "channel"),
                "event_coverage": _pct(len(event_id_set & span_event_ids), len(event_id_set)),
            },
            "flows": {
                "count": len(flows),
                "fields": _field_coverage(flows, FLOW_FIELDS),
                "type_counts": _counter(flows, "type"),
                "event_coverage": _pct(len(event_id_set & flow_event_ids), len(event_id_set)),
            },
            "file_impacts": {
                "count": len(file_impacts),
                "fields": _field_coverage(file_impacts, FILE_IMPACT_FIELDS),
                "operation_counts": _counter(file_impacts, "operation"),
                "claim_state_counts": _counter(file_impacts, "claim_state"),
                "generated_state_counts": _counter(file_impacts, "generated_state"),
                "event_coverage": _pct(len(event_id_set & file_event_ids), len(event_id_set)),
            },
            "proof_receipts": {
                "count": len(proof_receipts),
                "fields": _field_coverage(proof_receipts, PROOF_RECEIPT_FIELDS),
                "kind_counts": _counter(proof_receipts, "kind"),
                "status_counts": _counter(proof_receipts, "status"),
                "scope_counts": _counter(proof_receipts, "scope"),
                "event_coverage": _pct(len(event_id_set & proof_event_ids), len(event_id_set)),
            },
            "attention": {
                "count": len(attention),
                "kind_counts": _counter(attention, "kind"),
                "severity_counts": _counter(attention, "severity"),
                "event_coverage": _pct(len(event_id_set & attention_event_ids), len(event_id_set)),
            },
            "counters": {
                "count": len(counters),
                "fields": _field_coverage(counters, COUNTER_FIELDS),
                "names": sorted(str(counter.get("name")) for counter in counters if counter.get("name")),
            },
            "quality": _quality_stats(events, spans, flows, file_impacts, proof_receipts, counters),
            "delta": {
                "present": delta is not None,
                "op_count": len(delta_ops),
                "op_types": sorted(delta_op_types),
                "snapshot_required": delta_map.get("snapshot_required") if delta is not None else None,
                "snapshot_reason": delta_map.get("snapshot_reason") if delta is not None else None,
                "backpressure": _as_mapping(delta_map.get("backpressure")),
                "ops_with_quality": _field_coverage(delta_ops, ("op", "id", "quality")),
            },
            "data_quality": data_quality,
        },
        "consumer_contract": {
            "frontend_owned": ["layout", "animation_easing", "density", "selection", "scrubbing", "color"],
            "backend_owned": [
                "semantic channels",
                "animation directives",
                "spans",
                "flows",
                "counters",
                "file impacts",
                "proof receipts",
                "attention",
                "quality envelopes",
                "cursor",
                "backpressure",
            ],
            "forbidden_frontend_inference": [
                "classify proof from command strings",
                "infer file impact from summaries",
                "derive claim collisions from prose",
                "guess quality or missingness from raw trace text",
            ],
        },
    }
