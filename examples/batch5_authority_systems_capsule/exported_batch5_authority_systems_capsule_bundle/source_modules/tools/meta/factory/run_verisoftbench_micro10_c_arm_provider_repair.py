#!/usr/bin/env python3
"""Run the VeriSoftBench micro-10 C-arm provider repair pass.

This is the first solving arm for the local micro-slice.  It uses the official
VeriSoftBench annex dataset/context and a governed OpenAI-compatible provider
route, then checks every candidate with Lean/Lake.  Provider output is
advisory: solved means Lean accepts the generated proof body.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import nvidia_nim, openrouter_free_runtime
from tools.meta.factory import build_external_benchmark_calibration_spine as calibration
from tools.meta.factory import run_verisoftbench_micro10_calibration_rows as row_executor
from tools.meta.factory import run_verisoftbench_micro10_harness_differential as harness


SCHEMA_VERSION = "verisoftbench_c_arm_provider_repair_receipt_v0"
MANIFEST_SCHEMA_VERSION = "verisoftbench_c_arm_provider_repair_manifest_v0"
CHECK_SCHEMA_VERSION = "verisoftbench_c_arm_provider_repair_check_v0"
SUMMARY_SCHEMA_VERSION = "verisoftbench_c_arm_provider_repair_summary_v0"
MODEL_POLICY_SCHEMA_VERSION = "verisoftbench_c_arm_model_policy_live_shortlist_v0"
CLAIM_BOUNDARY = "micro_slice_c_arm_provider_repair_not_full_benchmark_score"
OPENROUTER_PROVIDER_ROUTE = "openrouter"
NVIDIA_PROVIDER_ROUTE = "trickle:nvidia_nim"
PROVIDER_ROUTE = OPENROUTER_PROVIDER_ROUTE
PROVIDER_ID = "openrouter"
WORK_ITEM_ID = calibration.WORK_ITEM_ID
OWNER_ID = calibration.OWNER_ID

ANNEX_REPO_ROOT = harness.ANNEX_REPO_ROOT
OFFICIAL_DATASET_PATH = harness.OFFICIAL_DATASET_PATH
C_ARM_ROOT = calibration.CALIBRATION_ROOT / "c_arm_provider_repair"
C_ARM_MANIFEST_PATH = C_ARM_ROOT / "c_arm_provider_repair_manifest.json"
C_ARM_MODEL_POLICY_PATH = C_ARM_ROOT / "c_arm_model_policy_live_shortlist.json"
C_ARM_RECEIPT_NAME = "c_arm_provider_repair_receipt.json"

DEFAULT_TARGET_TASK_IDS = (
    "verisoftbench:2",
    "verisoftbench:4",
    "verisoftbench:5",
    "verisoftbench:6",
    "verisoftbench:7",
    "verisoftbench:8",
    "verisoftbench:9",
    "verisoftbench:10",
)
MODEL_SELECTION_ORDER = (
    "z-ai/glm-5.1",
    "z-ai/glm4.7",
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
)
OPENROUTER_MIN_CONTEXT_LENGTH = 65_536
OPENROUTER_SELECTION_STRATEGIES = (
    "preferred-serious",
    "chinese-scout",
    "chinese-promotion",
    "chinese-premium",
    "chinese-ladder",
    "cheapest",
    "cheapest-paid",
    "free-first",
)
OPENROUTER_CHINESE_SCOUT_MODEL_IDS = (
    "deepseek/deepseek-v4-flash",
    "qwen/qwen3.6-35b-a3b",
    "minimax/minimax-m2.5",
    "qwen/qwen3.6-flash",
)
OPENROUTER_CHINESE_PROMOTION_MODEL_IDS = (
    "deepseek/deepseek-v4-pro",
    "qwen/qwen3.6-plus",
    "minimax/minimax-m2.7",
    "qwen/qwen3.6-max-preview",
)
OPENROUTER_CHINESE_PREMIUM_MODEL_IDS = (
    "moonshotai/kimi-k2.6",
    "z-ai/glm-5.1",
)
OPENROUTER_CHINESE_LADDER_MODEL_IDS = (
    *OPENROUTER_CHINESE_SCOUT_MODEL_IDS,
    *OPENROUTER_CHINESE_PROMOTION_MODEL_IDS,
    *OPENROUTER_CHINESE_PREMIUM_MODEL_IDS,
)
OPENROUTER_PREFERRED_SERIOUS_MODEL_IDS = (
    *OPENROUTER_CHINESE_LADDER_MODEL_IDS,
    "google/gemini-2.5-flash",
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-sonnet-4",
)
OPENROUTER_STRUCTURED_NAMES = {"structured_outputs", "response_format"}
OPENROUTER_DEFAULT_REASONING_MAX_TOKENS = 1024
OPENROUTER_SKIP_MODEL_ID_TOKENS = (
    "embedding",
    "embed",
    "rerank",
    "moderation",
    "tts",
    "transcribe",
    "image",
    "vision",
)
PROOF_CONTRACT_FAILED_STATUS = "provider_contract_failed_pre_lean"
LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS = "provider_schema_failed_plan_or_nonproof"
IDENTIFIER_GATE_SCHEMA_VERSION = "verisoftbench_c_arm_identifier_resolution_gate_v0"
IDENTIFIER_GATE_FAILED_STATUS = "identifier_gate_failed_pre_full_lean"
IDENTIFIER_GATE_TIMEOUT_STATUS = "identifier_gate_timeout_pre_full_lean"
IDENTIFIER_GATE_FAILURE_CLASS = "identifier_gate_unknown_identifier"

LEAN_TACTIC_OR_KEYWORD_ALLOWLIST = {
    "all_goals",
    "apply",
    "assumption",
    "at",
    "by",
    "by_cases",
    "calc",
    "case",
    "change",
    "constructor",
    "contradiction",
    "dsimp",
    "exact",
    "ext",
    "field_simp",
    "fin_cases",
    "first",
    "fun",
    "have",
    "intro",
    "intros",
    "left",
    "let",
    "omega",
    "obtain",
    "rcases",
    "refine",
    "rename_i",
    "repeat",
    "revert",
    "rfl",
    "right",
    "ring",
    "ring_nf",
    "rw",
    "simp",
    "simp_all",
    "simpa",
    "skip",
    "subst",
    "suffices",
    "try",
    "unfold",
    "use",
}
LEAN_BUILTIN_ALLOWLIST = {
    "False",
    "Fin",
    "Finset",
    "Function",
    "HAdd",
    "HMul",
    "HSub",
    "Int",
    "List",
    "Nat",
    "Prop",
    "Set",
    "True",
    "Type",
    "by_contra",
    "congrArg",
    "decide",
    "default",
    "id",
    "nomatch",
    "show",
}
LEAN_DECLARATION_KEYWORDS = (
    "abbrev",
    "axiom",
    "class",
    "def",
    "example",
    "inductive",
    "instance",
    "lemma",
    "opaque",
    "structure",
    "theorem",
)
LEMMA_LIKE_IDENTIFIER_HINTS = (
    "_add_",
    "_and_",
    "_eq_",
    "_iff",
    "_le_",
    "_lt_",
    "_mem_",
    "_mod_",
    "_mul_",
    "_of_",
    "_one",
    "_prod",
    "_range",
    "_root",
    "_succ",
    "_two",
    "_zero",
)

PROOF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "lean_proof_body",
        "uses",
        "strategy_summary",
        "expected_failure_modes",
    ],
    "properties": {
        "lean_proof_body": {"type": "string"},
        "uses": {"type": "array", "items": {"type": "string"}},
        "strategy_summary": {"type": "string"},
        "expected_failure_modes": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


def _proof_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "verisoftbench_proof_body_candidate",
            "strict": True,
            "schema": PROOF_SCHEMA,
        },
    }


def _provider_id(provider_route: str) -> str:
    token = str(provider_route or "").strip()
    if token == OPENROUTER_PROVIDER_ROUTE:
        return "openrouter"
    if token in {NVIDIA_PROVIDER_ROUTE, "nvidia_nim"}:
        return "nvidia_nim"
    return token or "unknown"


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _openrouter_price(row: Mapping[str, Any]) -> float:
    pricing = row.get("pricing_usd_per_million_tokens")
    if isinstance(pricing, Mapping):
        return float(_as_float(pricing.get("one_m_input_plus_one_m_output")) or 0.0)
    raw_pricing = row.get("pricing")
    if isinstance(raw_pricing, Mapping):
        prompt = _as_float(raw_pricing.get("prompt")) or 0.0
        completion = _as_float(raw_pricing.get("completion")) or 0.0
        return round((prompt + completion) * 1_000_000, 6)
    return 0.0


def _openrouter_context_length(row: Mapping[str, Any]) -> int:
    parsed = _as_float(row.get("context_length"))
    if parsed is None:
        top_provider = row.get("top_provider") if isinstance(row.get("top_provider"), Mapping) else {}
        parsed = _as_float(top_provider.get("context_length"))
    return int(parsed or 0)


def _openrouter_is_free(row: Mapping[str, Any]) -> bool:
    model_id = str(row.get("id") or "")
    if model_id.endswith(":free") or model_id == openrouter_free_runtime.FREE_ROUTER_MODEL_ID:
        return True
    pricing = row.get("pricing_usd_per_million_tokens")
    if isinstance(pricing, Mapping):
        return _openrouter_price(row) == 0.0
    return bool(row.get("free") or row.get("pricing_zero"))


def _openrouter_supports_structured(row: Mapping[str, Any]) -> bool:
    flags = row.get("capability_flags")
    if isinstance(flags, Mapping) and flags.get("structured_output") is True:
        return True
    supported = row.get("supported_parameters")
    if isinstance(supported, list):
        return bool(OPENROUTER_STRUCTURED_NAMES.intersection(str(item) for item in supported))
    return False


def _openrouter_candidate_allowed(row: Mapping[str, Any], *, min_context_length: int) -> bool:
    model_id = str(row.get("id") or "").strip()
    if not model_id:
        return False
    lowered = model_id.lower()
    if any(token in lowered for token in OPENROUTER_SKIP_MODEL_ID_TOKENS):
        return False
    if _openrouter_context_length(row) and _openrouter_context_length(row) < min_context_length:
        return False
    return _openrouter_supports_structured(row)


def _openrouter_candidate_rows(
    status: Mapping[str, Any],
    *,
    selection_strategy: str,
    allow_paid: bool,
    min_context_length: int,
) -> list[dict[str, Any]]:
    models = status.get("models") if isinstance(status.get("models"), Mapping) else {}
    snapshot = models.get("opportunity_snapshot") if isinstance(models.get("opportunity_snapshot"), Mapping) else {}
    free_rows = [
        dict(row)
        for row in snapshot.get("free_tool_structured_long_context") or []
        if isinstance(row, Mapping)
    ]
    paid_rows = [
        dict(row)
        for row in snapshot.get("cheapest_paid_tool_structured") or []
        if isinstance(row, Mapping)
    ]
    if selection_strategy == "cheapest-paid":
        raw_rows = paid_rows if allow_paid else []
    elif selection_strategy == "free-first":
        raw_rows = free_rows + (paid_rows if allow_paid else [])
    else:
        raw_rows = free_rows + (paid_rows if allow_paid else [])

    deduped: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        model_id = str(row.get("id") or "").strip()
        if not model_id or model_id in deduped:
            continue
        if not _openrouter_candidate_allowed(row, min_context_length=min_context_length):
            continue
        if not allow_paid and not _openrouter_is_free(row):
            continue
        deduped[model_id] = row

    rows = list(deduped.values())
    if selection_strategy == "free-first":
        return sorted(
            rows,
            key=lambda row: (
                0 if _openrouter_is_free(row) else 1,
                _openrouter_price(row),
                -_openrouter_context_length(row),
                str(row.get("id") or ""),
            ),
        )
    return sorted(
        rows,
        key=lambda row: (
            _openrouter_price(row),
            0 if _openrouter_is_free(row) else 1,
            -_openrouter_context_length(row),
            str(row.get("id") or ""),
        ),
    )


def _openrouter_known_model_rows(status: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    models = status.get("models") if isinstance(status.get("models"), Mapping) else {}
    rows_by_id: dict[str, dict[str, Any]] = {}
    for row in models.get("ranked_free_models") or []:
        if isinstance(row, Mapping) and row.get("id"):
            rows_by_id[str(row["id"])] = dict(row)
    snapshot = models.get("opportunity_snapshot") if isinstance(models.get("opportunity_snapshot"), Mapping) else {}
    for key in (
        "free_tool_structured_long_context",
        "cheapest_paid_text",
        "cheapest_paid_tool_structured",
        "cheapest_paid_long_context",
    ):
        for row in snapshot.get(key) or []:
            if isinstance(row, Mapping) and row.get("id"):
                rows_by_id[str(row["id"])] = {**rows_by_id.get(str(row["id"]), {}), **dict(row)}
    return rows_by_id


def _model_ids_for_openrouter_strategy(selection_strategy: str) -> tuple[str, ...] | None:
    if selection_strategy == "chinese-scout":
        return OPENROUTER_CHINESE_SCOUT_MODEL_IDS
    if selection_strategy == "chinese-promotion":
        return OPENROUTER_CHINESE_PROMOTION_MODEL_IDS
    if selection_strategy == "chinese-premium":
        return OPENROUTER_CHINESE_PREMIUM_MODEL_IDS
    if selection_strategy == "chinese-ladder":
        return OPENROUTER_CHINESE_LADDER_MODEL_IDS
    return None


def _model_policy_row(
    row: Mapping[str, Any],
    *,
    tier: str,
    rank: int,
    min_context_length: int,
    allow_paid: bool,
) -> dict[str, Any]:
    model_id = str(row.get("id") or "").strip()
    supported = row.get("supported_parameters") if isinstance(row.get("supported_parameters"), list) else []
    flags = row.get("capability_flags") if isinstance(row.get("capability_flags"), Mapping) else {}
    pricing = row.get("pricing_usd_per_million_tokens") if isinstance(row.get("pricing_usd_per_million_tokens"), Mapping) else {}
    eligible = (
        bool(model_id)
        and _openrouter_candidate_allowed(row, min_context_length=min_context_length)
        and (allow_paid or _openrouter_is_free(row))
    )
    missing_reasons: list[str] = []
    if not model_id:
        missing_reasons.append("missing_model_id")
    if _openrouter_context_length(row) and _openrouter_context_length(row) < min_context_length:
        missing_reasons.append("context_length_below_minimum")
    if not _openrouter_supports_structured(row):
        missing_reasons.append("structured_output_not_reported")
    if not allow_paid and not _openrouter_is_free(row):
        missing_reasons.append("paid_model_not_authorized")
    if row.get("metadata_missing"):
        missing_reasons.append("metadata_missing_from_live_models_api")
    return {
        "rank": rank,
        "tier": tier,
        "id": model_id,
        "name": row.get("name") or model_id,
        "eligible": eligible,
        "ineligibility_reasons": missing_reasons,
        "context_length": _openrouter_context_length(row) or row.get("context_length"),
        "pricing_usd_per_million_tokens": pricing,
        "capability_flags": {
            "structured_output": bool(flags.get("structured_output") or _openrouter_supports_structured(row)),
            "reasoning": bool(flags.get("reasoning") or ("reasoning" in supported) or ("include_reasoning" in supported)),
            "tools": bool(flags.get("tools") or ("tools" in supported)),
        },
        "supported_parameters": supported,
    }


def _openrouter_live_chinese_model_policy(
    status: Mapping[str, Any],
    *,
    allow_paid: bool,
    min_context_length: int,
    selection_strategy: str,
) -> dict[str, Any]:
    rows_by_id = _openrouter_known_model_rows(status)
    tiers = {
        "scout": OPENROUTER_CHINESE_SCOUT_MODEL_IDS,
        "promotion": OPENROUTER_CHINESE_PROMOTION_MODEL_IDS,
        "premium": OPENROUTER_CHINESE_PREMIUM_MODEL_IDS,
    }
    rows: list[dict[str, Any]] = []
    for tier, model_ids in tiers.items():
        for index, model_id in enumerate(model_ids, start=1):
            raw = dict(rows_by_id.get(model_id) or {"id": model_id, "metadata_missing": True})
            rows.append(
                _model_policy_row(
                    raw,
                    tier=tier,
                    rank=index,
                    min_context_length=min_context_length,
                    allow_paid=allow_paid,
                )
            )
    eligible_by_tier: dict[str, list[str]] = {}
    for tier in tiers:
        eligible_by_tier[tier] = [row["id"] for row in rows if row.get("tier") == tier and row.get("eligible")]
    return {
        "schema_version": MODEL_POLICY_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "provider_route": OPENROUTER_PROVIDER_ROUTE,
        "source": "OpenRouter live /api/v1/models metadata",
        "selection_strategy": selection_strategy,
        "allow_paid": allow_paid,
        "min_context_length": min_context_length,
        "required_parameters": ["response_format", "structured_outputs", "reasoning", "include_reasoning", "tools"],
        "tiers": {
            "scout": list(OPENROUTER_CHINESE_SCOUT_MODEL_IDS),
            "promotion": list(OPENROUTER_CHINESE_PROMOTION_MODEL_IDS),
            "premium": list(OPENROUTER_CHINESE_PREMIUM_MODEL_IDS),
        },
        "eligible_by_tier": eligible_by_tier,
        "rows": rows,
        "claim_boundary": "model_metadata_routing_prior_not_benchmark_result",
    }


def _openrouter_policy_candidate_rows(
    status: Mapping[str, Any],
    *,
    model_ids: Sequence[str],
    allow_paid: bool,
    min_context_length: int,
) -> list[dict[str, Any]]:
    rows_by_id = _openrouter_known_model_rows(status)
    rows: list[dict[str, Any]] = []
    for model_id in model_ids:
        row = dict(rows_by_id.get(model_id) or {"id": model_id, "metadata_missing": True})
        if not allow_paid and not _openrouter_is_free(row):
            continue
        if not _openrouter_candidate_allowed(row, min_context_length=min_context_length):
            continue
        rows.append(row)
    return rows


def _openrouter_preferred_candidate_rows(
    status: Mapping[str, Any],
    *,
    allow_paid: bool,
    min_context_length: int,
) -> list[dict[str, Any]]:
    rows_by_id = _openrouter_known_model_rows(status)
    rows: list[dict[str, Any]] = []
    for model_id in OPENROUTER_PREFERRED_SERIOUS_MODEL_IDS:
        row = dict(rows_by_id.get(model_id) or {"id": model_id, "metadata_missing": True})
        if not allow_paid and not _openrouter_is_free(row):
            continue
        if not _openrouter_candidate_allowed(row, min_context_length=min_context_length):
            continue
        rows.append(row)
    return rows


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _task_slug(task_id: str) -> str:
    return task_id.replace(":", "_")


def receipt_dir(task_id: str, *, repo_root: Path = REPO_ROOT) -> Path:
    return _repo_path(C_ARM_ROOT / _task_slug(task_id), repo_root=repo_root)


def receipt_path(task_id: str) -> Path:
    return C_ARM_ROOT / _task_slug(task_id) / C_ARM_RECEIPT_NAME


def _clip_text(value: str, limit: int = 12000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 2 :]
    return f"{head}\n\n/- clipped {len(text) - len(head) - len(tail)} chars -/\n\n{tail}"


def _dataset_entries(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    path = _repo_path(OFFICIAL_DATASET_PATH, repo_root=repo_root)
    entries: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return entries
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            task_id = f"verisoftbench:{row.get('id')}"
            if task_id in calibration.VERISOFTBENCH_TASK_IDS:
                entries[task_id] = row
    return entries


def _harness_receipt(task_id: str, *, repo_root: Path) -> dict[str, Any]:
    return _read_json_if_exists(_repo_path(harness.receipt_path(task_id), repo_root=repo_root))


def _row_execution_receipt(task_id: str, *, repo_root: Path) -> dict[str, Any]:
    return _read_json_if_exists(_repo_path(row_executor.row_receipt_path(task_id), repo_root=repo_root))


def _entry_context_lists(entry: Mapping[str, Any]) -> dict[str, Any]:
    sections: dict[str, Any] = {}
    for key in (
        "used_local_defs",
        "used_local_lemmas",
        "used_repo_defs",
        "repo_lemmas",
        "used_lib_defs",
        "lib_lemmas",
    ):
        rows = entry.get(key) if isinstance(entry.get(key), list) else []
        compact_rows = []
        for row in rows[:24]:
            if not isinstance(row, Mapping):
                continue
            compact_rows.append(
                {
                    "name": row.get("name"),
                    "module": row.get("module"),
                    "content": _clip_text(str(row.get("content") or ""), limit=800)
                    if row.get("content")
                    else None,
                }
            )
        sections[key] = compact_rows
    return sections


def _lean_feedback_excerpt(result: Mapping[str, Any]) -> str:
    text = str(result.get("stdout") or "") + "\n" + str(result.get("stderr") or "")
    return _clip_text(text, limit=6000)


def _prompt_packet(
    *,
    entry: Mapping[str, Any],
    row_receipt: Mapping[str, Any],
    harness_receipt: Mapping[str, Any],
    previous_attempt: Mapping[str, Any] | None,
    repair_round: int,
    context_mode: str,
) -> dict[str, Any]:
    thm_name = str(entry.get("thm_name") or "")
    short_name = thm_name.rsplit(".", 1)[-1]
    packet: dict[str, Any] = {
        "schema_version": "verisoftbench_c_arm_provider_prompt_packet_v0",
        "benchmark": "VeriSoftBench",
        "task_id": f"verisoftbench:{entry.get('id')}",
        "context_mode": context_mode,
        "authority": "Lean/Lake is the only proof authority.",
        "claim_boundary": "advisory_candidate_only",
        "ground_truth_used_for_provider": False,
        "target": {
            "theorem_name": thm_name,
            "short_theorem_name": short_name,
            "statement": str(entry.get("thm_stmt") or entry.get("target_theorem") or ""),
            "lean_root": entry.get("lean_root"),
            "rel_path": entry.get("rel_path"),
        },
        "official_filtered_context": {
            "imports": entry.get("imports") if isinstance(entry.get("imports"), list) else [],
            "local_context_excerpt": _clip_text(str(entry.get("local_ctx") or entry.get("local_ctxs") or ""), limit=9000),
            **_entry_context_lists(entry),
        },
        "symbol_grounding_contract": {
            **_collect_allowed_symbols(entry),
            "identifier_resolution_gate": "Before full theorem verification, the runner resolves claimed and extracted global identifiers in the target Lean environment. Out-of-scope identifiers are rejected and fed back for repair.",
        },
        "row_execution_evidence": {
            "status": row_receipt.get("status"),
            "statement_scope_status": row_receipt.get("statement_scope_status"),
            "failure_class": row_receipt.get("failure_class"),
            "lean_status": row_receipt.get("lean_status"),
            "receipt_refs": row_receipt.get("receipt_refs") or [],
        },
        "harness_differential_evidence": {
            "diagnosis": harness_receipt.get("diagnosis"),
            "official_ground_truth_check": harness_receipt.get("official_ground_truth_check"),
            "support_prefix_ground_truth_check": harness_receipt.get("support_prefix_ground_truth_check"),
            "receipt_ref": _rel(harness.receipt_path(f"verisoftbench:{entry.get('id')}")),
        },
        "response_contract": {
            "required_json_schema": PROOF_SCHEMA,
            "lean_proof_body_rule": "Return only the proof body, normally beginning with `by`. Do not return a theorem statement.",
            "invalid_outputs": [
                "plan only",
                "natural language proof only",
                "theorem restatement",
                "self-reference to the target theorem",
                "uses unavailable lemma names",
                "missing lean_proof_body",
                "sorry/admit placeholder",
            ],
            "forbidden_self_reference": [
                thm_name,
                short_name,
            ],
        },
    }
    if previous_attempt:
        previous_unknowns = previous_attempt.get("unresolved_identifiers")
        forbidden_identifiers = previous_unknowns if isinstance(previous_unknowns, list) else []
        packet["repair_feedback"] = {
            "repair_round": repair_round,
            "previous_lean_proof_body": previous_attempt.get("lean_proof_body"),
            "previous_status": previous_attempt.get("best_attempt_status"),
            "lean_feedback_excerpt": previous_attempt.get("lean_feedback_excerpt"),
            "forbidden_identifiers_from_previous_attempt": forbidden_identifiers,
            "instruction": "Repair the prior proof body using only this Lean feedback and the supplied context.",
        }
    return packet


def _prompt_text(packet: Mapping[str, Any]) -> str:
    return (
        "You are producing one Lean 4 proof body for a VeriSoftBench task.\n"
        "Return exactly one JSON object satisfying the provided schema. "
        "Do not include markdown fences. Do not return a plan. "
        "Do not claim success. Do not use the target theorem as a premise. "
        "Do not use sorry or admit.\n\n"
        + json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
    )


def _extract_json_object_with_metadata(text: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    stripped = text.strip()
    metadata: dict[str, Any] = {
        "raw_text_length": len(text),
        "fenced_output": False,
        "exact_json_object": False,
        "extracted_from_surrounding_text": False,
        "json_parse_status": "not_run",
    }
    if stripped.startswith("```"):
        metadata["fenced_output"] = True
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        payload = json.loads(stripped)
        metadata["json_parse_status"] = "exact_json_loaded"
        metadata["exact_json_object"] = isinstance(payload, dict)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            metadata["json_parse_status"] = "no_json_object_bounds"
            return None, metadata
        try:
            payload = json.loads(stripped[start : end + 1])
            metadata["json_parse_status"] = "extracted_json_loaded"
            metadata["extracted_from_surrounding_text"] = True
        except json.JSONDecodeError:
            metadata["json_parse_status"] = "json_decode_failed"
            return None, metadata
    if not isinstance(payload, dict):
        metadata["json_parse_status"] = "json_not_object"
        return None, metadata
    return payload, metadata


def _extract_json_object(text: str) -> dict[str, Any] | None:
    payload, _metadata = _extract_json_object_with_metadata(text)
    return payload


def _proof_contract_gate(
    payload: Mapping[str, Any] | None,
    *,
    target_name: str,
    raw_text: str,
    extraction_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = dict(extraction_metadata or {})
    violations: list[dict[str, Any]] = []
    if payload is None:
        lowered = str(raw_text or "").lower()
        code = "plan_or_nonproof"
        if not str(raw_text or "").strip():
            code = "empty_response"
        elif "```" in lowered or "<lean4_proof>" in lowered or "<fixed_lean4" in lowered:
            code = "tag_mismatch"
        elif "plan" in lowered or "strategy" in lowered or "approach" in lowered:
            code = "plan_or_nonproof"
        elif "lean_proof_body" not in lowered:
            code = "missing_json_object"
        violations.append({"code": code, "message": "provider output did not parse as the required JSON proof-body object"})
    else:
        proof = payload.get("lean_proof_body")
        if not isinstance(proof, str) or not proof.strip():
            violations.append({"code": "missing_proof_body", "message": "lean_proof_body is missing or empty"})
        else:
            lowered_proof = proof.lower()
            if "sorry" in lowered_proof or "admit" in lowered_proof:
                violations.append({"code": "forbidden_placeholder", "message": "proof body contains sorry/admit"})
            if "```" in proof or "<lean4_proof>" in proof or "<fixed_lean4" in proof:
                violations.append({"code": "tag_mismatch", "message": "proof body contains code fences or official prompt tags"})
            if re.search(r"\b(theorem|lemma)\b", proof):
                violations.append({"code": "repeated_theorem_declaration", "message": "proof body repeats a theorem or lemma declaration"})
            short = target_name.rsplit(".", 1)[-1]
            for forbidden in (target_name, short):
                if forbidden and re.search(rf"(?<![A-Za-z0-9_.']){re.escape(forbidden)}(?![A-Za-z0-9_.'])", proof):
                    violations.append({"code": "target_self_reference", "message": f"target theorem self-reference: {forbidden}"})
                    break
        if not isinstance(payload.get("uses"), list):
            violations.append({"code": "uses_not_array", "message": "uses must be an array"})
        if not isinstance(payload.get("strategy_summary"), str):
            violations.append({"code": "strategy_summary_not_string", "message": "strategy_summary must be a string"})
        if not isinstance(payload.get("expected_failure_modes"), list):
            violations.append({"code": "expected_failure_modes_not_array", "message": "expected_failure_modes must be an array"})
        if metadata.get("extracted_from_surrounding_text"):
            violations.append({"code": "extra_natural_language", "message": "JSON object was embedded in surrounding text"})
        if metadata.get("fenced_output"):
            violations.append({"code": "tag_mismatch", "message": "provider wrapped the JSON in a code fence"})

    priority = (
        "missing_proof_body",
        "missing_json_object",
        "empty_response",
        "plan_or_nonproof",
        "repeated_theorem_declaration",
        "forbidden_placeholder",
        "target_self_reference",
        "tag_mismatch",
        "extra_natural_language",
        "uses_not_array",
        "strategy_summary_not_string",
        "expected_failure_modes_not_array",
    )
    seen = {str(row.get("code")) for row in violations}
    primary = next((code for code in priority if code in seen), None)
    if primary is None and violations:
        primary = str(violations[0].get("code") or "contract_failed")
    return {
        "schema_version": "verisoftbench_provider_proof_contract_gate_v0",
        "status": "PASS" if not violations else "FAIL",
        "ok": not violations,
        "failure_class": None if not violations else f"provider_contract_{primary}",
        "legacy_failure_class": None if not violations else LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS,
        "violations": violations,
        "violation_codes": [str(row.get("code")) for row in violations],
        "extraction": metadata,
    }


def _validate_provider_payload(payload: Mapping[str, Any], *, target_name: str) -> list[str]:
    gate = _proof_contract_gate(payload, target_name=target_name, raw_text=json.dumps(dict(payload), ensure_ascii=False))
    return [str(row.get("message") or row.get("code")) for row in gate.get("violations") or [] if isinstance(row, Mapping)]


def _extract_declared_symbols(text: str) -> set[str]:
    symbols: set[str] = set()
    for keyword in LEAN_DECLARATION_KEYWORDS:
        pattern = rf"(?m)^\s*(?:private\s+|protected\s+)?{keyword}\s+([A-Za-z_][A-Za-z0-9_'.]*)"
        symbols.update(match.group(1).strip() for match in re.finditer(pattern, text))
    return {symbol for symbol in symbols if symbol and symbol != "_"}


def _extract_local_symbols(text: str) -> set[str]:
    locals_seen: set[str] = set()
    for pattern in (
        r"[\(\{\[]\s*([A-Za-z_][A-Za-z0-9_']*)\s*:",
        r"\b∀\s+([A-Za-z_][A-Za-z0-9_']*)\s*[,:\.]",
        r"\bfun\s+([A-Za-z_][A-Za-z0-9_']*)\s*=>",
        r"\bhave\s+([A-Za-z_][A-Za-z0-9_']*)\s*:",
        r"\blet\s+([A-Za-z_][A-Za-z0-9_']*)\s*:=",
        r"\bcase\s+([A-Za-z_][A-Za-z0-9_']*)\b",
        r"\brename_i\s+([A-Za-z_][A-Za-z0-9_']*)\b",
    ):
        locals_seen.update(match.group(1).strip() for match in re.finditer(pattern, text))
    return {symbol for symbol in locals_seen if symbol and symbol != "_"}


def _collect_allowed_symbols(entry: Mapping[str, Any]) -> dict[str, Any]:
    context_text = "\n".join(
        str(entry.get(key) or "")
        for key in ("local_ctx", "local_ctxs", "thm_stmt", "target_theorem")
        if entry.get(key)
    )
    named_context_symbols: set[str] = set()
    for rows in _entry_context_lists(entry).values():
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping) and row.get("name"):
                    named_context_symbols.add(str(row["name"]))
    declared = _extract_declared_symbols(context_text)
    target_name = str(entry.get("thm_name") or "")
    target_short = target_name.rsplit(".", 1)[-1]
    allowed = sorted(
        symbol
        for symbol in (named_context_symbols | declared | LEAN_BUILTIN_ALLOWLIST)
        if symbol and symbol not in {target_name, target_short}
    )
    locals_seen = sorted(_extract_local_symbols(context_text))
    return {
        "schema_version": "verisoftbench_c_arm_allowed_symbol_packet_v0",
        "allowed_symbols": allowed[:500],
        "allowed_symbol_count": len(allowed),
        "local_symbols": locals_seen[:240],
        "standard_tactics": sorted(LEAN_TACTIC_OR_KEYWORD_ALLOWLIST),
        "policy": "Qualified/global identifiers should resolve in the target Lean environment. Prefer local hypotheses, standard tactics, and allowed_symbols; do not invent lemma names.",
    }


def _strip_lean_comments_and_strings(text: str) -> str:
    no_block = re.sub(r"/-.*?-/", " ", text, flags=re.DOTALL)
    no_line = re.sub(r"--.*", " ", no_block)
    return re.sub(r'"(?:[^"\\]|\\.)*"', '""', no_line)


def _looks_lemma_like_identifier(token: str) -> bool:
    if "." in token:
        return True
    if token in LEAN_BUILTIN_ALLOWLIST or token in LEAN_TACTIC_OR_KEYWORD_ALLOWLIST:
        return False
    if token and token[0].isupper():
        return True
    return any(hint in token for hint in LEMMA_LIKE_IDENTIFIER_HINTS)


def _extract_candidate_identifiers(
    *,
    proof_body: str,
    uses: Any,
    target_name: str,
    local_symbols: set[str] | None = None,
) -> list[str]:
    local = set(local_symbols or set())
    target_short = target_name.rsplit(".", 1)[-1]
    candidates: set[str] = set()
    if isinstance(uses, list):
        for item in uses:
            token = str(item or "").strip()
            if token and token not in local:
                candidates.add(token)
    text = _strip_lean_comments_and_strings(proof_body)
    token_re = r"(?<![A-Za-z0-9_'.])([A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*)(?![A-Za-z0-9_'.])"
    for match in re.finditer(token_re, text):
        token = match.group(1).strip()
        if not token or token in local or token in {target_name, target_short}:
            continue
        if token in LEAN_TACTIC_OR_KEYWORD_ALLOWLIST or token in LEAN_BUILTIN_ALLOWLIST:
            continue
        if _looks_lemma_like_identifier(token):
            candidates.add(token)
    return sorted(candidates)


def _normalize_proof_body(value: str) -> str:
    proof = value.strip()
    if proof.startswith(":= by\n") or proof.startswith(":= by\r\n"):
        first, rest = proof.split("\n", 1)
        return first + "\n" + _normalize_tactic_block(rest)
    if proof.startswith(":="):
        return proof
    if proof == "by":
        return ":= by"
    if proof.startswith("by\n") or proof.startswith("by\r\n"):
        _, rest = proof.split("\n", 1)
        return ":= by\n" + _normalize_tactic_block(rest)
    if proof.startswith("by "):
        return f":= {proof}"
    return ":= by\n" + _normalize_tactic_block(proof)


def _normalize_tactic_block(block: str) -> str:
    lines = block.splitlines()
    non_empty_indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    min_indent = min(non_empty_indents) if non_empty_indents else 0
    normalized: list[str] = []
    previous_indent = 0
    previous_requires_child = False
    for raw_line in lines:
        if not raw_line.strip():
            normalized.append("")
            continue
        stripped = raw_line.strip()
        original_indent = len(raw_line) - len(raw_line.lstrip())
        indent = max(2, original_indent - min_indent + 2)
        if previous_requires_child and indent <= previous_indent:
            indent = previous_indent + 2
        normalized.append(" " * indent + stripped)
        previous_indent = indent
        previous_requires_child = stripped.endswith("=>") or stripped.endswith(":= by") or stripped == "by"
    return "\n".join(normalized)


def _classify_lean_failure(result: Mapping[str, Any]) -> str:
    status = str(result.get("compile_status") or "")
    text = (str(result.get("stdout") or "") + "\n" + str(result.get("stderr") or "")).lower()
    if status == "PASS":
        return "lean_accepted"
    if status == "TIMEOUT" or "timeout" in text or "timed out" in text:
        return "lean_timeout"
    if "unknown identifier" in text or "unknown constant" in text:
        return "lean_rejected_unknown_identifier"
    if "application type mismatch" in text or "type mismatch" in text:
        return "lean_rejected_type_mismatch"
    if "unsolved goals" in text or "goals unsolved" in text:
        return "lean_rejected_unsolved_goals"
    if "tactic" in text:
        return "lean_rejected_tactic_failure"
    return "lean_rejected"


def _dominant_attempt_status_and_failure(attempts: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    status_counts = Counter(str(row.get("status") or "unknown") for row in attempts)
    failure_counts = Counter(str(row.get("failure_class") or "unknown") for row in attempts)
    return (
        status_counts.most_common(1)[0][0] if status_counts else "unknown",
        failure_counts.most_common(1)[0][0] if failure_counts else "unknown",
    )


def _dominant_receipt_status_and_failure(receipt: Mapping[str, Any]) -> tuple[str, str]:
    status_payload = receipt.get("status_counts")
    failure_payload = receipt.get("failure_counts")
    status_counts = Counter(
        {str(key): int(value) for key, value in dict(status_payload or {}).items()}
        if isinstance(status_payload, Mapping)
        else {}
    )
    failure_counts = Counter(
        {str(key): int(value) for key, value in dict(failure_payload or {}).items()}
        if isinstance(failure_payload, Mapping)
        else {}
    )
    return (
        status_counts.most_common(1)[0][0] if status_counts else str(receipt.get("best_attempt_status") or "unknown"),
        failure_counts.most_common(1)[0][0] if failure_counts else str(receipt.get("failure_class") or "unknown"),
    )


def _provider_call(
    *,
    provider_route: str,
    prompt: str,
    model_id: str,
    timeout_seconds: int,
    seed: int,
    request_policy: Mapping[str, Any] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    policy = dict(request_policy or {})
    base_config = {
        "model": model_id,
        "timeout_s": timeout_seconds,
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 0.95,
        "seed": seed,
        "response_format": _proof_response_format(),
    }
    reasoning_max_tokens = int(policy.get("reasoning_max_tokens") or 0)
    if reasoning_max_tokens > 0:
        base_config["reasoning"] = {"max_tokens": reasoning_max_tokens}
        base_config["include_reasoning"] = False
    if provider_route == OPENROUTER_PROVIDER_ROUTE:
        provider_policy = {"sort": "price"}
        if policy.get("require_parameters") is True:
            provider_policy["require_parameters"] = True
        packet = openrouter_free_runtime.chat_completion_packet(
            prompt,
            config={
                **base_config,
                "free_only": False,
                "allow_paid": True,
                "provider": provider_policy,
            },
        )
        return (
            str(packet.get("response_text") or ""),
            "openrouter.response_format.json_schema",
            {
                key: value
                for key, value in packet.items()
                if key not in {"response_text"}
            },
        )
    try:
        return (
            nvidia_nim.chat_completion(
                prompt,
                config={**base_config, "nvext": {"guided_json": PROOF_SCHEMA}},
            ),
            "nvext.guided_json",
            {},
        )
    except Exception as guided_exc:
        text = str(guided_exc).lower()
        if "guided_json" not in text and "nvext" not in text and "json" not in text:
            raise
        return nvidia_nim.chat_completion(prompt, config=base_config), "response_format.json_object", {}


def _lean_canary_check(
    *,
    proof_body: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    lean_bin = shutil.which("lean")
    if not lean_bin:
        return {"status": "skipped", "reason": "lean executable not found"}
    with tempfile.TemporaryDirectory(prefix="verisoftbench_proof_canary_") as tmp:
        path = Path(tmp) / "OpenRouterProofBodyCanary.lean"
        path.write_text(
            "theorem openrouter_proof_body_canary (n : Nat) : n + 0 = n "
            + _normalize_proof_body(proof_body)
            + "\n#print axioms openrouter_proof_body_canary\n",
            encoding="utf-8",
        )
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [lean_bin, str(path)],
                cwd=str(REPO_ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(5, min(timeout_seconds, 30)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "duration_ms": int((time.monotonic() - started) * 1000)}
        return {
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "exit_code": completed.returncode,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "stdout_excerpt": _clip_text(completed.stdout or "", limit=1200),
            "stderr_excerpt": _clip_text(completed.stderr or "", limit=1200),
        }


def _openrouter_proof_body_canary(
    *,
    model_id: str,
    timeout_seconds: int,
    request_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    prompt = (
        "You are passing a Lean proof-body output-contract canary. "
        "Return exactly one JSON object, no markdown, no prose, no theorem declaration.\n"
        "Target theorem:\n"
        "theorem openrouter_proof_body_canary (n : Nat) : n + 0 = n :=\n\n"
        "Required schema:\n"
        + json.dumps(PROOF_SCHEMA, ensure_ascii=False, sort_keys=True)
        + "\n\nThe lean_proof_body must be a complete Lean proof body for the target, normally `by simp`."
    )
    canary_reasoning_max_tokens = min(int((request_policy or {}).get("reasoning_max_tokens") or 0), 64)
    try:
        packet = openrouter_free_runtime.chat_completion_packet(
            prompt,
            config={
                "model": model_id,
                "timeout_s": timeout_seconds,
                "max_tokens": 512,
                "temperature": 0,
                "response_format": _proof_response_format(),
                "free_only": False,
                "allow_paid": True,
                "provider": {
                    "sort": "price",
                    **({"require_parameters": True} if (request_policy or {}).get("require_parameters") is True else {}),
                },
                **(
                    {
                        "reasoning": {"max_tokens": canary_reasoning_max_tokens},
                        "include_reasoning": False,
                    }
                    if canary_reasoning_max_tokens > 0
                    else {}
                ),
            },
        )
        raw = str(packet.get("response_text") or "")
        payload, extraction = _extract_json_object_with_metadata(raw)
        gate = _proof_contract_gate(
            payload,
            target_name="OpenRouter.openrouter_proof_body_canary",
            raw_text=raw,
            extraction_metadata=extraction,
        )
        lean_canary = (
            _lean_canary_check(
                proof_body=str(payload.get("lean_proof_body") or ""),
                timeout_seconds=timeout_seconds,
            )
            if payload is not None and gate.get("ok") is True
            else {"status": "NOT_RUN"}
        )
        ok = gate.get("ok") is True and lean_canary.get("status") in {"PASS", "skipped"}
        return {
            "status": "ok" if ok else "proof_contract_failed",
            "model": packet.get("model") or model_id,
            "requested_model": model_id,
            "usage": packet.get("usage"),
            "finish_reason": packet.get("finish_reason"),
            "proof_contract": gate,
            "lean_canary": lean_canary,
            "violations": gate.get("violation_codes") or [],
        }
    except Exception as exc:
        return {
            "status": "error",
            "requested_model": model_id,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _select_openrouter_model(
    *,
    timeout_seconds: int,
    explicit_model_id: str | None,
    selection_strategy: str,
    allow_paid: bool,
    min_context_length: int,
    canary: bool,
    require_parameters: bool,
    reasoning_max_tokens: int,
) -> dict[str, Any]:
    request_policy = {
        "require_parameters": bool(require_parameters),
        "reasoning_max_tokens": int(reasoning_max_tokens or 0),
        "provider_sort": "price",
        "response_format": "json_schema",
        "cache_prefix_policy": "stable_system_and_schema_prefix_best_effort",
    }
    status = openrouter_free_runtime.runtime_status(
        {
            "timeout_s": timeout_seconds,
            "free_only": not allow_paid,
            "allow_paid": allow_paid,
        },
        probe_live=True,
        include_models=True,
        top_n=600,
    )
    live_probe = status.get("live_probe") if isinstance(status.get("live_probe"), Mapping) else {}
    if live_probe.get("status") != "ok":
        return {
            "status": "provider_unavailable",
            "provider_route": OPENROUTER_PROVIDER_ROUTE,
            "provider_id": "openrouter",
            "runtime_status": status,
            "selected_model_id": None,
            "candidate_models": [],
        }

    model_policy = _openrouter_live_chinese_model_policy(
        status,
        allow_paid=allow_paid,
        min_context_length=min_context_length,
        selection_strategy=selection_strategy,
    )
    strategy_model_ids = _model_ids_for_openrouter_strategy(selection_strategy)

    if explicit_model_id:
        known = _openrouter_known_model_rows(status)
        candidate_rows = [{**known.get(explicit_model_id, {}), "id": explicit_model_id, "explicit": True}]
    elif strategy_model_ids is not None:
        candidate_rows = _openrouter_policy_candidate_rows(
            status,
            model_ids=strategy_model_ids,
            allow_paid=allow_paid,
            min_context_length=min_context_length,
        )
    elif selection_strategy == "preferred-serious":
        candidate_rows = _openrouter_preferred_candidate_rows(
            status,
            allow_paid=allow_paid,
            min_context_length=min_context_length,
        )
        if not candidate_rows:
            candidate_rows = _openrouter_candidate_rows(
                status,
                selection_strategy="cheapest",
                allow_paid=allow_paid,
                min_context_length=min_context_length,
            )
    else:
        candidate_rows = _openrouter_candidate_rows(
            status,
            selection_strategy=selection_strategy,
            allow_paid=allow_paid,
            min_context_length=min_context_length,
        )
    canary_results: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for row in candidate_rows:
        model_id = str(row.get("id") or "").strip()
        if not model_id:
            continue
        result = (
            _openrouter_proof_body_canary(
                model_id=model_id,
                timeout_seconds=min(timeout_seconds, 90),
                request_policy=request_policy,
            )
            if canary
            else {"status": "skipped", "requested_model": model_id}
        )
        canary_results.append(result)
        if not canary or result.get("status") == "ok":
            selected = row
            break
    selected_id = str((selected or {}).get("id") or "")
    key_info = status.get("key_info") if isinstance(status.get("key_info"), Mapping) else {}
    return {
        "status": "ok" if selected_id else "provider_unavailable",
        "provider_route": OPENROUTER_PROVIDER_ROUTE,
        "provider_id": "openrouter",
        "runtime_status": {
            "configured": status.get("configured"),
            "limits": status.get("limits"),
            "key_info": {
                key: key_info.get(key)
                for key in (
                    "is_free_tier",
                    "credit_limit_usd",
                    "credit_limit_remaining_usd",
                    "usage",
                    "usage_daily",
                )
                if key in key_info
            },
            "live_probe": live_probe,
        },
        "candidate_models": [str(row.get("id") or "") for row in candidate_rows],
        "selected_model_id": selected_id or None,
        "selected_model_metadata": selected or {},
        "canary_status": (canary_results[-1].get("status") if selected_id and canary_results else "not_run"),
        "canary_results": canary_results,
        "live_model_policy": model_policy,
        "selection_policy": {
            "context": "OpenRouter live /api/v1/models inventory ranked by cheapest eligible text model with structured-output support and context budget.",
            "strategy": selection_strategy,
            "allow_paid": allow_paid,
            "explicit_model_id": explicit_model_id,
            "min_context_length": min_context_length,
            "proof_body_canary_required": canary,
            "request_policy": request_policy,
            "cost_basis": "OpenRouter pricing metadata, USD per one million prompt plus one million completion tokens; free zero-cost rows sort first unless cheapest-paid is requested.",
            "operator_authorization": "current turn explicitly requested OpenRouter API keys and cheapest model for this C-arm run",
        },
        "request_policy": request_policy,
    }


def _select_nvidia_model(*, timeout_seconds: int) -> dict[str, Any]:
    status = nvidia_nim.runtime_status({"timeout_s": timeout_seconds}, probe_live=True)
    live_probe = status.get("live_probe") if isinstance(status.get("live_probe"), Mapping) else {}
    if live_probe.get("status") != "ok":
        return {
            "status": "provider_unavailable",
            "provider_route": NVIDIA_PROVIDER_ROUTE,
            "provider_id": "nvidia_nim",
            "runtime_status": status,
            "selected_model_id": None,
            "candidate_models": [],
        }
    try:
        all_models = set(nvidia_nim.list_models(config={"timeout_s": timeout_seconds}))
    except Exception as exc:
        return {
            "status": "provider_unavailable",
            "provider_route": NVIDIA_PROVIDER_ROUTE,
            "provider_id": "nvidia_nim",
            "runtime_status": status,
            "selected_model_id": None,
            "candidate_models": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
    candidates = [model for model in MODEL_SELECTION_ORDER if model in all_models]
    selected = candidates[0] if candidates else str((status.get("configured") or {}).get("chat_model") or "")
    return {
        "status": "ok" if selected else "provider_unavailable",
        "provider_route": NVIDIA_PROVIDER_ROUTE,
        "provider_id": "nvidia_nim",
        "runtime_status": {
            "configured": status.get("configured"),
            "limits": status.get("limits"),
            "live_probe": {
                key: value for key, value in live_probe.items() if key != "models_sample"
            },
        },
        "candidate_models": candidates,
        "selected_model_id": selected or None,
        "selection_policy": {
            "context": "prefer cheap/fast coding-capable NIM models visible in live /v1/models",
            "order": list(MODEL_SELECTION_ORDER),
            "cost_basis": "cost_basis_unavailable_from_live_probe",
        },
    }


def _select_model(
    *,
    provider_route: str,
    timeout_seconds: int,
    explicit_model_id: str | None,
    openrouter_selection_strategy: str,
    openrouter_allow_paid: bool,
    openrouter_min_context_length: int,
    openrouter_canary: bool,
    openrouter_require_parameters: bool,
    openrouter_reasoning_max_tokens: int,
) -> dict[str, Any]:
    route = str(provider_route or PROVIDER_ROUTE)
    if route == OPENROUTER_PROVIDER_ROUTE:
        return _select_openrouter_model(
            timeout_seconds=timeout_seconds,
            explicit_model_id=explicit_model_id,
            selection_strategy=openrouter_selection_strategy,
            allow_paid=openrouter_allow_paid,
            min_context_length=openrouter_min_context_length,
            canary=openrouter_canary,
            require_parameters=openrouter_require_parameters,
            reasoning_max_tokens=openrouter_reasoning_max_tokens,
        )
    if route in {NVIDIA_PROVIDER_ROUTE, "nvidia_nim"}:
        return _select_nvidia_model(timeout_seconds=timeout_seconds)
    return {
        "status": "provider_unavailable",
        "provider_route": route,
        "provider_id": _provider_id(route),
        "selected_model_id": None,
        "candidate_models": [],
        "error": f"unsupported provider_route: {route}",
    }


def _official_verify_context(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    repo_root: Path,
) -> tuple[Any, str, str, str, str, str]:
    _, official_utils = harness._load_official_modules(repo_root)
    local_context, thm_stmt, _ground_truth_proof, suffix = harness._official_context(
        entry=entry,
        workspace_root=workspace_root,
        official_utils=official_utils,
    )
    lean_root = str(entry.get("lean_root") or "")
    rel_path = str(entry.get("rel_path") or "")
    source_path = workspace_root.parent / lean_root / rel_path
    full_file_content = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    remaining_mutual_content = (
        official_utils.get_remaining_mutual_content(full_file_content, thm_stmt, local_context)
        if full_file_content
        else ""
    )
    return official_utils, local_context, thm_stmt, suffix, remaining_mutual_content, str(source_path)


def _identifier_resolution_gate(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    repo_root: Path,
    out_dir: Path,
    sample_index: int,
    repair_round: int,
    proof_body: str,
    payload: Mapping[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    official_utils, local_context, _thm_stmt, _suffix, _remaining_mutual_content, _source_path = _official_verify_context(
        entry=entry,
        workspace_root=workspace_root,
        repo_root=repo_root,
    )
    del official_utils
    target_name = str(entry.get("thm_name") or "")
    symbol_packet = _collect_allowed_symbols(entry)
    local_symbols = set(symbol_packet.get("local_symbols") or [])
    local_symbols.update(_extract_local_symbols(proof_body))
    candidates = _extract_candidate_identifiers(
        proof_body=proof_body,
        uses=payload.get("uses"),
        target_name=target_name,
        local_symbols=local_symbols,
    )
    if not candidates:
        return {
            "schema_version": IDENTIFIER_GATE_SCHEMA_VERSION,
            "status": "PASS",
            "checked_identifier_count": 0,
            "checked_identifiers": [],
            "unresolved_identifiers": [],
            "allowed_symbol_count": symbol_packet.get("allowed_symbol_count"),
            "source_ref": None,
        }

    check_path = out_dir / f"identifier_gate_s{sample_index:02d}_r{repair_round:02d}.lean"
    stdout_path = out_dir / f"identifier_gate_s{sample_index:02d}_r{repair_round:02d}_stdout.txt"
    stderr_path = out_dir / f"identifier_gate_s{sample_index:02d}_r{repair_round:02d}_stderr.txt"
    check_lines = [local_context.rstrip(), "", "/- Identifier resolution gate: global names only, no theorem proof. -/"]
    for identifier in candidates:
        check_lines.append(f"#check {identifier}")
    _write_text(check_path, "\n".join(check_lines) + "\n")
    result = row_executor._run_lake_env_lean(
        check_path,
        workspace_root=workspace_root,
        timeout_seconds=max(10, min(timeout_seconds, 90)),
    )
    stdout = str(result.get("stdout") or "")
    stderr = str(result.get("stderr") or "")
    _write_text(stdout_path, stdout)
    _write_text(stderr_path, stderr)
    text = stdout + "\n" + stderr
    unresolved = sorted(
        set(
            re.findall(r"unknown (?:constant|identifier) ['\"]([^'\"]+)['\"]", text)
            + re.findall(r"unknown (?:constant|identifier) ([A-Za-z_][A-Za-z0-9_'.]*)", text)
        )
    )
    if result.get("compile_status") == "TIMEOUT":
        status = "TIMEOUT"
        failure_class = "identifier_gate_timeout"
    elif result.get("compile_status") == "PASS":
        status = "PASS"
        failure_class = None
    elif unresolved:
        status = "FAIL"
        failure_class = IDENTIFIER_GATE_FAILURE_CLASS
    else:
        status = "FAIL"
        failure_class = "identifier_gate_resolution_failed"
    return {
        "schema_version": IDENTIFIER_GATE_SCHEMA_VERSION,
        "status": status,
        "failure_class": failure_class,
        "checked_identifier_count": len(candidates),
        "checked_identifiers": candidates,
        "unresolved_identifiers": unresolved,
        "allowed_symbol_count": symbol_packet.get("allowed_symbol_count"),
        "source_ref": _rel(check_path, repo_root=repo_root),
        "source_sha256": _sha256_file(check_path),
        "stdout_ref": _rel(stdout_path, repo_root=repo_root),
        "stdout_sha256": _sha256_file(stdout_path),
        "stderr_ref": _rel(stderr_path, repo_root=repo_root),
        "stderr_sha256": _sha256_file(stderr_path),
        "stdout_excerpt": _clip_text(stdout, limit=1600),
        "stderr_excerpt": _clip_text(stderr, limit=1600),
        "duration_ms": result.get("duration_ms"),
    }


def _verify_candidate(
    *,
    entry: Mapping[str, Any],
    workspace_root: Path,
    repo_root: Path,
    out_dir: Path,
    sample_index: int,
    repair_round: int,
    proof_body: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    official_utils, local_context, thm_stmt, suffix, remaining_mutual_content, source_path = _official_verify_context(
        entry=entry,
        workspace_root=workspace_root,
        repo_root=repo_root,
    )
    theorem_proof = _normalize_proof_body(proof_body)
    content = official_utils.format_generated_lean(
        local_context,
        thm_stmt,
        theorem_proof,
        "",
        suffix,
        remaining_mutual_content,
    )
    lean_path = out_dir / f"candidate_s{sample_index:02d}_r{repair_round:02d}.lean"
    stdout_path = out_dir / f"candidate_s{sample_index:02d}_r{repair_round:02d}_stdout.txt"
    stderr_path = out_dir / f"candidate_s{sample_index:02d}_r{repair_round:02d}_stderr.txt"
    _write_text(lean_path, content)
    result = row_executor._run_lake_env_lean(
        lean_path,
        workspace_root=workspace_root,
        timeout_seconds=timeout_seconds,
    )
    _write_text(stdout_path, str(result.get("stdout") or ""))
    _write_text(stderr_path, str(result.get("stderr") or ""))
    return {
        "compile_status": result.get("compile_status"),
        "exit_code": result.get("exit_code"),
        "duration_ms": result.get("duration_ms"),
        "timeout": result.get("timeout"),
        "lean_source_ref": _rel(lean_path, repo_root=repo_root),
        "lean_source_sha256": _sha256_file(lean_path),
        "stdout_ref": _rel(stdout_path, repo_root=repo_root),
        "stdout_sha256": _sha256_file(stdout_path),
        "stderr_ref": _rel(stderr_path, repo_root=repo_root),
        "stderr_sha256": _sha256_file(stderr_path),
        "source_path": source_path,
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _blocked_receipt(
    *,
    task_id: str,
    status: str,
    failure_class: str,
    issues: Sequence[str],
    provider_selection: Mapping[str, Any] | None,
    repo_root: Path,
    context_mode: str,
    num_samples: int,
    repair_rounds: int,
) -> dict[str, Any]:
    route = str((provider_selection or {}).get("provider_route") or PROVIDER_ROUTE)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "task_id": task_id,
        "work_item_id": WORK_ITEM_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "official_leaderboard_submission": False,
        "public_claim_allowed": False,
        "protocol_arm": "C_provider_repair_filtered_context",
        "context_mode": context_mode,
        "attempt_budget": num_samples,
        "repair_round_budget": repair_rounds,
        "provider_route": route,
        "provider_id": str((provider_selection or {}).get("provider_id") or _provider_id(route)),
        "provider_model": (provider_selection or {}).get("selected_model_id"),
        "provider_attempt_count": 0,
        "lean_check_count": 0,
        "accepted_by_lean": False,
        "solved": False,
        "best_attempt_status": status,
        "failure_class": failure_class,
        "status": status,
        "ground_truth_used_for_provider": False,
        "score_counted_ground_truth": False,
        "receipt_refs": [],
        "issues": list(issues),
        "provider_selection": provider_selection or {},
    }
    _write_json(_repo_path(receipt_path(task_id), repo_root=repo_root), receipt)
    return receipt


def run_task(
    task_id: str,
    *,
    repo_root: Path = REPO_ROOT,
    provider_selection: Mapping[str, Any],
    num_samples: int = 8,
    repair_rounds: int = 3,
    context_mode: str = "filtered_context",
    lean_timeout_seconds: int = 180,
    provider_timeout_seconds: int = 180,
    max_lean_timeouts_per_row: int = 0,
    force: bool = False,
) -> dict[str, Any]:
    out_dir = receipt_dir(task_id, repo_root=repo_root)
    if force and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    existing_path = out_dir / C_ARM_RECEIPT_NAME
    if not force and existing_path.exists():
        existing = _read_json_if_exists(existing_path)
        if existing.get("schema_version") == SCHEMA_VERSION:
            return existing

    entries = _dataset_entries(repo_root=repo_root)
    entry = entries.get(task_id)
    workspace_root = row_executor._workspace_root(repo_root=repo_root)
    row_receipt = _row_execution_receipt(task_id, repo_root=repo_root)
    harness_receipt = _harness_receipt(task_id, repo_root=repo_root)
    selected_model = str(provider_selection.get("selected_model_id") or "")
    provider_route = str(provider_selection.get("provider_route") or PROVIDER_ROUTE)
    provider_id = str(provider_selection.get("provider_id") or _provider_id(provider_route))
    provider_request_policy = (
        provider_selection.get("request_policy")
        if isinstance(provider_selection.get("request_policy"), Mapping)
        else {}
    )
    if entry is None:
        return _blocked_receipt(
            task_id=task_id,
            status="blocked_official_dataset_entry_missing",
            failure_class="blocked_official_dataset_entry_missing",
            issues=[f"{task_id} missing from {OFFICIAL_DATASET_PATH}"],
            provider_selection=provider_selection,
            repo_root=repo_root,
            context_mode=context_mode,
            num_samples=num_samples,
            repair_rounds=repair_rounds,
        )
    if workspace_root is None:
        return _blocked_receipt(
            task_id=task_id,
            status="blocked_workspace_missing",
            failure_class="blocked_workspace_missing",
            issues=["pinned Lean workspace missing from oracle environment gate receipt"],
            provider_selection=provider_selection,
            repo_root=repo_root,
            context_mode=context_mode,
            num_samples=num_samples,
            repair_rounds=repair_rounds,
        )
    if harness_receipt.get("diagnosis") != "real_proof_search_needed":
        return _blocked_receipt(
            task_id=task_id,
            status="blocked_harness_not_validated_for_c_arm",
            failure_class="blocked_harness_not_validated_for_c_arm",
            issues=[f"harness diagnosis is {harness_receipt.get('diagnosis')}"],
            provider_selection=provider_selection,
            repo_root=repo_root,
            context_mode=context_mode,
            num_samples=num_samples,
            repair_rounds=repair_rounds,
        )
    if provider_selection.get("status") != "ok" or not selected_model:
        return _blocked_receipt(
            task_id=task_id,
            status="provider_unavailable",
            failure_class="provider_unavailable",
            issues=[str(provider_selection.get("error") or "no selected provider model")],
            provider_selection=provider_selection,
            repo_root=repo_root,
            context_mode=context_mode,
            num_samples=num_samples,
            repair_rounds=repair_rounds,
        )

    created_at = _utc_now()
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    provider_attempt_count = 0
    lean_check_count = 0
    identifier_check_count = 0
    accepted_attempt: dict[str, Any] | None = None
    best_attempt_status = "provider_not_called"
    failure_class = "provider_unavailable"
    last_provider_call = 0.0
    limits = (provider_selection.get("runtime_status") or {}).get("limits")
    interval = 1.5 if provider_route == OPENROUTER_PROVIDER_ROUTE else float(
        (limits or {}).get("recommended_min_interval_seconds")
        or (limits or {}).get("recommended_min_interval_seconds_for_always_on")
        or 1.5
    )

    for sample_index in range(1, num_samples + 1):
        previous_attempt: dict[str, Any] | None = None
        for repair_round in range(0, repair_rounds + 1):
            prompt_packet = _prompt_packet(
                entry=entry,
                row_receipt=row_receipt,
                harness_receipt=harness_receipt,
                previous_attempt=previous_attempt,
                repair_round=repair_round,
                context_mode=context_mode,
            )
            prompt = _prompt_text(prompt_packet)
            prompt_path = out_dir / f"prompt_s{sample_index:02d}_r{repair_round:02d}.json"
            raw_output_path = out_dir / f"provider_output_s{sample_index:02d}_r{repair_round:02d}.txt"
            parsed_output_path = out_dir / f"provider_output_s{sample_index:02d}_r{repair_round:02d}.json"
            _write_json(
                prompt_path,
                {
                    "schema_version": "verisoftbench_c_arm_prompt_receipt_v0",
                    "task_id": task_id,
                    "sample_index": sample_index,
                    "repair_round": repair_round,
                    "prompt_sha256": _sha256_text(prompt),
                    "prompt_packet": prompt_packet,
                    "ground_truth_used_for_provider": False,
                },
            )
            sleep_s = interval - (time.monotonic() - last_provider_call)
            if sleep_s > 0:
                time.sleep(sleep_s)
            call_started = time.monotonic()
            try:
                raw, request_mode, provider_call_receipt = _provider_call(
                    provider_route=provider_route,
                    prompt=prompt,
                    model_id=selected_model,
                    timeout_seconds=provider_timeout_seconds,
                    seed=sample_index * 100 + repair_round,
                    request_policy=provider_request_policy,
                )
                last_provider_call = time.monotonic()
                provider_attempt_count += 1
                latency_ms = int((time.monotonic() - call_started) * 1000)
                _write_text(raw_output_path, raw)
                payload, extraction_metadata = _extract_json_object_with_metadata(raw)
                if payload is not None:
                    _write_json(parsed_output_path, payload)
                contract_gate = _proof_contract_gate(
                    payload,
                    target_name=str(entry.get("thm_name") or ""),
                    raw_text=raw,
                    extraction_metadata=extraction_metadata,
                )
                if contract_gate.get("ok") is not True:
                    attempt = {
                        "sample_index": sample_index,
                        "repair_round": repair_round,
                        "status": PROOF_CONTRACT_FAILED_STATUS,
                        "failure_class": contract_gate.get("failure_class") or LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS,
                        "legacy_failure_class": LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS,
                        "provider_status": "ok",
                        "request_mode": request_mode,
                        "provider_call": provider_call_receipt,
                        "usage": provider_call_receipt.get("usage"),
                        "latency_ms": latency_ms,
                        "provider_contract": contract_gate,
                        "validation_violations": [
                            str(row.get("message") or row.get("code"))
                            for row in contract_gate.get("violations") or []
                            if isinstance(row, Mapping)
                        ],
                        "prompt_ref": _rel(prompt_path, repo_root=repo_root),
                        "prompt_sha256": _sha256_file(prompt_path),
                        "raw_output_ref": _rel(raw_output_path, repo_root=repo_root),
                        "raw_output_sha256": _sha256_file(raw_output_path),
                        "parsed_output_ref": _rel(parsed_output_path, repo_root=repo_root) if payload is not None else None,
                    }
                    attempts.append(attempt)
                    best_attempt_status = str(attempt["status"])
                    failure_class = str(attempt["failure_class"])
                    previous_attempt = None
                    break
                proof_body = str(payload["lean_proof_body"])
                identifier_gate = _identifier_resolution_gate(
                    entry=entry,
                    workspace_root=workspace_root,
                    repo_root=repo_root,
                    out_dir=out_dir,
                    sample_index=sample_index,
                    repair_round=repair_round,
                    proof_body=proof_body,
                    payload=payload,
                    timeout_seconds=lean_timeout_seconds,
                )
                if identifier_gate.get("checked_identifier_count"):
                    identifier_check_count += 1
                if identifier_gate.get("status") != "PASS":
                    status = (
                        IDENTIFIER_GATE_TIMEOUT_STATUS
                        if identifier_gate.get("status") == "TIMEOUT"
                        else IDENTIFIER_GATE_FAILED_STATUS
                    )
                    failure = str(identifier_gate.get("failure_class") or IDENTIFIER_GATE_FAILURE_CLASS)
                    attempt = {
                        "sample_index": sample_index,
                        "repair_round": repair_round,
                        "status": status,
                        "failure_class": failure,
                        "provider_status": "ok",
                        "request_mode": request_mode,
                        "provider_call": provider_call_receipt,
                        "usage": provider_call_receipt.get("usage"),
                        "latency_ms": latency_ms,
                        "prompt_ref": _rel(prompt_path, repo_root=repo_root),
                        "prompt_sha256": _sha256_file(prompt_path),
                        "raw_output_ref": _rel(raw_output_path, repo_root=repo_root),
                        "raw_output_sha256": _sha256_file(raw_output_path),
                        "parsed_output_ref": _rel(parsed_output_path, repo_root=repo_root),
                        "lean_proof_body": proof_body,
                        "uses": payload.get("uses"),
                        "strategy_summary": payload.get("strategy_summary"),
                        "expected_failure_modes": payload.get("expected_failure_modes"),
                        "provider_contract": contract_gate,
                        "identifier_gate": identifier_gate,
                        "accepted_by_lean": False,
                    }
                    attempts.append(attempt)
                    best_attempt_status = status
                    failure_class = failure
                    previous_attempt = {
                        "lean_proof_body": proof_body,
                        "best_attempt_status": status,
                        "unresolved_identifiers": identifier_gate.get("unresolved_identifiers") or [],
                        "lean_feedback_excerpt": (
                            "Identifier resolution failed before full theorem checking. "
                            f"Unresolved identifiers: {', '.join(identifier_gate.get('unresolved_identifiers') or [])}. "
                            "Replace these with identifiers from the allowed_symbols packet, local hypotheses, or standard tactics."
                        ),
                    }
                    continue
                verify = _verify_candidate(
                    entry=entry,
                    workspace_root=workspace_root,
                    repo_root=repo_root,
                    out_dir=out_dir,
                    sample_index=sample_index,
                    repair_round=repair_round,
                    proof_body=proof_body,
                    timeout_seconds=lean_timeout_seconds,
                )
                lean_check_count += 1
                accepted = verify.get("compile_status") == "PASS"
                status = "lean_accepted" if accepted else _classify_lean_failure(verify)
                attempt = {
                    "sample_index": sample_index,
                    "repair_round": repair_round,
                    "status": status,
                    "failure_class": "none" if accepted else status,
                    "provider_status": "ok",
                    "request_mode": request_mode,
                    "provider_call": provider_call_receipt,
                    "usage": provider_call_receipt.get("usage"),
                    "latency_ms": latency_ms,
                    "prompt_ref": _rel(prompt_path, repo_root=repo_root),
                    "prompt_sha256": _sha256_file(prompt_path),
                    "raw_output_ref": _rel(raw_output_path, repo_root=repo_root),
                    "raw_output_sha256": _sha256_file(raw_output_path),
                    "parsed_output_ref": _rel(parsed_output_path, repo_root=repo_root),
                    "lean_proof_body": proof_body,
                    "uses": payload.get("uses"),
                    "strategy_summary": payload.get("strategy_summary"),
                    "expected_failure_modes": payload.get("expected_failure_modes"),
                    "provider_contract": contract_gate,
                    "identifier_gate": identifier_gate,
                    "lean_result": {
                        key: value
                        for key, value in verify.items()
                        if key not in {"stdout", "stderr"}
                    },
                    "accepted_by_lean": accepted,
                }
                attempts.append(attempt)
                best_attempt_status = status
                failure_class = "none" if accepted else status
                if accepted:
                    accepted_attempt = attempt
                    break
                if (
                    max_lean_timeouts_per_row > 0
                    and sum(1 for row in attempts if row.get("status") == "lean_timeout")
                    >= max_lean_timeouts_per_row
                ):
                    break
                previous_attempt = {
                    "lean_proof_body": proof_body,
                    "best_attempt_status": status,
                    "lean_feedback_excerpt": _lean_feedback_excerpt(verify),
                }
            except Exception as exc:
                last_provider_call = time.monotonic()
                provider_attempt_count += 1
                issue = f"{type(exc).__name__}: {exc}"
                _write_text(raw_output_path, issue)
                attempt = {
                    "sample_index": sample_index,
                    "repair_round": repair_round,
                    "status": "provider_unavailable",
                    "failure_class": "provider_unavailable",
                    "provider_status": "error",
                    "latency_ms": int((time.monotonic() - call_started) * 1000),
                    "error": issue,
                    "prompt_ref": _rel(prompt_path, repo_root=repo_root),
                    "prompt_sha256": _sha256_file(prompt_path),
                    "raw_output_ref": _rel(raw_output_path, repo_root=repo_root),
                    "raw_output_sha256": _sha256_file(raw_output_path),
                }
                attempts.append(attempt)
                best_attempt_status = "provider_unavailable"
                failure_class = "provider_unavailable"
                break
        if attempts and attempts[-1].get("failure_class") == "provider_unavailable":
            break
        if (
            max_lean_timeouts_per_row > 0
            and sum(1 for row in attempts if row.get("status") == "lean_timeout")
            >= max_lean_timeouts_per_row
        ):
            break
        if accepted_attempt:
            break

    status_counts = Counter(str(row.get("status") or "unknown") for row in attempts)
    failure_counts = Counter(str(row.get("failure_class") or "unknown") for row in attempts)
    estimated_cost_usd = round(
        sum(
            float(((row.get("usage") or {}).get("cost") if isinstance(row.get("usage"), Mapping) else 0) or 0)
            for row in attempts
        ),
        8,
    )
    solved = accepted_attempt is not None
    if not solved and attempts:
        best_attempt_status, failure_class = _dominant_attempt_status_and_failure(attempts)
    receipt_refs = [
        row.get("prompt_ref")
        for row in attempts
        if isinstance(row.get("prompt_ref"), str)
    ] + [
        row.get("raw_output_ref")
        for row in attempts
        if isinstance(row.get("raw_output_ref"), str)
    ]
    for row in attempts:
        lean_result = row.get("lean_result") if isinstance(row.get("lean_result"), Mapping) else {}
        for key in ("lean_source_ref", "stdout_ref", "stderr_ref"):
            if isinstance(lean_result.get(key), str):
                receipt_refs.append(lean_result[key])
    contract_pass_count = sum(
        1
        for row in attempts
        if isinstance(row.get("provider_contract"), Mapping)
        and (row.get("provider_contract") or {}).get("ok") is True
    )
    contract_failure_counts = Counter(
        str((row.get("provider_contract") or {}).get("failure_class") or row.get("failure_class") or "unknown")
        for row in attempts
        if isinstance(row.get("provider_contract"), Mapping)
        and (row.get("provider_contract") or {}).get("ok") is not True
    )
    identifier_gate_rows = [
        row.get("identifier_gate")
        for row in attempts
        if isinstance(row.get("identifier_gate"), Mapping)
    ]
    identifier_pass_count = sum(1 for row in identifier_gate_rows if row.get("status") == "PASS")
    identifier_failure_counts = Counter(
        str(row.get("failure_class") or "unknown")
        for row in identifier_gate_rows
        if row.get("status") != "PASS"
    )
    unresolved_identifier_counts = Counter(
        str(identifier)
        for row in identifier_gate_rows
        for identifier in (row.get("unresolved_identifiers") or [])
    )
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "task_id": task_id,
        "work_item_id": WORK_ITEM_ID,
        "claim_boundary": CLAIM_BOUNDARY,
        "official_leaderboard_submission": False,
        "public_claim_allowed": False,
        "protocol_arm": "C_provider_repair_filtered_context",
        "context_mode": context_mode,
        "attempt_budget": num_samples,
        "repair_round_budget": repair_rounds,
        "max_lean_timeouts_per_row": max_lean_timeouts_per_row,
        "provider_route": provider_route,
        "provider_id": provider_id,
        "provider_model": selected_model,
        "model_id": selected_model,
        "provider_attempt_count": provider_attempt_count,
        "lean_check_count": lean_check_count,
        "identifier_check_count": identifier_check_count,
        "estimated_cost_usd": estimated_cost_usd,
        "accepted_by_lean": solved,
        "solved": solved,
        "best_attempt_status": "lean_accepted" if solved else best_attempt_status,
        "failure_class": "none" if solved else failure_class,
        "status": "lean_accepted" if solved else "c_arm_provider_repair_exhausted",
        "ground_truth_used_for_provider": False,
        "score_counted_ground_truth": False,
        "target_metadata": {
            "theorem_name": entry.get("thm_name"),
            "lean_root": entry.get("lean_root"),
            "rel_path": entry.get("rel_path"),
            "official_dataset_ref": _rel(OFFICIAL_DATASET_PATH, repo_root=repo_root),
        },
        "provider_selection": provider_selection,
        "status_counts": dict(status_counts),
        "failure_counts": dict(failure_counts),
        "proof_contract": {
            "schema_version": "verisoftbench_c_arm_provider_contract_summary_v0",
            "provider_attempt_count": provider_attempt_count,
            "contract_pass_count": contract_pass_count,
            "contract_failed_count": sum(contract_failure_counts.values()),
            "parseable_proof_rate": contract_pass_count / provider_attempt_count if provider_attempt_count else 0,
            "failure_counts": dict(contract_failure_counts),
            "dominant_failure_class": contract_failure_counts.most_common(1)[0][0]
            if contract_failure_counts
            else None,
        },
        "identifier_gate": {
            "schema_version": IDENTIFIER_GATE_SCHEMA_VERSION,
            "provider_attempt_count": provider_attempt_count,
            "identifier_check_count": identifier_check_count,
            "gate_record_count": len(identifier_gate_rows),
            "pass_count": identifier_pass_count,
            "failed_count": max(len(identifier_gate_rows) - identifier_pass_count, 0),
            "pass_rate": identifier_pass_count / len(identifier_gate_rows) if identifier_gate_rows else 0,
            "failure_counts": dict(identifier_failure_counts),
            "unresolved_identifier_counts": dict(unresolved_identifier_counts),
            "dominant_unresolved_identifier": unresolved_identifier_counts.most_common(1)[0][0]
            if unresolved_identifier_counts
            else None,
            "dominant_failure_class": identifier_failure_counts.most_common(1)[0][0]
            if identifier_failure_counts
            else None,
        },
        "attempts": attempts,
        "accepted_attempt": {
            "sample_index": accepted_attempt.get("sample_index"),
            "repair_round": accepted_attempt.get("repair_round"),
            "lean_source_ref": ((accepted_attempt.get("lean_result") or {}).get("lean_source_ref") if isinstance(accepted_attempt.get("lean_result"), Mapping) else None),
        }
        if accepted_attempt
        else None,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "receipt_refs": [ref for ref in receipt_refs if ref],
    }
    _write_json(_repo_path(receipt_path(task_id), repo_root=repo_root), receipt)
    return receipt


def _manifest_row_from_receipt(
    task_id: str,
    receipt: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    proof_contract = (
        receipt.get("proof_contract")
        if isinstance(receipt.get("proof_contract"), Mapping)
        else {}
    )
    identifier_gate = (
        receipt.get("identifier_gate")
        if isinstance(receipt.get("identifier_gate"), Mapping)
        else {}
    )
    return {
        "task_id": task_id,
        "status": receipt.get("status"),
        "best_attempt_status": receipt.get("best_attempt_status"),
        "failure_class": receipt.get("failure_class"),
        "accepted_by_lean": receipt.get("accepted_by_lean"),
        "solved": receipt.get("solved"),
        "provider_attempt_count": receipt.get("provider_attempt_count"),
        "lean_check_count": receipt.get("lean_check_count"),
        "identifier_check_count": receipt.get("identifier_check_count"),
        "estimated_cost_usd": receipt.get("estimated_cost_usd"),
        "model_id": receipt.get("model_id"),
        "proof_contract_provider_attempt_count": proof_contract.get("provider_attempt_count"),
        "proof_contract_pass_count": proof_contract.get("contract_pass_count"),
        "proof_contract_parseable_proof_rate": proof_contract.get("parseable_proof_rate"),
        "proof_contract_dominant_failure_class": proof_contract.get("dominant_failure_class"),
        "identifier_gate_record_count": identifier_gate.get("gate_record_count"),
        "identifier_gate_pass_count": identifier_gate.get("pass_count"),
        "identifier_gate_pass_rate": identifier_gate.get("pass_rate"),
        "identifier_gate_dominant_failure_class": identifier_gate.get("dominant_failure_class"),
        "identifier_gate_dominant_unresolved_identifier": identifier_gate.get("dominant_unresolved_identifier"),
        "receipt_ref": _rel(receipt_path(task_id), repo_root=repo_root),
    }


def _refresh_existing_receipt_classification(
    task_id: str,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    path = _repo_path(receipt_path(task_id), repo_root=repo_root)
    receipt = _read_json_if_exists(path)
    if receipt.get("schema_version") != SCHEMA_VERSION:
        return receipt
    attempts = receipt.get("attempts") if isinstance(receipt.get("attempts"), list) else []
    target_metadata = receipt.get("target_metadata") if isinstance(receipt.get("target_metadata"), Mapping) else {}
    target_name = str(target_metadata.get("theorem_name") or "")
    if target_name:
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            raw_ref = attempt.get("raw_output_ref")
            raw_path = _repo_path(raw_ref, repo_root=repo_root) if isinstance(raw_ref, str) else None
            if not raw_path or not raw_path.exists():
                continue
            if attempt.get("status") != PROOF_CONTRACT_FAILED_STATUS and not isinstance(attempt.get("provider_contract"), Mapping):
                continue
            raw = raw_path.read_text(encoding="utf-8")
            if attempt.get("request_mode") == "openrouter.response_format.json_object":
                attempt["request_mode"] = "openrouter.response_format.json_schema"
            payload, extraction_metadata = _extract_json_object_with_metadata(raw)
            contract_gate = _proof_contract_gate(
                payload,
                target_name=target_name,
                raw_text=raw,
                extraction_metadata=extraction_metadata,
            )
            attempt["provider_contract"] = contract_gate
            if attempt.get("status") == PROOF_CONTRACT_FAILED_STATUS:
                attempt["failure_class"] = contract_gate.get("failure_class") or LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS
                attempt["legacy_failure_class"] = LEGACY_PROVIDER_SCHEMA_FAILURE_CLASS
    if attempts:
        status_counts = Counter(str(row.get("status") or "unknown") for row in attempts if isinstance(row, Mapping))
        failure_counts = Counter(str(row.get("failure_class") or "unknown") for row in attempts if isinstance(row, Mapping))
        receipt["status_counts"] = dict(status_counts)
        receipt["failure_counts"] = dict(failure_counts)
        contract_pass_count = sum(
            1
            for row in attempts
            if isinstance(row, Mapping)
            and isinstance(row.get("provider_contract"), Mapping)
            and (row.get("provider_contract") or {}).get("ok") is True
        )
        contract_failure_counts = Counter(
            str((row.get("provider_contract") or {}).get("failure_class") or row.get("failure_class") or "unknown")
            for row in attempts
            if isinstance(row, Mapping)
            and isinstance(row.get("provider_contract"), Mapping)
            and (row.get("provider_contract") or {}).get("ok") is not True
        )
        provider_attempt_count = int(receipt.get("provider_attempt_count") or len(attempts))
        receipt["proof_contract"] = {
            "schema_version": "verisoftbench_c_arm_provider_contract_summary_v0",
            "provider_attempt_count": provider_attempt_count,
            "contract_pass_count": contract_pass_count,
            "contract_failed_count": sum(contract_failure_counts.values()),
            "parseable_proof_rate": contract_pass_count / provider_attempt_count if provider_attempt_count else 0,
            "failure_counts": dict(contract_failure_counts),
            "dominant_failure_class": contract_failure_counts.most_common(1)[0][0]
            if contract_failure_counts
            else None,
        }
        identifier_gate_rows = [
            row.get("identifier_gate")
            for row in attempts
            if isinstance(row, Mapping) and isinstance(row.get("identifier_gate"), Mapping)
        ]
        identifier_pass_count = sum(1 for row in identifier_gate_rows if row.get("status") == "PASS")
        identifier_failure_counts = Counter(
            str(row.get("failure_class") or "unknown")
            for row in identifier_gate_rows
            if row.get("status") != "PASS"
        )
        unresolved_identifier_counts = Counter(
            str(identifier)
            for row in identifier_gate_rows
            for identifier in (row.get("unresolved_identifiers") or [])
        )
        receipt["identifier_gate"] = {
            "schema_version": IDENTIFIER_GATE_SCHEMA_VERSION,
            "provider_attempt_count": provider_attempt_count,
            "identifier_check_count": int(receipt.get("identifier_check_count") or 0),
            "gate_record_count": len(identifier_gate_rows),
            "pass_count": identifier_pass_count,
            "failed_count": max(len(identifier_gate_rows) - identifier_pass_count, 0),
            "pass_rate": identifier_pass_count / len(identifier_gate_rows) if identifier_gate_rows else 0,
            "failure_counts": dict(identifier_failure_counts),
            "unresolved_identifier_counts": dict(unresolved_identifier_counts),
            "dominant_unresolved_identifier": unresolved_identifier_counts.most_common(1)[0][0]
            if unresolved_identifier_counts
            else None,
            "dominant_failure_class": identifier_failure_counts.most_common(1)[0][0]
            if identifier_failure_counts
            else None,
        }
    if receipt.get("accepted_by_lean") is True:
        receipt["best_attempt_status"] = "lean_accepted"
        receipt["failure_class"] = "none"
        receipt["status"] = "lean_accepted"
    elif isinstance(receipt.get("failure_counts"), Mapping) or isinstance(receipt.get("status_counts"), Mapping):
        best_status, dominant_failure = _dominant_receipt_status_and_failure(receipt)
        receipt["best_attempt_status"] = best_status
        receipt["failure_class"] = dominant_failure
        if receipt.get("status") == "lean_accepted":
            receipt["status"] = "c_arm_provider_repair_exhausted"
    _write_json(path, receipt)
    return receipt


def run_tasks(
    *,
    repo_root: Path = REPO_ROOT,
    task_ids: Sequence[str] = DEFAULT_TARGET_TASK_IDS,
    provider_route: str = PROVIDER_ROUTE,
    model_id: str | None = None,
    openrouter_selection_strategy: str = "preferred-serious",
    openrouter_allow_paid: bool = False,
    openrouter_min_context_length: int = OPENROUTER_MIN_CONTEXT_LENGTH,
    openrouter_canary: bool = True,
    openrouter_require_parameters: bool = False,
    openrouter_reasoning_max_tokens: int = 0,
    num_samples: int = 8,
    repair_rounds: int = 3,
    context_mode: str = "filtered_context",
    lean_timeout_seconds: int = 180,
    provider_timeout_seconds: int = 180,
    max_lean_timeouts_per_row: int = 0,
    merge_existing_non_targets: bool = False,
    refresh_existing_receipts: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    created_at = _utc_now()
    existing_manifest = _read_json_if_exists(_repo_path(C_ARM_MANIFEST_PATH, repo_root=repo_root))
    if refresh_existing_receipts and existing_manifest:
        if max_lean_timeouts_per_row == 0 and existing_manifest.get("max_lean_timeouts_per_row") is not None:
            max_lean_timeouts_per_row = int(existing_manifest.get("max_lean_timeouts_per_row") or 0)
        if num_samples == 8 and existing_manifest.get("attempt_budget_per_row") is not None:
            num_samples = int(existing_manifest.get("attempt_budget_per_row") or num_samples)
        if repair_rounds == 3 and existing_manifest.get("repair_round_budget") is not None:
            repair_rounds = int(existing_manifest.get("repair_round_budget") or repair_rounds)
    provider_selection = _select_model(
        provider_route=provider_route,
        timeout_seconds=provider_timeout_seconds,
        explicit_model_id=model_id,
        openrouter_selection_strategy=openrouter_selection_strategy,
        openrouter_allow_paid=openrouter_allow_paid,
        openrouter_min_context_length=openrouter_min_context_length,
        openrouter_canary=openrouter_canary,
        openrouter_require_parameters=openrouter_require_parameters,
        openrouter_reasoning_max_tokens=openrouter_reasoning_max_tokens,
    )
    rows_by_task: dict[str, dict[str, Any]] = {}
    for task_id in task_ids:
        if refresh_existing_receipts:
            receipt = _refresh_existing_receipt_classification(task_id, repo_root=repo_root)
            if not receipt:
                receipt = run_task(
                    task_id,
                    repo_root=repo_root,
                    provider_selection=provider_selection,
                    num_samples=num_samples,
                    repair_rounds=repair_rounds,
                    context_mode=context_mode,
                    lean_timeout_seconds=lean_timeout_seconds,
                    provider_timeout_seconds=provider_timeout_seconds,
                    max_lean_timeouts_per_row=max_lean_timeouts_per_row,
                    force=force,
                )
        else:
            receipt = run_task(
                task_id,
                repo_root=repo_root,
                provider_selection=provider_selection,
                num_samples=num_samples,
                repair_rounds=repair_rounds,
                context_mode=context_mode,
                lean_timeout_seconds=lean_timeout_seconds,
                provider_timeout_seconds=provider_timeout_seconds,
                max_lean_timeouts_per_row=max_lean_timeouts_per_row,
                force=force,
            )
        rows_by_task[task_id] = _manifest_row_from_receipt(task_id, receipt, repo_root=repo_root)
    if merge_existing_non_targets:
        for task_id in DEFAULT_TARGET_TASK_IDS:
            if task_id in rows_by_task:
                continue
            existing = _read_json_if_exists(_repo_path(receipt_path(task_id), repo_root=repo_root))
            if existing.get("schema_version") == SCHEMA_VERSION:
                rows_by_task[task_id] = _manifest_row_from_receipt(task_id, existing, repo_root=repo_root)
    manifest_task_ids = (
        list(DEFAULT_TARGET_TASK_IDS)
        if merge_existing_non_targets
        else list(task_ids)
    )
    rows = [rows_by_task[task_id] for task_id in manifest_task_ids if task_id in rows_by_task]
    status_counts = Counter(str(row.get("status") or "unknown") for row in rows)
    failure_counts = Counter(str(row.get("failure_class") or "unknown") for row in rows)
    solved_count = sum(1 for row in rows if row.get("accepted_by_lean") is True)
    contract_attempt_count = sum(int(row.get("proof_contract_provider_attempt_count") or 0) for row in rows)
    contract_pass_count = sum(int(row.get("proof_contract_pass_count") or 0) for row in rows)
    identifier_record_count = sum(int(row.get("identifier_gate_record_count") or 0) for row in rows)
    identifier_pass_count = sum(int(row.get("identifier_gate_pass_count") or 0) for row in rows)
    identifier_failure_counts = Counter(
        str(row.get("identifier_gate_dominant_failure_class") or "unknown")
        for row in rows
        if row.get("identifier_gate_dominant_failure_class")
    )
    unresolved_identifier_counts = Counter(
        str(row.get("identifier_gate_dominant_unresolved_identifier") or "unknown")
        for row in rows
        if row.get("identifier_gate_dominant_unresolved_identifier")
    )
    live_model_policy = (
        provider_selection.get("live_model_policy")
        if isinstance(provider_selection.get("live_model_policy"), Mapping)
        else {
            "schema_version": MODEL_POLICY_SCHEMA_VERSION,
            "created_at": created_at,
            "provider_route": provider_selection.get("provider_route") or provider_route,
            "selection_strategy": openrouter_selection_strategy,
            "rows": [],
        }
    )
    _write_json(_repo_path(C_ARM_MODEL_POLICY_PATH, repo_root=repo_root), live_model_policy)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "created_at": created_at,
        "work_item_id": WORK_ITEM_ID,
        "benchmark": "VeriSoftBench",
        "slice_id": "verisoftbench_micro_10_v0",
        "target_task_ids": manifest_task_ids,
        "fresh_target_task_ids": list(task_ids),
        "target_row_count": len(manifest_task_ids),
        "fresh_target_row_count": len(task_ids),
        "attempt_budget_per_row": num_samples,
        "repair_round_budget": repair_rounds,
        "max_lean_timeouts_per_row": max_lean_timeouts_per_row,
        "context_mode": context_mode,
        "merge_existing_non_targets": merge_existing_non_targets,
        "refresh_existing_receipts": refresh_existing_receipts,
        "provider_route": provider_selection.get("provider_route") or provider_route,
        "provider_id": provider_selection.get("provider_id") or _provider_id(provider_route),
        "provider_selection": provider_selection,
        "model_policy_ref": _rel(C_ARM_MODEL_POLICY_PATH, repo_root=repo_root),
        "model_policy": {
            "schema_version": MODEL_POLICY_SCHEMA_VERSION,
            "selection_strategy": live_model_policy.get("selection_strategy"),
            "eligible_by_tier": live_model_policy.get("eligible_by_tier"),
            "selected_model_id": provider_selection.get("selected_model_id"),
            "claim_boundary": live_model_policy.get("claim_boundary"),
        },
        "model_ids": sorted({str(row.get("model_id")) for row in rows if row.get("model_id")}),
        "c_arm_receipt_count": len(rows),
        "c_arm_solved_count": solved_count,
        "c_arm_solve_rate": solved_count / len(rows) if rows else 0,
        "provider_attempt_count": sum(int(row.get("provider_attempt_count") or 0) for row in rows),
        "lean_check_count": sum(int(row.get("lean_check_count") or 0) for row in rows),
        "identifier_check_count": sum(int(row.get("identifier_check_count") or 0) for row in rows),
        "estimated_cost_usd": round(sum(float(row.get("estimated_cost_usd") or 0.0) for row in rows), 8),
        "status_counts": dict(status_counts),
        "failure_counts": dict(failure_counts),
        "dominant_failure_class": failure_counts.most_common(1)[0][0] if failure_counts else None,
        "proof_contract": {
            "schema_version": "verisoftbench_c_arm_provider_contract_summary_v0",
            "provider_attempt_count": contract_attempt_count,
            "contract_pass_count": contract_pass_count,
            "contract_failed_count": max(contract_attempt_count - contract_pass_count, 0),
            "parseable_proof_rate": contract_pass_count / contract_attempt_count if contract_attempt_count else 0,
            "failure_counts": dict(
                Counter(
                    str(row.get("proof_contract_dominant_failure_class") or "unknown")
                    for row in rows
                    if row.get("proof_contract_dominant_failure_class")
                )
            ),
        },
        "identifier_gate": {
            "schema_version": IDENTIFIER_GATE_SCHEMA_VERSION,
            "gate_record_count": identifier_record_count,
            "pass_count": identifier_pass_count,
            "failed_count": max(identifier_record_count - identifier_pass_count, 0),
            "pass_rate": identifier_pass_count / identifier_record_count if identifier_record_count else 0,
            "failure_counts": dict(identifier_failure_counts),
            "unresolved_identifier_counts": dict(unresolved_identifier_counts),
            "dominant_failure_class": identifier_failure_counts.most_common(1)[0][0]
            if identifier_failure_counts
            else None,
            "dominant_unresolved_identifier": unresolved_identifier_counts.most_common(1)[0][0]
            if unresolved_identifier_counts
            else None,
        },
        "rows": rows,
        "ground_truth_used_for_provider": False,
        "score_counted_ground_truth": False,
        "official_leaderboard_submission": False,
        "public_claim_allowed": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_json(_repo_path(C_ARM_MANIFEST_PATH, repo_root=repo_root), manifest)
    return manifest


def _c_arm_receipts(*, repo_root: Path) -> list[dict[str, Any]]:
    root = _repo_path(C_ARM_ROOT, repo_root=repo_root)
    receipts: list[dict[str, Any]] = []
    for path in sorted(root.glob(f"verisoftbench_*/{C_ARM_RECEIPT_NAME}")):
        payload = _read_json_if_exists(path)
        if payload:
            payload["_receipt_ref"] = _rel(path, repo_root=repo_root)
            receipts.append(payload)
    return receipts


def check_outputs(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    issues: list[str] = []
    manifest_path = _repo_path(C_ARM_MANIFEST_PATH, repo_root=repo_root)
    manifest = _read_json_if_exists(manifest_path)
    if not manifest:
        issues.append(f"missing {C_ARM_MANIFEST_PATH}")
        rows: list[Mapping[str, Any]] = []
    elif manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        issues.append("C-arm manifest schema mismatch")
        rows = []
    else:
        rows = [row for row in manifest.get("rows") or [] if isinstance(row, Mapping)]
        if manifest.get("public_claim_allowed") is not False:
            issues.append("C-arm manifest public_claim_allowed must be false")
        if manifest.get("ground_truth_used_for_provider") is not False:
            issues.append("C-arm manifest ground_truth_used_for_provider must be false")
        model_policy_ref = manifest.get("model_policy_ref")
        if isinstance(model_policy_ref, str) and model_policy_ref and not _repo_path(model_policy_ref, repo_root=repo_root).exists():
            issues.append(f"C-arm model policy missing: {model_policy_ref}")
        expected = set(DEFAULT_TARGET_TASK_IDS)
        actual = {str(row.get("task_id")) for row in rows}
        if actual != expected:
            issues.append(f"C-arm rows must cover target set {sorted(expected)}; found {sorted(actual)}")

    for row in rows:
        ref = str(row.get("receipt_ref") or "")
        path = _repo_path(ref, repo_root=repo_root)
        if not path.exists():
            issues.append(f"missing C-arm receipt {ref}")
            continue
        receipt = _read_json(path)
        if receipt.get("schema_version") != SCHEMA_VERSION:
            issues.append(f"C-arm receipt schema mismatch: {ref}")
        if receipt.get("public_claim_allowed") is not False:
            issues.append(f"C-arm receipt public_claim_allowed must be false: {ref}")
        if receipt.get("ground_truth_used_for_provider") is not False:
            issues.append(f"C-arm receipt leaked ground truth to provider: {ref}")
        if receipt.get("score_counted_ground_truth") is not False:
            issues.append(f"C-arm receipt counted ground truth: {ref}")
        if int(receipt.get("provider_attempt_count") or 0) < 1 and receipt.get("failure_class") != "provider_unavailable":
            issues.append(f"C-arm receipt has no provider attempt and no provider blocker: {ref}")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "c_arm_provider_repair_manifest_ref": str(C_ARM_MANIFEST_PATH),
        "row_receipt_count": len(rows),
        "owner_id": OWNER_ID,
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--task-id", action="append", dest="task_ids")
    parser.add_argument(
        "--provider-route",
        default=PROVIDER_ROUTE,
        choices=(OPENROUTER_PROVIDER_ROUTE, NVIDIA_PROVIDER_ROUTE, "nvidia_nim"),
    )
    parser.add_argument("--model-id")
    parser.add_argument(
        "--openrouter-selection-strategy",
        default="preferred-serious",
        choices=OPENROUTER_SELECTION_STRATEGIES,
    )
    parser.add_argument("--openrouter-allow-paid", action="store_true")
    parser.add_argument(
        "--openrouter-require-parameters",
        action="store_true",
        help="Ask OpenRouter to reject providers that cannot honor response_format/reasoning parameters.",
    )
    parser.add_argument(
        "--openrouter-reasoning-max-tokens",
        type=int,
        default=0,
        help="Optional OpenRouter reasoning.max_tokens budget for reasoning-capable models.",
    )
    parser.add_argument(
        "--openrouter-min-context-length",
        type=int,
        default=OPENROUTER_MIN_CONTEXT_LENGTH,
    )
    parser.add_argument("--skip-openrouter-canary", action="store_true")
    parser.add_argument("--num-samples", type=int, default=8)
    parser.add_argument("--repair-rounds", type=int, default=3)
    parser.add_argument("--context-mode", default="filtered_context")
    parser.add_argument("--lean-timeout-seconds", type=int, default=180)
    parser.add_argument("--provider-timeout-seconds", type=int, default=180)
    parser.add_argument("--max-lean-timeouts-per-row", type=int, default=0)
    parser.add_argument(
        "--merge-existing-non-targets",
        action="store_true",
        help="After a subset rerun, keep existing default C-arm row receipts in the manifest.",
    )
    parser.add_argument(
        "--refresh-existing-receipts",
        action="store_true",
        help="Recompute C-arm receipt summary fields from existing per-attempt counts without provider calls.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root)
    if args.check:
        result = check_outputs(repo_root=repo_root)
    else:
        result = run_tasks(
            repo_root=repo_root,
            task_ids=tuple(args.task_ids) if args.task_ids else DEFAULT_TARGET_TASK_IDS,
            provider_route=args.provider_route,
            model_id=args.model_id,
            openrouter_selection_strategy=args.openrouter_selection_strategy,
            openrouter_allow_paid=args.openrouter_allow_paid,
            openrouter_min_context_length=args.openrouter_min_context_length,
            openrouter_canary=not args.skip_openrouter_canary,
            openrouter_require_parameters=args.openrouter_require_parameters,
            openrouter_reasoning_max_tokens=args.openrouter_reasoning_max_tokens,
            num_samples=args.num_samples,
            repair_rounds=args.repair_rounds,
            context_mode=args.context_mode,
            lean_timeout_seconds=args.lean_timeout_seconds,
            provider_timeout_seconds=args.provider_timeout_seconds,
            max_lean_timeouts_per_row=args.max_lean_timeouts_per_row,
            merge_existing_non_targets=args.merge_existing_non_targets,
            refresh_existing_receipts=args.refresh_existing_receipts,
            force=args.force,
        )
    if args.json or args.check:
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    else:
        print(
            "verisoftbench_micro10_c_arm_provider_repair: "
            f"receipts={result.get('c_arm_receipt_count') or result.get('row_receipt_count')} "
            f"solved={result.get('c_arm_solved_count')} "
            f"dominant_failure={result.get('dominant_failure_class')}"
        )
    status = result.get("status") if isinstance(result, Mapping) else None
    return 0 if not args.check or status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
