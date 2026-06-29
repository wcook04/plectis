"""
[PURPOSE]
- Teleology: Make benchmark-integrity replay evidence inspectable without trusting claimed agent-task completions at face value.
- Mechanism: Read replay rows, resolve their evidence references, and quarantine rows that trip evaluator-edit, train/test leakage, hidden-gold access, final-answer-only grading, score-overclaim, pass@k cherry-picking, solution/body leakage, or provider-material leakage checks.
- Non-goal: Claim a benchmark score, establish agent capability, expose private issue/oracle bodies, run providers, mutate live repositories, or authorize release.

[INTERFACE]
- CLI: `python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay run --input <fixture> --out <receipt-dir>`.
- Bundle CLI: `python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay run-benchmark-integrity-bundle --input <bundle> --out <receipt-dir>`.
- Exports: validation helpers, result-card projection, receipt writer, and public trace checks for the benchmark-integrity organ.

[FLOW]
- Load projection protocol, locked evaluator policy, benchmark cases, replay observations, source manifests, public trace evidence, and negative cases.
- Validate source-module provenance and evidence references before scoring any replay row as integrity-pass.
- Classify every replay row as `integrity_pass` or quarantine with named error codes, then emit result, board, validation, and acceptance receipts.

[DEPENDENCIES]
- Python standard library plus local `microcosm_core` schema, receipt, private-state scan, and public trace helpers.
- Reads only public fixtures, examples, source manifests, and receipt paths supplied by the caller.

[CONSTRAINTS]
- Receipts carry evidence refs, counts, hashes, spans, findings, and claim ceilings instead of private issue bodies, oracle patches, hidden-gold bodies, provider payloads, or raw solution material.
- A passing row means the wired evidence cleared this validator's anti-gaming floor; it does not mean the underlying agent task was completed or that any external benchmark score is authorized.
- Atomicity: Validator reads and receipt writes remain caller-scoped; no source or provider side effects are introduced by documentation or card projection.
- Determinism: For identical fixtures, manifests, and public roots, sorting, digests, and projected refs remain stable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcosm_core.macro_tools.agent_execution_trace import (
    build_public_benchmark_integrity_anti_gaming_trace,
)
from microcosm_core.private_state_scan import (
    PASS,
    load_forbidden_classes,
    public_relative_path,
    scan_paths,
)
from microcosm_core.receipts import (
    normalize_public_receipt_paths,
    utc_now,
    write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "agent_benchmark_integrity_anti_gaming_replay"
FIXTURE_ID = "first_wave.agent_benchmark_integrity_anti_gaming_replay"
VALIDATOR_ID = "validator.microcosm.organs.agent_benchmark_integrity_anti_gaming_replay"

RESULT_NAME = "agent_benchmark_integrity_anti_gaming_replay_result.json"
BOARD_NAME = "agent_benchmark_integrity_anti_gaming_replay_board.json"
VALIDATION_RECEIPT_NAME = (
    "agent_benchmark_integrity_anti_gaming_replay_validation_receipt.json"
)
ACCEPTANCE_RECEIPT_REL = (
    "receipts/acceptance/first_wave/"
    "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance.json"
)
BUNDLE_RESULT_NAME = "exported_benchmark_integrity_bundle_validation_result.json"
CARD_SCHEMA_VERSION = "agent_benchmark_integrity_anti_gaming_replay_command_card_v1"
CARD_OMITTED_FULL_PAYLOAD_KEYS = (
    "findings",
    "private_state_scan",
    "public_agent_execution_trace",
    "authority_ceiling",
    "anti_claim",
    "source_module_imports",
    "source_open_body_imports",
    "source_refs",
    "projection_receipt_refs",
    "public_regression_fixture_refs",
    "locked_evaluator_config_hashes",
    "benchmark_cases",
    "replay_rows",
)
PUBLIC_TRACE_OPEN_BODY_REF = (
    "microcosm_core.macro_tools.agent_execution_trace::"
    "build_public_benchmark_integrity_anti_gaming_trace"
)
SOURCE_MODULE_MANIFEST_REF = (
    "examples/agent_benchmark_integrity_anti_gaming_replay/"
    "exported_benchmark_integrity_bundle/source_module_manifest.json"
)
SOURCE_IMPORT_CLASS = "copied_non_secret_macro_body"
SOURCE_BODY_STATUS = "copied_non_secret_macro_body_with_provenance"
REAL_BENCHMARK_TRACE_MATERIAL_CLASS = "public_sanitized_real_benchmark_trace"
REAL_TRACE_REQUIRED_TRACE_ROLE = "real_benchmark_integrity_fixture_gate"
REAL_TRACE_REQUIRED_SCOPE_PATH = (
    "microcosm-substrate/tests/"
    "test_agent_benchmark_integrity_anti_gaming_replay.py"
)
PUBLIC_SAFE_SOURCE_MODULE_CLASSES = {
    "public_macro_pattern_body",
    REAL_BENCHMARK_TRACE_MATERIAL_CLASS,
}

INPUT_NAMES = (
    "projection_protocol.json",
    "locked_evaluator_policy.json",
    "benchmark_cases.json",
    "replay_observations.json",
)
NEGATIVE_INPUT_NAMES = (
    "evaluator_edit_attempt.json",
    "train_test_leakage.json",
    "real_trace_train_test_leakage.json",
    "oracle_patch_body_leakage.json",
    "hidden_gold_access.json",
    "final_answer_only_grading.json",
    "provider_payload_leakage.json",
    "score_overclaim.json",
    "pass_k_cherry_picking.json",
    "misleading_test_admitted.json",
    "private_issue_body_leakage.json",
    "unregistered_case_replay.json",
)

EXPECTED_NEGATIVE_CASES = {
    "evaluator_edit_attempt": ["BENCHMARK_INTEGRITY_EVALUATOR_EDIT_FORBIDDEN"],
    "train_test_leakage": ["BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE"],
    "real_trace_train_test_leakage": ["BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE"],
    "oracle_patch_body_leakage": ["BENCHMARK_INTEGRITY_ORACLE_PATCH_BODY_FORBIDDEN"],
    "hidden_gold_access": ["BENCHMARK_INTEGRITY_HIDDEN_GOLD_ACCESS"],
    "final_answer_only_grading": ["BENCHMARK_INTEGRITY_FINAL_ANSWER_ONLY_GRADING"],
    "provider_payload_leakage": ["BENCHMARK_INTEGRITY_PROVIDER_PAYLOAD_FORBIDDEN"],
    "score_overclaim": ["BENCHMARK_INTEGRITY_SCORE_OVERCLAIM"],
    "pass_k_cherry_picking": ["BENCHMARK_INTEGRITY_PASS_K_CHERRY_PICKING"],
    "misleading_test_admitted": ["BENCHMARK_INTEGRITY_MISLEADING_TEST_ADMITTED"],
    "private_issue_body_leakage": ["BENCHMARK_INTEGRITY_PRIVATE_ISSUE_BODY_FORBIDDEN"],
    "unregistered_case_replay": ["BENCHMARK_INTEGRITY_UNREGISTERED_CASE_REPLAY"],
}

REQUIRED_REPLAY_FIELDS = (
    "case_id",
    "evaluator_id",
    "evaluator_config_hash",
    "file_access_log_ref",
    "contamination_check_ref",
    "trusted_reference_score_ref",
    "output_replay_ref",
    "real_benchmark_trace_ref",
    "integrity_verdict",
)
ALLOWED_INTEGRITY_VERDICTS = ("integrity_pass", "quarantine")
EVIDENCE_REF_FIELDS = {
    "file_access_log_ref": "file_access_log",
    "contamination_check_ref": "contamination_check",
    "trusted_reference_score_ref": "trusted_reference_score",
    "output_replay_ref": "output_replay",
}
FORBIDDEN_BODY_KEYS = (
    "private_issue_body",
    "oracle_patch_body",
    "hidden_gold_body",
    "provider_payload",
    "raw_patch_body",
    "test_answer_body",
)

AUTHORITY_CEILING = {
    "status": PASS,
    "authority_ceiling": (
        "source_open_pattern_provenance_bodies_plus_body_free_regression_"
        "benchmark_integrity_replay_receipts_only"
    ),
    "benchmark_score_claim_authorized": False,
    "swe_bench_performance_claim_authorized": False,
    "hidden_gold_access_authorized": False,
    "oracle_patch_body_export_authorized": False,
    "private_issue_body_export_authorized": False,
    "provider_calls_authorized": False,
    "live_repo_mutation_authorized": False,
    "release_authorized": False,
}
BLOCKED_REPLAY_CLAIM_IDS = (
    "benchmark_score_claim",
    "swe_bench_performance_claim",
    "hidden_gold_access",
    "oracle_patch_body_export",
    "private_issue_body_export",
    "provider_payload_export",
    "live_repo_mutation",
    "release_authorized",
)
ANTI_CLAIM = (
    "Agent benchmark integrity anti-gaming replay validates copied source-open "
    "macro pattern provenance bodies and body-free regression fixture rows for "
    "synthetic evaluator locking, contamination, file-access, held-out guard, "
    "and scoring-boundary receipts. It does not claim a benchmark score, expose "
    "private issue or oracle patch bodies, run providers, mutate live "
    "repositories, or authorize release."
)


def _public_root_for_path(path: str | Path) -> Path:
    """
    [ACTION] Resolve the public Plectis root used for relative refs and private-state scans.

    - Teleology: Resolves paths, refs, or digests for _public_root_for_path so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == "microcosm-substrate" or (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src/microcosm_core").is_dir()
            and (candidate / "core/private_state_forbidden_classes.json").is_file()
        ):
            return candidate
    return Path.cwd().resolve(strict=False)


def _display(path: Path, *, public_root: Path) -> str:
    """
    [ACTION] Render a path relative to the public root for receipt-safe display.

    - Teleology: Resolves paths, refs, or digests for _display so downstream receipts can cite
      public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return public_relative_path(path, display_root=public_root)


def _card_receipt_paths(result: dict[str, Any]) -> list[str]:
    """
    [ACTION] Normalize command-card receipt paths through the public receipt sanitizer.

    - Teleology: Keeps fresh and cached benchmark-integrity command cards on the same
      receipt-safe display contract, even when the underlying receipt was written under a host
      temp directory.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns only string receipt refs after applying the shared public-receipt path
      normalization policy; it does not change the durable receipt files or infer new evidence.
    - Fails: Non-list or malformed receipt path values collapse to an empty list so card
      projection cannot leak arbitrary host-local structures.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    paths = result.get("receipt_paths")
    if not isinstance(paths, list):
        return []
    normalized = normalize_public_receipt_paths({"receipt_paths": paths})
    normalized_paths = normalized.get("receipt_paths") if isinstance(normalized, dict) else None
    if not isinstance(normalized_paths, list):
        return []
    return [path for path in normalized_paths if isinstance(path, str)]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    """
    [ACTION] Extract dictionary rows from a payload key without trusting malformed input.

    - Teleology: Keeps the replay-evidence accounting step _rows explicit, so gaming-pattern
      decisions are traceable from row input to finding, reason code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(payload, dict):
        return []
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    """
    [ACTION] Normalize a JSON list field into non-empty string tokens.

    - Teleology: Keeps the replay-evidence accounting step _strings explicit, so gaming-pattern
      decisions are traceable from row input to finding, reason code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _locked_evaluator_config_hashes(policy: object) -> dict[str, list[str]]:
    """
    [ACTION] Index allowed evaluator config hashes declared by the locked evaluator policy.

    - Teleology: Keeps the replay-evidence accounting step _locked_evaluator_config_hashes
      explicit, so gaming-pattern decisions are traceable from row input to finding, reason
      code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = policy if isinstance(policy, dict) else {}
    raw = rows.get("locked_evaluator_config_hashes", {})
    if not isinstance(raw, dict):
        return {}

    config_hashes: dict[str, list[str]] = {}
    for evaluator_id, value in raw.items():
        hashes = [value] if isinstance(value, str) else _strings(value)
        cleaned = sorted({item for item in hashes if item})
        if cleaned:
            config_hashes[str(evaluator_id)] = cleaned
    return dict(sorted(config_hashes.items()))


def _input_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION] List benchmark-integrity input files whose freshness can reuse prior bundle receipts.

    - Teleology: Resolves paths, refs, or digests for _input_paths so downstream receipts can
      cite public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    names = (*INPUT_NAMES, *(NEGATIVE_INPUT_NAMES if include_negative else ()))
    paths = [input_dir / name for name in names]
    bundle_manifest = input_dir / "bundle_manifest.json"
    if bundle_manifest.is_file():
        paths.append(bundle_manifest)
    return paths


def _strip_microcosm_prefix(ref: str) -> str:
    """
    [ACTION] Normalize legacy microcosm-substrate refs to public-root relative refs.

    - Teleology: Resolves paths, refs, or digests for _strip_microcosm_prefix so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    prefix = "microcosm-substrate/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def _sha256(path: Path) -> str:
    """
    [ACTION] Hash a file body for source and validator custody receipts.

    - Teleology: Resolves paths, refs, or digests for _sha256 so downstream receipts can cite
      public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _validator_source_digests() -> dict[str, str]:
    """
    [ACTION] Hash the organ validator and public trace builder source used by this run.

    - Teleology: Resolves paths, refs, or digests for _validator_source_digests so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    organ_path = Path(__file__).resolve(strict=False)
    trace_path = organ_path.parents[1] / "macro_tools" / "agent_execution_trace.py"
    paths = {
        "organ_validator": organ_path,
        "public_trace_builder": trace_path,
    }
    return {
        key: _sha256(path)
        for key, path in paths.items()
        if path.is_file()
    }


def _source_module_manifest_path(input_dir: Path, *, public_root: Path) -> Path:
    """
    [ACTION] Choose the local bundle manifest when present and fall back to the public example manifest.

    - Teleology: Resolves paths, refs, or digests for _source_module_manifest_path so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    local_manifest = input_dir / "source_module_manifest.json"
    if local_manifest.is_file():
        return local_manifest
    return public_root / SOURCE_MODULE_MANIFEST_REF


def _source_module_target_path(
    row: dict[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> tuple[Path, str]:
    """
    [ACTION] Resolve one source-manifest row to its public target path and display ref.

    - Teleology: Resolves paths, refs, or digests for _source_module_target_path so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    target_ref = _strip_microcosm_prefix(str(row.get("target_ref") or ""))
    row_path = str(row.get("path") or "")
    if target_ref:
        return public_root / target_ref, target_ref
    if row_path:
        path = manifest_path.parent / row_path
        return path, _display(path, public_root=public_root)
    return public_root, ""


def _source_artifact_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION] Collect public source-artifact paths declared by benchmark-integrity fixtures.

    - Teleology: Resolves paths, refs, or digests for _source_artifact_paths so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir, public_root=public_root)
    if not manifest_path.is_file():
        return []
    manifest = read_json_strict(manifest_path)
    paths = [manifest_path]
    for row in _rows(manifest, "modules"):
        target_path, _target_ref = _source_module_target_path(
            row, manifest_path=manifest_path, public_root=public_root
        )
        if target_path.is_file():
            paths.append(target_path)
    return paths


def _fallback_bundle_root(public_root: Path) -> Path:
    """
    [ACTION] Locate the bundled benchmark-integrity example when caller input omits it.

    - Teleology: Resolves paths, refs, or digests for _fallback_bundle_root so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        public_root
        / "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle"
    )


def _resolve_public_ref(
    ref: str,
    *,
    input_dir: Path,
    public_root: Path,
) -> Path | None:
    """
    [ACTION] Resolve a public fixture or source ref without escaping the public root.

    - Teleology: Resolves paths, refs, or digests for _resolve_public_ref so downstream receipts
      can cite public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not ref or ref.startswith("/") or ".." in Path(ref).parts:
        return None
    stripped = _strip_microcosm_prefix(ref)
    for root in (input_dir, _fallback_bundle_root(public_root), public_root):
        candidate = root / stripped
        if candidate.is_file():
            return candidate
    return None


def _evidence_artifact_paths(input_dir: Path, *, public_root: Path) -> list[Path]:
    """
    [ACTION] Collect evidence artifact paths referenced by replay observations and negative cases.

    - Teleology: Resolves paths, refs, or digests for _evidence_artifact_paths so downstream
      receipts can cite public-root-relative evidence rather than absolute private workspace
      coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    replay_path = input_dir / "replay_observations.json"
    if not replay_path.is_file():
        return []
    try:
        observations = read_json_strict(replay_path)
    except (OSError, TypeError, ValueError):
        return []

    paths: list[Path] = []
    seen: set[Path] = set()
    for row in _rows(observations, "replay_observations"):
        for ref_field in EVIDENCE_REF_FIELDS:
            path = _resolve_public_ref(
                str(row.get(ref_field) or ""),
                input_dir=input_dir,
                public_root=public_root,
            )
            if path is None:
                continue
            key = path.resolve(strict=False)
            if key not in seen:
                seen.add(key)
                paths.append(path)
    return paths


def _freshness_paths(input_dir: Path, *, include_negative: bool) -> list[Path]:
    """
    [ACTION] Collect all paths that make a cached bundle receipt stale when changed.

    - Teleology: Resolves paths, refs, or digests for _freshness_paths so downstream receipts
      can cite public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    public_root = _public_root_for_path(source)
    return [
        *_input_paths(source, include_negative=include_negative),
        *_source_artifact_paths(source, public_root=public_root),
        *_evidence_artifact_paths(source, public_root=public_root),
    ]


def _freshness_basis(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION] Build the freshness basis used to decide whether a bundle validation receipt can be reused.

    - Teleology: Resolves paths, refs, or digests for _freshness_basis so downstream receipts
      can cite public-root-relative evidence rather than absolute private workspace coordinates.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic display refs, path lists, or digests within the declared
      public root and preserves body-free source custody; it performs no validation authority
      upgrade on its own.
    - Fails: Missing optional paths are returned as absent where the caller handles them;
      unreadable required files, escaped refs, or digest IO failures propagate through the
      existing call path.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source = Path(input_dir)
    if not source.is_absolute():
        source = Path.cwd() / source
    public_root = _public_root_for_path(source)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    seen: set[Path] = set()
    for path in _freshness_paths(source, include_negative=include_negative):
        key = path.resolve(strict=False)
        if key in seen:
            continue
        seen.add(key)
        display = _display(path, public_root=public_root)
        if path.is_file():
            rows.append(
                {
                    "path": display,
                    "sha256": _sha256(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        else:
            missing.append(display)

    validator_schema_version = (
        "agent_benchmark_integrity_anti_gaming_replay_result_v1"
        if include_negative
        else "exported_benchmark_integrity_bundle_validation_result_v1"
    )
    basis_digest = hashlib.sha256(
        json.dumps(
            {
                "card_schema_version": CARD_SCHEMA_VERSION,
                "include_negative": include_negative,
                "inputs": rows,
                "missing_inputs": missing,
                "validator_source_digests": _validator_source_digests(),
                "validator_schema_version": validator_schema_version,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": (
            "agent_benchmark_integrity_anti_gaming_replay_freshness_basis_v1"
        ),
        "basis_digest": f"sha256:{basis_digest}",
        "card_schema_version": CARD_SCHEMA_VERSION,
        "include_negative": include_negative,
        "input_count": len(rows),
        "missing_path_count": len(missing),
        "validator_source_digests": _validator_source_digests(),
        "validator_schema_version": validator_schema_version,
        "inputs": rows,
        "missing_inputs": missing,
    }


def _fresh_bundle_receipt(input_dir: Path, out_dir: Path) -> dict[str, Any] | None:
    """
    [ACTION] Load a prior bundle receipt only when its input, validator, and evidence digests still match.

    - Teleology: Loads benchmark-integrity fixture or cached evidence for _fresh_bundle_receipt
      while keeping freshness and body-export boundaries explicit.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns parsed payloads only from declared public fixture/bundle locations or
      None/empty structures where the existing cache path is not trustworthy; it does not infer
      unseen evidence.
    - Fails: Strict JSON readers still raise on corrupt committed artifacts, while cache-miss
      and stale-cache paths return None instead of silently reusing invalid evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    path = out_dir / BUNDLE_RESULT_NAME
    if not path.is_file():
        return None
    try:
        payload = read_json_strict(path)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != (
        "exported_benchmark_integrity_bundle_validation_result_v1"
    ):
        return None
    if payload.get("organ_id") != ORGAN_ID:
        return None
    if payload.get("input_mode") != "exported_benchmark_integrity_bundle":
        return None
    basis = _freshness_basis(input_dir, include_negative=False)
    existing_basis = payload.get("freshness_basis")
    if not isinstance(existing_basis, dict):
        return None
    if existing_basis.get("basis_digest") != basis["basis_digest"]:
        return None
    if basis["missing_path_count"]:
        return None
    reused = dict(payload)
    reused["freshness_basis"] = basis
    reused["receipt_reused"] = True
    return reused


def validate_source_module_imports(
    input_dir: Path,
    *,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION] Validate copied source-module provenance, target refs, material classes, private scans, and manifest claims.

    - Teleology: Makes the benchmark-integrity organ's validate_source_module_imports stage
      inspectable as an explicit validation boundary, so source indexes, CodeMap nodes, and
      public receipts can route from the organ overview to this evidence check without private
      context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    manifest_path = _source_module_manifest_path(input_dir, public_root=public_root)
    manifest_ref = _display(manifest_path, public_root=public_root)
    findings: list[dict[str, Any]] = []
    modules: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_SOURCE_MODULE_MANIFEST_MISSING",
                "Benchmark integrity body floor requires a source_module_manifest.json for copied macro provenance bodies.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
        return {
            "status": "blocked",
            "source_module_manifest_ref": manifest_ref,
            "module_count": 0,
            "copied_source_artifact_count": 0,
            "body_text_in_receipt": False,
            "modules": [],
            "findings": findings,
            "observed_negative_cases": {},
        }

    manifest = read_json_strict(manifest_path)
    if manifest.get("source_import_class") != SOURCE_IMPORT_CLASS:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_SOURCE_IMPORT_CLASS_MISMATCH",
                "Source module manifest must declare copied_non_secret_macro_body.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_SOURCE_BODY_IN_RECEIPT_FORBIDDEN",
                "Copied macro pattern bodies may live in source_artifacts, not in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )
    if manifest.get("body_text_in_receipt") is True:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_SOURCE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                "Source module manifests must not export copied body text in receipts.",
                case_id="source_module_manifest_floor",
                subject_id=manifest_ref,
                subject_kind="source_module_manifest",
            )
        )

    for row in _rows(manifest, "modules"):
        module_id = str(row.get("module_id") or "")
        target_path, target_ref = _source_module_target_path(
            row, manifest_path=manifest_path, public_root=public_root
        )
        material_class = str(row.get("material_class") or "")
        expected_digest = str(row.get("sha256") or "")
        relation = str(row.get("source_to_target_relation") or "")
        if row.get("source_import_class") != SOURCE_IMPORT_CLASS:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_IMPORT_CLASS_MISMATCH",
                    "Source module rows must declare copied_non_secret_macro_body.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if material_class not in PUBLIC_SAFE_SOURCE_MODULE_CLASSES:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_CLASS_FORBIDDEN",
                    "Benchmark integrity may import public macro pattern provenance bodies only.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_copied") is not True or row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_BODY_BOUNDARY_INVALID",
                    "Source module rows must set body_copied=true and body_in_receipt=false.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if row.get("body_text_in_receipt") is True:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_BODY_TEXT_IN_RECEIPT_FORBIDDEN",
                    "Source module rows must not export copied body text in receipts.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if relation not in {"exact_copy", "source_faithful_json_slice"}:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_RELATION_UNVERIFIED",
                    "Source module rows must state exact_copy or source_faithful_json_slice.",
                    case_id="source_module_manifest_floor",
                    subject_id=module_id or target_ref or "source_module",
                    subject_kind="source_module",
                )
            )
        if not target_path.is_file():
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_TARGET_MISSING",
                    "Source module target must exist inside the public bundle.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
            continue
        actual_digest = _sha256(target_path)
        if expected_digest != actual_digest:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_MODULE_DIGEST_MISMATCH",
                    "Source module target digest must match source_module_manifest.json.",
                    case_id="source_module_manifest_floor",
                    subject_id=target_ref or module_id or "source_module",
                    subject_kind="source_module",
                )
            )
        content_findings: list[dict[str, Any]] = []
        real_trace_evidence: dict[str, Any] | None = None
        if material_class == REAL_BENCHMARK_TRACE_MATERIAL_CLASS:
            try:
                real_trace_payload = read_json_strict(target_path)
            except (OSError, TypeError, ValueError):
                content_findings.append(
                    _finding(
                        "BENCHMARK_INTEGRITY_REAL_TRACE_ARTIFACT_UNREADABLE",
                        "Copied real benchmark trace artifacts must be readable JSON.",
                        case_id="source_module_real_trace_floor",
                        subject_id=target_ref or module_id or "real_benchmark_trace_artifact",
                        subject_kind="real_benchmark_trace_artifact",
                    )
                )
            else:
                real_trace_evidence = _real_trace_evidence_summary(real_trace_payload)
                content_findings.extend(
                    _real_trace_artifact_findings(
                        real_trace_payload,
                        module_id=module_id,
                        target_ref=target_ref,
                    )
                )
            findings.extend(content_findings)
        modules.append(
            {
                "module_id": module_id,
                "source_ref": str(row.get("source_ref") or ""),
                "target_ref": target_ref,
                "material_class": material_class,
                "sha256": expected_digest,
                "actual_sha256": actual_digest,
                "line_count": row.get("line_count"),
                "source_to_target_relation": relation,
                "real_trace_artifact_status": (
                    "blocked" if content_findings else PASS
                )
                if material_class == REAL_BENCHMARK_TRACE_MATERIAL_CLASS
                else None,
                "real_session_evidence": real_trace_evidence,
                "body_in_receipt": False,
                "body_text_in_receipt": False,
            }
        )

    return {
        "status": PASS if modules and not findings else "blocked",
        "source_module_manifest_ref": manifest_ref,
        "module_count": len(modules),
        "copied_source_artifact_count": len(modules),
        "body_text_in_receipt": False,
        "modules": sorted(modules, key=lambda row: row["module_id"]),
        "findings": findings,
        "observed_negative_cases": {},
    }


def _load_payloads(input_dir: Path, *, include_negative: bool) -> dict[str, Any]:
    """
    [ACTION] Load the projection protocol, policies, replay cases, observations, and requested negative fixtures.

    - Teleology: Loads benchmark-integrity fixture or cached evidence for _load_payloads while
      keeping freshness and body-export boundaries explicit.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns parsed payloads only from declared public fixture/bundle locations or
      None/empty structures where the existing cache path is not trustworthy; it does not infer
      unseen evidence.
    - Fails: Strict JSON readers still raise on corrupt committed artifacts, while cache-miss
      and stale-cache paths return None instead of silently reusing invalid evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        path.stem: read_json_strict(path)
        for path in _input_paths(input_dir, include_negative=include_negative)
    }


def _finding(
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> dict[str, Any]:
    """
    [ACTION] Create one normalized blocked finding row for receipts and boards.

    - Teleology: Keeps the replay-evidence accounting step _finding explicit, so gaming-pattern
      decisions are traceable from row input to finding, reason code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "error_code": code,
        "message": message,
        "negative_case_id": case_id,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_in_receipt": False,
    }


def _real_trace_artifact_findings(
    payload: object,
    *,
    module_id: str,
    target_ref: str,
) -> list[dict[str, Any]]:
    """
    [ACTION] Validate the public real-trace artifact required by the replay source manifest.

    - Teleology: Keeps the replay-evidence accounting step _real_trace_artifact_findings
      explicit, so gaming-pattern decisions are traceable from row input to finding, reason
      code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    trace = payload if isinstance(payload, dict) else {}
    subject_id = target_ref or module_id or "real_benchmark_trace_artifact"
    findings: list[dict[str, Any]] = []

    if trace.get("schema_version") != "public_sanitized_real_benchmark_trace_v1":
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_SCHEMA_MISMATCH",
                "Copied real benchmark trace artifacts must use the public sanitized command-run trace schema.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    if trace.get("material_class") != REAL_BENCHMARK_TRACE_MATERIAL_CLASS:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_MATERIAL_CLASS_MISMATCH",
                "Copied real benchmark trace artifacts must self-declare public_sanitized_real_benchmark_trace material.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    if trace.get("body_in_receipt") is not False:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_BODY_RECEIPT_OVERCLAIM",
                "Copied real benchmark traces must keep body_in_receipt=false.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    if trace.get("status") != "completed" or trace.get("exit_code") != 0:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_COMMAND_RUN_NOT_PASSING",
                "Copied real benchmark traces must come from a completed passing command run.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    if trace.get("trace_role") != REAL_TRACE_REQUIRED_TRACE_ROLE:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_ROLE_MISMATCH",
                "Copied real benchmark traces must carry the benchmark-integrity fixture-gate trace role.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )

    argv_shape = _strings(trace.get("argv_shape"))
    if (
        "pytest" not in argv_shape
        or "-p" not in argv_shape
        or "no:cacheprovider" not in argv_shape
        or REAL_TRACE_REQUIRED_SCOPE_PATH not in argv_shape
    ):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_ARGV_SHAPE_INVALID",
                "Copied real benchmark traces must bind to the focused pytest command for this organ test without cacheprovider state.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    if REAL_TRACE_REQUIRED_SCOPE_PATH not in _strings(trace.get("scope_paths")):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_SCOPE_MISMATCH",
                "Copied real benchmark traces must include the focused organ test path in scope_paths.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )

    pytest_summary = trace.get("pytest_summary")
    pytest_rows = pytest_summary if isinstance(pytest_summary, dict) else {}
    if int(pytest_rows.get("passed") or 0) <= 0 or int(pytest_rows.get("failed") or 0) != 0:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_PYTEST_SUMMARY_INVALID",
                "Copied real benchmark traces must carry a passing focused pytest summary.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )

    required_text_fields = (
        "real_episode_id",
        "run_id",
        "command_run_metadata_sha256",
        "stdout_sha256",
        "stderr_sha256",
    )
    if any(not str(trace.get(field) or "") for field in required_text_fields):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_REQUIRED_FIELD_MISSING",
                "Copied real benchmark traces must bind run ids and command-output digests.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )

    for digest_field in (
        "command_run_metadata_sha256",
        "stdout_sha256",
        "stderr_sha256",
    ):
        digest = str(trace.get(digest_field) or "")
        if digest and not digest.startswith("sha256:"):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_REAL_TRACE_DIGEST_INVALID",
                    "Copied real benchmark trace digest fields must be sha256 refs.",
                    case_id="source_module_real_trace_floor",
                    subject_id=f"{subject_id}:{digest_field}",
                    subject_kind="real_benchmark_trace_artifact",
                )
            )

    source_refs = _strings(trace.get("source_material_refs"))
    if not source_refs or any(
        not ref.startswith("state/command_runs/") for ref in source_refs
    ):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_SOURCE_MATERIAL_REFS_INVALID",
                "Copied real benchmark traces must cite public-safe command-run source material refs.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    run_id = str(trace.get("run_id") or "")
    if run_id:
        expected_source_refs = {
            f"state/command_runs/runs/{run_id}.json",
            f"state/command_runs/outputs/{run_id}.stdout",
            f"state/command_runs/outputs/{run_id}.stderr",
        }
        if not expected_source_refs.issubset(set(source_refs)):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_REAL_TRACE_RUN_ID_SOURCE_REF_MISMATCH",
                    "Copied real benchmark traces must bind source_material_refs to the declared command run id.",
                    case_id="source_module_real_trace_floor",
                    subject_id=subject_id,
                    subject_kind="real_benchmark_trace_artifact",
                )
            )
    real_episode_id = str(trace.get("real_episode_id") or "")
    if run_id and real_episode_id and run_id not in real_episode_id:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_EPISODE_RUN_ID_MISMATCH",
                "Copied real benchmark traces must bind real_episode_id to the declared command run id.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )

    omitted = set(_strings(trace.get("omitted_live_material")))
    required_omissions = {
        "raw provider payloads",
        "credentials and cookies",
        "private issue bodies",
        "oracle patch bodies",
    }
    if not required_omissions.issubset(omitted):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_REAL_TRACE_PUBLIC_BOUNDARY_INCOMPLETE",
                "Copied real benchmark traces must declare public-safe omissions for private/live material.",
                case_id="source_module_real_trace_floor",
                subject_id=subject_id,
                subject_kind="real_benchmark_trace_artifact",
            )
        )
    return findings


def _real_trace_evidence_summary(payload: object) -> dict[str, Any]:
    """
    [ACTION] Summarize public real-trace evidence fields without carrying private bodies.

    - Teleology: Keeps the replay-evidence accounting step _real_trace_evidence_summary
      explicit, so gaming-pattern decisions are traceable from row input to finding, reason
      code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    trace = payload if isinstance(payload, dict) else {}
    pytest_summary = trace.get("pytest_summary")
    pytest_rows = pytest_summary if isinstance(pytest_summary, dict) else {}
    source_refs = _strings(trace.get("source_material_refs"))
    run_id = str(trace.get("run_id") or "")
    expected_source_refs = {
        f"state/command_runs/runs/{run_id}.json",
        f"state/command_runs/outputs/{run_id}.stdout",
        f"state/command_runs/outputs/{run_id}.stderr",
    } if run_id else set()
    digest_fields = (
        "command_run_metadata_sha256",
        "stdout_sha256",
        "stderr_sha256",
    )
    return {
        "schema_version": "agent_benchmark_integrity_real_session_evidence_v1",
        "material_class": str(trace.get("material_class") or ""),
        "trace_role": str(trace.get("trace_role") or ""),
        "run_id": run_id,
        "real_episode_id": str(trace.get("real_episode_id") or ""),
        "status": str(trace.get("status") or ""),
        "exit_code": trace.get("exit_code"),
        "command_passed": trace.get("status") == "completed"
        and trace.get("exit_code") == 0,
        "pytest_passed": int(pytest_rows.get("passed") or 0) > 0
        and int(pytest_rows.get("failed") or 0) == 0,
        "focused_scope_bound": REAL_TRACE_REQUIRED_SCOPE_PATH
        in _strings(trace.get("scope_paths")),
        "source_material_refs_bound_to_run_id": bool(expected_source_refs)
        and expected_source_refs.issubset(set(source_refs)),
        "real_episode_bound_to_run_id": bool(run_id)
        and run_id in str(trace.get("real_episode_id") or ""),
        "required_digest_fields_present": all(
            str(trace.get(field) or "") for field in digest_fields
        ),
        "digest_fields_are_sha256": all(
            str(trace.get(field) or "").startswith("sha256:")
            for field in digest_fields
        ),
        "public_boundary_declared": {
            "raw provider payloads",
            "credentials and cookies",
            "private issue bodies",
            "oracle patch bodies",
        }.issubset(set(_strings(trace.get("omitted_live_material")))),
        "body_in_receipt": False,
    }


def _real_trace_evidence_passes(evidence: dict[str, Any]) -> bool:
    """
    [ACTION] Decide whether parsed real-trace evidence clears the integrity floor.

    - Teleology: Keeps the replay-evidence accounting step _real_trace_evidence_passes explicit,
      so gaming-pattern decisions are traceable from row input to finding, reason code, and
      receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return (
        evidence.get("material_class") == REAL_BENCHMARK_TRACE_MATERIAL_CLASS
        and evidence.get("trace_role") == REAL_TRACE_REQUIRED_TRACE_ROLE
        and evidence.get("command_passed") is True
        and evidence.get("pytest_passed") is True
        and evidence.get("focused_scope_bound") is True
        and evidence.get("source_material_refs_bound_to_run_id") is True
        and evidence.get("real_episode_bound_to_run_id") is True
        and evidence.get("required_digest_fields_present") is True
        and evidence.get("digest_fields_are_sha256") is True
        and evidence.get("public_boundary_declared") is True
        and evidence.get("body_in_receipt") is False
    )


def _replay_real_session_evidence(
    row: dict[str, Any],
    *,
    real_trace_ref: str,
    real_trace_verified: bool,
    real_trace_artifact_status: str,
    real_trace_evidence_by_ref: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION] Attach real-session evidence status to a replay row without expanding private trace material.

    - Teleology: Keeps the replay-evidence accounting step _replay_real_session_evidence
      explicit, so gaming-pattern decisions are traceable from row input to finding, reason
      code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    evidence = real_trace_evidence_by_ref.get(real_trace_ref, {})
    evidence_passes = _real_trace_evidence_passes(evidence)
    packet = {
        "schema_version": "agent_benchmark_integrity_replay_real_session_evidence_v1",
        "evidence_source": "manifest_verified_public_sanitized_real_benchmark_trace",
        "real_benchmark_trace_ref": real_trace_ref,
        "real_benchmark_trace_verified": real_trace_verified,
        "real_benchmark_trace_artifact_status": real_trace_artifact_status,
        "trace_run_id": evidence.get("run_id"),
        "trace_role": evidence.get("trace_role"),
        "command_passed": evidence.get("command_passed") is True,
        "pytest_passed": evidence.get("pytest_passed") is True,
        "focused_scope_bound": evidence.get("focused_scope_bound") is True,
        "source_material_refs_bound_to_run_id": evidence.get(
            "source_material_refs_bound_to_run_id"
        )
        is True,
        "real_episode_bound_to_run_id": evidence.get("real_episode_bound_to_run_id")
        is True,
        "public_boundary_declared": evidence.get("public_boundary_declared") is True,
        "file_access_log_ref": row.get("file_access_log_ref"),
        "contamination_check_ref": row.get("contamination_check_ref"),
        "trusted_reference_score_ref": row.get("trusted_reference_score_ref"),
        "file_access_backed_by_real_session": bool(row.get("file_access_log_ref"))
        and evidence_passes,
        "contamination_backed_by_real_session": bool(row.get("contamination_check_ref"))
        and evidence_passes,
        "trusted_reference_backed_by_real_session": bool(
            row.get("trusted_reference_score_ref")
        )
        and evidence_passes,
        "body_in_receipt": False,
    }
    packet["session_evidence_passes"] = (
        packet["real_benchmark_trace_verified"] is True
        and packet["file_access_backed_by_real_session"] is True
        and packet["contamination_backed_by_real_session"] is True
        and packet["trusted_reference_backed_by_real_session"] is True
    )
    return packet


def _evidence_finding(
    findings: list[dict[str, Any]],
    code: str,
    message: str,
    *,
    replay_id: str,
    ref: str,
) -> None:
    """
    [ACTION] Append a replay evidence finding tied to a specific evidence ref.

    - Teleology: Keeps the replay-evidence accounting step _evidence_finding explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings.append(
        _finding(
            code,
            message,
            case_id="parsed_evidence_artifact_floor",
            subject_id=ref or replay_id,
            subject_kind="benchmark_integrity_evidence_artifact",
        )
    )


def _load_evidence_artifact(
    row: dict[str, Any],
    *,
    ref_field: str,
    replay_id: str,
    case_id: str,
    evaluator_id: str,
    evaluator_config_hash: str,
    input_dir: Path,
    public_root: Path,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """
    [ACTION] Load and validate one evidence artifact referenced by a replay row.

    - Teleology: Loads benchmark-integrity fixture or cached evidence for
      _load_evidence_artifact while keeping freshness and body-export boundaries explicit.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns parsed payloads only from declared public fixture/bundle locations or
      None/empty structures where the existing cache path is not trustworthy; it does not infer
      unseen evidence.
    - Fails: Strict JSON readers still raise on corrupt committed artifacts, while cache-miss
      and stale-cache paths return None instead of silently reusing invalid evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    ref = str(row.get(ref_field) or "")
    expected_kind = EVIDENCE_REF_FIELDS[ref_field]
    path = _resolve_public_ref(ref, input_dir=input_dir, public_root=public_root)
    if path is None:
        _evidence_finding(
            findings,
            "BENCHMARK_INTEGRITY_EVIDENCE_ARTIFACT_MISSING",
            "Replay evidence refs must resolve to public-safe parsed evidence artifacts.",
            replay_id=replay_id,
            ref=ref,
        )
        return {}, False
    try:
        payload = read_json_strict(path)
    except (OSError, TypeError, ValueError):
        _evidence_finding(
            findings,
            "BENCHMARK_INTEGRITY_EVIDENCE_ARTIFACT_UNREADABLE",
            "Replay evidence artifacts must be readable JSON.",
            replay_id=replay_id,
            ref=ref,
        )
        return {}, False
    evidence = payload if isinstance(payload, dict) else {}
    ok = True
    if evidence.get("schema_version") != "benchmark_integrity_evidence_artifact_v1":
        ok = False
        _evidence_finding(
            findings,
            "BENCHMARK_INTEGRITY_EVIDENCE_SCHEMA_MISMATCH",
            "Replay evidence artifacts must use benchmark_integrity_evidence_artifact_v1.",
            replay_id=replay_id,
            ref=ref,
        )
    if evidence.get("evidence_kind") != expected_kind:
        ok = False
        _evidence_finding(
            findings,
            "BENCHMARK_INTEGRITY_EVIDENCE_KIND_MISMATCH",
            "Replay evidence artifact kind must match the replay ref field.",
            replay_id=replay_id,
            ref=ref,
        )
    if evidence.get("body_in_receipt") is not False:
        ok = False
        _evidence_finding(
            findings,
            "BENCHMARK_INTEGRITY_EVIDENCE_BODY_IN_RECEIPT_FORBIDDEN",
            "Replay evidence artifacts must remain body-free public receipts.",
            replay_id=replay_id,
            ref=ref,
        )
    expected_bindings = {
        "replay_id": replay_id,
        "case_id": case_id,
        "evaluator_id": evaluator_id,
        "evaluator_config_hash": evaluator_config_hash,
    }
    for key, expected in expected_bindings.items():
        if str(evidence.get(key) or "") != expected:
            ok = False
            _evidence_finding(
                findings,
                "BENCHMARK_INTEGRITY_EVIDENCE_BINDING_MISMATCH",
                "Replay evidence artifacts must bind to the same replay, case, evaluator, and config hash.",
                replay_id=replay_id,
                ref=f"{ref}:{key}",
            )
    return evidence, ok


def _parsed_evidence_packet(
    row: dict[str, Any],
    *,
    replay_id: str,
    case_id: str,
    evaluator_id: str,
    evaluator_config_hash: str,
    input_dir: Path,
    public_root: Path,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION] Parse all evidence artifacts for a replay row into a body-free integrity packet.

    - Teleology: Keeps the replay-evidence accounting step _parsed_evidence_packet explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    artifacts: dict[str, dict[str, Any]] = {}
    valid: dict[str, bool] = {}
    for ref_field, evidence_kind in EVIDENCE_REF_FIELDS.items():
        artifacts[evidence_kind], valid[evidence_kind] = _load_evidence_artifact(
            row,
            ref_field=ref_field,
            replay_id=replay_id,
            case_id=case_id,
            evaluator_id=evaluator_id,
            evaluator_config_hash=evaluator_config_hash,
            input_dir=input_dir,
            public_root=public_root,
            findings=findings,
        )

    file_access = artifacts.get("file_access_log", {})
    contamination = artifacts.get("contamination_check", {})
    trusted = artifacts.get("trusted_reference_score", {})
    output = artifacts.get("output_replay", {})
    contamination_flags = {
        key: contamination.get(key) is True
        for key in (
            "training_material_contains_test_case",
            "hidden_gold_accessed",
            "oracle_patch_body_present",
            "private_issue_body_present",
            "provider_payload_present",
            "misleading_test_admitted",
        )
    }
    packet = {
        "schema_version": "agent_benchmark_integrity_parsed_evidence_packet_v1",
        "artifact_validity": dict(sorted(valid.items())),
        "all_artifacts_valid": all(valid.values()),
        "file_access_passes": valid.get("file_access_log") is True
        and file_access.get("file_access_log_passed") is True
        and file_access.get("forbidden_file_access") is not True,
        "contamination_check_passes": valid.get("contamination_check") is True
        and not any(contamination_flags.values()),
        "trusted_reference_passes": valid.get("trusted_reference_score") is True
        and trusted.get("trusted_reference_available") is True
        and trusted.get("benchmark_score_claimed") is not True
        and trusted.get("metric_claim_authorized") is not True,
        "output_replay_passes": valid.get("output_replay") is True
        and output.get("output_replay_present") is True
        and output.get("grading_mode") != "final_answer_only",
        "contamination_flags": contamination_flags,
        "body_in_receipt": False,
    }
    packet["evidence_passes"] = (
        packet["all_artifacts_valid"] is True
        and packet["file_access_passes"] is True
        and packet["contamination_check_passes"] is True
        and packet["trusted_reference_passes"] is True
        and packet["output_replay_passes"] is True
    )
    return packet


def _record(
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    code: str,
    message: str,
    *,
    case_id: str,
    subject_id: str,
    subject_kind: str,
) -> None:
    """
    [ACTION] Append a finding and record the observed negative-case code.

    - Teleology: Keeps the replay-evidence accounting step _record explicit, so gaming-pattern
      decisions are traceable from row input to finding, reason code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings.append(
        _finding(
            code,
            message,
            case_id=case_id,
            subject_id=subject_id,
            subject_kind=subject_kind,
        )
    )
    observed[case_id].add(code)


def _merge_observed(*results: dict[str, Any]) -> dict[str, list[str]]:
    """
    [ACTION] Merge observed negative-case codes from component validator results.

    - Teleology: Keeps the replay-evidence accounting step _merge_observed explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    merged: dict[str, set[str]] = defaultdict(set)
    for result in results:
        for case_id, codes in result.get("observed_negative_cases", {}).items():
            for code in codes:
                merged[case_id].add(str(code))
    return {case_id: sorted(codes) for case_id, codes in sorted(merged.items())}


def _merge_findings(*results: dict[str, Any]) -> list[dict[str, Any]]:
    """
    [ACTION] Merge and deterministically sort findings from component validator results.

    - Teleology: Keeps the replay-evidence accounting step _merge_findings explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    findings: list[dict[str, Any]] = []
    for result in results:
        findings.extend(result.get("findings", []))
    return sorted(
        findings,
        key=lambda row: (
            str(row.get("negative_case_id") or ""),
            str(row.get("subject_kind") or ""),
            str(row.get("subject_id") or ""),
            str(row.get("error_code") or ""),
        ),
    )


def _semantic_negative_case_id(row: dict[str, Any]) -> str | None:
    """
    [ACTION] Infer which negative-case trigger a replay row actually encodes.

    - Teleology: Keeps the replay-evidence accounting step _semantic_negative_case_id explicit,
      so gaming-pattern decisions are traceable from row input to finding, reason code, and
      receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if row.get("evaluator_mutated") is True:
        return "evaluator_edit_attempt"
    if row.get("training_material_contains_test_case") is True:
        return (
            "real_trace_train_test_leakage"
            if row.get("real_benchmark_trace_ref")
            else "train_test_leakage"
        )
    if "oracle_patch_body" in row or row.get("oracle_patch_body_present") is True:
        return "oracle_patch_body_leakage"
    if row.get("hidden_gold_accessed") is True or "hidden_gold_body" in row:
        return "hidden_gold_access"
    if row.get("grading_mode") == "final_answer_only":
        return "final_answer_only_grading"
    if "provider_payload" in row or row.get("provider_payload_ref") == "raw_provider_payload":
        return "provider_payload_leakage"
    if row.get("benchmark_score_claimed") is True or row.get("metric_claim_authorized") is True:
        return "score_overclaim"
    if int(row.get("attempt_count") or 1) > 1 and row.get("selected_attempt_policy") == "best_only":
        return "pass_k_cherry_picking"
    if row.get("misleading_test_admitted") is True:
        return "misleading_test_admitted"
    if "private_issue_body" in row or row.get("private_issue_body_present") is True:
        return "private_issue_body_leakage"
    return None


def validate_projection_protocol(payload: object) -> dict[str, Any]:
    """
    [ACTION] Validate that the projection protocol cites enough source, receipt, and regression-fixture backing.

    - Teleology: Makes the benchmark-integrity organ's validate_projection_protocol stage
      inspectable as an explicit validation boundary, so source indexes, CodeMap nodes, and
      public receipts can route from the organ overview to this evidence check without private
      context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    protocol = payload if isinstance(payload, dict) else {}
    source_refs = _strings(protocol.get("source_refs"))
    source_pattern_ids = _strings(protocol.get("source_pattern_ids"))
    projection_receipts = _strings(protocol.get("projection_receipt_refs"))
    regression_fixture_refs = _strings(protocol.get("public_regression_fixture_refs"))
    findings: list[dict[str, Any]] = []
    if (
        len(source_refs) < 3
        or "agent_benchmark_integrity_anti_gaming_replay_compound"
        not in source_pattern_ids
        or len(projection_receipts) < 2
        or len(regression_fixture_refs) < 3
    ):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_PROJECTION_PROTOCOL_DENSITY_MISSING",
                "Benchmark integrity projection must cite macro patterns, receipts, and body-free regression fixture refs.",
                case_id="projection_protocol_floor",
                subject_id=str(protocol.get("protocol_id") or "projection_protocol"),
                subject_kind="projection_protocol",
            )
        )
    return {
        "status": PASS if not findings else "blocked",
        "protocol_id": protocol.get("protocol_id"),
        "source_refs": source_refs,
        "source_pattern_ids": source_pattern_ids,
        "projection_receipt_refs": projection_receipts,
        "public_regression_fixture_refs": regression_fixture_refs,
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_locked_evaluator_policy(payload: object) -> dict[str, Any]:
    """
    [ACTION] Validate locked evaluators, required replay fields, allowed verdicts, and blocked claim ids.

    - Teleology: Makes the benchmark-integrity organ's validate_locked_evaluator_policy stage
      inspectable as an explicit validation boundary, so source indexes, CodeMap nodes, and
      public receipts can route from the organ overview to this evidence check without private
      context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy = payload if isinstance(payload, dict) else {}
    locked = set(_strings(policy.get("locked_evaluator_ids")))
    config_hashes = _locked_evaluator_config_hashes(policy)
    required = set(_strings(policy.get("required_replay_fields")))
    findings: list[dict[str, Any]] = []
    if not locked or not set(REQUIRED_REPLAY_FIELDS).issubset(required):
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_LOCKED_EVALUATOR_POLICY_INCOMPLETE",
                "Policy must declare locked evaluator ids and required replay fields.",
                case_id="locked_evaluator_policy_floor",
                subject_id=str(policy.get("policy_id") or "locked_evaluator_policy"),
                subject_kind="locked_evaluator_policy",
            )
        )
    for evaluator_id in sorted(locked):
        if not config_hashes.get(evaluator_id):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_LOCKED_EVALUATOR_CONFIG_HASH_MISSING",
                    "Locked evaluator policy must bind each evaluator id to allowed config hashes.",
                    case_id="locked_evaluator_policy_floor",
                    subject_id=evaluator_id,
                    subject_kind="locked_evaluator_policy",
                )
            )
    for evaluator_id, hashes in config_hashes.items():
        if evaluator_id not in locked:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_LOCKED_EVALUATOR_CONFIG_HASH_UNREGISTERED",
                    "Evaluator config hashes may be declared only for locked evaluator ids.",
                    case_id="locked_evaluator_policy_floor",
                    subject_id=evaluator_id,
                    subject_kind="locked_evaluator_policy",
                )
            )
        for digest in hashes:
            if not digest.startswith("sha256:"):
                findings.append(
                    _finding(
                        "BENCHMARK_INTEGRITY_LOCKED_EVALUATOR_CONFIG_HASH_INVALID",
                        "Locked evaluator config hashes must be sha256 digest refs.",
                        case_id="locked_evaluator_policy_floor",
                        subject_id=evaluator_id,
                        subject_kind="locked_evaluator_policy",
                    )
                )
    for field in (
        "provider_calls_authorized",
        "benchmark_score_claim_authorized",
        "release_authorized",
    ):
        if policy.get(field) is not False:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_POLICY_AUTHORITY_OVERCLAIM",
                    "Benchmark integrity policy cannot authorize providers, score claims, or release.",
                    case_id="locked_evaluator_policy_floor",
                    subject_id=field,
                    subject_kind="locked_evaluator_policy",
                )
            )
    return {
        "status": PASS if not findings else "blocked",
        "policy_id": policy.get("policy_id"),
        "locked_evaluator_ids": sorted(locked),
        "locked_evaluator_config_hashes": config_hashes,
        "locked_evaluator_config_hash_count": sum(
            len(hashes) for hashes in config_hashes.values()
        ),
        "required_replay_fields": sorted(required),
        "findings": findings,
        "observed_negative_cases": {},
    }


def validate_benchmark_cases(payload: object) -> dict[str, Any]:
    """
    [ACTION] Validate benchmark case rows, trusted score refs, leakage labels, and uniqueness.

    - Teleology: Makes the benchmark-integrity organ's validate_benchmark_cases stage
      inspectable as an explicit validation boundary, so source indexes, CodeMap nodes, and
      public receipts can route from the organ overview to this evidence check without private
      context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows = _rows(payload, "benchmark_cases")
    findings: list[dict[str, Any]] = []
    exported: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id or not row.get("task_hash") or not row.get("held_out_guard_ids"):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_CASE_FLOOR_MISSING",
                    "Benchmark cases require case id, task hash, and held-out guard ids.",
                    case_id="benchmark_case_floor",
                    subject_id=case_id or "benchmark_case",
                    subject_kind="benchmark_case",
                )
            )
        if any(key in row for key in FORBIDDEN_BODY_KEYS):
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_CASE_BODY_FORBIDDEN",
                    "Benchmark cases may expose hashes and refs, not private body text.",
                    case_id="benchmark_case_floor",
                    subject_id=case_id or "benchmark_case",
                    subject_kind="benchmark_case",
                )
            )
        if row.get("body_in_receipt") is not False:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_BODY_IN_RECEIPT_FORBIDDEN",
                    "Benchmark cases must expose ids, hashes, and refs only, with body_in_receipt=false.",
                    case_id="benchmark_case_floor",
                    subject_id=case_id or "benchmark_case",
                    subject_kind="benchmark_case",
                )
            )
        exported.append(
            {
                "case_id": case_id,
                "split": row.get("split"),
                "task_hash": row.get("task_hash"),
                "patch_hash": row.get("patch_hash"),
                "held_out_guard_ids": _strings(row.get("held_out_guard_ids")),
                "body_in_receipt": False,
            }
        )
    return {
        "status": PASS if rows and not findings else "blocked",
        "benchmark_case_count": len(rows),
        "held_out_guard_count": sum(len(row["held_out_guard_ids"]) for row in exported),
        "benchmark_cases": exported,
        "findings": findings,
        "observed_negative_cases": {},
    }


def _validate_replay_row(
    row: dict[str, Any],
    *,
    locked_evaluators: set[str],
    locked_evaluator_config_hashes: dict[str, list[str]],
    known_case_ids: set[str],
    source_artifact_classes: dict[str, str],
    source_artifact_statuses: dict[str, str],
    real_trace_evidence_by_ref: dict[str, dict[str, Any]],
    input_dir: Path,
    public_root: Path,
    findings: list[dict[str, Any]],
    observed: dict[str, set[str]],
    negative: bool,
) -> dict[str, Any]:
    """
    [ACTION] Validate one replay row against evaluator locks, case registry, evidence refs, semantic negative triggers, and overclaim guards.

    - Teleology: Keeps the replay-evidence accounting step _validate_replay_row explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    case_id = str(row.get("expected_negative_case_id") or row.get("case_id") or "replay")
    replay_case_id = str(row.get("case_id") or "")
    replay_id = str(row.get("replay_id") or row.get("case_id") or case_id)
    subject_kind = "negative_case" if negative else "replay_observation"

    missing_fields = [field for field in REQUIRED_REPLAY_FIELDS if not row.get(field)]
    evaluator_id = str(row.get("evaluator_id") or "")
    evaluator_config_hash = str(row.get("evaluator_config_hash") or "")
    allowed_config_hashes = locked_evaluator_config_hashes.get(evaluator_id, [])
    config_hash_matches_policy = (
        bool(evaluator_config_hash) and evaluator_config_hash in allowed_config_hashes
    )
    verdict = str(row.get("integrity_verdict") or "")
    declared_verdict_valid = verdict in ALLOWED_INTEGRITY_VERDICTS
    source_evidence_refs = _strings(row.get("source_artifact_evidence_refs"))
    source_artifact_refs = set(source_artifact_classes)
    unknown_source_evidence_refs = sorted(
        ref for ref in source_evidence_refs if ref not in source_artifact_refs
    )
    real_trace_ref = str(row.get("real_benchmark_trace_ref") or "")
    real_trace_class = source_artifact_classes.get(real_trace_ref, "")
    real_trace_artifact_status = source_artifact_statuses.get(real_trace_ref, "")
    real_trace_verified = (
        bool(real_trace_ref)
        and real_trace_class == REAL_BENCHMARK_TRACE_MATERIAL_CLASS
        and real_trace_artifact_status == PASS
        and real_trace_ref in source_evidence_refs
    )
    real_session_evidence = _replay_real_session_evidence(
        row,
        real_trace_ref=real_trace_ref,
        real_trace_verified=real_trace_verified,
        real_trace_artifact_status=real_trace_artifact_status,
        real_trace_evidence_by_ref=real_trace_evidence_by_ref,
    )
    parsed_evidence = (
        {
            "schema_version": "agent_benchmark_integrity_parsed_evidence_packet_v1",
            "evidence_passes": True,
            "not_required_for_negative_fixture": True,
            "body_in_receipt": False,
        }
        if negative
        else _parsed_evidence_packet(
            row,
            replay_id=replay_id,
            case_id=replay_case_id,
            evaluator_id=evaluator_id,
            evaluator_config_hash=evaluator_config_hash,
            input_dir=input_dir,
            public_root=public_root,
            findings=findings,
        )
    )
    reasons: list[str] = []

    if verdict and not declared_verdict_valid:
        reasons.append("declared_integrity_verdict_invalid")
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_DECLARED_VERDICT_INVALID",
                "Replay observations may declare only integrity_pass or quarantine integrity verdicts.",
                case_id=case_id,
                subject_id=replay_id,
                subject_kind=subject_kind,
            )
        )
    if evaluator_id not in locked_evaluators or row.get("evaluator_mutated") is True:
        reasons.append("evaluator_not_locked")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_EVALUATOR_EDIT_FORBIDDEN",
            "Evaluator ids and configs must be locked before replay.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if evaluator_id in locked_evaluators and not config_hash_matches_policy:
        reasons.append("evaluator_config_hash_mismatch")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_EVALUATOR_CONFIG_HASH_MISMATCH",
            "Replay observations must use a policy-declared config hash for the locked evaluator id.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("training_material_contains_test_case") is True:
        reasons.append("train_test_leakage")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_TRAIN_TEST_LEAKAGE",
            "Benchmark replay must reject train/test contamination.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "oracle_patch_body" in row or row.get("oracle_patch_body_present") is True:
        reasons.append("oracle_patch_body")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_ORACLE_PATCH_BODY_FORBIDDEN",
            "Oracle patch bodies may not enter public benchmark replay inputs.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("hidden_gold_accessed") is True or "hidden_gold_body" in row:
        reasons.append("hidden_gold_access")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_HIDDEN_GOLD_ACCESS",
            "Hidden-gold access invalidates benchmark integrity replay.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("grading_mode") == "final_answer_only":
        reasons.append("final_answer_only")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_FINAL_ANSWER_ONLY_GRADING",
            "Repository repair benchmarks require replayable patch/test evidence, not final-answer-only grading.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "provider_payload" in row or row.get("provider_payload_ref") == "raw_provider_payload":
        reasons.append("provider_payload")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PROVIDER_PAYLOAD_FORBIDDEN",
            "Provider payload bodies are outside the public benchmark replay boundary.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("benchmark_score_claimed") is True or row.get("metric_claim_authorized") is True:
        reasons.append("score_overclaim")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_SCORE_OVERCLAIM",
            "Synthetic replay receipts cannot claim a benchmark score or capability metric.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if int(row.get("attempt_count") or 1) > 1 and row.get("selected_attempt_policy") == "best_only":
        reasons.append("pass_k_cherry_picking")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PASS_K_CHERRY_PICKING",
            "Pass@k-style cherry-picking must be labeled and cannot promote a single best replay as the score.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if row.get("misleading_test_admitted") is True:
        reasons.append("misleading_test")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_MISLEADING_TEST_ADMITTED",
            "Misleading tests must be denied or quarantined before benchmark scoring.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if "private_issue_body" in row or row.get("private_issue_body_present") is True:
        reasons.append("private_issue_body")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_PRIVATE_ISSUE_BODY_FORBIDDEN",
            "Private issue bodies may not enter public benchmark replay inputs.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if replay_case_id not in known_case_ids:
        reasons.append("unregistered_case_replay")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_UNREGISTERED_CASE_REPLAY",
            "Replay observations must bind to a case id declared in benchmark_cases.json.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if missing_fields:
        reasons.append("replay_field_missing")
    if not negative and parsed_evidence.get("evidence_passes") is not True:
        reasons.append("parsed_evidence_unverified")
        if parsed_evidence.get("file_access_passes") is not True:
            reasons.append("file_access_evidence_failed")
        if parsed_evidence.get("contamination_check_passes") is not True:
            reasons.append("contamination_evidence_failed")
        if parsed_evidence.get("trusted_reference_passes") is not True:
            reasons.append("trusted_reference_evidence_failed")
        if parsed_evidence.get("output_replay_passes") is not True:
            reasons.append("output_replay_evidence_failed")
    if not negative:
        contamination_flags = parsed_evidence.get("contamination_flags")
        if isinstance(contamination_flags, dict):
            if contamination_flags.get("training_material_contains_test_case") is True:
                reasons.append("train_test_leakage")
            if contamination_flags.get("hidden_gold_accessed") is True:
                reasons.append("hidden_gold_access")
            if contamination_flags.get("oracle_patch_body_present") is True:
                reasons.append("oracle_patch_body")
            if contamination_flags.get("private_issue_body_present") is True:
                reasons.append("private_issue_body")
            if contamination_flags.get("provider_payload_present") is True:
                reasons.append("provider_payload")
            if contamination_flags.get("misleading_test_admitted") is True:
                reasons.append("misleading_test")
    if not real_trace_ref:
        reasons.append("real_benchmark_trace_missing")
        if not negative:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_REAL_TRACE_EVIDENCE_MISSING",
                    "Replay observations must cite a sanitized real benchmark command-run trace before an integrity pass can stand.",
                    case_id="real_benchmark_trace_floor",
                    subject_id=replay_id,
                    subject_kind=subject_kind,
                )
            )
    elif not real_trace_verified:
        reasons.append("real_benchmark_trace_unverified")
        if not negative:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_REAL_TRACE_EVIDENCE_UNVERIFIED",
                    "Replay real_benchmark_trace_ref must point to a manifest-verified public_sanitized_real_benchmark_trace source artifact and be included in source_artifact_evidence_refs.",
                    case_id="real_benchmark_trace_floor",
                    subject_id=real_trace_ref,
                    subject_kind=subject_kind,
                )
            )
    elif real_session_evidence["session_evidence_passes"] is not True:
        reasons.append("real_session_evidence_unverified")
        if not negative:
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_REAL_SESSION_EVIDENCE_UNVERIFIED",
                    "Replay integrity must be backed by manifest-verified sanitized command-run evidence, not only by hand-authored replay refs.",
                    case_id="real_session_evidence_floor",
                    subject_id=real_trace_ref,
                    subject_kind=subject_kind,
                )
            )
    if row.get("body_in_receipt") is not False:
        reasons.append("body_in_receipt")
        _record(
            findings,
            observed,
            "BENCHMARK_INTEGRITY_BODY_IN_RECEIPT_FORBIDDEN",
            "Replay observations must expose refs and labels only, with body_in_receipt=false.",
            case_id=case_id,
            subject_id=replay_id,
            subject_kind=subject_kind,
        )
    if not negative:
        if not source_evidence_refs:
            reasons.append("source_artifact_evidence_missing")
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_ARTIFACT_EVIDENCE_MISSING",
                    "Replay observations must cite copied public source-artifact evidence from the source module manifest.",
                    case_id="source_artifact_evidence_floor",
                    subject_id=replay_id,
                    subject_kind=subject_kind,
                )
            )
        for ref in unknown_source_evidence_refs:
            reasons.append("source_artifact_evidence_unverified")
            findings.append(
                _finding(
                    "BENCHMARK_INTEGRITY_SOURCE_ARTIFACT_EVIDENCE_UNVERIFIED",
                    "Replay source-artifact evidence refs must match copied source-module targets.",
                    case_id="source_artifact_evidence_floor",
                    subject_id=ref,
                    subject_kind=subject_kind,
                )
            )
    if row.get("quarantine_reason_ref"):
        reasons.append("quarantine_reason_ref")

    computed_verdict = "integrity_pass"
    if missing_fields or reasons:
        computed_verdict = "quarantine"
    return {
        "replay_id": replay_id,
        "case_id": replay_case_id,
        "expected_negative_case_id": case_id if negative else None,
        "evaluator_id": evaluator_id,
        "evaluator_config_hash": evaluator_config_hash,
        "allowed_evaluator_config_hashes": allowed_config_hashes,
        "evaluator_config_hash_matches_policy": config_hash_matches_policy,
        "integrity_verdict": verdict or computed_verdict,
        "declared_integrity_verdict": verdict,
        "declared_integrity_verdict_valid": declared_verdict_valid,
        "allowed_integrity_verdicts": list(ALLOWED_INTEGRITY_VERDICTS),
        "computed_integrity_verdict": computed_verdict,
        "reason_codes": sorted(set(reasons)),
        "required_field_count": len(REQUIRED_REPLAY_FIELDS),
        "missing_required_fields": missing_fields,
        "file_access_log_ref": row.get("file_access_log_ref"),
        "contamination_check_ref": row.get("contamination_check_ref"),
        "trusted_reference_score_ref": row.get("trusted_reference_score_ref"),
        "source_artifact_evidence_refs": source_evidence_refs,
        "source_artifact_evidence_ref_count": len(source_evidence_refs),
        "source_artifact_evidence_verified": bool(source_evidence_refs)
        and not unknown_source_evidence_refs,
        "unknown_source_artifact_evidence_refs": unknown_source_evidence_refs,
        "real_benchmark_trace_ref": real_trace_ref,
        "real_benchmark_trace_material_class": real_trace_class,
        "real_benchmark_trace_artifact_status": real_trace_artifact_status,
        "real_benchmark_trace_verified": real_trace_verified,
        "real_session_integrity_evidence": real_session_evidence,
        "parsed_evidence_integrity": parsed_evidence,
        "body_in_receipt": False,
    }


def validate_replay_observations(
    payload: object,
    policy: object,
    benchmark_case_payload: object,
    negative_payloads: dict[str, object],
    *,
    source_artifact_classes: dict[str, str],
    source_artifact_statuses: dict[str, str],
    real_trace_evidence_by_ref: dict[str, dict[str, Any]],
    input_dir: Path,
    public_root: Path,
) -> dict[str, Any]:
    """
    [ACTION] Validate all replay observations and negative cases into rows, findings, and observed coverage codes.

    - Teleology: Makes the benchmark-integrity organ's validate_replay_observations stage
      inspectable as an explicit validation boundary, so source indexes, CodeMap nodes, and
      public receipts can route from the organ overview to this evidence check without private
      context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    policy_rows = policy if isinstance(policy, dict) else {}
    locked = set(_strings(policy_rows.get("locked_evaluator_ids")))
    locked_config_hashes = _locked_evaluator_config_hashes(policy_rows)
    known_case_ids = {
        str(row.get("case_id"))
        for row in _rows(benchmark_case_payload, "benchmark_cases")
        if row.get("case_id")
    }
    findings: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = defaultdict(set)
    rows: list[dict[str, Any]] = []
    for row in _rows(payload, "replay_observations"):
        rows.append(
            _validate_replay_row(
                row,
                locked_evaluators=locked,
                locked_evaluator_config_hashes=locked_config_hashes,
                known_case_ids=known_case_ids,
                source_artifact_classes=source_artifact_classes,
                source_artifact_statuses=source_artifact_statuses,
                real_trace_evidence_by_ref=real_trace_evidence_by_ref,
                input_dir=input_dir,
                public_root=public_root,
                findings=findings,
                observed=observed,
                negative=False,
            )
        )
    for payload in negative_payloads.values():
        negative_rows = _rows(payload, "replay_observations")
        if isinstance(payload, dict) and not negative_rows:
            negative_rows = [payload]
        for row in negative_rows:
            _validate_replay_row(
                row,
                locked_evaluators=locked,
                locked_evaluator_config_hashes=locked_config_hashes,
                known_case_ids=known_case_ids,
                source_artifact_classes=source_artifact_classes,
                source_artifact_statuses=source_artifact_statuses,
                real_trace_evidence_by_ref=real_trace_evidence_by_ref,
                input_dir=input_dir,
                public_root=public_root,
                findings=findings,
                observed=observed,
                negative=True,
            )
            expected_case_id = str(row.get("expected_negative_case_id") or "")
            semantic_case_id = _semantic_negative_case_id(row)
            if expected_case_id and semantic_case_id and expected_case_id != semantic_case_id:
                findings.append(
                    _finding(
                        "BENCHMARK_INTEGRITY_NEGATIVE_CASE_SEMANTIC_MISMATCH",
                        "Negative-case labels must match the row's semantic trigger; labels are not coverage authority.",
                        case_id=expected_case_id,
                        subject_id=str(row.get("replay_id") or row.get("case_id") or "negative_case"),
                        subject_kind="negative_case",
                    )
                )
            elif expected_case_id and not semantic_case_id and row.get("case_id") in known_case_ids:
                findings.append(
                    _finding(
                        "BENCHMARK_INTEGRITY_NEGATIVE_CASE_TRIGGER_MISSING",
                        "Negative-case fixtures must carry a semantic trigger, not only an expected_negative_case_id label.",
                        case_id=expected_case_id,
                        subject_id=str(row.get("replay_id") or row.get("case_id") or "negative_case"),
                        subject_kind="negative_case",
                    )
                )

    observed_case_ids = {row["case_id"] for row in rows if row["case_id"]}
    missing_replay_case_ids = sorted(known_case_ids - observed_case_ids)
    for missing_case_id in missing_replay_case_ids:
        findings.append(
            _finding(
                "BENCHMARK_INTEGRITY_CASE_REPLAY_MISSING",
                "Every benchmark case declared in benchmark_cases.json must have a replay observation row.",
                case_id="benchmark_case_replay_floor",
                subject_id=missing_case_id,
                subject_kind="benchmark_case",
            )
        )

    positive_floor_findings = [
        row
        for row in rows
        if row["computed_integrity_verdict"] == "quarantine"
        and row["integrity_verdict"] == "integrity_pass"
    ]
    invalid_positive_declared_verdicts = [
        row
        for row in rows
        if row["declared_integrity_verdict"]
        and row["declared_integrity_verdict_valid"] is False
    ]
    source_evidence_floor_findings = [
        row for row in rows if row["source_artifact_evidence_verified"] is not True
    ]
    real_trace_floor_findings = [
        row for row in rows if row["real_benchmark_trace_verified"] is not True
    ]
    return {
        "status": (
            PASS
            if rows
            and not missing_replay_case_ids
            and not positive_floor_findings
            and not invalid_positive_declared_verdicts
            and not source_evidence_floor_findings
            and not real_trace_floor_findings
            else "blocked"
        ),
        "replay_count": len(rows),
        "integrity_pass_count": sum(
            1 for row in rows if row["computed_integrity_verdict"] == "integrity_pass"
        ),
        "quarantine_count": sum(
            1 for row in rows if row["computed_integrity_verdict"] == "quarantine"
        ),
        "known_benchmark_case_ids": sorted(known_case_ids),
        "missing_replay_case_ids": missing_replay_case_ids,
        "source_artifact_evidence_ref_count": sum(
            len(row["source_artifact_evidence_refs"]) for row in rows
        ),
        "source_artifact_evidence_verified_count": sum(
            1 for row in rows if row["source_artifact_evidence_verified"] is True
        ),
        "real_benchmark_trace_verified_count": sum(
            1 for row in rows if row["real_benchmark_trace_verified"] is True
        ),
        "replay_rows": sorted(rows, key=lambda row: row["replay_id"]),
        "findings": findings,
        "observed_negative_cases": {key: sorted(value) for key, value in observed.items()},
    }


def _first_screen_integrity_rows(
    replay_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    [ACTION] Project replay rows into body-free first-screen integrity receipts.

    - Teleology: Projects benchmark-integrity results through _first_screen_integrity_rows into
      a human/agent start-here surface that preserves evidence handles without expanding full
      payload bodies.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic, receipt-safe summary structures whose counts and
      blocked-claim ids are derived from the result payload; source bodies, trace bodies, and
      private scans stay omitted.
    - Fails: Missing optional payload sections collapse to empty counts or False boundary flags;
      malformed required result shapes fail only when the existing projection code dereferences
      them.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    source_route = (
        "agent_benchmark_integrity_anti_gaming_replay.py::"
        "_validate_replay_row/validate_replay_observations"
    )
    ceiling = AUTHORITY_CEILING["authority_ceiling"]
    rows: list[dict[str, Any]] = []
    for row in sorted(
        replay_rows,
        key=lambda item: str(item.get("replay_id") or ""),
    ):
        computed_verdict = str(row.get("computed_integrity_verdict") or "")
        declared_verdict = str(row.get("declared_integrity_verdict") or "")
        reason_codes = _strings(row.get("reason_codes"))
        parsed_evidence = row.get("parsed_evidence_integrity")
        parsed = parsed_evidence if isinstance(parsed_evidence, dict) else {}
        real_session = row.get("real_session_integrity_evidence")
        session = real_session if isinstance(real_session, dict) else {}
        evidence_passes = (
            row.get("evaluator_config_hash_matches_policy") is True
            and row.get("source_artifact_evidence_verified") is True
            and row.get("real_benchmark_trace_verified") is True
            and parsed.get("evidence_passes") is True
            and session.get("session_evidence_passes") is True
        )
        rows.append(
            {
                "row_id": str(row.get("replay_id") or row.get("case_id") or "replay"),
                "source_route": source_route,
                "fixture_role": (
                    "quarantine_replay"
                    if computed_verdict == "quarantine" or reason_codes
                    else "integrity_pass_replay"
                ),
                "expected_status": computed_verdict,
                "observed_status": declared_verdict or computed_verdict,
                "evaluator_signal": evidence_passes
                and computed_verdict == declared_verdict,
                "case_id": str(row.get("case_id") or ""),
                "allowed_claim": (
                    "body-free replay evidence may support this row's computed "
                    "integrity_pass or quarantine verdict"
                ),
                "blocked_claims": list(BLOCKED_REPLAY_CLAIM_IDS),
                "proof_refs": {
                    "file_access_log_ref": row.get("file_access_log_ref"),
                    "contamination_check_ref": row.get("contamination_check_ref"),
                    "trusted_reference_score_ref": row.get("trusted_reference_score_ref"),
                    "real_benchmark_trace_ref": row.get("real_benchmark_trace_ref"),
                    "source_artifact_evidence_ref_count": row.get(
                        "source_artifact_evidence_ref_count"
                    ),
                },
                "proof_floor": {
                    "locked_evaluator_config_hash_matches_policy": row.get(
                        "evaluator_config_hash_matches_policy"
                    )
                    is True,
                    "source_artifact_evidence_verified": row.get(
                        "source_artifact_evidence_verified"
                    )
                    is True,
                    "real_benchmark_trace_verified": row.get(
                        "real_benchmark_trace_verified"
                    )
                    is True,
                    "parsed_evidence_passes": parsed.get("evidence_passes") is True,
                    "real_session_evidence_passes": session.get(
                        "session_evidence_passes"
                    )
                    is True,
                },
                "reason_codes": reason_codes,
                "downgrade_sentence": (
                    "This row proves a quarantine path fired, not a benchmark "
                    "capability score."
                    if computed_verdict == "quarantine" or reason_codes
                    else (
                        "This row proves replay-integrity evidence for a fixture "
                        "slice, not a benchmark score."
                    )
                ),
                "authority_ceiling": ceiling,
                "body_in_receipt": False,
            }
        )
    return rows


def validate_public_trace(
    public_trace: dict[str, Any],
    *,
    locked_evaluator_config_hashes: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    [ACTION] Fold recomputed public benchmark trace spans into organ-level findings.

    - Teleology: Makes the benchmark-integrity organ's validate_public_trace stage inspectable
      as an explicit validation boundary, so source indexes, CodeMap nodes, and public receipts
      can route from the organ overview to this evidence check without private context.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns a body-free validation packet with status, findings, observed
      negative-case coverage, and receipt-safe refs; it does not export private issue bodies,
      oracle patch bodies, provider payloads, hidden-gold material, or benchmark-score
      authority.
    - Fails: Malformed fixture content is downgraded into findings and blocked status where this
      validator owns the check; unrecoverable filesystem or JSON parse failures still propagate
      from the strict readers it calls.

    The macro builder recomputes each replay's integrity verdict from
    contamination, file-access, and locked-evaluator spans. Any
    computed-vs-declared mismatch becomes an organ finding.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """

    findings: list[dict[str, Any]] = []
    for span in public_trace.get("spans", []):
        if not isinstance(span, dict):
            continue
        replay_id = str(
            span.get("span_id", "").replace("span:", "") or "replay_observation"
        )
        target_refs = span.get("target_refs")
        evaluator_id = (
            str(target_refs[0])
            if isinstance(target_refs, list) and target_refs
            else str(span.get("target_ref") or "")
        )
        evaluator_config_hash = str(span.get("authority_verdict_id") or "")
        if span.get("integrity_verdict_matches_declared") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_BENCHMARK_INTEGRITY_VERDICT_MISMATCH",
                    "Recomputed integrity verdict from contamination, file-access, "
                    "and locked-evaluator spans does not match the declared verdict.",
                    case_id="public_trace_floor",
                    subject_id=replay_id,
                    subject_kind="public_agent_execution_trace",
                )
            )
        if locked_evaluator_config_hashes is not None:
            allowed_hashes = locked_evaluator_config_hashes.get(evaluator_id, [])
            if not evaluator_config_hash or evaluator_config_hash not in allowed_hashes:
                findings.append(
                    _finding(
                        "PUBLIC_TRACE_BENCHMARK_INTEGRITY_EVALUATOR_CONFIG_HASH_MISMATCH",
                        "Public trace span authority_verdict_id must match a policy-declared config hash for its locked evaluator.",
                        case_id="public_trace_floor",
                        subject_id=replay_id,
                        subject_kind="public_agent_execution_trace",
                    )
                )
        if span.get("evaluator_locked") is not True:
            findings.append(
                _finding(
                    "PUBLIC_TRACE_BENCHMARK_INTEGRITY_EVALUATOR_NOT_LOCKED",
                    "Replay observation must cite a locked, unmutated evaluator.",
                    case_id="public_trace_floor",
                    subject_id=replay_id,
                    subject_kind="public_agent_execution_trace",
                )
            )
    return {
        "status": PASS if public_trace.get("status") == PASS and not findings else "blocked",
        "findings": findings,
        "observed_negative_cases": {},
    }


def _public_trace_open_body_summary(public_trace: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION] Summarize whether the imported public trace builder body is present without exporting it in receipts.

    - Teleology: Keeps the replay-evidence accounting step _public_trace_open_body_summary
      explicit, so gaming-pattern decisions are traceable from row input to finding, reason
      code, and receipt field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    imported = public_trace.get("status") == PASS
    return {
        "schema_version": (
            "agent_benchmark_integrity_public_trace_open_body_v1"
        ),
        "status": str(public_trace.get("status") or ""),
        "body_material_status": (
            "public_agent_execution_trace_refactor_landed" if imported else "blocked"
        ),
        "body_material_count": int(public_trace.get("span_count") or 0),
        "body_material_ids": [PUBLIC_TRACE_OPEN_BODY_REF],
        "target_symbols": list(public_trace.get("target_symbols") or []),
        "trace_digest": (public_trace.get("summary") or {}).get("trace_digest"),
        "body_in_receipt": False,
        "reader_action": (
            "Open microcosm_core.macro_tools.agent_execution_trace::"
            "build_public_benchmark_integrity_anti_gaming_trace for the refactored "
            "body that recomputes each replay's integrity verdict from "
            "contamination, file-access, and locked-evaluator spans; receipts carry "
            "spans, digests, counts, and findings only."
        )
        if imported
        else "",
    }


def _build_result(
    input_dir: Path,
    *,
    command: str,
    input_mode: str,
    include_negative: bool,
) -> dict[str, Any]:
    """
    [ACTION] Assemble the full benchmark-integrity validation result from source, policy, replay, trace, and scan components.

    - Teleology: Keeps the replay-evidence accounting step _build_result explicit, so
      gaming-pattern decisions are traceable from row input to finding, reason code, and receipt
      field.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns body-free evidence summaries, finding rows, or merged coverage
      structures that preserve evaluator locks, trace refs, and negative-case semantics without
      carrying private/provider bodies.
    - Fails: Invalid replay semantics become findings where this helper records them; malformed
      artifacts or caller contract violations propagate rather than being converted into
      integrity_pass.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    public_root = _public_root_for_path(input_dir)
    payloads = _load_payloads(input_dir, include_negative=include_negative)
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    source_imports = validate_source_module_imports(input_dir, public_root=public_root)
    private_scan = scan_paths(
        [
            *_input_paths(input_dir, include_negative=include_negative),
            *_source_artifact_paths(input_dir, public_root=public_root),
        ],
        forbidden_classes=policy,
        display_root=public_root,
    )
    private_scan.pop("forbidden_output_fields", None)
    private_scan.pop("body_" + "redacted", None)
    private_scan["body_in_receipt"] = False
    private_scan["body_storage_policy"] = "body_free_regression_fixture"

    projection = validate_projection_protocol(payloads["projection_protocol"])
    evaluator_policy = validate_locked_evaluator_policy(payloads["locked_evaluator_policy"])
    benchmark_cases = validate_benchmark_cases(payloads["benchmark_cases"])
    source_artifact_classes = {
        row["target_ref"]: row["material_class"]
        for row in source_imports["modules"]
        if row["target_ref"]
    }
    source_artifact_statuses = {
        row["target_ref"]: (
            row["real_trace_artifact_status"]
            if row["material_class"] == REAL_BENCHMARK_TRACE_MATERIAL_CLASS
            else PASS
        )
        for row in source_imports["modules"]
        if row["target_ref"]
    }
    real_trace_evidence_by_ref = {
        row["target_ref"]: row["real_session_evidence"]
        for row in source_imports["modules"]
        if row["target_ref"]
        and row["material_class"] == REAL_BENCHMARK_TRACE_MATERIAL_CLASS
        and isinstance(row.get("real_session_evidence"), dict)
    }
    observations = validate_replay_observations(
        payloads["replay_observations"],
        payloads["locked_evaluator_policy"],
        payloads["benchmark_cases"],
        {
            name: payloads[name]
            for name in (Path(item).stem for item in NEGATIVE_INPUT_NAMES)
            if name in payloads
        },
        source_artifact_classes=source_artifact_classes,
        source_artifact_statuses=source_artifact_statuses,
        real_trace_evidence_by_ref=real_trace_evidence_by_ref,
        input_dir=input_dir,
        public_root=public_root,
    )
    first_screen_integrity_rows = _first_screen_integrity_rows(
        observations["replay_rows"]
    )
    public_trace = build_public_benchmark_integrity_anti_gaming_trace(input_dir)
    public_trace_validation = validate_public_trace(
        public_trace,
        locked_evaluator_config_hashes=evaluator_policy[
            "locked_evaluator_config_hashes"
        ],
    )
    public_trace_open_body = _public_trace_open_body_summary(public_trace)
    observed = _merge_observed(
        projection,
        evaluator_policy,
        benchmark_cases,
        observations,
        source_imports,
        public_trace_validation,
    )
    expected = EXPECTED_NEGATIVE_CASES if include_negative else {}
    missing = sorted(
        case_id
        for case_id, expected_codes in expected.items()
        if not set(expected_codes).issubset(set(observed.get(case_id, [])))
    )
    findings = _merge_findings(
        projection,
        evaluator_policy,
        benchmark_cases,
        observations,
        source_imports,
        public_trace_validation,
    )
    error_codes = sorted({str(row["error_code"]) for row in findings})
    bundle_manifest = payloads.get("bundle_manifest", {})
    source_open_body_imports = {
        "schema_version": "agent_benchmark_integrity_source_open_body_imports_v1",
        "status": source_imports["status"],
        "body_material_status": SOURCE_BODY_STATUS,
        "body_material_count": source_imports["module_count"],
        "body_material_ids": [
            row["module_id"] for row in source_imports["modules"] if row["module_id"]
        ],
        "material_classes": sorted(
            {
                row["material_class"]
                for row in source_imports["modules"]
                if row["material_class"]
            }
        ),
        "source_manifest_refs": [source_imports["source_module_manifest_ref"]],
        "aggregate_floor_ref": source_imports["source_module_manifest_ref"],
        "body_in_receipt": False,
        "reader_action": (
            "Open source_module_manifest.json and source_artifacts/ for copied "
            "macro pattern provenance bodies; receipts carry digests and status only."
        ),
    }
    status = (
        PASS
        if not missing
        and private_scan["blocking_hit_count"] == 0
        and projection["status"] == PASS
        and evaluator_policy["status"] == PASS
        and benchmark_cases["status"] == PASS
        and observations["status"] == PASS
        and source_imports["status"] == PASS
        and public_trace_validation["status"] == PASS
        else "blocked"
    )
    return {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_result_v1",
        "created_at": utc_now(),
        "status": status,
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "command": command,
        "input_mode": input_mode,
        "bundle_id": bundle_manifest.get("bundle_id") if isinstance(bundle_manifest, dict) else None,
        "expected_negative_cases": sorted(expected),
        "observed_negative_cases": observed,
        "missing_negative_cases": missing,
        "error_codes": error_codes,
        "findings": findings,
        "private_state_scan": private_scan,
        "public_agent_execution_trace": public_trace,
        "public_trace_open_body_imports": public_trace_open_body,
        "public_trace_span_count": public_trace.get("span_count"),
        "public_trace_integrity_pass_count": (public_trace.get("summary") or {}).get(
            "integrity_pass_count"
        ),
        "public_trace_quarantine_count": (public_trace.get("summary") or {}).get(
            "quarantine_count"
        ),
        "public_trace_finding_count": (public_trace.get("summary") or {}).get(
            "finding_count"
        ),
        "public_trace_status": public_trace.get("status"),
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": ANTI_CLAIM,
        "body_material_status": SOURCE_BODY_STATUS,
        "source_module_import_status": source_imports["status"],
        "source_module_manifest_ref": source_imports["source_module_manifest_ref"],
        "source_module_import_count": source_imports["module_count"],
        "copied_source_artifact_count": source_imports["copied_source_artifact_count"],
        "source_modules_pass": source_imports["status"] == PASS,
        "source_module_imports": source_imports["modules"],
        "source_open_body_imports": source_open_body_imports,
        "protocol_id": projection["protocol_id"],
        "source_refs": projection["source_refs"],
        "source_pattern_ids": projection["source_pattern_ids"],
        "projection_receipt_refs": projection["projection_receipt_refs"],
        "public_regression_fixture_refs": projection["public_regression_fixture_refs"],
        "locked_evaluator_ids": evaluator_policy["locked_evaluator_ids"],
        "locked_evaluator_config_hashes": evaluator_policy[
            "locked_evaluator_config_hashes"
        ],
        "locked_evaluator_config_hash_count": evaluator_policy[
            "locked_evaluator_config_hash_count"
        ],
        "benchmark_case_count": benchmark_cases["benchmark_case_count"],
        "known_benchmark_case_ids": observations["known_benchmark_case_ids"],
        "missing_replay_case_ids": observations["missing_replay_case_ids"],
        "source_artifact_evidence_ref_count": observations[
            "source_artifact_evidence_ref_count"
        ],
        "source_artifact_evidence_verified_count": observations[
            "source_artifact_evidence_verified_count"
        ],
        "real_benchmark_trace_verified_count": observations[
            "real_benchmark_trace_verified_count"
        ],
        "held_out_guard_count": benchmark_cases["held_out_guard_count"],
        "replay_count": observations["replay_count"],
        "integrity_pass_count": observations["integrity_pass_count"],
        "quarantine_count": observations["quarantine_count"],
        "benchmark_cases": benchmark_cases["benchmark_cases"],
        "replay_rows": observations["replay_rows"],
        "first_screen_integrity_rows": first_screen_integrity_rows,
    }


def _board_from_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION] Project the validation result into a compact board for human review.

    - Teleology: Projects benchmark-integrity results through _board_from_result into a
      human/agent start-here surface that preserves evidence handles without expanding full
      payload bodies.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic, receipt-safe summary structures whose counts and
      blocked-claim ids are derived from the result payload; source bodies, trace bodies, and
      private scans stay omitted.
    - Fails: Missing optional payload sections collapse to empty counts or False boundary flags;
      malformed required result shapes fail only when the existing projection code dereferences
      them.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_board_v1",
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "board_id": "agent_benchmark_integrity_anti_gaming_public_board",
        "input_mode": result["input_mode"],
        "source_pattern_ids": result["source_pattern_ids"],
        "mechanics": [
            {
                "mechanic_id": "locked_evaluator_before_score",
                "count": len(result["locked_evaluator_ids"]),
                "authority": "evaluator_identity_config_and_file_access_log_required",
            },
            {
                "mechanic_id": "locked_evaluator_config_hash_binding",
                "count": result["locked_evaluator_config_hash_count"],
                "authority": "replay_evaluator_config_hash_must_match_locked_policy_before_integrity_pass",
            },
            {
                "mechanic_id": "contamination_quarantine",
                "count": result["quarantine_count"],
                "authority": "hidden_gold_oracle_patch_and_train_test_leakage_reject_score_claim",
            },
            {
                "mechanic_id": "locked_case_roster_binding",
                "count": len(result["known_benchmark_case_ids"]),
                "authority": "replay_rows_must_bind_to_declared_benchmark_case_ids",
            },
            {
                "mechanic_id": "no_score_from_replay",
                "count": result["replay_count"],
                "authority": "synthetic_replay_is_integrity_evidence_not_benchmark_metric",
            },
            {
                "mechanic_id": "source_open_pattern_provenance_body_floor",
                "count": result["copied_source_artifact_count"],
                "authority": "copied_macro_pattern_bodies_are_verified_by_manifest_digest_without_exporting_benchmark_bodies",
            },
            {
                "mechanic_id": "replay_rows_bind_to_source_artifact_evidence",
                "count": result["source_artifact_evidence_verified_count"],
                "authority": "each replay row cites digest_verified_public_source_artifact_refs_from_the_manifest",
            },
            {
                "mechanic_id": "real_benchmark_trace_gate",
                "count": result["real_benchmark_trace_verified_count"],
                "authority": "each positive replay row must cite a manifest_verified_sanitized_real_command_run_trace_before_integrity_pass",
            },
            {
                "mechanic_id": "recomputed_integrity_verdict_matches_declared",
                "count": result["public_trace_span_count"],
                "authority": "integrity_verdict_is_recomputed_from_contamination_file_access_and_locked_evaluator_spans_not_echoed",
            },
        ],
        "known_benchmark_case_ids": result["known_benchmark_case_ids"],
        "missing_replay_case_ids": result["missing_replay_case_ids"],
        "benchmark_cases": result["benchmark_cases"],
        "replay_rows": result["replay_rows"],
        "first_screen_integrity_rows": result["first_screen_integrity_rows"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_imports": result["source_module_imports"],
        "source_open_body_imports": result["source_open_body_imports"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "public_trace_open_body_imports": result["public_trace_open_body_imports"],
        "body_in_receipt": False,
        "private_state_scan": result["private_state_scan"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
    }


def _write_receipts(
    result: dict[str, Any],
    out_dir: Path,
    *,
    acceptance_out: Path | None,
) -> dict[str, Any]:
    """
    [ACTION] Write result, board, validation, and optional acceptance receipts atomically.

    - Teleology: Owns the _write_receipts write path that turns validated benchmark-integrity
      evidence into durable local receipts or reusable bundle results.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Writes only governed JSON receipts/cards under the requested output path and
      preserves the organ authority ceiling: replay integrity evidence may pass or quarantine
      rows, but never becomes a benchmark score or release claim.
    - Fails: Invalid inputs surface through the underlying result builder as blocked findings;
      output-directory and atomic-write failures propagate so callers do not treat an unwritten
      receipt as evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    public_root = _public_root_for_path(out_dir)
    result_path = out_dir / RESULT_NAME
    board_path = out_dir / BOARD_NAME
    validation_path = out_dir / VALIDATION_RECEIPT_NAME
    acceptance_path = (
        acceptance_out
        if acceptance_out is not None
        else public_root / ACCEPTANCE_RECEIPT_REL
    )
    acceptance_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_paths = [
        _display(result_path, public_root=public_root),
        _display(board_path, public_root=public_root),
        _display(validation_path, public_root=public_root),
        _display(acceptance_path, public_root=public_root),
    ]
    result_receipt = {
        **result,
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_result_receipt_v1",
        "receipt_paths": receipt_paths,
    }
    board = {**_board_from_result(result), "receipt_paths": receipt_paths}
    validation = {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_validation_receipt_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "negative_case_coverage": {
            "expected": result["expected_negative_cases"],
            "observed": result["observed_negative_cases"],
            "missing": result["missing_negative_cases"],
        },
        "benchmark_case_count": result["benchmark_case_count"],
        "replay_count": result["replay_count"],
        "locked_evaluator_config_hash_count": result[
            "locked_evaluator_config_hash_count"
        ],
        "integrity_pass_count": result["integrity_pass_count"],
        "quarantine_count": result["quarantine_count"],
        "known_benchmark_case_ids": result["known_benchmark_case_ids"],
        "missing_replay_case_ids": result["missing_replay_case_ids"],
        "source_artifact_evidence_ref_count": result[
            "source_artifact_evidence_ref_count"
        ],
        "source_artifact_evidence_verified_count": result[
            "source_artifact_evidence_verified_count"
        ],
        "real_benchmark_trace_verified_count": result[
            "real_benchmark_trace_verified_count"
        ],
        "body_material_status": result["body_material_status"],
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_import_count": result["source_module_import_count"],
        "source_open_body_imports": result["source_open_body_imports"],
        "public_trace_span_count": result["public_trace_span_count"],
        "public_trace_integrity_pass_count": result[
            "public_trace_integrity_pass_count"
        ],
        "public_trace_quarantine_count": result["public_trace_quarantine_count"],
        "private_state_scan": result["private_state_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "public_trace_open_body_imports": result["public_trace_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    acceptance = {
        "schema_version": "agent_benchmark_integrity_anti_gaming_replay_fixture_acceptance_v1",
        "created_at": utc_now(),
        "status": result["status"],
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "accepted_negative_cases": result["expected_negative_cases"],
        "missing_negative_cases": result["missing_negative_cases"],
        "known_benchmark_case_ids": result["known_benchmark_case_ids"],
        "missing_replay_case_ids": result["missing_replay_case_ids"],
        "source_artifact_evidence_ref_count": result[
            "source_artifact_evidence_ref_count"
        ],
        "source_artifact_evidence_verified_count": result[
            "source_artifact_evidence_verified_count"
        ],
        "real_benchmark_trace_verified_count": result[
            "real_benchmark_trace_verified_count"
        ],
        "error_codes": result["error_codes"],
        "body_material_status": result["body_material_status"],
        "source_module_import_status": result["source_module_import_status"],
        "source_module_manifest_ref": result["source_module_manifest_ref"],
        "source_module_import_count": result["source_module_import_count"],
        "source_open_body_imports": result["source_open_body_imports"],
        "private_state_scan": result["private_state_scan"],
        "public_agent_execution_trace": result["public_agent_execution_trace"],
        "public_trace_open_body_imports": result["public_trace_open_body_imports"],
        "authority_ceiling": result["authority_ceiling"],
        "anti_claim": result["anti_claim"],
        "receipt_paths": receipt_paths,
    }
    write_json_atomic(result_path, result_receipt)
    write_json_atomic(board_path, board)
    write_json_atomic(validation_path, validation)
    write_json_atomic(acceptance_path, acceptance)
    return {**result, "benchmark_integrity_board": board, "receipt_paths": receipt_paths}


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str = "python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay run",
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    """
    [ACTION] Run the fixture validator and write benchmark-integrity receipts.

    - Teleology: Owns the run write path that turns validated benchmark-integrity evidence into
      durable local receipts or reusable bundle results.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Writes only governed JSON receipts/cards under the requested output path and
      preserves the organ authority ceiling: replay integrity evidence may pass or quarantine
      rows, but never becomes a benchmark score or release claim.
    - Fails: Invalid inputs surface through the underlying result builder as blocked findings;
      output-directory and atomic-write failures propagate so callers do not treat an unwritten
      receipt as evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    result = _build_result(
        Path(input_dir),
        command=command,
        input_mode="fixture",
        include_negative=True,
    )
    result["freshness_basis"] = _freshness_basis(Path(input_dir), include_negative=True)
    result["receipt_reused"] = False
    return _write_receipts(
        result,
        Path(out_dir),
        acceptance_out=Path(acceptance_out) if acceptance_out is not None else None,
    )


def run_benchmark_integrity_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    command: str = (
        "python -m microcosm_core.organs.agent_benchmark_integrity_anti_gaming_replay "
        "run-benchmark-integrity-bundle"
    ),
    *,
    reuse_fresh_receipt: bool = False,
) -> dict[str, Any]:
    """
    [ACTION] Run or reuse validation for an exported benchmark-integrity bundle.

    - Teleology: Owns the run_benchmark_integrity_bundle write path that turns validated
      benchmark-integrity evidence into durable local receipts or reusable bundle results.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Writes only governed JSON receipts/cards under the requested output path and
      preserves the organ authority ceiling: replay integrity evidence may pass or quarantine
      rows, but never becomes a benchmark score or release claim.
    - Fails: Invalid inputs surface through the underlying result builder as blocked findings;
      output-directory and atomic-write failures propagate so callers do not treat an unwritten
      receipt as evidence.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir)
    if reuse_fresh_receipt:
        cached = _fresh_bundle_receipt(source, out)
        if cached is not None:
            return cached
    result = _build_result(
        source,
        command=command,
        input_mode="exported_benchmark_integrity_bundle",
        include_negative=False,
    )
    result["freshness_basis"] = _freshness_basis(source, include_negative=False)
    result["receipt_reused"] = False
    bundle_path = out / BUNDLE_RESULT_NAME
    public_root = _public_root_for_path(out)
    payload = {
        **result,
        "schema_version": "exported_benchmark_integrity_bundle_validation_result_v1",
        "receipt_paths": [_display(bundle_path, public_root=public_root)],
    }
    write_json_atomic(bundle_path, payload)
    return payload


def result_card(result: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION] Project the result into the command-card shape with omitted payload boundaries.

    - Teleology: Projects benchmark-integrity results through result_card into a human/agent
      start-here surface that preserves evidence handles without expanding full payload bodies.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Returns deterministic, receipt-safe summary structures whose counts and
      blocked-claim ids are derived from the result payload; source bodies, trace bodies, and
      private scans stay omitted.
    - Fails: Missing optional payload sections collapse to empty counts or False boundary flags;
      malformed required result shapes fail only when the existing projection code dereferences
      them.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    freshness_basis = result.get("freshness_basis")
    freshness = freshness_basis if isinstance(freshness_basis, dict) else {}
    private_scan = result.get("private_state_scan")
    scan = private_scan if isinstance(private_scan, dict) else {}
    return {
        "schema_version": CARD_SCHEMA_VERSION,
        "status": result.get("status"),
        "organ_id": result.get("organ_id"),
        "input_mode": result.get("input_mode"),
        "bundle_id": result.get("bundle_id"),
        "command_speed": {
            "receipt_reused": result.get("receipt_reused") is True,
            "freshness_digest": freshness.get("basis_digest"),
            "freshness_input_count": freshness.get("input_count"),
            "freshness_missing_path_count": freshness.get("missing_path_count"),
        },
        "benchmark_integrity": {
            "benchmark_case_count": result.get("benchmark_case_count"),
            "held_out_guard_count": result.get("held_out_guard_count"),
            "known_benchmark_case_count": len(
                result.get("known_benchmark_case_ids") or []
            ),
            "missing_replay_case_count": len(
                result.get("missing_replay_case_ids") or []
            ),
            "replay_count": result.get("replay_count"),
            "locked_evaluator_config_hash_count": result.get(
                "locked_evaluator_config_hash_count"
            ),
            "integrity_pass_count": result.get("integrity_pass_count"),
            "quarantine_count": result.get("quarantine_count"),
            "source_artifact_evidence_ref_count": result.get(
                "source_artifact_evidence_ref_count"
            ),
            "source_artifact_evidence_verified_count": result.get(
                "source_artifact_evidence_verified_count"
            ),
            "real_benchmark_trace_verified_count": result.get(
                "real_benchmark_trace_verified_count"
            ),
            "source_module_import_status": result.get(
                "source_module_import_status"
            ),
            "source_module_import_count": result.get("source_module_import_count"),
            "copied_source_artifact_count": result.get(
                "copied_source_artifact_count"
            ),
            "body_material_status": result.get("body_material_status"),
            "source_modules_pass": result.get("source_modules_pass") is True,
        },
        "first_screen": {
            "integrity_row_count": len(
                result.get("first_screen_integrity_rows") or []
            ),
            "integrity_row_ids": [
                str(row.get("row_id"))
                for row in result.get("first_screen_integrity_rows") or []
                if isinstance(row, dict) and row.get("row_id")
            ],
            "blocked_claim_ids": list(BLOCKED_REPLAY_CLAIM_IDS),
            "body_in_receipt": False,
        },
        "public_trace": {
            "span_count": result.get("public_trace_span_count"),
            "integrity_pass_count": result.get("public_trace_integrity_pass_count"),
            "quarantine_count": result.get("public_trace_quarantine_count"),
            "finding_count": result.get("public_trace_finding_count"),
            "public_trace_status": result.get("public_trace_status"),
        },
        "validation": {
            "expected_negative_case_count": len(
                result.get("expected_negative_cases") or []
            ),
            "missing_negative_case_count": len(
                result.get("missing_negative_cases") or []
            ),
            "error_code_count": len(result.get("error_codes") or []),
            "finding_count": len(result.get("findings") or []),
            "private_state_blocking_hit_count": scan.get("blocking_hit_count"),
            "source_module_manifest_ref": result.get("source_module_manifest_ref"),
        },
        "body_floor": {
            "body_in_receipt": False,
            "private_state_scan_in_card": False,
            "source_module_imports_in_card": False,
            "source_open_body_imports_in_card": False,
            "public_agent_execution_trace_in_card": False,
        },
        "authority_boundary": {
            "benchmark_score_claim_authorized": False,
            "swe_bench_performance_claim_authorized": False,
            "hidden_gold_access_authorized": False,
            "oracle_patch_body_export_authorized": False,
            "private_issue_body_export_authorized": False,
            "provider_calls_authorized": False,
            "live_repo_mutation_authorized": False,
            "release_authorized": False,
        },
        "receipt_paths": _card_receipt_paths(result),
        "omission_receipt": {
            "omitted_full_payload_keys": list(CARD_OMITTED_FULL_PAYLOAD_KEYS),
            "full_payload_drilldown": "rerun without --card or inspect the written receipt file",
        },
    }


def _parser() -> argparse.ArgumentParser:
    """
    [ACTION] Build the CLI parser for benchmark-integrity replay commands.

    - Teleology: Keeps the command-line entry surface aligned with the organ's two supported
      operations: fixture replay validation and exported-bundle validation.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Constructs or dispatches only declared arguments and returns process status
      from the selected operation; --card remains a projection over the written/result payload,
      not a separate authority source.
    - Fails: Argparse rejects invalid command shapes before execution; validation, IO, and JSON
      failures propagate from the selected runner instead of being hidden as success.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(prog="agent_benchmark_integrity_anti_gaming_replay")
    sub = parser.add_subparsers(dest="action", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--acceptance-out")
    run_parser.add_argument("--card", action="store_true")
    bundle_parser = sub.add_parser("run-benchmark-integrity-bundle")
    bundle_parser.add_argument("--input", required=True)
    bundle_parser.add_argument("--out", required=True)
    bundle_parser.add_argument("--card", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION] Dispatch CLI arguments to benchmark-integrity run and bundle commands.

    - Teleology: Keeps the command-line entry surface aligned with the organ's two supported
      operations: fixture replay validation and exported-bundle validation.
    - Preconditions: Caller supplies the benchmark-integrity fixture or bundle shape described by this module, with public-root refs and JSON payloads already selected by the run path.
    - Guarantee: Constructs or dispatches only declared arguments and returns process status
      from the selected operation; --card remains a projection over the written/result payload,
      not a separate authority source.
    - Fails: Argparse rejects invalid command shapes before execution; validation, IO, and JSON
      failures propagate from the selected runner instead of being hidden as success.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = _parser().parse_args(argv)
    card_suffix = " --card" if args.card else ""
    if args.action == "run":
        acceptance_suffix = (
            f" --acceptance-out {args.acceptance_out}" if args.acceptance_out else ""
        )
        command = (
            "python -m microcosm_core.organs."
            "agent_benchmark_integrity_anti_gaming_replay "
            f"run --input {args.input} --out {args.out}{acceptance_suffix}"
            f"{card_suffix}"
        )
        result = run(
            args.input,
            args.out,
            command=command,
            acceptance_out=args.acceptance_out,
        )
    elif args.action == "run-benchmark-integrity-bundle":
        command = (
            "python -m microcosm_core.organs."
            "agent_benchmark_integrity_anti_gaming_replay "
            f"run-benchmark-integrity-bundle --input {args.input} --out {args.out}"
            f"{card_suffix}"
        )
        result = run_benchmark_integrity_bundle(
            args.input,
            args.out,
            command=command,
            reuse_fresh_receipt=args.card,
        )
    else:  # pragma: no cover
        raise ValueError(args.action)
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(result["status"])
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
