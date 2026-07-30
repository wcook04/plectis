"""Validate Plectis's bounded public Lean-companion scale projection.

This validator binds the human-facing README counts to an exact upstream
public commit. It may also compare that commit with a sibling Lean checkout.
The receipt is navigation evidence only: it does not establish mathematical
correctness, authorize release, or assert equivalence with private work.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


SNAPSHOT_REL = Path("docs/lean_companion_snapshot.json")
README_REL = Path("README.md")
EXPECTED_SCHEMA = "plectis-lean-companion-snapshot/v1"
EXPECTED_ROLE = "public_companion_scale_projection_not_proof_or_release_authority"
SCALE_KEYS = (
    "module_count",
    "declaration_count",
    "theorem_like_count",
    "generated_certificate_declaration_count",
    "principal_claim_link_count",
)


def _git_output(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise ValueError(detail)
    return result.stdout


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _build_snapshot_from_upstream(
    payload: dict[str, Any],
    upstream_root: Path,
) -> dict[str, Any]:
    """Return a deterministic snapshot derived from the tracked public ref."""
    upstream = payload["upstream"]
    public_ref = _git_output(
        upstream_root,
        "rev-parse",
        str(upstream["remote_tracking_ref"]),
    ).strip()
    orientation_bytes = _git_output(
        upstream_root,
        "show",
        f"{public_ref}:{upstream['orientation_path']}",
    ).encode("utf-8")
    orientation = json.loads(orientation_bytes)
    upstream_scale = orientation["scale"]
    latest_tag = str(upstream["latest_tag"])

    refreshed = json.loads(json.dumps(payload))
    refreshed["observed_at"] = _git_output(
        upstream_root,
        "show",
        "-s",
        "--format=%cs",
        public_ref,
    ).strip()
    refreshed_upstream = refreshed["upstream"]
    refreshed_upstream["public_ref"] = public_ref
    refreshed_upstream["orientation_sha256"] = hashlib.sha256(
        orientation_bytes
    ).hexdigest()
    refreshed_upstream["release_tag_object"] = _git_output(
        upstream_root,
        "rev-parse",
        latest_tag,
    ).strip()
    refreshed_upstream["release_commit"] = _git_output(
        upstream_root,
        "rev-parse",
        f"{latest_tag}^{{}}",
    ).strip()
    refreshed["scale"] = {key: int(upstream_scale[key]) for key in SCALE_KEYS}
    refreshed["refresh"]["local_command"] = (
        "PYTHONPATH=src python3 scripts/check_lean_companion_snapshot.py "
        "--write --upstream-root ../plectis-lean-erdos249-257"
    )
    return refreshed


def _readme_companion_block(payload: dict[str, Any]) -> str:
    upstream = payload["upstream"]
    scale = payload["scale"]
    repository = str(upstream["repository"]).rstrip("/")
    public_ref = str(upstream["public_ref"])
    latest_tag = str(upstream["latest_tag"])
    return "\n".join(
        [
            f"- [**Browse the Lean source**]({repository}/tree/{public_ref}):",
            (
                f"  the recorded public source snapshot contains "
                f"{int(scale['module_count']):,} Lean modules and "
                f"{int(scale['theorem_like_count']):,}"
            ),
            "  theorem-like declarations, checked by the pinned kernel; start from",
            "  `docs/ORIENTATION.md`. These are scale and navigation counts, not separate",
            (
                f"  mathematical claims; `{latest_tag}` remains the tagged "
                "citation anchor."
            ),
        ]
    )


def refresh_lean_companion_snapshot(
    root: Path,
    *,
    upstream_root: Path,
) -> dict[str, Any]:
    """Refresh the bounded projection and its README binding from public Git."""
    root = root.resolve()
    upstream_root = upstream_root.resolve()
    snapshot_path = root / SNAPSHOT_REL
    readme_path = root / README_REL
    payload = _load_json(snapshot_path)
    refreshed = _build_snapshot_from_upstream(payload, upstream_root)

    readme = readme_path.read_text(encoding="utf-8")
    block_pattern = re.compile(
        r"(?ms)^- \[\*\*Browse the Lean source\*\*\].*?(?=^- \[\*\*Release )"
    )
    if block_pattern.search(readme) is None:
        raise ValueError("README Lean companion block is missing")
    refreshed_readme = block_pattern.sub(
        _readme_companion_block(refreshed) + "\n",
        readme,
        count=1,
    )

    snapshot_path.write_text(
        json.dumps(refreshed, indent=2) + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(refreshed_readme, encoding="utf-8")
    receipt = validate_lean_companion_snapshot(
        root,
        upstream_root=upstream_root,
    )
    receipt["mode"] = "refreshed"
    return receipt


def _expected_readme_fragments(payload: dict[str, Any]) -> list[str]:
    upstream = payload["upstream"]
    scale = payload["scale"]
    repository = str(upstream["repository"]).rstrip("/")
    public_ref = str(upstream["public_ref"])
    latest_tag = str(upstream["latest_tag"])
    return [
        f"{repository}/tree/{public_ref}",
        (
            f"the recorded public source snapshot contains "
            f"{int(scale['module_count']):,} Lean modules and "
            f"{int(scale['theorem_like_count']):,}"
        ),
        "theorem-like declarations, checked by the pinned kernel",
        "These are scale and navigation counts, not separate",
        "mathematical claims",
        f"`{latest_tag}` remains the tagged citation anchor",
    ]


def _validate_upstream(
    payload: dict[str, Any],
    upstream_root: Path,
    errors: list[dict[str, str]],
) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    upstream = payload["upstream"]
    public_ref = str(upstream["public_ref"])
    tracked_branch = str(upstream["tracked_branch"])
    remote_tracking_ref = str(upstream["remote_tracking_ref"])
    orientation_path = str(upstream["orientation_path"])

    try:
        public_head = _git_output(
            upstream_root,
            "rev-parse",
            remote_tracking_ref,
        ).strip()
        observed["tracked_branch_head"] = public_head
        if public_head != public_ref:
            errors.append(
                {
                    "code": "LEAN_COMPANION_PUBLIC_REF_STALE",
                    "detail": (
                        f"snapshot {public_ref} != {remote_tracking_ref} "
                        f"({tracked_branch}) {public_head}"
                    ),
                }
            )

        orientation_bytes = _git_output(
            upstream_root,
            "show",
            f"{public_ref}:{orientation_path}",
        ).encode("utf-8")
        observed["orientation_sha256"] = hashlib.sha256(orientation_bytes).hexdigest()
        orientation = json.loads(orientation_bytes)
        upstream_scale = orientation["scale"]
        observed["scale"] = {key: upstream_scale[key] for key in SCALE_KEYS}
        for key in SCALE_KEYS:
            expected = payload["scale"].get(key)
            actual = upstream_scale.get(key)
            if expected != actual:
                errors.append(
                    {
                        "code": "LEAN_COMPANION_SCALE_DRIFT",
                        "detail": f"{key}: snapshot {expected!r} != upstream {actual!r}",
                    }
                )

        expected_digest = str(upstream["orientation_sha256"])
        if observed["orientation_sha256"] != expected_digest:
            errors.append(
                {
                    "code": "LEAN_COMPANION_ORIENTATION_DIGEST_DRIFT",
                    "detail": (
                        f"snapshot {expected_digest} != upstream "
                        f"{observed['orientation_sha256']}"
                    ),
                }
            )

        release_commit = _git_output(
            upstream_root,
            "rev-parse",
            f"{upstream['latest_tag']}^{{}}",
        ).strip()
        observed["release_commit"] = release_commit
        if release_commit != upstream["release_commit"]:
            errors.append(
                {
                    "code": "LEAN_COMPANION_RELEASE_COMMIT_DRIFT",
                    "detail": (
                        f"snapshot {upstream['release_commit']} != upstream "
                        f"{release_commit}"
                    ),
                }
            )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        errors.append(
            {
                "code": "LEAN_COMPANION_UPSTREAM_READ_FAILED",
                "detail": str(exc),
            }
        )
    return observed


def validate_lean_companion_snapshot(
    root: Path,
    *,
    upstream_root: Path | None = None,
) -> dict[str, Any]:
    """Return a failure-first receipt for the companion snapshot binding."""
    root = root.resolve()
    snapshot_path = root / SNAPSHOT_REL
    readme_path = root / README_REL
    errors: list[dict[str, str]] = []
    findings: dict[str, Any] = {}

    if not snapshot_path.is_file():
        errors.append(
            {
                "code": "LEAN_COMPANION_SNAPSHOT_MISSING",
                "detail": str(SNAPSHOT_REL),
            }
        )
        return {
            "schema": "plectis-lean-companion-validation/v1",
            "status": "blocked",
            "errors": errors,
            "findings": findings,
            "authority_ceiling": {
                "release_authorized": False,
                "proof_correctness_claim": False,
                "private_root_equivalence_asserted": False,
            },
        }

    try:
        payload = _load_json(snapshot_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(
            {
                "code": "LEAN_COMPANION_SNAPSHOT_INVALID",
                "detail": str(exc),
            }
        )
        payload = {}

    if payload:
        if payload.get("schema") != EXPECTED_SCHEMA:
            errors.append(
                {
                    "code": "LEAN_COMPANION_SCHEMA_MISMATCH",
                    "detail": repr(payload.get("schema")),
                }
            )
        if payload.get("artifact_role") != EXPECTED_ROLE:
            errors.append(
                {
                    "code": "LEAN_COMPANION_ROLE_MISMATCH",
                    "detail": repr(payload.get("artifact_role")),
                }
            )

        try:
            scale = payload["scale"]
            for key in SCALE_KEYS:
                if not isinstance(scale.get(key), int) or scale[key] <= 0:
                    errors.append(
                        {
                            "code": "LEAN_COMPANION_SCALE_INVALID",
                            "detail": f"{key}={scale.get(key)!r}",
                        }
                    )
            ceiling = payload["authority_ceiling"]
            if ceiling.get("scale_projection_only") is not True:
                errors.append(
                    {
                        "code": "LEAN_COMPANION_SCALE_CEILING_MISSING",
                        "detail": "scale_projection_only must be true",
                    }
                )
            for key in (
                "release_authorized",
                "private_root_equivalence_asserted",
                "open_problem_solution_claimed",
            ):
                if ceiling.get(key) is not False:
                    errors.append(
                        {
                            "code": "LEAN_COMPANION_AUTHORITY_OVERCLAIM",
                            "detail": f"{key} must be false",
                        }
                    )
        except (KeyError, TypeError) as exc:
            errors.append(
                {
                    "code": "LEAN_COMPANION_REQUIRED_FIELD_MISSING",
                    "detail": str(exc),
                }
            )

        if readme_path.is_file():
            readme = readme_path.read_text(encoding="utf-8")
            try:
                missing = [
                    fragment
                    for fragment in _expected_readme_fragments(payload)
                    if fragment not in readme
                ]
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(
                    {
                        "code": "LEAN_COMPANION_README_BINDING_INVALID",
                        "detail": str(exc),
                    }
                )
                missing = []
            if missing:
                errors.append(
                    {
                        "code": "LEAN_COMPANION_README_DRIFT",
                        "detail": "; ".join(missing),
                    }
                )
            findings["readme_binding_missing"] = missing
        else:
            errors.append(
                {
                    "code": "LEAN_COMPANION_README_MISSING",
                    "detail": str(README_REL),
                }
            )

        if upstream_root is not None:
            findings["upstream"] = _validate_upstream(
                payload,
                upstream_root.resolve(),
                errors,
            )

        findings["public_ref"] = payload.get("upstream", {}).get("public_ref")
        findings["latest_tag"] = payload.get("upstream", {}).get("latest_tag")
        findings["scale"] = payload.get("scale")

    return {
        "schema": "plectis-lean-companion-validation/v1",
        "status": "pass" if not errors else "blocked",
        "errors": errors,
        "findings": findings,
        "authority_ceiling": {
            "release_authorized": False,
            "proof_correctness_claim": False,
            "private_root_equivalence_asserted": False,
        },
    }
