"""
[PURPOSE]
- Teleology: Own the shared 5x5 controller-heartbeat contract so Type A
  controllers, bridge missions, and live runtime projections can operate from
  one bounded mission shard instead of re-deriving state differently.
- Mechanism: Build deterministic heartbeat payloads from family/phase metadata,
  validate the five-sentence field contract, normalize source refs and wake
  conditions, and optionally wrap observe response schemas with a heartbeat ref.
- Non-goal: Replace synth_seed.json, autonomous_seed.json, or work-ledger state;
  this module only projects a compressed controller packet from those surfaces.

[INTERFACE]
- Exports: `build_controller_heartbeat`, `controller_heartbeat_ref`,
  `validate_controller_heartbeat`, `count_sentences`,
  `ControllerHeartbeatDeduper`, `controller_heartbeat_event_id`,
  `default_mission_blackboard_path`,
  `heartbeat_ref_schema`, and `wrap_response_schema_with_heartbeat_ref`.
- Reads: Caller-supplied family/phase metadata only.
- Writes: None.

[CONSTRAINTS]
- The five narrative fields always contain exactly five sentences each.
- Metadata stays machine-readable and separate from the narrative blocks.
- Schema wrapping preserves the original mission payload under `payload`.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


CONTROLLER_HEARTBEAT_SCHEMA_VERSION = "controller_heartbeat_v1"
CONTROLLER_HEARTBEAT_REF_SCHEMA_VERSION = "controller_heartbeat_ref_v1"
CONTROLLER_HEARTBEAT_FIELDS = (
    "system",
    "problem",
    "mission",
    "action",
    "continuity",
)
CONTROLLER_HEARTBEAT_SENTENCE_COUNT = 5
DEFAULT_MISSION_BLACKBOARD_PATH = "state/mission_blackboard/board.json"
LEGACY_GENERIC_PROBLEM_PREFIX = (
    "The system still compresses truth differently across bridge packets, family continuity, phase continuity, and runtime boards."
)
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?](?=\s|$)", re.DOTALL)
DEFAULT_HEARTBEAT_DEDUPE_TTL_SECONDS = 60 * 60
DEFAULT_HEARTBEAT_DEDUPE_MAX_ENTRIES = 1000


_HEARTBEAT_EVENT_ID_FIELDS = (
    "schema_version",
    "family_id",
    "phase_id",
    "wave_id",
    "execution_mode",
    "source_refs",
    "wake_conditions",
    *CONTROLLER_HEARTBEAT_FIELDS,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _strip_terminal_punctuation(value: Any) -> str:
    return _string(value).rstrip(" \t\r\n.!?")


def _coerce_epoch_seconds(value: Any) -> float:
    if value is None:
        return datetime.now(timezone.utc).timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, datetime):
        token = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return token.timestamp()
    token = _string(value)
    if token:
        try:
            return datetime.fromisoformat(token.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    return datetime.now(timezone.utc).timestamp()


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _normalize_ref_items(values: Any, *, required_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for raw in values:
        if not isinstance(raw, Mapping):
            continue
        item = {str(key): raw.get(key) for key in raw.keys()}
        signature = tuple(_string(item.get(key)) for key in required_keys)
        if not any(signature) or signature in seen:
            continue
        seen.add(signature)
        normalized.append(
            {
                "kind": _string(item.get("kind")) or None,
                "path": _string(item.get("path")) or None,
                "summary": _string(item.get("summary")) or None,
            }
        )
    return normalized


def split_sentences(text: Any) -> list[str]:
    token = _string(text)
    if not token:
        return []
    matches = [match.group(0).strip() for match in _SENTENCE_RE.finditer(token)]
    return [item for item in matches if item]


def count_sentences(text: Any) -> int:
    return len(split_sentences(text))


def default_mission_blackboard_path() -> str:
    return DEFAULT_MISSION_BLACKBOARD_PATH


def controller_heartbeat_event_id(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return ""
    identity_payload = {
        key: payload.get(key)
        for key in _HEARTBEAT_EVENT_ID_FIELDS
        if key in payload
    }
    if "schema_version" not in identity_payload:
        identity_payload["schema_version"] = CONTROLLER_HEARTBEAT_SCHEMA_VERSION
    encoded = json.dumps(
        identity_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return "chb_" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


class ControllerHeartbeatDeduper:
    """Bounded in-memory repeat suppression for heartbeat event consumers."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_HEARTBEAT_DEDUPE_TTL_SECONDS,
        max_entries: int = DEFAULT_HEARTBEAT_DEDUPE_MAX_ENTRIES,
    ) -> None:
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self._seen_at: OrderedDict[str, float] = OrderedDict()

    def prune(self, *, now: Any = None) -> int:
        now_seconds = _coerce_epoch_seconds(now)
        cutoff = now_seconds - self.ttl_seconds
        expired = [
            event_id
            for event_id, seen_at in self._seen_at.items()
            if seen_at < cutoff
        ]
        for event_id in expired:
            self._seen_at.pop(event_id, None)
        while len(self._seen_at) > self.max_entries:
            self._seen_at.popitem(last=False)
        return len(self._seen_at)

    def register(
        self,
        payload: Mapping[str, Any] | str | None,
        *,
        now: Any = None,
    ) -> dict[str, Any]:
        event_id = (
            _string(payload)
            if isinstance(payload, str)
            else controller_heartbeat_event_id(payload)
        )
        now_seconds = _coerce_epoch_seconds(now)
        self.prune(now=now_seconds)
        duplicate = bool(event_id and event_id in self._seen_at)
        if event_id:
            self._seen_at[event_id] = now_seconds
            self._seen_at.move_to_end(event_id)
        self.prune(now=now_seconds)
        return {
            "event_id": event_id,
            "duplicate": duplicate,
            "seen_count": len(self._seen_at),
            "ttl_seconds": self.ttl_seconds,
            "max_entries": self.max_entries,
        }


def validate_controller_heartbeat(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["controller heartbeat must be a JSON object."]
    errors: list[str] = []
    if _string(payload.get("schema_version")) != CONTROLLER_HEARTBEAT_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be `{CONTROLLER_HEARTBEAT_SCHEMA_VERSION}`."
        )
    for key in (
        "family_id",
        "phase_id",
        "wave_id",
        "execution_mode",
        "updated_at",
    ):
        if not _string(payload.get(key)):
            errors.append(f"{key} is required.")
    source_refs = payload.get("source_refs")
    if not isinstance(source_refs, list):
        errors.append("source_refs must be a list.")
    wake_conditions = payload.get("wake_conditions")
    if not isinstance(wake_conditions, list):
        errors.append("wake_conditions must be a list.")
    event_id = _string(payload.get("event_id"))
    if event_id and event_id != controller_heartbeat_event_id(payload):
        errors.append("event_id does not match the canonical controller heartbeat identity.")
    for field in CONTROLLER_HEARTBEAT_FIELDS:
        text = _string(payload.get(field))
        if not text:
            errors.append(f"{field} is required.")
            continue
        sentence_total = count_sentences(text)
        if sentence_total != CONTROLLER_HEARTBEAT_SENTENCE_COUNT:
            errors.append(
                f"{field} must contain exactly {CONTROLLER_HEARTBEAT_SENTENCE_COUNT} sentences "
                f"(found {sentence_total})."
            )
    return errors


def _default_source_refs(
    *,
    family_dir: str,
    phase_dir: str,
    family_charter_path: str,
    autonomous_seed_path: str,
    synth_seed_path: str,
) -> list[dict[str, Any]]:
    refs = [
        {
            "kind": "family_charter",
            "path": family_charter_path or f"{family_dir.rstrip('/')}/family_charter.json",
            "summary": "Family operating posture and broad execution charter.",
        },
        {
            "kind": "autonomous_seed",
            "path": autonomous_seed_path or f"{family_dir.rstrip('/')}/autonomous_seed.json",
            "summary": "Family continuity projection for detached controller re-entry.",
        },
        {
            "kind": "synth_seed",
            "path": synth_seed_path or f"{phase_dir.rstrip('/')}/synth_seed.json",
            "summary": "Active phase whiteboard authority for the current wave.",
        },
        {
            "kind": "mission_blackboard",
            "path": DEFAULT_MISSION_BLACKBOARD_PATH,
            "summary": "Live mission-board projection backed by seed state and work-ledger state.",
        },
        {
            "kind": "work_ledger_runtime",
            "path": "state/work_ledger/runtime_status.json",
            "summary": "Session and stale-work runtime projection for Type A activity.",
        },
    ]
    return _normalize_ref_items(refs, required_keys=("kind", "path"))


def _default_wake_conditions(*, phase_dir: str) -> list[dict[str, Any]]:
    conditions = [
        {
            "kind": "pipeline_attention",
            "path": f"{phase_dir.rstrip('/')}/pipeline_attention.json",
            "summary": "Wake when the phase pipeline requests controller review.",
        },
        {
            "kind": "resume_contract",
            "path": f"{phase_dir.rstrip('/')}/resume_contract.json",
            "summary": "Wake when detached observe work reaches a durable resume contract.",
        },
        {
            "kind": "continuation_packet",
            "path": f"{phase_dir.rstrip('/')}/continuation_packet.json",
            "summary": "Wake from the disk-first continuation packet rather than chat memory.",
        },
        {
            "kind": "mission_blackboard",
            "path": DEFAULT_MISSION_BLACKBOARD_PATH,
            "summary": "Wake when the live mission row changes enough to alter the next bounded action.",
        },
    ]
    return _normalize_ref_items(conditions, required_keys=("kind", "path"))


def _generated_heartbeat_fields(
    *,
    family_id: str,
    phase_id: str,
    phase_title: str,
    execution_mode: str,
    objective: str,
    bounded_question: str,
    next_step_posture: str,
) -> dict[str, str]:
    phase_label = phase_id or phase_title or "the active phase"
    execution = execution_mode or "hybrid"
    focus = _strip_terminal_punctuation(
        objective or bounded_question or phase_title or "the active bounded proof lane"
    ) or "the active bounded proof lane"
    problem_focus = _strip_terminal_punctuation(
        bounded_question or objective or phase_title or "the active bounded proof lane"
    ) or "the active bounded proof lane"
    next_posture = _strip_terminal_punctuation(
        next_step_posture or "the next smallest bounded proof"
    ) or "the next smallest bounded proof"
    return {
        "system": (
            "This repo already contains continuity, routing, bridge dispatch, raw-seed metabolism, and navigation substrates. "
            f"The live family is {family_id or 'the active family'} and the active phase is {phase_label} running in {execution} mode. "
            "Family autonomous_seed, phase synth_seed, paper modules, and the bridge runtime remain the authoritative controller surfaces. "
            "The gap is controller compression across agents rather than missing basic infrastructure. "
            "Every next move should start from disk state and choose the smallest change that makes the runtime more unified and more used."
        ),
        "problem": (
            f"Current bounded question: {problem_focus}. "
            "Agents must not replace that question with a stale generic problem statement. "
            "The controller packet has to carry one runtime truth across family seed, phase synth, runtime queues, and diagnostics. "
            "Provider or transport failures should be surfaced as evidence, not buried as manual fallback. "
            "The immediate fix is to keep the heartbeat tied to the active synth and the next verified proof lane."
        ),
        "mission": (
            "My mission is to keep the controller packet real, universal, and operational. "
            "I should treat the heartbeat as a projection over existing seeds rather than a replacement. "
            f"I should keep the active focus anchored to {focus}. "
            "I should prefer one bounded proof lane that uses bridge productively over broad cleanup or theory work. "
            "I should only widen scope after the last proof has been assimilated back into disk state."
        ),
        "action": (
            f"First resolve the authoritative disk packet for {phase_label}. "
            f"Then run the smallest probe that answers {problem_focus}. "
            "Next record provider, transport, and runtime evidence directly in the phase or runtime artifacts. "
            "Then update the synth and heartbeat instead of carrying drift in chat. "
            f"Finally assimilate the result, refresh continuity artifacts, and choose {next_posture}."
        ),
        "continuity": (
            "Use disk artifacts as the only continuity authority and assume later agents inherit more truth than this moment has. "
            "Keep the controller local for scoping, synthesis, verification, and apply gates. "
            "Use delegated workers only for bounded reasoning lanes that fit the active execution mode. "
            "Wake on durable review or resume artifacts instead of waiting in-thread. "
            "If the next step is unclear, prefer the smallest action that increases operator visibility, bridge usefulness, and navigation through existing surfaces."
        ),
    }


def build_controller_heartbeat(
    *,
    family_id: str,
    family_dir: str,
    phase_id: str,
    phase_title: str,
    phase_dir: str,
    wave_id: str,
    execution_mode: str,
    objective: str = "",
    bounded_question: str = "",
    next_step_posture: str = "",
    updated_at: str = "",
    family_charter_path: str = "",
    autonomous_seed_path: str = "",
    synth_seed_path: str = "",
    source_refs: Sequence[Mapping[str, Any]] | None = None,
    wake_conditions: Sequence[Mapping[str, Any]] | None = None,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    generated = _generated_heartbeat_fields(
        family_id=family_id,
        phase_id=phase_id,
        phase_title=phase_title,
        execution_mode=execution_mode,
        objective=objective,
        bounded_question=bounded_question,
        next_step_posture=next_step_posture,
    )
    prior = dict(existing or {})
    field_values: dict[str, str] = {}
    for field in CONTROLLER_HEARTBEAT_FIELDS:
        candidate = _string(prior.get(field))
        if field == "problem" and candidate.startswith(LEGACY_GENERIC_PROBLEM_PREFIX):
            candidate = ""
        field_values[field] = (
            candidate
            if count_sentences(candidate) == CONTROLLER_HEARTBEAT_SENTENCE_COUNT
            else generated[field]
        )

    normalized_source_refs = _normalize_ref_items(
        [
            *_default_source_refs(
                family_dir=family_dir,
                phase_dir=phase_dir,
                family_charter_path=family_charter_path,
                autonomous_seed_path=autonomous_seed_path,
                synth_seed_path=synth_seed_path,
            ),
            *list(source_refs or []),
            *list(prior.get("source_refs") or []),
        ],
        required_keys=("kind", "path"),
    )
    normalized_wake_conditions = _normalize_ref_items(
        [
            *_default_wake_conditions(phase_dir=phase_dir),
            *list(wake_conditions or []),
            *list(prior.get("wake_conditions") or []),
        ],
        required_keys=("kind", "path"),
    )
    heartbeat = {
        "schema_version": CONTROLLER_HEARTBEAT_SCHEMA_VERSION,
        "family_id": _string(family_id),
        "phase_id": _string(phase_id),
        "wave_id": _string(wave_id),
        "execution_mode": _string(execution_mode),
        "updated_at": _string(updated_at) or _utc_now(),
        "source_refs": normalized_source_refs,
        "wake_conditions": normalized_wake_conditions,
        **field_values,
    }
    heartbeat["event_id"] = controller_heartbeat_event_id(heartbeat)
    return heartbeat


def controller_heartbeat_ref(
    payload: Mapping[str, Any] | None,
    *,
    source_path: str | None = None,
) -> dict[str, Any]:
    heartbeat = dict(payload or {})
    ref = {
        "schema_version": CONTROLLER_HEARTBEAT_REF_SCHEMA_VERSION,
        "family_id": _string(heartbeat.get("family_id")),
        "phase_id": _string(heartbeat.get("phase_id")),
        "wave_id": _string(heartbeat.get("wave_id")),
        "execution_mode": _string(heartbeat.get("execution_mode")),
        "updated_at": _string(heartbeat.get("updated_at")),
        "event_id": _string(heartbeat.get("event_id"))
        or controller_heartbeat_event_id(heartbeat),
    }
    if _string(source_path):
        ref["source_path"] = _string(source_path)
    return ref


def heartbeat_ref_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "schema_version",
            "family_id",
            "phase_id",
            "wave_id",
            "execution_mode",
            "updated_at",
        ],
        "properties": {
            "schema_version": {"type": "string"},
            "family_id": {"type": "string"},
            "phase_id": {"type": "string"},
            "wave_id": {"type": "string"},
            "execution_mode": {"type": "string"},
            "updated_at": {"type": "string"},
            "event_id": {"type": "string"},
            "source_path": {"type": "string"},
        },
    }


def wrap_response_schema_with_heartbeat_ref(
    response_schema: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(response_schema, Mapping):
        return None
    required = response_schema.get("required")
    properties = response_schema.get("properties")
    if (
        isinstance(required, list)
        and "heartbeat_ref" in required
        and "payload" in required
        and isinstance(properties, Mapping)
        and isinstance(properties.get("payload"), Mapping)
    ):
        return dict(response_schema)
    return {
        "type": "object",
        "required": ["heartbeat_ref", "payload"],
        "properties": {
            "heartbeat_ref": heartbeat_ref_schema(),
            "payload": dict(response_schema),
        },
    }
