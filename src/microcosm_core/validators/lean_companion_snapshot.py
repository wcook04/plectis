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
# The compact cold-clone contract. Every provider adapter -- CLAUDE.md,
# CODEX.md, CURSOR.md and friends -- routes here, so a stale companion fact in
# this file is the first thing an unprimed agent learns about the mathematics.
# It sat outside this validator while the README was bound, and drifted: the
# README named eight open problems while this file said six.
AGENT_ENTRY_REL = Path("AGENTS.override.md")
EXPECTED_SCHEMA = "plectis-lean-companion-snapshot/v1"
EXPECTED_ROLE = "public_companion_scale_projection_not_proof_or_release_authority"
SCALE_KEYS = (
    "module_count",
    "declaration_count",
    "theorem_like_count",
    "generated_certificate_declaration_count",
    "principal_claim_link_count",
)
# Small enough to be exhaustive on purpose. A count this validator cannot spell
# is a count it should refuse rather than silently skip the prose check for.
_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


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


def _latest_release_tag(upstream_root: Path, public_ref: str) -> str | None:
    """The newest ``vX.Y.Z`` tag reachable from the tracked public ref.

    Only release tags count: the companion also carries dated provenance tags
    such as ``formal-source-2026-08-12-r2``, and ``git describe`` would return
    one of those, which is not a citation anchor. Returns ``None`` when no
    release tag is reachable, so the caller can keep the recorded value rather
    than blank a real anchor on a shallow or tagless checkout.
    """
    try:
        raw = _git_output(
            upstream_root, "tag", "--merged", public_ref, "--sort=-v:refname", "v*"
        )
    except Exception:
        return None
    for line in raw.splitlines():
        tag = line.strip()
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            return tag
    return None


def _problem_inventory_from_bytes(problems_bytes: bytes) -> dict[str, Any]:
    """Reduce the companion's problem registry to the facts prose may assert.

    Only three things travel: how many problems the companion tracks, which
    ones, and whether every one of them is still open. Those are exactly the
    claims Plectis prose makes about the companion, and none of them is a
    mathematical claim -- the registry is the authority, this is a projection.
    """
    problems = json.loads(problems_bytes)["problems"]
    numbers = sorted(int(problem["erdos_number"]) for problem in problems)
    statuses = {str(problem.get("status")) for problem in problems}
    return {
        "problem_count": len(numbers),
        "problem_numbers": numbers,
        "all_open": statuses == {"open"},
        "observed_statuses": sorted(statuses),
        "problems_sha256": hashlib.sha256(problems_bytes).hexdigest(),
    }


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
    # Derived, not carried forward. This field used to be copied from the
    # snapshot being refreshed, so every other value here tracked public main
    # while the tag silently aged: the README went on naming v0.6.0 as the
    # citation anchor two releases after the companion's own README and
    # CITATION.cff had moved to v0.8.0. Read it from the tags actually
    # reachable from the tracked ref, so a release cannot be announced by the
    # companion and missed here.
    latest_tag = _latest_release_tag(upstream_root, public_ref) or str(
        upstream["latest_tag"]
    )

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
    # Written back, not just used. Without this the name and the two hashes
    # below could disagree: the refresh would resolve the newest tag's objects
    # while still calling it by the old tag's name.
    refreshed_upstream["latest_tag"] = latest_tag
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
    # Derived from the tracked ref on every refresh, never carried forward from
    # the snapshot being replaced -- the same rule the release tag above had to
    # learn. If the companion opens a ninth problem or closes one, the count in
    # Plectis prose stops matching on the next refresh instead of aging quietly.
    problems_path = str(refreshed_upstream.setdefault("problems_path", "docs/problems.json"))
    problems_bytes = _git_output(
        upstream_root,
        "show",
        f"{public_ref}:{problems_path}",
    ).encode("utf-8")
    refreshed["problem_inventory"] = _problem_inventory_from_bytes(problems_bytes)
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
            # The release bullet is inside the managed block because it names
            # the same tag. It used to sit outside it, so a refresh updated the
            # sentence above and left this line pointing at an older release --
            # one README naming two different citation anchors.
            (
                f"- [**Release {latest_tag}**]"
                f"({repository}/releases/tag/{latest_tag}):"
            ),
            "  the tagged, citable scholarly artefact and citation anchor.",
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
        r"(?ms)^- \[\*\*Browse the Lean source\*\*\].*?citable scholarly "
        r"artefact and citation anchor\.\n"
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


def _expected_companion_fact_phrase(payload: dict[str, Any]) -> str:
    """The one sentence fragment any surface asserting the companion's scope owes.

    Deliberately a phrase and not a managed block: the README states this in
    running prose and the compact agent entry states it in its opening
    paragraph. Both must agree with the registry; neither should be rewritten
    wholesale by a refresh.
    """
    inventory = payload["problem_inventory"]
    count = int(inventory["problem_count"])
    word = _NUMBER_WORDS.get(count)
    if word is None:
        raise ValueError(f"no spelled form for problem_count={count}")
    if inventory["all_open"] is not True:
        # Not a formatting failure. The companion registry no longer reports
        # every tracked problem as open, so "N open Erdos problems" has become
        # a false public claim and a human has to choose the new wording.
        raise ValueError(
            "companion registry no longer reports every problem open: "
            f"{inventory.get('observed_statuses')}"
        )
    return f"{word} open Erdős problems"


def _validate_companion_facts(
    payload: dict[str, Any],
    root: Path,
    errors: list[dict[str, str]],
    findings: dict[str, Any],
) -> None:
    """Bind every public surface that names the companion's problem scope."""
    try:
        phrase = _expected_companion_fact_phrase(payload)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(
            {
                "code": "LEAN_COMPANION_PROBLEM_INVENTORY_INVALID",
                "detail": str(exc),
            }
        )
        return

    findings["companion_fact_phrase"] = phrase
    surfaces_missing: list[str] = []
    for rel in (README_REL, AGENT_ENTRY_REL):
        path = root / rel
        if not path.is_file():
            errors.append(
                {
                    "code": "LEAN_COMPANION_SURFACE_MISSING",
                    "detail": str(rel),
                }
            )
            continue
        if phrase not in path.read_text(encoding="utf-8"):
            surfaces_missing.append(str(rel))
    if surfaces_missing:
        errors.append(
            {
                "code": "LEAN_COMPANION_FACT_DRIFT",
                "detail": (
                    f"expected {phrase!r} in " + ", ".join(surfaces_missing)
                ),
            }
        )
    findings["companion_fact_missing_in"] = surfaces_missing


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

        problems_bytes = _git_output(
            upstream_root,
            "show",
            f"{public_ref}:{upstream.get('problems_path', 'docs/problems.json')}",
        ).encode("utf-8")
        upstream_inventory = _problem_inventory_from_bytes(problems_bytes)
        observed["problem_inventory"] = upstream_inventory
        recorded_inventory = payload.get("problem_inventory", {})
        for key in ("problem_count", "problem_numbers", "all_open", "problems_sha256"):
            if recorded_inventory.get(key) != upstream_inventory[key]:
                errors.append(
                    {
                        "code": "LEAN_COMPANION_PROBLEM_INVENTORY_DRIFT",
                        "detail": (
                            f"{key}: snapshot {recorded_inventory.get(key)!r} != "
                            f"upstream {upstream_inventory[key]!r}"
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

        _validate_companion_facts(payload, root, errors, findings)

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
