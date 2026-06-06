"""
[PURPOSE]
- Teleology: Compile observe-session artifacts back into kernel-standard apply operations and deterministic post-apply verification receipts.
- Mechanism: Resolve a session manifest, rank candidate response artifacts, parse surfaced JSON or diffs, normalize operations into the standard apply contract, and run deterministic quality gates before any live apply step.

[INTERFACE]
- Exports: load_session_manifest, compile_session_manifest_to_apply_plan, run_miner_after_apply, run_compiled_session_manifest.
- Reads: Session manifests, response artifacts, surfaced response sidecars, std-apply capability metadata, and Python documentation tree artifacts needed for deterministic quality gates.
- Writes: None directly; callers receive compiled plans or miner receipts for downstream apply paths.

[FLOW]
- Orders: load_session_manifest() resolves the source manifest -> compile_session_manifest_to_apply_plan() selects artifact candidates and validates normalized operations -> run_compiled_session_manifest() forwards the compiled plan into the runtime apply surface -> run_miner_after_apply() re-audits Python documentation after successful apply runs when requested.
- When-needed: Open when an agent needs to turn observe-session outputs into a kernel-ready apply plan or explain why compilation returned blocked status.
- Escalates-to: tools/meta/apply/observe_compiler.py::compile_session_manifest_to_apply_plan; tools/meta/apply.py::run; system/lib/python_documentation_tree.py::deterministic_quality_gates.
- Navigation-group: observe_apply.

[DEPENDENCIES]
- Couples: tools/meta/apply.py supplies the runtime apply compiler/executor that consumes the normalized plan this module emits.
- Couples: system/lib/python_documentation_tree.py changes compile outcomes because deterministic_quality_gates() can block operations even after parsing succeeds.
- Couples: system/lib/response_surfaces.py affects which surfaced payloads are treated as compileable apply candidates.

[CONSTRAINTS]
- Guarantee: Successful compilation returns operations already normalized for the standard apply contract and screened through deterministic gates.
- Orders: Preferred synthesis/evaluation artifacts win before probe aggregation and generic fallback artifacts.
- Non-goal: This module does not mutate source files itself; it only compiles and validates the artifacts that downstream apply surfaces may execute.
"""

from __future__ import annotations

import json
import re
import ast
from pathlib import Path
from typing import Any, Mapping

from system.lib.json_payloads import extract_json_value, json_candidate_blocks
from system.lib.markdown_routing import extract_section
from system.lib.observe_resilience import SEMANTIC_DEGRADED_STATUSES
from system.lib.response_surfaces import (
    is_surface_response,
    parse_surface_response,
    resolve_response_surface,
    response_surface_sidecar_path,
)
from system.lib.utils import resolve_root
from system.server.inspector import InspectorService
from tools.meta import apply as meta_apply
from tools.meta.miner import _collect_failures
from system.lib.python_documentation_tree import (
    build_file_entry,
    build_scope_summaries,
    deterministic_quality_gates,
)
from system.lib.python_scope_query import python_scope_exists


def _repo_root(root_hint: str | Path | None = None) -> Path:
    return Path(resolve_root(root_hint)).resolve()


def _dedupe_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _resolve_session_manifest_path(session_manifest_path: str | Path) -> Path:
    candidate = Path(session_manifest_path)
    if candidate.is_absolute():
        return candidate.resolve()
    if candidate.exists():
        return candidate.resolve()
    return (_repo_root() / candidate).resolve()


def load_session_manifest(session_manifest_path: str | Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load one observe-session manifest with a stable on-disk path attached for downstream compilation steps.
    - Mechanism: Resolve relative or absolute input, decode JSON, require a top-level object, and add `_session_manifest_path` to the returned mapping.
    - Reads: _resolve_session_manifest_path() and the manifest JSON file.
    - Guarantee: Returns a dict-backed manifest payload that includes `_session_manifest_path`.
    - Fails: Raises ValueError when the manifest path is missing, malformed JSON, or not a JSON object.
    - When-needed: Open when a caller needs the canonical manifest payload before candidate artifact selection or apply-plan compilation.
    - Escalates-to: tools/meta/apply/observe_session.py::SessionArtifactWriterImpl.write_manifest; tools/meta/apply/observe_compiler.py::compile_session_manifest_to_apply_plan.
    """
    manifest_path = _resolve_session_manifest_path(session_manifest_path)
    if not manifest_path.exists():
        raise ValueError(f"session manifest not found: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"session manifest is not valid JSON: {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("session manifest must decode to a JSON object.")
    payload["_session_manifest_path"] = str(manifest_path)
    return payload


def _manifest_repo_root(manifest: Mapping[str, Any], *, repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return _repo_root(repo_root)
    manifest_path = str(manifest.get("_session_manifest_path") or "").strip()
    if manifest_path:
        resolved_manifest = Path(manifest_path).resolve()
        for parent in [resolved_manifest.parent, *resolved_manifest.parents]:
            if (parent / "master_config.json").exists():
                return parent.resolve()
        return _repo_root(resolved_manifest.parent)
    return _repo_root()


def _artifact_candidates(manifest: Mapping[str, Any], *, prefer_artifact: str | None = None) -> list[str]:
    readback_state = manifest.get("readback_state") if isinstance(manifest.get("readback_state"), Mapping) else {}
    continuation = manifest.get("continuation") if isinstance(manifest.get("continuation"), Mapping) else {}
    response_index = _response_index_entries(manifest)

    candidates: list[str] = []
    if str(prefer_artifact or "").strip():
        candidates.append(str(prefer_artifact).strip())

    role_priority = {"synthesis": 0, "evaluation": 1, "probe": 2, "advisory": 3}
    ordered_index = sorted(
        response_index,
        key=lambda item: (
            role_priority.get(str(item.get("role") or "").strip(), 99),
            str(item.get("group_label") or "").strip(),
        ),
    )
    for item in ordered_index:
        artifact_path = str(item.get("artifact_path") or "").strip()
        if artifact_path:
            candidates.append(artifact_path)

    primary_artifact = str(readback_state.get("primary_artifact") or "").strip()
    if primary_artifact:
        candidates.append(primary_artifact)

    artifact_queue = readback_state.get("artifact_queue")
    if isinstance(artifact_queue, list):
        candidates.extend(str(item).strip() for item in artifact_queue if str(item).strip())

    latest_artifact = str(continuation.get("latest_artifact") or "").strip()
    if latest_artifact:
        candidates.append(latest_artifact)

    read_paths = continuation.get("read_paths")
    if isinstance(read_paths, list):
        candidates.extend(str(item).strip() for item in read_paths if str(item).strip())
    return _dedupe_strings(candidates)


def _resolve_repo_path(repo_root: Path, token: str) -> Path:
    candidate = Path(token)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _contract_groups_by_label(manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    contract_validation = (
        manifest.get("contract_validation")
        if isinstance(manifest.get("contract_validation"), Mapping)
        else {}
    )
    groups = contract_validation.get("groups") if isinstance(contract_validation.get("groups"), list) else []
    by_label: dict[str, dict[str, Any]] = {}
    for item in groups:
        if not isinstance(item, Mapping):
            continue
        label = _string(item.get("group_label"))
        if label:
            by_label[label] = dict(item)
    return by_label


def _response_index_entries(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    response_index = manifest.get("response_index") if isinstance(manifest.get("response_index"), list) else []
    return [dict(item) for item in response_index if isinstance(item, Mapping)]


def _json_block_candidates(text: str) -> list[str]:
    return json_candidate_blocks(text)


_STRUCTURED_OBSERVE_MARKDOWN_TOKENS = (
    "# Observe Group Response",
    "# Observe Result",
    "# Combined Observe Responses",
)
_APPLY_SECTION_TITLES = ("APPLY_PLAN_JSON", "OPERATIONS", "PATCH", "DIFF")
_STRUCTURED_RESPONSE_SECTION_TITLES = ("RESPONSE", "FINAL RESPONSE")


_FENCED_DIFF_RE = re.compile(r"```(?:diff|patch)\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _diff_block_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in _FENCED_DIFF_RE.finditer(str(text or "")):
        candidate = str(match.group(1) or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def _string(value: Any) -> str:
    return str(value or "").strip()


def _looks_like_structured_observe_markdown(text: str) -> bool:
    head = str(text or "")[:2000]
    return any(token in head for token in _STRUCTURED_OBSERVE_MARKDOWN_TOKENS)


def _parse_operations_from_candidate(candidate: str, *, repo_root: Path) -> list[dict[str, Any]] | None:
    stripped = str(candidate or "").strip()
    if not stripped:
        return None
    if stripped.startswith("--- "):
        compiled = meta_apply.compile_apply_plan(
            {"unified_diff": stripped},
            root_hint=str(repo_root),
        )
        operations = compiled.get("operations")
        if isinstance(operations, list):
            return [dict(item) for item in operations if isinstance(item, Mapping)]
        return None
    payload = json.loads(stripped)
    return _coerce_operations(payload, repo_root=repo_root)


def _section_operation_candidates(text: str, *, repo_root: Path) -> list[dict[str, Any]] | None:
    section_errors: list[str] = []
    saw_apply_section = False
    for title in _APPLY_SECTION_TITLES:
        section = extract_section(text, title) or ""
        if not section.strip():
            continue
        saw_apply_section = True
        section_candidates = [*_diff_block_candidates(section), *_json_block_candidates(section)]
        if not section_candidates:
            section_errors.append(f"{title}: no diff/JSON candidates found")
            continue
        for candidate in section_candidates:
            try:
                operations = _parse_operations_from_candidate(candidate, repo_root=repo_root)
            except Exception as exc:
                section_errors.append(f"{title}: {exc}")
                continue
            if operations is not None:
                return operations
        section_errors.append(f"{title}: no standard apply operations were found")
    if saw_apply_section:
        detail = "; ".join(section_errors[:3])
        raise ValueError(
            "no standard apply operations were found in declared apply sections"
            + (f" ({detail})" if detail else "")
        )
    return None


def _structured_observe_response_operations(text: str, *, repo_root: Path) -> list[dict[str, Any]] | None:
    errors: list[str] = []
    saw_response_section = False
    for title in _STRUCTURED_RESPONSE_SECTION_TITLES:
        section = extract_section(text, title) or ""
        if not section.strip():
            continue
        saw_response_section = True
        section_candidates: list[str] = []
        stripped_section = section.strip()
        section_candidates.append(stripped_section)
        section_candidates.extend(_diff_block_candidates(section))
        section_candidates.extend(_json_block_candidates(section))
        if not section_candidates:
            errors.append(f"{title}: no diff/JSON candidates found")
            continue
        seen_candidates: set[str] = set()
        for candidate in section_candidates:
            token = str(candidate or "").strip()
            if not token or token in seen_candidates:
                continue
            seen_candidates.add(token)
            try:
                operations = _parse_operations_from_candidate(token, repo_root=repo_root)
            except Exception as exc:
                try:
                    repaired_payload = extract_json_value(token)
                except Exception:
                    errors.append(f"{title}: {exc}")
                    continue
                if isinstance(repaired_payload, Mapping) and _string(repaired_payload.get("op")):
                    return [dict(repaired_payload)]
                operations = _coerce_operations(repaired_payload, repo_root=repo_root)
            if operations is not None:
                return operations
        errors.append(f"{title}: no standard apply operations were found")
    if saw_response_section:
        detail = "; ".join(errors[:3])
        raise ValueError(
            "no standard apply operations were found in structured observe response sections"
            + (f" ({detail})" if detail else "")
        )
    return None


def _parse_probe_operations_from_artifact(artifact_path: Path, *, repo_root: Path) -> list[dict[str, Any]]:
    try:
        return _parse_operations_from_artifact(artifact_path, repo_root=repo_root)
    except Exception:
        if artifact_path.suffix.lower() != ".md":
            raise
        sidecar_path = response_surface_sidecar_path(artifact_path)
        if not sidecar_path.exists():
            raise
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        operations = payload.get("payload", {}).get("operations") if isinstance(payload.get("payload"), Mapping) else None
        if isinstance(operations, Mapping):
            return [dict(operations)]
        raise


def _surface_compile_apply_candidates(
    payload: Any,
    *,
    response_surface: Mapping[str, Any] | None = None,
) -> list[Any]:
    if not isinstance(payload, Mapping) or not isinstance(response_surface, Mapping):
        return []
    candidates: list[Any] = []
    fields = [
        *(response_surface.get("required_fields", []) if isinstance(response_surface.get("required_fields"), list) else []),
        *(response_surface.get("optional_fields", []) if isinstance(response_surface.get("optional_fields"), list) else []),
    ]
    for field in fields:
        if not isinstance(field, Mapping):
            continue
        if _string(field.get("merge_mode")) != "compile_apply":
            continue
        field_id = _string(field.get("field_id"))
        if not field_id or field_id not in payload:
            continue
        value = payload.get(field_id)
        if isinstance(value, Mapping):
            candidates.append(dict(value))
            continue
        if isinstance(value, list):
            candidates.append({"operations": value})
            continue
        if isinstance(value, str) and value.strip():
            field_format = _string(field.get("format")).lower()
            value_shape = _string(field.get("value_shape")).lower()
            if field_format in {"diff", "patch", "unified_diff"} or value_shape in {"diff", "patch", "unified_diff"}:
                candidates.append({"unified_diff": value})
            else:
                candidates.append({field_id: value})
    return candidates


def _surface_payload_candidates(
    payload: Any,
    *,
    response_surface: Mapping[str, Any] | None = None,
) -> list[Any]:
    candidates: list[Any] = []
    if isinstance(payload, Mapping):
        payload_dict = dict(payload)
        candidates.extend(_surface_compile_apply_candidates(payload_dict, response_surface=response_surface))
        inner_payload = payload_dict.get("payload")
        if inner_payload is not None:
            candidates.extend(_surface_compile_apply_candidates(inner_payload, response_surface=response_surface))
            candidates.append(inner_payload)
        candidates.append(payload_dict)
        for key in ("apply_plan", "apply_plan_json", "plan"):
            value = payload_dict.get(key)
            if value is not None:
                candidates.append(value)
        for key in ("operations",):
            value = payload_dict.get(key)
            if value is not None:
                candidates.append({"operations": value})
        for key in ("unified_diff", "diff", "patch"):
            value = payload_dict.get(key)
            if isinstance(value, str) and value.strip():
                candidates.append({key: value})
    elif isinstance(payload, list):
        candidates.append(payload)
    return candidates


def _resolve_surface_contract(payload: Any, *, repo_root: Path) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    embedded = payload.get("response_surface")
    if isinstance(embedded, Mapping):
        resolved = resolve_response_surface(repo_root, dict(embedded))
        if isinstance(resolved, Mapping):
            return resolved
    surface_kind = _string(payload.get("surface_kind"))
    response_kind = _string(payload.get("response_kind"))
    if surface_kind or response_kind:
        resolved = resolve_response_surface(
            repo_root,
            {
                "surface_kind": surface_kind or None,
                "response_kind": response_kind or None,
            },
        )
        if isinstance(resolved, Mapping):
            return resolved
    if response_kind:
        resolved = resolve_response_surface(repo_root, response_kind)
        if isinstance(resolved, Mapping):
            return resolved
    if surface_kind:
        resolved = resolve_response_surface(repo_root, surface_kind)
        if isinstance(resolved, Mapping):
            return resolved
    return None


def _coerce_operations_from_surface_payload(
    payload: Any,
    *,
    repo_root: Path,
    response_surface: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]] | None:
    active_surface = response_surface if isinstance(response_surface, Mapping) else _resolve_surface_contract(payload, repo_root=repo_root)
    for candidate in _surface_payload_candidates(payload, response_surface=active_surface):
        operations = _coerce_operations(candidate, repo_root=repo_root)
        if operations is not None:
            return operations
        if isinstance(candidate, Mapping):
            for diff_key in ("unified_diff", "diff", "patch"):
                diff_text = candidate.get(diff_key)
                if not isinstance(diff_text, str) or not diff_text.strip():
                    continue
                try:
                    compiled = meta_apply.compile_apply_plan(
                        {diff_key: diff_text},
                        root_hint=str(repo_root),
                    )
                except Exception:
                    continue
                compiled_ops = compiled.get("operations")
                if isinstance(compiled_ops, list):
                    return [dict(item) for item in compiled_ops if isinstance(item, Mapping)]
    return None


def _coerce_operations(payload: Any, *, repo_root: Path) -> list[dict[str, Any]] | None:
    if isinstance(payload, Mapping):
        if payload.get("__grouped") is True:
            return None
        operations = payload.get("operations")
        if isinstance(operations, list):
            coerced = [dict(item) for item in operations if isinstance(item, Mapping)]
            return coerced or None
        nested_plan = payload.get("plan")
        if isinstance(nested_plan, Mapping):
            nested_operations = nested_plan.get("operations")
            if isinstance(nested_operations, list):
                coerced = [dict(item) for item in nested_operations if isinstance(item, Mapping)]
                return coerced or None
        try:
            compiled = meta_apply.compile_apply_plan(dict(payload), root_hint=str(repo_root))
        except Exception:
            return None
        compiled_ops = compiled.get("operations")
        if isinstance(compiled_ops, list):
            coerced = [dict(item) for item in compiled_ops if isinstance(item, Mapping)]
            return coerced or None
        return None
    if isinstance(payload, list):
        if payload and all(isinstance(item, Mapping) for item in payload):
            return [dict(item) for item in payload]
    return None


def _parse_operations_from_artifact(artifact_path: Path, *, repo_root: Path) -> list[dict[str, Any]]:
    text = artifact_path.read_text(encoding="utf-8")
    errors: list[str] = []
    looks_structured_observe = artifact_path.suffix.lower() == ".md" and _looks_like_structured_observe_markdown(text)
    if artifact_path.suffix.lower() == ".md":
        sidecar_path = response_surface_sidecar_path(artifact_path)
        if sidecar_path.exists():
            try:
                sidecar_payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{sidecar_path}: invalid surface payload ({exc})")
            else:
                operations = _coerce_operations_from_surface_payload(
                    sidecar_payload,
                    repo_root=repo_root,
                )
                if operations is not None:
                    return operations
                errors.append(f"{sidecar_path}: no standard apply operations were found in surfaced payload")
        try:
            operations = _section_operation_candidates(text, repo_root=repo_root)
        except Exception as exc:
            errors.append(f"{artifact_path}: {exc}")
        else:
            if operations is not None:
                return operations
        if looks_structured_observe:
            try:
                operations = _structured_observe_response_operations(text, repo_root=repo_root)
            except Exception as exc:
                errors.append(f"{artifact_path}: {exc}")
            else:
                if operations is not None:
                    return operations

    if is_surface_response(text):
        try:
            surfaced = parse_surface_response(text)
        except Exception as exc:
            errors.append(f"{artifact_path}: invalid surfaced response ({exc})")
        else:
            inline_surface = _resolve_surface_contract(surfaced, repo_root=repo_root)
            operations = _coerce_operations_from_surface_payload(
                surfaced.get("payload"),
                repo_root=repo_root,
                response_surface=inline_surface,
            )
            if operations is not None:
                return operations
            errors.append(f"{artifact_path}: no standard apply operations were found in surfaced payload")
    if looks_structured_observe:
        raise ValueError(
            "no standard apply operations were found in structured observe markdown"
            + (f" ({'; '.join(errors[:3])})" if errors else "")
        )
    for candidate in _diff_block_candidates(text):
        try:
            compiled = meta_apply.compile_apply_plan(
                {"unified_diff": candidate},
                root_hint=str(repo_root),
            )
        except Exception as exc:
            errors.append(f"{artifact_path}: invalid fenced diff candidate ({exc})")
            continue
        operations = compiled.get("operations")
        if isinstance(operations, list):
            return [dict(item) for item in operations if isinstance(item, Mapping)]
    for candidate in _json_block_candidates(text):
        if candidate.startswith(("{", "[")):
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError as exc:
                errors.append(f"{artifact_path}: invalid JSON candidate ({exc})")
                continue
            operations = _coerce_operations(payload, repo_root=repo_root)
            if operations is not None:
                return operations
            continue
        if candidate.startswith("--- "):
            try:
                compiled = meta_apply.compile_apply_plan(
                    {"unified_diff": candidate},
                    root_hint=str(repo_root),
                )
            except Exception as exc:
                errors.append(f"{artifact_path}: invalid diff candidate ({exc})")
                continue
            operations = compiled.get("operations")
            if isinstance(operations, list):
                return [dict(item) for item in operations if isinstance(item, Mapping)]
    if artifact_path.suffix.lower() == ".json":
        payload = json.loads(text)
        operations = _coerce_operations(payload, repo_root=repo_root)
        if operations is not None:
            return operations
        if isinstance(payload, Mapping):
            operations_value = payload.get("operations")
            if operations_value is not None:
                if isinstance(operations_value, list) and not all(isinstance(item, Mapping) for item in operations_value):
                    raise ValueError("operations field was malformed in JSON payload")
                if not isinstance(operations_value, (list, Mapping)):
                    raise ValueError("operations field was malformed in JSON payload")
                raise ValueError("operations field was present but contained no usable apply operations")
            if payload.get("__grouped") is True:
                raise ValueError("grouped observe aggregate contained no usable apply operations")
        raise ValueError("no usable apply operations were found in JSON payload")
    raise ValueError(
        "no standard apply operations were found in "
        f"{artifact_path}"
        + (f" ({'; '.join(errors[:3])})" if errors else "")
    )


def _allowed_ops_spec(repo_root: Path) -> dict[str, Any]:
    std_path = repo_root / "codex" / "standards" / "std_apply.json"
    if not std_path.exists():
        return {}
    payload = json.loads(std_path.read_text(encoding="utf-8"))
    allowed_ops = payload.get("allowed_ops")
    return dict(allowed_ops) if isinstance(allowed_ops, Mapping) else {}


def _validate_standard_operations(repo_root: Path, operations: list[dict[str, Any]]) -> None:
    allowed_ops = _allowed_ops_spec(repo_root)
    if not operations:
        raise ValueError("compiled apply plan is empty.")
    if not allowed_ops:
        raise ValueError("std_apply.json did not expose allowed_ops.")
    for index, operation in enumerate(operations):
        op_name = str(operation.get("op") or "").strip()
        if op_name not in allowed_ops:
            raise ValueError(f"compiled operation {index} uses unknown op '{op_name}'.")
        required_fields = allowed_ops.get(op_name, {}).get("required", [])
        for field_name in required_fields:
            if field_name not in operation or operation[field_name] in {None, ""}:
                raise ValueError(
                    f"compiled operation {index} ({op_name}) is missing required field '{field_name}'."
                )


def _normalize_docstring_scope(
    *,
    repo_root: Path,
    target: str,
    scope: str,
    cache: dict[str, ast.AST | None],
) -> str:
    clean_scope = _string(scope)
    if not clean_scope or clean_scope == "module":
        return clean_scope

    target_path = _resolve_repo_path(repo_root, target)
    tree: ast.AST | None = None
    if target_path.exists() and target_path.suffix.lower() == ".py":
        cache_key = str(target_path)
        if cache_key not in cache:
            try:
                cache[cache_key] = ast.parse(target_path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                cache[cache_key] = None
        tree = cache.get(cache_key)

    normalized_scope = meta_apply.normalize_python_scope_selector(clean_scope, tree=tree)
    if not normalized_scope or normalized_scope == clean_scope:
        return clean_scope
    if normalized_scope.startswith("method:"):
        return normalized_scope
    if clean_scope.startswith(("class ", "function ", "func ", "method ")):
        return normalized_scope
    if ":" in clean_scope:
        return clean_scope
    if "." in clean_scope:
        return normalized_scope
    if normalized_scope.startswith("function:"):
        return f"func:{normalized_scope.split(':', 1)[1]}"
    return normalized_scope


def _normalize_docstring_target_scope_pair(
    *,
    repo_root: Path,
    operation: Mapping[str, Any],
    cache: dict[str, ast.AST | None],
) -> tuple[str, str]:
    target = _string(operation.get("target") or operation.get("path") or operation.get("file"))
    scope = _string(operation.get("scope"))
    if ".py::" not in target:
        return target, scope
    target_path, symbol = target.split("::", 1)
    target_path = _string(target_path)
    symbol = _string(symbol)
    if not target_path:
        return target, scope
    normalized_scope = scope
    if symbol:
        scope_token = scope.lower()
        if scope_token in {"", "function", "func"}:
            normalized_scope = f"method:{symbol}" if "." in symbol else f"func:{symbol}"
        elif scope_token == "method":
            normalized_scope = f"method:{symbol}" if "." in symbol else scope
        elif scope_token == "class":
            normalized_scope = f"class:{symbol}"
    return target_path, normalized_scope


def _run_deterministic_gates(
    operations: list[dict[str, Any]],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Run deterministic quality checks on compiled operations before apply.
      Returns a list of gate results. Defect/critical results block compilation.
    - Mechanism: Checks op type, target existence, AST-addressable scope resolution,
      and required tag content. Uses real AST parsing to verify scopes exist.
    """
    import ast as _ast
    results: list[dict[str, Any]] = []
    scope_gated_ops = {"update_docstring", "inject_tag"}
    # Cache parsed ASTs per file
    ast_cache: dict[str, _ast.Module | None] = {}

    def _parse_file(path: Path) -> _ast.Module | None:
        key = str(path)
        if key not in ast_cache:
            try:
                ast_cache[key] = _ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                ast_cache[key] = None
        return ast_cache[key]

    # The scope-existence predicate previously lived inline as `_scope_exists_in_ast`.
    # It was lifted to `system/lib/python_scope_query.py::python_scope_exists` so audit
    # surfaces (this gate, future entrypoint_health / navigation_surface_audit consumers)
    # share one named primitive instead of duplicating the AST walk. Parity is pinned by
    # `test_observe_compiler.py::test_run_deterministic_gates_scope_existence_matrix`.

    for i, op in enumerate(operations):
        op_name = op.get("op", "")
        target = op.get("target", "") or op.get("path", "") or op.get("file", "")
        scope = op.get("scope", "")

        # Gate 1: Target file must exist
        target_path = repo_root / target if target else None
        if not target_path or not target_path.exists():
            results.append({"op_index": i, "gate": "target_exists", "severity": "defect",
                            "detail": f"Target file does not exist: {target}"})
            continue

        if op_name not in scope_gated_ops:
            continue

        # Gate 2: Scope must be non-empty for scope-addressable ops only
        if not scope:
            results.append({"op_index": i, "gate": "scope_present", "severity": "defect",
                            "detail": f"Operation on {target} has empty scope"})
            continue

        # Gate 3: Scope must be AST-addressable for scope-addressable ops only
        normalized_scope = scope
        if target_path.suffix == ".py":
            tree = _parse_file(target_path)
            if tree is not None:
                normalized_scope = meta_apply.normalize_python_scope_selector(scope, tree=tree)
            if tree is not None and not python_scope_exists(tree, scope):
                results.append({"op_index": i, "gate": "scope_addressable", "severity": "defect",
                                "detail": f"Scope '{scope}' not found in AST of {target}"})

        # Gate 4: Required tag content for update_docstring
        if op_name == "update_docstring":
            content = op.get("docstring", "") or op.get("content", "")
            if content and normalized_scope == "module" and "[PURPOSE]" not in content:
                results.append({"op_index": i, "gate": "module_purpose_tag", "severity": "warning",
                                "detail": f"Module docstring for {target} missing [PURPOSE] tag"})
            elif content and normalized_scope.startswith(("function:", "func:", "method:")) and "[ACTION]" not in content:
                results.append({"op_index": i, "gate": "action_tag", "severity": "warning",
                                "detail": f"Docstring for {normalized_scope} in {target} missing [ACTION] tag"})
            elif content and normalized_scope.startswith("class:") and "[ROLE]" not in content:
                results.append({"op_index": i, "gate": "role_tag", "severity": "warning",
                                "detail": f"Class docstring for {normalized_scope} in {target} missing [ROLE] tag"})

    # Gate 5: Substrate-level quality gates from scope summaries
    # Build scope summaries per unique Python target file, then match operations
    # to their scope summaries and run deterministic_quality_gates.
    py_targets = {
        (op.get("target", "") or op.get("path", "") or op.get("file", ""))
        for op in operations
        if (op.get("target", "") or op.get("path", "") or op.get("file", "")).endswith(".py")
    }
    scope_summary_cache: dict[str, list[dict[str, Any]]] = {}
    for target_rel in py_targets:
        target_path = repo_root / target_rel
        if not target_path.exists():
            continue
        try:
            entry = build_file_entry(target_path, repo_root=repo_root)
            scope_summary_cache[target_rel] = build_scope_summaries(entry)
        except Exception:
            pass  # File parse errors already caught by gates 2+4

    substrate_gated_ops = {"inject_tag"}

    for i, op in enumerate(operations):
        target = op.get("target", "") or op.get("path", "") or op.get("file", "")
        scope = op.get("scope", "")
        if op.get("op", "") not in substrate_gated_ops or not target or not scope or target not in scope_summary_cache:
            continue
        normalized_scope = scope
        target_path = repo_root / target
        tree = _parse_file(target_path) if target_path.suffix == ".py" else None
        if tree is not None:
            normalized_scope = meta_apply.normalize_python_scope_selector(scope, tree=tree)
        # Find the matching scope summary for this operation's scope
        summaries = scope_summary_cache[target]
        matched = None
        for s in summaries:
            sid = s.get("symbol_id", "")
            name = s.get("name", "")
            # Match by scope convention: "func:foo" matches name "foo",
            # "method:Cls.bar" matches name "bar" with owner "Cls"
            if normalized_scope.startswith(("function:", "func:")) and name == normalized_scope.split(":", 1)[-1].strip():
                matched = s
                break
            if normalized_scope.startswith("method:") and f".{name}" in normalized_scope:
                matched = s
                break
        if matched is None:
            continue
        substrate_gates = deterministic_quality_gates(matched)
        for gate in substrate_gates:
            results.append({
                "op_index": i,
                "gate": f"substrate_{gate['gate']}",
                "severity": gate["severity"],
                "detail": gate["detail"],
            })

    return results


def _normalize_operations_for_apply(
    repo_root: Path,
    operations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scope_cache: dict[str, ast.AST | None] = {}
    triple_double_escape = '\\"' * 3
    triple_single_escape = "\\'" * 3
    normalized: list[dict[str, Any]] = []
    for operation in operations:
        updated = dict(operation)
        op_name = _string(updated.get("op"))
        if op_name in {"update_docstring", "inject_tag"}:
            target, scope = _normalize_docstring_target_scope_pair(
                repo_root=repo_root,
                operation=updated,
                cache=scope_cache,
            )
            if target:
                updated["target"] = target
            if target and scope:
                updated["scope"] = _normalize_docstring_scope(
                    repo_root=repo_root,
                    target=target,
                    scope=scope,
                    cache=scope_cache,
                )
            content = updated.get("content")
            if not isinstance(content, str) or not content:
                docstring = updated.pop("docstring", None)
                if isinstance(docstring, str) and docstring:
                    updated["content"] = docstring
                    content = docstring
            if isinstance(content, str) and content:
                updated["content"] = (
                    content
                    .replace('"""', triple_double_escape)
                    .replace("'''", triple_single_escape)
                )
        normalized.append(updated)
    return normalized


def _operation_identity(operation: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _string(operation.get("op")),
        _string(operation.get("target") or operation.get("path") or operation.get("file")),
        _string(operation.get("scope")),
        _string(operation.get("search")),
        _string(operation.get("name")),
        _string(operation.get("heading")),
        _string(operation.get("tag")),
        operation.get("start_line"),
        operation.get("end_line"),
    )


def _merge_operation_lists(
    operation_lists: list[tuple[str, list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: dict[tuple[Any, ...], tuple[str, str]] = {}
    for source_artifact, operations in operation_lists:
        for operation in operations:
            identity = _operation_identity(operation)
            encoded = json.dumps(operation, sort_keys=True, ensure_ascii=False)
            prior = seen.get(identity)
            if prior is None:
                seen[identity] = (encoded, source_artifact)
                merged.append(dict(operation))
                continue
            if prior[0] == encoded:
                continue
            locator = "::".join(
                token
                for token in (
                    _string(operation.get("target") or operation.get("path") or operation.get("file")),
                    _string(operation.get("scope")),
                )
                if token
            ) or _string(operation.get("op")) or "unknown_operation"
            raise ValueError(
                f"conflicting operations detected for {locator}: {prior[1]} vs {source_artifact}"
            )
    return merged


_PARTIAL_SALVAGEABLE_BLOCKING_GATES = {
    "target_exists",
    "scope_present",
    "scope_addressable",
    "substrate_tag_presence",
}


def _can_salvage_blocked_operations(
    operations: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> bool:
    if not blockers:
        return False
    for blocker in blockers:
        gate = _string(blocker.get("gate"))
        if gate not in _PARTIAL_SALVAGEABLE_BLOCKING_GATES:
            return False
        try:
            op_index = int(blocker.get("op_index"))
        except (TypeError, ValueError):
            return False
        if op_index < 0 or op_index >= len(operations):
            return False
        if _string(operations[op_index].get("op")) not in {"update_docstring", "inject_tag"}:
            return False
    return True


def _single_artifact_compile_meta(
    *,
    strategy: str,
    artifact_path: str,
    role: str | None = None,
    group_label: str | None = None,
    warnings: list[str] | None = None,
    candidate_failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "source_artifacts": [artifact_path],
        "source_roles": [role] if role else [],
        "source_group_labels": [group_label] if group_label else [],
        "warnings": list(warnings or []),
        "candidate_failures": list(candidate_failures or []),
    }


def _aggregate_probe_operations(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    response_index = _response_index_entries(manifest)
    contract_by_label = _contract_groups_by_label(manifest)
    probe_entries = [entry for entry in response_index if _string(entry.get("role")).lower() == "probe"]
    if len(probe_entries) < 2:
        raise ValueError("probe aggregation requires at least two probe artifacts.")

    parsed_sources: list[tuple[str, list[dict[str, Any]]]] = []
    candidate_failures: list[dict[str, Any]] = []
    warnings: list[str] = []
    for entry in probe_entries:
        label = _string(entry.get("group_label"))
        artifact_path = _string(entry.get("artifact_path"))
        contract = contract_by_label.get(label, {})
        group_status = _string(contract.get("group_status") or entry.get("group_status")).lower()
        quality_status = _string(contract.get("quality_status") or entry.get("quality_status")).lower()
        if group_status and group_status != "success":
            raise ValueError(f"probe aggregation blocked because {label or artifact_path} has group_status={group_status}.")
        if quality_status and quality_status not in {"ok", *SEMANTIC_DEGRADED_STATUSES}:
            raise ValueError(f"probe aggregation blocked because {label or artifact_path} has quality_status={quality_status}.")
        if quality_status in SEMANTIC_DEGRADED_STATUSES:
            warnings.append(
                f"{label or artifact_path} quality_status={quality_status}; accepting semantic degradation because probe operations remained compileable."
            )
        if not artifact_path:
            raise ValueError(f"probe aggregation blocked because {label or 'a probe group'} has no artifact_path.")
        resolved_path = _resolve_repo_path(repo_root, artifact_path)
        try:
            operations = _parse_probe_operations_from_artifact(resolved_path, repo_root=repo_root)
        except Exception as exc:
            candidate_failures.append(
                {
                    "strategy": "probe_aggregation",
                    "artifact_path": artifact_path,
                    "group_label": label or None,
                    "role": "probe",
                    "error": str(exc),
                }
            )
            raise ValueError(f"probe aggregation failed for {artifact_path}: {exc}") from exc
        parsed_sources.append((artifact_path, operations))

    merged = _merge_operation_lists(parsed_sources)
    synthesis_contract = next(
        (
            contract
            for contract in contract_by_label.values()
            if _string(contract.get("role")).lower() == "synthesis"
        ),
        None,
    )
    if isinstance(synthesis_contract, Mapping) and _string(synthesis_contract.get("quality_status")).lower() not in {"", "ok"}:
        warnings.append(
            "Synthesis was not compileable; compiled from validated probe artifacts instead."
        )
    compile_meta = {
        "strategy": "aggregated_probes",
        "source_artifacts": [artifact for artifact, _ops in parsed_sources],
        "source_roles": ["probe"] * len(parsed_sources),
        "source_group_labels": [
            _string(entry.get("group_label"))
            for entry in probe_entries
            if _string(entry.get("group_label"))
        ],
        "warnings": warnings,
        "candidate_failures": candidate_failures,
    }
    return merged, compile_meta


def compile_session_manifest_to_apply_plan(
    session_manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
    prefer_artifact: str | None = None,
    include_meta: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compile one observe-session manifest into the standard apply-plan payload that kernel/apply runtime surfaces expect.
    - Mechanism: Load the manifest, rank preferred artifacts, parse surfaced operations or diffs, normalize operations for apply, and block output when deterministic quality gates emit defect or critical findings.
    - Reads: load_session_manifest(), session response artifacts, response sidecars, _validate_standard_operations(), and _run_deterministic_gates().
    - Guarantee: Returns `compile_status=ok` with normalized operations when compilation and gates succeed, or `compile_status=blocked` with blocking gate details when deterministic gates fail.
    - Fails: Raises ValueError when no compileable artifact candidates can be resolved from the manifest and its response index.
    - Orders: Preferred artifact override wins first, then synthesis/evaluation artifacts, then aggregated probes, then fallback artifact candidates.
    - When-needed: Open when `compile_session_manifest_to_apply_plan` is the seam you need to trace, or when a session manifest must be converted into kernel-standard apply operations and you need the exact artifact-selection and blocking-gate rules.
    - Escalates-to: tools/meta/apply.py::run; tools/meta/apply/observe_session.py::attach_apply_transaction; system/lib/python_documentation_tree.py::deterministic_quality_gates.
    """
    manifest = load_session_manifest(session_manifest_path)
    resolved_root = _manifest_repo_root(manifest, repo_root=repo_root)
    contract_by_label = _contract_groups_by_label(manifest)
    response_entries = _response_index_entries(manifest)
    candidates = _artifact_candidates(manifest, prefer_artifact=prefer_artifact)

    if not candidates and not response_entries:
        raise ValueError("session manifest did not expose any artifact candidates for compilation.")

    errors: list[str] = []
    candidate_failures: list[dict[str, Any]] = []

    def _return_plan(operations: list[dict[str, Any]], compile_meta: Mapping[str, Any]) -> dict[str, Any]:
        operations = _normalize_operations_for_apply(resolved_root, operations)
        _validate_standard_operations(resolved_root, operations)
        # Deterministic quality gates — run before any LLM judge or apply approval
        gate_results = _run_deterministic_gates(operations, resolved_root)
        blockers = [g for g in gate_results if g.get("severity") in ("defect", "critical")]
        warnings = [g for g in gate_results if g.get("severity") not in ("defect", "critical")]
        blocked_indices = {g["op_index"] for g in blockers}
        if blockers:
            survivors = [
                operations[i]
                for i in range(len(operations))
                if i not in blocked_indices
            ]
            if survivors and _can_salvage_blocked_operations(operations, blockers):
                salvage_warnings = [
                    {
                        **dict(blocker),
                        "severity": "warning",
                        "detail": f"Salvaged compile by dropping blocked operation: {_string(blocker.get('detail'))}",
                    }
                    for blocker in blockers
                ]
                payload: dict[str, Any] = {
                    "compile_status": "ok",
                    "operations": survivors,
                    "warnings": [*warnings, *salvage_warnings],
                    "blocking_gates": blockers,
                    "blocked_operations": [operations[i] for i in sorted(blocked_indices) if i < len(operations)],
                }
                if include_meta:
                    meta_payload = dict(compile_meta)
                    meta_payload["salvage_mode"] = "drop_blocked_operations"
                    payload["compile_meta"] = meta_payload
                return payload
            payload: dict[str, Any] = {
                "compile_status": "blocked",
                "operations": [],
                "blocking_gates": blockers,
                "blocked_operations": [operations[i] for i in sorted(blocked_indices) if i < len(operations)],
            }
            if warnings:
                payload["warnings"] = warnings
            if include_meta:
                payload["compile_meta"] = dict(compile_meta)
            return payload
        # Clean compile: all gates pass or only warnings
        payload = {
            "compile_status": "ok",
            "operations": operations,
        }
        if warnings:
            payload["warnings"] = warnings
        if include_meta:
            payload["compile_meta"] = dict(compile_meta)
        return payload

    if prefer_artifact:
        prefer_path = _resolve_repo_path(resolved_root, str(prefer_artifact).strip())
        if not prefer_path.exists():
            errors.append(f"{prefer_artifact}: not found")
        else:
            try:
                operations = _parse_operations_from_artifact(prefer_path, repo_root=resolved_root)
                return _return_plan(
                    operations,
                    _single_artifact_compile_meta(
                        strategy="preferred_artifact",
                        artifact_path=str(prefer_artifact).strip(),
                        warnings=[],
                        candidate_failures=candidate_failures,
                    ),
                )
            except Exception as exc:
                errors.append(f"{prefer_artifact}: {exc}")
                candidate_failures.append(
                    {
                        "strategy": "preferred_artifact",
                        "artifact_path": str(prefer_artifact).strip(),
                        "error": str(exc),
                    }
                )

    preferred_roles = {"synthesis", "evaluation"}
    preferred_entries = [
        entry for entry in response_entries if _string(entry.get("role")).lower() in preferred_roles
    ]
    for entry in preferred_entries:
        artifact_path = _string(entry.get("artifact_path"))
        role = _string(entry.get("role")).lower() or None
        group_label = _string(entry.get("group_label")) or None
        if not artifact_path:
            continue
        resolved_path = _resolve_repo_path(resolved_root, artifact_path)
        if not resolved_path.exists():
            errors.append(f"{artifact_path}: not found")
            candidate_failures.append(
                {
                    "strategy": "preferred_role_artifact",
                    "artifact_path": artifact_path,
                    "group_label": group_label,
                    "role": role,
                    "error": "not found",
                }
            )
            continue
        try:
            operations = _parse_operations_from_artifact(resolved_path, repo_root=resolved_root)
            warnings: list[str] = []
            contract = contract_by_label.get(group_label or "", {})
            quality_status = _string(contract.get("quality_status")).lower()
            if quality_status and quality_status != "ok":
                warnings.append(f"{group_label or artifact_path} quality_status={quality_status}")
            return _return_plan(
                operations,
                _single_artifact_compile_meta(
                    strategy="preferred_role_artifact",
                    artifact_path=artifact_path,
                    role=role,
                    group_label=group_label,
                    warnings=warnings,
                    candidate_failures=candidate_failures,
                ),
            )
        except Exception as exc:
            errors.append(f"{artifact_path}: {exc}")
            candidate_failures.append(
                {
                    "strategy": "preferred_role_artifact",
                    "artifact_path": artifact_path,
                    "group_label": group_label,
                    "role": role,
                    "error": str(exc),
                }
            )

    probe_entries = [entry for entry in response_entries if _string(entry.get("role")).lower() == "probe"]
    if len(probe_entries) > 1:
        try:
            operations, compile_meta = _aggregate_probe_operations(manifest, repo_root=resolved_root)
            compile_meta = dict(compile_meta)
            compile_meta["candidate_failures"] = [*candidate_failures, *list(compile_meta.get("candidate_failures", []))]
            return _return_plan(operations, compile_meta)
        except Exception as exc:
            errors.append(f"aggregated_probes: {exc}")
            candidate_failures.append(
                {
                    "strategy": "aggregated_probes",
                    "artifact_path": None,
                    "group_label": None,
                    "role": "probe",
                    "error": str(exc),
                }
            )

    fallback_candidates = [
        token for token in candidates
        if token and token != str(prefer_artifact or "").strip()
    ]
    if len(probe_entries) > 1:
        probe_artifact_paths = {
            _string(entry.get("artifact_path"))
            for entry in probe_entries
            if _string(entry.get("artifact_path"))
        }
        fallback_candidates = [token for token in fallback_candidates if token not in probe_artifact_paths]

    for token in fallback_candidates:
        artifact_path = _resolve_repo_path(resolved_root, token)
        if not artifact_path.exists():
            errors.append(f"{token}: not found")
            candidate_failures.append(
                {
                    "strategy": "fallback_artifact",
                    "artifact_path": token,
                    "error": "not found",
                }
            )
            continue
        try:
            operations = _parse_operations_from_artifact(artifact_path, repo_root=resolved_root)
            entry = next((item for item in response_entries if _string(item.get("artifact_path")) == token), {})
            return _return_plan(
                operations,
                _single_artifact_compile_meta(
                    strategy="fallback_artifact",
                    artifact_path=token,
                    role=_string(entry.get("role")).lower() or None,
                    group_label=_string(entry.get("group_label")) or None,
                    warnings=[],
                    candidate_failures=candidate_failures,
                ),
            )
        except Exception as exc:
            errors.append(f"{token}: {exc}")
            candidate_failures.append(
                {
                    "strategy": "fallback_artifact",
                    "artifact_path": token,
                    "group_label": _string(next((item.get("group_label") for item in response_entries if _string(item.get('artifact_path')) == token), "")) or None,
                    "role": _string(next((item.get("role") for item in response_entries if _string(item.get('artifact_path')) == token), "")) or None,
                    "error": str(exc),
                }
            )

    contract_validation = manifest.get("contract_validation") if isinstance(manifest.get("contract_validation"), Mapping) else {}
    summary = contract_validation.get("summary") if isinstance(contract_validation.get("summary"), Mapping) else {}
    validation_hint = ""
    if summary:
        validation_hint = (
            f" contract_validation summary={json.dumps(dict(summary), sort_keys=True)}"
        )
    raise ValueError(
        "failed to compile a standard apply plan from session manifest artifacts."
        + validation_hint
        + (f" Errors: {'; '.join(errors[:6])}" if errors else "")
    )


def run_miner_after_apply(*, root_hint: str | None = None, json_mode: bool = True) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Re-run the Python documentation audit after an apply pass so callers can see the post-mutation compliance state immediately.
    - Mechanism: Build an InspectorService for the resolved repo root, scan the tree, and collect per-file failures when the scan reports failing status.
    - Reads: InspectorService.scan_tree(), InspectorService.inspect_file(), and _collect_failures().
    - Guarantee: Returns a success payload with an empty failure list when the scan passes, otherwise returns a failure payload enumerating failing files.
    - Fails: None — service bootstrap errors are converted into a failure payload.
    - When-needed: Open when an apply pass requests immediate miner feedback instead of a separate audit command.
    - Escalates-to: system/server/inspector.py::InspectorService; tools/meta/miner.py::_collect_failures.
    """
    del json_mode
    try:
        service = InspectorService(root_dir=_repo_root(root_hint))
    except Exception as exc:
        return {"status": "failure", "error": str(exc), "failures": []}

    scan_result = service.scan_tree()
    tree = scan_result[0] if isinstance(scan_result, tuple) else scan_result
    if getattr(tree, "status", "ok") != "fail":
        return {"status": "success", "root": str(service.root), "failures": []}

    failures: list[dict[str, Any]] = []
    for file_path in _collect_failures(tree):
        try:
            details = service.inspect_file(file_path)
            entry = {
                "file": file_path,
                "errors": list(getattr(details, "errors", []) or []),
                "missing_module_tags": list(getattr(details, "missing_module_tags", []) or []),
                "classes_missing_role": list(getattr(details, "classes_missing_role", []) or []),
                "functions_missing_action": list(getattr(details, "functions_missing_action", []) or []),
            }
            if any(entry[key] for key in entry if key != "file"):
                failures.append(entry)
        except Exception as exc:
            failures.append({"file": file_path, "error": str(exc)})

    return {
        "status": "failure" if failures else "success",
        "root": str(service.root),
        "failures": failures,
    }


def run_compiled_session_manifest(
    session_manifest_path: str | Path,
    *,
    root_hint: str | None = None,
    dry_run: bool = True,
    validate_only: bool = False,
    capture_diffs: bool = True,
    patch_id: str | None = None,
    enforce_target_routing: bool = False,
    preferred_target_family: str | None = None,
    run_miner: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute the full compile-then-apply path for one observe-session manifest through the runtime apply surface.
    - Mechanism: Compile the manifest into a standard apply plan, assemble the apply runtime config, forward it into `meta_apply.run`, and optionally append a post-apply miner receipt on success.
    - Reads: compile_session_manifest_to_apply_plan(), tools.meta.apply.run(), and run_miner_after_apply() when `run_miner` is true.
    - Guarantee: Returns the runtime apply result, optionally augmented with `miner_result` after successful apply execution.
    - Fails: Propagates compilation or runtime-apply exceptions from the underlying compiler/executor surfaces.
    - When-needed: Open when a caller wants a single entrypoint that compiles a stored observe session and immediately runs the apply runtime against it.
    - Escalates-to: tools/meta/apply.py::run; tools/meta/apply/observe_compiler.py::compile_session_manifest_to_apply_plan.
    """
    resolved_root = _repo_root(root_hint)
    compiled_plan = compile_session_manifest_to_apply_plan(
        session_manifest_path,
        repo_root=resolved_root,
    )
    config: dict[str, Any] = {
        "mode": "apply",
        "root_hint": str(resolved_root),
        "plan": compiled_plan,
        "dry_run": bool(dry_run),
        "validate_only": bool(validate_only),
        "capture_diffs": bool(capture_diffs),
        "enforce_target_routing": bool(enforce_target_routing),
    }
    if str(patch_id or "").strip():
        config["patch_id"] = str(patch_id).strip()
    if str(preferred_target_family or "").strip():
        config["preferred_target_family"] = str(preferred_target_family).strip()

    result = dict(meta_apply.run(config))
    if run_miner and result.get("metadata", {}).get("status") == "success":
        result["miner_result"] = run_miner_after_apply(root_hint=str(resolved_root), json_mode=True)
    return result
