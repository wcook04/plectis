from __future__ import annotations

import argparse
import ast
from collections import deque
from collections.abc import Iterable, Iterator
import hashlib
import json
import os
import tomllib
from pathlib import Path
from typing import Any

from microcosm_core import architecture_kernel
from microcosm_core.bounded_paths import bounded_sorted_paths as _bounded_sorted_paths
from microcosm_core.public_payload_boundary import (
    SOURCE_OPEN_BODY_POLICY,
    public_payload_boundary,
)
from microcosm_core.receipts import (
    utc_now,
    write_local_state_json_atomic as write_json_atomic,
)
from microcosm_core.schemas import read_json_strict


PASS = "pass"
STATE_DIR = ".microcosm"
EVIDENCE_DIR = "evidence"
EVENT_STREAM = "events.jsonl"
OBSERVATORY_SERVE_COMMAND = (
    "microcosm serve <project> --host 127.0.0.1 --port 8765"
)
OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT = 7
OBSERVATORY_BOUNDED_VALIDATION_COMMAND = (
    f"{OBSERVATORY_SERVE_COMMAND} "
    f"--max-requests {OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT}"
)
OBSERVATORY_BOUNDED_VALIDATION_RULE = (
    "Use bounded_validation_command for first-screen route smokes; use command "
    "for an interactive browser session."
)
HASH_CHUNK_SIZE = 1024 * 1024
_EVENT_NUMBER_CACHE: dict[Path, tuple[tuple[int, int] | None, int]] = {}

IGNORE_DIRS = {
    ".git",
    STATE_DIR,
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
}

PACKAGE_MANIFESTS = {
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
}

SCRIPT_NAMES = {"Makefile", "justfile", "Taskfile.yml", "taskfile.yml"}
README_NAMES = {"README.md", "README.rst", "README.txt", "README"}
SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".swift"}
DOC_SUFFIXES = {".md", ".rst", ".txt"}
PYTHON_LENS_STATE = "python_lens.json"
TRUTH_READINESS_STATE = "truth_readiness.json"
PYTHON_LENS_SCAN_FULL = "full"
PYTHON_LENS_SCAN_FIRST_SCREEN = "first_screen_summary"
PYTHON_LENS_FIRST_SCREEN_PREFIX_BYTES = 4096
PYTHON_LENS_CARD_PREVIEW_LIMIT = 12
PROJECT_OBSERVE_CARD_COMMAND = "microcosm observe --card <project>"
PROJECT_OBSERVE_FULL_COMMAND = "microcosm observe <project>"
COMPILE_STATE_REFS = (
    f"{STATE_DIR}/project_manifest.json",
    f"{STATE_DIR}/architecture.json",
    f"{STATE_DIR}/state_index.json",
    f"{STATE_DIR}/catalog.json",
    f"{STATE_DIR}/{PYTHON_LENS_STATE}",
    f"{STATE_DIR}/patterns.json",
    f"{STATE_DIR}/routes.json",
    f"{STATE_DIR}/work_items.json",
    f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
    f"{STATE_DIR}/{EVENT_STREAM}",
    f"{STATE_DIR}/evidence/",
    f"{STATE_DIR}/graph.json",
    f"{STATE_DIR}/explanations/",
)
PROJECT_PYTHON_LENS_BOUNDARY_ID = "project_python_lens_read_model"
STD_PYTHON_NAVIGATION_LADDER = [
    "module_docs",
    "file_card",
    "symbol_capsule",
    "graph_context",
    "source_span",
]
# Controlled docstring-atom vocabulary mirrored from macro
# codex/standards/std_python.py::navigation_contract (contract_atoms +
# optional_contract_atoms). These are detected by NAME only; their authored
# prose is never exported, so source_bodies_exported stays False.
STD_PYTHON_CONTRACT_ATOMS = (
    "Teleology",
    "Mechanism",
    "Guarantee",
    "Forbid",
    "Fails",
    "Warns",
    "Reads",
    "Writes",
    "Locks",
    "Orders",
    "Schema",
    "Couples",
    "Non-goal",
    "When-needed",
    "Escalates-to",
    "Navigation-group",
)
SELF_DESCRIPTION_BAND_AUTHORED = "authored"
SELF_DESCRIPTION_BAND_LOCATOR_ONLY = "locator_only"
# Core contract triad: the spine atoms that distinguish a real authored capsule
# from a gameable prose docstring. Quality-tier ladder is ordered weakest->
# strongest so the scoreboard cannot be cheated by adding empty docstrings.
SELF_DESCRIPTION_CORE_TRIAD = ("Teleology", "Guarantee", "Fails")
SELF_DESCRIPTION_ROUTING_ATOMS = ("When-needed", "Escalates-to")
QUALITY_TIER_LOCATOR_ONLY = "locator_only"
QUALITY_TIER_AUTHORED_BARE = "authored_bare"
QUALITY_TIER_AUTHORED_MINIMAL = "authored_minimal"
QUALITY_TIER_AUTHORED_CONTRACT = "authored_contract"
QUALITY_TIER_AUTHORED_ROUTING = "authored_routing"
SELF_DESCRIPTION_QUALITY_TIERS = (
    QUALITY_TIER_LOCATOR_ONLY,
    QUALITY_TIER_AUTHORED_BARE,
    QUALITY_TIER_AUTHORED_MINIMAL,
    QUALITY_TIER_AUTHORED_CONTRACT,
    QUALITY_TIER_AUTHORED_ROUTING,
)
# Tiers at or above this index count as real authored coverage for release math.
SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER = QUALITY_TIER_AUTHORED_CONTRACT
PROBE_DISPOSITION_OUTCOMES = [
    "file_local_defect",
    "standard_amendment_candidate",
    "nothing_to_refine",
]
ROUTE_UTILITY_DISPOSITION_OUTCOMES = [
    "local_projection_defect",
    "local_source_or_test_defect",
    "macro_standard_amendment_candidate",
    "nothing_to_refine",
]


def _source_body_boundary_row() -> dict[str, Any]:
    """Stamp the source-body-boundary fields spliced into every public lens row.

    - Teleology: gives every emitted row the standing declaration that it is metadata-about-source, never a source-body export.
    - Guarantee: returns a dict carrying payload_boundary_ref, source_open_body_policy, and source_bodies_exported=False.
    - Fails: never raises; returns a fresh constant dict every call.
    - Reads: module constants PROJECT_PYTHON_LENS_BOUNDARY_ID and SOURCE_OPEN_BODY_POLICY only.
    - Non-goal: does not authorize source-body export, public-safe equivalence, or release; it only asserts the boundary.
    """
    return {
        "payload_boundary_ref": PROJECT_PYTHON_LENS_BOUNDARY_ID,
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "source_bodies_exported": False,
    }


def _evidence_interpretation_boundary() -> dict[str, Any]:
    """Standing interpretation rubric spliced into evidence list/inspect cards.

    - Teleology: tells a reader what a passing evidence card does and does not mean before they trust it.
    - Guarantee: returns a dict whose evidence_interpretation explains status_pass_means, payload_summary_means, and next_step.
    - Fails: never raises; returns a fresh constant dict every call.
    - Non-goal: does not authorize release, proof-correctness, trading, security, or private-root equivalence; it only frames evidence reading.
    - Escalates-to: the underlying receipt path or owning validator/builder named by next_step.
    """
    return {
        "evidence_interpretation": {
            "status_pass_means": (
                "the evidence card was produced and bounded; it is not release, "
                "proof-correctness, trading, security, or private-root equivalence authority"
            ),
            "payload_summary_means": (
                "safe shape/ref summary of the underlying receipt, not source body export"
            ),
            "next_step": (
                "use evidence_ref and schema_version to decide whether to open the "
                "underlying receipt path or the owning validator/builder"
            ),
        }
    }


def _evidence_full_payload_drilldown(
    *, project_ref: str, evidence_ref: str
) -> dict[str, str]:
    """Build the drilldown pointer from a compact evidence card to its full JSON.

    - Teleology: hands the reader the exact local path and command to open the complete receipt behind a compact card.
    - Guarantee: returns a dict with path, command, source_checkout_command, meaning, and an authority_boundary string.
    - Fails: never raises; a "." or "" project_ref yields a "./"-prefixed local path.
    - Non-goal: the full JSON it points to is drilldown evidence only; it does not authorize release, provider calls, source mutation, or proof correctness.
    """
    project_prefix = project_ref.rstrip("/")
    if project_prefix in {"", "."}:
        local_json_path = f"./{evidence_ref}"
    else:
        local_json_path = f"{project_prefix}/{evidence_ref}"
    return {
        "path": local_json_path,
        "command": f"python3 -m json.tool {local_json_path}",
        "source_checkout_command": f"python3 -m json.tool {local_json_path}",
        "meaning": "open the complete local JSON receipt behind this compact card",
        "authority_boundary": (
            "full local JSON is drilldown evidence only; it does not authorize "
            "release, provider calls, source mutation, proof correctness, trading "
            "advice, private-root equivalence, or whole-system correctness"
        ),
    }


def _project_python_lens_payload_boundary(command: str) -> dict[str, Any]:
    """Build the public-payload-boundary block for the python-lens surface.

    - Teleology: declares the python-lens read-model boundary so callers see input is unnormalized and output is ref/shape only.
    - Guarantee: returns the public_payload_boundary dict keyed to PROJECT_PYTHON_LENS_BOUNDARY_ID and the python_lens state surface.
    - Fails: never raises; delegates to public_payload_boundary.
    - Escalates-to: microcosm_core.public_payload_boundary.public_payload_boundary for the boundary contract.
    """
    return public_payload_boundary(
        boundary_id=PROJECT_PYTHON_LENS_BOUNDARY_ID,
        command=command,
        surface_ref=f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        input_payload_schema_normalized=False,
    )


def _project_name(project: Path) -> str:
    """Stable display name for a project root used in payload project_id fields.

    - Teleology: gives every receipt a non-empty project_id without leaking an absolute path.
    - Guarantee: returns the resolved final path component, or "project" when empty.
    - Fails: never raises; resolve uses strict=False.
    """
    return project.resolve(strict=False).name or "project"


def _state_dir(project: Path) -> Path:
    """Resolve the project's .microcosm state directory path.

    - Teleology: single source for where all project-local generated state lives.
    - Guarantee: returns project / STATE_DIR; does not create it.
    - Fails: never raises (pure path join).
    """
    return project / STATE_DIR


def _evidence_dir(project: Path) -> Path:
    """Resolve the project's .microcosm/evidence directory path.

    - Teleology: single source for where evidence receipt JSON is written.
    - Guarantee: returns the evidence subdirectory of the state dir; does not create it.
    - Fails: never raises (pure path join).
    """
    return _state_dir(project) / EVIDENCE_DIR


def _event_stream_path(project: Path) -> Path:
    """Resolve the project's append-only events.jsonl path.

    - Teleology: single source for the project-local event-history stream location.
    - Guarantee: returns the events.jsonl path under the state dir; does not create it.
    - Fails: never raises (pure path join).
    """
    return _state_dir(project) / EVENT_STREAM


def _path_exists(path: Path) -> bool:
    """OSError-tolerant existence check for a path.

    - Teleology: lets state-ref status surfaces probe paths without crashing on stat errors.
    - Guarantee: returns True iff the path exists; False on any OSError.
    - Fails: never raises; OSError is swallowed to False.
    """
    try:
        return path.exists()
    except OSError:
        return False


def _path_is_file(path: Path) -> bool:
    """OSError-tolerant is-file check for a path.

    - Teleology: gates reads/writes on whether a state ref is a regular file.
    - Guarantee: returns True iff the path is a regular file; False on any OSError.
    - Fails: never raises; OSError is swallowed to False.
    """
    try:
        return path.is_file()
    except OSError:
        return False


def _path_is_dir(path: Path) -> bool:
    """OSError-tolerant is-directory check for a path.

    - Teleology: gates directory-scoped scans on whether a state ref is a directory.
    - Guarantee: returns True iff the path is a directory; False on any OSError.
    - Fails: never raises; OSError is swallowed to False.
    """
    try:
        return path.is_dir()
    except OSError:
        return False


def _path_mtime_ns(path: Path) -> int | None:
    """OSError-tolerant nanosecond mtime read for freshness comparison.

    - Teleology: feeds the compile/ratchet staleness math that compares source vs cache mtimes.
    - Guarantee: returns st_mtime_ns on success; None on any OSError.
    - Fails: never raises; OSError is swallowed to None.
    """
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


def _path_size(path: Path) -> int:
    """OSError-tolerant byte-size read for a path.

    - Teleology: reports state-ref byte size in status cards without crashing on stat errors.
    - Guarantee: returns st_size on success; 0 on any OSError.
    - Fails: never raises; OSError is swallowed to 0.
    """
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _event_stream_signature(path: Path) -> tuple[int, int] | None:
    """Cheap (mtime_ns, size) signature used to invalidate the event-number cache.

    - Teleology: lets _next_event_number skip a full line count when the stream is unchanged.
    - Guarantee: returns (st_mtime_ns, st_size) on success; None on any OSError.
    - Fails: never raises; OSError is swallowed to None.
    """
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _project_relative(project: Path, path: Path) -> str:
    """Render a path as a posix ref relative to the project root.

    - Teleology: produces portable, home-free refs for receipts instead of absolute paths.
    - Guarantee: returns the project-relative posix string, or the bare name when path is outside the project.
    - Fails: never raises; a non-subpath ValueError falls back to path.name.
    """
    try:
        return path.resolve(strict=False).relative_to(project.resolve(strict=False)).as_posix()
    except ValueError:
        return path.name


def _read_project_json(project: Path, rel: str) -> dict[str, Any]:
    """Strictly read one .microcosm JSON state file as a dict.

    - Teleology: the single guarded reader for project-local generated state behind every card/observe surface.
    - Guarantee: returns the parsed dict, or {} when the file is absent or parses to a non-dict.
    - Fails: missing file -> {}; malformed JSON -> raises via read_json_strict.
    - Reads: STATE_DIR/<rel> under the project.
    """
    path = _state_dir(project) / rel
    if not _path_is_file(path):
        return {}
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dict rows, skipping blank lines.

    - Teleology: generic line-delimited reader for project-local jsonl state.
    - Guarantee: returns one dict per non-blank line that parses to a dict; missing file -> [].
    - Fails: a line that is not valid JSON -> raises json.JSONDecodeError.
    - Reads: the given jsonl path.
    """
    if not _path_is_file(path):
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _read_event_stream_summary(path: Path, *, tail_limit: int = 20) -> dict[str, Any]:
    """Summarize the append-only event stream into count, span histogram, and tail.

    - Teleology: gives observe/compile cards a bounded view of event history without loading the whole stream.
    - Guarantee: returns event_count, spans (per-span counts), a bounded events tail, and last_event; absent file -> zeroed summary.
    - Fails: a malformed jsonl line -> raises json.JSONDecodeError; non-dict lines are skipped.
    - Reads: the events.jsonl path.
    """
    if not _path_is_file(path):
        return {
            "event_count": 0,
            "spans": {},
            "events": [],
            "last_event": None,
        }
    event_count = 0
    spans: dict[str, int] = {}
    events_tail: deque[dict[str, Any]] = deque(maxlen=max(0, tail_limit))
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            event_count += 1
            span = str(payload.get("span") or "unknown")
            spans[span] = spans.get(span, 0) + 1
            events_tail.append(payload)
    events = list(events_tail)
    return {
        "event_count": event_count,
        "spans": spans,
        "events": events,
        "last_event": events[-1] if events else None,
    }


def _iter_files_under(root: Path, *, suffix: str | None = None) -> Iterator[Path]:
    """Iteratively yield files under a root, optionally filtered by suffix.

    - Teleology: bounded, symlink-safe directory walk powering evidence listing and state file counts.
    - Guarantee: yields each regular file (matching suffix when given) without following symlinks; non-dir root yields nothing.
    - Fails: never raises; per-entry and per-dir OSErrors are skipped.
    - Reads: the directory tree under root via os.scandir.
    """
    if not _path_is_dir(root):
        return
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False) and (
                            suffix is None or entry.name.endswith(suffix)
                        ):
                            yield Path(entry.path)
                        elif entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                    except OSError:
                        continue
        except OSError:
            continue


def _count_files_under(root: Path, *, suffix: str | None = None) -> int:
    """Count files under a root, optionally filtered by suffix.

    - Teleology: cheap file/evidence tallies for state-write-proof and status cards.
    - Guarantee: returns the number of files _iter_files_under yields; non-dir root -> 0.
    - Fails: never raises (delegates to the OSError-tolerant iterator).
    - Reads: the directory tree under root.
    """
    return sum(1 for _ in _iter_files_under(root, suffix=suffix))


def _append_event(project: Path, event: dict[str, Any]) -> None:
    """Append one event to the project's append-only events.jsonl and update the count cache.

    - Teleology: the single writer that records lifecycle spans as durable, ordered event history.
    - Guarantee: creates the state dir if needed, appends one canonical JSON line, and refreshes/clears the event-number cache for the stream.
    - Fails: directory or write failures -> raises OSError; a non-evt_ event_id just clears the cache entry.
    - Writes: STATE_DIR/events.jsonl under the project.
    """
    event_path = _event_stream_path(project)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
    event_number = _event_number_from_id(event.get("event_id"))
    cache_key = event_path.resolve(strict=False)
    if event_number is None:
        _EVENT_NUMBER_CACHE.pop(cache_key, None)
        return
    _EVENT_NUMBER_CACHE[cache_key] = (
        _event_stream_signature(event_path),
        event_number + 1,
    )


def _event_number_from_id(event_id: object) -> int | None:
    """Parse the integer ordinal out of an ``evt_NNNN`` event id.

    - Teleology: lets the append path seed the next-number cache from the id it just wrote.
    - Guarantee: returns the integer after the evt_ prefix; None for non-string/non-evt_/non-numeric input.
    - Fails: never raises; a non-numeric suffix returns None.
    """
    if not isinstance(event_id, str) or not event_id.startswith("evt_"):
        return None
    try:
        return int(event_id.removeprefix("evt_"))
    except ValueError:
        return None


def _next_event_number(project: Path) -> int:
    """Compute the next 1-based event ordinal for the project's stream.

    - Teleology: assigns monotonically increasing evt_ ids without re-counting an unchanged stream.
    - Guarantee: returns the cached next number when the stream signature is unchanged; otherwise counts non-blank lines + 1 and refreshes the cache.
    - Fails: never raises; a missing file yields 1.
    - Reads: STATE_DIR/events.jsonl (line count on cache miss).
    """
    event_path = _event_stream_path(project)
    cache_key = event_path.resolve(strict=False)
    signature = _event_stream_signature(event_path)
    cached = _EVENT_NUMBER_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return cached[1]
    if signature is None:
        _EVENT_NUMBER_CACHE[cache_key] = (signature, 1)
        return 1
    try:
        with event_path.open("r", encoding="utf-8") as fh:
            next_number = sum(1 for line in fh if line.strip()) + 1
    except FileNotFoundError:
        signature = None
        next_number = 1
    _EVENT_NUMBER_CACHE[cache_key] = (signature, next_number)
    return next_number


def _sha256_file(path: Path) -> str:
    """Chunked SHA-256 hex digest of a file's bytes.

    - Teleology: fingerprints a prior evidence body so an overwrite can record the replaced content's digest.
    - Guarantee: returns the lowercase hex SHA-256 over the full file, read in HASH_CHUNK_SIZE chunks.
    - Fails: unreadable/missing path -> raises OSError.
    - Reads: the bytes of the given path.
    - Non-goal: does not check public-safe equivalence or authorize source-body export; it only hashes bytes.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_evidence(project: Path, action_id: str, payload: dict[str, Any]) -> str:
    """Atomically write one evidence receipt, recording any prior-body digest.

    - Teleology: the single provenance-aware writer for project-local evidence cards under .microcosm/evidence.
    - Guarantee: writes the payload atomically with a stable evidence_ref and an evidence_replacement block (prior sha256, stable_ref, append-only history ref); returns the stable ref.
    - Fails: write failure -> raises OSError; replacement_recorded is False on first write.
    - Reads: any existing evidence file at the ref (to hash it).
    - Writes: STATE_DIR/evidence/<action_id>.json.
    - Non-goal: does not authorize release or treat the receipt as source-of-truth authority; it is drilldown evidence.
    """
    ref = f"{EVIDENCE_DIR}/{action_id}.json"
    evidence_path = _state_dir(project) / ref
    stable_ref = f"{STATE_DIR}/{ref}"
    previous_sha256 = _sha256_file(evidence_path) if _path_is_file(evidence_path) else None
    evidence_payload = dict(payload)
    evidence_payload.setdefault("evidence_ref", stable_ref)
    evidence_payload["evidence_replacement"] = {
        "stable_ref": stable_ref,
        "policy": "stable_ref_latest_body",
        "previous_sha256": previous_sha256,
        "replacement_recorded": previous_sha256 is not None,
        "append_only_event_history_ref": f"{STATE_DIR}/{EVENT_STREAM}",
    }
    write_json_atomic(evidence_path, evidence_payload)
    return stable_ref


def _base_payload(schema_version: str, project: Path) -> dict[str, Any]:
    """Standard envelope head shared by every result/receipt payload.

    - Teleology: guarantees every emitted payload carries schema, timestamp, project id, and the standing release-not-authorized posture.
    - Guarantee: returns a dict with schema_version, created_at, project_id, project_ref=".", state_ref, status=pass, release_authorized=False, receipts_are_drilldown_evidence=True.
    - Fails: never raises (string/timestamp assembly only).
    - Non-goal: status=pass is an envelope default, not a release or correctness authorization.
    """
    return {
        "schema_version": schema_version,
        "created_at": utc_now(),
        "project_id": _project_name(project),
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "status": PASS,
        "release_authorized": False,
        "receipts_are_drilldown_evidence": True,
    }


def _project_arg_ref(project_path: str | Path, project: Path) -> str:
    """Echo the project argument as the reader sees it for command templates.

    - Teleology: keeps emitted inspect/observe commands using the caller's own project token (e.g. ".") rather than a resolved absolute path.
    - Guarantee: returns the posix form of a Path arg or the raw string; falls back to project.name when empty.
    - Fails: never raises.
    """
    if isinstance(project_path, Path):
        raw = project_path.as_posix()
    else:
        raw = str(project_path)
    return raw or project.name


def _event(project: Path, span: str, status: str, **fields: Any) -> dict[str, Any]:
    """Construct one event record (id, timestamp, span, status, project) plus extra fields.

    - Teleology: the single factory for lifecycle event rows appended to the stream.
    - Guarantee: returns a dict with an evt_NNNN event_id, created_at, span, status, project_id, merged with any extra fields.
    - Fails: never raises; id numbering delegates to the cached _next_event_number.
    - Reads: the event stream (via _next_event_number) to pick the next ordinal.
    """
    event = {
        "event_id": f"evt_{_next_event_number(project):04d}",
        "created_at": utc_now(),
        "span": span,
        "status": status,
        "project_id": _project_name(project),
    }
    event.update(fields)
    return event


def _classify_file(
    rel: str,
    path: Path | None = None,
    *,
    name: str | None = None,
    suffix: str | None = None,
    parts: set[str] | None = None,
) -> str:
    """Assign a coarse catalog role to one file from its name/suffix/path parts.

    - Teleology: turns a raw file path into a role bucket (readme/package_manifest/script/test/docs/example/source/config/other) the catalog and patterns build on.
    - Guarantee: returns exactly one role string by first-match precedence over name sets, path parts, and suffixes.
    - Fails: never raises; an unrecognized file falls through to "other".
    - Reads: only the supplied path components (no disk access).
    """
    if path is not None:
        name = path.name
        suffix = path.suffix
        parts = set(path.parts)
    else:
        normalized = rel.replace(os.sep, "/")
        name = name or normalized.rsplit("/", 1)[-1]
        suffix = suffix if suffix is not None else os.path.splitext(name)[1]
        parts = parts if parts is not None else set(normalized.split("/"))
    if name in README_NAMES:
        return "readme"
    if name in PACKAGE_MANIFESTS:
        return "package_manifest"
    if name in SCRIPT_NAMES or suffix == ".sh":
        return "script"
    if "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test"
    if "docs" in parts or suffix in DOC_SUFFIXES:
        return "docs"
    if "examples" in parts:
        return "example"
    if "src" in parts or suffix in SOURCE_SUFFIXES:
        return "source"
    if suffix in {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config"
    return "other"


def _walk_project(project: Path) -> list[dict[str, Any]]:
    """Walk a project tree into sorted file rows with role and byte size.

    - Teleology: the source scan that feeds the catalog and every downstream lens; deterministic and ignore-pruned.
    - Guarantee: returns one row {path, name, suffix, role, bytes} per non-symlink file, with IGNORE_DIRS pruned and names sorted.
    - Fails: never raises; per-file stat errors and symlinks are skipped.
    - Reads: the project directory tree via os.walk.
    """
    rows: list[dict[str, Any]] = []
    project_root = project.resolve(strict=False)
    root_str = os.fspath(project_root)
    for current_root, dirnames, filenames in os.walk(root_str, topdown=True):
        dirnames[:] = sorted(
            dirname for dirname in dirnames if dirname not in IGNORE_DIRS
        )
        rel_dir = os.path.relpath(current_root, root_str)
        for name in sorted(filenames):
            full_path = os.path.join(current_root, name)
            if os.path.islink(full_path):
                continue
            try:
                size = os.stat(full_path, follow_symlinks=False).st_size
            except (FileNotFoundError, OSError):
                continue
            rel = name if rel_dir == "." else f"{rel_dir}/{name}"
            rel = rel.replace(os.sep, "/")
            suffix = os.path.splitext(name)[1]
            rows.append(
                {
                    "path": rel,
                    "name": name,
                    "suffix": suffix,
                    "role": _classify_file(
                        rel,
                        name=name,
                        suffix=suffix,
                        parts=set(rel.split("/")),
                    ),
                    "bytes": size,
                }
            )
    return rows


def _rows_by_role(files: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Invert catalog file rows into a sorted role -> paths index.

    - Teleology: gives patterns/routes a fast lookup of which paths exist under each role.
    - Guarantee: returns a dict keyed by role with sorted path lists, in sorted role order.
    - Fails: never raises; missing role/path fields default to "other"/"".
    """
    by_role: dict[str, list[str]] = {}
    for row in files:
        role = str(row.get("role") or "other")
        by_role.setdefault(role, []).append(str(row.get("path") or ""))
    return {key: sorted(value) for key, value in sorted(by_role.items())}


def _write_manifest(project: Path) -> dict[str, Any]:
    """Write the project manifest and refresh the architecture projection.

    - Teleology: declares the project-owned state contract, state-file inventory, and authority ceiling on init.
    - Guarantee: writes project_manifest.json atomically, triggers architecture_kernel.write_project_architecture, and returns the manifest dict (release/provider/source-mutation all False).
    - Fails: write or architecture failure -> raises OSError.
    - Writes: STATE_DIR/project_manifest.json (plus architecture state via the kernel).
    - Non-goal: does not authorize release, provider calls, live ledger mutation, or source mutation; the ceiling pins them False.
    """
    manifest = _base_payload("microcosm_project_manifest_v1", project)
    manifest.update(
        {
            "local_state_contract": "project_owned_state_only",
            "user_input": "project_folder",
            "useful_output": [
                "catalog",
                "patterns",
                "routes",
                "work_transactions",
                "event_stream",
                "evidence_refs",
            ],
            "state_files": [
                f"{STATE_DIR}/project_manifest.json",
                f"{STATE_DIR}/architecture.json",
                f"{STATE_DIR}/state_index.json",
                f"{STATE_DIR}/graph.json",
                f"{STATE_DIR}/catalog.json",
                f"{STATE_DIR}/{PYTHON_LENS_STATE}",
                f"{STATE_DIR}/patterns.json",
                f"{STATE_DIR}/routes.json",
                f"{STATE_DIR}/work_items.json",
                f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
                f"{STATE_DIR}/{EVENT_STREAM}",
                f"{STATE_DIR}/{EVIDENCE_DIR}/",
                f"{STATE_DIR}/explanations/",
            ],
            "authority_ceiling": {
                "live_task_ledger_mutation_authorized": False,
                "provider_calls_authorized": False,
                "release_authorized": False,
                "source_files_mutated": False,
            },
        }
    )
    write_json_atomic(_state_dir(project) / "project_manifest.json", manifest)
    architecture_kernel.write_project_architecture(project)
    return manifest


def init_project(project_path: str | Path) -> dict[str, Any]:
    """Initialize the .microcosm state scaffold for a target project.

    - Teleology: the public entrypoint that stands up project-local state (dirs, manifest, first init event/evidence).
    - Guarantee: creates project/.microcosm/evidence, writes the manifest, appends a project.init event, writes init evidence, and returns a result with manifest_ref, event_ref, evidence_ref.
    - Fails: filesystem failures -> raise OSError; otherwise status is pass.
    - When-needed: first contact with an uninitialized project, before index/compile.
    - Writes: STATE_DIR/ tree, project_manifest.json, events.jsonl, evidence/init.json.
    - Escalates-to: compile_project for the full loop; tests/test_project_substrate*.py for behavior.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    project.mkdir(parents=True, exist_ok=True)
    _state_dir(project).mkdir(parents=True, exist_ok=True)
    _evidence_dir(project).mkdir(parents=True, exist_ok=True)
    manifest = _write_manifest(project)
    event = _event(project, "project.init", PASS, evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/init.json")
    _append_event(project, event)
    evidence = dict(manifest)
    evidence["event_ref"] = f"{STATE_DIR}/{EVENT_STREAM}"
    evidence_ref = _write_evidence(project, "init", evidence)
    return {
        **_base_payload("microcosm_project_init_result_v1", project),
        "manifest_ref": f"{STATE_DIR}/project_manifest.json",
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "evidence_ref": evidence_ref,
    }


def _project_catalog_payload(project: Path) -> dict[str, Any]:
    """Build the in-memory catalog projection from a fresh project walk.

    - Teleology: the generated file-inventory read-model (counts, roles, detected roots) every other lens consumes.
    - Guarantee: returns a catalog dict with file_count, role_counts, roles, files, and detected manifest/source/test roots.
    - Fails: never raises beyond the underlying walk (which is OSError-tolerant).
    - Reads: the project tree via _walk_project.
    - Escalates-to: index_project, which persists this to catalog.json.
    """
    files = _walk_project(project)
    by_role = _rows_by_role(files)
    return {
        **_base_payload("microcosm_project_catalog_v1", project),
        "file_count": len(files),
        "role_counts": {role: len(paths) for role, paths in by_role.items()},
        "roles": by_role,
        "files": files,
        "detected_package_manifests": by_role.get("package_manifest", []),
        "detected_source_roots": sorted(
            {Path(path).parts[0] for path in by_role.get("source", []) if Path(path).parts}
        ),
        "detected_test_roots": sorted(
            {Path(path).parts[0] for path in by_role.get("test", []) if Path(path).parts}
        ),
    }


def index_project(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Index a project: walk it, persist catalog.json, emit an index event/evidence.

    - Teleology: the public step that materializes the file catalog as durable state for downstream lenses.
    - Guarantee: ensures init, writes catalog.json, optionally refreshes architecture, appends a project.index event, writes index evidence, and returns counts + evidence_ref.
    - Fails: filesystem failures -> raise OSError; otherwise status pass.
    - When-needed: refreshing the file inventory after the project tree changes.
    - Writes: STATE_DIR/catalog.json, events.jsonl, evidence/index.json.
    - Escalates-to: compile_project (full loop); architecture_kernel for the architecture projection.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    if not _path_is_file(_state_dir(project) / "project_manifest.json"):
        init_project(project)
    catalog = _project_catalog_payload(project)
    write_json_atomic(_state_dir(project) / "catalog.json", catalog)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.index",
        PASS,
        file_count=catalog["file_count"],
        catalog_ref=f"{STATE_DIR}/catalog.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/index.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(project, "index", {**catalog, "event_id": event["event_id"]})
    return {
        **_base_payload("microcosm_project_index_result_v1", project),
        "catalog_ref": f"{STATE_DIR}/catalog.json",
        "file_count": catalog["file_count"],
        "role_counts": catalog["role_counts"],
        "evidence_ref": evidence_ref,
    }


def catalog_project(project_path: str | Path) -> dict[str, Any]:
    """Return the project catalog view, indexing first if no cache exists.

    - Teleology: read-or-build accessor giving callers a catalog without forcing a re-index.
    - Guarantee: returns the cached catalog (re-stamped as catalog_view_v1, status pass); indexes once when catalog.json is absent.
    - Fails: indexing-side filesystem failure -> raises OSError.
    - Reads: STATE_DIR/catalog.json (writes it via index on cache miss).
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = _read_project_json(project, "catalog.json")
    if not catalog:
        index_project(project)
        catalog = _read_project_json(project, "catalog.json")
    return {**catalog, "schema_version": "microcosm_project_catalog_view_v1", "status": PASS}


def discover_patterns(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Detect grounded repo patterns (readme/manifest/source/tests/docs/...) from the catalog.

    - Teleology: the public pattern lens that reports which onboarding/runtime/test surfaces are present, each grounded in real refs.
    - Guarantee: writes patterns.json, appends a project.patterns event/evidence, and returns candidates with pass/missing status plus passing/missing counts.
    - Fails: filesystem failures -> raise OSError; otherwise status pass.
    - When-needed: assessing a project's structural surfaces before routing.
    - Writes: STATE_DIR/patterns.json, events.jsonl, evidence/patterns.json.
    - Non-goal: public pattern observation, not doctrine promotion or release; each row carries that authority_boundary.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    pattern_surface = architecture_kernel.pattern_surface_contract()
    standard_refs = pattern_surface.get("binding_standard_refs", [])
    standard_refs = standard_refs if isinstance(standard_refs, list) else []

    def present(role: str) -> bool:
        """Predicate: does the catalog have at least one path under this role?

        - Teleology: local helper guarding pattern checks on role presence.
        - Guarantee: returns True iff roles[role] is a non-empty list.
        - Fails: never raises; missing role -> False.
        """
        value = roles.get(role, [])
        return isinstance(value, list) and bool(value)

    candidates: list[dict[str, Any]] = []
    checks = [
        ("repo_has_readme", "README-first onboarding surface", "readme"),
        ("repo_has_package_manifest", "installable or runnable package metadata", "package_manifest"),
        ("repo_has_source_core", "visible source core", "source"),
        ("repo_has_tests", "behavior tests visible", "test"),
        ("repo_has_docs", "documentation surface visible", "docs"),
        ("repo_has_examples", "example usage surface visible", "example"),
        ("repo_has_scripts", "operator scripts or admin commands visible", "script"),
    ]
    for pattern_id, title, role in checks:
        refs = roles.get(role, []) if isinstance(roles.get(role), list) else []
        candidates.append(
            {
                "pattern_id": pattern_id,
                "title": title,
                "status": PASS if refs else "missing",
                "grounded_refs": refs[:12],
                "source": "project_index",
                "pattern_surface_id": pattern_surface.get("surface_id"),
                "state_ref": f"{STATE_DIR}/patterns.json::{pattern_id}",
                "evidence_ref": pattern_surface.get("evidence_ref", f"{STATE_DIR}/{EVIDENCE_DIR}/patterns.json"),
                "standard_refs": standard_refs,
                "authority_boundary": "public_pattern_observation_not_doctrine_promotion",
            }
        )
    payload = {
        **_base_payload("microcosm_project_patterns_v1", project),
        "pattern_surface": pattern_surface,
        "patterns": candidates,
        "passing_pattern_count": sum(1 for row in candidates if row["status"] == PASS),
        "missing_pattern_count": sum(1 for row in candidates if row["status"] != PASS),
    }
    write_json_atomic(_state_dir(project) / "patterns.json", payload)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.patterns",
        PASS,
        passing_pattern_count=payload["passing_pattern_count"],
        patterns_ref=f"{STATE_DIR}/patterns.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/patterns.json",
    )
    _append_event(project, event)
    payload["evidence_ref"] = _write_evidence(project, "patterns", {**payload, "event_id": event["event_id"]})
    return payload


def propose_routes(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Propose grounded navigation routes over a project from its catalog and patterns.

    - Teleology: the public route selector that turns detected surfaces into inspect/simulate/plan routes with grounded refs.
    - Guarantee: writes routes.json, appends a project.route event/evidence, and returns routes (always including a tests route, missing-variant when none) plus a pattern summary.
    - Fails: filesystem failures -> raise OSError; otherwise status pass.
    - When-needed: choosing where to start reading or simulating a project.
    - Writes: STATE_DIR/routes.json, events.jsonl, evidence/routes.json.
    - Escalates-to: explain_route and create_work/run_work, which consume a selected route.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project)
    patterns = discover_patterns(project, refresh_architecture=False)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    pattern_surface = architecture_kernel.pattern_surface_contract()

    routes: list[dict[str, Any]] = []

    def add(route_id: str, title: str, intent: str, refs: list[str], action: str) -> None:
        """Append one grounded route row to the local routes accumulator.

        - Teleology: local builder that attaches pattern/standard refs and authority fields to each route.
        - Guarantee: appends one route dict (refs capped at 12, source_mutation_authorized=False) to the enclosing routes list.
        - Fails: never raises; an unknown route_id just gets empty pattern_refs.
        """
        pattern_refs = {
            "readme_onboarding_route": ["repo_has_readme"],
            "package_runtime_route": ["repo_has_package_manifest"],
            "source_core_route": ["repo_has_source_core"],
            "test_behavior_route": ["repo_has_tests"],
            "missing_tests_route": ["repo_has_tests"],
            "docs_route": ["repo_has_docs"],
        }.get(route_id, [])
        routes.append(
            {
                "route_id": route_id,
                "title": title,
                "intent": intent,
                "grounded_refs": refs[:12],
                "action": action,
                "pattern_refs": pattern_refs,
                "pattern_surface_id": pattern_surface.get("surface_id"),
                "pattern_resolution_ref": pattern_surface.get("state_ref", f"{STATE_DIR}/patterns.json"),
                "standard_pressure_refs": architecture_kernel.standard_pressure_refs_for_route({"route_id": route_id}),
                "kernel_primitive_refs": ["catalog", "pattern", "route", "work", "event", "evidence"],
                "route_definition_ref": f"{STATE_DIR}/routes.json::{route_id}",
                "explain_command": f"microcosm explain <project> {route_id}",
                "authority": "project_local_projection_not_source_authority",
                "claims_source_authority": False,
                "source_mutation_authorized": False,
            }
        )

    readme_refs = roles.get("readme", []) if isinstance(roles.get("readme"), list) else []
    source_refs = roles.get("source", []) if isinstance(roles.get("source"), list) else []
    test_refs = roles.get("test", []) if isinstance(roles.get("test"), list) else []
    package_refs = roles.get("package_manifest", []) if isinstance(roles.get("package_manifest"), list) else []
    docs_refs = roles.get("docs", []) if isinstance(roles.get("docs"), list) else []

    if readme_refs:
        add("readme_onboarding_route", "Inspect README onboarding", "summarize public first-run path", readme_refs, "inspect")
    if package_refs:
        add("package_runtime_route", "Inspect package/runtime metadata", "find install and run surfaces", package_refs, "inspect")
    if source_refs:
        add("source_core_route", "Inspect source core", "locate primary implementation surfaces", source_refs, "inspect")
    if test_refs:
        add("test_behavior_route", "Run or inspect behavior tests", "find executable behavior checks", test_refs, "simulate")
    else:
        add("missing_tests_route", "Add behavior-test route", "project lacks visible tests", source_refs or readme_refs, "plan")
    if docs_refs:
        add("docs_route", "Inspect docs", "find user-facing explanatory surface", docs_refs, "inspect")

    payload = {
        **_base_payload("microcosm_project_routes_v1", project),
        "route_count": len(routes),
        "routes": routes,
        "pattern_summary": {
            "passing_pattern_count": patterns["passing_pattern_count"],
            "missing_pattern_count": patterns["missing_pattern_count"],
        },
    }
    write_json_atomic(_state_dir(project) / "routes.json", payload)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.route",
        PASS,
        route_count=len(routes),
        routes_ref=f"{STATE_DIR}/routes.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/routes.json",
    )
    _append_event(project, event)
    payload["evidence_ref"] = _write_evidence(project, "routes", {**payload, "event_id": event["event_id"]})
    return payload


def _read_text_prefix(path: Path, limit: int | None = 20000) -> str:
    """Read a bounded UTF-8 prefix of a file, tolerating decode/OS errors.

    - Teleology: bounds how much source text the lens pulls into memory for first-screen scans and pyproject parsing.
    - Guarantee: returns at most `limit` characters (whole file when limit is None); decode errors are ignored.
    - Fails: never raises; OSError -> "".
    - Reads: the given path's text.
    - Non-goal: not a source-body export surface; callers only derive counts/metadata from the text.
    """
    try:
        if limit is not None and limit >= 0:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                return fh.read(limit)
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text if limit is None else text[:limit]
    except OSError:
        return ""


def _python_lens_role(row: dict[str, Any]) -> str:
    """Classify a Python file into its lens role (package_init/test/source/script/...).

    - Teleology: gives each Python file the role that drives source-class tagging and criticality ranking.
    - Guarantee: returns exactly one role by first-match precedence over name and path parts; default "python_module".
    - Fails: never raises; a missing path defaults sensibly.
    - Reads: only the row's path string (no disk access).
    """
    rel = str(row.get("path") or "")
    path = Path(rel)
    parts = set(path.parts)
    name = path.name
    if name == "__init__.py":
        return "package_init"
    if name == "conftest.py":
        return "test_support"
    if "tests" in parts or name.startswith("test_") or name.endswith("_test.py"):
        return "test_module"
    if "examples" in parts:
        return "example_module"
    if "scripts" in parts or "bin" in parts:
        return "script"
    if "src" in parts:
        return "source_module"
    return "python_module"


def _python_package_root(rel: str) -> str | None:
    """Derive an importable package root from an ``__init__.py`` path.

    - Teleology: lets the lens surface package roots as a source-visibility signal even without loose modules.
    - Guarantee: returns "src/<pkg>" or the top part for an __init__.py path; None otherwise.
    - Fails: never raises; non-__init__ or too-shallow paths -> None.
    - Reads: only the rel string (no disk access).
    """
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == "src" and parts[-1] == "__init__.py":
        return f"src/{parts[1]}"
    if len(parts) >= 2 and parts[-1] == "__init__.py":
        return parts[0]
    return None


def _python_entrypoint_module_name(target: str) -> str | None:
    """Extract the importable module name from a console-script target string.

    - Teleology: lets entrypoint-row building resolve a pyproject console-script target to the module that backs it.
    - Guarantee: returns the dotted module portion before any ``:func``/``[extras]`` suffix, stripped; None when empty.
    - Fails: target with no module part (e.g. ":func") -> empty after strip -> returns None.
    """
    module_name = target.split(":", 1)[0].split("[", 1)[0].strip()
    return module_name or None


def _python_entrypoint_target_ref(project: Path, module_name: str) -> str | None:
    """Resolve a dotted module name to a real on-disk file ref under the project.

    - Teleology: grounds a console-script's module in an actual source path so entrypoint rows cite verifiable refs.
    - Guarantee: returns the first existing candidate path (src/ or root, .py or package __init__.py) as a posix ref; None if none exist.
    - Fails: empty module name or no matching file on disk -> returns None.
    - Reads: candidate source files under the given project root.
    """
    module_parts = [part for part in module_name.split(".") if part]
    if not module_parts:
        return None
    src_module_path = Path("src", *module_parts)
    root_module_path = Path(*module_parts)
    candidates = [
        src_module_path.with_suffix(".py").as_posix(),
        (src_module_path / "__init__.py").as_posix(),
        root_module_path.with_suffix(".py").as_posix(),
        (root_module_path / "__init__.py").as_posix(),
    ]
    for candidate in candidates:
        if _path_is_file(project / candidate):
            return candidate
    return None


def _python_console_entrypoint_rows(
    project: Path, pyproject_refs: list[str]
) -> list[dict[str, Any]]:
    """Build grounded console-script entrypoint rows from a project's pyproject files.

    - Teleology: surfaces declared CLI entrypoints as the python lens's runnable-surface evidence rows.
    - Guarantee: returns one row per ``[project.scripts]`` entry with script name, declaration ref, target, resolved module/target_ref, deduped grounded refs, and source-body boundary fields.
    - Fails: undecodable pyproject TOML -> that file skipped; blank/non-string script target -> that entry skipped; never raises.
    - Reads: each pyproject_ref's TOML and the candidate module files under project.
    """
    rows: list[dict[str, Any]] = []
    for pyproject_ref in pyproject_refs:
        try:
            payload = tomllib.loads(_read_text_prefix(project / pyproject_ref, limit=None))
        except tomllib.TOMLDecodeError:
            continue
        project_table = payload.get("project") if isinstance(payload, dict) else {}
        scripts = (
            project_table.get("scripts", {})
            if isinstance(project_table, dict)
            else {}
        )
        if not isinstance(scripts, dict):
            continue
        for script_name in sorted(str(key) for key in scripts):
            target = scripts.get(script_name)
            if not isinstance(target, str) or not target.strip():
                continue
            module_name = _python_entrypoint_module_name(target)
            target_ref = (
                _python_entrypoint_target_ref(project, module_name)
                if module_name
                else None
            )
            declaration_ref = f"{pyproject_ref}::project.scripts.{script_name}"
            rows.append(
                {
                    "script_name": script_name,
                    "declaration_ref": declaration_ref,
                    "target": target,
                    "target_module": module_name,
                    "target_ref": target_ref,
                    "grounded_refs": _dedupe_refs(
                        [target_ref] if target_ref else [], declaration_ref
                    ),
                    **_source_body_boundary_row(),
                }
            )
    return rows


def _python_import_counts(text: str) -> tuple[int, int]:
    """Count relative vs absolute import statements by scanning line starts.

    - Teleology: cheap import-shape signal for the file card without an AST parse.
    - Guarantee: returns (relative_count, absolute_count); ``from .`` counts relative, other import/from lines count absolute.
    - Fails: never raises (string scan only).
    - Reads: only the supplied text.
    """
    relative_count = 0
    absolute_count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from ."):
            relative_count += 1
        elif stripped.startswith("import ") or stripped.startswith("from "):
            absolute_count += 1
    return relative_count, absolute_count


def _python_route(route_id: str, title: str, refs: list[str], readiness: str) -> dict[str, Any]:
    """Build one Python route row with grounded refs and authority fields.

    - Teleology: shapes the python-lens route rows (metadata/source/test/entrypoint) consumed by the assay and cards.
    - Guarantee: returns a route dict with route_id, title, readiness, refs capped at 12, and source/provider-not-authorized fields.
    - Fails: never raises (dict assembly only).
    - Non-goal: a project-local route lens row, not static-analysis authority; carries that authority field.
    """
    return {
        "route_id": route_id,
        "title": title,
        "readiness": readiness,
        "grounded_refs": refs[:12],
        "source_mutation_authorized": False,
        "provider_calls_authorized": False,
        "authority": "project_local_python_route_lens_not_static_analysis_authority",
    }


def _python_symbol_kind(node: ast.AST) -> str:
    """Map an AST def/class node to a symbol-kind string.

    - Teleology: labels every extracted symbol capsule as class/async_function/function.
    - Guarantee: returns "class" for ClassDef, "async_function" for AsyncFunctionDef, else "function".
    - Fails: never raises (isinstance dispatch only).
    """
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "function"


def _detect_docstring_atoms(docstring: str | None) -> list[str]:
    """Return canonical std_python contract-atom names present in a docstring.

    Detects atom *keys* only (``Teleology:``, ``Guarantee:``, ...) by scanning
    line starts; the authored prose after the colon is never captured or
    returned, so this stays metadata-about-source, not a source-body export.

    - Teleology: the detector primitive that decides which std_python contract atoms a docstring names.
    - Guarantee: returns the subset of STD_PYTHON_CONTRACT_ATOMS whose ``<atom>:`` marker begins a stripped line (leading ``-``/``*`` removed); order follows the vocabulary; None/empty docstring -> [].
    - Fails: never raises (pure string scan).
    - Reads: only the supplied docstring; never the prose after the colon.
    - Escalates-to: macro codex/standards/std_python.py::navigation_contract for the atom vocabulary.
    """
    if not docstring:
        return []
    present: list[str] = []
    lines = docstring.splitlines()
    for atom in STD_PYTHON_CONTRACT_ATOMS:
        marker = f"{atom}:"
        for raw in lines:
            stripped = raw.strip().lstrip("-*").strip()
            if stripped.startswith(marker):
                present.append(atom)
                break
    return present


def _self_description_quality_tier(has_docstring: bool, atoms: list[str]) -> str:
    """Un-gameable quality ladder over a symbol's authored atoms.

    A bare prose docstring with no contract atoms lands at ``authored_bare``
    (presence without contract), so the scoreboard cannot be inflated by empty
    docstrings. Real coverage starts at ``authored_contract`` (the Teleology/
    Guarantee/Fails triad) and peaks at ``authored_routing`` (triad plus a
    navigation atom).

    - Teleology: maps (has_docstring, atoms) to the un-gameable quality tier the scoreboard ranks on.
    - Guarantee: returns locator_only (no docstring) < authored_bare (docstring, no atoms) < authored_minimal (atoms but no triad) < authored_contract (triad) < authored_routing (triad + a routing atom).
    - Fails: never raises (set membership only).
    - Reads: SELF_DESCRIPTION_CORE_TRIAD and SELF_DESCRIPTION_ROUTING_ATOMS constants.
    """
    if not has_docstring:
        return QUALITY_TIER_LOCATOR_ONLY
    atom_set = set(atoms)
    if not atom_set:
        return QUALITY_TIER_AUTHORED_BARE
    has_triad = all(atom in atom_set for atom in SELF_DESCRIPTION_CORE_TRIAD)
    if not has_triad:
        return QUALITY_TIER_AUTHORED_MINIMAL
    if any(atom in atom_set for atom in SELF_DESCRIPTION_ROUTING_ATOMS):
        return QUALITY_TIER_AUTHORED_ROUTING
    return QUALITY_TIER_AUTHORED_CONTRACT


def _quality_tier_is_real_coverage(tier: str) -> bool:
    """Decide whether a quality tier counts as real authored coverage.

    - Teleology: the single gate that release math uses to separate real coverage from bare/locator tiers.
    - Guarantee: returns True iff tier's ladder index is >= the authored_contract floor; unknown tier -> False.
    - Fails: never raises; an out-of-vocabulary tier returns False.
    - Reads: SELF_DESCRIPTION_QUALITY_TIERS / SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER constants.
    """
    floor = SELF_DESCRIPTION_QUALITY_TIERS.index(
        SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER
    )
    try:
        return SELF_DESCRIPTION_QUALITY_TIERS.index(tier) >= floor
    except ValueError:
        return False


def _symbol_self_description(node: ast.AST) -> dict[str, Any]:
    """Presence-only authored-atom metadata for one symbol capsule.

    Classifies the symbol's self-description band, its un-gameable quality tier,
    and which contract atoms its docstring names, without exporting the
    docstring body.

    - Teleology: turns one AST symbol into the presence-only self-description row the coverage and queue surfaces aggregate.
    - Guarantee: returns has_docstring, self_description_band, quality_tier, is_real_coverage, authored_contract_atoms, and authored_atom_count; never includes the docstring text.
    - Fails: never raises (delegates to ast.get_docstring and the pure tier helpers).
    - Reads: only the node's docstring.
    """
    docstring = ast.get_docstring(node)
    has_docstring = docstring is not None
    atoms = _detect_docstring_atoms(docstring)
    quality_tier = _self_description_quality_tier(has_docstring, atoms)
    return {
        "has_docstring": has_docstring,
        "self_description_band": (
            SELF_DESCRIPTION_BAND_AUTHORED
            if has_docstring
            else SELF_DESCRIPTION_BAND_LOCATOR_ONLY
        ),
        "quality_tier": quality_tier,
        "is_real_coverage": _quality_tier_is_real_coverage(quality_tier),
        "authored_contract_atoms": atoms,
        "authored_atom_count": len(atoms),
    }


# Release-criticality classes for the authoring queue, ordered most->least
# critical. Rank 0 is the release spine that must be authored first.
CODE_LENS_CRITICALITY_CLASSES = (
    "public_entrypoint",
    "validator",
    "source_custody",
    "organ_runner",
    "route_selector",
    "builder_projection",
    "evidence_receipt",
    "owned_core",
    "script",
    "test_negative_case",
    "trivial_or_imported",
)


# In-tree exact-copy / macro-body-import zones. Files under these dirs carry
# imported macro source bodies that must byte-match upstream (the source-capsule
# / macro_body_import_floor coupling gate). Authoring docstrings into them breaks
# that coupling and blocks `microcosm spine`, so they are custody, not owned
# authoring targets — even though they live under src/.
CODE_LENS_COUPLING_GOVERNED_MARKERS = (
    "/organs/",
    "/macro_tools/",
    "/engine_room/",
)


def _is_imported_source_bundle(path: str) -> bool:
    """True for paths that are source-custody, not owned authoring targets.

    Two categories are excluded from the owned authoring queue:
    1. Imported bundles under ``examples/`` / ``fixtures/`` as
       ``source_modules``/``source_artifacts`` — imported macro source.
    2. In-tree exact-copy / macro-body-import zones (``organs/``,
       ``macro_tools/``, ``engine_room/``) whose bodies must byte-match upstream
       under the coupling gate; authoring them breaks ``microcosm spine``.

    A usage-funded authoring campaign must not target either, or it would mutate
    code it does not own and break source coupling.

    - Teleology: the directory-heuristic custody gate that keeps the authoring queue off imported/exact-copy source.
    - Guarantee: returns True for examples/fixtures/.venv/site-packages, organs/macro_tools/engine_room coupling zones, and source_modules/source_artifacts/_bundle paths; False for owned paths.
    - Fails: never raises (string/parts test only).
    - Reads: only the path string.
    - Non-goal: a heuristic exclusion, not manifest proof; does not authorize source-body export or release.
    - Escalates-to: _load_manifest_custody_paths for manifest-authoritative custody.
    """
    lower = path.lower()
    parts = set(Path(path).parts)
    if {"examples", "fixtures", ".venv", "site-packages"} & parts:
        return True
    if any(marker in f"/{lower}/" for marker in CODE_LENS_COUPLING_GOVERNED_MARKERS):
        return True
    return any(
        marker in lower
        for marker in ("source_modules/", "source_artifacts/", "_bundle/")
    )


def _load_manifest_custody_paths(project: Path) -> set[str]:
    """Authoritative custody paths declared by source manifests, if present.

    Reads ``core/organ_registry.json`` (organ ``runner`` modules) and
    ``core/substrate_substitution_ledger.json`` (``microcosm_target_refs``) to
    build the set of files the substrate itself declares as exact-copy / source-
    custody. Returns relative posix paths. Empty (graceful) for projects without
    these manifests, e.g. scratch test projects.

    - Teleology: lifts custody declarations from the substrate's own manifests so the queue trusts source-of-truth over directory shape.
    - Guarantee: returns the set of relative posix .py paths declared by organ_registry runner modules and substitution-ledger microcosm_target_refs; empty set when manifests are absent or unreadable.
    - Fails: never raises; JSON/OS errors on a manifest degrade to no rows from that manifest.
    - Reads: core/organ_registry.json and core/substrate_substitution_ledger.json under the project.
    - Non-goal: reports custody; does not authorize source-body export, equivalence, or release.
    - Escalates-to: core/organ_registry.json and core/substrate_substitution_ledger.json as the authoritative custody sources.
    """
    custody: set[str] = set()
    registry = project / "core/organ_registry.json"
    if registry.is_file():
        try:
            rows = json.loads(registry.read_text(encoding="utf-8")).get(
                "implemented_organs", []
            )
        except (json.JSONDecodeError, OSError):
            rows = []
        for row in rows if isinstance(rows, list) else []:
            runner = row.get("runner") if isinstance(row, dict) else None
            if isinstance(runner, str) and runner.startswith("microcosm_core."):
                custody.add("src/" + runner.replace(".", "/") + ".py")
    ledger = project / "core/substrate_substitution_ledger.json"
    if ledger.is_file():
        try:
            disp = json.loads(ledger.read_text(encoding="utf-8")).get(
                "organ_substrate_dispositions", []
            )
        except (json.JSONDecodeError, OSError):
            disp = []
        for row in disp if isinstance(disp, list) else []:
            for ref in (row.get("microcosm_target_refs") or []) if isinstance(row, dict) else []:
                p = (ref.get("path") if isinstance(ref, dict) else str(ref)).split("::")[0].strip()
                if p.endswith(".py"):
                    custody.add(p)
    return custody


def _custody_basis(path: str, manifest_custody_paths: set[str]) -> str | None:
    """Why a path is source-custody (not owned authoring), or None if owned.

    Reports the evidence basis so the health board is honest about whether an
    exclusion is manifest-backed or only a directory heuristic:
    ``manifest_provenance`` > ``imported_bundle`` > ``directory_coupling_marker``.

    - Teleology: makes every custody exclusion auditable by naming why a path was excluded.
    - Guarantee: returns "manifest_provenance" for manifest-declared paths, "imported_bundle" for example/fixture/bundle paths, "directory_coupling_marker" for coupling zones, else None (owned).
    - Fails: never raises (string/parts/set test only).
    - Reads: only the path string and the supplied custody set.
    - Non-goal: classifies basis; does not authorize source-body export or release.
    """
    if path in manifest_custody_paths:
        return "manifest_provenance"
    lower = path.lower()
    parts = set(Path(path).parts)
    if {"examples", "fixtures", ".venv", "site-packages"} & parts or any(
        marker in lower for marker in ("source_modules/", "source_artifacts/", "_bundle/")
    ):
        return "imported_bundle"
    if any(marker in f"/{lower}/" for marker in CODE_LENS_COUPLING_GOVERNED_MARKERS):
        return "directory_coupling_marker"
    return None


def _code_lens_criticality(
    path: str, symbol_name: str, source_class: str
) -> tuple[str, int]:
    """Classify a symbol's release criticality for the authoring queue.

    Heuristic over path + symbol name + source class. Owned code earns a real
    rank; imported example/fixture bundles and plain tests sink to the bottom so
    the campaign spends usage on the release spine, not on custody-only surfaces.

    - Teleology: ranks each owned symbol so a usage-funded authoring campaign authors the release spine first.
    - Guarantee: returns (class, rank) where class is one of CODE_LENS_CRITICALITY_CLASSES and rank is its index (0 = most critical); imported/example bundles and tests sink to the bottom classes.
    - Fails: never raises (string-token classification only).
    - Reads: only the path, symbol_name, and source_class arguments.
    - Non-goal: a release-priority heuristic, not a correctness or release authorization.
    """
    lower_path = path.lower()
    name = symbol_name.split(".")[-1].lower()
    full = symbol_name.lower()
    if source_class == "example_module" or _is_imported_source_bundle(path):
        return "trivial_or_imported", CODE_LENS_CRITICALITY_CLASSES.index(
            "trivial_or_imported"
        )
    if source_class in {"test_module", "test_support"}:
        cls = "test_negative_case"
        return cls, CODE_LENS_CRITICALITY_CLASSES.index(cls)
    if "validators/" in lower_path or name.startswith("validate") or "validator" in name:
        cls = "validator"
    elif (
        lower_path.endswith("cli.py")
        or name in {"main", "build_parser", "serve", "run_server"}
        or name.startswith("serve")
        or "entrypoint" in name
    ):
        cls = "public_entrypoint"
    elif any(
        token in full
        for token in ("source_capsule", "source_coupling", "import", "export", "manifest", "provenance", "custody")
    ):
        cls = "source_custody"
    elif any(token in full for token in ("organ", "_run_work", "run_work", "board", "result_emit", "emit_result")):
        cls = "organ_runner"
    elif name.startswith("route") or name.endswith("_route") or "navigation" in name or "propose_routes" in full:
        cls = "route_selector"
    elif name.startswith(("build_", "_build_", "compile", "project", "_project")) or "projection" in full or "atlas" in full:
        cls = "builder_projection"
    elif any(token in full for token in ("evidence", "receipt", "observe", "ledger")):
        cls = "evidence_receipt"
    elif source_class == "script":
        cls = "script"
    elif source_class in {"source_module", "package_init", "python_module"}:
        cls = "owned_core"
    else:
        cls = "trivial_or_imported"
    return cls, CODE_LENS_CRITICALITY_CLASSES.index(cls)


def _python_span_projection(rel: str, text: str) -> dict[str, Any]:
    """Project one Python file's source into span/capsule/import rows via AST, no bodies.

    - Teleology: the AST extractor that turns a file into source-span locators, symbol capsules, and import edges for the lens.
    - Guarantee: returns parse_status, module_has_docstring, source_span_rows, symbol_capsule_rows, import_edges (capped 48), and parse_error; spans carry locators only, never bodies.
    - Fails: never raises; a SyntaxError returns parse_status "syntax_error" with a parse_error row and the module span only.
    - Reads: only the supplied source text (no disk access).
    - Non-goal: source-span locators, not source-body export or correctness authority; every row stamps that boundary.
    """
    line_count = max(1, len(text.splitlines()))
    module_span = {
        "span_id": f"{rel}::module",
        "path": rel,
        "symbol_name": "<module>",
        "symbol_kind": "module",
        "line_start": 1,
        "line_end": line_count,
        "depth_band": "source_span",
        **_source_body_boundary_row(),
        "authority": "source_span_locator_not_source_body_or_correctness_authority",
    }
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "parse_status": "syntax_error",
            "module_has_docstring": False,
            "source_span_rows": [module_span],
            "symbol_capsule_rows": [],
            "import_edges": [],
            "parse_error": {
                "path": rel,
                "line": exc.lineno,
                "message": exc.msg,
                **_source_body_boundary_row(),
            },
        }

    source_span_rows = [module_span]
    symbol_capsule_rows: list[dict[str, Any]] = []
    source_class = _python_lens_role({"path": rel})

    def visit_scope(node: ast.AST, parents: list[str]) -> None:
        """Recursively append source-span and symbol-capsule rows for nested defs/classes.

        - Teleology: walks one scope's body, emitting a span + capsule per class/function and recursing into it.
        - Guarantee: appends rows (with qualnames, line ranges, self-description, boundary fields) to the enclosing lists for every nested def/class; mutates no inputs beyond those accumulators.
        - Fails: never raises; non-def children are recursed without emitting a row.
        - Reads: only the AST node tree.
        """
        body = getattr(node, "body", [])
        for child in body if isinstance(body, list) else []:
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = ".".join([*parents, child.name])
                line_start = int(getattr(child, "lineno", 1))
                line_end = int(getattr(child, "end_lineno", line_start))
                symbol_kind = _python_symbol_kind(child)
                span_id = f"{rel}::{qualname}"
                source_span_rows.append(
                    {
                        "span_id": span_id,
                        "path": rel,
                        "symbol_name": qualname,
                        "symbol_kind": symbol_kind,
                        "line_start": line_start,
                        "line_end": line_end,
                        "depth_band": "source_span",
                        **_source_body_boundary_row(),
                        "authority": "source_span_locator_not_source_body_or_correctness_authority",
                    }
                )
                symbol_capsule_rows.append(
                    {
                        "symbol_id": span_id,
                        "path": rel,
                        "symbol_name": qualname,
                        "symbol_kind": symbol_kind,
                        "source_class": source_class,
                        "source_span_ref": span_id,
                        "depth_band": "symbol_capsule",
                        **_symbol_self_description(child),
                        **_source_body_boundary_row(),
                    }
                )
                visit_scope(child, [*parents, child.name])
            else:
                visit_scope(child, parents)

    visit_scope(tree, [])
    import_edges: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_edges.append(
                    {
                        "path": rel,
                        "edge": "imports",
                        "target": alias.name,
                        "line": int(getattr(node, "lineno", 1)),
                        "depth_band": "graph_context",
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * int(getattr(node, "level", 0))
            target = f"{prefix}{node.module or ''}"
            import_edges.append(
                {
                    "path": rel,
                    "edge": "imports_from",
                    "target": target,
                    "line": int(getattr(node, "lineno", 1)),
                    "depth_band": "graph_context",
                }
            )
    return {
        "parse_status": "parsed",
        "module_has_docstring": ast.get_docstring(tree) is not None,
        "source_span_rows": source_span_rows,
        "symbol_capsule_rows": symbol_capsule_rows,
        "import_edges": import_edges[:48],
        "parse_error": None,
    }


def _python_self_description_coverage(
    symbol_capsule_rows: list[dict[str, Any]],
    module_docstring_refs: list[str],
    module_count: int,
    deferred: bool = False,
) -> dict[str, Any]:
    """Honest authored-vs-locator coverage over the symbol capsule graph.

    Turns a flat count of capsules ("35k symbol_capsule rows") into the
    release-relevant split: how many capsules are authored (carry a docstring),
    how many are locator-only, which contract atoms are actually used, and how
    that breaks down by source class. Presence-derived only; no source bodies.

    ``deferred`` is True in compact/first-screen scan mode, where the full
    symbol walk is skipped; the band reports the deferral honestly instead of
    claiming ``no_symbols`` over an unscanned tree.

    - Teleology: the generated coverage projection that splits symbol capsules into authored/real/locator with quality bands and release-critical scoping.
    - Guarantee: returns a coverage_v2 dict (authored/real counts and ratios, quality_band_counts, atom histogram, by_source_class, release_critical_coverage, coverage_band); presence-derived only, source_bodies_exported=False.
    - Fails: never raises; empty rows -> zeroed ratios; deferred=True -> coverage_band "deferred_first_screen_summary".
    - Reads: only the supplied capsule rows and module docstring refs (no disk access).
    - Non-goal: a generated coverage read-model, not release or static-analysis or docstring-quality authority.
    - Escalates-to: python_lens (which embeds it) and macro std_python.py::navigation_contract for the atom vocabulary.
    """
    total = len(symbol_capsule_rows)
    authored = 0
    real_coverage = 0
    atom_histogram: dict[str, int] = {}
    by_source_class: dict[str, dict[str, int]] = {}
    quality_band_counts: dict[str, int] = {
        tier: 0 for tier in SELF_DESCRIPTION_QUALITY_TIERS
    }
    release_critical_total = 0
    release_critical_real = 0
    critical_floor = CODE_LENS_CRITICALITY_CLASSES.index("owned_core")
    for row in symbol_capsule_rows:
        band = row.get("self_description_band")
        is_authored = band == SELF_DESCRIPTION_BAND_AUTHORED
        if is_authored:
            authored += 1
        tier = str(row.get("quality_tier") or QUALITY_TIER_LOCATOR_ONLY)
        quality_band_counts[tier] = quality_band_counts.get(tier, 0) + 1
        is_real = _quality_tier_is_real_coverage(tier)
        if is_real:
            real_coverage += 1
        for atom in row.get("authored_contract_atoms", []) or []:
            atom_histogram[atom] = atom_histogram.get(atom, 0) + 1
        source_class = str(row.get("source_class") or "python_module")
        bucket = by_source_class.setdefault(
            source_class,
            {"total": 0, "authored": 0, "locator_only": 0},
        )
        bucket["total"] += 1
        if is_authored:
            bucket["authored"] += 1
        else:
            bucket["locator_only"] += 1
        _cls, rank = _code_lens_criticality(
            str(row.get("path") or ""),
            str(row.get("symbol_name") or ""),
            source_class,
        )
        if rank < critical_floor:
            release_critical_total += 1
            if is_real:
                release_critical_real += 1
    locator_only = total - authored
    authored_ratio = round(authored / total, 4) if total else 0.0
    real_coverage_ratio = round(real_coverage / total, 4) if total else 0.0
    release_critical_ratio = (
        round(release_critical_real / release_critical_total, 4)
        if release_critical_total
        else 0.0
    )
    if deferred:
        coverage_band = "deferred_first_screen_summary"
    elif total == 0:
        coverage_band = "no_symbols"
    elif authored_ratio >= 0.75:
        coverage_band = "authored_rich"
    elif authored_ratio >= 0.25:
        coverage_band = "mixed_self_description"
    else:
        coverage_band = "indexed_not_self_describing"
    module_with_docstring = len(module_docstring_refs)
    module_ratio = (
        round(module_with_docstring / module_count, 4) if module_count else 0.0
    )
    return {
        "schema_version": "microcosm_python_self_description_coverage_v2",
        "standard_ref": "macro:codex/standards/std_python.py::navigation_contract",
        "scan_deferred": deferred,
        "total_symbol_capsules": total,
        "authored_symbol_capsules": authored,
        "locator_only_symbol_capsules": locator_only,
        "authored_ratio": authored_ratio,
        "real_coverage_symbol_capsules": real_coverage,
        "real_coverage_ratio": real_coverage_ratio,
        "coverage_band": coverage_band,
        "quality_band_counts": quality_band_counts,
        "quality_tier_ladder": list(SELF_DESCRIPTION_QUALITY_TIERS),
        "real_coverage_floor_tier": SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER,
        "release_critical_coverage": {
            "critical_symbols": release_critical_total,
            "real_coverage_symbols": release_critical_real,
            "ratio": release_critical_ratio,
            "critical_classes": [
                cls
                for cls in CODE_LENS_CRITICALITY_CLASSES
                if CODE_LENS_CRITICALITY_CLASSES.index(cls) < critical_floor
            ],
        },
        "authored_atom_histogram": dict(sorted(atom_histogram.items())),
        "contract_atom_vocabulary": list(STD_PYTHON_CONTRACT_ATOMS),
        "by_source_class": dict(sorted(by_source_class.items())),
        "module_docstring_coverage": {
            "modules_with_docstring": module_with_docstring,
            "total_modules": module_count,
            "ratio": module_ratio,
        },
        "metric_meaning": (
            "authored = symbol carries a docstring; real_coverage = quality_tier "
            ">= authored_contract (the Teleology/Guarantee/Fails triad), which a "
            "bare docstring cannot reach; locator_only = path/name/kind/span "
            "locator with no authored self-description. release_critical_coverage "
            "scopes real_coverage to release-spine classes (entrypoints, "
            "validators, source custody, organ runners, routes, builders, "
            "receipts). Atom presence is detected by name; docstring prose is not "
            "exported"
        ),
        "source_bodies_exported": False,
        "authority": (
            "generated_project_local_self_description_coverage_not_release_"
            "or_static_analysis_or_docstring_quality_authority"
        ),
        "reentry_condition": (
            "rerun after Python docstrings, symbols, or the std_python contract "
            "atom vocabulary change"
        ),
    }


CODE_LENS_BATCH_BY_CRITICALITY = {
    "public_entrypoint": "A_public_entrypoint_spine",
    "validator": "B_validator_authority_spine",
    "source_custody": "C_source_custody_spine",
    "organ_runner": "D_organ_runner_spine",
    "route_selector": "D_organ_runner_spine",
    "builder_projection": "E_builders_projections",
    "evidence_receipt": "E_builders_projections",
    "test_negative_case": "F_selected_tests",
    "owned_core": "G_owned_core_tail",
    "script": "G_owned_core_tail",
    "trivial_or_imported": "Z_excluded_not_owned_compliance",
}
CODE_LENS_OWNED_SOURCE_CLASSES = (
    "source_module",
    "script",
    "package_init",
    "python_module",
)


def _code_lens_authoring_queue(
    symbol_capsule_rows: list[dict[str, Any]],
    *,
    include_done: bool = False,
    preview_limit: int = 40,
    manifest_custody_paths: set[str] | None = None,
) -> dict[str, Any]:
    """Ranked authoring work-list over Microcosm-owned symbols.

    Ranks every owned symbol by release criticality then current quality tier so
    a usage-funded campaign authors the release spine first. Source-custody
    surfaces (imported bundles + in-tree exact-copy/macro-body zones) are
    excluded; ``custody_classification`` reports, with an honest ``custody_basis``
    (manifest_provenance vs imported_bundle vs directory_coupling_marker), why
    each candidate path was excluded. Returns summary counts plus a bounded
    preview; the full ranked list is in ``queue_rows``.

    - Teleology: the generated authoring work-list that ranks owned, below-floor symbols by release criticality for a usage-funded campaign.
    - Guarantee: returns owned totals/ratios, by_batch/by_criticality counts, custody_classification (with honest custody_basis), a bounded queue_preview, and the full queue_rows sorted by criticality then tier_gap; source_bodies_exported=False.
    - Fails: never raises; missing custody set defaults to empty.
    - Reads: only the capsule rows and the supplied manifest custody set.
    - Non-goal: a generated authoring queue, not release authority; excluded paths are custody, not owned targets.
    - Escalates-to: python_lens (which embeds it) and core/organ_registry.json / substitution ledger for custody provenance.
    """
    manifest_custody_paths = manifest_custody_paths or set()
    rows: list[dict[str, Any]] = []
    by_batch: dict[str, int] = {}
    by_criticality: dict[str, int] = {}
    custody_basis_counts: dict[str, int] = {}
    custody_paths_seen: set[str] = set()
    owned_total = 0
    owned_real = 0
    for row in symbol_capsule_rows:
        source_class = str(row.get("source_class") or "python_module")
        path = str(row.get("path") or "")
        if source_class not in CODE_LENS_OWNED_SOURCE_CLASSES:
            continue
        # Exclusion is the union of the directory heuristic and manifest evidence
        # (organ runners + ledger refs): organ runners can live outside organs/
        # (e.g. a runner under validators/), so the manifest is authoritative.
        if _is_imported_source_bundle(path) or path in manifest_custody_paths:
            if path not in custody_paths_seen:
                custody_paths_seen.add(path)
                basis = _custody_basis(path, manifest_custody_paths) or "imported_bundle"
                custody_basis_counts[basis] = custody_basis_counts.get(basis, 0) + 1
            continue
        owned_total += 1
        tier = str(row.get("quality_tier") or QUALITY_TIER_LOCATOR_ONLY)
        is_real = _quality_tier_is_real_coverage(tier)
        if is_real:
            owned_real += 1
            if not include_done:
                continue
        cls, rank = _code_lens_criticality(
            path,
            str(row.get("symbol_name") or ""),
            source_class,
        )
        batch = CODE_LENS_BATCH_BY_CRITICALITY.get(cls, "G_owned_core_tail")
        by_batch[batch] = by_batch.get(batch, 0) + 1
        by_criticality[cls] = by_criticality.get(cls, 0) + 1
        # tier_gap: distance below the real-coverage floor (bigger = needier).
        tier_index = (
            SELF_DESCRIPTION_QUALITY_TIERS.index(tier)
            if tier in SELF_DESCRIPTION_QUALITY_TIERS
            else 0
        )
        floor_index = SELF_DESCRIPTION_QUALITY_TIERS.index(
            SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER
        )
        rows.append(
            {
                "symbol_id": row.get("symbol_id"),
                "path": row.get("path"),
                "symbol_name": row.get("symbol_name"),
                "symbol_kind": row.get("symbol_kind"),
                "source_class": source_class,
                "criticality_class": cls,
                "criticality_rank": rank,
                "current_quality_tier": tier,
                "is_real_coverage": is_real,
                "tier_gap": max(0, floor_index - tier_index),
                "suggested_batch": batch,
                **_source_body_boundary_row(),
            }
        )
    rows.sort(
        key=lambda r: (
            r["criticality_rank"],
            -r["tier_gap"],
            str(r["path"]),
            str(r["symbol_name"]),
        )
    )
    owned_needing = len(rows) if not include_done else sum(
        1 for r in rows if not r["is_real_coverage"]
    )
    return {
        "schema_version": "microcosm_code_lens_authoring_queue_v1",
        "standard_ref": "macro:codex/standards/std_python.py::navigation_contract",
        "owned_symbol_total": owned_total,
        "owned_real_coverage": owned_real,
        "owned_needing_authoring": owned_needing,
        "owned_real_coverage_ratio": (
            round(owned_real / owned_total, 4) if owned_total else 0.0
        ),
        "by_batch_counts": dict(sorted(by_batch.items())),
        "by_criticality_counts": dict(sorted(by_criticality.items())),
        "batch_order": sorted(set(CODE_LENS_BATCH_BY_CRITICALITY.values())),
        "custody_classification": {
            "excluded_candidate_paths": len(custody_paths_seen),
            "by_basis": dict(sorted(custody_basis_counts.items())),
            "manifest_custody_paths_loaded": len(manifest_custody_paths),
            "basis_meaning": (
                "manifest_provenance = declared by organ_registry/substitution "
                "ledger; imported_bundle = examples/fixtures/source bundles; "
                "directory_coupling_marker = in-tree organs/macro_tools/engine_room "
                "exact-copy zone (heuristic, not yet manifest-confirmed)"
            ),
        },
        "queue_preview_limit": preview_limit,
        "queue_preview": rows[:preview_limit],
        "omitted_queue_row_count": max(0, len(rows) - preview_limit),
        "queue_rows": rows,
        "metric_meaning": (
            "ranked owned symbols below the real-coverage floor, most release-"
            "critical first; a usage-funded authoring campaign consumes this top-"
            "down. Imported example bundles are excluded as custody surfaces"
        ),
        "source_bodies_exported": False,
        "authority": (
            "generated_project_local_authoring_queue_not_release_authority"
        ),
        "reentry_condition": (
            "rerun after authoring atoms or after the quality-tier ladder changes"
        ),
    }


def _authoring_queue_card(queue: dict[str, Any]) -> dict[str, Any]:
    """Lean card view of the authoring queue: summary counts only, no rows.

    Keeps the CLI card under its byte budget; the full ``queue_rows`` and
    preview stay in the ``--full`` lens payload for a campaign driver that calls
    ``python_lens`` directly.

    - Teleology: projects the heavy authoring queue down to summary scalars for the compact CLI card.
    - Guarantee: returns a dict of the kept summary keys plus queue_rows_omitted and a full_queue_route pointer; empty/non-dict input -> {}.
    - Fails: never raises (key projection only).
    - Reads: only the supplied queue dict.
    - Escalates-to: the ``--full`` python-lens payload's authoring_queue for the full rows.
    """
    if not isinstance(queue, dict) or not queue:
        return {}
    keep = (
        "schema_version",
        "owned_symbol_total",
        "owned_real_coverage",
        "owned_needing_authoring",
        "owned_real_coverage_ratio",
        "by_batch_counts",
    )
    card = {key: queue[key] for key in keep if key in queue}
    card["queue_rows_omitted"] = len(queue.get("queue_rows", []) or [])
    card["full_queue_route"] = "python-lens --full <project> ['authoring_queue']"
    return card


def _self_description_coverage_card(coverage: dict[str, Any]) -> dict[str, Any]:
    """Lean card view of coverage: scalars + quality bands, no static vocab lists.

    The full atom histogram, source-class breakdown, vocabulary, and ladder stay
    in the ``--full`` lens; the card keeps the release-relevant scalars.

    - Teleology: projects the heavy coverage read-model down to release-relevant scalars + quality bands for the compact card.
    - Guarantee: returns a dict of the kept coverage keys plus a trimmed release_critical_coverage; empty/non-dict input -> {}.
    - Fails: never raises (key projection only).
    - Reads: only the supplied coverage dict.
    - Escalates-to: the ``--full`` python-lens payload's self_description_coverage for the full breakdown.
    """
    if not isinstance(coverage, dict) or not coverage:
        return {}
    keep = (
        "schema_version",
        "scan_deferred",
        "coverage_band",
        "total_symbol_capsules",
        "authored_symbol_capsules",
        "locator_only_symbol_capsules",
        "authored_ratio",
        "real_coverage_symbol_capsules",
        "real_coverage_ratio",
        "quality_band_counts",
        "source_bodies_exported",
    )
    card = {key: coverage[key] for key in keep if key in coverage}
    critical = coverage.get("release_critical_coverage")
    if isinstance(critical, dict):
        card["release_critical_coverage"] = {
            "critical_symbols": critical.get("critical_symbols", 0),
            "real_coverage_symbols": critical.get("real_coverage_symbols", 0),
            "ratio": critical.get("ratio", 0.0),
        }
    return card


def _python_route_probe_tasks(route_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build navigation probe tasks (one per Python route) with expected depth and disposition.

    - Teleology: turns route rows into closeable probe tasks so the assay proves each route is navigable before success language.
    - Guarantee: returns one task per route with prompt, expected depth band, expected refs, readiness, and a probe_disposition (nothing_to_refine when ready or for an absent entrypoint, else file_local_defect).
    - Fails: never raises (row shaping only).
    - Reads: only the supplied route rows.
    """
    depth_by_route = {
        "python_package_metadata_route": "file_card",
        "python_source_core_route": "source_span",
        "python_test_behavior_route": "source_span",
        "python_entrypoint_route": "source_span",
    }
    prompts_by_route = {
        "python_package_metadata_route": "Find the package metadata source for this project.",
        "python_source_core_route": "Find the primary Python source span for this project.",
        "python_test_behavior_route": "Find the source span that proves Python behavior is tested.",
        "python_entrypoint_route": "Find the source span for a runnable Python entrypoint, if this project has one.",
    }
    tasks: list[dict[str, Any]] = []
    for row in route_rows:
        route_id = str(row.get("route_id") or "")
        readiness = str(row.get("readiness") or "missing")
        disposition = "nothing_to_refine" if readiness == PASS else "file_local_defect"
        if route_id == "python_entrypoint_route" and readiness != PASS:
            disposition = "nothing_to_refine"
        tasks.append(
            {
                "task_id": f"probe:{route_id}",
                "route_id": route_id,
                "prompt": prompts_by_route.get(route_id, f"Find the source evidence for {route_id}."),
                "expected_depth_band": depth_by_route.get(route_id, "file_card"),
                "expected_refs": row.get("grounded_refs", []),
                "readiness": readiness,
                "probe_disposition": disposition,
                "reentry_condition": (
                    "project declares a runnable Python entrypoint"
                    if route_id == "python_entrypoint_route" and readiness != PASS
                    else "route readiness changes"
                ),
            }
        )
    return tasks


def _python_probe_disposition_rows(
    route_probe_tasks: list[dict[str, Any]],
    parse_error_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Close every probe task and parse error into an explicit disposition row.

    - Teleology: enforces the no-unclosed-probe rule by giving each probe and parse error a named outcome.
    - Guarantee: returns one disposition row per probe task (carrying its outcome/readiness) and one file_local_defect row per parse error, with reentry conditions.
    - Fails: never raises (row shaping only).
    - Reads: only the supplied task and parse-error rows.
    """
    rows: list[dict[str, Any]] = []
    for task in route_probe_tasks:
        rows.append(
            {
                "disposition_id": f"disposition:{task['route_id']}",
                "subject_id": task["route_id"],
                "subject_kind": "route_probe_task",
                "outcome": task["probe_disposition"],
                "readiness": task["readiness"],
                "expected_depth_band": task["expected_depth_band"],
                "reentry_condition": task["reentry_condition"],
            }
        )
    for row in parse_error_rows:
        rows.append(
            {
                "disposition_id": f"disposition:parse:{row.get('path')}",
                "subject_id": row.get("path"),
                "subject_kind": "python_parse_projection",
                "outcome": "file_local_defect",
                "readiness": "blocked",
                "expected_depth_band": "source_span",
                "reentry_condition": "syntax parses or file is removed from Python lens scope",
                "line": row.get("line"),
                **_source_body_boundary_row(),
            }
        )
    return rows


def _disposition_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Tally probe disposition rows by their PROBE_DISPOSITION_OUTCOMES outcome.

    - Teleology: gives the assay a per-outcome histogram of how probes were disposed.
    - Guarantee: returns a dict with one count per known outcome (zero when absent).
    - Fails: never raises (counting only).
    - Reads: only the supplied rows.
    """
    return {
        outcome: sum(1 for row in rows if row.get("outcome") == outcome)
        for outcome in PROBE_DISPOSITION_OUTCOMES
    }


def _first_path_with_role(path_rows: list[dict[str, Any]], roles: set[str]) -> str | None:
    """Return the first file path whose python_role is in the requested set.

    - Teleology: picks a representative source/test/etc. card for route-utility fixtures.
    - Guarantee: returns the first matching non-empty path, or None when none match.
    - Fails: never raises (linear scan only).
    - Reads: only the supplied path rows.
    """
    for row in path_rows:
        if row.get("python_role") in roles and row.get("path"):
            return str(row["path"])
    return None


def _first_symbol_ref(symbol_capsule_rows: list[dict[str, Any]], path: str | None = None) -> str | None:
    """Return the first symbol_id, optionally restricted to one file path.

    - Teleology: supplies a representative symbol capsule ref for the symbol-lookup route fixture.
    - Guarantee: returns the first symbol_id (within `path` when given), or None.
    - Fails: never raises (linear scan only).
    - Reads: only the supplied capsule rows.
    """
    for row in symbol_capsule_rows:
        if path is not None and row.get("path") != path:
            continue
        if row.get("symbol_id"):
            return str(row["symbol_id"])
    return None


def _first_source_span_ref(
    source_span_rows: list[dict[str, Any]],
    path: str | None = None,
    *,
    prefer_non_module: bool = False,
) -> str | None:
    """Return the first source-span id, optionally per-path and preferring non-module spans.

    - Teleology: supplies a representative span locator for source/test/entrypoint route fixtures.
    - Guarantee: returns the first matching span_id (a non-module span when prefer_non_module), falling back to the first span; None when none match.
    - Fails: never raises (linear scan only).
    - Reads: only the supplied span rows.
    """
    fallback: str | None = None
    for row in source_span_rows:
        if path is not None and row.get("path") != path:
            continue
        span_id = row.get("span_id")
        if not span_id:
            continue
        if fallback is None:
            fallback = str(span_id)
        if not prefer_non_module or row.get("symbol_kind") != "module":
            return str(span_id)
    return fallback


def _first_graph_context_ref(import_edges: list[dict[str, Any]]) -> str | None:
    """Render the first import edge as a ``path:line->target`` graph-context ref.

    - Teleology: supplies a representative dependency-edge ref for the graph-context route fixture.
    - Guarantee: returns the first edge formatted as path:line->target, or None when no usable edge exists.
    - Fails: never raises (linear scan only).
    - Reads: only the supplied import edges.
    """
    for row in import_edges:
        path = row.get("path")
        target = row.get("target")
        line = row.get("line")
        if path and target:
            return f"{path}:{line}->{target}"
    return None


def _route_utility_task(
    *,
    task_id: str,
    task_intent: str,
    expected_start_band: str,
    selected_band: str,
    route_hops: list[str],
    requirement_met: bool,
    expected_file_card: str | None = None,
    expected_symbol_capsule: str | None = None,
    expected_graph_context: str | None = None,
    expected_source_span: str | None = None,
    token_or_tool_count_proxy: int | None = None,
    failure_class: str = "local_projection_defect",
    disposition: str = "local_projection_defect",
    reentry_condition: str = "route utility fixture rerun changes this result",
    not_applicable: bool = False,
) -> dict[str, Any]:
    """Build one route-utility assay task row with correctness and disposition.

    - Teleology: the factory for the route-utility curriculum tasks that prove the cheapest band reaches each target without exporting bodies.
    - Guarantee: returns a task dict with bands, route hops, expected refs, correctness (pass/blocked/not_applicable), worst_state, failure_class, and a final disposition (nothing_to_refine when met/N-A); stamps source-body boundary fields.
    - Fails: never raises (row assembly only).
    - Reads: only the supplied arguments.
    - Non-goal: a route-utility read-model row, not source or release authority.
    """
    correctness = "not_applicable" if not_applicable else (PASS if requirement_met else "blocked")
    final_disposition = "nothing_to_refine" if requirement_met or not_applicable else disposition
    return {
        "task_id": task_id,
        "task_intent": task_intent,
        "entry_surface_ref": "atlas/entry_packet.json::python_navigation_route",
        "route_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
        "expected_start_band": expected_start_band,
        "selected_band": selected_band,
        "route_hops": route_hops,
        "expected_file_card": expected_file_card,
        "expected_symbol_capsule": expected_symbol_capsule,
        "expected_graph_context": expected_graph_context,
        "expected_source_span": expected_source_span,
        "correctness": correctness,
        "provenance_state": "derived_from_local_ast_and_entry_route",
        "worst_state": PASS if requirement_met or not_applicable else "degraded",
        "token_or_tool_count_proxy": token_or_tool_count_proxy or len(route_hops),
        "failure_class": "none" if requirement_met else ("not_applicable" if not_applicable else failure_class),
        "disposition": final_disposition,
        "reentry_condition": reentry_condition,
        **_source_body_boundary_row(),
    }


def _route_utility_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    """Tally route-utility tasks by their ROUTE_UTILITY_DISPOSITION_OUTCOMES disposition.

    - Teleology: gives the curriculum a per-disposition histogram of route-utility outcomes.
    - Guarantee: returns a dict with one count per known route-utility outcome (zero when absent).
    - Fails: never raises (counting only).
    - Reads: only the supplied tasks.
    """
    return {
        outcome: sum(1 for row in tasks if row.get("disposition") == outcome)
        for outcome in ROUTE_UTILITY_DISPOSITION_OUTCOMES
    }


def _existing_project_refs(project: Path, refs: list[str | None]) -> list[str]:
    """Filter a ref list down to those that are real files under the project, deduped.

    - Teleology: grounds each route-utility task's watched surfaces in refs that actually exist on disk.
    - Guarantee: returns the input refs that resolve to existing project files, preserving order and dropping duplicates/None.
    - Fails: never raises (existence checks are OSError-tolerant).
    - Reads: probes each candidate path under the project root.
    """
    existing: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        if not ref:
            continue
        rel = str(ref)
        if rel in seen:
            continue
        if _path_is_file(project / rel):
            seen.add(rel)
            existing.append(rel)
    return existing


def _route_utility_ratchet(
    *,
    project: Path,
    tasks: list[dict[str, Any]],
    task_surface_refs: dict[str, list[str]],
    write_state: bool,
) -> dict[str, Any]:
    """Compare watched route surfaces against written lens state to flag stale route tasks.

    - Teleology: the freshness ratchet that names which route-utility tasks went stale because their source surfaces changed after the last state write.
    - Guarantee: returns a ratchet dict (changed_surface_refs, affected/stale_task_ids, state_freshness, last_run_result, next_reentry_condition); in write_state mode reports current_write with nothing stale.
    - Fails: never raises; missing/unreadable state -> honest no_written_state/unreadable_written_state freshness with nothing_to_refine.
    - Reads: the python_lens state file mtime and the watched source surfaces' mtimes.
    - Non-goal: reports staleness; does not itself rewrite state or authorize release.
    """
    state_path = _state_dir(project) / PYTHON_LENS_STATE
    task_ids = [str(row.get("task_id") or "") for row in tasks if row.get("task_id")]
    watched_refs = sorted(
        {
            ref
            for refs in task_surface_refs.values()
            for ref in refs
            if _path_is_file(project / ref)
        }
    )
    high_risk_route_families = [
        "entry_packet_drilldown",
        "implementation_atlas",
        "source_span_locator",
        "symbol_capsule_locator",
        "graph_context_locator",
        "probe_disposition_closure",
        "payload_boundary",
    ]
    if write_state:
        return {
            "schema_version": "microcosm_python_route_utility_ratchet_v1",
            "seed_task_count": len(tasks),
            "generated_task_count": 0,
            "changed_surface_refs": [],
            "affected_task_ids": [],
            "stale_task_ids": [],
            "high_risk_route_families": high_risk_route_families,
            "sampled_from": watched_refs,
            "state_freshness": "current_write",
            "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
            "last_run_result": "curriculum_current",
            "next_reentry_condition": (
                "rerun non-writing route utility ratchet after source, test, entry, "
                "symbol, graph, or payload-boundary surfaces change"
            ),
        }
    if not _path_is_file(state_path):
        return {
            "schema_version": "microcosm_python_route_utility_ratchet_v1",
            "seed_task_count": len(tasks),
            "generated_task_count": 0,
            "changed_surface_refs": [],
            "affected_task_ids": [],
            "stale_task_ids": [],
            "high_risk_route_families": high_risk_route_families,
            "sampled_from": watched_refs,
            "state_freshness": "no_written_state",
            "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
            "last_run_result": "nothing_to_refine",
            "next_reentry_condition": (
                "write python_lens state once before stale-surface comparison can "
                "name affected route tasks"
            ),
        }
    state_mtime_ns = _path_mtime_ns(state_path)
    if state_mtime_ns is None:
        return {
            "schema_version": "microcosm_python_route_utility_ratchet_v1",
            "seed_task_count": len(tasks),
            "generated_task_count": 0,
            "changed_surface_refs": [],
            "affected_task_ids": [],
            "stale_task_ids": [],
            "high_risk_route_families": high_risk_route_families,
            "sampled_from": watched_refs,
            "state_freshness": "unreadable_written_state",
            "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
            "last_run_result": "nothing_to_refine",
            "next_reentry_condition": (
                "rerun non-writing route utility ratchet after python_lens "
                "state metadata can be read"
            ),
        }
    changed_surface_refs: list[str] = []
    unreadable_surface_count = 0
    for rel in watched_refs:
        source_mtime_ns = _path_mtime_ns(project / rel)
        if source_mtime_ns is None:
            unreadable_surface_count += 1
            continue
        if source_mtime_ns > state_mtime_ns:
            changed_surface_refs.append(rel)
    changed_set = set(changed_surface_refs)
    affected_task_ids = [
        task_id
        for task_id in task_ids
        if changed_set.intersection(task_surface_refs.get(task_id, []))
    ]
    last_run_result = (
        "curriculum_stale_for_changed_surface"
        if affected_task_ids
        else "nothing_to_refine"
    )
    return {
        "schema_version": "microcosm_python_route_utility_ratchet_v1",
        "seed_task_count": len(tasks),
        "generated_task_count": len(affected_task_ids),
        "generated_task_ids": [
            f"ratchet:{task_id}" for task_id in affected_task_ids
        ],
        "changed_surface_refs": changed_surface_refs,
        "affected_task_ids": affected_task_ids,
        "stale_task_ids": affected_task_ids,
        "high_risk_route_families": high_risk_route_families,
        "sampled_from": watched_refs,
        "unreadable_surface_count": unreadable_surface_count,
        "state_freshness": "compared_to_written_state",
        "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "last_run_result": last_run_result,
        "next_reentry_condition": (
            "refresh python_lens state or repair the named route task surfaces "
            "before treating the curriculum as current"
            if affected_task_ids
            else "rerun after watched route surfaces change"
        ),
    }


def _python_route_utility_curriculum(
    *,
    project: Path,
    path_rows: list[dict[str, Any]],
    source_refs: list[str],
    test_refs: list[str],
    pyproject_refs: list[str],
    entrypoint_refs: list[str],
    source_span_rows: list[dict[str, Any]],
    symbol_capsule_rows: list[dict[str, Any]],
    import_edges: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
    probe_dispositions: list[dict[str, Any]],
    parse_error_rows: list[dict[str, Any]],
    write_state: bool,
) -> dict[str, Any]:
    """Build the route-utility curriculum: navigability tasks + freshness ratchet over the lens.

    - Teleology: the generated curriculum proving the Python navigation routes reach metadata/source/test/entrypoint/symbol/graph targets at the cheapest band without exporting bodies.
    - Guarantee: returns a curriculum dict with tasks, ratchet, route_utility_metrics, disposition buckets, nothing_to_refine receipts, and payload_boundary_ok; source_bodies_exported=False.
    - Fails: never raises (delegates to OSError-tolerant ref/mtime helpers).
    - Reads: the project's existing route surfaces (for grounding) and the lens state mtime (via the ratchet).
    - Non-goal: a public-safe route-utility read-model, not source or release authority.
    - Escalates-to: python_lens (which embeds it) and standards/std_microcosm_route_decision.json.
    """
    source_card = _first_path_with_role(path_rows, {"source_module", "package_init", "python_module"})
    test_card = _first_path_with_role(path_rows, {"test_module", "test_support"})
    entrypoint_card = entrypoint_refs[0] if entrypoint_refs else None
    source_span = _first_source_span_ref(source_span_rows, source_card)
    test_span = _first_source_span_ref(source_span_rows, test_card, prefer_non_module=True)
    entrypoint_span = _first_source_span_ref(source_span_rows, entrypoint_card, prefer_non_module=True)
    symbol_ref = _first_symbol_ref(symbol_capsule_rows, source_card) or _first_symbol_ref(symbol_capsule_rows)
    graph_ref = _first_graph_context_ref(import_edges)
    route_ids = {str(row.get("route_id") or "") for row in route_rows}
    closed_probe_count = sum(
        1
        for row in probe_dispositions
        if row.get("outcome") in PROBE_DISPOSITION_OUTCOMES
    )

    tasks = [
        _route_utility_task(
            task_id="route_utility:entry_surface_to_python_assay",
            task_intent="Start from the public entry packet and reach the Python navigation assay route.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=[
                "atlas/entry_packet.json::python_navigation_route",
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
            ],
            requirement_met=True,
            expected_file_card=source_card,
            reentry_condition="entry packet python_navigation_route changes",
        ),
        _route_utility_task(
            task_id="route_utility:implementation_atlas_drilldown",
            task_intent="Use the implementation atlas as the assay drilldown rather than a parallel registry.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=[
                "atlas/entry_packet.json::python_navigation_route",
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
            ],
            requirement_met=True,
            expected_file_card=source_card,
            reentry_condition="implementation atlas route changes",
        ),
        _route_utility_task(
            task_id="route_utility:package_metadata_file_card",
            task_intent="Locate package metadata through the cheapest sufficient file-card band.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["python_navigation_route", "route_rows.python_package_metadata_route"],
            requirement_met=bool(pyproject_refs),
            expected_file_card=pyproject_refs[0] if pyproject_refs else None,
            failure_class="local_source_or_test_defect",
            disposition="local_source_or_test_defect",
            reentry_condition="pyproject metadata is added or removed",
        ),
        _route_utility_task(
            task_id="route_utility:source_core_source_span",
            task_intent="Find the primary source-core proof locator without exporting source bodies.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "implementation_atlas.python_navigation_assay.primary_code_cards",
                "source_span_rows",
            ],
            requirement_met=bool(source_card and source_span),
            expected_file_card=source_card,
            expected_source_span=source_span,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="source core path or source-span extraction changes",
        ),
        _route_utility_task(
            task_id="route_utility:test_behavior_source_span",
            task_intent="Find the behavior-test proof locator through the test route.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "route_rows.python_test_behavior_route",
                "source_span_rows",
            ],
            requirement_met=bool(test_card and test_span),
            expected_file_card=test_card,
            expected_source_span=test_span,
            failure_class="local_source_or_test_defect",
            disposition="local_source_or_test_defect",
            reentry_condition="test route or test source spans change",
        ),
        _route_utility_task(
            task_id="route_utility:entrypoint_source_span",
            task_intent="Find a runnable Python entrypoint when the project declares one.",
            expected_start_band="file_card",
            selected_band="source_span",
            route_hops=[
                "python_navigation_route",
                "route_rows.python_entrypoint_route",
                "source_span_rows",
            ],
            requirement_met=bool(entrypoint_card and entrypoint_span),
            expected_file_card=entrypoint_card,
            expected_source_span=entrypoint_span,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="project declares a runnable Python entrypoint",
            not_applicable=not entrypoint_refs,
        ),
        _route_utility_task(
            task_id="route_utility:symbol_capsule_lookup",
            task_intent="Answer a symbol-level question at symbol-capsule depth before opening spans.",
            expected_start_band="symbol_capsule",
            selected_band="symbol_capsule",
            route_hops=["python_navigation_route", "symbol_capsule_rows"],
            requirement_met=bool(symbol_ref),
            expected_file_card=source_card,
            expected_symbol_capsule=symbol_ref,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="symbol extraction changes",
            not_applicable=not symbol_capsule_rows,
        ),
        _route_utility_task(
            task_id="route_utility:graph_context_lookup",
            task_intent="Answer a dependency question at graph-context depth before opening spans.",
            expected_start_band="graph_context",
            selected_band="graph_context",
            route_hops=["python_navigation_route", "graph_context_edges"],
            requirement_met=bool(graph_ref),
            expected_graph_context=graph_ref,
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="import graph extraction changes",
            not_applicable=not import_edges,
        ),
        _route_utility_task(
            task_id="route_utility:probe_disposition_closure",
            task_intent="Verify every route probe is closed into a disposition before success language.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["navigation_assay.route_probe_tasks", "navigation_assay.probe_dispositions"],
            requirement_met=closed_probe_count == len(probe_dispositions) and not parse_error_rows,
            failure_class="macro_standard_amendment_candidate",
            disposition="macro_standard_amendment_candidate",
            reentry_condition="probe disposition grammar or parse status changes",
        ),
        _route_utility_task(
            task_id="route_utility:payload_boundary",
            task_intent="Verify route utility uses refs and spans without exporting source bodies.",
            expected_start_band="file_card",
            selected_band="file_card",
            route_hops=["python_navigation_route", "authority_ceiling.source_bodies_exported"],
            requirement_met=all(row.get("source_bodies_exported") is False for row in path_rows),
            failure_class="local_projection_defect",
            disposition="local_projection_defect",
            reentry_condition="payload-boundary or authority-ceiling fields change",
        ),
    ]
    task_surface_refs = {
        "route_utility:entry_surface_to_python_assay": _existing_project_refs(
            project, ["atlas/entry_packet.json", "README.md"]
        ),
        "route_utility:implementation_atlas_drilldown": _existing_project_refs(
            project, ["atlas/entry_packet.json", "README.md", source_card]
        ),
        "route_utility:package_metadata_file_card": _existing_project_refs(
            project, pyproject_refs
        ),
        "route_utility:source_core_source_span": _existing_project_refs(
            project, [source_card]
        ),
        "route_utility:test_behavior_source_span": _existing_project_refs(
            project, [test_card]
        ),
        "route_utility:entrypoint_source_span": _existing_project_refs(
            project, [entrypoint_card]
        ),
        "route_utility:symbol_capsule_lookup": _existing_project_refs(
            project, [source_card]
        ),
        "route_utility:graph_context_lookup": _existing_project_refs(
            project, source_refs + test_refs + entrypoint_refs
        ),
        "route_utility:probe_disposition_closure": _existing_project_refs(
            project, source_refs + test_refs + pyproject_refs + entrypoint_refs
        ),
        "route_utility:payload_boundary": _existing_project_refs(
            project, source_refs + test_refs + pyproject_refs + entrypoint_refs
        ),
    }
    ratchet = _route_utility_ratchet(
        project=project,
        tasks=tasks,
        task_surface_refs=task_surface_refs,
        write_state=write_state,
    )
    disposition_counts = _route_utility_counts(tasks)
    pass_count = sum(1 for row in tasks if row.get("correctness") == PASS)
    not_applicable_count = sum(1 for row in tasks if row.get("correctness") == "not_applicable")
    failed_task_count = sum(1 for row in tasks if row.get("correctness") == "blocked")
    return {
        "schema_version": "microcosm_python_route_utility_curriculum_v1",
        "curriculum_id": "microcosm_python_route_utility_curriculum",
        "assay_id": "std_python_microcosm_navigation_assay",
        "target_root": _project_name(project),
        "entry_surface_ref": "atlas/entry_packet.json::python_navigation_route",
        "route_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::implementation_atlas.python_navigation_assay",
        "task_count": len(tasks),
        "tasks": tasks,
        "ratchet": ratchet,
        "route_utility_metrics": {
            "pass_count": pass_count,
            "not_applicable_count": not_applicable_count,
            "failed_task_count": failed_task_count,
            "max_route_hops": max((len(row.get("route_hops", [])) for row in tasks), default=0),
            "all_failures_disposed": all(row.get("disposition") for row in tasks),
            "known_route_id_count": len(route_ids),
            "stale_task_count": len(ratchet["stale_task_ids"]),
            "generated_task_count": ratchet["generated_task_count"],
        },
        "disposition_counts": disposition_counts,
        "local_projection_defects": [
            row for row in tasks if row.get("disposition") == "local_projection_defect"
        ],
        "local_source_or_test_defects": [
            row for row in tasks if row.get("disposition") == "local_source_or_test_defect"
        ],
        "macro_standard_amendment_candidates": [
            row for row in tasks if row.get("disposition") == "macro_standard_amendment_candidate"
        ],
        "nothing_to_refine_receipts": [
            {
                "task_id": row.get("task_id"),
                "selected_band": row.get("selected_band"),
                "reentry_condition": row.get("reentry_condition"),
            }
            for row in tasks
            if row.get("disposition") == "nothing_to_refine"
        ],
        "payload_boundary_ok": all(
            row.get("source_bodies_exported") is False for row in path_rows
        ),
        **_source_body_boundary_row(),
        "state_written": write_state,
        "authority": "route_utility_curriculum_is_public_safe_read_model_not_source_or_release_authority",
        "reentry_condition": "rerun after entry route, Python lens, source-span, graph, symbol, or std_python policy changes",
    }


def python_lens(
    project_path: str | Path,
    *,
    write_state: bool = True,
    refresh_architecture: bool = True,
    scan_mode: str = PYTHON_LENS_SCAN_FULL,
) -> dict[str, Any]:
    """Project Python route/readiness signals without exposing source bodies.

    - Teleology: the public Python lens entrypoint that builds the whole route/readiness/coverage/assay read-model over a target project.
    - Guarantee: returns the python_lens payload (path rows, capsules, spans, import edges, coverage, authoring queue, navigation assay, route-utility curriculum, authority ceiling); in write_state mode also writes python_lens.json and an event/evidence, source bodies never exported.
    - Fails: an unsupported scan_mode -> raises ValueError; filesystem failures in write mode -> raise OSError.
    - When-needed: building or refreshing the Python navigation read-model for a project; first-screen mode for a cheap summary.
    - Writes: STATE_DIR/python_lens.json, events.jsonl, evidence/python_lens.json (write_state only).
    - Escalates-to: macro std_python.py::navigation_contract and the python-lens tests; python_lens_card for the compact view.
    """
    if scan_mode not in {PYTHON_LENS_SCAN_FULL, PYTHON_LENS_SCAN_FIRST_SCREEN}:
        raise ValueError(f"unsupported Python lens scan mode: {scan_mode}")
    first_screen_summary = scan_mode == PYTHON_LENS_SCAN_FIRST_SCREEN
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = catalog_project(project) if write_state else _project_catalog_payload(project)
    roles = catalog.get("roles", {}) if isinstance(catalog.get("roles"), dict) else {}
    files = catalog.get("files", []) if isinstance(catalog.get("files"), list) else []
    python_files = [
        row
        for row in files
        if isinstance(row, dict) and str(row.get("suffix") or "") == ".py"
    ]
    path_rows: list[dict[str, Any]] = []
    source_span_rows: list[dict[str, Any]] = []
    symbol_capsule_rows: list[dict[str, Any]] = []
    import_edges: list[dict[str, Any]] = []
    parse_error_rows: list[dict[str, Any]] = []
    module_docstring_refs: list[str] = []
    for row in python_files:
        rel = str(row.get("path") or "")
        text = ""
        if first_screen_summary:
            text = _read_text_prefix(
                project / rel,
                limit=PYTHON_LENS_FIRST_SCREEN_PREFIX_BYTES,
            )
            span_projection = {
                "parse_status": "deferred_first_screen_summary",
                "module_has_docstring": False,
                "source_span_rows": [],
                "symbol_capsule_rows": [],
                "import_edges": [],
            }
        else:
            text = _read_text_prefix(project / rel, limit=None)
            span_projection = _python_span_projection(rel, text)
        source_span_rows.extend(span_projection["source_span_rows"])
        symbol_capsule_rows.extend(span_projection["symbol_capsule_rows"])
        import_edges.extend(span_projection["import_edges"])
        if span_projection["module_has_docstring"]:
            module_docstring_refs.append(rel)
        parse_error = span_projection.get("parse_error")
        if isinstance(parse_error, dict):
            parse_error_rows.append(parse_error)
        relative_import_count, absolute_import_count = _python_import_counts(text)
        path_rows.append(
            {
                "path": rel,
                "catalog_role": row.get("role"),
                "python_role": _python_lens_role(row),
                "bytes": row.get("bytes", 0),
                "parse_status": span_projection["parse_status"],
                "has_main_guard": "__main__" in text and "__name__" in text,
                "relative_import_count": relative_import_count,
                "absolute_import_count": absolute_import_count,
                **_source_body_boundary_row(),
            }
        )
    package_refs = roles.get("package_manifest", [])
    pyproject_refs = (
        [str(path) for path in package_refs if str(path).endswith("pyproject.toml")]
        if isinstance(package_refs, list)
        else []
    )
    console_entrypoint_rows = _python_console_entrypoint_rows(project, pyproject_refs)
    console_entrypoint_source_refs = [
        str(row["target_ref"])
        for row in console_entrypoint_rows
        if isinstance(row.get("target_ref"), str) and row.get("target_ref")
    ]
    console_entrypoint_declaration_refs = [
        str(row["declaration_ref"])
        for row in console_entrypoint_rows
        if isinstance(row.get("declaration_ref"), str) and row.get("declaration_ref")
    ]
    source_refs = [str(row["path"]) for row in path_rows if row["python_role"] == "source_module"]
    test_refs = [
        str(row["path"])
        for row in path_rows
        if row["python_role"] in {"test_module", "test_support"}
    ]
    main_guard_entrypoint_refs = [
        str(row["path"]) for row in path_rows if row["has_main_guard"]
    ]
    entrypoint_refs = _dedupe_refs(
        main_guard_entrypoint_refs, console_entrypoint_source_refs
    )
    entrypoint_visibility_refs = _dedupe_refs(
        entrypoint_refs, console_entrypoint_declaration_refs
    )
    package_roots = sorted(
        {
            root
            for root in (_python_package_root(str(row.get("path") or "")) for row in path_rows)
            if root
        }
    )
    checks = [
        {
            "check_id": "pyproject_declared",
            "status": PASS if pyproject_refs else "missing",
            "grounded_refs": pyproject_refs,
        },
        {
            "check_id": "python_source_visible",
            "status": PASS if source_refs or package_roots else "missing",
            "grounded_refs": source_refs[:12] or package_roots[:12],
        },
        {
            "check_id": "python_tests_visible",
            "status": PASS if test_refs else "missing",
            "grounded_refs": test_refs[:12],
        },
        {
            "check_id": "python_entrypoint_visible",
            "status": PASS if entrypoint_visibility_refs else "missing",
            "grounded_refs": entrypoint_visibility_refs[:12],
        },
        {
            "check_id": "python_package_roots_visible",
            "status": PASS if package_roots else "missing",
            "grounded_refs": package_roots,
        },
    ]
    route_rows = [
        _python_route(
            "python_package_metadata_route",
            "Inspect Python package metadata",
            pyproject_refs,
            PASS if pyproject_refs else "missing",
        ),
        _python_route(
            "python_source_core_route",
            "Inspect Python source core",
            source_refs or package_roots,
            PASS if source_refs or package_roots else "missing",
        ),
        _python_route(
            "python_test_behavior_route",
            "Inspect Python behavior tests",
            test_refs,
            PASS if test_refs else "missing",
        ),
        _python_route(
            "python_entrypoint_route",
            "Inspect Python entrypoint declarations",
            entrypoint_visibility_refs,
            PASS if entrypoint_visibility_refs else "missing",
        ),
    ]
    route_probe_tasks = _python_route_probe_tasks(route_rows)
    probe_dispositions = _python_probe_disposition_rows(route_probe_tasks, parse_error_rows)
    disposition_counts = _disposition_counts(probe_dispositions)
    depth_band_coverage = {
        "module_docs": len(module_docstring_refs),
        "file_card": len(path_rows),
        "symbol_capsule": len(symbol_capsule_rows),
        "graph_context": len(import_edges),
        "source_span": len(source_span_rows),
    }
    self_description_coverage = _python_self_description_coverage(
        symbol_capsule_rows,
        module_docstring_refs,
        len(path_rows),
        deferred=first_screen_summary,
    )
    authoring_queue = _code_lens_authoring_queue(
        symbol_capsule_rows,
        manifest_custody_paths=_load_manifest_custody_paths(project),
    )
    navigation_assay = {
        "schema_version": "microcosm_python_navigation_assay_v1",
        "assay_id": "std_python_microcosm_navigation_assay",
        "target_surface": "project_python_route_lens",
        "standard_ref": "macro:codex/standards/std_python.py::navigation_contract",
        "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
        "adapter_bands_quarantined": [
            "cluster_flag",
            "flag",
            "card",
            "source_span",
        ],
        "depth_band_coverage": depth_band_coverage,
        "self_description_coverage": self_description_coverage,
        "route_probe_tasks": route_probe_tasks,
        "probe_dispositions": probe_dispositions,
        "probe_disposition_counts": disposition_counts,
        "standard_amendment_candidates": [
            row
            for row in probe_dispositions
            if row.get("outcome") == "standard_amendment_candidate"
        ],
        "file_local_defect_count": disposition_counts["file_local_defect"],
        "standard_amendment_candidate_count": disposition_counts["standard_amendment_candidate"],
        "nothing_to_refine_count": disposition_counts["nothing_to_refine"],
        "source_span_count": len(source_span_rows),
        "symbol_capsule_count": len(symbol_capsule_rows),
        "graph_edge_count": len(import_edges),
        "parse_error_count": len(parse_error_rows),
        "route_utility_curriculum_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum",
        "route_utility_ratchet_ref": (
            f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum.ratchet"
        ),
        "authority": "generated_project_local_assay_not_std_python_source_authority",
        "reentry_condition": "rerun after Python file, catalog, route-readiness, or std_python ladder changes",
    }
    primary_source_spans = [
        str(row.get("span_id"))
        for row in source_span_rows
        if isinstance(row, dict) and row.get("span_id")
    ][:12]
    python_navigation_route = {
        "route_id": "std_python_microcosm_navigation_assay",
        "surface_id": "project_python_lens",
        "command": "microcosm python-lens <project>",
        "endpoint": "/project/python-lens",
        "assay_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
        "implementation_atlas_ref": (
            f"{STATE_DIR}/{PYTHON_LENS_STATE}"
            "::implementation_atlas.python_navigation_assay"
        ),
        "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
        "depth_selection": [
            {
                "intent": "project_python_orientation",
                "start_band": "file_card",
                "drilldown_when": "task requires exact function, class, import edge, or proof span",
            },
            {
                "intent": "symbol_or_dependency_question",
                "start_band": "symbol_capsule",
                "drilldown_when": "graph edge or caller/import context decides the next file",
            },
            {
                "intent": "mutation_or_proof_question",
                "start_band": "source_span",
                "drilldown_when": "exact source locator is required without exporting bodies",
            },
        ],
        "probe_disposition_counts": disposition_counts,
        "route_utility_curriculum_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum",
        "route_utility_ratchet_ref": (
            f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum.ratchet"
        ),
        **_source_body_boundary_row(),
        "authority": "route_selector_over_project_local_read_model_not_release_or_static_analysis_authority",
    }
    implementation_atlas = {
        "schema_version": "microcosm_project_implementation_atlas_v1",
        "source_surface": "project_python_route_lens",
        "python_navigation_assay": {
            "assay_id": navigation_assay["assay_id"],
            "assay_ref": python_navigation_route["assay_ref"],
            "route_id": python_navigation_route["route_id"],
            "command": python_navigation_route["command"],
            "endpoint": python_navigation_route["endpoint"],
            "canonical_depth_ladder": STD_PYTHON_NAVIGATION_LADDER,
            "depth_band_coverage": depth_band_coverage,
            "self_description_coverage": self_description_coverage,
            "file_card_count": len(path_rows),
            "symbol_capsule_count": len(symbol_capsule_rows),
            "graph_edge_count": len(import_edges),
            "source_span_count": len(source_span_rows),
            "route_probe_task_count": len(route_probe_tasks),
            "probe_disposition_counts": disposition_counts,
            "route_utility_curriculum_ref": (
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum"
            ),
            "route_utility_ratchet_ref": (
                f"{STATE_DIR}/{PYTHON_LENS_STATE}::route_utility_curriculum.ratchet"
            ),
            "standard_amendment_candidate_count": disposition_counts[
                "standard_amendment_candidate"
            ],
            "file_local_defect_count": disposition_counts["file_local_defect"],
            "nothing_to_refine_count": disposition_counts["nothing_to_refine"],
            "parse_error_count": len(parse_error_rows),
            "primary_code_cards": (
                source_refs
                or package_roots
                or [str(row["path"]) for row in path_rows]
            )[:12],
            "primary_source_spans": primary_source_spans,
            **_source_body_boundary_row(),
            "authority": navigation_assay["authority"],
            "reentry_condition": navigation_assay["reentry_condition"],
        },
    }
    route_utility_curriculum = _python_route_utility_curriculum(
        project=project,
        path_rows=path_rows,
        source_refs=source_refs,
        test_refs=test_refs,
        pyproject_refs=pyproject_refs,
        entrypoint_refs=entrypoint_refs,
        source_span_rows=source_span_rows,
        symbol_capsule_rows=symbol_capsule_rows,
        import_edges=import_edges,
        route_rows=route_rows,
        probe_dispositions=probe_dispositions,
        parse_error_rows=parse_error_rows,
        write_state=write_state,
    )
    navigation_assay["route_utility_task_count"] = route_utility_curriculum["task_count"]
    navigation_assay["route_utility_disposition_counts"] = route_utility_curriculum[
        "disposition_counts"
    ]
    navigation_assay["route_utility_ratchet_status"] = route_utility_curriculum[
        "ratchet"
    ]["last_run_result"]
    navigation_assay["route_utility_stale_task_count"] = len(
        route_utility_curriculum["ratchet"]["stale_task_ids"]
    )
    python_navigation_route["route_utility_curriculum_ref"] = navigation_assay[
        "route_utility_curriculum_ref"
    ]
    python_navigation_route["route_utility_ratchet_ref"] = navigation_assay[
        "route_utility_ratchet_ref"
    ]
    implementation_atlas["python_navigation_assay"]["route_utility_task_count"] = (
        route_utility_curriculum["task_count"]
    )
    implementation_atlas["python_navigation_assay"]["route_utility_disposition_counts"] = (
        route_utility_curriculum["disposition_counts"]
    )
    implementation_atlas["python_navigation_assay"]["route_utility_ratchet_status"] = (
        route_utility_curriculum["ratchet"]["last_run_result"]
    )
    implementation_atlas["python_navigation_assay"]["route_utility_stale_task_count"] = (
        len(route_utility_curriculum["ratchet"]["stale_task_ids"])
    )
    payload = {
        **_base_payload("microcosm_project_python_lens_v1", project),
        "lens_id": "project_python_route_lens",
        "command": "microcosm python-lens <project>",
        "scan_mode": scan_mode,
        "full_lens_command": "microcosm python-lens --full <project>",
        "compact_lens_command": "microcosm python-lens <project>",
        "first_screen_summary": first_screen_summary,
        "deferred_full_scan": first_screen_summary,
        "state_file_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "public_claim": (
            "Microcosm exposes Python project route readiness as path-level metadata "
            "without source bodies, provider calls, or source mutation."
        ),
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "payload_boundary": _project_python_lens_payload_boundary(
            "microcosm python-lens <project>"
        ),
        "safe_to_show": {
            "project_source_bodies_omitted": True,
            "python_lens_rows_are_public_payload_boundary_rows": True,
            "public_refs_are_drilldowns_not_replacements": True,
        },
        "python_file_count": len(path_rows),
        "console_entrypoint_count": len(console_entrypoint_rows),
        "console_entrypoint_rows": console_entrypoint_rows,
        "console_entrypoint_source_refs": console_entrypoint_source_refs,
        "package_roots": package_roots,
        "path_rows": path_rows,
        "symbol_capsule_rows": symbol_capsule_rows,
        "source_span_rows": source_span_rows,
        "graph_context_edges": import_edges,
        "source_span_count": len(source_span_rows),
        "symbol_capsule_count": len(symbol_capsule_rows),
        "graph_edge_count": len(import_edges),
        "self_description_coverage": self_description_coverage,
        "authoring_queue": authoring_queue,
        "self_description_contract": {
            "schema_version": "microcosm_python_self_description_contract_v1",
            "summary": (
                "Every Python symbol capsule is classified by self_description_band "
                "(authored | locator_only) and an un-gameable quality_tier "
                "(locator_only < authored_bare < authored_minimal < "
                "authored_contract < authored_routing). Authored capsules expose "
                "which std_python contract atoms their docstring names. The "
                "authoring_queue ranks owned symbols below the real-coverage floor "
                "by release criticality so a usage-funded campaign authors the "
                "spine first. No source bodies are exported and docstring quality "
                "beyond atom presence is not asserted."
            ),
            "donor_standard_ref": "macro:codex/standards/std_python.py::navigation_contract",
            "contract_atom_vocabulary": list(STD_PYTHON_CONTRACT_ATOMS),
            "self_description_bands": [
                SELF_DESCRIPTION_BAND_AUTHORED,
                SELF_DESCRIPTION_BAND_LOCATOR_ONLY,
            ],
            "quality_tier_ladder": list(SELF_DESCRIPTION_QUALITY_TIERS),
            "real_coverage_floor_tier": SELF_DESCRIPTION_REAL_COVERAGE_FLOOR_TIER,
            "criticality_classes": list(CODE_LENS_CRITICALITY_CLASSES),
            "source_classes_tracked": True,
            "promotion_residual": (
                "standalone std_microcosm_code_lens.json + TypeScript/JavaScript "
                "language adapters + organ-scoped organ-code-lens route + authored "
                "prose-atom export policy + usage-funded authoring campaign remain "
                "captured WorkItems"
            ),
            "authority": (
                "inline_code_lens_self_description_contract_not_release_or_"
                "static_analysis_authority"
            ),
        },
        "readiness_checks": checks,
        "passing_check_count": sum(1 for row in checks if row["status"] == PASS),
        "missing_check_count": sum(1 for row in checks if row["status"] != PASS),
        "route_rows": route_rows,
        "navigation_assay": navigation_assay,
        "python_navigation_route": python_navigation_route,
        "implementation_atlas": implementation_atlas,
        "route_utility_curriculum": route_utility_curriculum,
        "ready_route_count": sum(1 for row in route_rows if row["readiness"] == PASS),
        "standard_refs": [
            "macro:codex/standards/std_python.py::navigation_contract",
            "macro:codex/standards/std_navigation_population_acceptance.json::probe_disposition_contract",
            "standards/std_microcosm_route_decision.json",
            "standards/std_microcosm_source_capsule.json",
            "standards/std_microcosm_evidence_cell.json",
        ],
        "authority_ceiling": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutated": False,
            "source_bodies_exported": False,
            "static_analysis_authority_claim": False,
            "source_span_authority_claim": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "The Python lens is a public-safe path, source-span, and route-readiness "
            "read-model. It does not execute Python, infer correctness, export source "
            "bodies, mutate source, call providers, or claim production/package quality."
        ),
        "state_written": write_state,
    }
    if not write_state:
        payload["evidence_ref"] = None
        payload["event_id"] = None
        return payload

    write_json_atomic(_state_dir(project) / PYTHON_LENS_STATE, payload)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "project.python_lens",
        PASS,
        python_file_count=len(path_rows),
        python_lens_ref=f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/python_lens.json",
    )
    _append_event(project, event)
    payload["event_id"] = event["event_id"]
    payload["evidence_ref"] = _write_evidence(
        project,
        "python_lens",
        {**payload, "event_id": event["event_id"]},
    )
    write_json_atomic(_state_dir(project) / PYTHON_LENS_STATE, payload)
    return payload


def python_lens_card(
    project_path: str | Path,
    *,
    write_state: bool = True,
    refresh_architecture: bool = True,
) -> dict[str, Any]:
    """Emit a compact public first-contact Python lens card.

    - Teleology: the public compact card over the Python lens for cheap first contact, deferring the full source-span graph.
    - Guarantee: returns a card payload (file/route counts, bounded path preview, coverage + queue cards, navigation-assay summary) by running python_lens in first-screen mode; source bodies never exported.
    - Fails: filesystem failures in write mode -> raise OSError (inherited from python_lens).
    - When-needed: first contact with a project before exact spans/symbols/imports are required.
    - Writes: same state as python_lens when write_state is True (first-screen scan).
    - Escalates-to: python_lens (``microcosm python-lens --full``) for the full rows.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    lens = python_lens(
        project,
        write_state=write_state,
        refresh_architecture=refresh_architecture,
        scan_mode=PYTHON_LENS_SCAN_FIRST_SCREEN,
    )
    path_rows = lens.get("path_rows", [])
    if not isinstance(path_rows, list):
        path_rows = []
    route_rows = lens.get("route_rows", [])
    if not isinstance(route_rows, list):
        route_rows = []
    checks = lens.get("readiness_checks", [])
    if not isinstance(checks, list):
        checks = []
    navigation_assay = lens.get("navigation_assay", {})
    if not isinstance(navigation_assay, dict):
        navigation_assay = {}
    route_curriculum = lens.get("route_utility_curriculum", {})
    if not isinstance(route_curriculum, dict):
        route_curriculum = {}
    ratchet = route_curriculum.get("ratchet", {})
    if not isinstance(ratchet, dict):
        ratchet = {}
    route_metrics = route_curriculum.get("route_utility_metrics", {})
    if not isinstance(route_metrics, dict):
        route_metrics = {}

    payload = {
        **_base_payload("microcosm_project_python_lens_card_v1", project),
        "card_id": "project_python_lens_card",
        "lens_id": lens.get("lens_id"),
        "command": "microcosm python-lens <project>",
        "full_lens_command": "microcosm python-lens --full <project>",
        "scan_mode": lens.get("scan_mode"),
        "deferred_full_scan": True,
        "state_file_ref": lens.get("state_file_ref"),
        "state_written": lens.get("state_written"),
        "evidence_ref": lens.get("evidence_ref"),
        "event_id": lens.get("event_id"),
        "public_claim": lens.get("public_claim"),
        "source_open_body_policy": SOURCE_OPEN_BODY_POLICY,
        "unsafe_payload_bodies_in_receipt": False,
        "payload_boundary": _project_python_lens_payload_boundary(
            "microcosm python-lens <project>"
        ),
        "safe_to_show": {
            "project_source_bodies_omitted": True,
            "python_lens_rows_are_public_payload_boundary_rows": True,
            "public_refs_are_drilldowns_not_replacements": True,
            "full_source_span_graph_deferred": True,
        },
        "python_file_count": lens.get("python_file_count", 0),
        "package_roots": lens.get("package_roots", []),
        "path_preview_limit": PYTHON_LENS_CARD_PREVIEW_LIMIT,
        "path_preview": path_rows[:PYTHON_LENS_CARD_PREVIEW_LIMIT],
        "omitted_path_row_count": max(
            0, len(path_rows) - PYTHON_LENS_CARD_PREVIEW_LIMIT
        ),
        "source_span_count": lens.get("source_span_count", 0),
        "symbol_capsule_count": lens.get("symbol_capsule_count", 0),
        "graph_edge_count": lens.get("graph_edge_count", 0),
        "self_description_coverage": _self_description_coverage_card(
            lens.get("self_description_coverage", {})
        ),
        "authoring_queue": _authoring_queue_card(lens.get("authoring_queue", {})),
        "self_description_contract_ref": {
            "schema_version": lens.get("self_description_contract", {}).get(
                "schema_version"
            ),
            "full_lens_command": "microcosm python-lens --full <project>",
            "note": "full self_description_contract is in the --full lens payload",
        },
        "readiness_checks": checks,
        "passing_check_count": lens.get("passing_check_count", 0),
        "missing_check_count": lens.get("missing_check_count", 0),
        "route_rows": route_rows,
        "ready_route_count": lens.get("ready_route_count", 0),
        "navigation_assay": {
            "assay_id": navigation_assay.get("assay_id"),
            "canonical_depth_ladder": navigation_assay.get(
                "canonical_depth_ladder", []
            ),
            "depth_band_coverage": navigation_assay.get("depth_band_coverage", {}),
            "self_description_coverage": navigation_assay.get(
                "self_description_coverage", {}
            ),
            "probe_disposition_counts": navigation_assay.get(
                "probe_disposition_counts", {}
            ),
            "route_utility_curriculum_ref": navigation_assay.get(
                "route_utility_curriculum_ref"
            ),
            "route_utility_ratchet_ref": navigation_assay.get(
                "route_utility_ratchet_ref"
            ),
            "route_utility_task_count": navigation_assay.get(
                "route_utility_task_count", 0
            ),
            "route_utility_ratchet_status": navigation_assay.get(
                "route_utility_ratchet_status"
            ),
            "route_utility_stale_task_count": navigation_assay.get(
                "route_utility_stale_task_count", 0
            ),
            "authority": navigation_assay.get("authority"),
            "reentry_condition": navigation_assay.get("reentry_condition"),
        },
        "python_navigation_route": lens.get("python_navigation_route", {}),
        "route_utility_curriculum": {
            "curriculum_id": route_curriculum.get("curriculum_id"),
            "task_count": route_curriculum.get("task_count", 0),
            "disposition_counts": route_curriculum.get("disposition_counts", {}),
            "route_utility_metrics": {
                "failed_task_count": route_metrics.get("failed_task_count", 0),
                "not_applicable_count": route_metrics.get("not_applicable_count", 0),
                "stale_task_count": route_metrics.get("stale_task_count", 0),
            },
            "ratchet": {
                "last_run_result": ratchet.get("last_run_result"),
                "stale_task_ids": ratchet.get("stale_task_ids", []),
            },
            "payload_boundary_ok": route_curriculum.get("payload_boundary_ok"),
            "source_bodies_exported": route_curriculum.get("source_bodies_exported"),
        },
        "standard_refs": lens.get("standard_refs", []),
        "authority_ceiling": lens.get("authority_ceiling", {}),
        "anti_claim": lens.get("anti_claim"),
        "reader_action": (
            "Use this compact lens for first contact. Run "
            "`microcosm python-lens --full <project>` only when exact source-span, "
            "symbol, import, or graph rows are needed."
        ),
    }
    return payload


def _load_work_items(project: Path) -> list[dict[str, Any]]:
    """Load the project's work-item rows from work_items.json.

    - Teleology: the read side of the project-local work-transaction ledger.
    - Guarantee: returns the list of dict work-item rows; absent/malformed -> [].
    - Fails: malformed JSON -> raises via the strict reader; missing file -> [].
    - Reads: STATE_DIR/work_items.json.
    """
    payload = _read_project_json(project, "work_items.json")
    rows = payload.get("work_items", [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _write_work_items(project: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically persist the work-item rows back to work_items.json.

    - Teleology: the write side of the project-local work-transaction ledger.
    - Guarantee: writes a work_items_v1 payload (envelope + count + rows) atomically; returns None.
    - Fails: write failure -> raises OSError.
    - Writes: STATE_DIR/work_items.json.
    """
    payload = {
        **_base_payload("microcosm_project_work_items_v1", project),
        "work_item_count": len(rows),
        "work_items": rows,
    }
    write_json_atomic(_state_dir(project) / "work_items.json", payload)


def create_work(
    project_path: str | Path,
    route_id: str | None = None,
    *,
    refresh_architecture: bool = True,
) -> dict[str, Any]:
    """Create a work-transaction record from a selected (or first) project route.

    - Teleology: the public step that opens a governed, simulate-only work transaction bound to a route snapshot.
    - Guarantee: appends a created/selected/planned work row, writes work_items.json, emits a work.create event/evidence, and returns work_id/route_id/refs; source_files_mutated stays False.
    - Fails: an unknown route_id -> returns {"status":"blocked","reason":"route_not_found"} (no exception); filesystem failures -> raise OSError.
    - When-needed: starting a local work transaction over a chosen route.
    - Writes: STATE_DIR/work_items.json, events.jsonl, evidence/work_create_<id>.json.
    - Non-goal: simulate-only governance; does not mutate source or authorize release.
    - Escalates-to: run_work, which closes the transaction.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    route_payload = propose_routes(project, refresh_architecture=False)
    routes = route_payload.get("routes", [])
    route_rows = [row for row in routes if isinstance(row, dict)]
    if route_id:
        selected = next((row for row in route_rows if row.get("route_id") == route_id), None)
    else:
        selected = route_rows[0] if route_rows else None
    if not selected:
        return {
            **_base_payload("microcosm_project_work_create_result_v1", project),
            "status": "blocked",
            "reason": "route_not_found",
            "route_id": route_id,
        }
    rows = _load_work_items(project)
    work_id = f"work_{len(rows) + 1:04d}"
    contracts = architecture_kernel.work_contracts_for_route(selected, work_id)
    row = {
        "work_id": work_id,
        "route_id": selected["route_id"],
        "status": "created",
        "transaction_state": "created",
        "created_at": utc_now(),
        "grounded_refs": selected.get("grounded_refs", []),
        "route_snapshot": selected,
        "transaction_policy": "simulate_project_local_only",
        "workflow_definition_ref": f"{STATE_DIR}/routes.json::{selected['route_id']}",
        "workflow_execution_ref": f"{STATE_DIR}/work_items.json::{work_id}",
        "satisfaction_contract": contracts["satisfaction_contract"],
        "integration_contract": contracts["integration_contract"],
        "residual_policy": contracts["residual_policy"],
        "event_refs": [],
        "evidence_refs": [],
        "state_history": [
            {
                "state": "created",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Work transaction record created from a route snapshot.",
            },
            {
                "state": "selected",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Route selected for deterministic local simulation.",
            },
            {
                "state": "planned",
                "span": "work.create",
                "created_at": utc_now(),
                "note": "Source mutation is not authorized; run step will simulate governance only.",
            },
        ],
        "source_files_mutated": False,
    }
    rows.append(row)
    _write_work_items(project, rows)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "work.create",
        PASS,
        work_id=work_id,
        route_id=selected["route_id"],
        work_items_ref=f"{STATE_DIR}/work_items.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/work_create_{work_id}.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(
        project,
        f"work_create_{work_id}",
        {
            **_base_payload("microcosm_project_work_create_receipt_v1", project),
            "event_id": event["event_id"],
            "work_item": row,
            "work_id": work_id,
            "route_id": selected["route_id"],
        },
    )
    row["event_refs"].append(
        {
            "event_id": event["event_id"],
            "span": event["span"],
            "status": event["status"],
        }
    )
    row["evidence_refs"].append(evidence_ref)
    _write_work_items(project, rows)
    return {
        **_base_payload("microcosm_project_work_create_result_v1", project),
        "work_id": work_id,
        "route_id": selected["route_id"],
        "work_items_ref": f"{STATE_DIR}/work_items.json",
        "evidence_ref": evidence_ref,
    }


def run_work(
    project_path: str | Path,
    work_id: str | None = None,
    *,
    refresh_architecture: bool = True,
) -> dict[str, Any]:
    """Run (close) a work transaction as a deterministic project-local simulation.

    - Teleology: the public step that executes a governed simulate-only transaction over a route snapshot and closes it with evidence.
    - Guarantee: closes the selected (or first open) work item through executed_simulation->closed, writes a work.run event/evidence and a closeout; returns transaction_status pass and the state_machine; idempotent replay for already-closed items; source_files_mutated False.
    - Fails: no resolvable work item -> returns {"status":"blocked","reason":"work_item_not_found"} (no exception); filesystem failures -> raise OSError.
    - When-needed: completing/closing a project-local work transaction.
    - Writes: STATE_DIR/work_items.json, events.jsonl, evidence/work_run_<id>.json.
    - Non-goal: simulated governance only; does not mutate source, call providers, or authorize release.
    - Escalates-to: explain_route and observe_project for the resulting causal chain.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    rows = _load_work_items(project)
    if not rows:
        created = create_work(project, refresh_architecture=False)
        rows = _load_work_items(project)
        work_id = str(created.get("work_id") or "")
    selected = next((row for row in rows if row.get("work_id") == work_id), None) if work_id else None
    if selected is None:
        selected = next((row for row in rows if row.get("status") != "closed"), rows[-1] if rows else None)
    if selected is None:
        return {
            **_base_payload("microcosm_project_work_run_result_v1", project),
            "status": "blocked",
            "reason": "work_item_not_found",
            "work_id": work_id,
        }
    if selected.get("status") == "closed" and isinstance(selected.get("closeout"), dict):
        history = selected.get("state_history", [])
        state_machine = [
            str(row.get("state"))
            for row in history
            if isinstance(row, dict) and row.get("state")
        ]
        evidence_refs = selected.get("evidence_refs", [])
        latest_evidence_ref = evidence_refs[-1] if isinstance(evidence_refs, list) and evidence_refs else None
        return {
            **_base_payload("microcosm_project_work_run_result_v1", project),
            "work_id": selected["work_id"],
            "route_id": selected["route_id"],
            "transaction_status": PASS,
            "idempotent_replay": True,
            "state_machine": state_machine,
            "work_items_ref": f"{STATE_DIR}/work_items.json",
            "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
            "evidence_ref": latest_evidence_ref,
        }
    contracts = architecture_kernel.work_contracts_for_route(
        selected.get("route_snapshot", {"route_id": selected.get("route_id")}),
        str(selected.get("work_id") or ""),
    )
    selected.setdefault("satisfaction_contract", contracts["satisfaction_contract"])
    selected.setdefault("integration_contract", contracts["integration_contract"])
    selected.setdefault("residual_policy", contracts["residual_policy"])
    selected.setdefault("event_refs", [])
    selected.setdefault("evidence_refs", [])
    selected["status"] = "closed"
    selected["transaction_state"] = "closed"
    selected["closed_at"] = utc_now()
    history = selected.get("state_history", [])
    if not isinstance(history, list):
        history = []
    history.extend(
        [
            {
                "state": "executed_simulation",
                "span": "work.run",
                "created_at": utc_now(),
                "note": "Executed deterministic project-local simulation over route snapshot.",
            },
            {
                "state": "closed",
                "span": "work.run",
                "created_at": utc_now(),
                "note": "Closed with generated evidence and no source mutation.",
            },
        ]
    )
    selected["state_history"] = history
    selected["result"] = {
        "status": PASS,
        "summary": "Simulated a governed local transaction over project catalog state.",
        "definition_execution_separated": True,
        "workflow_definition_ref": selected.get("workflow_definition_ref"),
        "workflow_execution_ref": selected.get("workflow_execution_ref"),
        "source_files_mutated": False,
    }
    selected["closeout"] = {
        "status": PASS,
        "satisfaction_contract_met": True,
        "integration_contract_met": True,
        "residuals": [],
        "next_actions": [
            {
                "action_id": "inspect_route_explanation",
                "command": f"microcosm explain <project> {selected['route_id']}",
            },
            {
                "action_id": "inspect_event_stream",
                "command": "microcosm observe <project>",
            },
        ],
        "authority_boundary": "project_local_closeout_not_global_doctrine_promotion",
    }
    _write_work_items(project, rows)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event = _event(
        project,
        "work.run",
        PASS,
        work_id=selected["work_id"],
        route_id=selected["route_id"],
        work_items_ref=f"{STATE_DIR}/work_items.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/work_run_{selected['work_id']}.json",
    )
    _append_event(project, event)
    evidence_ref = _write_evidence(
        project,
        f"work_run_{selected['work_id']}",
        {
            **_base_payload("microcosm_project_work_run_receipt_v1", project),
            "event_id": event["event_id"],
            "work_item": selected,
            "work_id": selected["work_id"],
            "route_id": selected["route_id"],
            "transaction_status": PASS,
        },
    )
    event_row = {
        "event_id": event["event_id"],
        "span": event["span"],
        "status": event["status"],
    }
    if isinstance(selected.get("event_refs"), list):
        selected["event_refs"].append(event_row)
    if isinstance(selected.get("evidence_refs"), list):
        selected["evidence_refs"].append(evidence_ref)
    selected["closeout"]["event_ref"] = f"{STATE_DIR}/{EVENT_STREAM}::{event['event_id']}"
    selected["closeout"]["evidence_ref"] = evidence_ref
    _write_work_items(project, rows)
    return {
        **_base_payload("microcosm_project_work_run_result_v1", project),
        "work_id": selected["work_id"],
        "route_id": selected["route_id"],
        "transaction_status": PASS,
        "state_machine": ["created", "selected", "planned", "executed_simulation", "closed"],
        "work_items_ref": f"{STATE_DIR}/work_items.json",
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "evidence_ref": evidence_ref,
    }


def _run_work_for_route(
    project: Path,
    route_id: str,
    *,
    refresh_architecture: bool = True,
) -> dict[str, Any]:
    """Ensure a work item exists for a route, then run it.

    - Teleology: the compile-loop helper that drives one route's work transaction to closed.
    - Guarantee: reuses an open/last work item for the route or creates one, then returns run_work's result.
    - Fails: a blocked create (route_not_found) is returned as-is; otherwise inherits run_work's failure envelope.
    - Reads/Writes: work_items.json and the work event/evidence (via create_work/run_work).
    """
    rows = _load_work_items(project)
    matching_rows = [
        row for row in rows if str(row.get("route_id") or "") == route_id
    ]
    selected = next(
        (row for row in matching_rows if row.get("status") != "closed"),
        matching_rows[-1] if matching_rows else None,
    )
    if selected is None:
        created = create_work(project, route_id, refresh_architecture=False)
        if created.get("status") == "blocked":
            return created
        work_id = str(created.get("work_id") or "")
    else:
        work_id = str(selected.get("work_id") or "")
    return run_work(project, work_id, refresh_architecture=refresh_architecture)


def _work_row_for_chain(
    project: Path,
    *,
    route_id: str,
    work_id: Any,
) -> dict[str, Any]:
    """Select the work row that backs a reader causal-chain card.

    - Teleology: resolves which work item to cite in the route->work->event->evidence lineage.
    - Guarantee: returns the work row matching work_id, else the route's closed (or last) row, else {}.
    - Fails: never raises (lookups only).
    - Reads: STATE_DIR/work_items.json.
    """
    rows = _load_work_items(project)
    if work_id:
        selected = next((row for row in rows if row.get("work_id") == work_id), None)
        if selected is not None:
            return selected
    route_rows = [row for row in rows if str(row.get("route_id") or "") == route_id]
    return next(
        (row for row in route_rows if row.get("status") == "closed"),
        route_rows[-1] if route_rows else {},
    )


def _dedupe_refs(*groups: Any) -> list[str]:
    """Flatten string/list ref groups into one order-preserving deduped list.

    - Teleology: merges grounded-ref/evidence-ref groups from multiple sources without duplicates or empties.
    - Guarantee: returns the non-empty string refs across all groups in first-seen order, each once; non-str/non-list groups contribute nothing.
    - Fails: never raises (filtering only).
    - Reads: only the supplied argument groups.
    """
    refs: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            candidates = [group]
        elif isinstance(group, list):
            candidates = group
        else:
            candidates = []
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate:
                continue
            if candidate in seen:
                continue
            refs.append(candidate)
            seen.add(candidate)
    return refs


def _state_names(history: Any) -> list[str]:
    """Extract the ordered state names from a work-item state_history.

    - Teleology: flattens a transaction's lifecycle history into a compact state-machine list for chain cards.
    - Guarantee: returns the state strings in order; non-list input or stateless rows -> [].
    - Fails: never raises (filtering only).
    - Reads: only the supplied history value.
    """
    if not isinstance(history, list):
        return []
    return [
        str(row.get("state"))
        for row in history
        if isinstance(row, dict) and row.get("state")
    ]


def _reader_causal_chain_card(
    project: Path,
    *,
    route_id: str,
    work_result: dict[str, Any],
    explanation: dict[str, Any],
    observed: dict[str, Any],
    graph: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the reader causal-chain card linking route->work->events->evidence->graph.

    - Teleology: the generated lineage card that lets a reader trace a route through its work transaction, events, evidence, and graph.
    - Guarantee: returns a chain card with selected route/work, state refs, event/evidence ref counts, drilldowns, graph summary, observatory/proof-lab pointers, and an authority boundary; status pass only when route+closed work+explanation+proof all pass, else partial.
    - Fails: never raises (assembly over already-read inputs).
    - Reads: work_items.json (for the backing row); other inputs are passed in.
    - Non-goal: project-local lineage, not release or proof-correctness authority; safe_to_show pins release/provider/proof False.
    """
    proof = explanation.get("causal_chain_proof")
    proof = proof if isinstance(proof, dict) else {}
    work_id = work_result.get("work_id") or proof.get("selected_work_id")
    work_row = _work_row_for_chain(project, route_id=route_id, work_id=work_id)
    selected_work_id = str(
        work_row.get("work_id") or work_id or proof.get("selected_work_id") or ""
    )
    selected_work_status = (
        work_row.get("status") or proof.get("selected_work_status")
    )
    work_evidence_refs = (
        work_row.get("evidence_refs") if isinstance(work_row, dict) else []
    )
    proof_evidence_refs = proof.get("evidence_refs")
    evidence_refs = _dedupe_refs(
        proof_evidence_refs,
        work_evidence_refs,
        explanation.get("evidence_ref"),
        work_result.get("evidence_ref"),
    )
    proof_event_refs = proof.get("event_refs")
    work_event_refs = work_row.get("event_refs") if isinstance(work_row, dict) else []
    event_ref_count = proof.get("event_ref_count")
    if not isinstance(event_ref_count, int):
        event_ref_count = (
            len(proof_event_refs)
            if isinstance(proof_event_refs, list)
            else observed.get("event_count", 0)
        )
    evidence_ref_count = proof.get("evidence_ref_count")
    if not isinstance(evidence_ref_count, int):
        evidence_ref_count = len(evidence_refs) or evidence.get("evidence_count", 0)
    state_history = (
        proof.get("state_history")
        if isinstance(proof.get("state_history"), list)
        else _state_names(
            work_row.get("state_history") if isinstance(work_row, dict) else []
        )
    )
    status = (
        PASS
        if route_id
        and selected_work_id
        and selected_work_status == "closed"
        and explanation.get("status") == PASS
        and proof.get("status") == PASS
        else "partial"
    )
    return {
        "schema_version": "microcosm_compile_reader_causal_chain_v1",
        "status": status,
        "selected_route_id": route_id or None,
        "selected_route_ref": (
            f"{STATE_DIR}/routes.json::{route_id}" if route_id else None
        ),
        "selected_work_id": selected_work_id or None,
        "selected_work_status": selected_work_status,
        "work_state_ref": (
            f"{STATE_DIR}/work_items.json::{selected_work_id}"
            if selected_work_id
            else f"{STATE_DIR}/work_items.json"
        ),
        "route_explanation_ref": (
            f"{STATE_DIR}/explanations/{route_id}.json" if route_id else None
        ),
        "route_explanation_command": (
            f"microcosm explain <project> {route_id}"
            if route_id
            else "microcosm explain <project> <selected_route_id>"
        ),
        "event_log_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "event_ref_count": event_ref_count,
        "work_event_refs": work_event_refs if isinstance(work_event_refs, list) else [],
        "evidence_refs": evidence_refs,
        "evidence_ref_count": evidence_ref_count,
        "reader_drilldowns": _dedupe_refs(
            proof.get("reader_drilldowns"),
            [
                f"{STATE_DIR}/routes.json",
                f"{STATE_DIR}/work_items.json",
                f"{STATE_DIR}/{EVENT_STREAM}",
                f"{STATE_DIR}/evidence/",
                f"{STATE_DIR}/graph.json",
                f"{STATE_DIR}/explanations/{route_id}.json" if route_id else "",
            ],
        ),
        "state_history": state_history,
        "graph": {
            "graph_ref": graph.get("graph_ref") or f"{STATE_DIR}/graph.json",
            "node_count": graph.get("node_count", 0),
            "edge_count": graph.get("edge_count", 0),
        },
        "observatory": {
            "command": OBSERVATORY_SERVE_COMMAND,
            "bounded_validation_command": OBSERVATORY_BOUNDED_VALIDATION_COMMAND,
            "bounded_validation_request_count": (
                OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT
            ),
            "bounded_validation_rule": OBSERVATORY_BOUNDED_VALIDATION_RULE,
            "compact_endpoint": "/project/observatory-card",
            "expanded_endpoint": "/project/observatory",
            "route_explanation_endpoint": f"/project/explain/{route_id}"
            if route_id
            else "/project/explain/<selected_route_id>",
        },
        "proof_lab": {
            "command": "microcosm proof-lab --out /tmp/microcosm-proof-lab",
            "endpoint": "/proof-lab",
            "role": "first_screen_formal_route_smoke_not_project_correctness_proof",
        },
        "receipts_are_drilldown_evidence": True,
        "source_files_mutated": (
            work_row.get("source_files_mutated") is True
            if isinstance(work_row, dict)
            else False
        ),
        "authority_boundary": (
            proof.get("authority_boundary")
            or "project_local_lineage_not_release_or_proof_correctness_authority"
        ),
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
    }


def _selected_route_id_from_state(project: Path) -> str:
    """Pick the canonical selected route id from persisted routes.json.

    - Teleology: gives observe a stable default route (README onboarding, else first) to anchor the causal chain.
    - Guarantee: returns the readme_onboarding_route id when present, else the first route id, else "".
    - Fails: never raises (read + lookup only).
    - Reads: STATE_DIR/routes.json.
    """
    routes = _read_project_json(project, "routes.json")
    route_rows = [
        row for row in routes.get("routes", []) if isinstance(row, dict)
    ]
    selected_route = next(
        (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
        route_rows[0] if route_rows else {},
    )
    return str(selected_route.get("route_id") or "")


def _observed_reader_causal_chain_card(
    project: Path,
    *,
    observed: dict[str, Any],
) -> dict[str, Any]:
    """Build the causal-chain card for observe from persisted state (no work run).

    - Teleology: lets observe emit lineage purely from already-written state, without mutating work items.
    - Guarantee: resolves the selected route, work row, explanation, graph, and evidence from disk and returns _reader_causal_chain_card over them.
    - Fails: never raises (reads + delegation only).
    - Reads: routes.json, work_items.json, explanations/<route>.json, graph.json, and the evidence listing.
    """
    route_id = _selected_route_id_from_state(project)
    work_row = _work_row_for_chain(project, route_id=route_id, work_id=None)
    explanation = (
        _read_project_json(project, f"explanations/{route_id}.json")
        if route_id
        else {}
    )
    graph = _read_project_json(project, "graph.json")
    evidence = list_evidence(project, limit=0)
    return _reader_causal_chain_card(
        project,
        route_id=route_id,
        work_result=work_row,
        explanation=explanation,
        observed=observed,
        graph=graph,
        evidence=evidence,
    )


def _project_observe_state_write_proof_card(
    project: Path,
    *,
    project_ref: str = "<project>",
) -> dict[str, Any]:
    """Prove which required .microcosm state refs exist before treating observe as the lens.

    - Teleology: makes the state-write handoff auditable by checking the required refs are on disk.
    - Guarantee: returns a proof card with per-ref existence, missing_state_refs, file count, and status pass only when the state dir exists with no missing refs; records that observe does not write microcosm state.
    - Fails: never raises (existence checks are OSError-tolerant).
    - Reads: the project's STATE_DIR tree (routes/work/events/evidence/graph/state_index).
    - Non-goal: a state-presence proof, not release or correctness authority.
    """
    state_root = _state_dir(project)
    state_ref_statuses: dict[str, bool] = {}
    required_state_refs = [
        f"{STATE_DIR}/routes.json",
        f"{STATE_DIR}/work_items.json",
        f"{STATE_DIR}/{EVENT_STREAM}",
        f"{STATE_DIR}/{EVIDENCE_DIR}/",
        f"{STATE_DIR}/graph.json",
        f"{STATE_DIR}/state_index.json",
    ]
    for ref in required_state_refs:
        relative = ref.removeprefix(f"{STATE_DIR}/")
        target = state_root / relative.rstrip("/")
        state_ref_statuses[ref] = _path_exists(target)
    missing_state_refs = [
        ref for ref, exists in state_ref_statuses.items() if not exists
    ]
    state_file_count = _count_files_under(state_root)
    return {
        "schema_version": "microcosm_project_observe_state_write_proof_ref_v1",
        "status": PASS
        if _path_is_dir(state_root) and not missing_state_refs
        else "missing_state_refs",
        "status_scope": "project_local_state_write_handoff",
        "state_dir": STATE_DIR,
        "state_dir_exists": _path_is_dir(state_root),
        "state_file_count": state_file_count,
        "required_state_refs": required_state_refs,
        "missing_state_refs": missing_state_refs,
        "state_ref_statuses": state_ref_statuses,
        "state_write_result_ref": (
            f"microcosm tour --card {project_ref}::state_write_result"
        ),
        "state_write_status_ref": (
            f"microcosm tour --card {project_ref}::front_door_status."
            "surface_statuses.state_write"
        ),
        "state_inspection_status_ref": (
            f"microcosm tour --card {project_ref}::front_door_status."
            "surface_statuses.state_inspection"
        ),
        "status_card_project_state_ref": (
            f"microcosm status --card {project_ref}::front_door.project_state"
        ),
        "tour_card_writes_microcosm_state": True,
        "observe_writes_microcosm_state": False,
        "status_card_writes_microcosm_state": False,
        "source_files_mutated": False,
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "reader_action": (
            "Use these refs to verify that tour --card wrote the local "
            ".microcosm state before treating observe as the causal-chain lens."
        ),
    }


def observe_project(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Observe a project: summarize its event stream and reader causal chain (read-only of work).

    - Teleology: the public read lens that reports what the project's local state already proves, without running new work.
    - Guarantee: returns an observe result with event count/spans/tail, selected route, state-write proof, causal chain, drilldowns, and authority boundary; does not mutate work items.
    - Fails: never raises beyond an optional architecture refresh (which can raise OSError).
    - When-needed: inspecting a project's lineage and event history after compile.
    - Reads: events.jsonl plus routes/work/explanations/graph/evidence state; may write architecture state when refresh_architecture.
    - Escalates-to: observe_project_card for the compact view; compile_project to (re)build state.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    event_summary = _read_event_stream_summary(_state_dir(project) / EVENT_STREAM)
    observed = {
        "event_count": event_summary["event_count"],
        "spans": event_summary["spans"],
        "events": event_summary["events"],
        "event_ref": f"{STATE_DIR}/{EVENT_STREAM}",
        "architecture_ref": f"{STATE_DIR}/architecture.json",
        "state_index_ref": f"{STATE_DIR}/state_index.json",
        "graph_ref": f"{STATE_DIR}/graph.json",
    }
    causal_chain = _observed_reader_causal_chain_card(project, observed=observed)
    project_ref = _project_arg_ref(project_path, project)
    state_write_proof = _project_observe_state_write_proof_card(
        project,
        project_ref=project_ref,
    )
    return {
        **_base_payload("microcosm_project_observe_result_v1", project),
        **observed,
        "project_ref": project_ref,
        "selected_route_id": causal_chain.get("selected_route_id"),
        "state_write_proof": state_write_proof,
        "causal_chain": causal_chain,
        "reader_drilldowns": causal_chain.get("reader_drilldowns", []),
        "work_state_ref": causal_chain.get("work_state_ref"),
        "route_explanation_ref": causal_chain.get("route_explanation_ref"),
        "evidence_ref_count": causal_chain.get("evidence_ref_count", 0),
        "authority_boundary": causal_chain.get("authority_boundary"),
        "safe_to_show": causal_chain.get("safe_to_show", {}),
    }


def observe_project_card(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Emit the compact observe card: state-write proof, spans, and causal-chain summary.

    - Teleology: the public compact first-contact view over observe, deferring full event rows.
    - Guarantee: returns a card with card_status, event/span counts, state-write proof summary, and a causal-chain summary; runs observe_project under the hood.
    - Fails: inherits observe_project's behavior (optional architecture refresh may raise OSError).
    - When-needed: a cheap status check before pulling full observe event rows.
    - Escalates-to: observe_project (``microcosm observe <project>``) for full event rows.
    """
    observed = observe_project(
        project_path,
        refresh_architecture=refresh_architecture,
    )
    causal_chain = observed.get("causal_chain") or {}
    state_write_proof = observed.get("state_write_proof") or {}
    graph = causal_chain.get("graph") or {}
    spans = observed.get("spans") or {}
    return {
        **_base_payload("microcosm_project_observe_card_v1", Path(project_path)),
        "card_status": observed.get("status"),
        "command": f"microcosm observe --card {observed.get('project_ref', '<project>')}",
        "full_command": f"microcosm observe {observed.get('project_ref', '<project>')}",
        "endpoint": None,
        "endpoint_available": False,
        "full_endpoint": "/project/observe",
        "selected_route_id": observed.get("selected_route_id"),
        "event_count": observed.get("event_count", 0),
        "span_count": len(spans),
        "spans": spans,
        "state_write_proof": {
            "status": state_write_proof.get("status"),
            "state_dir_exists": state_write_proof.get("state_dir_exists"),
            "missing_state_refs": state_write_proof.get("missing_state_refs", []),
            "state_file_count": state_write_proof.get("state_file_count", 0),
            "tour_card_writes_microcosm_state": state_write_proof.get(
                "tour_card_writes_microcosm_state"
            ),
            "observe_writes_microcosm_state": state_write_proof.get(
                "observe_writes_microcosm_state"
            ),
            "source_files_mutated": state_write_proof.get("source_files_mutated"),
        },
        "causal_chain_summary": {
            "status": causal_chain.get("status"),
            "selected_work_id": causal_chain.get("selected_work_id"),
            "selected_work_status": causal_chain.get("selected_work_status"),
            "work_state_ref": observed.get("work_state_ref"),
            "route_explanation_ref": observed.get("route_explanation_ref"),
            "evidence_ref_count": observed.get("evidence_ref_count", 0),
            "graph": {
                "node_count": graph.get("node_count", 0),
                "edge_count": graph.get("edge_count", 0),
                "graph_ref": graph.get("graph_ref") or observed.get("graph_ref"),
            },
        },
        "reader_drilldowns": observed.get("reader_drilldowns", []),
        "authority_boundary": observed.get("authority_boundary"),
        "safe_to_show": observed.get("safe_to_show", {}),
        "reader_action": (
            "Use this compact card to confirm state refs, selected route, spans, "
            "and authority boundary; run full_command for event rows."
        ),
    }


def architecture_project(project_path: str | Path) -> dict[str, Any]:
    """Public passthrough that writes the project architecture projection.

    - Teleology: exposes the architecture-kernel projection as a CLI-reachable command.
    - Guarantee: returns architecture_kernel.write_project_architecture's result for the project.
    - Fails: filesystem failures in the kernel -> raise OSError.
    - Writes: STATE_DIR architecture state (delegated to architecture_kernel).
    - Escalates-to: microcosm_core.architecture_kernel.write_project_architecture.
    """
    return architecture_kernel.write_project_architecture(project_path)


def state_graph(
    project_path: str | Path, *, refresh_architecture: bool = True
) -> dict[str, Any]:
    """Build the project state graph, optionally refreshing architecture first.

    - Teleology: exposes the architecture-kernel graph (nodes/edges over project state) as a command.
    - Guarantee: returns architecture_kernel.build_graph's result; refreshes architecture state first when requested.
    - Fails: filesystem failures in the kernel -> raise OSError.
    - Reads/Writes: project architecture state via the kernel (write when refresh_architecture).
    - Escalates-to: microcosm_core.architecture_kernel.build_graph.
    """
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project_path)
    return architecture_kernel.build_graph(project_path)


def explain_route(
    project_path: str | Path,
    route_id: str,
    *,
    refresh_architecture: bool = True,
) -> dict[str, Any]:
    """Explain one route into a persisted causal-chain explanation with event/evidence.

    - Teleology: the public step that materializes a route's explanation and binds it to events and evidence.
    - Guarantee: on a passing kernel explanation, appends a project.explain event, folds event/evidence refs into the explanation and its proof, writes explanations/<route>.json and evidence, and returns the explanation.
    - Fails: a non-pass kernel explanation is returned unchanged (no event/write); filesystem failures -> raise OSError.
    - When-needed: producing the route->work->event->evidence lineage for a chosen route.
    - Writes: STATE_DIR/explanations/<route>.json, events.jsonl, evidence/explain_<route>.json.
    - Escalates-to: microcosm_core.architecture_kernel.explain_route and observe_project for the assembled chain.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    if not _path_is_file(_state_dir(project) / "routes.json"):
        propose_routes(project)
    explanation = architecture_kernel.explain_route(project, route_id)
    if explanation.get("status") != PASS:
        return explanation
    event = _event(
        project,
        "project.explain",
        PASS,
        route_id=route_id,
        explanation_ref=f"{STATE_DIR}/explanations/{route_id}.json",
        evidence_ref=f"{STATE_DIR}/{EVIDENCE_DIR}/explain_{route_id}.json",
    )
    _append_event(project, event)
    event_row = {
        "event_id": event["event_id"],
        "span": event["span"],
        "status": event["status"],
    }
    expected_evidence_ref = f"{STATE_DIR}/{EVIDENCE_DIR}/explain_{route_id}.json"
    explanation["event_id"] = event["event_id"]
    explanation["evidence_ref"] = expected_evidence_ref
    if isinstance(explanation.get("event_refs"), list) and not any(
        isinstance(row, dict) and row.get("event_id") == event["event_id"]
        for row in explanation["event_refs"]
    ):
        explanation["event_refs"].append(event_row)
    if (
        isinstance(explanation.get("evidence_refs"), list)
        and expected_evidence_ref not in explanation["evidence_refs"]
    ):
        explanation["evidence_refs"].append(expected_evidence_ref)
    proof = explanation.get("causal_chain_proof")
    if isinstance(proof, dict):
        proof_events = proof.get("event_refs")
        if isinstance(proof_events, list) and not any(
            isinstance(row, dict) and row.get("event_id") == event["event_id"]
            for row in proof_events
        ):
            proof_events.append(event_row)
            proof["event_ref_count"] = len(proof_events)
        proof_evidence_refs = proof.get("evidence_refs")
        if (
            isinstance(proof_evidence_refs, list)
            and expected_evidence_ref not in proof_evidence_refs
        ):
            proof_evidence_refs.append(expected_evidence_ref)
            proof["evidence_ref_count"] = len(proof_evidence_refs)
    evidence_ref = _write_evidence(project, f"explain_{route_id}", explanation)
    explanation["evidence_ref"] = evidence_ref
    write_json_atomic(_state_dir(project) / "explanations" / f"{route_id}.json", explanation)
    if refresh_architecture:
        architecture_kernel.write_project_architecture(project)
    return explanation


def _count_paths(paths: Iterable[Path]) -> int:
    """Count items in a path iterable.

    - Teleology: tiny helper to size a path iterator without materializing it.
    - Guarantee: returns the number of yielded items.
    - Fails: never raises on its own (may propagate the iterable's own errors).
    """
    return sum(1 for _ in paths)


def list_evidence(
    project_path: str | Path, *, limit: int | None = None
) -> dict[str, Any]:
    """List the project's evidence receipts as compact rows with inspect commands.

    - Teleology: the public index over .microcosm/evidence so a reader can pick a receipt to drill into.
    - Guarantee: returns a bounded, sorted list of evidence rows (ref, inspect commands, schema, status, replacement policy) plus total/returned counts and a truncated flag.
    - Fails: never raises; per-file read errors degrade a row's fields rather than aborting.
    - When-needed: discovering which receipts exist before inspecting one.
    - Reads: STATE_DIR/evidence/*.json.
    - Escalates-to: inspect_evidence for a single receipt's safe summary.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    project_ref = _project_arg_ref(project_path, project)
    evidence_dir = _evidence_dir(project)
    evidence_count, returned_paths = _bounded_sorted_paths(
        _iter_files_under(evidence_dir, suffix=".json"),
        limit,
    )
    rows: list[dict[str, Any]] = []
    for path in returned_paths:
        try:
            evidence_rel = path.resolve(strict=False).relative_to(
                evidence_dir.resolve(strict=False)
            ).as_posix()
        except ValueError:
            evidence_rel = path.name
        evidence_ref = f"{STATE_DIR}/{EVIDENCE_DIR}/{evidence_rel}"
        payload = _read_project_json(project, f"{EVIDENCE_DIR}/{evidence_rel}")
        rows.append(
            {
                "evidence_ref": evidence_ref,
                "inspect_command": (
                    f"microcosm evidence inspect --project {project_ref} {evidence_ref}"
                ),
                "source_checkout_inspect_command": (
                    "PYTHONPATH=src python3 -m microcosm_core evidence inspect "
                    f"--project {project_ref} {evidence_ref}"
                ),
                "schema_version": payload.get("schema_version"),
                "status": payload.get("status", "unknown"),
                "project_id": payload.get("project_id", _project_name(project)),
                "created_at": payload.get("created_at"),
                "replacement_policy": (
                    payload.get("evidence_replacement", {}).get("policy")
                    if isinstance(payload.get("evidence_replacement"), dict)
                    else None
                ),
            }
        )
    return {
        **_base_payload("microcosm_project_evidence_list_v1", project),
        "project_ref": project_ref,
        "evidence_count": evidence_count,
        "returned_evidence_count": len(rows),
        "limit": limit,
        "truncated": len(rows) < evidence_count,
        "inspect_drilldown": {
            "command_template": (
                "microcosm evidence inspect --project <project> <evidence_ref>"
            ),
            "source_checkout_command_template": (
                "PYTHONPATH=src python3 -m microcosm_core evidence inspect "
                "--project <project> <evidence_ref>"
            ),
            "project_key": "project_ref",
            "row_key": "evidence_ref",
            "field": "payload_summary",
        },
        "evidence": rows,
        **_evidence_interpretation_boundary(),
    }


def _bounded_string_values(value: object, *, limit: int = 12) -> list[str]:
    """Take up to `limit` string items from a value if it is a list.

    - Teleology: bounds ref samples surfaced in the evidence payload summary.
    - Guarantee: returns at most `limit` string items; non-list input -> [].
    - Fails: never raises (filtering only).
    - Reads: only the supplied value.
    """
    if not isinstance(value, list):
        return []
    return [item for item in value[:limit] if isinstance(item, str)]


def _row_ids(value: object, key: str, *, limit: int = 25) -> list[str]:
    """Collect up to `limit` non-empty string ids under `key` from a list of dict rows.

    - Teleology: pulls route/pattern ids into the evidence summary without dumping whole rows.
    - Guarantee: returns at most `limit` string ids found under key; non-list input -> [].
    - Fails: never raises (filtering only).
    - Reads: only the supplied value.
    """
    if not isinstance(value, list):
        return []
    ids: list[str] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        row_id = row.get(key)
        if isinstance(row_id, str) and row_id:
            ids.append(row_id)
        if len(ids) >= limit:
            break
    return ids


def _evidence_payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Summarize an evidence payload by shape and refs, never its source bodies.

    - Teleology: gives inspect_evidence a safe shape/ref digest of a receipt instead of dumping its contents.
    - Guarantee: returns key/list/object/count summaries, bounded ref samples, and selected id/work/causal summaries under a safe_shape_and_refs policy; no source bodies.
    - Fails: never raises (introspection over the dict only).
    - Reads: only the supplied payload dict.
    - Non-goal: a safe summary, not a source-body export or correctness claim.
    """
    payload_keys = sorted(payload.keys())
    list_field_counts = {
        key: len(value)
        for key, value in sorted(payload.items())
        if isinstance(value, list)
    }
    object_field_key_counts = {
        key: len(value)
        for key, value in sorted(payload.items())
        if isinstance(value, dict)
    }
    count_fields = {
        key: value
        for key, value in sorted(payload.items())
        if key.endswith("_count") and isinstance(value, int)
    }
    ref_samples = {
        key: _bounded_string_values(payload.get(key))
        for key in [
            "evidence_refs",
            "reader_drilldowns",
            "grounded_refs",
            "pattern_refs",
            "standard_pressure_refs",
        ]
        if _bounded_string_values(payload.get(key))
    }
    summary: dict[str, Any] = {
        "inspect_card_policy": "safe_shape_and_refs_no_source_bodies",
        "payload_key_count": len(payload_keys),
        "payload_keys": payload_keys,
        "count_fields": count_fields,
        "list_field_counts": list_field_counts,
        "object_field_key_counts": object_field_key_counts,
        "ref_samples": ref_samples,
    }
    route_ids = _row_ids(payload.get("routes"), "route_id")
    if route_ids:
        summary["route_ids"] = route_ids
    pattern_ids = _row_ids(payload.get("patterns"), "pattern_id")
    if pattern_ids:
        summary["pattern_ids"] = pattern_ids
    work_item = payload.get("work_item")
    if isinstance(work_item, dict):
        state_history = work_item.get("state_history")
        summary["work_item_summary"] = {
            "work_id": work_item.get("work_id"),
            "route_id": work_item.get("route_id"),
            "status": work_item.get("status"),
            "transaction_state": work_item.get("transaction_state"),
            "state_history": [
                row.get("state")
                for row in state_history
                if isinstance(row, dict) and isinstance(row.get("state"), str)
            ]
            if isinstance(state_history, list)
            else [],
            "evidence_ref_count": len(work_item.get("evidence_refs", []))
            if isinstance(work_item.get("evidence_refs"), list)
            else 0,
            "event_ref_count": len(work_item.get("event_refs", []))
            if isinstance(work_item.get("event_refs"), list)
            else 0,
        }
    causal_chain = payload.get("causal_chain_proof")
    if isinstance(causal_chain, dict):
        summary["causal_chain_summary"] = {
            "status": causal_chain.get("status"),
            "route_id": causal_chain.get("route_id"),
            "selected_work_id": causal_chain.get("selected_work_id"),
            "evidence_ref_count": causal_chain.get("evidence_ref_count"),
            "event_ref_count": causal_chain.get("event_ref_count"),
        }
    return summary


def _state_ref_status(project: Path, ref: str) -> dict[str, Any]:
    """Report existence/kind/size for one .microcosm state ref.

    - Teleology: per-ref status row backing the compile card's state-ref inventory.
    - Guarantee: returns {ref, exists, kind} plus bytes (file) or json_count (directory) when present.
    - Fails: never raises (existence/size checks are OSError-tolerant).
    - Reads: the resolved STATE_DIR path for the ref.
    """
    rel = ref.removeprefix(f"{STATE_DIR}/").rstrip("/")
    path = _state_dir(project) / rel
    exists = _path_exists(path)
    is_dir = _path_is_dir(path)
    is_file = _path_is_file(path)
    row: dict[str, Any] = {
        "ref": ref,
        "exists": exists,
        "kind": "directory" if ref.endswith("/") or is_dir else "file",
    }
    if is_file:
        row["bytes"] = _path_size(path)
    elif is_dir:
        row["json_count"] = _count_files_under(path, suffix=".json")
    return row


def _compile_source_freshness(
    project: Path, catalog: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compare source/dir mtimes against the state_index cache to judge cache freshness.

    - Teleology: tells the compile card whether the cached state is current, stale, or missing its cache marker.
    - Guarantee: returns status (current/stale/missing_cache_marker) with tracked/stale/missing counts and newest mtimes; source_refs_exported=False.
    - Fails: never raises (mtime reads are OSError-tolerant; unreadable sources counted, not raised).
    - Reads: state_index.json mtime and each catalog/walked source file's mtime.
    - Non-goal: a freshness signal, not source-body export or correctness authority.
    """
    cache_ref = f"{STATE_DIR}/state_index.json"
    cache_path = _state_dir(project) / "state_index.json"
    cache_mtime_ns = _path_mtime_ns(cache_path) if _path_is_file(cache_path) else None

    catalog_files = catalog.get("files") if isinstance(catalog, dict) else None
    if isinstance(catalog_files, list):
        source_rows = [row for row in catalog_files if isinstance(row, dict)]
        freshness_source = "cached_catalog"
    else:
        source_rows = _walk_project(project)
        freshness_source = "project_walk"

    tracked_source_count = 0
    stale_source_count = 0
    missing_cached_source_count = 0
    newest_source_mtime_ns: int | None = None
    parent_dirs: set[Path] = {project}
    for row in source_rows:
        rel = str(row.get("path") or "")
        if not rel:
            continue
        source_path = project / rel
        parent_dirs.add(source_path.parent)
        source_mtime_ns = _path_mtime_ns(source_path)
        if source_mtime_ns is None:
            missing_cached_source_count += 1
            continue
        tracked_source_count += 1
        if newest_source_mtime_ns is None or source_mtime_ns > newest_source_mtime_ns:
            newest_source_mtime_ns = source_mtime_ns
        if cache_mtime_ns is not None and source_mtime_ns > cache_mtime_ns:
            stale_source_count += 1

    stale_directory_count = 0
    newest_directory_mtime_ns: int | None = None
    if cache_mtime_ns is not None and freshness_source == "cached_catalog":
        for directory in parent_dirs:
            directory_mtime_ns = _path_mtime_ns(directory)
            if directory_mtime_ns is None:
                stale_directory_count += 1
                continue
            if (
                newest_directory_mtime_ns is None
                or directory_mtime_ns > newest_directory_mtime_ns
            ):
                newest_directory_mtime_ns = directory_mtime_ns
            if directory_mtime_ns > cache_mtime_ns:
                stale_directory_count += 1

    if cache_mtime_ns is None:
        status = "missing_cache_marker"
    elif stale_source_count or missing_cached_source_count or stale_directory_count:
        status = "stale"
    else:
        status = "current"
    return {
        "status": status,
        "source_status": status if status != "missing_cache_marker" else "unknown",
        "cache_ref": cache_ref,
        "cache_mtime_ns": cache_mtime_ns,
        "freshness_source": freshness_source,
        "catalog_file_count": len(source_rows) if freshness_source == "cached_catalog" else None,
        "tracked_source_count": tracked_source_count,
        "stale_source_count": stale_source_count,
        "missing_cached_source_count": missing_cached_source_count,
        "stale_directory_count": stale_directory_count,
        "newest_source_mtime_ns": newest_source_mtime_ns,
        "newest_directory_mtime_ns": newest_directory_mtime_ns,
        "source_refs_exported": False,
    }


def _selected_route_from_rows(route_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the canonical selected route row from a list of route rows.

    - Teleology: gives compile a stable default route (README onboarding, else first) to anchor its chain.
    - Guarantee: returns the readme_onboarding_route row when present, else the first row, else {}.
    - Fails: never raises (lookup only).
    - Reads: only the supplied route rows.
    """
    return next(
        (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
        route_rows[0] if route_rows else {},
    )


def _truth_readiness_surface(
    project: Path,
    *,
    route_id: str | None,
    route_explanation_status: str | None,
    selected_work_id: str | None,
    selected_work_status: str | None,
    event_count: int,
    evidence_count: int,
    graph_summary: dict[str, Any],
    source_files_mutated: bool,
    state_ref_status_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the truth/readiness accounting surface from the project's local state checks.

    - Teleology: the project-local inspection gate that scores whether the substrate loop produced a complete, human-inspectable result.
    - Guarantee: returns a readiness surface whose truth_accounting checks (state refs, route, explanation, closed work, events, evidence, graph) drive status pass only when all hold with source unmutated and release unauthorized, else partial.
    - Fails: never raises (boolean accounting over passed-in counts).
    - Reads: only the supplied summaries/counts (no disk access here).
    - Non-goal: a project-local readiness gate; does not authorize release, hosting, provider calls, source mutation, equivalence, or proof correctness.
    """
    state_summary = state_ref_status_summary or {}
    missing_state_count = int(state_summary.get("missing_state_ref_count") or 0)
    checks = {
        "project_local_state_refs_complete": missing_state_count == 0,
        "route_selected": bool(route_id),
        "route_explanation_available": route_explanation_status == PASS,
        "work_transaction_closed": selected_work_status == "closed",
        "event_stream_present": event_count > 0,
        "evidence_refs_present": evidence_count > 0,
        "graph_present": int(graph_summary.get("node_count") or 0) > 0
        and int(graph_summary.get("edge_count") or 0) > 0,
        "observatory_surface_available": True,
        "source_files_mutated": source_files_mutated is True,
        "release_authorized": False,
    }
    status = (
        PASS
        if all(
            checks[key] is True
            for key in [
                "project_local_state_refs_complete",
                "route_selected",
                "route_explanation_available",
                "work_transaction_closed",
                "event_stream_present",
                "evidence_refs_present",
                "graph_present",
                "observatory_surface_available",
            ]
        )
        and checks["source_files_mutated"] is False
        and checks["release_authorized"] is False
        else "partial"
    )
    return {
        **_base_payload("microcosm_truth_readiness_surface_v1", project),
        "surface_id": "public_microcosm_truth_readiness",
        "status": status,
        "readiness_posture": (
            "local_first_executable_research_prototype_ready_for_human_inspection"
            if status == PASS
            else "partial_local_state_needs_compile_refresh"
        ),
        "state_ref": f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
        "selected_route_id": route_id,
        "selected_work_id": selected_work_id,
        "selected_work_status": selected_work_status,
        "route_explanation_status": route_explanation_status,
        "truth_accounting": checks,
        "observatory_surface": {
            "project_observe_command": PROJECT_OBSERVE_CARD_COMMAND,
            "project_observe_full_command": PROJECT_OBSERVE_FULL_COMMAND,
            "command": OBSERVATORY_SERVE_COMMAND,
            "bounded_validation_command": OBSERVATORY_BOUNDED_VALIDATION_COMMAND,
            "bounded_validation_request_count": OBSERVATORY_BOUNDED_VALIDATION_REQUEST_COUNT,
            "compact_endpoint": "/project/observatory-card",
            "expanded_endpoint": "/project/observatory",
        },
        "reader_drilldowns": [
            f"{STATE_DIR}/architecture.json",
            f"{STATE_DIR}/state_index.json",
            f"{STATE_DIR}/graph.json",
            f"{STATE_DIR}/routes.json",
            f"{STATE_DIR}/work_items.json",
            f"{STATE_DIR}/events.jsonl",
            f"{STATE_DIR}/evidence/",
        ],
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
            "source_files_mutated": source_files_mutated,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "hosting_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "This truth/readiness surface is a project-local inspection gate. "
            "It does not authorize release, hosting, provider calls, source "
            "mutation, private-data equivalence, or proof correctness."
        ),
    }


def _write_truth_readiness_surface(
    project: Path,
    *,
    route_id: str | None,
    route_explanation_status: str | None,
    selected_work_id: str | None,
    selected_work_status: str | None,
    event_count: int,
    evidence_count: int,
    graph_summary: dict[str, Any],
    source_files_mutated: bool,
    state_ref_status_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and persist the truth/readiness surface to truth_readiness.json.

    - Teleology: the writing wrapper that makes the readiness gate a durable, re-readable state file.
    - Guarantee: computes the surface via _truth_readiness_surface, writes it atomically, and returns the payload.
    - Fails: write failure -> raises OSError.
    - Writes: STATE_DIR/truth_readiness.json.
    - Non-goal: persists the gate; does not authorize release or correctness.
    """
    payload = _truth_readiness_surface(
        project,
        route_id=route_id,
        route_explanation_status=route_explanation_status,
        selected_work_id=selected_work_id,
        selected_work_status=selected_work_status,
        event_count=event_count,
        evidence_count=evidence_count,
        graph_summary=graph_summary,
        source_files_mutated=source_files_mutated,
        state_ref_status_summary=state_ref_status_summary,
    )
    write_json_atomic(_state_dir(project) / TRUTH_READINESS_STATE, payload)
    return payload


def compile_project_card(project_path: str | Path) -> dict[str, Any]:
    """Read cached compile state without rebuilding project-local substrate.

    - Teleology: the public read-only compile lens that reports cached state status and freshness without re-running the loop.
    - Guarantee: returns a cached-card payload (cache_status, freshness, state-ref inventory, route/work/event/evidence/graph summaries, truth-readiness) and status pass only when state is complete, fresh, and explained; stale/missing reported honestly.
    - Fails: never raises beyond the strict JSON reads; a missing truth surface is synthesized in-memory, not written.
    - When-needed: repeat compile-state inspection between full rebuilds.
    - Reads: STATE_DIR/{catalog,python_lens,routes,graph,state_index,explanations,work_items,evidence,truth_readiness}.
    - Non-goal: a read-only lens; does not rebuild, mutate source, call providers, or authorize release.
    - Escalates-to: compile_project when cache_status is missing/stale.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    catalog = _read_project_json(project, "catalog.json")
    python_projection = _read_project_json(project, PYTHON_LENS_STATE)
    routes = _read_project_json(project, "routes.json")
    graph = _read_project_json(project, "graph.json")
    state_index = _read_project_json(project, "state_index.json")
    route_rows = [
        row for row in routes.get("routes", []) if isinstance(row, dict)
    ]
    selected_route = _selected_route_from_rows(route_rows)
    route_id = str(selected_route.get("route_id") or "")
    explanation = (
        _read_project_json(project, f"explanations/{route_id}.json")
        if route_id
        else {}
    )
    work_rows = _load_work_items(project)
    selected_work = next(
        (row for row in work_rows if row.get("route_id") == route_id),
        work_rows[0] if work_rows else {},
    )
    event_summary = _read_event_stream_summary(_state_dir(project) / EVENT_STREAM)
    state_ref_status = [_state_ref_status(project, ref) for ref in COMPILE_STATE_REFS]
    missing_state_refs_all = [
        str(row.get("ref")) for row in state_ref_status if row.get("exists") is not True
    ]
    optional_missing_state_refs = [
        ref for ref in missing_state_refs_all if ref == f"{STATE_DIR}/{TRUTH_READINESS_STATE}"
    ]
    missing_state_refs = [
        ref for ref in missing_state_refs_all if ref not in optional_missing_state_refs
    ]
    cache_freshness = _compile_source_freshness(project, catalog)
    route_explanation_status = explanation.get("status") if route_id else "missing_route"
    state_status = (
        PASS
        if _path_is_dir(_state_dir(project))
        and not missing_state_refs
        and bool(state_index)
        and bool(route_id)
        and route_explanation_status == PASS
        else "missing_cached_compile_state"
    )
    status = state_status
    if state_status == PASS and cache_freshness["status"] == "stale":
        status = "stale_cached_state"
    cache_status = (
        "cached_state_read"
        if status == PASS
        else "stale_cached_state"
        if status == "stale_cached_state"
        else "missing_cached_state"
    )
    last_event = event_summary["last_event"]
    graph_summary = {
        "node_count": graph.get("node_count", 0),
        "edge_count": graph.get("edge_count", 0),
        "graph_ref": f"{STATE_DIR}/graph.json",
    }
    state_ref_status_summary = {
        "checked_state_ref_count": len(state_ref_status),
        "missing_state_ref_count": len(missing_state_refs),
        "missing_state_refs": missing_state_refs,
        "optional_missing_state_refs": optional_missing_state_refs,
    }
    evidence_dir = _evidence_dir(project)
    evidence_count = _count_files_under(evidence_dir, suffix=".json")
    truth_readiness = _read_project_json(project, TRUTH_READINESS_STATE)
    if not truth_readiness:
        truth_readiness = _truth_readiness_surface(
            project,
            route_id=route_id or None,
            route_explanation_status=route_explanation_status,
            selected_work_id=selected_work.get("work_id") if selected_work else None,
            selected_work_status=selected_work.get("status") if selected_work else None,
            event_count=event_summary["event_count"],
            evidence_count=evidence_count,
            graph_summary=graph_summary,
            source_files_mutated=False,
            state_ref_status_summary=state_ref_status_summary,
        )
    return {
        **_base_payload("microcosm_project_compile_cached_card_v1", project),
        "status": status,
        "card_id": "compile_cached_state",
        "command": "microcosm compile --card <project>",
        "full_command": "microcosm compile <project>",
        "cache_status": cache_status,
        "cache_source_ref": f"{STATE_DIR}/state_index.json",
        "cache_freshness": cache_freshness,
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "state_ref_status_summary": state_ref_status_summary,
        "state_ref_status": state_ref_status,
        "file_count": catalog.get("file_count", 0),
        "role_counts": catalog.get("role_counts", {}),
        "python_lens_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "python_file_count": python_projection.get("python_file_count", 0),
        "python_ready_route_count": python_projection.get("ready_route_count", 0),
        "route_count": routes.get("route_count", len(route_rows)),
        "selected_route_id": route_id or None,
        "route_ids": [str(row.get("route_id")) for row in route_rows if row.get("route_id")],
        "route_explanation_status": route_explanation_status,
        "route_explanation_ref": (
            f"{STATE_DIR}/explanations/{route_id}.json" if route_id else None
        ),
        "selected_work_id": selected_work.get("work_id") if selected_work else None,
        "selected_work_status": selected_work.get("status") if selected_work else None,
        "work_item_count": len(work_rows),
        "event_count": event_summary["event_count"],
        "last_event": {
            "event_id": last_event.get("event_id"),
            "span": last_event.get("span"),
            "status": last_event.get("status"),
        }
        if last_event
        else None,
        "evidence_count": evidence_count,
        "graph_summary": graph_summary,
        "truth_readiness_ref": f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
        "truth_readiness_surface": truth_readiness,
        "reader_action": (
            "Use this cached card for repeat compile-state inspection; run "
            "`microcosm compile <project>` when cache_status is missing_cached_state "
            "or stale_cached_state."
        ),
        "next_commands": [
            "microcosm status --card <project>",
            (
                f"microcosm explain <project> {route_id}"
                if route_id
                else "microcosm explain <project> <selected_route_id>"
            ),
            OBSERVATORY_BOUNDED_VALIDATION_COMMAND,
            OBSERVATORY_SERVE_COMMAND,
        ],
        "source_files_mutated": False,
        "safe_to_show": {
            "project_local_state_refs_visible": True,
            "route_metadata_visible": True,
            "receipt_refs_visible": True,
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_authorized": False,
            "proof_correctness_claim": False,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutated": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "The compile cached card is a read-only state lens. It does not "
            "rebuild, mutate source files, call providers, authorize release, "
            "or claim project correctness."
        ),
    }


def compile_project(
    project_path: str | Path,
    *,
    python_lens_scan_mode: str = PYTHON_LENS_SCAN_FULL,
) -> dict[str, Any]:
    """Run the safe public substrate loop over a user-owned project.

    - Teleology: the public top-level command that runs the whole repo->.microcosm loop (init/index/lens/patterns/routes/work/explain/observe/evidence/architecture/truth-readiness).
    - Guarantee: materializes all project-local state, runs and closes a work transaction, writes the truth-readiness surface, and returns a compile result with what_happened, counts, the reader causal chain, and an authority ceiling pinned to release/provider/source-mutation False.
    - Fails: filesystem failures in any stage -> raise OSError; otherwise envelope status pass with source_files_mutated False.
    - When-needed: building or refreshing the full project-local substrate for inspection.
    - Writes: the entire STATE_DIR tree (manifest, catalog, python_lens, patterns, routes, work_items, events, evidence, explanations, graph, state_index, truth_readiness).
    - Non-goal: builds project-local public state only; does not authorize release, hosting, provider calls, source mutation, equivalence, live ledger mutation, or production readiness.
    - Escalates-to: compile_project_card for cached re-reads; observe_project for the resulting lineage.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    if not _path_is_file(_state_dir(project) / "project_manifest.json"):
        init_project(project)
    index_result = index_project(project, refresh_architecture=False)
    catalog = catalog_project(project)
    python_projection = python_lens(
        project,
        refresh_architecture=False,
        scan_mode=python_lens_scan_mode,
    )
    routes = propose_routes(project, refresh_architecture=False)
    patterns = _read_project_json(project, "patterns.json")
    route_rows = [
        row for row in routes.get("routes", []) if isinstance(row, dict)
    ]
    selected_route = next(
        (row for row in route_rows if row.get("route_id") == "readme_onboarding_route"),
        route_rows[0] if route_rows else {},
    )
    route_id = str(selected_route.get("route_id") or "")
    work_result = (
        _run_work_for_route(project, route_id, refresh_architecture=False)
        if route_id
        else run_work(project, refresh_architecture=False)
    )
    explanation = (
        explain_route(project, route_id, refresh_architecture=False) if route_id else {}
    )
    observed = observe_project(project, refresh_architecture=False)
    evidence = list_evidence(project, limit=0)
    architecture = architecture_kernel.write_project_architecture(project)
    graph = _read_project_json(project, "graph.json")
    work_id = work_result.get("work_id")
    graph_summary = {
        "node_count": graph.get("node_count", 0),
        "edge_count": graph.get("edge_count", 0),
        "graph_ref": f"{STATE_DIR}/graph.json",
    }
    reader_causal_chain = _reader_causal_chain_card(
        project,
        route_id=route_id,
        work_result=work_result,
        explanation=explanation,
        observed=observed,
        graph=graph,
        evidence=evidence,
    )
    pre_truth_state_refs = [
        ref
        for ref in COMPILE_STATE_REFS
        if ref != f"{STATE_DIR}/{TRUTH_READINESS_STATE}"
    ]
    pre_truth_status = [_state_ref_status(project, ref) for ref in pre_truth_state_refs]
    missing_pre_truth_refs = [
        str(row.get("ref")) for row in pre_truth_status if row.get("exists") is not True
    ]
    state_ref_status_summary = {
        "checked_state_ref_count": len(pre_truth_status),
        "missing_state_ref_count": len(missing_pre_truth_refs),
        "missing_state_refs": missing_pre_truth_refs,
    }
    truth_readiness = _write_truth_readiness_surface(
        project,
        route_id=route_id or None,
        route_explanation_status=explanation.get("status") if route_id else None,
        selected_work_id=str(work_id) if work_id else None,
        selected_work_status=work_result.get("selected_work_status")
        or work_result.get("work_status")
        or "closed"
        if work_id
        else None,
        event_count=int(observed.get("event_count", 0) or 0),
        evidence_count=int(evidence.get("evidence_count", 0) or 0),
        graph_summary=graph_summary,
        source_files_mutated=work_result.get("source_files_mutated") is True,
        state_ref_status_summary=state_ref_status_summary,
    )
    architecture_kernel.build_state_index(project)
    return {
        **_base_payload("microcosm_project_compile_result_v1", project),
        "headline": "repo -> .microcosm",
        "what_happened": [
            f"created or reused {STATE_DIR}/",
            f"indexed {index_result.get('file_count', 0)} files",
            f"projected Python lens over {python_projection.get('python_file_count', 0)} Python files",
            f"detected {patterns.get('passing_pattern_count', 0)} passing patterns",
            f"opened {routes.get('route_count', 0)} routes",
            f"ran {work_id}" if work_id else "no work item available",
            f"explained route/work chain for {route_id}" if route_id else "no route available to explain",
            f"emitted {observed.get('event_count', 0)} events",
            f"wrote {evidence.get('evidence_count', 0)} evidence refs",
        ],
        "project_ref": ".",
        "state_ref": STATE_DIR,
        "state_files": list(COMPILE_STATE_REFS),
        "file_count": index_result.get("file_count", 0),
        "role_counts": catalog.get("role_counts", {}),
        "python_lens_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}",
        "python_lens_scan_mode": python_projection.get(
            "scan_mode",
            python_lens_scan_mode,
        ),
        "python_lens_deferred_full_scan": python_projection.get(
            "deferred_full_scan",
            False,
        ),
        "python_lens_full_command": python_projection.get(
            "full_lens_command",
            "microcosm python-lens <project>",
        ),
        "python_navigation_assay_ref": f"{STATE_DIR}/{PYTHON_LENS_STATE}::navigation_assay",
        "python_file_count": python_projection.get("python_file_count", 0),
        "python_ready_route_count": python_projection.get("ready_route_count", 0),
        "python_source_span_count": python_projection.get("source_span_count", 0),
        "python_navigation_assay": {
            "assay_id": (
                python_projection.get("navigation_assay", {}).get("assay_id")
                if isinstance(python_projection.get("navigation_assay"), dict)
                else None
            ),
            "canonical_depth_ladder": (
                python_projection.get("navigation_assay", {}).get("canonical_depth_ladder", [])
                if isinstance(python_projection.get("navigation_assay"), dict)
                else []
            ),
            "probe_disposition_counts": (
                python_projection.get("navigation_assay", {}).get("probe_disposition_counts", {})
                if isinstance(python_projection.get("navigation_assay"), dict)
                else {}
            ),
            "route_utility_task_count": (
                python_projection.get("navigation_assay", {}).get("route_utility_task_count", 0)
                if isinstance(python_projection.get("navigation_assay"), dict)
                else 0
            ),
            "route_utility_disposition_counts": (
                python_projection.get("navigation_assay", {}).get(
                    "route_utility_disposition_counts", {}
                )
                if isinstance(python_projection.get("navigation_assay"), dict)
                else {}
            ),
            "route_utility_ratchet_status": (
                python_projection.get("navigation_assay", {}).get(
                    "route_utility_ratchet_status"
                )
                if isinstance(python_projection.get("navigation_assay"), dict)
                else None
            ),
            "route_utility_stale_task_count": (
                python_projection.get("navigation_assay", {}).get(
                    "route_utility_stale_task_count", 0
                )
                if isinstance(python_projection.get("navigation_assay"), dict)
                else 0
            ),
        },
        "route_utility_curriculum": python_projection.get("route_utility_curriculum", {}),
        "implementation_atlas": python_projection.get("implementation_atlas", {}),
        "python_navigation_route": python_projection.get("python_navigation_route", {}),
        "primitive_ids": architecture.get("primitive_ids", []),
        "passing_pattern_count": patterns.get("passing_pattern_count", 0),
        "route_count": routes.get("route_count", 0),
        "route_ids": [str(row.get("route_id")) for row in route_rows if row.get("route_id")],
        "selected_route_id": route_id,
        "resolved_pattern_refs": explanation.get("pattern_refs", []),
        "resolved_standard_pressure_refs": explanation.get("standard_pressure_refs", []),
        "work_id": work_id,
        "reader_causal_chain": reader_causal_chain,
        "transaction_status": work_result.get("transaction_status"),
        "idempotent_replay": work_result.get("idempotent_replay", False),
        "event_count": observed.get("event_count", 0),
        "evidence_count": evidence.get("evidence_count", 0),
        "graph_summary": graph_summary,
        "truth_readiness_ref": f"{STATE_DIR}/{TRUTH_READINESS_STATE}",
        "truth_readiness_surface": truth_readiness,
        "open_observatory": OBSERVATORY_SERVE_COMMAND,
        "bounded_observatory_validation": OBSERVATORY_BOUNDED_VALIDATION_COMMAND,
        "source_files_mutated": False,
        "authority_ceiling": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_files_mutated": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": (
            "Compile builds project-local public substrate state only. It does not "
            "authorize release, hosting, provider calls, source mutation, private-data "
            "equivalence, live Task Ledger mutation, or production readiness."
        ),
    }


def inspect_evidence(project_path: str | Path, evidence_ref: str) -> dict[str, Any]:
    """Inspect one evidence receipt as a safe-keys card plus a shape/ref summary.

    - Teleology: the public drilldown that opens a single receipt without dumping its full body.
    - Guarantee: returns a card with a whitelisted safe-keys view, a payload_summary (shape/refs only), and a full-payload drilldown pointer; a missing ref yields status not_found.
    - Fails: never raises; an absent receipt returns a not_found card, not an exception.
    - When-needed: examining a specific evidence ref surfaced by list_evidence.
    - Reads: STATE_DIR/<evidence_ref>.
    - Non-goal: a safe summary + pointer; does not export source bodies or authorize release.
    - Escalates-to: the full local JSON via the full_payload_drilldown command.
    """
    project = Path(project_path).expanduser().resolve(strict=False)
    project_ref = _project_arg_ref(project_path, project)
    rel = evidence_ref.removeprefix(f"{STATE_DIR}/")
    payload = _read_project_json(project, rel)
    if not payload:
        return {
            **_base_payload("microcosm_project_evidence_card_v1", project),
            "project_ref": project_ref,
            "status": "not_found",
            "evidence_ref": evidence_ref,
            "full_payload_drilldown": _evidence_full_payload_drilldown(
                project_ref=project_ref,
                evidence_ref=evidence_ref,
            ),
            **_evidence_interpretation_boundary(),
        }
    safe_keys = {
        "schema_version",
        "status",
        "project_id",
        "project_ref",
        "state_ref",
        "created_at",
        "route_id",
        "work_id",
        "event_id",
        "file_count",
        "role_counts",
        "release_authorized",
        "evidence_replacement",
    }
    return {
        **_base_payload("microcosm_project_evidence_card_v1", project),
        "project_ref": project_ref,
        "evidence_ref": evidence_ref,
        "evidence": {key: payload.get(key) for key in safe_keys if key in payload},
        "payload_summary": _evidence_payload_summary(payload),
        "full_payload_drilldown": _evidence_full_payload_drilldown(
            project_ref=project_ref,
            evidence_ref=evidence_ref,
        ),
        **_source_body_boundary_row(),
        **_evidence_interpretation_boundary(),
    }


def _print_json(payload: Any) -> int:
    """Print a payload as sorted JSON and derive a process exit code from its status.

    - Teleology: the CLI sink that renders a command result and maps its status to an exit code.
    - Guarantee: prints deterministic indented JSON and returns 0 when status is None/pass (or non-dict), else 1.
    - Fails: non-serializable payload -> raises TypeError from json.dumps.
    - Writes: stdout.
    """
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if not isinstance(payload, dict) or payload.get("status") in {None, PASS} else 1


def build_parser() -> argparse.ArgumentParser:
    """Construct the argparse parser for the microcosm-project CLI.

    - Teleology: declares every project-substrate subcommand (init, index, catalog, architecture, python-lens, patterns, route, compile, graph, explain, work, observe, evidence) so the CLI is one wired surface.
    - Guarantee: returns a configured ArgumentParser with all subparsers, nested work/evidence subcommands, and flags registered.
    - Fails: None (pure parser construction; no I/O).
    """
    parser = argparse.ArgumentParser(prog="microcosm-project")
    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project")
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("project")
    catalog_parser = subparsers.add_parser("catalog")
    catalog_parser.add_argument("project")
    architecture_parser = subparsers.add_parser("architecture")
    architecture_parser.add_argument("project")
    python_lens_parser = subparsers.add_parser("python-lens")
    python_lens_parser.add_argument(
        "--full",
        action="store_true",
        help="emit full source-span, symbol, import, and graph rows",
    )
    python_lens_parser.add_argument("project")
    patterns_parser = subparsers.add_parser("patterns")
    patterns_parser.add_argument("project")
    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("project")
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument(
        "--card",
        action="store_true",
        help="read cached compile state without rebuilding .microcosm",
    )
    compile_parser.add_argument("project")
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("project")
    explain_parser = subparsers.add_parser("explain")
    explain_parser.add_argument("project")
    explain_parser.add_argument("route_id")
    work_parser = subparsers.add_parser("work")
    work_sub = work_parser.add_subparsers(dest="work_command")
    create_parser = work_sub.add_parser("create")
    create_parser.add_argument("project")
    create_parser.add_argument("--route")
    run_parser = work_sub.add_parser("run")
    run_parser.add_argument("project")
    run_parser.add_argument("--work-id")
    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument(
        "--card",
        action="store_true",
        help="emit compact observe card instead of full event rows",
    )
    observe_parser.add_argument("project")
    evidence_parser = subparsers.add_parser("evidence")
    evidence_sub = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_list = evidence_sub.add_parser("list")
    evidence_list.add_argument("project")
    evidence_inspect = evidence_sub.add_parser("inspect")
    evidence_inspect.add_argument("project")
    evidence_inspect.add_argument("evidence_ref")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint dispatching microcosm-project subcommands to their handlers.

    - Teleology: the single shell front door for the project-substrate lens (compile/index/route/work/observe/evidence over a target project).
    - Guarantee: parses argv, runs the matched subcommand, prints its JSON result, and returns the handler's exit code; prints help and returns 2 when no subcommand matches.
    - Fails: unknown/missing command -> help printed -> return 2 (no exception).
    - Reads: argv and, via handlers, the target project tree and its .microcosm state.
    - Writes: handler side effects (e.g. init/compile/work materialize .microcosm artifacts); stdout.
    - When-needed: running the microcosm-project CLI from the shell.
    - Escalates-to: build_parser plus the per-command handlers (init_project, compile_project, propose_routes, run_work, observe_project, inspect_evidence, ...).
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return _print_json(init_project(args.project))
    if args.command == "index":
        return _print_json(index_project(args.project))
    if args.command == "catalog":
        return _print_json(catalog_project(args.project))
    if args.command == "architecture":
        return _print_json(architecture_project(args.project))
    if args.command == "python-lens":
        if args.full:
            return _print_json(python_lens(args.project))
        return _print_json(python_lens_card(args.project))
    if args.command == "patterns":
        return _print_json(discover_patterns(args.project))
    if args.command == "route":
        return _print_json(propose_routes(args.project))
    if args.command == "compile":
        if args.card:
            return _print_json(compile_project_card(args.project))
        return _print_json(compile_project(args.project))
    if args.command == "graph":
        return _print_json(state_graph(args.project))
    if args.command == "explain":
        return _print_json(explain_route(args.project, args.route_id))
    if args.command == "work":
        if args.work_command == "create":
            return _print_json(create_work(args.project, args.route))
        if args.work_command == "run":
            return _print_json(run_work(args.project, args.work_id))
    if args.command == "observe":
        if args.card:
            return _print_json(
                observe_project_card(args.project, refresh_architecture=False)
            )
        return _print_json(observe_project(args.project, refresh_architecture=False))
    if args.command == "evidence":
        if args.evidence_command == "list":
            return _print_json(list_evidence(args.project))
        if args.evidence_command == "inspect":
            return _print_json(inspect_evidence(args.project, args.evidence_ref))
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
