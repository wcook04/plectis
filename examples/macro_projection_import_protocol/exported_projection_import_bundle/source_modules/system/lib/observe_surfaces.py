"""
[PURPOSE]
- Teleology: Provide one shared grouped-observe continuation surface for kernel CLI, navigation, and runner readback.
- Mechanism: Pure helpers over grouped observe history payloads plus runner summaries.
- Non-goal: Session orchestration, bridge dispatch, or mutation of observe artifacts.

[INTERFACE]
- Exports: merge_observe_path_lists, observe_response_index, resolve_observe_digest_relpath, observe_resume_order, build_observe_resume_surface, build_session_resume_surface, build_observe_authoring_surface, build_grouped_observe_continuation.
- Reads: grouped observe history payloads, promoted digest or result-note paths, transaction receipts, and observe digest locations.
- Writes: None.

[FLOW]
- Orders: Normalize artifact path lists -> derive response and digest indexes -> project resume or authoring surfaces -> emit grouped continuation bundles that higher-level runtime surfaces can embed.

[DEPENDENCIES]
- Couples: system/lib/observe_runtime.py embeds these surface builders inside grouped runtime status payloads and continuation contracts.
- Couples: tools/meta/apply/run_observe_plan.py persists the grouped observe history entries that feed these projections.

[CONSTRAINTS]
- Guarantee: Resume and authoring surfaces prefer promoted typed artifacts before widening into raw response or dump files.
- When-needed: Open when a caller needs the shared continuation or readback surface for grouped observe history instead of recomputing artifact order by hand.
- Escalates-to: system/lib/observe_runtime.py; tools/meta/apply/run_observe_plan.py; system/lib/observe_apply_context.py
- Navigation-group: kernel_lib
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.observe_memory import observe_digest_path


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return items


def _dedupe_strings(values: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _transaction_receipt_path(payload: Mapping[str, Any]) -> str:
    transaction = payload.get("transaction_receipts")
    if not isinstance(transaction, Mapping):
        return ""
    return _clean_text(transaction.get("apply_loop_result_path"))


def merge_observe_path_lists(*sources: object) -> list[str]:
    """[ACTION]
    - Teleology: Merge multiple observe artifact-path sources into one stable, deduplicated read order.
    - Mechanism: Coerce each source into a string list, concatenate them, then dedupe while preserving first-seen order.
    - Reads: sources.
    - Writes: None.
    - Guarantee: Returns a list of non-blank path strings with duplicates removed in encounter order.
    - Fails: None.
    - When-needed: Open when resume or authoring surfaces need the exact path-merge rule for ordered artifact lists.
    - Escalates-to: system/lib/observe_surfaces.py::observe_response_index; system/lib/observe_runtime.py::grouped_runtime_status_payload
    """
    merged: list[str] = []
    for source in sources:
        merged.extend(_coerce_string_list(source))
    return _dedupe_strings(merged)


def _preferred_group_artifact(group: Mapping[str, Any]) -> tuple[str, str]:
    receipt_path = _clean_text(group.get("response_receipt_file"))
    if receipt_path:
        return receipt_path, "response_receipt"
    surface_path = _clean_text(group.get("response_surface_file"))
    if surface_path:
        return surface_path, "response_surface"
    response_path = _clean_text(group.get("response_file"))
    if response_path:
        return response_path, "response_markdown"
    return "", ""


def observe_response_index(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Project the per-group response metadata out of one grouped observe payload into a uniform index.
    - Mechanism: Iterate mapping-shaped groups and copy the small set of response, dump, status, and next-action fields into a list of dict rows.
    - Reads: payload["groups"].
    - Writes: None.
    - Guarantee: Returns one index row per mapping-shaped group, or an empty list when groups are absent or malformed.
    - Fails: None.
    - When-needed: Open when continuation or resume surfaces need the canonical per-group response index instead of iterating raw group payloads ad hoc.
    - Escalates-to: system/lib/observe_surfaces.py::build_observe_resume_surface; system/lib/observe_runtime.py::grouped_runtime_status_payload
    """
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        return []
    index: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        artifact_path, artifact_kind = _preferred_group_artifact(group)
        index.append(
            {
                "label": group.get("label"),
                "group_label": group.get("label"),
                "role": group.get("role"),
                "dump_file": group.get("dump_file"),
                "artifact_path": artifact_path or None,
                "artifact_kind": artifact_kind or None,
                "response_file": group.get("response_file"),
                "response_receipt_file": group.get("response_receipt_file"),
                "response_surface_file": group.get("response_surface_file"),
                "response_surface_kind": group.get("response_surface_kind"),
                "response_kind": group.get("response_kind"),
                "response_status": group.get("response_status"),
                "response_error_category": group.get("response_error_category"),
                "response_quality_status": group.get("response_quality_status"),
                "next_action": group.get("next_action"),
            }
        )
    return index


def resolve_observe_digest_relpath(root: Path, payload: Mapping[str, Any]) -> str:
    """[ACTION]
    - Teleology: Resolve the preferred repo-relative digest path for one grouped observe payload.
    - Mechanism: Prefer an explicit payload digest path; otherwise derive the canonical digest location from observe_id and return it only if the file exists.
    - Reads: payload["digest"], payload["observe_id"], and the candidate digest file on disk.
    - Writes: None.
    - Guarantee: Returns a repo-relative digest path string or an empty string when no digest is available.
    - Fails: None.
    - When-needed: Open when resume or readback surfaces need the canonical digest lookup rule before ordering artifacts.
    - Escalates-to: system/lib/observe_memory.py::observe_digest_path; system/lib/observe_surfaces.py::build_observe_resume_surface
    """
    digest = payload.get("digest")
    digest_data = digest if isinstance(digest, Mapping) else {}
    digest_path = _clean_text(digest_data.get("path"))
    if digest_path:
        return digest_path
    observe_id = _clean_text(payload.get("observe_id"))
    if not observe_id:
        return ""
    candidate = observe_digest_path(root, observe_id)
    return _rel(root, candidate) if candidate.exists() else ""


def observe_resume_order(root: Path, payload: Mapping[str, Any]) -> list[str]:
    """[ACTION]
    - Teleology: Order the stored observe artifacts in the sequence a reader should open them on resume.
    - Mechanism: Prefer digest, result note, bridge synthesis, heuristic synthesis, and explicit continuation read_paths; otherwise fall back to response and dump files.
    - Guarantee: Returns a de-duplicated list of repo-relative artifact paths, possibly empty.
    - Fails: None.
    - When-needed: Open when resume logic needs the canonical artifact-open order for a grouped observe history entry.
    - Escalates-to: system/lib/observe_surfaces.py::build_observe_resume_surface; system/lib/observe_runtime.py::grouped_runtime_status_payload
    """
    digest_path = resolve_observe_digest_relpath(root, payload)
    result_note = payload.get("result_note")
    result_note_data = result_note if isinstance(result_note, Mapping) else {}
    result_note_path = _clean_text(result_note_data.get("path"))
    bridge_synthesis = payload.get("bridge_synthesis")
    bridge_synthesis_data = bridge_synthesis if isinstance(bridge_synthesis, Mapping) else {}
    bridge_synthesis_path = _clean_text(bridge_synthesis_data.get("path"))
    heuristic_synthesis = payload.get("synthesis")
    heuristic_synthesis_data = heuristic_synthesis if isinstance(heuristic_synthesis, Mapping) else {}
    heuristic_synthesis_path = _clean_text(heuristic_synthesis_data.get("path"))
    continuation = payload.get("continuation")
    continuation_data = continuation if isinstance(continuation, Mapping) else {}
    primary_paths = merge_observe_path_lists(
        [digest_path, result_note_path, bridge_synthesis_path, heuristic_synthesis_path],
        continuation_data.get("read_paths"),
    )
    if primary_paths:
        return primary_paths

    response_index = observe_response_index(payload)
    return merge_observe_path_lists(
        [
            item.get("artifact_path")
            for item in response_index
            if isinstance(item, Mapping)
        ],
        [
            item.get("response_file")
            for item in response_index
            if isinstance(item, Mapping)
        ],
        [
            item.get("dump_file")
            for item in response_index
            if isinstance(item, Mapping)
        ],
    )


def build_observe_resume_surface(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Project one grouped observe history entry into the first-hop resume surface used by kernel and runtime callers.
    - Mechanism: Inspect dump contents, promoted digest or result-note or synthesis artifacts, transaction receipts, and continuation hints to choose mode, read_paths, preferred_artifact, and next_action.
    - Guarantee: Returns a dict describing resume mode, preferred_artifact, latest_artifact, read_paths, next_action, and related promoted artifacts.
    - Fails: None.
    - When-needed: Open when a grouped observe artifact bundle must be turned into a concrete `read this first` resume surface.
    - Escalates-to: system/lib/observe_surfaces.py::build_observe_authoring_surface; system/lib/observe_runtime.py::grouped_runtime_status_payload
    - Navigation-group: kernel_lib
    """
    dump_dir = str(payload.get("dump_dir", "")).strip()
    dump_path = (root / dump_dir).resolve() if dump_dir else None
    contents_rel = None
    meta_instruction_rel = None
    if dump_path is not None and dump_path.exists():
        contents_path = dump_path / "00_contents.json"
        if contents_path.exists():
            contents_rel = _rel(root, contents_path)
        meta_instruction_path = dump_path / "00_meta_instruction.md"
        if meta_instruction_path.exists():
            meta_instruction_rel = _rel(root, meta_instruction_path)

    continuation = payload.get("continuation")
    continuation_data = continuation if isinstance(continuation, Mapping) else {}
    continuation_read_paths = continuation_data.get("read_paths", [])
    response_paths = [
        str(path).strip()
        for path in continuation_read_paths
        if isinstance(path, str) and str(path).strip()
    ]
    response_index = observe_response_index(payload)
    if not response_paths:
        response_paths = merge_observe_path_lists(
            [
                item.get("artifact_path")
                for item in response_index
                if isinstance(item, Mapping)
            ],
            [
                item.get("response_file")
                for item in response_index
                if isinstance(item, Mapping)
            ],
        )

    dump_paths = [
        item.get("dump_file")
        for item in response_index
        if isinstance(item, Mapping)
        and isinstance(item.get("dump_file"), str)
        and item.get("dump_file", "").strip()
    ]
    ordered_resume_paths = observe_resume_order(root, payload)
    result_note = payload.get("result_note")
    result_note_data = result_note if isinstance(result_note, Mapping) else {}
    result_note_path = _clean_text(result_note_data.get("path"))
    promotion = payload.get("promotion")
    promotion_data = promotion if isinstance(promotion, Mapping) else {}
    synthesis = payload.get("synthesis")
    synthesis_data = synthesis if isinstance(synthesis, Mapping) else {}
    bridge_synthesis = payload.get("bridge_synthesis")
    bridge_synthesis_data = bridge_synthesis if isinstance(bridge_synthesis, Mapping) else {}
    digest_path = resolve_observe_digest_relpath(root, payload)
    transaction_path = _transaction_receipt_path(payload)
    transaction = payload.get("transaction_receipts")
    transaction_data = transaction if isinstance(transaction, Mapping) else {}
    run_next_action = _clean_text(payload.get("run_next_action"))
    run_latest_artifact = _clean_text(payload.get("run_latest_artifact"))

    if transaction_path and transaction_path not in ordered_resume_paths:
        ordered_resume_paths = merge_observe_path_lists([transaction_path], ordered_resume_paths)

    if transaction_path:
        mode = "transaction_receipt"
        read_paths = ordered_resume_paths
        failure_stage = _clean_text(transaction_data.get("failure_stage"))
        loop_status = _clean_text(transaction_data.get("loop_status"))
        continuation_next = str(continuation_data.get("next_action", "")).strip()
        if continuation_next:
            next_action = continuation_next
        elif failure_stage:
            next_action = (
                f"On continue, read `{transaction_path}` first and inspect the `{failure_stage}` receipt before retrying the write path."
            )
        elif loop_status == "success":
            next_action = (
                f"On continue, read `{transaction_path}` first and use the recorded receipts to reopen the successful write path."
            )
        else:
            next_action = f"On continue, read `{transaction_path}` first and follow the latest transaction receipts."
    elif digest_path:
        mode = "session_digest"
        read_paths = ordered_resume_paths
        next_action = (
            str(continuation_data.get("next_action", "")).strip()
            or f"On continue, read `{digest_path}` first and use it to orient the next bounded pass."
        )
    elif result_note_path:
        mode = "typed_result_note"
        read_paths = ordered_resume_paths or [result_note_path]
        continuation_next = run_next_action or str(continuation_data.get("next_action", "")).strip()
        if continuation_next:
            next_action = f"On continue, read `{result_note_path}` first. {continuation_next}"
        elif promotion_data.get("status") == "applied" and promotion_data.get("target_path"):
            next_action = (
                f"On continue, read `{result_note_path}` first, then inspect "
                f"`{promotion_data.get('target_path')}`."
            )
        else:
            next_action = (
                f"On continue, read `{result_note_path}` first and use the routing section to choose the next step."
            )
    elif _clean_text(bridge_synthesis_data.get("path")):
        mode = "bridge_synthesis_note"
        read_paths = ordered_resume_paths
        synthesis_path = _clean_text(bridge_synthesis_data.get("path"))
        next_action = (
            str(continuation_data.get("next_action", "")).strip()
            or f"On continue, read `{synthesis_path}` first and use it to orient the next bounded pass."
        )
    elif response_paths:
        mode = "bridge_response_files"
        read_paths = ordered_resume_paths or response_paths
        next_action = str(continuation_data.get("next_action", "")).strip()
        if not next_action:
            next_action = f"On continue, read `{response_paths[0]}` first and follow the stored NEXT_ACTION contract."
    else:
        mode = "group_dump_json"
        read_paths = ordered_resume_paths or dump_paths
        next_action = (
            f"On continue, read `{contents_rel or dump_dir or 'the dump index'}` first, then load only the batch-relevant group dump JSON."
        )

    return {
        "mode": mode,
        "history_entry_first": True,
        "contents_file": contents_rel,
        "meta_instruction_file": meta_instruction_rel,
        "read_paths": read_paths,
        "preferred_artifact": read_paths[0] if read_paths else None,
        "latest_artifact": (
            run_latest_artifact
            or digest_path
            or _clean_text(bridge_synthesis_data.get("path"))
            or result_note_path
            or (read_paths[-1] if read_paths else None)
        ),
        "next_action": next_action,
        "reference_maps": payload.get("reference_maps"),
        "promotion_target": promotion_data.get("target_path"),
        "promotion_status": promotion_data.get("status"),
        "digest_artifact": digest_path or None,
        "synthesis_artifact": synthesis_data.get("path"),
        "bridge_synthesis_artifact": bridge_synthesis_data.get("path"),
        "transaction_artifact": transaction_path or None,
        "transaction_status": transaction_data.get("status"),
        "transaction_failure_stage": transaction_data.get("failure_stage"),
    }


def build_session_resume_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Build the resume surface for an observe session manifest or runtime payload that already carries continuation and transaction state.
    - Mechanism: Prefer transaction receipts, then continuation artifacts, then primary readback artifacts, and synthesize read_paths plus a caller-facing next_action string.
    - Guarantee: Returns a dict with mode, preferred_artifact, latest_artifact, read_paths, next_action, and transaction status metadata.
    - Fails: None.
    - When-needed: Open when a session-level payload needs the same resume contract shape as grouped observe history entries.
    - Escalates-to: system/lib/observe_sessions.py::load_session_candidates; system/lib/observe_runtime.py::grouped_runtime_status_payload
    """
    continuation = payload.get("continuation")
    continuation_data = continuation if isinstance(continuation, Mapping) else {}
    readback_state = payload.get("readback_state")
    readback_data = readback_state if isinstance(readback_state, Mapping) else {}
    transaction = payload.get("transaction_receipts")
    transaction_data = transaction if isinstance(transaction, Mapping) else {}

    transaction_path = _clean_text(transaction_data.get("apply_loop_result_path"))
    continuation_paths = _coerce_string_list(continuation_data.get("read_paths"))
    readback_queue = _coerce_string_list(readback_data.get("artifact_queue"))
    read_paths = merge_observe_path_lists([transaction_path], continuation_paths, readback_queue)

    if transaction_path:
        mode = "transaction_receipt"
        preferred_artifact = transaction_path
        failure_stage = _clean_text(transaction_data.get("failure_stage"))
        if failure_stage:
            next_action = (
                str(continuation_data.get("next_action", "")).strip()
                or f"On continue, read `{transaction_path}` first and inspect the `{failure_stage}` receipt before retrying."
            )
        else:
            next_action = (
                str(continuation_data.get("next_action", "")).strip()
                or f"On continue, read `{transaction_path}` first and use the transaction receipts to reopen the write boundary."
            )
    elif _clean_text(continuation_data.get("latest_artifact")):
        mode = "continuation_artifact"
        preferred_artifact = _clean_text(continuation_data.get("latest_artifact"))
        next_action = (
            str(continuation_data.get("next_action", "")).strip()
            or f"On continue, read `{preferred_artifact}` first."
        )
    elif _clean_text(readback_data.get("primary_artifact")):
        mode = "primary_artifact"
        preferred_artifact = _clean_text(readback_data.get("primary_artifact"))
        next_action = f"On continue, read `{preferred_artifact}` first."
    else:
        mode = "session_manifest"
        preferred_artifact = None
        next_action = "On continue, read the session manifest first."

    return {
        "mode": mode,
        "preferred_artifact": preferred_artifact,
        "latest_artifact": _clean_text(continuation_data.get("latest_artifact")) or preferred_artifact,
        "read_paths": read_paths,
        "next_action": next_action,
        "transaction_status": transaction_data.get("status"),
        "transaction_failure_stage": transaction_data.get("failure_stage"),
    }


def build_observe_authoring_surface(root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Narrow a grouped observe history entry down to the artifact bundle an author should read before planning the next bounded pass.
    - Mechanism: Reuse the resume surface, prioritize typed result notes and synthesis artifacts, and keep raw response or dump files only as drilldown paths.
    - Guarantee: Returns a dict with mode, read_paths, latest_artifact, next_action, and drilldown_paths for authoring-oriented continuation.
    - Fails: None.
    - When-needed: Open when the next pass is authoring or synthesis work and the caller should stay on promoted artifacts unless a bounded gap remains.
    - Escalates-to: system/lib/observe_apply_context.py; system/lib/observe_plan_enrichment.py; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    resume_surface = build_observe_resume_surface(root, payload)
    continuation = payload.get("continuation")
    continuation_data = continuation if isinstance(continuation, Mapping) else {}
    continuation_read_paths = continuation_data.get("read_paths", [])
    response_paths = [
        str(path).strip()
        for path in continuation_read_paths
        if isinstance(path, str) and str(path).strip()
    ]
    response_index = observe_response_index(payload)
    if not response_paths:
        response_paths = merge_observe_path_lists(
            [
                item.get("artifact_path")
                for item in response_index
                if isinstance(item, Mapping)
            ],
            [
                item.get("response_file")
                for item in response_index
                if isinstance(item, Mapping)
            ],
        )

    dump_paths = [
        str(item.get("dump_file")).strip()
        for item in response_index
        if isinstance(item.get("dump_file"), str) and str(item.get("dump_file")).strip()
    ]
    result_note = payload.get("result_note")
    result_note_data = result_note if isinstance(result_note, Mapping) else {}
    result_note_path = _clean_text(result_note_data.get("path"))
    digest_path = resolve_observe_digest_relpath(root, payload)
    synthesis = payload.get("synthesis")
    synthesis_data = synthesis if isinstance(synthesis, Mapping) else {}
    bridge_synthesis = payload.get("bridge_synthesis")
    bridge_synthesis_data = bridge_synthesis if isinstance(bridge_synthesis, Mapping) else {}
    synthesis_path = _clean_text(synthesis_data.get("path"))
    promotion = payload.get("promotion")
    promotion_data = promotion if isinstance(promotion, Mapping) else {}
    run_next_action = _clean_text(payload.get("run_next_action"))
    run_latest_artifact = _clean_text(payload.get("run_latest_artifact"))

    read_paths = merge_observe_path_lists(
        [digest_path, result_note_path, _clean_text(bridge_synthesis_data.get("path")), synthesis_path],
        [
            run_latest_artifact
            if (
                run_latest_artifact
                and run_latest_artifact not in response_paths
                and run_latest_artifact not in dump_paths
            )
            else ""
        ],
    )
    if not read_paths:
        read_paths = [
            str(item).strip()
            for item in resume_surface.get("read_paths", [])
            if isinstance(item, str) and str(item).strip()
        ][:1]

    drilldown_paths = merge_observe_path_lists(
        [candidate for candidate in response_paths if candidate not in read_paths],
        [candidate for candidate in dump_paths if candidate not in read_paths],
    )

    if result_note_path:
        next_action = f"On authoring continue, read `{result_note_path}` first."
        if synthesis_path:
            next_action += f" Then read `{synthesis_path}`."
        if run_next_action:
            next_action += f" {run_next_action}"
        else:
            next_action += " Only drill into raw group responses if the typed artifact leaves a bounded gap."
        mode = "typed_result_note"
    else:
        next_action = str(resume_surface.get("next_action") or "").strip() or (
            "On authoring continue, read the primary stored artifact first and only widen into raw dumps if needed."
        )
        mode = str(resume_surface.get("mode") or "group_dump_json")

    return {
        "mode": mode,
        "history_entry_first": True,
        "read_paths": read_paths,
        "latest_artifact": read_paths[-1] if read_paths else None,
        "next_action": next_action,
        "result_note_path": result_note_path or None,
        "digest_path": digest_path or None,
        "synthesis_artifact": synthesis_path or None,
        "bridge_synthesis_artifact": _clean_text(bridge_synthesis_data.get("path")) or None,
        "drilldown_paths": drilldown_paths,
        "promotion_target": promotion_data.get("target_path"),
        "promotion_status": promotion_data.get("status"),
        "source_mode": resume_surface.get("mode"),
    }


def build_grouped_observe_continuation(
    *,
    result_note_rel: str | None,
    synthesis_summary: Mapping[str, Any],
    groups_payload: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit the continuation block that a grouped observe run writes into history after synthesis or result-note generation.
    - Mechanism: Merge result-note, synthesis, and per-group response paths into read_paths, then synthesize latest_artifact, next_action, and caller-facing hint text.
    - Guarantee: Returns a dict with read_paths, latest_result_note, latest_artifact, next_action, hint, and source.
    - Fails: None.
    - When-needed: Open when grouped observe execution needs to persist the continuation contract that downstream runtime and authoring surfaces will reopen.
    - Escalates-to: system/lib/observe_runtime.py::promote_grouped_observe_state; tools/meta/apply/run_observe_plan.py
    """
    synthesis_path = str(synthesis_summary.get("path", "")).strip()
    preferred_group_artifacts = []
    response_files = []
    for group in groups_payload:
        if not isinstance(group, Mapping):
            continue
        artifact_path, _artifact_kind = _preferred_group_artifact(group)
        if artifact_path:
            preferred_group_artifacts.append(artifact_path)
        response_file = str(group.get("response_file", "")).strip()
        if response_file:
            response_files.append(response_file)
    read_paths = merge_observe_path_lists(
        [result_note_rel or "", synthesis_path],
        preferred_group_artifacts,
        response_files,
    )
    latest_artifact = synthesis_path or result_note_rel or (read_paths[-1] if read_paths else None)
    run_next_action = str(synthesis_summary.get("run_next_action", "")).strip()
    if not run_next_action:
        run_next_action = (
            f"Read `{result_note_rel}` first, assimilate the owned notes directly, refresh the owning grounded reference surface and active seed surface, then compile the next bounded pass."
            if result_note_rel
            else "Read the latest grouped artifact first, assimilate the owned notes directly, refresh the owning grounded reference surface and active seed surface, then compile the next bounded pass."
        )
    hint_target = result_note_rel or synthesis_path or latest_artifact
    hint = run_next_action
    if hint_target:
        hint = f"On continue, read `{hint_target}` first. {run_next_action}"
    return {
        "read_paths": read_paths,
        "latest_response_file": None,
        "latest_result_note": result_note_rel,
        "latest_artifact": latest_artifact,
        "next_action": run_next_action,
        "hint": hint,
        "source": "synthesis" if synthesis_path else "result_note",
    }


__all__ = [
    "build_grouped_observe_continuation",
    "build_observe_authoring_surface",
    "build_observe_resume_surface",
    "merge_observe_path_lists",
    "observe_response_index",
    "observe_resume_order",
    "resolve_observe_digest_relpath",
]
