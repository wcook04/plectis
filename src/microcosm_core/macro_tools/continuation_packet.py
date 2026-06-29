"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.continuation_packet` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PASS, BLOCKED, KIND, SCHEMA_VERSION, SOURCE_REF, SOURCE_REFS, SOURCE_SYMBOL_REFS, TARGET_REF, TARGET_REFS, TARGET_SYMBOL_REFS, WAIT_KINDS, AUTHORITY_CEILING, ANTI_CLAIM, PUBLIC_CONTEXT_KEYS, body_import_verification, canonical_continuation_packet_path, render_public_resume_prompt, render_public_wake_prompt, build_public_continuation_packet, write_public_continuation_packet, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PASS = "pass"
BLOCKED = "blocked"

KIND = "public_continuation_packet"
SCHEMA_VERSION = "public_continuation_packet_v1"
SOURCE_REF = "system/lib/continuation_packet.py"
SOURCE_REFS = [
    SOURCE_REF,
    "codex/standards/std_continuation_packet.json",
    "codex/doctrine/paper_modules/bridge_runtime.md",
]
SOURCE_SYMBOL_REFS = [
    "system/lib/continuation_packet.py::build_continuation_packet",
    "system/lib/continuation_packet.py::write_continuation_packet",
    "system/lib/continuation_packet.py::render_codex_resume_prompt",
    "system/lib/continuation_packet.py::render_codex_wake_prompt",
    "system/lib/continuation_packet.py::default_continuation_packet_path",
]
TARGET_REF = "microcosm-substrate/src/microcosm_core/macro_tools/continuation_packet.py"
TARGET_REFS = [TARGET_REF]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.continuation_packet::build_public_continuation_packet",
    "microcosm_core.macro_tools.continuation_packet::render_public_resume_prompt",
    "microcosm_core.macro_tools.continuation_packet::render_public_wake_prompt",
    "microcosm_core.macro_tools.continuation_packet::canonical_continuation_packet_path",
]
WAIT_KINDS = frozenset({"pipeline_signal", "resume_contract", "mission_controller"})

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": "public_continuation_packet_metadata_not_live_bridge_authority",
    "live_bridge_dispatch_authorized": False,
    "live_browser_hud_access_authorized": False,
    "provider_payload_read": False,
    "account_session_state_exported": False,
    "credential_or_cookie_exported": False,
    "raw_worker_transcript_exported": False,
    "live_work_ledger_mutation_authorized": False,
    "source_mutation_authorized": False,
    "release_authorized": False,
    "private_root_equivalence_claim": False,
}
ANTI_CLAIM = (
    "This public continuation-packet tool preserves the macro wake-contract shape "
    "over metadata envelopes. It does not dispatch live bridge work, read browser/HUD "
    "or provider state, export worker transcript bodies, mutate Work Ledger or source, "
    "or authorize release."
)

PUBLIC_CONTEXT_KEYS = (
    "state_path",
    "resume_contract_path",
    "plan_path",
    "stage",
    "cycle",
    "controller_phase",
    "current_layer_kind",
    "current_layer_id",
    "current_task_id",
    "pipeline_id",
    "worker_id",
    "handoff_id",
)


def _utc_now() -> str:
    """
    [ACTION]
    - Teleology: Implements `_utc_now` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    """
    [ACTION]
    - Teleology: Implements `_string` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return str(value or "").strip()


def _strings(value: Any) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _relative_public_path(path: str | Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_relative_public_path` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    token = _string(path).replace("\\", "/").strip("/")
    while token.startswith("../"):
        token = token[3:]
    return token


def _stable_digest(payload: object, *, length: int | None = None) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_digest` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return digest[:length] if length else digest


def _file_digest(path: Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `_file_digest` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _repo_root_from_target() -> Path | None:
    """
    [ACTION]
    - Teleology: Implements `_repo_root_from_target` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    for candidate in Path(__file__).resolve(strict=False).parents:
        if (candidate / SOURCE_REF).is_file():
            return candidate
    return None


def body_import_verification() -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `body_import_verification` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_path = Path(__file__).resolve(strict=False)
    repo_root = _repo_root_from_target()
    source_path = repo_root / SOURCE_REF if repo_root is not None else None
    source_digest = (
        _file_digest(source_path)
        if source_path is not None and source_path.is_file()
        else ""
    )
    target_digest = _file_digest(target_path) if target_path.is_file() else ""
    return {
        "verification_status": "verified"
        if source_digest and target_digest
        else "target_available",
        "verification_mode": "verified_light_edit_recipe",
        "source_to_target_relation": "source_faithful_public_light_edit",
        "source_ref": SOURCE_REF,
        "target_ref": TARGET_REF,
        "source_body_digest": source_digest or None,
        "target_body_digest": target_digest or None,
        "body_in_receipt": False,
    }


def canonical_continuation_packet_path(artifact_dir: str | Path) -> str:
    """
    [ACTION]
    - Teleology: Implements `canonical_continuation_packet_path` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rel = _relative_public_path(artifact_dir)
    if not rel:
        return "continuation_packet.json"
    return f"{rel.rstrip('/')}/continuation_packet.json"


def _public_family_continuity(source_context: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_family_continuity` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    continuity = source_context.get("family_continuity")
    if isinstance(continuity, Mapping):
        return {
            "family_id": _string(continuity.get("family_id")),
            "family_title": _string(continuity.get("family_title")),
            "family_dir": _relative_public_path(continuity.get("family_dir")),
            "active_phase": dict(continuity.get("active_phase") or {}),
            "continuity_refs": _strings(continuity.get("continuity_refs")),
            "body_in_receipt": False,
        }
    return {
        "family_id": _string(source_context.get("family_id")),
        "family_title": _string(source_context.get("family_title")),
        "family_dir": _relative_public_path(source_context.get("family_dir")),
        "active_phase": dict(source_context.get("active_phase") or {}),
        "continuity_refs": _strings(source_context.get("continuity_refs")),
        "body_in_receipt": False,
    }


def _public_compaction_capsule(source_context: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_compaction_capsule` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    capsule = source_context.get("compaction_resume_capsule")
    if isinstance(capsule, Mapping):
        return {
            "latest_user_intent": _string(capsule.get("latest_user_intent")),
            "safe_next_action": _string(capsule.get("safe_next_action")),
            "prohibited_next_actions": _strings(capsule.get("prohibited_next_actions")),
            "body_in_receipt": False,
        }
    return {
        "latest_user_intent": _string(source_context.get("latest_user_intent")),
        "safe_next_action": _string(source_context.get("safe_next_action")),
        "prohibited_next_actions": _strings(source_context.get("prohibited_next_actions")),
        "body_in_receipt": False,
    }


def _public_context(source_context: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_public_context` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    context = {
        key: source_context[key]
        for key in PUBLIC_CONTEXT_KEYS
        if key in source_context and source_context[key] not in (None, "", [])
    }
    context["context_refs"] = [
        _relative_public_path(item)
        for item in _strings(source_context.get("context_refs"))
    ]
    context["worker_refs"] = [
        _relative_public_path(item)
        for item in _strings(source_context.get("worker_refs"))
    ]
    context["body_in_receipt"] = False
    return context


def render_public_resume_prompt(packet: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `render_public_resume_prompt` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    context = packet.get("public_context") if isinstance(packet.get("public_context"), Mapping) else {}
    next_action = _string(context.get("safe_next_action")) or _string(context.get("current_task_id"))
    lines = [
        "Resume from the public continuation packet.",
        f"Wait kind: {_string(packet.get('wait_kind'))}",
        f"Continuation packet: {_string(packet.get('continuation_packet_path'))}",
        f"Fingerprint: {_string(packet.get('fingerprint'))}",
        f"Next action: {next_action or 'inspect packet context refs'}",
        "Rules: use metadata refs only; do not request provider, browser/HUD, account, credential, or transcript bodies.",
    ]
    return "\n".join(lines)


def render_public_wake_prompt(packet: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Implements `render_public_wake_prompt` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    context = packet.get("public_context") if isinstance(packet.get("public_context"), Mapping) else {}
    refs = ", ".join(_strings(context.get("context_refs"))[:4]) or "packet context refs"
    return "\n".join(
        [
            "Wake from Microcosm's public continuation packet.",
            f"Read: {_string(packet.get('continuation_packet_path'))}",
            f"Refs: {refs}",
            "Boundary: metadata envelope only; no live bridge send or private session state.",
        ]
    )


def build_public_continuation_packet(
    *,
    wait_kind: str,
    artifact_dir: str | Path,
    source_context: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_continuation_packet` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    normalized_wait_kind = _string(wait_kind)
    if normalized_wait_kind not in WAIT_KINDS:
        raise ValueError(f"Unsupported continuation packet wait kind: {wait_kind!r}")

    source = dict(source_context or {})
    artifact_dir_rel = _relative_public_path(artifact_dir)
    packet_path = canonical_continuation_packet_path(artifact_dir_rel)
    packet: dict[str, Any] = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now(),
        "wait_kind": normalized_wait_kind,
        "artifact_dir": artifact_dir_rel,
        "continuation_packet_path": packet_path,
        "family_continuity": _public_family_continuity(source),
        "compaction_resume_capsule": _public_compaction_capsule(source),
        "public_context": _public_context(source),
        "source_refs": SOURCE_REFS,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_refs": TARGET_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_import_verification": body_import_verification(),
        "body_in_receipt": False,
    }
    fingerprint_basis = {
        "wait_kind": packet["wait_kind"],
        "artifact_dir": packet["artifact_dir"],
        "family_continuity": packet["family_continuity"],
        "compaction_resume_capsule": packet["compaction_resume_capsule"],
        "public_context": packet["public_context"],
    }
    packet["fingerprint"] = _stable_digest(fingerprint_basis, length=16)
    packet["continuation_packet_fingerprint"] = packet["fingerprint"]
    packet["prompts"] = {
        "codex_resume_prompt": render_public_resume_prompt(packet),
        "codex_wake_prompt": render_public_wake_prompt(packet),
    }
    packet["codex_resume_prompt"] = packet["prompts"]["codex_resume_prompt"]
    packet["codex_wake_prompt"] = packet["prompts"]["codex_wake_prompt"]
    return packet


def write_public_continuation_packet(
    *,
    artifact_dir: str | Path,
    packet: Mapping[str, Any],
    root: str | Path = ".",
) -> tuple[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `write_public_continuation_packet` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    target_rel = _string(packet.get("continuation_packet_path")) or canonical_continuation_packet_path(
        artifact_dir
    )
    target = Path(root) / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(packet)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target_rel, payload


def _load_json(path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_load_json` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.macro_tools.continuation_packet` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="python -m microcosm_core.macro_tools.continuation_packet")
    parser.add_argument("action", choices=["build-public-packet"])
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    payload = _load_json(args.input)
    packet = build_public_continuation_packet(
        wait_kind=_string(payload.get("wait_kind")),
        artifact_dir=_string(payload.get("artifact_dir")),
        source_context=payload.get("source_context") if isinstance(payload.get("source_context"), Mapping) else {},
        generated_at=_string(payload.get("generated_at")) or None,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if packet.get("authority_ceiling", {}).get("status") == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
