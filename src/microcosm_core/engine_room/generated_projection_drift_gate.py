"""Public-safe generated projection drift gate capsule.

This is a source-faithful public refactor of
`tools/meta/control/projection_drift.py` and
`system/lib/generated_projection_registry.py`. It models generated artifacts as
owner rows, scopes checks by changed paths, fingerprints source and artifact
files, uses prior clean receipts as a bounded skip cache, and treats each
owner's no-write check command as the drift authority.

The capsule is an owner-routed drift gate, not a semantic proof that every
builder in the macro registry is content-diff based. A clean result means the
selected owner's declared no-write check passed and required artifacts were
present for the supplied root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "engine_room_generated_projection_drift_gate_v1"
ORGAN_ID = "engine_room_generated_projection_drift_gate"
SOURCE_REFS = (
    "tools/meta/control/projection_drift.py",
    "system/lib/generated_projection_registry.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Owner-routed generated projection drift gate over declared artifacts, "
    "source authorities, clean-receipt fingerprints, and no-write check command "
    "return codes. It does not prove that every macro owner uses true "
    "content-diff semantics, does not repair files, and does not authorize "
    "public release."
)
ANTI_CLAIMS = (
    "not_semantic_drift_proof",
    "not_full_registry_validation",
    "not_repair_authority",
    "not_release_authority",
)
DEFAULT_COMMAND_TIMEOUT_SECONDS = 10
FACT_AUTHORITY_LINEAGE_REQUIRED_FIELDS = (
    "authority_ref",
    "appearance_refs",
    "derivation_path",
    "guard_ref",
    "treatment",
    "residual_route",
)
ALLOWED_FACT_AUTHORITY_TREATMENTS = (
    "guarded_public_projection",
    "computed_projection",
    "curated_exception",
)


@dataclass(frozen=True)
class ProjectionOwner:
    owner_id: str
    description: str
    artifacts: tuple[str, ...]
    source_authorities: tuple[str, ...]
    check_command: tuple[str, ...]
    repair_command: tuple[str, ...] = ()
    manual_edit_boundary: str = ""
    deterministic_regeneration_expectation: str = ""
    stale_drift_handling: str = ""
    fact_authority_lineage: Any = None
    require_fact_authority_lineage: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_json(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _sha256_bytes(data)


def _normalise_path_token(path: str) -> str:
    token = str(path or "").replace("\\", "/").strip("/")
    while token.startswith("./"):
        token = token[2:]
    return token


def _has_glob_token(pattern: str) -> bool:
    return any(token in pattern for token in ("*", "?", "["))


def projection_pattern_matches_path(pattern: str, path: str) -> bool:
    """Return whether a registry pattern covers a repo-relative path."""

    normalized_pattern = _normalise_path_token(pattern)
    normalized_path = _normalise_path_token(path)
    if not normalized_pattern or not normalized_path:
        return False
    if _has_glob_token(normalized_pattern):
        return fnmatchcase(normalized_path, normalized_pattern)
    return (
        normalized_path == normalized_pattern
        or normalized_path.startswith(f"{normalized_pattern}/")
        or normalized_pattern.startswith(f"{normalized_path}/")
    )


def owner_matches_path(owner: ProjectionOwner, path: str) -> bool:
    patterns = tuple(owner.artifacts) + tuple(owner.source_authorities)
    return any(projection_pattern_matches_path(pattern, path) for pattern in patterns)


def select_projection_owners(
    owners: Iterable[ProjectionOwner],
    *,
    owner_ids: Iterable[str] | None = None,
    changed_paths: Iterable[str] | None = None,
) -> tuple[list[ProjectionOwner], dict[str, Any]]:
    requested = {str(owner_id).strip() for owner_id in (owner_ids or []) if str(owner_id).strip()}
    paths = [str(path).strip() for path in (changed_paths or []) if str(path).strip()]
    rows = [owner for owner in owners if not requested or owner.owner_id in requested]
    if paths:
        rows = [owner for owner in rows if any(owner_matches_path(owner, path) for path in paths)]
        mode = "scoped_paths"
    else:
        mode = "owner_filter" if requested else "all_owners"
    return rows, {
        "mode": mode,
        "changed_paths": paths,
        "requested_owner_ids": sorted(requested),
        "selected_owner_ids": [owner.owner_id for owner in rows],
        "selected_owner_count": len(rows),
    }


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _files_for_pattern(root: Path, pattern: str) -> tuple[list[Path], list[str]]:
    token = _normalise_path_token(pattern)
    if not token:
        return [], [pattern]
    matches = sorted(root.glob(token)) if _has_glob_token(token) else [root / token]
    files: list[Path] = []
    missing: list[str] = []
    if not matches:
        missing.append(token)
    for path in matches:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*") if child.is_file()))
        else:
            missing.append(_relative_to_root(root, path))
    return files, missing


def _fingerprint_patterns(root: Path, patterns: Sequence[str]) -> dict[str, Any]:
    entries: list[dict[str, str]] = []
    missing: list[str] = []
    seen_paths: set[str] = set()
    for pattern in patterns:
        files, missing_patterns = _files_for_pattern(root, pattern)
        missing.extend(missing_patterns)
        for path in files:
            rel_path = _relative_to_root(root, path)
            if rel_path in seen_paths:
                continue
            seen_paths.add(rel_path)
            try:
                digest = _sha256_bytes(path.read_bytes())
            except OSError as exc:
                digest = f"unreadable:{type(exc).__name__}:{exc}"
            entries.append({"path": rel_path, "sha256": digest})
    entries.sort(key=lambda row: row["path"])
    missing = sorted(set(missing))
    payload = {
        "patterns": list(patterns),
        "files": entries,
        "missing": missing,
    }
    return {
        "hash": _sha256_json(payload),
        "path_count": len(entries),
        "missing_count": len(missing),
        "missing_patterns": missing,
        "files": entries,
    }


def _owner_fingerprint(root: Path, owner: ProjectionOwner) -> dict[str, Any]:
    source = _fingerprint_patterns(root, owner.source_authorities)
    artifacts = _fingerprint_patterns(root, owner.artifacts)
    return {
        "source_hash": source["hash"],
        "source_path_count": source["path_count"],
        "source_missing_count": source["missing_count"],
        "source_missing_patterns": source["missing_patterns"],
        "artifact_hash": artifacts["hash"],
        "artifact_path_count": artifacts["path_count"],
        "artifact_missing_count": artifacts["missing_count"],
        "artifact_missing_patterns": artifacts["missing_patterns"],
        "source_files": source["files"],
        "artifact_files": artifacts["files"],
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _fact_authority_lineage_receipt(owner: ProjectionOwner) -> dict[str, Any]:
    lineage = owner.fact_authority_lineage
    required = bool(owner.require_fact_authority_lineage)
    if lineage is None:
        return {
            "status": "missing_required" if required else "not_declared",
            "required": required,
            "missing_fields": list(FACT_AUTHORITY_LINEAGE_REQUIRED_FIELDS) if required else [],
            "invalid_fields": [],
            "allowed_treatments": list(ALLOWED_FACT_AUTHORITY_TREATMENTS),
        }
    if not isinstance(lineage, Mapping):
        return {
            "status": "invalid",
            "required": required,
            "missing_fields": [],
            "invalid_fields": ["fact_authority_lineage"],
            "allowed_treatments": list(ALLOWED_FACT_AUTHORITY_TREATMENTS),
        }

    missing_fields = [
        field
        for field in FACT_AUTHORITY_LINEAGE_REQUIRED_FIELDS
        if field not in lineage
        or (field != "appearance_refs" and not _nonempty_string(lineage.get(field)))
        or (field == "appearance_refs" and not _string_list(lineage.get(field)))
    ]
    invalid_fields: list[str] = []
    treatment = str(lineage.get("treatment") or "").strip()
    if treatment and treatment not in ALLOWED_FACT_AUTHORITY_TREATMENTS:
        invalid_fields.append("treatment")

    status = "pass" if not missing_fields and not invalid_fields else "invalid"
    return {
        "status": status,
        "required": required,
        "authority_ref": str(lineage.get("authority_ref") or "").strip() or None,
        "appearance_refs": _string_list(lineage.get("appearance_refs")),
        "derivation_path": str(lineage.get("derivation_path") or "").strip() or None,
        "guard_ref": str(lineage.get("guard_ref") or "").strip() or None,
        "treatment": treatment or None,
        "residual_route": str(lineage.get("residual_route") or "").strip() or None,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "allowed_treatments": list(ALLOWED_FACT_AUTHORITY_TREATMENTS),
    }


def _source_hash_cache_hit(
    owner: ProjectionOwner,
    fingerprint: Mapping[str, Any],
    source_hash_cache: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if int(fingerprint.get("artifact_missing_count") or 0):
        return None
    owners = source_hash_cache.get("owners") if isinstance(source_hash_cache, Mapping) else None
    row = owners.get(owner.owner_id) if isinstance(owners, Mapping) else None
    if not isinstance(row, Mapping):
        return None
    if row.get("status") != "clean":
        return None
    if int(row.get("artifact_missing_count") or 0):
        return None
    if row.get("source_hash") != fingerprint["source_hash"]:
        return None
    if row.get("artifact_hash") != fingerprint["artifact_hash"]:
        return None
    if list(row.get("check_command") or []) != list(owner.check_command):
        return None
    return row


def _expand_command(command: Sequence[str], root: Path) -> list[str]:
    replacements = {
        "{python}": sys.executable,
        "{root}": str(root),
    }
    expanded: list[str] = []
    for part in command:
        text = str(part)
        for token, value in replacements.items():
            text = text.replace(token, value)
        expanded.append(text)
    return expanded


def _command_receipt(
    *,
    command: Sequence[str],
    returncode: int,
    started_at: str,
    ended_at: str,
    stdout: str = "",
    stderr: str = "",
    source: str = "subprocess",
) -> dict[str, Any]:
    return {
        "command": list(command),
        "started_at": started_at,
        "ended_at": ended_at,
        "returncode": returncode,
        "source": source,
        "stdout_sha256": _sha256_bytes(stdout.encode("utf-8", errors="replace")),
        "stderr_sha256": _sha256_bytes(stderr.encode("utf-8", errors="replace")),
        "stdout_byte_count": len(stdout.encode("utf-8", errors="replace")),
        "stderr_byte_count": len(stderr.encode("utf-8", errors="replace")),
    }


def _run_builtin_command(command: Sequence[str], root: Path) -> dict[str, Any] | None:
    if not command:
        return None
    started_at = _utc_now()
    name = str(command[0])
    if name == "builtin:pass":
        return _command_receipt(
            command=command,
            returncode=0,
            started_at=started_at,
            ended_at=_utc_now(),
            stdout="builtin pass\n",
            source="builtin",
        )
    if name == "builtin:fail":
        return _command_receipt(
            command=command,
            returncode=7,
            started_at=started_at,
            ended_at=_utc_now(),
            stderr="builtin fail\n",
            source="builtin",
        )
    if name == "builtin:assert-file-equals" and len(command) == 3:
        left = root / _normalise_path_token(str(command[1]))
        right = root / _normalise_path_token(str(command[2]))
        try:
            ok = left.read_bytes() == right.read_bytes()
        except OSError as exc:
            return _command_receipt(
                command=command,
                returncode=8,
                started_at=started_at,
                ended_at=_utc_now(),
                stderr=f"{type(exc).__name__}\n",
                source="builtin",
            )
        return _command_receipt(
            command=command,
            returncode=0 if ok else 9,
            started_at=started_at,
            ended_at=_utc_now(),
            stdout="match\n" if ok else "",
            stderr="" if ok else "mismatch\n",
            source="builtin",
        )
    return None


def _run_command(
    command: Sequence[str],
    root: Path,
    *,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not command:
        now = _utc_now()
        return _command_receipt(command=(), returncode=2, started_at=now, ended_at=now, stderr="missing command\n")
    builtin = _run_builtin_command(command, root)
    if builtin is not None:
        return builtin
    expanded = _expand_command(command, root)
    started_at = _utc_now()
    try:
        completed = subprocess.run(
            expanded,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return _command_receipt(
            command=expanded,
            returncode=124,
            started_at=started_at,
            ended_at=_utc_now(),
            stdout=stdout,
            stderr=stderr or "timeout\n",
        )
    except OSError as exc:
        return _command_receipt(
            command=expanded,
            returncode=127,
            started_at=started_at,
            ended_at=_utc_now(),
            stderr=f"{type(exc).__name__}: {exc}\n",
        )
    return _command_receipt(
        command=expanded,
        returncode=completed.returncode,
        started_at=started_at,
        ended_at=_utc_now(),
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def _cached_clean_result(owner: ProjectionOwner, fingerprint: Mapping[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    return _command_receipt(
        command=owner.check_command,
        returncode=0,
        started_at=now,
        ended_at=now,
        stdout="skipped: source and artifact hashes match prior clean receipt\n",
        source="source_hash_cache",
    ) | {
        "source_hash": fingerprint["source_hash"],
        "artifact_hash": fingerprint["artifact_hash"],
    }


def _check_owner(
    root: Path,
    owner: ProjectionOwner,
    *,
    source_hash_cache: Mapping[str, Any] | None = None,
    use_source_hash_cache: bool = True,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    fingerprint = _owner_fingerprint(root, owner)
    lineage_receipt = _fact_authority_lineage_receipt(owner)
    cache_row = (
        _source_hash_cache_hit(owner, fingerprint, source_hash_cache or {})
        if use_source_hash_cache
        else None
    )
    if cache_row is not None:
        check_result = _cached_clean_result(owner, fingerprint)
        check_mode = "source_hash_cache_hit"
    else:
        check_result = _run_command(owner.check_command, root, timeout_seconds=timeout_seconds)
        check_mode = "command"

    drift_reasons: list[str] = []
    if int(check_result.get("returncode") or 0) != 0:
        drift_reasons.append("check_command_failed")
    if int(fingerprint.get("artifact_missing_count") or 0):
        drift_reasons.append("artifact_missing")
    if lineage_receipt["status"] == "missing_required":
        drift_reasons.append("fact_authority_lineage_missing_required")
    elif lineage_receipt["status"] == "invalid":
        drift_reasons.append("fact_authority_lineage_invalid")

    status = "drift" if drift_reasons else "clean"
    return {
        "owner_id": owner.owner_id,
        "description": owner.description,
        "artifacts": list(owner.artifacts),
        "source_authorities": list(owner.source_authorities),
        "status": status,
        "status_reasons": drift_reasons,
        "check_mode": check_mode,
        "source_hash_receipt": fingerprint,
        "check_command": list(owner.check_command),
        "repair_command": list(owner.repair_command),
        "manual_edit_boundary": owner.manual_edit_boundary,
        "deterministic_regeneration_expectation": owner.deterministic_regeneration_expectation,
        "stale_drift_handling": owner.stale_drift_handling,
        "fact_authority_lineage": lineage_receipt,
        "check_result": check_result,
    }


def check_projection_drift(
    root: Path,
    owners: Iterable[ProjectionOwner],
    *,
    owner_ids: Iterable[str] | None = None,
    changed_paths: Iterable[str] | None = None,
    source_hash_cache: Mapping[str, Any] | None = None,
    use_source_hash_cache: bool = True,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    selected, selection = select_projection_owners(
        owners,
        owner_ids=owner_ids,
        changed_paths=changed_paths,
    )
    rows = [
        _check_owner(
            root,
            owner,
            source_hash_cache=source_hash_cache,
            use_source_hash_cache=use_source_hash_cache,
            timeout_seconds=timeout_seconds,
        )
        for owner in selected
    ]
    drift_owner_count = sum(1 for row in rows if row["status"] == "drift")
    lineage_rows = [row["fact_authority_lineage"] for row in rows]
    lineage_required_count = sum(1 for row in lineage_rows if row.get("required"))
    lineage_declared_count = sum(1 for row in lineage_rows if row.get("status") != "not_declared")
    lineage_invalid_count = sum(
        1 for row in lineage_rows if row.get("status") in {"missing_required", "invalid"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "generated_at": _utc_now(),
        "status": "drift" if drift_owner_count else "clean",
        "root": ".",
        "selection": selection,
        "owner_count": len(rows),
        "drift_owner_count": drift_owner_count,
        "source_hash_cache": {
            "enabled": use_source_hash_cache,
            "hit_count": sum(1 for row in rows if row["check_mode"] == "source_hash_cache_hit"),
            "miss_count": sum(1 for row in rows if row["check_mode"] != "source_hash_cache_hit"),
        },
        "fact_authority_lineage": {
            "status": "blocked" if lineage_invalid_count else "pass",
            "required_owner_count": lineage_required_count,
            "declared_owner_count": lineage_declared_count,
            "invalid_owner_count": lineage_invalid_count,
            "required_fields": list(FACT_AUTHORITY_LINEAGE_REQUIRED_FIELDS),
            "allowed_treatments": list(ALLOWED_FACT_AUTHORITY_TREATMENTS),
        },
        "owners": rows,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
    }


def owner_from_mapping(row: Mapping[str, Any]) -> ProjectionOwner:
    def strings(key: str) -> tuple[str, ...]:
        value = row.get(key)
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Sequence):
            return tuple(str(item) for item in value)
        return ()

    owner_id = str(row.get("owner_id") or "").strip()
    if not owner_id:
        raise ValueError("owner_id is required")
    return ProjectionOwner(
        owner_id=owner_id,
        description=str(row.get("description") or ""),
        artifacts=strings("artifacts"),
        source_authorities=strings("source_authorities"),
        check_command=strings("check_command"),
        repair_command=strings("repair_command"),
        manual_edit_boundary=str(row.get("manual_edit_boundary") or ""),
        deterministic_regeneration_expectation=str(
            row.get("deterministic_regeneration_expectation") or ""
        ),
        stale_drift_handling=str(row.get("stale_drift_handling") or ""),
        fact_authority_lineage=row.get("fact_authority_lineage"),
        require_fact_authority_lineage=row.get("require_fact_authority_lineage") is True,
    )


def owners_from_json(path: Path) -> list[ProjectionOwner]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("owners") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain an owners array")
    return [owner_from_mapping(row) for row in rows if isinstance(row, Mapping)]


def _assemble_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_assemble_value(item) for item in value)
    if isinstance(value, Mapping):
        if "literal" in value:
            return str(value["literal"])
        if "join" in value:
            sep = str(value.get("sep", ""))
            return sep.join(str(part) for part in value.get("join") or [])
    return str(value)


def _safe_relative_path(raw: Any) -> Path:
    value = _assemble_value(raw)
    path = Path(value)
    if not value or path.is_absolute() or any(part == ".." for part in path.parts):
        raise ValueError(f"unsafe fixture path: {value!r}")
    return path


def _write_fixture_tree(case: Mapping[str, Any], root: Path) -> None:
    for row in case.get("files") or []:
        if not isinstance(row, Mapping):
            raise ValueError("fixture file rows must be JSON objects")
        rel = _safe_relative_path(row.get("path") if "path" in row else row.get("path_parts"))
        text = _assemble_value(row.get("text_parts") if "text_parts" in row else row.get("text"))
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _source_hash_cache_from_case(case: Mapping[str, Any]) -> Mapping[str, Any]:
    cache = case.get("source_hash_cache")
    return cache if isinstance(cache, Mapping) else {}


def evaluate_case(case: Mapping[str, Any], *, scratch: Path, path: str = "") -> dict[str, Any]:
    case_id = str(case.get("case_id") or Path(path).stem)
    case_root = scratch / case_id / "repo"
    case_root.mkdir(parents=True, exist_ok=True)
    _write_fixture_tree(case, case_root)

    owners_payload = case.get("owners")
    if not isinstance(owners_payload, list):
        raise ValueError(f"{case_id} must contain an owners array")
    owners = [owner_from_mapping(row) for row in owners_payload if isinstance(row, Mapping)]
    receipt = check_projection_drift(
        case_root,
        owners,
        owner_ids=case.get("owner_ids") if isinstance(case.get("owner_ids"), list) else None,
        changed_paths=case.get("changed_paths") if isinstance(case.get("changed_paths"), list) else None,
        source_hash_cache=_source_hash_cache_from_case(case),
        use_source_hash_cache=not bool(case.get("no_source_hash_cache")),
        timeout_seconds=int(case.get("timeout_seconds") or DEFAULT_COMMAND_TIMEOUT_SECONDS),
    )
    expected_status = str(case.get("expected_status") or "").strip().lower()
    expected_owner_count = case.get("expected_owner_count")
    owner_count_ok = (
        True if expected_owner_count is None else receipt["owner_count"] == int(expected_owner_count)
    )
    return {
        "case_id": case_id,
        "path": path,
        "expected_status": expected_status,
        "observed_status": receipt["status"],
        "expected_owner_count": expected_owner_count,
        "observed_owner_count": receipt["owner_count"],
        "expectation_met": bool(expected_status)
        and receipt["status"] == expected_status
        and owner_count_ok,
        "receipt": receipt,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_fixtures_") as tmp:
        scratch = Path(tmp)
        for path in sorted(input_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError(f"{path} did not contain a JSON object")
            cases.append(evaluate_case(payload, scratch=scratch, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engine Room generated projection drift gate.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Check owners for generated projection drift.")
    check.add_argument("--root", required=True)
    check.add_argument("--owners", required=True, help="JSON file containing an owners array.")
    check.add_argument("--owner", action="append", default=[])
    check.add_argument("--changed-path", "--path", action="append", default=[])
    check.add_argument("--no-source-cache", action="store_true")
    check.add_argument("--source-cache", default=None)
    check.add_argument("--timeout-seconds", type=int, default=DEFAULT_COMMAND_TIMEOUT_SECONDS)
    check.add_argument("--json", action="store_true")

    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "check":
        cache: Mapping[str, Any] = {}
        if args.source_cache:
            cache_payload = json.loads(Path(args.source_cache).read_text(encoding="utf-8"))
            if isinstance(cache_payload, Mapping):
                cache = cache_payload
        payload = check_projection_drift(
            Path(args.root),
            owners_from_json(Path(args.owners)),
            owner_ids=args.owner,
            changed_paths=args.changed_path,
            source_hash_cache=cache,
            use_source_hash_cache=not args.no_source_cache,
            timeout_seconds=args.timeout_seconds,
        )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{ORGAN_ID}: {payload['status']} owners={payload['owner_count']}")
        return 1 if payload["drift_owner_count"] else 0
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
