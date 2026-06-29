"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.receipts` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: AUTHORITY_CEILING, PUBLIC_PATH_POLICY_ID, PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA, ANTI_CLAIM, FALSE_ENV_VALUES, TRUE_ENV_VALUES, PACKAGE_ROOT, TRACKED_RECEIPTS_ROOT, PRIVATE_REPO_HOME_RE, PRIVATE_HOME_RE, PRIVATE_TMP_RE, REPO_ROOT_FRAGMENT_RE, utc_now, receipt_writes_enabled, tracked_receipt_writes_enabled, is_tracked_receipt_path, tracked_receipt_write_blocked_under_pytest, tracked_receipt_write_blocked, normalize_public_receipt_paths, write_json_atomic, write_local_state_json_atomic, base_receipt, write_receipt
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, environment variables.
- Writes: return values, declared filesystem outputs and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.schemas
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from microcosm_core.schemas import StrictJsonError, read_json_strict


AUTHORITY_CEILING = "command_receipt_evidence_not_runtime_product_completeness"
PUBLIC_PATH_POLICY_ID = "microcosm_public_path_secret_policy_v1"
PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA = (
    "microcosm_public_receipt_path_normalization_v1"
)
ANTI_CLAIM = (
    "This receipt records the named public command output over real public inputs, "
    "source-faithful fixtures, or explicit negative cases; synthetic receipts are "
    "not product progress or substitutes for available real substrate."
)
FALSE_ENV_VALUES = {"0", "false", "no", "off"}
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TRACKED_RECEIPTS_ROOT = (PACKAGE_ROOT / "receipts").resolve(strict=False)
PRIVATE_REPO_HOME_RE = re.compile(
    r"/Users/[^/\s\"']+/src/ai_workflow(?P<suffix>[^\s\"']*)"
)
PRIVATE_HOME_RE = re.compile(r"/Users/[^/\s\"']+(?P<suffix>[^\s\"']*)")
PRIVATE_TMP_RE = re.compile(r"/private/tmp(?P<suffix>[^\s\"']*)")
REPO_ROOT_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])src/ai_workflow(?P<suffix>[^\s\"']*)"
)


def _normalize_env_flag(value: str) -> str:
    """
    [ACTION]
    Canonicalize an env-var string for truthiness comparison.

    - Teleology: single chokepoint so receipt-write gate flags compare case/whitespace-insensitively against FALSE_ENV_VALUES / TRUE_ENV_VALUES.
    - Guarantee: returns the input stripped of surrounding whitespace and lowercased; no other transform.
    - Fails: never raises for str input; raises AttributeError if value is not a str.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return value.strip().lower()


def utc_now() -> str:
    """
    [ACTION]
    Produce the canonical receipt timestamp string.

    - Teleology: every receipt's created_at is stamped here so timestamps are uniform UTC and second-granular across all organ receipts.
    - Guarantee: returns an ISO-8601 string in UTC with microseconds zeroed and a +00:00 offset (e.g. "2026-06-08T12:00:00+00:00").
    - Fails: never raises; depends only on the system clock.
    - When-needed: inspect when receipt timestamps look non-UTC, sub-second, or non-deterministic.
    - Escalates-to: _payload_with_stable_created_at (which suppresses spurious created_at churn) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def receipt_writes_enabled() -> bool:
    """
    [ACTION]
    Decide whether receipt writes are permitted in this process.

    - Teleology: the master kill-switch letting callers (e.g. read-only CLI/test runs) suppress all receipt-file emission without code changes.
    - Guarantee: returns True unless MICROCOSM_RECEIPT_WRITES (or, when unset, MICROCOSM_RUNTIME_RECEIPT_WRITES) is set to a false value (0/false/no/off); default is enabled.
    - Fails: never raises; absent env vars default to enabled ("1").
    - When-needed: inspect when expected receipt files are missing or unexpectedly written.
    - Reads: env MICROCOSM_RECEIPT_WRITES, env MICROCOSM_RUNTIME_RECEIPT_WRITES.
    - Non-goal: does not authorize release, source-body export, or treat receipt emission as product completeness.
    - Escalates-to: write_json_atomic (the gate's consumer) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    value = os.environ.get("MICROCOSM_RECEIPT_WRITES")
    if value is None:
        value = os.environ.get("MICROCOSM_RUNTIME_RECEIPT_WRITES", "1")
    return _normalize_env_flag(value) not in FALSE_ENV_VALUES


def _env_flag_true(name: str) -> bool:
    """
    [ACTION]
    Test whether a named env var is explicitly set to a true value.

    - Teleology: strict opt-in primitive (unset == false) for guards like tracked-receipt writes that must default closed.
    - Guarantee: returns True only when os.environ[name] is present and normalizes to a member of TRUE_ENV_VALUES (1/true/yes/on); unset or any other value returns False.
    - Fails: never raises; missing env var returns False.
    - Reads: env <name>.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    value = os.environ.get(name)
    return value is not None and _normalize_env_flag(value) in TRUE_ENV_VALUES


def tracked_receipt_writes_enabled() -> bool:
    """
    [ACTION]
    Decide whether writes into the version-tracked receipts/ tree are allowed.

    - Teleology: protects the committed receipts/ corpus from incidental churn; tracked writes are opt-in only.
    - Guarantee: returns True only when MICROCOSM_TRACKED_RECEIPT_WRITES is explicitly set to a true value; default False.
    - Fails: never raises; absent env var returns False (tracked writes blocked).
    - Reads: env MICROCOSM_TRACKED_RECEIPT_WRITES.
    - Non-goal: does not authorize release or treat a tracked receipt as source-of-truth authority.
    - Escalates-to: tracked_receipt_write_blocked and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return _env_flag_true("MICROCOSM_TRACKED_RECEIPT_WRITES")


def _lexical_absolute(path: str | Path) -> Path:
    """
    [ACTION]
    Absolutize a path lexically without touching the filesystem.

    - Teleology: tracked-path containment checks must not follow symlinks or require the path to exist, so normalization stays purely textual.
    - Guarantee: returns an absolute Path computed via os.path.abspath (lexical .. collapse, cwd-anchored); no stat/symlink resolution.
    - Fails: never raises for str/PathLike input; raises TypeError for non-path-like input.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return Path(os.path.abspath(os.fspath(path)))


def _path_is_relative_to(path: Path, root: Path) -> bool:
    """
    [ACTION]
    Test path-under-root containment, Python-3.8-compatible.

    - Teleology: backport of Path.is_relative_to so tracked-receipt containment logic runs on older interpreters.
    - Guarantee: returns True iff path is lexically inside root (path.relative_to(root) succeeds); False otherwise.
    - Fails: never raises; the ValueError from a non-containing relative_to is caught and mapped to False.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_tracked_receipt_path(path: str | Path) -> bool:
    """
    [ACTION]
    Classify whether a target path lands inside the tracked receipts/ tree.

    - Teleology: the custody predicate that distinguishes the committed receipts/ corpus from scratch/local-state paths so writes there can be gated.
    - Guarantee: returns True iff path is contained in TRACKED_RECEIPTS_ROOT under either a lexical-absolute check or a parent-resolved (symlink-aware on the directory) check; False otherwise.
    - Fails: never raises for str/PathLike input; surfaces OSError only if parent.resolve hits an unrecoverable filesystem error.
    - When-needed: inspect when a write is unexpectedly blocked/allowed or symlinked receipt dirs misclassify.
    - Reads: TRACKED_RECEIPTS_ROOT (PACKAGE_ROOT / "receipts").
    - Non-goal: does not authorize the write; only classifies custody. Release/export authority is elsewhere.
    - Escalates-to: tracked_receipt_write_blocked and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    tracked_root = _lexical_absolute(TRACKED_RECEIPTS_ROOT)
    candidate = _lexical_absolute(path)
    if _path_is_relative_to(candidate, tracked_root):
        return True

    raw_path = Path(path).expanduser()
    parent_resolved_candidate = raw_path.parent.resolve(strict=False) / raw_path.name
    return _path_is_relative_to(
        parent_resolved_candidate,
        Path(TRACKED_RECEIPTS_ROOT).resolve(strict=False),
    )


def tracked_receipt_write_blocked_under_pytest(path: str | Path) -> bool:
    """
    [ACTION]
    Detect a tracked-receipt write attempted from within a pytest run.

    - Teleology: lets the suite assert that tests never mutate the committed receipts/ corpus, regardless of the env opt-in flag.
    - Guarantee: returns True iff PYTEST_CURRENT_TEST is in the environment AND path is a tracked-receipt path; False otherwise.
    - Fails: never raises for str/PathLike input; inherits is_tracked_receipt_path's OSError surface.
    - Reads: env PYTEST_CURRENT_TEST, TRACKED_RECEIPTS_ROOT.
    - Escalates-to: tests/test_receipts.py (the surface that exercises this guard).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return "PYTEST_CURRENT_TEST" in os.environ and is_tracked_receipt_path(path)


def tracked_receipt_write_blocked(path: str | Path) -> bool:
    """
    [ACTION]
    Decide whether a write to a tracked-receipt path must be suppressed.

    - Teleology: the enforcement predicate every atomic-write entrypoint consults to keep the committed receipts/ tree opt-in.
    - Guarantee: returns True iff path is a tracked-receipt path AND tracked writes are not enabled; a non-tracked path or enabled flag returns False.
    - Fails: never raises for str/PathLike input; inherits is_tracked_receipt_path's OSError surface.
    - When-needed: inspect when a receipt write into receipts/ silently no-ops.
    - Reads: TRACKED_RECEIPTS_ROOT, env MICROCOSM_TRACKED_RECEIPT_WRITES.
    - Escalates-to: write_json_atomic / write_local_state_json_atomic (callers) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    return is_tracked_receipt_path(path) and not tracked_receipt_writes_enabled()


def _read_json_object_if_exists(path: Path) -> dict[str, Any]:
    """
    [ACTION]
    Best-effort load of an existing receipt as a JSON object.

    - Teleology: supports stable-created_at diffing by reading the prior on-disk receipt without making absence or corruption fatal.
    - Guarantee: returns the parsed dict when path holds a strict JSON object; returns {} when the file is missing, unreadable, invalid JSON, or a non-object top-level value.
    - Fails: never raises; FileNotFoundError / StrictJsonError / OSError are caught and mapped to {}.
    - Reads: <path> (an existing receipt JSON file), via read_json_strict.
    - Escalates-to: microcosm_core.schemas.read_json_strict (the strict parser) and _payload_with_stable_created_at (sole caller).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    try:
        data = read_json_strict(path)
    except (FileNotFoundError, StrictJsonError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _sha256_text(value: str) -> str:
    """
    [ACTION]
    Hash a string into a prefixed SHA-256 digest for receipt evidence.

    - Teleology: lets the path-normalization ledger record an original private string only as a one-way digest, never as recoverable plaintext.
    - Guarantee: returns "sha256:" + the hex SHA-256 of value's UTF-8 bytes (undecodable bytes replaced); deterministic for equal inputs.
    - Fails: never raises for str input; raises AttributeError if value is not a str.
    - Non-goal: does not authorize re-emitting the original string; the digest is the only public-safe residue.
    - Escalates-to: _replacement_row / normalize_public_receipt_paths (consumers of the digest).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _replacement_row(
    *,
    original: str,
    replacement: str,
    treatment_class: str,
    field_path: str,
) -> dict[str, str]:
    """
    [ACTION]
    Build one audit row for the public-path substitution ledger.

    - Teleology: each private path that was rewritten leaves a structured, public-safe trace (hashed original, replacement token, treatment class, field path).
    - Guarantee: returns a 4-key dict {original_sha256, replacement, treatment_class, field_path} where original_sha256 is the digest of `original` (never the plaintext).
    - Fails: never raises for str inputs; inherits _sha256_text's AttributeError on non-str original.
    - Non-goal: does not authorize recovering the original string; only the digest is retained.
    - Escalates-to: normalize_public_receipt_paths (which aggregates rows into public_path_sanitization).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "original_sha256": _sha256_text(original),
        "replacement": replacement,
        "treatment_class": treatment_class,
        "field_path": field_path,
    }


def _normalize_public_receipt_string(
    value: str, *, field_path: str, replacements: list[dict[str, str]]
) -> str:
    """
    [ACTION]
    Rewrite host-local path fragments inside one receipt string.

    - Teleology: the leaf transform that strips private home roots, host temp roots, and the macro repo's host-local path fragment from a single string while logging each swap.
    - Guarantee: returns value with PRIVATE_REPO_HOME_RE / PRIVATE_HOME_RE / PRIVATE_TMP_RE / REPO_ROOT_FRAGMENT_RE matches replaced by <repo-root>/<private-home-path>/<host-temp> tokens; every replacement appends a row to `replacements` (mutated in place).
    - Fails: never raises for str input; raises AttributeError if value is not a str.
    - Reads: the four module-level private-path regexes.
    - Non-goal: does not guarantee exhaustive de-identification beyond these four patterns; it is not a full secret scanner.
    - Escalates-to: _normalize_public_receipt_value (recursive caller) and normalize_public_receipt_paths (public entrypoint).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """

    def repo_home_repl(match: re.Match[str]) -> str:
        """
        [ACTION]
        - Teleology: Implements `_normalize_public_receipt_string.repo_home_repl` for `microcosm_core.receipts` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        suffix = match.group("suffix") or ""
        replacement = f"<repo-root>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="repo_root_private_home_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def private_home_repl(match: re.Match[str]) -> str:
        """
        [ACTION]
        - Teleology: Implements `_normalize_public_receipt_string.private_home_repl` for `microcosm_core.receipts` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        replacement = "<private-home-path>"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="private_home_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def private_tmp_repl(match: re.Match[str]) -> str:
        """
        [ACTION]
        - Teleology: Implements `_normalize_public_receipt_string.private_tmp_repl` for `microcosm_core.receipts` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        suffix = match.group("suffix") or ""
        replacement = f"<host-temp>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="host_temp_path_transform",
                field_path=field_path,
            )
        )
        return replacement

    def repo_fragment_repl(match: re.Match[str]) -> str:
        """
        [ACTION]
        - Teleology: Implements `_normalize_public_receipt_string.repo_fragment_repl` for `microcosm_core.receipts` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        suffix = match.group("suffix") or ""
        replacement = f"<repo-root>{suffix}"
        replacements.append(
            _replacement_row(
                original=match.group(0),
                replacement=replacement,
                treatment_class="repo_root_fragment_transform",
                field_path=field_path,
            )
        )
        return replacement

    normalized = PRIVATE_REPO_HOME_RE.sub(repo_home_repl, value)
    normalized = PRIVATE_HOME_RE.sub(private_home_repl, normalized)
    normalized = PRIVATE_TMP_RE.sub(private_tmp_repl, normalized)
    return REPO_ROOT_FRAGMENT_RE.sub(repo_fragment_repl, normalized)


def _normalize_public_receipt_value(
    value: Any, *, field_path: str, replacements: list[dict[str, str]]
) -> Any:
    """
    [ACTION]
    Recursively normalize private paths through an arbitrary receipt value.

    - Teleology: walks the whole receipt tree so path sanitization reaches strings nested inside lists, tuples, and dicts at any depth.
    - Guarantee: returns a structurally equivalent value with every contained string normalized; lists and tuples both yield lists; the reserved "public_path_sanitization" key is dropped from dicts; non-str/list/tuple/dict scalars pass through unchanged. Replacement rows accumulate in `replacements`.
    - Fails: never raises for JSON-shaped values; deep structures may hit recursion limits (RecursionError).
    - Non-goal: does not validate the payload schema or guarantee de-identification beyond the string-level patterns.
    - Escalates-to: _normalize_public_receipt_string (leaf transform) and normalize_public_receipt_paths (entrypoint).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if isinstance(value, str):
        return _normalize_public_receipt_string(
            value, field_path=field_path, replacements=replacements
        )
    if isinstance(value, list):
        return [
            _normalize_public_receipt_value(
                item, field_path=f"{field_path}[{index}]", replacements=replacements
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return [
            _normalize_public_receipt_value(
                item, field_path=f"{field_path}[{index}]", replacements=replacements
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        return {
            key: _normalize_public_receipt_value(
                item,
                field_path=f"{field_path}.{key}" if field_path else str(key),
                replacements=replacements,
            )
            for key, item in value.items()
            if key != "public_path_sanitization"
        }
    return value


def normalize_public_receipt_paths(payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Return a receipt payload with host-local path strings made portable.

    Public receipts can preserve provenance shape, command intent, and artifact
    names without re-emitting private home roots, private temp roots, or the
    macro repo's host-local path fragment. Original strings are recorded only as
    hashes plus treatment classes so future builders can audit the transform.

    - Teleology: the public-safe boundary applied to every receipt before write, turning host-local path strings into portable tokens with an auditable substitution ledger.
    - Guarantee: returns the payload unchanged when nothing matched; otherwise returns a copy with all private path strings normalized and a "public_path_sanitization" block (schema PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA, policy PUBLIC_PATH_POLICY_ID, status "transformed", replacement_count, sorted transform_classes, hashed replacements, body_text_boundary). Original plaintext is never re-emitted.
    - Fails: never raises for dict payloads; returns the (possibly non-dict) normalized value as-is when normalization did not yield a dict or produced no replacements.
    - When-needed: inspect before trusting any receipt as public-safe, or when a private path leaks into emitted JSON.
    - Reads: PUBLIC_PATH_POLICY_ID, PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA, the four private-path regexes.
    - Non-goal: does not authorize release/publication and is not a full secret scanner; it sanitizes the four known private-path shapes only.
    - Escalates-to: secret_exclusion_scan.py / private_state_scan.py (stronger leak gates), policy id microcosm_public_path_secret_policy_v1, and tests/test_proof_lab_public_path_boundary.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """

    replacements: list[dict[str, str]] = []
    normalized = _normalize_public_receipt_value(
        payload, field_path="", replacements=replacements
    )
    if not isinstance(normalized, dict) or not replacements:
        return normalized

    normalized["public_path_sanitization"] = {
        "schema_version": PUBLIC_RECEIPT_PATH_NORMALIZATION_SCHEMA,
        "policy_id": PUBLIC_PATH_POLICY_ID,
        "status": "transformed",
        "replacement_count": len(replacements),
        "transform_classes": sorted({row["treatment_class"] for row in replacements}),
        "replacements": replacements,
        "body_text_boundary": (
            "Receipt path normalization records hashed originals, replacements, "
            "field paths, and treatment classes only; private host path strings "
            "are not public receipt evidence."
        ),
    }
    return normalized


def _payload_with_stable_created_at(
    path: Path, payload: dict[str, Any]
) -> dict[str, Any]:
    """
    [ACTION]
    Preserve a prior created_at when only the timestamp would change.

    - Teleology: keeps committed receipts byte-stable across reruns so an unchanged command does not produce a churning timestamp-only diff.
    - Guarantee: returns a copy whose created_at is the prior on-disk created_at iff both the new and previous payloads carry str created_at values AND are otherwise field-identical; otherwise returns the payload unchanged.
    - Fails: never raises; a missing/unreadable prior file (via _read_json_object_if_exists) yields the payload unchanged.
    - Reads: <path> (the existing receipt) to compare prior content.
    - Escalates-to: _write_json_atomic_unchecked (sole caller) and utc_now (the timestamp source it stabilizes).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Writes: return values.
    """
    created_at = payload.get("created_at")
    if not isinstance(created_at, str):
        return payload

    previous = _read_json_object_if_exists(path)
    previous_created_at = previous.get("created_at")
    if not isinstance(previous_created_at, str):
        return payload

    previous_without_created_at = dict(previous)
    previous_without_created_at.pop("created_at", None)
    payload_without_created_at = dict(payload)
    payload_without_created_at.pop("created_at", None)
    if previous_without_created_at != payload_without_created_at:
        return payload

    stable_payload = dict(payload)
    stable_payload["created_at"] = previous_created_at
    return stable_payload


def _write_json_atomic_unchecked(path: str | Path, payload: dict[str, Any]) -> None:
    """
    [ACTION]
    Atomically write a sanitized receipt JSON, bypassing write gates.

    - Teleology: the single low-level writer that applies path normalization + created_at stabilization and commits via tmpfile+os.replace so readers never see a torn file.
    - Guarantee: on success, target holds the public-path-normalized, created_at-stabilized payload as sorted-key, ASCII, 2-space-indented JSON with a trailing newline, written atomically (no partial file).
    - Fails: on any write/serialization error the temp file is unlinked and the original exception re-raises; OSError if the parent dir cannot be created.
    - Writes: <path> (the receipt JSON artifact).
    - Non-goal: does NOT consult receipt_writes_enabled / tracked_receipt_write_blocked — callers must gate; this is the unchecked primitive.
    - Escalates-to: write_json_atomic / write_local_state_json_atomic (the gated wrappers) and normalize_public_receipt_paths (the sanitizer it applies).
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    """
    target = Path(path)
    payload_to_write = _payload_with_stable_created_at(
        target, normalize_public_receipt_paths(payload)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{target.name}.", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload_to_write, fh, ensure_ascii=True, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_name, target)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    """
    [ACTION]
    Gated atomic receipt write — the public write entrypoint.

    - Teleology: the default receipt sink that honours both the global writes kill-switch and the tracked-tree opt-in before delegating to the atomic primitive.
    - Guarantee: writes the sanitized payload to path iff receipt writes are enabled AND the path is not a blocked tracked-receipt path; otherwise it is a silent no-op (file untouched).
    - Fails: never raises when gates suppress the write; otherwise inherits _write_json_atomic_unchecked's OSError / serialization failures.
    - When-needed: inspect when an organ receipt is unexpectedly absent or present.
    - Reads: env MICROCOSM_RECEIPT_WRITES, TRACKED_RECEIPTS_ROOT.
    - Writes: <path> (when permitted).
    - Non-goal: does not authorize release; a written receipt is command-output evidence, not runtime-product completeness (AUTHORITY_CEILING).
    - Escalates-to: write_receipt (the wrapper that also returns the payload) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    target = Path(path)
    if not receipt_writes_enabled() or tracked_receipt_write_blocked(target):
        return
    _write_json_atomic_unchecked(target, payload)


def write_local_state_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    """
    [ACTION]
    Atomic write for local-state JSON, gated only on the tracked-tree opt-in.

    - Teleology: persists local/generated state that must survive even when receipt writes are globally disabled, while still protecting the committed receipts/ tree.
    - Guarantee: writes the sanitized payload to path iff the path is not a blocked tracked-receipt path; the global receipt_writes_enabled kill-switch is intentionally NOT consulted.
    - Fails: never raises when the tracked-tree gate suppresses the write; otherwise inherits _write_json_atomic_unchecked's OSError / serialization failures.
    - Reads: TRACKED_RECEIPTS_ROOT, env MICROCOSM_TRACKED_RECEIPT_WRITES.
    - Writes: <path> (when not a blocked tracked path).
    - Non-goal: does not authorize release or treat local state as source-of-truth authority.
    - Escalates-to: _write_json_atomic_unchecked (the primitive) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    """
    target = Path(path)
    if tracked_receipt_write_blocked(target):
        return
    _write_json_atomic_unchecked(target, payload)


def base_receipt(organ_id: str, fixture_id: str, command: str | None = None) -> dict[str, Any]:
    """
    [ACTION]
    Construct the canonical skeleton every organ receipt starts from.

    - Teleology: one factory so all receipts share schema/id shape, the standing anti-claim, the authority ceiling, and a default not-run secret scan — preventing per-organ drift in the custody envelope.
    - Guarantee: returns a dict carrying schema_version/receipt_id "{organ_id}_receipt_v1", organ_id, fixture_id, a fresh utc_now created_at, status "pending", the command, ANTI_CLAIM, secret_exclusion_scan {"status":"not_run"}, AUTHORITY_CEILING, and empty receipt_paths.
    - Fails: never raises; command defaults to None.
    - When-needed: inspect when a receipt is missing the anti-claim, authority ceiling, or has an unexpected schema_version.
    - Non-goal: the returned receipt is evidence of a command run, NOT proof of product completeness or release authorization (authority_ceiling = command_receipt_evidence_not_runtime_product_completeness); status is "pending" until the organ finalizes it.
    - Escalates-to: write_receipt (which persists it) and the per-organ runner that fills status/receipt_paths.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "schema_version": f"{organ_id}_receipt_v1",
        "receipt_id": f"{organ_id}_receipt_v1",
        "organ_id": organ_id,
        "fixture_id": fixture_id,
        "created_at": utc_now(),
        "status": "pending",
        "command": command,
        "anti_claim": ANTI_CLAIM,
        "secret_exclusion_scan": {"status": "not_run"},
        "authority_ceiling": AUTHORITY_CEILING,
        "receipt_paths": [],
    }


def write_receipt(path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    Persist a receipt (gated) and hand the payload back to the caller.

    - Teleology: the convenience sink organ runners call to emit-and-return in one step, so the in-memory receipt and the on-disk one stay the same object.
    - Guarantee: returns the same payload it was given; the file is written iff write_json_atomic's gates permit (no-op write does not change the return value).
    - Fails: never raises when gates suppress the write; otherwise inherits write_json_atomic's OSError / serialization failures.
    - When-needed: inspect when a runner's returned receipt and the file on disk disagree.
    - Writes: <path> (when permitted by write_json_atomic).
    - Non-goal: does not finalize status or authorize release; it persists whatever payload it is handed.
    - Escalates-to: write_json_atomic (the gated writer) and tests/test_receipts.py.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    """
    write_json_atomic(path, payload)
    return payload
