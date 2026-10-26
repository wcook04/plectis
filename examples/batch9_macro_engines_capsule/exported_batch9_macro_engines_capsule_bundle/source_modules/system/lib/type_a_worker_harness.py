"""
Runtime-owned lower-class Type A worker harness.

[PURPOSE]
- Teleology: Let low-authority providers such as OpenRouter and NVIDIA perform
  bounded row transforms under the same Type A control plane as Codex/Claude,
  without granting repo/tool authority.
- Mechanism: Normalize a transform_job, render a JSON-only packet prompt,
  enforce provider budget/tool/write-root policy, call the selected provider,
  validate structured output, and persist provider_receipt + row_patch artifacts.
- Non-goal: This module does not promote row patches into doctrine or run
  arbitrary shell retries. Provider output is trusted as a bounded candidate;
  controller/apply review owns mutation.
"""

from __future__ import annotations

import dataclasses
import difflib
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib import compute_throughput, model_profile_registry
from system.lib.type_a_global_policy import (
    type_a_local_evidence_override_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_JOB_SCHEMA_VERSION = "std_transform_job_v1"
ROW_PATCH_SCHEMA_VERSION = "std_row_patch_v1"
PROVIDER_RECEIPT_SCHEMA_VERSION = "std_provider_receipt_v1"
CANDIDATE_SKIP_RECEIPT_SCHEMA_VERSION = "std_candidate_skip_receipt_v1"
DEFAULT_STATE_ROOT = "state/compute_workers"
LOWER_CLASS_PROVIDERS = frozenset({"openrouter_api", "nvidia_nim"})
PROVIDER_RUNTIME_TOKENS = {
    "openrouter_api": "openrouter_free",
    "nvidia_nim": "nvidia",
}
DEFAULT_PROVIDER_MODELS = {
    "openrouter_api": "openrouter/free",
    "nvidia_nim": model_profile_registry.nvidia_model_id(
        "default_worker",
        fallback="z-ai/glm-5.1",
    ),
}
FAILED_STATUSES = frozenset(
    {
        "empty_response",
        "schema_fail",
        "429",
        "5xx",
        "timeout",
        "worker_error",
        "policy_reject",
    }
)
FORMAL_MATH_BENCHMARK_IDS = frozenset({"constructivebench", "verisoftbench"})
FORMAL_MATH_NO_SOLVE_MANIFEST_IDS = frozenset(
    {"constructivebench_no_solve_manifest_v0", "verisoftbench_no_solve_manifest_v0"}
)


@dataclasses.dataclass(frozen=True)
class HarnessResult:
    receipt: dict[str, Any]
    row_patch: dict[str, Any] | None
    artifact_refs: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _month_slug(value: str | None = None) -> str:
    text = value or _utc_now()
    return text[:7]


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f"{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Expected JSON object at {path}")
    return dict(payload)


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _artifact_path(repo_root: Path, bucket: str, artifact_id: str, *, created_at: str | None = None) -> Path:
    return repo_root / DEFAULT_STATE_ROOT / bucket / _month_slug(created_at) / f"{artifact_id}.json"


def _fingerprint_path(repo_root: Path, fingerprint: str) -> Path:
    return repo_root / DEFAULT_STATE_ROOT / "run_fingerprints" / f"{fingerprint}.json"


def _cache_path(repo_root: Path, cache_key: str) -> Path:
    return repo_root / DEFAULT_STATE_ROOT / "cache" / f"{cache_key}.json"


def _source_fingerprint(repo_root: Path, path: str | Path) -> dict[str, Any]:
    candidate = _repo_path(repo_root, path)
    try:
        stat = candidate.stat()
        data = candidate.read_bytes()
    except OSError:
        return {
            "path": _rel(repo_root, candidate),
            "exists": False,
            "blake2b": None,
            "bytes": 0,
            "mtime": None,
        }
    return {
        "path": _rel(repo_root, candidate),
        "exists": True,
        "blake2b": hashlib.blake2b(data, digest_size=16).hexdigest(),
        "bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def _default_provider_budget(provider_id: str) -> dict[str, Any]:
    if provider_id == "openrouter_api":
        return {
            "free_only": True,
            "allow_paid": False,
            "max_usd": 0.0,
            "max_retries": 0,
        }
    return {
        "free_only": True,
        "allow_paid": False,
        "max_usd": 0.0,
        "max_retries": 0,
    }


def _policy_for_task(repo_root: Path, task_class: str) -> dict[str, Any]:
    standard = compute_throughput.load_compute_standard(repo_root)
    task_classes = standard.get("task_classes") if isinstance(standard.get("task_classes"), Mapping) else {}
    policy = task_classes.get(task_class) if isinstance(task_classes, Mapping) else None
    return dict(policy) if isinstance(policy, Mapping) else {}


def build_transform_job(
    repo_root: Path,
    *,
    task_class: str,
    target_row_id: str,
    target_facet: str,
    input_packet: Mapping[str, Any],
    target_band: str = "row",
    source_paths: Sequence[str | Path] | None = None,
    output_schema: Mapping[str, Any] | None = None,
    provider_selection_policy: Mapping[str, Any] | None = None,
    authority_ceiling: str = "provider_endpoint",
    connector_neighborhood_ref: str | None = None,
    validation_command: str | None = None,
    promotion_target: Mapping[str, Any] | None = None,
    created_by: str = "type_a_worker_harness",
) -> dict[str, Any]:
    policy = _policy_for_task(repo_root, task_class)
    source_fingerprints = [_source_fingerprint(repo_root, path) for path in (source_paths or [])]
    resolved_output_schema = dict(output_schema or policy.get("output_schema") or {})
    provider_policy = {
        "prefer": ["nvidia_nim", "openrouter_api"],
        "fallback": None,
        "paid_gate": False,
        "capacity_lane_semantics": "prefer selects one transform-job lane; provider metabolism should create separate jobs to use separate provider throughput.",
        "fallback_means": "same_job_recovery_only_not_capacity_substitution",
        **_safe_mapping(provider_selection_policy),
    }
    job_id = f"tj_{uuid.uuid4().hex[:16]}"
    material = {
        "task_class": task_class,
        "target_row_id": target_row_id,
        "target_facet": target_facet,
        "target_band": target_band,
        "source_fingerprints": source_fingerprints,
        "input_packet": dict(input_packet),
        "output_schema": resolved_output_schema,
        "provider_selection_policy": provider_policy,
        "local_evidence_override_policy": type_a_local_evidence_override_policy(),
    }
    created_at = _utc_now()
    return {
        "kind": "transform_job",
        "schema_version": TRANSFORM_JOB_SCHEMA_VERSION,
        "id": job_id,
        "task_class": task_class,
        "target_row_id": target_row_id,
        "target_facet": target_facet,
        "target_band": target_band,
        "source_fingerprints": source_fingerprints,
        "connector_neighborhood_ref": connector_neighborhood_ref,
        "input_packet": dict(input_packet),
        "output_schema": resolved_output_schema,
        "local_evidence_override_policy": type_a_local_evidence_override_policy(),
        "authority_ceiling": authority_ceiling,
        "forbidden_surfaces": list(policy.get("forbidden_surfaces") or []),
        "provider_selection_policy": provider_policy,
        "provider_budget": _default_provider_budget("openrouter_api"),
        "cache_key": _digest(material),
        "validation_command": validation_command or policy.get("validation_command"),
        "promotion_target": dict(promotion_target or {"state": "draft"}),
        "receipt_target": f"{DEFAULT_STATE_ROOT}/receipts/{_month_slug(created_at)}/<receipt_id>.json",
        "created_at": created_at,
        "created_by": created_by,
    }


def normalize_transform_job(repo_root: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    job = dict(payload)
    task_class = _string(job.get("task_class"))
    if not task_class:
        raise ValueError("transform_job.task_class is required")
    policy = _policy_for_task(repo_root, task_class)
    job_id = _string(job.get("id") or f"tj_{uuid.uuid4().hex[:16]}")
    created_at = _string(job.get("created_at")) or _utc_now()
    input_packet = _safe_mapping(job.get("input_packet"))
    output_schema = _safe_mapping(job.get("output_schema") or policy.get("output_schema"))
    provider_policy = {
        "prefer": ["nvidia_nim", "openrouter_api"],
        "fallback": None,
        "paid_gate": False,
        "capacity_lane_semantics": "prefer selects one transform-job lane; provider metabolism should create separate jobs to use separate provider throughput.",
        "fallback_means": "same_job_recovery_only_not_capacity_substitution",
        **_safe_mapping(job.get("provider_selection_policy")),
    }
    normalized = {
        **job,
        "kind": "transform_job",
        "schema_version": TRANSFORM_JOB_SCHEMA_VERSION,
        "id": job_id,
        "task_class": task_class,
        "target_row_id": _string(job.get("target_row_id") or "<target_row_id>"),
        "target_facet": _string(job.get("target_facet") or "<target_facet>"),
        "target_band": _string(job.get("target_band") or "row"),
        "source_fingerprints": _safe_list(job.get("source_fingerprints")),
        "connector_neighborhood_ref": job.get("connector_neighborhood_ref"),
        "input_packet": input_packet,
        "output_schema": output_schema,
        "local_evidence_override_policy": type_a_local_evidence_override_policy(
            _safe_mapping(job.get("local_evidence_override_policy"))
        ),
        "authority_ceiling": _string(job.get("authority_ceiling") or policy.get("required_authority_tier") or "provider_endpoint"),
        "forbidden_surfaces": _safe_list(job.get("forbidden_surfaces") or policy.get("forbidden_surfaces")),
        "provider_selection_policy": provider_policy,
        "provider_budget": {**_default_provider_budget("openrouter_api"), **_safe_mapping(job.get("provider_budget"))},
        "validation_command": _string(job.get("validation_command") or policy.get("validation_command")) or None,
        "promotion_target": _safe_mapping(job.get("promotion_target")) or {"state": "draft"},
        "created_at": created_at,
        "created_by": _string(job.get("created_by") or "unknown_controller"),
    }
    if not _string(normalized.get("cache_key")):
        normalized["cache_key"] = _digest(
            {
                "task_class": normalized["task_class"],
                "target_row_id": normalized["target_row_id"],
                "target_facet": normalized["target_facet"],
                "target_band": normalized["target_band"],
                "source_fingerprints": normalized["source_fingerprints"],
                "input_packet": normalized["input_packet"],
                "output_schema": normalized["output_schema"],
                "provider_selection_policy": normalized["provider_selection_policy"],
                "local_evidence_override_policy": normalized["local_evidence_override_policy"],
            }
        )
    normalized["receipt_target"] = _string(normalized.get("receipt_target")) or (
        f"{DEFAULT_STATE_ROOT}/receipts/{_month_slug(created_at)}/<receipt_id>.json"
    )
    return normalized


def write_transform_job(
    repo_root: Path,
    job: Mapping[str, Any],
    *,
    write_root: Path | None = None,
) -> dict[str, Any]:
    normalized = normalize_transform_job(repo_root, job)
    target_root = Path(write_root) if write_root is not None else repo_root
    path = _artifact_path(target_root, "transform_jobs", normalized["id"], created_at=normalized.get("created_at"))
    _atomic_write_json(path, normalized)
    return {**normalized, "artifact_path": _rel(target_root, path)}


# ---------------------------------------------------------------------------
# Row-job seed -> provider_transform_job materialization (non-dispatching)
# ---------------------------------------------------------------------------

# Map seed provider_id (used in compute_throughput catalogs and row jobs) to
# the runtime token the metabolism scheduler expects on a job's ``provider``
# field.  The same mapping is consulted by ``_remote_provider_harness_block_reason``
# in metabolism_scheduler when validating provider_transform_job dispatch.
_ROW_JOB_PROVIDER_RUNTIME_TOKENS = dict(PROVIDER_RUNTIME_TOKENS)


def materialize_provider_transform_job_from_row_job(
    repo_root: Path,
    row_job: Mapping[str, Any],
    *,
    write: bool = False,
    write_root: Path | None = None,
    created_by: str = "metabolism_row_job_materializer",
) -> dict[str, Any]:
    """Bridge a row job with ``transform_job_seed`` into a scheduler-shaped packet.

    Pure / local: this function never calls a provider, never mutates source
    authority, never enqueues a daemon job, never promotes doctrine.  It does
    one thing: project a ``transform_job_seed`` from a row job into the two
    artifacts a Type A controller would need to *eventually* dispatch a
    provider_transform_job through the metabolism scheduler:

    1. A normalized ``transform_job`` (the same shape ``build_transform_job``
       produces) — optionally written to disk under
       ``state/compute_workers/transform_jobs/<month>/<id>.json``.
    2. A ``metabolism_job`` posture (kind, provider, params.operation_id,
       params.operation_parameters) the scheduler's
       ``_provider_transform_job_block_reason`` can validate.

    The scheduler will *only* accept the metabolism_job posture when ``write``
    is True (so ``job_path`` is populated).  When ``write`` is False, the
    posture is a draft that the scheduler refuses with
    ``"requires job_path"`` — a feature, not a bug: it lets controllers
    inspect the materialization without ever risking a silent dispatch.

    Refusal cases (raise ValueError with explicit message):
      * row_job has no ``transform_job_seed``
      * seed missing task_class / target_row_id / target_facet / input_packet
      * seed.provider_selection_policy missing or paid_gate=True
      * capacity_lane_id missing, malformed, or pointing at an unknown provider
    """
    seed = row_job.get("transform_job_seed")
    if not isinstance(seed, Mapping):
        raise ValueError(
            "materialization refused: row_job has no transform_job_seed"
        )
    task_class = _string(seed.get("task_class"))
    if not task_class:
        raise ValueError(
            "materialization refused: transform_job_seed missing task_class"
        )
    target_row_id = _string(seed.get("target_row_id"))
    if not target_row_id:
        raise ValueError(
            "materialization refused: transform_job_seed missing target_row_id"
        )
    target_facet = _string(seed.get("target_facet"))
    if not target_facet:
        raise ValueError(
            "materialization refused: transform_job_seed missing target_facet"
        )
    input_packet = seed.get("input_packet")
    if not isinstance(input_packet, Mapping):
        raise ValueError(
            "materialization refused: transform_job_seed missing input_packet"
        )
    policy = seed.get("provider_selection_policy")
    if not isinstance(policy, Mapping):
        raise ValueError(
            "materialization refused: transform_job_seed missing provider_selection_policy"
        )
    if policy.get("paid_gate") is True:
        raise ValueError(
            "materialization refused: provider_selection_policy.paid_gate=True; "
            "non-dispatching materialization requires paid_gate=False"
        )
    capacity_lane_id = _string(policy.get("capacity_lane_id"))
    if not capacity_lane_id:
        raise ValueError(
            "materialization refused: provider_selection_policy missing capacity_lane_id"
        )
    if not capacity_lane_id.startswith("provider:"):
        raise ValueError(
            f"materialization refused: capacity_lane_id={capacity_lane_id!r} "
            "must be of the form 'provider:<provider_id>'"
        )
    provider_id = capacity_lane_id.split(":", 1)[1]
    if provider_id not in _ROW_JOB_PROVIDER_RUNTIME_TOKENS:
        raise ValueError(
            f"materialization refused: provider_id={provider_id!r} not in "
            f"{sorted(_ROW_JOB_PROVIDER_RUNTIME_TOKENS)}"
        )
    runtime_token = _ROW_JOB_PROVIDER_RUNTIME_TOKENS[provider_id]

    # Task-policy guard: the downstream Type A worker harness derives output
    # schema, forbidden surfaces, validation command, and required authority
    # tier from std_compute_provider.task_classes.  An unknown or
    # unconfigured task_class would let a malformed seed produce a
    # scheduler-accepted provider_transform_job whose actual run lacks
    # validation, so we refuse before build_transform_job rather than after.
    if not _policy_for_task(repo_root, task_class):
        raise ValueError(
            f"materialization refused: task_class={task_class!r} is not "
            "configured in std_compute_provider.task_classes; downstream "
            "harness would lack output_schema and validation_command"
        )

    transform_job = build_transform_job(
        repo_root,
        task_class=task_class,
        target_row_id=target_row_id,
        target_facet=target_facet,
        target_band=_string(seed.get("target_band") or "row"),
        input_packet=dict(input_packet),
        source_paths=[
            str(path)
            for path in (seed.get("source_paths") or [])
            if str(path).strip()
        ],
        output_schema=(
            dict(seed.get("output_schema"))
            if isinstance(seed.get("output_schema"), Mapping)
            else None
        ),
        provider_selection_policy={
            **dict(policy),
            "prefer": [provider_id],
        },
        authority_ceiling=_string(seed.get("authority_ceiling") or "provider_endpoint"),
        validation_command=_string(seed.get("validation_command")) or None,
        promotion_target=(
            dict(seed.get("promotion_target"))
            if isinstance(seed.get("promotion_target"), Mapping)
            else None
        ),
        created_by=created_by,
    )
    for optional_key in (
        "execution_profile",
        "failure_policy",
        "provider_budget",
        "model_profile",
    ):
        optional_value = seed.get(optional_key)
        if isinstance(optional_value, Mapping):
            transform_job[optional_key] = dict(optional_value)

    artifact_path: str | None = None
    if write:
        written = write_transform_job(repo_root, transform_job, write_root=write_root)
        artifact_path = _string(written.get("artifact_path")) or None
        transform_job = {
            key: value for key, value in written.items() if key != "artifact_path"
        }

    metabolism_job = {
        "kind": "provider_transform_job",
        "provider": runtime_token,
        "params": {
            "operation_id": "provider_transform_job",
            "operation_parameters": {
                "job_path": artifact_path or "",
                "provider_id": provider_id,
            },
        },
    }

    return {
        "transform_job": transform_job,
        "artifact_path": artifact_path,
        "metabolism_job": metabolism_job,
        "draft_state": "written" if write else "not_written",
        "row_job_target_row_id": _string(row_job.get("target_row_id")),
        "runtime_token": runtime_token,
        "provider_id": provider_id,
    }


def _provider_row(repo_root: Path, provider_id: str) -> dict[str, Any]:
    ledger = compute_throughput.build_compute_ledger(repo_root)
    for row in ledger.get("providers") or []:
        if isinstance(row, Mapping) and row.get("provider_id") == provider_id:
            return dict(row)
    return {}


def _select_provider(repo_root: Path, job: Mapping[str, Any], provider_id: str | None) -> tuple[str, dict[str, Any]]:
    explicit = _string(provider_id)
    if explicit and explicit != "auto":
        row = _provider_row(repo_root, explicit)
        if not row:
            raise ValueError(f"Unknown provider_id: {explicit}")
        return explicit, row
    route = compute_throughput.route_worker(_string(job.get("task_class")), repo_root)
    candidates = {
        _string(candidate.get("provider_id")): candidate
        for candidate in _safe_list(route.get("candidates"))
        if isinstance(candidate, Mapping)
    }
    preferred = _safe_mapping(job.get("provider_selection_policy")).get("prefer")
    if isinstance(preferred, list):
        for candidate_id_raw in preferred:
            candidate_id = _string(candidate_id_raw)
            if candidate_id in candidates:
                return candidate_id, _provider_row(repo_root, candidate_id)
    selected = _string(route.get("selected_provider"))
    if not route.get("route_allowed") or not selected:
        raise RuntimeError(route.get("reason") or "No low-authority provider route available")
    return selected, _provider_row(repo_root, selected)


def _model_id(job: Mapping[str, Any], provider_id: str, provider_row: Mapping[str, Any], override: str | None) -> str:
    if _string(override):
        return _string(override)
    policy = _safe_mapping(job.get("provider_selection_policy"))
    models = policy.get("models") if isinstance(policy.get("models"), Mapping) else {}
    if isinstance(models, Mapping) and _string(models.get(provider_id)):
        return _string(models.get(provider_id))
    profile = _safe_mapping(job.get("execution_profile") or job.get("model_profile"))
    if _string(profile.get("model_id") or profile.get("model")):
        return _string(profile.get("model_id") or profile.get("model"))
    configured = (_safe_mapping(provider_row.get("runtime_overlay")).get("nvidia_status") or {})
    if provider_id == "nvidia_nim" and isinstance(configured, Mapping):
        model = (_safe_mapping(configured.get("configured"))).get("chat_model")
        if _string(model):
            return _string(model)
    return DEFAULT_PROVIDER_MODELS.get(provider_id, "unknown")


def _model_is_openrouter_free(model_id: str) -> bool:
    token = _string(model_id)
    return token == "openrouter/free" or token.endswith(":free")


def _enforce_budget(job: Mapping[str, Any], provider_id: str, model_id: str) -> dict[str, Any]:
    budget = {**_default_provider_budget(provider_id), **_safe_mapping(job.get("provider_budget"))}
    if provider_id == "openrouter_api" and not _model_is_openrouter_free(model_id):
        allow_paid = bool(budget.get("allow_paid"))
        free_only = bool(budget.get("free_only", True))
        max_usd = float(budget.get("max_usd") or 0.0)
        if free_only or not allow_paid or max_usd <= 0:
            raise PermissionError("openrouter_paid_model_blocked_by_provider_budget")
    return budget


def _contains_forbidden_surface(job: Mapping[str, Any]) -> str:
    forbidden = [_string(item) for item in _safe_list(job.get("forbidden_surfaces")) if _string(item)]
    if not forbidden:
        return ""
    def _without_policy_declarations(value: Any) -> Any:
        if isinstance(value, Mapping):
            omitted_keys = {
                "forbidden",
                "forbidden_material",
                "forbidden_surfaces",
                "forbidden_surfaces_present",
            }
            return {
                key: _without_policy_declarations(child)
                for key, child in value.items()
                if _string(key) not in omitted_keys
            }
        if isinstance(value, list):
            return [_without_policy_declarations(child) for child in value]
        return value

    text = _stable_json(_without_policy_declarations(job.get("input_packet") or {}))
    for pattern in forbidden:
        if pattern.endswith("*"):
            if pattern[:-1] and pattern[:-1] in text:
                return pattern
            continue
        if pattern in text:
            return pattern
    return ""


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        rows: list[Mapping[str, Any]] = [value]
        for child in value.values():
            rows.extend(_walk_mappings(child))
        return rows
    if isinstance(value, list):
        rows = []
        for child in value:
            rows.extend(_walk_mappings(child))
        return rows
    return []


def _packet_references_formal_math_benchmark(packet: Mapping[str, Any]) -> bool:
    for row in _walk_mappings(packet):
        benchmark_id = _string(row.get("benchmark_id"))
        manifest_id = _string(row.get("manifest_id"))
        schema_version = _string(row.get("schema_version"))
        if benchmark_id in FORMAL_MATH_BENCHMARK_IDS:
            return True
        if manifest_id in FORMAL_MATH_NO_SOLVE_MANIFEST_IDS:
            return True
        if schema_version == "formal_math_no_solve_manifest_v0":
            return True
        manifest_task_id = _string(row.get("manifest_task_id") or row.get("task_id"))
        if any(manifest_task_id.startswith(f"{benchmark}:") for benchmark in FORMAL_MATH_BENCHMARK_IDS):
            return True
    return False


def _find_formal_math_prompt_boundary_guard(packet: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for row in _walk_mappings(packet):
        guard = row.get("prompt_boundary_guard")
        if isinstance(guard, Mapping):
            return guard
    return None


def _formal_math_prompt_boundary_violations(job: Mapping[str, Any]) -> list[str]:
    packet = _safe_mapping(job.get("input_packet"))
    if not _packet_references_formal_math_benchmark(packet):
        return []
    guard = _find_formal_math_prompt_boundary_guard(packet)
    if guard is None:
        return ["formal_math_prompt_boundary_guard_missing"]
    violations: list[str] = []
    if _string(guard.get("status")) != "PASS":
        violations.append("formal_math_prompt_boundary_guard_not_pass")
    if not _string(guard.get("manifest_ref")):
        violations.append("formal_math_prompt_boundary_manifest_ref_missing")
    if not _string(guard.get("redaction_receipt_ref")):
        violations.append("formal_math_prompt_boundary_redaction_receipt_ref_missing")
    if not _string(guard.get("prompt_boundary_receipt_ref")):
        violations.append("formal_math_prompt_boundary_receipt_ref_missing")
    execution_gate = _safe_mapping(guard.get("provider_execution_gate"))
    if execution_gate.get("next_provider_run_allowed") is not True:
        required = _string(execution_gate.get("required_next_workitem"))
        suffix = f":{required}" if required else ""
        violations.append(f"formal_math_provider_run_gate_closed{suffix}")
    return violations


def _render_prompt(job: Mapping[str, Any]) -> str:
    task_class = _string(job.get("task_class"))
    task_specific_rule = ""
    if task_class == "raw_seed_candidate_io":
        task_specific_rule = (
            "\nRaw-seed candidate I/O rule: do not summarize, do not emit takeaway/anchor pairs, "
            "and do not merely fix punctuation. Return canonical raw-seed distillation JSON with "
            "top-level shards[]. Each shard needs a materially clearer clarified_statement and a "
            "verbatim voice_anchor copied from the source paragraph. The goal is to say what the "
            "operator is trying to say much more clearly while preserving ambiguity, pressure, "
            "system vocabulary, and distinctive phrasing. If a source phrase says vague things like "
            "'it needs to look for what needs doing', name the concrete mechanism implied by the "
            "paragraph, such as autonomous work detection, consolidation, todo-layer routing, or "
            "self-organization. A cleaned-up quote is invalid. Before returning, verify each "
            "voice_anchor is an exact contiguous 6-20 word substring copied from "
            "input_packet.bounded_raw_seed_excerpt.text; do not paraphrase, add ellipses, normalize "
            "spelling, or stitch separated phrases. Then compare clarified_statement against "
            "voice_anchor; if it is only typo cleanup or a near-copy, rewrite it to name the "
            "underlying intent or omit the shard with uncertainty."
        )
    packet = {
        "task": {
            "task_class": job.get("task_class"),
            "target_row_id": job.get("target_row_id"),
            "target_facet": job.get("target_facet"),
            "target_band": job.get("target_band"),
            "authority_ceiling": job.get("authority_ceiling"),
        },
        "input_packet": job.get("input_packet") or {},
        "output_schema": job.get("output_schema") or {},
        "local_evidence_override_policy": job.get("local_evidence_override_policy") or {},
        "required_response_rule": "Return exactly one JSON object. No markdown, no prose outside JSON.",
        "authority_rule": (
            "You are a bounded provider worker. Source packets and memos are proposed contours; "
            "local system evidence in the packet overrides them. Produce a trusted candidate receipt; "
            "controller/apply review owns mutation."
        ),
    }
    return (
        "You are an ai_workflow lower-class Type A bounded provider worker.\n"
        "Consume only the packet below and return JSON that satisfies output_schema.\n"
        "If evidence is missing, include omissions and uncertainty in the JSON rather than inventing facts."
        f"{task_specific_rule}\n\n"
        f"{json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)}"
    )


def _extract_json(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    stripped = text.strip()
    if not stripped:
        return None, ["empty response"]
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end <= start:
            return None, ["response is not JSON"]
        try:
            parsed = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            return None, [f"json parse error: {exc.msg}"]
    if not isinstance(parsed, Mapping):
        return None, ["top-level JSON response is not an object"]
    return dict(parsed), []


def _schema_violations(payload: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    if not schema:
        return []
    violations: list[str] = []
    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(payload, Mapping):
        return ["payload is not an object"]
    required = schema.get("required")
    if isinstance(required, list):
        for key in required:
            if str(key) not in payload:
                violations.append(f"missing required field: {key}")
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        for key, prop in properties.items():
            if key not in payload or not isinstance(prop, Mapping):
                continue
            prop_type = prop.get("type")
            value = payload[key]
            if prop_type == "array" and not isinstance(value, list):
                violations.append(f"{key} must be array")
            elif prop_type == "object" and not isinstance(value, Mapping):
                violations.append(f"{key} must be object")
            elif prop_type == "string" and not isinstance(value, str):
                violations.append(f"{key} must be string")
            elif prop_type == "boolean" and not isinstance(value, bool):
                violations.append(f"{key} must be boolean")
            elif prop_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                violations.append(f"{key} must be number")
    return violations


def _normalized_words(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _word_count(text: str) -> int:
    normalized = _normalized_words(text)
    return len([part for part in normalized.split(" ") if part])


def _raw_seed_source_paragraph_from_job(job: Mapping[str, Any]) -> dict[str, Any]:
    packet = _safe_mapping(job.get("input_packet"))
    excerpt = _safe_mapping(packet.get("bounded_raw_seed_excerpt"))
    metadata = _safe_mapping(packet.get("paragraph_metadata"))
    text = _string(excerpt.get("text"))
    paragraph_id = _string(excerpt.get("paragraph_id"))
    return {
        "id": paragraph_id,
        "text": text,
        "plain_text": text,
        "source_substrate": _string(excerpt.get("source_substrate")),
        "line_start": metadata.get("line_start"),
        "line_end": metadata.get("line_end"),
    }


def _raw_seed_candidate_output_violations(
    payload: Mapping[str, Any],
    job: Mapping[str, Any],
) -> list[str]:
    if _string(job.get("task_class")) != "raw_seed_candidate_io":
        return []

    violations: list[str] = []
    if "candidate_shards" in payload:
        violations.append("raw_seed_candidate_io must return top-level shards, not candidate_shards")
    if "takeaway" in payload or "anchor" in payload:
        violations.append("takeaway/anchor output shape is invalid; return canonical raw-seed shards")

    shards = payload.get("shards")
    if not isinstance(shards, list) or not shards:
        violations.append("raw_seed_candidate_io requires non-empty shards array")
        return violations

    source = _raw_seed_source_paragraph_from_job(job)
    source_text = _normalized_words(_string(source.get("text")))
    source_id = _string(source.get("id"))
    required = (
        "parent_paragraph_id",
        "segment_ordinal",
        "clarified_statement",
        "voice_anchor",
        "compression_ratio",
        "distillation_confidence",
        "gestures_towards",
        "compression_notes",
    )
    for index, raw_shard in enumerate(shards):
        if not isinstance(raw_shard, Mapping):
            violations.append(f"shards[{index}] must be object")
            continue
        shard = dict(raw_shard)
        for key in required:
            if key not in shard:
                violations.append(f"shards[{index}] missing required field: {key}")
        forbidden_surface_keys = [key for key in ("summary", "takeaway", "anchor") if key in shard]
        if forbidden_surface_keys:
            violations.append(
                f"shards[{index}] uses summary/takeaway/anchor surface {forbidden_surface_keys}; "
                "use clarified_statement plus verbatim voice_anchor"
            )
        clarified = _string(shard.get("clarified_statement"))
        voice_anchor = _string(shard.get("voice_anchor"))
        if not clarified:
            violations.append(f"shards[{index}].clarified_statement must be non-empty")
        if not voice_anchor:
            violations.append(f"shards[{index}].voice_anchor must be non-empty")
        if clarified and voice_anchor and _normalized_words(clarified) == _normalized_words(voice_anchor):
            violations.append(
                f"shards[{index}].clarified_statement merely repeats voice_anchor; "
                "rewrite the operator intent more clearly"
            )
        if clarified and voice_anchor and _word_count(voice_anchor) >= 8:
            similarity = difflib.SequenceMatcher(
                None,
                _normalized_words(clarified),
                _normalized_words(voice_anchor),
            ).ratio()
            if similarity >= 0.86:
                violations.append(
                    f"shards[{index}].clarified_statement is a cosmetic rewrite of voice_anchor "
                    f"(similarity={similarity:.2f}); name the underlying intent more clearly"
                )
        if source_text and voice_anchor and _normalized_words(voice_anchor) not in source_text:
            violations.append(
                f"shards[{index}].voice_anchor must be verbatim from source paragraph {source_id or '<unknown>'}"
            )
        parent = _string(shard.get("parent_paragraph_id"))
        if source_id and parent and parent != source_id:
            violations.append(
                f"shards[{index}].parent_paragraph_id mismatch: {parent!r} != {source_id!r}"
            )
        if "gestures_towards" in shard and not isinstance(shard.get("gestures_towards"), list):
            violations.append(f"shards[{index}].gestures_towards must be array")
        if "compression_notes" in shard and not isinstance(shard.get("compression_notes"), list):
            violations.append(f"shards[{index}].compression_notes must be array")
        for numeric_key in ("compression_ratio", "distillation_confidence"):
            if numeric_key in shard and (
                not isinstance(shard.get(numeric_key), (int, float))
                or isinstance(shard.get(numeric_key), bool)
            ):
                violations.append(f"shards[{index}].{numeric_key} must be number")
    return violations


def _evidence_ref_token(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("ref", "id", "event_id", "work_item_id", "path"):
            token = _string(value.get(key))
            if token:
                return token
        return ""
    return _string(value)


def _workitem_heartbeat_output_violations(
    payload: Mapping[str, Any],
    job: Mapping[str, Any],
) -> list[str]:
    if _string(job.get("target_facet")) != "workitem_heartbeat_readiness_flag":
        return []

    packet = _safe_mapping(job.get("input_packet"))
    allowed_refs = {
        _string(ref)
        for ref in _safe_list(packet.get("allowed_evidence_refs"))
        if _string(ref)
    }
    neighborhood = _safe_mapping(packet.get("connector_neighborhood"))
    allowed_flags = {
        _string(flag)
        for flag in _safe_list(packet.get("allowed_flags") or neighborhood.get("allowed_flags"))
        if _string(flag)
    }

    violations: list[str] = []
    evidence_refs = _safe_list(payload.get("evidence_refs"))
    if allowed_refs and not evidence_refs:
        violations.append("workitem_heartbeat_readiness_flag requires evidence_refs from allowed_evidence_refs")
    for ref in evidence_refs:
        token = _evidence_ref_token(ref)
        if allowed_refs and token not in allowed_refs:
            violations.append(
                f"workitem_heartbeat_readiness_flag evidence_ref {token!r} is not in allowed_evidence_refs"
            )
    flag = _string(payload.get("flag"))
    if allowed_flags and flag and flag not in allowed_flags:
        violations.append(
            f"workitem_heartbeat_readiness_flag flag {flag!r} is outside allowed_flags"
        )
    confidence = payload.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
        if confidence < 0 or confidence > 1:
            violations.append("workitem_heartbeat_readiness_flag confidence must be between 0 and 1")
    return violations


_PROVIDER_PLANE_APPLICATION_REQUIRED_FIELDS = {
    "candidate_id",
    "title",
    "source_refs",
    "input_surface",
    "task_class_or_carrier",
    "output_facet",
    "trigger_condition",
    "batch_shape",
    "reducer_gate",
    "authority_ceiling",
    "expected_value",
    "risk",
    "first_command_or_surface",
    "workitem_binding",
}


def _provider_plane_application_output_violations(
    payload: Mapping[str, Any],
    job: Mapping[str, Any],
) -> list[str]:
    if _string(job.get("target_facet")) != "provider_plane_application_candidate":
        return []

    packet = _safe_mapping(job.get("input_packet"))
    allowed_refs = {
        _string(ref)
        for ref in _safe_list(packet.get("allowed_source_refs") or packet.get("allowed_evidence_refs"))
        if _string(ref)
    }
    violations: list[str] = []
    candidates = payload.get("application_candidates")
    if not isinstance(candidates, list) or not candidates:
        violations.append("provider_plane_application_candidate requires non-empty application_candidates")
        return violations
    for index, raw_candidate in enumerate(candidates):
        if not isinstance(raw_candidate, Mapping):
            violations.append(f"application_candidates[{index}] must be object")
            continue
        candidate = dict(raw_candidate)
        missing = sorted(
            field for field in _PROVIDER_PLANE_APPLICATION_REQUIRED_FIELDS
            if field not in candidate
        )
        if missing:
            violations.append(f"application_candidates[{index}] missing required fields: {missing}")
        source_refs = _safe_list(candidate.get("source_refs"))
        if allowed_refs and not source_refs:
            violations.append(f"application_candidates[{index}] requires packet-bounded source_refs")
        for ref in source_refs:
            token = _evidence_ref_token(ref)
            if allowed_refs and token not in allowed_refs:
                violations.append(
                    f"provider_plane_application_candidate source_ref {token!r} is not in allowed_source_refs"
                )
        authority = _string(candidate.get("authority_ceiling"))
        if authority and authority not in {"provider_endpoint", "advisory_only", "draft_advisory"}:
            violations.append(
                f"application_candidates[{index}].authority_ceiling {authority!r} exceeds provider-plane advisory authority"
            )
        command = _string(candidate.get("first_command_or_surface")).lower()
        trigger = _string(candidate.get("trigger_condition")).lower()
        if "metabolismd" in command or "daemon" in command or "always-on" in trigger:
            violations.append(
                f"application_candidates[{index}] proposes daemon-first operation; provider plane requires finite pull-triggered batches"
            )
    confidence = payload.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
        if confidence < 0 or confidence > 1:
            violations.append("provider_plane_application_candidate confidence must be between 0 and 1")
    return violations


def _status_from_exception(exc: BaseException) -> str:
    text = str(exc).lower()
    if isinstance(exc, PermissionError):
        return "policy_reject"
    if "429" in text or "rate limit" in text:
        return "429"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if " 5" in text or "5xx" in text:
        return "5xx"
    return "worker_error"


def _call_provider(
    provider_id: str,
    prompt: str,
    *,
    model_id: str,
    budget: Mapping[str, Any],
    max_tokens: int,
    timeout_s: int,
    request_extras: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any], int | None]:
    """Wave 11: when `request_extras` carries provider-native structured-output
    parameters (OpenRouter `response_format` json_schema + `provider`
    block; NVIDIA `nvext.guided_json`), they override the default loose
    `json_object` mode and the actual transmitted shape is recorded as
    `transmitted_request_extras` so the receipt can prove what was sent
    on the wire."""
    # Wave 11.5: lane runners now key request_extras by provider id
    # ("openrouter_api" / "nvidia_nim"). Earlier waves used bare aliases
    # ("openrouter" / "nvidia"), which silently dropped on the wire.
    # Accept either shape so legacy callers remain functional while the
    # canonical path stays provider-id-keyed.
    _PROVIDER_KEY_ALIASES = {
        "openrouter_api": "openrouter",
        "nvidia_nim": "nvidia",
    }
    extras_for_provider: Mapping[str, Any] = {}
    if isinstance(request_extras, Mapping):
        candidate = request_extras.get(provider_id)
        if not isinstance(candidate, Mapping):
            alias = _PROVIDER_KEY_ALIASES.get(provider_id, "")
            if alias:
                candidate = request_extras.get(alias)
        if isinstance(candidate, Mapping):
            extras_for_provider = candidate

    transmitted_extras: dict[str, Any] = {
        "structured_output": False,
        "schema_name": None,
        "provider_native_field": None,
    }

    if provider_id == "openrouter_api":
        from system.lib import openrouter_free_runtime

        config: dict[str, Any] = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": 0,
            "timeout_s": timeout_s,
            "free_only": bool(budget.get("free_only", True)),
            "allow_paid": bool(budget.get("allow_paid", False)),
            "response_format": {"type": "json_object"},
        }
        rf = extras_for_provider.get("response_format") if isinstance(extras_for_provider, Mapping) else None
        if isinstance(rf, Mapping) and rf.get("type"):
            config["response_format"] = rf
            if rf.get("type") == "json_schema":
                js = rf.get("json_schema") or {}
                transmitted_extras = {
                    "structured_output": True,
                    "schema_name": str(js.get("name") or ""),
                    "provider_native_field": "response_format.json_schema",
                    "strict": bool(js.get("strict")),
                }
        provider_block = extras_for_provider.get("provider") if isinstance(extras_for_provider, Mapping) else None
        if isinstance(provider_block, Mapping):
            config["provider"] = provider_block
            transmitted_extras["require_parameters"] = bool(provider_block.get("require_parameters"))
        packet = openrouter_free_runtime.chat_completion_packet(
            prompt,
            config=config,
        )
        return (
            str(packet.get("response_text") or ""),
            dict(packet.get("usage") or {}),
            {
                "openrouter_packet": {k: v for k, v in packet.items() if k != "response_text"},
                "transmitted_request_extras": transmitted_extras,
            },
            None,
        )
    if provider_id == "nvidia_nim":
        from system.lib import nvidia_nim

        config = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": 0,
            "timeout_s": timeout_s,
        }
        rf = extras_for_provider.get("response_format") if isinstance(extras_for_provider, Mapping) else None
        if isinstance(rf, Mapping) and rf.get("type"):
            config["response_format"] = rf
            transmitted_extras = {
                "structured_output": bool(rf.get("type")),
                "schema_name": str(
                    ((rf.get("json_schema") or {}) if isinstance(rf.get("json_schema"), Mapping) else {}).get("name")
                    or ""
                ),
                "provider_native_field": "response_format",
            }
        nvext = extras_for_provider.get("nvext") if isinstance(extras_for_provider, Mapping) else None
        if isinstance(nvext, Mapping) and nvext.get("guided_json"):
            config["nvext"] = nvext
            transmitted_extras = {
                "structured_output": True,
                "schema_name": str((nvext.get("guided_json") or {}).get("schema_version") or "guided_json"),
                "provider_native_field": "nvext.guided_json",
            }
        text = nvidia_nim.chat_completion(prompt, config=config)
        return str(text), {}, {"transmitted_request_extras": transmitted_extras}, None
    raise ValueError(f"Unsupported lower-class provider: {provider_id}")


def _build_row_patch(
    job: Mapping[str, Any],
    receipt_id: str,
    parsed: Mapping[str, Any],
) -> dict[str, Any]:
    proposed_value: Any = dict(parsed)
    evidence_refs: list[Any] = []
    omissions: list[Any] = []
    confidence: Any = None
    uncertainty = ""
    if "proposed_value" in parsed:
        proposed_value = parsed.get("proposed_value")
        evidence_refs = _safe_list(parsed.get("evidence_refs"))
        omissions = _safe_list(parsed.get("omissions"))
        confidence = parsed.get("confidence")
        uncertainty = _string(parsed.get("worker_dissent_or_uncertainty"))
    else:
        evidence_refs = _safe_list(parsed.get("evidence_refs"))
        omissions = _safe_list(parsed.get("omissions"))
        confidence = parsed.get("confidence")
        uncertainty = _string(parsed.get("worker_dissent_or_uncertainty"))
    if confidence is None:
        confidence = 0.5 if omissions else 0.7
    return {
        "kind": "row_patch",
        "schema_version": ROW_PATCH_SCHEMA_VERSION,
        "patch_id": f"rp_{uuid.uuid4().hex[:16]}",
        "receipt_id": receipt_id,
        "target_row_id": job.get("target_row_id"),
        "target_facet": job.get("target_facet"),
        "target_band": job.get("target_band"),
        "proposed_value": proposed_value,
        "evidence_refs": evidence_refs,
        "omissions": omissions,
        "confidence": confidence,
        "worker_dissent_or_uncertainty": uncertainty,
        "validation_status": "valid",
        "promotion_state": "draft",
        "reject_reason": None,
        "created_at": _utc_now(),
    }


def _base_receipt(
    *,
    job: Mapping[str, Any],
    provider_id: str,
    model_id: str,
    prompt_hash: str,
    input_packet_digest: str,
    neighbor_context_hash: str,
    started_at: str,
) -> dict[str, Any]:
    return {
        "kind": "provider_receipt",
        "schema_version": PROVIDER_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"rc_{uuid.uuid4().hex[:16]}",
        "transform_job_id": job.get("id"),
        "provider_id": provider_id,
        "runtime_provider": PROVIDER_RUNTIME_TOKENS.get(provider_id, provider_id),
        "model_id": model_id,
        "task_class": job.get("task_class"),
        "prompt_hash": prompt_hash,
        "input_packet_digest": input_packet_digest,
        "output_schema_hash": _digest(job.get("output_schema") or {}),
        "local_evidence_override_policy_id": _string(
            _safe_mapping(job.get("local_evidence_override_policy")).get("policy_id")
        ),
        "cache_key": job.get("cache_key"),
        "source_fingerprints": _safe_list(job.get("source_fingerprints")),
        "neighbor_context_hash": neighbor_context_hash,
        "output_digest": None,
        "usage": {},
        "cost": {"unit": "free", "amount": 0.0, "billed_to": "account_tier"},
        "latency_ms": None,
        "http_status": None,
        "status": "worker_error",
        "validation_result": {"passed": False, "violations": []},
        "promotion_state": "rejected",
        "created_at": started_at,
        "persisted_at": None,
    }


def _write_receipt_and_patch(
    repo_root: Path,
    receipt: Mapping[str, Any],
    row_patch: Mapping[str, Any] | None,
) -> dict[str, Any]:
    receipt_path = _artifact_path(
        repo_root,
        "receipts",
        str(receipt.get("receipt_id")),
        created_at=str(receipt.get("created_at") or _utc_now()),
    )
    persisted_receipt = {**dict(receipt), "persisted_at": _utc_now()}
    _atomic_write_json(receipt_path, persisted_receipt)
    refs: dict[str, Any] = {"receipt": _rel(repo_root, receipt_path)}
    if row_patch:
        patch_id = str(row_patch.get("patch_id"))
        patch_path = _artifact_path(
            repo_root,
            "row_patches",
            patch_id,
            created_at=str(row_patch.get("created_at") or receipt.get("created_at") or _utc_now()),
        )
        _atomic_write_json(patch_path, row_patch)
        refs["row_patch"] = _rel(repo_root, patch_path)
    return refs


def _find_existing_receipt_path(repo_root: Path, receipt_id: str) -> Path | None:
    receipts_root = repo_root / DEFAULT_STATE_ROOT / "receipts"
    if not receipts_root.exists():
        return None
    matches = sorted(receipts_root.glob(f"*/{receipt_id}.json"))
    return matches[0] if matches else None


def write_candidate_skip_receipt(
    repo_root: Path = REPO_ROOT,
    *,
    candidate: Mapping[str, Any],
    receipt_kind: str = "skip",
    skip_reason: str | None = None,
    hard_vetoes: Sequence[str] | None = None,
    governor_mode: str | None = None,
    cpu_gate_state: Mapping[str, Any] | None = None,
    job_id: str | None = None,
) -> HarnessResult:
    """Persist a deduped skip/no-op/veto receipt for a candidate job.

    This records controller evidence for work the always-on loop deliberately
    did not run.  It never writes row patches and never promotes provider
    output; it only makes low-heat no-op/veto decisions replayable.
    """
    normalized_kind = _string(receipt_kind) or "skip"
    if normalized_kind not in {"skip", "no_op", "veto"}:
        raise ValueError("receipt_kind must be one of: skip, no_op, veto")
    candidate_id = _string(candidate.get("candidate_id"))
    source_fingerprint = _string(candidate.get("source_fingerprint"))
    vetoes = [
        _string(reason)
        for reason in (
            list(hard_vetoes or [])
            or list(candidate.get("hard_vetoes") or [])
            or list(candidate.get("skip_reasons") or [])
            or list(candidate.get("provider_dispatch_skip_reasons") or [])
        )
        if _string(reason)
    ]
    reason = _string(skip_reason) or (vetoes[0] if vetoes else f"candidate_{normalized_kind}")
    receipt_hard_vetoes = sorted(set(vetoes)) if normalized_kind == "veto" else []
    dedupe_key = _digest(
        {
            "schema_version": CANDIDATE_SKIP_RECEIPT_SCHEMA_VERSION,
            "receipt_kind": normalized_kind,
            "candidate_id": candidate_id,
            "source_fingerprint": source_fingerprint,
            "reason": reason,
            "hard_vetoes": receipt_hard_vetoes,
        }
    )
    receipt_id = f"rc_{normalized_kind}_{dedupe_key[:16]}"
    existing = _find_existing_receipt_path(Path(repo_root), receipt_id)
    if existing is not None:
        receipt = _read_json(existing)
        refs = {"receipt": _rel(Path(repo_root), existing), "deduped": True}
        return HarnessResult(receipt=receipt, row_patch=None, artifact_refs=refs)

    created_at = _utc_now()
    receipt = {
        "kind": "candidate_skip_receipt",
        "schema_version": CANDIDATE_SKIP_RECEIPT_SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "receipt_kind": normalized_kind,
        "candidate_id": candidate_id,
        "job_id": _string(job_id) or None,
        "source_signal_id": _string(candidate.get("source_signal_id")),
        "source_fingerprint": source_fingerprint,
        "target_row_kind": _string(candidate.get("target_row_kind")),
        "target_row_id": _string(candidate.get("target_row_id")),
        "provider_id": _string(candidate.get("provider_id")) or None,
        "model_id": _string(candidate.get("model_id")) or None,
        "task_class": _string(candidate.get("task_class") or candidate.get("candidate_job_class")),
        "authority_ceiling": _string(candidate.get("authority_ceiling")),
        "skip_reason": reason,
        "hard_vetoes": receipt_hard_vetoes,
        "score_vector": _safe_mapping(candidate.get("score_vector")),
        "cpu_gate_state": dict(cpu_gate_state or candidate.get("cpu_gate") or candidate.get("cpu_gate_state") or {}),
        "governor_mode": _string(governor_mode),
        "promotion_state": "not_promoted",
        "validation_result": {
            "passed": True,
            "violations": [],
            "status": normalized_kind,
        },
        "created_at": created_at,
        "persisted_at": None,
    }
    refs = _write_receipt_and_patch(Path(repo_root), receipt, None)
    refs["deduped"] = False
    persisted = _read_json(Path(repo_root) / refs["receipt"])
    return HarnessResult(receipt=persisted, row_patch=None, artifact_refs=refs)


def run_transform_job(
    repo_root: Path = REPO_ROOT,
    *,
    job: Mapping[str, Any] | None = None,
    job_path: str | Path | None = None,
    provider_id: str | None = None,
    model_id: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    seat_id: str | None = None,
) -> HarnessResult:
    if job is None:
        if job_path is None:
            raise ValueError("run_transform_job requires job or job_path")
        job = _read_json(_repo_path(repo_root, job_path))
    normalized = normalize_transform_job(repo_root, job)
    selected_provider, provider_row = _select_provider(repo_root, normalized, provider_id)
    if selected_provider not in LOWER_CLASS_PROVIDERS:
        raise PermissionError(f"provider {selected_provider} is not a lower-class Type A provider")
    if normalized["authority_ceiling"] not in {"provider_endpoint", "bounded_worker"}:
        raise PermissionError(f"authority ceiling {normalized['authority_ceiling']} is too high for lower-class worker")

    selected_model = _model_id(normalized, selected_provider, provider_row, model_id)
    prompt = _render_prompt(normalized)
    prompt_hash = _text_digest(prompt)
    input_digest = _digest(normalized.get("input_packet") or {})
    neighbor_hash = _digest(normalized.get("connector_neighborhood_ref") or "")
    fingerprint = _digest(
        {
            "provider_id": selected_provider,
            "model_id": selected_model,
            "cache_key": normalized.get("cache_key"),
            "prompt_hash": prompt_hash,
        }
    )
    cache_key = _string(normalized.get("cache_key"))
    started_at = _utc_now()
    receipt = _base_receipt(
        job=normalized,
        provider_id=selected_provider,
        model_id=selected_model,
        prompt_hash=prompt_hash,
        input_packet_digest=input_digest,
        neighbor_context_hash=neighbor_hash,
        started_at=started_at,
    )
    try:
        budget = _enforce_budget(normalized, selected_provider, selected_model)
        forbidden = _contains_forbidden_surface(normalized)
        if forbidden:
            raise PermissionError(f"input packet references forbidden surface: {forbidden}")
        prompt_boundary_violations = _formal_math_prompt_boundary_violations(normalized)
        if prompt_boundary_violations:
            raise PermissionError(
                "formal math prompt boundary violation: "
                + "; ".join(prompt_boundary_violations)
            )
    except Exception as exc:
        receipt["status"] = _status_from_exception(exc)
        receipt["validation_result"] = {"passed": False, "violations": [f"{type(exc).__name__}: {exc}"]}
        receipt["promotion_state"] = "rejected"
        if dry_run:
            return HarnessResult(
                receipt={**receipt, "dry_run": True, "artifact_refs": {}},
                row_patch=None,
                artifact_refs={},
            )
        refs = _write_receipt_and_patch(repo_root, receipt, None)
        return HarnessResult(receipt={**receipt, "artifact_refs": refs}, row_patch=None, artifact_refs=refs)

    if dry_run:
        receipt.update(
            {
                "status": "dry_run",
                "validation_result": {
                    "passed": True,
                    "violations": [],
                    "status": "dry_run",
                },
                "promotion_state": "not_promoted",
                "cost": {"unit": "free", "amount": 0.0, "billed_to": "dry_run"},
                "latency_ms": 0,
                "http_status": None,
                "usage": {},
                "provider_metadata": {"dry_run": True, "provider_id": selected_provider},
                "output_digest": _text_digest(
                    json.dumps({"dry_run": True, "provenance": {"provider_id": selected_provider}})
                ),
                "dry_run": True,
            }
        )
        return HarnessResult(
            receipt={**receipt, "artifact_refs": {}},
            row_patch=None,
            artifact_refs={},
        )

    if cache_key and not force:
        cache = _cache_path(repo_root, cache_key)
        if cache.exists():
            cached = _read_json(cache)
            cached_receipt = _string(cached.get("receipt"))
            if cached_receipt and (repo_root / cached_receipt).exists():
                receipt.update(
                    {
                        "status": "cache_hit",
                        "validation_result": {"passed": True, "violations": []},
                        "promotion_state": "draft",
                        "cost": {"unit": "free", "amount": 0.0, "billed_to": "cache"},
                        "cached_receipt": cached_receipt,
                    }
                )
                refs = _write_receipt_and_patch(repo_root, receipt, None)
                return HarnessResult(receipt={**receipt, "artifact_refs": refs}, row_patch=None, artifact_refs=refs)

    fp_path = _fingerprint_path(repo_root, fingerprint)
    if fp_path.exists() and not force:
        previous = _read_json(fp_path)
        previous_status = _string(previous.get("status"))
        if previous_status in FAILED_STATUSES or previous_status == "running":
            receipt.update(
                {
                    "status": "blocked_duplicate",
                    "validation_result": {
                        "passed": False,
                        "violations": [f"duplicate fingerprint after {previous_status}"],
                    },
                    "promotion_state": "rejected",
                    "duplicate_of": previous,
                }
            )
            refs = _write_receipt_and_patch(repo_root, receipt, None)
            return HarnessResult(receipt={**receipt, "artifact_refs": refs}, row_patch=None, artifact_refs=refs)

    _atomic_write_json(
        fp_path,
        {
            "fingerprint": fingerprint,
            "status": "running",
            "transform_job_id": normalized.get("id"),
            "provider_id": selected_provider,
            "model_id": selected_model,
            "prompt_hash": prompt_hash,
            "started_at": started_at,
        },
    )

    row_patch: dict[str, Any] | None = None
    raw_text = ""
    call_started = time.monotonic()
    try:
        if selected_provider == "nvidia_nim":
            from system.lib.nvidia_runtime import NvidiaGlobalRateLimiter

            receipt["provider_rate_limit"] = NvidiaGlobalRateLimiter(repo_root).acquire(
                operation="type_a_worker_transform_job",
                batch_id=_string(normalized.get("task_class")) or None,
                source_kind=_string(normalized.get("target_facet")) or None,
                request_size=len(prompt),
                model=selected_model,
            )
        max_tokens = int(_safe_mapping(normalized.get("execution_profile")).get("max_tokens") or 512)
        timeout_s = int(_safe_mapping(normalized.get("failure_policy")).get("timeout_s") or 90)
        request_extras = (
            _safe_mapping(normalized.get("provider_selection_policy")).get("request_extras")
            or {}
        )
        raw_text, usage, provider_meta, http_status = _call_provider(
            selected_provider,
            prompt,
            model_id=selected_model,
            budget=budget,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            request_extras=request_extras,
        )
        parsed, parse_violations = _extract_json(raw_text)
        schema_violations = _schema_violations(parsed or {}, _safe_mapping(normalized.get("output_schema")))
        task_violations = [
            *_raw_seed_candidate_output_violations(parsed or {}, normalized),
            *_workitem_heartbeat_output_violations(parsed or {}, normalized),
            *_provider_plane_application_output_violations(parsed or {}, normalized),
        ]
        violations = [*parse_violations, *schema_violations, *task_violations]
        latency_ms = int((time.monotonic() - call_started) * 1000)
        receipt["latency_ms"] = latency_ms
        receipt["http_status"] = http_status
        receipt["usage"] = usage
        receipt["provider_metadata"] = provider_meta
        receipt["output_digest"] = _text_digest(raw_text)
        # Wave 11: surface what was actually transmitted on the wire for
        # provider-native structured-output. The adapter records it inside
        # provider_metadata; promote it to a top-level receipt field so
        # the lane runner can verify schema transmission without parsing
        # provider_metadata.
        if isinstance(provider_meta, Mapping):
            transmitted = provider_meta.get("transmitted_request_extras")
            if transmitted is not None:
                receipt["transmitted_request_extras"] = transmitted
        if violations:
            receipt["status"] = "empty_response" if "empty response" in violations else "schema_fail"
            receipt["validation_result"] = {"passed": False, "violations": violations}
            receipt["promotion_state"] = "rejected"
        else:
            assert parsed is not None
            receipt["status"] = "ok"
            receipt["validation_result"] = {"passed": True, "violations": []}
            receipt["promotion_state"] = "draft"
            row_patch = _build_row_patch(normalized, str(receipt["receipt_id"]), parsed)
    except Exception as exc:
        receipt["status"] = _status_from_exception(exc)
        receipt["validation_result"] = {"passed": False, "violations": [f"{type(exc).__name__}: {exc}"]}
        receipt["promotion_state"] = "rejected"
        receipt["output_digest"] = _text_digest(raw_text) if raw_text else None

    # Mark the receipt for the Approvals lane when produced outside a seat
    # context and the promotion_state is draft-eligible. The loader in
    # system/lib/approval_registry.py filters on this explicit review marker
    # so draft receipts produced inside a seat dispatch are never double-
    # surfaced.
    if seat_id:
        receipt["seat_id"] = seat_id
        receipt["approval_review_state"] = "bound_to_seat"
    elif str(receipt.get("promotion_state") or "").strip() == "draft":
        receipt["approval_review_state"] = "pending_review"

    refs = _write_receipt_and_patch(repo_root, receipt, row_patch)
    fp_payload = {
        "fingerprint": fingerprint,
        "status": receipt["status"],
        "transform_job_id": normalized.get("id"),
        "provider_id": selected_provider,
        "model_id": selected_model,
        "receipt": refs.get("receipt"),
        "updated_at": _utc_now(),
    }
    _atomic_write_json(fp_path, fp_payload)
    if receipt["status"] == "ok" and cache_key:
        _atomic_write_json(
            _cache_path(repo_root, cache_key),
            {
                "cache_key": cache_key,
                "receipt": refs.get("receipt"),
                "row_patch": refs.get("row_patch"),
                "provider_id": selected_provider,
                "model_id": selected_model,
                "output_digest": receipt.get("output_digest"),
                "created_at": _utc_now(),
            },
        )
    return HarnessResult(receipt={**receipt, "artifact_refs": refs}, row_patch=row_patch, artifact_refs=refs)
