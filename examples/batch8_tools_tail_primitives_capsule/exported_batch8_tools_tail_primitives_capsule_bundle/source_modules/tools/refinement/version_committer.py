"""
[PURPOSE]
- Teleology: Provide atomic dossier mutation with git commit auditing for the refinement pipeline.
- Mechanism: Accept a list of patch operations (slash-selector vocabulary), apply them to the
  target dossier JSON atomically (temp-file + fsync + os.replace), then commit via git with a
  structured message. Returns a structured artifact JSON.
- Non-goal: Graph topology validation (handled by CodexPatcher); this module is a lower-level
  applier that trusts ops have already been validated.

[INTERFACE]
- Exports: VersionCommitter, commit_dossier_update
- Schema: Input ops use unified vocabulary: {op: set|merge|append, selector: slash/path, payload: any}
- Returns: {applied_ops, skipped_ops, commit_hash, dossier_path, run_id}

[CONSTRAINTS]
- Atomicity: All writes use temp-file + flush + fsync + os.replace. No .tmp left on success or failure.
- Containment: dossier_path must resolve within repo root (enforced by caller / PatcherError pattern).
- Git: If git is unavailable or fails, commit_hash = "NO_GIT" and execution continues.
- Idempotency: ops that find nothing to mutate (e.g. set-null on absent key) count as skipped, not failed.
- When-needed: Open when a refinement surface needs the atomic dossier mutation and git-audited commit boundary instead of the higher-level pipeline wrapper.
- Escalates-to: tools/refinement/run_evolve.py::run_evolve; tools/refinement/__init__.py
- Navigation-group: diff_refinement
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VersionCommitterError(Exception):
    """
    [ROLE]
    - Teleology: Domain exception for version committer failures.
    - Ownership: Owns no state; carries only the exception message.
    - Mutability: Immutable after construction.
    - Concurrency: Safe to raise and catch across threads.
    """
    pass


def _apply_op(data: Dict[str, Any], op: str, selector: str, payload: Any) -> Tuple[bool, str]:
    """
    [ACTION]
    Apply a single patch operation to a JSON dict in-place.

    - **Returns:** (was_mutated: bool, reason: str).
    - **Ops supported:** set, merge, append.
    - **Null-delete:** op=set with payload=None deletes the key (same contract as patcher.py).
    - **Raises:** VersionCommitterError on invalid selector traversal or unsupported op.
    """
    parts = [p for p in selector.split("/") if p] if selector else []

    if not parts:
        if op == "merge" and isinstance(payload, dict):
            data.update(payload)
            return True, "merged at root"
        raise VersionCommitterError(
            f"Empty selector is only valid for 'merge'; op={op!r} at root is not allowed."
        )

    # Traverse to parent container.
    container = data
    for part in parts[:-1]:
        if part not in container:
            container[part] = {}
        node = container[part]
        if not isinstance(node, dict):
            raise VersionCommitterError(
                f"Selector '{selector}' traverses into non-dict at '{part}' (got {type(node).__name__})."
            )
        container = node

    key = parts[-1]

    if op == "set":
        if payload is None:
            # Null-delete: remove the key if it exists.
            if key in container:
                del container[key]
                return True, f"deleted key '{key}'"
            return False, f"set-null: key '{key}' not present, nothing to delete"
        container[key] = payload
        return True, f"set '{key}'"

    elif op == "merge":
        if not isinstance(payload, dict):
            raise VersionCommitterError(f"'merge' op requires a dict payload; got {type(payload).__name__}.")
        if key not in container:
            container[key] = {}
        if not isinstance(container[key], dict):
            container[key] = {}
        container[key].update(payload)
        return True, f"merged into '{key}'"

    elif op == "append":
        if key not in container:
            container[key] = []
        if not isinstance(container[key], list):
            raise VersionCommitterError(f"Cannot append to non-list at '{key}'.")
        container[key].append(payload)
        return True, f"appended to '{key}'"

    else:
        raise VersionCommitterError(f"Unsupported op: {op!r}. Allowed: set, merge, append.")


def _git_commit(repo_root: Path, file_path: Path, message: str) -> str:
    """
    [ACTION]
    Stage and commit a single file via git.

    - **Returns:** Short commit hash on success, "NO_GIT" if git unavailable or fails.
    - **Guarantee:** Never raises; failures are logged and fall back to "NO_GIT".
    """
    try:
        subprocess.run(
            ["git", "add", str(file_path)],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            timeout=10,
        )
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Extract short hash from "git commit" output: "[branch abc1234] ..."
        output = result.stdout.strip()
        for line in output.splitlines():
            import re
            match = re.search(r"\[[\w/]+ ([0-9a-f]+)\]", line)
            if match:
                return match.group(1)
        # Fallback: ask git directly.
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return rev.stdout.strip()
    except Exception as exc:
        logger.warning("[version_committer] git commit failed: %s", exc)
        return "NO_GIT"


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    """
    [ACTION]
    Write JSON data atomically using temp-file + fsync + os.replace.

    - **Guarantee:** No .tmp file is left on success OR failure (cleaned up in except block).
    - **Guarantee:** File content is fully flushed to OS before rename.
    """
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Optional[Path] = None
    try:
        fd, tmp_str = tempfile.mkstemp(dir=str(parent), suffix=".tmp", prefix=f"{path.stem}_")
        tmp_path = Path(tmp_str)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        tmp_path = None  # Rename succeeded — no cleanup needed.
    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise


class VersionCommitter:
    """
    [ROLE]
    - Teleology: Apply a list of patch operations to a dossier JSON file atomically and commit via git.
    - Mechanism: Load dossier -> apply ops in order -> atomic write -> git commit -> return artifact.
    - Ownership: Owns the repo_root binding; delegates file I/O to _atomic_write and git to _git_commit.
    - Mutability: Effectively immutable after __init__; repo_root is set once and never modified.
    - Concurrency: Not thread-safe; callers must serialize commits to the same dossier file.
    - Guarantee: No partial writes. Either all ops apply and get committed, or the file is unchanged.
    - Non-goal: Cross-file transactions or topology validation (handled by CodexPatcher upstream).
    """

    def __init__(self, repo_root: Path) -> None:
        """
        [ACTION]
        - Teleology: Bind the committer to a repository root for git operations.
        - Guarantee: self.repo_root is an absolute resolved Path after construction.
        - Fails: None.
        """
        self.repo_root = Path(repo_root).resolve()

    def commit(
        self,
        *,
        ops: List[Dict[str, Any]],
        dossier_path: str,
        run_id: str,
        lane: str,
        observation_report_path: str,
    ) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Apply one batch of validated dossier ops and produce the auditable mutation artifact consumed by refinement callers.
        - Mechanism: Resolve the dossier path under repo_root, load JSON, apply ops in order through _apply_op(), atomically rewrite the dossier, then attempt a git commit.
        - Reads: dossier_path JSON under repo_root and the git repository state for commit metadata.
        - Writes: The target dossier JSON via _atomic_write() and the git index/history via _git_commit().
        - Guarantee: Returns {applied_ops, skipped_ops, commit_hash, dossier_path, run_id} after the dossier write completes; git failures degrade to commit_hash="NO_GIT" instead of aborting the mutation.
        - Fails: Raises VersionCommitterError on dossier read/write failures or invalid op contracts before the atomic write completes.
        - When-needed: Open when a refinement caller needs the exact write, skip, and commit semantics for one dossier mutation batch.
        - Escalates-to: tools/refinement/run_evolve.py::run_evolve; tools/refinement/__init__.py
        - Navigation-group: diff_refinement
        """
        target = Path(dossier_path)
        if not target.is_absolute():
            target = (self.repo_root / target).resolve()

        # Load existing dossier.
        if not target.exists():
            raise VersionCommitterError(f"Dossier not found: {target}")
        try:
            with open(target, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
        except Exception as exc:
            raise VersionCommitterError(f"Failed to read dossier {target}: {exc}") from exc

        applied_ops: List[Dict[str, Any]] = []
        skipped_ops: List[Dict[str, Any]] = []

        # Apply each op.
        for idx, op_spec in enumerate(ops):
            op = str(op_spec.get("op", "")).lower()
            selector = str(op_spec.get("selector", ""))
            payload = op_spec.get("payload")

            try:
                mutated, reason = _apply_op(data, op, selector, payload)
                if mutated:
                    applied_ops.append({"index": idx, "op": op, "selector": selector, "reason": reason})
                else:
                    skipped_ops.append({"index": idx, "op": op, "selector": selector, "reason": reason})
            except VersionCommitterError as op_err:
                raise VersionCommitterError(
                    f"Op #{idx} failed ({op!r} @ {selector!r}): {op_err}"
                ) from op_err

        # Atomic write.
        _atomic_write(target, data)
        logger.info("[version_committer] Wrote %s (%d applied, %d skipped)", target.name, len(applied_ops), len(skipped_ops))

        # Git commit.
        commit_message = (
            f"refine(dossier): {lane} updated by run {run_id} from {observation_report_path}"
        )
        commit_hash = _git_commit(self.repo_root, target, commit_message)

        return {
            "applied_ops": applied_ops,
            "skipped_ops": skipped_ops,
            "commit_hash": commit_hash,
            "dossier_path": str(target),
            "run_id": run_id,
        }


def commit_dossier_update(
    *,
    ops: List[Dict[str, Any]],
    dossier_path: str,
    run_id: str,
    lane: str,
    observation_report_path: str,
    repo_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Expose a function-level convenience wrapper for dossier updates when callers do not need to manage a VersionCommitter instance directly.
    - Mechanism: Resolve repo_root, instantiate VersionCommitter, and delegate to commit().
    - Guarantee: Returns the same artifact dict shape as VersionCommitter.commit().
    - Fails: Propagates VersionCommitterError from the underlying commit() call.
    - When-needed: Open when a caller wants the refinement mutation entrypoint without reading the class surface first.
    - Escalates-to: tools/refinement/version_committer.py::VersionCommitter.commit; tools/refinement/run_evolve.py::run_evolve
    """
    root = Path(repo_root).resolve() if repo_root else Path(".").resolve()
    committer = VersionCommitter(repo_root=root)
    return committer.commit(
        ops=ops,
        dossier_path=dossier_path,
        run_id=run_id,
        lane=lane,
        observation_report_path=observation_report_path,
    )
