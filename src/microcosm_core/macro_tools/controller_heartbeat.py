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

import argparse
import hashlib
import json
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


PASS = "pass"
BLOCKED = "blocked"

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

KIND = "public_controller_continuity_heartbeat"
SCHEMA_VERSION = "public_controller_continuity_heartbeat_v1"
SOURCE_REF = "system/lib/controller_heartbeat.py"
SOURCE_REFS = [
    SOURCE_REF,
    "codex/standards/std_controller_heartbeat.json",
    "codex/doctrine/paper_modules/controller_heartbeat.md",
    "docs/controller_continuity.md",
    "state/microcosm_portfolio/extracted_patterns_ledger.jsonl#controller_continuity_heartbeat",
]
SOURCE_SYMBOL_REFS = [
    "system/lib/controller_heartbeat.py::build_controller_heartbeat",
    "system/lib/controller_heartbeat.py::validate_controller_heartbeat",
    "system/lib/controller_heartbeat.py::controller_heartbeat_event_id",
    "system/lib/controller_heartbeat.py::controller_heartbeat_ref",
    "system/lib/controller_heartbeat.py::wrap_response_schema_with_heartbeat_ref",
    "system/lib/controller_heartbeat.py::ControllerHeartbeatDeduper",
]
TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/controller_heartbeat.py"
TARGET_REFS = [TARGET_REF]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.controller_heartbeat::build_controller_heartbeat",
    "microcosm_core.macro_tools.controller_heartbeat::validate_controller_heartbeat",
    "microcosm_core.macro_tools.controller_heartbeat::controller_heartbeat_event_id",
    "microcosm_core.macro_tools.controller_heartbeat::controller_heartbeat_ref",
    "microcosm_core.macro_tools.controller_heartbeat::wrap_response_schema_with_heartbeat_ref",
    "microcosm_core.macro_tools.controller_heartbeat::ControllerHeartbeatDeduper",
    "microcosm_core.macro_tools.controller_heartbeat::build_public_controller_heartbeat_view",
]
AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_controller_heartbeat_projection_not_live_controller_authority",
    "live_controller_authority_authorized": False,
    "seed_or_blackboard_read_authorized": False,
    "work_ledger_runtime_read_authorized": False,
    "work_ledger_mutation_authorized": False,
    "provider_payload_read": False,
    "browser_hud_live_access": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "recipient_send_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "private_root_equivalence_claim": False,
}
ANTI_CLAIM = (
    "This public controller heartbeat tool validates the real macro 5x5 "
    "continuity projection over public metadata and bundle inputs. It does "
    "not read live seeds, mission blackboards, Work Ledger runtime, provider "
    "payloads, browser/HUD state, account/session state, credentials, cookies, "
    "or recipient-send material, and it does not mutate source or authorize release."
)
INPUT_NAMES = (
    "bundle_manifest.json",
    "heartbeat_inputs.json",
    "response_schemas.json",
    "dedupe_sequence.json",
    "controller_heartbeat_policy.json",
    "expected_heartbeat_summary.json",
)
FORBIDDEN_PAYLOAD_KEYS = {
    "raw_worker_transcript_body",
    "raw_controller_transcript",
    "provider_payload",
    "browser_hud_state",
    "browser_hud_cockpit_state",
    "account_session_state",
    "credential_value",
    "cookie_value",
    "recipient_send_payload",
    "seed_body",
    "mission_blackboard_body",
    "work_ledger_runtime_body",
}

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


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _stable_digest(payload: object, *, length: int | None = None) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return digest[:length] if length else digest


def _walk_keys(payload: object) -> list[str]:
    if isinstance(payload, Mapping):
        keys = [str(key) for key in payload.keys()]
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_finding(
    error_code: str,
    message: str,
    *,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    return {
        "status": BLOCKED,
        "error_code": error_code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
    }


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


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root_from_target() -> Path | None:
    for candidate in Path(__file__).resolve(strict=False).parents:
        if (candidate / SOURCE_REF).is_file():
            return candidate
    return None


def _body_import_verification() -> dict[str, Any]:
    target_path = Path(__file__).resolve(strict=False)
    repo_root = _repo_root_from_target()
    source_path = repo_root / SOURCE_REF if repo_root else None
    source_digest = (
        _file_sha256(source_path)
        if source_path is not None and source_path.is_file()
        else ""
    )
    target_digest = _file_sha256(target_path) if target_path.is_file() else ""
    return {
        "verification_status": "verified" if source_digest and target_digest else "target_available",
        "verification_mode": "verified_light_edit_recipe",
        "source_to_target_relation": "source_faithful_public_light_edit",
        "source_ref": SOURCE_REF,
        "target_ref": TARGET_REF,
        "source_body_digest": source_digest or None,
        "target_body_digest": target_digest or None,
        "body_in_receipt": False,
    }


def _validate_controller_heartbeat_policy(payload: object) -> dict[str, Any]:
    policy = payload if isinstance(payload, Mapping) else {}
    findings: list[dict[str, Any]] = []
    required_false = (
        "live_controller_authority_authorized",
        "seed_or_blackboard_read_authorized",
        "work_ledger_runtime_read_authorized",
        "work_ledger_mutation_authorized",
        "provider_payload_read",
        "browser_hud_live_access",
        "account_session_state_exported",
        "credential_or_cookie_exported",
        "recipient_send_authorized",
        "source_mutation_authorized",
        "release_authorized",
    )
    for key in required_false:
        if policy.get(key) is not False:
            findings.append(
                _bundle_finding(
                    "CONTROLLER_HEARTBEAT_AUTHORITY_OVERCLAIM",
                    "Controller heartbeat public replay policy must deny live controller, seed, ledger, provider, browser, account, credential, send, source mutation, and release authority.",
                    subject_id=key,
                    subject_kind="controller_heartbeat_policy",
                )
            )
    if policy.get("body_in_receipt") is not False:
        findings.append(
            _bundle_finding(
                "CONTROLLER_HEARTBEAT_BODY_RECEIPT_OVERCLAIM",
                "Controller heartbeat receipts must carry public summaries and refs, not private seed, blackboard, ledger, provider, or browser bodies.",
                subject_id="body_in_receipt",
                subject_kind="controller_heartbeat_policy",
            )
        )
    return {
        "status": PASS if not findings else BLOCKED,
        "policy_id": _string(policy.get("policy_id"))
        or "public_controller_heartbeat_projection_policy",
        "forbidden_authority_rejected": not findings,
        "source_open_payload_boundary": bool(
            policy.get("source_open_payload_boundary", True)
        ),
        "body_in_receipt": False,
        "findings": findings,
    }


def _heartbeat_from_input_row(row: Mapping[str, Any]) -> dict[str, Any]:
    existing = row.get("existing")
    return build_controller_heartbeat(
        family_id=_string(row.get("family_id"))
        or "microcosm_substrate_flagship_population",
        family_dir=_string(row.get("family_dir"))
        or "state/meta_missions/type_a_autonomous_seed_loop",
        phase_id=_string(row.get("phase_id")) or "09_54_1",
        phase_title=_string(row.get("phase_title"))
        or "Phase 09.54.1 - Microcosm Total Correction and Real Substrate Import",
        phase_dir=_string(row.get("phase_dir"))
        or "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine",
        wave_id=_string(row.get("wave_id"))
        or "microcosm_substrate_flagship_population_wave",
        execution_mode=_string(row.get("execution_mode")) or "direct_local",
        objective=_string(row.get("objective")),
        bounded_question=_string(row.get("bounded_question")),
        next_step_posture=_string(row.get("next_step_posture")),
        updated_at=_string(row.get("updated_at")),
        family_charter_path=_string(row.get("family_charter_path")),
        autonomous_seed_path=_string(row.get("autonomous_seed_path")),
        synth_seed_path=_string(row.get("synth_seed_path")),
        source_refs=[
            *[
                {"kind": "public_source_ref", "path": ref, "summary": "Public source-open controller-heartbeat substrate."}
                for ref in SOURCE_REFS
            ],
            *(
                list(row.get("source_refs") or [])
                if isinstance(row.get("source_refs"), list)
                else []
            ),
        ],
        wake_conditions=(
            list(row.get("wake_conditions") or [])
            if isinstance(row.get("wake_conditions"), list)
            else []
        ),
        existing=existing if isinstance(existing, Mapping) else None,
    )


def _event_stability_rows(heartbeats: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for heartbeat in heartbeats:
        updated_only = dict(heartbeat)
        updated_only["updated_at"] = "2099-01-01T00:00:00+00:00"
        semantic_change = dict(heartbeat)
        semantic_change["wave_id"] = f"{_string(heartbeat.get('wave_id'))}_semantic_change"
        rows.append(
            {
                "event_id": _string(heartbeat.get("event_id")),
                "updated_at_change_keeps_event_id": (
                    controller_heartbeat_event_id(heartbeat)
                    == controller_heartbeat_event_id(updated_only)
                ),
                "semantic_wave_change_changes_event_id": (
                    controller_heartbeat_event_id(heartbeat)
                    != controller_heartbeat_event_id(semantic_change)
                ),
            }
        )
    return rows


def _schema_wrap_rows(
    payload: object,
    *,
    heartbeat_refs: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = _rows(payload, "response_schemas")
    heartbeat_ref = heartbeat_refs[0] if heartbeat_refs else {}
    reports: list[dict[str, Any]] = []
    for row in rows:
        schema = row.get("schema")
        wrapped = wrap_response_schema_with_heartbeat_ref(
            schema if isinstance(schema, Mapping) else None
        )
        second_wrap = wrap_response_schema_with_heartbeat_ref(wrapped)
        reports.append(
            {
                "schema_id": _string(row.get("schema_id")) or "response_schema",
                "wrapped": isinstance(wrapped, Mapping),
                "idempotent": wrapped == second_wrap,
                "heartbeat_ref_event_id": _string(heartbeat_ref.get("event_id")),
                "required": list(wrapped.get("required", []))
                if isinstance(wrapped, Mapping)
                else [],
            }
        )
    return reports


def _dedupe_rows(
    payload: object,
    *,
    heartbeats: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sequence = _rows(payload, "dedupe_sequence")
    settings = payload.get("dedupe_settings", {}) if isinstance(payload, Mapping) else {}
    settings = settings if isinstance(settings, Mapping) else {}
    deduper = ControllerHeartbeatDeduper(
        ttl_seconds=int(settings.get("ttl_seconds") or 60),
        max_entries=int(settings.get("max_entries") or 10),
    )
    reports: list[dict[str, Any]] = []
    for row in sequence:
        index = int(row.get("heartbeat_index") or 0)
        heartbeat = heartbeats[index] if 0 <= index < len(heartbeats) else None
        payload_or_id: Mapping[str, Any] | str | None = heartbeat
        if _string(row.get("event_id")):
            payload_or_id = _string(row.get("event_id"))
        report = deduper.register(payload_or_id, now=row.get("now"))
        report["sequence_id"] = _string(row.get("sequence_id")) or "dedupe_row"
        reports.append(report)
    return reports


def _validate_expected_summary(
    payload: object,
    *,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    expected = payload if isinstance(payload, Mapping) else {}
    findings: list[dict[str, Any]] = []
    for key, expected_value in expected.items():
        if summary.get(key) != expected_value:
            findings.append(
                _bundle_finding(
                    "CONTROLLER_HEARTBEAT_EXPECTED_SUMMARY_MISMATCH",
                    "Controller heartbeat expected summary did not match the generated public replay summary.",
                    subject_id=str(key),
                    subject_kind="expected_heartbeat_summary",
                )
            )
    return {
        "status": PASS if not findings else BLOCKED,
        "expected_keys": sorted(str(key) for key in expected.keys()),
        "findings": findings,
    }


def build_public_controller_heartbeat_view(
    payloads: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = payloads.get("bundle_manifest")
    manifest = manifest if isinstance(manifest, Mapping) else {}
    input_rows = _rows(payloads.get("heartbeat_inputs"), "heartbeat_inputs")
    heartbeats = [_heartbeat_from_input_row(row) for row in input_rows]
    validation_errors = [
        {
            "heartbeat_id": _string(row.get("heartbeat_id")) or f"heartbeat_{index}",
            "errors": validate_controller_heartbeat(heartbeat),
        }
        for index, (row, heartbeat) in enumerate(zip(input_rows, heartbeats))
    ]
    exact_5x5_count = sum(
        1
        for heartbeat in heartbeats
        if all(
            count_sentences(heartbeat.get(field)) == CONTROLLER_HEARTBEAT_SENTENCE_COUNT
            for field in CONTROLLER_HEARTBEAT_FIELDS
        )
    )
    heartbeat_refs = [
        controller_heartbeat_ref(
            heartbeat,
            source_path=_string(input_rows[index].get("source_path"))
            or "examples/agent_route_observability_runtime/exported_controller_heartbeat_bundle/heartbeat_inputs.json",
        )
        for index, heartbeat in enumerate(heartbeats)
    ]
    stability_rows = _event_stability_rows(heartbeats)
    schema_rows = _schema_wrap_rows(
        payloads.get("response_schemas"),
        heartbeat_refs=heartbeat_refs,
    )
    dedupe_reports = _dedupe_rows(
        payloads.get("dedupe_sequence"),
        heartbeats=heartbeats,
    )
    legacy_problem_regenerated_count = sum(
        1
        for row, heartbeat in zip(input_rows, heartbeats)
        if isinstance(row.get("existing"), Mapping)
        and _string(row["existing"].get("problem")).startswith(
            LEGACY_GENERIC_PROBLEM_PREFIX
        )
        and not _string(heartbeat.get("problem")).startswith(
            LEGACY_GENERIC_PROBLEM_PREFIX
        )
    )
    policy_validation = _validate_controller_heartbeat_policy(
        payloads.get("controller_heartbeat_policy")
    )
    leaked_keys = sorted(FORBIDDEN_PAYLOAD_KEYS & set(_walk_keys(payloads)))
    findings = [
        _bundle_finding(
            "CONTROLLER_HEARTBEAT_FORBIDDEN_PAYLOAD_KEY",
            "Controller heartbeat public replay inputs cannot include seed bodies, mission-board bodies, Work Ledger runtime bodies, transcript bodies, provider/browser/account state, credentials, cookies, secrets, or recipient-send payloads.",
            subject_id=key,
            subject_kind="controller_heartbeat_input",
        )
        for key in leaked_keys
    ]
    for item in validation_errors:
        for error in item["errors"]:
            findings.append(
                _bundle_finding(
                    "CONTROLLER_HEARTBEAT_CONTRACT_VIOLATION",
                    error,
                    subject_id=str(item["heartbeat_id"]),
                    subject_kind="controller_heartbeat",
                )
            )
    findings.extend(policy_validation["findings"])
    summary = {
        "heartbeat_input_count": len(input_rows),
        "heartbeat_count": len(heartbeats),
        "valid_heartbeat_count": sum(1 for row in validation_errors if not row["errors"]),
        "exact_5x5_count": exact_5x5_count,
        "heartbeat_ref_count": len(heartbeat_refs),
        "semantic_event_stable_count": sum(
            1 for row in stability_rows if row["updated_at_change_keeps_event_id"]
        ),
        "semantic_event_changed_count": sum(
            1 for row in stability_rows if row["semantic_wave_change_changes_event_id"]
        ),
        "legacy_problem_regenerated_count": legacy_problem_regenerated_count,
        "wrapped_schema_count": sum(1 for row in schema_rows if row["wrapped"]),
        "idempotent_wrap_count": sum(1 for row in schema_rows if row["idempotent"]),
        "dedupe_register_count": len(dedupe_reports),
        "dedupe_duplicate_count": sum(
            1 for row in dedupe_reports if bool(row.get("duplicate"))
        ),
        "source_ref_count": len(SOURCE_REFS),
        "target_ref_count": len(TARGET_REFS),
    }
    expected_validation = _validate_expected_summary(
        payloads.get("expected_heartbeat_summary"),
        summary=summary,
    )
    findings.extend(expected_validation["findings"])
    status = (
        PASS
        if not findings
        and summary["heartbeat_count"] >= 2
        and summary["valid_heartbeat_count"] == summary["heartbeat_count"]
        and summary["exact_5x5_count"] == summary["heartbeat_count"]
        and summary["heartbeat_ref_count"] == summary["heartbeat_count"]
        and summary["semantic_event_stable_count"] == summary["heartbeat_count"]
        and summary["semantic_event_changed_count"] == summary["heartbeat_count"]
        and summary["wrapped_schema_count"] >= 2
        and summary["idempotent_wrap_count"] >= 1
        and summary["dedupe_duplicate_count"] >= 1
        else BLOCKED
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "status": status,
        "bundle_id": _string(manifest.get("bundle_id"))
        or "public_controller_heartbeat_runtime_example",
        "bundle_manifest_schema_version": manifest.get("schema_version"),
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": AUTHORITY_CEILING,
        "source_refs": _strings(manifest.get("source_refs")) or SOURCE_REFS,
        "target_refs": _strings(manifest.get("target_refs")) or TARGET_REFS,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "summary": summary,
        "findings": sorted(
            findings,
            key=lambda item: (
                str(item.get("subject_kind") or ""),
                str(item.get("subject_id") or ""),
                str(item.get("error_code") or ""),
            ),
        ),
        "error_codes": sorted({str(item.get("error_code") or "") for item in findings}),
        "controller_heartbeat_schema": CONTROLLER_HEARTBEAT_SCHEMA_VERSION,
        "controller_heartbeat_ref_schema": CONTROLLER_HEARTBEAT_REF_SCHEMA_VERSION,
        "controller_heartbeats": heartbeats,
        "controller_heartbeat_refs": heartbeat_refs,
        "heartbeat_validation": validation_errors,
        "event_stability_rows": stability_rows,
        "schema_wrap_rows": schema_rows,
        "dedupe_reports": dedupe_reports,
        "policy_validation": policy_validation,
        "expected_summary_validation": expected_validation,
        "body_import_verification": _body_import_verification(),
        "forbidden_payload_keys": leaked_keys,
        "metadata_envelope_only": True,
        "body_in_receipt": False,
        "view_fingerprint": _stable_digest(
            {
                "bundle_id": _string(manifest.get("bundle_id")),
                "summary": summary,
                "heartbeat_refs": heartbeat_refs,
                "policy_id": policy_validation.get("policy_id"),
            }
        ),
    }


def load_public_controller_heartbeat_bundle(input_dir: str | Path) -> dict[str, Any]:
    root = Path(input_dir)
    return {path.stem: _load_json(path) for path in (root / name for name in INPUT_NAMES)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate-public-bundle"])
    parser.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    if args.action == "validate-public-bundle":
        view = build_public_controller_heartbeat_view(
            load_public_controller_heartbeat_bundle(args.input)
        )
        print(json.dumps(view, indent=2, sort_keys=True))
        return 0 if view.get("status") == PASS else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
